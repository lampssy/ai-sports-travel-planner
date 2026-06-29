# Feature Spec: Destination Boundaries And Connected Terrain

## Status

- Status: accepted
- Advisory design review: completed 2026-06-29 after Task 1 quality-review
  remediation; no remaining High findings pending re-review
- Owner: solo-builder
- Related docs:
  - `docs/domain-language.md`
  - `docs/data-trust-model.md`
  - `docs/product-backlog.md`
  - `docs/superpowers/specs/2026-06-20-resort-fit-data-model-design.md`
- Related plan:
  - `docs/superpowers/plans/2026-06-29-destination-boundaries-and-campiglio-migration.md`
- Related ADRs:
  - `docs/architecture/adr/0005-catalog-scope-model.md`
  - `docs/architecture/adr/0006-shared-terrain-domains.md`
  - `docs/architecture/adr/0007-ski-area-weather-evidence-and-catalog-retirement.md`
  - new destination-boundary ADR required during implementation

## User Outcome

Snowcast should recommend independently meaningful ski-trip destinations while
still representing the complete terrain available through connected ski areas
and shared passes. A user choosing Madonna di Campiglio, Pinzolo, or
Folgarida-Marilleva should see the correct local stay context, local weather
evidence, local pass choices, and the shared 156 km connected domain without
three copies of the same aggregate terrain facts.

The same destination-boundary rule must apply to every catalog entry. Existing
entries are not grandfathered permanently; a follow-up catalog-wide audit will
identify structures that should be migrated.

## Scope

In scope:

- Define a source-reviewable rule for deciding when a place is a separate
  destination, stay base, ski area, or shared terrain domain.
- Broaden ski-area boundaries beyond the current disconnected-terrain heuristic.
- Model Madonna di Campiglio, Pinzolo, and Folgarida-Marilleva as three separate
  destinations and ski areas.
- Add one shared connected terrain domain for the three ski areas.
- Keep full-domain and local lift-pass products explicit.
- Preserve existing Madonna weather evidence under its current ski-area id.
- Source-review Madonna's local coordinates, elevations, and season geometry;
  if the accepted weather-request geometry changes, route a full archive
  refetch and climatology rebuild through post-deploy GitHub Actions.
- Make destination-boundary assessments and full-scope curation coverage typed,
  validator-enforced report contracts before editing catalog data.
- Add source-backed terrain-domain trust coverage for membership, aggregate
  metrics, and season windows.
- Update curation and review guidance so future curations apply the same rule.
- Record ski sub-areas as a parked future concept.
- Define a later consistency audit for already curated destinations.

Out of scope:

- Implement ski sub-areas or attach weather, lift status, or ranking to them.
- Perform the catalog-wide destination-boundary audit in this change.
- Migrate unrelated destinations while adjusting the Madonna curation PR.
- Treat pass-only external terrain as a connected terrain domain.
- Rebuild or move historical weather rows automatically.
- Mutate production weather or climatology data from this PR, a local command,
  catalog validation, or database bootstrap.
- Redesign the full search-result grouping or scoring model in this change.

## Product Fit

- Destination cards remain trip choices rather than marketing-area labels.
- Local weather and season evidence stays attached to terrain the selected
  destination directly accesses.
- Shared terrain scale remains available for planning without copying aggregate
  values into every child ski area.
- Local pass products preserve lower-cost or narrower-skiing choices.
- Source uncertainty remains visible when local terrain metrics cannot be
  separated reliably from shared-domain totals.

## Domain Model

Bounded contexts touched:

- static catalog and trust;
- terrain and lift-pass scope;
- ski-area weather evidence identity;
- recommendation grouping semantics.

### Destination Boundary Rule

A candidate place is a separate `Destination` only when all three hard gates
pass:

1. **Independent stay context:** users can book a multi-night ski trip under the
   place name and it has meaningful lodging inventory or stay-base choices.
2. **Independent ski access:** the place directly accesses a stable local ski
   area rather than only being a neighborhood inside another base.
3. **Independent recommendation value:** returning the place separately can
   materially change trip fit, such as lodging price, atmosphere, travel effort,
   lift access, local ticket cost, season timing, or weather evidence.

