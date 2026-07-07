# KitzSki and Kitzbühel Catalog Curation - normalized model migration

Migrates PR #14 onto the normalized Snowcast catalog and the schema-version-2 entity-scope contract. The retained ski-area ID is displayed as KitzSki; Kirchberg and Jochberg are added as independent stay destinations with village bases, direct access edges, and KitzSki pass availability. Pengelstein, Jochberg, Pass Thurn, and Resterhöhe remain connected sectors of the retained terrain owner. Disconnected local terrain and the remaining western accommodation markets are explicitly deferred through one regional backlog item because they require a weather-owner and aggregate-metric migration.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:kitzski-skipass` | `full` | all canonical fields |
| `rental_display_fact:kitzbuhel-element3-sport-noichl` | `full` | all canonical fields |
| `ski_area:kitzbuhel-ski-area` | `full` | all canonical fields |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `full` | all canonical fields |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `full` | all canonical fields |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `full` | all canonical fields |
| `ski_region:kitzbuhel` | `full` | all canonical fields |
| `stay_base:jochberg-jochberg` | `full` | all canonical fields |
| `stay_base:kirchberg-kirchberg` | `full` | all canonical fields |
| `stay_base:kitzbuhel-kitzbuhel` | `full` | all canonical fields |
| `stay_destination:jochberg` | `full` | all canonical fields |
| `stay_destination:kirchberg` | `full` | all canonical fields |
| `stay_destination:kitzbuhel` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_regions:kitzbuhel` | `full` | all canonical fields |
| `trust_manifest:stay_bases:jochberg-jochberg` | `full` | all canonical fields |
| `trust_manifest:stay_bases:kirchberg-kirchberg` | `full` | all canonical fields |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:jochberg` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:kirchberg` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:kitzbuhel` | `full` | all canonical fields |

## Entity Scope Assessments

