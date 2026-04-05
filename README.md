# AI Sports Travel Planner

## Project Overview
AI Sports Travel Planner helps athletes plan ski trips with structured resort recommendations, accommodation-area options, and rental suggestions. The backend exposes deterministic APIs for search and activity recommendations, leaving AI-specific features for later sprints.

## Features
- Search ski resorts by country, budget, quality level, skill level, and lift-distance preference
- Return ranked resort matches with one selected area and one rental option
- Include lightweight weather/snow conditions, structured explanation output, and confidence metadata in search results
- Expose snow-confidence and resort availability signals in search results
- Load normalized resort data from checked-in JSON
- Parse free-text ski trip queries into structured filters with confidence metadata
- Recommend sports activities in a selected region
- Structured JSON responses for backend/API consumers
- Separate React/Vite demo frontend for the main ski-trip search flow

## Tech Stack
- Python 3.11+
- FastAPI
- LangChain / LangGraph / OpenAI API
- SQLite / PostgreSQL
- Pytest
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

7. Install frontend dependencies:
```bash
cd frontend
npm install
```

8. Run the frontend demo:
```bash
npm run dev
```

9. Open:
- `http://localhost:8000/docs` to inspect backend endpoints
- `http://localhost:5173` to use the frontend demo

## API Endpoints
- `GET /recommend-activities?sport=ski&region=Alps&difficulty=beginner`
- `GET /search?location=France&min_price=150&max_price=320&stars=2&skill_level=intermediate&lift_distance=medium&budget_flex=0.1`
- `POST /parse-query` with JSON body `{ "query": "cheap france ski trip close to lift for intermediate" }`

`/search` results now include:
- resort id
- region
- conditions summary
- conditions score
- snow confidence score
- snow confidence label
- availability status
- explanation:
  - highlights
  - risks
  - confidence contributors
- recommendation confidence

Contract hardening in this phase keeps the API semantics close to the code:
- request and response semantics are described in the Pydantic models
- seed data uses stable `resort_id` values and geographic `region`

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
npm run build
```

GitHub Actions runs lint, formatting checks, and tests on every push.

## Project Structure
```text
ai-sports-travel-planner/
├── AGENTS.md         # Codex instructions
├── docs/             # Engineering notes and future project documentation
├── frontend/         # React/Vite/Tailwind demo frontend
├── PROJECT.md        # Project plan / roadmap
├── app/              # Backend logic
│   ├── ai/           # Query parsing helpers
│   ├── data/         # Seed JSON and loading/normalization
│   └── domain/       # Models, ranking, and search logic
├── tests/            # Unit & integration tests
├── pyproject.toml
└── README.md         # This file
```

Additional reference:
- [docs/engineering-notes.md](docs/engineering-notes.md) for curated technical notes, tradeoffs, and learning-oriented explanations tied to this project
