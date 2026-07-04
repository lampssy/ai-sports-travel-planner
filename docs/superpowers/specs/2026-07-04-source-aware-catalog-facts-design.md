# Feature Spec: Source-Aware Catalog Fit Facts

## Status

- Status: accepted
- Owner: solo-builder
- Related docs:
  - `docs/domain-language.md`
  - `docs/data-trust-model.md`
  - `docs/superpowers/specs/2026-06-20-resort-fit-data-model-design.md`
  - `docs/superpowers/specs/2026-07-01-trip-market-catalog-and-search-design.md`
- Related plan: N/A until the committed spec is reviewed
- Related ADRs:
  - `docs/architecture/adr/0008-destination-and-ski-area-boundaries.md`
  - `docs/architecture/adr/0009-normalized-trip-market-catalog.md`
  - A focused ADR recording typed fact objects and controlled vocabularies is
    required before schema implementation.

## User Outcome

Snowcast's static catalog can preserve a broader set of useful ski-area and
stay-base facts without relying on free-form tags, silently treating missing
data as false, or losing source scope and seasonal context.

Catalog curation becomes more consistent because every new fact has a named
owner, constrained values, explicit missing-data semantics, and a corresponding
trust-manifest group.

## Scope

In scope:

- typed ski-area facts for snowmaking, glacier terrain, snow parks, night
  skiing, marked freeride routes, official trail maps, and ski-day apres;
- typed stay-base facts for elevation, structural type, local character, and
  local apres;
- an optional official trail-map link on a terrain domain when the source map
  is aggregate rather than child-area scoped;
- deprecation and removal of free-form atmosphere tags;
- stricter curation semantics for existing ski-area access modes;
- trust-manifest, catalog-curation report, validation, persistence, domain-doc,
  and curation-skill changes needed to support the new contract;
- conservative migration of the existing catalog without promoting legacy tags
  into trusted facts.

Out of scope:

- live lift, piste, snow-depth, operating-hours, or venue-status feeds;
- detailed weekly schedules for night skiing or apres venues;
- venue-level bar, restaurant, or nightlife entities;
- snow-cannon counts;
- destination-level ski-bus or apres fields;
- broad recuration of every existing destination in the schema-change branch;
- client presentation or downstream interpretation of the new facts.

## Product Fit

- The change keeps Snowcast ski-specific by modeling terrain facilities,
  snowmaking, access, and stay-base character explicitly.
- Unknown, unavailable, estimated, stale, aggregate, and child-scoped facts
  remain distinguishable.
- Official, open-data, and specialist sources retain their existing trust
  hierarchy.
- The catalog does not claim marketplace completeness or live operational
  accuracy.

## Domain Model

### Bounded contexts touched

- Catalog and Data Trust
- Catalog Curation

### Terms introduced or changed

- `AvailabilityStatus`
- `SnowmakingFact`
- `AvailabilityFact`
- `SnowParkFact`
- `SeasonalFeatureFact`
- `MarkedFreerideRoutesFact`
- `OfficialLinkFact`
- `ApresProfileFact`
- `BaseType`
- `BaseCharacterFact`

### Common missing-data semantics

Feature availability uses:

```text
available | unavailable | unknown
```

- `available`: a suitable source explicitly supports the feature.
- `unavailable`: an authoritative source explicitly rules it out, or a reviewed
  authoritative inventory establishes its absence. A complete inventory must
  be explicitly scoped to the owning entity, feature category, and applicable
  season; the curation report must explain why it is complete.
- `unknown`: evidence is insufficient. Failure to find a statement is not
  evidence of unavailability.

For scalar fields such as stay-base elevation and official link metadata,
`null` means the value has not been curated or the source does not publish it.

### Source-aware storage boundary

The canonical catalog stores typed values and semantic context such as basis,
terrain ownership, and season label. The trust manifest stores verification
status, direct source references, and normalization notes.

Source URLs are not duplicated inside every fact object. An
`OfficialLinkFact.url` is stored in the catalog because the URL is itself the
catalog value.

### Ski-area fields

#### `snowmaking`

```text
SnowmakingFact:
  availability: available | unavailable | unknown
  coverage_pct: float | null
  coverage_basis:
    piste_length
    skiable_area
    run_count
    publisher_unspecified
    unknown
  season_label: string | null
```

Invariants:

- `coverage_pct` is between 0 and 100 inclusive.
- A positive percentage requires `availability=available`; an explicitly
  published zero requires `availability=unavailable`.
