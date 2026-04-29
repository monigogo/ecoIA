---
name: ods7_impact
description: Translate solar plan output into ODS 7 impact metrics (clean energy generated, CO2 avoided, equivalent households).
---

# ODS 7 Impact skill

## When to use

User asks about environmental impact, CO2 savings, or contribution to ODS 7.

## Process

1. Take lifetime production (kWh) from degradation_analysis.
2. Apply Spain grid emission factor (default ~0.19 kgCO2/kWh, configurable).
3. Compute CO2 avoided over lifetime.
4. Compute equivalent metrics (households powered, trees, km not driven).

## Output

- CO2 avoided (kg, ton).
- Households equivalent.
- Narrative framing aligned with ODS 7.
- Source for emission factor.
