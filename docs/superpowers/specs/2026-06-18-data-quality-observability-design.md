# Data Quality Observability Design

## Summary

Add production observability for Snowcast data freshness and data completeness.
The first slice fixes existing weather-refresh metrics so scheduled jobs export
freshness telemetry reliably, then adds a broader data-quality audit command that
checks historical weather coverage, climatology coverage, catalog completeness,
and source-trust coverage. The audit remains metrics-and-artifact based; it does
not add new canonical database tables in this phase.

## Decision And Review Gate

- Classification: `review-gated`
- High-risk domains touched: observability, production reliability, scheduled
  jobs, data correctness, data trust, dashboard semantics, alerting foundation
- Developer Decision Checkpoint status: resolved by owner discussion
  - Use summary metrics plus a detailed JSON/Markdown audit artifact for data
    completeness.
  - Do not add a persistent database snapshot table in this slice.
  - Keep free-form and sensitive detail out of high-cardinality metric labels.
    Bounded catalog IDs such as `resort_id` and `ski_area_id` are allowed for
    drilldown panels while full date-level issue lists remain in artifacts.
  - Add alert candidates and dashboard signals first; enable noisy paging later
    only after the baseline is clean.
- ADR status: not required for this slice. The approach is intentionally
  reversible; a future ADR is appropriate if data-quality snapshots become
  persistent database state or if Grafana/Terraform becomes the canonical
  observability control plane.
- Advisory design-review status: completed using `observability-ops`,
  `data-trust-source-integrity`, and `backend-api`. Review found one
  implementation-blocking dashboard correctness issue: snapshot-style
  completeness metrics must be gauges, not `_total` counters. The spec was
  corrected before planning.
- Advisory feature-review status: required before final handoff.

## Problem

The current dashboard has Weather / Data Freshness panels, but those panels are
not populated consistently because the relevant metrics are emitted from
standalone jobs. The FastAPI app initializes OpenTelemetry on web startup; the
weather-refresh and climatology commands do not currently initialize and flush
OpenTelemetry as standalone processes, and the GitHub Actions workflows do not
pass OTLP export secrets into those job processes.

Snowcast also needs a product-data health signal that is independent from HTTP
availability. A search can return `200` while silently relying on incomplete
archive data, missing climatology rows, stale current conditions, or weak catalog
source coverage. Those conditions should be visible in Grafana before they become
recommendation-quality regressions.

## Goals

- Export existing conditions-refresh freshness metrics from scheduled jobs.
- Make short-lived CLI jobs initialize and flush OpenTelemetry reliably.
- Add a scheduled/manual data-quality audit command.
- Emit low-cardinality metrics for data completeness and data trust coverage.
- Write a detailed audit artifact listing exact incomplete ski areas, bands,
  fields, and source-trust gaps.
- Add dashboard panels for freshness and completeness.
- Add alert-rule candidates or documented alert thresholds without creating a
  noisy paging setup before the baseline is known.
- Keep the first implementation low-maintenance for a solo builder.

## Non-Goals

- Do not add a new data-quality database table.
- Do not make data-quality checks part of the request path.
- Do not block search requests when data-quality checks fail.
- Do not expose raw user search text, raw LLM prompts/responses, tokens, or
  provider URLs in metrics.
- Do not create high-cardinality metrics with date ranges, URLs, raw field
  names, or free-form issue text as labels.
- Do not enable paging alerts until expected baseline values are known.

## Architecture

```text
app/observability/
  cli.py                  # CLI OTel setup/shutdown for short-lived jobs
  jobs.py                 # job spans, freshness metrics, audit metrics helpers

app/data/
  refresh_conditions.py   # uses CLI OTel setup in main()
  rebuild_snow_climatology.py
  audit_data_quality.py   # new scheduled/manual audit command

artifacts/data-quality/
  data-quality-summary.json
  data-quality-report.md

.github/workflows/
  refresh-conditions.yml
  rebuild-snow-climatology.yml
  audit-data-quality.yml

ops/grafana/
  dashboards/snowcast-production-overview.dashboard.json
  dashboards/snowcast-data-quality.dashboard.json
```

