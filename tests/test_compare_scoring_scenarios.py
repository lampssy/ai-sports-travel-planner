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
