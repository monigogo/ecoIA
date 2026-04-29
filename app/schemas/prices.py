"""Schemas for energy price providers (ESIOS, OMIE) and price tools.

Reasoning-first contract:

- All inputs are explicit. No silent defaults.
- Outputs always carry source, unit, date range, and warnings.
- Currency normalization is mechanical, not heuristic — handled by
  ``normalize_energy_price_series``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PriceSource(StrEnum):
    """Recognized data sources. Extend explicitly when a new provider lands."""

    esios = "esios"
    omie = "omie"
    user_provided = "user_provided"


class PriceUnit(StrEnum):
    """Recognized price units."""

    eur_per_mwh = "EUR_PER_MWH"
    eur_per_kwh = "EUR_PER_KWH"


# Aggregation requested from the provider when applicable.
PriceAggregation = Literal["hourly", "daily", "monthly", "yearly"]

# Market areas exposed by OMIE.
MarketArea = Literal["ES", "PT", "MIBEL"]


class PricePoint(BaseModel):
    """A single timestamped price observation."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    value: float
    unit: PriceUnit
    value_eur_kwh: float = Field(
        description="Value normalized to EUR per kWh for downstream tools.",
    )


class PriceProviderWarning(BaseModel):
    """Structured warning attached to a price result."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class PriceSeriesResult(BaseModel):
    """Normalized price series result returned by every price tool."""

    model_config = ConfigDict(extra="forbid")

    source_name: PriceSource
    source_url: str | None = None
    indicator_id: int | None = None
    market_area: MarketArea | None = None
    date_range_start: datetime
    date_range_end: datetime
    aggregation: PriceAggregation
    unit_original: PriceUnit
    unit_normalized: PriceUnit = PriceUnit.eur_per_kwh
    average_price_eur_kwh: float
    price_series: list[PricePoint] = Field(default_factory=list)
    retrieved_at: datetime
    warnings: list[PriceProviderWarning] = Field(default_factory=list)


class EsiosIndicatorRequest(BaseModel):
    """Explicit input to query an ESIOS indicator."""

    model_config = ConfigDict(extra="forbid")

    indicator_id: int = Field(gt=0)
    start_datetime: datetime
    end_datetime: datetime
    aggregation: PriceAggregation = "hourly"
    timezone: str = Field(default="Europe/Madrid", min_length=1)
    geo_id: int | None = None

    @model_validator(mode="after")
    def validate_window(self) -> EsiosIndicatorRequest:
        if self.end_datetime <= self.start_datetime:
            raise ValueError("end_datetime must be strictly after start_datetime.")
        return self


class OmieMarketPriceRequest(BaseModel):
    """Explicit input for an OMIE market price query."""

    model_config = ConfigDict(extra="forbid")

    start_date: datetime
    end_date: datetime
    market_area: MarketArea = "ES"
    aggregation: PriceAggregation = "daily"

    @model_validator(mode="after")
    def validate_window(self) -> OmieMarketPriceRequest:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class PriceSeriesNormalizationRequest(BaseModel):
    """Explicit input for the deterministic price-normalization tool."""

    model_config = ConfigDict(extra="forbid")

    series: list[PricePoint] = Field(min_length=1)
    unit_original: PriceUnit
    source_name: PriceSource
    date_range_start: datetime
    date_range_end: datetime
    aggregation: PriceAggregation
    source_url: str | None = None
    indicator_id: int | None = None
    market_area: MarketArea | None = None


__all__ = [
    "EsiosIndicatorRequest",
    "MarketArea",
    "OmieMarketPriceRequest",
    "PriceAggregation",
    "PricePoint",
    "PriceProviderWarning",
    "PriceSeriesNormalizationRequest",
    "PriceSeriesResult",
    "PriceSource",
    "PriceUnit",
]
