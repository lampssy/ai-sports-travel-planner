# Search Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/api/search` fast enough for interactive use by removing repeated remote DB round trips from weather-history and travel-effort calculation while preserving current ranking behavior.

**Architecture:** Keep the public `/api/search` contract stable. Optimize inside the backend request path by adding request-scoped caches, a batch raw-weather repository method, and a deterministic travel-effort fast path that does not persist approximate routes during search. Defer connection pooling unless measured timings remain unacceptable after reducing query count.

**Tech Stack:** FastAPI, Pydantic, psycopg 3, pytest, existing Postgres-backed repositories, existing React frontend.

---

## Current Problem Summary

Observed local timings against the current remote Neon-backed database:

- `/api/parse-query` for a normal trip brief: about `1.2s`.
- `/api/search` with country + month and no origin: about `18s`.
- `/api/search` with country + month + origin: up to about `40s`.

The slow path is not primarily frontend rendering. The backend search path does too much remote database work:

- `search_resorts()` calls raw weather history inside nested `resort -> stay_base -> ski_area` loops.
- `_list_raw_weather_observations()` can call `list_observations_for_resort()` up to three times per ski area (`mid`, `upper`, `base`).
- Each repository call opens a fresh psycopg connection.
- Each raw-weather call loads a full elevation-band history, then filters the selected travel window in Python.
- Travel effort currently calls the persistent travel cache for each matching destination, even though the current route provider is deterministic `approximate_haversine_v2`.

## Target Behavior

- Country + month search should usually return in under `3s` against the remote DB.
- Country + month + origin search should usually return in under `4s` while the route provider is still deterministic fallback.
- Search should not change ranking, scoring, response schema, evidence wording, or UI behavior except for becoming faster.
- Existing maintenance jobs and full-history repository callers should keep working.
- No dependency changes unless the post-fix timing still requires `psycopg-pool`; if so, stop and ask before adding the package.

## Files

- Modify: `app/domain/search_service.py`
  - Add request-scoped raw-weather cache.
  - Preload raw weather for candidate ski areas using a batch repository method when available.
  - Use an in-memory travel cache for deterministic fallback routes in the default search path.
- Modify: `app/data/repositories.py`
  - Add batch raw-weather history loading.
  - Preserve `list_observations_for_resort()` for existing callers.
- Modify: `app/domain/travel.py`
  - Add a search-safe deterministic travel helper or request-cache wrapper without changing existing `assess_travel_effort()` behavior.
- Modify: `tests/test_services.py`
  - Add query-count style regression tests around `search_resorts()`.
- Modify: `tests/test_repository.py`
  - Add repository tests for the batch raw-weather method.
- Modify: `tests/test_travel.py`
  - Add tests for request-local deterministic travel cache behavior if a wrapper/helper is introduced.
- Modify: `tests/test_api.py`
  - Add one API-level regression proving origin search still returns travel fields.
- Modify: `docs/engineering-notes.md`
  - Document the search request performance model.
- Modify: `PROJECT.md`
  - Add a concise Sprint 34 follow-up note when implementation is complete.

---

## Task 1: Add Search Query-Count Regression Tests

**Files:**
- Modify: `tests/test_services.py`

- [ ] **Step 1: Add local test helpers near the existing search-service helper classes**

Add these helpers below `_multi_stay_base_tignes()` or near the existing planning tests:

```python
class StaticConditionsProvider:
    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions:
        return ResortConditions(
            resort_name=resort_name,
            snow_confidence_score=0.7,
            snow_confidence_label="good",
            availability_status="open",
            weather_summary="Good current signal.",
            conditions_score=0.7,
            updated_at="2026-05-06T21:43:00+00:00",
            source="test",
        )


class EmptyConditionHistoryRepository:
    def list_snapshots_for_resort(self, resort_id: str) -> tuple:
        return ()


class CountingRawHistoryRepository:
    def __init__(self, observations: tuple[RawWeatherObservation, ...]) -> None:
        self.observations = observations
        self.single_calls: list[tuple[str, str | None]] = []
        self.batch_calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def list_observations_for_resort(
        self,
        resort_id: str,
        *,
        elevation_band: str | None = None,
    ) -> tuple[RawWeatherObservation, ...]:
        self.single_calls.append((resort_id, elevation_band))
        if elevation_band != "mid":
            return ()
        return tuple(
            observation
            for observation in self.observations
            if observation.resort_id == resort_id
            and observation.elevation_band == elevation_band
        )

    def list_observations_for_resorts(
        self,
        resort_ids: tuple[str, ...],
        *,
        elevation_bands: tuple[str, ...],
    ) -> dict[tuple[str, str], tuple[RawWeatherObservation, ...]]:
        self.batch_calls.append((resort_ids, elevation_bands))
        grouped: dict[tuple[str, str], list[RawWeatherObservation]] = {
            (resort_id, elevation_band): []
            for resort_id in resort_ids
            for elevation_band in elevation_bands
        }
        for observation in self.observations:
            key = (observation.resort_id, observation.elevation_band)
            if key in grouped:
                grouped[key].append(observation)
        return {key: tuple(value) for key, value in grouped.items()}
```

- [ ] **Step 2: Add a failing test for request-scoped raw-weather reuse**

Add this test near the existing raw-weather planning tests:

```python
def test_search_resorts_reuses_raw_weather_across_matching_stay_bases() -> None:
    resort = _multi_stay_base_tignes()
    ski_area = resort.ski_areas[0]
    raw_repository = CountingRawHistoryRepository(
        (
            _raw_weather_observation(
                resort_id=ski_area.ski_area_id,
                resort_name=ski_area.name,
                elevation_band="mid",
                observed_on="2024-03-05",
                snowfall_cm=8,
                snow_depth_m=1.2,
                max_temp_c=-3,
                gust_kmh=22,
            ),
            _raw_weather_observation(
                resort_id=ski_area.ski_area_id,
                resort_name=ski_area.name,
                elevation_band="mid",
                observed_on="2025-03-07",
                snowfall_cm=7,
                snow_depth_m=1.1,
                max_temp_c=-2,
                gust_kmh=25,
            ),
        )
    )

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=EmptyConditionHistoryRepository(),
        raw_weather_history_repository=raw_repository,
    )

    assert results
    assert raw_repository.single_calls == []
    assert raw_repository.batch_calls == [
        ((ski_area.ski_area_id,), ("mid", "upper", "base"))
    ]
```

Expected initial result: FAIL because `search_resorts()` does not use the batch method yet and calls the single method once per matching stay base.

- [ ] **Step 3: Add a fallback test for repositories without the batch method**

Add this test to preserve compatibility with simple test doubles and any future lightweight repositories:

```python
def test_search_resorts_single_repository_fallback_still_caches_per_request() -> None:
    resort = _multi_stay_base_tignes()
    ski_area = resort.ski_areas[0]

    class SingleOnlyRawHistoryRepository:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str | None]] = []

        def list_observations_for_resort(
            self,
            resort_id: str,
            *,
            elevation_band: str | None = None,
        ) -> tuple[RawWeatherObservation, ...]:
            self.calls.append((resort_id, elevation_band))
            if resort_id != ski_area.ski_area_id or elevation_band != "mid":
                return ()
            return (
                _raw_weather_observation(
                    resort_id=ski_area.ski_area_id,
                    resort_name=ski_area.name,
                    elevation_band="mid",
                    observed_on="2024-03-05",
                    snowfall_cm=8,
                    snow_depth_m=1.2,
                    max_temp_c=-3,
                    gust_kmh=22,
                ),
            )

    raw_repository = SingleOnlyRawHistoryRepository()

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=EmptyConditionHistoryRepository(),
        raw_weather_history_repository=raw_repository,
    )

    assert results
    assert raw_repository.calls == [(ski_area.ski_area_id, "mid")]
```

