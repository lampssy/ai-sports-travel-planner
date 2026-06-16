# Snowcast Product Charter

## Purpose

Snowcast is a conditions-smart ski trip planner. It helps skiers choose a resort,
understand snow and weather uncertainty before booking, and carry useful
trip-specific context into the companion phase.

The product promise is trusted decision support under uncertainty. Snowcast
should make conditions signals explainable, timestamped, and honest about what
is forecast, reported, estimated, stale, or weakly evidenced.

## Target User

Primary users are adults aged 30-55 who ski or snowboard one to three times per
year, research before booking, care about snow reliability, and travel with a
partner, family, or small group.

Secondary users may later include ski tour operators and travel agents that need
a recommendation and conditions layer for clients.

Snowcast is not for generic travel planning, broad multi-sport discovery, or
hardcore locals who already know where to ski every day.

## Product Scope

Snowcast is ski and snowboard only. Other sports are out of scope unless a
future deliberate product decision proves they share the same audience,
conditions-driven logic, and data quality requirements.

In scope:

- ski-resort discovery and comparison
- conditions-aware planning and ranking
- source-backed resort catalog improvement
- provider-agnostic booking handoff
- saved-trip and current-trip companion context
- AI-assisted parsing and narrative where deterministic logic remains the owner

Out of scope for the current product:

- generic AI itinerary generation
- unsupported marketplace inventory claims
- social features before the planning and companion loops are strong
- LLM-generated catalog truth
- broad account/profile surfaces before trip continuity needs them

## Product Principles

- Conditions are the core differentiator.
- Deterministic domain logic owns ranking and product decisions.
- AI helps interpret messy input and explain structured output; it does not own
  catalog truth, ranking policy, provider data, or source integrity.
- Source trust must stay visible. Estimated, stale, weak, or provider-missing
  data should not be presented as verified fact.
- The product sequence is discovery -> booking handoff -> companion.
- Booking.com or any other provider is a channel, not the product identity.
- Mobile is the long-term companion surface; web remains the public planning and
  demo surface.
- Snowcast should stay useful for users who book through the app, book
  elsewhere, or already have accommodation arranged.

## Product Stages

### Stage 1: Discovery Engine

Help users find the right resort for a trip.

- structured search by location, budget, quality tier, skill level, lift access,
  travel window, and travel effort
- conditions-aware ranking using snow confidence, disruption risk, weather
  evidence, and planning confidence
- explainable results with highlights, risks, provenance, and source freshness
- free-text trip brief parsing into visible, editable trip state

### Stage 2: Booking Handoff And Trip Context

Close the recommendation loop and capture context for later companion value.

- outbound accommodation handoff and referral tracking
- suggested stays where provider-backed or clearly caveated data exists
- provider-agnostic current-trip record
- booking status that works for users who book through Snowcast, book elsewhere,
  or are not booked yet

### Stage 3: Trip Companion

Use saved trip context to provide current, personalized guidance.

- current-trip status and change history
- alert eligibility and companion events for meaningful condition changes
- mobile-first notification readiness
- future grounded assistant behavior for saved-trip questions

### Stage 4: Group And Operator Expansion

Only after the core loop is proven:

- shared trip views
- group decision support
- premium companion features
- possible B2B planning layer for operators or travel agents

## Current Product State

Snowcast currently has:

- a FastAPI backend with PostgreSQL-backed repositories
- curated Alpine resort data with explicit destination, ski-area, stay-base, and
  rental display facts
- catalog validation and a trust manifest for source-backed review
- Open-Meteo-backed conditions refresh and historical weather evidence
- derived snow climatology for archive-backed future-window planning
- deterministic planning, ranking, and explanation policy
- LLM-assisted trip-brief parsing and grounded narrative support with fallback
  behavior
- a React/Vite web planning surface with brief-first search, visible filter
  chips, routeable result/detail/current-trip views, and booking handoff
- backend-rendered public resort pages with SEO support
- a Flutter mobile companion client with Google sign-in, backend session
  exchange, search, current-trip, and companion-event flows
- production deployment assets, scheduled refresh workflows, health checks,
  observability foundations, and runbooks

## Current Roadmap

### Now

- Keep the product/docs framework coherent: product charter, strategy, feature
  specs, ADRs, domain language, advisory reviews, and runbooks should each have
  a clear role.
- Keep historical docs clearly marked and generated artifacts out of version
  control so active guidance is easy to find.
- Preserve trust and privacy boundaries while maintaining observability and
  data-refresh reliability.
- Rebuild historical weather and derived snow climatology after weather-critical
  resort coordinates and elevation bands are locked.

### Next

- Strengthen operational resort-status acquisition as a separate frequent data
  pipeline rather than mixing live lift/status observations into static catalog
  acquisition.
- Improve catalog/source integrity where high-impact fields remain estimated or
  weakly sourced.
- Tighten frontend and mobile maintainability when working in those clients,
  especially large all-in-one app files.
- Reconcile mobile production readiness items such as package IDs, signing, and
  notification delivery when companion work becomes active again.

### Later

- Add richer accommodation filters only after the stay-base and provider data can
  support them honestly.
- Expand booking handoff beyond first-channel referral links when provider data
  and conversion evidence justify it.
- Add premium companion features, push notifications, and grounded trip assistant
  behavior after saved-trip context proves useful.
- Consider group or operator workflows only after the consumer discovery ->
  booking handoff -> companion loop is credible.

## Open Product Questions

- Which trust gaps in the resort catalog most affect real booking decisions?
- What operational-status sources can provide reliable lift, piste, snow-depth,
  or disruption evidence without overclaiming official status?
- How much accommodation data is enough before exposing richer stay filters?
- When does web auth create enough continuity value to justify login friction?
- Which mobile companion actions are useful enough to justify real push
  notification delivery?

## Planning And Documentation Model

`PROJECT.md` is the product charter and current roadmap snapshot. It should stay
short, current, and product-facing.

Use the rest of the docs system for more specific purposes:

- `README.md`: setup, local development, usage, deployment entry points
- `docs/product-backlog.md`: candidate ideas and future work that are not active
  implementation commitments yet
- `docs/strategy.md`: deeper market, monetization, and sequencing strategy
- `docs/domain-language.md`: shared domain terms, bounded contexts, and
  invariants
- `docs/data-trust-model.md`: catalog/source trust contract
- `docs/planning-model.md`: planning, ranking, evidence, and policy semantics
- `docs/engineering-notes.md`: durable technical notes and tradeoffs
- `docs/architecture/adr/`: Architecture Decision Records
- `docs/operating-model/review-playbook.md`: advisory routing, Developer
  Decision Checkpoints, Superpowers integration, and framework maintenance
- `docs/operating-model/feature-spec-template.md`: feature spec convention for
  high-risk or durable behavior changes
- `docs/operating-model/advisory-reviewers.md`: advisory reviewer contracts and
  output formats
- `docs/superpowers/specs/`: feature or sprint design specs
- `docs/superpowers/plans/`: implementation plans and execution records
- `docs/*runbook.md`: operational procedures

Completed sprint history should not live in this file. Historical plans,
screenshots, and audit records can remain in their dedicated docs folders when
they are still useful as evidence or context, but they should not be treated as
active product direction.

Detailed backlog ideas should live in `docs/product-backlog.md` until they are
promoted into feature specs or implementation plans.