At least one strong source-backed identity signal is also required:

- a local lift-pass product;
- a separate operator, operating schedule, status feed, or weather presentation;
- official treatment as a resort or destination rather than only a piste sector,
  neighborhood, or marketing label.

The rule applies catalog-wide. Official naming and lift connectivity are
evidence inputs, not decisive rules by themselves.

### Failure Routing

- Independent lodging identity without independent ski identity becomes a
  `StayBase` under the destination.
- Independent terrain, weather, or operations without an independently useful
  trip destination becomes a `SkiArea` under the parent destination.
- A recognizable connected sector without independent operations remains part
  of its parent ski area; a future `SkiSubArea` may represent it when product
  needs justify the extra layer.
- Ski-connected areas spanning destinations are aggregated by a
  `TerrainDomain`.
- A shared pass covering terrain that is not ski-connected remains
  `regional_network` pass context and does not create a terrain domain.

### Typed Pre-Edit Boundary Gate

Before any catalog edit that creates a destination or changes a destination
boundary, the typed curation report must contain one
`destination_boundary_assessment` per candidate. Each assessment records:

- all three hard gates separately with `pass`, `fail`, or `unresolved` status,
  explanatory notes, and one or more typed `evidence_refs`;
- at least one strong source-backed identity signal, also with a typed status,
  notes, signal type, and typed `evidence_refs`;
- a typed failure route when any gate or required identity signal does not pass:
  `stay_base`, `ski_area`, `ski_sub_area_backlog`, `terrain_domain`,
  `external_pass_context`, or `blocked`.

Every evidence ref must resolve to a unique typed report evidence item containing
source type, direct URL, title, source value, and evidence summary. Official
sources remain preferred, followed by open data and reviewed editorial sources;
the assessment contract does not impose a blanket official-only rule. A passing
identity signal must reference source-backed evidence and match one of the
spec's strong signal types. The `official_destination_treatment` signal
specifically requires official evidence because that source status is the signal
being claimed.

New destination creation is blocked unless all three gates pass and at least
one identity signal passes. An `unresolved` result is not an implicit pass. The
validator must require assessments for every destination boundary decision in
the migration, not only newly created destinations. For Campiglio the required
set is exactly `madonna-di-campiglio`, `pinzolo`, and
`folgarida-marilleva`. Madonna is required even though it is retained because
the migration re-reviews the boundary of the connected domain around it.

### Ski Area Rule

A `SkiArea` is the smallest durable terrain unit that merits separate weather
or operational evidence. It may be lift-connected to another ski area.

Separate ski areas when reviewed sources and skier experience show a stable
combination of materially distinct access, operations, ticketing, elevations,
weather behavior, or opening schedules. Do not split internal sectors solely
because they have map labels or recognizable mountain names.

Historical weather, current conditions, and climatology continue to attach to
`ski_area_id`. Terrain groups and terrain domains remain aggregate facts and do
not own weather evidence.

### Campiglio Target Model

Create or retain these destinations and local ski areas:

| Destination | Ski area | Notes |
| --- | --- | --- |
| `madonna-di-campiglio` | existing `madonna-di-campiglio-ski-area` | Retain the id and existing weather evidence; localize terrain metrics to Madonna-only facts when sources support them. |
| `pinzolo` | `pinzolo-ski-area` | New independent destination and weather entity with Pinzolo stay context and local pass product. |
| `folgarida-marilleva` | `folgarida-marilleva-ski-area` | New independent destination and weather entity; Folgarida and Marilleva are stay bases under one operational ski-area identity. |

Add `campiglio-dolomiti-di-brenta` to `app/data/terrain_domains.json` with all
three destination/ski-area references. Store source-backed connected-domain
facts such as 156 piste kilometers and the reviewed aggregate lift count only on
the domain unless a source explicitly supports a local child value.

Retaining Madonna's ski-area id does not grandfather its existing weather
geometry. Source review must record local coordinate, elevation, season-month,
and exact season-window deltas.

The typed report must also include a Madonna
`weather_request_geometry_assessment`. Its `before` and `after` values each
contain exactly:

- `latitude`;
- `longitude`;
- `base_elevation_m`;
- `mid_elevation_m`;
- `upper_elevation_m`.

