# AI Ski Travel Planner

## 1. What this product is

A conditions-smart ski trip planner that helps skiers discover the right resort, book their trip, and then stay informed and guided throughout it. The product travels with the user — from pre-trip planning at home to daily mountain decisions on the slope.

---

## 2. Problems being solved

1. **Discovery overload.** Hundreds of resorts, too many variables (snow reliability, skill fit, budget, crowd levels, travel distance) and no tool that weighs them together intelligently.
2. **Conditions anxiety.** Snow reliability is declining at lower-altitude resorts due to climate change. Skiers increasingly want data-backed assurance that the resort they're booking will actually have good snow when they arrive.
3. **On-mountain information gap.** Once at a resort, skiers have no personalized, conditions-aware daily guide. Resort apps are trail maps. Weather apps are generic. Nobody tells you which specific runs are best *for your level* based on *today's conditions*.

---

## 3. Target audience

**Primary:** Adults aged 30–55, intermediate to advanced skiers, planning 1–3 ski trips per year. They ski in Europe (Alps, Pyrenees) or North America (Rockies). They research before booking, care about snow quality, and travel with a partner, family, or small group. They are willing to pay for a better experience and have above-average disposable income.

**Secondary (later):** Ski tour operators and travel agents needing a recommendation and conditions layer for their clients.

**Not the target:** Complete beginners who default to the nearest resort, or hardcore locals who already know where to go.

---

## 4. Sport focus

**Ski and snowboard only.** The product is not a multi-sport travel planner. Windsurfing, kitesurfing, and other sports are out of scope. Diluting the focus across sports weakens positioning, data quality, and audience targeting. If a second sport is added in future, it must share the same core audience profile and conditions-driven logic — not be a superficial filter.

---

## 5. Product stages

### Stage 1 — Discovery engine
Help users find the right resort for their trip.

- Structured search: location, budget, skill level, quality tier, lift proximity
- Conditions-aware ranking: snow confidence, availability status, weather signal
- Explainable results: why this resort fits, what to watch out for, confidence score
- Natural language query parsing: free-text trip brief → structured filters
- Real foundation: persistence, real resort/conditions data, and a stronger natural-language layer

### Stage 2 — Booking integration
Close the loop so the product generates revenue and captures trip context.

- Affiliate links for accommodation booking (Booking.com, ski-specific operators)
- Rental equipment booking integration (Ski-Set, Intersport, local operators)
- Lift pass purchasing where available (resort direct, Liftopia-style partners)
- Trip record stored in the app after booking — this context powers Stage 3

### Stage 3 — Trip companion
Once the user has booked, the product becomes a daily travel companion.

- Push notifications: actionable, timely, non-obvious alerts
  - "15cm fresh snow overnight — powder runs best before 10am"
  - "Strong wind forecast — top lifts likely closed this afternoon"
  - "Visibility poor this morning — tree runs suggested, open pistes by noon"
- Daily "what to do today" chat: LLM grounded in live conditions + resort knowledge + user profile
  - Knows the user's skill level, group composition, equipment type
  - Answers questions like "which runs should we hit first?" or "is it worth going out today?"
- Trip dashboard: conditions summary, lift status, forecast for remaining days

### Stage 4 — Group and social layer
- Shared trip view for travel groups
- Group voting on where to ski
- Trip photo/moment sharing
- Organic viral loop: one booking pulls 3–5 friends into the app as users

---

## 6. Form factor

- **Primary client: mobile app** — the trip companion features (push notifications, on-mountain chat, daily conditions) only make sense on mobile. This is the target end state.
- **Secondary: web app** — the planning/discovery phase works well on desktop. Keep the web frontend as the planning surface.
- **Recommended mobile stack: Flutter** — better performance for maps, conditions dashboards, and real-time UI than React Native. Dart is accessible for TypeScript developers. Given the frontend will be rebuilt from scratch anyway, the React web demo's stack does not constrain this choice.
- **Backend: unchanged** — FastAPI remains the right foundation regardless of frontend platform. All mobile and web clients consume the same REST API.

Do not over-invest in the React web frontend beyond what is needed to validate UX and demo the product. The web demo is a prototype, not the final client.

---

## 7. Data strategy

The conditions + resort dataset is the core moat. Without real data, the recommendation engine has no surface to match against and the conditions signals are hollow.

**Resort database:**
- Target 100+ resorts across Alps (AT, CH, FR, IT), Pyrenees, Scandinavia, and eventually North America
- Rich structured data per resort: terrain profile, altitude range, typical season dates, family-friendliness, crowd levels, price band, lift system quality
- Start with 20–30 well-covered Alpine resorts for launch, expand incrementally
- Data must be manually curated and validated — do not rely on LLM-generated resort facts

**Conditions data:**
- Connect to real APIs: Open-Meteo (free tier), resort snow report feeds, weather services
- Daily refresh minimum; hourly during active trip companion use
- Snow confidence score must be derived from real signals, not mock data
- Build a conditions history model per resort over time — this enables the "conditions calendar" feature

**Conditions calendar (Stage 2/3 feature):**
- For a given resort: historically when is snow most reliable?
- For a given travel window: which resorts have the best expected conditions?
- Directly addresses climate anxiety and is a strong SEO/content asset

---

## 8. Monetization

