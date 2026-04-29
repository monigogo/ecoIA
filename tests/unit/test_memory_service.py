from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.services.memory_service import ConversationMemoryService


class _HistoryAgent:
    async def aget_state(self, config):
        assert config == {"configurable": {"thread_id": "thread-1"}}
        return SimpleNamespace(
            values={
                "messages": [
                    HumanMessage(content="hola"),
                    AIMessage(content="respuesta"),
                    ToolMessage(content="ok", tool_call_id="tool-1"),
                ]
            }
        )


class _MissingHistoryAgent:
    async def aget_state(self, config):
        raise RuntimeError("thread not found")


def test_ensure_thread_id_reuses_existing_id() -> None:
    service = ConversationMemoryService()
    assert service.ensure_thread_id("thread-1") == "thread-1"


def test_ensure_thread_id_generates_when_missing() -> None:
    service = ConversationMemoryService()
    generated = service.ensure_thread_id(None)
    assert generated
    assert isinstance(generated, str)


async def test_get_thread_history_maps_langchain_messages_to_chat_messages() -> None:
    service = ConversationMemoryService()
    history = await service.get_thread_history(_HistoryAgent(), "thread-1")

    assert history.thread_id == "thread-1"
    assert [(message.role, message.content) for message in history.messages] == [
        ("user", "hola"),
        ("assistant", "respuesta"),
        ("tool", "ok"),
    ]


async def test_get_thread_history_returns_empty_for_unknown_thread() -> None:
    service = ConversationMemoryService()
    history = await service.get_thread_history(_MissingHistoryAgent(), "missing-thread")
    assert history.thread_id == "missing-thread"
    assert history.messages == []
