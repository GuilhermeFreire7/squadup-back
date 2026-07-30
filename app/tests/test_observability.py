import os

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_health_response_includes_request_id_header() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]


def test_health_response_propagates_client_request_id() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"X-Request-ID": "custom-request-id"})

    assert response.headers["x-request-id"] == "custom-request-id"


def test_metrics_endpoint_returns_prometheus_exposition_format() -> None:
    client = TestClient(app)
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_metrics_endpoint_requires_token_when_configured(client: TestClient) -> None:
    os.environ["METRICS_TOKEN"] = "secret-token"
    try:
        get_settings.cache_clear()

        response = client.get("/metrics")
        authorized_response = client.get("/metrics", headers={"X-Metrics-Token": "secret-token"})

        assert response.status_code == 401
        assert authorized_response.status_code == 200
    finally:
        del os.environ["METRICS_TOKEN"]
        get_settings.cache_clear()
