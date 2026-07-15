# Resort Fit Data Model Design

## Summary

Define a durable resort fit and data-reliability model for Snowcast. The model
should improve ranking correctness and launch trust for the current catalog
while making room for future resorts, richer stay-base data, and eventually
hotel-level amenities.

The core direction is to stop treating current catalog labels such as
`quality`, `supported_skill_levels`, and `lift_distance` as permanent direct
truth. Instead, Snowcast should separate raw source-backed facts, derived fit
factors, trust state, ranking policy, and user-facing explanation.

## Decision And Review Gate

- Classification: `review-gated`
- High-risk domains touched by future implementation: ranking correctness, data
  trust, public claims, catalog acquisition, user-facing recommendation
  semantics, and future maintenance patterns.
- Developer Decision Checkpoint status: resolved by owner discussion.
  - Optimize v1 for ranking correctness plus launch trust cleanup.
  - Keep current-catalog cleanup tied to a reusable model because more resorts
    will be added over time.
  - Define important fit factors beyond today's current filters, including
    terrain scale, resort character, stay-base access, and future amenities.
  - Avoid redesigning scoring every time a new filter appears by introducing an
    extensible factor registry.
- ADR status: not required for this design document. A later ADR is appropriate
  if implementation adds persistent factor tables, materially changes the public
  API contract, or makes a long-lived ranking architecture change.
- Advisory review status: deferred for this brainstorming output. Before
  implementation changes ranking behavior or public trust semantics, run
  advisory `design-review` or record an explicit skip reason in the plan.

## Problem

Snowcast's weather and climatology evidence is relatively strong and has a
defined model. Resort and stay-base fit is weaker: several high-impact fields
are estimated, yet they affect ranking and confidence. The main risk is not only
missing catalog rows. The bigger risk is using loosely defined labels as if they
were source-backed, durable product facts.

Current examples:

- `stay_base.quality` heavily influences score and recommendation confidence.
- `supported_skill_levels` gates and boosts results.
- `lift_distance` affects filtering, score, and explanation.
- Source trust gaps are concentrated in quality, lift distance, skill levels,
  prices, and rental facts.

The current model needs a clearer answer to:

- What actually makes a resort or stay base a good fit?
- Which factors should always influence ranking?
- Which factors should only matter when a user asks for them?
- Which fields can be source-backed now, derived now, or only planned for later?
- How should low-trust factors be prevented from dominating recommendations?

## Goals

- Define a factor taxonomy that covers current and future trip-choice drivers.
- Introduce a consistent factor shape that can support future filters without a
  scoring redesign.
- Define how raw facts become derived labels.
- Define trust-state caps so weak data cannot create strong ranking boosts.
- Prioritize current-catalog cleanup based on ranking and public-claim impact.
- Preserve acquisition extensibility for future resorts.
- Keep implementation possible without a large database redesign in v1.

## Non-Goals

- Do not build a hotel marketplace.
- Do not ingest accommodation inventory or hotel amenities in v1.
- Do not use LLM output as catalog truth.
- Do not make broad acquisition artifacts runtime inputs.
- Do not add operational lift/piste status to ranking until source-backed status
  ingestion exists.
- Do not force every planned future factor into the UI immediately.

## Factor Taxonomy

The model should organize resort fit around factor groups, not only current
fields.

### Trip Viability

Trip viability answers whether the trip is likely to work for the requested
window.

Factors include:

- snow reliability
- season window
- weather disruption risk
- current forecast assistance
- official operational status when future sources support it

These should normally carry the strongest ranking influence because a poor snow
or season match can ruin the trip.

### Ski Experience Fit

Ski experience fit answers whether the mountain suits the skier.

Factors include:

- terrain scale
- total piste kilometers
- piste difficulty mix
- lift count and lift network strength
- beginner friendliness
- advanced challenge
- grooming or terrain variety when source-backed
- glacier, altitude, and late-season resilience

Skill fit belongs here, but it should become more nuanced than today's
`supported_skill_levels` list. The list can remain a compatibility label while
the model moves toward derived skill profiles. Distance-based
`piste_km_by_difficulty` and count-based `piste_count_by_difficulty` are distinct
facts. Counts are useful fallback evidence but cannot be relabelled as measured
kilometres because piste segmentation and length vary materially.

### Stay-Base Practicality

Stay-base practicality answers whether the recommended base is useful in real
trip logistics.

Factors include:

- walking distance to lifts
- nearest lift distance in meters
- ski bus availability
- car requirement
- access mode
- proximity to rental or ski-school areas
- lodging-zone quality and convenience

This is where current `stay_base_lift_distance` should evolve into a derived
access profile.

### Budget And Value

Budget and value should remain separate.

Factors include:

- nightly lodging budget fit
- lift-pass price examples
- rental price examples
- total-trip affordability later
- value-for-money later, once the model can compare cost against quality,
  terrain, snow reliability, and access

Cheap is not automatically good value. V1 should keep budget fit in effect and
defer richer value scoring until the required facts are stronger.

### Resort Character

Resort character answers what kind of trip the resort supports.

Factors include:

- apres or nightlife
- quiet village
- family-friendly
- pure-skiing focus
- premium or luxury
- scenic or romantic
- restaurants
- wellness orientation
- group suitability

These should not become universal ranking boosts. They should mostly affect
ranking when the user expresses a relevant preference or when the UI explains
why a destination suits a selected trip style.

### Accommodation Amenities

Accommodation amenities are planned future factors, not v1 ranking inputs.

Factors include:

- sauna
- hot tub
- spa
- pool
- half-board
- on-site restaurant
- family rooms
- ski room or boot room
- shuttle service

These belong at an accommodation or provider-backed stay option level once
Snowcast has reliable hotel/provider data.

### Trust And Evidence

Every factor should expose a trust state:

- `source_backed`
- `derived_from_partial_data`
- `manual_estimate`
- `needs_source`

Low-trust factors can help identify cleanup priorities. They should not create
strong positive ranking boosts.

## Scoring Policy

Ranking should have two layers.

### Always-On Core Fit

These factors should influence most searches:

- snow reliability and season viability
- terrain fit for requested skill level
- budget fit
- stay-base access practicality
- travel effort when origin is supplied
- evidence and trust confidence

### Preference-Activated Fit

These factors should mostly influence ranking only when requested or safely
inferred:

- apres or nightlife
- quiet village
- family-friendly
- luxury or wellness
- pure-skiing focus
- restaurants
- scenic village
- group suitability

This avoids encoding one universal definition of "best resort." A nightlife
resort should not beat a better skiing fit unless nightlife matters for the
user. A quiet family base should not win by default unless the trip context makes
that relevant.

### Skill Fit

Skill fit should remain important, but not as a simplistic universal filter.

Policy:

- Beginner mismatch can gate or heavily penalize a result.
- Intermediate fit should be broad and forgiving.
- Advanced fit should boost destinations with enough challenge, terrain scale,
  altitude, or expert indicators.
- Skill fit should be derived from terrain facts and reviewed source evidence,
  not manually assigned to stay bases forever.

### Trust Caps

Trust state should cap ranking influence:

- `source_backed`: full influence.
- `derived_from_partial_data`: reduced influence.
- `manual_estimate`: small influence, mostly explanation.
- `needs_source`: no positive ranking boost.

This keeps Snowcast useful before every field is perfect, while preventing weak
catalog labels from dominating recommendations.

## Extensible Factor Registry

Each factor should have a consistent shape:

```text
factor_id
scope: destination | ski_area | stay_base | accommodation | rental
raw_inputs
derived_value
trust_state
ranking_role
user_filter_role
display_role
lifecycle_state
```

Lifecycle states:

- `active`: defined, derivable, and ranking-ready inside factor policy after
  review. It is not permission to change production `/api/search` ordering,
  saved-trip grouping, or itinerary ranking; that still requires a later
  ranking-integration checkpoint and comparison review.
- `measured_not_ranked`: collected and audited, but not ranking yet.
- `planned`: model slot exists, no runtime behavior yet.
- `disabled`: explicitly out of scope.

Examples:

### `terrain_scale`

- Scope: `ski_area`
- Raw inputs: total piste km for the initial bucket; lift count and linked
  ski-area structure are retained as raw/future refinement inputs.
- Derived value: small, medium, large, mega.
- Ranking role: core boost, especially for intermediate and advanced trips.
- User filter role: future "large ski area" preference.
- Initial lifecycle: `active` once source-backed terrain facts are review-ready
  in factor policy, otherwise `measured_not_ranked` or `planned`.

### `stay_base_access`

- Scope: `stay_base`
- Raw inputs: nearest lift distance meters, access mode, ski bus availability,
  car requirement.
- Derived value: walkable, shuttle-easy, car-recommended, unknown.
- Ranking role: core practicality factor.
- User filter role: future "walk to lift" or "ski bus okay" filters.
- Initial lifecycle: `active` where enough data exists for factor-policy
  readiness; conservative fallback elsewhere.

### `resort_character`

- Scope: `destination` or `stay_base`
- Raw inputs: official tourism descriptions, reviewed tags, amenities,
  source-backed editorial evidence.
- Derived value: quiet, family-friendly, nightlife, pure-skiing, premium,
  scenic.
- Ranking role: preference-activated.
- User filter role: future trip-style filters.
- Initial lifecycle: `planned` or `measured_not_ranked`.

### `accommodation_amenities`

