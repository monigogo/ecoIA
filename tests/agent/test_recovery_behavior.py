from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.prompts import SUPERVISOR_PROMPT
from app.repositories.trace_repository import get_trace_repository
from app.schemas.chat import ChatRequest
from app.services.conversation_service import ConversationService


class _RecoveryAgent:
    def __init__(self) -> None:
        self.threads: dict[str, list[object]] = {}

    async def ainvoke(self, payload, config, context):
        thread_id = config["configurable"]["thread_id"]
        user_text = payload["messages"][0]["content"]
        history = self.threads.setdefault(thread_id, [])
        history.append(HumanMessage(content=user_text))
        history.append(
            AIMessage(
                content=(
                    "Puedo darte una estimación orientativa parcial, pero todavía faltan "
                    "potencia y dimensiones del panel para cerrar producción y encaje."
                )
            )
        )
        return {
            "messages": list(history),
            "structured_response": {
                "summary": (
                    "Estimación orientativa parcial: faltan potencia y dimensiones del panel. "
                    "Puedo continuar con supuestos explícitos o si compartes una ficha técnica."
                ),
                "key_points": [
                    "Se identificaron datos faltantes antes de fabricar una producción anual.",
                ],
                "assumptions_used": [],
                "sources": [],
                "warnings": [
                    "Resultado parcial: aún falta potencia del panel y dimensiones físicas.",
                ],
"natural_trace": [
            {
                "actor": "supervisor",
                "summary": "Detected missing panel metadata before calling PVGIS.",
                "kind": "missing_information",
            },
            {
                "actor": "supervisor",
                "summary": "Offered explicit scenarios instead of inventing panel specifications.",
                "kind": "recovery_attempt",
            },
            {
                "actor": "supervisor",
                "summary": "Returned only the safe partial result available from the user data.",
                "kind": "partial_result",
            },
        ],
                "next_steps": [
                    "Indica potencia del panel en W o permite usar escenarios explícitos.",
                ],
            },
            "natural_trace_events": [
            {
                "kind": "missing_information",
                "actor": "supervisor",
                "title": "missing_information",
                "summary": "Panel wattage and dimensions were still missing.",
                "details": {"fields": ["panel_power_w", "panel_width_m", "panel_height_m"]},
            },
            {
                "kind": "recovery_attempt",
                "actor": "supervisor",
                "title": "recovery_attempt",
                "summary": "Switched to explicit scenarios instead of applying silent defaults.",
                "details": {"strategy": "assumption_candidates_or_user_followup"},
            },
            {
                "kind": "partial_result",
                "actor": "supervisor",
                "title": "partial_result",
                "summary": "Returned the safe subset of the solar layout answer.",
                "details": {"completed_blocks": ["problem_framing"]},
            },
        ],
        }

    async def aget_state(self, config):
        thread_id = config["configurable"]["thread_id"]
        return SimpleNamespace(values={"messages": list(self.threads.get(thread_id, []))})


def test_supervisor_prompt_includes_graceful_recovery_rule() -> None:
    prompt = SUPERVISOR_PROMPT.lower()
    assert "safe recovery" in prompt or "do not stop immediately" in prompt
    assert "smallest missing input" in prompt or "missing input" in prompt
    assert "never invent values to recover" in prompt or "never invent" in prompt


async def test_chat_recovery_flow_persists_recovery_events() -> None:
    repository = get_trace_repository()
    service = ConversationService(agent=_RecoveryAgent(), trace_repository=repository)

    response = await service.chat(
        ChatRequest(
            user_id="demo-user",
            thread_id="demo-thread-recovery",
            message="Vivo en Sevilla y quiero saber cuántos paneles necesito y cuánto ahorraré.",
            include_trace=True,
        ),
        request_id="req-recovery",
    )

    assert response.trace_id
    assert response.answer_text
    assert "orientativa" in response.answer_text.lower()
    assert response.structured_result is not None
    assert response.structured_result.warnings
    assert any("falt" in warning.lower() for warning in response.structured_result.warnings)

    trace = repository.get_trace(response.trace_id)
    kinds = [event.kind for event in trace.events]

    assert "missing_information" in kinds
    assert "recovery_attempt" in kinds
    assert "partial_result" in kinds
    assert "final_answer_generated" in kinds
