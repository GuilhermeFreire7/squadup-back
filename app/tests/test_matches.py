from collections.abc import Generator
from datetime import date, time
from typing import cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.database import get_session
from app.core.security import hash_password
from app.main import app
from app.models.enums import ExperienceLevel, MatchStatus, ParticipationStatus, Sport
from app.models.match import Match
from app.models.participant import Participant
from app.models.user import User

MATCH_CREATE_PAYLOAD = {
    "sport": "football",
    "title": "Pelada de domingo na arena",
    "location": "Arena Botafogo — Rua General Polidoro, 400",
    "date": "2026-05-25",
    "time": "09:00:00",
    "max_participants": 10,
    "level": "intermediate",
}


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


def _join(client: TestClient, match_id: str, token: str) -> Response:
    headers = {"Authorization": f"Bearer {token}"}
    return cast(Response, client.post(f"/matches/{match_id}/join", headers=headers))


def _leave(client: TestClient, match_id: str, token: str) -> Response:
    headers = {"Authorization": f"Bearer {token}"}
    return cast(Response, client.post(f"/matches/{match_id}/leave", headers=headers))


def _make_match(
    session: Session,
    id_: str,
    organizer: User,
    sport: Sport = Sport.FOOTBALL,
    max_participants: int = 4,
    match_date: date = date(2026, 5, 25),
    location: str = "Arena Botafogo",
    level: ExperienceLevel = ExperienceLevel.INTERMEDIATE,
    status: MatchStatus = MatchStatus.OPEN,
) -> Match:
    match = Match(
        id=id_,
        sport=sport,
        title=f"Partida {id_}",
        location=location,
        date=match_date,
        time=time(9, 0),
        max_participants=max_participants,
        level=level,
        organizer_id=organizer.id,
        status=status,
    )
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def test_list_matches_returns_all_without_filters(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "match-1", organizer)
    _make_match(session, "match-2", organizer, sport=Sport.VOLLEYBALL)

    response = client.get("/matches")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2


