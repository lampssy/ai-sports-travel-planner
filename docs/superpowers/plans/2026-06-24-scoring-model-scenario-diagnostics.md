# Scoring Model Scenario Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add diagnostic-only golden scoring scenarios that expose expected ranking behavior, future factor gaps, and AI-interpreted intent shape before any production `/api/search` scoring change.

**Architecture:** Keep production search unchanged. Add a small scenario-definition domain module, extend ranking comparison artifacts with factor availability and missing-factor diagnostics, and add a synthetic scenario runner that can test scoring behavior independently of incomplete real catalog data. Scenario diagnostics become the review surface for deciding scoring weights, grouping semantics, and which new factors must be modeled before production integration.

**Tech Stack:** Python 3.11, dataclasses, Pydantic domain models already in `app/domain/models.py`, existing `app/domain/ranking_comparison.py`, pytest, Ruff, Markdown/JSON artifacts under `artifacts/scoring-scenarios`.

---

## Review Gate

Classification: `review-gated`.

Developer Decision Checkpoint status: resolved by owner discussion:

- Golden scenarios are aspirational and must include factors beyond current implementation.
- AI-assisted search may interpret a large pool of filters and preferences, but deterministic backend code owns scoring.
- This slice remains diagnostic-only and must not change production `/api/search` ordering, response shape, saved-trip grouping, or frontend behavior.
- Missing future factors should be visible in diagnostics instead of silently ignored.

ADR status: not required for this diagnostic slice because there is no persistence, public API, or production ranking change. Add an ADR when the production scoring architecture or public search contract changes.

Advisory review status: run design/feature review before production ranking integration. This diagnostic slice can be reviewed after implementation by product-strategy, data-trust-source-integrity, backend-api, and UI/UX.

---

## File Structure

- Create `app/domain/scoring_scenarios.py`
  - Owns scenario metadata, factor availability states, and target scenario expectations.
  - Contains no search execution, database access, LLM calls, or catalog mutation.
- Modify `app/domain/ranking_comparison.py`
  - Extend diagnostic-only factor inputs and rows with factor availability states and missing-factor notes.
  - Keep `SearchResult.score` immutable.
- Modify `app/data/compare_ranking.py`
  - Render factor availability and missing-factor notes in existing JSON/Markdown artifacts.
  - Keep the existing real-catalog comparison command working.
- Create `app/data/compare_scoring_scenarios.py`
  - Builds synthetic scenario fixtures and writes scenario diagnostics to `artifacts/scoring-scenarios`.
  - Uses existing `compare_rankings` and `FactorComparisonInput`.
- Create `tests/test_scoring_scenarios.py`
  - Validates scenario definitions, ids, factor states, and expected coverage.
- Modify `tests/test_ranking_comparison.py`
  - Tests factor availability propagation into comparison rows.
- Modify `tests/test_compare_ranking.py`
  - Tests JSON/Markdown rendering of factor availability and missing-factor notes.
- Create `tests/test_compare_scoring_scenarios.py`
  - Tests synthetic scenario runner, executable winners, blocked-by-missing-data diagnostics, and artifact writing.
- Modify `docs/planning-model.md`
  - Document the scenario diagnostics command and review interpretation.
- Modify `docs/data-trust-model.md`
  - Document that future factors can appear in diagnostics only when explicitly marked as missing, proxy-only, or future candidate.

---

### Task 1: Factor Availability Diagnostics In Ranking Comparison

**Files:**
- Modify: `app/domain/ranking_comparison.py`
- Modify: `app/data/compare_ranking.py`
- Test: `tests/test_ranking_comparison.py`
- Test: `tests/test_compare_ranking.py`

- [ ] **Step 1: Add failing tests for factor availability propagation**

Add this test to `tests/test_ranking_comparison.py`:

```python
def test_compare_rankings_preserves_factor_availability_notes() -> None:
    result = _search_result(resort_id="beginner-fit", score=2.5)

    report = compare_rankings(
        [result],
        factor_inputs={
            "beginner-fit": FactorComparisonInput(
                terrain_scale="small",
                terrain_trust_cap=1.0,
                skill_fit=("beginner",),
                skill_trust_cap=1.0,
                stay_base_access="walkable",
                access_trust_cap=1.0,
                factor_availability={
                    "beginner_terrain": "proxy_only",
                    "ski_school_quality": "known_missing",
                    "hotel_spa": "future_candidate",
                },
                missing_factor_notes={
                    "ski_school_quality": "No source-backed ski school signal exists.",
                    "hotel_spa": "Hotel inventory is not modeled in this slice.",
                },
            )
        },
        scenario_id="beginner_first_trip",
    )

    row = report.rows[0]

    assert row.factor_availability["beginner_terrain"] == "proxy_only"
    assert row.factor_availability["ski_school_quality"] == "known_missing"
    assert row.factor_availability["hotel_spa"] == "future_candidate"
    assert (
        row.missing_factor_notes["ski_school_quality"]
        == "No source-backed ski school signal exists."
    )
    assert (
        row.missing_factor_notes["hotel_spa"]
        == "Hotel inventory is not modeled in this slice."
    )
```

