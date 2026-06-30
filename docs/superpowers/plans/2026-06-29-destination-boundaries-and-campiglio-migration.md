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
  manually refetch from 1991-01-01 through an operator-derived
  `archive_end_date` with `force_refetch=true` and `rebuild=false`, then rebuild
  baseline 2025 climatology. Immediately before dispatch, the end date is the
  latest existing Madonna raw archive date or UTC run date minus one after
  proving it is not earlier. After new ids deploy, the owner will backfill
  Pinzolo and Folgarida-Marilleva through the same end date with
  `force_refetch=false` and `rebuild=false`, then rebuild baseline 2025
  climatology.
- ADR status: required in Task 3.
- Advisory review status: Task 1 quality-review remediation completed. In
  addition to the prior review-loop resolutions, catalog/trust parity is now an
  atomic migration prerequisite and rental snapshot identity is deterministic.
  These corrections are routed into Tasks 5, 7, and 8; no remaining High
  findings are pending re-review. Feature review remains required before the
  final PR update.
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

- [x] Incorporate design re-review findings. Backend/API required validator-derived
  weather materiality, required retained Madonna decisions, and base/current
  snapshot reconciliation. Data trust required typed evidence keys, consistent
  strong source-backed identity policy, `display_name` coverage, all changed
  trust records, and an update to the owning data-trust document. These are
  resolved in the accepted spec and Tasks 2, 5, 6, 8, and 10; no remaining High
  findings pending re-review.

- [x] Incorporate third review-loop findings. Use frozen PR base
  `ce6090d^2=e8f4e11`, preserve the real Madonna 1550 m base in geometry tests,
  derive an archive end that includes current-year rows, use canonical strong
  source-backed identity wording, and add negative terrain-domain trust and
  `display_name` reconciliation tests. These corrections leave no High finding
  pending re-review.

- [x] Incorporate Task 1 quality-review findings. The catalog migration must
  add its required destination and Campiglio terrain-domain trust records before
  catalog validation or commit, while the following task only reconciles and
  renders the typed report from that already-valid state. Rentals use one shared
  destination-qualified deterministic reconciliation key, and a rental rename
  is reported as removal plus addition. These corrections leave no High finding
  pending re-review.

- [x] Keep merge commit `ce6090d`. Do not squash or rewrite the existing PR history.

Task 1 is complete only with the accepted-spec and implementation-plan
remediation committed. No unresolved owner decision remains.

## Task 2: Enforce Terrain-Domain Invariants And Trust

**Files:**
- Modify: `app/data/validate_resort_catalog.py`
- Modify: `app/domain/models.py`
- Modify: `app/data/resort_trust_manifest.json`
- Modify: `docs/data-trust-model.md`
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

- [ ] Update `docs/data-trust-model.md` in the same implementation task. Define
  the top-level `terrain_domains` mapping, its `display_name`,
  `membership`/`terrain_metrics`/`season_window` status groups, direct-source
  requirements, id-parity validation, and namespaced report-target convention.

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
  docs/data-trust-model.md \
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
  2. require one strong source-backed identity signal; official sources are
     preferred and required only for `official_destination_treatment`;
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

## Task 5: Enforce Typed Curation And Snapshot Reconciliation Contracts

**Files:**
- Modify: `app/data/catalog_curation.py`
- Create: `app/data/catalog_curation_reconciliation.py`
- Modify: `app/data/validate_catalog_curation.py`
- Test: `tests/test_catalog_curation.py`
- Create: `tests/test_catalog_curation_reconciliation.py`

- [ ] Add `trust_manifest` to `CatalogTargetType`. Keep trust-manifest
  `display_name`, `source_refs`, `notes`, and `field_statuses.<group>` changes as
  first-class typed targets rather than overloading destination fields. Use
  namespaced ids: `destination:<resort_id>` and
  `terrain_domain:<terrain_domain_id>`.

