# ADR 0013: Use Versioned Forecast Runs And Latest-Run Serving Heads

Status: accepted
Date: 2026-07-13

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-13-trip-window-weather-forecast-evidence-design.md`
- `docs/superpowers/specs/2026-07-10-search-v4-factor-registry-and-dynamic-refinement-design.md`

Related docs:
- `docs/search-ranking-model.md`
- `docs/planning-model.md`
- `docs/data-trust-model.md`
- `docs/domain-language.md`
- `docs/architecture/adr/0002-window-scoped-raw-weather-planning-queries.md`
- `docs/architecture/adr/0003-derived-snow-climatology.md`
- `docs/architecture/adr/0012-versioned-search-factor-registry-and-ranking-policy.md`

## Context

Search V4 needs forecast evidence aligned to exact requested ski dates and
representative ski-area elevations. Near-term forecast conditions may justifiably
outweigh historical climatology, but influence must fall with lead time,
coverage, confidence, and calibration.

The current conditions refresh stores the latest normalized one-day snapshot.
That supports present-conditions display but does not describe arbitrary future
trip dates. `raw_weather_history` supports archive and forecast row types, but
its uniqueness model does not preserve multiple issue versions, provider model
runs, or ensemble quantiles cleanly. Overwriting the latest valid-day row would
also remove the evidence needed to calibrate forecasts against later
observations.

Finding the latest issue through a request-path aggregate over all retained
runs would make query cost and index behavior more difficult to bound. Fetching
providers during search would couple user latency and availability to an
external weather service.

## Decision

Snowcast will persist forecast evidence as immutable versioned runs and expose
the latest complete evidence through atomic per-ski-area serving heads.

The persistence boundary will contain three concepts:

1. `weather_forecast_runs` identifies a stable forecast source key and its
   provider/model issue versions, forecast kind, issue and ingestion time,
   valid horizon, parser version, and run state.
2. `ski_area_weather_forecast_daily` stores normalized immutable daily rows by
   run, ski area, valid date, and elevation band, including supported ensemble
   summaries and completeness metadata.
3. `ski_area_forecast_heads` maps ski area and forecast source key to the latest
   validated complete run. Source-keyed heads allow multiple current ensemble
   routes to coexist without collapsing them into one generic ensemble head.

A background refresh creates a building run, fetches and normalizes bounded
provider batches, validates publishable area coverage, marks the run complete,
and atomically advances heads for successful areas. A failed or incomplete
area keeps its previous head. No head points to a building, rejected, or failed
run.

Search applies static constraints first, then obtains forecast rows for all
candidate ski areas and requested dates through one indexed bulk query joining
the heads to the immutable daily rows. Search will not:

- call a forecast provider;
- perform one forecast query per candidate;
- select the latest issue through `MAX(issued_at)` over retained daily rows;
- scan forecast history used for calibration.

Postgres is both source of truth and the initial serving surface. Redis or
another cache may be added only after measured search traces demonstrate a
need; any cache remains an optimization over the Postgres head contract.

The serving horizon is at most 30 days and normalized serving rows are daily.
The first implementation acquires the representative mid-mountain elevation
only while retaining elevation band in row identity. Open-Meteo is the initial
API gateway: ECMWF IFS 0.25 degree ensemble mean is preferred through lead day
15, while NOAA GEFS 0.5 degree ensemble mean supplies days 16 through 30 and is
the gap fallback for shorter dates. Planning selects one eligible source per
ski-area/date; it does not blend model products. Exact forecasts beyond an
eligible source horizon have zero coverage. Searches beyond 30 days use
climatology.

Lead day is calculated from the model initialization time published by
Open-Meteo's model-update metadata, not from retrieval time. The acquisition
job records that initialization and provider-availability time, waits through
the provider's documented ten-minute consistency window, and rejects a
building run if metadata shows that a new cycle appeared while coordinate
batches were being fetched. Daily snow depth is the instantaneous value at
12:00 local time; accumulated variables are summed and extrema are derived over
the complete 23-, 24-, or 25-hour local day. Required variables are declared
per source because optional spread and freezing-level support differs by model.
Incomplete boundary dates are omitted and never replaced by an adjacent date.

A bounded sample of old issue runs is retained to make a later
forecast-versus-observation calibration project possible. Historical
meteorological validation and an additional provider calibration multiplier
are not prerequisites for initial activation: the versioned lead-time policy
already limits forecast influence to 80%, 60%, 40%, or 15% and returns missing
coverage to climatology.

Forecast rows remain prediction evidence. They never enter historical archive
or derived climatology, and snow depth must not be interpreted as operational
snow coverage, open-piste ratio, or open terrain.

## Consequences

Benefits:

- Search latency is independent from provider availability and uses one bounded
  repository operation.
- Atomic heads make the serving run explicit and avoid incomplete publication.
- Immutable issue versions support audit, reproducibility, ensemble handling,
  and later calibration.
- The storage model represents provider/model/issue/valid-time semantics
  directly rather than overloading observations.
- Postgres is sufficient at current catalog and 30-day serving scale without a
  second consistency boundary.
- Failed refreshes degrade to older capped evidence or climatology instead of
  failing search.

Costs and constraints:

- New tables, indexes, repository contracts, refresh state transitions, and
  retention maintenance are required.
- Provider/model eligibility and lead-time influence remain versioned
  product/scientific policy rather than being solved by the schema.
- Immutable history uses reviewed tiered retention: every complete run for 45
  days, one canonical daily run per source through two years, and one canonical
  weekly run through five years. Current head-referenced runs are never purged.
- Per-area heads make partial publication safe but add explicit state that must
  be monitored and repaired if inconsistent.
- A future cache must preserve atomic-head and freshness semantics.

## Alternatives Considered

- **Keep only the latest normalized conditions snapshot.** Operationally
  simple, but it cannot align evidence to requested dates or support issue-time
  calibration.
- **Reuse `raw_weather_history` and overwrite one forecast row per valid day.**
  Avoids new tables, but loses issue versions and conflates observation-oriented
  uniqueness with forecast runs and ensembles.
- **Store versioned rows but query the latest issue with an aggregate.** Avoids
  head state, but puts growing-history selection into the request path and makes
  partial-run publication harder to express.
- **Fetch the provider during `/api/search`.** Always current in theory, but
  makes latency, availability, rate limits, and cost user-facing dependencies.
- **Store only latest rows in a dedicated table.** Fast to serve, but removes
  the audit and calibration evidence needed to assign scientifically defensible
  confidence.
- **Use ECMWF EC46 weekly rows for days 16 through 30.** This provides a
  subseasonal product but would require mixed daily/weekly serving semantics.
  Daily NOAA GEFS ensemble means preserve exact requested-date lookup while the
  15% long-range cap keeps their coarse-grid precision in proportion.
- **Key heads only by generic forecast kind.** Simpler, but one ensemble head
  cannot safely publish both the preferred short-range and extended-range
  sources needed by the accepted routing policy.
- **Use Redis as the primary serving store.** Fast, but creates an unnecessary
  persistence/invalidation boundary before Postgres query cost is shown to be a
  problem.

## Revisit When

- Measured bulk-query or decoding latency makes Postgres serving a material
  part of search latency.
- Catalog scale or forecast resolution makes the daily serving set
  substantially larger.
- Calibration requires a warehouse or object-store history beyond bounded
  Postgres samples.
- Multiple providers need probabilistic model blending rather than the current
  deterministic preferred-source/fallback selection.
- Operational snowpack or open-terrain prediction becomes an active model with
  separate input and publication requirements.
