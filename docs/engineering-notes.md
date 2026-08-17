# Engineering Notes

Curated technical notes for this project. This file captures:
- how selected tools and frameworks work in the context of this repo
- why key technical decisions were made
- important tradeoffs and consequences
- concise notes prompted by clarification questions during development

This is not a changelog and not a transcript of chat discussions. Keep entries short, practical, and tied to this codebase.

Use `docs/architecture/adr/` for durable architecture decisions with meaningful
alternatives or long-lived consequences. Use `docs/domain-language.md` for
shared Snowcast domain terms, bounded contexts, and invariants.

## Architecture

### Maintainer dispatch correction

- A completed helper rejection with `reason=invalid-command`, `stage=dispatch`,
  and `outcome.mutation_occurred=false` proves that no capability ran. The
  maintainer must reload the registered same recipe and execute one corrected
  attempt; generic capability-error stops do not apply to this first safe
  rejection.
- Missing or positive mutation status, uncertain execution, a non-dispatch
  error, an ambiguous recipe, or a second rejection still stops fail-closed.

### Maintainer evidence inventory completion

- The initial catalog review evidence envelope is provisional until independent
  source-trust and graph-scope lanes both return complete dispositions.
- An incomplete lane produces a structured missing-item checklist instead of
  immediately authorizing a catalog fix or ending an otherwise productive run.
- The maintainer may perform at most two report-only inventory-completion passes.
  Each pass must shrink the unresolved checklist and is followed by fresh dual
  review on the exact new head.
- Completion may change only the canonical curation report. Catalog and trust
  payloads and object IDs remain unchanged, and no helper continuation or
  cross-run authority is created from the local report commit.
- Inventory completeness is a knowledge gate, not a correctness gate. Each
  checklist item becomes missing, verified complete, actionable, defensibly
  deferred, or blocked by concretely unavailable evidence. Actionable catalog,
  trust, backlog, rendered-report, and focused-test defects move into ordinary
  remediation rather than keeping the review incomplete.
- Missing exact evidence for an optional scalar fact is actionable whenever the
  value can be safely qualified as a proxy, downgraded, or removed. Unavailable
  evidence blocks inventory only for graph-critical identity, ownership,
  access, or pass-validity facts with no conservative graph-safe disposition.
- A graph-blocking deferral closes the knowledge gap but creates a graph-safety
  finding; only a regional follow-up can defer without remediation. Conflicting
  lane outcomes remain missing until a focused exact-head reconciliation.
- A first pass that strictly shrinks the checklist receives the second permitted
  pass before the 210-minute cutoff. Unavailable items are excluded without
  cancelling research for other missing items, and predicted non-completion is
  not a stop condition.
- Triage exposes only the pass count, remaining unresolved count, and bounded
  stop reason so operators can diagnose convergence without persisting semantic
  evidence in helper state.
- `review-incomplete` remains the safe outcome when evidence cannot be found,
  progress stops, scope becomes unsafe, time expires, or two passes do not
  complete the inventory.

### User-facing content ownership

- B2 English is the maximum product-language complexity; simpler is preferred.
- Refinement vocabulary is server-owned and versioned.
- Data-dependent recommendation and dossier sentences are built from typed view models.
- Reusable actions, statuses, and empty states use the shared frontend copy module.
- Components do not translate raw trust enums or reconstruct domain meaning.
- Human Content & Language review remains authoritative; readability scores and blocked-word checks are supporting tools only.
- Public `Trip option` counts refer to recommendation groups. Internal candidate
  or configuration counts must not be relabeled as customer-visible trip
  options. Variants inside one group are described as other ways to plan that
  trip, not as additional top-level Trip options.
- Terrain-distance copy must preserve both evidence scope and trust on every
  client. A ski-area or terrain-domain value is not pass-covered terrain unless
  the typed evidence says so.
- Primary weather copy explains useful conditions and limitations. Exact
  aggregation methods, source rows, and calculation details belong in the
  advanced technical disclosure.
- A displayed recommendation keeps the applied search intent that produced it.
  Saving that recommendation must use its applied travel window, not newer
  draft controls that the user has not searched with yet.
- Weather headings derive from typed freshness provenance. Only fresh data is
  called current; stale data is labeled out of date, and unknown freshness is
  presented as the latest available information without a current-data claim.

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
1. FastAPI validates a typed `SearchV4Request` submitted to `POST /api/search`.
2. Hard constraints remove ineligible concrete access/area/pass candidates.
3. Search evaluates registered static factors, then bulk-loads climatology and
   latest complete forecast heads for the remaining ski areas.
4. The generic scorer applies the versioned group/factor policy and returns
   source-aware contribution breakdowns.
5. Optional LLM refinement proposes only registered typed patches;
   deterministic validation and impact simulation decide what is shown.
6. Results are grouped by trip-market `ski_region_id` with bounded material
   alternatives.

### Why the backend stays primary
- The product value is in the decision engine: ranking, fit, conditions, and explanation quality.
- The frontend is intended to exercise and present backend behavior, not define the domain model prematurely.
- The API contract remains stable while runtime reads are handled through Postgres-backed repositories.

## API Contract

### `/search`
- The endpoint is a typed POST contract with constraints, party and travel
  context, objectives, group priorities, factor preferences, and visible
  assumptions.
- Exact dates take precedence over a supplied month.
- The request cannot supply raw numeric weights or unregistered factor IDs.
- The response includes model/policy versions, the applied intent, candidate
  counts, fit/group/factor breakdowns, evidence provenance, and optional
  validated refinement questions.
- Important output groups:
  - one `RecommendationGroup` per ski-region trip market
  - a selected `TripConfiguration` with destination, base, focus area, and pass IDs
  - bounded alternative configurations inside the same market
  - grouped fit contributions plus factor evidence and provenance
  - optional typed refinement proposals

### Car-first travel effort
- Travel effort is a recommendation signal and explanation layer, not a generic travel planner.
- If no origin is supplied, the factor is inactive and results are not
  penalized for missing travel context.
- With an origin and car mode, the first evaluator is an approximate
  deterministic estimate based on known-origin geocoding, straight-line
  distance, a road multiplier, and calibrated long-distance speed. Its evidence
  cap is limited because it is not live routing.
- Travel effort soft-ranks when comparable evidence exists. A typed maximum
  travel-duration constraint excludes candidates before scoring.
- Rail, public transport, and flight modes remain neutral until a comparable
  evaluator is implemented; accepting the mode in the request is not a claim
  that route evidence exists.
- Flights, trains, airport selection, transfers, live traffic, and itinerary planning are intentionally out of scope until the ski recommendation model needs them.
- Approximate car travel cost is still deferred from total-trip budget calculations until duration, party size, lodging, and travel-cost assumptions can be combined without false precision.

### Historical Weather Evidence Bands
- Planning prefers mid-band archive weather for normal trip-window evidence.
- During the elevation-band migration period, older archive rows may exist only in the `upper` band. Search should fall back from mid to upper and then base when the preferred band has no archive rows for the requested month/day window.
- Fallback band usage remains visible through `planning_weather_metrics.elevation_band`; the long-term fix is still to run the banded historical-weather rebuild so mid-band evidence is available for supported resorts.

### Derived snow climatology
- `raw_weather_history` remains the audit and rebuild source for historical
  weather evidence.
- `ski_area_snow_climatology_daily` is a derived read model for request-path
  planning. It stores day-of-season aggregates by ski area, elevation band,
  baseline period, and model version.
- Search should prefer the derived climatology table for future trip windows and
  only fall back to raw archive rows when climatology is missing.
- The primary planning baseline is a WMO-style 30-year normal. Search V4 uses
  the recent 15-year baseline only when that normal is unavailable; it does not
  apply a hidden recent-period adjustment to the displayed normal.
- Physical snowpack models such as SNOWPACK, Crocus, and S2M-style chains are
  reference architectures for future upgrades, not current Snowcast
  implementation claims.

### `/parse-query`
- `/parse-query` can return richer trip context alongside the existing filter projection.
- `trip_context` captures context that may matter later but is not always a direct search filter yet, such as total-trip budget, party size, trip duration, and user-provided origin text.
- `clarifications` are generated by deterministic policy after parsing. They are bounded choices that patch local UI state; they are not an open-ended chat loop and they do not trigger routing, geocoding, or itinerary planning by themselves.
- Nightly lodging budget can still project into `/search` `min_price` and `max_price`. Total-trip budget remains context until enough duration, party-size, and travel-cost support exists to estimate it honestly.
- Parser output should not show already-consumed date text as `unknown_parts`. If the parser extracts exact dates from malformed-but-clear ordinal text such as `27st`, that token is treated as consumed by the travel window.
- Transient parser LLM errors are retried before deterministic heuristic fallback. The heuristic parser still needs to handle common date forms so search remains usable when the provider is temporarily unavailable.

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
- The redirect endpoint records one Postgres event row before sending the user to the external accommodation target.
- This keeps click tracking deterministic and testable without introducing third-party analytics.
- The current outbound target is a stay-destination-level Booking.com search
  deep link; later affiliate-backed variants should be swapped in behind the
  same redirect boundary.

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
- Current stage: stay-destination-level outbound accommodation search links.
- Next stage: area-level deep links that land closer to the recommended option when the product can support them reliably.
- Later: affiliate-backed variants of those same links once partner setup is ready.
- Property-level links should come only once the product can credibly recommend a specific accommodation rather than just a resort or area.

