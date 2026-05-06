# AI Sports Travel Planner

## Project Overview
AI Sports Travel Planner helps athletes plan ski trips with structured destination recommendations, stay-base options, ski-area-aware conditions, and rental suggestions. The backend exposes deterministic APIs for search and trip companion flows, leaving AI-specific features as thin supporting layers rather than ranking owners.

## Features
- Search ski resorts by country, budget, quality level, skill level, and lift-distance preference
- Add an optional travel window, either month-level or exact dates, so resort ranking can reflect planning confidence for a selected window
- Return ranked destination matches with one selected ski area, one selected stay base, and one rental option
- Include lightweight weather/snow conditions, structured explanation output, provenance metadata, planning summaries, and confidence metadata in search results
- Add a grounded recommendation narrative for the top-ranked search result
- Surface a tracked outbound accommodation CTA that routes through the backend before redirecting to the external booking target
- Save one authenticated current trip per user from the mobile selected-result flow with a booking status for later companion features
- Switch into a dedicated mobile `Current trip` view with trip-specific current conditions and change tracking since the last explicit check
- Attach exact trip dates to the saved current trip and use them for companion relevance and notification eligibility
- Record deterministic companion events for meaningful current-trip condition changes and expose them as in-app history
- Expose snow-confidence and weather-derived disruption signals in search results
- Load curated Alpine resort data through Postgres-backed repositories
- Validate the explicit resort catalog and trust manifest before catalog changes
- Refresh real resort conditions from Open-Meteo into Postgres through an internal command
- Parse free-text ski trip queries with LLM-first extraction and heuristic fallback
- Structured JSON responses for backend/API consumers
- React/Vite demo frontend with brief-first search, inferred filter chips, a secondary refine panel, and accommodation booking CTA
- Backend-rendered public resort guide pages under `/ski-resorts/{resort_id}` with an evergreen historical conditions calendar, SEO metadata, sitemap, and robots.txt
- Flutter mobile scaffold with Google sign-in, backend bearer-token exchange, mobile search, and current-trip flow
- Resort-level booking handoff plus anchored current-trip save flow in the mobile selected-result panel
- Seed the first linked-area glacier validation destinations: Hintertux, Stubai Glacier, and Zell am See-Kaprun

## Tech Stack
- Python 3.11+
- FastAPI
- Gemini Developer API
- PostgreSQL
- Pytest
- Playwright
- Docker (optional)
- uv for project and environment management

## Getting Started
1. Install `uv` (following Astral instructions):
```bash
curl -sSf https://install.astral.sh | sh
```

2. Clone the repository:
```bash
git clone <repo-url>
cd ai-sports-travel-planner
```

3. Create the project environment and install dependencies:
```bash
uv sync --dev
```

If your global `uv` config points at a private package index, use:
```bash
UV_CACHE_DIR=.uv-cache uv sync --dev --no-config
```

4. Start local Postgres:
```bash
docker compose up -d postgres
```

5. Copy the example env and adjust only if you need non-default values:
```bash
cp .env.example .env
```

6. Run tests:
```bash
uv run pytest
```

7. Install local pre-commit hooks:
```bash
uv run pre-commit install
```

8. Bootstrap the local database:
```bash
uv run python -m app.data.bootstrap_database
```

To validate the checked-in resort catalog, trust manifest, and source refs for source-backed trust statuses:
```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```

To generate local catalog acquisition proposals from configured official/open sources,
regional open-data providers, DEM sanity checks, narrowed official-site pages, and
configured fallback providers:
```bash
uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition --resort alta-badia --skip-llm --output-dir artifacts/catalog-acquisition
```

The acquisition cascade is artifact-only. It can use:
- OpenDataHub discovery and detail fetches for supported ski areas
- configured or Wikidata-derived official websites and OSM relation IDs as
  temporary same-run inputs
- OSM and Wikidata facts for source-backed coordinates and identifiers
- OSM fallback discovery around catalog coordinates when Wikidata is weak,
  proposing likely ski-area official URLs and OSM relation IDs for review
- DEM elevation checks as warnings, not replacement elevation facts
- static official-link discovery from homepages, sitemaps, and first-level links
  without a browser runtime
- optional LLM link classification and official-page fact extraction on narrowed
  role pages
