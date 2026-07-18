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
OTEL_TRACES_SAMPLER_ARG=1.0
LOG_FORMAT=json
LOG_LEVEL=INFO
```

Local development can leave `OTEL_ENABLED=false`. `LOG_FORMAT=json` is
independent from telemetry export and can be enabled locally when inspecting log
shape.

Scheduled GitHub Actions jobs should use the same OTLP endpoint and auth header,
but set `OTEL_SERVICE_NAME=snowcast-jobs`. Dashboard queries intentionally cover
both `snowcast` and `snowcast-jobs` so app request telemetry and operator job
telemetry can be viewed together.

Keep production trace sampling at `1.0` while Snowcast traffic is low. Complete
Tempo coverage is more useful than sampling cost reduction at this stage because
slow search investigations often need one specific trace waterfall. Revisit this
only after real traffic makes trace volume meaningful, preferably with collector
or tail-sampling policy rather than blind request sampling.

Health and readiness endpoints are excluded from FastAPI tracing; they remain
available through HTTP metrics and Fly health checks, but they should not crowd
Tempo trace searches.

The dashboard's Tempo panels use TraceQL and TraceQL metrics. Grafana Cloud
supports these through the Tempo datasource; if a future self-hosted Tempo stack
is used, confirm TraceQL metrics support before relying on those panels.

Do not place raw trip briefs, identity tokens, LLM prompts, raw LLM responses,
provider page text, URLs, or exact user origins in logs, metric labels, or span
attributes.

## First Checks

```bash
fly status --app snowcast
fly logs --app snowcast
curl -s https://snowcast.fly.dev/api/healthz
curl -s https://snowcast.fly.dev/api/readyz
curl -s https://snowcast.fly.dev/api/search-readiness
```

Use `/api/healthz` for process liveness and `/api/readyz` for database-backed
readiness. Readiness failures usually mean database connectivity, credentials,
or cold database compute rather than an application process crash.

Use `/api/search-readiness` for product readiness. It checks database access,
catalog availability, Search V4 policy/registry integrity, and latest forecast
heads. A response is `degraded` when forecast heads are missing, stale, or
partial; search remains available through its climatology fallback.

## Dashboard Panels

Minimum useful dashboard:

- HTTP request rate by `route`, `method`, `status_class`
- HTTP request p50/p95 by `route`
- `/api/search` p50/p95 from `snowcast_search_duration_seconds`
- Search phase p50/p95 from `snowcast_search_phase_duration_seconds` by `phase`
- Search empty-result rate from `snowcast_search_empty_results_total`
- Parser mode/status from `snowcast_parse_requests_total`
- LLM request status and model from `snowcast_llm_requests_total`
- Bounded LLM provider failure class from `snowcast_llm_failures_total`
- LLM retries from `snowcast_llm_retries_total`
- LLM fallback reason from `snowcast_llm_fallbacks_total`
- Search refinement status and bounded reason from
  `snowcast_search_refinement_requests_total`, plus admission and route outcomes
  from `snowcast_search_refinement_route_outcomes_total`
- Evaluated-baseline handoff health from
  `snowcast_search_refinement_snapshot_outcomes_total`; watch the bounded
  `hit`, `miss`, `expired`, `intent_mismatch`, and `evicted` outcomes
- Forecast refresh status, incomplete-area count, head age, and valid-date
  count from the `snowcast_weather_forecast_*` metrics
- Conditions freshness from
  `snowcast_conditions_refresh_updated_timestamp_seconds`, computed in Grafana as
  current time minus the last recorded refresh timestamp
- Conditions refresh success/failure counters
- Data-quality completeness by domain from `snowcast_data_completeness_ratio`
- Historical archive missing-day aggregates from `snowcast_data_missing_days`
- Historical archive drilldown from `snowcast_archive_coverage_ratio`,
  `snowcast_archive_missing_days_by_ski_area`, and
  `snowcast_archive_last_observed_timestamp_seconds`
- Derived climatology weak groups from
  `snowcast_climatology_weak_coverage_groups`
- Climatology drilldown from `snowcast_climatology_coverage_ratio`,
  `snowcast_climatology_missing_rows_by_ski_area`, and
  `snowcast_climatology_gap_count`
- Catalog required-field gaps from `snowcast_catalog_field_groups`
- Catalog required-field drilldown from `snowcast_catalog_gap_count`
- Catalog source-trust gaps from `snowcast_catalog_trust_status`
- Catalog source-trust drilldown from `snowcast_trust_gap_count`
- Tempo search phase p95 from TraceQL metrics for sampled `search.*` spans
- Recent slow `api.search` traces above five seconds
- Fly machine CPU, memory, restart count, proxy latency, and 5xx rate

The Snowcast production dashboard is managed from
`ops/grafana/dashboards/snowcast-production-overview.dashboard.json`. The
operator drilldown dashboard for exact resort/ski-area data gaps is managed from
`ops/grafana/dashboards/snowcast-data-quality.dashboard.json`. Validate
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
- Use `Domain search duration` and `Slow search phases (P95)` before route-level
  HTTP panels when investigating slow search. The domain timer measures
  `search_resorts`; full `/api/search` HTTP timing also includes FastAPI request
  handling, response model construction, JSON serialization, and middleware
  overhead.
- Use `Search HTTP vs domain timing` when the HTTP panel looks materially slower
  than the domain search panel. A sustained gap means the overhead is outside the
  ranking/search phases; sparse low-traffic histograms can also exaggerate p95
  when a request lands in a wide bucket.
- Use the `Trace Drilldown` row to confirm a slow metric phase against the
  sampled trace waterfall. Metric panels are the first alerting signal; Tempo
  panels show whether the slow phase belongs to one trace or a repeated pattern.
- Use conditions freshness panels only after scheduled refresh jobs are exporting
  OTel metrics; no data there usually means job telemetry is not wired or has not
  run inside the selected time range.
- Use the production dashboard data-quality panels as a summary alarm. Use the
  `Snowcast Data Quality` dashboard for bounded resort/ski-area drilldowns. The
  full date-level evidence still lives in the uploaded `data-quality-report.md`
  and `data-quality-summary.json` artifacts.

Useful trace filters:

```text
route = "/api/search"
span name = "api.search"
span name starts with "search."
span attribute snowcast.search.window_type = "month|exact_dates|none"
```

Useful TraceQL snippets:

```text
{ resource.service.name = "snowcast" && span:name = "api.search" && span:duration > 5s }
{ resource.service.name = "snowcast" && span:name =~ "search\\..*" }
{ resource.service.name = "snowcast" && span:name = "llm.query_parser" }
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
search.static_factor_evaluation
search.weather_preload
search.weather_factor_evaluation
search.ranking
search.refinement
```

Likely causes:

- repeated database round trips or broken bulk weather preloading
- cold Fly machine or cold database compute
- accidental provider call in the hot search path
- a slow optional refinement LLM request
- repeated refinement snapshot misses after deploys, restarts, expiry, or
  routing a request to a different process
- large catalog growth without query/index review

First response:

```bash
fly logs --app snowcast | tail -200
curl --fail --silent --show-error \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{"intent":{"constraints":{"location":{"country":"Italy"},"travel_window":{"month":3}},"party":{"skill_levels":["intermediate"]}},"generate_refinements":false}' \
  https://snowcast.fly.dev/api/search
