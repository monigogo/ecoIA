"""Schemas for persisted natural trace API surfaces."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TraceStatus = Literal["started", "completed", "failed"]


class PersistedTraceEvent(BaseModel):
    """One persisted trace event."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    timestamp: datetime
    kind: str
    title: str
    natural_description: str
    metadata: dict[str, Any] | None = None


class TraceResponse(BaseModel):
    """Detailed persisted trace response."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    user_id: str | None = None
    thread_id: str
    request_id: str | None = None
    created_at: datetime
    status: TraceStatus
    final_summary: str | None = None
    events: list[PersistedTraceEvent] = Field(default_factory=list)


__all__ = ["PersistedTraceEvent", "TraceResponse", "TraceStatus"]
