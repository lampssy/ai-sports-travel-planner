# AI Sports Travel Planner

## Project Overview
AI Sports Travel Planner helps athletes plan ski trips with structured resort recommendations, accommodation-area options, and rental suggestions. The backend exposes deterministic APIs for search and activity recommendations, leaving AI-specific features for later sprints.

## Features
- Search ski resorts by country, budget, quality level, skill level, and lift-distance preference
- Add an optional travel month so resort ranking can reflect planning confidence for a selected window
- Return ranked resort matches with one selected area and one rental option
- Include lightweight weather/snow conditions, structured explanation output, provenance metadata, planning summaries, and confidence metadata in search results
- Add a grounded recommendation narrative for the top-ranked search result
- Surface a tracked outbound accommodation CTA that routes through the backend before redirecting to the external booking target
- Save one provider-agnostic current trip from the selected result with a booking status for later companion features
- Switch into a dedicated `Current trip` view with trip-specific current conditions and change tracking since the last explicit check
- Expose snow-confidence and resort availability signals in search results
- Load curated Alpine resort data through SQLite-backed repositories
- Refresh real resort conditions from Open-Meteo into SQLite through an internal command
- Parse free-text ski trip queries with LLM-first extraction and heuristic fallback
- Recommend sports activities in a selected region
- Structured JSON responses for backend/API consumers
- React/Vite demo frontend with AI-assisted trip-brief interpretation and accommodation booking CTA
- Resort-level booking handoff plus anchored current-trip save flow in the selected-result panel

## Tech Stack
- Python 3.11+
- FastAPI
- Gemini Developer API
- SQLite
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

4. Run tests:
```bash
uv run pytest
```

5. Install local pre-commit hooks:
```bash
uv run pre-commit install
```

6. Run the backend:
```bash
uv run python -m app.main
```

To enable the LLM-backed parser and top-result narrative:
```bash
export GEMINI_API_KEY=...
```

Optional model override:
```bash
export GEMINI_MODEL=gemini-2.5-flash
```

You can also place these in a local `.env` file in the repo root:
```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

The app loads `.env` automatically for local development. Keep this file local only; it is ignored by git.

7. Refresh real conditions data into SQLite:
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

8. Install frontend dependencies:
```bash
cd frontend
npm install
```

9. Run the frontend demo:
```bash
npm run dev
```

10. Open:
- `http://localhost:8000/docs` to inspect backend endpoints
- `http://localhost:5173` to use the frontend demo

For a single-URL production-style local run, build the frontend first:
```bash
cd frontend
npm run build
cd ..
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
export APP_DB_PATH=/absolute/path/to/planner.db
export FRONTEND_DIST_DIR=/absolute/path/to/frontend/dist
```

## API Endpoints
- `GET /api/recommend-activities?sport=ski&region=Alps&difficulty=beginner`
- `GET /api/search?location=France&min_price=150&max_price=320&stars=2&skill_level=intermediate&lift_distance=medium&budget_flex=0.1&travel_month=2`
- `POST /api/parse-query` with JSON body `{ "query": "cheap france ski trip close to lift for intermediate" }`
- `GET /api/healthz`
- `GET /api/readyz`
- `GET /api/current-trip`
- `GET /api/current-trip/summary`
- `PUT /api/current-trip`
- `POST /api/current-trip/mark-checked`
- `DELETE /api/current-trip`

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
- conditions summary
- conditions provenance
- optional planning summary
- optional planning provenance
- optional planning evidence count
- best travel months
- conditions score
- snow confidence score
- snow confidence label
- availability status
- explanation:
  - highlights
  - risks
  - confidence contributors
- recommendation narrative
- recommendation confidence

Contract hardening in this phase keeps the API semantics close to the code:
- request and response semantics are described in the Pydantic models
- seed data uses stable `resort_id` values and geographic `region`
- current live Open-Meteo conditions are surfaced as `forecast` signals
- month-aware planning is surfaced as `estimated` from snapshot history plus seasonality
- outbound accommodation links are currently resort-level Booking.com search deep links generated behind the redirect endpoint
- current trip persistence is a single-record, provider-agnostic local model keyed off the selected result panel
- the companion surface reads from a dedicated current-trip summary endpoint and only advances its comparison baseline when `mark-checked` is called

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

GitHub Actions runs lint, formatting checks, and tests on every push.

## Deployment
Sprint 11 targets a single public URL with FastAPI serving the built frontend and API together.

Included deployment assets:
- `Dockerfile` for a combined backend + built frontend image
- `fly.toml` for a Fly.io-style deployment with a persistent SQLite volume at `/data`

Expected hosted environment variables:
- `GEMINI_API_KEY`
- optional `GEMINI_MODEL`
- optional `APP_DB_PATH` if the default `/data/planner.db` is not used

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
│   ├── data/         # Resort seed, SQLite bootstrap, repositories, refresh command
│   ├── integrations/ # Weather/provider normalization boundaries
│   └── domain/       # Models, ranking, and search logic
├── tests/            # Unit & integration tests
├── pyproject.toml
└── README.md         # This file
```

Additional reference:
- [docs/engineering-notes.md](docs/engineering-notes.md) for curated technical notes, tradeoffs, and learning-oriented explanations tied to this project
