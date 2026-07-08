from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import (
    authenticate_user,
    refresh_tokens,
    register_user,
    revoke_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo usuário",
    description="Cria um novo usuário com senha criptografada.",
)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> User:
    return register_user(session, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autenticar usuário",
    description="Valida e-mail e senha, retornando um token JWT de acesso.",
)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    return authenticate_user(session, payload)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Usuário autenticado",
    description="Retorna os dados do usuário associado ao token JWT informado.",
)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar sessão",
    description="Troca um refresh token válido por um novo par de access/refresh token "
    "(rotação: o refresh token usado é invalidado).",
)
def refresh(payload: RefreshRequest, session: Session = Depends(get_session)) -> TokenResponse:
    return refresh_tokens(session, payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Encerrar sessão",
    description="Revoga o refresh token informado, impedindo seu uso futuro.",
)
def logout(payload: RefreshRequest, session: Session = Depends(get_session)) -> None:
    revoke_refresh_token(session, payload.refresh_token)
