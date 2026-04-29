from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage

from app.agents.context import SolarAgentContext
from app.agents.output_schemas import SubagentStructuredResponse
from app.tracing.trace_middleware import NaturalTraceMiddleware


def _runtime() -> SimpleNamespace:
    return SimpleNamespace(
        context=SolarAgentContext(request_id="req-trace", thread_id="thread-trace"),
        config={"metadata": {"langgraph_node": "degradation-analyst"}},
    )


async def test_trace_middleware_records_tool_calls_without_raw_location_text() -> None:
    middleware = NaturalTraceMiddleware()
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "name": "geocode_location",
                        "args": {"location_text": "Sevilla, España", "country_hint": "ES"},
                    }
                ],
            )
        ]
    }

    await middleware.abefore_agent(state, _runtime())
    updates = await middleware.aafter_model(state, _runtime())

    assert updates is not None
    assert updates["natural_trace_request_id"] == "req-trace"
    details = updates["natural_trace_events"][-1]["details"]
    assert details["country_hint"] == "ES"
    assert details["location_text_redacted"] is True
    assert "location_text" not in details


async def test_trace_middleware_renames_reserved_tool_arg_names() -> None:
    middleware = NaturalTraceMiddleware()
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "name": "task",
                        "args": {"summary": "delegate this", "actor": "planner", "kind": "task"},
                    }
                ],
            )
        ]
    }

    await middleware.abefore_agent(state, _runtime())
    updates = await middleware.aafter_model(state, _runtime())

    assert updates is not None
    details = updates["natural_trace_events"][-1]["details"]
    assert details["summary"] == "delegate this"
    assert details["actor"] == "planner"
    assert details["kind"] == "task"


async def test_trace_middleware_injects_natural_trace_into_structured_response() -> None:
    middleware = NaturalTraceMiddleware(response_schema=SubagentStructuredResponse)
    runtime = _runtime()
    state = {
        "messages": [],
        "structured_response": SubagentStructuredResponse(summary="done"),
    }

    before = await middleware.abefore_agent(state, runtime)
    assert before is not None
    state.update(before)

    after = await middleware.aafter_agent(state, runtime)

    assert after is not None
    response = after["structured_response"]
    assert isinstance(response, SubagentStructuredResponse)
    assert [line.summary for line in response.natural_trace] == [
        "Started agent run",
        "Finished agent run",
    ]
    assert [line.kind for line in response.natural_trace] == ["note", "note"]


async def test_trace_middleware_merges_model_supplied_recovery_lines() -> None:
    middleware = NaturalTraceMiddleware(response_schema=SubagentStructuredResponse)
    runtime = _runtime()
    state = {
        "messages": [],
        "structured_response": SubagentStructuredResponse(
            summary="faltan datos",
            natural_trace=[
                {
                    "actor": "supervisor",
                    "summary": "Asked for panel wattage before estimating annual production.",
                    "kind": "missing_information",
                },
                {
                    "actor": "supervisor",
                    "summary": "Returned partial layout result while production remains pending.",
                    "kind": "partial_result",
                },
            ],
        ),
    }

    before = await middleware.abefore_agent(state, runtime)
    assert before is not None
    state.update(before)

    after = await middleware.aafter_agent(state, runtime)

    assert after is not None
    response = after["structured_response"]
    assert isinstance(response, SubagentStructuredResponse)
    assert [line.kind for line in response.natural_trace] == [
        "note",
        "missing_information",
        "partial_result",
        "note",
    ]
    assert [event["kind"] for event in after["natural_trace_events"]] == [
        "note",
        "missing_information",
        "partial_result",
        "note",
    ]


async def test_trace_state_has_single_canonical_event_key() -> None:
    middleware = NaturalTraceMiddleware(response_schema=SubagentStructuredResponse)
    runtime = _runtime()
    state = {
        "messages": [],
        "structured_response": SubagentStructuredResponse(summary="done"),
    }

    before = await middleware.abefore_agent(state, runtime)
    assert before is not None
    assert "natural_trace_events" in before
    assert "trace_events_for_persistence" not in before

    state.update(before)
    after = await middleware.aafter_agent(state, runtime)

    assert after is not None
    assert "natural_trace_events" in after
    assert "trace_events_for_persistence" not in after
