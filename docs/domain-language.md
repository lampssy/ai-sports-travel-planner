# Snowcast Domain Language

This document defines Snowcast's shared domain language, bounded contexts, and
core invariants. It is a lightweight Domain-Driven Design reference, not a
requirement to use heavy DDD tactical patterns.

Use this document when writing feature specs, ADRs, advisory reviews, API
contracts, UI copy, and model docs.

## Principles

- Prefer precise product terms over generic travel-marketplace terms.
- Keep ski planning, catalog trust, conditions evidence, AI assistance, and
  booking handoff as distinct concerns.
- Treat uncertainty as part of the domain model. Estimated, stale, weak, or
  provider-missing data must remain visible.
- Do not let LLM output become catalog truth, ranking policy, or source-backed
  evidence without deterministic validation and human review.
- Update this document when a feature introduces a durable domain term, changes
  a term's meaning, or moves ownership between bounded contexts.

## Bounded Contexts

### Planning

Owns the recommendation decision model.

Primary concepts:

- search filters
- trip option
- recommendation group
- planning evidence
- evidence profile
- travel effort
- ranking and explanation policy

Boundaries:

- Uses catalog entities and conditions evidence.
- Does not own source acquisition, provider scraping, booking inventory, or LLM
  interpretation.
- LLMs may help parse input or explain output, but deterministic domain logic
  owns ranking.

### Catalog And Data Trust

Owns curated resort metadata and source-backed trust status.

Primary concepts:

- destination
- ski area
- stay base
- rental display fact
- source ref
- trust manifest
- acquisition proposal

Boundaries:

- Owns whether a field is verified, adjusted, estimated, or source-needed.
- Does not own live conditions, ranking weights, or booking availability.
- LLM extraction can propose facts, but cannot promote them to catalog truth
  without review.

### Conditions And Weather Evidence

Owns refreshed current conditions and historical weather evidence.

Primary concepts:

- condition snapshot
- current forecast
- archive weather history
- freshness
- disruption signal

Boundaries:

- Provides weather-derived evidence to planning.
- Does not claim official lift-operation status unless a future official status
  provider explicitly supports that provenance.
- Keeps forecast evidence separate from archive evidence.

### Companion

Owns saved-trip and on-trip user context.

Primary concepts:

- current trip
- trip watch
- alert decision
- last checked time
- companion state

Boundaries:

- Uses planning, catalog, and conditions data to explain changes for a concrete
  saved trip.
- Stays provider-agnostic: a user may book through Snowcast, book elsewhere, or
  not book yet.
- Does not turn the web planner into a generic account dashboard.

### Acquisition

Owns source discovery and proposal artifacts for catalog improvement.

Primary concepts:

- acquisition run
- configured source
- discovered source
- proposal
- fetch log
- source cascade

Boundaries:

- Produces reviewable artifacts and source-backed proposals.
- Does not update trusted catalog fields without validation and review.
- Keeps official/open source evidence preferred over LLM-derived extraction.

### Booking Handoff

Owns outbound accommodation/referral handoff.

Primary concepts:

- outbound target
- booking redirect
- click event
- suggested stay
- provider-backed stay

Boundaries:

- Converts a recommendation into an external booking/search action.
- Does not make Snowcast a hotel marketplace or inventory owner.
- Provider-specific behavior stays behind the redirect/link boundary.

### AI Assistance

Owns optional LLM-assisted interpretation and narrative support.

Primary concepts:

- parsed trip context
- clarification
- narrative
- deterministic fallback
- prompt boundary

Boundaries:

- May transform user text into structured context or explain ranked output.
- Does not own ranking, catalog truth, source trust, or provider data fetching.
- Must keep prompts, raw model responses, raw trip briefs, and sensitive user
  data out of logs, metrics, and traces.

### Observability And Operations

Owns runtime visibility and operational execution language.

Primary concepts:

