from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import authenticate_user, register_user

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
