from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core.errors import (
    AgentExecutionError,
    ExternalServiceError,
    ToolExecutionError,
    ValidationAppError,
)
from app.main import create_app


def _app_with_failing_routes() -> TestClient:
    app = create_app()
    router = APIRouter()

    @router.get("/_test/validation")
    def _validation() -> None:
        raise ValidationAppError("bad input", details={"field": "consumption_kwh"})

    @router.get("/_test/external")
    def _external() -> None:
        raise ExternalServiceError("PVGIS down")

    @router.get("/_test/agent")
    def _agent() -> None:
        raise AgentExecutionError("agent could not plan")

    @router.get("/_test/tool")
    def _tool() -> None:
        raise ToolExecutionError("tool crashed")

    @router.get("/_test/boom")
    def _boom() -> None:
        raise RuntimeError("boom")

    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def test_validation_error_envelope() -> None:
    client = _app_with_failing_routes()
    response = client.get("/_test/validation")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "bad input"
    assert body["error"]["details"] == {"field": "consumption_kwh"}


def test_external_service_error_maps_to_502() -> None:
    client = _app_with_failing_routes()
    response = client.get("/_test/external")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "external_service_error"


def test_agent_execution_error_maps_to_500() -> None:
    client = _app_with_failing_routes()
    response = client.get("/_test/agent")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "agent_execution_error"


def test_tool_execution_error_maps_to_500() -> None:
    client = _app_with_failing_routes()
    response = client.get("/_test/tool")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "tool_execution_error"


def test_unexpected_error_is_masked() -> None:
    client = _app_with_failing_routes()
    response = client.get("/_test/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Unexpected server error"