- [ ] Add a required unique `evidence_id` to `CatalogEvidenceItem`. Boundary
  gates and identity signals reference typed `evidence_refs`, never arbitrary
  URL lists. A referenced item supplies `source_type`, `source_url`,
  `source_title`, `source_value`, and `evidence_summary` through the existing
  evidence contract.

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
  - `trust_manifest`: `display_name`, `field_statuses`, `source_refs`, `notes`.

  When a canonical collection is populated, keep one collection-level coverage
  row and require exact changed/evidence rows for each edited indexed or nested
  value. This preserves deterministic full-scope enforcement without teaching
  the report model every runtime collection length.

- [ ] Give rentals a deterministic reconciliation identity without adding a
  catalog schema field. Implement one shared
  `rental_reconciliation_target_id(resort_id, rental_name)` helper and use it for
  base indexing, current indexing, report-target validation, changes, and field
  coverage. It returns `<resort_id>:<slugified-rental-name>`, where the slug is
  produced exactly as follows:
  1. normalize the rental name with Unicode `NFKD`, then `casefold()` it;
  2. discard Unicode combining marks;
  3. preserve ASCII `a`-`z` and `0`-`9`, replacing each maximal run of all other
     characters with one `-`;
  4. strip leading/trailing `-` and reject an empty result.

  Fail reconciliation if two rentals under the same destination normalize to
  the same target id. The destination prefix keeps equal provider names in
  different destinations distinct. A name change that produces a different
  slug is not an in-place field change: derive removal of the old rental key and
  addition of the new rental key, and require both targets and their deltas in
  `changes[]`, `reviewed_targets`, and `field_coverage`.

- [ ] Add typed boundary models using the existing Pydantic base:
  - `CatalogBoundaryGateAssessment` with gate name, `pass|fail|unresolved`,
    notes, and non-empty `evidence_refs`;
  - `CatalogIdentitySignalAssessment` with signal type,
    `pass|fail|unresolved`, notes, and non-empty `evidence_refs`;
  - `CatalogDestinationBoundaryAssessment` with candidate destination id,
    exactly the three named hard gates, one or more identity signals, and a
    typed failure route when the candidate does not pass.

  Resolve every ref against unique typed evidence. A passing gate must have at
  least one source-backed evidence item. A passing identity signal must match a
  strong signal type from the spec and reference at least one `official`,
  `open_data`, or `reviewed_editorial` item. Official sources are preferred,
  not globally mandatory; only `official_destination_treatment` inherently
  requires `source_type=official`. Permit boundary-only evidence without a
  matching catalog change only when a gate/signal references it; continue to
  reject unreferenced evidence that has no matching change.

- [ ] Add typed weather models:
  - `CatalogWeatherRequestGeometry` with `latitude`, `longitude`,
    `base_elevation_m`, `mid_elevation_m`, and `upper_elevation_m`;
  - `CatalogWeatherRequestGeometryAssessment` with `ski_area_id`, `before`, and
    `after` only;
  - a Pydantic computed field/property `material_change` that cannot be supplied
    in report JSON because `extra="forbid"` remains active.

  Derive base/mid/upper values by calling the same
  `weather_elevation_points(SkiArea)` helper used by Open-Meteo. The computed
  result is `true` when either coordinate or any derived band differs and
  `false` only when all five values are identical.

- [ ] Use a small set of composable Pydantic `model_validator` methods and
  canonical-set helpers for structural enforcement. Keep evidence/change
  cross-reference checks in `validate_catalog_curation_report`; do not add
  renderer heuristics or ad hoc changed-only detection.

