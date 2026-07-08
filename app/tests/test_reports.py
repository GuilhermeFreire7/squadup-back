from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.database import get_session
from app.core.security import hash_password
from app.main import app
from app.models.enums import ExperienceLevel, ReportStatus, Sport, UserRole
from app.models.match import Match
from app.models.report import Report
from app.models.user import User

REPORT_PAYLOAD = {
    "reason": "bad_behavior",
    "description": "Foi agressivo com outros jogadores durante a partida.",
}


def _register_and_login(client: TestClient, email: str = "user@example.com") -> str:
    register_payload = {
        "name": "Usuária",
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


def _make_user(session: Session, id_: str, name: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=id_,
        name=name,
        email=f"{id_}@example.com",
        hashed_password=hash_password("senha-super-secreta"),
        age=25,
        location="Rio de Janeiro, RJ",
        favorite_sports=[Sport.FOOTBALL],
        level=ExperienceLevel.INTERMEDIATE,
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _promote_to_admin(session: Session, user_id: str) -> None:
    user = session.get(User, user_id)
    assert user is not None
    user.role = UserRole.ADMIN
    session.add(user)
    session.commit()


def test_authenticated_user_can_report_another_user(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    reported = _make_user(session, "u1", "Alice")
    token = _register_and_login(client, email="reporter@example.com")

    response = client.post(
        "/reports",
        json={**REPORT_PAYLOAD, "reported_user_id": reported.id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["reported_user"]["id"] == reported.id
    assert body["status"] == "pending"
    assert body["match_id"] is None


def test_report_can_reference_a_match(db_client: tuple[TestClient, Session]) -> None:
    from datetime import date, time

    client, session = db_client
    reported = _make_user(session, "u1", "Alice")
    match = Match(
        id="match-1",
        sport=Sport.FOOTBALL,
        title="Partida 1",
        location="Arena Botafogo",
        date=date(2026, 5, 25),
        time=time(9, 0),
        max_participants=4,
        level=ExperienceLevel.INTERMEDIATE,
        organizer_id=reported.id,
    )
    session.add(match)
    session.commit()
    token = _register_and_login(client, email="reporter@example.com")

    response = client.post(
        "/reports",
        json={**REPORT_PAYLOAD, "reported_user_id": reported.id, "match_id": match.id},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["match_id"] == match.id


def test_report_rejects_unknown_match(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    reported = _make_user(session, "u1", "Alice")
    token = _register_and_login(client, email="reporter@example.com")

    response = client.post(
        "/reports",
        json={**REPORT_PAYLOAD, "reported_user_id": reported.id, "match_id": "does-not-exist"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "MATCH_NOT_FOUND"


def test_cannot_report_self(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    token = _register_and_login(client, email="reporter@example.com")
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()

    response = client.post(
        "/reports",
        json={**REPORT_PAYLOAD, "reported_user_id": me["id"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CANNOT_REPORT_SELF"


def test_report_returns_404_for_unknown_reported_user(
    db_client: tuple[TestClient, Session],
) -> None:
    client, _ = db_client
    token = _register_and_login(client, email="reporter@example.com")

    response = client.post(
        "/reports",
        json={**REPORT_PAYLOAD, "reported_user_id": "does-not-exist"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "USER_NOT_FOUND"


def test_report_rejects_missing_token(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    reported = _make_user(session, "u1", "Alice")

    response = client.post("/reports", json={**REPORT_PAYLOAD, "reported_user_id": reported.id})

    assert response.status_code == 401


def test_non_admin_cannot_list_reports(db_client: tuple[TestClient, Session]) -> None:
    client, _ = db_client
    token = _register_and_login(client, email="user@example.com")

    response = client.get("/reports", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ADMIN_ONLY"


def test_admin_can_list_reports_most_recent_first(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    reported = _make_user(session, "u1", "Alice")
    reporter = _make_user(session, "u2", "Bob")
    session.add(
        Report(
            id="report-1",
            reported_user_id=reported.id,
            reporter_user_id=reporter.id,
            reason="spam",
            description="Mensagens repetidas.",
        )
    )
    session.add(
        Report(
            id="report-2",
            reported_user_id=reported.id,
            reporter_user_id=reporter.id,
            reason="no_show",
            description="Não apareceu na partida.",
        )
    )
    session.commit()
    admin_token = _register_and_login(client, email="admin@example.com")
    admin = client.get("/users/me", headers={"Authorization": f"Bearer {admin_token}"}).json()
    _promote_to_admin(session, admin["id"])

    response = client.get("/reports", headers={"Authorization": f"Bearer {admin_token}"})

    assert response.status_code == 200
    body = response.json()
    assert {report["id"] for report in body} == {"report-1", "report-2"}


def test_admin_can_archive_a_pending_report(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    reported = _make_user(session, "u1", "Alice")
    reporter = _make_user(session, "u2", "Bob")
    session.add(
        Report(
            id="report-1",
            reported_user_id=reported.id,
            reporter_user_id=reporter.id,
            reason="spam",
            description="Mensagens repetidas.",
        )
    )
    session.commit()
    admin_token = _register_and_login(client, email="admin@example.com")
    admin = client.get("/users/me", headers={"Authorization": f"Bearer {admin_token}"}).json()
    _promote_to_admin(session, admin["id"])

    response = client.patch(
        "/reports/report-1",
        json={"action": "archive"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_admin_can_ban_a_pending_report(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    reported = _make_user(session, "u1", "Alice")
    reporter = _make_user(session, "u2", "Bob")
    session.add(
        Report(
            id="report-1",
            reported_user_id=reported.id,
            reporter_user_id=reporter.id,
            reason="violence",
            description="Agressão física durante a partida.",
        )
    )
    session.commit()
    admin_token = _register_and_login(client, email="admin@example.com")
    admin = client.get("/users/me", headers={"Authorization": f"Bearer {admin_token}"}).json()
    _promote_to_admin(session, admin["id"])

    response = client.patch(
        "/reports/report-1",
        json={"action": "ban"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "banned"


def test_cannot_resolve_an_already_resolved_report(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    reported = _make_user(session, "u1", "Alice")
    reporter = _make_user(session, "u2", "Bob")
    session.add(
        Report(
            id="report-1",
            reported_user_id=reported.id,
            reporter_user_id=reporter.id,
            reason="spam",
            description="Mensagens repetidas.",
            status=ReportStatus.ARCHIVED,
        )
    )
    session.commit()
    admin_token = _register_and_login(client, email="admin@example.com")
    admin = client.get("/users/me", headers={"Authorization": f"Bearer {admin_token}"}).json()
    _promote_to_admin(session, admin["id"])

    response = client.patch(
        "/reports/report-1",
        json={"action": "warn"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "REPORT_ALREADY_RESOLVED"


def test_non_admin_cannot_resolve_report(db_client: tuple[TestClient, Session]) -> None:
    client, session = db_client
    reported = _make_user(session, "u1", "Alice")
    reporter = _make_user(session, "u2", "Bob")
    session.add(
        Report(
            id="report-1",
            reported_user_id=reported.id,
            reporter_user_id=reporter.id,
            reason="spam",
            description="Mensagens repetidas.",
        )
    )
    session.commit()
    token = _register_and_login(client, email="user@example.com")

    response = client.patch(
        "/reports/report-1",
        json={"action": "archive"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ADMIN_ONLY"


def test_resolve_returns_404_for_unknown_report(
    db_client: tuple[TestClient, Session],
) -> None:
    client, session = db_client
    admin_token = _register_and_login(client, email="admin@example.com")
    admin = client.get("/users/me", headers={"Authorization": f"Bearer {admin_token}"}).json()
    _promote_to_admin(session, admin["id"])

    response = client.patch(
        "/reports/does-not-exist",
        json={"action": "archive"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "REPORT_NOT_FOUND"
