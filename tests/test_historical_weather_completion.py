from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.data.backfill_historical_weather import (
    HistoricalBackfillFailure,
    HistoricalBackfillResult,
)
from app.data.catalog_loader import load_catalog
from app.data.complete_historical_weather import complete_historical_weather
from app.data.rebuild_snow_climatology import SnowClimatologyRebuildResult
from app.data.repositories import ArchiveCoverageStats, ClimatologyCoverageStats


class _CatalogRepository:
    def __init__(self, _database_url: str) -> None:
        pass

    def get_snapshot(self):
        return load_catalog()


class _RawRepository:
    def __init__(self, coverage):
        self._coverage = coverage

    def list_archive_coverage(self, **_kwargs):
        return self._coverage


class _ClimatologyRepository:
    def __init__(self, coverage):
        self._coverage = coverage

    def list_climatology_coverage(self, **_kwargs):
        return self._coverage


def _archive_coverage(*, complete: bool) -> dict:
    covered_days = 1 if complete else 0
    return {
        ("tignes-ski-area", band): ArchiveCoverageStats(
            covered_days=covered_days,
            first_observed_on="2025-12-31" if complete else None,
            last_observed_on="2025-12-31" if complete else None,
        )
        for band in ("base", "mid", "upper")
    }


def _climatology_coverage(*, complete: bool) -> dict:
    return {
        ("tignes-ski-area", band, period): ClimatologyCoverageStats(
            row_count=366 if complete else 0,
            min_evidence_seasons=15 if complete else None,
            latest_archive_year=2025 if complete else None,
            baseline_end_year=2025 if complete else None,
        )
        for band in ("base", "mid", "upper")
        for period in ("normal_30y", "recent_15y")
    }


def _patch_dependencies(
    monkeypatch,
    *,
    backfill_result: HistoricalBackfillResult,
    archive_complete: bool,
    climatology_complete: bool,
) -> list[tuple[str, ...]]:
    rebuilt: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        "app.data.complete_historical_weather.bootstrap_database",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.data.complete_historical_weather.CatalogRepository",
        _CatalogRepository,
    )
    monkeypatch.setattr(
        "app.data.complete_historical_weather.backfill_historical_weather",
        lambda **_kwargs: backfill_result,
    )
    monkeypatch.setattr(
        "app.data.complete_historical_weather.RawWeatherHistoryRepository",
        lambda _database_url: _RawRepository(
            _archive_coverage(complete=archive_complete)
        ),
    )
    monkeypatch.setattr(
        "app.data.complete_historical_weather.SnowClimatologyRepository",
        lambda _database_url: _ClimatologyRepository(
            _climatology_coverage(complete=climatology_complete)
        ),
    )

    def _rebuild(**kwargs):
        rebuilt.append(kwargs["ski_area_ids"])
        return SnowClimatologyRebuildResult(
            targeted_ski_areas=len(kwargs["ski_area_ids"]),
            climatology_rows_written=2196 * len(kwargs["ski_area_ids"]),
        )

    monkeypatch.setattr(
        "app.data.complete_historical_weather.rebuild_snow_climatology",
        _rebuild,
    )
    return rebuilt


@pytest.mark.db_free
def test_completion_rebuilds_only_archive_complete_stale_area(monkeypatch) -> None:
    rebuilt = _patch_dependencies(
        monkeypatch,
        backfill_result=HistoricalBackfillResult(targeted_ski_areas=1),
        archive_complete=True,
        climatology_complete=False,
    )

    result = complete_historical_weather(
        database_url="postgresql://unused",
        start_date=date(2025, 12, 31),
        end_date=date(2025, 12, 31),
        baseline_end_year=2025,
        ski_area_ids=("tignes-ski-area",),
        max_provider_requests=200,
    )

    assert result.outcome == "complete"
    assert result.archive_complete_ski_areas == 1
    assert result.remaining_ski_areas == 0
    assert result.climatology_rebuilt_ski_areas == 1
    assert rebuilt == [("tignes-ski-area",)]


