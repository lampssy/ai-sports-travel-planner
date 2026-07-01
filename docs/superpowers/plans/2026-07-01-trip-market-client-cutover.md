# Trip-Market Client Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch all Snowcast surfaces to the normalized trip-market contract, remove the old nested model, and prepare one evidence-safe deployment.

**Architecture:** Update durable trip, handoff, public-page, web, and mobile contracts together, then remove all legacy catalog/search paths. Finalize the database schema only after every application consumer uses stable region/destination/base/area/pass IDs. Deploy from a verified backup with before/after evidence counts.

**Tech Stack:** Python/FastAPI/PostgreSQL, React/TypeScript/Vite, Flutter/Dart, pytest, Vitest/Playwright, Ruff.

---

## Decision Gate Before Execution

- Classification: review-gated, coordinated cutover
- High-risk domains: user trip schema, web/mobile contracts, public routes,
  booking handoff, production migration and rollback
- Resolved decisions: no external-user compatibility layer; pre-public trip
  state may be cleared; weather evidence must be preserved; mixed old/new
  application/schema versions are unsupported
- ADR status: ADR 0009 accepted
- Advisory status: focused feature review required after this phase

### Task 1: Replace Saved-Trip And Event Identity

**Files:**
- Modify: `app/domain/models.py:1023-1314`
- Modify: `app/data/database.py:320-450`
- Modify: `app/data/repositories.py:1629-1922`
- Modify: `app/domain/trip_companion.py`
- Modify: `tests/test_repository.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing current-trip contract tests**

```python
def test_current_trip_uses_full_configuration_identity() -> None:
    trip = CurrentTrip(
        ski_region_id="tignes-val-disere",
        ski_region_name="Tignes - Val d'Isere",
        stay_destination_id="tignes",
        stay_destination_name="Tignes",
        stay_base_id="tignes-val-claret",
        stay_base_name="Val Claret",
        focus_ski_area_id="tignes-ski-area",
        focus_ski_area_name="Tignes",
        lift_pass_product_id="tignes-val-disere-ski-pass",
        lift_pass_product_name="Tignes - Val d'Isere ski pass",
        travel_month=3,
        trip_start_date=None,
        trip_end_date=None,
        booking_status="planning",
        created_at="2026-07-01T10:00:00+00:00",
        updated_at="2026-07-01T10:00:00+00:00",
        last_checked_at=None,
    )
    assert trip.stay_base_id == "tignes-val-claret"
```

API tests must reject a region/destination mismatch, a base that does not belong
to the destination, a base/area pair without an access edge, and a pass that is
not available from the destination or does not cover the focus area.

- [ ] **Step 2: Replace trip request/response fields**

`CurrentTrip` and `UpsertCurrentTripRequest` use these stable IDs and display
names:

- `ski_region_id`, `ski_region_name`;
- `stay_destination_id`, `stay_destination_name`;
- `stay_base_id`, `stay_base_name`;
- `focus_ski_area_id`, `focus_ski_area_name`;
- `lift_pass_product_id`, `lift_pass_product_name`;
- travel month or exact dates, booking status, timestamps.

Remove `resort_id`, `selected_area_name`, and name-only selection aliases.

- [ ] **Step 3: Recreate disposable trip/event tables under new FKs**

Inside one migration transaction:

1. delete `companion_events`, `user_current_trip`, and unused singleton
   `current_trip` rows;
2. recreate `user_current_trip` with FKs to normalized region, destination,
   base, area, and pass tables;
3. recreate `companion_events` with the same stable trip identity needed for
   event audit;
4. retain users, sessions, and devices.

The migration is intentionally destructive only for pre-public trip/event data.
It must not touch weather tables.

- [ ] **Step 4: Update repository and companion behavior**

Validate the complete saved relationship chain against one catalog graph:
region -> destination -> base -> access -> focus area and destination -> pass ->
focus-area coverage. Current conditions and deltas load by
`focus_ski_area_id`; region/domain/pass IDs never become condition keys.

- [ ] **Step 5: Run focused tests and commit**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_repository.py tests/test_api.py -k 'current_trip or companion or device' -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/models.py app/domain/trip_companion.py app/data/database.py app/data/repositories.py tests/test_api.py tests/test_repository.py
git add app/domain/models.py app/domain/trip_companion.py app/data/database.py app/data/repositories.py tests/test_api.py tests/test_repository.py
git commit -m "feat: save normalized trip configurations"
```

