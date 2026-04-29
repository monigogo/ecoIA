"""Conceptual regression tests: ahorro vs compensación vs venta vs OMIE.

These tests are deliberately small but enforce the project invariants:

- compensation result is not the same shape or semantics as sale revenue;
- OMIE results carry the wholesale-reference warning;
- free market export compensation requires an explicit export price;
- PVPC surplus indicator default stays at 1739;
- sale revenue refuses to invent net income without explicit costs.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.economics import ExportCompensationRequest
from app.services.omie_service import OMIEService
from app.tools.economic_tools import (
    build_estimate_export_compensation_tool,
    build_estimate_export_sale_revenue_tool,
)
from app.tools.price_tools import build_get_market_sale_reference_price_tool


def test_export_compensation_is_not_sale_revenue() -> None:
    """Compensation and sale revenue tools must produce structurally
    distinct outputs so the agent cannot confuse them."""

    compensation = build_estimate_export_compensation_tool().invoke(
        {
            "exported_energy_kwh": 200.0,
            "contract_type": "pvpc",
            "export_price_eur_kwh": 0.06,
            "billing_period": "monthly",
            "energy_term_cost_eur": 8.0,
            "compensation_cap_enabled": True,
        }
    )
    sale = build_estimate_export_sale_revenue_tool().invoke(
        {
            "exported_energy_kwh": 200.0,
            "average_market_price_eur_kwh": 0.06,
            "billing_period": "monthly",
            "market_reference_source": "omie",
        }
    )

    assert "applied_compensation_eur" in compensation
    assert "uncompensated_excess_value_eur" in compensation
    assert "estimated_net_sale_revenue_eur" not in compensation

    assert "gross_sale_revenue_eur" in sale
    assert "estimated_net_sale_revenue_eur" in sale
    assert "applied_compensation_eur" not in sale


def test_free_market_requires_explicit_export_price() -> None:
    """A free-market export with positive energy must carry a price."""

    with pytest.raises(ValidationError, match="export_price_eur_kwh is required"):
        ExportCompensationRequest(
            exported_energy_kwh=100.0,
            contract_type="free_market",
            billing_period="monthly",
            compensation_cap_enabled=False,
        )


def test_pvpc_surplus_indicator_default_is_1739() -> None:
    settings = get_settings()
    assert settings.esios_indicator_pvpc_surplus_compensation == 1739


def test_sale_revenue_refuses_net_without_costs() -> None:
    payload = build_estimate_export_sale_revenue_tool().invoke(
        {
            "exported_energy_kwh": 100.0,
            "average_market_price_eur_kwh": 0.05,
            "billing_period": "monthly",
            "market_reference_source": "user_provided",
        }
    )

    assert payload["estimated_net_sale_revenue_eur"] is None
    assert any(
        "net sale revenue cannot be estimated" in warning
        for warning in payload["warnings"]
    )


@pytest.mark.asyncio
@respx.mock
async def test_omie_market_price_carries_wholesale_warning() -> None:
    rows = ["MARGINALPDBC;"]
    for hour in range(1, 25):
        rows.append(f"2026;04;01;{hour:02d};50.0;60.0;")
    rows.append("*")
    text = "\n".join(rows)
    respx.get("https://www.omie.es/es/file-download").mock(
        return_value=httpx.Response(200, text=text)
    )

    async with httpx.AsyncClient() as client:
        service = OMIEService(http_client=client, max_retries=1)
        tool = build_get_market_sale_reference_price_tool(service=service)
        payload = await tool.ainvoke(
            {
                "start_date": datetime(2026, 4, 1, tzinfo=UTC).isoformat(),
                "end_date": datetime(2026, 4, 1, tzinfo=UTC).isoformat(),
                "market_area": "ES",
                "aggregation": "hourly",
            }
        )

    codes = {warning["code"] for warning in payload["warnings"]}
    assert "omie_wholesale_reference_only" in codes
