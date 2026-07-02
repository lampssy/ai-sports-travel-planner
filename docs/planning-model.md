# Planning Model

This document is the canonical human-readable specification for Snowcast
planning and ranking.

## Purpose

The model ranks concrete trip configurations and groups them into trip markets.
It answers:

- which stay destination, stay base, ski area, and pass best fit the request;
- how strong snow and conditions evidence is for the selected ski area; and
- which alternatives belong under the same market rather than occupying
  additional top-level slots.

The executable planning algorithm lives in app/domain/planning.py. Search V3
candidate generation, scoring, and grouping live in app/domain/search_v3_*.py.
Tunable weather/evidence policy lives in app/domain/planning_policy.py.

## Supported Inputs

The search API accepts country, nightly lodging budget, quality tier, skill
level, optional lift-distance preference, optional origin/travel tolerance, and
one travel window:

- month planning through travel_month; or
- exact planning through trip_start_date plus trip_end_date.

Exact dates take precedence. Ski-area season windows are checked before
month-based fallback when a matching season is known.

## Search V3 Candidate

A candidate is a TripConfiguration:

- SkiRegion trip-market identity;
- StayDestination and StayBase;
- independently stored focus SkiArea;
- explicit SkiAreaAccess edge;
- selected LiftPassProduct and alternative pass products;
- lodging budget/quality fit and optional travel effort; and
- current and historical evidence for the focus ski area.

No access is inferred from shared branding, destination nesting, or pass
coverage. Candidate generation reads only explicit active catalog relations.

## Ranking Components

Search V3 adapts the previously reviewed Search V2 global components to the
normalized candidate:

- lodging quality;
- terrain scale, capped by source trust;
- skill fit, capped by source trust;
- stay-base-to-area access fit, capped by source trust;
- snow evidence;
- current conditions;
- budget penalty; and
- optional travel-effort penalty.

The selected pass is chosen deterministically from availability, date-matching
price examples, coverage, and stable tie-breaking. Pass fit selects the pass but
does not add a ranking component in Search V3.

Resilience describes alternative ski areas available on the selected pass and
their evidence coverage. It is measured-not-ranked. Any future score influence
from pass fit, resilience, operational status, crowds, amenity fit, or predicted
open terrain requires a new search-model version and an explicit review of
weights and behavior.

## Recommendation Grouping

Search ranks concrete configurations, then groups them by trip-market
ski_region_id. Each RecommendationGroup contains:

- the winning configuration;
- up to three alternatives from the same market; and
- a group score equal to the winning configuration score.

Alternative selection preserves score order while prioritizing an unseen stay
destination, then an unseen focus ski area, before using remaining slots for
additional bases on terrain already represented. The winning configuration and
group score do not change.

This prevents Tignes and Val d'Isere, or the three Campiglio stay destinations,
from consuming several top-level result slots when they represent one reviewed
trip market. The winning card still names the concrete stay destination, stay
base, selected ski area, access, and pass.

Weather is never averaged merely because configurations share a group. Every
configuration keeps conditions, archive history, climatology, and evidence
quality from its selected ski_area_id.

## Search Model Contract

search_v3 is the only supported runtime model. SNOWCAST_SEARCH_MODEL defaults to
search_v3 and rejects retired search_v1/search_v2 values. A private debug request
may explicitly request search_v3 only when
SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE=true and debug=true.

## Weather Evidence Metrics

Search results and public stay-destination pages may include optional historical
weather metrics for each explicitly named ski area in the selected travel window:

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

Both tables are keyed by `ski_area_id`. Ski-region and terrain-domain displays may summarize or select from member ski-area evidence,
but they should not create implicit destination-level weather history.

For `travel_month`, matching rows are all derived climatology rows or archive
observations from that month across available years. For exact dates, matching
rows use the same recurring month/day window as exact-date planning. Forecast
rows, heuristic-only fallback, and legacy snapshot fallback do not synthesize
these metrics; the object remains `null` when archive/climatology rows are
unavailable.

Snow-depth display metrics ignore implausible provider outliers above 8m of snow depth. That prevents summit/upper-mountain artifacts from producing unrealistic public values while keeping the raw rows available for future model work.

The metrics are user-facing explanation data, not ranking inputs. They let the UI say things like "Mid-mountain typical snow depth: 135 cm" without changing the underlying configuration ordering.

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

## Remaining Deliberate Constraints

- travel_month remains supported for month-level planning;
- date matching uses recurring calendar windows rather than a richer analogue
  season model;
- weak archive coverage can still fall back to legacy condition snapshots;
- pass fit and resilience are visible but intentionally do not influence score;
- predicted open lifts/pistes, crowds, and property amenities are future
  evidence/factor families, not fields to overload onto the static catalog.
