import os

import pytest

os.environ.setdefault("APP_NAME", "ecoIA")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("TRACE_ENABLED", "false")
os.environ.setdefault("MEMORY_STORAGE_BACKEND", "memory")


def _smoke_tests_enabled() -> bool:
    return os.getenv("RUN_SMOKE_TESTS") == "1"


def _slow_smoke_tests_enabled() -> bool:
    return os.getenv("RUN_SLOW_SMOKE_TESTS") == "1"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    del config
    skip_smoke = pytest.mark.skip(reason="Set RUN_SMOKE_TESTS=1 to run smoke tests.")
    skip_slow = pytest.mark.skip(reason="Set RUN_SLOW_SMOKE_TESTS=1 to run slow smoke tests.")

    for item in items:
        if "smoke" in item.keywords and not _smoke_tests_enabled():
            item.add_marker(skip_smoke)
        if "slow" in item.keywords and not _slow_smoke_tests_enabled():
            item.add_marker(skip_slow)
