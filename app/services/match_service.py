from datetime import date

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.models.enums import ExperienceLevel, ParticipationStatus, Sport
from app.models.match import Match
from app.models.participant import Participant
from app.schemas.match import MatchDetailRead, MatchRead, ParticipantRead
from app.services.user_service import build_public_profile


def get_confirmed_count(session: Session, match_id: str) -> int:
    return session.exec(
        select(func.count()).where(
            Participant.match_id == match_id,
            Participant.status == ParticipationStatus.CONFIRMED,
        )
    ).one()


def build_match_read(session: Session, match: Match) -> MatchRead:
    confirmed_count = get_confirmed_count(session, match.id)
    return MatchRead(
        **match.model_dump(),
        confirmed_count=confirmed_count,
        available_slots=max(match.max_participants - confirmed_count, 0),
    )


def build_match_detail(session: Session, match: Match) -> MatchDetailRead:
    confirmed_count = get_confirmed_count(session, match.id)
    participants = [
        ParticipantRead(
            user=build_public_profile(session, participant.user),
            status=participant.status,
        )
        for participant in match.participants
    ]
    return MatchDetailRead(
        **match.model_dump(),
        confirmed_count=confirmed_count,
        available_slots=max(match.max_participants - confirmed_count, 0),
        organizer=build_public_profile(session, match.organizer),
        participants=participants,
    )


def list_matches(
    session: Session,
    sport: Sport | None = None,
    match_date: date | None = None,
    location: str | None = None,
    level: ExperienceLevel | None = None,
    has_open_slots: bool = False,
) -> list[MatchRead]:
    query = select(Match)
    if sport is not None:
        query = query.where(Match.sport == sport)
    if match_date is not None:
        query = query.where(Match.date == match_date)
    if location is not None:
        query = query.where(func.lower(Match.location).contains(location.lower()))
    if level is not None:
        query = query.where(Match.level == level)

    matches = session.exec(query).all()
    results = [build_match_read(session, match) for match in matches]

    if has_open_slots:
        results = [match for match in results if match.available_slots > 0]

    return results


def get_match_detail(session: Session, match_id: str) -> MatchDetailRead:
    match = session.get(Match, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MATCH_NOT_FOUND", "message": "Partida não encontrada."},
        )
    return build_match_detail(session, match)
