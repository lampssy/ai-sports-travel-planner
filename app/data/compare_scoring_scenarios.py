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
    FactorAvailabilityState,
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
    selected_ski_area_id: str,
    selected_stay_base_name: str,
    score: float,
    rating_estimate: int,
    snow_confidence_score: float,
    conditions_score: float,
    budget_penalty: float = 0.0,
) -> SearchResult:
    resort_name = resort_id.replace("-", " ").title()
    ski_area_name = selected_ski_area_id.replace("-", " ").title()
    return SearchResult(
        resort_id=resort_id,
        resort_name=resort_name,
        region="Synthetic Alps",
        selected_ski_area_id=selected_ski_area_id,
        selected_ski_area_name=ski_area_name,
        selected_stay_base_name=selected_stay_base_name,
        selected_stay_base_lift_distance="near",
        stay_base_price_range="synthetic stay price",
        selected_area_name=selected_stay_base_name,
        selected_area_lift_distance="near",
        area_price_range="synthetic area price",
        rental_name=f"{resort_name} Rental",
        rental_price_range="synthetic rental price",
        rating_estimate=rating_estimate,
        link=f"https://example.invalid/{resort_id}",
        score=score,
        budget_penalty=budget_penalty,
        conditions_summary="Synthetic scoring scenario conditions.",
        snow_confidence_score=snow_confidence_score,
        snow_confidence_label="good",
        availability_status="open",
        conditions_score=conditions_score,
        conditions_provenance=_provenance(),
        explanation=_explanation(),
        recommendation_confidence=0.75,
    )


def _factor(
    *,
    terrain_scale: str | None,
    skill_fit: tuple[str, ...],
    stay_base_access: str | None,
    factor_availability: dict[str, FactorAvailabilityState],
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
    factor_availability = dict(scenario.factor_availability)
    missing_factor_notes = dict(scenario.missing_factor_notes)
    if scenario.expected_today_status == "blocked_by_missing_data":
        result = _result(
            resort_id=scenario.scenario_id.replace("_", "-"),
            selected_ski_area_id="unresolved-area",
            selected_stay_base_name="Unresolved Base",
            score=2.0,
            rating_estimate=2,
            snow_confidence_score=0.65,
            conditions_score=0.65,
        )
        return (
            [result],
            {
                option_key_for_result(result): _factor(
                    terrain_scale=None,
                    skill_fit=(),
                    stay_base_access=None,
                    factor_availability=factor_availability,
                    missing_factor_notes=missing_factor_notes,
                )
            },
        )

    if scenario.expected_today_winner_key is None:
        raise ValueError(f"{scenario.scenario_id}: scenario winner key is required")

    winner_resort_id, winner_ski_area_id, winner_stay_base_slug = (
        scenario.expected_today_winner_key.split("--")
    )
    weaker_result = _result(
        resort_id=f"{scenario.scenario_id.replace('_', '-')}-weaker",
        selected_ski_area_id="weaker-area",
        selected_stay_base_name="Weaker Base",
        score=3.0,
        rating_estimate=1,
        snow_confidence_score=0.35,
        conditions_score=0.35,
        budget_penalty=0.08,
    )
    winner_result = _result(
        resort_id=winner_resort_id,
        selected_ski_area_id=winner_ski_area_id,
        selected_stay_base_name=winner_stay_base_slug.replace("-", " ").title(),
        score=2.5,
        rating_estimate=3,
        snow_confidence_score=0.9,
        conditions_score=0.85,
    )
    factor_inputs = {
        option_key_for_result(weaker_result): _factor(
            terrain_scale="small",
            skill_fit=("intermediate",),
            stay_base_access="car_recommended",
            factor_availability=factor_availability,
            missing_factor_notes=missing_factor_notes,
        ),
        option_key_for_result(winner_result): _factor(
            terrain_scale=_winner_terrain_scale(scenario),
            skill_fit=_winner_skill_fit(scenario),
            stay_base_access="walkable",
            factor_availability=factor_availability,
            missing_factor_notes=missing_factor_notes,
            result_group_key=_winner_result_group_key(scenario),
        ),
    }
    return [weaker_result, winner_result], factor_inputs


def _winner_terrain_scale(scenario: ScoringScenario) -> str:
    if any(
        token in scenario.scenario_id
        for token in ("terrain", "advanced", "shared_domain")
    ):
        return "mega"
    return "medium"


def _winner_skill_fit(scenario: ScoringScenario) -> tuple[str, ...]:
    if "mixed_skill" in scenario.scenario_id:
        return ("beginner", "intermediate", "advanced")
    if "beginner" in scenario.scenario_id:
        return ("beginner",)
    return ("intermediate", "advanced")


def _winner_result_group_key(scenario: ScoringScenario) -> str | None:
    if "shared_domain" in scenario.scenario_id:
        return "terrain-domain:tignes-val-disere"
    return None


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
    output_dir: Path = DEFAULT_OUTPUT_DIR,
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
        _render_markdown_report(report, scenario_statuses=scenario_statuses),
        encoding="utf-8",
    )


def _render_markdown_report(
    report: RankingComparisonReport,
    *,
    scenario_statuses: dict[str, str],
) -> str:
    lines = [
        "# Scoring Scenario Report",
        "",
        "## Scenario Statuses",
        "",
    ]
    for scenario_id, status in sorted(scenario_statuses.items()):
        lines.append(f"- `{scenario_id}`: `{status}`")
    lines.extend(
        [
            "",
            "## Group Counts",
            "",
        ]
    )
    if report.group_counts:
        for group_key, count in sorted(report.group_counts.items()):
            lines.append(f"- `{group_key}`: {count}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| Scenario | Resort | Result Group | Current Rank | Candidate Rank | "
            "Rank Delta | Candidate Score | Factor Availability | "
            "Missing Factor Notes | Top Components |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in report.rows:
        factor_availability = ", ".join(
            f"`{name}={value}`"
            for name, value in sorted(row.factor_availability.items())
        )
        if not factor_availability:
            factor_availability = "-"
        missing_notes = "; ".join(
            f"{name}: {note}" for name, note in sorted(row.missing_factor_notes.items())
        )
        if not missing_notes:
            missing_notes = "-"
        components = ", ".join(
            f"`{name}={value:.3f}`"
            for name, value in row.top_candidate_components.items()
        )
        lines.append(
            "| "
            f"{row.scenario_id} | "
            f"{row.resort_id} | "
            f"{row.result_group_key} | "
            f"{row.current_rank} | "
            f"{row.candidate_rank} | "
            f"{row.rank_delta} | "
            f"{row.candidate_score:.3f} | "
            f"{factor_availability} | "
            f"{missing_notes} | "
            f"{components} |"
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
