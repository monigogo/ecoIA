from __future__ import annotations

from app.agents.subagents import build_subagents

REQUIRED_KEYS = {"name", "description", "system_prompt", "tools"}
EXPECTED_NAMES = {
    "degradation-analyst",
    "battery-advisor",
    "subsidy-finder",
    "energy-economics-advisor",
    "rdtools-analyzer",
    "report-synthesizer",
}


def test_all_subagents_present() -> None:
    subs = build_subagents()
    names = {s["name"] for s in subs}
    assert names == EXPECTED_NAMES


def test_subagent_required_fields() -> None:
    for sub in build_subagents():
        missing = REQUIRED_KEYS - sub.keys()
        assert not missing, f"{sub['name']} missing keys: {missing}"
        assert sub["description"].strip()
        assert sub["system_prompt"].strip()
        assert isinstance(sub["tools"], list)


def test_descriptions_are_action_oriented_and_unique() -> None:
    descriptions = [s["description"] for s in build_subagents()]
    assert len(descriptions) == len(set(descriptions))
    for desc in descriptions:
        assert len(desc) >= 40, f"description too short: {desc!r}"


def test_assumption_tool_is_wired_into_reasoning_subagents() -> None:
    """Every subagent that produces numeric outputs must have access to
    the assumption tool. Report-synthesizer aggregates only."""

    needs_assumptions = {
        "degradation-analyst",
        "battery-advisor",
        "subsidy-finder",
        "energy-economics-advisor",
        "rdtools-analyzer",
    }
    for sub in build_subagents():
        tool_names = {t.name for t in sub["tools"]}
        if sub["name"] in needs_assumptions:
            assert "get_assumption_candidates" in tool_names, sub["name"]
        else:
            assert "get_assumption_candidates" not in tool_names


def test_geocoding_tool_is_wired_only_into_subsidy_finder() -> None:
    for sub in build_subagents():
        tool_names = {t.name for t in sub["tools"]}
        if sub["name"] == "subsidy-finder":
            assert "geocode_location" in tool_names, sub["name"]
        else:
            assert "geocode_location" not in tool_names, sub["name"]

def test_degradation_tools_are_wired_only_into_degradation_analyst() -> None:
    expected = {
        "calculate_degradation_projection",
        "calculate_lifetime_threshold",
        "compare_degradation_scenarios",
    }
    for sub in build_subagents():
        tool_names = {t.name for t in sub["tools"]}
        if sub["name"] == "degradation-analyst":
            assert expected.issubset(tool_names)
        else:
            assert expected.isdisjoint(tool_names)


def test_battery_tools_are_wired_only_into_battery_advisor() -> None:
    expected = {
        "estimate_battery_size",
        "compare_battery_scenarios",
    }
    for sub in build_subagents():
        tool_names = {t.name for t in sub["tools"]}
        if sub["name"] == "battery-advisor":
            assert expected.issubset(tool_names)
        else:
            assert expected.isdisjoint(tool_names)


def test_rdtools_validation_tool_is_wired_only_into_rdtools_analyzer() -> None:
    for sub in build_subagents():
        tool_names = {t.name for t in sub["tools"]}
        if sub["name"] == "rdtools-analyzer":
            assert "validate_rdtools_csv" in tool_names
            assert "analyze_existing_installation_with_rdtools" in tool_names
        else:
            assert "validate_rdtools_csv" not in tool_names
            assert "analyze_existing_installation_with_rdtools" not in tool_names


def test_economic_tools_are_wired_only_into_energy_economics_advisor() -> None:
    expected = {
        "estimate_self_consumption_savings",
        "estimate_export_compensation",
        "estimate_export_sale_revenue",
        "estimate_energy_bill_impact",
        "compare_battery_vs_export",
    }
    for sub in build_subagents():
        tool_names = {t.name for t in sub["tools"]}
        if sub["name"] == "energy-economics-advisor":
            assert expected.issubset(tool_names)
        else:
            assert expected.isdisjoint(tool_names)


def test_energy_economics_prompt_states_economic_separation_rule() -> None:
    for sub in build_subagents():
        if sub["name"] != "energy-economics-advisor":
            continue
        prompt = sub["system_prompt"].lower()
        assert "savings" in prompt
        assert "compensation" in prompt
        assert "sale" in prompt
        assert "estimate_export_sale_revenue" in prompt
        assert "estimate_export_compensation" in prompt


