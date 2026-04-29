"""Supervisor agent factory.

Builds the SolarLife supervisor on top of ``deepagents.create_deep_agent``
with our programmatic subagents, the AssumptionProviderTool, the
``AGENTS.md`` memory, and the filesystem skills folder.

Reasoning-first contract (see ``AGENTS.md``):

- The supervisor is purely an orchestrator. It does not encode domain
  decisions in code; it reasons over user input, delegates to subagents,
  and calls tools.
- Tools and the AssumptionProvider produce options. The supervisor picks
  and declares choices.
- This module exposes only construction; it does not invoke the agent.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from app.agents.context import SolarAgentContext
from app.agents.guardrails import build_filesystem_permissions
from app.agents.memory import get_agent_checkpointer, get_agent_checkpointer_async, get_agent_store
from app.agents.middleware import build_agent_middleware
from app.agents.output_schemas import SolarAgentStructuredResponse
from app.agents.prompts import SUPERVISOR_PROMPT
from app.agents.subagents import build_compiled_subagents
from app.core.config import get_settings
from app.core.errors import ConfigurationError
from app.llm import build_default_chat_model

if TYPE_CHECKING:  # pragma: no cover
    from langchain_core.language_models import BaseChatModel

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_MD = REPO_ROOT / "AGENTS.md"
SKILLS_DIR = REPO_ROOT / "skills"


def _resolve_model(model: BaseChatModel | str | None):
    """Resolve the model used by the supervisor.

    - Passing ``None`` builds the default provider-native chat model from settings.
    - Passing a string is forwarded as-is to ``create_deep_agent``
      (deepagents accepts ``"openai:gpt-4o-mini"`` style strings).
    - Passing a ``BaseChatModel`` is forwarded as-is.
    """

    if model is not None:
        return model

    settings = get_settings()
    if not settings.has_llm_credentials:
        raise ConfigurationError(
            f"{settings.llm_credential_hint} is not set; cannot build the SolarLife supervisor.",
        )
    return build_default_chat_model(settings=settings, temperature=0)


def _supports_supervisor_response_format(
    model: BaseChatModel | str | None,
    resolved_model: Any,
) -> bool:
    if isinstance(model, str):
        return "nvidia" not in model.lower()
    if model is None:
        return get_settings().resolved_llm_provider != "nvidia"
    return resolved_model.__class__.__name__ != "ChatNVIDIA"
def supervisor_tools() -> list[Any]:
    """Tools the supervisor can call directly.

    Core solar estimation tools are on the supervisor so it can handle basic
    solar sizing without delegating to a subagent. Specialized subagents have
    their own tool sets defined in :mod:`app.agents.subagents`.
    """
    from app.tools.assumption_tools import build_assumption_tool
    from app.tools.geocoding_tools import build_geocoding_tool
    from app.tools.layout_tools import (
        build_calculate_panel_capacity_by_area_tool,
        build_calculate_required_area_for_panels_tool,
        build_calculate_row_spacing_for_self_shading_tool,
        build_evaluate_layout_feasibility_tool,
    )
    from app.tools.pvgis_tools import build_pvgis_tool
    from app.tools.solar_calculation_tools import (
        build_calculate_annual_consumption_tool,
        build_calculate_coverage_tool,
        build_calculate_system_kwp_tool,
        build_estimate_panels_for_future_target_tool,
    )
    from app.tools.solar_scenario_tools import build_solar_base_scenario_tool

    return [
        build_geocoding_tool(),
        build_pvgis_tool(),
        build_solar_base_scenario_tool(),
        build_assumption_tool(),
        build_calculate_system_kwp_tool(),
        build_calculate_annual_consumption_tool(),
        build_calculate_coverage_tool(),
        build_estimate_panels_for_future_target_tool(),
        build_calculate_panel_capacity_by_area_tool(),
        build_calculate_required_area_for_panels_tool(),
        build_calculate_row_spacing_for_self_shading_tool(),
        build_evaluate_layout_feasibility_tool(),
    ]


def build_solar_agent(model: BaseChatModel | str | None = None) -> Any:
    """Construct the SolarLife supervisor as a compiled deepagent graph.

    Parameters
    ----------
    model:
        Optional override. ``None`` builds the default provider-native chat model.
        Tests pass a fake model or a string id.
    """

    resolved_model = _resolve_model(model)
    use_structured_response = _supports_supervisor_response_format(model, resolved_model)
    return _compile_solar_agent(
        resolved_model,
        use_structured_response=use_structured_response,
        checkpointer=get_agent_checkpointer(),
    )


async def build_solar_agent_async(model: BaseChatModel | str | None = None) -> Any:
    """Async builder for the SolarLife supervisor."""

    resolved_model = _resolve_model(model)
    use_structured_response = _supports_supervisor_response_format(model, resolved_model)
    return _compile_solar_agent(
        resolved_model,
        use_structured_response=use_structured_response,
        checkpointer=await get_agent_checkpointer_async(),
    )


def _compile_solar_agent(
    resolved_model: BaseChatModel | str | Any,
    *,
    use_structured_response: bool,
    checkpointer: Any,
) -> Any:
    from deepagents import create_deep_agent

    middleware = cast(
        list[Any],
        build_agent_middleware(
            response_schema=SolarAgentStructuredResponse if use_structured_response else None,
        ),
    )

    return create_deep_agent(
        model=resolved_model,
        tools=supervisor_tools(),
        system_prompt=SUPERVISOR_PROMPT,
        middleware=middleware,
        subagents=build_compiled_subagents(
            resolved_model,
            middleware_factory=lambda: build_agent_middleware(
                response_schema=None,
            ),
        ),
        skills=[str(SKILLS_DIR) + "/"],
        memory=[str(AGENTS_MD)],
        permissions=build_filesystem_permissions(),
        response_format=SolarAgentStructuredResponse if use_structured_response else None,
        context_schema=SolarAgentContext,
        checkpointer=checkpointer,
        store=get_agent_store(),
        name="solarlife_supervisor",
    )


__all__ = ["build_solar_agent", "build_solar_agent_async", "supervisor_tools"]