- [ ] Extend `CatalogCurationReport` with typed `reviewed_targets` and
  `destination_boundary_assessments`, explicit `boundary_decision_targets`, and
  explicit `weather_request_geometry_targets` plus
  `weather_request_geometry_assessments`. Normal typed validation enforces:
  - every changed target is declared in `reviewed_targets`;
  - every reviewed target has exactly its required typed field coverage;
  - a full target with changed-only coverage fails even when every change has a
    matching coverage row;
  - duplicate reviewed targets and duplicate candidate assessments fail;
  - every declared boundary decision has an assessment, whether the destination
    is new, changed, removed, or retained;
  - new destination creation fails validation unless all three gates pass and
    at least one identity signal passes;
  - any failed or unresolved candidate requires explicit failure routing;
  - every declared weather geometry target has exactly one assessment;
  - duplicate weather geometry assessments fail and caller-supplied
    `material_change` is rejected.

- [ ] Keep snapshot reconciliation out of the normal Pydantic model. Implement
  `reconcile_catalog_curation_report(...)` in the dedicated reconciliation
  module. Parse base/current resorts and terrain domains through the existing
  loaders, validate/read both trust manifests, map nested entities by stable id,
  map rentals with the shared destination-qualified helper above, and flatten
  canonical fields deterministically.

- [ ] Derive new, removed, and changed targets/field paths from both snapshot
  sets. Require bidirectional parity:
  - every derived delta has an exact `changes[]` row with snapshot-derived
    `before`/`after`, a matching typed `reviewed_target`, and
    `field_coverage.status=changed`;
  - every reported change exists in the derived delta set;
  - new/removed nested entities, terrain domains, destination trust records, and
    terrain-domain trust records cannot hide behind a parent summary row;
  - required retained semantic decisions are validated separately from file
    deltas.

- [ ] During reconciliation, derive the required Madonna weather assessment
  from base/current `madonna-di-campiglio-ski-area` snapshots, including
  coordinates and all three weather bands. Require exact equality with the
  report's typed before/after assessment and use only its computed
  `material_change` result for the post-deploy workflow condition.

- [ ] Extend `validate_catalog_curation` with explicit modes:
  - `--validation-mode typed-only` runs normal report validation for pre-edit
    gate review without snapshot paths;
  - `--validation-mode reconcile` is mandatory for final full/migration
    acceptance and requires all six paths:
    `--base-resorts-path`, `--current-resorts-path`,
    `--base-terrain-domains-path`, `--current-terrain-domains-path`,
    `--base-trust-manifest-path`, and `--current-trust-manifest-path`;
  - repeatable `--required-boundary-target` and
    `--required-weather-geometry-target` arguments define retained semantic
    decisions that snapshots cannot infer. Every required boundary target must
    have a complete passing assessment; a failed/unresolved assessment remains
    valid only as a routed review artifact outside this accepted migration.

  In reconcile mode fail before rendering Markdown when any required path or
  target argument is missing. Keep `validate_catalog_curation_report(report)`
  file-system-free and directly unit-testable.

- [ ] Add focused omission tests before implementation:
  - full target missing one canonical path;
  - full target containing only changed paths;
  - narrow target missing `required_field_paths`;
  - changed `trust_manifest` target omitted from `reviewed_targets`;
  - required retained destination missing its assessment;
  - one missing, failed, or unresolved hard gate;
  - no passing identity signal;
  - unknown/missing typed evidence ref or missing failure route;
  - valid mixed full/narrow report;
  - missing Madonna weather geometry assessment;
  - coordinate-only change computes `material_change=true`;
  - derived elevation-band change computes `material_change=true`;
  - the real `e8f4e11` Madonna snapshot with `base_elevation_m=1550` and
    `summit_elevation_m=2504` derives base/mid/upper request elevations
    1550/2027/2409 m; comparing those with final reviewed geometry computes
    `material_change=true` whenever a final coordinate or derived band differs;
  - identical full geometry computes `material_change=false`;
  - caller-supplied `material_change` is rejected.

