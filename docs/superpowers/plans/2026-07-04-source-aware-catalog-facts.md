# Source-Aware Catalog Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ambiguous catalog atmosphere metadata with typed, source-aware ski-area and stay-base facts, a version-2 catalog/trust contract, deterministic migration, and reviewable curation support.

**Architecture:** Keep the canonical JSON catalog as the single static truth. Add frozen Pydantic value objects to the existing entity owners, mirror each nested object through dedicated JSON persistence columns, keep provenance in independently statused trust-manifest groups, and perform the version-1-to-version-2 cutover with a deterministic migration command and typed audit report.

**Tech Stack:** Python 3.12, Pydantic v2, PostgreSQL/psycopg, pytest, Ruff, checked-in JSON catalog and trust manifest, Markdown ADR/domain documentation, Codex catalog-curation skill.

---

## Decision and Review Gate

- Classification: `review-gated`
- Owner checkpoints: resolved in `docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md`
- Accepted persistence assumption: one typed JSON projection column per nested fact object; no new source-of-truth tables
- ADR: Task 1 creates ADR 0010 before schema work
- Advisory design review: completed; its catalog-version and trust-granularity findings are incorporated
- Advisory feature review: Task 8 runs `backend-api` and `data-trust-source-integrity`
- Broad destination research: excluded; later work uses normal destination-sized curation cycles

## Planned File Structure

### New files

- `docs/architecture/adr/0010-use-typed-source-aware-catalog-facts.md` — durable ownership, typing, trust, persistence, and migration decision.
- `app/data/catalog_v2_migration.py` — pure version-1-to-version-2 payload transformation, report models, hashing, and reconciliation.
- `app/data/migrate_catalog_v2.py` — CLI wrapper for dry-run, write, and reconciliation modes.
- `tests/test_catalog_v2_migration.py` — deterministic migration and tamper-detection tests.
- `docs/catalog-curation/2026-07-04-source-aware-catalog-v2-migration.json` — generated typed migration audit.

### Modified files

- `app/domain/catalog.py` — new enums/value objects, entity fields, version 2, controlled `BaseType`, retired atmosphere fields.
- `app/domain/catalog_trust.py` — version 2 and independent field groups.
- `app/data/catalog.json` and `app/data/resort_trust_manifest.json` — mechanically migrated canonical data.
- `app/data/database.py` and `app/data/catalog_schema.py` — persistence columns and retired-column cleanup.
- `app/data/catalog_sync.py` and `app/data/catalog_repository.py` — persistence round trip.
- `app/data/catalog_curation.py` and `app/data/catalog_curation_reconciliation.py` — exact field coverage and access-mode completeness.
- `tests/fixtures/minimal-catalog.json` and catalog/trust/persistence/curation tests — version-2 verification.
- `docs/domain-language.md`, `docs/data-trust-model.md`, and `docs/engineering-notes.md` — durable vocabulary and trust rules.
- `docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md` — ADR/plan links and final status.
- `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md` — new full-sweep fields and evidence gates.

---

### Task 1: Record the durable catalog-fact architecture decision

**Files:**
- Create: `docs/architecture/adr/0010-use-typed-source-aware-catalog-facts.md`
- Modify: `docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md:3-18`
- Modify if indexed: `docs/architecture/adr/README.md`

- [ ] **Step 1: Write ADR 0010**

Create the ADR with this complete decision:

```markdown
# ADR 0010: Use Typed Source-Aware Catalog Facts

Status: accepted
Date: 2026-07-04

Supersedes: N/A
Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md`

Related docs:
- `docs/domain-language.md`
- `docs/data-trust-model.md`
- `docs/architecture/adr/0009-normalized-trip-market-catalog.md`

## Context

`StayBase.base_type` is an unconstrained string and destination/base
`atmosphere_tags` mix settlement form, character, access, terrain, amenities,
and geography. Missing evidence must remain distinguishable from verified
absence, and independently sourced facts need independent trust state.

## Decision

Use small frozen Pydantic value objects owned by `SkiArea`, `StayBase`, and
`TerrainDomain`. Store typed values in the canonical catalog and keep source
references plus verification status in the trust manifest. Mirror each nested
fact through a dedicated JSON projection column. Replace free-form atmosphere
tags with controlled `BaseType`, `BaseCharacterFact`, and scoped apres profiles.
Move catalog and trust contracts together from version 1 to version 2 through a
deterministic audited migration.

## Consequences

Values become constrained, source scope remains visible, and missing data is
explicit. Curation and persistence gain more fields and validation. Existing
atmosphere tags are retired rather than retained as an untyped compatibility
escape hatch.

## Alternatives Considered

- Nullable booleans cannot preserve unknown, season, count, percentage basis,
  or intensity consistently.
- A generic attribute registry weakens typing, ownership, persistence clarity,
  and exact curation coverage.
- Relational child tables for every small fact are disproportionate to this
  static catalog and its current projection pattern.

## Revisit When

- Venue-level requirements justify first-class venue entities.
- One base/area pair needs independently queryable parallel access modes.
- Fact volume or query patterns make JSON projection unsuitable.
- A fact needs operational freshness beyond review-time season metadata.
```

- [ ] **Step 2: Link the plan and ADR from the feature spec**

Set these exact values:

```markdown
- Related plan: `docs/superpowers/plans/2026-07-04-source-aware-catalog-facts.md`
- Related ADRs:
  - `docs/architecture/adr/0008-destination-and-ski-area-boundaries.md`
  - `docs/architecture/adr/0009-normalized-trip-market-catalog.md`
  - `docs/architecture/adr/0010-use-typed-source-aware-catalog-facts.md`
```

Set the gate line to `ADR status: ADR 0010 accepted`.

- [ ] **Step 3: Verify links and commit**

```bash
rg -n "0010-use-typed-source-aware-catalog-facts|2026-07-04-source-aware-catalog-facts.md" \
  docs/architecture/adr/0010-use-typed-source-aware-catalog-facts.md \
  docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md
git diff --check
git add docs/architecture/adr/0010-use-typed-source-aware-catalog-facts.md \
  docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md