- [ ] **Step 2: Add failing artifact rendering test**

Extend `test_write_ranking_comparison_artifacts_creates_json_and_markdown` in
`tests/test_compare_ranking.py` so its `RankingComparisonRow` includes:

```python
factor_availability={
    "beginner_terrain": "proxy_only",
    "ski_school_quality": "known_missing",
}
missing_factor_notes={
    "ski_school_quality": "No source-backed ski school signal exists."
}
```

Add these assertions:

```python
assert summary["rows"][0]["factor_availability"] == {
    "beginner_terrain": "proxy_only",
    "ski_school_quality": "known_missing",
}
assert summary["rows"][0]["missing_factor_notes"] == {
    "ski_school_quality": "No source-backed ski school signal exists."
}
assert "`ski_school_quality=known_missing`" in markdown
assert "No source-backed ski school signal exists." in markdown
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_ranking_comparison.py tests/test_compare_ranking.py -q
```

Expected: fail because `FactorComparisonInput`, `RankingComparisonRow`, and artifact rendering do not expose `factor_availability` or `missing_factor_notes`.

- [ ] **Step 4: Extend comparison dataclasses**

In `app/domain/ranking_comparison.py`, add a literal type near the component maps:

```python
FactorAvailabilityState = Literal[
    "active_now",
    "near_term",
    "proxy_only",
    "known_missing",
    "future_candidate",
]
```

Update imports:

```python
from typing import Literal, Mapping
```

Add defaulted fields to `FactorComparisonInput`:

```python
factor_availability: dict[str, FactorAvailabilityState] = field(
    default_factory=dict
)
missing_factor_notes: dict[str, str] = field(default_factory=dict)
```

Add required row fields to `RankingComparisonRow`:

```python
factor_availability: dict[str, FactorAvailabilityState]
missing_factor_notes: dict[str, str]
```

When constructing `RankingComparisonRow` in `compare_rankings`, pass:

```python
factor_availability=dict(factor_input.factor_availability),
missing_factor_notes=dict(factor_input.missing_factor_notes),
```

- [ ] **Step 5: Render factor availability and notes**

In `app/data/compare_ranking.py`, update `_render_markdown_report` so the table
columns become:

```python
"| Scenario | Resort | Result Group | Current Rank | Candidate Rank | "
"Rank Delta | Candidate Score | Factor Sources | Factor Availability | "
"Missing Factor Notes | Top Components |",
"| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
```

Inside the row loop, add:

```python
factor_availability = ", ".join(
    f"`{name}={value}`" for name, value in sorted(row.factor_availability.items())
)
if not factor_availability:
    factor_availability = "-"
missing_notes = "; ".join(
    f"{name}: {note}" for name, note in sorted(row.missing_factor_notes.items())
)
if not missing_notes:
    missing_notes = "-"
```

Update the Markdown row append to include:

```python
f"{factor_sources} | "
f"{factor_availability} | "
f"{missing_notes} | "
f"{components} |"
```

The JSON artifact already uses `asdict(row)`, so it should include the new row
fields automatically.

- [ ] **Step 6: Run tests and verify GREEN**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_ranking_comparison.py tests/test_compare_ranking.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add app/domain/ranking_comparison.py app/data/compare_ranking.py tests/test_ranking_comparison.py tests/test_compare_ranking.py
git commit -m "feat: add factor availability ranking diagnostics"
```

---

### Task 2: Scenario Definition Registry

**Files:**
- Create: `app/domain/scoring_scenarios.py`
- Test: `tests/test_scoring_scenarios.py`

- [ ] **Step 1: Add failing scenario registry tests**

Create `tests/test_scoring_scenarios.py`:

```python
from app.domain.scoring_scenarios import (
    SCORING_SCENARIOS,
    SCORING_SCENARIOS_BY_ID,
)


def test_scoring_scenarios_cover_initial_golden_set() -> None:
    assert [scenario.scenario_id for scenario in SCORING_SCENARIOS] == [
        "snow_sure_late_season_intermediate",
        "beginner_first_trip_low_hassle",
        "family_children_mixed_confidence",
        "advanced_big_terrain",
        "short_break_no_car",
        "value_optimizer",
        "crowd_averse_quiet_slopes",
        "non_skier_partner",
        "luxury_wellness_hotel_trip",
        "late_booking_conditions_chaser",
        "mixed_skill_group",
        "shared_domain_multi_ski_area_grouping",
    ]


def test_scoring_scenarios_include_future_and_missing_factors() -> None:
    beginner = SCORING_SCENARIOS_BY_ID["beginner_first_trip_low_hassle"]
    assert beginner.factor_availability["ski_school_quality"] == "known_missing"
    assert beginner.factor_availability["beginner_package_availability"] == (
        "future_candidate"
    )

    value = SCORING_SCENARIOS_BY_ID["value_optimizer"]
    assert value.factor_availability["lift_pass_price_per_km"] == "near_term"

    crowd = SCORING_SCENARIOS_BY_ID["crowd_averse_quiet_slopes"]
    assert crowd.expected_today_status == "blocked_by_missing_data"
    assert crowd.factor_availability["lift_queue_time"] == "known_missing"


