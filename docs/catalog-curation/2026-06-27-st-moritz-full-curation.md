# St. Moritz Catalog Curation - Corviglia and Celerina scope correction

Rebuilds PR #19 on current main and corrects the Upper Engadin graph around Corviglia / Piz Nair. St. Moritz is split into Dorf, Bad and Suvretta stay bases, Celerina is added as a separate stay destination and base, and each receives an explicit source-backed feeder relationship. Corviglia retains one operating owner with official terrain metrics and map; the broader disconnected Upper Engadin pass context is represented without inventing a connected terrain domain. Missing Upper Engadin destinations and ski-area owners are explicitly deferred to the catalog-curation backlog. Celerina elevation is resolved from the official municipality profile, and the latest official exact Corviglia window is retained for Winter 2025/26 while 2026/27 remains unpublished.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `full` | all canonical fields |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `full` | all canonical fields |
| `ski_area:st-moritz-ski-area` | `full` | all canonical fields |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `full` | all canonical fields |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `full` | all canonical fields |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `full` | all canonical fields |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `full` | all canonical fields |
| `ski_region:st-moritz` | `full` | all canonical fields |
| `stay_base:celerina-celerina` | `full` | all canonical fields |
| `stay_base:st-moritz-st-moritz` | `full` | all canonical fields |
| `stay_base:st-moritz-st-moritz-bad` | `full` | all canonical fields |
| `stay_base:st-moritz-suvretta` | `full` | all canonical fields |
| `stay_destination:celerina` | `full` | all canonical fields |
| `stay_destination:st-moritz` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:engadin-st-moritz-day-multiday-ski-ticket` | `full` | all canonical fields |
| `trust_manifest:rental_display_facts:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:celerina-celerina--st-moritz-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:st-moritz-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_regions:st-moritz` | `full` | all canonical fields |
| `trust_manifest:stay_bases:celerina-celerina` | `full` | all canonical fields |
| `trust_manifest:stay_bases:st-moritz-st-moritz` | `full` | all canonical fields |
| `trust_manifest:stay_bases:st-moritz-st-moritz-bad` | `full` | all canonical fields |
| `trust_manifest:stay_bases:st-moritz-suvretta` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:celerina` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:st-moritz` | `full` | all canonical fields |

## Entity Scope Assessments

| Candidate | Kind | Disposition | Signals | Catalog Targets | Evidence | Backlog | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `st-moritz` (St. Moritz) | `stay_destination` | `represented` | `independent_stay_market`, `distinct_access` | `stay_destination:st-moritz` | `change-111` |  | Official tourism and distinct Dorf/Bad/Suvretta access support the retained destination. |
| `celerina` (Celerina/Schlarigna) | `stay_destination` | `add_entity` | `independent_stay_market`, `distinct_access` | `stay_destination:celerina` | `change-104` |  | Official tourism treats Celerina as its own accommodation destination with direct Marguns access. |
| `st-moritz-dorf` (St. Moritz Dorf) | `stay_base` | `represented` | `distinct_access` | `stay_base:st-moritz-st-moritz` | `change-082` |  | The retained base is narrowed to the Dorf and Chantarella access context. |
| `st-moritz-bad` (St. Moritz Bad) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:st-moritz-st-moritz-bad` | `change-087` |  | Bad has a distinct settlement and Signal feeder relationship. |
| `suvretta` (Suvretta) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:st-moritz-suvretta` | `change-097` |  | Suvretta has a distinct ski-in/ski-out lodging and feeder context. |
| `celerina-base` (Celerina/Schlarigna base) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:celerina-celerina` | `change-070` |  | The representative village base owns Celerina lodging and Marguns access. |
| `corviglia-piz-nair` (Corviglia / Piz Nair) | `ski_area` | `represented` | `official_independent_identity`, `independent_status_or_schedule`, `child_scoped_terrain_metrics` | `ski_area:st-moritz-ski-area` | `change-024` |  | The operator publishes one Corviglia owner with its own metrics, facilities and map. |
| `dorf-corviglia-access` (Dorf to Corviglia) | `ski_area_access` | `represented` | `direct_access_relationship` | `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `change-035` |  | Chantarella is the documented Dorf feeder. |
| `bad-corviglia-access` (Bad to Corviglia) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `change-047` |  | Signal is the documented Bad feeder. |
| `suvretta-corviglia-access` (Suvretta to Corviglia) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `change-057` |  | The Suvretta lifts provide direct access. |
| `celerina-corviglia-access` (Celerina to Corviglia) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:celerina-celerina--st-moritz-ski-area` | `change-031` |  | Marguns is the documented Celerina feeder. |
| `upper-engadin-snow-deal` (Upper Engadin Snow-Deal) | `lift_pass_product` | `add_entity` | `official_product_identity` | `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `change-004` |  | The official booking flow establishes a separate regional pass product. |
| `provuler` (Provulèr) | `ski_area` | `not_separate` | `official_map_sector`, `limited_area_ticket` | `ski_area:st-moritz-ski-area` | `scope-provuler-sector` |  | Provulèr is a Corviglia sector, not an independently operated weather owner. |
| `upper-engadin-domain` (Upper Engadin pass coverage) | `terrain_domain` | `external_pass_context` | `official_product_identity` |  | `scope-upper-engadin-ticket` |  | The pass spans disconnected terrain, so it must not create a connected terrain domain. |
| `corvatsch-furtschellas-ski-area` (Corvatsch / Furtschellas) | `ski_area` | `deferred` | `official_independent_identity`, `disconnected_terrain` |  | `scope-upper-engadin-ticket` | `docs/product-backlog.md#upper-engadin-catalog-extension` | The official product names this separate area, but adding its full owner, weather and access graph would make this PR too broad. |
| `diavolezza-lagalb-ski-area` (Diavolezza / Lagalb) | `ski_area` | `deferred` | `official_independent_identity`, `disconnected_terrain` |  | `scope-upper-engadin-ticket` | `docs/product-backlog.md#upper-engadin-catalog-extension` | The official product names this separate area, but adding its full owner, weather and access graph would make this PR too broad. |
| `zuoz-ski-area` (Zuoz) | `ski_area` | `deferred` | `official_independent_identity`, `disconnected_terrain` |  | `scope-upper-engadin-ticket` | `docs/product-backlog.md#upper-engadin-catalog-extension` | The official product names this separate area, but adding its full owner, weather and access graph would make this PR too broad. |
| `pontresina-languard-ski-area` (Pontresina / Languard) | `ski_area` | `deferred` | `official_independent_identity`, `disconnected_terrain` |  | `scope-upper-engadin-ticket` | `docs/product-backlog.md#upper-engadin-catalog-extension` | The official product names this separate area, but adding its full owner, weather and access graph would make this PR too broad. |
| `samedan-ski-area` (Samedan) | `ski_area` | `deferred` | `official_independent_identity`, `disconnected_terrain` |  | `scope-upper-engadin-ticket` | `docs/product-backlog.md#upper-engadin-catalog-extension` | The official product names this separate area, but adding its full owner, weather and access graph would make this PR too broad. |
| `la-punt-ski-area` (La Punt) | `ski_area` | `deferred` | `official_independent_identity`, `disconnected_terrain` |  | `scope-upper-engadin-ticket` | `docs/product-backlog.md#upper-engadin-catalog-extension` | The official product names this separate area, but adding its full owner, weather and access graph would make this PR too broad. |
| `maloja-ski-area` (Maloja) | `ski_area` | `deferred` | `official_independent_identity`, `disconnected_terrain` |  | `scope-upper-engadin-ticket` | `docs/product-backlog.md#upper-engadin-catalog-extension` | The official product names this separate area, but adding its full owner, weather and access graph would make this PR too broad. |
| `s-chanf-ski-area` (S-chanf) | `ski_area` | `deferred` | `official_independent_identity`, `disconnected_terrain` |  | `scope-upper-engadin-ticket` | `docs/product-backlog.md#upper-engadin-catalog-extension` | The official product names this separate area, but adding its full owner, weather and access graph would make this PR too broad. |
| `silvaplana` (Silvaplana) | `stay_destination` | `deferred` | `independent_stay_market` |  | `scope-engadin-holiday-resorts` | `docs/product-backlog.md#upper-engadin-catalog-extension` | Official tourism identifies a separate holiday resort, but its bases and access graph belong in a focused follow-up. |
| `sils` (Sils) | `stay_destination` | `deferred` | `independent_stay_market` |  | `scope-engadin-holiday-resorts` | `docs/product-backlog.md#upper-engadin-catalog-extension` | Official tourism identifies a separate holiday resort, but its bases and access graph belong in a focused follow-up. |
| `pontresina` (Pontresina) | `stay_destination` | `deferred` | `independent_stay_market` |  | `scope-engadin-holiday-resorts` | `docs/product-backlog.md#upper-engadin-catalog-extension` | Official tourism identifies a separate holiday resort, but its bases and access graph belong in a focused follow-up. |
| `zuoz` (Zuoz) | `stay_destination` | `deferred` | `independent_stay_market` |  | `scope-engadin-holiday-resorts` | `docs/product-backlog.md#upper-engadin-catalog-extension` | Official tourism identifies a separate holiday resort, but its bases and access graph belong in a focused follow-up. |
| `samedan` (Samedan) | `stay_destination` | `deferred` | `independent_stay_market` |  | `scope-engadin-holiday-resorts` | `docs/product-backlog.md#upper-engadin-catalog-extension` | Official tourism identifies a separate holiday resort, but its bases and access graph belong in a focused follow-up. |
| `la-punt-chamues-ch` (La Punt Chamues-ch) | `stay_destination` | `deferred` | `independent_stay_market` |  | `scope-engadin-holiday-resorts` | `docs/product-backlog.md#upper-engadin-catalog-extension` | Official tourism identifies a separate holiday resort, but its bases and access graph belong in a focused follow-up. |
| `maloja` (Maloja) | `stay_destination` | `deferred` | `independent_stay_market` |  | `scope-engadin-holiday-resorts` | `docs/product-backlog.md#upper-engadin-catalog-extension` | Official tourism identifies a separate holiday resort, but its bases and access graph belong in a focused follow-up. |
| `s-chanf` (S-chanf) | `stay_destination` | `deferred` | `independent_stay_market` |  | `scope-engadin-holiday-resorts` | `docs/product-backlog.md#upper-engadin-catalog-extension` | Official tourism identifies a separate holiday resort, but its bases and access graph belong in a focused follow-up. |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `available_from_stay_destination_ids` | `null` | `["celerina", "st-moritz"]` | `verified_with_adjustment` | no |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `default_for_stay_destination_ids` | `null` | `["st-moritz"]` | `verified_with_adjustment` | no |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `external_validity_summary` | `null` | `"Upper Engadin day and multi-day tickets cover Corvatsch/Furtschellas, Corviglia/Piz Nair, Diavolezza/Lagalb, Muottas Muragl, Zuoz, Pontresina/Languard, Samedan, La Punt, Maloja and S-chanf; only Corviglia/Piz Nair is currently modeled in Snowcast."` | `verified_with_adjustment` | no |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `lift_pass_product_id` | `null` | `"engadin-st-moritz-day-multiday-ski-ticket"` | `verified_with_adjustment` | no |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `name` | `null` | `"Upper Engadin Snow-Deal day and multi-day ski ticket"` | `verified_with_adjustment` | no |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `prices` | `null` | `[]` | `needs_source` | no |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | no |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `valid_ski_area_ids` | `null` | `["st-moritz-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `stay_base_id` | `null` | `"st-moritz-st-moritz"` | `verified` | no |
| `ski_area:st-moritz-ski-area` | `base_elevation_m` | `1856` | `1730` | `verified_with_adjustment` | yes |
| `ski_area:st-moritz-ski-area` | `name` | `"St Moritz"` | `"Corviglia / Piz Nair"` | `estimated` | no |
| `ski_area:st-moritz-ski-area` | `official_trail_map.season_label` | `null` | `"2025/26"` | `verified` | no |
| `ski_area:st-moritz-ski-area` | `official_trail_map.url` | `null` | `"https://www.mountains.ch/fileadmin/user_upload/Bilddatenbank_HP/Organisation/Dokumente/Panoramakarten/web_2025_Panoramakarte_Corviglia_Winter_504x420_Karte_vorne.pdf"` | `verified` | no |
| `ski_area:st-moritz-ski-area` | `piste_km_by_difficulty.advanced` | `null` | `34.0` | `verified_with_adjustment` | yes |
| `ski_area:st-moritz-ski-area` | `piste_km_by_difficulty.beginner` | `null` | `42.0` | `verified_with_adjustment` | yes |
| `ski_area:st-moritz-ski-area` | `piste_km_by_difficulty.intermediate` | `null` | `79.0` | `verified_with_adjustment` | yes |
| `ski_area:st-moritz-ski-area` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `ski_area:st-moritz-ski-area` | `season_windows` | `[]` | `[{"end_date": "2026-04-06", "season_label": "Winter 2025/26", "start_date": "2025-11-29", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:st-moritz-ski-area` | `ski_day_apres_profile.availability` | `"unknown"` | `"available"` | `verified_with_adjustment` | yes |
| `ski_area:st-moritz-ski-area` | `ski_day_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | yes |
| `ski_area:st-moritz-ski-area` | `snow_park.availability` | `"unknown"` | `"available"` | `verified` | yes |
| `ski_area:st-moritz-ski-area` | `snow_park.park_count` | `null` | `1` | `verified` | yes |
| `ski_area:st-moritz-ski-area` | `snowmaking.availability` | `"unknown"` | `"available"` | `verified` | yes |
| `ski_area:st-moritz-ski-area` | `supported_skill_levels` | `["intermediate", "advanced"]` | `["beginner", "intermediate", "advanced"]` | `verified` | yes |
| `ski_area:st-moritz-ski-area` | `total_lift_count` | `null` | `24` | `verified_with_adjustment` | yes |
| `ski_area:st-moritz-ski-area` | `total_piste_km` | `null` | `155.0` | `verified_with_adjustment` | yes |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `access_mode` | `null` | `"mixed"` | `verified_with_adjustment` | yes |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `distance_m` | `null` | `464` | `verified_with_adjustment` | yes |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `is_direct` | `null` | `false` | `verified_with_adjustment` | yes |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `nearest_lift_name` | `null` | `"Celerina - Marguns gondola"` | `verified_with_adjustment` | no |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "665939771"}` | `verified_with_adjustment` | no |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `ski_area_access_id` | `null` | `"celerina-celerina--st-moritz-ski-area"` | `verified` | no |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `ski_area_id` | `null` | `"st-moritz-ski-area"` | `verified` | no |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `source_urls` | `null` | `["https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina", "https://www.openstreetmap.org/node/665939771", "https://www.openstreetmap.org/relation/1684062"]` | `verified_with_adjustment` | no |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `stay_base_id` | `null` | `"celerina-celerina"` | `verified` | no |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `distance_m` | `null` | `147` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `lift_distance` | `"medium"` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `nearest_lift_name` | `null` | `"St. Moritz Dorf - Chantarella funicular"` | `verified_with_adjustment` | no |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `regional_data_ids` | `{}` | `{"nearest_lift_osm_node_id": "309543453"}` | `verified_with_adjustment` | no |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `source_urls` | `["https://www.bergfex.com/st-moritz-corviglia/"]` | `["https://www.openstreetmap.org/node/309543453", "https://www.openstreetmap.org/relation/1684175", "https://www.stmoritz.com/en/directory/mountains/corviglia"]` | `verified_with_adjustment` | no |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `distance_m` | `null` | `671` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `is_direct` | `null` | `false` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `lift_distance` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `nearest_lift_name` | `null` | `"St. Moritz Bad - Signal cable car"` | `verified_with_adjustment` | no |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "2192847631"}` | `verified_with_adjustment` | no |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `ski_area_access_id` | `null` | `"st-moritz-st-moritz-bad--st-moritz-ski-area"` | `verified` | no |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `ski_area_id` | `null` | `"st-moritz-ski-area"` | `verified` | no |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `source_urls` | `null` | `["https://www.mountains.ch/en/facilities/", "https://www.openstreetmap.org/node/2192847631", "https://www.openstreetmap.org/node/9935735584", "https://www.stmoritz.com/en/directory/mountains/corviglia"]` | `verified_with_adjustment` | no |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `stay_base_id` | `null` | `"st-moritz-st-moritz-bad"` | `verified` | no |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `access_mode` | `null` | `"ski_in_ski_out"` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `distance_m` | `null` | `87` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `nearest_lift_name` | `null` | `"Suvretta lift"` | `verified_with_adjustment` | no |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "3445699153"}` | `verified_with_adjustment` | no |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `ski_area_access_id` | `null` | `"st-moritz-suvretta--st-moritz-ski-area"` | `verified` | no |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `ski_area_id` | `null` | `"st-moritz-ski-area"` | `verified` | no |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `source_urls` | `null` | `["https://www.mountains.ch/en/facilities/", "https://www.openstreetmap.org/node/3445699153", "https://www.openstreetmap.org/way/268146958", "https://www.stmoritz.com/en/directory/hotels/hotel-suvretta-house"]` | `verified_with_adjustment` | no |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `stay_base_id` | `null` | `"st-moritz-suvretta"` | `verified` | no |
| `ski_region:st-moritz` | `name` | `"St Moritz"` | `"Engadin St. Moritz"` | `verified_with_adjustment` | no |
| `ski_region:st-moritz` | `source_urls` | `[]` | `["https://www.engadin.ch/en/guide/engadin-holiday-resorts"]` | `verified_with_adjustment` | no |
| `stay_base:celerina-celerina` | `base_character.development_style` | `null` | `"traditional"` | `verified_with_adjustment` | yes |
| `stay_base:celerina-celerina` | `base_character.local_pace` | `null` | `"balanced"` | `verified_with_adjustment` | yes |
| `stay_base:celerina-celerina` | `base_type` | `null` | `"village"` | `verified` | yes |
| `stay_base:celerina-celerina` | `elevation_m` | `null` | `1730` | `verified` | yes |
| `stay_base:celerina-celerina` | `latitude` | `null` | `46.5122544` | `verified_with_adjustment` | no |
| `stay_base:celerina-celerina` | `local_apres_profile.availability` | `null` | `"available"` | `verified_with_adjustment` | yes |
| `stay_base:celerina-celerina` | `local_apres_profile.intensity` | `null` | `"moderate"` | `verified_with_adjustment` | yes |
| `stay_base:celerina-celerina` | `longitude` | `null` | `9.8588858` | `verified_with_adjustment` | no |
| `stay_base:celerina-celerina` | `name` | `null` | `"Celerina/Schlarigna"` | `verified` | no |
| `stay_base:celerina-celerina` | `price_max` | `null` | `270.0` | `estimated` | no |
| `stay_base:celerina-celerina` | `price_min` | `null` | `180.0` | `estimated` | no |
| `stay_base:celerina-celerina` | `price_range` | `null` | `"EUR 180-270"` | `estimated` | no |
| `stay_base:celerina-celerina` | `quality` | `null` | `"premium"` | `estimated` | no |
| `stay_base:celerina-celerina` | `regional_data_ids` | `null` | `{"osm_relation_id": "1684062"}` | `verified_with_adjustment` | no |
| `stay_base:celerina-celerina` | `stay_base_id` | `null` | `"celerina-celerina"` | `verified` | no |
| `stay_base:celerina-celerina` | `stay_destination_id` | `null` | `"celerina"` | `verified` | no |
| `stay_base:st-moritz-st-moritz` | `base_character.development_style` | `"unknown"` | `"mixed"` | `verified_with_adjustment` | yes |
| `stay_base:st-moritz-st-moritz` | `base_character.local_pace` | `"unknown"` | `"lively"` | `verified_with_adjustment` | yes |
| `stay_base:st-moritz-st-moritz` | `base_type` | `null` | `"neighbourhood"` | `verified_with_adjustment` | yes |
| `stay_base:st-moritz-st-moritz` | `elevation_m` | `null` | `1846` | `verified` | yes |
| `stay_base:st-moritz-st-moritz` | `latitude` | `null` | `46.4978958` | `verified_with_adjustment` | no |
| `stay_base:st-moritz-st-moritz` | `local_apres_profile.availability` | `"unknown"` | `"available"` | `verified_with_adjustment` | yes |
| `stay_base:st-moritz-st-moritz` | `local_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | yes |
| `stay_base:st-moritz-st-moritz` | `longitude` | `null` | `9.8392428` | `verified_with_adjustment` | no |
| `stay_base:st-moritz-st-moritz` | `name` | `"St. Moritz"` | `"St. Moritz Dorf"` | `verified_with_adjustment` | no |
| `stay_base:st-moritz-st-moritz-bad` | `base_character.development_style` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:st-moritz-st-moritz-bad` | `base_character.local_pace` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:st-moritz-st-moritz-bad` | `base_type` | `null` | `"neighbourhood"` | `verified_with_adjustment` | yes |
| `stay_base:st-moritz-st-moritz-bad` | `elevation_m` | `null` | `1772` | `verified` | yes |
| `stay_base:st-moritz-st-moritz-bad` | `latitude` | `null` | `46.4893548` | `verified` | no |
| `stay_base:st-moritz-st-moritz-bad` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:st-moritz-st-moritz-bad` | `longitude` | `null` | `9.8349515` | `verified` | no |
| `stay_base:st-moritz-st-moritz-bad` | `name` | `null` | `"St. Moritz Bad"` | `verified` | no |
| `stay_base:st-moritz-st-moritz-bad` | `price_max` | `null` | `310.0` | `estimated` | no |
| `stay_base:st-moritz-st-moritz-bad` | `price_min` | `null` | `210.0` | `estimated` | no |
| `stay_base:st-moritz-st-moritz-bad` | `price_range` | `null` | `"EUR 210-310"` | `estimated` | no |
| `stay_base:st-moritz-st-moritz-bad` | `quality` | `null` | `"premium"` | `estimated` | no |
| `stay_base:st-moritz-st-moritz-bad` | `regional_data_ids` | `null` | `{"osm_node_id": "9935735584"}` | `verified` | no |
| `stay_base:st-moritz-st-moritz-bad` | `stay_base_id` | `null` | `"st-moritz-st-moritz-bad"` | `verified` | no |
| `stay_base:st-moritz-st-moritz-bad` | `stay_destination_id` | `null` | `"st-moritz"` | `verified` | no |
| `stay_base:st-moritz-suvretta` | `base_character.development_style` | `null` | `"traditional"` | `verified_with_adjustment` | yes |
| `stay_base:st-moritz-suvretta` | `base_character.local_pace` | `null` | `"quiet"` | `verified_with_adjustment` | yes |
| `stay_base:st-moritz-suvretta` | `base_type` | `null` | `"resort_sector"` | `verified_with_adjustment` | yes |
| `stay_base:st-moritz-suvretta` | `elevation_m` | `null` | `1900` | `verified` | yes |
| `stay_base:st-moritz-suvretta` | `latitude` | `null` | `46.4848584` | `verified_with_adjustment` | no |
| `stay_base:st-moritz-suvretta` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:st-moritz-suvretta` | `longitude` | `null` | `9.8197765` | `verified_with_adjustment` | no |
| `stay_base:st-moritz-suvretta` | `name` | `null` | `"Suvretta"` | `verified` | no |
| `stay_base:st-moritz-suvretta` | `price_max` | `null` | `380.0` | `estimated` | no |
| `stay_base:st-moritz-suvretta` | `price_min` | `null` | `260.0` | `estimated` | no |
| `stay_base:st-moritz-suvretta` | `price_range` | `null` | `"EUR 260-380"` | `estimated` | no |
| `stay_base:st-moritz-suvretta` | `quality` | `null` | `"premium"` | `estimated` | no |
| `stay_base:st-moritz-suvretta` | `regional_data_ids` | `null` | `{"osm_way_id": "268146958"}` | `verified_with_adjustment` | no |
| `stay_base:st-moritz-suvretta` | `stay_base_id` | `null` | `"st-moritz-suvretta"` | `verified` | no |
| `stay_base:st-moritz-suvretta` | `stay_destination_id` | `null` | `"st-moritz"` | `verified` | no |
| `stay_destination:celerina` | `country` | `null` | `"Switzerland"` | `verified` | no |
| `stay_destination:celerina` | `latitude` | `null` | `46.5122544` | `verified_with_adjustment` | no |
| `stay_destination:celerina` | `longitude` | `null` | `9.8588858` | `verified_with_adjustment` | no |
| `stay_destination:celerina` | `name` | `null` | `"Celerina/Schlarigna"` | `verified` | no |
| `stay_destination:celerina` | `price_level` | `null` | `"high"` | `estimated` | no |
| `stay_destination:celerina` | `region` | `null` | `"Engadin"` | `verified` | no |
| `stay_destination:celerina` | `regional_data_ids` | `null` | `{"osm_relation_id": "1684062"}` | `verified_with_adjustment` | no |
| `stay_destination:celerina` | `stay_destination_id` | `null` | `"celerina"` | `verified` | no |
| `stay_destination:celerina` | `trip_market_region_id` | `null` | `"st-moritz"` | `verified` | no |
| `stay_destination:st-moritz` | `latitude` | `46.4908` | `46.4978958` | `verified_with_adjustment` | no |
| `stay_destination:st-moritz` | `longitude` | `9.8355` | `9.8392428` | `verified_with_adjustment` | no |
| `stay_destination:st-moritz` | `name` | `"St Moritz"` | `"St. Moritz"` | `verified` | no |
| `stay_destination:st-moritz` | `regional_data_ids` | `{}` | `{"osm_relation_id": "1684175"}` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:engadin-st-moritz-day-multiday-ski-ticket` | `display_name` | `null` | `"Upper Engadin Snow-Deal day and multi-day ski ticket"` | `estimated` | no |
| `trust_manifest:lift_pass_products:engadin-st-moritz-day-multiday-ski-ticket` | `field_source_refs` | `null` | `{"coverage": ["https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets"], "identity_scope_availability": ["https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets"], "pass_accessible_terrain": ["https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets"], "prices": ["https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:engadin-st-moritz-day-multiday-ski-ticket` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "needs_source"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:engadin-st-moritz-day-multiday-ski-ticket` | `notes` | `null` | `["The stored product is the Entire Upper Engadin variant of the official Snow-Deal day and multi-day ticket flow; local one-day selections are not represented by this regional product.", "Only the modeled Corviglia / Piz Nair ski area is linked directly. Other named Upper Engadin areas remain explicit deferred catalog candidates, not a connected terrain domain.", "The dynamic booking flow requires dates and passenger selection, so prices remain needs_source until representative dated quotes are captured."]` | `estimated` | no |
| `trust_manifest:rental_display_facts:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `field_source_refs` | `{"identity_ownership": [], "price_quality_access": []}` | `{"identity_ownership": ["https://www.stmoritz.com/en/directory/shopping/sports/ski-service-corvatsch-st-moritz-dorf"], "price_quality_access": ["https://www.stmoritz.com/en/directory/shopping/sports/ski-service-corvatsch-st-moritz-dorf"]}` | `estimated` | no |
| `trust_manifest:rental_display_facts:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `field_statuses` | `{"identity_ownership": "estimated", "price_quality_access": "estimated"}` | `{"identity_ownership": "verified", "price_quality_access": "estimated"}` | `estimated` | no |
| `trust_manifest:rental_display_facts:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands."]` | `["Official destination material places this rental provider in St. Moritz Dorf at the Chantarella valley station, so the display fact now owns the Dorf stay-base relationship.", "Price range, quality and lift-distance remain product estimates because no representative price-sampling policy was applied."]` | `estimated` | no |
| `trust_manifest:ski_area_access:celerina-celerina--st-moritz-ski-area` | `display_name` | `null` | `"Celerina/Schlarigna -> Corviglia / Piz Nair"` | `estimated` | no |
| `trust_manifest:ski_area_access:celerina-celerina--st-moritz-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina", "https://www.openstreetmap.org/node/665939771", "https://www.openstreetmap.org/relation/1684062"], "relationship": ["https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina", "https://www.openstreetmap.org/node/665939771", "https://www.openstreetmap.org/relation/1684062"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:celerina-celerina--st-moritz-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:celerina-celerina--st-moritz-ski-area` | `notes` | `null` | `["Official Celerina tourism identifies both the Marguns feeder and the seasonal ski bus to its valley station.", "The mixed access mode records walkable proximity plus the official ski bus; 464 m is a rounded Haversine distance from the representative Celerina relation point to OSM station node 665939771."]` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `display_name` | `"St. Moritz -> St Moritz"` | `"St. Moritz Dorf -> Corviglia / Piz Nair"` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/st-moritz-corviglia/"], "relationship": ["https://www.bergfex.com/st-moritz-corviglia/"]}` | `{"access_mode_distance": ["https://www.openstreetmap.org/node/309543453", "https://www.openstreetmap.org/relation/1684175", "https://www.stmoritz.com/en/directory/mountains/corviglia"], "relationship": ["https://www.openstreetmap.org/node/309543453", "https://www.openstreetmap.org/relation/1684175", "https://www.stmoritz.com/en/directory/mountains/corviglia"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Provider-backed relationship remains estimated; no exact distance or duration is asserted."]` | `["Official destination material names the Dorf-Chantarella feeder to Corviglia.", "The 147 m distance is a rounded Haversine calculation from the representative St. Moritz relation point to OSM station node 309543453."]` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `display_name` | `null` | `"St. Moritz Bad -> Corviglia / Piz Nair"` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.mountains.ch/en/facilities/", "https://www.openstreetmap.org/node/2192847631", "https://www.openstreetmap.org/node/9935735584", "https://www.stmoritz.com/en/directory/mountains/corviglia"], "relationship": ["https://www.mountains.ch/en/facilities/", "https://www.openstreetmap.org/node/2192847631", "https://www.openstreetmap.org/node/9935735584", "https://www.stmoritz.com/en/directory/mountains/corviglia"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `notes` | `null` | `["Official operator and destination pages identify the Signal cable car as the St. Moritz Bad feeder.", "The 671 m distance is a rounded Haversine calculation from OSM St. Moritz Bad node 9935735584 to Signal station node 2192847631."]` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `display_name` | `null` | `"Suvretta -> Corviglia / Piz Nair"` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.mountains.ch/en/facilities/", "https://www.openstreetmap.org/node/3445699153", "https://www.openstreetmap.org/way/268146958", "https://www.stmoritz.com/en/directory/hotels/hotel-suvretta-house"], "relationship": ["https://www.mountains.ch/en/facilities/", "https://www.openstreetmap.org/node/3445699153", "https://www.openstreetmap.org/way/268146958", "https://www.stmoritz.com/en/directory/hotels/hotel-suvretta-house"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `notes` | `null` | `["Official sources describe Suvretta House as ski-in/ski-out and the operator lists the Suvretta feeder lifts.", "The 87 m distance is a rounded Haversine calculation from the representative Suvretta House geometry to OSM Suvretta station node 3445699153."]` | `estimated` | no |
| `trust_manifest:ski_areas:st-moritz-ski-area` | `display_name` | `"St Moritz"` | `"Corviglia / Piz Nair"` | `estimated` | no |
| `trust_manifest:ski_areas:st-moritz-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://www.engadin.ch/de/guide/berge-bahnen/betriebszeiten-fahrplaene/betriebszeiten-bergbahnen-im-winter", "https://www.mountains.ch/fileadmin/user_upload/Bilddatenbank_HP/Organisation/Dokumente/Panoramakarten/web_2025_Panoramakarte_Corviglia_Winter_504x420_Karte_vorne.pdf", "https://www.openstreetmap.org/node/665939771", "https://www.stmoritz.com/en/directory/mountains/corviglia"], "glacier_terrain": [], "identity_coordinates": ["https://www.stmoritz.com/en/directory/mountains/corviglia"], "marked_freeride_routes": [], "night_skiing": [], "official_documents": ["https://www.mountains.ch/fileadmin/user_upload/Bilddatenbank_HP/Organisation/Dokumente/Panoramakarten/web_2025_Panoramakarte_Corviglia_Winter_504x420_Karte_vorne.pdf"], "ski_day_apres": ["https://www.mountains.ch/en/food-drink/star-bar-marguns/", "https://www.mountains.ch/en/winter/"], "skill_fit": ["https://www.mountains.ch/en/winter/skiing/pisten/"], "snow_park": ["https://www.mountains.ch/de/winter/skifahren/crowland/"], "snowmaking": ["https://www.engadin.ch/en/stories/two-lakes-in-the-name-of-sustainability"], "terrain_metrics": ["https://www.mountains.ch/en/facilities/", "https://www.mountains.ch/en/winter/skiing/pisten/", "https://www.stmoritz.com/en/directory/mountains/corviglia"]}` | `estimated` | no |
| `trust_manifest:ski_areas:st-moritz-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "needs_source", "identity_coordinates": "estimated", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "verified", "ski_day_apres": "verified_with_adjustment", "skill_fit": "verified", "snow_park": "verified", "snowmaking": "verified", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:st-moritz-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Corviglia / Piz Nair remains one weather and operating owner across St. Moritz Dorf, Bad, Suvretta and Celerina; named feeders and sectors are not split into child ski areas.", "Official current overview pages publish 155 piste km, 42/79/34 km by difficulty and 24 lifts. The winter 2025/26 live-status inventory lists 23 facilities, so the general current inventory is stored as 24 with the season-specific distinction retained here.", "Base elevation is normalized to the 1730 m Celerina-Marguns valley station, the lowest reviewed feeder; the existing weather coordinate is preserved and remains estimated.", "The stored Winter 2025/26 season window runs from the first opening of the main Corviglia feeder network on 29 November through the common closing date of 6 April; some upper and secondary lifts opened later. No official 2026/27 operating window was published at review time. Glacier terrain, night skiing and marked freeride routes remain unknown rather than inferred unavailable."]` | `estimated` | no |
| `trust_manifest:ski_regions:st-moritz` | `display_name` | `"St Moritz"` | `"Engadin St. Moritz"` | `estimated` | no |
| `trust_manifest:ski_regions:st-moritz` | `field_source_refs` | `{"identity": [], "membership_context": []}` | `{"identity": ["https://www.engadin.ch/en/guide/engadin-holiday-resorts"], "membership_context": ["https://www.engadin.ch/en/guide/engadin-holiday-resorts", "https://www.engadin.ch/en/guide/engadin-holiday-resorts/celerina"]}` | `estimated` | no |
| `trust_manifest:ski_regions:st-moritz` | `field_statuses` | `{"identity": "needs_source", "membership_context": "estimated"}` | `{"identity": "verified_with_adjustment", "membership_context": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_regions:st-moritz` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Trip-market membership is retained as reviewed migration context and remains estimated.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["The retained st-moritz region ID is normalized to the official Engadin St. Moritz holiday-market name.", "Official tourism presents St. Moritz and Celerina as distinct accommodation destinations inside the same Engadin holiday market."]` | `estimated` | no |
| `trust_manifest:stay_bases:celerina-celerina` | `display_name` | `null` | `"Celerina/Schlarigna"` | `estimated` | no |
| `trust_manifest:stay_bases:celerina-celerina` | `field_source_refs` | `null` | `{"base_character": ["https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf", "https://www.engadin.ch/en/guide/engadin-holiday-resorts/celerina"], "base_type": ["https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf", "https://www.engadin.ch/en/guide/engadin-holiday-resorts/celerina"], "coordinates": ["https://www.openstreetmap.org/relation/1684062"], "elevation": ["https://www.gemeinde-celerina.ch/celerina"], "identity_ownership": ["https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf", "https://www.engadin.ch/en/guide/engadin-holiday-resorts/celerina"], "local_apres": ["https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf", "https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina"], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:celerina-celerina` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:celerina-celerina` | `notes` | `null` | `["Official tourism presents Celerina as a traditional Engadin village with a broad lodging inventory, several bars and direct Marguns access.", "The municipality's official portrait publishes Celerina/Schlarigna at 1,730 m; the balanced pace and moderate local apres classifications normalize its cozy village identity and documented bar inventory."]` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-st-moritz` | `display_name` | `"St. Moritz"` | `"St. Moritz Dorf"` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-st-moritz` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `{"base_character": ["https://www.stmoritz.com/en/about-st-moritz-tourismus-ag", "https://www.stmoritz.com/en/directory/bars-nightlife"], "base_type": ["https://api.stmoritz.com/fileadmin/user_upload/pdf/PDF_high_altitude_training_st.moritz_DE_A4_59_.pdf", "https://www.stmoritz.com/en/directory/mountains/corviglia"], "coordinates": ["https://www.openstreetmap.org/relation/1684175"], "elevation": ["https://api.stmoritz.com/fileadmin/user_upload/pdf/PDF_high_altitude_training_st.moritz_DE_A4_59_.pdf"], "identity_ownership": ["https://api.stmoritz.com/fileadmin/user_upload/pdf/PDF_high_altitude_training_st.moritz_DE_A4_59_.pdf", "https://www.stmoritz.com/en/directory/mountains/corviglia"], "local_apres": ["https://www.stmoritz.com/en/directory/bars-nightlife"], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-st-moritz` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified_with_adjustment", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-st-moritz` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["The retained base ID is narrowed from generic St. Moritz to the Dorf accommodation and Chantarella-access context.", "The official map publishes St. Moritz Dorf at 1846 m; neighbourhood type, mixed development and lively pace are normalized from official destination and nightlife material.", "Lodging price and quality remain product estimates."]` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-st-moritz-bad` | `display_name` | `null` | `"St. Moritz Bad"` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-st-moritz-bad` | `field_source_refs` | `null` | `{"base_character": [], "base_type": ["https://www.engadin.ch/en/guide/activities/more-activities/guided-village-tour-of-st-moritz", "https://www.stmoritz.com/en/directory/mountains/corviglia"], "coordinates": ["https://www.openstreetmap.org/node/9935735584"], "elevation": ["https://www.mountains.ch/fileadmin/user_upload/Bilddatenbank_HP/Organisation/Dokumente/Panoramakarten/web_2025_Panoramakarte_Corviglia_Winter_504x420_Karte_vorne.pdf"], "identity_ownership": ["https://www.mountains.ch/en/facilities/", "https://www.stmoritz.com/en/directory/mountains/corviglia"], "local_apres": [], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-st-moritz-bad` | `field_statuses` | `null` | `{"base_character": "needs_source", "base_type": "verified_with_adjustment", "coordinates": "verified", "elevation": "verified", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-st-moritz-bad` | `notes` | `null` | `["St. Moritz Bad is modeled as a neighbourhood base because official sources distinguish the lower Bad settlement and its Signal feeder from Dorf.", "Character and local apres remain unknown; lodging price and quality remain product estimates."]` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-suvretta` | `display_name` | `null` | `"Suvretta"` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-suvretta` | `field_source_refs` | `null` | `{"base_character": ["https://www.stmoritz.com/en/directory/hotels/hotel-suvretta-house"], "base_type": ["https://www.mountains.ch/en/facilities/", "https://www.stmoritz.com/en/directory/hotels/hotel-suvretta-house"], "coordinates": ["https://www.openstreetmap.org/way/268146958"], "elevation": ["https://api.stmoritz.com/fileadmin/user_upload/pdf/PDF_high_altitude_training_st.moritz_DE_A4_59_.pdf"], "identity_ownership": ["https://www.mountains.ch/en/facilities/", "https://www.stmoritz.com/en/directory/hotels/hotel-suvretta-house"], "local_apres": [], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-suvretta` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:st-moritz-suvretta` | `notes` | `null` | `["Suvretta is modeled as a distinct resort-sector base around its ski-in/ski-out hotel and dedicated feeder lifts.", "The hotel source explicitly supports a traditional, relaxed and quiet character; local apres remains unknown and lodging price remains estimated."]` | `estimated` | no |
| `trust_manifest:stay_destinations:celerina` | `display_name` | `null` | `"Celerina/Schlarigna"` | `estimated` | no |
| `trust_manifest:stay_destinations:celerina` | `field_source_refs` | `null` | `{"coordinates": ["https://www.openstreetmap.org/relation/1684062"], "identity_location": ["https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf", "https://www.engadin.ch/en/guide/engadin-holiday-resorts/celerina"], "price_level": []}` | `estimated` | no |
| `trust_manifest:stay_destinations:celerina` | `field_statuses` | `null` | `{"coordinates": "verified_with_adjustment", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:celerina` | `notes` | `null` | `["Official tourism presents Celerina as a named holiday village with its own accommodation inventory and direct Marguns access to Corviglia.", "Coordinates use the OSM administrative-relation representative point; price level remains a product estimate."]` | `estimated` | no |
| `trust_manifest:stay_destinations:st-moritz` | `display_name` | `"St Moritz"` | `"St. Moritz"` | `estimated` | no |
| `trust_manifest:stay_destinations:st-moritz` | `field_source_refs` | `{"coordinates": [], "identity_location": [], "price_level": []}` | `{"coordinates": ["https://www.openstreetmap.org/relation/1684175"], "identity_location": ["https://www.engadin.ch/en/guide/engadin-holiday-resorts", "https://www.stmoritz.com/en/directory/mountains/corviglia"], "price_level": []}` | `estimated` | no |
| `trust_manifest:stay_destinations:st-moritz` | `field_statuses` | `{"coordinates": "needs_source", "identity_location": "needs_source", "price_level": "estimated"}` | `{"coordinates": "verified_with_adjustment", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:st-moritz` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Official tourism treats St. Moritz as an independent holiday and ski-stay destination.", "Coordinates use the OSM administrative-relation representative point; price level remains a product estimate."]` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `name` | `changed` |  |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `pass_accessible_terrain` | `unresolved` | The broad pass terrain must wait for the deferred ski-area owners and a product-level aggregation policy. |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `prices` | `changed` |  |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `validity_scope` | `changed` |  |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `lift_distance` | `reviewed-no-change` |  |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `name` | `reviewed-no-change` |  |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `price_max` | `reviewed-no-change` |  |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `price_min` | `reviewed-no-change` |  |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `price_range` | `reviewed-no-change` |  |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `quality` | `reviewed-no-change` |  |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `rental_display_fact_id` | `reviewed-no-change` |  |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `stay_base_id` | `changed` |  |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `stay_destination_id` | `reviewed-no-change` |  |
| `ski_area:st-moritz-ski-area` | `base_elevation_m` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `glacier_terrain.availability` | `unresolved` | No accepted source establishes glacier terrain for this owner. |
| `ski_area:st-moritz-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:st-moritz-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:st-moritz-ski-area` | `marked_freeride_routes.availability` | `unresolved` | No published inventory of marked freeride routes was verified. |
| `ski_area:st-moritz-ski-area` | `marked_freeride_routes.route_count` | `unresolved` | Marked freeride-route availability remains unresolved. |
| `ski_area:st-moritz-ski-area` | `marked_freeride_routes.season_label` | `unresolved` | Marked freeride-route availability remains unresolved. |
| `ski_area:st-moritz-ski-area` | `name` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `night_skiing.availability` | `unresolved` | No recurring public night-skiing product was verified. |
| `ski_area:st-moritz-ski-area` | `night_skiing.season_label` | `unresolved` | Night skiing remains unresolved, so no season label is asserted. |
| `ski_area:st-moritz-ski-area` | `official_trail_map.season_label` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `official_trail_map.url` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:st-moritz-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `season_windows` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:st-moritz-ski-area` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `ski_day_apres_profile.intensity` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `ski_day_apres_profile.season_label` | `unresolved` | The official venue evidence is not tied to one season label. |
| `ski_area:st-moritz-ski-area` | `snow_park.availability` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `snow_park.park_count` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `snow_park.season_label` | `unresolved` | The current Crowland page does not establish a season label. |
| `ski_area:st-moritz-ski-area` | `snowmaking.availability` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `snowmaking.coverage_basis` | `unresolved` | No reliable published coverage basis was found. |
| `ski_area:st-moritz-ski-area` | `snowmaking.coverage_pct` | `unresolved` | Snowmaking is official, but no reliable coverage percentage was found. |
| `ski_area:st-moritz-ski-area` | `snowmaking.season_label` | `unresolved` | The official source is not tied to one season label. |
| `ski_area:st-moritz-ski-area` | `summit_elevation_m` | `reviewed-no-change` |  |
| `ski_area:st-moritz-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:st-moritz-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `duration_minutes` | `reviewed-no-change` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `duration_minutes` | `reviewed-no-change` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `is_direct` | `reviewed-no-change` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `ski_area_access_id` | `reviewed-no-change` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `stay_base_id` | `reviewed-no-change` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `duration_minutes` | `reviewed-no-change` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `duration_minutes` | `reviewed-no-change` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `stay_base_id` | `changed` |  |
| `ski_region:st-moritz` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:st-moritz` | `name` | `changed` |  |
| `ski_region:st-moritz` | `parent_ski_region_id` | `reviewed-no-change` |  |
| `ski_region:st-moritz` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:st-moritz` | `source_urls` | `changed` |  |
| `stay_base:celerina-celerina` | `base_character.development_style` | `changed` |  |
| `stay_base:celerina-celerina` | `base_character.local_pace` | `changed` |  |
| `stay_base:celerina-celerina` | `base_type` | `changed` |  |
| `stay_base:celerina-celerina` | `elevation_m` | `changed` |  |
| `stay_base:celerina-celerina` | `latitude` | `changed` |  |
| `stay_base:celerina-celerina` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:celerina-celerina` | `local_apres_profile.intensity` | `changed` |  |
| `stay_base:celerina-celerina` | `local_apres_profile.season_label` | `reviewed-no-change` |  |
| `stay_base:celerina-celerina` | `longitude` | `changed` |  |
| `stay_base:celerina-celerina` | `name` | `changed` |  |
| `stay_base:celerina-celerina` | `price_max` | `changed` |  |
| `stay_base:celerina-celerina` | `price_min` | `changed` |  |
| `stay_base:celerina-celerina` | `price_range` | `changed` |  |
| `stay_base:celerina-celerina` | `quality` | `changed` |  |
| `stay_base:celerina-celerina` | `regional_data_ids` | `changed` |  |
| `stay_base:celerina-celerina` | `stay_base_id` | `changed` |  |
| `stay_base:celerina-celerina` | `stay_destination_id` | `changed` |  |
| `stay_base:st-moritz-st-moritz` | `base_character.development_style` | `changed` |  |
| `stay_base:st-moritz-st-moritz` | `base_character.local_pace` | `changed` |  |
| `stay_base:st-moritz-st-moritz` | `base_type` | `changed` |  |
| `stay_base:st-moritz-st-moritz` | `elevation_m` | `changed` |  |
| `stay_base:st-moritz-st-moritz` | `latitude` | `changed` |  |
| `stay_base:st-moritz-st-moritz` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:st-moritz-st-moritz` | `local_apres_profile.intensity` | `changed` |  |
| `stay_base:st-moritz-st-moritz` | `local_apres_profile.season_label` | `reviewed-no-change` |  |
| `stay_base:st-moritz-st-moritz` | `longitude` | `changed` |  |
| `stay_base:st-moritz-st-moritz` | `name` | `changed` |  |
| `stay_base:st-moritz-st-moritz` | `price_max` | `reviewed-no-change` |  |
| `stay_base:st-moritz-st-moritz` | `price_min` | `reviewed-no-change` |  |
| `stay_base:st-moritz-st-moritz` | `price_range` | `reviewed-no-change` |  |
| `stay_base:st-moritz-st-moritz` | `quality` | `reviewed-no-change` |  |
| `stay_base:st-moritz-st-moritz` | `regional_data_ids` | `reviewed-no-change` |  |
| `stay_base:st-moritz-st-moritz` | `stay_base_id` | `reviewed-no-change` |  |
| `stay_base:st-moritz-st-moritz` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_base:st-moritz-st-moritz-bad` | `base_character.development_style` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `base_character.local_pace` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `base_type` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `elevation_m` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `latitude` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `local_apres_profile.intensity` | `reviewed-no-change` |  |
| `stay_base:st-moritz-st-moritz-bad` | `local_apres_profile.season_label` | `reviewed-no-change` |  |
| `stay_base:st-moritz-st-moritz-bad` | `longitude` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `name` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `price_max` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `price_min` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `price_range` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `quality` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `regional_data_ids` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `stay_base_id` | `changed` |  |
| `stay_base:st-moritz-st-moritz-bad` | `stay_destination_id` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `base_character.development_style` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `base_character.local_pace` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `base_type` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `elevation_m` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `latitude` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `local_apres_profile.intensity` | `reviewed-no-change` |  |
| `stay_base:st-moritz-suvretta` | `local_apres_profile.season_label` | `reviewed-no-change` |  |
| `stay_base:st-moritz-suvretta` | `longitude` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `name` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `price_max` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `price_min` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `price_range` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `quality` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `regional_data_ids` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `stay_base_id` | `changed` |  |
| `stay_base:st-moritz-suvretta` | `stay_destination_id` | `changed` |  |
| `stay_destination:celerina` | `country` | `changed` |  |
| `stay_destination:celerina` | `latitude` | `changed` |  |
| `stay_destination:celerina` | `longitude` | `changed` |  |
| `stay_destination:celerina` | `name` | `changed` |  |
| `stay_destination:celerina` | `price_level` | `changed` |  |
| `stay_destination:celerina` | `region` | `changed` |  |
| `stay_destination:celerina` | `regional_data_ids` | `changed` |  |
| `stay_destination:celerina` | `stay_destination_id` | `changed` |  |
| `stay_destination:celerina` | `trip_market_region_id` | `changed` |  |
| `stay_destination:st-moritz` | `country` | `reviewed-no-change` |  |
| `stay_destination:st-moritz` | `latitude` | `changed` |  |
| `stay_destination:st-moritz` | `longitude` | `changed` |  |
| `stay_destination:st-moritz` | `name` | `changed` |  |
| `stay_destination:st-moritz` | `price_level` | `reviewed-no-change` |  |
| `stay_destination:st-moritz` | `region` | `reviewed-no-change` |  |
| `stay_destination:st-moritz` | `regional_data_ids` | `changed` |  |
| `stay_destination:st-moritz` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:st-moritz` | `trip_market_region_id` | `reviewed-no-change` |  |
| `trust_manifest:lift_pass_products:engadin-st-moritz-day-multiday-ski-ticket` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:engadin-st-moritz-day-multiday-ski-ticket` | `field_source_refs` | `changed` |  |
| `trust_manifest:lift_pass_products:engadin-st-moritz-day-multiday-ski-ticket` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:engadin-st-moritz-day-multiday-ski-ticket` | `notes` | `changed` |  |
| `trust_manifest:rental_display_facts:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:rental_display_facts:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `field_source_refs` | `changed` |  |
| `trust_manifest:rental_display_facts:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `field_statuses` | `changed` |  |
| `trust_manifest:rental_display_facts:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:celerina-celerina--st-moritz-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:celerina-celerina--st-moritz-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:celerina-celerina--st-moritz-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:celerina-celerina--st-moritz-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:st-moritz-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:st-moritz-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:st-moritz-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:st-moritz-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_regions:st-moritz` | `display_name` | `changed` |  |
| `trust_manifest:ski_regions:st-moritz` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_regions:st-moritz` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_regions:st-moritz` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:celerina-celerina` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:celerina-celerina` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:celerina-celerina` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:celerina-celerina` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-st-moritz` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-st-moritz` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-st-moritz` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-st-moritz` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-st-moritz-bad` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-st-moritz-bad` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-st-moritz-bad` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-st-moritz-bad` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-suvretta` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-suvretta` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-suvretta` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:st-moritz-suvretta` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:celerina` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:celerina` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:celerina` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:celerina` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:st-moritz` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:st-moritz` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:st-moritz` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:st-moritz` | `notes` | `changed` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `available_from_stay_destination_ids` | [Engadin Snow-Deal booking](https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets) | `["celerina", "st-moritz"]` | The cited source supports the curated identity scope availability fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `default_for_stay_destination_ids` | [Engadin Snow-Deal booking](https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets) | `["st-moritz"]` | The cited source supports the curated identity scope availability fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `external_validity_summary` | [Engadin Snow-Deal booking](https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets) | `"Upper Engadin day and multi-day tickets cover Corvatsch/Furtschellas, Corviglia/Piz Nair, Diavolezza/Lagalb, Muottas Muragl, Zuoz, Pontresina/Languard, Samedan, La Punt, Maloja and S-chanf; only Corviglia/Piz Nair is currently modeled in Snowcast."` | The cited source supports the curated coverage fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `lift_pass_product_id` | [Engadin Snow-Deal booking](https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets) | `"engadin-st-moritz-day-multiday-ski-ticket"` | The cited source supports the curated identity scope availability fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `name` | [Engadin Snow-Deal booking](https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets) | `"Upper Engadin Snow-Deal day and multi-day ski ticket"` | The cited source supports the curated identity scope availability fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `terrain_domain_ids` | [Engadin Snow-Deal booking](https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets) | `[]` | The cited source supports the curated coverage fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `valid_ski_area_ids` | [Engadin Snow-Deal booking](https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets) | `["st-moritz-ski-area"]` | The cited source supports the curated coverage fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `validity_scope` | [Engadin Snow-Deal booking](https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets) | `"regional_network"` | The cited source supports the curated identity scope availability fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `rental_display_fact:st-moritz-ski-service-corvatsch-st-moritz-dorf` | `stay_base_id` | [St. Moritz official tourism](https://www.stmoritz.com/en/directory/shopping/sports/ski-service-corvatsch-st-moritz-dorf) | `"st-moritz-st-moritz"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `base_elevation_m` | [Engadin St. Moritz Mountains](https://www.mountains.ch/fileadmin/user_upload/Bilddatenbank_HP/Organisation/Dokumente/Panoramakarten/web_2025_Panoramakarte_Corviglia_Winter_504x420_Karte_vorne.pdf) | `1730` | The cited source supports the curated elevation season fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `official_trail_map.season_label` | [Engadin St. Moritz Mountains](https://www.mountains.ch/fileadmin/user_upload/Bilddatenbank_HP/Organisation/Dokumente/Panoramakarten/web_2025_Panoramakarte_Corviglia_Winter_504x420_Karte_vorne.pdf) | `"2025/26"` | The cited source supports the curated official documents fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `official_trail_map.url` | [Engadin St. Moritz Mountains](https://www.mountains.ch/fileadmin/user_upload/Bilddatenbank_HP/Organisation/Dokumente/Panoramakarten/web_2025_Panoramakarte_Corviglia_Winter_504x420_Karte_vorne.pdf) | `"https://www.mountains.ch/fileadmin/user_upload/Bilddatenbank_HP/Organisation/Dokumente/Panoramakarten/web_2025_Panoramakarte_Corviglia_Winter_504x420_Karte_vorne.pdf"` | The cited source supports the curated official documents fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `piste_km_by_difficulty.advanced` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `34.0` | The cited source supports the curated terrain metrics fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `piste_km_by_difficulty.beginner` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `42.0` | The cited source supports the curated terrain metrics fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `piste_km_by_difficulty.intermediate` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `79.0` | The cited source supports the curated terrain metrics fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `season_start_month` | [Engadin St. Moritz Mountains](https://www.mountains.ch/fileadmin/user_upload/Bilddatenbank_HP/Organisation/Dokumente/Panoramakarten/web_2025_Panoramakarte_Corviglia_Winter_504x420_Karte_vorne.pdf) | `11` | The cited source supports the curated elevation season fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `ski_day_apres_profile.availability` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/food-drink/star-bar-marguns/) | `"available"` | The cited source supports the curated ski day apres fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `ski_day_apres_profile.intensity` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/food-drink/star-bar-marguns/) | `"lively"` | The cited source supports the curated ski day apres fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `snow_park.availability` | [Engadin St. Moritz Mountains](https://www.mountains.ch/de/winter/skifahren/crowland/) | `"available"` | The cited source supports the curated snow park fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `snow_park.park_count` | [Engadin St. Moritz Mountains](https://www.mountains.ch/de/winter/skifahren/crowland/) | `1` | The cited source supports the curated snow park fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `snowmaking.availability` | [Engadin official tourism](https://www.engadin.ch/en/stories/two-lakes-in-the-name-of-sustainability) | `"available"` | The cited source supports the curated snowmaking fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `supported_skill_levels` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/winter/skiing/pisten/) | `["beginner", "intermediate", "advanced"]` | The cited source supports the curated skill fit fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `total_lift_count` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `24` | The cited source supports the curated terrain metrics fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area:st-moritz-ski-area` | `total_piste_km` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `155.0` | The cited source supports the curated terrain metrics fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `access_mode` | [Engadin official tourism](https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina) | `"mixed"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `distance_m` | [Engadin official tourism](https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina) | `464` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `is_direct` | [Engadin official tourism](https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina) | `false` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `lift_distance` | [Engadin official tourism](https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina) | `"near"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `nearest_lift_name` | [Engadin official tourism](https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina) | `"Celerina - Marguns gondola"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `regional_data_ids` | [Engadin official tourism](https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina) | `{"nearest_lift_osm_node_id": "665939771"}` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `ski_area_access_id` | [Engadin official tourism](https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina) | `"celerina-celerina--st-moritz-ski-area"` | The cited source supports the curated relationship fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `ski_area_id` | [Engadin official tourism](https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina) | `"st-moritz-ski-area"` | The cited source supports the curated relationship fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `source_urls` | [Engadin official tourism](https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina) | `["https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina", "https://www.openstreetmap.org/node/665939771", "https://www.openstreetmap.org/relation/1684062"]` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:celerina-celerina--st-moritz-ski-area` | `stay_base_id` | [Engadin official tourism](https://www.engadin.ch/en/guide/holiday-resorts/celerina/ski-paradise-celerina) | `"celerina-celerina"` | The cited source supports the curated relationship fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `access_mode` | [OpenStreetMap](https://www.openstreetmap.org/node/309543453) | `"walk"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `distance_m` | [OpenStreetMap](https://www.openstreetmap.org/node/309543453) | `147` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `lift_distance` | [OpenStreetMap](https://www.openstreetmap.org/node/309543453) | `"near"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `nearest_lift_name` | [OpenStreetMap](https://www.openstreetmap.org/node/309543453) | `"St. Moritz Dorf - Chantarella funicular"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `regional_data_ids` | [OpenStreetMap](https://www.openstreetmap.org/node/309543453) | `{"nearest_lift_osm_node_id": "309543453"}` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz--st-moritz-ski-area` | `source_urls` | [OpenStreetMap](https://www.openstreetmap.org/node/309543453) | `["https://www.openstreetmap.org/node/309543453", "https://www.openstreetmap.org/relation/1684175", "https://www.stmoritz.com/en/directory/mountains/corviglia"]` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `access_mode` | [OpenStreetMap](https://www.openstreetmap.org/node/2192847631) | `"walk"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `distance_m` | [OpenStreetMap](https://www.openstreetmap.org/node/2192847631) | `671` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `is_direct` | [OpenStreetMap](https://www.openstreetmap.org/node/2192847631) | `false` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `lift_distance` | [OpenStreetMap](https://www.openstreetmap.org/node/2192847631) | `"medium"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `nearest_lift_name` | [OpenStreetMap](https://www.openstreetmap.org/node/2192847631) | `"St. Moritz Bad - Signal cable car"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `regional_data_ids` | [OpenStreetMap](https://www.openstreetmap.org/node/2192847631) | `{"nearest_lift_osm_node_id": "2192847631"}` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `ski_area_access_id` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"st-moritz-st-moritz-bad--st-moritz-ski-area"` | The cited source supports the curated relationship fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `ski_area_id` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"st-moritz-ski-area"` | The cited source supports the curated relationship fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `source_urls` | [OpenStreetMap](https://www.openstreetmap.org/node/2192847631) | `["https://www.mountains.ch/en/facilities/", "https://www.openstreetmap.org/node/2192847631", "https://www.openstreetmap.org/node/9935735584", "https://www.stmoritz.com/en/directory/mountains/corviglia"]` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-st-moritz-bad--st-moritz-ski-area` | `stay_base_id` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"st-moritz-st-moritz-bad"` | The cited source supports the curated relationship fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `access_mode` | [OpenStreetMap](https://www.openstreetmap.org/node/3445699153) | `"ski_in_ski_out"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `distance_m` | [OpenStreetMap](https://www.openstreetmap.org/node/3445699153) | `87` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `is_direct` | [OpenStreetMap](https://www.openstreetmap.org/node/3445699153) | `true` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `lift_distance` | [OpenStreetMap](https://www.openstreetmap.org/node/3445699153) | `"near"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `nearest_lift_name` | [OpenStreetMap](https://www.openstreetmap.org/node/3445699153) | `"Suvretta lift"` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `regional_data_ids` | [OpenStreetMap](https://www.openstreetmap.org/node/3445699153) | `{"nearest_lift_osm_node_id": "3445699153"}` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `ski_area_access_id` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"st-moritz-suvretta--st-moritz-ski-area"` | The cited source supports the curated relationship fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `ski_area_id` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"st-moritz-ski-area"` | The cited source supports the curated relationship fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `source_urls` | [OpenStreetMap](https://www.openstreetmap.org/node/3445699153) | `["https://www.mountains.ch/en/facilities/", "https://www.openstreetmap.org/node/3445699153", "https://www.openstreetmap.org/way/268146958", "https://www.stmoritz.com/en/directory/hotels/hotel-suvretta-house"]` | The cited source supports the curated access mode distance fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_area_access:st-moritz-suvretta--st-moritz-ski-area` | `stay_base_id` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"st-moritz-suvretta"` | The cited source supports the curated relationship fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_region:st-moritz` | `name` | [Engadin official tourism](https://www.engadin.ch/en/guide/engadin-holiday-resorts) | `"Engadin St. Moritz"` | The cited source supports the curated identity fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `ski_region:st-moritz` | `source_urls` | [Engadin official tourism](https://www.engadin.ch/en/guide/engadin-holiday-resorts) | `["https://www.engadin.ch/en/guide/engadin-holiday-resorts"]` | The cited source supports the curated membership context fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `base_character.development_style` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"traditional"` | The cited source supports the curated base character fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `base_character.local_pace` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"balanced"` | The cited source supports the curated base character fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `base_type` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"village"` | The cited source supports the curated base type fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `latitude` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684062) | `46.5122544` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `local_apres_profile.availability` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"available"` | The cited source supports the curated local apres fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `local_apres_profile.intensity` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"moderate"` | The cited source supports the curated local apres fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `longitude` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684062) | `9.8588858` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `name` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"Celerina/Schlarigna"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `regional_data_ids` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684062) | `{"osm_relation_id": "1684062"}` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `stay_base_id` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"celerina-celerina"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:celerina-celerina` | `stay_destination_id` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"celerina"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz` | `base_character.development_style` | [St. Moritz official tourism](https://www.stmoritz.com/en/about-st-moritz-tourismus-ag) | `"mixed"` | The cited source supports the curated base character fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz` | `base_character.local_pace` | [St. Moritz official tourism](https://www.stmoritz.com/en/about-st-moritz-tourismus-ag) | `"lively"` | The cited source supports the curated base character fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz` | `base_type` | [St. Moritz official tourism](https://api.stmoritz.com/fileadmin/user_upload/pdf/PDF_high_altitude_training_st.moritz_DE_A4_59_.pdf) | `"neighbourhood"` | The cited source supports the curated base type fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz` | `elevation_m` | [St. Moritz official tourism](https://api.stmoritz.com/fileadmin/user_upload/pdf/PDF_high_altitude_training_st.moritz_DE_A4_59_.pdf) | `1846` | The cited source supports the curated elevation fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz` | `latitude` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684175) | `46.4978958` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz` | `local_apres_profile.availability` | [St. Moritz official tourism](https://www.stmoritz.com/en/directory/bars-nightlife) | `"available"` | The cited source supports the curated local apres fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz` | `local_apres_profile.intensity` | [St. Moritz official tourism](https://www.stmoritz.com/en/directory/bars-nightlife) | `"lively"` | The cited source supports the curated local apres fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz` | `longitude` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684175) | `9.8392428` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz` | `name` | [St. Moritz official tourism](https://api.stmoritz.com/fileadmin/user_upload/pdf/PDF_high_altitude_training_st.moritz_DE_A4_59_.pdf) | `"St. Moritz Dorf"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz-bad` | `base_type` | [Engadin official tourism](https://www.engadin.ch/en/guide/activities/more-activities/guided-village-tour-of-st-moritz) | `"neighbourhood"` | The cited source supports the curated base type fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz-bad` | `elevation_m` | [Engadin St. Moritz Mountains](https://www.mountains.ch/fileadmin/user_upload/Bilddatenbank_HP/Organisation/Dokumente/Panoramakarten/web_2025_Panoramakarte_Corviglia_Winter_504x420_Karte_vorne.pdf) | `1772` | The cited source supports the curated elevation fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz-bad` | `latitude` | [OpenStreetMap](https://www.openstreetmap.org/node/9935735584) | `46.4893548` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz-bad` | `longitude` | [OpenStreetMap](https://www.openstreetmap.org/node/9935735584) | `9.8349515` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz-bad` | `name` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"St. Moritz Bad"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz-bad` | `regional_data_ids` | [OpenStreetMap](https://www.openstreetmap.org/node/9935735584) | `{"osm_node_id": "9935735584"}` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz-bad` | `stay_base_id` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"st-moritz-st-moritz-bad"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-st-moritz-bad` | `stay_destination_id` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"st-moritz"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-suvretta` | `base_character.development_style` | [St. Moritz official tourism](https://www.stmoritz.com/en/directory/hotels/hotel-suvretta-house) | `"traditional"` | The cited source supports the curated base character fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-suvretta` | `base_character.local_pace` | [St. Moritz official tourism](https://www.stmoritz.com/en/directory/hotels/hotel-suvretta-house) | `"quiet"` | The cited source supports the curated base character fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-suvretta` | `base_type` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"resort_sector"` | The cited source supports the curated base type fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-suvretta` | `elevation_m` | [St. Moritz official tourism](https://api.stmoritz.com/fileadmin/user_upload/pdf/PDF_high_altitude_training_st.moritz_DE_A4_59_.pdf) | `1900` | The cited source supports the curated elevation fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-suvretta` | `latitude` | [OpenStreetMap](https://www.openstreetmap.org/way/268146958) | `46.4848584` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-suvretta` | `longitude` | [OpenStreetMap](https://www.openstreetmap.org/way/268146958) | `9.8197765` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-suvretta` | `name` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"Suvretta"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-suvretta` | `regional_data_ids` | [OpenStreetMap](https://www.openstreetmap.org/way/268146958) | `{"osm_way_id": "268146958"}` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-suvretta` | `stay_base_id` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"st-moritz-suvretta"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_base:st-moritz-suvretta` | `stay_destination_id` | [Engadin St. Moritz Mountains](https://www.mountains.ch/en/facilities/) | `"st-moritz"` | The cited source supports the curated identity ownership fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:celerina` | `country` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"Switzerland"` | The cited source supports the curated identity location fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:celerina` | `latitude` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684062) | `46.5122544` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:celerina` | `longitude` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684062) | `9.8588858` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:celerina` | `name` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"Celerina/Schlarigna"` | The cited source supports the curated identity location fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:celerina` | `region` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"Engadin"` | The cited source supports the curated identity location fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:celerina` | `regional_data_ids` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684062) | `{"osm_relation_id": "1684062"}` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:celerina` | `stay_destination_id` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"celerina"` | The cited source supports the curated identity location fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:celerina` | `trip_market_region_id` | [Engadin official tourism](https://api.engadin.ch/fileadmin/user_upload/engadin/PDF_Ortspl%C3%A4ne/Ortsplan_Celerina.pdf) | `"st-moritz"` | The cited source supports the curated identity location fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:st-moritz` | `latitude` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684175) | `46.4978958` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:st-moritz` | `longitude` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684175) | `9.8392428` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:st-moritz` | `name` | [Engadin official tourism](https://www.engadin.ch/en/guide/engadin-holiday-resorts) | `"St. Moritz"` | The cited source supports the curated identity location fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `stay_destination:st-moritz` | `regional_data_ids` | [OpenStreetMap](https://www.openstreetmap.org/relation/1684175) | `{"osm_relation_id": "1684175"}` | The cited source supports the curated coordinates fact. | The source fact is normalized into the catalog's typed owner-level field. |
| `lift_pass_product:engadin-st-moritz-day-multiday-ski-ticket` | `external_validity_summary` | [Engadin Snow-Deal booking](https://booking.engadin.ch/en/ski-tickets/day-and-multi-day-ski-tickets) | `"The Entire Upper Engadin selection names the wider set of independently presented ski areas."` | The official booking flow establishes broad pass context but not one connected terrain owner. | The catalog summary enumerates the named areas while only linking the currently modeled Corviglia owner. |
| `ski_region:st-moritz` | `source_urls` | [Engadin holiday resorts](https://www.engadin.ch/en/guide/engadin-holiday-resorts) | `["https://www.engadin.ch/en/guide/engadin-holiday-resorts"]` | Official tourism presents the Upper Engadin settlements as distinct holiday resorts within one market. | The source is stored as the region membership reference and also supports deferred destination candidates. |
| `ski_area:st-moritz-ski-area` | `name` | [Corviglia official mountain page](https://www.stmoritz.com/en/directory/mountains/corviglia) | `"Provulèr is presented as a family sector at the edge of Corviglia."` | The official destination nests Provulèr within Corviglia rather than presenting an independent operating owner. | The retained ski-area name represents the parent operating owner; Provulèr is not split. |
| `stay_base:celerina-celerina` | `elevation_m` | [Celerina/Schlarigna municipality profile](https://www.gemeinde-celerina.ch/celerina) | `1730` | The municipality's facts section publishes Celerina/Schlarigna at 1,730 m above sea level. |  |
| `ski_area:st-moritz-ski-area` | `season_windows` | [Engadin winter operating times (German)](https://www.engadin.ch/de/guide/berge-bahnen/betriebszeiten-fahrplaene/betriebszeiten-bergbahnen-im-winter) | `[{"end_date": "2026-04-06", "season_label": "Winter 2025/26", "start_date": "2025-11-29", "status": "planned"}]` | The official Winter 2025/26 timetable gives 29 November 2025 to 6 April 2026 for the main Signal, Dorf/Chantarella and Celerina feeders; Piz Nair, Suvretta and Provulèr opened later and closed on 6 April. | The ski-area window starts with the first opening of the main feeder network and ends on the common closing date; later upper and secondary lift openings remain documented in the evidence summary. |

## Boundary Decisions

- `st-moritz`: `pass`
- `celerina`: `pass`

## Weather Request Geometry

- `st-moritz-ski-area`: material change

## Ranking Impact

Source-backed terrain, base-character and access facts become eligible for later product-policy use. Estimated lodging values and unresolved pass pricing remain explicitly non-source-backed.

## Verification

- `uv run python -m app.data.validate_catalog --trust-manifest-path app/data/resort_trust_manifest.json`
- `uv run python -m app.data.validate_catalog_curation typed docs/catalog-curation/2026-06-27-st-moritz-full-curation.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md`
- `uv run python -m app.data.validate_catalog_curation reconcile docs/catalog-curation/2026-06-27-st-moritz-full-curation.json --base-catalog-path /tmp/pr19-base-catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path /tmp/pr19-base-trust.json --current-trust-manifest-path app/data/resort_trust_manifest.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md`
- `uv run pytest tests/test_catalog_curation.py tests/test_catalog_curation_reconciliation.py tests/test_catalog_curation_backlog.py tests/test_catalog_models.py tests/test_catalog_trust.py -q`

## Caveats

- The regional Snow-Deal booking flow uses dynamic dated pricing; no representative fixed price samples are stored.
- The Corviglia weather coordinate is retained as an estimate; the verified base elevation changes request geometry from 1856 m to 1730 m.
- The stored exact season window is Winter 2025/26; no official 2026/27 window or reliable snowmaking coverage percentage was published at review time.
- Recurring night skiing, glacier terrain and marked freeride routes remain unresolved rather than inferred.
- The additional Upper Engadin ski areas and destinations listed in the scope assessment are deferred under the dedicated backlog section.
