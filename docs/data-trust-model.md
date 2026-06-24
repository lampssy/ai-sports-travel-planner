# Data Trust Model

Snowcast recommendations are only useful if the catalog and evidence labels are honest. This document defines the current data-trust contract for resort metadata and recommendation semantics.

## Catalog Entities

Every destination in `app/data/resorts.json` must define:

- `ski_areas`: terrain/weather entities used for snow, seasonality, elevation, and Open-Meteo lookups.
- `terrain_groups`: optional aggregate terrain entities used when a source
  describes linked ski areas together rather than one child ski area.
- `terrain_domains`: optional shared aggregate terrain entities in
  `app/data/terrain_domains.json`, used when a source describes a linked domain
  that spans ski areas modeled under multiple destinations.
- `lift_pass_products`: optional named pass products with explicit
  `single_ski_area`, `local_multi_area`, or `regional_network` validity scope,
  one optional default product, and reviewed adult/default price examples under
  each product.
- `stay_bases`: accommodation towns or zones used for lodging fit, budget filtering, lift-distance fit, and saved-trip context.
- `rentals`: example rental options shown as display facts, not as exhaustive provider inventory.

The production loader no longer creates silent default ski areas. If a destination is missing explicit `ski_areas` or `stay_bases`, catalog loading fails.

Child `ski_areas[]` must stay scoped to one modeled ski area. If a source
publishes aggregate terrain metrics for linked areas, store those metrics under
`terrain_groups[]` with `metric_scope=aggregate` instead of copying them onto
each child ski area when all members belong to one destination. If the linked
terrain spans multiple destinations, store the aggregate under
`terrain_domains[]` in `app/data/terrain_domains.json` and reference members as
`{resort_id, ski_area_id}` pairs.

Lift-pass products keep local `valid_ski_area_ids` for the destination that owns
the product. When the same pass also covers a modeled cross-destination terrain
domain, include the shared `terrain_domain_ids` so review and future ranking can
understand the accessible terrain without duplicating aggregate facts onto local
ski areas.

## Trust Statuses

`app/data/resort_trust_manifest.json` tracks critical field groups for every destination using these statuses:

- `verified`: checked against source-backed data without meaningful adjustment.
- `verified_with_adjustment`: checked against source-backed data but normalized for product modeling.
- `estimated`: curated estimate that is useful for ranking/display but not source-backed enough to present as fact.
- `needs_source`: present only as a placeholder or weak assumption and should not be over-presented.

The manifest is a trust contract, not a full provenance database. It keeps source quality visible while the catalog is still small.

`verified` and `verified_with_adjustment` fields must be backed by `source_refs` beyond the catalog file itself. `app/data/resorts.json` can be listed as the edited artifact, but it cannot be the only source for source-backed trust statuses.

When official sources conflict for the same scoped metric, first compare scope,
season, and metric wording. If no official source is clearly authoritative for
the modeled entity, a reviewed Bergfex skiregion or ski-resort page may be used
as a fallback corroborating source. The resulting field should use
`verified_with_adjustment`, the curation report should show the conflicting
official values, and the normalization note should explain the Bergfex fallback
and any arithmetic such as summed lift categories.

The first source-backed recheck covered the previously estimated glacier/linked-area destinations:

- Hintertux: official glacier pages, ticket/season pages, geospatial lookup, and rental-provider lookup now support the destination, glacier ski area, winter-main-season adjustment, stay base, and example rental.
- Stubai Glacier: official ski-area, season/snow, and ski-rental sources now support the glacier ski area, nearby stay-base modeling, and Intersport Okay rental example.
- Zell am See-Kaprun: official regional, Kitzsteinhorn, Schmittenhoehe, and sports-shop sources now support the linked destination model and the Kitzsteinhorn/Maiskogel/Schmittenhoehe split.

Tignes, La Plagne, and Zermatt were also spot-checked against official sources to make sure existing `verified`/`verified_with_adjustment` labels were not only inherited from earlier catalog work. Zermatt remains marked as `verified_with_adjustment` for seasonality because Matterhorn Ski Paradise has year-round skiing while the current catalog keeps a winter-main-season product window.

## Catalog Curation Reports

High-impact source-backed catalog changes should include a typed curation report
for review. Each changed field should identify the target entity and field path,
before and after values, trust status, source URL, source title, source type,
evidence summary, and any normalization note when the catalog value differs from
the source wording or shape.

The report validators check shape, required evidence fields, clickable source
links, and reviewability. They do not decide whether a source really supports
the proposed meaning; the owner still reviews source interpretation, product
fit, and any ranking-impact notes before accepting catalog truth.

## Price And Quality Semantics

`min_price` and `max_price` in `/api/search` mean nightly stay-base budget estimates in EUR. They do not include equipment rental.

Rental prices remain separate display facts. They should not be mixed into a fake package price until the product has real package/provider data.

Lift-pass prices are modeled under `lift_pass_products[].prices`; the legacy
destination-level `lift_pass_prices` field is no longer accepted in the static
catalog. Each curated destination should have one source-backed default
adult/default product when official ticket data is available. Add additional
products only when they materially change accessible terrain, price, or trip
suitability, such as a single-ski-area ticket versus a regional network card.

