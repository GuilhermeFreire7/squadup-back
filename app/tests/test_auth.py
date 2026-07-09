from collections.abc import Generator
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, delete, select
from sqlmodel.pool import StaticPool

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import ALGORITHM, create_access_token, hash_refresh_token, utc_now_naive
from app.main import app
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth_service import purge_expired_refresh_tokens

VALID_PAYLOAD = {
    "name": "Ana Souza",
    "email": "ana.souza@example.com",
    "password": "senha-super-secreta",
    "age": 28,
    "location": "São Paulo, SP",
    "favorite_sports": ["football"],
}


def test_register_creates_user(client: TestClient) -> None:
    response = client.post("/auth/register", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == VALID_PAYLOAD["email"]
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    client.post("/auth/register", json=VALID_PAYLOAD)
    response = client.post("/auth/register", json=VALID_PAYLOAD)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_login_returns_token(client: TestClient) -> None:
    client.post("/auth/register", json=VALID_PAYLOAD)

    response = client.post(
        "/auth/login",
        json={"email": VALID_PAYLOAD["email"], "password": VALID_PAYLOAD["password"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_rejects_wrong_password(client: TestClient) -> None:
    client.post("/auth/register", json=VALID_PAYLOAD)

    response = client.post(
        "/auth/login",
        json={"email": VALID_PAYLOAD["email"], "password": "senha-errada"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "ninguem@example.com", "password": "qualquer-coisa"},
    )

    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token(client: TestClient) -> None:
    client.post("/auth/register", json=VALID_PAYLOAD)
    login_response = client.post(
        "/auth/login",
        json={"email": VALID_PAYLOAD["email"], "password": VALID_PAYLOAD["password"]},
    )
    token = login_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == VALID_PAYLOAD["email"]


def test_me_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401


def _login(client: TestClient) -> dict[str, str]:
    client.post("/auth/register", json=VALID_PAYLOAD)
    response = client.post(
        "/auth/login",
        json={"email": VALID_PAYLOAD["email"], "password": VALID_PAYLOAD["password"]},
    )
    return dict(response.json())


def test_refresh_returns_new_token_pair(client: TestClient) -> None:
    tokens = _login(client)

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["refresh_token"] != tokens["refresh_token"]


def test_refresh_rotates_and_invalidates_old_refresh_token(client: TestClient) -> None:
    tokens = _login(client)
    client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_REFRESH_TOKEN"


def test_refresh_rejects_unknown_token(client: TestClient) -> None:
    response = client.post("/auth/refresh", json={"refresh_token": "does-not-exist"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_REFRESH_TOKEN"


def test_refreshed_access_token_grants_access(client: TestClient) -> None:
    tokens = _login(client)

    refresh_response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    new_access_token = refresh_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {new_access_token}"})

    assert response.status_code == 200


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    tokens = _login(client)

    logout_response = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout_response.status_code == 204

    refresh_response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"]["code"] == "INVALID_REFRESH_TOKEN"


def test_logout_rejects_unknown_token(client: TestClient) -> None:
    response = client.post("/auth/logout", json={"refresh_token": "does-not-exist"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_REFRESH_TOKEN"


def test_logout_all_revokes_every_active_refresh_token(client: TestClient) -> None:
    tokens = _login(client)
    second_login = client.post(
        "/auth/login",
        json={"email": VALID_PAYLOAD["email"], "password": VALID_PAYLOAD["password"]},
    ).json()

    response = client.post(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 204

    first_refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    second_refresh = client.post(
        "/auth/refresh", json={"refresh_token": second_login["refresh_token"]}
    )

    assert first_refresh.status_code == 401
    assert second_refresh.status_code == 401


def test_logout_all_rejects_missing_token(client: TestClient) -> None:
    response = client.post("/auth/logout-all")

    assert response.status_code == 401


def test_logout_all_does_not_affect_other_users_tokens(client: TestClient) -> None:
    tokens = _login(client)
    other_payload = {**VALID_PAYLOAD, "email": "other@example.com"}
    client.post("/auth/register", json=other_payload)
    other_tokens = client.post(
        "/auth/login",
        json={"email": other_payload["email"], "password": other_payload["password"]},
    ).json()

    response = client.post(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 204

    other_refresh = client.post(
        "/auth/refresh", json={"refresh_token": other_tokens["refresh_token"]}
    )
    assert other_refresh.status_code == 200


def test_me_rejects_token_without_subject(client: TestClient) -> None:
    settings = get_settings()
    token = jwt.encode({"foo": "bar"}, settings.secret_key, algorithm=ALGORITHM)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_me_rejects_token_for_deleted_user(client: TestClient) -> None:
    token = create_access_token(subject="does-not-exist")

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


@pytest.fixture
def db_client() -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    def get_session_override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as test_client:
        yield test_client, session
    app.dependency_overrides.clear()
    session.close()


def test_refresh_rejects_when_user_no_longer_exists(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    tokens = _login(client)

    user = session.exec(select(User)).one()
    session.exec(delete(User).where(User.id == user.id))  # type: ignore[arg-type]
    session.commit()

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_REFRESH_TOKEN"


def _make_user(session: Session) -> User:
    user = User(
        name="Ana Souza",
        email="ana.souza@example.com",
        hashed_password="hashed",
        age=28,
        location="São Paulo, SP",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_purge_removes_expired_and_revoked_tokens(session: Session) -> None:
    user = _make_user(session)
    expired = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token("expired-token"),
        expires_at=utc_now_naive() - timedelta(days=1),
    )
    revoked = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token("revoked-token"),
        expires_at=utc_now_naive() + timedelta(days=30),
        revoked=True,
    )
    valid = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token("valid-token"),
        expires_at=utc_now_naive() + timedelta(days=30),
    )
    session.add_all([expired, revoked, valid])
    session.commit()

    removed = purge_expired_refresh_tokens(session)

    assert removed == 2
    remaining = session.exec(select(RefreshToken)).all()
    assert len(remaining) == 1
    assert remaining[0].token_hash == hash_refresh_token("valid-token")


def test_purge_is_noop_when_no_stale_tokens(session: Session) -> None:
    removed = purge_expired_refresh_tokens(session)

    assert removed == 0
