# ADR 0003: Use Derived Snow Climatology For Planning Evidence

Status: accepted
Date: 2026-06-15

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-06-15-snow-evidence-climatology-design.md`

Related docs:
- `docs/snow-evidence-model.md`
- `docs/planning-model.md`
- `docs/engineering-notes.md`

## Context

Snowcast is moving toward multi-decade daily historical weather evidence. A
30-year archive across 100-200 ski areas and several elevation bands is still
reasonable to store in Postgres, but it should not be read wholesale on every
search request.

The prior optimization moved raw-history reads to SQL-window-scoped queries.
That reduced the immediate request-path cost, but long-term planning still
needs stable day-of-season statistics, evidence counts, and user-facing metrics
without repeatedly reconstructing raw daily model objects.

The product also needs a scientifically defensible planning model. The practical
standard for long-horizon climate context is a 30-year normal, while near-term
trip decisions can blend that with current forecast only when the travel window
is close. Physical snowpack models such as SNOWPACK, Crocus, or S2M-style
chains are stronger for operational snowpack simulation, but they are too heavy
for the current product stage.

## Decision

Keep `raw_weather_history` as the audit/rebuild source and add a derived daily
climatology read model:

- table: `ski_area_snow_climatology_daily`
- key: ski area, elevation band, month, day, baseline period, source-model
  version
- baseline periods:
  - `normal_30y`
  - `recent_15y`
- request-path lookup index:
  - ski area
  - elevation band
  - baseline period
  - month
  - day

Search planning should prefer derived climatology, fall back to window-scoped
raw archive rows only when climatology is missing, then fall back to legacy
snapshots or heuristics.

The derived climatology includes:

- snow-depth percentiles
- 30 cm / 50 cm threshold probabilities
- snowfall, rain-risk, freeze-thaw, temperature, and wind summaries
- average empirical Snowcast snow-confidence and conditions scores
- evidence-season count

## Consequences

Search can answer far-future travel-window planning from a small indexed table
instead of loading years of daily archive rows.

Raw historical data remains available for audit, rebuilding, and future model
work.

The 30-year normal and 15-year recent adjustment are explicit model policy
rather than hidden heuristics.

The implementation introduces an additional rebuild command that must be run
after large historical backfills or after changing weather-critical coordinates,
elevations, or empirical scoring policy.

The model remains empirical and planning-oriented. It should not be described as
an official resort snow report or as a physical snowpack simulation.

## Alternatives Considered

- Keep only raw archive rows and query them on every search. This preserves
  auditability but keeps too much CPU, memory, and Pydantic model construction on
  the request path.
- Use monthly aggregates only. This is simpler, but too coarse for exact trip
  windows such as March 21-27 versus late April.
- Use only 15 recent seasons. This may better reflect climate change, but is
  less stable and departs from the common 30-year climatology baseline.
- Implement or consume physical snowpack models now. This could be scientifically
  stronger, but it adds data, compute, calibration, validation, and operating
  complexity before the product needs that level of precision.
- Move climatology to a separate analytics store. This is unnecessary for the
  expected initial scale and adds operational overhead.

## Revisit When

Revisit this decision when:

- search latency remains high after climatology preloading is populated
- supported ski areas exceed the expected 100-200 range
- the app needs blended base/mid/upper evidence instead of one preferred band
- source providers offer licensed snowpack/climatology products at reasonable
  cost
- Snowcast begins making high-stakes operational claims rather than booking
  decision support
- the project adopts a migration framework that should own index/table changes
  outside bootstrap
