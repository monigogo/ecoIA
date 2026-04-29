"""End-to-end conversational orchestration with trace persistence."""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

import anyio

from app.agents.context import build_agent_context
from app.agents.solar_agent import build_solar_agent_async
from app.core.config import Settings, get_settings
from app.core.errors import AgentExecutionError, ConfigurationError
from app.repositories.trace_repository import get_trace_repository
from app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse
from app.services.conversation_response_builder import (
    build_chat_response,
    exception_detail,
    resolve_response_payload,
)
from app.services.conversation_trace_builder import (
    build_failure_event,
    build_final_answer_event,
    build_message_received_event,
    build_warning_events,
    extract_trace_events,
    normalize_event_timestamps,
)
from app.services.memory_service import ConversationMemoryService


class ConversationService:
    """Thin orchestration layer for multi-turn chat with trace persistence."""

    def __init__(
        self,
        agent: Any | None = None,
        memory_service: ConversationMemoryService | None = None,
        trace_repository: Any | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._agent = agent
        self._memory = memory_service or ConversationMemoryService()
        self._trace_repository = trace_repository or get_trace_repository()
        self._settings = settings or get_settings()

    async def _ensure_agent(self) -> Any:
        if self._agent is not None:
            return self._agent
        if not self._settings.has_llm_credentials:
            raise ConfigurationError(
                f"{self._settings.llm_credential_hint} is not set; the conversational agent cannot run."
            )
        self._agent = await build_solar_agent_async()
        return self._agent

    async def _persist_trace_session(
        self,
        *,
        trace_id: str,
        user_id: str | None,
        thread_id: str,
        request_id: str | None,
    ) -> None:
        await anyio.to_thread.run_sync(
            lambda: self._trace_repository.create_trace_session(
                trace_id=trace_id,
                user_id=user_id,
                thread_id=thread_id,
                request_id=request_id,
                status="started",
            )
        )

    async def _append_trace_events(
        self,
        *,
        trace_id: str,
        events: list[dict[str, Any]],
        sequence_number: int,
    ) -> int:
        return await anyio.to_thread.run_sync(
            lambda: self._trace_repository.append_events(
                trace_id=trace_id,
                events=normalize_event_timestamps(events),
                start_sequence_number=sequence_number,
            )
        )

    async def _update_trace_session(
        self,
        *,
        trace_id: str,
        status: str,
        final_summary: str | None = None,
    ) -> None:
        await anyio.to_thread.run_sync(
            lambda: self._trace_repository.update_trace_session(
                trace_id=trace_id,
                status=status,
                final_summary=final_summary,
            )
        )

    async def _agent_state(self, agent: Any, thread_id: str) -> dict[str, Any]:
        try:
            if hasattr(agent, "aget_state"):
                snapshot = await agent.aget_state(config=self._memory.config_for_thread(thread_id))
            elif hasattr(agent, "get_state"):
                snapshot = await anyio.to_thread.run_sync(
                    lambda: agent.get_state(self._memory.config_for_thread(thread_id))
                )
            else:
                return {}
        except Exception:
            return {}

        values = getattr(snapshot, "values", {})
        return values if isinstance(values, dict) else {}

    async def _invoke_agent(
        self,
        *,
        agent: Any,
        request: ChatRequest,
        request_id: str | None,
        trace_id: str,
        thread_id: str,
    ) -> Any:
        context = build_agent_context(
            request_id=request_id,
            trace_id=trace_id,
            thread_id=thread_id,
            user_id=request.user_id,
            locale=request.locale or "es-ES",
            country_code=request.country_code or "ES",
        )
        config = self._memory.config_for_thread(thread_id)
        payload = {"messages": [{"role": "user", "content": request.message}]}

        with anyio.fail_after(float(self._settings.agent_runtime_timeout_seconds)):
            if hasattr(agent, "ainvoke"):
                return await agent.ainvoke(payload, config=config, context=context)
            if hasattr(agent, "invoke"):
                return await anyio.to_thread.run_sync(
                    lambda: agent.invoke(payload, config=config, context=context)
                )
            raise RuntimeError("Chat agent does not expose invoke or ainvoke")

    async def chat(self, request: ChatRequest, request_id: str | None = None) -> ChatResponse:
        thread_id = self._memory.ensure_thread_id(request.thread_id)
        trace_id = str(uuid.uuid4())
        sequence_number = 0

        await self._persist_trace_session(
            trace_id=trace_id,
            user_id=request.user_id,
            thread_id=thread_id,
            request_id=request_id,
        )
        sequence_number = await self._append_trace_events(
            trace_id=trace_id,
            events=[build_message_received_event(len(request.message))],
            sequence_number=sequence_number,
        )

        try:
            agent = await self._ensure_agent()
            result = await self._invoke_agent(
                agent=agent,
                request=request,
                request_id=request_id,
                trace_id=trace_id,
                thread_id=thread_id,
            )
        except ConfigurationError as exc:
            sequence_number = await self._append_trace_events(
                trace_id=trace_id,
                events=[
                    build_failure_event(
                        "Agent execution could not start because configuration is missing.",
                        exception_detail(exc),
                    )
                ],
                sequence_number=sequence_number,
            )
            await self._update_trace_session(trace_id=trace_id, status="failed")
            raise
        except Exception as exc:  # noqa: BLE001
            error_detail = exception_detail(exc)
            sequence_number = await self._append_trace_events(
                trace_id=trace_id,
                events=[
                    build_failure_event(
                        "Agent execution failed before a full answer could be generated.",
                        error_detail,
                    )
                ],
                sequence_number=sequence_number,
            )
            await self._update_trace_session(trace_id=trace_id, status="failed")
            if isinstance(exc, AgentExecutionError):
                raise
            raise AgentExecutionError(
                "The agent failed while processing the request.",
                details={"error": error_detail, "trace_id": trace_id},
            ) from exc

        state_values = await self._agent_state(agent, thread_id)
        sequence_number = await self._append_trace_events(
            trace_id=trace_id,
            events=extract_trace_events(result, state_values),
            sequence_number=sequence_number,
        )

        structured_result, answer_text, warnings = resolve_response_payload(
            result,
            include_trace=request.include_trace,
            locale=request.locale,
        )
        if warnings:
            sequence_number = await self._append_trace_events(
                trace_id=trace_id,
                events=build_warning_events(warnings),
                sequence_number=sequence_number,
            )

        sequence_number = await self._append_trace_events(
            trace_id=trace_id,
            events=[build_final_answer_event(answer_text)],
            sequence_number=sequence_number,
        )
        await self._update_trace_session(
            trace_id=trace_id,
            status="completed",
            final_summary=answer_text,
        )

        history = await self.get_history(thread_id)
        return build_chat_response(
            thread_id=thread_id,
            user_id=request.user_id,
            trace_id=trace_id,
            answer_text=answer_text,
            structured_result=structured_result,
            warnings=warnings,
            history_length=len(history.messages),
            request_id=request_id,
        )

    async def get_history(self, thread_id: str) -> ChatHistoryResponse:
        agent = await self._ensure_agent()
        return await self._memory.get_thread_history(agent, thread_id)


@lru_cache(maxsize=1)
def get_conversation_service() -> ConversationService:
    return ConversationService()


__all__ = ["ConversationService", "get_conversation_service"]
