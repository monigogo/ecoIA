"""Runtime context definitions for the SolarLife deep agent graph.

The runtime context is per-run metadata passed through LangGraph/Deep Agents.
It is not part of the model prompt unless middleware explicitly reads it and
injects relevant parts into the system message.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(slots=True)
class SolarAgentContext:
    """Stable per-run metadata for the supervisor and all subagents."""

    request_id: str | None = None
    trace_id: str | None = None
    thread_id: str = "default"
    user_id: str | None = None
    locale: str | None = None
    country_code: str | None = None
    trace_enabled: bool = True


def build_agent_context(
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
    thread_id: str | None = None,
    user_id: str | None = None,
    locale: str | None = None,
    country_code: str | None = None,
    trace_enabled: bool | None = None,
    settings: Settings | None = None,
) -> SolarAgentContext:
    """Build a context object for agent invocation.

    ``thread_id`` falls back to ``request_id`` when available so a caller can
    get deterministic checkpoint scoping without repeating both values.
    """

    resolved_settings = settings or get_settings()
    return SolarAgentContext(
        request_id=request_id,
        trace_id=trace_id,
        thread_id=thread_id or request_id or "default",
        user_id=user_id,
        locale=locale,
        country_code=country_code,
        trace_enabled=resolved_settings.trace_enabled if trace_enabled is None else trace_enabled,
    )


__all__ = ["SolarAgentContext", "build_agent_context"]
