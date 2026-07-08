# LAAX full catalog curation - Flims Laax Falera destination and access correction

Rebuilds PR #21 on current main. Flims, Laax, and Falera are separate stay destinations in one Flims Laax Falera trip market; Laax Dorf and Laax Murschetg are separated into distinct stay bases; and all four base-to-mountain relationships point to one connected LAAX ski area. The report records the shared pass, current official trail map, published Winter 2025/26 season, terrain and feature facts, and reproducible access geometry without inventing a terrain domain or copying village facts across owners.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:laax-ski-snowboard-ticket` | `full` | all canonical fields |
| `rental_display_fact:laax-laax-rental` | `full` | all canonical fields |
| `rental_display_fact:laax-murschetg-rental` | `full` | all canonical fields |
| `ski_area:laax-ski-area` | `full` | all canonical fields |
| `ski_area_access:falera-falera--laax-ski-area` | `full` | all canonical fields |
| `ski_area_access:flims-flims--laax-ski-area` | `full` | all canonical fields |
| `ski_area_access:laax-dorf--laax-ski-area` | `full` | all canonical fields |
| `ski_area_access:laax-laax--laax-ski-area` | `full` | all canonical fields |
| `ski_area_access:laax-murschetg--laax-ski-area` | `full` | all canonical fields |
| `ski_region:laax` | `full` | all canonical fields |
| `stay_base:falera-falera` | `full` | all canonical fields |
| `stay_base:flims-flims` | `full` | all canonical fields |
| `stay_base:laax-dorf` | `full` | all canonical fields |
| `stay_base:laax-laax` | `full` | all canonical fields |
| `stay_base:laax-murschetg` | `full` | all canonical fields |
| `stay_destination:falera` | `full` | all canonical fields |
| `stay_destination:flims` | `full` | all canonical fields |
| `stay_destination:laax` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:laax-ski-snowboard-ticket` | `full` | all canonical fields |
| `trust_manifest:rental_display_facts:laax-laax-rental` | `full` | all canonical fields |
| `trust_manifest:rental_display_facts:laax-murschetg-rental` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:falera-falera--laax-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:flims-flims--laax-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:laax-dorf--laax-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:laax-laax--laax-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:laax-murschetg--laax-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:laax-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_regions:laax` | `full` | all canonical fields |
| `trust_manifest:stay_bases:falera-falera` | `full` | all canonical fields |
| `trust_manifest:stay_bases:flims-flims` | `full` | all canonical fields |
| `trust_manifest:stay_bases:laax-dorf` | `full` | all canonical fields |
| `trust_manifest:stay_bases:laax-laax` | `full` | all canonical fields |
| `trust_manifest:stay_bases:laax-murschetg` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:falera` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:flims` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:laax` | `full` | all canonical fields |

## Entity Scope Assessments

| Candidate | Kind | Disposition | Signals | Catalog Targets | Evidence | Backlog | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `falera` (Falera) | `stay_destination` | `add_entity` | `independent_stay_market`, `distinct_access` | `stay_destination:falera` | `change-168` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `flims` (Flims) | `stay_destination` | `add_entity` | `independent_stay_market`, `distinct_access` | `stay_destination:flims` | `change-177` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `laax` (Laax) | `stay_destination` | `represented` | `independent_stay_market`, `distinct_access` | `stay_destination:laax` | `boundary-laax` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `falera-falera` (Falera) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:falera-falera` | `change-106` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `flims-flims` (Flims) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:flims-flims` | `change-121` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `laax-dorf` (Laax Dorf) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:laax-dorf` | `change-136` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `laax-murschetg` (Laax Murschetg) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:laax-murschetg` | `change-163` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `laax-laax` (Legacy blended Laax base) | `stay_base` | `not_separate` | `distinct_access` | `stay_base:laax-laax` | `scope-retired-base` |  | The legacy blended record is retired because official material establishes more precise source-backed owners. |
| `laax-ski-area` (LAAX) | `ski_area` | `represented` | `official_independent_identity`, `ski_connected_terrain` | `ski_area:laax-ski-area` | `change-042` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `falera-falera--laax-ski-area` (Falera to LAAX) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:falera-falera--laax-ski-area` | `change-049` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `flims-flims--laax-ski-area` (Flims to LAAX) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:flims-flims--laax-ski-area` | `change-059` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `laax-dorf--laax-ski-area` (Laax Dorf to LAAX) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:laax-dorf--laax-ski-area` | `change-069` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `laax-murschetg--laax-ski-area` (Laax Murschetg to LAAX) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:laax-murschetg--laax-ski-area` | `change-087` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |
| `laax-laax--laax-ski-area` (Legacy blended Laax access) | `ski_area_access` | `not_separate` | `direct_access_relationship` | `ski_area_access:laax-laax--laax-ski-area` | `scope-retired-access` |  | The legacy blended record is retired because official material establishes more precise source-backed owners. |
| `laax-ski-snowboard-ticket` (LAAX ski and snowboard ticket) | `lift_pass_product` | `add_entity` | `official_product_identity` | `lift_pass_product:laax-ski-snowboard-ticket` | `change-003` |  | The source-backed graph assigns this candidate to the narrowest owner that preserves its independent stay, access, terrain, or product meaning. |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:laax-ski-snowboard-ticket` | `available_from_stay_destination_ids` | `null` | `["falera", "flims", "laax"]` | `verified_with_adjustment` | no |
| `lift_pass_product:laax-ski-snowboard-ticket` | `default_for_stay_destination_ids` | `null` | `["falera", "flims", "laax"]` | `verified_with_adjustment` | no |
| `lift_pass_product:laax-ski-snowboard-ticket` | `lift_pass_product_id` | `null` | `"laax-ski-snowboard-ticket"` | `verified_with_adjustment` | no |
| `lift_pass_product:laax-ski-snowboard-ticket` | `name` | `null` | `"LAAX ski and snowboard ticket"` | `verified_with_adjustment` | no |
| `lift_pass_product:laax-ski-snowboard-ticket` | `prices` | `null` | `[{"amount": null, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "unknown", "season_label": "Winter 2025/26 dynamic day and multi-day tickets", "source_url": "https://www.laax.com/en/tickets"}]` | `verified_with_adjustment` | no |
| `lift_pass_product:laax-ski-snowboard-ticket` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | no |
| `lift_pass_product:laax-ski-snowboard-ticket` | `valid_ski_area_ids` | `null` | `["laax-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:laax-ski-snowboard-ticket` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | no |
| `rental_display_fact:laax-laax-rental` | `lift_distance` | `"near"` | `null` | `estimated` | no |
| `rental_display_fact:laax-laax-rental` | `name` | `"LAAX Rental"` | `null` | `estimated` | no |
| `rental_display_fact:laax-laax-rental` | `price_max` | `55.0` | `null` | `estimated` | no |
| `rental_display_fact:laax-laax-rental` | `price_min` | `35.0` | `null` | `estimated` | no |
| `rental_display_fact:laax-laax-rental` | `price_range` | `"EUR 35-55"` | `null` | `estimated` | no |
| `rental_display_fact:laax-laax-rental` | `quality` | `"standard"` | `null` | `estimated` | no |
| `rental_display_fact:laax-laax-rental` | `rental_display_fact_id` | `"laax-laax-rental"` | `null` | `estimated` | no |
| `rental_display_fact:laax-laax-rental` | `stay_destination_id` | `"laax"` | `null` | `estimated` | no |
| `rental_display_fact:laax-murschetg-rental` | `lift_distance` | `null` | `"near"` | `estimated` | no |
| `rental_display_fact:laax-murschetg-rental` | `name` | `null` | `"LAAX Rental"` | `estimated` | no |
| `rental_display_fact:laax-murschetg-rental` | `price_max` | `null` | `55.0` | `estimated` | no |
| `rental_display_fact:laax-murschetg-rental` | `price_min` | `null` | `35.0` | `estimated` | no |
| `rental_display_fact:laax-murschetg-rental` | `price_range` | `null` | `"EUR 35-55"` | `estimated` | no |
| `rental_display_fact:laax-murschetg-rental` | `quality` | `null` | `"standard"` | `estimated` | no |
| `rental_display_fact:laax-murschetg-rental` | `rental_display_fact_id` | `null` | `"laax-murschetg-rental"` | `estimated` | no |
| `rental_display_fact:laax-murschetg-rental` | `stay_base_id` | `null` | `"laax-murschetg"` | `estimated` | no |
| `rental_display_fact:laax-murschetg-rental` | `stay_destination_id` | `null` | `"laax"` | `estimated` | no |
| `ski_area:laax-ski-area` | `glacier_terrain.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:laax-ski-area` | `marked_freeride_routes.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:laax-ski-area` | `marked_freeride_routes.route_count` | `null` | `12` | `verified` | no |
| `ski_area:laax-ski-area` | `night_skiing.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:laax-ski-area` | `night_skiing.season_label` | `null` | `"2025/26"` | `verified` | no |
| `ski_area:laax-ski-area` | `official_trail_map.url` | `null` | `"https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf"` | `verified` | no |
| `ski_area:laax-ski-area` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `ski_area:laax-ski-area` | `season_windows` | `[]` | `[{"end_date": "2026-04-12", "season_label": "Winter 2025/26", "start_date": "2025-11-29", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:laax-ski-area` | `ski_day_apres_profile.availability` | `"unknown"` | `"available"` | `verified_with_adjustment` | no |
| `ski_area:laax-ski-area` | `ski_day_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `ski_area:laax-ski-area` | `snow_park.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:laax-ski-area` | `snow_park.park_count` | `null` | `5` | `verified` | no |
| `ski_area:laax-ski-area` | `snow_park.season_label` | `null` | `"2025/26"` | `verified` | no |
| `ski_area:laax-ski-area` | `snowmaking.availability` | `"unknown"` | `"available"` | `verified_with_adjustment` | no |
| `ski_area:laax-ski-area` | `supported_skill_levels` | `["intermediate", "advanced"]` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:laax-ski-area` | `total_lift_count` | `null` | `30` | `verified` | yes |
| `ski_area:laax-ski-area` | `total_piste_km` | `null` | `216.0` | `verified` | yes |
| `ski_area_access:falera-falera--laax-ski-area` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:falera-falera--laax-ski-area` | `distance_m` | `null` | `358` | `verified_with_adjustment` | yes |
| `ski_area_access:falera-falera--laax-ski-area` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:falera-falera--laax-ski-area` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:falera-falera--laax-ski-area` | `nearest_lift_name` | `null` | `"Falera-Curnius chairlift"` | `verified_with_adjustment` | no |
| `ski_area_access:falera-falera--laax-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "330181586", "stay_base_osm_relation_id": "1684074"}` | `verified_with_adjustment` | no |
| `ski_area_access:falera-falera--laax-ski-area` | `ski_area_access_id` | `null` | `"falera-falera--laax-ski-area"` | `verified_with_adjustment` | no |
| `ski_area_access:falera-falera--laax-ski-area` | `ski_area_id` | `null` | `"laax-ski-area"` | `verified_with_adjustment` | no |
| `ski_area_access:falera-falera--laax-ski-area` | `source_urls` | `null` | `["https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/330181586", "https://www.openstreetmap.org/relation/1684074"]` | `verified_with_adjustment` | no |
| `ski_area_access:falera-falera--laax-ski-area` | `stay_base_id` | `null` | `"falera-falera"` | `verified_with_adjustment` | no |
| `ski_area_access:flims-flims--laax-ski-area` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:flims-flims--laax-ski-area` | `distance_m` | `null` | `559` | `verified_with_adjustment` | yes |
| `ski_area_access:flims-flims--laax-ski-area` | `is_direct` | `null` | `false` | `verified_with_adjustment` | yes |
| `ski_area_access:flims-flims--laax-ski-area` | `lift_distance` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `ski_area_access:flims-flims--laax-ski-area` | `nearest_lift_name` | `null` | `"FlemXpress Flims valley station"` | `verified_with_adjustment` | no |
| `ski_area_access:flims-flims--laax-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "10681585981", "stay_base_osm_node_id": "33589791"}` | `verified_with_adjustment` | no |
| `ski_area_access:flims-flims--laax-ski-area` | `ski_area_access_id` | `null` | `"flims-flims--laax-ski-area"` | `verified_with_adjustment` | no |
| `ski_area_access:flims-flims--laax-ski-area` | `ski_area_id` | `null` | `"laax-ski-area"` | `verified_with_adjustment` | no |
| `ski_area_access:flims-flims--laax-ski-area` | `source_urls` | `null` | `["https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/10681585981", "https://www.openstreetmap.org/node/33589791"]` | `verified_with_adjustment` | no |
| `ski_area_access:flims-flims--laax-ski-area` | `stay_base_id` | `null` | `"flims-flims"` | `verified_with_adjustment` | no |
| `ski_area_access:laax-dorf--laax-ski-area` | `access_mode` | `null` | `"ski_bus"` | `verified_with_adjustment` | yes |
| `ski_area_access:laax-dorf--laax-ski-area` | `distance_m` | `null` | `1578` | `verified_with_adjustment` | yes |
| `ski_area_access:laax-dorf--laax-ski-area` | `is_direct` | `null` | `false` | `verified_with_adjustment` | yes |
| `ski_area_access:laax-dorf--laax-ski-area` | `lift_distance` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `ski_area_access:laax-dorf--laax-ski-area` | `nearest_lift_name` | `null` | `"Laax Murschetg valley station"` | `verified_with_adjustment` | no |
| `ski_area_access:laax-dorf--laax-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "244501524", "stay_base_osm_relation_id": "1684097"}` | `verified_with_adjustment` | no |
| `ski_area_access:laax-dorf--laax-ski-area` | `ski_area_access_id` | `null` | `"laax-dorf--laax-ski-area"` | `verified_with_adjustment` | no |
| `ski_area_access:laax-dorf--laax-ski-area` | `ski_area_id` | `null` | `"laax-ski-area"` | `verified_with_adjustment` | no |
| `ski_area_access:laax-dorf--laax-ski-area` | `source_urls` | `null` | `["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.flimslaax.com/en/transport", "https://www.openstreetmap.org/node/244501524", "https://www.openstreetmap.org/relation/1684097"]` | `verified_with_adjustment` | no |
| `ski_area_access:laax-dorf--laax-ski-area` | `stay_base_id` | `null` | `"laax-dorf"` | `verified_with_adjustment` | no |
| `ski_area_access:laax-laax--laax-ski-area` | `access_mode` | `"unknown"` | `null` | `estimated` | no |
| `ski_area_access:laax-laax--laax-ski-area` | `is_direct` | `false` | `null` | `estimated` | no |
| `ski_area_access:laax-laax--laax-ski-area` | `lift_distance` | `"near"` | `null` | `estimated` | no |
| `ski_area_access:laax-laax--laax-ski-area` | `regional_data_ids` | `{}` | `null` | `estimated` | no |
| `ski_area_access:laax-laax--laax-ski-area` | `ski_area_access_id` | `"laax-laax--laax-ski-area"` | `null` | `estimated` | no |
| `ski_area_access:laax-laax--laax-ski-area` | `ski_area_id` | `"laax-ski-area"` | `null` | `estimated` | no |
| `ski_area_access:laax-laax--laax-ski-area` | `source_urls` | `["https://www.bergfex.com/laax/"]` | `null` | `estimated` | no |
| `ski_area_access:laax-laax--laax-ski-area` | `stay_base_id` | `"laax-laax"` | `null` | `estimated` | no |
| `ski_area_access:laax-murschetg--laax-ski-area` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:laax-murschetg--laax-ski-area` | `distance_m` | `null` | `127` | `verified_with_adjustment` | yes |
| `ski_area_access:laax-murschetg--laax-ski-area` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:laax-murschetg--laax-ski-area` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:laax-murschetg--laax-ski-area` | `nearest_lift_name` | `null` | `"Laax Murschetg valley station"` | `verified_with_adjustment` | no |
| `ski_area_access:laax-murschetg--laax-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "244501524", "stay_base_osm_node_id": "244479992"}` | `verified_with_adjustment` | no |
| `ski_area_access:laax-murschetg--laax-ski-area` | `ski_area_access_id` | `null` | `"laax-murschetg--laax-ski-area"` | `verified_with_adjustment` | no |
| `ski_area_access:laax-murschetg--laax-ski-area` | `ski_area_id` | `null` | `"laax-ski-area"` | `verified_with_adjustment` | no |
| `ski_area_access:laax-murschetg--laax-ski-area` | `source_urls` | `null` | `["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/244479992", "https://www.openstreetmap.org/node/244501524"]` | `verified_with_adjustment` | no |
| `ski_area_access:laax-murschetg--laax-ski-area` | `stay_base_id` | `null` | `"laax-murschetg"` | `verified_with_adjustment` | no |
| `ski_region:laax` | `name` | `"Laax"` | `"Flims Laax Falera"` | `verified_with_adjustment` | no |
| `ski_region:laax` | `source_urls` | `[]` | `["https://www.flimslaax.com/en/getting-there", "https://www.flimslaax.com/en/winter/ski-resort/ski-snowboard"]` | `verified_with_adjustment` | no |
| `stay_base:falera-falera` | `base_character.development_style` | `null` | `"traditional"` | `verified_with_adjustment` | no |
| `stay_base:falera-falera` | `base_character.local_pace` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:falera-falera` | `base_type` | `null` | `"village"` | `verified_with_adjustment` | no |
| `stay_base:falera-falera` | `elevation_m` | `null` | `1220` | `verified_with_adjustment` | no |
| `stay_base:falera-falera` | `latitude` | `null` | `46.8007977` | `verified_with_adjustment` | no |
| `stay_base:falera-falera` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:falera-falera` | `longitude` | `null` | `9.2321371` | `verified_with_adjustment` | no |
| `stay_base:falera-falera` | `name` | `null` | `"Falera"` | `verified_with_adjustment` | no |
| `stay_base:falera-falera` | `price_max` | `null` | `250.0` | `estimated` | no |
| `stay_base:falera-falera` | `price_min` | `null` | `170.0` | `estimated` | no |
| `stay_base:falera-falera` | `price_range` | `null` | `"EUR 170-250"` | `estimated` | no |
| `stay_base:falera-falera` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:falera-falera` | `regional_data_ids` | `null` | `{"osm_relation_id": "1684074"}` | `verified_with_adjustment` | no |
| `stay_base:falera-falera` | `stay_base_id` | `null` | `"falera-falera"` | `verified_with_adjustment` | no |
| `stay_base:falera-falera` | `stay_destination_id` | `null` | `"falera"` | `verified_with_adjustment` | yes |
| `stay_base:flims-flims` | `base_character.development_style` | `null` | `"mixed"` | `verified_with_adjustment` | no |
| `stay_base:flims-flims` | `base_character.local_pace` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:flims-flims` | `base_type` | `null` | `"village"` | `verified_with_adjustment` | no |
| `stay_base:flims-flims` | `elevation_m` | `null` | `1100` | `verified_with_adjustment` | no |
| `stay_base:flims-flims` | `latitude` | `null` | `46.8367698` | `verified_with_adjustment` | no |
| `stay_base:flims-flims` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:flims-flims` | `longitude` | `null` | `9.2876705` | `verified_with_adjustment` | no |
| `stay_base:flims-flims` | `name` | `null` | `"Flims"` | `verified_with_adjustment` | no |
| `stay_base:flims-flims` | `price_max` | `null` | `280.0` | `estimated` | no |
| `stay_base:flims-flims` | `price_min` | `null` | `190.0` | `estimated` | no |
| `stay_base:flims-flims` | `price_range` | `null` | `"EUR 190-280"` | `estimated` | no |
| `stay_base:flims-flims` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:flims-flims` | `regional_data_ids` | `null` | `{"osm_node_id": "33589791"}` | `verified_with_adjustment` | no |
| `stay_base:flims-flims` | `stay_base_id` | `null` | `"flims-flims"` | `verified_with_adjustment` | no |
| `stay_base:flims-flims` | `stay_destination_id` | `null` | `"flims"` | `verified_with_adjustment` | yes |
| `stay_base:laax-dorf` | `base_character.development_style` | `null` | `"traditional"` | `verified_with_adjustment` | no |
| `stay_base:laax-dorf` | `base_character.local_pace` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:laax-dorf` | `base_type` | `null` | `"village"` | `verified_with_adjustment` | no |
| `stay_base:laax-dorf` | `elevation_m` | `null` | `1020` | `verified_with_adjustment` | no |
| `stay_base:laax-dorf` | `latitude` | `null` | `46.806412` | `verified_with_adjustment` | no |
| `stay_base:laax-dorf` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:laax-dorf` | `longitude` | `null` | `9.2581267` | `verified_with_adjustment` | no |
| `stay_base:laax-dorf` | `name` | `null` | `"Laax Dorf"` | `verified_with_adjustment` | no |
| `stay_base:laax-dorf` | `price_max` | `null` | `260.0` | `estimated` | no |
| `stay_base:laax-dorf` | `price_min` | `null` | `180.0` | `estimated` | no |
| `stay_base:laax-dorf` | `price_range` | `null` | `"EUR 180-260"` | `estimated` | no |
| `stay_base:laax-dorf` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:laax-dorf` | `regional_data_ids` | `null` | `{"osm_relation_id": "1684097"}` | `verified_with_adjustment` | no |
| `stay_base:laax-dorf` | `stay_base_id` | `null` | `"laax-dorf"` | `verified_with_adjustment` | no |
| `stay_base:laax-dorf` | `stay_destination_id` | `null` | `"laax"` | `verified_with_adjustment` | yes |
| `stay_base:laax-laax` | `base_character.development_style` | `"unknown"` | `null` | `estimated` | no |
| `stay_base:laax-laax` | `base_character.local_pace` | `"unknown"` | `null` | `estimated` | no |
| `stay_base:laax-laax` | `local_apres_profile.availability` | `"unknown"` | `null` | `estimated` | no |
| `stay_base:laax-laax` | `name` | `"Laax"` | `null` | `estimated` | no |
| `stay_base:laax-laax` | `price_max` | `270.0` | `null` | `estimated` | no |
| `stay_base:laax-laax` | `price_min` | `200.0` | `null` | `estimated` | no |
| `stay_base:laax-laax` | `price_range` | `"EUR 200-270"` | `null` | `estimated` | no |
| `stay_base:laax-laax` | `quality` | `"standard"` | `null` | `estimated` | no |
| `stay_base:laax-laax` | `regional_data_ids` | `{}` | `null` | `estimated` | no |
| `stay_base:laax-laax` | `stay_base_id` | `"laax-laax"` | `null` | `estimated` | no |
| `stay_base:laax-laax` | `stay_destination_id` | `"laax"` | `null` | `estimated` | no |
| `stay_base:laax-murschetg` | `base_character.development_style` | `null` | `"planned_resort"` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `base_character.local_pace` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `base_type` | `null` | `"resort_station"` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `elevation_m` | `null` | `1100` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `latitude` | `null` | `46.8193045` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `local_apres_profile.availability` | `null` | `"available"` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `local_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `longitude` | `null` | `9.2643581` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `name` | `null` | `"Laax Murschetg"` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `price_max` | `null` | `320.0` | `estimated` | no |
| `stay_base:laax-murschetg` | `price_min` | `null` | `220.0` | `estimated` | no |
| `stay_base:laax-murschetg` | `price_range` | `null` | `"EUR 220-320"` | `estimated` | no |
| `stay_base:laax-murschetg` | `quality` | `null` | `"premium"` | `estimated` | no |
| `stay_base:laax-murschetg` | `regional_data_ids` | `null` | `{"osm_node_id": "244479992"}` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `stay_base_id` | `null` | `"laax-murschetg"` | `verified_with_adjustment` | no |
| `stay_base:laax-murschetg` | `stay_destination_id` | `null` | `"laax"` | `verified_with_adjustment` | yes |
| `stay_destination:falera` | `country` | `null` | `"Switzerland"` | `verified_with_adjustment` | no |
| `stay_destination:falera` | `latitude` | `null` | `46.8007977` | `verified_with_adjustment` | no |
| `stay_destination:falera` | `longitude` | `null` | `9.2321371` | `verified_with_adjustment` | no |
| `stay_destination:falera` | `name` | `null` | `"Falera"` | `verified_with_adjustment` | no |
| `stay_destination:falera` | `price_level` | `null` | `"medium"` | `estimated` | no |
| `stay_destination:falera` | `region` | `null` | `"Graubunden"` | `verified_with_adjustment` | no |
| `stay_destination:falera` | `regional_data_ids` | `null` | `{"osm_relation_id": "1684074"}` | `verified_with_adjustment` | no |
| `stay_destination:falera` | `stay_destination_id` | `null` | `"falera"` | `verified_with_adjustment` | no |
| `stay_destination:falera` | `trip_market_region_id` | `null` | `"laax"` | `verified_with_adjustment` | no |
| `stay_destination:flims` | `country` | `null` | `"Switzerland"` | `verified_with_adjustment` | no |
| `stay_destination:flims` | `latitude` | `null` | `46.8332439` | `verified_with_adjustment` | no |
| `stay_destination:flims` | `longitude` | `null` | `9.2834557` | `verified_with_adjustment` | no |
| `stay_destination:flims` | `name` | `null` | `"Flims"` | `verified_with_adjustment` | no |
| `stay_destination:flims` | `price_level` | `null` | `"medium"` | `estimated` | no |
| `stay_destination:flims` | `region` | `null` | `"Graubunden"` | `verified_with_adjustment` | no |
| `stay_destination:flims` | `regional_data_ids` | `null` | `{"osm_relation_id": "1684080"}` | `verified_with_adjustment` | no |
| `stay_destination:flims` | `stay_destination_id` | `null` | `"flims"` | `verified_with_adjustment` | no |
| `stay_destination:flims` | `trip_market_region_id` | `null` | `"laax"` | `verified_with_adjustment` | no |
| `stay_destination:laax` | `latitude` | `46.8351` | `46.806412` | `verified_with_adjustment` | no |
| `stay_destination:laax` | `longitude` | `9.2583` | `9.2581267` | `verified_with_adjustment` | no |
| `stay_destination:laax` | `regional_data_ids` | `{}` | `{"osm_relation_id": "1684097"}` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:laax-ski-snowboard-ticket` | `display_name` | `null` | `"LAAX ski and snowboard ticket"` | `estimated` | no |
| `trust_manifest:lift_pass_products:laax-ski-snowboard-ticket` | `field_source_refs` | `null` | `{"coverage": ["https://www.laax.com/en/tickets"], "identity_scope_availability": ["https://www.laax.com/en/tickets"], "pass_accessible_terrain": [], "prices": ["https://www.laax.com/en/tickets"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:laax-ski-snowboard-ticket` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:laax-ski-snowboard-ticket` | `notes` | `null` | `["The official LAAX ticket product is available to all three modeled stay destinations and covers the single connected LAAX ski area.", "Winter 2025/26 prices were dynamic, so the product is retained with price_kind=unknown rather than an invented fixed amount."]` | `estimated` | no |
| `trust_manifest:rental_display_facts:laax-laax-rental` | `display_name` | `"LAAX Rental"` | `null` | `estimated` | no |
| `trust_manifest:rental_display_facts:laax-laax-rental` | `field_source_refs` | `{"identity_ownership": [], "price_quality_access": []}` | `null` | `estimated` | no |
| `trust_manifest:rental_display_facts:laax-laax-rental` | `field_statuses` | `{"identity_ownership": "estimated", "price_quality_access": "estimated"}` | `null` | `estimated` | no |
| `trust_manifest:rental_display_facts:laax-laax-rental` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands."]` | `null` | `estimated` | no |
| `trust_manifest:rental_display_facts:laax-murschetg-rental` | `display_name` | `null` | `"LAAX Rental"` | `estimated` | no |
| `trust_manifest:rental_display_facts:laax-murschetg-rental` | `field_source_refs` | `null` | `{"identity_ownership": [], "price_quality_access": []}` | `estimated` | no |
| `trust_manifest:rental_display_facts:laax-murschetg-rental` | `field_statuses` | `null` | `{"identity_ownership": "estimated", "price_quality_access": "estimated"}` | `estimated` | no |
| `trust_manifest:rental_display_facts:laax-murschetg-rental` | `notes` | `null` | `["The existing LAAX Rental display fact is assigned to Laax Murschetg, the lift-base district, while identity, pricing, quality, and exact access remain curated estimates pending dedicated rental sourcing."]` | `estimated` | no |
| `trust_manifest:ski_area_access:falera-falera--laax-ski-area` | `display_name` | `null` | `"Falera -> Laax"` | `estimated` | no |
| `trust_manifest:ski_area_access:falera-falera--laax-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/330181586", "https://www.openstreetmap.org/relation/1684074"], "relationship": ["https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/330181586", "https://www.openstreetmap.org/relation/1684074"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:falera-falera--laax-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:falera-falera--laax-ski-area` | `notes` | `null` | `["The official operating page lists the Falera-Curnius chairlift as a winter feeder into LAAX.", "The 358 m distance is a rounded Haversine calculation from the OSM Falera relation centroid to the OSM chairlift valley station."]` | `estimated` | no |
| `trust_manifest:ski_area_access:flims-flims--laax-ski-area` | `display_name` | `null` | `"Flims -> Laax"` | `estimated` | no |
| `trust_manifest:ski_area_access:flims-flims--laax-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/10681585981", "https://www.openstreetmap.org/node/33589791"], "relationship": ["https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/10681585981", "https://www.openstreetmap.org/node/33589791"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:flims-flims--laax-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:flims-flims--laax-ski-area` | `notes` | `null` | `["The official operating page lists FlemX as the Flims winter feeder into LAAX.", "The 559 m distance is a rounded Haversine calculation from the OSM Flims place node to the OSM FlemXpress valley station."]` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-dorf--laax-ski-area` | `display_name` | `null` | `"Laax Dorf -> Laax"` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-dorf--laax-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.flimslaax.com/en/transport", "https://www.openstreetmap.org/node/244501524", "https://www.openstreetmap.org/relation/1684097"], "relationship": ["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.flimslaax.com/en/transport", "https://www.openstreetmap.org/node/244501524", "https://www.openstreetmap.org/relation/1684097"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-dorf--laax-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-dorf--laax-ski-area` | `notes` | `null` | `["Official local-transport information connects Laax village to Laax Murschetg, and the destination page identifies the Laax Posta/Dorf and Laax Bergbahnen stops separately.", "The 1,578 m distance is a rounded Haversine calculation from the OSM Laax relation centroid to the OSM Murschetg valley station; the access mode is ski_bus rather than a routed walking claim."]` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-laax--laax-ski-area` | `display_name` | `"Laax -> Laax"` | `null` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-laax--laax-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/laax/"], "relationship": ["https://www.bergfex.com/laax/"]}` | `null` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-laax--laax-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `null` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-laax--laax-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Provider-backed relationship remains estimated; no exact distance or duration is asserted."]` | `null` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-murschetg--laax-ski-area` | `display_name` | `null` | `"Laax Murschetg -> Laax"` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-murschetg--laax-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/244479992", "https://www.openstreetmap.org/node/244501524"], "relationship": ["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/244479992", "https://www.openstreetmap.org/node/244501524"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-murschetg--laax-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:laax-murschetg--laax-ski-area` | `notes` | `null` | `["Official destination material places the Laax Bergbahnen stop and valley-station district in Murschetg.", "The 127 m distance is a rounded Haversine calculation from the OSM Murschetg place node to the OSM valley station."]` | `estimated` | no |
| `trust_manifest:ski_areas:laax-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://www.laax.com/en/opening-hours", "https://www.laax.com/en/ski-snowboard"], "glacier_terrain": ["https://www.laax.com/en/ski-snowboard"], "identity_coordinates": [], "marked_freeride_routes": ["https://www.laax.com/en/freeride"], "night_skiing": ["https://www.flimslaax.com/en/winter/ski-resort/ski-snowboard"], "official_documents": ["https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf"], "ski_day_apres": ["https://www.laax.com/en", "https://www.laax.com/en/food-drinks"], "skill_fit": ["https://www.laax.com/en/ski-snowboard"], "snow_park": ["https://www.laax.com/en/freestyle"], "snowmaking": ["https://www.laax.com/en/meeting/activity-hinter-den-kulissen-von-laax"], "terrain_metrics": ["https://www.laax.com/en/ski-snowboard"]}` | `estimated` | no |
| `trust_manifest:ski_areas:laax-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "verified", "identity_coordinates": "needs_source", "marked_freeride_routes": "verified", "night_skiing": "verified", "official_documents": "verified", "ski_day_apres": "verified_with_adjustment", "skill_fit": "verified_with_adjustment", "snow_park": "verified", "snowmaking": "verified", "terrain_metrics": "verified"}` | `estimated` | no |
| `trust_manifest:ski_areas:laax-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Current official sources establish one connected LAAX ski area entered from Flims, Laax, and Falera, with 216 km of slopes, 30 lifts, five snowparks, and terrain reaching the Vorab Glacier.", "The published Winter 2025/26 feeder schedule establishes the exact 29 November 2025 to 12 April 2026 operating span; a 2026/27 exact schedule was not yet published at review time.", "Snowmaking coverage remains unset because the operator confirms infrastructure but publishes no percentage or denominator.", "The legacy area request coordinates remain unchanged pending a dedicated weather-geometry migration."]` | `estimated` | no |
| `trust_manifest:ski_regions:laax` | `display_name` | `"Laax"` | `"Flims Laax Falera"` | `estimated` | no |
| `trust_manifest:ski_regions:laax` | `field_source_refs` | `{"identity": [], "membership_context": []}` | `{"identity": ["https://www.flimslaax.com/en/getting-there", "https://www.flimslaax.com/en/winter/ski-resort/ski-snowboard"], "membership_context": ["https://www.flimslaax.com/en/getting-there", "https://www.flimslaax.com/en/winter/ski-resort/ski-snowboard"]}` | `estimated` | no |
| `trust_manifest:ski_regions:laax` | `field_statuses` | `{"identity": "needs_source", "membership_context": "estimated"}` | `{"identity": "verified", "membership_context": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_regions:laax` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Trip-market membership is retained as reviewed migration context and remains estimated.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Official destination material presents Flims, Laax, and Falera as one visitor region with shared transport and one connected winter-sports area.", "The trip market contains three independent stay destinations while the connected terrain remains one ski area."]` | `estimated` | no |
| `trust_manifest:stay_bases:falera-falera` | `display_name` | `null` | `"Falera"` | `estimated` | no |
| `trust_manifest:stay_bases:falera-falera` | `field_source_refs` | `null` | `{"base_character": ["https://www.falera.net/gemeinde/portrait/", "https://www.falera.net/wp-content/uploads/2022/10/KRL_Falera_final.pdf"], "base_type": ["https://www.flimslaax.com/en/transport", "https://www.openstreetmap.org/relation/1684074"], "coordinates": ["https://www.openstreetmap.org/relation/1684074"], "elevation": ["https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf"], "identity_ownership": ["https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/relation/1684074"], "local_apres": [], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:falera-falera` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:falera-falera` | `notes` | `null` | `["Falera is retained as a village base with its own feeder lift; the official slope map labels the base station at 1,220 m.", "The municipality says Falera remained a farming village despite tourism, and its spatial plan protects the historical house-yard-garden settlement pattern; this is normalized to traditional development.", "Lodging price and quality remain product-curated estimates; local pace and recurring apres remain unresolved."]` | `estimated` | no |
| `trust_manifest:stay_bases:flims-flims` | `display_name` | `null` | `"Flims"` | `estimated` | no |
| `trust_manifest:stay_bases:flims-flims` | `field_source_refs` | `null` | `{"base_character": ["https://www.gemeindeflims.ch/geschichte/9071", "https://www.gemeindeflims.ch/geschichtefs"], "base_type": ["https://www.flimslaax.com/en/transport", "https://www.openstreetmap.org/node/33589791"], "coordinates": ["https://www.openstreetmap.org/node/33589791"], "elevation": ["https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf"], "identity_ownership": ["https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/33589791"], "local_apres": [], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:flims-flims` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified_with_adjustment", "elevation": "verified_with_adjustment", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:flims-flims` | `notes` | `null` | `["Flims is retained as a village base around the official Flims feeder; 1,100 m is the operator-published elevation for the Flims base station.", "The municipality describes Flims as a modern holiday resort with tradition and documents substantial hotel and resort development layered onto the inherited settlement; this is normalized to mixed development.", "Lodging price and quality remain product-curated estimates; local pace and recurring apres remain unresolved."]` | `estimated` | no |
| `trust_manifest:stay_bases:laax-dorf` | `display_name` | `null` | `"Laax Dorf"` | `estimated` | no |
| `trust_manifest:stay_bases:laax-dorf` | `field_source_refs` | `null` | `{"base_character": ["https://www.laax-gr.ch/de/das-dorf-laax/geschichte-entwicklung/", "https://www.laax-gr.ch/wp-content/uploads/2022/08/PMB_Genehmigung.pdf"], "base_type": ["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.flimslaax.com/en/transport"], "coordinates": ["https://www.openstreetmap.org/relation/1684097"], "elevation": ["https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf"], "identity_ownership": ["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.openstreetmap.org/relation/1684097"], "local_apres": [], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:laax-dorf` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:laax-dorf` | `notes` | `null` | `["Official destination material explicitly distinguishes Laax village from Laax Murschetg, and the official slope map labels Laax Dorf at 1,020 m.", "Municipal history and planning identify the historically evolved village core and preserved patrician buildings; with planned resort development owned separately by Murschetg, Laax Dorf is normalized to traditional development.", "Lodging price and quality remain product-curated estimates; local pace and recurring apres remain unresolved for Laax Dorf."]` | `estimated` | no |
| `trust_manifest:stay_bases:laax-laax` | `display_name` | `"Laax"` | `null` | `estimated` | no |
| `trust_manifest:stay_bases:laax-laax` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `null` | `estimated` | no |
| `trust_manifest:stay_bases:laax-laax` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `null` | `estimated` | no |
| `trust_manifest:stay_bases:laax-laax` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `null` | `estimated` | no |
| `trust_manifest:stay_bases:laax-murschetg` | `display_name` | `null` | `"Laax Murschetg"` | `estimated` | no |
| `trust_manifest:stay_bases:laax-murschetg` | `field_source_refs` | `null` | `{"base_character": ["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.laax.com/en"], "base_type": ["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.laax.com/en/transportation"], "coordinates": ["https://www.openstreetmap.org/node/244479992"], "elevation": ["https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf", "https://www.laax.com/en/ski-snowboard"], "identity_ownership": ["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.openstreetmap.org/node/244479992"], "local_apres": ["https://www.laax.com/en", "https://www.laax.com/en/food-drinks"], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:laax-murschetg` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified_with_adjustment", "elevation": "verified_with_adjustment", "identity_ownership": "verified", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:laax-murschetg` | `notes` | `null` | `["Laax Murschetg is modeled separately from Laax Dorf because official material identifies the lift-base district, rocksresort development, parking, and public-transport stop independently.", "Its contemporary resort-station development and concentrated bars support planned_resort, lively pace, and lively local apres; lodging price and quality remain estimates."]` | `estimated` | no |
| `trust_manifest:stay_destinations:falera` | `display_name` | `null` | `"Falera"` | `estimated` | no |
| `trust_manifest:stay_destinations:falera` | `field_source_refs` | `null` | `{"coordinates": ["https://www.openstreetmap.org/relation/1684074"], "identity_location": ["https://www.flimslaax.com/en/getting-there", "https://www.flimslaax.com/en/holiday-booking/hotels", "https://www.laax.com/en/opening-hours"], "price_level": []}` | `estimated` | no |
| `trust_manifest:stay_destinations:falera` | `field_statuses` | `null` | `{"coordinates": "verified_with_adjustment", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:falera` | `notes` | `null` | `["Official tourism and lift information treat Falera as a named accommodation village with its own feeder lift into the shared LAAX ski area.", "The medium price level remains a product-curated estimate pending a reviewed accommodation sampling policy."]` | `estimated` | no |
| `trust_manifest:stay_destinations:flims` | `display_name` | `null` | `"Flims"` | `estimated` | no |
| `trust_manifest:stay_destinations:flims` | `field_source_refs` | `null` | `{"coordinates": ["https://www.openstreetmap.org/relation/1684080"], "identity_location": ["https://www.flimslaax.com/en/getting-there", "https://www.flimslaax.com/en/holiday-booking/hotels", "https://www.laax.com/en/opening-hours"], "price_level": []}` | `estimated` | no |
| `trust_manifest:stay_destinations:flims` | `field_statuses` | `null` | `{"coordinates": "verified_with_adjustment", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:flims` | `notes` | `null` | `["Official tourism and lift information treat Flims as a named accommodation destination with its own feeder lift into the shared LAAX ski area.", "The medium price level remains a product-curated estimate pending a reviewed accommodation sampling policy."]` | `estimated` | no |
| `trust_manifest:stay_destinations:laax` | `field_source_refs` | `{"coordinates": [], "identity_location": [], "price_level": []}` | `{"coordinates": ["https://www.openstreetmap.org/relation/1684097"], "identity_location": ["https://www.flimslaax.com/en/getting-there", "https://www.flimslaax.com/en/holiday-booking/hotels", "https://www.flimslaax.com/en/senda-dil-dragun"], "price_level": []}` | `estimated` | no |
| `trust_manifest:stay_destinations:laax` | `field_statuses` | `{"coordinates": "needs_source", "identity_location": "needs_source", "price_level": "estimated"}` | `{"coordinates": "verified_with_adjustment", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:laax` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Official material identifies Laax as an accommodation destination and distinguishes Laax Dorf from the Murschetg resort district within it.", "The medium price level remains a product-curated estimate pending a reviewed accommodation sampling policy."]` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:laax-ski-snowboard-ticket` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:laax-ski-snowboard-ticket` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:laax-ski-snowboard-ticket` | `external_validity_summary` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `lift_pass_product:laax-ski-snowboard-ticket` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:laax-ski-snowboard-ticket` | `name` | `changed` |  |
| `lift_pass_product:laax-ski-snowboard-ticket` | `pass_accessible_terrain` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `lift_pass_product:laax-ski-snowboard-ticket` | `prices` | `changed` |  |
| `lift_pass_product:laax-ski-snowboard-ticket` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:laax-ski-snowboard-ticket` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:laax-ski-snowboard-ticket` | `validity_scope` | `changed` |  |
| `rental_display_fact:laax-laax-rental` | `lift_distance` | `changed` |  |
| `rental_display_fact:laax-laax-rental` | `name` | `changed` |  |
| `rental_display_fact:laax-laax-rental` | `price_max` | `changed` |  |
| `rental_display_fact:laax-laax-rental` | `price_min` | `changed` |  |
| `rental_display_fact:laax-laax-rental` | `price_range` | `changed` |  |
| `rental_display_fact:laax-laax-rental` | `quality` | `changed` |  |
| `rental_display_fact:laax-laax-rental` | `rental_display_fact_id` | `changed` |  |
| `rental_display_fact:laax-laax-rental` | `stay_base_id` | `not-applicable` | The legacy entity is removed by this curation. |
| `rental_display_fact:laax-laax-rental` | `stay_destination_id` | `changed` |  |
| `rental_display_fact:laax-murschetg-rental` | `lift_distance` | `changed` |  |
| `rental_display_fact:laax-murschetg-rental` | `name` | `changed` |  |
| `rental_display_fact:laax-murschetg-rental` | `price_max` | `changed` |  |
| `rental_display_fact:laax-murschetg-rental` | `price_min` | `changed` |  |
| `rental_display_fact:laax-murschetg-rental` | `price_range` | `changed` |  |
| `rental_display_fact:laax-murschetg-rental` | `quality` | `changed` |  |
| `rental_display_fact:laax-murschetg-rental` | `rental_display_fact_id` | `changed` |  |
| `rental_display_fact:laax-murschetg-rental` | `stay_base_id` | `changed` |  |
| `rental_display_fact:laax-murschetg-rental` | `stay_destination_id` | `changed` |  |
| `ski_area:laax-ski-area` | `base_elevation_m` | `reviewed-no-change` |  |
| `ski_area:laax-ski-area` | `glacier_terrain.availability` | `changed` |  |
| `ski_area:laax-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:laax-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:laax-ski-area` | `marked_freeride_routes.availability` | `changed` |  |
| `ski_area:laax-ski-area` | `marked_freeride_routes.route_count` | `changed` |  |
| `ski_area:laax-ski-area` | `marked_freeride_routes.season_label` | `unresolved` | The official route inventory exposes no unambiguous season label. |
| `ski_area:laax-ski-area` | `name` | `reviewed-no-change` |  |
| `ski_area:laax-ski-area` | `night_skiing.availability` | `changed` |  |
| `ski_area:laax-ski-area` | `night_skiing.season_label` | `changed` |  |
| `ski_area:laax-ski-area` | `official_trail_map.season_label` | `unresolved` | The current official map URL exposes no unambiguous season label. |
| `ski_area:laax-ski-area` | `official_trail_map.url` | `changed` |  |
| `ski_area:laax-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | Official sources confirm blue, red, and black terrain but do not publish a clean kilometre split by difficulty. |
| `ski_area:laax-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | Official sources confirm blue, red, and black terrain but do not publish a clean kilometre split by difficulty. |
| `ski_area:laax-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | Official sources confirm blue, red, and black terrain but do not publish a clean kilometre split by difficulty. |
| `ski_area:laax-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:laax-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:laax-ski-area` | `season_windows` | `changed` |  |
| `ski_area:laax-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:laax-ski-area` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:laax-ski-area` | `ski_day_apres_profile.intensity` | `changed` |  |
| `ski_area:laax-ski-area` | `ski_day_apres_profile.season_label` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area:laax-ski-area` | `snow_park.availability` | `changed` |  |
| `ski_area:laax-ski-area` | `snow_park.park_count` | `changed` |  |
| `ski_area:laax-ski-area` | `snow_park.season_label` | `changed` |  |
| `ski_area:laax-ski-area` | `snowmaking.availability` | `changed` |  |
| `ski_area:laax-ski-area` | `snowmaking.coverage_basis` | `unresolved` | No accepted source in this curation establishes a more specific owner-scoped value. |
| `ski_area:laax-ski-area` | `snowmaking.coverage_pct` | `unresolved` | Official sources confirm snowmaking infrastructure but publish no resort-wide percentage or denominator. |
| `ski_area:laax-ski-area` | `snowmaking.season_label` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area:laax-ski-area` | `summit_elevation_m` | `reviewed-no-change` |  |
| `ski_area:laax-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:laax-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:laax-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area_access:falera-falera--laax-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:falera-falera--laax-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:falera-falera--laax-ski-area` | `duration_minutes` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area_access:falera-falera--laax-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:falera-falera--laax-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:falera-falera--laax-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:falera-falera--laax-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:falera-falera--laax-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:falera-falera--laax-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:falera-falera--laax-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:falera-falera--laax-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:flims-flims--laax-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:flims-flims--laax-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:flims-flims--laax-ski-area` | `duration_minutes` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area_access:flims-flims--laax-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:flims-flims--laax-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:flims-flims--laax-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:flims-flims--laax-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:flims-flims--laax-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:flims-flims--laax-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:flims-flims--laax-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:flims-flims--laax-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `duration_minutes` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area_access:laax-dorf--laax-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:laax-laax--laax-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:laax-laax--laax-ski-area` | `distance_m` | `not-applicable` | The legacy entity is removed by this curation. |
| `ski_area_access:laax-laax--laax-ski-area` | `duration_minutes` | `not-applicable` | The legacy entity is removed by this curation. |
| `ski_area_access:laax-laax--laax-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:laax-laax--laax-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:laax-laax--laax-ski-area` | `nearest_lift_name` | `not-applicable` | The legacy entity is removed by this curation. |
| `ski_area_access:laax-laax--laax-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:laax-laax--laax-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:laax-laax--laax-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:laax-laax--laax-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:laax-laax--laax-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `duration_minutes` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_area_access:laax-murschetg--laax-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `stay_base_id` | `changed` |  |
| `ski_region:laax` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:laax` | `name` | `changed` |  |
| `ski_region:laax` | `parent_ski_region_id` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `ski_region:laax` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:laax` | `source_urls` | `changed` |  |
| `stay_base:falera-falera` | `base_character.development_style` | `changed` |  |
| `stay_base:falera-falera` | `base_character.local_pace` | `changed` |  |
| `stay_base:falera-falera` | `base_type` | `changed` |  |
| `stay_base:falera-falera` | `elevation_m` | `changed` |  |
| `stay_base:falera-falera` | `latitude` | `changed` |  |
| `stay_base:falera-falera` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:falera-falera` | `local_apres_profile.intensity` | `unresolved` | No accepted source in this curation establishes a more specific owner-scoped value. |
| `stay_base:falera-falera` | `local_apres_profile.season_label` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `stay_base:falera-falera` | `longitude` | `changed` |  |
| `stay_base:falera-falera` | `name` | `changed` |  |
| `stay_base:falera-falera` | `price_max` | `changed` |  |
| `stay_base:falera-falera` | `price_min` | `changed` |  |
| `stay_base:falera-falera` | `price_range` | `changed` |  |
| `stay_base:falera-falera` | `quality` | `changed` |  |
| `stay_base:falera-falera` | `regional_data_ids` | `changed` |  |
| `stay_base:falera-falera` | `stay_base_id` | `changed` |  |
| `stay_base:falera-falera` | `stay_destination_id` | `changed` |  |
| `stay_base:flims-flims` | `base_character.development_style` | `changed` |  |
| `stay_base:flims-flims` | `base_character.local_pace` | `changed` |  |
| `stay_base:flims-flims` | `base_type` | `changed` |  |
| `stay_base:flims-flims` | `elevation_m` | `changed` |  |
| `stay_base:flims-flims` | `latitude` | `changed` |  |
| `stay_base:flims-flims` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:flims-flims` | `local_apres_profile.intensity` | `unresolved` | No accepted source in this curation establishes a more specific owner-scoped value. |
| `stay_base:flims-flims` | `local_apres_profile.season_label` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `stay_base:flims-flims` | `longitude` | `changed` |  |
| `stay_base:flims-flims` | `name` | `changed` |  |
| `stay_base:flims-flims` | `price_max` | `changed` |  |
| `stay_base:flims-flims` | `price_min` | `changed` |  |
| `stay_base:flims-flims` | `price_range` | `changed` |  |
| `stay_base:flims-flims` | `quality` | `changed` |  |
| `stay_base:flims-flims` | `regional_data_ids` | `changed` |  |
| `stay_base:flims-flims` | `stay_base_id` | `changed` |  |
| `stay_base:flims-flims` | `stay_destination_id` | `changed` |  |
| `stay_base:laax-dorf` | `base_character.development_style` | `changed` |  |
| `stay_base:laax-dorf` | `base_character.local_pace` | `changed` |  |
| `stay_base:laax-dorf` | `base_type` | `changed` |  |
| `stay_base:laax-dorf` | `elevation_m` | `changed` |  |
| `stay_base:laax-dorf` | `latitude` | `changed` |  |
| `stay_base:laax-dorf` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:laax-dorf` | `local_apres_profile.intensity` | `unresolved` | No accepted source in this curation establishes a more specific owner-scoped value. |
| `stay_base:laax-dorf` | `local_apres_profile.season_label` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `stay_base:laax-dorf` | `longitude` | `changed` |  |
| `stay_base:laax-dorf` | `name` | `changed` |  |
| `stay_base:laax-dorf` | `price_max` | `changed` |  |
| `stay_base:laax-dorf` | `price_min` | `changed` |  |
| `stay_base:laax-dorf` | `price_range` | `changed` |  |
| `stay_base:laax-dorf` | `quality` | `changed` |  |
| `stay_base:laax-dorf` | `regional_data_ids` | `changed` |  |
| `stay_base:laax-dorf` | `stay_base_id` | `changed` |  |
| `stay_base:laax-dorf` | `stay_destination_id` | `changed` |  |
| `stay_base:laax-laax` | `base_character.development_style` | `changed` |  |
| `stay_base:laax-laax` | `base_character.local_pace` | `changed` |  |
| `stay_base:laax-laax` | `base_type` | `not-applicable` | The legacy entity is removed by this curation. |
| `stay_base:laax-laax` | `elevation_m` | `not-applicable` | The legacy entity is removed by this curation. |
| `stay_base:laax-laax` | `latitude` | `not-applicable` | The legacy entity is removed by this curation. |
| `stay_base:laax-laax` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:laax-laax` | `local_apres_profile.intensity` | `not-applicable` | The legacy entity is removed by this curation. |
| `stay_base:laax-laax` | `local_apres_profile.season_label` | `not-applicable` | The legacy entity is removed by this curation. |
| `stay_base:laax-laax` | `longitude` | `not-applicable` | The legacy entity is removed by this curation. |
| `stay_base:laax-laax` | `name` | `changed` |  |
| `stay_base:laax-laax` | `price_max` | `changed` |  |
| `stay_base:laax-laax` | `price_min` | `changed` |  |
| `stay_base:laax-laax` | `price_range` | `changed` |  |
| `stay_base:laax-laax` | `quality` | `changed` |  |
| `stay_base:laax-laax` | `regional_data_ids` | `changed` |  |
| `stay_base:laax-laax` | `stay_base_id` | `changed` |  |
| `stay_base:laax-laax` | `stay_destination_id` | `changed` |  |
| `stay_base:laax-murschetg` | `base_character.development_style` | `changed` |  |
| `stay_base:laax-murschetg` | `base_character.local_pace` | `changed` |  |
| `stay_base:laax-murschetg` | `base_type` | `changed` |  |
| `stay_base:laax-murschetg` | `elevation_m` | `changed` |  |
| `stay_base:laax-murschetg` | `latitude` | `changed` |  |
| `stay_base:laax-murschetg` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:laax-murschetg` | `local_apres_profile.intensity` | `changed` |  |
| `stay_base:laax-murschetg` | `local_apres_profile.season_label` | `not-applicable` | Optional field is not applicable to the modeled owner or product. |
| `stay_base:laax-murschetg` | `longitude` | `changed` |  |
| `stay_base:laax-murschetg` | `name` | `changed` |  |
| `stay_base:laax-murschetg` | `price_max` | `changed` |  |
| `stay_base:laax-murschetg` | `price_min` | `changed` |  |
| `stay_base:laax-murschetg` | `price_range` | `changed` |  |
| `stay_base:laax-murschetg` | `quality` | `changed` |  |
| `stay_base:laax-murschetg` | `regional_data_ids` | `changed` |  |
| `stay_base:laax-murschetg` | `stay_base_id` | `changed` |  |
| `stay_base:laax-murschetg` | `stay_destination_id` | `changed` |  |
| `stay_destination:falera` | `country` | `changed` |  |
| `stay_destination:falera` | `latitude` | `changed` |  |
| `stay_destination:falera` | `longitude` | `changed` |  |
| `stay_destination:falera` | `name` | `changed` |  |
| `stay_destination:falera` | `price_level` | `changed` |  |
| `stay_destination:falera` | `region` | `changed` |  |
| `stay_destination:falera` | `regional_data_ids` | `changed` |  |
| `stay_destination:falera` | `stay_destination_id` | `changed` |  |
| `stay_destination:falera` | `trip_market_region_id` | `changed` |  |
| `stay_destination:flims` | `country` | `changed` |  |
| `stay_destination:flims` | `latitude` | `changed` |  |
| `stay_destination:flims` | `longitude` | `changed` |  |
| `stay_destination:flims` | `name` | `changed` |  |
| `stay_destination:flims` | `price_level` | `changed` |  |
| `stay_destination:flims` | `region` | `changed` |  |
| `stay_destination:flims` | `regional_data_ids` | `changed` |  |
| `stay_destination:flims` | `stay_destination_id` | `changed` |  |
| `stay_destination:flims` | `trip_market_region_id` | `changed` |  |
| `stay_destination:laax` | `country` | `reviewed-no-change` |  |
| `stay_destination:laax` | `latitude` | `changed` |  |
| `stay_destination:laax` | `longitude` | `changed` |  |
| `stay_destination:laax` | `name` | `reviewed-no-change` |  |
| `stay_destination:laax` | `price_level` | `reviewed-no-change` |  |
| `stay_destination:laax` | `region` | `reviewed-no-change` |  |
| `stay_destination:laax` | `regional_data_ids` | `changed` |  |
| `stay_destination:laax` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:laax` | `trip_market_region_id` | `reviewed-no-change` |  |
| `trust_manifest:lift_pass_products:laax-ski-snowboard-ticket` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:laax-ski-snowboard-ticket` | `field_source_refs` | `changed` |  |
| `trust_manifest:lift_pass_products:laax-ski-snowboard-ticket` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:laax-ski-snowboard-ticket` | `notes` | `changed` |  |
| `trust_manifest:rental_display_facts:laax-laax-rental` | `display_name` | `changed` |  |
| `trust_manifest:rental_display_facts:laax-laax-rental` | `field_source_refs` | `changed` |  |
| `trust_manifest:rental_display_facts:laax-laax-rental` | `field_statuses` | `changed` |  |
| `trust_manifest:rental_display_facts:laax-laax-rental` | `notes` | `changed` |  |
| `trust_manifest:rental_display_facts:laax-murschetg-rental` | `display_name` | `changed` |  |
| `trust_manifest:rental_display_facts:laax-murschetg-rental` | `field_source_refs` | `changed` |  |
| `trust_manifest:rental_display_facts:laax-murschetg-rental` | `field_statuses` | `changed` |  |
| `trust_manifest:rental_display_facts:laax-murschetg-rental` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:falera-falera--laax-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:falera-falera--laax-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:falera-falera--laax-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:falera-falera--laax-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:flims-flims--laax-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:flims-flims--laax-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:flims-flims--laax-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:flims-flims--laax-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:laax-dorf--laax-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:laax-dorf--laax-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:laax-dorf--laax-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:laax-dorf--laax-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:laax-laax--laax-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:laax-laax--laax-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:laax-laax--laax-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:laax-laax--laax-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:laax-murschetg--laax-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:laax-murschetg--laax-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:laax-murschetg--laax-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:laax-murschetg--laax-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:laax-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:laax-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:laax-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:laax-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_regions:laax` | `display_name` | `changed` |  |
| `trust_manifest:ski_regions:laax` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_regions:laax` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_regions:laax` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:falera-falera` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:falera-falera` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:falera-falera` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:falera-falera` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:flims-flims` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:flims-flims` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:flims-flims` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:flims-flims` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:laax-dorf` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:laax-dorf` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:laax-dorf` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:laax-dorf` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:laax-laax` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:laax-laax` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:laax-laax` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:laax-laax` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:laax-murschetg` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:laax-murschetg` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:laax-murschetg` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:laax-murschetg` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:falera` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:falera` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:falera` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:falera` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:flims` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:flims` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:flims` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:flims` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:laax` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:stay_destinations:laax` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:laax` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:laax` | `notes` | `changed` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:laax-ski-snowboard-ticket` | `available_from_stay_destination_ids` | [Official LAAX tickets page](https://www.laax.com/en/tickets) | `["falera", "flims", "laax"]` | The cited source supports the reviewed lift_pass_product value for available_from_stay_destination_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `lift_pass_product:laax-ski-snowboard-ticket` | `default_for_stay_destination_ids` | [Official LAAX tickets page](https://www.laax.com/en/tickets) | `["falera", "flims", "laax"]` | The cited source supports the reviewed lift_pass_product value for default_for_stay_destination_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `lift_pass_product:laax-ski-snowboard-ticket` | `lift_pass_product_id` | [Official LAAX tickets page](https://www.laax.com/en/tickets) | `"laax-ski-snowboard-ticket"` | The cited source supports the reviewed lift_pass_product value for lift_pass_product_id. |  |
| `lift_pass_product:laax-ski-snowboard-ticket` | `name` | [Official LAAX tickets page](https://www.laax.com/en/tickets) | `"LAAX ski and snowboard ticket"` | The cited source supports the reviewed lift_pass_product value for name. |  |
| `lift_pass_product:laax-ski-snowboard-ticket` | `prices` | [Official LAAX tickets page](https://www.laax.com/en/tickets) | `[{"amount": null, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "unknown", "season_label": "Winter 2025/26 dynamic day and multi-day tickets", "source_url": "https://www.laax.com/en/tickets"}]` | The cited source supports the reviewed lift_pass_product value for prices. | The cited source is normalized into the catalog's typed owner and field shape. |
| `lift_pass_product:laax-ski-snowboard-ticket` | `terrain_domain_ids` | [Official LAAX tickets page](https://www.laax.com/en/tickets) | `[]` | The cited source supports the reviewed lift_pass_product value for terrain_domain_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `lift_pass_product:laax-ski-snowboard-ticket` | `valid_ski_area_ids` | [Official LAAX tickets page](https://www.laax.com/en/tickets) | `["laax-ski-area"]` | The cited source supports the reviewed lift_pass_product value for valid_ski_area_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `lift_pass_product:laax-ski-snowboard-ticket` | `validity_scope` | [Official LAAX tickets page](https://www.laax.com/en/tickets) | `"single_ski_area"` | The cited source supports the reviewed lift_pass_product value for validity_scope. |  |
| `ski_area:laax-ski-area` | `glacier_terrain.availability` | [Official LAAX ski and snowboard page](https://www.laax.com/en/ski-snowboard) | `"available"` | The cited source supports the reviewed ski_area value for glacier_terrain.availability. |  |
| `ski_area:laax-ski-area` | `marked_freeride_routes.availability` | [Official LAAX freeride page](https://www.laax.com/en/freeride) | `"available"` | The cited source supports the reviewed ski_area value for marked_freeride_routes.availability. |  |
| `ski_area:laax-ski-area` | `marked_freeride_routes.route_count` | [Official LAAX freeride page](https://www.laax.com/en/freeride) | `12` | The cited source supports the reviewed ski_area value for marked_freeride_routes.route_count. |  |
| `ski_area:laax-ski-area` | `night_skiing.availability` | [Official Flims Laax ski and snowboard page](https://www.flimslaax.com/en/winter/ski-resort/ski-snowboard) | `"available"` | The cited source supports the reviewed ski_area value for night_skiing.availability. |  |
| `ski_area:laax-ski-area` | `night_skiing.season_label` | [Official Flims Laax ski and snowboard page](https://www.flimslaax.com/en/winter/ski-resort/ski-snowboard) | `"2025/26"` | The cited source supports the reviewed ski_area value for night_skiing.season_label. |  |
| `ski_area:laax-ski-area` | `official_trail_map.url` | [Official LAAX winter slope map](https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf) | `"https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf"` | The cited source supports the reviewed ski_area value for official_trail_map.url. |  |
| `ski_area:laax-ski-area` | `season_start_month` | [Official LAAX opening hours](https://www.laax.com/en/opening-hours) | `11` | The cited source supports the reviewed ski_area value for season_start_month. |  |
| `ski_area:laax-ski-area` | `season_windows` | [Official LAAX opening hours](https://www.laax.com/en/opening-hours) | `[{"end_date": "2026-04-12", "season_label": "Winter 2025/26", "start_date": "2025-11-29", "status": "planned"}]` | The cited source supports the reviewed ski_area value for season_windows. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area:laax-ski-area` | `ski_day_apres_profile.availability` | [Official LAAX food and drinks directory](https://www.laax.com/en/food-drinks) | `"available"` | The cited source supports the reviewed ski_area value for ski_day_apres_profile.availability. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area:laax-ski-area` | `ski_day_apres_profile.intensity` | [Official LAAX food and drinks directory](https://www.laax.com/en/food-drinks) | `"lively"` | The cited source supports the reviewed ski_area value for ski_day_apres_profile.intensity. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area:laax-ski-area` | `snow_park.availability` | [Official LAAX freestyle page](https://www.laax.com/en/freestyle) | `"available"` | The cited source supports the reviewed ski_area value for snow_park.availability. |  |
| `ski_area:laax-ski-area` | `snow_park.park_count` | [Official LAAX freestyle page](https://www.laax.com/en/freestyle) | `5` | The cited source supports the reviewed ski_area value for snow_park.park_count. |  |
| `ski_area:laax-ski-area` | `snow_park.season_label` | [Official LAAX freestyle page](https://www.laax.com/en/freestyle) | `"2025/26"` | The cited source supports the reviewed ski_area value for snow_park.season_label. |  |
| `ski_area:laax-ski-area` | `snowmaking.availability` | [Official LAAX behind-the-scenes page](https://www.laax.com/en/meeting/activity-hinter-den-kulissen-von-laax) | `"available"` | The cited source supports the reviewed ski_area value for snowmaking.availability. |  |
| `ski_area:laax-ski-area` | `supported_skill_levels` | [Official LAAX ski and snowboard page](https://www.laax.com/en/ski-snowboard) | `["beginner", "intermediate", "advanced"]` | The cited source supports the reviewed ski_area value for supported_skill_levels. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area:laax-ski-area` | `total_lift_count` | [Official LAAX ski and snowboard page](https://www.laax.com/en/ski-snowboard) | `30` | The cited source supports the reviewed ski_area value for total_lift_count. |  |
| `ski_area:laax-ski-area` | `total_piste_km` | [Official LAAX ski and snowboard page](https://www.laax.com/en/ski-snowboard) | `216.0` | The cited source supports the reviewed ski_area value for total_piste_km. |  |
| `ski_area_access:falera-falera--laax-ski-area` | `access_mode` | [Official destination access information](https://www.laax.com/en/opening-hours) | `"walk"` | The cited source supports the reviewed ski_area_access value for access_mode. |  |
| `ski_area_access:falera-falera--laax-ski-area` | `distance_m` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/330181586) | `358` | The cited source supports the reviewed ski_area_access value for distance_m. | Rounded Haversine distance from the two cited OSM endpoints; not a routed walking distance. |
| `ski_area_access:falera-falera--laax-ski-area` | `is_direct` | [Official destination access information](https://www.laax.com/en/opening-hours) | `true` | The cited source supports the reviewed ski_area_access value for is_direct. |  |
| `ski_area_access:falera-falera--laax-ski-area` | `lift_distance` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/330181586) | `"near"` | The cited source supports the reviewed ski_area_access value for lift_distance. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:falera-falera--laax-ski-area` | `nearest_lift_name` | [Official destination access information](https://www.laax.com/en/opening-hours) | `"Falera-Curnius chairlift"` | The cited source supports the reviewed ski_area_access value for nearest_lift_name. |  |
| `ski_area_access:falera-falera--laax-ski-area` | `regional_data_ids` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/330181586) | `{"nearest_lift_osm_node_id": "330181586", "stay_base_osm_relation_id": "1684074"}` | The cited source supports the reviewed ski_area_access value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:falera-falera--laax-ski-area` | `ski_area_access_id` | [Official destination access information](https://www.laax.com/en/opening-hours) | `"falera-falera--laax-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_access_id. |  |
| `ski_area_access:falera-falera--laax-ski-area` | `ski_area_id` | [Official destination access information](https://www.laax.com/en/opening-hours) | `"laax-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_id. |  |
| `ski_area_access:falera-falera--laax-ski-area` | `source_urls` | [Official destination access information](https://www.laax.com/en/opening-hours) | `["https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/330181586", "https://www.openstreetmap.org/relation/1684074"]` | The cited source supports the reviewed ski_area_access value for source_urls. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:falera-falera--laax-ski-area` | `stay_base_id` | [Official destination access information](https://www.laax.com/en/opening-hours) | `"falera-falera"` | The cited source supports the reviewed ski_area_access value for stay_base_id. |  |
| `ski_area_access:flims-flims--laax-ski-area` | `access_mode` | [Official destination access information](https://www.laax.com/en/opening-hours) | `"walk"` | The cited source supports the reviewed ski_area_access value for access_mode. |  |
| `ski_area_access:flims-flims--laax-ski-area` | `distance_m` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/10681585981) | `559` | The cited source supports the reviewed ski_area_access value for distance_m. | Rounded Haversine distance from the two cited OSM endpoints; not a routed walking distance. |
| `ski_area_access:flims-flims--laax-ski-area` | `is_direct` | [Official destination access information](https://www.laax.com/en/opening-hours) | `false` | The cited source supports the reviewed ski_area_access value for is_direct. |  |
| `ski_area_access:flims-flims--laax-ski-area` | `lift_distance` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/10681585981) | `"medium"` | The cited source supports the reviewed ski_area_access value for lift_distance. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:flims-flims--laax-ski-area` | `nearest_lift_name` | [Official destination access information](https://www.laax.com/en/opening-hours) | `"FlemXpress Flims valley station"` | The cited source supports the reviewed ski_area_access value for nearest_lift_name. |  |
| `ski_area_access:flims-flims--laax-ski-area` | `regional_data_ids` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/10681585981) | `{"nearest_lift_osm_node_id": "10681585981", "stay_base_osm_node_id": "33589791"}` | The cited source supports the reviewed ski_area_access value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:flims-flims--laax-ski-area` | `ski_area_access_id` | [Official destination access information](https://www.laax.com/en/opening-hours) | `"flims-flims--laax-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_access_id. |  |
| `ski_area_access:flims-flims--laax-ski-area` | `ski_area_id` | [Official destination access information](https://www.laax.com/en/opening-hours) | `"laax-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_id. |  |
| `ski_area_access:flims-flims--laax-ski-area` | `source_urls` | [Official destination access information](https://www.laax.com/en/opening-hours) | `["https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/10681585981", "https://www.openstreetmap.org/node/33589791"]` | The cited source supports the reviewed ski_area_access value for source_urls. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:flims-flims--laax-ski-area` | `stay_base_id` | [Official destination access information](https://www.laax.com/en/opening-hours) | `"flims-flims"` | The cited source supports the reviewed ski_area_access value for stay_base_id. |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `access_mode` | [Official destination access information](https://www.flimslaax.com/en/transport) | `"ski_bus"` | The cited source supports the reviewed ski_area_access value for access_mode. |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `distance_m` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/244501524) | `1578` | The cited source supports the reviewed ski_area_access value for distance_m. | Rounded Haversine distance from the two cited OSM endpoints; not a routed walking distance. |
| `ski_area_access:laax-dorf--laax-ski-area` | `is_direct` | [Official destination access information](https://www.flimslaax.com/en/transport) | `false` | The cited source supports the reviewed ski_area_access value for is_direct. |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `lift_distance` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/244501524) | `"medium"` | The cited source supports the reviewed ski_area_access value for lift_distance. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:laax-dorf--laax-ski-area` | `nearest_lift_name` | [Official destination access information](https://www.flimslaax.com/en/transport) | `"Laax Murschetg valley station"` | The cited source supports the reviewed ski_area_access value for nearest_lift_name. |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `regional_data_ids` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/244501524) | `{"nearest_lift_osm_node_id": "244501524", "stay_base_osm_relation_id": "1684097"}` | The cited source supports the reviewed ski_area_access value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:laax-dorf--laax-ski-area` | `ski_area_access_id` | [Official destination access information](https://www.flimslaax.com/en/transport) | `"laax-dorf--laax-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_access_id. |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `ski_area_id` | [Official destination access information](https://www.flimslaax.com/en/transport) | `"laax-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_id. |  |
| `ski_area_access:laax-dorf--laax-ski-area` | `source_urls` | [Official destination access information](https://www.flimslaax.com/en/transport) | `["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.flimslaax.com/en/transport", "https://www.openstreetmap.org/node/244501524", "https://www.openstreetmap.org/relation/1684097"]` | The cited source supports the reviewed ski_area_access value for source_urls. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:laax-dorf--laax-ski-area` | `stay_base_id` | [Official destination access information](https://www.flimslaax.com/en/transport) | `"laax-dorf"` | The cited source supports the reviewed ski_area_access value for stay_base_id. |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `access_mode` | [Official destination access information](https://www.flimslaax.com/en/senda-dil-dragun) | `"walk"` | The cited source supports the reviewed ski_area_access value for access_mode. |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `distance_m` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/244501524) | `127` | The cited source supports the reviewed ski_area_access value for distance_m. | Rounded Haversine distance from the two cited OSM endpoints; not a routed walking distance. |
| `ski_area_access:laax-murschetg--laax-ski-area` | `is_direct` | [Official destination access information](https://www.flimslaax.com/en/senda-dil-dragun) | `true` | The cited source supports the reviewed ski_area_access value for is_direct. |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `lift_distance` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/244501524) | `"near"` | The cited source supports the reviewed ski_area_access value for lift_distance. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:laax-murschetg--laax-ski-area` | `nearest_lift_name` | [Official destination access information](https://www.flimslaax.com/en/senda-dil-dragun) | `"Laax Murschetg valley station"` | The cited source supports the reviewed ski_area_access value for nearest_lift_name. |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `regional_data_ids` | [OpenStreetMap feeder-station geometry](https://www.openstreetmap.org/node/244501524) | `{"nearest_lift_osm_node_id": "244501524", "stay_base_osm_node_id": "244479992"}` | The cited source supports the reviewed ski_area_access value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:laax-murschetg--laax-ski-area` | `ski_area_access_id` | [Official destination access information](https://www.flimslaax.com/en/senda-dil-dragun) | `"laax-murschetg--laax-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_access_id. |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `ski_area_id` | [Official destination access information](https://www.flimslaax.com/en/senda-dil-dragun) | `"laax-ski-area"` | The cited source supports the reviewed ski_area_access value for ski_area_id. |  |
| `ski_area_access:laax-murschetg--laax-ski-area` | `source_urls` | [Official destination access information](https://www.flimslaax.com/en/senda-dil-dragun) | `["https://www.flimslaax.com/en/senda-dil-dragun", "https://www.laax.com/en/opening-hours", "https://www.openstreetmap.org/node/244479992", "https://www.openstreetmap.org/node/244501524"]` | The cited source supports the reviewed ski_area_access value for source_urls. | The cited source is normalized into the catalog's typed owner and field shape. |
| `ski_area_access:laax-murschetg--laax-ski-area` | `stay_base_id` | [Official destination access information](https://www.flimslaax.com/en/senda-dil-dragun) | `"laax-murschetg"` | The cited source supports the reviewed ski_area_access value for stay_base_id. |  |
| `ski_region:laax` | `name` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"Flims Laax Falera"` | The cited source supports the reviewed ski_region value for name. |  |
| `ski_region:laax` | `source_urls` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `["https://www.flimslaax.com/en/getting-there", "https://www.flimslaax.com/en/winter/ski-resort/ski-snowboard"]` | The cited source supports the reviewed ski_region value for source_urls. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_base:falera-falera` | `base_character.development_style` | [Official Falera municipal portrait](https://www.falera.net/gemeinde/portrait/) | `"traditional"` | The municipality says Falera remained a farming village despite tourism and protects its historical settlement pattern. | Predominantly inherited village form is normalized to development_style=traditional. |
| `stay_base:falera-falera` | `base_type` | [Official destination and feeder information](https://www.laax.com/en/opening-hours) | `"village"` | The cited source supports the reviewed stay_base value for base_type. |  |
| `stay_base:falera-falera` | `elevation_m` | [Official LAAX winter slope map](https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf) | `1220` | The cited source supports the reviewed stay_base value for elevation_m. |  |
| `stay_base:falera-falera` | `latitude` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/relation/1684074) | `46.8007977` | The cited source supports the reviewed stay_base value for latitude. |  |
| `stay_base:falera-falera` | `longitude` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/relation/1684074) | `9.2321371` | The cited source supports the reviewed stay_base value for longitude. |  |
| `stay_base:falera-falera` | `name` | [Official destination and feeder information](https://www.laax.com/en/opening-hours) | `"Falera"` | The cited source supports the reviewed stay_base value for name. |  |
| `stay_base:falera-falera` | `regional_data_ids` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/relation/1684074) | `{"osm_relation_id": "1684074"}` | The cited source supports the reviewed stay_base value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_base:falera-falera` | `stay_base_id` | [Official destination and feeder information](https://www.laax.com/en/opening-hours) | `"falera-falera"` | The cited source supports the reviewed stay_base value for stay_base_id. |  |
| `stay_base:falera-falera` | `stay_destination_id` | [Official destination and feeder information](https://www.laax.com/en/opening-hours) | `"falera"` | The cited source supports the reviewed stay_base value for stay_destination_id. |  |
| `stay_base:flims-flims` | `base_character.development_style` | [Official Flims municipal profile](https://www.gemeindeflims.ch/geschichtefs) | `"mixed"` | The municipality explicitly presents Flims as a modern holiday resort with tradition and documents substantial resort-era development. | The inherited settlement plus substantial resort-era development is normalized to development_style=mixed. |
| `stay_base:flims-flims` | `base_type` | [Official destination and feeder information](https://www.laax.com/en/opening-hours) | `"village"` | The cited source supports the reviewed stay_base value for base_type. |  |
| `stay_base:flims-flims` | `elevation_m` | [Official LAAX winter slope map](https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf) | `1100` | The cited source supports the reviewed stay_base value for elevation_m. |  |
| `stay_base:flims-flims` | `latitude` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/node/33589791) | `46.8367698` | The cited source supports the reviewed stay_base value for latitude. |  |
| `stay_base:flims-flims` | `longitude` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/node/33589791) | `9.2876705` | The cited source supports the reviewed stay_base value for longitude. |  |
| `stay_base:flims-flims` | `name` | [Official destination and feeder information](https://www.laax.com/en/opening-hours) | `"Flims"` | The cited source supports the reviewed stay_base value for name. |  |
| `stay_base:flims-flims` | `regional_data_ids` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/node/33589791) | `{"osm_node_id": "33589791"}` | The cited source supports the reviewed stay_base value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_base:flims-flims` | `stay_base_id` | [Official destination and feeder information](https://www.laax.com/en/opening-hours) | `"flims-flims"` | The cited source supports the reviewed stay_base value for stay_base_id. |  |
| `stay_base:flims-flims` | `stay_destination_id` | [Official destination and feeder information](https://www.laax.com/en/opening-hours) | `"flims"` | The cited source supports the reviewed stay_base value for stay_destination_id. |  |
| `stay_base:laax-dorf` | `base_character.development_style` | [Official Laax municipal planning report](https://www.laax-gr.ch/wp-content/uploads/2022/08/PMB_Genehmigung.pdf) | `"traditional"` | Municipal planning identifies Laax Dorf as a historically evolved settlement with a preserved historical core; planned resort development is modeled separately in Murschetg. | The inherited village core, separated from Murschetg's planned resort development, is normalized to development_style=traditional. |
| `stay_base:laax-dorf` | `base_type` | [Official destination and feeder information](https://www.flimslaax.com/en/senda-dil-dragun) | `"village"` | The cited source supports the reviewed stay_base value for base_type. |  |
| `stay_base:laax-dorf` | `elevation_m` | [Official LAAX winter slope map](https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf) | `1020` | The cited source supports the reviewed stay_base value for elevation_m. |  |
| `stay_base:laax-dorf` | `latitude` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/relation/1684097) | `46.806412` | The cited source supports the reviewed stay_base value for latitude. |  |
| `stay_base:laax-dorf` | `longitude` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/relation/1684097) | `9.2581267` | The cited source supports the reviewed stay_base value for longitude. |  |
| `stay_base:laax-dorf` | `name` | [Official destination and feeder information](https://www.flimslaax.com/en/senda-dil-dragun) | `"Laax Dorf"` | The cited source supports the reviewed stay_base value for name. |  |
| `stay_base:laax-dorf` | `regional_data_ids` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/relation/1684097) | `{"osm_relation_id": "1684097"}` | The cited source supports the reviewed stay_base value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_base:laax-dorf` | `stay_base_id` | [Official destination and feeder information](https://www.flimslaax.com/en/senda-dil-dragun) | `"laax-dorf"` | The cited source supports the reviewed stay_base value for stay_base_id. |  |
| `stay_base:laax-dorf` | `stay_destination_id` | [Official destination and feeder information](https://www.flimslaax.com/en/senda-dil-dragun) | `"laax"` | The cited source supports the reviewed stay_base value for stay_destination_id. |  |
| `stay_base:laax-murschetg` | `base_character.development_style` | [Official Laax Murschetg and Laax village page](https://www.flimslaax.com/en/senda-dil-dragun) | `"planned_resort"` | Official destination material identifies the contemporary rocksresort lift-base district separately from Laax village. | The contemporary lift-base district is normalized to development_style=planned_resort. |
| `stay_base:laax-murschetg` | `base_character.local_pace` | [Official Laax Murschetg and Laax village page](https://www.flimslaax.com/en/senda-dil-dragun) | `"lively"` | The cited source supports the reviewed stay_base value for base_character.local_pace. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_base:laax-murschetg` | `base_type` | [Official destination and feeder information](https://www.flimslaax.com/en/senda-dil-dragun) | `"resort_station"` | The cited source supports the reviewed stay_base value for base_type. |  |
| `stay_base:laax-murschetg` | `elevation_m` | [Official LAAX winter slope map](https://cdn.sanity.io/files/y4s4a5hi/production/2e2d294de0e704791655a592efa2c2ba99ba3993.pdf) | `1100` | The cited source supports the reviewed stay_base value for elevation_m. |  |
| `stay_base:laax-murschetg` | `latitude` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/node/244479992) | `46.8193045` | The cited source supports the reviewed stay_base value for latitude. |  |
| `stay_base:laax-murschetg` | `local_apres_profile.availability` | [Official LAAX food and drinks directory](https://www.laax.com/en/food-drinks) | `"available"` | The cited source supports the reviewed stay_base value for local_apres_profile.availability. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_base:laax-murschetg` | `local_apres_profile.intensity` | [Official LAAX food and drinks directory](https://www.laax.com/en/food-drinks) | `"lively"` | The cited source supports the reviewed stay_base value for local_apres_profile.intensity. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_base:laax-murschetg` | `longitude` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/node/244479992) | `9.2643581` | The cited source supports the reviewed stay_base value for longitude. |  |
| `stay_base:laax-murschetg` | `name` | [Official destination and feeder information](https://www.flimslaax.com/en/senda-dil-dragun) | `"Laax Murschetg"` | The cited source supports the reviewed stay_base value for name. |  |
| `stay_base:laax-murschetg` | `regional_data_ids` | [OpenStreetMap settlement geometry](https://www.openstreetmap.org/node/244479992) | `{"osm_node_id": "244479992"}` | The cited source supports the reviewed stay_base value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_base:laax-murschetg` | `stay_base_id` | [Official destination and feeder information](https://www.flimslaax.com/en/senda-dil-dragun) | `"laax-murschetg"` | The cited source supports the reviewed stay_base value for stay_base_id. |  |
| `stay_base:laax-murschetg` | `stay_destination_id` | [Official destination and feeder information](https://www.flimslaax.com/en/senda-dil-dragun) | `"laax"` | The cited source supports the reviewed stay_base value for stay_destination_id. |  |
| `stay_destination:falera` | `country` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"Switzerland"` | The cited source supports the reviewed stay_destination value for country. |  |
| `stay_destination:falera` | `latitude` | [OpenStreetMap Falera relation](https://www.openstreetmap.org/relation/1684074) | `46.8007977` | The cited source supports the reviewed stay_destination value for latitude. |  |
| `stay_destination:falera` | `longitude` | [OpenStreetMap Falera relation](https://www.openstreetmap.org/relation/1684074) | `9.2321371` | The cited source supports the reviewed stay_destination value for longitude. |  |
| `stay_destination:falera` | `name` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"Falera"` | The cited source supports the reviewed stay_destination value for name. |  |
| `stay_destination:falera` | `region` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"Graubunden"` | The cited source supports the reviewed stay_destination value for region. |  |
| `stay_destination:falera` | `regional_data_ids` | [OpenStreetMap Falera relation](https://www.openstreetmap.org/relation/1684074) | `{"osm_relation_id": "1684074"}` | The cited source supports the reviewed stay_destination value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_destination:falera` | `stay_destination_id` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"falera"` | The cited source supports the reviewed stay_destination value for stay_destination_id. |  |
| `stay_destination:falera` | `trip_market_region_id` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"laax"` | The cited source supports the reviewed stay_destination value for trip_market_region_id. |  |
| `stay_destination:flims` | `country` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"Switzerland"` | The cited source supports the reviewed stay_destination value for country. |  |
| `stay_destination:flims` | `latitude` | [OpenStreetMap Flims relation](https://www.openstreetmap.org/relation/1684080) | `46.8332439` | The cited source supports the reviewed stay_destination value for latitude. |  |
| `stay_destination:flims` | `longitude` | [OpenStreetMap Flims relation](https://www.openstreetmap.org/relation/1684080) | `9.2834557` | The cited source supports the reviewed stay_destination value for longitude. |  |
| `stay_destination:flims` | `name` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"Flims"` | The cited source supports the reviewed stay_destination value for name. |  |
| `stay_destination:flims` | `region` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"Graubunden"` | The cited source supports the reviewed stay_destination value for region. |  |
| `stay_destination:flims` | `regional_data_ids` | [OpenStreetMap Flims relation](https://www.openstreetmap.org/relation/1684080) | `{"osm_relation_id": "1684080"}` | The cited source supports the reviewed stay_destination value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_destination:flims` | `stay_destination_id` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"flims"` | The cited source supports the reviewed stay_destination value for stay_destination_id. |  |
| `stay_destination:flims` | `trip_market_region_id` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"laax"` | The cited source supports the reviewed stay_destination value for trip_market_region_id. |  |
| `stay_destination:laax` | `latitude` | [OpenStreetMap Laax relation](https://www.openstreetmap.org/relation/1684097) | `46.806412` | The cited source supports the reviewed stay_destination value for latitude. |  |
| `stay_destination:laax` | `longitude` | [OpenStreetMap Laax relation](https://www.openstreetmap.org/relation/1684097) | `9.2581267` | The cited source supports the reviewed stay_destination value for longitude. |  |
| `stay_destination:laax` | `regional_data_ids` | [OpenStreetMap Laax relation](https://www.openstreetmap.org/relation/1684097) | `{"osm_relation_id": "1684097"}` | The cited source supports the reviewed stay_destination value for regional_data_ids. | The cited source is normalized into the catalog's typed owner and field shape. |
| `stay_destination:laax` | `name` | [Official Flims Laax Falera travel page](https://www.flimslaax.com/en/getting-there) | `"Laax"` | Official destination material treats Laax as one of the three named visitor places in Flims Laax Falera. |  |
| `stay_base:laax-laax` | `stay_base_id` | [Official Laax Murschetg and Laax village page](https://www.flimslaax.com/en/senda-dil-dragun) | `"Laax Dorf and Laax Murschetg"` | Official material distinguishes the two districts, so the legacy blended Laax base is retired. | The source distinction is normalized by replacing the blended record with two explicit stay bases. |
| `ski_area_access:laax-laax--laax-ski-area` | `ski_area_access_id` | [Official Laax Murschetg and Laax village page](https://www.flimslaax.com/en/senda-dil-dragun) | `"Separate Dorf and Murschetg access owners"` | The blended access edge is retired because Laax Dorf and Murschetg have different access modes and distances. | One legacy edge is normalized into two explicit access records. |

## Boundary Decisions

- `falera`: `pass`
- `flims`: `pass`
- `laax`: `pass`

## Ranking Impact

Search and planning can now compare Flims, Laax, and Falera as distinct stay contexts while using the correct base-specific feeder mode and distance, one shared terrain owner, and the published season and terrain facts. No ranking policy or weights are changed.

## Verification

- `UV_PROJECT_ENVIRONMENT=/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv uv run --no-config --no-sync python -m app.data.validate_catalog_curation typed docs/catalog-curation/2026-06-27-laax-full-curation.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output docs/catalog-curation/2026-06-27-laax-full-curation.md`
- `UV_PROJECT_ENVIRONMENT=/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv uv run --no-config --no-sync python -m app.data.validate_catalog_curation reconcile docs/catalog-curation/2026-06-27-laax-full-curation.json --base-catalog-path /tmp/pr21-current-main-catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path /tmp/pr21-current-main-trust.json --current-trust-manifest-path app/data/resort_trust_manifest.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output docs/catalog-curation/2026-06-27-laax-full-curation.md`

## Caveats

- Official sources confirm blue, red, and black terrain but do not publish a clean kilometre split by difficulty, so piste_km_by_difficulty remains unresolved.
- Official LAAX material confirms snowmaking infrastructure but publishes no resort-wide coverage percentage or denominator.
- The official current map and marked-freeride inventory expose no unambiguous season label.
- The exact Winter 2026/27 ski-season schedule was not yet published; the catalog records the complete official Winter 2025/26 operating span rather than projecting dates.
- Winter ticket pricing remains dynamic, so the pass product uses price_kind=unknown instead of an invented fixed price.
- Lodging and rental price and quality fields remain product-curated estimates pending dedicated sampling policies.
- Local pace and recurring local apres remain unresolved for Flims, Falera, and Laax Dorf.
- The legacy ski-area request coordinates are unchanged; this curation does not trigger a weather-history geometry migration.
