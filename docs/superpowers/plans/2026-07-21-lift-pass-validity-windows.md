# Lift-Pass Validity Windows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make lift-pass date validity independent from ski-area operation, keep safe future-season candidates with explicit uncertainty, and prevent partial pass networks from overstating or ranking on unavailable terrain.

**Architecture:** Add optional typed validity windows to `LiftPassProduct`, persist them through the normalized catalog, and centralize season/pass applicability in one pure deterministic module. Search V4 derives a per-trip pass-coverage projection before candidate creation, passes it into ranking, and exposes default-safe API fields. Curation report schema v3 gains the additive field through its existing canonical reconciliation path; no catalog or report schema version changes. The generic feature lands before the existing Mayrhofen/Hintertux curation PR is recovered through the maintainer.

**Tech Stack:** Python 3.12, Pydantic v2, PostgreSQL/psycopg, FastAPI Search V4, React 18, TypeScript, Vitest, pytest, Ruff, existing catalog/trust/curation schema v2/v3 tooling.

## Global Constraints

- Classification: `review-gated`; this changes catalog correctness, planning eligibility, source trust, persistence, shared API behavior, and ranking inputs.
- Developer Decision Checkpoints: resolved. Pass validity and ski-area operation remain separate; missing pass windows add no restriction; an unpublished future-season tariff remains eligible but unverified; partial coverage keeps operating-area candidates but does not recalculate or rank on the full-network aggregate.
- ADR status: `docs/architecture/adr/0019-separate-pass-validity-from-ski-area-operation.md` is accepted; no additional ADR is required unless execution changes the ownership or fallback rules.
- Advisory design review: completed with `backend-api` and
  `data-trust-source-integrity` against the accepted spec, ADR, and this plan;
  documentation corrections resolved all Blocker, High, and material Medium
  findings before implementation.
- Advisory feature review: run the same two reviewers against the final diff before handoff. Reviewers do not modify code.
- No request-path LLM call, new dependency, catalog schema-version bump, or curation report schema-version bump.
- `LiftPassProduct.validity_windows=()` means “no separate pass-date restriction modeled”; it never means year-round validity and never copies `SkiArea.season_windows`.
- Exact windows are authoritative only with source-backed owning trust. A pass
  window with `status="estimated"`, or pass/area evidence with trust
  `estimated`/`needs_source`, remains unverified and cannot confirm or exclude.
- Exact-date applicability requires complete-trip containment. A matching-season explicit window outside the trip is authoritative and must exclude the pass; an absent future-season window is uncertainty, not evidence of invalidity.
- Month-only and absent-window searches retain candidates conservatively and must not manufacture exact dates.
- Pass coverage remains static per product. Different date-dependent coverage requires separate product variants; do not add pass-to-area edge dates.
- Do not dynamically sum ski-area terrain. Under partial or unverified coverage, rank only on a source-backed selected ski area or a wholly operating terrain domain; otherwise use neutral missing-data behavior.
- Keep existing API construction backward-compatible by making new response fields default-safe. Keep `covered_ski_area_ids` as the contract coverage alias for existing clients.
- The implementation branch must not manually absorb unpublished PR #35 catalog commits. After the generic feature is merged, recover PR #35 through the normal maintainer flow so its source-backed product split, trust changes, schema-v3 report, and independent review remain authoritative.
- Do not approve or merge catalog PRs automatically.

---

### Task 1: Clear the advisory design gate

**Files:**
- Review: `docs/superpowers/specs/2026-07-21-lift-pass-validity-windows-design.md`
- Review: `docs/architecture/adr/0019-separate-pass-validity-from-ski-area-operation.md`
- Review: `docs/superpowers/plans/2026-07-21-lift-pass-validity-windows.md`
- Modify only if a finding changes the accepted contract: the three files above

**Interfaces:**
- Produces: an advisory `design-review` disposition from `backend-api` and `data-trust-source-integrity` with no unresolved Blocker, High, or material Medium finding.
- Consumes: the accepted ownership, fallback, partial-coverage, trust, and compatibility decisions.

- [x] **Step 1: Run the two focused advisory design reviews**

Invoke `snowcast-advisory-review` in `design-review` mode with these exact reviewer lanes and artifacts:

```text
reviewers: backend-api, data-trust-source-integrity
artifacts:
  docs/superpowers/specs/2026-07-21-lift-pass-validity-windows-design.md
  docs/architecture/adr/0019-separate-pass-validity-from-ski-area-operation.md
  docs/superpowers/plans/2026-07-21-lift-pass-validity-windows.md
```

- [x] **Step 2: Resolve findings without silently changing owner decisions**

Mechanical clarifications may update the spec/plan directly. Stop for a new Developer Decision Checkpoint if a reviewer proposes per-edge validity, dynamic terrain calculation, a different future-season policy, or a breaking API shape.

- [x] **Step 3: Record the completed design-review disposition**

Update the spec’s Decision and Review Gate from `pending` to the actual reviewer disposition. If this changes documentation, commit only the reviewed docs:

