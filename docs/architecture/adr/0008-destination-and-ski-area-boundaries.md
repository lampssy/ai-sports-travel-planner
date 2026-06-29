# ADR 0008: Define Destination And Ski-Area Boundaries

Status: Accepted
Date: 2026-06-29

Supersedes: N/A
Superseded by: N/A

Related ADRs:
- `docs/architecture/adr/0005-catalog-scope-model.md`
- `docs/architecture/adr/0006-shared-terrain-domains.md`
- `docs/architecture/adr/0007-ski-area-weather-evidence-and-catalog-retirement.md`

Related specs:
- `docs/superpowers/specs/2026-06-29-destination-boundaries-and-connected-terrain-design.md`

Related docs:
- `docs/domain-language.md`
- `docs/superpowers/specs/2026-06-23-static-catalog-curation-skill-design.md`

## Context

Official resort names, pass products, and lift connectivity do not define the
same product boundary. A marketing label may contain several useful trip
choices, while one lift-connected domain may span destinations with different
lodging, access, ticketing, operations, weather, and season timing. Treating
connectivity or marketing identity as destination identity can therefore hide
meaningful recommendations and attach local weather evidence to terrain it does
not describe.

Snowcast needs separate, stable boundaries for the place a user chooses, the
terrain that owns weather and operational evidence, and aggregate connected
terrain.

## Decision

A `Destination` is a recommendation and stay boundary. A candidate is a
separate destination only when all three hard gates pass:

1. **Independent stay context:** users can book a multi-night ski trip under the
   place name and it has meaningful lodging inventory or stay-base choices.
2. **Independent ski access:** the place directly accesses a stable local ski
   area rather than only being a neighborhood inside another base.
3. **Independent recommendation value:** returning the place separately can
   materially change trip fit, such as lodging price, atmosphere, travel effort,
   lift access, local ticket cost, season timing, or weather evidence.

At least one strong source-backed identity signal must also pass: a local
lift-pass product; a separate operator, operating schedule, status feed, or
weather presentation; or official treatment as a resort or destination rather
than only a piste sector, neighborhood, or marketing label. Official naming and
lift connectivity are evidence inputs, not decisive rules by themselves.

A `SkiArea` is the smallest durable terrain unit that merits separate weather or
operational evidence. Lift connectivity does not prevent separate ski areas
when reviewed sources and skier experience show materially distinct access,
operations, ticketing, elevations, weather behavior, or opening schedules.

Cross-destination ski connectivity belongs to `TerrainDomain`. Aggregate domain
facts remain domain-scoped and do not own weather evidence. A shared pass that
covers terrain without ski connectivity remains `regional_network` pass context
and does not create a terrain domain.

Any destination or ski-area split, merge, or ID change is an owner-reviewed
model migration. It must inventory affected ski-area weather identities and
preserve existing archive and climatology on the old ID unless an explicit
reviewed data migration moves or rewrites that evidence. A replacement or new
ski-area identity can be backfilled separately. Catalog reshaping must not
silently reassign or delete weather evidence, and `reset_database()` remains a
separate explicit destructive operator action that is never implied by a split,
merge, or ID change.

The rule applies catalog-wide. `docs/domain-language.md` owns the canonical
failure routing for candidates that do not satisfy the destination boundary.

## Consequences

Recommendation cards remain meaningful stay choices even when their ski areas
share connected terrain. Weather and operational evidence stays local to the
ski area it describes, while `TerrainDomain` can preserve shared terrain scale
without copying aggregate values into child ski areas.

Catalog curation must review destination identity before routine enrichment. A
proposed boundary change stops being a field-edit task and requires explicit
owner review, stable-ID handling, and weather-evidence migration planning.

Some current destinations may need later catalog-wide audit. Existing entries
are not permanently grandfathered, but this ADR does not predetermine which ones
must split or merge.

## Alternatives Considered

- Use the official marketing label as destination identity. Rejected because
  official labels vary in scope and can collapse independently useful trip
  choices.
- Merge destinations whenever their terrain is lift-connected. Rejected because
  connectivity describes ski access, not lodging, recommendation, ticket,
  operational, or weather identity.
- Introduce `SkiSubArea` immediately for every recognizable sector. Rejected
  because named sectors without independent operations do not yet justify a new
  weather or ranking entity. The concept remains parked until a concrete product
  need supports it.

## Revisit When

Revisit if catalog-wide audits show that the hard gates consistently over-split
normal resort villages, or if localized operational-status and access needs make
ski sub-areas a product priority.
