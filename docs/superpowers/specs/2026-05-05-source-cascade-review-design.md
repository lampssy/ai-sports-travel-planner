# Source Cascade and Consolidated Review Design

## Status

Ready for user review before implementation planning.

## Goal

Extend the artifact-only resort acquisition system so one run can gather
Wikidata, OSM, OpenDataHub, DEM, and official-site evidence, then produce one
field-level review packet instead of several sequential approval rounds.

This is Sprint 30 work on the existing resort-acquisition branch. Sprint 29
remains the static acquisition foundation; Sprint 30 adds source cascading,
official subpage discovery, and consolidated review.

## Decisions

- Keep approved catalog truth in `app/data/resorts.json` and
  `app/data/resort_trust_manifest.json`.
- Keep acquisition output artifact-only. No source adapter may auto-write the
  approved catalog.
- Use discovered values as temporary same-run inputs only. A Wikidata official
  URL, OSM relation ID, or discovered subpage can feed downstream adapters in
  the same run, but it is not approved until reviewed.
- Review fields, not sources. `evidence.md` should group evidence by
  `(resort_id, target, field_path)` and highlight the field recommendation.
- Keep `proposals.json` as the machine-readable per-candidate artifact.
- Use static HTML/sitemap link extraction plus LLM link classification for
  official subpage discovery in v1. Do not add Playwright or rendered-browser
  crawling in Sprint 30.
- Do not ingest dynamic operational status values in this sprint. Official
  status URLs may be discovered as pointers for a later dynamic-status sprint.

## Source Cascade

The acquisition runner should build an in-memory run context for each selected
resort:

```text
source registry + current catalog
  -> Wikidata adapter
  -> OSM adapter
  -> OpenDataHub adapter
  -> DEM sanity adapter
  -> official homepage/subpage discovery
  -> LLM link classification
  -> role-specific official-page LLM extraction
  -> Bergfex public-page fallback
  -> field-grouped evidence packet
```

The run context contains source candidates with provenance:

- configured sources from `sources.json`
- discovered sources from Wikidata, OpenDataHub, or official-site links
- source type and source URL/API endpoint
- whether the source is configured, discovered, or derived
- confidence and evidence

Configured sources win only as stable inputs. They do not suppress conflicts
from discovered evidence.

## Provider Roles

### Wikidata

Input:

- configured `regional_data_ids.wikidata_id`

Fetch:

- `https://www.wikidata.org/wiki/Special:EntityData/{qid}.json`

Extract:

- official website `P856` -> `ski_area_official_url`
- coordinate location `P625` -> destination/ski-area coordinate proposals
- OpenStreetMap relation ID `P402` -> `regional_data_ids.osm_relation_id`

Rules:

- Do not search Wikidata by resort name in v1.
- Use a clear User-Agent.
- Treat Wikidata as identity and coordinate evidence, not as ski-domain fact
  truth for base/summit, piste totals, lift count, or season dates.

Reference:

- Wikidata data access and `Special:EntityData` JSON:
  https://www.wikidata.org/wiki/Help:Data_access
- Official website property:
  https://www.wikidata.org/wiki/Property:P856
- Coordinate location property:
  https://www.wikidata.org/wiki/Property:P625
- OSM relation ID property:
  https://www.wikidata.org/wiki/Property:P402

### OSM

Input:

- configured `regional_data_ids.osm_relation_id`
- same-run discovered `P402` from Wikidata

Fetch:

- Overpass relation lookup by ID, not broad name search.

Extract:

- relation center or geometry-derived coordinate evidence

Rules:

- Do not use Nominatim for recurring bulk resort lookup.
- Do not use OSM as primary truth for base/summit elevation, piste totals, lift
  count, or season dates.
- Cache fetched source snapshots and use source logs so repeated seasonal runs
  do not re-query unnecessarily.

Reference:

- Nominatim public policy discourages bulk/systematic use and limits public
  usage to 1 request/second:
  https://operations.osmfoundation.org/policies/nominatim/
- Overpass public instance guidance:
  https://wiki.openstreetmap.org/wiki/Overpass_API

### OpenDataHub

Input:

- configured or discovered `regional_data_ids.opendatahub_ski_area_id`

Extract:

- ski-area ID
- piste/lift facts
- piste split
- trail map URL
- ski-area coordinates
- base/summit elevation
- exact `season_windows` plus derived season months from `OperationSchedule`

Rules:

- Keep the existing `ClosedData=false` license guard.
- Treat OpenDataHub `SkiArea` values as ski-area scoped.
- Mirror to destination-level fields only under the existing single-ski-area
  duplicate rule.

### DEM / OpenTopoData

Input:

- current or proposed ski-area coordinates

Fetch:

- OpenTopoData public API using the dataset stack `eudem25m,mapzen,srtm90m`.

Extract:

- point elevation at candidate/current coordinates

Rules:

- DEM output is sanity evidence, not direct replacement for skiable
  `base_elevation_m` or `summit_elevation_m`.
- Produce validation notes or warning proposals when point elevation is
  implausibly far from catalog base elevation or coordinate expectations.
- Batch locations where possible and respect public limits.

Reference:

- OpenTopoData API:
  https://www.opentopodata.org/api/
- OpenTopoData public limits include 100 locations/request, 1 call/second, and
  1000 calls/day:
  https://www.opentopodata.org/

## Official Site Discovery

Official subpage discovery starts from approved or discovered homepage seeds:

- configured official URLs in `sources.json`
- Wikidata `P856`
- OpenDataHub contact URL
- already approved catalog URLs, when present

Discovery v1 uses static fetches only:

- fetch homepage HTML
- fetch `sitemap.xml` when present
- extract normal `<a href>` links with generic HTML parsing
- fetch up to 20 first-level internal pages selected by deterministic URL/text
  scores
- no site-specific selectors
- no form submission, search box use, login, cookie interaction, or broad crawl

Each link candidate records:

- normalized absolute URL
- source page URL
- visible link text
- `title` / `aria-label`, when available
- nearby or parent text, truncated
- source page title, when available
- deterministic role scores

Scope limits:

- same hostname or direct subdomain of the official seed hostname by default
- external links are candidates only when linked from an official seed page
- maximum 100 collected links per resort before LLM classification
- maximum 40 sitemap URLs considered per resort
- maximum 3 candidate URLs per role after classification
- unsupported content types are logged and skipped

## LLM Link Classification

The LLM may classify and rerank a bounded list of link candidates. It must not
drive website navigation.

Input:

- link candidate JSON array
- target roles
- current official URL roles, when configured

Output:

- role candidates for `ski_pass`, `season_dates`, `trail_map`,
  `official_status`, and `rental`
- URL
- confidence
- short reason
- language or label clue when relevant

Rules:

- Validate LLM output against a strict JSON schema.
- Cache by homepage/source-page hashes, link-candidate hash, prompt version,
  schema version, and model.
- Deterministic domain/safety checks run after LLM classification.
- LLM classification may propose role URLs and feed same-run extraction, but it
  does not approve the URLs.

## Official-Page LLM Extraction

The existing official-page extraction should run only on narrowed role pages:

- `ski_pass` pages for adult 1-day, 3-day, and 6-day pass prices
- `season_dates` pages for exact `season_windows`, plus
  `season_start_month` and `season_end_month` derived from explicit official
  date ranges
- `trail_map` pages as map URL evidence
- `rental` pages for rental facts
- `ski_area` pages for static ski-area facts when explicitly present

This sprint should keep dynamic operational status extraction out of scope.
`official_status` pages may be discovered and proposed as URLs only.

## Bergfex Public-Page Fallback

Bergfex can be added as a proprietary public-page fallback source for
catalog/static evidence, not as a licensed or canonical provider.

Input:

- configured `provider_urls.bergfex` in `sources.json`

Fetch:

- the configured public Bergfex resort page only
- no guessed slug lookup in v1
- no `/ajax/`, `/export/`, `/download/`, image, map, app, or internal API
  endpoints

Extract:

- external official/operator website link when present as a normal page link
- elevation range -> `base_elevation_m` / `summit_elevation_m`
- explicit public season range -> exact `season_windows` plus
  `season_start_month` / `season_end_month`
- public total piste km
- public total lift count when present alongside current lift status, while
  ignoring the current open lift count

Rules:

- Run after Wikidata, OSM, OpenDataHub, DEM, official-link discovery, and
  official-page extraction.