```bash
git add docs/superpowers/specs/2026-07-21-lift-pass-validity-windows-design.md docs/architecture/adr/0019-separate-pass-validity-from-ski-area-operation.md docs/superpowers/plans/2026-07-21-lift-pass-validity-windows.md
git commit -m "docs: resolve lift pass validity design review"
```

### Task 2: Add and persist the lift-pass validity contract

**Files:**
- Modify: `app/domain/catalog.py`
- Modify: `app/data/catalog_schema.py`
- Modify: `app/data/catalog_sync.py`
- Modify: `app/data/catalog_repository.py`
- Test: `tests/test_catalog_models.py`
- Test: `tests/test_catalog_schema_v2.py`
- Test: `tests/test_catalog_sync.py`
- Test: `tests/test_catalog_repository.py`

**Interfaces:**
- Produces: `LiftPassProduct.validity_windows: tuple[CatalogSeasonWindow, ...]`, normalized `lift_pass_products.validity_windows_json`, and lossless snapshot round trips.
- Consumes: existing `CatalogSeasonWindow`, `_model_list_json()`, `_decode_json()`, and additive schema expansion conventions.

- [ ] **Step 1: Write failing model tests for the additive field**

Add tests to `tests/test_catalog_models.py` proving the default and typed values:

```python
def test_lift_pass_validity_windows_default_to_no_separate_constraint() -> None:
    snapshot = CatalogSnapshot.model_validate(minimal_catalog_payload())

    assert snapshot.lift_pass_products[0].validity_windows == ()


def test_lift_pass_validity_windows_use_typed_complete_date_ranges() -> None:
    payload = minimal_catalog_payload()
    payload["lift_pass_products"][0]["validity_windows"] = [
        {
            "season_label": "2026-2027",
            "start_date": "2026-12-05",
            "end_date": "2027-04-11",
            "status": "planned",
        },
        {
            "season_label": "2027 autumn",
            "start_date": "2027-10-02",
            "end_date": "2027-12-03",
            "status": "estimated",
        },
    ]

    product = CatalogSnapshot.model_validate(payload).lift_pass_products[0]

    assert tuple(window.start_date for window in product.validity_windows) == (
        date(2026, 12, 5),
        date(2027, 10, 2),
    )
```

Also add an invalid reversed-window case and assert Pydantic rejects it through the inherited `SeasonWindow` validator.

- [ ] **Step 2: Run the model tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_catalog_models.py -k lift_pass_validity_windows
```

Expected: failure because `LiftPassProduct` forbids the new field.

- [ ] **Step 3: Add the minimal typed catalog field**

Add one defaulted field after `terrain_domain_ids`:

```python
class LiftPassProduct(_CatalogModel):
    # existing identity and coverage fields
    validity_windows: tuple[CatalogSeasonWindow, ...] = ()
    external_validity_summary: str | None = None
```

Do not add a new date model or catalog version; reuse the frozen typed window already used by ski areas and terrain domains.

- [ ] **Step 4: Write failing schema, sync, and repository round-trip tests**

Extend `NORMALIZED_TABLE_COLUMNS["lift_pass_products"]` in `tests/test_catalog_schema_v2.py` with `validity_windows_json`. In `tests/test_catalog_sync.py` and `tests/test_catalog_repository.py`, add cases for zero, one, and two windows and assert:

```python
assert loaded.lift_pass_products[0].validity_windows == snapshot.lift_pass_products[0].validity_windows
```

Add an upgrade-path assertion that an existing `lift_pass_products` table receives a non-null `[]` default without destructive recreation.

- [ ] **Step 5: Run persistence tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_catalog_schema_v2.py tests/test_catalog_sync.py tests/test_catalog_repository.py -k 'validity_window or normalized_catalog_schema_has_expected_tables_and_keys'
```

Expected: schema-column and round-trip failures because the JSON column is absent.

- [ ] **Step 6: Add additive normalized storage**

Add this column to both create and upgrade paths:

```sql
validity_windows_json TEXT NOT NULL DEFAULT '[]'
```

Update `_upsert_passes()` to insert/update `_model_list_json(product.validity_windows)`. Update the repository SELECT and model payload to decode it with `default=[]`:

```python
"validity_windows": _decode_json(
    row,
    "validity_windows_json",
    table_name="lift_pass_products",
    default=[],
),
```