- configured Bergfex public resort pages as a last-resort, lower-confidence
  fallback for static review evidence only

OpenDataHub discovery fetches the public `SkiArea` index once per run and proposes
`regional_data_ids.opendatahub_ski_area_id` when a selected resort has one exact
normalized name match. The proposal still requires human review before promotion.
For configured or same-run discovered OpenDataHub ski areas, proposals can also
check existing source-backed coordinates, elevations, season-month fields, and
exact `season_windows` when source pages publish full opening/closing dates.
Month fields remain compatibility fallbacks when exact dates are unavailable.
Those proposals include an explicit `target` so reviewers can distinguish
destination-level travel/display fields from nested `ski_areas[]`
weather/model fields.

Useful skip flags:
- `--skip-llm` disables both LLM link classification and official-page fact
  extraction.
- `--skip-opendatahub`, `--skip-wikidata`, `--skip-osm`, and `--skip-dem`
  disable deterministic/open-data providers independently.
- `--skip-official-discovery` disables static official-site link discovery.
- `--skip-llm-link-classification` keeps official-page LLM fact extraction
  enabled but disables LLM classification of discovered official links.
- `--skip-bergfex` disables configured Bergfex public-page fallback extraction.
- `--llm-min-interval-seconds` controls the delay between uncached LLM provider
  calls. The default `15` seconds is conservative for a 5-RPM free tier; use `0`
  or a smaller value only when the provider tier allows it.
- `--llm-request-budget` limits uncached LLM provider calls in one acquisition
  run. The default `20` prevents a single run from exceeding a 20-RPD free tier;
  use `0` for unlimited on a paid/higher-limit tier.
- `--quiet` suppresses normal progress logs; `--verbose` also shows third-party
  HTTP client request logs.

Configured official pages use source roles such as `ski_area`, `ski_pass`,
`season_dates`, `trail_map`, `official_status`, and `rental`. The role contract
and prioritization guidance live in
[`docs/superpowers/specs/2026-05-04-static-resort-data-acquisition-design.md`](docs/superpowers/specs/2026-05-04-static-resort-data-acquisition-design.md).

Configured Bergfex pages use `provider_urls.bergfex` in
`app/data/resort_acquisition/sources.json`. Bergfex pages are not treated as
official pages and are not sent to official-page LLM extraction. The fallback
extracts only atomic static/semi-static facts such as official/operator links,
elevation range, exact season windows plus derived season months, total piste
km, and total lift count. Current open lifts, open piste km, snow depth, and
live operating status belong to the separate operational-status acquisition
backlog, not the catalog pipeline.

The command writes review artifacts under the output directory:
- `proposals.json` for normalized candidate facts and current-value comparisons
- `evidence.md` for human review by resort and field
- `fetch-log.json` for source status, timestamps, hashes, warnings, and errors

To turn only conservative safe proposals into local review edits:
```bash
uv run --no-config python -m app.data.resort_acquisition.generate_catalog_patch --artifacts-dir artifacts/catalog-acquisition
```

The patch command only fills missing values. It can add reviewed ski-area terrain
facts under `ski_areas[]`, destination `lift_pass_prices`, exact
`season_windows`, and missing source-registry URLs/IDs. Changed values,
conflicts, warnings, rejected proposals, and destination-scoped terrain facts
remain in `evidence.md`/`patch-review.md` for manual review.

The manual **Catalog Acquisition** GitHub Actions workflow remains artifact-only
by default. Set `create_pr=true` to run the conservative patch command after a
successful acquisition, validate the patched catalog, run focused tests, and
open a draft PR only when `resorts.json` or `sources.json` changed.

Accepted values must still be applied through reviewed changes to `app/data/resorts.json` and `app/data/resort_trust_manifest.json`, followed by:
```bash
uv run --no-config python -m app.data.validate_resort_catalog
```

