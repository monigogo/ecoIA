---
name: rdtools_analysis
description: Run reproducible degradation/soiling/availability analysis on real PV time-series data using RdTools. Advanced module for existing installations.
---

# RdTools Analysis skill

## When to use

User uploads or references real PV time-series data and wants degradation, soiling, or availability metrics.

## Process

1. Validate CSV schema (timestamp, AC power, irradiance, temperature).
2. Normalize data per RdTools conventions.
3. Run year-on-year degradation analysis.
4. Optionally run soiling and availability analyses.
5. Return metrics + interpretation.

## Output

- Estimated degradation rate (%/year) with confidence interval.
- Soiling losses (if computed).
- Data quality flags.
- Notes on caveats (data window, sensor coverage).