def test_scoring_scenarios_do_not_duplicate_ids() -> None:
    ids = [scenario.scenario_id for scenario in SCORING_SCENARIOS]
    assert len(ids) == len(set(ids))
    assert set(SCORING_SCENARIOS_BY_ID) == set(ids)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_scoring_scenarios.py -q
```

Expected: fail because `app.domain.scoring_scenarios` does not exist.

- [ ] **Step 3: Implement scenario registry dataclasses**

Create `app/domain/scoring_scenarios.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.ranking_comparison import FactorAvailabilityState

ScenarioTodayStatus = Literal["executable", "proxy_only", "blocked_by_missing_data"]
PreferenceWeight = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ScoringScenario:
    scenario_id: str
    user_intent: str
    expected_today_status: ScenarioTodayStatus
    expected_today_winner_key: str | None
    hard_constraints: dict[str, str]
    weighted_preferences: dict[str, PreferenceWeight]
    expected_group_behavior: str
    factor_availability: dict[str, FactorAvailabilityState]
    missing_factor_notes: dict[str, str]
    target_behavior: str


def _scenario(
    *,
    scenario_id: str,
    user_intent: str,
    expected_today_status: ScenarioTodayStatus,
    expected_today_winner_key: str | None,
    hard_constraints: dict[str, str],
    weighted_preferences: dict[str, PreferenceWeight],
    expected_group_behavior: str,
    factor_availability: dict[str, FactorAvailabilityState],
    missing_factor_notes: dict[str, str],
    target_behavior: str,
) -> ScoringScenario:
    if expected_today_status == "executable" and expected_today_winner_key is None:
        raise ValueError(f"{scenario_id}: executable scenarios require a winner")
    return ScoringScenario(
        scenario_id=scenario_id,
        user_intent=user_intent,
        expected_today_status=expected_today_status,
        expected_today_winner_key=expected_today_winner_key,
        hard_constraints=hard_constraints,
        weighted_preferences=weighted_preferences,
        expected_group_behavior=expected_group_behavior,
        factor_availability=factor_availability,
        missing_factor_notes=missing_factor_notes,
        target_behavior=target_behavior,
    )
