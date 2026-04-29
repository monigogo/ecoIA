"""MunicipalBenefitService — curated reader for IBI/ICIO/IAE benefits.

Reasoning-first contract:

- The service reads a curated dataset and returns candidates whose
  municipality and applicability tags match the explicit request.
- The match is structural (municipality string + tag set), not a
  similarity score and not keyword matching against free-form user
  text.
- Every candidate is tagged ``requires_verification=True`` and carries
  the source URL of the official ordinance reference.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.errors import ConfigurationError
from app.core.logging import get_logger
from app.schemas.subsidy import (
    MunicipalTaxBenefitCandidate,
    MunicipalTaxBenefitSearchRequest,
    MunicipalTaxBenefitSearchResult,
    SubsidyStatus,
    TaxBenefitType,
)

logger = get_logger(__name__)

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "municipal_benefits_sample.json"
)


class MunicipalBenefitService:
    """Curated reader for municipal IBI/ICIO/IAE benefits."""

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
                "municipal benefits dataset not found",
                details={"path": str(self._dataset_path)},
            ) from exc
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                "municipal benefits dataset is not valid JSON",
                details={"path": str(self._dataset_path), "error": str(exc)},
            ) from exc
        benefits = raw.get("benefits") or []
        if not isinstance(benefits, list):
            raise ConfigurationError(
                "municipal benefits dataset 'benefits' must be a list",
                details={"path": str(self._dataset_path)},
            )
        self._dataset = benefits
        return benefits

    @staticmethod
    def _matches(
        entry: dict[str, object], request: MunicipalTaxBenefitSearchRequest
    ) -> bool:
        municipality_value = entry.get("municipality")
        if not isinstance(municipality_value, str):
            return False
        if municipality_value.strip().lower() != request.municipality.strip().lower():
            return False
        if request.province is not None:
            province_value = entry.get("province")
            if isinstance(province_value, str) and province_value.strip().lower() != (
                request.province.strip().lower()
            ):
                return False
        applies_to_projects = entry.get("applies_to_project_types")
        if (
            isinstance(applies_to_projects, list)
            and request.project_type not in applies_to_projects
        ):
            return False
        applies_to_installations = entry.get("applies_to_installation_types")
        return not (
            isinstance(applies_to_installations, list)
            and request.installation_type not in applies_to_installations
        )

    @staticmethod
    def _to_candidate(entry: dict[str, object]) -> MunicipalTaxBenefitCandidate:
        benefit_type_raw = entry.get("benefit_type")
        try:
            benefit_type = TaxBenefitType(str(benefit_type_raw))
        except ValueError:
            benefit_type = TaxBenefitType.other
        validity_raw = entry.get("validity_status")
        try:
            validity = SubsidyStatus(str(validity_raw))
        except ValueError:
            validity = SubsidyStatus.unknown
        return MunicipalTaxBenefitCandidate(
            municipality=str(entry["municipality"]),
            province=str(entry["province"]) if entry.get("province") else None,
            benefit_type=benefit_type,
            title=str(entry["title"]),
            description=str(entry["description"]),
            source_name=str(entry.get("source_name") or "municipal_ordinance"),
            source_url=(
                str(entry["source_url"]) if entry.get("source_url") else None
            ),
            validity_status=validity,
            requires_verification=True,
        )

    def search(
        self, request: MunicipalTaxBenefitSearchRequest
    ) -> MunicipalTaxBenefitSearchResult:
        dataset = self._load()
        candidates = [
            self._to_candidate(entry)
            for entry in dataset
            if isinstance(entry, dict) and self._matches(entry, request)
        ]
        warnings: list[str] = [
            "Municipal tax benefits are sourced from a curated dataset and must be "
            "verified against the official municipal ordinance before relying on them.",
        ]
        if not candidates:
            warnings.append(
                f"No curated municipal benefits were found for {request.municipality}; "
                "this does not imply that none exist — verify with the municipality directly."
            )
        return MunicipalTaxBenefitSearchResult(
            candidates=candidates, warnings=warnings
        )
