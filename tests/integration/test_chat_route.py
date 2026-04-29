from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.main import app
from app.services.conversation_service import get_conversation_service


class _FakeCheckpointedAgent:
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
                "warnings": [],
                "natural_trace": [],
                "next_steps": [],
            },
        }

    async def aget_state(self, config):
        thread_id = config["configurable"]["thread_id"]
        return SimpleNamespace(values={"messages": list(self.threads.get(thread_id, []))})


def test_chat_route_reuses_thread_memory_and_exposes_history() -> None:
    from app.services.conversation_service import ConversationService

    service = ConversationService(agent=_FakeCheckpointedAgent())
    app.dependency_overrides[get_conversation_service] = lambda: service
    client = TestClient(app)

    try:
        first = client.post("/chat", json={"message": "hola"})
        assert first.status_code == 200
        first_body = first.json()
        thread_id = first_body["thread_id"]
        assert first_body["answer_text"] == "Structured: hola"
        assert first_body["trace_id"]
        assert first_body["history_length"] == 2

        second = client.post("/chat", json={"message": "continua", "thread_id": thread_id})
        assert second.status_code == 200
        second_body = second.json()
        assert second_body["thread_id"] == thread_id
        assert second_body["history_length"] == 4

        history = client.get(f"/chat/{thread_id}/history")
        assert history.status_code == 200
        history_body = history.json()
        assert [message["role"] for message in history_body["messages"]] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert [message["content"] for message in history_body["messages"]] == [
            "hola",
            "Echo: hola",
            "continua",
            "Echo: continua",
        ]
    finally:
        app.dependency_overrides.clear()
