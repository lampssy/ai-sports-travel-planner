# Grindelwald and Wengen full catalog curation - destination and ski-area topology correction

Rebuilds PR #22 on current main. Grindelwald and Wengen are modeled as separate stay destinations in one Jungfrau Region trip market; the connected Grindelwald-Wengen weather owner is retained; Grindelwald-First is added as an independently operated ski area; and three source-backed base-to-area access edges replace the legacy combined relationship. The regional pass owns its published 211 km aggregate and Winter 2026/27 1-, 3-, and 6-day price ranges, while the missing Mürren graph is explicitly deferred.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:jungfrau-ski-region-pass` | `full` | all canonical fields |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `full` | all canonical fields |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `full` | all canonical fields |
| `ski_area:grindelwald-first-ski-area` | `full` | all canonical fields |
| `ski_area:grindelwald-wengen-ski-area` | `full` | all canonical fields |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `full` | all canonical fields |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `full` | all canonical fields |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `full` | all canonical fields |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `full` | all canonical fields |
| `ski_region:grindelwald-wengen` | `full` | all canonical fields |
| `stay_base:grindelwald-grindelwald` | `full` | all canonical fields |
| `stay_base:grindelwald-wengen-grindelwald` | `full` | all canonical fields |
| `stay_base:wengen-wengen` | `full` | all canonical fields |
| `stay_destination:grindelwald` | `full` | all canonical fields |
| `stay_destination:grindelwald-wengen` | `full` | all canonical fields |
| `stay_destination:wengen` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:jungfrau-ski-region-pass` | `full` | all canonical fields |
| `trust_manifest:rental_display_facts:grindelwald-buri-sport-grindelwald` | `full` | all canonical fields |
| `trust_manifest:rental_display_facts:grindelwald-wengen-buri-sport-grindelwald` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:grindelwald-first-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:grindelwald-wengen-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_regions:grindelwald-wengen` | `full` | all canonical fields |
| `trust_manifest:stay_bases:grindelwald-grindelwald` | `full` | all canonical fields |
| `trust_manifest:stay_bases:grindelwald-wengen-grindelwald` | `full` | all canonical fields |
| `trust_manifest:stay_bases:wengen-wengen` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:grindelwald` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:grindelwald-wengen` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:wengen` | `full` | all canonical fields |

## Entity Scope Assessments

| Candidate | Kind | Disposition | Signals | Catalog Targets | Evidence | Backlog | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `grindelwald-wengen-combined-stay-market` (Legacy combined Grindelwald-Wengen stay market) | `stay_destination` | `not_separate` | `independent_stay_market` | `stay_destination:grindelwald-wengen` | `scope-combined-destination` |  | The legacy combined accommodation owner is retired because official tourism establishes separate Grindelwald and Wengen stay markets. |
| `grindelwald` (Grindelwald) | `stay_destination` | `add_entity` | `independent_stay_market`, `distinct_access` | `stay_destination:grindelwald` | `change-153` |  | Grindelwald has an independent accommodation identity and direct access to two distinct ski areas. |
| `wengen` (Wengen) | `stay_destination` | `add_entity` | `independent_stay_market`, `distinct_access` | `stay_destination:wengen` | `change-171` |  | Wengen is a separate car-free accommodation market with its own direct lift access. |
| `grindelwald-wengen-grindelwald` (Legacy Grindelwald base under combined destination) | `stay_base` | `not_separate` | `distinct_access` | `stay_base:grindelwald-wengen-grindelwald` | `scope-combined-base` |  | The legacy record is retired and replaced by the correctly owned Grindelwald base. |
| `grindelwald-grindelwald` (Grindelwald) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:grindelwald-grindelwald` | `change-121` |  | The village base owns local character, lodging context, and two explicit access edges. |
| `wengen-wengen` (Wengen) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:wengen-wengen` | `change-148` |  | The car-free village base owns its local character and direct cableway access. |
| `grindelwald-grund` (Grindelwald Grund and Terminal) | `stay_base` | `not_separate` | `distinct_access` | `stay_base:grindelwald-grindelwald` | `scope-grindelwald-grund` |  | Official material presents Grund and Terminal as Grindelwald access points rather than a separate accommodation recommendation market. |
| `grindelwald-first-ski-area` (Grindelwald-First) | `ski_area` | `add_entity` | `official_independent_identity`, `separate_operator`, `independent_status_or_schedule` | `ski_area:grindelwald-first-ski-area` | `change-040` |  | Independent operator, schedule, status, map, and child terrain metrics require a separate ski-area owner. |
| `grindelwald-wengen-ski-area` (Grindelwald-Wengen) | `ski_area` | `represented` | `official_independent_identity`, `ski_connected_terrain` | `ski_area:grindelwald-wengen-ski-area` | `change-051` |  | The retained stable weather owner represents the connected Kleine Scheidegg-Männlichen terrain serving Grindelwald and Wengen. |
| `grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` (Legacy combined-base access) | `ski_area_access` | `not_separate` | `direct_access_relationship` | `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `scope-combined-access` |  | The relationship is retained under a corrected Grindelwald base and access identity. |
| `grindelwald-grindelwald--grindelwald-first-ski-area` (Grindelwald to Grindelwald-First) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `change-072` |  | Official arrival guidance and lift geometry establish direct walk access. |
| `grindelwald-grindelwald--grindelwald-wengen-ski-area` (Grindelwald to Grindelwald-Wengen) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `change-082` |  | Official winter bus service and Terminal geometry establish the feeder relationship. |
| `wengen-wengen--grindelwald-wengen-ski-area` (Wengen to Grindelwald-Wengen) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `change-100` |  | Official tourism and lift geometry establish direct walk access. |
| `jungfrau-ski-region-pass` (Jungfrau Ski Region ski pass) | `lift_pass_product` | `add_entity` | `official_product_identity` | `lift_pass_product:jungfrau-ski-region-pass` | `change-004` |  | The published regional product owns shared availability, modeled coverage, aggregate terrain, and representative prices. |
| `jungfrau-ski-region-terrain-domain` (Jungfrau Ski Region terrain) | `terrain_domain` | `external_pass_context` | `disconnected_terrain`, `official_product_identity` |  | `scope-jungfrau-network` |  | Shared ticket validity and regional branding do not create one ski-connected terrain domain. |
| `murren` (Mürren) | `stay_destination` | `deferred` | `independent_stay_market`, `distinct_access` |  | `scope-murren` | `docs/product-backlog.md#jungfrau-region-catalog-extension` | Mürren is a separate accommodation market whose complete graph belongs in a focused curation. |
| `murren-murren` (Mürren) | `stay_base` | `deferred` | `distinct_access` |  | `scope-murren` | `docs/product-backlog.md#jungfrau-region-catalog-extension` | The Mürren base depends on the deferred destination and ski-area graph. |
| `murren-schilthorn-ski-area` (Mürren-Schilthorn) | `ski_area` | `deferred` | `official_independent_identity`, `separate_operator`, `independent_status_or_schedule` |  | `scope-murren` | `docs/product-backlog.md#jungfrau-region-catalog-extension` | The independent weather and terrain owner requires a focused source-aware curation. |
| `murren-murren--murren-schilthorn-ski-area` (Mürren to Mürren-Schilthorn) | `ski_area_access` | `deferred` | `direct_access_relationship` |  | `scope-murren` | `docs/product-backlog.md#jungfrau-region-catalog-extension` | The access edge depends on the deferred Mürren destination, base, and ski area. |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:jungfrau-ski-region-pass` | `available_from_stay_destination_ids` | `null` | `["grindelwald", "wengen"]` | `verified_with_adjustment` | no |
| `lift_pass_product:jungfrau-ski-region-pass` | `default_for_stay_destination_ids` | `null` | `["grindelwald", "wengen"]` | `verified_with_adjustment` | no |
| `lift_pass_product:jungfrau-ski-region-pass` | `external_validity_summary` | `null` | `"The pass also covers the unmodeled Mürren-Schilthorn ski area; the published 2026/27 tariff requires a supplement for the Mürren-Schilthorn ascent."` | `verified_with_adjustment` | no |
| `lift_pass_product:jungfrau-ski-region-pass` | `lift_pass_product_id` | `null` | `"jungfrau-ski-region-pass"` | `verified_with_adjustment` | no |
| `lift_pass_product:jungfrau-ski-region-pass` | `name` | `null` | `"Jungfrau Ski Region ski pass"` | `verified_with_adjustment` | no |
| `lift_pass_product:jungfrau-ski-region-pass` | `pass_accessible_terrain` | `null` | `{"metric_scope": "pass_accessible", "piste_km_by_difficulty": null, "source_urls": ["https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf"], "total_lift_count": null, "total_piste_km": 211.0}` | `verified` | no |
| `lift_pass_product:jungfrau-ski-region-pass` | `prices` | `null` | `[{"amount": null, "amount_max": 83.0, "amount_min": 79.0, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "range", "season_label": "Winter 2026/27 regular-to-high-season tariff", "source_url": "https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf"}, {"amount": null, "amount_max": 244.0, "amount_min": 232.0, "audience": "adult", "currency": "CHF", "duration_days": 3, "price_kind": "range", "season_label": "Winter 2026/27 regular-to-high-season tariff", "source_url": "https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf"}, {"amount": null, "amount_max": 424.0, "amount_min": 404.0, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "range", "season_label": "Winter 2026/27 regular-to-high-season tariff", "source_url": "https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf"}]` | `verified` | no |
| `lift_pass_product:jungfrau-ski-region-pass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | no |
| `lift_pass_product:jungfrau-ski-region-pass` | `valid_ski_area_ids` | `null` | `["grindelwald-first-ski-area", "grindelwald-wengen-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:jungfrau-ski-region-pass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `lift_distance` | `null` | `"near"` | `estimated` | no |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `name` | `null` | `"Buri Sport Grindelwald"` | `verified` | no |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `price_max` | `null` | `50.0` | `estimated` | no |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `price_min` | `null` | `35.0` | `estimated` | no |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `price_range` | `null` | `"EUR 35-50"` | `estimated` | no |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `quality` | `null` | `"standard"` | `estimated` | no |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `rental_display_fact_id` | `null` | `"grindelwald-buri-sport-grindelwald"` | `verified` | no |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `stay_base_id` | `null` | `"grindelwald-grindelwald"` | `verified` | no |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `stay_destination_id` | `null` | `"grindelwald"` | `verified` | no |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `lift_distance` | `"medium"` | `null` | `estimated` | no |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `name` | `"Buri Sport Grindelwald"` | `null` | `estimated` | no |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `price_max` | `50.0` | `null` | `estimated` | no |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `price_min` | `35.0` | `null` | `estimated` | no |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `price_range` | `"EUR 35-50"` | `null` | `estimated` | no |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `quality` | `"standard"` | `null` | `estimated` | no |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `rental_display_fact_id` | `"grindelwald-wengen-buri-sport-grindelwald"` | `null` | `estimated` | no |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `stay_destination_id` | `"grindelwald-wengen"` | `null` | `estimated` | no |
| `ski_area:grindelwald-first-ski-area` | `base_elevation_m` | `null` | `1034` | `verified` | yes |
| `ski_area:grindelwald-first-ski-area` | `glacier_terrain.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:grindelwald-first-ski-area` | `latitude` | `null` | `46.6250229` | `verified_with_adjustment` | no |
| `ski_area:grindelwald-first-ski-area` | `longitude` | `null` | `8.0417827` | `verified_with_adjustment` | no |
| `ski_area:grindelwald-first-ski-area` | `marked_freeride_routes.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:grindelwald-first-ski-area` | `name` | `null` | `"Grindelwald-First"` | `verified` | no |
| `ski_area:grindelwald-first-ski-area` | `night_skiing.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:grindelwald-first-ski-area` | `official_trail_map.season_label` | `null` | `"2026/27"` | `verified` | no |
| `ski_area:grindelwald-first-ski-area` | `official_trail_map.url` | `null` | `"https://www.jungfrau.ch/maps/en/winter/grindelwald-first/"` | `verified` | no |
| `ski_area:grindelwald-first-ski-area` | `season_end_month` | `null` | `3` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-first-ski-area` | `season_start_month` | `null` | `12` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-first-ski-area` | `season_windows` | `null` | `[{"end_date": "2027-03-29", "season_label": "Winter 2026/27", "start_date": "2026-12-19", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-first-ski-area` | `ski_area_id` | `null` | `"grindelwald-first-ski-area"` | `verified` | no |
| `ski_area:grindelwald-first-ski-area` | `ski_day_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:grindelwald-first-ski-area` | `snow_park.availability` | `null` | `"available"` | `verified` | no |
| `ski_area:grindelwald-first-ski-area` | `snow_park.park_count` | `null` | `2` | `verified` | no |
| `ski_area:grindelwald-first-ski-area` | `snow_park.season_label` | `null` | `"2026/27"` | `verified` | no |
| `ski_area:grindelwald-first-ski-area` | `snowmaking.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:grindelwald-first-ski-area` | `snowmaking.coverage_basis` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:grindelwald-first-ski-area` | `summit_elevation_m` | `null` | `2168` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-first-ski-area` | `supported_skill_levels` | `null` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-first-ski-area` | `total_lift_count` | `null` | `5` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-first-ski-area` | `total_piste_km` | `null` | `56.0` | `verified` | yes |
| `ski_area:grindelwald-wengen-ski-area` | `name` | `"Grindelwald Wengen"` | `"Grindelwald-Wengen"` | `verified` | no |
| `ski_area:grindelwald-wengen-ski-area` | `official_trail_map.season_label` | `null` | `"2026/27"` | `verified` | no |
| `ski_area:grindelwald-wengen-ski-area` | `official_trail_map.url` | `null` | `"https://www.jungfrau.ch/maps/en/winter/grindelwald-wengen/"` | `verified` | no |
| `ski_area:grindelwald-wengen-ski-area` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-wengen-ski-area` | `season_windows` | `[]` | `[{"end_date": "2027-04-25", "season_label": "Winter 2026/27", "start_date": "2026-11-21", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-wengen-ski-area` | `ski_day_apres_profile.availability` | `"unknown"` | `"available"` | `verified_with_adjustment` | no |
| `ski_area:grindelwald-wengen-ski-area` | `ski_day_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `ski_area:grindelwald-wengen-ski-area` | `ski_day_apres_profile.season_label` | `null` | `"2025/26"` | `verified_with_adjustment` | no |
| `ski_area:grindelwald-wengen-ski-area` | `snowmaking.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:grindelwald-wengen-ski-area` | `snowmaking.season_label` | `null` | `"2016/17"` | `verified` | no |
| `ski_area:grindelwald-wengen-ski-area` | `summit_elevation_m` | `2500` | `2320` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-wengen-ski-area` | `supported_skill_levels` | `["intermediate", "advanced"]` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-wengen-ski-area` | `total_lift_count` | `null` | `21` | `verified_with_adjustment` | yes |
| `ski_area:grindelwald-wengen-ski-area` | `total_piste_km` | `null` | `103.0` | `verified` | yes |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `distance_m` | `null` | `394` | `verified_with_adjustment` | yes |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `duration_minutes` | `null` | `10` | `verified_with_adjustment` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `is_direct` | `null` | `true` | `verified` | yes |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `nearest_lift_name` | `null` | `"Grindelwald (Firstbahn)"` | `verified` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "272868374"}` | `verified_with_adjustment` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `ski_area_access_id` | `null` | `"grindelwald-grindelwald--grindelwald-first-ski-area"` | `verified` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `ski_area_id` | `null` | `"grindelwald-first-ski-area"` | `verified` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `source_urls` | `null` | `["https://www.jungfrau.ch/en-gb/grindelwaldfirst/", "https://www.openstreetmap.org/node/272868374"]` | `verified` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `stay_base_id` | `null` | `"grindelwald-grindelwald"` | `verified` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `access_mode` | `null` | `"ski_bus"` | `verified_with_adjustment` | yes |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `distance_m` | `null` | `1390` | `verified_with_adjustment` | yes |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `is_direct` | `null` | `false` | `verified` | yes |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `lift_distance` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `nearest_lift_name` | `null` | `"Grindelwald Terminal"` | `verified` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "299136559"}` | `verified_with_adjustment` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `ski_area_access_id` | `null` | `"grindelwald-grindelwald--grindelwald-wengen-ski-area"` | `verified` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `ski_area_id` | `null` | `"grindelwald-wengen-ski-area"` | `verified` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `source_urls` | `null` | `["https://grindelwald.swiss/en/service/guest-information.html", "https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php", "https://www.openstreetmap.org/node/299136559"]` | `verified` | no |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `stay_base_id` | `null` | `"grindelwald-grindelwald"` | `verified` | no |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `access_mode` | `"unknown"` | `null` | `estimated` | no |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `is_direct` | `false` | `null` | `estimated` | no |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `lift_distance` | `"medium"` | `null` | `estimated` | no |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `regional_data_ids` | `{}` | `null` | `estimated` | no |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `ski_area_access_id` | `"grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area"` | `null` | `estimated` | no |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `ski_area_id` | `"grindelwald-wengen-ski-area"` | `null` | `estimated` | no |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `source_urls` | `["https://www.bergfex.com/jungfrau-grindelwald-wengen/"]` | `null` | `estimated` | no |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `stay_base_id` | `"grindelwald-wengen-grindelwald"` | `null` | `estimated` | no |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `distance_m` | `null` | `92` | `verified_with_adjustment` | yes |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `is_direct` | `null` | `true` | `verified` | yes |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `nearest_lift_name` | `null` | `"Wengen-Männlichen cableway"` | `verified` | no |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "11078038620"}` | `verified_with_adjustment` | no |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `ski_area_access_id` | `null` | `"wengen-wengen--grindelwald-wengen-ski-area"` | `verified` | no |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `ski_area_id` | `null` | `"grindelwald-wengen-ski-area"` | `verified` | no |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `source_urls` | `null` | `["https://wengen.swiss/en/destination/about-wengen/skiing.html", "https://www.openstreetmap.org/node/11078038620"]` | `verified` | no |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `stay_base_id` | `null` | `"wengen-wengen"` | `verified` | no |
| `ski_region:grindelwald-wengen` | `name` | `"Grindelwald Wengen"` | `"Jungfrau Region"` | `verified_with_adjustment` | no |
| `ski_region:grindelwald-wengen` | `source_urls` | `[]` | `["https://www.jungfrau.ch/en-gb/jungfrau-ski-region/", "https://wengen.swiss/en/about-us/company.html"]` | `verified_with_adjustment` | no |
| `stay_base:grindelwald-grindelwald` | `base_character.development_style` | `null` | `"mixed"` | `verified_with_adjustment` | no |
| `stay_base:grindelwald-grindelwald` | `base_character.local_pace` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:grindelwald-grindelwald` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:grindelwald-grindelwald` | `elevation_m` | `null` | `1050` | `verified` | no |
| `stay_base:grindelwald-grindelwald` | `latitude` | `null` | `46.6242733` | `verified` | no |
| `stay_base:grindelwald-grindelwald` | `local_apres_profile.availability` | `null` | `"available"` | `verified_with_adjustment` | no |
| `stay_base:grindelwald-grindelwald` | `local_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:grindelwald-grindelwald` | `local_apres_profile.season_label` | `null` | `"2025/26"` | `verified_with_adjustment` | no |
| `stay_base:grindelwald-grindelwald` | `longitude` | `null` | `8.0367462` | `verified` | no |
| `stay_base:grindelwald-grindelwald` | `name` | `null` | `"Grindelwald"` | `verified` | no |
| `stay_base:grindelwald-grindelwald` | `price_max` | `null` | `255.0` | `estimated` | no |
| `stay_base:grindelwald-grindelwald` | `price_min` | `null` | `190.0` | `estimated` | no |
| `stay_base:grindelwald-grindelwald` | `price_range` | `null` | `"EUR 190-255"` | `estimated` | no |
| `stay_base:grindelwald-grindelwald` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:grindelwald-grindelwald` | `regional_data_ids` | `null` | `{"osm_relation_id": "1682457"}` | `verified` | no |
| `stay_base:grindelwald-grindelwald` | `stay_base_id` | `null` | `"grindelwald-grindelwald"` | `verified` | no |
| `stay_base:grindelwald-grindelwald` | `stay_destination_id` | `null` | `"grindelwald"` | `verified` | yes |
| `stay_base:grindelwald-wengen-grindelwald` | `base_character.development_style` | `"unknown"` | `null` | `estimated` | no |
| `stay_base:grindelwald-wengen-grindelwald` | `base_character.local_pace` | `"unknown"` | `null` | `estimated` | no |
| `stay_base:grindelwald-wengen-grindelwald` | `local_apres_profile.availability` | `"unknown"` | `null` | `estimated` | no |
| `stay_base:grindelwald-wengen-grindelwald` | `name` | `"Grindelwald"` | `null` | `estimated` | no |
| `stay_base:grindelwald-wengen-grindelwald` | `price_max` | `255.0` | `null` | `estimated` | no |
| `stay_base:grindelwald-wengen-grindelwald` | `price_min` | `190.0` | `null` | `estimated` | no |
| `stay_base:grindelwald-wengen-grindelwald` | `price_range` | `"EUR 190-255"` | `null` | `estimated` | no |
| `stay_base:grindelwald-wengen-grindelwald` | `quality` | `"standard"` | `null` | `estimated` | no |
| `stay_base:grindelwald-wengen-grindelwald` | `regional_data_ids` | `{}` | `null` | `estimated` | no |
| `stay_base:grindelwald-wengen-grindelwald` | `stay_base_id` | `"grindelwald-wengen-grindelwald"` | `null` | `estimated` | no |
| `stay_base:grindelwald-wengen-grindelwald` | `stay_destination_id` | `"grindelwald-wengen"` | `null` | `estimated` | no |
| `stay_base:wengen-wengen` | `base_character.development_style` | `null` | `"mixed"` | `verified_with_adjustment` | no |
| `stay_base:wengen-wengen` | `base_character.local_pace` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:wengen-wengen` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:wengen-wengen` | `elevation_m` | `null` | `1274` | `verified` | no |
| `stay_base:wengen-wengen` | `latitude` | `null` | `46.6054411` | `verified` | no |
| `stay_base:wengen-wengen` | `local_apres_profile.availability` | `null` | `"available"` | `verified_with_adjustment` | no |
| `stay_base:wengen-wengen` | `local_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:wengen-wengen` | `longitude` | `null` | `7.9217237` | `verified` | no |
| `stay_base:wengen-wengen` | `name` | `null` | `"Wengen"` | `verified` | no |
| `stay_base:wengen-wengen` | `price_max` | `null` | `320.0` | `estimated` | no |
| `stay_base:wengen-wengen` | `price_min` | `null` | `220.0` | `estimated` | no |
| `stay_base:wengen-wengen` | `price_range` | `null` | `"EUR 220-320"` | `estimated` | no |
| `stay_base:wengen-wengen` | `quality` | `null` | `"premium"` | `estimated` | no |
| `stay_base:wengen-wengen` | `regional_data_ids` | `null` | `{"osm_node_id": "240096898"}` | `verified` | no |
| `stay_base:wengen-wengen` | `stay_base_id` | `null` | `"wengen-wengen"` | `verified` | no |
| `stay_base:wengen-wengen` | `stay_destination_id` | `null` | `"wengen"` | `verified` | yes |
| `stay_destination:grindelwald` | `country` | `null` | `"Switzerland"` | `verified_with_adjustment` | no |
| `stay_destination:grindelwald` | `latitude` | `null` | `46.6242733` | `verified_with_adjustment` | no |
| `stay_destination:grindelwald` | `longitude` | `null` | `8.0367462` | `verified_with_adjustment` | no |
| `stay_destination:grindelwald` | `name` | `null` | `"Grindelwald"` | `verified_with_adjustment` | no |
| `stay_destination:grindelwald` | `price_level` | `null` | `"medium"` | `estimated` | no |
| `stay_destination:grindelwald` | `region` | `null` | `"Bernese Oberland"` | `verified_with_adjustment` | no |
| `stay_destination:grindelwald` | `regional_data_ids` | `null` | `{"osm_relation_id": "1682457"}` | `verified_with_adjustment` | no |
| `stay_destination:grindelwald` | `stay_destination_id` | `null` | `"grindelwald"` | `verified_with_adjustment` | no |
| `stay_destination:grindelwald` | `trip_market_region_id` | `null` | `"grindelwald-wengen"` | `verified_with_adjustment` | no |
| `stay_destination:grindelwald-wengen` | `country` | `"Switzerland"` | `null` | `estimated` | no |
| `stay_destination:grindelwald-wengen` | `latitude` | `46.6242` | `null` | `estimated` | no |
| `stay_destination:grindelwald-wengen` | `longitude` | `8.0414` | `null` | `estimated` | no |
| `stay_destination:grindelwald-wengen` | `name` | `"Grindelwald Wengen"` | `null` | `estimated` | no |
| `stay_destination:grindelwald-wengen` | `price_level` | `"medium"` | `null` | `estimated` | no |
| `stay_destination:grindelwald-wengen` | `region` | `"Bernese Oberland"` | `null` | `estimated` | no |
| `stay_destination:grindelwald-wengen` | `regional_data_ids` | `{}` | `null` | `estimated` | no |
| `stay_destination:grindelwald-wengen` | `stay_destination_id` | `"grindelwald-wengen"` | `null` | `estimated` | no |
| `stay_destination:grindelwald-wengen` | `trip_market_region_id` | `"grindelwald-wengen"` | `null` | `estimated` | no |
| `stay_destination:wengen` | `country` | `null` | `"Switzerland"` | `verified_with_adjustment` | no |
| `stay_destination:wengen` | `latitude` | `null` | `46.6054411` | `verified_with_adjustment` | no |
| `stay_destination:wengen` | `longitude` | `null` | `7.9217237` | `verified_with_adjustment` | no |
| `stay_destination:wengen` | `name` | `null` | `"Wengen"` | `verified_with_adjustment` | no |
| `stay_destination:wengen` | `price_level` | `null` | `"high"` | `estimated` | no |
| `stay_destination:wengen` | `region` | `null` | `"Bernese Oberland"` | `verified_with_adjustment` | no |
| `stay_destination:wengen` | `regional_data_ids` | `null` | `{"osm_node_id": "240096898"}` | `verified_with_adjustment` | no |
| `stay_destination:wengen` | `stay_destination_id` | `null` | `"wengen"` | `verified_with_adjustment` | no |
| `stay_destination:wengen` | `trip_market_region_id` | `null` | `"grindelwald-wengen"` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:jungfrau-ski-region-pass` | `display_name` | `null` | `"Jungfrau Ski Region ski pass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:jungfrau-ski-region-pass` | `field_source_refs` | `null` | `{"coverage": ["https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf", "https://www.jungfrau.ch/en-gb/jungfrau-ski-region/"], "identity_scope_availability": ["https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf", "https://www.jungfrau.ch/en-gb/jungfrau-ski-region/"], "pass_accessible_terrain": ["https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf"], "prices": ["https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:jungfrau-ski-region-pass` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified", "pass_accessible_terrain": "verified", "prices": "verified"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:jungfrau-ski-region-pass` | `notes` | `null` | `["The regional product is available from both modeled destinations and covers both modeled ski areas plus the unmodeled Mürren-Schilthorn area.", "The tariff's 211 km is retained as a pass-accessible aggregate and is not copied onto either modeled child ski area; the conflicting current transport-facility counts are omitted.", "The representative 1-, 3-, and 6-day adult ranges capture regular and high-season Winter 2026/27 tariffs.", "The external validity summary preserves the tariff note that the Mürren-Schilthorn ascent requires a supplement."]` | `estimated` | no |
| `trust_manifest:rental_display_facts:grindelwald-buri-sport-grindelwald` | `display_name` | `null` | `"Buri Sport Grindelwald"` | `estimated` | no |
| `trust_manifest:rental_display_facts:grindelwald-buri-sport-grindelwald` | `field_source_refs` | `null` | `{"identity_ownership": ["https://www.burisport.ch/en/ski-rental/"], "price_quality_access": []}` | `estimated` | no |
| `trust_manifest:rental_display_facts:grindelwald-buri-sport-grindelwald` | `field_statuses` | `null` | `{"identity_ownership": "verified", "price_quality_access": "estimated"}` | `estimated` | no |
| `trust_manifest:rental_display_facts:grindelwald-buri-sport-grindelwald` | `notes` | `null` | `["The official business site establishes Buri Sport as a Grindelwald ski and snowboard rental provider.", "The rental is reassigned from the removed combined destination to the Grindelwald destination and base.", "Price range, quality, and near-lift classification remain product-curated estimates."]` | `estimated` | no |
| `trust_manifest:rental_display_facts:grindelwald-wengen-buri-sport-grindelwald` | `display_name` | `"Buri Sport Grindelwald"` | `null` | `estimated` | no |
| `trust_manifest:rental_display_facts:grindelwald-wengen-buri-sport-grindelwald` | `field_source_refs` | `{"identity_ownership": [], "price_quality_access": []}` | `null` | `estimated` | no |
| `trust_manifest:rental_display_facts:grindelwald-wengen-buri-sport-grindelwald` | `field_statuses` | `{"identity_ownership": "estimated", "price_quality_access": "estimated"}` | `null` | `estimated` | no |
| `trust_manifest:rental_display_facts:grindelwald-wengen-buri-sport-grindelwald` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands."]` | `null` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `display_name` | `null` | `"Grindelwald -> Grindelwald-First"` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.jungfrau.ch/en-gb/grindelwaldfirst/", "https://www.openstreetmap.org/node/272868374"], "relationship": ["https://www.jungfrau.ch/en-gb/grindelwaldfirst/", "https://www.openstreetmap.org/node/272868374"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `notes` | `null` | `["The operator places the Firstbahn valley station in central Grindelwald about a ten-minute walk from the railway station.", "The 394 metre distance is a straight-line open-geodata measurement from the curated base coordinate to the Firstbahn station; the official source supplies the walking-duration context."]` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `display_name` | `null` | `"Grindelwald -> Grindelwald-Wengen"` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://grindelwald.swiss/en/service/guest-information.html", "https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php", "https://www.openstreetmap.org/node/299136559"], "relationship": ["https://grindelwald.swiss/en/service/guest-information.html", "https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php", "https://www.openstreetmap.org/node/299136559"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `notes` | `null` | `["Official guest information and the published winter line 121 establish ski-bus access from Grindelwald village to Grindelwald Terminal.", "The 1,390 metre distance is a straight-line open-geodata measurement from the curated base coordinate to the Terminal aerialway station."]` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `display_name` | `"Grindelwald -> Grindelwald Wengen"` | `null` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/jungfrau-grindelwald-wengen/"], "relationship": ["https://www.bergfex.com/jungfrau-grindelwald-wengen/"]}` | `null` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `null` | `estimated` | no |
| `trust_manifest:ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Provider-backed relationship remains estimated; no exact distance or duration is asserted."]` | `null` | `estimated` | no |
| `trust_manifest:ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `display_name` | `null` | `"Wengen -> Grindelwald-Wengen"` | `estimated` | no |
| `trust_manifest:ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://wengen.swiss/en/destination/about-wengen/skiing.html", "https://www.openstreetmap.org/node/11078038620"], "relationship": ["https://wengen.swiss/en/destination/about-wengen/skiing.html", "https://www.openstreetmap.org/node/11078038620"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `notes` | `null` | `["Official Wengen tourism identifies the Wengen-Männlichen cableway as a direct ten-minute entry to the Grindelwald-Wengen ski area and confirms village-return slopes.", "The 92 metre distance is a straight-line open-geodata measurement from the curated Wengen base coordinate to the cableway station."]` | `estimated` | no |
| `trust_manifest:ski_areas:grindelwald-first-ski-area` | `display_name` | `null` | `"Grindelwald-First"` | `estimated` | no |
| `trust_manifest:ski_areas:grindelwald-first-ski-area` | `field_source_refs` | `null` | `{"elevation_season": ["https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/"], "glacier_terrain": [], "identity_coordinates": ["https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/", "https://www.openstreetmap.org/node/272868374"], "marked_freeride_routes": [], "night_skiing": [], "official_documents": ["https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/", "https://www.jungfrau.ch/maps/en/winter/grindelwald-first/"], "ski_day_apres": [], "skill_fit": ["https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/"], "snow_park": ["https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/"], "snowmaking": [], "terrain_metrics": ["https://jungfrauregion.swiss/en/map/detail/grindelwald-first-b8e09f4c-b0e7-439b-a1fa-fb0285e72279.html", "https://jungfrauregion.swiss/en/map/detail/grindelwald-first-ski-area-817e68d6-3c8b-424f-a220-8f432b54c268.html"]}` | `estimated` | no |
| `trust_manifest:ski_areas:grindelwald-first-ski-area` | `field_statuses` | `null` | `{"elevation_season": "verified", "glacier_terrain": "needs_source", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "verified", "ski_day_apres": "needs_source", "skill_fit": "verified_with_adjustment", "snow_park": "verified", "snowmaking": "needs_source", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:grindelwald-first-ski-area` | `notes` | `null` | `["Official operator sources establish Grindelwald-First as a separate ski area with an independent operator, operating schedule, live status, and map.", "The weather request uses the Firstbahn valley station as its representative coordinate and the operator's 1,034-2,168 metre range for elevation bands.", "The dedicated current ski-area page publishes 56 km; a broader attraction page still says 58 km and five lifts, so Snowcast keeps the dedicated 56 km value and records the five-lift inventory with an adjustment note.", "The operator explicitly publishes two parks plus a halfpipe; the park_count records the two named park units and does not count the halfpipe as another park.", "No child-scoped source accepted in this curation establishes snowmaking coverage, glacier terrain, night skiing, marked freeride routes, or ski-day apres.", "grindelwald-first-ski-area is a new weather identity that requires owner-run history backfill and climatology after deployment."]` | `estimated` | no |
| `trust_manifest:ski_areas:grindelwald-wengen-ski-area` | `display_name` | `"Grindelwald Wengen"` | `"Grindelwald-Wengen"` | `estimated` | no |
| `trust_manifest:ski_areas:grindelwald-wengen-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-wengen/"], "glacier_terrain": [], "identity_coordinates": ["https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-wengen/"], "marked_freeride_routes": [], "night_skiing": [], "official_documents": ["https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-wengen/", "https://www.jungfrau.ch/maps/en/winter/grindelwald-wengen/"], "ski_day_apres": ["https://grindelwald.swiss/en/detail-events/apres-ski-820fef28-8137-4060-83c0-dfdd6973cc0b.html", "https://www.jungfrau.ch/en-gb/after-slopes-sounds/"], "skill_fit": ["https://wengen.swiss/en/destination/about-wengen/skiing.html", "https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-wengen/"], "snow_park": [], "snowmaking": ["https://www.jungfrau.ch/business-report-2016/en_2016_for-regional-value-creation_investments-winter-sports.html"], "terrain_metrics": ["https://jungfrauregion.swiss/en/destination/about-the-region/ski-areas.html", "https://jungfrauregion.swiss/en/map/detail/grindelwald-wengen-ski-area-0e76f9be-6f65-4a2f-8b6d-d6718fef6ab2.html"]}` | `estimated` | no |
| `trust_manifest:ski_areas:grindelwald-wengen-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "verified", "ski_day_apres": "verified_with_adjustment", "skill_fit": "verified_with_adjustment", "snow_park": "needs_source", "snowmaking": "verified", "terrain_metrics": "verified"}` | `estimated` | no |
| `trust_manifest:ski_areas:grindelwald-wengen-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Official sources establish Grindelwald-Wengen as the connected Kleine Scheidegg-Männlichen ski area serving both Grindelwald and Wengen.", "The 103 km and 21-lift values are child-scoped; the 211 km Jungfrau aggregate remains on the pass product.", "The retained latitude and longitude preserve the existing weather identity but lack an accepted source for the exact representative point, so identity_coordinates remains needs_source and the report marks both fields unresolved.", "The summit correction changes request elevation bands and requires an owner-run forced weather refetch and climatology rebuild after deployment.", "Snowmaking availability is source-backed, but no current child-scope percentage or denominator basis was found.", "Night tobogganing and the neighboring Grindelwald-First snowpark are not evidence for night skiing or a snowpark in this ski area."]` | `estimated` | no |
| `trust_manifest:ski_regions:grindelwald-wengen` | `display_name` | `"Grindelwald Wengen"` | `"Jungfrau Region"` | `estimated` | no |
| `trust_manifest:ski_regions:grindelwald-wengen` | `field_source_refs` | `{"identity": [], "membership_context": []}` | `{"identity": ["https://wengen.swiss/en/about-us/company.html", "https://www.jungfrau.ch/en-gb/jungfrau-ski-region/"], "membership_context": ["https://wengen.swiss/en/about-us/company.html", "https://www.jungfrau.ch/en-gb/jungfrau-ski-region/"]}` | `estimated` | no |
| `trust_manifest:ski_regions:grindelwald-wengen` | `field_statuses` | `{"identity": "needs_source", "membership_context": "estimated"}` | `{"identity": "verified", "membership_context": "verified"}` | `estimated` | no |
| `trust_manifest:ski_regions:grindelwald-wengen` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Trip-market membership is retained as reviewed migration context and remains estimated.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Official operator and tourism sources present Grindelwald, Wengen, and Mürren as distinct destinations within the broader Jungfrau trip market.", "The region groups trip-planning context and shared pass validity; it does not assert ski connectivity between Grindelwald-First and the other ski areas."]` | `estimated` | no |
| `trust_manifest:stay_bases:grindelwald-grindelwald` | `display_name` | `null` | `"Grindelwald"` | `estimated` | no |
| `trust_manifest:stay_bases:grindelwald-grindelwald` | `field_source_refs` | `null` | `{"base_character": ["https://grindelwald.swiss/en/destination/about-the-region/things-to-know-about-grindelwald/historical-background-stories.html", "https://www.jungfrau.ch/en-gb/grindelwald"], "base_type": ["https://www.jungfrau.ch/en-gb/grindelwald", "https://www.openstreetmap.org/relation/1682457"], "coordinates": ["https://www.openstreetmap.org/relation/1682457"], "elevation": ["https://www.gemeinde-grindelwald.ch/zahlen-fakten/"], "identity_ownership": ["https://www.jungfrau.ch/en-gb/grindelwald", "https://www.openstreetmap.org/relation/1682457"], "local_apres": ["https://grindelwald.swiss/en/detail-events/apres-ski-820fef28-8137-4060-83c0-dfdd6973cc0b.html", "https://www.jungfrau.ch/en-gb/after-slopes-sounds/"], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:grindelwald-grindelwald` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified", "coordinates": "verified", "elevation": "verified", "identity_ownership": "verified", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:grindelwald-grindelwald` | `notes` | `null` | `["Official and open-data sources establish Grindelwald as a village accommodation base at 1,050 metres.", "Mixed development normalizes the historic village and hotel growth together with substantial modern resort infrastructure; lively pace and apres normalize the official venue and recurring event inventory.", "Lodging price and quality remain product-curated estimates."]` | `estimated` | no |
| `trust_manifest:stay_bases:grindelwald-wengen-grindelwald` | `display_name` | `"Grindelwald"` | `null` | `estimated` | no |
| `trust_manifest:stay_bases:grindelwald-wengen-grindelwald` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `null` | `estimated` | no |
| `trust_manifest:stay_bases:grindelwald-wengen-grindelwald` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `null` | `estimated` | no |
| `trust_manifest:stay_bases:grindelwald-wengen-grindelwald` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `null` | `estimated` | no |
| `trust_manifest:stay_bases:wengen-wengen` | `display_name` | `null` | `"Wengen"` | `estimated` | no |
| `trust_manifest:stay_bases:wengen-wengen` | `field_source_refs` | `null` | `{"base_character": ["https://wengen.swiss/en/destination/about-wengen.html", "https://wengen.swiss/en/map/detail/hotel-bellevue-traditional-swiss-hideaway-e23f9742-7c22-49a7-9a8b-e8a97ff239f5.html"], "base_type": ["https://wengen.swiss/en/destination/about-wengen.html"], "coordinates": ["https://www.openstreetmap.org/node/240096898"], "elevation": ["https://wengen.swiss/en/destination/about-wengen.html"], "identity_ownership": ["https://wengen.swiss/en/destination/about-wengen.html", "https://www.openstreetmap.org/node/240096898"], "local_apres": ["https://wengen.swiss/en/map/detail/apres-ski-bar-hasenstall-89551e4f-668d-4c16-ab72-928b537258f0.html"], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:wengen-wengen` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified", "coordinates": "verified", "elevation": "verified", "identity_ownership": "verified", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:wengen-wengen` | `notes` | `null` | `["Official tourism establishes Wengen as a car-free village accommodation base at 1,274 metres with direct ski access.", "Mixed development normalizes the long-standing village identity and historic hotel fabric together with the accommodation scale of a major ski resort; lively pace and apres normalize official high-season and late-night venue evidence.", "Lodging price and quality remain product-curated estimates."]` | `estimated` | no |
| `trust_manifest:stay_destinations:grindelwald` | `display_name` | `null` | `"Grindelwald"` | `estimated` | no |
| `trust_manifest:stay_destinations:grindelwald` | `field_source_refs` | `null` | `{"coordinates": ["https://www.openstreetmap.org/relation/1682457"], "identity_location": ["https://www.jungfrau.ch/en-gb/grindelwald", "https://www.openstreetmap.org/relation/1682457"], "price_level": []}` | `estimated` | no |
| `trust_manifest:stay_destinations:grindelwald` | `field_statuses` | `null` | `{"coordinates": "verified", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:grindelwald` | `notes` | `null` | `["Grindelwald is modeled as its own accommodation destination inside the Jungfrau Region trip market.", "The medium price level remains a product-curated estimate pending a dedicated lodging sample."]` | `estimated` | no |
| `trust_manifest:stay_destinations:grindelwald-wengen` | `display_name` | `"Grindelwald Wengen"` | `null` | `estimated` | no |
| `trust_manifest:stay_destinations:grindelwald-wengen` | `field_source_refs` | `{"coordinates": [], "identity_location": [], "price_level": []}` | `null` | `estimated` | no |
| `trust_manifest:stay_destinations:grindelwald-wengen` | `field_statuses` | `{"coordinates": "needs_source", "identity_location": "needs_source", "price_level": "estimated"}` | `null` | `estimated` | no |
| `trust_manifest:stay_destinations:grindelwald-wengen` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `null` | `estimated` | no |
| `trust_manifest:stay_destinations:wengen` | `display_name` | `null` | `"Wengen"` | `estimated` | no |
| `trust_manifest:stay_destinations:wengen` | `field_source_refs` | `null` | `{"coordinates": ["https://www.openstreetmap.org/node/240096898"], "identity_location": ["https://wengen.swiss/en/destination/about-wengen.html", "https://www.openstreetmap.org/node/240096898"], "price_level": []}` | `estimated` | no |
| `trust_manifest:stay_destinations:wengen` | `field_statuses` | `null` | `{"coordinates": "verified", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:wengen` | `notes` | `null` | `["Official tourism treats car-free Wengen as a named village and accommodation market with its own access and lodging inventory.", "The high price level remains a product-curated estimate pending a dedicated lodging sample."]` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:jungfrau-ski-region-pass` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `name` | `changed` |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `pass_accessible_terrain` | `changed` |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `prices` | `changed` |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `validity_scope` | `changed` |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `lift_distance` | `changed` |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `name` | `changed` |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `price_max` | `changed` |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `price_min` | `changed` |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `price_range` | `changed` |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `quality` | `changed` |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `rental_display_fact_id` | `changed` |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `stay_base_id` | `changed` |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `stay_destination_id` | `changed` |  |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `lift_distance` | `changed` | The legacy field is removed with its owner. |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `name` | `changed` | The legacy field is removed with its owner. |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `price_max` | `changed` | The legacy field is removed with its owner. |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `price_min` | `changed` | The legacy field is removed with its owner. |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `price_range` | `changed` | The legacy field is removed with its owner. |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `quality` | `changed` | The legacy field is removed with its owner. |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `rental_display_fact_id` | `changed` | The legacy field is removed with its owner. |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `stay_base_id` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `rental_display_fact:grindelwald-wengen-buri-sport-grindelwald` | `stay_destination_id` | `changed` | The legacy field is removed with its owner. |
| `ski_area:grindelwald-first-ski-area` | `base_elevation_m` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `glacier_terrain.availability` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `latitude` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `longitude` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `marked_freeride_routes.availability` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `marked_freeride_routes.route_count` | `unresolved` | No accepted child-scope inventory establishes marked freeride routes. |
| `ski_area:grindelwald-first-ski-area` | `marked_freeride_routes.season_label` | `unresolved` | No accepted child-scope inventory establishes marked freeride routes. |
| `ski_area:grindelwald-first-ski-area` | `name` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `night_skiing.availability` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `night_skiing.season_label` | `unresolved` | No accepted source establishes recurring night skiing; night tobogganing is not treated as evidence. |
| `ski_area:grindelwald-first-ski-area` | `official_trail_map.season_label` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `official_trail_map.url` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | Reviewed official sources do not publish a clean child-scope kilometre split by difficulty. |
| `ski_area:grindelwald-first-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | Reviewed official sources do not publish a clean child-scope kilometre split by difficulty. |
| `ski_area:grindelwald-first-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | Reviewed official sources do not publish a clean child-scope kilometre split by difficulty. |
| `ski_area:grindelwald-first-ski-area` | `season_end_month` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `season_windows` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `ski_day_apres_profile.intensity` | `unresolved` | No accepted source establishes an area-scoped ski-day apres profile. |
| `ski_area:grindelwald-first-ski-area` | `ski_day_apres_profile.season_label` | `unresolved` | No accepted source establishes an area-scoped ski-day apres profile. |
| `ski_area:grindelwald-first-ski-area` | `snow_park.availability` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `snow_park.park_count` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `snow_park.season_label` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `snowmaking.availability` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `snowmaking.coverage_basis` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `snowmaking.coverage_pct` | `unresolved` | No accepted child-scope source establishes this exact snowmaking value or denominator. |
| `ski_area:grindelwald-first-ski-area` | `snowmaking.season_label` | `unresolved` | No accepted child-scope source establishes this exact snowmaking value or denominator. |
| `ski_area:grindelwald-first-ski-area` | `summit_elevation_m` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:grindelwald-first-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `base_elevation_m` | `reviewed-no-change` |  |
| `ski_area:grindelwald-wengen-ski-area` | `glacier_terrain.availability` | `unresolved` | No accepted child-scope source establishes maintained glacier ski terrain. |
| `ski_area:grindelwald-wengen-ski-area` | `latitude` | `unresolved` | The stable weather owner is retained, but no accepted source establishes the policy-correct representative point for this connected ski area. |
| `ski_area:grindelwald-wengen-ski-area` | `longitude` | `unresolved` | The stable weather owner is retained, but no accepted source establishes the policy-correct representative point for this connected ski area. |
| `ski_area:grindelwald-wengen-ski-area` | `marked_freeride_routes.availability` | `unresolved` | No accepted child-scope inventory establishes marked freeride routes. |
| `ski_area:grindelwald-wengen-ski-area` | `marked_freeride_routes.route_count` | `unresolved` | No accepted child-scope inventory establishes marked freeride routes. |
| `ski_area:grindelwald-wengen-ski-area` | `marked_freeride_routes.season_label` | `unresolved` | No accepted child-scope inventory establishes marked freeride routes. |
| `ski_area:grindelwald-wengen-ski-area` | `name` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `night_skiing.availability` | `unresolved` | No accepted source establishes recurring night skiing; night tobogganing is not treated as evidence. |
| `ski_area:grindelwald-wengen-ski-area` | `night_skiing.season_label` | `unresolved` | No accepted source establishes recurring night skiing; night tobogganing is not treated as evidence. |
| `ski_area:grindelwald-wengen-ski-area` | `official_trail_map.season_label` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `official_trail_map.url` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | Reviewed official sources do not publish a clean child-scope kilometre split by difficulty. |
| `ski_area:grindelwald-wengen-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | Reviewed official sources do not publish a clean child-scope kilometre split by difficulty. |
| `ski_area:grindelwald-wengen-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | Reviewed official sources do not publish a clean child-scope kilometre split by difficulty. |
| `ski_area:grindelwald-wengen-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:grindelwald-wengen-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `season_windows` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:grindelwald-wengen-ski-area` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `ski_day_apres_profile.intensity` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `ski_day_apres_profile.season_label` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `snow_park.availability` | `unresolved` | No accepted child-scope source establishes this snow-park value. |
| `ski_area:grindelwald-wengen-ski-area` | `snow_park.park_count` | `unresolved` | No accepted child-scope source establishes this snow-park value. |
| `ski_area:grindelwald-wengen-ski-area` | `snow_park.season_label` | `unresolved` | No accepted child-scope source establishes this snow-park value. |
| `ski_area:grindelwald-wengen-ski-area` | `snowmaking.availability` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `snowmaking.coverage_basis` | `unresolved` | No accepted child-scope source establishes this exact snowmaking value or denominator. |
| `ski_area:grindelwald-wengen-ski-area` | `snowmaking.coverage_pct` | `unresolved` | No accepted child-scope source establishes this exact snowmaking value or denominator. |
| `ski_area:grindelwald-wengen-ski-area` | `snowmaking.season_label` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `summit_elevation_m` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:grindelwald-wengen-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `duration_minutes` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `duration_minutes` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `access_mode` | `changed` | The legacy field is removed with its owner. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `distance_m` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `duration_minutes` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `is_direct` | `changed` | The legacy field is removed with its owner. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `lift_distance` | `changed` | The legacy field is removed with its owner. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `nearest_lift_name` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `regional_data_ids` | `changed` | The legacy field is removed with its owner. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `ski_area_access_id` | `changed` | The legacy field is removed with its owner. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `ski_area_id` | `changed` | The legacy field is removed with its owner. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `source_urls` | `changed` | The legacy field is removed with its owner. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `stay_base_id` | `changed` | The legacy field is removed with its owner. |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `duration_minutes` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `stay_base_id` | `changed` |  |
| `ski_region:grindelwald-wengen` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:grindelwald-wengen` | `name` | `changed` |  |
| `ski_region:grindelwald-wengen` | `parent_ski_region_id` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_region:grindelwald-wengen` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:grindelwald-wengen` | `source_urls` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `base_character.development_style` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `base_character.local_pace` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `base_type` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `elevation_m` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `latitude` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `local_apres_profile.intensity` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `local_apres_profile.season_label` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `longitude` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `name` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `price_max` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `price_min` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `price_range` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `quality` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `regional_data_ids` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `stay_base_id` | `changed` |  |
| `stay_base:grindelwald-grindelwald` | `stay_destination_id` | `changed` |  |
| `stay_base:grindelwald-wengen-grindelwald` | `base_character.development_style` | `changed` | The legacy field is removed with its owner. |
| `stay_base:grindelwald-wengen-grindelwald` | `base_character.local_pace` | `changed` | The legacy field is removed with its owner. |
| `stay_base:grindelwald-wengen-grindelwald` | `base_type` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `stay_base:grindelwald-wengen-grindelwald` | `elevation_m` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `stay_base:grindelwald-wengen-grindelwald` | `latitude` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `stay_base:grindelwald-wengen-grindelwald` | `local_apres_profile.availability` | `changed` | The legacy field is removed with its owner. |
| `stay_base:grindelwald-wengen-grindelwald` | `local_apres_profile.intensity` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `stay_base:grindelwald-wengen-grindelwald` | `local_apres_profile.season_label` | `unresolved` | The official Wengen venue evidence is current but does not publish an unambiguous season label. |
| `stay_base:grindelwald-wengen-grindelwald` | `longitude` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `stay_base:grindelwald-wengen-grindelwald` | `name` | `changed` | The legacy field is removed with its owner. |
| `stay_base:grindelwald-wengen-grindelwald` | `price_max` | `changed` | The legacy field is removed with its owner. |
| `stay_base:grindelwald-wengen-grindelwald` | `price_min` | `changed` | The legacy field is removed with its owner. |
| `stay_base:grindelwald-wengen-grindelwald` | `price_range` | `changed` | The legacy field is removed with its owner. |
| `stay_base:grindelwald-wengen-grindelwald` | `quality` | `changed` | The legacy field is removed with its owner. |
| `stay_base:grindelwald-wengen-grindelwald` | `regional_data_ids` | `changed` | The legacy field is removed with its owner. |
| `stay_base:grindelwald-wengen-grindelwald` | `stay_base_id` | `changed` | The legacy field is removed with its owner. |
| `stay_base:grindelwald-wengen-grindelwald` | `stay_destination_id` | `changed` | The legacy field is removed with its owner. |
| `stay_base:wengen-wengen` | `base_character.development_style` | `changed` |  |
| `stay_base:wengen-wengen` | `base_character.local_pace` | `changed` |  |
| `stay_base:wengen-wengen` | `base_type` | `changed` |  |
| `stay_base:wengen-wengen` | `elevation_m` | `changed` |  |
| `stay_base:wengen-wengen` | `latitude` | `changed` |  |
| `stay_base:wengen-wengen` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:wengen-wengen` | `local_apres_profile.intensity` | `changed` |  |
| `stay_base:wengen-wengen` | `local_apres_profile.season_label` | `unresolved` | The official Wengen venue evidence is current but does not publish an unambiguous season label. |
| `stay_base:wengen-wengen` | `longitude` | `changed` |  |
| `stay_base:wengen-wengen` | `name` | `changed` |  |
| `stay_base:wengen-wengen` | `price_max` | `changed` |  |
| `stay_base:wengen-wengen` | `price_min` | `changed` |  |
| `stay_base:wengen-wengen` | `price_range` | `changed` |  |
| `stay_base:wengen-wengen` | `quality` | `changed` |  |
| `stay_base:wengen-wengen` | `regional_data_ids` | `changed` |  |
| `stay_base:wengen-wengen` | `stay_base_id` | `changed` |  |
| `stay_base:wengen-wengen` | `stay_destination_id` | `changed` |  |
| `stay_destination:grindelwald` | `country` | `changed` |  |
| `stay_destination:grindelwald` | `latitude` | `changed` |  |
| `stay_destination:grindelwald` | `longitude` | `changed` |  |
| `stay_destination:grindelwald` | `name` | `changed` |  |
| `stay_destination:grindelwald` | `price_level` | `changed` |  |
| `stay_destination:grindelwald` | `region` | `changed` |  |
| `stay_destination:grindelwald` | `regional_data_ids` | `changed` |  |
| `stay_destination:grindelwald` | `stay_destination_id` | `changed` |  |
| `stay_destination:grindelwald` | `trip_market_region_id` | `changed` |  |
| `stay_destination:grindelwald-wengen` | `country` | `changed` | The legacy field is removed with its owner. |
| `stay_destination:grindelwald-wengen` | `latitude` | `changed` | The legacy field is removed with its owner. |
| `stay_destination:grindelwald-wengen` | `longitude` | `changed` | The legacy field is removed with its owner. |
| `stay_destination:grindelwald-wengen` | `name` | `changed` | The legacy field is removed with its owner. |
| `stay_destination:grindelwald-wengen` | `price_level` | `changed` | The legacy field is removed with its owner. |
| `stay_destination:grindelwald-wengen` | `region` | `changed` | The legacy field is removed with its owner. |
| `stay_destination:grindelwald-wengen` | `regional_data_ids` | `changed` | The legacy field is removed with its owner. |
| `stay_destination:grindelwald-wengen` | `stay_destination_id` | `changed` | The legacy field is removed with its owner. |
| `stay_destination:grindelwald-wengen` | `trip_market_region_id` | `changed` | The legacy field is removed with its owner. |
| `stay_destination:wengen` | `country` | `changed` |  |
| `stay_destination:wengen` | `latitude` | `changed` |  |
| `stay_destination:wengen` | `longitude` | `changed` |  |
| `stay_destination:wengen` | `name` | `changed` |  |
| `stay_destination:wengen` | `price_level` | `changed` |  |
| `stay_destination:wengen` | `region` | `changed` |  |
| `stay_destination:wengen` | `regional_data_ids` | `changed` |  |
| `stay_destination:wengen` | `stay_destination_id` | `changed` |  |
| `stay_destination:wengen` | `trip_market_region_id` | `changed` |  |
| `trust_manifest:lift_pass_products:jungfrau-ski-region-pass` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:jungfrau-ski-region-pass` | `field_source_refs` | `changed` |  |
| `trust_manifest:lift_pass_products:jungfrau-ski-region-pass` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:jungfrau-ski-region-pass` | `notes` | `changed` |  |
| `trust_manifest:rental_display_facts:grindelwald-buri-sport-grindelwald` | `display_name` | `changed` |  |
| `trust_manifest:rental_display_facts:grindelwald-buri-sport-grindelwald` | `field_source_refs` | `changed` |  |
| `trust_manifest:rental_display_facts:grindelwald-buri-sport-grindelwald` | `field_statuses` | `changed` |  |
| `trust_manifest:rental_display_facts:grindelwald-buri-sport-grindelwald` | `notes` | `changed` |  |
| `trust_manifest:rental_display_facts:grindelwald-wengen-buri-sport-grindelwald` | `display_name` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:rental_display_facts:grindelwald-wengen-buri-sport-grindelwald` | `field_source_refs` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:rental_display_facts:grindelwald-wengen-buri-sport-grindelwald` | `field_statuses` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:rental_display_facts:grindelwald-wengen-buri-sport-grindelwald` | `notes` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `display_name` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `field_source_refs` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `field_statuses` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `notes` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:grindelwald-first-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:grindelwald-first-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:grindelwald-first-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:grindelwald-first-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:grindelwald-wengen-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:grindelwald-wengen-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:grindelwald-wengen-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:grindelwald-wengen-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_regions:grindelwald-wengen` | `display_name` | `changed` |  |
| `trust_manifest:ski_regions:grindelwald-wengen` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_regions:grindelwald-wengen` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_regions:grindelwald-wengen` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:grindelwald-grindelwald` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:grindelwald-grindelwald` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:grindelwald-grindelwald` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:grindelwald-grindelwald` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:grindelwald-wengen-grindelwald` | `display_name` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:stay_bases:grindelwald-wengen-grindelwald` | `field_source_refs` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:stay_bases:grindelwald-wengen-grindelwald` | `field_statuses` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:stay_bases:grindelwald-wengen-grindelwald` | `notes` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:stay_bases:wengen-wengen` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:wengen-wengen` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:wengen-wengen` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:wengen-wengen` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:grindelwald` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:grindelwald` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:grindelwald` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:grindelwald` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:grindelwald-wengen` | `display_name` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:stay_destinations:grindelwald-wengen` | `field_source_refs` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:stay_destinations:grindelwald-wengen` | `field_statuses` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:stay_destinations:grindelwald-wengen` | `notes` | `changed` | The legacy field is removed with its owner. |
| `trust_manifest:stay_destinations:wengen` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:wengen` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:wengen` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:wengen` | `notes` | `changed` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:jungfrau-ski-region-pass` | `available_from_stay_destination_ids` | [Official Jungfrau Ski Region Winter 2026/27 tariff](https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf) | `["grindelwald", "wengen"]` | The cited source supports the reviewed lift_pass_product value for available_from_stay_destination_ids. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `lift_pass_product:jungfrau-ski-region-pass` | `default_for_stay_destination_ids` | [Official Jungfrau Ski Region Winter 2026/27 tariff](https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf) | `["grindelwald", "wengen"]` | The cited source supports the reviewed lift_pass_product value for default_for_stay_destination_ids. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `lift_pass_product:jungfrau-ski-region-pass` | `external_validity_summary` | [Official Jungfrau Ski Region Winter 2026/27 tariff](https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf) | `"The pass also covers the unmodeled Mürren-Schilthorn ski area; the published 2026/27 tariff requires a supplement for the Mürren-Schilthorn ascent."` | The cited source supports the reviewed lift_pass_product value for external_validity_summary. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `lift_pass_product:jungfrau-ski-region-pass` | `lift_pass_product_id` | [Official Jungfrau Ski Region Winter 2026/27 tariff](https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf) | `"jungfrau-ski-region-pass"` | The cited source supports the reviewed lift_pass_product value for lift_pass_product_id. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `lift_pass_product:jungfrau-ski-region-pass` | `name` | [Official Jungfrau Ski Region Winter 2026/27 tariff](https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf) | `"Jungfrau Ski Region ski pass"` | The cited source supports the reviewed lift_pass_product value for name. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `lift_pass_product:jungfrau-ski-region-pass` | `pass_accessible_terrain` | [Official Jungfrau Ski Region Winter 2026/27 tariff](https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf) | `{"metric_scope": "pass_accessible", "piste_km_by_difficulty": null, "source_urls": ["https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf"], "total_lift_count": null, "total_piste_km": 211.0}` | The cited source supports the reviewed lift_pass_product value for pass_accessible_terrain. |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `prices` | [Official Jungfrau Ski Region Winter 2026/27 tariff](https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf) | `[{"amount": null, "amount_max": 83.0, "amount_min": 79.0, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "range", "season_label": "Winter 2026/27 regular-to-high-season tariff", "source_url": "https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf"}, {"amount": null, "amount_max": 244.0, "amount_min": 232.0, "audience": "adult", "currency": "CHF", "duration_days": 3, "price_kind": "range", "season_label": "Winter 2026/27 regular-to-high-season tariff", "source_url": "https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf"}, {"amount": null, "amount_max": 424.0, "amount_min": 404.0, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "range", "season_label": "Winter 2026/27 regular-to-high-season tariff", "source_url": "https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf"}]` | The cited source supports the reviewed lift_pass_product value for prices. |  |
| `lift_pass_product:jungfrau-ski-region-pass` | `terrain_domain_ids` | [Official Jungfrau Ski Region Winter 2026/27 tariff](https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf) | `[]` | The cited source supports the reviewed lift_pass_product value for terrain_domain_ids. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `lift_pass_product:jungfrau-ski-region-pass` | `valid_ski_area_ids` | [Official Jungfrau Ski Region Winter 2026/27 tariff](https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf) | `["grindelwald-first-ski-area", "grindelwald-wengen-ski-area"]` | The cited source supports the reviewed lift_pass_product value for valid_ski_area_ids. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `lift_pass_product:jungfrau-ski-region-pass` | `validity_scope` | [Official Jungfrau Ski Region Winter 2026/27 tariff](https://cdn.jungfrau.ch/Prospekte_und_Broschueren/Preisliste-Jungfrau-Ski-Region.pdf) | `"regional_network"` | The cited source supports the reviewed lift_pass_product value for validity_scope. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `name` | [Official Buri Sport rental page](https://www.burisport.ch/en/ski-rental/) | `"Buri Sport Grindelwald"` | The cited source supports the reviewed rental_display_fact value for name. |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `rental_display_fact_id` | [Official Buri Sport rental page](https://www.burisport.ch/en/ski-rental/) | `"grindelwald-buri-sport-grindelwald"` | The cited source supports the reviewed rental_display_fact value for rental_display_fact_id. |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `stay_base_id` | [Official Buri Sport rental page](https://www.burisport.ch/en/ski-rental/) | `"grindelwald-grindelwald"` | The cited source supports the reviewed rental_display_fact value for stay_base_id. |  |
| `rental_display_fact:grindelwald-buri-sport-grindelwald` | `stay_destination_id` | [Official Buri Sport rental page](https://www.burisport.ch/en/ski-rental/) | `"grindelwald"` | The cited source supports the reviewed rental_display_fact value for stay_destination_id. |  |
| `ski_area:grindelwald-first-ski-area` | `base_elevation_m` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `1034` | The cited source supports the reviewed ski_area value for base_elevation_m. |  |
| `ski_area:grindelwald-first-ski-area` | `latitude` | [OpenStreetMap Firstbahn valley station](https://www.openstreetmap.org/node/272868374) | `46.6250229` | The cited source supports the reviewed ski_area value for latitude. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-first-ski-area` | `longitude` | [OpenStreetMap Firstbahn valley station](https://www.openstreetmap.org/node/272868374) | `8.0417827` | The cited source supports the reviewed ski_area value for longitude. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-first-ski-area` | `name` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `"Grindelwald-First"` | The cited source supports the reviewed ski_area value for name. |  |
| `ski_area:grindelwald-first-ski-area` | `official_trail_map.season_label` | [Official Grindelwald-First winter map](https://www.jungfrau.ch/maps/en/winter/grindelwald-first/) | `"2026/27"` | The cited source supports the reviewed ski_area value for official_trail_map.season_label. |  |
| `ski_area:grindelwald-first-ski-area` | `official_trail_map.url` | [Official Grindelwald-First winter map](https://www.jungfrau.ch/maps/en/winter/grindelwald-first/) | `"https://www.jungfrau.ch/maps/en/winter/grindelwald-first/"` | The cited source supports the reviewed ski_area value for official_trail_map.url. |  |
| `ski_area:grindelwald-first-ski-area` | `season_end_month` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `3` | The cited source supports the reviewed ski_area value for season_end_month. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-first-ski-area` | `season_start_month` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `12` | The cited source supports the reviewed ski_area value for season_start_month. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-first-ski-area` | `season_windows` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `[{"end_date": "2027-03-29", "season_label": "Winter 2026/27", "start_date": "2026-12-19", "status": "planned"}]` | The cited source supports the reviewed ski_area value for season_windows. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-first-ski-area` | `ski_area_id` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `"grindelwald-first-ski-area"` | The cited source supports the reviewed ski_area value for ski_area_id. |  |
| `ski_area:grindelwald-first-ski-area` | `snow_park.availability` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `"available"` | The cited source supports the reviewed ski_area value for snow_park.availability. |  |
| `ski_area:grindelwald-first-ski-area` | `snow_park.park_count` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `2` | The cited source supports the reviewed ski_area value for snow_park.park_count. |  |
| `ski_area:grindelwald-first-ski-area` | `snow_park.season_label` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `"2026/27"` | The cited source supports the reviewed ski_area value for snow_park.season_label. |  |
| `ski_area:grindelwald-first-ski-area` | `summit_elevation_m` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `2168` | The cited source supports the reviewed ski_area value for summit_elevation_m. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-first-ski-area` | `supported_skill_levels` | [Official Grindelwald-First ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-first-ski-area/) | `["beginner", "intermediate", "advanced"]` | The cited source supports the reviewed ski_area value for supported_skill_levels. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-first-ski-area` | `total_lift_count` | [Official Grindelwald-First mountain page](https://jungfrauregion.swiss/en/map/detail/grindelwald-first-b8e09f4c-b0e7-439b-a1fa-fb0285e72279.html) | `5` | The cited source supports the reviewed ski_area value for total_lift_count. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-first-ski-area` | `total_piste_km` | [Official Grindelwald-First ski-area page](https://jungfrauregion.swiss/en/map/detail/grindelwald-first-ski-area-817e68d6-3c8b-424f-a220-8f432b54c268.html) | `56.0` | The cited source supports the reviewed ski_area value for total_piste_km. |  |
| `ski_area:grindelwald-wengen-ski-area` | `name` | [Official Grindelwald-Wengen ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-wengen/) | `"Grindelwald-Wengen"` | The cited source supports the reviewed ski_area value for name. |  |
| `ski_area:grindelwald-wengen-ski-area` | `official_trail_map.season_label` | [Official Grindelwald-Wengen winter map](https://www.jungfrau.ch/maps/en/winter/grindelwald-wengen/) | `"2026/27"` | The cited source supports the reviewed ski_area value for official_trail_map.season_label. |  |
| `ski_area:grindelwald-wengen-ski-area` | `official_trail_map.url` | [Official Grindelwald-Wengen winter map](https://www.jungfrau.ch/maps/en/winter/grindelwald-wengen/) | `"https://www.jungfrau.ch/maps/en/winter/grindelwald-wengen/"` | The cited source supports the reviewed ski_area value for official_trail_map.url. |  |
| `ski_area:grindelwald-wengen-ski-area` | `season_start_month` | [Official Grindelwald-Wengen ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-wengen/) | `11` | The cited source supports the reviewed ski_area value for season_start_month. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-wengen-ski-area` | `season_windows` | [Official Grindelwald-Wengen ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-wengen/) | `[{"end_date": "2027-04-25", "season_label": "Winter 2026/27", "start_date": "2026-11-21", "status": "planned"}]` | The cited source supports the reviewed ski_area value for season_windows. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-wengen-ski-area` | `ski_day_apres_profile.availability` | [Official Jungfrau after-slopes events](https://www.jungfrau.ch/en-gb/after-slopes-sounds/) | `"available"` | The cited source supports the reviewed ski_area value for ski_day_apres_profile.availability. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-wengen-ski-area` | `ski_day_apres_profile.intensity` | [Official Jungfrau after-slopes events](https://www.jungfrau.ch/en-gb/after-slopes-sounds/) | `"lively"` | The cited source supports the reviewed ski_area value for ski_day_apres_profile.intensity. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-wengen-ski-area` | `ski_day_apres_profile.season_label` | [Official Jungfrau after-slopes events](https://www.jungfrau.ch/en-gb/after-slopes-sounds/) | `"2025/26"` | The cited source supports the reviewed ski_area value for ski_day_apres_profile.season_label. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-wengen-ski-area` | `snowmaking.availability` | [Official Jungfrau Railways winter-sports investment report](https://www.jungfrau.ch/business-report-2016/en_2016_for-regional-value-creation_investments-winter-sports.html) | `"available"` | The cited source supports the reviewed ski_area value for snowmaking.availability. |  |
| `ski_area:grindelwald-wengen-ski-area` | `snowmaking.season_label` | [Official Jungfrau Railways winter-sports investment report](https://www.jungfrau.ch/business-report-2016/en_2016_for-regional-value-creation_investments-winter-sports.html) | `"2016/17"` | The cited source supports the reviewed ski_area value for snowmaking.season_label. |  |
| `ski_area:grindelwald-wengen-ski-area` | `summit_elevation_m` | [Official Grindelwald-Wengen ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-wengen/) | `2320` | The cited source supports the reviewed ski_area value for summit_elevation_m. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-wengen-ski-area` | `supported_skill_levels` | [Official Wengen skiing page](https://wengen.swiss/en/destination/about-wengen/skiing.html) | `["beginner", "intermediate", "advanced"]` | The cited source supports the reviewed ski_area value for supported_skill_levels. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-wengen-ski-area` | `total_lift_count` | [Official Jungfrau Region ski-area overview](https://jungfrauregion.swiss/en/destination/about-the-region/ski-areas.html) | `21` | The cited source supports the reviewed ski_area value for total_lift_count. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area:grindelwald-wengen-ski-area` | `total_piste_km` | [Official Jungfrau Region ski-area overview](https://jungfrauregion.swiss/en/destination/about-the-region/ski-areas.html) | `103.0` | The cited source supports the reviewed ski_area value for total_piste_km. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `access_mode` | [Official Firstbahn arrival and OSM station geometry](https://www.jungfrau.ch/en-gb/grindelwaldfirst/) | `"walk"` | The cited source supports the reviewed ski_area_access value for access_mode. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `distance_m` | [Official Firstbahn arrival and OSM station geometry](https://www.openstreetmap.org/node/272868374) | `394` | The cited source supports the reviewed ski_area_access value for distance_m. | Rounded Haversine distance from the curated base and cited OSM lift station; this is not a routed walking distance. |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `duration_minutes` | [Official Firstbahn arrival and OSM station geometry](https://www.jungfrau.ch/en-gb/grindelwaldfirst/) | `10` | The cited source supports the reviewed ski_area_access value for duration_minutes. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `is_direct` | [Official Firstbahn arrival and OSM station geometry](https://www.jungfrau.ch/en-gb/grindelwaldfirst/) | `true` | The cited source supports the reviewed ski_area_access value for is_direct. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `lift_distance` | [Official Firstbahn arrival and OSM station geometry](https://www.openstreetmap.org/node/272868374) | `"near"` | The cited source supports the reviewed ski_area_access value for lift_distance. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `nearest_lift_name` | [Official Firstbahn arrival and OSM station geometry](https://www.jungfrau.ch/en-gb/grindelwaldfirst/) | `"Grindelwald (Firstbahn)"` | The cited source supports the reviewed ski_area_access value for nearest_lift_name. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `regional_data_ids` | [Official Firstbahn arrival and OSM station geometry](https://www.openstreetmap.org/node/272868374) | `{"nearest_lift_osm_node_id": "272868374"}` | The cited source supports the reviewed ski_area_access value for regional_data_ids. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `ski_area_access_id` | [Official Firstbahn arrival and OSM station geometry](https://www.jungfrau.ch/en-gb/grindelwaldfirst/) | `"grindelwald-grindelwald--grindelwald-first-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_access_id. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `ski_area_id` | [Official Firstbahn arrival and OSM station geometry](https://www.jungfrau.ch/en-gb/grindelwaldfirst/) | `"grindelwald-first-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_id. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `source_urls` | [Official Firstbahn arrival and OSM station geometry](https://www.jungfrau.ch/en-gb/grindelwaldfirst/) | `["https://www.jungfrau.ch/en-gb/grindelwaldfirst/", "https://www.openstreetmap.org/node/272868374"]` | The cited source supports the reviewed ski_area_access value for source_urls. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-first-ski-area` | `stay_base_id` | [Official Firstbahn arrival and OSM station geometry](https://www.jungfrau.ch/en-gb/grindelwaldfirst/) | `"grindelwald-grindelwald"` | The cited source supports the reviewed ski_area_access value for stay_base_id. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `access_mode` | [Official winter ski-bus line and OSM Terminal geometry](https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php) | `"ski_bus"` | The cited source supports the reviewed ski_area_access value for access_mode. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `distance_m` | [Official winter ski-bus line and OSM Terminal geometry](https://www.openstreetmap.org/node/299136559) | `1390` | The cited source supports the reviewed ski_area_access value for distance_m. | Rounded Haversine distance from the curated base and cited OSM lift station; this is not a routed walking distance. |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `is_direct` | [Official winter ski-bus line and OSM Terminal geometry](https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php) | `false` | The cited source supports the reviewed ski_area_access value for is_direct. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `lift_distance` | [Official winter ski-bus line and OSM Terminal geometry](https://www.openstreetmap.org/node/299136559) | `"medium"` | The cited source supports the reviewed ski_area_access value for lift_distance. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `nearest_lift_name` | [Official winter ski-bus line and OSM Terminal geometry](https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php) | `"Grindelwald Terminal"` | The cited source supports the reviewed ski_area_access value for nearest_lift_name. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `regional_data_ids` | [Official winter ski-bus line and OSM Terminal geometry](https://www.openstreetmap.org/node/299136559) | `{"nearest_lift_osm_node_id": "299136559"}` | The cited source supports the reviewed ski_area_access value for regional_data_ids. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `ski_area_access_id` | [Official winter ski-bus line and OSM Terminal geometry](https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php) | `"grindelwald-grindelwald--grindelwald-wengen-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_access_id. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `ski_area_id` | [Official winter ski-bus line and OSM Terminal geometry](https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php) | `"grindelwald-wengen-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_id. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `source_urls` | [Official winter ski-bus line and OSM Terminal geometry](https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php) | `["https://grindelwald.swiss/en/service/guest-information.html", "https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php", "https://www.openstreetmap.org/node/299136559"]` | The cited source supports the reviewed ski_area_access value for source_urls. |  |
| `ski_area_access:grindelwald-grindelwald--grindelwald-wengen-ski-area` | `stay_base_id` | [Official winter ski-bus line and OSM Terminal geometry](https://www.grindelwaldbus.ch/grindelwaldbus-en/timetables/timetablewinter/local-lines/line-121.php) | `"grindelwald-grindelwald"` | The cited source supports the reviewed ski_area_access value for stay_base_id. |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `access_mode` | [Official Wengen lift access and OSM cableway geometry](https://wengen.swiss/en/destination/about-wengen/skiing.html) | `"walk"` | The cited source supports the reviewed ski_area_access value for access_mode. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `distance_m` | [Official Wengen lift access and OSM cableway geometry](https://www.openstreetmap.org/node/11078038620) | `92` | The cited source supports the reviewed ski_area_access value for distance_m. | Rounded Haversine distance from the curated base and cited OSM lift station; this is not a routed walking distance. |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `is_direct` | [Official Wengen lift access and OSM cableway geometry](https://wengen.swiss/en/destination/about-wengen/skiing.html) | `true` | The cited source supports the reviewed ski_area_access value for is_direct. |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `lift_distance` | [Official Wengen lift access and OSM cableway geometry](https://www.openstreetmap.org/node/11078038620) | `"near"` | The cited source supports the reviewed ski_area_access value for lift_distance. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `nearest_lift_name` | [Official Wengen lift access and OSM cableway geometry](https://wengen.swiss/en/destination/about-wengen/skiing.html) | `"Wengen-Männlichen cableway"` | The cited source supports the reviewed ski_area_access value for nearest_lift_name. |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `regional_data_ids` | [Official Wengen lift access and OSM cableway geometry](https://www.openstreetmap.org/node/11078038620) | `{"nearest_lift_osm_node_id": "11078038620"}` | The cited source supports the reviewed ski_area_access value for regional_data_ids. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `ski_area_access_id` | [Official Wengen lift access and OSM cableway geometry](https://wengen.swiss/en/destination/about-wengen/skiing.html) | `"wengen-wengen--grindelwald-wengen-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_access_id. |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `ski_area_id` | [Official Wengen lift access and OSM cableway geometry](https://wengen.swiss/en/destination/about-wengen/skiing.html) | `"grindelwald-wengen-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_id. |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `source_urls` | [Official Wengen lift access and OSM cableway geometry](https://wengen.swiss/en/destination/about-wengen/skiing.html) | `["https://wengen.swiss/en/destination/about-wengen/skiing.html", "https://www.openstreetmap.org/node/11078038620"]` | The cited source supports the reviewed ski_area_access value for source_urls. |  |
| `ski_area_access:wengen-wengen--grindelwald-wengen-ski-area` | `stay_base_id` | [Official Wengen lift access and OSM cableway geometry](https://wengen.swiss/en/destination/about-wengen/skiing.html) | `"wengen-wengen"` | The cited source supports the reviewed ski_area_access value for stay_base_id. |  |
| `ski_region:grindelwald-wengen` | `name` | [Official Jungfrau Ski Region overview](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/) | `"Jungfrau Region"` | The cited source supports the reviewed ski_region value for name. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `ski_region:grindelwald-wengen` | `source_urls` | [Official Jungfrau Ski Region overview](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/) | `["https://www.jungfrau.ch/en-gb/jungfrau-ski-region/", "https://wengen.swiss/en/about-us/company.html"]` | The cited source supports the reviewed ski_region value for source_urls. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_base:grindelwald-grindelwald` | `base_character.development_style` | [Official Grindelwald history](https://grindelwald.swiss/en/destination/about-the-region/things-to-know-about-grindelwald/historical-background-stories.html) | `"mixed"` | The cited source supports the reviewed stay_base value for base_character.development_style. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_base:grindelwald-grindelwald` | `base_character.local_pace` | [Official Grindelwald history](https://grindelwald.swiss/en/destination/about-the-region/things-to-know-about-grindelwald/historical-background-stories.html) | `"lively"` | The cited source supports the reviewed stay_base value for base_character.local_pace. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_base:grindelwald-grindelwald` | `base_type` | [Official Grindelwald destination page](https://www.jungfrau.ch/en-gb/grindelwald) | `"village"` | The cited source supports the reviewed stay_base value for base_type. |  |
| `stay_base:grindelwald-grindelwald` | `elevation_m` | [Official Grindelwald municipal facts](https://www.gemeinde-grindelwald.ch/zahlen-fakten/) | `1050` | The cited source supports the reviewed stay_base value for elevation_m. |  |
| `stay_base:grindelwald-grindelwald` | `latitude` | [OpenStreetMap Grindelwald relation](https://www.openstreetmap.org/relation/1682457) | `46.6242733` | The cited source supports the reviewed stay_base value for latitude. |  |
| `stay_base:grindelwald-grindelwald` | `local_apres_profile.availability` | [Official Grindelwald apres inventory](https://grindelwald.swiss/en/detail-events/apres-ski-820fef28-8137-4060-83c0-dfdd6973cc0b.html) | `"available"` | The cited source supports the reviewed stay_base value for local_apres_profile.availability. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_base:grindelwald-grindelwald` | `local_apres_profile.intensity` | [Official Grindelwald apres inventory](https://grindelwald.swiss/en/detail-events/apres-ski-820fef28-8137-4060-83c0-dfdd6973cc0b.html) | `"lively"` | The cited source supports the reviewed stay_base value for local_apres_profile.intensity. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_base:grindelwald-grindelwald` | `local_apres_profile.season_label` | [Official Grindelwald apres inventory](https://grindelwald.swiss/en/detail-events/apres-ski-820fef28-8137-4060-83c0-dfdd6973cc0b.html) | `"2025/26"` | The cited source supports the reviewed stay_base value for local_apres_profile.season_label. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_base:grindelwald-grindelwald` | `longitude` | [OpenStreetMap Grindelwald relation](https://www.openstreetmap.org/relation/1682457) | `8.0367462` | The cited source supports the reviewed stay_base value for longitude. |  |
| `stay_base:grindelwald-grindelwald` | `name` | [Official Grindelwald destination page](https://www.jungfrau.ch/en-gb/grindelwald) | `"Grindelwald"` | The cited source supports the reviewed stay_base value for name. |  |
| `stay_base:grindelwald-grindelwald` | `regional_data_ids` | [OpenStreetMap Grindelwald relation](https://www.openstreetmap.org/relation/1682457) | `{"osm_relation_id": "1682457"}` | The cited source supports the reviewed stay_base value for regional_data_ids. |  |
| `stay_base:grindelwald-grindelwald` | `stay_base_id` | [Official Grindelwald destination page](https://www.jungfrau.ch/en-gb/grindelwald) | `"grindelwald-grindelwald"` | The cited source supports the reviewed stay_base value for stay_base_id. |  |
| `stay_base:grindelwald-grindelwald` | `stay_destination_id` | [Official Grindelwald destination page](https://www.jungfrau.ch/en-gb/grindelwald) | `"grindelwald"` | The cited source supports the reviewed stay_base value for stay_destination_id. |  |
| `stay_base:wengen-wengen` | `base_character.development_style` | [Official Wengen historic hotel listing](https://wengen.swiss/en/map/detail/hotel-bellevue-traditional-swiss-hideaway-e23f9742-7c22-49a7-9a8b-e8a97ff239f5.html) | `"mixed"` | The cited source supports the reviewed stay_base value for base_character.development_style. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_base:wengen-wengen` | `base_character.local_pace` | [Official Wengen apres venue page](https://wengen.swiss/en/map/detail/apres-ski-bar-hasenstall-89551e4f-668d-4c16-ab72-928b537258f0.html) | `"lively"` | The cited source supports the reviewed stay_base value for base_character.local_pace. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_base:wengen-wengen` | `base_type` | [Official Wengen destination page](https://wengen.swiss/en/destination/about-wengen.html) | `"village"` | The cited source supports the reviewed stay_base value for base_type. |  |
| `stay_base:wengen-wengen` | `elevation_m` | [Official Wengen destination page](https://wengen.swiss/en/destination/about-wengen.html) | `1274` | The cited source supports the reviewed stay_base value for elevation_m. |  |
| `stay_base:wengen-wengen` | `latitude` | [OpenStreetMap Wengen place node](https://www.openstreetmap.org/node/240096898) | `46.6054411` | The cited source supports the reviewed stay_base value for latitude. |  |
| `stay_base:wengen-wengen` | `local_apres_profile.availability` | [Official Wengen apres venue page](https://wengen.swiss/en/map/detail/apres-ski-bar-hasenstall-89551e4f-668d-4c16-ab72-928b537258f0.html) | `"available"` | The cited source supports the reviewed stay_base value for local_apres_profile.availability. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_base:wengen-wengen` | `local_apres_profile.intensity` | [Official Wengen apres venue page](https://wengen.swiss/en/map/detail/apres-ski-bar-hasenstall-89551e4f-668d-4c16-ab72-928b537258f0.html) | `"lively"` | The cited source supports the reviewed stay_base value for local_apres_profile.intensity. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_base:wengen-wengen` | `longitude` | [OpenStreetMap Wengen place node](https://www.openstreetmap.org/node/240096898) | `7.9217237` | The cited source supports the reviewed stay_base value for longitude. |  |
| `stay_base:wengen-wengen` | `name` | [Official Wengen destination page](https://wengen.swiss/en/destination/about-wengen.html) | `"Wengen"` | The cited source supports the reviewed stay_base value for name. |  |
| `stay_base:wengen-wengen` | `regional_data_ids` | [OpenStreetMap Wengen place node](https://www.openstreetmap.org/node/240096898) | `{"osm_node_id": "240096898"}` | The cited source supports the reviewed stay_base value for regional_data_ids. |  |
| `stay_base:wengen-wengen` | `stay_base_id` | [Official Wengen destination page](https://wengen.swiss/en/destination/about-wengen.html) | `"wengen-wengen"` | The cited source supports the reviewed stay_base value for stay_base_id. |  |
| `stay_base:wengen-wengen` | `stay_destination_id` | [Official Wengen destination page](https://wengen.swiss/en/destination/about-wengen.html) | `"wengen"` | The cited source supports the reviewed stay_base value for stay_destination_id. |  |
| `stay_destination:grindelwald` | `country` | [Official Grindelwald destination page](https://www.jungfrau.ch/en-gb/grindelwald) | `"Switzerland"` | The cited source supports the reviewed stay_destination value for country. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:grindelwald` | `latitude` | [OpenStreetMap Grindelwald relation](https://www.openstreetmap.org/relation/1682457) | `46.6242733` | The cited source supports the reviewed stay_destination value for latitude. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:grindelwald` | `longitude` | [OpenStreetMap Grindelwald relation](https://www.openstreetmap.org/relation/1682457) | `8.0367462` | The cited source supports the reviewed stay_destination value for longitude. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:grindelwald` | `name` | [Official Grindelwald destination page](https://www.jungfrau.ch/en-gb/grindelwald) | `"Grindelwald"` | The cited source supports the reviewed stay_destination value for name. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:grindelwald` | `region` | [Official Grindelwald destination page](https://www.jungfrau.ch/en-gb/grindelwald) | `"Bernese Oberland"` | The cited source supports the reviewed stay_destination value for region. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:grindelwald` | `regional_data_ids` | [OpenStreetMap Grindelwald relation](https://www.openstreetmap.org/relation/1682457) | `{"osm_relation_id": "1682457"}` | The cited source supports the reviewed stay_destination value for regional_data_ids. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:grindelwald` | `stay_destination_id` | [Official Grindelwald destination page](https://www.jungfrau.ch/en-gb/grindelwald) | `"grindelwald"` | The cited source supports the reviewed stay_destination value for stay_destination_id. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:grindelwald` | `trip_market_region_id` | [Official Grindelwald destination page](https://www.jungfrau.ch/en-gb/grindelwald) | `"grindelwald-wengen"` | The cited source supports the reviewed stay_destination value for trip_market_region_id. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:wengen` | `country` | [Official Wengen destination page](https://wengen.swiss/en/destination/about-wengen.html) | `"Switzerland"` | The cited source supports the reviewed stay_destination value for country. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:wengen` | `latitude` | [OpenStreetMap Wengen place node](https://www.openstreetmap.org/node/240096898) | `46.6054411` | The cited source supports the reviewed stay_destination value for latitude. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:wengen` | `longitude` | [OpenStreetMap Wengen place node](https://www.openstreetmap.org/node/240096898) | `7.9217237` | The cited source supports the reviewed stay_destination value for longitude. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:wengen` | `name` | [Official Wengen destination page](https://wengen.swiss/en/destination/about-wengen.html) | `"Wengen"` | The cited source supports the reviewed stay_destination value for name. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:wengen` | `region` | [Official Wengen destination page](https://wengen.swiss/en/destination/about-wengen.html) | `"Bernese Oberland"` | The cited source supports the reviewed stay_destination value for region. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:wengen` | `regional_data_ids` | [OpenStreetMap Wengen place node](https://www.openstreetmap.org/node/240096898) | `{"osm_node_id": "240096898"}` | The cited source supports the reviewed stay_destination value for regional_data_ids. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:wengen` | `stay_destination_id` | [Official Wengen destination page](https://wengen.swiss/en/destination/about-wengen.html) | `"wengen"` | The cited source supports the reviewed stay_destination value for stay_destination_id. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:wengen` | `trip_market_region_id` | [Official Wengen destination page](https://wengen.swiss/en/destination/about-wengen.html) | `"grindelwald-wengen"` | The cited source supports the reviewed stay_destination value for trip_market_region_id. | The cited source is normalized into the catalog's typed owner, relationship, or controlled vocabulary. |
| `stay_destination:grindelwald-wengen` | `name` | [Official Wengen Tourism company page](https://wengen.swiss/en/about-us/company.html) | `"Separate Grindelwald and Wengen destination brands"` | Official tourism treats Grindelwald and Wengen as separate destination brands rather than one accommodation market. | The source-backed topology is normalized into the explicit Snowcast graph decision. |
| `stay_base:grindelwald-wengen-grindelwald` | `stay_base_id` | [Official Grindelwald destination page](https://www.jungfrau.ch/en-gb/grindelwald) | `"Grindelwald"` | The legacy base belongs to the explicit Grindelwald destination rather than a combined destination. | The source-backed topology is normalized into the explicit Snowcast graph decision. |
| `ski_area_access:grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area` | `ski_area_access_id` | [Official Grindelwald-Wengen ski-area page](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/grindelwald-wengen/) | `"Grindelwald to Grindelwald-Wengen access"` | The access relationship is retained under the corrected Grindelwald base identity. | The source-backed topology is normalized into the explicit Snowcast graph decision. |
| `stay_base:grindelwald-grindelwald` | `name` | [Official Grindelwald arrival page](https://grindelwald.swiss/en/destination/arrival.html) | `"Grindelwald railway and Terminal access points"` | Official material presents Grund and Terminal as access points within Grindelwald, not as an independent accommodation market. | The source-backed topology is normalized into the explicit Snowcast graph decision. |
| `lift_pass_product:jungfrau-ski-region-pass` | `valid_ski_area_ids` | [Official Jungfrau Ski Region overview](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/) | `["Grindelwald-Wengen", "Grindelwald-First", "Mürren-Schilthorn"]` | The operator presents three distinct ski areas under one pass and requires transport between the separate systems. | The source-backed topology is normalized into the explicit Snowcast graph decision. |
| `lift_pass_product:jungfrau-ski-region-pass` | `external_validity_summary` | [Official Jungfrau Ski Region overview](https://www.jungfrau.ch/en-gb/jungfrau-ski-region/) | `"Mürren-Schilthorn"` | The official three-area inventory establishes Mürren-Schilthorn as missing pass-covered catalog scope. | The source-backed topology is normalized into the explicit Snowcast graph decision. |

## Boundary Decisions

- `grindelwald`: `pass`
- `wengen`: `pass`

## Weather Request Geometry

- `grindelwald-wengen-ski-area`: material change

## Ranking Impact

The corrected destination, ski-area, and access ownership changes the facts available to downstream planning and ranking. Ranking policy is intentionally unchanged and outside this curation.

## Verification

- `UV_PROJECT_ENVIRONMENT=/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv uv run --no-config --no-sync python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_PROJECT_ENVIRONMENT=/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv uv run --no-config --no-sync python -m app.data.validate_catalog_curation typed docs/catalog-curation/2026-06-27-grindelwald-wengen-full-curation.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output docs/catalog-curation/2026-06-27-grindelwald-wengen-full-curation.md`
- `UV_PROJECT_ENVIRONMENT=/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv uv run --no-config --no-sync python -m app.data.validate_catalog_curation reconcile docs/catalog-curation/2026-06-27-grindelwald-wengen-full-curation.json --base-catalog-path /private/tmp/snowcast-current-main-review/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path /private/tmp/snowcast-current-main-review/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output docs/catalog-curation/2026-06-27-grindelwald-wengen-full-curation.md`

## Caveats

- The stable Grindelwald-Wengen weather ID is retained, but its exact representative latitude and longitude remain unresolved pending a policy-backed area-coordinate source.
- The Grindelwald-Wengen summit correction changes weather request elevation bands; the owner must run a forced history refetch and rebuild climatology after deployment.
- Grindelwald-First is a new weather identity and requires owner-run history backfill and climatology after deployment.
- Official sources do not publish clean child-scope piste-kilometre splits by difficulty for either modeled ski area.
- Grindelwald-First official pages currently conflict between 56 km on the dedicated ski-area page and 58 km on a broader attraction page; the narrower current ski-area value is retained.
- No accepted child-scope sources establish a current snowmaking percentage for either area or the unresolved feature fields recorded in field coverage.
- The 2026/27 tariff publishes 45 transport facilities while the current live overview has shown a different count, so pass-level lift count remains unset.
- Lodging and rental price and quality fields remain product-curated estimates pending dedicated sampling policies.
- Mürren, its base, Mürren-Schilthorn ski area, and access edge are deferred together to the Jungfrau Region catalog extension backlog item.
