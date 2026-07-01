# Normalized Catalog Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a versioned, fully validated normalized catalog and migrate current static data into it without changing runtime persistence or search yet.

**Architecture:** Define catalog-only Pydantic models in a focused module, load one `catalog.json` into a `CatalogSnapshot`, and validate all cross-entity references before use. A temporary deterministic converter plus an explicit reviewed override file flatten the current nested files; both remain until the final cutover proves parity.

**Tech Stack:** Python 3.12, Pydantic v2, JSON, pytest, Ruff.

---

## Decision Gate Before Execution

- Classification: review-gated
- High-risk domains: catalog truth, source trust, stable IDs, future search input
- Resolved decisions: normalized top-level entities; one file; explicit access;
  `TerrainDomain` only for connected terrain; pass-scoped metrics for
  non-connected pass aggregates
- ADR status: ADR 0009 accepted
- Advisory status: covered by accepted design review

### Task 1: Define The Normalized Catalog Models

**Files:**
- Create: `app/domain/catalog.py`
- Create: `tests/test_catalog_models.py`
- Reference: `app/domain/models.py:90-676`

- [ ] **Step 1: Write a valid minimal-catalog fixture and failing load test**

```python
from app.domain.catalog import CatalogSnapshot


def minimal_catalog_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "ski_regions": [
            {
                "ski_region_id": "example",
                "name": "Example Valley",
                "grouping_policy": "trip_market",
            }
        ],
        "stay_destinations": [
            {
                "stay_destination_id": "example",
                "name": "Example",
                "country": "France",
                "region": "Savoie",
                "price_level": "mid",
                "latitude": 45.0,
                "longitude": 6.0,
                "trip_market_region_id": "example",
            }
        ],
        "stay_bases": [
            {
                "stay_base_id": "example-village",
                "stay_destination_id": "example",
                "name": "Example Village",
                "price_range": "EUR 150-220",
                "price_min": 150,
                "price_max": 220,
                "quality": "standard",
            }
        ],
        "ski_areas": [
            {
                "ski_area_id": "example-area",
                "name": "Example Area",
                "latitude": 45.01,
                "longitude": 6.01,
                "base_elevation_m": 1200,
                "summit_elevation_m": 2400,
                "season_start_month": 12,
                "season_end_month": 4,
                "supported_skill_levels": ["intermediate"],
            }
        ],
        "ski_area_access": [
            {
                "ski_area_access_id": "example-village--example-area",
                "stay_base_id": "example-village",
                "ski_area_id": "example-area",
                "access_mode": "walk",
                "lift_distance": "near",
                "nearest_lift_name": "Example Gondola",
                "distance_m": 300,
                "is_direct": True,
                "source_urls": ["https://www.openstreetmap.org/way/1"],
            }
        ],
        "terrain_domains": [],
        "lift_pass_products": [
            {
                "lift_pass_product_id": "example-local-pass",
                "name": "Example Local Pass",
                "validity_scope": "single_ski_area",
                "available_from_stay_destination_ids": ["example"],
                "default_for_stay_destination_ids": ["example"],
                "valid_ski_area_ids": ["example-area"],
                "terrain_domain_ids": [],
                "prices": [],
            }
        ],
        "rental_display_facts": [],
    }


def test_catalog_snapshot_accepts_a_complete_graph() -> None:
    snapshot = CatalogSnapshot.model_validate(minimal_catalog_payload())
    assert snapshot.schema_version == 1
    assert snapshot.stay_destinations[0].trip_market_region_id == "example"
```

- [ ] **Step 2: Run the test and verify the module is missing**

Run: `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_models.py::test_catalog_snapshot_accepts_a_complete_graph -q`

Expected: FAIL with `ModuleNotFoundError: app.domain.catalog`.

- [ ] **Step 3: Implement catalog entity types and field ownership**

Create these public types in `app/domain/catalog.py`:

```python
CatalogSchemaVersion = Literal[1]
SkiRegionGroupingPolicy = Literal["trip_market", "regional_network"]
SkiAreaAccessMode = Literal[
    "walk", "ski_bus", "drive", "ski_in_ski_out", "mixed", "unknown"
]
TerrainMetricScope = Literal["aggregate", "pass_accessible"]

class SkiRegion(BaseModel):
    ski_region_id: str
    name: str
    grouping_policy: SkiRegionGroupingPolicy
    parent_ski_region_id: str | None = None
    source_urls: list[str] = Field(default_factory=list)

class StayDestination(BaseModel):
    stay_destination_id: str
    name: str
    country: str
    region: str
    price_level: PriceLevel
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    trip_market_region_id: str
    atmosphere_tags: list[str] = Field(default_factory=list)
    regional_data_ids: dict[str, str] = Field(default_factory=dict)

class StayBase(BaseModel):
    stay_base_id: str
    stay_destination_id: str
    name: str
    price_range: str
    price_min: float
    price_max: float
    quality: Quality
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    base_type: str | None = None
    atmosphere_tags: list[str] = Field(default_factory=list)
    regional_data_ids: dict[str, str] = Field(default_factory=dict)

class SkiArea(BaseModel):
    ski_area_id: str
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    base_elevation_m: int = Field(ge=0)
    summit_elevation_m: int = Field(ge=0)
    season_start_month: int = Field(ge=1, le=12)
    season_end_month: int = Field(ge=1, le=12)
    season_windows: list[SeasonWindow] = Field(default_factory=list)
    total_piste_km: float | None = Field(default=None, ge=0)
    total_lift_count: int | None = Field(default=None, ge=0)
    piste_km_by_difficulty: PisteKmByDifficulty | None = None
    supported_skill_levels: list[SkillLevel] = Field(default_factory=list)

class SkiAreaAccess(BaseModel):
    ski_area_access_id: str
    stay_base_id: str
    ski_area_id: str
    access_mode: SkiAreaAccessMode
    lift_distance: LiftDistance
    nearest_lift_name: str | None = None
    distance_m: int | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, ge=0)
    is_direct: bool
    regional_data_ids: dict[str, str] = Field(default_factory=dict)
    source_urls: list[str] = Field(min_length=1)

class AggregateTerrainMetrics(BaseModel):
    metric_scope: Literal["pass_accessible"] = "pass_accessible"
    total_piste_km: float | None = Field(default=None, ge=0)
    total_lift_count: int | None = Field(default=None, ge=0)
    piste_km_by_difficulty: PisteKmByDifficulty | None = None
    source_urls: list[str] = Field(min_length=1)

class TerrainDomain(BaseModel):
    terrain_domain_id: str
    name: str
    ski_area_ids: list[str] = Field(min_length=2)
    metric_scope: Literal["aggregate"] = "aggregate"
    total_piste_km: float | None = Field(default=None, ge=0)
    total_lift_count: int | None = Field(default=None, ge=0)
    base_elevation_m: int | None = Field(default=None, ge=0)
    summit_elevation_m: int | None = Field(default=None, ge=0)
    piste_km_by_difficulty: PisteKmByDifficulty | None = None
    season_windows: list[SeasonWindow] = Field(default_factory=list)
    source_urls: list[str] = Field(min_length=1)

class LiftPassProduct(BaseModel):
    lift_pass_product_id: str
    name: str
    validity_scope: LiftPassValidityScope
    available_from_stay_destination_ids: list[str] = Field(min_length=1)
    default_for_stay_destination_ids: list[str] = Field(default_factory=list)
    valid_ski_area_ids: list[str] = Field(default_factory=list)
    terrain_domain_ids: list[str] = Field(default_factory=list)
    external_validity_summary: str | None = None
    pass_accessible_terrain: AggregateTerrainMetrics | None = None
    prices: list[LiftPassPrice] = Field(default_factory=list)

class RentalDisplayFact(BaseModel):
    rental_display_fact_id: str
    stay_destination_id: str
    stay_base_id: str | None = None
    name: str
    price_range: str
    price_min: float
    price_max: float
    quality: Quality
    lift_distance: LiftDistance
```

Reuse `SeasonWindow`, `PisteKmByDifficulty`, `LiftPassPrice`, and shared literal
types from `app.domain.models` during this phase. Move them only during the final
cleanup; do not duplicate validation logic.

- [ ] **Step 4: Add failing graph-invariant tests**

Cover duplicate IDs, unknown references, non-trip-market destination grouping,
region parent cycles, duplicate access pairs, inaccessible bases/areas, unknown
pass/domain references, invalid single-area pass shape, and rental owner mismatch.

```python
def test_catalog_rejects_unknown_access_area() -> None:
    payload = minimal_catalog_payload()
    payload["ski_area_access"][0]["ski_area_id"] = "missing"
    with pytest.raises(ValidationError, match="unknown ski_area_id: missing"):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_destination_without_trip_market_region() -> None:
    payload = minimal_catalog_payload()
    payload["ski_regions"][0]["grouping_policy"] = "regional_network"
    with pytest.raises(ValidationError, match="must reference a trip_market"):
        CatalogSnapshot.model_validate(payload)
```