Expected initial result: FAIL because current code calls the single method once per matching stay base.

- [ ] **Step 4: Run the failing tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_services.py::test_search_resorts_reuses_raw_weather_across_matching_stay_bases tests/test_services.py::test_search_resorts_single_repository_fallback_still_caches_per_request -q
```

Expected: both tests fail before implementation.

---

## Task 2: Add Request-Scoped Raw Weather Cache And Batch Preload

**Files:**
- Modify: `app/domain/search_service.py`
- Test: `tests/test_services.py`

- [ ] **Step 1: Add cache type aliases near module constants**

Add below `MIN_ALTERNATIVE_SCORE_DELTA`:

```python
RAW_WEATHER_BANDS: tuple[str, ...] = ("mid", "upper", "base")
RawWeatherCache = dict[tuple[str, str], tuple]
```

- [ ] **Step 2: Add a batch preload helper**

Add this helper above `_list_raw_weather_observations()`:

```python
def _preload_raw_weather_observations(
    *,
    raw_history_repository,
    resorts: tuple[Destination, ...],
) -> RawWeatherCache:
    resort_ids = tuple(
        dict.fromkeys(
            ski_area.ski_area_id
            for resort in resorts
            for ski_area in resort.ski_areas
        )
    )
    cache: RawWeatherCache = {}
    if not resort_ids:
        return cache

    batch_loader = getattr(
        raw_history_repository,
        "list_observations_for_resorts",
        None,
    )
    if batch_loader is None:
        return cache

    grouped = batch_loader(
        resort_ids,
        elevation_bands=RAW_WEATHER_BANDS,
    )
    for resort_id in resort_ids:
        for elevation_band in RAW_WEATHER_BANDS:
            cache[(resort_id, elevation_band)] = grouped.get(
                (resort_id, elevation_band),
                (),
            )
    return cache
```

- [ ] **Step 3: Add a single-load cache helper**

Add this helper below `_preload_raw_weather_observations()`:

```python
def _cached_raw_weather_observations_for_resort(
    *,
    raw_history_repository,
    raw_weather_cache: RawWeatherCache,
    resort_id: str,
    elevation_band: str,
) -> tuple:
    key = (resort_id, elevation_band)
    if key not in raw_weather_cache:
        raw_weather_cache[key] = raw_history_repository.list_observations_for_resort(
            resort_id,
            elevation_band=elevation_band,
        )
    return raw_weather_cache[key]
```

- [ ] **Step 4: Preload only country-matching resorts**

In `search_resorts()`, replace:

```python
active_resorts = resorts or get_resort_repository().list_resorts()
```

with:

```python
active_resorts = resorts or get_resort_repository().list_resorts()
candidate_resorts = tuple(
    resort for resort in active_resorts if resort.country.lower() == normalized_location
)
```

Then add after `active_raw_history_repository`:

```python
raw_weather_cache: RawWeatherCache = {}
if filters.travel_month is not None or (
    filters.trip_start_date is not None and filters.trip_end_date is not None
):
    raw_weather_cache = _preload_raw_weather_observations(
        raw_history_repository=active_raw_history_repository,
        resorts=candidate_resorts,
    )
```

Then change:

```python
for resort in active_resorts:
```

to:

```python
for resort in candidate_resorts:
```

Remove the now-redundant country check inside the loop:

```python
if resort.country.lower() != normalized_location:
    continue
```

- [ ] **Step 5: Thread the cache through raw-weather selection**

Change `_list_raw_weather_observations()` signature to include:

```python
    raw_weather_cache: RawWeatherCache,
```

Change the call site in `search_resorts()` to pass:

```python
raw_weather_cache=raw_weather_cache,
```

Change `_list_raw_weather_observations_for_band()` signature to include:

```python
    raw_weather_cache: RawWeatherCache,
