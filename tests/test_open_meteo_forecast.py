from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.integrations.open_meteo_forecast import (
    FORECAST_SOURCES,
    ForecastRequestPoint,
    ModelCycleChangedError,
    OpenMeteoEnsembleMeanClient,
    assert_same_model_cycle,
    normalize_daily_forecast,
    parse_model_cycle_metadata,
)

pytestmark = pytest.mark.db_free


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class _HttpClient:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get(self, url: str, *, params=None, timeout=None) -> _Response:
        self.calls.append((url, params or {}))
        return _Response(self.payload)


def _point() -> ForecastRequestPoint:
    return ForecastRequestPoint(
        ski_area_id="area-one",
        latitude=47.1,
        longitude=11.2,
        elevation_m=2100,
    )


def _local_day_epochs(day: date, timezone_name: str) -> list[int]:
    timezone = ZoneInfo(timezone_name)
    local_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone)
    local_end = datetime.combine(
        day + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone,
    )
    current = local_start.astimezone(UTC)
    end = local_end.astimezone(UTC)
    epochs: list[int] = []
    while current < end:
        epochs.append(int(current.timestamp()))
        current += timedelta(hours=1)
    return epochs


def _payload(
    day: date,
    *,
    timezone_name: str = "Europe/Vienna",
    optional_freezing_level: bool = True,
) -> dict[str, object]:
    epochs = _local_day_epochs(day, timezone_name)
    local_hours = [
        datetime.fromtimestamp(epoch, tz=UTC).astimezone(ZoneInfo(timezone_name)).hour
        for epoch in epochs
    ]
    count = len(epochs)
    hourly: dict[str, list[int | float | None]] = {
        "time": epochs,
        "temperature_2m": [-2.0 if hour < 12 else 1.5 for hour in local_hours],
        "temperature_2m_spread": [1.0] * count,
        "snowfall": [0.5] * count,
        "snowfall_spread": [0.1] * count,
        "rain": [0.25] * count,
        "snow_depth": [0.4 + hour / 100 for hour in local_hours],
        "snow_depth_spread": [0.05] * count,
        "wind_speed_10m": [20.0] * count,
        "wind_gusts_10m": [35.0] * count,
    }
    if optional_freezing_level:
        hourly["freezing_level_height"] = [1800.0] * count
    return {
        "latitude": 47.125,
        "longitude": 11.25,
        "timezone": timezone_name,
        "utc_offset_seconds": 3600,
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
            **({"freezing_level_height": "m"} if optional_freezing_level else {}),
        },
        "hourly": hourly,
    }


def test_source_contract_uses_verified_model_ids_and_capabilities() -> None:
    ecmwf = FORECAST_SOURCES["ecmwf_ifs025_ensemble_mean"]
    gefs = FORECAST_SOURCES["ncep_gefs05_ensemble_mean"]

    assert ecmwf.provider_model_parameter == "ecmwf_ifs025_ensemble_mean"
    assert ecmwf.maximum_lead_days == 15
    assert "freezing_level_height" not in ecmwf.optional_hourly_variables
    assert gefs.provider_model_parameter == "ncep_gefs05_ensemble_mean"
    assert gefs.maximum_lead_days == 30
    assert "freezing_level_height" in gefs.optional_hourly_variables


def test_metadata_parser_uses_provider_cycle_and_availability_timestamps() -> None:
    metadata = parse_model_cycle_metadata(
        "ecmwf_ifs025_ensemble_mean",
        {
            "last_run_initialisation_time": 1_767_225_600,
            "last_run_availability_time": 1_767_250_800,
            "last_run_modification_time": 1_767_250_800,
            "data_end_time": 1_768_521_600,
            "update_interval_seconds": 21_600,
            "temporal_resolution_seconds": 10_800,
        },
    )

    assert metadata.initialization_time == datetime(2026, 1, 1, tzinfo=UTC)
    assert metadata.availability_time == datetime(2026, 1, 1, 7, tzinfo=UTC)
    assert metadata.raw_metadata["temporal_resolution_seconds"] == 10_800


