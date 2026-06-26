# Planning Model

This document is the canonical human-readable spec for the ski planning model.

## Purpose

The planning model answers two related questions:

- How good is a resort likely to be for a requested travel window?
- How trustworthy is that answer, based on archive history, current forecast, or fallback heuristics?

The executable algorithm lives in [`app/domain/planning.py`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/domain/planning.py). Tunable weights, thresholds, and canonical wording live in [`app/domain/planning_policy.py`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/domain/planning_policy.py).
The scientific evidence policy and rebuild workflow are documented in
[`docs/snow-evidence-model.md`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/docs/snow-evidence-model.md).

## Supported Inputs

The planning API supports two input shapes through `/api/search`:

- `travel_month`
- `trip_start_date` + `trip_end_date`

Precedence:

- if `trip_start_date` and `trip_end_date` are present, exact-date planning is used
- otherwise `travel_month` planning is used

`travel_month` remains for month-level planning and backward-compatible search requests. Exact-date planning is the preferred source of truth for saved-trip companion behavior when concrete trip dates are known.

Ski areas may also define exact `season_windows` with `start_date` and
`end_date` for a specific operating season. Exact-date planning checks those
windows first when the requested trip year matches a known window. If no
relevant exact window is known, the model falls back to `season_start_month` and
`season_end_month`. Month-only planning always uses the month fields.

## Search Fit Semantics

The planning model sits inside the broader recommendation contract:

- `min_price` and `max_price` are nightly stay-base budget estimates in EUR.
- rental prices are separate display facts, not part of a combined package price.
- the compatibility field `stars` means internal stay-base quality tier: `1=budget`, `2=standard`, `3=premium`.
- `availability_status` means weather-derived disruption/conditions status unless provenance is explicitly `reported`.

These semantics keep ranking explainable while the catalog is still curated rather than provider-backed.

The resort fit model separates raw catalog facts from derived fit factors.
Search still accepts compatibility filters such as `stars`, `skill_level`, and
`lift_distance`, but factor policy should gradually own the semantics behind
terrain scale, skill fit, stay-base access, and trust caps. An `active`
resort-fit factor means it is defined, derivable, and ranking-ready inside
factor policy after review; it does not authorize production `/api/search`
ordering, saved-trip grouping, or itinerary ranking changes. Production ranking
weights should not be changed until the later ranking-integration checkpoint and
ranking comparison output have been reviewed.

### Ranking Comparison Diagnostics

