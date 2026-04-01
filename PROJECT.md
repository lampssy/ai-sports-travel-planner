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
- Activity recommendation module (MVP)
- Hardcoded dataset of activities (resorts/spots)
- Simple API interface for structured requests (sport, region, difficulty)
- Unit tests for core filtering logic

### Sprint 2
- Resort, accommodation (area) and rental recommendation (structured input only)
- Hardcoded dataset of resorts, areas, and rentals (5–10 resorts)
- Filtering and ranking logic for recommendations:
  - filter by location, price range, area quality
- rank results by score (e.g., rating + price)
- API endpoint /search returning structured JSON results
- Deterministic ranking without LLM
- Unit tests for filtering + ranking logic

### Sprint 3
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
- Add one high-value external signal to the recommendation engine:
  - weather / snow conditions for trip timing confidence
- Enrich recommendation output with clearer decision support:
  - explanation of why each resort ranked highly
  - estimated total trip cost or cost breakdown
  - recommendation confidence / tradeoff summary
- Add targeted AI usage only where it improves user understanding:
  - ranking explanation
  - concise recommendation summary
- Prepare MVP for demo or release:
  - deployment setup
  - stable API contract
  - seed data quality improvements
- Optional commercial extensions closely tied to the core flow:
  - placeholder booking / affiliate links
  - basic accommodation expansion if it directly supports resort selection

---

## 6. Working Guidelines
- Keep AI logic separate from business logic
- Write tests for critical logic
- Modular architecture: each module has a clear purpose
- Thoughtful use of LLM: cache, testable prompts
- Prioritize readable and typed Python code
- Do not generate tests for deterministic/simple code (e.g., CRUD), only for logic requiring verification