```

- [ ] **Step 4: Add the 12 scenario definitions**

In the same file, define `SCORING_SCENARIOS` exactly as:

```python
SCORING_SCENARIOS: tuple[ScoringScenario, ...] = (
    _scenario(
        scenario_id="snow_sure_late_season_intermediate",
        user_intent="March or April trip with strong snow odds, intermediate skiing, and reasonable value.",
        expected_today_status="executable",
        expected_today_winner_key="snow-sure-glacier--glacier-area--walkable-base",
        hard_constraints={"skill_level": "intermediate", "season": "late"},
        weighted_preferences={
            "snow_reliability": "high",
            "budget_fit": "medium",
            "terrain_size": "medium",
        },
        expected_group_behavior="Rank one snow-sure option above cheaper weak-snow options.",
        factor_availability={
            "snow_reliability": "active_now",
            "season_fit": "active_now",
            "terrain_scale": "active_now",
            "open_piste_share": "future_candidate",
        },
        missing_factor_notes={
            "open_piste_share": "Operational piste status is not ingested yet."
        },
        target_behavior="Open piste and recent snowfall should refine the late-season winner once live feeds exist.",
    ),
    _scenario(
        scenario_id="beginner_first_trip_low_hassle",
        user_intent="First ski trip, nervous beginner, easy logistics, not too expensive.",
        expected_today_status="executable",
        expected_today_winner_key="easy-beginner--learning-area--walkable-base",
        hard_constraints={"skill_level": "beginner"},
        weighted_preferences={
            "beginner_friendliness": "high",
            "low_hassle": "high",
            "terrain_size": "low",
            "budget_fit": "high",
        },
        expected_group_behavior="Small easy option can beat huge expert terrain.",
        factor_availability={
            "skill_fit": "active_now",
            "stay_base_access": "active_now",
            "beginner_terrain": "proxy_only",
            "ski_school_quality": "known_missing",
            "beginner_package_availability": "future_candidate",
        },
        missing_factor_notes={
            "ski_school_quality": "No source-backed ski school quality signal exists.",
            "beginner_package_availability": "Lesson, rental, and lift-ticket package data is not modeled.",
        },
        target_behavior="Ski school, rental distance, and beginner packages should become first-class boosts.",
    ),
    _scenario(
        scenario_id="family_children_mixed_confidence",
        user_intent="Family ski week with children, some beginners, parents intermediate.",
        expected_today_status="proxy_only",
        expected_today_winner_key="family-easy-access--main-area--walkable-base",
        hard_constraints={"group": "family", "skill_mix": "beginner_to_intermediate"},
        weighted_preferences={
            "family_fit": "high",
            "low_hassle": "high",
            "snow_reliability": "medium",
        },
        expected_group_behavior="Easy logistics beats stronger mountain with family friction.",
        factor_availability={
            "skill_fit": "active_now",
            "stay_base_access": "active_now",
            "childcare": "known_missing",
            "family_rooms": "future_candidate",
        },
        missing_factor_notes={
            "childcare": "Childcare and ski school pickup/dropoff are not modeled."
        },
        target_behavior="Childcare, family rooms, and lesson meeting-point access should influence score when requested.",
    ),
    _scenario(
        scenario_id="advanced_big_terrain",
        user_intent="Advanced skier wants serious terrain and enough variety for a week.",
        expected_today_status="executable",
        expected_today_winner_key="advanced-domain--linked-domain--central-base",
        hard_constraints={"skill_level": "advanced"},
        weighted_preferences={
            "accessible_terrain": "high",
            "advanced_terrain": "high",
            "snow_reliability": "medium",
        },
        expected_group_behavior="Linked-domain terrain can beat local child-area terrain.",
        factor_availability={
            "terrain_scale": "active_now",
            "skill_fit": "active_now",
            "terrain_domain": "near_term",
            "lift_queue_time": "known_missing",
        },
        missing_factor_notes={
            "lift_queue_time": "Lift queue and lift capacity signals are not modeled."
        },
        target_behavior="Open lift network and advanced-terrain quality should refine big-terrain ranking.",
    ),
    _scenario(
        scenario_id="short_break_no_car",
        user_intent="Two ski days, no car, minimal wasted time.",
        expected_today_status="executable",
        expected_today_winner_key="compact-car-free--main-area--station-base",
        hard_constraints={"no_car": "true", "trip_length": "short"},
        weighted_preferences={
            "transfer_simplicity": "high",
            "stay_base_access": "high",
            "terrain_size": "low",
        },
        expected_group_behavior="Compact car-free option beats famous spread-out option.",
        factor_availability={
            "stay_base_access": "active_now",
            "travel_effort": "active_now",
            "bus_frequency": "known_missing",
            "transfer_reliability": "future_candidate",
        },
        missing_factor_notes={
            "bus_frequency": "Ski bus frequency and station transfer quality are not modeled."
        },
        target_behavior="Train, airport, and shuttle reliability should become scoring inputs for short trips.",
    ),
    _scenario(
        scenario_id="value_optimizer",
        user_intent="Best skiing value for money, not just cheapest lodging.",
        expected_today_status="proxy_only",
        expected_today_winner_key="balanced-value--main-area--standard-base",
        hard_constraints={"budget_goal": "value"},
        weighted_preferences={
            "budget_fit": "high",
            "snow_reliability": "high",
            "accessible_terrain": "medium",
        },
        expected_group_behavior="Balanced value beats cheap poor-snow option.",
        factor_availability={
            "lodging_budget_fit": "active_now",
            "terrain_scale": "active_now",
            "lift_pass_price": "near_term",
            "lift_pass_price_per_km": "near_term",
            "total_trip_cost": "known_missing",
        },
        missing_factor_notes={
            "total_trip_cost": "Food, transfer, lesson, and package inclusion costs are not modeled."
        },
        target_behavior="Use pass price, included products, and total cost to score utility per trip.",
    ),
    _scenario(
        scenario_id="crowd_averse_quiet_slopes",
        user_intent="Reliable snow, but avoid crowds and lift queues.",
        expected_today_status="blocked_by_missing_data",
        expected_today_winner_key=None,
        hard_constraints={"avoid": "crowds"},
        weighted_preferences={
            "snow_reliability": "high",
            "quiet_slopes": "high",
            "apres": "low",
        },
        expected_group_behavior="Do not claim a crowd-aware winner without crowd data.",
        factor_availability={
            "snow_reliability": "active_now",
            "crowding": "known_missing",
            "lift_queue_time": "known_missing",
            "review_derived_crowd_signal": "future_candidate",
        },
        missing_factor_notes={
            "crowding": "Crowd and lift-queue data are not modeled."
        },
        target_behavior="Crowding should become a preference-activated penalty once reliable signals exist.",
    ),
    _scenario(
        scenario_id="non_skier_partner",
        user_intent="One skier and one non-skier partner need a nice town and things to do.",
        expected_today_status="blocked_by_missing_data",
        expected_today_winner_key=None,
        hard_constraints={"non_skier_partner": "true"},
        weighted_preferences={
            "non_ski_activities": "high",
            "restaurants": "medium",
            "transit_access": "medium",
        },
        expected_group_behavior="Do not let pure ski terrain dominate when non-skier fit is requested.",
        factor_availability={
            "stay_base_quality": "proxy_only",
            "non_ski_activities": "known_missing",
            "restaurants": "known_missing",
            "wellness": "future_candidate",
        },
        missing_factor_notes={
            "non_ski_activities": "Non-ski activity inventory is not modeled."
        },
        target_behavior="Town character, food, wellness, and day-trip access should become preference factors.",
    ),
    _scenario(
        scenario_id="luxury_wellness_hotel_trip",
        user_intent="Premium ski trip with spa, sauna, food, easy access, and solid snow.",
        expected_today_status="blocked_by_missing_data",
        expected_today_winner_key=None,
        hard_constraints={"quality": "premium"},
        weighted_preferences={
            "hotel_spa": "high",
            "snow_reliability": "high",
            "ski_in_ski_out": "medium",
        },
        expected_group_behavior="Do not rank hotels until accommodation inventory exists.",
        factor_availability={
            "snow_reliability": "active_now",
            "stay_base_quality": "proxy_only",
            "hotel_spa": "future_candidate",
            "half_board": "future_candidate",
        },
        missing_factor_notes={
            "hotel_spa": "Hotel amenity inventory is not modeled."
        },
        target_behavior="Hotel-level amenities should influence ranking only after provider-backed inventory exists.",
    ),
    _scenario(
        scenario_id="late_booking_conditions_chaser",
        user_intent="Last-minute trip next week with the best current conditions.",
        expected_today_status="proxy_only",
        expected_today_winner_key="fresh-conditions--main-area--walkable-base",
        hard_constraints={"booking_window": "last_minute"},
        weighted_preferences={
            "current_conditions": "high",
            "recent_snowfall": "high",
            "historical_average": "low",
        },
        expected_group_behavior="Current conditions should dominate static resort quality.",
        factor_availability={
            "current_conditions": "active_now",
            "open_lifts": "known_missing",
            "open_pistes": "known_missing",
            "recent_snowfall": "future_candidate",
        },
        missing_factor_notes={
            "open_lifts": "Official open-lift status is not ingested."
        },
        target_behavior="Provider-backed live status should dominate last-minute scoring.",
    ),
    _scenario(
        scenario_id="mixed_skill_group",
        user_intent="Group with beginners, intermediates, and advanced skiers.",
        expected_today_status="proxy_only",
        expected_today_winner_key="mixed-skill-balanced--main-area--central-base",
        hard_constraints={"skill_mix": "beginner_intermediate_advanced"},
        weighted_preferences={
            "beginner_fit": "high",
            "intermediate_fit": "high",
            "advanced_fit": "medium",
        },
        expected_group_behavior="Balanced terrain beats advanced-only terrain.",
        factor_availability={
            "skill_fit": "active_now",
            "terrain_scale": "active_now",
            "difficulty_mix": "near_term",
            "terrain_connectivity": "known_missing",
        },
        missing_factor_notes={
            "terrain_connectivity": "Beginner-safe connectivity across the domain is not modeled."
        },
        target_behavior="Group itinerary compatibility should become a first-class factor.",
    ),
    _scenario(
        scenario_id="shared_domain_multi_ski_area_grouping",
        user_intent="Show the best linked-area option without filling the list with the same ski domain.",
        expected_today_status="executable",
        expected_today_winner_key="tignes-domain--tignes-ski-area--val-claret",
        hard_constraints={"dedupe_linked_domains": "true"},
        weighted_preferences={
            "accessible_terrain": "high",
            "result_diversity": "high",
        },
        expected_group_behavior="Shared domains should expose one result group with nested alternatives.",
        factor_availability={
            "result_group_key": "active_now",
            "terrain_domain": "near_term",
            "nested_alternatives": "known_missing",
        },
        missing_factor_notes={
            "nested_alternatives": "Production grouped-result response is not implemented."
        },
        target_behavior="Production search should group linked-domain alternatives after owner review.",
    ),
)