- [ ] **Step 5: Implement `CatalogSnapshot` cross-reference validation**

```python
class CatalogSnapshot(BaseModel):
    schema_version: CatalogSchemaVersion
    ski_regions: list[SkiRegion]
    stay_destinations: list[StayDestination]
    stay_bases: list[StayBase]
    ski_areas: list[SkiArea]
    ski_area_access: list[SkiAreaAccess]
    terrain_domains: list[TerrainDomain]
    lift_pass_products: list[LiftPassProduct]
    rental_display_facts: list[RentalDisplayFact]

    @model_validator(mode="after")
    def validate_graph(self) -> "CatalogSnapshot":
        # Build one ID set per entity type and reject duplicates.
        # Validate region parents and reject parent cycles.
        # Require every stay destination to reference a trip_market region.
        # Validate base -> destination and access -> base/area references.
        # Reject duplicate (stay_base_id, ski_area_id) access pairs.
        # Require every active base and area to occur in at least one access edge.
        # Validate terrain-domain members, pass availability/default destination
        # references, and pass area/domain coverage references.
        # Require defaults to be a subset of availability and at most one
        # default product per stay destination.
        # Require each pass to cover at least one area directly or by domain.
        # Validate rental destination/base ownership.
        return self
```

Implement each comment as a small private helper returning precise IDs in error
messages. Validate direct URLs with `validate_direct_external_http_url`.

- [ ] **Step 6: Run model tests and lint**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_models.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/catalog.py tests/test_catalog_models.py
```

Expected: all tests and Ruff pass.

- [ ] **Step 7: Commit the catalog contract**

```bash
git add app/domain/catalog.py tests/test_catalog_models.py
git commit -m "feat: define normalized catalog contract"
```

### Task 2: Add The Catalog Loader And Validation CLI

**Files:**
- Create: `app/data/catalog_loader.py`
- Create: `app/data/validate_catalog.py`
- Create: `tests/fixtures/minimal-catalog.json`
- Create: `tests/test_catalog_loader_v2.py`
- Modify: `app/data/__init__.py`

- [ ] **Step 1: Write failing loader tests**

```python
def test_load_catalog_from_path_returns_validated_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(minimal_catalog_payload()), encoding="utf-8")
    snapshot = load_catalog_from_path(path)
    assert snapshot.ski_areas[0].ski_area_id == "example-area"


def test_load_catalog_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    payload = minimal_catalog_payload()
    payload["schema_version"] = 2
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValidationError, match="schema_version"):
        load_catalog_from_path(path)
```

- [ ] **Step 2: Implement the loader and canonical path**

```python
CATALOG_PATH = Path(__file__).with_name("catalog.json")


def load_catalog_from_path(path: Path) -> CatalogSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CatalogSnapshot.model_validate(payload)


@lru_cache(maxsize=1)
def load_catalog() -> CatalogSnapshot:
    return load_catalog_from_path(CATALOG_PATH)
```

The CLI accepts `--catalog-path`, prints bounded entity counts, and exits nonzero
on JSON/Pydantic failure. It must not access or mutate the database.

- [ ] **Step 3: Run focused tests, a CLI smoke test, and lint**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_loader_v2.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path tests/fixtures/minimal-catalog.json
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/catalog_loader.py app/data/validate_catalog.py tests/test_catalog_loader_v2.py
```

Expected: tests pass; CLI reports one region, destination, base, area, access,
and pass.

- [ ] **Step 4: Commit the loader**

```bash
git add app/data/catalog_loader.py app/data/validate_catalog.py app/data/__init__.py tests/test_catalog_loader_v2.py tests/fixtures/minimal-catalog.json
git commit -m "feat: load and validate normalized catalog"
```

### Task 3: Convert Current Catalog Data With Explicit Mapping Overrides

**Files:**
- Create: `app/data/catalog_migration.py`
- Create: `app/data/catalog_migration_overrides.json`
- Create: `app/data/catalog.json`
- Create: `artifacts/catalog-migration/catalog-migration-review.md` (generated,
  inspect locally; do not commit unless explicitly useful)
- Create: `tests/test_catalog_migration.py`
- Read: `app/data/resorts.json`
- Read: `app/data/terrain_domains.json`

- [ ] **Step 1: Write parity tests before generating canonical data**

Assert that conversion preserves all 31 current destination IDs as stay-
destination IDs, 45 stay-base IDs, 36 ski-area IDs, 32 rental rows, all ski-area
season/elevation/terrain values, pass prices, and all three existing terrain-
domain IDs. Assert destination-level season/elevation compatibility copies are
listed as intentionally dropped, and no `TerrainGroup` survives.

