from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.models.enums import ExperienceLevel, Sport
from app.schemas.match import MatchDetailRead, MatchRead
from app.services.match_service import get_match_detail, list_matches

router = APIRouter(prefix="/matches", tags=["matches"])


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
