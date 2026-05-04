# AI Ski Travel Planner

## 1. What this product is

A conditions-smart ski trip planner that helps skiers discover the right resort, book their trip, and then stay informed and guided throughout it. The product travels with the user — from pre-trip planning at home to daily mountain decisions on the slope.

The core product promise is trusted decision support under uncertainty, not generic AI chat. The app
should increasingly earn trust by making conditions signals explainable, timestamped, and clear about
what is forecast, reported, or estimated.

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
- Conditions-aware ranking: snow confidence, disruption risk, weather signal
- Explainable results: why this resort fits, what to watch out for, confidence score
- Transparency over false certainty: show source freshness and make uncertainty legible where possible
- Natural language query parsing: free-text trip brief → structured filters
- Real foundation: persistence, real resort/conditions data, and a stronger natural-language layer

### Stage 2 — Booking handoff and trip context
Close the loop so the product generates revenue and captures trip context.

- Affiliate links and outbound handoff for accommodation booking (Booking.com first, then ski-specific operators)
- Rental equipment booking integration (Ski-Set, Intersport, local operators)
- Lift pass purchasing where available (resort direct, Liftopia-style partners)
- Capture a provider-agnostic trip record in the app after booking handoff or manual trip setup — this context powers Stage 3
- Users who book elsewhere should still remain first-class users; Booking.com is a first monetization channel, not the product identity

### Stage 3 — Trip companion
Once the user has trip context, the product becomes a daily travel companion.

- Push notifications: actionable, timely, non-obvious alerts
  - "15cm fresh snow overnight — powder runs best before 10am"
  - "Strong wind forecast — top lifts likely closed this afternoon"
  - "Visibility poor this morning — tree runs suggested, open pistes by noon"
- Daily "what to do today" chat: LLM grounded in live conditions + resort knowledge + user profile
  - Knows the user's skill level, group composition, equipment type
  - Answers questions like "which runs should we hit first?" or "is it worth going out today?"
- Trip dashboard: conditions summary, disruption risk, forecast for remaining days
- Trip context should include resort, area, travel dates, accommodation status, and optional accommodation name/provider when known

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

### Current client split

- **React web remains the easiest demo surface.** It is the fastest way to show the product in a browser, portfolio, or live conversation because it has no install friction.
- **Flutter currently exists as the mobile companion client.** It is not replacing the public demo surface yet; it is proving the authenticated mobile path and later push-oriented companion features.
- **The Flutter app is intentionally mobile-only in this repo.** Keep only `ios/` and `android/` as Flutter platform folders. The generated `macos/`, `linux/`, `windows/`, and Flutter `web/` shells add maintenance cost without supporting the near-term product plan.
- **Most Flutter product logic lives in shared Dart code.** The real app logic is in `mobile/lib/`; `ios/` and `android/` mainly hold the native host wrappers, platform configuration, bundle/package identifiers, permissions, and Google sign-in wiring.
- **The separate React web app remains the web strategy.** Do not treat Flutter web as a second web frontend unless there is a deliberate product decision to replace or merge the existing React demo.

### Auth model by client

- **Backend-owned sessions are the source of truth.** Google is currently only the upstream identity provider; the backend verifies the Google identity token and then issues its own bearer token.
- **Mobile auth is implemented first.** The Flutter app uses native Google sign-in and exchanges the Google identity token with the backend through `/api/auth/google/sign-in`.
- **Web auth is not a first-class product surface yet.** The current web app remains mostly anonymous so it stays frictionless as a planning and demo surface.
- **If web auth is added later, it should reuse the same backend session model.** The web client would obtain a Google identity token using a web OAuth client and then call the same backend sign-in endpoint rather than inventing a separate auth system.
- **Keep the client roles distinct for now.** Web is the main planning/demo surface; mobile is the authenticated companion surface.

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
- Use Booking.com as the first accommodation partner where practical, but keep the product useful for users who book directly or through other providers

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
- **AI module:** direct Gemini API behind a local provider seam for query parsing and grounded narrative generation; LangChain/LangGraph deferred until retrieval or orchestration complexity justifies them
- **Database:** PostgreSQL (local/dev + prod)
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
- Very early activity recommendation module (MVP), later retired once the repo narrowed to ski-trip planning
- Hardcoded dataset of activities (resorts/spots), later removed as non-core scaffolding
- Simple API interface for structured requests (sport, region, difficulty), later removed
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
- Disruption status (open/limited/temporarily_closed/out_of_season compatibility values)
- Conditions score integrated into ranking with disruption penalties

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

