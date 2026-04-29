"""Schemas for the subsidy / tax-benefit / tax-deduction subsystem.

Reasoning rules:

- Tools find candidates. They do not classify eligibility.
- Compatibility is reasoned by an LLM via structured output, not by
  scoring tables.
- Every candidate carries source, status, and a
  ``requires_verification`` flag.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Administration(StrEnum):
    """Recognized administration levels for a public subsidy."""

    eu = "eu"
    state = "state"
    autonomous_community = "autonomous_community"
    province = "province"
    municipality = "municipality"
    other = "other"


class SubsidyStatus(StrEnum):
    """Lifecycle status of a subsidy/call."""

    open = "open"
    upcoming = "upcoming"
    closed = "closed"
    unknown = "unknown"


class TaxBenefitType(StrEnum):
    """Recognized municipal tax benefit categories."""

    ibi = "ibi"
    icio = "icio"
    iae = "iae"
    other = "other"


class TaxDeductionType(StrEnum):
    """Recognized state-level tax deduction categories (AEAT)."""

    irpf_energy_efficiency_demand = "irpf_energy_efficiency_demand"
    irpf_energy_efficiency_consumption = "irpf_energy_efficiency_consumption"
    irpf_residential_rehabilitation = "irpf_residential_rehabilitation"
    irpf_self_consumption_2026 = "irpf_self_consumption_2026"
    other = "other"


class CompatibilityLevel(StrEnum):
    """Reasoned compatibility level for a candidate."""

    high = "high"
    medium = "medium"
    low = "low"
    requires_verification = "requires_verification"


# ---------------------------------------------------------------------------
# Subsidy candidate (BDNS / SNPSAP)
# ---------------------------------------------------------------------------


class SubsidyCandidate(BaseModel):
    """A candidate subsidy returned by BDNS / SNPSAP after normalization."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_name: str = Field(default="BDNS")
    source_url: str | None = None
    administration: Administration
    region: str | None = None
    municipality: str | None = None
    beneficiary_summary: str | None = None
    purpose_summary: str | None = None
    status: SubsidyStatus = SubsidyStatus.unknown
    deadline: date | None = None
    amount_summary: str | None = None
    raw_metadata: dict[str, object] | None = None
    requires_verification: bool = True


class SubsidySearchRequest(BaseModel):
    """Explicit input for ``search_subsidies``."""

    model_config = ConfigDict(extra="forbid")

    project_context: str = Field(min_length=1)
    location_context: str = Field(min_length=1)
    autonomous_community: str | None = None
    municipality: str | None = None
    province: str | None = None
    beneficiary_type: Literal[
        "residential", "smb", "industrial", "public_administration", "other"
    ] = "residential"
    technology: Literal["solar_pv", "solar_thermal", "battery_storage", "other"] = "solar_pv"
    installation_type: Literal["new", "refurbishment", "extension", "other"] = "new"
    has_battery: bool = False
    reasoned_query: str = Field(
        min_length=1,
        description="Free-form natural-language query the agent already reasoned about.",
    )
    date_range_start: date | None = None
    date_range_end: date | None = None

    @model_validator(mode="after")
    def validate_window(self) -> SubsidySearchRequest:
        if (
            self.date_range_start is not None
            and self.date_range_end is not None
            and self.date_range_end < self.date_range_start
        ):
            raise ValueError("date_range_end must be on or after date_range_start.")
        return self


class SubsidySearchResult(BaseModel):
    """Normalized output of ``search_subsidies``."""

    model_config = ConfigDict(extra="forbid")

    candidates: list[SubsidyCandidate] = Field(default_factory=list)
    source_name: str = "BDNS"
    source_url: str | None = None
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Compatibility evaluation
# ---------------------------------------------------------------------------


