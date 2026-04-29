"""Helpers to shape chat responses from raw agent outputs."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from app.agents.output_schemas import SolarAgentStructuredResponse
from app.core.messages import MessageKey, get_message
from app.schemas.chat import ChatResponse


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part)
    return str(content)


def exception_detail(exc: BaseException) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


def last_ai_message_text(messages: list[Any]) -> str | None:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = content_to_text(message.content).strip()
            if text:
                return text
    return None


def deduplicate_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduplicated: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduplicated.append(item)
    return deduplicated


def enrich_warnings_from_structured_result(
    warnings: list[str],
    structured_result: SolarAgentStructuredResponse | None,
    *,
    locale: str | None,
) -> list[str]:
    if structured_result is None:
        return warnings

    enriched = list(warnings)
    if structured_result.subsidy_candidates:
        enriched.append(get_message(MessageKey.SUBSIDY_LEGAL_DISCLAIMER, locale))
    if structured_result.export_compensation:
        enriched.append(get_message(MessageKey.ECONOMIC_COMPENSATION_DISCLAIMER, locale))
    if structured_result.export_sale_revenue:
        enriched.append(get_message(MessageKey.REAL_SALE_REVENUE_DISCLAIMER, locale))
    if structured_result.rdtools_analysis:
        enriched.append(get_message(MessageKey.RDTOOLS_DATA_QUALITY_DISCLAIMER, locale))
    return deduplicate_preserving_order(enriched)


def coerce_structured_response(
    payload: Any,
    *,
    include_trace: bool,
) -> SolarAgentStructuredResponse | None:
    if payload is None:
        return None
    if isinstance(payload, SolarAgentStructuredResponse):
        response = payload
    elif isinstance(payload, dict):
        response = SolarAgentStructuredResponse.model_validate(payload)
    else:
        return None

    if include_trace:
        return response

    return response.model_copy(update={"natural_trace": []})


def resolve_response_payload(
    result: Any,
    *,
    include_trace: bool,
    locale: str | None = "es",
) -> tuple[SolarAgentStructuredResponse | None, str, list[str]]:
    messages = result.get("messages", []) if isinstance(result, dict) else []
    structured_result = coerce_structured_response(
        result.get("structured_response") if isinstance(result, dict) else None,
        include_trace=include_trace,
    )
    answer_text = (
        structured_result.summary
        if structured_result is not None
        else last_ai_message_text(messages) or ""
    )
    warnings = enrich_warnings_from_structured_result(
        list(structured_result.warnings) if structured_result is not None else [],
        structured_result,
        locale=locale,
    )
    return structured_result, answer_text, warnings


def build_chat_response(
    *,
    thread_id: str,
    user_id: str | None,
    trace_id: str,
    answer_text: str,
    structured_result: SolarAgentStructuredResponse | None,
    warnings: list[str],
    history_length: int,
    request_id: str | None,
) -> ChatResponse:
    return ChatResponse(
        thread_id=thread_id,
        user_id=user_id,
        trace_id=trace_id,
        answer_text=answer_text,
        structured_result=structured_result,
        warnings=warnings,
        error=None,
        history_length=history_length,
        request_id=request_id,
    )


__all__ = [
    "build_chat_response",
    "coerce_structured_response",
    "content_to_text",
    "deduplicate_preserving_order",
    "enrich_warnings_from_structured_result",
    "exception_detail",
    "last_ai_message_text",
    "resolve_response_payload",
]
