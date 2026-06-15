# OpenTelemetry Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Sprint 35: an OpenTelemetry-first observability foundation that makes `/api/search`, `/api/parse-query`, LLM use, and weather-data freshness measurable and debuggable in production.

**Architecture:** Add a narrow `app/observability/` package that owns configuration, structured logging, metrics, trace helpers, and request middleware. Keep domain code free of vendor details by calling small helper functions/context managers. Telemetry must be no-op by default unless explicitly enabled, so local development and tests do not require Grafana Cloud or any collector.

**Tech Stack:** FastAPI, Python logging, OpenTelemetry Python SDK/instrumentations, OTLP HTTP exporter, Fly.io health checks, pytest, Ruff.

---

## Scope

Implement the Sprint 35 P0 scope and the low-risk parts of P1:

- OpenTelemetry setup behind env flags.
- Structured request logs with request IDs and trace IDs.
- HTTP request metrics/traces.
- Search phase spans and metrics.
- Parser/LLM mode, retry, fallback, and duration metrics.
- Conditions freshness telemetry.
- Fly health-check config and observability runbook.

Do not implement:

- Self-hosted collector.
- Sentry.
- Catalog acquisition telemetry.
- Log export pipeline.
- High-cardinality metrics containing raw queries, origins, URLs, prompts, or resort names.

## Required Dependency Decision

This sprint requires adding runtime dependencies. Get explicit user approval before editing `pyproject.toml` or running dependency-install commands.

Proposed dependencies:

```toml
"opentelemetry-api>=1.34,<2.0",
"opentelemetry-sdk>=1.34,<2.0",
"opentelemetry-exporter-otlp-proto-http>=1.34,<2.0",
"opentelemetry-instrumentation-fastapi>=0.55b0,<1.0",
"opentelemetry-instrumentation-logging>=0.55b0,<1.0",
"opentelemetry-instrumentation-psycopg>=0.55b0,<1.0",
"opentelemetry-instrumentation-urllib>=0.55b0,<1.0",
```

`urllib` instrumentation matters because Snowcast currently uses `urllib.request.urlopen` for Gemini, Open-Meteo, and Google auth. `httpx` instrumentation can wait until catalog acquisition telemetry is promoted, because `httpx` is currently a dev dependency and the core runtime path does not rely on it.

## File Structure

Create:

- `app/observability/__init__.py` - package exports.
- `app/observability/config.py` - env-driven observability settings.
- `app/observability/context.py` - request ID context variable and safe accessors.
- `app/observability/logging.py` - JSON logging formatter and event helper.
- `app/observability/metrics.py` - metric recorder protocol, no-op recorder, OTel recorder, test recorder hooks, metric names.
- `app/observability/tracing.py` - span helpers, attribute helpers, no-op-safe wrappers.
- `app/observability/middleware.py` - request ID, request log, and HTTP metrics middleware.
- `app/observability/search.py` - search-specific phase context manager and result metric helpers.
- `app/observability/parser.py` - parser/LLM metric helpers.
- `docs/observability-runbook.md` - setup, dashboards, alerts, and first-response runbook.
- `tests/test_observability.py` - DB-free unit tests for config, logging, middleware, and helpers.
- `tests/test_observability_search.py` - DB-free tests for search instrumentation with small fake repositories/providers.
- `tests/test_observability_parser.py` - DB-free tests for parser/LLM instrumentation using fake LLM clients and fake cache.

Modify:

- `tests/conftest.py` - add observability test files to `DB_FREE_TEST_FILES`.
- `pyproject.toml` - add OTel dependencies after explicit user approval.
- `app/main.py` - configure logging/telemetry and install request middleware.
- `app/domain/search_service.py` - add search spans/phase metrics without changing response shape.
- `app/domain/services.py` - add top-level search telemetry around narrative generation if needed.
- `app/ai/parser.py` - record parser mode/fallback/cache/model/confidence telemetry.
- `app/ai/retry.py` - record LLM retry metrics without coupling to Gemini.
- `app/data/refresh_conditions.py` - record refresh success/failure/freshness telemetry.
- `fly.toml` - add health checks; consider `min_machines_running = 1` only if explicitly approved.
- `README.md`, `docs/engineering-notes.md`, `PROJECT.md` - update Sprint 35 status and setup references.

## Environment Contract

Use standard OTel env vars where possible:

```text
OTEL_ENABLED=false
OTEL_SERVICE_NAME=snowcast
OTEL_SERVICE_VERSION=<git sha or app version when available>
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-eu-west-0.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <redacted>
OTEL_TRACES_SAMPLER_ARG=0.1
LOG_FORMAT=text|json
LOG_LEVEL=INFO
```

Rules:

- If `OTEL_ENABLED` is not true, all OTel exporters/instrumentors stay disabled.
- If `OTEL_ENABLED=true` but `OTEL_EXPORTER_OTLP_ENDPOINT` is missing, configure in-process providers but no exporter; log one warning.
- Tests should set `OTEL_ENABLED=false` unless they explicitly test setup behavior.
- Structured logs should be controlled independently by `LOG_FORMAT=json`.

---

## Task 1: Observability Config, Context, And Test Hooks

**Files:**

- Create: `app/observability/__init__.py`
- Create: `app/observability/config.py`
- Create: `app/observability/context.py`
- Create: `app/observability/metrics.py`
- Create: `app/observability/tracing.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_observability.py`

- [ ] **Step 1: Add DB-free test registration**

Modify `tests/conftest.py`:

```python
DB_FREE_TEST_FILES = {
    "test_env.py",
    "test_loader.py",
    "test_observability.py",
    "test_observability_parser.py",
    "test_observability_search.py",
    "test_planning.py",
    "test_resort_acquisition.py",
}
```

- [ ] **Step 2: Write failing config/context tests**

Create `tests/test_observability.py`:

```python
import json
import logging

from app.observability.config import ObservabilitySettings, load_observability_settings
from app.observability.context import current_request_id, request_id_context
from app.observability.metrics import InMemoryMetricsRecorder, reset_metrics_recorder_for_tests, set_metrics_recorder_for_tests
from app.observability.tracing import set_span_attributes, start_span


def test_observability_settings_default_to_disabled(monkeypatch):
    monkeypatch.delenv("OTEL_ENABLED", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("LOG_FORMAT", raising=False)

    settings = load_observability_settings()

    assert settings.enabled is False
    assert settings.service_name == "snowcast"
    assert settings.otlp_endpoint is None
    assert settings.log_format == "text"


def test_observability_settings_read_enabled_env(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "snowcast-api")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://otel.example/otlp")
    monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.25")
    monkeypatch.setenv("LOG_FORMAT", "json")

    settings = load_observability_settings()

    assert settings == ObservabilitySettings(
        enabled=True,
        service_name="snowcast-api",
        service_version=None,
        otlp_endpoint="https://otel.example/otlp",
        otlp_headers=None,
        trace_sample_rate=0.25,
        log_format="json",
    )


def test_request_id_context_is_scoped():
    assert current_request_id() is None

    token = request_id_context.set("req-test")
    try:
        assert current_request_id() == "req-test"
    finally:
        request_id_context.reset(token)

    assert current_request_id() is None


def test_noop_tracing_helpers_are_safe_when_disabled():
    with start_span("test.span") as span:
        set_span_attributes(span, {"snowcast.test": "ok", "snowcast.count": 3})


def test_in_memory_metrics_recorder_captures_counter_and_histogram():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        recorder.increment("snowcast_test_total", {"status": "ok"})
        recorder.observe("snowcast_test_seconds", 1.25, {"phase": "test"})

        assert recorder.counters == [
            ("snowcast_test_total", {"status": "ok"}, 1)
        ]
        assert recorder.histograms == [
            ("snowcast_test_seconds", {"phase": "test"}, 1.25)
        ]
    finally:
        reset_metrics_recorder_for_tests()
```

- [ ] **Step 3: Run test and verify it fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
```

Expected: FAIL because `app.observability` modules do not exist.

- [ ] **Step 4: Implement config and context**

Create `app/observability/__init__.py`:

```python
"""Snowcast observability helpers."""
```

Create `app/observability/config.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ObservabilitySettings:
    enabled: bool
    service_name: str
    service_version: str | None
    otlp_endpoint: str | None
    otlp_headers: str | None
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
```

Create `app/observability/context.py`:

```python
from __future__ import annotations

from contextvars import ContextVar

request_id_context: ContextVar[str | None] = ContextVar(
    "snowcast_request_id",
    default=None,
)


def current_request_id() -> str | None:
    return request_id_context.get()
```

- [ ] **Step 5: Implement no-op metrics and tracing helpers**

Create `app/observability/metrics.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

MetricAttributes = Mapping[str, str | int | float | bool]


