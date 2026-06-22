import json

from app.data.compare_ranking import write_ranking_comparison_artifacts
from app.domain.ranking_comparison import RankingComparisonReport, RankingComparisonRow


def test_write_ranking_comparison_artifacts_creates_json_and_markdown(tmp_path) -> None:
    report = RankingComparisonReport(
        rows=[
            RankingComparisonRow(
                option_key="candidate-top--candidate-top-ski-area--village-base",
                scenario_id="test_scenario",
                resort_id="candidate-top",
                resort_name="Candidate Top",
                selected_ski_area_id="candidate-top-ski-area",
                selected_ski_area_name="Candidate Top Ski Area",
                selected_stay_base_name="Village Base",
                current_rank=2,
                candidate_rank=1,
                rank_delta=-1,
                current_score=2.8,
                candidate_score=1.25,
                top_candidate_components={
                    "terrain": 0.28,
                    "snow_evidence": 0.26,
                    "stay_base_access": 0.18,
                },
            )
        ]
    )

    write_ranking_comparison_artifacts(report, output_dir=tmp_path)

    summary = json.loads(
        (tmp_path / "ranking-comparison-summary.json").read_text(encoding="utf-8")
    )
    markdown = (tmp_path / "ranking-comparison-report.md").read_text(encoding="utf-8")

    assert summary["rows"][0]["current_rank"] == 2
    assert summary["rows"][0]["candidate_rank"] == 1
    assert summary["rows"][0]["rank_delta"] == -1
    assert summary["rows"][0]["candidate_score"] == 1.25
    assert "terrain" in summary["rows"][0]["top_candidate_components"]
    assert summary["rows"][0]["scenario_id"] == "test_scenario"
    assert "| test_scenario | candidate-top | 2 | 1 | -1 |" in markdown
    assert "`terrain=0.280`" in markdown
