# Search V3 Trip-Market Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate, score, group, and return normalized trip configurations as one ranked result per trip market.

**Architecture:** Build candidates only from explicit stay-base-to-ski-area access edges, reuse ski-area weather/planning evidence once per request, choose a pass with a separate local pass-fit policy, and group concrete configurations by their stay destination's primary trip-market region. Adapt the existing `search_v2` global components without adding pass or resilience weight.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, pytest, OpenTelemetry helpers already in the repo, Ruff.

---

## Decision Gate Before Execution

- Classification: review-gated
- High-risk domains: ranking, planning evidence, API response, request-path
  performance
- Resolved decisions: one result per trip market; winner-derived score; primary
  ski-area weather only; explicit access; pass selection separate from global
  scoring; resilience measured-not-ranked
- ADR status: ADR 0009 accepted
- Advisory status: design review completed; final feature review deferred until
  client cutover

### Task 1: Define Search V3 Models And Catalog Indexes

**Files:**
- Create: `app/domain/search_v3_models.py`
- Create: `app/domain/catalog_graph.py`
- Create: `tests/test_search_v3_models.py`

- [ ] **Step 1: Write failing response-model tests**

```python
def test_recommendation_group_score_must_match_winner() -> None:
    top = make_trip_configuration(score=0.82)
    with pytest.raises(ValidationError, match="must equal top configuration"):
        RecommendationGroup(
            ski_region_id="example",
            ski_region_name="Example Valley",
            score=0.75,
            top_configuration=top,
            alternative_configurations=[],
        )
```

- [ ] **Step 2: Implement explicit v3 API/domain models**

```python
class AccessSummary(BaseModel):
    ski_area_access_id: str
    mode: SkiAreaAccessMode
    lift_distance: LiftDistance
    nearest_lift_name: str | None
    distance_m: int | None
    duration_minutes: int | None
    is_direct: bool

class PassPriceExample(BaseModel):
    duration_days: int
    audience: str
    amount: float | None
    amount_min: float | None
    amount_max: float | None
    currency: str
    match_kind: Literal["exact_duration", "representative", "unavailable"]

class PassOption(BaseModel):
    lift_pass_product_id: str
    name: str
    validity_scope: LiftPassValidityScope
    accessible_ski_area_ids: list[str]
    accessible_terrain_label: str
    accessible_piste_km: float | None
    price_example: PassPriceExample | None
    pass_fit_score: float = Field(ge=0, le=1)
    tradeoff_summary: str

class AreaResilienceItem(BaseModel):
    ski_area_id: str
    ski_area_name: str
    evidence_profile: PlanningEvidenceProfile | None
    evidence_seasons: int | None
    conditions_summary: str | None

class ResilienceSummary(BaseModel):
    alternative_area_count: int
    evidenced_alternative_count: int
    areas: list[AreaResilienceItem]
    summary: str
    ranking_component: Literal[0] = 0

class TripConfiguration(BaseModel):
    configuration_id: str
    ski_region_id: str
    stay_destination_id: str
    stay_destination_name: str
    stay_base_id: str
    stay_base_name: str
    focus_ski_area_id: str
    focus_ski_area_name: str
    access: AccessSummary
    selected_pass: PassOption
    alternative_passes: list[PassOption]
    resilience: ResilienceSummary
    score: float
    score_components: dict[str, float]
    budget_penalty: float
    travel_effort: TravelEffort | None
    conditions_summary: str
    snow_confidence_score: float
    conditions_score: float
    planning_summary: str | None
    planning_provenance: ProvenanceInfo | None
    planning_evidence_count: int | None
    planning_weather_metrics: WeatherEvidenceMetrics | None
    evidence_quality: ProvenanceInfo
    explanation: SearchExplanation

class RecommendationGroup(BaseModel):
    ski_region_id: str
    ski_region_name: str
    rank: int
    score: float
    top_configuration: TripConfiguration
    alternative_configurations: list[TripConfiguration]

class SearchV3Response(BaseModel):
    results: list[RecommendationGroup]
```

Validate winner score equality, region consistency, unique alternative IDs, and
zero resilience ranking component.

