# Saalbach Hinterglemm Catalog Curation - normalized model migration

Migrates PR #15 onto the normalized Snowcast catalog. Facts are assigned to explicit regions, stay destinations, stay bases, ski areas, access edges, terrain domains, pass products, and rental facts.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:ski-alpin-card` | `full` | all canonical fields |
| `rental_display_fact:saalbach-hinterglemm-sport-hagleitner` | `full` | all canonical fields |
| `ski_area:saalbach-hinterglemm-ski-area` | `full` | all canonical fields |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `full` | all canonical fields |
| `ski_region:saalbach-hinterglemm` | `full` | all canonical fields |
| `stay_base:saalbach-hinterglemm-saalbach` | `full` | all canonical fields |
| `stay_destination:saalbach-hinterglemm` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:ski-alpin-card` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:saalbach-hinterglemm-ski-area` | `full` | all canonical fields |
| `trust_manifest:stay_bases:saalbach-hinterglemm-saalbach` | `full` | all canonical fields |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:ski-alpin-card` | `available_from_stay_destination_ids` | `["zell-am-see-kaprun"]` | `["saalbach-hinterglemm", "zell-am-see-kaprun"]` | `estimated` | no |
| `lift_pass_product:ski-alpin-card` | `default_for_stay_destination_ids` | `["zell-am-see-kaprun"]` | `["saalbach-hinterglemm", "zell-am-see-kaprun"]` | `estimated` | no |
| `lift_pass_product:ski-alpin-card` | `external_validity_summary` | `"Also valid beyond Zell am See-Kaprun in the Skicircus Saalbach Hinterglemm Leogang Fieberbrunn network."` | `"Valid across Skicircus Saalbach Hinterglemm Leogang Fieberbrunn and Zell am See-Kaprun terrain including Schmittenhöhe, Kitzsteinhorn, and Maiskogel."` | `estimated` | no |
| `lift_pass_product:ski-alpin-card` | `pass_accessible_terrain` | `null` | `{"metric_scope": "pass_accessible", "piste_km_by_difficulty": null, "source_urls": ["https://www.saalbach.com/en/winter/ski-resort", "https://www.saalbach.com/en/winter/skitickets/peak-season", "https://www.saalbach.com/en/winter/skitickets/skitickets-shlf"], "total_lift_count": 121, "total_piste_km": 408.0}` | `estimated` | no |
| `lift_pass_product:ski-alpin-card` | `prices` | `[{"amount": 396.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 440.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 74.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 82.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}]` | `[{"amount": 74.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 82.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 240.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 peak season", "source_url": "https://www.saalbach.com/en/winter/skitickets/peak-season"}, {"amount": 396.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 440.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}]` | `estimated` | no |
| `lift_pass_product:ski-alpin-card` | `valid_ski_area_ids` | `["kitzsteinhorn", "maiskogel", "schmittenhoehe"]` | `["kitzsteinhorn", "maiskogel", "saalbach-hinterglemm-ski-area", "schmittenhoehe"]` | `estimated` | no |
| `ski_area:saalbach-hinterglemm-ski-area` | `piste_km_by_difficulty.advanced` | `null` | `18.0` | `verified` | yes |
| `ski_area:saalbach-hinterglemm-ski-area` | `piste_km_by_difficulty.beginner` | `null` | `140.0` | `verified` | yes |
| `ski_area:saalbach-hinterglemm-ski-area` | `piste_km_by_difficulty.intermediate` | `null` | `112.0` | `verified` | yes |
| `ski_area:saalbach-hinterglemm-ski-area` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `ski_area:saalbach-hinterglemm-ski-area` | `season_windows` | `[]` | `[{"end_date": "2027-04-04", "season_label": "Winter 2026/27", "start_date": "2026-11-27", "status": "planned"}]` | `verified` | yes |
| `ski_area:saalbach-hinterglemm-ski-area` | `supported_skill_levels` | `["beginner", "intermediate"]` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:saalbach-hinterglemm-ski-area` | `total_lift_count` | `null` | `70` | `verified` | yes |
| `ski_area:saalbach-hinterglemm-ski-area` | `total_piste_km` | `null` | `270.0` | `verified` | yes |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `distance_m` | `null` | `300` | `verified_with_adjustment` | yes |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `nearest_lift_name` | `null` | `"Kohlmaisbahn / Schattberg X-Press"` | `verified_with_adjustment` | no |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `source_urls` | `["https://www.bergfex.com/saalbach-hinterglemm-leogang/"]` | `["https://www.bergfex.com/saalbach-hinterglemm-leogang/", "https://www.openstreetmap.org/node/240047212", "https://www.openstreetmap.org/way/120875813", "https://www.openstreetmap.org/way/989835855"]` | `verified_with_adjustment` | no |
| `stay_base:saalbach-hinterglemm-saalbach` | `atmosphere_tags` | `[]` | `["family_friendly", "apres_ski", "walkable_lifts"]` | `verified_with_adjustment` | no |
| `stay_base:saalbach-hinterglemm-saalbach` | `base_type` | `null` | `"resort_village"` | `verified_with_adjustment` | no |
| `stay_base:saalbach-hinterglemm-saalbach` | `latitude` | `null` | `47.3915` | `verified_with_adjustment` | no |
| `stay_base:saalbach-hinterglemm-saalbach` | `longitude` | `null` | `12.6364` | `verified_with_adjustment` | no |
| `stay_base:saalbach-hinterglemm-saalbach` | `regional_data_ids` | `{}` | `{"osm_node_id": "240047212"}` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:ski-alpin-card` | `field_statuses` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "verified_with_adjustment"}` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "estimated", "prices": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "estimated"}` | `estimated` | no |
| `trust_manifest:ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `source_refs` | `["https://www.bergfex.com/saalbach-hinterglemm-leogang/"]` | `["https://www.bergfex.com/saalbach-hinterglemm-leogang/", "https://www.openstreetmap.org/node/240047212", "https://www.openstreetmap.org/way/120875813", "https://www.openstreetmap.org/way/989835855"]` | `estimated` | no |
| `trust_manifest:ski_areas:saalbach-hinterglemm-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "identity_coordinates": "needs_source", "skill_fit": "estimated", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "identity_coordinates": "needs_source", "skill_fit": "estimated", "terrain_metrics": "verified"}` | `estimated` | no |
| `trust_manifest:ski_areas:saalbach-hinterglemm-ski-area` | `source_refs` | `[]` | `["https://www.saalbach.com/en/winter/ski-resort"]` | `estimated` | no |
| `trust_manifest:stay_bases:saalbach-hinterglemm-saalbach` | `field_statuses` | `{"atmosphere": "estimated", "coordinates": "needs_source", "identity_ownership": "needs_source", "lodging_price_quality": "estimated"}` | `{"atmosphere": "estimated", "coordinates": "verified_with_adjustment", "identity_ownership": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:saalbach-hinterglemm-saalbach` | `source_refs` | `[]` | `["https://www.openstreetmap.org/node/240047212", "https://www.saalbach.com/en/winter/ski-resort"]` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:ski-alpin-card` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:ski-alpin-card` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:ski-alpin-card` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:ski-alpin-card` | `lift_pass_product_id` | `reviewed-no-change` |  |
| `lift_pass_product:ski-alpin-card` | `name` | `reviewed-no-change` |  |
| `lift_pass_product:ski-alpin-card` | `pass_accessible_terrain` | `changed` |  |
| `lift_pass_product:ski-alpin-card` | `prices` | `changed` |  |
| `lift_pass_product:ski-alpin-card` | `terrain_domain_ids` | `reviewed-no-change` |  |
| `lift_pass_product:ski-alpin-card` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:ski-alpin-card` | `validity_scope` | `reviewed-no-change` |  |
| `rental_display_fact:saalbach-hinterglemm-sport-hagleitner` | `lift_distance` | `reviewed-no-change` |  |
| `rental_display_fact:saalbach-hinterglemm-sport-hagleitner` | `name` | `reviewed-no-change` |  |
| `rental_display_fact:saalbach-hinterglemm-sport-hagleitner` | `price_max` | `reviewed-no-change` |  |
| `rental_display_fact:saalbach-hinterglemm-sport-hagleitner` | `price_min` | `reviewed-no-change` |  |
| `rental_display_fact:saalbach-hinterglemm-sport-hagleitner` | `price_range` | `reviewed-no-change` |  |
| `rental_display_fact:saalbach-hinterglemm-sport-hagleitner` | `quality` | `reviewed-no-change` |  |
| `rental_display_fact:saalbach-hinterglemm-sport-hagleitner` | `rental_display_fact_id` | `reviewed-no-change` |  |
| `rental_display_fact:saalbach-hinterglemm-sport-hagleitner` | `stay_base_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `rental_display_fact:saalbach-hinterglemm-sport-hagleitner` | `stay_destination_id` | `reviewed-no-change` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `base_elevation_m` | `reviewed-no-change` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `name` | `reviewed-no-change` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `season_windows` | `changed` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `summit_elevation_m` | `reviewed-no-change` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `duration_minutes` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `is_direct` | `reviewed-no-change` |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `lift_distance` | `reviewed-no-change` |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `regional_data_ids` | `reviewed-no-change` |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `ski_area_access_id` | `reviewed-no-change` |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `stay_base_id` | `reviewed-no-change` |  |
| `ski_region:saalbach-hinterglemm` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:saalbach-hinterglemm` | `name` | `reviewed-no-change` |  |
| `ski_region:saalbach-hinterglemm` | `parent_ski_region_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `ski_region:saalbach-hinterglemm` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:saalbach-hinterglemm` | `source_urls` | `reviewed-no-change` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `atmosphere_tags` | `changed` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `base_type` | `changed` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `latitude` | `changed` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `longitude` | `changed` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `name` | `reviewed-no-change` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `price_max` | `reviewed-no-change` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `price_min` | `reviewed-no-change` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `price_range` | `reviewed-no-change` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `quality` | `reviewed-no-change` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `regional_data_ids` | `changed` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `stay_base_id` | `reviewed-no-change` |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:saalbach-hinterglemm` | `atmosphere_tags` | `reviewed-no-change` |  |
| `stay_destination:saalbach-hinterglemm` | `country` | `reviewed-no-change` |  |
| `stay_destination:saalbach-hinterglemm` | `latitude` | `reviewed-no-change` |  |
| `stay_destination:saalbach-hinterglemm` | `longitude` | `reviewed-no-change` |  |
| `stay_destination:saalbach-hinterglemm` | `name` | `reviewed-no-change` |  |
| `stay_destination:saalbach-hinterglemm` | `price_level` | `reviewed-no-change` |  |
| `stay_destination:saalbach-hinterglemm` | `region` | `reviewed-no-change` |  |
| `stay_destination:saalbach-hinterglemm` | `regional_data_ids` | `reviewed-no-change` |  |
| `stay_destination:saalbach-hinterglemm` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:saalbach-hinterglemm` | `trip_market_region_id` | `reviewed-no-change` |  |
| `trust_manifest:lift_pass_products:ski-alpin-card` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:lift_pass_products:ski-alpin-card` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:ski-alpin-card` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:lift_pass_products:ski-alpin-card` | `source_refs` | `reviewed-no-change` |  |
| `trust_manifest:ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `source_refs` | `changed` |  |
| `trust_manifest:ski_areas:saalbach-hinterglemm-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:saalbach-hinterglemm-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:saalbach-hinterglemm-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:saalbach-hinterglemm-ski-area` | `source_refs` | `changed` |  |
| `trust_manifest:stay_bases:saalbach-hinterglemm-saalbach` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:saalbach-hinterglemm-saalbach` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:saalbach-hinterglemm-saalbach` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:saalbach-hinterglemm-saalbach` | `source_refs` | `changed` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `ski_area:saalbach-hinterglemm-ski-area` | `piste_km_by_difficulty.advanced` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `{"advanced": 18.0, "beginner": 140.0, "intermediate": 112.0}` | Official page lists 140 km blue, 112 km red, and 18 km black slopes. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:saalbach-hinterglemm-ski-area` | `piste_km_by_difficulty.beginner` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `{"advanced": 18.0, "beginner": 140.0, "intermediate": 112.0}` | Official page lists 140 km blue, 112 km red, and 18 km black slopes. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:saalbach-hinterglemm-ski-area` | `piste_km_by_difficulty.intermediate` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `{"advanced": 18.0, "beginner": 140.0, "intermediate": 112.0}` | Official page lists 140 km blue, 112 km red, and 18 km black slopes. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:saalbach-hinterglemm-ski-area` | `season_start_month` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `11` | Official planned 2026/27 ski operation starts on 27 November 2026. |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `season_windows` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `[{"end_date": "2027-04-04", "season_label": "Winter 2026/27", "start_date": "2026-11-27", "status": "planned"}]` | Official page lists planned Skicircus ski operation from 27 November 2026 to 4 April 2027. |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `supported_skill_levels` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `11` | Official planned 2026/27 ski operation starts on 27 November 2026. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:saalbach-hinterglemm-ski-area` | `total_lift_count` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `70` | Official page lists 70 cableways and lifts. |  |
| `ski_area:saalbach-hinterglemm-ski-area` | `total_piste_km` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `270.0` | Official page lists 270 kilometres of ski slopes for Skicircus Saalbach Hinterglemm Leogang Fieberbrunn. |  |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `access_mode` | [OpenStreetMap way 989835855](https://www.openstreetmap.org/way/989835855) | `"Kohlmaisbahn in Saalbach"` | OSM places Kohlmaisbahn close to the Saalbach village node. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `distance_m` | [OpenStreetMap way 989835855](https://www.openstreetmap.org/way/989835855) | `{"kohlmaisbahn_talstation": [47.3920181, 12.6403194], "saalbach": [47.3914586, 12.6364473]}` | OSM village node and Kohlmaisbahn valley-station geometry support an approximate 300 m lift-access distance. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `nearest_lift_name` | [OpenStreetMap way 989835855](https://www.openstreetmap.org/way/989835855) | `"Kohlmaisbahn I"` | OSM identifies Kohlmaisbahn I at Saalbach. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area` | `source_urls` | [OpenStreetMap way 989835855](https://www.openstreetmap.org/way/989835855) | `"Kohlmaisbahn in Saalbach"` | OSM places Kohlmaisbahn close to the Saalbach village node. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:saalbach-hinterglemm-saalbach` | `atmosphere_tags` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `["family_friendly", "apres_ski", "walkable_lifts"]` | Official source emphasizes families, huts, varied winter activities, and village lift access. |  |
| `stay_base:saalbach-hinterglemm-saalbach` | `base_type` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `"Saalbach Hinterglemm"` | Official tourism context presents Saalbach as a resort village base in the Skicircus. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:saalbach-hinterglemm-saalbach` | `latitude` | [OpenStreetMap node 240047212](https://www.openstreetmap.org/node/240047212) | `47.3914586` | OSM place node provides the Saalbach village latitude. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:saalbach-hinterglemm-saalbach` | `longitude` | [OpenStreetMap node 240047212](https://www.openstreetmap.org/node/240047212) | `12.6364473` | OSM place node provides the Saalbach village longitude. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:saalbach-hinterglemm-saalbach` | `regional_data_ids` | [OpenStreetMap node 240047212](https://www.openstreetmap.org/node/240047212) | `{"osm_node_id": "240047212"}` | OSM node id is stored for future regional-data joins. |  |
| `stay_destination:saalbach-hinterglemm` | `name` | [Skicircus ski resort](https://www.saalbach.com/en/winter/ski-resort) | `"Saalbach Hinterglemm"` | The normalized migration retains the already reviewed destination boundary. |  |

## Boundary Decisions

- `saalbach-hinterglemm`: `pass`

## Ranking Impact

Ranking-relevant facts now attach to the normalized ski-area, stay-base, and access-edge owners; Search V3 scoring policy is unchanged.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation typed REPORT.json --markdown-output REPORT.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation reconcile REPORT.json --base-catalog-path BASE/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json`

## Caveats

- ALPIN CARD terrain-domain difficulty split is not populated because reviewed official sources provide aggregate 408 km / 121 lift totals but not an aggregate blue/red/black split for all three regions combined.
- Saalbach ski-area base/summit and weather coordinates were not changed in this sweep to avoid moving existing weather evidence without a dedicated evidence-migration decision.
- Accommodation/rental price ranges and quality tiers remain product-curated estimates pending a reviewed provider sampling policy.