- [ ] Add reconciliation tests with temporary parsed snapshots:
  - undeclared new destination fails;
  - undeclared destination trust record fails;
  - undeclared terrain-domain change fails;
  - omitted `terrain_domain:tignes-val-disere` or
    `terrain_domain:matterhorn-ski-paradise` trust record fails independently of
    the terrain-domain catalog delta;
  - a changed trust-manifest `display_name` omitted from `changes[]` or changed
    coverage fails;
  - `test_rental_reconciliation_keys_are_destination_qualified` proves
    `Rent & Go` maps to `pinzolo:rent-go` and
    `folgarida-marilleva:rent-go` in the two destinations without collision;
  - `test_rental_rename_reconciles_as_removal_and_addition` renames
    `Rent & Go` to `Rent and Go`, derives removal of `pinzolo:rent-go` plus
    addition of `pinzolo:rent-and-go`, and fails unless both are reconciled and
    reported;
  - required retained Madonna boundary decision omitted from the report fails;
  - an invented report change absent from snapshots fails;
  - complete reconciled migration fixture passes.

- [ ] Run focused tests and lint:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check \
  app/data/catalog_curation.py \
  app/data/catalog_curation_reconciliation.py \
  app/data/validate_catalog_curation.py \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py
```

- [ ] Commit:

```bash
git add \
  app/data/catalog_curation.py \
  app/data/catalog_curation_reconciliation.py \
  app/data/validate_catalog_curation.py \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py
git commit -m "feat: reconcile typed catalog curation"
```

## Task 6: Build The Reviewed Campiglio Evidence Set

**Files:**
- Inspect: `app/data/resorts.json`
- Inspect: `app/data/resort_trust_manifest.json`
- Prepare changes for: `docs/catalog-curation/2026-06-27-madonna-di-campiglio.json`

- [ ] Before editing either catalog JSON file, populate and validate typed
  `destination_boundary_assessments` for exactly:
  `madonna-di-campiglio`, `pinzolo`, and `folgarida-marilleva`. Each candidate
  must include all three hard gates, at least one strong source-backed identity
  signal, notes, and typed evidence refs. Every ref must resolve to a report
  evidence item with source type, direct URL, title, value, and summary. Search
  pages, internal docs, prior reports, and generated artifacts are not direct
  evidence. Official sources are preferred but open data and reviewed editorial
  evidence remain valid under the source policy; do not impose an official-only
  rule on all gates or signals.

- [ ] Set typed `boundary_decision_targets` to exactly the same three ids. This
  migration-level declaration makes retained Madonna mandatory independently of
  new-destination detection. Final reconciliation in Task 8 also receives these
  three ids as external required targets.

- [ ] Set typed `weather_request_geometry_targets` to exactly
  `madonna-di-campiglio-ski-area`. Final reconciliation also receives this id as
  an external required weather geometry target.

- [ ] Require all three candidates to pass all hard gates and at least one
  identity signal before Task 7. A `fail` or `unresolved` gate blocks the
  accepted three-destination migration. For Pinzolo or Folgarida-Marilleva it
  blocks new destination creation; for retained Madonna it blocks acceptance of
  the reviewed boundary until routed. Record the route as `stay_base`,
  `ski_area`, `ski_sub_area_backlog`, `terrain_domain`,
  `external_pass_context`, or `blocked`. Do not downgrade an unresolved
  assessment to a prose caveat.

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

- [ ] Record before/after Madonna ski-area coordinates, source elevations,
  season months, and exact season windows. Add the required typed
  `weather_request_geometry_assessment` for
  `madonna-di-campiglio-ski-area`; each side contains latitude, longitude, and
  derived base/mid/upper elevations from `weather_elevation_points`. Do not write
  `material_change` into report JSON. The validator/computed field derives it,
  and final snapshot reconciliation verifies both geometry objects. Its outcome
  alone selects the conditional GitHub Actions path in Task 10; it does not
  authorize a local or PR-time backfill.

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
  every stay base and rental, all pass products, every changed namespaced
  trust-manifest record, and the Campiglio terrain domain. Use `scope=full` for
  this migration. Trust targets include these records when changed by the
  base/current snapshots:
  - `destination:madonna-di-campiglio`;
  - `destination:pinzolo`;
  - `destination:folgarida-marilleva`;
  - `terrain_domain:tignes-val-disere`;
  - `terrain_domain:matterhorn-ski-paradise`;
  - `terrain_domain:campiglio-dolomiti-di-brenta`.

- [ ] Build typed field coverage against Task 5's canonical path sets before
  editing JSON. Every path must end as `changed`, `reviewed-no-change`,
  `unresolved`, or `not-applicable`; a changed-only report is invalid.

- [ ] Validate the pre-edit report contract. Task 7 remains blocked until all
  three boundary assessments and full-scope target declarations validate:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
  --validation-mode typed-only \
  --report-path docs/catalog-curation/2026-06-27-madonna-di-campiglio.json
```