The three elevation bands are derived from the base/current `SkiArea` snapshots
through the same canonical `weather_elevation_points` helper used by weather
fetching. The report never accepts a caller-supplied `material_change` value.
The typed model exposes it as a validator/computed result: a latitude or
longitude change alone is material; a change to any derived elevation band is
material; identical full geometry is not material. Snapshot reconciliation must
also prove the reported before/after geometry matches the parsed base/current
catalogs. The computed result alone controls whether the conditional Madonna
archive refetch described below is required.

The frozen PR base is `e8f4e11` (`ce6090d^2`), where Madonna's ski area has
`base_elevation_m=1550` and `summit_elevation_m=2504`, producing reviewed
request bands 1550/2027/2409 m through `weather_elevation_points`.
Reconciliation must derive that base geometry and the final reviewed geometry
from snapshots. If the final coordinate or any derived base/mid/upper band
differs, the regression must compute `material_change=true`; it must not compare
only the post-merge branch state.

The shared Skiarea pass should be represented on each relevant destination:

- use the connected terrain-domain reference for Madonna, Pinzolo, and
  Folgarida-Marilleva coverage;
- retain `regional_network` semantics and an explicit external summary when the
  same product includes Pejo or other non-connected terrain;
- make the shared product the default representative planning product, matching
  the existing Tignes-Val d'Isere pattern;
- add source-backed local `single_ski_area` products for Pinzolo and
  Folgarida-Marilleva as non-default alternatives;
- do not invent a Madonna-only product when official tariff sources do not offer
  one.

### Comparison Examples

- Tignes and Val d'Isere remain separate destinations and ski areas under the
  shared `tignes-val-disere` terrain domain.
- Tignes villages remain stay bases because they do not expose independent
  local ski-area identities.
- Folgarida and Marilleva remain stay bases within one destination because they
  share one operational ski-area and local pass identity.
- Pejo remains external pass coverage unless it is separately curated; pass
  validity alone does not make it part of the ski-connected Campiglio domain.

### Catalog-Wide Applicability

The curation skill must apply the destination hard gates before editing every
new or existing destination. When the rule suggests a split or merge, curation
must stop treating the task as routine field enrichment and record an explicit
owner-reviewed migration decision.

The curation report contract must include typed `reviewed_targets`. Each target
declares `full` or `narrow` scope. Canonical required field-path sets are owned
in code by target type. A `full` target validates only when typed
`field_coverage` contains every canonical path, including reviewed-no-change,
unresolved, and not-applicable rows; changed-only coverage must fail. A
`narrow` target must explicitly declare its non-empty required path set. Add
`trust_manifest` as a first-class target type so provenance changes cannot hide
behind destination rows or Markdown prose.

Typed report validation and snapshot reconciliation are separate, composable
layers. Normal model validation checks report shape, evidence references,
coverage, and internal consistency without file-system context. Full/migration
CLI validation additionally parses explicit base and current resorts,
terrain-domain, and trust-manifest snapshots; derives every new, removed, and
changed target/field; and requires bidirectional agreement with `changes`,
`reviewed_targets`, and changed `field_coverage`. A self-declared report cannot
hide an undeclared catalog, domain, or trust-manifest delta, and cannot claim a
delta absent from the snapshots.

The reconciliation base for this migration is frozen at `e8f4e11`, the second
parent of merge commit `ce6090d` and the deployed/main parent before any PR #24
catalog, terrain-domain, or trust-manifest changes. Final validation reconciles
the complete `e8f4e11..HEAD` delta, including the original PR changes that were
already present on `ce6090d`'s first parent. The post-merge commit itself is not
a valid base because it would hide those changes.

Rentals do not gain a catalog id field in this migration. Snapshot
reconciliation instead uses one shared deterministic helper for base snapshots,
current snapshots, report targets, changes, and field coverage. Its target id is
`<resort_id>:<slugified-rental-name>`. The slug algorithm is exact: normalize the
name with Unicode NFKD and then `casefold()`; discard Unicode combining marks;
preserve ASCII `a`-`z` and `0`-`9`; replace each maximal run of all other
characters with one hyphen; strip leading and trailing hyphens; and reject an
empty result. Equal rental names in separate destinations remain distinct because
the destination id is part of the key. Two rentals in one destination that
normalize to the same key fail reconciliation. A rename that changes the slug is
the removal of the old key plus addition of the new key, and both deltas must be
present in `changes`, `reviewed_targets`, and changed field coverage.

