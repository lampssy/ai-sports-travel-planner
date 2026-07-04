# Kitzbühel Catalog Curation - normalized model migration

Migrates PR #14 onto the normalized Snowcast catalog. Facts are assigned to explicit regions, stay destinations, stay bases, ski areas, access edges, terrain domains, pass products, and rental facts.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:kitzski-skipass` | `full` | all canonical fields |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `full` | all canonical fields |
| `ski_area:kitzbuhel-ski-area` | `full` | all canonical fields |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `full` | all canonical fields |
| `ski_region:kitzbuhel` | `full` | all canonical fields |
| `stay_base:kitzbuhel-kitzbuhel` | `full` | all canonical fields |
| `stay_destination:kitzbuhel` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_regions:kitzbuhel` | `full` | all canonical fields |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:kitzbuhel` | `full` | all canonical fields |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:kitzski-skipass` | `available_from_stay_destination_ids` | `null` | `["kitzbuhel"]` | `estimated` | no |
| `lift_pass_product:kitzski-skipass` | `default_for_stay_destination_ids` | `null` | `["kitzbuhel"]` | `estimated` | no |
| `lift_pass_product:kitzski-skipass` | `lift_pass_product_id` | `null` | `"kitzski-skipass"` | `estimated` | no |
| `lift_pass_product:kitzski-skipass` | `name` | `null` | `"KitzSki Ski Pass"` | `estimated` | no |
| `lift_pass_product:kitzski-skipass` | `prices` | `null` | `[{"amount": 244.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 premium season cash desk", "source_url": "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"}, {"amount": 423.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 premium season cash desk", "source_url": "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"}, {"amount": 83.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 premium season cash desk", "source_url": "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"}]` | `estimated` | no |
| `lift_pass_product:kitzski-skipass` | `terrain_domain_ids` | `null` | `[]` | `estimated` | no |
| `lift_pass_product:kitzski-skipass` | `valid_ski_area_ids` | `null` | `["kitzbuhel-ski-area"]` | `estimated` | no |
| `lift_pass_product:kitzski-skipass` | `validity_scope` | `null` | `"single_ski_area"` | `estimated` | no |
| `ski_area:kitzbuhel-ski-area` | `name` | `"Kitzbuhel"` | `"Kitzbühel"` | `verified_with_adjustment` | no |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.advanced` | `null` | `20.0` | `verified_with_adjustment` | yes |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.beginner` | `null` | `94.0` | `verified_with_adjustment` | yes |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.intermediate` | `null` | `67.0` | `verified_with_adjustment` | yes |
| `ski_area:kitzbuhel-ski-area` | `supported_skill_levels` | `["beginner", "intermediate"]` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:kitzbuhel-ski-area` | `total_lift_count` | `null` | `58` | `verified` | yes |
| `ski_area:kitzbuhel-ski-area` | `total_piste_km` | `null` | `181.0` | `verified_with_adjustment` | yes |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `distance_m` | `null` | `380` | `verified_with_adjustment` | yes |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `lift_distance` | `"medium"` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `nearest_lift_name` | `null` | `"Hahnenkammbahn"` | `verified_with_adjustment` | no |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `source_urls` | `["https://www.bergfex.com/kitzbuehel-kirchberg/"]` | `["https://www.bergfex.com/kitzbuehel-kirchberg/", "https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/node/1685958015", "https://www.openstreetmap.org/relation/85657", "https://www.openstreetmap.org/way/156335495"]` | `verified_with_adjustment` | no |
| `ski_region:kitzbuhel` | `name` | `"Kitzbuhel"` | `"Kitzbühel"` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `base_type` | `null` | `"town"` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `latitude` | `null` | `47.4464` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `longitude` | `null` | `12.3911` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `name` | `"Kitzbuhel"` | `"Kitzbühel"` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `regional_data_ids` | `{}` | `{"osm_relation_id": "85657"}` | `verified_with_adjustment` | no |
| `stay_destination:kitzbuhel` | `name` | `"Kitzbuhel"` | `"Kitzbühel"` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `display_name` | `null` | `"KitzSki Ski Pass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `field_source_refs` | `null` | `{"coverage": ["https://www.element3-kitzbuehel.at/en/", "https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.kitzski.at/en/service-info/ski-rental-amp-ski-service.html", "https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html", "https://www.kitzski.at/en/tickets-vouchers/ski-ticket.html", "https://www.kitzski.at/media/preise-26-27-hp-en.pdf", "https://www.openstreetmap.org/node/1685958015", "https://www.openstreetmap.org/relation/85657", "https://www.openstreetmap.org/way/156335495"], "identity_scope_availability": ["https://www.element3-kitzbuehel.at/en/", "https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.kitzski.at/en/service-info/ski-rental-amp-ski-service.html", "https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html", "https://www.kitzski.at/en/tickets-vouchers/ski-ticket.html", "https://www.kitzski.at/media/preise-26-27-hp-en.pdf", "https://www.openstreetmap.org/node/1685958015", "https://www.openstreetmap.org/relation/85657", "https://www.openstreetmap.org/way/156335495"], "pass_accessible_terrain": ["https://www.element3-kitzbuehel.at/en/", "https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.kitzski.at/en/service-info/ski-rental-amp-ski-service.html", "https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html", "https://www.kitzski.at/en/tickets-vouchers/ski-ticket.html", "https://www.kitzski.at/media/preise-26-27-hp-en.pdf", "https://www.openstreetmap.org/node/1685958015", "https://www.openstreetmap.org/relation/85657", "https://www.openstreetmap.org/way/156335495"], "prices": ["https://www.element3-kitzbuehel.at/en/", "https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.kitzski.at/en/service-info/ski-rental-amp-ski-service.html", "https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html", "https://www.kitzski.at/en/tickets-vouchers/ski-ticket.html", "https://www.kitzski.at/media/preise-26-27-hp-en.pdf", "https://www.openstreetmap.org/node/1685958015", "https://www.openstreetmap.org/relation/85657", "https://www.openstreetmap.org/way/156335495"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `field_statuses` | `null` | `{"coverage": "estimated", "identity_scope_availability": "estimated", "pass_accessible_terrain": "needs_source", "prices": "estimated"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `notes` | `null` | `["PR #14 legacy curation was translated onto normalized catalog ownership and relationships."]` | `estimated` | no |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `display_name` | `"Kitzbuhel -> Kitzbuhel"` | `"Kitzbühel -> Kitzbühel"` | `estimated` | no |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/kitzbuehel-kirchberg/"], "relationship": ["https://www.bergfex.com/kitzbuehel-kirchberg/"]}` | `{"access_mode_distance": ["https://www.bergfex.com/kitzbuehel-kirchberg/", "https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/node/1685958015", "https://www.openstreetmap.org/relation/85657", "https://www.openstreetmap.org/way/156335495"], "relationship": ["https://www.bergfex.com/kitzbuehel-kirchberg/", "https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/node/1685958015", "https://www.openstreetmap.org/relation/85657", "https://www.openstreetmap.org/way/156335495"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "estimated"}` | `estimated` | no |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `display_name` | `"Kitzbuhel"` | `"Kitzbühel"` | `estimated` | no |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "glacier_terrain": [], "identity_coordinates": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "snow_park": [], "snowmaking": [], "terrain_metrics": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"]}` | `estimated` | no |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_regions:kitzbuhel` | `display_name` | `"Kitzbuhel"` | `"Kitzbühel"` | `estimated` | no |
| `trust_manifest:ski_regions:kitzbuhel` | `field_source_refs` | `{"identity": [], "membership_context": []}` | `{"identity": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "membership_context": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"]}` | `estimated` | no |
| `trust_manifest:ski_regions:kitzbuhel` | `field_statuses` | `{"identity": "needs_source", "membership_context": "estimated"}` | `{"identity": "verified_with_adjustment", "membership_context": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `display_name` | `"Kitzbuhel"` | `"Kitzbühel"` | `estimated` | no |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `{"base_character": [], "base_type": [], "coordinates": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/relation/85657"], "elevation": [], "identity_ownership": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/relation/85657"], "local_apres": [], "lodging_price_quality": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/relation/85657"]}` | `estimated` | no |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "verified_with_adjustment", "elevation": "needs_source", "identity_ownership": "verified_with_adjustment", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:kitzbuhel` | `display_name` | `"Kitzbuhel"` | `"Kitzbühel"` | `estimated` | no |
| `trust_manifest:stay_destinations:kitzbuhel` | `field_source_refs` | `{"coordinates": [], "identity_location": [], "price_level": []}` | `{"coordinates": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "identity_location": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "price_level": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"]}` | `estimated` | no |
| `trust_manifest:stay_destinations:kitzbuhel` | `field_statuses` | `{"coordinates": "needs_source", "identity_location": "needs_source", "price_level": "estimated"}` | `{"coordinates": "needs_source", "identity_location": "verified_with_adjustment", "price_level": "estimated"}` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:kitzski-skipass` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:kitzski-skipass` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:kitzski-skipass` | `external_validity_summary` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `lift_pass_product:kitzski-skipass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:kitzski-skipass` | `name` | `changed` |  |
| `lift_pass_product:kitzski-skipass` | `pass_accessible_terrain` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `lift_pass_product:kitzski-skipass` | `prices` | `changed` |  |
| `lift_pass_product:kitzski-skipass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:kitzski-skipass` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:kitzski-skipass` | `validity_scope` | `changed` |  |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `lift_distance` | `reviewed-no-change` |  |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `name` | `reviewed-no-change` |  |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `price_max` | `reviewed-no-change` |  |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `price_min` | `reviewed-no-change` |  |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `price_range` | `reviewed-no-change` |  |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `quality` | `reviewed-no-change` |  |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `rental_display_fact_id` | `reviewed-no-change` |  |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `stay_base_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `stay_destination_id` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `base_elevation_m` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `glacier_terrain.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.route_count` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `name` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `night_skiing.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `night_skiing.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `official_trail_map.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `official_trail_map.url` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `season_start_month` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `season_windows` | `unresolved` | Reviewed sources did not resolve a retained structured value. |
| `ski_area:kitzbuhel-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `ski_day_apres_profile.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `ski_day_apres_profile.intensity` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `ski_day_apres_profile.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `snow_park.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `snow_park.park_count` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `snow_park.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `snowmaking.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `snowmaking.coverage_basis` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `snowmaking.coverage_pct` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `snowmaking.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `ski_area:kitzbuhel-ski-area` | `summit_elevation_m` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `duration_minutes` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `is_direct` | `reviewed-no-change` |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `regional_data_ids` | `reviewed-no-change` |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `ski_area_access_id` | `reviewed-no-change` |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `stay_base_id` | `reviewed-no-change` |  |
| `ski_region:kitzbuhel` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:kitzbuhel` | `name` | `changed` |  |
| `ski_region:kitzbuhel` | `parent_ski_region_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `ski_region:kitzbuhel` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:kitzbuhel` | `source_urls` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `base_character.development_style` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:kitzbuhel-kitzbuhel` | `base_character.local_pace` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:kitzbuhel-kitzbuhel` | `base_type` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `elevation_m` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:kitzbuhel-kitzbuhel` | `latitude` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `local_apres_profile.availability` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:kitzbuhel-kitzbuhel` | `local_apres_profile.intensity` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:kitzbuhel-kitzbuhel` | `local_apres_profile.season_label` | `unresolved` | Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up. |
| `stay_base:kitzbuhel-kitzbuhel` | `longitude` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `name` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `price_max` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `price_min` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `price_range` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `quality` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `regional_data_ids` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `stay_base_id` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:kitzbuhel` | `country` | `reviewed-no-change` |  |
| `stay_destination:kitzbuhel` | `latitude` | `reviewed-no-change` |  |
| `stay_destination:kitzbuhel` | `longitude` | `reviewed-no-change` |  |
| `stay_destination:kitzbuhel` | `name` | `changed` |  |
| `stay_destination:kitzbuhel` | `price_level` | `reviewed-no-change` |  |
| `stay_destination:kitzbuhel` | `region` | `reviewed-no-change` |  |
| `stay_destination:kitzbuhel` | `regional_data_ids` | `reviewed-no-change` |  |
| `stay_destination:kitzbuhel` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:kitzbuhel` | `trip_market_region_id` | `reviewed-no-change` |  |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `field_source_refs` | `changed` |  |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_regions:kitzbuhel` | `display_name` | `changed` |  |
| `trust_manifest:ski_regions:kitzbuhel` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_regions:kitzbuhel` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_regions:kitzbuhel` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:stay_destinations:kitzbuhel` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:kitzbuhel` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:kitzbuhel` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:kitzbuhel` | `notes` | `reviewed-no-change` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `ski_area:kitzbuhel-ski-area` | `name` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"Kitzbühel"` | Official ski-area page uses the Kitzbühel spelling. |  |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.advanced` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `{"black": 20, "blue": 94, "red": 67}` | Official FAQ lists 94 km blue, 67 km red, and 20 km black runs. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.beginner` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `{"black": 20, "blue": 94, "red": 67}` | Official FAQ lists 94 km blue, 67 km red, and 20 km black runs. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.intermediate` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `{"black": 20, "blue": 94, "red": 67}` | Official FAQ lists 94 km blue, 67 km red, and 20 km black runs. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:kitzbuhel-ski-area` | `supported_skill_levels` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"Kitzbühel"` | Official ski-area page uses the Kitzbühel spelling. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:kitzbuhel-ski-area` | `total_lift_count` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `58` | Official tourism page lists 58 gondolas and ski lifts. |  |
| `ski_area:kitzbuhel-ski-area` | `total_piste_km` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `{"black": 20, "blue": 94, "groomed_total_by_difficulty": 181, "red": 67}` | Official page lists blue/red/black groomed run kilometres that sum to 181 km. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `access_mode` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"from the heart of town, lifts connect directly to skiing"` | Official page says lifts connect directly from the heart of town to the ski area. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `distance_m` | [OpenStreetMap node 1685958015](https://www.openstreetmap.org/node/1685958015) | `{"station": [47.4432306, 12.3893632], "town_centroid": [47.4463585, 12.3911473]}` | OSM town centroid and Hahnenkammbahn valley-station node support an approximate walk distance of about 380 m. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `lift_distance` | [OpenStreetMap node 1685958015](https://www.openstreetmap.org/node/1685958015) | `"Hahnenkammbahn valley station in Kitzbühel"` | OSM places the Hahnenkammbahn station close to central Kitzbühel. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `nearest_lift_name` | [OpenStreetMap way 156335495](https://www.openstreetmap.org/way/156335495) | `"Hahnenkammbahn"` | OSM identifies the Hahnenkammbahn aerialway in Kitzbühel. |  |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `source_urls` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"from the heart of town, lifts connect directly to skiing"` | Official page says lifts connect directly from the heart of town to the ski area. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_region:kitzbuhel` | `name` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"Kitzbühel"` | Official tourism page uses the Kitzbühel spelling. |  |
| `stay_base:kitzbuhel-kitzbuhel` | `base_type` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"750-year-old town"` | Official page describes Kitzbühel as a historic town base. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:kitzbuhel-kitzbuhel` | `latitude` | [OpenStreetMap relation 85657](https://www.openstreetmap.org/relation/85657) | `47.4463585` | OSM administrative relation provides the Kitzbühel centroid latitude. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:kitzbuhel-kitzbuhel` | `longitude` | [OpenStreetMap relation 85657](https://www.openstreetmap.org/relation/85657) | `12.3911473` | OSM administrative relation provides the Kitzbühel centroid longitude. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:kitzbuhel-kitzbuhel` | `name` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"Kitzbühel"` | Official destination page uses the Kitzbühel spelling for the town stay base. |  |
| `stay_base:kitzbuhel-kitzbuhel` | `regional_data_ids` | [OpenStreetMap relation 85657](https://www.openstreetmap.org/relation/85657) | `{"osm_relation_id": "85657"}` | OSM relation id is stored for future regional-data joins. |  |
| `stay_destination:kitzbuhel` | `name` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"Kitzbühel"` | Official tourism page uses the Kitzbühel spelling. |  |
| `stay_destination:kitzbuhel` | `name` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"Kitzbühel"` | The normalized migration retains the already reviewed destination boundary. |  |

## Boundary Decisions

- `kitzbuhel`: `pass`

## Ranking Impact

Ranking-relevant facts now attach to the normalized ski-area, stay-base, and access-edge owners; Search V3 scoring policy is unchanged.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation typed REPORT.json --markdown-output REPORT.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation reconcile REPORT.json --base-catalog-path BASE/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json`

## Caveats

- Exact 2026/27 opening and closing dates remain unresolved; the reviewed KitzSki tariff sources provide date bands but not a full operating season window.
- Official Kitzbühel pages market 233 km of skiing and marked ski routes, while the official blue/red/black difficulty facts sum to 181 km; the catalog stores the difficulty-backed groomed piste total and keeps the broader marketed terrain visible as a caveat.
- Accommodation/rental price ranges and quality tiers remain product-curated estimates pending a reviewed provider sampling policy.
- Version-2-only fields were not assessed by the original version-1 curation and require source-backed follow-up.
