# AI Sports Travel Planner

## Project Overview
AI Sports Travel Planner helps athletes plan ski trips with structured resort recommendations, accommodation-area options, and rental suggestions. The backend exposes deterministic APIs for search and activity recommendations, leaving AI-specific features for later sprints.

## Features
- Search ski resorts by country, budget, quality level, skill level, and lift-distance preference
- Return ranked resort matches with one selected area and one rental option
- Load normalized resort data from checked-in JSON
- Parse free-text ski trip queries into structured filters with confidence metadata
- Recommend sports activities in a selected region
- Structured JSON responses for backend/API consumers

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

5. Run the backend:
```bash
uv run python -m app.main
```

6. Open `http://localhost:8000/docs` to explore API endpoints.

## API Endpoints
- `GET /recommend-activities?sport=ski&region=Alps&difficulty=beginner`
- `GET /search?location=France&min_price=150&max_price=320&stars=2&skill_level=intermediate&lift_distance=medium&budget_flex=0.1`
- `POST /parse-query` with JSON body `{ "query": "cheap france ski trip close to lift for intermediate" }`

## Project Structure
```text
ai-sports-travel-planner/
├── AGENTS.md         # Codex instructions
├── PROJECT.md        # Project plan / roadmap
├── app/              # Backend logic
│   ├── ai/           # Query parsing helpers
│   ├── data/         # Seed JSON and loading/normalization
│   └── domain/       # Models, ranking, and search logic
├── tests/            # Unit & integration tests
├── pyproject.toml
└── README.md         # This file
```