### Sprint 9 — completed
- Integrate one real external conditions source, starting with Open-Meteo, and normalize it into the existing internal conditions model
- Expand the resort dataset to 20–30 manually curated Alpine resorts with richer structured metadata
- Define data freshness and fallback behavior:
  - refresh interval
  - stale-data handling
  - degraded-mode behavior when external conditions fail
- Keep resort metadata manually curated and verified; do not use LLM-generated resort facts
- Add tests for normalization, staleness handling, and fallback behavior

### Sprint 10 — completed
- Replace the heuristic free-text parser with an LLM-backed parser that converts trip briefs into structured filters
- Add a concise recommendation narrative layer grounded strictly in the existing structured explanation output
- Keep deterministic ranking underneath; the LLM does not decide ranking
- Cache both parser and narrative outputs to reduce repeated calls and latency
- Preserve parser confidence and fallback behavior when extraction is weak or incomplete
- Add tests with mocked LLM calls for structure, validation, and fallback behavior

### Sprint 11 — superseded by later completed work
- Make the product deployment-ready for a public launch, with one single-URL app shape that can be hosted when sharing begins
- Add the hosted environment foundation: runtime configuration, secret handling, and a practical production persistence choice
- Introduce basic CI/CD and lightweight observability so hosted behavior is visible and debuggable
- Add a small frontend polish step for demo readiness: integrate `/parse-query` as an AI-assisted trip-brief interpretation flow above the structured search form
- Keep the UX transparent and controllable: show extracted filters, confidence, and unknown parts, then let the user review/apply the results into the editable structured form before running `/search`
- Keep the deployment scope pragmatic: enough reliability for strong demos and local validation, not a full production platform
- Add tests/checks needed to keep the deployable path trustworthy
- Defer the actual public hosting step until sharing/demo timing justifies it; provisioning a live URL is a Sprint 11 close-out task rather than the definition of implementation completeness

### Sprint 12 — completed
- Add one real tracked outbound booking/referral flow so discovery can lead to measurable user action
- Frame the first version pragmatically: affiliate-backed if feasible, but not blocked on deep partner integration complexity
- Add simple click/event tracking so the product can measure whether recommendations drive booking intent
- Improve result presentation and CTA placement around discovery-to-action rather than building a full booking platform
- Keep the scope focused on closing the recommendation loop and proving an early business signal

### Sprint 13 — completed
- Add a month-level travel-window input so resort search can consider a selected planning month instead of only current conditions
- Build the first conditions-calendar foundation using snapshot-style conditions history per resort, appended from the existing refresh pipeline
- Extend the deterministic planning model to answer “which resorts are safer for this travel window?” while degrading gracefully when history is sparse
- Surface lightweight comparative planning output in the current search flow, including planning summaries, evidence counts, and best-fit months per resort
- Keep the first version scoped to planning confidence rather than full long-range forecasting or provider-history backfill
- Add a broader hardening batch around the new planning flow:
  - backend scenario/integration coverage for multi-step product flows
  - narrow frontend end-to-end/browser coverage for critical demo journeys
  - single-app smoke coverage for the built frontend + `/api` backend shape
- Keep testing as a supporting deliverable for the planning feature, not as a separate test-only sprint

### Sprint 14 — completed
- Make trust and provenance a first-class product surface in the existing search and planning flow
- Add visible signal freshness and source-type cues so conditions evidence is easier to trust:
  - last-updated timestamps
  - clearer distinctions between forecast, reported, and estimated signals where supported
  - clearer uncertainty wording in planning and search explanations
