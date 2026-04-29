from __future__ import annotations

import pytest

from app.agents.solar_agent import build_solar_agent, supervisor_tools
from app.core.errors import ConfigurationError


def test_supervisor_tools_includes_core_solar_tools() -> None:
    """Supervisor has core solar tools directly for basic solar sizing."""
    tools = supervisor_tools()
    tool_names = {t.name for t in tools}
    assert "geocode_location" in tool_names
    assert "estimate_solar_production_with_pvgis" in tool_names
    assert "get_solar_base_scenario_candidates" in tool_names
    assert "calculate_system_kwp" in tool_names
    assert "calculate_annual_consumption" in tool_names
    assert "calculate_coverage" in tool_names
    assert "estimate_panels_for_future_target" in tool_names
    assert "calculate_panel_capacity_by_area" in tool_names
    assert "calculate_required_area_for_panels" in tool_names
    assert "calculate_row_spacing_for_self_shading" in tool_names
    assert "evaluate_layout_feasibility" in tool_names
    assert "get_assumption_candidates" in tool_names


def test_build_solar_agent_raises_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    from app.core.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ConfigurationError):
        build_solar_agent()
    get_settings.cache_clear()


def test_build_solar_agent_compiles_with_injected_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compile path with a real chat model instance. We don't invoke the
    agent; we only verify deepagents can wire our prompts, subagents and
    tools. Skipped when no API key is available (CI without secrets).
    """

    pytest.importorskip("deepagents")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o-mini", api_key="sk-test-not-real", temperature=0)
    agent = build_solar_agent(model=model)
    assert agent is not None
    assert hasattr(agent, "invoke")
    assert hasattr(agent, "stream")
