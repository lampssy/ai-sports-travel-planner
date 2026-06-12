# Grouped Trip Options And Stay-Base Acquisition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Sprint 33: grouped trip recommendations with clickable stay-base alternatives, then extend catalog acquisition with stay-base enrichment adapters.

**Architecture:** Search will evaluate full trip options internally, then return one backward-compatible recommendation group per destination/ski-area with `top_option` and `alternative_options`. The frontend will keep the main card grouped and allow click-to-preview stay-base alternatives inside the detail page. Acquisition will target stable stay-base IDs and emit review-only proposals for deterministic facts first, then constrained qualitative profile tags.

**Tech Stack:** FastAPI, Pydantic, Postgres seed sync, React/Vite/TypeScript, pytest, Vitest, existing `app/data/resort_acquisition` artifact pipeline.

---

## Implementation Slices

Execute in order:

1. Backend grouped trip-option model.
2. Frontend clickable stay-base alternatives.
3. Stable stay-base IDs in catalog/model/database.
4. Stay-base acquisition target resolution and deterministic adapters.
5. Constrained profile LLM proposals.
6. Docs and final verification.

Do not start acquisition work before grouped search and UI are working. The acquisition field set should serve the product model, not the other way around.

---

## Files

### Backend Search

- Modify `app/domain/models.py`
  - Add `TripOption` response model.
  - Add `top_option` and `alternative_options` to `SearchResult`.
  - Later add stable stay-base fields to `StayBase`.
- Modify `app/domain/search_service.py`
  - Make `_build_result` the top-option compatibility wrapper.
  - Add option conversion and alternative selection helpers.
  - Return one grouped result per destination/ski-area.
- Modify `app/domain/services.py`
  - Keep narrative generation only on the grouped top result.
- Modify `tests/test_services.py`
  - Add grouped-search behavior tests.
- Modify `tests/test_api.py`
  - Assert response includes `top_option` and `alternative_options` without breaking existing fields.

### Frontend

- Modify `frontend/src/types.ts`
  - Add `TripOption`.
  - Add `top_option` and `alternative_options` to `SearchResult`.
- Modify `frontend/src/App.tsx`
  - Show alternative count on result cards.
  - Add click-to-preview alternative stay-base rows in result details.
  - Update detail facts and booking redirect for the active option.
- Modify `frontend/src/App.test.tsx`
  - Add tests for alternative count and click-to-preview behavior.

### Stay-Base Data Model

- Modify `app/domain/models.py`
  - Add `stay_base_id`, optional coordinates, access fields, and profile fields to `StayBase`.
- Modify `app/data/loader.py`
  - Derive a stable `stay_base_id` from `resort_id` and stay-base name when missing.
- Modify `app/data/database.py`
  - Add stay-base columns and bootstrap sync.
- Modify `app/data/repositories.py`
  - Read/write new stay-base fields.
- Modify `tests/test_catalog_validation.py`, `tests/test_repository.py`
  - Cover generated IDs and DB persistence.

### Stay-Base Acquisition

- Modify `app/data/resort_acquisition/models.py`
  - Add `stay_base` proposal target.
  - Add extraction methods: `stay_base_osm`, `stay_base_wikidata`, `stay_base_lift_distance`, `stay_base_profile_llm`.
- Modify `app/data/resort_acquisition/proposals.py`
  - Resolve target field paths for `stay_bases[]`.
- Create `app/data/resort_acquisition/stay_bases.py`
  - Catalog stay-base target loading.
  - OSM/Wikidata candidate extraction from mocked provider payloads.
  - Lift-distance bucket computation.
  - Profile proposal validation.
- Modify `app/data/resort_acquisition/run_catalog_acquisition.py`
  - Add `--scope resort-static|stay-bases|full-catalog`.
  - Run stay-base scope after resort-level source context.
- Modify `app/data/resort_acquisition/reports.py`
  - Group stay-base proposals by resort and stay base in `evidence.md`.
- Modify `tests/test_resort_acquisition.py`
  - Add stay-base proposal target, extraction, report, and CLI scope tests.

### Documentation

- Modify `PROJECT.md`
  - Mark Sprint 33 as in progress or completed after implementation.
- Modify `README.md`
  - Document grouped search fields and stay-base acquisition scope.
- Modify `docs/engineering-notes.md`
  - Capture grouped trip-option model and stay-base acquisition boundaries.

---

## Task 1: Backend Trip Option Response Model

**Files:**
- Modify `app/domain/models.py`
- Modify `tests/test_services.py`
- Modify `tests/test_api.py`

- [ ] **Step 1: Write failing model/API tests**

Append to `tests/test_services.py`:

```python
def test_search_result_exposes_top_option_and_alternatives() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=120,
            max_price=340,
            stars=1,
            skill_level="intermediate",
        )
    )

    assert results
    result = results[0]
    assert result.top_option.stay_base_name == result.selected_stay_base_name
    assert result.top_option.ski_area_id == result.selected_ski_area_id
    assert result.top_option.score == result.score
    assert isinstance(result.alternative_options, list)
```

Append to `tests/test_api.py`:

```python
def test_search_response_includes_grouped_trip_option_fields() -> None:
    response = client.get(
        "/api/search",
        params={
            "location": "France",
            "min_price": 120,
            "max_price": 340,
            "stars": 1,
            "skill_level": "intermediate",
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["top_option"]["stay_base_name"] == result["selected_stay_base_name"]
    assert "alternative_options" in result
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_services.py::test_search_result_exposes_top_option_and_alternatives \
  tests/test_api.py::test_search_response_includes_grouped_trip_option_fields -q
```

Expected: fail because `top_option` does not exist.

- [ ] **Step 3: Add `TripOption` model**

In `app/domain/models.py`, add before `SearchResult`:

```python
class TripOption(BaseModel):
    option_id: str = Field(description="Stable option id within one search response.")
    ski_area_id: str
    ski_area_name: str
    stay_base_name: str
    stay_base_lift_distance: LiftDistance
    stay_base_price_range: str
    rental_name: str
    rental_price_range: str
    rating_estimate: int
    score: float
    recommendation_confidence: float = Field(ge=0, le=1)
    budget_penalty: float
    travel_effort: TravelEffort | None = None
    explanation: SearchExplanation
    tradeoff_summary: str
```

Then add these fields to `SearchResult`:

```python
    top_option: TripOption | None = Field(default=None)
    alternative_options: list[TripOption] = Field(default_factory=list)
```

- [ ] **Step 4: Add a temporary top-option builder**

In `app/domain/search_service.py`, add:

```python
def _trip_option_from_result(result: SearchResult) -> TripOption:
    return TripOption(
        option_id=_trip_option_id(result),
        ski_area_id=result.selected_ski_area_id,
        ski_area_name=result.selected_ski_area_name,
        stay_base_name=result.selected_stay_base_name,
        stay_base_lift_distance=result.selected_stay_base_lift_distance,
        stay_base_price_range=result.stay_base_price_range,
        rental_name=result.rental_name,
        rental_price_range=result.rental_price_range,
        rating_estimate=result.rating_estimate,
        score=result.score,
        recommendation_confidence=result.recommendation_confidence,
        budget_penalty=result.budget_penalty,
        travel_effort=result.travel_effort,
        explanation=result.explanation,
        tradeoff_summary=_trip_option_tradeoff_summary(result),
    )


def _trip_option_id(result: SearchResult) -> str:
    return "|".join(
        [
            result.selected_ski_area_id,
            result.selected_stay_base_name,
            result.rental_name,
        ]
    )


def _trip_option_tradeoff_summary(result: SearchResult) -> str:
    access = result.selected_stay_base_lift_distance.replace("_", " ")
    return (
        f"{result.selected_stay_base_name}: {access} lift access, "
        f"{result.stay_base_price_range} stay estimate."
    )
```

Update `_build_result` so it constructs the result, then fills `top_option`:

```python
    result = SearchResult(
        resort_id=destination.resort_id,
        resort_name=destination.name,
        region=destination.region,
        selected_ski_area_id=ski_area.ski_area_id,
        selected_ski_area_name=ski_area.name,
        selected_stay_base_name=stay_base.name,
        selected_stay_base_lift_distance=stay_base.lift_distance,
        stay_base_price_range=stay_base.price_range,
        selected_area_name=stay_base.name,
        selected_area_lift_distance=stay_base.lift_distance,
        area_price_range=stay_base.price_range,
        rental_name=rental.name,
        rental_price_range=rental.price_range,
        rating_estimate=quality,
        link=build_accommodation_link(
            resort_name=destination.name,
            country=destination.country,
        ),
        score=score,
        budget_penalty=penalty,
        conditions_summary=active_conditions.weather_summary,
        snow_confidence_score=snow_confidence_score,
        snow_confidence_label=active_conditions.snow_confidence_label,
        availability_status=active_conditions.availability_status,
        conditions_score=conditions_score,
        conditions_provenance=conditions_provenance,
        explanation=explanation,
        recommendation_confidence=min(
            (quality / 3) * 0.45
            + snow_confidence_score * 0.35
            + (1 - availability_score_penalty) * 0.2,
            1.0,
        ),
        planning_summary=planning_summary,
        planning_provenance=planning_provenance,
        planning_evidence_count=planning_evidence_count,
        planning_weather_metrics=planning_weather_metrics,
        best_travel_months=list(best_travel_months),
        travel_effort=travel_effort,
    )
    return result.model_copy(update={"top_option": _trip_option_from_result(result)})
```

The final search/API tests require `top_option` to be non-null for returned results, even though the model allows `None` while constructing compatibility objects.

- [ ] **Step 5: Run focused tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_services.py::test_search_result_exposes_top_option_and_alternatives \
  tests/test_api.py::test_search_response_includes_grouped_trip_option_fields -q
```

Expected: pass.

---

## Task 2: Group Trip Options And Select Alternatives

**Files:**
- Modify `app/domain/search_service.py`
- Modify `tests/test_services.py`

- [ ] **Step 1: Write failing grouping tests**

Append to `tests/test_services.py`:

```python
def test_search_groups_stay_base_alternatives_under_one_result() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=120,
            max_price=340,
            stars=1,
            skill_level="intermediate",
        )
    )

    by_resort = {result.resort_id: result for result in results}
    assert "tignes" in by_resort
    tignes = by_resort["tignes"]
    alternative_names = {
        option.stay_base_name for option in tignes.alternative_options
    }

    assert tignes.selected_stay_base_name not in alternative_names
    assert len(alternative_names) <= 3
    assert all(option.score <= tignes.score for option in tignes.alternative_options)
```

Add a duplicate-suppression check:

```python
def test_search_does_not_return_duplicate_resort_cards_by_default() -> None:
    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=120,
            max_price=340,
            stars=1,
            skill_level="intermediate",
        )
    )

    resort_ids = [result.resort_id for result in results]
    assert len(resort_ids) == len(set(resort_ids))
```

- [ ] **Step 2: Run tests and confirm failure or missing alternatives**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_services.py::test_search_groups_stay_base_alternatives_under_one_result \
  tests/test_services.py::test_search_does_not_return_duplicate_resort_cards_by_default -q
```

Expected: the alternatives test fails until grouping is implemented.

- [ ] **Step 3: Add option grouping helper**

In `app/domain/search_service.py`, replace the existing `if matching_pairs:` block with a helper:

```python
        grouped_result = _build_recommendation_group(matching_pairs)
        if grouped_result is not None:
            results.append(grouped_result)
```

Add:

```python
MAX_ALTERNATIVE_OPTIONS = 3
MIN_ALTERNATIVE_SCORE_DELTA = 0.03


def _build_recommendation_group(
    options: list[SearchResult],
) -> SearchResult | None:
    if not options:
        return None
    sorted_options = sorted(options, key=_result_sort_key)
    top = sorted_options[0]
    alternatives = _select_alternative_options(top, sorted_options[1:])
    return top.model_copy(
        update={
            "top_option": _trip_option_from_result(top),
            "alternative_options": alternatives,
        }
    )


def _select_alternative_options(
    top: SearchResult,
    remaining_options: list[SearchResult],
) -> list[TripOption]:
    selected: list[TripOption] = []
    seen_stay_bases = {top.selected_stay_base_name}
    for option in remaining_options:
        if option.selected_stay_base_name in seen_stay_bases:
            continue
        if not _option_is_meaningfully_different(top, option):
            continue
        selected.append(_trip_option_from_result(option))
        seen_stay_bases.add(option.selected_stay_base_name)
        if len(selected) >= MAX_ALTERNATIVE_OPTIONS:
            break
    return selected


def _option_is_meaningfully_different(
    top: SearchResult,
    option: SearchResult,
) -> bool:
    if abs(top.score - option.score) <= MIN_ALTERNATIVE_SCORE_DELTA:
        return True
    return (
        option.selected_stay_base_lift_distance != top.selected_stay_base_lift_distance
        or option.stay_base_price_range != top.stay_base_price_range
        or option.rating_estimate != top.rating_estimate
    )


def _result_sort_key(result: SearchResult) -> tuple[float, float, str, str, str]:
    return (
        -result.score,
        -result.snow_confidence_score,
        result.resort_name,
        result.selected_stay_base_name,
        result.selected_ski_area_name,
    )
```

Use `_result_sort_key` for the final return:

```python
    return sorted(results, key=_result_sort_key)[:3]
```

- [ ] **Step 4: Run focused grouping tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_services.py::test_search_groups_stay_base_alternatives_under_one_result \
  tests/test_services.py::test_search_does_not_return_duplicate_resort_cards_by_default -q
```

Expected: pass.

---

## Task 3: Frontend Alternative Count And Click-To-Preview

**Files:**
- Modify `frontend/src/types.ts`
- Modify `frontend/src/App.tsx`
- Modify `frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Update the first fixture in `frontend/src/App.test.tsx` to include:

```ts
top_option: {
  option_id: "alpine-horizon-main-bowl|Pine Chalet Zone|Budget Ski Stop",
  ski_area_id: "alpine-horizon-main-bowl",
  ski_area_name: "Alpine Horizon Main Bowl",
  stay_base_name: "Pine Chalet Zone",
  stay_base_lift_distance: "near",
  stay_base_price_range: "EUR 150-190",
  rental_name: "Budget Ski Stop",
  rental_price_range: "EUR 30-45",
  rating_estimate: 2,
  score: 1.7,
  recommendation_confidence: 0.86,
  budget_penalty: 0,
  travel_effort: null,
  explanation: firstResponse.results[0].explanation,
  tradeoff_summary: "Pine Chalet Zone: near lift access, EUR 150-190 stay estimate.",
},
alternative_options: [
  {
    option_id: "alpine-horizon-main-bowl|Lake Quarter|Budget Ski Stop",
    ski_area_id: "alpine-horizon-main-bowl",
    ski_area_name: "Alpine Horizon Main Bowl",
    stay_base_name: "Lake Quarter",
    stay_base_lift_distance: "medium",
    stay_base_price_range: "EUR 120-160",
    rental_name: "Budget Ski Stop",
    rental_price_range: "EUR 30-45",
    rating_estimate: 2,
    score: 1.55,
    recommendation_confidence: 0.8,
    budget_penalty: 0,
    travel_effort: null,
    explanation: firstResponse.results[0].explanation,
    tradeoff_summary: "Lake Quarter: medium lift access, EUR 120-160 stay estimate.",
  },
],
```

Add tests:

```ts
it("shows alternative stay-base count on the result card", async () => {
  setupFetch(firstResponse);
  render(<App />);
  await runDefaultSearch();

  expect(screen.getByText("1 alternative base")).toBeInTheDocument();
});

it("previews a clicked stay-base alternative in the detail page", async () => {
  const user = userEvent.setup();
  setupFetch(firstResponse);
  render(<App />);
  await runDefaultSearch();

  await user.click(screen.getByText("View resort details"));
  await user.click(screen.getByRole("button", { name: /Lake Quarter/i }));

  expect(screen.getAllByText("Lake Quarter").length).toBeGreaterThan(0);
  expect(screen.getByText("EUR 120-160")).toBeInTheDocument();
  expect(screen.getByText(/Medium lift access/i)).toBeInTheDocument();
});
```

Use the existing helper names in `App.test.tsx`; if `setupFetch` or `runDefaultSearch` are named differently, adapt to the local test helpers.

- [ ] **Step 2: Run frontend tests and confirm failure**

Run:

```bash
cd frontend && npm test -- App.test.tsx
```

Expected: fail because alternatives are not rendered.

- [ ] **Step 3: Add frontend types**

In `frontend/src/types.ts`, add:

```ts
export interface TripOption {
  option_id: string;
  ski_area_id: string;
  ski_area_name: string;
  stay_base_name: string;
  stay_base_lift_distance: LiftDistance;
  stay_base_price_range: string;
  rental_name: string;
  rental_price_range: string;
  rating_estimate: number;
  score: number;
  recommendation_confidence: number;
  budget_penalty: number;
  travel_effort?: TravelEffort | null;
  explanation: SearchExplanation;
  tradeoff_summary: string;
}
```

Add to `SearchResult`:

```ts
  top_option: TripOption;
  alternative_options: TripOption[];
```

- [ ] **Step 4: Render alternative count on cards**

In `SearchResultCard`, under the stay-base line, add:

```tsx
{result.alternative_options.length > 0 ? (
  <span className="rounded-full bg-frost px-3 py-1 text-sm font-semibold text-alpine">
    {result.alternative_options.length} alternative
    {result.alternative_options.length === 1 ? "" : "s"} base
    {result.alternative_options.length === 1 ? "" : "s"}
  </span>
) : null}
```

- [ ] **Step 5: Add click-to-preview state**

Inside `ResultDetails`, add:

```tsx
const [activeOptionId, setActiveOptionId] = useState(result.top_option.option_id);
useEffect(() => {
  setActiveOptionId(result.top_option.option_id);
}, [result.resort_id, result.top_option.option_id]);

const allOptions = [result.top_option, ...result.alternative_options];
const activeOption =
  allOptions.find((option) => option.option_id === activeOptionId) ??
  result.top_option;
```

Use `activeOption` for stay-base-specific detail fields:

- stay base name
- lift distance
- stay-base price range
- rental name
- rental price range
- option confidence where shown for stay-specific comparison

Do not replace resort-level fields such as resort name, region, snow signal, planning summary, or current conditions.

- [ ] **Step 6: Render alternative option buttons**

Add a `DetailPanel title="Stay-base options"` before `Stay + Rental`:

```tsx
<DetailPanel title="Stay-base options">
  <div className="grid gap-3">
    {allOptions.map((option) => {
      const selected = option.option_id === activeOption.option_id;
      return (
        <button
          key={option.option_id}
          type="button"
          className={`rounded-2xl border px-4 py-4 text-left transition ${
            selected
              ? "border-alpine bg-frost"
              : "border-slate-200 bg-white hover:border-alpine/40"
          }`}
          onClick={() => setActiveOptionId(option.option_id)}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="font-semibold text-ink">{option.stay_base_name}</span>
            <span className="text-sm font-semibold text-alpine">
              {option.stay_base_price_range}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-600">
            {option.tradeoff_summary}
          </p>
        </button>
      );
    })}
  </div>
</DetailPanel>
```

- [ ] **Step 7: Run frontend tests**

Run:

```bash
cd frontend && npm test -- App.test.tsx
```

Expected: pass.

---

## Task 4: Stable Stay-Base IDs And Optional Facts

**Files:**
- Modify `app/domain/models.py`
- Modify `app/data/loader.py`
- Modify `app/data/database.py`
- Modify `app/data/repositories.py`
- Modify `tests/test_catalog_validation.py`
- Modify `tests/test_repository.py`

- [ ] **Step 1: Write failing loader/repository tests**

Add to `tests/test_repository.py`:

```python
def test_repository_preserves_stable_stay_base_ids() -> None:
    resorts = get_resort_repository().list_resorts()
    tignes = next(resort for resort in resorts if resort.resort_id == "tignes")

    assert tignes.stay_bases
    assert all(stay_base.stay_base_id for stay_base in tignes.stay_bases)
```

Add to `tests/test_catalog_validation.py`:

```python
def test_catalog_loader_derives_stay_base_id_when_missing(tmp_path) -> None:
    payload = [_minimal_valid_resort()]
    payload[0]["stay_bases"][0].pop("stay_base_id", None)
    path = tmp_path / "resorts.json"
    path.write_text(json.dumps(payload))

    resorts = load_resorts_from_path(path)

    assert resorts[0].stay_bases[0].stay_base_id.startswith(
        f"{resorts[0].resort_id}-"
    )
```

Use existing helper names in `tests/test_catalog_validation.py`.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_repository.py::test_repository_preserves_stable_stay_base_ids \
  tests/test_catalog_validation.py::test_catalog_loader_derives_stay_base_id_when_missing -q
```

Expected: fail because `StayBase.stay_base_id` does not exist.

- [ ] **Step 3: Extend `StayBase`**

In `app/domain/models.py`, update `StayBase`:

```python
    stay_base_id: str = Field(
        description="Stable stay-base identifier used by grouped options and acquisition."
    )
    latitude: float | None = None
    longitude: float | None = None
    nearest_lift_name: str | None = None
    nearest_lift_distance_m: int | None = Field(default=None, ge=0)
    access_mode: Literal["walk", "ski_bus", "car_recommended", "unknown"] = "unknown"
    base_type: str | None = None
    atmosphere_tags: list[str] = Field(default_factory=list)
    regional_data_ids: dict[str, str] = Field(default_factory=dict)
```

If type aliases are preferred, add them near the existing domain literals.

- [ ] **Step 4: Derive missing IDs in loader**

In `app/data/loader.py`, change `_build_stay_base` signature:

```python
def _build_stay_base(payload: dict, *, resort_id: str) -> StayBase:
    minimum, maximum = _parse_price_range(payload["price_range"])
    stay_base_id = payload.get("stay_base_id") or _stable_stay_base_id(
        resort_id=resort_id,
        name=payload["name"],
    )
    return StayBase.model_validate(
        {
            **payload,
            "stay_base_id": stay_base_id,
            "price_min": minimum,
            "price_max": maximum,
        }
    )