- A non-null percentage cannot use an `unknown` basis. If the publisher gives a
  percentage without defining its denominator, the basis is
  `publisher_unspecified`.
- A null percentage requires `coverage_basis=unknown`.
- Cannon counts, marketing phrases such as "snow guaranteed", and arithmetic
  derived from unrelated metrics cannot produce a coverage percentage.
- Aggregate percentages are not copied to a child ski area.

#### `glacier_terrain`

```text
AvailabilityFact:
  availability: available | unavailable | unknown
```

This means the modeled ski area itself contains officially skiable glacier
terrain. Nearby glacier terrain, pass-only access to another area, legacy
`glacier_access` tags, and ski-area names do not establish availability.

#### `snow_park`

```text
SnowParkFact:
  availability: available | unavailable | unknown
  park_count: integer | null
  season_label: string | null
```

An eligible park is an officially designated snow or freestyle park. Generic
beginner areas, fun slopes, and undesignated natural terrain do not qualify.

If `park_count` is present it must be positive and availability must be
`available`.

#### `night_skiing`

```text
SeasonalFeatureFact:
  availability: available | unavailable | unknown
  season_label: string | null
```

Eligible night skiing is official lift-served downhill skiing offered on a
recurring schedule or published season dates. Cross-country night skiing,
illuminated sledging, private sessions, and isolated exceptional events do not
qualify.

Detailed schedules stay outside the static catalog.

#### `marked_freeride_routes`

```text
MarkedFreerideRoutesFact:
  availability: available | unavailable | unknown
  route_count: integer | null
  season_label: string | null
```

An eligible route is an official ungroomed route that is marked and managed,
secured, or patrolled as part of the ski-area offer. Generic off-piste
marketing, unmarked freeride zones, ski touring, heliskiing, and advanced
groomed pistes do not qualify.

If `route_count` is present it must be positive and availability must be
`available`.

#### `official_trail_map`

```text
OfficialLinkFact:
  url: string
  season_label: string | null
```

The URL must be a direct external HTTP(S) link from the official operator or
destination. A child-scoped map belongs to `SkiArea`. A connected aggregate map
belongs to `TerrainDomain`. The same aggregate map must not be copied to its
child ski areas.

#### `ski_day_apres_profile`

```text
ApresProfileFact:
  availability: available | unavailable | unknown
  intensity:
    low_key
    moderate
    lively
    destination_defining
    null
  season_label: string | null
```

This describes apres directly associated with skiing: on-mountain, slope-side,
or lift-terminal venues that form part of the ski-day experience.

Intensity meanings:

- `low_key`: a small, relaxed offer;
- `moderate`: a visible offer that does not define the area;
- `lively`: multiple active venues or a consistently energetic scene;
- `destination_defining`: the offer is a primary, repeatedly evidenced part of
  the area's identity.

`intensity` must be null when availability is `unavailable` or `unknown`, and
must be non-null when availability is `available`.

### Stay-base fields

#### `elevation_m`

```text
elevation_m: integer | null
```

This is the representative elevation of the named accommodation base or
settlement center. It is not the ski area's valley-station elevation or a broad
destination altitude range. It must be zero or greater when present.

#### `base_type`

`base_type` changes from an unconstrained optional string to a nullable
`BaseType`:

```text
town
village
hamlet
resort_station
neighbourhood
resort_sector
```

- `town`: substantial year-round settlement with a meaningful non-resort center
  and service base;
- `village`: smaller distinct settlement, normally year-round;
- `hamlet`: very small named settlement with limited independent services;
- `resort_station`: distinct, predominantly ski-tourism-oriented accommodation
  and lift settlement;
- `neighbourhood`: named district within a larger town or settlement;
- `resort_sector`: named accommodation/lift zone within a larger resort
  destination without independent settlement identity.

`null` means the field has not been curated; it is not a seventh base type.

#### `base_character`

```text
BaseCharacterFact:
  development_style:
    traditional
    mixed
    planned_resort
    unknown
  local_pace:
    quiet
    balanced
    lively
    unknown
```

Development-style meanings:

- `traditional`: built form predominantly inherited from a settlement that
  predates ski-tourism development;
- `mixed`: established settlement combined with substantial resort-era
  development, with neither form adequately describing the whole base;
- `planned_resort`: predominantly planned and built as a ski-tourism
  accommodation base;
- `unknown`: evidence is insufficient.

These values describe physical development history, not quality.