**Primary (Stage 2):** Affiliate and referral revenue
- Accommodation referrals: ~€30–80 per completed booking
- Rental equipment referrals: ~5–10% commission
- Lift pass referrals where available

**Secondary (Stage 3+):** Premium subscription
- Free tier: discovery and basic conditions
- Premium: trip companion, push notifications, daily chat, conditions calendar
- Pricing: ~€5–10/month or ~€15–25/season pass

**Later:** B2B licensing to ski tour operators and travel agents needing a recommendation layer.

---

## 9. Competitive position

No existing product combines conditions intelligence + personalized matching + booking + on-mountain companion in a single flow. Current alternatives are either:
- Conditions-only apps (OnTheSnow, PowderAlert) — no planning or personalization
- Booking platforms (Liftopia, SkiBookings) — transactional, no discovery or conditions
- Generic AI travel planners (Roam Around, Layla) — no sport-specific depth, no conditions data
- Resort apps — glorified trail maps, no personalization

The window for an independent product in this space is approximately 18–24 months before large travel incumbents (Booking.com, Google, Skyscanner) add sport-specific AI filtering. Speed of real data acquisition and booking integration is the priority.

---

## 10. What not to build

- Multi-sport generalization (windsurf, kite, etc.) — dilutes focus and data investment
- Generic AI itinerary generation — crowded, low defensibility
- Social features before the core planning + companion loop is solid
- A native app before the booking layer exists and trip context can be stored
- Elaborate personalization before there are real users generating history data

---

## 11. Architecture

- **Frontend (web, prototype):** React + TypeScript + Vite + Tailwind
- **Frontend (mobile, target):** Flutter
- **Backend:** FastAPI + Python 3.11+
- **AI module:** LangChain / LangGraph / OpenAI API — for query parsing, explanation generation, trip companion chat
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **External integrations:** conditions/weather APIs (Open-Meteo), booking affiliate APIs, resort snow report feeds
- **Testing:** Pytest (backend), Vitest + React Testing Library (web frontend)

---

## 12. Working guidelines

- Keep AI logic separate from business logic
- Write tests for critical logic, not for simple glue code
- Modular architecture: each module has a clear purpose
- Thoughtful use of LLM: cache expensive calls, use testable prompts
- Prioritize readable and typed code
- Do not rely on LLM-generated resort or trail facts — all structured data must be verified

---

## 13. Sprint history

### Sprint 1 — completed
- Activity recommendation module (MVP)
- Hardcoded dataset of activities (resorts/spots)
- Simple API interface for structured requests (sport, region, difficulty)
- Unit tests for core filtering logic

### Sprint 2 — completed
- Resort, accommodation (area) and rental recommendation (structured input only)
- Hardcoded dataset of resorts, areas, and rentals (5–10 resorts)
- Filtering and ranking logic; API endpoint `/search` returning structured JSON
- Deterministic ranking without LLM

### Sprint 3 — completed
- Extended deterministic search filters: skill level, lift distance, budget flexibility
- Refactored backend: separated input models, ranking logic, data loading
- Moved resort dataset from hardcoded Python to validated JSON loading
- Optional LLM-assisted query parser as thin input layer

### Sprint 4 — completed
- Lightweight external conditions signal (weather/snow confidence)
- Structured explanation of why each resort ranked highly
- Recommendation confidence / tradeoff summary
- Stable API contract and seed data quality improvements

### Sprint 5 — completed
- Refined conditions model: snow confidence score + label (poor/fair/good)
- Availability status (open/limited/temporarily_closed/out_of_season)
- Conditions score integrated into ranking with availability penalties

### Sprint 6 — completed
- Grouped explanation structure: highlights / watchouts / confidence_contributors
- Deterministic explanation generation grounded in ranking factors

### Sprint 7 — completed
- Thin demo frontend: React + TypeScript + Vite + Tailwind
- Structured search form, ranked result cards, selected-result details panel
- Smoke-level frontend tests with Vitest and React Testing Library

### Sprint 8 — completed
- Introduce SQLite as the first real storage layer, with PostgreSQL deferred for later production use
- Add a repository/data-access boundary so domain logic no longer depends directly on checked-in JSON files
- Migrate resort and conditions seed data into the database
- Keep the existing domain model and `/search` contract stable; persistence is an implementation detail in this sprint
- Add repository-level tests and keep all existing service/API tests passing

### Sprint 9 — real resort and conditions data
- Integrate one real external conditions source, starting with Open-Meteo, and normalize it into the existing internal conditions model
- Expand the resort dataset to 20–30 manually curated Alpine resorts with richer structured metadata
- Define data freshness and fallback behavior:
  - refresh interval
  - stale-data handling
  - degraded-mode behavior when external conditions fail
- Keep resort metadata manually curated and verified; do not use LLM-generated resort facts
- Add tests for normalization, staleness handling, and fallback behavior

### Sprint 10 — LLM layer on top of the discovery engine
- Replace the heuristic free-text parser with an LLM-backed parser that converts trip briefs into structured filters
- Add a concise recommendation narrative layer grounded strictly in the existing structured explanation output
- Keep deterministic ranking underneath; the LLM does not decide ranking
- Cache both parser and narrative outputs to reduce repeated calls and latency
- Preserve parser confidence and fallback behavior when extraction is weak or incomplete
- Add tests with mocked LLM calls for structure, validation, and fallback behavior
