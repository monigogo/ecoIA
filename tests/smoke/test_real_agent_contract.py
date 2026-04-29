from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.smoke._helpers import configure_smoke_env, has_real_llm_credentials

pytestmark = [
    pytest.mark.smoke,
    pytest.mark.skipif(
        not has_real_llm_credentials(),
        reason="NVIDIA_API_KEY or OPENAI_API_KEY is required for real-agent smoke tests.",
    ),
]


def test_real_agent_chat_contract_via_chat_endpoint(monkeypatch, smoke_tmp_path) -> None:
    configure_smoke_env(monkeypatch, smoke_tmp_path)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={
                    "user_id": "smoke-user",
                    "thread_id": "smoke-contract",
                    "include_trace": True,
                    "message": "Hola, explícame brevemente qué puedes hacer.",
                },
            )
            assert response.status_code == 200, response.text

            chat_body = response.json()
            assert chat_body["trace_id"]
            assert chat_body["thread_id"] == "smoke-contract"
            assert chat_body["answer_text"].strip()
            assert "traceback" not in response.text.lower()

            trace_response = client.get(f"/traces/{chat_body['trace_id']}")
            assert trace_response.status_code == 200, trace_response.text
            trace_body = trace_response.json()
            kinds = [event["kind"] for event in trace_body["events"]]
            assert "message_received" in kinds
            assert "final_answer_generated" in kinds
    finally:
        from app.core.config import get_settings
        from app.services.conversation_service import get_conversation_service

        get_settings.cache_clear()
        get_conversation_service.cache_clear()
