---
name: report_generation
description: Synthesize all subagent outputs into a final structured response with assumptions, warnings, and a natural trace of the reasoning.
---

# Report Generation skill

## When to use

Final step before returning to user. Aggregate solar plan, degradation, battery, subsidies, and ODS 7 impact.

## Process

1. Collect outputs from all upstream subagents.
2. Build structured response (Pydantic schema in `app/schemas/responses.py`).
3. Append assumptions list.
4. Append warnings (low confidence, missing data, regulatory caveats).
5. Embed natural trace from `NaturalTraceLogger`.

## Output

- Structured JSON response.
- Human-readable summary text.
- Natural trace of reasoning steps.
