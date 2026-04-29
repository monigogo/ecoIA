from __future__ import annotations

from typing import Any

from app.tracing.natural_trace import NaturalTraceLogger
from app.tracing.trace_events import TraceEventKind


def test_logger_records_events_in_order() -> None:
    logger = NaturalTraceLogger(request_id="req-1")
    logger.tool_call("supervisor", "called geocode_location", location_text="Sevilla")
    logger.tool_call("supervisor", "called PVGIS PVcalc", lat=37.4, lon=-5.99)
    logger.recovery_attempt(
        "supervisor",
        "requested explicit assumptions after incomplete panel metadata",
        missing_field="panel_power_w",
    )
    logger.assumption_used(
        "degradation-analyst",
        "selected residential central degradation candidate",
        candidate_id="c2",
        confidence="medium",
    )

    events = logger.trace.events
    assert [e.kind for e in events] == [
        TraceEventKind.tool_call,
        TraceEventKind.tool_call,
        TraceEventKind.recovery_attempt,
        TraceEventKind.assumption_used,
    ]
    assert events[0].actor == "supervisor"
    assert events[1].details == {"lat": 37.4, "lon": -5.99}
    assert events[2].details["missing_field"] == "panel_power_w"
    assert events[3].details["candidate_id"] == "c2"


def test_dump_returns_serializable_dict() -> None:
    import json

    logger = NaturalTraceLogger(request_id="req-2")
    logger.warning("subsidy-finder", "result is orientative; user must verify")
    payload = logger.dump()
    json.dumps(payload, default=str)
    assert payload["request_id"] == "req-2"
    assert len(payload["events"]) == 1


def test_natural_trace_logger_add_event_is_canonical() -> None:
    logger = NaturalTraceLogger(request_id="req-add")
    event = logger.add_event(
        TraceEventKind.tool_call,
        title="supervisor",
        natural_description="Called PVGIS",
        metadata={"lat": 37.4, "lon": -5.99},
    )

    assert event.kind == TraceEventKind.tool_call
    assert event.actor == "supervisor"
    assert event.summary == "Called PVGIS"
    assert event.details == {"lat": 37.4, "lon": -5.99}
    assert logger.trace.events == [event]


def test_natural_trace_logger_add_event_metadata_defaults_to_none() -> None:
    logger = NaturalTraceLogger(request_id="req-add-2")
    event = logger.add_event(
        TraceEventKind.note,
        title="supervisor",
        natural_description="Started run",
    )

    assert event.details is None


_COMPARABLE_FIELDS = ("kind", "actor", "summary", "details")


def _comparable(event: Any) -> dict[str, Any]:
    payload = event.model_dump()
    return {field: payload[field] for field in _COMPARABLE_FIELDS}


def test_natural_trace_logger_shortcuts_delegate_to_add_event() -> None:
    logger = NaturalTraceLogger(request_id="req-shortcuts")
    via_shortcut = logger.tool_call("supervisor", "Called PVGIS", lat=37.4)
    via_canonical = logger.add_event(
        TraceEventKind.tool_call,
        title="supervisor",
        natural_description="Called PVGIS",
        metadata={"lat": 37.4},
    )

    assert _comparable(via_shortcut) == _comparable(via_canonical)


def test_natural_trace_logger_record_delegates_to_add_event() -> None:
    logger = NaturalTraceLogger(request_id="req-record")
    via_record = logger.record(
        TraceEventKind.warning,
        "supervisor",
        "subsidies orientative",
        {"source": "BDNS"},
    )
    via_canonical = logger.add_event(
        TraceEventKind.warning,
        title="supervisor",
        natural_description="subsidies orientative",
        metadata={"source": "BDNS"},
    )

    assert _comparable(via_record) == _comparable(via_canonical)


def test_natural_trace_events_keep_insertion_order_via_add_event() -> None:
    logger = NaturalTraceLogger(request_id="req-order")
    logger.add_event(TraceEventKind.note, "supervisor", "first")
    logger.add_event(TraceEventKind.tool_call, "supervisor", "second")
    logger.add_event(TraceEventKind.warning, "supervisor", "third")

    summaries = [event.summary for event in logger.trace.events]
    assert summaries == ["first", "second", "third"]


def test_natural_trace_dump_remains_json_serializable_after_add_event() -> None:
    import json

    logger = NaturalTraceLogger(request_id="req-dump-add")
    logger.add_event(
        TraceEventKind.partial_result,
        title="supervisor",
        natural_description="returned safe partial",
        metadata={"completed_blocks": ["framing"]},
    )
    payload = logger.dump()
    json.dumps(payload, default=str)
    assert payload["request_id"] == "req-dump-add"
    assert len(payload["events"]) == 1
    assert payload["events"][0]["kind"] == "partial_result"


def test_logger_accepts_summary_and_actor_inside_detail_fields() -> None:
    logger = NaturalTraceLogger(request_id="req-3")
    logger.tool_call(
        "report-synthesizer",
        "called summary tool",
        summary="user-facing summary",
        actor="inner-actor",
    )

    event = logger.trace.events[0]
    assert event.summary == "called summary tool"
    assert event.details == {
        "summary": "user-facing summary",
        "actor": "inner-actor",
    }
