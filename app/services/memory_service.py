"""Conversation-memory helpers built on LangGraph short-term memory.

The memory model follows LangChain/LangGraph guidance:

- short-term memory is thread-scoped and persisted by the graph checkpointer
- long-term memory belongs in a store namespace and is handled separately

This service only handles the conversational, thread-scoped layer needed for
multi-turn chat continuity.
"""

from __future__ import annotations

import uuid
from typing import Any

import anyio
from langchain_core.messages import BaseMessage

from app.schemas.chat import ChatHistoryResponse, ChatMessage

_ROLE_MAP = {
    "ai": "assistant",
    "assistant": "assistant",
    "human": "user",
    "system": "system",
    "tool": "tool",
}


class ConversationMemoryService:
    """Utilities for working with thread-scoped conversational memory."""

    @staticmethod
    def ensure_thread_id(thread_id: str | None) -> str:
        return thread_id or str(uuid.uuid4())

    @staticmethod
    def config_for_thread(thread_id: str) -> dict[str, dict[str, str]]:
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _role_for_message(message: BaseMessage) -> str:
        return _ROLE_MAP.get(message.type, "assistant")

    @staticmethod
    def _content_to_text(content: Any) -> str:
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

    def to_chat_message(self, message: BaseMessage) -> ChatMessage:
        return ChatMessage(
            role=self._role_for_message(message),  # type: ignore[arg-type]
            content=self._content_to_text(message.content),
        )

    async def get_thread_history(self, agent: Any, thread_id: str) -> ChatHistoryResponse:
        try:
            if hasattr(agent, "aget_state"):
                snapshot = await agent.aget_state(config=self.config_for_thread(thread_id))
            elif hasattr(agent, "get_state"):
                snapshot = await anyio.to_thread.run_sync(
                    lambda: agent.get_state(self.config_for_thread(thread_id))
                )
            else:
                return ChatHistoryResponse(thread_id=thread_id, messages=[])
        except Exception:  # noqa: BLE001 - checkpoint backends vary on missing threads
            return ChatHistoryResponse(thread_id=thread_id, messages=[])
        values = getattr(snapshot, "values", {}) or {}
        raw_messages = values.get("messages", [])
        messages = [
            self.to_chat_message(message)
            for message in raw_messages
            if isinstance(message, BaseMessage)
        ]
        return ChatHistoryResponse(thread_id=thread_id, messages=messages)


__all__ = ["ConversationMemoryService"]
