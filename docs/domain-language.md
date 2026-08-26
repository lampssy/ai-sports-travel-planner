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

- search constraints
- search preferences
- trip configuration
- recommendation group
- planning evidence
- evidence profile
- ranking factor
- factor evaluation
- ranking policy
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

Owns refreshed current conditions, versioned forecast runs, and historical
weather evidence supplied to Planning.

Primary concepts:

- condition snapshot
- forecast run
- forecast head
- issue time, valid time, and lead time
- trip-window snowpack outlook
- archive weather history
- climatological snow reliability
- weather sampling status
- weather request geometry
- freshness
- disruption signal

Boundaries:

- Provides weather-derived evidence to planning.
- Publishes only validated complete forecast runs through atomic per-ski-area
  heads; provider calls never occur inside search.
- Does not claim official lift-operation status unless a future official status
  provider explicitly supports that provenance.
- Keeps forecast evidence separate from archive evidence.
- Samples only ski areas whose reviewed weather request geometry is `active`;
  `deferred` ski areas remain catalog entities but are excluded from automated
  weather refresh, backfill, completion, climatology rebuild, and product
  weather-evidence reads.
- Does not equate modeled snow depth with ski-area snow cover, open pistes, or
  lift operations.

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
- evidence envelope
- graph blocker
- regional follow-up
- coherent destination graph slice
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

### AI Orchestration And Assistance

Owns optional cross-product AI interaction and orchestration across structured
Snowcast surfaces. It binds registered domain capabilities together without
absorbing their business logic or becoming a chat-centric product shell.

Primary concepts:

- parsed trip context
- assistant context
- assistant interaction
- clarification opportunity
- clarification
- refinement proposal
- resolved refinement topic
- typed capability invocation
- explicit preference customization
- retrieved explanatory material
- deterministic fallback
- prompt boundary

Boundaries:

- May transform user text into structured context, select registered
  capabilities, explain grounded output, and present typed actions.
- Structured search, result, dossier, trip, and companion surfaces remain
  first-class; optional chat is only one possible interaction surface.
- May dynamically propose which registered factors to clarify, including
  question wording, answer options, and typed preference patches.
- A resolved refinement topic is one registered clarification topic that the
  traveler answered or skipped in the current search context. It stays
  suppressed until the trip context materially changes or the traveler
  manually changes the preference owned by that topic.
- Does not own ranking, catalog truth, source trust, or provider data fetching.
- Does not own weather derivation, companion event or alert eligibility,
  booking handoff, or durable trip and preference persistence.
- Does not create factor IDs, controlled values, weights, trust, utilities, or
  candidate scores; Planning validates proposed patches and their impact.
- Retrieves structured current data through typed domain capabilities. Uses
  document retrieval only for relevant unstructured, source-attributed
  explanatory material.
- Reads durable preferences from explicit assistant customization. Search
  refinements remain search-scoped by default and do not silently update that
  profile; deliberate trip choices may be trip-scoped. Persistent preferences
  are user-visible, editable, deletable, and scoped to the authenticated owner.
- Uses the minimum task-relevant context rather than sending all available user,
  search, trip, or conversation state to an LLM.
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

### Public Planning Language

Customer interfaces use `Trip option` for a ranked recommendation group,
`Trip details` for its detail view, and `Must-haves` for search constraints.
These public labels do not rename the internal Planning models below.

Trip details present one primary explanation. A separate `Why this trip`
section adds non-duplicated supporting evidence and limitations. Raw weights,
points, caps, policy identifiers, catalog trust internals, statistical methods,
weather source rows, and daily values belong in one collapsed `Technical
calculation details` disclosure.

In Conditions and Weather Evidence, `source type` identifies historical versus
forecast-assisted evidence; `source currency` identifies the forecast issue
time and archive/baseline years; `coverage` identifies usable dates and seasons;
and `expected conditions` summarizes response values. Request evaluation time
and cache expiry are not source freshness. A modeled snow-depth reference is
not a claim about ski-area snow coverage, open runs, comfort, or safety.

### Accepted Target Catalog Terminology

**Ski region**

The non-bookable trip-market umbrella used to group recommendation results. A
region may represent one stay market, a valley, or another reviewed market
identity. The trip-market grouping policy is the current ranked grouping; a
regional-network parent can organize broader pass geography without forcing one
ranked result.

**Stay destination**