| Candidate | Kind | Disposition | Signals | Catalog Targets | Evidence | Backlog | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `kitzbuhel-destination` (Kitzbühel) | `stay_destination` | `represented` | `independent_stay_market`, `direct_access_relationship` | `stay_destination:kitzbuhel` | `boundary-kitzbuhel` |  | The existing Kitzbühel stay destination remains the premium town accommodation market. |
| `kitzbuhel-base` (Kitzbühel town base) | `stay_base` | `represented` | `independent_stay_market`, `direct_access_relationship` | `stay_base:kitzbuhel-kitzbuhel` | `delta-23` |  | The existing town base owns Kitzbühel lodging character and Hahnenkammbahn access context. |
| `kitzski-terrain-owner` (KitzSki) | `ski_area` | `represented` | `official_independent_identity`, `ski_connected_terrain` | `ski_area:kitzbuhel-ski-area` | `scope-kitzski-owner` |  | The stable ski-area ID is retained and displayed as KitzSki for the current shared terrain and weather owner. |
| `kitzbuhel-kitzski-access` (Kitzbühel to KitzSki access) | `ski_area_access` | `represented` | `direct_access_relationship`, `distinct_access` | `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `delta-19` |  | The existing Hahnenkammbahn edge represents Kitzbühel town access to KitzSki. |
| `kitzski-pass` (KitzSki Ski Pass) | `lift_pass_product` | `represented` | `official_product_identity` | `lift_pass_product:kitzski-skipass` | `pass-kitzski-name` |  | The official KitzSki ticket remains the modeled pass product for all three in-scope stay destinations. |
| `jochberg` (Jochberg) | `stay_destination` | `add_entity` | `independent_stay_market`, `direct_access_relationship` | `stay_destination:jochberg` | `boundary-jochberg` |  | Jochberg is a bookable, quieter village market with direct Wagstättbahn access and independent recommendation value. |
| `jochberg-base` (Jochberg village base) | `stay_base` | `add_entity` | `independent_stay_market`, `direct_access_relationship` | `stay_base:jochberg-jochberg` | `new-jochberg-jochberg-stay_base_id` |  | The named village is the representative accommodation base for the new Jochberg destination. |
| `jochberg-kitzski-access` (Jochberg to KitzSki access) | `ski_area_access` | `add_entity` | `direct_access_relationship`, `distinct_access` | `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `new-jochberg-jochberg--kitzbuhel-ski-area-ski_area_access_id` |  | Wagstättbahn provides a source-backed walkable edge from Jochberg village into KitzSki. |
| `kirchberg` (Kirchberg in Tirol) | `stay_destination` | `add_entity` | `independent_stay_market`, `direct_access_relationship` | `stay_destination:kirchberg` | `boundary-kirchberg` |  | Kirchberg is a large bookable village market with its own atmosphere and direct KitzSki lift and ski-bus access. |
| `kirchberg-base` (Kirchberg village base) | `stay_base` | `add_entity` | `independent_stay_market`, `direct_access_relationship` | `stay_base:kirchberg-kirchberg` | `new-kirchberg-kirchberg-stay_base_id` |  | The named village is the representative accommodation base for the new Kirchberg destination. |
| `kirchberg-kitzski-access` (Kirchberg to KitzSki access) | `ski_area_access` | `add_entity` | `direct_access_relationship`, `distinct_access` | `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `new-kirchberg-kirchberg--kitzbuhel-ski-area-ski_area_access_id` |  | Official sources document Fleckalmbahn entry and free ski buses from Kirchberg accommodation to KitzSki valley stations. |
| `pengelstein-sector` (Pengelstein) | `ski_area` | `not_separate` | `official_map_sector`, `ski_connected_terrain` | `ski_area:kitzbuhel-ski-area` | `scope-kitzski-connected-sectors` |  | Pengelstein is a connected KitzSki sector without a stronger independent terrain-owner signal. |
| `jochberg-sector` (Jochberg terrain sector) | `ski_area` | `not_separate` | `official_map_sector`, `ski_connected_terrain` | `ski_area:kitzbuhel-ski-area` | `scope-kitzski-connected-sectors` |  | Jochberg is a separate stay destination but its terrain is lift-connected to the retained KitzSki owner. |
| `pass-thurn-sector` (Pass Thurn and Resterhöhe sectors) | `ski_area` | `not_separate` | `official_map_sector`, `ski_connected_terrain` | `ski_area:kitzbuhel-ski-area` | `scope-kitzski-connected-sectors` |  | Pass Thurn and Resterhöhe are connected KitzSki sectors; their limited products do not independently establish ski areas. |
| `kitzbuheler-horn` (Kitzbüheler Horn) | `ski_area` | `deferred` | `official_independent_identity`, `full_local_pass`, `disconnected_terrain` |  | `scope-kitzski-disconnected-terrain` | `docs/product-backlog.md#kitzski-regional-extension` | The standalone Horn merits a separate owner review, but adding it now would require re-scoping the retained weather identity and KitzSki-wide metrics. |
| `gaisberg-kirchberg` (Gaisberg) | `ski_area` | `deferred` | `limited_area_ticket`, `disconnected_terrain`, `distinct_access` |  | `scope-kitzski-disconnected-terrain` | `docs/product-backlog.md#kitzski-regional-extension` | Gaisberg has distinct local access and special-ticket context, but its weather and alpine-skiing ownership need a focused migration. |
| `bichlalm` (Bichlalm) | `ski_area` | `deferred` | `limited_area_ticket`, `disconnected_terrain`, `distinct_access` |  | `scope-kitzski-disconnected-terrain` | `docs/product-backlog.md#kitzski-regional-extension` | Bichlalm is a separate touring/access context whose weather ownership should be handled with the other disconnected KitzSki terrain. |
| `mittersill` (Mittersill) | `stay_destination` | `deferred` | `independent_stay_market`, `distinct_access` |  | `scope-kitzski-western-markets` | `docs/product-backlog.md#kitzski-regional-extension` | Mittersill is a concrete western KitzSki stay-market extension, but adding it would exceed this three-destination batch. |
| `hollersbach` (Hollersbach) | `stay_destination` | `deferred` | `independent_stay_market`, `direct_access_relationship` |  | `scope-kitzski-western-markets` | `docs/product-backlog.md#kitzski-regional-extension` | Hollersbach has Panoramabahn access and a concrete stay market, but it belongs in the separate western KitzSki curation batch. |
| `mittersill-pass-thurn` (Pass Thurn stay base) | `stay_base` | `deferred` | `independent_stay_market`, `distinct_access` |  | `scope-kitzski-western-markets` | `docs/product-backlog.md#kitzski-regional-extension` | Pass Thurn is a named accommodation/access base that depends on the deferred Mittersill destination graph. |
| `hollersbach-hollersbach` (Hollersbach village base) | `stay_base` | `deferred` | `independent_stay_market`, `direct_access_relationship` |  | `scope-kitzski-western-markets` | `docs/product-backlog.md#kitzski-regional-extension` | The village base and Panoramabahn edge depend on the deferred Hollersbach destination curation. |
| `reith-bei-kitzbuhel` (Reith bei Kitzbühel) | `stay_destination` | `unresolved` | `independent_stay_market`, `distinct_access` |  | `scope-kitzbuhel-region-villages` | `docs/product-backlog.md#kitzski-regional-extension` | Official sources confirm lodging identity, but the independent stable-ski-access and recommendation boundary need a focused review. |
| `aurach-bei-kitzbuhel` (Aurach bei Kitzbühel) | `stay_destination` | `unresolved` | `independent_stay_market`, `distinct_access` |  | `scope-kitzbuhel-region-villages` | `docs/product-backlog.md#kitzski-regional-extension` | Official sources confirm lodging identity, but a source-backed direct access edge and independent recommendation boundary remain unresolved. |
| `kirchberg-aschau` (Aschau im Spertental) | `stay_base` | `deferred` | `independent_stay_market`, `distinct_access` |  | `scope-kitzski-western-markets` | `docs/product-backlog.md#kitzski-regional-extension` | Aschau is a named accommodation village within Kirchberg, but adding its access edge belongs in the broader regional extension. |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:kitzski-skipass` | `available_from_stay_destination_ids` | `null` | `["jochberg", "kirchberg", "kitzbuhel"]` | `verified_with_adjustment` | no |
| `lift_pass_product:kitzski-skipass` | `default_for_stay_destination_ids` | `null` | `["jochberg", "kirchberg", "kitzbuhel"]` | `estimated` | no |
| `lift_pass_product:kitzski-skipass` | `lift_pass_product_id` | `null` | `"kitzski-skipass"` | `verified` | no |
| `lift_pass_product:kitzski-skipass` | `name` | `null` | `"KitzSki Ski Pass"` | `verified` | no |
| `lift_pass_product:kitzski-skipass` | `prices` | `null` | `[{"amount": 83.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 premium season cash desk", "source_url": "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"}, {"amount": 244.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 premium season cash desk", "source_url": "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"}, {"amount": 423.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 premium season cash desk", "source_url": "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"}]` | `verified` | no |
| `lift_pass_product:kitzski-skipass` | `terrain_domain_ids` | `null` | `[]` | `estimated` | no |
| `lift_pass_product:kitzski-skipass` | `valid_ski_area_ids` | `null` | `["kitzbuhel-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:kitzski-skipass` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | no |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.route_count` | `null` | `12` | `verified` | no |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.season_label` | `null` | `"2025/26"` | `verified` | no |
| `ski_area:kitzbuhel-ski-area` | `name` | `"Kitzbuhel"` | `"KitzSki"` | `verified_with_adjustment` | no |
| `ski_area:kitzbuhel-ski-area` | `official_trail_map.season_label` | `null` | `"2025/26"` | `verified` | no |
| `ski_area:kitzbuhel-ski-area` | `official_trail_map.url` | `null` | `"https://www.kitzski.at/media/drucksorten/KitzSki-Infoplan-Winter25-26-EN-WEB.pdf"` | `verified` | no |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.advanced` | `null` | `20.0` | `verified_with_adjustment` | yes |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.beginner` | `null` | `94.0` | `verified_with_adjustment` | yes |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.intermediate` | `null` | `67.0` | `verified_with_adjustment` | yes |
| `ski_area:kitzbuhel-ski-area` | `ski_day_apres_profile.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:kitzbuhel-ski-area` | `ski_day_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `ski_area:kitzbuhel-ski-area` | `snow_park.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:kitzbuhel-ski-area` | `snow_park.park_count` | `null` | `2` | `verified` | no |
| `ski_area:kitzbuhel-ski-area` | `snowmaking.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:kitzbuhel-ski-area` | `supported_skill_levels` | `["beginner", "intermediate"]` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:kitzbuhel-ski-area` | `total_lift_count` | `null` | `58` | `verified` | yes |
| `ski_area:kitzbuhel-ski-area` | `total_piste_km` | `null` | `181.0` | `verified_with_adjustment` | yes |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `distance_m` | `null` | `320` | `verified_with_adjustment` | yes |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `nearest_lift_name` | `null` | `"Wagstättbahn"` | `verified` | no |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "3097464362"}` | `verified_with_adjustment` | no |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `ski_area_access_id` | `null` | `"jochberg-jochberg--kitzbuhel-ski-area"` | `verified` | no |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `ski_area_id` | `null` | `"kitzbuhel-ski-area"` | `verified` | no |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `source_urls` | `null` | `["https://www.kitzbuehel.com/en/jochberg/", "https://www.openstreetmap.org/node/240102052", "https://www.openstreetmap.org/node/3097464362"]` | `verified_with_adjustment` | no |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `stay_base_id` | `null` | `"jochberg-jochberg"` | `verified` | no |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `access_mode` | `null` | `"ski_bus"` | `verified_with_adjustment` | yes |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `distance_m` | `null` | `1580` | `verified_with_adjustment` | yes |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `is_direct` | `null` | `false` | `verified_with_adjustment` | yes |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `lift_distance` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `nearest_lift_name` | `null` | `"Fleckalmbahn"` | `verified` | no |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_way_id": "125149747"}` | `verified_with_adjustment` | no |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `ski_area_access_id` | `null` | `"kirchberg-kirchberg--kitzbuhel-ski-area"` | `verified` | no |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `ski_area_id` | `null` | `"kitzbuhel-ski-area"` | `verified` | no |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `source_urls` | `null` | `["https://www.kitzbueheler-alpen.com/en/bri/wi/ski/busses.html", "https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/fleckalmbahn.html", "https://www.openstreetmap.org/node/240062251", "https://www.openstreetmap.org/way/125149747"]` | `verified_with_adjustment` | no |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `stay_base_id` | `null` | `"kirchberg-kirchberg"` | `verified` | no |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `distance_m` | `null` | `380` | `verified_with_adjustment` | yes |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `lift_distance` | `"medium"` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `nearest_lift_name` | `null` | `"Hahnenkammbahn"` | `verified_with_adjustment` | no |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `source_urls` | `["https://www.bergfex.com/kitzbuehel-kirchberg/"]` | `["https://www.bergfex.com/kitzbuehel-kirchberg/", "https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/node/1685958015", "https://www.openstreetmap.org/relation/85657", "https://www.openstreetmap.org/way/156335495"]` | `verified_with_adjustment` | no |
| `ski_region:kitzbuhel` | `name` | `"Kitzbuhel"` | `"Kitzbühel"` | `verified_with_adjustment` | no |
| `stay_base:jochberg-jochberg` | `base_character.development_style` | `null` | `"traditional"` | `verified_with_adjustment` | no |
| `stay_base:jochberg-jochberg` | `base_character.local_pace` | `null` | `"quiet"` | `verified_with_adjustment` | no |
| `stay_base:jochberg-jochberg` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:jochberg-jochberg` | `elevation_m` | `null` | `924` | `verified` | no |
| `stay_base:jochberg-jochberg` | `latitude` | `null` | `47.3805` | `verified_with_adjustment` | no |
| `stay_base:jochberg-jochberg` | `local_apres_profile.availability` | `null` | `"available"` | `verified_with_adjustment` | no |
| `stay_base:jochberg-jochberg` | `local_apres_profile.intensity` | `null` | `"moderate"` | `verified_with_adjustment` | no |
| `stay_base:jochberg-jochberg` | `local_apres_profile.season_label` | `null` | `"2025/26"` | `verified_with_adjustment` | no |
| `stay_base:jochberg-jochberg` | `longitude` | `null` | `12.418` | `verified_with_adjustment` | no |
| `stay_base:jochberg-jochberg` | `name` | `null` | `"Jochberg"` | `verified` | no |
| `stay_base:jochberg-jochberg` | `price_max` | `null` | `240.0` | `estimated` | yes |
| `stay_base:jochberg-jochberg` | `price_min` | `null` | `160.0` | `estimated` | yes |
| `stay_base:jochberg-jochberg` | `price_range` | `null` | `"EUR 160-240"` | `estimated` | yes |
| `stay_base:jochberg-jochberg` | `quality` | `null` | `"standard"` | `estimated` | yes |
| `stay_base:jochberg-jochberg` | `regional_data_ids` | `null` | `{"osm_node_id": "240102052"}` | `verified_with_adjustment` | no |
| `stay_base:jochberg-jochberg` | `stay_base_id` | `null` | `"jochberg-jochberg"` | `verified` | no |
| `stay_base:jochberg-jochberg` | `stay_destination_id` | `null` | `"jochberg"` | `verified_with_adjustment` | no |
| `stay_base:kirchberg-kirchberg` | `base_character.development_style` | `null` | `"mixed"` | `verified_with_adjustment` | no |
| `stay_base:kirchberg-kirchberg` | `base_character.local_pace` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:kirchberg-kirchberg` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:kirchberg-kirchberg` | `elevation_m` | `null` | `832` | `verified` | no |
| `stay_base:kirchberg-kirchberg` | `latitude` | `null` | `47.4476` | `verified_with_adjustment` | no |
| `stay_base:kirchberg-kirchberg` | `local_apres_profile.availability` | `null` | `"available"` | `verified_with_adjustment` | no |
| `stay_base:kirchberg-kirchberg` | `local_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:kirchberg-kirchberg` | `longitude` | `null` | `12.3144` | `verified_with_adjustment` | no |
| `stay_base:kirchberg-kirchberg` | `name` | `null` | `"Kirchberg in Tirol"` | `verified` | no |
| `stay_base:kirchberg-kirchberg` | `price_max` | `null` | `230.0` | `estimated` | yes |
| `stay_base:kirchberg-kirchberg` | `price_min` | `null` | `150.0` | `estimated` | yes |
| `stay_base:kirchberg-kirchberg` | `price_range` | `null` | `"EUR 150-230"` | `estimated` | yes |
| `stay_base:kirchberg-kirchberg` | `quality` | `null` | `"standard"` | `estimated` | yes |
| `stay_base:kirchberg-kirchberg` | `regional_data_ids` | `null` | `{"osm_node_id": "240062251"}` | `verified_with_adjustment` | no |
| `stay_base:kirchberg-kirchberg` | `stay_base_id` | `null` | `"kirchberg-kirchberg"` | `verified` | no |
| `stay_base:kirchberg-kirchberg` | `stay_destination_id` | `null` | `"kirchberg"` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `base_character.development_style` | `"unknown"` | `"mixed"` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `base_character.local_pace` | `"unknown"` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `base_type` | `null` | `"town"` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `elevation_m` | `null` | `800` | `verified` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `latitude` | `null` | `47.4464` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `local_apres_profile.availability` | `"unknown"` | `"available"` | `verified` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `local_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `longitude` | `null` | `12.3911` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `name` | `"Kitzbuhel"` | `"Kitzbühel"` | `verified_with_adjustment` | no |
| `stay_base:kitzbuhel-kitzbuhel` | `regional_data_ids` | `{}` | `{"osm_relation_id": "85657"}` | `verified_with_adjustment` | no |
| `stay_destination:jochberg` | `country` | `null` | `"Austria"` | `verified` | no |
| `stay_destination:jochberg` | `latitude` | `null` | `47.3805` | `verified_with_adjustment` | yes |
| `stay_destination:jochberg` | `longitude` | `null` | `12.418` | `verified_with_adjustment` | yes |
| `stay_destination:jochberg` | `name` | `null` | `"Jochberg"` | `verified` | no |
| `stay_destination:jochberg` | `price_level` | `null` | `"medium"` | `estimated` | yes |
| `stay_destination:jochberg` | `region` | `null` | `"Tyrol"` | `verified` | no |
| `stay_destination:jochberg` | `regional_data_ids` | `null` | `{"osm_relation_id": "85643"}` | `verified_with_adjustment` | no |
| `stay_destination:jochberg` | `stay_destination_id` | `null` | `"jochberg"` | `verified` | no |
| `stay_destination:jochberg` | `trip_market_region_id` | `null` | `"kitzbuhel"` | `verified_with_adjustment` | no |
| `stay_destination:kirchberg` | `country` | `null` | `"Austria"` | `verified` | no |
| `stay_destination:kirchberg` | `latitude` | `null` | `47.4476` | `verified_with_adjustment` | yes |
| `stay_destination:kirchberg` | `longitude` | `null` | `12.3144` | `verified_with_adjustment` | yes |
| `stay_destination:kirchberg` | `name` | `null` | `"Kirchberg in Tirol"` | `verified` | no |
| `stay_destination:kirchberg` | `price_level` | `null` | `"medium"` | `estimated` | yes |
| `stay_destination:kirchberg` | `region` | `null` | `"Tyrol"` | `verified` | no |
| `stay_destination:kirchberg` | `regional_data_ids` | `null` | `{"osm_relation_id": "541914"}` | `verified_with_adjustment` | no |
| `stay_destination:kirchberg` | `stay_destination_id` | `null` | `"kirchberg"` | `verified` | no |
| `stay_destination:kirchberg` | `trip_market_region_id` | `null` | `"kitzbuhel"` | `verified_with_adjustment` | no |
| `stay_destination:kitzbuhel` | `name` | `"Kitzbuhel"` | `"Kitzbühel"` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `display_name` | `null` | `"KitzSki Ski Pass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `field_source_refs` | `null` | `{"coverage": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.kitzbuehel.com/en/jochberg/", "https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/fleckalmbahn.html", "https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html", "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"], "identity_scope_availability": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.kitzbuehel.com/en/jochberg/", "https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html", "https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html", "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"], "pass_accessible_terrain": [], "prices": ["https://www.kitzski.at/media/preise-26-27-hp-en.pdf"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "verified"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:kitzski-skipass` | `notes` | `null` | `["Official KitzSki and destination sources support product identity, 2026/27 representative prices, and availability from Kitzbühel, Kirchberg, and Jochberg.", "Existing default relationships are retained for this curation cycle pending the separate pass-product selection refinement."]` | `estimated` | no |
| `trust_manifest:ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `display_name` | `null` | `"Jochberg -> KitzSki"` | `estimated` | no |
| `trust_manifest:ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.kitzbuehel.com/en/jochberg/", "https://www.openstreetmap.org/node/240102052", "https://www.openstreetmap.org/node/3097464362"], "relationship": ["https://www.kitzbuehel.com/en/jochberg/", "https://www.openstreetmap.org/node/240102052", "https://www.openstreetmap.org/node/3097464362"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `notes` | `null` | `["The official destination page states that Wagstättbahn provides direct KitzSki access from Jochberg village centre.", "The 320 m distance is a rounded Haversine calculation from the OSM Jochberg village node to the Wagstättbahn valley-station node."]` | `estimated` | no |
| `trust_manifest:ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `display_name` | `null` | `"Kirchberg in Tirol -> KitzSki"` | `estimated` | no |
| `trust_manifest:ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/fleckalmbahn.html", "https://www.kitzbueheler-alpen.com/en/bri/wi/ski/busses.html", "https://www.openstreetmap.org/node/240062251", "https://www.openstreetmap.org/way/125149747"], "relationship": ["https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/fleckalmbahn.html", "https://www.kitzbueheler-alpen.com/en/bri/wi/ski/busses.html", "https://www.openstreetmap.org/node/240062251", "https://www.openstreetmap.org/way/125149747"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `notes` | `null` | `["Official sources identify Fleckalmbahn as a direct KitzSki entry and document free ski buses from Kirchberg accommodation to valley stations.", "The 1,580 m distance is a rounded Haversine calculation from the OSM Kirchberg village node to the Fleckalmbahn valley-station building."]` | `estimated` | no |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `display_name` | `"Kitzbuhel -> Kitzbuhel"` | `"Kitzbühel -> KitzSki"` | `estimated` | no |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/kitzbuehel-kirchberg/"], "relationship": ["https://www.bergfex.com/kitzbuehel-kirchberg/"]}` | `{"access_mode_distance": ["https://www.bergfex.com/kitzbuehel-kirchberg/", "https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/node/1685958015", "https://www.openstreetmap.org/relation/85657", "https://www.openstreetmap.org/way/156335495"], "relationship": ["https://www.bergfex.com/kitzbuehel-kirchberg/", "https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/node/1685958015", "https://www.openstreetmap.org/relation/85657", "https://www.openstreetmap.org/way/156335495"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "estimated"}` | `estimated` | no |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `display_name` | `"Kitzbuhel"` | `"KitzSki"` | `estimated` | no |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "glacier_terrain": [], "identity_coordinates": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "marked_freeride_routes": ["https://press.kitzski.at/media/kitzski-factsheet-2025-26-de.pdf"], "night_skiing": [], "official_documents": ["https://www.kitzski.at/media/drucksorten/KitzSki-Infoplan-Winter25-26-EN-WEB.pdf"], "ski_day_apres": ["https://www.kitzbuehel.com/en/lifestyle/nightlife/apres-ski/"], "skill_fit": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "snow_park": ["https://www.kitzski.at/de/skigebiet-tirol/familie-kinder/kitzski-snowpark-hanglalm.html"], "snowmaking": ["https://press.kitzski.at/media/kitzski-factsheet-2025-26-de.pdf"], "terrain_metrics": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"]}` | `estimated` | no |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "verified", "night_skiing": "needs_source", "official_documents": "verified", "ski_day_apres": "verified_with_adjustment", "skill_fit": "estimated", "snow_park": "verified", "snowmaking": "verified", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner.", "Source-aware v2 enrichment reviewed current KitzSki 2025/26 facts and map sources on 2026-07-04.", "Snowmaking coverage remains null because the publisher provides areas rather than a coverage percentage."]` | `estimated` | no |
| `trust_manifest:ski_regions:kitzbuhel` | `display_name` | `"Kitzbuhel"` | `"Kitzbühel"` | `estimated` | no |
| `trust_manifest:ski_regions:kitzbuhel` | `field_source_refs` | `{"identity": [], "membership_context": []}` | `{"identity": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "membership_context": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"]}` | `estimated` | no |
| `trust_manifest:ski_regions:kitzbuhel` | `field_statuses` | `{"identity": "needs_source", "membership_context": "estimated"}` | `{"identity": "verified_with_adjustment", "membership_context": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:jochberg-jochberg` | `display_name` | `null` | `"Jochberg"` | `estimated` | no |
| `trust_manifest:stay_bases:jochberg-jochberg` | `field_source_refs` | `null` | `{"base_character": ["https://www.kitzbuehel.com/en/jochberg/"], "base_type": ["https://www.kitzbuehel.com/en/jochberg/"], "coordinates": ["https://www.openstreetmap.org/node/240102052"], "elevation": ["https://www.kitzbuehel.com/en/jochberg/"], "identity_ownership": ["https://www.kitzbuehel.com/en/jochberg/", "https://www.openstreetmap.org/node/240102052"], "local_apres": ["https://www.kitzbuehel.com/en/holiday/kitz-a-z/infrastructure/hofalm-jochberg-jochberg/"], "lodging_price_quality": ["https://www.kitzbuehel.com/urlaub/unterkunft-buchen/details/gaestehaus-jochberg/"]}` | `estimated` | no |
| `trust_manifest:stay_bases:jochberg-jochberg` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:jochberg-jochberg` | `notes` | `null` | `["The official destination profile describes Jochberg as a traditional, peaceful village at 924 m with direct KitzSki access.", "The local apres profile is moderate: one recurring daily venue with scheduled live music and DJs supports availability without making apres destination-defining.", "Lodging price and quality remain product-curated estimates pending a reviewed sampling policy."]` | `estimated` | no |
| `trust_manifest:stay_bases:kirchberg-kirchberg` | `display_name` | `null` | `"Kirchberg in Tirol"` | `estimated` | no |
| `trust_manifest:stay_bases:kirchberg-kirchberg` | `field_source_refs` | `null` | `{"base_character": ["https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html", "https://www.kitzbueheler-alpen.com/en/bri/wi/ski/apresski.html"], "base_type": ["https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html"], "coordinates": ["https://www.openstreetmap.org/node/240062251"], "elevation": ["https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html"], "identity_ownership": ["https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html", "https://www.openstreetmap.org/node/240062251"], "local_apres": ["https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/gamsstadl.html", "https://www.kitzbueheler-alpen.com/en/bri/wi/ski/apresski.html"], "lodging_price_quality": ["https://www.kitzbueheler-alpen.com/en/bri/booking.html"]}` | `estimated` | no |
| `trust_manifest:stay_bases:kirchberg-kirchberg` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:kirchberg-kirchberg` | `notes` | `null` | `["Official sources describe Kirchberg as an 832 m village combining a picture-book centre, modern lift access, events, and a broad apres scene.", "Lodging price and quality remain product-curated estimates pending a reviewed sampling policy."]` | `estimated` | no |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `display_name` | `"Kitzbuhel"` | `"Kitzbühel"` | `estimated` | no |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `{"base_character": ["https://www.kitzbuehel.com/en/kitzbuehel/", "https://www.kitzbuehel.com/en/lifestyle/nightlife/"], "base_type": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/"], "coordinates": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/relation/85657"], "elevation": ["https://www.kitzbuehel.com/en/kitzbuehel/"], "identity_ownership": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/relation/85657"], "local_apres": ["https://www.kitzbuehel.com/en/lifestyle/nightlife/", "https://www.kitzbuehel.com/en/lifestyle/nightlife/apres-ski/"], "lodging_price_quality": ["https://www.kitzbuehel.com/en/activities/ski-resort/skiing/", "https://www.openstreetmap.org/relation/85657"]}` | `estimated` | no |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified_with_adjustment", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner.", "Source-aware v2 enrichment reviewed official Kitzbühel identity, elevation, apres, and nightlife sources on 2026-07-04."]` | `estimated` | no |
| `trust_manifest:stay_destinations:jochberg` | `display_name` | `null` | `"Jochberg"` | `estimated` | no |
| `trust_manifest:stay_destinations:jochberg` | `field_source_refs` | `null` | `{"coordinates": ["https://www.openstreetmap.org/relation/85643"], "identity_location": ["https://www.kitzbuehel.com/en/jochberg/"], "price_level": ["https://www.kitzbuehel.com/urlaub/unterkunft-buchen/details/gaestehaus-jochberg/"]}` | `estimated` | no |
| `trust_manifest:stay_destinations:jochberg` | `field_statuses` | `null` | `{"coordinates": "verified_with_adjustment", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:jochberg` | `notes` | `null` | `["Official tourism sources treat Jochberg as a bookable village with direct KitzSki access and a quieter recommendation context than Kitzbühel.", "The medium price level is a product-curated estimate pending a reviewed accommodation sampling policy."]` | `estimated` | no |
| `trust_manifest:stay_destinations:kirchberg` | `display_name` | `null` | `"Kirchberg in Tirol"` | `estimated` | no |
| `trust_manifest:stay_destinations:kirchberg` | `field_source_refs` | `null` | `{"coordinates": ["https://www.openstreetmap.org/relation/541914"], "identity_location": ["https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html"], "price_level": ["https://www.kitzbueheler-alpen.com/en/bri/booking.html"]}` | `estimated` | no |
| `trust_manifest:stay_destinations:kirchberg` | `field_statuses` | `null` | `{"coordinates": "verified_with_adjustment", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:kirchberg` | `notes` | `null` | `["Official Brixental sources treat Kirchberg as an independent holiday village with substantial lodging inventory and direct KitzSki access.", "The medium price level is a product-curated estimate pending a reviewed accommodation sampling policy."]` | `estimated` | no |
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
| `ski_area:kitzbuhel-ski-area` | `glacier_terrain.availability` | `unresolved` | Current official KitzSki sources were reviewed, but they did not establish this exact value for the modeled ski area; it remains unknown rather than being inferred. |
| `ski_area:kitzbuhel-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.availability` | `changed` | The current official factsheet inventories ski routes. |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.route_count` | `changed` | The 2025/26 factsheet publishes 12 ski routes totaling 41 km. |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.season_label` | `changed` | The route inventory is explicitly labeled winter 2025/26. |
| `ski_area:kitzbuhel-ski-area` | `name` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `night_skiing.availability` | `unresolved` | The reviewed KitzSki media page does not establish a current recurring downhill night-skiing offer; availability remains unknown rather than being inferred from historical wording, evening sledding, or piste touring. |
| `ski_area:kitzbuhel-ski-area` | `night_skiing.season_label` | `unresolved` | Current official KitzSki sources were reviewed, but they did not establish this exact value for the modeled ski area; it remains unknown rather than being inferred. |
| `ski_area:kitzbuhel-ski-area` | `official_trail_map.season_label` | `changed` | The official map is labeled winter 2025/26. |
| `ski_area:kitzbuhel-ski-area` | `official_trail_map.url` | `changed` | Direct official KitzSki winter information and piste-map PDF. |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `season_start_month` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `season_windows` | `unresolved` | Reviewed sources did not resolve a retained structured value. |
| `ski_area:kitzbuhel-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `ski_day_apres_profile.availability` | `changed` | The official destination inventories numerous slope-side apres venues. |
| `ski_area:kitzbuhel-ski-area` | `ski_day_apres_profile.intensity` | `changed` | Multiple mountain venues offer DJs, events, and lively atmosphere. |
| `ski_area:kitzbuhel-ski-area` | `ski_day_apres_profile.season_label` | `unresolved` | Current official KitzSki sources were reviewed, but they did not establish this exact value for the modeled ski area; it remains unknown rather than being inferred. |
| `ski_area:kitzbuhel-ski-area` | `snow_park.availability` | `changed` | The operator explicitly describes snowparks at Hanglalm and Kitzbüheler Horn. |
| `ski_area:kitzbuhel-ski-area` | `snow_park.park_count` | `changed` | The current official page identifies two dedicated snowparks. |
| `ski_area:kitzbuhel-ski-area` | `snow_park.season_label` | `unresolved` | Current official KitzSki sources were reviewed, but they did not establish this exact value for the modeled ski area; it remains unknown rather than being inferred. |
| `ski_area:kitzbuhel-ski-area` | `snowmaking.availability` | `changed` | The 2025/26 factsheet documents 1,260 snowmaking machines and technically snow-covered piste area. |
| `ski_area:kitzbuhel-ski-area` | `snowmaking.coverage_basis` | `unresolved` | Current official KitzSki sources were reviewed, but they did not establish this exact value for the modeled ski area; it remains unknown rather than being inferred. |
| `ski_area:kitzbuhel-ski-area` | `snowmaking.coverage_pct` | `unresolved` | Current official KitzSki sources were reviewed, but they did not establish this exact value for the modeled ski area; it remains unknown rather than being inferred. |
| `ski_area:kitzbuhel-ski-area` | `snowmaking.season_label` | `unresolved` | Current official KitzSki sources were reviewed, but they did not establish this exact value for the modeled ski area; it remains unknown rather than being inferred. |
| `ski_area:kitzbuhel-ski-area` | `summit_elevation_m` | `reviewed-no-change` |  |
| `ski_area:kitzbuhel-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:kitzbuhel-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `duration_minutes` | `unresolved` | Official access sources do not publish a representative journey duration for this edge. |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `duration_minutes` | `unresolved` | Official access sources do not publish a representative journey duration for this edge. |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `stay_base_id` | `changed` |  |
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
| `stay_base:jochberg-jochberg` | `base_character.development_style` | `changed` |  |
| `stay_base:jochberg-jochberg` | `base_character.local_pace` | `changed` |  |
| `stay_base:jochberg-jochberg` | `base_type` | `changed` |  |
| `stay_base:jochberg-jochberg` | `elevation_m` | `changed` |  |
| `stay_base:jochberg-jochberg` | `latitude` | `changed` |  |
| `stay_base:jochberg-jochberg` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:jochberg-jochberg` | `local_apres_profile.intensity` | `changed` |  |
| `stay_base:jochberg-jochberg` | `local_apres_profile.season_label` | `changed` |  |
| `stay_base:jochberg-jochberg` | `longitude` | `changed` |  |
| `stay_base:jochberg-jochberg` | `name` | `changed` |  |
| `stay_base:jochberg-jochberg` | `price_max` | `changed` |  |
| `stay_base:jochberg-jochberg` | `price_min` | `changed` |  |
| `stay_base:jochberg-jochberg` | `price_range` | `changed` |  |
| `stay_base:jochberg-jochberg` | `quality` | `changed` |  |
| `stay_base:jochberg-jochberg` | `regional_data_ids` | `changed` |  |
| `stay_base:jochberg-jochberg` | `stay_base_id` | `changed` |  |
| `stay_base:jochberg-jochberg` | `stay_destination_id` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `base_character.development_style` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `base_character.local_pace` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `base_type` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `elevation_m` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `latitude` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `local_apres_profile.intensity` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `local_apres_profile.season_label` | `not-applicable` | The recurring official apres inventory is not limited to one published season label. |
| `stay_base:kirchberg-kirchberg` | `longitude` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `name` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `price_max` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `price_min` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `price_range` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `quality` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `regional_data_ids` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `stay_base_id` | `changed` |  |
| `stay_base:kirchberg-kirchberg` | `stay_destination_id` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `base_character.development_style` | `changed` | The historic 750-year-old Alpine town combines retained tradition with international flair and stylish amenities. |
| `stay_base:kitzbuhel-kitzbuhel` | `base_character.local_pace` | `changed` | The official town presents year-round nightlife, events, bars, lounges, and clubs. |
| `stay_base:kitzbuhel-kitzbuhel` | `base_type` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `elevation_m` | `changed` | The official town profile places Kitzbühel at 800 m above sea level. |
| `stay_base:kitzbuhel-kitzbuhel` | `latitude` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `local_apres_profile.availability` | `changed` | The official destination lists more than ten bars and multiple mountain locations. |
| `stay_base:kitzbuhel-kitzbuhel` | `local_apres_profile.intensity` | `changed` | A diverse year-round town nightlife continues after slope-side apres. |
| `stay_base:kitzbuhel-kitzbuhel` | `local_apres_profile.season_label` | `unresolved` | Official Kitzbühel town sources were reviewed, but they did not establish this exact stay-base value; it remains unknown rather than being inferred. |
| `stay_base:kitzbuhel-kitzbuhel` | `longitude` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `name` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `price_max` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `price_min` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `price_range` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `quality` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `regional_data_ids` | `changed` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `stay_base_id` | `reviewed-no-change` |  |
| `stay_base:kitzbuhel-kitzbuhel` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:jochberg` | `country` | `changed` |  |
| `stay_destination:jochberg` | `latitude` | `changed` |  |
| `stay_destination:jochberg` | `longitude` | `changed` |  |
| `stay_destination:jochberg` | `name` | `changed` |  |
| `stay_destination:jochberg` | `price_level` | `changed` |  |
| `stay_destination:jochberg` | `region` | `changed` |  |
| `stay_destination:jochberg` | `regional_data_ids` | `changed` |  |
| `stay_destination:jochberg` | `stay_destination_id` | `changed` |  |
| `stay_destination:jochberg` | `trip_market_region_id` | `changed` |  |
| `stay_destination:kirchberg` | `country` | `changed` |  |
| `stay_destination:kirchberg` | `latitude` | `changed` |  |
| `stay_destination:kirchberg` | `longitude` | `changed` |  |
| `stay_destination:kirchberg` | `name` | `changed` |  |
| `stay_destination:kirchberg` | `price_level` | `changed` |  |
| `stay_destination:kirchberg` | `region` | `changed` |  |
| `stay_destination:kirchberg` | `regional_data_ids` | `changed` |  |
| `stay_destination:kirchberg` | `stay_destination_id` | `changed` |  |
| `stay_destination:kirchberg` | `trip_market_region_id` | `changed` |  |
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
| `trust_manifest:ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:kitzbuhel-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_regions:kitzbuhel` | `display_name` | `changed` |  |
| `trust_manifest:ski_regions:kitzbuhel` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_regions:kitzbuhel` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_regions:kitzbuhel` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:jochberg-jochberg` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:jochberg-jochberg` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:jochberg-jochberg` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:jochberg-jochberg` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:kirchberg-kirchberg` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:kirchberg-kirchberg` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:kirchberg-kirchberg` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:kirchberg-kirchberg` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:kitzbuhel-kitzbuhel` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:jochberg` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:jochberg` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:jochberg` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:jochberg` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:kirchberg` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:kirchberg` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:kirchberg` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:kirchberg` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:kitzbuhel` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:kitzbuhel` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:kitzbuhel` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:kitzbuhel` | `notes` | `reviewed-no-change` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `ski_area:kitzbuhel-ski-area` | `name` | [Kitzbühel Ski Resort and KitzSki sections](https://www.kitzbuehel.com/en/activities/ski-resort/) | `"KitzSki"` | Official tourism material uses KitzSki for the shared terrain reached from Kitzbühel, Kirchberg, and Jochberg. | The stable ski-area ID is retained while its display name is normalized to the operator brand that matches the modeled scope. |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.advanced` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `{"black": 20, "blue": 94, "red": 67}` | Official FAQ lists 94 km blue, 67 km red, and 20 km black runs. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.beginner` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `{"black": 20, "blue": 94, "red": 67}` | Official FAQ lists 94 km blue, 67 km red, and 20 km black runs. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:kitzbuhel-ski-area` | `piste_km_by_difficulty.intermediate` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `{"black": 20, "blue": 94, "red": 67}` | Official FAQ lists 94 km blue, 67 km red, and 20 km black runs. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:kitzbuhel-ski-area` | `supported_skill_levels` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `{"black": 20, "blue": 94, "red": 67}` | The official difficulty inventory includes substantial blue, red, and black terrain. | Published blue, red, and black terrain is mapped to beginner, intermediate, and advanced support. |
| `ski_area:kitzbuhel-ski-area` | `total_lift_count` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `58` | Official tourism page lists 58 gondolas and ski lifts. | The OSM aerialway name is normalized as the nearest lift label on the Snowcast access edge. |
| `ski_area:kitzbuhel-ski-area` | `total_piste_km` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `{"black": 20, "blue": 94, "groomed_total_by_difficulty": 181, "red": 67}` | Official page lists blue/red/black groomed run kilometres that sum to 181 km. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `access_mode` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"from the heart of town, lifts connect directly to skiing"` | Official page says lifts connect directly from the heart of town to the ski area. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `distance_m` | [OpenStreetMap node 1685958015](https://www.openstreetmap.org/node/1685958015) | `{"station": [47.4432306, 12.3893632], "town_centroid": [47.4463585, 12.3911473]}` | OSM town centroid and Hahnenkammbahn valley-station node support an approximate walk distance of about 380 m. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `lift_distance` | [OpenStreetMap node 1685958015](https://www.openstreetmap.org/node/1685958015) | `"Hahnenkammbahn valley station in Kitzbühel"` | OSM places the Hahnenkammbahn station close to central Kitzbühel. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `nearest_lift_name` | [OpenStreetMap way 156335495](https://www.openstreetmap.org/way/156335495) | `"Hahnenkammbahn"` | OSM identifies the Hahnenkammbahn aerialway in Kitzbühel. | The OSM aerialway name is normalized as the nearest lift label on the Snowcast access edge. |
| `ski_area_access:kitzbuhel-kitzbuhel--kitzbuhel-ski-area` | `source_urls` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"from the heart of town, lifts connect directly to skiing"` | Official page says lifts connect directly from the heart of town to the ski area. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_region:kitzbuhel` | `name` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"Kitzbühel"` | Official tourism page uses the Kitzbühel spelling. | The official destination spelling is retained as the Snowcast regional display name. |
| `stay_base:kitzbuhel-kitzbuhel` | `base_type` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"750-year-old town"` | Official page describes Kitzbühel as a historic town base. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:kitzbuhel-kitzbuhel` | `latitude` | [OpenStreetMap relation 85657](https://www.openstreetmap.org/relation/85657) | `47.4463585` | OSM administrative relation provides the Kitzbühel centroid latitude. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:kitzbuhel-kitzbuhel` | `longitude` | [OpenStreetMap relation 85657](https://www.openstreetmap.org/relation/85657) | `12.3911473` | OSM administrative relation provides the Kitzbühel centroid longitude. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:kitzbuhel-kitzbuhel` | `name` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"Kitzbühel"` | Official destination page uses the Kitzbühel spelling for the town stay base. | The official destination spelling is retained as the Snowcast stay-base display name. |
| `stay_base:kitzbuhel-kitzbuhel` | `regional_data_ids` | [OpenStreetMap relation 85657](https://www.openstreetmap.org/relation/85657) | `{"osm_relation_id": "85657"}` | OSM relation id is stored for future regional-data joins. | The OSM administrative relation identifier is stored as the stay base's regional-data join key. |
| `stay_destination:kitzbuhel` | `name` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"Kitzbühel"` | Official tourism page uses the Kitzbühel spelling. | The official destination spelling is retained as the Snowcast stay-destination display name. |
| `stay_destination:kitzbuhel` | `name` | [Skiing in Kitzbühel](https://www.kitzbuehel.com/en/activities/ski-resort/skiing/) | `"Kitzbühel"` | The normalized migration retains the already reviewed destination boundary. | The existing reviewed town boundary is retained as the Kitzbühel stay destination. |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.availability` | [KitzSki facts and figures 2025/26](https://press.kitzski.at/media/kitzski-factsheet-2025-26-de.pdf) | `"available"` | The current official factsheet inventories ski routes. |  |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.route_count` | [KitzSki facts and figures 2025/26](https://press.kitzski.at/media/kitzski-factsheet-2025-26-de.pdf) | `12` | The 2025/26 factsheet publishes 12 ski routes totaling 41 km. |  |
| `ski_area:kitzbuhel-ski-area` | `marked_freeride_routes.season_label` | [KitzSki facts and figures 2025/26](https://press.kitzski.at/media/kitzski-factsheet-2025-26-de.pdf) | `"2025/26"` | The route inventory is explicitly labeled winter 2025/26. |  |
| `ski_area:kitzbuhel-ski-area` | `official_trail_map.season_label` | [KitzSki winter information and piste map 2025/26](https://www.kitzski.at/media/drucksorten/KitzSki-Infoplan-Winter25-26-EN-WEB.pdf) | `"2025/26"` | The official map is labeled winter 2025/26. |  |
| `ski_area:kitzbuhel-ski-area` | `official_trail_map.url` | [KitzSki winter information and piste map 2025/26](https://www.kitzski.at/media/drucksorten/KitzSki-Infoplan-Winter25-26-EN-WEB.pdf) | `"https://www.kitzski.at/media/drucksorten/KitzSki-Infoplan-Winter25-26-EN-WEB.pdf"` | Direct official KitzSki winter information and piste-map PDF. |  |
| `ski_area:kitzbuhel-ski-area` | `ski_day_apres_profile.availability` | [Kitzbühel apres-ski](https://www.kitzbuehel.com/en/lifestyle/nightlife/apres-ski/) | `"available"` | The official destination inventories numerous slope-side apres venues. |  |
| `ski_area:kitzbuhel-ski-area` | `ski_day_apres_profile.intensity` | [Kitzbühel apres-ski](https://www.kitzbuehel.com/en/lifestyle/nightlife/apres-ski/) | `"lively"` | Multiple mountain venues offer DJs, events, and lively atmosphere. | The broad slope-side offer is mapped to lively. |
| `ski_area:kitzbuhel-ski-area` | `snow_park.availability` | [KitzSki snowparks](https://www.kitzski.at/de/skigebiet-tirol/familie-kinder/kitzski-snowpark-hanglalm.html) | `"available"` | The operator explicitly describes snowparks at Hanglalm and Kitzbüheler Horn. |  |
| `ski_area:kitzbuhel-ski-area` | `snow_park.park_count` | [KitzSki snowparks](https://www.kitzski.at/de/skigebiet-tirol/familie-kinder/kitzski-snowpark-hanglalm.html) | `2` | The current official page identifies two dedicated snowparks. |  |
| `ski_area:kitzbuhel-ski-area` | `snowmaking.availability` | [KitzSki facts and figures 2025/26](https://press.kitzski.at/media/kitzski-factsheet-2025-26-de.pdf) | `"available"` | The 2025/26 factsheet documents 1,260 snowmaking machines and technically snow-covered piste area. |  |
| `stay_base:kitzbuhel-kitzbuhel` | `base_character.development_style` | [Kitzbühel town profile](https://www.kitzbuehel.com/en/kitzbuehel/) | `"mixed"` | The historic 750-year-old Alpine town combines retained tradition with international flair and stylish amenities. | The explicit historic and international blend is mapped to mixed. |
| `stay_base:kitzbuhel-kitzbuhel` | `base_character.local_pace` | [Kitzbühel nightlife](https://www.kitzbuehel.com/en/lifestyle/nightlife/) | `"lively"` | The official town presents year-round nightlife, events, bars, lounges, and clubs. | The year-round event and nightlife breadth is mapped to lively. |
| `stay_base:kitzbuhel-kitzbuhel` | `elevation_m` | [Kitzbühel town profile](https://www.kitzbuehel.com/en/kitzbuehel/) | `800` | The official town profile places Kitzbühel at 800 m above sea level. |  |
| `stay_base:kitzbuhel-kitzbuhel` | `local_apres_profile.availability` | [Kitzbühel apres-ski](https://www.kitzbuehel.com/en/lifestyle/nightlife/apres-ski/) | `"available"` | The official destination lists more than ten bars and multiple mountain locations. |  |
| `stay_base:kitzbuhel-kitzbuhel` | `local_apres_profile.intensity` | [Kitzbühel nightlife](https://www.kitzbuehel.com/en/lifestyle/nightlife/) | `"lively"` | A diverse year-round town nightlife continues after slope-side apres. | Nightlife is substantial but one part of a broader town identity, so it is mapped to lively. |
| `stay_destination:jochberg` | `name` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"Jochberg"` | Official tourism material presents Jochberg as a named holiday village with accommodation, direct KitzSki access, and a quieter recommendation context. |  |
| `stay_destination:kirchberg` | `name` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"Kirchberg in Tirol"` | Official tourism material presents Kirchberg as a holiday village with about 8,200 guest beds, direct KitzSki access, and its own village character. |  |
| `ski_area:kitzbuhel-ski-area` | `name` | [Kitzbühel Ski Resort and KitzSki sections](https://www.kitzbuehel.com/en/activities/ski-resort/) | `"KitzSki"` | Official tourism material presents KitzSki as the shared terrain reached from Kitzbühel, Kirchberg, Jochberg, and the Pass Thurn side. | The stable ski-area ID is retained while its display name is normalized to the operator brand that matches the modeled scope. |
| `ski_area:kitzbuhel-ski-area` | `name` | [KitzSki connected-sector overview](https://www.kitzbuehel.com/en/activities/ski-resort/) | `["Pengelstein", "Jochberg", "Pass Thurn", "Resterhöhe"]` | Official material treats these names as lift-connected sections of the wider KitzSki terrain. | The sector inventory supports not_separate decisions and is not copied into the ski-area display name. |
| `ski_area:kitzbuhel-ski-area` | `name` | [KitzSki winter information and local specials](https://www.kitzski.at/media/blaetterkataloge/winterinfoplan-2025-26-de.pdf) | `["Kitzbüheler Horn", "Gaisberg", "Bichlalm"]` | The official map and local-special products expose disconnected or independently accessed terrain that merits a future weather-owner review. | The candidates are deferred instead of being duplicated inside the current coarse ski-area owner. |
| `stay_destination:kitzbuhel` | `name` | [Brixental KitzSki resort coverage](https://www.kitzbueheler-alpen.com/en/bri/wi/ski/resorts.html) | `["Pass Thurn-Mittersill", "Hollersbach", "Kirchberg", "Aschau"]` | Official regional material identifies additional accommodation and access markets on the KitzSki graph. | Kirchberg is added now; the remaining markets are consolidated into one regional deferral. |
| `stay_destination:kitzbuhel` | `name` | [Kitzbühel holiday region](https://www.kitzbuehel.com/en/region/) | `["Kitzbühel", "Reith bei Kitzbühel", "Aurach bei Kitzbühel", "Jochberg"]` | Official tourism material exposes Reith and Aurach as lodging villages within the Kitzbühel holiday region. | Jochberg is added now; Reith and Aurach remain unresolved destination-boundary candidates. |
| `stay_destination:jochberg` | `country` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"Austria"` | Official tourism material supports the destination identity and Tyrol location. |  |
| `stay_destination:jochberg` | `latitude` | [OpenStreetMap relation 85643](https://www.openstreetmap.org/relation/85643) | `47.3805` | The OSM administrative relation provides the destination identity and representative coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_destination:jochberg` | `longitude` | [OpenStreetMap relation 85643](https://www.openstreetmap.org/relation/85643) | `12.418` | The OSM administrative relation provides the destination identity and representative coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_destination:jochberg` | `price_level` | [Official Jochberg accommodation listing](https://www.kitzbuehel.com/urlaub/unterkunft-buchen/details/gaestehaus-jochberg/) | `"bookable accommodation inventory"` | The official booking surface demonstrates a broad, bookable accommodation market. | The active booking inventory is normalized to a medium product price tier pending a formal sampling policy. |
| `stay_destination:jochberg` | `region` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"Tyrol"` | Official tourism material supports the destination identity and Tyrol location. |  |
| `stay_destination:jochberg` | `regional_data_ids` | [OpenStreetMap relation 85643](https://www.openstreetmap.org/relation/85643) | `{"osm_relation_id": "85643"}` | The OSM administrative relation provides the destination identity and representative coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_destination:jochberg` | `stay_destination_id` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"jochberg"` | Official tourism material supports the destination identity and Tyrol location. |  |
| `stay_destination:jochberg` | `trip_market_region_id` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"kitzbuhel"` | Official tourism material supports the destination identity and Tyrol location. | The official destination identity is normalized into Snowcast ownership. |
| `stay_destination:kirchberg` | `country` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"Austria"` | Official tourism material supports the destination identity and Tyrol location. |  |
| `stay_destination:kirchberg` | `latitude` | [OpenStreetMap relation 541914](https://www.openstreetmap.org/relation/541914) | `47.4476` | The OSM administrative relation provides the destination identity and representative coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_destination:kirchberg` | `longitude` | [OpenStreetMap relation 541914](https://www.openstreetmap.org/relation/541914) | `12.3144` | The OSM administrative relation provides the destination identity and representative coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_destination:kirchberg` | `price_level` | [Official Brixental accommodation booking](https://www.kitzbueheler-alpen.com/en/bri/booking.html) | `"bookable accommodation inventory"` | The official booking surface demonstrates a broad, bookable accommodation market. | The active booking inventory is normalized to a medium product price tier pending a formal sampling policy. |
| `stay_destination:kirchberg` | `region` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"Tyrol"` | Official tourism material supports the destination identity and Tyrol location. |  |
| `stay_destination:kirchberg` | `regional_data_ids` | [OpenStreetMap relation 541914](https://www.openstreetmap.org/relation/541914) | `{"osm_relation_id": "541914"}` | The OSM administrative relation provides the destination identity and representative coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_destination:kirchberg` | `stay_destination_id` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"kirchberg"` | Official tourism material supports the destination identity and Tyrol location. |  |
| `stay_destination:kirchberg` | `trip_market_region_id` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"kitzbuhel"` | Official tourism material supports the destination identity and Tyrol location. | The official destination identity is normalized into Snowcast ownership. |
| `stay_base:jochberg-jochberg` | `base_character.development_style` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"Peaceful village, slower pace, historic farmhouses, and authentic Tyrolean character."` | The official profile supports traditional development and a quiet local pace. | The descriptive wording is normalized to traditional and quiet. |
| `stay_base:jochberg-jochberg` | `base_character.local_pace` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"Peaceful village, slower pace, historic farmhouses, and authentic Tyrolean character."` | The official profile supports traditional development and a quiet local pace. | The descriptive wording is normalized to traditional and quiet. |
| `stay_base:jochberg-jochberg` | `base_type` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"village"` | Official tourism material supports the stay-base identity, village type, elevation, and ownership. |  |
| `stay_base:jochberg-jochberg` | `elevation_m` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `924` | Official tourism material supports the stay-base identity, village type, elevation, and ownership. |  |
| `stay_base:jochberg-jochberg` | `latitude` | [OpenStreetMap Jochberg village node](https://www.openstreetmap.org/node/240102052) | `47.3805` | The OSM village node provides the representative stay-base identity and coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_base:jochberg-jochberg` | `local_apres_profile.availability` | [Hofalm Jochberg apres profile](https://www.kitzbuehel.com/en/holiday/kitz-a-z/infrastructure/hofalm-jochberg-jochberg/) | `"Daily apres from mid-December, with weekly live music and DJ nights through mid-April 2026."` | The official recurring venue schedule supports local apres availability without a destination-defining scene. | The recurring programme is normalized to available, moderate, and Winter 2025/26 where applicable. |
| `stay_base:jochberg-jochberg` | `local_apres_profile.intensity` | [Hofalm Jochberg apres profile](https://www.kitzbuehel.com/en/holiday/kitz-a-z/infrastructure/hofalm-jochberg-jochberg/) | `"Daily apres from mid-December, with weekly live music and DJ nights through mid-April 2026."` | The official recurring venue schedule supports local apres availability without a destination-defining scene. | The recurring programme is normalized to available, moderate, and Winter 2025/26 where applicable. |
| `stay_base:jochberg-jochberg` | `local_apres_profile.season_label` | [Hofalm Jochberg apres profile](https://www.kitzbuehel.com/en/holiday/kitz-a-z/infrastructure/hofalm-jochberg-jochberg/) | `"Daily apres from mid-December, with weekly live music and DJ nights through mid-April 2026."` | The official recurring venue schedule supports local apres availability without a destination-defining scene. | The recurring programme is normalized to available, moderate, and Winter 2025/26 where applicable. |
| `stay_base:jochberg-jochberg` | `longitude` | [OpenStreetMap Jochberg village node](https://www.openstreetmap.org/node/240102052) | `12.418` | The OSM village node provides the representative stay-base identity and coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_base:jochberg-jochberg` | `name` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"Jochberg"` | Official tourism material supports the stay-base identity, village type, elevation, and ownership. |  |
| `stay_base:jochberg-jochberg` | `price_max` | [Official Jochberg accommodation listing](https://www.kitzbuehel.com/urlaub/unterkunft-buchen/details/gaestehaus-jochberg/) | `"official bookable lodging inventory without a canonical market-wide price distribution"` | The official booking surface confirms lodging inventory for the base. | Representative price and quality values remain product-curated estimates pending a formal sampling policy. |
| `stay_base:jochberg-jochberg` | `price_min` | [Official Jochberg accommodation listing](https://www.kitzbuehel.com/urlaub/unterkunft-buchen/details/gaestehaus-jochberg/) | `"official bookable lodging inventory without a canonical market-wide price distribution"` | The official booking surface confirms lodging inventory for the base. | Representative price and quality values remain product-curated estimates pending a formal sampling policy. |
| `stay_base:jochberg-jochberg` | `price_range` | [Official Jochberg accommodation listing](https://www.kitzbuehel.com/urlaub/unterkunft-buchen/details/gaestehaus-jochberg/) | `"official bookable lodging inventory without a canonical market-wide price distribution"` | The official booking surface confirms lodging inventory for the base. | Representative price and quality values remain product-curated estimates pending a formal sampling policy. |
| `stay_base:jochberg-jochberg` | `quality` | [Official Jochberg accommodation listing](https://www.kitzbuehel.com/urlaub/unterkunft-buchen/details/gaestehaus-jochberg/) | `"official bookable lodging inventory without a canonical market-wide price distribution"` | The official booking surface confirms lodging inventory for the base. | Representative price and quality values remain product-curated estimates pending a formal sampling policy. |
| `stay_base:jochberg-jochberg` | `regional_data_ids` | [OpenStreetMap Jochberg village node](https://www.openstreetmap.org/node/240102052) | `{"osm_node_id": "240102052"}` | The OSM village node provides the representative stay-base identity and coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_base:jochberg-jochberg` | `stay_base_id` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"jochberg-jochberg"` | Official tourism material supports the stay-base identity, village type, elevation, and ownership. |  |
| `stay_base:jochberg-jochberg` | `stay_destination_id` | [Jochberg destination profile](https://www.kitzbuehel.com/en/jochberg/) | `"jochberg"` | Official tourism material supports the stay-base identity, village type, elevation, and ownership. | The stay destination relationship is normalized into Snowcast ownership. |
| `stay_base:kirchberg-kirchberg` | `base_character.development_style` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"Picture-perfect village centre, modern lifts, events, shops, restaurants, and active apres."` | The official profile supports mixed development and a lively pace. | The traditional centre and modern tourism offer are normalized to mixed and lively. |
| `stay_base:kirchberg-kirchberg` | `base_character.local_pace` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"Picture-perfect village centre, modern lifts, events, shops, restaurants, and active apres."` | The official profile supports mixed development and a lively pace. | The traditional centre and modern tourism offer are normalized to mixed and lively. |
| `stay_base:kirchberg-kirchberg` | `base_type` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"village"` | Official tourism material supports the stay-base identity, village type, elevation, and ownership. |  |
| `stay_base:kirchberg-kirchberg` | `elevation_m` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `832` | Official tourism material supports the stay-base identity, village type, elevation, and ownership. |  |
| `stay_base:kirchberg-kirchberg` | `latitude` | [OpenStreetMap Kirchberg village node](https://www.openstreetmap.org/node/240062251) | `47.4476` | The OSM village node provides the representative stay-base identity and coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_base:kirchberg-kirchberg` | `local_apres_profile.availability` | [Brixental apres inventory](https://www.kitzbueheler-alpen.com/en/bri/wi/ski/apresski.html) | `"Kirchberg and the Brixental villages offer slope-side and village apres ranging from laid-back to lively."` | The official inventory supports a broad, lively local apres offer in Kirchberg. | The source wording and venue breadth are normalized to available and lively. |
| `stay_base:kirchberg-kirchberg` | `local_apres_profile.intensity` | [Brixental apres inventory](https://www.kitzbueheler-alpen.com/en/bri/wi/ski/apresski.html) | `"Kirchberg and the Brixental villages offer slope-side and village apres ranging from laid-back to lively."` | The official inventory supports a broad, lively local apres offer in Kirchberg. | The source wording and venue breadth are normalized to available and lively. |
| `stay_base:kirchberg-kirchberg` | `longitude` | [OpenStreetMap Kirchberg village node](https://www.openstreetmap.org/node/240062251) | `12.3144` | The OSM village node provides the representative stay-base identity and coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_base:kirchberg-kirchberg` | `name` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"Kirchberg in Tirol"` | Official tourism material supports the stay-base identity, village type, elevation, and ownership. |  |
| `stay_base:kirchberg-kirchberg` | `price_max` | [Official Brixental accommodation booking](https://www.kitzbueheler-alpen.com/en/bri/booking.html) | `"official bookable lodging inventory without a canonical market-wide price distribution"` | The official booking surface confirms lodging inventory for the base. | Representative price and quality values remain product-curated estimates pending a formal sampling policy. |
| `stay_base:kirchberg-kirchberg` | `price_min` | [Official Brixental accommodation booking](https://www.kitzbueheler-alpen.com/en/bri/booking.html) | `"official bookable lodging inventory without a canonical market-wide price distribution"` | The official booking surface confirms lodging inventory for the base. | Representative price and quality values remain product-curated estimates pending a formal sampling policy. |
| `stay_base:kirchberg-kirchberg` | `price_range` | [Official Brixental accommodation booking](https://www.kitzbueheler-alpen.com/en/bri/booking.html) | `"official bookable lodging inventory without a canonical market-wide price distribution"` | The official booking surface confirms lodging inventory for the base. | Representative price and quality values remain product-curated estimates pending a formal sampling policy. |
| `stay_base:kirchberg-kirchberg` | `quality` | [Official Brixental accommodation booking](https://www.kitzbueheler-alpen.com/en/bri/booking.html) | `"official bookable lodging inventory without a canonical market-wide price distribution"` | The official booking surface confirms lodging inventory for the base. | Representative price and quality values remain product-curated estimates pending a formal sampling policy. |
| `stay_base:kirchberg-kirchberg` | `regional_data_ids` | [OpenStreetMap Kirchberg village node](https://www.openstreetmap.org/node/240062251) | `{"osm_node_id": "240062251"}` | The OSM village node provides the representative stay-base identity and coordinate. | OSM geometry is rounded to the catalog coordinate precision. |
| `stay_base:kirchberg-kirchberg` | `stay_base_id` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"kirchberg-kirchberg"` | Official tourism material supports the stay-base identity, village type, elevation, and ownership. |  |
| `stay_base:kirchberg-kirchberg` | `stay_destination_id` | [Kirchberg destination profile](https://www.kitzbueheler-alpen.com/en/bri/kirchberg.html) | `"kirchberg"` | Official tourism material supports the stay-base identity, village type, elevation, and ownership. | The stay destination relationship is normalized into Snowcast ownership. |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `access_mode` | [Jochberg direct KitzSki access](https://www.kitzbuehel.com/en/jochberg/) | `"walk"` | Official destination and lift material supports the stay-base-to-KitzSki relationship. | Official village-to-Wagstättbahn access is normalized to the walk access mode. |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `distance_m` | [OpenStreetMap Wagstättbahn valley station](https://www.openstreetmap.org/node/3097464362) | `{"base": [47.3804596, 12.4180047], "lift": [47.3776074, 12.4181819]}` | OSM village and valley-station geometry supports the rounded point-to-point distance. | Haversine distance is rounded to the nearest practical catalog value and mapped to the lift-distance bucket. |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `is_direct` | [Jochberg direct KitzSki access](https://www.kitzbuehel.com/en/jochberg/) | `true` | The official access description supports whether the base reaches KitzSki directly or by ski bus. | Directness is normalized from the published access mode. |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `lift_distance` | [OpenStreetMap Wagstättbahn valley station](https://www.openstreetmap.org/node/3097464362) | `320` | OSM village and valley-station geometry supports the rounded point-to-point distance. | Haversine distance is rounded to the nearest practical catalog value and mapped to the lift-distance bucket. |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `nearest_lift_name` | [OpenStreetMap Wagstättbahn valley station](https://www.openstreetmap.org/node/3097464362) | `"Wagstättbahn"` | The OSM lift object provides the nearest-lift identity and stored geometry provenance. |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `regional_data_ids` | [OpenStreetMap Wagstättbahn valley station](https://www.openstreetmap.org/node/3097464362) | `{"nearest_lift_osm_node_id": "3097464362"}` | The OSM lift object provides the nearest-lift identity and stored geometry provenance. | The selected valley-station object is stored on the access edge. |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `ski_area_access_id` | [Jochberg direct KitzSki access](https://www.kitzbuehel.com/en/jochberg/) | `"jochberg-jochberg--kitzbuhel-ski-area"` | Official destination and lift material supports the stay-base-to-KitzSki relationship. |  |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `ski_area_id` | [Jochberg direct KitzSki access](https://www.kitzbuehel.com/en/jochberg/) | `"kitzbuhel-ski-area"` | Official destination and lift material supports the stay-base-to-KitzSki relationship. | The relationship is normalized into the explicit Snowcast access graph. |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `source_urls` | [Jochberg direct KitzSki access](https://www.kitzbuehel.com/en/jochberg/) | `["https://www.kitzbuehel.com/en/jochberg/", "https://www.openstreetmap.org/node/240102052", "https://www.openstreetmap.org/node/3097464362"]` | The stored source set combines direct official access evidence with the exact OSM place and lift objects. | Official and open-data sources are grouped on the access edge. |
| `ski_area_access:jochberg-jochberg--kitzbuhel-ski-area` | `stay_base_id` | [Jochberg direct KitzSki access](https://www.kitzbuehel.com/en/jochberg/) | `"jochberg-jochberg"` | Official destination and lift material supports the stay-base-to-KitzSki relationship. | The relationship is normalized into the explicit Snowcast access graph. |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `access_mode` | [Brixental ski buses](https://www.kitzbueheler-alpen.com/en/bri/wi/ski/busses.html) | `"Free ski buses take guests from accommodation in Kirchberg to KitzSki valley stations."` | The official regional mobility page directly supports ski-bus access. | The published transport offer is normalized to access_mode=ski_bus. |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `distance_m` | [OpenStreetMap Fleckalmbahn valley-station building](https://www.openstreetmap.org/way/125149747) | `{"base": [47.4475913, 12.3144495], "lift": [47.4503842, 12.3350551]}` | OSM village and valley-station geometry supports the rounded point-to-point distance. | Haversine distance is rounded to the nearest practical catalog value and mapped to the lift-distance bucket. |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `is_direct` | [Fleckalmbahn KitzSki access](https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/fleckalmbahn.html) | `false` | The official access description supports whether the base reaches KitzSki directly or by ski bus. | Directness is normalized from the published access mode. |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `lift_distance` | [OpenStreetMap Fleckalmbahn valley-station building](https://www.openstreetmap.org/way/125149747) | `1580` | OSM village and valley-station geometry supports the rounded point-to-point distance. | Haversine distance is rounded to the nearest practical catalog value and mapped to the lift-distance bucket. |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `nearest_lift_name` | [OpenStreetMap Fleckalmbahn valley-station building](https://www.openstreetmap.org/way/125149747) | `"Fleckalmbahn"` | The OSM lift object provides the nearest-lift identity and stored geometry provenance. |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `regional_data_ids` | [OpenStreetMap Fleckalmbahn valley-station building](https://www.openstreetmap.org/way/125149747) | `{"nearest_lift_osm_way_id": "125149747"}` | The OSM lift object provides the nearest-lift identity and stored geometry provenance. | The selected valley-station object is stored on the access edge. |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `ski_area_access_id` | [Fleckalmbahn KitzSki access](https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/fleckalmbahn.html) | `"kirchberg-kirchberg--kitzbuhel-ski-area"` | Official destination and lift material supports the stay-base-to-KitzSki relationship. |  |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `ski_area_id` | [Fleckalmbahn KitzSki access](https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/fleckalmbahn.html) | `"kitzbuhel-ski-area"` | Official destination and lift material supports the stay-base-to-KitzSki relationship. | The relationship is normalized into the explicit Snowcast access graph. |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `source_urls` | [Fleckalmbahn KitzSki access](https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/fleckalmbahn.html) | `["https://www.kitzbueheler-alpen.com/en/bri/wi/ski/busses.html", "https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/fleckalmbahn.html", "https://www.openstreetmap.org/node/240062251", "https://www.openstreetmap.org/way/125149747"]` | The stored source set combines direct official access evidence with the exact OSM place and lift objects. | Official and open-data sources are grouped on the access edge. |
| `ski_area_access:kirchberg-kirchberg--kitzbuhel-ski-area` | `stay_base_id` | [Fleckalmbahn KitzSki access](https://www.kitzbueheler-alpen.com/en/bri/infra/a-z/fleckalmbahn.html) | `"kirchberg-kirchberg"` | Official destination and lift material supports the stay-base-to-KitzSki relationship. | The relationship is normalized into the explicit Snowcast access graph. |
| `lift_pass_product:kitzski-skipass` | `available_from_stay_destination_ids` | [KitzSki ski-pass scope](https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html) | `["jochberg", "kirchberg", "kitzbuhel"]` | Official KitzSki material supports the named product and its availability across the modeled KitzSki stay markets. | Published product coverage is normalized into Snowcast availability and modeled ski-area relationships. |
| `lift_pass_product:kitzski-skipass` | `lift_pass_product_id` | [KitzSki ski-pass scope](https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html) | `"kitzski-skipass"` | Official KitzSki material supports the named product and its availability across the modeled KitzSki stay markets. |  |
| `lift_pass_product:kitzski-skipass` | `name` | [KitzSki ski-pass scope](https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html) | `"KitzSki Ski Pass"` | Official KitzSki material supports the named product and its availability across the modeled KitzSki stay markets. |  |
| `lift_pass_product:kitzski-skipass` | `prices` | [KitzSki 2026/27 tariff](https://www.kitzski.at/media/preise-26-27-hp-en.pdf) | `[{"amount": 83.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 premium season cash desk", "source_url": "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"}, {"amount": 244.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 premium season cash desk", "source_url": "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"}, {"amount": 423.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 premium season cash desk", "source_url": "https://www.kitzski.at/media/preise-26-27-hp-en.pdf"}]` | The official tariff publishes the adult premium-season cash-desk prices for 1, 3, and 6 days. |  |
| `lift_pass_product:kitzski-skipass` | `valid_ski_area_ids` | [KitzSki ski-pass scope](https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html) | `["kitzbuhel-ski-area"]` | Official KitzSki material supports the named product and its availability across the modeled KitzSki stay markets. | Published product coverage is normalized into Snowcast availability and modeled ski-area relationships. |
| `lift_pass_product:kitzski-skipass` | `validity_scope` | [KitzSki ski-pass scope](https://www.kitzski.at/en/tickets-vouchers/ski-passes-for-kitzbuehel-kirchberg-mittersill.html) | `"single_ski_area"` | Official KitzSki material supports the named product and its availability across the modeled KitzSki stay markets. | Published product coverage is normalized into Snowcast availability and modeled ski-area relationships. |

## Boundary Decisions

- `kitzbuhel`: `pass`
- `jochberg`: `pass`
- `kirchberg`: `pass`

## Ranking Impact

The catalog adds two stay contexts and explicit access edges while retaining the existing KitzSki terrain owner and calculation policy.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation typed docs/catalog-curation/2026-06-26-kitzbuhel-full-curation.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output docs/catalog-curation/2026-06-26-kitzbuhel-full-curation.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation reconcile docs/catalog-curation/2026-06-26-kitzbuhel-full-curation.json --base-catalog-path BASE/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output docs/catalog-curation/2026-06-26-kitzbuhel-full-curation.md`

## Caveats

- Exact 2026/27 opening and closing dates remain unresolved; the reviewed KitzSki tariff sources provide price bands rather than a complete operating window.
- KitzSki publishes 233 total run kilometres while the official blue/red/black prepared-piste inventory sums to 181 km; the catalog retains the difficulty-backed value and records the broader scope without averaging them.
- The retained kitzbuhel-ski-area weather owner remains a coarse KitzSki representation pending the consolidated Kitzbüheler Horn, Gaisberg, Bichlalm, and western-market migration.
- Accommodation and rental price ranges and quality tiers remain product-curated estimates pending a reviewed provider sampling policy.
- Current official KitzSki material does not establish a recurring downhill night-skiing offer for the modeled ski area; Gaisberg evening sledding and piste touring do not satisfy this fact.
- Family fun areas and the Jufenbeach skill park are not counted as dedicated snowparks; the operator explicitly describes two snowparks.
