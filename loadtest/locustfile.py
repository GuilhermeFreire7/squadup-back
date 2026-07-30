"""Teste de carga básico do SquadUp backend (T5).

Uso:
    locust -f loadtest/locustfile.py --host https://squadup-back.up.railway.app

Ou localmente, com o servidor rodando (`uvicorn app.main:app`):
    locust -f loadtest/locustfile.py --host http://127.0.0.1:8000

Roda em modo interativo por padrão (abre uma UI web em http://localhost:8089 para configurar
número de usuários simulados e taxa de spawn). Para rodar sem UI:
    locust -f loadtest/locustfile.py --host <url> --headless -u 50 -r 5 -t 2m
"""

import random
import uuid

from locust import HttpUser, between, task

SPORTS = ["football", "volleyball", "basketball", "tennis", "futsal"]


class SquadUpUser(HttpUser):
    wait_time = between(1, 3)
    access_token: str | None = None

    def on_start(self) -> None:
        email = f"loadtest-{uuid.uuid4()}@example.com"
        password = "senha-super-secreta"
        self.client.post(
            "/auth/register",
            json={
                "name": "Usuário de Carga",
                "email": email,
                "password": password,
                "age": 25,
                "location": "São Paulo, SP",
                "favorite_sports": [random.choice(SPORTS)],
            },
            name="/auth/register",
        )
        login_response = self.client.post(
            "/auth/login",
            json={"email": email, "password": password},
            name="/auth/login",
        )
        if login_response.status_code == 200:
            self.access_token = login_response.json()["access_token"]

    def _auth_headers(self) -> dict[str, str]:
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    @task(5)
    def health(self) -> None:
        self.client.get("/health", name="/health")

    @task(4)
    def list_matches(self) -> None:
        self.client.get(
            "/matches",
            params={"sport": random.choice(SPORTS)},
            headers=self._auth_headers(),
            name="/matches",
        )

    @task(2)
    def read_my_profile(self) -> None:
        self.client.get("/users/me", headers=self._auth_headers(), name="/users/me")

    @task(1)
    def refresh_token(self) -> None:
        self.client.get("/auth/me", headers=self._auth_headers(), name="/auth/me")