FastAPI remains responsible for request-path metrics and traces. Standalone jobs
use a dedicated CLI observability helper that reads the same environment
settings, configures the same meter/tracer providers, and forces an export flush
at process exit.

The data-quality audit is a read-only job. It queries the database and catalog,
emits summary metrics, and writes detailed artifacts. It does not mutate
catalog, weather, climatology, or trust state.

## CLI OpenTelemetry Export

Add a small helper for command modules:

```python
from app.observability.cli import configure_cli_observability

def main() -> None:
    with configure_cli_observability(job_name="refresh_conditions"):
        ...
```

The helper should:

- load `ObservabilitySettings` from the existing env-based configuration;
- configure the same tracer and metrics recorder used by FastAPI;
- instrument `psycopg`, `urllib`, and logging once per process;
- set service attributes suitable for jobs:
  - `service.name`: use `OTEL_SERVICE_NAME` or `snowcast-jobs`;
  - `snowcast.job.name`: command name on job spans;
- call `force_flush()` and `shutdown()` on configured providers at exit when
  supported;
- remain safe when `OTEL_ENABLED=false` or OTLP endpoint is missing.

## GitHub Actions Environment

Scheduled data jobs must receive the same OTLP export settings already used by
production:

```yaml
env:
  OTEL_ENABLED: "true"
  OTEL_SERVICE_NAME: snowcast-jobs
  OTEL_EXPORTER_OTLP_ENDPOINT: ${{ secrets.OTEL_EXPORTER_OTLP_ENDPOINT }}
  OTEL_EXPORTER_OTLP_HEADERS: ${{ secrets.OTEL_EXPORTER_OTLP_HEADERS }}
```

The workflow should not fail solely because OTLP secrets are missing on a local
fork or dry-run environment. In the production repository, missing OTLP endpoint
should be visible as a warning and as absent metrics.

## Freshness Metrics

Keep the current conditions-refresh metrics and make them export reliably:

- `snowcast_conditions_refresh_success_total{source}`
- `snowcast_conditions_refresh_failure_total{source,reason}`
- `snowcast_conditions_refresh_age_seconds{source}`
- `snowcast_conditions_refresh_duration_seconds{status}`

Definitions:

- refresh success means the job either refreshed a row or skipped a row that was
  still fresh;
- refresh failure means an attempted source fetch, normalization, or database
  write failed;
- age is seconds since the latest known successful condition timestamp by source;
- duration is the job wall-clock duration by status.

`refresh_conditions.main()` should wrap the command body in both
`configure_cli_observability(job_name="refresh_conditions")` and
`job_span("conditions_refresh")` so duration and spans are emitted even when the
refresh function exits through an error path.

## Data-Quality Audit Scope

The audit command checks four domains.

### Historical Weather Archive

For each supported ski area and each planned weather elevation band
(`base`, `mid`, `upper`), check archive coverage over the configured baseline
window.

Inputs:

- `--archive-start-date`, default: `1991-01-01`
- `--archive-end-date`, default: latest complete archive date supplied by the
  operator or inferred from DB max archive date
- `--source`, default: `open-meteo`

Output metrics:

- `snowcast_data_completeness_ratio{domain="historical_archive"}`
- `snowcast_data_completeness_entities{domain="historical_archive",status}`
- `snowcast_data_missing_days{domain="historical_archive",elevation_band}`
- `snowcast_archive_coverage_ratio{ski_area_id,elevation_band}`
- `snowcast_archive_missing_days_by_ski_area{ski_area_id,elevation_band}`
- `snowcast_archive_last_observed_timestamp_seconds{ski_area_id,elevation_band}`

