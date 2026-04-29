"""LangChain tool wrapping the AssumptionService.

Exposed to the supervisor agent and any subagent that needs technical
assumptions when user data and external APIs cannot supply a value.

Reasoning rules (see ``AGENTS.md``):

- The tool returns CANDIDATES. It does NOT pick a winner.
- The agent MUST select one candidate and disclose it in the natural trace.
- No regex / keyword matching / silent defaults anywhere on this path.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool

from app.schemas.assumptions import AssumptionRequest
from app.services.assumption_service import AssumptionService

if TYPE_CHECKING:  # pragma: no cover
    from langchain_core.language_models import BaseChatModel


@lru_cache(maxsize=1)
def _default_service() -> AssumptionService:
    """Lazy singleton for the default service. Tests inject their own service
    via :func:`build_assumption_tool` instead.
    """

    return AssumptionService()


def build_assumption_tool(service: AssumptionService | None = None):
    """Return a LangChain tool bound to a specific ``AssumptionService``.

    Use this in tests (with a fake model-backed service) or in agent
    construction when a non-default model should be used.
    """

    bound_service = service or _default_service()

    @tool("get_assumption_candidates", args_schema=AssumptionRequest)
    def get_assumption_candidates(domain: str, context: str) -> dict[str, Any]:
        """Return candidate technical or regulatory assumptions when the user
        did not provide a value and external APIs cannot supply one.

        The tool does NOT decide. It returns several plausible candidates with
        source, confidence, reasoning and limitations. The agent must pick one
        and disclose it in the natural trace.

        Use this tool for a blocking parameter, not to fill an entire broad
        scenario one field at a time. If several independent values are
        missing in the same turn, prefer a safe partial answer plus the
        smallest set of missing inputs the user can provide next.

        Args:
            domain: Free-form key naming the parameter the agent needs
                (for example ``solar_degradation``, ``system_losses``,
                ``battery_depth_of_discharge``).
            context: Natural-language context the agent supplies so that the
                provider can reason about plausible scenarios.
        """

        request = AssumptionRequest(domain=domain, context=context)
        response = bound_service.generate_candidates(request)
        return response.model_dump()

    return get_assumption_candidates


def build_assumption_tool_with_model(model: BaseChatModel):
    """Convenience builder: wrap a model into a service and a tool."""

    return build_assumption_tool(AssumptionService(model=model))


# Default export for direct import in agent construction.
get_assumption_candidates = build_assumption_tool()
