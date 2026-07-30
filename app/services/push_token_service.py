from sqlmodel import Session, col, select

from app.models.push_token import PushToken


def register_push_token(
    session: Session, user_id: str, token: str, device_id: str | None = None
) -> None:
    """Registra o Expo Push Token do dispositivo. Idempotente por `token` (unique).

    Se o mesmo token já pertence a outro usuário (ex.: dispositivo compartilhado, login de
    uma conta diferente), o registro é realocado para o usuário atual em vez de duplicar a
    linha ou falhar. `device_id`, se informado, é gravado/atualizado junto — é o que permite
    revogar só este token num logout de um único dispositivo (`revoke_push_token_by_device`).
    """
    existing = session.exec(select(PushToken).where(PushToken.token == token)).first()
    if existing is not None:
        existing.user_id = user_id
        existing.device_id = device_id
        session.add(existing)
        session.commit()
        return

    session.add(PushToken(user_id=user_id, token=token, device_id=device_id))
    session.commit()


def revoke_all_push_tokens(session: Session, user_id: str) -> int:
    """Remove todos os push tokens de um usuário. Retorna quantos foram removidos."""
    tokens = session.exec(select(PushToken).where(PushToken.user_id == user_id)).all()
    for token in tokens:
        session.delete(token)
    session.commit()
    return len(tokens)


def revoke_push_token_by_device(session: Session, user_id: str, device_id: str) -> int:
    """Remove só o(s) push token(s) do usuário associados a este `device_id`.

    Usado por `POST /auth/logout` (single-device) quando o cliente informa `device_id`: ao
    contrário de `revoke_all_push_tokens` (logout-all), não afeta push tokens de outras
    sessões/dispositivos ativos do mesmo usuário. Retorna quantos foram removidos.
    """
    tokens = session.exec(
        select(PushToken).where(
            PushToken.user_id == user_id,
            PushToken.device_id == device_id,
        )
    ).all()
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