The complete, independently evidenced accommodation market presented to a user.
It owns country, region, center coordinates, price level, and its parent trip-
market region. It does not own ski areas, local apres, or stay-base character.

A separate stay destination must have complete stay-market scope, independent
stay-market ownership, and material destination-level separation value. Direct
official stay-market evidence must support the ownership claim. A named village,
municipality, lift access point, or dedicated web page is not enough by itself.
A useful place that fails any gate is normally a `StayBase` under the nearest
qualifying destination. When several sibling markets each pass all three gates,
they remain separate destinations and their familiar umbrella is a `SkiRegion`.
See ADR 0018.

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

**Factor evidence mode**

The ranking-policy classification that determines how a factor becomes ready
and how missing evidence behaves. `comparative` factors need broad comparable
coverage. `positive_presence` factors may reward a verified available feature
without requiring widespread proof of absence. `categorical_match` factors
reward a requested trusted category. `objective_comparison` factors require a
comparable request-specific slice, and `composed_prediction` factors use
time-scoped coverage, freshness, and confidence. In every mode, catalog
`unknown` remains unknown; the mode changes ranking readiness, not catalog
truth.

A registry capability may also declare a typed composition target instead of
an independent factor weight. Snowmaking availability is the initial example:
when preferred, it supplies a bounded resilience input to trip-window snow fit
only while natural snow utility is weak. It never becomes a claim about
snowmaking coverage or open terrain.

**Ski area**

A complete terrain entity with independent or coordinated evidence ownership.
Current conditions, archive weather, climatology, season windows, elevation,
terrain metrics, and skill support attach to ski_area_id. A ski area may be
reachable from several stay destinations.

A separate ski area must have complete terrain scope, at least one durable
operations, weather, or full-local-pass owner, and material separation value.
Dedicated identity pages, child-scoped metrics, individual lift tickets,
webcams, and named map sectors are supporting evidence only. Curation must
compare every candidate with its nearest parent owner scope.

A ski-connected child remains part of its parent by default. Splitting it
requires two independent owner categories across operations, weather, and full
local pass, including operations or weather. A disconnected or
transfer-required complete area may qualify with one owner category. A
recognizable sector that fails these gates is `not_separate`; it may become a
future ski sub-area if product needs justify that layer. Provider boundaries
corroborate this assessment but do not determine it.

Evidence ownership may be `independent` or `coordinated`. Independent ownership
uses the existing area-level operations, weather, or full-local-pass evidence.
A coordinated multi-operator ski area requires an official complete lift or
terrain inventory (`official_complete_lift_inventory`), an exhaustive component
roster, a current status or schedule presentation
(`coordinated_status_or_schedule`) in which every component is addressable, one
pass covering every component (`common_full_coverage_pass`), and an explicit
child assessment. Each coordinated child is assessed exactly once with
`disposition=not_separate`, `parent_ski_area_id` equal to the coordinated
parent, a target reference to that parent, and `operational_scope=coordinated`.
The parent records five typed `coordination_evidence_families`:
`complete_terrain_lift_inventory`,
`exhaustive_component_operator_roster`,
`component_addressable_operations_status`,
`every_component_pass_coverage`, and
`direct_component_parent_assignment`. Every family has official
`evidence_refs` and `covered_component_candidate_ids` equal to the parent's
exact `component_candidate_ids`; aggregate `coordination_evidence_refs` is the
union of those family refs. Direct assignment must resolve every component,
although a common official source may establish several assignments. Children
do not repeat the parent's coordination metadata. The pass may also cover a
separately modeled adjacent ski area and does not establish the boundary by
itself. Coordinated scope and metadata require report schema version 3.

A coordinated child's `not_separate`, `separation_value=redundant`,
`operational_scope=coordinated`, parent-owned weather, and provider-consensus
declarations do not erase contradictory source-backed evidence. Complete terrain
plus a terrain-identity signal is evaluated with owner categories derived from
signals: operations (`separate_operator` or
`independent_status_or_schedule`), weather
(`independent_weather_presentation`), and a full local pass (`full_local_pass`
with `pass_scope=full_local`). A connected child is independently viable with
two categories including operations or weather; a transfer-required or
disconnected child is viable with one. Shared branding, provider consensus
alone, sector terrain, or one connected pass-only category is insufficient.

Minor nursery or satellite lifts may remain coordinated components when they
share the complete inventory, status system, pass, and stay market and have no
material independent recommendation, weather, season, operations, or pass
value. A complete transfer-required, weather-distinct, or independently owned
area remains a separate ski area. Coordinated operational ownership does not
imply active weather sampling; `weather_scope` and ADR 0021 are evaluated
independently.

