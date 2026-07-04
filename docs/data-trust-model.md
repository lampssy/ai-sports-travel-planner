# Data Trust Model

Snowcast recommendations are useful only when catalog facts and evidence labels
are honest. This document defines the trust contract for the normalized static
catalog.

## Canonical Catalog

app/data/catalog.json is the only static catalog source. It is validated as an
immutable CatalogSnapshot with these independent entity types:

- ski_regions: trip-market and regional-network umbrellas;
- stay_destinations: bookable town/destination contexts;
- stay_bases: accommodation zones owned by one stay destination;
- ski_areas: independent terrain and weather-evidence entities;
- ski_area_access: explicit sourced stay-base-to-ski-area relationships;
- terrain_domains: ski-connected aggregates over at least two ski areas;
- lift_pass_products: ticket availability, coverage, prices, and optional
  pass-accessible aggregate terrain; and
- rental_display_facts: reviewed equipment-rental examples.

Catalog relations are explicit. Destination nesting does not imply ski access,
pass validity does not imply physical connectivity, and aggregate metrics are
not copied to child ski areas without child-scoped evidence.

Every active stay base and ski area must participate in at least one access
edge. Every access edge requires a direct external source URL. A terrain domain
requires at least two distinct ski-area members and source URLs supporting
connectivity and populated aggregate metrics.

Weather evidence is owned only by ski_area_id. Catalog bootstrap soft-retires
missing entities and preserves weather rows; destructive database reset is an
explicit development/test operation.

The catalog and trust manifest use coordinated schema version `2`. Mixed
catalog/trust versions are invalid.

Feature presence uses `AvailabilityStatus`; stay-base structure and character
use `BaseType` and `BaseCharacterFact`; local and ski-day apres use
`ApresProfileFact`. These catalog values are typed independently of their trust
status and evidence.

## Trust Manifest

app/data/resort_trust_manifest.json mirrors every catalog entity exactly. Its
entity namespaces and field groups are contract-defined:

- ski_regions: identity, membership context;
- stay_destinations: `identity_location`, `coordinates`, `price_level`;
- stay_bases: `identity_ownership`, `coordinates`, `elevation`,
  `lodging_price_quality`, `base_type`, `base_character`, `local_apres`;
- ski_areas: `identity_coordinates`, `elevation_season`, `terrain_metrics`,
  `skill_fit`, `snowmaking`, `glacier_terrain`, `snow_park`, `night_skiing`,
  `marked_freeride_routes`, `ski_day_apres`, `official_documents`;
- ski_area_access: relationship, access mode/distance;
- terrain_domains: `membership_connectivity`, `aggregate_terrain`, `season`,
  `official_documents`;
- lift_pass_products: identity/scope/availability, coverage, prices,
  pass-accessible terrain; and
- rental_display_facts: identity/ownership, price/quality/access.

Each field group has one status:

- verified: directly supported without meaningful normalization;
- verified_with_adjustment: source-backed but normalized for Snowcast's model;
- estimated: useful curated estimate that must not be presented as verified;
- needs_source: unresolved or weakly supported.

Independently sourced facts have independent statuses. Every field group owns a
validated `field_source_refs` list, and evidence on one group does not satisfy
another. `verified` and `verified_with_adjustment` require at least one direct
external URL on that exact group. catalog.json, internal reports, PR
descriptions, and generated artifacts are edit/review history, not independent
evidence.

An `unavailable` feature value requires an authoritative statement or a
reviewed complete inventory explicitly scoped to the owning entity, feature,
and applicable season. Failure to find a feature means `unknown`, not
`unavailable`. Qualitative normalization such as character or apres normally
uses `verified_with_adjustment` because a source statement is mapped into a
controlled Snowcast vocabulary.

Season labels stay with catalog values because they qualify the meaning of the
fact. Retrieval context, source URLs, verification status, and normalization
notes stay in the trust manifest and curation artifacts.

The version-2 cutover is proved by a typed migration report containing canonical
before/after hashes for both catalog and trust payloads. Reconciliation reruns
the deterministic transforms and requires exact payload and report equality.