class MetricsRecorder(Protocol):
    def increment(
        self,
        name: str,
        attributes: MetricAttributes | None = None,
        amount: int = 1,
    ) -> None:
        raise NotImplementedError

    def observe(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        raise NotImplementedError

    def gauge(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        raise NotImplementedError


class NoopMetricsRecorder:
    def increment(
        self,
        name: str,
        attributes: MetricAttributes | None = None,
        amount: int = 1,
    ) -> None:
        return None

    def observe(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        return None

    def gauge(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        return None


@dataclass
class InMemoryMetricsRecorder:
    counters: list[tuple[str, dict[str, str | int | float | bool], int]] = field(
        default_factory=list
    )
    histograms: list[tuple[str, dict[str, str | int | float | bool], float]] = field(
        default_factory=list
    )
    gauges: list[tuple[str, dict[str, str | int | float | bool], float]] = field(
        default_factory=list
    )

    def increment(
        self,
        name: str,
        attributes: MetricAttributes | None = None,
        amount: int = 1,
    ) -> None:
        self.counters.append((name, dict(attributes or {}), amount))

    def observe(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        self.histograms.append((name, dict(attributes or {}), value))

    def gauge(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        self.gauges.append((name, dict(attributes or {}), value))


_metrics_recorder: MetricsRecorder = NoopMetricsRecorder()


def get_metrics_recorder() -> MetricsRecorder:
    return _metrics_recorder


def configure_metrics_recorder(recorder: MetricsRecorder) -> None:
    global _metrics_recorder
    _metrics_recorder = recorder


def set_metrics_recorder_for_tests(recorder: MetricsRecorder) -> None:
    configure_metrics_recorder(recorder)


def reset_metrics_recorder_for_tests() -> None:
    configure_metrics_recorder(NoopMetricsRecorder())
```

Create `app/observability/tracing.py`:

```python
from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager


@contextmanager
def start_span(
    name: str,
    attributes: Mapping[str, str | int | float | bool | None] | None = None,
) -> Iterator[object]:
    yield _NoopSpan()


def set_span_attributes(
    span: object,
    attributes: Mapping[str, str | int | float | bool | None],
) -> None:
    setter = getattr(span, "set_attribute", None)
    if setter is None:
        return
    for key, value in attributes.items():
        if value is not None:
            setter(key, value)


class _NoopSpan:
    def set_attribute(self, key: str, value: str | int | float | bool) -> None:
        return None
```

- [ ] **Step 6: Run test and verify it passes**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
```

Expected: PASS.

---

## Task 2: OpenTelemetry SDK Setup And Runtime Bootstrap

**Files:**

- Modify: `pyproject.toml`
- Create: `app/observability/otel.py`
- Modify: `app/observability/metrics.py`
- Modify: `app/observability/tracing.py`
- Modify: `app/main.py`
- Test: `tests/test_observability.py`

- [ ] **Step 1: Get dependency approval**

Before editing dependencies, ask:

```text
Sprint 35 needs OpenTelemetry runtime dependencies in pyproject.toml. Approve adding the listed OTel packages?
```

Do not edit `pyproject.toml` until approved.

- [ ] **Step 2: Add dependency test expectations**

Append to `tests/test_observability.py`:

```python
from fastapi import FastAPI

from app.observability.otel import configure_observability


def test_configure_observability_disabled_is_noop(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    app = FastAPI()

    settings = configure_observability(app)

    assert settings.enabled is False


def test_configure_observability_enabled_without_endpoint_is_safe(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    app = FastAPI()

    settings = configure_observability(app)

    assert settings.enabled is True
    assert settings.otlp_endpoint is None
```

- [ ] **Step 3: Run test and verify it fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
```

Expected: FAIL because `app.observability.otel` does not exist.

- [ ] **Step 4: Add OTel dependencies**

Modify `pyproject.toml` dependencies:

```toml
  "opentelemetry-api>=1.34,<2.0",
  "opentelemetry-sdk>=1.34,<2.0",
  "opentelemetry-exporter-otlp-proto-http>=1.34,<2.0",
  "opentelemetry-instrumentation-fastapi>=0.55b0,<1.0",
  "opentelemetry-instrumentation-logging>=0.55b0,<1.0",
  "opentelemetry-instrumentation-psycopg>=0.55b0,<1.0",
  "opentelemetry-instrumentation-urllib>=0.55b0,<1.0",
```

Run:

```bash
UV_CACHE_DIR=.uv-cache uv sync --no-config --dev
```

Expected: dependency lock/update succeeds.

- [ ] **Step 5: Implement OTel setup**

Create `app/observability/otel.py`:

```python
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
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.observability.config import ObservabilitySettings, load_observability_settings
from app.observability.metrics import OpenTelemetryMetricsRecorder, configure_metrics_recorder
from app.observability.tracing import configure_tracer

LOGGER = logging.getLogger(__name__)


def configure_observability(app: FastAPI) -> ObservabilitySettings:
    settings = load_observability_settings()
    if not settings.enabled:
        return settings

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
    configure_tracer(trace.get_tracer("snowcast"))

    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)
    configure_metrics_recorder(
        OpenTelemetryMetricsRecorder(metrics.get_meter("snowcast"))
    )

    FastAPIInstrumentor.instrument_app(app)
    LoggingInstrumentor().instrument(set_logging_format=False)
    PsycopgInstrumentor().instrument()
    URLLibInstrumentor().instrument()
    return settings


def _parse_otlp_headers(value: str | None) -> Mapping[str, str]:
    if not value:
        return {}
    headers: dict[str, str] = {}
    for item in value.split(","):
        if "=" not in item:
            continue
        key, header_value = item.split("=", 1)
        headers[key.strip()] = header_value.strip()
    return headers
```

- [ ] **Step 6: Extend metrics and tracing implementations**

Add to `app/observability/metrics.py`:

```python
class OpenTelemetryMetricsRecorder:
    def __init__(self, meter) -> None:
        self._meter = meter
        self._counters = {}
        self._histograms = {}

    def increment(
        self,
        name: str,
        attributes: MetricAttributes | None = None,
        amount: int = 1,
    ) -> None:
        instrument = self._counters.get(name)
        if instrument is None:
            instrument = self._meter.create_counter(name)
            self._counters[name] = instrument
        instrument.add(amount, attributes=dict(attributes or {}))

    def observe(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        instrument = self._histograms.get(name)
        if instrument is None:
            instrument = self._meter.create_histogram(name)
            self._histograms[name] = instrument
        instrument.record(value, attributes=dict(attributes or {}))

    def gauge(
        self,
        name: str,
        value: float,
        attributes: MetricAttributes | None = None,
    ) -> None:
        self.observe(name, value, attributes)
```

Replace `app/observability/tracing.py` with OTel-aware helpers:

```python
from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager

_tracer = None


def configure_tracer(tracer) -> None:
    global _tracer
    _tracer = tracer


@contextmanager
def start_span(
    name: str,
    attributes: Mapping[str, str | int | float | bool | None] | None = None,
) -> Iterator[object]:
    if _tracer is None:
        span = _NoopSpan()
        set_span_attributes(span, attributes or {})
        yield span
        return
    with _tracer.start_as_current_span(name) as span:
        set_span_attributes(span, attributes or {})
        yield span


def set_span_attributes(
    span: object,
    attributes: Mapping[str, str | int | float | bool | None],
) -> None:
    setter = getattr(span, "set_attribute", None)
    if setter is None:
        return
    for key, value in attributes.items():
        if value is not None:
            setter(key, value)


class _NoopSpan:
    def set_attribute(self, key: str, value: str | int | float | bool) -> None:
        return None
```

- [ ] **Step 7: Wire setup into app startup**

Modify `app/main.py`:

```python
from app.observability.otel import configure_observability
```

Inside `create_app` after the `FastAPI` instance is created and before routes/middleware are exercised:

```python
    configure_observability(app)
```

- [ ] **Step 8: Run tests and lint**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/observability tests/test_observability.py
```

Expected: PASS.

---

## Task 3: Structured Logging And Request Middleware

**Files:**

- Create: `app/observability/logging.py`
- Create: `app/observability/middleware.py`
- Modify: `app/main.py`
- Test: `tests/test_observability.py`

- [ ] **Step 1: Add failing middleware/logging tests**

Append to `tests/test_observability.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.observability.logging import JsonLogFormatter, configure_logging, safe_log_extra
from app.observability.middleware import add_observability_middleware


def test_safe_log_extra_drops_sensitive_and_free_text_fields():
    extra = safe_log_extra(
        {
            "query": "ski trip from Warsaw in March",
            "identity_token": "secret",
            "authorization": "Bearer secret",
            "route": "/api/search",
            "has_origin": True,
            "duration_ms": 12.5,
        }
    )

    assert "query" not in extra
    assert "identity_token" not in extra
    assert "authorization" not in extra
    assert extra == {
        "route": "/api/search",
        "has_origin": True,
        "duration_ms": 12.5,
    }


def test_json_log_formatter_includes_event_request_and_trace_fields():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="snowcast.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Request handled.",
        args=(),
        exc_info=None,
    )
    record.event = "http.request.completed"
    record.request_id = "req-test"
    record.trace_id = "trace-test"
    record.route = "/api/healthz"

    payload = json.loads(formatter.format(record))

    assert payload["event"] == "http.request.completed"
    assert payload["request_id"] == "req-test"
    assert payload["trace_id"] == "trace-test"
    assert payload["route"] == "/api/healthz"
    assert payload["message"] == "Request handled."


def test_request_middleware_sets_request_id_header_and_metric(monkeypatch):
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    app = FastAPI()
    add_observability_middleware(app)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    try:
        response = TestClient(app).get("/healthz", headers={"x-request-id": "req-in"})
    finally:
        reset_metrics_recorder_for_tests()

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-in"
    assert recorder.counters == [
        (
            "snowcast_http_requests_total",
            {"route": "/healthz", "method": "GET", "status_class": "2xx"},
            1,
        )
    ]
    assert recorder.histograms[0][0] == "snowcast_http_request_duration_seconds"
    assert recorder.histograms[0][1] == {
        "route": "/healthz",
        "method": "GET",
        "status_class": "2xx",
    }
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
```

Expected: FAIL because logging and middleware helpers do not exist.

- [ ] **Step 3: Implement structured logging helpers**

Create `app/observability/logging.py`:

```python
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from opentelemetry import trace

from app.observability.context import current_request_id

SENSITIVE_LOG_FIELDS = {
    "authorization",
    "identity_token",
    "access_token",
    "refresh_token",
    "token",
    "api_key",
    "password",
    "query",
    "prompt",
    "raw_response",
    "user_prompt",
    "system_prompt",
}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in _STANDARD_LOG_RECORD_FIELDS:
                continue
            if key in SENSITIVE_LOG_FIELDS:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                payload[key] = value
        payload.setdefault("request_id", current_request_id())
        trace_id = _current_trace_id()
        if trace_id:
            payload.setdefault("trace_id", trace_id)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    level = os.getenv("LOG_LEVEL", "INFO")
    if os.getenv("LOG_FORMAT", "text").strip().lower() == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        root.addHandler(handler)
        root.setLevel(level)
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def safe_log_extra(extra: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in extra.items()
        if key not in SENSITIVE_LOG_FIELDS
        and (isinstance(value, (str, int, float, bool)) or value is None)
    }


def _current_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return f"{span_context.trace_id:032x}"


_STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}
```

- [ ] **Step 4: Implement request middleware**

Create `app/observability/middleware.py`:

```python
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request

from app.observability.context import request_id_context
from app.observability.logging import safe_log_extra
from app.observability.metrics import get_metrics_recorder

LOGGER = logging.getLogger("snowcast.request")


def add_observability_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex}"
        token = request_id_context.set(request_id)
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            status_class = f"{status_code // 100}xx"
            route = request.scope.get("route")
            route_path = getattr(route, "path", request.url.path)
            attributes = {
                "route": route_path,
                "method": request.method,
                "status_class": status_class,
            }
            recorder = get_metrics_recorder()
            recorder.increment("snowcast_http_requests_total", attributes)
            recorder.observe(
                "snowcast_http_request_duration_seconds",
                duration_ms / 1000,
                attributes,
            )
            LOGGER.info(
                "Request handled.",
                extra=safe_log_extra(
                    {
                        "event": "http.request.completed",
                        "request_id": request_id,
                        "route": route_path,
                        "method": request.method,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    }
                ),
            )
            if "response" in locals():
                response.headers["x-request-id"] = request_id
            request_id_context.reset(token)
```

- [ ] **Step 5: Replace existing request middleware in `app/main.py`**

Modify imports:

```python
from app.observability.logging import configure_logging
from app.observability.middleware import add_observability_middleware
from app.observability.otel import configure_observability
```

In `create_app`:

```python
def create_app(frontend_dist_dir: Path | None = None) -> FastAPI:
    configure_logging()
    app = FastAPI(title="Snowcast")
    configure_observability(app)
    add_observability_middleware(app)
    app.include_router(router, prefix="/api")
```

Remove the existing inline `log_requests` middleware and `_configure_logging()` helper from `app/main.py`.

- [ ] **Step 6: Run tests and lint**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/main.py app/observability tests/test_observability.py
```

Expected: PASS.

---

## Task 4: Search Phase Metrics And Spans

**Files:**

- Create: `app/observability/search.py`
- Modify: `app/domain/search_service.py`
- Test: `tests/test_observability_search.py`

- [ ] **Step 1: Write failing search observability test**

Create `tests/test_observability_search.py`:

```python
from app.domain.models import Destination, Rental, ResortConditions, SearchFilters, SkiArea, StayBase
from app.domain.search_service import search_resorts
from app.observability.metrics import InMemoryMetricsRecorder, reset_metrics_recorder_for_tests, set_metrics_recorder_for_tests


class StaticConditionsProvider:
    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions:
        return ResortConditions(
            resort_name=resort_name,
            snow_confidence_score=0.82,
            snow_confidence_label="good",
            availability_status="open",
            weather_summary="Good current snow outlook.",
            conditions_score=0.78,
            updated_at="2026-01-15T00:00:00+00:00",
            source="open-meteo",
        )


class EmptyHistoryRepository:
    def list_snapshots_for_resort(self, resort_id: str) -> tuple:
        return ()


class EmptyRawWeatherRepository:
    def list_observations_for_resorts(self, resort_ids, *, elevation_bands):
        return {
            (resort_id, elevation_band): ()
            for resort_id in resort_ids
            for elevation_band in elevation_bands
        }


def test_search_records_phase_and_completion_metrics():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        results = search_resorts(
            SearchFilters(
                location="Italy",
                min_price=100,
                max_price=250,
                stars=1,
                skill_level="intermediate",
                travel_month=3,
            ),
            resorts=(_destination(),),
            conditions_provider=StaticConditionsProvider(),
            condition_history_repository=EmptyHistoryRepository(),
            raw_weather_history_repository=EmptyRawWeatherRepository(),
        )
    finally:
        reset_metrics_recorder_for_tests()

    assert results
    metric_names = [name for name, _, _ in recorder.histograms]
    assert "snowcast_search_duration_seconds" in metric_names
    assert "snowcast_search_phase_duration_seconds" in metric_names
    phase_attributes = [
        attrs for name, attrs, _ in recorder.histograms
        if name == "snowcast_search_phase_duration_seconds"
    ]
    assert {"phase": "preload_raw_weather", "window_type": "month", "has_origin": False} in phase_attributes
    assert {"phase": "build_planning_context", "window_type": "month", "has_origin": False} in phase_attributes
    assert recorder.counters[-1] == (
        "snowcast_search_requests_total",
        {"parser_mode": "unknown", "has_origin": False, "window_type": "month"},
        1,
    )


def _destination() -> Destination:
    return Destination(
        resort_id="test-resort",
        name="Test Resort",
        country="Italy",
        region="Test Region",
        price_level="medium",
        latitude=46.0,
        longitude=11.0,
        base_elevation_m=1200,
        summit_elevation_m=2400,
        season_start_month=12,
        season_end_month=4,
        ski_areas=[
            SkiArea(
                ski_area_id="test-ski-area",
                name="Test Ski Area",
                latitude=46.0,
                longitude=11.0,
                base_elevation_m=1200,
                summit_elevation_m=2400,
                season_start_month=12,
                season_end_month=4,
            )
        ],
        stay_bases=[
            StayBase(
                stay_base_id="test-base",
                name="Test Base",
                price_range="EUR 100-180",
                price_min=100,
                price_max=180,
                quality="standard",
                lift_distance="near",
                supported_skill_levels=["intermediate"],
            )
        ],
        rentals=[
            Rental(
                name="Test Rental",
                price_range="EUR 30-45",
                price_min=30,
                price_max=45,
                quality="standard",
                lift_distance="near",
            )
        ],
    )
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability_search.py -q
```

Expected: FAIL because search metrics are not recorded.

- [ ] **Step 3: Implement search observability helper**

Create `app/observability/search.py`:

```python
from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from app.domain.models import SearchFilters
from app.observability.metrics import get_metrics_recorder
from app.observability.tracing import start_span, set_span_attributes


def search_window_type(filters: SearchFilters) -> str:
    if filters.trip_start_date is not None and filters.trip_end_date is not None:
        return "exact_dates"
    if filters.travel_month is not None:
        return "month"
    return "none"


def search_common_attributes(
    filters: SearchFilters,
    *,
    parser_mode: str = "unknown",
) -> dict[str, str | bool]:
    return {
        "parser_mode": parser_mode,
        "has_origin": bool(filters.origin_text),
        "window_type": search_window_type(filters),
    }


@contextmanager
def search_span(
    filters: SearchFilters,
    *,
    candidate_resort_count: int | None = None,
) -> Iterator[object]:
    with start_span(
        "api.search",
        {
            "snowcast.search.window_type": search_window_type(filters),
            "snowcast.search.has_origin": bool(filters.origin_text),
            "snowcast.search.candidate_resort_count": candidate_resort_count,
        },
    ) as span:
        yield span


@contextmanager
def search_phase(
    name: str,
    filters: SearchFilters,
) -> Iterator[None]:
    attributes = {
        "phase": name,
        "window_type": search_window_type(filters),
        "has_origin": bool(filters.origin_text),
    }
    start = time.perf_counter()
    with start_span(
        f"search.{name}",
        {
            "snowcast.search.phase": name,
            "snowcast.search.window_type": attributes["window_type"],
            "snowcast.search.has_origin": attributes["has_origin"],
        },
    ):
        try:
            yield
        finally:
            get_metrics_recorder().observe(
                "snowcast_search_phase_duration_seconds",
                time.perf_counter() - start,
                attributes,
            )


def record_search_completed(
    *,
    filters: SearchFilters,
    result_count: int,
    duration_seconds: float,
    parser_mode: str = "unknown",
    span: object | None = None,
) -> None:
    attributes = search_common_attributes(filters, parser_mode=parser_mode)
    recorder = get_metrics_recorder()
    recorder.increment("snowcast_search_requests_total", attributes)
    recorder.observe("snowcast_search_duration_seconds", duration_seconds, attributes)
    recorder.observe(
        "snowcast_search_results_total",
        float(result_count),
        {
            "window_type": attributes["window_type"],
            "has_origin": attributes["has_origin"],
        },
    )
    if result_count == 0:
        recorder.increment(
            "snowcast_search_empty_results_total",
            {
                "window_type": attributes["window_type"],
                "has_origin": attributes["has_origin"],
            },
        )
    if span is not None:
        set_span_attributes(
            span,
            {
                "snowcast.search.result_count": result_count,
                "snowcast.search.empty_results": result_count == 0,
            },
        )
```

- [ ] **Step 4: Instrument `search_resorts`**

Modify `app/domain/search_service.py` imports:

```python
import time
from app.observability.search import record_search_completed, search_phase, search_span
```

Inside `search_resorts`, after `candidate_resorts` is built:

```python
    search_started = time.perf_counter()
    with search_span(filters, candidate_resort_count=len(candidate_resorts)) as span:
        # Move the existing repository setup, preload, candidate iteration, and
        # final ranking code inside this block.
```

Wrap the specific existing blocks as follows:

```python
with search_phase("load_conditions_provider", filters):
    active_conditions_provider = conditions_provider or get_conditions_provider()

with search_phase("load_history_repositories", filters):
    history_repository = condition_history_repository or get_condition_history_repository()
    active_raw_history_repository = raw_weather_history_repository or get_raw_weather_history_repository()

with search_phase("preload_raw_weather", filters):
    raw_weather_cache = _preload_raw_weather_observations(
        raw_history_repository=active_raw_history_repository,
        resorts=candidate_resorts,
    )

with search_phase("preload_planning_snapshots", filters):
    planning_snapshot_cache = _preload_planning_snapshots(
        history_repository=history_repository,
        resort_ids=snapshot_resort_ids,
    )

with search_phase("assess_travel_effort", filters):
    if filters.origin_text:
        if travel_cache_repository is None:
            travel_effort = assess_deterministic_travel_effort(
                origin_text=filters.origin_text,
                destination=resort,
                max_drive_minutes=filters.max_drive_minutes,
                tolerance=filters.travel_tolerance,
            )
        else:
            travel_effort = assess_travel_effort(
                origin_text=filters.origin_text,
                destination=resort,
                cache=travel_cache_repository,
                max_drive_minutes=filters.max_drive_minutes,
                tolerance=filters.travel_tolerance,
            )

with search_phase("build_planning_context", filters):
    planning_context = _build_ski_area_planning_context(
        filters=filters,
        conditions_provider=active_conditions_provider,
        history_repository=history_repository,
        raw_history_repository=active_raw_history_repository,
        raw_weather_cache=raw_weather_cache,
        planning_snapshot_cache=planning_snapshot_cache,
        destination=resort,
        ski_area=ski_area,
    )

with search_phase("rank_results", filters):
    ranked_results = sorted(results, key=_result_sort_key)[:3]
```

The `assess_travel_effort` phase should wrap the existing per-resort travel
block, not add a second travel calculation. The `build_planning_context` phase
should wrap only cache misses where the ski-area planning context builder is
called, not every reuse of a cached planning context.

Before return:

```python
        record_search_completed(
            filters=filters,
            result_count=len(ranked_results),
            duration_seconds=time.perf_counter() - search_started,
            span=span,
        )
        return ranked_results
```

Keep response shape unchanged.

- [ ] **Step 5: Run test and focused service tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability_search.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config python -m py_compile app/domain/search_service.py app/observability/search.py
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/domain/search_service.py app/observability/search.py tests/test_observability_search.py
```

Expected: PASS.

If local Postgres is available, also run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_services.py::test_search_resorts_reuses_raw_weather_across_matching_stay_bases -q
```

If Postgres is unavailable, record that limitation in the final handoff.

---

## Task 5: Parser And LLM Observability

**Files:**

- Create: `app/observability/parser.py`
- Modify: `app/ai/parser.py`
- Modify: `app/ai/retry.py`
- Test: `tests/test_observability_parser.py`

- [ ] **Step 1: Write failing parser telemetry tests**

Create `tests/test_observability_parser.py`:

```python
from app.ai.llm_client import LLMClient, LLMClientError
from app.ai.parser import LLMBackedQueryParser
from app.observability.metrics import InMemoryMetricsRecorder, reset_metrics_recorder_for_tests, set_metrics_recorder_for_tests


class FakeCache:
    def __init__(self):
        self.payload = None

    def get_parse_cache(self, cache_key):
        return self.payload

    def set_parse_cache(self, **kwargs):
        self.payload = kwargs["response"]


class SuccessfulClient(LLMClient):
    @property
    def model(self) -> str:
        return "test-model"

    def complete(self, **kwargs) -> str:
        return (
            '{"filters":{"location":"Italy","skill_level":"intermediate"},'
            '"confidence":0.91,"unknown_parts":[]}'
        )


class FailingClient(LLMClient):
    @property
    def model(self) -> str:
        return "test-model"

    def complete(self, **kwargs) -> str:
        raise LLMClientError("network failed", reason="network_error")


def test_llm_parser_records_success_mode_and_model():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    parser = LLMBackedQueryParser(
        client=SuccessfulClient(),
        cache_repository=FakeCache(),
    )
    try:
        payload, debug = parser.parse_with_debug("ski in italy")
    finally:
        reset_metrics_recorder_for_tests()

    assert payload["filters"]["location"] == "Italy"
    assert debug.parser_source == "llm"
    assert (
        "snowcast_parse_requests_total",
        {"mode": "llm", "status": "success"},
        1,
    ) in recorder.counters
    assert (
        "snowcast_llm_requests_total",
        {"operation": "query_parser", "model": "test-model", "status": "success"},
        1,
    ) in recorder.counters


def test_llm_parser_records_fallback_reason_without_query_text():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    parser = LLMBackedQueryParser(
        client=FailingClient(),
        cache_repository=FakeCache(),
    )
    try:
        payload, debug = parser.parse_with_debug("ski in france in march")
    finally:
        reset_metrics_recorder_for_tests()

    assert debug.parser_source == "heuristic_fallback"
    assert debug.fallback_reason == "network_error"
    assert (
        "snowcast_parse_requests_total",
        {"mode": "deterministic_fallback", "status": "fallback"},
        1,
    ) in recorder.counters
    assert (
        "snowcast_llm_fallbacks_total",
        {"operation": "query_parser", "reason": "network_error"},
        1,
    ) in recorder.counters
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability_parser.py -q
```

Expected: FAIL because parser metrics are not recorded.

- [ ] **Step 3: Implement parser metric helpers**

Create `app/observability/parser.py`:

```python
from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from app.observability.metrics import get_metrics_recorder
from app.observability.tracing import set_span_attributes, start_span


@contextmanager
def parser_operation(operation: str, *, model: str | None = None) -> Iterator[float]:
    start = time.perf_counter()
    with start_span(
        f"llm.{operation}",
        {
            "snowcast.llm.operation": operation,
            "snowcast.llm.model": model,
        },
    ) as span:
        yield start


def record_parse_result(
    *,
    mode: str,
    status: str,
    duration_seconds: float,
    confidence: float | None = None,
    fallback_reason: str | None = None,
    model: str | None = None,
) -> None:
    recorder = get_metrics_recorder()
    recorder.increment("snowcast_parse_requests_total", {"mode": mode, "status": status})
    recorder.observe(
        "snowcast_parse_duration_seconds",
        duration_seconds,
        {"mode": mode, "status": status},
    )
    if confidence is not None:
        recorder.observe("snowcast_parse_confidence", confidence, {"mode": mode})
    if fallback_reason is not None:
        recorder.increment(
            "snowcast_llm_fallbacks_total",
            {"operation": "query_parser", "reason": fallback_reason},
        )


def record_llm_result(
    *,
    operation: str,
    model: str | None,
    status: str,
    duration_seconds: float,
) -> None:
    recorder = get_metrics_recorder()
    attributes = {
        "operation": operation,
        "model": model or "unknown",
        "status": status,
    }
    recorder.increment("snowcast_llm_requests_total", attributes)
    recorder.observe("snowcast_llm_duration_seconds", duration_seconds, attributes)


def record_llm_retry(
    *,
    operation: str,
    model: str | None,
    reason: str,
) -> None:
    get_metrics_recorder().increment(
        "snowcast_llm_retries_total",
        {
            "operation": operation,
            "model": model or "unknown",
            "reason": reason,
        },
    )


def set_parser_span_attributes(
    span: object,
    *,
    mode: str,
    fallback_used: bool,
    confidence: float | None,
    fallback_reason: str | None,
    model: str | None,
    status: str,
) -> None:
    set_span_attributes(
        span,
        {
            "snowcast.parser.mode": mode,
            "snowcast.parser.fallback_used": fallback_used,
            "snowcast.parser.fallback_reason": fallback_reason or "none",
            "snowcast.parser.confidence": confidence,
            "snowcast.llm.model": model,
            "snowcast.llm.status": status,
        },
    )
```

- [ ] **Step 4: Instrument retry helper**

Modify `app/ai/retry.py`:

```python
from app.observability.parser import record_llm_retry
```

Inside the retry warning branch before the existing warning log call:

```python
            record_llm_retry(
                operation=operation,
                model=llm_client.model,
                reason=error.reason,
            )
```

- [ ] **Step 5: Instrument `LLMBackedQueryParser.parse_with_debug`**

Modify `app/ai/parser.py` imports:

```python
import time
from app.observability.parser import (
    record_llm_result,
    record_parse_result,
    set_parser_span_attributes,
)
from app.observability.tracing import start_span
```

Inside `parse_with_debug`, wrap the body:

```python
    def parse_with_debug(self, query: str) -> tuple[dict, ParseQueryDebugInfo]:
        started = time.perf_counter()
        with start_span("api.parse_query") as span:
            # Indent the current cache lookup, LLM request, fallback decisions,
            # cache write, and final return under this span block.
```

When cache hit returns:

```python
                record_parse_result(
                    mode="llm_cache",
                    status="success",
                    duration_seconds=time.perf_counter() - started,
                    confidence=cached.get("confidence"),
                    model=self._client.model,
                )
                set_parser_span_attributes(
                    span,
                    mode="llm_cache",
                    fallback_used=False,
                    confidence=cached.get("confidence"),
                    fallback_reason=None,
                    model=self._client.model,
                    status="success",
                )
```

Around `complete_with_retries`:

```python
            llm_started = time.perf_counter()
            raw_response = complete_with_retries(
                llm_client=self._client,
                operation="query_parser",
                logger=logger,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0,
                response_mime_type="application/json",
                response_json_schema=PARSER_RESPONSE_JSON_SCHEMA,
            )
            record_llm_result(
                operation="query_parser",
                model=self._client.model,
                status="success",
                duration_seconds=time.perf_counter() - llm_started,
            )
```

In exception fallback:

```python
            record_llm_result(
                operation="query_parser",
                model=self._client.model,
                status="error",
                duration_seconds=time.perf_counter() - llm_started
                if "llm_started" in locals()
                else 0.0,
            )
            record_parse_result(
                mode="deterministic_fallback",
                status="fallback",
                duration_seconds=time.perf_counter() - started,
                fallback_reason=reason,
                model=self._client.model,
            )
            set_parser_span_attributes(
                span,
                mode="deterministic_fallback",
                fallback_used=True,
                confidence=None,
                fallback_reason=reason,
                model=self._client.model,
                status="fallback",
            )
```

Before successful LLM return:

```python
        record_parse_result(
            mode="llm",
            status="success",
            duration_seconds=time.perf_counter() - started,
            confidence=parsed["confidence"],
            model=self._client.model,
        )
        set_parser_span_attributes(
            span,
            mode="llm",
            fallback_used=False,
            confidence=parsed["confidence"],
            fallback_reason=None,
            model=self._client.model,
            status="success",
        )
```

For empty-filter and low-confidence fallbacks, call `record_parse_result` with:

```python
mode="deterministic_fallback"
status="fallback"
fallback_reason="empty_filters" or "low_confidence"
confidence=parsed["confidence"]
```

Do not add raw query text, prompts, or raw LLM responses to metric labels or trace attributes.

- [ ] **Step 6: Run tests and lint**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability_parser.py tests/test_observability.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/ai/parser.py app/ai/retry.py app/observability tests/test_observability_parser.py
```

Expected: PASS.

---

## Task 6: Conditions Refresh And Freshness Telemetry

**Files:**

- Create: `app/observability/jobs.py`
- Modify: `app/data/refresh_conditions.py`
- Test: `tests/test_observability.py`

- [ ] **Step 1: Add failing job telemetry tests**

Append to `tests/test_observability.py`:

```python
from datetime import UTC, datetime, timedelta

from app.observability.jobs import record_conditions_refresh_result, seconds_since


def test_seconds_since_returns_age_in_seconds():
    now = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    then = now - timedelta(hours=2, minutes=30)

    assert seconds_since(then.isoformat(), now=now) == 9000


def test_conditions_refresh_result_records_success_and_age():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    try:
        record_conditions_refresh_result(
            source="open-meteo",
            status="success",
            updated_at="2026-01-15T10:00:00+00:00",
            now=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        )
    finally:
        reset_metrics_recorder_for_tests()

    assert (
        "snowcast_conditions_refresh_success_total",
        {"source": "open-meteo"},
        1,
    ) in recorder.counters
    assert (
        "snowcast_conditions_refresh_age_seconds",
        {"source": "open-meteo"},
        7200,
    ) in recorder.gauges
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
```

Expected: FAIL because `app.observability.jobs` does not exist.

- [ ] **Step 3: Implement job telemetry helpers**

Create `app/observability/jobs.py`:

```python
from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from app.observability.metrics import get_metrics_recorder
from app.observability.tracing import start_span


@contextmanager
def job_span(name: str, *, attributes: dict[str, str | int | float | bool] | None = None) -> Iterator[None]:
    started = time.perf_counter()
    status = "success"
    with start_span(f"job.{name}", attributes):
        try:
            yield
        except Exception:
            status = "failure"
            raise
        finally:
            get_metrics_recorder().observe(
                f"snowcast_{name}_duration_seconds",
                time.perf_counter() - started,
                {"status": status},
            )


def record_conditions_refresh_result(
    *,
    source: str,
    status: str,
    updated_at: str | None = None,
    reason: str | None = None,
    now: datetime | None = None,
) -> None:
    recorder = get_metrics_recorder()
    if status == "success":
        recorder.increment(
            "snowcast_conditions_refresh_success_total",
            {"source": source},
        )
        age_seconds = seconds_since(updated_at, now=now)
        if age_seconds is not None:
            recorder.gauge(
                "snowcast_conditions_refresh_age_seconds",
                age_seconds,
                {"source": source},
            )
        return
    recorder.increment(
        "snowcast_conditions_refresh_failure_total",
        {"source": source, "reason": reason or "unknown"},
    )


def seconds_since(value: str | None, *, now: datetime | None = None) -> float | None:
    if value is None:
        return None
    reference = now or datetime.now(UTC)
    observed = datetime.fromisoformat(value)
    return (reference - observed).total_seconds()
```

- [ ] **Step 4: Instrument refresh jobs lightly**

In `app/data/refresh_conditions.py`, import:

```python
from app.observability.jobs import record_conditions_refresh_result
```

After each successful conditions repository upsert call, call:

```python
record_conditions_refresh_result(
    source=normalized.source or "open-meteo",
    status="success",
    updated_at=normalized.updated_at,
)
```

In provider fetch/normalization exception paths, call:

```python
record_conditions_refresh_result(
    source="open-meteo",
    status="failure",
    reason=error.__class__.__name__,
)
```

Keep existing logs and CLI output unchanged.

Do not instrument `app/data/reconcile_recent_archive.py` in Sprint 35. It remains
post-Sprint 35 job telemetry work because the user-facing conditions freshness
alert is the first operational priority.

- [ ] **Step 5: Run tests and syntax checks**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config python -m py_compile app/data/refresh_conditions.py app/observability/jobs.py
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/refresh_conditions.py app/observability/jobs.py tests/test_observability.py
```

Expected: PASS.

---

## Task 7: Fly Config, Runbook, And Documentation

**Files:**

- Modify: `fly.toml`
- Create: `docs/observability-runbook.md`
- Modify: `docs/observability-plan.md`
- Modify: `docs/engineering-notes.md`
- Modify: `README.md`
- Modify: `PROJECT.md`

- [ ] **Step 1: Add Fly health checks**

Modify `fly.toml`:

```toml
[[http_service.checks]]
  interval = "30s"
  timeout = "5s"
  grace_period = "20s"
  method = "GET"
  path = "/api/healthz"

[[http_service.checks]]
  interval = "60s"
  timeout = "10s"
  grace_period = "30s"
  method = "GET"
  path = "/api/readyz"
```

Do not change `min_machines_running` in this task unless the user explicitly approves the cost/latency tradeoff.

- [ ] **Step 2: Create observability runbook**

Create `docs/observability-runbook.md`:

```markdown
# Observability Runbook

## Runtime Environment

Required only when telemetry export is enabled:

```text
OTEL_ENABLED=true
OTEL_SERVICE_NAME=snowcast
OTEL_EXPORTER_OTLP_ENDPOINT=<Grafana Cloud OTLP endpoint>
OTEL_EXPORTER_OTLP_HEADERS=<Grafana Cloud auth header>
OTEL_TRACES_SAMPLER_ARG=0.1
LOG_FORMAT=json
LOG_LEVEL=INFO
```

Local development can leave `OTEL_ENABLED=false`.

## First Checks

```bash
fly status --app snowcast
fly logs --app snowcast
curl -s https://snowcast.fly.dev/api/healthz
curl -s https://snowcast.fly.dev/api/readyz
```

## Slow Search

Symptoms:

- `/api/search` p95 > 4s for 10 minutes
- user reports search feels stuck

Check:

1. Dashboard panel: `snowcast_search_duration_seconds` p50/p95.
2. Dashboard panel: `snowcast_search_phase_duration_seconds` by phase.
3. Trace query: route `/api/search`, sort by longest duration.
4. Inspect spans:
   - `search.preload_raw_weather`
   - `search.preload_planning_snapshots`
   - `search.build_planning_context`
   - `search.assess_travel_effort`
   - `search.rank_results`

Likely causes:

- repeated database round trips
- cold Fly machine or cold Neon compute
- missing raw weather preloading
- route provider or LLM accidentally in hot path

## Parser/LLM Fallback Spike

Symptoms:

- `snowcast_parse_requests_total{mode="deterministic_fallback"}` spikes
- user sees low interpretation confidence

Check:

1. `snowcast_llm_requests_total` by model/status.
2. `snowcast_llm_retries_total` by reason.
3. `snowcast_llm_fallbacks_total` by reason.
4. Fly logs for `Parser falling back to heuristic parser`.

Do not log or paste raw user prompts into tickets or dashboards.

## Stale Conditions

Symptoms:

- `snowcast_conditions_refresh_age_seconds` > 28800
- search shows stale or missing current conditions

Check:

1. GitHub Actions refresh workflow status.
2. `fly logs --app snowcast` for readiness/database errors.
3. Neon availability and credentials.
4. Manual command:

```bash
uv run python -m app.data.refresh_conditions --database-url "$DATABASE_URL" --force
```

## Alerts

Initial thresholds:

- `/api/search` p95 > 4s for 10 minutes
- `/api/search` p50 > 2s for 10 minutes
- 5xx rate > 2% for 5 minutes
- parse fallback rate > 20% for 15 minutes
- conditions refresh age > 8 hours
- readiness failures
- machine restart loop or OOM
```

- [ ] **Step 3: Update README production env section**

Add:

```markdown
Optional observability environment variables:
- `OTEL_ENABLED=true` to enable OpenTelemetry instrumentation/export
- `OTEL_EXPORTER_OTLP_ENDPOINT` for the hosted OTLP endpoint
- `OTEL_EXPORTER_OTLP_HEADERS` for exporter auth headers
- `OTEL_TRACES_SAMPLER_ARG` for trace sampling, for example `0.1`
- `LOG_FORMAT=json` for structured logs

See [`docs/observability-runbook.md`](docs/observability-runbook.md).
```

- [ ] **Step 4: Update Sprint 35 status**

In `PROJECT.md`, change Sprint 35 from `planned` to `in progress` during implementation, then to `completed` after final verification. Add concise completion bullets only after implementation succeeds:

```markdown
- Added OpenTelemetry-backed request/search/parser/LLM instrumentation with no-op local defaults.
- Added structured JSON logs with request IDs and trace IDs.
- Added Fly health checks and an observability runbook.
```

- [ ] **Step 5: Run docs/config checks**

Run:

```bash
git diff --check -- fly.toml README.md PROJECT.md docs/engineering-notes.md docs/observability-plan.md docs/observability-runbook.md
```

Expected: PASS.

---

## Final Verification

Run after all tasks:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py tests/test_observability_search.py tests/test_observability_parser.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests/test_observability.py tests/test_observability_search.py tests/test_observability_parser.py
UV_CACHE_DIR=.uv-cache uv run --no-config python -m py_compile app/main.py app/observability/*.py app/domain/search_service.py app/ai/parser.py app/ai/retry.py app/data/refresh_conditions.py
git diff --check -- app pyproject.toml uv.lock fly.toml README.md PROJECT.md docs tests
```

If Docker/Postgres is running, also run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest -q
```

If local Postgres is not running, state that DB-backed pytest was not available and list the DB-free observability tests that passed.

Manual smoke:

```bash
LOG_FORMAT=json OTEL_ENABLED=false UV_CACHE_DIR=.uv-cache uv run --no-config uvicorn app.main:app --reload
curl -i "http://127.0.0.1:8000/api/healthz"
curl -s "http://127.0.0.1:8000/api/search?location=Italy&min_price=150&max_price=320&stars=1&skill_level=intermediate&travel_month=5"
```

Expected:

- `/api/healthz` returns `200`.
- response includes `x-request-id`.
- stdout logs are JSON when `LOG_FORMAT=json`.
- search returns results.
- no raw query text, prompts, tokens, or headers appear in logs.

## Self-Review Checklist

- Every metric label is low-cardinality.
- No raw query text, prompts, response bodies, auth headers, tokens, or origin text are logged as metric labels or trace attributes.
- Telemetry is disabled by default.
- Search response shape is unchanged.
- Parser debug response shape is unchanged.
- Fly checks use existing public health endpoints.
- Dependency changes were explicitly approved before editing `pyproject.toml`.
