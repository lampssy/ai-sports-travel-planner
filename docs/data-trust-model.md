# Data Trust Model

Snowcast recommendations are only useful if the catalog and evidence labels are honest. This document defines the current data-trust contract for resort metadata and recommendation semantics.

## Catalog Entities

Every destination in `app/data/resorts.json` must define:

- `ski_areas`: terrain/weather entities used for snow, seasonality, elevation, and Open-Meteo lookups.
- `stay_bases`: accommodation towns or zones used for lodging fit, budget filtering, lift-distance fit, and saved-trip context.
- `rentals`: example rental options shown as display facts, not as exhaustive provider inventory.

The production loader no longer creates silent default ski areas. If a destination is missing explicit `ski_areas` or `stay_bases`, catalog loading fails.

## Trust Statuses

`app/data/resort_trust_manifest.json` tracks critical field groups for every destination using these statuses:

- `verified`: checked against source-backed data without meaningful adjustment.
- `verified_with_adjustment`: checked against source-backed data but normalized for product modeling.
- `estimated`: curated estimate that is useful for ranking/display but not source-backed enough to present as fact.
- `needs_source`: present only as a placeholder or weak assumption and should not be over-presented.

The manifest is a trust contract, not a full provenance database. It keeps source quality visible while the catalog is still small.

`verified` and `verified_with_adjustment` fields must be backed by `source_refs` beyond the catalog file itself. `app/data/resorts.json` can be listed as the edited artifact, but it cannot be the only source for source-backed trust statuses.

The first source-backed recheck covered the previously estimated glacier/linked-area destinations:

- Hintertux: official glacier pages, ticket/season pages, geospatial lookup, and rental-provider lookup now support the destination, glacier ski area, winter-main-season adjustment, stay base, and example rental.
- Stubai Glacier: official ski-area, season/snow, and ski-rental sources now support the glacier ski area, nearby stay-base modeling, and Intersport Okay rental example.
- Zell am See-Kaprun: official regional, Kitzsteinhorn, Schmittenhoehe, and sports-shop sources now support the linked destination model and the Kitzsteinhorn/Maiskogel/Schmittenhoehe split.

Tignes, La Plagne, and Zermatt were also spot-checked against official sources to make sure existing `verified`/`verified_with_adjustment` labels were not only inherited from earlier catalog work. Zermatt remains marked as `verified_with_adjustment` for seasonality because Matterhorn Ski Paradise has year-round skiing while the current catalog keeps a winter-main-season product window.

## Price And Quality Semantics

`min_price` and `max_price` in `/api/search` mean nightly stay-base budget estimates in EUR. They do not include equipment rental.

Rental prices remain separate display facts. They should not be mixed into a fake package price until the product has real package/provider data.

The API field `stars` is retained for compatibility, but it means minimum internal stay-base quality tier:

- `1`: budget
- `2`: standard
- `3`: premium

It is not a hotel-star rating.

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
