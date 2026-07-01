# Feature Spec: Trip-Market Catalog And Search Model

## Status

- Status: accepted 2026-07-01
- Owner: solo-builder
- Related docs:
  - `docs/domain-language.md`
  - `docs/planning-model.md`
  - `docs/data-trust-model.md`
  - `docs/snow-evidence-model.md`
- Related plans:
  - `docs/superpowers/plans/2026-07-01-trip-market-catalog-rollout.md`
  - `docs/superpowers/plans/2026-07-01-normalized-catalog-contract.md`
  - `docs/superpowers/plans/2026-07-01-normalized-catalog-persistence.md`
  - `docs/superpowers/plans/2026-07-01-search-v3-trip-market-ranking.md`
  - `docs/superpowers/plans/2026-07-01-trip-market-client-cutover.md`
- Related ADRs:
  - `docs/architecture/adr/0005-catalog-scope-model.md`
  - `docs/architecture/adr/0006-shared-terrain-domains.md`
  - `docs/architecture/adr/0007-ski-area-weather-evidence-and-catalog-retirement.md`
  - `docs/architecture/adr/0008-destination-and-ski-area-boundaries.md`
  - `docs/architecture/adr/0009-normalized-trip-market-catalog.md`

## User Outcome

Snowcast should rank distinct ski-trip markets without filling the result list
with several configurations from the same valley. Each result should still be
grounded in a concrete choice: where to stay, which ski area is the weather and
skiing focus, how that base reaches the area, and which pass best fits the trip.

For example, a result may be headed `Chamonix Valley` while its winning
configuration says `Stay in Argentiere - ski Grands Montets`. The score and
weather explanation come from that concrete configuration. Alternative bases,
ski areas, and pass choices remain available inside the result rather than
occupying duplicate global result slots.

## Scope

In scope:

- Normalize the static catalog around independent stay, ski, access, terrain,
  pass, and user-facing region entities.
- Narrow `Destination` into `StayDestination`, a stay and arrival market that
  does not own ski areas.
- Store `StayBase` independently while retaining exactly one owning
  `StayDestination` reference.
- Store `SkiArea` independently and keep it as the durable owner of weather,
  climatology, and future operational evidence.
- Add explicit many-to-many `SkiAreaAccess` links from stay bases to ski areas.
- Add `SkiRegion` for familiar user-facing umbrellas and distinguish
  result-grouping trip markets from contextual regional networks.
- Retain current rental display facts under explicit stay-destination ownership
  without making them part of recommendation identity.
- Generalize connected aggregate terrain under `TerrainDomain`, regardless of
  whether member ski areas share a stay destination or cross destinations.
- Keep `LiftPassProduct` as the commercial entitlement and price entity.
- Generate and score concrete `TripConfiguration` values at runtime, then group
  them into distinct `RecommendationGroup` results.
- Make the recommended pass part of the configuration while keeping meaningful
  pass alternatives nested in its dossier.
- Introduce the new response and ranking behavior as `search_v3` behind the
  existing model-version switch and private debug override.
- Keep initial `search_v3` global scoring equivalent to the current `search_v2`
  policy after adapting factor ownership to the normalized graph. Pass fit
  chooses the recommended product and resilience is measured/displayed, but
  neither changes global ranking until a future scoring-model checkpoint.
- Update backend, web, mobile, public-page, handoff, and companion contracts to
  the new model in one coordinated pre-public cutover.
- Replace the nested catalog authoring shape with one normalized, Pydantic-
  validated `catalog.json` plus the separate trust manifest.
- Migrate catalog persistence non-destructively while preserving stable ski-area
  weather identities and existing archive/climatology rows.
- Update catalog curation and review guidance to reason about linked stay
  destinations, ski regions, access links, passes, and terrain domains before
  treating a curation as isolated.

Out of scope:

- Live or predicted open-lift, open-piste, snow-coverage, or accessible-kilometer
  snapshots.
- Hotel/property inventory, amenities, price availability, or property-level
  ranking.
- Automatic pass purchasing or booking inventory.
- Blended region-level weather or synthetic terrain-domain climatology.
- Backward compatibility for old API clients, old search implementations, or
  disposable pre-public saved/current-trip rows.
- A general-purpose catalog administration application.
- Splitting the source catalog into many files while one-file authoring remains
  convenient for the solo owner.

## Product Fit

- Results begin with a familiar ski-trip market but remain auditable down to the
  exact stay-base, ski-area, access, pass, and weather evidence that earned the
  rank.
