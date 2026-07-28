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
