from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
    model_validator,
)

from app.domain.search_factors.models import FrozenMapping

ForecastRunStatus = Literal["building", "complete", "rejected", "failed"]
ForecastKind = Literal["deterministic", "ensemble", "ensemble_mean"]
WeatherElevationBand = Literal["base", "mid", "upper"]
_NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")


class _WeatherForecastModel(BaseModel):
    model_config = _MODEL_CONFIG


class WeatherForecastRun(_WeatherForecastModel):
    forecast_run_id: _NonBlankText
    forecast_source_key: _NonBlankText
    provider_gateway: _NonBlankText
    producer: _NonBlankText
    provider_model_id: _NonBlankText
    forecast_kind: ForecastKind
    model_initialization_time: datetime
    provider_availability_time: datetime
    ingested_at: datetime
    completed_at: datetime | None = None
    first_valid_date: date
    last_valid_date: date
    status: ForecastRunStatus
    schema_version: _NonBlankText
    parser_version: _NonBlankText
    aggregation_policy_version: _NonBlankText
    provider_metadata: FrozenMapping
    failure_reason: _NonBlankText | None = None

    @field_validator(
        "model_initialization_time",
        "provider_availability_time",
        "ingested_at",
        "completed_at",
    )
    @classmethod
    def require_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("forecast run times must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_run(self) -> Self:
        if self.last_valid_date < self.first_valid_date:
            raise ValueError("last_valid_date must be on or after first_valid_date")
        if self.provider_availability_time < self.model_initialization_time:
            raise ValueError(
                "provider availability cannot precede model initialization"
            )
        if self.status == "building":
            if self.completed_at is not None or self.failure_reason is not None:
                raise ValueError(
                    "building run cannot have completion or failure fields"
                )
        elif self.status == "complete":
            if self.completed_at is None:
                raise ValueError("complete run needs completed_at")
            if self.failure_reason is not None:
                raise ValueError("complete run cannot have failure_reason")
        elif self.completed_at is None or self.failure_reason is None:
            raise ValueError(
                "rejected or failed run needs completed_at and failure_reason"
            )
        return self


class WeatherForecastDaily(_WeatherForecastModel):
    forecast_run_id: _NonBlankText
    ski_area_id: _NonBlankText
    valid_local_date: date
    provider_timezone: _NonBlankText
    elevation_band: WeatherElevationBand = "mid"
    representative_elevation_m: int = Field(ge=0)
    request_latitude: float = Field(ge=-90, le=90)
    request_longitude: float = Field(ge=-180, le=180)
    snow_depth_cm: float | None = Field(default=None, ge=0)
    snow_depth_spread_cm: float | None = Field(default=None, ge=0)
    snowfall_cm: float = Field(ge=0)
    rain_mm: float = Field(ge=0)
    positive_degree_hours: float = Field(ge=0)
    temperature_2m_min_c: float
    temperature_2m_max_c: float
    freezing_level_mean_m: float | None = Field(default=None, ge=0)
    freezing_level_max_m: float | None = Field(default=None, ge=0)
    wind_speed_10m_max_kmh: float | None = Field(default=None, ge=0)
    wind_gusts_10m_max_kmh: float | None = Field(default=None, ge=0)
    ensemble_member_count: int | None = Field(default=None, gt=0)
    is_complete: bool
    completeness_metadata: FrozenMapping

    @field_validator("provider_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("provider_timezone must be an IANA timezone") from error
        return value

    @model_validator(mode="after")
    def validate_temperature_range(self) -> Self:
        if self.temperature_2m_max_c < self.temperature_2m_min_c:
            raise ValueError(
                "temperature_2m_max_c must be at least temperature_2m_min_c"
            )
        return self


class ServedWeatherForecastDaily(_WeatherForecastModel):
    run: WeatherForecastRun
    daily: WeatherForecastDaily

    @model_validator(mode="after")
    def validate_run_identity(self) -> Self:
        if self.daily.forecast_run_id != self.run.forecast_run_id:
            raise ValueError("daily row and run IDs must match")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def lead_days(self) -> int:
        timezone = ZoneInfo(self.daily.provider_timezone)
        initialization_date = self.run.model_initialization_time.astimezone(
            timezone
        ).date()
        return (self.daily.valid_local_date - initialization_date).days


class WeatherForecastHead(_WeatherForecastModel):
    ski_area_id: _NonBlankText
    forecast_source_key: _NonBlankText
    run: WeatherForecastRun
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("forecast head update time must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_source_identity(self) -> Self:
        if self.forecast_source_key != self.run.forecast_source_key:
            raise ValueError("forecast head and run source keys must match")
        if self.run.status != "complete":
            raise ValueError("forecast head run must be complete")
        return self


class ForecastRetentionResult(_WeatherForecastModel):
    deleted_complete_runs: int = Field(ge=0)
    deleted_failed_or_rejected_runs: int = Field(ge=0)
    protected_head_runs: int = Field(ge=0)