- One trip market occupies at most one global result slot, preventing a large
  valley from crowding out materially different destinations.
- Local and broad pass options can affect fit without turning search into a pass
  price comparison tool.
- Weather uncertainty remains ski-area-specific. A regional label never implies
  weather evidence that was not collected for its member areas.
- The model leaves explicit extension points for future operational predictions
  and accommodation properties without putting volatile data into the static
  catalog.

## Domain Model

Bounded contexts touched:

- catalog and data trust;
- conditions and weather evidence;
- planning and ranking;
- companion/saved-trip identity;
- acquisition and curation review.

### Persistent Catalog Entities

| Entity | Responsibility | Key invariants |
| --- | --- | --- |
| `SkiRegion` | Familiar user-facing umbrella and result-group context. | Has `grouping_policy=trip_market` or `regional_network`. It owns neither weather nor a rank. Trip-market regions may sit below contextual regional-network parents. |
| `StayDestination` | Stable accommodation, arrival, booking-search, and broad local-atmosphere market. | Owns no ski terrain or weather. Has one or more stay bases and exactly one `trip_market_region_id`. Transitional APIs may continue to expose `resort_id` while the migration is active. |
| `StayBase` | Exact village, neighborhood, or lodging zone used for price, quality, atmosphere, and lift-access fit. | Has one stable `stay_base_id` and exactly one `stay_destination_id`. It is stored as a top-level catalog record rather than nested JSON. |
| `SkiArea` | Smallest durable skiable terrain unit that merits independent weather or operational evidence. | Has a stable `ski_area_id`. Archive weather, climatology, current conditions, and future operational evidence remain keyed to it. It is not owned by a stay destination. |
| `SkiAreaAccess` | Source-backed relationship describing how one stay base reaches one ski area. | References valid base and area IDs and records access mode, representative distance/time, directness, and evidence. Candidate generation may use only explicit active access links. |
| `TerrainDomain` | Aggregate facts for physically ski-connected member ski areas. | Owns aggregate terrain metrics and connectivity evidence, never weather. It may be destination-local or cross-destination. Pass validity without physical ski connectivity does not create a domain. |
| `LiftPassProduct` | Commercial product describing sale context, terrain entitlement, reviewed representative prices, and optional pass-accessible aggregate terrain published for non-connected coverage. | Availability/default relationships reference stay destinations; coverage separately references ski areas and/or terrain domains. Pass-scoped aggregate metrics are labeled `pass_accessible` and are not copied to member areas. It owns no weather. Local and broad products may coexist; one configuration selects one recommended product and retains alternatives. |
| `RentalDisplayFact` | Curated rental-shop or representative equipment-price context used in the dossier. | References one stay destination and optionally one stay base. It is not live inventory, a ranking identity, or part of the candidate key. |

`TerrainGroup` becomes unnecessary in the target model. Existing destination-
local connected groups migrate to `TerrainDomain`. A non-connected aggregate
published specifically for one pass, such as Chamonix Le Pass terrain, migrates
to that `LiftPassProduct` as explicitly labeled pass-accessible metrics.
User-facing grouping migrates to `SkiRegion`.

### Catalog Field Ownership

| Fact | Canonical owner |
| --- | --- |
| Country, broad arrival geography, booking-market identity, broad atmosphere | `StayDestination` |
| Lodging price/quality estimate, local atmosphere, precise village/zone coordinates | `StayBase` |
| Nearest lift, representative access distance/time, walk/shuttle/drive mode, directness | `SkiAreaAccess` |
| Terrain size, local lift count, elevations, season windows, difficulty mix, skiing skill fit | `SkiArea` |
| Connected aggregate piste/lift metrics | `TerrainDomain` |
| Pass availability/default stay markets, coverage, validity scope, duration, age band, representative reviewed price, and non-connected pass-accessible aggregate metrics | `LiftPassProduct` |
| Familiar result label and trip-market/regional hierarchy | `SkiRegion` |
| Curated equipment rental context | `RentalDisplayFact` |

The same fact must not be copied across owners for convenience. APIs may project
owned facts into a configuration or dossier, but the catalog keeps one canonical
source location.

### Stay-Destination Boundary

`StayDestination` answers `where is the broad accommodation and arrival
market?`; `StayBase` answers `where within that market would the user actually
stay?`.

A place is a separate stay destination when it has a stable bookable identity,
meaningful accommodation inventory or base choices, and independent value in
travel effort, price, atmosphere, or local mobility. It no longer needs to own
or uniquely identify a ski area. Ski access is evaluated separately through
`SkiAreaAccess`.

