from __future__ import annotations

from app.agents.context import SolarAgentContext, build_agent_context
from app.core.config import Settings


def test_build_agent_context_uses_request_id_as_thread_fallback() -> None:
    context = build_agent_context(
        request_id="req-123",
        settings=Settings(_env_file=None, trace_enabled=True),  # type: ignore[call-arg]
    )
    assert isinstance(context, SolarAgentContext)
    assert context.request_id == "req-123"
    assert context.thread_id == "req-123"
    assert context.trace_enabled is True


def test_build_agent_context_allows_explicit_thread_id_override() -> None:
    context = build_agent_context(
        request_id="req-123",
        thread_id="thread-9",
        locale="es-ES",
        settings=Settings(_env_file=None, trace_enabled=True),  # type: ignore[call-arg]
    )
    assert context.thread_id == "thread-9"
    assert context.locale == "es-ES"
