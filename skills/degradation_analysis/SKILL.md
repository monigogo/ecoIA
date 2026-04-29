---
name: degradation_analysis
description: Estimate panel degradation and lifetime production over 25 years using standard degradation rates.
---

# Degradation Analysis skill

## When to use

User asks about long-term production, panel lifetime, or 25-year output.

## Process

1. Take baseline year-1 production from solar_planning.
2. Apply standard linear degradation (default ~0.5%/year, configurable per panel tech).
3. Compute year-by-year production curve.
4. Sum lifetime energy.

## Output

- Year-by-year production array.
- Cumulative lifetime production (kWh).
- Production at year 25 vs year 1 (%).
- Assumptions used.
