# Snowcast

## Project Overview
Snowcast helps skiers compare clear trip options for their dates, must-haves, and preferences. Each option explains snow conditions, a recommended place to stay, and practical travel details; searching for stays is kept separate from that planning guidance.

## Features
- Search trip options by country, budget, stay quality, skill level, and lift-access preference
- Add an optional travel window, either month-level or exact dates, so trip options can reflect planning confidence for that window
- Add optional car-first travel effort from a user origin, with max-drive filtering, travel tolerance, result badges, and provider/provenance caveats
- Return trip options with a destination, recommended place to stay, selected ski area, access details, lift pass, and alternatives
- Keep property-level hotel and apartment suggestions as future work; current accommodation handoff is a destination-level Booking.com search
- Include lightweight weather/snow conditions, structured explanation output, provenance metadata, planning summaries, and confidence metadata in search results
- Surface a tracked outbound accommodation CTA that routes through the backend before redirecting to the external booking target
- Save one authenticated current trip per user from the mobile selected-result flow with a booking status for later companion features
- Switch into a dedicated mobile `Current trip` view with trip-specific current conditions and change tracking since the last explicit check
- Attach exact trip dates to the saved current trip and use them for companion relevance and notification eligibility
- Record deterministic companion events for meaningful current-trip condition changes and expose them as in-app history
- Expose snow-confidence and weather-derived disruption signals in search results
- Load the normalized Alpine trip-market catalog through Postgres-backed repositories
- Validate the canonical catalog graph and trust manifest before catalog changes
- Refresh real resort conditions from Open-Meteo into Postgres through an internal command
- Parse free-text ski trip queries with LLM-first extraction and heuristic fallback
- Show bounded clarification cards when a parsed trip brief has high-impact ambiguity such as nightly-vs-total budget, duration, party size, or origin intent
- Structured JSON responses for backend/API consumers
- React/Vite demo frontend with brief-first search, inferred filter chips, a secondary refine panel, and accommodation booking CTA
- Backend-rendered public stay-destination guide pages under `/ski-destinations/{stay_destination_id}` with area-labeled conditions, an evergreen historical calendar, SEO metadata, sitemap, and robots.txt
- Flutter mobile scaffold with Google sign-in, backend bearer-token exchange, mobile search, and current-trip flow
- Destination-level accommodation search handoff plus anchored current-trip save flow in the mobile selected-result panel
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

To validate the checked-in catalog graph and trust manifest:
```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog \
  --catalog-path app/data/catalog.json \
  --trust-manifest-path app/data/resort_trust_manifest.json
```

### Static catalog curation

Slow-changing resort, ski-area, stay-base, rental, terrain, price, and season
facts are maintained through source-backed curation, not the retired static
catalog acquisition workflow. Use the `snowcast-catalog-curation` Codex skill
for this work. Approved truth remains in `app/data/catalog.json` and
`app/data/resort_trust_manifest.json`.

Standalone curation owns its normal draft-PR workflow. When the local
maintainer invokes the same skill in `maintainer-managed` mode, the skill runs
inside the verified isolated worktree and contributes only semantic curation;
the maintainer retains branch, commit, helper validation, and publication
ownership.

Keep entities independent during curation. Stay destinations own stay bases,
explicit `ski_area_access` edges link bases to ski areas, terrain domains model
ski-connected aggregates, and lift-pass products declare destination
availability, defaults, coverage, prices, and pass-accessible aggregates.

High-impact changes should include a typed catalog curation report with
before/after values, affected entities, trust statuses, clickable source links,
normalization notes, validation commands, and ranking-impact notes when the
changed fields affect ranking or fit behavior.

Run the catalog validator after catalog or trust-manifest edits:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog \
  --catalog-path app/data/catalog.json \
  --trust-manifest-path app/data/resort_trust_manifest.json
```

When a curation report exists, validate it and render the Markdown review packet:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
  typed docs/catalog-curation/REPORT.json \
  --markdown-output docs/catalog-curation/2026-06-23-zell-am-see-kaprun.md
```

When ranking or fit inputs change, include a concise ranking-impact assessment
in the typed report and verify the affected search behavior directly.

Bergfex is not catalog truth. It may later be used only as a warning-only
freshness sentinel that points reviewers back to official or open sources.