- [ ] **Step 7: Run Task 2 verification and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_catalog_models.py tests/test_catalog_schema_v2.py tests/test_catalog_sync.py tests/test_catalog_repository.py
uv run --no-config ruff check app/domain/catalog.py app/data/catalog_schema.py app/data/catalog_sync.py app/data/catalog_repository.py tests/test_catalog_models.py tests/test_catalog_schema_v2.py tests/test_catalog_sync.py tests/test_catalog_repository.py
```

Expected: all selected tests pass and Ruff exits 0.

Commit:

```bash
git add app/domain/catalog.py app/data/catalog_schema.py app/data/catalog_sync.py app/data/catalog_repository.py tests/test_catalog_models.py tests/test_catalog_schema_v2.py tests/test_catalog_sync.py tests/test_catalog_repository.py
git commit -m "feat: persist lift pass validity windows"
```

### Task 3: Centralize deterministic operation and pass applicability

**Files:**
- Create: `app/domain/catalog_applicability.py`
- Modify: `app/domain/planning.py`
- Test: `tests/test_catalog_applicability.py`
- Test: `tests/test_planning.py`

**Interfaces:**
- Produces: `AreaOperationStatus`, `PassValidityStatus`, `PassCoverageStatus`, `PassCoverageProjection`, `season_year_for_date()`, `evaluate_ski_area_operation()`, `evaluate_pass_validity()`, `project_pass_coverage()`, and `candidate_is_applicable()`.
- Consumes: `SkiArea`, `LiftPassProduct`, their owning catalog trust statuses,
  raw month/exact-date inputs, and existing season-year/month semantics.

- [ ] **Step 1: Write the full failing applicability matrix**

Create `tests/test_catalog_applicability.py` with table-driven tests for:

```text
undated pass + known in-window area -> retained, not_constrained
undated pass + known closed area -> excluded
dated pass + complete trip inside matching-season window -> confirmed
dated pass + partial overlap -> inapplicable
dated pass + matching-season window outside trip -> inapplicable, no fallback
dated pass + no requested-season window -> retained, unverified_for_requested_season
post-main-winter window -> matched by applying the area season-year rule to the window start
estimated or non-source-backed pass window -> retained but unverified, never authoritative
non-source-backed area season -> retained but unverified, never called operating or unavailable
old pass dates -> never emitted as future dates
month outside recurring area months -> unavailable
month inside recurring area months -> retained but operation unverified
no travel window -> retained without an exact-date claim
one open + one closed covered area -> partial
one open + one unknown covered area -> unverified
all covered areas closed -> no applicable candidate
```

Use this public shape in test expectations:

```python
@dataclass(frozen=True)
class PassCoverageProjection:
    validity_status: PassValidityStatus
    coverage_status: PassCoverageStatus
    contract_covered_ski_area_ids: tuple[str, ...]
    operating_covered_ski_area_ids: tuple[str, ...]
    unavailable_covered_ski_area_ids: tuple[str, ...]
    unverified_covered_ski_area_ids: tuple[str, ...]
    warnings: tuple[str, ...] = ()
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_catalog_applicability.py
```

Expected: import failure because the pure applicability module does not exist.

- [ ] **Step 3: Implement the smallest pure evaluator**

Use these exact status vocabularies:

```python
AreaOperationStatus = Literal["operating", "unavailable", "unverified"]
PassValidityStatus = Literal[
    "not_constrained",
    "confirmed",
    "unverified_for_requested_season",
    "inapplicable",
]
PassCoverageStatus = Literal["full", "partial", "unverified"]
```

Functions accept `travel_month`, `trip_start_date`, and `trip_end_date` directly so the shared module does not depend on Search V4 models. Implement these deterministic rules:

```python
def season_year_for_date(value: date, season_start_month: int) -> int:
    return value.year if value.month >= season_start_month else value.year - 1
```

- Exact ski-area dates: the raw evaluator returns `operating` when one
  matching-season window contains the complete trip; returns `unavailable` when
  matching-season windows exist but none contains it; otherwise uses recurring
  months as the cautious fallback and returns `unverified` only when every trip
  date is within them. `project_pass_coverage()` must downgrade that raw result
  to `unverified` whenever `elevation_season` trust is not source-backed. Keeping
  trust at the projection boundary lets the legacy planning helper reuse the
  date calculation without pretending it owns the separate trust manifest.
- Month-only: return `unavailable` outside recurring months and `unverified` inside them.
- No travel window: return `unverified` so candidates remain compatible without an operating claim.
- Empty pass windows: return `not_constrained`.
- Exact pass dates: the raw evaluator derives requested season year from the
  trip with the selected ski area, and classifies every pass window by calling
  `season_year_for_date(window.start_date, ski_area.season_start_month)` rather
  than comparing the raw start year. At the projection boundary, require
  source-backed `identity_scope_availability` trust and `status="planned"`
  before a window is authoritative. Matching authoritative containment returns
  `confirmed`, an authoritative same-season miss returns `inapplicable`, and
  absent or non-authoritative same-season evidence returns
  `unverified_for_requested_season`.
- Month-only or no dates with explicit pass windows: return `unverified_for_requested_season`; never parse or project `season_label`.
- Coverage precedence: any unverified covered area makes status `unverified`; otherwise some unavailable plus some operating makes `partial`; all operating makes `full`. Pass-validity uncertainty does not rename area coverage, but it does add the public unverified warning.
- `candidate_is_applicable()` returns false only when pass validity is `inapplicable` or the focus area is in the unavailable set.

Define centralized B2 warnings so backend and frontend do not invent divergent policy copy:

```python
PARTIAL_COVERAGE_WARNING = (
    "Some areas covered by this pass are outside their operating season for "
    "your dates. The published full-network terrain is not date-adjusted."
)
UNVERIFIED_COVERAGE_WARNING = (
    "Exact pass and area coverage is not yet confirmed for this season."
)
```

For a request with no travel window, retain `coverage_status="unverified"` but leave warnings empty because no date-specific claim was requested.

`project_pass_coverage()` receives the pass
`identity_scope_availability` trust status and an area-ID-to-`elevation_season`
trust mapping. Treat only `verified` and `verified_with_adjustment` as
source-backed, matching the existing Search constraint policy. Add
`UNVERIFIED_COVERAGE_WARNING` whenever exact/month context is
present and either pass validity or any covered area's operation is unverified;
add the partial warning when known unavailable and operating subsets coexist.

- [ ] **Step 4: Replace planning’s private duplicate season logic**

Change `_is_planning_window_in_season()` to call `evaluate_ski_area_operation()` and return `status != "unavailable"`. Remove only the now-duplicate private `_season_year_for_date()`; retain `_is_month_in_season()` if other planning behavior uses it.

- [ ] **Step 5: Add planning regression tests**

Extend `tests/test_planning.py` to prove the legacy companion path still:

- accepts an exact trip inside a known area window;
- rejects an exact trip outside a matching-season known window;
- accepts the recurring-month fallback when no matching-season window exists.

- [ ] **Step 6: Run Task 3 verification and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_catalog_applicability.py tests/test_planning.py
uv run --no-config ruff check app/domain/catalog_applicability.py app/domain/planning.py tests/test_catalog_applicability.py tests/test_planning.py
```

