"""Schemas for the conversational chat API surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agents.output_schemas import SolarAgentStructuredResponse


class ChatRequest(BaseModel):
    """One user turn sent to the conversational supervisor."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, description="User message for this turn.")
    thread_id: str | None = Field(
        default=None,
        description="Conversation thread id. Reuse it to continue the same chat.",
    )
    user_id: str | None = Field(
        default=None,
        description="Optional stable user id for user-scoped runtime context.",
    )
    locale: str | None = Field(default=None, description="Optional locale hint, for example es-ES.")
    country_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="Optional ISO-3166 alpha-2 country hint, for example ES.",
    )
    include_trace: bool = Field(
        default=False,
        description="Whether to include inline natural trace lines in the structured result.",
    )


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant", "system", "tool"]
    content: str


class ChatResponse(BaseModel):
    """Response returned by ``POST /chat``."""

    model_config = ConfigDict(extra="forbid")

    thread_id: str
    user_id: str | None = None
    trace_id: str
    answer_text: str
    structured_result: SolarAgentStructuredResponse | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    history_length: int = Field(
        ge=0,
        description="Current number of persisted messages in the thread after this turn.",
    )
    request_id: str | None = None

    @property
    def message(self) -> str:
        return self.answer_text

    @property
    def structured_response(self) -> SolarAgentStructuredResponse | None:
        return self.structured_result


class ChatHistoryResponse(BaseModel):
    """Persisted thread history reconstructed from short-term memory."""

    model_config = ConfigDict(extra="forbid")

    thread_id: str
    messages: list[ChatMessage] = Field(default_factory=list)


__all__ = ["ChatHistoryResponse", "ChatMessage", "ChatRequest", "ChatResponse"]
