# ADR 0002: Use Window-Scoped Raw Weather Planning Queries

Status: accepted
Date: 2026-06-15

Supersedes: N/A
Superseded by: N/A

Related specs:
- N/A

Related docs:
- `docs/engineering-notes.md`
- `docs/planning-model.md`

## Context

Snowcast search and public planning metrics derive weather evidence from
`raw_weather_history`. After the elevation-banded backfill work, each ski area
can store multiple years of daily archive rows for base, mid, and upper
elevation bands.

The original search preload path loaded all raw rows for every candidate ski
area and filtered the requested month or exact trip dates in Python. That was
acceptable with a small dataset, but it scales poorly as the archive grows:

- country-level searches can match many ski areas
- each ski area can have multiple years of daily rows
- Python then builds Pydantic `RawWeatherObservation` objects for rows that are
  irrelevant to the requested travel window
- deployed memory pressure can appear before the final search result is even
  built

The owner decision was to implement the low-risk optimization now: move
travel-window filtering to SQL and add the matching database index. Larger
materialized or pre-aggregated metric tables remain deferred until the archive
size or query patterns justify them.

## Decision

Search planning evidence queries must be travel-window scoped at the repository
boundary before Python model construction.

For month-level planning, the repository converts `travel_month` into concrete
date ranges for each historical year. For exact-date planning, it converts the
requested trip start/end into recurring month/day ranges for each historical
year.

The query filters:

- `resort_id`
- `elevation_band`
- `record_type = 'archive'`
- `observed_on` within the generated historical date ranges

The database schema creates:

```sql
CREATE INDEX IF NOT EXISTS raw_weather_history_search_window_idx
ON raw_weather_history (
    resort_id,
    elevation_band,
    record_type,
    observed_on
)
```

Exact dates take precedence over `travel_month` when both are available.

## Consequences

Search no longer loads unrelated archive rows for non-requested months or date
windows. That reduces memory use and Pydantic model construction on the request
path.

The query shape remains compatible with the existing `/api/search` contract and
does not require a new schema table, ranking change, or response change.

The repository method now owns travel-window query policy, so service code can
stay focused on ranking and planning composition.

The implementation still issues a bounded bounds query before the window query.
That is acceptable for the current catalog and archive size, but it is not the
final shape for a much larger multi-decade or multi-region dataset.

Index creation currently runs through the project schema/bootstrap path. For a
substantially larger production table, this may need a dedicated migration step
using a deployment-safe index creation strategy.

## Alternatives Considered

- Filter with SQL `EXTRACT(MONTH FROM observed_on)` or `TO_CHAR` predicates.
  This keeps query code shorter, but it makes normal B-tree index usage harder
  unless the project adds expression indexes. It also hides the exact date
  ranges being queried.
- Keep loading all rows and filter in Python. This is simplest, but it scales
  poorly in memory and CPU as archive years, ski areas, and elevation bands
  grow.
- Add a precomputed monthly or travel-window metrics table now. This could be
  faster for reads, but it adds write-path complexity, invalidation policy, and
  another data model before the observed bottleneck requires it.
- Use an ORM to express the same query. This would not solve the bottleneck
  because the bottleneck is query selectivity and indexing, not SQL syntax.

## Revisit When

Revisit this decision when:

- search still shows high DB latency or memory pressure after window-scoped
  queries and banded backfill
- the raw archive grows enough that generated per-year `OR` ranges become
  unwieldy
- public pages or search need aggregate metrics across many resorts/months at
  once
- the project introduces a formal migration framework that can handle
  deployment-safe index creation separately from startup schema checks
- ranking begins to require blended base/mid/upper evidence rather than the
  current default mid-band planning metrics