```python
def test_conversion_preserves_all_ski_area_ids() -> None:
    legacy = load_resorts_from_path(LEGACY_RESORTS_PATH)
    converted = convert_legacy_catalog(legacy, load_terrain_domains())
    assert {area.ski_area_id for area in converted.ski_areas} == {
        area.ski_area_id for destination in legacy for area in destination.ski_areas
    }


def test_conversion_routes_legacy_terrain_groups_by_meaning() -> None:
    converted = build_converted_catalog()
    assert "kitzsteinhorn-maiskogel" in {
        domain.terrain_domain_id for domain in converted.terrain_domains
    }
    chamonix_pass = next(
        product
        for product in converted.lift_pass_products
        if product.lift_pass_product_id == "chamonix-le-pass"
    )
    assert chamonix_pass.pass_accessible_terrain.total_piste_km == 110
```

- [ ] **Step 2: Define reviewed migration overrides**

The override file must explicitly record:

```json
{
  "shared_trip_markets": {
    "tignes-val-disere": ["tignes", "val-disere"],
    "campiglio-dolomiti-di-brenta": [
      "madonna-di-campiglio",
      "pinzolo",
      "folgarida-marilleva"
    ],
    "chamonix-valley": ["chamonix-mont-blanc"]
  },
  "terrain_group_routes": {
    "kitzsteinhorn-maiskogel": "terrain_domain",
    "chamonix-le-pass-terrain": "pass:chamonix-le-pass"
  },
  "shared_pass_ids": {
    "tignes-val-disere-ski-pass": [
      "tignes:tignes-val-disere-ski-pass",
      "val-disere:tignes-val-disere-ski-pass"
    ],
    "campiglio-skiarea-pass": [
      "madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass",
      "pinzolo:pinzolo-campiglio-skiarea-pass",
      "folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass"
    ]
  }
}
```

All other stay destinations receive a one-to-one trip-market region with the
same stable ID. Do not create broad regional-network groups only because a pass
mentions external terrain.

For every single-area destination, generate one access edge from each current
stay base to that area. For multi-area destinations use explicit edges:

- Chamonix base -> Brevent-Flegere;
- Argentiere -> Grands Montets and Balme-Le Tour-Vallorcine;
- Les Houches -> Les Houches-Saint-Gervais;
- Kaprun -> Maiskogel and Kitzsteinhorn;
- Zell am See -> Schmittenhoehe.

Move current nearest-lift/access fields to the direct matching edge. For the
Argentiere-to-Balme secondary edge, complete a focused official/OSM source
review before generation and store the reviewed mode plus direct URLs. If the
edge cannot be sourced, the migration review must stop rather than activating
an estimated search relationship. Apply the same rule to every generated access
edge: it must inherit a direct external source from reviewed catalog/trust data
or be reported as blocked for owner resolution. Do not generate every
base-by-area pair and do not invent source URLs to satisfy validation.

- [ ] **Step 3: Implement deterministic conversion**

`convert_legacy_catalog()` must:

- flatten destination records into stay destinations, bases, and ski areas;
- parse price ranges with the existing loader helper;
- derive ski-area skill levels from existing difficulty facts where possible,
  otherwise use the union of existing destination stay-base levels and retain
  estimated trust;
- construct trip-market regions from overrides plus one-to-one defaults;
- strip destination ownership from ski areas and domains;
- consolidate identical shared passes and merge their availability, default,
  and area/domain coverage relationships;
- move Chamonix pass aggregate metrics onto `chamonix-le-pass`;
- convert Kitzsteinhorn-Maiskogel into a connected terrain domain;
- create stable rental IDs using the existing NFKD/casefold slug policy;
- emit a Markdown review containing entity counts, ID changes, merged passes,
  generated access edges, blocked/unsourced relationships, and dropped fields.

- [ ] **Step 4: Generate and format `catalog.json`**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.catalog_migration \
  --resorts-path app/data/resorts.json \
  --terrain-domains-path app/data/terrain_domains.json \
  --overrides-path app/data/catalog_migration_overrides.json \
  --output-path app/data/catalog.json \
  --report-path artifacts/catalog-migration/catalog-migration-review.md
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog \
  --catalog-path app/data/catalog.json
