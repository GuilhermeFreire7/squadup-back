from datetime import date

from sqlmodel import Session, col, func, or_, select

from app.models.enums import ParticipationStatus
from app.models.match import Match
from app.models.participant import Participant
from app.models.user import User
from app.schemas.match import MyMatchRead
from app.services.match_service import FINISHED_STATUSES, build_match_read, local_today


def _is_past(match: Match, today: date) -> bool:
    """Encerrada, cancelada ou com data já passada (mesmo que ninguém a tenha encerrado)."""
    return match.status in FINISHED_STATUSES or match.date < today


def _sort_key(match: Match, today: date) -> tuple[int, int, int]:
    """Próximas primeiro, da mais perto para a mais distante; depois as anteriores, da mais
    recente para a mais antiga."""
    day = match.date.toordinal()
    seconds = match.time.hour * 3600 + match.time.minute * 60 + match.time.second
    if _is_past(match, today):
        return (1, -day, -seconds)
    return (0, day, seconds)


def _pending_requests_by_match(session: Session, match_ids: list[str]) -> dict[str, int]:
    if not match_ids:
        return {}
    rows = session.exec(
        select(Participant.match_id, func.count())
        .where(
            col(Participant.match_id).in_(match_ids),
            Participant.status == ParticipationStatus.PENDING,
        )
        .group_by(col(Participant.match_id))
    ).all()
    return {match_id: count for match_id, count in rows}


def list_my_matches(session: Session, user: User, today: date | None = None) -> list[MyMatchRead]:
    """Partidas que o usuário organiza ou das quais participa (confirmado ou aguardando
    aprovação). Participações canceladas ficam de fora."""
    today = today or local_today()

    my_participations = {
        participant.match_id: participant.status
        for participant in session.exec(
            select(Participant).where(
                Participant.user_id == user.id,
                Participant.status != ParticipationStatus.CANCELLED,
            )
        ).all()
    }
    matches = session.exec(
        select(Match).where(
            or_(
                Match.organizer_id == user.id,
                col(Match.id).in_(list(my_participations)),
            )
        )
    ).all()

    organized_ids = [match.id for match in matches if match.organizer_id == user.id]
    pending_requests = _pending_requests_by_match(session, organized_ids)

    return [
        MyMatchRead(
            **build_match_read(session, match).model_dump(),
            is_organizer=match.organizer_id == user.id,
            my_status=my_participations.get(match.id),
            pending_requests=pending_requests.get(match.id, 0),
            is_past=_is_past(match, today),
        )
        for match in sorted(matches, key=lambda match: _sort_key(match, today))
    ]
