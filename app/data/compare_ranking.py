from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.data.repositories import ResortRepository
from app.domain.models import (
    Destination,
    ResortConditions,
    SearchFilters,
    SearchResult,
    SkiArea,
    StayBase,
)
from app.domain.ranking_comparison import (
    FactorComparisonInput,
    RankingComparisonReport,
    compare_rankings,
    option_key_for_result,
)
from app.domain.resort_fit import (
    ResortFitFactor,
    skill_fit_factor_for_ski_area,
    stay_base_access_factor,
    terrain_scale_factor_for_ski_area,
)

DEFAULT_OUTPUT_DIR = Path("artifacts/ranking-comparison")
DEFAULT_SCENARIOS: tuple[tuple[str, SearchFilters], ...] = (
    (
        "france_intermediate_value",
        SearchFilters(
            location="France",
            min_price=120,
            max_price=340,
            stars=1,
            skill_level="intermediate",
        ),
    ),
    (
        "austria_advanced_access",
        SearchFilters(
            location="Austria",
            min_price=130,
            max_price=380,
            stars=1,
            skill_level="advanced",
        ),
    ),
    (
        "italy_beginner_value",
        SearchFilters(
            location="Italy",
            min_price=100,
            max_price=320,
            stars=1,
            skill_level="beginner",
        ),
    ),
    (
        "switzerland_intermediate",
        SearchFilters(
            location="Switzerland",
            min_price=150,
            max_price=460,
            stars=1,
            skill_level="intermediate",
        ),
    ),
)


class _NoConditionsProvider:
    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions | None:
        return None


class _EmptySnapshotRepository:
    def list_snapshots_for_resort(self, resort_id: str):
        return ()


class _EmptyRawHistoryRepository:
    def list_observations_for_resort(self, resort_id: str, **kwargs):
        return ()


class _EmptySnowClimatologyRepository:
    def list_rows_for_ski_area(self, ski_area_id: str, **kwargs):
        return ()


def build_factor_inputs_for_results(
    results: list[SearchResult],
    *,
    resorts: tuple[Destination, ...],
) -> dict[str, FactorComparisonInput]:
    resorts_by_id = {resort.resort_id: resort for resort in resorts}
    factor_inputs: dict[str, FactorComparisonInput] = {}
    for result in results:
        resort = resorts_by_id.get(result.resort_id)
        ski_area = _find_ski_area(resort, result.selected_ski_area_id)
        stay_base = _find_stay_base(resort, result.selected_stay_base_name)
        terrain_factor = (
            terrain_scale_factor_for_ski_area(ski_area)
            if ski_area is not None
            else None
        )
        skill_factor = (
            skill_fit_factor_for_ski_area(ski_area) if ski_area is not None else None
        )
        access_factor = (
            stay_base_access_factor(stay_base) if stay_base is not None else None
        )
        factor_inputs[option_key_for_result(result)] = FactorComparisonInput(
            terrain_scale=_string_value(terrain_factor),
            terrain_trust_cap=_candidate_cap(terrain_factor),
            skill_fit=_tuple_value(skill_factor),
            skill_trust_cap=_candidate_cap(skill_factor),
            stay_base_access=_string_value(access_factor),
            access_trust_cap=_candidate_cap(access_factor),
        )
    return factor_inputs


def run_ranking_comparison_for_results(
    results: list[SearchResult],
    *,
    resorts: tuple[Destination, ...],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    scenario_id: str = "default",
) -> RankingComparisonReport:
    report = compare_rankings(
        results,
        factor_inputs=build_factor_inputs_for_results(results, resorts=resorts),
        scenario_id=scenario_id,
    )
    write_ranking_comparison_artifacts(report, output_dir=output_dir)
    return report


def run_ranking_comparison(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> RankingComparisonReport:
    from app.domain.search_service import search_resorts

    resorts = ResortRepository().list_resorts()
    rows = []
    for scenario_id, filters in DEFAULT_SCENARIOS:
        results = search_resorts(
            filters,
            resorts=resorts,
            conditions_provider=_NoConditionsProvider(),
            condition_history_repository=_EmptySnapshotRepository(),
            raw_weather_history_repository=_EmptyRawHistoryRepository(),
            snow_climatology_repository=_EmptySnowClimatologyRepository(),
        )
        report = compare_rankings(
            results,
            factor_inputs=build_factor_inputs_for_results(results, resorts=resorts),
            scenario_id=scenario_id,
        )
        rows.extend(report.rows)
    combined_report = RankingComparisonReport(rows=rows)
    write_ranking_comparison_artifacts(combined_report, output_dir=output_dir)
    return combined_report


def write_ranking_comparison_artifacts(
    report: RankingComparisonReport,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {"rows": [asdict(row) for row in report.rows]}
    (output_dir / "ranking-comparison-summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "ranking-comparison-report.md").write_text(
        _render_markdown_report(report),
        encoding="utf-8",
    )


def _render_markdown_report(report: RankingComparisonReport) -> str:
    lines = [
        "# Ranking Comparison Report",
        "",
        "| Scenario | Resort | Current Rank | Candidate Rank | Rank Delta | "
        "Candidate Score | Top Components |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in report.rows:
        components = ", ".join(
            f"`{name}={value:.3f}`"
            for name, value in row.top_candidate_components.items()
        )
        lines.append(
            "| "
            f"{row.scenario_id} | "
            f"{row.resort_id} | "
            f"{row.current_rank} | "
            f"{row.candidate_rank} | "
            f"{row.rank_delta} | "
            f"{row.candidate_score:.3f} | "
            f"{components} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write debug-only current-vs-candidate ranking diagnostics."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for JSON and Markdown ranking comparison artifacts.",
    )
    args = parser.parse_args()
    report = run_ranking_comparison(output_dir=args.output_dir)
    print(
        "Ranking comparison:",
        f"rows={len(report.rows)}",
        f"output_dir={args.output_dir}",
    )


def _find_ski_area(resort: Destination | None, ski_area_id: str) -> SkiArea | None:
    if resort is None:
        return None
    return next(
        (
            ski_area
            for ski_area in resort.ski_areas
            if ski_area.ski_area_id == ski_area_id
        ),
        None,
    )


def _find_stay_base(resort: Destination | None, stay_base_name: str) -> StayBase | None:
    if resort is None:
        return None
    normalized_name = stay_base_name.strip().casefold()
    return next(
        (
            stay_base
            for stay_base in resort.stay_bases
            if stay_base.name.strip().casefold() == normalized_name
        ),
        None,
    )


def _candidate_cap(factor: ResortFitFactor | None) -> float:
    if factor is None or factor.lifecycle_state != "active":
        return 0.0
    return factor.ranking_cap


def _string_value(factor: ResortFitFactor | None) -> str | None:
    if factor is None or factor.value is None:
        return None
    if isinstance(factor.value, str):
        return factor.value
    return str(factor.value)


def _tuple_value(factor: ResortFitFactor | None) -> tuple[str, ...]:
    if factor is None or factor.value is None:
        return ()
    if isinstance(factor.value, tuple):
        return tuple(str(value) for value in factor.value)
    return (str(factor.value),)


if __name__ == "__main__":
    main()
