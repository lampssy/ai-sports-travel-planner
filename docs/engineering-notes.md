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
- The parser endpoint `/parse-query` is an AI-assisted interpretation layer that can support the main search UX, but structured filters remain the source of truth.

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
  - outbound accommodation target
  - condition signals
  - `recommendation_confidence`
  - grouped `explanation`
  - `recommendation_narrative` on the top-ranked result

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

### Outbound booking click tracking
- The first booking/referral step is a backend-mediated redirect rather than a direct frontend link.
- The redirect endpoint records one SQLite event row before sending the user to the external accommodation target.
- This keeps click tracking deterministic and testable without introducing third-party analytics.
- The current outbound target is a resort-level Booking.com search deep link; later affiliate-backed variants should be swapped in behind the same redirect boundary.

### Booking-provider boundary
- Booking-provider specifics should stay isolated to the outbound link / redirect layer.
- The medium-term product model should be a provider-agnostic trip record rather than a Booking.com-specific booking record.
- Companion features should work for users who:
  - booked through an affiliate link
  - booked elsewhere
  - manually entered where they are staying
- This keeps monetization channels replaceable without making the product depend on one provider's attribution model or data shape.

### Deep-link strategy
- The deep-link path should become more specific over time, but only when the product can justify the specificity.
- Current stage: resort-level outbound accommodation search links.
- Next stage: area-level deep links that land closer to the recommended option when the product can support them reliably.
- Later: affiliate-backed variants of those same links once partner setup is ready.
- Property-level links should come only once the product can credibly recommend a specific accommodation rather than just a resort or area.

### Current trip model
- The first persisted trip context is a single current-trip record, not a multi-trip system.
- Trip creation is explicit and anchored to the selected result panel rather than auto-created on booking click.
- The saved record is intentionally provider-agnostic and currently stores:
  - `resort_id`
  - `resort_name`
  - `selected_area_name`
  - optional `travel_month`
  - `booking_status`
  - timestamps
- `booking_status` is modeled independently of provider attribution:
  - `not_booked_yet`
  - `booked_through_app`
  - `booked_elsewhere`
- This is the minimum durable trip context needed for later companion features without prematurely introducing account or multi-trip complexity.

### Current trip companion baseline
- The first companion surface is a separate in-app `Current trip` view rather than more detail crammed into the search panel.
- The saved trip now tracks `last_checked_at` in addition to save/update timestamps.
- Companion deltas are intentionally narrow:
  - current conditions only
  - compared against `last_checked_at` when present, otherwise `created_at`
  - baseline advances only through an explicit `Mark checked` action
- Opening the companion view must not silently reset that baseline.
- If there is no earlier snapshot before the baseline timestamp, the API returns a graceful `not enough earlier history to compare yet` state instead of inventing a delta.

### LLM narrative behavior
- The recommendation narrative is generated only for the top-ranked `/search` result.
- Lower-ranked results keep `recommendation_narrative = null` so the response shape stays uniform without multiplying cost and latency.
- The narrative must be grounded in existing structured result fields and must not invent resort facts or alter ranking.
- Optional `debug=true` metadata can expose whether parser and narrative outputs came from fresh LLM calls, cache hits, or fallback paths without polluting the default API contract.
- Debug metadata uses compact typed provider reasons such as `quota_error`, `auth_error`, `network_error`, and `provider_error` instead of exposing raw upstream error text.

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

### Trust and provenance
- `/search` now exposes provenance metadata alongside current conditions and month-aware planning signals.
- Current live Open-Meteo-backed resort conditions are classified as `forecast`.
- Month-aware planning is classified as `estimated` because it blends stored snapshots with seasonality heuristics rather than using a single live forecast.
- `reported` is reserved for future true report feeds and is not emitted yet.
- Provenance metadata is intentionally compact:
  - source name
  - source type
  - last updated timestamp when available
  - freshness classification
  - one short basis summary
- The trust UI should make evidence legible without turning the product into a diagnostics console.

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
- Free-text parsing should support the main flow as a transparent interpretation step rather than replace it.
- The intended UX is one integrated search experience:
  - trip brief input
  - interpret action
  - parsed preview with confidence and unknown parts
  - explicit review/apply into the structured form
- This avoids an opaque AI-only mode while still making the LLM value visible in demos and normal product use.

### Direct Gemini API vs LangChain / LangGraph
- Direct Gemini API behind a small local `LLMClient` seam is the current choice because the LLM workflows are still narrow: query parsing and one short grounded narrative.
- This keeps the control flow explicit and avoids introducing a framework before retrieval, tool-calling, or multi-step orchestration is needed.
- LangChain is still unnecessary for the current planner/ranker core.
- LangGraph becomes more plausible later if the product grows into stateful companion workflows such as:
  - trip-companion chat grounded in trip context, live conditions, and lift status
  - plan-B / contingency assistance when conditions deteriorate
  - multi-step operational guidance around a booked trip
