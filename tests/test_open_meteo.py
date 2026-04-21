from datetime import UTC, date, datetime, timedelta

import pytest

from app.data.backfill_historical_weather import (
    backfill_historical_weather,
)
from app.data.backfill_historical_weather import (
    main as backfill_main,
)
from app.data.reconcile_recent_archive import (
    main as reconcile_recent_archive_main,
)
from app.data.reconcile_recent_archive import (
    reconcile_recent_archive,
)
from app.data.refresh_conditions import main as refresh_main
from app.data.refresh_conditions import refresh_conditions
from app.data.repositories import (
    RawWeatherHistoryRepository,
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    ResortRepository,
)
from app.integrations.open_meteo import normalize_open_meteo_conditions


def test_normalize_open_meteo_maps_strong_snow_signal_to_open() -> None:
    resort = next(
        item for item in ResortRepository().list_resorts() if item.name == "Tignes"
    )

    conditions = normalize_open_meteo_conditions(
        resort,
        {
            "current": {
                "weather_code": 3,
                "temperature_2m": -4,
                "snowfall": 1.2,
                "wind_speed_10m": 18,
                "wind_gusts_10m": 25,
            },
            "daily": {
                "weather_code": [3],
                "temperature_2m_max": [-1],
                "temperature_2m_min": [-8],
                "snowfall_sum": [14],
                "wind_speed_10m_max": [22],
                "wind_gusts_10m_max": [30],
            },
        },
        observed_at=datetime(2026, 1, 15, tzinfo=UTC),
    )

    assert conditions.availability_status == "open"
    assert conditions.snow_confidence_label == "good"
    assert conditions.conditions_score > 0.7


def test_normalize_open_meteo_maps_severe_weather_to_temporary_closure() -> None:
    resort = next(
        item
        for item in ResortRepository().list_resorts()
        if item.name == "St Anton am Arlberg"
    )

    conditions = normalize_open_meteo_conditions(
        resort,
        {
            "current": {
                "weather_code": 95,
                "temperature_2m": -1,
                "snowfall": 0,
                "wind_speed_10m": 60,
                "wind_gusts_10m": 92,
            },
            "daily": {
                "weather_code": [95],
                "temperature_2m_max": [1],
                "temperature_2m_min": [-6],
                "snowfall_sum": [2],
                "wind_speed_10m_max": [68],
                "wind_gusts_10m_max": [92],
            },
        },
        observed_at=datetime(2026, 1, 15, tzinfo=UTC),
    )

    assert conditions.availability_status == "temporarily_closed"
    assert conditions.conditions_score < 0.4


