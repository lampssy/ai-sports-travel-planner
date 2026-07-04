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
- trip configuration
- recommendation group
- planning evidence
- evidence profile
- travel effort
- ranking and explanation policy

Boundaries:

- Uses catalog entities and conditions evidence.
- Does not own source research, provider scraping, booking inventory, or LLM
  interpretation.
- LLMs may help parse input or explain output, but deterministic domain logic
  owns ranking.

### Catalog And Data Trust

Owns the normalized trip-market catalog and source-backed trust status.

Primary concepts:

- ski region
- stay destination
- stay base
- ski area
- ski-area access
- terrain domain
- lift-pass product
- rental display fact
- field source refs
- trust manifest
- curation report

Boundaries:

- Owns whether a field is verified, adjusted, estimated, or source-needed.
- Does not own live conditions, ranking weights, or booking availability.
- Research may use AI assistance, but only reviewed source-backed edits become
  catalog truth.

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

### Catalog Curation

Owns source research and review artifacts for catalog improvement.

Primary concepts:

- curation pass
- reviewed target
- field coverage
- evidence item
- normalization note

Boundaries:

- Produces reviewable catalog edits and typed evidence reports.
- Does not update trusted catalog fields without validation and review.
- Keeps direct official/open evidence preferred over secondary corroboration.

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

Owns optional LLM-assisted interpretation at the user-input boundary.

Primary concepts:

- parsed trip context
- clarification
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

### Accepted Target Catalog Terminology

**Ski region**

The non-bookable trip-market umbrella used to group recommendation results. A
region may represent one stay market, a valley, or another reviewed market
identity. The trip-market grouping policy is the current ranked grouping; a
regional-network parent can organize broader pass geography without forcing one
ranked result.

**Stay destination**

The bookable town or destination context presented to a user. It owns country,
region, center coordinates, price level, and its parent trip-market region. It
does not own ski areas, local apres, or stay-base character.

**Stay base**

A village, neighbourhood, resort station, or resort sector where the user can
stay. It owns lodging price/quality estimates, representative elevation,
structural base type, local character, and local apres. Ski access is always an
explicit edge.

**BaseType**

The structural class of a stay base: `town`, `village`, `hamlet`,
`resort_station`, `neighbourhood`, or `resort_sector`. It describes settlement
form, not development history, pace, quality, or elevation. A null value means
the type has not been curated.

**BaseCharacterFact**

The stay base's independently curated development style and local pace.
Development style is `traditional`, `mixed`, `planned_resort`, or `unknown`;
local pace is `quiet`, `balanced`, `lively`, or `unknown`. `balanced` is a
positive assertion, not a fallback for missing evidence.

**ApresProfileFact**

A source-aware apres classification with availability, intensity, and optional
season label. `StayBase.local_apres_profile` describes activity within or around
the accommodation base; `SkiArea.ski_day_apres_profile` describes the ski-day
offer. The two may legitimately differ.

**AvailabilityStatus**

The shared feature state `available`, `unavailable`, or `unknown`. `available`
requires supporting evidence. `unavailable` requires an explicit authoritative
statement or a reviewed complete inventory for the owning entity and season.
Website silence and incomplete research mean `unknown`.

**Ski area**

An independently stored terrain and weather-evidence entity. Current conditions,
archive weather, climatology, season windows, elevation, terrain metrics, and
skill support attach to ski_area_id. A ski area may be reachable from several
stay destinations.

**Ski-area access**

A reviewed relationship from one stay base to one ski area. It carries access
mode, lift-distance bucket, optional distance/duration and nearest-lift facts,
directness, source URLs, and regional IDs. The catalog never creates Cartesian
stay-base-to-area access.

**Terrain domain**

A ski-connected aggregate over two or more ski areas. It may be local or
cross-destination and can carry source-scoped aggregate terrain metrics. It does
not own weather evidence and is not created by pass validity alone.

**Lift-pass product**

A named ticket product available from explicit stay destinations and valid for
explicit ski areas and/or terrain domains. Default selection is scoped per stay
destination. Reviewed prices and pass-accessible aggregate terrain remain on
the product rather than being copied to child ski areas.

**Rental display fact**

A reviewed equipment-rental example scoped to a stay destination and optionally
a stay base. It is display context, not exhaustive provider inventory.

**Trip configuration**

A concrete candidate composed of ski region, stay destination, stay base,
selected ski area, explicit access edge, selected pass, travel window, budget
fit, travel effort, and ski-area evidence.

**Recommendation group**

One ranked trip-market result keyed by ski_region_id. It contains the winning
trip configuration plus a bounded set of materially useful alternatives from
the same region. Weather and snow evidence shown on each configuration remains
scoped to its selected ski area.

**Search filters**

Structured planning inputs such as country, nightly lodging budget, quality
tier, skill level, lift distance, travel window, and car-first travel context.

**Trip context**

Parsed or saved context such as party size, total-trip budget, duration, dates,
origin, or user priorities. Not every trip-context field is a ranking input.

**Current trip**

The authenticated user's active saved trip configuration for companion
behavior. Stable IDs are canonical; display names are stored snapshots only.

**Condition snapshot**

A point-in-time weather-derived conditions record keyed by ski_area_id. It is
not official lift-operation status.

**Evidence profile**

The trust shape of planning evidence: forecast-assisted, archive-backed, or
fallback-heavy.

**Source ref**

Direct external evidence attached to the exact trust group it supports. One
group's source does not establish an unrelated fact.

**Trust manifest**

The field-group contract that marks catalog data as verified,
verified-with-adjustment, estimated, or needs-source and stores each group's
own source-reference list.

**Catalog curation report**

A typed review packet that covers every applicable field for reviewed entities,
links evidence, records changes and unresolved gaps, and states ranking impact.

**Suggested stay**

A future provider-backed or estimate-only accommodation option under a stay
base. Suggested stays are not top-level search results.

**Trip watch**

A future monitoring concept that evaluates whether a saved trip configuration
has materially improved or degraded.

## Core Invariants

- Ski region, stay destination, stay base, ski area, access edge, terrain
  domain, and lift-pass product are independent concepts.
- Search recommendations are concrete trip configurations grouped by trip
  market, not generic resort cards or hotel inventory cards.
- `stars` remains a compatibility API field but means internal stay-base quality
  tier, not hotel-star rating.
- Nightly stay-base budget and rental prices are separate display facts until a
  real package-price model exists.
- Weather-derived `availability_status` is a disruption/conditions signal, not
  official lift-operation status.
- Verified and verified-with-adjustment catalog groups need group-specific
  source refs outside the catalog file itself.
- Estimated values must remain visible as estimates in user-facing contexts.
- LLM output can assist parsing and source research, but cannot own deterministic
  ranking or become trusted catalog data without review.
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