Local-pace meanings:

- `quiet`: limited general bustle and evening activity around accommodation;
- `balanced`: meaningful services and activity without a consistently lively
  atmosphere;
- `lively`: consistently active public spaces, services, or social atmosphere;
- `unknown`: evidence is insufficient.

`balanced` is a positive curated assertion, not a fallback for missing data.

#### `local_apres_profile`

`local_apres_profile` uses `ApresProfileFact`. It describes bars, social
activity, and evening or nightlife atmosphere within or immediately around the
accommodation base.

It is independent of `SkiArea.ski_day_apres_profile`. A quiet accommodation
base and a lively ski-day offer can both be true for one explicit trip
configuration.

No canonical destination-level apres field is introduced.

### Existing ski-area access field

`SkiAreaAccess.access_mode` keeps its existing values:

```text
walk
ski_bus
drive
ski_in_ski_out
mixed
unknown
```

- `walk`: walking is the representative practical connection;
- `ski_bus`: a regular ski-bus connection is the representative mode;
- `drive`: driving is the representative practical mode;
- `ski_in_ski_out`: direct ski access connects the base and area when
  conditions permit;
- `mixed`: a genuinely multi-stage or multi-mode connection with no single
  adequate label;
- `unknown`: unresolved curation state.

The field remains mandatory. A full review must not silently accept `unknown`:
the curation report must mark it unresolved. `mixed` does not prove that a ski
bus is available.

### Free-form atmosphere fields

The following fields are deprecated and removed:

```text
StayDestination.atmosphere_tags
StayBase.atmosphere_tags
```

Legacy values are not authoritative inputs for the new facts. Migration may
use them as research hints, but source-sensitive facts remain `unknown` until
reviewed evidence supports another value.

## Migration Contract

### Base-type normalization

| Existing value | New representation |
| --- | --- |
| `town` | `town` |
| `village` | `village` |
| `traditional_village` | `village`; development style requires review |
| `lake_village` | `village`; lake setting is not part of this contract |
| `hamlet` | `hamlet` |
| `neighbourhood` | `neighbourhood` |
| `resort_station` | `resort_station` |
| `planned_village` | `resort_station`; development style requires review |
| `resort_centre` | `resort_sector` |
| `high_altitude_sector` | `resort_sector`; elevation requires a source |
| `village_sector` | `resort_sector` |
| `null` | `null` |

The structural mapping can be applied mechanically. The notes after each
semicolon identify facts that must not be asserted mechanically.

### Atmosphere-tag retirement

- Existing tags are captured in the migration report for auditability.
- Tags do not automatically populate new typed facts.
- Direct synonyms and spelling variants are removed together.
- Access, terrain, snow, amenity, and geographic hints are routed to their
  correct owner only through later source-backed curation.
- Historical curation reports remain unchanged as review history.

### Delivery sequencing

1. Add domain types, canonical fields, persistence support, trust groups,
   report coverage, validation, docs, tests, and curation-skill guidance.
2. Increment the canonical catalog and matching trust-manifest schema version
   from `1` to `2`. Mixed version-1/version-2 application and data combinations
   are unsupported, following ADR 0009.
3. Normalize existing structural base types and retire free-form tags through a
   reconciled migration report.
4. Default new source-sensitive facts to `unknown` or `null` unless the same
   change includes direct reviewed evidence.
5. Curate actual values in normal destination-sized curation cycles rather than
   one broad schema-change pull request.

## Trust Manifest Contract

### Stay-base groups

```text
identity_ownership
coordinates
elevation
lodging_price_quality
base_type
base_character
local_apres
```

The stay-destination group `price_level_atmosphere` becomes `price_level` when
the destination atmosphere field is removed.

### Ski-area groups

Existing groups remain, with these additions:

```text
snowmaking
glacier_terrain
snow_park
night_skiing
marked_freeride_routes
ski_day_apres
official_documents
```

### Terrain-domain groups

Add `official_documents` for aggregate trail-map links.

Trust requirements:

- `verified` and `verified_with_adjustment` require direct external source
  references.
- `unavailable` requires explicit evidence or a reviewed complete inventory.
- A season-sensitive fact retains the publisher's season label when present.
- Conflicting scope, denominator, or season evidence remains unresolved until
  reconciled in the curation report.
- Independently sourced feature facts retain independent trust statuses and
  source sets.

## Curation Contract

