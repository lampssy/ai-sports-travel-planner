# Snow Evidence Climatology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Snowcast's daily historical archive plus derived snow climatology layer, and use it as the preferred evidence source for ski planning.

**Architecture:** `raw_weather_history` remains the auditable source table. A new `ski_area_snow_climatology_daily` table stores compact baseline features for `normal_30y` and `recent_15y`; search/planning prefers those rows and falls back to raw archive windows while climatology is missing. Historical backfill moves from one-row connection churn to chunk-level batch upserts before a large 1991-present rebuild.

**Tech Stack:** FastAPI backend, Python domain services, psycopg/Postgres, Neon-compatible schema bootstrap, pytest, ruff.

---

## File Structure

- Create `app/data/rebuild_snow_climatology.py`: command/module that derives climatology rows from raw archive rows.
- Modify `app/domain/models.py`: add `SnowClimatologyBaselinePeriod` and `SnowClimatologyDaily`.
- Modify `app/data/database.py`: create `ski_area_snow_climatology_daily` and indexes.
- Modify `app/data/repositories.py`: add batch raw-history upsert and `SnowClimatologyRepository`.
- Modify `app/data/backfill_historical_weather.py`: use batch raw-history upsert per fetched chunk.
- Modify `app/domain/planning.py`: accept climatology rows, prefer climatology planning values, keep raw fallback.
- Modify `app/domain/search_service.py`: preload climatology and load raw archive rows only for missing climatology evidence.
- Create `docs/snow-evidence-model.md`: canonical scientific/industry method explanation.
- Create `docs/architecture/adr/0003-derived-snow-climatology.md`: persistence/request-path ADR.
- Modify `docs/planning-model.md`, `docs/engineering-notes.md`, `PROJECT.md`: link and summarize the new model.
- Tests:
  - `tests/test_repository.py`
  - `tests/test_open_meteo.py`
  - `tests/test_services.py`
  - new `tests/test_snow_climatology.py`

## Task 1: Schema, Domain Model, And Repository

**Files:**
- Modify: `app/domain/models.py`
- Modify: `app/data/database.py`
- Modify: `app/data/repositories.py`
- Test: `tests/test_repository.py`

- [ ] **Step 1: Write schema/model tests**

Add tests proving bootstrap creates the climatology table and repository upserts/listing work:

```python
def test_bootstrap_database_creates_snow_climatology_table() -> None:
    bootstrap_database()
    with connect() as connection:
        columns = {
            row["column_name"]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'ski_area_snow_climatology_daily'
                """
            ).fetchall()
        }
    assert {"ski_area_id", "baseline_period", "month", "day", "snow_depth_cm_p50"} <= columns


def test_snow_climatology_repository_upserts_and_lists_window_rows() -> None:
    repository = SnowClimatologyRepository()
    repository.upsert_daily_rows((
        _snow_climatology_row(ski_area_id="tignes-ski-area", month=3, day=10),
        _snow_climatology_row(ski_area_id="tignes-ski-area", month=3, day=11),
    ))
    grouped = repository.list_daily_rows_for_resorts_window(
        ("tignes-ski-area",),
        elevation_bands=("mid",),
        baseline_periods=("normal_30y", "recent_15y"),
        trip_start_date=date(2027, 3, 10),
        trip_end_date=date(2027, 3, 11),
    )
    assert len(grouped[("tignes-ski-area", "mid", "normal_30y")]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_repository.py::test_bootstrap_database_creates_snow_climatology_table tests/test_repository.py::test_snow_climatology_repository_upserts_and_lists_window_rows -q
```

Expected: fail because `SnowClimatologyRepository` and the table do not exist.

- [ ] **Step 3: Add model and repository implementation**

Add `SnowClimatologyDaily` with fields from the design spec plus planner-ready `avg_snow_confidence_score`, `avg_conditions_score`, and `elevation_m`.

Add repository methods:

```python
class SnowClimatologyRepository:
    def upsert_daily_rows(self, rows: tuple[SnowClimatologyDaily, ...]) -> int: ...
    def delete_rows_for_ski_area(self, *, ski_area_id: str, source_model: str | None = None) -> int: ...
    def list_daily_rows_for_resorts_window(... ) -> dict[tuple[str, WeatherElevationBand, SnowClimatologyBaselinePeriod], tuple[SnowClimatologyDaily, ...]]: ...
```