def test_normalize_open_meteo_maps_out_of_season_from_resort_metadata() -> None:
    resort = next(
        item for item in ResortRepository().list_resorts() if item.name == "La Plagne"
    )

    conditions = normalize_open_meteo_conditions(
        resort,
        {
            "current": {
                "weather_code": 0,
                "temperature_2m": 8,
                "snowfall": 0,
                "wind_speed_10m": 8,
                "wind_gusts_10m": 14,
            },
            "daily": {
                "weather_code": [0],
                "temperature_2m_max": [10],
                "temperature_2m_min": [4],
                "snowfall_sum": [0],
                "wind_speed_10m_max": [15],
                "wind_gusts_10m_max": [18],
            },
        },
        observed_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    assert conditions.availability_status == "out_of_season"
    assert conditions.snow_confidence_label == "poor"


def test_normalize_open_meteo_summary_uses_normalized_snow_label() -> None:
    resort = next(
        item for item in ResortRepository().list_resorts() if item.name == "Tignes"
    )

    conditions = normalize_open_meteo_conditions(
        resort,
        {
            "current": {
                "weather_code": 0,
                "temperature_2m": 1.5,
                "snowfall": 0,
                "wind_speed_10m": 10,
                "wind_gusts_10m": 14,
            },
            "daily": {
                "weather_code": [0],
                "temperature_2m_max": [2],
                "temperature_2m_min": [-5],
                "snowfall_sum": [0],
                "wind_speed_10m_max": [12],
                "wind_gusts_10m_max": [14],
            },
        },
        observed_at=datetime(2026, 1, 15, tzinfo=UTC),
    )

    assert conditions.snow_confidence_label == "fair"
    assert conditions.weather_summary.startswith("Fair snow outlook")


class StubClient:
    def __init__(self, *, fail_for: str | None = None) -> None:
        self.fail_for = fail_for

    def fetch_conditions(self, resort) -> dict:
        if resort.name == self.fail_for:
            raise RuntimeError("provider failure")
        return {
            "current": {
                "weather_code": 3,
                "temperature_2m": -2,
                "snowfall": 0.4,
                "wind_speed_10m": 12,
                "wind_gusts_10m": 18,
            },
            "daily": {
                "weather_code": [3],
                "temperature_2m_max": [0],
                "temperature_2m_min": [-6],
                "snowfall_sum": [8],
                "wind_speed_10m_max": [20],
                "wind_gusts_10m_max": [25],
            },
            "hourly": {
                "time": [
                    "2026-01-15T00:00",
                    "2026-01-15T12:00",
                ],
                "snow_depth": [0.85, 0.9],
            },
        }

    def fetch_historical_weather(
        self,
        resort,
        *,
        start_date: date,
        end_date: date,
    ) -> dict:
        dates: list[date] = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)

        hourly_times: list[str] = []
        hourly_depths: list[float] = []
        for index, observed_on in enumerate(dates):
            hourly_times.extend(
                [
                    f"{observed_on.isoformat()}T00:00",
                    f"{observed_on.isoformat()}T12:00",
                ]
            )
            base_depth = 0.7 + (observed_on.day - 1) * 0.2
            hourly_depths.extend([base_depth, base_depth + 0.1])

        return {
            "daily": {
                "time": [observed_on.isoformat() for observed_on in dates],
                "weather_code": [3 + index for index, _ in enumerate(dates)],
                "temperature_2m_max": [-1 - index for index, _ in enumerate(dates)],
                "temperature_2m_min": [-7 - index for index, _ in enumerate(dates)],
                "snowfall_sum": [6 + (index * 3) for index, _ in enumerate(dates)],
                "wind_speed_10m_max": [
                    18 + (index * 4) for index, _ in enumerate(dates)
                ],
                "wind_gusts_10m_max": [
                    28 + (index * 4) for index, _ in enumerate(dates)
                ],
            },
            "hourly": {
                "time": hourly_times,
                "snow_depth": hourly_depths,
            },
            "model": "best_match",
        }


class FlakyClient(StubClient):
    def __init__(self, *, fail_once_for: str) -> None:
        super().__init__()
        self.fail_once_for = fail_once_for
        self.calls: dict[str, int] = {}

    def fetch_conditions(self, resort) -> dict:
        self.calls[resort.name] = self.calls.get(resort.name, 0) + 1
        if resort.name == self.fail_once_for and self.calls[resort.name] == 1:
            raise RuntimeError("temporary provider failure")
        return super().fetch_conditions(resort)


class FlakyHistoricalClient(StubClient):
    def __init__(self, *, fail_once_for: str) -> None:
        super().__init__()
        self.fail_once_for = fail_once_for
        self.calls: dict[tuple[str, str, str], int] = {}

    def fetch_historical_weather(
        self,
        resort,
        *,
        start_date: date,
        end_date: date,
    ) -> dict:
        key = (resort.name, start_date.isoformat(), end_date.isoformat())
        self.calls[key] = self.calls.get(key, 0) + 1
        if resort.name == self.fail_once_for and self.calls[key] == 1:
            raise RuntimeError("temporary archive timeout")
        return super().fetch_historical_weather(
            resort,
            start_date=start_date,
            end_date=end_date,
        )


