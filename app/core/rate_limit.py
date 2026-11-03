"""Limite de tentativas em memória para as rotas de autenticação.

Janela deslizante por chave (IP do cliente ou e-mail), guardada no próprio processo. Basta para
o deploy atual (um único processo uvicorn no Render). Com várias réplicas, cada uma teria o seu
contador e o limite efetivo seria multiplicado; aí o estado precisaria ir para um armazenamento
compartilhado (ex.: Redis).
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable

import structlog
from fastapi import HTTPException, Request, status

from app.core.config import get_settings

logger = structlog.get_logger("app.rate_limit")

RATE_LIMITED_MESSAGE = "Muitas tentativas. Aguarde um pouco e tente novamente."

# Acima disso, cada registro de tentativa também descarta as chaves sem tentativas na janela,
# para o dicionário não crescer sem limite com IPs/e-mails que não voltam mais.
_MAX_KEYS_BEFORE_PRUNE = 10_000


class RateLimiter:
    """Permite até `limit` eventos por chave dentro de `window_seconds` (janela deslizante)."""

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _expire(self, events: deque[float], now: float) -> None:
        while events and now - events[0] >= self.window_seconds:
            events.popleft()

    def retry_after(self, key: str) -> float | None:
        """Segundos até a chave voltar a ser aceita, ou `None` se ainda há tentativas livres."""
        with self._lock:
            now = self._clock()
            events = self._events.get(key)
            if events is None:
                return None
            self._expire(events, now)
            if len(events) < self.limit:
                return None
            return self.window_seconds - (now - events[0])

    def record(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            if len(self._events) > _MAX_KEYS_BEFORE_PRUNE:
                self._prune(now)
            events = self._events.setdefault(key, deque())
            self._expire(events, now)
            events.append(now)

    def hit(self, key: str) -> float | None:
        """Registra uma tentativa se houver espaço; senão devolve o `retry_after` sem registrar."""
        with self._lock:
            now = self._clock()
            events = self._events.setdefault(key, deque())
            self._expire(events, now)
            if len(events) >= self.limit:
                return self.window_seconds - (now - events[0])
            events.append(now)
            return None

    def _prune(self, now: float) -> None:
        for key in list(self._events):
            events = self._events[key]
            self._expire(events, now)
            if not events:
                del self._events[key]

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


# Folgados de propósito: na defesa/demonstração, várias pessoas na mesma rede saem pelo mesmo IP.
login_ip_limiter = RateLimiter(limit=20, window_seconds=60)
register_ip_limiter = RateLimiter(limit=10, window_seconds=60 * 60)
# Falhas de login por e-mail, independente do IP: protege cada conta (inclusive a de admin)
# contra força bruta distribuída. Login bem-sucedido não conta.
login_failure_limiter = RateLimiter(limit=10, window_seconds=15 * 60)

ALL_LIMITERS = (login_ip_limiter, register_ip_limiter, login_failure_limiter)


def rate_limited_error(retry_after: float) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={"code": "RATE_LIMITED", "message": RATE_LIMITED_MESSAGE},
        headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
    )


def client_ip(request: Request) -> str:
    """IP do cliente usado como chave do limite.

    No Render, a requisição chega pelo Cloudflare, que preenche `True-Client-IP` com o IP real e
    sobrescreve o que o cliente mandar. O `X-Forwarded-For` não serve: o proxy do Render anexa ao
    valor recebido em vez de substituí-lo, então o cliente consegue forjá-lo. Sem o header
    configurado (ou ausente, como em dev/testes), usa o IP da conexão TCP.
    """
    return _client_ip_and_source(request)[0]


def _client_ip_and_source(request: Request) -> tuple[str, str]:
    header = get_settings().client_ip_header
    if header:
        value = request.headers.get(header, "").strip()
        if value:
            return value, "header"
    return (request.client.host if request.client else "unknown"), "connection"


def _ip_limit_dependency(limiter: RateLimiter) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        ip, source = _client_ip_and_source(request)
        # Só a origem da chave, nunca o IP (dado pessoal). Em produção deve ser sempre "header";
        # "connection" no Render indicaria que o limite está agrupando todos pelo IP do proxy.
        logger.info("rate_limit_key", ip_source=source)
        retry_after = limiter.hit(ip)
        if retry_after is not None:
            raise rate_limited_error(retry_after)

    return dependency


limit_login_by_ip = _ip_limit_dependency(login_ip_limiter)
limit_register_by_ip = _ip_limit_dependency(register_ip_limiter)
