from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from app.agents.memory import close_agent_memory_resources
from app.core.config import get_settings
from app.services.conversation_service import get_conversation_service


def has_real_llm_credentials() -> bool:
    process_keys = (
        os.getenv("NVIDIA_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
    )
    if any(process_keys):
        return True
    env_path = Path(".env")
    if not env_path.exists():
        return False
    env_values = dotenv_values(env_path)
    return bool(env_values.get("NVIDIA_API_KEY") or env_values.get("OPENAI_API_KEY"))


def reset_runtime_caches() -> None:
    close_agent_memory_resources()
    get_settings.cache_clear()
    get_conversation_service.cache_clear()


def configure_smoke_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("TRACE_ENABLED", "true")
    monkeypatch.setenv("MEMORY_STORAGE_BACKEND", "memory")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'smoke.db').as_posix()}")
    monkeypatch.setenv(
        "AGENT_CHECKPOINT_SQLITE_PATH",
        str(tmp_path / "langgraph_checkpoints.sqlite"),
    )
    reset_runtime_caches()


def combined_chat_text(chat_body: dict[str, Any], trace_body: dict[str, Any] | None = None) -> str:
    structured = chat_body.get("structured_result") or {}
    parts: list[str] = [str(chat_body.get("answer_text", ""))]
    parts.extend(str(item) for item in chat_body.get("warnings", []))
    parts.append(str(structured.get("summary", "")))
    parts.extend(str(item) for item in structured.get("key_points", []))
    parts.extend(str(item) for item in structured.get("warnings", []))
    parts.extend(str(item) for item in structured.get("missing_information", []))
    parts.extend(str(item) for item in structured.get("next_questions", []))
    parts.extend(str(item) for item in structured.get("next_steps", []))
    parts.extend(
        str(item.get("chosen_value", ""))
        for item in structured.get("assumptions_used", [])
        if isinstance(item, dict)
    )

    if trace_body is not None:
        parts.extend(
            str(event.get("natural_description", ""))
            for event in trace_body.get("events", [])
            if isinstance(event, dict)
        )

    return "\n".join(part for part in parts if part)


def contains_any(text: str, *needles: str) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)