Because retained boundary decisions and retained weather identities can be
semantically reviewed without an object-creation delta, migration reconciliation
also receives explicit required boundary-target and weather-geometry-target
sets. For this migration those sets require all three destination ids and the
existing Madonna ski-area id respectively.

The review skill must flag destination structures that fail the hard gates or
copy shared-domain metrics into a local ski area.

A later audit should inspect all current catalog destinations. Zell am
See-Kaprun, Les Houches/Chamonix, and other multi-place or multi-area entries are
audit candidates, not predetermined migrations.

## Decision and Review Gate

- Classification: review-gated
- High-risk domains touched: catalog truth, domain identity, weather evidence
  ownership, pass scope, shared terrain, ranking inputs, and future maintenance.
- Developer Decision Checkpoints:
  - resolved:
    - destination boundaries use trip-planning independence rather than terrain
      connectivity alone;
    - Madonna, Pinzolo, and Folgarida-Marilleva become separate destinations and
      local ski areas under one connected terrain domain;
    - the rule applies to all catalog destinations;
    - existing entries receive a later consistency audit rather than permanent
      grandfathering;
    - ski sub-areas are parked and do not own weather or ranking now.
    - retain `madonna-di-campiglio-ski-area` and source-review its local weather
      geometry rather than replacing the id;
    - after merge and deployment, the owner manually runs the conditional
      Madonna archive refetch and the required new-id backfills through GitHub
      Actions; no PR or local command mutates production weather data.
  - accepted scope decisions:
    - the shared Skiarea product is the default planning product, following the
      existing Tignes-Val d'Isere pattern;
    - production result-grouping changes remain in the scoring-model workstream.
  - unresolved owner decisions: none for implementation planning.
- ADR status: required; add an ADR for destination and ski-area boundary
  semantics during implementation.
- Advisory design-review:
  - reviewers: `backend-api`, `data-trust-source-integrity`
  - status: completed 2026-06-29 after initial and re-review remediation; no
    remaining High findings pending re-review
  - initial backend/API High findings: the terrain-domain destination invariant was not
    self-contained in Pydantic; curation reports could validate changed-only
    coverage; selector/API regressions and production-safe workflow handoff were
    incomplete.
  - initial data-trust High findings: destination gates were not typed or required
    before edits; local geometry fallback policy was underspecified; terrain
    domains lacked their own trust representation and required provenance.
  - initial resolution: require the Pydantic and cross-catalog invariants, typed report
    scope and boundary assessments, canonical coverage sets, direct geometry
    evidence policy, terrain-domain trust records, selector/API tests, and exact
    post-deploy GitHub Actions inputs defined in this spec and plan.
  - re-review backend/API High findings: weather materiality remained
    self-asserted; hard-gate enforcement could omit retained Madonna; and report
    deltas were not reconciled against base/current catalog snapshots.
  - re-review data-trust High findings: gate evidence was URL-only, identity
    source policy was inconsistent, trust coverage omitted `display_name` and
    changed terrain-domain records, and the terrain-domain trust change did not
    update its owning data-trust document.
  - re-review resolution: require computed weather request geometry, external
    required decision sets, typed evidence keys, bidirectional snapshot
    reconciliation, complete namespaced trust-manifest targets including
    `display_name`, and `docs/data-trust-model.md` in the implementation task.
  - third review-loop findings: the post-merge base hid original PR #24 deltas;
    the fixed 2025 archive end omitted current-year rows; one skill instruction
    drifted from the canonical identity wording; and reconciliation tests did
    not separately cover omitted terrain-domain trust records or changed
    `display_name`.
  - third review-loop resolution: freeze reconciliation at
    `ce6090d^2=e8f4e11`, test Madonna's 1550 m base against final geometry,
    derive the operator archive end immediately before execution, use canonical
    strong source-backed identity wording, and add both negative trust tests.
  - Task 1 quality-review findings: the plan temporarily validated and committed
    the Campiglio catalog before adding its required trust parity, and rental
    records lacked deterministic snapshot identity and rename semantics.
  - Task 1 quality-review resolution: make Madonna, Pinzolo,
    Folgarida-Marilleva, and Campiglio terrain-domain trust changes atomic with
    the catalog/domain migration before validation or commit; keep the earlier
    Tignes/Matterhorn migration in the trust-contract task; make the following
    report task consume the already-valid state; and use the shared
    destination-qualified rental key and explicit removal/addition rename model.
  - skipped reason: N/A