## Task 7: Atomically Apply The Campiglio Catalog And Trust Migration

**Files:**
- Modify: `tests/test_seed_data.py`
- Modify: `app/data/resorts.json`
- Modify: `app/data/terrain_domains.json`
- Modify: `app/data/resort_trust_manifest.json`

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

- [ ] Before running `validate_resort_catalog`, complete the matching trust
  migration in `app/data/resort_trust_manifest.json` as part of this same
  working change:
  - update the `destinations["madonna-di-campiglio"]` record for the reviewed
    local geometry, child/domain metric scope, and retained weather identity;
  - add `destinations["pinzolo"]` and
    `destinations["folgarida-marilleva"]`, distinguishing verified fields,
    reviewed adjustments, curated estimates, and unresolved fields;
  - add `terrain_domains["campiglio-dolomiti-di-brenta"]` to the top-level
    mapping with `display_name`, separate `membership`, `terrain_metrics`, and
    `season_window` statuses, direct external `source_refs`, notes, and Pejo's
    exclusion;
  - state that the shared 156 km belongs to the Campiglio terrain domain and
    that weather history remains on `madonna-di-campiglio-ski-area` rather than
    being copied to either new id.

  Use the direct external evidence accepted in Task 6. Tignes-Val d'Isere and
  Matterhorn Ski Paradise were already migrated when Task 2 introduced the
  terrain-domain trust contract; keep those entries intact. Catalog/domain edits
  and all required destination/domain trust parity form one atomic migration.
  Do not run catalog validation and do not commit an intermediate state in which
  any of these four records is absent or stale.

- [ ] Do not call `bootstrap_database()`, historical backfill, or climatology
  rebuild while applying or validating catalog data. This task changes static
  files and tests only.

- [ ] Only after all catalog, domain, and trust-manifest edits above are complete,
  run catalog validation and focused tests:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_seed_data.py tests/test_catalog_validation.py -q
```

- [ ] Commit:

```bash
git add \
  app/data/resorts.json \
  app/data/terrain_domains.json \
  app/data/resort_trust_manifest.json \
  tests/test_seed_data.py
git commit -m "data: atomically model Campiglio catalog and trust"
```

## Task 8: Reconcile And Render The Typed Curation Report

**Files:**
- Modify: `docs/catalog-curation/2026-06-27-madonna-di-campiglio.json`
- Regenerate: `docs/catalog-curation/2026-06-27-madonna-di-campiglio.md`
- Snapshot artifacts only: `/private/tmp/snowcast-campiglio-base/`

- [ ] Start from the already-valid catalog/domain/trust state committed by Task 7.
  Run `validate_resort_catalog` before changing the report. If parity fails,
  return to Task 7 and fix that atomic migration; do not repair or defer required
  trust entries in this report task:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```

- [ ] Replace the one-destination report with a linked three-destination
  migration report. Keep the existing filename so PR #24 has one authoritative
  report rather than competing historical/current reports. This task consumes
  the final catalog, domain, and trust snapshots; it does not mutate those data
  files.

