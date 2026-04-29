"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


def _normalize_sqlite_url(url: str) -> str:
    if not url.startswith("sqlite:///"):
        return url
    relative_path = url.removeprefix("sqlite:///")
    path = Path(relative_path)
    if path.parent and str(path.parent) not in {"", "."}:
        path.parent.mkdir(parents=True, exist_ok=True)
    return url


@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    database_url = _normalize_sqlite_url(settings.database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    import app.db.models  # noqa: F401

    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def close_db_resources() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()


__all__ = ["close_db_resources", "create_db_and_tables", "get_engine", "get_session"]