- Improve frontend presentation so trust cues are visible without turning the product into a diagnostics console
- Keep the backend deterministic; this sprint is about exposing and explaining evidence better, not changing ranking ownership
- Keep public deployment as an optional close-out task only if sharing starts during the sprint; do not let hosting displace the trust/provenance work

### Sprint 15 — completed
- Upgrade booking from a generic CTA into a more useful handoff layer
- Improve outbound deep links from generic search to a resort-level handoff, with area-level links deferred until the data and product can support them
- Introduce the first provider-agnostic trip-context model:
  - booked through app
  - booked elsewhere
  - not booked yet
- Persist a single current trip from the selected result panel, including resort, selected area, optional travel month, and booking status
- Use that trip-context model in the UI and backend as the basis for later companion features
- Explicitly defer accommodation-provider details, accommodation-preference filters, and multi-trip support until the underlying data model can support them credibly

### Sprint 16 — completed
- Add the first lightweight Stage 3 capability using the trip-context model from Sprint 15
- Focus on trip-specific conditions and delta-based guidance rather than a large assistant surface:
  - what changed since the trip was saved
  - what changed since the last explicit check
- Add a dedicated `Current trip` view with a simple app-level `Search / Current trip` switch
- Keep the sprint provider-agnostic so companion value works whether the user booked through the app or elsewhere
- Keep baseline advancement explicit via `Mark checked`; opening the companion view does not reset it
- Do not expand into a full LangGraph-style assistant yet; keep orchestration simple unless the product clearly needs multi-step stateful behavior

### Sprint 17 — completed
- Improve recommendation trust before launch through a two-phase Sprint 17:
  - Phase 1: source-backed audit of current resort metadata
  - Phase 2: planning calibration and realism fixes
- Audit season months, elevations, coordinates, and synthetic area naming across the current resort set
- Make sparse-history and season-edge planning materially more conservative, with realism tests for known late-season problem cases
- Keep `/api/search` stable; improve output quality rather than widening the product surface
- See [`docs/sprints-17-19.md`](docs/sprints-17-19.md) for detailed Sprint 17–19 planning and [`docs/sprint-17-resort-audit-results.md`](docs/sprint-17-resort-audit-results.md) for the completed audit record

Launch should follow this sprint, not precede it, because recommendation trust is currently the gating issue.

### Sprint 18 — completed
- Deploy the single-URL app publicly using the existing built-frontend + FastAPI shape
- Add a scheduled conditions refresh job outside the search request path, currently via GitHub Actions rather than a resident app worker
- Use Fly.io for hosting and Neon as the external managed Postgres provider
- Make PostgreSQL the default database in both local/dev and production; no SQLite migration path is planned
- Add GitHub Actions CI/CD with deploys on push to `main`
- Add minimal observability and a production runbook for health, freshness, and booking-click visibility
- Keep this sprint narrowly operational: no Kubernetes and no broad data-model expansion

### Sprint 19 — completed
- Add a new raw historical weather layer so planning no longer depends only on sparse derived snapshot history
- Add a manual operator backfill command for roughly five years of daily history, shaped so GitHub Actions can wrap it later if needed
- Make ongoing refresh append raw daily weather observations so historical evidence keeps growing after the initial backfill
- Introduce a finer-grained derived planning evidence layer over raw history while keeping the public search contract centered on `travel_month`
- Strengthen conditions and planning evidence with additional snow signals such as snow depth, while leaving live operational coverage signals such as `% lifts active` for later sprints
- Add narrow horizon-aware planning foundations so same-month or next-month planning can later blend forecast signal more credibly without exposing exact-date trip inputs yet
- Keep resort expansion out of scope for this sprint so the data and planning foundation lands cleanly first