- If introduced later, it should sit in companion-style orchestration flows rather than in deterministic ranking, conditions scoring, or simple parser/narrative calls.

### Local provider seam
- Parser and narrative helpers depend on a local `LLMClient` interface rather than on provider-specific request shapes.
- This keeps the application code decoupled from Gemini wire format while avoiding the abstraction overhead of LangChain or LangGraph before they are actually justified.
- The current concrete implementation is Gemini-only, with `gemini-2.5-flash` as the default model.

### Dynamic filter surfacing and user-stated priorities

There are potentially 20–30 meaningful accommodation and resort filters (board type, sauna, jacuzzi, ski bus, ski-in/ski-out, creche, après-ski vibe, parking, dog-friendly, etc.). Showing all of them upfront is overwhelming; surfacing only the ones relevant to what the user typed is a cleaner UX.

The intended model:
- Maintain a large pool of filter dimensions in the data model and ranking layer
- Show only the subset relevant to the user's query in the UI (inferred from the NL parse step)
- Allow users to state priorities explicitly ("budget and lift distance matter most") which adjusts ranking weights rather than just filtering — this is more powerful than hard filtering for soft preferences like wellness amenities

**This is a data problem first, not a UI problem.** The filter pool is only useful if the underlying resort/area data carries the corresponding attributes. Adding a "sauna" filter that returns empty or wrong results is worse than not having it. The right sequence:
1. Decide which filter dimensions are worth supporting and that can be realistically curated at scale
2. Expand the resort/area schema and seed data incrementally as the dataset grows
3. Build dynamic filter surfacing in the UI once the data is non-embarrassing

The UI logic (show relevant filters from query) is a small implementation step. The data curation behind it is the actual work.

### Near-term product direction
- The active product wedge is still trust-first ski planning: helping users decide where and when to ski with higher confidence.
- The immediate next execution step, however, is deployment readiness and a minimal discovery-to-action loop so the product becomes easy to launch, measurable, and easier to validate with real users once sharing starts.
- Public hosting can be deferred until the product is about to be shown externally; the important near-term milestone is a launch-ready codebase, not paying for a live URL before it is needed.
- Time-aware conditions history remains the next meaningful data-model expansion, but it now follows deployment readiness and one tracked outbound booking/referral action rather than preceding them.

### Operational direction for the next phase
- Lightweight observability and deployment support are worth adding once they improve demo reliability or feedback loops.
- Heavy platform work should remain subordinate to product learning at this stage.
- Event sourcing is out of scope for the near-term architecture; historical/time-aware conditions data is the right complexity step instead.

### Testing direction for the next phase
- Unit and integration tests remain the primary safety net for deterministic backend logic.
- The app has now reached enough cross-layer complexity that a small browser/E2E layer is justified for demo-critical journeys.
- That E2E layer should stay narrow and product-led:
  - trip brief -> interpret -> apply -> search
  - structured search -> select result -> book accommodation
  - time-aware planning flow once travel-window support lands
- The next meaningful hardening step should arrive together with time-aware planning rather than as a separate testing-only sprint.

### Snapshot-based planning model
- Month-aware ski-planning now uses a deterministic planning layer rather than an LLM-generated score.
- The existing refresh pipeline still updates the latest `resort_conditions` row, but it also appends a per-refresh snapshot into a separate history table.
- Search can optionally switch into a planning mode with a `travel_month` input:
  - use stored snapshots for that month when available
  - fall back toward resort seasonality and elevation heuristics when history is thin
  - expose a lightweight planning summary plus evidence count instead of a large diagnostics payload
- This keeps the first conditions-calendar step compatible with the existing architecture while avoiding provider-history backfill too early.
- Planning heuristics now live in one internal policy module rather than as scattered literals inside the planning function.
- The current policy is treated as heuristic version `v1`; future tuning should update that policy surface intentionally instead of changing isolated numeric literals in `planning.py`.

### Browser smoke coverage
- A small Playwright layer now protects the critical demo journeys that span browser, API, and app-serving boundaries.
- The scope stays intentionally narrow:
  - trip brief -> interpret -> apply -> search
  - month-aware search -> planning output -> booking CTA
- Vitest remains the primary frontend/unit layer; Playwright is only a smoke/regression layer for the highest-value user flows.

### Version-keyed LLM cache
- Parser and narrative cache entries are keyed by exact input plus model and prompt/schema version identifiers.
- There is no TTL in the first version.
- Cache invalidation happens naturally when the implementation version changes, not when time passes.

### Local `.env` loading
- The repo uses a small internal `.env` loader instead of adding a dotenv dependency.
- `.env` is loaded lazily when the Gemini client is instantiated.
- Values from the real shell environment still win; `.env` only fills missing variables.

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