- Scope: `accommodation`
- Raw inputs: provider-backed hotel facts.
- Derived value: spa, sauna, hot tub, half-board, restaurant, family rooms.
- Ranking role: not ranked until Snowcast has accommodation data.
- User filter role: future hotel-level filters.
- Initial lifecycle: `planned`.

The guardrail is that new factors can be added without changing the scoring
architecture, but they cannot influence ranking until their trust state and
ranking role are explicitly defined.

## Data Acquisition And Cleanup Strategy

### Acquire Or Source-Back Now

Prioritize facts that improve ranking trust for the current catalog and create a
repeatable path for future resorts:

- official links by role: ski area, ski pass, season dates, trail map, status
  pointer
- exact or current-season `season_windows`
- ski-area terrain facts: `total_piste_km`, `total_lift_count`,
  `piste_km_by_difficulty`, and `piste_count_by_difficulty` when publishers
  expose run counts rather than lengths
- aggregate linked-terrain facts under `terrain_groups` when a source covers
  multiple modeled ski areas together
- shared linked-domain facts under `terrain_domains` when a source covers ski
  areas modeled under multiple destinations
- stay-base access facts: coordinates, nearest lift, distance meters, access
  mode, ski bus or car requirement where available
- lift-pass prices and scoped lift-pass products
- lift-pass product `terrain_domain_ids` when a regional pass covers a modeled
  shared terrain domain
- lodging and rental price ranges where source-backed enough
- zero or missing climatology groups for important ski areas

### Derive Now

Create deterministic derived labels from current or attainable facts:

- `skill_fit_profile`
  - Based first on piste-kilometre difficulty mix, then source-backed run-count
    mix with reduced influence, then positive-only qualitative skill labels.
    Unknown or weak evidence shrinks toward neutral rather than zero. The
    initial balanced policy saturates beginner fit at `30%/10 km` compatible
    terrain, intermediate fit at `70%/30 km`, and advanced fit at `100%/50 km`;
    mixed-skill party fit uses the minimum represented-level result.
- `terrain_scale`
  - Based on total piste km for the initial buckets. For selected ski-area
    diagnostics, use selected ski-area terrain when no broader reviewed scope is
    available. When the default lift-pass product references destination-local
    `terrain_groups` or shared `terrain_domains`, derive an accessible-terrain
    diagnostic factor from that pass scope instead of copying aggregate facts
    onto child ski areas. Lift count and linked ski-area structure remain raw
    inputs for refinement.
- `stay_base_access`
  - Based on distance meters, access mode, and transport requirement.
- `stay_base_quality_profile`
  - Initially conservative, based on lodging price band, source-backed
    stay-base character, and manual review.
- `resort_snow_reliability`
  - Based on climatology, elevation, season windows, and historical weather.

### Plan But Do Not Rank Yet

Model these factors without letting them influence ranking until data improves:

- apres or nightlife strength
- quiet, family, premium, scenic, and pure-skiing character
- restaurants, wellness, spa, sauna, hot tub
- hotel-level amenities
- operational lift and piste status
- crowding or lift-line risk
- snowmaking coverage, unless source-backed cleanly
- transfer, airport, train, package, or flight data beyond current car-first
  travel effort

### Current Catalog Cleanup Priority

For the current 26 destinations, cleanup should prioritize:

1. Fields that gate or heavily affect ranking: skill fit, access or lift
   distance, quality, and price.
2. Fields that protect public claims: official links, season windows, and source
   references.
3. Major weather evidence holes: zero or missing climatology groups for
   important ski areas.
4. Future expansion identifiers: regional IDs only where they unlock acquisition
   or status sources.

Regional IDs are acquisition infrastructure, not fit-score inputs. They should
be added when they support a real source path or reduce ambiguity for a
high-impact entity.

## Architecture And Data Flow

Introduce a boundary between raw catalog data and ranking:

```text
catalog facts
  -> factor derivation
  -> factor trust caps
  -> ranking policy
  -> explanation and UI labels
```

`app/data/resorts.json` remains the approved catalog source for v1 raw facts:

- piste km
- difficulty split
- lift count
- lift-pass products and pass scope
- destination-local terrain groups
- shared terrain-domain references through `app/data/terrain_domains.json`
- coordinates
- lift distance meters
- access mode
- price ranges
- source-backed season windows

A new domain policy layer should derive normalized factors:

- `terrain_scale`
- `skill_fit_profile`
- `stay_base_access`
- `stay_base_quality_profile`
- `snow_reliability_profile`
- future `resort_character_profile`

Use `factor_id` as the code and audit identity. Names ending in `_profile` are
display/profile terminology unless the factor registry explicitly declares them
as factor IDs; for this slice, the stay-base access factor ID is
`stay_base_access`.

