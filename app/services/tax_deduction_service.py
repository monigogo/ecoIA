"""TaxDeductionService — curated reader for AEAT IRPF deductions.

Reasoning-first contract:

- The service reads a curated AEAT-derived dataset and returns
  candidates whose property/work tags match the explicit request and
  whose validity period covers the requested installation year.
- It does not classify eligibility. Every candidate carries
  ``requires_verification=True`` and a structured warning that the
  AEAT site is the authoritative source.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from app.core.errors import ConfigurationError
from app.core.logging import get_logger
from app.schemas.subsidy import (
    TaxDeductionCandidate,
    TaxDeductionSearchRequest,
    TaxDeductionSearchResult,
    TaxDeductionType,
)

logger = get_logger(__name__)

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "aeat_tax_deductions.json"
)


class TaxDeductionService:
    """Curated reader for AEAT IRPF deductions."""

    def __init__(self, dataset_path: Path | None = None) -> None:
        self._dataset_path = dataset_path or DEFAULT_DATASET_PATH
        self._dataset: list[dict[str, object]] | None = None

    def _load(self) -> list[dict[str, object]]:
        if self._dataset is not None:
            return self._dataset
        try:
            raw = json.loads(self._dataset_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError(
                "AEAT tax deductions dataset not found",
                details={"path": str(self._dataset_path)},
            ) from exc
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                "AEAT tax deductions dataset is not valid JSON",
                details={"path": str(self._dataset_path), "error": str(exc)},
            ) from exc
        deductions = raw.get("deductions") or []
        if not isinstance(deductions, list):
            raise ConfigurationError(
                "AEAT tax deductions dataset 'deductions' must be a list",
                details={"path": str(self._dataset_path)},
            )
        self._dataset = deductions
        return deductions

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None

    @classmethod
    def _matches(
        cls, entry: dict[str, object], request: TaxDeductionSearchRequest
    ) -> bool:
        applies_to_property = entry.get("applies_to_property_types")
        if (
            isinstance(applies_to_property, list)
            and request.property_type not in applies_to_property
        ):
            return False
        applies_to_work = entry.get("applies_to_work_types")
        if (
            isinstance(applies_to_work, list)
            and request.work_type not in applies_to_work
        ):
            return False
        installation_year = request.installation_year
        start = cls._parse_date(entry.get("validity_period_start"))
        end = cls._parse_date(entry.get("validity_period_end"))
        if start is not None and installation_year < start.year:
            return False
        return not (end is not None and installation_year > end.year)

    @classmethod
    def _to_candidate(cls, entry: dict[str, object]) -> TaxDeductionCandidate:
        try:
            tax_type = TaxDeductionType(str(entry.get("tax_type")))
        except ValueError:
            tax_type = TaxDeductionType.other
        evidence_raw = entry.get("required_evidence") or []
        if not isinstance(evidence_raw, list):
            evidence: list[str] = []
        else:
            evidence = [str(item) for item in evidence_raw]
        return TaxDeductionCandidate(
            id=str(entry["id"]),
            title=str(entry["title"]),
            source_name=str(entry.get("source_name") or "AEAT"),
            source_url=str(entry["source_url"]) if entry.get("source_url") else None,
            tax_type=tax_type,
            eligibility_summary=str(entry["eligibility_summary"]),
            required_evidence=evidence,
            validity_period_start=cls._parse_date(entry.get("validity_period_start")),
            validity_period_end=cls._parse_date(entry.get("validity_period_end")),
            max_base_or_percentage=(
                str(entry["max_base_or_percentage"])
                if entry.get("max_base_or_percentage")
                else None
            ),
            requires_verification=True,
        )

    def search(self, request: TaxDeductionSearchRequest) -> TaxDeductionSearchResult:
        dataset = self._load()
        candidates = [
            self._to_candidate(entry)
            for entry in dataset
            if isinstance(entry, dict) and self._matches(entry, request)
        ]
        warnings: list[str] = [
            "Tax deduction candidates are orientative. AEAT is the authoritative "
            "source; the user must verify validity, percentages, and required "
            "evidence at https://sede.agenciatributaria.gob.es before applying.",
            "An IRPF deduction is not the same as a direct subsidy or a municipal "
            "tax benefit; do not aggregate values across categories.",
        ]
        if request.user_type == "company":
            warnings.append(
                "These IRPF deductions apply to individuals; a company should "
                "consult corporate-tax incentives separately."
            )
        return TaxDeductionSearchResult(candidates=candidates, warnings=warnings)
