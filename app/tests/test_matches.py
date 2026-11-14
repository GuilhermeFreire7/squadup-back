from collections.abc import Generator
from datetime import UTC, date, datetime, time
from typing import cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.core.database import get_session
from app.core.security import hash_password
from app.main import app
from app.models.enums import ExperienceLevel, MatchStatus, ParticipationStatus, Sport
from app.models.match import Match
from app.models.participant import Participant
from app.models.user import User
from app.services import match_service
from app.services.match_service import local_today

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


TEST_TODAY = date(2026, 1, 1)


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(match_service, "local_today", lambda: TEST_TODAY)


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
    match_time: time = time(9, 0),
    location: str = "Arena Botafogo",
    level: ExperienceLevel = ExperienceLevel.INTERMEDIATE,
    status: MatchStatus = MatchStatus.OPEN,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Match:
    match = Match(
        id=id_,
        sport=sport,
        title=f"Partida {id_}",
        location=location,
        date=match_date,
        time=match_time,
        max_participants=max_participants,
        level=level,
        organizer_id=organizer.id,
        status=status,
        latitude=latitude,
        longitude=longitude,
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


def test_list_matches_orders_upcoming_by_date_and_time(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    # Inseridas fora de ordem: a resposta não pode depender da ordem de inserção.
    _make_match(session, "later-day", organizer, match_date=date(2026, 6, 2))
    _make_match(
        session, "same-day-evening", organizer, match_date=date(2026, 6, 1), match_time=time(20)
    )
    _make_match(
        session, "same-day-morning", organizer, match_date=date(2026, 6, 1), match_time=time(8)
    )

    response = client.get("/matches")

    assert response.status_code == 200
    assert [m["id"] for m in response.json()] == [
        "same-day-morning",
        "same-day-evening",
        "later-day",
    ]


def test_list_matches_puts_finished_last_most_recent_first(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(
        session, "closed-old", organizer, match_date=date(2026, 5, 1), status=MatchStatus.CLOSED
    )
    _make_match(
        session,
        "cancelled-recent",
        organizer,
        match_date=date(2026, 5, 10),
        status=MatchStatus.CANCELLED,
    )
    _make_match(session, "open-late", organizer, match_date=date(2026, 7, 1))
    _make_match(
        session, "full-soon", organizer, match_date=date(2026, 6, 1), status=MatchStatus.FULL
    )

    response = client.get("/matches")

    assert response.status_code == 200
    assert [m["id"] for m in response.json()] == [
        "full-soon",
        "open-late",
        "cancelled-recent",
        "closed-old",
    ]


def _user_id(client: TestClient, token: str) -> str:
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    return str(response.json()["id"])


def test_local_today_uses_brasilia_time() -> None:
    # 02:00 UTC ainda é o dia anterior em Brasília (UTC-3).
    assert local_today(datetime(2026, 12, 20, 2, 0, tzinfo=UTC)) == date(2026, 12, 19)
    assert local_today(datetime(2026, 12, 20, 3, 0, tzinfo=UTC)) == date(2026, 12, 20)


def test_list_matches_hides_active_matches_in_the_past(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "open-past", organizer, match_date=date(2025, 12, 31))
    _make_match(
        session, "full-past", organizer, match_date=date(2025, 12, 31), status=MatchStatus.FULL
    )
    _make_match(session, "open-today", organizer, match_date=TEST_TODAY)
    _make_match(
        session, "closed-past", organizer, match_date=date(2025, 12, 1), status=MatchStatus.CLOSED
    )
    _make_match(
        session,
        "cancelled-past",
        organizer,
        match_date=date(2025, 12, 2),
        status=MatchStatus.CANCELLED,
    )

    response = client.get("/matches")

    assert response.status_code == 200
    assert [m["id"] for m in response.json()] == ["open-today", "cancelled-past", "closed-past"]


def test_list_matches_keeps_past_active_match_for_its_organizer(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    token = _register_and_login(client, "org@example.com")
    organizer = session.get(User, _user_id(client, token))
    assert organizer is not None
    _make_match(session, "mine-past", organizer, match_date=date(2025, 12, 31))

    as_organizer = client.get("/matches", headers={"Authorization": f"Bearer {token}"})
    other_token = _register_and_login(client, "other@example.com")
    as_other = client.get("/matches", headers={"Authorization": f"Bearer {other_token}"})

    assert [m["id"] for m in as_organizer.json()] == ["mine-past"]
    assert as_other.json() == []


def test_list_matches_keeps_past_active_match_for_its_participants(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "played-past", organizer, match_date=date(2025, 12, 31))
    token = _register_and_login(client, "player@example.com")
    session.add(
        Participant(
            match_id="played-past",
            user_id=_user_id(client, token),
            status=ParticipationStatus.CONFIRMED,
        )
    )
    session.commit()

    response = client.get("/matches", headers={"Authorization": f"Bearer {token}"})

    assert [m["id"] for m in response.json()] == ["played-past"]


def test_list_matches_with_invalid_token_is_treated_as_anonymous(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "open-future", organizer, match_date=date(2026, 2, 1))
    _make_match(session, "open-past", organizer, match_date=date(2025, 12, 31))

    response = client.get("/matches", headers={"Authorization": "Bearer token-invalido"})

    assert response.status_code == 200
    assert [m["id"] for m in response.json()] == ["open-future"]


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


def test_list_matches_filters_by_date(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "match-1", organizer, match_date=date(2026, 5, 25))
    _make_match(session, "match-2", organizer, match_date=date(2026, 6, 1))

    response = client.get("/matches", params={"date": "2026-05-25"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "match-1"


def test_list_matches_filters_by_level(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "match-1", organizer, level=ExperienceLevel.BEGINNER)
    _make_match(session, "match-2", organizer, level=ExperienceLevel.ADVANCED)

    response = client.get("/matches", params={"level": "advanced"})

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
    token = _register_and_login(client, email="viewer@example.com")

    response = client.get(f"/matches/{match.id}", headers={"Authorization": f"Bearer {token}"})

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
    token = _register_and_login(client, email="viewer@example.com")

    response = client.get("/matches/does-not-exist", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MATCH_NOT_FOUND"


def test_read_match_detail_rejects_missing_token(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)

    response = client.get(f"/matches/{match.id}")

    assert response.status_code == 401


def test_list_matches_stays_public(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "match-1", organizer)

    response = client.get("/matches")

    assert response.status_code == 200
    assert len(response.json()) == 1


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
    assert body["confirmed_count"] == 1
    assert body["available_slots"] == cast(int, MATCH_CREATE_PAYLOAD["max_participants"]) - 1

    me_response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert body["organizer_id"] == me_response.json()["id"]


def test_create_match_adds_organizer_as_confirmed_participant(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    match_id = client.post("/matches", json=MATCH_CREATE_PAYLOAD, headers=headers).json()["id"]
    detail = client.get(f"/matches/{match_id}", headers=headers).json()

    assert detail["participants"] == [
        {"user": detail["organizer"], "status": "confirmed"},
    ]


def test_create_match_with_single_slot_is_full_with_organizer(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client)
    payload = {**MATCH_CREATE_PAYLOAD, "max_participants": 1}

    response = client.post("/matches", json=payload, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "full"
    assert body["available_slots"] == 0


def test_organizer_of_created_match_can_close_and_rate_participant(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    organizer_headers = {"Authorization": f"Bearer {_register_and_login(client)}"}
    player_token = _register_and_login(client, email="player@example.com")
    match_id = client.post("/matches", json=MATCH_CREATE_PAYLOAD, headers=organizer_headers).json()[
        "id"
    ]
    _join(client, match_id, player_token)
    client.post(f"/matches/{match_id}/close", headers=organizer_headers)
    player_id = client.get("/users/me", headers={"Authorization": f"Bearer {player_token}"}).json()[
        "id"
    ]
    rating = {"punctuality": 5, "respect": 5, "behavior": 5, "presence": 5, "overall": 5}

    response = client.post(
        f"/matches/{match_id}/ratings/{player_id}", json=rating, headers=organizer_headers
    )

    assert response.status_code == 201


def test_create_match_emits_system_message(db_client: tuple[TestClient, Session]) -> None:
    client, _ = db_client
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post("/matches", json=MATCH_CREATE_PAYLOAD, headers=headers)
    match_id = create_response.json()["id"]

    messages_response = client.get(f"/matches/{match_id}/messages", headers=headers)

    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert len(messages) == 1
    assert messages[0]["type"] == "system"


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


@pytest.mark.parametrize("resolved_status", [MatchStatus.CLOSED, MatchStatus.CANCELLED])
def test_leave_match_rejects_closed_or_cancelled_match(
    db_client: tuple[TestClient, Session],
    resolved_status: MatchStatus,
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=4)
    token = _register_and_login(client, email="player@example.com")
    _join(client, match.id, token)
    match.status = resolved_status
    session.add(match)
    session.commit()

    response = _leave(client, match.id, token)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "MATCH_NOT_LEAVABLE"
    participant = session.exec(select(Participant).where(Participant.match_id == match.id)).one()
    assert participant.status == ParticipationStatus.CONFIRMED


def test_leave_match_rejects_organizer(db_client: tuple[TestClient, Session]) -> None:
    client, _ = db_client
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    match_id = client.post("/matches", json=MATCH_CREATE_PAYLOAD, headers=headers).json()["id"]

    response = _leave(client, match_id, token)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ORGANIZER_CANNOT_LEAVE"
    detail = client.get(f"/matches/{match_id}", headers=headers).json()
    assert detail["confirmed_count"] == 1


def test_join_match_after_leaving_reactivates_participant(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, max_participants=4)
    token = _register_and_login(client, email="player@example.com")
    _join(client, match.id, token)
    _leave(client, match.id, token)

    response = _join(client, match.id, token)

    assert response.status_code == 200
    body = response.json()
    assert body["confirmed_count"] == 1


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


def test_approve_participant_rejects_when_match_already_full(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer_token = _register_and_login(client, email="organizer@example.com")
    organizer_id = client.get(
        "/users/me", headers={"Authorization": f"Bearer {organizer_token}"}
    ).json()["id"]
    organizer = session.get(User, organizer_id)
    assert organizer is not None
    match = _make_match(session, "match-1", organizer, max_participants=1)
    match.requires_approval = True
    session.add(match)
    session.commit()

    first_token = _register_and_login(client, email="first@example.com")
    first_id = client.get("/users/me", headers={"Authorization": f"Bearer {first_token}"}).json()[
        "id"
    ]
    _join(client, match.id, first_token)
    client.post(
        f"/matches/{match.id}/participants/{first_id}/approve",
        headers={"Authorization": f"Bearer {organizer_token}"},
    )

    second_token = _register_and_login(client, email="second@example.com")
    second_id = client.get("/users/me", headers={"Authorization": f"Bearer {second_token}"}).json()[
        "id"
    ]
    _join(client, match.id, second_token)

    response = client.post(
        f"/matches/{match.id}/participants/{second_id}/approve",
        headers={"Authorization": f"Bearer {organizer_token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "MATCH_FULL"


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


# Coordenadas reais do Rio de Janeiro, usadas nos testes de busca geográfica.
BOTAFOGO = (-22.9519, -43.1889)
COPACABANA = (-22.9711, -43.1822)  # ~4km de Botafogo
BRASILIA = (-15.7801, -47.9292)  # ~1000km+ de distância


def test_create_match_accepts_optional_coordinates(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client)
    payload = {**MATCH_CREATE_PAYLOAD, "latitude": BOTAFOGO[0], "longitude": BOTAFOGO[1]}

    response = client.post("/matches", json=payload, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 201
    body = response.json()
    assert body["latitude"] == BOTAFOGO[0]
    assert body["longitude"] == BOTAFOGO[1]


def test_create_match_without_coordinates_defaults_to_null(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client)

    response = client.post(
        "/matches", json=MATCH_CREATE_PAYLOAD, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["latitude"] is None
    assert body["longitude"] is None


def test_list_matches_with_geo_filters_out_matches_beyond_radius(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "match-near", organizer, latitude=COPACABANA[0], longitude=COPACABANA[1])
    _make_match(session, "match-far", organizer, latitude=BRASILIA[0], longitude=BRASILIA[1])

    response = client.get(
        "/matches",
        params={"lat": BOTAFOGO[0], "lng": BOTAFOGO[1], "radius_km": 20},
    )

    assert response.status_code == 200
    body = response.json()
    assert [m["id"] for m in body] == ["match-near"]
    assert body[0]["distance_km"] is not None


def test_list_matches_with_geo_orders_by_distance(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "match-far", organizer, latitude=COPACABANA[0], longitude=COPACABANA[1])
    _make_match(session, "match-near", organizer, latitude=BOTAFOGO[0], longitude=BOTAFOGO[1])

    response = client.get(
        "/matches",
        params={"lat": BOTAFOGO[0], "lng": BOTAFOGO[1], "radius_km": 20},
    )

    assert response.status_code == 200
    body = response.json()
    assert [m["id"] for m in body] == ["match-near", "match-far"]
    assert body[0]["distance_km"] == 0.0
    assert body[1]["distance_km"] > body[0]["distance_km"]


def test_list_matches_with_geo_excludes_matches_without_coordinates(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(
        session, "match-with-coords", organizer, latitude=BOTAFOGO[0], longitude=BOTAFOGO[1]
    )
    _make_match(session, "match-without-coords", organizer)

    response = client.get("/matches", params={"lat": BOTAFOGO[0], "lng": BOTAFOGO[1]})

    assert response.status_code == 200
    body = response.json()
    assert [m["id"] for m in body] == ["match-with-coords"]


def test_list_matches_without_lat_lng_ignores_radius_km(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    _make_match(session, "match-1", organizer, latitude=BRASILIA[0], longitude=BRASILIA[1])

    response = client.get("/matches", params={"radius_km": 1})

    assert response.status_code == 200
    body = response.json()
    assert [m["id"] for m in body] == ["match-1"]
    assert body[0]["distance_km"] is None


def test_close_match_sends_push_to_confirmed_participants_excluding_organizer(
    db_client: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, session = db_client
    organizer_token = _register_and_login(client, email="organizer@example.com")
    organizer_id = client.get(
        "/users/me", headers={"Authorization": f"Bearer {organizer_token}"}
    ).json()["id"]
    organizer = session.get(User, organizer_id)
    assert organizer is not None
    match = _make_match(session, "match-1", organizer, max_participants=4)

    player_token = _register_and_login(client, email="player@example.com")
    player_headers = {"Authorization": f"Bearer {player_token}"}
    _join(client, match.id, player_token)
    client.post("/users/me/push-token", json={"token": "player-token"}, headers=player_headers)
    client.post(
        "/users/me/push-token",
        json={"token": "organizer-token"},
        headers={"Authorization": f"Bearer {organizer_token}"},
    )

    sent_tokens: list[str] = []
    monkeypatch.setattr(
        "app.services.notification_service.httpx.post",
        lambda url, json, timeout: sent_tokens.extend(m["to"] for m in json),
    )

    response = client.post(
        f"/matches/{match.id}/close",
        headers={"Authorization": f"Bearer {organizer_token}"},
    )

    assert response.status_code == 200
    assert sent_tokens == ["player-token"]


def test_approve_participant_sends_push_to_approved_user(
    db_client: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
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
    player_headers = {"Authorization": f"Bearer {player_token}"}
    player_id = client.get("/users/me", headers=player_headers).json()["id"]
    _join(client, match.id, player_token)
    client.post("/users/me/push-token", json={"token": "player-token"}, headers=player_headers)

    sent_tokens: list[str] = []
    monkeypatch.setattr(
        "app.services.notification_service.httpx.post",
        lambda url, json, timeout: sent_tokens.extend(m["to"] for m in json),
    )

    response = client.post(
        f"/matches/{match.id}/participants/{player_id}/approve",
        headers={"Authorization": f"Bearer {organizer_token}"},
    )

    assert response.status_code == 200
    assert sent_tokens == ["player-token"]
