from datetime import UTC, date, datetime, timedelta
from urllib.error import HTTPError

import httpx
import pytest

from app.data.backfill_historical_weather import (
    HistoricalBackfillResult,
    backfill_historical_weather,
)
from app.data.backfill_historical_weather import (
    main as backfill_main,
)
from app.data.catalog_repository import CatalogRepository
from app.data.database import connect
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
)
from app.domain.catalog import SkiArea
from app.domain.models import RawWeatherObservation
from app.integrations.open_meteo import (
    OPEN_METEO_ARCHIVE_URL,
    OpenMeteoClient,
    normalize_open_meteo_conditions,
    weather_elevation_points,
)


def _catalog_ski_area(name: str) -> SkiArea:
    return next(
        area
        for area in CatalogRepository().get_snapshot().ski_areas
        if area.name == name
    )


def _raw_weather_observation(
    *,
    ski_area_id: str,
    resort_name: str,
    observed_on: str,
    elevation_band: str = "mid",
    record_type: str = "archive",
    snow_depth_m: float | None = 1.2,
) -> RawWeatherObservation:
    return RawWeatherObservation(
        ski_area_id=ski_area_id,
        resort_name=resort_name,
        elevation_band=elevation_band,
        elevation_m=2500,
        observed_on=observed_on,
        observed_at=f"{observed_on}T12:00:00+00:00",
        snowfall_cm=8,
        snow_depth_m=snow_depth_m,
        temperature_2m_max_c=-3,
        temperature_2m_min_c=-9,
        wind_speed_10m_max_kmh=18,
        wind_gusts_10m_max_kmh=24,
        weather_code=3,
        record_type=record_type,
        source="open-meteo",
        source_model="best_match",
    )


def test_normalize_open_meteo_maps_strong_snow_signal_to_open() -> None:
    ski_area = _catalog_ski_area("Tignes")

    conditions = normalize_open_meteo_conditions(
        ski_area,
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
    ski_area = _catalog_ski_area("St Anton am Arlberg")

    conditions = normalize_open_meteo_conditions(
        ski_area,
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
    ski_area = _catalog_ski_area("La Plagne")

    conditions = normalize_open_meteo_conditions(
        ski_area,
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
    ski_area = _catalog_ski_area("Tignes")

    conditions = normalize_open_meteo_conditions(
        ski_area,
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

    def fetch_conditions(self, ski_area, *, elevation_m: int | None = None) -> dict:
        if ski_area.name == self.fail_for:
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
                "precipitation_sum": [8],
                "rain_sum": [0],
                "precipitation_hours": [2],
                "snowfall_water_equivalent_sum": [6],
                "apparent_temperature_max": [-5],
                "apparent_temperature_min": [-12],
                "cloud_cover_mean": [35],
                "sunshine_duration": [18000],
                "wind_speed_10m_max": [20],
                "wind_gusts_10m_max": [25],
            },
            "hourly": {
                "time": [
                    "2026-01-15T00:00",
                    "2026-01-15T12:00",
                ],
                "snow_depth": [0.85, 0.9],
                "visibility": [22000, 18000],
            },
        }

    def fetch_historical_weather(
        self,
        ski_area,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
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
                "precipitation_sum": [8 + (index * 2) for index, _ in enumerate(dates)],
                "rain_sum": [index * 0.5 for index, _ in enumerate(dates)],
                "precipitation_hours": [2 + index for index, _ in enumerate(dates)],
                "snowfall_water_equivalent_sum": [
                    6 + index for index, _ in enumerate(dates)
                ],
                "apparent_temperature_max": [
                    -5 - index for index, _ in enumerate(dates)
                ],
                "apparent_temperature_min": [
                    -12 - index for index, _ in enumerate(dates)
                ],
                "cloud_cover_mean": [35 + index for index, _ in enumerate(dates)],
                "sunshine_duration": [
                    18000 - (index * 1000) for index, _ in enumerate(dates)
                ],
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


class FakeHttpxResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FakeHttpxClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict]] = []
        self.closed = False

    def get(self, url: str, *, params: dict, timeout) -> FakeHttpxResponse:
        self.calls.append((url, params))
        return FakeHttpxResponse(self.payload)

    def close(self) -> None:
        self.closed = True


def test_open_meteo_client_reuses_injected_http_client() -> None:
    ski_area = _catalog_ski_area("Tignes")
    fake_http_client = FakeHttpxClient(
        StubClient().fetch_historical_weather(
            ski_area,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            elevation_m=2500,
        )
    )
    client = OpenMeteoClient(http_client=fake_http_client)

    client.fetch_historical_weather(
        ski_area,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        elevation_m=2500,
    )
    client.fetch_historical_weather(
        ski_area,
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 2),
        elevation_m=2500,
    )
    client.close()

    assert len(fake_http_client.calls) == 2
    assert fake_http_client.calls[0][0] == OPEN_METEO_ARCHIVE_URL
    assert fake_http_client.calls[0][1]["elevation"] == 2500
    assert fake_http_client.calls[1][0] == OPEN_METEO_ARCHIVE_URL
    assert fake_http_client.closed is False