git commit -m "docs: record typed catalog fact architecture"
```

Expected: both links appear, the whitespace check passes, and the commit contains
only documentation. Add `docs/architecture/adr/README.md` only if it has an
explicit ADR list that changed.

---

### Task 2: Add frozen typed catalog fact objects

**Files:**
- Modify: `app/domain/catalog.py:29-280`
- Modify: `tests/test_catalog_models.py:1-184`
- Modify: `tests/test_catalog_models.py:820-1025`

- [ ] **Step 1: Write failing valid/default tests**

```python
def test_catalog_accepts_source_aware_fact_objects() -> None:
    payload = minimal_catalog_payload()
    payload["stay_bases"][0].update(
        {
            "elevation_m": 1450,
            "base_character": {
                "development_style": "mixed",
                "local_pace": "quiet",
            },
            "local_apres_profile": {
                "availability": "available",
                "intensity": "low_key",
                "season_label": "2026/27",
            },
        }
    )
    payload["ski_areas"][0].update(
        {
            "snowmaking": {
                "availability": "available",
                "coverage_pct": 80,
                "coverage_basis": "piste_length",
                "season_label": "2026/27",
            },
            "glacier_terrain": {"availability": "available"},
            "snow_park": {
                "availability": "available",
                "park_count": 2,
                "season_label": "2026/27",
            },
            "night_skiing": {
                "availability": "available",
                "season_label": "2026/27",
            },
            "marked_freeride_routes": {
                "availability": "available",
                "route_count": 3,
                "season_label": "2026/27",
            },
            "official_trail_map": {
                "url": "https://www.example.com/trail-map.pdf",
                "season_label": "2026/27",
            },
            "ski_day_apres_profile": {
                "availability": "available",
                "intensity": "lively",
                "season_label": "2026/27",
            },
        }
    )

    snapshot = CatalogSnapshot.model_validate(payload)

    assert snapshot.stay_bases[0].elevation_m == 1450
    assert snapshot.stay_bases[0].base_character.local_pace == "quiet"
    assert snapshot.ski_areas[0].snowmaking.coverage_pct == 80
    assert snapshot.ski_areas[0].official_trail_map is not None


def test_catalog_fact_defaults_are_unknown_or_null() -> None:
    snapshot = CatalogSnapshot.model_validate(minimal_catalog_payload())

    assert snapshot.stay_bases[0].elevation_m is None
    assert snapshot.stay_bases[0].base_character.development_style == "unknown"
    assert snapshot.stay_bases[0].local_apres_profile.availability == "unknown"
    assert snapshot.ski_areas[0].snowmaking.coverage_basis == "unknown"
    assert snapshot.ski_areas[0].glacier_terrain.availability == "unknown"
    assert snapshot.ski_areas[0].official_trail_map is None
```

- [ ] **Step 2: Write failing invariant tests**

```python
@pytest.mark.parametrize(
    "snowmaking",
    [
        {"availability": "unknown", "coverage_pct": 80, "coverage_basis": "piste_length"},
        {"availability": "available", "coverage_pct": None, "coverage_basis": "piste_length"},
        {"availability": "available", "coverage_pct": 80, "coverage_basis": "unknown"},
        {"availability": "available", "coverage_pct": 0, "coverage_basis": "piste_length"},
    ],
)
def test_catalog_rejects_inconsistent_snowmaking(snowmaking: dict[str, Any]) -> None:
    payload = minimal_catalog_payload()
    payload["ski_areas"][0]["snowmaking"] = snowmaking
    with pytest.raises(ValidationError):
        CatalogSnapshot.model_validate(payload)


@pytest.mark.parametrize("field_name", ["snow_park", "marked_freeride_routes"])
def test_catalog_rejects_feature_count_without_availability(field_name: str) -> None:
    payload = minimal_catalog_payload()
    count_name = "park_count" if field_name == "snow_park" else "route_count"
    payload["ski_areas"][0][field_name] = {
        "availability": "unknown",
        count_name: 1,
    }
    with pytest.raises(ValidationError):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_apres_intensity_without_availability() -> None:
    payload = minimal_catalog_payload()
    payload["stay_bases"][0]["local_apres_profile"] = {
        "availability": "unknown",
        "intensity": "lively",
    }
    with pytest.raises(ValidationError):
        CatalogSnapshot.model_validate(payload)
```

- [ ] **Step 3: Run tests to verify failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_models.py \
  -k "source_aware_fact or fact_defaults or inconsistent_snowmaking or feature_count or apres_intensity" -q
```

Expected: FAIL because the new value objects do not exist.

- [ ] **Step 4: Implement enums and frozen value objects**

Add `AvailabilityStatus`, `SnowmakingCoverageBasis`, `ApresIntensity`,
`BaseType`, `DevelopmentStyle`, `LocalPace`, and a stripped non-blank
`SeasonLabel`. Add these `_CatalogModel` subclasses with the exact spec fields:

```python
class AvailabilityFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"


class SnowmakingFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"
    coverage_pct: float | None = Field(default=None, ge=0, le=100)
    coverage_basis: SnowmakingCoverageBasis = "unknown"
    season_label: SeasonLabel | None = None

    @model_validator(mode="after")
    def validate_coverage(self) -> Self:
        if self.coverage_pct is None:
            if self.coverage_basis != "unknown":
                raise ValueError("snowmaking coverage basis requires a percentage")
            return self
        if self.coverage_basis == "unknown":
            raise ValueError("snowmaking percentage requires a coverage basis")
        expected = "unavailable" if self.coverage_pct == 0 else "available"
        if self.availability != expected:
            raise ValueError(f"snowmaking percentage requires availability={expected}")
        return self


class SnowParkFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"
    park_count: int | None = Field(default=None, ge=1)
    season_label: SeasonLabel | None = None

    @model_validator(mode="after")
    def validate_count(self) -> Self:
        if self.park_count is not None and self.availability != "available":
            raise ValueError("snow park count requires availability=available")
        return self


class SeasonalFeatureFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"
    season_label: SeasonLabel | None = None


class MarkedFreerideRoutesFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"
    route_count: int | None = Field(default=None, ge=1)
    season_label: SeasonLabel | None = None

    @model_validator(mode="after")
    def validate_count(self) -> Self:
        if self.route_count is not None and self.availability != "available":
            raise ValueError("freeride route count requires availability=available")
        return self


class OfficialLinkFact(_CatalogModel):
    url: str
    season_label: SeasonLabel | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return validate_direct_external_http_url(value)


class ApresProfileFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"
    intensity: ApresIntensity | None = None
    season_label: SeasonLabel | None = None

    @model_validator(mode="after")
    def validate_intensity(self) -> Self:
        if self.availability == "available" and self.intensity is None:
            raise ValueError("available apres requires intensity")
        if self.availability != "available" and self.intensity is not None:
            raise ValueError("apres intensity requires availability=available")
        return self


class BaseCharacterFact(_CatalogModel):
    development_style: DevelopmentStyle = "unknown"
    local_pace: LocalPace = "unknown"
```

Reuse `validate_direct_external_http_url` directly so official links retain the
same normalization and error text as existing source URLs.

- [ ] **Step 5: Add entity fields additively**

