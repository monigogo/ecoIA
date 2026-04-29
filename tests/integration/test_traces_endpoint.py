from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.main import app
from app.services.conversation_service import ConversationService, get_conversation_service


class _TraceAgent:
    def __init__(self) -> None:
        self.threads: dict[str, list[object]] = {}

    async def ainvoke(self, payload, config, context):
        thread_id = config["configurable"]["thread_id"]
        user_text = payload["messages"][0]["content"]
        history = self.threads.setdefault(thread_id, [])
        history.append(HumanMessage(content=user_text))
        history.append(AIMessage(content="respuesta"))
        return {
            "messages": list(history),
            "structured_response": {
                "summary": "respuesta",
                "key_points": [],
                "assumptions_used": [],
                "sources": [],
                "warnings": [],
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


def test_get_trace_returns_events_in_order() -> None:
    app.dependency_overrides[get_conversation_service] = lambda: ConversationService(agent=_TraceAgent())
    client = TestClient(app)

    try:
        chat = client.post("/chat", json={"message": "hola", "thread_id": "trace-thread"})
        assert chat.status_code == 200
        trace_id = chat.json()["trace_id"]

        trace = client.get(f"/traces/{trace_id}")
        assert trace.status_code == 200
        body = trace.json()
        assert body["trace_id"] == trace_id
        assert body["status"] == "completed"
        assert [event["kind"] for event in body["events"]] == [
            "message_received",
            "tool_call",
            "tool_call",
            "final_answer_generated",
        ]
        assert all("title" in event for event in body["events"])
        assert all("natural_description" in event for event in body["events"])
    finally:
        app.dependency_overrides.clear()


def test_get_trace_returns_404_for_missing_trace() -> None:
    client = TestClient(app)
    response = client.get("/traces/trace-does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