```

Add:

```python
def _stable_stay_base_id(*, resort_id: str, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{resort_id}-{slug}"
```

Import `re`.

Update call site:

```python
stay_bases = [
    _build_stay_base(stay_base, resort_id=resort_payload["resort_id"])
    for stay_base in stay_base_payloads
]
```

- [ ] **Step 5: Extend database schema and sync**

In `app/data/database.py`, add to `stay_bases` table:

```sql
stay_base_id TEXT NOT NULL,
latitude DOUBLE PRECISION,
longitude DOUBLE PRECISION,
nearest_lift_name TEXT,
nearest_lift_distance_m INTEGER,
access_mode TEXT NOT NULL DEFAULT 'unknown',
base_type TEXT,
atmosphere_tags_json TEXT NOT NULL DEFAULT '[]',
regional_data_ids_json TEXT NOT NULL DEFAULT '{}',
UNIQUE(resort_id, stay_base_id)
```

Add `ALTER TABLE` statements for existing databases:

```sql
ALTER TABLE stay_bases ADD COLUMN IF NOT EXISTS stay_base_id TEXT;
ALTER TABLE stay_bases ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE stay_bases ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE stay_bases ADD COLUMN IF NOT EXISTS nearest_lift_name TEXT;
ALTER TABLE stay_bases ADD COLUMN IF NOT EXISTS nearest_lift_distance_m INTEGER;
ALTER TABLE stay_bases ADD COLUMN IF NOT EXISTS access_mode TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE stay_bases ADD COLUMN IF NOT EXISTS base_type TEXT;
ALTER TABLE stay_bases ADD COLUMN IF NOT EXISTS atmosphere_tags_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE stay_bases ADD COLUMN IF NOT EXISTS regional_data_ids_json TEXT NOT NULL DEFAULT '{}';
```

Because old rows are deleted/reinserted during seed sync, `stay_base_id` can be nullable in the `ALTER TABLE` path but non-null in created fresh schema.

Update stay-base insert to include all new fields.

- [ ] **Step 6: Extend repository read path**

In `app/data/repositories.py`, include the new columns in the stay-base select:

```sql
SELECT id, resort_id, stay_base_id, name, price_range, price_min, price_max,
       quality, lift_distance, latitude, longitude, nearest_lift_name,
       nearest_lift_distance_m, access_mode, base_type, atmosphere_tags_json,
       regional_data_ids_json
FROM stay_bases
ORDER BY resort_id, id
```

Then pass them into `StayBase.model_validate(...)`:

```python
StayBase.model_validate(
    {
        "stay_base_id": row["stay_base_id"],
        "name": row["name"],
        "price_range": row["price_range"],
        "price_min": row["price_min"],
        "price_max": row["price_max"],
        "quality": row["quality"],
        "lift_distance": row["lift_distance"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "nearest_lift_name": row["nearest_lift_name"],
        "nearest_lift_distance_m": row["nearest_lift_distance_m"],
        "access_mode": row["access_mode"],
        "base_type": row["base_type"],
        "atmosphere_tags": json.loads(row["atmosphere_tags_json"] or "[]"),
        "regional_data_ids": json.loads(row["regional_data_ids_json"] or "{}"),
        "supported_skill_levels": skills_by_stay_base.get(row["id"], []),
    }
)
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_repository.py::test_repository_preserves_stable_stay_base_ids \
  tests/test_catalog_validation.py::test_catalog_loader_derives_stay_base_id_when_missing -q
```

Expected: pass.

---

## Task 5: Stay-Base Acquisition Targets And Deterministic Adapters

**Files:**
- Modify `app/data/resort_acquisition/models.py`
- Modify `app/data/resort_acquisition/proposals.py`
- Create `app/data/resort_acquisition/stay_bases.py`
- Modify `app/data/resort_acquisition/run_catalog_acquisition.py`
- Modify `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing proposal-target tests**

Add to `tests/test_resort_acquisition.py`:

```python
def test_build_proposals_resolves_stay_base_target() -> None:
    raw_catalog = {
        "tignes": {
            "resort_id": "tignes",
            "stay_bases": [
                {
                    "stay_base_id": "tignes-val-claret",
                    "name": "Val Claret",
                    "lift_distance": "near",
                }
            ],
        }
    }
    candidate = CandidateFact(
        resort_id="tignes",
        target={"entity_type": "stay_base", "entity_id": "tignes-val-claret"},
        field_path="lift_distance",
        proposed_value="medium",
        source={"source_type": "osm", "source_name": "OSM"},
        extraction_method="stay_base_lift_distance",
        fetched_at=datetime.now(timezone.utc),
        confidence=0.82,
    )

    proposals = build_proposals(raw_catalog, [candidate])

    assert proposals[0].current_value == "near"
    assert proposals[0].status == "changed"
```

- [ ] **Step 2: Run test and confirm failure**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_resort_acquisition.py::test_build_proposals_resolves_stay_base_target -q
```

Expected: fail because `stay_base` is not an allowed target.

- [ ] **Step 3: Add stay-base target type and methods**

In `app/data/resort_acquisition/models.py`:

```python
ExtractionMethod = Literal[
    "registry",
    "opendatahub",
    "opendatahub_discovery",
    "official_page_llm",
    "wikidata",
    "osm",
    "osm_discovery",
    "dem",
    "official_link_discovery",
    "official_link_llm",
    "bergfex_public_page",
    "stay_base_osm",
    "stay_base_wikidata",
    "stay_base_lift_distance",
    "stay_base_profile_llm",
]

ProposalTargetEntityType = Literal["destination", "ski_area", "stay_base"]
```

In `app/data/resort_acquisition/proposals.py`, update `_get_target_field_path`:

```python
    if target.entity_type == "stay_base":
        stay_base = _find_stay_base_payload(resort_payload, target.entity_id)
        if stay_base is None:
            return None, [
                f"Target stay_base '{target.entity_id}' not found in resort catalog"
            ]
        return _get_field_path(stay_base, field_path), []
```

Add:

```python
def _find_stay_base_payload(
    resort_payload: dict[str, Any],
    stay_base_id: str,
) -> dict[str, Any] | None:
    stay_bases = resort_payload.get("stay_bases")
    if not isinstance(stay_bases, list):
        return None
    for stay_base in stay_bases:
        if not isinstance(stay_base, dict):
            continue
        if stay_base.get("stay_base_id") == stay_base_id:
            return stay_base
    return None
```

- [ ] **Step 4: Add deterministic stay-base extraction tests**

Add tests with mocked payloads:

```python
def test_extract_osm_stay_base_candidates_maps_exact_place_match() -> None:
    candidates = extract_osm_stay_base_candidates(
        resort_id="tignes",
        stay_base={
            "stay_base_id": "tignes-val-claret",
            "name": "Val Claret",
        },
        osm_elements=[
            {
                "type": "node",
                "id": 123,
                "lat": 45.456,
                "lon": 6.902,
                "tags": {"name": "Val Claret", "place": "village"},
            }
        ],
        fetched_at=datetime.now(timezone.utc),
        source_url="https://overpass-api.de/api/interpreter",
    )

    by_field = {candidate.field_path: candidate for candidate in candidates}
    assert by_field["latitude"].proposed_value == 45.456
    assert by_field["longitude"].proposed_value == 6.902
    assert by_field["regional_data_ids.osm_object_id"].proposed_value == "node/123"
```

```python
def test_compute_lift_distance_candidate_uses_nearest_aerialway_station() -> None:
    candidates = extract_lift_distance_candidates(
        resort_id="tignes",
        stay_base={
            "stay_base_id": "tignes-val-claret",
            "name": "Val Claret",
            "latitude": 45.456,
            "longitude": 6.902,
        },
        lift_elements=[
            {
                "type": "node",
                "id": 456,
                "lat": 45.457,
                "lon": 6.903,
                "tags": {"name": "Tufs", "aerialway": "station"},
            }
        ],
        fetched_at=datetime.now(timezone.utc),
        source_url="https://overpass-api.de/api/interpreter",
    )

    by_field = {candidate.field_path: candidate for candidate in candidates}
    assert by_field["nearest_lift_name"].proposed_value == "Tufs"
    assert by_field["nearest_lift_distance_m"].proposed_value < 200
    assert by_field["lift_distance"].proposed_value == "near"
```

- [ ] **Step 5: Implement `stay_bases.py` deterministic helpers**

Create `app/data/resort_acquisition/stay_bases.py` with:

```python
from __future__ import annotations

from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from typing import Any

from app.data.resort_acquisition.models import CandidateFact, SourceReference

EARTH_RADIUS_M = 6_371_000


def extract_osm_stay_base_candidates(
    *,
    resort_id: str,
    stay_base: dict[str, Any],
    osm_elements: list[dict[str, Any]],
    fetched_at: datetime,
    source_url: str,
) -> list[CandidateFact]:
    match = _best_name_match(stay_base["name"], osm_elements)
    if match is None:
        return []
    source = SourceReference(source_type="osm", source_url=source_url)
    target = {"entity_type": "stay_base", "entity_id": stay_base["stay_base_id"]}
    candidates = [
        CandidateFact(
            resort_id=resort_id,
            target=target,
            field_path="latitude",
            proposed_value=match["lat"],
            source=source,
            extraction_method="stay_base_osm",
            fetched_at=fetched_at,
            confidence=0.82,
            evidence=f"OSM {match['type']}/{match['id']} exact name match for {stay_base['name']}",
        ),
        CandidateFact(
            resort_id=resort_id,
            target=target,
            field_path="longitude",
            proposed_value=match["lon"],
            source=source,
            extraction_method="stay_base_osm",
            fetched_at=fetched_at,
            confidence=0.82,
            evidence=f"OSM {match['type']}/{match['id']} exact name match for {stay_base['name']}",
        ),
        CandidateFact(
            resort_id=resort_id,
            target=target,
            field_path="regional_data_ids.osm_object_id",
            proposed_value=f"{match['type']}/{match['id']}",
            source=source,
            extraction_method="stay_base_osm",
            fetched_at=fetched_at,
            confidence=0.82,
            evidence=f"OSM {match['type']}/{match['id']} exact name match for {stay_base['name']}",
        ),
    ]
    return candidates
```

Also implement:

```python
def extract_lift_distance_candidates(
    *,
    resort_id: str,
    stay_base: dict[str, Any],
    lift_elements: list[dict[str, Any]],
    fetched_at: datetime,
    source_url: str,
) -> list[CandidateFact]:
    stay_lat = stay_base.get("latitude")
    stay_lon = stay_base.get("longitude")
    if not isinstance(stay_lat, (int, float)) or not isinstance(stay_lon, (int, float)):
        return []
    nearest = _nearest_lift(stay_lat, stay_lon, lift_elements)
    if nearest is None:
        return []
    distance_m = round(
        _haversine_m(stay_lat, stay_lon, nearest["lat"], nearest["lon"])
    )
    source = SourceReference(source_type="osm", source_url=source_url)
    target = {"entity_type": "stay_base", "entity_id": stay_base["stay_base_id"]}
    evidence = (
        f"Nearest OSM aerialway station '{nearest['name']}' is {distance_m}m "
        f"from {stay_base['name']}."
    )
    return [
        CandidateFact(
            resort_id=resort_id,
            target=target,
            field_path="nearest_lift_name",
            proposed_value=nearest["name"],
            source=source,
            extraction_method="stay_base_lift_distance",
            fetched_at=fetched_at,
            confidence=0.78,
            evidence=evidence,
        ),
        CandidateFact(
            resort_id=resort_id,
            target=target,
            field_path="nearest_lift_distance_m",
            proposed_value=distance_m,
            source=source,
            extraction_method="stay_base_lift_distance",
            fetched_at=fetched_at,
            confidence=0.78,
            evidence=evidence,
        ),
        CandidateFact(
            resort_id=resort_id,
            target=target,
            field_path="lift_distance",
            proposed_value=_lift_bucket(distance_m),
            source=source,
            extraction_method="stay_base_lift_distance",
            fetched_at=fetched_at,
            confidence=0.72,
            evidence=evidence,
        ),
    ]


def _best_name_match(
    name: str,
    elements: list[dict[str, Any]],
) -> dict[str, Any] | None:
    normalized_name = _normalize_name(name)
    for element in elements:
        tags = element.get("tags") or {}
        if _normalize_name(str(tags.get("name", ""))) == normalized_name:
            if isinstance(element.get("lat"), (int, float)) and isinstance(
                element.get("lon"), (int, float)
            ):
                return element
    return None


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat_delta = radians(lat2 - lat1)
    lon_delta = radians(lon2 - lon1)
    origin_lat = radians(lat1)
    destination_lat = radians(lat2)
    haversine = (
        sin(lat_delta / 2) ** 2
        + cos(origin_lat) * cos(destination_lat) * sin(lon_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * asin(sqrt(haversine))


def _lift_bucket(distance_m: float) -> str:
    if distance_m <= 400:
        return "near"
    if distance_m <= 1200:
        return "medium"
    return "far"
```

Keep v1 matching conservative: exact normalized name match only.

- [ ] **Step 6: Add CLI `--scope`**

In `run_catalog_acquisition.py`, add argument:

```python
parser.add_argument(
    "--scope",
    choices=("resort-static", "stay-bases", "full-catalog"),
    default="resort-static",
)
```

Behavior:

- `resort-static`: current behavior.
- `stay-bases`: run only registry context needed plus stay-base extraction.
- `full-catalog`: run current behavior and stay-base extraction.

For this task, wire mocked/testable extraction helpers first. Live Overpass/Wikidata fetch integration can be added in the next task.

- [ ] **Step 7: Run acquisition focused tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_resort_acquisition.py::test_build_proposals_resolves_stay_base_target \
  tests/test_resort_acquisition.py::test_extract_osm_stay_base_candidates_maps_exact_place_match \
  tests/test_resort_acquisition.py::test_compute_lift_distance_candidate_uses_nearest_aerialway_station -q
```

Expected: pass.

---

## Task 6: Wikidata And Profile LLM Stay-Base Proposals

**Files:**
- Modify `app/data/resort_acquisition/stay_bases.py`
- Modify `app/data/resort_acquisition/run_catalog_acquisition.py`
- Modify `app/data/resort_acquisition/reports.py`
- Modify `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing Wikidata/profile tests**

Add:

```python
def test_extract_wikidata_stay_base_candidates_maps_coordinates_and_id() -> None:
    candidates = extract_wikidata_stay_base_candidates(
        resort_id="tignes",
        stay_base={"stay_base_id": "tignes-le-lac", "name": "Tignes le Lac"},
        entity={
            "id": "Q123",
            "labels": {"en": {"value": "Tignes le Lac"}},
            "claims": {
                "P625": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {
                                    "latitude": 45.47,
                                    "longitude": 6.91,
                                }
                            }
                        }
                    }
                ]
            },
        },
        fetched_at=datetime.now(timezone.utc),
    )

    by_field = {candidate.field_path: candidate for candidate in candidates}
    assert by_field["regional_data_ids.wikidata_id"].proposed_value == "Q123"
    assert by_field["latitude"].proposed_value == 45.47
    assert by_field["longitude"].proposed_value == 6.91