### Current trip model
- The first persisted trip context is a single current-trip record, not a multi-trip system.
- Trip creation is explicit and anchored to the selected result panel rather than auto-created on booking click.
- The saved record is intentionally provider-agnostic and currently stores:
  - `ski_region_id` and display name
  - `stay_destination_id` and display name
  - `stay_base_id` and display name
  - `focus_ski_area_id` and display name
  - `lift_pass_product_id` and display name
  - optional `travel_month`
  - optional exact trip dates
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
- Exact `trip_start_date` and `trip_end_date` now belong to the saved current-trip model when known.
- Companion deltas are intentionally narrow:
  - current conditions only
  - compared against `last_checked_at` when present, otherwise `created_at`
  - baseline advances only through an explicit `Mark checked` action
- Opening the companion view must not silently reset that baseline.
- If there is no earlier snapshot before the baseline timestamp, the API returns a graceful `not enough earlier history to compare yet` state instead of inventing a delta.

### Trip-window-aware companion eligibility
- Exact saved-trip dates are now the source of truth for companion timing when present; `travel_month` remains useful for planning/search but is not enough for push-style relevance.
- The backend classifies each saved trip into a small deterministic state:
  - `unscheduled`
  - `upcoming`
  - `active`
  - `past`
- Companion eligibility is derived from that state rather than from client heuristics.
- The initial policy is intentionally narrow:
  - `upcoming` and `active` trips are eligible
  - `past` and `unscheduled` trips are not

### Companion events and duplicate suppression
- The first companion event model is a thin backend-owned layer on top of existing current-trip summary deltas rather than a separate change-detection subsystem.
- Current-trip summary remains the canonical comparison surface; companion events are recorded only from meaningful eligible deltas.
- The first event scope is intentionally narrow and deterministic:
  - snow-confidence changes
  - disruption-status changes through the compatibility field `availability_status`
  - relevant refreshed conditions during an eligible trip window
- Events are deduplicated with deterministic signatures so repeated equivalent refreshes do not produce endless identical history rows.
- This gives mobile an in-app notification/history surface now and keeps APNs/FCM delivery optional for later.

### Device registration boundary
- Device registration is now a backend-owned authenticated concept tied to a user rather than a client-only concern.
- Current scope is push-ready persistence only:
  - installation id
  - platform
  - optional push token
  - push-enabled flag
- Provider delivery is still deferred. The backend needs to own notification targets before APNs/FCM integration is worth adding.

### Place-model convention
- The product models places and access as independent typed entities:
  - `SkiRegion` is the ranked trip-market grouping and user-facing umbrella;
  - `StayDestination` is a complete, independently owned accommodation market
    with material destination-level separation value;
  - `StayBase` is a concrete accommodation town, village, or district;
  - `SkiArea` is the independently weathered and operated terrain unit;
  - `SkiAreaAccess` is a reviewed base-to-area relationship.
- A stay destination does not own a ski area. Shared branding, pass validity,
  and physical connectivity do not create access edges automatically.
- A named village becomes a separate stay destination only when it passes all
  three ADR 0018 gates: complete stay-market scope, independent stay-market
  ownership, and material destination-level separation value. Otherwise it is
  normally a stay base. Direct lift access is modeled on `SkiAreaAccess`, not as
  a destination-identity shortcut.
- Stay-destination and stay-base names should use recognizable, searchable real
  place labels. Avoid helper suffixes such as `Dorf`, `Centre`, or `Zentrum`
  unless the full label is itself what travelers use.
- Rental names currently represent one real rental option in the destination, not an exhaustive shop list or a canonical best-shop recommendation. Multiple rentals can be modeled later.
- `min_price` and `max_price` filter nightly stay-base budget estimates in EUR. Rental price is a separate display fact and no longer participates in budget filtering as a fake package price.
- Search ranks concrete destination/base/area/pass combinations and then groups
  them by ski region. This keeps several viable configurations inside one market
  card instead of letting one valley occupy several global result slots.
- Conditions, archive history, and climatology always remain keyed by the focus
  `ski_area_id`; region, destination, domain, and pass aggregates are context,
  not synthetic weather keys.

## Integrations

### Conditions model
- Ski conditions are represented as lightweight normalized signals rather than raw provider-style data.
- Current public condition-related fields include:
  - `conditions_score`
  - `snow_confidence_score`
  - `snow_confidence_label`
  - `availability_status`
- Runtime condition reads now come from the Postgres persistence layer.
- New databases bootstrap curated resorts only; condition rows appear after the internal Open-Meteo refresh command runs.

### Why one snow-confidence signal
- A single combined snow-confidence signal was chosen instead of splitting snow quality and depth confidence.
- Reason: simpler model, easier ranking semantics, and enough fidelity for the current stage.

### Availability behavior
- `availability_status` remains the compatibility field name, but current Open-Meteo-backed values are weather-derived disruption/conditions signals, not official lift-operation status.
- The categorical values currently mean:
  - `open`
    - low weather disruption risk
  - `limited`
    - some weather disruption risk
  - `temporarily_closed`
    - high weather disruption risk
  - `out_of_season`
- `out_of_season` is excluded from results.
- `temporarily_closed` is still returned but penalized, because high weather disruption risk should not automatically hide potentially strong resorts.
- `reported` provenance remains reserved for a future official resort/lift/status provider; the current Open-Meteo flow must not present weather-derived values as official operations.

### Real-data refresh flow
- `/search` reads cached condition rows from Postgres and never fetches provider data inline.
- A separate internal refresh command fetches Open-Meteo data, normalizes it, and upserts condition rows.
- Freshness is currently 24 hours.
- If refresh fails, stale cached rows remain usable; generic fallback is only used when no conditions row exists at all.
- The refresh command supports a forced recomputation mode and exact resort targeting for operator workflows such as re-normalizing cached rows after logic changes.

### Conditions output consistency
- The user-facing weather summary should derive from the same normalized snow-confidence signal as `snow_confidence_label`.
- Explanation framing should follow the same rule: strong snow can appear as a positive fit signal, fair snow should be treated conservatively, and poor snow should be expressed as a risk or negative confidence contributor.
- This keeps summary text, explanation groups, and confidence reasoning aligned without changing the ranking model.

### Trust and provenance
- `/search` exposes source-aware factor provenance, evidence caps, and warnings;
  current conditions remain a separate companion concern.
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
- Catalog trust now has an explicit manifest at `app/data/resort_trust_manifest.json`. Critical field groups use `verified`, `verified_with_adjustment`, `estimated`, or `needs_source` so later product work can distinguish curated facts from assumptions.
- The canonical loader validates `app/data/catalog.json` as one normalized graph;
  it never creates silent ski areas or access relationships.
- `verified` and `verified_with_adjustment` catalog trust statuses require source
  references beyond `app/data/catalog.json`; the edited artifact is not evidence
  for its own correctness.
- Validate catalog changes with `python -m app.data.validate_catalog` against the
  catalog and trust manifest.

### Target-date forecast evidence and Search V4 snow fit

- The current `resort_conditions` record is the latest one-day conditions
  snapshot. It remains useful for current display but is not a forecast for a
  requested future trip date.
- Search V4 composes climatological snow reliability with target-date forecast
  evidence per requested ski day. Maximum forecast shares fall from 80% at
  `0–5` days to 60%, 40%, 15%, and finally zero beyond 30 days; coverage,
  freshness, and completeness determine whether a forecast row is usable.
- The initial gateway is Open-Meteo's Ensemble Mean API. ECMWF IFS 0.25 degree
  ensemble mean is preferred through lead day 15; NOAA GEFS 0.5 degree ensemble
  mean provides days 16 through 30 and shorter-range gap fallback. Planning
  selects one source per date rather than averaging models.
- Open-Meteo exposes model initialization and availability through a separate
  metadata surface. A versioned acquisition records both, waits through the
  documented consistency window, and rejects a batch if the model cycle changes
  during fetch; retrieval time is not treated as model issue time.
- Daily snow depth is the instantaneous 12:00 local value. Snowfall and rain are
  summed over a complete local day; temperature, freezing level, and wind use
  named extrema/means. Required variables are source-specific because ECMWF and
  GEFS do not expose every optional field identically.
- Forecast acquisition and scoring initially use the representative `mid`
  elevation only. The stored elevation band keeps later base/upper expansion
  possible without changing the evidence boundary.
- Long-range GEFS values remain daily storage rows for exact-date lookup, but
  its coarse grid and long lead do not imply daily precision. The 17–30-day
  forecast share remains capped at 15%, with 85% climatology.
- Forecast evidence uses immutable provider/model issue runs and atomic
  per-ski-area latest-run heads. Search reads candidate areas and dates in one
  indexed Postgres query and never calls a weather provider.
- Postgres is the initial serving source. A cache is justified only by measured
  search latency and must remain an optimization over the head contract.
- Retained issue versions support later forecast-versus-observation calibration.
  That calibration is a follow-up refinement rather than an initial activation
  gate. Forecast rows never become observations or climatology.
- Forecast retention keeps every complete run for 45 days, a preferred `00Z`
  complete run per source/day through two years, and one complete run per
  source/week through five years. The earliest complete daily run is the
  fallback when `00Z` is missing; current head-referenced runs are never purged.
- Modeled snow depth at representative elevations is distinct from skiable
  snow coverage, open-piste kilometers, and open lifts.
- The depth-led snowpack-outlook utility is a transparent ranking policy over
  forecast-model output, not a physical snowpack simulator. SNOW-17 and
  Crocus-Resort support the selected driver families, but their coupled and
  locally calibrated physics do not provide universal ranking weights. The
  provider's snow-depth state is primary; snowfall and rain/thaw are bounded
  surface-condition modifiers, with policy curves anchored by ski-reliability
  research and validated through named scenarios.