### Sprint 20 — completed
- Make planning time-aware and semantically cleaner before expanding product breadth
- Add exact-date or date-range planning support to the backend and REST API while keeping the current web UI mostly month-oriented
- Add automated recent-day archive reconciliation so provisional `forecast` rows can be replaced or superseded by `archive` truth after the fact
- Make planning explicitly horizon-aware:
  - close trip windows can weight forecast materially
  - farther trip windows rely mostly on archive/history and seasonal evidence
- Improve planning provenance and evidence metadata so clients can distinguish forecast-assisted, archive-backed, and fallback-heavy recommendations
- Keep this sprint backend/API heavy; do not turn the prototype React frontend into the main exact-date planning client

### Sprint 21 — completed
- Initialize Flutter as the primary future client while keeping the React web frontend in maintenance mode only
- Implement the first mobile planning surface against the existing FastAPI backend:
  - trip brief/search
  - results
  - selected resort detail
  - current trip view
- Add lightweight authenticated user identity in the same sprint so trip context belongs to a real user before companion features arrive
- Keep auth intentionally narrow:
  - Google-only login
  - backend-issued bearer tokens
  - enough to bind user, trip context, and later device tokens
  - not a broad profile/settings/account-management sprint
- Add API contract tests for the mobile-dependent endpoints so the backend/client boundary is protected during the Flutter transition

### Sprint 22 — completed
- Build the first credible Stage 3 companion loop on top of authenticated trip context, with the right client emphasis:
  - backend first for trip-window awareness, notification eligibility, and change detection
  - web second for planning improvements that are easier to demo and share publicly
  - mobile third as the thin authenticated companion client
- Reframe the sprint as a companion-foundation sprint rather than a broad Flutter UI sprint
- Add exact trip dates to the saved trip-context/current-trip model and use them in backend logic for:
  - active/upcoming/past trip classification
  - notification eligibility
  - trip-window-aware change detection
- Add backend support for device registration and notification-target persistence tied to authenticated users
- Build the first backend-driven companion event loop:
  - detect meaningful conditions changes for the user's saved trip
  - record only eligible/actionable updates
  - suppress duplicate events with deterministic signatures
  - keep the logic deterministic and explainable
- Keep the mobile scope intentionally narrow:
  - authenticated current-trip retrieval
  - minimal notification history/status surface
  - enough UI to prove the notification-ready companion path
- Make exact-date planning more visible in the web UI as the main demo surface without adding web auth or authenticated saved-trip editing
- Do not make mobile UI polish a core Sprint 22 goal
- Keep this sprint focused on companion infrastructure and utility, not full daily chat, richer assistant orchestration, broad settings/profile work, or real APNs/FCM delivery

### Sprint 23 — completed
- Build an AI-native web planning experience while keeping the backend search contract mostly unchanged
- Make the trip brief the primary web planning input rather than a helper above a static filter form
- Show inferred and applied filters as removable chips so users can see and adjust the structured state behind the search
- Replace separate `Travel month`, `Trip start date`, and `Trip end date` controls with one user-facing `Travel window` concept:
  - no time constraint
  - month-level planning
  - exact date range planning
- Move the existing manual controls into a secondary `Refine filters` panel:
  - location
  - skill level
  - budget
  - minimum quality
  - lift distance
  - budget flexibility
  - travel window
- Extend the parser so interpreted trip briefs can distinguish:
  - month-only requests such as "March"
  - exact ranges such as "9 Apr to 16 Apr"
  - approximate ranges such as "first week of March" when a concrete date window can be inferred
- Apply parsed travel timing into the new web `Travel window` state, with exact dates taking precedence over month when both are inferred
- Keep Sprint 23 focused on existing filter semantics only:
  - no spa, food, ski bus, apartment type, board type, wellness, family, or ski-in/ski-out filters
  - no new resort or stay-base data model fields
  - no ranking changes for new preference dimensions
  - no generic AI chat panel
  - no web auth
  - no broad mobile UI polish

### Sprint 24 — completed
**Demo reliability and product-state cleanup**

