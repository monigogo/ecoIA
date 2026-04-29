"""Conceptual regression tests: subsidy / municipal benefit / IRPF deduction.

These tests enforce the project invariants for the subsidy block:

- the three categories produce structurally distinct payloads;
- no scoring file lives next to the curated data;
- candidates always carry ``requires_verification=True``;
- the subsidy-finder prompt forbids aggregating values.
"""

from __future__ import annotations

from pathlib import Path

from app.agents.subagents import build_subagents
from app.schemas.subsidy import (
    MunicipalTaxBenefitSearchRequest,
    TaxDeductionSearchRequest,
)
from app.services.municipal_benefit_service import MunicipalBenefitService
from app.services.tax_deduction_service import TaxDeductionService


def test_municipal_benefit_is_not_a_subsidy_or_a_deduction() -> None:
    municipal = MunicipalBenefitService().search(
        MunicipalTaxBenefitSearchRequest(municipality="Madrid", province="Madrid")
    )
    deduction = TaxDeductionService().search(
        TaxDeductionSearchRequest(
            installation_year=2026,
            property_type="primary_residence",
            work_type="self_consumption_pv",
        )
    )

    assert municipal.candidates, "expected at least one curated municipal candidate"
    assert deduction.candidates, "expected at least one curated AEAT candidate"

    municipal_fields = set(municipal.candidates[0].model_dump().keys())
    deduction_fields = set(deduction.candidates[0].model_dump().keys())

    assert "benefit_type" in municipal_fields
    assert "tax_type" in deduction_fields
    assert "benefit_type" not in deduction_fields
    assert "tax_type" not in municipal_fields


def test_no_subsidy_keywords_or_scoring_files_in_data_dir() -> None:
    data_dir = Path(__file__).resolve().parents[2] / "app" / "data"
    forbidden = {
        "subsidy_keywords.yaml",
        "subsidy_keywords.json",
        "subsidy_scores.yaml",
        "subsidy_scores.json",
    }
    present = {p.name for p in data_dir.iterdir() if p.is_file()}
    assert forbidden.isdisjoint(present), present & forbidden


def test_curated_candidates_always_require_verification() -> None:
    municipal = MunicipalBenefitService().search(
        MunicipalTaxBenefitSearchRequest(municipality="Madrid", province="Madrid")
    )
    deduction = TaxDeductionService().search(
        TaxDeductionSearchRequest(
            installation_year=2026,
            property_type="primary_residence",
            work_type="self_consumption_pv",
        )
    )
    assert all(c.requires_verification for c in municipal.candidates)
    assert all(c.requires_verification for c in deduction.candidates)


def test_subsidy_finder_prompt_forbids_aggregation_across_categories() -> None:
    for sub in build_subagents():
        if sub["name"] != "subsidy-finder":
            continue
        prompt = sub["system_prompt"].lower()
        assert "never aggregate" in prompt or "do not aggregate" in prompt