Every active stay destination references exactly one primary ski region whose
policy is `trip_market`. The selected stay destination therefore determines the
configuration's single top-level grouping key. A stay destination or its trip
market may also appear under contextual `regional_network` regions, but those
memberships never create or collapse ranked result slots. A ski area can support
configurations in more than one trip market when explicit access links make that
terrain realistically reachable from different stay destinations.

Examples:

- Tignes is a stay destination; Val Claret, Le Lac, and Les Brevieres are stay
  bases.
- Val d'Isere is a stay destination; La Daille and Le Fornet are stay bases.
- Chamonix Valley can be a trip-market ski region while concrete stay
  destinations and bases below it retain their own booking and access identity.

### Runtime Planning Entities

`TripConfiguration` is the concrete scored planning choice. It contains:

- trip-market ski-region context;
- stay destination and selected stay base;
- focus ski area and its access link;
- selected pass and meaningful pass alternatives;
- static accessible-terrain context;
- requested dates or month;
- primary ski-area weather/planning evidence;
- optional pass-wide resilience derived from member ski-area evidence;
- travel, budget, terrain, skill, and access fit factors;
- score components, evidence quality, and explanation.

`RecommendationGroup` is the top-level search object. It contains:

- one trip-market region label and grouping key;
- the winning trip configuration;
- materially useful alternative configurations;
- a score inherited from the winner rather than averaged across the region.

It is generated at runtime and is not another persisted catalog entity.

### Weather And Conditions

Primary conditions fit is computed only from the selected focus ski area's
weather, archive, climatology, and season evidence. This remains a major ranking
factor and is the evidence shown most prominently on the result card.

Pass-wide or access-wide resilience is separate contextual evidence. It may
summarize whether alternative member ski areas provide useful fallback terrain,
but every contribution retains its own ski-area evidence and freshness. It is
displayed but has zero global ranking weight in `search_v3`; the model must not
average member observations into fictional region weather.

Future live and predicted operational data should use time-indexed snapshots
keyed by `ski_area_id`. Static pass-accessible terrain and predicted terrain
available for selected dates remain different concepts.

### Candidate Generation And Ranking

Search must:

1. Load the validated active catalog graph and request-scoped conditions data.
2. Begin with explicit active `SkiAreaAccess` links rather than calculating a
   stay-base by ski-area Cartesian product.
3. Generate only pass variants whose modeled coverage includes the focus ski
   area or its connected domain and whose availability includes the selected
   stay destination.
4. Score each base/area configuration using the existing `search_v2` global
   components adapted to their new canonical owners: primary conditions, snow
   evidence, stay and access fit, travel effort, terrain fit, budget fit, and
   evidence quality.
5. Evaluate pass variants with a separate pass-fit comparison, select one
   recommended product, and retain meaningful alternatives. Pass fit does not
   add to the global configuration score in `search_v3`.
6. Derive pass-wide/access-wide resilience as measured explanation data without
   adding it to the global configuration score in `search_v3`.
7. Group configurations by their primary `trip_market` ski region.
8. Rank distinct recommendation groups by their winning configuration.

Accommodation properties, rentals, and other add-ons do not form candidate
identity and cannot create duplicate global result slots.

### Future Extension Boundary

The model intentionally allows later additions without changing recommendation
identity:

- `SkiAreaOperationalSnapshot` or predictions keyed by ski area and validity
  window for open lifts, pistes, snow coverage, and expected accessible terrain;
- `AccommodationProperty` under a stay base for amenity and availability fit;
- additional typed factors and evidence payloads interpreted from AI-assisted
  search preferences.

These are separate volatile or provider-backed contexts, not fields copied into
the static catalog.

## Decision And Review Gate

- Classification: review-gated, full design flow
- High-risk domains touched: catalog identity, database persistence, historical
  weather preservation, ranking/grouping semantics, API contracts, source trust,
  and future catalog maintenance.
- Developer Decision Checkpoints:
  - resolved:
    - show one familiar trip-market result with a concrete winning
      configuration and nested alternatives;
    - use the winning configuration score rather than blended region weather or
      score;
    - keep ski area as the sole durable weather-evidence owner;
    - narrow destination to an independent stay market and connect stay bases to
      independent ski areas through explicit access links;
    - persist ski regions with separate trip-market and regional-network
      grouping policies;
    - treat pass choice as part of the configuration, with one recommended pass
      on the result and detailed alternatives in the dossier;
    - keep one normalized catalog source file for the solo editor;
    - migrate through non-destructive upsert/retirement semantics and preserve
      stable ski-area weather IDs;
    - preserve the current global scoring policy for `search_v3`; use pass fit
      only for pass selection and keep resilience measured-not-ranked until a
      future model version;
    - defer operational predictions and accommodation properties while retaining
      explicit extension points.
  - accepted assumptions: none
  - unresolved: none
