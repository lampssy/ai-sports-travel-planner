# Resort Fit Data Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first resort-fit factor foundation so Snowcast can derive and audit ranking-relevant factors before changing production ranking weights.

**Architecture:** Add a pure domain module for factor derivation and trust caps, then surface factor readiness in the existing data-quality audit. This first slice does not change production ranking behavior; it creates the tested model boundary and cleanup signal needed before a later factor-aware ranking switch.

**Tech Stack:** Python 3, Pydantic domain models, dataclasses, pytest, existing `uv run --no-config` test workflow.

---

## Scope Check

The approved design covers several subsystems: factor policy, data-quality audit,
ranking behavior, acquisition expansion, future filters, and eventually
hotel-level amenities. This plan implements the first working slice only:

- pure factor derivation for terrain scale, skill fit, stay-base access, and
  trust caps
- data-quality audit visibility for factor readiness
- documentation links from the current trust and planning model docs

This plan intentionally does not:

- change `search_resorts()` scoring weights
- add user-facing API fields
- ingest new acquisition sources
- model hotel amenities
- add operational lift or piste status

Those changes should be separate plans after factor readiness data and ranking
comparison output are reviewed.

## Decision Assumptions For This Plan

These assumptions make the first slice executable while keeping the design easy
to revise:

- Factor registry representation: Python dataclasses in `app/domain/resort_fit.py`.
- Trust source: use current catalog facts and trust-state helpers only; do not
  create a new factor-trust manifest in this slice.
- Terrain-scale buckets:
  - `small`: less than 50 piste km
  - `medium`: 50 to 149 piste km
  - `large`: 150 to 299 piste km
  - `mega`: 300 or more piste km
- Stay-base access buckets:
  - `walkable`: explicit `access_mode="walk"` or nearest lift distance at most
    500m
  - `shuttle_easy`: explicit `access_mode="ski_bus"` or nearest lift distance at
    most 1500m
  - `car_recommended`: explicit `access_mode="car_recommended"` or nearest lift
    distance above 1500m
  - `unknown`: no useful access evidence
- Skill-fit derivation:
  - beginner fit when beginner piste share is at least 30% or beginner piste km
    is at least 40
  - intermediate fit when intermediate piste share is at least 25% or total
    piste km is at least 50
  - advanced fit when advanced piste share is at least 20%, advanced piste km is
    at least 35, or total terrain is at least 150km with summit elevation at or
    above 2800m
- Production ranking behavior remains unchanged in this plan.

## File Structure

- Create `app/domain/resort_fit.py`
  - Owns factor dataclasses, lifecycle/trust literals, ranking caps, and pure
    derivation functions.
  - Depends on `app.domain.models.SkiArea` and `StayBase`.
- Create `tests/test_resort_fit.py`
  - Unit tests for factor derivation and trust caps.
- Modify `app/data/audit_data_quality.py`
  - Adds a resort-fit factor summary domain to the existing audit.
  - Reuses current metric snapshot conventions and bounded labels.
- Modify `tests/test_data_quality_audit.py`
  - Tests audit visibility for factor readiness.
- Modify `docs/data-trust-model.md`
  - Documents that high-impact fit labels should be derived factors, not
    permanent direct truth.
- Modify `docs/planning-model.md`
  - Links planning/ranking semantics to the new resort-fit factor policy.

---

### Task 1: Add Pure Resort-Fit Factor Policy

**Files:**
- Create: `tests/test_resort_fit.py`
- Create: `app/domain/resort_fit.py`

- [ ] **Step 1: Write the failing factor-policy tests**

Create `tests/test_resort_fit.py` with this content:

```python
from app.domain.models import PisteKmByDifficulty, SkiArea, StayBase
from app.domain.resort_fit import (
    ranking_cap_for_trust_state,
    skill_fit_factor_for_ski_area,
    stay_base_access_factor,
    terrain_scale_factor_for_ski_area,
    trust_state_for_manifest_status,
)


def _ski_area(
    *,
    total_piste_km: float | None = None,
    beginner: float | None = None,
    intermediate: float | None = None,
    advanced: float | None = None,
    summit_elevation_m: int = 2600,
) -> SkiArea:
    difficulty = None
    if beginner is not None and intermediate is not None and advanced is not None:
        difficulty = PisteKmByDifficulty(
            beginner=beginner,
            intermediate=intermediate,
            advanced=advanced,
        )
    return SkiArea(
        ski_area_id="test-ski-area",
        name="Test Ski Area",
        latitude=45.5,
        longitude=6.7,
        base_elevation_m=1200,
        summit_elevation_m=summit_elevation_m,
        season_start_month=12,
        season_end_month=4,
        total_piste_km=total_piste_km,
        total_lift_count=20,
        piste_km_by_difficulty=difficulty,
    )


def _stay_base(
    *,
    nearest_lift_distance_m: int | None = None,
    access_mode: str = "unknown",
    lift_distance: str = "medium",
) -> StayBase:
    return StayBase(
        stay_base_id="test-village",
        name="Test Village",
        price_range="EUR 150-220",
        price_min=150,
        price_max=220,
        quality="standard",
        lift_distance=lift_distance,
        supported_skill_levels=["beginner", "intermediate"],
        nearest_lift_distance_m=nearest_lift_distance_m,
        access_mode=access_mode,
    )


def test_terrain_scale_uses_source_backed_total_piste_km() -> None:
    assert (
        terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=30)).value
        == "small"
    )
    assert (
        terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=80)).value
        == "medium"
    )
    assert (
        terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=180)).value
        == "large"
    )
    mega = terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=320))
    assert mega.value == "mega"
    assert mega.trust_state == "source_backed"
    assert mega.lifecycle_state == "active"


def test_terrain_scale_marks_missing_total_piste_km_as_needs_source() -> None:
    factor = terrain_scale_factor_for_ski_area(_ski_area())

    assert factor.value is None
    assert factor.trust_state == "needs_source"
    assert factor.lifecycle_state == "planned"
    assert factor.missing_inputs == ("total_piste_km",)


def test_skill_fit_profile_uses_piste_difficulty_mix() -> None:
    factor = skill_fit_factor_for_ski_area(
        _ski_area(
            total_piste_km=130,
            beginner=50,
            intermediate=55,
            advanced=25,
        )
    )

    assert factor.value == ("beginner", "intermediate")
    assert factor.trust_state == "source_backed"
    assert factor.lifecycle_state == "active"


def test_skill_fit_profile_can_mark_advanced_large_high_terrain() -> None:
    factor = skill_fit_factor_for_ski_area(
        _ski_area(
            total_piste_km=180,
            beginner=55,
            intermediate=90,
            advanced=35,
            summit_elevation_m=3000,
        )
    )

    assert factor.value == ("beginner", "intermediate", "advanced")


def test_skill_fit_profile_requires_difficulty_mix_for_source_backed_profile() -> None:
    factor = skill_fit_factor_for_ski_area(_ski_area(total_piste_km=90))

    assert factor.value == ("intermediate",)
    assert factor.trust_state == "derived_from_partial_data"
    assert factor.missing_inputs == ("piste_km_by_difficulty",)


def test_stay_base_access_prefers_distance_and_access_mode() -> None:
    walkable = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=450, access_mode="unknown")
    )
    shuttle = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=1200, access_mode="unknown")
    )
    car = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=2200, access_mode="unknown")
    )

    assert walkable.value == "walkable"
    assert shuttle.value == "shuttle_easy"
    assert car.value == "car_recommended"
    assert walkable.trust_state == "source_backed"


def test_stay_base_access_falls_back_to_legacy_bucket_with_partial_trust() -> None:
    factor = stay_base_access_factor(_stay_base(lift_distance="near"))

    assert factor.value == "walkable"
    assert factor.trust_state == "derived_from_partial_data"
    assert factor.missing_inputs == ("nearest_lift_distance_m", "access_mode")


def test_trust_state_and_ranking_caps_map_current_manifest_statuses() -> None:
    assert trust_state_for_manifest_status("verified") == "source_backed"
    assert (
        trust_state_for_manifest_status("verified_with_adjustment")
        == "source_backed"
    )
    assert trust_state_for_manifest_status("estimated") == "manual_estimate"
    assert trust_state_for_manifest_status("needs_source") == "needs_source"
    assert trust_state_for_manifest_status(None) == "needs_source"

    assert ranking_cap_for_trust_state("source_backed") == 1.0
    assert ranking_cap_for_trust_state("derived_from_partial_data") == 0.7
    assert ranking_cap_for_trust_state("manual_estimate") == 0.25
    assert ranking_cap_for_trust_state("needs_source") == 0.0
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_fit.py -q
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'app.domain.resort_fit'`.

