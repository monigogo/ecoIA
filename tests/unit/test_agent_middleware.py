from __future__ import annotations

from types import SimpleNamespace

from langchain.agents.middleware.types import ModelRequest
from langgraph.store.memory import InMemoryStore

from app.agents.context import SolarAgentContext
from app.agents.middleware import (
    ToolFilterMiddleware,
    build_agent_middleware,
    runtime_context_prompt,
)
from app.core.config import get_settings


def test_runtime_context_prompt_injects_context_and_store_preferences() -> None:
    store = InMemoryStore()
    store.put(("agent_preferences",), "user-1", {"communication_style": "concise"})

    runtime = SimpleNamespace(
        context=SolarAgentContext(
            request_id="req-1",
            thread_id="thread-1",
            user_id="user-1",
            locale="es-ES",
            country_code="ES",
            trace_enabled=True,
        ),
        store=store,
    )
    request = ModelRequest(
        model=object(),  # type: ignore[arg-type]
        messages=[],
        state={"messages": []},
        runtime=runtime,
    )

    captured: dict[str, ModelRequest[SolarAgentContext]] = {}

    def handler(updated_request: ModelRequest[SolarAgentContext]) -> ModelRequest[SolarAgentContext]:
        captured["request"] = updated_request
        return updated_request

    runtime_context_prompt.wrap_model_call(request, handler)

    system_message = captured["request"].system_message
    assert system_message is not None
    assert "Prefer the response locale es-ES." in system_message.text
    assert "Use ES as geographic context" in system_message.text
    assert "communication style: concise" in system_message.text
    assert "Never persist exact street addresses" in system_message.text


def test_build_agent_middleware_includes_prompt_trace_and_guardrails() -> None:
    get_settings.cache_clear()
    middleware = build_agent_middleware()
    names = [item.__class__.__name__ for item in middleware]
    assert len(middleware) == 10
    assert names[0] == runtime_context_prompt.__class__.__name__
    assert "NonEmptyStructuredResponseMiddleware" in names
    assert "NaturalTraceMiddleware" in names
    assert names.count("PIIMiddleware") == 2
    assert "ModelCallLimitMiddleware" in names
    assert names.count("ToolCallLimitMiddleware") == 4


def test_tool_filter_middleware_restricts_runtime_tools() -> None:
    middleware = ToolFilterMiddleware({"task"})
    request = ModelRequest(
        model=object(),  # type: ignore[arg-type]
        messages=[],
        tools=[{"name": "task"}, {"name": "write_todos"}, {"name": "execute"}],
        state={"messages": []},
        runtime=SimpleNamespace(context=SolarAgentContext()),
    )

    captured: dict[str, ModelRequest[SolarAgentContext]] = {}

    def handler(updated_request: ModelRequest[SolarAgentContext]) -> ModelRequest[SolarAgentContext]:
        captured["request"] = updated_request
        return updated_request

    middleware.wrap_model_call(request, handler)

    assert [tool["name"] for tool in captured["request"].tools] == ["task"]


def test_supervisor_tool_filter_allows_core_solar_tools() -> None:
    """Supervisor middleware must NOT filter all tools down to {"task"}.

    Regression guard: an earlier configuration restricted the supervisor to
    the ``task`` delegation tool only, which hid every core solar tool from
    the model and broke the direct planning flow. The supervisor must keep
    direct access to its registered tools.
    """

    from app.agents.solar_agent import supervisor_tools

    middleware = build_agent_middleware()
    names = [item.__class__.__name__ for item in middleware]
    assert "ToolFilterMiddleware" not in names, (
        "Supervisor middleware must not register ToolFilterMiddleware, "
        "otherwise direct solar tools become invisible to the model."
    )

    supervisor_tool_names = {tool.name for tool in supervisor_tools()}
    expected_visible = {
        "geocode_location",
        "estimate_solar_production_with_pvgis",
        "get_solar_base_scenario_candidates",
        "get_assumption_candidates",
        "calculate_system_kwp",
        "calculate_annual_consumption",
        "calculate_coverage",
        "estimate_panels_for_future_target",
        "calculate_panel_capacity_by_area",
        "calculate_required_area_for_panels",
        "calculate_row_spacing_for_self_shading",
        "evaluate_layout_feasibility",
    }
    missing = expected_visible - supervisor_tool_names
    assert not missing, f"supervisor_tools() missing core solar tools: {missing}"


def test_tool_filter_does_not_expose_specialized_subagent_tools_to_supervisor() -> None:
    """Specialized subagent tools must stay scoped to their subagent.

    The supervisor delegates to specialists via ``task``. Tools owned by
    battery-advisor, subsidy-finder, energy-economics-advisor or
    rdtools-analyzer must not be registered directly on the supervisor —
    otherwise the supervisor could shortcut delegation and the routing
    decision becomes ambiguous.
    """

    from app.agents.solar_agent import supervisor_tools

    supervisor_tool_names = {tool.name for tool in supervisor_tools()}
    forbidden = {
        "estimate_battery_size",
        "compare_battery_scenarios",
        "search_subsidies",
        "evaluate_subsidy_compatibility",
        "search_municipal_tax_benefits",
        "search_tax_deduction_candidates",
        "estimate_self_consumption_savings",
        "estimate_export_compensation",
        "estimate_export_sale_revenue",
        "estimate_energy_bill_impact",
        "compare_battery_vs_export",
        "get_pvpc_surplus_compensation_price",
        "get_pvpc_import_reference_price",
        "get_market_sale_reference_price",
        "normalize_energy_price_series",
        "calculate_degradation_projection",
        "calculate_lifetime_threshold",
        "compare_degradation_scenarios",
        "validate_rdtools_csv",
        "analyze_existing_installation_with_rdtools",
    }
    leaked = forbidden & supervisor_tool_names
    assert not leaked, (
        f"Specialized subagent tools leaked onto the supervisor: {leaked}"
    )