class CompatibilityEvaluationRequest(BaseModel):
    """Explicit input for ``evaluate_subsidy_compatibility``."""

    model_config = ConfigDict(extra="forbid")

    project_context: str = Field(min_length=1)
    subsidy_candidate: SubsidyCandidate
    available_evidence: str = Field(
        default="",
        description="Documents, datasheets, prior bills, certificates the user already provided.",
    )


class CompatibilityEvaluationResult(BaseModel):
    """Reasoned compatibility evaluation. Never a guarantee."""

    model_config = ConfigDict(extra="forbid")

    compatibility_level: CompatibilityLevel
    reasoning: str = Field(min_length=1)
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    documents_to_verify: list[str] = Field(default_factory=list)
    legal_warning: str = Field(
        default=(
            "This evaluation is orientative; eligibility is decided exclusively by "
            "the issuing administration."
        )
    )


# ---------------------------------------------------------------------------
# Municipal tax benefits
# ---------------------------------------------------------------------------


class MunicipalTaxBenefitCandidate(BaseModel):
    """A municipal IBI/ICIO/IAE benefit candidate."""

    model_config = ConfigDict(extra="forbid")

    municipality: str = Field(min_length=1)
    province: str | None = None
    benefit_type: TaxBenefitType
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source_name: str
    source_url: str | None = None
    validity_status: SubsidyStatus = SubsidyStatus.unknown
    requires_verification: bool = True


class MunicipalTaxBenefitSearchRequest(BaseModel):
    """Explicit input for ``search_municipal_tax_benefits``."""

    model_config = ConfigDict(extra="forbid")

    municipality: str = Field(min_length=1)
    province: str | None = None
    project_type: Literal[
        "residential", "smb", "industrial", "public_administration", "other"
    ] = "residential"
    installation_type: Literal["new", "refurbishment", "extension", "other"] = "new"


class MunicipalTaxBenefitSearchResult(BaseModel):
    """Normalized output of ``search_municipal_tax_benefits``."""

    model_config = ConfigDict(extra="forbid")

    candidates: list[MunicipalTaxBenefitCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# State-level tax deductions (AEAT)
# ---------------------------------------------------------------------------


class TaxDeductionCandidate(BaseModel):
    """A state-level (IRPF) tax deduction candidate from AEAT."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_name: str = "AEAT"
    source_url: str | None = None
    tax_type: TaxDeductionType
    eligibility_summary: str = Field(min_length=1)
    required_evidence: list[str] = Field(default_factory=list)
    validity_period_start: date | None = None
    validity_period_end: date | None = None
    max_base_or_percentage: str | None = None
    requires_verification: bool = True


class TaxDeductionSearchRequest(BaseModel):
    """Explicit input for ``search_tax_deduction_candidates``."""

    model_config = ConfigDict(extra="forbid")

    tax_residency_country: Literal["ES"] = "ES"
    installation_year: int = Field(ge=2020, le=2100)
    property_type: Literal["primary_residence", "secondary_residence", "rental", "other"]
    work_type: Literal[
        "self_consumption_pv",
        "battery_storage",
        "thermal_renewable",
        "energy_rehabilitation",
        "other",
    ]
    energy_improvement_evidence: bool = False
    user_type: Literal["individual", "company"] = "individual"


class TaxDeductionSearchResult(BaseModel):
    """Normalized output of ``search_tax_deduction_candidates``."""

    model_config = ConfigDict(extra="forbid")

    candidates: list[TaxDeductionCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


__all__ = [
    "Administration",
    "CompatibilityEvaluationRequest",
    "CompatibilityEvaluationResult",
    "CompatibilityLevel",
    "MunicipalTaxBenefitCandidate",
    "MunicipalTaxBenefitSearchRequest",
    "MunicipalTaxBenefitSearchResult",
    "SubsidyCandidate",
    "SubsidySearchRequest",
    "SubsidySearchResult",
    "SubsidyStatus",
    "TaxBenefitType",
    "TaxDeductionCandidate",
    "TaxDeductionSearchRequest",
    "TaxDeductionSearchResult",
    "TaxDeductionType",
]
