from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.report import ReportCreate, ReportRead, ReportUpdate
from app.services.report_service import create_report, list_reports, update_report_status

router = APIRouter(tags=["reports"])


@router.post(
    "/reports",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Denunciar um usuário",
    description="Registra uma denúncia contra outro usuário, opcionalmente associada a uma "
    "partida específica.",
)
def report_user(
    payload: ReportCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ReportRead:
    return create_report(session, payload, current_user)


@router.get(
    "/reports",
    response_model=list[ReportRead],
    summary="Listar denúncias (moderação)",
    description="Lista todas as denúncias registradas, mais recentes primeiro. Requer papel "
    "de administrador.",
)
def read_reports(
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> list[ReportRead]:
    return list_reports(session)


@router.patch(
    "/reports/{report_id}",
    response_model=ReportRead,
    summary="Resolver denúncia (moderação)",
    description="Aplica uma ação de moderação (arquivar, advertir ou banir) a uma denúncia "
    "pendente. Requer papel de administrador.",
)
def resolve_report(
    report_id: str,
    payload: ReportUpdate,
    _: User = Depends(get_current_admin),
    session: Session = Depends(get_session),
) -> ReportRead:
    return update_report_status(session, report_id, payload)
