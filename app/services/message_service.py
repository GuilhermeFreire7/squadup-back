from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.enums import ParticipationStatus
from app.models.match import Match
from app.models.message import Message
from app.models.participant import Participant
from app.models.user import User
from app.schemas.message import MessageCreate, MessageRead
from app.services.user_service import build_public_profile

MAX_MESSAGES_PAGE_SIZE = 100


def _get_match_or_404(session: Session, match_id: str) -> Match:
    match = session.get(Match, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MATCH_NOT_FOUND", "message": "Partida não encontrada."},
        )
    return match


def _ensure_can_access_chat(session: Session, match: Match, user: User) -> None:
    if match.organizer_id == user.id:
        return
    participant = session.get(Participant, (match.id, user.id))
    if participant is not None and participant.status == ParticipationStatus.CONFIRMED:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "NOT_MATCH_PARTICIPANT",
            "message": "Apenas o organizador ou participantes confirmados podem acessar o chat.",
        },
    )


def build_message_read(session: Session, message: Message) -> MessageRead:
    return MessageRead(
        id=message.id,
        match_id=message.match_id,
        sender=build_public_profile(session, message.sender),
        text=message.text,
        created_at=message.created_at,
        type=message.type,
    )


def list_messages(
    session: Session,
    match_id: str,
    user: User,
    skip: int = 0,
    limit: int = 50,
) -> list[MessageRead]:
    match = _get_match_or_404(session, match_id)
    _ensure_can_access_chat(session, match, user)

    limit = min(limit, MAX_MESSAGES_PAGE_SIZE)
    messages = session.exec(
        select(Message)
        .where(Message.match_id == match_id)
        .order_by(Message.created_at)  # type: ignore[arg-type]
        .offset(skip)
        .limit(limit)
    ).all()

    return [build_message_read(session, message) for message in messages]


def create_message(
    session: Session, match_id: str, payload: MessageCreate, user: User
) -> MessageRead:
    match = _get_match_or_404(session, match_id)
    _ensure_can_access_chat(session, match, user)

    message = Message(match_id=match_id, sender_id=user.id, text=payload.text)
    session.add(message)
    session.commit()
    session.refresh(message)
    return build_message_read(session, message)