class FailingHistoricalClient(StubClient):
    def __init__(self, *, fail_for: str) -> None:
        super().__init__()
        self.fail_for = fail_for

    def fetch_historical_weather(
        self,
        resort,
        *,
        start_date: date,
        end_date: date,
    ) -> dict:
        if resort.name == self.fail_for:
            raise RuntimeError("archive handshake timeout")
        return super().fetch_historical_weather(
            resort,
            start_date=start_date,
            end_date=end_date,
        )


class CountingHistoricalClient(StubClient):
    def __init__(self) -> None:
        super().__init__()
        self.calls: dict[tuple[str, str, str], int] = {}

    def fetch_historical_weather(
        self,
        resort,
        *,
        start_date: date,
        end_date: date,
    ) -> dict:
        key = (resort.name, start_date.isoformat(), end_date.isoformat())
        self.calls[key] = self.calls.get(key, 0) + 1
        return super().fetch_historical_weather(
            resort,
            start_date=start_date,
            end_date=end_date,
        )


def test_refresh_conditions_writes_rows_and_metadata() -> None:
    result = refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )

    repository = ResortConditionsRepository()
    history_repository = ResortConditionHistoryRepository()
    raw_history_repository = RawWeatherHistoryRepository()
    conditions = repository.get_conditions_for_resort("Tignes")
    snapshots = history_repository.list_snapshots_for_resort("tignes")
    raw_observations = raw_history_repository.list_observations_for_resort("tignes")

    assert result.refreshed > 0
    assert result.failed == 0
    assert conditions is not None
    assert conditions.updated_at == "2026-01-15T00:00:00+00:00"
    assert conditions.source == "open-meteo"
    assert len(snapshots) == 1
    assert snapshots[0].observed_month == 1
    assert len(raw_observations) == 1
    assert raw_observations[0].observed_on == "2026-01-15"
    assert raw_observations[0].snow_depth_m == pytest.approx(0.875)
    assert raw_observations[0].record_type == "forecast"


def test_refresh_conditions_appends_history_snapshots_when_forced() -> None:
    refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )
    refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 16, tzinfo=UTC),
        force=True,
    )

    snapshots = ResortConditionHistoryRepository().list_snapshots_for_resort("tignes")

    assert len(snapshots) == 2
    assert snapshots[0].observed_at == "2026-01-15T00:00:00+00:00"
    assert snapshots[1].observed_at == "2026-01-16T00:00:00+00:00"


def test_backfill_historical_weather_stores_daily_raw_rows_idempotently() -> None:
    result = backfill_historical_weather(
        client=StubClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        targets=("tignes",),
        chunk_days=2,
    )
    rerun = backfill_historical_weather(
        client=StubClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        targets=("tignes",),
        chunk_days=1,
    )

    observations = RawWeatherHistoryRepository().list_observations_for_resort("tignes")

    assert result.targeted_ski_areas == 1
    assert result.requested_chunks == 1
    assert result.inserted_or_updated == 2
    assert rerun.requested_chunks == 2
    assert len(observations) == 2
    assert observations[0].snow_depth_m == pytest.approx(0.75)
    assert observations[1].snow_depth_m == pytest.approx(0.95)
    assert all(observation.record_type == "archive" for observation in observations)


def test_raw_weather_history_repository_detects_complete_archive_coverage() -> None:
    backfill_historical_weather(
        client=StubClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        targets=("tignes",),
        chunk_days=2,
    )

    repository = RawWeatherHistoryRepository()

    assert repository.has_complete_archive_coverage(
        resort_id="tignes-ski-area",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
    )
    assert not repository.has_complete_archive_coverage(
        resort_id="tignes-ski-area",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 3),
    )


