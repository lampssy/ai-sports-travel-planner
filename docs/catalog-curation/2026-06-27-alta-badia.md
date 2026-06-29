# Alta Badia Catalog Curation

Reviewed Alta Badia destination identity, local ski-area scope, winter 2026/27 season window, default local pass product, terrain metrics, Corvara stay-base access, and Varallo rental-provider evidence against official Alta Badia/Dolomiti Superski pages, OSM geometry, Varallo pages, and reviewed editorial sources. Kept broader Dolomiti Superski and Sellaronda coverage as external pass context rather than copying regional terrain metrics into the local Alta Badia ski-area record.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:alta-badia` | `summit_elevation_m` | `2550` | `2778` | `verified_with_adjustment` | yes |
| `destination:alta-badia` | `season_windows` | `null` | `[{"end_date": "2027-04-04", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `destination:alta-badia` | `lift_pass_products` | `null` | `[{"external_validity_summary": "Local Alta Badia pass covers the modeled 130 km Alta Badia ski area; broader Dolomiti Superski and Sellaronda access is available through separate regional products and is not copied into this local ski-area record.", "is_default": true, "lift_pass_product_id": "alta-badia-skipass", "name": "Alta Badia Ski Pass", "prices": [{"amount": 80.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "main season", "source_url": "https://www.skiresort.info/ski-resort/alta-badia/"}], "valid_ski_area_ids": ["alta-badia-ski-area"], "validity_scope": "single_ski_area"}]` | `verified_with_adjustment` | no |
| `ski_area:alta-badia-ski-area` | `summit_elevation_m` | `2550` | `2778` | `verified_with_adjustment` | yes |
| `ski_area:alta-badia-ski-area` | `season_windows` | `null` | `[{"end_date": "2027-04-04", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:alta-badia-ski-area` | `total_piste_km` | `null` | `130.0` | `verified` | yes |
| `ski_area:alta-badia-ski-area` | `total_lift_count` | `null` | `53` | `verified` | yes |
| `ski_area:alta-badia-ski-area` | `piste_km_by_difficulty` | `null` | `{"advanced": 9.0, "beginner": 74.0, "intermediate": 47.0}` | `verified_with_adjustment` | yes |
| `stay_base:alta-badia-corvara` | `stay_base_id` | `null` | `"alta-badia-corvara"` | `verified` | no |
| `stay_base:alta-badia-corvara` | `lift_distance` | `"medium"` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:alta-badia-corvara` | `latitude` | `null` | `46.5496` | `verified_with_adjustment` | no |
| `stay_base:alta-badia-corvara` | `longitude` | `null` | `11.874` | `verified_with_adjustment` | no |
| `stay_base:alta-badia-corvara` | `nearest_lift_name` | `null` | `"Boè"` | `verified` | no |
| `stay_base:alta-badia-corvara` | `nearest_lift_distance_m` | `null` | `214` | `verified_with_adjustment` | yes |
| `stay_base:alta-badia-corvara` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:alta-badia-corvara` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:alta-badia-corvara` | `atmosphere_tags` | `[]` | `["dolomites", "family_friendly", "food_scene"]` | `verified_with_adjustment` | no |
| `stay_base:alta-badia-corvara` | `regional_data_ids` | `{}` | `{"nearest_lift_osm_node_id": "224065479", "osm_relation_id": "47252"}` | `verified` | no |
| `destination:alta-badia` | `trust_manifest.field_statuses.destination_identity` | `"verified_with_adjustment"` | `"verified"` | `verified` | no |
| `destination:alta-badia` | `trust_manifest.field_statuses.country_region` | `"verified_with_adjustment"` | `"verified"` | `verified` | no |
| `destination:alta-badia` | `trust_manifest.field_statuses.stay_bases` | `"verified_with_adjustment"` | `"verified"` | `verified` | no |
| `destination:alta-badia` | `trust_manifest.field_statuses.stay_base_lift_distance` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:alta-badia` | `trust_manifest.field_statuses.lift_pass_products` | `"needs_source"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:alta-badia` | `trust_manifest.field_statuses.rental_examples` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `destination:alta-badia` | `resort_id` | `reviewed-no-change` | Stable catalog id remains alta-badia. |
| `destination:alta-badia` | `name` | `reviewed-no-change` | Official sources use Alta Badia for the destination and ski-area identity. |
| `destination:alta-badia` | `country` | `reviewed-no-change` | Italy remains source-consistent. |
| `destination:alta-badia` | `region` | `reviewed-no-change` | Dolomites remains source-consistent for product grouping. |
| `destination:alta-badia` | `price_level` | `reviewed-no-change` | Legacy medium price tier remains product-curated. |
| `destination:alta-badia` | `latitude` | `reviewed-no-change` | Destination coordinate remains product-normalized to Alta Badia for weather lookup. |
| `destination:alta-badia` | `longitude` | `reviewed-no-change` | Destination coordinate remains product-normalized to Alta Badia for weather lookup. |
| `destination:alta-badia` | `base_elevation_m` | `reviewed-no-change` | Existing 1,324 m value matches reviewed ski-area elevation range. |
| `destination:alta-badia` | `summit_elevation_m` | `changed` | Updated high-point elevation to the reviewed 2,778 m ski-area value. |
| `destination:alta-badia` | `season_start_month` | `reviewed-no-change` | December remains aligned to the exact winter 2026/27 opening. |
| `destination:alta-badia` | `season_end_month` | `reviewed-no-change` | April remains aligned to the exact winter 2026/27 closing. |
| `destination:alta-badia` | `season_windows` | `changed` | Added exact official winter 2026/27 season window. |
| `destination:alta-badia` | `lift_pass_products` | `changed` | Added one default local Alta Badia pass product with representative adult day price. |
| `destination:alta-badia` | `terrain_groups` | `not-applicable` | No local aggregate terrain group created beyond the single modeled Alta Badia ski area. |
| `ski_area:alta-badia-ski-area` | `ski_area_id` | `reviewed-no-change` | Stable ski-area id preserved. |
| `ski_area:alta-badia-ski-area` | `name` | `reviewed-no-change` | Ski-area display name remains Alta Badia. |
| `ski_area:alta-badia-ski-area` | `summit_elevation_m` | `changed` | Updated high-point elevation to the reviewed 2,778 m ski-area value. |
| `ski_area:alta-badia-ski-area` | `season_windows` | `changed` | Added exact official winter 2026/27 season window. |
| `ski_area:alta-badia-ski-area` | `total_piste_km` | `changed` | Added official 130 km local piste metric. |
| `ski_area:alta-badia-ski-area` | `total_lift_count` | `changed` | Added official 53-lift local metric. |
| `ski_area:alta-badia-ski-area` | `piste_km_by_difficulty` | `changed` | Added reviewed blue/red/black terrain split. |
| `stay_base:alta-badia-corvara` | `stay_base_id` | `changed` | Added explicit stable stay-base id. |
| `stay_base:alta-badia-corvara` | `name` | `reviewed-no-change` | Corvara remains the modeled stay base. |
| `stay_base:alta-badia-corvara` | `price_range` | `reviewed-no-change` | Legacy lodging price range remains estimated. |
| `stay_base:alta-badia-corvara` | `quality` | `reviewed-no-change` | Standard quality tier remains product-curated. |
| `stay_base:alta-badia-corvara` | `lift_distance` | `changed` | Corrected legacy bucket from medium to near using OSM Corvara-to-Boè geometry. |
| `stay_base:alta-badia-corvara` | `supported_skill_levels` | `reviewed-no-change` | Existing beginner/intermediate suitability is preserved to avoid unsupported skill-policy expansion. |
| `stay_base:alta-badia-corvara` | `latitude` | `changed` | Added OSM-backed stay-base coordinate. |
| `stay_base:alta-badia-corvara` | `longitude` | `changed` | Added OSM-backed stay-base coordinate. |
| `stay_base:alta-badia-corvara` | `nearest_lift_name` | `changed` | Added nearest lift-station context. |
| `stay_base:alta-badia-corvara` | `nearest_lift_distance_m` | `changed` | Added computed OSM Haversine access distance. |
| `stay_base:alta-badia-corvara` | `access_mode` | `changed` | Normalized 214 m access distance to walk. |
| `stay_base:alta-badia-corvara` | `base_type` | `changed` | Added village base type from OSM settlement context. |
| `stay_base:alta-badia-corvara` | `atmosphere_tags` | `changed` | Added source-backed/product-normalized character tags. |
| `stay_base:alta-badia-corvara` | `regional_data_ids` | `changed` | Added stable OSM object identifiers. |
| `rental:Marcello Varallo Sport` | `name` | `reviewed-no-change` | Existing rental display name preserved and source-backed by Varallo/Alta Badia pages. |
| `rental:Marcello Varallo Sport` | `price_range` | `reviewed-no-change` | Legacy rental price range remains estimated. |
| `terrain_domain:dolomiti-superski` | `terrain_domain_id` | `not-applicable` | No Dolomiti Superski terrain domain introduced in this PR; regional scope remains pass external validity. |
| `destination:alta-badia` | `trust_manifest.field_statuses.destination_identity` | `changed` | Updated trust state after official source review. |
| `destination:alta-badia` | `trust_manifest.field_statuses.country_region` | `changed` | Updated trust state after official source review. |
| `destination:alta-badia` | `trust_manifest.field_statuses.stay_bases` | `changed` | Updated trust state after OSM stay-base review. |
| `destination:alta-badia` | `trust_manifest.field_statuses.stay_base_lift_distance` | `changed` | Updated trust state after OSM lift-access review. |
| `destination:alta-badia` | `trust_manifest.field_statuses.lift_pass_products` | `changed` | Updated trust state after official pass scope and reviewed price evidence. |
| `destination:alta-badia` | `trust_manifest.field_statuses.rental_examples` | `changed` | Updated trust state after Varallo provider review. |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `destination:alta-badia` | `summit_elevation_m` | [Skiresort.info Alta Badia](https://www.skiresort.info/ski-resort/alta-badia/) | `2778` | Reviewed ski-area page lists Alta Badia elevation from 1,324 m to 2,778 m. |  |
| `destination:alta-badia` | `season_windows` | [Alta Badia lifts, slopes and snow](https://www.altabadia.org/en/open-lifts-snow-report-dolomites) | `[{"end_date": "2027-04-04", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | Official Alta Badia live-info page lists the winter 2026/27 window as December 4, 2026 to April 4, 2027. |  |
| `destination:alta-badia` | `lift_pass_products` | [Alta Badia skipass and rates](https://www.altabadia.org/en/alta-badia-skipass-prices/skipass-dolomites) | `[{"external_validity_summary": "Local Alta Badia pass covers the modeled 130 km Alta Badia ski area; broader Dolomiti Superski and Sellaronda access is available through separate regional products and is not copied into this local ski-area record.", "is_default": true, "lift_pass_product_id": "alta-badia-skipass", "name": "Alta Badia Ski Pass", "prices": [{"amount": 80.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "main season", "source_url": "https://www.skiresort.info/ski-resort/alta-badia/"}], "valid_ski_area_ids": ["alta-badia-ski-area"], "validity_scope": "single_ski_area"}]` | Official Alta Badia pass page describes one Alta Badia ski pass covering 130 piste kilometres and 53 lifts; reviewed static price source gives the representative EUR 80 adult day-ticket value. | Product id, validity_scope, local ski-area id, external regional context, and price source URL are Snowcast normalization around official pass identity. |
| `ski_area:alta-badia-ski-area` | `summit_elevation_m` | [Skiresort.info Alta Badia](https://www.skiresort.info/ski-resort/alta-badia/) | `2778` | Reviewed ski-area page lists Alta Badia elevation from 1,324 m to 2,778 m. |  |
| `ski_area:alta-badia-ski-area` | `season_windows` | [Alta Badia lifts, slopes and snow](https://www.altabadia.org/en/open-lifts-snow-report-dolomites) | `[{"end_date": "2027-04-04", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | Official Alta Badia live-info page lists the winter 2026/27 window used for the modeled ski area. |  |
| `ski_area:alta-badia-ski-area` | `total_piste_km` | [Alta Badia skipass and rates](https://www.altabadia.org/en/alta-badia-skipass-prices/skipass-dolomites) | `130.0` | Official Alta Badia pass page states the local ski pass covers 130 piste kilometres. |  |
| `ski_area:alta-badia-ski-area` | `total_lift_count` | [Alta Badia skipass and rates](https://www.altabadia.org/en/alta-badia-skipass-prices/skipass-dolomites) | `53` | Official Alta Badia pass page states the ski area has 53 lift facilities. |  |
| `ski_area:alta-badia-ski-area` | `piste_km_by_difficulty` | [Skiresort.info Alta Badia](https://www.skiresort.info/ski-resort/alta-badia/) | `{"advanced": 9.0, "beginner": 74.0, "intermediate": 47.0}` | Reviewed slope table splits Alta Badia's 130 km terrain into 74 km easy, 47 km intermediate, and 9 km difficult slopes. |  |
| `stay_base:alta-badia-corvara` | `stay_base_id` | [OpenStreetMap Corvara relation](https://www.openstreetmap.org/relation/47252) | `"alta-badia-corvara"` | OSM confirms Corvara as a real local village stay base; catalog id is the stable Snowcast identifier. |  |
| `stay_base:alta-badia-corvara` | `lift_distance` | [OpenStreetMap Boè lift station](https://www.openstreetmap.org/node/224065479) | `214` | Computed Haversine distance from the OSM Corvara relation coordinate to the OSM Boè lift-station node is 214 m. | Distance is normalized from the legacy medium bucket to lift_distance=near because it is within the walkable access threshold. |
| `stay_base:alta-badia-corvara` | `latitude` | [OpenStreetMap Corvara relation](https://www.openstreetmap.org/relation/47252) | `46.5495743` | OSM relation for Corvara provides the stay-base village coordinate. | Rounded to 4 decimal places for catalog consistency. |
| `stay_base:alta-badia-corvara` | `longitude` | [OpenStreetMap Corvara relation](https://www.openstreetmap.org/relation/47252) | `11.8740339` | OSM relation for Corvara provides the stay-base village coordinate. | Rounded to 4 decimal places for catalog consistency. |
| `stay_base:alta-badia-corvara` | `nearest_lift_name` | [OpenStreetMap Boè lift station](https://www.openstreetmap.org/node/224065479) | `"Boè"` | OSM lift-station node identifies Boè as a nearby Corvara access lift. |  |
| `stay_base:alta-badia-corvara` | `nearest_lift_distance_m` | [OpenStreetMap Boè lift station](https://www.openstreetmap.org/node/224065479) | `214` | Computed Haversine distance from the OSM Corvara relation coordinate to the OSM Boè lift-station node is 214 m. |  |
| `stay_base:alta-badia-corvara` | `access_mode` | [OpenStreetMap Boè lift station](https://www.openstreetmap.org/node/224065479) | `214` | OSM geometry puts Corvara's village coordinate within 214 m of the Boè lift-station node. | Distance is normalized to access_mode=walk. |
| `stay_base:alta-badia-corvara` | `base_type` | [OpenStreetMap Corvara relation](https://www.openstreetmap.org/relation/47252) | `"village"` | OSM settlement relation supports Corvara as the modeled village stay base. | Nominatim classifies the relation addresstype as village. |
| `stay_base:alta-badia-corvara` | `atmosphere_tags` | [Alta Badia skiing](https://www.altabadia.org/en/skiing-alta-badia-dolomites) | `"Dolomiti Superski carousel, Sellaronda, Corvara/La Villa/San Cassiano, culinary experiences."` | Official Alta Badia skiing page supports Dolomites, family-friendly local-skiing, and food-scene character. | Official descriptive context is normalized into Snowcast atmosphere tags. |
| `stay_base:alta-badia-corvara` | `regional_data_ids` | [OpenStreetMap Corvara relation](https://www.openstreetmap.org/relation/47252) | `{"nearest_lift_osm_node_id": "224065479", "osm_relation_id": "47252"}` | OSM provides stable object identifiers for Corvara and the nearby Boè lift-station node. |  |
| `destination:alta-badia` | `trust_manifest.field_statuses.destination_identity` | [Alta Badia skiing](https://www.altabadia.org/en/skiing-alta-badia-dolomites) | `"verified"` | Official Alta Badia page confirms the destination and ski-area identity. |  |
| `destination:alta-badia` | `trust_manifest.field_statuses.country_region` | [Alta Badia skiing](https://www.altabadia.org/en/skiing-alta-badia-dolomites) | `"verified"` | Official Alta Badia context confirms the Italian Dolomites destination grouping used by the catalog. |  |
| `destination:alta-badia` | `trust_manifest.field_statuses.stay_bases` | [OpenStreetMap Corvara relation](https://www.openstreetmap.org/relation/47252) | `"verified"` | OSM geospatial evidence confirms Corvara as a real local stay base. |  |
| `destination:alta-badia` | `trust_manifest.field_statuses.stay_base_lift_distance` | [OpenStreetMap Boè lift station](https://www.openstreetmap.org/node/224065479) | `"verified_with_adjustment"` | OSM town/lift geometry now supports the stay-base lift-distance field group. |  |
| `destination:alta-badia` | `trust_manifest.field_statuses.lift_pass_products` | [Alta Badia skipass and rates](https://www.altabadia.org/en/alta-badia-skipass-prices/skipass-dolomites) | `"verified_with_adjustment"` | Official pass scope and reviewed price evidence now support the lift-pass-products field group. |  |
| `destination:alta-badia` | `trust_manifest.field_statuses.rental_examples` | [Varallo Sport](https://www.varallosport.com/en/) | `"verified_with_adjustment"` | Varallo and Alta Badia directory pages confirm the rental provider; price and quality remain product-curated. |  |

## Ranking Impact

Default comparison diagnostics wrote 12 DB-backed rows to artifacts/ranking-comparison. Alta Badia is not part of the current default comparison scenario set, so no rank movement row was emitted for this branch; the edited static catalog nevertheless changes ranking-relevant elevation, season, terrain, and stay-base access fields for future Alta Badia-covered scenarios.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-27-alta-badia.json --markdown-output docs/catalog-curation/2026-06-27-alta-badia.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`
- `git diff --check`
- `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_seed_data.py::test_seed_data_uses_real_rental_names_for_current_destinations tests/test_services.py::test_search_resorts_excludes_unsuitable_skill_levels -q`

## Caveats

- The official live-info page shows 54 live lift entries while the official skiing/pass pages and reviewed static source state 53 lifts; the catalog keeps 53 for local pass/terrain consistency.
- Broader Dolomiti Superski and Sellaronda access is not modeled as a terrain domain in this PR; it remains external pass context until a broader Dolomiti terrain-domain curation pass.
- The adult day-ticket price uses reviewed editorial evidence because the official Dolomiti/Alta Badia price calculator was offline during this curation sweep.
- Lodging price range, stay-base quality, supported skill levels, rental price range, rental quality, and rental lift-distance remain product-curated estimates.
