from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.data.refresh_weather_forecasts import refresh_forecast_source
from app.domain.weather_forecast import WeatherForecastDaily, WeatherForecastRun
from app.integrations.open_meteo_forecast import (
    ForecastRequestPoint,
    ModelCycleMetadata,
)

pytestmark = pytest.mark.db_free


class _Repository:
    def __init__(self, *, existing_run_id: str | None = None) -> None:
        self.existing_run_id = existing_run_id
        self.lookup_area_ids: list[tuple[str, ...]] = []
        self.created: list[WeatherForecastRun] = []
        self.rows: list[WeatherForecastDaily] = []
        self.published: list[tuple[str, tuple[str, ...]]] = []
        self.terminal: list[tuple[str, str, str]] = []

    def find_complete_run_id(
        self,
        source_key: str,
        model_initialization_time: datetime,
        ski_area_ids: tuple[str, ...],
    ) -> str | None:
        self.lookup_area_ids.append(ski_area_ids)
        return self.existing_run_id

    def create_building_run(self, run: WeatherForecastRun) -> None:
        self.created.append(run)

    def insert_daily_rows(
        self,
        run_id: str,
        rows: tuple[WeatherForecastDaily, ...],
    ) -> None:
        assert all(row.forecast_run_id == run_id for row in rows)
        self.rows.extend(rows)

    def complete_run_and_advance_heads(
        self,
        run_id: str,
        *,
        publishable_ski_area_ids: tuple[str, ...],
        completed_at: datetime,
    ) -> None:
        self.published.append((run_id, publishable_ski_area_ids))

    def reject_or_fail_run(
        self,
        run_id: str,
        *,
        status: str,
        reason: str,
        completed_at: datetime,
    ) -> None:
        self.terminal.append((run_id, status, reason))


class _Client:
    def __init__(
        self,
        *,
        cycles: tuple[ModelCycleMetadata, ModelCycleMetadata],
        payloads: tuple[dict[str, object], ...],
    ) -> None:
        self.cycles = list(cycles)
        self.payloads = payloads
        self.fetch_calls = 0

    def fetch_model_cycle(self, source_key: str) -> ModelCycleMetadata:
        cycle = self.cycles.pop(0)
        assert cycle.source_key == source_key
        return cycle

    def fetch_hourly(
        self,
        source_key: str,
        points: tuple[ForecastRequestPoint, ...],
    ) -> tuple[dict[str, object], ...]:
        self.fetch_calls += 1
        return self.payloads[: len(points)]


class _Clock:
    def __init__(self, now: datetime) -> None:
        self.value = now
        self.sleeps: list[float] = []

    def now(self) -> datetime:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += timedelta(seconds=seconds)


def _point(area_id: str) -> ForecastRequestPoint:
    return ForecastRequestPoint(
        ski_area_id=area_id,
        latitude=47,
        longitude=11,
        elevation_m=2000,
    )


def _cycle(initialized_at: datetime) -> ModelCycleMetadata:
    return ModelCycleMetadata(
        source_key="ecmwf_ifs025_ensemble_mean",
        initialization_time=initialized_at,
        availability_time=initialized_at + timedelta(hours=7),
        raw_metadata={"last_run_initialisation_time": int(initialized_at.timestamp())},
    )


def _complete_payload(day: date) -> dict[str, object]:
    timezone = ZoneInfo("Europe/Vienna")
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone).astimezone(UTC)
    end = datetime.combine(
        day + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone,
    ).astimezone(UTC)
    epochs: list[int] = []
    current = start
    while current < end:
        epochs.append(int(current.timestamp()))
        current += timedelta(hours=1)
    count = len(epochs)
    return {
        "timezone": "Europe/Vienna",
        "hourly_units": {
            "time": "unixtime",
            "temperature_2m": "°C",
            "temperature_2m_spread": "K",
            "snowfall": "cm",
            "snowfall_spread": "cm",
            "rain": "mm",
            "snow_depth": "m",
            "snow_depth_spread": "m",
            "wind_speed_10m": "km/h",
            "wind_gusts_10m": "km/h",
        },
        "hourly": {
            "time": epochs,
            "temperature_2m": [-3.0] * count,
            "temperature_2m_spread": [1.0] * count,
            "snowfall": [0.5] * count,
            "snowfall_spread": [0.1] * count,
            "rain": [0.0] * count,
            "snow_depth": [0.6] * count,
            "snow_depth_spread": [0.05] * count,
            "wind_speed_10m": [15.0] * count,
            "wind_gusts_10m": [25.0] * count,
        },
    }