- [ ] Include every changed trust record from the already-valid current manifest
  as a full typed `target_type=trust_manifest` reviewed target with coverage for
  `display_name`, `field_statuses`, `source_refs`, and `notes`. Reconciliation
  determines applicability from snapshots; the expected changed records are:
  - `destination:madonna-di-campiglio`;
  - `destination:pinzolo`;
  - `destination:folgarida-marilleva`;
  - `terrain_domain:tignes-val-disere`;
  - `terrain_domain:matterhorn-ski-paradise`;
  - `terrain_domain:campiglio-dolomiti-di-brenta`.

- [ ] In the typed report, retain the three validated pre-edit boundary
  assessments and declare `scope=full` reviewed targets with complete canonical
  `field_coverage[]` for:
  - three destinations;
  - three ski areas;
  - every retained stay base and rental;
  - every shared/local lift-pass product and representative price;
  - every changed destination and terrain-domain trust-manifest entry;
  - the Campiglio terrain domain.

  Represent manifest `display_name`, `source_refs`, `notes`, and each changed
  `field_statuses.<group>` under `target_type=trust_manifest`; do not hide them
  under destination rows.

- [ ] Preserve conflicts and scope decisions in `evidence[]`/`unresolved_caveats[]`:
  - child metrics are unresolved unless child-scoped evidence exists;
  - the shared 156 km is not child terrain;
  - aggregate lift-count conflicts and any Bergfex fallback are explicit;
  - Pejo is external pass validity, not a domain member;
  - the two new ski-area ids need archive backfill and climatology rebuild;
  - Madonna's snapshot-verified before/after weather request geometry and the
    validator-computed `material_change` outcome determine whether its
    conditional full refetch is required;
  - production search may display multiple domain members until separate dedup work lands.

- [ ] Materialize the immutable actual PR base `ce6090d^2=e8f4e11` into
  temporary files. `e8f4e11` is the deployed/main parent before any PR #24
  changes; using post-merge `ce6090d` would hide the original branch-side
  catalog deltas. Final reconciliation therefore covers all
  `e8f4e11..HEAD` resorts, terrain-domain, and trust-manifest changes. These
  temporary files are review inputs only and are not staged:

  `e8f4e11` predates the canonical top-level `terrain_domains` trust namespace,
  so reconciliation against this immutable base must explicitly allow that one
  legacy omission. The compatibility flag accepts only complete absence on the
  base; malformed base data, current-snapshot omissions, and normal catalog
  validation remain strict.

```bash
rm -rf /private/tmp/snowcast-campiglio-base
mkdir -p /private/tmp/snowcast-campiglio-base
git show e8f4e11:app/data/resorts.json \
  > /private/tmp/snowcast-campiglio-base/resorts.json
git show e8f4e11:app/data/terrain_domains.json \
  > /private/tmp/snowcast-campiglio-base/terrain_domains.json
git show e8f4e11:app/data/resort_trust_manifest.json \
  > /private/tmp/snowcast-campiglio-base/resort_trust_manifest.json
```

- [ ] Reconcile the report against parsed base/current snapshots and render
  Markdown only after reconciliation succeeds:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
  --validation-mode reconcile \
  --allow-legacy-base-trust-without-terrain-domains \
  --report-path docs/catalog-curation/2026-06-27-madonna-di-campiglio.json \
  --base-resorts-path /private/tmp/snowcast-campiglio-base/resorts.json \
  --current-resorts-path app/data/resorts.json \
  --base-terrain-domains-path /private/tmp/snowcast-campiglio-base/terrain_domains.json \
  --current-terrain-domains-path app/data/terrain_domains.json \
  --base-trust-manifest-path /private/tmp/snowcast-campiglio-base/resort_trust_manifest.json \
  --current-trust-manifest-path app/data/resort_trust_manifest.json \
  --required-boundary-target madonna-di-campiglio \
  --required-boundary-target pinzolo \
  --required-boundary-target folgarida-marilleva \
  --required-weather-geometry-target madonna-di-campiglio-ski-area \
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
  docs/catalog-curation/2026-06-27-madonna-di-campiglio.json \
  docs/catalog-curation/2026-06-27-madonna-di-campiglio.md
