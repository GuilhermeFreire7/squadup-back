from collections.abc import Generator
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.database import get_session
from app.core.security import hash_password
from app.main import app
from app.models.enums import ExperienceLevel, MatchStatus, ParticipationStatus, Sport
from app.models.match import Match
from app.models.participant import Participant
from app.models.user import User


def _register_and_login(client: TestClient, email: str = "organizer@example.com") -> str:
    register_payload = {
        "name": "Organizadora",
        "email": email,
        "password": "senha-super-secreta",
        "age": 28,
        "location": "Rio de Janeiro, RJ",
        "favorite_sports": ["football"],
    }
    client.post("/auth/register", json=register_payload)
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": register_payload["password"]},
    )
    return str(login_response.json()["access_token"])


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


def _make_user(session: Session, id_: str, name: str) -> User:
    user = User(
        id=id_,
        name=name,
        email=f"{id_}@example.com",
        hashed_password=hash_password("senha-super-secreta"),
        age=25,
        location="Rio de Janeiro, RJ",
        favorite_sports=[Sport.FOOTBALL],
        level=ExperienceLevel.INTERMEDIATE,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_match(
    session: Session,
    id_: str,
    organizer: User,
    max_participants: int = 4,
    status: MatchStatus = MatchStatus.OPEN,
) -> Match:
    match = Match(
        id=id_,
        sport=Sport.FOOTBALL,
        title=f"Partida {id_}",
        location="Arena Botafogo",
        date=date(2026, 5, 25),
        time=time(9, 0),
        max_participants=max_participants,
        level=ExperienceLevel.INTERMEDIATE,
        organizer_id=organizer.id,
        status=status,
    )
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def _confirm_participant(session: Session, match_id: str, user_id: str) -> None:
    session.add(
        Participant(match_id=match_id, user_id=user_id, status=ParticipationStatus.CONFIRMED)
    )
    session.commit()


def test_organizer_can_send_message(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    token = _register_and_login(client)
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    organizer = session.get(User, me["id"])
    assert organizer is not None
    match = _make_match(session, "match-1", organizer)

    response = client.post(
        f"/matches/{match.id}/messages",
        json={"text": "Bora jogar!"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["text"] == "Bora jogar!"
    assert body["match_id"] == match.id
    assert body["sender"]["id"] == organizer.id
    assert body["type"] == "message"


def test_confirmed_participant_can_send_message(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)
    player_token = _register_and_login(client, email="player@example.com")
    player = client.get("/users/me", headers={"Authorization": f"Bearer {player_token}"}).json()
    _confirm_participant(session, match.id, player["id"])

    response = client.post(
        f"/matches/{match.id}/messages",
        json={"text": "Confirmado!"},
        headers={"Authorization": f"Bearer {player_token}"},
    )

    assert response.status_code == 201
    assert response.json()["sender"]["id"] == player["id"]


def test_non_participant_cannot_send_message(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)
    outsider_token = _register_and_login(client, email="outsider@example.com")

    response = client.post(
        f"/matches/{match.id}/messages",
        json={"text": "Posso entrar?"},
        headers={"Authorization": f"Bearer {outsider_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "NOT_MATCH_PARTICIPANT"


def test_pending_participant_cannot_send_message(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)
    player_token = _register_and_login(client, email="player@example.com")
    player = client.get("/users/me", headers={"Authorization": f"Bearer {player_token}"}).json()
    session.add(
        Participant(match_id=match.id, user_id=player["id"], status=ParticipationStatus.PENDING)
    )
    session.commit()

    response = client.post(
        f"/matches/{match.id}/messages",
        json={"text": "Ainda aguardando aprovação"},
        headers={"Authorization": f"Bearer {player_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "NOT_MATCH_PARTICIPANT"


def test_send_message_rejects_missing_token(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)

    response = client.post(f"/matches/{match.id}/messages", json={"text": "Oi"})

    assert response.status_code == 401


def test_send_message_returns_404_for_unknown_match(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client)

    response = client.post(
        "/matches/does-not-exist/messages",
        json={"text": "Oi"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MATCH_NOT_FOUND"


def test_send_message_rejects_blank_text(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    token = _register_and_login(client)
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    organizer = session.get(User, me["id"])
    assert organizer is not None
    match = _make_match(session, "match-1", organizer)

    response = client.post(
        f"/matches/{match.id}/messages",
        json={"text": ""},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_list_messages_returns_history_in_chronological_order(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    token = _register_and_login(client)
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    organizer = session.get(User, me["id"])
    assert organizer is not None
    match = _make_match(session, "match-1", organizer)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(f"/matches/{match.id}/messages", json={"text": "primeira"}, headers=headers)
    client.post(f"/matches/{match.id}/messages", json={"text": "segunda"}, headers=headers)

    response = client.get(f"/matches/{match.id}/messages", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert [message["text"] for message in body] == ["primeira", "segunda"]


def test_list_messages_respects_pagination(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    token = _register_and_login(client)
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    organizer = session.get(User, me["id"])
    assert organizer is not None
    match = _make_match(session, "match-1", organizer)
    headers = {"Authorization": f"Bearer {token}"}
    for text in ["um", "dois", "tres"]:
        client.post(f"/matches/{match.id}/messages", json={"text": text}, headers=headers)

    response = client.get(
        f"/matches/{match.id}/messages", params={"skip": 1, "limit": 1}, headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["text"] == "dois"


def test_list_messages_rejects_non_participant(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)
    outsider_token = _register_and_login(client, email="outsider@example.com")

    response = client.get(
        f"/matches/{match.id}/messages",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "NOT_MATCH_PARTICIPANT"


def test_list_messages_returns_404_for_unknown_match(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client)

    response = client.get(
        "/matches/does-not-exist/messages",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MATCH_NOT_FOUND"
