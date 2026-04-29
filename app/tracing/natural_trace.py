"""NaturalTraceLogger — minimal in-memory implementation.

Step 5 stub: enough surface for the agent layer to record events. A
later step will persist traces and integrate them with the supervisor's
middleware so events emit automatically. For now, callers (subagents,
tools) append events explicitly.
"""

from __future__ import annotations

from typing import Any

from app.tracing.trace_events import NaturalTrace, TraceEvent, TraceEventKind


class NaturalTraceLogger:
    """Append-only natural-language trace bound to a request id."""

    def __init__(
        self,
        request_id: str | None = None,
        *,
        trace_id: str | None = None,
        thread_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        self._trace = NaturalTrace(request_id=request_id)
        self.trace_id = trace_id
        self.thread_id = thread_id
        self.user_id = user_id

    def add_event(
        self,
        kind: TraceEventKind,
        title: str,
        natural_description: str,
        metadata: dict[str, Any] | None = None,
    ) -> TraceEvent:
        """Canonical entry point: append a single trace event.

        ``title`` maps to :class:`TraceEvent.actor` (the source/label of the
        event) and ``natural_description`` maps to :class:`TraceEvent.summary`.
        ``metadata`` maps to :class:`TraceEvent.details`. The mapping keeps
        ``TraceEvent`` Pydantic schema unchanged while exposing a name-cleaner
        public API. ``record`` and the typed shortcuts below delegate here.
        """

        event = TraceEvent(
            kind=kind,
            actor=title,
            summary=natural_description,
            details=metadata,
        )
        self._trace.events.append(event)
        return event

    def record(
        self,
        event_kind: TraceEventKind,
        event_actor: str,
        message: str,
        detail_fields: dict[str, Any] | None = None,
    ) -> TraceEvent:
        return self.add_event(event_kind, event_actor, message, detail_fields)

    # Convenience shortcuts -------------------------------------------------

    def decision(self, event_actor: str, message: str, **detail_fields: Any) -> TraceEvent:
        return self.add_event(TraceEventKind.decision, event_actor, message, detail_fields or None)

    def assumption_used(self, event_actor: str, message: str, **detail_fields: Any) -> TraceEvent:
        return self.add_event(
            TraceEventKind.assumption_used, event_actor, message, detail_fields or None
        )

    def recovery_attempt(self, event_actor: str, message: str, **detail_fields: Any) -> TraceEvent:
        return self.add_event(
            TraceEventKind.recovery_attempt, event_actor, message, detail_fields or None
        )

    def partial_result(self, event_actor: str, message: str, **detail_fields: Any) -> TraceEvent:
        return self.add_event(
            TraceEventKind.partial_result, event_actor, message, detail_fields or None
        )

    def missing_information(
        self,
        event_actor: str,
        message: str,
        **detail_fields: Any,
    ) -> TraceEvent:
        return self.add_event(
            TraceEventKind.missing_information, event_actor, message, detail_fields or None
        )

    def tool_retry(self, event_actor: str, message: str, **detail_fields: Any) -> TraceEvent:
        return self.add_event(
            TraceEventKind.tool_retry, event_actor, message, detail_fields or None
        )

    def fallback_used(self, event_actor: str, message: str, **detail_fields: Any) -> TraceEvent:
        return self.add_event(
            TraceEventKind.fallback_used, event_actor, message, detail_fields or None
        )

    def tool_call(self, event_actor: str, message: str, **detail_fields: Any) -> TraceEvent:
        return self.add_event(
            TraceEventKind.tool_call, event_actor, message, detail_fields or None
        )

    def delegation(self, event_actor: str, message: str, **detail_fields: Any) -> TraceEvent:
        return self.add_event(
            TraceEventKind.delegation, event_actor, message, detail_fields or None
        )

    def warning(self, event_actor: str, message: str, **detail_fields: Any) -> TraceEvent:
        return self.add_event(TraceEventKind.warning, event_actor, message, detail_fields or None)

    def note(self, event_actor: str, message: str, **detail_fields: Any) -> TraceEvent:
        return self.add_event(TraceEventKind.note, event_actor, message, detail_fields or None)

    # Access ----------------------------------------------------------------

    @property
    def trace(self) -> NaturalTrace:
        return self._trace

    def dump(self) -> dict[str, Any]:
        payload = self._trace.model_dump()
        if self.trace_id:
            payload["trace_id"] = self.trace_id
        if self.thread_id:
            payload["thread_id"] = self.thread_id
        if self.user_id:
            payload["user_id"] = self.user_id
        return payload
