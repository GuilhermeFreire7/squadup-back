import pytest
from fastapi.testclient import TestClient

from app.services import storage_service

VALID_PAYLOAD = {
    "name": "Ana Souza",
    "email": "ana.souza@example.com",
    "password": "senha-super-secreta",
    "age": 28,
    "location": "São Paulo, SP",
    "favorite_sports": ["football"],
}

OTHER_PAYLOAD = {
    "name": "Bruno Lima",
    "email": "bruno.lima@example.com",
    "password": "outra-senha-secreta",
    "age": 31,
    "location": "Rio de Janeiro, RJ",
    "favorite_sports": ["volleyball"],
}


def _register_and_login(client: TestClient, payload: dict[str, object]) -> tuple[str, str]:
    register_response = client.post("/auth/register", json=payload)
    user_id = register_response.json()["id"]
    login_response = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    token = login_response.json()["access_token"]
    return user_id, token


def test_read_my_profile_returns_derived_fields(client: TestClient) -> None:
    _, token = _register_and_login(client, VALID_PAYLOAD)

    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == VALID_PAYLOAD["email"]
    assert body["average_rating"] is None
    assert body["matches_played"] == 0


def test_read_my_profile_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/users/me")

    assert response.status_code == 401


def test_update_my_profile_applies_partial_changes(client: TestClient) -> None:
    _, token = _register_and_login(client, VALID_PAYLOAD)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        "/users/me",
        json={"bio": "Nova bio", "location": "Curitiba, PR"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["bio"] == "Nova bio"
    assert body["location"] == "Curitiba, PR"
    assert body["name"] == VALID_PAYLOAD["name"]


def test_read_public_profile_hides_private_fields(client: TestClient) -> None:
    user_id, _ = _register_and_login(client, VALID_PAYLOAD)
    _, other_token = _register_and_login(client, OTHER_PAYLOAD)

    response = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user_id
    assert "email" not in body
    assert "role" not in body


def test_read_public_profile_returns_404_for_unknown_user(client: TestClient) -> None:
    response = client.get("/users/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "USER_NOT_FOUND"


def test_register_push_token_returns_no_content(client: TestClient) -> None:
    _, token = _register_and_login(client, VALID_PAYLOAD)

    response = client.post(
        "/users/me/push-token",
        json={"token": "ExponentPushToken[aaaaaaaaaaaaaaaaaaaaaa]"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204


def test_register_push_token_is_idempotent(client: TestClient) -> None:
    _, token = _register_and_login(client, VALID_PAYLOAD)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"token": "ExponentPushToken[aaaaaaaaaaaaaaaaaaaaaa]"}

    first = client.post("/users/me/push-token", json=payload, headers=headers)
    second = client.post("/users/me/push-token", json=payload, headers=headers)

    assert first.status_code == 204
    assert second.status_code == 204


def test_register_push_token_rejects_missing_token(client: TestClient) -> None:
    response = client.post(
        "/users/me/push-token",
        json={"token": "ExponentPushToken[aaaaaaaaaaaaaaaaaaaaaa]"},
    )

    assert response.status_code == 401


def test_upload_avatar_updates_photo_url(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, token = _register_and_login(client, VALID_PAYLOAD)
    monkeypatch.setattr(
        storage_service,
        "upload_avatar",
        lambda user_id, content, content_type: "https://cdn/avatar.jpg",
    )

    response = client.post(
        "/users/me/avatar",
        files={"file": ("avatar.jpg", b"fake-bytes", "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["photo_url"] == "https://cdn/avatar.jpg"


def test_upload_avatar_rejects_unsupported_content_type(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, token = _register_and_login(client, VALID_PAYLOAD)
    monkeypatch.setattr(
        storage_service, "upload_avatar", lambda user_id, content, content_type: "https://cdn/x"
    )

    response = client.post(
        "/users/me/avatar",
        files={"file": ("avatar.gif", b"fake-bytes", "image/gif")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_IMAGE_TYPE"


def test_upload_avatar_rejects_file_too_large(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, token = _register_and_login(client, VALID_PAYLOAD)
    oversized = b"x" * (storage_service.MAX_AVATAR_SIZE_BYTES + 1)

    response = client.post(
        "/users/me/avatar",
        files={"file": ("avatar.jpg", oversized, "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "IMAGE_TOO_LARGE"


def test_upload_avatar_returns_503_when_storage_not_configured(client: TestClient) -> None:
    _, token = _register_and_login(client, VALID_PAYLOAD)

    response = client.post(
        "/users/me/avatar",
        files={"file": ("avatar.jpg", b"fake-bytes", "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "STORAGE_NOT_CONFIGURED"


def test_upload_avatar_rejects_missing_token(client: TestClient) -> None:
    response = client.post(
        "/users/me/avatar",
        files={"file": ("avatar.jpg", b"fake-bytes", "image/jpeg")},
    )

    assert response.status_code == 401
