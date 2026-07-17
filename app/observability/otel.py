from __future__ import annotations

import logging
from collections.abc import Mapping

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.urllib import URLLibInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.util.re import parse_env_headers

from app.observability.config import ObservabilitySettings, load_observability_settings
from app.observability.metrics import (
    OpenTelemetryMetricsRecorder,
    configure_metrics_recorder,
)
from app.observability.tracing import configure_tracer

LOGGER = logging.getLogger(__name__)
_runtime_configured = False
_global_instrumentors_configured = False
_configured_signature: tuple[str, str | None, str | None, bool, float] | None = None

HEALTHCHECK_TRACE_EXCLUDED_URLS = "/api/healthz,/api/readyz,/healthz,/readyz"

_DURATION_SECONDS_BUCKETS = (
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.0,
    3.0,
    4.0,
    5.0,
    6.0,
    7.0,
    8.0,
    9.0,
    10.0,
    11.0,
    12.0,
    13.0,
    15.0,
    21.0,
    34.0,
)
_CONFIDENCE_BUCKETS = (0.0, 0.25, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0)
_COUNT_BUCKETS = (0.0, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0)


def configure_observability(app: FastAPI) -> ObservabilitySettings:
    settings = configure_observability_runtime()
    if not settings.enabled:
        return settings

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls=HEALTHCHECK_TRACE_EXCLUDED_URLS,
    )
    return settings


def configure_observability_runtime() -> ObservabilitySettings:
    settings = load_observability_settings()
    if not settings.enabled:
        return settings

    signature = _runtime_signature(settings)
    if not _runtime_configured:
        _configure_runtime(settings, signature)
    elif _configured_signature != signature:
        LOGGER.warning(
            "OpenTelemetry runtime is already configured; changed runtime "
            "settings will be ignored until process restart."
        )

    configure_tracer(trace.get_tracer("snowcast"))
    configure_metrics_recorder(
        OpenTelemetryMetricsRecorder(metrics.get_meter("snowcast"))
    )
    _instrument_global_libraries_once()
    return settings


def shutdown_observability_runtime() -> None:
    for provider in (_get_trace_provider(), _get_meter_provider()):
        if provider is None:
            continue
        for method_name in ("force_flush", "shutdown"):
            method = getattr(provider, method_name, None)
            if not callable(method):
                continue
            try:
                method()
            except Exception:
                LOGGER.warning(
                    "OpenTelemetry %s failed during runtime shutdown.",
                    method_name,
                    exc_info=True,
                )


def _get_trace_provider() -> object | None:
    try:
        return trace.get_tracer_provider()
    except Exception:
        return None


def _get_meter_provider() -> object | None:
    try:
        return metrics.get_meter_provider()
    except Exception:
        return None


def _configure_runtime(
    settings: ObservabilitySettings,
    signature: tuple[str, str | None, str | None, bool, float],
) -> None:
    global _configured_signature, _runtime_configured

    resource = Resource.create(
        {
            "service.name": settings.service_name,
            "service.version": settings.service_version or "unknown",
        }
    )

    sampler = ParentBased(TraceIdRatioBased(settings.trace_sample_rate))
    trace_provider = TracerProvider(resource=resource, sampler=sampler)
    metric_readers = []

    if settings.otlp_endpoint:
        headers = _parse_otlp_headers(settings.otlp_headers)
        trace_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=f"{settings.otlp_endpoint.rstrip('/')}/v1/traces",
                    headers=headers,
                )
            )
        )
        metric_readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=f"{settings.otlp_endpoint.rstrip('/')}/v1/metrics",
                    headers=headers,
                )
            )
        )
    else:
        LOGGER.warning(
            "OTEL_ENABLED=true but OTEL_EXPORTER_OTLP_ENDPOINT is not set; "
            "telemetry will be local-only."
        )

    trace.set_tracer_provider(trace_provider)
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=metric_readers,
        views=_metric_views(),
    )
    metrics.set_meter_provider(meter_provider)

    _runtime_configured = True
    _configured_signature = signature


def _instrument_global_libraries_once() -> None:
    global _global_instrumentors_configured
    if _global_instrumentors_configured:
        return
    LoggingInstrumentor().instrument(set_logging_format=False)
    PsycopgInstrumentor().instrument()
    URLLibInstrumentor().instrument()
    _global_instrumentors_configured = True


def _runtime_signature(
    settings: ObservabilitySettings,
) -> tuple[str, str | None, str | None, bool, float]:
    return (
        settings.service_name,
        settings.service_version,
        settings.otlp_endpoint,
        bool(settings.otlp_headers),
        settings.trace_sample_rate,
    )


def _parse_otlp_headers(value: str | None) -> Mapping[str, str]:
    if not value:
        return {}
    return parse_env_headers(value, liberal=True)


def _metric_views() -> list[View]:
    duration_views = [
        _histogram_view(name, _DURATION_SECONDS_BUCKETS)
        for name in (
            "snowcast_http_request_duration_seconds",
            "snowcast_search_duration_seconds",
            "snowcast_search_refinement_duration_seconds",
            "snowcast_search_phase_duration_seconds",
            "snowcast_parse_duration_seconds",
            "snowcast_llm_duration_seconds",
            "snowcast_conditions_refresh_duration_seconds",
            "snowcast_rebuild_snow_climatology_duration_seconds",
            "snowcast_audit_data_quality_duration_seconds",
            "snowcast_weather_forecast_refresh_duration_seconds",
            "snowcast_weather_forecast_retention_duration_seconds",
        )
    ]
    return [
        *duration_views,
        _histogram_view("snowcast_parse_confidence", _CONFIDENCE_BUCKETS),
        _histogram_view("snowcast_search_candidates", _COUNT_BUCKETS),
        _histogram_view("snowcast_search_eligible_candidates", _COUNT_BUCKETS),
        _histogram_view("snowcast_search_result_groups", _COUNT_BUCKETS),
        _histogram_view("snowcast_search_refinement_questions", _COUNT_BUCKETS),
    ]


def _histogram_view(name: str, boundaries: tuple[float, ...]) -> View:
    return View(
        instrument_name=name,
        aggregation=ExplicitBucketHistogramAggregation(boundaries=boundaries),
    )
