from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.errors import AUTH_ERRORS, error_responses
from app.schemas.user import UserRead
from app.services.auth_service import (
    authenticate_user,
    refresh_tokens,
    register_user,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo usuário",
    description="Cria um novo usuário com senha criptografada.",
    responses=error_responses(
        (409, "EMAIL_ALREADY_REGISTERED", "Este e-mail já está cadastrado."),
    ),
)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> User:
    return register_user(session, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autenticar usuário",
    description="Valida e-mail e senha, retornando um token JWT de acesso.",
    responses=error_responses(
        (401, "INVALID_CREDENTIALS", "E-mail ou senha inválidos."),
    ),
)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    return authenticate_user(session, payload)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Usuário autenticado",
    description="Retorna os dados do usuário associado ao token JWT informado.",
    responses=error_responses(*AUTH_ERRORS),
)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar sessão",
    description="Troca um refresh token válido por um novo par de access/refresh token "
    "(rotação: o refresh token usado é invalidado).",
    responses=error_responses(
        (401, "INVALID_REFRESH_TOKEN", "Refresh token inválido, expirado ou já utilizado."),
    ),
)
def refresh(payload: RefreshRequest, session: Session = Depends(get_session)) -> TokenResponse:
    return refresh_tokens(session, payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Encerrar sessão",
    description="Revoga o refresh token informado, impedindo seu uso futuro.",
    responses=error_responses(
        (401, "INVALID_REFRESH_TOKEN", "Refresh token inválido, expirado ou já utilizado."),
    ),
)
def logout(payload: RefreshRequest, session: Session = Depends(get_session)) -> None:
    revoke_refresh_token(session, payload.refresh_token)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Encerrar todas as sessões",
    description="Revoga todos os refresh tokens ativos do usuário autenticado, encerrando "
    "todas as sessões (ex.: em caso de suspeita de dispositivo comprometido).",
    responses=error_responses(*AUTH_ERRORS),
)
def logout_all(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    revoke_all_refresh_tokens(session, current_user.id)