```

Use `_cached_raw_weather_observations_for_resort()` instead of calling the repository directly:

```python
observations = _cached_raw_weather_observations_for_resort(
    raw_history_repository=raw_history_repository,
    raw_weather_cache=raw_weather_cache,
    resort_id=ski_area.ski_area_id,
    elevation_band=elevation_band,
)
if observations or ski_area.ski_area_id == destination.resort_id:
    return observations
return _cached_raw_weather_observations_for_resort(
    raw_history_repository=raw_history_repository,
    raw_weather_cache=raw_weather_cache,
    resort_id=destination.resort_id,
    elevation_band=elevation_band,
)
```

- [ ] **Step 6: Run the search-service regression tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_services.py::test_search_resorts_reuses_raw_weather_across_matching_stay_bases tests/test_services.py::test_search_resorts_single_repository_fallback_still_caches_per_request -q
```

Expected: PASS.

---

## Task 3: Add Batch Raw Weather Repository Loading

**Files:**
- Modify: `app/data/repositories.py`
- Modify: `tests/test_repository.py`
- Test: `tests/test_repository.py`

- [ ] **Step 1: Add a repository test for batch grouping**

Add this test near `test_raw_weather_history_upsert_is_elevation_band_aware()`:

```python
def test_raw_weather_history_lists_multiple_resorts_by_band() -> None:
    repository = RawWeatherHistoryRepository()
    repository.upsert_observation(
        _raw_weather_observation(
            resort_id="tignes-ski-area",
            resort_name="Tignes",
            elevation_band="mid",
            elevation_m=2500,
            observed_on="2024-03-05",
            snow_depth_m=1.3,
        )
    )
    repository.upsert_observation(
        _raw_weather_observation(
            resort_id="cervinia-ski-area",
            resort_name="Cervinia",
            elevation_band="upper",
            elevation_m=3300,
            observed_on="2024-03-05",
            snow_depth_m=2.2,
        )
    )

    grouped = repository.list_observations_for_resorts(
        ("tignes-ski-area", "cervinia-ski-area"),
        elevation_bands=("mid", "upper", "base"),
    )

    assert grouped[("tignes-ski-area", "mid")][0].snow_depth_m == 1.3
    assert grouped[("cervinia-ski-area", "upper")][0].snow_depth_m == 2.2
    assert grouped[("tignes-ski-area", "upper")] == ()
    assert grouped[("cervinia-ski-area", "base")] == ()
```

Expected initial result: FAIL because the method does not exist.

- [ ] **Step 2: Extract the raw-weather SELECT list**

In `app/data/repositories.py`, add this module-level constant near other helper functions:

```python
RAW_WEATHER_SELECT_COLUMNS = """
    resort_id, resort_name, observed_on::text AS observed_on,
    elevation_band, elevation_m, observed_at, snowfall_cm,
    snow_depth_m, precipitation_sum_mm, rain_sum_mm,
    precipitation_hours, snowfall_water_equivalent_sum_mm,
    temperature_2m_max_c, temperature_2m_min_c,
    apparent_temperature_2m_max_c,
    apparent_temperature_2m_min_c, cloud_cover_mean_pct,
    sunshine_duration_seconds, visibility_min_m,
    wind_speed_10m_max_kmh, wind_gusts_10m_max_kmh,
    weather_code, record_type, source, source_model
"""
```

Replace duplicated `SELECT ...` column lists in `RawWeatherHistoryRepository.list_observations_for_resort()` with `SELECT {RAW_WEATHER_SELECT_COLUMNS}`.

- [ ] **Step 3: Implement the batch method**

Add this method to `RawWeatherHistoryRepository` below `list_observations_for_resort()`:

