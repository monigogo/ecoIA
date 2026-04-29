---
name: subsidy_detection
description: Detect potentially applicable subsidies, municipal tax benefits, and IRPF tax deductions for solar installations in Spain via BDNS/SNPSAP, curated municipal data, and AEAT references.
---

# Subsidy Detection skill

## When to use

User asks about subsidies, grants, ayudas, IBI/ICIO bonifications,
Next Generation funds, or IRPF deductions related to solar/renewable
self-consumption.

## Conceptual distinctions (mandatory)

1. **Direct subsidy** — public call published in BDNS/SNPSAP.
2. **Municipal tax benefit** — IBI / ICIO / IAE bonuses defined by
   municipal ordinances.
3. **IRPF tax deduction** — state-level deductions managed by AEAT.

Never aggregate values across these categories. A subsidy is not a
deduction. A bonus is not income. A candidate is not a grant.

## Process

1. Collect explicit context: region, province, municipality,
   beneficiary type, technology, installation type, installation year,
   property type, available evidence.
2. For public calls: call `search_subsidies` with a reasoned
   natural-language query. Do not pre-filter by keyword.
3. For each promising candidate: call
   `evaluate_subsidy_compatibility`. The result is structured: level,
   matched, missing, and documents to verify.
4. For municipal IBI/ICIO/IAE: call `search_municipal_tax_benefits`
   with the explicit municipality.
5. For IRPF deductions: call `search_tax_deduction_candidates` with
   installation year, property type, work type, and user type.
6. Cite every source URL and id. Always declare that results are
   orientative and require official verification.

## Output

- Subsidy candidates with BDNS id, status, deadline, source URL.
- Per-candidate compatibility evaluation (level + reasoning).
- Municipal tax benefit candidates with ordinance reference.
- IRPF tax deduction candidates with AEAT reference and validity.
- Disclaimer: results are orientative; eligibility is decided by the
  issuing administration. The user must verify before applying.

## Forbidden

- Inventing calls, percentages, beneficiaries, or deadlines.
- Hardcoded scoring like "+30 if region matches".
- Keyword matching against the user message.
- Aggregating subsidies, municipal benefits, and IRPF deductions into
  a single number.
- Claiming a subsidy is granted.
