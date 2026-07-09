from datetime import timedelta

from fastapi import HTTPException, status
from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    utc_now_naive,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

INVALID_REFRESH_TOKEN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={
        "code": "INVALID_REFRESH_TOKEN",
        "message": "Refresh token inválido, expirado ou já utilizado.",
    },
)


def register_user(session: Session, payload: RegisterRequest) -> User:
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EMAIL_ALREADY_REGISTERED",
                "message": "Este e-mail já está cadastrado.",
            },
        )

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        age=payload.age,
        location=payload.location,
        bio=payload.bio,
        favorite_sports=payload.favorite_sports,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _issue_token_pair(session: Session, user: User) -> TokenResponse:
    settings = get_settings()
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token()
    expires_at = utc_now_naive() + timedelta(days=settings.refresh_token_expire_days)

    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
        )
    )
    session.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def authenticate_user(session: Session, payload: LoginRequest) -> TokenResponse:
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "INVALID_CREDENTIALS", "message": "E-mail ou senha inválidos."},
    )

    user = session.exec(select(User).where(User.email == payload.email)).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials

    return _issue_token_pair(session, user)


def _get_valid_refresh_token(session: Session, refresh_token: str) -> RefreshToken:
    token_hash = hash_refresh_token(refresh_token)
    stored = session.exec(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if stored is None or stored.revoked or stored.expires_at < utc_now_naive():
        raise INVALID_REFRESH_TOKEN
    return stored


def refresh_tokens(session: Session, refresh_token: str) -> TokenResponse:
    stored = _get_valid_refresh_token(session, refresh_token)

    user = session.get(User, stored.user_id)
    if user is None:
        raise INVALID_REFRESH_TOKEN

    stored.revoked = True
    session.add(stored)
    session.commit()

    return _issue_token_pair(session, user)


def revoke_refresh_token(session: Session, refresh_token: str) -> None:
    stored = _get_valid_refresh_token(session, refresh_token)
    stored.revoked = True
    session.add(stored)
    session.commit()


def purge_expired_refresh_tokens(session: Session) -> int:
    """Remove refresh tokens expirados ou revogados. Retorna quantas linhas foram removidas."""
    stale_tokens = session.exec(
        select(RefreshToken).where(
            col(RefreshToken.revoked).is_(True) | (RefreshToken.expires_at < utc_now_naive())
        )
    ).all()
    for token in stale_tokens:
        session.delete(token)
    session.commit()
    return len(stale_tokens)
