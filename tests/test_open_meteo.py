from datetime import UTC, datetime

import pytest

from app.data.refresh_conditions import main, refresh_conditions
from app.data.repositories import (
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    ResortRepository,
)
from app.integrations.open_meteo import normalize_open_meteo_conditions


def test_normalize_open_meteo_maps_strong_snow_signal_to_open(tmp_path) -> None:
    resort = next(
        item
        for item in ResortRepository(tmp_path / "planner.db").list_resorts()
        if item.name == "Tignes"
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


def test_normalize_open_meteo_maps_severe_weather_to_temporary_closure(
    tmp_path,
) -> None:
    resort = next(
        item
        for item in ResortRepository(tmp_path / "planner.db").list_resorts()
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


def test_normalize_open_meteo_maps_out_of_season_from_resort_metadata(tmp_path) -> None:
    resort = next(
        item
        for item in ResortRepository(tmp_path / "planner.db").list_resorts()
        if item.name == "La Plagne"
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


def test_normalize_open_meteo_summary_uses_normalized_snow_label(tmp_path) -> None:
    resort = next(
        item
        for item in ResortRepository(tmp_path / "planner.db").list_resorts()
        if item.name == "Tignes"
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


def test_refresh_conditions_writes_rows_and_metadata(tmp_path) -> None:
    result = refresh_conditions(
        db_path=tmp_path / "planner.db",
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )

    repository = ResortConditionsRepository(tmp_path / "planner.db")
    history_repository = ResortConditionHistoryRepository(tmp_path / "planner.db")
    conditions = repository.get_conditions_for_resort("Tignes")
    snapshots = history_repository.list_snapshots_for_resort("tignes")

    assert result.refreshed > 0
    assert result.failed == 0
    assert conditions is not None
    assert conditions.updated_at == "2026-01-15T00:00:00+00:00"
    assert conditions.source == "open-meteo"
    assert len(snapshots) == 1
    assert snapshots[0].observed_month == 1


def test_refresh_conditions_appends_history_snapshots_when_forced(tmp_path) -> None:
    db_path = tmp_path / "planner.db"
    refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )
    refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 16, tzinfo=UTC),
        force=True,
    )

    snapshots = ResortConditionHistoryRepository(db_path).list_snapshots_for_resort(
        "tignes"
    )

    assert len(snapshots) == 2
    assert snapshots[0].observed_at == "2026-01-15T00:00:00+00:00"
    assert snapshots[1].observed_at == "2026-01-16T00:00:00+00:00"


def test_refresh_conditions_skips_fresh_rows(tmp_path) -> None:
    db_path = tmp_path / "planner.db"
    refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )

    result = refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 15, 12, tzinfo=UTC),
    )

    assert result.refreshed == 0
    assert result.skipped_fresh > 0


def test_refresh_conditions_force_recomputes_fresh_rows(tmp_path) -> None:
    db_path = tmp_path / "planner.db"
    refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )

    result = refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 15, 12, tzinfo=UTC),
        force=True,
    )

    conditions = ResortConditionsRepository(db_path).get_conditions_for_resort("Tignes")

    assert result.refreshed > 0
    assert result.skipped_fresh == 0
    assert conditions is not None
    assert conditions.updated_at == "2026-01-15T12:00:00+00:00"


def test_refresh_conditions_targets_single_resort_by_id(tmp_path) -> None:
    db_path = tmp_path / "planner.db"

    result = refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        targets=("tignes",),
    )

    repository = ResortConditionsRepository(db_path)

    assert result.refreshed == 1
    assert repository.get_conditions_for_resort("Tignes") is not None
    assert repository.get_conditions_for_resort("Chamonix Mont-Blanc") is None


def test_refresh_conditions_targets_single_resort_by_exact_name(tmp_path) -> None:
    db_path = tmp_path / "planner.db"

    result = refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        targets=("St Anton am Arlberg",),
    )

    repository = ResortConditionsRepository(db_path)

    assert result.refreshed == 1
    assert repository.get_conditions_for_resort("St Anton am Arlberg") is not None
    assert repository.get_conditions_for_resort("Tignes") is None


def test_refresh_conditions_force_and_targets_refresh_selected_fresh_row(
    tmp_path,
) -> None:
    db_path = tmp_path / "planner.db"
    refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        targets=("tignes",),
    )

    result = refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 15, 12, tzinfo=UTC),
        force=True,
        targets=("tignes",),
    )

    repository = ResortConditionsRepository(db_path)
    tignes = repository.get_conditions_for_resort("Tignes")
    chamonix = repository.get_conditions_for_resort("Chamonix Mont-Blanc")

    assert result.refreshed == 1
    assert result.skipped_fresh == 0
    assert tignes is not None
    assert tignes.updated_at == "2026-01-15T12:00:00+00:00"
    assert chamonix is None


def test_refresh_conditions_rejects_unknown_targets(tmp_path) -> None:
    with pytest.raises(ValueError, match="Unknown resort target"):
        refresh_conditions(
            db_path=tmp_path / "planner.db",
            client=StubClient(),
            now=datetime(2026, 1, 15, tzinfo=UTC),
            targets=("not-a-resort",),
        )


def test_refresh_conditions_retries_and_succeeds_on_second_attempt(tmp_path) -> None:
    result = refresh_conditions(
        db_path=tmp_path / "planner.db",
        client=FlakyClient(fail_once_for="Tignes"),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        backoff_seconds=0,
    )

    conditions = ResortConditionsRepository(
        tmp_path / "planner.db"
    ).get_conditions_for_resort("Tignes")

    assert result.failed == 0
    assert result.refreshed > 0
    assert conditions is not None


def test_refresh_conditions_keeps_stale_cached_rows_when_provider_fails(
    tmp_path,
) -> None:
    db_path = tmp_path / "planner.db"
    refresh_conditions(
        db_path=db_path,
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
    )

    result = refresh_conditions(
        db_path=db_path,
        client=StubClient(fail_for="Tignes"),
        now=datetime(2026, 1, 18, tzinfo=UTC),
        backoff_seconds=0,
    )
    conditions = ResortConditionsRepository(db_path).get_conditions_for_resort("Tignes")

    assert result.failed >= 1
    assert any(failure.resort_name == "Tignes" for failure in result.failures)
    assert conditions is not None
    assert conditions.updated_at == "2026-01-15T00:00:00+00:00"


def test_refresh_command_main_exits_non_zero_on_failure(
    monkeypatch, tmp_path, capsys
) -> None:
    monkeypatch.setattr(
        "app.data.refresh_conditions.refresh_conditions",
        lambda **kwargs: refresh_conditions(
            db_path=tmp_path / "planner.db",
            client=StubClient(fail_for="Tignes"),
            now=datetime(2026, 1, 18, tzinfo=UTC),
            backoff_seconds=0,
        ),
    )
    monkeypatch.setattr("sys.argv", ["refresh_conditions"])

    with pytest.raises(SystemExit) as error:
        main()

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
        main()

    output = capsys.readouterr().out
    assert error.value.code == 1
    assert "Unknown resort target(s): not-a-resort" in output


def test_refresh_command_main_supports_force_and_target(
    monkeypatch, tmp_path, capsys
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_conditions",
            "--db-path",
            str(tmp_path / "planner.db"),
            "--force",
            "--resort",
            "tignes",
        ],
    )

    main()

    output = capsys.readouterr().out
    assert "Selected resorts: tignes" in output
    assert "refreshed=1" in output
