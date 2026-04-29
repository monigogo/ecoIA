from __future__ import annotations

from typing import Any

from app.schemas.assumptions import (
    AssumptionCandidate,
    AssumptionConfidence,
    AssumptionResponse,
    AssumptionSourceType,
)
from app.services.assumption_service import AssumptionService
from app.tools.assumption_tools import build_assumption_tool
from tests.fixtures.fake_chat_model import FakeChatModel


def _factory(_messages: Any) -> AssumptionResponse:
    return AssumptionResponse(
        candidates=[
            AssumptionCandidate(
                id="c1",
                domain="system_losses",
                label="central",
                value=14,
                unit="%",
                source_type=AssumptionSourceType.technical_reference,
                source_name="IEA PVPS Task 13",
                source_url=None,
                confidence=AssumptionConfidence.medium,
                reasoning="Typical aggregate loss for residential rooftop PV.",
                limitations="Varies with cabling, inverter and soiling.",
                requires_user_disclosure=True,
            ),
            AssumptionCandidate(
                id="c2",
                domain="system_losses",
                label="conservative",
                value=20,
                unit="%",
                source_type=AssumptionSourceType.technical_reference,
                source_name="IEA PVPS Task 13",
                source_url=None,
                confidence=AssumptionConfidence.low,
                reasoning="Older systems or shaded sites.",
                limitations="May overestimate losses for new installs.",
                requires_user_disclosure=True,
            ),
        ]
    )


def _build() -> Any:
    service = AssumptionService(model=FakeChatModel(_factory))
    return build_assumption_tool(service=service)


def test_tool_has_expected_name_and_schema() -> None:
    tool = _build()
    assert tool.name == "get_assumption_candidates"
    assert tool.description
    schema = tool.args_schema.model_json_schema()
    assert "domain" in schema["properties"]
    assert "context" in schema["properties"]


def test_tool_invokes_and_returns_serializable_dict() -> None:
    tool = _build()
    result = tool.invoke(
        {"domain": "system_losses", "context": "rooftop residential, no inverter info"}
    )
    assert isinstance(result, dict)
    assert "candidates" in result
    assert len(result["candidates"]) >= 2
    # Every candidate JSON-serializable, no datetime/enum issues
    import json

    json.dumps(result)


def test_tool_does_not_select_a_winner() -> None:
    tool = _build()
    result = tool.invoke({"domain": "system_losses", "context": "ctx"})
    assert "selected_candidate" not in result
    assert "decision" not in result
    assert "winner" not in result


def test_tool_payload_carries_disclosure_flags_and_sources() -> None:
    tool = _build()
    result = tool.invoke({"domain": "system_losses", "context": "ctx"})
    for cand in result["candidates"]:
        assert cand["source_name"]
        assert cand["reasoning"]
        assert cand["limitations"]
        if cand["source_type"] != AssumptionSourceType.user_provided.value:
            assert cand["requires_user_disclosure"] is True