- [ ] **Step 3: Implement immutable catalog indexes**

```python
@dataclass(frozen=True)
class CatalogGraph:
    snapshot: CatalogSnapshot
    regions_by_id: Mapping[str, SkiRegion]
    destinations_by_id: Mapping[str, StayDestination]
    bases_by_id: Mapping[str, StayBase]
    areas_by_id: Mapping[str, SkiArea]
    accesses_by_base_id: Mapping[str, tuple[SkiAreaAccess, ...]]
    domains_by_id: Mapping[str, TerrainDomain]
    passes_by_destination_area: Mapping[
        tuple[str, str], tuple[LiftPassProduct, ...]
    ]
    rentals_by_destination_id: Mapping[str, tuple[RentalDisplayFact, ...]]

    @classmethod
    def from_snapshot(cls, snapshot: CatalogSnapshot) -> "CatalogGraph":
        domains_by_id = {
            item.terrain_domain_id: item for item in snapshot.terrain_domains
        }
        passes_by_destination_area: dict[
            tuple[str, str], list[LiftPassProduct]
        ] = defaultdict(list)
        for product in snapshot.lift_pass_products:
            covered_ids = set(product.valid_ski_area_ids)
            for domain_id in product.terrain_domain_ids:
                covered_ids.update(domains_by_id[domain_id].ski_area_ids)
            for stay_destination_id in product.available_from_stay_destination_ids:
                for ski_area_id in covered_ids:
                    passes_by_destination_area[
                        (stay_destination_id, ski_area_id)
                    ].append(product)
        return cls(
            snapshot=snapshot,
            regions_by_id=MappingProxyType(
                {item.ski_region_id: item for item in snapshot.ski_regions}
            ),
            destinations_by_id=MappingProxyType(
                {
                    item.stay_destination_id: item
                    for item in snapshot.stay_destinations
                }
            ),
            bases_by_id=MappingProxyType(
                {item.stay_base_id: item for item in snapshot.stay_bases}
            ),
            areas_by_id=MappingProxyType(
                {item.ski_area_id: item for item in snapshot.ski_areas}
            ),
            accesses_by_base_id=_group_access_by_base(snapshot.ski_area_access),
            domains_by_id=MappingProxyType(domains_by_id),
            passes_by_destination_area=MappingProxyType(
                {
                    key: tuple(sorted(value, key=lambda item: item.lift_pass_product_id))
                    for key, value in passes_by_destination_area.items()
                }
            ),
            rentals_by_destination_id=_group_rentals_by_destination(
                snapshot.rental_display_facts
            ),
        )
```

Pass indexing includes direct area coverage and areas contained in referenced
terrain domains. Keep all values immutable tuples/mappings for request reuse.

- [ ] **Step 4: Run model/index tests and commit**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_search_v3_models.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/search_v3_models.py app/domain/catalog_graph.py tests/test_search_v3_models.py
git add app/domain/search_v3_models.py app/domain/catalog_graph.py tests/test_search_v3_models.py
git commit -m "feat: define trip market search models"
```

### Task 2: Generate Candidates Only From Explicit Access Edges

**Files:**
- Create: `app/domain/search_v3_candidates.py`
- Create: `tests/test_search_v3_candidates.py`
- Modify: `app/domain/ranking.py`

- [ ] **Step 1: Write tests that reject Cartesian candidates**

```python
def test_candidate_generation_uses_only_explicit_access_edges() -> None:
    graph = graph_with_two_bases_two_areas_and_one_access_each()
    candidates = generate_candidate_seeds(graph, matching_filters())
    assert {
        (candidate.stay_base.stay_base_id, candidate.ski_area.ski_area_id)
        for candidate in candidates
    } == {("base-a", "area-a"), ("base-b", "area-b")}
```

Also test country, quality, budget-flex, ski-area skill level, and access-distance
filters use their new canonical owners.

- [ ] **Step 2: Implement typed candidate seeds**

```python
@dataclass(frozen=True)
class TripConfigurationSeed:
    region: SkiRegion
    stay_destination: StayDestination
    stay_base: StayBase
    ski_area: SkiArea
    access: SkiAreaAccess
    candidate_passes: tuple[LiftPassProduct, ...]
    rental_facts: tuple[RentalDisplayFact, ...]


