"""SolarLife-specific Deep Agents middleware assembly."""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import dynamic_prompt
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest
from pydantic import BaseModel

from app.agents.context import SolarAgentContext
from app.agents.guardrails import build_guardrail_middleware, build_output_guardrail_middleware
from app.tracing.trace_middleware import NaturalTraceMiddleware


def _tool_name(tool: Any) -> str | None:
    if isinstance(tool, dict):
        name = tool.get("name")
        return name if isinstance(name, str) else None
    name = getattr(tool, "name", None)
    return name if isinstance(name, str) else None


class ToolFilterMiddleware(AgentMiddleware[Any, SolarAgentContext, Any]):
    """Restrict the tools exposed to the model at runtime."""

    def __init__(self, allowed_tool_names: set[str]) -> None:
        self._allowed_tool_names = allowed_tool_names

    def wrap_model_call(self, request: ModelRequest[SolarAgentContext], handler):
        filtered_tools = [
            tool for tool in request.tools if _tool_name(tool) in self._allowed_tool_names
        ]
        return handler(request.override(tools=filtered_tools))

    async def awrap_model_call(self, request: ModelRequest[SolarAgentContext], handler):
        filtered_tools = [
            tool for tool in request.tools if _tool_name(tool) in self._allowed_tool_names
        ]
        return await handler(request.override(tools=filtered_tools))


def _preference_style(request: ModelRequest[SolarAgentContext]) -> str | None:
    runtime = request.runtime
    store = getattr(runtime, "store", None)
    context = getattr(runtime, "context", None)
    user_id = getattr(context, "user_id", None)
    if store is None or not user_id:
        return None
    item = store.get(("agent_preferences",), user_id)
    if item is None or not isinstance(item.value, dict):
        return None
    style = item.value.get("communication_style")
    return style if isinstance(style, str) and style else None


@dynamic_prompt
def runtime_context_prompt(request: ModelRequest[SolarAgentContext]) -> str:
    """Inject per-run instructions derived from runtime context/store."""

    context = request.runtime.context or SolarAgentContext()
    lines = [
        "Use the runtime context only as metadata. Do not invent domain values from it.",
        "Never persist exact street addresses or raw geocoding queries to memory or files unless the user explicitly asked for persistence.",
        "If you use assumptions, disclose them explicitly with source and confidence.",
    ]

    if context.locale:
        lines.append(f"Prefer the response locale {context.locale}.")
    if context.country_code:
        lines.append(f"Use {context.country_code} as geographic context only when the user request depends on country context.")
    if context.trace_enabled:
        lines.append("Keep each reasoning step concise so the natural trace stays auditable.")

    communication_style = _preference_style(request)
    if communication_style:
        lines.append(f"Respect the user's preferred communication style: {communication_style}.")

    return "\n".join(lines)


def build_agent_middleware(
    *,
    response_schema: type[BaseModel] | None = None,
    allowed_tool_names: set[str] | None = None,
) -> list[AgentMiddleware[Any, SolarAgentContext, Any]]:
    """Return the middleware stack shared by the supervisor and subagents."""

    middleware: list[AgentMiddleware[Any, SolarAgentContext, Any]] = [
        runtime_context_prompt,
        *build_output_guardrail_middleware(response_schema=response_schema),
        NaturalTraceMiddleware(response_schema=response_schema),
        *build_guardrail_middleware(response_schema=response_schema),
    ]
    if allowed_tool_names is not None:
        middleware.append(ToolFilterMiddleware(allowed_tool_names))
    return middleware


__all__ = ["ToolFilterMiddleware", "build_agent_middleware", "runtime_context_prompt"]
