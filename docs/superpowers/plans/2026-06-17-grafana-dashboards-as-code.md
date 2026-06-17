# Grafana Dashboards As Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store, validate, and deploy Snowcast Grafana dashboards from the repo.

**Architecture:** Keep committed dashboard resources in Grafana's dashboard
resource format under `ops/grafana/dashboards/`. Use small standard-library
Python scripts for normalization, validation, and deployment through Grafana's
Dashboard HTTP API. Keep a manifest and Terraform notes so a future Terraform
provider migration can reuse the same dashboard files.

**Tech Stack:** Python 3.13 standard library, pytest, GitHub Actions, Grafana
Cloud Dashboard HTTP API.

---

## Decision Gate Before Execution

- Classification: `review-gated`
- High-risk domains touched: observability, production reliability, CI/CD,
  external Grafana Cloud integration
- Resolved owner decisions:
  - Use script-first dashboard deployment now.
  - Keep layout and source files Terraform-friendly.
  - Use a separate Grafana service account token for dashboard deployment.
  - Keep deployment manual until the flow is proven.
- Accepted assumptions:
  - The exported dashboard at
    `/Users/awownysz/Downloads/dashboard-1781696901568.json` is the initial
    dashboard source.
  - `GRAFANA_DASHBOARD_NAMESPACE` is `stacks-1693732` in the user's current
    Grafana Cloud stack.
- Unresolved owner decisions: None.
- ADR status: not needed for this reversible operational slice.
- Advisory review status: `observability-ops` feature-review completed before
  final handoff with no blocking findings.

## File Structure

- Create `ops/grafana/scripts/dashboard_resources.py`: shared parsing,
  sanitization, validation, manifest loading, and Grafana API client helpers.
- Create `ops/grafana/scripts/normalize_dashboard.py`: CLI to sanitize an
  exported dashboard into the canonical repo format.
- Create `ops/grafana/scripts/validate_dashboards.py`: CI-friendly validation
  entry point.
- Create `ops/grafana/scripts/deploy_dashboards.py`: dry-run/apply dashboard
  deploy entry point.
- Create `ops/grafana/dashboards.manifest.json`: dashboard registry consumed by
  scripts and later Terraform.
- Create `ops/grafana/dashboards/snowcast-production-overview.dashboard.json`:
  sanitized Snowcast Production Overview dashboard.
- Create `ops/grafana/README.md`: local and GitHub usage.
- Create `ops/grafana/terraform/README.md`: migration notes.
- Create `.github/workflows/validate-grafana-dashboards.yml`: PR-safe
  validation.
- Create `.github/workflows/deploy-grafana-dashboards.yml`: manual deployment.
- Create `tests/test_grafana_dashboards.py`: focused unit tests.

## Tasks

### Task 1: Shared Dashboard Resource Helpers

**Files:**
- Create: `ops/grafana/scripts/dashboard_resources.py`
- Create: `tests/test_grafana_dashboards.py`

- [x] Write failing tests for sanitization and validation.
- [x] Run `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_grafana_dashboards.py -q` and confirm the helpers are missing.
- [x] Implement dashboard resource normalization and validation.
- [x] Run the focused test and confirm it passes.

### Task 2: Manifest And CLI Entry Points

**Files:**
- Modify: `ops/grafana/scripts/dashboard_resources.py`
- Create: `ops/grafana/scripts/normalize_dashboard.py`
- Create: `ops/grafana/scripts/validate_dashboards.py`
- Create: `ops/grafana/scripts/deploy_dashboards.py`
- Modify: `tests/test_grafana_dashboards.py`

- [x] Write failing tests for manifest loading and mocked deploy create/update
  behavior.
- [x] Run the focused test and confirm it fails for missing behavior.
- [x] Implement manifest loading, CLI scripts, and the Grafana API client.
- [x] Run the focused test and confirm it passes.

### Task 3: Dashboard Asset And Docs

**Files:**
- Create: `ops/grafana/dashboards.manifest.json`
- Create: `ops/grafana/dashboards/snowcast-production-overview.dashboard.json`
- Create: `ops/grafana/README.md`
- Create: `ops/grafana/terraform/README.md`

- [x] Normalize the exported dashboard into the repo dashboard path.
- [x] Validate the committed dashboard with `validate_dashboards.py`.
- [x] Document required environment variables, dry-run/apply commands, and
  Terraform migration expectations.

### Task 4: GitHub Workflows

**Files:**
- Create: `.github/workflows/validate-grafana-dashboards.yml`
- Create: `.github/workflows/deploy-grafana-dashboards.yml`

- [x] Add PR/push validation for dashboard JSON and scripts.
- [x] Add manual deploy workflow with required Grafana environment variables.
- [x] Parse workflow YAML locally with Python.

### Task 5: Verification And Review

**Files:**
- Inspect current diff

- [x] Run focused pytest.
- [x] Run ruff for Grafana scripts and tests.
- [x] Run dashboard validation.
- [x] Run deploy dry-run.
- [x] Run YAML parse check.
- [x] Run `git diff --check`.
- [x] Run `observability-ops` feature-review on the current diff.
