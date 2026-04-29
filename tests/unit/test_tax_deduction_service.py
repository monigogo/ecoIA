from __future__ import annotations

from app.schemas.subsidy import TaxDeductionSearchRequest, TaxDeductionType
from app.services.tax_deduction_service import TaxDeductionService


def test_self_consumption_2026_candidate_present_for_2026_install() -> None:
    service = TaxDeductionService()
    result = service.search(
        TaxDeductionSearchRequest(
            installation_year=2026,
            property_type="primary_residence",
            work_type="self_consumption_pv",
        )
    )
    ids = {c.id for c in result.candidates}
    assert "irpf_self_consumption_2026" in ids
    assert all(c.requires_verification for c in result.candidates)
    assert any(c.tax_type == TaxDeductionType.irpf_self_consumption_2026 for c in result.candidates)


def test_self_consumption_2026_excluded_for_2025_install() -> None:
    service = TaxDeductionService()
    result = service.search(
        TaxDeductionSearchRequest(
            installation_year=2025,
            property_type="primary_residence",
            work_type="self_consumption_pv",
        )
    )
    ids = {c.id for c in result.candidates}
    assert "irpf_self_consumption_2026" not in ids


def test_warnings_state_separation_from_subsidies() -> None:
    service = TaxDeductionService()
    result = service.search(
        TaxDeductionSearchRequest(
            installation_year=2026,
            property_type="primary_residence",
            work_type="self_consumption_pv",
        )
    )
    assert any("not the same as a direct subsidy" in w for w in result.warnings)


def test_company_user_gets_extra_warning() -> None:
    service = TaxDeductionService()
    result = service.search(
        TaxDeductionSearchRequest(
            installation_year=2026,
            property_type="primary_residence",
            work_type="self_consumption_pv",
            user_type="company",
        )
    )
    assert any("company should" in w for w in result.warnings)


def test_filter_by_work_type_excludes_unrelated_deductions() -> None:
    service = TaxDeductionService()
    result = service.search(
        TaxDeductionSearchRequest(
            installation_year=2026,
            property_type="primary_residence",
            work_type="thermal_renewable",
        )
    )
    ids = {c.id for c in result.candidates}
    assert "irpf_self_consumption_2026" not in ids
    assert "irpf_demand_reduction" in ids