- ADR status: `0009` drafted with this spec
- Advisory design review:
  - reviewers: Product / Strategy, Backend / API, Data Trust & Source
    Integrity, UI / UX, Security & Privacy, and Observability / Ops
  - status: completed 2026-07-01 through the Snowcast core panel; no remaining
    Blocker or High findings after API-cutover, persistence, field-ownership,
    and source-versioning remediation
- Advisory feature review before final handoff:
  - reviewers: selected from the same core concerns and adjusted to the final
    implementation scope
  - status: planned

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Product / Domain | Top-level result identity | Controls duplicate results and the user's mental model. | Place-first; configuration-first; trip-market group with concrete winner. | Trip-market group with concrete winner. | Preserves familiar place context without hiding the scored skiing/stay choice. | This spec and ADR 0009 |
| Mixed | Stay and ski ownership | Controls catalog consistency, access, weather identity, and migration complexity. | Destination-owned ski areas; independent stay and ski graphs. | Independent graphs joined by access links. | Adds explicit relationships but removes false ownership and Cartesian candidates. | This spec and ADR 0009 |
| Product / Domain | Pass presentation | Controls terrain/value fit and result duplication. | Ignore pass; separate results per pass; nested pass variants. | Recommended pass with nested alternatives. | Keeps pass value useful without making Snowcast primarily a tariff comparator. | This spec |
| Technical | Authoring storage | Controls solo curation ergonomics and future migration. | Nested current file; normalized single file; sharded files; authoring database. | Normalized single file with typed snapshot boundary. | Best current simplicity; storage can change later without changing domain semantics. | This spec and ADR 0009 |
| Technical | Rollout | Controls history safety without preserving unused pre-public contracts. | Dual compatibility model; coordinated clean cutover. | Coordinated clean cutover that preserves ski-area evidence only. | Removes compatibility overhead; rollback across the schema boundary requires restoring the matching database backup and application image together. | Implementation plan |
| Product / Domain | Initial scoring impact | Controls whether ontology and score changes can be evaluated separately. | Preserve global weights; add small pass/resilience weights; fully retune. | Preserve `search_v2` global scoring semantics in `search_v3`; pass fit selects the product and resilience stays measured-not-ranked. | Isolates the catalog/grouping change and reserves new ranking effects for a future model version. | Search v3 implementation plan |

## Architecture Decisions

- Durable decisions made:
  - separate catalog identity from physical catalog storage;
  - normalize stay destinations, bases, ski areas, access links, regions,
    domains, and passes under one typed catalog snapshot;
  - use the database as the runtime source and JSON as reviewed authoring truth;
  - generate trip configurations from explicit graph edges;
  - group and rank trip-market recommendation groups by their winning concrete
    configuration;
  - retain weather ownership at ski-area level.
- ADRs needed: ADR 0009 records this target and supersession boundaries.
- Existing ADRs that constrain this feature: ADRs 0005-0008.
- Revisit criteria:
  - one-file authoring becomes materially difficult;
  - provider-backed operational data requires a dedicated service boundary;
  - property inventory becomes a first-class planning surface;
  - trip-market grouping proves too coarse or unstable in user evaluation.

## API And Client Contract

`search_v3` should return `RecommendationGroup` records containing:

- region ID, name, grouping policy, rank, and winner-derived group score;
- `top_configuration`;
- bounded `alternative_configurations`.

Each configuration should expose stable IDs and display names for its stay
destination, stay base, focus ski area, access link, selected pass, and
alternative passes, plus accessible-terrain context, primary conditions,
resilience, evidence quality, score components, and explanation.

The search card should show:

- the trip-market name as the familiar headline;
- the concrete stay-base and focus-ski-area choice;
- one recommended pass/access summary;
- primary selected-area weather and evidence seasons;
- a small indication that alternatives exist.

The dossier should compare alternative bases, ski areas, and meaningful pass
products while keeping evidence scoped to each ski area.

Saved trips should persist stable IDs for the region, stay destination, stay
base, focus ski area, selected pass, and dates. The pre-public migration may
clear and reseed existing saved/current-trip rows rather than preserving their
old resort-shaped identity.

