# Ranking Comparison Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a debug-only factor-aware ranking comparison path so Snowcast can compare current trip-option ranking against candidate scoring before changing production `/api/search` ordering.

**Architecture:** Keep production search unchanged. Add pure domain code that computes candidate score breakdowns from existing `SearchResult` trip options plus derived resort-fit factors, then add a CLI/report layer that compares current rank and candidate rank for representative scenarios. Curated catalog sourcing is limited to 8-10 representative destinations so comparison output is meaningful without pretending the whole catalog is launch-clean.

**Tech Stack:** Python 3.11, Pydantic domain models, deterministic domain functions, pytest, existing catalog JSON/trust manifest, optional JSON/Markdown artifacts under `artifacts/ranking-comparison`.

---

## Review Gate

Classification: `review-gated`.

Developer Decision Checkpoint status: proceeding with these implementation assumptions unless the owner redirects after seeing the comparison report:

- Candidate scoring is diagnostics-only and must not change `/api/search` ordering, saved-trip grouping, frontend types, or public API responses.
- Comparison output is file/CLI based, not a new public endpoint.
- Representative destinations: `tignes`, `zermatt`, `ischgl`, `st-anton-am-arlberg`, `la-plagne`, `chamonix-mont-blanc`, `hintertux`, `zell-am-see-kaprun`, `val-gardena`, and `livigno`.
- Initial candidate scoring uses conservative weights and reports components rather than treating them as final product weights.
- Official/provider/reviewed sources must be cited for curated catalog values; weak values stay estimated or partial.

ADR status: not required for this slice because there is no persistence schema, public API, or production ranking change.

Advisory review status: run design/feature review before any production ranking switch. For this diagnostic slice, run focused review after implementation across product-strategy, data-trust-source-integrity, backend-api, and UI/UX.

---

## File Structure

- Create `app/domain/ranking_comparison.py`
  - Pure candidate scoring and current-vs-candidate comparison dataclasses.
  - Depends on `SearchResult`, `TripOption`, and existing resort-fit factor helpers.
- Create `app/data/compare_ranking.py`
  - CLI that runs representative scenarios against the seed catalog and writes JSON/Markdown diagnostics.
- Create `tests/test_ranking_comparison.py`
  - Unit tests for candidate score breakdowns, trust caps, rank-delta output, and no production mutation.
- Create or modify `tests/test_compare_ranking.py`
  - CLI/report tests using tiny fixtures and temporary output directory.
- Modify `app/data/resorts.json`
  - Add source-backed terrain/access inputs only for the representative destinations that can be verified in this slice.
- Modify `app/data/resort_trust_manifest.json`
  - Update trust statuses and source refs only for fields actually sourced.
- Modify `docs/planning-model.md`
  - Document that comparison diagnostics are the required step before ranking integration.
- Modify `docs/data-trust-model.md`
  - Document that curated representative sourcing is a comparison aid, not broad catalog completeness.

---

### Task 1: Pure Candidate Score Breakdown

**Files:**
- Create: `app/domain/ranking_comparison.py`
- Test: `tests/test_ranking_comparison.py`

- [ ] **Step 1: Write failing tests for candidate breakdown**

Add tests that expect:

```python
from app.domain.ranking_comparison import (
    CandidateScoreBreakdown,
    candidate_score_for_result,
)

def test_candidate_score_keeps_trip_option_components_separate() -> None:
    result = _search_result(
        score=2.5,
        quality=2,
        lift_distance="near",
        snow_confidence_score=0.8,
        conditions_score=0.75,
        budget_penalty=0.0,
    )
    breakdown = candidate_score_for_result(
        result,
        terrain_scale="large",
        terrain_trust_cap=1.0,
        skill_fit=("intermediate", "advanced"),
        skill_trust_cap=1.0,
        stay_base_access="walkable",
        access_trust_cap=1.0,
    )

    assert isinstance(breakdown, CandidateScoreBreakdown)
    assert breakdown.components["terrain"] > 0
    assert breakdown.components["skill_fit"] > 0
    assert breakdown.components["stay_base_access"] > 0
    assert breakdown.components["snow_evidence"] > 0
    assert breakdown.total == sum(breakdown.components.values())
```