### Local catalog maintainer

Snowcast has a local, review-gated maintainer helper for two future Codex App
workers:

- curation reviews and remediates at most one safe same-repository `codex/*`
  catalog PR; and
- discovery researches backlog or external candidates read-only, then creates
  at most one complete owner-gated proposal after revalidation.

Codex owns semantic selection, research, review, fixes, and lifecycle requests.
The checked-in helper owns only objective inspection, guarded preparation,
validation, exact-head publication, recovery, and readiness gates. GitHub keeps
the branch, checks, one lane/state label pair, an allowlisted managed body block,
and one canonical maintainer comment. The helper never approves or merges.

Curation starts with parallel source/trust and graph/scope reviews of the exact
prepared head. Later fresh reviewers independently recheck the full scope and
then reconcile a private finding ledger, while current-main conflict probes and
150/180-minute soft/hard deadlines keep long remediation loops bounded.

Discovery is backlog-first: it retries a previously sourceable candidate that
lost only to `lock-busy`, then advances the next bounded `candidate` slice under
Catalog Curation Refinements, and uses external research only when no backlog
slice is actionable. A boundary, stable-ID, or weather-owner change may be
published as an explicit owner-gated decision-bearing proposal when the current
catalog model can express it; database/schema execution remains separate and
the proposal cannot become ready while its migration handoff is unresolved. An
actual old-key removal is accepted only as an explicit same-kind re-key with a
full old-target review and unresolved handoff, not as an unrelated deletion.

Removing `maintainer:proposal` is the owner acceptance action. Automation must
never restore that label when its absence could represent owner acceptance.

The repository code does not itself install the personal orchestration skill or
create or enable either schedule. Initial local activation is complete; the
[post-merge activation checklist](docs/operating-model/local-maintainer-activation.md)
remains the reactivation and rollback procedure. The authoritative contract is
the
[simplified maintainer spec](docs/superpowers/specs/2026-07-08-local-maintainer-simplification-design.md);
the original automation spec and plan are superseded history.

#### Capability CLI

Use the project-scoped GitHub CLI profile as a global option. Read-only
inspection does not acquire a lease and does not create a missing state
directory:

```bash
STATE_DIR="$HOME/.local/state/snowcast-maintainer"
GH_DIR="$HOME/.config/gh-lampssy-snowcast"

uv run --no-config python -m ops.maintainer.cli \
  --state-dir "$STATE_DIR" --gh-config-dir "$GH_DIR" \
  inspect curation

uv run --no-config python -m ops.maintainer.cli \
  --state-dir "$STATE_DIR" --gh-config-dir "$GH_DIR" \
  inspect discovery
```

The final command families are:

```text
lock acquire|heartbeat|release
inspect curation|discovery
prepare curation
validate curation|proposal
publish push|manual-check|recover|proposal|outcome|state|ensure-labels
```

Every mutation supplies the exact worker and 32-character `run_id` returned by
`lock acquire`. Hold the curation lease from prepare through review, fix,
validation, push, and publication. Discovery backlog interpretation and source
research happen before acquisition; after Codex chooses a candidate it acquires
the discovery lease, reruns inspection, and keeps the lease through proposal
publication. Heartbeat before and after capabilities and at least every five
minutes during longer work. A lease becomes eligible for fenced stale takeover
after one hour without a heartbeat; takeover preserves the prior owner record
and prevents the interrupted run from using or releasing its successor's lease.

Discovery proposal duplicate checks deliberately use two different views. The
candidate delta is validated from its immutable base and proposal head, while
"already cataloged" is rechecked from a freshly fetched immutable `main`
catalog and "already proposed" comes from GitHub. The modified proposal
worktree is never treated as the accepted catalog, so a proposal cannot reject
itself merely because it contains the candidate it is adding.

Publication prose is passed only through owner-private, direct-child
`title-file`, `body-file`, and `summary-file` basenames inside
`STATE_DIR`. The helper rejects symlinks, unsafe ownership or permissions,
invalid UTF-8, and oversized content. Caller-selected paths are never passed to
`gh`. `waiting-ci` and `ready` publication require a concise current synopsis
through `--body-file`. On an automation-owned curation PR whose legacy body has
no managed markers, `--adopt-body` explicitly replaces that legacy description;
without that flag, unmarked text is preserved. Later publications update the
managed block idempotently. The complete curation report remains checked in and
is not copied into the PR body.