Expected: all selected tests pass and Ruff exits 0.

Commit:

```bash
git add app/domain/catalog_applicability.py app/domain/planning.py tests/test_catalog_applicability.py tests/test_planning.py
git commit -m "feat: evaluate pass and area date applicability"
```

### Task 4: Filter Search V4 candidates and expose coverage safely

**Files:**
- Modify: `app/domain/search_v4_service.py`
- Modify: `app/domain/search_constraints.py`
- Modify: `app/domain/search_factors/static.py`
- Test: `tests/test_search_v4_service.py`
- Test: `tests/test_search_constraints.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: date-aware `V4CandidateRecord.pass_coverage` and additive `SearchV4PassSummary` validity/coverage fields.
- Consumes: `PassCoverageProjection`, `project_pass_coverage()`, `candidate_is_applicable()`, the existing catalog graph, and `SearchIntent.constraints.travel_window`.

- [ ] **Step 1: Write failing candidate-generation tests**

Build a two-area pass fixture in `tests/test_search_v4_service.py` and test exact dates for:

- both areas operating: both focused candidates remain and coverage is full;
- one area closed: its focused candidate is absent, the operating candidate remains partial;
- all areas closed: no candidate remains for the pass;
- pass matching-season window outside trip: no candidate remains;
- pass with no future matching window: candidate remains and validity is unverified;
- estimated/non-source-backed pass and area windows: candidates remain with
  explicit uncertainty instead of being confirmed or excluded;
- month-only and no-window requests: candidate generation remains deterministic and conservative.

Keep the current assertion that `covered_ski_area_ids` equals the full static contract set.

- [ ] **Step 2: Write failing response compatibility tests**

Add assertions for this additive response contract:

```python
class SearchV4PassSummary(_SearchV4Model):
    # existing required fields stay unchanged
    operating_covered_ski_area_ids: tuple[str, ...] = ()
    unavailable_covered_ski_area_ids: tuple[str, ...] = ()
    unverified_covered_ski_area_ids: tuple[str, ...] = ()
    coverage_status: PassCoverageStatus = "unverified"
    validity_status: PublicPassValidityStatus = "not_constrained"
    coverage_warning: str | None = None
    published_full_network_piste_km: float | None = None
```

`PublicPassValidityStatus` excludes internal `inapplicable` because inapplicable candidates never reach the response. Verify the existing constructor in `tests/test_api.py` still succeeds without passing any new field.

Define it explicitly as:

```python
PublicPassValidityStatus = Literal[
    "not_constrained",
    "confirmed",
    "unverified_for_requested_season",
]
```

- [ ] **Step 3: Run Search V4 tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_search_v4_service.py tests/test_api.py -k 'candidate_generation or pass_summary or validity or partial_coverage'
```

Expected: failures because records and summaries do not carry a projection.

- [ ] **Step 4: Derive and gate coverage during candidate generation**

Replace `V4CandidateRecord.pass_covered_ski_area_ids` with a required `pass_coverage: PassCoverageProjection`. In `generate_v4_candidate_records()`:

1. derive static contract coverage with the existing `_pass_covered_ski_area_ids()`;
2. project it against `graph.areas_by_id`, the request window, and the owning
   pass/area trust statuses from `trust_manifest`;
3. skip the product/access candidate when `candidate_is_applicable()` is false;
4. retain the projection on the record.

Do not mutate `CatalogGraph` or make pass coverage date-dependent in storage.

Keep Search's season constraint path aligned with the centralized result.
Extend `CandidateSeasonEvidence` with a default-safe optional
`operation_status`, populate it from the focus area's projection, and make
`_evaluate_season()` use that status when present: `unavailable` is a failure,
`unverified` is the existing warning, and `operating` passes. Preserve the
legacy raw-window fallback only for direct callers that omit the new field.
This prevents the old exact-window constraint logic from rejecting the
central evaluator's cautious unknown-season fallback.

- [ ] **Step 5: Emit default-safe API fields**

