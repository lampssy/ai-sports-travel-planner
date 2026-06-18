# Data Quality Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Snowcast scheduled data jobs export freshness telemetry and add a read-only data-quality audit with dashboard panels and artifacts.

**Architecture:** Reuse the existing OpenTelemetry settings and metric recorder, but add a CLI entrypoint helper for short-lived jobs. Add a read-only audit command that queries existing catalog, raw-weather, and climatology data, emits low-cardinality gauges, and writes detailed JSON/Markdown artifacts. Keep Grafana dashboards repo-managed and do not add data-quality database tables in this slice.

**Tech Stack:** Python 3.13, FastAPI, OpenTelemetry Python, psycopg, GitHub Actions, Grafana dashboard resources, pytest, ruff.

---

## Decision Gate Before Execution

- Classification: `review-gated`
- High-risk domains touched: observability, production reliability, scheduled jobs, data correctness, data trust, dashboard semantics
- Resolved owner decisions:
  - Use summary metrics plus a detailed JSON/Markdown audit artifact.
  - Do not add a persistent data-quality database table now.
  - Keep exact missing resort/field lists out of high-cardinality metric labels.
  - Start with dashboard visibility and runbook alert candidates, not noisy paging alerts.
- Accepted assumptions:
  - Historical archive completeness checks all calendar days.
  - Audit workflow exposes an explicit archive end-date input with a safe inferred fallback for manual/local runs.
  - Grafana alert resources can be added after the baseline is clean.
- Unresolved owner decisions: None
- ADR status: not required for this slice because no canonical storage or irreversible observability control-plane decision is added.
- Advisory review status:
  - Design review completed in `docs/superpowers/specs/2026-06-18-data-quality-observability-design.md`.
  - Feature review required before final handoff.

## File Map

- Create `app/observability/cli.py`: context manager for standalone OTel setup and flush.
- Modify `app/observability/otel.py`: expose reusable runtime setup for non-FastAPI commands and safe shutdown hooks.
- Modify `app/observability/jobs.py`: add data-quality metric helpers and keep job-span behavior.
- Modify `app/data/refresh_conditions.py`: wrap CLI main with OTel setup and job span.
- Modify `app/data/rebuild_snow_climatology.py`: wrap CLI main with OTel setup and job span; emit rebuild summary metrics.
- Create `app/data/audit_data_quality.py`: read-only audit command, calculations, artifact writers.
- Modify `app/data/repositories.py`: add bounded read helpers for archive and climatology coverage if the audit cannot use existing methods efficiently.
- Modify `.github/workflows/refresh-conditions.yml`: pass OTel env vars to the job.
- Modify `.github/workflows/rebuild-snow-climatology.yml`: pass OTel env vars to the job.
- Create `.github/workflows/audit-data-quality.yml`: manual/scheduled audit with artifact upload and OTel env vars.
- Modify `ops/grafana/dashboards/snowcast-production-overview.dashboard.json`: add Data Quality & Freshness panels.
- Modify `tests/test_observability.py`: CLI OTel and job metric tests.
- Create `tests/test_data_quality_audit.py`: audit calculations, artifact shape, and privacy/cardinality checks.
- Modify `tests/test_grafana_dashboards.py`: dashboard panel/query assertions.
- Modify `docs/observability-runbook.md`: runbook usage and alert candidates.
- Modify `docs/production-runbook.md`: operator commands and workflow instructions.
- Modify `docs/engineering-notes.md`: concise note on data-quality audit pattern if the file has a relevant observability/data section.

## Task 1: Add CLI OpenTelemetry Setup

**Files:**
- Create: `app/observability/cli.py`
- Modify: `app/observability/otel.py`
- Modify: `tests/test_observability.py`

- [ ] **Step 1: Write failing CLI setup tests**

Add tests in `tests/test_observability.py` for:

```python
def test_cli_observability_disabled_is_noop(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    with configure_cli_observability(job_name="refresh_conditions") as settings:
        assert settings.enabled is False


def test_cli_observability_enabled_without_endpoint_configures_local_recorder(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    with configure_cli_observability(job_name="audit_data_quality") as settings:
        assert settings.enabled is True
        get_metrics_recorder().increment("snowcast_test_total")
```

Use monkeypatches matching the existing `configure_observability` tests so no real exporters are created.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
```

Expected: fails because `app.observability.cli` and `configure_cli_observability` do not exist.

- [ ] **Step 3: Refactor reusable runtime setup**

In `app/observability/otel.py`, keep `configure_observability(app)` unchanged for FastAPI callers, but extract runtime setup so CLI code can call it without a FastAPI app:

```python
def configure_observability_runtime() -> ObservabilitySettings:
    settings = load_observability_settings()
    if not settings.enabled:
        return settings

    signature = _runtime_signature(settings)
    if not _runtime_configured:
        _configure_runtime(settings, signature)
    elif _configured_signature != signature:
        LOGGER.warning(
            "OpenTelemetry runtime is already configured; changed runtime "
            "settings will be ignored until process restart."
        )

    configure_tracer(trace.get_tracer("snowcast"))
    configure_metrics_recorder(
        OpenTelemetryMetricsRecorder(metrics.get_meter("snowcast"))
    )
    _instrument_global_libraries_once()
    return settings
```

Then simplify `configure_observability(app)`:

```python
def configure_observability(app: FastAPI) -> ObservabilitySettings:
    settings = configure_observability_runtime()
    if not settings.enabled:
        return settings
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls=HEALTHCHECK_TRACE_EXCLUDED_URLS,
    )
    return settings
```

Add a safe shutdown helper:

```python
def shutdown_observability_runtime() -> None:
    try:
        trace.get_tracer_provider().force_flush()
        trace.get_tracer_provider().shutdown()
    except Exception:
        LOGGER.debug("OpenTelemetry tracer provider shutdown failed", exc_info=True)
    try:
        metrics.get_meter_provider().force_flush()
        metrics.get_meter_provider().shutdown()
    except Exception:
        LOGGER.debug("OpenTelemetry meter provider shutdown failed", exc_info=True)
```

The helper must not raise during command shutdown.

- [ ] **Step 4: Implement CLI context manager**

Create `app/observability/cli.py`:

```python
from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from app.observability.config import ObservabilitySettings
from app.observability.otel import (
    configure_observability_runtime,
    shutdown_observability_runtime,
)
from app.observability.tracing import start_span

LOGGER = logging.getLogger(__name__)


@contextmanager
def configure_cli_observability(*, job_name: str) -> Iterator[ObservabilitySettings]:
    settings = configure_observability_runtime()
    try:
        with start_span("job.cli", {"snowcast.job.name": job_name}):
            yield settings
    finally:
        if settings.enabled:
            shutdown_observability_runtime()
```

- [ ] **Step 5: Run tests and ruff**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/observability tests/test_observability.py
```

Expected: all tests pass and ruff reports no issues.

## Task 2: Export Existing Refresh And Climatology Job Metrics

**Files:**
- Modify: `app/data/refresh_conditions.py`
- Modify: `app/data/rebuild_snow_climatology.py`
- Modify: `app/observability/jobs.py`
- Modify: `.github/workflows/refresh-conditions.yml`
- Modify: `.github/workflows/rebuild-snow-climatology.yml`
- Modify: `tests/test_observability.py`

- [ ] **Step 1: Write failing job entrypoint tests**

Add focused tests using monkeypatches:

```python
def test_refresh_conditions_main_uses_cli_observability_and_job_span(monkeypatch):
    import app.data.refresh_conditions as refresh_module

    calls: list[str] = []

    @contextmanager
    def fake_cli(*, job_name: str):
        calls.append(f"cli:{job_name}")
        yield SimpleNamespace(enabled=False)

    @contextmanager
    def fake_job(name: str):
        calls.append(f"job:{name}")
        yield

    monkeypatch.setattr(refresh_module, "configure_cli_observability", fake_cli)
    monkeypatch.setattr(refresh_module, "job_span", fake_job)
    monkeypatch.setattr(
        refresh_module,
        "refresh_conditions",
        lambda **_kwargs: refresh_module.RefreshResult(refreshed=1),
    )
    monkeypatch.setattr(
        refresh_module.argparse.ArgumentParser,
        "parse_args",
        lambda _self: SimpleNamespace(database_url="postgresql://test", force=False, resort=[]),
    )

    refresh_module.main()

    assert calls == ["cli:refresh_conditions", "job:conditions_refresh"]
```

Add the same shape for `rebuild_snow_climatology.main()` with
`job:rebuild_snow_climatology`.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
```

Expected: tests fail because the modules do not import or use the CLI/job span helpers.

- [ ] **Step 3: Wrap refresh main**

In `app/data/refresh_conditions.py`, import:

```python
from app.observability.cli import configure_cli_observability
from app.observability.jobs import job_span, record_conditions_refresh_result
```

Wrap the body after argument parsing:

```python
with configure_cli_observability(job_name="refresh_conditions"):
    with job_span("conditions_refresh"):
        result = refresh_conditions(...)
```

Keep existing `UnknownRefreshTargetError` behavior and exit code.

- [ ] **Step 4: Add climatology rebuild metrics**

In `app/observability/jobs.py`, add:

```python
def record_snow_climatology_rebuild_result(
    *,
    source_model: str,
    status: str,
    targeted_ski_areas: int,
    raw_rows_read: int,
    climatology_rows_written: int,
    weak_coverage_groups: int,
) -> None:
    recorder = get_metrics_recorder()
    recorder.increment(
        "snowcast_snow_climatology_rebuild_total",
        {"source_model": source_model, "status": status},
    )
    recorder.gauge(
        "snowcast_snow_climatology_rebuild_ski_areas",
        targeted_ski_areas,
        {"source_model": source_model, "status": status},
    )
    recorder.gauge(
        "snowcast_snow_climatology_raw_rows_read",
        raw_rows_read,
        {"source_model": source_model, "status": status},
    )
    recorder.gauge(
        "snowcast_snow_climatology_rows_written",
        climatology_rows_written,
        {"source_model": source_model, "status": status},
    )
    recorder.gauge(
        "snowcast_snow_climatology_weak_coverage_groups",
        weak_coverage_groups,
        {"source_model": source_model, "status": status},
    )
```

In `rebuild_snow_climatology.main()`, wrap with
`configure_cli_observability(job_name="rebuild_snow_climatology")` and
`job_span("rebuild_snow_climatology")`. Record success after the rebuild and
failure before re-raising when an exception occurs.

- [ ] **Step 5: Wire GitHub Actions OTel env**

Add to both refresh and rebuild workflow job env:

```yaml
OTEL_ENABLED: "true"
OTEL_SERVICE_NAME: snowcast-jobs
OTEL_EXPORTER_OTLP_ENDPOINT: ${{ secrets.OTEL_EXPORTER_OTLP_ENDPOINT }}
OTEL_EXPORTER_OTLP_HEADERS: ${{ secrets.OTEL_EXPORTER_OTLP_HEADERS }}
OTEL_TRACES_SAMPLER_ARG: "1.0"
```

- [ ] **Step 6: Run focused verification**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/observability app/data/refresh_conditions.py app/data/rebuild_snow_climatology.py tests/test_observability.py
```

Expected: all tests pass and ruff reports no issues.

## Task 3: Build Data-Quality Audit Calculations

**Files:**
- Create: `app/data/audit_data_quality.py`
- Modify: `app/data/repositories.py`
- Create: `tests/test_data_quality_audit.py`

