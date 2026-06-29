# Destination Boundaries And Campiglio Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make destination identity a consistent trip-planning boundary, enforce that terrain domains join ski areas from multiple destinations, and replace PR #24's single aggregate Madonna di Campiglio entry with three independently useful destinations under one connected Campiglio terrain domain.

**Architecture:** `Destination` owns the trip/stay choice, `SkiArea` owns local weather and operational evidence, and `TerrainDomain` owns ski-connected aggregate terrain spanning destinations. The existing `madonna-di-campiglio-ski-area` id remains stable, but its local coordinates, elevations, and season geometry are source-reviewed rather than grandfathered. New Pinzolo and Folgarida-Marilleva ski-area ids start without archive evidence. Any required archive work is an explicit owner-triggered GitHub Actions operation after merge and deployment; this implementation does not mutate production weather. Shared-pass coverage outside the connected domain remains `regional_network` external validity rather than creating terrain connectivity.

**Tech Stack:** Python 3.13, Pydantic v2, JSON static catalogs, pytest, Ruff, Markdown/ADRs, Snowcast Codex skills, GitHub CLI.

---

## Scope And Guardrails

- Classification: `review-gated`, using the full design flow because this changes
  durable catalog identity, weather-evidence ownership, pass scope, and ranking
  inputs.
- Developer Decision Checkpoint: resolved by the owner in the accepted spec;
  use three destinations and ski areas under one connected terrain domain, keep
  ski sub-areas parked, apply the same boundary rule catalog-wide, retain
  `madonna-di-campiglio-ski-area`, and source-review its local weather geometry.
- Weather-evidence DDC: if accepted Madonna latitude, longitude, base elevation,
  or summit elevation changes the derived weather request points, the owner will
  manually refetch its 1991-01-01 through 2025-12-31 archive with
  `force_refetch=true` and `rebuild=false`, then rebuild baseline 2025
  climatology. After new ids deploy, the owner will backfill Pinzolo and
  Folgarida-Marilleva over the same range with `force_refetch=false` and
  `rebuild=false`, then rebuild baseline 2025 climatology.
- ADR status: required in Task 3.
- Advisory review status: design review completed with backend/API and
  data-trust High findings routed into Tasks 2, 5, 6, 7, 8, 9, and 10; feature
  review remains required before the final PR update.
- Work on `codex/catalog-curation-madonna-di-campiglio`, the existing branch for draft PR #24.
- Merge current `origin/main` before changing catalog data. Preserve all catalog entries merged after PR #24 was opened.
- Do not change or replace `madonna-di-campiglio-ski-area`.
- Do not copy the 156 km, aggregate lift count, elevation range, or difficulty split into a child ski area unless a child-scoped source supports the value.
- Do not add Pejo to `campiglio-dolomiti-di-brenta`; it is pass-accessible but not ski-connected to the three modeled destinations.
- Do not implement ski sub-areas or production shared-domain result deduplication in this change.
- Do not run local or PR-time commands that backfill, rebuild, bootstrap, or
  otherwise mutate production weather/climatology data.
- Keep generated curation Markdown subordinate to the typed JSON report.
- Do not begin catalog edits until the typed report contract is implemented and
  all three Campiglio destination-boundary assessments pass.
- Use project-scoped GitHub authentication for PR updates:

```bash
export GH_CONFIG_DIR="$HOME/.config/gh-lampssy-snowcast"
```

## Task 1: Synchronize The Existing PR Branch And Complete Design Review

**Files:**
- Review: `docs/superpowers/specs/2026-06-29-destination-boundaries-and-connected-terrain-design.md`
- Review: `docs/operating-model/advisory-reviewers.md`
- Review: `docs/operating-model/review-playbook.md`
- Merge-sensitive: `app/data/resorts.json`
- Merge-sensitive: `app/data/resort_trust_manifest.json`
- Merge-sensitive: `app/data/terrain_domains.json`

- [x] Confirm the branch and worktree before integrating main:

```bash
git status --short --branch
git branch --show-current
git fetch origin main
```

Expected branch: `codex/catalog-curation-madonna-di-campiglio`. Stop if unrelated uncommitted changes appear.

- [x] Merge current main without rebasing the published PR branch:

```bash
git merge --no-edit origin/main
```

Resolve catalog conflicts by retaining every destination/domain from `origin/main`, then retaining the current Madonna entry only as the input to the later split. Do not resolve by accepting either complete JSON file wholesale.

- [x] Establish a passing post-merge baseline:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_validation.py \
  tests/test_seed_data.py \
  tests/test_repository.py -q