The API field `stars` is retained for compatibility, but it means minimum internal stay-base quality tier:

- `1`: budget
- `2`: standard
- `3`: premium

It is not a hotel-star rating.

## Resort Fit Factor Semantics

High-impact recommendation labels should be treated as derived fit factors, not
permanent direct truth in the catalog.

Current compatibility fields still exist:

- `stay_base.quality`
- `stay_base.lift_distance`
- `stay_base.supported_skill_levels`

The forward model is:

- raw catalog facts such as piste kilometers, difficulty mix, lift count,
  aggregate terrain groups, shared terrain domains, pass-product scope, nearest
  lift distance, access mode, price ranges, and source-backed season windows
  stay in the catalog;
- domain policy derives normalized factors and keeps ranking semantics out of
  raw catalog fields;
- each factor carries both a lifecycle state and a trust state.

Current first-slice factor examples are:

- `terrain_scale`: current first-slice ski-area size buckets derived from piste
  kilometers. Lift count and linked ski-area structure remain raw inputs for
  future refinement, not required inputs for the initial bucket.
- `skill_fit_profile`: beginner, intermediate, or advanced fit from piste
  difficulty mix and reviewed terrain facts.
- `stay_base_access`: walkable, shuttle-easy, or car-recommended access from
  lift distance, access mode, and transport requirement.

Ranking comparison diagnostics may derive an accessible-terrain version of
`terrain_scale` from the default lift-pass product. The source scope must be
recorded as `ski_area`, `terrain_group`, or `terrain_domain` in the diagnostic
factor inputs and report artifacts. This lets linked-domain facts such as
Tignes-Val d'Isere influence candidate scoring review without copying aggregate
300 km terrain claims onto the local Tignes or Val d'Isere ski-area records.
The same report records `result_group_key` and `group_counts` so reviewers can
separate option-level scoring from later production result-grouping decisions.

Scoring scenario diagnostics can mention factors before they are production
ready, but every such factor must declare a factor availability state:
`active_now`, `near_term`, `proxy_only`, `known_missing`, or
`future_candidate`. Only `active_now` factors can affect current diagnostic
scores. `proxy_only`, `known_missing`, and `future_candidate` factors must be
visible as caveats rather than hidden ranking boosts.

The model also reserves room for broader factor categories:

- `resort_character`: quiet, family-friendly, nightlife, pure-skiing, premium,
  or scenic fit from reviewed tourism and editorial evidence.
- `operational_convenience`: lift-status, pass, rental, transfer, and transport
  practicality when provider-backed data exists.
- `lodging_wellness`: lodging comfort, wellness, spa, sauna, hot-tub, and
  recovery amenities when accommodation or stay-base evidence exists.
- `dining_food`: restaurant, half-board, on-mountain food, and apres dining
  fit when provider-backed or reviewed source evidence exists.

Future stay-base quality and value semantics should move into an explicit
factor such as `stay_base_quality_profile`, because legacy
`stay_base.quality` remains high-impact for search fit and should not stay an
ambiguous catalog label forever.

Lifecycle controls factor-policy readiness, not production search behavior.
`active` means the factor is defined, derivable, and ranking-ready inside the
factor policy after review. It does not mean the factor is already integrated
into production `/api/search` ordering, saved-trip grouping, or itinerary
ranking. Trust caps only scale factors after a later ranking-integration
checkpoint and comparison review explicitly promote them into production
ranking.

`measured_not_ranked` and `planned` factors are audit-only, even when their
source evidence is strong. Likewise, an `active` or `core` factor is not safe for
production ranking consumption until the ranking-integration gate is complete.

The first implementation slice exposes catalog and audit readiness only. It
does not change production search or itinerary ranking behavior.

For future resorts and new factor families, source-backed factors need raw
inputs that can be traced to official, provider, or reviewed editorial sources.
LLM or acquisition output can propose values, but source-backed statuses require
external source refs and unresolved conflicts should remain review artifacts.
New factors should define their `factor_id`, scope, raw inputs, lifecycle,
ranking role, user-filter role, display role, and trust mapping before they can
be considered ranking-ready in factor policy. Production recommendation
influence still requires the later ranking-integration checkpoint.

## Conditions And Disruption Semantics

The API field `availability_status` is retained for compatibility, but current Open-Meteo-backed values are weather-derived conditions/disruption signals:

- `open`: low disruption risk
- `limited`: some disruption risk
- `temporarily_closed`: high disruption risk
- `out_of_season`: outside the typical ski season

These values are not official lift-operation status. The `reported` provenance type is reserved for future official resort/lift/status providers.

## Validation

Run the catalog validator before committing catalog changes:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```

The validator checks explicit ski areas and stay bases, duplicate IDs, plausible coordinates and elevations, trust-manifest coverage, allowed trust statuses, and source references for source-backed trust statuses.

For acquisition or scoring work, also run the read-only data-quality audit and
inspect the `resort_fit_factors` domain in the JSON or Markdown artifacts:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.audit_data_quality \
  --database-url "$DATABASE_URL" \
  --output-dir artifacts/data-quality
```
