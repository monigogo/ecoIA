from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from app.repositories.trace_repository import get_trace_repository
from app.schemas.chat import ChatRequest
from app.services.conversation_service import ConversationService


class _ReasoningFlowAgent:
    def __init__(self) -> None:
        self.threads: dict[str, list[object]] = {}

    async def ainvoke(self, payload, config, context):
        thread_id = config["configurable"]["thread_id"]
        user_text = payload["messages"][0]["content"]
        history = self.threads.setdefault(thread_id, [])
        history.append(HumanMessage(content=user_text))
        history.append(AIMessage(content="resultado final"))
        return {
            "messages": list(history),
            "structured_response": {
                "summary": "resultado final",
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
                "details": {"location_text": "Sevilla"},
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


async def test_chat_reasoning_flow_persists_tool_calls_and_final_answer() -> None:
    repository = get_trace_repository()
    service = ConversationService(agent=_ReasoningFlowAgent(), trace_repository=repository)

    response = await service.chat(
        ChatRequest(
            user_id="demo-user",
            thread_id="demo-thread-reasoning",
            message="Planifica una instalación solar en Sevilla.",
        ),
        request_id="req-reasoning",
    )

    trace = repository.get_trace(response.trace_id)
    kinds = [event.kind for event in trace.events]

    assert "tool_call" in kinds
    assert "final_answer_generated" in kinds
    assert kinds.index("tool_call") < kinds.index("final_answer_generated")
