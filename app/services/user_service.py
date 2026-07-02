from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.models.enums import ParticipationStatus
from app.models.participant import Participant
from app.models.rating import Rating
from app.models.user import User
from app.schemas.user import MyProfileRead, PublicProfileRead, UserUpdate


def get_average_rating(session: Session, user_id: str) -> float | None:
    average = session.exec(
        select(func.avg(Rating.overall)).where(Rating.rated_user_id == user_id)
    ).one()
    return round(average, 1) if average is not None else None


def get_matches_played(session: Session, user_id: str) -> int:
    return session.exec(
        select(func.count()).where(
            Participant.user_id == user_id,
            Participant.status == ParticipationStatus.CONFIRMED,
        )
    ).one()


def build_public_profile(session: Session, user: User) -> PublicProfileRead:
    return PublicProfileRead(
        **user.model_dump(),
        average_rating=get_average_rating(session, user.id),
        matches_played=get_matches_played(session, user.id),
    )


def build_my_profile(session: Session, user: User) -> MyProfileRead:
    return MyProfileRead(
        **user.model_dump(),
        average_rating=get_average_rating(session, user.id),
        matches_played=get_matches_played(session, user.id),
    )


def get_public_profile(session: Session, user_id: str) -> PublicProfileRead:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "Usuário não encontrado."},
        )
    return build_public_profile(session, user)


def update_my_profile(session: Session, user: User, payload: UserUpdate) -> MyProfileRead:
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)
    session.add(user)
    session.commit()
    session.refresh(user)
    return build_my_profile(session, user)