```python
def list_observations_for_resorts(
    self,
    resort_ids: tuple[str, ...],
    *,
    elevation_bands: tuple[WeatherElevationBand, ...],
) -> dict[tuple[str, WeatherElevationBand], tuple[RawWeatherObservation, ...]]:
    grouped: dict[tuple[str, WeatherElevationBand], list[RawWeatherObservation]] = {
        (resort_id, elevation_band): []
        for resort_id in resort_ids
        for elevation_band in elevation_bands
    }
    if not resort_ids or not elevation_bands:
        return {key: tuple(value) for key, value in grouped.items()}

    with connect(self._database_url) as connection:
        rows = connection.execute(
            f"""
            SELECT {RAW_WEATHER_SELECT_COLUMNS}
            FROM raw_weather_history
            WHERE resort_id = ANY(%s)
              AND elevation_band = ANY(%s)
            ORDER BY resort_id, elevation_band, observed_on
            """,
            (list(resort_ids), list(elevation_bands)),
        ).fetchall()

    for row in rows:
        observation = RawWeatherObservation.model_validate(dict(row))
        grouped[(observation.resort_id, observation.elevation_band)].append(
            observation
        )
    return {key: tuple(value) for key, value in grouped.items()}
```

- [ ] **Step 4: Run repository tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_repository.py::test_raw_weather_history_lists_multiple_resorts_by_band tests/test_repository.py::test_raw_weather_history_upsert_is_elevation_band_aware -q
```

Expected: PASS.

- [ ] **Step 5: Run search-service tests again with the real batch method available**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_services.py::test_search_resorts_reuses_raw_weather_across_matching_stay_bases tests/test_services.py::test_search_resorts_single_repository_fallback_still_caches_per_request -q
```

Expected: PASS.

---

## Task 4: Remove Persistent Travel Cache From Deterministic Search Hot Path

**Files:**
- Modify: `app/domain/travel.py`
- Modify: `app/domain/search_service.py`
- Modify: `tests/test_travel.py`
- Modify: `tests/test_services.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Add a pure deterministic helper test**

In `tests/test_travel.py`, add:

```python
def test_assess_deterministic_travel_effort_does_not_require_cache() -> None:
    destination = _destination(
        resort_id="cervinia",
        name="Cervinia",
        latitude=45.9369,
        longitude=7.6317,
    )

    assessment = assess_deterministic_travel_effort(
        origin_text="Warsaw",
        destination=destination,
        tolerance="medium",
    )

    assert assessment is not None
    assert assessment.origin_label == "Warsaw"
    assert assessment.destination_label == "Cervinia"
    assert assessment.provider == "approximate_haversine_v2"
    assert assessment.provenance == "estimated_fallback"
    assert assessment.cache_hit is False
```

Expected initial result: FAIL because `assess_deterministic_travel_effort` does not exist.

- [ ] **Step 2: Add the pure helper in `app/domain/travel.py`**

Add below `assess_travel_effort()`:

```python
def assess_deterministic_travel_effort(
    origin_text: str,
    destination: Destination,
    max_drive_minutes: int | None = None,
    tolerance: TravelTolerance | None = None,
) -> TravelEffort | None:
    origin_key = normalize_origin_text(origin_text)
    if not origin_key:
        return None
    origin_key = ORIGIN_ALIASES.get(origin_key, origin_key)

    origin = KNOWN_ORIGINS.get(origin_key)
    if origin is None:
        return None

    route = _estimate_route(origin, destination)
    effort_label = _effort_label(route.duration_minutes)
    exceeds_max_drive = (
        max_drive_minutes is not None and route.duration_minutes > max_drive_minutes
    )
    return TravelEffort(
        origin_label=origin.label,
        destination_label=destination.name,
        mode="car",
        distance_km=route.distance_km,
        duration_minutes=route.duration_minutes,
        effort_label=effort_label,
        score=_score_for_effort(effort_label, route.duration_minutes, tolerance),
        summary=f"Approx. {_format_duration(route.duration_minutes)} drive from "
        f"{origin.label}.",
        provenance="estimated_fallback",
        provider=PROVIDER,
        cache_hit=False,
        caveat=CAVEAT,
        exceeds_max_drive=exceeds_max_drive,
    )
