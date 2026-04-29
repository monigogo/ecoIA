"""Deterministic LangChain tools for solar energy economics."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.schemas.economics import (
    BatteryVsExportRequest,
    BatteryVsExportResult,
    EnergyBillImpactRequest,
    EnergyBillImpactResult,
    ExportCompensationRequest,
    ExportCompensationResult,
    ExportSaleRevenueRequest,
    ExportSaleRevenueResult,
    SelfConsumptionSavingsRequest,
    SelfConsumptionSavingsResult,
)


def _calculate_export_compensation_values(
    *,
    exported_energy_kwh: float,
    export_price_eur_kwh: float,
    energy_term_cost_eur: float | None,
    compensation_cap_enabled: bool,
) -> tuple[float, float, float]:
    gross_export_value = exported_energy_kwh * export_price_eur_kwh
    if compensation_cap_enabled and energy_term_cost_eur is not None:
        applied_compensation = min(gross_export_value, energy_term_cost_eur)
    else:
        applied_compensation = gross_export_value
    uncompensated_excess_value = gross_export_value - applied_compensation
    return gross_export_value, applied_compensation, uncompensated_excess_value


def build_estimate_self_consumption_savings_tool():
    """Return a deterministic LangChain tool for direct self-consumption savings."""

    @tool("estimate_self_consumption_savings", args_schema=SelfConsumptionSavingsRequest)
    def estimate_self_consumption_savings(
        solar_generation_kwh: float,
        self_consumed_kwh: float,
        grid_import_price_eur_kwh: float,
        billing_period: str,
        taxes_included: bool,
    ) -> dict[str, Any]:
        """Estimate direct savings from consuming PV generation behind the meter."""

        response = SelfConsumptionSavingsResult(
            direct_self_consumption_savings_eur=self_consumed_kwh * grid_import_price_eur_kwh,
            avoided_grid_kwh=self_consumed_kwh,
            effective_import_price_eur_kwh=grid_import_price_eur_kwh,
            method_used="direct_self_consumption_value",
        )

        return response.model_dump()

    return estimate_self_consumption_savings


def build_estimate_export_compensation_tool():
    """Return a deterministic LangChain tool for export compensation calculations."""

    @tool("estimate_export_compensation", args_schema=ExportCompensationRequest)
    def estimate_export_compensation(
        exported_energy_kwh: float,
        contract_type: str,
        billing_period: str,
        compensation_cap_enabled: bool,
        export_price_eur_kwh: float | None = None,
        energy_term_cost_eur: float | None = None,
    ) -> dict[str, Any]:
        """Estimate export compensation from explicit contract price inputs."""

        resolved_export_price = export_price_eur_kwh or 0.0
        warnings: list[str] = []
        if contract_type == "unknown":
            warnings.append(
                "Contract type is unknown; compensation was calculated mechanically from the explicit price only."
            )

        (
            gross_export_value,
            applied_compensation,
            uncompensated_excess_value,
        ) = _calculate_export_compensation_values(
            exported_energy_kwh=exported_energy_kwh,
            export_price_eur_kwh=resolved_export_price,
            energy_term_cost_eur=energy_term_cost_eur,
            compensation_cap_enabled=compensation_cap_enabled,
        )

        response = ExportCompensationResult(
            gross_export_value_eur=gross_export_value,
            applied_compensation_eur=applied_compensation,
            uncompensated_excess_value_eur=uncompensated_excess_value,
            price_source="explicit_export_price",
            method_used="mechanical_export_compensation",
            warnings=warnings,
        )

        return response.model_dump()

    return estimate_export_compensation


def build_estimate_energy_bill_impact_tool():
    """Return a deterministic LangChain tool for overall bill-impact estimation."""

    @tool("estimate_energy_bill_impact", args_schema=EnergyBillImpactRequest)
    def estimate_energy_bill_impact(
        monthly_consumption_kwh: float,
        solar_generation_kwh: float,
        self_consumed_kwh: float,
        exported_energy_kwh: float,
        grid_import_kwh: float,
        import_price_eur_kwh: float,
        contract_type: str,
        compensation_cap_enabled: bool,
        export_price_eur_kwh: float | None = None,
        fixed_costs_eur: float | None = None,
        taxes_and_charges_eur: float | None = None,
    ) -> dict[str, Any]:
        """Estimate monthly and annual bill impact from explicit energy and price inputs."""

        resolved_export_price = export_price_eur_kwh or 0.0
        self_consumption_savings = self_consumed_kwh * import_price_eur_kwh
        baseline_energy_term = monthly_consumption_kwh * import_price_eur_kwh
        post_solar_energy_term = grid_import_kwh * import_price_eur_kwh
        _, export_compensation, _ = _calculate_export_compensation_values(
            exported_energy_kwh=exported_energy_kwh,
            export_price_eur_kwh=resolved_export_price,
            energy_term_cost_eur=post_solar_energy_term,
            compensation_cap_enabled=compensation_cap_enabled,
        )
        resolved_fixed_costs = fixed_costs_eur or 0.0
        resolved_taxes = taxes_and_charges_eur or 0.0
        baseline_total = baseline_energy_term + resolved_fixed_costs + resolved_taxes
        post_solar_total = post_solar_energy_term + resolved_fixed_costs + resolved_taxes
        post_solar_total -= export_compensation
        total_monthly_savings = baseline_total - post_solar_total

        warnings: list[str] = []
        if contract_type == "unknown":
            warnings.append(
                "Contract type is unknown; bill impact was calculated mechanically from the explicit prices only."
            )
        if fixed_costs_eur is None:
            warnings.append("fixed_costs_eur was omitted; the result excludes non-energy fixed costs.")
        if taxes_and_charges_eur is None:
            warnings.append(
                "taxes_and_charges_eur was omitted; the result excludes non-energy taxes and charges."
            )

        response = EnergyBillImpactResult(
            baseline_energy_cost_eur=baseline_total,
            post_solar_energy_cost_eur=post_solar_total,
            self_consumption_savings_eur=self_consumption_savings,
            export_compensation_eur=export_compensation,
            total_monthly_savings_eur=total_monthly_savings,
            total_annual_savings_eur=total_monthly_savings * 12.0,
            warnings=warnings,
        )

        return response.model_dump()

    return estimate_energy_bill_impact


def build_estimate_export_sale_revenue_tool():
    """Return a deterministic LangChain tool for real export-sale revenue.

    This tool is conceptually distinct from
    :func:`build_estimate_export_compensation_tool`:

    - Compensation = bill credit under simplified PVPC. Capped by the
      energy term, never produces a negative bill.
    - Sale = real wholesale or representation-based sale of surplus
      energy. May be subject to fees, taxes, and representation costs
      that the agent must supply explicitly.

    The tool computes ``gross_sale_revenue_eur`` always. It computes
    ``estimated_net_sale_revenue_eur`` only when at least one explicit
    cost component (fees, taxes, or representative costs) is supplied;
    otherwise it returns ``None`` plus an explicit warning, so the
    agent never reports a fabricated net figure.
    """

    @tool("estimate_export_sale_revenue", args_schema=ExportSaleRevenueRequest)
    def estimate_export_sale_revenue(
        exported_energy_kwh: float,
        average_market_price_eur_kwh: float,
        billing_period: str,
        market_reference_source: str,
        fees_eur: float | None = None,
        taxes_eur: float | None = None,
        representative_costs_eur: float | None = None,
    ) -> dict[str, Any]:
        """Estimate revenue from selling surplus energy under explicit prices."""

        gross_sale_revenue_eur = exported_energy_kwh * average_market_price_eur_kwh

        cost_components: dict[str, float | None] = {
            "fees_eur": fees_eur,
            "taxes_eur": taxes_eur,
            "representative_costs_eur": representative_costs_eur,
        }
        explicit = {name: value for name, value in cost_components.items() if value is not None}
        excluded = [name for name, value in cost_components.items() if value is None]

        warnings: list[str] = [
            "Real sale revenue is not the same as PVPC simplified compensation. "
            "Net revenue depends on contract type, representation, taxes, and access charges.",
        ]

        if explicit:
            estimated_net_sale_revenue_eur: float | None = gross_sale_revenue_eur - sum(
                explicit.values()
            )
            if excluded:
                warnings.append(
                    "Net sale revenue excludes the following cost components that were "
                    f"not supplied: {', '.join(sorted(excluded))}."
                )
        else:
            estimated_net_sale_revenue_eur = None
            warnings.append(
                "No explicit fees, taxes, or representation costs were supplied; "
                "net sale revenue cannot be estimated and is reported as null."
            )

        response = ExportSaleRevenueResult(
            gross_sale_revenue_eur=gross_sale_revenue_eur,
            estimated_net_sale_revenue_eur=estimated_net_sale_revenue_eur,
            market_reference_source=market_reference_source,
            average_market_price_eur_kwh=average_market_price_eur_kwh,
            included_costs=sorted(explicit.keys()),
            excluded_costs=sorted(excluded),
            method_used="explicit_market_price_revenue",
            warnings=warnings,
        )

        return response.model_dump()

    return estimate_export_sale_revenue


def build_compare_battery_vs_export_tool():
    """Return a deterministic LangChain tool for comparing storage vs export value."""

    @tool("compare_battery_vs_export", args_schema=BatteryVsExportRequest)
    def compare_battery_vs_export(
        exported_energy_kwh: float,
        export_price_eur_kwh: float,
        import_price_eur_kwh: float,
        battery_roundtrip_efficiency_pct: float,
        battery_cost_eur: float | None = None,
        battery_lifetime_years: float | None = None,
    ) -> dict[str, Any]:
        """Compare the gross value of exporting energy against storing and later consuming it."""

        value_if_exported = exported_energy_kwh * export_price_eur_kwh
        value_if_stored = (
            exported_energy_kwh
            * (battery_roundtrip_efficiency_pct / 100.0)
            * import_price_eur_kwh
        )
        warnings: list[str] = []
        if battery_cost_eur is not None and battery_lifetime_years is not None:
            warnings.append(
                "Battery capex and lifetime were supplied for context only; this comparison is still gross-energy-value only."
            )

        response = BatteryVsExportResult(
            value_if_exported_eur=value_if_exported,
            value_if_stored_and_used_later_eur=value_if_stored,
            difference_eur=value_if_stored - value_if_exported,
            warnings=warnings,
        )

        return response.model_dump()

    return compare_battery_vs_export


estimate_self_consumption_savings = build_estimate_self_consumption_savings_tool()
estimate_export_compensation = build_estimate_export_compensation_tool()
estimate_export_sale_revenue = build_estimate_export_sale_revenue_tool()
estimate_energy_bill_impact = build_estimate_energy_bill_impact_tool()
compare_battery_vs_export = build_compare_battery_vs_export_tool()


__all__ = [
    "build_compare_battery_vs_export_tool",
    "build_estimate_energy_bill_impact_tool",
    "build_estimate_export_compensation_tool",
    "build_estimate_export_sale_revenue_tool",
    "build_estimate_self_consumption_savings_tool",
    "compare_battery_vs_export",
    "estimate_energy_bill_impact",
    "estimate_export_compensation",
    "estimate_export_sale_revenue",
    "estimate_self_consumption_savings",
]