@pytest.mark.db_free
def test_completion_skips_current_climatology(monkeypatch) -> None:
    rebuilt = _patch_dependencies(
        monkeypatch,
        backfill_result=HistoricalBackfillResult(targeted_ski_areas=1),
        archive_complete=True,
        climatology_complete=True,
    )
    monkeypatch.setattr(
        "app.data.complete_historical_weather.backfill_historical_weather",
        lambda **_kwargs: pytest.fail(
            "archive-complete ski areas must not enter chunked backfill"
        ),
    )

    result = complete_historical_weather(
        database_url="postgresql://unused",
        start_date=date(2025, 12, 31),
        end_date=date(2025, 12, 31),
        baseline_end_year=2025,
        ski_area_ids=("tignes-ski-area",),
        max_provider_requests=200,
    )

    assert result.outcome == "complete"
    assert result.climatology_rebuilt_ski_areas == 0
    assert rebuilt == []


@pytest.mark.db_free
def test_completion_treats_rate_limit_as_resumable(monkeypatch) -> None:
    rebuilt = _patch_dependencies(
        monkeypatch,
        backfill_result=HistoricalBackfillResult(
            targeted_ski_areas=1,
            failed_chunks=1,
            rate_limited=True,
            failures=[
                HistoricalBackfillFailure(
                    resort_name="Tignes",
                    elevation_band="base",
                    chunk_start="2025-12-31",
                    chunk_end="2025-12-31",
                    error="429 Too Many Requests",
                    is_rate_limited=True,
                )
            ],
        ),
        archive_complete=False,
        climatology_complete=False,
    )

    result = complete_historical_weather(
        database_url="postgresql://unused",
        start_date=date(2025, 12, 31),
        end_date=date(2025, 12, 31),
        baseline_end_year=2025,
        ski_area_ids=("tignes-ski-area",),
        max_provider_requests=200,
    )

    assert result.outcome == "throttled"
    assert result.remaining_ski_areas == 1
    assert result.hard_failures == 0
    assert rebuilt == []


@pytest.mark.db_free
def test_completion_preserves_hard_failure_precedence(monkeypatch) -> None:
    rebuilt = _patch_dependencies(
        monkeypatch,
        backfill_result=HistoricalBackfillResult(
            targeted_ski_areas=1,
            failed_chunks=1,
            failures=[
                HistoricalBackfillFailure(
                    resort_name="Tignes",
                    elevation_band="base",
                    chunk_start="2025-12-31",
                    chunk_end="2025-12-31",
                    error="invalid provider payload",
                )
            ],
        ),
        archive_complete=False,
        climatology_complete=False,
    )

    result = complete_historical_weather(
        database_url="postgresql://unused",
        start_date=date(2025, 12, 31),
        end_date=date(2025, 12, 31),
        baseline_end_year=2025,
        ski_area_ids=("tignes-ski-area",),
        max_provider_requests=200,
    )

    assert result.outcome == "hard_failure"
    assert result.hard_failures == 1
    assert rebuilt == []


@pytest.mark.db_free
def test_archive_workflows_share_provider_concurrency_group() -> None:
    workflow_paths = (
        Path(".github/workflows/backfill-historical-weather.yml"),
        Path(".github/workflows/reconcile-recent-archive.yml"),
        Path(".github/workflows/complete-historical-weather.yml"),
    )

    for workflow_path in workflow_paths:
        workflow = workflow_path.read_text(encoding="utf-8")
        assert "group: open-meteo-archive-writes" in workflow
        assert "cancel-in-progress: false" in workflow

    completion_workflow = workflow_paths[-1].read_text(encoding="utf-8")
    assert "schedule:" in completion_workflow
    assert 'cron: "15 1 * * *"' in completion_workflow
    assert 'default: "200"' in completion_workflow
    assert "--rebuild" not in completion_workflow

    forecast_workflow = Path(
        ".github/workflows/refresh-weather-forecasts.yml"
    ).read_text(encoding="utf-8")
    assert 'cron: "25 */6 * * *"' in forecast_workflow