```

- [x] Run a Snowcast `design-review` against the accepted spec with the `backend-api` and `data-trust-source-integrity` reviewers. The backend/API High findings require a self-contained Pydantic terrain-domain invariant, enforceable full-scope report coverage, selector/CLI tests, a response-level Madonna id regression, and a production-safe workflow handoff. The data-trust High findings require typed pre-edit boundary gates, a blocking geometry source hierarchy, and first-class terrain-domain trust provenance. This remediation resolves/routes all High findings in the accepted spec and Tasks 2, 5-10; feature review remains planned.

- [x] Keep merge commit `ce6090d`. Do not squash or rewrite the existing PR history.

Task 1 is complete only with the accepted-spec and implementation-plan
remediation committed. No unresolved owner decision remains.

## Task 2: Enforce Terrain-Domain Invariants And Trust

**Files:**
- Modify: `app/data/validate_resort_catalog.py`
- Modify: `app/domain/models.py`
- Modify: `app/data/resort_trust_manifest.json`
- Test: `tests/test_catalog_validation.py`

- [ ] Add a failing Pydantic model test that constructs a `TerrainDomain` with
  multiple ski-area refs but fewer than two distinct `resort_id` values. Assert
  model validation rejects it before any catalog is available.

- [ ] Add a separate failing cross-catalog validation test:

```python
def test_validate_catalog_rejects_unknown_terrain_domain_ref(
    tmp_path,
) -> None:
    payload = _valid_resort_payload()
    terrain_domains = [
        {
            "terrain_domain_id": "test-local-domain",
            "name": "Invalid Local Domain",
            "ski_area_refs": [
                {
                    "resort_id": "test-resort",
                    "ski_area_id": "test-resort-ski-area",
                },
                {
                    "resort_id": "second-resort",
                    "ski_area_id": "missing-second-ski-area",
                }
            ],
            "metric_scope": "aggregate",
            "total_piste_km": 100,
            "source_urls": ["https://example.com/reviewed-domain"],
        }
    ]
    resorts_path = tmp_path / "resorts.json"
    terrain_domains_path = tmp_path / "terrain_domains.json"
    manifest_path = tmp_path / "trust.json"
    _write_json(resorts_path, payload)
    _write_json(terrain_domains_path, terrain_domains)
    _write_json(manifest_path, _valid_manifest_payload())

    with pytest.raises(CatalogValidationError) as error:
        validate_catalog(
            resorts_path=resorts_path,
            terrain_domains_path=terrain_domains_path,
            trust_manifest_path=manifest_path,
        )

    assert any(
        "terrain domain references unknown ski area" in issue
        for issue in error.value.issues
    )
```

- [ ] Run both tests and confirm the Pydantic and cross-catalog protections fail
  for their distinct missing behavior:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_validation.py::test_terrain_domain_requires_two_distinct_destinations \
  tests/test_catalog_validation.py::test_validate_catalog_rejects_unknown_terrain_domain_ref -q
```

- [ ] In `TerrainDomain`, use one maintainable `model_validator` to require at
  least two distinct `ski_area_refs[].resort_id` values. Keep cross-catalog
  reference validation in `_validate_loaded_catalog` so unknown
  `{resort_id, ski_area_id}` pairs still fail independently. Do not rely on a
  `min_length` alone because two refs from one destination are still invalid.

- [ ] Require non-empty direct HTTP(S) `source_urls` on `TerrainDomain`. They
  must support membership and every populated aggregate metric; pass validity
  alone is not membership evidence. Add omission and invalid-URL tests.

- [ ] Add a top-level `terrain_domains` mapping to
  `app/data/resort_trust_manifest.json` with this stable shape:

```json
{
  "terrain_domains": {
    "tignes-val-disere": {
      "display_name": "Tignes - Val d'Isere",
      "field_statuses": {
        "membership": "verified",
        "terrain_metrics": "verified_with_adjustment",
        "season_window": "needs_source"
      },
      "source_refs": [
        "https://en.tignes.net/skiing/ski-area",
        "https://www.valdisere.com/en/val-disere-in-winter/skiing-winter-fun/ski-area-french-alps/"
      ],
      "notes": ["Scope and normalization note."]
    }
  }
}
```

  The implementation must use the complete reviewed direct external source set
  represented by each domain, not only the abbreviated shape example.

- [ ] Extend trust-manifest validation to require exact id parity between the
  top-level mapping and `terrain_domains.json`, the exact field groups
  `membership`, `terrain_metrics`, and `season_window`, valid existing trust
  statuses, direct external `source_refs` for source-backed statuses, and
  non-blank notes. Add tests for missing/extra domain ids, missing status groups,
  and absent direct provenance.

- [ ] Migrate `tignes-val-disere` and `matterhorn-ski-paradise` into the new
  trust mapping using their reviewed direct URLs and scope notes. Do not defer
  existing entries until the Campiglio data edit.

- [ ] Keep the cross-catalog check explicit after Pydantic validation:

```python
for ski_area_ref in terrain_domain.ski_area_refs:
    key = (ski_area_ref.resort_id, ski_area_ref.ski_area_id)
    if key not in ski_area_keys:
        issues.append(
            f"{terrain_domain.terrain_domain_id}: terrain domain references "
            f"unknown ski area {ski_area_ref.resort_id}/"
            f"{ski_area_ref.ski_area_id}"
        )
```

The self-contained structural invariant belongs to Pydantic; catalog validation
owns only references to the loaded destination catalog and trust-id parity.

- [ ] Update Pydantic field descriptions without changing serialized contracts:
  - `Destination.resort_id`: stable trip-planning destination identity.
  - `SkiArea.ski_area_id`: smallest durable local terrain unit owning weather/operations; it may connect by lift/piste to other ski areas.
  - `TerrainDomain`: ski-connected aggregate spanning at least two distinct destinations; shared ticket validity alone is insufficient and direct membership provenance is required.

- [ ] Run focused tests and lint:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_validation.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check \
  app/domain/models.py app/data/validate_resort_catalog.py \
  tests/test_catalog_validation.py
```

- [ ] Commit:

```bash
git add \
  app/domain/models.py \
  app/data/validate_resort_catalog.py \
  app/data/resort_trust_manifest.json \
  tests/test_catalog_validation.py
