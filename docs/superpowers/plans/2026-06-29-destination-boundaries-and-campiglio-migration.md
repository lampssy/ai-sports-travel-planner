# Destination Boundaries And Campiglio Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make destination identity a consistent trip-planning boundary, enforce that terrain domains join ski areas from multiple destinations, and replace PR #24's single aggregate Madonna di Campiglio entry with three independently useful destinations under one connected Campiglio terrain domain.

**Architecture:** `Destination` owns the trip/stay choice, `SkiArea` owns local weather and operational evidence, and `TerrainDomain` owns ski-connected aggregate terrain spanning destinations. The existing `madonna-di-campiglio-ski-area` id remains stable so its historical weather and climatology remain attached. New Pinzolo and Folgarida-Marilleva ski-area ids start without archive evidence and are backfilled explicitly after deployment. Shared-pass coverage outside the connected domain remains `regional_network` external validity rather than creating terrain connectivity.

**Tech Stack:** Python 3.13, Pydantic v2, JSON static catalogs, pytest, Ruff, Markdown/ADRs, Snowcast Codex skills, GitHub CLI.

---

## Scope And Guardrails

- Classification: `review-gated`, using the full design flow because this changes
  durable catalog identity, weather-evidence ownership, pass scope, and ranking
  inputs.
- Developer Decision Checkpoint: resolved by the owner in the accepted spec;
  use three destinations and ski areas under one connected terrain domain, keep
  ski sub-areas parked, and apply the same boundary rule catalog-wide.
- ADR status: required in Task 3.
- Advisory review status: design review required before implementation and
  feature review required before the final PR update.
- Work on `codex/catalog-curation-madonna-di-campiglio`, the existing branch for draft PR #24.
- Merge current `origin/main` before changing catalog data. Preserve all catalog entries merged after PR #24 was opened.
- Do not change or replace `madonna-di-campiglio-ski-area`.
- Do not copy the 156 km, aggregate lift count, elevation range, or difficulty split into a child ski area unless a child-scoped source supports the value.
- Do not add Pejo to `campiglio-dolomiti-di-brenta`; it is pass-accessible but not ski-connected to the three modeled destinations.
- Do not implement ski sub-areas or production shared-domain result deduplication in this change.
- Keep generated curation Markdown subordinate to the typed JSON report.
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

- [ ] Confirm the branch and worktree before integrating main:

```bash
git status --short --branch
git branch --show-current
git fetch origin main
```

Expected branch: `codex/catalog-curation-madonna-di-campiglio`. Stop if unrelated uncommitted changes appear.

- [ ] Merge current main without rebasing the published PR branch:

```bash
git merge --no-edit origin/main
```

Resolve catalog conflicts by retaining every destination/domain from `origin/main`, then retaining the current Madonna entry only as the input to the later split. Do not resolve by accepting either complete JSON file wholesale.

- [ ] Establish a passing post-merge baseline:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_validation.py \
  tests/test_seed_data.py \
  tests/test_repository.py -q
```

- [ ] Run a Snowcast `design-review` against the accepted spec with the `backend-api` and `data-trust-source-integrity` reviewers. Resolve Blocker and High findings before Task 2. Record accepted Medium/Low residuals in the spec's Advisory Review section.

- [ ] If the merge creates a merge commit, keep it. Do not squash or rewrite the existing PR history.

## Task 2: Enforce The Cross-Destination Terrain-Domain Invariant

**Files:**
- Modify: `app/data/validate_resort_catalog.py`
- Modify: `app/domain/models.py`
- Test: `tests/test_catalog_validation.py`

- [ ] Add a failing catalog-validation test:

```python
def test_validate_catalog_rejects_terrain_domain_with_one_destination(
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
                }
            ],
            "metric_scope": "aggregate",
            "total_piste_km": 100,
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
        "terrain domain must span at least two destinations" in issue
        for issue in error.value.issues
    )
```

- [ ] Run the test and confirm it fails for the missing invariant:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_catalog_validation.py::test_validate_catalog_rejects_terrain_domain_with_one_destination -q
```

- [ ] In `_validate_loaded_catalog`, validate distinct owning destinations independently of duplicate/unknown ski-area validation:

```python
referenced_resort_ids = {
    ski_area_ref.resort_id for ski_area_ref in terrain_domain.ski_area_refs
}
if len(referenced_resort_ids) < 2:
    issues.append(
        f"{terrain_domain.terrain_domain_id}: terrain domain must span "
        "at least two destinations"
    )
```

Place this after processing a domain's refs so an invalid reference can report both structural and reference failures.

- [ ] Update Pydantic field descriptions without changing serialized contracts:
  - `Destination.resort_id`: stable trip-planning destination identity.
  - `SkiArea.ski_area_id`: smallest durable local terrain unit owning weather/operations; it may connect by lift/piste to other ski areas.
  - `TerrainDomain`: ski-connected aggregate spanning at least two destinations; shared ticket validity alone is insufficient.

- [ ] Run focused tests and lint:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_validation.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check \
  app/domain/models.py app/data/validate_resort_catalog.py \
  tests/test_catalog_validation.py
```

- [ ] Commit:

```bash
git add app/domain/models.py app/data/validate_resort_catalog.py tests/test_catalog_validation.py
git commit -m "feat: enforce destination-spanning terrain domains"
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