SCORING_SCENARIOS_BY_ID: dict[str, ScoringScenario] = {
    scenario.scenario_id: scenario for scenario in SCORING_SCENARIOS
}
```

- [ ] **Step 5: Run tests and verify GREEN**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_scoring_scenarios.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add app/domain/scoring_scenarios.py tests/test_scoring_scenarios.py
git commit -m "feat: add scoring scenario registry"
```

---

### Task 3: Synthetic Scenario Runner

**Files:**
- Create: `app/data/compare_scoring_scenarios.py`
- Test: `tests/test_compare_scoring_scenarios.py`

- [ ] **Step 1: Add failing tests for scenario runner artifacts**

Create `tests/test_compare_scoring_scenarios.py`:

```python
import json

from app.data.compare_scoring_scenarios import run_scoring_scenario_diagnostics


def test_scoring_scenario_diagnostics_writes_expected_artifacts(tmp_path) -> None:
    report = run_scoring_scenario_diagnostics(output_dir=tmp_path)

    assert len(report.rows) >= 12
    assert (tmp_path / "scoring-scenario-summary.json").exists()
    assert (tmp_path / "scoring-scenario-report.md").exists()

    payload = json.loads(
        (tmp_path / "scoring-scenario-summary.json").read_text(encoding="utf-8")
    )
    assert "snow_sure_late_season_intermediate" in payload["scenario_statuses"]
    assert payload["scenario_statuses"]["crowd_averse_quiet_slopes"] == (
        "blocked_by_missing_data"
    )
    assert any(
        row["scenario_id"] == "beginner_first_trip_low_hassle"
        and row["candidate_rank"] == 1
        and row["resort_id"] == "easy-beginner"
        for row in payload["rows"]
    )


def test_scoring_scenario_diagnostics_reports_missing_future_factors(tmp_path) -> None:
    run_scoring_scenario_diagnostics(output_dir=tmp_path)

    markdown = (tmp_path / "scoring-scenario-report.md").read_text(encoding="utf-8")

    assert "`ski_school_quality=known_missing`" in markdown
    assert "No source-backed ski school quality signal exists." in markdown
    assert "`hotel_spa=future_candidate`" in markdown
    assert "`lift_queue_time=known_missing`" in markdown
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_compare_scoring_scenarios.py -q
```

