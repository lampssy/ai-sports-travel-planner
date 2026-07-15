# Production Runbook

## Required secrets

- Fly:
  - `FLY_API_TOKEN` for GitHub Actions deploys
- Fly runtime:
  - `DATABASE_URL` pointing to the Neon production database
  - `GEMINI_API_KEY`
  - optional `GEMINI_MODEL`
- GitHub Actions:
  - `DATABASE_URL` for scheduled/manual current-conditions, forecast,
    climatology, audit, and retention workflows

## Local setup

1. Start Postgres:
```bash
docker compose up -d postgres
```
2. Create local env:
```bash
cp .env.example .env
```
3. Install dependencies:
```bash
UV_CACHE_DIR=.uv-cache uv sync --dev --no-config
cd frontend && npm install && cd ..
```
4. Run tests:
```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest
```
5. Run the built app:
```bash
cd frontend && npm run build && cd ..
./scripts/run-built-app.sh
```

## Bootstrap and refresh

- Fly runs schema creation and seed sync through the release command before new web machines serve traffic.
- Manual bootstrap:
```bash
uv run python -m app.data.bootstrap_database --database-url "$DATABASE_URL"
```
- Manual refresh:
```bash
uv run python -m app.data.refresh_conditions --database-url "$DATABASE_URL"
```
- Force refresh:
```bash
uv run python -m app.data.refresh_conditions --database-url "$DATABASE_URL" --force
```

## Deploy flow

- CI runs on push and pull request.
- Production deploy runs from `.github/workflows/deploy.yml` on push to `main`.
- Fly deploy command:
```bash
flyctl deploy --remote-only --app snowcast
```
- The deploy runs the Fly release command first:
  - `python -m app.data.bootstrap_database --database-url "$DATABASE_URL"`

## Search V4 policy management

Search has one active contract, `search-v4`, and one checked-in versioned
ranking policy. There is no runtime model-selection flag or V3 compatibility
route. Before deploying a policy or evaluator change, run:

```bash
uv run python -m app.data.explain_search_policy --check
uv run python -m app.data.audit_search_factor_readiness
uv run pytest -q tests/test_search_v4_golden.py
```

The first command rejects drift between
`app/config/search-ranking/search-v4.toml` and the generated inventory in
`docs/search-ranking-model.md`. Increment `ranking_policy_version` for a
weight, activation, curve, source-preference, or other numeric policy change.
Increment `search_model_version` only when the request/response or evaluation
algorithm contract changes.

There is no environment-only rollback. Revert the application and policy
together through source control. If a reverted image cannot read an already
deployed database schema, restore a matching database checkpoint as part of the
same rollback.

## Trip-market catalog cutover

Rehearse this sequence against a disposable/test database before production:

```bash
pg_dump "$DATABASE_URL" --format=custom \
  --file "snowcast-pre-trip-market-$(date +%Y%m%d%H%M%S).dump"
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.verify_catalog_evidence \
  --write-snapshot /tmp/snowcast-evidence-before.json
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.bootstrap_database \
  --catalog-path app/data/catalog.json
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.verify_catalog_evidence \
  --compare-snapshot /tmp/snowcast-evidence-before.json
```

The comparison rejects newly introduced ski-area IDs by default. If the new
catalog intentionally adds areas, inspect each reported ID and repeat the
comparison with one `--allow-new-area <ski_area_id>` flag per expected addition.
An allowed new area must still have zero evidence rows; the command fails if
evidence was unexpectedly attached to it.

Bootstrap preserves `raw_weather_history`, `ski_area_snow_climatology_daily`,
`resort_conditions`, and `resort_condition_history` by stable `ski_area_id`.
The one-time upgrade clears disposable saved-trip/event/click rows while
removing destination-owned compatibility tables and columns.

## Refresh process

- Conditions refresh is scheduled by GitHub Actions, not by a resident Fly worker.
- Scheduled cadence: every 6 hours.
- In Worker / Function / Trigger terms:
  - trigger: GitHub Actions schedule or manual `workflow_dispatch`
  - function: refresh current resort conditions and freshness telemetry
  - worker: GitHub Actions runner executing the refresh command