- Treat this as a short hardening sprint before the next visible web redesign
- Update stale Playwright e2e tests so they cover the current Sprint 23 brief-first UI:
  - user note input
  - inferred/applied chips
  - `Travel window`
  - `Adjust filters`
  - `Find resorts`
- Clean stale documentation that now contradicts the product state:
  - exact trip dates are stored on current trips
  - Sprint 23 replaced separate month/date controls with one `Travel window`
  - older near-term roadmap notes should no longer imply deployment/history work is still the immediate next step
- Tighten only small parser fallback gaps for already-supported filters:
  - common lift-distance phrasing such as "close to the lift" and "not too far from the lifts"
  - common affordability wording that should map to the existing budget fields when safe
- Clarify filter chip wording/provenance where needed so users understand the chips represent current search state, not necessarily only AI-inferred fields
- Wire mobile exact-date search into the existing backend contract:
  - Flutter search should send `trip_start_date` and `trip_end_date` when both date fields are present
  - exact dates should take precedence over `travel_month` for mobile search requests
  - this should reuse the current mobile fields and avoid a mobile UI redesign
- Audit remaining mobile parity gaps and document or make small low-risk fixes where practical:
  - parsed-filter parity
  - device registration readiness
  - companion-specific UI cleanup
- Keep Sprint 24 explicitly out of product expansion:
  - no new semantic filters
  - no web auth
  - no routeable redesign
  - no mobile redesign or new mobile planning controls
  - no push delivery
  - no new ranking dimensions

### Sprint 25 — completed
**Routeable search and selected-resort detail**

- Split the previous single-screen web planning experience into clearer routeable app surfaces:
  - search/discovery page with AI-assisted input, active filter chips, refine panel, and resort result cards
  - selected-resort detail page with snow confidence, travel-window fit, evidence/provenance, highlights, risks, booking CTA, and save-current-trip CTA
  - current-trip page focused on companion status, conditions changes, and notification/event history
- Added lightweight client-side routing without a new dependency:
  - `/` for search/discovery
  - `/resorts/:resortId` for the selected-resort detail route
  - `/current-trip` for the companion/current-trip route
- Persisted the latest search context in `sessionStorage` so a selected-resort app route can survive reloads during a demo
- Kept direct selected-resort routes honest: when no cached search context exists, the page shows a clear "Run a search first" fallback instead of pretending to be a public resort page
- Preserved the Sprint 23 interaction model:
  - user note first
  - visible applied chips
  - manual refinement second
  - structured backend ranking remains the source of truth
- Use the references in [`docs/ui-ideas`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/docs/ui-ideas) as inspiration for cleaner cards, empty states, and detail-page hierarchy, not as a literal design to copy
- Preserved the product differentiators while redesigning:
  - visible trust/provenance
  - evidence-backed planning
  - explanation of why a resort fits
  - continuity from discovery to saved trip and companion mode
- Avoided fake marketplace polish unless the underlying data supports it; do not make the app look more complete than the resort/accommodation data actually is
- Kept Sprint 25 focused on web information architecture:
  - no accommodation provider integration
  - no richer spa, food, ski-bus, family, wellness, or ski-in/ski-out filters
  - no generic AI chat panel
  - no web auth unless a small guardrail is required for an existing saved-trip action
- No backend API, database, npm dependency, or search-contract changes were introduced

### Sprint 26 — completed
**Web UI/UX redesign and selected-resort hierarchy**

- Redesigned the routeable web experience on top of the Sprint 25 routes:
  - `/` search/discovery
  - `/resorts/:resortId` selected-resort detail
  - `/current-trip` companion/current-trip status
- Used the references in [`docs/ui-ideas`](/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/docs/ui-ideas) as inspiration for cleaner cards, stronger empty states, clearer detail sections, and a more product-grade visual language without copying unsupported marketplace features
- Kept the current product model intact:
  - trip brief remains primary
  - inferred/applied filter chips stay visible and removable
  - `Adjust filters` remains the manual control surface
  - backend ranking, parser/search behavior, and evidence/provenance remain unchanged
