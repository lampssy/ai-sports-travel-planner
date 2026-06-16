# Snow Evidence Climatology Design

## Summary

Build Snowcast's ski-planning evidence model around daily historical archive
data, derived climatology features, and horizon-aware forecast assistance.

The raw `raw_weather_history` table remains the auditable evidence source.
Search should move toward a compact derived climatology layer so Snowcast can
scale from the current resort set to roughly 100-200 ski areas without scanning
large raw-weather windows on every request.

## Goals

- Support a 1991-present daily historical weather backfill for each ski area and
  elevation band.
- Add a derived climatology table that stores WMO-style 30-year baseline
  features and recent-winter adjustment features.
- Keep search performant by preferring derived climatology evidence at request
  time, with raw-weather fallback while derived data is missing.
- Optimize the historical backfill writer before a large rebuild by replacing
  one-row, one-connection upserts with batch writes.
- Document the scientific method clearly enough that ranking behavior is
  defensible, maintainable, and transparent.
- Keep user-facing method names understandable without making the product feel
  academic.

## Non-Goals

- Do not implement a physical Crocus, SNOWPACK, or S2M snowpack simulation in
  this phase.
- Do not store hourly historical archives for the core planner.
- Do not change weather provider selection in this phase.
- Do not make official open-piste status part of this climatology model.
- Do not remove raw-history fallback until the derived layer is proven in
  production.

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Technical | Keep raw archive rows as audit source and add a derived climatology read model. | This changes persistence and request-path query shape before a large historical rebuild. | Raw-only is simpler but expensive on search; DB-canonical derived rows add rebuild responsibility but keep request reads small; external analytics storage is heavier than current scale needs. | Use raw archive plus derived Postgres climatology. | Good fit for 100-200 ski areas; requires explicit rebuild after archive/model changes. | `docs/architecture/adr/0003-derived-snow-climatology.md` |
| Product / Domain | Use empirical climatology rather than physical snowpack simulation. | User trust depends on honest scientific claims. | Physical models are stronger but require more data/validation/ops; empirical climatology is defensible for booking decision support. | Implement empirical Snowcast climatology now; document Crocus/SNOWPACK/S2M as references only. | Avoids overclaiming while keeping future upgrade path visible. | `docs/snow-evidence-model.md` |
| Mixed | Prefer `normal_30y` with `recent_15y` adjustment. | This decides how much recent climate drift affects recommendations. | 30-year only is stable but slower to reflect warming; 15-year only is responsive but noisier; blended keeps stable baseline with controlled recent signal. | Use 30-year normal as primary baseline and a small recent-baseline adjustment. | Reasonable v1 policy; keep weights centralized in `planning_policy.py`. | `docs/planning-model.md` |
| Technical | Search should preload climatology first and load raw archive only when climatology is missing. | This directly affects latency and DB load on broad searches. | Always loading raw is robust but expensive; climatology-first is faster but needs fallback and rebuild discipline. | Use climatology-first with raw/snapshot/heuristic fallback. | Correct request-path direction; verify with fake repos now and real data after backfill. | `docs/architecture/adr/0003-derived-snow-climatology.md` |
| Technical | Use bootstrap-managed schema/indexes for this phase instead of adding a migration framework now. | New tables/indexes affect deploy behavior. | Formal migrations are safer long term; bootstrap matches current repo convention and keeps scope contained. | Use existing bootstrap path for now. | Acceptable for current project stage; revisit before larger production schema operations. | `docs/architecture/adr/0003-derived-snow-climatology.md` |
| Ops | Batch historical writes before full 1991-present backfill. | Full rebuild volume will make one-row connection churn too slow and fragile. | Per-row writes are simple but inefficient; chunk-level batch upserts reduce connection overhead while preserving retry chunks. | Use repository-level batch upserts per fetched chunk. | Good low-risk optimization; deeper copy/bulk loading can wait for observed need. | `docs/engineering-notes.md` |

## Scientific Model

Snowcast will use an empirical snow climatology model:

- WMO-style 30-year climate-normal baseline for typical historical conditions.
- Recent 15-winter comparison to reflect current-climate drift.
- Ski-reliability threshold probabilities inspired by ski-tourism literature,
  especially snow-depth thresholds such as 30 cm and 50 cm.
- Horizon-weighted forecast assistance for near-term trips.
- Snowpack-model-inspired indicators from available weather variables:
  snow depth, snowfall, rain risk, freeze-thaw risk, wind, and elevation band.

Snowcast should document Crocus, SNOWPACK, and S2M as reference models for how
operational snow systems reason about snowpack drivers, but should not claim to
run those models.

## Data Model

Add a derived table named `ski_area_snow_climatology_daily`.

Recommended columns:

- `ski_area_id`
- `elevation_band`
- `month`
- `day`
- `baseline_period`
- `baseline_start_year`
- `baseline_end_year`
- `evidence_seasons`
- `latest_archive_year`
- `snow_depth_cm_p25`
- `snow_depth_cm_p50`
- `snow_depth_cm_p75`
- `prob_snow_depth_ge_30cm`
- `prob_snow_depth_ge_50cm`
- `avg_daily_snowfall_cm`
- `prob_rain_risk`
- `prob_freeze_thaw`
- `avg_max_temperature_c`
- `avg_wind_gust_kmh`
- `source_model`
- `computed_at`

Unique key:

- `(ski_area_id, elevation_band, month, day, baseline_period, source_model)`

Indexes:

- `(ski_area_id, elevation_band, baseline_period, month, day)`
- optional covering index for broad searches after real query plans are
  measured.

Initial baseline periods:

- `normal_30y`: latest 30 complete winter seasons available.
- `recent_15y`: latest 15 complete winter seasons available.

## Backfill Optimization

Before running a 1991-present rebuild, `backfill_historical_weather` should use
batch upserts:

- fetch one provider chunk per ski area/elevation band as it does today
- normalize the response into daily observations
- upsert the full chunk in one connection/transaction
- keep the existing chunk-level retry behavior
- report inserted/updated row counts per chunk

This keeps the large backfill from opening a database connection per daily row.

## Climatology Rebuild

Add a command or module that rebuilds derived climatology from
`raw_weather_history`.

Behavior:

- read only `record_type = 'archive'`
- calculate baselines per ski area, elevation band, and month/day
- ignore implausible snow-depth display outliers above the existing 8 m cap for
  display-style metrics
- count unique years/seasons as evidence, not raw rows
- write derived rows idempotently with upserts
- allow targeted rebuilds for selected ski areas
- produce summary logs for rows read, rows written, and weak-coverage groups

The climatology rebuild should be safe to run after every historical backfill or
catalog coordinate/elevation change.

## Planning Integration

The planner should prefer derived climatology when it can answer the request:

1. Resolve the travel window.
2. Load derived climatology rows for matching month/day values and relevant
   elevation bands.
3. Aggregate the derived rows into the same planning concepts currently built
   from raw archive windows.
4. Blend with current forecast according to the existing horizon policy.
5. Fall back to raw archive windows if derived climatology is unavailable.
6. Fall back to seasonality/elevation heuristics only when archive evidence is
   weak or absent.

The request/response contract can remain compatible in this phase. Existing
fields such as `planning_evidence_count`, `planning_weather_metrics`, and
`planning_provenance.evidence_profile` should continue to work.

## Evidence Quality Policy

Evidence quality should be based on available unique seasons:

- `climate_normal_grade`: 25-30+ seasons, if added as a future public profile.
- `archive_backed`: at least 15 seasons.
- `limited_archive`: 8-14 seasons, if added as a future internal/public profile.
- `fallback_heavy`: fewer than 8 seasons or no reliable climatology/archive
  evidence.

For this implementation, the public enum can remain
`forecast_assisted | archive_backed | fallback_heavy` unless expanding the API
is clearly worth it. Internally, the planner may track finer coverage tiers.

## User-Facing Language

Default UI and API summaries should use plain labels:

- "30-year archive baseline"
- "recent-winter adjusted"
- "forecast-assisted"
- "archive-backed"
- "limited evidence"

Avoid exposing Crocus, SNOWPACK, S2M, or WMO names in normal result cards.

Methodology docs and deeper evidence views may mention:

- WMO climate normals
- ski-industry snow-depth thresholds
- ERA5-Land/Open-Meteo historical/reanalysis source
- Crocus/SNOWPACK/S2M as reference models, not implemented models

## Documentation

Add or update:

- `docs/snow-evidence-model.md`: canonical method document.
- `docs/planning-model.md`: link to the snow evidence model and describe the
  derived climatology layer.
- `docs/engineering-notes.md`: concise note on the derived climatology pattern.
- `PROJECT.md`: mention the snow evidence/climatology implementation as the
  next planning-model/data-platform follow-up.
- `docs/architecture/adr/`: add an ADR for "raw archive plus derived
  climatology" because this changes persistence and request-path query shape.

## Rollout

Recommended rollout order:

1. Add schema and repositories for climatology.
2. Add batch raw-history upsert.
3. Add climatology rebuild command.
4. Keep search using raw history while tests prove the derived layer.
5. Integrate derived climatology into planning with raw fallback.
6. Run a small backfill/rebuild smoke test for one or two ski areas.
7. Run the full 1991-present archive rebuild only after coordinates/elevation
   bands are locked.
8. Rebuild climatology after the full archive rebuild.

## Testing

Unit tests:

- batch upsert writes multiple raw observations idempotently
- climatology rebuild computes p25/p50/p75 snow depth
- climatology rebuild computes 30 cm and 50 cm probabilities
- climatology rebuild computes rain and freeze-thaw probabilities
- evidence season counts use unique years/seasons
- weak coverage produces fallback-heavy or limited evidence behavior

Planner tests:

- derived climatology is preferred when available
- raw archive fallback is used when derived rows are absent
- forecast-assisted trips still use current forecast horizon weights
- far-future trips remain archive/climatology dominated
- recent 15-year evidence can be exposed separately from 30-year baseline

Repository/API tests:

- schema bootstrap creates climatology table and indexes
- targeted rebuild writes only selected ski areas
- existing search response shape remains backward compatible

Performance checks:

- compare broad search with raw-history path versus derived-climatology path
- inspect `EXPLAIN ANALYZE` for climatology lookup once real data exists
- measure backfill chunk duration before and after batch upsert

## Open Assumptions

- Daily historical data is the right granularity for v1 planning.
- 30-year and 15-year baselines are enough for the first derived model.
- The public evidence enum can stay unchanged for the first implementation.
- Search should retain raw-history fallback until derived climatology is proven
  with real backfilled data.
