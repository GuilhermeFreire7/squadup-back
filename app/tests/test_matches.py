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