- Improved the search/discovery page:
  - split planning input and results into clearer surfaces
  - made result cards scan like credible recommendation cards with status, confidence, evidence, stay-base, and rental facts
  - kept the routeable search state and direct-detail fallback from Sprint 25
- Redesigned the selected-resort page so it no longer feels like a widened side panel:
  - hero summary
  - current conditions
  - travel-window fit
  - highlights and risks
  - evidence/provenance
  - stay/rental facts
  - booking and save-current-trip CTAs
- Tightened the current-trip empty state so the web demo explains why companion status appears only after a resort is saved
- Kept trust/provenance visible through user-facing evidence wording rather than raw debug output
- Kept Sprint 26 focused on presentation and hierarchy:
  - no backend API or schema changes
  - no public SEO pages yet
  - no new semantic filters
  - no accommodation provider integration
  - no web auth
  - no generic AI chat panel
  - no broad mobile redesign

### Sprint 27 — completed
**Public resort pages and conditions-calendar content**

- Built the first public, shareable, indexable content surface for demo and organic growth
- Added backend-rendered resort guide pages under `/ski-resorts/{resort_id}` so the page body and metadata are visible in raw HTML before any React app loads
- Kept the existing `/resorts/:resortId` route as the search-context React detail route; public SEO pages live under the separate `/ski-resorts/*` namespace
- Added deterministic resort pages powered by the existing planning/provenance model:
  - where the resort is
  - when it tends to be a good fit
  - current snow/availability signal
  - historical weather evidence
  - why the recommendation is or is not confident
- Added a conditions-calendar section generated for each resort's in-season months using the same planning assessment logic as search
- Refined public calendar copy so it reads as evergreen resort guidance:
  - month cards use archive-backed seasonal evidence only
  - current forecast remains isolated in the `Current snow signal` section
  - raw evidence-window counts and timestamp strings are kept out of primary month-card copy
- Added derived historical weather metrics from `raw_weather_history`:
  - average snow depth
  - average daily snowfall
  - average max temperature
  - average wind gust
  - historical season coverage
  - latest observed archive date
- Exposed optional `planning_weather_metrics` on search results and surfaced compact `Mid-mountain snow`, `Avg high`, and historical-season cues in the React result/detail UI without changing ranking behavior
- Added public discovery endpoints:
  - `/sitemap.xml` lists public resort pages from the resort repository
  - `/robots.txt` allows indexing and points crawlers at the sitemap
- Included minimum public-page discovery metadata as part of the feature, not as a later cleanup:
  - canonical URL per public resort page
  - page-specific title and meta description
  - basic Open Graph/Twitter preview metadata
  - sitemap entries for every catalog resort
- Chose a crawler-friendly rendering path using FastAPI-rendered HTML before the SPA catch-all; SPA-only client-side metadata remains out of scope for public pages
- Kept Sprint 27 focused on public content:
  - no mandatory sign-in
  - no full SEO platform work beyond deterministic public pages and their required metadata
  - no provider-backed accommodation overhaul
  - no push notification delivery
  - no country/month collection pages yet

### Sprint 28 — completed
**Recommendation trust and data quality**

Sprint 28 made the current recommendation engine and 26-destination catalog more explicit, validated, and honestly labeled before more public growth, web auth, or notification delivery work.