### Task 2: Update Public Pages And Accommodation Handoff

**Files:**
- Modify: `app/api/routes.py:386-430`
- Modify: `app/public_pages.py`
- Modify: `app/data/repositories.py:1629-1685`
- Modify: `tests/test_public_pages.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing ID-based route tests**

Test `/ski-destinations/{stay_destination_id}` renders stay-destination facts
and its accessible ski areas without blended weather. Test outbound handoff
requires `stay_base_id` and `focus_ski_area_id` that form a real access edge.

- [ ] **Step 2: Replace route and click-record contracts**

```python
@router.get("/outbound/accommodation/{stay_destination_id}")
def outbound_accommodation_redirect(
    stay_destination_id: str,
    stay_base_id: str,
    focus_ski_area_id: str,
    request: Request,
    source_surface: str = Query(min_length=1),
) -> RedirectResponse:
    graph = CatalogGraph.from_snapshot(CatalogRepository().get_snapshot())
    destination = graph.destinations_by_id.get(stay_destination_id)
    base = graph.bases_by_id.get(stay_base_id)
    access = next(
        (
            item
            for item in graph.accesses_by_base_id.get(stay_base_id, ())
            if item.ski_area_id == focus_ski_area_id
        ),
        None,
    )
    if (
        destination is None
        or base is None
        or base.stay_destination_id != stay_destination_id
        or access is None
    ):
        raise HTTPException(status_code=404, detail="Unknown trip configuration")
    target_url = build_accommodation_link(
        resort_name=destination.name,
        country=destination.country,
    )
    OutboundBookingClickRepository().record_click(
        created_at=datetime.now(UTC).isoformat(),
        stay_destination_id=stay_destination_id,
        stay_base_id=stay_base_id,
        focus_ski_area_id=focus_ski_area_id,
        target_url=target_url,
        source_surface=source_surface,
        request_id=request.headers.get("x-request-id"),
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse(url=target_url, status_code=307)
```

Store IDs in `outbound_booking_clicks`; clear old pre-public click rows before
recreating its FKs. Keep provider URL generation based on stay destination name
and country.

Public destination pages list the ski areas reachable through their bases. If
weather is shown, render each area's conditions under that area's explicit
name; do not choose an undocumented primary area and do not synthesize region
weather.

- [ ] **Step 3: Update sitemap and route-order tests**

Generate `/ski-destinations/{stay_destination_id}` URLs from active catalog
destinations. Remove `/ski-resorts/{resort_id}` because the product is not
externally launched and no redirect compatibility is required.

- [ ] **Step 4: Run focused tests and commit**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_public_pages.py tests/test_api.py -k 'outbound or public or sitemap or robots' -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/api/routes.py app/public_pages.py app/data/repositories.py tests/test_public_pages.py tests/test_api.py
git add app/api/routes.py app/public_pages.py app/data/repositories.py tests/test_public_pages.py tests/test_api.py
git commit -m "feat: use stay destinations in public handoff routes"
```

### Task 3: Cut The React App Over To Recommendation Groups

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/ui/TripEntityStack.tsx`
- Modify: `frontend/src/ui/snowcastCopy.ts`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/tests/e2e/app.spec.ts`

- [ ] **Step 1: Replace TypeScript fixtures and write failing UI tests**

Test that a card headed `Chamonix Valley` shows `Stay in Argentiere - Ski
Grands Montets`, selected-area evidence seasons, one recommended pass, and an
alternative count. Test selecting an alternative changes all concrete fields
without changing the top-level market label.

- [ ] **Step 2: Replace frontend contracts**

Mirror backend `RecommendationGroup`, `TripConfiguration`, `PassOption`, and
`ResilienceSummary` types exactly. Remove `SearchResult` and old aliases.

`saveCurrentTrip()` sends the active configuration's region, destination, base,
area, pass, and date IDs. `buildAccommodationBookingRedirectUrl()` sends stable
destination/base/area IDs.

- [ ] **Step 3: Update the search card hierarchy**

Card hierarchy:

1. ski-region/trip-market name;
2. `Stay in {base} - Ski {focus area}`;
3. primary selected-area conditions and evidence seasons;
4. recommended pass/access summary;
5. trip-fit score and bounded alternative count.

The dossier compares alternative configurations and pass products. Resilience
is labeled as fallback-area context, not a blended snow score. Do not add hotel
property cards.

- [ ] **Step 4: Update route identity**

Use `/recommendations/{ski_region_id}` plus session search state for the dossier.
Do not overload a stay destination ID as recommendation-group identity.

- [ ] **Step 5: Run unit/build verification**

```bash
cd frontend
npm test -- --run
npm run build
```

Expected: tests and TypeScript build pass.

- [ ] **Step 6: Run Playwright desktop/mobile visual checks**

Start the backend and Vite server, then run:

```bash
cd frontend
npx playwright test tests/e2e/app.spec.ts
```

Inspect at least 1440x900 and 390x844 screenshots. Verify no overlapping card
text, pass labels, evidence blocks, or alternative controls.

- [ ] **Step 7: Commit web cutover**

```bash
git add frontend/src frontend/tests/e2e/app.spec.ts
git commit -m "feat: show trip market recommendation groups"
```

### Task 4: Cut The Flutter Client Over

**Files:**
- Modify: `mobile/lib/main.dart`
- Modify: `mobile/test/smoke_test.dart`

- [ ] **Step 1: Write failing decode and rendering tests**

Add a v3 response fixture and assert the mobile card renders trip-market name,
base, focus area, recommended pass, and selected-area evidence. Add current-trip
serialization assertions for all stable IDs.

- [ ] **Step 2: Replace mobile DTOs and API requests**

Decode the same group/configuration fields as web. Remove resort/name-only trip
selection. Saving a trip sends the active configuration IDs.

- [ ] **Step 3: Preserve mobile product scope**

Show one compact group card and a concrete configuration detail. Do not rebuild
the full web dossier or introduce property inventory. Current-trip conditions
remain keyed/displayed by focus ski area.

- [ ] **Step 4: Run Flutter verification and commit**

```bash
cd mobile
flutter analyze
flutter test
```

```bash
git add mobile/lib/main.dart mobile/test/smoke_test.dart
git commit -m "feat: use trip market search on mobile"
```

### Task 5: Update Weather Jobs And Data-Quality Audit

**Files:**
- Modify: `app/data/backfill_historical_weather.py`
- Modify: `app/data/rebuild_snow_climatology.py`
- Modify: `app/data/refresh_conditions.py`
- Modify: `app/data/reconcile_recent_archive.py`
- Modify: `app/data/audit_data_quality.py`
- Modify: `.github/workflows/backfill-historical-weather.yml`
- Modify: `.github/workflows/rebuild-snow-climatology.yml`
- Modify: `.github/workflows/refresh-conditions.yml`
- Modify: `.github/workflows/reconcile-recent-archive.yml`
- Modify: `tests/test_conditions.py`
- Modify: `tests/test_snow_climatology.py`
- Modify: `tests/test_data_quality_audit.py`

- [ ] **Step 1: Write failing normalized target-selection tests**

Test all weather commands support:

- `--ski-area ID` for exact area selection;
- `--stay-destination ID` for the distinct areas reachable from that
  destination's bases;
- no target for every active ski area;
- unknown IDs as explicit errors;
- duplicate access paths deduplicated by `ski_area_id`.

For Chamonix, a stay-destination target must select every explicitly accessible
area; for a single-area destination it selects one. Remove `--resort` tests.

- [ ] **Step 2: Centralize area target resolution**

Create one shared helper in `app/data/catalog_repository.py`:

```python
def select_active_ski_areas(
    snapshot: CatalogSnapshot,
    *,
    ski_area_ids: tuple[str, ...] = (),
    stay_destination_ids: tuple[str, ...] = (),
) -> tuple[SkiArea, ...]:
    areas_by_id = {area.ski_area_id: area for area in snapshot.ski_areas}
    bases_by_destination: dict[str, set[str]] = defaultdict(set)
    for base in snapshot.stay_bases:
        bases_by_destination[base.stay_destination_id].add(base.stay_base_id)
    access_by_base: dict[str, set[str]] = defaultdict(set)
    for access in snapshot.ski_area_access:
        access_by_base[access.stay_base_id].add(access.ski_area_id)

    unknown_area_ids = set(ski_area_ids) - areas_by_id.keys()
    known_destination_ids = {
        item.stay_destination_id for item in snapshot.stay_destinations
    }
    unknown_destination_ids = set(stay_destination_ids) - known_destination_ids
    if unknown_area_ids or unknown_destination_ids:
        raise ValueError(
            "unknown catalog targets: "
            f"areas={sorted(unknown_area_ids)}, "
            f"stay_destinations={sorted(unknown_destination_ids)}"
        )

    selected_ids = set(ski_area_ids)
    for destination_id in stay_destination_ids:
        for base_id in bases_by_destination[destination_id]:
            selected_ids.update(access_by_base[base_id])
    if not ski_area_ids and not stay_destination_ids:
        selected_ids.update(areas_by_id)
    return tuple(areas_by_id[item] for item in sorted(selected_ids))
```

Implement it by following base and access records, then sorting unique area IDs.
All four weather commands must call this helper rather than reimplementing
catalog traversal.

- [ ] **Step 3: Update GitHub Actions inputs**

Expose optional comma-separated `ski_area_ids` and `stay_destination_ids` inputs.
Build the corresponding CLI arguments and leave both empty for all active areas.
Do not retain an ambiguous `resort_ids` input.

- [ ] **Step 4: Normalize data-quality ownership**

Audit the full `CatalogSnapshot` by entity type. Emit bounded gauges using
`entity_type`, `entity_id`, `field_group`, and trust/factor status. Continue
checking weather/archive/climatology coverage by `ski_area_id`. Remove logic that
assumes every area, base, pass, or rental is nested below one resort.

- [ ] **Step 5: Run job/audit tests and commit**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_conditions.py tests/test_snow_climatology.py tests/test_data_quality_audit.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/backfill_historical_weather.py app/data/rebuild_snow_climatology.py app/data/refresh_conditions.py app/data/reconcile_recent_archive.py app/data/audit_data_quality.py tests/test_conditions.py tests/test_snow_climatology.py tests/test_data_quality_audit.py
git add app/data/backfill_historical_weather.py app/data/rebuild_snow_climatology.py app/data/refresh_conditions.py app/data/reconcile_recent_archive.py app/data/audit_data_quality.py app/data/catalog_repository.py .github/workflows/backfill-historical-weather.yml .github/workflows/rebuild-snow-climatology.yml .github/workflows/refresh-conditions.yml .github/workflows/reconcile-recent-archive.yml tests/test_conditions.py tests/test_snow_climatology.py tests/test_data_quality_audit.py
git commit -m "feat: target weather jobs by normalized ski area"
```

### Task 6: Update Catalog Curation And Review Contracts

**Files:**
- Modify: `app/data/catalog_policy.py`
- Modify: `app/data/catalog_curation.py`
- Modify: `app/data/catalog_curation_reconciliation.py`
- Modify: `app/data/validate_catalog_curation.py`
- Modify: `tests/test_catalog_curation.py`
- Modify: `tests/test_catalog_curation_reconciliation.py`
- Modify: `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`
- Modify: `/Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md`

- [ ] **Step 1: Write failing normalized-target coverage tests**

Replace destination-nested target paths with entity-qualified paths for regions,
stay destinations, bases, ski areas, access links, domains, passes, rentals, and
trust entries. Require every changed relation and both sides of an access link
to appear in reconciliation.

- [ ] **Step 2: Replace reconciliation inputs**

CLI contract:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
  reconcile REPORT.json \
  --base-catalog-path BASE/catalog.json \
  --current-catalog-path app/data/catalog.json \
  --base-trust-manifest-path BASE/resort_trust_manifest.json \
  --current-trust-manifest-path app/data/resort_trust_manifest.json \
  --markdown-output REPORT.md
```

Remove separate resorts/terrain-domain arguments. Reconciliation parses typed
snapshots and derives exact entity/field/link deltas.

- [ ] **Step 3: Update both global skills consistently**

The curation skill must:

- inspect linked regions, destinations, access, passes, and domains first;
- edit `catalog.json`, not removed files;
- treat stay-destination and ski-area identity independently;
- require source-backed access edges and pass/domain scope;
- preserve one destination per PR by default and existing batch rules;
- run normalized validation and reconciliation before PR creation.

The review skill must check the same ownership rules, no Cartesian/invented
access, no copied aggregate metrics, stable IDs, evidence links, and full field
coverage.

- [ ] **Step 4: Run curation tests and skill validation**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/catalog_policy.py app/data/catalog_curation.py app/data/catalog_curation_reconciliation.py app/data/validate_catalog_curation.py tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py
```

Run the skill-authoring/skill validation command documented by the installed
skill-creator tooling against both skill directories.

- [ ] **Step 5: Commit repo-owned curation changes**

```bash
git add app/data/catalog_policy.py app/data/catalog_curation.py app/data/catalog_curation_reconciliation.py app/data/validate_catalog_curation.py tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py
git commit -m "feat: curate normalized catalog relationships"
```

Global skill files are outside the repository and are reported separately in
the final handoff.

### Task 7: Remove The Legacy Catalog And Search Model

**Files:**
- Delete: `app/data/resorts.json`
- Delete: `app/data/terrain_domains.json`
- Delete: `app/data/catalog_migration.py`
- Delete: `app/data/catalog_migration_overrides.json`
- Delete: `app/data/loader.py`
- Delete: `app/data/compare_ranking.py`
- Delete: `app/domain/ranking_comparison.py`
- Delete: `app/domain/search_service.py`
- Delete: `app/domain/search_scoring.py`
- Delete: `app/data/resort_acquisition/`
- Delete: `tests/test_resort_acquisition.py`
- Delete: `tests/test_compare_ranking.py`
- Delete: `tests/test_ranking_comparison.py`
- Modify: `app/domain/models.py`
- Modify: `app/domain/resort_fit.py`
- Modify: `app/domain/search_models.py`
- Modify: `app/data/database.py`
- Modify: `app/data/repositories.py`
- Modify: `tests/conftest.py`
- Modify: `docs/operating-model/advisory-reviewers.md`
- Modify/remove legacy tests that only assert the old contract

- [ ] **Step 1: Add absence/retired-version tests before deletion**

Assert `search_v1` and `search_v2` receive a clear invalid-model error, canonical
loading only reads `catalog.json`, and no database column/table requires
destination-owned ski areas.

- [ ] **Step 2: Finalize schema cleanup**

After clearing disposable trip/click/event rows and recreating their normalized
tables:

- drop `resorts`, legacy `rentals`, and `stay_base_skill_levels`;
- drop `ski_areas.resort_id` and `stay_bases.resort_id`;
- drop legacy destination compatibility columns/JSON fields;
- keep `ski_areas(ski_area_id)` and all evidence FKs intact;
- ensure normalized catalog tables are the only bootstrap target.

- [ ] **Step 3: Remove legacy domain and diagnostic code**

Delete `Destination`, `TerrainGroup`, old nested `StayBase`, old `SearchResult`,
old `TripOption`, old service/scoring, and synthetic ranking-comparison CLI/tests.
Move any shared primitives still needed by catalog/search v3 into focused modules
before deletion.

Delete the unused static `resort_acquisition` subsystem and its large test file;
the reviewed catalog-curation skill is the supported static acquisition path.
Remove its references from active reviewer guidance and test configuration.
Historical specs/plans may retain references as history.

- [ ] **Step 4: Replace old seed/loader/repository tests**

Keep behavioral coverage for catalog validation, repository reads, search,
planning, API, evidence preservation, and data quality. Delete tests only when
their old contract no longer exists; do not lower coverage to make cleanup pass.

- [ ] **Step 5: Run dead-reference scan**

```bash
rg -n 'resorts\.json|terrain_domains\.json|ResortRepository|\bDestination\b|TerrainGroup|SearchResult|search_v1|search_v2|compare_ranking|ranking_comparison' app tests frontend mobile docs README.md PROJECT.md
```

Expected: only intentional historical ADR/spec references remain. Runtime code,
active docs, skills, and tests contain no legacy references.

- [ ] **Step 6: Run backend tests and commit cleanup**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
git diff --check
git add -u app tests
git commit -m "refactor: remove destination nested catalog model"
```

### Task 8: Align Canonical Documentation And Operations

**Files:**
- Modify: `docs/domain-language.md`
- Modify: `docs/planning-model.md`
- Modify: `docs/data-trust-model.md`
- Modify: `docs/engineering-notes.md`
- Modify: `docs/production-runbook.md`
- Modify: `README.md`
- Modify: `PROJECT.md`
- Modify: `.env.example`
- Modify: related historical ADR headers to point to ADR 0009 where superseded

- [ ] **Step 1: Update canonical terminology**

Document `SkiRegion`, `StayDestination`, `StayBase`, independent `SkiArea`,
`SkiAreaAccess`, generalized `TerrainDomain`, `LiftPassProduct`,
`TripConfiguration`, and `RecommendationGroup`. Remove active guidance that says
destination owns ski areas or recommendation grouping is destination+area.

- [ ] **Step 2: Update planning/scoring documentation**

State that `search_v3` uses adapted `search_v2` global components, pass fit only
selects a pass, resilience is measured-not-ranked, and future ranking influence
requires another model version.

- [ ] **Step 3: Update runbook cutover procedure**

Document:

```bash
pg_dump "$DATABASE_URL" --format=custom --file "snowcast-pre-trip-market-$(date +%Y%m%d%H%M%S).dump"
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.verify_catalog_evidence --write-snapshot /tmp/snowcast-evidence-before.json
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.bootstrap_database --catalog-path app/data/catalog.json
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.verify_catalog_evidence --compare-snapshot /tmp/snowcast-evidence-before.json
```

State that rollback requires restoring the dump and previous image together.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md PROJECT.md .env.example docs
git commit -m "docs: document trip market catalog and search"
```

### Task 9: Run Final Verification And Feature Review

- [ ] **Step 1: Validate catalog and evidence policy**

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog \
  --catalog-path app/data/catalog.json \
  --trust-manifest-path app/data/resort_trust_manifest.json
UV_CACHE_DIR=.uv-cache uv run --no-config pytest -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
```

- [ ] **Step 2: Verify web and mobile**

```bash
cd frontend && npm test -- --run && npm run build && npx playwright test
cd ../mobile && flutter analyze && flutter test
```

- [ ] **Step 3: Run local product acceptance**

Start backend and frontend. Search at least:

- France in March: verify Tignes/Val d'Isere occupies one market slot and the
  card still names the winning area/base;
- Chamonix: verify local/broad passes remain alternatives and selected-area
  evidence is explicit;
- Campiglio: verify three stay destinations group under one trip market;
- Cervinia/Zermatt: verify shared terrain does not automatically force one trip
  market when their stay markets remain distinct.

Save one current trip, reload it, inspect its summary, and open an accommodation
handoff.

- [ ] **Step 4: Run focused advisory feature review**

Use Product / Strategy, Backend / API, Data Trust & Source Integrity, UI / UX,
Observability / Ops, Performance, and Release / Change Management against the
complete diff. Resolve every Blocker/High finding; record Medium/Low follow-ups
without spawning broad extra review cycles.

- [ ] **Step 5: Capture deployment evidence snapshot and final git state**

```bash
git status --short
git diff --check
git log --oneline --decorate -12
```

Do not deploy unless the database backup command and evidence-count comparison
have been rehearsed against a disposable/test database.
