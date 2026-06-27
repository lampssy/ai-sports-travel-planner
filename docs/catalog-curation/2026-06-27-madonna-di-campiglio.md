# Madonna di Campiglio Catalog Curation

Full destination sweep for Madonna di Campiglio. Added a source-backed Skiarea Campiglio Dolomiti di Brenta pass product, exact 2026/27 operating window, ski-area terrain metrics, source-backed stay-base access metadata, rental-provider evidence, and external trust-manifest references while keeping lodging price, quality, broad skill support, and rental quality as estimates.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:madonna-di-campiglio` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `destination:madonna-di-campiglio` | `season_windows` | `null` | `[{"end_date": "2027-04-11", "season_label": "2026/2027", "start_date": "2026-11-21", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `destination:madonna-di-campiglio` | `lift_pass_products` | `null` | `["campiglio-dolomiti-di-brenta-skiarea-skipass"]` | `verified_with_adjustment` | yes |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `lift_pass_product_id` | `null` | `"campiglio-dolomiti-di-brenta-skiarea-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `name` | `null` | `"Skiarea Campiglio Dolomiti di Brenta Skipass"` | `verified` | no |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | yes |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `valid_ski_area_ids` | `null` | `["madonna-di-campiglio-ski-area"]` | `verified_with_adjustment` | yes |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `external_validity_summary` | `null` | `"Also covers the linked Pinzolo and Folgarida-Marilleva/Pejo lift-company network under the Skiarea Campiglio Dolomiti di Brenta pass."` | `verified_with_adjustment` | yes |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `prices[0]` | `null` | `{"amount": 85, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "high season 2025/26", "source_url": "https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"}` | `verified` | no |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `prices[1]` | `null` | `{"amount": 237, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "high season 2025/26", "source_url": "https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"}` | `verified` | no |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `prices[2]` | `null` | `{"amount": 424, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "high season 2025/26", "source_url": "https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"}` | `verified` | no |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `stay_base_id` | `null` | `"madonna-di-campiglio-madonna-di-campiglio"` | `verified_with_adjustment` | no |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `latitude` | `null` | `46.2267` | `verified_with_adjustment` | no |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `longitude` | `null` | `10.8268` | `verified_with_adjustment` | no |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_name` | `null` | `"Spinale Express"` | `verified_with_adjustment` | yes |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_distance_m` | `null` | `277` | `verified_with_adjustment` | yes |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `base_type` | `null` | `"town"` | `verified` | no |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags` | `[]` | `["scenic", "premium", "family-friendly"]` | `estimated` | no |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `regional_data_ids.osm_node` | `null` | `"1796357582"` | `verified` | no |
| `ski_area:madonna-di-campiglio-ski-area` | `base_elevation_m` | `1550` | `852` | `verified_with_adjustment` | yes |
| `ski_area:madonna-di-campiglio-ski-area` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `ski_area:madonna-di-campiglio-ski-area` | `season_windows` | `null` | `[{"end_date": "2027-04-11", "season_label": "2026/2027", "start_date": "2026-11-21", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:madonna-di-campiglio-ski-area` | `total_piste_km` | `null` | `156` | `verified` | yes |
| `ski_area:madonna-di-campiglio-ski-area` | `total_lift_count` | `null` | `61` | `verified` | yes |
| `ski_area:madonna-di-campiglio-ski-area` | `piste_km_by_difficulty` | `null` | `{"advanced": 33, "beginner": 50, "intermediate": 72}` | `verified_with_adjustment` | yes |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `destination:madonna-di-campiglio` | `resort_id` | `reviewed-no-change` | Stable catalog id retained. |
| `destination:madonna-di-campiglio` | `name` | `reviewed-no-change` | Display name matches official destination spelling. |
| `destination:madonna-di-campiglio` | `country` | `reviewed-no-change` | Official and open sources place the destination in Italy. |
| `destination:madonna-di-campiglio` | `region` | `reviewed-no-change` | Dolomites regional grouping retained. |
| `destination:madonna-di-campiglio` | `price_level` | `reviewed-no-change` | Premium destination estimate retained pending lodging sampling policy. |
| `destination:madonna-di-campiglio` | `latitude` | `reviewed-no-change` | Existing display coordinate remains a town-center approximation. |
| `destination:madonna-di-campiglio` | `longitude` | `reviewed-no-change` | Existing display coordinate remains a town-center approximation. |
| `destination:madonna-di-campiglio` | `base_elevation_m` | `reviewed-no-change` | Destination town/base elevation retained; ski-area base was normalized separately. |
| `destination:madonna-di-campiglio` | `summit_elevation_m` | `reviewed-no-change` | Existing destination-level summit metadata retained. |
| `destination:madonna-di-campiglio` | `season_start_month` | `changed` | Updated to match late-November operating window. |
| `destination:madonna-di-campiglio` | `season_end_month` | `reviewed-no-change` | April closing month retained. |
| `destination:madonna-di-campiglio` | `season_windows` | `changed` | Added exact 2026/27 window from reviewed operating-time source. |
| `destination:madonna-di-campiglio` | `lift_pass_products` | `changed` | Added default Skiarea Campiglio Dolomiti di Brenta pass product. |
| `destination:madonna-di-campiglio` | `ski_areas` | `reviewed-no-change` | Container and ski-area id retained; child ski-area fields carry the changed rows. |
| `destination:madonna-di-campiglio` | `terrain_groups` | `not-applicable` | No separate child terrain split was introduced in this PR. |
| `destination:madonna-di-campiglio` | `stay_bases` | `reviewed-no-change` | Existing stay-base container retained; child stay-base fields carry the changed rows. |
| `destination:madonna-di-campiglio` | `rentals` | `reviewed-no-change` | Kept Ski Rent Campiglio display name stable for seed-data expectations; provider page supports the rental identity. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `lift_pass_product_id` | `changed` | Stable id normalized from source product name. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `name` | `changed` | Official pass page names the Skiarea skipass. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `validity_scope` | `changed` | Modeled as regional network because the pass covers linked lift-company areas outside the local Madonna ski-area id. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `valid_ski_area_ids` | `changed` | References the existing Madonna di Campiglio ski-area model. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `external_validity_summary` | `changed` | External validity is summarized rather than modeled as a shared terrain domain. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `prices[0]` | `changed` | Added representative adult one-day high-season price. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `prices[1]` | `changed` | Added representative adult three-day high-season price. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `prices[2]` | `changed` | Added representative adult six-day high-season price. |
| `ski_area:madonna-di-campiglio-ski-area` | `ski_area_id` | `reviewed-no-change` | Existing ski-area id retained to avoid weather/climatology migration. |
| `ski_area:madonna-di-campiglio-ski-area` | `name` | `reviewed-no-change` | Source pages support the Madonna di Campiglio ski-area display name. |
| `ski_area:madonna-di-campiglio-ski-area` | `latitude` | `reviewed-no-change` | Existing weather lookup coordinate retained. |
| `ski_area:madonna-di-campiglio-ski-area` | `longitude` | `reviewed-no-change` | Existing weather lookup coordinate retained. |
| `ski_area:madonna-di-campiglio-ski-area` | `base_elevation_m` | `changed` | Normalized from town elevation to reviewed ski-area network base elevation. |
| `ski_area:madonna-di-campiglio-ski-area` | `summit_elevation_m` | `reviewed-no-change` | Reviewed source confirms the existing 2504 m top elevation. |
| `ski_area:madonna-di-campiglio-ski-area` | `season_start_month` | `changed` | Updated from December to November. |
| `ski_area:madonna-di-campiglio-ski-area` | `season_end_month` | `reviewed-no-change` | April closing month retained. |
| `ski_area:madonna-di-campiglio-ski-area` | `season_windows` | `changed` | Added exact 2026/27 operating window. |
| `ski_area:madonna-di-campiglio-ski-area` | `total_piste_km` | `changed` | Official Campiglio Dolomiti source supports 156 km of slopes. |
| `ski_area:madonna-di-campiglio-ski-area` | `total_lift_count` | `changed` | Official Campiglio Dolomiti live-info source supports 61 lifts. |
| `ski_area:madonna-di-campiglio-ski-area` | `piste_km_by_difficulty` | `changed` | Difficulty-km split uses reviewed-editorial fallback because the official page does not publish blue/red/black kilometers. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `stay_base_id` | `changed` | Added explicit stable id. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `name` | `reviewed-no-change` | Town stay-base name retained. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `price_range` | `reviewed-no-change` | Lodging price range remains an estimate pending sampling policy. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `quality` | `reviewed-no-change` | Quality tier remains a product estimate. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `lift_distance` | `reviewed-no-change` | Existing near bucket is supported by the source-backed 277 m nearest-lift distance. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `supported_skill_levels` | `reviewed-no-change` | Kept existing beginner/intermediate policy stable; broader advanced support remains an owner policy decision. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `latitude` | `changed` | Added existing destination display latitude to the stay-base record. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `longitude` | `changed` | Added existing destination display longitude to the stay-base record. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_name` | `changed` | Added nearest lift source-backed by OSM/Nominatim lookup. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_distance_m` | `changed` | Rounded Haversine distance from catalog stay-base coordinate to OSM Spinale Express station. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `access_mode` | `changed` | Set to walk because the lower Spinale Express station is within 300 m of the modeled stay-base coordinate. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `base_type` | `changed` | Classified as town stay base. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags` | `changed` | Added product-facing descriptive tags as estimates. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `regional_data_ids.osm_node` | `changed` | Added OSM node id for the town stay base. |
| `rental:Ski Rent Campiglio` | `name` | `reviewed-no-change` | Display name kept stable and supported by provider page. |
| `rental:Ski Rent Campiglio` | `price_range` | `reviewed-no-change` | Rental price range remains an estimate because no catalog pricing policy was introduced. |
| `rental:Ski Rent Campiglio` | `quality` | `reviewed-no-change` | Rental quality tier remains an estimate. |
| `rental:Ski Rent Campiglio` | `lift_distance` | `reviewed-no-change` | Near rental distance retained. |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `destination:madonna-di-campiglio` | `season_start_month` | [Skiresort.info - Madonna di Campiglio/Pinzolo/Folgarida/Marilleva](https://www.skiresort.info/ski-resort/madonna-di-campiglio-pinzolo-folgarida-marilleva/) | `11` | Reviewed ski-area page lists the current season as starting in late November. |  |
| `destination:madonna-di-campiglio` | `season_windows` | [Skiresort.info - Madonna di Campiglio/Pinzolo/Folgarida/Marilleva](https://www.skiresort.info/ski-resort/madonna-di-campiglio-pinzolo-folgarida-marilleva/) | `[{"end_date": "2027-04-11", "season_label": "2026/2027", "start_date": "2026-11-21", "status": "planned"}]` | Reviewed ski-area page lists current-season operating dates as 2026-11-21 to 2027-04-11. |  |
| `destination:madonna-di-campiglio` | `lift_pass_products` | [Campiglio Dolomiti - Skipass Skiarea](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Skiarea Campiglio Dolomiti di Brenta Skipass"` | Official pass page describes the Skiarea skipass product. | Mapped the source product name to the stable catalog lift_pass_product_id. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `lift_pass_product_id` | [Campiglio Dolomiti - Skipass Skiarea](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Skiarea Campiglio Dolomiti di Brenta Skipass"` | Official pass page describes the Skiarea skipass product. | Normalized source product name into a stable lowercase catalog id. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `name` | [Campiglio Dolomiti - Skipass Skiarea](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Skiarea Campiglio Dolomiti di Brenta Skipass"` | Official pass page names the Skiarea skipass product. |  |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `validity_scope` | [Campiglio Dolomiti - Skipass Skiarea](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"regional_network"` | Official page says the pass permits unlimited circulation on the Funivie Madonna di Campiglio, Pinzolo, and Folgarida-Marilleva/Pejo areas. |  |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `valid_ski_area_ids` | [Campiglio Dolomiti - Skipass Skiarea](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `["Madonna di Campiglio"]` | Official pass source anchors the product to the Madonna di Campiglio lift-company area. | Mapped the source area to the existing local ski_area_id rather than introducing a ski-area migration. |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `external_validity_summary` | [Campiglio Dolomiti - Skipass Skiarea](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Also covers the linked Pinzolo and Folgarida-Marilleva/Pejo lift-company network under the Skiarea Campiglio Dolomiti di Brenta pass."` | Official pass description lists the linked areas included in the Skiarea product. |  |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `prices[0]` | [Campiglio Dolomiti - Skipass Skiarea](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `{"amount": 85, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "high season 2025/26", "source_url": "https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"}` | Official tariff table lists the adult high-season one-day pass at EUR 85. |  |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `prices[1]` | [Campiglio Dolomiti - Skipass Skiarea](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `{"amount": 237, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "high season 2025/26", "source_url": "https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"}` | Official tariff table lists the adult high-season three-day pass at EUR 237. |  |
| `lift_pass_product:campiglio-dolomiti-di-brenta-skiarea-skipass` | `prices[2]` | [Campiglio Dolomiti - Skipass Skiarea](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `{"amount": 424, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "high season 2025/26", "source_url": "https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"}` | Official tariff table lists the adult high-season six-day pass at EUR 424. |  |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `stay_base_id` | [OpenStreetMap - Madonna di Campiglio](https://www.openstreetmap.org/node/1796357582) | `"Madonna di Campiglio"` | OSM node identifies the Madonna di Campiglio place used for the stay base. | Normalized place name into the catalog stay_base_id. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `latitude` | [OpenStreetMap - Madonna di Campiglio](https://www.openstreetmap.org/node/1796357582) | `46.2269942` | OSM place node corroborates the modeled town stay-base latitude. | Catalog keeps the existing rounded town-center latitude. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `longitude` | [OpenStreetMap - Madonna di Campiglio](https://www.openstreetmap.org/node/1796357582) | `10.8270157` | OSM place node corroborates the modeled town stay-base longitude. | Catalog keeps the existing rounded town-center longitude. |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_name` | [OpenStreetMap - Spinale Express](https://www.openstreetmap.org/node/1023438277) | `"Spinale Express"` | OSM identifies the nearby Spinale Express lift station. |  |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_distance_m` | [OpenStreetMap - Spinale Express](https://www.openstreetmap.org/node/1023438277) | `277` | Rounded Haversine distance from the modeled Madonna di Campiglio stay-base coordinate to OSM node 1023438277. |  |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `access_mode` | [OpenStreetMap - Spinale Express](https://www.openstreetmap.org/node/1023438277) | `"walk"` | The source-backed nearest-lift distance is under the catalog walkable threshold. |  |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `base_type` | [OpenStreetMap - Madonna di Campiglio](https://www.openstreetmap.org/node/1796357582) | `"town"` | OSM place node represents Madonna di Campiglio as the destination town stay base. |  |
| `stay_base:madonna-di-campiglio-madonna-di-campiglio` | `regional_data_ids.osm_node` | [OpenStreetMap - Madonna di Campiglio](https://www.openstreetmap.org/node/1796357582) | `"1796357582"` | OSM node id captured for the town stay base. |  |
| `ski_area:madonna-di-campiglio-ski-area` | `base_elevation_m` | [Skiresort.info - Madonna di Campiglio/Pinzolo/Folgarida/Marilleva](https://www.skiresort.info/ski-resort/madonna-di-campiglio-pinzolo-folgarida-marilleva/) | `852` | Reviewed ski-area page lists the connected winter sports area base elevation at 852 m. |  |
| `ski_area:madonna-di-campiglio-ski-area` | `season_start_month` | [Skiresort.info - Madonna di Campiglio/Pinzolo/Folgarida/Marilleva](https://www.skiresort.info/ski-resort/madonna-di-campiglio-pinzolo-folgarida-marilleva/) | `11` | Reviewed ski-area page lists current season opening in November. |  |
| `ski_area:madonna-di-campiglio-ski-area` | `season_windows` | [Skiresort.info - Madonna di Campiglio/Pinzolo/Folgarida/Marilleva](https://www.skiresort.info/ski-resort/madonna-di-campiglio-pinzolo-folgarida-marilleva/) | `[{"end_date": "2027-04-11", "season_label": "2026/2027", "start_date": "2026-11-21", "status": "planned"}]` | Reviewed ski-area page lists current-season operating dates as 2026-11-21 to 2027-04-11. |  |
| `ski_area:madonna-di-campiglio-ski-area` | `total_piste_km` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `156` | Official Campiglio Dolomiti page states the ski area totals 156 km of slopes. |  |
| `ski_area:madonna-di-campiglio-ski-area` | `total_lift_count` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `61` | Official Campiglio Dolomiti page exposes live lift status over 61 total lifts. |  |
| `ski_area:madonna-di-campiglio-ski-area` | `piste_km_by_difficulty` | [Skiresort.info - Madonna di Campiglio/Pinzolo/Folgarida/Marilleva](https://www.skiresort.info/ski-resort/madonna-di-campiglio-pinzolo-folgarida-marilleva/) | `{"advanced": 33, "beginner": 50, "intermediate": 72}` | Reviewed ski-area page publishes the connected-area slope total split into easy, intermediate, and difficult kilometers. |  |

## Ranking Impact

Ranking comparison completed with rows=12 and groups=11. Madonna di Campiglio appears in the italy_beginner_value scenario at current rank 3 and candidate rank 3, with rank_delta=0 and candidate_score=0.480.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-27-madonna-di-campiglio.json --markdown-output docs/catalog-curation/2026-06-27-madonna-di-campiglio.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`
- `git diff --check`

## Caveats

- The existing single ski-area id was retained to avoid a weather/climatology evidence migration; a future owner-reviewed model could split Pinzolo and Folgarida-Marilleva/Pejo if that becomes product-relevant.
- Official Campiglio Dolomiti sources support 156 km and 61 lifts; the blue/red/black kilometer split, base elevation, and exact 2026/27 window use reviewed-editorial data because the official pages reviewed here did not publish those fields in a stable structured table.
- The Skiarea pass external validity is summarized on the pass product rather than modeled as a terrain domain because Pinzolo and Folgarida-Marilleva/Pejo are not separate Snowcast destinations.
- Lodging price range, stay-base quality tier, supported skill levels, rental price range, rental quality tier, and atmosphere tags remain estimates pending dedicated policy or source sampling.