```

Add:

```python
def test_validate_stay_base_profile_output_accepts_enum_only_tags() -> None:
    candidates = profile_candidates_from_llm_output(
        resort_id="tignes",
        stay_base={"stay_base_id": "tignes-1800", "name": "Tignes 1800"},
        output={
            "base_type": "satellite_village",
            "access_mode": "walk",
            "atmosphere_tags": ["quiet", "family_friendly"],
            "evidence_summary": "Official tourism text describes a quieter family base.",
            "source_claims": [
                {
                    "url": "https://www.tignes.net/",
                    "claim": "Tignes 1800 is described as a quieter family area.",
                }
            ],
            "confidence": 0.74,
        },
        fetched_at=datetime.now(timezone.utc),
    )

    by_field = {candidate.field_path: candidate for candidate in candidates}
    assert by_field["base_type"].proposed_value == "satellite_village"
    assert by_field["access_mode"].proposed_value == "walk"
    assert by_field["atmosphere_tags"].proposed_value == ["quiet", "family_friendly"]
    assert all(candidate.validation_status == "warning" for candidate in candidates)
```

Use `warning` status for qualitative tags so they remain review-required.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_resort_acquisition.py::test_extract_wikidata_stay_base_candidates_maps_coordinates_and_id \
  tests/test_resort_acquisition.py::test_validate_stay_base_profile_output_accepts_enum_only_tags -q
```