Keep `covered_ski_area_ids=record.pass_coverage.contract_covered_ski_area_ids`. Fill the derived area sets/statuses and collapse `projection.warnings` into a deterministic single public warning with `" ".join(...) or None`. Set `published_full_network_piste_km` from `product.pass_accessible_terrain.total_piste_km` when present; this is contextual catalog data, not the safe ranking metric.

- [ ] **Step 6: Pass the projection into static evaluation**

Add `pass_coverage: PassCoverageProjection | None = None` as the final defaulted field on `StaticFactorCandidate`, then set it in `_static_candidate(record)`. The default preserves existing direct factor-test constructors until their coverage-specific cases opt in.

- [ ] **Step 7: Run Task 4 verification and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_search_v4_service.py tests/test_search_constraints.py tests/test_api.py
uv run --no-config ruff check app/domain/search_v4_service.py app/domain/search_constraints.py app/domain/search_factors/static.py tests/test_search_v4_service.py tests/test_search_constraints.py tests/test_api.py
```

Expected: all selected tests pass and Ruff exits 0.

Commit:

```bash
git add app/domain/search_v4_service.py app/domain/search_constraints.py app/domain/search_factors/static.py tests/test_search_v4_service.py tests/test_search_constraints.py tests/test_api.py
git commit -m "feat: apply pass coverage to search candidates"
```

### Task 5: Prevent partial networks from inflating ranking

**Files:**
- Modify: `app/domain/search_factors/static.py`
- Test: `tests/test_search_static_factors.py`
- Test: `tests/test_search_v4_service.py`

**Interfaces:**
- Produces: coverage-aware accessible-terrain selection used consistently by `accessible_terrain_scale`, `pass_terrain_value`, numeric bounds, result summaries, and explanations.
- Consumes: `StaticFactorCandidate.pass_coverage`, the existing trust resolver, and source-backed pass/domain/area metrics.

- [ ] **Step 1: Write failing terrain-source tests**

Add direct tests for `select_accessible_terrain_source()`:

```text
full coverage -> preserve pass aggregate selection
partial coverage -> skip pass aggregate
partial coverage + wholly operating terrain domain -> use domain metric
partial coverage + no wholly operating domain -> use selected-area metric
unverified selected area + source-backed area metric -> use area metric with warning
no safe source -> value None and needs_source/neutral behavior
```

Add factor tests proving both `accessible_terrain_scale` and `pass_terrain_value` do not use the published full-network total when coverage is partial or unverified.

- [ ] **Step 2: Run focused factor tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_search_static_factors.py tests/test_search_v4_service.py -k 'accessible_terrain or pass_terrain_value or partial_coverage'
```

Expected: current selection still prefers `pass_accessible_terrain` regardless of operation.

- [ ] **Step 3: Make terrain selection projection-aware**

Add an optional argument for compatibility:

```python
def select_accessible_terrain_source(
    *,
    product: LiftPassProduct,
    ski_area: SkiArea,
    terrain_domains: tuple[TerrainDomain, ...],
    trust_resolver: CatalogEvidenceResolver,
    pass_coverage: PassCoverageProjection | None = None,
) -> AccessibleTerrainSelection:
```

Selection order:

1. With no projection or `coverage_status="full"`, preserve pass aggregate then domain then area behavior.
2. With partial/unverified coverage, never add the pass aggregate as a scoring candidate.
3. Add a terrain-domain metric only if every `domain.ski_area_ids` member belongs to `operating_covered_ski_area_ids`.
4. Permit selected-area fallback even when the product declares terrain domains, provided the selected area is not unavailable and its metric is source-backed.
5. Attach the projection warning to the selected source. If no safe metric exists, return `value=None` and preserve neutral factor utility.

The `published_full_network_piste_km` response field remains separate and must not enter this selector.

- [ ] **Step 4: Propagate safe selection to every numeric path**

Pass `candidate.pass_coverage` through `_accessible_terrain_source()`. Ensure raw bound derivation and both active factors use the same selector. In `_pass_terrain_value()`, include `terrain.warnings` in the evaluation and add `coverage_status` to `explanation_inputs`; do not duplicate terrain logic locally.