- [ ] **Step 1: Write calculation tests**

Create `tests/test_data_quality_audit.py` with tests for pure calculation helpers:

```python
def test_archive_coverage_summary_marks_complete_partial_and_missing():
    rows = (
        ArchiveCoverageRow(
            ski_area_id="complete",
            resort_name="Complete",
            elevation_band="mid",
            expected_days=10,
            covered_days=10,
            first_observed_on="1991-01-01",
            last_observed_on="1991-01-10",
        ),
        ArchiveCoverageRow(
            ski_area_id="partial",
            resort_name="Partial",
            elevation_band="mid",
            expected_days=10,
            covered_days=8,
            first_observed_on="1991-01-01",
            last_observed_on="1991-01-10",
        ),
        ArchiveCoverageRow(
            ski_area_id="missing",
            resort_name="Missing",
            elevation_band="mid",
            expected_days=10,
            covered_days=0,
            first_observed_on=None,
            last_observed_on=None,
        ),
    )

    summary = summarize_archive_coverage(rows)

    assert summary.ratio == 0.6
    assert summary.status_counts == {"complete": 1, "partial": 1, "missing": 1}
    assert summary.missing_days_by_band == {"mid": 12}
```

Add tests for climatology weak coverage, catalog field groups, trust statuses,
and artifact privacy by asserting no URL/token-like keys are emitted as labels.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_data_quality_audit.py -q
```

Expected: fails because audit module does not exist.

- [ ] **Step 3: Add audit dataclasses and status helpers**

Create `app/data/audit_data_quality.py` with:

```python
@dataclass(frozen=True)
class CoverageSummary:
    ratio: float
    status_counts: dict[str, int]
    issue_count: int


@dataclass(frozen=True)
class ArchiveCoverageRow:
    ski_area_id: str
    resort_name: str
    elevation_band: str
    expected_days: int
    covered_days: int
    first_observed_on: str | None
    last_observed_on: str | None

    @property
    def missing_days(self) -> int:
        return max(self.expected_days - self.covered_days, 0)

    @property
    def status(self) -> str:
        if self.covered_days == self.expected_days:
            return "complete"
        if self.covered_days == 0:
            return "missing"
        return "partial"
```

Use status values only from `complete`, `partial`, `missing`, `weak`, `invalid`,
and `error`.

- [ ] **Step 4: Add repository coverage helpers**

If existing repository methods are not sufficient, add bounded aggregate queries:

```python
def list_archive_coverage(
    self,
    *,
    resort_ids: tuple[str, ...],
    elevation_bands: tuple[WeatherElevationBand, ...],
    start_date: date,
    end_date: date,
) -> dict[tuple[str, WeatherElevationBand], ArchiveCoverageStats]:
```

The query should count distinct archive `observed_on` values and min/max observed
dates grouped by `resort_id, elevation_band`.

Add a climatology helper:

```python
def list_climatology_coverage(
    self,
    *,
    ski_area_ids: tuple[str, ...],
    elevation_bands: tuple[WeatherElevationBand, ...],
    baseline_periods: tuple[SnowClimatologyBaselinePeriod, ...],
    source_model: str,
) -> dict[tuple[str, WeatherElevationBand, SnowClimatologyBaselinePeriod], ClimatologyCoverageStats]:
```

It should return row count, min evidence seasons, and latest archive year per
group.

- [ ] **Step 5: Implement summary helpers**

Implement pure helpers:

```python
def summarize_archive_coverage(rows: tuple[ArchiveCoverageRow, ...]) -> ArchiveCoverageSummary:
    ...

def summarize_climatology_coverage(rows: tuple[ClimatologyCoverageRow, ...]) -> ClimatologyCoverageSummary:
    ...

def summarize_catalog_field_groups(resorts: tuple[Destination, ...]) -> CatalogCompletenessSummary:
    ...

