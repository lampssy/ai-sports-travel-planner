# AI Sports Travel Planner

## 1. Project Goal
An application that helps athletes (skiers, windsurfers) plan trips by recommending resorts, areas for accommodation, and rental options for equipment. AI provides optimized suggestions and explanations tailored to the user’s skill level, budget, and preferences.

---

## 2. MVP Scope
Core features:
- Recommend resorts or sports spots in a selected region based on user preferences (sport, skill level, budget)
- Suggest accommodation areas and rental options for equipment
- Generate a structured recommendation summary in JSON with resort, area, rental, and basic metadata (price ranges, quality, ratings, links)

Optional / future features:
- Weather integration (weather API) for trip planning
- Map integration and route visualization
- Detailed hotel and restaurant recommendations
- Ranking of best resorts/spots for the season
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
Status: completed
- Activity recommendation module (MVP)
- Hardcoded dataset of activities (resorts/spots)
- Simple API interface for structured requests (sport, region, difficulty)
- Unit tests for core filtering logic

### Sprint 2
Status: completed
- Resort, accommodation (area) and rental recommendation (structured input only)
- Hardcoded dataset of resorts, areas, and rentals (5–10 resorts)
- Filtering and ranking logic for recommendations:
  - filter by location, price range, area quality
- rank results by score (e.g., rating + price)
- API endpoint /search returning structured JSON results
- Deterministic ranking without LLM
- Unit tests for filtering + ranking logic

### Sprint 3
Status: completed
- Extended deterministic search filters:
  - skill level / difficulty suitability
  - distance to lift
  - budget flexibility or soft price scoring
- Refactor backend structure to separate:
  - search/filter input models
  - ranking logic
  - data loading / normalization
- Move resort dataset from hardcoded Python objects to validated JSON loading
- Add manual data ingestion/update path for resort data
- Optional LLM-assisted query parser as a thin input layer:
  - parse free-text into structured filters
  - structured input keeps priority over parsed values
  - parser output includes confidence and fallback behavior
- Unit tests for:
  - new filtering and ranking behavior
  - data loading and validation
  - mocked LLM parser behavior

### Sprint 4
Status: completed
- Add one lightweight external signal to the recommendation engine:
  - weather / snow conditions for trip timing confidence
- Improve recommendation trust and clarity:
  - structured explanation of why each resort ranked highly
  - recommendation confidence / tradeoff summary
- Add targeted AI usage only where it improves user understanding:
  - concise explanation text grounded in structured ranking factors
- Stabilize the backend for the next phase:
  - stable API contract
  - seed data quality improvements

### Sprint 5
Status: planned
- Deepen lightweight conditions integration:
  - refine the weather / snow integration module with a minimal normalized conditions model
  - enrich ranking inputs with a small number of condition signals
  - expose condition-related fields in the search result payload consistently
  - add tests for normalization, fallback behavior, and ranking impact

### Sprint 6
Status: planned
- Recommendation explanation and confidence:
  - extend the result payload with structured reasons, tradeoff fields, and simple confidence output
  - keep explanation generation mostly deterministic and grounded in ranking factors
  - if AI is used here, limit it to optional concise explanation text built from structured facts

### Sprint 7
Status: planned
- Thin demo frontend:
  - build a small frontend that consumes `/search` and related endpoints directly
  - support the main decision flow: enter filters, inspect ranked options, compare why-ranked output
  - use the demo to identify where the API contract is awkward before introducing any BFF-like layer

---

## 6. Working Guidelines
- Keep AI logic separate from business logic
- Write tests for critical logic
- Modular architecture: each module has a clear purpose
- Thoughtful use of LLM: cache, testable prompts
- Prioritize readable and typed Python code
- Do not generate tests for deterministic/simple code (e.g., CRUD), only for logic requiring verification