```

If `weather_preload` is slow, inspect the climatology and forecast latest-head
bulk queries before tuning ranking code. If `refinement` is slow, inspect LLM
telemetry and the refinement snapshot hit rate. A miss never reruns Search V4;
it returns `temporarily_unavailable`, while a successful new ranking creates a
fresh 60-second handoff.

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
- timestamp-derived conditions age exceeds alert threshold
- refresh job reports failures

Check:

1. `snowcast_conditions_refresh_updated_timestamp_seconds` by `source`.
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

## Trip-Window Forecast Freshness

Symptoms:

- `/api/search-readiness` reports `forecast_heads=missing_or_partial` or
  `stale_or_partial`
- target-date searches show forecast-unavailable warnings and fall back to
  climatology
- refresh telemetry reports failed or incomplete ski areas

Check:

1. `snowcast_weather_forecast_refresh_total` by `source_key` and `status`.
2. `snowcast_weather_forecast_incomplete_ski_areas` by source.
3. `snowcast_weather_forecast_head_age_seconds` against the provider update
   interval.
4. `snowcast_weather_forecast_valid_date_count` for expected source horizon.
5. The `Refresh Weather Forecasts` GitHub Actions run and provider errors.

First response:

```bash
uv run python -m app.data.refresh_weather_forecasts \
  --database-url "$DATABASE_URL"