## Task 5: Build The Reviewed Campiglio Evidence Set

**Files:**
- Inspect: `app/data/resorts.json`
- Inspect: `app/data/resort_trust_manifest.json`
- Prepare changes for: `docs/catalog-curation/2026-06-27-madonna-di-campiglio.json`

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

- [ ] Re-review local terrain/elevation/season pages for Madonna, Pinzolo, and Folgarida-Marilleva. Store only values whose source scope matches the child ski area. Keep the existing 156 km and difficulty split as aggregate-domain evidence.

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

- [ ] Build a field-coverage worksheet for all destination, ski-area, stay-base, rental, pass-product, trust-manifest, and terrain-domain fields before editing JSON. Every field must end as `changed`, `reviewed-no-change`, `unresolved`, or `not-applicable` in the typed report.

## Task 6: Test-Drive And Apply The Campiglio Catalog Migration

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

Add only reviewed `total_lift_count`, elevation, difficulty, season, and additional source fields from Task 5; omitted optional values must be documented as unresolved.

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

## Task 7: Update Trust And Rewrite The Typed Curation Report

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

- [ ] In the typed report, include complete `field_coverage[]` for:
  - three destinations;
  - three ski areas;
  - every retained stay base and rental;
  - every shared/local lift-pass product and representative price;
  - three trust-manifest entries;
  - the Campiglio terrain domain.

- [ ] Preserve conflicts and scope decisions in `evidence[]`/`unresolved_caveats[]`:
  - child metrics are unresolved unless child-scoped evidence exists;
  - the shared 156 km is not child terrain;
  - aggregate lift-count conflicts and any Bergfex fallback are explicit;
  - Pejo is external pass validity, not a domain member;
  - the two new ski-area ids need archive backfill and climatology rebuild;
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

## Task 8: Reconcile Repository And Search Regression Expectations

**Files:**
- Modify if required: `tests/test_repository.py`
- Modify if required: `tests/test_services.py`
- Modify if required: `tests/test_search_models.py`
- Do not modify merely to force old rank order.

- [ ] Run shared catalog/repository/search tests:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest \
  tests/test_repository.py \
  tests/test_services.py \
  tests/test_search_models.py -q
```

- [ ] If repository fixtures contain a one-destination `TerrainDomain`, add a second fixture destination and ref so the test models the real invariant. Do not weaken the validator.

- [ ] Update brittle fixture-count or expected-name assertions only where the two newly valid destinations change catalog cardinality. Keep service tests behavioral: destination eligibility, grouping key semantics, evidence identity, and penalties rather than an exact production rank position.

- [ ] Add no production search dedup behavior in this task. If current search returns multiple Campiglio-domain destinations, record it in the report and scoring backlog rather than hiding destinations in seed data.

- [ ] Run affected lint and commit only if test files changed:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check \
  tests/test_repository.py tests/test_services.py tests/test_search_models.py
git add tests/test_repository.py tests/test_services.py tests/test_search_models.py
git diff --cached --quiet || git commit -m "test: align fixtures with destination boundaries"
```

## Task 9: Verify Catalog, Ranking Inputs, And Weather Selection

**Files:**
- Verify: all changed files
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
  tests/test_search_models.py -q
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

- [ ] Confirm weather commands select each new destination without running a network backfill. Use command help and selector-level tests; do not invoke live archive downloads as part of PR verification:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.backfill_historical_weather --help
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.rebuild_snow_climatology --help
rg -n "madonna-di-campiglio-ski-area|pinzolo-ski-area|folgarida-marilleva-ski-area" \
  app/data/resorts.json
```

Document post-deploy operator commands without running them locally:

```bash
uv run --no-config python -m app.data.backfill_historical_weather --resort pinzolo
uv run --no-config python -m app.data.backfill_historical_weather --resort folgarida-marilleva
uv run --no-config python -m app.data.rebuild_snow_climatology --resort pinzolo
uv run --no-config python -m app.data.rebuild_snow_climatology --resort folgarida-marilleva
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

## Task 10: Feature Review And Update Draft PR #24

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
  tests/test_services.py -q
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
  - the preserved Madonna weather id and required post-deploy backfill for two new ids;
  - direct links to the rendered curation evidence and ADR;
  - validation, tests, ranking-diagnostic result, advisory-review status, and residual caveats;
  - that both catalog skills were updated outside the repo.

- [ ] Keep the PR as draft until checks pass and the owner reviews the new entity boundaries and curated estimates.

## Completion Criteria

- PR #24 contains exactly three Campiglio destinations with three stable local ski-area ids and one shared connected domain.
- The 156 km aggregate is present only on `campiglio-dolomiti-di-brenta` unless independent child evidence supports a coincident value.
- The shared pass is correctly modeled as regional-network coverage with Pejo external; local products are non-default alternatives.
- The typed curation report covers every applicable field and links directly to evidence.
- Existing Madonna weather identity is unchanged; no bootstrap or verification command deletes historical data.
- Validator, model descriptions, domain docs, ADR, curation skill, and review skill all express the same boundary rule.
- Focused tests, catalog/report validation, Ruff, advisory review, and GitHub checks pass or any external check blocker is explicitly reported.