#### State, outcomes, and recovery

Local state is deliberately small:

- `run.lock/owner.json`: current worker, run ID, acquisition time, heartbeat;
- `work/*.json`: one selected -> prepared -> reviewed -> validated -> pushed
  -> published phase record per work item; and
- `push/*.json`: the separate irreversible-operation journal used for exact
  push and proposal recovery.

There is no private lease token, worker credential file, runtime coverage
registry, deterministic backlog parser, lineage counter, or cycle counter.

Every command prints one bounded JSON outcome for Triage: worker, optional
work/PR/candidate identity, last phase, whether this invocation actually
mutated anything, and a terminal or no-op reason. Lease run IDs remain private.
Errors contain allowlisted reason/stage/check metadata, not raw command output,
PR prose, sources, paths, environment values, or tokens.

For a safe PR-specific terminal stop, `publish outcome` updates the existing
canonical maintainer comment and the single lifecycle label against the exact
unchanged remote head. It never pushes or changes the PR body, and its observed
head/reason record is separate from reviewed and validated head evidence. A new
commit or deliberate label removal makes the paused PR eligible again.

Recovery is journal-first:

1. inspect both inventories before choosing fresh work;
2. if there is exactly one unresolved journal, only its named worker may acquire
   the lease and run `publish recover --work-id ... --run-id ...`;
3. multiple unresolved journals fail closed for owner attention;
4. discovery recovery accepts only an absent remote or the exact journaled new
   head, finds PRs across all lifecycle states, and never recreates an
   owner-closed proposal;
5. a canonical proposal comment without `maintainer:proposal` fails closed
   because owner acceptance cannot be distinguished from an interrupted final
   label write; and
6. never delete or edit the owner record, work state, push journals, stale-lock
   archives, or backup refs during diagnosis.

The helper uses atomic create-only publication for a new discovery branch and
guarded `--force-with-lease` plus backup refs for automation-owned curation
branches. Never use plain `--force`. Pause/disable both future schedules before
manual diagnosis or rollback, and preserve journals for evidence.

9. Run the backend:
```bash
uv run python -m app.main
```

To enable the LLM-backed parser:
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

To refresh an exact ski area or every area reachable from a stay destination:
```bash
uv run python -m app.data.refresh_conditions --ski-area tignes-ski-area
uv run python -m app.data.refresh_conditions --force --stay-destination chamonix-mont-blanc
```

Weather jobs always operate on independently stored ski areas. Destination
targeting resolves explicit catalog access edges and deduplicates areas.

11. Backfill raw historical weather data into Postgres:
```bash
uv run python -m app.data.backfill_historical_weather --start-date 2021-01-01 --end-date 2026-01-01
```