- Advisory feature-review before final handoff:
  - reviewers: `backend-api`, `data-trust-source-integrity`
  - status: planned
  - skipped reason: N/A

## Developer Decision Checkpoints

| Type | Decision | Why it matters | Options and tradeoffs | Owner choice | Agent review after choice | Follow-up doc |
| --- | --- | --- | --- | --- | --- | --- |
| Product / Domain | Destination boundary | Determines recommendation identity and prevents marketing areas from swallowing independently useful trip choices. | Official naming is inconsistent; connectivity conflates terrain with booking; planning-independence gates are more stable but expose existing entries for audit. | Use planning-independence hard gates catalog-wide. | This is the most reliable option, provided splits trigger reviewed weather-evidence migration rather than casual id replacement. | New ADR and `docs/domain-language.md` |
| Mixed | Campiglio entity shape | Controls local weather, pass prices, terrain scale, and future result grouping. | One destination is simpler but mis-scopes weather and local passes; three destinations match Tignes-Val d'Isere but add new weather entities. | Three destinations and one terrain domain. | Preserve the existing Madonna ski-area id, create new ids for Pinzolo and Folgarida-Marilleva, and backfill those separately. | Curation report and terrain-domain catalog |
| Operational / Data | Weather evidence migration | Determines whether historical rows still describe the accepted local geometry and prevents production mutation during review. | Keeping rows without re-review risks stale geometry; deleting/rebuilding in the PR is unsafe; post-deploy targeted GitHub Actions preserve explicit operator control. | Retain the Madonna id; source-review coordinates, elevations, and season geometry. If weather geometry materially changes, refetch Madonna from 1991-01-01 through the operator-derived `archive_end_date` with `force_refetch=true`, `rebuild=false`, then rebuild baseline 2025 climatology. Backfill Pinzolo and Folgarida-Marilleva through the same end date with `force_refetch=false`, `rebuild=false`, then rebuild their climatology. | Immediately before execution, determine Madonna's latest existing archive date. Use it as `archive_end_date`, or use UTC run date minus one only after proving it is not earlier. Selector/date tests and operator checks must include current-year rows. The owner runs workflows only after merge and deployment; implementation and verification must not execute production-mutating commands. | Curation report, implementation plan, and PR operator handoff |
| Product / Domain | Ski sub-areas | Could improve local status, access, and terrain detail but risks duplicating ski-area semantics. | Implement now or park until operational-status and hotel-level access need it. | Park. | Record a bounded backlog item and do not add schema fields now. | `docs/product-backlog.md` |

## Architecture Decisions

- Durable decisions made:
  - destination identity is a planning boundary;
  - ski-area identity is a weather/operations boundary;
  - connectivity is represented by terrain domains, not by merging destinations;
  - pass-only relationships do not imply terrain connectivity.
- ADRs needed: one destination-boundary ADR that extends ADRs 0005-0007.
- Existing ADRs that constrain this feature: ADRs 0005, 0006, and 0007.
- Revisit criteria: evidence shows the hard gates consistently over-split normal
  resort villages, or ski sub-area operational data becomes a product priority.

## API and Client Contract

- No new public API fields are required for the catalog migration.
- Existing destination, selected ski-area, stay-base, pass, and terrain-domain
  contracts remain authoritative.
- Search may expose Pinzolo and Folgarida-Marilleva as destination candidates.
- Shared-domain result deduplication remains a separate scoring/search concern;
  the catalog must not preserve an incorrect entity boundary merely to avoid
  duplicate cards in the current runtime.