- Historical reliability is calculated from median snow depth, the probability
  of reaching 30 cm and 50 cm, and one maximum-composed rain/freeze-thaw risk.
  Historical snowfall and average maximum temperature remain explanation data;
  fresh-snow likelihood belongs to a separate future powder preference.
- Snow assessment and forecast applicability are separate backend-owned states.
  In particular, `not_yet_available` beyond the forecast horizon is neutral
  context and cannot be promoted to a customer-facing snow concern by React.
- Canonical decisions live in `docs/search-ranking-model.md`, the trip-window
  forecast evidence spec, and ADR 0013.

### Sprint 17 planning calibration
- Sprint 17 separates source-backed resort-fact correction from heuristic retuning.
- Resort provenance for the audit lives in documentation, not in the resort data schema:
  - one reusable audit template
  - one completed audit results doc
- The current product problem is not only sparse history; it is sparse history combined with a
  permissive late-season heuristic that lets summit elevation overstate edge-month viability.
- The selected fix for Sprint 17 is still deterministic and policy-driven:
  - factual resort metadata is corrected first
  - sparse-evidence penalties are then applied more aggressively
  - late-spring closing months receive additional caution, especially for lower-base resorts
- This avoids adding a new resort-schema field such as `glacier_served` before the data audit proves
  that a new explicit dimension is actually needed.

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
  - trip-brief-first search surface
  - applied filter chips plus a secondary refine panel
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

### Brief-first search over visible structured state
- The main product flow remains structured search, but the web UX is now brief-first.
- A changed trip brief is parsed automatically when the user searches; inferred filters are merged into the visible structured state before `/api/search` runs.
- Applied filters are rendered as removable chips derived from current state, not from the raw parser response.
- Parsed trip context is cached with the search state, and high-impact ambiguities can appear as small clarification cards under the brief.
- Answering a clarification updates local trip context and any safe filter projection, but unanswered clarifications do not block search.
- Manual editing stays available in `Refine filters`, so the user can recover from weak parser output without exposing every control by default.
- If parsing fails, the frontend shows the parse error and does not run a stale/default search.
- Travel timing is one user-facing `Travel window` concept:
  - `any` sends no timing filter
  - `month` sends only `travel_month`
  - `dates` sends only `trip_start_date` and `trip_end_date`
- Exact dates take precedence over month-level planning when both are inferred; the frontend and parser both normalize toward dates only in that case.

### Search request performance
- `/api/search` keeps the public request and response model stable, but the backend treats one request as a single planning evaluation unit.
- Raw weather history is loaded once per candidate ski-area set and reused across matching stay bases, instead of being fetched inside every stay-base option loop.
- Ski-area planning context is computed once per ski area per request, then reused across stay-base and rental alternatives.
- Planning snapshot history is loaded only when raw weather evidence is unavailable for that ski area; raw-backed ski areas do not pay for unused snapshot queries.
- Static catalog reads are cached in-process because catalog changes are deploy/review-time events. Current condition lists use a short in-process TTL, so separate refresh jobs can update ranking inputs without requiring a web-process restart.
- The existing full-history raw weather repository method remains available for backfills and maintenance jobs.
- While travel effort uses the deterministic approximate car model, default search computes routes in memory and avoids persistent travel-cache reads/writes on the hot path. Provider-backed routing can reintroduce persistent route caching through explicit dependency injection.
- Connection pooling is deferred until query-count reductions are measured; reducing remote round trips is the first performance lever.

### Routeable app routes vs public stay-destination pages
- The React app has lightweight client-side routes for `/`,
  `/recommendations/:skiRegionId`, and `/current-trip` without adding a routing
  dependency. Navigation uses the browser History API while the active search,
  selected alternatives, expansions, dossier navigator state, and return scroll
  position remain in the in-memory React search session.
- A recommendation route is an app-state route, not a public SEO page. It uses
  the latest search context because detail includes the selected configuration,
  alternatives, travel window, ranking evidence, and parser-derived filters.
- Dossier routes are intentionally not reloadable or transferable yet. A reload,
  direct navigation, or new tab has no in-memory ranked search context and shows
  the explicit "Run a search first" recovery state instead of reconstructing or
  inventing a recommendation.
- Public, crawler-friendly stay-destination pages use
  `/ski-destinations/{stay_destination_id}`.
- FastAPI registers destination pages, `/sitemap.xml`, and `/robots.txt` before
  the SPA catch-all so crawlers receive complete backend-rendered responses.
- Public pages are deterministic and data-backed. Each page lists explicitly
  accessible ski areas and labels any conditions under the corresponding area;
  it does not synthesize destination weather or use LLM-generated copy.
- Public calendars are evergreen. Month cards use archive weather history and
  seasonal area traits only; current forecast remains a separate signal.
- Historical weather metrics are derived from `raw_weather_history` archive rows and remain nullable when archive data is missing. The main display metric is average snow depth in centimeters because the stored source field is `snow_depth_m`, not percentage terrain snow coverage.
- Raw weather history is elevation-banded. Each ski area/day/source can store `base`, `mid`, and `upper` observations with the requested Open-Meteo elevation. Public/search planning metrics use the `mid` band by default because summit/upper snow-depth responses can produce unrealistic user-facing "typical snow" values for normal trip planning.
- Raw weather observations store extra weather evidence for later quality modeling: precipitation total, rain total, precipitation hours, snowfall water equivalent, apparent temperature, cloud cover, sunshine duration, and forecast-only visibility when available. These fields are storage inputs only until a dedicated scoring policy uses them.
- Existing unbanded rows are treated as `upper` during migration. A full `backfill_historical_weather --rebuild` run is required after deployment so mid-band archive rows exist for default planning metrics.
- The optional `planning_weather_metrics` object is display/provenance enrichment for search results and public pages. It does not change ranking weights, scoring formulas, or search request parameters.
- `/sitemap.xml` is generated from active stay destinations in
  `CatalogRepository`, so canonical catalog sync controls public page URLs.

### Trip-market groups and normalized access
- Search ranks concrete `TripConfiguration` values and groups them by
  trip-market `ski_region_id`.
- Every configuration names a stay destination/base, focus ski area, explicit
  access edge, and selected pass. Alternatives remain inside the same market.
- Stay destinations do not own ski areas. Shared branding, connectivity, or pass
  validity never creates implicit access; only reviewed `SkiAreaAccess` edges do.
- Weather and climatology remain attached to each selected `ski_area_id`, even
  when several configurations appear in one recommendation group.

### Target web UI route boundaries
- The React web app remains the anonymous planning and demo surface, not the authenticated mobile companion.
- `lucide-react` is the presentation icon system for the web experience. Icons
  inside labeled controls are decorative; icon-only controls carry an
  accessible name and tooltip. Domain charts remain semantic application UI,
  not Lucide illustrations.
- Search should open as an editorial command surface, then collapse into a compact command bar after results exist.
- Manual filter editing belongs in a refine drawer; the primary post-search workspace belongs to recommendation comparison, evidence, and tradeoffs.
- The post-search decision rail is the place for parsed context, active chips, assumptions, evidence mode, travel effort, and "why this leads" context. This keeps the result board readable while still making the ranking inputs auditable.
- `/recommendations/:skiRegionId` remains a search-context recommendation
  dossier. Public stay-destination content remains backend-rendered under
  `/ski-destinations/{stay_destination_id}`.
- The shared visual system uses midnight blue for trust, creamy alpenglow pink for brand atmosphere and date/window emphasis, alpine blue for evidence/data, and green/amber/orange for semantic status. Pink must not be the only risk indicator.
- Abstract alpine imagery can support brand atmosphere, but specific resort imagery must be real, licensed/source-safe, or omitted.
- Result cards and dossiers should show trip market context followed by the
  concrete stay destination/base, selected ski area, access, and pass.
- The ranked object is a trip configuration, not a standalone resort.
- The selected stay base belongs in the result-card headline and near the top of the dossier. Alternative stay bases should remain nested, clickable choices inside the configuration rather than duplicate global results.
- Hotels and apartments are a nested lodging layer under the selected stay base. They should not become global search result cards, because that would turn Snowcast into a generic accommodation marketplace and create duplicate resort spam.
- Accommodation-option UI requires provider/freshness evidence. Without provider-backed lodging data, show a stay-base estimate and booking handoff rather than property cards.
- User-facing percentages should be labeled `Trip fit` or `Match score`, not primary `Confidence`. Explanation and evidence quality should carry trust before the score does.
- Trust language should use one evidence-quality framework: Archive-backed, Forecast-assisted, and Fallback-heavy. Use `Snow reliability` for archive-backed/history views and `Snow outlook` for current/forecast views.

### On-demand dossier weather evidence

- Detailed historical and target-date weather profiles belong to the selected
  recommendation dossier, not to every configuration in the grouped Search V4
  response. The full-catalog response duplicated ski-area profiles and exceeded
  the accepted payload and construction guardrails without changing ranking.
- `POST /api/search/weather-evidence` accepts the applied typed intent and one
  canonical ski-area ID. It reuses Search V4's stored climatology and latest
  complete forecast-head policy, but it does not rerun ranking, call a provider,
  or invoke an LLM.
- Refinement impact previews and weather interpretation/provenance summaries
  are server-owned typed presentation contracts. The browser renders those
  summaries and never derives rank movement from scores or parses raw factor
  values to create weather claims.
- The dossier caches available and typed unavailable responses only for the
  current browser session by travel window and ski area and only until the
  server-declared validity time. Forecast-assisted validity follows the earliest
  selected run expiry; responses without usable forecast evidence revalidate
  after five minutes. Transport failures remain retryable. Evidence loaded
  later may be fresher than the original ranking request, so issue times and
  provenance stay visible.
