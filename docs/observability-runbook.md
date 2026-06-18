# Observability Runbook

Snowcast uses an OpenTelemetry-first observability model for user-facing runtime
paths. Local development can leave telemetry export disabled; production should
emit structured logs and send traces/metrics to a hosted OTLP-compatible backend.

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

Local development can leave `OTEL_ENABLED=false`. `LOG_FORMAT=json` is
independent from telemetry export and can be enabled locally when inspecting log
shape.

Do not place raw trip briefs, identity tokens, LLM prompts, raw LLM responses,
provider page text, URLs, or exact user origins in logs, metric labels, or span
attributes.

## First Checks

```bash
fly status --app snowcast
fly logs --app snowcast
curl -s https://snowcast.fly.dev/api/healthz
curl -s https://snowcast.fly.dev/api/readyz
```

Use `/api/healthz` for process liveness and `/api/readyz` for database-backed
readiness. Readiness failures usually mean database connectivity, credentials,
or cold database compute rather than an application process crash.

## Dashboard Panels

Minimum useful dashboard:

- HTTP request rate by `route`, `method`, `status_class`
- HTTP request p50/p95 by `route`
- `/api/search` p50/p95 from `snowcast_search_duration_seconds`
- Search phase p50/p95 from `snowcast_search_phase_duration_seconds` by `phase`
- Search empty-result rate from `snowcast_search_empty_results_total`
- Parser mode/status from `snowcast_parse_requests_total`
- LLM request status and model from `snowcast_llm_requests_total`
- LLM retries from `snowcast_llm_retries_total`
- LLM fallback reason from `snowcast_llm_fallbacks_total`
- Conditions freshness from `snowcast_conditions_refresh_age_seconds`
- Conditions refresh success/failure counters
- Fly machine CPU, memory, restart count, proxy latency, and 5xx rate

The Snowcast production dashboard is managed from
`ops/grafana/dashboards/snowcast-production-overview.dashboard.json`. Validate
dashboard resources with:

```bash
uv run --no-config python ops/grafana/scripts/validate_dashboards.py
```

Deploy is manual-only until the flow is proven:

```bash
uv run --no-config python ops/grafana/scripts/deploy_dashboards.py --apply
```

Dashboard interpretation:

- Treat top-row `HTTP 5xx` as the user-impacting server-error signal. Route-level
  `4xx` panels are diagnostic because client/request-quality errors can be
  expected during normal product use.
- Treat empty or `No data` top-row panels as missing traffic or missing telemetry,
  not as green success. This is deliberate for low-traffic periods.
- Use `Search duration` and `Slow search phases (P95)` before route-level HTTP
  panels when investigating slow search.
- Use conditions freshness panels only after scheduled refresh jobs are exporting
  OTel metrics; no data there usually means job telemetry is not wired or has not
  run inside the selected time range.

Useful trace filters:

```text
route = "/api/search"
span name = "api.search"
span name starts with "search."
span attribute snowcast.search.window_type = "month|exact_dates|none"
```

## Slow Search

Symptoms:

- `/api/search` p95 above 4 seconds for 10 minutes
- user reports search feels stuck
- trace waterfall shows one dominant `search.*` span

Check:

1. `snowcast_search_duration_seconds` p50/p95.
2. `snowcast_search_phase_duration_seconds` by phase.
3. Longest `api.search` traces.
4. Fly CPU/memory/restarts around the same time.

Important spans:

```text
api.search
search.load_conditions_provider
search.load_history_repositories
search.preload_raw_weather
search.preload_planning_snapshots
search.assess_travel_effort
search.build_planning_context
search.rank_results
```

Likely causes:

- repeated database round trips or missing weather preloading
- cold Fly machine or cold database compute
- accidental provider call in the hot search path
- route provider or LLM accidentally added to `/api/search`
- large catalog growth without query/index review

First response:

```bash
fly logs --app snowcast | tail -200
curl -s "https://snowcast.fly.dev/api/search?location=Italy&min_price=150&max_price=320&stars=2&skill_level=intermediate&travel_month=3"
```

If the slow phase is raw-weather or planning-context related, inspect recent
weather-history rebuilds and repository query shape before tuning ranking code.

## Parser/LLM Fallback Spike

Symptoms:

- `snowcast_parse_requests_total{mode="deterministic_fallback"}` spikes
- users see low interpretation confidence or missing origin/date details
- `snowcast_llm_fallbacks_total` increases

Check:

1. `snowcast_llm_requests_total` by model/status.
2. `snowcast_llm_retries_total` by reason.
3. `snowcast_llm_fallbacks_total` by reason.
4. Logs for `Parser falling back to heuristic parser`.

Likely causes:

- provider quota/rate limit
- provider network errors
- model/schema incompatibility
- prompt/schema drift producing invalid JSON
- missing production `GEMINI_MODEL` or API key configuration

First response:

```bash
fly secrets list --app snowcast
fly logs --app snowcast | rg "Parser falling back|LLM call failed|query_parser"
```

Do not log or paste raw user prompts into incident notes. Use bounded labels:
`model`, `status`, `reason`, `mode`.

## Conditions Freshness

Symptoms:

- current conditions panel shows stale or missing data
- `snowcast_conditions_refresh_age_seconds` exceeds alert threshold
- refresh job reports failures

Check:

1. `snowcast_conditions_refresh_age_seconds` by `source`.
2. `snowcast_conditions_refresh_success_total`.
3. `snowcast_conditions_refresh_failure_total` by `reason`.
4. Scheduled job logs.

First response:

```bash
fly logs --app snowcast | rg "REFRESH|DONE|FAIL|open-meteo"
uv run --no-config python -m app.data.refresh_conditions --resort cervinia --force
```

Replace the resort with a known supported resort or ski-area ID. If the command
is run locally against production data, confirm `DATABASE_URL` points to the
intended database first.

## 5xx Spike Or Readiness Failures

Symptoms:

- `snowcast_http_requests_total{status_class="5xx"}` increases
- Fly readiness checks fail
- `/api/readyz` returns an error

Check:

1. Fly logs for stack traces.
2. Database availability and connection string.
3. Recent deploy and release-command output.
4. Whether failures are isolated to `/api/readyz` or affect user routes.

Commands:

```bash
fly status --app snowcast
fly releases --app snowcast
fly logs --app snowcast
curl -i https://snowcast.fly.dev/api/readyz
```

## Machine Restarts Or Cold Starts

Symptoms:

- Fly machine restart loop
- high startup latency after idle periods
- search latency varies heavily between first and later requests

Check:

1. Fly machine events and restart counts.
2. CPU/memory panels.
3. Whether `auto_stop_machines` and `min_machines_running = 0` are causing cold
   starts.

`min_machines_running = 1` is currently enabled in `fly.toml`. This should reduce
user-visible cold starts and make search-latency panels easier to interpret, but
it still has a cost tradeoff.

## Alert Candidates

Start with few alerts:

- `/api/search` p95 > 4s for 10 minutes
- `/api/search` p50 > 2s for 10 minutes
- HTTP 5xx rate > 2% for 5 minutes
- parse fallback rate > 20% for 15 minutes
- LLM error/rate-limit spike
- empty-result rate > 30% for common searches
- conditions refresh age > 8 hours
- readiness check failures
- machine restart loop or OOM

Each alert should link back to the relevant section in this runbook.