- Existing Madonna ids remain backward compatible.
- Add a response-level API regression that asserts Madonna is serialized with
  `resort_id=madonna-di-campiglio` and
  `selected_ski_area_id=madonna-di-campiglio-ski-area`.

## Data Trust and Source Integrity

- Use official Campiglio, ski.it tariff, operating-date, weather, and live-status
  sources first.
- Geometry policy is ordered and blocking:
  1. use an official local source when it publishes the exact child entity's
     coordinates, elevations, or operating geometry;
  2. otherwise use OSM, DEM, or another reviewed open-data object at the exact
     destination, ski-area, or stay-base scope;
  3. use reviewed editorial fallback only at that exact child scope and label
     it `verified_with_adjustment` with the normalization documented;
  4. use an explicitly labeled estimate only when the existing catalog policy
     permits that field and the typed report documents its evidence and method;
  5. otherwise block new destination creation and mark the field unresolved.
- Keep aggregate 156 km and lift-count evidence scoped to the terrain domain.
- Every terrain domain requires non-empty direct `source_urls` supporting its
  membership and every populated aggregate metric. Membership cannot be
  inferred only from pass validity.
- Add a top-level `terrain_domains` mapping to
  `app/data/resort_trust_manifest.json`. Each domain has
  `display_name`, `membership`, `terrain_metrics`, and `season_window`
  statuses, direct `source_refs`, and notes. Validation requires exact id parity
  with `terrain_domains.json`, applies the existing source-backed status rules,
  and
  rejects internal artifacts as direct provenance. Migrate
  `tignes-val-disere` and `matterhorn-ski-paradise` when this contract is
  implemented; add `campiglio-dolomiti-di-brenta` with the catalog migration.
- Use namespaced trust-report target ids so destination and terrain-domain
  records are unambiguous. Reconciliation requires every changed record,
  including `destination:madonna-di-campiglio`, `destination:pinzolo`,
  `destination:folgarida-marilleva`, `terrain_domain:tignes-val-disere`,
  `terrain_domain:matterhorn-ski-paradise`, and
  `terrain_domain:campiglio-dolomiti-di-brenta` when their snapshots differ.
- Treat the Campiglio catalog/domain and required trust changes as one atomic
  migration. Add or update Madonna, Pinzolo, Folgarida-Marilleva, and Campiglio
  terrain-domain trust records before running catalog validation and before the
  data commit. Tignes-Val d'Isere and Matterhorn remain part of the earlier
  trust-contract migration. The subsequent report task must consume this
  already-valid current state and must not defer or repair trust parity.
- Local ski-area metrics may remain unresolved when sources publish only the
  connected-domain value.
- Rewrite the Madonna curation report as a linked three-destination curation with
  separate typed field coverage for each destination and the shared domain.
- Keep Pejo clearly classified as non-connected external pass validity.

## AI / LLM Use

- Destination classification, source scope, references, and validation remain
  deterministic and human-reviewed.
- No LLM output becomes catalog truth.
- An LLM may assist source discovery or report drafting only under the existing
  curation review boundary.

## Background Work

| Trigger | Function | Worker | Notes |
| --- | --- | --- | --- |
| After merge/deploy, if Madonna's computed `material_change=true` | GitHub Actions `Backfill Historical Weather` | Owner-triggered workflow | `start_date=1991-01-01`, `end_date=<archive_end_date>`, `resort_targets=madonna-di-campiglio`, `force_refetch=true`, `rebuild=false`; the force-refetch must rewrite every existing archive date under reviewed geometry. |
| After successful conditional Madonna refetch | GitHub Actions `Rebuild Snow Climatology` | Owner-triggered workflow | `baseline_end_year=2025`, `resort_targets=madonna-di-campiglio`, `source_model=snowcast_empirical_v1`. |
| After merge/deploy for new ids | GitHub Actions `Backfill Historical Weather` | Owner-triggered workflow | `start_date=1991-01-01`, `end_date=<archive_end_date>`, `resort_targets=pinzolo,folgarida-marilleva`, `force_refetch=false`, `rebuild=false`; use the same end date as Madonna. |
| After successful new-id backfill | GitHub Actions `Rebuild Snow Climatology` | Owner-triggered workflow | `baseline_end_year=2025`, `resort_targets=pinzolo,folgarida-marilleva`, `source_model=snowcast_empirical_v1`. |