`CANONICAL_FIELD_PATHS` and typed report coverage must include every new field.
A full stay-base or ski-area review classifies each field as `changed`,
`reviewed-no-change`, `unresolved`, or `not-applicable`.

Source order remains:

1. official operator, destination, map, or facility source;
2. OSM or Wikidata for settlement identity, coordinates, and elevation;
3. specialist secondary evidence when qualitative character is not adequately
   documented by primary sources.

Rules:

- Generic promotional language is not enough to establish intensity or
  development style.
- Qualitative normalized values normally use `verified_with_adjustment`.
  `verified` is reserved for sources that state an equivalent classification
  directly.
- `destination_defining` apres requires repeated official positioning plus
  independent specialist corroboration; one promotional page is insufficient.
- LLM output is never source evidence.
- Source excerpts must preserve the owning area, base, domain, season, and
  measurement basis.
- Failure to find a feature is recorded as `unknown`, not `unavailable`.
- Access-edge review keeps `access_mode`, `lift_distance`, distance, duration,
  directness, and source evidence internally consistent.
- The local curation skill must list the new fields, definitions, scope gates,
  and unresolved-value rules.

## Decision and Review Gate

- Classification: review-gated
- High-risk domains touched: catalog correctness, source trust, persistence,
  shared domain contracts, and curation workflow
- Developer Decision Checkpoints:
  - resolved:
    - use small typed fact objects instead of more free-form booleans or a
      generic attribute registry;
    - keep ski-bus information on `SkiAreaAccess` rather than adding it to
      `StayDestination`;
    - keep local apres and ski-day apres as separate facts;
    - use structural `BaseType` plus a two-axis `BaseCharacterFact`;
    - use `planned_resort` rather than `purpose_built`;
    - remove free-form atmosphere tags after a conservative migration;
  - accepted assumptions:
    - canonical nested objects are mirrored through the existing catalog
      persistence boundary without introducing independent source-of-truth
      tables;
  - unresolved: none
- ADR status: focused ADR required before schema implementation
- Advisory design-review:
  - reviewers: backend-api, data-trust-source-integrity
  - status: completed
- Advisory feature-review before final handoff:
  - reviewers: backend-api, data-trust-source-integrity
  - status: planned

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Mixed | Representation of new catalog facts | Determines type safety, missing-data semantics, and extensibility | Loose booleans are simple but ambiguous; a generic registry is flexible but weakly typed; small typed objects preserve semantics | Small typed source-aware objects | Appropriate for the current bounded catalog and extensible without creating a generic metadata system | Focused ADR |
| Product / Domain | Apres ownership | Local accommodation atmosphere and ski-day venues can differ | Base-only loses ski-day context; area-only loses local context; dual ownership preserves both scopes | Separate `local_apres_profile` and `ski_day_apres_profile` | Prevents false destination-wide generalization | Domain language |
| Product / Domain | Stay-base classification | Current values mix settlement form, development history, altitude, and character | Preserve free strings; use one large enum; separate structural type and character | Structural `BaseType` plus `BaseCharacterFact` | Produces clearer sourcing and migration rules | Domain language |
| Technical | Persistence boundary | Nested domain objects must survive sync and repository reads consistently | New normalized tables; opaque shared registry; existing catalog projection with typed objects | Existing projection boundary | Proportionate to static catalog data and avoids a second truth model | Focused ADR and implementation plan |

## Architecture Decisions

- Durable decisions made:
  - canonical typed facts belong to the entity that owns their physical or
    experiential scope;
  - source and verification metadata remain in the trust manifest;
  - free-form atmosphere tags do not remain as a compatibility escape hatch;
  - broad recuration is separated from the schema migration.
- ADRs needed:
  - typed source-aware catalog fact objects and controlled vocabulary migration.
- Existing ADRs that constrain this feature:
  - ADR 0008 keeps destination, stay-base, and ski-area ownership distinct;
  - ADR 0009 requires explicit normalized entities and access edges.
- Revisit criteria:
  - venue-level product requirements justify a separate venue entity;
  - a single trust group cannot represent independently sourced feature facts;
  - multiple access modes for one base/area pair must become independently
    queryable;
  - persistence volume or query requirements make JSON projection unsuitable.

## API and Client Contract

- Backend endpoints or response fields: none in this implementation slice.
- Web UI states: N/A.
- Mobile companion states: N/A.
- Backward compatibility:
  - the canonical catalog and trust manifest move together to schema version 2;
  - catalog loaders and repository projections must migrate atomically;
  - legacy atmosphere fields are removed only after all internal readers and
    tests use the typed replacements;
  - obsolete persistence columns are dropped as part of the coordinated schema
    cutover rather than retained as an undocumented compatibility surface;
  - external clients receive no new or removed fields in this slice.