- [ ] **Step 4: Run focused repository tests**

Run the same command from Step 2. Expected: pass.

## Task 2: Batch Raw-History Upsert

**Files:**
- Modify: `app/data/repositories.py`
- Modify: `app/data/backfill_historical_weather.py`
- Test: `tests/test_repository.py`, `tests/test_open_meteo.py`

- [ ] **Step 1: Write failing batch-upsert test**

Add:

```python
def test_raw_weather_history_batch_upsert_writes_multiple_rows_idempotently() -> None:
    repository = RawWeatherHistoryRepository()
    rows = (
        _raw_weather_observation(elevation_band="mid", elevation_m=2500, observed_on="2024-03-05", snow_depth_m=1.3),
        _raw_weather_observation(elevation_band="mid", elevation_m=2500, observed_on="2024-03-06", snow_depth_m=1.4),
    )
    assert repository.upsert_observations(rows) == 2
    assert repository.upsert_observations(rows) == 2
    stored = repository.list_observations_for_resort("tignes-ski-area", elevation_band="mid")
    assert [row.observed_on for row in stored] == ["2024-03-05", "2024-03-06"]
```

- [ ] **Step 2: Implement batch upsert**

Add `RawWeatherHistoryRepository.upsert_observations()` using one connection and `executemany` with the existing `ON CONFLICT` statement.

- [ ] **Step 3: Update backfill command**

Replace:

```python
for observation in observations:
    raw_history_repository.upsert_observation(observation)
```

with:

```python
stored_rows = raw_history_repository.upsert_observations(tuple(observations))
result.inserted_or_updated += stored_rows
```

- [ ] **Step 4: Run focused tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_repository.py::test_raw_weather_history_batch_upsert_writes_multiple_rows_idempotently tests/test_open_meteo.py::test_backfill_historical_weather_stores_daily_raw_rows_idempotently -q
```

Expected: pass.

## Task 3: Climatology Rebuild Module

**Files:**
- Create: `app/data/rebuild_snow_climatology.py`
- Modify: `app/data/repositories.py`
- Test: `tests/test_snow_climatology.py`

- [ ] **Step 1: Write climatology calculation tests**

Cover percentile, threshold probability, rain risk, freeze-thaw risk, and unique evidence years:

```python
def test_rebuild_snow_climatology_computes_daily_baseline_features() -> None:
    raw_repository = RawWeatherHistoryRepository()
    climatology_repository = SnowClimatologyRepository()
    raw_repository.upsert_observations((
        _raw_weather_observation("2020-03-10", snow_depth_m=0.2, rain_sum_mm=0, min_temp=-5, max_temp=-1),
        _raw_weather_observation("2021-03-10", snow_depth_m=0.4, rain_sum_mm=2, min_temp=-2, max_temp=2),
        _raw_weather_observation("2022-03-10", snow_depth_m=0.8, rain_sum_mm=0, min_temp=-6, max_temp=-2),
    ))
    result = rebuild_snow_climatology(targets=("tignes",), baseline_end_year=2022)
    rows = climatology_repository.list_daily_rows_for_resorts_window(
        ("tignes-ski-area",), elevation_bands=("mid",), baseline_periods=("normal_30y",), trip_start_date=date(2027, 3, 10), trip_end_date=date(2027, 3, 10)
    )
    row = rows[("tignes-ski-area", "mid", "normal_30y")][0]
    assert row.evidence_seasons == 3
    assert row.prob_snow_depth_ge_30cm == pytest.approx(2 / 3)
    assert row.prob_rain_risk == pytest.approx(1 / 3)
    assert row.prob_freeze_thaw == pytest.approx(1 / 3)
```

- [ ] **Step 2: Implement rebuild module**

Implement:

```python
def rebuild_snow_climatology(
    *,
    database_url: str | None = None,
    targets: tuple[str, ...] | None = None,
    baseline_end_year: int | None = None,
    source_model: str = "snowcast_empirical_v1",
) -> SnowClimatologyRebuildResult:
    ...
