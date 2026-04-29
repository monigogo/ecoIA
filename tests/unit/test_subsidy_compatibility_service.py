from __future__ import annotations

from typing import Any

import pytest

from app.core.errors import ConfigurationError
from app.schemas.subsidy import (
    Administration,
    CompatibilityEvaluationRequest,
    CompatibilityEvaluationResult,
    CompatibilityLevel,
    SubsidyCandidate,
    SubsidyStatus,
)
from app.services.subsidy_compatibility_service import SubsidyCompatibilityService
from tests.fixtures.fake_chat_model import FakeChatModel


def _candidate() -> SubsidyCandidate:
    return SubsidyCandidate(
        id="BDNS-1",
        title="Ayudas autoconsumo solar Andalucía",
        administration=Administration.autonomous_community,
        region="Andalucía",
        beneficiary_summary="Personas físicas",
        purpose_summary="Autoconsumo fotovoltaico residencial",
        status=SubsidyStatus.open,
    )


def _factory(_messages: Any) -> CompatibilityEvaluationResult:
    return CompatibilityEvaluationResult(
        compatibility_level=CompatibilityLevel.medium,
        reasoning="Plausible match: residential PV in the right region; verify deadline.",
        matched_requirements=["region", "technology"],
        missing_requirements=["deadline_confirmation"],
        documents_to_verify=["DNI", "Factura", "CIE"],
    )


def test_evaluate_returns_structured_result() -> None:
    fake = FakeChatModel(_factory)
    service = SubsidyCompatibilityService(model=fake)
    response = service.evaluate(
        CompatibilityEvaluationRequest(
            project_context="Vivienda unifamiliar 5kWp Andalucía",
            subsidy_candidate=_candidate(),
            available_evidence="DNI",
        )
    )
    assert response.compatibility_level == CompatibilityLevel.medium
    assert "deadline_confirmation" in response.missing_requirements
    assert response.legal_warning  # default is non-empty
    assert fake.last_schema is CompatibilityEvaluationResult


def test_evaluate_requires_model_when_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("NVIDIA_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    from app.core import config as config_module

    config_module.get_settings.cache_clear()
    service = SubsidyCompatibilityService()
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        service.evaluate(
            CompatibilityEvaluationRequest(
                project_context="x",
                subsidy_candidate=_candidate(),
            )
        )
    config_module.get_settings.cache_clear()
