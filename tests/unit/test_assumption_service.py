from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.core.errors import ConfigurationError, ExternalServiceError
from app.schemas.assumptions import (
    AssumptionCandidate,
    AssumptionConfidence,
    AssumptionRequest,
    AssumptionResponse,
    AssumptionSourceType,
)
from app.services.assumption_service import AssumptionService
from tests.fixtures.fake_chat_model import FakeChatModel


def _candidate(**overrides: Any) -> AssumptionCandidate:
    base = dict(
        id="cand-1",
        domain="solar_degradation",
        label="residential central",
        value=0.5,
        unit="%/year",
        source_type=AssumptionSourceType.technical_reference,
        source_name="NREL PV degradation studies",
        source_url="https://www.nrel.gov/pv/module-reliability-research.html",
        confidence=AssumptionConfidence.medium,
        reasoning="Typical residential c-Si module degradation in temperate climates.",
        limitations="Highly dependent on module quality and operating temperature.",
        requires_user_disclosure=True,
    )
    base.update(overrides)
    return AssumptionCandidate(**base)


def _response_factory_two_candidates(_messages: Any) -> AssumptionResponse:
    return AssumptionResponse(
        candidates=[
            _candidate(id="c1", label="conservative", value=0.8),
            _candidate(id="c2", label="optimistic", value=0.3, confidence=AssumptionConfidence.low),
        ],
        notes="Both options orientative; user must disclose.",
    )


def _workspace_temp_dir() -> Path:
    root = Path(".test_artifacts")
    root.mkdir(exist_ok=True)
    path = root / f"assumption-service-{uuid4().hex}"
    path.mkdir()
    return path


def test_load_registry_reads_default_file() -> None:
    service = AssumptionService(model=FakeChatModel(_response_factory_two_candidates))
    sources = service.load_registry()
    assert len(sources) > 0
    assert all(s.source_id and s.title and s.organization for s in sources)


def test_load_registry_raises_configuration_error_on_missing_file() -> None:
    temp_dir = _workspace_temp_dir()
    try:
        missing = temp_dir / "nope.json"
        service = AssumptionService(
            model=FakeChatModel(_response_factory_two_candidates),
            registry_path=missing,
        )
        with pytest.raises(ConfigurationError):
            service.load_registry()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_load_registry_raises_configuration_error_on_invalid_json() -> None:
    temp_dir = _workspace_temp_dir()
    try:
        bad = temp_dir / "bad.json"
        bad.write_text("{ not valid json", encoding="utf-8")
        service = AssumptionService(
            model=FakeChatModel(_response_factory_two_candidates),
            registry_path=bad,
        )
        with pytest.raises(ConfigurationError):
            service.load_registry()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_generate_candidates_returns_multiple_options() -> None:
    fake = FakeChatModel(_response_factory_two_candidates)
    service = AssumptionService(model=fake)
    response = service.generate_candidates(
        AssumptionRequest(
            domain="solar_degradation",
            context="Residential install in Sevilla, no panel datasheet.",
        )
    )
    assert len(response.candidates) >= 2
    assert response.candidates[0].label != response.candidates[1].label


def test_generate_candidates_does_not_select_winner() -> None:
    fake = FakeChatModel(_response_factory_two_candidates)
    service = AssumptionService(model=fake)
    response = service.generate_candidates(
        AssumptionRequest(domain="solar_degradation", context="ctx")
    )
    payload = response.model_dump()
    assert "selected_candidate" not in payload
    assert "decision" not in payload


def test_generate_candidates_enforces_disclosure_for_non_user_sources() -> None:
    fake = FakeChatModel(_response_factory_two_candidates)
    service = AssumptionService(model=fake)
    response = service.generate_candidates(
        AssumptionRequest(domain="solar_degradation", context="ctx")
    )
    for cand in response.candidates:
        if cand.source_type != AssumptionSourceType.user_provided:
            assert cand.requires_user_disclosure is True


def test_generate_candidates_each_candidate_has_reasoning_and_limitations() -> None:
    fake = FakeChatModel(_response_factory_two_candidates)
    service = AssumptionService(model=fake)
    response = service.generate_candidates(
        AssumptionRequest(domain="solar_degradation", context="ctx")
    )
    for cand in response.candidates:
        assert cand.reasoning
        assert cand.limitations
        assert cand.source_name


def test_generate_candidates_normalizes_domain_echo() -> None:
    """If the LLM returns a candidate with a different domain string, the
    service rewrites it to the requested domain so downstream code stays
    consistent. This is plumbing, not branching on domain meaning.
    """

    def factory(_messages: Any) -> AssumptionResponse:
        return AssumptionResponse(
            candidates=[_candidate(id="c1", domain="something_else")],
        )

    fake = FakeChatModel(factory)
    service = AssumptionService(model=fake)
    response = service.generate_candidates(
        AssumptionRequest(domain="solar_degradation", context="ctx")
    )
    assert response.candidates[0].domain == "solar_degradation"


def test_generate_candidates_wraps_model_errors() -> None:
    def boom(_messages: Any) -> AssumptionResponse:
        raise RuntimeError("model unavailable")

    fake = FakeChatModel(boom)
    service = AssumptionService(model=fake)
    with pytest.raises(ExternalServiceError):
        service.generate_candidates(
            AssumptionRequest(domain="solar_degradation", context="ctx")
        )


def test_prompt_includes_registry_sources() -> None:
    fake = FakeChatModel(_response_factory_two_candidates)
    service = AssumptionService(model=fake)
    service.generate_candidates(
        AssumptionRequest(domain="solar_degradation", context="ctx")
    )
    user_message = fake.last_input[1]["content"]  # type: ignore[index]
    sources = service.load_registry()
    for src in sources:
        assert src.source_id in user_message


def test_registry_file_is_well_formed_json() -> None:
    raw = json.loads(
        Path("app/data/reference_sources.json").read_text(encoding="utf-8")
    )
    assert "sources" in raw
    assert isinstance(raw["sources"], list)
    assert len(raw["sources"]) >= 2