- [ ] **Step 5: Run Task 5 verification and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_search_static_factors.py tests/test_search_v4_service.py
uv run --no-config ruff check app/domain/search_factors/static.py tests/test_search_static_factors.py tests/test_search_v4_service.py
```

Expected: all selected tests pass, partial pass totals do not influence numeric bounds/scores, and Ruff exits 0.

Commit:

```bash
git add app/domain/search_factors/static.py tests/test_search_static_factors.py tests/test_search_v4_service.py
git commit -m "fix: exclude unavailable pass terrain from ranking"
```

### Task 6: Extend schema-v3 curation and trust validation

**Files:**
- Modify: `app/data/catalog_curation.py`
- Test: `tests/test_catalog_curation.py`
- Test: `tests/test_catalog_curation_reconciliation.py`
- Test: `tests/test_catalog_trust.py`
- Test: `tests/test_maintainer_validation.py`

**Interfaces:**
- Produces: canonical `lift_pass_product.validity_windows` change/review paths accepted and reconciled by existing report schema v3; direct evidence remains in `identity_scope_availability`.
- Consumes: `CANONICAL_FIELD_PATHS`, `NESTED_FIELD_PATH_ROOTS`, generic catalog/trust delta reconciliation, and existing report evidence rules.

- [ ] **Step 1: Write failing canonical-path tests**

Extend `test_canonical_paths_cover_only_normalized_catalog_entities()`:

```python
assert "validity_windows" in CANONICAL_FIELD_PATHS["lift_pass_product"]
assert "validity_windows" in NESTED_FIELD_PATH_ROOTS["lift_pass_product"]
```

Add a report validation test whose change, field coverage, and evidence all use
the reconciled root `field_path="validity_windows"`, with
`source_type="official"` and an operator URL. The evidence `source_value` must
describe the complete resulting window list, or carry a normalization note when
the official page expresses the same dates in another shape. Do not use a
nested evidence path such as `validity_windows[0].start_date`: current schema-v3
validation intentionally matches evidence to catalog deltas by exact field path,
and reconciliation emits one root `validity_windows` delta.

- [ ] **Step 2: Write failing exact reconciliation and trust tests**

In `tests/test_catalog_curation_reconciliation.py`, change one pass from `[]` to an explicit window and require one exact `lift_pass_product:<id>/validity_windows` delta. Change the corresponding trust-manifest `identity_scope_availability` source refs and require exact trust delta parity.

In `tests/test_catalog_trust.py`, assert the lift-pass group inventory remains exactly:

```python
{
    "identity_scope_availability",
    "coverage",
    "prices",
    "pass_accessible_terrain",
}
```

No new trust group or version is allowed.

- [ ] **Step 3: Run curation tests and verify RED**

Run:

```bash
uv run --no-config pytest -q tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py tests/test_catalog_trust.py tests/test_maintainer_validation.py -k 'validity_window or canonical_paths or field_group'
```

Expected: unsupported field-path or missing-delta failures.

- [ ] **Step 4: Register the additive canonical path**

Add `"validity_windows"` to both lift-pass collections. Rely on generic nested-path validation and snapshot reconciliation; do not special-case report schema v3 or create a schema-v4 branch.

Document in test fixtures that a changed explicit window needs direct operator/tariff evidence and that empty windows mean no separate window modeled, not verified year-round validity.

Extend `render_catalog_resulting_graph_markdown()` so a pass with explicit windows includes deterministic compact lines in its node label, for example `valid 2026-12-05 to 2027-04-11`. Keep undated pass labels unchanged. Add a rendering assertion so a material pass-window change is visible in the schema-v3 graph as well as in the change ledger.

- [ ] **Step 5: Run Task 6 verification and commit**

Run:

```bash
uv run --no-config pytest -q tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py tests/test_catalog_trust.py tests/test_maintainer_validation.py
uv run --no-config ruff check app/data/catalog_curation.py tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py tests/test_catalog_trust.py tests/test_maintainer_validation.py
```

Expected: schema-v3 reports reconcile pass windows without a version bump; all selected tests pass.

Commit:

```bash
git add app/data/catalog_curation.py tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py tests/test_catalog_trust.py tests/test_maintainer_validation.py
git commit -m "feat: reconcile pass validity in curation reports"
```

### Task 7: Show partial and unverified coverage in the UI

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/search/searchPresentation.ts`
- Modify: `frontend/src/search/RecommendationCard.tsx`
- Modify: `frontend/src/search/TripConfigurationDetails.tsx`
- Test: `frontend/src/search/searchPresentation.test.ts`
- Test: `frontend/src/search/RecommendationCard.test.tsx`
- Test: `frontend/src/search/RecommendationDossier.test.tsx`
- Test: `frontend/src/App.test.tsx`

**Interfaces:**
- Produces: typed additive API fields, contextual published full-network terrain, and one visible coverage warning in recommendation and dossier/detail paths.
- Consumes: backend-owned `coverage_warning`, `coverage_status`, `validity_status`, safe `accessible_piste_km`, and contextual `published_full_network_piste_km`.

- [ ] **Step 1: Add failing TypeScript presentation tests**

Update the central pass fixture with:

```typescript
operating_covered_ski_area_ids: ["mayrhofen-ski-area"],
unavailable_covered_ski_area_ids: ["hintertux-glacier"],
unverified_covered_ski_area_ids: [],
coverage_status: "partial",
validity_status: "confirmed",
coverage_warning:
  "Some areas covered by this pass are outside their operating season for your dates. The published full-network terrain is not date-adjusted.",
published_full_network_piste_km: 548,
```

Test that:

- `terrainPresentation()` describes `accessible_piste_km` only at its safe selected area/domain scope;
- a new `passCoveragePresentation()` returns the backend warning and labels `548 km` as published full-network, not date-adjusted context;
- future-season validity says exact dates are unconfirmed;
- future-season validity receives the backend unverified warning even when all
  covered ski areas have confirmed operation;
- full coverage with no warning adds no warning block.

- [ ] **Step 2: Run focused frontend tests and verify RED**

Run:

```bash
cd frontend
npm test -- src/search/searchPresentation.test.ts src/search/RecommendationCard.test.tsx src/search/RecommendationDossier.test.tsx
```