def generate_candidate_seeds(
    graph: CatalogGraph,
    filters: SearchFilters,
) -> tuple[TripConfigurationSeed, ...]:
    seeds: list[TripConfigurationSeed] = []
    for base in graph.snapshot.stay_bases:
        destination = graph.destinations_by_id[base.stay_destination_id]
        if destination.country.casefold() != filters.location.strip().casefold():
            continue
        if quality_score(base.quality) < filters.stars:
            continue
        if budget_range_penalty(
            base.price_min,
            base.price_max,
            filters.min_price,
            filters.max_price,
            filters.budget_flex,
        ) is None:
            continue
        region = graph.regions_by_id[destination.trip_market_region_id]
        for access in graph.accesses_by_base_id.get(base.stay_base_id, ()):
            area = graph.areas_by_id[access.ski_area_id]
            if filters.skill_level not in area.supported_skill_levels:
                continue
            if not lift_distance_matches(access.lift_distance, filters.lift_distance):
                continue
            products = graph.passes_by_destination_area.get(
                (destination.stay_destination_id, area.ski_area_id), ()
            )
            if not products:
                continue
            seeds.append(
                TripConfigurationSeed(
                    region=region,
                    stay_destination=destination,
                    stay_base=base,
                    ski_area=area,
                    access=access,
                    candidate_passes=products,
                    rental_facts=graph.rentals_by_destination_id.get(
                        destination.stay_destination_id, ()
                    ),
                )
            )
    return tuple(sorted(seeds, key=_candidate_seed_sort_key))
```

Algorithm:

1. Filter stay destinations by country/location.
2. Filter their bases by quality and lodging budget overlap.
3. Follow only indexed access edges.
4. Filter area skill levels and access `lift_distance`.
5. Require at least one pass covering the focus area.
6. Resolve exactly one `trip_market` region from the stay destination.
7. Sort seeds by stable `(region, destination, base, area)` IDs.

Move `skill_level_matches` to operate on `SkiArea` and access-distance helpers to
operate on `SkiAreaAccess`. Leave deprecated wrappers only until Phase 4.

- [ ] **Step 3: Run candidate tests and commit**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_search_v3_candidates.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/search_v3_candidates.py app/domain/ranking.py tests/test_search_v3_candidates.py
git add app/domain/search_v3_candidates.py app/domain/ranking.py tests/test_search_v3_candidates.py
git commit -m "feat: generate access backed trip candidates"
```

### Task 3: Select Passes Without Affecting Global Rank

**Files:**
- Create: `app/domain/pass_selection.py`
- Create: `tests/test_pass_selection.py`

- [ ] **Step 1: Write pass-selection behavior tests**

Cover:

- exact-date duration selects an exact-duration price when available;
- month-only search prefers the product marked default for the selected stay
  destination;
- otherwise higher pass fit wins using coverage and comparable price;
- non-connected pass aggregate metrics remain pass-scoped;
- pass score never appears in global score components;
- stable product ID breaks exact ties.

```python
def test_pass_selection_does_not_mutate_configuration_score() -> None:
    selection = select_pass(
        products=(local_pass(), broad_pass()),
        graph=example_graph(),
        stay_destination_id="destination-a",
        focus_ski_area_id="area-a",
        trip_start_date=None,
        trip_end_date=None,
    )
    assert selection.selected.lift_pass_product_id == "default-local"
    assert "pass_fit" not in GLOBAL_SEARCH_V3_COMPONENTS
```

- [ ] **Step 2: Preserve destination-scoped default-pass fallback**

Validate `default_for_stay_destination_ids` is a subset of
`available_from_stay_destination_ids` and at most one product is default for
each stay destination. The relationship is only a selection fallback; it is not
a global rank bonus.

- [ ] **Step 3: Implement deterministic pass fit**

