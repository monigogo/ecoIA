"""Checkpointer/store builders for the SolarLife deep agent runtime."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path

import aiosqlite
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from app.core.config import get_settings
from app.core.errors import ConfigurationError

_async_sqlite_checkpointer: AsyncSqliteSaver | None = None


def _sqlite_checkpoint_path() -> str:
    settings = get_settings()
    path = Path(settings.agent_checkpoint_sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


@lru_cache(maxsize=1)
def get_agent_checkpointer() -> BaseCheckpointSaver:
    """Return the configured LangGraph checkpointer.

    Synchronous callers can use only the in-memory backend. SQLite-backed
    checkpointing requires the async builder because LangGraph expects
    ``AsyncSqliteSaver`` when the graph is invoked with ``ainvoke``.
    """

    settings = get_settings()
    if settings.memory_storage_backend == "memory":
        return InMemorySaver()
    if settings.memory_storage_backend == "sqlite":
        raise ConfigurationError(
            "memory_storage_backend='sqlite' requires the async agent checkpointer builder."
        )
    msg = (
        f"memory_storage_backend={settings.memory_storage_backend!r} is not implemented "
        "for the agent checkpointer."
    )
    raise ConfigurationError(msg)


async def get_agent_checkpointer_async() -> BaseCheckpointSaver:
    """Return the configured LangGraph checkpointer for async agent execution."""

    settings = get_settings()
    if settings.memory_storage_backend != "sqlite":
        return get_agent_checkpointer()

    global _async_sqlite_checkpointer
    if _async_sqlite_checkpointer is None:
        conn = await aiosqlite.connect(_sqlite_checkpoint_path())
        _async_sqlite_checkpointer = AsyncSqliteSaver(conn)
    return _async_sqlite_checkpointer


@lru_cache(maxsize=1)
def get_agent_store() -> BaseStore:
    """Return the configured long-term store for runtime context lookups.

    The conversation history persistence lives in the LangGraph checkpointer.
    The runtime store is still kept in-memory for now because this repo does
    not yet define a persistent long-term memory backend.
    """

    if get_settings().memory_storage_backend in {"memory", "sqlite"}:
        return InMemoryStore()
    msg = (
        f"memory_storage_backend={get_settings().memory_storage_backend!r} is not implemented "
        "for the agent store."
    )
    raise ConfigurationError(msg)


async def aclose_agent_memory_resources() -> None:
    """Close cached persistence resources and clear builder caches."""

    global _async_sqlite_checkpointer

    async_checkpointer = _async_sqlite_checkpointer
    _async_sqlite_checkpointer = None
    if async_checkpointer is not None:
        conn = getattr(async_checkpointer, "conn", None)
        if conn is not None and hasattr(conn, "close"):
            await conn.close()

    sync_checkpointer = (
        get_agent_checkpointer() if get_agent_checkpointer.cache_info().currsize else None
    )
    if sync_checkpointer is not None and hasattr(sync_checkpointer, "conn"):
        conn = getattr(sync_checkpointer, "conn", None)
        if conn is not None and hasattr(conn, "close"):
            conn.close()
    get_agent_checkpointer.cache_clear()
    get_agent_store.cache_clear()

def close_agent_memory_resources() -> None:
    """Synchronously close cached persistence resources."""

    asyncio.run(aclose_agent_memory_resources())


__all__ = [
    "aclose_agent_memory_resources",
    "close_agent_memory_resources",
    "get_agent_checkpointer",
    "get_agent_checkpointer_async",
    "get_agent_store",
]