def summarize_trust_manifest(manifest: dict[str, object]) -> TrustCoverageSummary:
    ...
```

Ratios are floats from `0.0` to `1.0`, rounded to four decimals for artifact
output and emitted as raw gauge values for Grafana.

- [ ] **Step 6: Run tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_data_quality_audit.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/audit_data_quality.py app/data/repositories.py tests/test_data_quality_audit.py
```

Expected: all tests pass and ruff reports no issues.

## Task 4: Add Audit CLI, Metrics, And Artifacts

**Files:**
- Modify: `app/data/audit_data_quality.py`
- Modify: `app/observability/jobs.py`
- Modify: `tests/test_data_quality_audit.py`
- Modify: `tests/test_observability.py`

- [ ] **Step 1: Write CLI artifact tests**

Add tests that run the audit with fake repositories or monkeypatched collectors:

```python
def test_write_audit_artifacts_creates_json_and_markdown(tmp_path):
    result = DataQualityAuditResult(
        generated_at="2026-06-18T00:00:00+00:00",
        archive_window={"start_date": "1991-01-01", "end_date": "2026-03-01"},
        summary_by_domain={
            "historical_archive": {"ratio": 0.98, "status_counts": {"partial": 1}},
        },
        historical_archive_issues=[
            {"ski_area_id": "tignes", "elevation_band": "mid", "missing_days": 3},
        ],
        snow_climatology_issues=[],
        catalog_field_issues=[],
        source_trust_issues=[],
        warnings=[],
    )

    write_audit_artifacts(result, output_dir=tmp_path)

    assert (tmp_path / "data-quality-summary.json").exists()
    report = (tmp_path / "data-quality-report.md").read_text()
    assert "historical_archive" in report
    assert "tignes" in report
```

Add metric tests with `InMemoryMetricsRecorder` asserting gauge names and labels.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_data_quality_audit.py tests/test_observability.py -q
```

Expected: fails because CLI/artifact/metric functions are incomplete.

- [ ] **Step 3: Add metric helper**

In `app/observability/jobs.py`, add:

```python
def record_data_quality_audit_result(result: DataQualityAuditMetricSnapshot) -> None:
    recorder = get_metrics_recorder()
    for domain, ratio in result.completeness_ratios.items():
        recorder.gauge("snowcast_data_completeness_ratio", ratio, {"domain": domain})
    for item in result.entity_counts:
        recorder.gauge(
            "snowcast_data_completeness_entities",
            item.count,
            {"domain": item.domain, "status": item.status},
        )
    for item in result.gauges:
        recorder.gauge(item.name, item.value, item.labels)