To backfill selected ski areas or stay destinations, repeat the relevant flag:
```bash
uv run python -m app.data.backfill_historical_weather --start-date 2021-01-01 --end-date 2026-01-01 --ski-area tignes-ski-area
uv run python -m app.data.backfill_historical_weather --start-date 2021-01-01 --end-date 2026-01-01 --stay-destination chamonix-mont-blanc
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

Search results and public stay-destination pages derive optional historical metrics from mid-mountain archive rows for each explicitly named ski area, including typical snow depth, average daily snowfall, average max temperature, wind gusts, historical season coverage, and latest observed archive date. Metrics stay empty when mid-band archive data is missing.

Recommendation semantics:
- `min_price` and `max_price` are nightly stay-base budget estimates in EUR.
- `stars` is a compatibility parameter for minimum internal quality tier: `1=budget`, `2=standard`, `3=premium`.
- rental price is shown separately and is not part of budget filtering.
- `availability_status` is currently a weather-derived disruption signal, not official lift-operation status, unless future provenance is explicitly `reported`.

Production archive completion is automated by:
- `.github/workflows/complete-historical-weather.yml`
- scheduled daily at `01:15 UTC`, after the midnight conditions and forecast
  refresh windows
- fixed archive window `1991-01-01` through `2025-12-31`
- default budget of 200 provider requests, including retries, per run
- automatic per-ski-area climatology rebuild after all three elevation bands
  have complete archive coverage

The workflow uses persisted archive coverage as its checkpoint. `work_remaining`
and `throttled` are normal successful outcomes: the next daily run skips complete
chunks and resumes the missing work. Run it immediately from Actions ->
`Complete Historical Weather` -> `Run workflow`; otherwise the first scheduled
run starts it automatically. The workflow writes progress to the GitHub job
summary and to low-cardinality completion metrics.

All archive-writing workflows share one concurrency group, so scheduled
completion, recent reconciliation, and targeted manual backfills cannot consume
Open-Meteo quota concurrently.

For a targeted repair against the deployed Neon database, use the manual workflow:
- `.github/workflows/backfill-historical-weather.yml`
- Actions -> `Backfill Historical Weather` -> `Run workflow`
- inputs:
  - `start_date`
  - `end_date`
- optional `chunk_days`
- optional comma-separated `ski_area_ids` and `stay_destination_ids`
- optional `rebuild` to delete selected archive rows before refetching banded data
- optional retry/throttle inputs for large provider backfills:
  `retry_attempts`, `backoff_seconds`, `request_delay_seconds`,
  `request_jitter_ratio`, `retry_jitter_ratio`,
  `provider_pressure_error_threshold`, and
  `provider_pressure_cooldown_seconds`

Large Open-Meteo archive backfills can hit provider rate limits because long
date ranges with many variables count as more than one effective API call. The
backfill command reuses HTTP connections, adds jitter to pacing/retry sleeps, and
applies a longer cooldown after repeated timeout-like provider-pressure errors.
If a partial `rebuild` run stops on a `429 Too Many Requests` response, wait for
the quota window to reset and rerun the same target/date range with
`rebuild=false` and `force_refetch=false`. Completed chunks will be skipped and
missing chunks will be filled.

The free Open-Meteo endpoint is intended for non-commercial use and has
published minute, hour, day, and month limits in its
[pricing](https://open-meteo.com/en/pricing) and
[terms](https://open-meteo.com/en/terms). Use an appropriate paid or self-hosted
endpoint before relying on this workload commercially.

After a targeted archive rebuild or weather-critical catalog change, rebuild
the derived snow climatology table through the manual workflow:
- `.github/workflows/rebuild-snow-climatology.yml`
- Actions -> `Rebuild Snow Climatology` -> `Run workflow`
- keep `baseline_end_year=2025` until the full 2026 archive is available
- optional comma-separated `ski_area_ids` and `stay_destination_ids`

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

Keep the backend from step 9 running while using the Vite frontend. Local
frontend `/api/*` calls are proxied to `http://127.0.0.1:8000`.

14. Open:
- `http://localhost:8000/docs` to inspect backend endpoints
- `http://localhost:5173` to use the frontend demo
- `http://localhost:8000/ski-destinations/tignes` to inspect a server-rendered public stay-destination page
- `http://localhost:8000/sitemap.xml` to inspect generated public stay-destination URLs

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
  - `GET /ski-destinations/{stay_destination_id}`
  - `GET /sitemap.xml`
  - `GET /robots.txt`
- `POST /api/search` with a typed Search V4 intent, for example:

```bash
curl --request POST http://127.0.0.1:8000/api/search \
  --header 'Content-Type: application/json' \
  --data '{
    "intent": {
      "constraints": {
        "location": {"country": "France"},
        "travel_window": {"month": 3},
        "lodging_budget": {
          "mode": "lodging_nightly",
          "maximum": 320,
          "currency": "EUR",
          "budget_flex": 0.1
        }
      },
      "party": {"skill_levels": ["intermediate"]},
      "travel_context": {"origin_text": "Berlin", "mode": "car"},
      "objectives": [
        {"factor_id": "pass_terrain_value", "importance": "normal"}
      ]
    }
  }'
```

- `POST /api/search/refinements` after a successful ranking. Send the returned
  canonical `applied_intent`, `baseline_fingerprint`, the optional trip brief,
  and answered question IDs. The endpoint returns one explicit status:
  `questions_available`, `not_needed`, or `temporarily_unavailable`. The
  ranking-to-refinement handoff is process-local and expires after 60 seconds;
  delivered questions do not expire, and applying an answer creates a fresh
  ranked baseline before Snowcast asks the next question.
- `POST /api/search/weather-evidence` with the returned `applied_intent` and one
  canonical `ski_area_id` to load typed dossier weather evidence on demand.
- `POST /api/parse-query` with JSON body `{ "query": "cheap france ski trip close to lift for intermediate in March" }`
- `POST /api/parse-query` can also extract exact date windows such as `{ "query": "France intermediate ski trip 9 Apr to 16 Apr" }`
- The fallback parser also handles compact numeric date ranges such as `21-27.01.2027` and common origin phrasing such as `from Munich`.
- `GET /api/healthz`
- `GET /api/readyz`
- `GET /api/search-readiness` for Search V4 policy, factor-registry, catalog,
  and per-ski-area/source forecast-head readiness
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

Parse debug can distinguish compact typed LLM/provider failures such as:
- `quota_error`
- `auth_error`
- `network_error`
- `provider_error`

For provider errors, parse debug may include sanitized provider diagnostics such
as HTTP status, provider status, and a short normalized message.

`/search` results now include:
- `search_model_version`, `ranking_policy_version`, and ranked/unscored status
- applied typed intent plus eligible and excluded candidate counts
- `ski_region_id`, display name, rank, and fit score per ski region
- `top_configuration` plus bounded `alternative_configurations`
- stable stay-destination, stay-base, focus-ski-area, access, and pass IDs/names
- selected pass coverage and comparable price slice
- source-aware group/factor contributions, evidence caps, warnings, and
  provenance scoped to the selected ski area
- a public `baseline_fingerprint` used with the canonical intent digest to look
  up the exact short-lived evaluated baseline for a later refinement request

`/search/refinements` returns optional validated questions whose answers are
typed intent patches. Visible question and option copy is grounded
deterministically from those validated patches; the LLM does not supply
recommendation facts or ranking claims.

Contract hardening in this phase keeps the API semantics close to the code:
- request and response semantics are described in the Pydantic models
- canonical catalog entities use stable independent IDs and explicit relations
- top-level ranking groups by reviewed trip-market ski region
- target-date forecast evidence is pre-acquired into versioned runs and bulk
  loaded by Search V4; the request path never calls the weather provider
- current conditions remain a separate current-trip companion signal
- outbound accommodation links are currently stay-destination-level Booking.com search deep links generated behind the redirect endpoint
- current trip persistence is now one backend-owned record per authenticated user
- the companion surface reads from a dedicated current-trip summary endpoint and only advances its comparison baseline when `mark-checked` is called
- exact saved-trip dates now live in the current-trip model and drive trip-window-aware companion eligibility
- current-trip companion events are backend-owned records deduplicated by deterministic event signatures
- travel-effort ranking is car-first in this phase; other travel modes can be
  expressed in the typed contract but remain neutral until an evaluator has
  comparable route evidence

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

GitHub Actions preserves the Linux Python lint/test job and runs the locked
frontend unit, production-build, and full Chromium E2E/visual suite in a
dedicated macOS job. The visual baselines are Darwin-specific and are not
treated as portable Ubuntu snapshots. A separate deploy workflow runs on push
to `main`.

## Deployment
Snowcast uses a single public app shape with FastAPI serving the built frontend and API together.

Included deployment assets:
- `Dockerfile` for a combined backend + built frontend image
- `fly.toml` for a Fly.io deployment with one web process plus a release bootstrap step
- `docker-compose.yml` for local Postgres
- `.github/workflows/deploy.yml` for deploy-on-push-to-main CI/CD
- `.github/workflows/refresh-conditions.yml` for scheduled/manual conditions refresh against Neon
- `.github/workflows/reconcile-recent-archive.yml` for scheduled/manual recent archive reconciliation against Neon
- `.github/workflows/complete-historical-weather.yml` for scheduled/manual resumable 1991-2025 archive and climatology completion
- `.github/workflows/rebuild-snow-climatology.yml` for manual derived climatology rebuilds after archive backfills or model/catalog changes
- `.github/workflows/product-canary.yml` for scheduled/manual production search canaries
- `.github/workflows/parse-canary.yml` for scheduled/manual production parse canaries
- `.github/workflows/validate-grafana-dashboards.yml` for validating repo-managed Grafana dashboard resources
- `.github/workflows/deploy-grafana-dashboards.yml` for manual Grafana dashboard deployment

Expected hosted environment variables:
- `DATABASE_URL` (Neon Postgres connection string)
- `GEMINI_API_KEY`
- optional `GEMINI_MODEL`
- optional observability settings:
  - `OTEL_ENABLED`
  - `OTEL_SERVICE_NAME`
  - `OTEL_EXPORTER_OTLP_ENDPOINT`
  - `OTEL_EXPORTER_OTLP_HEADERS`
  - `OTEL_TRACES_SAMPLER_ARG`
  - `LOG_FORMAT`
  - `LOG_LEVEL`

For the current low-traffic production app, keep `OTEL_TRACES_SAMPLER_ARG=1.0`
so slow searches have complete Tempo traces. Lower this later only when real
traffic makes trace volume meaningful. FastAPI health and readiness endpoints
are excluded from traces to keep Tempo focused on user-facing requests.

Production runbook:
- [`docs/production-runbook.md`](docs/production-runbook.md)
- [`docs/observability-runbook.md`](docs/observability-runbook.md)

## Project Structure
```text
ai-sports-travel-planner/
├── AGENTS.md         # Codex instructions
├── docs/             # Product, architecture, operating-model, and runbook docs
├── frontend/         # React/Vite/Tailwind demo frontend
├── PROJECT.md        # Product charter and current roadmap snapshot
├── app/              # Backend logic
│   ├── ai/           # Query parsing helpers
│   │                  # plus the direct Gemini query parser helper
│   ├── data/         # Resort seed, Postgres bootstrap command, repositories, refresh command
│   ├── integrations/ # Weather/provider normalization boundaries
│   └── domain/       # Models, ranking, and search logic
├── ops/              # Operational tooling such as Grafana dashboard resources
├── tests/            # Unit & integration tests
├── pyproject.toml
└── README.md         # This file
```

Additional reference:
- [docs/engineering-notes.md](docs/engineering-notes.md) for curated technical notes, tradeoffs, and learning-oriented explanations tied to this project
- [docs/product-backlog.md](docs/product-backlog.md) for candidate ideas and future work that are not active implementation commitments yet
- [docs/domain-language.md](docs/domain-language.md) for shared Snowcast domain terms, bounded contexts, and invariants
- [docs/architecture/adr](docs/architecture/adr) for lightweight Architecture Decision Records
- [docs/operating-model/review-playbook.md](docs/operating-model/review-playbook.md) for advisory review routing, Developer Decision Checkpoints, Superpowers integration, and framework maintenance
- [docs/operating-model/feature-spec-template.md](docs/operating-model/feature-spec-template.md) for feature specs before high-risk or durable implementation work
- [docs/operating-model/advisory-reviewers.md](docs/operating-model/advisory-reviewers.md) for Snowcast advisory reviewer contracts and review output formats
- [docs/planning-model.md](docs/planning-model.md) for the canonical planning model spec, evidence profiles, and tuning-policy overview
- [docs/search-ranking-model.md](docs/search-ranking-model.md) for the exact active Search V4 equation, architecture, factor inventory, weights, and dynamic refinement model
- [docs/observability-plan.md](docs/observability-plan.md) for the OpenTelemetry-first observability architecture, metrics, traces, logs, alerts, and sprint fit
- [docs/observability-runbook.md](docs/observability-runbook.md) for production telemetry env vars, dashboard panels, alert candidates, and first-response checks
- [ops/grafana/README.md](ops/grafana/README.md) for repo-managed Grafana dashboard validation and deployment
- [docs/ui-concepts/2026-06-10-accommodation-guidelines](docs/ui-concepts/2026-06-10-accommodation-guidelines) for the latest Snowcast grouped-recommendation and suggested-stay visual concepts
- [docs/ui-concepts/2026-06-11-main-page-closeout](docs/ui-concepts/2026-06-11-main-page-closeout) for the Sprint 34 main-page accepted concept and rendered desktop/mobile close-out screenshots