def test_raw_weather_history_repository_ignores_forecast_rows() -> None:
    refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )

    repository = RawWeatherHistoryRepository()

    assert not repository.has_complete_archive_coverage(
        resort_id="tignes",
        start_date=date(2026, 1, 15),
        end_date=date(2026, 1, 15),
    )


def test_backfill_historical_weather_skips_complete_archive_chunks() -> None:
    client = CountingHistoricalClient()

    initial = backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        targets=("tignes",),
        chunk_days=2,
    )
    rerun = backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        targets=("tignes",),
        chunk_days=2,
    )

    assert initial.skipped_chunks == 0
    assert rerun.skipped_chunks == 1
    assert rerun.inserted_or_updated == 0
    assert client.calls[("Tignes", "2024-01-01", "2024-01-02")] == 1


def test_backfill_historical_weather_force_refetch_bypasses_skip() -> None:
    client = CountingHistoricalClient()

    backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        targets=("tignes",),
        chunk_days=2,
    )
    rerun = backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        targets=("tignes",),
        chunk_days=2,
        force_refetch=True,
    )

    assert rerun.skipped_chunks == 0
    assert rerun.inserted_or_updated == 2
    assert client.calls[("Tignes", "2024-01-01", "2024-01-02")] == 2


def test_recent_archive_reconciliation_overwrites_forecast_rows_with_archive() -> None:
    refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        force=True,
        targets=("tignes",),
    )

    before = RawWeatherHistoryRepository().list_observations_for_resort("tignes")
    assert before[0].record_type == "forecast"

    result = reconcile_recent_archive(
        lookback_days=1,
        end_date=date(2026, 1, 15),
        targets=("tignes",),
    )
    after = RawWeatherHistoryRepository().list_observations_for_resort("tignes")

    assert result.backfill_result.failed_chunks == 0
    assert result.backfill_result.inserted_or_updated == 1
    assert after[0].record_type == "archive"


def test_recent_archive_reconciliation_is_idempotent() -> None:
    reconcile_recent_archive(
        lookback_days=1,
        end_date=date(2026, 1, 15),
        targets=("tignes",),
    )
    rerun = reconcile_recent_archive(
        lookback_days=1,
        end_date=date(2026, 1, 15),
        targets=("tignes",),
    )

    observations = RawWeatherHistoryRepository().list_observations_for_resort("tignes")

    assert rerun.backfill_result.failed_chunks == 0
    assert len(observations) == 1
    assert observations[0].record_type == "archive"


def test_backfill_historical_weather_retries_and_succeeds() -> None:
    result = backfill_historical_weather(
        client=FlakyHistoricalClient(fail_once_for="Tignes"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        targets=("tignes",),
        chunk_days=2,
        retry_attempts=1,
        backoff_seconds=0,
    )

    observations = RawWeatherHistoryRepository().list_observations_for_resort("tignes")

    assert result.failed_chunks == 0
    assert result.inserted_or_updated == 2
    assert len(observations) == 2


def test_backfill_historical_weather_records_failed_chunks_and_continues() -> None:
    result = backfill_historical_weather(
        client=FailingHistoricalClient(fail_for="Tignes"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        targets=("tignes", "cervinia"),
        chunk_days=2,
        retry_attempts=1,
        backoff_seconds=0,
    )

    tignes = RawWeatherHistoryRepository().list_observations_for_resort("tignes")
    cervinia = RawWeatherHistoryRepository().list_observations_for_resort("cervinia")

    assert result.failed_chunks == 1
    assert len(result.failures) == 1
    assert result.failures[0].resort_name == "Tignes"
    assert tignes == ()
    assert len(cervinia) == 2


def test_backfill_command_main_logs_progress(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.backfill_historical_weather",
        lambda **kwargs: type(
            "StubResult",
            (),
            {
                "targeted_ski_areas": 1,
                "requested_chunks": 2,
                "inserted_or_updated": 730,
                "failed_chunks": 0,
                "skipped_chunks": 1,
                "failures": [],
            },
        )(),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "backfill_historical_weather",
            "--start-date",
            "2021-01-01",
            "--end-date",
            "2022-12-31",
            "--resort",
            "tignes",
        ],
    )

    backfill_main()

    output = capsys.readouterr().out
    assert "Selected resorts: tignes" in output
    assert "Historical backfill complete:" in output
    assert "rows=730" in output
    assert "skipped_chunks=1" in output


def test_backfill_command_main_exits_non_zero_when_chunks_fail(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.backfill_historical_weather",
        lambda **kwargs: type(
            "StubResult",
            (),
            {
                "targeted_ski_areas": 1,
                "requested_chunks": 2,
                "inserted_or_updated": 365,
                "failed_chunks": 1,
                "skipped_chunks": 0,
                "failures": [
                    type(
                        "StubFailure",
                        (),
                        {
                            "resort_name": "Tignes",
                            "chunk_start": "2024-01-01",
                            "chunk_end": "2024-12-31",
                            "error": "archive handshake timeout",
                        },
                    )()
                ],
            },
        )(),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "backfill_historical_weather",
            "--start-date",
            "2021-01-01",
            "--end-date",
            "2022-12-31",
        ],
    )

    with pytest.raises(SystemExit) as error:
        backfill_main()

    output = capsys.readouterr().out
    assert error.value.code == 1
    assert "failed_chunks=1" in output
    assert "Failed chunks:" in output


