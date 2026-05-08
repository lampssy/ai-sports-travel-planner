# Car-First Travel Effort Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Sprint 32 car-first travel effort to search results while keeping the product ski-trip-focused and provider-ready.

**Architecture:** Search gains optional origin and drive-preference inputs. A deterministic travel domain module normalizes origin, estimates car route effort with an approximate provider, uses cache interfaces for repeatability, and returns explainable travel effort into ranking/results. The UI surfaces origin/tolerance as bounded trip context and compact result badges, without flights, trains, itinerary planning, or traffic controls.

**Tech Stack:** FastAPI, Pydantic v2, pytest, React 18, TypeScript, Vitest/React Testing Library.

---

## File Structure

- Create `app/domain/travel.py`
  - Owns origin normalization, deterministic geocoding, approximate car-route estimation, effort labels, scoring, and cache protocol helpers.
  - Does not import FastAPI, repositories, or frontend concerns.
- Modify `app/domain/models.py`
  - Adds travel literals/models.
  - Extends `SearchFilters` with optional `origin_text`, `max_drive_minutes`, and `travel_tolerance`.
  - Extends `SearchResult` with optional `travel_effort`.
- Modify `app/domain/search_service.py`
  - Calls travel assessment only when origin context is present.
  - Applies travel score softly by default and excludes only when `max_drive_minutes` is exceeded.
  - Adds travel explanation highlights/risks.
- Modify `app/api/routes.py`
  - Accepts optional search query params: `origin_text`, `max_drive_minutes`, and `travel_tolerance`.
- Modify `app/data/database.py`
  - Adds provider-ready cache tables for geocode and route estimates.
- Modify `app/data/repositories.py`
  - Adds `TravelCacheRepository` implementing the travel cache protocol.
- Modify `tests/test_travel.py`
  - Covers geocoding, route estimation, cache keying, scoring buckets, and threshold behavior.
- Modify `tests/test_services.py` and `tests/test_api.py`
  - Covers search compatibility without origin and travel fields/ranking with origin.
- Modify `frontend/src/types.ts`
  - Adds travel filter/result types.
- Modify `frontend/src/api.ts`
  - Sends optional travel params to `/api/search`.
- Modify `frontend/src/App.tsx`
  - Projects parsed `trip_context.origin_text` into search filters.
  - Adds advanced origin/max-drive/tolerance controls.
  - Renders travel chips and compact travel badges on result cards/details.
- Modify `frontend/src/App.test.tsx`
  - Covers parsed origin projection, travel chips, API query params, and result travel badge.
- Modify `README.md`, `PROJECT.md`, and `docs/engineering-notes.md`
  - Documents Sprint 32 completion and the approximate-provider boundary.

## Data Contract

Search query additions:

```text
origin_text=Munich
max_drive_minutes=300
travel_tolerance=medium
```

`travel_tolerance` values:

- `short`
- `medium`
- `flexible`

Search result addition:

```json
{
  "travel_effort": {
    "origin_label": "Munich",
    "destination_label": "Alta Badia",
    "mode": "car",
    "distance_km": 295.4,
    "duration_minutes": 268,
    "effort_label": "moderate",
    "score": 0.78,
    "summary": "Approx. 4h 28m drive from Munich.",
    "provenance": "estimated_fallback",
    "provider": "approximate_haversine_v1",
    "cache_hit": false,
    "caveat": "Approximate car estimate based on straight-line distance and a road multiplier."
  }
}
```

## Task 1: Travel Domain Models And Deterministic Provider

**Files:**
- Create: `app/domain/travel.py`
- Modify: `app/domain/models.py`
- Test: `tests/test_travel.py`

- [ ] **Step 1: Write failing travel-domain tests**

Create `tests/test_travel.py` with tests for:

