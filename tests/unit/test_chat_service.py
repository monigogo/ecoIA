from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.core.errors import AgentExecutionError
from app.schemas.chat import ChatRequest
from app.services.conversation_service import ConversationService as ChatService


class _FakeCheckpointedAgent:
    def __init__(self, *, include_structured_response: bool = True) -> None:
        self.include_structured_response = include_structured_response
        self.threads: dict[str, list[object]] = {}
        self.calls: list[dict[str, object]] = []

    async def ainvoke(self, payload, config, context):
        thread_id = config["configurable"]["thread_id"]
        user_text = payload["messages"][0]["content"]
        history = self.threads.setdefault(thread_id, [])
        history.append(HumanMessage(content=user_text))
        history.append(AIMessage(content=f"Echo: {user_text}"))
        self.calls.append(
            {
                "thread_id": thread_id,
                "request_id": getattr(context, "request_id", None),
                "user_id": getattr(context, "user_id", None),
                "locale": getattr(context, "locale", None),
                "country_code": getattr(context, "country_code", None),
            }
        )
        result = {"messages": list(history)}
        if self.include_structured_response:
            result["structured_response"] = {
                "summary": f"Structured: {user_text}",
                "key_points": [],
                "assumptions_used": [],
                "sources": [],
                "warnings": [],
                "natural_trace": [],
                "next_steps": [],
            }
        return result

    async def aget_state(self, config):
        thread_id = config["configurable"]["thread_id"]
        return SimpleNamespace(values={"messages": list(self.threads.get(thread_id, []))})


class _FailingAgent:
    async def ainvoke(self, payload, config, context):
        raise RuntimeError("model down")

    async def aget_state(self, config):
        return SimpleNamespace(values={"messages": []})


class _SyncCheckpointedAgent:
    def __init__(self) -> None:
        self.threads: dict[str, list[object]] = {}

    def invoke(self, payload, config=None, context=None):
        thread_id = config["configurable"]["thread_id"]
        user_text = payload["messages"][0]["content"]
        history = self.threads.setdefault(thread_id, [])
        history.append(HumanMessage(content=user_text))
        history.append(AIMessage(content=f"Echo sync: {user_text}"))
        return {"messages": list(history)}

    def get_state(self, config=None):
        thread_id = config["configurable"]["thread_id"]
        return SimpleNamespace(values={"messages": list(self.threads.get(thread_id, []))})


async def test_chat_service_uses_thread_scoped_short_term_memory() -> None:
    agent = _FakeCheckpointedAgent()
    service = ChatService(agent=agent)

    first = await service.chat(
        ChatRequest(message="hola", user_id="user-1", locale="es-ES", country_code="ES"),
        request_id="req-1",
    )
    second = await service.chat(
        ChatRequest(message="sigue", thread_id=first.thread_id, user_id="user-1"),
        request_id="req-2",
    )

    assert first.thread_id == second.thread_id
    assert first.trace_id
    assert second.trace_id
    assert first.message == "Structured: hola"
    assert second.message == "Structured: sigue"
    assert first.history_length == 2
    assert second.history_length == 4
    assert agent.calls[0] == {
        "thread_id": first.thread_id,
        "request_id": "req-1",
        "user_id": "user-1",
        "locale": "es-ES",
        "country_code": "ES",
    }
    assert agent.calls[1]["thread_id"] == first.thread_id


async def test_chat_service_falls_back_to_last_ai_message_when_no_structured_response() -> None:
    service = ChatService(agent=_FakeCheckpointedAgent(include_structured_response=False))

    response = await service.chat(ChatRequest(message="hola"), request_id="req-1")

    assert response.message == "Echo: hola"
    assert response.structured_response is None
    assert response.trace_id


async def test_chat_service_wraps_agent_failures() -> None:
    service = ChatService(agent=_FailingAgent())

    with pytest.raises(AgentExecutionError) as exc_info:
        await service.chat(ChatRequest(message="hola"), request_id="req-1")

    assert exc_info.value.details["error"] == "model down"
    assert exc_info.value.details["trace_id"]


async def test_chat_service_uses_sync_graph_api_when_available() -> None:
    service = ChatService(agent=_SyncCheckpointedAgent())

    response = await service.chat(ChatRequest(message="hola", thread_id="thread-sync"))

    assert response.thread_id == "thread-sync"
    assert response.message == "Echo sync: hola"
    assert response.history_length == 2
    assert response.trace_id