class FlakyClient(StubClient):
    def __init__(self, *, fail_once_for: str) -> None:
        super().__init__()
        self.fail_once_for = fail_once_for
        self.calls: dict[str, int] = {}

    def fetch_conditions(self, ski_area, *, elevation_m: int | None = None) -> dict:
        self.calls[ski_area.name] = self.calls.get(ski_area.name, 0) + 1
        if ski_area.name == self.fail_once_for and self.calls[ski_area.name] == 1:
            raise RuntimeError("temporary provider failure")
        return super().fetch_conditions(ski_area, elevation_m=elevation_m)


class FlakyHistoricalClient(StubClient):
    def __init__(self, *, fail_once_for: str) -> None:
        super().__init__()
        self.fail_once_for = fail_once_for
        self.calls: dict[tuple[str, str, str], int] = {}

    def fetch_historical_weather(
        self,
        ski_area,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
    ) -> dict:
        key = (ski_area.name, start_date.isoformat(), end_date.isoformat())
        self.calls[key] = self.calls.get(key, 0) + 1
        if ski_area.name == self.fail_once_for and self.calls[key] == 1:
            raise RuntimeError("temporary archive timeout")
        return super().fetch_historical_weather(
            ski_area,
            start_date=start_date,
            end_date=end_date,
            elevation_m=elevation_m,
        )


class FailingHistoricalClient(StubClient):
    def __init__(self, *, fail_for: str) -> None:
        super().__init__()
        self.fail_for = fail_for

    def fetch_historical_weather(
        self,
        ski_area,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
    ) -> dict:
        if ski_area.name == self.fail_for:
            raise RuntimeError("archive handshake timeout")
        return super().fetch_historical_weather(
            ski_area,
            start_date=start_date,
            end_date=end_date,
            elevation_m=elevation_m,
        )


class RateLimitedHistoricalClient(StubClient):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def fetch_historical_weather(
        self,
        ski_area,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
    ) -> dict:
        self.calls += 1
        raise HTTPError(
            url="https://archive-api.open-meteo.com/v1/archive",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=None,
        )


class RetryAfterHistoricalClient(StubClient):
    def __init__(self) -> None:
        super().__init__()
        self.calls: dict[tuple[str, int | None], int] = {}

    def fetch_historical_weather(
        self,
        ski_area,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
    ) -> dict:
        key = (ski_area.name, elevation_m)
        self.calls[key] = self.calls.get(key, 0) + 1
        if self.calls[key] == 1:
            raise HTTPError(
                url="https://archive-api.open-meteo.com/v1/archive",
                code=429,
                msg="Too Many Requests",
                hdrs={"Retry-After": "12"},
                fp=None,
            )
        return super().fetch_historical_weather(
            ski_area,
            start_date=start_date,
            end_date=end_date,
            elevation_m=elevation_m,
        )


class HttpxRateLimitedHistoricalClient(StubClient):
    def __init__(self, *, retry_after: str | None = None) -> None:
        super().__init__()
        self.calls = 0
        self.retry_after = retry_after

    def fetch_historical_weather(
        self,
        ski_area,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
    ) -> dict:
        self.calls += 1
        request = httpx.Request("GET", OPEN_METEO_ARCHIVE_URL)
        response = httpx.Response(
            429,
            request=request,
            headers=(
                {"Retry-After": self.retry_after}
                if self.retry_after is not None
                else {}
            ),
        )
        raise httpx.HTTPStatusError(
            "Too Many Requests",
            request=request,
            response=response,
        )


class TimeoutThenSuccessHistoricalClient(StubClient):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def fetch_historical_weather(
        self,
        ski_area,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
    ) -> dict:
        self.calls += 1
        if self.calls in {1, 3, 5}:
            request = httpx.Request("GET", OPEN_METEO_ARCHIVE_URL)
            raise httpx.ConnectTimeout(
                "The handshake operation timed out",
                request=request,
            )
        return super().fetch_historical_weather(
            ski_area,
            start_date=start_date,
            end_date=end_date,
            elevation_m=elevation_m,
        )


