"""LangChain middleware that captures a compact natural trace in agent state."""

from __future__ import annotations

from typing import Annotated, Any, NotRequired

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    PrivateStateAttr,
    ResponseT,
)
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from app.agents.output_schemas import NaturalTraceLine
from app.tracing.natural_trace import NaturalTraceLogger
from app.tracing.trace_events import TraceEvent, TraceEventKind

_REDACTED_TRACE_FIELDS = {
    "api_key",
    "authorization",
    "location_text",
    "password",
    "secret",
    "token",
}


class TraceMiddlewareState(AgentState[ResponseT]):
    """State schema for natural-trace capture."""

    natural_trace_events: NotRequired[Annotated[list[dict[str, Any]], PrivateStateAttr]]
    natural_trace_request_id: NotRequired[Annotated[str | None, PrivateStateAttr]]


class NaturalTraceMiddleware(AgentMiddleware[TraceMiddlewareState[ResponseT], ContextT, ResponseT]):
    """Capture delegations/tool calls and inject them into structured output."""

    state_schema = TraceMiddlewareState  # type: ignore[assignment]

    def __init__(self, response_schema: type[BaseModel] | None = None) -> None:
        self._response_schema = response_schema

    @staticmethod
    def _request_id(runtime: Any) -> str | None:
        context = getattr(runtime, "context", None)
        return getattr(context, "request_id", None)

    @staticmethod
    def _trace_id(runtime: Any) -> str | None:
        context = getattr(runtime, "context", None)
        return getattr(context, "trace_id", None)

    @staticmethod
    def _agent_name(runtime: Any) -> str:
        config = getattr(runtime, "config", None)
        if isinstance(config, dict):
            metadata = config.get("metadata")
            if isinstance(metadata, dict):
                node_name = metadata.get("langgraph_node") or metadata.get("lc_agent_name")
                if isinstance(node_name, str) and node_name:
                    return node_name
        return "agent"

    @staticmethod
    def _sanitize_details(details: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in details.items():
            if key in _REDACTED_TRACE_FIELDS:
                sanitized[f"{key}_redacted"] = True
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[key] = value
                continue
            if isinstance(value, list):
                sanitized[f"{key}_count"] = len(value)
                continue
            if isinstance(value, dict):
                sanitized[f"{key}_keys"] = sorted(value.keys())
                continue
            sanitized[key] = str(value)
        return sanitized

    @staticmethod
    def _load_logger(
        state: TraceMiddlewareState[ResponseT],
        request_id: str | None,
    ) -> NaturalTraceLogger:
        if state.get("natural_trace_request_id") != request_id:
            return NaturalTraceLogger(request_id=request_id)
        logger = NaturalTraceLogger(request_id=request_id)
        for raw_event in state.get("natural_trace_events", []):
            logger.trace.events.append(TraceEvent.model_validate(raw_event))
        return logger

    @staticmethod
    def _merge_structured_trace(
        logger: NaturalTraceLogger,
        payload: dict[str, Any],
    ) -> None:
        raw_lines = payload.get("natural_trace")
        if not isinstance(raw_lines, list):
            return

        for raw_line in raw_lines:
            try:
                line = NaturalTraceLine.model_validate(raw_line)
            except Exception:  # noqa: BLE001 - preserve agent output when one line is malformed
                continue
            logger.record(
                TraceEventKind(line.kind),
                line.actor,
                line.summary,
            )

    async def abefore_agent(
        self,
        state: TraceMiddlewareState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        request_id = self._request_id(runtime)
        trace_id = self._trace_id(runtime)
        logger = self._load_logger(state, trace_id or request_id)
        if logger.trace.events:
            return None
        logger.note(
            self._agent_name(runtime),
            "Started agent run",
        )
        return {
            "natural_trace_events": [event.model_dump() for event in logger.trace.events],
            "natural_trace_request_id": trace_id or request_id,
        }

    async def aafter_model(
        self,
        state: TraceMiddlewareState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        messages = state.get("messages", [])
        if not messages:
            return None

        last_ai_message = next(
            (message for message in reversed(messages) if isinstance(message, AIMessage)),
            None,
        )
        if last_ai_message is None or not last_ai_message.tool_calls:
            return None

        request_id = self._request_id(runtime)
        trace_id = self._trace_id(runtime)
        logger = self._load_logger(state, trace_id or request_id)
        actor = self._agent_name(runtime)

        for tool_call in last_ai_message.tool_calls:
            tool_name = tool_call["name"]
            raw_args = tool_call.get("args", {})
            args = raw_args if isinstance(raw_args, dict) else {}
            safe_details = self._sanitize_details(args)

            if tool_name == "task":
                logger.delegation(
                    actor,
                    "Delegated work to a specialized subagent",
                    **safe_details,
                )
            else:
                logger.tool_call(
                    tool_name,
                    f"Requested tool {tool_name}",
                    **safe_details,
                )

        return {
            "natural_trace_events": [event.model_dump() for event in logger.trace.events],
            "natural_trace_request_id": trace_id or request_id,
        }

    async def aafter_agent(
        self,
        state: TraceMiddlewareState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        request_id = self._request_id(runtime)
        trace_id = self._trace_id(runtime)
        logger = self._load_logger(state, trace_id or request_id)
        structured_response = state.get("structured_response")
        if isinstance(structured_response, BaseModel):
            payload = structured_response.model_dump()
        elif isinstance(structured_response, dict):
            payload = dict(structured_response)
        else:
            payload = None

        if payload is not None:
            self._merge_structured_trace(logger, payload)

        logger.note(
            self._agent_name(runtime),
            "Finished agent run",
        )

        trace_lines = [
            NaturalTraceLine(actor=event.actor, summary=event.summary, kind=event.kind)
            for event in logger.trace.events
        ]
        updates: dict[str, Any] = {
            "natural_trace_events": [event.model_dump() for event in logger.trace.events],
            "natural_trace_request_id": trace_id or request_id,
        }

        if payload is None:
            return updates

        payload["natural_trace"] = [line.model_dump() for line in trace_lines]

        if self._response_schema is not None:
            updates["structured_response"] = self._response_schema.model_validate(payload)
        else:
            updates["structured_response"] = payload
        return updates


__all__ = ["NaturalTraceMiddleware", "TraceMiddlewareState"]
