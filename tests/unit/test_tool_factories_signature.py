"""Regression guard: tool factories must not accept ``trace_logger``.

Tracing is captured by ``NaturalTraceMiddleware`` from the agent runtime.
Factories used to expose an optional ``trace_logger`` parameter that was
never wired in production. Re-introducing it would create two tracing
paths and risk events being emitted from the tool but never persisted by
the conversation orchestrator.
"""

from __future__ import annotations

import inspect

from app.tools.assumption_tools import build_assumption_tool
from app.tools.battery_tools import (
    build_compare_battery_scenarios_tool,
    build_estimate_battery_size_tool,
)
from app.tools.degradation_tools import (
    build_calculate_degradation_projection_tool,
    build_calculate_lifetime_threshold_tool,
    build_compare_degradation_scenarios_tool,
)
from app.tools.economic_tools import (
    build_compare_battery_vs_export_tool,
    build_estimate_energy_bill_impact_tool,
    build_estimate_export_compensation_tool,
    build_estimate_export_sale_revenue_tool,
    build_estimate_self_consumption_savings_tool,
)
from app.tools.geocoding_tools import build_geocoding_tool
from app.tools.layout_tools import (
    build_calculate_panel_capacity_by_area_tool,
    build_calculate_required_area_for_panels_tool,
    build_calculate_row_spacing_for_self_shading_tool,
    build_evaluate_layout_feasibility_tool,
)
from app.tools.price_tools import (
    build_get_market_sale_reference_price_tool,
    build_get_pvpc_import_reference_price_tool,
    build_get_pvpc_surplus_compensation_price_tool,
    build_normalize_energy_price_series_tool,
)
from app.tools.pvgis_tools import build_pvgis_tool
from app.tools.rdtools_tools import (
    build_analyze_existing_installation_with_rdtools_tool,
    build_validate_rdtools_csv_tool,
)
from app.tools.solar_scenario_tools import build_solar_base_scenario_tool
from app.tools.solar_calculation_tools import (
    build_calculate_annual_consumption_tool,
    build_calculate_coverage_tool,
    build_calculate_system_kwp_tool,
    build_estimate_panels_for_future_target_tool,
)
from app.tools.subsidy_tools import (
    build_evaluate_subsidy_compatibility_tool,
    build_search_municipal_tax_benefits_tool,
    build_search_subsidies_tool,
    build_search_tax_deduction_candidates_tool,
)

ALL_FACTORIES = [
    build_assumption_tool,
    build_compare_battery_scenarios_tool,
    build_estimate_battery_size_tool,
    build_calculate_degradation_projection_tool,
    build_calculate_lifetime_threshold_tool,
    build_compare_degradation_scenarios_tool,
    build_compare_battery_vs_export_tool,
    build_estimate_energy_bill_impact_tool,
    build_estimate_export_compensation_tool,
    build_estimate_export_sale_revenue_tool,
    build_estimate_self_consumption_savings_tool,
    build_geocoding_tool,
    build_calculate_panel_capacity_by_area_tool,
    build_calculate_required_area_for_panels_tool,
    build_calculate_row_spacing_for_self_shading_tool,
    build_evaluate_layout_feasibility_tool,
    build_get_market_sale_reference_price_tool,
    build_get_pvpc_import_reference_price_tool,
    build_get_pvpc_surplus_compensation_price_tool,
    build_normalize_energy_price_series_tool,
    build_pvgis_tool,
    build_analyze_existing_installation_with_rdtools_tool,
    build_validate_rdtools_csv_tool,
    build_solar_base_scenario_tool,
    build_calculate_annual_consumption_tool,
    build_calculate_coverage_tool,
    build_calculate_system_kwp_tool,
    build_estimate_panels_for_future_target_tool,
    build_evaluate_subsidy_compatibility_tool,
    build_search_municipal_tax_benefits_tool,
    build_search_subsidies_tool,
    build_search_tax_deduction_candidates_tool,
]


def test_tool_factories_do_not_accept_trace_logger() -> None:
    offenders: list[str] = []
    for factory in ALL_FACTORIES:
        params = inspect.signature(factory).parameters
        if "trace_logger" in params:
            offenders.append(factory.__name__)
    assert not offenders, (
        "Tool factories must not expose a ``trace_logger`` parameter. "
        "Tracing belongs to NaturalTraceMiddleware, not to factory injection. "
        f"Offenders: {offenders}"
    )


def test_tool_factories_expose_only_service_or_no_args() -> None:
    """Allowed factory signatures: () or (service=None). Anything else is a
    re-introduced injection seam that must be reviewed before adding back."""

    allowed = [frozenset(), frozenset({"service"})]
    offenders: list[tuple[str, frozenset[str]]] = []
    for factory in ALL_FACTORIES:
        params = frozenset(inspect.signature(factory).parameters.keys())
        if params not in allowed:
            offenders.append((factory.__name__, params))
    assert not offenders, (
        "Tool factories should accept either nothing or a single optional "
        f"`service` override. Offenders: {offenders}"
    )