Expected: import failures for missing functions.

- [ ] **Step 3: Implement Wikidata stay-base helper**

In `stay_bases.py`, add:

```python
def extract_wikidata_stay_base_candidates(
    *,
    resort_id: str,
    stay_base: dict[str, Any],
    entity: dict[str, Any],
    fetched_at: datetime,
) -> list[CandidateFact]:
    label = _wikidata_english_label(entity)
    if _normalize_name(label) != _normalize_name(stay_base["name"]):
        return []
    coordinate = _wikidata_coordinate(entity)
    source = SourceReference(
        source_type="wikidata",
        source_url=f"https://www.wikidata.org/wiki/{entity['id']}",
    )
    target = {"entity_type": "stay_base", "entity_id": stay_base["stay_base_id"]}
    candidates = [
        CandidateFact(
            resort_id=resort_id,
            target=target,
            field_path="regional_data_ids.wikidata_id",
            proposed_value=entity["id"],
            source=source,
            extraction_method="stay_base_wikidata",
            fetched_at=fetched_at,
            confidence=0.8,
            evidence=f"Wikidata label '{label}' matched stay base '{stay_base['name']}'.",
        )
    ]
    if coordinate is not None:
        latitude, longitude = coordinate
        candidates.extend(
            [
                CandidateFact(
                    resort_id=resort_id,
                    target=target,
                    field_path="latitude",
                    proposed_value=latitude,
                    source=source,
                    extraction_method="stay_base_wikidata",
                    fetched_at=fetched_at,
                    confidence=0.72,
                    evidence=(
                        f"Wikidata coordinate for '{label}' matched stay base "
                        f"'{stay_base['name']}'."
                    ),
                ),
                CandidateFact(
                    resort_id=resort_id,
                    target=target,
                    field_path="longitude",
                    proposed_value=longitude,
                    source=source,
                    extraction_method="stay_base_wikidata",
                    fetched_at=fetched_at,
                    confidence=0.72,
                    evidence=(
                        f"Wikidata coordinate for '{label}' matched stay base "
                        f"'{stay_base['name']}'."
                    ),
                ),
            ]
        )
    return candidates
```

Implement `_wikidata_english_label` and `_wikidata_coordinate` conservatively.

- [ ] **Step 4: Implement profile validation**

In `stay_bases.py`, define allowed enums:

```python
BASE_TYPES = {
    "resort_center",
    "satellite_village",
    "quiet_village",
    "family_base",
    "premium_base",
    "budget_base",
    "nightlife_base",
}
ACCESS_MODES = {
    "walk",
    "ski_bus",
    "car_recommended",
    "unknown",
}
ATMOSPHERE_TAGS = {
    "quiet",
    "lively",
    "family_friendly",
    "premium",
    "budget_friendly",
    "beginner_friendly",
}
```