The trust manifest or a companion trust structure should decide how strongly
each factor can affect ranking. Search ranking should consume derived factors
rather than raw loosely defined labels, but only after the later
ranking-integration checkpoint promotes them into production ranking.

### Accessible Terrain And Result Grouping

Selected ski area remains the weather, seasonality, and current-conditions unit.
Accessible terrain can be broader than the selected ski area when the default
lift-pass product covers a destination-local terrain group or a shared terrain
domain. Ranking diagnostics should therefore record the terrain source scope:

- `ski_area`: selected ski-area facts only;
- `terrain_group`: destination-local aggregate facts;
- `terrain_domain`: shared cross-destination aggregate facts.

Production result grouping is a separate decision from option scoring. The
diagnostic path should continue to score option rows, but it should also report
when several rows compete for the same user-facing result group. Candidate
grouping analysis should compare:

- destination-level grouping for multi-ski-area destinations such as Chamonix;
- shared-domain grouping for linked terrain such as Tignes-Val d'Isere;
- stay-base alternatives inside each selected group.

The production ranking switch should not happen until the owner reviews both
candidate scores and candidate grouping behavior. The intended user-facing
direction is one ranked result per destination or shared domain, with the best
ski-area/stay-base option and alternatives nested inside that result.

Example target shape:

```text
stay_base_quality_profile:
  value: premium
  basis: lodging_price_band + reviewed_source
  trust_state: derived_from_partial_data
  ranking_cap: reduced
```

Avoid a large database redesign in v1. This can start as domain policy code,
docs, tests, and catalog-derived computation. Richer persisted factor tables
should wait until acquisition volume or runtime needs justify them.

## Error Handling

Missing or weak data should degrade explicitly:

- If a core factor is missing, use a neutral fallback or uncertainty penalty
  depending on the factor.
- If a factor is `needs_source`, it must not create a positive ranking boost.
- If a derived factor depends on incomplete inputs, mark it
  `derived_from_partial_data`.
- If acquisition sources conflict, keep the current catalog value and generate a
  review artifact.
- If a future filter depends on missing data, avoid offering it broadly or mark
  results as incomplete rather than pretending all resorts were evaluated
  equally.

## Verification

### Policy Tests

Add focused tests for factor derivation:

- piste difficulty mix maps to expected skill profiles
- total piste km maps to initial terrain-scale buckets
- lift count and linked ski-area structure remain available for future
  terrain-scale refinement
- default-pass accessible terrain uses `terrain_groups` or `terrain_domains`
  without mutating child ski-area facts
- distance meters and access mode map to stay-base access factors
- trust state caps ranking influence
- grouping analysis identifies duplicate destination or shared-domain result
  slots without changing production `/api/search`

### Golden Recommendation Tests

Protect ranking behavior with representative scenarios:

- beginner-friendly resort beats advanced-only resort despite weaker snow
- large high-altitude terrain beats small low-altitude terrain for advanced
  spring trips
- low-trust quality labels cannot dominate better source-backed snow and terrain
  fit
- preference-activated factors do not affect ranking unless requested

### Catalog Audit Checks

Extend audit or validation so the current catalog shows:

- required core factor inputs or explicit missing states
- high-impact estimated fields in cleanup output
- major climatology holes
- source refs for source-backed statuses

### Source And Acquisition Checks

Keep acquisition safe:

- LLM output remains proposal-only.
- Source-backed statuses require external source refs.
- Regional IDs are validated only where relevant to configured sources.
- Conflicting source proposals remain review artifacts.

## Rollout

1. Write and approve this resort fit model spec.
2. Add factor policy and tests without materially changing ranking behavior.
3. Derive factors for the current 26 destinations and compare ranking output.
4. Add diagnostic support for default-pass accessible terrain and grouping
   analysis before judging the candidate model.
5. Adjust ranking weights, grouping semantics, and user-facing labels only after
   comparison.
6. Expand acquisition to fill the highest-impact missing factor inputs.
7. Revisit persistence only if acquisition volume or runtime performance makes
   catalog-derived computation insufficient.

## Open Follow-Up Decisions

These should be owner-reviewed during implementation planning:

- Exact factor registry representation: Python policy dataclasses, catalog JSON
  metadata, or a separate generated artifact.
- Whether trust state remains only in `resort_trust_manifest.json` or gets a
  companion factor-trust manifest.
- Initial terrain-scale thresholds.
- Initial skill-fit derivation thresholds.
- Initial stay-base access buckets for walk, ski bus, and car-required cases.
- Whether diagnostic terrain should prefer selected ski-area terrain,
  default-pass accessible terrain, or user-selected pass terrain when those
  differ.
- Whether production search should group by destination, shared terrain domain,
  or a hybrid result key for linked domains and multi-ski-area destinations.
- What comparison diagnostics are required before a later ranking-integration
  checkpoint can change production ranking behavior.