def test_price_tools_are_wired_only_into_energy_economics_advisor() -> None:
    expected = {
        "get_pvpc_surplus_compensation_price",
        "get_pvpc_import_reference_price",
        "get_market_sale_reference_price",
        "normalize_energy_price_series",
    }
    for sub in build_subagents():
        tool_names = {t.name for t in sub["tools"]}
        if sub["name"] == "energy-economics-advisor":
            assert expected.issubset(tool_names)
        else:
            assert expected.isdisjoint(tool_names)


def test_energy_economics_prompt_distinguishes_compensation_and_sale() -> None:
    for sub in build_subagents():
        if sub["name"] != "energy-economics-advisor":
            continue
        prompt = sub["system_prompt"].lower()
        assert "pvpc" in prompt
        assert "omie" in prompt
        assert "wholesale" in prompt or "mayorista" in prompt
        assert "never" in prompt or "do not" in prompt


def test_energy_economics_prompt_forbids_inventing_prices() -> None:
    for sub in build_subagents():
        if sub["name"] != "energy-economics-advisor":
            continue
        prompt = sub["system_prompt"].lower()
        assert "invent" in prompt
        assert "fabricat" in prompt or "do not fabricate" in prompt or "fabricate" in prompt


def test_all_reasoning_subagents_include_safe_recovery_guidance() -> None:
    for sub in build_subagents():
        if sub["name"] == "report-synthesizer":
            continue
        prompt = sub["system_prompt"].lower()
        assert (
            "recovery" in prompt
            or "do not stop immediately" in prompt
            or "partial answer" in prompt
            or "partial result" in prompt
            or "smallest missing input" in prompt
            or "corrective action" in prompt
        )
        assert (
            "partial" in prompt
            or "missing" in prompt
            or "corrective action" in prompt
            or "incomplete" in prompt
        )
        assert "invent" in prompt or "fabricat" in prompt


def test_subsidy_tools_are_wired_only_into_subsidy_finder() -> None:
    expected = {
        "search_subsidies",
        "evaluate_subsidy_compatibility",
        "search_municipal_tax_benefits",
        "search_tax_deduction_candidates",
    }
    for sub in build_subagents():
        tool_names = {t.name for t in sub["tools"]}
        if sub["name"] == "subsidy-finder":
            assert expected.issubset(tool_names)
        else:
            assert expected.isdisjoint(tool_names)


def test_subsidy_finder_prompt_distinguishes_subsidy_municipal_and_irpf() -> None:
    for sub in build_subagents():
        if sub["name"] != "subsidy-finder":
            continue
        prompt = sub["system_prompt"].lower()
        assert "bdns" in prompt
        assert "ibi" in prompt or "icio" in prompt
        assert "irpf" in prompt or "aeat" in prompt
        assert "never aggregate" in prompt or "do not aggregate" in prompt
        assert "requires_verification" in prompt or "verify" in prompt


def test_subsidy_finder_prompt_forbids_keyword_matching_and_scoring() -> None:
    for sub in build_subagents():
        if sub["name"] != "subsidy-finder":
            continue
        prompt = sub["system_prompt"].lower()
        assert "keyword matching" in prompt
        assert "hardcoded scoring" in prompt or "+30" in prompt


def test_no_hardcoded_numeric_defaults_in_prompts() -> None:
    """Reasoning-first invariant: subagent prompts must not encode numeric
    defaults (e.g. '0.5%', '14% losses'). Picking values is the LLM's job
    via AssumptionProvider."""

    forbidden_substrings = ["0.5%", "0.5 %", "14%", "14 %", "default to "]
    for sub in build_subagents():
        prompt_lower = sub["system_prompt"].lower()
        for needle in forbidden_substrings:
            assert needle.lower() not in prompt_lower, (
                f"{sub['name']} prompt contains forbidden default '{needle}'"
            )


def test_optional_middleware_and_response_formats_are_wired_per_subagent() -> None:
    sentinel = object()
    subs = build_subagents(
        middleware_factory=lambda: [sentinel],
        subagent_response_format=dict,
        final_response_format=list,
    )

    for sub in subs[:-1]:
        assert sub["middleware"] == [sentinel]
        assert sub["response_format"] is dict
    assert subs[0]["middleware"] is not subs[1]["middleware"]
    assert subs[-1]["response_format"] is list