- [ ] **Step 3: Add the factor-policy module**

Create `app/domain/resort_fit.py` with this content:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.domain.models import SkiArea, StayBase

FactorScope = Literal[
    "destination",
    "ski_area",
    "stay_base",
    "accommodation",
    "rental",
]
FactorTrustState = Literal[
    "source_backed",
    "derived_from_partial_data",
    "manual_estimate",
    "needs_source",
]
FactorLifecycleState = Literal["active", "measured_not_ranked", "planned", "disabled"]
FactorRankingRole = Literal["core", "preference_activated", "none"]

TrustManifestStatus = Literal[
    "verified",
    "verified_with_adjustment",
    "estimated",
    "needs_source",
]

TERRAIN_SCALE_FACTOR_ID = "terrain_scale"
SKILL_FIT_FACTOR_ID = "skill_fit_profile"
STAY_BASE_ACCESS_FACTOR_ID = "stay_base_access"

TRUST_RANKING_CAPS: dict[FactorTrustState, float] = {
    "source_backed": 1.0,
    "derived_from_partial_data": 0.7,
    "manual_estimate": 0.25,
    "needs_source": 0.0,
}


@dataclass(frozen=True)
class ResortFitFactor:
    factor_id: str
    scope: FactorScope
    entity_id: str
    value: str | int | float | tuple[str, ...] | None
    trust_state: FactorTrustState
    lifecycle_state: FactorLifecycleState
    ranking_role: FactorRankingRole
    user_filter_role: str | None = None
    display_role: str | None = None
    raw_inputs: dict[str, Any] = field(default_factory=dict)
    missing_inputs: tuple[str, ...] = ()

    @property
    def ranking_cap(self) -> float:
        return ranking_cap_for_trust_state(self.trust_state)


def ranking_cap_for_trust_state(trust_state: FactorTrustState) -> float:
    return TRUST_RANKING_CAPS[trust_state]


def trust_state_for_manifest_status(
    status: TrustManifestStatus | str | None,
) -> FactorTrustState:
    if status in {"verified", "verified_with_adjustment"}:
        return "source_backed"
    if status == "estimated":
        return "manual_estimate"
    return "needs_source"


def terrain_scale_factor_for_ski_area(ski_area: SkiArea) -> ResortFitFactor:
    total_piste_km = ski_area.total_piste_km
    if total_piste_km is None:
        return ResortFitFactor(
            factor_id=TERRAIN_SCALE_FACTOR_ID,
            scope="ski_area",
            entity_id=ski_area.ski_area_id,
            value=None,
            trust_state="needs_source",
            lifecycle_state="planned",
            ranking_role="core",
            user_filter_role="large_ski_area",
            display_role="terrain_size",
            raw_inputs={
                "total_piste_km": None,
                "total_lift_count": ski_area.total_lift_count,
            },
            missing_inputs=("total_piste_km",),
        )

    if total_piste_km < 50:
        value = "small"
    elif total_piste_km < 150:
        value = "medium"
    elif total_piste_km < 300:
        value = "large"
    else:
        value = "mega"

    return ResortFitFactor(
        factor_id=TERRAIN_SCALE_FACTOR_ID,
        scope="ski_area",
        entity_id=ski_area.ski_area_id,
        value=value,
        trust_state="source_backed",
        lifecycle_state="active",
        ranking_role="core",
        user_filter_role="large_ski_area",
        display_role="terrain_size",
        raw_inputs={
            "total_piste_km": total_piste_km,
            "total_lift_count": ski_area.total_lift_count,
        },
    )


