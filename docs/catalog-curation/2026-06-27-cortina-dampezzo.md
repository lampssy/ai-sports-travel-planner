# Cortina d'Ampezzo Catalog Curation

Full destination sweep for Cortina d'Ampezzo. Added a source-backed Cortina valley pass product, exact 2026/27 operating window, ski-area terrain metrics, source-backed stay-base access metadata, and external trust-manifest references while keeping lodging price, quality, broad skill support, and rental quality as estimates.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:cortina-dampezzo` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `season_end_month` | `4` | `5` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `season_windows` | `null` | `[{"end_date": "2027-05-02", "season_label": "2026/2027", "start_date": "2026-11-21", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `lift_pass_products` | `null` | `["cortina-valle-skipass"]` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-valle-skipass` | `lift_pass_product_id` | `null` | `"cortina-valle-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:cortina-valle-skipass` | `name` | `null` | `"Valle Skipass Cortina"` | `verified_with_adjustment` | no |
| `lift_pass_product:cortina-valle-skipass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-valle-skipass` | `valid_ski_area_ids` | `null` | `["cortina-dampezzo-ski-area"]` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-valle-skipass` | `external_validity_summary` | `null` | `"Also covers Cortina Skyline and Lagazuoi down to Armentarola, San Vito di Cadore, and Auronzo-Misurina within the Cortina valley pass area."` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-valle-skipass` | `prices[0]` | `null` | `{"amount": 80, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "main season", "source_url": "https://www.skiresort.info/ski-resort/cortina-dampezzo/"}` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `stay_base_id` | `null` | `"cortina-dampezzo-cortina-dampezzo"` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `lift_distance` | `"medium"` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `latitude` | `null` | `46.5405` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `longitude` | `null` | `12.1357` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_name` | `null` | `"Funivia Faloria"` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_distance_m` | `null` | `472` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `base_type` | `null` | `"town"` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags` | `[]` | `["premium", "scenic", "historic"]` | `estimated` | no |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `regional_data_ids.osm_relation` | `null` | `"47235"` | `verified_with_adjustment` | no |
| `ski_area:cortina-dampezzo-ski-area` | `base_elevation_m` | `1224` | `1217` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `summit_elevation_m` | `2930` | `2828` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `season_end_month` | `4` | `5` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows` | `null` | `[{"end_date": "2027-05-02", "season_label": "2026/2027", "start_date": "2026-11-21", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `total_piste_km` | `null` | `120` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `total_lift_count` | `null` | `26` | `verified` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `piste_km_by_difficulty` | `null` | `{"advanced": 16, "beginner": 45, "intermediate": 59}` | `verified_with_adjustment` | yes |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `destination:cortina-dampezzo` | `resort_id` | `reviewed-no-change` | Stable catalog id retained. |
| `destination:cortina-dampezzo` | `name` | `reviewed-no-change` | Display name matches official destination spelling. |
| `destination:cortina-dampezzo` | `country` | `reviewed-no-change` | Official/open sources place the destination in Italy. |
| `destination:cortina-dampezzo` | `region` | `reviewed-no-change` | Dolomites regional grouping retained. |
| `destination:cortina-dampezzo` | `price_level` | `reviewed-no-change` | Premium destination estimate retained pending lodging sampling policy. |
| `destination:cortina-dampezzo` | `latitude` | `reviewed-no-change` | Existing display coordinate remains a town-center approximation. |
| `destination:cortina-dampezzo` | `longitude` | `reviewed-no-change` | Existing display coordinate remains a town-center approximation. |
| `destination:cortina-dampezzo` | `base_elevation_m` | `reviewed-no-change` | Destination town/base elevation retained; ski-area base was normalized separately. |
| `destination:cortina-dampezzo` | `summit_elevation_m` | `reviewed-no-change` | Destination-level 2930 m retained as broad resort metadata; modeled ski-area summit was normalized to reviewed ski-area scope. |
| `destination:cortina-dampezzo` | `season_start_month` | `changed` | Updated to match late-November operating window. |
| `destination:cortina-dampezzo` | `season_end_month` | `changed` | Updated to match early-May operating window. |
| `destination:cortina-dampezzo` | `season_windows` | `changed` | Added exact 2026/27 window from reviewed operating-time source. |
| `destination:cortina-dampezzo` | `lift_pass_products` | `changed` | Added default Valle Skipass product. |
| `destination:cortina-dampezzo` | `ski_areas` | `reviewed-no-change` | Container and ski-area id retained; child ski-area fields carry the changed rows. |
| `destination:cortina-dampezzo` | `terrain_groups` | `not-applicable` | No separate destination-local child ski-area split was introduced in this PR. |
| `destination:cortina-dampezzo` | `stay_bases` | `reviewed-no-change` | Existing stay-base container retained; child stay-base fields carry the changed rows. |
| `destination:cortina-dampezzo` | `rentals` | `reviewed-no-change` | Kept Cortina Pro Sport display name stable for seed-data expectations; official rental page supports the provider identity. |
| `lift_pass_product:cortina-valle-skipass` | `lift_pass_product_id` | `changed` | Stable id normalized from source product name. |
| `lift_pass_product:cortina-valle-skipass` | `name` | `changed` | Official Cortina page names the valley pass. |
| `lift_pass_product:cortina-valle-skipass` | `validity_scope` | `changed` | Modeled as regional network because the pass includes neighboring San Vito and Auronzo-Misurina terrain outside the main destination. |
| `lift_pass_product:cortina-valle-skipass` | `valid_ski_area_ids` | `changed` | References the single existing Cortina ski-area model. |
| `lift_pass_product:cortina-valle-skipass` | `external_validity_summary` | `changed` | External validity copied into a summary rather than a shared terrain domain. |
| `lift_pass_product:cortina-valle-skipass` | `prices[0]` | `changed` | Added one representative adult day-ticket price; full tariff table was not copied. |
| `ski_area:cortina-dampezzo-ski-area` | `ski_area_id` | `reviewed-no-change` | Existing ski-area id retained to avoid weather/climatology migration. |
| `ski_area:cortina-dampezzo-ski-area` | `name` | `reviewed-no-change` | Source pages support the Cortina d'Ampezzo ski-area display name. |
| `ski_area:cortina-dampezzo-ski-area` | `latitude` | `reviewed-no-change` | Existing weather lookup coordinate retained. |
| `ski_area:cortina-dampezzo-ski-area` | `longitude` | `reviewed-no-change` | Existing weather lookup coordinate retained. |
| `ski_area:cortina-dampezzo-ski-area` | `base_elevation_m` | `changed` | Normalized from town elevation to reviewed ski-area base elevation. |
| `ski_area:cortina-dampezzo-ski-area` | `summit_elevation_m` | `changed` | Normalized from broad 2930 m resort metadata to reviewed ski-area summit elevation. |
| `ski_area:cortina-dampezzo-ski-area` | `season_start_month` | `changed` | Updated from December to November. |
| `ski_area:cortina-dampezzo-ski-area` | `season_end_month` | `changed` | Updated from April to May. |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows` | `changed` | Added exact 2026/27 operating window. |
| `ski_area:cortina-dampezzo-ski-area` | `total_piste_km` | `changed` | Official Cortina page supports 120 km for the local valley pass scope. |
| `ski_area:cortina-dampezzo-ski-area` | `total_lift_count` | `changed` | Official Cortina page lists 26 lifts. |
| `ski_area:cortina-dampezzo-ski-area` | `piste_km_by_difficulty` | `changed` | Difficulty-km split uses reviewed-editorial fallback because official page does not publish blue/red/black kilometers. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `stay_base_id` | `changed` | Added explicit stable id. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `name` | `reviewed-no-change` | Town stay-base name retained. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `price_range` | `reviewed-no-change` | Lodging price range remains an estimate pending sampling policy. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `quality` | `reviewed-no-change` | Premium quality tier remains a product estimate. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `lift_distance` | `changed` | Updated to near based on town-center to Faloria lower-station geometry. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `supported_skill_levels` | `reviewed-no-change` | Kept existing intermediate/advanced policy stable; broad beginner support remains an owner policy decision. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `latitude` | `changed` | Added existing destination display latitude to the stay-base record. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `longitude` | `changed` | Added existing destination display longitude to the stay-base record. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_name` | `changed` | Added nearest lift source-backed by OSM/Nominatim lookup. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_distance_m` | `changed` | Rounded Haversine distance from catalog stay-base coordinate to OSM Faloria station. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `access_mode` | `changed` | Set to walk because the lower Faloria station is within 500 m of the modeled stay-base coordinate. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `base_type` | `changed` | Classified as town stay base. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags` | `changed` | Added product-facing descriptive tags as estimates. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `regional_data_ids.osm_relation` | `changed` | Added OSM relation id for the town boundary. |
| `rental:Cortina Pro Sport` | `name` | `reviewed-no-change` | Display name kept stable and supported by official provider page. |
| `rental:Cortina Pro Sport` | `price_range` | `reviewed-no-change` | Rental price range remains an estimate because the provider page did not expose a complete stable price table. |
| `rental:Cortina Pro Sport` | `quality` | `reviewed-no-change` | Rental quality tier remains an estimate. |
| `rental:Cortina Pro Sport` | `lift_distance` | `reviewed-no-change` | Near rental distance retained; provider address is in central Cortina. |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `destination:cortina-dampezzo` | `season_start_month` | [Skiresort.info - Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `11` | Reviewed ski-area page lists the current season as starting in late November. |  |
| `destination:cortina-dampezzo` | `season_end_month` | [Skiresort.info - Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `5` | Reviewed ski-area page lists the current season as ending in early May. |  |
| `destination:cortina-dampezzo` | `season_windows` | [Skiresort.info - Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `[{"end_date": "2027-05-02", "season_label": "2026/2027", "start_date": "2026-11-21", "status": "planned"}]` | Reviewed ski-area page lists current-season operating dates as 2026-11-21 to 2027-05-02. |  |
| `lift_pass_product:cortina-valle-skipass` | `lift_pass_product_id` | [Cortina Dolomiti - Lifts](https://cortina.dolomiti.org/en/winter/plan/lifts/) | `"Valle Skipass"` | Official Cortina page names the valley pass product. | Normalized source product name into a stable lowercase catalog id. |
| `destination:cortina-dampezzo` | `lift_pass_products` | [Cortina Dolomiti - Lifts](https://cortina.dolomiti.org/en/winter/plan/lifts/) | `["Valle Skipass"]` | Official Cortina page names Valle Skipass as a local pass product. | Mapped source product name to the stable catalog lift_pass_product_id. |
| `lift_pass_product:cortina-valle-skipass` | `name` | [Cortina Dolomiti - Lifts](https://cortina.dolomiti.org/en/winter/plan/lifts/) | `"Valle Skipass"` | Official Cortina page names Valle Skipass as the local pass. | Catalog display name adds Cortina for clarity. |
| `lift_pass_product:cortina-valle-skipass` | `validity_scope` | [Cortina Dolomiti - Lifts](https://cortina.dolomiti.org/en/winter/plan/lifts/) | `"regional_network"` | Official page says the pass covers Cortina d'Ampezzo plus San Vito di Cadore and Auronzo-Misurina. |  |
| `lift_pass_product:cortina-valle-skipass` | `valid_ski_area_ids` | [Cortina Dolomiti - Lifts](https://cortina.dolomiti.org/en/winter/plan/lifts/) | `["Cortina d'Ampezzo area"]` | Official pass source anchors the product to the Cortina ski area. | Mapped the source area to the existing local ski_area_id rather than introducing a ski-area migration. |
| `lift_pass_product:cortina-valle-skipass` | `external_validity_summary` | [Cortina Dolomiti - Lifts](https://cortina.dolomiti.org/en/winter/plan/lifts/) | `"Also covers Cortina Skyline and Lagazuoi down to Armentarola, San Vito di Cadore, and Auronzo-Misurina within the Cortina valley pass area."` | Official pass description lists the neighboring areas included in Valle Skipass. |  |
| `lift_pass_product:cortina-valle-skipass` | `prices[0]` | [Skiresort.info - Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `{"amount": 80, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "main season", "source_url": "https://www.skiresort.info/ski-resort/cortina-dampezzo/"}` | Reviewed ski-area page lists the adult main-season day ticket at EUR 80. |  |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `stay_base_id` | [OpenStreetMap - Cortina d'Ampezzo](https://www.openstreetmap.org/relation/47235) | `"Cortina d'Ampezzo"` | OSM relation identifies the Cortina d'Ampezzo place/boundary used for the stay base. | Normalized place name into the catalog stay_base_id. |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `lift_distance` | [OpenStreetMap - Funivia Faloria](https://www.openstreetmap.org/node/606939921) | `"near"` | OSM identifies Funivia Faloria as a lift station within a near/walkable distance of the modeled town coordinate. |  |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `latitude` | [OpenStreetMap - Cortina d'Ampezzo](https://www.openstreetmap.org/relation/47235) | `46.5405` | Catalog keeps the existing town-center coordinate while linking the stay base to the OSM Cortina relation. |  |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `longitude` | [OpenStreetMap - Cortina d'Ampezzo](https://www.openstreetmap.org/relation/47235) | `12.1357` | Catalog keeps the existing town-center coordinate while linking the stay base to the OSM Cortina relation. |  |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_name` | [OpenStreetMap - Funivia Faloria](https://www.openstreetmap.org/node/606939921) | `"Funivia Faloria"` | OSM identifies the nearby Faloria cable-car station. |  |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_distance_m` | [OpenStreetMap - Funivia Faloria](https://www.openstreetmap.org/node/606939921) | `472` | Rounded Haversine distance from the modeled Cortina stay-base coordinate to OSM node 606939921. |  |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `access_mode` | [OpenStreetMap - Funivia Faloria](https://www.openstreetmap.org/node/606939921) | `"walk"` | The source-backed nearest-lift distance is under the catalog walkable threshold. |  |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `base_type` | [OpenStreetMap - Cortina d'Ampezzo](https://www.openstreetmap.org/relation/47235) | `"town"` | OSM relation represents Cortina d'Ampezzo as the destination town boundary. |  |
| `stay_base:cortina-dampezzo-cortina-dampezzo` | `regional_data_ids.osm_relation` | [OpenStreetMap - Cortina d'Ampezzo](https://www.openstreetmap.org/relation/47235) | `"47235"` | OSM relation id captured for the town stay base. |  |
| `ski_area:cortina-dampezzo-ski-area` | `base_elevation_m` | [Skiresort.info - Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `1217` | Reviewed ski-area page lists the winter sports area elevation base at 1217 m. |  |
| `ski_area:cortina-dampezzo-ski-area` | `summit_elevation_m` | [Skiresort.info - Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `2828` | Reviewed ski-area page lists the winter sports area top elevation at 2828 m. |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_start_month` | [Skiresort.info - Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `11` | Reviewed ski-area page lists current season opening in November. |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_end_month` | [Skiresort.info - Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `5` | Reviewed ski-area page lists current season closing in May. |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows` | [Skiresort.info - Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `[{"end_date": "2027-05-02", "season_label": "2026/2027", "start_date": "2026-11-21", "status": "planned"}]` | Reviewed ski-area page lists current-season operating dates as 2026-11-21 to 2027-05-02. |  |
| `ski_area:cortina-dampezzo-ski-area` | `total_piste_km` | [Cortina Dolomiti - Lifts](https://cortina.dolomiti.org/en/winter/plan/lifts/) | `120` | Official Cortina page states the valley pass area totals 120 km of slopes. |  |
| `ski_area:cortina-dampezzo-ski-area` | `total_lift_count` | [Cortina Dolomiti - Lifts](https://cortina.dolomiti.org/en/winter/plan/lifts/) | `26` | Official Cortina page says the ski area is served by 26 lifts. |  |
| `ski_area:cortina-dampezzo-ski-area` | `piste_km_by_difficulty` | [Skiresort.info - Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `{"advanced": 16, "beginner": 45, "intermediate": 59}` | Reviewed ski-area page publishes the 120 km slope total split into easy, intermediate, and difficult kilometers. |  |

## Ranking Impact

Ranking comparison completed with rows=12 and groups=11. Cortina d'Ampezzo did not appear in the emitted top-result comparison rows, so no current canned scenario reports a Cortina rank or score delta.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-27-cortina-dampezzo.json --markdown-output docs/catalog-curation/2026-06-27-cortina-dampezzo.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`
- `git diff --check`

## Caveats

- The existing single ski-area id was retained to avoid a weather/climatology evidence migration; a future owner-reviewed model could split Cortina sectors or external San Vito/Auronzo validity if that becomes product-relevant.
- Official Cortina sources support 120 km and 26 lifts; the blue/red/black kilometer split and exact 2026/27 window use reviewed-editorial data because the official pages reviewed here did not publish those fields in a stable structured table.
- The Valle Skipass external validity is summarized on the pass product rather than modeled as a terrain domain because San Vito di Cadore and Auronzo-Misurina are not separate Snowcast destinations.
- Lodging price range, stay-base quality tier, supported skill levels, rental price range, rental quality tier, and atmosphere tags remain estimates pending dedicated policy or source sampling.