Expected: fail because `app.data.compare_scoring_scenarios` does not exist.

- [ ] **Step 3: Implement scenario result builders**

Create `app/data/compare_scoring_scenarios.py` with the imports and helper
types:

```python
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.domain.models import (
    ConfidenceContributor,
    ExplanationItem,
    ProvenanceInfo,
    SearchExplanation,
    SearchResult,
)
from app.domain.ranking_comparison import (
    FactorComparisonInput,
    RankingComparisonReport,
    compare_rankings,
    group_counts_for_rows,
    option_key_for_result,
)
from app.domain.scoring_scenarios import SCORING_SCENARIOS, ScoringScenario

DEFAULT_OUTPUT_DIR = Path("artifacts/scoring-scenarios")


def _explanation() -> SearchExplanation:
    return SearchExplanation(
        highlights=[ExplanationItem(label="Synthetic scenario fixture.")],
        risks=[],
        confidence_contributors=[
            ConfidenceContributor(label="Diagnostic fixture.", direction="positive")
        ],
    )


def _provenance() -> ProvenanceInfo:
    return ProvenanceInfo(
        source_name="scoring-scenario-fixture",
        source_type="estimated",
        updated_at="2026-06-24T00:00:00+00:00",
        freshness_status="unknown",
        basis_summary="Synthetic scoring scenario fixture.",
    )


def _result(
    *,
    resort_id: str,
    ski_area_id: str,
    stay_base_name: str,
    score: float,
    rating_estimate: int,
    snow_confidence_score: float,
    conditions_score: float,
    budget_penalty: float = 0.0,
) -> SearchResult:
    return SearchResult(
        resort_id=resort_id,
        resort_name=resort_id.replace("-", " ").title(),
        region="Synthetic Alps",
        selected_ski_area_id=ski_area_id,
        selected_ski_area_name=ski_area_id.replace("-", " ").title(),
        selected_stay_base_name=stay_base_name,
        selected_stay_base_lift_distance="near",
        stay_base_price_range="EUR 180-240",
        selected_area_name=stay_base_name,
        selected_area_lift_distance="near",
        area_price_range="EUR 180-240",
        rental_name="Scenario Rental",
        rental_price_range="EUR 35-55",
        rating_estimate=rating_estimate,
        link="https://example.com/scoring-scenario",
        score=score,
        budget_penalty=budget_penalty,
        conditions_summary="Synthetic diagnostic conditions.",
        snow_confidence_score=snow_confidence_score,
        snow_confidence_label="good",
        availability_status="open",
        conditions_score=conditions_score,
        conditions_provenance=_provenance(),
        explanation=_explanation(),
        recommendation_confidence=0.8,
    )
```

- [ ] **Step 4: Implement fixture factors and options**

Add these helpers to `app/data/compare_scoring_scenarios.py`:

```python
def _factor(
    *,
    terrain_scale: str | None,
    skill_fit: tuple[str, ...],
    stay_base_access: str | None,
    factor_availability: dict[str, str],
    missing_factor_notes: dict[str, str],
    result_group_key: str | None = None,
) -> FactorComparisonInput:
    return FactorComparisonInput(
        terrain_scale=terrain_scale,
        terrain_trust_cap=1.0 if terrain_scale else 0.0,
        skill_fit=skill_fit,
        skill_trust_cap=1.0 if skill_fit else 0.0,
        stay_base_access=stay_base_access,
        access_trust_cap=1.0 if stay_base_access else 0.0,
        factor_availability=factor_availability,
        missing_factor_notes=missing_factor_notes,
        result_group_key=result_group_key,
    )


def _scenario_options(
    scenario: ScoringScenario,
) -> tuple[list[SearchResult], dict[str, FactorComparisonInput]]:
    winner_key = scenario.expected_today_winner_key
    if scenario.expected_today_status == "blocked_by_missing_data":
        results = [
            _result(
                resort_id=scenario.scenario_id.replace("_", "-"),
                ski_area_id="unresolved-area",
                stay_base_name="Unresolved Base",
                score=2.0,
                rating_estimate=2,
                snow_confidence_score=0.65,
                conditions_score=0.65,
            )
        ]
        option_key = option_key_for_result(results[0])
        return results, {
            option_key: _factor(
                terrain_scale=None,
                skill_fit=(),
                stay_base_access=None,
                factor_availability=scenario.factor_availability,
                missing_factor_notes=scenario.missing_factor_notes,
            )
        }

    assert winner_key is not None
    loser_resort_id = f"{scenario.scenario_id.replace('_', '-')}-weaker"
    winner_parts = winner_key.split("--")
    winner_resort_id = winner_parts[0]
    winner_ski_area_id = winner_parts[1]
    winner_stay_base_name = winner_parts[2].replace("-", " ").title()
    results = [
        _result(
            resort_id=loser_resort_id,
            ski_area_id="weaker-area",
            stay_base_name="Weaker Base",
            score=3.0,
            rating_estimate=1,
            snow_confidence_score=0.35,
            conditions_score=0.35,
            budget_penalty=0.08,
        ),
        _result(
            resort_id=winner_resort_id,
            ski_area_id=winner_ski_area_id,
            stay_base_name=winner_stay_base_name,
            score=2.5,
            rating_estimate=3,
            snow_confidence_score=0.9,
            conditions_score=0.85,
            budget_penalty=0.0,
        ),
    ]
    factor_inputs = {
        option_key_for_result(results[0]): _factor(
            terrain_scale="small",
            skill_fit=("intermediate",),
            stay_base_access="car_recommended",
            factor_availability=scenario.factor_availability,
            missing_factor_notes=scenario.missing_factor_notes,
        ),
        option_key_for_result(results[1]): _factor(
            terrain_scale="mega"
            if "terrain" in scenario.scenario_id
            or "advanced" in scenario.scenario_id
            or "shared_domain" in scenario.scenario_id
            else "medium",
            skill_fit=("beginner", "intermediate", "advanced")
            if "mixed_skill" in scenario.scenario_id
            else ("beginner",)
            if "beginner" in scenario.scenario_id
            else ("intermediate", "advanced"),
            stay_base_access="walkable",
            factor_availability=scenario.factor_availability,
            missing_factor_notes=scenario.missing_factor_notes,
            result_group_key="terrain-domain:tignes-val-disere"
            if "shared_domain" in scenario.scenario_id
            else None,
        ),
    }
    return results, factor_inputs
```

- [ ] **Step 5: Implement runner and artifact writer**

Add:

```python
def run_scoring_scenario_diagnostics(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> RankingComparisonReport:
    rows = []
    scenario_statuses: dict[str, str] = {}
    for scenario in SCORING_SCENARIOS:
        results, factor_inputs = _scenario_options(scenario)
        report = compare_rankings(
            results,
            factor_inputs=factor_inputs,
            scenario_id=scenario.scenario_id,
        )
        rows.extend(report.rows)
        scenario_statuses[scenario.scenario_id] = scenario.expected_today_status

    combined_report = RankingComparisonReport(
        rows=rows,
        group_counts=group_counts_for_rows(rows),
    )
    _write_artifacts(
        combined_report,
        scenario_statuses=scenario_statuses,
        output_dir=output_dir,
    )
    return combined_report


def _write_artifacts(
    report: RankingComparisonReport,
    *,
    scenario_statuses: dict[str, str],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "scenario_statuses": scenario_statuses,
        "group_counts": report.group_counts,
        "rows": [asdict(row) for row in report.rows],
    }
    (output_dir / "scoring-scenario-summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "scoring-scenario-report.md").write_text(
        _render_markdown(payload),
        encoding="utf-8",
    )


def _render_markdown(payload: dict[str, object]) -> str:
    rows = payload["rows"]
    scenario_statuses = payload["scenario_statuses"]
    assert isinstance(rows, list)
    assert isinstance(scenario_statuses, dict)
    lines = ["# Scoring Scenario Diagnostics", "", "## Scenario Statuses", ""]
    for scenario_id, status in sorted(scenario_statuses.items()):
        lines.append(f"- `{scenario_id}`: `{status}`")
    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| Scenario | Resort | Candidate Rank | Factor Availability | Missing Factor Notes |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for row in rows:
        assert isinstance(row, dict)
        availability = ", ".join(
            f"`{name}={value}`"
            for name, value in sorted(row["factor_availability"].items())
        )
        notes = "; ".join(
            f"{name}: {note}" for name, note in sorted(row["missing_factor_notes"].items())
        )
        lines.append(
            "| "
            f"{row['scenario_id']} | "
            f"{row['resort_id']} | "
            f"{row['candidate_rank']} | "
            f"{availability or '-'} | "
            f"{notes or '-'} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write diagnostic-only golden scoring scenario artifacts."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for JSON and Markdown scoring scenario artifacts.",
    )
    args = parser.parse_args()
    report = run_scoring_scenario_diagnostics(output_dir=args.output_dir)
    print(
        "Scoring scenario diagnostics:",
        f"rows={len(report.rows)}",
        f"groups={len(report.group_counts)}",
        f"output_dir={args.output_dir}",
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests and verify GREEN**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_compare_scoring_scenarios.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add app/data/compare_scoring_scenarios.py tests/test_compare_scoring_scenarios.py
git commit -m "feat: add scoring scenario diagnostics runner"
```