git commit -m "docs: reconcile Campiglio curation evidence"
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
  tests/test_catalog_curation_reconciliation.py \
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

Recreate the `e8f4e11` baseline with the Task 8 commands first if the temporary
snapshot directory is absent or stale.

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
  --validation-mode reconcile \
  --allow-legacy-base-trust-without-terrain-domains \
  --report-path docs/catalog-curation/2026-06-27-madonna-di-campiglio.json \
  --base-resorts-path /private/tmp/snowcast-campiglio-base/resorts.json \
  --current-resorts-path app/data/resorts.json \
  --base-terrain-domains-path /private/tmp/snowcast-campiglio-base/terrain_domains.json \
  --current-terrain-domains-path app/data/terrain_domains.json \
  --base-trust-manifest-path /private/tmp/snowcast-campiglio-base/resort_trust_manifest.json \
  --current-trust-manifest-path app/data/resort_trust_manifest.json \
  --required-boundary-target madonna-di-campiglio \
  --required-boundary-target pinzolo \
  --required-boundary-target folgarida-marilleva \
  --required-weather-geometry-target madonna-di-campiglio-ski-area \
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

- [ ] Add a current-year window regression using a fixed UTC run-date fixture.
  Assert an `archive_end_date` in the run's current year is forwarded unchanged,
  is not capped at 2025, is greater than or equal to the fixture's latest
  existing Madonna archive date, and is used for both Madonna and the combined
  Pinzolo/Folgarida-Marilleva invocation. For Madonna also assert
  `force_refetch=true` so every existing date is rewritten under new geometry.

- [ ] Run the selector and CLI tests, not live commands:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_open_meteo.py \
  tests/test_snow_climatology.py -q