```

Do not remove or change `assess_travel_effort()`. Existing travel-cache tests should continue to pass.

- [ ] **Step 3: Use the deterministic helper in default search**

In `app/domain/search_service.py`, change the import:

```python
from app.domain.travel import (
    TravelCacheProtocol,
    assess_deterministic_travel_effort,
    assess_travel_effort,
)
```

Then replace the travel block in `search_resorts()` with:

```python
travel_effort: TravelEffort | None = None
if filters.origin_text:
    if travel_cache_repository is None:
        travel_effort = assess_deterministic_travel_effort(
            origin_text=filters.origin_text,
            destination=resort,
            max_drive_minutes=filters.max_drive_minutes,
            tolerance=filters.travel_tolerance,
        )
    else:
        travel_effort = assess_travel_effort(
            origin_text=filters.origin_text,
            destination=resort,
            cache=travel_cache_repository,
            max_drive_minutes=filters.max_drive_minutes,
            tolerance=filters.travel_tolerance,
        )
    if travel_effort is not None and travel_effort.exceeds_max_drive:
        continue
```

This preserves dependency injection: tests or future provider-backed routing can still pass a persistent `travel_cache_repository`.

- [ ] **Step 4: Add a search-service test proving no persistent travel cache is needed by default**

In `tests/test_services.py`, add:

```python
def test_search_resorts_with_origin_uses_deterministic_travel_without_cache() -> None:
    resort = _multi_stay_base_tignes()

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
            travel_month=3,
            origin_text="Berlin",
        ),
        resorts=(resort,),
        conditions_provider=StaticConditionsProvider(),
        condition_history_repository=EmptyConditionHistoryRepository(),
        raw_weather_history_repository=CountingRawHistoryRepository(()),
    )

    assert results
    assert results[0].travel_effort is not None
    assert results[0].travel_effort.origin_label == "Berlin"
    assert results[0].travel_effort.provider == "approximate_haversine_v2"
```

- [ ] **Step 5: Run focused travel and search tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_travel.py::test_assess_deterministic_travel_effort_does_not_require_cache tests/test_travel.py::test_assess_travel_effort_uses_route_cache_on_second_call tests/test_services.py::test_search_resorts_with_origin_uses_deterministic_travel_without_cache tests/test_services.py::test_search_resorts_with_origin_returns_travel_effort -q
```

Expected: PASS.

---

## Task 5: Add Runtime Timing Smoke Checks

**Files:**
- No code changes required if Task 1-4 pass.
- Optional modify: `docs/engineering-notes.md` after measuring.

- [ ] **Step 1: Run the focused backend suite**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_services.py tests/test_repository.py tests/test_travel.py tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 2: Run lint**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
```

Expected: PASS.

- [ ] **Step 3: Start the backend locally**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config uvicorn app.main:app --reload
```

Expected: app starts on `http://127.0.0.1:8000`.

- [ ] **Step 4: Time no-origin search**

In a separate shell, run:

```bash
time curl -s "http://127.0.0.1:8000/api/search?location=Italy&min_price=150&max_price=320&stars=1&skill_level=intermediate&travel_month=5" >/tmp/snowcast-search-italy-may.json
```

Expected: response under `3s` against the current remote DB. If local Postgres is used, it should be materially faster.

- [ ] **Step 5: Time origin search**

Run:

```bash
time curl -s "http://127.0.0.1:8000/api/search?location=Italy&min_price=150&max_price=320&stars=1&skill_level=intermediate&travel_month=5&origin_text=Warsaw" >/tmp/snowcast-search-italy-may-warsaw.json
```

Expected: response under `4s` against the current remote DB because deterministic fallback route estimates no longer do persistent cache reads/writes during default search.