def skill_fit_factor_for_ski_area(ski_area: SkiArea) -> ResortFitFactor:
    if ski_area.piste_km_by_difficulty is None:
        if ski_area.total_piste_km is not None and ski_area.total_piste_km >= 50:
            return ResortFitFactor(
                factor_id=SKILL_FIT_FACTOR_ID,
                scope="ski_area",
                entity_id=ski_area.ski_area_id,
                value=("intermediate",),
                trust_state="derived_from_partial_data",
                lifecycle_state="measured_not_ranked",
                ranking_role="core",
                user_filter_role="skill_level",
                display_role="skill_fit",
                raw_inputs={
                    "total_piste_km": ski_area.total_piste_km,
                    "summit_elevation_m": ski_area.summit_elevation_m,
                    "piste_km_by_difficulty": None,
                },
                missing_inputs=("piste_km_by_difficulty",),
            )
        return ResortFitFactor(
            factor_id=SKILL_FIT_FACTOR_ID,
            scope="ski_area",
            entity_id=ski_area.ski_area_id,
            value=None,
            trust_state="needs_source",
            lifecycle_state="planned",
            ranking_role="core",
            user_filter_role="skill_level",
            display_role="skill_fit",
            raw_inputs={
                "total_piste_km": ski_area.total_piste_km,
                "summit_elevation_m": ski_area.summit_elevation_m,
                "piste_km_by_difficulty": None,
            },
            missing_inputs=("piste_km_by_difficulty",),
        )

    difficulty = ski_area.piste_km_by_difficulty
    total = max(difficulty.beginner + difficulty.intermediate + difficulty.advanced, 1)
    beginner_share = difficulty.beginner / total
    intermediate_share = difficulty.intermediate / total
    advanced_share = difficulty.advanced / total

    values: list[str] = []
    if beginner_share >= 0.3 or difficulty.beginner >= 40:
        values.append("beginner")
    if intermediate_share >= 0.25 or total >= 50:
        values.append("intermediate")
    if (
        advanced_share >= 0.2
        or difficulty.advanced >= 35
        or (total >= 150 and ski_area.summit_elevation_m >= 2800)
    ):
        values.append("advanced")
    if not values:
        values.append("intermediate")

    return ResortFitFactor(
        factor_id=SKILL_FIT_FACTOR_ID,
        scope="ski_area",
        entity_id=ski_area.ski_area_id,
        value=tuple(values),
        trust_state="source_backed",
        lifecycle_state="active",
        ranking_role="core",
        user_filter_role="skill_level",
        display_role="skill_fit",
        raw_inputs={
            "total_piste_km": ski_area.total_piste_km,
            "summit_elevation_m": ski_area.summit_elevation_m,
            "piste_km_by_difficulty": {
                "beginner": difficulty.beginner,
                "intermediate": difficulty.intermediate,
                "advanced": difficulty.advanced,
            },
        },
    )


def stay_base_access_factor(stay_base: StayBase) -> ResortFitFactor:
    if stay_base.access_mode == "walk":
        return _stay_base_access_source_backed(stay_base, "walkable")
    if stay_base.access_mode == "ski_bus":
        return _stay_base_access_source_backed(stay_base, "shuttle_easy")
    if stay_base.access_mode == "car_recommended":
        return _stay_base_access_source_backed(stay_base, "car_recommended")

    distance_m = stay_base.nearest_lift_distance_m
    if distance_m is not None:
        if distance_m <= 500:
            return _stay_base_access_source_backed(stay_base, "walkable")
        if distance_m <= 1500:
            return _stay_base_access_source_backed(stay_base, "shuttle_easy")
        return _stay_base_access_source_backed(stay_base, "car_recommended")

    fallback_by_legacy_bucket = {
        "near": "walkable",
        "medium": "shuttle_easy",
        "far": "car_recommended",
    }
    return ResortFitFactor(
        factor_id=STAY_BASE_ACCESS_FACTOR_ID,
        scope="stay_base",
        entity_id=stay_base.stay_base_id,
        value=fallback_by_legacy_bucket.get(stay_base.lift_distance, "unknown"),
        trust_state="derived_from_partial_data",
        lifecycle_state="measured_not_ranked",
        ranking_role="core",
        user_filter_role="stay_base_access",
        display_role="access",
        raw_inputs={
            "nearest_lift_distance_m": None,
            "access_mode": stay_base.access_mode,
            "lift_distance": stay_base.lift_distance,
        },
        missing_inputs=("nearest_lift_distance_m", "access_mode"),
    )