- Manual operator runs happen through `workflow_dispatch` with:
  - optional `force=true`
  - optional comma-separated `ski_area_ids` and `stay_destination_ids`
- Manual refresh command shape remains:
```bash
uv run python -m app.data.refresh_conditions --database-url "$DATABASE_URL" \
  --force --stay-destination tignes
```

## Trip-window forecast refresh and retention

Versioned forecast acquisition is scheduled by GitHub Actions every six hours
at minute 25. It refreshes both configured source keys unless a manual dispatch
selects one:

```bash
uv run python -m app.data.refresh_weather_forecasts \
  --database-url "$DATABASE_URL"
```

Target one source or ski area with repeatable options:

```bash
uv run python -m app.data.refresh_weather_forecasts \
  --database-url "$DATABASE_URL" \
  --source ecmwf_ifs025_ensemble_mean \
  --ski-area tignes-ski-area
```

A refresh checks the provider model initialization before downloading area
rows. If that source cycle is already complete, it exits successfully with
`status=unchanged`. New runs remain immutable. Only complete per-area payloads
advance latest heads; a partial failure leaves the previous head intact for the
affected area.

Tiered retention runs weekly and can be invoked manually:

```bash
uv run python -m app.data.retain_weather_forecasts \
  --database-url "$DATABASE_URL"
```

Retention preserves all runs referenced by heads, all complete runs from the
last 45 days, one canonical run per source/day through two years, and one per
source/week through five years. Failed or rejected unreferenced runs are kept
for 90 days.

## Historical archive and climatology rebuild

Historical weather backfills are manual/operator-driven. Run them after
weather-critical ski-area coordinates and elevation bands are reviewed.

Recommended sequence:

1. Backfill `raw_weather_history` for the intended ski areas and date range.
2. Rebuild derived snow climatology from the raw archive.
3. Run a representative search and confirm planning evidence uses
   `snow_climatology` rather than raw-history or heuristic fallback.

Targeted local shape:

```bash
uv run python -m app.data.backfill_historical_weather --database-url "$DATABASE_URL" \
  --stay-destination tignes --start-date 1991-01-01 --end-date 2025-12-31 --rebuild
```

Large historical archive runs should be paced rather than retried aggressively.
The backfill client reuses HTTP connections, jitters successful-request and
retry waits, and applies a longer cooldown when repeated timeout-like errors
suggest provider pressure:

```bash
uv run python -m app.data.backfill_historical_weather \
  --database-url "$DATABASE_URL" \
  --stay-destination tignes \
  --start-date 1991-01-01 \
  --end-date 2025-12-31 \
  --retry-attempts 5 \
  --backoff-seconds 30 \
  --request-delay-seconds 5 \
  --request-jitter-ratio 0.25 \
  --retry-jitter-ratio 0.25 \
  --provider-pressure-error-threshold 3 \
  --provider-pressure-cooldown-seconds 300
```

If a rebuild run stops on provider rate limiting, do not immediately rerun with
`--rebuild`. Wait for the quota window to reset, then rerun the same target/date
range without `--rebuild` and without `--force-refetch` so completed chunks are
skipped and only missing chunks are fetched.

Derived-only rebuild:

```bash
uv run python -m app.data.rebuild_snow_climatology --database-url "$DATABASE_URL" \
  --stay-destination tignes --baseline-end-year 2025
```

Production derived-only rebuild:

- GitHub Actions -> `Rebuild Snow Climatology` -> `Run workflow`
- keep `baseline_end_year=2025` until the full 2026 archive is available
- leave both target inputs empty for all ski areas, or pass comma-separated
  `ski_area_ids` and/or `stay_destination_ids`

Daily recent-archive reconciliation updates raw archive rows only. It does not
rebuild climatology automatically, because climatology should use an explicitly
chosen complete archive year rather than a partial current-year baseline.

For production-scale rebuilds, prefer targeted batches and inspect logs for
`raw_rows_read`, `climatology_rows_written`, and `weak_coverage_groups` before
expanding to the full supported catalog.

## Data quality audit

Run the data-quality audit after large backfills, climatology rebuilds, catalog
curation review, or source-trust manifest changes. The audit is read-only: it
does not change the database or catalog files. It emits low-cardinality Grafana
metrics and writes detailed JSON/Markdown artifacts for review.

