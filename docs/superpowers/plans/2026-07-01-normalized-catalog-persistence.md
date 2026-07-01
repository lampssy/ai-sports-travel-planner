# Normalized Catalog Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist the normalized catalog graph and expose it through a repository without deleting or rekeying any retained ski-area evidence.

**Architecture:** Expand the existing PostgreSQL schema with normalized tables and relationship columns while temporarily retaining legacy catalog-owner columns during branch development. Rename legacy evidence key columns from `resort_id` to `ski_area_id` in place, synchronize one validated `CatalogSnapshot` transactionally, retire missing entities with `is_active`, and keep the existing `ski_areas.id` surrogate primary key plus the stable unique `ski_area_id` evidence key so evidence rows are never rekeyed.

**Tech Stack:** Python 3.12, psycopg 3, PostgreSQL, Pydantic v2, pytest, Ruff.

---

## Decision Gate Before Execution

- Classification: review-gated
- High-risk domains: schema migration, catalog sync, historical evidence,
  request-path repository reads
- Resolved decisions: use explicit normalized tables; preserve ski-area IDs;
  inactive retirement instead of deletion; no production deployment until full
  client cutover
- ADR status: ADR 0009 accepted
- Advisory status: covered by design review; release/ops feature review occurs
  after the final phase

### Task 1: Expand The Catalog Schema Without Rekeying Ski Areas

**Files:**
- Create: `app/data/catalog_schema.py`
- Modify: `app/data/database.py:70-1129`
- Modify: `app/data/repositories.py:45-1370`
- Modify: `app/domain/models.py:677-915`
- Create: `tests/test_catalog_schema_v2.py`
- Modify: `tests/test_repository.py`

- [ ] **Step 1: Write failing fresh-schema assertions**

```python
def test_normalized_catalog_schema_has_expected_tables_and_keys() -> None:
    ensure_normalized_catalog_schema()
    with connect() as connection:
        tables = {
            row["table_name"]
            for row in connection.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            ).fetchall()
        }
        ski_area_keys = connection.execute(
            """
            SELECT a.attname, i.indisprimary, i.indisunique
            FROM pg_index i
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = 'ski_areas'::regclass
              AND (i.indisprimary OR i.indisunique)
            """
        ).fetchall()

    assert {
        "ski_regions",
        "stay_destinations",
        "ski_area_access",
        "lift_pass_products",
        "lift_pass_ski_areas",
        "lift_pass_terrain_domains",
        "terrain_domain_ski_areas",
        "rental_display_facts",
    } <= tables
    assert any(
        row["attname"] == "id" and row["indisprimary"]
        for row in ski_area_keys
    )
    assert any(
        row["attname"] == "ski_area_id" and row["indisunique"]
        for row in ski_area_keys
    )
```

- [ ] **Step 2: Implement idempotent schema creation**

Create focused functions in `catalog_schema.py`:

```python
def ensure_normalized_catalog_schema(database_url: str | None = None) -> None:
    with connect(database_url) as connection:
        _create_normalized_catalog_tables(connection)
        _expand_legacy_catalog_tables(connection)
        _rename_ski_area_evidence_keys(connection)
        _protect_ski_area_evidence_foreign_keys(connection)


def _expand_legacy_catalog_tables(connection: Connection[Any]) -> None:
    connection.execute(
        "ALTER TABLE stay_bases ADD COLUMN IF NOT EXISTS "
        "stay_destination_id TEXT"
    )
    # Keep resort_id only until Phase 4 so branch-level old tests can coexist.
```

Normalized table shape:

- `ski_regions(ski_region_id PK, name, grouping_policy,
  parent_ski_region_id FK nullable, source_urls_json, is_active)`;
- `stay_destinations(stay_destination_id PK, name, country, region,
  price_level, latitude, longitude, trip_market_region_id FK,
  atmosphere_tags_json, regional_data_ids_json, is_active)`;
- existing `stay_bases` gains `stay_destination_id`; stable `stay_base_id`
  remains unique and becomes the relationship key;
- existing `ski_areas` retains `ski_area_id` and weather columns; `resort_id`
  remains temporary until Phase 4 but is not used by the new repository;
- `ski_area_access(ski_area_access_id PK, stay_base_id FK,
  ski_area_id FK, access fields, source/regional IDs, is_active,
  UNIQUE(stay_base_id, ski_area_id))`;