```python
class StayBase(_CatalogModel):
    elevation_m: int | None = Field(default=None, ge=0)
    base_character: BaseCharacterFact = Field(default_factory=BaseCharacterFact)
    local_apres_profile: ApresProfileFact = Field(default_factory=ApresProfileFact)


class SkiArea(_CatalogModel):
    snowmaking: SnowmakingFact = Field(default_factory=SnowmakingFact)
    glacier_terrain: AvailabilityFact = Field(default_factory=AvailabilityFact)
    snow_park: SnowParkFact = Field(default_factory=SnowParkFact)
    night_skiing: SeasonalFeatureFact = Field(default_factory=SeasonalFeatureFact)
    marked_freeride_routes: MarkedFreerideRoutesFact = Field(
        default_factory=MarkedFreerideRoutesFact
    )
    official_trail_map: OfficialLinkFact | None = None
    ski_day_apres_profile: ApresProfileFact = Field(default_factory=ApresProfileFact)


class TerrainDomain(_CatalogModel):
    official_trail_map: OfficialLinkFact | None = None
```

Keep current atmosphere fields and current schema version in this additive
commit. Extend existing nested immutability and extra-field tests to the new
objects.

- [ ] **Step 6: Run and commit domain tests**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_models.py -q
git add app/domain/catalog.py tests/test_catalog_models.py
git commit -m "feat: add typed catalog fact objects"
```

Expected: tests PASS and the commit does not modify canonical data yet.

---

### Task 3: Persist and reload every typed fact

**Files:**
- Modify: `app/data/database.py:95-190`
- Modify: `app/data/catalog_schema.py:29-120`
- Modify: `app/data/catalog_sync.py:176-353`
- Modify: `app/data/catalog_repository.py:135-450`
- Modify: `tests/test_catalog_schema_v2.py:1-160`
- Modify: `tests/test_catalog_sync.py:1-150`
- Modify: `tests/test_catalog_repository.py:40-225`

- [ ] **Step 1: Write failing physical-schema tests**

```python
CATALOG_FACT_COLUMNS = {
    "stay_bases": {
        "elevation_m",
        "base_character_json",
        "local_apres_profile_json",
    },
    "ski_areas": {
        "snowmaking_json",
        "glacier_terrain_json",
        "snow_park_json",
        "night_skiing_json",
        "marked_freeride_routes_json",
        "official_trail_map_json",
        "ski_day_apres_profile_json",
    },
    "terrain_domains": {"official_trail_map_json"},
}


def test_normalized_schema_has_catalog_fact_projection_columns() -> None:
    ensure_normalized_catalog_schema()
    columns = _table_columns()

    for table_name, expected in CATALOG_FACT_COLUMNS.items():
        assert expected <= columns[table_name]
```

- [ ] **Step 2: Write failing sync/repository round-trip tests**

Add this helper to `tests/test_catalog_sync.py`:

```python
def catalog_payload_with_typed_facts() -> dict[str, Any]:
    payload = complete_catalog_payload()
    payload["stay_bases"][0].update(
        {
            "elevation_m": 1450,
            "base_character": {
                "development_style": "mixed",
                "local_pace": "quiet",
            },
            "local_apres_profile": {
                "availability": "available",
                "intensity": "low_key",
                "season_label": "2026/27",
            },
        }
    )
    payload["ski_areas"][0].update(
        {
            "snowmaking": {
                "availability": "available",
                "coverage_pct": 80,
                "coverage_basis": "piste_length",
                "season_label": "2026/27",
            },
            "glacier_terrain": {"availability": "available"},
            "snow_park": {
                "availability": "available",
                "park_count": 1,
                "season_label": "2026/27",
            },
            "night_skiing": {
                "availability": "available",
                "season_label": "2026/27",
            },
            "marked_freeride_routes": {
                "availability": "available",
                "route_count": 2,
                "season_label": "2026/27",
            },
            "official_trail_map": {
                "url": "https://www.example.com/map.pdf",
                "season_label": "2026/27",
            },
            "ski_day_apres_profile": {
                "availability": "available",
                "intensity": "lively",
                "season_label": "2026/27",
            },
        }
    )
    payload["terrain_domains"][0]["official_trail_map"] = {
        "url": "https://www.example.com/domain-map.pdf",
        "season_label": "2026/27",
    }
    return payload


def test_sync_and_repository_round_trip_typed_catalog_facts() -> None:
    snapshot = CatalogSnapshot.model_validate(catalog_payload_with_typed_facts())

    sync_catalog_snapshot(snapshot)
    loaded = CatalogRepository().get_snapshot()

    assert loaded == snapshot
```

- [ ] **Step 3: Run tests to verify missing-column failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_schema_v2.py::test_normalized_schema_has_catalog_fact_projection_columns \
  tests/test_catalog_sync.py::test_sync_and_repository_round_trip_typed_catalog_facts -q
```

Expected: FAIL because columns and SQL mappings do not exist.

- [ ] **Step 4: Add idempotent persistence columns**

Add matching columns to fresh table definitions and an existing-table upgrade:

```sql
ALTER TABLE stay_bases
ADD COLUMN IF NOT EXISTS elevation_m INTEGER,
ADD COLUMN IF NOT EXISTS base_character_json TEXT NOT NULL
    DEFAULT '{"development_style":"unknown","local_pace":"unknown"}',
ADD COLUMN IF NOT EXISTS local_apres_profile_json TEXT NOT NULL
    DEFAULT '{"availability":"unknown","intensity":null,"season_label":null}';

ALTER TABLE ski_areas
ADD COLUMN IF NOT EXISTS snowmaking_json TEXT NOT NULL
    DEFAULT '{"availability":"unknown","coverage_pct":null,"coverage_basis":"unknown","season_label":null}',
ADD COLUMN IF NOT EXISTS glacier_terrain_json TEXT NOT NULL
    DEFAULT '{"availability":"unknown"}',
ADD COLUMN IF NOT EXISTS snow_park_json TEXT NOT NULL
    DEFAULT '{"availability":"unknown","park_count":null,"season_label":null}',
ADD COLUMN IF NOT EXISTS night_skiing_json TEXT NOT NULL
    DEFAULT '{"availability":"unknown","season_label":null}',
ADD COLUMN IF NOT EXISTS marked_freeride_routes_json TEXT NOT NULL
    DEFAULT '{"availability":"unknown","route_count":null,"season_label":null}',
ADD COLUMN IF NOT EXISTS official_trail_map_json TEXT,
ADD COLUMN IF NOT EXISTS ski_day_apres_profile_json TEXT NOT NULL
    DEFAULT '{"availability":"unknown","intensity":null,"season_label":null}';

ALTER TABLE terrain_domains
ADD COLUMN IF NOT EXISTS official_trail_map_json TEXT;
```

Put shared upgrade SQL in one helper called by both schema entry points rather
than duplicating different column sets.

- [ ] **Step 5: Extend sync and repository mappings**

Add every column to the relevant `INSERT ... ON CONFLICT`, update clause, and
parameter tuple. Serialize nested objects with `_model_json`:

```python
_model_json(stay_base.base_character)
_model_json(stay_base.local_apres_profile)
_model_json(ski_area.snowmaking)
_model_json(ski_area.glacier_terrain)
_model_json(ski_area.snow_park)
_model_json(ski_area.night_skiing)
_model_json(ski_area.marked_freeride_routes)
_model_json(ski_area.official_trail_map)
_model_json(ski_area.ski_day_apres_profile)
_model_json(domain.official_trail_map)
```

Select the columns in `catalog_repository.py` and decode required objects with
`default={}` and optional official links with `default=None`:

```python
"elevation_m": row["elevation_m"],
"base_character": _decode_json(
    row, "base_character_json", table_name="stay_bases", default={}
),
"local_apres_profile": _decode_json(
    row, "local_apres_profile_json", table_name="stay_bases", default={}
),
```

Repeat the exact pattern for every ski-area fact and the terrain-domain map.
Keep the repository-created snapshot on version 1 until Task 5.

- [ ] **Step 6: Add malformed JSON coverage**

```python
def test_catalog_repository_rejects_malformed_catalog_fact_json() -> None:
    snapshot = CatalogSnapshot.model_validate(catalog_payload_with_typed_facts())
    sync_catalog_snapshot(snapshot)
    with connect() as connection:
        connection.execute("UPDATE ski_areas SET snowmaking_json = '{'")

    with pytest.raises(
        CatalogRepositoryError,
        match=r"ski_areas\.snowmaking_json",
    ):
        CatalogRepository().get_snapshot()
```

- [ ] **Step 7: Run persistence tests and commit**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_schema_v2.py tests/test_catalog_sync.py \
  tests/test_catalog_repository.py -q
git add app/data/database.py app/data/catalog_schema.py \
  app/data/catalog_sync.py app/data/catalog_repository.py \
  tests/test_catalog_schema_v2.py tests/test_catalog_sync.py \
  tests/test_catalog_repository.py
git commit -m "feat: persist typed catalog facts"
```

Expected: tests PASS and non-default objects survive a database round trip.

---

### Task 4: Build the deterministic version-2 migration command

**Files:**
- Create: `app/data/catalog_v2_migration.py`
- Create: `app/data/migrate_catalog_v2.py`
- Create: `tests/test_catalog_v2_migration.py`

- [ ] **Step 1: Write failing catalog and trust transformation tests**

```python
def test_migrate_catalog_v1_to_v2_normalizes_structure_and_retires_tags() -> None:
    catalog = minimal_catalog_payload()
    catalog["stay_destinations"][0]["atmosphere_tags"] = ["premium"]
    catalog["stay_bases"][0].update(
        {
            "base_type": "traditional_village",
            "atmosphere_tags": ["quiet", "family-friendly"],
        }
    )

    migrated, audit = migrate_catalog_payload(catalog)

    assert migrated["schema_version"] == 2
    assert "atmosphere_tags" not in migrated["stay_destinations"][0]
    assert "atmosphere_tags" not in migrated["stay_bases"][0]
    assert migrated["stay_bases"][0]["base_type"] == "village"
    assert migrated["stay_bases"][0]["base_character"] == {
        "development_style": "unknown",
        "local_pace": "unknown",
    }
    assert migrated["ski_areas"][0]["snowmaking"]["availability"] == "unknown"
    assert audit.retired_atmosphere_tags[0].field_path == "atmosphere_tags"


def test_migrate_trust_v1_to_v2_uses_independent_needs_source_groups() -> None:
    trust = minimal_manifest_payload()
    area = trust["entities"]["ski_areas"]["example-area"]
    area["field_statuses"]["identity_coordinates"] = "verified"
    area["source_refs"] = ["https://www.example.com/area"]

    migrated = migrate_trust_payload(trust)

    assert migrated["catalog_schema_version"] == 2
    destination = migrated["entities"]["stay_destinations"]["example"]
    stay_base = migrated["entities"]["stay_bases"]["example-village"]
    ski_area = migrated["entities"]["ski_areas"]["example-area"]
    assert destination["field_statuses"]["price_level"] == "estimated"
    assert stay_base["field_statuses"]["base_character"] == "needs_source"
    assert ski_area["field_statuses"]["night_skiing"] == "needs_source"
    assert ski_area["field_source_refs"]["identity_coordinates"] == [
        "https://www.example.com/area"
    ]
    assert ski_area["field_source_refs"]["night_skiing"] == []
    assert "source_refs" not in ski_area
```

Build the helper from literal version-1 groups, not runtime `FIELD_GROUPS`, so
the migration test remains independent of the new contract:

```python
VERSION_1_GROUPS = {
    "ski_regions": ("identity", "membership_context"),
    "stay_destinations": (
        "identity_location",
        "coordinates",
        "price_level_atmosphere",
    ),
    "stay_bases": (
        "identity_ownership",
        "coordinates",
        "lodging_price_quality",
        "atmosphere",
    ),
    "ski_areas": (
        "identity_coordinates",
        "elevation_season",
        "terrain_metrics",
        "skill_fit",
    ),
    "ski_area_access": ("relationship", "access_mode_distance"),
    "terrain_domains": (
        "membership_connectivity",
        "aggregate_terrain",
        "season",
    ),
    "lift_pass_products": (
        "identity_scope_availability",
        "coverage",
        "prices",
        "pass_accessible_terrain",
    ),
    "rental_display_facts": ("identity_ownership", "price_quality_access"),
}


def _version_1_entry(display_name: str, entity_type: str) -> dict[str, Any]:
    return {
        "display_name": display_name,
        "field_statuses": {
            group: "estimated" for group in VERSION_1_GROUPS[entity_type]
        },
        "source_refs": [],
        "notes": [],
    }


def minimal_manifest_payload() -> dict[str, Any]:
    return {
        "version": "test-v1",
        "catalog_schema_version": 1,
        "status_values": [
            "verified",
            "verified_with_adjustment",
            "estimated",
            "needs_source",
        ],
        "field_groups": {
            key: list(value) for key, value in VERSION_1_GROUPS.items()
        },
        "entities": {
            "ski_regions": {
                "example": _version_1_entry("Example Valley", "ski_regions")
            },
            "stay_destinations": {
                "example": _version_1_entry("Example", "stay_destinations")
            },
            "stay_bases": {
                "example-village": _version_1_entry(
                    "Example Village", "stay_bases"
                )
            },
            "ski_areas": {
                "example-area": _version_1_entry("Example Area", "ski_areas")
            },
            "ski_area_access": {
                "example-village--example-area": _version_1_entry(
                    "Example Village -> Example Area", "ski_area_access"
                )
            },
            "terrain_domains": {},
            "lift_pass_products": {
                "example-local-pass": _version_1_entry(
                    "Example Local Pass", "lift_pass_products"
                )
            },
            "rental_display_facts": {},
        },
    }
