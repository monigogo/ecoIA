---
name: battery_sizing
description: Recommend approximate battery storage capacity based on consumption profile, autonomy days, and self-consumption goals.
---

# Battery Sizing skill

## When to use

User asks if a battery is worth it, or what capacity to install.

## Process

1. Take daily consumption (kWh/day).
2. Apply target autonomy (default 1 day for residential).
3. Apply depth-of-discharge factor (default 80%).
4. Apply round-trip efficiency (default 90%).
5. Recommend nominal capacity range.

## Output

- Recommended usable kWh.
- Recommended nominal kWh (with DoD margin).
- Assumptions used.
- Caveats (cost not estimated, regulatory check needed).
