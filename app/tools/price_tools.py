"""LangChain tools wrapping the energy-price providers (ESIOS, OMIE).

Reasoning rules (see ``AGENTS.md``):

- The tools fetch and normalize. They never invent a price.
- They never decide whether the user is on PVPC vs free market — the
  agent must reason about that and call the right tool with the right
  indicator.
- Every result carries source, indicator/market area, unit, date range,
  and structured warnings. Downstream economic tools consume the
  normalized ``average_price_eur_kwh`` or the full ``price_series``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from langchain_core.tools import tool

from app.core.config import get_settings
from app.core.errors import ConfigurationError
from app.schemas.prices import (
    EsiosIndicatorRequest,
    OmieMarketPriceRequest,
    PricePoint,
    PriceSeriesNormalizationRequest,
    PriceSeriesResult,
    PriceSource,
    PriceUnit,
)
from app.services.esios_service import ESIOSService
from app.services.omie_service import OMIEService


@lru_cache(maxsize=1)
def _default_esios_service() -> ESIOSService:
    return ESIOSService()


@lru_cache(maxsize=1)
def _default_omie_service() -> OMIEService:
    return OMIEService()


def _serialize(result: PriceSeriesResult) -> dict[str, Any]:
    return result.model_dump(mode="json")


# ---------------------------------------------------------------------------
# 1) PVPC surplus compensation price (ESIOS indicator 1739 by default)
# ---------------------------------------------------------------------------


def build_get_pvpc_surplus_compensation_price_tool(
    service: ESIOSService | None = None,
):
    """Return a LangChain tool for ESIOS PVPC surplus compensation price."""

    bound_service = service or _default_esios_service()

    @tool("get_pvpc_surplus_compensation_price", args_schema=EsiosIndicatorRequest)
    async def get_pvpc_surplus_compensation_price(
        indicator_id: int,
        start_datetime: datetime,
        end_datetime: datetime,
        aggregation: str = "hourly",
        timezone: str = "Europe/Madrid",
        geo_id: int | None = None,
    ) -> dict[str, Any]:
        """Fetch the PVPC surplus compensation price series from ESIOS.

        Use only for residential customers under PVPC with simplified
        compensation. Do not use for free-market contracts. Returns
        normalized EUR/kWh prices, source metadata, and warnings. If the
        ESIOS token is not configured, raises a controlled error rather
        than fabricating a price.
        """

        request = EsiosIndicatorRequest(
            indicator_id=indicator_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            aggregation=aggregation,  # type: ignore[arg-type]
            timezone=timezone,
            geo_id=geo_id,
        )

        result = await bound_service.fetch_indicator(request)

        return _serialize(result)

    return get_pvpc_surplus_compensation_price


# ---------------------------------------------------------------------------
# 2) PVPC import reference price
# ---------------------------------------------------------------------------


def build_get_pvpc_import_reference_price_tool(
    service: ESIOSService | None = None,
):
    """Return a LangChain tool for the PVPC import reference price."""

    bound_service = service or _default_esios_service()

    @tool("get_pvpc_import_reference_price", args_schema=EsiosIndicatorRequest)
    async def get_pvpc_import_reference_price(
        indicator_id: int,
        start_datetime: datetime,
        end_datetime: datetime,
        aggregation: str = "hourly",
        timezone: str = "Europe/Madrid",
        geo_id: int | None = None,
    ) -> dict[str, Any]:
        """Fetch a PVPC import reference price series from ESIOS.

        The ESIOS indicator id must be configured explicitly via the
        ``indicator_id`` argument or via the
        ``ESIOS_INDICATOR_PVPC_IMPORT_REFERENCE`` setting; the project
        does not hardcode an opaque PVPC import indicator. Use only as a
        reference price for PVPC scenarios — never assume the user is on
        PVPC.
        """

        settings = get_settings()
        resolved_id = indicator_id or settings.esios_indicator_pvpc_import_reference
        if not resolved_id:
            raise ConfigurationError(
                "ESIOS indicator for PVPC import reference price is not configured. "
                "Pass an explicit indicator_id or set ESIOS_INDICATOR_PVPC_IMPORT_REFERENCE."
            )

        request = EsiosIndicatorRequest(
            indicator_id=resolved_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            aggregation=aggregation,  # type: ignore[arg-type]
            timezone=timezone,
            geo_id=geo_id,
        )

        result = await bound_service.fetch_indicator(request)

        return _serialize(result)

    return get_pvpc_import_reference_price


# ---------------------------------------------------------------------------
# 3) Market sale reference price (OMIE)
# ---------------------------------------------------------------------------


def build_get_market_sale_reference_price_tool(
    service: OMIEService | None = None,
):
    """Return a LangChain tool for OMIE market reference price."""

    bound_service = service or _default_omie_service()

    @tool("get_market_sale_reference_price", args_schema=OmieMarketPriceRequest)
    async def get_market_sale_reference_price(
        start_date: datetime,
        end_date: datetime,
        market_area: str = "ES",
        aggregation: str = "daily",
    ) -> dict[str, Any]:
        """Fetch the OMIE wholesale marginal price series.

        This is a wholesale market reference. It is NOT a residential
        prosumer's net revenue and it is NOT the same as PVPC simplified
        compensation. The result includes structured warnings stating
        that representation, taxes and access charges are not included.
        """

        request = OmieMarketPriceRequest(
            start_date=start_date,
            end_date=end_date,
            market_area=market_area,  # type: ignore[arg-type]
            aggregation=aggregation,  # type: ignore[arg-type]
        )

        result = await bound_service.fetch_marginal_prices(request)

        return _serialize(result)

    return get_market_sale_reference_price


# ---------------------------------------------------------------------------
# 4) Deterministic price normalization
# ---------------------------------------------------------------------------


def build_normalize_energy_price_series_tool():
    """Return a LangChain tool that normalizes a price series to EUR/kWh."""

    @tool("normalize_energy_price_series", args_schema=PriceSeriesNormalizationRequest)
    def normalize_energy_price_series(
        series: list[PricePoint],
        unit_original: PriceUnit,
        source_name: PriceSource,
        date_range_start: datetime,
        date_range_end: datetime,
        aggregation: str,
        source_url: str | None = None,
        indicator_id: int | None = None,
        market_area: str | None = None,
    ) -> dict[str, Any]:
        """Normalize a price series to EUR/kWh deterministically.

        Pure conversion: divides EUR/MWh by 1000, leaves EUR/kWh as is,
        and recomputes ``value_eur_kwh`` for every point and the
        ``average_price_eur_kwh`` over the series. It does not decide
        whether the series applies to a user, and does not pick a
        source.
        """

        if not series:
            raise ValueError("series must contain at least one PricePoint.")

        normalized: list[PricePoint] = []
        for point in series:
            value_eur_kwh = (
                point.value / 1000.0
                if unit_original == PriceUnit.eur_per_mwh
                else point.value
            )
            normalized.append(
                PricePoint(
                    timestamp=point.timestamp,
                    value=point.value,
                    unit=unit_original,
                    value_eur_kwh=value_eur_kwh,
                )
            )

        average_eur_kwh = sum(p.value_eur_kwh for p in normalized) / len(normalized)
        result = PriceSeriesResult(
            source_name=source_name,
            source_url=source_url,
            indicator_id=indicator_id,
            market_area=market_area,  # type: ignore[arg-type]
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            aggregation=aggregation,  # type: ignore[arg-type]
            unit_original=unit_original,
            unit_normalized=PriceUnit.eur_per_kwh,
            average_price_eur_kwh=average_eur_kwh,
            price_series=normalized,
            retrieved_at=datetime.now(tz=UTC),
            warnings=[],
        )

        return _serialize(result)

    return normalize_energy_price_series


# Default exports for agent construction.
get_pvpc_surplus_compensation_price = build_get_pvpc_surplus_compensation_price_tool()
get_pvpc_import_reference_price = build_get_pvpc_import_reference_price_tool()
get_market_sale_reference_price = build_get_market_sale_reference_price_tool()
normalize_energy_price_series = build_normalize_energy_price_series_tool()


__all__ = [
    "build_get_market_sale_reference_price_tool",
    "build_get_pvpc_import_reference_price_tool",
    "build_get_pvpc_surplus_compensation_price_tool",
    "build_normalize_energy_price_series_tool",
    "get_market_sale_reference_price",
    "get_pvpc_import_reference_price",
    "get_pvpc_surplus_compensation_price",
    "normalize_energy_price_series",
]