Operations ownership describes the scope of official evidence, not ownership
of a dedicated website. A candidate-scoped official operator/member page and a
candidate-scoped current status or opening presentation can jointly prove that
scope even when a regional network publishes the live feed. Company identity
without current candidate-scoped operations remains only a discovery signal.

**Piste difficulty profile**

A ski-area breakdown normalized into beginner, intermediate, and advanced
buckets. `piste_km_by_difficulty` records published or defensibly measured
lengths. `piste_count_by_difficulty` records published run counts. The two
bases remain explicit because run segmentation and length vary; count evidence
may inform a lower-strength planning factor but never becomes claimed piste
kilometers. Qualitative supported-skill labels are weaker positive-only
fallback evidence.

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

An optional **pass validity window** records a separately published period of
ticket entitlement. It does not own or replace ski-area operating dates. When
no separate pass window is modeled, the pass adds no date restriction and the
covered ski area's season still governs practical applicability. When a dated
pass has no published window for a requested future season, Snowcast may retain
the configuration only with exact pass validity marked unverified; it never
projects an older tariff's dates into the future.

**Effective pass coverage** is the date-specific operating subset of a pass's
static contract coverage. A closed covered ski area does not invalidate the
pass for other operating areas, while an area with insufficient season evidence
remains explicitly unverified. Under partial coverage, a published full-network
terrain figure may remain visible only as non-date-adjusted context with a clear
warning; it does not contribute to terrain or pass-value ranking until a
reliable reduced value can be reproduced.

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

**Search constraint**

A typed rule that determines whether a trip configuration is eligible. A
constraint has no ranking weight. Country, travel dates, maximum travel time,
budget ceilings, and verified must-have features are examples.

**Search filter**

Compatibility and UI terminology for a structured search input. Search V4
classifies each filter as a constraint, a factor-backed preference, or an
assumption so that filtering and scoring semantics remain explicit.

**Search preference**

A typed instruction to prefer, avoid, or ignore a registered ranking factor. A
require instruction becomes a search constraint. User-facing importance maps
to policy-defined multipliers rather than an arbitrary LLM-provided weight.

**Group importance**

A controlled priority that multiplies one ranking group's default budget before
all active groups are normalized. It changes that group's possible overall
influence. It never weakens a hard constraint.

**Factor importance**

A controlled priority that reallocates weight among active factors inside one
group. It does not change the group's total effective budget.

**Ranking factor**

A stable registered dimension of trip fit, such as trip-window snow fit,
accessible terrain, party skill coverage, stay-base access, pass value, or
local apres. A
factor declares scope, lifecycle, roles, missing-data semantics, trust behavior,
and policy ownership.

**Factor evaluation**

One candidate's raw value, normalized utility, evidence scope, source trust,
prediction confidence, freshness, effective evidence cap, and explanation
inputs for one ranking factor. Static catalog trust and time-scoped prediction
confidence remain distinct even though both can cap influence.

**Ranking policy**

The versioned deterministic contract defining factor groups, group and factor
weights, activation, importance, trust, missing-data, correlation, and score
composition. It is inspectable independently from evaluator implementation.

**Refinement proposal**

An LLM-generated but non-authoritative question, answer options, reason, and
typed preference patches over registered factors. Planning shows it only after
deterministic schema, coverage, repetition, and ranking-impact validation.

**Trip context**

Parsed or saved context such as party size, total-trip budget, duration, dates,
origin, or user priorities. Not every trip-context field is a ranking input.

**Current trip**

The authenticated user's active saved trip configuration for companion
behavior. Stable IDs are canonical; display names are stored snapshots only.

**Condition snapshot**

A point-in-time weather-derived conditions record keyed by ski_area_id. It is
not official lift-operation status.

**Forecast run**

One immutable provider/model forecast issue with a stable run ID, stable
forecast source key, model initialization time, provider availability time,
forecast kind, valid-date horizon, and publication state. The source key
identifies the configured acquisition route; provider and model identify the
scientific provenance of that issue.

**Forecast head**

The atomic pointer from one ski area and forecast source key to its latest
validated complete forecast run. Search reads all configured eligible heads in
bulk rather than finding the latest issue from retained history. Source-keyed
heads allow the preferred ECMWF and extended-range GEFS ensemble routes to
coexist.