```python
from app.domain.models import Destination
from app.domain.travel import (
    InMemoryTravelCache,
    assess_travel_effort,
    normalize_origin_text,
)


def test_normalize_origin_text_is_stable() -> None:
    assert normalize_origin_text("  München, Germany ") == "munchen germany"


def test_assess_travel_effort_returns_approximate_car_estimate_for_known_origin(
    sample_destination: Destination,
) -> None:
    cache = InMemoryTravelCache()
    assessment = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=cache,
    )

    assert assessment is not None
    assert assessment.origin_label == "Munich"
    assert assessment.mode == "car"
    assert assessment.distance_km > 0
    assert assessment.duration_minutes > 0
    assert assessment.provenance == "estimated_fallback"
    assert assessment.provider == "approximate_haversine_v1"


def test_assess_travel_effort_uses_route_cache_on_second_call(
    sample_destination: Destination,
) -> None:
    cache = InMemoryTravelCache()
    first = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=cache,
    )
    second = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=cache,
    )

    assert first is not None
    assert second is not None
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.duration_minutes == first.duration_minutes


def test_assess_travel_effort_respects_max_drive_threshold(
    sample_destination: Destination,
) -> None:
    assessment = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=InMemoryTravelCache(),
        max_drive_minutes=1,
    )

    assert assessment is not None
    assert assessment.exceeds_max_drive is True
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_travel.py -q
```

Expected: fail because `app.domain.travel` and travel models do not exist.

- [ ] **Step 3: Add models in `app/domain/models.py`**

Add literals near existing aliases:

```python
TravelMode = Literal["car"]
TravelTolerance = Literal["short", "medium", "flexible"]
TravelEffortLabel = Literal["easy", "moderate", "long", "very_long"]
TravelRouteProvenance = Literal["provider_backed", "estimated_fallback"]
```

Extend `SearchFilters`:

```python
origin_text: str | None = Field(default=None)
max_drive_minutes: int | None = Field(default=None, ge=1)
travel_tolerance: TravelTolerance | None = Field(default=None)
```

Add:

```python
class TravelEffort(BaseModel):
    origin_label: str
    destination_label: str
    mode: TravelMode = "car"
    distance_km: float = Field(ge=0)
    duration_minutes: int = Field(ge=0)
    effort_label: TravelEffortLabel
    score: float = Field(ge=0, le=1)
    summary: str
    provenance: TravelRouteProvenance
    provider: str
    cache_hit: bool = False
    caveat: str | None = None
    exceeds_max_drive: bool = False
```

Extend `SearchResult`:

```python
travel_effort: TravelEffort | None = Field(default=None)
```

- [ ] **Step 4: Implement `app/domain/travel.py`**

Implement:

- `normalize_origin_text(text: str) -> str`
- `TravelCacheProtocol` with geocode and route get/set methods
- `InMemoryTravelCache`
- static known origins for common European starting points: Munich, Milan, Zurich, Vienna, Berlin, Paris, Lyon, Prague, Warsaw, Amsterdam, Brussels, London
- `assess_travel_effort(origin_text, destination, cache, max_drive_minutes=None, tolerance=None)`
- haversine distance, `ROAD_DISTANCE_MULTIPLIER = 1.35`, `AVERAGE_CAR_SPEED_KMH = 72`
- labels:
  - easy: `<= 180` minutes
  - moderate: `<= 360`
  - long: `<= 540`
  - very_long: `> 540`
- scoring:
  - easy `0.95`
  - moderate `0.78`
  - long `0.48`
  - very_long `0.2`
  - tolerance can nudge scores: short penalizes long trips more, flexible reduces penalty

- [ ] **Step 5: Run Task 1 tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_travel.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/travel.py app/domain/models.py tests/test_travel.py
```

Expected: pass.

## Task 2: Search/API Integration And Persistent Cache

**Files:**
- Modify: `app/domain/search_service.py`
- Modify: `app/api/routes.py`
- Modify: `app/data/database.py`
- Modify: `app/data/repositories.py`
- Test: `tests/test_services.py`, `tests/test_api.py`

- [ ] **Step 1: Write failing integration tests**

Add tests that assert:

- search without `origin_text` still returns results and `travel_effort is None`
- search with `origin_text="Munich"` returns `travel_effort`
- `max_drive_minutes=1` excludes all results for a far destination
- API `/api/search?...&origin_text=Munich&travel_tolerance=medium` returns travel fields

- [ ] **Step 2: Run failing integration tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_services.py::test_search_resorts_with_origin_returns_travel_effort tests/test_api.py::test_search_with_origin_returns_travel_effort -q
```

Expected: fail until API/search integration exists.

- [ ] **Step 3: Add database cache tables**

In `_create_schema`, add:

```sql
CREATE TABLE IF NOT EXISTS travel_geocode_cache (
    normalized_origin TEXT NOT NULL,
    provider TEXT NOT NULL,
    resolved_label TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (normalized_origin, provider)
);

CREATE TABLE IF NOT EXISTS travel_route_cache (
    origin_key TEXT NOT NULL,
    destination_entity_type TEXT NOT NULL,
    destination_entity_id TEXT NOT NULL,
    destination_coord_key TEXT NOT NULL,
    mode TEXT NOT NULL,
    provider TEXT NOT NULL,
    distance_km DOUBLE PRECISION NOT NULL,
    duration_minutes INTEGER NOT NULL,
    provenance TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (
        origin_key,
        destination_entity_type,
        destination_entity_id,
        destination_coord_key,
        mode,
        provider
    )
);
```

- [ ] **Step 4: Add `TravelCacheRepository`**

In `app/data/repositories.py`, implement the cache protocol from `app.domain.travel`.

- [ ] **Step 5: Wire search**

In `search_resorts`, add optional `travel_cache_repository=None`.

When `filters.origin_text` is present:

- call `assess_travel_effort(...)` for the destination
- skip result when `assessment.exceeds_max_drive`
- subtract `(1 - assessment.score) * 0.35` from ranking score
- pass `travel_effort=assessment` into `SearchResult`
- add explanation highlight/risk for travel effort

- [ ] **Step 6: Wire API**

Add query params in `app/api/routes.py`:

```python
origin_text: str | None = None
max_drive_minutes: Annotated[int | None, Query(ge=1)] = None
travel_tolerance: TravelTolerance | None = None
```

Populate `SearchFilters`.

- [ ] **Step 7: Run Task 2 tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_travel.py tests/test_services.py tests/test_api.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests/test_travel.py tests/test_services.py tests/test_api.py
```

Expected: pass.

## Task 3: Frontend Travel Controls And Badges

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Add tests that assert:

- parsed `trip_context.origin_text` populates the travel origin filter
- search sends `origin_text` and `travel_tolerance`
- a result with `travel_effort` shows an approximate drive badge

- [ ] **Step 2: Run failing frontend tests**

Run:

```bash
cd frontend && npm test -- App.test.tsx -t "travel effort"
```

Expected: fail until frontend is wired.

- [ ] **Step 3: Add frontend types**

Extend `SearchFilters`:

```ts
originText: string;
maxDriveHours: string;
travelTolerance: "" | "short" | "medium" | "flexible";
```

Add `TravelEffort` to `SearchResult`.

- [ ] **Step 4: Send API params**

In `searchResorts`, set:

```ts
if (filters.originText.trim()) query.set("origin_text", filters.originText.trim());
if (filters.maxDriveHours) query.set("max_drive_minutes", String(Math.round(Number(filters.maxDriveHours) * 60)));
if (filters.travelTolerance) query.set("travel_tolerance", filters.travelTolerance);
```

- [ ] **Step 5: Project parsed origin**

When `parsed.trip_context?.origin_text` exists, set `filters.originText`.

When applying a clarification option with `context_patch.origin_text`, update `filters.originText`.

- [ ] **Step 6: Render controls and badges**

Add advanced filter inputs for origin, max drive hours, and travel tolerance.

Render:

- applied origin chip
- max drive chip
- travel tolerance chip
- compact result card badge using `result.travel_effort.summary`
- detail view evidence row for travel effort

- [ ] **Step 7: Run frontend tests/build**

Run:

```bash
cd frontend && npm test -- App.test.tsx
cd frontend && npm run build
```

Expected: pass.

## Task 4: Documentation And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `PROJECT.md`
- Modify: `docs/engineering-notes.md`

- [ ] **Step 1: Update docs**

Document:

- Sprint 32 completed
- car-first approximate travel effort
- no flights/trains/itinerary planning
- cache boundary/provider-ready design

- [ ] **Step 2: Run final checks**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_travel.py tests/test_services.py tests/test_api.py tests/test_parser.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
cd frontend && npm test -- App.test.tsx
cd frontend && npm run build
```

- [ ] **Step 3: Manual acceptance**

Start backend and frontend:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config uvicorn app.main:app --reload
cd frontend && npm run dev
```

Search:

```text
Ski in Italy from Munich, 22-29.01.2027
```

Expected:

- search sends `origin_text=Munich`
- results include travel badges
- ranking stays ski-focused
- no flight/train/itinerary UI appears
