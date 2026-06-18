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
