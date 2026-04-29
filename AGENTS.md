# SolarLife AI — Agent Context

Conversational backend for solar planning aligned with ODS 7.

## Mission

Help users plan residential/commercial solar PV installations: estimate production, degradation over 25 years, battery sizing, and detect available subsidies in Spain.

## Core capabilities

- Geocode user location.
- Query PVGIS for irradiance and production estimates.
- Request candidate assumptions from `AssumptionProviderTool` when user data is missing — never apply silent defaults.
- Calculate degradation and lifetime production via deterministic tools.
- Recommend approximate battery capacity.
- Detect subsidies via BDNS/SNPSAP and curated municipal datasets.
- Persist user/conversation memory.
- Emit a natural trace explaining reasoning.

## Reasoning rules (strict)

The agent must reason. The system must not.

### Forbidden

- Hardcoded default values silently applied to user requests.
- Regex-based intent detection or entity extraction.
- Keyword matching for classification (e.g. detecting "subvención" by string match).
- String similarity heuristics to pick a category.
- if/else branches that decide domain outcomes (degradation rate, battery sizing scenario, subsidy applicability).
- YAML/JSON files acting as "hidden defaults" that drive logic without being declared.

### Required

- LLM extracts entities and intent via structured output (Pydantic schema).
- LLM decides which tool to call and with what parameters.
- Domain calculations live in deterministic tools (math, no LLM arithmetic).
- Assumptions come from `AssumptionProviderTool`, which returns candidate scenarios with source, confidence, and disclosure requirement.
- The agent picks one assumption and declares it in the trace, with reasoning.
- External data (PVGIS, BDNS, geocoding) is the primary source. Reference values are fallback only, always cited.

## Source priority for any value

1. User-provided data (datasheets, real measurements, explicit values).
2. External API (PVGIS, BDNS/SNPSAP, geocoding, NASA POWER).
3. Uploaded documents (datasheets, prior bills) — extracted by LLM reasoning.
4. Versioned technical reference (cited, with confidence and disclosure flag).

## Operating principles

- Always declare assumptions used and their source.
- Cite data sources (PVGIS dataset version, BDNS ID, reference doc).
- Never invent regulatory or subsidy details.
- Prefer deterministic tool output over LLM guessing for numeric work.
- Return structured response + natural trace.

## Recovery rule

Do not give up at the first missing field, ambiguous result, or tool failure.

Before failing:

1. Identify what is missing or what failed.
2. Check whether the missing value can be obtained from:
   - user-provided data,
   - an external API,
   - uploaded documents,
   - AssumptionProvider candidates,
   - cached data,
   - a clearly declared scenario.
3. If recovery is possible, continue with explicit warnings.
4. If recovery is not possible, ask for the smallest missing piece of information.
5. Never invent values to recover.
6. Always record the recovery attempt in the natural trace.

## Out of scope (current MVP)

- Frontend.
- LangSmith.
- Real-time SCADA integration.