git commit -m "feat: enforce terrain-domain trust"
```

## Task 3: Make The Boundary Rule Canonical In Repo Documentation

**Files:**
- Create: `docs/architecture/adr/0008-destination-and-ski-area-boundaries.md`
- Modify: `docs/domain-language.md`
- Modify: `docs/engineering-notes.md`
- Modify: `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`
- Verify: `docs/product-backlog.md`

- [ ] Add ADR 0008 with status `Accepted` and these decisions:
  - destination identity is a recommendation/stay boundary, determined by all three hard gates plus one strong source identity signal;
  - ski-area identity is a weather/operations boundary and does not require disconnection from adjacent terrain;
  - cross-destination ski connectivity belongs to `TerrainDomain`;
  - pass-only networks do not imply terrain domains;
  - destination/ski-area splits require explicit weather-evidence migration handling;
  - alternatives rejected: official marketing label as identity, connectivity-only destination merging, and immediate ski-sub-area modeling.

- [ ] Add the exact hard gates and failure routing from the accepted spec to `docs/domain-language.md`. Keep `resort_id` documented as a transitional field name for destination identity.

- [ ] Add a concise durable note to `docs/engineering-notes.md` explaining why lift-connected ski areas can still be separate and why aggregate metrics remain on domains.

- [ ] Align the static curation skill design with the accepted boundary rule. State that destination-boundary review precedes routine field enrichment and that a split/merge becomes an owner-reviewed model migration.

- [ ] Confirm the parked `Ski Sub-Areas And Terrain Sectors` backlog item remains out of active scope.

- [ ] Run documentation checks:

```bash
rg -n "Independent stay context|Independent ski access|Independent recommendation value" \
  docs/domain-language.md \
  docs/architecture/adr/0008-destination-and-ski-area-boundaries.md
rg -n "Ski Sub-Areas And Terrain Sectors" docs/product-backlog.md
git diff --check
```

- [ ] Commit:

```bash
git add \
  docs/architecture/adr/0008-destination-and-ski-area-boundaries.md \
  docs/domain-language.md \
  docs/engineering-notes.md \
  docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md
git commit -m "docs: define destination and ski-area boundaries"
```

## Task 4: Align The Curation And Review Skills

**Files outside project git:**
- Modify: `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`
- Modify: `/Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md`

- [ ] In `snowcast-catalog-curation`, add a `Destination Boundary Discovery` stage before linked-destination discovery:
  1. apply all three hard gates;
  2. require one strong official identity signal;
  3. route failed candidates to stay base, ski area, future ski sub-area, terrain domain, or external pass context;
  4. treat a proposed destination split/merge or ski-area id replacement as a model migration requiring an owner checkpoint;
  5. allow one PR containing more than three destinations only when a single connected terrain-domain migration requires the related set.

- [ ] Replace the old disconnected-terrain wording in `Scope Rules` with the accepted rule that ski areas may be lift-connected when local access, operations, ticketing, elevation/weather, or schedule identity is materially distinct.

- [ ] In `snowcast-catalog-review`, require review of the hard gates and flag:
  - independently useful destinations merged into one catalog entry;
  - a destination created from only a neighborhood or piste-sector label;
  - a terrain domain that does not span destinations;
  - a terrain domain created only to represent a pass network;
  - copied aggregate metrics on child ski areas without child-scoped evidence;
  - an unacknowledged ski-area id change that would orphan weather evidence.

- [ ] Verify the skill wording:

```bash
rg -n "Destination Boundary|Independent stay|Independent ski access|recommendation value|model migration" \
  /Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md \
  /Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md
rg -n "may be lift-connected|pass.*alone|at least two destinations" \
  /Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md \
  /Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md