- Snow charts use bounded semantic inline SVG with labeled chart roles and an
  equivalent expandable structured-value table. The visual trend is therefore
  not the only way to access the underlying dates, depth, snowfall,
  temperature, and risk values.
- The representative maximum-shape one-area route measured 32,809 serialized
  bytes and 7.273 ms warm-domain p95 construction time. This remains the
  reference measurement for the accepted on-demand boundary.
- ADR 0014 owns this API and request-path boundary.

### Direct Gemini API vs LangChain / LangGraph
- Direct Gemini API behind a small local `LLMClient` seam is the current choice
  because the LLM workflow is narrow query parsing.
- This keeps the control flow explicit and avoids introducing a framework before retrieval, tool-calling, or multi-step orchestration is needed.
- LangChain is still unnecessary for the current planner/ranker core.
- LangGraph becomes more plausible later if the product grows into stateful companion workflows such as:
  - trip-companion chat grounded in trip context, live conditions, and reported lift/status data if that provider layer exists
  - plan-B / contingency assistance when conditions deteriorate
  - multi-step operational guidance around a booked trip
- If introduced later, it should sit in companion-style orchestration flows
  rather than in deterministic ranking, conditions scoring, or query parsing.

### Local provider seam
- Query-parser helpers depend on a local `LLMClient` interface rather than on
  provider-specific request shapes.
- This keeps the application code decoupled from Gemini wire format while avoiding the abstraction overhead of LangChain or LangGraph before they are actually justified.
- The current concrete implementation is Gemini-only, with `gemini-3.1-flash-lite-preview` as the default model.

### Dynamic filter surfacing and user-stated priorities

Search V4 maintains a registered pool of resort, ski-area, pass, access, and
character factors. The UI exposes a small useful subset directly; the optional
LLM can propose other registry-backed clarification topics dynamically. It
cannot invent filters or numeric weights, and deterministic impact simulation
removes questions whose answers would not materially affect the current result
set.

The same pattern can later support accommodation attributes such as board type,
wellness, parking, or pet policy, but this remains a data problem first. A new
filter is useful only after its typed fact, ownership, source policy, missing
semantics, evaluator, and coverage are credible. Adding a visible control over
empty or unreliable data is worse than leaving the factor planned.

### Search V4 ranking-policy hierarchy

- The active default group budgets are Trip Viability 30, Ski Experience 30,
  Stay Practicality 15, Value 10, Character 10, and Travel Effort 5.
- Group importance multiplies a default group budget before active groups are
  normalized. Factor importance only redistributes weight inside that group.
- Travel Effort can reach at most 30% at `very_high`; excess caused by inactive
  groups is redistributed. Literal nearest-first or cheapest-first behavior is
  a primary-sort objective instead of an unbounded weight.
- Maximum travel time, known out-of-season dates, and sufficiently trusted
  must-have features are pre-score constraints.
- Party ability and terrain preference are independent. Advanced ability does
  not imply freeride.
- Search V4 uses factor-shaped evidence readiness. Broad coverage gates remain
  appropriate for always-on and comparative factors, while verified sparse
  features such as glacier terrain, parks, night skiing, marked freeride,
  snowmaking availability, and apres can reward explicit preferences with
  unknown held at neutral `0.50`. Catalog silence is never treated as absence.
- Lodging-budget fit remains measured with zero ranking weight while its price
  inputs are fully estimated. An explicit budget remains an estimate-aware
  constraint with at least 10% uncertainty flexibility and no cheaper-is-better
  ranking bonus. Snowmaking availability is preference-only and modifies the
  target-date snow factor solely through the reviewed `0.30–0.75`, maximum
  `0.25` conditional-resilience composition.
- The exact equation, importance multipliers, initial factor weights, and
  forecast composition live in `docs/search-ranking-model.md`; do not duplicate
  tunable values in evaluator code or LLM prompts.

### Near-term product direction
- The active product wedge is still trust-first ski planning: helping users decide where and when to ski with higher confidence.
- The roadmap source of truth is `PROJECT.md`; this file captures durable architecture and tradeoffs rather than sprint sequencing.
- The current near-term direction is to use public stay-destination pages as the
  first organic growth/demo content layer, then decide whether country/month
  collection pages, richer catalog facts, or web-auth continuity are the next
  highest-leverage step.
- Web remains the main public planning surface; mobile remains the authenticated companion surface.

### Operational direction for the next phase
- OpenTelemetry should be the application instrumentation standard. Fly.io built-in metrics/logs remain the infrastructure baseline, but Snowcast-specific behavior needs request traces, structured logs, and low-cardinality metrics around search, parser/LLM use, provider calls, and freshness.
- The first observability slice should prioritize user-facing runtime paths, especially `/api/search`, `/api/parse-query`, conditions freshness, and LLM fallback behavior.
- Heavy platform work should remain subordinate to product learning at this stage: use a hosted OTel-compatible backend rather than operating a self-hosted telemetry stack.
- Event sourcing is out of scope for the near-term architecture; historical/time-aware conditions data is the right complexity step instead.
- Runtime telemetry should stay behind narrow helper modules under `app/observability/`. Domain code may record bounded events such as search phases, parser modes, LLM status, retry reasons, and freshness age, but must not put raw trip briefs, exact origins, prompts, raw model responses, URLs, or resort names into metric labels. Request-specific details belong in traces/logs only after sanitization.
- Grafana dashboards are operational config and should be repo-owned under
  `ops/grafana/`. UI edits are acceptable for exploration, but durable changes
  should be exported, normalized, validated, committed, and deployed from the
  repo. The first deployment mechanism is a small Python script against
  Grafana's dashboard API; dashboard files and manifest metadata stay
  Terraform-friendly for a later provider migration.
- Grafana alert rules, the `Snowcast Alerts` folder, and the initial owner
  email contact point are also repo-owned under `ops/grafana/alerting/`.
  Notification-policy routing is intentionally left as a manual Grafana UI step
  for now. Grafana's policy API replaces the whole routing tree, so Snowcast
  should only automate policies once the full alerting tree is captured in
  Terraform or another explicit policy manifest.
- Product canaries should exercise production like a user without using real
  user inputs. The current canary checks health, readiness, search-readiness,
  and one deterministic representative search from GitHub Actions, then lets
  Grafana alerts handle sustained runtime symptoms from low-cardinality metrics.
- Data-quality observability should use a summary-metric plus artifact-detail
  model. Grafana receives bounded labels such as domain, field group, status,
  elevation band, source model, baseline period, `entity_type`, `entity_id`,
  and `ski_area_id` where weather evidence is involved. The production
  dashboard should stay summary-oriented, while the separate `Snowcast Data
  Quality` dashboard can show bounded entity and ski-area drilldowns.
  Source URLs, raw issue text, date-level missing windows, and detailed evidence
  remain in audit JSON/Markdown artifacts so metrics stay cheap, safe, and
  queryable.

### Testing direction for the next phase
- Unit and integration tests remain the primary safety net for deterministic backend logic.
- The app has now reached enough cross-layer complexity that a small browser/E2E layer is justified for demo-critical journeys.
- That E2E layer should stay narrow and product-led:
  - trip brief -> auto-parse -> chips -> search
  - structured search -> select result -> book accommodation
  - travel-window planning flow
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
- This section describes the current production baseline. The accepted Search
  V4 target uses requested-date forecast runs rather than treating the latest
  snapshot as near-term forecast evidence.

### Browser smoke coverage
- A small Playwright layer now protects the critical demo journeys that span browser, API, and app-serving boundaries.
- The scope stays intentionally narrow:
  - trip brief -> auto-parse -> chips -> search
  - month-aware search -> planning output -> booking CTA
- Vitest remains the primary frontend/unit layer; Playwright is only a smoke/regression layer for the highest-value user flows.

### Version-keyed LLM cache
- Query-parser cache entries are keyed by exact input plus model and
  prompt/schema version identifiers.
- There is no TTL in the first version.
- Cache invalidation happens naturally when the implementation version changes, not when time passes.
- Parser prompt versions should be bumped when normalization changes can alter user-visible parse output, so stale cached rows do not keep showing old interpretation warnings.

### Local `.env` loading
- The repo uses a small internal `.env` loader instead of adding a dotenv dependency.
- `.env` is loaded lazily when the Gemini client is instantiated.
- Values from the real shell environment still win; `.env` only fills missing variables.

### No backward compatibility for evolving internal product API
- This is a private, still-evolving project.
- When the contract improved, old explanation fields were removed instead of preserved.
- This keeps the API cleaner while the product is still being shaped.

### Why raw SQL instead of an ORM
- The backend is still sync and the schema is small.
- The main learning goal is repository separation, not ORM depth.
- Swappability later comes from the repository boundary, not from introducing more abstraction early.

### Postgres as the default runtime database
- Postgres is now the default database in local/dev and production.
- `DATABASE_URL` is the canonical runtime input.
- Docker Compose is the default local setup; Neon is the external managed Postgres provider for hosted deployment.
- The Postgres cutover is bootstrap-only:
  - create schema if needed
  - sync canonical resort seed data
  - rebuild refreshable runtime data through the refresh command
  - do not migrate the old SQLite file
- Schema creation and seed sync now run as an explicit bootstrap command:
  - local/dev can run `python -m app.data.bootstrap_database`
  - Fly production runs the same command as a release step before web startup
- The FastAPI app and repositories no longer bootstrap the database implicitly on request-serving startup paths.