- `terrain_domains(terrain_domain_id PK, name, metric_scope,
  total_piste_km, total_lift_count, base_elevation_m, summit_elevation_m,
  piste_km_by_difficulty_json, season_windows_json, source_urls_json,
  is_active)` plus
  `terrain_domain_ski_areas(terrain_domain_id, ski_area_id, ordinal)`;
- `lift_pass_products(lift_pass_product_id PK, name, validity_scope,
  external_validity_summary, pass_accessible_terrain_json,
  prices_json, is_active)` plus area/domain join tables;
- `lift_pass_stay_destinations(lift_pass_product_id,
  stay_destination_id, is_default)` stores commercial availability separately
  from terrain coverage;
- `rental_display_facts(rental_display_fact_id PK, stay_destination_id FK,
  stay_base_id nullable FK, display fields, is_active)`.

Rename `raw_weather_history.resort_id` and
`resort_condition_history.resort_id` to `ski_area_id` with idempotent
information-schema guards. Recreate their unique constraints and indexes using
the new column name. Rename `RawWeatherObservation.resort_id` and
`ResortConditionSnapshot.resort_id` to `ski_area_id`, and update repository
method arguments and SQL so no evidence API stores or retrieves a ski-area key
under a resort name. These are key-column renames only; do not update or copy
evidence rows.

Keep archive, climatology, current-condition, and condition-history foreign
keys pointing to the same `ski_areas(ski_area_id)` table with
`ON DELETE RESTRICT`.

- [ ] **Step 3: Write and pass idempotency and evidence-FK tests**

Call `ensure_normalized_catalog_schema()` twice and assert no failure. Assert
that all four evidence tables expose `ski_area_id`, neither history table still
exposes `resort_id`, and existing row counts are unchanged. Query
`pg_constraint.confdeltype` for `raw_weather_history`,
`ski_area_snow_climatology_daily`, `resort_conditions`, and
`resort_condition_history`; expect `r` for every ski-area evidence FK.

- [ ] **Step 4: Run focused tests and lint**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_schema_v2.py tests/test_repository.py::test_ski_area_evidence_foreign_keys_do_not_cascade_delete tests/test_repository.py::test_weather_models_and_repositories_use_ski_area_id -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/catalog_schema.py app/data/database.py app/data/repositories.py app/domain/models.py tests/test_catalog_schema_v2.py tests/test_repository.py
```

- [ ] **Step 5: Commit schema expansion**

```bash
git add app/data/catalog_schema.py app/data/database.py app/data/repositories.py app/domain/models.py tests/test_catalog_schema_v2.py tests/test_repository.py
git commit -m "feat: add normalized catalog persistence schema"
```

### Task 2: Implement Transactional Catalog Synchronization

**Files:**
- Create: `app/data/catalog_sync.py`
- Modify: `app/data/database.py:70-103`
- Create: `tests/test_catalog_sync.py`

- [ ] **Step 1: Write a failing sync round-trip test**

```python
def test_sync_catalog_writes_every_entity_type() -> None:
    snapshot = CatalogSnapshot.model_validate(minimal_catalog_payload())
    sync_catalog_snapshot(snapshot)

    with connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) AS count FROM ski_regions WHERE is_active"
        ).fetchone()["count"] == 1
        assert connection.execute(
            "SELECT COUNT(*) AS count FROM ski_area_access WHERE is_active"
        ).fetchone()["count"] == 1
        assert connection.execute(
            "SELECT COUNT(*) AS count FROM lift_pass_products WHERE is_active"
        ).fetchone()["count"] == 1
```

- [ ] **Step 2: Implement one-transaction upsert and retirement**

```python
def sync_catalog_snapshot(
    snapshot: CatalogSnapshot,
    database_url: str | None = None,
) -> CatalogSyncResult:
    ensure_normalized_catalog_schema(database_url)
    with connect(database_url) as connection:
        _upsert_ski_regions(connection, snapshot.ski_regions)
        _upsert_stay_destinations(connection, snapshot.stay_destinations)
        _upsert_stay_bases(connection, snapshot.stay_bases)
        _upsert_ski_areas_preserving_ids(connection, snapshot.ski_areas)
        _upsert_access(connection, snapshot.ski_area_access)
        _upsert_terrain_domains(connection, snapshot.terrain_domains)
        _upsert_passes(connection, snapshot.lift_pass_products)
        _upsert_rentals(connection, snapshot.rental_display_facts)
        _retire_absent_entities(connection, snapshot)
    clear_repository_caches()
    return CatalogSyncResult.from_snapshot(snapshot)
