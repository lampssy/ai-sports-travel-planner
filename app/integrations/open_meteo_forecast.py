from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.domain.weather_forecast import WeatherElevationBand, WeatherForecastDaily

OPEN_METEO_ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
OPEN_METEO_FORECAST_TIMEOUT = httpx.Timeout(
    connect=15.0,
    read=90.0,
    write=10.0,
    pool=15.0,
)
OPEN_METEO_FORECAST_LIMITS = httpx.Limits(
    max_connections=4,
    max_keepalive_connections=2,
    keepalive_expiry=60.0,
)
OPEN_METEO_FORECAST_USER_AGENT = "snowcast-ensemble-forecast/0.1"

_REQUIRED_HOURLY_VARIABLES = (
    "temperature_2m",
    "snowfall",
    "rain",
    "snow_depth",
)
_COMMON_OPTIONAL_HOURLY_VARIABLES = (
    "temperature_2m_spread",
    "snowfall_spread",
    "snow_depth_spread",
    "wind_speed_10m",
    "wind_gusts_10m",
)
_EXPECTED_UNITS = {
    "temperature_2m": "°C",
    "temperature_2m_spread": "K",
    "snowfall": "cm",
    "snowfall_spread": "cm",
    "rain": "mm",
    "snow_depth": "m",
    "snow_depth_spread": "m",
    "wind_speed_10m": "km/h",
    "wind_gusts_10m": "km/h",
    "freezing_level_height": "m",
}


class ForecastProviderError(ValueError):
    pass


class ForecastProviderPayloadError(ForecastProviderError):
    pass


class ModelCycleChangedError(ForecastProviderError):
    pass


@dataclass(frozen=True)
class ForecastSourceConfig:
    source_key: str
    producer: str
    provider_model_id: str
    provider_model_parameter: str
    metadata_url: str
    maximum_lead_days: int
    required_hourly_variables: tuple[str, ...]
    optional_hourly_variables: tuple[str, ...]

    @property
    def forecast_days(self) -> int:
        return self.maximum_lead_days + 1

    @property
    def requested_hourly_variables(self) -> tuple[str, ...]:
        return self.required_hourly_variables + self.optional_hourly_variables


FORECAST_SOURCES: Mapping[str, ForecastSourceConfig] = {
    "ecmwf_ifs025_ensemble_mean": ForecastSourceConfig(
        source_key="ecmwf_ifs025_ensemble_mean",
        producer="ecmwf",
        provider_model_id="ifs025-ensemble-mean",
        provider_model_parameter="ecmwf_ifs025_ensemble_mean",
        metadata_url=(
            "https://ensemble-api.open-meteo.com/data/"
            "ecmwf_ifs025_ensemble/static/meta.json"
        ),
        maximum_lead_days=15,
        required_hourly_variables=_REQUIRED_HOURLY_VARIABLES,
        optional_hourly_variables=_COMMON_OPTIONAL_HOURLY_VARIABLES,
    ),
    "ncep_gefs05_ensemble_mean": ForecastSourceConfig(
        source_key="ncep_gefs05_ensemble_mean",
        producer="noaa-ncep",
        provider_model_id="gefs05-ensemble-mean",
        provider_model_parameter="ncep_gefs05_ensemble_mean",
        metadata_url=(
            "https://ensemble-api.open-meteo.com/data/ncep_gefs05/static/meta.json"
        ),
        maximum_lead_days=30,
        required_hourly_variables=_REQUIRED_HOURLY_VARIABLES,
        optional_hourly_variables=(
            *_COMMON_OPTIONAL_HOURLY_VARIABLES,
            "freezing_level_height",
        ),
    ),
}


@dataclass(frozen=True)
class ForecastRequestPoint:
    ski_area_id: str
    latitude: float
    longitude: float
    elevation_m: int
    elevation_band: WeatherElevationBand = "mid"

    def __post_init__(self) -> None:
        if not self.ski_area_id.strip():
            raise ValueError("ski_area_id must not be blank")
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        if self.elevation_m < 0:
            raise ValueError("elevation_m cannot be negative")