```python
@dataclass(frozen=True)
class PassSelection:
    selected: PassOption
    alternatives: tuple[PassOption, ...]


def select_pass(
    *,
    products: tuple[LiftPassProduct, ...],
    graph: CatalogGraph,
    stay_destination_id: str,
    focus_ski_area_id: str,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> PassSelection:
    options = tuple(
        _build_pass_option(
            product=product,
            graph=graph,
            stay_destination_id=stay_destination_id,
            focus_ski_area_id=focus_ski_area_id,
            trip_start_date=trip_start_date,
            trip_end_date=trip_end_date,
            peer_products=products,
        )
        for product in products
    )
    ordered = sorted(options, key=_pass_option_sort_key)
    return PassSelection(selected=ordered[0], alternatives=tuple(ordered[1:4]))
```

Implement `_build_pass_option()` from the exact duration/coverage rules below.
Implement `_pass_option_sort_key()` as descending pass-fit, then whether the
selected stay destination occurs in `default_for_stay_destination_ids`, then
stable product ID; never read the global configuration score.

For exact dates, compare only adult prices with matching inclusive duration;
when exact examples are unavailable, mark price unavailable rather than implying
a tariff. Normalize accessible piste kilometers and exact comparable price among
the candidate products, using `0.6 * coverage + 0.4 * price`. For month-only
search, select the single default covering product; if none, use coverage then
stable ID. Return at most three meaningful alternatives. The pass-fit score is
serialized but never passed to global scoring.

- [ ] **Step 4: Run tests and commit**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_pass_selection.py tests/test_catalog_models.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/pass_selection.py app/domain/catalog.py tests/test_pass_selection.py
git add app/domain/pass_selection.py app/domain/catalog.py tests/test_pass_selection.py tests/test_catalog_models.py
git commit -m "feat: select recommended lift pass"
```

### Task 4: Adapt Search V2 Global Scoring To Canonical Owners

**Files:**
- Create: `app/domain/search_v3_scoring.py`
- Create: `tests/test_search_v3_scoring.py`
- Modify: `app/domain/resort_fit.py`
- Reference: `app/domain/search_scoring.py`

- [ ] **Step 1: Characterize existing component values**

Create a generic fixture with known quality, terrain, skill, access, snow,
conditions, budget, and travel values. Assert the adapted function returns the
same component names and values as `candidate_score_for_result` for equivalent
inputs.

- [ ] **Step 2: Implement input-based scoring without legacy `SearchResult`**

```python
@dataclass(frozen=True)
class SearchV3ScoreInputs:
    lodging_quality: int
    terrain_scale: str | None
    terrain_trust_cap: float
    skill_fit: tuple[str, ...]
    skill_trust_cap: float
    access_fit: str | None
    access_trust_cap: float
    snow_confidence_score: float
    conditions_score: float
    budget_penalty: float
    travel_effort_score: float | None


@dataclass(frozen=True)
class SearchV3ScoreBreakdown:
    components: Mapping[str, float]
    total: float


GLOBAL_SEARCH_V3_COMPONENTS = frozenset({
    "legacy_base",
    "terrain",
    "skill_fit",
    "stay_base_access",
    "snow_evidence",
    "conditions",
    "budget",
    "travel_effort",
})


def score_search_v3_configuration(
    inputs: SearchV3ScoreInputs,
) -> SearchV3ScoreBreakdown:
    components = {
        "legacy_base": inputs.lodging_quality * 0.12,
        "terrain": TERRAIN_COMPONENT.get(inputs.terrain_scale or "", 0.0)
        * inputs.terrain_trust_cap,
        "skill_fit": skill_component(inputs.skill_fit) * inputs.skill_trust_cap,
        "stay_base_access": ACCESS_COMPONENT.get(inputs.access_fit or "", 0.0)
        * inputs.access_trust_cap,
        "snow_evidence": inputs.snow_confidence_score * 0.35,
        "conditions": inputs.conditions_score * 0.25,
        "budget": -inputs.budget_penalty,
        "travel_effort": 0.0
        if inputs.travel_effort_score is None
        else -(1 - inputs.travel_effort_score) * 0.35,
    }
    return SearchV3ScoreBreakdown(
        components=MappingProxyType(components),
        total=sum(components.values()),
    )
