from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.enums import ExperienceLevel, Sport
from app.models.user import User
from app.schemas.match import MatchCreate, MatchDetailRead, MatchRead
from app.services.match_service import (
    approve_participant,
    create_match,
    get_match_detail,
    join_match,
    leave_match,
    list_matches,
)

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post(
    "",
    response_model=MatchRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar partida",
    description="Cria uma nova partida com o usuário autenticado como organizador.",
)
def create_new_match(
    payload: MatchCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MatchRead:
    return create_match(session, payload, current_user)


@router.get(
    "",
    response_model=list[MatchRead],
    summary="Listar partidas",
    description="Lista partidas com filtros opcionais por esporte, data, local, nível e "
    "disponibilidade de vagas.",
)
def read_matches(
    sport: Sport | None = Query(default=None, examples=[Sport.FOOTBALL]),
    match_date: date | None = Query(default=None, alias="date", examples=["2026-05-25"]),
    location: str | None = Query(default=None, examples=["Botafogo"]),
    level: ExperienceLevel | None = Query(default=None, examples=[ExperienceLevel.INTERMEDIATE]),
    has_open_slots: bool = Query(default=False, examples=[True]),
    session: Session = Depends(get_session),
) -> list[MatchRead]:
    return list_matches(
        session,
        sport=sport,
        match_date=match_date,
        location=location,
        level=level,
        has_open_slots=has_open_slots,
    )


@router.get(
    "/{match_id}",
    response_model=MatchDetailRead,
    summary="Detalhes da partida",
    description="Retorna os detalhes de uma partida, com organizador e participantes "
    "expandidos.",
)
def read_match_detail(
    match_id: str,
    session: Session = Depends(get_session),
) -> MatchDetailRead:
    return get_match_detail(session, match_id)


@router.post(
    "/{match_id}/join",
    response_model=MatchRead,
    summary="Participar de partida",
    description="Cria uma participação para o usuário autenticado: confirmada de imediato, "
    "ou pendente se a partida exigir aprovação do organizador.",
)
def join_match_route(
    match_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MatchRead:
    return join_match(session, match_id, current_user)


@router.post(
    "/{match_id}/leave",
    response_model=MatchRead,
    summary="Cancelar participação",
    description="Cancela a participação do usuário autenticado na partida.",
)
def leave_match_route(
    match_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MatchRead:
    return leave_match(session, match_id, current_user)


@router.post(
    "/{match_id}/participants/{user_id}/approve",
    response_model=MatchRead,
    summary="Aprovar solicitação de participação",
    description="Confirma a participação pendente de um usuário. Apenas o organizador da "
    "partida pode aprovar.",
)
def approve_participant_route(
    match_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MatchRead:
    return approve_participant(session, match_id, user_id, current_user)