```

- [ ] **Step 2: Write failing reconciliation and safety tests**

```python
def test_migration_report_reconciliation_rejects_tampered_output() -> None:
    catalog = minimal_catalog_payload()
    trust = minimal_manifest_payload()
    migrated_catalog, audit = migrate_catalog_payload(catalog)
    migrated_trust = migrate_trust_payload(trust)
    report = build_migration_report(
        before_catalog=catalog,
        after_catalog=migrated_catalog,
        before_trust=trust,
        after_trust=migrated_trust,
        audit=audit,
    )
    migrated_catalog["stay_bases"][0]["base_type"] = "town"

    with pytest.raises(ValueError, match="catalog after hash"):
        reconcile_migration_report(
            report,
            before_catalog=catalog,
            after_catalog=migrated_catalog,
            before_trust=trust,
            after_trust=migrated_trust,
        )


@pytest.mark.parametrize("version", [0, 2, 3])
def test_migration_rejects_non_v1_input(version: int) -> None:
    catalog = minimal_catalog_payload()
    catalog["schema_version"] = version
    with pytest.raises(ValueError, match="expected catalog schema version 1"):
        migrate_catalog_payload(catalog)
```

- [ ] **Step 3: Run migration tests to verify failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_v2_migration.py -q
```

Expected: FAIL because the modules do not exist.

- [ ] **Step 4: Implement report models and exact mappings**

Use frozen, `extra="forbid"` Pydantic rows:

```python
class RetiredAtmosphereTags(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    target_type: Literal["stay_destination", "stay_base"]
    target_id: str
    field_path: Literal["atmosphere_tags"] = "atmosphere_tags"
    values: tuple[str, ...]


class BaseTypeNormalization(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    stay_base_id: str
    before: str
    after: str


class CatalogV2MigrationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    from_schema_version: Literal[1] = 1
    to_schema_version: Literal[2] = 2
    catalog_before_sha256: str
    catalog_after_sha256: str
    trust_before_sha256: str
    trust_after_sha256: str
    retired_atmosphere_tags: tuple[RetiredAtmosphereTags, ...]
    base_type_normalizations: tuple[BaseTypeNormalization, ...]
```

Use the exact base-type mapping from the accepted spec. Unknown non-null values
raise instead of being guessed. Define explicit unknown dictionaries for every
new fact; do not derive them from legacy tags.

- [ ] **Step 5: Implement trust transformation exactly**

Preserve unchanged group statuses, notes, and display names. Rename
`price_level_atmosphere` to `price_level`; add new groups as `needs_source`:

```python
STAY_BASE_GROUPS = (
    "identity_ownership",
    "coordinates",
    "elevation",
    "lodging_price_quality",
    "base_type",
    "base_character",
    "local_apres",
)
SKI_AREA_NEW_GROUPS = (
    "snowmaking",
    "glacier_terrain",
    "snow_park",
    "night_skiing",
    "marked_freeride_routes",
    "ski_day_apres",
    "official_documents",
)
```

Add `official_documents` to terrain domains. Replace each legacy entity-wide
`source_refs` list with an exact `field_source_refs` mapping:

```python
field_source_refs = {
    group: list(legacy_source_refs) for group in unchanged_version_1_groups
}
field_source_refs.update({group: [] for group in newly_introduced_groups})
```

This deliberately preserves the old coarse evidence boundary without claiming
that it is more precise. Later curation narrows each group to only the sources
that support it. Set `catalog_schema_version=2` and `version="2026-07-04"`.

- [ ] **Step 6: Implement canonical hashes and exact reconciliation**

```python
def payload_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

`reconcile_migration_report()` must recompute all four hashes, rerun both pure
transforms from the before payloads, and require exact equality with both after
payloads.

- [ ] **Step 7: Implement safe CLI modes**

Support:

```text
python -m app.data.migrate_catalog_v2 dry-run --catalog-path PATH --trust-manifest-path PATH
python -m app.data.migrate_catalog_v2 write --catalog-path PATH --trust-manifest-path PATH --report-path PATH
python -m app.data.migrate_catalog_v2 reconcile --base-catalog-path PATH --current-catalog-path PATH --base-trust-manifest-path PATH --current-trust-manifest-path PATH --report-path PATH
```

`write` uses temporary sibling files followed by `Path.replace()`. Errors emit
one `[catalog-v2-migration-invalid]` line to stderr, return non-zero, and omit a
traceback.

- [ ] **Step 8: Run tests and commit migration tooling**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_v2_migration.py -q
git add app/data/catalog_v2_migration.py app/data/migrate_catalog_v2.py \
  tests/test_catalog_v2_migration.py
git commit -m "feat: add audited catalog v2 migration"
```

Expected: tests PASS, including tamper detection and non-v1 rejection.

---

### Task 5: Cut all canonical contracts to version 2

**Files:**
- Modify: `app/domain/catalog.py`
- Modify: `app/domain/catalog_trust.py`
- Modify: `app/data/database.py`
- Modify: `app/data/catalog_schema.py`
- Modify: `app/data/catalog_sync.py`
- Modify: `app/data/catalog_repository.py`
- Modify: `app/data/catalog_curation.py`
- Modify: `app/data/catalog.json`
- Modify: `app/data/resort_trust_manifest.json`
- Modify: `tests/fixtures/minimal-catalog.json`
- Modify: `tests/test_catalog_models.py`
- Modify: `tests/test_catalog_trust.py`
- Modify: `tests/test_catalog_schema_v2.py`
- Modify: `tests/test_catalog_repository.py`
- Modify: `tests/test_catalog_curation.py`
- Create: `docs/catalog-curation/2026-07-04-source-aware-catalog-v2-migration.json`

- [ ] **Step 1: Preserve version-1 source inputs outside Git**

```bash
mkdir -p .tmp/catalog-v2-migration
cp app/data/catalog.json .tmp/catalog-v2-migration/catalog-v1.json
cp app/data/resort_trust_manifest.json \
  .tmp/catalog-v2-migration/resort-trust-manifest-v1.json
```

Expected: two version-1 snapshots exist under ignored `.tmp/` and `git status`
does not list them.

- [ ] **Step 2: Write failing version, type, and retired-field tests**

Change `minimal_catalog_payload()` to version 2 and add:

```python
def test_catalog_rejects_version_1_after_v2_cutover() -> None:
    payload = minimal_catalog_payload()
    payload["schema_version"] = 1
    with pytest.raises(ValidationError):
        CatalogSnapshot.model_validate(payload)


def test_stay_base_rejects_noncanonical_base_type() -> None:
    payload = minimal_catalog_payload()
    payload["stay_bases"][0]["base_type"] = "traditional_village"
    with pytest.raises(ValidationError):
        CatalogSnapshot.model_validate(payload)


def test_catalog_rejects_retired_atmosphere_fields() -> None:
    payload = minimal_catalog_payload()
    payload["stay_bases"][0]["atmosphere_tags"] = ["quiet"]
    with pytest.raises(ValidationError, match="atmosphere_tags"):
        CatalogSnapshot.model_validate(payload)
```

Update `EXPECTED_FIELD_GROUPS` in `tests/test_catalog_trust.py` to:

```python
EXPECTED_FIELD_GROUPS = {
    "ski_regions": ("identity", "membership_context"),
    "stay_destinations": ("identity_location", "coordinates", "price_level"),
    "stay_bases": (
        "identity_ownership",
        "coordinates",
        "elevation",
        "lodging_price_quality",
        "base_type",
        "base_character",
        "local_apres",
    ),
    "ski_areas": (
        "identity_coordinates",
        "elevation_season",
        "terrain_metrics",
        "skill_fit",
        "snowmaking",
        "glacier_terrain",
        "snow_park",
        "night_skiing",
        "marked_freeride_routes",
        "ski_day_apres",
        "official_documents",
    ),
    "ski_area_access": ("relationship", "access_mode_distance"),
    "terrain_domains": (
        "membership_connectivity",
        "aggregate_terrain",
        "season",
        "official_documents",
    ),
    "lift_pass_products": (
        "identity_scope_availability",
        "coverage",
        "prices",
        "pass_accessible_terrain",
    ),
    "rental_display_facts": ("identity_ownership", "price_quality_access"),
}
```

Change trust version assertions to 2.

Update trust test helpers to emit group-specific source mappings:

```python
def _entry_payload(display_name: str, groups: tuple[str, ...]) -> dict[str, Any]:
    return {
        "display_name": display_name,
        "field_statuses": {group: "estimated" for group in groups},
        "field_source_refs": {group: [] for group in groups},
        "notes": [],
    }
```

Replace entity-wide source tests with loops over
`entry.field_source_refs.items()`. Direct-URL, immutable mapping, canonical JSON,
and verified-source tests must all target a named field group.

Add group-specific source validation coverage:

```python
def test_verified_group_requires_group_specific_source() -> None:
    snapshot = _minimal_snapshot()
    payload = _manifest_payload(snapshot)
    entry = payload["entities"]["ski_areas"]["example-area"]
    entry["field_statuses"]["identity_coordinates"] = "verified"
    entry["field_source_refs"]["identity_coordinates"] = []

    manifest = CatalogTrustManifest.model_validate(payload)
    with pytest.raises(ValueError, match="identity_coordinates.*source"):
        manifest.validate_against_catalog(snapshot)
```

- [ ] **Step 3: Write failing exact curation-path tests**

Update expected paths to include every nested leaf, including:

```python
{
    "elevation_m",
    "base_type",
    "base_character.development_style",
    "base_character.local_pace",
    "local_apres_profile.availability",
    "local_apres_profile.intensity",
    "local_apres_profile.season_label",
}
```

and for ski areas:

```python
{
    "snowmaking.availability",
    "snowmaking.coverage_pct",
    "snowmaking.coverage_basis",
    "snowmaking.season_label",
    "glacier_terrain.availability",
    "snow_park.availability",
    "snow_park.park_count",
    "snow_park.season_label",
    "night_skiing.availability",
    "night_skiing.season_label",
    "marked_freeride_routes.availability",
    "marked_freeride_routes.route_count",
    "marked_freeride_routes.season_label",
    "official_trail_map.url",
    "official_trail_map.season_label",
    "ski_day_apres_profile.availability",
    "ski_day_apres_profile.intensity",
    "ski_day_apres_profile.season_label",
}
```

Terrain domains add `official_trail_map.url` and
`official_trail_map.season_label`. Remove both atmosphere roots.

- [ ] **Step 4: Run focused tests to verify failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_models.py \
  tests/test_catalog_trust.py::test_contract_declares_exact_entity_types_statuses_and_field_groups \
  tests/test_catalog_curation.py::test_canonical_paths_cover_only_normalized_catalog_entities -q
```

Expected: FAIL until runtime version, groups, paths, and fields change.

- [ ] **Step 5: Switch model and trust contracts atomically**

Apply:

```python
CatalogSchemaVersion = Literal[2]
```

Remove `StayDestination.atmosphere_tags` and `StayBase.atmosphere_tags`; change
the stay-base declaration to:

```python
base_type: BaseType | None = None
```

Change `CatalogTrustManifest.catalog_schema_version` to `Literal[2]` and replace
`FIELD_GROUPS` with the exact tuples above. Replace entity-wide `source_refs`
with an exact group-keyed mapping:

```python
class EntityTrustEntry(_TrustModel):
    display_name: str
    field_statuses: _FieldStatuses
    field_source_refs: _FieldSourceRefs
    notes: tuple[str, ...] = ()
```

Validate that `field_statuses` and `field_source_refs` keys exactly match the
owning namespace's `FIELD_GROUPS`. Normalize and validate every URL with the
existing direct-source validator. During `validate_against_catalog`, require a
non-empty `field_source_refs[group]` for each `verified` or
`verified_with_adjustment` group; sources attached to another group do not
satisfy that requirement.

- [ ] **Step 6: Replace executable curation paths**

Remove retired paths from `CANONICAL_FIELD_PATHS` and add every leaf listed in
Step 3. Set nested roots to:

```python
"stay_base": frozenset(
    {"base_character", "local_apres_profile", "regional_data_ids"}
),
"ski_area": frozenset(
    {
        "season_windows",
        "supported_skill_levels",
        "snowmaking",
        "glacier_terrain",
        "snow_park",
        "night_skiing",
        "marked_freeride_routes",
        "official_trail_map",
        "ski_day_apres_profile",
    }
),
"terrain_domain": frozenset(
    {"ski_area_ids", "season_windows", "official_trail_map", "source_urls"}
),
```

For `trust_manifest`, replace `source_refs` with `field_source_refs` in both
`CANONICAL_FIELD_PATHS` and `NESTED_FIELD_PATH_ROOTS`.

- [ ] **Step 7: Remove retired persistence surfaces**

Remove atmosphere columns from fresh table definitions, sync SQL, repository
queries, and repository payload construction. Add idempotent cleanup after new
columns exist:

```sql
ALTER TABLE stay_destinations
DROP COLUMN IF EXISTS atmosphere_tags_json;