```

Do not add pass or resilience components, directly or indirectly. Derive the
terrain factor from the focus `SkiArea` or its physically connected
`TerrainDomain`, never from the selected pass or pass-accessible aggregate.
Derive skill factors from `SkiArea` and access factors from `SkiAreaAccess`
while preserving existing trust caps. Add a test proving that changing only the
selected pass leaves the total score and every component unchanged.

Move the exact constants and helper formulas required by v3 into
`search_v3_scoring.py`; do not import a breakdown type or policy from the
ranking-comparison diagnostics that Phase 4 deletes.

- [ ] **Step 3: Run equivalence and absence tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_search_v3_scoring.py tests/test_resort_fit.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/search_v3_scoring.py app/domain/resort_fit.py tests/test_search_v3_scoring.py
```

Assert component keys are exactly:

```python
{
    "legacy_base",
    "terrain",
    "skill_fit",
    "stay_base_access",
    "snow_evidence",
    "conditions",
    "budget",
    "travel_effort",
}
```

- [ ] **Step 4: Commit scoring adaptation**

```bash
git add app/domain/search_v3_scoring.py app/domain/resort_fit.py tests/test_search_v3_scoring.py
git commit -m "feat: adapt scoring to normalized trip configurations"
```

### Task 5: Extract Reusable Ski-Area Planning Evidence

**Files:**
- Create: `app/domain/search_evidence.py`
- Modify: `app/domain/search_service.py:81-768`
- Create: `tests/test_search_evidence.py`
- Modify: `tests/test_search_climatology.py`

- [ ] **Step 1: Add characterization tests around evidence caching**

Test one ski area's planning context is built once even when multiple bases
access it, climatology precedes raw archive, raw archive precedes snapshot
fallback, and all repository lookups use `ski_area_id`.

- [ ] **Step 2: Move evidence preload/build helpers without changing formulas**

Expose:

```python
@dataclass(frozen=True)
class SkiAreaPlanningContext:
    conditions: ResortConditions
    conditions_provenance: ProvenanceInfo
    planning_summary: str | None
    planning_provenance: ProvenanceInfo | None
    planning_evidence_count: int | None
    planning_weather_metrics: WeatherEvidenceMetrics | None
    best_travel_months: tuple[int, ...]


def load_planning_contexts(
    *,
    ski_areas: tuple[SkiArea, ...],
    filters: SearchFilters,
    conditions_provider: ConditionsProvider,
    condition_history_repository: ConditionHistoryProtocol,
    raw_weather_history_repository: RawWeatherHistoryProtocol,
    snow_climatology_repository: SnowClimatologyProtocol,
) -> dict[str, SkiAreaPlanningContext]:
    raw_cache = preload_raw_weather_for_areas(
        ski_areas=ski_areas,
        filters=filters,
        repository=raw_weather_history_repository,
    )
    climatology_cache = preload_climatology_for_areas(
        ski_areas=ski_areas,
        filters=filters,
        repository=snow_climatology_repository,
    )
    snapshot_cache = preload_snapshot_fallback_for_areas(
        ski_areas=ski_areas,
        filters=filters,
        repository=condition_history_repository,
        raw_cache=raw_cache,
        climatology_cache=climatology_cache,
    )
    return {
        area.ski_area_id: build_ski_area_planning_context(
            area=area,
            filters=filters,
            conditions_provider=conditions_provider,
            raw_cache=raw_cache,
            climatology_cache=climatology_cache,
            snapshot_cache=snapshot_cache,
        )
        for area in ski_areas
    }
```

Move code mechanically from `search_service.py`; do not retune planning or
weather policy.

