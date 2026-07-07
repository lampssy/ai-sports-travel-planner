# Verbier Catalog Curation - complete local sector and defer 4 Vallées domain

Migrates PR #18 to the schema-version-2 curation contract and aligns every fact with its owner. The retained Verbier ski-area ID is clarified as the official 106 km, 33-lift Verbier sector spanning Verbier, La Tzoumaz-Savoleyres, and Bruson. La Tzoumaz and Bruson are added as separate stay destinations with representative village bases and source-backed access edges. The complete 4 Vallées map is removed from the narrower ski area, and Nendaz, Veysonnaz, Thyon, their terrain owners, and the connected 4 Vallées domain are explicitly deferred. The 4 Vallées pass now stores correct fixed adult 1-, 3-, and 6-day 2025/26 examples; its commercial tariff source is classified as reviewed editorial rather than first-party official evidence.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:verbier-4-vallees-pass` | `full` | all canonical fields |
| `rental_display_fact:verbier-mountain-air` | `full` | all canonical fields |
| `ski_area:verbier-ski-area` | `full` | all canonical fields |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `full` | all canonical fields |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `full` | all canonical fields |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `full` | all canonical fields |
| `ski_region:verbier` | `full` | all canonical fields |
| `stay_base:bruson-bruson` | `full` | all canonical fields |
| `stay_base:la-tzoumaz-la-tzoumaz` | `full` | all canonical fields |
| `stay_base:verbier-verbier` | `full` | all canonical fields |
| `stay_destination:bruson` | `full` | all canonical fields |
| `stay_destination:la-tzoumaz` | `full` | all canonical fields |
| `stay_destination:verbier` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `full` | all canonical fields |
| `trust_manifest:rental_display_facts:verbier-mountain-air` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:bruson-bruson--verbier-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:verbier-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_regions:verbier` | `full` | all canonical fields |
| `trust_manifest:stay_bases:bruson-bruson` | `full` | all canonical fields |
| `trust_manifest:stay_bases:la-tzoumaz-la-tzoumaz` | `full` | all canonical fields |
| `trust_manifest:stay_bases:verbier-verbier` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:bruson` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:la-tzoumaz` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:verbier` | `full` | all canonical fields |

## Entity Scope Assessments

