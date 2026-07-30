import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import ValidationError
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.core.security import decode_access_token
from app.core.ws_manager import manager
from app.models.user import User
from app.schemas.errors import AUTH_ERRORS, error_responses
from app.schemas.message import MessageCreate, MessageRead
from app.services.message_service import create_message, ensure_chat_access, list_messages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches/{match_id}/messages", tags=["messages"])

# Códigos de fechamento WebSocket específicos da aplicação (faixa 4000-4999, livre por RFC 6455).
WS_UNAUTHORIZED = 4401
WS_FORBIDDEN = 4403
WS_NOT_FOUND = 4404

ws_router = APIRouter(prefix="/matches/{match_id}", tags=["messages"])

_CHAT_ACCESS_ERRORS = (
    (404, "MATCH_NOT_FOUND", "Partida não encontrada."),
    (
        403,
        "NOT_MATCH_PARTICIPANT",
        "Apenas o organizador ou participantes confirmados podem acessar o chat.",
    ),
)


@router.get(
    "",
    response_model=list[MessageRead],
    summary="Histórico de mensagens da partida",
    description="Lista o histórico de mensagens da partida, em ordem cronológica, paginado. "
    "Acessível apenas ao organizador ou a participantes confirmados.",
    responses=error_responses(*AUTH_ERRORS, *_CHAT_ACCESS_ERRORS),
)
def read_messages(
    match_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, gt=0, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[MessageRead]:
    return list_messages(session, match_id, current_user, skip=skip, limit=limit)


@router.post(
    "",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensagem na partida",
    description="Envia uma nova mensagem no chat da partida, com timestamp gerado pelo "
    "servidor. Acessível apenas ao organizador ou a participantes confirmados.",
    responses=error_responses(*AUTH_ERRORS, *_CHAT_ACCESS_ERRORS),
)
def send_message(
    match_id: str,
    payload: MessageCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageRead:
    message = create_message(session, match_id, payload, current_user, background_tasks)
    background_tasks.add_task(manager.broadcast, match_id, message)
    return message


@ws_router.websocket("/ws")
async def match_chat_ws(
    websocket: WebSocket,
    match_id: str,
    token: str,
    session: Session = Depends(get_session),
) -> None:
    """Chat em tempo real da partida, complementar ao REST acima (que continua funcionando
    sem mudança). Autenticação via `token` na query string — o front (Expo) não tem controle
    fino de headers na conexão WebSocket nativa. Mensagens enviadas via REST (`send_message`
    acima) também chegam aqui via broadcast, então clientes conectados recebem tanto as
    mensagens enviadas pelo WS quanto pelo REST.
    """
    payload = decode_access_token(token)
    user = session.get(User, payload["sub"]) if payload else None
    if user is None:
        await websocket.close(code=WS_UNAUTHORIZED)
        return

    try:
        ensure_chat_access(session, match_id, user)
    except HTTPException as exc:
        code = WS_NOT_FOUND if exc.status_code == status.HTTP_404_NOT_FOUND else WS_FORBIDDEN
        await websocket.close(code=code)
        return

    await manager.connect(match_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            try:
                message_payload = MessageCreate.model_validate(data)
            except ValidationError:
                continue

            background_tasks = BackgroundTasks()
            message = create_message(session, match_id, message_payload, user, background_tasks)
            await manager.broadcast(match_id, message)
            await background_tasks()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(match_id, websocket)