```

Use latest available archive year when `baseline_end_year` is absent. Generate `normal_30y` from `end_year - 29` through `end_year`, and `recent_15y` from `end_year - 14` through `end_year`.

- [ ] **Step 3: Add CLI entrypoint**

Support:

```bash
uv run --no-config python -m app.data.rebuild_snow_climatology --target tignes --baseline-end-year 2025
```

- [ ] **Step 4: Run climatology tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_snow_climatology.py -q
```

Expected: pass.

## Task 4: Planning Integration

**Files:**
- Modify: `app/domain/planning.py`
- Modify: `app/domain/search_service.py`
- Test: `tests/test_services.py`

- [ ] **Step 1: Write planner tests**

Add tests:

```python
def test_planning_prefers_snow_climatology_when_available() -> None:
    assessment = derive_planning_assessment(
        resort=tignes_ski_area,
        travel_month=3,
        snapshots=(),
        raw_weather_observations=weak_raw_rows,
        snow_climatology_rows=strong_climatology_rows,
    )
    assert assessment.evidence_source == "snow_climatology"
    assert assessment.evidence_count == 30
```

```python
def test_planning_falls_back_to_raw_history_when_climatology_is_missing() -> None:
    assessment = derive_planning_assessment(
        resort=tignes_ski_area,
        travel_month=3,
        snapshots=(),
        raw_weather_observations=raw_rows,
        snow_climatology_rows=(),
    )
    assert assessment.evidence_source == "raw_history"
```

- [ ] **Step 2: Add planning support**

Extend `derive_planning_assessment()` with:

```python
snow_climatology_rows: tuple[SnowClimatologyDaily, ...] = ()
```

Prefer `normal_30y` rows, expose `evidence_count` from `evidence_seasons`, and retain forecast-assisted behavior when current forecast has non-zero weight.

- [ ] **Step 3: Add search preload**

Add `SnowClimatologyRepository` to the search path, preload rows by candidate ski area/window, and load raw weather only for ski areas where no climatology band has usable rows.

- [ ] **Step 4: Run focused service tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_services.py::test_planning_prefers_snow_climatology_when_available tests/test_services.py::test_planning_falls_back_to_raw_history_when_climatology_is_missing -q
```

Expected: pass.

## Task 5: Docs And ADR

**Files:**
- Create: `docs/snow-evidence-model.md`
- Create: `docs/architecture/adr/0003-derived-snow-climatology.md`
- Modify: `docs/planning-model.md`
- Modify: `docs/engineering-notes.md`
- Modify: `PROJECT.md`

- [ ] **Step 1: Write method doc**

Document:

- WMO-style 30-year baseline
- recent 15-winter adjustment
- 30 cm / 50 cm snow-depth threshold probabilities
- horizon-weighted forecast assistance
- Crocus/SNOWPACK/S2M as reference models only
- user-facing language policy

- [ ] **Step 2: Write ADR**

Decision: raw archive table plus derived climatology table, not raw-only request path and not physical snowpack modeling.

- [ ] **Step 3: Update planning model and project notes**

Link `docs/snow-evidence-model.md` from `docs/planning-model.md`, add an engineering note, and record the follow-up in `PROJECT.md`.

## Task 6: Verification

**Files:**
- No code changes expected.

- [ ] **Step 1: Run focused test suite**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_repository.py tests/test_open_meteo.py tests/test_snow_climatology.py tests/test_services.py tests/test_planning.py -q
```

- [ ] **Step 2: Run lint**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
```

- [ ] **Step 3: Run smoke commands**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.backfill_historical_weather --target tignes --start-date 2024-03-01 --end-date 2024-03-10 --chunk-days 10 --rebuild
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.rebuild_snow_climatology --target tignes --baseline-end-year 2024
```

Expected: backfill stores daily rows in batch; climatology rebuild writes rows and logs weak coverage.

## Self-Review

Spec coverage:

- Derived climatology schema: Task 1.
- Batch backfill optimization: Task 2.
- Climatology rebuild command: Task 3.
- Planner/search integration and raw fallback: Task 4.
- Scientific documentation and ADR: Task 5.
- Verification: Task 6.

No placeholders remain. The implementation intentionally keeps the public evidence enum unchanged while allowing internal coverage tiers later.
