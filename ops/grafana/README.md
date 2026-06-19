# Snowcast Grafana Dashboards

This directory stores Snowcast Grafana dashboard resources as code. Grafana UI
edits are useful for exploration, but durable dashboard changes should be
exported, normalized, reviewed, committed, and deployed from this directory.

## Files

```text
ops/grafana/
  dashboards.manifest.json
  alerting.manifest.json
  alerting/
    alert-rules.json
    contact-points.json
    folders.json
  dashboards/
    snowcast-production-overview.dashboard.json
    snowcast-data-quality.dashboard.json
  scripts/
    normalize_dashboard.py
    validate_dashboards.py
    deploy_dashboards.py
    validate_alerts.py
    deploy_alerts.py
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
- Secret: `GRAFANA_ALERT_EMAIL_TO` for alert deploys
- Variable or secret: `GRAFANA_URL`
- Variable or secret: `GRAFANA_DASHBOARD_NAMESPACE`

## Validate Dashboards

Dashboard validation does not need Grafana credentials:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/validate_dashboards.py
```

Alert validation also runs without Grafana credentials:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/validate_alerts.py
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

## Alerting

Alert rules and the first owner email contact point are also repo-owned:

```text
ops/grafana/alerting.manifest.json
ops/grafana/alerting/folders.json
ops/grafana/alerting/contact-points.json
ops/grafana/alerting/alert-rules.json
```

The alert manifest is intentionally logical rather than a raw Grafana export.
This keeps it easier to review now and easier to translate into Terraform later.
The Python deployer materializes the logical rules into Grafana provisioning API
payloads. It creates or updates the repo-owned `Snowcast Alerts` folder before
creating contact points and alert rules, so apply deploys require
`GRAFANA_DASHBOARD_NAMESPACE`.

Dry-run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/deploy_alerts.py
```

Apply:

```bash
GRAFANA_DASHBOARD_NAMESPACE="stacks-1693732" \
GRAFANA_ALERT_EMAIL_TO="owner@example.com" \
  UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/deploy_alerts.py --apply
```

The deployer creates or updates:

- `Snowcast Alerts` folder
- `snowcast-owner-email` contact point
- search latency warning/critical rules
- API 5xx rule
- empty-search and parse-success rules
- conditions freshness and refresh-failure rules
- LLM retry rule
- search-readiness canary rule

Notification policy routing is not automatically overwritten. Grafana's
notification policy API replaces the whole policy tree, so routing alerts to
`snowcast-owner-email` should remain a manual Grafana UI step until Snowcast
fully migrates alerting and dashboards to Terraform or an explicit policy
manifest.

## Operating Rule

- Repo files are the source of truth.
- Grafana UI edits are temporary experiments.
- If a UI edit is worth keeping, export it, normalize it, validate it, commit
  it, and deploy it from this directory.
- If an alert edit is worth keeping, update the logical alerting manifest,
  validate it, commit it, and deploy it from this directory.
- Do not commit tokens, OTLP headers, raw query text, raw prompts, or other
  sensitive telemetry data.