- Normalized the catalog so all 26 destinations now carry explicit `ski_areas` and `stay_bases`; production seed loading no longer silently generates default ski areas.
- Preserved existing generated ski-area IDs such as `{resort_id}-ski-area` where needed to avoid invalidating weather-history identity.
- Added `app/data/resort_trust_manifest.json` with trust statuses for critical field groups: `verified`, `verified_with_adjustment`, `estimated`, and `needs_source`.
- Added `python -m app.data.validate_resort_catalog` to validate explicit entities, stable IDs, plausible coordinates/elevations, trust-manifest coverage, and source refs for source-backed trust statuses.
- Source-backed the previously estimated Hintertux, Stubai Glacier, and Zell am See-Kaprun trust entries using official/geospatial/rental-provider references; spot-checked Tignes, La Plagne, and Zermatt against official sources so the verified labels are not only inherited from earlier catalog work.
- Clarified recommendation semantics without changing `/api/search` request fields:
  - `stars` remains the compatibility parameter but means internal quality tier: budget, standard, or premium.
  - `min_price` and `max_price` mean nightly stay-base budget estimates in EUR.
  - rental price is displayed separately and is no longer mixed into budget filtering as a fake package price.
  - `availability_status` remains the compatibility field but is presented as weather-derived disruption risk unless future provenance is truly `reported`.
- Updated backend explanations, public pages, and React copy so weather-derived signals no longer read like official lift-operation status.
- Added golden recommendation coverage for stay-budget semantics, beginner fit, sparse evidence, late-spring high-elevation behavior, and exact-date forecast-assisted vs archive-backed planning.
- Added durable methodology docs in [`docs/data-trust-model.md`](docs/data-trust-model.md), with supporting updates in [`docs/planning-model.md`](docs/planning-model.md) and [`docs/engineering-notes.md`](docs/engineering-notes.md).

Execution detail lives in [`docs/superpowers/specs/2026-05-02-recommendation-trust-data-quality-design.md`](docs/superpowers/specs/2026-05-02-recommendation-trust-data-quality-design.md). `PROJECT.md` is the roadmap source; the linked spec is the agent handoff for scope, acceptance criteria, data contract, and verification.

## Backlog

These are important next-wave concerns that should stay visible after Sprint 23. Sprint 25, Sprint 26, and Sprint 27 promote the routeable web redesign, UI/design-language pass, and public resort pages from this backlog into planned work; the remaining items are still uncommitted candidates for later product, growth, and data-quality work.

### Web authentication and cross-surface continuity
- Add optional Google sign-in to the React web app once authenticated trip continuity is valuable after Sprint 27
- Keep anonymous web search available so the product remains easy to demo and share
- Use web auth to unlock saved-trip ownership, trip-date editing, and continuity between web planning and the mobile companion
- Reuse the existing backend session model and `/api/auth/google/sign-in` exchange pattern rather than inventing a separate web-specific auth system

### Mobile companion parity
- Bring the Flutter companion closer to the backend/web product model once the web demo surface is stronger
- Add exact-date search parity so mobile search can send `trip_start_date` and `trip_end_date`, not only `travel_month`
- Apply parsed filters consistently where mobile already exposes matching controls:
  - travel window
  - lift distance
  - quality tier
  - budget flexibility if kept in mobile
- Register mobile devices against the existing backend device-registration endpoint when real notification delivery becomes closer
- Keep mobile cleanup companion-specific rather than broad visual polish

### Search origin and distance filtering
- Add an explicit origin or travel-distance input to search so users can avoid resorts that are too far away
- Prefer a deterministic first version based on user-provided origin or distance preference rather than inferred device location
- Consider user-location-based convenience only later, when mobile/auth are in place and permissions/UX can be handled cleanly

### Accommodation filter enhancements
- Revisit accommodation-side filters such as board type, wellness, ski bus, and ski-in/ski-out
- Only expose these filters once the underlying stay-base data model and curation are trustworthy enough to support them credibly
- Treat this as post-Sprint-23 structured data and ranking work, not just a UI filter addition

### Accommodation price and quality realism
- Revisit whether current accommodation price ranges and stars/quality should become provider-backed or otherwise more factual
- Treat current values as product-curated heuristics until a real accommodation data source exists
- Plan this work only once the project is ready to invest in a stronger accommodation/provider data path

### Lift-distance semantics
- Reassess the usefulness of `lift_distance` while the product still models only coarse stay bases
- Keep the concept only where the selected stay base is meaningfully near, medium, or clearly far from lift access
- Improve or de-emphasize this filter later depending on whether stay-base granularity becomes richer
