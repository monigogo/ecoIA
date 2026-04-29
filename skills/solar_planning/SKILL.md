---
name: solar_planning
description: Plan a residential/commercial solar PV installation from user inputs (location, consumption, roof). Estimate panel count, orientation, annual production via PVGIS, and physical layout on the available surface.
---

# Solar Planning skill

## When to use

User asks about installing solar panels, sizing a system, estimating
production for a given location and consumption, or fitting panels in
a roof / surface.

## Architecture note

The supervisor handles basic solar sizing directly using the core solar
tools. It only delegates to specialized subagents for isolated domains:
degradation-analyst, battery-advisor, subsidy-finder, energy-economics-
advisor, rdtools-analyzer, and report-synthesizer.

## Required inputs

- Location (city or coordinates).
- Annual or monthly consumption (kWh).
- Optional: roof area, tilt, azimuth, available budget.
- For physical layout: usable width and length, panel dimensions,
  spacing, maintenance margin.

## Core solar estimation workflow

1. **Geocode location** with `geocode_location` (textual locations only).
   If geocoding returns multiple candidates, ask user to disambiguate.
2. **Resolve missing parameters**:
   - if three or more base PV parameters are missing, use
     `get_solar_base_scenario_candidates` once when the user accepts an
     orientative estimate;
   - otherwise use `get_assumption_candidates` for the smallest missing
     blocking parameter only.
   In both cases, disclose source, confidence, and limitations.
   If a chosen scenario already supplies a field, do not reopen that same
   field with `get_assumption_candidates`.
3. **Call PVGIS** with `estimate_solar_production_with_pvgis` once
   latitude, longitude, peak power, losses, tilt, and azimuth are
   explicit. Do not let PVGIS fill missing parameters implicitly.
4. **Compute deterministic values** with:
   - `calculate_system_kwp` — system peak power from panel count/wattage
   - `calculate_annual_consumption` — normalize monthly to annual kWh
   - `calculate_coverage` — production vs consumption ratio
   - `estimate_panels_for_future_target` — panels needed for target year
5. **Physical layout** (if user asks about fitting panels, see below).

## Physical layout

When the user mentions area, surface, meters, distance, rows, fit, or roof:

1. Separate three quantities:
   - panels required by energy demand
   - panels physically fittable in the available area
   - panels recommended after considering both
2. Use the layout tools:
   - `calculate_panel_capacity_by_area` — how many panels fit on an
     explicit rectangular area.
   - `calculate_required_area_for_panels` — area required for an
     explicit panel count.
   - `calculate_row_spacing_for_self_shading` — geometric row spacing
     for a given tilt and solar elevation criterion.
   - `evaluate_layout_feasibility` — compare energy-required vs
     physically-fittable and report the gap.
3. Never assume panel dimensions, spacing, or maintenance margin. If
   several of them are missing together, prefer
   `get_solar_base_scenario_candidates` once over multiple field-by-field
   assumption calls. If the user did not accept an orientative scenario,
   ask for the smallest missing input instead.
4. Solar elevation for self-shading is an explicit design criterion
   (e.g. winter solstice noon at the user's latitude); never pick it
   silently.
5. Declare results as geometric approximations. They do not replace
   a professional design or shading study.

## Forbidden

- Numeric defaults applied silently
- Invented panel dimensions, spacing, or maintenance margins
- Regex extraction or keyword matching for intent
- Silently filling missing PVGIS parameters
- Repeated field-by-field assumption calls to assemble a base panel
  scenario

## Output

- Estimated annual production (kWh).
- Panel count and total kWp.
- Coverage ratio vs consumption.
- Layout: max panels by area, layout grid (rows × columns),
  orientation chosen, used vs unused area.
- Feasibility verdict: energy-required vs physically-fittable, gap,
  optional coverage of target if energy-per-panel is supplied.
- Assumptions used and their source.
