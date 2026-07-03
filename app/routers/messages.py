from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.message import MessageCreate, MessageRead
from app.services.message_service import create_message, list_messages

router = APIRouter(prefix="/matches/{match_id}/messages", tags=["messages"])


@router.get(
    "",
    response_model=list[MessageRead],
    summary="Histórico de mensagens da partida",
    description="Lista o histórico de mensagens da partida, em ordem cronológica, paginado. "
    "Acessível apenas ao organizador ou a participantes confirmados.",
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
)
def send_message(
    match_id: str,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageRead:
    return create_message(session, match_id, payload, current_user)
