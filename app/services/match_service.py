from datetime import date

from fastapi import BackgroundTasks, HTTPException, status
from sqlmodel import Session, func, select

from app.models.enums import ExperienceLevel, MatchStatus, MessageType, ParticipationStatus, Sport
from app.models.match import Match
from app.models.message import Message
from app.models.participant import Participant
from app.models.user import User
from app.schemas.match import MatchCreate, MatchDetailRead, MatchRead, ParticipantRead
from app.services.geo import haversine_km
from app.services.notification_service import send_push
from app.services.push_token_service import get_push_tokens_for_users
from app.services.user_service import build_public_profile

MATCH_CREATED_SYSTEM_MESSAGE = "Partida criada. Bem-vindos!"
DEFAULT_SEARCH_RADIUS_KM = 20.0


def get_confirmed_count(session: Session, match_id: str) -> int:
    return session.exec(
        select(func.count()).where(
            Participant.match_id == match_id,
            Participant.status == ParticipationStatus.CONFIRMED,
        )
    ).one()


def _confirmed_participant_ids(session: Session, match_id: str) -> list[str]:
    return list(
        session.exec(
            select(Participant.user_id).where(
                Participant.match_id == match_id,
                Participant.status == ParticipationStatus.CONFIRMED,
            )
        ).all()
    )


def build_match_read(session: Session, match: Match, distance_km: float | None = None) -> MatchRead:
    confirmed_count = get_confirmed_count(session, match.id)
    return MatchRead(
        **match.model_dump(),
        confirmed_count=confirmed_count,
        available_slots=max(match.max_participants - confirmed_count, 0),
        distance_km=distance_km,
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


def _filter_matches_by_radius(
    matches: list[Match], lat: float, lng: float, radius_km: float
) -> tuple[list[Match], dict[str, float]]:
    """Mantém só as partidas com coordenadas dentro do raio, junto da distância de cada uma.

    Sem PostGIS: distância calculada em Python via Haversine, suficiente para o volume
    esperado do MVP (dezenas/centenas de partidas), sem escanear a tabela via SQL geográfico.
    """
    matches_in_radius = []
    distances: dict[str, float] = {}
    for match in matches:
        if match.latitude is None or match.longitude is None:
            continue
        distance = haversine_km(lat, lng, match.latitude, match.longitude)
        if distance <= radius_km:
            distances[match.id] = distance
            matches_in_radius.append(match)
    return matches_in_radius, distances


def list_matches(
    session: Session,
    sport: Sport | None = None,
    match_date: date | None = None,
    location: str | None = None,
    level: ExperienceLevel | None = None,
    has_open_slots: bool = False,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float = DEFAULT_SEARCH_RADIUS_KM,
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

    matches = list(session.exec(query).all())

    # Filtro/ordenação por distância só entra em jogo quando lat/lng são informados juntos
    # (radius_km sozinho não tem efeito).
    geo_search = lat is not None and lng is not None
    distances: dict[str, float] = {}
    if lat is not None and lng is not None:
        matches, distances = _filter_matches_by_radius(matches, lat, lng, radius_km)

    results = [
        build_match_read(session, match, distance_km=distances.get(match.id)) for match in matches
    ]

    if has_open_slots:
        results = [match for match in results if match.available_slots > 0]

    if geo_search:
        results.sort(key=lambda m: m.distance_km if m.distance_km is not None else float("inf"))

    return results


def create_match(session: Session, payload: MatchCreate, organizer: User) -> MatchRead:
    match = Match(**payload.model_dump(), organizer_id=organizer.id)
    session.add(match)
    session.commit()
    session.refresh(match)

    session.add(
        Message(
            match_id=match.id,
            sender_id=organizer.id,
            text=MATCH_CREATED_SYSTEM_MESSAGE,
            type=MessageType.SYSTEM,
        )
    )
    session.commit()

    return build_match_read(session, match)


def get_match_detail(session: Session, match_id: str) -> MatchDetailRead:
    match = session.get(Match, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MATCH_NOT_FOUND", "message": "Partida não encontrada."},
        )
    return build_match_detail(session, match)


def _get_match_or_404(session: Session, match_id: str) -> Match:
    match = session.get(Match, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MATCH_NOT_FOUND", "message": "Partida não encontrada."},
        )
    return match


def _sync_match_status(session: Session, match: Match) -> None:
    if match.status not in (MatchStatus.OPEN, MatchStatus.FULL):
        return
    confirmed_count = get_confirmed_count(session, match.id)
    is_full = confirmed_count >= match.max_participants
    new_status = MatchStatus.FULL if is_full else MatchStatus.OPEN
    if match.status != new_status:
        match.status = new_status
        session.add(match)
        session.commit()
        session.refresh(match)


def join_match(session: Session, match_id: str, user: User) -> MatchRead:
    match = _get_match_or_404(session, match_id)

    if match.status in (MatchStatus.CLOSED, MatchStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MATCH_NOT_JOINABLE",
                "message": "Esta partida não está mais aceitando participantes.",
            },
        )

    existing = session.get(Participant, (match_id, user.id))
    if existing is not None and existing.status != ParticipationStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ALREADY_PARTICIPATING",
                "message": "Você já participa desta partida.",
            },
        )

    confirmed_count = get_confirmed_count(session, match.id)
    if confirmed_count >= match.max_participants and not match.requires_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MATCH_FULL", "message": "Esta partida não tem mais vagas."},
        )

    new_status = (
        ParticipationStatus.PENDING if match.requires_approval else ParticipationStatus.CONFIRMED
    )

    if existing is not None:
        existing.status = new_status
        session.add(existing)
    else:
        session.add(Participant(match_id=match_id, user_id=user.id, status=new_status))
    session.commit()

    _sync_match_status(session, match)
    return build_match_read(session, match)


