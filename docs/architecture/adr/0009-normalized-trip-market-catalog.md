# ADR 0009: Normalize The Catalog Around Trip Markets And Access Links

Status: accepted
Date: 2026-07-01

Supersedes:
- ADR 0005's destination ownership of lift-pass products and terrain groups.
- ADR 0006's requirement that a terrain domain cross destination boundaries.
- ADR 0008's use of `Destination` as both the stay and top-level recommendation
  boundary.

Superseded by: N/A

Related specs:
- `docs/superpowers/specs/2026-07-01-trip-market-catalog-and-search-design.md`

Related docs:
- `docs/domain-language.md`
- `docs/planning-model.md`
- `docs/data-trust-model.md`
- `docs/snow-evidence-model.md`
- `docs/architecture/adr/0016-require-evidence-owner-boundaries-for-ski-areas.md`
- `docs/architecture/adr/0018-require-independent-stay-market-boundaries.md`

## Context

The current catalog nests stay bases, ski areas, passes, and terrain groups
under destinations. Search then evaluates destination-owned stay-base and
ski-area combinations and groups results by destination plus ski area.

That model combines several different boundaries:

- where a user searches for accommodation and arrives;
- which terrain owns weather and operational evidence;
- which stay base can realistically access which terrain;
- which connected terrain a pass exposes;
- which familiar valley or holiday market should occupy one result slot.

The overlap works for a simple one-town, one-area resort but becomes ambiguous
for Chamonix-style valleys, Tignes-Val d'Isere-style connected terrain,
destination-local multi-area groups, and passes spanning both connected and
external terrain. It also permits candidate combinations that are implied by
nesting rather than supported by an explicit access relationship.

Snowcast needs independent stable identities for stay, ski evidence, access,
connected terrain, commercial entitlement, and user-facing result grouping.
The solo catalog owner also needs a source format that remains simple to curate.

## Decision

Normalize the static catalog into one typed `CatalogSnapshot` containing
top-level records for:

- `SkiRegion`;
- `StayDestination`;
- `StayBase`;
- `SkiArea`;
- `SkiAreaAccess`;
- `TerrainDomain`;
- `LiftPassProduct`;
- `RentalDisplayFact`.

Use one normalized `catalog.json` as the reviewed authoring source while that is
convenient for the solo editor. Keep source/evidence trust in its separate
manifest. Hide physical storage behind a small snapshot-loading boundary so a
future directory, importer, or authoring database can produce the same typed
snapshot without changing domain semantics.

The snapshot has an explicit schema version. Rental display facts reference a
stay destination and optional stay base; they remain curated dossier context and
do not participate in candidate identity.

`StayDestination` owns a complete, independently evidenced accommodation market
with material destination-level separation value, not ski terrain. `StayBase`
belongs to exactly one stay destination. Candidates that do not pass all three
stay-market gates route to stay bases or another normalized entity rather than
becoming overlapping ranked destinations. Every active stay destination belongs
to exactly one primary `trip_market` ski region, which determines the grouping
key for its configurations. Contextual regional-network membership does not
change search grouping. `SkiArea` is independent and remains the stable
weather-evidence identity. Explicit many-to-many `SkiAreaAccess` records connect
bases to areas and carry source-backed access facts. ADR 0018 owns the detailed
stay-destination boundary policy.

Generalize `TerrainDomain` to any physically ski-connected aggregate, including
destination-local domains. Retire `TerrainGroup` from the target model.
`LiftPassProduct` remains the commercial entitlement and price scope. When an
official product publishes aggregate terrain for non-connected pass coverage,
the product may own explicitly labeled `pass_accessible` aggregate metrics;
those values do not create a terrain domain or become child ski-area facts.
Pass availability/default relationships reference stay destinations separately
from ski-area/domain coverage, preventing a product sold in one market from
appearing automatically in every market sharing that terrain.

