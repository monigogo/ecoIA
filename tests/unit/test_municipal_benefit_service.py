from __future__ import annotations

from app.schemas.subsidy import (
    MunicipalTaxBenefitSearchRequest,
    SubsidyStatus,
    TaxBenefitType,
)
from app.services.municipal_benefit_service import MunicipalBenefitService


def test_search_returns_curated_madrid_ibi_candidate() -> None:
    service = MunicipalBenefitService()
    result = service.search(
        MunicipalTaxBenefitSearchRequest(
            municipality="Madrid",
            province="Madrid",
            project_type="residential",
            installation_type="new",
        )
    )
    assert any(c.benefit_type == TaxBenefitType.ibi for c in result.candidates)
    assert all(c.requires_verification for c in result.candidates)
    assert any("verified" in w.lower() for w in result.warnings)


def test_search_returns_no_candidates_for_unknown_municipality() -> None:
    service = MunicipalBenefitService()
    result = service.search(
        MunicipalTaxBenefitSearchRequest(municipality="NoSuchCity")
    )
    assert result.candidates == []
    assert any("No curated municipal benefits" in w for w in result.warnings)


def test_search_filters_by_project_type_match() -> None:
    service = MunicipalBenefitService()
    result = service.search(
        MunicipalTaxBenefitSearchRequest(
            municipality="Madrid",
            province="Madrid",
            project_type="public_administration",
            installation_type="new",
        )
    )
    assert result.candidates == []


def test_search_status_is_unknown_until_verified() -> None:
    service = MunicipalBenefitService()
    result = service.search(
        MunicipalTaxBenefitSearchRequest(
            municipality="Madrid", province="Madrid", project_type="residential"
        )
    )
    assert all(c.validity_status == SubsidyStatus.unknown for c in result.candidates)
