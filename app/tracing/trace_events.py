"""Natural-trace event types.

A natural trace is a sequence of small, human-readable events that
explain what the agent did and why. Distinct from structured tool calls
in LangGraph state — the natural trace is meant to be embedded in the
final response so the user can audit the reasoning.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TraceEventKind(StrEnum):
    message_received = "message_received"
    decision = "decision"
    tool_call = "tool_call"
    assumption_used = "assumption_used"
    recovery_attempt = "recovery_attempt"
    partial_result = "partial_result"
    missing_information = "missing_information"
    tool_retry = "tool_retry"
    fallback_used = "fallback_used"
    delegation = "delegation"
    warning = "warning"
    note = "note"
    final_answer_generated = "final_answer_generated"


class TraceEvent(BaseModel):
    kind: TraceEventKind
    actor: str = Field(description="Supervisor, subagent name, or tool name.")
    summary: str = Field(description="Short natural-language description of the step.")
    details: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NaturalTrace(BaseModel):
    request_id: str | None = None
    events: list[TraceEvent] = Field(default_factory=list)