```

These files are intentionally not staged in the project repository. Summarize their exact changes in PR #24 so reviewers know the operational guidance was updated.

## Task 5: Enforce Typed Curation Scope And Destination Gates

**Files:**
- Modify: `app/data/catalog_curation.py`
- Test: `tests/test_catalog_curation.py`

- [ ] Add `trust_manifest` to `CatalogTargetType`. Keep trust-manifest
  `source_refs`, `notes`, and `field_statuses.<group>` changes as first-class
  typed targets rather than overloading destination fields.

- [ ] Add a typed `CatalogReviewedTarget` contract with:
  - `target_type` and `target_id`;
  - `scope: Literal["full", "narrow"]`;
  - `required_field_paths`, forbidden for `full` scope and required/non-empty
    for `narrow` scope.

- [ ] Define immutable canonical field-path sets in one mapping keyed by target
  type. Use the field lists in the curation skill as the initial contract,
  including the trust-manifest paths. For a `full` reviewed target, resolve the
  canonical set in code and require one typed `field_coverage` row for every
  path. For a `narrow` target, require exactly the declared path set. Do not
  infer scope from `changes[]`, changed-entity counts, or rendered Markdown.

  Canonical top-level sets are:
  - `destination`: `resort_id`, `name`, `country`, `region`, `price_level`,
    `latitude`, `longitude`, `base_elevation_m`, `summit_elevation_m`,
    `season_start_month`, `season_end_month`, `season_windows`,
    `lift_pass_products`, `ski_areas`, `terrain_groups`, `stay_bases`,
    `rentals`;
  - `ski_area`: `ski_area_id`, `name`, `latitude`, `longitude`,
    `base_elevation_m`, `summit_elevation_m`, `season_start_month`,
    `season_end_month`, `season_windows`, `total_piste_km`,
    `total_lift_count`, `piste_km_by_difficulty.beginner`,
    `piste_km_by_difficulty.intermediate`,
    `piste_km_by_difficulty.advanced`;
  - `terrain_group`: `terrain_group_id`, `name`, `ski_area_ids`,
    `metric_scope`, `total_piste_km`, `total_lift_count`,
    `piste_km_by_difficulty.beginner`,
    `piste_km_by_difficulty.intermediate`,
    `piste_km_by_difficulty.advanced`, `source_urls`;
  - `terrain_domain`: `terrain_domain_id`, `name`, `ski_area_refs`,
    `metric_scope`, `total_piste_km`, `total_lift_count`,
    `base_elevation_m`, `summit_elevation_m`,
    `piste_km_by_difficulty.beginner`,
    `piste_km_by_difficulty.intermediate`,
    `piste_km_by_difficulty.advanced`, `season_windows`, `source_urls`;
  - `stay_base`: `stay_base_id`, `name`, `price_range`, `price_min`,
    `price_max`, `quality`, `lift_distance`, `supported_skill_levels`,
    `latitude`, `longitude`, `nearest_lift_name`,
    `nearest_lift_distance_m`, `access_mode`, `base_type`, `atmosphere_tags`,
    `regional_data_ids`;
  - `rental`: `name`, `price_range`, `price_min`, `price_max`, `quality`,
    `lift_distance`;
  - `lift_pass_product`: `lift_pass_product_id`, `name`, `validity_scope`,
    `is_default`, `valid_ski_area_ids`, `terrain_domain_ids`,
    `external_validity_summary`, `prices`;
  - `trust_manifest`: `field_statuses`, `source_refs`, `notes`.

  When a canonical collection is populated, keep one collection-level coverage
  row and require exact changed/evidence rows for each edited indexed or nested
  value. This preserves deterministic full-scope enforcement without teaching
  the report model every runtime collection length.

- [ ] Add typed boundary models using the existing Pydantic base and URL helper:
  - `CatalogBoundaryGateAssessment` with gate name, `pass|fail|unresolved`,
    notes, and non-empty direct `source_urls`;
  - `CatalogIdentitySignalAssessment` with signal type,
    `pass|fail|unresolved`, notes, and non-empty direct `source_urls`;
  - `CatalogDestinationBoundaryAssessment` with candidate destination id,
    exactly the three named hard gates, one or more identity signals, and a
    typed failure route when the candidate does not pass.

- [ ] Use a small set of composable Pydantic `model_validator` methods and
  canonical-set helpers for structural enforcement. Keep evidence/change
  cross-reference checks in `validate_catalog_curation_report`; do not add
  renderer heuristics or ad hoc changed-only detection.

- [ ] Extend `CatalogCurationReport` with typed `reviewed_targets` and
  `destination_boundary_assessments`. Enforce:
  - every changed target is declared in `reviewed_targets`;
  - every reviewed target has exactly its required typed field coverage;
  - a full target with changed-only coverage fails even when every change has a
    matching coverage row;
  - duplicate reviewed targets and duplicate candidate assessments fail;
  - every newly created destination, detected from a destination identity
    change with `before=null`, has an assessment;
  - new destination creation fails validation unless all three gates pass and
    at least one identity signal passes;
  - any failed or unresolved candidate requires explicit failure routing.

- [ ] Add focused omission tests before implementation:
  - full target missing one canonical path;
  - full target containing only changed paths;
  - narrow target missing `required_field_paths`;
  - changed `trust_manifest` target omitted from `reviewed_targets`;
  - newly created destination missing its assessment;
  - one missing, failed, or unresolved hard gate;
  - no passing identity signal;
  - missing direct source URL or missing failure route;
  - valid mixed full/narrow report.

- [ ] Run focused tests and lint:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_curation.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check \
  app/data/catalog_curation.py tests/test_catalog_curation.py
```

- [ ] Commit:

```bash
git add app/data/catalog_curation.py tests/test_catalog_curation.py
git commit -m "feat: enforce typed catalog review scope"
```

## Task 6: Build The Reviewed Campiglio Evidence Set

**Files:**
- Inspect: `app/data/resorts.json`
- Inspect: `app/data/resort_trust_manifest.json`
- Prepare changes for: `docs/catalog-curation/2026-06-27-madonna-di-campiglio.json`

- [ ] Before editing either catalog JSON file, populate and validate typed
  `destination_boundary_assessments` for exactly:
  `madonna-di-campiglio`, `pinzolo`, and `folgarida-marilleva`. Each candidate
  must include all three hard gates, at least one identity signal, notes, and
  direct source URLs. Search pages, internal docs, prior reports, and generated
  artifacts are not direct evidence.

- [ ] Require all three candidates to pass all hard gates and at least one
  identity signal before Task 7. A `fail` or `unresolved` gate blocks creation
  of the new destination and records its route as `stay_base`, `ski_area`,
  `ski_sub_area_backlog`, `terrain_domain`, `external_pass_context`, or
  `blocked`. Do not downgrade an unresolved assessment to prose caveat.

- [ ] Re-review the official connected-domain and operating sources:
  - `https://www.campigliodolomiti.it/en/ski-area`
  - `https://www.ski.it/en/info-live/lift-status`
  - `https://www.ski.it/en/info-live/slopes`
  - the official Folgarida-Marilleva annual-report PDF already identified in the spec research, which names the three separate operating domains.

- [ ] Re-review shared and local pass sources:
  - `https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea`
  - `https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf`
  - `https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf`
  - `https://www.ski.it/it/skipass/giornate-integrative-skiarea`

Use the PDF page images, not scrambled text extraction, to transcribe adult high-season 1-, 3-, and 6-day examples. If a duration is absent or ambiguous, omit that example and mark it unresolved; do not infer it.

- [ ] Re-review local coordinates, terrain, elevation, and season geometry for
  Madonna, Pinzolo, and Folgarida-Marilleva using this blocking order:
  1. official local source at the exact child scope;
  2. OSM, DEM, or another reviewed open-data object for coordinates/elevation;
  3. reviewed editorial fallback only at the exact child scope, recorded as
     `verified_with_adjustment` with normalization notes;
  4. an explicitly labeled estimate only where existing catalog policy permits
     it and the typed evidence documents the method;
  5. otherwise mark unresolved and block a new destination.

  Store only values whose source scope matches the child ski area. Keep the
  existing 156 km and difficulty split as aggregate-domain evidence.