ALTER TABLE stay_bases
DROP COLUMN IF EXISTS atmosphere_tags_json;
```

Change repository-created snapshots to `"schema_version": 2`. Update schema
tests to assert both retired columns are absent. Replace old optional-atmosphere
JSON tests with new-fact JSON tests from Task 3.

- [ ] **Step 8: Run the canonical migration**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.migrate_catalog_v2 write \
  --catalog-path app/data/catalog.json \
  --trust-manifest-path app/data/resort_trust_manifest.json \
  --report-path docs/catalog-curation/2026-07-04-source-aware-catalog-v2-migration.json
```

Expected: one success line for version 1 -> 2. Canonical records contain
explicit unknown/null facts, controlled base types, and no atmosphere fields.

- [ ] **Step 9: Reconcile the exact migration**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.migrate_catalog_v2 reconcile \
  --base-catalog-path .tmp/catalog-v2-migration/catalog-v1.json \
  --current-catalog-path app/data/catalog.json \
  --base-trust-manifest-path .tmp/catalog-v2-migration/resort-trust-manifest-v1.json \
  --current-trust-manifest-path app/data/resort_trust_manifest.json \
  --report-path docs/catalog-curation/2026-07-04-source-aware-catalog-v2-migration.json
```

Expected: all hashes and recomputed payloads match.

- [ ] **Step 10: Update remaining fixtures and literal versions**

Change `tests/fixtures/minimal-catalog.json` and non-migration test literals from
1 to 2. Keep explicit version-1 values only in migration tests. Search with:

```bash
rg -n '"(schema_version|catalog_schema_version)": 1' tests app/data
```

Expected: matches remain only where version-1 input is intentionally tested.

- [ ] **Step 11: Run coordinated cutover tests and canonical validation**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_models.py tests/test_catalog_trust.py \
  tests/test_catalog_schema_v2.py tests/test_catalog_sync.py \
  tests/test_catalog_repository.py tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py \
  tests/test_catalog_v2_migration.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog \
  --catalog-path app/data/catalog.json \
  --trust-manifest-path app/data/resort_trust_manifest.json
```

Expected: tests PASS and validation reports `schema_version=2`.

- [ ] **Step 12: Commit the coordinated cutover**

```bash
git add app/domain/catalog.py app/domain/catalog_trust.py \
  app/data/database.py app/data/catalog_schema.py app/data/catalog_sync.py \
  app/data/catalog_repository.py app/data/catalog_curation.py \
  app/data/catalog.json app/data/resort_trust_manifest.json \
  tests/fixtures/minimal-catalog.json tests/test_catalog_models.py \
  tests/test_catalog_trust.py tests/test_catalog_schema_v2.py \
  tests/test_catalog_sync.py tests/test_catalog_repository.py \
  tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py \
  docs/catalog-curation/2026-07-04-source-aware-catalog-v2-migration.json
git commit -m "feat: migrate catalog contract to version 2"
```

---

### Task 6: Enforce access-mode completeness and update curation guidance

**Files:**
- Modify: `app/data/catalog_curation_reconciliation.py:31-360`
- Modify: `tests/test_catalog_curation_reconciliation.py:1-240`
- Modify: `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`

- [ ] **Step 1: Write failing full-review tests**

Import `CANONICAL_FIELD_PATHS` from `app.data.catalog_curation`, then add:

```python
def _unknown_access_report(
    *,
    access_mode_status: Literal["reviewed-no-change", "unresolved"],
) -> CatalogCurationReport:
    access_id = "example-village--example-area"
    return CatalogCurationReport(
        title="Unknown access mode review",
        summary="Reviews a normalized access edge with unresolved mode.",
        reviewed_targets=[
            CatalogReviewedTarget(
                target_type="ski_area_access",
                target_id=access_id,
                scope="full",
            )
        ],
        field_coverage=[
            CatalogFieldCoverage(
                target_type="ski_area_access",
                target_id=access_id,
                field_path=field_path,
                status=(
                    access_mode_status
                    if field_path == "access_mode"
                    else "reviewed-no-change"
                ),
                notes=(
                    "No authoritative access mode has been established."
                    if field_path == "access_mode"
                    and access_mode_status == "unresolved"
                    else None
                ),
            )
            for field_path in sorted(CANONICAL_FIELD_PATHS["ski_area_access"])
        ],
    )


def _unknown_access_snapshots(tmp_path: Path) -> tuple[tuple[Path, Path], tuple[Path, Path]]:
    payload = minimal_catalog_payload()
    payload["ski_area_access"][0]["access_mode"] = "unknown"
    return (
        _write_snapshot(tmp_path, "unknown-base", payload),
        _write_snapshot(tmp_path, "unknown-current", payload),
    )


def test_full_access_review_requires_unknown_mode_to_be_unresolved(
    tmp_path: Path,
) -> None:
    base_paths, current_paths = _unknown_access_snapshots(tmp_path)

    with pytest.raises(
        CatalogValidationError,
        match="access_mode=unknown must be unresolved",
    ):
        reconcile_catalog_curation_report(
            _unknown_access_report(access_mode_status="reviewed-no-change"),
            base_catalog_path=base_paths[0],
            current_catalog_path=current_paths[0],
            base_trust_manifest_path=base_paths[1],
            current_trust_manifest_path=current_paths[1],
        )


def test_full_access_review_accepts_unresolved_unknown_mode(tmp_path: Path) -> None:
    base_paths, current_paths = _unknown_access_snapshots(tmp_path)

    result = reconcile_catalog_curation_report(
        _unknown_access_report(access_mode_status="unresolved"),
        base_catalog_path=base_paths[0],
        current_catalog_path=current_paths[0],
        base_trust_manifest_path=base_paths[1],
        current_trust_manifest_path=current_paths[1],
    )

    assert result is not None
```

Also import `Literal` from `typing`. These helpers build on the existing
`_write_snapshot()` fixture path and do not introduce a second framework.

- [ ] **Step 2: Run the tests to verify failure**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_curation_reconciliation.py -k "unknown_mode" -q
```

Expected: FAIL because current reconciliation does not inspect the reviewed
current access value.

- [ ] **Step 3: Implement the invariant**

Add a helper called by `reconcile_catalog_curation_report()`:

```python
def _validate_full_access_mode_resolution(
    report: CatalogCurationReport,
    current: _CatalogSnapshot,
    issues: list[str],
) -> None:
    coverage_by_key = {
        coverage.target_key: coverage for coverage in report.field_coverage
    }
    for reviewed in report.reviewed_targets:
        if reviewed.target_type != "ski_area_access" or reviewed.scope != "full":
            continue
        access = current.access_by_id.get(reviewed.target_id)
        if access is None or access.access_mode != "unknown":
            continue
        coverage = coverage_by_key.get(
            ("ski_area_access", reviewed.target_id, "access_mode")
        )
        if coverage is None or coverage.status != "unresolved":
            issues.append(
                f"ski_area_access:{reviewed.target_id} "
                "access_mode=unknown must be unresolved in a full review"
            )