`/api/search` moves directly to the structured `RecommendationGroup` contract;
backend, web, and mobile update together. The search-context dossier moves from
destination-only identity toward recommendation-group/region plus selected-
configuration identity. Public resort pages and accommodation handoffs are
updated to use stay-destination identity in the same cutover. Introducing public
ski-region pages remains a separate SEO/product decision and is out of scope.

The search-model selection mechanism remains, but `search_v1` and `search_v2`
are retired because their candidate and response contracts depend on the old
catalog topology. `search_v3` becomes the first model on the normalized graph.
Future compatible scoring candidates such as `search_v4` can again use the
global switch and gated private override without changing catalog identity or
the API shape.

## Data Trust And Source Integrity

- Static catalog values remain human-reviewed and evidence-backed through the
  trust manifest and typed curation reports.
- `catalog.json` carries an explicit `schema_version`; unsupported versions fail
  before parsing or synchronization.
- Access links require provenance for representative origin/endpoint,
  distance/time calculation, access mode, and directness.
- Trip-market region membership requires reviewed evidence that configurations
  are realistic substitutes in one holiday, arrival, and local-mobility market;
  a shared pass alone is insufficient.
- Terrain-domain membership requires physical ski connectivity evidence.
- Pass coverage and prices require product-scoped official or accepted fallback
  evidence.
- Missing or conflicting evidence remains unresolved or review-only; it must not
  be synthesized by candidate generation.
- Catalog review must inspect linked destinations or areas mentioned by passes,
  domains, region membership, access relationships, or source material.

## AI / LLM Use

- Catalog validation, relationship integrity, candidate generation, weather
  ownership, ranking, grouping, and migration are deterministic.
- LLMs may parse user preferences into typed filters/factor priorities and may
  produce grounded explanations from deterministic results.
- LLM output cannot create catalog relationships, evidence, scores, pass
  coverage, or grouping membership without human-reviewed curation.
- Existing prompt, caching, fallback, and privacy boundaries remain in force.

## Background Work

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| Deploy or explicit catalog sync | Validate `CatalogSnapshot`; upsert active entities and relationships; retire missing catalog entities | Existing bootstrap/sync command | Must not delete archive, climatology, or condition history. |
| Scheduled/manual weather jobs | Refresh, backfill, or rebuild evidence for active ski-area IDs | Existing weather workers | No region/domain weather rows are introduced. |

## Security, Privacy, And Abuse

- No new user-sensitive data is required for the static catalog migration.
- New saved trip IDs and dates follow existing companion/session privacy rules.
- Raw trip briefs, prompts, and user preference text remain excluded from logs,
  metrics, and traces.
- Debug search-model overrides retain their existing private feature gate.

## Observability And Operations

- Catalog sync logs inserted, updated, retired, and rejected entities by bounded
  type counts, not unbounded source payloads.
- Validation failure prevents partial catalog synchronization.
- Sync is transactional and idempotent.
- Search telemetry records selected model version and bounded group/configuration
  counts so duplicate-group regressions are visible.
- Weather coverage dashboards remain ski-area-based.
- Destructive full database reset remains a separate explicit operator action.

## Migration Strategy

1. Add the normalized Pydantic catalog models and convert the current static
   data into one validated snapshot without changing stable ski-area IDs.
2. Add normalized persistence for ski regions, stay destinations, stay bases,
   independent ski areas, access links, terrain domains, and pass products. The
   long-term schema uses an explicit `stay_destinations` table rather than
   preserving `resorts` as the canonical name.
3. Migrate the existing `ski_areas` records in place or through a transactional
   ID-preserving table replacement so every weather-backed `ski_area_id` remains
   unchanged. Rename legacy evidence keys called `resort_id` to `ski_area_id`
   without moving rows. Keep archive weather, climatology, current conditions,
   and condition-history snapshots attached to those IDs.
4. Clear and recreate disposable pre-public saved/current-trip and other
   resort-shaped demo state under the new schema. Update backend, web, mobile,
   public pages, and handoff routes to the new IDs and response contract.
5. Synchronize catalog changes by transactionally upserting current records and
   marking absent catalog records inactive. Never cascade-delete historical
   weather, climatology, current conditions, or condition-history snapshots.
6. Cut over to `search_v3` and retire old catalog/search compatibility code.
7. Verify the complete application and evidence counts before deployment. Take
   a database backup first; rollback across this cutover restores the matching
   pre-migration database and application image together rather than running an
   old image against the new schema.