- trace
- metric
- structured log
- freshness signal
- worker
- function
- trigger

Boundaries:

- Observes request paths, background work, provider boundaries, LLM behavior, and
  freshness.
- Does not change domain decisions or ranking semantics.
- Uses bounded labels and sanitized details.

## Core Glossary

**Destination**

The user-facing resort or trip destination, such as Tignes or Cervinia. It is the
top-level planning object shown to users.

**Ski area**

The mountain or ski-domain component used for snow, seasonality, elevation, and
conditions evidence. A destination may contain one or more ski areas.

**Stay base**

The village, town, or accommodation zone where the user would stay. Stay bases
drive lodging budget fit, lift-distance fit, and companion context.

**Suggested stay**

A provider-backed or estimate-only accommodation option under a stay base.
Suggested stays are not the top-level recommendation unit.

**Trip option**

A concrete planning option: destination plus ski area plus stay base plus travel
window plus budget fit plus evidence quality, optionally with travel effort and
suggested stay context.

**Recommendation group**

A compact user-facing group, normally destination plus selected ski area, that
contains a top trip option and optional alternative stay-base options.

**Search filters**

Structured planning inputs such as location, nightly stay-base budget, skill
level, quality tier, lift distance, travel window, and car-first travel context.
Structured filters are the source of truth for search.

**Trip context**

Parsed or saved context that may matter to planning or companion behavior, such
as party size, total-trip budget, duration, dates, origin, or user priorities.
Not every trip-context field is immediately a search filter.

**Current trip**

The user's active saved trip context for companion behavior. It is intentionally
provider-agnostic and minimal.

**Trip watch**

A future saved-trip monitoring concept that can evaluate whether a trip option
has materially improved or degraded.

**Condition snapshot**

A point-in-time weather or conditions record used for current conditions,
freshness, or historical evidence. It is not automatically official lift status.

**Evidence profile**

The trust shape of planning evidence, currently `forecast_assisted`,
`archive_backed`, or `fallback_heavy`.

**Source ref**

A reference to evidence outside the catalog file that supports a verified or
verified-with-adjustment catalog field.

**Trust manifest**

The catalog trust contract that marks field groups as verified,
verified-with-adjustment, estimated, or needs-source.

**Acquisition proposal**

A reviewable artifact generated by acquisition work. It may recommend catalog
changes, but it is not catalog truth until reviewed and accepted.

**Booking handoff**

The transition from Snowcast decision support to an external accommodation or
booking provider.

**Worker / Function / Trigger**

Documentation vocabulary for async, scheduled, or operator-started work:
trigger starts work, function is the bounded unit of work, and worker is the
runtime that executes it.

## Core Invariants

- Destination, ski area, and stay base are distinct concepts and should not be
  collapsed in UI, API, or model docs.
- Search recommendations are trip options, not generic resort cards or hotel
  inventory cards.
- `stars` remains a compatibility API field but means internal stay-base quality
  tier, not hotel-star rating.
- Nightly stay-base budget and rental prices are separate display facts until a
  real package-price model exists.
- Weather-derived `availability_status` is a disruption/conditions signal, not
  official lift-operation status.
- Verified and verified-with-adjustment catalog fields need source refs outside
  the catalog file itself.
- Estimated values must remain visible as estimates in user-facing contexts.
- LLM output can assist parsing, narrative, and proposal generation, but cannot
  own deterministic ranking or become trusted catalog data without review.
- Companion trip records remain provider-agnostic.
- Booking-provider behavior stays isolated to the booking handoff boundary.
- Background jobs should be described with Worker / Function / Trigger language
  before code-level orchestration abstractions are introduced.

## Updating This Document

Update this document when:

- a feature introduces a durable domain term
- an existing term changes meaning
- a new bounded context appears
- ownership moves between contexts
- an invariant is added, weakened, or removed

If the change also creates a durable architecture decision, add an ADR under
`docs/architecture/adr/`.
