from __future__ import annotations

from app.tools.subsidy_tools import (
    build_evaluate_subsidy_compatibility_tool,
    build_search_municipal_tax_benefits_tool,
    build_search_subsidies_tool,
    build_search_tax_deduction_candidates_tool,
)


def test_search_subsidies_tool_has_expected_name() -> None:
    tool = build_search_subsidies_tool()
    assert tool.name == "search_subsidies"
    assert tool.description


def test_evaluate_subsidy_compatibility_tool_has_expected_name() -> None:
    tool = build_evaluate_subsidy_compatibility_tool()
    assert tool.name == "evaluate_subsidy_compatibility"


def test_search_municipal_tax_benefits_tool_has_expected_name() -> None:
    tool = build_search_municipal_tax_benefits_tool()
    assert tool.name == "search_municipal_tax_benefits"


def test_search_tax_deduction_candidates_tool_has_expected_name() -> None:
    tool = build_search_tax_deduction_candidates_tool()
    assert tool.name == "search_tax_deduction_candidates"


def test_search_municipal_tax_benefits_tool_returns_serializable_payload() -> None:
    tool = build_search_municipal_tax_benefits_tool()
    payload = tool.invoke(
        {
            "municipality": "Madrid",
            "province": "Madrid",
            "project_type": "residential",
            "installation_type": "new",
        }
    )
    assert "candidates" in payload
    assert all(c["requires_verification"] for c in payload["candidates"])


def test_search_tax_deduction_candidates_tool_returns_serializable_payload() -> None:
    tool = build_search_tax_deduction_candidates_tool()
    payload = tool.invoke(
        {
            "installation_year": 2026,
            "property_type": "primary_residence",
            "work_type": "self_consumption_pv",
        }
    )
    assert "candidates" in payload
    assert all(c["requires_verification"] for c in payload["candidates"])
    assert any("not the same as a direct subsidy" in w for w in payload["warnings"])
