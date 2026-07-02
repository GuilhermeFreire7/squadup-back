from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Healthcheck da API",
    description=(
        "Retorna o status do serviço e o ambiente atual. "
        "Usado para monitoramento e checagem de disponibilidade."
    ),
)
def healthcheck() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", environment=settings.environment)