Candidate resort-fit scoring can be inspected through a debug report:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison
```

The report writes `ranking-comparison-summary.json` and
`ranking-comparison-report.md`. It compares `search_v1` order against candidate
factor scoring and remains useful for review even after `search_v2` is enabled.

The diagnostic report records:

- current rank, candidate rank, and rank delta;
- top candidate score components;
- terrain source scope: selected `ski_area`, destination-local `terrain_group`,
  or shared `terrain_domain`;
- result-group keys and group counts, so product review can see when multiple
  option rows compete for one destination or linked-domain user-facing result.

Use this output as the required review artifact before any production
ranking-integration checkpoint. A repeated group such as
`terrain-domain:tignes-val-disere` means the scorer is still evaluating option
rows, while product grouping may later need one top-level linked-domain result
with nested destination/ski-area/stay-base alternatives.

### Search Model Versions

Production search ranking is selected by `SNOWCAST_SEARCH_MODEL`.

- `search_v1`: legacy search scoring and ordering.
- `search_v2`: resort-fit candidate scoring using terrain scale, skill fit,
  stay-base access, snow evidence, conditions, budget penalty, and travel
  effort.

Private manual testing can request a model override with
`debug=true&search_model=search_v2`, but only when
`SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE=true`. Normal requests use the configured
model, which keeps rollback simple while the app is pre-public.

`search_v2` changes `/api/search` ordering when selected, but it does not change
saved-trip option grouping or itinerary ranking behavior. `planning_policy.py`
remains the policy home for snow, travel-window, climatology, forecast, and
planning-evidence semantics rather than resort-fit factor weighting.

## Recommendation Grouping

Search evaluates concrete trip options internally: selected ski area, stay base,
rental estimate, snow/planning evidence, budget fit, and optional travel effort.
The main response then groups those options by destination plus selected ski area
so the UI can show one compact recommendation card with a `top_option` and a
small set of `alternative_options`.

Weather, seasonality, archive, and climatology evidence remain scoped to the
selected ski area inside the grouped card. A destination-level card such as
Chamonix Mont-Blanc can inherit its score from the best concrete option, for
example "stay in Argentière, ski Grands Montets", but the card must not imply
that one blended Chamonix-wide snow score exists. Alternative ski areas under the
same destination should keep their own evidence scope and caveats.

The user-facing React search surface should describe the ranked object as a
trip configuration: destination + ski area + stay base + travel window +
travel effort + budget fit + evidence quality. That keeps the product from
reading like a generic resort list or a hotel marketplace while preserving the
backend grouping contract.

Existing selected stay-base fields remain on `SearchResult` for compatibility
and mirror the `top_option`. Alternative options are stay-base previews inside
the same destination/ski-area context; they are not separate global filters and
do not change resort-level weather, date-window, or evidence provenance.

Multiple cards for the same destination are allowed when the selected ski area is
materially different. Multiple stay bases for the same destination/ski-area group
should appear as alternatives under that card instead of duplicate top-level
results.

Linked cross-destination domains such as Tignes-Val d'Isere should eventually
group into one user-facing domain result with destination and stay-base
alternatives, but the scored rows still remain concrete destination + ski area +
stay base options. Terrain domains and terrain groups can influence accessible
terrain scale; they do not replace ski-area weather evidence.

## Weather Evidence Metrics

Search results and public resort pages may include optional historical weather metrics for the selected travel window:

- `average_snow_depth_cm`
- `average_daily_snowfall_cm`
- `average_max_temperature_c`
- `average_wind_gust_kmh`
- `evidence_years`
- `latest_observed_on`
- `elevation_band`
- `elevation_m`

These metrics are derived from `ski_area_snow_climatology_daily` when the
derived climatology table has rows for the requested window. If climatology is
missing, the model falls back to `raw_weather_history` rows with
`record_type = "archive"` and `elevation_band = "mid"` by default.

Both tables are keyed by `ski_area_id`. Destination, terrain-group, and
terrain-domain displays may summarize or select from member ski-area evidence,
but they should not create implicit destination-level weather history.

For `travel_month`, matching rows are all derived climatology rows or archive
observations from that month across available years. For exact dates, matching
rows use the same recurring month/day window as exact-date planning. Forecast
rows, heuristic-only fallback, and legacy snapshot fallback do not synthesize
these metrics; the object remains `null` when archive/climatology rows are
unavailable.

Snow-depth display metrics ignore implausible provider outliers above 8m of snow depth. That prevents summit/upper-mountain artifacts from producing unrealistic public values while keeping the raw rows available for future model work.

The metrics are user-facing explanation data, not ranking inputs. They let the UI say things like "Mid-mountain typical snow depth: 135 cm" without changing the underlying resort ordering.

## Evidence Sources

The model can draw on four evidence layers:

1. Derived snow climatology
- source table: `ski_area_snow_climatology_daily`
- preferred request-path evidence source once populated
- default planning metrics use `elevation_band = "mid"`
- stores `normal_30y` and `recent_15y` day-of-season aggregates
- exposes evidence-season counts and display metrics without loading raw daily
  rows

2. Archive weather history
- source table: `raw_weather_history`
- only rows with `record_type = "archive"` count as planning evidence
- default planning metrics use `elevation_band = "mid"`
- forecast rows are intentionally excluded from historical planning windows
- used as fallback and as the rebuild/audit source for climatology

3. Current forecast conditions
- source: latest refreshed `resort_conditions`
- keyed and retrieved by `ski_area_id`; the stored ski-area name is display
  metadata, not a lookup key
- used only when the trip window is close enough to justify it

4. Heuristic baseline
- seasonality
- elevation
- sparse-evidence penalties

Legacy `resort_condition_history` snapshot rows remain as a fallback when
climatology and archive history are weak or absent.

## Evidence Window Construction

### Month planning

For `travel_month`, derived climatology rows are selected by calendar month.
When climatology is missing, raw archive rows are grouped into year-month
windows:

- select archive rows whose observed month matches the requested month
- group them by `(year, month)`
- normalize each row into planning conditions
- average each window into a single yearly evidence window

### Exact-date planning

For `trip_start_date` / `trip_end_date`, derived climatology rows are selected
by recurring calendar month/day. When climatology is missing, archive rows are
matched by calendar month/day across prior years:

- normalize each archive row to its month/day
- normalize the requested trip window to month/day
- include archive rows whose month/day falls inside that recurring window
- group matched rows by year
- average each year into one evidence window

This is a recurring seasonal-date match, not a rolling weather-pattern similarity model.

Exact-date requests are still bounded by the resort season check before weather
evidence is blended. Known exact `season_windows` take precedence over coarse
month windows, so a trip just before an explicitly published opening date is
treated as out of season even when the month itself is usually in season.

## Core Blend

The planning algorithm blends:

- derived climatology or raw archive evidence
- heuristic baseline
- optional current forecast assistance

When raw archive evidence exists:

- `history_weight = (1 - current_weight) * 0.7`
- `heuristic_weight = 1 - current_weight - history_weight`

Then:

- snow score = `average_archive_snow * history_weight + heuristic_snow * heuristic_weight`
- conditions score = `average_archive_conditions * history_weight + heuristic_conditions * heuristic_weight`

If current forecast assistance is enabled, the current forecast contribution is then added on top using `current_weight`.

When derived climatology exists, the 30-year normal is the primary evidence
source. The recent 15-year baseline nudges the 30-year normal using the
policy-defined recent-adjustment weight. The resulting climatology score is
then blended with the heuristic baseline and optional forecast assistance.
Climatology with fewer than the archive-backed season threshold receives a
small evidence penalty and maps to the cautious `fallback_heavy` public profile
until a dedicated limited-archive profile is added.

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

- climatology or archive evidence exists
- current forecast gets non-zero weight
- the trip window is close enough that live forecast should materially influence the result

### `archive_backed`

Meaning:

- climatology or archive evidence exists
- current forecast does not materially contribute
- the result is mostly driven by historical evidence plus heuristics

### `fallback_heavy`

Meaning:

- climatology/archive evidence is sparse or absent
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
- climatology blend and recent-baseline adjustment weights
- climatology evidence thresholds and low-coverage penalties
- sparse-evidence penalties
- forecast horizon thresholds and weights
- canonical evidence-profile summary templates
- canonical provenance/basis-summary templates

## What Is Still Transitional

- `travel_month` compatibility remains in place for month-level planning and older client flows
- web and mobile clients can send exact trip dates through `trip_start_date` and `trip_end_date`; exact dates take precedence over month-level planning when both are available
- date matching is seasonal calendar-window matching, not a richer similarity model
- planning still uses legacy snapshot fallback in weak archive-evidence cases

Those are deliberate transitional constraints, not hidden behavior.
