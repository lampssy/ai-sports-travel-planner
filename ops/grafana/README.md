# Snowcast Grafana Dashboards

This directory stores Snowcast Grafana dashboard resources as code. Grafana UI
edits are useful for exploration, but durable dashboard changes should be
exported, normalized, reviewed, committed, and deployed from this directory.

## Files

```text
ops/grafana/
  dashboards.manifest.json
  dashboards/
    snowcast-production-overview.dashboard.json
    snowcast-data-quality.dashboard.json
  scripts/
    normalize_dashboard.py
    validate_dashboards.py
    deploy_dashboards.py
  terraform/
    README.md
```

The committed dashboard uses Grafana's dashboard resource format:

```json
{
  "apiVersion": "dashboard.grafana.app/v2",
  "kind": "Dashboard",
  "metadata": {
    "name": "snowcast-production-overview"
  },
  "spec": {
    "title": "Snowcast Production Overview"
  }
}
```

Runtime stack values such as namespace and resource version are not committed.
The repo currently owns two dashboards:

- `Snowcast Production Overview` is the operator landing page for HTTP, search,
  parser/LLM, freshness, and summary data-quality signals.
- `Snowcast Data Quality` is the drilldown surface for bounded resort/ski-area
  audit gaps after weather backfills, catalog review batches, or climatology
  rebuilds.

Data-quality audit metrics are emitted as short-lived job snapshots, not as
continuously refreshed runtime gauges. Dashboard panels that read audit metrics
should use a bounded lookback such as `last_over_time(...[7d])` or
`max_over_time(...[7d])` so drilldowns continue to show the most recent audit
result after the job timestamp falls outside the selected dashboard range.

The dashboards expect Grafana Cloud datasources named
`grafanacloud-prom` for Prometheus metrics and
`grafanacloud-tallgoldfinch1476-traces` for Tempo traces. If a future stack uses
different datasource names, update the dashboard JSON before deployment.

## Required Grafana Credentials

Dashboard deployment uses a Grafana service account token. Do not reuse the
OTLP ingestion token used by the application to send telemetry.

Local environment variables:

```bash
export GRAFANA_URL="https://tallgoldfinch1476.grafana.net"
export GRAFANA_DASHBOARD_NAMESPACE="stacks-1693732"
export GRAFANA_SERVICE_ACCOUNT_TOKEN="..."
```

GitHub configuration:

- Secret: `GRAFANA_SERVICE_ACCOUNT_TOKEN`
- Variable or secret: `GRAFANA_URL`
- Variable or secret: `GRAFANA_DASHBOARD_NAMESPACE`

## Validate

Validation does not need Grafana credentials:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/validate_dashboards.py
```

## Normalize A Grafana Export

When a dashboard is edited in the Grafana UI, export it and normalize it before
committing:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/normalize_dashboard.py \
  /path/to/exported-dashboard.json \
  ops/grafana/dashboards/snowcast-production-overview.dashboard.json \
  --name snowcast-production-overview \
  --folder-uid ''
```

The normalizer removes volatile fields such as Grafana resource versions,
creation timestamps, stack namespace, deprecated internal IDs, and saved-from-UI
metadata.

## Dry-Run Deploy

Dry-run validates the dashboard and prints intended actions. It does not write
to Grafana:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/deploy_dashboards.py
```

## Apply Deploy

Apply deploy creates or updates the dashboard through Grafana's Dashboard HTTP
API:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/deploy_dashboards.py --apply
```

The deployer first updates the dashboard whose resource name matches the
manifest entry. If that resource does not exist, it searches the target folder
for exactly one dashboard with the same title and adopts it by updating that
dashboard instead of creating another copy. If multiple dashboards with the same
title exist, deploy fails so the duplicates can be deleted or renamed in the
Grafana UI before retrying.

The GitHub workflow `Deploy Grafana Dashboards` is manual-only for now. After
the flow is proven, it can be changed to deploy automatically when
`ops/grafana/**` changes on `main`.

## Operating Rule

- Repo files are the source of truth.
- Grafana UI edits are temporary experiments.
- If a UI edit is worth keeping, export it, normalize it, validate it, commit
  it, and deploy it from this directory.
- Do not commit tokens, OTLP headers, raw query text, raw prompts, or other
  sensitive telemetry data.