### Why conditions are refreshed by command instead of API
- Conditions refresh is an operational concern, not a user-facing product action.
- Keeping it out of FastAPI avoids exposing admin/update behavior through the public API too early.
- It also keeps `/search` latency predictable because provider calls are not made during request handling.
- Periodic refresh is currently handled by GitHub Actions on a schedule rather than by a resident Fly worker.
- This keeps the scheduler host-agnostic while the product is still small; it is a portable intermediate ops model, not a permanent worker architecture.

### Background work vocabulary
- Use Worker / Function / Trigger as Snowcast's internal documentation vocabulary
  for async, scheduled, or operator-started work once background jobs grow.
- **Trigger** means the event that starts work: a schedule, `workflow_dispatch`,
  stale-data threshold, user-created trip watch, deploy hook, or operator
  command.
- **Function** means the bounded unit of work: refresh conditions, backfill
  historical weather, evaluate trip-watch alerts, reconcile acquisition
  artifacts, or send a notification.
- **Worker** means the runtime that executes functions: a GitHub Actions runner,
  local operator command, Fly machine, queue consumer, or future background
  service.
- Current examples:
  - scheduled GitHub Actions trigger -> conditions refresh function -> GitHub
    Actions runner
  - operator command trigger -> historical weather backfill function -> local or
    GitHub Actions runner
  - future trip-watch trigger -> alert evaluation function -> future
    notification worker
- This is docs vocabulary first. Do not add code-level worker/function/trigger
  abstractions until there are enough repeated jobs to justify orchestration,
  retries, ownership boundaries, or shared observability.

### Local maintainer workers

Snowcast's local catalog maintainer uses Codex App for scheduling and
semantic work, the repository helper for objective safety, and GitHub for
durable branch and workflow visibility.

The shared `snowcast-catalog-curation` skill has two explicit invocation modes.
Standalone mode owns its normal branch and draft-PR workflow. Under the local
maintainer, `maintainer-managed` mode accepts the helper-verified isolated
worktree but supplies only research, catalog/trust/report edits, and
reconciliation; the parent maintainer retains lease, branch, commit, validation,
and publication authority. This avoids weakening worktree isolation or giving a
sub-skill a second GitHub mutation path.

The helper exposes four capability groups: inspect, prepare, validate, and
publish. `ops/maintainer/cli.py` is only the JSON parser and dependency
composition boundary; `ops/maintainer/capabilities.py` dispatches the explicit
capabilities to the runtime, inspection, git, validation, publication, state,
and GitHub modules. It does not select the oldest PR, interpret backlog prose,
rank discovery candidates, or maintain a runtime coverage registry.

After owner-controlled activation, normal scheduled cycles use the concise,
parser-tested
`docs/operating-model/maintainer-runtime-command-contract.md` for exact helper
argv, critical sequence prefixes, and dispatch-error classification. The long
design spec remains rationale and workflow-change authority rather than
per-cycle command input. This keeps semantic orchestration in Codex without
making command spelling an inference problem; a dispatch-stage
`invalid-command` is treated as an orchestration-contract defect, not as a
finding against the selected PR. A completed structured dispatch rejection may
receive one corrected attempt of the same named registry recipe after the exact
contract is reloaded, provided the structured outcome also reports no mutation.
The malformed argv is never repeated, and uncertainty, missing or positive
mutation status, recipe ambiguity, capability switching, a non-dispatch error,
or a second dispatch rejection still stops the cycle.

Incoming curation reports are review input, not preparation authority.
Preparation validates the resulting diff rather than freezing the incoming
blob IDs, path set, or catalog targets. Catalog data, non-control-plane
documentation, and tests may change during remediation; production code,
operational code, the maintainer's own instructions, unsafe file modes, and
empty diffs fail closed. Before the initial dual review, a legacy, malformed,
graph-less refreshed, incomplete, or non-reconciling report receives one
`maintainer-managed` structural normalization pass. It reads the exact prepared
base/current catalog and trust snapshots, rebuilds and locally commits the
single schema-v3 report, then yields to review without claiming semantic
resolution or consuming a remediation cycle. It validates those snapshots
before edits, stops without edits when catalog/trust validation fails, asserts
the catalog/trust object IDs remain identical, and permits only the report path
in its local commit. Catalog/trust semantic changes begin only after the
dual-review ledger and consume a normal remediation cycle. Normalization and
remediation run catalog validation, exact reconciliation, and finding-related
focused tests; the fixed broad catalog suite remains final helper-validation
work.
Validation-backed push and readiness still require one canonical schema-v3
report reconciled to the exact reviewed catalog and trust changes.

Ski-area-access catalog `source_urls` are the entity-level union of the trust
manifest's independent `relationship` and `access_mode_distance` source refs.
Each group keeps its own source sufficiency rules; the catalog roll-up may not
contain an unowned URL, and a group may not cite a URL absent from that roll-up.

One owner record serializes mutation across curation and discovery. Every
mutation is bound to its worker and run ID. Inspection is truly read-only.
Curation holds the lease across prepare, review/fix, validation, push, and
publication. Discovery performs backlog interpretation and external research
before acquisition, then re-inspects and holds the shorter mutation-window
lease through catalog changes and proposal publication. While held, the
orchestration skill heartbeats before and after capabilities and at least every
five minutes. A lease becomes stale after one hour without a heartbeat. This
leaves twelve missed heartbeat intervals before a fenced successor takeover,
while allowing an interrupted Codex task to stop blocking later scheduled runs
within the same day.

A structured `lock-busy` acquisition result is an expected concurrency no-op,
not a malformed helper response or capability failure. The losing worker never
inspects the active owner's record, retries around the lease, or releases a lock
it did not acquire. If discovery had already selected a sourceable candidate,
its bounded identity/source hint becomes preferred retry in automation memory;
the next run revalidates it before considering backlog or new research.

Catalog discovery is backlog-first. Catalog Curation Refinements uses explicit
candidate items with one next bounded slice and retains truly dependency-blocked
work as parked. Merged proposals consume or advance their originating slice;
external research runs only when no known slice can progress. This remains
semantic Codex policy rather than a deterministic Markdown parser or registry.

Existing-model boundary, stable-ID, and weather-owner changes may be published
as decision-bearing discovery proposals. They include the intended catalog
state plus historical-data impact, preserve/migrate/backfill decision, manual
commands when exceptional intervention is needed, merge order, rollback, and
the policy-adjudication result. A policy-determined graph proceeds through the
normal fix and fresh-review cycle; only two policy-compliant alternatives
justify an unresolved owner decision. The proposal label and later curation
review keep incomplete migration handling from readiness. Actual database
migration execution, catalog-schema changes, production code, and production
weather jobs remain outside the catalog proposal helper and require separate
work.
The proposal validator keeps deletion safety narrow: an old catalog key may be
removed only when the proposal adds its same-kind replacement candidate, fully
reviews the old target, declares the identity deletion, records that target as
an unresolved scoped decision with a backlog reference, and carries an explicit
unresolved caveat. Other entity-kind removals still fail closed.

One work record stores the ordinary phase progression; a separate push journal
stores only irreversible-operation recovery facts. Unresolved journals take
priority over fresh work. Exactly one journal restricts acquisition to its
worker and can be adopted by a successor; multiple journals fail closed. The
journal check and stale takeover share one transition mutex, preventing a
journal from appearing between eligibility check and acquisition. Completed
journals can be replaced by a new authorized journal for a later review/fix
cycle on the same PR. A discovery journal also stores the validated report path
and immutable canonical graph. This lets journal-only recovery enforce the same
publication input as the original run; historical or incomplete journals
without that evidence stop rather than publishing a caller-supplied graph.

A third owner-private record preserves reviewed-but-unpushed curation work.
`validate reviewed` binds one exact local reviewed commit to the unchanged
remote PR head, guarded-sync lineage, single report, a persistent reviewed ref,
and a helper-created one-commit squash ref. A successor on the same base reruns
only missing deterministic gates. If `main` advanced, the helper replays that
single delta and requires one fresh full independent review; one conflict set
may be resolved only within the helper-returned curation scope before the
helper completes and revalidates the replay. Interrupted conflict worktrees are
never trusted by a successor, which recreates the attempt from immutable refs.
The continuation remains local authority only until push authorization; the
push journal then becomes the sole recovery authority and the continuation is
terminalized.

Normal curation push remains validation-gated. The narrow exception is
`publish manual-check`: after an unresolved bounded review, it revalidates the
scope-safe local reviewed head, journals and exact-lease pushes that head, and
publishes the pause. The work and canonical machine evidence remain
`reviewed` with no validated head. If publication fails after push, the pushed
journal blocks fresh work until a successor run adopts it and completes the
same idempotent handoff.

Curation recovery exposes its evidence level instead of making Codex probe
lifecycle gates. The helper returns the exact reviewed head plus validation
status: `validated`, `absent`, or `unknown`. Validated recovery may follow
current CI facts toward waiting-CI or ready. Reviewed-only recovery cannot be
validated after the fact or represented as ready; it completes an honest
manual-check or owner-decision state. Unknown evidence stops without guessing.
After an exact push, GitHub's PR API may briefly lag the Git ref, so publication
allows at most five three-second retries only while Git has the journaled new
head and the API still has the journaled old head. A third head remains an
immediate stale-head stop.

