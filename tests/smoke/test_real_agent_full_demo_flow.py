from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.smoke._helpers import (
    combined_chat_text,
    configure_smoke_env,
    contains_any,
    has_real_llm_credentials,
)

pytestmark = [
    pytest.mark.smoke,
    pytest.mark.slow,
    pytest.mark.xfail(
        reason="Full demo flow is still being tuned; contract and minimal smoke are green.",
    ),
    pytest.mark.skipif(
        not has_real_llm_credentials(),
        reason="NVIDIA_API_KEY or OPENAI_API_KEY is required for real-agent smoke tests.",
    ),
]


def test_real_agent_full_demo_flow_via_chat_endpoint(monkeypatch, smoke_tmp_path) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_TIMEOUT_SECONDS", "300")
    configure_smoke_env(monkeypatch, smoke_tmp_path)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={
                    "user_id": "smoke-user",
                    "thread_id": "smoke-full-demo",
                    "include_trace": True,
                    "message": (
                        "Vivo en Sevilla, consumo 500 kWh al mes y tengo un tejado de 8 metros "
                        "por 5 metros. Si falta algun dato tecnico, usa un escenario orientativo "
                        "declarado en vez de pedirme cada dato por separado. Quiero una "
                        "estimacion orientativa de cuantos paneles necesito, cuantos caben "
                        "fisicamente, cuanta energia podrian producir en 25 anos, si necesito "
                        "bateria, cuanto podria ahorrar y si hay ayudas."
                    ),
                },
            )
            assert response.status_code == 200, response.text

            chat_body = response.json()
            assert chat_body["trace_id"]
            assert chat_body["answer_text"].strip()

            trace_response = client.get(f"/traces/{chat_body['trace_id']}")
            assert trace_response.status_code == 200, trace_response.text
            trace_body = trace_response.json()

            kinds = [event["kind"] for event in trace_body["events"]]
            assert "message_received" in kinds
            assert "final_answer_generated" in kinds

            combined = combined_chat_text(chat_body, trace_body).lower()
            assert contains_any(combined, "orientativ", "estim", "aproxim")
            assert "panel" in combined
            assert contains_any(combined, "caben", "fisic", "espacio")
            assert contains_any(combined, "neces", "demanda", "consumo", "energ")

            forbidden_guarantee_phrases = (
                "ayuda garantizada",
                "ayudas garantizadas",
                "subvencion garantizada",
                "subvenciones garantizadas",
                "eres elegible",
                "es elegible",
            )
            assert not any(phrase in combined for phrase in forbidden_guarantee_phrases)

            if "compens" in combined and "venta" in combined:
                assert contains_any(
                    combined,
                    "no es lo mismo",
                    "distint",
                    "venta real",
                    "no equivale",
                )

            structured = chat_body.get("structured_result") or {}
            assumptions = structured.get("assumptions_used") or []
            warnings = structured.get("warnings") or []
            assert assumptions or warnings or contains_any(
                combined,
                "supuest",
                "falt",
                "dato",
                "escenario",
            )
    finally:
        from app.core.config import get_settings
        from app.services.conversation_service import get_conversation_service

        get_settings.cache_clear()
        get_conversation_service.cache_clear()
