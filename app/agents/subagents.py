"""Programmatic subagent definitions.

Each subagent is a plain dict matching the deepagents ``SubAgent`` shape:

    {
        "name": str,
        "description": str,
        "system_prompt": str,
        "tools": list[BaseTool],
        # optional: "model", "middleware", "skills", "interrupt_on"
    }

The descriptions are action-oriented so the supervisor selects the right
subagent without ambiguity. Tool sets are deliberately minimal — each
subagent gets only what it needs.

This module does NOT branch on domain. It is a flat registry. The
supervisor decides whom to delegate to via the ``task`` tool.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from deepagents.middleware.subagents import CompiledSubAgent, SubAgent
from langchain.agents import create_agent

from app.agents.prompts import (
    BATTERY_ADVISOR_PROMPT,
    DEGRADATION_ANALYST_PROMPT,
    ENERGY_ECONOMICS_ADVISOR_PROMPT,
    RDTOOLS_ANALYZER_PROMPT,
    REPORT_SYNTHESIZER_PROMPT,
    SUBSIDY_FINDER_PROMPT,
)
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
from app.tools.price_tools import (
    build_get_market_sale_reference_price_tool,
    build_get_pvpc_import_reference_price_tool,
    build_get_pvpc_surplus_compensation_price_tool,
    build_normalize_energy_price_series_tool,
)
from app.tools.rdtools_tools import (
    build_analyze_existing_installation_with_rdtools_tool,
    build_validate_rdtools_csv_tool,
)
from app.tools.subsidy_tools import (
    build_evaluate_subsidy_compatibility_tool,
    build_search_municipal_tax_benefits_tool,
    build_search_subsidies_tool,
    build_search_tax_deduction_candidates_tool,
)


def build_subagents(
    *,
    middleware_factory: Callable[[], list[Any]] | None = None,
    subagent_response_format: Any | None = None,
    final_response_format: Any | None = None,
) -> list[SubAgent]:
    """Return the canonical list of SolarLife subagents.

    Order is informational only — the supervisor picks by description.
    """

    def _middleware() -> list[Any]:
        if middleware_factory is None:
            return []
        return list(middleware_factory())

    return [
        {
            "name": "degradation-analyst",
            "description": (
                "Estimates lifetime production curve and total energy over the "
                "warranty horizon. Uses manufacturer data when present, "
                "otherwise picks an assumption candidate explicitly and runs "
                "deterministic degradation projections and threshold checks."
            ),
            "system_prompt": DEGRADATION_ANALYST_PROMPT,
            "tools": [
                build_assumption_tool(),
                build_calculate_degradation_projection_tool(),
                build_calculate_lifetime_threshold_tool(),
                build_compare_degradation_scenarios_tool(),
            ],
            "middleware": _middleware(),
            "response_format": subagent_response_format,
        },
        {
            "name": "battery-advisor",
            "description": (
                "Recommends usable and nominal battery capacity ranges. Asks "
                "for autonomy and consumption profile; calls assumption "
                "candidates for DoD, round-trip efficiency, and similar, then "
                "runs deterministic battery sizing and scenario comparison."
            ),
            "system_prompt": BATTERY_ADVISOR_PROMPT,
            "tools": [
                build_assumption_tool(),
                build_estimate_battery_size_tool(),
                build_compare_battery_scenarios_tool(),
            ],
            "middleware": _middleware(),
            "response_format": subagent_response_format,
        },
        {
            "name": "subsidy-finder",
            "description": (
                "Returns a ranked, orientative list of Spanish subsidies for "
                "solar PV given a geographic context. Cites BDNS/SNPSAP IDs "
                "and warns that the user must verify."
            ),
            "system_prompt": SUBSIDY_FINDER_PROMPT,
            "tools": [
                build_assumption_tool(),
                build_geocoding_tool(),
                build_search_subsidies_tool(),
                build_evaluate_subsidy_compatibility_tool(),
                build_search_municipal_tax_benefits_tool(),
                build_search_tax_deduction_candidates_tool(),
            ],
            "middleware": _middleware(),
            "response_format": subagent_response_format,
        },
        {
            "name": "energy-economics-advisor",
            "description": (
                "Estimates direct self-consumption savings, export "
                "compensation, overall bill impact, and the gross-value "
                "comparison between exporting energy and storing it in a battery."
            ),
            "system_prompt": ENERGY_ECONOMICS_ADVISOR_PROMPT,
            "tools": [
                build_assumption_tool(),
                build_get_pvpc_surplus_compensation_price_tool(),
                build_get_pvpc_import_reference_price_tool(),
                build_get_market_sale_reference_price_tool(),
                build_normalize_energy_price_series_tool(),
                build_estimate_self_consumption_savings_tool(),
                build_estimate_export_compensation_tool(),
                build_estimate_export_sale_revenue_tool(),
                build_estimate_energy_bill_impact_tool(),
                build_compare_battery_vs_export_tool(),
            ],
            "middleware": _middleware(),
            "response_format": subagent_response_format,
        },
        {
            "name": "rdtools-analyzer",
            "description": (
                "Analyzes real PV time series with RdTools for degradation, "
                "soiling, and availability. Validates explicit CSV mappings "
                "before deeper analysis and only runs when the user supplied "
                "a CSV or pointer to time-series data."
            ),
            "system_prompt": RDTOOLS_ANALYZER_PROMPT,
            "tools": [
                build_assumption_tool(),
                build_validate_rdtools_csv_tool(),
                build_analyze_existing_installation_with_rdtools_tool(),
            ],
            "middleware": _middleware(),
            "response_format": subagent_response_format,
        },
        {
            "name": "report-synthesizer",
            "description": (
                "Final aggregator. Combines all upstream subagent outputs into "
                "a structured response with assumptions, warnings, and a "
                "natural trace. Call this last."
            ),
            "system_prompt": REPORT_SYNTHESIZER_PROMPT,
            "tools": [],
            "middleware": _middleware(),
            "response_format": final_response_format or subagent_response_format,
        },
    ]


def build_compiled_subagents(
    model: Any,
    *,
    middleware_factory: Callable[[], list[Any]] | None = None,
) -> list[CompiledSubAgent]:
    """Compile declarative subagent specs into ordinary LangChain agents.

    Deepagents task calls only pass the subagent's final message back to the
    supervisor, so subagents intentionally do not use `response_format`.
    """

    compiled: list[CompiledSubAgent] = []
    for spec in build_subagents(middleware_factory=middleware_factory):
        runnable = create_agent(
            model,
            system_prompt=spec["system_prompt"],
            tools=spec["tools"],
            middleware=spec.get("middleware", []),
            name=spec["name"],
        )
        compiled.append(
            {
                "name": spec["name"],
                "description": spec["description"],
                "runnable": runnable,
            }
        )
    return compiled


__all__ = ["CompiledSubAgent", "SubAgent", "build_compiled_subagents", "build_subagents"]