Expected: type and assertion failures because the new presentation does not exist.

- [ ] **Step 3: Extend the frontend type additively**

Add these fields to `SearchV4PassSummary`:

```typescript
operating_covered_ski_area_ids: string[];
unavailable_covered_ski_area_ids: string[];
unverified_covered_ski_area_ids: string[];
coverage_status: "full" | "partial" | "unverified";
validity_status:
  | "not_constrained"
  | "confirmed"
  | "unverified_for_requested_season";
coverage_warning: string | null;
published_full_network_piste_km: number | null;
```

Update shared fixtures instead of weakening the interface with optional client fields; the backend always serializes the default-safe values.

- [ ] **Step 4: Add one presentation helper and render it consistently**

Implement:

```typescript
export interface PassCoveragePresentation {
  warning: string;
  publishedTerrainContext: string | null;
}

export function passCoveragePresentation(
  selectedPass: SearchV4PassSummary,
): PassCoveragePresentation | null {
  if (!selectedPass.coverage_warning) return null;
  return {
    warning: selectedPass.coverage_warning,
    publishedTerrainContext:
      selectedPass.published_full_network_piste_km == null
        ? null
        : `${selectedPass.published_full_network_piste_km} km is the published full-network figure and is not date-adjusted.`,
  };
}
```

Render it next to the selected-pass terrain in `RecommendationCard` and in `TripConfigurationDetails`, which is used by the dossier route. Use the existing warning visual pattern; do not reconstruct area dates or counts in the client.

- [ ] **Step 5: Run Task 7 verification and commit**

Run:

```bash
cd frontend
npm test -- src/search/searchPresentation.test.ts src/search/RecommendationCard.test.tsx src/search/RecommendationDossier.test.tsx src/App.test.tsx
npm run build
```

Expected: tests pass and TypeScript/Vite build exits 0.

Commit from repository root:

```bash
git add frontend/src/types.ts frontend/src/search/searchPresentation.ts frontend/src/search/RecommendationCard.tsx frontend/src/search/TripConfigurationDetails.tsx frontend/src/search/searchPresentation.test.ts frontend/src/search/RecommendationCard.test.tsx frontend/src/search/RecommendationDossier.test.tsx frontend/src/App.test.tsx
git commit -m "feat: explain date-specific pass coverage"
```

### Task 8: Align durable docs and complete feature verification

**Files:**
- Modify: `docs/planning-model.md`
- Modify: `docs/search-ranking-model.md`
- Modify: `docs/data-trust-model.md`
- Modify: `docs/superpowers/specs/2026-07-21-lift-pass-validity-windows-design.md`
- Review: `docs/domain-language.md`
- Review: `docs/architecture/adr/0019-separate-pass-validity-from-ski-area-operation.md`

**Interfaces:**
- Produces: aligned human-readable runtime, ranking, trust, and implementation status; final backend/frontend verification; required advisory feature review.
- Consumes: the exact implemented statuses, response fields, source selection, and test evidence.

- [ ] **Step 1: Update the owning documentation**

Document:

- in `planning-model.md`: complete-trip intersection of area operation and pass validity, future-season uncertainty, month/no-window behavior, and focused-area exclusion;
- in `search-ranking-model.md`: partial/unverified coverage disables full-network aggregate scoring and uses only source-backed safe scope;
- in `data-trust-model.md`: pass dates use `identity_scope_availability`, empty windows are not year-round evidence, and published full-network terrain may be contextual but not date-adjusted;
- in the feature spec: implementation status and this plan path.

Do not duplicate the ADR rationale or add a changelog transcript.

- [ ] **Step 2: Run the complete focused backend suite**

Run:

```bash
uv run --no-config pytest -q \
  tests/test_catalog_models.py \
  tests/test_catalog_schema_v2.py \
  tests/test_catalog_sync.py \
  tests/test_catalog_repository.py \
  tests/test_catalog_applicability.py \
  tests/test_planning.py \
  tests/test_search_constraints.py \
  tests/test_search_static_factors.py \
  tests/test_search_v4_service.py \
  tests/test_api.py \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py \
  tests/test_catalog_trust.py \
  tests/test_maintainer_validation.py
```

Expected: all selected tests pass.

- [ ] **Step 3: Validate the canonical catalog and trust manifest**

Run:

```bash
uv run --no-config python -m app.data.validate_catalog \
  --catalog-path app/data/catalog.json \
  --trust-manifest-path app/data/resort_trust_manifest.json
```

Expected: one `[catalog-valid] schema_version=2 ...` line and exit 0.

- [ ] **Step 4: Run the full backend regression suite**

Run:

```bash
uv run --no-config pytest -q
```

Expected: the complete backend suite passes. Investigate failures rather than excluding unrelated test files unless the failure is independently reproduced on unchanged main and recorded in the handoff.

- [ ] **Step 5: Run lint and frontend verification**

Run:

```bash
uv run --no-config ruff check app tests
cd frontend
npm test
npm run build
```

Expected: Ruff, Vitest, TypeScript, and Vite all exit 0.

