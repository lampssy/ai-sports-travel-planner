# AI Sports Travel Planner

## 1. Project Goal
An application that helps athletes (skiers, windsurfers) plan trips and routes, taking into account weather conditions, trail availability, and sports equipment. AI provides optimized plans and recommends gear suited to the sport type and user skill level.

---

## 2. MVP Scope
Core features:
- Planning sports routes in a selected region
- Weather integration (weather API)
- Equipment recommendations based on sport type
- Generating a simple summary/route in text form

Optional / future features:
- Map integration and route visualization
- Hotel and restaurant recommendations
- Ranking of best routes for the season
- Personalized suggestions based on user history

---

## 3. High-level Architecture
- **Frontend (optional for MVP):** simple webpage or API for sending requests
- **Backend:** FastAPI
- **Database:** SQLite or PostgreSQL (storing routes, users, equipment)
- **AI Module:** LangChain / LangGraph / OpenAI API for route and equipment recommendations
- **External integrations:** weather, maps
- **Testing:** unit + integration (backend logic), mock LLM calls

---

## 4. Technology Stack
- Python 3.11+
- FastAPI
- LangChain / LangGraph / OpenAI API
- PostgreSQL / SQLite
- Pytest
- Docker (optional)
- Requests / httpx for weather and map API integrations

---

## 5. Roadmap / Sprints

### Sprint 1
- Route planning module (MVP)
- Basic weather integration
- Simple API interface for requests

### Sprint 2
- AI equipment recommendations
- Unit and integration tests for backend logic
- Mock LLM calls in tests

### Sprint 3
- Extended route functionality (filters, difficulty levels)
- Architecture refactor for larger scope
- Simple caching for AI recommendations

### Sprint 4
- Additional features: maps, hotel suggestions
- AI optimization, prompt engineering
- Preparation for potential MVP deployment / release

---

## 6. Working Guidelines
- Keep AI logic separate from business logic
- Write tests for critical logic
- Modular architecture: each module has a clear purpose
- Thoughtful use of LLM: cache, testable prompts
- Prioritize readable and typed Python code
- Do not generate tests for deterministic/simple code (e.g., CRUD), only for logic requiring verification