from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.errors import AUTH_ERRORS, error_responses
from app.schemas.rating import RatingCreate, RatingRead
from app.services.rating_service import create_rating, list_ratings_received

router = APIRouter(tags=["ratings"])


@router.post(
    "/matches/{match_id}/ratings/{user_id}",
    response_model=RatingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Avaliar participante da partida",
    description="Registra uma avaliação de outro usuário após uma partida encerrada. Só é "
    "permitido se ambos os usuários estavam confirmados na partida e ainda não houver "
    "avaliação prévia do mesmo par nesta partida.",
    responses=error_responses(
        *AUTH_ERRORS,
        (404, "MATCH_NOT_FOUND", "Partida não encontrada."),
        (400, "CANNOT_RATE_SELF", "Você não pode avaliar a si mesmo."),
        (404, "USER_NOT_FOUND", "Usuário não encontrado."),
        (400, "MATCH_NOT_CLOSED", "Só é possível avaliar depois que a partida for encerrada."),
        (
            403,
            "NOT_MATCH_PARTICIPANT",
            "Você precisa ter participado desta partida para avaliar.",
        ),
        (400, "RATED_USER_NOT_PARTICIPANT", "Este usuário não participou desta partida."),
        (400, "ALREADY_RATED", "Você já avaliou este usuário nesta partida."),
    ),
)
def rate_participant(
    match_id: str,
    user_id: str,
    payload: RatingCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RatingRead:
    return create_rating(session, match_id, user_id, payload, current_user)


@router.get(
    "/users/{user_id}/ratings",
    response_model=list[RatingRead],
    summary="Avaliações recebidas por um usuário",
    description="Lista as avaliações recebidas por um usuário, mais recentes primeiro.",
    responses=error_responses(
        (404, "USER_NOT_FOUND", "Usuário não encontrado."),
    ),
)
def read_user_ratings(
    user_id: str,
    session: Session = Depends(get_session),
) -> list[RatingRead]:
    return list_ratings_received(session, user_id)
