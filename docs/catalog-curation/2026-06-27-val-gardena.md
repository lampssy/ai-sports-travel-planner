# Val Gardena Catalog Curation

Reviewed Val Gardena destination, Val Gardena/Seiser Alm ski-area terrain, winter 2026/27 season window, default local pass product, Ortisei stay-base access, and rental-provider evidence against official Val Gardena, Dolomiti Superski, OSM, Sport Gardena/Everestski, and reviewed editorial sources. Kept the broader Dolomiti Superski/Sellaronda scope as pass context only and did not create a shared terrain domain because the modeled catalog entry is scoped to Val Gardena/Seiser Alm.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:val-gardena` | `season_windows` | `null` | `[{"end_date": "2027-04-04", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `destination:val-gardena` | `lift_pass_products` | `null` | `[{"is_default": true, "lift_pass_product_id": "val-gardena-seiser-alm-skipass", "name": "Val Gardena/Seiser Alm Ski Pass", "prices": [{"amount": 80.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "main season", "source_url": "https://www.skiresort.info/ski-resort/val-gardena-groeden/"}], "valid_ski_area_ids": ["val-gardena-ski-area"], "validity_scope": "single_ski_area"}]` | `verified_with_adjustment` | no |
| `ski_area:val-gardena-ski-area` | `season_windows` | `null` | `[{"end_date": "2027-04-04", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:val-gardena-ski-area` | `total_piste_km` | `null` | `181.0` | `verified_with_adjustment` | yes |
| `ski_area:val-gardena-ski-area` | `total_lift_count` | `null` | `79` | `verified_with_adjustment` | yes |
| `ski_area:val-gardena-ski-area` | `piste_km_by_difficulty` | `null` | `{"advanced": 21.0, "beginner": 52.0, "intermediate": 108.0}` | `verified_with_adjustment` | yes |
| `stay_base:val-gardena-ortisei` | `lift_distance` | `"medium"` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:val-gardena-ortisei` | `latitude` | `null` | `46.5752` | `verified_with_adjustment` | no |
| `stay_base:val-gardena-ortisei` | `longitude` | `null` | `11.6721` | `verified_with_adjustment` | no |
| `stay_base:val-gardena-ortisei` | `nearest_lift_name` | `null` | `"Ortisei - Furnes"` | `verified_with_adjustment` | no |
| `stay_base:val-gardena-ortisei` | `nearest_lift_distance_m` | `null` | `269` | `verified_with_adjustment` | yes |
| `stay_base:val-gardena-ortisei` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:val-gardena-ortisei` | `base_type` | `null` | `"town"` | `verified` | no |
| `stay_base:val-gardena-ortisei` | `atmosphere_tags` | `[]` | `["scenic", "premium", "family_friendly"]` | `verified_with_adjustment` | no |
| `stay_base:val-gardena-ortisei` | `regional_data_ids` | `{}` | `{"nearest_lift_osm_node_id": "411679826", "osm_relation_id": "47265"}` | `verified` | no |
| `destination:val-gardena` | `trust_manifest.field_statuses.destination_identity` | `"verified_with_adjustment"` | `"verified"` | `verified` | no |
| `destination:val-gardena` | `trust_manifest.field_statuses.country_region` | `"verified_with_adjustment"` | `"verified"` | `verified` | no |
| `destination:val-gardena` | `trust_manifest.field_statuses.stay_bases` | `"verified_with_adjustment"` | `"verified"` | `verified` | no |
| `destination:val-gardena` | `trust_manifest.field_statuses.stay_base_lift_distance` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:val-gardena` | `trust_manifest.field_statuses.lift_pass_products` | `"needs_source"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:val-gardena` | `trust_manifest.field_statuses.rental_examples` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `destination:val-gardena` | `resort_id` | `reviewed-no-change` | Stable catalog id remains val-gardena. |
| `destination:val-gardena` | `name` | `reviewed-no-change` | Official tourism and ski-pass sources use Val Gardena for the destination. |
| `destination:val-gardena` | `country` | `reviewed-no-change` | Italy remains source-consistent. |
| `destination:val-gardena` | `region` | `reviewed-no-change` | Dolomites remains source-consistent for product grouping. |
| `destination:val-gardena` | `price_level` | `reviewed-no-change` | Legacy high price tier remains estimated; detailed price ranges stay product-curated. |
| `destination:val-gardena` | `latitude` | `reviewed-no-change` | Destination coordinate remains the existing product-normalized Val Gardena weather lookup coordinate. |
| `destination:val-gardena` | `longitude` | `reviewed-no-change` | Destination coordinate remains the existing product-normalized Val Gardena weather lookup coordinate. |
| `destination:val-gardena` | `base_elevation_m` | `reviewed-no-change` | Existing 1,236 m value matches reviewed ski-area elevation range. |
| `destination:val-gardena` | `summit_elevation_m` | `reviewed-no-change` | Existing 2,518 m value matches reviewed ski-area elevation range. |
| `destination:val-gardena` | `season_start_month` | `reviewed-no-change` | December remains aligned to the reviewed winter 2026/27 planned opening. |
| `destination:val-gardena` | `season_end_month` | `reviewed-no-change` | April remains aligned to the reviewed winter 2026/27 planned closing. |
| `destination:val-gardena` | `season_windows` | `changed` | Added exact winter 2026/27 season window. |
| `destination:val-gardena` | `lift_pass_products` | `changed` | Added one default local Val Gardena/Seiser Alm pass product with a representative adult day price. |
| `destination:val-gardena` | `terrain_groups` | `not-applicable` | No intra-destination aggregate terrain group applies beyond the single modeled ski area. |
| `ski_area:val-gardena-ski-area` | `ski_area_id` | `reviewed-no-change` | Stable ski-area id preserved. |
| `ski_area:val-gardena-ski-area` | `name` | `reviewed-no-change` | Ski-area display name remains Val Gardena. |
| `ski_area:val-gardena-ski-area` | `latitude` | `reviewed-no-change` | Ski-area coordinate remains product-normalized to the Val Gardena ski area. |
| `ski_area:val-gardena-ski-area` | `longitude` | `reviewed-no-change` | Ski-area coordinate remains product-normalized to the Val Gardena ski area. |
| `ski_area:val-gardena-ski-area` | `base_elevation_m` | `reviewed-no-change` | Existing 1,236 m value matches reviewed ski-area elevation range. |
| `ski_area:val-gardena-ski-area` | `summit_elevation_m` | `reviewed-no-change` | Existing 2,518 m value matches reviewed ski-area elevation range. |
| `ski_area:val-gardena-ski-area` | `season_windows` | `changed` | Added exact winter 2026/27 season window. |
| `ski_area:val-gardena-ski-area` | `total_piste_km` | `changed` | Added reviewed local 181 km terrain metric. |
| `ski_area:val-gardena-ski-area` | `total_lift_count` | `changed` | Added reviewed 79-lift inventory metric. |
| `ski_area:val-gardena-ski-area` | `piste_km_by_difficulty` | `changed` | Added reviewed blue/red/black terrain split. |
| `stay_base:val-gardena-ortisei` | `stay_base_id` | `reviewed-no-change` | Stable stay-base id preserved. |
| `stay_base:val-gardena-ortisei` | `name` | `reviewed-no-change` | Ortisei remains the modeled stay base. |
| `stay_base:val-gardena-ortisei` | `price_range` | `reviewed-no-change` | Legacy lodging price range remains estimated. |
| `stay_base:val-gardena-ortisei` | `quality` | `reviewed-no-change` | Premium quality tier remains product-curated. |
| `stay_base:val-gardena-ortisei` | `lift_distance` | `changed` | Corrected legacy bucket from medium to near using OSM town-to-lift geometry. |
| `stay_base:val-gardena-ortisei` | `latitude` | `changed` | Added OSM-backed stay-base coordinate. |
| `stay_base:val-gardena-ortisei` | `longitude` | `changed` | Added OSM-backed stay-base coordinate. |
| `stay_base:val-gardena-ortisei` | `nearest_lift_name` | `changed` | Added nearest lift-station context. |
| `stay_base:val-gardena-ortisei` | `nearest_lift_distance_m` | `changed` | Added computed OSM Haversine access distance. |
| `stay_base:val-gardena-ortisei` | `access_mode` | `changed` | Normalized 269 m lift access to walk. |
| `stay_base:val-gardena-ortisei` | `base_type` | `changed` | Added town base type from OSM settlement classification. |
| `stay_base:val-gardena-ortisei` | `atmosphere_tags` | `changed` | Added source-backed/product-normalized character tags. |
| `stay_base:val-gardena-ortisei` | `regional_data_ids` | `changed` | Added stable OSM object identifiers. |
| `stay_base:val-gardena-ortisei` | `supported_skill_levels` | `reviewed-no-change` | Existing beginner/intermediate/advanced suitability is left unchanged to avoid unsupported skill-policy expansion. |
| `rental:Everestski Ortisei` | `name` | `reviewed-no-change` | Existing rental display name preserved and source-backed by Everestski/Sport Gardena pages. |
| `rental:Everestski Ortisei` | `price_range` | `reviewed-no-change` | Legacy rental price range remains estimated because no stable official static price table was curated. |
| `rental:Everestski Ortisei` | `quality` | `reviewed-no-change` | Premium rental quality tier remains product-curated. |
| `rental:Everestski Ortisei` | `lift_distance` | `reviewed-no-change` | Legacy rental lift-distance bucket remains unchanged. |
| `terrain_domain:dolomiti-superski` | `terrain_domain_id` | `not-applicable` | No shared terrain domain is introduced for this PR; Dolomiti Superski/Sellaronda coverage is external pass context. |
| `destination:val-gardena` | `trust_manifest.field_statuses.destination_identity` | `changed` | Updated trust state after external official source review. |
| `destination:val-gardena` | `trust_manifest.field_statuses.country_region` | `changed` | Updated trust state after external official source review. |
| `destination:val-gardena` | `trust_manifest.field_statuses.stay_bases` | `changed` | Updated trust state after OSM stay-base review. |
| `destination:val-gardena` | `trust_manifest.field_statuses.stay_base_lift_distance` | `changed` | Updated trust state after OSM lift-access review. |
| `destination:val-gardena` | `trust_manifest.field_statuses.lift_pass_products` | `changed` | Updated trust state after official pass-scope and reviewed price evidence. |
| `destination:val-gardena` | `trust_manifest.field_statuses.rental_examples` | `changed` | Updated trust state after Everestski/Sport Gardena provider review. |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `destination:val-gardena` | `season_windows` | [Skiresort.info Val Gardena overview](https://www.skiresort.info/ski-resort/val-gardena-groeden/) | `[{"end_date": "2027-04-04", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | Reviewed current-season page lists Val Gardena's 2026/27 operating window from December 4, 2026 through April 4, 2027. |  |
| `destination:val-gardena` | `lift_pass_products` | [Val Gardena ski passes](https://www.valgardena.it/en/winter-holidays-dolomites/ski-passes/) | `[{"is_default": true, "lift_pass_product_id": "val-gardena-seiser-alm-skipass", "name": "Val Gardena/Seiser Alm Ski Pass", "prices": [{"amount": 80.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "main season", "source_url": "https://www.skiresort.info/ski-resort/val-gardena-groeden/"}], "valid_ski_area_ids": ["val-gardena-ski-area"], "validity_scope": "single_ski_area"}]` | Official Val Gardena pass page describes the Val Gardena/Seiser Alm pass for the local lift and slope network; reviewed pricing source provides the representative adult day-ticket value. | Product id, local ski-area id, default flag, and price source URL are Snowcast normalization around the official pass identity. |
| `ski_area:val-gardena-ski-area` | `season_windows` | [Skiresort.info Val Gardena overview](https://www.skiresort.info/ski-resort/val-gardena-groeden/) | `[{"end_date": "2027-04-04", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | Reviewed current-season page lists Val Gardena's 2026/27 operating window used for the single modeled ski area. |  |
| `ski_area:val-gardena-ski-area` | `total_piste_km` | [Val Gardena slope offering](https://www.skiresort.info/ski-resort/val-gardena-groeden/slope-offering/) | `181.0` | Reviewed slope table lists 181 km of local Val Gardena/Seiser Alm slopes; this matches the Dolomiti Superski live-info row and the official Val Gardena heading. |  |
| `ski_area:val-gardena-ski-area` | `total_lift_count` | [Skiresort.info Val Gardena overview](https://www.skiresort.info/ski-resort/val-gardena-groeden/) | `79` | Reviewed overview lists 79 lifts for the Val Gardena/Seiser Alm ski resort. |  |
| `ski_area:val-gardena-ski-area` | `piste_km_by_difficulty` | [Val Gardena slope offering](https://www.skiresort.info/ski-resort/val-gardena-groeden/slope-offering/) | `{"advanced": 21.0, "beginner": 52.0, "intermediate": 108.0}` | Reviewed slope table splits the 181 km local terrain into 52 km easy, 108 km intermediate, and 21 km difficult slopes. |  |
| `stay_base:val-gardena-ortisei` | `lift_distance` | [OpenStreetMap Ortisei lift station](https://www.openstreetmap.org/node/411679826) | `269` | Computed Haversine distance from the OSM Ortisei relation coordinate to the OSM Ortisei lift-station node is 269 m. | Distance is normalized from the legacy medium bucket to lift_distance=near because it is within the walkable access threshold. |
| `stay_base:val-gardena-ortisei` | `latitude` | [OpenStreetMap Ortisei relation](https://www.openstreetmap.org/relation/47265) | `46.5752077` | OSM relation for Ortisei provides the stay-base town coordinate. | Rounded to 4 decimal places for catalog consistency. |
| `stay_base:val-gardena-ortisei` | `longitude` | [OpenStreetMap Ortisei relation](https://www.openstreetmap.org/relation/47265) | `11.6721382` | OSM relation for Ortisei provides the stay-base town coordinate. | Rounded to 4 decimal places for catalog consistency. |
| `stay_base:val-gardena-ortisei` | `nearest_lift_name` | [OpenStreetMap Ortisei lift station](https://www.openstreetmap.org/node/411679826) | `"Ortisei"` | OSM station node identifies the Ortisei lift access point for the Ortisei-Furnes gondola. | Catalog uses the lift-line display name Ortisei - Furnes for clearer stay-base access context. |
| `stay_base:val-gardena-ortisei` | `nearest_lift_distance_m` | [OpenStreetMap Ortisei lift station](https://www.openstreetmap.org/node/411679826) | `269` | Computed Haversine distance from the OSM Ortisei relation coordinate to the OSM Ortisei lift-station node. |  |
| `stay_base:val-gardena-ortisei` | `access_mode` | [OpenStreetMap Ortisei lift station](https://www.openstreetmap.org/node/411679826) | `269` | OSM geometry puts Ortisei's town coordinate within 269 m of the lift-station node. | Distance is normalized to access_mode=walk. |
| `stay_base:val-gardena-ortisei` | `base_type` | [OpenStreetMap Ortisei relation](https://www.openstreetmap.org/relation/47265) | `"town"` | OSM settlement relation supports Ortisei as the modeled town stay base. |  |
| `stay_base:val-gardena-ortisei` | `atmosphere_tags` | [Val Gardena ski passes](https://www.valgardena.it/en/winter-holidays-dolomites/ski-passes/) | `"Val Gardena/Seiser Alm, Sellaronda access, and premium Dolomites winter-holiday positioning."` | Official pass and destination context supports scenic, premium, family-friendly product character for Ortisei. | Official descriptive context is normalized into Snowcast atmosphere tags. |
| `stay_base:val-gardena-ortisei` | `regional_data_ids` | [OpenStreetMap Ortisei relation](https://www.openstreetmap.org/relation/47265) | `{"nearest_lift_osm_node_id": "411679826", "osm_relation_id": "47265"}` | OSM provides stable object identifiers for Ortisei and its nearest lift-station node. |  |
| `destination:val-gardena` | `trust_manifest.field_statuses.destination_identity` | [Val Gardena ski passes](https://www.valgardena.it/en/winter-holidays-dolomites/ski-passes/) | `"verified"` | Official Val Gardena page confirms the destination and ski-pass identity. |  |
| `destination:val-gardena` | `trust_manifest.field_statuses.country_region` | [Val Gardena ski passes](https://www.valgardena.it/en/winter-holidays-dolomites/ski-passes/) | `"verified"` | Official Val Gardena context confirms the Italian Dolomites destination grouping used by the catalog. |  |
| `destination:val-gardena` | `trust_manifest.field_statuses.stay_bases` | [OpenStreetMap Ortisei relation](https://www.openstreetmap.org/relation/47265) | `"verified"` | OSM geospatial evidence confirms Ortisei as a real local stay base. |  |
| `destination:val-gardena` | `trust_manifest.field_statuses.stay_base_lift_distance` | [OpenStreetMap Ortisei lift station](https://www.openstreetmap.org/node/411679826) | `"verified_with_adjustment"` | OSM town/lift geometry now supports the stay-base lift-distance field group. |  |
| `destination:val-gardena` | `trust_manifest.field_statuses.lift_pass_products` | [Val Gardena ski passes](https://www.valgardena.it/en/winter-holidays-dolomites/ski-passes/) | `"verified_with_adjustment"` | Official pass scope and reviewed price evidence now support the lift-pass-products field group. |  |
| `destination:val-gardena` | `trust_manifest.field_statuses.rental_examples` | [Everestski service](https://www.everestski.com/en/service.html) | `"verified_with_adjustment"` | Everestski and Sport Gardena pages confirm the Ortisei rental provider; price and quality remain product-curated. |  |

## Ranking Impact

Default comparison diagnostics wrote 12 DB-backed rows to artifacts/ranking-comparison. Val Gardena appears in the italy_beginner_value scenario and remains current rank 1 / candidate rank 1 with candidate score 0.600; the row uses terrain_source_id=val-gardena-ski-area and terrain_source_scope=ski_area. The edited static catalog now adds source-backed terrain and walk-access facts, but the comparison row remains rank-stable for the covered scenario.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-27-val-gardena.json --markdown-output docs/catalog-curation/2026-06-27-val-gardena.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`
- `git diff --check`
- `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_seed_data.py::test_seed_data_uses_real_rental_names_for_current_destinations tests/test_services.py::test_search_resorts_excludes_unsuitable_skill_levels -q`

## Caveats

- Official Val Gardena pass page includes both 181 km and 175 km wording for the local Val Gardena/Seiser Alm terrain; catalog keeps 181 km because the official heading, Dolomiti Superski live-info row, and reviewed editorial slope table align on 181 km.
- Dolomiti Superski/Sellaronda coverage is not modeled as a terrain domain in this PR; it remains external pass context until a broader Dolomiti terrain-domain curation pass.
- Lodging price range, stay-base quality, supported skill levels, rental price range, rental quality, and rental lift-distance remain product-curated estimates.