@dataclass(frozen=True)
class ModelCycleMetadata:
    source_key: str
    initialization_time: datetime
    availability_time: datetime
    raw_metadata: Mapping[str, int | float | str | None]


class OpenMeteoEnsembleMeanClient:
    def __init__(self, http_client: Any | None = None) -> None:
        self._http_client = http_client or httpx.Client(
            timeout=OPEN_METEO_FORECAST_TIMEOUT,
            limits=OPEN_METEO_FORECAST_LIMITS,
            headers={"User-Agent": OPEN_METEO_FORECAST_USER_AGENT},
        )
        self._owns_http_client = http_client is None

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def __enter__(self) -> OpenMeteoEnsembleMeanClient:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def fetch_model_cycle(self, source_key: str) -> ModelCycleMetadata:
        source = _source_config(source_key)
        response = self._http_client.get(
            source.metadata_url,
            params={},
            timeout=OPEN_METEO_FORECAST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ForecastProviderPayloadError(
                "Open-Meteo model metadata must be a JSON object"
            )
        return parse_model_cycle_metadata(source_key, payload)

    def fetch_hourly(
        self,
        source_key: str,
        points: Sequence[ForecastRequestPoint],
    ) -> tuple[dict[str, Any], ...]:
        source = _source_config(source_key)
        if not points:
            return ()
        response = self._http_client.get(
            OPEN_METEO_ENSEMBLE_URL,
            params={
                "latitude": ",".join(str(point.latitude) for point in points),
                "longitude": ",".join(str(point.longitude) for point in points),
                "elevation": ",".join(str(point.elevation_m) for point in points),
                "timezone": "auto",
                "timeformat": "unixtime",
                "forecast_days": source.forecast_days,
                "models": source.provider_model_parameter,
                "hourly": ",".join(source.requested_hourly_variables),
            },
            timeout=OPEN_METEO_FORECAST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        raw_payloads = payload if isinstance(payload, list) else [payload]
        if len(raw_payloads) != len(points) or not all(
            isinstance(item, dict) for item in raw_payloads
        ):
            raise ForecastProviderPayloadError(
                "Open-Meteo response count must match request point count"
            )
        return tuple(raw_payloads)


def parse_model_cycle_metadata(
    source_key: str,
    payload: Mapping[str, object],
) -> ModelCycleMetadata:
    _source_config(source_key)
    initialization_epoch = _required_epoch(
        payload,
        "last_run_initialisation_time",
    )
    availability_epoch = _required_epoch(payload, "last_run_availability_time")
    if availability_epoch < initialization_epoch:
        raise ForecastProviderPayloadError(
            "model availability cannot precede initialization"
        )
    bounded_metadata = {
        key: value
        for key, value in payload.items()
        if key
        in {
            "data_end_time",
            "last_run_availability_time",
            "last_run_initialisation_time",
            "last_run_modification_time",
            "temporal_resolution_seconds",
            "update_interval_seconds",
        }
        and (value is None or isinstance(value, (int, float, str)))
    }
    return ModelCycleMetadata(
        source_key=source_key,
        initialization_time=datetime.fromtimestamp(initialization_epoch, tz=UTC),
        availability_time=datetime.fromtimestamp(availability_epoch, tz=UTC),
        raw_metadata=bounded_metadata,
    )


def assert_same_model_cycle(
    before: ModelCycleMetadata,
    after: ModelCycleMetadata,
) -> None:
    if before.source_key != after.source_key:
        raise ValueError("model-cycle source keys must match")
    if before.initialization_time != after.initialization_time:
        raise ModelCycleChangedError(
            f"{before.source_key} model cycle changed during acquisition"
        )


def normalize_daily_forecast(
    *,
    run_id: str,
    source_key: str,
    point: ForecastRequestPoint,
    payload: Mapping[str, object],
) -> tuple[WeatherForecastDaily, ...]:
    source = _source_config(source_key)
    timezone_name = payload.get("timezone")
    if not isinstance(timezone_name, str):
        raise ForecastProviderPayloadError("forecast payload needs a timezone")
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ForecastProviderPayloadError(
            "forecast timezone must be an IANA timezone"
        ) from error
    hourly = payload.get("hourly")
    units = payload.get("hourly_units")
    if not isinstance(hourly, Mapping) or not isinstance(units, Mapping):
        raise ForecastProviderPayloadError(
            "forecast payload needs hourly values and units"
        )
    timestamps = _timestamps(hourly.get("time"))
    values_by_variable = _hourly_values(source, hourly, len(timestamps))
    _validate_units(source, units)

    indices_by_date: dict[date, list[int]] = {}
    localized_timestamps: list[datetime] = []
    for index, timestamp in enumerate(timestamps):
        localized = timestamp.astimezone(timezone)
        localized_timestamps.append(localized)
        indices_by_date.setdefault(localized.date(), []).append(index)

    rows: list[WeatherForecastDaily] = []
    for valid_date, indices in sorted(indices_by_date.items()):
        expected_epochs = _expected_day_epochs(valid_date, timezone)
        actual_epochs = {int(timestamps[index].timestamp()) for index in indices}
        required_complete = all(
            all(values_by_variable[variable][index] is not None for index in indices)
            for variable in source.required_hourly_variables
        )
        if actual_epochs != expected_epochs or not required_complete:
            continue
        noon_indices = [
            index
            for index in indices
            if localized_timestamps[index].hour == 12
            and localized_timestamps[index].minute == 0
        ]
        if len(noon_indices) != 1:
            continue
        noon_index = noon_indices[0]
        temperature = _required_floats(
            values_by_variable["temperature_2m"],
            indices,
        )
        snowfall = _required_floats(values_by_variable["snowfall"], indices)
        rain = _required_floats(values_by_variable["rain"], indices)
        snow_depth_m = _required_float(values_by_variable["snow_depth"][noon_index])
        optional_missing = tuple(
            variable
            for variable in source.optional_hourly_variables
            if variable not in values_by_variable
            or any(values_by_variable[variable][index] is None for index in indices)
        )
        rows.append(
            WeatherForecastDaily(
                forecast_run_id=run_id,
                ski_area_id=point.ski_area_id,
                valid_local_date=valid_date,
                provider_timezone=timezone_name,
                elevation_band=point.elevation_band,
                representative_elevation_m=point.elevation_m,
                request_latitude=point.latitude,
                request_longitude=point.longitude,
                snow_depth_cm=snow_depth_m * 100,
                snow_depth_spread_cm=_optional_at(
                    values_by_variable,
                    "snow_depth_spread",
                    noon_index,
                    multiplier=100,
                ),
                snowfall_cm=sum(snowfall),
                rain_mm=sum(rain),
                positive_degree_hours=sum(max(value, 0) for value in temperature),
                temperature_2m_min_c=min(temperature),
                temperature_2m_max_c=max(temperature),
                freezing_level_mean_m=_optional_mean(
                    values_by_variable,
                    "freezing_level_height",
                    indices,
                ),
                freezing_level_max_m=_optional_max(
                    values_by_variable,
                    "freezing_level_height",
                    indices,
                ),
                wind_speed_10m_max_kmh=_optional_max(
                    values_by_variable,
                    "wind_speed_10m",
                    indices,
                ),
                wind_gusts_10m_max_kmh=_optional_max(
                    values_by_variable,
                    "wind_gusts_10m",
                    indices,
                ),
                ensemble_member_count=None,
                is_complete=True,
                completeness_metadata={
                    "expected_hour_count": len(expected_epochs),
                    "observed_hour_count": len(indices),
                    "required_variables": source.required_hourly_variables,
                    "requested_optional_variables": (source.optional_hourly_variables),
                    "missing_optional_variables": optional_missing,
                    "original_units": {
                        variable: units.get(variable)
                        for variable in source.requested_hourly_variables
                    },
                },
            )
        )
    return tuple(rows)


def _source_config(source_key: str) -> ForecastSourceConfig:
    try:
        return FORECAST_SOURCES[source_key]
    except KeyError as error:
        raise ValueError(f"unknown forecast source: {source_key}") from error


def _required_epoch(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ForecastProviderPayloadError(f"model metadata needs numeric {key}")
    if not math.isfinite(value):
        raise ForecastProviderPayloadError(f"model metadata has invalid {key}")
    return int(value)


def _timestamps(raw: object) -> tuple[datetime, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ForecastProviderPayloadError("hourly time must be an array")
    result: list[datetime] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ForecastProviderPayloadError(
                "hourly time must contain Unix timestamps"
            )
        result.append(datetime.fromtimestamp(value, tz=UTC))
    if len({value.timestamp() for value in result}) != len(result):
        raise ForecastProviderPayloadError("hourly timestamps must be unique")
    return tuple(result)


def _hourly_values(
    source: ForecastSourceConfig,
    hourly: Mapping[str, object],
    timestamp_count: int,
) -> dict[str, tuple[float | None, ...]]:
    result: dict[str, tuple[float | None, ...]] = {}
    for variable in source.requested_hourly_variables:
        raw = hourly.get(variable)
        if raw is None:
            if variable in source.required_hourly_variables:
                raise ForecastProviderPayloadError(
                    f"forecast payload is missing required {variable}"
                )
            continue
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise ForecastProviderPayloadError(f"{variable} must be an array")
        if len(raw) != timestamp_count:
            raise ForecastProviderPayloadError(
                f"{variable} length must match hourly time"
            )
        result[variable] = tuple(_optional_float(value) for value in raw)
    return result


def _validate_units(
    source: ForecastSourceConfig,
    units: Mapping[object, object],
) -> None:
    if units.get("time") != "unixtime":
        raise ForecastProviderPayloadError("hourly time must use Unix timestamps")
    for variable in source.required_hourly_variables:
        expected = _EXPECTED_UNITS[variable]
        if units.get(variable) != expected:
            raise ForecastProviderPayloadError(
                f"unexpected unit for {variable}: {units.get(variable)!r}"
            )
    for variable in source.optional_hourly_variables:
        if variable in units and units.get(variable) != _EXPECTED_UNITS[variable]:
            raise ForecastProviderPayloadError(
                f"unexpected unit for {variable}: {units.get(variable)!r}"
            )


def _expected_day_epochs(valid_date: date, timezone: ZoneInfo) -> set[int]:
    start = datetime.combine(valid_date, time.min, tzinfo=timezone).astimezone(UTC)
    end = datetime.combine(
        valid_date + timedelta(days=1),
        time.min,
        tzinfo=timezone,
    ).astimezone(UTC)
    result: set[int] = set()
    current = start
    while current < end:
        result.add(int(current.timestamp()))
        current += timedelta(hours=1)
    return result


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ForecastProviderPayloadError("hourly values must be numeric or null")
    result = float(value)
    if not math.isfinite(result):
        raise ForecastProviderPayloadError("hourly values must be finite")
    return result


def _required_float(value: float | None) -> float:
    if value is None:
        raise ForecastProviderPayloadError("required hourly value is null")
    return value


def _required_floats(
    values: Sequence[float | None],
    indices: Sequence[int],
) -> tuple[float, ...]:
    return tuple(_required_float(values[index]) for index in indices)


def _optional_at(
    values_by_variable: Mapping[str, Sequence[float | None]],
    variable: str,
    index: int,
    *,
    multiplier: float = 1,
) -> float | None:
    values = values_by_variable.get(variable)
    if values is None or values[index] is None:
        return None
    return _required_float(values[index]) * multiplier


def _optional_values(
    values_by_variable: Mapping[str, Sequence[float | None]],
    variable: str,
    indices: Sequence[int],
) -> tuple[float, ...] | None:
    values = values_by_variable.get(variable)
    if values is None or any(values[index] is None for index in indices):
        return None
    return tuple(_required_float(values[index]) for index in indices)


def _optional_mean(
    values_by_variable: Mapping[str, Sequence[float | None]],
    variable: str,
    indices: Sequence[int],
) -> float | None:
    values = _optional_values(values_by_variable, variable, indices)
    return None if values is None else sum(values) / len(values)


def _optional_max(
    values_by_variable: Mapping[str, Sequence[float | None]],
    variable: str,
    indices: Sequence[int],
) -> float | None:
    values = _optional_values(values_by_variable, variable, indices)
    return None if values is None else max(values)
