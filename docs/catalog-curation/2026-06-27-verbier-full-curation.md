# Verbier Full Static Catalog Curation - 2026-06-27 - normalized model migration

Migrates PR #18 onto the normalized Snowcast catalog. Facts are assigned to explicit regions, stay destinations, stay bases, ski areas, access edges, terrain domains, pass products, and rental facts.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:verbier-4-vallees-pass` | `full` | all canonical fields |
| `rental_display_fact:verbier-mountain-air` | `full` | all canonical fields |
| `ski_area:verbier-ski-area` | `full` | all canonical fields |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `full` | all canonical fields |
| `ski_region:verbier` | `full` | all canonical fields |
| `stay_base:verbier-verbier` | `full` | all canonical fields |
| `stay_destination:verbier` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:verbier-ski-area` | `full` | all canonical fields |
| `trust_manifest:stay_bases:verbier-verbier` | `full` | all canonical fields |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:verbier-4-vallees-pass` | `available_from_stay_destination_ids` | `null` | `["verbier"]` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `default_for_stay_destination_ids` | `null` | `["verbier"]` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `external_validity_summary` | `null` | `"Covers the Verbier sector locally and the wider 4 Vallées network including Bruson, La Tzoumaz, Nendaz, Veysonnaz and Thyon when those links are operating."` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `lift_pass_product_id` | `null` | `"verbier-4-vallees-pass"` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `name` | `null` | `"4 Vallées ski pass"` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `prices` | `null` | `[{"amount": 409.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "from", "season_label": "Winter 2025/26 4 Vallées six-day from price", "source_url": "https://www.verbier.com/ski-passes"}, {"amount": 87.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "from", "season_label": "Winter 2025/26 dynamic day-pass from price", "source_url": "https://www.verbier.com/ski-passes"}]` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `valid_ski_area_ids` | `null` | `["verbier-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `ski_area:verbier-ski-area` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `ski_area:verbier-ski-area` | `supported_skill_levels` | `["intermediate", "advanced"]` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:verbier-ski-area` | `total_lift_count` | `null` | `33` | `verified_with_adjustment` | yes |
| `ski_area:verbier-ski-area` | `total_piste_km` | `null` | `106.0` | `verified_with_adjustment` | yes |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `distance_m` | `null` | `600` | `verified_with_adjustment` | yes |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `nearest_lift_name` | `null` | `"Medran / Place Blanche"` | `verified_with_adjustment` | no |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `source_urls` | `["https://www.bergfex.com/verbier/"]` | `["https://www.bergfex.com/verbier/", "https://www.openstreetmap.org/node/1038335696", "https://www.openstreetmap.org/node/310532759", "https://www.verbier.com/equipment-hire/mountain-air-verbier", "https://www.verbier.com/ski-passes"]` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `base_type` | `null` | `"village"` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `latitude` | `null` | `46.0961` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `longitude` | `null` | `7.2287` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `regional_data_ids` | `{}` | `{"osm_node_id": "310532759", "rental_osm_node_id": "1038335696"}` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `display_name` | `null` | `"4 Vallées ski pass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `field_source_refs` | `null` | `{"coverage": ["https://www.verbier.com/ski-passes"], "identity_scope_availability": ["https://www.verbier.com/ski-passes"], "pass_accessible_terrain": ["https://www.verbier.com/ski-passes"], "prices": ["https://www.verbier.com/ski-passes"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `notes` | `null` | `["PR #18 legacy curation was translated onto normalized catalog ownership and relationships."]` | `estimated` | no |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/verbier/"], "relationship": ["https://www.bergfex.com/verbier/"]}` | `{"access_mode_distance": ["https://www.bergfex.com/verbier/", "https://www.openstreetmap.org/node/1038335696", "https://www.openstreetmap.org/node/310532759", "https://www.verbier.com/equipment-hire/mountain-air-verbier", "https://www.verbier.com/ski-passes"], "relationship": ["https://www.bergfex.com/verbier/", "https://www.openstreetmap.org/node/1038335696", "https://www.openstreetmap.org/node/310532759", "https://www.verbier.com/equipment-hire/mountain-air-verbier", "https://www.verbier.com/ski-passes"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "estimated"}` | `estimated` | no |
| `trust_manifest:ski_areas:verbier-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://verbier4vallees.ch/en/ski-resort", "https://verbier4vallees.ch/en/ski-resort/4-vallees"], "glacier_terrain": [], "identity_coordinates": ["https://verbier4vallees.ch/en/ski-resort", "https://verbier4vallees.ch/en/ski-resort/4-vallees"], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": ["https://verbier4vallees.ch/en/ski-resort", "https://verbier4vallees.ch/en/ski-resort/4-vallees"], "snow_park": [], "snowmaking": [], "terrain_metrics": ["https://verbier4vallees.ch/en/ski-resort", "https://verbier4vallees.ch/en/ski-resort/4-vallees"]}` | `estimated` | no |
| `trust_manifest:ski_areas:verbier-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:stay_bases:verbier-verbier` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `{"base_character": [], "base_type": [], "coordinates": ["https://verbier4vallees.ch/en/ski-resort", "https://www.openstreetmap.org/node/310532759"], "elevation": [], "identity_ownership": ["https://verbier4vallees.ch/en/ski-resort", "https://www.openstreetmap.org/node/310532759"], "local_apres": [], "lodging_price_quality": ["https://verbier4vallees.ch/en/ski-resort", "https://www.openstreetmap.org/node/310532759"]}` | `estimated` | no |
| `trust_manifest:stay_bases:verbier-verbier` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "verified_with_adjustment", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:verbier-4-vallees-pass` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `name` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `pass_accessible_terrain` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `lift_pass_product:verbier-4-vallees-pass` | `prices` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `validity_scope` | `changed` |  |
| `rental_display_fact:verbier-mountain-air` | `lift_distance` | `reviewed-no-change` |  |
| `rental_display_fact:verbier-mountain-air` | `name` | `reviewed-no-change` |  |
| `rental_display_fact:verbier-mountain-air` | `price_max` | `reviewed-no-change` |  |
| `rental_display_fact:verbier-mountain-air` | `price_min` | `reviewed-no-change` |  |
| `rental_display_fact:verbier-mountain-air` | `price_range` | `reviewed-no-change` |  |
| `rental_display_fact:verbier-mountain-air` | `quality` | `reviewed-no-change` |  |
| `rental_display_fact:verbier-mountain-air` | `rental_display_fact_id` | `reviewed-no-change` |  |
| `rental_display_fact:verbier-mountain-air` | `stay_base_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `rental_display_fact:verbier-mountain-air` | `stay_destination_id` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `base_elevation_m` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `glacier_terrain.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `marked_freeride_routes.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `marked_freeride_routes.route_count` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `marked_freeride_routes.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `name` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `night_skiing.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `night_skiing.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `official_trail_map.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `official_trail_map.url` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area:verbier-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area:verbier-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area:verbier-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:verbier-ski-area` | `season_windows` | `unresolved` | Reviewed sources did not resolve a retained structured value. |
| `ski_area:verbier-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `ski_day_apres_profile.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `ski_day_apres_profile.intensity` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `ski_day_apres_profile.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `snow_park.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `snow_park.park_count` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `snow_park.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `snowmaking.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `snowmaking.coverage_basis` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `snowmaking.coverage_pct` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `snowmaking.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:verbier-ski-area` | `summit_elevation_m` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:verbier-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:verbier-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `duration_minutes` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `is_direct` | `reviewed-no-change` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `lift_distance` | `reviewed-no-change` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `regional_data_ids` | `reviewed-no-change` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `ski_area_access_id` | `reviewed-no-change` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `stay_base_id` | `reviewed-no-change` |  |
| `ski_region:verbier` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:verbier` | `name` | `reviewed-no-change` |  |
| `ski_region:verbier` | `parent_ski_region_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `ski_region:verbier` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:verbier` | `source_urls` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `base_character.development_style` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:verbier-verbier` | `base_character.local_pace` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:verbier-verbier` | `base_type` | `changed` |  |
| `stay_base:verbier-verbier` | `elevation_m` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:verbier-verbier` | `latitude` | `changed` |  |
| `stay_base:verbier-verbier` | `local_apres_profile.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:verbier-verbier` | `local_apres_profile.intensity` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:verbier-verbier` | `local_apres_profile.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:verbier-verbier` | `longitude` | `changed` |  |
| `stay_base:verbier-verbier` | `name` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `price_max` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `price_min` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `price_range` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `quality` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `regional_data_ids` | `changed` |  |
| `stay_base:verbier-verbier` | `stay_base_id` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:verbier` | `country` | `reviewed-no-change` |  |
| `stay_destination:verbier` | `latitude` | `reviewed-no-change` |  |
| `stay_destination:verbier` | `longitude` | `reviewed-no-change` |  |
| `stay_destination:verbier` | `name` | `reviewed-no-change` |  |
| `stay_destination:verbier` | `price_level` | `reviewed-no-change` |  |
| `stay_destination:verbier` | `region` | `reviewed-no-change` |  |
| `stay_destination:verbier` | `regional_data_ids` | `reviewed-no-change` |  |
| `stay_destination:verbier` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:verbier` | `trip_market_region_id` | `reviewed-no-change` |  |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `field_source_refs` | `changed` |  |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:verbier-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:verbier-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:verbier-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:verbier-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:verbier-verbier` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:verbier-verbier` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:verbier-verbier` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:verbier-verbier` | `notes` | `reviewed-no-change` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:verbier-4-vallees-pass` | `available_from_stay_destination_ids` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `"4 Vallées ski pass"` | Official Verbier pass guidance supports the 4 Vallées pass product, broad network validity, and representative from-prices. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:verbier-4-vallees-pass` | `default_for_stay_destination_ids` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `"4 Vallées ski pass"` | Official Verbier pass guidance supports the 4 Vallées pass product, broad network validity, and representative from-prices. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:verbier-4-vallees-pass` | `external_validity_summary` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `"Covers the Verbier sector locally and the wider 4 Vallées network including Bruson, La Tzoumaz, Nendaz, Veysonnaz and Thyon when those links are operating."` | Official Verbier pass guidance supports the 4 Vallées pass product, broad network validity, and representative from-prices. |  |
| `lift_pass_product:verbier-4-vallees-pass` | `lift_pass_product_id` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `"4 Vallées ski pass"` | Official Verbier pass guidance supports the 4 Vallées pass product, broad network validity, and representative from-prices. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:verbier-4-vallees-pass` | `name` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `"4 Vallées ski pass"` | Official Verbier pass guidance supports the 4 Vallées pass product, broad network validity, and representative from-prices. |  |
| `lift_pass_product:verbier-4-vallees-pass` | `prices` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `[{"amount": 87.0, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "from", "season_label": "Winter 2025/26 dynamic day-pass from price", "source_url": "https://www.verbier.com/ski-passes"}, {"amount": 409.0, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "from", "season_label": "Winter 2025/26 4 Vallées six-day from price", "source_url": "https://www.verbier.com/ski-passes"}]` | Official Verbier pass guidance supports the 4 Vallées pass product, broad network validity, and representative from-prices. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:verbier-4-vallees-pass` | `terrain_domain_ids` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `"4 Vallées ski pass"` | Official Verbier pass guidance supports the 4 Vallées pass product, broad network validity, and representative from-prices. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:verbier-4-vallees-pass` | `valid_ski_area_ids` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `["verbier-ski-area"]` | Official Verbier pass guidance supports the 4 Vallées pass product, broad network validity, and representative from-prices. |  |
| `lift_pass_product:verbier-4-vallees-pass` | `validity_scope` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `"regional_network"` | Official Verbier pass guidance supports the 4 Vallées pass product, broad network validity, and representative from-prices. | Modeled as regional_network because the pass extends beyond the local Verbier sector. |
| `ski_area:verbier-ski-area` | `season_start_month` | [Verbier 4Vallées 4 Vallées ski area](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `11` | Official 4 Vallées page describes the winter season as running from November until the end of April. | Normalized month wording to numeric start month. |
| `ski_area:verbier-ski-area` | `supported_skill_levels` | [Verbier 4Vallées 4 Vallées ski area](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `11` | Official 4 Vallées page describes the winter season as running from November until the end of April. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:verbier-ski-area` | `total_lift_count` | [Verbier 4Vallées ski resort](https://verbier4vallees.ch/en/ski-resort) | `33` | Official Verbier sector section states the Verbier sector has 33 lifts. |  |
| `ski_area:verbier-ski-area` | `total_piste_km` | [Verbier 4Vallées ski resort](https://verbier4vallees.ch/en/ski-resort) | `106.0` | Official Verbier sector section states the Verbier sector has 106 km of runs. |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `access_mode` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `"walk"` | Official tourism guidance describes the Verbier village beginner/base area and the Medran/Place Blanche access context; OSM distance supports walk access. |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `distance_m` | [OpenStreetMap Mountain Air node](https://www.openstreetmap.org/node/1038335696) | `600` | OSM places Mountain Air at Place Blanche about 581 m from the Verbier village node; this is used as the reviewed Medran base-area access proxy. | Rounded to 600 m because the lift station itself is not separately indexed in Nominatim. |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `nearest_lift_name` | [Mountain Air Verbier](https://www.verbier.com/equipment-hire/mountain-air-verbier) | `"Medran / Place Blanche"` | Official tourism listing places Mountain Air at Rue de Medran/Place Blanche, the lift-adjacent Verbier base area. | Normalized the lift access label to Medran / Place Blanche. |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `source_urls` | [Verbier.com ski passes](https://www.verbier.com/ski-passes) | `"walk"` | Official tourism guidance describes the Verbier village beginner/base area and the Medran/Place Blanche access context; OSM distance supports walk access. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:verbier-verbier` | `base_type` | [OpenStreetMap Verbier node](https://www.openstreetmap.org/node/310532759) | `"village"` | OSM classifies Verbier as a village. |  |
| `stay_base:verbier-verbier` | `latitude` | [OpenStreetMap Verbier node](https://www.openstreetmap.org/node/310532759) | `46.0961` | OSM node 310532759 provides Verbier village coordinates. | Rounded OSM latitude 46.0961011 to four decimals. |
| `stay_base:verbier-verbier` | `longitude` | [OpenStreetMap Verbier node](https://www.openstreetmap.org/node/310532759) | `7.2287` | OSM node 310532759 provides Verbier village coordinates. | Rounded OSM longitude 7.2286765 to four decimals. |
| `stay_base:verbier-verbier` | `regional_data_ids` | [OpenStreetMap Verbier node](https://www.openstreetmap.org/node/310532759) | `{"osm_node_id": "310532759", "rental_osm_node_id": "1038335696"}` | OSM village and Mountain Air nodes anchor stay-base and base-area references. |  |
| `stay_destination:verbier` | `name` | [Verbier 4Vallées 4 Vallées ski area](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `"Verbier"` | The normalized migration retains the already reviewed destination boundary. |  |

## Boundary Decisions

- `verbier`: `pass`

## Ranking Impact

Ranking-relevant facts now attach to the normalized ski-area, stay-base, and access-edge owners; Search V3 scoring policy is unchanged.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation typed REPORT.json --markdown-output REPORT.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation reconcile REPORT.json --base-catalog-path BASE/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json`

## Caveats

- Exact 2026/27 Verbier day-ticket table and exact operating window remain unresolved; reviewed official pages expose dynamic pricing and snow-condition-dependent dates rather than a stable full future tariff/window.
- Piste difficulty split remains unresolved because reviewed official sources did not publish beginner/intermediate/advanced piste kilometers for the Verbier sector.
- Rental/stay price ranges and normalized quality tiers remain estimated.
- Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up.