Review/fix convergence begins with two complementary independent reviews of the
same normalized prepared head: source/trust and graph/scope. Source/trust
enumerates every applicable group from the canonical `FIELD_GROUPS` code
registry, recording each group's status, direct refs, normalization-note need,
and coverage disposition. Graph/scope enumerates every concrete operator
presentation and lift-pass candidate; deferred or unresolved pass products
carry typed assessments and canonical backlog refs. Their findings are
consolidated into a private candidate inventory, an assertion-level finding
ledger, and one first fix. The inventory answers which entities, products,
edges, sectors, and documents were inspected. The ledger answers which exact
assertion and acceptance criterion failed; one finding can link several
candidates, and one candidate can acquire a different finding. Each later fresh
full review independently rechecks the complete scope, then reconciles those
untrusted views so resolved, narrower residual, repeated, regressed, and
genuinely new findings remain visible without asking a reviewer to trust prior
conclusions.

A possible destination or ski-area owner choice receives one additional focused
boundary adjudication before escalation. This is not another full review: it
applies the accepted boundary gates to the concrete candidates and returns
`policy_determined`, `owner_choice_required`, or `evidence_insufficient`. A
policy-determined graph goes back through the normal fixer and fresh-review
loop; only multiple defensible product graphs reach the owner. The adjudication
shares the existing cycle clock, starts before minute 180, and never extends the
210-minute semantic or 240-minute hard deadlines. A late boundary question is
preserved as an exact-head follow-up rather than being prematurely labeled an
owner decision.

The adaptive maximum remains six remediation cycles. Before every fix and each
adaptive review, the parent fetches current main and runs a read-only merge-tree
probe; a conflict stops the cycle before more work is accumulated. The first
four cycles remain the normal bound. Convergence is assertion-level, not a
candidate-count percentage. A strictly narrower residual may continue. The
same exact assertion and acceptance criterion may receive two consecutive
repeat retries only when each has a materially different bounded fix strategy;
the third unchanged repeat stops. Regression or unsafe scope expansion still
stops immediately. New semantic work stops at 210 minutes.
At 240 minutes the parent interrupts semantic contexts and enters
finalization-only mode. After
revalidating the exact head, worktree, remote, current-main mergeability, and
review evidence, it may use up to 30 active minutes for helper validation,
publication, recovery, cleanup, and final reporting. Report reconciliation and
validation remain pinned to the prepare-time base even when the merge-tree
probe uses a newer current main. This accommodates sleep and large reports
without allowing an unbounded or stale-base review loop.

When the cycle or semantic-time bound is reached after such legitimate progress,
a mechanically valid and scope-safe reviewed head is preserved through the
helper's `manual-check` publication path. An unresolved finding, active residual
or repeat, regression, incomplete inventory, incomplete review, or unsafe scope
expansion still uses status-only blocked publication because the local head is
not a safe owner handoff.

Long-running helper commands use a completion protocol rather than treating the
first tool response as the result. Codex first resumes any yielded orchestration
cell, then polls the underlying command session through process exit. All chunks
are accumulated, and JSON is parsed only after completion. An exact same-lease
curation-validation retry is additionally
idempotent: the helper revalidates the immutable PR, reviewed head, prepare-time
base, and report path and returns `already-validated` without rerunning tests.
Changed inputs or a later phase still fail closed.

Publication inputs remain owner-private direct children of the maintainer state
directory. Callers pass only basenames, while path-shaped arguments return a
safe `publication-input/not-basename` diagnostic without exposing the rejected
path. Discovery records a bounded preferred-retry hint as soon as one candidate
is source-validated, so lock contention, sleep, or task interruption cannot
silently discard the candidate; the next run must still revalidate it.

Each automation appends one owner-private mode-`0600` bounded diagnostic JSONL
row after cleanup. The row captures selected identity, heads, cycle count, last
stage, helper reason, mutation flag, elapsed time, and recovery obligation, with explicit nulls and
no raw prose or authority-bearing lease data. It supports weekly audits but is
never read as selection, recovery, review, or mutation authority.

Safe PR-specific terminal stops use a separate status-only outcome record in
the existing canonical maintainer comment. Its observed remote head and
allowlisted reason are distinct from reviewed/validated-head evidence. The
helper updates exactly one lifecycle label and the one comment, never the PR
body or branch. An unchanged blocked/owner-decision head remains paused; a new
commit or deliberate label removal makes it eligible again. Lock-busy, stale
head, authentication failure, unknown state, and unsafe capability errors
remain Triage-only because safe GitHub authority is unavailable. Semantic
deadline expiry may still use exact-state bounded finalization.

GitHub state is one lane label, one lifecycle label, an allowlisted managed body
block, and one canonical schema-versioned comment. Codex chooses semantic
states. The helper alone authorizes proposal, waiting-CI, and ready from exact
candidate/head/validation/check facts. A new proposal branch uses atomic
create-only push. Push-before-PR recovery searches exact branch/head across all
PR lifecycle states, so an owner-closed proposal is never recreated.

Discovery duplicate checks separate accepted catalog truth from proposal
output. The proposal validator proves that the candidate is absent from its
immutable base and present in its proposed head. Independently, validation and
each proposal-publication gate fetch immutable current `main` and use that
catalog for the live "already represented" check, while GitHub remains the
authority for open proposal identity. Reading the modified worktree for this
gate would make every valid addition appear to duplicate itself.

For curation readiness, the checked-in schema-v3 report is the complete source
of truth and the PR body is only a concise human synopsis. Both `waiting-ci` and
`ready` require that synopsis. Legacy unmarked bodies are replaced only through
an explicit helper adoption flag on an already-authorized automation-owned PR;
once managed markers exist, updates are idempotent. Recovery must finish the
body publication as well as the label and canonical comment, so a recovered PR
cannot become ready with its original discovery-era description still shown.

Schema-v3 reports may declare `resulting_graph.focus_stay_destination_ids`.
Historical v3 reports remain readable without it, but current maintainer
validation requires it. The renderer derives regions, destinations, stay bases,
access edges, ski areas, terrain domains, and lift-pass coverage from the exact
normalized catalog head and emits one canonical Mermaid section. Validation
also derives every final-catalog destination reached by the report's reviewed
graph targets and requires the focus list to cover them; extra focus destinations
are allowed, but omissions are not. The helper persists the rendered section
with validation and journal evidence and requires the same section in the
managed PR body, preventing report and PR diagrams from drifting apart. The
unvalidated `manual-check` path receives the report path explicitly, verifies
that it is the PR diff's single curation report, and reproduces the graph from
the immutable reviewed head before allowing its push.

An unchanged `ready` head is held out of fresh curation selection and becomes
eligible again only after a new commit. An unchanged `waiting-ci` head remains
visible as compatibility presentation while its exact helper CI continuation
controls same-run or successor waiting, repair, and readiness without rebasing
or repeating semantic review.

After the reviewed and validated head is pushed, the implemented post-push
lifecycle keeps the same curation lease through a 30-minute exact-head CI wait.
Every first-wait and second-wait iteration calls `lock heartbeat curation ->
inspect curation -> lock heartbeat curation` before branching, with heartbeats
at least every five minutes and no same-run reacquisition. A successor
separately enters through `lock acquire curation -> lock heartbeat curation ->
inspect curation -> lock heartbeat curation` before any selected next
capability. Success plus mergeability publishes ready; pending at the limit
retains the continuation; Codex classifies a confirmed failure from bounded
helper facts and, only when needed, read-only untrusted failed-check logs. A
failure caused only by stale assertions in ordinary root-level
`tests/test_*.py` modules may receive one statically prepared and independently
reviewed repair, with at most 60 active minutes for that repair and one final
30-minute CI wait. Codex does not execute target-PR `tests/test_*.py` files
locally. A second CI failure publishes blocked/CI-failure and permits no second
repair.

Heartbeat always returns base field `worker`. Only when the run owns an active
CI continuation does it conditionally add `ci_budget`, containing exactly the
helper-owned cumulative `first_wait_seconds`, `repair_active_seconds`, and
`second_wait_seconds`.

The cumulative post-push budget is 30/60/30. Its separate 120-minute ceiling
does not reopen or extend the semantic 240-minute clock, and no semantic work
starts after the initial push. The helper persists exact CI-continuation
authority, enforces an unchanged non-test tree and one attempt, and journals the
repair push. Helper output and continuation state are authority, while
automation memory and labels are hints and presentation only. GitHub CI remains
the execution boundary for the modified test code; `maintainer:waiting-ci` is
retained only as human-visible compatibility state.

Terminal blocked publication during an active or reviewed repair uses an
owner-private terminal-publication intent before any GitHub mutation. The
intent embeds the exact continuation generation and binds the PR, branch,
current/semantic/repair heads, lease recovery owner, target state/reason,
canonical summary, and machine evidence. It has priority over the push journal,
so the complete recovery order is `terminal publication -> push journal ->
post-push CI continuation -> reviewed continuation -> remediation continuation
-> ordinary PR`. Recovery replays publication idempotently, then blocks the
exact matching continuation and completes the intent. Repair cannot resume
while the intent is unresolved; drift fails closed.

Post-push recovery is phase-aware. A successor resumes both `repair-active` and
`repair-reviewed` through `prepare ci-repair`: the former recreates the exact
worktree and still needs a fresh focused review, while the latter revalidates
the immutable repair checkpoint before publication. Recovery does not reset
the single repair attempt or any cumulative 30/60/30 budget. Every
`prepare ci-repair`, `checkpoint ci-repair`, `publish ci-repair`, and
`invalidate ci-continuation` request rejects any unresolved push journal; only
exact journal recovery may proceed. The helper uses live exact-PR facts to
`invalidate ci-continuation` when a continuation is no longer resumable. On
rollover, replaced terminal `consumed`, `blocked`, and `invalidated`
generations move to an owner-private archive keyed by semantic head. A new
generation is allowed only after a different semantic head is validated and
pushed for the same work, and only that generation starts with zero consumed
budgets.

