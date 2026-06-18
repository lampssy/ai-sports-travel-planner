import json
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.models import ResortConditions
from app.observability.config import (
    ObservabilitySettings,
    load_observability_settings,
)
from app.observability.context import current_request_id, request_id_context
from app.observability.jobs import record_conditions_refresh_result, seconds_since
from app.observability.logging import JsonLogFormatter, safe_log_extra
from app.observability.metrics import (
    InMemoryMetricsRecorder,
    OpenTelemetryMetricsRecorder,
    get_metrics_recorder,
    reset_metrics_recorder_for_tests,
    set_metrics_recorder_for_tests,
)
from app.observability.middleware import add_observability_middleware
from app.observability.otel import (
    HEALTHCHECK_TRACE_EXCLUDED_URLS,
    _metric_views,
    _parse_otlp_headers,
    configure_observability,
)
from app.observability.tracing import configure_tracer, set_span_attributes, start_span


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
        active_recorder = get_metrics_recorder()
        active_recorder.increment("snowcast_test_total", {"status": "ok"})
        active_recorder.observe("snowcast_test_seconds", 1.25, {"phase": "test"})

        assert recorder.counters == [("snowcast_test_total", {"status": "ok"}, 1)]
        assert recorder.histograms == [
            ("snowcast_test_seconds", {"phase": "test"}, 1.25)
        ]
    finally:
        reset_metrics_recorder_for_tests()


def test_configure_observability_disabled_is_noop(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    app = FastAPI()

    try:
        settings = configure_observability(app)

        assert settings.enabled is False
        get_metrics_recorder().increment("snowcast_test_total")
        assert recorder.counters == [("snowcast_test_total", {}, 1)]
    finally:
        reset_metrics_recorder_for_tests()


def test_configure_observability_enabled_without_endpoint_is_safe(monkeypatch):
    import app.observability.otel as otel

    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setattr(otel, "_runtime_configured", False)
    monkeypatch.setattr(otel, "_configured_signature", None)
    monkeypatch.setattr(otel, "_global_instrumentors_configured", False)
    monkeypatch.setattr(otel.trace, "set_tracer_provider", lambda _provider: None)
    monkeypatch.setattr(otel.metrics, "set_meter_provider", lambda _provider: None)
    monkeypatch.setattr(otel.trace, "get_tracer", lambda _name: object())
    monkeypatch.setattr(otel.metrics, "get_meter", lambda _name: object())
    monkeypatch.setattr(
        otel.FastAPIInstrumentor,
        "instrument_app",
        lambda _app, **_kwargs: None,
    )
    monkeypatch.setattr(
        otel.LoggingInstrumentor,
        "instrument",
        lambda _self, set_logging_format=False: None,
    )
    monkeypatch.setattr(otel.PsycopgInstrumentor, "instrument", lambda _self: None)
    monkeypatch.setattr(otel.URLLibInstrumentor, "instrument", lambda _self: None)
    app = FastAPI()

    try:
        settings = configure_observability(app)
    finally:
        configure_tracer(None)
        reset_metrics_recorder_for_tests()

    assert settings.enabled is True
    assert settings.otlp_endpoint is None


def test_configure_observability_enabled_is_idempotent(monkeypatch):
    import app.observability.otel as otel

    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setattr(otel, "_runtime_configured", False)
    monkeypatch.setattr(otel, "_configured_signature", None)
    monkeypatch.setattr(otel, "_global_instrumentors_configured", False)
    provider_calls: list[str] = []
    monkeypatch.setattr(
        otel.trace,
        "set_tracer_provider",
        lambda _provider: provider_calls.append("trace"),
    )
    monkeypatch.setattr(
        otel.metrics,
        "set_meter_provider",
        lambda _provider: provider_calls.append("metrics"),
    )
    monkeypatch.setattr(otel.trace, "get_tracer", lambda _name: object())
    monkeypatch.setattr(otel.metrics, "get_meter", lambda _name: object())
    monkeypatch.setattr(
        otel.FastAPIInstrumentor,
        "instrument_app",
        lambda _app, **_kwargs: None,
    )
    monkeypatch.setattr(
        otel.LoggingInstrumentor,
        "instrument",
        lambda _self, set_logging_format=False: None,
    )
    monkeypatch.setattr(otel.PsycopgInstrumentor, "instrument", lambda _self: None)
    monkeypatch.setattr(otel.URLLibInstrumentor, "instrument", lambda _self: None)

    try:
        configure_observability(FastAPI())
        configure_observability(FastAPI())
    finally:
        configure_tracer(None)
        reset_metrics_recorder_for_tests()

    assert provider_calls == ["trace", "metrics"]


def test_configure_observability_excludes_healthcheck_traces(monkeypatch):
    import app.observability.otel as otel

    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setattr(otel, "_runtime_configured", False)
    monkeypatch.setattr(otel, "_configured_signature", None)
    monkeypatch.setattr(otel, "_global_instrumentors_configured", False)
    monkeypatch.setattr(otel.trace, "set_tracer_provider", lambda _provider: None)
    monkeypatch.setattr(otel.metrics, "set_meter_provider", lambda _provider: None)
    monkeypatch.setattr(otel.trace, "get_tracer", lambda _name: object())
    monkeypatch.setattr(otel.metrics, "get_meter", lambda _name: object())
    instrument_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        otel.FastAPIInstrumentor,
        "instrument_app",
        lambda _app, **kwargs: instrument_calls.append(kwargs),
    )
    monkeypatch.setattr(
        otel.LoggingInstrumentor,
        "instrument",
        lambda _self, set_logging_format=False: None,
    )
    monkeypatch.setattr(otel.PsycopgInstrumentor, "instrument", lambda _self: None)
    monkeypatch.setattr(otel.URLLibInstrumentor, "instrument", lambda _self: None)

    try:
        configure_observability(FastAPI())
    finally:
        configure_tracer(None)
        reset_metrics_recorder_for_tests()

    assert instrument_calls == [{"excluded_urls": HEALTHCHECK_TRACE_EXCLUDED_URLS}]