The acquisition command logs per-provider progress while running, which makes
scheduled or manual GitHub Actions runs easier to follow before artifacts are
uploaded. Transient LLM network/provider errors are retried; if retries are
exhausted, LLM extraction is recorded as `warning` and the review packet is still
generated. Deterministic official-link discovery uses role-specific token and
phrase scoring so generic event pages, directions links, and incidental words do
not become ski-status or trail-map proposals. LLM link classification sends only a
capped, high-signal subset of deterministically role-scored link candidates,
filters low-confidence role assignments, and avoids oversized prompts. Official
page LLM extraction validates returned facts and prices item by item, and accepts
only adult/default public lift-pass prices; a bad child/promo price item becomes a
warning without discarding other valid facts from the page. Uncached LLM calls are
paced by a run-local limiter, and a quota response disables further provider calls
for the rest of the run so later pages become warnings instead of more
quota-consuming requests. Auth/configuration LLM errors remain hard failures.
Same-run
discovered official URLs are treated as optional until validated, so a stale OSM
or Wikidata URL is logged as `skipped` instead of failing the whole run.

For a free-tier validation run, keep the resort set small and cap the LLM budget
explicitly, for example:
```bash
uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition --resort stubai-glacier --llm-min-interval-seconds 15 --llm-request-budget 4 --output-dir artifacts/catalog-acquisition-stubai
```
If the daily provider limit is already exhausted before the command starts, no
local timeout can make the provider accept requests; use `--skip-llm`, wait for
the quota reset, or use a higher-limit key.

The acquisition command can return non-zero while still writing artifacts. Exit
`1` means one or more hard fetch or extraction failures were recorded in
`fetch-log.json`; `warning` and `skipped` entries do not trigger exit `1`. Exit
`2` means no accepted candidates were generated.

9. Run the backend:
```bash
uv run python -m app.main
```

To enable the LLM-backed parser and top-result narrative:
```bash
export GEMINI_API_KEY=...
```

Optional model override:
```bash
export GEMINI_MODEL=gemini-3.1-flash-lite-preview
```

You can also place these in a local `.env` file in the repo root:
```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.1-flash-lite-preview
GOOGLE_OAUTH_CLIENT_IDS=your-google-web-client-id.apps.googleusercontent.com,your-google-ios-client-id.apps.googleusercontent.com
```

The app loads `.env` automatically for local development. Keep this file local only; it is ignored by git.

10. Refresh real conditions data into Postgres:
```bash
uv run python -m app.data.refresh_conditions
```

To recompute rows even when cached conditions are still fresh:
```bash
uv run python -m app.data.refresh_conditions --force
```

To refresh only selected resorts by exact resort id or exact resort name:
```bash
uv run python -m app.data.refresh_conditions --resort tignes
uv run python -m app.data.refresh_conditions --force --resort "St Anton am Arlberg"
```

The refresh command now operates on ski areas under the hood. Legacy one-ski-area destinations still work via their destination id/name, while multi-area destinations such as `zell-am-see-kaprun` can be refreshed by destination id or by exact ski-area id/name.

11. Backfill raw historical weather data into Postgres:
```bash
uv run python -m app.data.backfill_historical_weather --start-date 2021-01-01 --end-date 2026-01-01
```

To backfill only selected resorts or ski areas, repeat `--resort`:
```bash
uv run python -m app.data.backfill_historical_weather --start-date 2021-01-01 --end-date 2026-01-01 --resort tignes
uv run python -m app.data.backfill_historical_weather --start-date 2021-01-01 --end-date 2026-01-01 --resort "St Anton am Arlberg"
```

The backfill command stores date-level raw weather history in Postgres for three deterministic elevation bands per ski area:
- `base`: ski-area base elevation
- `mid`: midpoint between base and summit
- `upper`: 90% of the base-to-summit elevation range

Month-aware planning and display metrics use `mid` by default. `upper` rows are retained for future upper-mountain evidence, but they do not drive default public/search metrics because summit-biased snow-depth data can be unrealistic for normal trip planning.

Raw weather rows include snowfall, snow depth, temperature, wind, weather code, precipitation/rain duration and amount, apparent temperature, cloud cover, and sunshine duration. Forecast rows can also store visibility when the forecast provider returns it; Open-Meteo archive rows leave visibility empty because historical visibility is not available there.

After deploying the banded weather schema, rebuild existing archive rows so old summit-biased rows are replaced by explicit banded data:
```bash
uv run python -m app.data.backfill_historical_weather --start-date 2021-01-01 --end-date 2026-01-01 --rebuild
```

