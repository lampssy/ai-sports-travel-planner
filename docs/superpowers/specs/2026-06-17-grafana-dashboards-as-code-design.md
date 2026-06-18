# Grafana Dashboards As Code Design

## Summary

Bring the Snowcast Grafana dashboard under repo ownership so the production
observability view can be reviewed, versioned, and redeployed from GitHub.
Start with a lightweight Python deploy script instead of Terraform, but store
dashboard resources and metadata in a shape that can later be consumed by the
Grafana Terraform provider with minimal reshaping.

## Decision And Review Gate

- Classification: `review-gated`
- High-risk domains touched: observability, production reliability, CI/CD,
  external integration with Grafana Cloud
- Developer Decision Checkpoint status: resolved by owner discussion
  - Use Grafana Cloud as the Snowcast application observability home.
  - Use Fly built-in Grafana/logs as the infrastructure support view.
  - Manage dashboards in the repo with a script-first deploy flow for now.
  - Keep the layout Terraform-friendly so migration does not rewrite dashboard
    source files.
- ADR status: not required for this slice. The decision is operationally useful
  but reversible and can be revisited when Terraform state is introduced.
- Advisory design-review status: accepted as scoped `observability-ops` review
  during planning; feature-review should run before final handoff.
- Advisory feature-review status: completed after implementation with no
  blocking findings.

## Goals

- Store the Snowcast Production Overview dashboard in git.
- Sanitize exported Grafana dashboard JSON so volatile stack/user metadata is
  not committed.
- Provide a local validation command that needs no Grafana credentials.
- Provide a local and GitHub Actions deploy path for the dashboard.
- Keep deployment token handling separate from OTLP ingestion credentials.
- Keep the design easy to migrate to Terraform later.

## Non-Goals

- Do not introduce Terraform state in this phase.
- Do not provision Grafana alert rules yet.
- Do not provision Grafana folders, contact points, or notification policies.
- Do not replace Fly.io built-in metrics/logs.
- Do not ship Grafana skills or local agent tool caches as Snowcast source.

## Architecture

```text
ops/grafana/
  README.md
  dashboards.manifest.json
  dashboards/
    snowcast-production-overview.dashboard.json
  scripts/
    dashboard_resources.py
    normalize_dashboard.py
    validate_dashboards.py
    deploy_dashboards.py
  terraform/
    README.md
.github/workflows/
  validate-grafana-dashboards.yml
  deploy-grafana-dashboards.yml
```

The committed dashboard remains a Grafana dashboard resource:

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

The deploy script injects runtime deployment context from environment variables:

- `GRAFANA_URL`
- `GRAFANA_SERVICE_ACCOUNT_TOKEN`
- `GRAFANA_DASHBOARD_NAMESPACE`

## Dashboard Sanitization Rules

Committed dashboard resources must not include:

- `metadata.uid`
- `metadata.namespace`
- `metadata.resourceVersion`
- `metadata.generation`
- `metadata.creationTimestamp`
- `metadata.labels["grafana.app/deprecatedInternalID"]`
- `metadata.annotations["grafana.app/createdBy"]`
- `metadata.annotations["grafana.app/saved-from-ui"]`

The deploy endpoint owns the namespace, and Grafana owns resource versions and
creation metadata.

## Deploy Flow

Validation:

```bash
uv run --no-config python ops/grafana/scripts/validate_dashboards.py
```

Dry-run deploy:

```bash
uv run --no-config python ops/grafana/scripts/deploy_dashboards.py
```

Apply deploy:

```bash
GRAFANA_URL=https://tallgoldfinch1476.grafana.net \
GRAFANA_SERVICE_ACCOUNT_TOKEN=... \
GRAFANA_DASHBOARD_NAMESPACE=stacks-1693732 \
uv run --no-config python ops/grafana/scripts/deploy_dashboards.py --apply
```

The GitHub workflow starts as manual-only. Automatic deployment from `main` can
be added after the flow has proven stable.

## Terraform Migration Path

Keep dashboard source files independent from the Python deployment script:

- dashboard JSON is stored under `ops/grafana/dashboards/`
- dashboard registry metadata is stored in `dashboards.manifest.json`
- secrets and deployment target are environment-driven
- no Python-specific wrapper is embedded in dashboard JSON

Later Terraform can read the same dashboard files, manage folders/alerts, and
own dashboard deployment state. Terraform state should not be stored in git.

## Security And Privacy

- Do not commit Grafana service account tokens.
- Do not reuse OTLP ingestion tokens for dashboard deployment.
- Keep dashboard variables and labels low-cardinality.
- Avoid panels that expose raw user prompts, raw search queries, exact origins,
  auth tokens, provider URLs, or LLM prompt/response bodies.

## Verification

- Unit tests cover sanitizer, validator, manifest loading, and deploy client
  behavior with mocked HTTP calls.
- Local validation succeeds against committed dashboard files.
- GitHub workflow YAML parses.
- Manual deploy dry-run prints intended dashboard actions without network
  writes.
- Manual apply can be run with real Grafana credentials after user configures
  GitHub secrets/variables.
