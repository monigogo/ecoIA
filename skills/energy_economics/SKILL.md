---
name: energy_economics
description: Estimate economic impact of solar self-consumption — direct savings, simplified compensation, market sale references, and bill impact — using public price providers (ESIOS, OMIE) and deterministic economic tools.
---

# Energy Economics skill

## When to use

User asks about savings, payback, bill impact, surplus compensation,
selling energy, or comparing battery storage against export.

## Conceptual distinctions

- Direct self-consumption savings: avoided grid imports valued at the
  user's import price.
- Simplified compensation (PVPC): exported energy is valued at the
  ESIOS surplus price, capped by the same period energy term. Never
  produces a negative bill.
- Market sale: real wholesale revenue (OMIE) — only available with the
  right contract; net of representation, taxes, and access charges.
- PVPC ≠ free market. Always confirm contract.

## Economic separation rule (mandatory)

1. **Savings**: solar energy self-consumed × avoided import price.
   Use `estimate_self_consumption_savings`.
2. **Compensation**: surplus credited on the bill, normally capped,
   no negative bill possible. Use `estimate_export_compensation`.
3. **Sale**: surplus sold as a producer or via representation, not
   equivalent to simplified compensation. Use
   `estimate_export_sale_revenue`. Net revenue is only reported when
   fees, taxes, or representation costs are supplied explicitly.

Never use "earn" for simplified compensation unless you also explain
it is a bill credit, not net income.

## Process

1. Identify the question: savings, compensation, sale, bill impact, or
   storage vs export.
2. Collect explicit inputs (consumption, generation, prices) from the
   user. If a price is missing, choose a price tool consciously:
   - PVPC simplified compensation → `get_pvpc_surplus_compensation_price`.
   - PVPC import reference → `get_pvpc_import_reference_price`.
   - Wholesale reference → `get_market_sale_reference_price`.
3. If the price series is in EUR/MWh, call
   `normalize_energy_price_series` to convert to EUR/kWh.
4. Run the deterministic economic tool that matches the question:
   `estimate_self_consumption_savings`, `estimate_export_compensation`,
   `estimate_export_sale_revenue`, `estimate_energy_bill_impact`, or
   `compare_battery_vs_export`.
5. Disclose every price source, indicator id or market area, date
   range, and the structured warnings returned by the price tool.

## Output

- Numeric result (savings, compensation, bill delta, comparison).
- Source of every price (user, ESIOS indicator id, OMIE market area).
- Warnings carried through from the price provider.
- Disclaimer that simplified compensation is not market sale and that
  OMIE is not residential net revenue.

## Forbidden

- Inventing prices.
- Hardcoded fallback prices when an API fails.
- Assuming PVPC without explicit user confirmation.
- Reporting OMIE wholesale price as a user's selling price.