## Source Policy

Prefer sources in this order:

1. official operator, destination, ticket, or season source;
2. authoritative open data such as OSM/Wikidata for scoped identity/geometry;
3. specialist secondary corroboration.

Bergfex is not primary catalog truth. It may corroborate a static metric when
official sources conflict after scope, season, and wording are checked. Such a
value uses verified_with_adjustment and the report must show the conflict and
normalization.

Do not use internal Snowcast documents as evidence. Do not promote LLM output to
catalog truth. AI may help research, but the curation report must link the
actual external source reviewed by the owner.

## Scope Rules

- Ski-area terrain totals belong to a ski area only when a child-level source
  supports them.
- Domain totals and pass-accessible totals remain aggregates even when they do
  not equal the arithmetic sum of child facts from different source scopes.
- Pass availability and defaults are explicit per stay destination.
- A regional-network pass may reference modeled terrain but does not create a
  terrain domain unless the member areas are physically ski-connected.
- Stay-base lodging estimates and rental examples are separate.
- Stay-base elevation, structural type, character, and local apres remain
  independent facts. A ski area's ski-day apres does not imply the stay base's
  local profile.
- Snowmaking percentages retain their published denominator basis. Cannon
  counts and broad marketing claims do not establish coverage.
- Glacier terrain, snow parks, night skiing, and marked freeride routes require
  evidence scoped to the modeled ski area; nearby or pass-accessible features
  are not copied across ownership boundaries.
- Official trail maps belong to the ski area they describe, or to a terrain
  domain only when the document is genuinely aggregate.
- A full curation review must record `access_mode=unknown` as unresolved.
- The API stars field means internal lodging quality tier, not hotel stars.
- Current open lifts/pistes, snow depth, and disruption status are operational
  observations with freshness; they do not belong in this static catalog.

## Curation Reports

Material catalog changes use a typed CatalogCurationReport. A report must:

- declare every reviewed entity;
- classify every applicable canonical field as changed, reviewed-no-change,
  unresolved, or not-applicable;
- show before/after values for changes;
- link direct evidence with source title/type and an evidence summary;
- record normalization notes;
- assess destination boundaries and weather request geometry when relevant;
- state ranking impact for ranking-relevant changes; and
- list unresolved caveats without hiding them in prose.

Reconciliation compares base and current catalog plus trust manifest. Declared
changes must exactly match actual deltas. An access-edge change also requires
review of both its stay-base and ski-area endpoints.

Default batching is one stay destination per PR. A user-requested batch may
contain up to three related destinations; a larger batch is reserved for one
closely connected domain migration.

## Derived Fit Factors

Raw catalog facts are converted into policy-owned factors:

- terrain_scale from source-scoped ski-area or connected-domain terrain;
- skill_fit_profile from reviewed skill support and difficulty evidence; and
- stay_base_access from the explicit SkiAreaAccess edge.

Each factor carries trust and lifecycle state. Missing or partially derived
facts can cap or disable ranking contribution. Pass fit currently chooses a
pass; pass fit and resilience do not add Search V3 score components.

## Conditions Trust

availability_status is weather-derived unless provenance explicitly says
reported. It is not official lift status.

Planning evidence profiles are:

- forecast_assisted;
- archive_backed; and
- fallback_heavy.

Current conditions, condition history, raw archive weather, and derived
climatology remain keyed by ski_area_id. Display names are not durable evidence
keys.

## Validation

Validate the canonical graph and trust manifest:

    UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog \
      --catalog-path app/data/catalog.json \
      --trust-manifest-path app/data/resort_trust_manifest.json

Validate and render a curation report:

    UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
      typed docs/catalog-curation/REPORT.json \
      --markdown-output docs/catalog-curation/REPORT.md

Reconcile a report against a base checkout:

    UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
      reconcile docs/catalog-curation/REPORT.json \
      --base-catalog-path BASE/app/data/catalog.json \
      --current-catalog-path app/data/catalog.json \
      --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json \
      --current-trust-manifest-path app/data/resort_trust_manifest.json