Immediately before the owner dispatches the workflows, query the latest
existing Madonna raw archive `observed_on`. Set `archive_end_date` to that date,
or conservatively to the UTC workflow run date minus one only when the latter is
greater than or equal to the latest existing archive date. Both backfill runs
use the same end date. Operator verification must prove all existing dates,
including current-year observations, fall inside `1991-01-01..archive_end_date`.
The climatology boundary remains `baseline_end_year=2025`; it does not cap the
archive refetch window.

## Security, Privacy, and Abuse

- No user data or new sensitive fields are involved.
- No new permissions, sessions, external writes, or request-path provider calls
  are introduced.

## Observability and Operations

- Existing archive and climatology coverage metrics should show the two new ski
  areas as missing until explicitly backfilled.
- Catalog bootstrap must insert the new entities without deleting historical
  Madonna rows.
- Existing Madonna weather rows remain attached to
  `madonna-di-campiglio-ski-area`.
- Backfill and climatology failures remain visible through existing job logs and
  data-quality dashboards.
- Catalog/report validation, tests, and local verification are read-only with
  respect to production weather. The PR must not call a production-targeted
  backfill, climatology rebuild, or bootstrap command.

## Acceptance Criteria

- `docs/domain-language.md` contains the destination hard gates, ski-area rule,
  failure routing, and catalog-wide applicability statement.
- A new ADR records destination, ski-area, and connectivity ownership.
- Curation and review skills enforce the destination-boundary review before
  routine field enrichment.
- The typed report assesses Madonna, Pinzolo, and Folgarida-Marilleva before
  catalog edits, with all three gates, a passing strong source-backed identity
  signal, typed evidence refs, and explicit failure routing; neither new
  destination is created unless all required results pass, and retained Madonna
  cannot be omitted from migration validation.
- `CatalogTargetType` includes `trust_manifest`; typed `reviewed_targets`
  distinguish full and narrow scope; canonical field-path sets make a
  changed-only full curation invalid; `display_name` is part of full
  trust-manifest coverage; omission tests lock the contract.
- Full/migration CLI validation reconciles explicit base/current resorts,
  terrain-domain, and trust-manifest snapshots from frozen base `e8f4e11`
  through current `HEAD`. Every derived new, removed, or changed target/field is
  declared with matching before/after values, reviewed target scope, and changed
  field coverage; undeclared or invented deltas fail.
- Rental reconciliation uses the shared destination-qualified normalized-name
  target id without expanding the catalog schema. The normalization algorithm is
  deterministic, equal names in different destinations do not collide, and a
  rename is reconciled and reported as removal of the old key plus addition of
  the new key.
- Madonna has a required typed weather request-geometry assessment. Snapshot
  reconciliation derives and verifies before/after coordinate plus
  base/mid/upper geometry, while the typed model computes materiality. Missing
  assessment, coordinate-only change, elevation-band change, and
  identical-geometry behavior are covered by tests. A regression starts from
  the real `e8f4e11` Madonna base elevation of 1550 m and requires
  `material_change=true` when final reviewed geometry changes a band.
- `TerrainDomain` itself rejects fewer than two distinct destination ids, while
  cross-catalog validation still rejects unknown destination/ski-area refs.
- Terrain domains require direct membership/metric `source_urls`, and the trust
  manifest contains validated domain entries for Tignes-Val d'Isere,
  Matterhorn Ski Paradise, and Campiglio after migration.
- The Campiglio data task adds the two new destination trust entries, updates
  Madonna trust, and adds Campiglio terrain-domain trust in the same working
  change as the catalog/domain edits. `validate_resort_catalog` and the data
  commit occur only after that parity is complete; report rendering follows from
  the already-valid state.
- `docs/data-trust-model.md` owns and documents the top-level terrain-domain
  trust shape, source rules, id parity, and namespaced report targets.
- Madonna, Pinzolo, and Folgarida-Marilleva are three validated destinations
  with distinct local ski-area ids and stay contexts.