Renames retain stable IDs. Splits and merges create or retire explicit IDs and
require owner-reviewed weather evidence migration or a new backfill; catalog
sync never silently moves history between ski areas.

## Acceptance Criteria

- A versioned validated catalog snapshot can represent independent stay
  destinations, stay bases, ski areas, access links, ski regions, terrain
  domains, passes, and rental display facts.
- Every reference is validated and duplicate or orphan IDs fail before database
  writes.
- A stay base belongs to exactly one stay destination but can access multiple ski
  areas through explicit links.
- A ski area can be accessed from multiple stay bases or stay destinations and
  retains one stable weather identity.
- Candidate generation does not produce combinations without an access link or
  compatible pass.
- Pass variants for one base and focus area do not become duplicate top-level
  results.
- Pass availability and pass terrain coverage are validated separately, so a
  product sold for one stay market is not automatically offered from every
  destination touching the same terrain domain.
- Pass fit deterministically selects and explains a recommended product without
  changing the `search_v3` global configuration score.
- Resilience is returned as measured explanation data but contributes zero to
  the `search_v3` global configuration score.
- Pass-accessible aggregate metrics for non-connected terrain remain pass-scoped
  and cannot be treated as a physical terrain domain or copied to ski areas.
- At most one result per primary trip-market grouping key occupies the ranked
  list; its score equals its winning configuration score.
- Every active stay destination references exactly one valid `trip_market`
  region; contextual regional-network membership cannot change grouping.
- Primary weather and evidence-season wording identify the selected focus ski
  area and never imply blended region weather.
- Terrain domains and ski regions own no archive, climatology, or condition rows.
- Normal catalog sync preserves all historical weather, climatology,
  current-condition, and condition-history rows and retires missing catalog
  entities non-destructively.
- Existing ski-area current conditions remain attached to unchanged area IDs or
  can be safely refreshed without affecting archive/climatology preservation.
- Backend, web, mobile, public pages, handoffs, and newly seeded saved trips use
  the new IDs and structured group contract after the coordinated cutover.
- The model-selection mechanism accepts `search_v3` and remains ready for future
  compatible model versions; retired versions are rejected explicitly.
- Curation and review contracts cover region membership, access links, domain
  connectivity, pass coverage, rental ownership, stable IDs, and linked catalog
  entities.

## Verification

- Unit tests:
  - catalog snapshot invariants and cross-reference failures;
  - access-driven candidate generation;
  - pass selection/collapse;
  - trip-market grouping and winner score inheritance;
  - primary conditions versus resilience evidence scope;
  - non-destructive retirement behavior.
- API/integration tests:
  - `search_v3` response and retired-version rejection;
  - debug override authorization;
  - catalog sync idempotency and transaction rollback;
  - preserved archive, climatology, and current-condition rows across catalog
    reshaping;
  - clean recreation of saved/current-trip demo state under new IDs.
- UI/manual checks:
  - Chamonix-style multi-area market;
  - Tignes-Val d'Isere-style connected cross-destination terrain;
  - local versus broader pass choices;
  - one global slot per trip market with inspectable alternatives.
- Operational checks:
  - deploy/bootstrap dry run and entity counts;
  - weather coverage remains stable by ski-area ID;
  - old search model remains selectable during rollout.

## Advisory Review

- Design reviewers: core-panel review completed 2026-07-01 by Product / Strategy,
  Backend / API, Data Trust & Source Integrity, UI / UX, Security & Privacy, and
  Observability / Ops.
- Findings remediated in this draft:
  - replaced an unnecessary dual compatibility model with a coordinated
    pre-public cutover while preserving ski-area evidence;
  - made trip-market membership and API identity deterministic;
  - added explicit catalog field ownership, rental-fact ownership, and catalog
    schema versioning;
  - added backup and matched application/database rollback requirements.
- Remaining Blocker or High findings: none.
- Feature reviewers: planned before implementation handoff.
- Known residual risks:
  - catalog-wide migration may expose ambiguous stay-destination and trip-market
    boundaries requiring explicit owner decisions;
  - access evidence may initially be incomplete, reducing candidate coverage;
  - the coordinated cutover requires full backend/web/mobile verification and a
    matching pre-migration database backup because mixed old/new versions are
    intentionally unsupported;
  - resilience weighting and pass-value weighting remain later scoring-policy
    checkpoints for a future model version rather than being mixed into
    `search_v3`.
