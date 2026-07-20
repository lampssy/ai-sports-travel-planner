# Data Trust Model

Snowcast recommendations are useful only when catalog facts and evidence labels
are honest. This document defines the trust contract for the normalized static
catalog and the provenance boundary between catalog, observed weather,
climatology, and forecast evidence.

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

For `ski_area_access`, the catalog-level `source_urls` list is the entity-level
roll-up of those independent groups. It must equal the set union of
`relationship` and `access_mode_distance` source refs. A URL may support both
groups, but it need not be repeated on a group whose fields it does not support;
catalog-only URLs and trust-only URLs are invalid.

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
- Search V4 terrain summaries preserve the owning manifest field status and
  source scope. A pass summary may retain a ski-area or terrain-domain fallback,
  but the API and UI must not promote that fallback into unqualified
  pass-accessible terrain.
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
- declare focus stay destinations for a deterministic resulting graph in
  current schema-v3 work;
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
facts can cap or neutralize ranking contribution. Search V4 expands every
applicable pass instead of selecting an arbitrary default. Comparable pass
price or pass-terrain value contributes only when the matching objective is
selected; broader resilience remains explanation-only.

Search V4 readiness follows the factor's evidence mode rather than treating
catalog completeness as one universal requirement. Comparative numeric factors
need broad enough resolved evidence for fair comparison. Positive-presence
facts such as glacier terrain, a snow park, night skiing, marked freeride
routes, snowmaking availability, and apres may reward an explicit preference
once enough verified positives exist, even when authoritative absence is
sparse. In that mode verified availability is positive, verified
unavailability is negative, and unknown remains neutral. Categorical matches
likewise reward trusted matches without converting missing values into
mismatches.

This ranking behavior does not weaken catalog truth. Website silence and an
incomplete search remain `unknown`, never `unavailable`; `needs_source` has zero
source-backed influence. Snowmaking availability may support the explicitly
requested conditional-resilience composition, but it does not establish a
coverage percentage, operation, open terrain, or physical snowpack truth.
Unknown and unavailable produce no resilience uplift while remaining distinct
for explanations and requirements.

## Conditions Trust

availability_status is weather-derived unless provenance explicitly says
reported. It is not official lift status.

The latest `resort_conditions` row is a current one-day conditions snapshot. It
is not target-date evidence for a future trip merely because the trip is close.
Search V4 target-date evidence must retain:

- provider, model, forecast kind, and immutable run ID;
- model initialization, provider availability, and ingestion time;
- valid local date, timezone, and derived lead time;
- ski area, request coordinate, elevation band, and representative elevation;
- ensemble-mean basis, supported spread fields, and member count;
- date/elevation completeness and freshness;
- configured source-selection and lead-time policy version.

Source provenance, model spread, coverage, and freshness are distinct. A
provider value being present does not establish high confidence. The initial
ranking limit comes from the reviewed lead-time/climatology composition, not a
provider marketing label or an additional uncalibrated multiplier.

Forecast snow depth is a modelled point/elevation value. It does not prove
ski-area snow-cover percentage, expected open-piste ratio or kilometres, open
lifts, official operations, avalanche safety, or route safety. These require
separately named sources and evidence models.

Forecast runs remain prediction evidence. They must never be included in raw
archive planning windows or used to build `ski_area_snow_climatology_daily`.
Observed values may later be compared with retained forecast issue versions for
calibration, but that comparison does not relabel predictions as observations.

Only validated complete forecast runs are published to request-path serving
heads. A partial or failed run leaves the previous area head in place. Stale or
partial evidence receives a reduced cap and a visible uncertainty state; it is
not silently imputed as favourable conditions.

Planning evidence profiles are:

- forecast_assisted;
- archive_backed; and
- fallback_heavy.

Current conditions, condition history, raw archive weather, and derived
climatology remain keyed by ski_area_id. Display names are not durable evidence
keys.

Search V4 forecast runs and heads are also keyed by `ski_area_id`. Terrain
domains, passes, stay destinations, and ski regions cannot acquire synthetic
forecast truth by aggregation or branding. The forecast evidence storage and
publication contract is defined in ADR 0013 and the trip-window forecast
evidence feature spec.

The initial acquisition gateway is Open-Meteo, but model producer remains
explicit provenance: ECMWF IFS 0.25 degree ensemble mean is preferred through
lead day 15, and NOAA GEFS 0.5 degree ensemble mean supplies days 16 through 30
and shorter-range gaps. Heads are source-keyed so both current model runs can
coexist. Snowcast selects one eligible source per ski-area/date and never hides
cross-model averaging behind one forecast value.

Search V4 skill evidence keeps difficulty lengths, run counts, and qualitative
labels distinct. Source-backed kilometre breakdowns receive full factor
strength; source-backed count profiles receive half strength; positive
qualitative labels receive quarter strength; missing evidence is neutral. The
planning evaluator shrinks weak evidence toward neutral `0.50` and never treats
run-count proportions as verified kilometres.

The value payload and model-update metadata are separate provider surfaces.
Snowcast records the metadata initialization timestamp and rejects an
acquisition batch when that timestamp changes during the fetch. Retrieval time
must never be mislabeled as model issue time. Unsupported optional variables
remain null with explicit completeness metadata; an adjacent date cannot fill a
missing requested date.

## Validation

Validate the canonical graph and trust manifest:

    UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog \
      --catalog-path app/data/catalog.json \
      --trust-manifest-path app/data/resort_trust_manifest.json

Validate and render a curation report:

    UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
      typed docs/catalog-curation/REPORT.json \
      --current-catalog-path app/data/catalog.json \
      --markdown-output docs/catalog-curation/REPORT.md

Reconcile a report against a base checkout:

    UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation \
      reconcile docs/catalog-curation/REPORT.json \
      --base-catalog-path BASE/app/data/catalog.json \
      --current-catalog-path app/data/catalog.json \
      --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json \
      --current-trust-manifest-path app/data/resort_trust_manifest.json