All publication text is created by the lease-bound `publication-input create`
capability: it consumes bounded UTF-8 from stdin, makes a random mode-`0600`
direct child through the already-validated state-directory descriptor, fsyncs,
rechecks lease ownership, and returns only the basename. Errors and Triage
outcomes do not echo untrusted prose, sources, command output, paths,
environment values, or credentials. `mutation_occurred` describes the current
invocation, including false for idempotent retries.

The maintainer never approves or merges. The repository implementation does not
install the personal skill or schedules. Post-merge installation, review,
enablement, and rollback are owned by
[local-maintainer-activation.md](operating-model/local-maintainer-activation.md);
ADR 0011 and the
[simplified feature spec](superpowers/specs/2026-07-08-local-maintainer-simplification-design.md)
remain the durable design references.

### Historical planning evidence architecture
- Historical weather storage is now split into two layers:
  - `raw_weather_history` stores date-level weather facts such as snowfall, snow depth, temperature, wind, weather code, elevation band, and requested elevation
  - `resort_condition_history` remains as a legacy derived snapshot layer during the transition
- The refresh pipeline still updates the current `resort_conditions` row from the mid-mountain signal, but it stores raw forecast observations for base, mid, and upper bands so future evidence can distinguish valley/base conditions from upper-mountain exposure.
- Historical ingestion has both targeted and scheduled entry points:
  - `python -m app.data.backfill_historical_weather --start-date ... --end-date ...`
    remains the manual repair command
  - the command fetches base, mid, and upper bands for each selected ski area
  - use `--rebuild` after the banded schema migration to delete selected archive rows before refetching trusted banded data
  - `.github/workflows/backfill-historical-weather.yml` is the manual GitHub
    Actions wrapper for that command shape
  - `.github/workflows/complete-historical-weather.yml` is the bounded daily
    controller for the fixed 1991-2025 full-catalog campaign
- Month-aware planning now prefers a derived evidence view over raw daily history:
  - raw rows are grouped into historical month windows per year
  - planning aggregates those windows instead of treating every raw row as a direct evidence unit
  - this keeps date-level history durable while allowing planning granularity to evolve later
- Public planning now supports two inputs:
  - `travel_month` remains as a compatibility fallback
  - exact-date planning can use `trip_start_date` and `trip_end_date` through `/api/search`
- Date-aware planning prefers exact dates when they are present and only falls back to month planning when they are absent.
- Planning provenance remains `estimated` at the top level, but now exposes a more specific evidence profile:
  - `forecast_assisted`
  - `archive_backed`
  - `fallback_heavy`
- Horizon awareness is now explicit:
  - near trip windows can materially borrow current forecast signal
  - farther trip windows remain archive/history- and seasonality-dominant
- Raw planning evidence is now archive-only:
  - `forecast` rows remain useful for current conditions freshness
  - archive-backed planning windows are built only from `archive` rows in `raw_weather_history`
- Search preloads raw planning evidence with window-scoped SQL rather than loading
  all archive rows for every candidate ski area. Month and exact-date searches
  are converted into concrete historical date ranges so Postgres can use the
  `(ski_area_id, elevation_band, record_type, observed_on)` index before Python
  builds `RawWeatherObservation` objects. See
  [`ADR 0002`](architecture/adr/0002-window-scoped-raw-weather-planning-queries.md).
- The canonical human-readable spec for the planning model now lives in:
  - [`docs/planning-model.md`](planning-model.md)
- Keep `engineering-notes.md` for durable architectural summary and tradeoffs, and use `planning-model.md` for the detailed model contract, evidence profiles, and tunable policy overview.

### Recent archive reconciliation
- Recent `forecast` rows are provisional and should not remain the long-term planning truth.
- The product now treats archive reconciliation as a separate operational concern from live refresh:
  - `refresh_conditions` writes fresh `forecast` rows
  - `reconcile_recent_archive` re-fetches a rolling recent archive window and overwrites matching rows through the existing raw weather upsert path
- Reconciliation runs as a separate GitHub Actions workflow rather than being folded into the refresh command.
- The default reconciliation window ends at yesterday in UTC so current-day forecast freshness is preserved while completed days converge to archive truth.
- Daily recent reconciliation does not rebuild climatology. The fixed
  historical completion controller may rebuild one ski area's derived
  climatology only after base, mid, and upper archive coverage is complete for
  `1991-01-01` through `2025-12-31`. Targeted and future-baseline rebuilds remain
  explicit operator actions.
- Large archive backfills should use provider pacing and exponential retry
  backoff. If Open-Meteo returns `429 Too Many Requests`, the backfill aborts
  early so the operator can rerun later without `--rebuild`; completed chunks
  are skipped by archive coverage checks.
- The Open-Meteo client uses a persistent HTTP client for connection reuse
  during archive backfills. Successful-request delays and retry delays are
  jittered by default so large runs do not hit the provider in a fixed rhythm.
- Repeated timeout-like provider failures, including SSL handshake timeouts, are
  treated as provider pressure. After the configured threshold, the backfill
  applies a longer global cooldown before retrying the current chunk.
- Full-catalog completion is a serialized, scheduled GitHub Actions function:
  - raw archive rows are the durable checkpoint; there is no separate queue
  - one run attempts at most its configured number of provider requests,
    including retries
  - complete chunks are skipped without consuming the provider budget
  - `429` and request-budget exhaustion pause work without deleting data
  - a hard provider/data/database failure remains a failed workflow
  - completion, manual backfill, and recent reconciliation share the
    `open-meteo-archive-writes` concurrency group
- Per-ski-area climatology replacement is transactional. The completion
  controller validates the expected 2,196 rows before replacing the current
  `snowcast_empirical_v1` rows for that area.

### Roadmap sequencing source of truth
- Historical sprint sequencing notes should not be treated as active roadmap.
- Use `PROJECT.md` for the product charter and current roadmap snapshot.
- Use `docs/product-backlog.md` for candidate ideas and future work that are not
  active implementation commitments yet.
- Promote backlog items into `docs/superpowers/specs/` and implementation plans
  when they are ready for design review and execution.
- Keep this file focused on durable decisions such as backend/API boundaries, planning evidence policy, auth ownership, and mobile platform scope.

### Developer decision checkpoints
- Non-trivial Snowcast work should preserve owner learning and technical
  ownership before implementation plans lock in a direction.
- Classify non-trivial work as `fast path` or `review-gated` before
  implementation. Use `review-gated` when work affects durable product
  behavior, user trust, data correctness, persistence, shared API contracts,
  request-path performance, production reliability, security/privacy,
  observability, external integrations, or future maintenance patterns.
- If classification is ambiguous, choose `review-gated`; the project prefers
  reviewers being invoked too often rather than too rarely.
- Feature specs can use Developer Decision Checkpoints for material choices that
  deserve review, including:
  - technical choices such as indexes, schema boundaries, API contracts,
    caching, background work, migrations, deploy shape, and observability
  - product/domain choices such as ranking semantics, thresholds, source trust,
    uncertainty display, alert policy, and booking handoff behavior
  - mixed choices where system shape and user behavior are coupled
- Close-to-default technical choices can still be surfaced when they are useful
  learning moments, but related choices should be grouped so normal development
  does not become process-heavy.
- Superpowers plans and subagent execution should proceed only after owner
  checkpoints are resolved or explicitly accepted as assumptions.

### Mobile auth and current-trip ownership
- Sprint 21 moved current-trip persistence from a global singleton concept to one current trip per authenticated user.
- The backend owns both user identity and app session tokens:
  - Google sign-in supplies the upstream identity token
  - the backend verifies that token
  - the backend then issues its own bearer token for app API calls
- This keeps provider identity separate from app identity and gives the backend a stable place to hang current trip, later device tokens, and future subscription/account state.
- Search and query parsing remain anonymous so the web prototype can continue working as a demo/planning surface.
- Current-trip APIs are now authenticated and should be treated as mobile-first in this phase; the anonymous web frontend is intentionally maintenance-only rather than a full authenticated client.

### Flutter platform scope in this repo
- The Flutter app is being used as a mobile companion client, not as a universal multi-platform shell.
- Keep Flutter platform support limited to:
  - `ios/`
  - `android/`
- The generated Flutter `macos/`, `linux/`, `windows/`, and Flutter `web/` directories were intentionally removed because:
  - the project already has a separate React web frontend
  - desktop Flutter targets do not support a near-term product need
  - every extra generated host shell adds native config surface, dependency churn, and maintenance cost
- In practical terms:
  - shared app behavior belongs in `mobile/lib/`
  - `ios/` and `android/` mostly exist to host the shared Dart app and carry native config such as bundle ids, package ids, plist/manifest settings, and plugin integration

### Web auth stance
- The current backend auth model is suitable for both mobile and web:
  - client obtains a Google identity token
  - backend verifies it
  - backend issues its own bearer session token
- Only the mobile client currently implements that flow.
- The React web app intentionally remains mostly anonymous because its job right now is planning/demo presentation, not authenticated companion usage.
- If web auth is added later, it should reuse the same `/api/auth/google/sign-in` exchange pattern with a web OAuth client id rather than introducing a separate auth mechanism.

## Resort Catalog Curation

Slow-changing ski-region, stay-destination/base, ski-area, access, terrain,
pass, rental, and season facts are maintained through skill-led, source-backed
curation. Canonical facts live in `app/data/catalog.json`; the trust manifest
owns entity-level trust and provenance metadata.

Meaningful catalog changes should use Pydantic evidence and report contracts so
review packets show the changed entity, field path, before/after values, trust
status, clickable source links, source type, evidence summary, and normalization
notes. Policy validators check report shape, required review fields, source-link
presence, trust-manifest coverage, and catalog consistency. They do not replace
owner judgment about whether a source supports the proposed meaning.

