from fastapi.testclient import TestClient

from app.core.constants import REQUEST_ID_HEADER
from app.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body and body["service"]
    assert "environment" in body and body["environment"]


def test_health_emits_request_id_header() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert REQUEST_ID_HEADER in response.headers
    assert response.headers[REQUEST_ID_HEADER]


def test_health_echoes_provided_request_id() -> None:
    client = TestClient(app)
    response = client.get("/health", headers={REQUEST_ID_HEADER: "abc-123"})
    assert response.headers[REQUEST_ID_HEADER] == "abc-123"