def test_cycle_change_is_rejected() -> None:
    before = parse_model_cycle_metadata(
        "ecmwf_ifs025_ensemble_mean",
        {
            "last_run_initialisation_time": 1_767_225_600,
            "last_run_availability_time": 1_767_250_800,
        },
    )
    after = parse_model_cycle_metadata(
        "ecmwf_ifs025_ensemble_mean",
        {
            "last_run_initialisation_time": 1_767_247_200,
            "last_run_availability_time": 1_767_272_400,
        },
    )

    with pytest.raises(ModelCycleChangedError, match="changed during acquisition"):
        assert_same_model_cycle(before, after)


def test_client_requests_unix_time_and_source_specific_variables() -> None:
    http_client = _HttpClient([_payload(date(2026, 1, 2))])
    client = OpenMeteoEnsembleMeanClient(http_client=http_client)

    payloads = client.fetch_hourly(
        "ecmwf_ifs025_ensemble_mean",
        (_point(),),
    )

    assert len(payloads) == 1
    url, params = http_client.calls[0]
    assert url.endswith("/v1/ensemble")
    assert params["models"] == "ecmwf_ifs025_ensemble_mean"
    assert params["timeformat"] == "unixtime"
    assert params["timezone"] == "auto"
    assert params["forecast_days"] == 16
    assert "freezing_level_height" not in str(params["hourly"])


@pytest.mark.parametrize(
    ("day", "expected_hours"),
    [
        (date(2026, 1, 2), 24),
        (date(2026, 3, 29), 23),
        (date(2026, 10, 25), 25),
    ],
)
def test_daily_normalization_accepts_complete_local_days_across_dst(
    day: date,
    expected_hours: int,
) -> None:
    rows = normalize_daily_forecast(
        run_id="run-one",
        source_key="ncep_gefs05_ensemble_mean",
        point=_point(),
        payload=_payload(day),
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.valid_local_date == day
    assert row.completeness_metadata["expected_hour_count"] == expected_hours
    assert row.completeness_metadata["observed_hour_count"] == expected_hours
    assert row.snow_depth_cm == pytest.approx(52.0)
    assert row.snow_depth_spread_cm == pytest.approx(5.0)
    assert row.snowfall_cm == pytest.approx(expected_hours * 0.5)
    assert row.rain_mm == pytest.approx(expected_hours * 0.25)
    assert row.positive_degree_hours == pytest.approx(
        sum(
            1.5
            for epoch in _local_day_epochs(day, "Europe/Vienna")
            if datetime.fromtimestamp(epoch, tz=UTC)
            .astimezone(ZoneInfo("Europe/Vienna"))
            .hour
            >= 12
        )
    )


def test_incomplete_boundary_day_and_missing_required_value_are_omitted() -> None:
    day = date(2026, 1, 2)
    partial = _payload(day)
    for values in partial["hourly"].values():  # type: ignore[union-attr]
        values.pop()  # type: ignore[union-attr]
    required_missing = _payload(day)
    required_missing["hourly"]["snow_depth"][12] = None  # type: ignore[index]

    assert (
        normalize_daily_forecast(
            run_id="run-one",
            source_key="ncep_gefs05_ensemble_mean",
            point=_point(),
            payload=partial,
        )
        == ()
    )
    assert (
        normalize_daily_forecast(
            run_id="run-one",
            source_key="ncep_gefs05_ensemble_mean",
            point=_point(),
            payload=required_missing,
        )
        == ()
    )


def test_unsupported_optional_field_stays_null_without_invalidating_day() -> None:
    rows = normalize_daily_forecast(
        run_id="run-one",
        source_key="ecmwf_ifs025_ensemble_mean",
        point=_point(),
        payload=_payload(date(2026, 1, 2), optional_freezing_level=False),
    )

    assert len(rows) == 1
    assert rows[0].freezing_level_mean_m is None
    assert rows[0].freezing_level_max_m is None
    assert (
        "freezing_level_height"
        not in rows[0].completeness_metadata["requested_optional_variables"]
    )