## Data Trust and Source Integrity

- Data sources: official operator/destination sources, authoritative open data,
  and reviewed specialist secondary evidence under the established source
  hierarchy.
- Freshness: seasonal facts retain season labels; retrieval and review context
  stays in curation evidence and trust notes.
- Required evidence: direct source references for verified statuses and for
  every changed access edge.
- Missing data: `unknown` or `null`, never inferred negative.
- Conflicting data: remain unresolved until scope, season, and terminology are
  reconciled explicitly.
- Estimated legacy tags: migration hints only, never automatically promoted.

## AI / LLM Use

- Deterministic logic owns schema validation, enum validation, migration,
  reconciliation, and trust enforcement.
- AI may assist source discovery or summarize evidence during curation.
- AI output is not a source and cannot directly populate trusted catalog facts.
- No new request-path model call, prompt, cache, or fallback behavior is added.

## Background Work

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| N/A | N/A | N/A | Static catalog and review-time curation only |

## Security, Privacy, and Abuse

- No user data is involved.
- No secrets, credentials, or private provider data enter the catalog.
- Source excerpts and URLs remain public external evidence.
- No new permission, session, or rate-limit behavior is introduced.

## Observability and Operations

- No new runtime provider or scheduled job is introduced.
- Invalid catalog or trust data must fail existing validation and bootstrap
  checks explicitly.
- Schema migration failures must remain visible through current startup and test
  failures rather than silently dropping fields.
- No runbook or alert changes are required unless implementation adds an
  operational migration command beyond existing catalog sync/bootstrap.

## Acceptance Criteria

- Domain models implement every type and invariant in this spec.
- Canonical catalog and trust-manifest schema versions are both `2` after the
  migration and mismatched versions fail validation.
- `StayBase.base_type` accepts only the six defined non-null values.
- Ski-area, stay-base, and terrain-domain ownership matches this spec.
- Canonical catalog serialization, persistence sync, repository loading, and
  round-trip tests preserve all new objects.
- Trust-manifest namespaces and field groups exactly cover the new fields.
- Verified statuses without direct source references fail validation.
- Curation coverage includes every new canonical field.
- Full reviews surface `unknown` access modes as unresolved.
- Existing base types are normalized according to the migration table.
- Legacy atmosphere tags are captured in migration evidence and removed from
  canonical models, physical persistence columns, and active tests.
- Legacy tags do not automatically populate source-sensitive facts.
- Domain language and data-trust documentation define the new ownership and
  missing-data semantics.
- The local catalog-curation skill documents the new sweep and source rules.
- Existing canonical catalog and trust validation pass after migration.
- Migration reconciliation accounts for every catalog and trust delta.

## Verification

- Unit tests:
  - enum acceptance and rejection;
  - cross-field invariants for availability, counts, percentages, and apres
    intensity;
  - strict URL and percentage bounds;
  - base-type normalization;
  - legacy-tag non-promotion;
  - curation coverage and unresolved handling.
- Integration tests:
  - canonical JSON to domain model;
  - catalog sync to persistence and repository round trip;
  - trust-manifest mirror and source-ref enforcement;
  - typed curation report rendering and reconciliation.
- Static checks:
  - canonical catalog validation;
  - migration report reconciliation;
  - documentation and curation-skill vocabulary alignment.
- Manual review:
  - inspect representative ski-area, stay-base, access, and terrain-domain
    records;
  - confirm aggregate scope is not copied to child entities;
  - confirm retired tags survive only in review history.

## Advisory Review

- Design reviewers: Backend / API; Data Trust & Source Integrity
- Feature reviewers: Backend / API; Data Trust & Source Integrity
- Design review completed on 2026-07-04.
- Findings resolved in this spec:
  - made the breaking catalog and trust schema-version transition explicit;
  - replaced a combined feature trust group with per-fact trust groups;
  - defined the evidence boundary for authoritative unavailability;
  - clarified physical retirement of obsolete persistence columns;
  - strengthened evidence requirements for qualitative classifications.
- Known residual risks:
  - qualitative character remains harder to source consistently than structural
    settlement type;
  - official feature pages may disappear or omit season labels;
  - broad catalog completeness requires later destination-sized curation cycles.