Add `SkiRegion` as a familiar umbrella. Regions with
`grouping_policy=trip_market` group realistic substitute configurations into one
ranked result. Regions with `grouping_policy=regional_network` provide hierarchy
and context only; a shared pass alone does not collapse all network members into
one result.

Generate concrete runtime `TripConfiguration` values only from explicit access
and pass coverage. Collapse pass variants for the same base and focus ski area,
then group configurations by primary trip market. A runtime
`RecommendationGroup` inherits its score from the winning configuration and
contains alternatives; it is not persisted catalog truth.

Keep primary weather, archive, climatology, current conditions, and condition
history on `ski_area_id`. Rename legacy evidence key columns and model fields
from `resort_id` to `ski_area_id` without rekeying rows. Any pass-wide resilience
calculation remains a derived summary of separate member evidence and does not
create region or domain weather.

Roll the behavior out as `search_v3`. Catalog persistence uses transactional
upsert and inactive retirement semantics. Existing ski-area IDs and all
weather/condition evidence rows are preserved; a destructive rebuild remains
an explicit separate operator action.

Use an explicit `stay_destinations` persistence table as the long-term schema.
Do not retain `resorts` as the canonical database term. Because Snowcast has no
external users, update the backend, web, mobile, public-page, handoff, and saved-
trip contracts in one coordinated cutover instead of maintaining a dual catalog
or API shape. Pre-public saved/current-trip rows may be cleared and reseeded.

Retain the search-model version mechanism for future scoring changes, but retire
`search_v1` and `search_v2` when the old catalog topology is removed.
`search_v3` is the first supported model on the normalized graph. Rollback across
the schema boundary restores a matching database backup and application image;
mixed old/new application and schema versions are intentionally unsupported.

Keep `search_v3` topology-first: adapt the current `search_v2` global score to
the normalized owners without adding pass-value or resilience weight. Pass fit
selects the recommended product, and resilience is measured explanation data.
Any effect from those factors on global ordering requires a later search-model
decision.

## Consequences

The catalog can represent realistic stay-to-ski relationships without forcing a
ski area to belong to one destination. Search no longer needs a base-by-area
Cartesian product, and large valleys no longer occupy several global slots when
their configurations are substitutes inside one trip market.

Weather provenance becomes clearer because the visible region label, accessible
terrain, and pass choice cannot silently broaden the focus ski area's evidence.
Pass value and fallback terrain can influence a concrete trip without becoming
separate duplicate results.

The source file becomes more reference-heavy: editors must follow stable IDs and
explicit links rather than relying on nesting. Typed full-graph validation and
review reports are therefore mandatory before synchronization.

Migration requires a catalog-wide relationship conversion, coordinated backend
and client updates, and owner review of ambiguous region, destination, and access
boundaries. Missing access evidence may initially exclude configurations that
the old Cartesian model produced.

The clean cutover avoids long-lived dual models but gives up mixed-version
rollback. Expensive ski-area evidence remains durable; disposable demo/user state
is recreated under the new model.

One authoring file may eventually become unwieldy. Changing the source later is
limited to the snapshot loader as long as it produces the same validated model.

## Alternatives Considered

- Keep destination-owned ski areas and improve grouping only. This would reduce
  duplicate cards but retain false ownership and inferred access combinations.
- Rank only concrete configurations globally. This is precise but lets several
  variants from one valley crowd out distinct trip markets.
- Rank destinations or regions using blended conditions. This is familiar but
  creates weather semantics unsupported by ski-area observations.
- Make lift passes the primary grouping entity. Passes are useful commercial
  choices but can span disconnected destinations that are not realistic trip
  substitutes.
- Split the catalog into many files or build an authoring database immediately.
  Either can scale later, but both add unnecessary solo-editor overhead now.

## Revisit When

Revisit the authoring format when one normalized file causes material review or
merge difficulty. Revisit trip-market grouping when user evaluation shows that
the configured markets hide materially different holiday choices or still
produce duplicate-looking results. Revisit the static/runtime boundary when
provider-backed operations or accommodation inventory becomes a first-class
planning dependency.
