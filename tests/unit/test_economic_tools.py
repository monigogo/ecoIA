from __future__ import annotations

import json

import pytest

from app.tools.economic_tools import (
    build_compare_battery_vs_export_tool,
    build_estimate_energy_bill_impact_tool,
    build_estimate_export_compensation_tool,
    build_estimate_export_sale_revenue_tool,
    build_estimate_self_consumption_savings_tool,
)


def test_estimate_self_consumption_savings_tool_has_expected_name() -> None:
    tool = build_estimate_self_consumption_savings_tool()
    assert tool.name == "estimate_self_consumption_savings"
    assert tool.description


def test_estimate_export_compensation_tool_has_expected_name() -> None:
    tool = build_estimate_export_compensation_tool()
    assert tool.name == "estimate_export_compensation"


def test_estimate_energy_bill_impact_tool_has_expected_name() -> None:
    tool = build_estimate_energy_bill_impact_tool()
    assert tool.name == "estimate_energy_bill_impact"


def test_compare_battery_vs_export_tool_has_expected_name() -> None:
    tool = build_compare_battery_vs_export_tool()
    assert tool.name == "compare_battery_vs_export"


def test_estimate_self_consumption_savings_returns_serializable_output() -> None:
    tool = build_estimate_self_consumption_savings_tool()
    payload = tool.invoke(
        {
            "solar_generation_kwh": 600.0,
            "self_consumed_kwh": 350.0,
            "grid_import_price_eur_kwh": 0.18,
            "billing_period": "monthly",
            "taxes_included": True,
        }
    )

    assert payload["direct_self_consumption_savings_eur"] == pytest.approx(63.0)
    assert payload["avoided_grid_kwh"] == pytest.approx(350.0)
    json.dumps(payload)


def test_estimate_export_compensation_applies_cap() -> None:
    tool = build_estimate_export_compensation_tool()
    payload = tool.invoke(
        {
            "exported_energy_kwh": 200.0,
            "contract_type": "pvpc",
            "export_price_eur_kwh": 0.08,
            "billing_period": "monthly",
            "energy_term_cost_eur": 10.0,
            "compensation_cap_enabled": True,
        }
    )

    assert payload["gross_export_value_eur"] == pytest.approx(16.0)
    assert payload["applied_compensation_eur"] == pytest.approx(10.0)
    assert payload["uncompensated_excess_value_eur"] == pytest.approx(6.0)


def test_estimate_energy_bill_impact_returns_serializable_output() -> None:
    tool = build_estimate_energy_bill_impact_tool()
    payload = tool.invoke(
        {
            "monthly_consumption_kwh": 500.0,
            "solar_generation_kwh": 600.0,
            "self_consumed_kwh": 350.0,
            "exported_energy_kwh": 200.0,
            "grid_import_kwh": 150.0,
            "import_price_eur_kwh": 0.18,
            "contract_type": "pvpc",
            "export_price_eur_kwh": 0.08,
            "compensation_cap_enabled": True,
        }
    )

    assert payload["self_consumption_savings_eur"] == pytest.approx(63.0)
    assert payload["export_compensation_eur"] == pytest.approx(16.0)
    assert payload["total_monthly_savings_eur"] > 0.0
    assert len(payload["warnings"]) == 2
    json.dumps(payload)


def test_estimate_export_sale_revenue_tool_has_expected_name() -> None:
    tool = build_estimate_export_sale_revenue_tool()
    assert tool.name == "estimate_export_sale_revenue"
    assert tool.description


def test_estimate_export_sale_revenue_returns_gross_only_without_costs() -> None:
    tool = build_estimate_export_sale_revenue_tool()
    payload = tool.invoke(
        {
            "exported_energy_kwh": 200.0,
            "average_market_price_eur_kwh": 0.06,
            "billing_period": "monthly",
            "market_reference_source": "omie",
        }
    )

    assert payload["gross_sale_revenue_eur"] == pytest.approx(12.0)
    assert payload["estimated_net_sale_revenue_eur"] is None
    assert payload["included_costs"] == []
    assert sorted(payload["excluded_costs"]) == [
        "fees_eur",
        "representative_costs_eur",
        "taxes_eur",
    ]
    assert any("net sale revenue" in w.lower() for w in payload["warnings"])
    json.dumps(payload)


def test_estimate_export_sale_revenue_computes_net_when_costs_provided() -> None:
    tool = build_estimate_export_sale_revenue_tool()
    payload = tool.invoke(
        {
            "exported_energy_kwh": 200.0,
            "average_market_price_eur_kwh": 0.06,
            "billing_period": "monthly",
            "market_reference_source": "omie",
            "fees_eur": 1.5,
            "taxes_eur": 1.0,
            "representative_costs_eur": 0.5,
        }
    )

    assert payload["gross_sale_revenue_eur"] == pytest.approx(12.0)
    assert payload["estimated_net_sale_revenue_eur"] == pytest.approx(9.0)
    assert sorted(payload["included_costs"]) == [
        "fees_eur",
        "representative_costs_eur",
        "taxes_eur",
    ]
    assert payload["excluded_costs"] == []


def test_estimate_export_sale_revenue_warns_when_some_costs_missing() -> None:
    tool = build_estimate_export_sale_revenue_tool()
    payload = tool.invoke(
        {
            "exported_energy_kwh": 200.0,
            "average_market_price_eur_kwh": 0.06,
            "billing_period": "monthly",
            "market_reference_source": "omie",
            "fees_eur": 1.0,
        }
    )

    assert payload["gross_sale_revenue_eur"] == pytest.approx(12.0)
    assert payload["estimated_net_sale_revenue_eur"] == pytest.approx(11.0)
    assert payload["included_costs"] == ["fees_eur"]
    assert sorted(payload["excluded_costs"]) == [
        "representative_costs_eur",
        "taxes_eur",
    ]
    assert any("excludes the following cost components" in w for w in payload["warnings"])


def test_compare_battery_vs_export_returns_value_difference() -> None:
    tool = build_compare_battery_vs_export_tool()
    payload = tool.invoke(
        {
            "exported_energy_kwh": 100.0,
            "export_price_eur_kwh": 0.08,
            "import_price_eur_kwh": 0.18,
            "battery_roundtrip_efficiency_pct": 90.0,
        }
    )

    assert payload["value_if_exported_eur"] == pytest.approx(8.0)
    assert payload["value_if_stored_and_used_later_eur"] == pytest.approx(16.2)
    assert payload["difference_eur"] == pytest.approx(8.2)
