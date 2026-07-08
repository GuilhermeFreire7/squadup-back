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
from app.models.rating import Rating
from app.models.user import User

RATING_PAYLOAD = {
    "punctuality": 5,
    "respect": 5,
    "behavior": 4,
    "presence": 5,
    "overall": 5,
    "comment": "Ótimo parceiro de jogo!",
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


def _make_match(
    session: Session,
    id_: str,
    organizer: User,
    max_participants: int = 4,
    status: MatchStatus = MatchStatus.CLOSED,
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


def _confirm_participant(
    session: Session,
    match_id: str,
    user_id: str,
    status_: ParticipationStatus = ParticipationStatus.CONFIRMED,
) -> None:
    session.add(Participant(match_id=match_id, user_id=user_id, status=status_))
    session.commit()


def test_confirmed_participant_can_rate_another_after_match_closed(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)
    rater_token = _register_and_login(client, email="rater@example.com")
    rater = client.get("/users/me", headers={"Authorization": f"Bearer {rater_token}"}).json()
    _confirm_participant(session, match.id, organizer.id)
    _confirm_participant(session, match.id, rater["id"])

    response = client.post(
        f"/matches/{match.id}/ratings/{organizer.id}",
        json=RATING_PAYLOAD,
        headers={"Authorization": f"Bearer {rater_token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["match_id"] == match.id
    assert body["rated_user"]["id"] == organizer.id
    assert body["rater"]["id"] == rater["id"]
    assert body["overall"] == 5
    assert body["comment"] == "Ótimo parceiro de jogo!"


def test_cannot_rate_before_match_is_closed(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer, status=MatchStatus.OPEN)
    rater_token = _register_and_login(client, email="rater@example.com")
    rater = client.get("/users/me", headers={"Authorization": f"Bearer {rater_token}"}).json()
    _confirm_participant(session, match.id, organizer.id)
    _confirm_participant(session, match.id, rater["id"])

    response = client.post(
        f"/matches/{match.id}/ratings/{organizer.id}",
        json=RATING_PAYLOAD,
        headers={"Authorization": f"Bearer {rater_token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "MATCH_NOT_CLOSED"


def test_cannot_rate_self(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)
    token = _register_and_login(client, email="rater@example.com")
    rater = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    _confirm_participant(session, match.id, rater["id"])

    response = client.post(
        f"/matches/{match.id}/ratings/{rater['id']}",
        json=RATING_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CANNOT_RATE_SELF"


def test_rater_must_have_been_confirmed_participant(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)
    outsider_token = _register_and_login(client, email="outsider@example.com")
    _confirm_participant(session, match.id, organizer.id)

    response = client.post(
        f"/matches/{match.id}/ratings/{organizer.id}",
        json=RATING_PAYLOAD,
        headers={"Authorization": f"Bearer {outsider_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "NOT_MATCH_PARTICIPANT"


def test_rated_user_must_have_been_confirmed_participant(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    outsider = _make_user(session, "u2", "Bob")
    match = _make_match(session, "match-1", organizer)
    token = _register_and_login(client, email="rater@example.com")
    rater = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    _confirm_participant(session, match.id, rater["id"])

    response = client.post(
        f"/matches/{match.id}/ratings/{outsider.id}",
        json=RATING_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "RATED_USER_NOT_PARTICIPANT"


def test_cannot_rate_same_user_twice_for_same_match(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)
    token = _register_and_login(client, email="rater@example.com")
    rater = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    _confirm_participant(session, match.id, organizer.id)
    _confirm_participant(session, match.id, rater["id"])
    headers = {"Authorization": f"Bearer {token}"}
    client.post(f"/matches/{match.id}/ratings/{organizer.id}", json=RATING_PAYLOAD, headers=headers)

    response = client.post(
        f"/matches/{match.id}/ratings/{organizer.id}", json=RATING_PAYLOAD, headers=headers
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ALREADY_RATED"


def test_rate_participant_rejects_missing_token(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)

    response = client.post(f"/matches/{match.id}/ratings/{organizer.id}", json=RATING_PAYLOAD)

    assert response.status_code == 401


def test_rate_participant_returns_404_for_unknown_match(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    token = _register_and_login(client, email="rater@example.com")

    response = client.post(
        f"/matches/does-not-exist/ratings/{organizer.id}",
        json=RATING_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MATCH_NOT_FOUND"


def test_rate_participant_returns_404_for_unknown_user(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)
    token = _register_and_login(client, email="rater@example.com")

    response = client.post(
        f"/matches/{match.id}/ratings/does-not-exist",
        json=RATING_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "USER_NOT_FOUND"


def test_rate_participant_rejects_out_of_range_criteria(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    organizer = _make_user(session, "u1", "Alice")
    match = _make_match(session, "match-1", organizer)
    token = _register_and_login(client, email="rater@example.com")

    response = client.post(
        f"/matches/{match.id}/ratings/{organizer.id}",
        json={**RATING_PAYLOAD, "overall": 6},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_list_ratings_received_orders_most_recent_first(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    rated = _make_user(session, "u1", "Alice")
    rater_a = _make_user(session, "u2", "Bob")
    rater_b = _make_user(session, "u3", "Carla")
    match = _make_match(session, "match-1", rated)
    session.add(
        Rating(
            id="rating-1",
            rated_user_id=rated.id,
            rater_user_id=rater_a.id,
            match_id=match.id,
            punctuality=4,
            respect=4,
            behavior=4,
            presence=4,
            overall=4,
        )
    )
    session.add(
        Rating(
            id="rating-2",
            rated_user_id=rated.id,
            rater_user_id=rater_b.id,
            match_id=match.id,
            punctuality=5,
            respect=5,
            behavior=5,
            presence=5,
            overall=5,
        )
    )
    session.commit()

    response = client.get(f"/users/{rated.id}/ratings")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {rating["id"] for rating in body} == {"rating-1", "rating-2"}


def test_list_ratings_received_returns_404_for_unknown_user(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client

    response = client.get("/users/does-not-exist/ratings")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "USER_NOT_FOUND"