Search results and public resort pages derive optional historical metrics from mid-mountain archive rows, including mid-mountain typical snow depth, average daily snowfall, average max temperature, wind gusts, historical season coverage, and latest observed archive date. Metrics stay empty when mid-band archive data is missing.

Recommendation semantics:
- `min_price` and `max_price` are nightly stay-base budget estimates in EUR.
- `stars` is a compatibility parameter for minimum internal quality tier: `1=budget`, `2=standard`, `3=premium`.
- rental price is shown separately and is not part of budget filtering.
- `availability_status` is currently a weather-derived disruption signal, not official lift-operation status, unless future provenance is explicitly `reported`.

If you would rather run the backfill against the deployed Neon database through GitHub Actions, use the manual workflow:
- `.github/workflows/backfill-historical-weather.yml`
- Actions -> `Backfill Historical Weather` -> `Run workflow`
- inputs:
  - `start_date`
  - `end_date`
- optional `chunk_days`
- optional comma-separated `resort_targets`
- optional `rebuild` to delete selected archive rows before refetching banded data

To reconcile recent provisional forecast rows with archive truth, run:
```bash
uv run python -m app.data.reconcile_recent_archive --lookback-days 7
```

The reconciliation command reuses the archive backfill path for a rolling recent window ending at yesterday in UTC and force-refetches that window so existing forecast rows are replaced by archive rows when available.

12. Install frontend dependencies:
```bash
cd frontend
npm install
```

13. Run the frontend demo:
```bash
npm run dev
```

14. Open:
- `http://localhost:8000/docs` to inspect backend endpoints
- `http://localhost:5173` to use the frontend demo
- `http://localhost:8000/ski-resorts/tignes` to inspect a server-rendered public resort page
- `http://localhost:8000/sitemap.xml` to inspect generated public resort URLs

For a single-URL production-style local run, build the frontend first:
```bash
cd frontend
npm run build
cd ..
uv run python -m app.data.bootstrap_database
uv run python -m app.main
```

Or use the helper script from the repo root:
```bash
./scripts/run-built-app.sh
```

You can pass through normal Uvicorn flags, for example:
```bash
./scripts/run-built-app.sh --port 8001
```

Optional runtime configuration:
```bash
export DATABASE_URL=postgresql://planner:planner@127.0.0.1:5432/ai_sports_travel_planner
export TEST_DATABASE_URL=postgresql://planner:planner@127.0.0.1:5432/ai_sports_travel_planner_test
export FRONTEND_DIST_DIR=/absolute/path/to/frontend/dist
```

## API Endpoints
- Public pages:
  - `GET /ski-resorts/{resort_id}`
  - `GET /sitemap.xml`
  - `GET /robots.txt`
- `GET /api/search?location=France&min_price=150&max_price=320&stars=2&skill_level=intermediate&lift_distance=medium&budget_flex=0.1&travel_month=2`
- `GET /api/search?location=France&min_price=150&max_price=320&stars=2&skill_level=intermediate&trip_start_date=2026-03-08&trip_end_date=2026-03-12`
- `POST /api/parse-query` with JSON body `{ "query": "cheap france ski trip close to lift for intermediate in March" }`
- `POST /api/parse-query` can also extract exact date windows such as `{ "query": "France intermediate ski trip 9 Apr to 16 Apr" }`
- `GET /api/healthz`
- `GET /api/readyz`
- `POST /api/auth/google/sign-in`
- `GET /api/current-trip` (authenticated)
- `GET /api/current-trip/summary` (authenticated)
- `GET /api/current-trip/events` (authenticated)
- `PUT /api/current-trip` (authenticated)
- `POST /api/current-trip/mark-checked` (authenticated)
- `POST /api/devices/register` (authenticated)
- `DELETE /api/current-trip` (authenticated)

Debug helpers for local testing:
- `POST /api/parse-query?debug=true`
- `GET /api/search?...&debug=true`

`debug=true` can now distinguish compact typed LLM/provider failures such as:
- `quota_error`
- `auth_error`
- `network_error`
- `provider_error`

`/search` results now include:
- resort id
- region
- selected ski area name
- selected stay base name
- conditions summary
- conditions provenance
- optional planning summary
- optional planning provenance
- optional planning evidence count
- best travel months
- conditions score
- snow confidence score
- snow confidence label
- disruption status through the compatibility field `availability_status`
- explanation:
  - highlights
  - risks
  - confidence contributors