- `campiglio-dolomiti-di-brenta` references all three ski areas and owns the
  reviewed connected-domain terrain totals.
- No child ski area receives the 156 km aggregate unless a source explicitly
  supports the same child scope.
- Shared and local pass products reference the correct local ski areas and
  terrain domain.
- Pejo remains explicit non-connected external validity.
- The curation report has complete typed field coverage and direct evidence
  links for all three destinations and the terrain domain.
- Existing Madonna weather evidence is preserved; the two new ski-area ids are
  ready for explicit archive backfill and climatology rebuild. A computed
  Madonna `material_change=true` result is explicitly routed to the conditional
  full refetch through the operator-derived archive end before its baseline 2025
  climatology rebuild.
- The pre-run operator check derives one `archive_end_date` that is not earlier
  than Madonna's latest existing raw archive observation. Madonna uses
  `force_refetch=true`, and Madonna plus both new destinations include existing
  current-year rows through that same end date.
- Selector/CLI tests prove the three destination targets resolve to the expected
  ski-area ids without performing network or database writes, and the operator
  handoff contains only the exact GitHub Actions inputs.
- A response-level regression preserves the Madonna destination and selected
  ski-area ids.
- Ski sub-areas remain out of the schema and are recorded as parked backlog.
- A follow-up catalog-wide consistency audit is identified without migrating
  unrelated destinations in this PR.

## Verification

- Unit tests:
  - Pydantic rejection of a terrain domain with fewer than two distinct
    destination ids, plus cross-catalog reference validation;
  - report omission tests for `trust_manifest`, full-scope canonical field
    coverage, reviewed targets, and required destination gate assessments;
  - weather geometry omission plus coordinate-only, elevation-band, and
    identical-geometry materiality behavior;
  - real-base regression from Madonna `base_elevation_m=1550` at `e8f4e11` to
    final reviewed geometry, requiring materiality when a derived band changes;
  - snapshot reconciliation failures for an undeclared new destination, changed
    terrain domain, changed trust record, and omitted retained Madonna decision;
  - negative reconciliation for an omitted terrain-domain trust record and a
    changed trust `display_name` missing from report change/coverage;
  - distinct reconciliation ids for equal rental names in separate destinations,
    plus removal/addition reconciliation and reporting for a rental rename;
  - catalog validation for three destination/ski-area references;
  - terrain-domain reference and aggregate-scope validation;
  - lift-pass local/domain/external scope validation;
  - focused repository and resort-fit tests for the new catalog shape.
- Data validation:
  - `python -m app.data.validate_resort_catalog`;
  - `python -m app.data.validate_catalog_curation` for the rewritten report;
  - read-only verification that the new entities and domain load correctly.
- Ranking diagnostics:
  - run `python -m app.data.compare_ranking` and report whether the Campiglio
    options appear or share a diagnostic result group.
- Regression:
  - focused catalog, repository, resort-fit, search, selector/CLI, and API
    response tests;
  - `git diff --check` and lint for changed Python or skill files.
- Operational/manual:
  - verify the existing Madonna ski-area id is unchanged;
  - verify selector tests map Madonna, Pinzolo, and Folgarida-Marilleva to their
    exact ski-area ids without invoking live work;
  - record the exact GitHub Actions inputs from `Background Work`; do not provide
    or run local production backfill commands;
  - query and record the latest Madonna archive observation immediately before
    dispatch, verify `archive_end_date` is not earlier, and verify current-year
    rows are inside both backfill windows;
  - verify no normal bootstrap path deletes weather history.

## Advisory Review

- Design reviewers: `backend-api` and `data-trust-source-integrity`.
- Design-review status: completed after the Task 1 quality-review findings were
  resolved in the accepted spec and implementation plan; no remaining High
  findings pending re-review and no unresolved owner decision remains.
- Feature reviewers: `backend-api` and `data-trust-source-integrity` after the PR
  data and guidance changes are complete.
- Known residual risks:
  - local child terrain metrics may remain unresolved;
  - production search can still show multiple shared-domain destination cards
    until the scoring/search grouping workstream consumes the domain group;
  - a later catalog audit may require additional reviewed ski-area id migrations.
