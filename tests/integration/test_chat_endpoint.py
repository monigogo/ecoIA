from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.core.config import get_settings
from app.main import app
from app.services.conversation_service import ConversationService, get_conversation_service


class _FakeAgent:
    def __init__(self) -> None:
        self.threads: dict[str, list[object]] = {}

    async def ainvoke(self, payload, config, context):
        thread_id = config["configurable"]["thread_id"]
        user_text = payload["messages"][0]["content"]
        history = self.threads.setdefault(thread_id, [])
        history.append(HumanMessage(content=user_text))
        history.append(AIMessage(content=f"Echo: {user_text}"))
        return {
            "messages": list(history),
            "structured_response": {
                "summary": f"Structured: {user_text}",
                "key_points": [],
                "assumptions_used": [],
                "sources": [],
                "warnings": ["orientative"],
                "natural_trace": [],
                "next_steps": [],
            },
            "natural_trace_events": [
            {
                "kind": "tool_call",
                "actor": "supervisor",
                "title": "geocode_location",
                "summary": "Requested tool geocode_location.",
                "details": {"country_hint": "ES"},
            },
            {
                "kind": "tool_call",
                "actor": "supervisor",
                "title": "estimate_solar_production_with_pvgis",
                "summary": "Requested tool estimate_solar_production_with_pvgis.",
                "details": {"lat": 37.38, "lon": -5.99},
            },
        ],
        }

    async def aget_state(self, config):
        thread_id = config["configurable"]["thread_id"]
        return SimpleNamespace(values={"messages": list(self.threads.get(thread_id, []))})


class _ExplodingAgent:
    async def ainvoke(self, payload, config, context):
        raise RuntimeError("provider malformed tool args")

    async def aget_state(self, config):
        return SimpleNamespace(values={"messages": []})


def test_chat_endpoint_returns_200_with_fake_agent() -> None:
    app.dependency_overrides[get_conversation_service] = lambda: ConversationService(agent=_FakeAgent())
    client = TestClient(app)

    try:
        response = client.post(
            "/chat",
            json={
                "user_id": "demo-user",
                "thread_id": "demo-thread",
                "message": "hola",
                "include_trace": True,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["trace_id"]
        assert body["thread_id"] == "demo-thread"
        assert body["user_id"] == "demo-user"
        assert body["answer_text"] == "Structured: hola"
        assert body["warnings"] == ["orientative"]
        assert body["structured_result"]["summary"] == "Structured: hola"
        assert body["structured_result"]["natural_trace"] == []
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_returns_controlled_error_without_model_credentials(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("NVIDIA_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    get_settings.cache_clear()
    get_conversation_service.cache_clear()
    client = TestClient(app)

    try:
        response = client.post("/chat", json={"message": "hola"})
        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "configuration_error"
        assert "OPENAI_API_KEY" in body["error"]["message"]
        assert "traceback" not in response.text.lower()
    finally:
        get_settings.cache_clear()
        get_conversation_service.cache_clear()


def test_chat_endpoint_returns_controlled_error_on_runtime_failure() -> None:
    app.dependency_overrides[get_conversation_service] = lambda: ConversationService(
        agent=_ExplodingAgent()
    )
    client = TestClient(app)

    try:
        response = client.post("/chat", json={"message": "hola", "include_trace": True})
        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "agent_execution_error"
        assert body["error"]["message"] == "The agent failed while processing the request."
        assert body["error"]["details"]["error"] == "provider malformed tool args"
        assert body["error"]["details"]["trace_id"]
        assert "traceback" not in response.text.lower()
    finally:
        app.dependency_overrides.clear()
