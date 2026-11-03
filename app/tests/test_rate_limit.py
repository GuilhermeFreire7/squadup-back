from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import get_settings
from app.core.rate_limit import RateLimiter, client_ip

REGISTER_PAYLOAD = {
    "name": "Ana Souza",
    "email": "ana@example.com",
    "password": "senha-super-secreta",
    "age": 28,
    "location": "Rio de Janeiro, RJ",
}


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _request(headers: dict[str, str], host: str = "10.0.0.1") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (host, 1234),
    }
    return Request(scope)


def _login(
    client: TestClient, email: str, password: str, ip: str | None = None
) -> tuple[int, dict[str, str], dict[str, Any]]:
    headers = {"True-Client-IP": ip} if ip else {}
    response = client.post(
        "/auth/login", json={"email": email, "password": password}, headers=headers
    )
    return response.status_code, dict(response.headers), response.json()


# --- RateLimiter ---------------------------------------------------------------------------


def test_rate_limiter_blocks_after_limit_and_reports_retry_after() -> None:
    clock = FakeClock()
    limiter = RateLimiter(limit=2, window_seconds=60, clock=clock)

    assert limiter.hit("k") is None
    clock.now += 10
    assert limiter.hit("k") is None
    clock.now += 5

    assert limiter.hit("k") == pytest.approx(45)


def test_rate_limiter_window_slides() -> None:
    clock = FakeClock()
    limiter = RateLimiter(limit=1, window_seconds=60, clock=clock)
    limiter.hit("k")

    clock.now += 60

    assert limiter.hit("k") is None


def test_rate_limiter_keys_are_independent() -> None:
    limiter = RateLimiter(limit=1, window_seconds=60, clock=FakeClock())
    limiter.hit("a")

    assert limiter.hit("b") is None
    assert limiter.hit("a") is not None


def test_rate_limiter_record_and_retry_after_do_not_count_queries() -> None:
    limiter = RateLimiter(limit=2, window_seconds=60, clock=FakeClock())

    assert limiter.retry_after("k") is None
    limiter.record("k")
    assert limiter.retry_after("k") is None
    limiter.record("k")

    assert limiter.retry_after("k") is not None


def test_rate_limiter_prunes_expired_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.rate_limit._MAX_KEYS_BEFORE_PRUNE", 2)
    clock = FakeClock()
    limiter = RateLimiter(limit=5, window_seconds=60, clock=clock)
    for key in ("a", "b", "c"):
        limiter.record(key)
    clock.now += 61

    limiter.record("d")

    assert set(limiter._events) == {"d"}


# --- client_ip -----------------------------------------------------------------------------


def test_client_ip_uses_configured_header() -> None:
    request = _request({"True-Client-IP": "203.0.113.7", "X-Forwarded-For": "1.1.1.1"})

    assert client_ip(request) == "203.0.113.7"


def test_client_ip_falls_back_to_connection_when_header_missing() -> None:
    assert client_ip(_request({"X-Forwarded-For": "1.1.1.1"})) == "10.0.0.1"


def test_client_ip_ignores_header_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "client_ip_header", None)

    assert client_ip(_request({"True-Client-IP": "203.0.113.7"})) == "10.0.0.1"


# --- Rotas ---------------------------------------------------------------------------------


def test_login_is_limited_per_ip(client: TestClient) -> None:
    for i in range(20):
        status_code, _, _ = _login(client, f"ninguem{i}@example.com", "x", ip="203.0.113.7")
        assert status_code == 401

    status_code, headers, body = _login(client, "outro@example.com", "x", ip="203.0.113.7")

    assert status_code == 429
    assert body["detail"] == {
        "code": "RATE_LIMITED",
        "message": "Muitas tentativas. Aguarde um pouco e tente novamente.",
    }
    assert int(headers["retry-after"]) >= 1


def test_login_limit_is_separate_per_client_ip(client: TestClient) -> None:
    for i in range(20):
        _login(client, f"ninguem{i}@example.com", "x", ip="203.0.113.7")

    status_code, _, _ = _login(client, "outro@example.com", "x", ip="198.51.100.9")

    assert status_code == 401


def test_login_limit_ignores_spoofed_x_forwarded_for(client: TestClient) -> None:
    for i in range(20):
        client.post(
            "/auth/login",
            json={"email": f"ninguem{i}@example.com", "password": "x"},
            headers={"X-Forwarded-For": f"10.9.9.{i}"},
        )

    response = client.post(
        "/auth/login",
        json={"email": "outro@example.com", "password": "x"},
        headers={"X-Forwarded-For": "10.9.9.250"},
    )

    assert response.status_code == 429


def test_login_blocks_account_after_failures_from_any_ip(client: TestClient) -> None:
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    for i in range(10):
        status_code, _, _ = _login(client, "ana@example.com", "errada", ip=f"203.0.113.{i}")
        assert status_code == 401

    # Mesmo com a senha certa e de outro IP: a conta fica bloqueada até a janela passar.
    status_code, _, body = _login(
        client, "ANA@example.com", str(REGISTER_PAYLOAD["password"]), ip="198.51.100.1"
    )

    assert status_code == 429
    assert body["detail"]["code"] == "RATE_LIMITED"


def test_successful_logins_do_not_count_as_failures(client: TestClient) -> None:
    client.post("/auth/register", json=REGISTER_PAYLOAD)
    for i in range(11):
        status_code, _, _ = _login(
            client, "ana@example.com", str(REGISTER_PAYLOAD["password"]), ip=f"203.0.113.{i}"
        )
        assert status_code == 200


def test_register_is_limited_per_ip(client: TestClient) -> None:
    headers = {"True-Client-IP": "203.0.113.7"}
    for i in range(10):
        payload = {**REGISTER_PAYLOAD, "email": f"user{i}@example.com"}
        assert client.post("/auth/register", json=payload, headers=headers).status_code == 201

    payload = {**REGISTER_PAYLOAD, "email": "user10@example.com"}
    response = client.post("/auth/register", json=payload, headers=headers)

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "RATE_LIMITED"


def test_rate_limit_can_be_disabled(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", False)
    client.post("/auth/register", json=REGISTER_PAYLOAD)

    for _ in range(25):
        status_code, _, _ = _login(client, "ana@example.com", "errada", ip="203.0.113.7")
        assert status_code == 401
