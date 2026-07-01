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
    TerrainDomain,
)
from app.domain.ranking_comparison import (
    FactorComparisonInput,
    RankingComparisonReport,
    compare_rankings,
    group_counts_for_rows,
    option_key_for_result,
)
from app.domain.resort_fit import (
    ResortFitFactor,
    accessible_terrain_factor_for_option,
    skill_fit_factor_for_ski_area,
    stay_base_access_factor,
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
    def list_snapshots_for_ski_area(self, ski_area_id: str):
        return ()


class _EmptyRawHistoryRepository:
    def list_observations_for_ski_area(self, ski_area_id: str, **kwargs):
        return ()


class _EmptySnowClimatologyRepository:
    def list_rows_for_ski_area(self, ski_area_id: str, **kwargs):
        return ()


def build_factor_inputs_for_results(
    results: list[SearchResult],
    *,
    resorts: tuple[Destination, ...],
    terrain_domains: tuple[TerrainDomain, ...] = (),
) -> dict[str, FactorComparisonInput]:
    resorts_by_id = {resort.resort_id: resort for resort in resorts}
    factor_inputs: dict[str, FactorComparisonInput] = {}
    for result in results:
        resort = resorts_by_id.get(result.resort_id)
        ski_area = _find_ski_area(resort, result.selected_ski_area_id)
        stay_base = _find_stay_base(resort, result.selected_stay_base_name)
        terrain_factor = (
            accessible_terrain_factor_for_option(
                destination=resort,
                selected_ski_area_id=result.selected_ski_area_id,
                terrain_domains=terrain_domains,
            )
            if resort is not None
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
            candidate_factor_sources=_factor_sources(terrain_factor),
            result_group_key=_result_group_key(terrain_factor, result.resort_id),
        )
    return factor_inputs


def run_ranking_comparison_for_results(
    results: list[SearchResult],
    *,
    resorts: tuple[Destination, ...],
    terrain_domains: tuple[TerrainDomain, ...] = (),
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    scenario_id: str = "default",
) -> RankingComparisonReport:
    report = compare_rankings(
        results,
        factor_inputs=build_factor_inputs_for_results(
            results,
            resorts=resorts,
            terrain_domains=terrain_domains,
        ),
        scenario_id=scenario_id,
    )
    write_ranking_comparison_artifacts(report, output_dir=output_dir)
    return report


def run_ranking_comparison(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> RankingComparisonReport:
    from app.domain.search_service import search_resorts

    repository = ResortRepository()
    resorts = repository.list_resorts()
    terrain_domains = repository.list_terrain_domains()
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
            factor_inputs=build_factor_inputs_for_results(
                results,
                resorts=resorts,
                terrain_domains=terrain_domains,
            ),
            scenario_id=scenario_id,
        )
        rows.extend(report.rows)
    combined_report = RankingComparisonReport(
        rows=rows,
        group_counts=group_counts_for_rows(rows),
    )
    write_ranking_comparison_artifacts(combined_report, output_dir=output_dir)
    return combined_report


def write_ranking_comparison_artifacts(
    report: RankingComparisonReport,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "group_counts": report.group_counts,
        "rows": [asdict(row) for row in report.rows],
    }
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
        "## Group Counts",
        "",
    ]
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
            "Rank Delta | Candidate Score | Factor Sources | Factor Availability | "
            "Missing Factor Notes | Top Components |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in report.rows:
        factor_sources = ", ".join(
            f"`{name}={value}`"
            for name, value in sorted(row.candidate_factor_sources.items())
        )
        if not factor_sources:
            factor_sources = "-"
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
            f"{factor_sources} | "
            f"{factor_availability} | "
            f"{missing_notes} | "
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
        f"groups={len(report.group_counts)}",
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


def _factor_sources(factor: ResortFitFactor | None) -> dict[str, str]:
    if factor is None:
        return {}
    sources: dict[str, str] = {}
    for key in ("terrain_source_scope", "terrain_source_id"):
        value = factor.raw_inputs.get(key)
        if value is not None:
            sources[key] = str(value)
    return sources


def _result_group_key(factor: ResortFitFactor | None, resort_id: str) -> str:
    sources = _factor_sources(factor)
    terrain_source_scope = sources.get("terrain_source_scope")
    terrain_source_id = sources.get("terrain_source_id")
    if terrain_source_scope == "terrain_domain" and terrain_source_id:
        return f"terrain-domain:{terrain_source_id}"
    return f"destination:{resort_id}"


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