```

All join-table replacement happens inside the same transaction. Never issue
`DELETE FROM ski_areas`. Missing ski areas become inactive. A sync validation or
SQL failure rolls back every catalog table.

During Phases 2-3, populate temporary `resort_id` owner columns using the
stay-destination ID selected by the migration converter so existing branch tests
can still run. New code must not read those columns.

- [ ] **Step 3: Add retirement, idempotency, and rollback tests**

Test:

- two identical syncs have the same row counts;
- removing an area marks it inactive while its weather rows remain;
- invalid FK input leaves all previous rows unchanged;
- changing metadata updates the row but not its stable ID;
- access and pass join rows exactly match the latest snapshot.

- [ ] **Step 4: Wire canonical bootstrap to normalized sync without removing legacy sync yet**

Add optional `catalog_path` to `bootstrap_database()`. When provided, load and
sync the normalized snapshot. Keep current `resorts_path` arguments until Phase
4 parity cleanup.

- [ ] **Step 5: Run focused persistence tests and lint**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_sync.py tests/test_catalog_schema_v2.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/catalog_sync.py app/data/database.py tests/test_catalog_sync.py
```

- [ ] **Step 6: Commit synchronization**

```bash
git add app/data/catalog_sync.py app/data/database.py tests/test_catalog_sync.py
git commit -m "feat: sync normalized catalog transactionally"
```

### Task 3: Add The Normalized Catalog Repository

**Files:**
- Create: `app/data/catalog_repository.py`
- Create: `tests/test_catalog_repository.py`
- Modify: `app/data/repositories.py:2074-2119`

- [ ] **Step 1: Write a failing repository round-trip test**

```python
def test_catalog_repository_returns_active_normalized_snapshot() -> None:
    snapshot = CatalogSnapshot.model_validate(minimal_catalog_payload())
    sync_catalog_snapshot(snapshot)

    loaded = CatalogRepository().get_snapshot()

    assert loaded == snapshot
    assert loaded.ski_area_access[0].stay_base_id == "example-village"
```

- [ ] **Step 2: Implement bounded table reads**

`CatalogRepository.get_snapshot()` should issue one bounded query per entity or
join table, reconstruct typed models, and cache the immutable snapshot in-process
until `clear_repository_caches()` is called. Add convenience lookups only for
public request paths actually needed later:

```python
class CatalogRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or resolve_database_url()
        self._snapshot: CatalogSnapshot | None = None

    def get_snapshot(self) -> CatalogSnapshot:
        if self._snapshot is None:
            self._snapshot = _read_active_catalog_snapshot(self._database_url)
        return self._snapshot

    def get_stay_destination(
        self, stay_destination_id: str
    ) -> StayDestination | None:
        return next(
            (
                destination
                for destination in self.get_snapshot().stay_destinations
                if destination.stay_destination_id == stay_destination_id
            ),
            None,
        )

    def get_ski_area(self, ski_area_id: str) -> SkiArea | None:
        return next(
            (
                area
                for area in self.get_snapshot().ski_areas
                if area.ski_area_id == ski_area_id
            ),
            None,
        )
```

Implement `_read_active_catalog_snapshot()` with the bounded queries listed
above and one final `CatalogSnapshot.model_validate()` call; do not bypass graph
validation for database rows.

Do not reconstruct destination-owned nested models.

- [ ] **Step 3: Add malformed-row and inactive-row tests**

Verify malformed JSON raises an explicit repository error, inactive rows are
excluded, missing optional JSON becomes the typed default, and one ski area can
be reached by bases from multiple stay destinations.

