# Catalog Acquisition Patch PR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert reviewed catalog acquisition proposals into conservative local catalog/source-registry edits, and optionally publish those edits as a draft GitHub PR.

**Architecture:** Approved truth remains git-canonical. The acquisition runner still writes artifacts first; a separate patch command reads `proposals.json`, applies only safe new fields into `app/data/resorts.json` and `app/data/resort_acquisition/sources.json`, then writes a review summary. The GitHub Actions workflow runs acquisition, validates artifacts, runs the patch command, re-validates the catalog, and opens a draft PR only when changes exist.

**Tech Stack:** Python 3, Pydantic domain models, JSON seed catalog, GitHub Actions, `gh` CLI on GitHub-hosted runners.

**Spec:** `docs/superpowers/specs/2026-05-06-catalog-acquisition-patch-pr-design.md`

---

## File Structure

- `app/domain/models.py`: add app-facing terrain and lift-pass catalog models.
- `app/data/database.py`: persist new optional catalog fields during seed sync.
- `app/data/repositories.py`: hydrate new fields from Postgres.
- `app/data/resort_acquisition/generate_catalog_patch.py`: new conservative patch generator CLI.
- `app/data/resort_acquisition/extractors.py`, `bergfex.py`, `llm_extract.py`, `run_catalog_acquisition.py`: target terrain facts at `ski_area` entities where catalog context is available.
- `.github/workflows/catalog-acquisition.yml`: add optional draft PR creation after validation.
- `tests/test_loader.py`, `tests/test_resort_acquisition.py`: coverage for schema fields, proposal targeting, patching, and workflow behavior.
- `README.md`, `PROJECT.md`, `docs/engineering-notes.md`: document the new review and PR flow.

## Tasks

### Task 1: Add Catalog Fields

- [ ] Add/keep failing tests in `tests/test_loader.py` proving `SkiArea` accepts `total_piste_km`, `total_lift_count`, `piste_km_by_difficulty`, and `Destination` accepts `lift_pass_prices`.
- [ ] Add/keep failing tests in `tests/test_resort_acquisition.py` proving OpenDataHub and Bergfex terrain facts target the known `ski_area` entity when catalog context is available.
- [ ] Implement Pydantic models in `app/domain/models.py`:
  - `PisteKmByDifficulty`
  - `LiftPassPrice`
  - optional terrain fields on `SkiArea`
  - `lift_pass_prices` on `Destination`
- [ ] Persist new fields through `app/data/database.py` and `app/data/repositories.py`:
  - `resorts.lift_pass_prices_json`
  - `ski_areas.total_piste_km`
  - `ski_areas.total_lift_count`
  - `ski_areas.piste_km_by_difficulty_json`
- [ ] Update terrain proposal targeting in `app/data/resort_acquisition/extractors.py` and `app/data/resort_acquisition/bergfex.py`.
- [ ] Run:
  `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_loader.py tests/test_resort_acquisition.py -q`

### Task 2: Add Conservative Patch Generator

- [ ] Add failing tests in `tests/test_resort_acquisition.py` for applying safe `new` proposals into `resorts.json` and `sources.json`.
- [ ] Add failing tests proving `changed`, `conflict`, `warning`, `rejected`, and unsupported destination-scoped terrain proposals are not auto-applied.
- [ ] Implement `app/data/resort_acquisition/generate_catalog_patch.py` with CLI:
  `python -m app.data.resort_acquisition.generate_catalog_patch --artifacts-dir artifacts/catalog-acquisition`
- [ ] Patch only missing values:
  - `sources.json`: `official_urls.*` and `regional_data_ids.*`
  - `resorts.json`: `ski_areas[]` terrain fields, `season_windows`, and selected `lift_pass_prices`
- [ ] Emit `patch-review.md` listing applied and skipped proposals with reasons.
- [ ] Run:
  `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py -q`
  and
  `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`

### Task 3: Add Draft PR Workflow Mode

- [ ] Update workflow static assertions in `tests/test_resort_acquisition.py`:
  - `create_pr` defaults to `false`
  - permissions allow PR creation only for the opt-in workflow path
  - patch, validate, focused tests, and draft PR creation are gated on `create_pr=true`
- [ ] Update `.github/workflows/catalog-acquisition.yml` so default runs remain artifact-only.
- [ ] When `create_pr=true`, run the patch command, validate the patched catalog, run focused tests, and create a draft PR only if git has changes.
- [ ] Upload acquisition artifacts and patch review summary regardless of whether a PR was created.
- [ ] Run lint plus the focused test suite after workflow edits.

## Validation Gates

1. Task 1 must pass loader/acquisition tests before patch generation is implemented.
2. Task 2 must pass patch-generator tests and catalog validation before workflow PR automation is added.
3. Task 3 must keep default manual workflow runs artifact-only unless `create_pr=true`.