```python
def test_candidate_score_applies_trust_caps_without_positive_boost_for_needs_source() -> None:
    result = _search_result(score=2.5)

    trusted = candidate_score_for_result(
        result,
        terrain_scale="mega",
        terrain_trust_cap=1.0,
        skill_fit=("intermediate",),
        skill_trust_cap=1.0,
        stay_base_access="walkable",
        access_trust_cap=1.0,
    )
    untrusted = candidate_score_for_result(
        result,
        terrain_scale="mega",
        terrain_trust_cap=0.0,
        skill_fit=("intermediate",),
        skill_trust_cap=0.0,
        stay_base_access="walkable",
        access_trust_cap=0.0,
    )

    assert trusted.total > untrusted.total
    assert untrusted.components["terrain"] == 0
    assert untrusted.components["skill_fit"] == 0
    assert untrusted.components["stay_base_access"] == 0
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_ranking_comparison.py -q
```

Expected: fail because `app.domain.ranking_comparison` does not exist.

- [ ] **Step 3: Implement minimal candidate score code**

Create `CandidateScoreBreakdown`, `candidate_score_for_result`, and helper maps:

```python
TERRAIN_COMPONENT = {"small": 0.05, "medium": 0.12, "large": 0.2, "mega": 0.28}
ACCESS_COMPONENT = {"walkable": 0.18, "shuttle_easy": 0.12, "car_recommended": 0.04}
SKILL_COMPONENT = {"beginner": 0.18, "intermediate": 0.16, "advanced": 0.16}
```

The function should include named components:

- `legacy_base`
- `terrain`
- `skill_fit`
- `stay_base_access`
- `snow_evidence`
- `conditions`
- `budget`
- `travel_effort`

Do not write back to `SearchResult.score`.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_ranking_comparison.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add app/domain/ranking_comparison.py tests/test_ranking_comparison.py
git commit -m "feat: add ranking comparison candidate scorer"
```

---

### Task 2: Current-vs-Candidate Ranking Report

**Files:**
- Modify: `app/domain/ranking_comparison.py`
- Create: `app/data/compare_ranking.py`
- Test: `tests/test_ranking_comparison.py`
- Test: `tests/test_compare_ranking.py`

- [ ] **Step 1: Write failing tests for rank deltas**

Add tests that build three synthetic results and assert:

```python
from app.domain.ranking_comparison import compare_rankings

def test_compare_rankings_reports_current_and_candidate_rank_delta() -> None:
    weak_current_top = _search_result(resort_id="legacy-top", score=3.0)
    strong_candidate = _search_result(resort_id="candidate-top", score=2.8)

    report = compare_rankings(
        [weak_current_top, strong_candidate],
        factor_inputs={
            "legacy-top": _factor_inputs(terrain_scale="small", access="car_recommended"),
            "candidate-top": _factor_inputs(terrain_scale="mega", access="walkable"),
        },
    )

    candidate_row = next(row for row in report.rows if row.resort_id == "candidate-top")
    assert candidate_row.current_rank == 2
    assert candidate_row.candidate_rank == 1
    assert candidate_row.rank_delta == -1
    assert "terrain" in candidate_row.top_candidate_components
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_ranking_comparison.py -q
```

Expected: fail because `compare_rankings` is not implemented.

- [ ] **Step 3: Implement comparison dataclasses**

Add:

- `RankingComparisonRow`
- `RankingComparisonReport`
- `FactorComparisonInput`
- `compare_rankings(results, factor_inputs)`

`compare_rankings` should sort current results by current `score` and candidate results by `candidate_score.total`, then report current rank, candidate rank, `rank_delta`, candidate score, current score, and top three positive candidate components.

- [ ] **Step 4: Add CLI tests**

Add a CLI test that calls a report writer with two rows and asserts both JSON and Markdown contain:

- `current_rank`
- `candidate_rank`
- `rank_delta`
- `candidate_score`
- `top_candidate_components`

- [ ] **Step 5: Implement CLI/report writer**

`app/data/compare_ranking.py` should provide:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison
```

The CLI writes:

- `ranking-comparison-summary.json`
- `ranking-comparison-report.md`

It should be read-only against production ranking and catalog files.