class CountingHistoricalClient(StubClient):
    def __init__(self) -> None:
        super().__init__()
        self.calls: dict[tuple[str, str, str], int] = {}

    def fetch_historical_weather(
        self,
        ski_area,
        *,
        start_date: date,
        end_date: date,
        elevation_m: int | None = None,
    ) -> dict:
        key = (ski_area.name, start_date.isoformat(), end_date.isoformat())
        self.calls[key] = self.calls.get(key, 0) + 1
        return super().fetch_historical_weather(
            ski_area,
            start_date=start_date,
            end_date=end_date,
            elevation_m=elevation_m,
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
    snapshots = history_repository.list_snapshots_for_ski_area("tignes-ski-area")
    raw_observations = raw_history_repository.list_observations_for_ski_area(
        "tignes-ski-area"
    )

    assert result.refreshed > 0
    assert result.failed == 0
    assert conditions is not None
    assert conditions.updated_at == "2026-01-15T00:00:00+00:00"
    assert conditions.source == "open-meteo"
    assert len(snapshots) == 1
    assert snapshots[0].observed_month == 1
    assert len(raw_observations) == 3
    assert {observation.elevation_band for observation in raw_observations} == {
        "base",
        "mid",
        "upper",
    }
    mid_observation = next(
        observation
        for observation in raw_observations
        if observation.elevation_band == "mid"
    )
    assert mid_observation.observed_on == "2026-01-15"
    assert mid_observation.snow_depth_m == pytest.approx(0.875)
    assert mid_observation.record_type == "forecast"
    assert mid_observation.precipitation_sum_mm == pytest.approx(8.0)
    assert mid_observation.rain_sum_mm == pytest.approx(0.0)
    assert mid_observation.precipitation_hours == pytest.approx(2.0)
    assert mid_observation.snowfall_water_equivalent_sum_mm == pytest.approx(6.0)
    assert mid_observation.apparent_temperature_2m_max_c == pytest.approx(-5.0)
    assert mid_observation.apparent_temperature_2m_min_c == pytest.approx(-12.0)
    assert mid_observation.cloud_cover_mean_pct == pytest.approx(35.0)
    assert mid_observation.sunshine_duration_seconds == pytest.approx(18000.0)
    assert mid_observation.visibility_min_m == pytest.approx(18000.0)


def test_weather_elevation_points_are_deterministic() -> None:
    ski_area = _catalog_ski_area("Cervinia")

    points = weather_elevation_points(ski_area)

    assert points[0].band == "base"
    assert points[0].elevation_m == ski_area.base_elevation_m
    assert points[1].band == "mid"
    assert points[1].elevation_m == round(
        (ski_area.base_elevation_m + ski_area.summit_elevation_m) / 2
    )
    assert points[2].band == "upper"
    assert points[2].elevation_m == round(
        ski_area.base_elevation_m
        + 0.9 * (ski_area.summit_elevation_m - ski_area.base_elevation_m)
    )


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

    snapshots = ResortConditionHistoryRepository().list_snapshots_for_ski_area(
        "tignes-ski-area"
    )

    assert len(snapshots) == 2
    assert snapshots[0].observed_at == "2026-01-15T00:00:00+00:00"
    assert snapshots[1].observed_at == "2026-01-16T00:00:00+00:00"


def test_backfill_historical_weather_stores_daily_raw_rows_idempotently() -> None:
    result = backfill_historical_weather(
        client=StubClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes",),
        chunk_days=2,
    )
    rerun = backfill_historical_weather(
        client=StubClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes",),
        chunk_days=1,
    )

    observations = RawWeatherHistoryRepository().list_observations_for_ski_area(
        "tignes-ski-area"
    )

    assert result.targeted_ski_areas == 1
    assert result.requested_chunks == 3
    assert result.inserted_or_updated == 6
    assert rerun.requested_chunks == 6
    assert len(observations) == 6
    mid_observations = tuple(
        observation
        for observation in observations
        if observation.elevation_band == "mid"
    )
    assert mid_observations[0].snow_depth_m == pytest.approx(0.75)
    assert mid_observations[1].snow_depth_m == pytest.approx(0.95)
    assert mid_observations[0].precipitation_sum_mm == pytest.approx(8.0)
    assert mid_observations[1].precipitation_sum_mm == pytest.approx(10.0)
    assert mid_observations[0].rain_sum_mm == pytest.approx(0.0)
    assert mid_observations[1].rain_sum_mm == pytest.approx(0.5)
    assert mid_observations[0].precipitation_hours == pytest.approx(2.0)
    assert mid_observations[1].precipitation_hours == pytest.approx(3.0)
    assert mid_observations[0].snowfall_water_equivalent_sum_mm == pytest.approx(6.0)
    assert mid_observations[1].snowfall_water_equivalent_sum_mm == pytest.approx(7.0)
    assert mid_observations[0].apparent_temperature_2m_max_c == pytest.approx(-5.0)
    assert mid_observations[1].apparent_temperature_2m_max_c == pytest.approx(-6.0)
    assert mid_observations[0].apparent_temperature_2m_min_c == pytest.approx(-12.0)
    assert mid_observations[1].apparent_temperature_2m_min_c == pytest.approx(-13.0)
    assert mid_observations[0].cloud_cover_mean_pct == pytest.approx(35.0)
    assert mid_observations[1].cloud_cover_mean_pct == pytest.approx(36.0)
    assert mid_observations[0].sunshine_duration_seconds == pytest.approx(18000.0)
    assert mid_observations[1].sunshine_duration_seconds == pytest.approx(17000.0)
    assert all(observation.visibility_min_m is None for observation in mid_observations)
    assert {observation.elevation_m for observation in observations}
    assert all(observation.record_type == "archive" for observation in observations)


def test_backfill_historical_weather_counts_chunks_across_all_targets() -> None:
    result = backfill_historical_weather(
        client=StubClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        stay_destination_ids=("tignes", "la-plagne"),
        chunk_days=1,
    )

    assert result.targeted_ski_areas == 2
    assert result.requested_chunks == 6


def test_raw_weather_history_repository_detects_complete_archive_coverage() -> None:
    backfill_historical_weather(
        client=StubClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes",),
        chunk_days=2,
    )

    repository = RawWeatherHistoryRepository()

    assert repository.has_complete_archive_coverage(
        ski_area_id="tignes-ski-area",
        elevation_band="mid",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
    )
    assert not repository.has_complete_archive_coverage(
        ski_area_id="tignes-ski-area",
        elevation_band="mid",
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
        ski_area_id="tignes-ski-area",
        elevation_band="mid",
        start_date=date(2026, 1, 15),
        end_date=date(2026, 1, 15),
    )


def test_raw_weather_history_repository_lists_only_month_window_rows() -> None:
    ski_area = _catalog_ski_area("Tignes")
    repository = RawWeatherHistoryRepository()
    for observation in (
        _raw_weather_observation(
            ski_area_id=ski_area.ski_area_id,
            resort_name=ski_area.name,
            observed_on="2024-03-05",
        ),
        _raw_weather_observation(
            ski_area_id=ski_area.ski_area_id,
            resort_name=ski_area.name,
            observed_on="2025-03-08",
        ),
        _raw_weather_observation(
            ski_area_id=ski_area.ski_area_id,
            resort_name=ski_area.name,
            observed_on="2025-04-08",
        ),
        _raw_weather_observation(
            ski_area_id=ski_area.ski_area_id,
            resort_name=ski_area.name,
            observed_on="2025-03-08",
            elevation_band="upper",
        ),
        _raw_weather_observation(
            ski_area_id=ski_area.ski_area_id,
            resort_name=ski_area.name,
            observed_on="2026-03-08",
            record_type="forecast",
        ),
    ):
        repository.upsert_observation(observation)

    grouped = repository.list_archive_observations_for_ski_areas_window(
        (ski_area.ski_area_id,),
        elevation_bands=("mid",),
        travel_month=3,
    )

    observations = grouped[(ski_area.ski_area_id, "mid")]
    assert [observation.observed_on for observation in observations] == [
        "2024-03-05",
        "2025-03-08",
    ]
    assert all(observation.elevation_band == "mid" for observation in observations)
    assert all(observation.record_type == "archive" for observation in observations)


def test_raw_weather_history_repository_lists_only_exact_date_window_rows() -> None:
    ski_area = _catalog_ski_area("Tignes")
    repository = RawWeatherHistoryRepository()
    for observation in (
        _raw_weather_observation(
            ski_area_id=ski_area.ski_area_id,
            resort_name=ski_area.name,
            observed_on="2024-03-09",
        ),
        _raw_weather_observation(
            ski_area_id=ski_area.ski_area_id,
            resort_name=ski_area.name,
            observed_on="2024-03-12",
        ),
        _raw_weather_observation(
            ski_area_id=ski_area.ski_area_id,
            resort_name=ski_area.name,
            observed_on="2024-03-13",
        ),
        _raw_weather_observation(
            ski_area_id=ski_area.ski_area_id,
            resort_name=ski_area.name,
            observed_on="2025-03-10",
        ),
    ):
        repository.upsert_observation(observation)

    grouped = repository.list_archive_observations_for_ski_areas_window(
        (ski_area.ski_area_id,),
        elevation_bands=("mid",),
        trip_start_date=date(2026, 3, 9),
        trip_end_date=date(2026, 3, 12),
    )

    observations = grouped[(ski_area.ski_area_id, "mid")]
    assert [observation.observed_on for observation in observations] == [
        "2024-03-09",
        "2024-03-12",
        "2025-03-10",
    ]


def test_raw_weather_history_schema_includes_search_window_index() -> None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'raw_weather_history'
              AND indexname = 'raw_weather_history_search_window_idx'
            """
        ).fetchone()

    assert row is not None


def test_backfill_historical_weather_skips_complete_archive_chunks() -> None:
    client = CountingHistoricalClient()

    initial = backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes",),
        chunk_days=2,
    )
    rerun = backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes",),
        chunk_days=2,
    )

    assert initial.skipped_chunks == 0
    assert rerun.skipped_chunks == 3
    assert rerun.inserted_or_updated == 0
    assert client.calls[("Tignes", "2024-01-01", "2024-01-02")] == 3


def test_backfill_historical_weather_stops_at_provider_request_budget() -> None:
    client = CountingHistoricalClient()

    partial = backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        stay_destination_ids=("tignes",),
        chunk_days=1,
        retry_attempts=0,
        max_provider_requests=2,
    )
    resumed = backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        stay_destination_ids=("tignes",),
        chunk_days=1,
        retry_attempts=0,
        max_provider_requests=2,
    )

    assert partial.attempted_provider_requests == 2
    assert partial.provider_request_budget_exhausted is True
    assert partial.inserted_or_updated == 2
    assert resumed.attempted_provider_requests == 1
    assert resumed.provider_request_budget_exhausted is False
    assert resumed.skipped_chunks == 2
    assert (
        len(
            RawWeatherHistoryRepository().list_observations_for_ski_area(
                "tignes-ski-area"
            )
        )
        == 3
    )


def test_backfill_historical_weather_force_refetch_bypasses_skip() -> None:
    client = CountingHistoricalClient()

    backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes",),
        chunk_days=2,
    )
    rerun = backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes",),
        chunk_days=2,
        force_refetch=True,
    )

    assert rerun.skipped_chunks == 0
    assert rerun.inserted_or_updated == 6
    assert client.calls[("Tignes", "2024-01-01", "2024-01-02")] == 6


def test_backfill_historical_weather_rebuild_deletes_selected_archive_rows() -> None:
    repository = RawWeatherHistoryRepository()
    backfill_historical_weather(
        client=StubClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes",),
        chunk_days=2,
    )
    before = repository.list_observations_for_ski_area("tignes-ski-area")

    result = backfill_historical_weather(
        client=StubClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes",),
        chunk_days=2,
        rebuild=True,
    )
    after = repository.list_observations_for_ski_area("tignes-ski-area")

    assert len(before) == 6
    assert result.skipped_chunks == 0
    assert result.inserted_or_updated == 6
    assert len(after) == 6


def test_recent_archive_reconciliation_overwrites_forecast_rows_with_archive() -> None:
    refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        force=True,
        stay_destination_ids=("tignes",),
    )

    before = RawWeatherHistoryRepository().list_observations_for_ski_area(
        "tignes-ski-area"
    )
    assert len(before) == 3
    assert {observation.record_type for observation in before} == {"forecast"}

    result = reconcile_recent_archive(
        lookback_days=1,
        end_date=date(2026, 1, 15),
        stay_destination_ids=("tignes",),
    )
    after = RawWeatherHistoryRepository().list_observations_for_ski_area(
        "tignes-ski-area"
    )

    assert result.backfill_result.failed_chunks == 0
    assert result.backfill_result.inserted_or_updated == 3
    assert {observation.record_type for observation in after} == {"archive"}


def test_recent_archive_reconciliation_is_idempotent() -> None:
    reconcile_recent_archive(
        lookback_days=1,
        end_date=date(2026, 1, 15),
        stay_destination_ids=("tignes",),
    )
    rerun = reconcile_recent_archive(
        lookback_days=1,
        end_date=date(2026, 1, 15),
        stay_destination_ids=("tignes",),
    )

    observations = RawWeatherHistoryRepository().list_observations_for_ski_area(
        "tignes-ski-area"
    )

    assert rerun.backfill_result.failed_chunks == 0
    assert len(observations) == 3
    assert {observation.record_type for observation in observations} == {"archive"}


def test_backfill_historical_weather_retries_and_succeeds() -> None:
    result = backfill_historical_weather(
        client=FlakyHistoricalClient(fail_once_for="Tignes"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes",),
        chunk_days=2,
        retry_attempts=1,
        backoff_seconds=0,
        provider_pressure_error_threshold=0,
    )

    observations = RawWeatherHistoryRepository().list_observations_for_ski_area(
        "tignes-ski-area"
    )

    assert result.failed_chunks == 0
    assert result.inserted_or_updated == 6
    assert len(observations) == 6


def test_backfill_historical_weather_records_failed_chunks_and_continues() -> None:
    result = backfill_historical_weather(
        client=FailingHistoricalClient(fail_for="Tignes"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes", "cervinia"),
        chunk_days=2,
        retry_attempts=1,
        backoff_seconds=0,
        provider_pressure_error_threshold=0,
    )

    tignes = RawWeatherHistoryRepository().list_observations_for_ski_area(
        "tignes-ski-area"
    )
    cervinia = RawWeatherHistoryRepository().list_observations_for_ski_area(
        "cervinia-ski-area"
    )

    assert result.failed_chunks == 3
    assert len(result.failures) == 3
    assert result.failures[0].resort_name == "Tignes"
    assert tignes == ()
    assert len(cervinia) == 6


def test_backfill_historical_weather_aborts_after_provider_rate_limit(
    monkeypatch,
) -> None:
    sleep_delays: list[float] = []
    client = RateLimitedHistoricalClient()
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.time.sleep",
        lambda seconds: sleep_delays.append(seconds),
    )

    result = backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        stay_destination_ids=("tignes", "cervinia"),
        chunk_days=2,
        retry_attempts=1,
        backoff_seconds=30,
        retry_jitter_ratio=0,
    )

    tignes = RawWeatherHistoryRepository().list_observations_for_ski_area(
        "tignes-ski-area"
    )
    cervinia = RawWeatherHistoryRepository().list_observations_for_ski_area(
        "cervinia-ski-area"
    )

    assert result.failed_chunks == 1
    assert result.rate_limited is True
    assert result.attempted_provider_requests == 2
    assert len(result.failures) == 1
    assert result.failures[0].is_rate_limited is True
    assert result.failures[0].elevation_band == "base"
    assert client.calls == 2
    assert sleep_delays == [30]
    assert tignes == ()
    assert cervinia == ()


def test_backfill_budget_does_not_hide_rate_limit_on_last_attempt() -> None:
    client = RateLimitedHistoricalClient()

    result = backfill_historical_weather(
        client=client,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        stay_destination_ids=("tignes",),
        chunk_days=1,
        retry_attempts=1,
        max_provider_requests=1,
        backoff_seconds=0,
    )

    assert client.calls == 1
    assert result.attempted_provider_requests == 1
    assert result.provider_request_budget_exhausted is True
    assert result.rate_limited is True
    assert result.failed_chunks == 1
    assert result.failures[0].is_rate_limited is True


def test_backfill_historical_weather_honors_retry_after_header(monkeypatch) -> None:
    sleep_delays: list[float] = []
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.time.sleep",
        lambda seconds: sleep_delays.append(seconds),
    )

    result = backfill_historical_weather(
        client=RetryAfterHistoricalClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        stay_destination_ids=("tignes",),
        chunk_days=1,
        retry_attempts=1,
        backoff_seconds=1,
        retry_jitter_ratio=0,
    )

    observations = RawWeatherHistoryRepository().list_observations_for_ski_area(
        "tignes-ski-area"
    )

    assert result.failed_chunks == 0
    assert result.inserted_or_updated == 3
    assert len(observations) == 3
    assert sleep_delays == [12, 12, 12]


def test_backfill_historical_weather_aborts_after_httpx_rate_limit(
    monkeypatch,
) -> None:
    sleep_delays: list[float] = []
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.time.sleep",
        lambda seconds: sleep_delays.append(seconds),
    )

    result = backfill_historical_weather(
        client=HttpxRateLimitedHistoricalClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        stay_destination_ids=("tignes", "cervinia"),
        chunk_days=1,
        retry_attempts=1,
        backoff_seconds=30,
        retry_jitter_ratio=0,
    )

    assert result.failed_chunks == 1
    assert result.failures[0].elevation_band == "base"
    assert sleep_delays == [30]


def test_backfill_historical_weather_honors_httpx_retry_after_header(
    monkeypatch,
) -> None:
    sleep_delays: list[float] = []
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.time.sleep",
        lambda seconds: sleep_delays.append(seconds),
    )

    result = backfill_historical_weather(
        client=HttpxRateLimitedHistoricalClient(retry_after="12"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        stay_destination_ids=("tignes",),
        chunk_days=1,
        retry_attempts=1,
        backoff_seconds=1,
        retry_jitter_ratio=0,
    )

    assert result.failed_chunks == 1
    assert sleep_delays == [12]


def test_jittered_delay_applies_fractional_spread(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.random.uniform",
        lambda lower, upper: upper,
    )

    from app.data.backfill_historical_weather import _jittered_delay_seconds

    assert _jittered_delay_seconds(10, jitter_ratio=0.25) == 12.5


def test_jittered_delay_can_be_disabled() -> None:
    from app.data.backfill_historical_weather import _jittered_delay_seconds

    assert _jittered_delay_seconds(10, jitter_ratio=0) == 10


def test_backfill_historical_weather_can_throttle_successful_requests(
    monkeypatch,
) -> None:
    sleep_delays: list[float] = []
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.time.sleep",
        lambda seconds: sleep_delays.append(seconds),
    )

    result = backfill_historical_weather(
        client=StubClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        stay_destination_ids=("tignes",),
        chunk_days=1,
        retry_attempts=0,
        request_delay_seconds=2,
        request_jitter_ratio=0,
    )

    assert result.failed_chunks == 0
    assert result.inserted_or_updated == 3
    assert sleep_delays == [2, 2, 2]


def test_backfill_historical_weather_cools_down_after_repeated_timeouts(
    monkeypatch,
) -> None:
    sleep_delays: list[float] = []
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.time.sleep",
        lambda seconds: sleep_delays.append(seconds),
    )
    monkeypatch.setattr(
        "app.data.backfill_historical_weather.random.uniform",
        lambda lower, upper: lower,
    )

    result = backfill_historical_weather(
        client=TimeoutThenSuccessHistoricalClient(),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        stay_destination_ids=("tignes",),
        chunk_days=1,
        retry_attempts=1,
        backoff_seconds=10,
        retry_jitter_ratio=0,
        provider_pressure_error_threshold=3,
        provider_pressure_cooldown_seconds=300,
    )

    assert result.failed_chunks == 0
    assert result.inserted_or_updated == 3
    assert 300 in sleep_delays


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
            "--stay-destination",
            "tignes",
        ],
    )

    backfill_main()

    output = capsys.readouterr().out
    assert "Selected stay destinations: tignes" in output
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
                            "elevation_band": "mid",
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


def test_backfill_command_main_supports_force_refetch_and_rebuild(monkeypatch) -> None:
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
            "--ski-area",
            "tignes-ski-area",
            "--force-refetch",
            "--rebuild",
        ],
    )

    backfill_main()

    assert captured["ski_area_ids"] == ("tignes-ski-area",)
    assert captured["stay_destination_ids"] == ()
    assert captured["chunk_days"] == 90
    assert captured["force_refetch"] is True
    assert captured["rebuild"] is True


@pytest.mark.db_free
def test_backfill_command_main_forwards_campiglio_workflow_arguments(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def _stub_backfill(**kwargs):
        captured.update(kwargs)
        return HistoricalBackfillResult(targeted_ski_areas=2)

    monkeypatch.setattr(
        "app.data.backfill_historical_weather.backfill_historical_weather",
        _stub_backfill,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "backfill_historical_weather",
            "--database-url",
            "postgresql://unused",
            "--start-date",
            "1991-01-01",
            "--end-date",
            "2026-06-29",
            "--chunk-days",
            "365",
            # The workflow comma-expands stay_destination_ids into repeated options.
            "--stay-destination",
            "pinzolo",
            "--stay-destination",
            "folgarida-marilleva",
            "--force-refetch",
            "--rebuild",
        ],
    )

    backfill_main()

    assert captured["start_date"] == date(1991, 1, 1)
    assert captured["end_date"] == date(2026, 6, 29)
    assert captured["stay_destination_ids"] == ("pinzolo", "folgarida-marilleva")
    assert captured["force_refetch"] is True
    assert captured["rebuild"] is True


@pytest.mark.db_free
def test_backfill_command_main_preserves_campiglio_archive_window(
    monkeypatch,
) -> None:
    fixed_utc_run_date = date(2026, 6, 30)
    latest_existing_madonna_archive_date = date(2026, 6, 28)
    archive_end_date = fixed_utc_run_date - timedelta(days=1)
    captured_calls: list[dict[str, object]] = []

    def _stub_backfill(**kwargs):
        captured_calls.append(kwargs)
        return HistoricalBackfillResult(
            targeted_ski_areas=len(kwargs["stay_destination_ids"])
        )

    monkeypatch.setattr(
        "app.data.backfill_historical_weather.backfill_historical_weather",
        _stub_backfill,
    )

    def _run_cli(*targets: str, force_refetch: bool = False) -> None:
        argv = [
            "backfill_historical_weather",
            "--database-url",
            "postgresql://unused",
            "--start-date",
            "1991-01-01",
            "--end-date",
            archive_end_date.isoformat(),
        ]
        for target in targets:
            argv.extend(("--stay-destination", target))
        if force_refetch:
            argv.append("--force-refetch")
        monkeypatch.setattr("sys.argv", argv)
        backfill_main()

    # Capability only: material_change=false means this PR does not dispatch Madonna.
    _run_cli("madonna-di-campiglio", force_refetch=True)
    _run_cli("pinzolo", "folgarida-marilleva")

    assert archive_end_date.year == fixed_utc_run_date.year
    assert archive_end_date.year > 2025
    assert archive_end_date >= latest_existing_madonna_archive_date
    assert [call["end_date"] for call in captured_calls] == [
        archive_end_date,
        archive_end_date,
    ]
    assert captured_calls[0]["stay_destination_ids"] == ("madonna-di-campiglio",)
    assert captured_calls[0]["force_refetch"] is True
    assert captured_calls[0]["rebuild"] is False
    assert captured_calls[1]["stay_destination_ids"] == (
        "pinzolo",
        "folgarida-marilleva",
    )
    assert captured_calls[1]["force_refetch"] is False
    assert captured_calls[1]["rebuild"] is False


def test_reconcile_recent_archive_main_logs_summary(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def _stub_reconcile(**kwargs):
        captured.update(kwargs)
        return type(
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
        )()

    monkeypatch.setattr(
        "app.data.reconcile_recent_archive.reconcile_recent_archive",
        _stub_reconcile,
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "reconcile_recent_archive",
            "--lookback-days",
            "7",
            "--stay-destination",
            "tignes",
            "--ski-area",
            "tignes-ski-area",
        ],
    )

    reconcile_recent_archive_main()

    output = capsys.readouterr().out
    assert captured["ski_area_ids"] == ("tignes-ski-area",)
    assert captured["stay_destination_ids"] == ("tignes",)
    assert "Selected stay destinations: tignes" in output
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


def test_refresh_conditions_targets_single_stay_destination_by_id() -> None:
    result = refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        stay_destination_ids=("tignes",),
    )

    repository = ResortConditionsRepository()

    assert result.refreshed == 1
    assert repository.get_conditions_for_resort("Tignes") is not None
    assert repository.get_conditions_for_resort("Chamonix Mont-Blanc") is None


def test_refresh_conditions_targets_single_ski_area_by_id() -> None:
    result = refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        ski_area_ids=("st-anton-am-arlberg-ski-area",),
    )

    repository = ResortConditionsRepository()

    assert result.refreshed == 1
    assert repository.get_conditions_for_resort("St Anton am Arlberg") is not None
    assert repository.get_conditions_for_resort("Tignes") is None


def test_refresh_conditions_force_and_targets_refresh_selected_fresh_row() -> None:
    refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, tzinfo=UTC),
        stay_destination_ids=("tignes",),
    )

    result = refresh_conditions(
        client=StubClient(),
        now=datetime(2026, 1, 15, 12, tzinfo=UTC),
        force=True,
        stay_destination_ids=("tignes",),
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
    with pytest.raises(
        ValueError,
        match=r"unknown catalog targets: areas=\[\], "
        r"stay_destinations=\['not-a-destination'\]",
    ):
        refresh_conditions(
            client=StubClient(),
            now=datetime(2026, 1, 15, tzinfo=UTC),
            stay_destination_ids=("not-a-destination",),
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
        ["refresh_conditions", "--stay-destination", "not-a-destination"],
    )

    with pytest.raises(SystemExit) as error:
        refresh_main()

    output = capsys.readouterr().out
    assert error.value.code == 1
    assert "unknown catalog targets" in output


def test_refresh_command_main_supports_force_and_target(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_conditions",
            "--database-url",
            "postgresql://planner:planner@127.0.0.1:5432/ai_sports_travel_planner_test",
            "--force",
            "--ski-area",
            "tignes-ski-area",
        ],
    )

    refresh_main()

    output = capsys.readouterr().out
    assert "Selected ski areas: tignes-ski-area" in output
    assert "refreshed=1" in output
