from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ObservabilitySettings:
    enabled: bool
    service_name: str
    service_version: str | None
    otlp_endpoint: str | None
    otlp_headers: str | None = field(repr=False)
    trace_sample_rate: float
    log_format: str


def load_observability_settings() -> ObservabilitySettings:
    return ObservabilitySettings(
        enabled=_env_bool("OTEL_ENABLED", default=False),
        service_name=os.getenv("OTEL_SERVICE_NAME", "snowcast"),
        service_version=os.getenv("OTEL_SERVICE_VERSION") or None,
        otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or None,
        otlp_headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS") or None,
        trace_sample_rate=_env_float("OTEL_TRACES_SAMPLER_ARG", default=1.0),
        log_format=os.getenv("LOG_FORMAT", "text").strip().lower() or "text",
    )


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, *, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return max(0.0, min(parsed, 1.0))
