from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.services import my_matches_service

TODAY = date(2026, 1, 1)


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(my_matches_service, "local_today", lambda: TODAY)


def _register(client: TestClient, name: str, email: str) -> dict[str, str]:
    payload = {
        "name": name,
        "email": email,
        "password": "senha-super-secreta",
        "age": 28,
        "location": "Rio de Janeiro, RJ",
        "favorite_sports": ["football"],
    }
    client.post("/auth/register", json=payload)
    token = client.post(
        "/auth/login", json={"email": email, "password": payload["password"]}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_match(
    client: TestClient,
    headers: dict[str, str],
    title: str,
    match_date: str = "2026-02-01",
    match_time: str = "09:00:00",
    requires_approval: bool = False,
) -> str:
    response = client.post(
        "/matches",
        json={
            "sport": "football",
            "title": title,
            "location": "Arena Botafogo",
            "date": match_date,
            "time": match_time,
            "max_participants": 10,
            "level": "intermediate",
            "requires_approval": requires_approval,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _my_matches(client: TestClient, headers: dict[str, str]) -> list[dict[str, object]]:
    response = client.get("/users/me/matches", headers=headers)
    assert response.status_code == 200
    body: list[dict[str, object]] = response.json()
    return body


def test_my_matches_requires_authentication(client: TestClient) -> None:
    assert client.get("/users/me/matches").status_code == 401


def test_my_matches_lists_organized_and_joined_matches_only(client: TestClient) -> None:
    ana = _register(client, "Ana", "ana@example.com")
    bruno = _register(client, "Bruno", "bruno@example.com")
    organized = _create_match(client, ana, "Da Ana")
    joined = _create_match(client, bruno, "Do Bruno, com a Ana")
    requested = _create_match(client, bruno, "Do Bruno, com aprovação", requires_approval=True)
    left = _create_match(client, bruno, "Do Bruno, Ana saiu")
    _create_match(client, bruno, "Do Bruno, sem a Ana")
    client.post(f"/matches/{joined}/join", headers=ana)
    client.post(f"/matches/{requested}/join", headers=ana)
    client.post(f"/matches/{left}/join", headers=ana)
    client.post(f"/matches/{left}/leave", headers=ana)

    by_id = {m["id"]: m for m in _my_matches(client, ana)}

    assert set(by_id) == {organized, joined, requested}
    assert by_id[organized]["is_organizer"] is True
    assert by_id[organized]["my_status"] == "confirmed"
    assert by_id[joined]["is_organizer"] is False
    assert by_id[joined]["my_status"] == "confirmed"
    assert by_id[requested]["my_status"] == "pending"


def test_my_matches_counts_pending_requests_for_the_organizer_only(client: TestClient) -> None:
    ana = _register(client, "Ana", "ana@example.com")
    bruno = _register(client, "Bruno", "bruno@example.com")
    carla = _register(client, "Carla", "carla@example.com")
    match_id = _create_match(client, ana, "Com aprovação", requires_approval=True)
    client.post(f"/matches/{match_id}/join", headers=bruno)
    client.post(f"/matches/{match_id}/join", headers=carla)

    [as_organizer] = _my_matches(client, ana)
    [as_requester] = _my_matches(client, bruno)

    assert as_organizer["pending_requests"] == 2
    assert as_requester["pending_requests"] == 0


def test_my_matches_puts_upcoming_first_then_past_most_recent_first(client: TestClient) -> None:
    ana = _register(client, "Ana", "ana@example.com")
    later = _create_match(client, ana, "Mais tarde", "2026-03-01")
    soon_evening = _create_match(client, ana, "Logo, à noite", "2026-01-10", "20:00:00")
    soon_morning = _create_match(client, ana, "Logo, de manhã", "2026-01-10", "08:00:00")
    stale = _create_match(client, ana, "Ninguém encerrou", "2025-12-20")
    old = _create_match(client, ana, "Antiga", "2025-11-01")
    closed_future = _create_match(client, ana, "Encerrada antes", "2026-02-01")
    client.post(f"/matches/{closed_future}/close", headers=ana)

    matches = _my_matches(client, ana)

    assert [m["id"] for m in matches] == [
        soon_morning,
        soon_evening,
        later,
        closed_future,
        stale,
        old,
    ]
    assert [m["is_past"] for m in matches] == [False, False, False, True, True, True]


def test_my_matches_is_empty_for_a_new_user(client: TestClient) -> None:
    ana = _register(client, "Ana", "ana@example.com")

    assert _my_matches(client, ana) == []
