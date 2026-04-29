"""SQLite-backed repository for persisted natural traces."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from sqlmodel import Session, col, select

from app.core.errors import NotFoundAppError, ValidationAppError
from app.db.models import TraceEventRecord, TraceSessionRecord
from app.db.session import create_db_and_tables, get_engine
from app.schemas.trace import PersistedTraceEvent, TraceResponse


@dataclass(slots=True)
class TraceRepository:
    """Persistence adapter for trace sessions and trace events."""

    def create_trace_session(
        self,
        *,
        trace_id: str,
        user_id: str | None,
        thread_id: str,
        request_id: str | None,
        status: str = "started",
        final_summary: str | None = None,
    ) -> None:
        create_db_and_tables()
        with Session(get_engine()) as session:
            existing = session.get(TraceSessionRecord, trace_id)
            if existing is None:
                session.add(
                    TraceSessionRecord(
                        trace_id=trace_id,
                        user_id=user_id,
                        thread_id=thread_id,
                        request_id=request_id,
                        status=status,
                        final_summary=final_summary,
                    )
                )
            else:
                existing.user_id = user_id
                existing.thread_id = thread_id
                existing.request_id = request_id
                existing.status = status
                existing.final_summary = final_summary
                session.add(existing)
            session.commit()

    def append_events(
        self,
        *,
        trace_id: str,
        events: list[dict[str, Any]],
        start_sequence_number: int,
    ) -> int:
        if not events:
            return start_sequence_number

        create_db_and_tables()
        with Session(get_engine()) as session:
            for offset, event in enumerate(events):
                session.add(
                    TraceEventRecord(
                        trace_id=trace_id,
                        sequence_number=start_sequence_number + offset,
                        timestamp=event["timestamp"],
                        kind=str(event["kind"]),
                        title=event.get("title") or str(event.get("actor", "event")),
                        natural_description=str(event.get("summary", "")),
                        metadata_json=event.get("details"),
                    )
                )
            session.commit()
        return start_sequence_number + len(events)

    def update_trace_session(
        self,
        *,
        trace_id: str,
        status: str,
        final_summary: str | None = None,
    ) -> None:
        create_db_and_tables()
        with Session(get_engine()) as session:
            record = session.get(TraceSessionRecord, trace_id)
            if record is None:
                raise ValidationAppError(
                    "Trace session does not exist.",
                    details={"trace_id": trace_id},
                )
            record.status = status
            record.final_summary = final_summary
            session.add(record)
            session.commit()

    def get_trace(self, trace_id: str) -> TraceResponse:
        create_db_and_tables()
        with Session(get_engine()) as session:
            record = session.get(TraceSessionRecord, trace_id)
            if record is None:
                raise NotFoundAppError(
                    "Trace not found.",
                    details={"trace_id": trace_id},
                )
            events = session.exec(
                select(TraceEventRecord)
                .where(TraceEventRecord.trace_id == trace_id)
                .order_by(col(TraceEventRecord.sequence_number))
            ).all()

        return TraceResponse(
            trace_id=record.trace_id,
            user_id=record.user_id,
            thread_id=record.thread_id,
            request_id=record.request_id,
            created_at=record.created_at,
            status=record.status,  # type: ignore[arg-type]
            final_summary=record.final_summary,
            events=[
                PersistedTraceEvent(
                    event_id=event.event_id,
                    timestamp=event.timestamp,
                    kind=event.kind,
                    title=event.title,
                    natural_description=event.natural_description,
                    metadata=event.metadata_json,
                )
                for event in events
            ],
        )


@lru_cache(maxsize=1)
def get_trace_repository() -> TraceRepository:
    return TraceRepository()


__all__ = ["TraceRepository", "get_trace_repository"]
