"""Schemas for deterministic energy economics calculations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ContractType = Literal["pvpc", "free_market", "unknown"]


class SelfConsumptionSavingsRequest(BaseModel):
    """Explicit inputs for direct self-consumption savings."""

    model_config = ConfigDict(extra="forbid")

    solar_generation_kwh: float = Field(gt=0.0)
    self_consumed_kwh: float = Field(ge=0.0)
    grid_import_price_eur_kwh: float = Field(gt=0.0)
    billing_period: str = Field(min_length=1)
    taxes_included: bool

    @model_validator(mode="after")
    def validate_energy_balance(self) -> SelfConsumptionSavingsRequest:
        if self.self_consumed_kwh > self.solar_generation_kwh:
            raise ValueError("self_consumed_kwh cannot exceed solar_generation_kwh.")
        return self


class SelfConsumptionSavingsResult(BaseModel):
    """Normalized output for direct self-consumption savings."""

    model_config = ConfigDict(extra="forbid")

    direct_self_consumption_savings_eur: float
    avoided_grid_kwh: float
    effective_import_price_eur_kwh: float
    method_used: str
    warnings: list[str] = Field(default_factory=list)


class ExportCompensationRequest(BaseModel):
    """Explicit inputs for export compensation calculations."""

    model_config = ConfigDict(extra="forbid")

    exported_energy_kwh: float = Field(ge=0.0)
    contract_type: ContractType
    export_price_eur_kwh: float | None = Field(default=None, ge=0.0)
    billing_period: str = Field(min_length=1)
    energy_term_cost_eur: float | None = Field(default=None, ge=0.0)
    compensation_cap_enabled: bool

    @model_validator(mode="after")
    def validate_price_presence(self) -> ExportCompensationRequest:
        if self.exported_energy_kwh > 0.0 and self.export_price_eur_kwh is None:
            raise ValueError(
                "export_price_eur_kwh is required when exported_energy_kwh is greater than zero."
            )
        return self


class ExportCompensationResult(BaseModel):
    """Normalized output for compensation of exported energy."""

    model_config = ConfigDict(extra="forbid")

    gross_export_value_eur: float
    applied_compensation_eur: float
    uncompensated_excess_value_eur: float
    price_source: str
    method_used: str
    warnings: list[str] = Field(default_factory=list)


class EnergyBillImpactRequest(BaseModel):
    """Explicit inputs for monthly bill impact estimation."""

    model_config = ConfigDict(extra="forbid")

    monthly_consumption_kwh: float = Field(gt=0.0)
    solar_generation_kwh: float = Field(ge=0.0)
    self_consumed_kwh: float = Field(ge=0.0)
    exported_energy_kwh: float = Field(ge=0.0)
    grid_import_kwh: float = Field(ge=0.0)
    import_price_eur_kwh: float = Field(gt=0.0)
    contract_type: ContractType
    export_price_eur_kwh: float | None = Field(default=None, ge=0.0)
    fixed_costs_eur: float | None = Field(default=None, ge=0.0)
    taxes_and_charges_eur: float | None = Field(default=None, ge=0.0)
    compensation_cap_enabled: bool

    @model_validator(mode="after")
    def validate_energy_consistency(self) -> EnergyBillImpactRequest:
        if self.self_consumed_kwh > self.solar_generation_kwh:
            raise ValueError("self_consumed_kwh cannot exceed solar_generation_kwh.")
        if self.self_consumed_kwh + self.exported_energy_kwh > self.solar_generation_kwh:
            raise ValueError(
                "self_consumed_kwh plus exported_energy_kwh cannot exceed solar_generation_kwh."
            )
        if self.self_consumed_kwh + self.grid_import_kwh > self.monthly_consumption_kwh + 1e-9:
            raise ValueError(
                "self_consumed_kwh plus grid_import_kwh cannot exceed monthly_consumption_kwh."
            )
        if self.exported_energy_kwh > 0.0 and self.export_price_eur_kwh is None:
            raise ValueError(
                "export_price_eur_kwh is required when exported_energy_kwh is greater than zero."
            )
        return self


class EnergyBillImpactResult(BaseModel):
    """Normalized bill-impact output."""

    model_config = ConfigDict(extra="forbid")

    baseline_energy_cost_eur: float
    post_solar_energy_cost_eur: float
    self_consumption_savings_eur: float
    export_compensation_eur: float
    total_monthly_savings_eur: float
    total_annual_savings_eur: float
    warnings: list[str] = Field(default_factory=list)


class ExportSaleRevenueRequest(BaseModel):
    """Explicit inputs for real export-sale revenue estimation.

    Distinct from simplified compensation: this represents selling
    surplus energy as a producer or via a representation contract. The
    request never assumes fees, taxes, or representation costs — they
    must be supplied explicitly when a net figure is wanted.
    """

    model_config = ConfigDict(extra="forbid")

    exported_energy_kwh: float = Field(ge=0.0)
    average_market_price_eur_kwh: float = Field(gt=0.0)
    billing_period: str = Field(min_length=1)
    market_reference_source: str = Field(
        min_length=1,
        description="Origin of the market price (for example 'omie', 'user_provided').",
    )
    fees_eur: float | None = Field(default=None, ge=0.0)
    taxes_eur: float | None = Field(default=None, ge=0.0)
    representative_costs_eur: float | None = Field(default=None, ge=0.0)


class ExportSaleRevenueResult(BaseModel):
    """Normalized output for real export-sale revenue."""

    model_config = ConfigDict(extra="forbid")

    gross_sale_revenue_eur: float
    estimated_net_sale_revenue_eur: float | None
    market_reference_source: str
    average_market_price_eur_kwh: float
    included_costs: list[str] = Field(default_factory=list)
    excluded_costs: list[str] = Field(default_factory=list)
    method_used: str
    warnings: list[str] = Field(default_factory=list)


class BatteryVsExportRequest(BaseModel):
    """Explicit inputs for comparing battery storage against exporting energy."""

    model_config = ConfigDict(extra="forbid")

    exported_energy_kwh: float = Field(ge=0.0)
    export_price_eur_kwh: float = Field(ge=0.0)
    import_price_eur_kwh: float = Field(gt=0.0)
    battery_roundtrip_efficiency_pct: float = Field(gt=0.0, le=100.0)
    battery_cost_eur: float | None = Field(default=None, ge=0.0)
    battery_lifetime_years: float | None = Field(default=None, gt=0.0)


class BatteryVsExportResult(BaseModel):
    """Normalized comparison of exported vs stored energy value."""

    model_config = ConfigDict(extra="forbid")

    value_if_exported_eur: float
    value_if_stored_and_used_later_eur: float
    difference_eur: float
    warnings: list[str] = Field(default_factory=list)
