# Planning And Weather Evidence Model

This document explains Snowcast planning evidence and its boundary with the
active Search V4 ranking model. The exact ranking equation, active factor
inventory, weights, activation rules, and refinement behavior live in
[`docs/search-ranking-model.md`](search-ranking-model.md).

## Context Boundaries

Snowcast has two related but separate planning contexts:

- **Discovery search** ranks concrete trip configurations for a requested
  travel window. Search V4 owns this behavior.
- **Current-trip companion planning** explains a saved trip using current
  conditions and the legacy planning helpers in `app/domain/planning.py` and
  `app/domain/planning_policy.py`.

The latest one-day `resort_conditions` snapshot remains useful for current-trip
display. It is not evidence for a future search date and does not enter Search
V4 ranking.

## Search V4 Inputs And Candidate

`POST /api/search` accepts a typed `SearchIntent`. It can contain:

- geographic scope;
- a month or exact dates, with exact dates taking precedence;
- lodging, travel, quality, feature, and pass-price constraints;
- party skill levels and travel context;
- group priorities, factor preferences, and objectives; and
- visible assumptions.

A Search V4 candidate is one explicit catalog configuration:

```text
Trip-market ski region
  + stay destination
  + stay base
  + ski-area access edge
  + focus ski area
  + applicable lift-pass product
```

No access or pass relationship is inferred from shared branding or geographic
proximity. Candidate generation expands every applicable pass for each access
edge so an arbitrary default pass cannot alter ranking. Hard constraints run
before any weather preload or factor scoring.

Search ranks candidates and then groups them by trip-market ski region. The
winning configuration defines the group score. Up to three materially distinct
alternatives may expose another stay destination or focus ski area in the same
market. Weather evidence always remains scoped to the selected ski area.

## Search V4 Snow Evidence

Search V4 uses one composed ranking factor, `trip_window_snow_fit`. It combines
two registered explanation components:

- `climatological_snow_reliability`; and
- `trip_window_snowpack_outlook` for exact dates with a usable forecast.

They are components of one factor, not independent full-strength bonuses.

For each requested ski day `d`:

```text
forecast_share_d = lead_time_share_d * usable_date_coverage_d

natural_snow_utility_d =
    forecast_share_d * snowpack_outlook_d
  + (1 - forecast_share_d) * climatology_utility_d

trip_window_snow_fit = mean(day_utility_d)
```

If no evidence exists for a component, its utility is neutral rather than a
fabricated negative result. The factor's evidence cap and warnings expose
missing climatology or forecast dates.

### Lead-Time Blend

| Lead time | Maximum forecast share | Climatology share |
| --- | ---: | ---: |
| `0–5` days | `0.80` | `0.20` |
| `6–10` days | `0.60` | `0.40` |
| `11–16` days | `0.40` | `0.60` |
| `17–30` days | `0.15` | `0.85` |
| More than `30` days | `0` | `1.00` |

The forecast share is a cap. A missing, incomplete, or stale row contributes
zero forecast coverage, returning that part of the blend to climatology. A
month-only request has no target dates and is therefore climatology-only.

Forecast absence is classified separately from snow quality. Exact dates more
than 30 days away use `not_yet_available`; that is expected neutral context,
not a snow concern. Missing usable evidence inside the forecast horizon uses
`unexpectedly_unavailable`. The other states are `available`, `partial`, and
`not_applicable`.

### Climatology Reliability

For one requested calendar day, Search V4 calculates historical reliability
directly from the displayed climatology distribution:

```text
typical_depth = depth_curve(snow_depth_cm_p50)
depth_reliability =
    0.60 * P(snow depth >= 30 cm)
  + 0.40 * P(snow depth >= 50 cm)
historical_deterioration = max(P(rain risk), P(freeze-thaw))

climatology_utility = clamp(
    0.50 * typical_depth
  + 0.50 * depth_reliability
  - 0.25 * historical_deterioration,
  0,
  1
)
```

The equivalent flattened positive weights are `0.50` for median-depth
adequacy, `0.30` for the 30 cm probability, and `0.20` for the 50 cm
probability. Average historical snowfall and average maximum temperature stay
available for explanation; they do not add independent reliability bonuses.
Fresh-snow or powder likelihood is a separate future preference rather than a
hidden part of general historical reliability. A missing median snow depth
leaves the day unresolved instead of falling back to the legacy empirical
confidence score.

The detailed evidence view also shows the averaged historical deterioration
input, using the stronger rain or freeze-thaw probability for each matching
date. The backend names the largest negative contribution as the primary
concern reason; the UI does not reconstruct this explanation independently.

