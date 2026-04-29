from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.agents.memory import (
    aclose_agent_memory_resources,
    get_agent_checkpointer,
    get_agent_checkpointer_async,
    get_agent_store,
)
from app.core.errors import ConfigurationError


def test_agent_memory_builders_return_in_memory_backends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEMORY_STORAGE_BACKEND", "memory")
    from app.core.config import get_settings

    get_settings.cache_clear()
    get_agent_checkpointer.cache_clear()
    get_agent_store.cache_clear()

    checkpointer = get_agent_checkpointer()
    store = get_agent_store()

    assert checkpointer.__class__.__name__ == "InMemorySaver"
    assert store.__class__.__name__ == "InMemoryStore"

    get_settings.cache_clear()
    get_agent_checkpointer.cache_clear()
    get_agent_store.cache_clear()


async def test_agent_memory_builders_return_sqlite_async_checkpointer_and_in_memory_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEMORY_STORAGE_BACKEND", "sqlite")
    db_dir = Path(".test_artifacts")
    db_dir.mkdir(exist_ok=True)
    monkeypatch.setenv(
        "AGENT_CHECKPOINT_SQLITE_PATH",
        str(db_dir / f"agent-memory-{uuid.uuid4().hex}.sqlite"),
    )
    from app.core.config import get_settings

    get_settings.cache_clear()
    get_agent_checkpointer.cache_clear()
    get_agent_store.cache_clear()

    with pytest.raises(ConfigurationError):
        get_agent_checkpointer()

    checkpointer = await get_agent_checkpointer_async()
    store = get_agent_store()

    assert checkpointer.__class__.__name__ == "AsyncSqliteSaver"
    assert store.__class__.__name__ == "InMemoryStore"

    await aclose_agent_memory_resources()
    get_settings.cache_clear()


def test_agent_memory_builders_fail_loudly_for_unimplemented_backends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEMORY_STORAGE_BACKEND", "store")
    from app.core.config import get_settings

    get_settings.cache_clear()
    get_agent_checkpointer.cache_clear()
    get_agent_store.cache_clear()

    with pytest.raises(ConfigurationError):
        get_agent_checkpointer()
    with pytest.raises(ConfigurationError):
        get_agent_store()

    get_settings.cache_clear()
    get_agent_checkpointer.cache_clear()
    get_agent_store.cache_clear()
