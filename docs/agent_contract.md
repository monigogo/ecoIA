# Agent Contract

## Core rule

ecoIA reasons over explicit data, external APIs, uploaded documents, and declared assumptions. It does not silently apply hidden defaults.

## Required behavior

- use structured outputs for intent and entities
- delegate domain math to deterministic tools
- cite data sources
- disclose assumptions with source and confidence
- distinguish orientative results from authoritative facts

## Critical messages

- critical ES/EN user-facing disclaimers are centralized in `app/core/messages.py`
- this registry is intentionally small and is not a full i18n system
- use runtime locale to choose between Spanish and English variants
- prefer structured outputs and response builders over duplicating disclaimers across prompts and tests
- this follows the LangChain pattern of using runtime context to inject configuration and structured outputs to reserve stable fields for warnings and assumptions

## Security note

- PII detection currently relies on LangChain built-in middleware for email and credit-card patterns
- custom API-key detectors are intentionally not implemented to avoid regex and hardcoded secret patterns
- secrets protection must come from configuration hygiene, no credential persistence in traces, and careful logging

## Graceful recovery

ecoIA should not give up at the first missing field, ambiguous result, or tool failure.

Before failing, it should try:

- user follow-up for the smallest missing input
- explicit assumption candidates
- declared scenarios
- cached data
- partial results when only part of the question can be answered safely

It must never:

- invent coordinates if geocoding fails
- invent production if PVGIS fails
- invent prices if ESIOS data is unavailable
- invent subsidies if BDNS fails
- invent panel specifications that were never provided or explicitly assumed

## Trace expectations

Relevant trace event kinds include:

- `message_received`
- `delegation`
- `tool_call`
- `assumption_used`
- `recovery_attempt`
- `missing_information`
- `partial_result`
- `tool_retry`
- `fallback_used`
- `warning`
- `final_answer_generated`

The trace should make it clear what failed, how recovery was attempted, and what remained partial.