- recommendation narrative
- recommendation confidence

Contract hardening in this phase keeps the API semantics close to the code:
- request and response semantics are described in the Pydantic models
- seed data uses stable `resort_id` values and geographic `region`
- the place model now distinguishes destination, ski area, and stay base while still keeping one row per destination in search
- current live Open-Meteo conditions are surfaced as `forecast` signals
- planning remains surfaced as `estimated`, but provenance now distinguishes `forecast_assisted`, `archive_backed`, and `fallback_heavy` planning evidence profiles
- outbound accommodation links are currently resort-level Booking.com search deep links generated behind the redirect endpoint
- current trip persistence is now one backend-owned record per authenticated user
- the companion surface reads from a dedicated current-trip summary endpoint and only advances its comparison baseline when `mark-checked` is called
- exact saved-trip dates now live in the current-trip model and drive trip-window-aware companion eligibility
- current-trip companion events are backend-owned records deduplicated by deterministic event signatures

## Mobile Client

The first Flutter mobile scaffold lives in [mobile/README.md](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/mobile/README.md).

It currently covers:
- Google sign-in on device
- backend token exchange through `/api/auth/google/sign-in`
- mobile search and trip-brief parsing
- saving one current trip per authenticated user, including exact trip dates when known
- loading current-trip summary, trip relevance, and companion event history
- marking the comparison baseline checked explicitly

Run it after starting the backend:

```bash
cd mobile
flutter pub get
flutter run \
  --dart-define=API_BASE_URL=http://10.0.2.2:8010/api \
  --dart-define=GOOGLE_SERVER_CLIENT_ID=your-google-server-client-id
```

Important:
- the web frontend remains anonymous in this sprint
- current-trip persistence is now mobile-auth-only
- native Google sign-in platform setup is still required before the mobile login flow will work
- backend `GOOGLE_OAUTH_CLIENT_IDS` should include every allowed client audience you use in development, typically at least the web client and the iOS client

## Quality Checks
Local commits run fast quality hooks through `pre-commit`:
```bash
uv run pre-commit install
```

Manual commands:
```bash
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .
uv run pytest
```

Frontend commands:
```bash
cd frontend
npm run test
npm run test:e2e
npm run build
```

GitHub Actions runs lint, formatting checks, and tests on pushes and pull requests. A separate deploy workflow runs on push to `main`.

## Deployment
Sprint 11 targets a single public URL with FastAPI serving the built frontend and API together.

Included deployment assets:
- `Dockerfile` for a combined backend + built frontend image
- `fly.toml` for a Fly.io deployment with one web process plus a release bootstrap step
- `docker-compose.yml` for local Postgres
- `.github/workflows/deploy.yml` for deploy-on-push-to-main CI/CD
- `.github/workflows/refresh-conditions.yml` for scheduled/manual conditions refresh against Neon
- `.github/workflows/reconcile-recent-archive.yml` for scheduled/manual recent archive reconciliation against Neon

Expected hosted environment variables:
- `DATABASE_URL` (Neon Postgres connection string)
- `GEMINI_API_KEY`
- optional `GEMINI_MODEL`

Production runbook:
- [`docs/production-runbook.md`](docs/production-runbook.md)

## Project Structure
```text
ai-sports-travel-planner/
├── AGENTS.md         # Codex instructions
├── docs/             # Engineering notes and future project documentation
├── frontend/         # React/Vite/Tailwind demo frontend
├── PROJECT.md        # Project plan / roadmap
├── app/              # Backend logic
│   ├── ai/           # Query parsing helpers
│   │                  # plus direct Gemini parser/narrative helpers
│   ├── data/         # Resort seed, Postgres bootstrap command, repositories, refresh command
│   ├── integrations/ # Weather/provider normalization boundaries
│   └── domain/       # Models, ranking, and search logic
├── tests/            # Unit & integration tests
├── pyproject.toml
└── README.md         # This file
```

Additional reference:
- [docs/engineering-notes.md](docs/engineering-notes.md) for curated technical notes, tradeoffs, and learning-oriented explanations tied to this project
- [docs/planning-model.md](docs/planning-model.md) for the canonical planning model spec, evidence profiles, and tuning-policy overview
