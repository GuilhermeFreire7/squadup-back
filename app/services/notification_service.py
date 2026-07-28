import logging

import httpx

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_push(
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> None:
    """Envia uma notificação push via Expo Push API para os tokens informados.

    Nunca propaga exceção: falha de entrega (rede fora do ar, token inválido/expirado) é só
    logada, para não comprometer a resposta do endpoint que originou o evento (D-Push-4).
    Chamada de dentro de um `BackgroundTasks`, depois que a transação principal já commitou.
    """
    if not tokens:
        return

    messages = [{"to": token, "title": title, "body": body, "data": data or {}} for token in tokens]

    try:
        httpx.post(EXPO_PUSH_URL, json=messages, timeout=5.0)
    except httpx.HTTPError:
        logger.warning("Falha ao enviar push para %d destinatário(s)", len(tokens), exc_info=True)
