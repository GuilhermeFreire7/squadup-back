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
        response = httpx.post(EXPO_PUSH_URL, json=messages, timeout=5.0)
    except httpx.HTTPError:
        logger.warning("Falha ao enviar push para %d destinatário(s)", len(tokens), exc_info=True)
        return

    _log_rejected_pushes(response, len(tokens))


def _log_rejected_pushes(response: httpx.Response, sent: int) -> None:
    """Registra as recusas da Expo, que responde 200 mesmo quando rejeita um envio.

    Cada mensagem gera um "ticket"; um ticket com `status: error` traz o motivo (ex.:
    `InvalidCredentials` quando falta a chave do FCM no projeto, `DeviceNotRegistered` quando o
    app foi desinstalado). Só o código do erro vai para o log: tokens identificam aparelhos.
    """
    if response.status_code >= 400:
        logger.warning("Expo recusou o envio de %d push(es): HTTP %d", sent, response.status_code)
        return
    try:
        tickets = response.json().get("data", [])
    except (ValueError, AttributeError):
        logger.warning("Resposta inesperada da Expo ao enviar %d push(es)", sent)
        return
    errors = [
        ticket.get("details", {}).get("error", "unknown")
        for ticket in tickets
        if isinstance(ticket, dict) and ticket.get("status") == "error"
    ]
    if errors:
        logger.warning("Expo recusou %d de %d push(es): %s", len(errors), sent, sorted(set(errors)))