```

No implementation, PR verification, or local completion command may mutate
production weather. After merge and deployment, the owner manually triggers
these GitHub Actions workflows in order.

Immediately before dispatch, run this read-only production query and record the
result in the operator handoff:

```sql
SELECT
    MAX(observed_on) AS latest_existing_archive_date,
    ((CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date - 1) AS utc_previous_day,
    COUNT(DISTINCT observed_on) FILTER (
        WHERE EXTRACT(YEAR FROM observed_on) = EXTRACT(
            YEAR FROM (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
        )
    ) AS current_year_days
FROM raw_weather_history
WHERE resort_id = 'madonna-di-campiglio-ski-area'
  AND record_type = 'archive';
```

Set `archive_end_date` to `latest_existing_archive_date`. The conservative
alternative is `utc_previous_day`, but use it only after asserting
`utc_previous_day >= latest_existing_archive_date`. The chosen value must not be
hardcoded, must include any current-year archive rows, and must be reused for
both backfill runs. `baseline_end_year=2025` remains a separate climatology
choice and does not cap archive refetch.

If Task 6's typed weather assessment computes `material_change=true`, first run
**Backfill Historical Weather** for Madonna with every dispatch input set as
follows:

| Input | Value |
| --- | --- |
| `start_date` | `1991-01-01` |
| `end_date` | `<archive_end_date>` |
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

`force_refetch=true` is required for Madonna so every archive date already in
the database, including current-year rows, is fetched and rewritten under the
reviewed request geometry. Do not substitute the destructive `rebuild` mode.

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
| `end_date` | `<archive_end_date>` |
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
the new-id workflow pair is still required and uses the same derived
`archive_end_date`.

- [ ] After each backfill, run this read-only operator verification. Require
  `last_observed_on >= archive_end_date` for every dispatched target. When the
  chosen end date is in the current UTC year, require `current_year_days > 0`:

```sql
SELECT
    resort_id,
    MAX(observed_on) AS last_observed_on,
    COUNT(DISTINCT observed_on) FILTER (
        WHERE EXTRACT(YEAR FROM observed_on) = EXTRACT(
            YEAR FROM (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
        )
    ) AS current_year_days
FROM raw_weather_history
WHERE resort_id IN (
    'madonna-di-campiglio-ski-area',
    'pinzolo-ski-area',
    'folgarida-marilleva-ski-area'
)
  AND record_type = 'archive'
GROUP BY resort_id
ORDER BY resort_id;
```

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
  tests/test_catalog_curation_reconciliation.py \
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
  Pinzolo, and Folgarida-Marilleva; all three hard gates and at least one strong
  source-backed identity signal pass for each decision, including retained
  Madonna. Gate/signal evidence resolves through typed evidence ids with source
  type, URL, title, value, and summary.
- The 156 km aggregate is present only on `campiglio-dolomiti-di-brenta` unless independent child evidence supports a coincident value.
- The shared pass is correctly modeled as regional-network coverage with Pejo external; local products are non-default alternatives.
- Pydantic rejects terrain domains with fewer than two distinct destination ids;
  cross-catalog validation rejects unknown refs; every domain has direct
  membership/metric `source_urls`.
- The trust manifest has validated `terrain_domains` entries for
  Tignes-Val d'Isere, Matterhorn Ski Paradise, and Campiglio with membership,
  terrain-metric, and season-window statuses, display names, direct refs, and
  notes. Every changed destination/domain trust record is a namespaced typed
  report target.
- Task 7 adds or updates the Madonna, Pinzolo, Folgarida-Marilleva, and
  Campiglio terrain-domain trust records in the same change as the related
  catalog/domain data, then validates and commits that state atomically. Task 8
  changes only the typed report and its rendered Markdown.
- The typed curation report declares full/narrow reviewed targets, includes
  `trust_manifest` targets, covers every canonical full-scope path, and links
  directly to evidence; changed-only full coverage fails tests.
- Final full/migration validation reconciles parsed `e8f4e11` base snapshots
  against current `HEAD` resorts, terrain domains, and trust manifest. This is
  the deployed/main parent before PR #24 and covers original plus later PR
  deltas. Derived and reported changes agree bidirectionally; undeclared
  new/removed/changed targets or fields and invented report changes fail.
- Rental reconciliation uses the shared
  `<resort_id>:<slugified-rental-name>` key without a catalog schema change;
  tests prove equal names in separate destinations remain distinct and a rename
  is reported as removal of the old key plus addition of the new key.
- Existing Madonna weather identity is unchanged. Local geometry and season
  values follow the blocking source hierarchy. The report contains the required
  before/after coordinate plus derived base/mid/upper geometry, and only the
  validator-computed `material_change` controls whether the conditional Madonna
  archive refetch is required.
- Geometry regression starts from the actual `e8f4e11` Madonna
  `base_elevation_m=1550` and computes `material_change=true` whenever final
  reviewed geometry changes coordinates or a derived elevation band.
- Reconciliation tests separately reject omitted terrain-domain trust targets
  and changed trust `display_name` fields missing from report changes/coverage.
- Selector/CLI tests and a response-level API regression preserve all three
  weather targets and both Madonna response ids.
- The completion handoff contains exact post-deploy GitHub Actions inputs for
  the 1991-01-01 through operator-derived `archive_end_date` window and baseline
  2025 climatology. The end date is not earlier than Madonna's latest existing
  raw archive observation, both destination groups use it, and operator checks
  prove current-year rows are included. No bootstrap, local verification, or PR
  command mutates production weather.
- Validator, model descriptions, domain docs, ADR, curation skill, and review skill all express the same boundary rule.
- Ski sub-areas and production shared-domain result deduplication remain out of
  scope.
- Task 1 design review is complete after quality-review remediation with no
  remaining High findings pending re-review and no unresolved owner decision;
  feature review remains planned until Task 11 runs on the implemented diff.
- Focused tests, catalog/report validation, Ruff, advisory review, and GitHub checks pass or any external check blocker is explicitly reported.
