from fastapi import APIRouter, Header, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import get_settings

router = APIRouter(tags=["observability"])


@router.get(
    "/metrics",
    summary="Métricas Prometheus",
    description="Expõe contadores/histogramas de requisições HTTP no formato de exposição do "
    "Prometheus. Protegido por `X-Metrics-Token` se `METRICS_TOKEN` estiver configurado no "
    "ambiente; aberto (sem token) em dev/CI.",
    include_in_schema=False,
)
def metrics(x_metrics_token: str | None = Header(default=None)) -> Response:
    settings = get_settings()
    if settings.metrics_token and x_metrics_token != settings.metrics_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
