from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.tools.price_tools import (
    build_get_market_sale_reference_price_tool,
    build_get_pvpc_import_reference_price_tool,
    build_get_pvpc_surplus_compensation_price_tool,
    build_normalize_energy_price_series_tool,
)


def test_pvpc_surplus_tool_has_expected_name() -> None:
    tool = build_get_pvpc_surplus_compensation_price_tool()
    assert tool.name == "get_pvpc_surplus_compensation_price"
    assert tool.description


def test_pvpc_import_reference_tool_has_expected_name() -> None:
    tool = build_get_pvpc_import_reference_price_tool()
    assert tool.name == "get_pvpc_import_reference_price"


def test_market_sale_reference_tool_has_expected_name() -> None:
    tool = build_get_market_sale_reference_price_tool()
    assert tool.name == "get_market_sale_reference_price"


def test_normalize_tool_has_expected_name() -> None:
    tool = build_normalize_energy_price_series_tool()
    assert tool.name == "normalize_energy_price_series"


def test_normalize_converts_eur_per_mwh_to_eur_per_kwh() -> None:
    tool = build_normalize_energy_price_series_tool()
    payload = tool.invoke(
        {
            "series": [
                {
                    "timestamp": datetime(2026, 4, 1, 0, tzinfo=UTC).isoformat(),
                    "value": 80.0,
                    "unit": "EUR_PER_MWH",
                    "value_eur_kwh": 0.0,
                },
                {
                    "timestamp": datetime(2026, 4, 1, 1, tzinfo=UTC).isoformat(),
                    "value": 120.0,
                    "unit": "EUR_PER_MWH",
                    "value_eur_kwh": 0.0,
                },
            ],
            "unit_original": "EUR_PER_MWH",
            "source_name": "user_provided",
            "date_range_start": datetime(2026, 4, 1, tzinfo=UTC).isoformat(),
            "date_range_end": datetime(2026, 4, 2, tzinfo=UTC).isoformat(),
            "aggregation": "hourly",
        }
    )

    assert payload["unit_original"] == "EUR_PER_MWH"
    assert payload["unit_normalized"] == "EUR_PER_KWH"
    assert payload["average_price_eur_kwh"] == pytest.approx(0.1)
    assert payload["price_series"][0]["value_eur_kwh"] == pytest.approx(0.08)
    assert payload["price_series"][1]["value_eur_kwh"] == pytest.approx(0.12)


def test_normalize_keeps_eur_per_kwh_as_is() -> None:
    tool = build_normalize_energy_price_series_tool()
    payload = tool.invoke(
        {
            "series": [
                {
                    "timestamp": datetime(2026, 4, 1, tzinfo=UTC).isoformat(),
                    "value": 0.18,
                    "unit": "EUR_PER_KWH",
                    "value_eur_kwh": 0.18,
                },
            ],
            "unit_original": "EUR_PER_KWH",
            "source_name": "esios",
            "date_range_start": datetime(2026, 4, 1, tzinfo=UTC).isoformat(),
            "date_range_end": datetime(2026, 4, 2, tzinfo=UTC).isoformat(),
            "aggregation": "daily",
            "indicator_id": 1739,
        }
    )

    assert payload["average_price_eur_kwh"] == pytest.approx(0.18)
    assert payload["price_series"][0]["value_eur_kwh"] == pytest.approx(0.18)
    assert payload["indicator_id"] == 1739
