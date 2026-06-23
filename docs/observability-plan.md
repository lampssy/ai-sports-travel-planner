# Snowcast Observability Plan

Snowcast should make production behavior visible before a user reports that search
is slow, parsing is falling back, refresh data is stale, or an external provider
is failing. Observability should support a solo-builder workflow: low operating
overhead, clear signals, and enough request-level detail to debug real issues
without turning the project into an observability platform.

## Goals

- Detect `/api/search` latency regressions early.
- Explain slow searches by phase, for example raw weather preload, planning
  context construction, travel effort, parser calls, or ranking.
- Show whether query parsing used LLM extraction, deterministic parsing, or
  fallback behavior.
- Make LLM failures, retries, fallback use, and model selection visible.
- Track freshness of weather/conditions data and scheduled refresh jobs.
- Preserve privacy by avoiding raw user query text, auth tokens, LLM prompts,
  and secrets in logs, metrics, and traces.
- Keep the implementation backend-first and OpenTelemetry-compatible.

## Historical Gaps Addressed

Before the observability foundation landed, Snowcast had these operational gaps:

- Request logging was plain text and only recorded method, path, status, and
  total duration.
- Search had no phase-level timing, so slow requests could not be attributed to
  repositories, weather evidence, parser behavior, travel effort, or ranking.
- There were no custom metrics, traces, alert thresholds, or dashboard specs.
- Fly.io could show built-in app/proxy/machine metrics, but Snowcast did not
  expose product-level metrics.
- Scheduled jobs and LLM calls had local logs but no shared production telemetry
  model.

## Platform Direction

Use OpenTelemetry as the application instrumentation standard from the start.
Keep Fly.io built-in metrics as the infrastructure baseline, and send OTel
telemetry to a hosted backend rather than operating a self-hosted telemetry
stack.

Recommended initial backend:

- **Grafana Cloud** for OpenTelemetry metrics/traces/logs and dashboards.
- **Fly.io managed metrics/Grafana** for Fly proxy, machine, CPU, memory,
  restarts, and custom Prometheus metrics where useful.

Sentry can be added later if error triage and release regression workflows become
more important than keeping all telemetry in one Grafana-oriented backend.

Relevant platform references:

- Fly.io metrics and managed Grafana:
  <https://fly.io/docs/monitoring/metrics/>
- OpenTelemetry Python:
  <https://opentelemetry.io/docs/languages/python/>
- OpenTelemetry FastAPI instrumentation:
  <https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html>
- Grafana Cloud application observability:
  <https://grafana.com/docs/grafana-cloud/monitor-applications/application-observability/>

## Architecture

Add an observability package with narrow boundaries:

```text
app/observability/
  config.py       # env-driven enablement, service name, sampling, exporter config
  logging.py      # JSON logs, trace/request IDs, safe event helpers
  metrics.py      # counters, histograms, gauges, no-op fallback when disabled
  tracing.py      # manual span helpers and shared attribute names
  middleware.py   # request IDs, request logging, request metrics
```

Instrumentation layers:

- **Automatic**: FastAPI/ASGI requests, `httpx` outbound calls, `psycopg` DB
  calls where supported.
- **Manual domain spans**: search phases, parser decisions, LLM operations,
  refresh jobs, catalog curation validation, source diagnostics, future
  operational-status refresh/acquisition, and provider-specific boundaries.
- **Structured logs**: event-style JSON logs with request/trace IDs.
- **Metrics**: low-cardinality counters, histograms, and gauges for dashboards
  and alerts.

All observability helpers should degrade to no-op behavior when telemetry is not
configured, so local development and tests do not require external services.

## Core Metrics

HTTP:

```text
snowcast_http_requests_total{route,method,status_class}
snowcast_http_request_duration_seconds{route,method,status_class}
```

Search:

```text
snowcast_search_requests_total{parser_mode,has_origin,window_type}
snowcast_search_duration_seconds{parser_mode,has_origin,window_type}
snowcast_search_phase_duration_seconds{phase,window_type,has_origin}
snowcast_search_results_total{window_type,has_origin}
snowcast_search_empty_results_total{window_type,has_origin}
snowcast_search_cache_events_total{cache,result}
```

Parser and LLM:

```text
snowcast_parse_requests_total{mode,status}
snowcast_parse_duration_seconds{mode,status}
snowcast_parse_confidence{mode}
snowcast_llm_requests_total{operation,model,status}
snowcast_llm_duration_seconds{operation,model,status}
snowcast_llm_retries_total{operation,model,reason}
snowcast_llm_fallbacks_total{operation,reason}
```

Weather and scheduled jobs:

```text
snowcast_conditions_refresh_age_seconds
snowcast_conditions_refresh_success_total{source}
snowcast_conditions_refresh_failure_total{source,reason}
snowcast_raw_weather_backfill_duration_seconds{scope,status}
snowcast_catalog_curation_validation_duration_seconds{scope,status}
```

Cardinality rules:

- Allowed labels: route, method, status class, parser mode, operation, model,
  phase, status, source, window type, boolean flags.
- Avoid labels containing free text, resort names for high-volume metrics,
  origin names, exact dates, URLs, prompts, or full error messages.
- Use logs/traces for request-specific details instead of high-cardinality metric
  labels.

## Search Trace Model

Each `/api/search` request should have one request trace with spans such as:

```text
api.search
  search.load_catalog
  search.load_current_conditions
  search.filter_candidates
  search.preload_raw_weather
  search.preload_planning_snapshots
  search.build_planning_context
  search.assess_travel_effort
  search.rank_results
  search.build_response
```

Important trace attributes:

```text
snowcast.search.window_type = "month|exact_dates|none"
snowcast.search.has_origin = true|false
snowcast.search.candidate_resort_count = 12
snowcast.search.candidate_ski_area_count = 14
snowcast.search.result_count = 2
snowcast.search.empty_results = false
snowcast.search.raw_weather_cache = "hit|miss|partial"
snowcast.travel.provider = "approximate_haversine_v1"
```

For parser and combined search UX:

```text
snowcast.parser.mode = "llm|deterministic|deterministic_fallback"
snowcast.parser.fallback_used = true|false
snowcast.parser.fallback_reason = "llm_network_error|schema_validation|disabled|none"
snowcast.parser.confidence = 0.92
snowcast.llm.model = "gemini-3.1-flash-lite-preview"
snowcast.llm.status = "success|retry|error|fallback"
```

The recent search-latency issue should have been visible as a high
`snowcast_search_duration_seconds` p95 plus an oversized
`search.preload_raw_weather` or `search.build_planning_context` span.

## Logging Policy

Logs should be structured JSON on stdout so Fly can capture them and a log
backend can ingest them later.

Example:

```json
{
  "event": "search.completed",
  "level": "info",
  "request_id": "req_...",
  "trace_id": "...",
  "route": "/api/search",
  "duration_ms": 2671,
  "status_code": 200,
  "result_count": 2,
  "window_type": "month",
  "has_origin": true,
  "parser_mode": "llm"
}
```

Do not log:

- raw free-text trip briefs
- identity tokens or access tokens
- LLM prompts or full responses
- exact user origin text in general-purpose logs
- raw provider pages or extracted page text

Use sanitized fields such as `has_origin`, `window_type`, `country`, and
`parser_mode` instead.

## Fly.io Integration

Fly remains useful for infrastructure visibility:

- Built-in app/proxy latency and status metrics.
- Machine CPU, memory, restarts, exits, and OOM indicators.
- `fly logs --app snowcast` for immediate operational inspection.
- Health and readiness endpoints for deploy/routing safety.

Sprint 35 Fly changes:

- Add health checks for `/api/healthz` and `/api/readyz`.
- Consider `min_machines_running = 1` for production if cold starts make search
  latency hard to interpret.
- Add a custom metrics endpoint only if Prometheus scraping remains useful next
  to OTLP. The OTel path is primary; Prometheus-on-Fly can be a secondary
  dashboard/alert path.

## Alert Candidates

Initial alerts should be few and actionable:

- `/api/search` p95 above 4 seconds for 10 minutes.
- `/api/search` p50 above 2 seconds for 10 minutes.
- 5xx rate above 2% for 5 minutes.
- Parse fallback rate above 20% for 15 minutes.
- LLM error or rate-limit warning spike.
- Empty-result rate above 30% for common searches.
- Conditions refresh age above 8 hours.
- Readiness failures.
- Machine restart loop or OOM.

Alerts should link to a runbook section with the dashboard, trace query, likely
causes, and first commands to run.

## Implementation Status

The observability foundation has landed for the main user-facing runtime path.
The search latency issue exposed a real operational blind spot, and adding more
product surfaces without request-level visibility would make future regressions
harder to debug.

Completed foundation:

- OpenTelemetry-first runtime bootstrap
- structured request logs
- HTTP, search, parser, LLM, and freshness metrics
- Fly health checks
- production observability runbook

Remaining backlog: expand telemetry to skill-led catalog curation validation
and reporting, future operational-status acquisition, richer alerting, log
export, and optional Sentry. The central backlog item lives in
`docs/product-backlog.md`.

## Foundation Scope And Remaining Work

Original priority grouping:

P0:

- Add `app/observability/` with OTel setup, no-op behavior when disabled, and
  common attributes.
- Instrument FastAPI request traces and request duration metrics.
- Add request IDs and trace IDs to structured JSON logs.
- Add manual spans and phase metrics for `/api/search`.
- Add parser/LLM mode metrics and trace attributes.
- Add Fly health-check configuration and document production env vars.
- Add `docs/observability-runbook.md` with dashboards, alert thresholds, and
  first-response playbooks.

P1:

- Instrument `httpx` and `psycopg` automatically where dependency overhead stays
  reasonable.
- Add telemetry to conditions refresh and recent archive reconciliation jobs.
- Add dashboard definitions or at least exact dashboard panel queries.
- Add basic alert definitions for search latency, 5xx rate, parser fallback
  spikes, LLM errors, and stale conditions.

P2:

- Add catalog curation validation and reporting telemetry for validation run
  duration, source-diagnostic outcomes, and proposed patch counts.
- Add future operational-status acquisition telemetry for live/status
  observation run duration, provider failures, and freshness.
- Add log export if Fly's native log search is not enough.
- Add Sentry if error ownership, release tracking, or issue triage becomes worth
  the extra tool.

## Acceptance Criteria

- A slow `/api/search` request can be diagnosed from one trace waterfall.
- Search p50/p95 latency is visible by route and by search window type.
- Search phase duration is visible, including raw weather, planning context,
  travel effort, and response building.
- The dashboard shows whether parsing is LLM-backed, deterministic, or fallback.
- LLM model, status, retries, and fallback count are visible without exposing
  prompts or user text.
- Current conditions freshness is visible and alertable.
- Local/test runs do not require a telemetry backend.
- Production setup is documented with exact env vars and first debug commands.

## Implementation References

- Runtime helpers: [`app/observability/`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/observability/)
- Search instrumentation: [`app/domain/search_service.py`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/domain/search_service.py)
- Parser/LLM instrumentation: [`app/ai/parser.py`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/ai/parser.py) and [`app/ai/retry.py`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/ai/retry.py)
- Conditions freshness telemetry: [`app/data/refresh_conditions.py`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/app/data/refresh_conditions.py)
- Operations runbook: [`docs/observability-runbook.md`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/docs/observability-runbook.md)