def test_metric_views_use_domain_specific_histogram_buckets():
    views_by_name = {view._instrument_name: view for view in _metric_views()}

    assert views_by_name[
        "snowcast_search_phase_duration_seconds"
    ]._aggregation._boundaries == (
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.0,
        3.0,
        5.0,
        8.0,
        13.0,
        21.0,
        34.0,
    )
    assert views_by_name["snowcast_parse_confidence"]._aggregation._boundaries == (
        0.0,
        0.25,
        0.5,
        0.7,
        0.8,
        0.9,
        0.95,
        0.99,
        1.0,
    )
    assert views_by_name["snowcast_search_results_total"]._aggregation._boundaries == (
        0.0,
        1.0,
        2.0,
        3.0,
        5.0,
        10.0,
        20.0,
        50.0,
    )


def test_parse_otlp_headers_decodes_standard_encoded_values():
    headers = _parse_otlp_headers("Authorization=Basic%20abc%3D%3D,x-test=value")

    assert headers["authorization"] == "Basic abc=="
    assert headers["x-test"] == "value"


def test_opentelemetry_metrics_recorder_uses_observable_gauge():
    class FakeMeter:
        def __init__(self) -> None:
            self.gauge_callbacks = []

        def create_observable_gauge(
            self,
            name,
            callbacks=None,
            unit="",
            description="",
        ):
            self.gauge_callbacks.extend(callbacks or [])
            return object()

    meter = FakeMeter()
    recorder = OpenTelemetryMetricsRecorder(meter)

    recorder.gauge("snowcast_test_current", 42, {"phase": "test"})

    observations = list(meter.gauge_callbacks[0](None))
    assert observations[0].value == 42
    assert observations[0].attributes == {"phase": "test"}


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


def test_request_middleware_uses_bounded_unknown_route_label():
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    app = FastAPI()
    add_observability_middleware(app)

    try:
        response = TestClient(app).get("/missing/raw-user-path")
    finally:
        reset_metrics_recorder_for_tests()

    assert response.status_code == 404
    assert recorder.counters == [
        (
            "snowcast_http_requests_total",
            {"route": "__unknown__", "method": "GET", "status_class": "4xx"},
            1,
        )
    ]


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


def test_refresh_conditions_records_age_for_skipped_fresh_rows(monkeypatch):
    import app.data.refresh_conditions as refresh_module

    observed_at = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    existing_conditions = ResortConditions(
        resort_name="Test Ski Area",
        snow_confidence_score=0.8,
        snow_confidence_label="good",
        availability_status="open",
        weather_summary="Fresh conditions.",
        conditions_score=0.8,
        updated_at="2026-01-15T10:00:00+00:00",
        source="open-meteo",
    )

    class FakeResortRepository:
        def __init__(self, _database_url: str) -> None:
            pass

        def list_resorts(self):
            return (
                SimpleNamespace(
                    resort_id="test-resort",
                    name="Test Resort",
                    ski_areas=[
                        SimpleNamespace(
                            ski_area_id="test-ski-area",
                            name="Test Ski Area",
                        )
                    ],
                ),
            )

    class FakeConditionsRepository:
        def __init__(self, _database_url: str) -> None:
            pass

        def get_conditions_for_ski_area(self, _name: str):
            return existing_conditions

    class FakeHistoryRepository:
        def __init__(self, _database_url: str) -> None:
            pass

    monkeypatch.setattr(refresh_module, "ResortRepository", FakeResortRepository)
    monkeypatch.setattr(
        refresh_module,
        "ResortConditionsRepository",
        FakeConditionsRepository,
    )
    monkeypatch.setattr(
        refresh_module,
        "ResortConditionHistoryRepository",
        FakeHistoryRepository,
    )
    monkeypatch.setattr(
        refresh_module,
        "RawWeatherHistoryRepository",
        FakeHistoryRepository,
    )
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)

    try:
        result = refresh_module.refresh_conditions(
            database_url="postgresql://test",
            client=object(),
            now=observed_at,
        )
    finally:
        reset_metrics_recorder_for_tests()

    assert result.skipped_fresh == 1
    assert (
        "snowcast_conditions_refresh_age_seconds",
        {"source": "open-meteo"},
        7200,
    ) in recorder.gauges
