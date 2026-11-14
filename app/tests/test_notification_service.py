from typing import Any

import httpx
import pytest

from app.services import notification_service
from app.services.notification_service import send_push


def test_send_push_is_noop_without_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: calls.append((a, k)))

    send_push([], "Título", "Corpo")

    assert calls == []


def test_send_push_calls_expo_api_with_expected_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, json: Any = None, timeout: float | None = None) -> httpx.Response:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return httpx.Response(status_code=200, json={"data": []})

    monkeypatch.setattr(httpx, "post", fake_post)

    send_push(
        ["ExponentPushToken[aaa]", "ExponentPushToken[bbb]"],
        "Nova mensagem",
        "Bora jogar!",
        data={"type": "new_message", "matchId": "match-1"},
    )

    assert captured["url"] == notification_service.EXPO_PUSH_URL
    assert captured["json"] == [
        {
            "to": "ExponentPushToken[aaa]",
            "title": "Nova mensagem",
            "body": "Bora jogar!",
            "data": {"type": "new_message", "matchId": "match-1"},
        },
        {
            "to": "ExponentPushToken[bbb]",
            "title": "Nova mensagem",
            "body": "Bora jogar!",
            "data": {"type": "new_message", "matchId": "match-1"},
        },
    ]


def test_send_push_never_raises_on_network_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("boom", request=httpx.Request("POST", "https://exp.host"))

    monkeypatch.setattr(httpx, "post", fake_post)

    send_push(["ExponentPushToken[aaa]"], "Título", "Corpo")


def _respond_with(response: httpx.Response) -> Any:
    return lambda *args, **kwargs: response


def test_send_push_logs_error_tickets_without_tokens(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    tickets = [
        {"status": "ok", "id": "t1"},
        {"status": "error", "message": "...", "details": {"error": "InvalidCredentials"}},
        {"status": "error", "message": "...", "details": {"error": "DeviceNotRegistered"}},
    ]
    monkeypatch.setattr(httpx, "post", _respond_with(httpx.Response(200, json={"data": tickets})))

    with caplog.at_level("WARNING"):
        send_push([f"ExponentPushToken[{n}]" for n in "abc"], "T", "C")

    assert "Expo recusou 2 de 3 push(es)" in caplog.text
    assert "InvalidCredentials" in caplog.text
    assert "DeviceNotRegistered" in caplog.text
    assert "ExponentPushToken" not in caplog.text


def test_send_push_logs_http_error_status(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(httpx, "post", _respond_with(httpx.Response(500, text="erro")))

    with caplog.at_level("WARNING"):
        send_push(["ExponentPushToken[a]"], "T", "C")

    assert "HTTP 500" in caplog.text


def test_send_push_logs_unexpected_response_body(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(httpx, "post", _respond_with(httpx.Response(200, text="não é json")))

    with caplog.at_level("WARNING"):
        send_push(["ExponentPushToken[a]"], "T", "C")

    assert "Resposta inesperada da Expo" in caplog.text


def test_send_push_does_not_log_when_all_tickets_ok(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    ok = httpx.Response(200, json={"data": [{"status": "ok", "id": "t1"}]})
    monkeypatch.setattr(httpx, "post", _respond_with(ok))

    with caplog.at_level("WARNING"):
        send_push(["ExponentPushToken[a]"], "T", "C")

    assert caplog.text == ""