def test_list_matches_filters_by_sport(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "match-1", organizer, sport=Sport.FOOTBALL)
    _make_match(session, "match-2", organizer, sport=Sport.VOLLEYBALL)

    response = client.get("/matches", params={"sport": "volleyball"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "match-2"


def test_list_matches_filters_by_location(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "match-1", organizer, location="Arena Botafogo")
    _make_match(session, "match-2", organizer, location="Praia da Barra")

    response = client.get("/matches", params={"location": "botafogo"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "match-1"


def test_list_matches_filters_by_open_slots(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    player = _make_user(session, "u2", "Bob")
    full_match = _make_match(session, "match-1", organizer, max_participants=1)
    _make_match(session, "match-2", organizer, max_participants=4)

    session.add(
        Participant(
            match_id=full_match.id,
            user_id=player.id,
            status=ParticipationStatus.CONFIRMED,
        )
    )
    session.commit()

    response = client.get("/matches", params={"has_open_slots": True})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "match-2"


def test_list_matches_computes_available_slots_from_confirmed_participants(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    player = _make_user(session, "u2", "Bob")
    match = _make_match(session, "match-1", organizer, max_participants=4)

    session.add(
        Participant(match_id=match.id, user_id=player.id, status=ParticipationStatus.CONFIRMED)
    )
    session.add(
        Participant(match_id=match.id, user_id=organizer.id, status=ParticipationStatus.PENDING)
    )
    session.commit()

    response = client.get("/matches")

    assert response.status_code == 200
    body = response.json()
    match_payload = next(m for m in body if m["id"] == "match-1")
    assert match_payload["confirmed_count"] == 1
    assert match_payload["available_slots"] == 3


def test_read_match_detail_expands_organizer_and_participants(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    player = _make_user(session, "u2", "Bob")
    match = _make_match(session, "match-1", organizer, max_participants=4)
    session.add(
        Participant(match_id=match.id, user_id=player.id, status=ParticipationStatus.CONFIRMED)
    )
    session.commit()

    response = client.get(f"/matches/{match.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["organizer"]["id"] == organizer.id
    assert len(body["participants"]) == 1
    assert body["participants"][0]["user"]["id"] == player.id
    assert body["participants"][0]["status"] == "confirmed"


def test_read_match_detail_returns_404_for_unknown_match(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client

    response = client.get("/matches/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MATCH_NOT_FOUND"


def test_create_match_sets_authenticated_user_as_organizer(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client)

    response = client.post(
        "/matches",
        json=MATCH_CREATE_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == MATCH_CREATE_PAYLOAD["title"]
    assert body["status"] == "open"
    assert body["confirmed_count"] == 0
    assert body["available_slots"] == MATCH_CREATE_PAYLOAD["max_participants"]

    me_response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert body["organizer_id"] == me_response.json()["id"]


def test_create_match_appears_in_listing(db_client: tuple[TestClient, Session]) -> None:
    client, _ = db_client
    token = _register_and_login(client)

    create_response = client.post(
        "/matches",
        json=MATCH_CREATE_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    match_id = create_response.json()["id"]

    list_response = client.get("/matches")

    assert list_response.status_code == 200
    assert any(match["id"] == match_id for match in list_response.json())


def test_create_match_rejects_missing_token(db_client: tuple[TestClient, Session]) -> None:
    client, _ = db_client

    response = client.post("/matches", json=MATCH_CREATE_PAYLOAD)

    assert response.status_code == 401


def test_create_match_rejects_non_positive_max_participants(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client)
    payload = {**MATCH_CREATE_PAYLOAD, "max_participants": 0}

    response = client.post(
        "/matches",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_create_match_rejects_blank_title(db_client: tuple[TestClient, Session]) -> None:
    client, _ = db_client
    token = _register_and_login(client)
    payload = {**MATCH_CREATE_PAYLOAD, "title": ""}

    response = client.post(
        "/matches",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_create_match_rejects_invalid_sport(db_client: tuple[TestClient, Session]) -> None:
    client, _ = db_client
    token = _register_and_login(client)
    payload = {**MATCH_CREATE_PAYLOAD, "sport": "chess"}

    response = client.post(
        "/matches",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_join_match_confirms_when_no_approval_required(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=4)
    token = _register_and_login(client, email="player@example.com")

    response = _join(client, match.id, token)

    assert response.status_code == 200
    body = response.json()
    assert body["confirmed_count"] == 1
    assert body["status"] == "open"


def test_join_match_stays_pending_when_approval_required(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=4)
    match.requires_approval = True
    session.add(match)
    session.commit()
    token = _register_and_login(client, email="player@example.com")

    response = _join(client, match.id, token)

    assert response.status_code == 200
    body = response.json()
    assert body["confirmed_count"] == 0


def test_join_match_sets_status_full_when_last_slot_taken(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=1)
    token = _register_and_login(client, email="player@example.com")

    response = _join(client, match.id, token)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "full"
    assert body["available_slots"] == 0


def test_join_match_rejects_when_full_and_no_approval(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=1)
    session.add(
        Participant(match_id=match.id, user_id=organizer.id, status=ParticipationStatus.CONFIRMED)
    )
    session.commit()
    token = _register_and_login(client, email="player@example.com")

    response = _join(client, match.id, token)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "MATCH_FULL"


def test_join_match_rejects_duplicate_participation(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=4)
    token = _register_and_login(client, email="player@example.com")
    _join(client, match.id, token)

    response = _join(client, match.id, token)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ALREADY_PARTICIPATING"


def test_join_match_rejects_closed_match(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, status=MatchStatus.CLOSED)
    token = _register_and_login(client, email="player@example.com")

    response = _join(client, match.id, token)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "MATCH_NOT_JOINABLE"


def test_join_match_returns_404_for_unknown_match(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client, email="player@example.com")

    response = client.post(
        "/matches/does-not-exist/join", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


def test_leave_match_cancels_confirmed_participation(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=4)
    token = _register_and_login(client, email="player@example.com")
    _join(client, match.id, token)

    response = _leave(client, match.id, token)

    assert response.status_code == 200
    assert response.json()["confirmed_count"] == 0


def test_leave_match_reopens_full_match(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=1)
    token = _register_and_login(client, email="player@example.com")
    _join(client, match.id, token)

    response = _leave(client, match.id, token)

    assert response.status_code == 200
    assert response.json()["status"] == "open"


def test_leave_match_rejects_when_not_participating(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=4)
    token = _register_and_login(client, email="player@example.com")

    response = _leave(client, match.id, token)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "NOT_PARTICIPATING"


def test_approve_participant_confirms_pending_request(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer_token = _register_and_login(client, email="organizer@example.com")
    organizer_id = client.get(
        "/users/me", headers={"Authorization": f"Bearer {organizer_token}"}
    ).json()["id"]
    organizer = session.get(User, organizer_id)
    assert organizer is not None
    match = _make_match(session, "match-1", organizer, max_participants=4)
    match.requires_approval = True
    session.add(match)
    session.commit()

    player_token = _register_and_login(client, email="player@example.com")
    player_id = client.get("/users/me", headers={"Authorization": f"Bearer {player_token}"}).json()[
        "id"
    ]
    _join(client, match.id, player_token)

    response = client.post(
        f"/matches/{match.id}/participants/{player_id}/approve",
        headers={"Authorization": f"Bearer {organizer_token}"},
    )

    assert response.status_code == 200
    assert response.json()["confirmed_count"] == 1


def test_approve_participant_rejects_non_organizer(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=4)
    match.requires_approval = True
    session.add(match)
    session.commit()

    player_token = _register_and_login(client, email="player@example.com")
    player_id = client.get("/users/me", headers={"Authorization": f"Bearer {player_token}"}).json()[
        "id"
    ]
    _join(client, match.id, player_token)

    other_token = _register_and_login(client, email="other@example.com")

    response = client.post(
        f"/matches/{match.id}/participants/{player_id}/approve",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "NOT_MATCH_ORGANIZER"


def test_close_match_sets_status_closed(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer_token = _register_and_login(client, email="organizer@example.com")
    organizer_id = client.get(
        "/users/me", headers={"Authorization": f"Bearer {organizer_token}"}
    ).json()["id"]
    organizer = session.get(User, organizer_id)
    assert organizer is not None
    match = _make_match(session, "match-1", organizer, max_participants=4)

    response = client.post(
        f"/matches/{match.id}/close",
        headers={"Authorization": f"Bearer {organizer_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "closed"


def test_close_match_rejects_non_organizer(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=4)
    other_token = _register_and_login(client, email="other@example.com")

    response = client.post(
        f"/matches/{match.id}/close",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "NOT_MATCH_ORGANIZER"


def test_close_match_rejects_already_closed_match(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer_token = _register_and_login(client, email="organizer@example.com")
    organizer_id = client.get(
        "/users/me", headers={"Authorization": f"Bearer {organizer_token}"}
    ).json()["id"]
    organizer = session.get(User, organizer_id)
    assert organizer is not None
    match = _make_match(
        session, "match-1", organizer, max_participants=4, status=MatchStatus.CLOSED
    )

    response = client.post(
        f"/matches/{match.id}/close",
        headers={"Authorization": f"Bearer {organizer_token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "MATCH_ALREADY_RESOLVED"


def test_close_match_returns_404_for_unknown_match(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client)

    response = client.post(
        "/matches/does-not-exist/close", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


def test_close_match_rejects_missing_token(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=4)

    response = client.post(f"/matches/{match.id}/close")

    assert response.status_code == 401


def test_approve_participant_rejects_when_no_pending_request(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer_token = _register_and_login(client, email="organizer@example.com")
    organizer_id = client.get(
        "/users/me", headers={"Authorization": f"Bearer {organizer_token}"}
    ).json()["id"]
    organizer = session.get(User, organizer_id)
    assert organizer is not None
    match = _make_match(session, "match-1", organizer, max_participants=4)

    response = client.post(
        f"/matches/{match.id}/participants/unknown-user/approve",
        headers={"Authorization": f"Bearer {organizer_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PENDING_PARTICIPANT_NOT_FOUND"