```

Expected counts: 31 stay destinations, 45 stay bases, 36 ski areas, 28
trip-market regions from the reviewed overrides, no terrain groups, and
unchanged ski-area IDs.

- [ ] **Step 5: Stop for owner review of the migration report**

The owner must inspect every shared trip market, every multi-area access mapping,
all merged pass IDs, both routed terrain groups, and every estimated field. Do
not continue to persistence until the report is approved.

- [ ] **Step 6: Run parity tests and lint**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_models.py tests/test_catalog_loader_v2.py tests/test_catalog_migration.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/catalog.py app/data/catalog_loader.py app/data/catalog_migration.py tests/test_catalog_models.py tests/test_catalog_loader_v2.py tests/test_catalog_migration.py
```

- [ ] **Step 7: Commit normalized canonical data**

```bash
git add app/data/catalog.json app/data/catalog_migration.py app/data/catalog_migration_overrides.json tests/test_catalog_migration.py
git commit -m "data: normalize catalog entities and relationships"
```

Keep the legacy files and converter during Phases 1-3 for parity checks. Phase 4
removes them after the complete application uses `catalog.json`.

### Task 4: Add A Typed Normalized Trust Manifest

**Files:**
- Create: `app/domain/catalog_trust.py`
- Modify: `app/data/resort_trust_manifest.json`
- Create: `tests/test_catalog_trust.py`
- Modify: `app/data/validate_catalog.py`

- [ ] **Step 1: Write failing trust-manifest graph tests**

Test one entry per catalog entity ID, allowed statuses, required external refs for
verified statuses, exact field-group names by entity type, no unknown entity IDs,
and no missing trust entries for ranking-relevant entities.

- [ ] **Step 2: Implement generic typed trust entries**

```python
CatalogEntityType = Literal[
    "ski_regions",
    "stay_destinations",
    "stay_bases",
    "ski_areas",
    "ski_area_access",
    "terrain_domains",
    "lift_pass_products",
    "rental_display_facts",
]

class EntityTrustEntry(BaseModel):
    display_name: str
    field_statuses: dict[str, TrustManifestStatus]
    source_refs: list[str]
    notes: list[str] = Field(default_factory=list)

class CatalogTrustManifest(BaseModel):
    version: str
    catalog_schema_version: Literal[1]
    status_values: list[TrustManifestStatus]
    field_groups: dict[CatalogEntityType, list[str]]
    entities: dict[CatalogEntityType, dict[str, EntityTrustEntry]]
```

Add `validate_against_catalog(snapshot)` so verified/adjusted fields require a
direct external source and entity IDs match the snapshot. Keep estimates honest;
do not upgrade statuses during mechanical conversion.

- [ ] **Step 3: Convert current trust entries deterministically**

Map destination-level statuses to their new owners using the field-ownership
table in the accepted spec. Split `stay_base_lift_distance` into individual
access entries. Route Chamonix terrain-group trust to the pass and
Kitzsteinhorn-Maiskogel trust to the new terrain domain. Preserve source refs and
notes, but do not treat internal sprint docs as sufficient evidence for verified
status.

- [ ] **Step 4: Validate canonical catalog and manifest together**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog \
  --catalog-path app/data/catalog.json \
  --trust-manifest-path app/data/resort_trust_manifest.json
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_trust.py tests/test_catalog_validation.py -q
```

Expected: canonical validation passes; legacy validation remains green until its
removal in Phase 4.

- [ ] **Step 5: Commit trust migration**

```bash
git add app/domain/catalog_trust.py app/data/resort_trust_manifest.json app/data/validate_catalog.py tests/test_catalog_trust.py
git commit -m "feat: validate normalized catalog trust"
```

### Task 5: Verify The Contract Phase

**Files:**
- Modify: `docs/domain-language.md` only to add a clearly marked accepted-target
  terminology note; full canonical replacement waits for Phase 4

- [ ] **Step 1: Run the complete contract verification**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_models.py \
  tests/test_catalog_loader_v2.py \
  tests/test_catalog_migration.py \
  tests/test_catalog_trust.py \
  tests/test_catalog_validation.py \
  tests/test_seed_data.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/catalog.py app/domain/catalog_trust.py app/data/catalog_loader.py app/data/catalog_migration.py app/data/validate_catalog.py tests/test_catalog_models.py tests/test_catalog_loader_v2.py tests/test_catalog_migration.py tests/test_catalog_trust.py
git diff --check
```

Expected: all focused tests and lint pass; old runtime search tests are unchanged.

- [ ] **Step 2: Record phase result and commit docs**

Document generated counts, owner-approved mappings, any blocked access
relationships, and the fact that runtime still uses the legacy repository until
Phase 2.

```bash
git add docs/domain-language.md
git commit -m "docs: record normalized catalog target terminology"
```
