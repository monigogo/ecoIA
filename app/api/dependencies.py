from typing import Annotated

import structlog
from fastapi import Depends, Request

from app.agents.context import SolarAgentContext, build_agent_context
from app.core.config import Settings, get_settings
from app.core.constants import REQUEST_ID_HEADER
from app.repositories.trace_repository import TraceRepository, get_trace_repository

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_request_id(request: Request) -> str:
    """Return the request id bound by ``RequestContextMiddleware``.

    Falls back to the incoming header if middleware was bypassed (e.g. in tests).
    Tools and services that need correlation should depend on this.
    """

    bound = structlog.contextvars.get_contextvars().get("request_id")
    if bound:
        return str(bound)
    return request.headers.get(REQUEST_ID_HEADER, "")


RequestIdDep = Annotated[str, Depends(get_request_id)]


def get_agent_context(request_id: RequestIdDep, settings: SettingsDep) -> SolarAgentContext:
    """Return the typed runtime context passed into the agent graph."""

    return build_agent_context(
        request_id=request_id or None,
        trace_enabled=settings.trace_enabled,
    )


AgentContextDep = Annotated[SolarAgentContext, Depends(get_agent_context)]
TraceRepositoryDep = Annotated[TraceRepository, Depends(get_trace_repository)]


def get_trace_context(agent_context: AgentContextDep) -> dict[str, str]:
    """Seed trace correlation metadata for tools/services that emit events.

    The deep-agent middleware owns the richer natural trace. This dependency
    only exposes correlation identifiers to service/tool layers.
    """

    payload: dict[str, str] = {}
    if agent_context.request_id:
        payload["request_id"] = agent_context.request_id
    if agent_context.trace_id:
        payload["trace_id"] = agent_context.trace_id
    if agent_context.thread_id:
        payload["thread_id"] = agent_context.thread_id
    return payload


TraceContextDep = Annotated[dict[str, str], Depends(get_trace_context)]
