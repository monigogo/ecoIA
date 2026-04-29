from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.guardrails import NonEmptyStructuredResponseMiddleware, build_guardrail_middleware
from app.agents.output_schemas import SubagentStructuredResponse
from app.core.config import get_settings


def test_build_guardrail_middleware_can_enable_human_in_the_loop(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENT_HUMAN_IN_THE_LOOP_ENABLED", "true")
    monkeypatch.setenv("AGENT_HUMAN_IN_THE_LOOP_TOOLS", '["search_subsidies"]')
    get_settings.cache_clear()

    middleware = build_guardrail_middleware(response_schema=SubagentStructuredResponse)

    assert "HumanInTheLoopMiddleware" in [item.__class__.__name__ for item in middleware]
    get_settings.cache_clear()


def _empty_response_request() -> object:
    return type(
        "Req",
        (),
        {
            "messages": [HumanMessage(content="hola")],
            "runtime": object(),
        },
    )()


def test_empty_structured_response_does_not_loop() -> None:
    middleware = NonEmptyStructuredResponseMiddleware(response_schema=SubagentStructuredResponse)
    attempts = {"count": 0}

    def handler(_request):
        attempts["count"] += 1
        return type(
            "Resp",
            (),
            {
                "result": [AIMessage(content="Resumen util")],
                "structured_response": SubagentStructuredResponse(summary=""),
            },
        )()

    response = middleware.wrap_model_call(_empty_response_request(), handler)

    assert attempts["count"] == 1
    assert response.structured_response.summary == "Resumen util"


def test_non_empty_structured_response_middleware_uses_model_text_on_empty_summary() -> None:
    middleware = NonEmptyStructuredResponseMiddleware(response_schema=SubagentStructuredResponse)

    def handler(_request):
        return type(
            "Resp",
            (),
            {
                "result": [AIMessage(content="Resumen desde el modelo")],
                "structured_response": SubagentStructuredResponse(summary=""),
            },
        )()

    response = middleware.wrap_model_call(_empty_response_request(), handler)

    assert response.structured_response.summary == "Resumen desde el modelo"


def test_non_empty_structured_response_middleware_keeps_empty_summary_when_model_text_is_empty() -> None:
    middleware = NonEmptyStructuredResponseMiddleware(response_schema=SubagentStructuredResponse)

    def handler(_request):
        return type(
            "Resp",
            (),
            {
                "result": [AIMessage(content="")],
                "structured_response": SubagentStructuredResponse(summary=""),
            },
        )()

    response = middleware.wrap_model_call(_empty_response_request(), handler)

    assert response.structured_response.summary == ""


def test_non_empty_structured_response_middleware_passes_through_non_empty() -> None:
    middleware = NonEmptyStructuredResponseMiddleware(response_schema=SubagentStructuredResponse)
    attempts = {"count": 0}

    def handler(_request):
        attempts["count"] += 1
        return type(
            "Resp",
            (),
            {
                "result": [AIMessage(content="Resumen util")],
                "structured_response": SubagentStructuredResponse(summary="Resumen util"),
            },
        )()

    response = middleware.wrap_model_call(_empty_response_request(), handler)

    assert attempts["count"] == 1
    assert response.structured_response.summary == "Resumen util"