- [ ] **Step 6: Smoke-test the date-aware API and UI locally**

Start the backend and frontend in separate terminals:

```bash
uv run --no-config uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm run dev
```

Exercise an exact Austrian trip window:

```bash
curl --request POST http://127.0.0.1:8000/api/search \
  --header 'Content-Type: application/json' \
  --data '{
    "intent": {
      "constraints": {
        "location": {"country": "Austria"},
        "travel_window": {
          "start_date": "2027-04-15",
          "end_date": "2027-04-20"
        }
      },
      "objectives": [
        {"factor_id": "pass_terrain_value", "importance": "normal"}
      ]
    }
  }' | jq '.results[].top_configuration.selected_pass | {
    name,
    validity_status,
    coverage_status,
    operating_covered_ski_area_ids,
    unavailable_covered_ski_area_ids,
    unverified_covered_ski_area_ids,
    accessible_piste_km,
    published_full_network_piste_km,
    coverage_warning
  }'
```

Open `http://localhost:5173`, run the same dates, and inspect the selected-pass block and dossier. Confirm a contextual full-network figure is visibly non-date-adjusted, while the ranked terrain figure uses a safe area/domain scope. If canonical data does not yet contain explicit Zillertal windows, use the Task 4/5 automated fixtures for the partial case and repeat this manual path after Task 9 recovers PR #35.

- [ ] **Step 7: Run the required advisory feature review**

Invoke `snowcast-advisory-review` in `feature-review` mode with `backend-api` and `data-trust-source-integrity` against the exact final diff and verification evidence. Fix every concrete Blocker/High and material Medium finding, then rerun affected tests and the exact-head feature review.

- [ ] **Step 8: Commit documentation and any final reviewed corrections**

```bash
git add docs/planning-model.md docs/search-ranking-model.md docs/data-trust-model.md docs/superpowers/specs/2026-07-21-lift-pass-validity-windows-design.md docs/domain-language.md docs/architecture/adr/0019-separate-pass-validity-from-ski-area-operation.md
git commit -m "docs: explain lift pass date applicability"
```

### Task 9: Recover the source-backed Mayrhofen/Hintertux curation after merge

**Files:**
- Expected in PR #35 only: `app/data/catalog.json`
- Expected in PR #35 only: `app/data/resort_trust_manifest.json`
- Expected in PR #35 only: its existing schema-v3 file under `docs/catalog-curation/`
- No manual changes on the generic implementation branch

**Interfaces:**
- Produces: source-backed product variants whose static coverage is true throughout each modeled validity window, with an independently reviewed schema-v3 report.
- Consumes: the merged generic feature, official Mayrhofen/Hintertux tariff evidence, and the normal local maintainer review/fix/publication flow.

- [ ] **Step 1: Merge the generic feature before touching PR #35**

Verify main contains the catalog field, persistence, applicability, ranking, curation, API, and UI changes. Do not cherry-pick PR #35’s unpublished reviewed head into main.

- [ ] **Step 2: Make PR #35 eligible for a fresh bounded maintainer recovery**

Remove only its current `maintainer:blocked` label. Rerun the standard curation maintainer cycle. The helper must prepare the live remote head on current main; Codex may reuse source-backed report material but must perform a fresh independent exact-head review after remediation.

- [ ] **Step 3: Require the curation outcome to model the date regimes explicitly**

The recovered proposal must:

- use explicit `validity_windows` for the reviewed Zillertaler Superskipass season;
- use separate local Hintertux product variant(s) when regional coverage is not true outside the main-winter window;
- keep static coverage accurate for every variant’s complete window;
- update `identity_scope_availability` source refs and preserve separate coverage evidence;
- reconcile every catalog/trust delta in report schema v3;
- flag any unresolved product-identity or owner choice in the canonical PR comment rather than inventing dates.

- [ ] **Step 4: Verify the published PR state**

Confirm the exact pushed head is labeled `maintainer:ready`, `maintainer:owner-decision`, or another honest terminal review state; its canonical comment and body show the resulting graph and pass-window caveats; and helper inspection reports no unresolved push journal. Do not approve or merge automatically.

## Final Self-Review Checklist

- [ ] Every acceptance criterion in the accepted spec maps to a test step above.
- [ ] `validity_windows` is additive in catalog schema v2 and curation report schema v3.
- [ ] The requested season is derived from dates and `season_start_month`, never free-text labels.
- [ ] The same season-year function classifies both trip and pass-window starts,
      including post-main-winter windows in cross-calendar seasons.
- [ ] Only source-backed planned windows confirm or exclude; estimated and
      source-needed evidence stays unverified.
- [ ] Known invalidity excludes; missing future evidence retains with uncertainty.
- [ ] Closed focus areas are excluded while operating alternatives survive.
- [ ] Unverified areas are never called open.
- [ ] Published full-network terrain is context only under partial/unverified coverage.
- [ ] No component-terrain summation, ranking-weight change, or request-path LLM was introduced.
- [ ] API additions are default-safe and frontend copy comes from the backend warning.
- [ ] PR #35 recovery remains helper-controlled and independently reviewed.
- [ ] No placeholder text, unresolved type mismatch, or unspecified verification command remains.