```

Use the existing `CatalogFieldCoverage.target_key` identity property; do not add
parallel identity logic.

- [ ] **Step 4: Update the local curation skill**

Add this concise section:

```markdown
## Source-Aware Fit Facts

- `SkiArea`: review snowmaking, glacier terrain, snow park, night skiing,
  marked freeride routes, official trail map, and ski-day apres.
- `StayBase`: review elevation, controlled base type, base character, and local
  apres.
- `TerrainDomain`: use `official_trail_map` only for a genuinely aggregate map.
- Use `available`, `unavailable`, and `unknown` exactly as defined in the domain
  model. Website silence means `unknown`.
- Do not infer snowmaking percentage from cannon count, glacier terrain from a
  name, freeride routes from off-piste marketing, or destination-wide character
  from one base.
- Full access review must classify `access_mode=unknown` as unresolved.
```

Keep `CANONICAL_FIELD_PATHS` as the executable field-list source of truth.

- [ ] **Step 5: Run curation verification and commit repository files**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py -q
git diff --check
git add app/data/catalog_curation_reconciliation.py \
  tests/test_catalog_curation_reconciliation.py
git commit -m "feat: enforce resolved catalog access modes"
```

Expected: tests PASS. The external skill file remains outside the repository;
preserve and report its local diff separately.

---

### Task 7: Align domain and trust documentation

**Files:**
- Modify: `docs/domain-language.md:1-240`
- Modify: `docs/data-trust-model.md:1-145`
- Modify: `docs/engineering-notes.md`
- Modify: `docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md`

- [ ] **Step 1: Update catalog domain language**

Replace broad atmosphere ownership with:

```markdown
**Stay destination**

The bookable town or destination context presented to a user. It owns country,
region, center coordinates, price level, and its parent trip-market region. It
does not own ski areas, local apres, or stay-base character.

**Stay base**

A village, neighbourhood, resort station, or resort sector where the user can
stay. It owns lodging price/quality estimates, representative elevation,
structural base type, local character, and local apres. Ski access is always an
explicit edge.
```

Add glossary entries for `BaseType`, `BaseCharacterFact`, `ApresProfileFact`,
and `AvailabilityStatus` using the exact accepted definitions.

- [ ] **Step 2: Update the data-trust contract**

Document all of these concrete rules:

- catalog and trust schema version 2;
- exact new stay-base, ski-area, and terrain-domain trust groups;
- independently sourced facts have independent statuses;
- every trust group has its own validated source-reference list;
- explicit unavailability requires a scoped complete source;
- qualitative normalization normally uses `verified_with_adjustment`;
- seasonal labels stay with catalog values while retrieval/source context stays
  in trust and curation artifacts;
- the typed hash-based migration report proves the version cutover.

Delete obsolete generic atmosphere-group descriptions.

- [ ] **Step 3: Add one concise engineering note**

```markdown
### Typed static catalog facts

Static feature and character facts use small frozen value objects in the
canonical catalog and dedicated JSON projection columns in PostgreSQL. Source
references and verification state remain in the trust manifest. The separation
keeps catalog values type-safe without creating relational tables for every
small fact, while independent trust groups prevent one strong source from
overstating unrelated fields. Versioned breaking migrations are deterministic,
audited, and coordinated across catalog, trust, persistence, and curation.
```

- [ ] **Step 4: Verify terminology alignment**

```bash
rg -n "BaseType|BaseCharacterFact|ApresProfileFact|AvailabilityStatus" \
  docs/domain-language.md docs/data-trust-model.md docs/engineering-notes.md
! rg -n "price_level_atmosphere|stay-base.*atmosphere tags" \
  docs/domain-language.md docs/data-trust-model.md
git diff --check
```

Expected: new terms appear in owning docs and obsolete trust wording does not.

- [ ] **Step 5: Commit documentation alignment**

```bash
git add docs/domain-language.md docs/data-trust-model.md \
  docs/engineering-notes.md \
  docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md
git commit -m "docs: define typed catalog fact vocabulary"
```

Keep the spec status `accepted` until Task 8 passes.

---

### Task 8: Run final verification and focused feature review

**Files:**
- Modify after review if needed: files named by defensible findings
- Modify: `docs/superpowers/specs/2026-07-04-source-aware-catalog-facts-design.md`

- [ ] **Step 1: Run formatting and static checks**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff format --check app tests
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 2: Run focused catalog verification**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_models.py \
  tests/test_catalog_trust.py \
  tests/test_catalog_schema_v2.py \
  tests/test_catalog_sync.py \
  tests/test_catalog_repository.py \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py \
  tests/test_catalog_v2_migration.py -q
```

Expected: PASS.

- [ ] **Step 3: Validate canonical catalog and trust data**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog \
  --catalog-path app/data/catalog.json \
  --trust-manifest-path app/data/resort_trust_manifest.json
```

Expected: `[catalog-valid] schema_version=2 ...`.

- [ ] **Step 4: Reconcile the migration from preserved inputs**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.migrate_catalog_v2 reconcile \
  --base-catalog-path .tmp/catalog-v2-migration/catalog-v1.json \
  --current-catalog-path app/data/catalog.json \
  --base-trust-manifest-path .tmp/catalog-v2-migration/resort-trust-manifest-v1.json \
  --current-trust-manifest-path app/data/resort_trust_manifest.json \
  --report-path docs/catalog-curation/2026-07-04-source-aware-catalog-v2-migration.json
```

Expected: all four hashes and transformed payloads match.

- [ ] **Step 5: Run the full backend suite**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest -q
```

Expected: PASS. If an unrelated environment-dependent test cannot run, record
the exact command, error, and focused replacement evidence.

- [ ] **Step 6: Run focused Snowcast feature review**

Use `snowcast-advisory-review` in `feature-review` mode with:

- `backend-api`
- `data-trust-source-integrity`

Provide the complete implementation diff, accepted spec, ADR 0010, migration
report, and verification output. Fix all Blocker and High findings. Record
defensible Medium and Low findings as follow-up only when they are outside this
contract.

- [ ] **Step 7: Mark the feature spec implemented**

After all checks and feature review pass, set:

```markdown
- Status: implemented
```

Set advisory feature review to completed and summarize resolved findings.

- [ ] **Step 8: Commit final review adjustments**

```bash
git add app tests docs
git commit -m "chore: finalize catalog fact migration"
```

If only the spec status changed, stage only that spec. Never stage unrelated
files. Keep the external curation-skill change outside the repository commit.

- [ ] **Step 9: Confirm final state**

```bash
git status --short --branch
git log --oneline --decorate -8
```

Expected: no uncommitted repository changes and the planned small commits are
present. Report the external skill diff separately. Do not push or open a pull
request unless the owner explicitly requests it.