curl -s https://snowcast.fly.dev/api/search-readiness
```

Do not mutate forecast heads manually. A complete refresh advances them
atomically; partial area failures deliberately keep the previous heads.

## Data Quality Audit

Symptoms:

- data completeness ratio drops below the expected baseline
- historical archive missing days appear after a backfill or reconciliation run
- climatology weak groups appear after a derived rebuild
- catalog field gaps or source-trust gaps increase after catalog edits

Check:

1. `snowcast_data_completeness_ratio` by `domain`.
2. `snowcast_data_completeness_entities` by `domain` and `status`.
3. `snowcast_data_missing_days` by `elevation_band`.
4. `snowcast_archive_missing_days_by_ski_area` by `ski_area_id` and
   `elevation_band`.
5. `snowcast_archive_coverage_ratio` by `ski_area_id` and `elevation_band`.
6. `snowcast_archive_last_observed_timestamp_seconds` by `ski_area_id` and
   `elevation_band`.
7. `snowcast_climatology_weak_coverage_groups` by `source_model` and
   `baseline_period`.
8. `snowcast_climatology_coverage_ratio` and
   `snowcast_climatology_gap_count` by `ski_area_id`, `elevation_band`,
   `baseline_period`, and `source_model`.
9. `snowcast_catalog_field_groups` by `field_group` and `status`.
10. `snowcast_catalog_gap_count` by `resort_id`, `field_group`, and `status`.
11. `snowcast_catalog_trust_status` by `field_group` and `trust_status`.
12. `snowcast_trust_gap_count` by `resort_id`, `field_group`, and
   `trust_status`.
13. The latest `data-quality-report.md` GitHub Actions artifact for the concrete
   resort/field list.

Manual local command:

```bash
uv run --no-config python -m app.data.audit_data_quality \
  --database-url "$DATABASE_URL" \
  --archive-start-date 1991-01-01 \
  --archive-end-date 2026-03-01 \
  --output-dir artifacts/data-quality
```

If `--archive-end-date` is omitted, the audit infers it from the latest
`raw_weather_history` archive row and records a warning in the artifact. Use an
explicit end date after large backfills when you want the audit expectation to
match a known operator target.

Metric labels deliberately stop at bounded groups and stable catalog IDs:
`domain`, `field_group`, `status`, `trust_status`, `elevation_band`,
`source_model`, `baseline_period`, `resort_id`, and `ski_area_id`. Do not add
resort names, source URLs, source pages, date ranges, raw issue text, or raw
evidence strings as metric labels; keep those in the Markdown/JSON artifacts.

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

## Product Canary And Alerts

The `Product Canary` GitHub Actions workflow runs every 6 hours and can also be
started manually. It checks:

- `/api/healthz`
- `/api/readyz`
- `/api/search-readiness`
- one representative anonymous search with origin, month, price, quality, and
  skill filters

Local command:

```bash
uv run --no-config python ops/canary/search_canary.py \
  --base-url https://snowcast.fly.dev \
  --latency-threshold-seconds 15
```

The `Parse Canary` workflow runs daily and can also be started manually. It
posts one representative free-text query through `/api/parse-query` so parser
telemetry has an explicit production check without making every product canary
invoke the LLM path.

Local parse canary:

```bash
uv run --no-config python ops/canary/parse_canary.py \
  --base-url https://snowcast.fly.dev
```

Repo-managed Grafana alerting resources live under `ops/grafana/alerting/`.
Validate them without credentials:

```bash
uv run --no-config python ops/grafana/scripts/validate_alerts.py
```

Deploy is manual-only:

```bash
GRAFANA_DASHBOARD_NAMESPACE="stacks-1693732" \
GRAFANA_ALERT_EMAIL_TO="owner@example.com" \
uv run --no-config python ops/grafana/scripts/deploy_alerts.py --apply
```

The alert deployer creates or updates the repo-owned `Snowcast Alerts` folder
before contact points and rules. GitHub Actions apply runs therefore need
`GRAFANA_DASHBOARD_NAMESPACE` in addition to `GRAFANA_URL`,
`GRAFANA_SERVICE_ACCOUNT_TOKEN`, and `GRAFANA_ALERT_EMAIL_TO`.

Current alert rules:

- search p95 warning: `> 6s` for 10 minutes
- search p95 critical: `> 12s` for 10 minutes
- API 5xx critical: `> 5%` for 5 minutes, excluding health/readiness endpoints
- empty searches warning: `> 30%` over 30 minutes
- parse success warning: `< 90%` over 30 minutes when parse traffic is present
- conditions stale warning: `> 30h`
- conditions stale critical: `> 48h`
- conditions refresh failures warning: at least one failure in 6 hours
- LLM retries warning: at least one retry in 30 minutes
- search-readiness critical: any 5xx readiness failure in 15 minutes

The repo owns alert rules, the `Snowcast Alerts` folder, and the first owner
email contact point. Notification policy routing is intentionally not
overwritten by the deploy script because the Grafana policy API replaces the
whole routing tree. Route these rules to the `snowcast-owner-email` contact
point in the Grafana UI until policy management is moved to an explicit manifest
or Terraform.
