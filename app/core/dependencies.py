from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.database import get_session
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# Mesma origem do token, mas sem 401 automático quando ele não vem: para rotas públicas que
# só personalizam a resposta quando há um usuário autenticado.
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _user_from_token(token: str, session: Session) -> User | None:
    payload = decode_access_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    return session.get(User, user_id)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    user = _user_from_token(token, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Não foi possível validar as credenciais.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_current_user(
    token: str | None = Depends(optional_oauth2_scheme),
    session: Session = Depends(get_session),
) -> User | None:
    """Usuário do token, se houver um válido; None caso contrário (a rota continua pública).

    Token ausente, inválido ou expirado não gera 401: a requisição segue como anônima.
    """
    if token is None:
        return None
    return _user_from_token(token, session)


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ADMIN_ONLY",
                "message": "Apenas administradores podem acessar este recurso.",
            },
        )
    return current_user