Production workflow:

- GitHub Actions -> `Audit Data Quality` -> `Run workflow`
- keep `archive_start_date=1991-01-01` for the 35-season baseline
- set `archive_end_date` explicitly when validating a known backfill target,
  for example `2026-03-01`
- leave `archive_end_date` empty only when you want the job to infer the latest
  available archive row from the database

Local command shape:

```bash
uv run --no-config python -m app.data.audit_data_quality \
  --database-url "$DATABASE_URL" \
  --archive-start-date 1991-01-01 \
  --archive-end-date 2026-03-01 \
  --output-dir artifacts/data-quality
```

Review `artifacts/data-quality/data-quality-report.md` for the concrete missing
resorts, ski areas, elevation bands, catalog field groups, and trust-manifest
entries. Grafana panels intentionally show only grouped summaries such as
domain, field group, status, elevation band, model, and baseline period.

## Product canary and Grafana alerts

The `Product Canary` GitHub Actions workflow runs every 6 hours against
production and can be started manually with an optional base URL override. It
checks health, database readiness, search-specific readiness, and a
representative anonymous search.

Local canary:

```bash
uv run --no-config python ops/canary/search_canary.py \
  --base-url https://snowcast.fly.dev \
  --latency-threshold-seconds 15
```

The `Parse Canary` workflow runs daily and can be started manually to exercise a
representative `/api/parse-query` request:

```bash
uv run --no-config python ops/canary/parse_canary.py \
  --base-url https://snowcast.fly.dev
```

Grafana alert rules are maintained in `ops/grafana/alerting/` and deployed by
the manual `Deploy Grafana Alerts` workflow. Required GitHub configuration:

- Secret: `GRAFANA_SERVICE_ACCOUNT_TOKEN`
- Secret: `GRAFANA_ALERT_EMAIL_TO`
- Variable or secret: `GRAFANA_URL`
- Variable or secret: `GRAFANA_DASHBOARD_NAMESPACE`

Validate locally:

```bash
uv run --no-config python ops/grafana/scripts/validate_alerts.py
```

Apply from GitHub Actions with `apply=true`, or locally with:

```bash
GRAFANA_DASHBOARD_NAMESPACE="stacks-1693732" \
GRAFANA_ALERT_EMAIL_TO="owner@example.com" \
  uv run --no-config python ops/grafana/scripts/deploy_alerts.py --apply
```

Alert deploy creates or updates the `Snowcast Alerts` folder, the owner email
contact point, and the provisioned alert rules. After the first alert deploy,
route the provisioned alert rules to the `snowcast-owner-email` contact point in
Grafana's notification policy UI. The repo does not overwrite notification
policies yet because the Grafana policy API replaces the whole routing tree.

## Smoke checks

- App root: `/`
- Health: `/api/healthz`
- Ready: `/api/readyz`
- Product readiness: `/api/search-readiness`
- Representative search:
```bash
curl --fail --silent --show-error \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{"intent":{"constraints":{"location":{"country":"France"},"travel_window":{"month":3}},"party":{"skill_levels":["intermediate"]},"objectives":[{"factor_id":"pass_terrain_value","importance":"normal"}]},"generate_refinements":false}' \
  "https://snowcast.fly.dev/api/search"
```

## Failure inspection

- Fly app logs:
```bash
fly logs --app snowcast
```
- Process-specific machine status:
```bash
fly status --app snowcast
```
- If readiness fails, validate:
  - `DATABASE_URL`
  - Neon connectivity / credentials
  - release-command bootstrap success
- If readiness is degraded, inspect `forecast_heads`,
  `expected_forecast_head_count`, `missing_forecast_head_count`, and
  `stale_forecast_head_count` in `/api/search-readiness`. Coverage is measured
  per active ski area and configured source, rather than by distinct run count.
  Search remains available through climatology when heads are missing or stale.
- If freshness lags, inspect:
  - `.github/workflows/refresh-weather-forecasts.yml` run history
  - GitHub Actions `DATABASE_URL` secret
  - source status and failed-area counts from `refresh_weather_forecasts`
