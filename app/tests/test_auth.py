from fastapi.testclient import TestClient

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