- [ ] **Step 4: Run repository tests and lint**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_repository.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/catalog_repository.py app/data/repositories.py tests/test_catalog_repository.py
```

- [ ] **Step 5: Commit repository support**

```bash
git add app/data/catalog_repository.py app/data/repositories.py tests/test_catalog_repository.py
git commit -m "feat: read normalized catalog graph"
```

### Task 4: Prove Evidence Preservation Across Migration

**Files:**
- Create: `app/data/verify_catalog_evidence.py`
- Create: `tests/test_catalog_evidence_migration.py`
- Modify: `app/data/bootstrap_database.py`

- [ ] **Step 1: Write a failing preservation test with real foreign-key rows**

```python
def test_normalized_sync_preserves_weather_evidence_by_ski_area_id() -> None:
    bootstrap_database()
    seed_raw_climatology_conditions_and_history("tignes-ski-area")
    before = evidence_counts("tignes-ski-area")

    sync_catalog_snapshot(load_catalog())

    assert evidence_counts("tignes-ski-area") == before
    assert CatalogRepository().get_ski_area("tignes-ski-area") is not None
```

Also test retiring an area preserves its evidence rows and hides it from active
catalog reads.

- [ ] **Step 2: Implement read-only evidence inventory CLI**

```python
@dataclass(frozen=True)
class SkiAreaEvidenceCounts:
    raw_weather_history: int
    climatology_daily: int
    current_conditions: int
    condition_history: int


def collect_evidence_counts(database_url: str | None = None) -> dict[str, SkiAreaEvidenceCounts]:
    counts: dict[str, dict[str, int]] = {}
    tables = {
        "raw_weather_history": "raw_weather_history",
        "climatology_daily": "ski_area_snow_climatology_daily",
        "current_conditions": "resort_conditions",
        "condition_history": "resort_condition_history",
    }
    with connect(database_url) as connection:
        for field_name, table_name in tables.items():
            rows = connection.execute(
                sql.SQL(
                    "SELECT ski_area_id, COUNT(*) AS count "
                    "FROM {} GROUP BY ski_area_id"
                ).format(sql.Identifier(table_name))
            ).fetchall()
            for row in rows:
                counts.setdefault(row["ski_area_id"], {})[field_name] = row["count"]
    return {
        ski_area_id: SkiAreaEvidenceCounts(
            raw_weather_history=values.get("raw_weather_history", 0),
            climatology_daily=values.get("climatology_daily", 0),
            current_conditions=values.get("current_conditions", 0),
            condition_history=values.get("condition_history", 0),
        )
        for ski_area_id, values in counts.items()
    }
```

CLI modes:

- `--write-snapshot PATH`: write area IDs and counts before migration;
- `--compare-snapshot PATH`: fail if any retained area loses rows;
- `--allow-new-area ID`: permit new IDs with zero evidence.

It must never mutate the database.

- [ ] **Step 3: Add bootstrap CLI support for explicit normalized catalog path**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.bootstrap_database \
  --catalog-path app/data/catalog.json
```

The command validates the snapshot before opening a transaction and prints
bounded sync counts.

- [ ] **Step 4: Run migration preservation tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_schema_v2.py \
  tests/test_catalog_sync.py \
  tests/test_catalog_repository.py \
  tests/test_catalog_evidence_migration.py \
  tests/test_repository.py::test_bootstrap_preserves_historical_evidence_for_retired_ski_area \
  tests/test_repository.py::test_ski_area_evidence_foreign_keys_do_not_cascade_delete -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/catalog_schema.py app/data/catalog_sync.py app/data/catalog_repository.py app/data/verify_catalog_evidence.py app/data/bootstrap_database.py tests/test_catalog_evidence_migration.py
```

- [ ] **Step 5: Commit evidence verification**

```bash
git add app/data/verify_catalog_evidence.py app/data/bootstrap_database.py tests/test_catalog_evidence_migration.py
git commit -m "test: protect ski area evidence during catalog migration"
```

### Task 5: Verify The Persistence Phase

- [ ] **Step 1: Run all catalog and repository tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_models.py \
  tests/test_catalog_loader_v2.py \
  tests/test_catalog_migration.py \
  tests/test_catalog_trust.py \
  tests/test_catalog_schema_v2.py \
  tests/test_catalog_sync.py \
  tests/test_catalog_repository.py \
  tests/test_catalog_evidence_migration.py \
  tests/test_repository.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data app/domain/catalog.py app/domain/catalog_trust.py tests/test_catalog_*.py
git diff --check
```

Expected: normalized repository and legacy repository tests both pass on the
development branch; evidence counts remain unchanged.

- [ ] **Step 2: Commit a final correction only when verification changed files**

```bash
git status --short
# If verification required a correction, stage only those named files and commit
# them with a message describing the correction. Otherwise, do not add an empty
# phase-completion commit.
```

Do not deploy this intermediate phase.