def _stay_base_access_source_backed(
    stay_base: StayBase,
    value: str,
) -> ResortFitFactor:
    return ResortFitFactor(
        factor_id=STAY_BASE_ACCESS_FACTOR_ID,
        scope="stay_base",
        entity_id=stay_base.stay_base_id,
        value=value,
        trust_state="source_backed",
        lifecycle_state="active",
        ranking_role="core",
        user_filter_role="stay_base_access",
        display_role="access",
        raw_inputs={
            "nearest_lift_distance_m": stay_base.nearest_lift_distance_m,
            "access_mode": stay_base.access_mode,
            "lift_distance": stay_base.lift_distance,
        },
    )
```

- [ ] **Step 4: Run the factor-policy tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_fit.py -q
```

Expected: PASS.

- [ ] **Step 5: Run lint for the new module and tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/resort_fit.py tests/test_resort_fit.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add app/domain/resort_fit.py tests/test_resort_fit.py
git commit -m "feat: add resort fit factor policy"
```

---

### Task 2: Surface Resort-Fit Factor Readiness In Data Quality Audit

**Files:**
- Modify: `app/data/audit_data_quality.py`
- Modify: `tests/test_data_quality_audit.py`

- [ ] **Step 1: Write failing audit tests**

Modify the import list from `app.data.audit_data_quality` in
`tests/test_data_quality_audit.py` to include:

```python
    summarize_resort_fit_factors,
```

Modify the import list from `app.domain.models` in
`tests/test_data_quality_audit.py` to include:

```python
    PisteKmByDifficulty,
```

Modify `ALLOWED_AUDIT_METRIC_LABELS` in `tests/test_data_quality_audit.py` to include:

```python
    "factor_id",
    "scope",
    "trust_state",
```

Add this test after `test_catalog_summary_groups_source_backed_fields_without_id_labels`:

```python
def test_resort_fit_factor_summary_flags_core_factor_readiness() -> None:
    complete = _destination("complete", with_source_backed_fields=True)
    complete_ski_area = complete.ski_areas[0].model_copy(
        update={
            "total_piste_km": 130,
            "total_lift_count": 24,
            "piste_km_by_difficulty": PisteKmByDifficulty(
                beginner=50,
                intermediate=55,
                advanced=25,
            ),
        }
    )
    complete = complete.model_copy(update={"ski_areas": [complete_ski_area]})
    thin = _destination("thin", with_source_backed_fields=False)

    summary = summarize_resort_fit_factors((complete, thin))

    assert summary.status_counts["complete"] >= 3
    assert summary.issue_count > 0
    assert any(
        issue["resort_id"] == "thin" and issue["factor_id"] == "terrain_scale"
        for issue in summary.issues
    )
    assert any(
        issue["resort_id"] == "thin" and issue["factor_id"] == "skill_fit_profile"
        for issue in summary.issues
    )
```

Modify `test_run_data_quality_audit_writes_artifacts_from_seeded_database` so the
expected summary domains include `resort_fit_factors`:

```python
    assert set(result.summary_by_domain) == {
        "historical_archive",
        "snow_climatology",
        "catalog_required_fields",
        "catalog_source_trust",
        "resort_fit_factors",
    }
```

Add this assertion to `test_write_audit_artifacts_creates_json_and_markdown`
after the existing report assertions:

```python
    assert "Resort Fit Factor Issues" in report
```

- [ ] **Step 2: Run the targeted audit tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_data_quality_audit.py::test_resort_fit_factor_summary_flags_core_factor_readiness tests/test_data_quality_audit.py::test_run_data_quality_audit_writes_artifacts_from_seeded_database tests/test_data_quality_audit.py::test_write_audit_artifacts_creates_json_and_markdown -q
```

Expected: FAIL because `summarize_resort_fit_factors` does not exist and the
audit summary does not yet include `resort_fit_factors`.

- [ ] **Step 3: Add resort-fit imports to the audit module**

Modify the imports near the top of `app/data/audit_data_quality.py`:

```python
from app.domain.resort_fit import (
    ResortFitFactor,
    skill_fit_factor_for_ski_area,
    stay_base_access_factor,
    terrain_scale_factor_for_ski_area,
)
```

- [ ] **Step 4: Add the factor summary dataclass**

Add this dataclass after `TrustCoverageSummary` in
`app/data/audit_data_quality.py`:

```python
@dataclass(frozen=True)
class ResortFitFactorSummary:
    ratio: float
    status_counts: dict[str, int]
    factor_status_counts: dict[str, dict[str, int]]
    issue_count: int
    issues: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))

    def metric_snapshot(
        self,
        *,
        domain: str = "resort_fit_factors",
    ) -> DataQualityMetricSnapshot:
        gauges: list[MetricGauge] = []
        for factor_id, status_counts in sorted(self.factor_status_counts.items()):
            for status, count in status_counts.items():
                gauges.append(
                    MetricGauge(
                        name="snowcast_resort_fit_factor_status",
                        value=count,
                        labels={
                            "domain": domain,
                            "factor_id": factor_id,
                            "status": status,
                        },
                    )
                )

        gap_counts: Counter[tuple[str, str, str, str]] = Counter()
        for issue in self.issues:
            resort_id = issue.get("resort_id")
            factor_id = issue.get("factor_id")
            scope = issue.get("scope")
            trust_state = issue.get("trust_state")
            if not resort_id or not factor_id or not scope or not trust_state:
                continue
            gap_counts[
                (str(resort_id), str(factor_id), str(scope), str(trust_state))
            ] += 1

        for (resort_id, factor_id, scope, trust_state), count in sorted(
            gap_counts.items()
        ):
            gauges.append(
                MetricGauge(
                    name="snowcast_resort_fit_factor_gap_count",
                    value=count,
                    labels={
                        "resort_id": resort_id,
                        "factor_id": factor_id,
                        "scope": scope,
                        "trust_state": trust_state,
                    },
                )
            )

        return _summary_metric_snapshot(
            domain=domain,
            ratio=self.ratio,
            status_counts=self.status_counts,
            gauges=tuple(gauges),
        )
```

- [ ] **Step 5: Add factor summary functions**

Add these functions after `summarize_trust_manifest` in
`app/data/audit_data_quality.py`:

```python
def summarize_resort_fit_factors(
    resorts: tuple[Destination, ...],
) -> ResortFitFactorSummary:
    rows: list[dict[str, Any]] = []
    for resort in resorts:
        for ski_area in resort.ski_areas:
            _add_resort_fit_factor_row(
                rows,
                resort_id=resort.resort_id,
                factor=terrain_scale_factor_for_ski_area(ski_area),
            )
            _add_resort_fit_factor_row(
                rows,
                resort_id=resort.resort_id,
                factor=skill_fit_factor_for_ski_area(ski_area),
            )
        for stay_base in resort.stay_bases:
            _add_resort_fit_factor_row(
                rows,
                resort_id=resort.resort_id,
                factor=stay_base_access_factor(stay_base),
            )

    status_counts = Counter(str(row["status"]) for row in rows)
    factor_status_counts: dict[str, dict[str, int]] = {}
    for factor_id in sorted({str(row["factor_id"]) for row in rows}):
        group_counts = Counter(
            str(row["status"]) for row in rows if row["factor_id"] == factor_id
        )
        factor_status_counts[factor_id] = _ordered_counts(
            group_counts,
            ("complete", "partial", "weak", "missing", "invalid", "error"),
        )

    issues = [row for row in rows if row["status"] != "complete"]
    return ResortFitFactorSummary(
        ratio=_ratio(status_counts.get("complete", 0), len(rows)),
        status_counts=_ordered_counts(
            status_counts,
            ("complete", "partial", "weak", "missing", "invalid", "error"),
        ),
        factor_status_counts=factor_status_counts,
        issue_count=len(issues),
        issues=issues,
    )


def _add_resort_fit_factor_row(
    rows: list[dict[str, Any]],
    *,
    resort_id: str,
    factor: ResortFitFactor,
) -> None:
    rows.append(
        {
            "resort_id": resort_id,
            "entity_id": factor.entity_id,
            "scope": factor.scope,
            "factor_id": factor.factor_id,
            "value": factor.value,
            "trust_state": factor.trust_state,
            "lifecycle_state": factor.lifecycle_state,
            "ranking_role": factor.ranking_role,
            "ranking_cap": factor.ranking_cap,
            "missing_inputs": list(factor.missing_inputs),
            "status": _factor_data_quality_status(factor),
        }
    )


def _factor_data_quality_status(factor: ResortFitFactor) -> DataQualityStatus:
    if factor.trust_state == "source_backed":
        return "complete"
    if factor.trust_state == "derived_from_partial_data":
        return "partial"
    if factor.trust_state == "manual_estimate":
        return "weak"
    return "missing"
```