| Candidate | Kind | Disposition | Signals | Catalog Targets | Evidence | Backlog | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `verbier-destination` (Verbier) | `stay_destination` | `represented` | `independent_stay_market`, `direct_access_relationship` | `stay_destination:verbier` | `boundary-verbier` |  | Verbier remains the international premium accommodation destination. |
| `verbier-base` (Verbier village base) | `stay_base` | `represented` | `independent_stay_market`, `direct_access_relationship` | `stay_base:verbier-verbier` | `boundary-verbier` |  | The retained village base owns Verbier-local lodging, character and access facts. |
| `verbier-sector-owner` (Verbier sector) | `ski_area` | `represented` | `official_independent_identity`, `child_scoped_terrain_metrics`, `independent_status_or_schedule` | `ski_area:verbier-ski-area` | `scope-verbier-sector` |  | The retained ski-area ID owns the operator's jointly published Verbier, La Tzoumaz-Savoleyres and Bruson sector. |
| `verbier-medran-access` (Verbier to Médran access) | `ski_area_access` | `represented` | `direct_access_relationship`, `distinct_access` | `ski_area_access:verbier-verbier--verbier-ski-area` | `boundary-verbier` |  | The retained edge records the representative village walk to Médran. |
| `verbier-4-vallees-pass` (4 Vallées ski pass) | `lift_pass_product` | `represented` | `official_product_identity` | `lift_pass_product:verbier-4-vallees-pass` | `scope-four-vallees` |  | The pass remains represented with explicit modeled Verbier-sector coverage and wider external context pending the connected-domain extension. |
| `la-tzoumaz` (La Tzoumaz) | `stay_destination` | `add_entity` | `independent_stay_market`, `direct_access_relationship` | `stay_destination:la-tzoumaz` | `boundary-la-tzoumaz` |  | La Tzoumaz is a named bookable market with its own access and materially different recommendation context. |
| `la-tzoumaz-base` (La Tzoumaz village base) | `stay_base` | `add_entity` | `independent_stay_market`, `direct_access_relationship` | `stay_base:la-tzoumaz-la-tzoumaz` | `boundary-la-tzoumaz` |  | The named village is the representative base for La Tzoumaz. |
| `la-tzoumaz-access` (La Tzoumaz to Verbier-sector access) | `ski_area_access` | `add_entity` | `direct_access_relationship`, `distinct_access` | `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `boundary-la-tzoumaz` |  | A source-backed edge connects La Tzoumaz to the shared Verbier sector. |
| `bruson` (Bruson) | `stay_destination` | `add_entity` | `independent_stay_market`, `direct_access_relationship` | `stay_destination:bruson` | `boundary-bruson` |  | Bruson is a named bookable market with its own access and materially different recommendation context. |
| `bruson-base` (Bruson village base) | `stay_base` | `add_entity` | `independent_stay_market`, `direct_access_relationship` | `stay_base:bruson-bruson` | `boundary-bruson` |  | The named village is the representative base for Bruson. |
| `bruson-access` (Bruson to Verbier-sector access) | `ski_area_access` | `add_entity` | `direct_access_relationship`, `distinct_access` | `ski_area_access:bruson-bruson--verbier-ski-area` | `boundary-bruson` |  | A source-backed edge connects Bruson to the shared Verbier sector. |
| `verbier-terrain-component` (Verbier terrain component) | `ski_area` | `not_separate` | `official_map_sector`, `ski_connected_terrain` | `ski_area:verbier-ski-area` | `scope-verbier-sector` |  | The component has distinct access and sector treatment, but the operator publishes the primary 106 km / 33-lift inventory jointly rather than as an independent weather owner. |
| `la-tzoumaz-savoleyres-terrain-component` (La Tzoumaz-Savoleyres terrain component) | `ski_area` | `not_separate` | `official_map_sector`, `ski_connected_terrain` | `ski_area:verbier-ski-area` | `scope-verbier-sector` |  | The component has distinct access and sector treatment, but the operator publishes the primary 106 km / 33-lift inventory jointly rather than as an independent weather owner. |
| `bruson-terrain-component` (Bruson terrain component) | `ski_area` | `not_separate` | `official_map_sector`, `ski_connected_terrain` | `ski_area:verbier-ski-area` | `scope-verbier-sector` |  | The component has distinct access and sector treatment, but the operator publishes the primary 106 km / 33-lift inventory jointly rather than as an independent weather owner. |
| `nendaz` (Nendaz destination) | `stay_destination` | `deferred` | `independent_stay_market`, `direct_access_relationship` |  | `scope-four-vallees` | `docs/product-backlog.md#verbier-4-vallees-extension` | Nendaz requires a complete destination boundary across Haute-Nendaz and Siviez. |
| `nendaz-haute-nendaz` (Haute-Nendaz stay base) | `stay_base` | `deferred` | `independent_stay_market`, `distinct_access` |  | `scope-four-vallees` | `docs/product-backlog.md#verbier-4-vallees-extension` | Haute-Nendaz should be curated with the complete Nendaz destination boundary. |
| `nendaz-siviez` (Siviez stay base) | `stay_base` | `deferred` | `independent_stay_market`, `distinct_access` |  | `scope-four-vallees` | `docs/product-backlog.md#verbier-4-vallees-extension` | Siviez has a materially different accommodation and connection context from Haute-Nendaz. |
| `nendaz-haute-nendaz--nendaz-veysonnaz-ski-area` (Haute-Nendaz ski-area access) | `ski_area_access` | `deferred` | `direct_access_relationship`, `distinct_access` |  | `scope-four-vallees` | `docs/product-backlog.md#verbier-4-vallees-extension` | The destination requires an explicit Haute-Nendaz gondola/access edge. |
| `nendaz-siviez--nendaz-veysonnaz-ski-area` (Siviez ski-area access) | `ski_area_access` | `deferred` | `direct_access_relationship`, `distinct_access` |  | `scope-four-vallees` | `docs/product-backlog.md#verbier-4-vallees-extension` | The destination requires a separate Siviez connection edge. |
| `veysonnaz` (Veysonnaz destination) | `stay_destination` | `deferred` | `independent_stay_market`, `direct_access_relationship` |  | `scope-four-vallees` | `docs/product-backlog.md#verbier-4-vallees-extension` | Veysonnaz is a separate connected accommodation market requiring full curation. |
| `veysonnaz-veysonnaz` (Veysonnaz village base) | `stay_base` | `deferred` | `independent_stay_market`, `direct_access_relationship` |  | `scope-four-vallees` | `docs/product-backlog.md#verbier-4-vallees-extension` | The village and direct gondola access should be added with the destination. |
| `veysonnaz-veysonnaz--nendaz-veysonnaz-ski-area` (Veysonnaz gondola access) | `ski_area_access` | `deferred` | `direct_access_relationship`, `distinct_access` |  | `scope-four-vallees` | `docs/product-backlog.md#verbier-4-vallees-extension` | The direct access edge depends on the deferred destination and base identities. |
| `thyon` (Thyon destination) | `stay_destination` | `deferred` | `independent_stay_market`, `distinct_access` |  | `scope-thyon-owner` | `docs/product-backlog.md#verbier-4-vallees-extension` | Thyon requires a boundary review across Thyon 2000, Les Collons and Les Masses. |
| `thyon-thyon-2000` (Thyon 2000 stay base) | `stay_base` | `deferred` | `independent_stay_market`, `distinct_access` |  | `scope-thyon-owner` | `docs/product-backlog.md#verbier-4-vallees-extension` | Thyon 2000 should be assessed with the complete destination boundary. |
| `thyon-les-collons` (Les Collons stay base) | `stay_base` | `deferred` | `independent_stay_market`, `distinct_access` |  | `scope-thyon-owner` | `docs/product-backlog.md#verbier-4-vallees-extension` | Les Collons should be assessed as a separate base within the Thyon market. |
| `thyon-les-masses` (Les Masses stay base) | `stay_base` | `deferred` | `independent_stay_market`, `distinct_access` |  | `scope-thyon-owner` | `docs/product-backlog.md#verbier-4-vallees-extension` | Les Masses should be assessed as a separate base within the Thyon market. |
| `thyon-thyon-2000--thyon-ski-area` (Thyon 2000 ski-area access) | `ski_area_access` | `deferred` | `direct_access_relationship`, `distinct_access` |  | `scope-thyon-owner` | `docs/product-backlog.md#verbier-4-vallees-extension` | Thyon 2000 requires its own local lift-access edge. |
| `thyon-les-collons--thyon-ski-area` (Les Collons ski-area access) | `ski_area_access` | `deferred` | `direct_access_relationship`, `distinct_access` |  | `scope-thyon-owner` | `docs/product-backlog.md#verbier-4-vallees-extension` | Les Collons requires its own local lift or ski-bus access edge. |
| `thyon-les-masses--thyon-ski-area` (Les Masses ski-area access) | `ski_area_access` | `deferred` | `direct_access_relationship`, `distinct_access` |  | `scope-thyon-owner` | `docs/product-backlog.md#verbier-4-vallees-extension` | Les Masses requires its own local lift or ski-bus access edge. |
| `nendaz-veysonnaz-ski-area` (Nendaz-Veysonnaz ski-area owner) | `ski_area` | `deferred` | `separate_operator`, `independent_status_or_schedule` |  | `scope-nvrm-owner` | `docs/product-backlog.md#verbier-4-vallees-extension` | NVRM and its Mont-Fort boundary require a dedicated weather-owner review. |
| `thyon-ski-area` (Thyon ski-area owner) | `ski_area` | `deferred` | `separate_operator`, `independent_status_or_schedule`, `child_scoped_terrain_metrics` |  | `scope-thyon-owner` | `docs/product-backlog.md#verbier-4-vallees-extension` | Thyon publishes independent local lifts and operation, requiring a separate owner. |
| `4-vallees` (4 Vallées connected terrain domain) | `terrain_domain` | `deferred` | `ski_connected_terrain`, `official_product_identity` |  | `scope-four-vallees` | `docs/product-backlog.md#verbier-4-vallees-extension` | The domain can be created only after all independent member ski-area owners exist. |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:verbier-4-vallees-pass` | `available_from_stay_destination_ids` | `null` | `["bruson", "la-tzoumaz", "verbier"]` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `default_for_stay_destination_ids` | `null` | `["verbier"]` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `external_validity_summary` | `null` | `"Covers the modeled Verbier sector (Verbier, La Tzoumaz-Savoleyres and Bruson) plus the wider 4 Vallées network of Nendaz, Veysonnaz and Thyon when those links are operating."` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `lift_pass_product_id` | `null` | `"verbier-4-vallees-pass"` | `verified` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `name` | `null` | `"4 Vallées ski pass"` | `verified` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `prices` | `null` | `[{"amount": 94.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 4 Vallées adult cash-desk tariff", "source_url": "https://www.verbier.com/ski-passes"}, {"amount": 247.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 4 Vallées adult cash-desk tariff", "source_url": "https://www.verbier.com/ski-passes"}, {"amount": 409.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 4 Vallées adult cash-desk tariff", "source_url": "https://www.verbier.com/ski-passes"}]` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `valid_ski_area_ids` | `null` | `["verbier-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:verbier-4-vallees-pass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `ski_area:verbier-ski-area` | `marked_freeride_routes.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:verbier-ski-area` | `marked_freeride_routes.route_count` | `null` | `6` | `verified_with_adjustment` | no |
| `ski_area:verbier-ski-area` | `name` | `"Verbier"` | `"Verbier sector"` | `verified` | no |
| `ski_area:verbier-ski-area` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `ski_area:verbier-ski-area` | `ski_day_apres_profile.availability` | `"unknown"` | `"available"` | `verified_with_adjustment` | no |
| `ski_area:verbier-ski-area` | `ski_day_apres_profile.intensity` | `null` | `"destination_defining"` | `verified_with_adjustment` | no |
| `ski_area:verbier-ski-area` | `snow_park.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:verbier-ski-area` | `snow_park.park_count` | `null` | `1` | `verified` | no |
| `ski_area:verbier-ski-area` | `snowmaking.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:verbier-ski-area` | `supported_skill_levels` | `["intermediate", "advanced"]` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:verbier-ski-area` | `total_lift_count` | `null` | `33` | `verified` | yes |
| `ski_area:verbier-ski-area` | `total_piste_km` | `null` | `106.0` | `verified` | yes |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `access_mode` | `null` | `"ski_bus"` | `verified_with_adjustment` | yes |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `is_direct` | `null` | `false` | `verified_with_adjustment` | yes |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `lift_distance` | `null` | `"far"` | `verified_with_adjustment` | yes |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `nearest_lift_name` | `null` | `"Mayens de Bruson lifts"` | `verified` | no |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `regional_data_ids` | `null` | `{"stay_base_osm_node_id": "240097683", "valbord_bus_stop_osm_node_id": "300965457"}` | `verified_with_adjustment` | no |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `ski_area_access_id` | `null` | `"bruson-bruson--verbier-ski-area"` | `verified` | no |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `ski_area_id` | `null` | `"verbier-ski-area"` | `verified` | no |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `source_urls` | `null` | `["https://www.openstreetmap.org/node/240097683", "https://www.openstreetmap.org/node/300965457", "https://www.verbier.ch/en/destination/bruson/"]` | `verified_with_adjustment` | no |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `stay_base_id` | `null` | `"bruson-bruson"` | `verified` | no |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `distance_m` | `null` | `140` | `verified_with_adjustment` | yes |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `nearest_lift_name` | `null` | `"La Tzoumaz-Savoleyres gondola"` | `verified` | no |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "316315926", "stay_base_osm_node_id": "316314676"}` | `verified_with_adjustment` | no |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `ski_area_access_id` | `null` | `"la-tzoumaz-la-tzoumaz--verbier-ski-area"` | `verified` | no |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `ski_area_id` | `null` | `"verbier-ski-area"` | `verified` | no |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `source_urls` | `null` | `["https://verbier4vallees.ch/en/experiences-in-verbier/accommodation", "https://www.openstreetmap.org/node/316314676", "https://www.openstreetmap.org/node/316315926"]` | `verified_with_adjustment` | no |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `stay_base_id` | `null` | `"la-tzoumaz-la-tzoumaz"` | `verified` | no |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `distance_m` | `null` | `490` | `verified_with_adjustment` | yes |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `nearest_lift_name` | `null` | `"Medran / Place Blanche"` | `verified` | no |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `regional_data_ids` | `{}` | `{"nearest_lift_osm_node_id": "3415318439", "stay_base_osm_node_id": "310532759"}` | `verified_with_adjustment` | no |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `source_urls` | `["https://www.bergfex.com/verbier/"]` | `["https://www.openstreetmap.org/node/310532759", "https://www.openstreetmap.org/node/3415318439", "https://verbier4vallees.ch/en/useful-information/points-of-sale/sales-desks-and-infopoint_infrastructure_1230"]` | `verified_with_adjustment` | no |
| `stay_base:bruson-bruson` | `base_character.development_style` | `null` | `"traditional"` | `verified_with_adjustment` | no |
| `stay_base:bruson-bruson` | `base_character.local_pace` | `null` | `"quiet"` | `verified_with_adjustment` | no |
| `stay_base:bruson-bruson` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:bruson-bruson` | `elevation_m` | `null` | `1080` | `verified` | no |
| `stay_base:bruson-bruson` | `latitude` | `null` | `46.0662119` | `verified_with_adjustment` | no |
| `stay_base:bruson-bruson` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:bruson-bruson` | `longitude` | `null` | `7.2186328` | `verified_with_adjustment` | no |
| `stay_base:bruson-bruson` | `name` | `null` | `"Bruson"` | `verified` | no |
| `stay_base:bruson-bruson` | `price_max` | `null` | `230.0` | `estimated` | yes |
| `stay_base:bruson-bruson` | `price_min` | `null` | `150.0` | `estimated` | yes |
| `stay_base:bruson-bruson` | `price_range` | `null` | `"EUR 150-230"` | `estimated` | yes |
| `stay_base:bruson-bruson` | `quality` | `null` | `"standard"` | `estimated` | yes |
| `stay_base:bruson-bruson` | `regional_data_ids` | `null` | `{"osm_node_id": "240097683"}` | `verified_with_adjustment` | no |
| `stay_base:bruson-bruson` | `stay_base_id` | `null` | `"bruson-bruson"` | `verified` | no |
| `stay_base:bruson-bruson` | `stay_destination_id` | `null` | `"bruson"` | `verified_with_adjustment` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `base_character.development_style` | `null` | `"mixed"` | `verified_with_adjustment` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `base_character.local_pace` | `null` | `"quiet"` | `verified_with_adjustment` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `elevation_m` | `null` | `1500` | `verified` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `latitude` | `null` | `46.1444445` | `verified_with_adjustment` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `longitude` | `null` | `7.2348916` | `verified_with_adjustment` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `name` | `null` | `"La Tzoumaz"` | `verified` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `price_max` | `null` | `260.0` | `estimated` | yes |
| `stay_base:la-tzoumaz-la-tzoumaz` | `price_min` | `null` | `170.0` | `estimated` | yes |
| `stay_base:la-tzoumaz-la-tzoumaz` | `price_range` | `null` | `"EUR 170-260"` | `estimated` | yes |
| `stay_base:la-tzoumaz-la-tzoumaz` | `quality` | `null` | `"standard"` | `estimated` | yes |
| `stay_base:la-tzoumaz-la-tzoumaz` | `regional_data_ids` | `null` | `{"osm_node_id": "316314676"}` | `verified_with_adjustment` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `stay_base_id` | `null` | `"la-tzoumaz-la-tzoumaz"` | `verified` | no |
| `stay_base:la-tzoumaz-la-tzoumaz` | `stay_destination_id` | `null` | `"la-tzoumaz"` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `base_character.development_style` | `"unknown"` | `"mixed"` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `base_character.local_pace` | `"unknown"` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:verbier-verbier` | `elevation_m` | `null` | `1500` | `verified` | no |
| `stay_base:verbier-verbier` | `latitude` | `null` | `46.0961` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `local_apres_profile.availability` | `"unknown"` | `"available"` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `local_apres_profile.intensity` | `null` | `"destination_defining"` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `longitude` | `null` | `7.2287` | `verified_with_adjustment` | no |
| `stay_base:verbier-verbier` | `regional_data_ids` | `{}` | `{"osm_node_id": "310532759", "rental_osm_node_id": "1038335696"}` | `verified_with_adjustment` | no |
| `stay_destination:bruson` | `country` | `null` | `"Switzerland"` | `verified` | no |
| `stay_destination:bruson` | `latitude` | `null` | `46.0662119` | `verified_with_adjustment` | yes |
| `stay_destination:bruson` | `longitude` | `null` | `7.2186328` | `verified_with_adjustment` | yes |
| `stay_destination:bruson` | `name` | `null` | `"Bruson"` | `verified` | no |
| `stay_destination:bruson` | `price_level` | `null` | `"medium"` | `estimated` | yes |
| `stay_destination:bruson` | `region` | `null` | `"Valais"` | `verified` | no |
| `stay_destination:bruson` | `regional_data_ids` | `null` | `{"osm_node_id": "240097683"}` | `verified_with_adjustment` | no |
| `stay_destination:bruson` | `stay_destination_id` | `null` | `"bruson"` | `verified` | no |
| `stay_destination:bruson` | `trip_market_region_id` | `null` | `"verbier"` | `verified_with_adjustment` | no |
| `stay_destination:la-tzoumaz` | `country` | `null` | `"Switzerland"` | `verified` | no |
| `stay_destination:la-tzoumaz` | `latitude` | `null` | `46.1444445` | `verified_with_adjustment` | yes |
| `stay_destination:la-tzoumaz` | `longitude` | `null` | `7.2348916` | `verified_with_adjustment` | yes |
| `stay_destination:la-tzoumaz` | `name` | `null` | `"La Tzoumaz"` | `verified` | no |
| `stay_destination:la-tzoumaz` | `price_level` | `null` | `"medium"` | `estimated` | yes |
| `stay_destination:la-tzoumaz` | `region` | `null` | `"Valais"` | `verified` | no |
| `stay_destination:la-tzoumaz` | `regional_data_ids` | `null` | `{"osm_node_id": "316314676"}` | `verified_with_adjustment` | no |
| `stay_destination:la-tzoumaz` | `stay_destination_id` | `null` | `"la-tzoumaz"` | `verified` | no |
| `stay_destination:la-tzoumaz` | `trip_market_region_id` | `null` | `"verbier"` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `display_name` | `null` | `"4 Vallées ski pass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `field_source_refs` | `null` | `{"coverage": ["https://verbier4vallees.ch/en/ski-resort", "https://verbier4vallees.ch/en/ski-resort/4-vallees"], "identity_scope_availability": ["https://verbier4vallees.ch/en/ski-resort/4-vallees", "https://verbier4vallees.ch/en/useful-information/prices-winter"], "pass_accessible_terrain": [], "prices": ["https://www.verbier.com/ski-passes"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:verbier-4-vallees-pass` | `notes` | `null` | `["Official operator sources establish the 4 Vallées product identity, availability, and network scope; the modeled coverage currently resolves only the Verbier sector.", "The static 2025/26 adult 1-, 3-, and 6-day cash-desk examples come from the reviewed commercial Verbier.com tariff table, not from a first-party operator tariff artifact.", "Nendaz, Veysonnaz, Thyon, and the connected 4 Vallées terrain domain remain explicit catalog-curation backlog work."]` | `estimated` | no |
| `trust_manifest:ski_area_access:bruson-bruson--verbier-ski-area` | `display_name` | `null` | `"Bruson -> Verbier sector"` | `estimated` | no |
| `trust_manifest:ski_area_access:bruson-bruson--verbier-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.openstreetmap.org/node/240097683", "https://www.openstreetmap.org/node/300965457", "https://www.verbier.ch/en/destination/bruson/"], "relationship": ["https://www.openstreetmap.org/node/240097683", "https://www.openstreetmap.org/node/300965457", "https://www.verbier.ch/en/destination/bruson/"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:bruson-bruson--verbier-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:bruson-bruson--verbier-ski-area` | `notes` | `null` | `["Official tourism documents a bus from Le Châble to Bruson village and a required onward shuttle from Valbord to the Mayens de Bruson lift base.", "Snowcast records ski-bus access as far and indirect because the village stay base does not itself sit at the Mayens lift station; no unsupported end-to-end duration is asserted."]` | `estimated` | no |
| `trust_manifest:ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `display_name` | `null` | `"La Tzoumaz -> Verbier sector"` | `estimated` | no |
| `trust_manifest:ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://verbier4vallees.ch/en/experiences-in-verbier/accommodation", "https://www.openstreetmap.org/node/316314676", "https://www.openstreetmap.org/node/316315926"], "relationship": ["https://verbier4vallees.ch/en/experiences-in-verbier/accommodation", "https://www.openstreetmap.org/node/316314676", "https://www.openstreetmap.org/node/316315926"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `notes` | `null` | `["The official accommodation page places T-Resort at the foot of the slopes opposite the La Tzoumaz cable-car station.", "The 140 m distance is a rounded Haversine calculation from the OSM La Tzoumaz village node to the Savoleyres gondola station node."]` | `estimated` | no |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `display_name` | `"Verbier -> Verbier"` | `"Verbier -> Verbier sector"` | `estimated` | no |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/verbier/"], "relationship": ["https://www.bergfex.com/verbier/"]}` | `{"access_mode_distance": ["https://verbier4vallees.ch/en/useful-information/points-of-sale/sales-desks-and-infopoint_infrastructure_1230", "https://www.openstreetmap.org/node/310532759", "https://www.openstreetmap.org/node/3415318439"], "relationship": ["https://verbier4vallees.ch/en/useful-information/points-of-sale/sales-desks-and-infopoint_infrastructure_1230", "https://www.openstreetmap.org/node/310532759", "https://www.openstreetmap.org/node/3415318439"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Provider-backed relationship remains estimated; no exact distance or duration is asserted."]` | `["The official operator identifies Médran as the Verbier-sector ski-day departure point.", "The 490 m distance is a rounded Haversine calculation from the OSM Verbier village node to the Médran gondola-station node."]` | `estimated` | no |
| `trust_manifest:ski_areas:verbier-ski-area` | `display_name` | `"Verbier"` | `"Verbier sector"` | `estimated` | no |
| `trust_manifest:ski_areas:verbier-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://verbier4vallees.ch/en/ski-resort", "https://verbier4vallees.ch/en/ski-resort/4-vallees"], "glacier_terrain": [], "identity_coordinates": ["https://verbier4vallees.ch/en/ski-resort", "https://www.openstreetmap.org/node/310532759"], "marked_freeride_routes": ["https://verbier4vallees.ch/en/experiences-in-verbier/freeriding"], "night_skiing": [], "official_documents": [], "ski_day_apres": ["https://verbier4vallees.ch/en/ski-resort/verbier"], "skill_fit": ["https://verbier4vallees.ch/en/ski-resort/verbier"], "snow_park": ["https://verbier4vallees.ch/en/experiences-in-verbier/fun-zones"], "snowmaking": ["https://verbier4vallees.ch/en/about-us"], "terrain_metrics": ["https://verbier4vallees.ch/en/ski-resort"]}` | `estimated` | no |
| `trust_manifest:ski_areas:verbier-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "needs_source", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "verified_with_adjustment", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "verified_with_adjustment", "skill_fit": "verified_with_adjustment", "snow_park": "verified", "snowmaking": "verified", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:verbier-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["The official operator defines the Verbier sector as Verbier, La Tzoumaz-Savoleyres, and Bruson, jointly publishing 106 km of runs and 33 lifts.", "The marked-freeride count is scoped to the six itineraries explicitly assigned to those three sector components; the separate wider-4Vallées Gentianes-Tortin itinerary is excluded.", "The official PDF covers the complete 4 Vallées, so it is not stored as a local Verbier-sector map; it is deferred to the future connected terrain domain."]` | `estimated` | no |
| `trust_manifest:ski_regions:verbier` | `field_source_refs` | `{"identity": [], "membership_context": []}` | `{"identity": ["https://www.verbier.ch/en/destination/verbier/"], "membership_context": ["https://www.verbier.ch/en/destination/bruson/", "https://www.verbier.ch/en/destination/la-tzoumaz/", "https://www.verbier.ch/en/destination/verbier/"]}` | `estimated` | no |
| `trust_manifest:ski_regions:verbier` | `field_statuses` | `{"identity": "needs_source", "membership_context": "estimated"}` | `{"identity": "verified", "membership_context": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_regions:verbier` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Trip-market membership is retained as reviewed migration context and remains estimated.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["The Verbier trip market groups three distinct official accommodation destinations that share the jointly published Verbier ski sector: Verbier, La Tzoumaz, and Bruson.", "Nendaz, Veysonnaz, and Thyon remain independent future trip markets under a deferred 4 Vallees regional-network parent."]` | `estimated` | no |
| `trust_manifest:stay_bases:bruson-bruson` | `display_name` | `null` | `"Bruson"` | `estimated` | no |
| `trust_manifest:stay_bases:bruson-bruson` | `field_source_refs` | `null` | `{"base_character": ["https://www.verbier.ch/en/destination/bruson/"], "base_type": ["https://www.openstreetmap.org/node/240097683", "https://www.verbier.ch/en/destination/bruson/"], "coordinates": ["https://www.openstreetmap.org/node/240097683"], "elevation": ["https://www.verbier.ch/app/uploads/ot-verbier/2024/11/Verbier_PocketGuide_Hivers_241024-10-bd.pdf"], "identity_ownership": ["https://www.openstreetmap.org/node/240097683", "https://www.verbier.ch/en/destination/bruson/"], "local_apres": [], "lodging_price_quality": ["https://www.verbier.ch/en/destination/bruson/"]}` | `estimated` | no |
| `trust_manifest:stay_bases:bruson-bruson` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified", "coordinates": "verified", "elevation": "verified_with_adjustment", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:bruson-bruson` | `notes` | `null` | `["Official tourism describes Bruson as a preserved Alpine village where agriculture and mountain traditions remain active, with a calm and intimate pace.", "The official winter pocket guide labels Bruson village at 1,080 m.", "Lodging price and quality remain product-curated estimates pending a reviewed accommodation sampling policy; a recurring local apres profile was not established."]` | `estimated` | no |
| `trust_manifest:stay_bases:la-tzoumaz-la-tzoumaz` | `display_name` | `null` | `"La Tzoumaz"` | `estimated` | no |
| `trust_manifest:stay_bases:la-tzoumaz-la-tzoumaz` | `field_source_refs` | `null` | `{"base_character": ["https://verbier4vallees.ch/en/experiences-in-verbier/accommodation", "https://www.verbier.ch/en/destination/la-tzoumaz/"], "base_type": ["https://www.openstreetmap.org/node/316314676", "https://www.verbier.ch/en/destination/la-tzoumaz/"], "coordinates": ["https://www.openstreetmap.org/node/316314676"], "elevation": ["https://verbier4vallees.ch/en/experiences-in-verbier/accommodation"], "identity_ownership": ["https://www.openstreetmap.org/node/316314676", "https://www.verbier.ch/en/destination/la-tzoumaz/"], "local_apres": [], "lodging_price_quality": ["https://www.verbier.ch/en/destination/la-tzoumaz/"]}` | `estimated` | no |
| `trust_manifest:stay_bases:la-tzoumaz-la-tzoumaz` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified", "coordinates": "verified", "elevation": "verified", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:la-tzoumaz-la-tzoumaz` | `notes` | `null` | `["Official tourism presents La Tzoumaz as a family village whose identity emphasizes rest and nature, while the slopeside T-Resort adds modern resort accommodation; Snowcast normalizes that combination to mixed development and a quiet pace.", "The official operator places the village and its slopeside accommodation at 1,500 m.", "Lodging price and quality remain product-curated estimates pending a reviewed accommodation sampling policy; a recurring local apres profile was not established."]` | `estimated` | no |
| `trust_manifest:stay_bases:verbier-verbier` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `{"base_character": ["https://www.verbier.ch/en/", "https://www.verbier.ch/en/destination/verbier/"], "base_type": ["https://www.openstreetmap.org/node/310532759", "https://www.verbier.ch/en/destination/verbier/"], "coordinates": ["https://verbier4vallees.ch/en/ski-resort", "https://www.openstreetmap.org/node/310532759"], "elevation": ["https://www.verbier.ch/en/"], "identity_ownership": ["https://verbier4vallees.ch/en/ski-resort", "https://www.openstreetmap.org/node/310532759"], "local_apres": ["https://www.verbier.ch/en/", "https://www.verbier.ch/en/destination/verbier/"], "lodging_price_quality": ["https://verbier4vallees.ch/en/ski-resort", "https://www.openstreetmap.org/node/310532759"]}` | `estimated` | no |
| `trust_manifest:stay_bases:verbier-verbier` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `{"base_character": "verified_with_adjustment", "base_type": "verified", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:verbier-verbier` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Official destination and open-geodata sources establish Verbier as the village accommodation base at 1,500 m.", "Character and apres values normalize the destination's explicit combination of Alpine-village charm, cosmopolitan resort identity, and vibrant nightlife.", "Lodging price and quality remain product-curated estimates pending a reviewed accommodation sampling policy."]` | `estimated` | no |
| `trust_manifest:stay_destinations:bruson` | `display_name` | `null` | `"Bruson"` | `estimated` | no |
| `trust_manifest:stay_destinations:bruson` | `field_source_refs` | `null` | `{"coordinates": ["https://www.openstreetmap.org/node/240097683"], "identity_location": ["https://www.verbier.ch/en/destination/bruson/"], "price_level": ["https://www.verbier.ch/en/destination/bruson/"]}` | `estimated` | no |
| `trust_manifest:stay_destinations:bruson` | `field_statuses` | `null` | `{"coordinates": "verified", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:bruson` | `notes` | `null` | `["Official tourism presents Bruson as a distinct four-season accommodation destination with its own quiet, traditional village character and ski access.", "The medium price level is a product-curated estimate pending a reviewed accommodation sampling policy."]` | `estimated` | no |
| `trust_manifest:stay_destinations:la-tzoumaz` | `display_name` | `null` | `"La Tzoumaz"` | `estimated` | no |
| `trust_manifest:stay_destinations:la-tzoumaz` | `field_source_refs` | `null` | `{"coordinates": ["https://www.openstreetmap.org/node/316314676"], "identity_location": ["https://www.verbier.ch/en/destination/la-tzoumaz/"], "price_level": ["https://www.verbier.ch/en/destination/la-tzoumaz/"]}` | `estimated` | no |
| `trust_manifest:stay_destinations:la-tzoumaz` | `field_statuses` | `null` | `{"coordinates": "verified", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:la-tzoumaz` | `notes` | `null` | `["Official tourism presents La Tzoumaz as a distinct family-focused accommodation destination with direct Savoleyres lift access and a quieter recommendation context than Verbier.", "The medium price level is a product-curated estimate pending a reviewed accommodation sampling policy."]` | `estimated` | no |
| `trust_manifest:stay_destinations:verbier` | `field_source_refs` | `{"coordinates": [], "identity_location": [], "price_level": []}` | `{"coordinates": ["https://www.openstreetmap.org/node/310532759"], "identity_location": ["https://www.verbier.ch/en/destination/verbier/"], "price_level": ["https://www.verbier.ch/en/destination/verbier/"]}` | `estimated` | no |
| `trust_manifest:stay_destinations:verbier` | `field_statuses` | `{"coordinates": "needs_source", "identity_location": "needs_source", "price_level": "estimated"}` | `{"coordinates": "verified_with_adjustment", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:verbier` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Official tourism treats Verbier as a distinct international accommodation destination inside the wider Verbier trip market.", "The high price level is a product-curated estimate pending a reviewed accommodation sampling policy."]` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:verbier-4-vallees-pass` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `name` | `changed` |  |
| `lift_pass_product:verbier-4-vallees-pass` | `pass_accessible_terrain` | `unresolved` | The complete 4 Vallées aggregate remains external context until the missing ski areas and connected terrain domain are modeled. |
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
| `rental_display_fact:verbier-mountain-air` | `stay_base_id` | `reviewed-no-change` |  |
| `rental_display_fact:verbier-mountain-air` | `stay_destination_id` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `base_elevation_m` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `glacier_terrain.availability` | `unresolved` | Reviewed sources do not establish maintained glacier ski terrain for the 106 km Verbier-sector owner. |
| `ski_area:verbier-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `marked_freeride_routes.availability` | `changed` |  |
| `ski_area:verbier-ski-area` | `marked_freeride_routes.route_count` | `changed` |  |
| `ski_area:verbier-ski-area` | `marked_freeride_routes.season_label` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `name` | `changed` |  |
| `ski_area:verbier-ski-area` | `night_skiing.availability` | `unresolved` | Reviewed sources do not establish a recurring public floodlit alpine-skiing offer for the Verbier sector. |
| `ski_area:verbier-ski-area` | `night_skiing.season_label` | `unresolved` | No qualifying recurring night-skiing offer exists to label. |
| `ski_area:verbier-ski-area` | `official_trail_map.season_label` | `unresolved` | No child-scoped Verbier-sector map was found, so no local map season label can be stored. |
| `ski_area:verbier-ski-area` | `official_trail_map.url` | `unresolved` | The available official PDF covers the complete 4 Vallées and belongs to the future connected terrain domain, not this narrower ski-area owner. |
| `ski_area:verbier-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | No current official Verbier-sector difficulty-kilometre subtotal was found. |
| `ski_area:verbier-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | No current official Verbier-sector difficulty-kilometre subtotal was found. |
| `ski_area:verbier-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | No current official Verbier-sector difficulty-kilometre subtotal was found. |
| `ski_area:verbier-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:verbier-ski-area` | `season_windows` | `unresolved` | Reviewed operator sources publish conditions-dependent sector operation, not a complete stable future Verbier-sector window. |
| `ski_area:verbier-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:verbier-ski-area` | `ski_day_apres_profile.intensity` | `changed` |  |
| `ski_area:verbier-ski-area` | `ski_day_apres_profile.season_label` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `snow_park.availability` | `changed` |  |
| `ski_area:verbier-ski-area` | `snow_park.park_count` | `changed` |  |
| `ski_area:verbier-ski-area` | `snow_park.season_label` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `snowmaking.availability` | `changed` |  |
| `ski_area:verbier-ski-area` | `snowmaking.coverage_basis` | `unresolved` | The operator says most marked slopes have snowmaking but supplies no comparable denominator. |
| `ski_area:verbier-ski-area` | `snowmaking.coverage_pct` | `unresolved` | The operator says most marked slopes have snowmaking but publishes no exact coverage percentage. |
| `ski_area:verbier-ski-area` | `snowmaking.season_label` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `summit_elevation_m` | `reviewed-no-change` |  |
| `ski_area:verbier-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:verbier-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:verbier-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `distance_m` | `reviewed-no-change` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `duration_minutes` | `reviewed-no-change` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `duration_minutes` | `reviewed-no-change` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `distance_m` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `duration_minutes` | `reviewed-no-change` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `is_direct` | `reviewed-no-change` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `lift_distance` | `reviewed-no-change` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `ski_area_access_id` | `reviewed-no-change` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `stay_base_id` | `reviewed-no-change` |  |
| `ski_region:verbier` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:verbier` | `name` | `reviewed-no-change` |  |
| `ski_region:verbier` | `parent_ski_region_id` | `reviewed-no-change` |  |
| `ski_region:verbier` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:verbier` | `source_urls` | `reviewed-no-change` |  |
| `stay_base:bruson-bruson` | `base_character.development_style` | `changed` |  |
| `stay_base:bruson-bruson` | `base_character.local_pace` | `changed` |  |
| `stay_base:bruson-bruson` | `base_type` | `changed` |  |
| `stay_base:bruson-bruson` | `elevation_m` | `changed` |  |
| `stay_base:bruson-bruson` | `latitude` | `changed` |  |
| `stay_base:bruson-bruson` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:bruson-bruson` | `local_apres_profile.intensity` | `unresolved` | No recurring base-local apres profile was established for this new stay base. |
| `stay_base:bruson-bruson` | `local_apres_profile.season_label` | `unresolved` | No recurring base-local apres profile was established for this new stay base. |
| `stay_base:bruson-bruson` | `longitude` | `changed` |  |
| `stay_base:bruson-bruson` | `name` | `changed` |  |
| `stay_base:bruson-bruson` | `price_max` | `changed` |  |
| `stay_base:bruson-bruson` | `price_min` | `changed` |  |
| `stay_base:bruson-bruson` | `price_range` | `changed` |  |
| `stay_base:bruson-bruson` | `quality` | `changed` |  |
| `stay_base:bruson-bruson` | `regional_data_ids` | `changed` |  |
| `stay_base:bruson-bruson` | `stay_base_id` | `changed` |  |
| `stay_base:bruson-bruson` | `stay_destination_id` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `base_character.development_style` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `base_character.local_pace` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `base_type` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `elevation_m` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `latitude` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `local_apres_profile.intensity` | `unresolved` | No recurring base-local apres profile was established for this new stay base. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `local_apres_profile.season_label` | `unresolved` | No recurring base-local apres profile was established for this new stay base. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `longitude` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `name` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `price_max` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `price_min` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `price_range` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `quality` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `regional_data_ids` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `stay_base_id` | `changed` |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `stay_destination_id` | `changed` |  |
| `stay_base:verbier-verbier` | `base_character.development_style` | `changed` |  |
| `stay_base:verbier-verbier` | `base_character.local_pace` | `changed` |  |
| `stay_base:verbier-verbier` | `base_type` | `changed` |  |
| `stay_base:verbier-verbier` | `elevation_m` | `changed` |  |
| `stay_base:verbier-verbier` | `latitude` | `changed` |  |
| `stay_base:verbier-verbier` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:verbier-verbier` | `local_apres_profile.intensity` | `changed` |  |
| `stay_base:verbier-verbier` | `local_apres_profile.season_label` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `longitude` | `changed` |  |
| `stay_base:verbier-verbier` | `name` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `price_max` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `price_min` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `price_range` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `quality` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `regional_data_ids` | `changed` |  |
| `stay_base:verbier-verbier` | `stay_base_id` | `reviewed-no-change` |  |
| `stay_base:verbier-verbier` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:bruson` | `country` | `changed` |  |
| `stay_destination:bruson` | `latitude` | `changed` |  |
| `stay_destination:bruson` | `longitude` | `changed` |  |
| `stay_destination:bruson` | `name` | `changed` |  |
| `stay_destination:bruson` | `price_level` | `changed` |  |
| `stay_destination:bruson` | `region` | `changed` |  |
| `stay_destination:bruson` | `regional_data_ids` | `changed` |  |
| `stay_destination:bruson` | `stay_destination_id` | `changed` |  |
| `stay_destination:bruson` | `trip_market_region_id` | `changed` |  |
| `stay_destination:la-tzoumaz` | `country` | `changed` |  |
| `stay_destination:la-tzoumaz` | `latitude` | `changed` |  |
| `stay_destination:la-tzoumaz` | `longitude` | `changed` |  |
| `stay_destination:la-tzoumaz` | `name` | `changed` |  |
| `stay_destination:la-tzoumaz` | `price_level` | `changed` |  |
| `stay_destination:la-tzoumaz` | `region` | `changed` |  |
| `stay_destination:la-tzoumaz` | `regional_data_ids` | `changed` |  |
| `stay_destination:la-tzoumaz` | `stay_destination_id` | `changed` |  |
| `stay_destination:la-tzoumaz` | `trip_market_region_id` | `changed` |  |
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
| `trust_manifest:rental_display_facts:verbier-mountain-air` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:rental_display_facts:verbier-mountain-air` | `field_source_refs` | `reviewed-no-change` |  |
| `trust_manifest:rental_display_facts:verbier-mountain-air` | `field_statuses` | `reviewed-no-change` |  |
| `trust_manifest:rental_display_facts:verbier-mountain-air` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_area_access:bruson-bruson--verbier-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:bruson-bruson--verbier-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:bruson-bruson--verbier-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:bruson-bruson--verbier-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:verbier-verbier--verbier-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:verbier-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:verbier-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:verbier-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:verbier-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_regions:verbier` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_regions:verbier` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_regions:verbier` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_regions:verbier` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:bruson-bruson` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:bruson-bruson` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:bruson-bruson` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:bruson-bruson` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:la-tzoumaz-la-tzoumaz` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:la-tzoumaz-la-tzoumaz` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:la-tzoumaz-la-tzoumaz` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:la-tzoumaz-la-tzoumaz` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:verbier-verbier` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:verbier-verbier` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:verbier-verbier` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:verbier-verbier` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:bruson` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:bruson` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:bruson` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:bruson` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:la-tzoumaz` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:la-tzoumaz` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:la-tzoumaz` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:la-tzoumaz` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:verbier` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:stay_destinations:verbier` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:verbier` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:verbier` | `notes` | `changed` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:verbier-4-vallees-pass` | `available_from_stay_destination_ids` | [Official 4 Vallées ski-area profile](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `["bruson", "la-tzoumaz", "verbier"]` | The operator identifies the 4 Vallées product context and the six connected resorts covered by the wider network. | The source fact is normalized to Snowcast's available_from_stay_destination_ids representation and scoped to lift_pass_product:verbier-4-vallees-pass. |
| `lift_pass_product:verbier-4-vallees-pass` | `default_for_stay_destination_ids` | [Official 4 Vallées ski-area profile](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `["verbier"]` | The operator identifies the 4 Vallées product context and the six connected resorts covered by the wider network. | The source fact is normalized to Snowcast's default_for_stay_destination_ids representation and scoped to lift_pass_product:verbier-4-vallees-pass. |
| `lift_pass_product:verbier-4-vallees-pass` | `external_validity_summary` | [Official 4 Vallées ski-area profile](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `"Covers the modeled Verbier sector (Verbier, La Tzoumaz-Savoleyres and Bruson) plus the wider 4 Vallées network of Nendaz, Veysonnaz and Thyon when those links are operating."` | The operator identifies the 4 Vallées product context and the six connected resorts covered by the wider network. | The source fact is normalized to Snowcast's external_validity_summary representation and scoped to lift_pass_product:verbier-4-vallees-pass. |
| `lift_pass_product:verbier-4-vallees-pass` | `lift_pass_product_id` | [Official 4 Vallées ski-area profile](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `"verbier-4-vallees-pass"` | The operator identifies the 4 Vallées product context and the six connected resorts covered by the wider network. |  |
| `lift_pass_product:verbier-4-vallees-pass` | `name` | [Official 4 Vallées ski-area profile](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `"4 Vallées ski pass"` | The operator identifies the 4 Vallées product context and the six connected resorts covered by the wider network. |  |
| `lift_pass_product:verbier-4-vallees-pass` | `prices` | [Verbier.com 2025/26 ski-pass table](https://www.verbier.com/ski-passes) | `[{"amount": 94.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 4 Vallées adult cash-desk tariff", "source_url": "https://www.verbier.com/ski-passes"}, {"amount": 247.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 4 Vallées adult cash-desk tariff", "source_url": "https://www.verbier.com/ski-passes"}, {"amount": 409.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 4 Vallées adult cash-desk tariff", "source_url": "https://www.verbier.com/ski-passes"}]` | The reviewed commercial tariff table lists adult 4 Vallées cash-desk prices of CHF 94 for one day, CHF 247 for three days, and CHF 409 for six days. | The source fact is normalized to Snowcast's prices representation and scoped to lift_pass_product:verbier-4-vallees-pass. |
| `lift_pass_product:verbier-4-vallees-pass` | `terrain_domain_ids` | [Official 4 Vallées ski-area profile](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `[]` | The operator identifies the 4 Vallées product context and the six connected resorts covered by the wider network. | The source fact is normalized to Snowcast's terrain_domain_ids representation and scoped to lift_pass_product:verbier-4-vallees-pass. |
| `lift_pass_product:verbier-4-vallees-pass` | `valid_ski_area_ids` | [Official 4 Vallées ski-area profile](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `["verbier-ski-area"]` | The operator identifies the 4 Vallées product context and the six connected resorts covered by the wider network. | The source fact is normalized to Snowcast's valid_ski_area_ids representation and scoped to lift_pass_product:verbier-4-vallees-pass. |
| `lift_pass_product:verbier-4-vallees-pass` | `validity_scope` | [Official 4 Vallées ski-area profile](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `"regional_network"` | The operator identifies the 4 Vallées product context and the six connected resorts covered by the wider network. | The source fact is normalized to Snowcast's validity_scope representation and scoped to lift_pass_product:verbier-4-vallees-pass. |
| `ski_area:verbier-ski-area` | `marked_freeride_routes.availability` | [Official Verbier 4Vallées freeride itineraries](https://verbier4vallees.ch/en/experiences-in-verbier/freeriding) | `"available"` | The operator lists seven marked, secured and ungroomed itineraries and assigns six to Verbier, La Tzoumaz or Bruson. |  |
| `ski_area:verbier-ski-area` | `marked_freeride_routes.route_count` | [Official Verbier 4Vallées freeride itineraries](https://verbier4vallees.ch/en/experiences-in-verbier/freeriding) | `6` | The operator lists seven marked, secured and ungroomed itineraries and assigns six to Verbier, La Tzoumaz or Bruson. | The source fact is normalized to Snowcast's marked_freeride_routes.route_count representation and scoped to ski_area:verbier-ski-area. |
| `ski_area:verbier-ski-area` | `name` | [Official Verbier ski-resort scope](https://verbier4vallees.ch/en/ski-resort) | `"Verbier sector"` | The operator defines the Verbier sector as Verbier, La Tzoumaz-Savoleyres and Bruson with 106 km of runs and 33 lifts. |  |
| `ski_area:verbier-ski-area` | `season_start_month` | [Official Verbier ski-resort scope](https://verbier4vallees.ch/en/ski-resort) | `11` | The operator defines the Verbier sector as Verbier, La Tzoumaz-Savoleyres and Bruson with 106 km of runs and 33 lifts. | The source fact is normalized to Snowcast's season_start_month representation and scoped to ski_area:verbier-ski-area. |
| `ski_area:verbier-ski-area` | `ski_day_apres_profile.availability` | [Official Verbier sector profile](https://verbier4vallees.ch/en/ski-resort/verbier) | `"available"` | The operator describes runs at all difficulty levels and presents after-ski as a defining part of the Verbier ski day. | The source fact is normalized to Snowcast's ski_day_apres_profile.availability representation and scoped to ski_area:verbier-ski-area. |
| `ski_area:verbier-ski-area` | `ski_day_apres_profile.intensity` | [Official Verbier sector profile](https://verbier4vallees.ch/en/ski-resort/verbier) | `"destination_defining"` | The operator describes runs at all difficulty levels and presents after-ski as a defining part of the Verbier ski day. | The source fact is normalized to Snowcast's ski_day_apres_profile.intensity representation and scoped to ski_area:verbier-ski-area. |
| `ski_area:verbier-ski-area` | `snow_park.availability` | [Official Verbier fun zones](https://verbier4vallees.ch/en/experiences-in-verbier/fun-zones) | `"available"` | The operator documents the dedicated Verbier Snowpark at La Chaux. |  |
| `ski_area:verbier-ski-area` | `snow_park.park_count` | [Official Verbier fun zones](https://verbier4vallees.ch/en/experiences-in-verbier/fun-zones) | `1` | The operator documents the dedicated Verbier Snowpark at La Chaux. |  |
| `ski_area:verbier-ski-area` | `snowmaking.availability` | [About Téléverbier](https://verbier4vallees.ch/en/about-us) | `"available"` | Téléverbier states that most marked slopes in its operated domain have artificial snowmaking facilities. |  |
| `ski_area:verbier-ski-area` | `supported_skill_levels` | [Official Verbier sector profile](https://verbier4vallees.ch/en/ski-resort/verbier) | `["beginner", "intermediate", "advanced"]` | The operator describes runs at all difficulty levels and presents after-ski as a defining part of the Verbier ski day. | The source fact is normalized to Snowcast's supported_skill_levels representation and scoped to ski_area:verbier-ski-area. |
| `ski_area:verbier-ski-area` | `total_lift_count` | [Official Verbier ski-resort scope](https://verbier4vallees.ch/en/ski-resort) | `33` | The operator defines the Verbier sector as Verbier, La Tzoumaz-Savoleyres and Bruson with 106 km of runs and 33 lifts. |  |
| `ski_area:verbier-ski-area` | `total_piste_km` | [Official Verbier ski-resort scope](https://verbier4vallees.ch/en/ski-resort) | `106.0` | The operator defines the Verbier sector as Verbier, La Tzoumaz-Savoleyres and Bruson with 106 km of runs and 33 lifts. |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `access_mode` | [Official Bruson destination access](https://www.verbier.ch/en/destination/bruson/) | `"ski_bus"` | Official tourism documents bus access to Bruson and an onward shuttle to the Mayens de Bruson lift base. | The source fact is normalized to Snowcast's access_mode representation and scoped to ski_area_access:bruson-bruson--verbier-ski-area. |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `is_direct` | [Official Bruson destination access](https://www.verbier.ch/en/destination/bruson/) | `false` | Official tourism documents bus access to Bruson and an onward shuttle to the Mayens de Bruson lift base. | The source fact is normalized to Snowcast's is_direct representation and scoped to ski_area_access:bruson-bruson--verbier-ski-area. |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `lift_distance` | [Official Bruson destination access](https://www.verbier.ch/en/destination/bruson/) | `"far"` | Official tourism documents bus access to Bruson and an onward shuttle to the Mayens de Bruson lift base. | The source fact is normalized to Snowcast's lift_distance representation and scoped to ski_area_access:bruson-bruson--verbier-ski-area. |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `nearest_lift_name` | [Official Bruson destination access](https://www.verbier.ch/en/destination/bruson/) | `"Mayens de Bruson lifts"` | Official tourism documents bus access to Bruson and an onward shuttle to the Mayens de Bruson lift base. |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `regional_data_ids` | [OpenStreetMap Bruson village](https://www.openstreetmap.org/node/240097683) | `{"stay_base_osm_node_id": "240097683", "valbord_bus_stop_osm_node_id": "300965457"}` | Open data identifies the Bruson village and Valbord public-transport nodes. | The source fact is normalized to Snowcast's regional_data_ids representation and scoped to ski_area_access:bruson-bruson--verbier-ski-area. |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `ski_area_access_id` | [Official Bruson destination access](https://www.verbier.ch/en/destination/bruson/) | `"bruson-bruson--verbier-ski-area"` | Official tourism documents bus access to Bruson and an onward shuttle to the Mayens de Bruson lift base. |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `ski_area_id` | [Official Bruson destination access](https://www.verbier.ch/en/destination/bruson/) | `"verbier-ski-area"` | Official tourism documents bus access to Bruson and an onward shuttle to the Mayens de Bruson lift base. |  |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `source_urls` | [Official Bruson destination access](https://www.verbier.ch/en/destination/bruson/) | `["https://www.openstreetmap.org/node/240097683", "https://www.openstreetmap.org/node/300965457", "https://www.verbier.ch/en/destination/bruson/"]` | Official tourism documents bus access to Bruson and an onward shuttle to the Mayens de Bruson lift base. | The source fact is normalized to Snowcast's source_urls representation and scoped to ski_area_access:bruson-bruson--verbier-ski-area. |
| `ski_area_access:bruson-bruson--verbier-ski-area` | `stay_base_id` | [Official Bruson destination access](https://www.verbier.ch/en/destination/bruson/) | `"bruson-bruson"` | Official tourism documents bus access to Bruson and an onward shuttle to the Mayens de Bruson lift base. |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `access_mode` | [Official La Tzoumaz accommodation access](https://verbier4vallees.ch/en/experiences-in-verbier/accommodation) | `"walk"` | The operator places T-Resort at the foot of the slopes opposite the cable-car station. | The source fact is normalized to Snowcast's access_mode representation and scoped to ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area. |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `distance_m` | [OpenStreetMap La Tzoumaz gondola station](https://www.openstreetmap.org/node/316315926) | `140` | Open data locates the La Tzoumaz village and Savoleyres gondola station about 140 metres apart. | The source fact is normalized to Snowcast's distance_m representation and scoped to ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area. |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `is_direct` | [Official La Tzoumaz accommodation access](https://verbier4vallees.ch/en/experiences-in-verbier/accommodation) | `true` | The operator places T-Resort at the foot of the slopes opposite the cable-car station. | The source fact is normalized to Snowcast's is_direct representation and scoped to ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area. |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `lift_distance` | [Official La Tzoumaz accommodation access](https://verbier4vallees.ch/en/experiences-in-verbier/accommodation) | `"near"` | The operator places T-Resort at the foot of the slopes opposite the cable-car station. | The source fact is normalized to Snowcast's lift_distance representation and scoped to ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area. |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `nearest_lift_name` | [Official La Tzoumaz accommodation access](https://verbier4vallees.ch/en/experiences-in-verbier/accommodation) | `"La Tzoumaz-Savoleyres gondola"` | The operator places T-Resort at the foot of the slopes opposite the cable-car station. |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `regional_data_ids` | [OpenStreetMap La Tzoumaz gondola station](https://www.openstreetmap.org/node/316315926) | `{"nearest_lift_osm_node_id": "316315926", "stay_base_osm_node_id": "316314676"}` | Open data locates the La Tzoumaz village and Savoleyres gondola station about 140 metres apart. | The source fact is normalized to Snowcast's regional_data_ids representation and scoped to ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area. |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `ski_area_access_id` | [Official La Tzoumaz accommodation access](https://verbier4vallees.ch/en/experiences-in-verbier/accommodation) | `"la-tzoumaz-la-tzoumaz--verbier-ski-area"` | The operator places T-Resort at the foot of the slopes opposite the cable-car station. |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `ski_area_id` | [Official La Tzoumaz accommodation access](https://verbier4vallees.ch/en/experiences-in-verbier/accommodation) | `"verbier-ski-area"` | The operator places T-Resort at the foot of the slopes opposite the cable-car station. |  |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `source_urls` | [Official La Tzoumaz accommodation access](https://verbier4vallees.ch/en/experiences-in-verbier/accommodation) | `["https://verbier4vallees.ch/en/experiences-in-verbier/accommodation", "https://www.openstreetmap.org/node/316314676", "https://www.openstreetmap.org/node/316315926"]` | The operator places T-Resort at the foot of the slopes opposite the cable-car station. | The source fact is normalized to Snowcast's source_urls representation and scoped to ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area. |
| `ski_area_access:la-tzoumaz-la-tzoumaz--verbier-ski-area` | `stay_base_id` | [Official La Tzoumaz accommodation access](https://verbier4vallees.ch/en/experiences-in-verbier/accommodation) | `"la-tzoumaz-la-tzoumaz"` | The operator places T-Resort at the foot of the slopes opposite the cable-car station. |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `access_mode` | [Official Médran departure point](https://verbier4vallees.ch/en/useful-information/points-of-sale/sales-desks-and-infopoint_infrastructure_1230) | `"walk"` | The operator identifies Médran as a principal departure point for Verbier-sector ski days. | The source fact is normalized to Snowcast's access_mode representation and scoped to ski_area_access:verbier-verbier--verbier-ski-area. |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `distance_m` | [OpenStreetMap Médran gondola station](https://www.openstreetmap.org/node/3415318439) | `490` | Open data locates the Verbier village reference point and Médran gondola about 490 metres apart. | The source fact is normalized to Snowcast's distance_m representation and scoped to ski_area_access:verbier-verbier--verbier-ski-area. |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `nearest_lift_name` | [Official Médran departure point](https://verbier4vallees.ch/en/useful-information/points-of-sale/sales-desks-and-infopoint_infrastructure_1230) | `"Medran / Place Blanche"` | The operator identifies Médran as a principal departure point for Verbier-sector ski days. |  |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `regional_data_ids` | [OpenStreetMap Médran gondola station](https://www.openstreetmap.org/node/3415318439) | `{"nearest_lift_osm_node_id": "3415318439", "stay_base_osm_node_id": "310532759"}` | Open data locates the Verbier village reference point and Médran gondola about 490 metres apart. | The source fact is normalized to Snowcast's regional_data_ids representation and scoped to ski_area_access:verbier-verbier--verbier-ski-area. |
| `ski_area_access:verbier-verbier--verbier-ski-area` | `source_urls` | [Official Médran departure point](https://verbier4vallees.ch/en/useful-information/points-of-sale/sales-desks-and-infopoint_infrastructure_1230) | `["https://www.openstreetmap.org/node/310532759", "https://www.openstreetmap.org/node/3415318439", "https://verbier4vallees.ch/en/useful-information/points-of-sale/sales-desks-and-infopoint_infrastructure_1230"]` | The operator identifies Médran as a principal departure point for Verbier-sector ski days. | The source fact is normalized to Snowcast's source_urls representation and scoped to ski_area_access:verbier-verbier--verbier-ski-area. |
| `stay_base:bruson-bruson` | `base_character.development_style` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"traditional"` | Official tourism establishes the named village, its accommodation context, and its published character. | The source fact is normalized to Snowcast's base_character.development_style representation and scoped to stay_base:bruson-bruson. |
| `stay_base:bruson-bruson` | `base_character.local_pace` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"quiet"` | Official tourism establishes the named village, its accommodation context, and its published character. | The source fact is normalized to Snowcast's base_character.local_pace representation and scoped to stay_base:bruson-bruson. |
| `stay_base:bruson-bruson` | `base_type` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"village"` | Official tourism establishes the named village, its accommodation context, and its published character. |  |
| `stay_base:bruson-bruson` | `elevation_m` | [Official Verbier winter pocket guide](https://www.verbier.ch/app/uploads/ot-verbier/2024/11/Verbier_PocketGuide_Hivers_241024-10-bd.pdf) | `1080` | The official winter pocket guide labels Bruson at 1,080 metres. |  |
| `stay_base:bruson-bruson` | `latitude` | [OpenStreetMap bruson-bruson place record](https://www.openstreetmap.org/node/240097683) | `46.0662119` | Open data supplies the normalized stay-base reference point and regional ID. | The source fact is normalized to Snowcast's latitude representation and scoped to stay_base:bruson-bruson. |
| `stay_base:bruson-bruson` | `longitude` | [OpenStreetMap bruson-bruson place record](https://www.openstreetmap.org/node/240097683) | `7.2186328` | Open data supplies the normalized stay-base reference point and regional ID. | The source fact is normalized to Snowcast's longitude representation and scoped to stay_base:bruson-bruson. |
| `stay_base:bruson-bruson` | `name` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"Bruson"` | Official tourism establishes the named village, its accommodation context, and its published character. |  |
| `stay_base:bruson-bruson` | `price_max` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `230.0` | Official tourism establishes the named village, its accommodation context, and its published character. | This is a product-curated estimate; the source establishes the accommodation context but not the exact value. |
| `stay_base:bruson-bruson` | `price_min` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `150.0` | Official tourism establishes the named village, its accommodation context, and its published character. | This is a product-curated estimate; the source establishes the accommodation context but not the exact value. |
| `stay_base:bruson-bruson` | `price_range` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"EUR 150-230"` | Official tourism establishes the named village, its accommodation context, and its published character. | This is a product-curated estimate; the source establishes the accommodation context but not the exact value. |
| `stay_base:bruson-bruson` | `quality` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"standard"` | Official tourism establishes the named village, its accommodation context, and its published character. | This is a product-curated estimate; the source establishes the accommodation context but not the exact value. |
| `stay_base:bruson-bruson` | `regional_data_ids` | [OpenStreetMap bruson-bruson place record](https://www.openstreetmap.org/node/240097683) | `{"osm_node_id": "240097683"}` | Open data supplies the normalized stay-base reference point and regional ID. | The source fact is normalized to Snowcast's regional_data_ids representation and scoped to stay_base:bruson-bruson. |
| `stay_base:bruson-bruson` | `stay_base_id` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"bruson-bruson"` | Official tourism establishes the named village, its accommodation context, and its published character. |  |
| `stay_base:bruson-bruson` | `stay_destination_id` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"bruson"` | Official tourism establishes the named village, its accommodation context, and its published character. | The source fact is normalized to Snowcast's stay_destination_id representation and scoped to stay_base:bruson-bruson. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `base_character.development_style` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"mixed"` | Official tourism establishes the named village, its accommodation context, and its published character. | The source fact is normalized to Snowcast's base_character.development_style representation and scoped to stay_base:la-tzoumaz-la-tzoumaz. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `base_character.local_pace` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"quiet"` | Official tourism establishes the named village, its accommodation context, and its published character. | The source fact is normalized to Snowcast's base_character.local_pace representation and scoped to stay_base:la-tzoumaz-la-tzoumaz. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `base_type` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"village"` | Official tourism establishes the named village, its accommodation context, and its published character. |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `elevation_m` | [Official la-tzoumaz-la-tzoumaz elevation context](https://verbier4vallees.ch/en/experiences-in-verbier/accommodation) | `1500` | Official destination or operator material establishes the representative village elevation used by Snowcast. |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `latitude` | [OpenStreetMap la-tzoumaz-la-tzoumaz place record](https://www.openstreetmap.org/node/316314676) | `46.1444445` | Open data supplies the normalized stay-base reference point and regional ID. | The source fact is normalized to Snowcast's latitude representation and scoped to stay_base:la-tzoumaz-la-tzoumaz. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `longitude` | [OpenStreetMap la-tzoumaz-la-tzoumaz place record](https://www.openstreetmap.org/node/316314676) | `7.2348916` | Open data supplies the normalized stay-base reference point and regional ID. | The source fact is normalized to Snowcast's longitude representation and scoped to stay_base:la-tzoumaz-la-tzoumaz. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `name` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"La Tzoumaz"` | Official tourism establishes the named village, its accommodation context, and its published character. |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `price_max` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `260.0` | Official tourism establishes the named village, its accommodation context, and its published character. | This is a product-curated estimate; the source establishes the accommodation context but not the exact value. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `price_min` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `170.0` | Official tourism establishes the named village, its accommodation context, and its published character. | This is a product-curated estimate; the source establishes the accommodation context but not the exact value. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `price_range` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"EUR 170-260"` | Official tourism establishes the named village, its accommodation context, and its published character. | This is a product-curated estimate; the source establishes the accommodation context but not the exact value. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `quality` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"standard"` | Official tourism establishes the named village, its accommodation context, and its published character. | This is a product-curated estimate; the source establishes the accommodation context but not the exact value. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `regional_data_ids` | [OpenStreetMap la-tzoumaz-la-tzoumaz place record](https://www.openstreetmap.org/node/316314676) | `{"osm_node_id": "316314676"}` | Open data supplies the normalized stay-base reference point and regional ID. | The source fact is normalized to Snowcast's regional_data_ids representation and scoped to stay_base:la-tzoumaz-la-tzoumaz. |
| `stay_base:la-tzoumaz-la-tzoumaz` | `stay_base_id` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"la-tzoumaz-la-tzoumaz"` | Official tourism establishes the named village, its accommodation context, and its published character. |  |
| `stay_base:la-tzoumaz-la-tzoumaz` | `stay_destination_id` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"la-tzoumaz"` | Official tourism establishes the named village, its accommodation context, and its published character. | The source fact is normalized to Snowcast's stay_destination_id representation and scoped to stay_base:la-tzoumaz-la-tzoumaz. |
| `stay_base:verbier-verbier` | `base_character.development_style` | [Official Verbier destination profile](https://www.verbier.ch/en/destination/verbier/) | `"mixed"` | Official tourism establishes the named village, its accommodation context, and its published character. | The source fact is normalized to Snowcast's base_character.development_style representation and scoped to stay_base:verbier-verbier. |
| `stay_base:verbier-verbier` | `base_character.local_pace` | [Official Verbier destination profile](https://www.verbier.ch/en/destination/verbier/) | `"lively"` | Official tourism establishes the named village, its accommodation context, and its published character. | The source fact is normalized to Snowcast's base_character.local_pace representation and scoped to stay_base:verbier-verbier. |
| `stay_base:verbier-verbier` | `base_type` | [Official Verbier destination profile](https://www.verbier.ch/en/destination/verbier/) | `"village"` | Official tourism establishes the named village, its accommodation context, and its published character. |  |
| `stay_base:verbier-verbier` | `elevation_m` | [Official verbier-verbier elevation context](https://www.verbier.ch/en/) | `1500` | Official destination or operator material establishes the representative village elevation used by Snowcast. |  |
| `stay_base:verbier-verbier` | `latitude` | [OpenStreetMap verbier-verbier place record](https://www.openstreetmap.org/node/310532759) | `46.0961` | Open data supplies the normalized stay-base reference point and regional ID. | The source fact is normalized to Snowcast's latitude representation and scoped to stay_base:verbier-verbier. |
| `stay_base:verbier-verbier` | `local_apres_profile.availability` | [Official Verbier destination profile](https://www.verbier.ch/en/destination/verbier/) | `"available"` | Official tourism establishes the named village, its accommodation context, and its published character. | The source fact is normalized to Snowcast's local_apres_profile.availability representation and scoped to stay_base:verbier-verbier. |
| `stay_base:verbier-verbier` | `local_apres_profile.intensity` | [Official Verbier destination profile](https://www.verbier.ch/en/destination/verbier/) | `"destination_defining"` | Official tourism establishes the named village, its accommodation context, and its published character. | The source fact is normalized to Snowcast's local_apres_profile.intensity representation and scoped to stay_base:verbier-verbier. |
| `stay_base:verbier-verbier` | `longitude` | [OpenStreetMap verbier-verbier place record](https://www.openstreetmap.org/node/310532759) | `7.2287` | Open data supplies the normalized stay-base reference point and regional ID. | The source fact is normalized to Snowcast's longitude representation and scoped to stay_base:verbier-verbier. |
| `stay_base:verbier-verbier` | `regional_data_ids` | [OpenStreetMap verbier-verbier place record](https://www.openstreetmap.org/node/310532759) | `{"osm_node_id": "310532759", "rental_osm_node_id": "1038335696"}` | Open data supplies the normalized stay-base reference point and regional ID. | The source fact is normalized to Snowcast's regional_data_ids representation and scoped to stay_base:verbier-verbier. |
| `stay_destination:bruson` | `country` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"Switzerland"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. |  |
| `stay_destination:bruson` | `latitude` | [OpenStreetMap bruson place record](https://www.openstreetmap.org/node/240097683) | `46.0662119` | Open data supplies the normalized destination reference point and regional ID. | The source fact is normalized to Snowcast's latitude representation and scoped to stay_destination:bruson. |
| `stay_destination:bruson` | `longitude` | [OpenStreetMap bruson place record](https://www.openstreetmap.org/node/240097683) | `7.2186328` | Open data supplies the normalized destination reference point and regional ID. | The source fact is normalized to Snowcast's longitude representation and scoped to stay_destination:bruson. |
| `stay_destination:bruson` | `name` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"Bruson"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. |  |
| `stay_destination:bruson` | `price_level` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"medium"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. | This is a product-curated estimate; the source establishes the accommodation context but not the exact value. |
| `stay_destination:bruson` | `region` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"Valais"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. |  |
| `stay_destination:bruson` | `regional_data_ids` | [OpenStreetMap bruson place record](https://www.openstreetmap.org/node/240097683) | `{"osm_node_id": "240097683"}` | Open data supplies the normalized destination reference point and regional ID. | The source fact is normalized to Snowcast's regional_data_ids representation and scoped to stay_destination:bruson. |
| `stay_destination:bruson` | `stay_destination_id` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"bruson"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. |  |
| `stay_destination:bruson` | `trip_market_region_id` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `"verbier"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. | The source fact is normalized to Snowcast's trip_market_region_id representation and scoped to stay_destination:bruson. |
| `stay_destination:la-tzoumaz` | `country` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"Switzerland"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. |  |
| `stay_destination:la-tzoumaz` | `latitude` | [OpenStreetMap la-tzoumaz place record](https://www.openstreetmap.org/node/316314676) | `46.1444445` | Open data supplies the normalized destination reference point and regional ID. | The source fact is normalized to Snowcast's latitude representation and scoped to stay_destination:la-tzoumaz. |
| `stay_destination:la-tzoumaz` | `longitude` | [OpenStreetMap la-tzoumaz place record](https://www.openstreetmap.org/node/316314676) | `7.2348916` | Open data supplies the normalized destination reference point and regional ID. | The source fact is normalized to Snowcast's longitude representation and scoped to stay_destination:la-tzoumaz. |
| `stay_destination:la-tzoumaz` | `name` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"La Tzoumaz"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. |  |
| `stay_destination:la-tzoumaz` | `price_level` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"medium"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. | This is a product-curated estimate; the source establishes the accommodation context but not the exact value. |
| `stay_destination:la-tzoumaz` | `region` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"Valais"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. |  |
| `stay_destination:la-tzoumaz` | `regional_data_ids` | [OpenStreetMap la-tzoumaz place record](https://www.openstreetmap.org/node/316314676) | `{"osm_node_id": "316314676"}` | Open data supplies the normalized destination reference point and regional ID. | The source fact is normalized to Snowcast's regional_data_ids representation and scoped to stay_destination:la-tzoumaz. |
| `stay_destination:la-tzoumaz` | `stay_destination_id` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"la-tzoumaz"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. |  |
| `stay_destination:la-tzoumaz` | `trip_market_region_id` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `"verbier"` | Official tourism treats this place as a named, bookable accommodation destination with its own recommendation context. | The source fact is normalized to Snowcast's trip_market_region_id representation and scoped to stay_destination:la-tzoumaz. |
| `stay_destination:verbier` | `name` | [Official Verbier destination profile](https://www.verbier.ch/en/destination/verbier/) | `{"bookable": true, "destination": "verbier", "distinct_access": true, "distinct_recommendation_context": true}` | Verbier is an international Alpine village with independent accommodation, access, atmosphere, and recommendation value. | The source's destination treatment is evaluated through Snowcast's three stay-destination boundary gates. |
| `stay_destination:la-tzoumaz` | `name` | [Official La Tzoumaz destination profile](https://www.verbier.ch/en/destination/la-tzoumaz/) | `{"bookable": true, "destination": "la-tzoumaz", "distinct_access": true, "distinct_recommendation_context": true}` | La Tzoumaz has a distinct family-oriented accommodation inventory, village identity, and direct Savoleyres access. | The source's destination treatment is evaluated through Snowcast's three stay-destination boundary gates. |
| `stay_destination:bruson` | `name` | [Official Bruson destination profile](https://www.verbier.ch/en/destination/bruson/) | `{"bookable": true, "destination": "bruson", "distinct_access": true, "distinct_recommendation_context": true}` | Bruson has a distinct quiet traditional-village offer, accommodation inventory, and its own shuttle access to the ski sector. | The source's destination treatment is evaluated through Snowcast's three stay-destination boundary gates. |
| `ski_area:verbier-ski-area` | `name` | [Official Verbier-sector definition](https://verbier4vallees.ch/en/ski-resort) | `{"components": ["Verbier", "La Tzoumaz-Savoleyres", "Bruson"], "name": "Verbier", "total_lift_count": 33, "total_piste_km": 106}` | The operator publishes Verbier, La Tzoumaz-Savoleyres and Bruson together as the 106 km, 33-lift Verbier sector. | Snowcast retains one ski-area owner and uses the display name Verbier sector to make the official aggregate scope explicit. |
| `ski_area:verbier-ski-area` | `official_trail_map.url` | [Official 4 Vallées definition](https://verbier4vallees.ch/en/ski-resort/4-vallees) | `{"connected_resorts": ["Verbier", "Bruson", "La Tzoumaz", "Nendaz", "Veysonnaz", "Thyon"], "map_url": "https://verbier4vallees.ch/V4V-Website/Documents/Cartes/plan_pistes.pdf", "total_piste_km": 410}` | The operator defines a wider ski-connected six-resort domain; its full map includes Nendaz, Veysonnaz and Thyon beyond the modeled Verbier sector. | This evidence supports deferral to terrain_domain:4-vallees and explains why the map is not stored on ski_area:verbier-ski-area. |
| `ski_area:verbier-ski-area` | `official_trail_map.url` | [Téléverbier and NVRM operating boundary](https://verbier4vallees.ch/en/about-us) | `"NVRM co-manages Mont-Fort alongside Téléverbier"` | The operator explicitly names NVRM as a neighboring lift company and joint Mont-Fort operator, supporting an independent terrain-owner review. | The source establishes an operator boundary but does not by itself finalize the future Nendaz-Veysonnaz ski-area geometry. |
| `ski_area:verbier-ski-area` | `official_trail_map.url` | [Official Thyon ski-area profile](https://www.thyon.ch/winter/) | `{"local_lifts": 11, "owner_candidate": "thyon-ski-area", "season": "2025/26"}` | Thyon publishes its own local lift inventory and operating schedule while presenting connection to the wider 4 Vallées. | The independent local operating evidence requires a future ski-area owner rather than inclusion in the Verbier weather owner. |

## Boundary Decisions

- `verbier`: `pass`
- `la-tzoumaz`: `pass`
- `bruson`: `pass`

## Ranking Impact

Candidate generation can now represent Verbier, La Tzoumaz, and Bruson as distinct stay configurations against one correctly scoped ski-area owner; no runtime policy is changed by this curation.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation typed REPORT.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output REPORT.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation reconcile REPORT.json --base-catalog-path BASE/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output REPORT.md`

## Caveats

- The 4 Vallées pass price examples are fixed 2025/26 adult cash-desk tariffs from a reviewed commercial guide; the current operator page is authoritative for product availability but does not expose the static table in its rendered HTML.
- The complete 4 Vallées map, 410 km aggregate and 82-lift total belong to the deferred connected terrain domain, not the 106 km Verbier-sector ski area.
- Nendaz, Veysonnaz, Thyon, their stay networks and independent terrain owners remain deferred under one explicit catalog-curation backlog item.
- No current official Verbier-sector piste-kilometre difficulty split or stable complete future operating window was found.
- The operator confirms snowmaking on most marked slopes but publishes no exact comparable coverage percentage.
- Maintained glacier terrain and recurring public floodlit night skiing remain unknown for the modeled Verbier-sector owner.
- La Tzoumaz and Bruson lodging price ranges and quality tiers remain product-curated estimates, and no recurring base-local apres profile was established for either village.
- The current pass-default relationship is intentionally preserved pending the separate pass-product refinement.
