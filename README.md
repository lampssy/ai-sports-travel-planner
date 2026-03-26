# AI Sports Travel Planner

## Project Overview
AI Sports Travel Planner helps athletes (skiers, windsurfers) plan trips and routes based on weather, trail availability, and equipment. AI provides optimized plans and recommends gear suited to the sport type and user skill level.

## Features
- Plan sports routes in a selected region
- Weather integration via API
- Equipment recommendations based on sport type
- Generate a text summary of the trip/route

## Tech Stack
- Python 3.11+
- FastAPI
- LangChain / LangGraph / OpenAI API
- SQLite / PostgreSQL
- Pytest
- Docker (optional)
- **uv (Astral)** for project and environment management

## Getting Started
1. Install **uv** (following Astral instructions):
```bash
curl -sSf https://install.astral.sh | sh
```

2. Clone the repository:
```bash
git clone <repo-url>
cd ai-sports-travel-planner
```

3. Create and enter the project environment:
```bash
uv init
uv shell
```

4. Install dependencies:
```bash
uv install -r requirements.txt
```

5. Run the backend:
```bash
uv run python -m app.main
```

6. Open `http://localhost:8000/docs` to explore API endpoints.

## Project Structure
```text
ai-sports-travel-planner/
├── AGENTS.md         # Codex instructions
├── PROJECT.md        # Project plan / roadmap
├── app/              # Backend logic
├── ai/               # AI modules / LangChain
├── tests/            # Unit & integration tests
├── requirements.txt
└── README.md         # This file
```
