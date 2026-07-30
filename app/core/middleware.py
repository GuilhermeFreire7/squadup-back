import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.metrics import REQUEST_DURATION_SECONDS, REQUESTS_TOTAL

logger = structlog.get_logger("app.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Correlaciona logs e métricas por requisição (T5).

    Gera (ou propaga, se o cliente já enviou) um `request_id`, devolvido em
    `X-Request-ID`, e o injeta em todo log estruturado emitido durante a requisição via
    `structlog.contextvars` — permite juntar todas as linhas de uma mesma requisição num
    sistema de agregação de logs. Também alimenta os contadores/histogramas do Prometheus
    expostos em `GET /metrics`.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        status_code = 500
        response: Response | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start
            route = request.scope.get("route")
            path_template = route.path if route is not None else request.url.path

            REQUESTS_TOTAL.labels(request.method, path_template, status_code).inc()
            REQUEST_DURATION_SECONDS.labels(request.method, path_template).observe(duration)
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=round(duration * 1000, 2),
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
