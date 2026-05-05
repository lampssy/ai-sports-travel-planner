# Static Resort Data Acquisition Design

## Goal

Build the first automated acquisition loop for static and semi-static resort catalog facts. The system should reduce manual research effort while preserving human review and git-based catalog approval.

Approved catalog truth remains in:

- `app/data/resorts.json`
- `app/data/resort_trust_manifest.json`

The acquisition system produces proposals and evidence only. The app must not read unapproved acquisition output.

## Decisions

- Use the hybrid model: approved catalog values stay in git, acquisition runs produce separate proposal/evidence artifacts.
- Use PR-style review material, meaning diff-like proposal and evidence files; v1 GitHub Actions output is artifacts-only and does not create PRs.
- Include LLM extraction for narrow official-page extraction.
- Exclude dynamic operational status from this sprint: no open piste km, open piste count, open lift count, live resort status, or daily snow-report values.
- Include stable denominators and source pointers that later operational-status work will need.

## Architecture

Add a focused acquisition subsystem under `app/data/resort_acquisition/`:

```text
source registry
  -> source adapters and official-page fetchers
  -> deterministic extraction and LLM extraction
  -> normalized candidate facts
  -> comparison against current catalog
  -> artifact-only proposal/evidence output
```

The subsystem has these responsibilities:

- Load a source registry for each resort.
- Fetch only configured URLs and supported open/official APIs.
- Extract candidate facts using deterministic adapters first.
- Use LLM extraction only for configured official pages and narrow schemas.
- Compare candidates with the current catalog.
- Generate machine-readable proposals and a Markdown evidence packet.
- Generate a fetch log with source status, hashes, timestamps, and extraction method.

## Field Scope

### Static Resort Facts

The acquisition pipeline may propose:

- `total_piste_km`
- `total_lift_count`
- `piste_km_by_difficulty`
- `ski_area_official_url`
- `ski_pass_url`
- `rental_url`
- `season_dates_url`
- `trail_map_url`
- `official_status_url`
- `regional_data_ids`
- `osm_relation_id`
- `wikidata_id`

`official_status_url` is only a pointer for future work. The v1 pipeline must not extract live status values from it.

### Semi-Static Lift Pass Prices

Lift-pass prices are represented as a list of structured price candidates. The v1 targets are:

- adult 1-day price
- adult 3-day price, when present
- adult 6-day price, when present
- currency
- season or validity label
- price kind: `fixed`, `from`, `range`, or `unknown`

Candidate shape:

```json
{
  "duration_days": 6,
  "audience": "adult",
  "amount": 390,
  "currency": "EUR",
  "price_kind": "fixed",
  "season_label": "2025/26 winter",
  "source_url": "https://example.com/prices",
  "confidence": 0.9
}
```

### Semi-Static Rental Facts

The acquisition pipeline may propose:

- rental provider name
- official or provider URL
- representative rental price range, when available
- rental quality tier, when evidence supports it
- lift-distance proposal only when source or location evidence supports it

## Source Strategy

### Official URL Role Contract

Official resort websites rarely expose one clean page per catalog field. The
source registry therefore models configured pages by role, not by individual
field. A single official URL may support more than one role when the same page
contains multiple kinds of evidence.

Supported `official_urls` roles:

- `ski_area`: primary official ski-area or resort facts page. Prefer this first;
  it can support piste kilometers, lift count, elevation range, difficulty split,
  terrain overview, map links, and sometimes season dates.
- `ski_pass`: official lift-pass or prices page. Use for adult 1-day, 3-day, and
  6-day lift-pass price extraction when explicitly listed.
- `season_dates`: official opening dates, winter season, or operating-calendar
  page. Use only when season dates are not clearly available on the `ski_area`
  page.
- `trail_map`: official piste-map page or PDF. Use as map evidence and later
  richer terrain extraction; it should not be treated as live status.
- `official_status`: official lift/piste/status page. Store as a pointer for
  future reported operational status work; the current acquisition pipeline must
  not extract live open/closed values from it.
- `rental`: official rental partner page or configured rental provider page.
  Useful for representative rental facts, but lower priority than ski-area,
  ski-pass, and season evidence.

When one page covers several roles, the current registry may repeat the same URL
under several roles. That is acceptable for review output, but future work should
consider a `url + roles[]` registry shape to avoid duplicate fetches and duplicate
LLM extraction calls.

