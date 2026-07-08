from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.errors import AUTH_ERRORS, error_responses
from app.schemas.user import MyProfileRead, PublicProfileRead, UserUpdate
from app.services.user_service import build_my_profile, get_public_profile, update_my_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=MyProfileRead,
    summary="Meu perfil",
    description="Retorna o perfil completo do usuário autenticado, com métricas derivadas.",
    responses=error_responses(*AUTH_ERRORS),
)
def read_my_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MyProfileRead:
    return build_my_profile(session, current_user)


@router.patch(
    "/me",
    response_model=MyProfileRead,
    summary="Editar meu perfil",
    description="Atualiza campos do perfil do usuário autenticado.",
    responses=error_responses(*AUTH_ERRORS),
)
def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MyProfileRead:
    return update_my_profile(session, current_user, payload)


@router.get(
    "/{user_id}",
    response_model=PublicProfileRead,
    summary="Perfil público",
    description="Retorna o perfil público de um usuário, com métricas derivadas de avaliações e "
    "partidas.",
    responses=error_responses(
        (404, "USER_NOT_FOUND", "Usuário não encontrado."),
    ),
)
def read_public_profile(
    user_id: str,
    session: Session = Depends(get_session),
) -> PublicProfileRead:
    return get_public_profile(session, user_id)