def test_backfill_command_main_supports_force_refetch(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _stub_backfill(**kwargs):
        captured.update(kwargs)
        return type(
            "StubResult",
            (),
            {
                "targeted_ski_areas": 1,
                "requested_chunks": 1,
                "inserted_or_updated": 365,
                "failed_chunks": 0,
                "skipped_chunks": 0,
                "failures": [],
            },
        )()

    monkeypatch.setattr(
        "app.data.backfill_historical_weather.backfill_historical_weather",
        _stub_backfill,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "backfill_historical_weather",
            "--start-date",
            "2021-01-01",
            "--end-date",
            "2021-03-31",
            "--chunk-days",
            "90",
            "--resort",
            "tignes",
            "--force-refetch",
        ],
    )

    backfill_main()

    assert captured["targets"] == ("tignes",)
    assert captured["chunk_days"] == 90
    assert captured["force_refetch"] is True


def test_reconcile_recent_archive_main_logs_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "app.data.reconcile_recent_archive.reconcile_recent_archive",
        lambda **kwargs: type(
            "StubReconcileResult",
            (),
            {
                "start_date": date(2026, 1, 9),
                "end_date": date(2026, 1, 15),
                "backfill_result": type(
                    "StubBackfillResult",
                    (),
                    {
                        "targeted_ski_areas": 1,
                        "inserted_or_updated": 7,
                        "failed_chunks": 0,
                        "skipped_chunks": 0,
                        "failures": [],
                    },
                )(),
            },
        )(),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "reconcile_recent_archive",
            "--lookback-days",
            "7",
            "--resort",
            "tignes",
        ],
    )

    reconcile_recent_archive_main()

    output = capsys.readouterr().out
    assert "Selected resorts: tignes" in output
    assert "Recent archive reconciliation complete:" in output
    assert "rows=7" in output


def test_refresh_conditions_skips_fresh_rows() -> None:
    refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )

    result = refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, 12, tzinfo=UTC),
    )

    assert result.refreshed == 0
    assert result.skipped_fresh > 0


def test_refresh_conditions_force_recomputes_fresh_rows() -> None:
    refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )

    result = refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, 12, tzinfo=UTC),
        force=True,
    )

    conditions = ResortConditionsRepository().get_conditions_for_resort("Tignes")

    assert result.refreshed > 0
    assert result.skipped_fresh == 0
    assert conditions is not None
    assert conditions.updated_at == "2026-01-15T12:00:00+00:00"


