"""Guardrails for the SolarLife deep-agent runtime.

These controls are technical runtime constraints. They do not decide
domain outcomes for the solar planning flow.
"""

from __future__ import annotations

from typing import Any

from deepagents.middleware.permissions import FilesystemPermission
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    PIIMiddleware,
    ToolCallLimitMiddleware,
)
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from app.agents.context import SolarAgentContext
from app.core.config import get_settings


def _last_ai_message_text(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            content = str(message.content).strip()
            if content:
                return content
    return ""


class NonEmptyStructuredResponseMiddleware(
    AgentMiddleware[Any, SolarAgentContext, Any]
):
    """Fill an empty structured summary from the model's own final text."""

    def __init__(self, response_schema: type[BaseModel] | None = None) -> None:
        self._response_schema = response_schema

    @staticmethod
    def _summary_from_structured_response(response: ModelResponse[Any]) -> str:
        structured = response.structured_response
        if isinstance(structured, BaseModel):
            summary = structured.model_dump().get("summary", "")
            return summary if isinstance(summary, str) else ""
        if isinstance(structured, dict):
            summary = structured.get("summary", "")
            return summary if isinstance(summary, str) else ""
        return ""

    @staticmethod
    def _is_empty_structured_response(response: ModelResponse[Any]) -> bool:
        return not NonEmptyStructuredResponseMiddleware._summary_from_structured_response(
            response
        ).strip()

    def _coerce_structured_response(
        self,
        summary: str,
        current_value: Any,
    ) -> BaseModel | dict[str, Any]:
        payload = {"summary": summary}
        if self._response_schema is not None:
            return self._response_schema.model_validate(payload)
        if isinstance(current_value, BaseModel):
            return current_value.__class__.model_validate(payload)
        return payload

    def _build_fallback_response(
        self,
        response: ModelResponse[Any],
    ) -> ModelResponse[Any]:
        summary = _last_ai_message_text(list(response.result))
        if not summary:
            return response
        return ModelResponse(
            result=response.result,
            structured_response=self._coerce_structured_response(
                summary,
                response.structured_response,
            ),
        )

    def wrap_model_call(
        self,
        request: ModelRequest[SolarAgentContext],
        handler,
    ) -> ModelResponse[Any]:
        response = handler(request)
        if self._response_schema is None or not self._is_empty_structured_response(response):
            return response
        return self._build_fallback_response(response)

    async def awrap_model_call(
        self,
        request: ModelRequest[SolarAgentContext],
        handler,
    ) -> ModelResponse[Any]:
        response = await handler(request)
        if self._response_schema is None or not self._is_empty_structured_response(response):
            return response
        return self._build_fallback_response(response)


def build_guardrail_middleware(
    *,
    response_schema: type[BaseModel] | None = None,
) -> list[AgentMiddleware[Any, SolarAgentContext, Any]]:
    """Return runtime guardrails for the agent loop."""

    del response_schema
    settings = get_settings()
    middleware: list[AgentMiddleware[Any, SolarAgentContext, Any]] = []

    if settings.agent_pii_guardrails_enabled:
        middleware.extend(
            [
                PIIMiddleware(
                    "email",
                    strategy="redact",
                    apply_to_input=True,
                    apply_to_output=True,
                    apply_to_tool_results=True,
                ),
                PIIMiddleware(
                    "credit_card",
                    strategy="mask",
                    apply_to_input=True,
                    apply_to_output=True,
                    apply_to_tool_results=True,
                ),
            ]
        )

    if settings.agent_human_in_the_loop_enabled and settings.agent_human_in_the_loop_tools:
        middleware.append(
            HumanInTheLoopMiddleware(
                interrupt_on={tool_name: True for tool_name in settings.agent_human_in_the_loop_tools},
                description_prefix="SolarLife tool execution requires approval",
            )
        )

    middleware.extend(
        [
            ModelCallLimitMiddleware(
                run_limit=settings.agent_model_call_limit,
                exit_behavior="error",
            ),
            ToolCallLimitMiddleware(
                run_limit=settings.agent_tool_call_limit,
                exit_behavior="error",
            ),
            ToolCallLimitMiddleware(
                tool_name="task",
                run_limit=settings.agent_task_call_limit,
                exit_behavior="continue",
            ),
            ToolCallLimitMiddleware(
                tool_name="get_assumption_candidates",
                run_limit=settings.agent_assumption_call_limit,
                exit_behavior="continue",
            ),
            ToolCallLimitMiddleware(
                tool_name="get_solar_base_scenario_candidates",
                run_limit=settings.agent_solar_base_scenario_call_limit,
                exit_behavior="continue",
            ),
        ]
    )
    return middleware


def build_output_guardrail_middleware(
    *,
    response_schema: type[BaseModel] | None = None,
) -> list[AgentMiddleware[Any, SolarAgentContext, Any]]:
    """Return final-output guardrails that should run after tracing."""

    settings = get_settings()
    if not settings.agent_output_guardrails_enabled:
        return []
    return [NonEmptyStructuredResponseMiddleware(response_schema=response_schema)]


def build_filesystem_permissions() -> list[FilesystemPermission]:
    """Deny filesystem writes from the agent runtime."""

    return [FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")]


__all__ = [
    "NonEmptyStructuredResponseMiddleware",
    "build_filesystem_permissions",
    "build_guardrail_middleware",
    "build_output_guardrail_middleware",
]
