# Mayrhofen Full Static Catalog Curation - 2026-06-26 - normalized model migration

Migrates PR #16 onto the normalized Snowcast catalog. Facts are assigned to explicit regions, stay destinations, stay bases, ski areas, access edges, terrain domains, pass products, and rental facts.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `full` | all canonical fields |
| `rental_display_fact:mayrhofen-manni-rental` | `full` | all canonical fields |
| `ski_area:mayrhofen-ski-area` | `full` | all canonical fields |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `full` | all canonical fields |
| `ski_region:mayrhofen` | `full` | all canonical fields |
| `stay_base:mayrhofen-mayrhofen` | `full` | all canonical fields |
| `stay_destination:mayrhofen` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `full` | all canonical fields |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `full` | all canonical fields |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `available_from_stay_destination_ids` | `null` | `["mayrhofen"]` | `verified_with_adjustment` | no |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `default_for_stay_destination_ids` | `null` | `["mayrhofen"]` | `verified_with_adjustment` | no |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `external_validity_summary` | `null` | `"One-day Skipass Mayrhofen covers Mayrhofen, Eggalm, Rastkogel, Finkenberg, and Hintertux Glacier. Multi-day Zillertaler Superskipass covers all lifts in the Zillertal during the published 2026/27 main winter window. Wider Zillertal terrain is summarized here rather than copied into Mayrhofen's 142 km local ski-area metrics."` | `verified_with_adjustment` | no |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `lift_pass_product_id` | `null` | `"zillertaler-superskipass-mayrhofen"` | `verified_with_adjustment` | no |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `name` | `null` | `"Zillertaler Superskipass / Skipass Mayrhofen"` | `verified_with_adjustment` | no |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `prices` | `null` | `[{"amount": 241.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 Zillertaler Superskipass main window", "source_url": "https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter"}, {"amount": 399.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 Zillertaler Superskipass main window", "source_url": "https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter"}, {"amount": 82.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 Skipass Mayrhofen day ticket", "source_url": "https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter"}]` | `verified_with_adjustment` | no |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | no |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `valid_ski_area_ids` | `null` | `["mayrhofen-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.advanced` | `null` | `32.0` | `verified_with_adjustment` | yes |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.beginner` | `null` | `44.0` | `verified_with_adjustment` | yes |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.intermediate` | `null` | `66.0` | `verified_with_adjustment` | yes |
| `ski_area:mayrhofen-ski-area` | `season_windows` | `[]` | `[{"end_date": "2027-04-11", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:mayrhofen-ski-area` | `total_lift_count` | `null` | `61` | `verified_with_adjustment` | yes |
| `ski_area:mayrhofen-ski-area` | `total_piste_km` | `null` | `142.0` | `verified_with_adjustment` | yes |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `distance_m` | `null` | `490` | `verified_with_adjustment` | yes |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `lift_distance` | `"medium"` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `nearest_lift_name` | `null` | `"Penkenbahn"` | `verified_with_adjustment` | no |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `regional_data_ids` | `{}` | `{"nearest_lift_osm_node_id": "344469170"}` | `verified_with_adjustment` | no |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `source_urls` | `["https://www.bergfex.com/mayrhofen/"]` | `["https://www.bergfex.com/mayrhofen/", "https://www.openstreetmap.org/node/344469170", "https://www.openstreetmap.org/relation/80064"]` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `atmosphere_tags` | `[]` | `["central", "apres_ski", "walkable_lifts", "zillertal_access"]` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `base_type` | `null` | `"town"` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `latitude` | `null` | `47.1672` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `longitude` | `null` | `11.8639` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `regional_data_ids` | `{}` | `{"osm_relation_id": "80064"}` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `display_name` | `null` | `"Zillertaler Superskipass / Skipass Mayrhofen"` | `estimated` | no |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `notes` | `null` | `["PR #16 legacy curation was translated onto normalized catalog ownership and relationships."]` | `estimated` | no |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `source_refs` | `null` | `["https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html", "https://www.zillertal.at/en/winter/holidays/zillertal-superskipass.html"]` | `estimated` | no |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "estimated"}` | `estimated` | no |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `source_refs` | `["https://www.bergfex.com/mayrhofen/"]` | `["https://www.bergfex.com/mayrhofen/", "https://www.openstreetmap.org/node/344469170", "https://www.openstreetmap.org/relation/80064"]` | `estimated` | no |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "identity_coordinates": "needs_source", "skill_fit": "estimated", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "identity_coordinates": "needs_source", "skill_fit": "estimated", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `source_refs` | `[]` | `["https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"]` | `estimated` | no |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `field_statuses` | `{"atmosphere": "estimated", "coordinates": "needs_source", "identity_ownership": "needs_source", "lodging_price_quality": "estimated"}` | `{"atmosphere": "estimated", "coordinates": "verified_with_adjustment", "identity_ownership": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `source_refs` | `[]` | `["https://www.openstreetmap.org/relation/80064", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"]` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `name` | `changed` |  |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `pass_accessible_terrain` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `prices` | `changed` |  |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `validity_scope` | `changed` |  |
| `rental_display_fact:mayrhofen-manni-rental` | `lift_distance` | `reviewed-no-change` |  |
| `rental_display_fact:mayrhofen-manni-rental` | `name` | `reviewed-no-change` |  |
| `rental_display_fact:mayrhofen-manni-rental` | `price_max` | `reviewed-no-change` |  |
| `rental_display_fact:mayrhofen-manni-rental` | `price_min` | `reviewed-no-change` |  |
| `rental_display_fact:mayrhofen-manni-rental` | `price_range` | `reviewed-no-change` |  |
| `rental_display_fact:mayrhofen-manni-rental` | `quality` | `reviewed-no-change` |  |
| `rental_display_fact:mayrhofen-manni-rental` | `rental_display_fact_id` | `reviewed-no-change` |  |
| `rental_display_fact:mayrhofen-manni-rental` | `stay_base_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `rental_display_fact:mayrhofen-manni-rental` | `stay_destination_id` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `base_elevation_m` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `name` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `season_start_month` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `season_windows` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `summit_elevation_m` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `supported_skill_levels` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `duration_minutes` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `is_direct` | `reviewed-no-change` |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `ski_area_access_id` | `reviewed-no-change` |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `stay_base_id` | `reviewed-no-change` |  |
| `ski_region:mayrhofen` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:mayrhofen` | `name` | `reviewed-no-change` |  |
| `ski_region:mayrhofen` | `parent_ski_region_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `ski_region:mayrhofen` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:mayrhofen` | `source_urls` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `atmosphere_tags` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `base_type` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `latitude` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `longitude` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `name` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `price_max` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `price_min` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `price_range` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `quality` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `regional_data_ids` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `stay_base_id` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:mayrhofen` | `atmosphere_tags` | `reviewed-no-change` |  |
| `stay_destination:mayrhofen` | `country` | `reviewed-no-change` |  |
| `stay_destination:mayrhofen` | `latitude` | `reviewed-no-change` |  |
| `stay_destination:mayrhofen` | `longitude` | `reviewed-no-change` |  |
| `stay_destination:mayrhofen` | `name` | `reviewed-no-change` |  |
| `stay_destination:mayrhofen` | `price_level` | `reviewed-no-change` |  |
| `stay_destination:mayrhofen` | `region` | `reviewed-no-change` |  |
| `stay_destination:mayrhofen` | `regional_data_ids` | `reviewed-no-change` |  |
| `stay_destination:mayrhofen` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:mayrhofen` | `trip_market_region_id` | `reviewed-no-change` |  |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `notes` | `changed` |  |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `source_refs` | `changed` |  |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `source_refs` | `changed` |  |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `source_refs` | `changed` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `available_from_stay_destination_ids` | [Mayrhofner Bergbahnen prices and opening hours](https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter) | `"Zillertaler Superskipass / Skipass Mayrhofen"` | Official Mayrhofen page lists Skipass Mayrhofen and the Zillertaler Superskipass products. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `default_for_stay_destination_ids` | [Mayrhofner Bergbahnen prices and opening hours](https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter) | `"Zillertaler Superskipass / Skipass Mayrhofen"` | Official Mayrhofen page lists Skipass Mayrhofen and the Zillertaler Superskipass products. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `external_validity_summary` | [Zillertal Superskipass](https://www.zillertal.at/en/winter/holidays/zillertal-superskipass.html) | `"One-day Skipass Mayrhofen covers Mayrhofen, Eggalm, Rastkogel, Finkenberg, and Hintertux Glacier. Multi-day Zillertaler Superskipass covers all lifts in the Zillertal during the published 2026/27 main winter window. Wider Zillertal terrain is summarized here rather than copied into Mayrhofen's 142 km local ski-area metrics."` | Official Zillertal pass page publishes all-valley Zillertal Superskipass coverage and 2026/27 tariffs; Mayrhofen pricing page states the same main winter validity window. | External validity summary avoids copying the all-valley aggregate terrain into Mayrhofen's local ski-area metrics. |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `lift_pass_product_id` | [Mayrhofner Bergbahnen prices and opening hours](https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter) | `"Zillertaler Superskipass / Skipass Mayrhofen"` | Official Mayrhofen page lists Skipass Mayrhofen and the Zillertaler Superskipass products. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `name` | [Mayrhofner Bergbahnen prices and opening hours](https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter) | `"Zillertaler Superskipass / Skipass Mayrhofen"` | Official Mayrhofen page lists Skipass Mayrhofen and the Zillertaler Superskipass products. |  |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `prices` | [Mayrhofner Bergbahnen prices and opening hours](https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter) | `[{"amount": 82.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 Skipass Mayrhofen day ticket", "source_url": "https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 Zillertaler Superskipass main window", "source_url": "https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter"}, {"amount": 399.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 Zillertaler Superskipass main window", "source_url": "https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter"}]` | Official Mayrhofen price table lists adult 1-day Skipass Mayrhofen at EUR 82 and adult Zillertaler Superskipass 3-day/6-day prices at EUR 241/EUR 399. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `terrain_domain_ids` | [Mayrhofner Bergbahnen prices and opening hours](https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter) | `"Zillertaler Superskipass / Skipass Mayrhofen"` | Official Mayrhofen page lists Skipass Mayrhofen and the Zillertaler Superskipass products. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `valid_ski_area_ids` | [Mayrhofner Bergbahnen - Mountopolis](https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html) | `["mayrhofen-ski-area"]` | The only first-class local ski-area entity under the Mayrhofen destination is the Mountopolis/Mayrhofen ski area. |  |
| `lift_pass_product:zillertaler-superskipass-mayrhofen` | `validity_scope` | [Mayrhofner Bergbahnen prices and opening hours](https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter) | `"regional_network"` | Official pricing page states Skipass Mayrhofen validity across local Zillertal 3000 areas and Zillertaler Superskipass validity across all Zillertal lifts. | Normalized to regional_network because the pass validity extends beyond the single modeled Mayrhofen ski area. |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.advanced` | [Skiresort.info Mayrhofen Mountopolis](https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/) | `{"advanced": 32.0, "beginner": 44.0, "intermediate": 66.0}` | Reviewed ski-resort listing provides the easy/intermediate/difficult piste split as 44/66/32 km. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.beginner` | [Skiresort.info Mayrhofen Mountopolis](https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/) | `{"advanced": 32.0, "beginner": 44.0, "intermediate": 66.0}` | Reviewed ski-resort listing provides the easy/intermediate/difficult piste split as 44/66/32 km. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.intermediate` | [Skiresort.info Mayrhofen Mountopolis](https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/) | `{"advanced": 32.0, "beginner": 44.0, "intermediate": 66.0}` | Reviewed ski-resort listing provides the easy/intermediate/difficult piste split as 44/66/32 km. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:mayrhofen-ski-area` | `season_windows` | [Mayrhofner Bergbahnen - Mountopolis](https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html) | `[{"end_date": "2027-04-11", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | Official operating-period table supports the Mayrhofen ski-area 2026/27 window. |  |
| `ski_area:mayrhofen-ski-area` | `total_lift_count` | [Mayrhofner Bergbahnen - Mountopolis](https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html) | `61` | Official Zillertal page states 61 modern lifts in the Mountopolis ski area. |  |
| `ski_area:mayrhofen-ski-area` | `total_piste_km` | [Mayrhofner Bergbahnen - Mountopolis](https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html) | `142.0` | Official Zillertal page states 142 kilometres of pistes in the Mountopolis ski area. |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `access_mode` | [OpenStreetMap Penkenbahn station](https://www.openstreetmap.org/node/344469170) | `"walk"` | Penkenbahn is within roughly 500 m of the reviewed Mayrhofen town reference point, supporting walk access. |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `distance_m` | [OpenStreetMap Penkenbahn station](https://www.openstreetmap.org/node/344469170) | `490` | Mayrhofen OSM relation center to Penkenbahn station is about 488 m by haversine distance. | Rounded to the nearest ten metres for catalog stability. |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `lift_distance` | [OpenStreetMap Penkenbahn station](https://www.openstreetmap.org/node/344469170) | `"near"` | OSM Penkenbahn station is approximately 490 m from the Mayrhofen OSM relation center, supporting a near lift-distance bucket. | Distance bucket derived from OSM coordinates and rounded haversine distance. |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `nearest_lift_name` | [OpenStreetMap Penkenbahn station](https://www.openstreetmap.org/node/344469170) | `"Penkenbahn"` | OSM identifies the nearby aerialway station as Penkenbahn. |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `regional_data_ids` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `{"nearest_lift_osm_node_id": "344469170", "osm_relation_id": "80064"}` | OSM relation 80064 and Penkenbahn station node 344469170 anchor the stay-base and nearest-lift references. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `source_urls` | [OpenStreetMap Penkenbahn station](https://www.openstreetmap.org/node/344469170) | `"walk"` | Penkenbahn is within roughly 500 m of the reviewed Mayrhofen town reference point, supporting walk access. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:mayrhofen-mayrhofen` | `atmosphere_tags` | [Mayrhofner Bergbahnen - Mountopolis](https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html) | `["central", "apres_ski", "walkable_lifts", "zillertal_access"]` | Official resort page highlights family/beginner terrain on Ahorn, action terrain on Penken, and Zillertal pass access; OSM access supports walkable_lifts. | Atmosphere tags are normalized Snowcast editorial labels derived from reviewed official/open sources. |
| `stay_base:mayrhofen-mayrhofen` | `base_type` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `"town"` | OSM classifies Mayrhofen as a town-level administrative/place entity. |  |
| `stay_base:mayrhofen-mayrhofen` | `latitude` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `47.1672` | OSM relation 80064 provides Mayrhofen coordinates used for stay-base enrichment. | Rounded OSM latitude 47.1672188 to four decimals. |
| `stay_base:mayrhofen-mayrhofen` | `longitude` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `11.8639` | OSM relation 80064 provides Mayrhofen coordinates used for stay-base enrichment. | Rounded OSM longitude 11.8638664 to four decimals. |
| `stay_base:mayrhofen-mayrhofen` | `regional_data_ids` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `{"nearest_lift_osm_node_id": "344469170", "osm_relation_id": "80064"}` | OSM relation 80064 and Penkenbahn station node 344469170 anchor the stay-base and nearest-lift references. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_destination:mayrhofen` | `name` | [Mayrhofner Bergbahnen - Mountopolis](https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html) | `"Mayrhofen"` | The normalized migration retains the already reviewed destination boundary. |  |

## Boundary Decisions

- `mayrhofen`: `pass`

## Ranking Impact

Ranking-relevant facts now attach to the normalized ski-area, stay-base, and access-edge owners; Search V3 scoring policy is unchanged.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation typed REPORT.json --markdown-output REPORT.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation reconcile REPORT.json --base-catalog-path BASE/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json`

## Caveats

- MANNI Rental is externally verified, but reviewed MANNI sources did not expose a current price table; rental price_range and rental_quality_tier remain estimated.
- The Zillertaler Superskipass covers a broader 546 km Zillertal network; this pass validity is summarized without adding a shared terrain domain because most covered ski areas are not modeled as first-class catalog destinations.