- [ ] **Step 3: Run characterization tests and commit**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_search_evidence.py tests/test_search_climatology.py tests/test_planning.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/search_evidence.py app/domain/search_service.py tests/test_search_evidence.py
git add app/domain/search_evidence.py app/domain/search_service.py tests/test_search_evidence.py tests/test_search_climatology.py
git commit -m "refactor: isolate ski area planning evidence"
```

### Task 6: Build And Group Trip-Market Results

**Files:**
- Create: `app/domain/search_v3_service.py`
- Create: `tests/test_search_v3_service.py`
- Modify: `app/domain/travel.py`
- Modify: `app/observability/search.py`

- [ ] **Step 1: Write behavior-first service tests**

Cover:

- Tignes and Val d'Isere configurations occupy one trip-market result;
- only explicit access pairs become configurations;
- result score equals winner score;
- alternative configurations may change destination/base/area;
- pass alternatives remain inside one configuration;
- resilience lists member evidence but has ranking component zero;
- rental facts do not multiply candidates;
- sorting is stable without asserting one real resort must always outrank another.

- [ ] **Step 2: Implement resilience derivation**

```python
def build_resilience_summary(
    *,
    selected_pass: PassOption,
    focus_ski_area_id: str,
    graph: CatalogGraph,
    planning_contexts: Mapping[str, SkiAreaPlanningContext],
) -> ResilienceSummary:
    items = [
        AreaResilienceItem(
            ski_area_id=area_id,
            ski_area_name=graph.areas_by_id[area_id].name,
            evidence_profile=(
                planning_contexts[area_id].planning_provenance.evidence_profile
                if planning_contexts[area_id].planning_provenance is not None
                else None
            ),
            evidence_seasons=planning_contexts[area_id].planning_evidence_count,
            conditions_summary=planning_contexts[area_id].conditions.weather_summary,
        )
        for area_id in selected_pass.accessible_ski_area_ids
        if area_id != focus_ski_area_id and area_id in planning_contexts
    ]
    return ResilienceSummary(
        alternative_area_count=len(selected_pass.accessible_ski_area_ids) - 1,
        evidenced_alternative_count=sum(
            item.evidence_seasons is not None and item.evidence_seasons > 0
            for item in items
        ),
        areas=items[:4],
        summary=_resilience_summary_text(items),
        ranking_component=0,
    )
```

Return bounded member facts and a deterministic summary. Do not average snow,
conditions, evidence seasons, or weather metrics. Set `ranking_component=0`.

- [ ] **Step 3: Implement service orchestration**

```python
def search_trip_markets(
    filters: SearchFilters,
    *,
    catalog_repository: CatalogRepository | None = None,
    conditions_provider: ConditionsProvider | None = None,
    condition_history_repository: ConditionHistoryProtocol | None = None,
    raw_weather_history_repository: RawWeatherHistoryProtocol | None = None,
    snow_climatology_repository: SnowClimatologyProtocol | None = None,
) -> list[RecommendationGroup]:
    repository = catalog_repository or CatalogRepository()
    graph = CatalogGraph.from_snapshot(repository.get_snapshot())
    seeds = generate_candidate_seeds(graph, filters)
    planning_contexts = load_planning_contexts(
        ski_areas=tuple(
            {seed.ski_area.ski_area_id: seed.ski_area for seed in seeds}.values()
        ),
        filters=filters,
        conditions_provider=conditions_provider or get_conditions_provider(),
        condition_history_repository=(
            condition_history_repository or get_condition_history_repository()
        ),
        raw_weather_history_repository=(
            raw_weather_history_repository or get_raw_weather_history_repository()
        ),
        snow_climatology_repository=(
            snow_climatology_repository or get_snow_climatology_repository()
        ),
    )
    configurations = [
        build_trip_configuration(seed, graph, filters, planning_contexts)
        for seed in seeds
    ]
    return rank_and_group_configurations(configurations)