### Forecast Snowpack Outlook

The initial forecast evaluates the representative mid-mountain band. For a
usable daily row:

```text
snowpack_outlook = clamp(
    depth_adequacy
  + 0.15 * fresh_snow_benefit
  - 0.25 * max(rain_risk, thaw_risk),
  0,
  1
)
```

Depth, fresh snow, rain, and positive-degree-hour values are transformed by the
piecewise curves in `app/config/search-ranking/search-v4.toml`. Temperature,
freezing level, wind, and ensemble spread remain stored explanation and future
calibration inputs; they are not silently assigned extra ranking weights.

Modelled snow depth is not ski-area snow-cover percentage, open-piste
kilometres, or open-lift ratio. Those are separate planned factors and require
dedicated evidence.

### Conditional Snowmaking Resilience

Snowmaking never adds an unconditional bonus. It is used only when the user
requests the factor and positive catalog evidence exists. The uplift is largest
when natural snow utility is below `0.30`, declines to zero at `0.75`, is capped
at `0.25`, and cannot push the result above `1.0`. Unknown or unavailable
snowmaking gives no uplift.

## Forecast Acquisition And Serving

Search never calls a weather provider. Scheduled acquisition writes immutable,
versioned forecast runs and advances atomic per-ski-area/source heads only after
a complete area payload is published.

- Open-Meteo is the acquisition gateway.
- ECMWF IFS 0.25° ensemble mean is preferred through lead day 15.
- NOAA GEFS 0.5° ensemble mean supplies days 16–30 and fills shorter-range
  gaps when the preferred row is unusable.
- Search performs one bulk latest-head query for all eligible ski areas and
  requested dates.
- Stale heads are excluded and search falls back safely to climatology.

Refresh runs are no-ops when the same provider model initialization is already
complete. Retention keeps all recent issue versions, then thins older complete
runs to daily and weekly calibration samples while never deleting a run still
referenced by a head.

The full persistence, provider, publication, failure, and retention contract is
defined by ADR 0013 and
`docs/superpowers/specs/2026-07-13-trip-window-weather-forecast-evidence-design.md`.

## Historical Evidence

Derived climatology is read from `ski_area_snow_climatology_daily`, keyed by
`ski_area_id`, elevation band, baseline, and day of season. Search requests both
the 30-year normal and recent 15-year baseline in one bulk query. Search V4 uses
the normal as its scoring baseline and uses the recent row only when that normal
is unavailable; there is no hidden recent-period adjustment to the displayed
normal.

`raw_weather_history` remains the rebuild and audit source for climatology.
Forecast rows never become historical truth merely by ageing; recent archive
reconciliation replaces provisional forecast observations with archive data
when it becomes available.

## Trust, Freshness, And Provenance

Catalog source trust, prediction confidence, forecast freshness, and requested
date coverage are distinct concepts. Search exposes factor-level:

- raw and effective utility;
- effective evidence cap and its components;
- warnings;
- source/provenance summary; and
- explanation inputs, including per-day forecast source and run identity when
  applicable.

Run IDs are request-level provenance, not metric labels. Missing forecast heads
degrade readiness but do not make the search endpoint unavailable because
climatology is the defined fallback.

The current-trip companion may continue to use the older public evidence
profiles `forecast_assisted`, `archive_backed`, and `fallback_heavy`. Search V4
uses its typed factor breakdown instead of relabelling a latest snapshot as a
target-date forecast.

## Policy And Code Ownership

- Ranking and weather numerical policy:
  `app/config/search-ranking/search-v4.toml`
- Generic grouped scorer: `app/domain/search_ranking.py`
- Weather factor evaluators: `app/domain/search_factors/weather.py`
- Forecast run and daily models: `app/domain/weather_forecast.py`
- Forecast persistence/query surface:
  `app/data/weather_forecast_repository.py`
- Acquisition gateway: `app/integrations/open_meteo_forecast.py`
- Current-trip companion planning: `app/domain/planning.py` and
  `app/domain/planning_policy.py`

Change ranking weights, lead-time shares, curves, source preference, or
activation only through a versioned policy update with matching tests and a
regenerated inventory in `docs/search-ranking-model.md`.

## Deliberate Limits

- Search uses the representative mid-mountain band for its initial snow model.
- There is no provider-versus-observation calibration multiplier yet.
- Forecast issue versions are retained so later calibration can replay what was
  known at each issue time.
- Predicted open pistes/lifts, snow-cover percentage, crowds, property
  amenities, and lift-accessible off-piste terrain remain planned evidence
  families rather than overloaded static facts.