- [ ] **Step 6: Run tests and verify GREEN**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_ranking_comparison.py tests/test_compare_ranking.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/ranking_comparison.py app/data/compare_ranking.py tests/test_ranking_comparison.py tests/test_compare_ranking.py
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add app/domain/ranking_comparison.py app/data/compare_ranking.py tests/test_ranking_comparison.py tests/test_compare_ranking.py
git commit -m "feat: add ranking comparison report"
```

---

### Task 3: Curated Representative Resort Inputs

**Files:**
- Modify: `app/data/resorts.json`
- Modify: `app/data/resort_trust_manifest.json`
- Test: `tests/test_catalog_validation.py` or existing catalog/audit tests as needed

- [ ] **Step 1: Source representative inputs**

For each representative resort, use official resort pages first, then provider/reviewed resort facts when official pages are incomplete. Capture source refs for:

- `total_piste_km`
- `piste_km_by_difficulty`
- `total_lift_count` where available
- stay-base nearest lift/access facts where available

Do not promote weak stay-base quality/value claims to source-backed unless the source supports the claim.

- [ ] **Step 2: Update catalog conservatively**

For each sourced ski area, add or update:

```json
"total_piste_km": 300,
"total_lift_count": 78,
"piste_km_by_difficulty": {
  "beginner": 170,
  "intermediate": 78,
  "advanced": 52
}
```

For each sourced stay base, add or update:

```json
"nearest_lift_name": "Example lift",
"nearest_lift_distance_m": 450,
"access_mode": "walk"
```

Only use values actually supported by sources.

- [ ] **Step 3: Update trust manifest**

For each changed field group, set trust to `verified` or `verified_with_adjustment` only when source-backed. Leave `estimated` where still judgment-based.

Add source refs for every upgraded field group.

- [ ] **Step 4: Verify catalog and audit**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.audit_data_quality --archive-start-date 2024-03-01 --archive-end-date 2024-03-02 --output-dir artifacts/data-quality
```

Expected: catalog valid and `resort_fit` readiness improves for the representative set.

- [ ] **Step 5: Commit**

```bash
git add app/data/resorts.json app/data/resort_trust_manifest.json
git commit -m "data: source representative resort fit inputs"
```

---

### Task 4: Run Comparison Diagnostics

**Files:**
- Modify: `docs/planning-model.md`
- Modify: `docs/data-trust-model.md`
- Generated, ignored: `artifacts/ranking-comparison/`

- [ ] **Step 1: Run comparison CLI**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison
```

Expected: writes JSON and Markdown report with current rank, candidate rank, rank deltas, and top score components.

- [ ] **Step 2: Inspect report**

Run:

```bash
rg -n "candidate_rank|rank_delta|terrain|skill_fit|stay_base_access|trust" artifacts/ranking-comparison
```

Expected: report shows factor-aware deltas and missing/partial factor caveats.

- [ ] **Step 3: Update docs**

Update docs to point operators/product review to the comparison command and restate that the output is diagnostic until owner-reviewed.

- [ ] **Step 4: Run final verification**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_ranking_comparison.py tests/test_compare_ranking.py tests/test_resort_fit.py tests/test_data_quality_audit.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/ranking_comparison.py app/data/compare_ranking.py app/domain/resort_fit.py app/data/audit_data_quality.py tests/test_ranking_comparison.py tests/test_compare_ranking.py tests/test_resort_fit.py tests/test_data_quality_audit.py
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
git diff --check
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add docs/planning-model.md docs/data-trust-model.md
git commit -m "docs: document ranking comparison diagnostics"
```

---

## Final Handoff

Include:

- Classification: review-gated.
- Developer Decision Checkpoint: proceeded with documented diagnostic-only assumptions.
- ADR: not added unless implementation crosses into persistence/API/production ranking changes.
- Advisory review: run focused review before production ranking switch; diagnostic branch can ship after implementation review if no Blocker/High issues.
- Verification commands and outcomes.
- Link to generated ranking comparison artifacts and summarize top rank deltas.

## Self-Review Notes

- Spec coverage: covers deferred follow-up item 1 from the resort-fit plan: ranking comparison diagnostics across candidate scoring and current catalog.
- Intentional gaps: production ranking switch, public API response changes, frontend display of score breakdowns, and broad all-resort acquisition remain deferred.
- Type consistency: `SearchResult`, `TripOption`, and `ResortFitFactor` remain the existing domain contracts; comparison types are diagnostic-only.