```

Sequence:

1. Load one `CatalogSnapshot` and build one `CatalogGraph`.
2. Generate access-backed seeds.
3. Preload each candidate ski area's evidence once.
4. Compute travel effort once per stay destination.
5. Select pass and derive terrain source.
6. Adapt existing global score components.
7. Build one configuration per `(stay_base_id, focus_ski_area_id)`.
8. Group by `ski_region_id`, choose the highest score, and retain at most three
   materially different alternatives.
9. Assign ranks after stable descending sort.

Update travel helpers to accept a small destination protocol containing name,
country, latitude, and longitude instead of the legacy `Destination` class.

- [ ] **Step 4: Add bounded telemetry**

Record `search_model=search_v3`, candidate seed count, configuration count,
trip-market group count, and evidence profile counts. Never label metrics by
region/base/area IDs.

- [ ] **Step 5: Run service tests and commit**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_search_v3_service.py tests/test_search_evidence.py tests/test_observability_search.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/search_v3_service.py app/domain/travel.py app/observability/search.py tests/test_search_v3_service.py
git add app/domain/search_v3_service.py app/domain/travel.py app/observability/search.py tests/test_search_v3_service.py
git commit -m "feat: rank trip market recommendation groups"
```

### Task 7: Expose Search V3 Through The Backend Contract

**Files:**
- Modify: `app/domain/search_models.py`
- Modify: `app/domain/models.py:1603-1638`
- Modify: `app/api/routes.py:55-187`
- Modify: `tests/test_search_models.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Update model-selection tests first**

During Phase 3, allow `search_v3` and make it the configured default while old
service tests still exist. Assert explicit invalid/retired versions receive 422
after Phase 4 removes them.

- [ ] **Step 2: Route `/api/search` to structured v3 results**

```python
class SearchResponse(BaseModel):
    results: list[RecommendationGroup]


def _search_v3_response(
    filters: SearchFilters,
    selection: SearchModelSelection,
    *,
    debug: bool,
) -> SearchResponse | DebugSearchV3Response:
    results = search_trip_markets(filters)
    if debug:
        return DebugSearchV3Response(
            results=results,
            debug=SearchDebugInfo.from_selection(selection),
        )
    return SearchResponse(results=results)
```

After the existing query parameters are validated and converted to
`SearchFilters`, call `_search_v3_response(filters, selection, debug=debug)`.

Keep debug metadata for configured/requested/effective model, but return the same
group result contract in normal and debug responses.

- [ ] **Step 3: Replace API assertions with semantic v3 contract tests**

Assert stable IDs, one result per trip market, winner score inheritance,
selected-area evidence, nested passes, and zero resilience ranking component.
Do not assert a permanently fixed ranking among named real resorts.

- [ ] **Step 4: Run backend search verification and commit**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_search_models.py \
  tests/test_search_v3_models.py \
  tests/test_search_v3_candidates.py \
  tests/test_pass_selection.py \
  tests/test_search_v3_scoring.py \
  tests/test_search_evidence.py \
  tests/test_search_v3_service.py \
  tests/test_api.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain app/api/routes.py tests/test_search_v3*.py tests/test_pass_selection.py tests/test_api.py
git add app/domain/search_models.py app/domain/models.py app/api/routes.py tests/test_search_models.py tests/test_api.py
git commit -m "feat: expose search v3 recommendation groups"
```

### Task 8: Verify The Search V3 Phase

- [ ] **Step 1: Run focused backend regression suites**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_services.py \
  tests/test_planning.py \
  tests/test_search_climatology.py \
  tests/test_resort_fit.py \
  tests/test_search_v3_models.py \
  tests/test_search_v3_candidates.py \
  tests/test_pass_selection.py \
  tests/test_search_v3_scoring.py \
  tests/test_search_evidence.py \
  tests/test_search_v3_service.py \
  tests/test_api.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
git diff --check
```

Expected: backend v3 contract passes; frontend/mobile are intentionally updated
in Phase 4 before any deployment.

- [ ] **Step 2: Run a local API smoke request**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config uvicorn app.main:app --port 8011
curl -sS 'http://127.0.0.1:8011/api/search?location=France&min_price=140&max_price=320&stars=1&skill_level=intermediate&travel_month=3' | jq '.results[] | {region:.ski_region_name,stay:.top_configuration.stay_base_name,area:.top_configuration.focus_ski_area_name,pass:.top_configuration.selected_pass.name,seasons:.top_configuration.planning_evidence_count}'
```

Expected: distinct trip markets, concrete winning configurations, and no pass
or resilience key inside `score_components`.