- [ ] **Step 6: Add the new audit result field**

Modify `DataQualityAuditResult` in `app/data/audit_data_quality.py` by adding
`resort_fit_factor_issues` after `warnings`:

```python
    warnings: list[str]
    resort_fit_factor_issues: list[dict[str, Any]] = field(default_factory=list)
    metric_snapshot: DataQualityMetricSnapshot = field(
        default_factory=DataQualityMetricSnapshot
    )
```

- [ ] **Step 7: Wire factor summary into `run_data_quality_audit`**

In `run_data_quality_audit`, after `trust_summary = summarize_trust_manifest(...)`,
add:

```python
    factor_summary = summarize_resort_fit_factors(resorts)
```

In the `DataQualityMetricSnapshot.combine(...)` call, add:

```python
        factor_summary.metric_snapshot(),
```

In `summary_by_domain`, add:

```python
            "resort_fit_factors": factor_summary.as_dict(),
```

In the `DataQualityAuditResult(...)` construction, add:

```python
        resort_fit_factor_issues=factor_summary.issues,
```

- [ ] **Step 8: Render factor issues in the Markdown report**

In `render_markdown_report`, after the "Source Trust Issues" section, add:

```python
    _append_issue_section(
        lines,
        "Resort Fit Factor Issues",
        result.resort_fit_factor_issues,
        (
            "resort_id",
            "scope",
            "entity_id",
            "factor_id",
            "trust_state",
            "status",
            "missing_inputs",
        ),
    )
```

- [ ] **Step 9: Update CLI summary output**

In `main()` in `app/data/audit_data_quality.py`, extend the `print(...)` call
with:

```python
        f"resort_fit={result.summary_by_domain['resort_fit_factors']['ratio']:.1%}",
```

- [ ] **Step 10: Run the targeted audit tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_data_quality_audit.py::test_resort_fit_factor_summary_flags_core_factor_readiness tests/test_data_quality_audit.py::test_run_data_quality_audit_writes_artifacts_from_seeded_database tests/test_data_quality_audit.py::test_write_audit_artifacts_creates_json_and_markdown -q
```

Expected: PASS.

- [ ] **Step 11: Run the full data quality audit test file**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_data_quality_audit.py -q
```

Expected: PASS.

- [ ] **Step 12: Run lint for touched code**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/audit_data_quality.py tests/test_data_quality_audit.py
```

Expected: PASS.

- [ ] **Step 13: Commit Task 2**

```bash
git add app/data/audit_data_quality.py tests/test_data_quality_audit.py
git commit -m "feat: audit resort fit factor readiness"
```

---

### Task 3: Document The Runtime Boundary

**Files:**
- Modify: `docs/data-trust-model.md`
- Modify: `docs/planning-model.md`

- [ ] **Step 1: Update the data trust model**

In `docs/data-trust-model.md`, add this section after "Price And Quality Semantics":

```markdown
## Resort Fit Factor Semantics

High-impact recommendation labels should be treated as derived fit factors, not
permanent direct truth in the catalog.

Current compatibility fields still exist:

- `stay_base.quality`
- `stay_base.lift_distance`
- `stay_base.supported_skill_levels`

The forward model is:

- raw catalog facts such as piste kilometers, difficulty mix, lift count,
  nearest lift distance, access mode, price ranges, and source-backed season
  windows stay in the catalog;
- domain policy derives normalized factors such as `terrain_scale`,
  `skill_fit_profile`, and `stay_base_access`;
- each factor carries a trust state that caps ranking influence;
- low-trust factors may appear in audit output but should not create strong
  positive ranking boosts.