def test_refresh_conditions_targets_single_resort_by_id() -> None:
    result = refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        targets=("tignes",),
    )

    repository = ResortConditionsRepository()

    assert result.refreshed == 1
    assert repository.get_conditions_for_resort("Tignes") is not None
    assert repository.get_conditions_for_resort("Chamonix Mont-Blanc") is None


def test_refresh_conditions_targets_single_resort_by_exact_name() -> None:
    result = refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        targets=("St Anton am Arlberg",),
    )

    repository = ResortConditionsRepository()

    assert result.refreshed == 1
    assert repository.get_conditions_for_resort("St Anton am Arlberg") is not None
    assert repository.get_conditions_for_resort("Tignes") is None


def test_refresh_conditions_force_and_targets_refresh_selected_fresh_row() -> None:
    refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        targets=("tignes",),
    )

    result = refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, 12, tzinfo=UTC),
        force=True,
        targets=("tignes",),
    )

    repository = ResortConditionsRepository()
    tignes = repository.get_conditions_for_resort("Tignes")
    chamonix = repository.get_conditions_for_resort("Chamonix Mont-Blanc")

    assert result.refreshed == 1
    assert result.skipped_fresh == 0
    assert tignes is not None
    assert tignes.updated_at == "2026-01-15T12:00:00+00:00"
    assert chamonix is None


def test_refresh_conditions_rejects_unknown_targets() -> None:
    with pytest.raises(ValueError, match="Unknown resort target"):
        refresh_conditions(
            client=StubClient(),
            now=datetime(2026, 1, 15, tzinfo=UTC),
            targets=("not-a-resort",),
        )


def test_refresh_conditions_retries_and_succeeds_on_second_attempt() -> None:
    result = refresh_conditions(
        client=FlakyClient(fail_once_for="Tignes"),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        backoff_seconds=0,
    )

    conditions = ResortConditionsRepository().get_conditions_for_resort("Tignes")

    assert result.failed == 0
    assert result.refreshed > 0
    assert conditions is not None


def test_refresh_conditions_keeps_stale_cached_rows_when_provider_fails() -> None:
    refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )

    result = refresh_conditions(
        client=StubClient(fail_for="Tignes"),
        now=datetime(2026, 1, 18, tzinfo=UTC),
        backoff_seconds=0,
    )
    conditions = ResortConditionsRepository().get_conditions_for_resort("Tignes")

    assert result.failed >= 1
    assert any(failure.resort_name == "Tignes" for failure in result.failures)
    assert conditions is not None
    assert conditions.updated_at == "2026-01-15T00:00:00+00:00"


def test_refresh_command_main_exits_non_zero_on_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "app.data.refresh_conditions.refresh_conditions",
        lambda **kwargs: refresh_conditions(
            client=StubClient(fail_for="Tignes"),
            now=datetime(2026, 1, 18, tzinfo=UTC),
            backoff_seconds=0,
        ),
    )
    monkeypatch.setattr("sys.argv", ["refresh_conditions"])

    with pytest.raises(SystemExit) as error:
        refresh_main()

    output = capsys.readouterr().out
    assert error.value.code == 1
    assert "failed=1" in output
    assert "Tignes" in output


def test_refresh_command_main_exits_non_zero_on_unknown_target(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["refresh_conditions", "--resort", "not-a-resort"],
    )

    with pytest.raises(SystemExit) as error:
        refresh_main()

    output = capsys.readouterr().out
    assert error.value.code == 1
    assert "Unknown resort target(s): not-a-resort" in output


def test_refresh_command_main_supports_force_and_target(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_conditions",
            "--database-url",
            "postgresql://planner:planner@127.0.0.1:5432/ai_sports_travel_planner_test",
            "--force",
            "--resort",
            "tignes",
        ],
    )

    refresh_main()

    output = capsys.readouterr().out
    assert "Selected resorts: tignes" in output
    assert "refreshed=1" in output
