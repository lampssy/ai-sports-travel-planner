# Planning Model

This document is the canonical human-readable spec for the ski planning model.

## Purpose

The planning model answers two related questions:

- How good is a resort likely to be for a requested travel window?
- How trustworthy is that answer, based on archive history, current forecast, or fallback heuristics?

The executable algorithm lives in [`app/domain/planning.py`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/domain/planning.py). Tunable weights, thresholds, and canonical wording live in [`app/domain/planning_policy.py`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/domain/planning_policy.py).

## Supported Inputs

The planning API supports two input shapes through `/api/search`:

- `travel_month`
- `trip_start_date` + `trip_end_date`

Precedence:

- if `trip_start_date` and `trip_end_date` are present, exact-date planning is used
- otherwise `travel_month` planning is used

`travel_month` remains a compatibility fallback for the current web client and parser. Exact-date planning is the preferred path for future clients.

## Evidence Sources

The model can draw on three evidence layers:

1. Archive weather history
- source table: `raw_weather_history`
- only rows with `record_type = "archive"` count as planning evidence
- forecast rows are intentionally excluded from historical planning windows

2. Current forecast conditions
- source: latest refreshed `resort_conditions`
- used only when the trip window is close enough to justify it

3. Heuristic baseline
- seasonality
- elevation
- sparse-evidence penalties

Legacy `resort_condition_history` snapshot rows remain as a fallback when archive history is weak or absent.

## Evidence Window Construction

### Month planning

For `travel_month`, archive rows are grouped into year-month windows:

- select archive rows whose observed month matches the requested month
- group them by `(year, month)`
- normalize each row into planning conditions
- average each window into a single yearly evidence window

### Exact-date planning

For `trip_start_date` / `trip_end_date`, archive rows are matched by calendar month/day across prior years:

- normalize each archive row to its month/day
- normalize the requested trip window to month/day
- include archive rows whose month/day falls inside that recurring window
- group matched rows by year
- average each year into one evidence window

This is a recurring seasonal-date match, not a rolling weather-pattern similarity model.

## Core Blend

The planning algorithm blends:

- archive evidence
- heuristic baseline
- optional current forecast assistance

When archive evidence exists:

- `history_weight = (1 - current_weight) * 0.7`
- `heuristic_weight = 1 - current_weight - history_weight`

Then:

- snow score = `average_archive_snow * history_weight + heuristic_snow * heuristic_weight`
- conditions score = `average_archive_conditions * history_weight + heuristic_conditions * heuristic_weight`

If current forecast assistance is active, the current forecast contribution is then added on top using `current_weight`.

After blending, the model still applies:

- single-window penalty
- sparse-evidence penalty
- late-spring caution penalties where applicable

## Forecast Assistance Rules

Forecast assistance is controlled by the forecast-window policy in `planning_policy.py`.

Current default thresholds:

- exact-date trips starting in `0–14` days: forecast weight `0.35`
- exact-date trips starting in `15–30` days: forecast weight `0.15`
- farther exact-date trips: forecast weight `0.0`

Month fallback weights:

- same month as the reference date: `0.20`
- next month: `0.08`
- later months: `0.0`

These values are tunable policy, not algorithm structure.

## Evidence Profiles

Planning provenance exposes an `evidence_profile` to make trust more legible.

### `forecast_assisted`

Meaning:

- archive evidence exists
- current forecast gets non-zero weight
- the trip window is close enough that live forecast should materially influence the result

### `archive_backed`

Meaning:

- archive evidence exists
- current forecast does not materially contribute
- the result is mostly driven by archive history plus heuristics

### `fallback_heavy`

Meaning:

- archive evidence is sparse or absent
- the result leans mostly on heuristics, and sometimes legacy snapshot fallback

This is the least trustworthy planning mode.

## Provenance Meanings

Planning provenance remains top-level `estimated`, but the evidence profile narrows that into:

- archive-backed estimate
- forecast-assisted estimate
- fallback-heavy estimate

Canonical provenance wording lives in `planning_policy.py` so the API/UI wording and the model spec stay aligned.

## Where Tunables Live

Planning tunables and canonical wording are centralized in:

- [`app/domain/planning_policy.py`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/domain/planning_policy.py)

This includes:

- seasonality and elevation heuristics
- sparse-evidence penalties
- forecast horizon thresholds and weights
- canonical evidence-profile summary templates
- canonical provenance/basis-summary templates

## What Is Still Transitional

- `travel_month` compatibility remains in place for the current web client
- exact trip dates are not yet stored in `CurrentTrip`
- date matching is seasonal calendar-window matching, not a richer similarity model
- planning still uses legacy snapshot fallback in weak archive-evidence cases

Those are deliberate transitional constraints, not hidden behavior.
