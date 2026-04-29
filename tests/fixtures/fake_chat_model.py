"""Test helpers: a minimal stand-in for a LangChain chat model.

Only implements the contract the AssumptionService relies on:
``with_structured_output(schema).invoke(messages)``. Avoids the cost and
flakiness of hitting a real LLM in unit tests.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class _FakeStructuredRunnable:
    def __init__(self, response_factory: Callable[[Any], Any]) -> None:
        self._factory = response_factory
        self.last_input: Any = None

    def invoke(self, messages: Any) -> Any:
        self.last_input = messages
        return self._factory(messages)


class FakeChatModel:
    """Stub chat model with the surface AssumptionService needs."""

    def __init__(self, response_factory: Callable[[Any], Any]) -> None:
        self._factory = response_factory
        self.last_schema: Any = None
        self.last_input: Any = None

    def with_structured_output(self, schema: Any) -> _FakeStructuredRunnable:
        self.last_schema = schema
        runnable = _FakeStructuredRunnable(self._factory)

        original_invoke = runnable.invoke

        def _capture(messages: Any) -> Any:
            self.last_input = messages
            return original_invoke(messages)

        runnable.invoke = _capture  # type: ignore[method-assign]
        return runnable
