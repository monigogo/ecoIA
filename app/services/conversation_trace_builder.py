"""Helpers to build and normalize chat trace events."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.tracing.trace_events import TraceEventKind


def default_trace_title(kind: str, actor: str) -> str:
    return actor if kind == TraceEventKind.tool_call.value else kind


def normalize_event_timestamps(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for event in events:
        item = dict(event)
        timestamp = item.get("timestamp")
        if not isinstance(timestamp, datetime):
            item["timestamp"] = datetime.now(UTC)
        item["title"] = item.get("title") or default_trace_title(
            str(item.get("kind", "note")),
            str(item.get("actor", "event")),
        )
        normalized.append(item)
    return normalized


def build_message_received_event(message_length: int) -> dict[str, Any]:
    return {
        "kind": TraceEventKind.message_received.value,
        "actor": "chat",
        "title": "message_received",
        "summary": "Received user message for conversational planning.",
        "details": {"message_length": message_length},
        "timestamp": datetime.now(UTC),
    }


def build_warning_events(warnings: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "kind": TraceEventKind.warning.value,
            "actor": "chat",
            "title": "warning",
            "summary": warning,
            "details": None,
            "timestamp": datetime.now(UTC),
        }
        for warning in warnings
    ]


def build_failure_event(summary: str, error_detail: str) -> dict[str, Any]:
    return {
        "kind": TraceEventKind.warning.value,
        "actor": "chat",
        "title": "warning",
        "summary": summary,
        "details": {"error": error_detail},
        "timestamp": datetime.now(UTC),
    }


def build_final_answer_event(answer_text: str) -> dict[str, Any]:
    return {
        "kind": TraceEventKind.final_answer_generated.value,
        "actor": "chat",
        "title": "final_answer_generated",
        "summary": "Generated final answer for the user.",
        "details": {"answer_length": len(answer_text)},
        "timestamp": datetime.now(UTC),
    }


def _event_dicts(events: Any) -> list[dict[str, Any]]:
    if not isinstance(events, list):
        return []
    return [event for event in events if isinstance(event, dict)]


def extract_trace_events(result: Any, state_values: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(result, dict):
        events = _event_dicts(result.get("natural_trace_events"))
        if events:
            return events
    return _event_dicts(state_values.get("natural_trace_events"))


__all__ = [
    "build_failure_event",
    "build_final_answer_event",
    "build_message_received_event",
    "build_warning_events",
    "default_trace_title",
    "extract_trace_events",
    "normalize_event_timestamps",
]
