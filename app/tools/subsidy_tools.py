"""LangChain tools for subsidies, municipal tax benefits, and AEAT deductions.

Reasoning rules (see ``AGENTS.md``):

- Tools fetch and normalize. They do not classify eligibility.
- Compatibility is reasoned by the LLM via structured output.
- Every result carries source, status, and ``requires_verification``.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool

from app.schemas.subsidy import (
    CompatibilityEvaluationRequest,
    MunicipalTaxBenefitSearchRequest,
    SubsidyCandidate,
    SubsidySearchRequest,
    TaxDeductionSearchRequest,
)
from app.services.bdns_service import BDNSService
from app.services.municipal_benefit_service import MunicipalBenefitService
from app.services.subsidy_compatibility_service import SubsidyCompatibilityService
from app.services.tax_deduction_service import TaxDeductionService

if TYPE_CHECKING:  # pragma: no cover
    from langchain_core.language_models import BaseChatModel


@lru_cache(maxsize=1)
def _default_bdns_service() -> BDNSService:
    return BDNSService()


@lru_cache(maxsize=1)
def _default_municipal_service() -> MunicipalBenefitService:
    return MunicipalBenefitService()


@lru_cache(maxsize=1)
def _default_tax_deduction_service() -> TaxDeductionService:
    return TaxDeductionService()


# ---------------------------------------------------------------------------
# 1) search_subsidies (BDNS / SNPSAP)
# ---------------------------------------------------------------------------


def build_search_subsidies_tool(
    service: BDNSService | None = None,
):
    """Return a LangChain tool that queries BDNS/SNPSAP for subsidies."""

    bound_service = service or _default_bdns_service()

    @tool("search_subsidies", args_schema=SubsidySearchRequest)
    async def search_subsidies(
        project_context: str,
        location_context: str,
        reasoned_query: str,
        autonomous_community: str | None = None,
        municipality: str | None = None,
        province: str | None = None,
        beneficiary_type: str = "residential",
        technology: str = "solar_pv",
        installation_type: str = "new",
        has_battery: bool = False,
        date_range_start: date | None = None,
        date_range_end: date | None = None,
    ) -> dict[str, Any]:
        """Search BDNS/SNPSAP for candidate subsidies.

        Returns normalized candidates with source URL, administration,
        region, status, and ``requires_verification=True``. The tool does
        not classify eligibility — it returns options. The agent must
        evaluate compatibility separately and never claim a subsidy is
        granted.
        """

        request = SubsidySearchRequest(
            project_context=project_context,
            location_context=location_context,
            reasoned_query=reasoned_query,
            autonomous_community=autonomous_community,
            municipality=municipality,
            province=province,
            beneficiary_type=beneficiary_type,  # type: ignore[arg-type]
            technology=technology,  # type: ignore[arg-type]
            installation_type=installation_type,  # type: ignore[arg-type]
            has_battery=has_battery,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
        )

        result = await bound_service.search(request)

        return result.model_dump(mode="json")

    return search_subsidies


# ---------------------------------------------------------------------------
# 2) evaluate_subsidy_compatibility (LLM structured output)
# ---------------------------------------------------------------------------


def build_evaluate_subsidy_compatibility_tool(
    service: SubsidyCompatibilityService | None = None,
):
    """Return a LangChain tool that reasons compatibility for one candidate."""

    bound_service = service or SubsidyCompatibilityService()

    @tool(
        "evaluate_subsidy_compatibility",
        args_schema=CompatibilityEvaluationRequest,
    )
    def evaluate_subsidy_compatibility(
        project_context: str,
        subsidy_candidate: SubsidyCandidate,
        available_evidence: str = "",
    ) -> dict[str, Any]:
        """Reason compatibility between a project and a candidate subsidy.

        Returns a structured evaluation with compatibility level,
        matched and missing requirements, and documents the user must
        verify. Never returns a guarantee of grant.
        """

        request = CompatibilityEvaluationRequest(
            project_context=project_context,
            subsidy_candidate=subsidy_candidate,
            available_evidence=available_evidence,
        )

        response = bound_service.evaluate(request)

        return response.model_dump(mode="json")

    return evaluate_subsidy_compatibility


def build_evaluate_subsidy_compatibility_tool_with_model(model: BaseChatModel):
    """Convenience builder: wrap a model into a service and a tool."""

    return build_evaluate_subsidy_compatibility_tool(
        SubsidyCompatibilityService(model=model)
    )


# ---------------------------------------------------------------------------
# 3) search_municipal_tax_benefits
# ---------------------------------------------------------------------------


def build_search_municipal_tax_benefits_tool(
    service: MunicipalBenefitService | None = None,
):
    """Return a LangChain tool that queries curated municipal IBI/ICIO/IAE benefits."""

    bound_service = service or _default_municipal_service()

    @tool(
        "search_municipal_tax_benefits",
        args_schema=MunicipalTaxBenefitSearchRequest,
    )
    def search_municipal_tax_benefits(
        municipality: str,
        province: str | None = None,
        project_type: str = "residential",
        installation_type: str = "new",
    ) -> dict[str, Any]:
        """Look up curated municipal IBI/ICIO/IAE benefits for a municipality.

        The dataset is a curated reference, not an authoritative source
        — every candidate must be verified against the official
        municipal ordinance. The tool returns
        ``requires_verification=True`` on every candidate.
        """

        request = MunicipalTaxBenefitSearchRequest(
            municipality=municipality,
            province=province,
            project_type=project_type,  # type: ignore[arg-type]
            installation_type=installation_type,  # type: ignore[arg-type]
        )

        result = bound_service.search(request)

        return result.model_dump(mode="json")

    return search_municipal_tax_benefits


# ---------------------------------------------------------------------------
# 4) search_tax_deduction_candidates (AEAT)
# ---------------------------------------------------------------------------


def build_search_tax_deduction_candidates_tool(
    service: TaxDeductionService | None = None,
):
    """Return a LangChain tool that queries curated AEAT IRPF deductions."""

    bound_service = service or _default_tax_deduction_service()

    @tool(
        "search_tax_deduction_candidates",
        args_schema=TaxDeductionSearchRequest,
    )
    def search_tax_deduction_candidates(
        installation_year: int,
        property_type: str,
        work_type: str,
        tax_residency_country: str = "ES",
        energy_improvement_evidence: bool = False,
        user_type: str = "individual",
    ) -> dict[str, Any]:
        """Look up curated AEAT IRPF deduction candidates.

        Distinct from a direct subsidy and from a municipal tax
        benefit. The result is orientative; the user must verify
        validity, percentages, and required evidence on the official
        AEAT site.
        """

        request = TaxDeductionSearchRequest(
            tax_residency_country=tax_residency_country,  # type: ignore[arg-type]
            installation_year=installation_year,
            property_type=property_type,  # type: ignore[arg-type]
            work_type=work_type,  # type: ignore[arg-type]
            energy_improvement_evidence=energy_improvement_evidence,
            user_type=user_type,  # type: ignore[arg-type]
        )

        result = bound_service.search(request)

        return result.model_dump(mode="json")

    return search_tax_deduction_candidates


# Default exports for agent construction.
search_subsidies = build_search_subsidies_tool()
evaluate_subsidy_compatibility = build_evaluate_subsidy_compatibility_tool()
search_municipal_tax_benefits = build_search_municipal_tax_benefits_tool()
search_tax_deduction_candidates = build_search_tax_deduction_candidates_tool()


__all__ = [
    "build_evaluate_subsidy_compatibility_tool",
    "build_evaluate_subsidy_compatibility_tool_with_model",
    "build_search_municipal_tax_benefits_tool",
    "build_search_subsidies_tool",
    "build_search_tax_deduction_candidates_tool",
    "evaluate_subsidy_compatibility",
    "search_municipal_tax_benefits",
    "search_subsidies",
    "search_tax_deduction_candidates",
]
