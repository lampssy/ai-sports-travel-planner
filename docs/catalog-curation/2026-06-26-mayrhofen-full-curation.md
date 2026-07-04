# Mayrhofen Full Static Catalog Curation - 2026-06-26 - normalized model migration

Migrates PR #16 onto the normalized Snowcast catalog. Facts are assigned to explicit regions, stay destinations, stay bases, ski areas, access edges, terrain domains, pass products, and rental facts. Source-aware v2 enrichment follow-up: Reviewed Mayrhofen and Mountopolis facts against official destination and lift-company sources. Added snowmaking, PenkenPark, the direct official trail map, ski-day apres, village elevation, mixed character, lively pace, and local apres while retaining unsupported glacier terrain, public night skiing, and marked freeride-route values as unknown.

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
| `ski_area:mayrhofen-ski-area` | `official_trail_map.season_label` | `null` | `"2025/26"` | `verified` | no |
| `ski_area:mayrhofen-ski-area` | `official_trail_map.url` | `null` | `"https://images.contenthub.dev/390osprlshgj/57d055309f846c1d65a0ad341ee3f426/2025-26_MBB_Pano_MBB_LEGENDE_EN.jpg"` | `verified` | no |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.advanced` | `null` | `32.0` | `verified_with_adjustment` | yes |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.beginner` | `null` | `44.0` | `verified_with_adjustment` | yes |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.intermediate` | `null` | `66.0` | `verified_with_adjustment` | yes |
| `ski_area:mayrhofen-ski-area` | `season_windows` | `[]` | `[{"end_date": "2027-04-11", "season_label": "Winter 2026/27", "start_date": "2026-12-04", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `ski_area:mayrhofen-ski-area` | `snow_park.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:mayrhofen-ski-area` | `snow_park.park_count` | `null` | `1` | `verified` | no |
| `ski_area:mayrhofen-ski-area` | `snowmaking.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:mayrhofen-ski-area` | `total_lift_count` | `null` | `61` | `verified_with_adjustment` | yes |
| `ski_area:mayrhofen-ski-area` | `total_piste_km` | `null` | `142.0` | `verified_with_adjustment` | yes |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `distance_m` | `null` | `490` | `verified_with_adjustment` | yes |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `lift_distance` | `"medium"` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `nearest_lift_name` | `null` | `"Penkenbahn"` | `verified_with_adjustment` | no |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `regional_data_ids` | `{}` | `{"nearest_lift_osm_node_id": "344469170"}` | `verified_with_adjustment` | no |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `source_urls` | `["https://www.bergfex.com/mayrhofen/"]` | `["https://www.bergfex.com/mayrhofen/", "https://www.openstreetmap.org/node/344469170", "https://www.openstreetmap.org/relation/80064"]` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `base_character.development_style` | `"unknown"` | `"mixed"` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `base_character.local_pace` | `"unknown"` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `base_type` | `null` | `"town"` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `elevation_m` | `null` | `630` | `verified` | no |
| `stay_base:mayrhofen-mayrhofen` | `latitude` | `null` | `47.1672` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.availability` | `"unknown"` | `"available"` | `verified` | no |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `longitude` | `null` | `11.8639` | `verified_with_adjustment` | no |
| `stay_base:mayrhofen-mayrhofen` | `regional_data_ids` | `{}` | `{"osm_relation_id": "80064"}` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `display_name` | `null` | `"Zillertaler Superskipass / Skipass Mayrhofen"` | `estimated` | no |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `field_source_refs` | `null` | `{"coverage": ["https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html", "https://www.zillertal.at/en/winter/holidays/zillertal-superskipass.html"], "identity_scope_availability": ["https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html", "https://www.zillertal.at/en/winter/holidays/zillertal-superskipass.html"], "pass_accessible_terrain": ["https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html", "https://www.zillertal.at/en/winter/holidays/zillertal-superskipass.html"], "prices": ["https://www.mayrhofen.at/en/stories/mountopolis-prices-and-opening-hours-winter", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html", "https://www.zillertal.at/en/winter/holidays/zillertal-superskipass.html"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `notes` | `null` | `["PR #16 legacy curation was translated onto normalized catalog ownership and relationships."]` | `estimated` | no |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/mayrhofen/"], "relationship": ["https://www.bergfex.com/mayrhofen/"]}` | `{"access_mode_distance": ["https://www.bergfex.com/mayrhofen/", "https://www.openstreetmap.org/node/344469170", "https://www.openstreetmap.org/relation/80064"], "relationship": ["https://www.bergfex.com/mayrhofen/", "https://www.openstreetmap.org/node/344469170", "https://www.openstreetmap.org/relation/80064"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "estimated"}` | `estimated` | no |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"], "glacier_terrain": [], "identity_coordinates": ["https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"], "marked_freeride_routes": [], "night_skiing": [], "official_documents": ["https://images.contenthub.dev/390osprlshgj/57d055309f846c1d65a0ad341ee3f426/2025-26_MBB_Pano_MBB_LEGENDE_EN.jpg"], "ski_day_apres": ["https://www.mayrhofen.at/de/service-providers/kasermandl-penken-1800m-penken"], "skill_fit": ["https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"], "snow_park": ["https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter"], "snowmaking": ["https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter"], "terrain_metrics": ["https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"]}` | `estimated` | no |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "verified", "ski_day_apres": "verified_with_adjustment", "skill_fit": "estimated", "snow_park": "verified", "snowmaking": "verified", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner.", "Source-aware v2 enrichment reviewed official Mayrhofner Bergbahnen sources on 2026-07-04.", "Hintertux glacier access was kept separate from the modeled non-glacier Mayrhofen ski area."]` | `needs_source` | no |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `{"base_character": ["https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal"], "base_type": [], "coordinates": ["https://www.openstreetmap.org/relation/80064", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"], "elevation": ["https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal"], "identity_ownership": ["https://www.openstreetmap.org/relation/80064", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"], "local_apres": ["https://www.mayrhofen.at/de/service-providers/yeti-bar", "https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal"], "lodging_price_quality": ["https://www.openstreetmap.org/relation/80064", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"]}` | `estimated` | no |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `{"base_character": "verified_with_adjustment", "base_type": "needs_source", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "needs_source", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner.", "Source-aware v2 enrichment reviewed official Mayrhofen elevation, identity, and apres sources on 2026-07-04."]` | `needs_source` | no |

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
| `ski_area:mayrhofen-ski-area` | `glacier_terrain.availability` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `marked_freeride_routes.availability` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `marked_freeride_routes.route_count` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `marked_freeride_routes.season_label` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `name` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `night_skiing.availability` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `night_skiing.season_label` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `official_trail_map.season_label` | `changed` | The official map is explicitly labeled 2025/26. |
| `ski_area:mayrhofen-ski-area` | `official_trail_map.url` | `changed` | Direct official Mountopolis ski-map image. |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `season_start_month` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `season_windows` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.availability` | `changed` | The official destination listing documents a dedicated apres venue on Penken. |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.intensity` | `changed` | The on-mountain venue advertises legendary parties, a dance floor, music, and active celebration. |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.season_label` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `snow_park.availability` | `changed` | The official operator presents PenkenPark as the ski area's dedicated snowpark. |
| `ski_area:mayrhofen-ski-area` | `snow_park.park_count` | `changed` | The scoped operator inventory names one dedicated snowpark, PenkenPark. |
| `ski_area:mayrhofen-ski-area` | `snow_park.season_label` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `snowmaking.availability` | `changed` | The official operator explicitly credits cutting-edge snowmaking technology for December-to-April conditions. |
| `ski_area:mayrhofen-ski-area` | `snowmaking.coverage_basis` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `snowmaking.coverage_pct` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `snowmaking.season_label` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
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
| `stay_base:mayrhofen-mayrhofen` | `base_character.development_style` | `changed` | The official profile explicitly says strong traditions and modernity coexist, from farmhouses to luxury hotels. |
| `stay_base:mayrhofen-mayrhofen` | `base_character.local_pace` | `changed` | The official profile positions Mayrhofen as an Alpine tourism flagship combining fun, action, hospitality, and a busy town offer. |
| `stay_base:mayrhofen-mayrhofen` | `base_type` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `elevation_m` | `changed` | The official town profile places Mayrhofen at 630 m. |
| `stay_base:mayrhofen-mayrhofen` | `latitude` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.availability` | `changed` | The official directory includes established central and lift-base apres venues. |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.intensity` | `changed` | Yeti Bar is described as a pulsating daily ski-season party venue, supported by a broader nightlife inventory. |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.season_label` | `unresolved` | Official Mayrhofen destination sources were reviewed, but they did not establish this exact stay-base value; it remains unknown rather than being inferred. |
| `stay_base:mayrhofen-mayrhofen` | `longitude` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `name` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `price_max` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `price_min` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `price_range` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `quality` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `regional_data_ids` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `stay_base_id` | `reviewed-no-change` |  |
| `stay_base:mayrhofen-mayrhofen` | `stay_destination_id` | `reviewed-no-change` |  |
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
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `field_source_refs` | `changed` |  |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:zillertaler-superskipass-mayrhofen` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `notes` | `changed` |  |

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
| `stay_base:mayrhofen-mayrhofen` | `base_type` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `"town"` | OSM classifies Mayrhofen as a town-level administrative/place entity. |  |
| `stay_base:mayrhofen-mayrhofen` | `latitude` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `47.1672` | OSM relation 80064 provides Mayrhofen coordinates used for stay-base enrichment. | Rounded OSM latitude 47.1672188 to four decimals. |
| `stay_base:mayrhofen-mayrhofen` | `longitude` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `11.8639` | OSM relation 80064 provides Mayrhofen coordinates used for stay-base enrichment. | Rounded OSM longitude 11.8638664 to four decimals. |
| `stay_base:mayrhofen-mayrhofen` | `regional_data_ids` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `{"nearest_lift_osm_node_id": "344469170", "osm_relation_id": "80064"}` | OSM relation 80064 and Penkenbahn station node 344469170 anchor the stay-base and nearest-lift references. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_destination:mayrhofen` | `name` | [Mayrhofner Bergbahnen - Mountopolis](https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html) | `"Mayrhofen"` | The normalized migration retains the already reviewed destination boundary. |  |
| `ski_area:mayrhofen-ski-area` | `official_trail_map.season_label` | [Mountopolis official ski map 2025/26](https://images.contenthub.dev/390osprlshgj/57d055309f846c1d65a0ad341ee3f426/2025-26_MBB_Pano_MBB_LEGENDE_EN.jpg) | `"2025/26"` | The official map is explicitly labeled 2025/26. |  |
| `ski_area:mayrhofen-ski-area` | `official_trail_map.url` | [Mountopolis official ski map 2025/26](https://images.contenthub.dev/390osprlshgj/57d055309f846c1d65a0ad341ee3f426/2025-26_MBB_Pano_MBB_LEGENDE_EN.jpg) | `"https://images.contenthub.dev/390osprlshgj/57d055309f846c1d65a0ad341ee3f426/2025-26_MBB_Pano_MBB_LEGENDE_EN.jpg"` | Direct official Mountopolis ski-map image. |  |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.availability` | [Kasermandl Penken apres-ski](https://www.mayrhofen.at/de/service-providers/kasermandl-penken-1800m-penken) | `"available"` | The official destination listing documents a dedicated apres venue on Penken. |  |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.intensity` | [Kasermandl Penken apres-ski](https://www.mayrhofen.at/de/service-providers/kasermandl-penken-1800m-penken) | `"lively"` | The on-mountain venue advertises legendary parties, a dance floor, music, and active celebration. | The explicit party-oriented venue is mapped to lively. |
| `ski_area:mayrhofen-ski-area` | `snow_park.availability` | [Mountopolis winter](https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter) | `"available"` | The official operator presents PenkenPark as the ski area's dedicated snowpark. |  |
| `ski_area:mayrhofen-ski-area` | `snow_park.park_count` | [Mountopolis winter](https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter) | `1` | The scoped operator inventory names one dedicated snowpark, PenkenPark. |  |
| `ski_area:mayrhofen-ski-area` | `snowmaking.availability` | [Mountopolis winter](https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter) | `"available"` | The official operator explicitly credits cutting-edge snowmaking technology for December-to-April conditions. |  |
| `stay_base:mayrhofen-mayrhofen` | `base_character.development_style` | [Mayrhofen in Zillertal](https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal) | `"mixed"` | The official profile explicitly says strong traditions and modernity coexist, from farmhouses to luxury hotels. | The explicit traditional-modern blend is mapped to mixed. |
| `stay_base:mayrhofen-mayrhofen` | `base_character.local_pace` | [Mayrhofen in Zillertal](https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal) | `"lively"` | The official profile positions Mayrhofen as an Alpine tourism flagship combining fun, action, hospitality, and a busy town offer. | The broad active resort-town offer is mapped to lively. |
| `stay_base:mayrhofen-mayrhofen` | `elevation_m` | [Mayrhofen in Zillertal](https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal) | `630` | The official town profile places Mayrhofen at 630 m. |  |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.availability` | [Yeti Bar apres-ski](https://www.mayrhofen.at/de/service-providers/yeti-bar) | `"available"` | The official directory includes established central and lift-base apres venues. |  |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.intensity` | [Yeti Bar apres-ski](https://www.mayrhofen.at/de/service-providers/yeti-bar) | `"lively"` | Yeti Bar is described as a pulsating daily ski-season party venue, supported by a broader nightlife inventory. | The official party-oriented venue evidence is mapped to lively. |

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
- Source-aware v2 enrichment follow-up: The official operator promises snowmaking-supported conditions but publishes no exact coverage percentage.
- Source-aware v2 enrichment follow-up: The modeled ski area does not include Hintertux glacier terrain even though wider pass products may provide access there.
- Source-aware v2 enrichment follow-up: The operator explicitly closes slopes outside normal operating times, and no public night-skiing offer was established.
