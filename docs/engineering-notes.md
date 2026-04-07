# Engineering Notes

Curated technical notes for this project. This file captures:
- how selected tools and frameworks work in the context of this repo
- why key technical decisions were made
- important tradeoffs and consequences
- concise notes prompted by clarification questions during development

This is not a changelog and not a transcript of chat discussions. Keep entries short, practical, and tied to this codebase.

## Architecture

### Current shape
- Backend-first architecture using FastAPI.
- Deterministic domain logic is kept separate from AI helpers and integrations.
- The search flow is centered on one structured endpoint: `/search`.
- The parser endpoint `/parse-query` exists as a helper layer, not as the primary product flow.

### Separation of concerns
- `app/domain/` holds models, ranking behavior, and recommendation logic.
- `app/data/` holds checked-in seed data plus persistence/bootstrap code and repositories.
- `app/integrations/` holds external-signal boundaries such as ski conditions.
- `app/ai/` holds optional AI-specific helpers and should not absorb deterministic business logic.

## Backend Flow

### Search request flow
1. FastAPI validates query parameters in the API layer.
2. `SearchFilters` is constructed from structured input.
3. The search service loads resorts, fetches normalized condition records, filters candidate areas/rentals, and ranks results.
4. The API returns UI-oriented JSON, not raw internal ranking details.

### Why the backend stays primary
- The product value is in the decision engine: ranking, fit, conditions, and explanation quality.
- The frontend is intended to exercise and present backend behavior, not define the domain model prematurely.
- The API contract remains stable while runtime reads are handled through SQLite-backed repositories.

## API Contract

### `/search`
- Structured input only: location, budget, stars, skill level, lift distance, optional budget flexibility.
- The response is shaped for product use, not just debugging.
- Important output groups:
  - selected resort/area/rental fields
  - condition signals
  - `recommendation_confidence`
  - grouped `explanation`

### Explanation contract
- The flat explanation fields were replaced with a grouped `explanation` object.
- Current shape:
  - `highlights`
  - `risks`
  - `confidence_contributors`
- This is intended to be easier for a frontend to render than free-form strings.

### Why grouped explanation was chosen
- Better for product presentation than a flat list of reasons.
- More compact and stable than exposing internal ranking diagnostics.
- Keeps one overall confidence score while still explaining it.

## Integrations

### Conditions model
- Ski conditions are represented as lightweight normalized signals rather than raw provider-style data.
- Current public condition-related fields include:
  - `conditions_score`
  - `snow_confidence_score`
  - `snow_confidence_label`
  - `availability_status`
- Runtime condition reads now come from the SQLite persistence layer.
- New databases bootstrap curated resorts only; condition rows appear after the internal Open-Meteo refresh command runs.

### Why one snow-confidence signal
- A single combined snow-confidence signal was chosen instead of splitting snow quality and depth confidence.
- Reason: simpler model, easier ranking semantics, and enough fidelity for the current stage.

### Availability behavior
- Availability is categorical, not numeric:
  - `open`
  - `limited`
  - `temporarily_closed`
  - `out_of_season`
- `out_of_season` is excluded from results.
- `temporarily_closed` is still returned but penalized, because temporary closures should not automatically hide potentially strong resorts.

### Real-data refresh flow
- `/search` reads cached condition rows from SQLite and never fetches provider data inline.
- A separate internal refresh command fetches Open-Meteo data, normalizes it, and upserts condition rows.
- Freshness is currently 24 hours.
- If refresh fails, stale cached rows remain usable; generic fallback is only used when no conditions row exists at all.
- The refresh command supports a forced recomputation mode and exact resort targeting for operator workflows such as re-normalizing cached rows after logic changes.

### Conditions output consistency
- The user-facing weather summary should derive from the same normalized snow-confidence signal as `snow_confidence_label`.
- Explanation framing should follow the same rule: strong snow can appear as a positive fit signal, fair snow should be treated conservatively, and poor snow should be expressed as a risk or negative confidence contributor.
- This keeps summary text, explanation groups, and confidence reasoning aligned without changing the ranking model.

## Frontend Stack

### Current web frontend shape
- Thin demo frontend as a separate app, not served by FastAPI initially.
- Current stack:
  - React
  - TypeScript
  - Vite
  - Tailwind
- Current demo scope:
  - one page only
  - structured search form
  - ranked result cards
  - one selected-result details panel

### Why React + TypeScript + Vite + Tailwind
- React: component-based UI and stateful interactions.
- TypeScript: safer contracts and easier refactoring against backend response shapes.
- Vite: fast local frontend development.
- Tailwind: closer to modern product-app conventions and faster demo iteration than hand-written CSS for this project.

### Why local fetch instead of TanStack Query for now
- The first demo is intentionally small: one page, one main search flow, one selected-result panel.
- Plain React state plus `fetch` keeps the first version simpler.
- TanStack Query becomes more attractive once frontend server-state patterns grow beyond this small surface.

### Vite proxy in local development
- The frontend calls proxied paths like `/api/search`.
- Vite forwards those requests to the FastAPI backend during development.
- This avoids adding CORS changes to the backend for the first demo iteration.

### Curated presentation over raw JSON
- The frontend should not present the API as raw fields only.
- The selected-result panel is curated into sections:
  - Why it fits
  - Watchouts
  - Conditions
  - Confidence
- This is still direct API consumption; the curation happens in frontend presentation logic, not through a BFF layer.

## Decisions and Tradeoffs

### Structured input over free-text in the main flow
- The main product flow remains structured search.
- Free-text parsing exists, but it is not the primary interface because the product is still validating deterministic recommendation quality.

### No backward compatibility for evolving internal product API
- This is a private, still-evolving project.
- When the contract improved, old explanation fields were removed instead of preserved.
- This keeps the API cleaner while the product is still being shaped.

### Why sqlite3 instead of an ORM
- The backend is still sync and the schema is small.
- The main learning goal is repository separation, not ORM depth.
- Swappability later comes from the repository boundary, not from introducing more abstraction early.

### What sqlite3 is
- `sqlite3` is Python's built-in interface to SQLite, a small file-based relational database.
- In this project it means the app can store structured data in one local `.db` file without running a separate database server.
- We use it directly instead of an ORM, so SQL stays explicit and the repository boundary stays easy to understand.
- This is suitable for the current stage because the backend is sync, local development is simple, and the data model is still small.

### Why conditions are refreshed by command instead of API
- Conditions refresh is an operational concern, not a user-facing product action.
- Keeping it out of FastAPI avoids exposing admin/update behavior through the public API too early.
- It also keeps `/search` latency predictable because provider calls are not made during request handling.

## Concepts Clarified

### BFF
- BFF means Backend for Frontend.
- It is a backend layer tailored specifically to one frontend experience.
- This project is not using a formal BFF yet because the app is still small and the frontend can call the existing API directly.

### React vs TypeScript vs Vite vs Tailwind
- React: UI/component layer.
- TypeScript: static typing for frontend code.
- Vite: dev/build tool for the frontend app.
- Tailwind: utility-first styling framework.
- These solve different problems and are complementary rather than interchangeable.

### Local fetch vs TanStack Query
- Local `fetch` means managing request/loading/error/data state directly in React components.
- TanStack Query is a server-state management library that handles fetching, caching, retries, and refetching patterns.
- For this project, local `fetch` is enough for the first thin frontend demo.