**Issue time**

The model initialization or reference time for a forecast cycle. It is distinct
from provider availability time, Snowcast ingestion time, and the future valid
date it predicts. Retrieval time must not be relabelled as issue time when a
provider exposes model-update metadata separately.

**Valid time / valid date**

The future instant or ski day described by forecast evidence.

**Lead time**

The duration between forecast issue time and valid time. Forecast influence and
calibration depend on this duration. For daily evidence, Snowcast derives
`lead_days` from the valid local date and the model initialization timestamp
converted to the stored ski-area/provider timezone.

**Trip-window snowpack outlook**

A deterministic Snowcast utility derived from model forecast variables for the
requested exact ski dates and representative ski-area elevations. It is not an
official resort report or an open-terrain prediction.

The first version evaluates one representative mid-mountain elevation. It
selects ECMWF ensemble mean through lead day 15 when complete, then GEFS
ensemble mean through day 30, with GEFS also available as a shorter-range gap
fallback. Daily GEFS values do not imply daily certainty; lead-time blending
limits days 17 through 30 to at most 15% forecast influence.

**Trip-window snow fit**

The ranked Trip Viability factor produced by composing climatological snow
reliability with any sufficiently covered, confident, and calibrated target-date
snowpack outlook for each requested ski day.

**Climatological snow reliability**

Historical seasonal evidence for a recurring travel window. It remains
separate from current forecast evidence even when Planning composes both into
one trip-window snow factor.

**Party skill coverage**

The amount and share of classified piste terrain broadly usable by the party's
ability level. Advanced coverage includes the complete classified network;
ability does not imply freeride or another terrain preference.

**Terrain preference**

An explicit preference such as freeride, cruising, challenging groomed pistes,
parks, night skiing, or glacier terrain. It is independent from skier ability.

**Hard travel limit**

A maximum journey duration or equivalent typed eligibility requirement. A
candidate outside the limit is excluded before weighted Travel Effort is
evaluated.

**Modeled snow depth**

Forecast or observed snow depth at a representative coordinate and elevation.
It is distinct from ski-area snow-cover percentage, skiable piste coverage,
open-piste kilometers, and open-lift count.

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
links evidence, records changes and unresolved gaps, states ranking impact, and
renders the resulting destination graph from normalized catalog relationships.

**Evidence envelope**

The bounded source and candidate universe frozen before semantic remediation.
It names the official source families, catalog relationships, concrete
candidates, and linked dependencies that the curation review must account for;
it does not make source meaning or candidate existence a deterministic claim.

**Graph blocker**

A source-backed omission or contradiction that can make the selected resulting
graph materially wrong or misleading, such as incorrect destination, ski-area,
pass, weather-owner, terrain-owner, or access ownership. It remains blocking
until fixed or routed through an explicit evidence or owner-decision gate.

**Regional follow-up**

An additive adjacent catalog opportunity whose omission does not make the
selected graph incorrect. It is recorded in the schema-v3 report and merged
product backlog for discovery; it does not by itself make curation
non-converging.

**Coherent destination graph slice**

One primary stay destination plus the bases, access edges, ski areas, terrain
domains, pass products, trust evidence, and weather or migration handoffs needed
to review that destination as an internally meaningful proposal. It is neither
one entity per proposal nor an entire region by default.

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
- Forecast issue versions remain prediction evidence and never enter observed
  archive history or climatology.
- One eligible forecast source is selected for each ski-area/date evaluation;
  ECMWF and GEFS values are not averaged into an opaque synthetic forecast.
- The latest condition snapshot is not target-date forecast evidence merely
  because a requested trip is near-term.
- Search constraints decide eligibility; ranking factors compare eligible trip
  configurations and cannot hide hard requirements as negative weights.
- Group importance changes normalized group budgets; factor importance only
  redistributes a group's existing budget.
- Maximum journey duration and known out-of-season dates are evaluated before
  scoring.
- Party ability and terrain preference are independent.
- LLM-generated refinement wording may be dynamic, but only registered and
  deterministically validated preference patches can affect ranking.
- Adding a ranking factor must not silently increase the maximum score or turn
  unknown evidence into verified absence.
- Sparse positive-presence facts may influence ranking only after an explicit
  preference or validated clarification; they do not create an always-on
  feature-count bonus.
- Estimated lodging ranges may enforce only an explicit, visibly estimate-aware
  budget constraint; they do not create lodging-price ranking influence.
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