Important current limitation: official-page LLM extraction can propose the
`season_dates_url` pointer, but it does not yet extract normalized season start
and end dates/months from official pages. OpenDataHub operation schedules can
propose season-month fields for supported resorts; broader official-page season
date extraction should be added before relying on `season_dates` pages for
non-OpenDataHub resorts.

### Deterministic Sources First

Use deterministic sources before LLM extraction:

- current `resorts.json` as the baseline
- configured official resort URLs
- OpenDataHub for South Tyrol ski-area facts and IDs where applicable
- configured or deterministic OSM/Wikidata IDs

Deterministic candidates must include source URL, source type, extraction method, timestamp, and confidence.

### LLM Extraction Second

LLM extraction is allowed only for configured official or provider pages:

- official ski pass page
- official season/opening page
- official resort facts page
- official or configured rental provider page

LLM extraction rules:

- The prompt requests only the fields in the extraction schema.
- Every non-null extracted value must include an evidence snippet.
- Every extracted value must include confidence.
- Missing values must be returned as `null`.
- The LLM must not infer prices or facts from unrelated text.
- Aggregator pages must not be used as source-of-truth LLM inputs for this sprint.
- LLM output never marks a field as verified automatically.

Use a cache key based on URL, content hash, extraction schema version, and prompt version.

## Proposal And Evidence Output

The v1 command writes an output directory such as:

```text
artifacts/catalog-acquisition/
  proposals.json
  evidence.md
  fetch-log.json
  source-snapshots/
```

`proposals.json` contains normalized candidate facts and comparisons against the current catalog.

`evidence.md` is a human-readable report grouped by resort and field, including:

- current value
- proposed value
- source URL
- evidence snippet
- extraction method
- confidence
- conflict or validation notes

`fetch-log.json` records:

- URL or API endpoint
- fetch timestamp
- status
- content hash
- extraction method
- truncation flag
- error message, when applicable

`source-snapshots/` may store compact extracted text, hashes, and metadata. It should avoid storing full copyrighted pages unless the source terms are safe.

## CLI And GitHub Workflow

Add a local command with this shape:

```bash
uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition \
  --resort tignes \
  --output-dir artifacts/catalog-acquisition
```

Supported inputs:

- repeated `--resort`
- optional `--country`
- `--output-dir`
- `--max-pages-per-resort`
- `--skip-llm`

Add `.github/workflows/catalog-acquisition.yml` as a manual workflow only:

- trigger: `workflow_dispatch`
- permissions: `contents: read`
- inputs: resort targets, country, skip LLM, max pages per resort
- install with `uv sync --dev --no-config`
- run the existing catalog validator first
- run the acquisition command
- upload the artifact bundle

The workflow must not commit, create branches, open PRs, or push to `main`.

## Review And Approval

Human review happens outside the acquisition command:

1. Run the workflow or local CLI.
2. Inspect `evidence.md` and `proposals.json`.
3. Apply accepted values manually or with a separate reviewed patch to:
   - `app/data/resorts.json`
   - `app/data/resort_trust_manifest.json`
4. Run the catalog validator.

The acquisition output is review material, not application data.

## Error Handling

- Source fetch failures are recorded in `fetch-log.json` and `evidence.md`; they do not fail the whole run unless every source for a selected resort fails.
- LLM provider failures produce deterministic-only output for that resort when possible.
- Invalid LLM JSON is recorded as an extraction error and ignored for proposals.
- Conflicting source values are reported as conflicts; v1 does not auto-resolve them.
- Candidate values that fail basic validation are included only as rejected/flagged evidence, not as normal proposals.

## Testing

Implementation should use TDD. Tests should cover:

- source registry loading and validation
- deterministic candidate creation
- official-page LLM extraction using a fake LLM client
- candidate comparison against current catalog values
- proposal JSON generation
- Markdown evidence generation
- CLI output files
- artifact-only GitHub workflow shape and permissions
- existing catalog validator compatibility

Tests must not depend on live official resort pages or real LLM calls.

## Rollout

Start locally with deterministic extraction:

```bash
uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition \
  --resort tignes \
  --skip-llm \
  --output-dir artifacts/catalog-acquisition
```

Then test LLM extraction against one or two configured resorts.

Then run the manual GitHub Action and inspect artifacts.

Do not add scheduled runs until proposal quality, source failure reporting, and LLM noise are acceptable.

## Out Of Scope

- Open piste km or lift-status ingestion
- Licensed aggregator ingestion
- DB-canonical catalog storage
- Proposal tables
- Admin review UI
- GitHub PR creation
- Automatic edits to `resorts.json` or `resort_trust_manifest.json`