---

### Task 4: Scenario Diagnostics Documentation

**Files:**
- Modify: `docs/planning-model.md`
- Modify: `docs/data-trust-model.md`
- Test: none for docs

- [ ] **Step 1: Update planning model docs**

Add this subsection after the existing "Ranking Comparison Diagnostics" section
in `docs/planning-model.md`:

````markdown
### Scoring Scenario Diagnostics

Golden scoring scenarios are diagnostic-only acceptance cases for the future
production scoring model. They intentionally include implemented, near-term,
proxy-only, known-missing, and future-candidate factors.

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_scoring_scenarios --output-dir artifacts/scoring-scenarios
```

The report writes:

- `scoring-scenario-summary.json`
- `scoring-scenario-report.md`

Use this report to decide whether candidate scoring behavior is defensible,
which scenarios are blocked by missing data, and which future factors should be
modeled before production search ranking changes.
````

- [ ] **Step 2: Update data trust docs**

Add this paragraph under "Resort Fit Factor Semantics" in
`docs/data-trust-model.md`:

```markdown
Scoring scenario diagnostics can mention factors before they are production
ready, but every such factor must declare a factor availability state:
`active_now`, `near_term`, `proxy_only`, `known_missing`, or
`future_candidate`. Only `active_now` factors can affect current diagnostic
scores. `proxy_only`, `known_missing`, and `future_candidate` factors must be
visible as caveats rather than hidden ranking boosts.
```

- [ ] **Step 3: Run docs sanity checks**

Run:

```bash
rg -n "Scoring Scenario Diagnostics|factor availability state|known_missing|future_candidate" docs/planning-model.md docs/data-trust-model.md
git diff --check
```

Expected: both docs include the new guidance and `git diff --check` prints no output.

- [ ] **Step 4: Commit**

```bash
git add docs/planning-model.md docs/data-trust-model.md
git commit -m "docs: document scoring scenario diagnostics"
```

---

### Task 5: Final Verification And Scenario Smoke Run

**Files:**
- Generated, ignored: `artifacts/scoring-scenarios/`

- [ ] **Step 1: Run focused test suite**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_ranking_comparison.py tests/test_compare_ranking.py tests/test_scoring_scenarios.py tests/test_compare_scoring_scenarios.py -q
```

Expected: pass.

- [ ] **Step 2: Run focused lint**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/ranking_comparison.py app/data/compare_ranking.py app/domain/scoring_scenarios.py app/data/compare_scoring_scenarios.py tests/test_ranking_comparison.py tests/test_compare_ranking.py tests/test_scoring_scenarios.py tests/test_compare_scoring_scenarios.py
```

Expected: pass.

- [ ] **Step 3: Run scenario diagnostics**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_scoring_scenarios --output-dir artifacts/scoring-scenarios
```

Expected: prints a row count, group count, and output directory.

- [ ] **Step 4: Inspect scenario artifacts**

Run:

```bash
rg -n "blocked_by_missing_data|proxy_only|known_missing|future_candidate|beginner_first_trip_low_hassle|value_optimizer|shared_domain_multi_ski_area_grouping" artifacts/scoring-scenarios
```

Expected: artifacts show executable, proxy-only, and blocked scenarios plus missing future factors.

- [ ] **Step 5: Validate existing catalog and comparison still work**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison
git diff --check
```

Expected: catalog valid, existing ranking comparison still writes artifacts, and `git diff --check` prints no output.

- [ ] **Step 6: Commit final verification docs if needed**

If Task 5 changes only ignored artifacts, skip this commit. If documentation or test fixtures changed during verification, commit them with:

```bash
git add docs/planning-model.md docs/data-trust-model.md tests/test_scoring_scenarios.py tests/test_compare_scoring_scenarios.py
git commit -m "test: verify scoring scenario diagnostics"
```

---

## Final Handoff

Include:

- Classification: review-gated.
- Developer Decision Checkpoint: owner approved aspirational scenarios and AI-assisted intent interpretation as deterministic scoring inputs.
- ADR: not added because production scoring architecture remains unchanged.
- Advisory review: required before production ranking integration.
- Verification commands and outcomes.
- Scenario artifact location.
- Summary of:
  - executable scenarios;
  - proxy-only scenarios;
  - blocked-by-missing-data scenarios;
  - most important future factors surfaced by diagnostics.

## Self-Review Notes

- Spec coverage: covers scenario registry, future factor visibility, factor availability states, AI-assisted intent interpretation boundaries, diagnostics artifacts, and verification before production ranking changes.
- Intentional gaps: production `/api/search` scoring integration, public API grouped-result shape, real LLM prompt changes, provider feeds for live open lift/piste status, and hotel-level inventory ingestion remain separate future implementation slices.
- Type consistency: `FactorAvailabilityState` is defined in `app/domain/ranking_comparison.py` and reused by `app/domain/scoring_scenarios.py`; scenario runner uses existing `SearchResult`, `FactorComparisonInput`, and `compare_rankings` contracts.
