from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.main import app
from app.services.conversation_service import ConversationService, get_conversation_service


class _RecoveryEndpointAgent:
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
                    "Puedo continuar con una estimación orientativa, pero necesito consumo "
                    "anual o permiso para usar escenarios explícitos."
                )
            )
        )
        return {
            "messages": list(history),
            "structured_response": {
                "summary": (
                    "Resultado parcial orientativo: falta consumo anual explícito para cerrar "
                    "la parte económica."
                ),
                "key_points": ["Se ofrecieron escenarios en lugar de inventar consumo."],
                "assumptions_used": [],
                "sources": [],
                "warnings": ["Falta información de consumo y precio eléctrico."],
                "natural_trace": [
                    {
                        "actor": "energy-economics-advisor",
                        "summary": "Asked for the smallest missing economic inputs.",
                        "kind": "missing_information",
                    },
                    {
                        "actor": "energy-economics-advisor",
                        "summary": "Kept the answer partial instead of fabricating a bill-impact result.",
                        "kind": "partial_result",
                    },
                ],
                "next_steps": ["Comparte factura o permite escenarios explícitos de consumo."],
            },
            "natural_trace_events": [
                {
                    "kind": "recovery_attempt",
                    "actor": "energy-economics-advisor",
                    "title": "recovery_attempt",
                    "summary": "Switched to a partial economic answer with follow-up questions.",
                    "details": {"missing": ["annual_consumption_kwh", "import_price_eur_kwh"]},
                },
                {
                    "kind": "missing_information",
                    "actor": "energy-economics-advisor",
                    "title": "missing_information",
                    "summary": "Explicit consumption and contract price were missing.",
                    "details": {"missing_count": 2},
                },
                {
                    "kind": "partial_result",
                    "actor": "energy-economics-advisor",
                    "title": "partial_result",
                    "summary": "Returned only the safe planning guidance available.",
                    "details": {"returned_sections": ["next_steps", "warnings"]},
                },
            ],
        }

    async def aget_state(self, config):
        thread_id = config["configurable"]["thread_id"]
        return SimpleNamespace(values={"messages": list(self.threads.get(thread_id, []))})


def test_chat_endpoint_returns_partial_recovery_answer_and_trace() -> None:
    app.dependency_overrides[get_conversation_service] = lambda: ConversationService(
        agent=_RecoveryEndpointAgent()
    )
    client = TestClient(app)

    try:
        chat = client.post(
            "/chat",
            json={
                "message": "Vivo en Sevilla y quiero saber cuánto ahorraré.",
                "thread_id": "recovery-thread",
                "include_trace": True,
            },
        )
        assert chat.status_code == 200
        body = chat.json()
        assert body["trace_id"]
        assert body["answer_text"]
        assert "orientativ" in body["answer_text"].lower()
        assert body["structured_result"]["warnings"]

        trace = client.get(f"/traces/{body['trace_id']}")
        assert trace.status_code == 200
        trace_body = trace.json()
        kinds = [event["kind"] for event in trace_body["events"]]
        assert "message_received" in kinds
        assert "recovery_attempt" in kinds
        assert "missing_information" in kinds
        assert "partial_result" in kinds
        assert "final_answer_generated" in kinds
    finally:
        app.dependency_overrides.clear()
