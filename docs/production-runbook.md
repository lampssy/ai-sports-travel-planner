# Production Runbook

## Required secrets

- Fly:
  - `FLY_API_TOKEN` for GitHub Actions deploys
- Fly runtime:
  - `DATABASE_URL` pointing to the Neon production database
  - `GEMINI_API_KEY`
  - optional `GEMINI_MODEL`
  - optional `SNOWCAST_SEARCH_MODEL` (`search_v1` by default, or `search_v2`
    for resort-fit candidate scoring)
  - optional `SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE=true` for private debug-only
    `/api/search?debug=true&search_model=...` testing
- GitHub Actions:
  - `DATABASE_URL` for the scheduled/manual refresh workflow

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

## Search model rollout

Production search ranking is controlled by `SNOWCAST_SEARCH_MODEL`.

- `search_v1`: legacy search ranking.
- `search_v2`: resort-fit candidate scoring using reviewed active factors.

Keep `SNOWCAST_ALLOW_SEARCH_MODEL_OVERRIDE` unset in normal production. During
private pre-public validation, setting it to `true` allows debug requests such
as:

```bash
curl "https://snowcast.fly.dev/api/search?location=France&min_price=140&max_price=320&stars=1&skill_level=intermediate&debug=true&search_model=search_v2"
```

Rollback is an environment-only change: set `SNOWCAST_SEARCH_MODEL=search_v1`
and redeploy or restart the app.

## Refresh process

- Conditions refresh is scheduled by GitHub Actions, not by a resident Fly worker.
- Scheduled cadence: every 6 hours.
- In Worker / Function / Trigger terms:
  - trigger: GitHub Actions schedule or manual `workflow_dispatch`
  - function: refresh current resort conditions and freshness telemetry
  - worker: GitHub Actions runner executing the refresh command
- Manual operator runs happen through `workflow_dispatch` with:
  - optional `force=true`
  - optional comma-separated `resort_targets`
- Manual refresh command shape remains:
```bash
uv run python -m app.data.refresh_conditions --database-url "$DATABASE_URL" --force --resort tignes
```

## Historical archive and climatology rebuild

Historical weather backfills are manual/operator-driven. Run them after
weather-critical ski-area coordinates and elevation bands are reviewed.

Recommended sequence:

1. Backfill `raw_weather_history` for the intended resorts and date range.
2. Rebuild derived snow climatology from the raw archive.
3. Run a representative search and confirm planning evidence uses
   `snow_climatology` rather than raw-history or heuristic fallback.

Targeted local shape:

```bash
uv run python -m app.data.backfill_historical_weather --database-url "$DATABASE_URL" --resort tignes --start-date 1991-01-01 --end-date 2025-12-31 --rebuild
```

Large historical archive runs should be paced rather than retried aggressively.
The backfill client reuses HTTP connections, jitters successful-request and
retry waits, and applies a longer cooldown when repeated timeout-like errors
suggest provider pressure:

```bash
uv run python -m app.data.backfill_historical_weather \
  --database-url "$DATABASE_URL" \
  --resort tignes \
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
uv run python -m app.data.rebuild_snow_climatology --database-url "$DATABASE_URL" --target tignes --baseline-end-year 2025
```

Production derived-only rebuild:

- GitHub Actions -> `Rebuild Snow Climatology` -> `Run workflow`
- keep `baseline_end_year=2025` until the full 2026 archive is available
- leave `resort_targets` empty for all supported ski areas, or pass a
  comma-separated list of exact destination ids or ski-area ids

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
curl -s "https://snowcast.fly.dev/api/search?location=France&min_price=150&max_price=320&stars=1&skill_level=intermediate"
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
- If freshness lags, inspect:
  - `.github/workflows/refresh-conditions.yml` run history
  - GitHub Actions `DATABASE_URL` secret
  - provider failures from `refresh_conditions`
