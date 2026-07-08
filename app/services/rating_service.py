from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.enums import MatchStatus, ParticipationStatus
from app.models.match import Match
from app.models.participant import Participant
from app.models.rating import Rating
from app.models.user import User
from app.schemas.match import MatchRef
from app.schemas.rating import RatingCreate, RatingRead
from app.services.user_service import build_public_profile


def _get_match_or_404(session: Session, match_id: str) -> Match:
    match = session.get(Match, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MATCH_NOT_FOUND", "message": "Partida não encontrada."},
        )
    return match


def _get_user_or_404(session: Session, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "Usuário não encontrado."},
        )
    return user


def _ensure_was_confirmed(
    session: Session,
    match_id: str,
    user_id: str,
    *,
    status_code: int,
    code: str,
    message: str,
) -> None:
    participant = session.get(Participant, (match_id, user_id))
    if participant is None or participant.status != ParticipationStatus.CONFIRMED:
        raise HTTPException(
            status_code=status_code,
            detail={"code": code, "message": message},
        )


def build_rating_read(session: Session, rating: Rating) -> RatingRead:
    return RatingRead(
        id=rating.id,
        match=MatchRef.model_validate(rating.match),
        rated_user=build_public_profile(session, rating.rated_user),
        rater=build_public_profile(session, rating.rater_user),
        punctuality=rating.punctuality,
        respect=rating.respect,
        behavior=rating.behavior,
        presence=rating.presence,
        overall=rating.overall,
        comment=rating.comment,
        created_at=rating.created_at,
    )


def create_rating(
    session: Session,
    match_id: str,
    rated_user_id: str,
    payload: RatingCreate,
    rater: User,
) -> RatingRead:
    match = _get_match_or_404(session, match_id)

    if rated_user_id == rater.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CANNOT_RATE_SELF", "message": "Você não pode avaliar a si mesmo."},
        )

    _get_user_or_404(session, rated_user_id)

    if match.status != MatchStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MATCH_NOT_CLOSED",
                "message": "Só é possível avaliar depois que a partida for encerrada.",
            },
        )

    _ensure_was_confirmed(
        session,
        match_id,
        rater.id,
        status_code=status.HTTP_403_FORBIDDEN,
        code="NOT_MATCH_PARTICIPANT",
        message="Você precisa ter participado desta partida para avaliar.",
    )
    _ensure_was_confirmed(
        session,
        match_id,
        rated_user_id,
        status_code=status.HTTP_400_BAD_REQUEST,
        code="RATED_USER_NOT_PARTICIPANT",
        message="Este usuário não participou desta partida.",
    )

    existing = session.exec(
        select(Rating).where(
            Rating.match_id == match_id,
            Rating.rater_user_id == rater.id,
            Rating.rated_user_id == rated_user_id,
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ALREADY_RATED",
                "message": "Você já avaliou este usuário nesta partida.",
            },
        )

    rating = Rating(
        rated_user_id=rated_user_id,
        rater_user_id=rater.id,
        match_id=match_id,
        **payload.model_dump(),
    )
    session.add(rating)
    session.commit()
    session.refresh(rating)
    return build_rating_read(session, rating)


def list_ratings_received(session: Session, user_id: str) -> list[RatingRead]:
    _get_user_or_404(session, user_id)

    ratings = session.exec(
        select(Rating)
        .where(Rating.rated_user_id == user_id)
        .order_by(Rating.created_at.desc())  # type: ignore[attr-defined]
    ).all()

    return [build_rating_read(session, rating) for rating in ratings]