Add this function:

```python
def profile_candidates_from_llm_output(
    *,
    resort_id: str,
    stay_base: dict[str, Any],
    output: dict[str, Any],
    fetched_at: datetime,
) -> list[CandidateFact]:
    confidence = float(output.get("confidence", 0))
    if confidence < 0.6:
        return []

    base_type = output.get("base_type")
    access_mode = output.get("access_mode")
    atmosphere_tags = output.get("atmosphere_tags") or []
    if base_type is not None and base_type not in BASE_TYPES:
        return []
    if access_mode is not None and access_mode not in ACCESS_MODES:
        return []
    if not isinstance(atmosphere_tags, list):
        return []
    if any(tag not in ATMOSPHERE_TAGS for tag in atmosphere_tags):
        return []

    evidence = _profile_evidence_text(output)
    source = SourceReference(
        source_type="official",
        source_name="stay-base profile LLM review packet",
    )
    target = {"entity_type": "stay_base", "entity_id": stay_base["stay_base_id"]}
    candidates: list[CandidateFact] = []
    if base_type is not None:
        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                target=target,
                field_path="base_type",
                proposed_value=base_type,
                source=source,
                extraction_method="stay_base_profile_llm",
                fetched_at=fetched_at,
                confidence=confidence,
                evidence=evidence,
                validation_status="warning",
            )
        )
    if access_mode is not None:
        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                target=target,
                field_path="access_mode",
                proposed_value=access_mode,
                source=source,
                extraction_method="stay_base_profile_llm",
                fetched_at=fetched_at,
                confidence=confidence,
                evidence=evidence,
                validation_status="warning",
            )
        )
    if atmosphere_tags:
        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                target=target,
                field_path="atmosphere_tags",
                proposed_value=atmosphere_tags,
                source=source,
                extraction_method="stay_base_profile_llm",
                fetched_at=fetched_at,
                confidence=confidence,
                evidence=evidence,
                validation_status="warning",
            )
        )
    return candidates
```

Requirements:

- rejects unknown enum values by returning no candidates with a validation note, or raises a local validation error caught by the runner.
- emits `CandidateFact` with `validation_status="warning"` for accepted qualitative fields.
- includes evidence summary and source claims in `evidence`.
- requires `confidence >= 0.6`.

- [ ] **Step 5: Add report grouping by stay base**

In `reports.py`, when rendering proposal headers, include target entity:

```text
### `stay_base:tignes-1800` / `profile_tags`
```

Then add a resort/stay-base summary section before field-level details:

```text
## Stay-base review groups

### Tignes / Tignes 1800
- profile tags: warning
- coordinates: new
- nearest lift: changed
```

Keep current field-level output so existing review behavior remains available.

- [ ] **Step 6: Run focused tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_resort_acquisition.py::test_extract_wikidata_stay_base_candidates_maps_coordinates_and_id \
  tests/test_resort_acquisition.py::test_validate_stay_base_profile_output_accepts_enum_only_tags -q
```

Expected: pass.

---

## Task 7: Documentation And Sprint Status

**Files:**
- Modify `PROJECT.md`
- Modify `README.md`
- Modify `docs/engineering-notes.md`

- [ ] **Step 1: Update PROJECT.md**

When implementation is done, change Sprint 33 from `planned` to `completed` or `in progress` depending on actual scope completed.

Include:

- grouped search model with trip options and alternatives
- clickable stay-base alternatives in detail page
- stay-base acquisition scope and adapters
- qualitative tags review-required

- [ ] **Step 2: Update README.md**

Add API note:

```markdown
Search results are recommendation groups. Existing selected stay-base fields remain available for compatibility, and richer clients can inspect `top_option` plus `alternative_options`.
```

Add acquisition command note:

```bash
uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition \
  --scope stay-bases \
  --resort tignes \
  --output-dir artifacts/stay-base-acquisition
```

- [ ] **Step 3: Update engineering notes**

Add durable notes:

- Search ranks trip options but displays groups.
- Alternative stay bases are detail-page previews, not global search filters yet.
- Stay-base acquisition remains review-only and grouped by resort/stay base.
- Qualitative tags are warning/review-required until trusted enough for automated approval.

- [ ] **Step 4: Run focused docs check**

Run:

```bash
git diff --check -- PROJECT.md README.md docs/engineering-notes.md
```

Expected: no whitespace errors.

---

## Final Verification

Run focused backend:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_services.py \
  tests/test_api.py \
  tests/test_repository.py \
  tests/test_catalog_validation.py \
  -q
```

Run acquisition tests:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py -q
```

Run lint:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check \
  app/domain app/data tests/test_services.py tests/test_api.py \
  tests/test_repository.py tests/test_catalog_validation.py tests/test_resort_acquisition.py
```

Run frontend:

```bash
cd frontend && npm test -- App.test.tsx
cd frontend && npm run build
```

Run product smoke:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python - <<'PY'
from fastapi.testclient import TestClient
from app.main import create_app

client = TestClient(create_app())
response = client.get(
    "/api/search",
    params={
        "location": "France",
        "min_price": 120,
        "max_price": 340,
        "stars": 1,
        "skill_level": "intermediate",
        "debug": "true",
    },
)
payload = response.json()
print(response.status_code)
print(payload["results"][0]["resort_name"])
print(payload["results"][0]["top_option"]["stay_base_name"])
print(len(payload["results"][0]["alternative_options"]))
PY
```

Expected:

- status `200`
- first result has `top_option`
- alternatives count is present and stable

Run acquisition smoke after stay-base scope exists:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition \
  --scope stay-bases \
  --resort tignes \
  --skip-llm \
  --output-dir /tmp/stay-base-acquisition-smoke
```

Expected:

- command exits `0` when configured/open sources are reachable
- `proposals.json`, `fetch-log.json`, and `evidence.md` are written
- `evidence.md` groups proposals by resort and stay base
