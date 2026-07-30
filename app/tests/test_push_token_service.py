from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.push_token import PushToken
from app.models.user import User
from app.services.push_token_service import (
    get_push_tokens_for_users,
    register_push_token,
    revoke_all_push_tokens,
    revoke_push_token_by_device,
)


def _make_user(session: Session, id_: str) -> User:
    user = User(
        id=id_,
        name=f"User {id_}",
        email=f"{id_}@example.com",
        hashed_password=hash_password("senha-super-secreta"),
        age=25,
        location="Rio de Janeiro, RJ",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_register_push_token_creates_row(session: Session) -> None:
    user = _make_user(session, "u1")

    register_push_token(session, user.id, "token-1")

    rows = session.exec(select(PushToken)).all()
    assert len(rows) == 1
    assert rows[0].user_id == user.id
    assert rows[0].token == "token-1"


def test_register_push_token_is_idempotent_for_same_token(session: Session) -> None:
    user = _make_user(session, "u1")

    register_push_token(session, user.id, "token-1")
    register_push_token(session, user.id, "token-1")

    rows = session.exec(select(PushToken)).all()
    assert len(rows) == 1


def test_register_push_token_reassigns_owner_on_shared_device(session: Session) -> None:
    first_user = _make_user(session, "u1")
    second_user = _make_user(session, "u2")

    register_push_token(session, first_user.id, "shared-token")
    register_push_token(session, second_user.id, "shared-token")

    rows = session.exec(select(PushToken)).all()
    assert len(rows) == 1
    assert rows[0].user_id == second_user.id


def test_revoke_all_push_tokens_removes_every_token_for_user(session: Session) -> None:
    user = _make_user(session, "u1")
    other = _make_user(session, "u2")
    register_push_token(session, user.id, "token-1")
    register_push_token(session, user.id, "token-2")
    register_push_token(session, other.id, "token-3")

    removed = revoke_all_push_tokens(session, user.id)

    assert removed == 2
    remaining = session.exec(select(PushToken)).all()
    assert [t.token for t in remaining] == ["token-3"]


def test_get_push_tokens_for_users_returns_tokens_for_given_users_only(session: Session) -> None:
    user = _make_user(session, "u1")
    other = _make_user(session, "u2")
    register_push_token(session, user.id, "token-1")
    register_push_token(session, other.id, "token-2")

    tokens = get_push_tokens_for_users(session, [user.id])

    assert tokens == ["token-1"]


def test_get_push_tokens_for_users_returns_empty_for_empty_input(session: Session) -> None:
    assert get_push_tokens_for_users(session, []) == []


def test_register_push_token_stores_device_id(session: Session) -> None:
    user = _make_user(session, "u1")

    register_push_token(session, user.id, "token-1", device_id="device-a")

    rows = session.exec(select(PushToken)).all()
    assert rows[0].device_id == "device-a"


def test_revoke_push_token_by_device_removes_only_matching_device(session: Session) -> None:
    user = _make_user(session, "u1")
    register_push_token(session, user.id, "token-a", device_id="device-a")
    register_push_token(session, user.id, "token-b", device_id="device-b")

    removed = revoke_push_token_by_device(session, user.id, "device-a")

    assert removed == 1
    remaining = session.exec(select(PushToken)).all()
    assert [t.token for t in remaining] == ["token-b"]


def test_revoke_push_token_by_device_does_not_affect_other_users(session: Session) -> None:
    user = _make_user(session, "u1")
    other = _make_user(session, "u2")
    register_push_token(session, user.id, "token-a", device_id="shared-device-id")
    register_push_token(session, other.id, "token-b", device_id="shared-device-id")

    removed = revoke_push_token_by_device(session, user.id, "shared-device-id")

    assert removed == 1
    remaining = session.exec(select(PushToken)).all()
    assert [t.token for t in remaining] == ["token-b"]
