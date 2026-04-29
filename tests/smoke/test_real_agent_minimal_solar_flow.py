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
    pytest.mark.skipif(
        not has_real_llm_credentials(),
        reason="NVIDIA_API_KEY or OPENAI_API_KEY is required for real-agent smoke tests.",
    ),
]


def test_real_agent_minimal_solar_flow_via_chat_endpoint(monkeypatch, smoke_tmp_path) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_TIMEOUT_SECONDS", "120")
    configure_smoke_env(monkeypatch, smoke_tmp_path)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={
                    "user_id": "smoke-user",
                    "thread_id": "smoke-minimal-solar",
                    "include_trace": True,
                    "message": (
                        "Vivo en Sevilla y consumo 500 kWh al mes. "
                        "Para empezar una estimación solar residencial, dime solo qué datos "
                        "adicionales necesitarías antes de calcular producción, ayudas o batería."
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
            assert contains_any(combined, "sevilla", "consumo", "panel", "solar")
            assert contains_any(
                combined,
                "dato",
                "necesit",
                "inform",
                "falt",
                "estim",
                "falt",
            )
            assert "ayuda garantizada" not in combined
            assert "subvención garantizada" not in combined
    finally:
        from app.core.config import get_settings
        from app.services.conversation_service import get_conversation_service

        get_settings.cache_clear()
        get_conversation_service.cache_clear()