Detailed artifact rows include `ski_area_id`, `resort_name`, `elevation_band`,
`expected_days`, `covered_days`, `missing_days`, `first_observed_on`, and
`last_observed_on`.

### Snow Climatology

Check that expected climatology rows exist for each ski area, elevation band,
baseline period, and source model.

Inputs:

- `--source-model`, default: `snowcast_empirical_v1`
- `--baseline-period`, repeatable, default: `normal_30y,recent_15y`
- `--minimum-evidence-seasons`, default: `8`

Output metrics:

- `snowcast_data_completeness_ratio{domain="snow_climatology"}`
- `snowcast_data_completeness_entities{domain="snow_climatology",status}`
- `snowcast_climatology_weak_coverage_groups{source_model,baseline_period}`
- `snowcast_climatology_coverage_ratio{ski_area_id,elevation_band,baseline_period,source_model}`
- `snowcast_climatology_missing_rows_by_ski_area{ski_area_id,elevation_band,baseline_period,source_model}`
- `snowcast_climatology_gap_count{ski_area_id,elevation_band,baseline_period,source_model,status}`

Detailed artifact rows include `ski_area_id`, `elevation_band`,
`baseline_period`, `expected_rows`, `actual_rows`, `min_evidence_seasons`, and
`latest_archive_year`.

### Catalog Required Fields

Check catalog structure through the existing catalog validator, then compute
field-group completeness for supported resort and ski-area fields.

Field groups:

- `destination_coordinates`
- `destination_elevation`
- `ski_area_coordinates`
- `ski_area_elevation`
- `season_windows`
- `official_links`
- `regional_ids`
- `stay_bases`
- `rentals`

Output metrics:

- `snowcast_catalog_field_groups{field_group,status}`
- `snowcast_data_completeness_ratio{domain="catalog_required_fields"}`
- `snowcast_catalog_gap_count{resort_id,field_group,status}`

Detailed artifact rows include `entity_type`, `entity_id`, `field_group`,
`status`, and `issue`.

### Source Trust Coverage

Use `app/data/resort_trust_manifest.json` to summarize trust coverage for the
field groups that the validator already treats as source-backed critical data.

Output metrics:

- `snowcast_catalog_trust_status{field_group,trust_status}`
- `snowcast_data_completeness_ratio{domain="catalog_source_trust"}`
- `snowcast_trust_gap_count{resort_id,field_group,trust_status}`

Detailed artifact rows include `resort_id`, `field_group`, `trust_status`, and
`source_ref_count`.

## Metric Label Policy

Allowed labels:

- bounded domain names: `domain`, `status`, `field_group`, `source`,
  `source_model`, `baseline_period`, `elevation_band`, `job_name`, `reason`
- bounded catalog IDs: `resort_id`, `ski_area_id`

Disallowed labels:

- URLs
- raw user text
- exact origin text
- date ranges
- raw validation issue text
- raw LLM prompt/response content
- provider API payloads

Metric labels may identify the affected resort or ski area by stable catalog ID,
but they must not carry raw names, URLs, source refs, issue text, date ranges, or
provider payloads. The exact date-level missing windows and full source-backed
evidence belong in artifacts, not metric labels.

Completeness and coverage metrics are gauges that represent the current audit
snapshot. They must not use `_total` suffixes unless they are true monotonic
counters, such as refresh successes or failures.

## Artifact Format

Write both machine-readable and human-readable outputs:

```text
artifacts/data-quality/data-quality-summary.json
artifacts/data-quality/data-quality-report.md
```

The JSON artifact contains:

- `generated_at`
- `archive_window`
- `summary_by_domain`
- `historical_archive_issues`
- `snow_climatology_issues`
- `catalog_field_issues`
- `source_trust_issues`
- `warnings`

The Markdown report is optimized for GitHub Actions review and should start with
the highest-risk gaps.

## Dashboard Additions

Update the Snowcast Production Overview dashboard with a compact
`Data Quality & Freshness` row:

- Conditions age by source
- Conditions refresh success/failure rate
- Historical archive completeness %
- Snow climatology completeness %
- Catalog completeness by field group
- Source trust coverage by field group

Keep the dashboard readable:

- top executive cards should show only the most important data-quality failures;
- completeness panels should use percent/stat views for fast scanning;
- detailed issue lists should link or point to artifacts rather than crowd the
  dashboard.

Add a separate `Snowcast Data Quality` drilldown dashboard for operator review
after backfills, catalog updates, and climatology rebuilds. It should include:

- summary cards for audit age and aggregate gap counts;
- historical archive tables by `ski_area_id` and `elevation_band`;
- climatology coverage tables by `ski_area_id`, `elevation_band`, baseline, and
  source model;
- catalog and source-trust gap tables by `resort_id` and field group;
- an audit handoff panel that points to the GitHub Actions artifact and local
  audit command.

## Alerting Foundation

Document alert candidates in the observability runbook. Add Grafana-managed
alert resources only if the baseline is already clean and the expected threshold
is stable.

Initial warning candidates:

- conditions freshness exceeds 12 hours for `open-meteo`;
- refresh failure rate is greater than zero for more than one run;
- historical archive completeness drops below 99%;
- climatology completeness drops below 99%;
- catalog source-backed critical field coverage drops below 100%.

Do not page on these alerts until Snowcast has stable traffic and known-clean
data baselines. Start with dashboard visibility and optional notification-only
rules.

## Security And Privacy

- OTLP export secrets stay in GitHub Actions secrets and Fly secrets.
- The audit artifact must not include database URLs, OTLP headers, tokens,
  provider request URLs with credentials, raw user prompts, or raw LLM payloads.
- Metrics must not contain unbounded user-controlled labels.
- GitHub Actions artifacts are acceptable for detailed data-quality outputs
  because they contain catalog/weather coverage metadata, not secrets.

## Verification

Automated verification:

- unit tests for CLI observability setup in disabled, enabled-without-endpoint,
  and enabled-with-mocked-provider modes;
- unit tests that refresh conditions calls job setup from `main()` and records
  freshness metrics;
- unit tests for historical archive completeness calculations;
- unit tests for climatology completeness calculations;
- unit tests for catalog field-group and trust-status summaries;
- dashboard validation tests for the new panels and PromQL expressions;
- dashboard validation tests for the dedicated `Snowcast Data Quality`
  drilldown dashboard and manifest entry;
- workflow static checks for OTLP env wiring.

Focused commands:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py tests/test_data_quality_audit.py tests/test_grafana_dashboards.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/validate_dashboards.py
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/observability app/data tests/test_observability.py tests/test_data_quality_audit.py tests/test_grafana_dashboards.py
```

Manual verification:

- run refresh conditions locally with `OTEL_ENABLED=false` and confirm no crash;
- run data-quality audit against local or staging DB and inspect JSON/Markdown
  artifacts;
- trigger the GitHub Actions audit job and confirm artifacts are uploaded;
- deploy the dashboard and confirm Data Quality & Freshness panels populate
  after the next job run.

## Rollout

1. Implement CLI OTel setup and job workflow env wiring.
2. Verify conditions freshness panels populate after one refresh run.
3. Implement the read-only data-quality audit and artifact output.
4. Add dashboard panels.
5. Add runbook alert candidates.
6. Enable warning-only Grafana alerts later after the data baseline is known.

## Implementation Assumptions

- The audit workflow exposes `archive_end_date` as an explicit input with a safe
  default derived from the latest complete archive date.
- The audit treats all calendar days as required for historical archive
  completeness. This matches the current backfill and climatology model and
  avoids hiding off-season coverage gaps that might affect future model changes.
- Alerts start as dashboard/runbook candidates. Grafana-managed alert resources
  can be added after a clean baseline is confirmed.