def test_refresh_waits_for_consistency_and_publishes_complete_areas() -> None:
    initialized_at = datetime(2026, 1, 1, tzinfo=UTC)
    cycle = _cycle(initialized_at)
    clock = _Clock(cycle.availability_time + timedelta(minutes=4))
    repository = _Repository()
    client = _Client(
        cycles=(cycle, cycle),
        payloads=(_complete_payload(date(2026, 1, 2)),),
    )

    result = refresh_forecast_source(
        source_key="ecmwf_ifs025_ensemble_mean",
        points=(_point("area-one"),),
        repository=repository,
        client=client,
        clock=clock.now,
        sleep=clock.sleep,
        run_id_factory=lambda: "run-one",
    )

    assert clock.sleeps == [pytest.approx(6 * 60)]
    assert result.status == "complete"
    assert result.published_ski_area_ids == ("area-one",)
    assert result.daily_row_count == 1
    assert repository.created[0].ingested_at == cycle.availability_time + timedelta(
        minutes=10
    )
    assert repository.published == [("run-one", ("area-one",))]


def test_refresh_rejects_run_when_model_cycle_changes() -> None:
    initialized_at = datetime(2026, 1, 1, tzinfo=UTC)
    before = _cycle(initialized_at)
    after = _cycle(initialized_at + timedelta(hours=6))
    clock = _Clock(before.availability_time + timedelta(minutes=20))
    repository = _Repository()
    client = _Client(
        cycles=(before, after),
        payloads=(_complete_payload(date(2026, 1, 2)),),
    )

    result = refresh_forecast_source(
        source_key="ecmwf_ifs025_ensemble_mean",
        points=(_point("area-one"),),
        repository=repository,
        client=client,
        clock=clock.now,
        sleep=clock.sleep,
        run_id_factory=lambda: "run-changed",
    )

    assert result.status == "rejected"
    assert repository.published == []
    assert repository.terminal[0][0:2] == ("run-changed", "rejected")
    assert "changed during acquisition" in repository.terminal[0][2]


def test_refresh_keeps_partial_area_failure_out_of_published_heads() -> None:
    initialized_at = datetime(2026, 1, 1, tzinfo=UTC)
    cycle = _cycle(initialized_at)
    clock = _Clock(cycle.availability_time + timedelta(minutes=20))
    repository = _Repository()
    malformed = _complete_payload(date(2026, 1, 2))
    malformed["hourly"] = {"time": []}
    client = _Client(
        cycles=(cycle, cycle),
        payloads=(_complete_payload(date(2026, 1, 2)), malformed),
    )

    result = refresh_forecast_source(
        source_key="ecmwf_ifs025_ensemble_mean",
        points=(_point("area-one"), _point("area-two")),
        repository=repository,
        client=client,
        clock=clock.now,
        sleep=clock.sleep,
        run_id_factory=lambda: "run-partial",
        batch_size=2,
    )

    assert result.status == "complete"
    assert result.published_ski_area_ids == ("area-one",)
    assert result.failed_ski_area_ids == ("area-two",)
    assert repository.published == [("run-partial", ("area-one",))]


def test_refresh_is_a_safe_no_op_for_an_already_completed_model_issue() -> None:
    initialized_at = datetime(2026, 1, 1, tzinfo=UTC)
    cycle = _cycle(initialized_at)
    clock = _Clock(cycle.availability_time + timedelta(minutes=20))
    repository = _Repository(existing_run_id="existing-run")
    client = _Client(
        cycles=(cycle, cycle),
        payloads=(_complete_payload(date(2026, 1, 2)),),
    )

    result = refresh_forecast_source(
        source_key="ecmwf_ifs025_ensemble_mean",
        points=(_point("area-one"),),
        repository=repository,
        client=client,
        clock=clock.now,
        sleep=clock.sleep,
    )

    assert result.status == "unchanged"
    assert result.run_id == "existing-run"
    assert client.fetch_calls == 0
    assert repository.created == []
    assert repository.lookup_area_ids == [("area-one",)]
