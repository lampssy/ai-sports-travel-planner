# Bergfex Catalog Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configured, review-only Bergfex public-page fallback to catalog acquisition for static and semi-static resort facts.

**Architecture:** Bergfex remains outside canonical catalog truth and outside operational-status ingestion. The runner fetches only configured `provider_urls.bergfex` pages after official/open sources, parses a narrow set of atomic facts, filters them to true fallback cases, and writes ordinary proposals/evidence.

**Tech Stack:** Python, Pydantic acquisition models, stdlib HTML parsing/regex, pytest, ruff.

---

### Task 1: Model And Source Policy

**Files:**
- Modify: `app/data/resort_acquisition/models.py`
- Modify: `app/data/resort_acquisition/run_catalog_acquisition.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing model tests**

Add tests that construct a `SourceReference(source_type="bergfex", ...)` and a `CandidateFact(extraction_method="bergfex_public_page", ...)`.

- [ ] **Step 2: Run focused tests**

Run: `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_bergfex_source_type_and_extraction_method_are_valid -q`

Expected: fail because the literals are not yet accepted.

- [ ] **Step 3: Extend model literals**

Add `"bergfex_public_page"` to `ExtractionMethod` and `"bergfex"` to `SourceType`.

- [ ] **Step 4: Add CLI flag**

Add `--skip-bergfex` to the acquisition CLI.

- [ ] **Step 5: Re-run focused tests**

Run the same focused pytest command and expect it to pass.

### Task 2: Bergfex Parser

**Files:**
- Create: `app/data/resort_acquisition/bergfex.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write parser tests**

Add tests with a small Bergfex-like HTML fixture containing an external official link, elevation range, season range, open-lift summary, and piste km summary. Assert the parser emits:

- `ski_area_official_url`
- `base_elevation_m`
- `summit_elevation_m`
- `season_start_month`
- `season_end_month`
- `total_piste_km`
- `total_lift_count`

Assert it does not emit current dynamic fields such as open lift count or open piste km.

- [ ] **Step 2: Verify parser tests fail**

Run: `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_extract_bergfex_catalog_candidates_parses_static_fallback_facts tests/test_resort_acquisition.py::test_bergfex_parser_ignores_noisy_links_and_open_status -q`

Expected: fail because `app.data.resort_acquisition.bergfex` does not exist.

- [ ] **Step 3: Implement parser**

Create `bergfex.py` with:

- constants for provider key, confidence, and denied external domains
- `extract_bergfex_catalog_candidates(...)`
- stdlib anchor extraction
- regex extraction for elevation range, season dates, total piste km, and total lift count
- ski-area targets for elevation/season fields using `proposal_targets_for_single_area_source`

- [ ] **Step 4: Re-run parser tests**

Run the same focused pytest command and expect it to pass.

### Task 3: Runner Fallback Integration

**Files:**
- Modify: `app/data/resort_acquisition/run_catalog_acquisition.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write runner tests**

Add tests proving:

- configured `provider_urls.bergfex` is fetched after official/open sources and produces proposals
- `--skip-bergfex` disables the fetch
- Bergfex provider URLs are not sent through official-page LLM extraction
- Bergfex candidates are suppressed when earlier accepted source evidence already covers the same field and agrees with the catalog
- Bergfex candidates are kept when there is no earlier source evidence or earlier evidence conflicts

- [ ] **Step 2: Verify runner tests fail**

Run the new focused tests and expect missing helper/import/flag failures.

- [ ] **Step 3: Implement runner integration**

Import the Bergfex adapter, add `_extract_bergfex_fallback`, add fallback filtering, skip `provider_urls.bergfex` in official-page extraction, and run Bergfex after official-page extraction.

- [ ] **Step 4: Re-run runner tests**

Run the same focused pytest command and expect it to pass.

### Task 4: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `PROJECT.md`
- Modify: `docs/engineering-notes.md`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Update docs**

Document that Bergfex is a configured proprietary public-page fallback for static catalog review evidence only. Keep dynamic operational-status acquisition documented as separate backlog work.

- [ ] **Step 2: Run full focused verification**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/resort_acquisition tests/test_resort_acquisition.py tests/conftest.py
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
git diff --check
```

- [ ] **Step 3: Smoke run**

Run a smoke acquisition for a resort with configured Bergfex URL, or a test registry fixture if no production source mapping is added. Inspect `fetch-log.json` and `proposals.json` for `bergfex_public_page`.