```

Keep the helper independent from DB and artifact code.

- [ ] **Step 4: Implement artifact writers**

In `app/data/audit_data_quality.py`, implement:

```python
def write_audit_artifacts(
    result: DataQualityAuditResult,
    *,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data-quality-summary.json").write_text(
        json.dumps(asdict(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "data-quality-report.md").write_text(
        render_markdown_report(result),
        encoding="utf-8",
    )
```

The Markdown report should start with a summary table, then list issues by
domain in priority order.

- [ ] **Step 5: Implement audit orchestration and CLI**

Add:

```python
def run_data_quality_audit(
    *,
    database_url: str | None = None,
    archive_start_date: date,
    archive_end_date: date | None,
    source_model: str,
    output_dir: Path,
) -> DataQualityAuditResult:
    ...
```

Add `main()` with arguments:

```text
--database-url
--archive-start-date
--archive-end-date
--source-model
--minimum-evidence-seasons
--output-dir
```

Wrap CLI execution with:

```python
with configure_cli_observability(job_name="audit_data_quality"):
    with job_span("audit_data_quality"):
        result = run_data_quality_audit(...)
        record_data_quality_audit_result(result.to_metric_snapshot())
```

- [ ] **Step 6: Run focused verification**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_data_quality_audit.py tests/test_observability.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/observability app/data/audit_data_quality.py tests/test_data_quality_audit.py tests/test_observability.py
```

Expected: all tests pass and ruff reports no issues.

## Task 5: Add GitHub Actions Audit Workflow

**Files:**
- Create: `.github/workflows/audit-data-quality.yml`
- Modify: `tests/test_data_quality_audit.py` or add workflow checks to existing workflow test file if present.

- [ ] **Step 1: Write static workflow test**

Add a test that reads `.github/workflows/audit-data-quality.yml` as text and
asserts it contains:

```text
python -m app.data.audit_data_quality
actions/upload-artifact
OTEL_EXPORTER_OTLP_ENDPOINT
OTEL_EXPORTER_OTLP_HEADERS
DATABASE_URL
```

- [ ] **Step 2: Create workflow**

Create `.github/workflows/audit-data-quality.yml`:

```yaml
name: Audit Data Quality

on:
  schedule:
    - cron: "30 3 * * *"
  workflow_dispatch:
    inputs:
      archive_start_date:
        description: "First archive date expected in raw_weather_history."
        required: false
        default: "1991-01-01"
        type: string
      archive_end_date:
        description: "Latest archive date expected. Leave empty to infer from DB."
        required: false
        default: ""
        type: string
      source_model:
        description: "Derived climatology source-model/version label."
        required: false
        default: "snowcast_empirical_v1"
        type: string

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      ARCHIVE_START_DATE: ${{ inputs.archive_start_date || '1991-01-01' }}
      ARCHIVE_END_DATE: ${{ inputs.archive_end_date || '' }}
      SOURCE_MODEL: ${{ inputs.source_model || 'snowcast_empirical_v1' }}
      OTEL_ENABLED: "true"
      OTEL_SERVICE_NAME: snowcast-jobs
      OTEL_EXPORTER_OTLP_ENDPOINT: ${{ secrets.OTEL_EXPORTER_OTLP_ENDPOINT }}
      OTEL_EXPORTER_OTLP_HEADERS: ${{ secrets.OTEL_EXPORTER_OTLP_HEADERS }}
      OTEL_TRACES_SAMPLER_ARG: "1.0"
```

Add checkout, uv setup, Python setup, dependency install, database secret
validation, audit command execution, and `actions/upload-artifact@v4` for
`artifacts/data-quality`.

- [ ] **Step 3: Run tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_data_quality_audit.py -q
```

Expected: workflow static test passes.

## Task 6: Add Dashboard Panels

**Files:**
- Modify: `ops/grafana/dashboards/snowcast-production-overview.dashboard.json`
- Modify: `tests/test_grafana_dashboards.py`

- [ ] **Step 1: Write dashboard query tests**

In `tests/test_grafana_dashboards.py`, assert the dashboard includes panels with
queries for:

```text
snowcast_conditions_refresh_age_seconds
snowcast_conditions_refresh_success_total
snowcast_conditions_refresh_failure_total
snowcast_data_completeness_ratio
snowcast_data_completeness_entities
snowcast_catalog_field_groups
snowcast_catalog_trust_status
```

Also assert no new dashboard query uses deprecated `_total` snapshot names:

```python
for expr in all_dashboard_exprs:
    assert "snowcast_data_completeness_entities_total" not in expr
    assert "snowcast_catalog_field_groups_total" not in expr
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_grafana_dashboards.py -q
```

Expected: fails because the new panels are not present.

- [ ] **Step 3: Add Data Quality & Freshness row**

Update `ops/grafana/dashboards/snowcast-production-overview.dashboard.json` with
a row titled `Data Quality & Freshness`.

Recommended panels:

- stat: `Conditions age`
  - query: `max(snowcast_conditions_refresh_age_seconds)`
  - unit: seconds
- timeseries: `Conditions refresh rate`
  - success: `sum(rate(snowcast_conditions_refresh_success_total[15m]))`
  - failure: `sum(rate(snowcast_conditions_refresh_failure_total[15m]))`
- stat: `Historical archive completeness`
  - query: `max(snowcast_data_completeness_ratio{domain="historical_archive"})`
  - unit: percentunit
- stat: `Snow climatology completeness`
  - query: `max(snowcast_data_completeness_ratio{domain="snow_climatology"})`
  - unit: percentunit
- bar gauge: `Catalog completeness by field group`
  - query: `snowcast_catalog_field_groups`
- bar gauge: `Source trust coverage`
  - query: `snowcast_catalog_trust_status`

Keep panel layout compact and readable in the existing dashboard style.

- [ ] **Step 4: Validate dashboard**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_grafana_dashboards.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/validate_dashboards.py
```

Expected: tests and dashboard validation pass.

## Task 7: Update Runbooks And Engineering Notes

**Files:**
- Modify: `docs/observability-runbook.md`
- Modify: `docs/production-runbook.md`
- Modify: `docs/engineering-notes.md`

- [ ] **Step 1: Update observability runbook**

Add a section explaining:

- why job freshness panels require scheduled job OTel export;
- how to interpret data-quality completeness ratios;
- where to find `data-quality-summary.json` and `data-quality-report.md`;
- alert candidates and initial thresholds;
- that alerts start as warning/dashboard signals until baseline is clean.

- [ ] **Step 2: Update production runbook**

Add operator commands:

```bash
uv run --no-config python -m app.data.audit_data_quality \
  --database-url "$DATABASE_URL" \
  --archive-start-date 1991-01-01 \
  --archive-end-date 2026-03-01 \
  --output-dir artifacts/data-quality
```

Document the GitHub Actions workflow:

```text
GitHub Actions -> Audit Data Quality -> Run workflow
```

- [ ] **Step 3: Update engineering notes**

Add a concise note that the data-quality audit is a read-only observability
snapshot, not canonical data. The exact missing-data details live in artifacts;
Grafana receives low-cardinality summary metrics.

- [ ] **Step 4: Run doc checks**

Run:

```bash
git diff --check
```

Expected: no whitespace errors.

## Task 8: Final Verification And Feature Review

**Files:**
- Current diff
- `docs/superpowers/specs/2026-06-18-data-quality-observability-design.md`
- `docs/superpowers/plans/2026-06-18-data-quality-observability.md`

- [ ] **Step 1: Run complete focused verification**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_observability.py tests/test_data_quality_audit.py tests/test_grafana_dashboards.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/validate_dashboards.py
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/observability app/data tests/test_observability.py tests/test_data_quality_audit.py tests/test_grafana_dashboards.py
git diff --check
```

- [ ] **Step 2: Smoke audit locally with telemetry disabled**

Run against a configured local/staging database:

```bash
OTEL_ENABLED=false \
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.audit_data_quality \
  --database-url "$DATABASE_URL" \
  --archive-start-date 1991-01-01 \
  --output-dir artifacts/data-quality
```

Expected:

- command exits successfully;
- `artifacts/data-quality/data-quality-summary.json` exists;
- `artifacts/data-quality/data-quality-report.md` exists.

- [ ] **Step 3: Dry-run dashboard deploy**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python ops/grafana/scripts/deploy_dashboards.py
```

Expected: dry-run prints dashboard action without applying changes.

- [ ] **Step 4: Run advisory feature review**

Run Snowcast advisory feature-review for:

- `observability-ops`
- `data-trust-source-integrity`
- `backend-api`

Feature-review must inspect the current diff and verification output. Blocker or
High findings must be fixed before final handoff.

- [ ] **Step 5: Final handoff**

Final response must include:

- review-gated classification;
- Developer Decision Checkpoint status;
- ADR status;
- advisory design-review and feature-review status;
- verification commands and results;
- local testing command;
- GitHub Actions workflow names to run;
- dashboard deployment command.