### Typed static catalog facts

Static feature and character facts use small frozen value objects in the
canonical catalog and dedicated JSON projection columns in PostgreSQL. Source
references and verification state remain in the trust manifest. The separation
keeps catalog values type-safe without creating relational tables for every
small fact, while independent trust groups prevent one strong source from
overstating unrelated fields. Versioned breaking migrations are deterministic,
audited, and coordinated across catalog, trust, persistence, and curation.

Scope matters for catalog truth. Ski areas are independent weather entities;
stay-base access is explicit; physically connected aggregates use generalized
terrain domains; and pass availability/defaults are explicit per stay
destination. Aggregate metrics remain on their source-scoped domain or pass.
See ADR 0009 for the canonical relationship model.

### Entity-scope assessment during curation

Full curation starts with a source-first inventory of material accommodation
markets, bases, terrain candidates, access relationships, connected domains,
and pass products. The curation report records each candidate's disposition and
evidence before field completeness is accepted. This makes missing graph nodes
and relationships reviewable without treating every name found on a map as a
new catalog entity.

Official map sectors, webcams, limited-area tickets, dedicated identity pages,
and child-scoped metrics are discovery or terrain-identity signals. They do not
create a `SkiArea` without a durable operations, weather, or full-local-pass
owner and material separation value. Connected candidates default to the parent
and require two independent owner categories, including operations or weather,
before being split. Disconnected or transfer-required complete terrain may
qualify with one owner category. Every candidate is compared with its nearest
parent scope; provider aggregation is corroborating evidence rather than the
deciding rule. Artificial child areas must not be created merely to manufacture
a `TerrainDomain`. See ADR 0016.

Accommodation and terrain boundaries remain independent. A distinct,
bookable accommodation market such as Kirchberg may justify its own
`StayDestination` and bases while sharing the same KitzSki `SkiArea`, provided
explicit access edges connect them. The market must still pass complete-scope,
independent-ownership, and material-separation gates; a place name or municipal
boundary alone does not qualify it. See ADR 0018.

Boundary adjudication should return `policy_determined` when only one graph
satisfies the destination or ski-area policy. `owner_choice_required` is for the
rare case where two materially different graphs both satisfy the applicable
gates with comparable evidence. Missing source evidence is
`evidence_insufficient`, not an owner preference.

Catalog maintenance never runs production weather migration inline. New active
ski-area IDs start without archive/climatology rows; after merge, the separate
Complete Historical Weather workflow discovers them, resumes backfill across
scheduled runs, and rebuilds climatology once archive coverage is complete.
Retained IDs keep their evidence. A material coordinate/elevation change on a
retained ID requires an explicit forced refetch and rebuild handoff.

Sourceable missing entities that fit the active curation batch should be added
in that PR. Deferral is an escape hatch for work that would make the batch
unmanageably broad, mix a separate model concern, depend on uncurated graph
nodes, require weather-identity migration, or remain genuinely unresolved. In
schema-version-3 reports, every `deferred` or `unresolved` assessment carries a
canonical `backlog_ref` to one consolidated regional H3 item under
`Catalog Curation Refinements`; that item contains the exact
`candidate_kind:candidate_id` marker for each linked assessment. Other
dispositions do not carry backlog references, and `not_separate` creates no
backlog item.

Maintainer review deliberately discovers first-order linked graph candidates
beyond the selected PR, but discovery scope is not mutation scope. When a
modeled linked entity is covered by another open curation PR, or a new linked
entity depends on that PR's unresolved graph, the selected PR records a
source-backed deferral and remains internally valid without changing the
dependency. Terrain domains, access edges, pass coverage, and owner decisions
that depend on the linked boundary belong to the owning PR. The selected PR may
still correct its own local metrics, evidence scope, and unsupported linked
claims. An owner choice confined to the linked dependency must never be
published against the selected PR. A dependency-only entity retained in
`reviewed_targets[]` for evidence uses
`resulting_graph_role=linked_dependency`; it remains visible in the review
inventory but cannot own changes or force its destination into the canonical
Resulting Graph.

When curation changes ranking or fit inputs, include ranking-impact notes and
run the Search V4 factor-readiness audit plus affected golden scenarios.

Bergfex is not primary catalog truth. It may act as warning-only freshness
sentinel evidence, and it may act as a fallback corroborating source when
official sources conflict for the same scoped static metric and no official page
is clearly authoritative. In those cases use `verified_with_adjustment`, keep the
official conflict visible in the curation report, and document any arithmetic or
normalization. Live open lifts, open piste kilometers, snow depth, and current
operating status should remain a separate operational-status concern with its
own freshness, observation, and trust model rather than being mixed into static
catalog curation.

## Search V4 Client And API Boundaries

Search ranking and optional refinement generation are separate request
lifecycles. `POST /api/search` returns a complete usable ranking and never waits
for an LLM. After deterministic ranking it stores a typed, lightweight
evaluated-baseline snapshot in a thread-safe process-local LRU/TTL store. The
store holds at most 64 entries for 60 seconds and retains only the canonical
intent SHA-256 digest, not a full `SearchIntent`, origin text, full
`CatalogSnapshot` or `CatalogTrustManifest`, brief, or provider secrets.
This exact-view consistency may retain evaluated baseline data for the full
60-second window; deploy or process restart clears it.

The browser then requests `POST /api/search/refinements` from the canonical
applied intent and public baseline fingerprint. The endpoint accepts only the
exact stored snapshot bound to both that fingerprint and the SHA-256 digest
recomputed from canonical request intent. Canonical serialization supplies the
equality binding; the store retains neither the full intent nor origin text, and
no separate typed-equality check occurs. The caller-visible fingerprint is not
trusted by itself. It never reruns deterministic search. Miss, expiry, eviction,
process restart, or canonical-intent digest mismatch returns typed
`temporarily_unavailable` and invokes neither deterministic search nor Gemini.
Ranking remains usable, and a deliberate ranking refresh creates a new snapshot.

The 60-second TTL is the ranking-to-refinement server handoff window for
generating a question, not a user answer timeout. A delivered question remains
answerable after expiry. Applying its typed answer reruns full search with the
updated intent, stores a new baseline, and immediately requests the next
refinement from that new snapshot. The process-local design is accepted for the
current single-instance deployment; horizontal scaling requires sticky routing,
shared state, or a redesigned handoff. Bounded `hit`, `miss`, `expired`, and
`evicted` outcomes make the handoff observable without recording intent, brief,
fingerprint, candidate, or client identifiers. ADR 0015 owns these handoff,
deadline, local admission, and compatibility rules.

Derived travel-window and lodging-budget values remain plain domain properties,
not Pydantic request or response fields. The web API client also projects typed
objects back to request-shaped payloads before search, refinement, or weather
requests. This explicit boundary prevents a response object from being posted
back as an accidentally broader request contract.

The LLM may identify useful typed refinement patches, but validated patches are
the only trusted output. User-visible question, reason, label, and description
copy is regenerated deterministically from policy-owned labels after validation.
Access claims likewise require both relationship and distance/mode trust; a
`needs_source` component cannot render as a positive near-lift claim.
Recommendation evidence mode is also backend-owned. Search V4 emits
`archive_backed`, `forecast_assisted`, or `fallback_heavy` from the evaluated
trip-window snow evidence; React only maps that typed value to traveler copy.

Repeated React interaction semantics live in a deliberately small internal UI
foundation under `frontend/src/ui`. It owns actions, alerts, async states,
badges, disclosures, metric tiles, section headers, and segmented tabs. Search
components retain domain composition and copy; there is no generic card layer
or full component-framework migration. Snow evidence uses a lazy Recharts
module over typed API rows, preserves null gaps, and pairs every chart with an
accessible data table. A failed chart chunk falls back to a compact table of the
same values. The browser must not interpolate observations or derive new
weather claims.

## Maintainer Pre-Push Curation Authority

Pre-push curation recovery uses one bounded generation timeline per PR. A
generation binds the selected remote head, prepare-time base, current local
head, report, and append-only stage events. Both delta-validated and reviewed
heads use the same two-phase idempotent `checkpoint curation` capability;
inspection returns a typed recipe ID and substitutions for the clean-head next
action. Prepared and review-required generations still enter the complete
normalization, inventory, review, and remediation flow. A clean review uses the
reviewed checkpoint; requested changes produce a bounded local commit that must
pass the delta checkpoint and another fresh review before it can become reviewed
authority. The helper validates the caller-created remediation head when the
delta checkpoint is invoked. Reviewed authority remains distinct from fully
validated authority, so ordinary push cannot bypass the final deterministic
suite while the existing manual-check path can still preserve an explicitly
unvalidated reviewed head.

Curation report mutations are atomic at the review-artifact boundary: the
canonical schema-v3 JSON report and its deterministic Markdown companion move
together before any delta or reviewed checkpoint. Boundary evidence also names
every assessment candidate explicitly through `boundary_target_ids`; an
evidence target alone does not establish boundary ownership. These mechanical
invariants are corrected in the same fixer pass and are not semantic
`review-incomplete` outcomes.

Legacy reviewed/remediation continuations are archived once through the
lease-free `migrate curation-state --archive-legacy` capability. Migration
refuses active leases and unresolved push, CI, or terminal-publication recovery,
leaves discovery and external-mutation state unchanged, and writes the
generation-v2 format marker last. Once a generation exists, the archived
pre-push state cannot be restored as authority. Push journals, post-push CI
continuations, and terminal-publication recovery remain unchanged by ADR 0020.

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