def leave_match(session: Session, match_id: str, user: User) -> MatchRead:
    match = _get_match_or_404(session, match_id)

    participant = session.get(Participant, (match_id, user.id))
    if participant is None or participant.status == ParticipationStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NOT_PARTICIPATING",
                "message": "Você não participa desta partida.",
            },
        )

    participant.status = ParticipationStatus.CANCELLED
    session.add(participant)
    session.commit()

    _sync_match_status(session, match)
    return build_match_read(session, match)


def close_match(
    session: Session,
    match_id: str,
    organizer: User,
    background_tasks: BackgroundTasks | None = None,
) -> MatchRead:
    match = _get_match_or_404(session, match_id)

    if match.organizer_id != organizer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "NOT_MATCH_ORGANIZER",
                "message": "Apenas o organizador pode encerrar a partida.",
            },
        )

    if match.status in (MatchStatus.CLOSED, MatchStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MATCH_ALREADY_RESOLVED",
                "message": "Esta partida já foi encerrada ou cancelada.",
            },
        )

    match.status = MatchStatus.CLOSED
    session.add(match)
    session.commit()
    session.refresh(match)

    if background_tasks is not None:
        recipient_ids = [
            user_id
            for user_id in _confirmed_participant_ids(session, match.id)
            if user_id != organizer.id
        ]
        tokens = get_push_tokens_for_users(session, recipient_ids)
        background_tasks.add_task(
            send_push,
            tokens,
            "Partida encerrada",
            f'A partida "{match.title}" foi encerrada pelo organizador.',
            {"type": "match_closed", "matchId": match.id},
        )

    return build_match_read(session, match)


def approve_participant(
    session: Session,
    match_id: str,
    user_id: str,
    organizer: User,
    background_tasks: BackgroundTasks | None = None,
) -> MatchRead:
    match = _get_match_or_404(session, match_id)

    if match.organizer_id != organizer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "NOT_MATCH_ORGANIZER",
                "message": "Apenas o organizador pode aprovar participantes.",
            },
        )

    participant = session.get(Participant, (match_id, user_id))
    if participant is None or participant.status != ParticipationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PENDING_PARTICIPANT_NOT_FOUND",
                "message": "Não há solicitação pendente para este usuário.",
            },
        )

    confirmed_count = get_confirmed_count(session, match.id)
    if confirmed_count >= match.max_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MATCH_FULL", "message": "Esta partida não tem mais vagas."},
        )

    participant.status = ParticipationStatus.CONFIRMED
    session.add(participant)
    session.commit()

    _sync_match_status(session, match)

    if background_tasks is not None:
        tokens = get_push_tokens_for_users(session, [user_id])
        background_tasks.add_task(
            send_push,
            tokens,
            "Participação aprovada",
            f'Sua participação em "{match.title}" foi aprovada!',
            {"type": "participation_approved", "matchId": match.id},
        )

    return build_match_read(session, match)