- [ ] Record before/after Madonna ski-area latitude, longitude, base elevation,
  summit elevation, season months, and exact season windows. Compute and record
  whether accepted coordinate/elevation changes alter the weather request
  points. This typed `weather_geometry_materially_changed` outcome selects the
  conditional GitHub Actions path in Task 10; it does not authorize a local or
  PR-time backfill.

- [ ] Resolve the aggregate lift-count conflict using the existing trust policy: first compare source scope and currency; if no official source is clearly authoritative for the same static domain, use a same-scope Bergfex value only as `verified_with_adjustment`, preserving both official conflicting values and the fallback arithmetic in the report. If no same-scope fallback can be defended, leave `total_lift_count` unset and record the conflict.

- [ ] Review OSM objects directly for each stay base. Use type-specific keys (`osm_node_id`, `osm_relation_id`, `nearest_lift_osm_node_id`, or `nearest_lift_osm_way_id`) and record the exact object coordinate or endpoint used.

Known candidate objects to verify, not blindly copy:

| Stay base | Place object | Lift object |
| --- | --- | --- |
| Pinzolo | node `4311362989` | node `298987790`, Funivia Pinzolo - Pra Rodont |
| Folgarida | node `327580361` | node `648469713`, Folgarida lower station |
| Marilleva 900 | node `331259493` | node `1096349618`; verify station role before use |
| Marilleva 1400 | node `331259364` | node `1096349822` |
| Daolasa | node `6043719130` | node `1096349433` |

- [ ] Calculate nearest-lift distances with the same Haversine method for every retained stay base and capture the input coordinates in evidence notes:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python - <<'PY'
from math import asin, cos, radians, sin, sqrt