The first implementation slice exposes factor readiness in the data-quality
audit without changing production search ranking behavior.
```

- [ ] **Step 2: Update the planning model**

In `docs/planning-model.md`, add this paragraph after "Search Fit Semantics":

```markdown
The resort fit model separates raw catalog facts from derived ranking factors.
Search still accepts compatibility filters such as `stars`, `skill_level`, and
`lift_distance`, but factor policy should gradually own the semantics behind
terrain scale, skill fit, stay-base access, and trust caps. Production ranking
weights should not be changed until factor readiness and ranking comparison
output have been reviewed.
```

- [ ] **Step 3: Verify docs render as plain Markdown**

Run:

```bash
git diff --check docs/data-trust-model.md docs/planning-model.md
```

Expected: no output and exit code 0.

- [ ] **Step 4: Commit Task 3**

```bash
git add docs/data-trust-model.md docs/planning-model.md
git commit -m "docs: document resort fit factor boundary"
```

---

### Task 4: Final Verification

**Files:**
- Verify: `app/domain/resort_fit.py`
- Verify: `app/data/audit_data_quality.py`
- Verify: `tests/test_resort_fit.py`
- Verify: `tests/test_data_quality_audit.py`
- Verify: `docs/data-trust-model.md`
- Verify: `docs/planning-model.md`

- [ ] **Step 1: Run focused tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_fit.py tests/test_data_quality_audit.py -q
```

Expected: PASS.

- [ ] **Step 2: Run focused lint**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/resort_fit.py app/data/audit_data_quality.py tests/test_resort_fit.py tests/test_data_quality_audit.py
```

Expected: PASS.

- [ ] **Step 3: Run the catalog validator**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```

Expected: PASS with no catalog validation errors.

- [ ] **Step 4: Run the audit command locally**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.audit_data_quality --archive-start-date 2024-03-01 --archive-end-date 2024-03-02 --output-dir artifacts/data-quality
```

Expected: command exits 0 and prints ratios including `resort_fit=...`.

- [ ] **Step 5: Inspect generated audit artifacts**

Run:

```bash
rg -n "resort_fit_factors|Resort Fit Factor Issues|terrain_scale|skill_fit_profile|stay_base_access" artifacts/data-quality/data-quality-summary.json artifacts/data-quality/data-quality-report.md
```

Expected: output includes the new `resort_fit_factors` domain and the three
core factor IDs.

- [ ] **Step 6: Check git diff cleanliness**

Run:

```bash
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 7: Commit verification-only artifact policy**

Do not commit `artifacts/data-quality/*` unless the user explicitly asks for
generated audit artifacts to be committed. If generated artifacts are present
from Step 4, leave them untracked or remove only the generated artifact files
created by this task.

- [ ] **Step 8: Prepare final implementation handoff**

Include this status in the final handoff:

```text
Classification: review-gated
Developer Decision Checkpoint: resolved for first slice through plan assumptions
ADR: not added; no persistent factor tables or public API contract changes
Advisory review: skipped for this first implementation slice because production ranking behavior is unchanged
Verification: list exact commands and outcomes
```

---

## Deferred Follow-Up Plans

After this plan lands and factor readiness output is reviewed, write separate
plans for:

1. Ranking comparison diagnostics: compare current ranking with factor-aware
   candidate scoring across golden scenarios and current seed catalog.
2. Factor-aware ranking switch: change production ranking weights only after
   comparison output is accepted.
3. Acquisition expansion: fill source-backed terrain, access, and official-link
   inputs for the highest-impact current catalog gaps.
4. Future filters: expose preference-activated filters such as large terrain,
   walkable stay base, quiet village, family-friendly, and nightlife only after
   the factor has reliable data and UI semantics.

## Self-Review Notes

- Spec coverage: this plan covers the first implementation slice from the
  approved design: pure factor model, trust caps, audit visibility, and docs.
- Intentional gaps: production ranking changes, acquisition expansion, hotel
  amenities, and public API changes are deferred to separate plans because they
  are independent subsystems with higher product risk.
- Type consistency: `ResortFitFactor`, `FactorTrustState`, factor IDs, and audit
  field names are consistent across tests and implementation steps.
