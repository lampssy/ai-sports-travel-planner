# St Anton Full Catalog Curation - normalized model migration

Migrates PR #11 onto the normalized Snowcast catalog. Facts are assigned to explicit regions, stay destinations, stay bases, ski areas, access edges, terrain domains, pass products, and rental facts.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:ski-arlberg-pass` | `full` | all canonical fields |
| `rental_display_fact:st-anton-am-arlberg-intersport-arlberg-shop-st-anton` | `full` | all canonical fields |
| `ski_area:st-anton-am-arlberg-ski-area` | `full` | all canonical fields |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `full` | all canonical fields |
| `ski_region:st-anton-am-arlberg` | `full` | all canonical fields |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `full` | all canonical fields |
| `stay_destination:st-anton-am-arlberg` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:ski-arlberg-pass` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:st-anton-am-arlberg-ski-area` | `full` | all canonical fields |
| `trust_manifest:stay_bases:st-anton-am-arlberg-st-anton-am-arlberg` | `full` | all canonical fields |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:ski-arlberg-pass` | `available_from_stay_destination_ids` | `null` | `["st-anton-am-arlberg"]` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-arlberg-pass` | `default_for_stay_destination_ids` | `null` | `["st-anton-am-arlberg"]` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-arlberg-pass` | `external_validity_summary` | `null` | `"Covers the linked Ski Arlberg area including St. Anton, St. Christoph, Stuben, Lech, Oberlech, Zurs, Warth, Schroecken, and related Arlberg sectors; only the St Anton weather unit is modeled locally."` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-arlberg-pass` | `lift_pass_product_id` | `null` | `"ski-arlberg-pass"` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-arlberg-pass` | `name` | `null` | `"Ski Arlberg Pass"` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-arlberg-pass` | `prices` | `null` | `[{"amount": 241.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 450.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 81.5, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}]` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-arlberg-pass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-arlberg-pass` | `valid_ski_area_ids` | `null` | `["st-anton-am-arlberg-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-arlberg-pass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `ski_area:st-anton-am-arlberg-ski-area` | `season_windows` | `[]` | `[{"end_date": "2026-04-19", "season_label": "Winter 2025/26", "start_date": "2025-12-03", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `nearest_lift_name` | `null` | `"Galzigbahn / Gampenbahn"` | `verified_with_adjustment` | no |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `source_urls` | `["https://www.bergfex.com/stanton-stchristoph/"]` | `["https://www.bergfex.com/stanton-stchristoph/", "https://www.openstreetmap.org/relation/76825", "https://www.openstreetmap.org/way/29710303", "https://www.skiarlberg.at/en/st-anton/winter/ski-region"]` | `verified_with_adjustment` | no |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `atmosphere_tags` | `[]` | `["sporty", "apres_ski", "walkable_lifts"]` | `verified_with_adjustment` | no |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `base_type` | `null` | `"resort_village"` | `verified_with_adjustment` | no |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `latitude` | `null` | `47.1289` | `verified_with_adjustment` | no |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `longitude` | `null` | `10.2664` | `verified_with_adjustment` | no |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `regional_data_ids` | `{}` | `{"osm_relation_id": "76825"}` | `verified` | no |
| `trust_manifest:lift_pass_products:ski-arlberg-pass` | `display_name` | `null` | `"Ski Arlberg Pass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:ski-arlberg-pass` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:ski-arlberg-pass` | `notes` | `null` | `["PR #11 legacy curation was translated onto normalized catalog ownership and relationships."]` | `estimated` | no |
| `trust_manifest:lift_pass_products:ski-arlberg-pass` | `source_refs` | `null` | `["https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"]` | `estimated` | no |
| `trust_manifest:ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "estimated"}` | `estimated` | no |
| `trust_manifest:ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `source_refs` | `["https://www.bergfex.com/stanton-stchristoph/"]` | `["https://www.bergfex.com/stanton-stchristoph/", "https://www.openstreetmap.org/relation/76825", "https://www.openstreetmap.org/way/29710303", "https://www.skiarlberg.at/en/st-anton/winter/ski-region"]` | `estimated` | no |
| `trust_manifest:ski_areas:st-anton-am-arlberg-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "identity_coordinates": "needs_source", "skill_fit": "estimated", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "identity_coordinates": "needs_source", "skill_fit": "estimated", "terrain_metrics": "needs_source"}` | `estimated` | no |
| `trust_manifest:ski_areas:st-anton-am-arlberg-ski-area` | `source_refs` | `[]` | `["https://www.skiarlberg.at/en/tickets-season-times/season-times-winter"]` | `estimated` | no |
| `trust_manifest:stay_bases:st-anton-am-arlberg-st-anton-am-arlberg` | `field_statuses` | `{"atmosphere": "estimated", "coordinates": "needs_source", "identity_ownership": "needs_source", "lodging_price_quality": "estimated"}` | `{"atmosphere": "estimated", "coordinates": "verified_with_adjustment", "identity_ownership": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:st-anton-am-arlberg-st-anton-am-arlberg` | `source_refs` | `[]` | `["https://www.openstreetmap.org/relation/76825", "https://www.skiarlberg.at/en/st-anton/winter/ski-region"]` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:ski-arlberg-pass` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:ski-arlberg-pass` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:ski-arlberg-pass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:ski-arlberg-pass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:ski-arlberg-pass` | `name` | `changed` |  |
| `lift_pass_product:ski-arlberg-pass` | `pass_accessible_terrain` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `lift_pass_product:ski-arlberg-pass` | `prices` | `changed` |  |
| `lift_pass_product:ski-arlberg-pass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:ski-arlberg-pass` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:ski-arlberg-pass` | `validity_scope` | `changed` |  |
| `rental_display_fact:st-anton-am-arlberg-intersport-arlberg-shop-st-anton` | `lift_distance` | `reviewed-no-change` |  |
| `rental_display_fact:st-anton-am-arlberg-intersport-arlberg-shop-st-anton` | `name` | `reviewed-no-change` |  |
| `rental_display_fact:st-anton-am-arlberg-intersport-arlberg-shop-st-anton` | `price_max` | `reviewed-no-change` |  |
| `rental_display_fact:st-anton-am-arlberg-intersport-arlberg-shop-st-anton` | `price_min` | `reviewed-no-change` |  |
| `rental_display_fact:st-anton-am-arlberg-intersport-arlberg-shop-st-anton` | `price_range` | `reviewed-no-change` |  |
| `rental_display_fact:st-anton-am-arlberg-intersport-arlberg-shop-st-anton` | `quality` | `reviewed-no-change` |  |
| `rental_display_fact:st-anton-am-arlberg-intersport-arlberg-shop-st-anton` | `rental_display_fact_id` | `reviewed-no-change` |  |
| `rental_display_fact:st-anton-am-arlberg-intersport-arlberg-shop-st-anton` | `stay_base_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `rental_display_fact:st-anton-am-arlberg-intersport-arlberg-shop-st-anton` | `stay_destination_id` | `reviewed-no-change` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `base_elevation_m` | `reviewed-no-change` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `name` | `reviewed-no-change` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area:st-anton-am-arlberg-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area:st-anton-am-arlberg-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area:st-anton-am-arlberg-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `season_start_month` | `reviewed-no-change` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `season_windows` | `changed` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `summit_elevation_m` | `reviewed-no-change` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `supported_skill_levels` | `reviewed-no-change` |  |
| `ski_area:st-anton-am-arlberg-ski-area` | `total_lift_count` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area:st-anton-am-arlberg-ski-area` | `total_piste_km` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `distance_m` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `duration_minutes` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `is_direct` | `reviewed-no-change` |  |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `lift_distance` | `reviewed-no-change` |  |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `regional_data_ids` | `reviewed-no-change` |  |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `ski_area_access_id` | `reviewed-no-change` |  |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `stay_base_id` | `reviewed-no-change` |  |
| `ski_region:st-anton-am-arlberg` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:st-anton-am-arlberg` | `name` | `reviewed-no-change` |  |
| `ski_region:st-anton-am-arlberg` | `parent_ski_region_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `ski_region:st-anton-am-arlberg` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:st-anton-am-arlberg` | `source_urls` | `reviewed-no-change` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `atmosphere_tags` | `changed` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `base_type` | `changed` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `latitude` | `changed` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `longitude` | `changed` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `name` | `reviewed-no-change` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `price_max` | `reviewed-no-change` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `price_min` | `reviewed-no-change` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `price_range` | `reviewed-no-change` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `quality` | `reviewed-no-change` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `regional_data_ids` | `changed` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `stay_base_id` | `reviewed-no-change` |  |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:st-anton-am-arlberg` | `atmosphere_tags` | `reviewed-no-change` |  |
| `stay_destination:st-anton-am-arlberg` | `country` | `reviewed-no-change` |  |
| `stay_destination:st-anton-am-arlberg` | `latitude` | `reviewed-no-change` |  |
| `stay_destination:st-anton-am-arlberg` | `longitude` | `reviewed-no-change` |  |
| `stay_destination:st-anton-am-arlberg` | `name` | `reviewed-no-change` |  |
| `stay_destination:st-anton-am-arlberg` | `price_level` | `reviewed-no-change` |  |
| `stay_destination:st-anton-am-arlberg` | `region` | `reviewed-no-change` |  |
| `stay_destination:st-anton-am-arlberg` | `regional_data_ids` | `reviewed-no-change` |  |
| `stay_destination:st-anton-am-arlberg` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:st-anton-am-arlberg` | `trip_market_region_id` | `reviewed-no-change` |  |
| `trust_manifest:lift_pass_products:ski-arlberg-pass` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:ski-arlberg-pass` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:ski-arlberg-pass` | `notes` | `changed` |  |
| `trust_manifest:lift_pass_products:ski-arlberg-pass` | `source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `source_refs` | `changed` |  |
| `trust_manifest:ski_areas:st-anton-am-arlberg-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:st-anton-am-arlberg-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:st-anton-am-arlberg-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:st-anton-am-arlberg-ski-area` | `source_refs` | `changed` |  |
| `trust_manifest:stay_bases:st-anton-am-arlberg-st-anton-am-arlberg` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:st-anton-am-arlberg-st-anton-am-arlberg` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:st-anton-am-arlberg-st-anton-am-arlberg` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:st-anton-am-arlberg-st-anton-am-arlberg` | `source_refs` | `changed` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:ski-arlberg-pass` | `available_from_stay_destination_ids` | [Ski Arlberg Ticket Guide Winter 2025/26](https://www.skiarlberg.at/api/backend/download/de/asset?id=2130) | `{"external_validity_summary": "Covers the linked Ski Arlberg area including St. Anton, St. Christoph, Stuben, Lech, Oberlech, Zurs, Warth, Schroecken, and related Arlberg sectors; only the St Anton weather unit is modeled locally.", "is_default": true, "lift_pass_product_id": "ski-arlberg-pass", "name": "Ski Arlberg Pass", "prices": [{"amount": 81.5, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 450.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}], "valid_ski_area_ids": ["st-anton-am-arlberg-ski-area"], "validity_scope": "regional_network"}` | Official Ski Arlberg ticket guide lists adult high-season 1-day, 3-day, and 6-day prices and states Ski Arlberg ticket validity across member facilities. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:ski-arlberg-pass` | `default_for_stay_destination_ids` | [Ski Arlberg Ticket Guide Winter 2025/26](https://www.skiarlberg.at/api/backend/download/de/asset?id=2130) | `{"external_validity_summary": "Covers the linked Ski Arlberg area including St. Anton, St. Christoph, Stuben, Lech, Oberlech, Zurs, Warth, Schroecken, and related Arlberg sectors; only the St Anton weather unit is modeled locally.", "is_default": true, "lift_pass_product_id": "ski-arlberg-pass", "name": "Ski Arlberg Pass", "prices": [{"amount": 81.5, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 450.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}], "valid_ski_area_ids": ["st-anton-am-arlberg-ski-area"], "validity_scope": "regional_network"}` | Official Ski Arlberg ticket guide lists adult high-season 1-day, 3-day, and 6-day prices and states Ski Arlberg ticket validity across member facilities. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:ski-arlberg-pass` | `external_validity_summary` | [Ski Arlberg Ticket Guide Winter 2025/26](https://www.skiarlberg.at/api/backend/download/de/asset?id=2130) | `{"external_validity_summary": "Covers the linked Ski Arlberg area including St. Anton, St. Christoph, Stuben, Lech, Oberlech, Zurs, Warth, Schroecken, and related Arlberg sectors; only the St Anton weather unit is modeled locally.", "is_default": true, "lift_pass_product_id": "ski-arlberg-pass", "name": "Ski Arlberg Pass", "prices": [{"amount": 81.5, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 450.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}], "valid_ski_area_ids": ["st-anton-am-arlberg-ski-area"], "validity_scope": "regional_network"}` | Official Ski Arlberg ticket guide lists adult high-season 1-day, 3-day, and 6-day prices and states Ski Arlberg ticket validity across member facilities. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:ski-arlberg-pass` | `lift_pass_product_id` | [Ski Arlberg Ticket Guide Winter 2025/26](https://www.skiarlberg.at/api/backend/download/de/asset?id=2130) | `{"external_validity_summary": "Covers the linked Ski Arlberg area including St. Anton, St. Christoph, Stuben, Lech, Oberlech, Zurs, Warth, Schroecken, and related Arlberg sectors; only the St Anton weather unit is modeled locally.", "is_default": true, "lift_pass_product_id": "ski-arlberg-pass", "name": "Ski Arlberg Pass", "prices": [{"amount": 81.5, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 450.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}], "valid_ski_area_ids": ["st-anton-am-arlberg-ski-area"], "validity_scope": "regional_network"}` | Official Ski Arlberg ticket guide lists adult high-season 1-day, 3-day, and 6-day prices and states Ski Arlberg ticket validity across member facilities. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:ski-arlberg-pass` | `name` | [Ski Arlberg Ticket Guide Winter 2025/26](https://www.skiarlberg.at/api/backend/download/de/asset?id=2130) | `{"external_validity_summary": "Covers the linked Ski Arlberg area including St. Anton, St. Christoph, Stuben, Lech, Oberlech, Zurs, Warth, Schroecken, and related Arlberg sectors; only the St Anton weather unit is modeled locally.", "is_default": true, "lift_pass_product_id": "ski-arlberg-pass", "name": "Ski Arlberg Pass", "prices": [{"amount": 81.5, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 450.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}], "valid_ski_area_ids": ["st-anton-am-arlberg-ski-area"], "validity_scope": "regional_network"}` | Official Ski Arlberg ticket guide lists adult high-season 1-day, 3-day, and 6-day prices and states Ski Arlberg ticket validity across member facilities. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:ski-arlberg-pass` | `prices` | [Ski Arlberg Ticket Guide Winter 2025/26](https://www.skiarlberg.at/api/backend/download/de/asset?id=2130) | `{"external_validity_summary": "Covers the linked Ski Arlberg area including St. Anton, St. Christoph, Stuben, Lech, Oberlech, Zurs, Warth, Schroecken, and related Arlberg sectors; only the St Anton weather unit is modeled locally.", "is_default": true, "lift_pass_product_id": "ski-arlberg-pass", "name": "Ski Arlberg Pass", "prices": [{"amount": 81.5, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 450.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}], "valid_ski_area_ids": ["st-anton-am-arlberg-ski-area"], "validity_scope": "regional_network"}` | Official Ski Arlberg ticket guide lists adult high-season 1-day, 3-day, and 6-day prices and states Ski Arlberg ticket validity across member facilities. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:ski-arlberg-pass` | `terrain_domain_ids` | [Ski Arlberg Ticket Guide Winter 2025/26](https://www.skiarlberg.at/api/backend/download/de/asset?id=2130) | `{"external_validity_summary": "Covers the linked Ski Arlberg area including St. Anton, St. Christoph, Stuben, Lech, Oberlech, Zurs, Warth, Schroecken, and related Arlberg sectors; only the St Anton weather unit is modeled locally.", "is_default": true, "lift_pass_product_id": "ski-arlberg-pass", "name": "Ski Arlberg Pass", "prices": [{"amount": 81.5, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 450.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}], "valid_ski_area_ids": ["st-anton-am-arlberg-ski-area"], "validity_scope": "regional_network"}` | Official Ski Arlberg ticket guide lists adult high-season 1-day, 3-day, and 6-day prices and states Ski Arlberg ticket validity across member facilities. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:ski-arlberg-pass` | `valid_ski_area_ids` | [Ski Arlberg Ticket Guide Winter 2025/26](https://www.skiarlberg.at/api/backend/download/de/asset?id=2130) | `{"external_validity_summary": "Covers the linked Ski Arlberg area including St. Anton, St. Christoph, Stuben, Lech, Oberlech, Zurs, Warth, Schroecken, and related Arlberg sectors; only the St Anton weather unit is modeled locally.", "is_default": true, "lift_pass_product_id": "ski-arlberg-pass", "name": "Ski Arlberg Pass", "prices": [{"amount": 81.5, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 450.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}], "valid_ski_area_ids": ["st-anton-am-arlberg-ski-area"], "validity_scope": "regional_network"}` | Official Ski Arlberg ticket guide lists adult high-season 1-day, 3-day, and 6-day prices and states Ski Arlberg ticket validity across member facilities. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:ski-arlberg-pass` | `validity_scope` | [Ski Arlberg Ticket Guide Winter 2025/26](https://www.skiarlberg.at/api/backend/download/de/asset?id=2130) | `{"external_validity_summary": "Covers the linked Ski Arlberg area including St. Anton, St. Christoph, Stuben, Lech, Oberlech, Zurs, Warth, Schroecken, and related Arlberg sectors; only the St Anton weather unit is modeled locally.", "is_default": true, "lift_pass_product_id": "ski-arlberg-pass", "name": "Ski Arlberg Pass", "prices": [{"amount": 81.5, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}, {"amount": 450.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 high season", "source_url": "https://www.skiarlberg.at/api/backend/download/de/asset?id=2130"}], "valid_ski_area_ids": ["st-anton-am-arlberg-ski-area"], "validity_scope": "regional_network"}` | Official Ski Arlberg ticket guide lists adult high-season 1-day, 3-day, and 6-day prices and states Ski Arlberg ticket validity across member facilities. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:st-anton-am-arlberg-ski-area` | `season_windows` | [Winter Season Times \| Ski Arlberg](https://www.skiarlberg.at/en/tickets-season-times/season-times-winter) | `[{"end_date": "2026-04-19", "season_label": "Winter 2025/26", "start_date": "2025-12-03", "status": "planned"}]` | Official Ski Arlberg season page lists the relevant St. Anton winter operating window. | Mirrors the destination season window for the single modeled weather unit. |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `access_mode` | [Ski region St. Anton](https://www.skiarlberg.at/en/st-anton/winter/ski-region) | `"Galzigbahn valley station in St Anton"` | Official page supports direct village access to the Galzigbahn valley station. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `nearest_lift_name` | [Ski region St. Anton](https://www.skiarlberg.at/en/st-anton/winter/ski-region) | `"Tourist information located at the Galzigbahn valley station"` | Official St Anton ski-region page places tourist information at the Galzigbahn valley station. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area` | `source_urls` | [Ski region St. Anton](https://www.skiarlberg.at/en/st-anton/winter/ski-region) | `"Galzigbahn valley station in St Anton"` | Official page supports direct village access to the Galzigbahn valley station. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `atmosphere_tags` | [Ski region St. Anton](https://www.skiarlberg.at/en/st-anton/winter/ski-region) | `["sporty", "cradle of Alpine skiing", "Galzigbahn valley station"]` | Official St Anton page emphasizes sporty winter sports, ski heritage, and direct village lift access. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `base_type` | [Ski region St. Anton](https://www.skiarlberg.at/en/st-anton/winter/ski-region) | `"St. Anton. St. Christoph. Stuben."` | Official page describes St Anton as one of the three eastern Arlberg locations shaping the ski region. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `latitude` | [OpenStreetMap Sankt Anton am Arlberg relation](https://www.openstreetmap.org/relation/76825) | `47.1288996` | OSM relation 76825 locates Sankt Anton am Arlberg at latitude 47.1288996. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `longitude` | [OpenStreetMap Sankt Anton am Arlberg relation](https://www.openstreetmap.org/relation/76825) | `10.2663669` | OSM relation 76825 locates Sankt Anton am Arlberg at longitude 10.2663669. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:st-anton-am-arlberg-st-anton-am-arlberg` | `regional_data_ids` | [OpenStreetMap Sankt Anton am Arlberg relation](https://www.openstreetmap.org/relation/76825) | `{"osm_relation_id": "76825"}` | OSM identifies Sankt Anton am Arlberg as relation 76825. |  |
| `stay_destination:st-anton-am-arlberg` | `name` | [Winter Season Times \| Ski Arlberg](https://www.skiarlberg.at/en/tickets-season-times/season-times-winter) | `"St Anton am Arlberg"` | The normalized migration retains the already reviewed destination boundary. |  |

## Boundary Decisions

- `st-anton-am-arlberg`: `pass`

## Ranking Impact

Ranking-relevant facts now attach to the normalized ski-area, stay-base, and access-edge owners; Search V3 scoring policy is unchanged.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation typed REPORT.json --markdown-output REPORT.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation reconcile REPORT.json --base-catalog-path BASE/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json`

## Caveats

- Ski Arlberg publishes 300 km of runs and 85 lifts for the linked Arlberg domain; these metrics are not copied to the local St Anton ski_area because linked member sectors are outside the modeled child weather unit.
- No child-scoped official piste difficulty-km split was found for the St Anton weather unit.
- Official 2026/27 winter ticket tariffs are not published yet; representative pass prices use the official Winter 2025/26 ticket guide.
- Accommodation and rental price ranges remain product-curated estimates until a provider sampling policy is reviewed.
