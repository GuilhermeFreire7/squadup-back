from typing import Any

import httpx


def record_push(sent_tokens: list[str], messages: list[dict[str, Any]]) -> httpx.Response:
    """Substituto de `httpx.post` nos testes: guarda os tokens e responde como a Expo (200, ok)."""
    sent_tokens.extend(message["to"] for message in messages)
    return httpx.Response(200, json={"data": [{"status": "ok"} for _ in messages]})