- [ ] **Step 6: Inspect response shape**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("/tmp/snowcast-search-italy-may-warsaw.json").read_text())
results = payload["results"]
print("results", len(results))
for result in results:
    print(
        result["resort_id"],
        result.get("planning_provenance", {}).get("evidence_profile"),
        result.get("travel_effort", {}).get("provider"),
        result.get("travel_effort", {}).get("duration_minutes"),
    )
PY
```

Expected: results have the same response fields as before. `travel_effort.provider` should be `approximate_haversine_v2` for origin searches.

---

## Task 6: Decide Whether Connection Pooling Is Still Needed

**Files:**
- Modify only if Task 5 misses the target:
  - `app/data/database.py`
  - `pyproject.toml`
  - `uv.lock`
  - repository tests touching DB setup

- [ ] **Step 1: Compare timings to targets**

Use the results from Task 5:

- If country + month is under `3s` and origin search is under `4s`, do not add pooling now.
- If either target is missed by more than `1s`, continue to Step 2.

- [ ] **Step 2: Inspect remaining query count before adding dependencies**

Run a simple local timing probe with Python `time.perf_counter()` around:

```python
from app.domain.models import SearchFilters
from app.domain.search_service import search_resorts

filters = SearchFilters(
    location="Italy",
    min_price=150,
    max_price=320,
    stars=1,
    skill_level="intermediate",
    travel_month=5,
    origin_text="Warsaw",
)
results = search_resorts(filters)
```

If this is still slow and DB logs show many short-lived connections, stop and ask before adding `psycopg-pool`. The project currently depends on `psycopg[binary]` only, and AGENTS.md requires asking before modifying dependencies.

---

## Task 7: Documentation And Roadmap Notes

**Files:**
- Modify: `docs/engineering-notes.md`
- Modify: `PROJECT.md`

- [ ] **Step 1: Update engineering notes**

Add a short section to `docs/engineering-notes.md`:

```markdown
### Search Request Performance

- `/api/search` keeps the public request and response model stable, but the backend treats one request as a single planning evaluation unit.
- Raw weather history is loaded once per candidate ski-area set and reused across matching stay bases, instead of being fetched inside every stay-base option loop.
- The existing full-history raw weather repository method remains available for backfills and maintenance jobs.
- While travel effort uses the deterministic approximate car model, default search computes routes in memory and avoids persistent travel-cache reads/writes on the hot path. Provider-backed routing can reintroduce persistent route caching through explicit dependency injection.
- Connection pooling is deferred until query-count reductions are measured; reducing remote round trips is the first performance lever.
```

- [ ] **Step 2: Update PROJECT.md**

Add a concise Sprint 34 follow-up bullet under the current sprint/status area:

```markdown
- Added a search performance follow-up: `/api/search` now preloads/reuses raw weather evidence per request and avoids persistent route-cache I/O for deterministic fallback travel estimates, keeping the trip-configuration response model unchanged while making search interactive.
```

- [ ] **Step 3: Run docs-safe checks**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
```

Expected: PASS.

---

## Self-Review Checklist

- [ ] Public `/api/search` request fields remain unchanged.
- [ ] Public `/api/search` response fields remain unchanged.
- [ ] Raw weather planning still prefers `mid`, then `upper`, then `base`.
- [ ] Existing `RawWeatherHistoryRepository.list_observations_for_resort()` remains compatible for backfills and tests.
- [ ] Batch raw-weather loading returns empty tuples for missing `(resort_id, elevation_band)` keys.
- [ ] Default search no longer performs persistent travel-cache I/O for deterministic fallback route estimates.
- [ ] Explicitly injected `travel_cache_repository` still uses existing cache-aware `assess_travel_effort()`.
- [ ] No dependency changes were made unless separately approved.
- [ ] Timed smoke checks were run and recorded in the final handoff.

