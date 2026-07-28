from sqlmodel import Session, col, select

from app.models.push_token import PushToken


def register_push_token(session: Session, user_id: str, token: str) -> None:
    """Registra o Expo Push Token do dispositivo. Idempotente por `token` (unique).

    Se o mesmo token já pertence a outro usuário (ex.: dispositivo compartilhado, login de
    uma conta diferente), o registro é realocado para o usuário atual em vez de duplicar a
    linha ou falhar.
    """
    existing = session.exec(select(PushToken).where(PushToken.token == token)).first()
    if existing is not None:
        existing.user_id = user_id
        session.add(existing)
        session.commit()
        return

    session.add(PushToken(user_id=user_id, token=token))
    session.commit()


def revoke_all_push_tokens(session: Session, user_id: str) -> int:
    """Remove todos os push tokens de um usuário. Retorna quantos foram removidos."""
    tokens = session.exec(select(PushToken).where(PushToken.user_id == user_id)).all()
    for token in tokens:
        session.delete(token)
    session.commit()
    return len(tokens)


def get_push_tokens_for_users(session: Session, user_ids: list[str]) -> list[str]:
    if not user_ids:
        return []
    return list(
        session.exec(select(PushToken.token).where(col(PushToken.user_id).in_(user_ids))).all()
    )
