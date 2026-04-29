"""SQLModel tables for persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TraceSessionRecord(SQLModel, table=True):
    __tablename__ = "trace_sessions"

    trace_id: str = Field(primary_key=True)
    user_id: str | None = Field(default=None, index=True)
    thread_id: str = Field(index=True)
    request_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=_utcnow, index=True)
    status: str = Field(index=True)
    final_summary: str | None = None


class TraceEventRecord(SQLModel, table=True):
    __tablename__ = "trace_events"

    event_id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    trace_id: str = Field(index=True, foreign_key="trace_sessions.trace_id")
    sequence_number: int = Field(index=True)
    timestamp: datetime = Field(default_factory=_utcnow, index=True)
    kind: str = Field(index=True)
    title: str
    natural_description: str
    metadata_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata_json", JSON, nullable=True),
    )


__all__ = ["TraceEventRecord", "TraceSessionRecord"]