- Keep it lower confidence than official/open sources.
- Emit Bergfex candidates only when a field lacks earlier accepted source
  evidence, when earlier source evidence conflicts, when earlier evidence
  disagrees with the current catalog, or when the current catalog value is
  missing.
- Do not feed Bergfex pages into official-site LLM extraction.
- Do not store raw Bergfex HTML in artifacts; store only URL, fetch metadata,
  atomic proposed values, and short evidence strings.
- Do not extract current open lift count, current open piste km, live operating
  status, snow depth, or daily snow-report values in this catalog pipeline.
  Those belong to a separate operational-status acquisition pipeline.

## Consolidated Review Packet

`proposals.json` remains a per-candidate artifact with source, method,
confidence, evidence, target, current value, proposed value, and status.

`evidence.md` becomes the primary human review packet. It should group by:

```text
resort
  target
    field_path
      current value
      recommended value or no single recommendation
      review status
      evidence from all sources
      conflicts and validation notes
```

Review status policy:

- `same`: summarize compactly; no manual action needed.
- `new`: review before catalog promotion.
- `changed`: review before catalog promotion.
- `conflict`: highlight as manual decision required.
- `warning`: highlight when DEM/source sanity checks find suspicious values.
- `source_failed`: include in source-health summary.

The report should surface changed/new/conflicting/warning fields first. Same
checks should be collapsible or summarized so seasonal refreshes do not become
noisy.

## CLI And Workflow

Extend the existing acquisition CLI rather than adding a new command.

Useful flags:

- `--skip-wikidata`
- `--skip-osm`
- `--skip-dem`
- `--skip-official-discovery`
- `--skip-llm-link-classification`
- `--skip-bergfex`
- `--llm-min-interval-seconds`
- `--llm-request-budget`
- `--quiet`
- `--verbose`
- existing `--skip-opendatahub`
- existing `--skip-llm`

`--skip-llm` disables both LLM link classification and official-page LLM fact
extraction.

The CLI emits per-resort/per-provider progress logs so GitHub Actions runs are
inspectable while they are still running. Transient LLM network/provider errors
are retried, then recorded as `warning` fetch-log entries if retries are
exhausted. LLM link classification sends only a capped, high-signal subset of
deterministically role-scored candidates to keep prompts bounded, and
low-confidence role assignments are ignored. Deterministic official-link scoring
uses role-specific tokens and phrases so event pages, directions links, and
incidental words do not become official-status or trail-map evidence.
Official-page LLM extraction validates returned facts and lift-pass prices item
by item, accepts only adult/default public lift-pass prices, and records invalid
child/promo price rows as warnings without discarding valid facts from the same
page. Uncached LLM calls are paced by a run-local limiter, capped by a per-run
request budget, and stopped for the rest of the run after provider quota
exhaustion. LLM auth/configuration errors remain hard failures. Same-run
discovered official URLs are optional until fetched successfully, so stale
OSM/Wikidata website tags are logged as skipped rather than failing the whole
artifact run.

The GitHub Actions artifact-only workflow should continue to upload artifacts
without committing, pushing, or opening PRs.

## Out Of Scope

- Browser-rendered crawling or Playwright fallback
- Broad search-engine discovery
- Name-based Wikidata or OSM search
- Automatic Bergfex page discovery or slug guessing
- Automated catalog writes
- Database canonical storage or new DB tables
- Dynamic open piste/lift ingestion
- Scraping aggregator snow reports
- Approval CLI or admin UI
- Full source snapshot storage of copyrighted pages

## Verification

Implementation should include mocked unit tests for:

- Wikidata claim extraction for P856, P625, and P402
- OSM relation coordinate extraction from Overpass responses
- DEM sanity warnings from OpenTopoData responses
- static HTML anchor extraction and sitemap parsing
- LLM link-classification schema validation and cache behavior
- same-run temporary source use without marking sources approved
- field-grouped evidence rendering
- skip flags disabling the intended adapters

Live smoke checks should be optional and artifact-only:

- one OpenDataHub-supported resort
- one resort with configured Wikidata/OSM IDs after IDs are added
- one official homepage discovery run with `--skip-llm` and one with mocked LLM
  in tests

All implementation must preserve existing checks:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py -q
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/resort_acquisition tests/test_resort_acquisition.py tests/conftest.py
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```