def haversine_m(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> int:
    dlat = radians(b_lat - a_lat)
    dlon = radians(b_lon - a_lon)
    lat1 = radians(a_lat)
    lat2 = radians(b_lat)
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return round(2 * 6_371_000 * asin(sqrt(h)))

assert haversine_m(46.1617322, 10.7650043, 46.1635157, 10.7657124) > 0
print(haversine_m(46.1617322, 10.7650043, 46.1635157, 10.7657124))
PY
```

- [ ] Declare typed `reviewed_targets` for all three destinations, ski areas,
  every stay base and rental, all pass products, all three trust-manifest
  entries, and the Campiglio terrain domain. Use `scope=full` for this migration.

- [ ] Build typed field coverage against Task 5's canonical path sets before
  editing JSON. Every path must end as `changed`, `reviewed-no-change`,
  `unresolved`, or `not-applicable`; a changed-only report is invalid.

- [ ] Validate the pre-edit report contract. Task 7 remains blocked until all
  three boundary assessments and full-scope target declarations validate:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
  --report-path docs/catalog-curation/2026-06-27-madonna-di-campiglio.json
```

## Task 7: Test-Drive And Apply The Campiglio Catalog Migration

**Files:**
- Modify: `tests/test_seed_data.py`
- Modify: `app/data/resorts.json`
- Modify: `app/data/terrain_domains.json`

- [ ] Add a failing seed-data test that locks the entity shape, not volatile ranking order:

```python
from app.data.loader import load_resorts, load_terrain_domains


def test_seed_data_models_campiglio_as_three_destinations_and_one_domain() -> None:
    resorts = {resort.resort_id: resort for resort in load_resorts()}
    domains = {
        domain.terrain_domain_id: domain for domain in load_terrain_domains()
    }

    assert {
        "madonna-di-campiglio",
        "pinzolo",
        "folgarida-marilleva",
    } <= resorts.keys()
    assert resorts["madonna-di-campiglio"].ski_areas[0].ski_area_id == (
        "madonna-di-campiglio-ski-area"
    )
    assert resorts["pinzolo"].ski_areas[0].ski_area_id == "pinzolo-ski-area"
    assert resorts["folgarida-marilleva"].ski_areas[0].ski_area_id == (
        "folgarida-marilleva-ski-area"
    )

    domain = domains["campiglio-dolomiti-di-brenta"]
    assert {
        (ref.resort_id, ref.ski_area_id) for ref in domain.ski_area_refs
    } == {
        ("madonna-di-campiglio", "madonna-di-campiglio-ski-area"),
        ("pinzolo", "pinzolo-ski-area"),
        ("folgarida-marilleva", "folgarida-marilleva-ski-area"),
    }
    assert domain.total_piste_km == 156
    assert all(
        ski_area.total_piste_km != 156
        for resort_id in (
            "madonna-di-campiglio",
            "pinzolo",
            "folgarida-marilleva",
        )
        for ski_area in resorts[resort_id].ski_areas
    )
```

- [ ] Add a second test for pass semantics:
  - all three destinations have the shared Skiarea product as their only default;
  - it has `validity_scope="regional_network"`;
  - it references `campiglio-dolomiti-di-brenta`;
  - its local `valid_ski_area_ids` contains only the owning destination's local ski-area id;
  - `external_validity_summary` explicitly names Pejo as non-connected pass coverage;
  - Pinzolo and Folgarida-Marilleva each also have one non-default `single_ski_area` local product;
  - no invented Madonna-only local product exists.

- [ ] Run the new tests and confirm they fail because Pinzolo, Folgarida-Marilleva, and the domain do not exist:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_seed_data.py::test_seed_data_models_campiglio_as_three_destinations_and_one_domain \
  tests/test_seed_data.py::test_seed_data_models_campiglio_pass_scope -q
```

- [ ] Reshape `app/data/resorts.json`:
  - retain `madonna-di-campiglio` and `madonna-di-campiglio-ski-area` ids;
  - apply only the source-reviewed Madonna local coordinates, elevations, and
    season geometry from Task 6; record rather than execute the conditional
    weather-history action;
  - correct Madonna OSM provenance from generic `osm_node` to a verified type-specific key and add exact lift-object provenance if the distance remains modeled;
  - remove the aggregate 156 km, aggregate lift count, aggregate difficulty split, and aggregate-only elevation values from the Madonna child ski area unless re-supported at local scope;
  - add `pinzolo` with `pinzolo-ski-area`, independent stay context, source-reviewed rental data, the shared pass, and the local Pinzolo pass;
  - add `folgarida-marilleva` with `folgarida-marilleva-ski-area`, source-reviewed Folgarida/Marilleva stay bases, source-reviewed rental data, the shared pass, and the local Folgarida-Marilleva pass;
  - use full curation fields; do not insert guessed price ranges, quality tiers, supported skill levels, atmosphere tags, or rental prices without the report classifying them as curated estimates under the existing policy.

- [ ] Add `campiglio-dolomiti-di-brenta` to `app/data/terrain_domains.json`:

```json
{
  "terrain_domain_id": "campiglio-dolomiti-di-brenta",
  "name": "Campiglio Dolomiti di Brenta",
  "ski_area_refs": [
    {
      "resort_id": "madonna-di-campiglio",
      "ski_area_id": "madonna-di-campiglio-ski-area"
    },
    {
      "resort_id": "pinzolo",
      "ski_area_id": "pinzolo-ski-area"
    },
    {
      "resort_id": "folgarida-marilleva",
      "ski_area_id": "folgarida-marilleva-ski-area"
    }
  ],
  "metric_scope": "aggregate",
  "total_piste_km": 156,
  "source_urls": [
    "https://www.campigliodolomiti.it/en/ski-area"
  ]
}
```

`source_urls` must directly support the three-member ski-connected domain and
every populated aggregate metric. Add only reviewed `total_lift_count`,
elevation, difficulty, season, and additional source fields from Task 6; omitted
optional values must be documented as unresolved.

- [ ] Do not call `bootstrap_database()`, historical backfill, or climatology
  rebuild while applying or validating catalog data. This task changes static
  files and tests only.

- [ ] Run catalog and focused tests:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_seed_data.py tests/test_catalog_validation.py -q
```

- [ ] Commit:

```bash
git add app/data/resorts.json app/data/terrain_domains.json tests/test_seed_data.py
git commit -m "data: model Campiglio as linked destinations"
```

## Task 8: Update Trust And Rewrite The Typed Curation Report

**Files:**
- Modify: `app/data/resort_trust_manifest.json`
- Modify: `docs/catalog-curation/2026-06-27-madonna-di-campiglio.json`
- Regenerate: `docs/catalog-curation/2026-06-27-madonna-di-campiglio.md`

- [ ] Replace the one-destination report with a linked three-destination migration report. Keep the existing filename so PR #24 has one authoritative report rather than competing historical/current reports.

- [ ] Add trust-manifest entries for `pinzolo` and `folgarida-marilleva`; update Madonna notes. Each entry must:
  - distinguish official verified fields, reviewed adjustments, curated estimates, and unresolved fields;
  - include direct official source refs rather than internal docs or generated reports;
  - state that shared 156 km terrain belongs to `campiglio-dolomiti-di-brenta`;
  - state that historical weather remains attached to `madonna-di-campiglio-ski-area` and has not been copied to the new ids.

- [ ] Add `campiglio-dolomiti-di-brenta` to the top-level trust-manifest
  `terrain_domains` mapping implemented in Task 2. Set and explain separate
  `membership`, `terrain_metrics`, and `season_window` statuses, include direct
  external `source_refs`, and document Pejo's exclusion. Keep the existing
  Tignes-Val d'Isere and Matterhorn entries intact.

- [ ] In the typed report, retain the three validated pre-edit boundary
  assessments and declare `scope=full` reviewed targets with complete canonical
  `field_coverage[]` for:
  - three destinations;
  - three ski areas;
  - every retained stay base and rental;
  - every shared/local lift-pass product and representative price;
  - three trust-manifest entries;
  - the Campiglio terrain domain.

  Represent manifest `source_refs`, `notes`, and each changed
  `field_statuses.<group>` under `target_type=trust_manifest`; do not hide them
  under destination rows.

- [ ] Preserve conflicts and scope decisions in `evidence[]`/`unresolved_caveats[]`:
  - child metrics are unresolved unless child-scoped evidence exists;
  - the shared 156 km is not child terrain;
  - aggregate lift-count conflicts and any Bergfex fallback are explicit;
  - Pejo is external pass validity, not a domain member;
  - the two new ski-area ids need archive backfill and climatology rebuild;
  - Madonna's before/after local weather geometry and the typed material-change
    outcome determine whether its conditional full refetch is required;
  - production search may display multiple domain members until separate dedup work lands.

- [ ] Render Markdown only from the valid typed report:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
  --report-path docs/catalog-curation/2026-06-27-madonna-di-campiglio.json \
  --markdown-output docs/catalog-curation/2026-06-27-madonna-di-campiglio.md
```

- [ ] Verify evidence hygiene:

```bash
rg -n "https://" docs/catalog-curation/2026-06-27-madonna-di-campiglio.md
! rg -n "docs/|localhost|/tmp/|artifacts/" \
  docs/catalog-curation/2026-06-27-madonna-di-campiglio.json
git diff --check
```

- [ ] Commit:

```bash
git add \
  app/data/resort_trust_manifest.json \
  docs/catalog-curation/2026-06-27-madonna-di-campiglio.json \
  docs/catalog-curation/2026-06-27-madonna-di-campiglio.md
git commit -m "docs: rewrite Campiglio curation evidence"
```

## Task 9: Reconcile Repository, API, And Search Regression Expectations

**Files:**
- Modify if required: `tests/test_repository.py`
- Modify if required: `tests/test_services.py`
- Modify if required: `tests/test_search_models.py`
- Modify: `tests/test_api.py`
- Do not modify merely to force old rank order.

- [ ] Run shared catalog/repository/search tests:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_repository.py \
  tests/test_services.py \
  tests/test_search_models.py \
  tests/test_api.py -q
```

- [ ] If repository fixtures contain a one-destination `TerrainDomain`, add a second fixture destination and ref so the test models the real invariant. Do not weaken the validator.

- [ ] Update brittle fixture-count or expected-name assertions only where the two newly valid destinations change catalog cardinality. Keep service tests behavioral: destination eligibility, grouping key semantics, evidence identity, and penalties rather than an exact production rank position.

- [ ] Add a response-level API regression that exercises `/api/search` response
  serialization with a Madonna result and asserts both stable identifiers:
  `resort_id == "madonna-di-campiglio"` and
  `selected_ski_area_id == "madonna-di-campiglio-ski-area"`. Stub ranking input
  if needed to avoid locking production order; this test protects the HTTP
  contract, not a top-three position.

- [ ] Add no production search dedup behavior in this task. If current search returns multiple Campiglio-domain destinations, record it in the report and scoring backlog rather than hiding destinations in seed data.

- [ ] Run affected lint and commit only if test files changed:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check \
  tests/test_repository.py tests/test_services.py tests/test_search_models.py \
  tests/test_api.py
git add \
  tests/test_repository.py tests/test_services.py tests/test_search_models.py \
  tests/test_api.py
git diff --cached --quiet || git commit -m "test: align fixtures with destination boundaries"
```

## Task 10: Verify Catalog, Ranking Inputs, And Weather Selection

**Files:**
- Verify: all changed files
- Test: `tests/test_open_meteo.py`
- Test: `tests/test_snow_climatology.py`
- Artifact output only: `/private/tmp/snowcast-campiglio-ranking-comparison`

- [ ] Run the complete focused suite:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_validation.py \
  tests/test_catalog_curation.py \
  tests/test_seed_data.py \
  tests/test_repository.py \
  tests/test_resort_fit.py \
  tests/test_services.py \
  tests/test_search_models.py \
  tests/test_api.py \
  tests/test_open_meteo.py \
  tests/test_snow_climatology.py -q
```

- [ ] Run catalog and report validation:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
  --report-path docs/catalog-curation/2026-06-27-madonna-di-campiglio.json \
  --markdown-output docs/catalog-curation/2026-06-27-madonna-di-campiglio.md
```

- [ ] Perform a read-only loader check. Do not call `bootstrap_database()`:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python - <<'PY'
from app.data.loader import load_resorts, load_terrain_domains

resorts = {resort.resort_id: resort for resort in load_resorts()}
domain = next(
    domain
    for domain in load_terrain_domains()
    if domain.terrain_domain_id == "campiglio-dolomiti-di-brenta"
)
for resort_id in (
    "madonna-di-campiglio",
    "pinzolo",
    "folgarida-marilleva",
):
    resort = resorts[resort_id]
    print(resort_id, [area.ski_area_id for area in resort.ski_areas])
print([(ref.resort_id, ref.ski_area_id) for ref in domain.ski_area_refs])
PY
```

- [ ] Add selector tests that load the seed catalog and prove each destination
  target resolves to exactly one expected pair in both the backfill selector and
  climatology selector:
  - `madonna-di-campiglio` -> `madonna-di-campiglio-ski-area`;
  - `pinzolo` -> `pinzolo-ski-area`;
  - `folgarida-marilleva` -> `folgarida-marilleva-ski-area`.

- [ ] Add CLI forwarding tests with the database/network function stubbed. For
  backfill, assert dates, repeated/comma-expanded targets, `force_refetch`, and
  `rebuild` reach the application function unchanged. For climatology, assert
  targets and `baseline_end_year=2025` are forwarded. These tests must not call
  `bootstrap_database()`, Postgres, or Open-Meteo.

- [ ] Run the selector and CLI tests, not live commands:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_open_meteo.py \
  tests/test_snow_climatology.py -q
```

No implementation, PR verification, or local completion command may mutate
production weather. After merge and deployment, the owner manually triggers
these GitHub Actions workflows in order.

If Task 6 records `weather_geometry_materially_changed=true`, first run
**Backfill Historical Weather** for Madonna with every dispatch input set as
follows:

| Input | Value |
| --- | --- |
| `start_date` | `1991-01-01` |
| `end_date` | `2025-12-31` |
| `chunk_days` | `365` |
| `resort_targets` | `madonna-di-campiglio` |
| `force_refetch` | `true` |
| `rebuild` | `false` |
| `retry_attempts` | `5` |
| `backoff_seconds` | `30` |
| `request_delay_seconds` | `2` |
| `request_jitter_ratio` | `0.25` |
| `retry_jitter_ratio` | `0.25` |
| `provider_pressure_error_threshold` | `3` |
| `provider_pressure_cooldown_seconds` | `300` |

After that workflow succeeds, run **Rebuild Snow Climatology**:

| Input | Value |
| --- | --- |
| `baseline_end_year` | `2025` |
| `resort_targets` | `madonna-di-campiglio` |
| `source_model` | `snowcast_empirical_v1` |

After both new destination ids are deployed, run **Backfill Historical
Weather** for the new ids with every dispatch input set as follows:

| Input | Value |
| --- | --- |
| `start_date` | `1991-01-01` |
| `end_date` | `2025-12-31` |
| `chunk_days` | `365` |
| `resort_targets` | `pinzolo,folgarida-marilleva` |
| `force_refetch` | `false` |
| `rebuild` | `false` |
| `retry_attempts` | `5` |
| `backoff_seconds` | `30` |
| `request_delay_seconds` | `2` |
| `request_jitter_ratio` | `0.25` |
| `retry_jitter_ratio` | `0.25` |
| `provider_pressure_error_threshold` | `3` |
| `provider_pressure_cooldown_seconds` | `300` |

After that workflow succeeds, run **Rebuild Snow Climatology**:

| Input | Value |
| --- | --- |
| `baseline_end_year` | `2025` |
| `resort_targets` | `pinzolo,folgarida-marilleva` |
| `source_model` | `snowcast_empirical_v1` |

If Madonna geometry did not materially change, skip both Madonna workflow runs;
the new-id workflow pair is still required.

- [ ] Run ranking comparison and reconcile the report summary with actual output:

```bash
rm -rf /private/tmp/snowcast-campiglio-ranking-comparison
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking \
  --output-dir /private/tmp/snowcast-campiglio-ranking-comparison
rg -n "Madonna|Pinzolo|Folgarida|Campiglio" \
  /private/tmp/snowcast-campiglio-ranking-comparison/ranking-comparison-report.md || true
```

If no default diagnostic scenario emits these destinations, say so explicitly; do not claim a ranking outcome not present in the artifact.

- [ ] Run final static checks:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
git diff --check
git status --short --branch
```

## Task 11: Feature Review And Update Draft PR #24

**Files:**
- Modify only as findings require.
- Update: PR #24 title/body/checklist.

- [ ] Run Snowcast `feature-review` on the complete diff with `backend-api` and `data-trust-source-integrity`. Resolve all Blocker and High findings. Resolve Medium findings that affect entity boundaries, source scope, weather identity, pass validity, or reviewer comprehension; document any intentionally deferred low-risk finding.

- [ ] Re-run the exact verification affected by review fixes plus:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_validation.py \
  tests/test_catalog_curation.py \
  tests/test_seed_data.py \
  tests/test_repository.py \
  tests/test_services.py \
  tests/test_api.py \
  tests/test_open_meteo.py \
  tests/test_snow_climatology.py -q
git diff --check
```

- [ ] Commit review fixes if present:

```bash
git add -A
git diff --cached --quiet || git commit -m "fix: address Campiglio model review"
```

- [ ] Push the existing branch and update, rather than replace, draft PR #24:

```bash
export GH_CONFIG_DIR="$HOME/.config/gh-lampssy-snowcast"
git push origin codex/catalog-curation-madonna-di-campiglio
gh pr edit 24 \
  --title "Model Campiglio as linked ski destinations" \
  --body-file /tmp/snowcast-pr24-body.md
gh pr checks 24
```

The PR body must summarize:
  - the three destination/ski-area identities;
  - the shared connected terrain domain and aggregate metric ownership;
  - shared versus local pass products and Pejo external validity;
  - the preserved Madonna weather id, the material-geometry outcome, and the
    exact conditional Madonna plus required new-id GitHub Actions inputs;
  - direct links to the rendered curation evidence and ADR;
  - validation, tests, ranking-diagnostic result, advisory-review status, and residual caveats;
  - that both catalog skills were updated outside the repo.

- [ ] Keep the PR as draft until checks pass and the owner reviews the new entity boundaries and curated estimates.

## Completion Criteria

- PR #24 contains exactly three Campiglio destinations with three stable local ski-area ids and one shared connected domain.
- The accepted report contains passing typed pre-edit assessments for Madonna,
  Pinzolo, and Folgarida-Marilleva; all three hard gates and at least one direct
  source-backed identity signal pass for each created destination.
- The 156 km aggregate is present only on `campiglio-dolomiti-di-brenta` unless independent child evidence supports a coincident value.
- The shared pass is correctly modeled as regional-network coverage with Pejo external; local products are non-default alternatives.
- Pydantic rejects terrain domains with fewer than two distinct destination ids;
  cross-catalog validation rejects unknown refs; every domain has direct
  membership/metric `source_urls`.
- The trust manifest has validated `terrain_domains` entries for
  Tignes-Val d'Isere, Matterhorn Ski Paradise, and Campiglio with membership,
  terrain-metric, and season-window statuses, direct refs, and notes.
- The typed curation report declares full/narrow reviewed targets, includes
  `trust_manifest` targets, covers every canonical full-scope path, and links
  directly to evidence; changed-only full coverage fails tests.
- Existing Madonna weather identity is unchanged. Local geometry and season
  values follow the blocking source hierarchy, and the report records whether
  the conditional Madonna archive refetch is required.
- Selector/CLI tests and a response-level API regression preserve all three
  weather targets and both Madonna response ids.
- The completion handoff contains exact post-deploy GitHub Actions inputs for
  the 1991-01-01 through 2025-12-31 archive and baseline 2025 climatology. No
  bootstrap, local verification, or PR command mutates production weather.
- Validator, model descriptions, domain docs, ADR, curation skill, and review skill all express the same boundary rule.
- Ski sub-areas and production shared-domain result deduplication remain out of
  scope.
- The design review is complete with no unresolved owner decisions; feature
  review remains planned until Task 11 runs on the implemented diff.
- Focused tests, catalog/report validation, Ruff, advisory review, and GitHub checks pass or any external check blocker is explicitly reported.
