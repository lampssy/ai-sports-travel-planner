# Cortina d'Ampezzo Catalog Curation

Recurated Cortina's valley-pass scope and split the linked Cadore bases into separate destinations where the current boundary gates pass. San Vito di Cadore, Auronzo di Cadore, and Misurina are added as independent destinations; Cortina's 120 km valley-pass wording stays in regional pass context rather than being copied into the Cortina child ski-area terrain metrics.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `destination:auronzo-di-cadore` | `narrow` | `base_elevation_m`, `country`, `latitude`, `lift_pass_products`, `longitude`, `name`, `price_level`, `region`, `rentals`, `resort_id`, `season_end_month`, `season_start_month`, `season_windows`, `ski_areas`, `stay_bases`, `summit_elevation_m`, `terrain_groups` |
| `destination:cortina-dampezzo` | `narrow` | `lift_pass_products`, `name`, `season_end_month`, `season_start_month`, `season_windows`, `stay_bases` |
| `destination:misurina` | `narrow` | `base_elevation_m`, `country`, `latitude`, `lift_pass_products`, `longitude`, `name`, `price_level`, `region`, `rentals`, `resort_id`, `season_end_month`, `season_start_month`, `season_windows`, `ski_areas`, `stay_bases`, `summit_elevation_m`, `terrain_groups` |
| `destination:san-vito-di-cadore` | `narrow` | `base_elevation_m`, `country`, `latitude`, `lift_pass_products`, `longitude`, `name`, `price_level`, `region`, `rentals`, `resort_id`, `season_end_month`, `season_start_month`, `season_windows`, `ski_areas`, `stay_bases`, `summit_elevation_m`, `terrain_groups` |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `narrow` | `external_validity_summary`, `is_default`, `lift_pass_product_id`, `name`, `prices`, `terrain_domain_ids`, `valid_ski_area_ids`, `validity_scope` |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `narrow` | `is_default`, `lift_pass_product_id`, `name`, `prices`, `terrain_domain_ids`, `valid_ski_area_ids`, `validity_scope` |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `narrow` | `external_validity_summary`, `is_default`, `lift_pass_product_id`, `name`, `prices`, `terrain_domain_ids`, `valid_ski_area_ids`, `validity_scope` |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `narrow` | `external_validity_summary`, `is_default`, `lift_pass_product_id`, `name`, `prices`, `terrain_domain_ids`, `valid_ski_area_ids`, `validity_scope` |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `narrow` | `is_default`, `lift_pass_product_id`, `name`, `prices`, `terrain_domain_ids`, `valid_ski_area_ids`, `validity_scope` |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `narrow` | `external_validity_summary`, `is_default`, `lift_pass_product_id`, `name`, `prices`, `terrain_domain_ids`, `valid_ski_area_ids`, `validity_scope` |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `narrow` | `is_default`, `lift_pass_product_id`, `name`, `prices`, `terrain_domain_ids`, `valid_ski_area_ids`, `validity_scope` |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `narrow` | `lift_distance`, `name`, `price_max`, `price_min`, `price_range`, `quality` |
| `rental:misurina:misurina-ski-area-rental` | `narrow` | `lift_distance`, `name`, `price_max`, `price_min`, `price_range`, `quality` |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `narrow` | `lift_distance`, `name`, `price_max`, `price_min`, `price_range`, `quality` |
| `ski_area:auronzo-monte-agudo` | `narrow` | `base_elevation_m`, `latitude`, `longitude`, `name`, `piste_km_by_difficulty.advanced`, `piste_km_by_difficulty.beginner`, `piste_km_by_difficulty.intermediate`, `season_end_month`, `season_start_month`, `season_windows`, `ski_area_id`, `summit_elevation_m`, `total_lift_count`, `total_piste_km` |
| `ski_area:cortina-dampezzo-ski-area` | `narrow` | `base_elevation_m`, `season_end_month`, `season_start_month`, `season_windows`, `summit_elevation_m` |
| `ski_area:misurina-passo-tre-croci` | `narrow` | `base_elevation_m`, `latitude`, `longitude`, `name`, `piste_km_by_difficulty.advanced`, `piste_km_by_difficulty.beginner`, `piste_km_by_difficulty.intermediate`, `season_end_month`, `season_start_month`, `season_windows`, `ski_area_id`, `summit_elevation_m`, `total_lift_count`, `total_piste_km` |
| `ski_area:san-vito-di-cadore-ski-area` | `narrow` | `base_elevation_m`, `latitude`, `longitude`, `name`, `piste_km_by_difficulty.advanced`, `piste_km_by_difficulty.beginner`, `piste_km_by_difficulty.intermediate`, `season_end_month`, `season_start_month`, `season_windows`, `ski_area_id`, `summit_elevation_m`, `total_lift_count`, `total_piste_km` |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `narrow` | `access_mode`, `atmosphere_tags`, `base_type`, `latitude`, `lift_distance`, `longitude`, `name`, `nearest_lift_distance_m`, `nearest_lift_name`, `price_max`, `price_min`, `price_range`, `quality`, `regional_data_ids`, `stay_base_id`, `supported_skill_levels` |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `narrow` | `access_mode`, `atmosphere_tags`, `lift_distance`, `name`, `price_max`, `price_min`, `price_range`, `quality`, `regional_data_ids`, `stay_base_id`, `supported_skill_levels` |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `narrow` | `access_mode`, `atmosphere_tags`, `base_type`, `latitude`, `lift_distance`, `longitude`, `name`, `nearest_lift_distance_m`, `nearest_lift_name`, `price_max`, `price_min`, `price_range`, `quality`, `regional_data_ids`, `stay_base_id`, `supported_skill_levels` |
| `stay_base:misurina:misurina-misurina` | `narrow` | `access_mode`, `atmosphere_tags`, `base_type`, `latitude`, `lift_distance`, `longitude`, `name`, `nearest_lift_distance_m`, `nearest_lift_name`, `price_max`, `price_min`, `price_range`, `quality`, `regional_data_ids`, `stay_base_id`, `supported_skill_levels` |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `narrow` | `access_mode`, `atmosphere_tags`, `base_type`, `latitude`, `lift_distance`, `longitude`, `name`, `nearest_lift_distance_m`, `nearest_lift_name`, `price_max`, `price_min`, `price_range`, `quality`, `regional_data_ids`, `stay_base_id`, `supported_skill_levels` |
| `trust_manifest:destination:auronzo-di-cadore` | `narrow` | `display_name`, `field_statuses`, `notes`, `source_refs` |
| `trust_manifest:destination:cortina-dampezzo` | `narrow` | `field_statuses`, `notes`, `source_refs` |
| `trust_manifest:destination:misurina` | `narrow` | `display_name`, `field_statuses`, `notes`, `source_refs` |
| `trust_manifest:destination:san-vito-di-cadore` | `narrow` | `display_name`, `field_statuses`, `notes`, `source_refs` |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:auronzo-di-cadore` | `base_elevation_m` | `null` | `856` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `country` | `null` | `"Italy"` | `verified_with_adjustment` | no |
| `destination:auronzo-di-cadore` | `latitude` | `null` | `46.5512` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `lift_pass_products[0]` | `null` | `"auronzo-cortina-valle-skipass"` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `lift_pass_products[1]` | `null` | `"auronzo-monte-agudo-skipass"` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `longitude` | `null` | `12.443` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `name` | `null` | `"Auronzo di Cadore"` | `verified_with_adjustment` | no |
| `destination:auronzo-di-cadore` | `price_level` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `region` | `null` | `"Dolomites"` | `verified_with_adjustment` | no |
| `destination:auronzo-di-cadore` | `rentals[0]` | `null` | `"auronzo-di-cadore:monte-agudo-ski-rental"` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `resort_id` | `null` | `"auronzo-di-cadore"` | `verified_with_adjustment` | no |
| `destination:auronzo-di-cadore` | `season_end_month` | `null` | `3` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `season_start_month` | `null` | `12` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `season_windows` | `null` | `[]` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `ski_areas[0]` | `null` | `"auronzo-monte-agudo"` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `stay_bases[0]` | `null` | `"auronzo-di-cadore-auronzo-di-cadore"` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `summit_elevation_m` | `null` | `1585` | `verified_with_adjustment` | yes |
| `destination:auronzo-di-cadore` | `terrain_groups` | `null` | `[]` | `verified_with_adjustment` | no |
| `destination:cortina-dampezzo` | `lift_pass_products[0]` | `null` | `"cortina-valle-skipass"` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `season_end_month` | `4` | `5` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `season_windows[0].end_date` | `null` | `"2027-05-02"` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `season_windows[0].season_label` | `null` | `"2026/2027"` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `season_windows[0].start_date` | `null` | `"2026-11-21"` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `season_windows[0].status` | `null` | `"planned"` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `stay_bases[0]` | `"cortina-dampezzo-cortina-d-ampezzo"` | `null` | `verified_with_adjustment` | yes |
| `destination:cortina-dampezzo` | `stay_bases[1]` | `null` | `"cortina-dampezzo-cortina-dampezzo"` | `verified_with_adjustment` | yes |
| `destination:misurina` | `base_elevation_m` | `null` | `1752` | `verified_with_adjustment` | yes |
| `destination:misurina` | `country` | `null` | `"Italy"` | `verified_with_adjustment` | no |
| `destination:misurina` | `latitude` | `null` | `46.5785` | `verified_with_adjustment` | yes |
| `destination:misurina` | `lift_pass_products[0]` | `null` | `"misurina-cortina-valle-skipass"` | `verified_with_adjustment` | yes |
| `destination:misurina` | `lift_pass_products[1]` | `null` | `"misurina-passo-tre-croci-skipass"` | `verified_with_adjustment` | yes |
| `destination:misurina` | `longitude` | `null` | `12.252` | `verified_with_adjustment` | yes |
| `destination:misurina` | `name` | `null` | `"Misurina"` | `verified_with_adjustment` | no |
| `destination:misurina` | `price_level` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `destination:misurina` | `region` | `null` | `"Dolomites"` | `verified_with_adjustment` | no |
| `destination:misurina` | `rentals[0]` | `null` | `"misurina:misurina-ski-area-rental"` | `verified_with_adjustment` | yes |
| `destination:misurina` | `resort_id` | `null` | `"misurina"` | `verified_with_adjustment` | no |
| `destination:misurina` | `season_end_month` | `null` | `3` | `verified_with_adjustment` | yes |
| `destination:misurina` | `season_start_month` | `null` | `12` | `verified_with_adjustment` | yes |
| `destination:misurina` | `season_windows` | `null` | `[]` | `verified_with_adjustment` | yes |
| `destination:misurina` | `ski_areas[0]` | `null` | `"misurina-passo-tre-croci"` | `verified_with_adjustment` | yes |
| `destination:misurina` | `stay_bases[0]` | `null` | `"misurina-misurina"` | `verified_with_adjustment` | yes |
| `destination:misurina` | `summit_elevation_m` | `null` | `2114` | `verified_with_adjustment` | yes |
| `destination:misurina` | `terrain_groups` | `null` | `[]` | `verified_with_adjustment` | no |
| `destination:san-vito-di-cadore` | `base_elevation_m` | `null` | `1048` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `country` | `null` | `"Italy"` | `verified_with_adjustment` | no |
| `destination:san-vito-di-cadore` | `latitude` | `null` | `46.4764` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `lift_pass_products[0]` | `null` | `"san-vito-cortina-valle-skipass"` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `lift_pass_products[1]` | `null` | `"san-vito-ski-area-skipass"` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `longitude` | `null` | `12.2079` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `name` | `null` | `"San Vito di Cadore"` | `verified_with_adjustment` | no |
| `destination:san-vito-di-cadore` | `price_level` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `region` | `null` | `"Dolomites"` | `verified_with_adjustment` | no |
| `destination:san-vito-di-cadore` | `rentals[0]` | `null` | `"san-vito-di-cadore:san-vito-ski-area-rental"` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `resort_id` | `null` | `"san-vito-di-cadore"` | `verified_with_adjustment` | no |
| `destination:san-vito-di-cadore` | `season_end_month` | `null` | `3` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `season_start_month` | `null` | `12` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `season_windows` | `null` | `[]` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `ski_areas[0]` | `null` | `"san-vito-di-cadore-ski-area"` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `stay_bases[0]` | `null` | `"san-vito-di-cadore-san-vito-di-cadore"` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `summit_elevation_m` | `null` | `1584` | `verified_with_adjustment` | yes |
| `destination:san-vito-di-cadore` | `terrain_groups` | `null` | `[]` | `verified_with_adjustment` | no |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `external_validity_summary` | `null` | `"Also valid in Cortina d'Ampezzo, San Vito di Cadore, and Misurina under the Cortina valley pass; shared ticket validity is pass context, not a ski-connected terrain domain."` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `is_default` | `null` | `false` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `lift_pass_product_id` | `null` | `"auronzo-cortina-valle-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `name` | `null` | `"Valle Skipass Cortina"` | `verified_with_adjustment` | no |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `prices` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `valid_ski_area_ids[0]` | `null` | `"auronzo-monte-agudo"` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `is_default` | `null` | `true` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `lift_pass_product_id` | `null` | `"auronzo-monte-agudo-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `name` | `null` | `"Auronzo di Cadore - Monte Agudo Skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].amount` | `null` | `49.0` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].audience` | `null` | `"adult"` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].currency` | `null` | `"EUR"` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].duration_days` | `null` | `1` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].price_kind` | `null` | `"fixed"` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].season_label` | `null` | `"main season"` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].source_url` | `null` | `"https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/"` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `valid_ski_area_ids[0]` | `null` | `"auronzo-monte-agudo"` | `verified_with_adjustment` | yes |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `external_validity_summary` | `null` | `"Also covers San Vito di Cadore, Auronzo di Cadore, and Misurina under the Cortina valley pass; shared ticket validity is not modeled as a terrain domain because these areas are not represented as ski-connected."` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `is_default` | `null` | `true` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `lift_pass_product_id` | `null` | `"cortina-valle-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `name` | `null` | `"Valle Skipass Cortina"` | `verified_with_adjustment` | no |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].amount` | `null` | `80.0` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].audience` | `null` | `"adult"` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].currency` | `null` | `"EUR"` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].duration_days` | `null` | `1` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].price_kind` | `null` | `"fixed"` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].season_label` | `null` | `"main season"` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].source_url` | `null` | `"https://www.skiresort.info/ski-resort/cortina-dampezzo/"` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `valid_ski_area_ids[0]` | `null` | `"cortina-dampezzo-ski-area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `external_validity_summary` | `null` | `"Also valid in Cortina d'Ampezzo, San Vito di Cadore, and Auronzo di Cadore under the Cortina valley pass; shared ticket validity is pass context, not a ski-connected terrain domain."` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `is_default` | `null` | `false` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `lift_pass_product_id` | `null` | `"misurina-cortina-valle-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `name` | `null` | `"Valle Skipass Cortina"` | `verified_with_adjustment` | no |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `prices` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `valid_ski_area_ids[0]` | `null` | `"misurina-passo-tre-croci"` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `is_default` | `null` | `true` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `lift_pass_product_id` | `null` | `"misurina-passo-tre-croci-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `name` | `null` | `"Misurina - Passo Tre Croci Skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].amount` | `null` | `49.0` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].audience` | `null` | `"adult"` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].currency` | `null` | `"EUR"` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].duration_days` | `null` | `1` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].price_kind` | `null` | `"fixed"` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].season_label` | `null` | `"main season"` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].source_url` | `null` | `"https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/"` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `valid_ski_area_ids[0]` | `null` | `"misurina-passo-tre-croci"` | `verified_with_adjustment` | yes |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `external_validity_summary` | `null` | `"Also valid in Cortina d'Ampezzo, Auronzo di Cadore, and Misurina under the Cortina valley pass; shared ticket validity is pass context, not a ski-connected terrain domain."` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `is_default` | `null` | `false` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `lift_pass_product_id` | `null` | `"san-vito-cortina-valle-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `name` | `null` | `"Valle Skipass Cortina"` | `verified_with_adjustment` | no |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `prices` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `valid_ski_area_ids[0]` | `null` | `"san-vito-di-cadore-ski-area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `is_default` | `null` | `true` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `lift_pass_product_id` | `null` | `"san-vito-ski-area-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `name` | `null` | `"San Vito Ski Area Skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].amount` | `null` | `51.0` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].audience` | `null` | `"adult"` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].currency` | `null` | `"EUR"` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].duration_days` | `null` | `1` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].price_kind` | `null` | `"fixed"` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].season_label` | `null` | `"2025/2026 high season"` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].source_url` | `null` | `"https://www.skiareasanvito.com/en/rates/"` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `valid_ski_area_ids[0]` | `null` | `"san-vito-di-cadore-ski-area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | yes |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `lift_distance` | `null` | `"near"` | `estimated` | yes |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `name` | `null` | `"Monte Agudo ski rental"` | `estimated` | no |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `price_max` | `null` | `55.0` | `estimated` | yes |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `price_min` | `null` | `35.0` | `estimated` | yes |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `price_range` | `null` | `"EUR 35-55"` | `estimated` | yes |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `quality` | `null` | `"standard"` | `estimated` | yes |
| `rental:misurina:misurina-ski-area-rental` | `lift_distance` | `null` | `"near"` | `estimated` | yes |
| `rental:misurina:misurina-ski-area-rental` | `name` | `null` | `"Misurina ski-area rental"` | `estimated` | no |
| `rental:misurina:misurina-ski-area-rental` | `price_max` | `null` | `55.0` | `estimated` | yes |
| `rental:misurina:misurina-ski-area-rental` | `price_min` | `null` | `35.0` | `estimated` | yes |
| `rental:misurina:misurina-ski-area-rental` | `price_range` | `null` | `"EUR 35-55"` | `estimated` | yes |
| `rental:misurina:misurina-ski-area-rental` | `quality` | `null` | `"standard"` | `estimated` | yes |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `lift_distance` | `null` | `"near"` | `estimated` | yes |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `name` | `null` | `"San Vito ski-area rental"` | `estimated` | no |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `price_max` | `null` | `55.0` | `estimated` | yes |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `price_min` | `null` | `35.0` | `estimated` | yes |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `price_range` | `null` | `"EUR 35-55"` | `estimated` | yes |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `quality` | `null` | `"standard"` | `estimated` | yes |
| `ski_area:auronzo-monte-agudo` | `base_elevation_m` | `null` | `856` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `latitude` | `null` | `46.545` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `longitude` | `null` | `12.42` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `name` | `null` | `"Auronzo di Cadore - Monte Agudo"` | `verified_with_adjustment` | no |
| `ski_area:auronzo-monte-agudo` | `piste_km_by_difficulty.advanced` | `null` | `0.7` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `piste_km_by_difficulty.beginner` | `null` | `0.2` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `piste_km_by_difficulty.intermediate` | `null` | `5.2` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `season_end_month` | `null` | `3` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `season_start_month` | `null` | `12` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `season_windows` | `null` | `[]` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `ski_area_id` | `null` | `"auronzo-monte-agudo"` | `verified_with_adjustment` | no |
| `ski_area:auronzo-monte-agudo` | `summit_elevation_m` | `null` | `1585` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `total_lift_count` | `null` | `3` | `verified_with_adjustment` | yes |
| `ski_area:auronzo-monte-agudo` | `total_piste_km` | `null` | `6.1` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `base_elevation_m` | `1224` | `1217` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `season_end_month` | `4` | `5` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `season_start_month` | `12` | `11` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].end_date` | `null` | `"2027-05-02"` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].season_label` | `null` | `"2026/2027"` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].start_date` | `null` | `"2026-11-21"` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].status` | `null` | `"planned"` | `verified_with_adjustment` | yes |
| `ski_area:cortina-dampezzo-ski-area` | `summit_elevation_m` | `2930` | `2828` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `base_elevation_m` | `null` | `1752` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `latitude` | `null` | `46.5723` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `longitude` | `null` | `12.2705` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `name` | `null` | `"Misurina - Passo Tre Croci"` | `verified_with_adjustment` | no |
| `ski_area:misurina-passo-tre-croci` | `piste_km_by_difficulty.advanced` | `null` | `0.5` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `piste_km_by_difficulty.beginner` | `null` | `0.8` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `piste_km_by_difficulty.intermediate` | `null` | `2.9` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `season_end_month` | `null` | `3` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `season_start_month` | `null` | `12` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `season_windows` | `null` | `[]` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `ski_area_id` | `null` | `"misurina-passo-tre-croci"` | `verified_with_adjustment` | no |
| `ski_area:misurina-passo-tre-croci` | `summit_elevation_m` | `null` | `2114` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `total_lift_count` | `null` | `2` | `verified_with_adjustment` | yes |
| `ski_area:misurina-passo-tre-croci` | `total_piste_km` | `null` | `4.2` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `base_elevation_m` | `null` | `1048` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `latitude` | `null` | `46.459` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `longitude` | `null` | `12.2057` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `name` | `null` | `"San Vito di Cadore"` | `verified_with_adjustment` | no |
| `ski_area:san-vito-di-cadore-ski-area` | `piste_km_by_difficulty.advanced` | `null` | `1.0` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `piste_km_by_difficulty.beginner` | `null` | `4.0` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `piste_km_by_difficulty.intermediate` | `null` | `5.0` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `season_end_month` | `null` | `3` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `season_start_month` | `null` | `12` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `season_windows` | `null` | `[]` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `ski_area_id` | `null` | `"san-vito-di-cadore-ski-area"` | `verified_with_adjustment` | no |
| `ski_area:san-vito-di-cadore-ski-area` | `summit_elevation_m` | `null` | `1584` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `total_lift_count` | `null` | `5` | `verified_with_adjustment` | yes |
| `ski_area:san-vito-di-cadore-ski-area` | `total_piste_km` | `null` | `10.0` | `verified_with_adjustment` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `access_mode` | `null` | `"ski_bus"` | `verified_with_adjustment` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `atmosphere_tags[0]` | `null` | `"family"` | `estimated` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `atmosphere_tags[1]` | `null` | `"quiet"` | `estimated` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `atmosphere_tags[2]` | `null` | `"value"` | `estimated` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `base_type` | `null` | `"town"` | `estimated` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `latitude` | `null` | `46.5512` | `verified_with_adjustment` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `lift_distance` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `longitude` | `null` | `12.443` | `verified_with_adjustment` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `name` | `null` | `"Auronzo di Cadore"` | `verified_with_adjustment` | no |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `nearest_lift_distance_m` | `null` | `2100` | `verified_with_adjustment` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `nearest_lift_name` | `null` | `"Taiarezze-Malon Chairlift"` | `verified_with_adjustment` | no |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `price_max` | `null` | `220.0` | `estimated` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `price_min` | `null` | `140.0` | `estimated` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `price_range` | `null` | `"EUR 140-220"` | `estimated` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `quality` | `null` | `"standard"` | `estimated` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `regional_data_ids.osm_relation_id` | `null` | `"47236"` | `verified_with_adjustment` | no |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `stay_base_id` | `null` | `"auronzo-di-cadore-auronzo-di-cadore"` | `verified_with_adjustment` | no |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `supported_skill_levels[0]` | `null` | `"advanced"` | `verified_with_adjustment` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `supported_skill_levels[1]` | `null` | `"beginner"` | `verified_with_adjustment` | yes |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `supported_skill_levels[2]` | `null` | `"intermediate"` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `access_mode` | `"unknown"` | `null` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `atmosphere_tags` | `[]` | `null` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `lift_distance` | `"medium"` | `null` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `name` | `"Cortina d'Ampezzo"` | `null` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `price_max` | `300.0` | `null` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `price_min` | `210.0` | `null` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `price_range` | `"EUR 210-300"` | `null` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `quality` | `"premium"` | `null` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `regional_data_ids` | `{}` | `null` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `stay_base_id` | `"cortina-dampezzo-cortina-d-ampezzo"` | `null` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `supported_skill_levels[0]` | `"advanced"` | `null` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `supported_skill_levels[1]` | `"intermediate"` | `null` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags[0]` | `null` | `"historic"` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags[1]` | `null` | `"premium"` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags[2]` | `null` | `"scenic"` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `base_type` | `null` | `"town"` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `latitude` | `null` | `46.5405` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `longitude` | `null` | `12.1357` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `name` | `null` | `"Cortina d'Ampezzo"` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_distance_m` | `null` | `472` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_name` | `null` | `"Funivia Faloria"` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `price_max` | `null` | `300.0` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `price_min` | `null` | `210.0` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `price_range` | `null` | `"EUR 210-300"` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `quality` | `null` | `"premium"` | `estimated` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `regional_data_ids.osm_relation_id` | `null` | `"47235"` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `stay_base_id` | `null` | `"cortina-dampezzo-cortina-dampezzo"` | `verified_with_adjustment` | no |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `supported_skill_levels[0]` | `null` | `"advanced"` | `verified_with_adjustment` | yes |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `supported_skill_levels[1]` | `null` | `"intermediate"` | `verified_with_adjustment` | yes |
| `stay_base:misurina:misurina-misurina` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:misurina:misurina-misurina` | `atmosphere_tags[0]` | `null` | `"high_altitude"` | `estimated` | yes |
| `stay_base:misurina:misurina-misurina` | `atmosphere_tags[1]` | `null` | `"quiet"` | `estimated` | yes |
| `stay_base:misurina:misurina-misurina` | `atmosphere_tags[2]` | `null` | `"scenic"` | `estimated` | yes |
| `stay_base:misurina:misurina-misurina` | `base_type` | `null` | `"lake_village"` | `estimated` | yes |
| `stay_base:misurina:misurina-misurina` | `latitude` | `null` | `46.5785` | `verified_with_adjustment` | yes |
| `stay_base:misurina:misurina-misurina` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:misurina:misurina-misurina` | `longitude` | `null` | `12.252` | `verified_with_adjustment` | yes |
| `stay_base:misurina:misurina-misurina` | `name` | `null` | `"Misurina"` | `verified_with_adjustment` | no |
| `stay_base:misurina:misurina-misurina` | `nearest_lift_distance_m` | `null` | `900` | `verified_with_adjustment` | yes |
| `stay_base:misurina:misurina-misurina` | `nearest_lift_name` | `null` | `"Col de Varda Chairlift"` | `verified_with_adjustment` | no |
| `stay_base:misurina:misurina-misurina` | `price_max` | `null` | `230.0` | `estimated` | yes |
| `stay_base:misurina:misurina-misurina` | `price_min` | `null` | `150.0` | `estimated` | yes |
| `stay_base:misurina:misurina-misurina` | `price_range` | `null` | `"EUR 150-230"` | `estimated` | yes |
| `stay_base:misurina:misurina-misurina` | `quality` | `null` | `"standard"` | `estimated` | yes |
| `stay_base:misurina:misurina-misurina` | `regional_data_ids.osm_node_id` | `null` | `"1427982374"` | `verified_with_adjustment` | no |
| `stay_base:misurina:misurina-misurina` | `stay_base_id` | `null` | `"misurina-misurina"` | `verified_with_adjustment` | no |
| `stay_base:misurina:misurina-misurina` | `supported_skill_levels[0]` | `null` | `"advanced"` | `verified_with_adjustment` | yes |
| `stay_base:misurina:misurina-misurina` | `supported_skill_levels[1]` | `null` | `"beginner"` | `verified_with_adjustment` | yes |
| `stay_base:misurina:misurina-misurina` | `supported_skill_levels[2]` | `null` | `"intermediate"` | `verified_with_adjustment` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `access_mode` | `null` | `"ski_bus"` | `verified_with_adjustment` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `atmosphere_tags[0]` | `null` | `"family"` | `estimated` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `atmosphere_tags[1]` | `null` | `"quiet"` | `estimated` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `atmosphere_tags[2]` | `null` | `"sunny"` | `estimated` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `base_type` | `null` | `"town"` | `estimated` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `latitude` | `null` | `46.4764` | `verified_with_adjustment` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `longitude` | `null` | `12.2079` | `verified_with_adjustment` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `name` | `null` | `"San Vito di Cadore"` | `verified_with_adjustment` | no |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `nearest_lift_distance_m` | `null` | `800` | `verified_with_adjustment` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `nearest_lift_name` | `null` | `"Tambres Chairlift"` | `verified_with_adjustment` | no |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `price_max` | `null` | `230.0` | `estimated` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `price_min` | `null` | `150.0` | `estimated` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `price_range` | `null` | `"EUR 150-230"` | `estimated` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `quality` | `null` | `"standard"` | `estimated` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `regional_data_ids.osm_relation_id` | `null` | `"47211"` | `verified_with_adjustment` | no |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `stay_base_id` | `null` | `"san-vito-di-cadore-san-vito-di-cadore"` | `verified_with_adjustment` | no |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `supported_skill_levels[0]` | `null` | `"beginner"` | `verified_with_adjustment` | yes |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `supported_skill_levels[1]` | `null` | `"intermediate"` | `verified_with_adjustment` | yes |
| `trust_manifest:destination:auronzo-di-cadore` | `display_name` | `null` | `"Auronzo di Cadore"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.country_region` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.destination_coordinates` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.destination_elevation` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.destination_identity` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.lift_pass_products` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.price_ranges` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.rental_examples` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.rental_quality_tier` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.season_window` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.ski_areas` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.stay_base_lift_distance` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.stay_base_quality_tier` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.stay_bases` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.supported_skill_levels` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.terrain_groups` | `null` | `"needs_source"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `notes[0]` | `null` | `"Modeled as a separate destination from Misurina because Auronzo has its own stay context, Monte Agudo ski access, town/value recommendation profile, and official destination treatment."` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `notes[1]` | `null` | `"Monte Agudo terrain metrics use child-scope reviewed ski-area data that matches the detailed official lift/slope table; broader official narrative says nearly 20 km and remains a scope caveat."` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `notes[2]` | `null` | `"Auronzo/Misurina shared ski-school/operator/pass wording is preserved as linked pass and source context, not used to merge the destinations."` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `notes[3]` | `null` | `"Lodging and rental price ranges, stay-base quality tier, and rental quality tier remain product-curated estimates pending a dedicated sampling policy."` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs[0]` | `null` | `"https://auronzo.info/en/lifts-and-slopes/"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs[1]` | `null` | `"https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs[2]` | `null` | `"https://monteagudo.it/en/auronzo-misurina-ski-area/"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs[3]` | `null` | `"https://www.openstreetmap.org/relation/47236"` | `estimated` | no |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs[4]` | `null` | `"https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/"` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `field_statuses.lift_pass_products` | `"needs_source"` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `field_statuses.rental_examples` | `"estimated"` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `field_statuses.stay_base_lift_distance` | `"estimated"` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `notes[0]` | `"Trust-contract first pass; not a full official-source recuration."` | `"Full destination recuration replaced the internal sprint-note source with official, open-data, and reviewed-editorial source refs."` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `notes[1]` | `"Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands."` | `"San Vito di Cadore, Auronzo di Cadore, and Misurina are modeled as separate destinations; the 120 km Cortina valley pass scope remains pass context and is not copied onto the Cortina child ski-area terrain metrics."` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `notes[2]` | `null` | `"Cortina child ski-area elevations, operating months, future season window, and representative pass price are normalized from reviewed ski-area data; child piste/lift totals remain omitted until accepted Cortina-only scope evidence is available."` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `notes[3]` | `null` | `"Price ranges, stay-base quality tier, supported skill levels, and rental quality tier remain product-curated estimates pending a dedicated price and lodging sampling policy."` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[0]` | `"docs/sprint-17-resort-audit-results.md"` | `null` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[1]` | `null` | `"https://cortina.dolomiti.org/en/winter/plan/lifts/"` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[2]` | `null` | `"https://cortinaprosport.com/en/ski/rental.html"` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[3]` | `null` | `"https://skipasscortina.com/EN/page17-cortina-winter-prices"` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[4]` | `null` | `"https://www.openstreetmap.org/node/606939921"` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[5]` | `null` | `"https://www.openstreetmap.org/relation/47235"` | `estimated` | no |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[6]` | `null` | `"https://www.skiresort.info/ski-resort/cortina-dampezzo/"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `display_name` | `null` | `"Misurina"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.country_region` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.destination_coordinates` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.destination_elevation` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.destination_identity` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.lift_pass_products` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.price_ranges` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.rental_examples` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.rental_quality_tier` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.season_window` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.ski_areas` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.stay_base_lift_distance` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.stay_base_quality_tier` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.stay_bases` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.supported_skill_levels` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `field_statuses.terrain_groups` | `null` | `"needs_source"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `notes[0]` | `null` | `"Modeled separately from Auronzo di Cadore because Misurina has its own lodging base, direct Col de Varda/Loita ski access, high-elevation lake setting, and official destination treatment."` | `estimated` | no |
| `trust_manifest:destination:misurina` | `notes[1]` | `null` | `"Misurina - Passo Tre Croci terrain metrics use reviewed ski-area data for the Misurina child scope; Auronzo/Misurina shared branding remains pass/operator context."` | `estimated` | no |
| `trust_manifest:destination:misurina` | `notes[2]` | `null` | `"The Cortina valley pass is represented as regional-network pass context, not as a ski-connected terrain domain."` | `estimated` | no |
| `trust_manifest:destination:misurina` | `notes[3]` | `null` | `"Lodging and rental price ranges, stay-base quality tier, and rental quality tier remain product-curated estimates pending a dedicated sampling policy."` | `estimated` | no |
| `trust_manifest:destination:misurina` | `source_refs[0]` | `null` | `"https://auronzo.info/en/misurina-dolomites/"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `source_refs[1]` | `null` | `"https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `source_refs[2]` | `null` | `"https://www.openstreetmap.org/node/1427982374"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `source_refs[3]` | `null` | `"https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/"` | `estimated` | no |
| `trust_manifest:destination:misurina` | `source_refs[4]` | `null` | `"https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `display_name` | `null` | `"San Vito di Cadore"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.country_region` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.destination_coordinates` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.destination_elevation` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.destination_identity` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.lift_pass_products` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.price_ranges` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.rental_examples` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.rental_quality_tier` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.season_window` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.ski_areas` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.stay_base_lift_distance` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.stay_base_quality_tier` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.stay_bases` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.supported_skill_levels` | `null` | `"verified_with_adjustment"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.terrain_groups` | `null` | `"needs_source"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `notes[0]` | `null` | `"Modeled as a separate destination because San Vito has independent lodging identity, local lift access, a local-only ski pass, and distinct family/value recommendation value."` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `notes[1]` | `null` | `"The catalog stores child-scope San Vito terrain metrics from reviewed ski-area data; official tourism pages also publish broader 20 km wording, so the conflicting source is preserved as a caveat rather than copied into the child ski-area metrics."` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `notes[2]` | `null` | `"The Cortina valley pass is represented as regional-network pass context, not as a ski-connected terrain domain."` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `notes[3]` | `null` | `"Lodging and rental price ranges, stay-base quality tier, and rental quality tier remain product-curated estimates pending a dedicated sampling policy."` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs[0]` | `null` | `"https://visitcadoredolomiti.com/en/ski-area-san-vito-2/"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs[1]` | `null` | `"https://www.openstreetmap.org/relation/47211"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs[2]` | `null` | `"https://www.skiareasanvito.com/en/rates/"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs[3]` | `null` | `"https://www.skiresort.info/ski-resort/san-vito-di-cadore/"` | `estimated` | no |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs[4]` | `null` | `"https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas"` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `destination:auronzo-di-cadore` | `base_elevation_m` | `changed` |  |
| `destination:auronzo-di-cadore` | `country` | `changed` |  |
| `destination:auronzo-di-cadore` | `latitude` | `changed` |  |
| `destination:auronzo-di-cadore` | `lift_pass_products` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:auronzo-di-cadore` | `lift_pass_products[0]` | `changed` |  |
| `destination:auronzo-di-cadore` | `lift_pass_products[1]` | `changed` |  |
| `destination:auronzo-di-cadore` | `longitude` | `changed` |  |
| `destination:auronzo-di-cadore` | `name` | `changed` |  |
| `destination:auronzo-di-cadore` | `price_level` | `changed` |  |
| `destination:auronzo-di-cadore` | `region` | `changed` |  |
| `destination:auronzo-di-cadore` | `rentals` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:auronzo-di-cadore` | `rentals[0]` | `changed` |  |
| `destination:auronzo-di-cadore` | `resort_id` | `changed` |  |
| `destination:auronzo-di-cadore` | `season_end_month` | `changed` |  |
| `destination:auronzo-di-cadore` | `season_start_month` | `changed` |  |
| `destination:auronzo-di-cadore` | `season_windows` | `changed` |  |
| `destination:auronzo-di-cadore` | `ski_areas` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:auronzo-di-cadore` | `ski_areas[0]` | `changed` |  |
| `destination:auronzo-di-cadore` | `stay_bases` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:auronzo-di-cadore` | `stay_bases[0]` | `changed` |  |
| `destination:auronzo-di-cadore` | `summit_elevation_m` | `changed` |  |
| `destination:auronzo-di-cadore` | `terrain_groups` | `changed` |  |
| `destination:cortina-dampezzo` | `lift_pass_products` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:cortina-dampezzo` | `lift_pass_products[0]` | `changed` |  |
| `destination:cortina-dampezzo` | `name` | `reviewed-no-change` | Boundary identity reviewed against current source set. |
| `destination:cortina-dampezzo` | `season_end_month` | `changed` |  |
| `destination:cortina-dampezzo` | `season_start_month` | `changed` |  |
| `destination:cortina-dampezzo` | `season_windows` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:cortina-dampezzo` | `season_windows[0].end_date` | `changed` |  |
| `destination:cortina-dampezzo` | `season_windows[0].season_label` | `changed` |  |
| `destination:cortina-dampezzo` | `season_windows[0].start_date` | `changed` |  |
| `destination:cortina-dampezzo` | `season_windows[0].status` | `changed` |  |
| `destination:cortina-dampezzo` | `stay_bases` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:cortina-dampezzo` | `stay_bases[0]` | `changed` |  |
| `destination:cortina-dampezzo` | `stay_bases[1]` | `changed` |  |
| `destination:misurina` | `base_elevation_m` | `changed` |  |
| `destination:misurina` | `country` | `changed` |  |
| `destination:misurina` | `latitude` | `changed` |  |
| `destination:misurina` | `lift_pass_products` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:misurina` | `lift_pass_products[0]` | `changed` |  |
| `destination:misurina` | `lift_pass_products[1]` | `changed` |  |
| `destination:misurina` | `longitude` | `changed` |  |
| `destination:misurina` | `name` | `changed` |  |
| `destination:misurina` | `price_level` | `changed` |  |
| `destination:misurina` | `region` | `changed` |  |
| `destination:misurina` | `rentals` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:misurina` | `rentals[0]` | `changed` |  |
| `destination:misurina` | `resort_id` | `changed` |  |
| `destination:misurina` | `season_end_month` | `changed` |  |
| `destination:misurina` | `season_start_month` | `changed` |  |
| `destination:misurina` | `season_windows` | `changed` |  |
| `destination:misurina` | `ski_areas` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:misurina` | `ski_areas[0]` | `changed` |  |
| `destination:misurina` | `stay_bases` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:misurina` | `stay_bases[0]` | `changed` |  |
| `destination:misurina` | `summit_elevation_m` | `changed` |  |
| `destination:misurina` | `terrain_groups` | `changed` |  |
| `destination:san-vito-di-cadore` | `base_elevation_m` | `changed` |  |
| `destination:san-vito-di-cadore` | `country` | `changed` |  |
| `destination:san-vito-di-cadore` | `latitude` | `changed` |  |
| `destination:san-vito-di-cadore` | `lift_pass_products` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:san-vito-di-cadore` | `lift_pass_products[0]` | `changed` |  |
| `destination:san-vito-di-cadore` | `lift_pass_products[1]` | `changed` |  |
| `destination:san-vito-di-cadore` | `longitude` | `changed` |  |
| `destination:san-vito-di-cadore` | `name` | `changed` |  |
| `destination:san-vito-di-cadore` | `price_level` | `changed` |  |
| `destination:san-vito-di-cadore` | `region` | `changed` |  |
| `destination:san-vito-di-cadore` | `rentals` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:san-vito-di-cadore` | `rentals[0]` | `changed` |  |
| `destination:san-vito-di-cadore` | `resort_id` | `changed` |  |
| `destination:san-vito-di-cadore` | `season_end_month` | `changed` |  |
| `destination:san-vito-di-cadore` | `season_start_month` | `changed` |  |
| `destination:san-vito-di-cadore` | `season_windows` | `changed` |  |
| `destination:san-vito-di-cadore` | `ski_areas` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:san-vito-di-cadore` | `ski_areas[0]` | `changed` |  |
| `destination:san-vito-di-cadore` | `stay_bases` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `destination:san-vito-di-cadore` | `stay_bases[0]` | `changed` |  |
| `destination:san-vito-di-cadore` | `summit_elevation_m` | `changed` |  |
| `destination:san-vito-di-cadore` | `terrain_groups` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `is_default` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `name` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `prices` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `valid_ski_area_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `valid_ski_area_ids[0]` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `validity_scope` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `is_default` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `name` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].amount` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].audience` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].currency` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].duration_days` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].price_kind` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].season_label` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].source_url` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `valid_ski_area_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `valid_ski_area_ids[0]` | `changed` |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `validity_scope` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `is_default` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `name` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].amount` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].audience` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].currency` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].duration_days` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].price_kind` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].season_label` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].source_url` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `valid_ski_area_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `valid_ski_area_ids[0]` | `changed` |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `validity_scope` | `changed` |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `is_default` | `changed` |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `name` | `changed` |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `prices` | `changed` |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `valid_ski_area_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `valid_ski_area_ids[0]` | `changed` |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `validity_scope` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `is_default` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `name` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].amount` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].audience` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].currency` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].duration_days` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].price_kind` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].season_label` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].source_url` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `valid_ski_area_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `valid_ski_area_ids[0]` | `changed` |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `validity_scope` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `is_default` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `name` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `prices` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `valid_ski_area_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `valid_ski_area_ids[0]` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `validity_scope` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `is_default` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `name` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].amount` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].audience` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].currency` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].duration_days` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].price_kind` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].season_label` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].source_url` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `valid_ski_area_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `valid_ski_area_ids[0]` | `changed` |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `validity_scope` | `changed` |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `lift_distance` | `changed` |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `name` | `changed` |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `price_max` | `changed` |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `price_min` | `changed` |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `price_range` | `changed` |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `quality` | `changed` |  |
| `rental:misurina:misurina-ski-area-rental` | `lift_distance` | `changed` |  |
| `rental:misurina:misurina-ski-area-rental` | `name` | `changed` |  |
| `rental:misurina:misurina-ski-area-rental` | `price_max` | `changed` |  |
| `rental:misurina:misurina-ski-area-rental` | `price_min` | `changed` |  |
| `rental:misurina:misurina-ski-area-rental` | `price_range` | `changed` |  |
| `rental:misurina:misurina-ski-area-rental` | `quality` | `changed` |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `lift_distance` | `changed` |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `name` | `changed` |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `price_max` | `changed` |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `price_min` | `changed` |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `price_range` | `changed` |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `quality` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `base_elevation_m` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `latitude` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `longitude` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `name` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `season_end_month` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `season_start_month` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `season_windows` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `ski_area_id` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `summit_elevation_m` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `total_lift_count` | `changed` |  |
| `ski_area:auronzo-monte-agudo` | `total_piste_km` | `changed` |  |
| `ski_area:cortina-dampezzo-ski-area` | `base_elevation_m` | `changed` |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_end_month` | `changed` |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].end_date` | `changed` |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].season_label` | `changed` |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].start_date` | `changed` |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].status` | `changed` |  |
| `ski_area:cortina-dampezzo-ski-area` | `summit_elevation_m` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `base_elevation_m` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `latitude` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `longitude` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `name` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `season_end_month` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `season_start_month` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `season_windows` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `ski_area_id` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `summit_elevation_m` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `total_lift_count` | `changed` |  |
| `ski_area:misurina-passo-tre-croci` | `total_piste_km` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `base_elevation_m` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `latitude` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `longitude` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `name` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `season_end_month` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `season_windows` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `summit_elevation_m` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:san-vito-di-cadore-ski-area` | `total_piste_km` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `access_mode` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `atmosphere_tags` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `atmosphere_tags[0]` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `atmosphere_tags[1]` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `atmosphere_tags[2]` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `base_type` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `latitude` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `lift_distance` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `longitude` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `name` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `nearest_lift_distance_m` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `nearest_lift_name` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `price_max` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `price_min` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `price_range` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `quality` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `regional_data_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `regional_data_ids.osm_relation_id` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `stay_base_id` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `supported_skill_levels` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `supported_skill_levels[0]` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `supported_skill_levels[1]` | `changed` |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `supported_skill_levels[2]` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `access_mode` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `atmosphere_tags` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `lift_distance` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `name` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `price_max` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `price_min` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `price_range` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `quality` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `regional_data_ids` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `stay_base_id` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `supported_skill_levels` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `supported_skill_levels[0]` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `supported_skill_levels[1]` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `access_mode` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags[0]` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags[1]` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags[2]` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `base_type` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `latitude` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `lift_distance` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `longitude` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `name` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_distance_m` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_name` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `price_max` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `price_min` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `price_range` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `quality` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `regional_data_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `regional_data_ids.osm_relation_id` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `stay_base_id` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `supported_skill_levels` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `supported_skill_levels[0]` | `changed` |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `supported_skill_levels[1]` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `access_mode` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `atmosphere_tags` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:misurina:misurina-misurina` | `atmosphere_tags[0]` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `atmosphere_tags[1]` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `atmosphere_tags[2]` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `base_type` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `latitude` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `lift_distance` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `longitude` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `name` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `nearest_lift_distance_m` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `nearest_lift_name` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `price_max` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `price_min` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `price_range` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `quality` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `regional_data_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:misurina:misurina-misurina` | `regional_data_ids.osm_node_id` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `stay_base_id` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `supported_skill_levels` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:misurina:misurina-misurina` | `supported_skill_levels[0]` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `supported_skill_levels[1]` | `changed` |  |
| `stay_base:misurina:misurina-misurina` | `supported_skill_levels[2]` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `access_mode` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `atmosphere_tags` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `atmosphere_tags[0]` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `atmosphere_tags[1]` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `atmosphere_tags[2]` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `base_type` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `latitude` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `lift_distance` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `longitude` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `name` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `nearest_lift_distance_m` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `nearest_lift_name` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `price_max` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `price_min` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `price_range` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `quality` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `regional_data_ids` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `regional_data_ids.osm_relation_id` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `stay_base_id` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `supported_skill_levels` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `supported_skill_levels[0]` | `changed` |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `supported_skill_levels[1]` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `display_name` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.country_region` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.destination_coordinates` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.destination_elevation` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.destination_identity` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.lift_pass_products` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.price_ranges` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.rental_examples` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.rental_quality_tier` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.season_window` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.ski_areas` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.stay_base_lift_distance` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.stay_base_quality_tier` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.stay_bases` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.supported_skill_levels` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `field_statuses.terrain_groups` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `notes` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:auronzo-di-cadore` | `notes[0]` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `notes[1]` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `notes[2]` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `notes[3]` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs[0]` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs[1]` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs[2]` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs[3]` | `changed` |  |
| `trust_manifest:destination:auronzo-di-cadore` | `source_refs[4]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `field_statuses` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:cortina-dampezzo` | `field_statuses.lift_pass_products` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `field_statuses.rental_examples` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `field_statuses.stay_base_lift_distance` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `notes` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:cortina-dampezzo` | `notes[0]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `notes[1]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `notes[2]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `notes[3]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[0]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[1]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[2]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[3]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[4]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[5]` | `changed` |  |
| `trust_manifest:destination:cortina-dampezzo` | `source_refs[6]` | `changed` |  |
| `trust_manifest:destination:misurina` | `display_name` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:misurina` | `field_statuses.country_region` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.destination_coordinates` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.destination_elevation` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.destination_identity` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.lift_pass_products` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.price_ranges` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.rental_examples` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.rental_quality_tier` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.season_window` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.ski_areas` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.stay_base_lift_distance` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.stay_base_quality_tier` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.stay_bases` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.supported_skill_levels` | `changed` |  |
| `trust_manifest:destination:misurina` | `field_statuses.terrain_groups` | `changed` |  |
| `trust_manifest:destination:misurina` | `notes` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:misurina` | `notes[0]` | `changed` |  |
| `trust_manifest:destination:misurina` | `notes[1]` | `changed` |  |
| `trust_manifest:destination:misurina` | `notes[2]` | `changed` |  |
| `trust_manifest:destination:misurina` | `notes[3]` | `changed` |  |
| `trust_manifest:destination:misurina` | `source_refs` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:misurina` | `source_refs[0]` | `changed` |  |
| `trust_manifest:destination:misurina` | `source_refs[1]` | `changed` |  |
| `trust_manifest:destination:misurina` | `source_refs[2]` | `changed` |  |
| `trust_manifest:destination:misurina` | `source_refs[3]` | `changed` |  |
| `trust_manifest:destination:misurina` | `source_refs[4]` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `display_name` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.country_region` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.destination_coordinates` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.destination_elevation` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.destination_identity` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.lift_pass_products` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.price_ranges` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.rental_examples` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.rental_quality_tier` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.season_window` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.ski_areas` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.stay_base_lift_distance` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.stay_base_quality_tier` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.stay_bases` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.supported_skill_levels` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `field_statuses.terrain_groups` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `notes` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:san-vito-di-cadore` | `notes[0]` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `notes[1]` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `notes[2]` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `notes[3]` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs` | `reviewed-no-change` | Canonical field reviewed through nested changed leaves. |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs[0]` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs[1]` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs[2]` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs[3]` | `changed` |  |
| `trust_manifest:destination:san-vito-di-cadore` | `source_refs[4]` | `changed` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization | Boundary Targets |
| --- | --- | --- | --- | --- | --- | --- |
| `destination:auronzo-di-cadore` | `base_elevation_m` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `856` | Reviewed source supports the normalized `base_elevation_m` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `country` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"Italy"` | Reviewed source supports the normalized `country` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `latitude` | [OpenStreetMap Auronzo di Cadore relation](https://www.openstreetmap.org/relation/47236) | `46.5512` | Reviewed source supports the normalized `latitude` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `lift_pass_products[0]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"auronzo-cortina-valle-skipass"` | Reviewed source supports the normalized `lift_pass_products[0]` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `lift_pass_products[1]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"auronzo-monte-agudo-skipass"` | Reviewed source supports the normalized `lift_pass_products[1]` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `longitude` | [OpenStreetMap Auronzo di Cadore relation](https://www.openstreetmap.org/relation/47236) | `12.443` | Reviewed source supports the normalized `longitude` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `name` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"Auronzo di Cadore"` | Reviewed source supports the normalized `name` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `price_level` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"medium"` | Reviewed source supports the normalized `price_level` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `region` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"Dolomites"` | Reviewed source supports the normalized `region` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `rentals[0]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"auronzo-di-cadore:monte-agudo-ski-rental"` | Reviewed source supports the normalized `rentals[0]` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `resort_id` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"auronzo-di-cadore"` | Reviewed source supports the normalized `resort_id` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `season_end_month` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `3` | Reviewed source supports the normalized `season_end_month` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `season_start_month` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `12` | Reviewed source supports the normalized `season_start_month` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `season_windows` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `[]` | Reviewed source supports the normalized `season_windows` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `ski_areas[0]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"auronzo-monte-agudo"` | Reviewed source supports the normalized `ski_areas[0]` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `stay_bases[0]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"auronzo-di-cadore-auronzo-di-cadore"` | Reviewed source supports the normalized `stay_bases[0]` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `summit_elevation_m` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `1585` | Reviewed source supports the normalized `summit_elevation_m` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `terrain_groups` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `[]` | Reviewed source supports the normalized `terrain_groups` value for `auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `auronzo-di-cadore` |
| `destination:cortina-dampezzo` | `lift_pass_products[0]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"cortina-valle-skipass"` | Reviewed source supports the normalized `lift_pass_products[0]` value for `cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `cortina-dampezzo` |
| `destination:cortina-dampezzo` | `season_end_month` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `5` | Reviewed source supports the normalized `season_end_month` value for `cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `cortina-dampezzo` |
| `destination:cortina-dampezzo` | `season_start_month` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `11` | Reviewed source supports the normalized `season_start_month` value for `cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `cortina-dampezzo` |
| `destination:cortina-dampezzo` | `season_windows[0].end_date` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"2027-05-02"` | Reviewed source supports the normalized `season_windows[0].end_date` value for `cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `cortina-dampezzo` |
| `destination:cortina-dampezzo` | `season_windows[0].season_label` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"2026/2027"` | Reviewed source supports the normalized `season_windows[0].season_label` value for `cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `cortina-dampezzo` |
| `destination:cortina-dampezzo` | `season_windows[0].start_date` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"2026-11-21"` | Reviewed source supports the normalized `season_windows[0].start_date` value for `cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `cortina-dampezzo` |
| `destination:cortina-dampezzo` | `season_windows[0].status` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"planned"` | Reviewed source supports the normalized `season_windows[0].status` value for `cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `cortina-dampezzo` |
| `destination:cortina-dampezzo` | `stay_bases[0]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `stay_bases[0]` value for `cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `cortina-dampezzo` |
| `destination:cortina-dampezzo` | `stay_bases[1]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"cortina-dampezzo-cortina-dampezzo"` | Reviewed source supports the normalized `stay_bases[1]` value for `cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `cortina-dampezzo` |
| `destination:misurina` | `base_elevation_m` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `1752` | Reviewed source supports the normalized `base_elevation_m` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `country` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"Italy"` | Reviewed source supports the normalized `country` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `latitude` | [OpenStreetMap Misurina node](https://www.openstreetmap.org/node/1427982374) | `46.5785` | Reviewed source supports the normalized `latitude` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `lift_pass_products[0]` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"misurina-cortina-valle-skipass"` | Reviewed source supports the normalized `lift_pass_products[0]` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `lift_pass_products[1]` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"misurina-passo-tre-croci-skipass"` | Reviewed source supports the normalized `lift_pass_products[1]` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `longitude` | [OpenStreetMap Misurina node](https://www.openstreetmap.org/node/1427982374) | `12.252` | Reviewed source supports the normalized `longitude` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `name` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"Misurina"` | Reviewed source supports the normalized `name` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `price_level` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"medium"` | Reviewed source supports the normalized `price_level` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `region` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"Dolomites"` | Reviewed source supports the normalized `region` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `rentals[0]` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"misurina:misurina-ski-area-rental"` | Reviewed source supports the normalized `rentals[0]` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `resort_id` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"misurina"` | Reviewed source supports the normalized `resort_id` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `season_end_month` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `3` | Reviewed source supports the normalized `season_end_month` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `season_start_month` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `12` | Reviewed source supports the normalized `season_start_month` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `season_windows` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `[]` | Reviewed source supports the normalized `season_windows` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `ski_areas[0]` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"misurina-passo-tre-croci"` | Reviewed source supports the normalized `ski_areas[0]` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `stay_bases[0]` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"misurina-misurina"` | Reviewed source supports the normalized `stay_bases[0]` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `summit_elevation_m` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `2114` | Reviewed source supports the normalized `summit_elevation_m` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:misurina` | `terrain_groups` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `[]` | Reviewed source supports the normalized `terrain_groups` value for `misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `misurina` |
| `destination:san-vito-di-cadore` | `base_elevation_m` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `1048` | Reviewed source supports the normalized `base_elevation_m` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `country` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"Italy"` | Reviewed source supports the normalized `country` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `latitude` | [OpenStreetMap San Vito di Cadore relation](https://www.openstreetmap.org/relation/47211) | `46.4764` | Reviewed source supports the normalized `latitude` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `lift_pass_products[0]` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"san-vito-cortina-valle-skipass"` | Reviewed source supports the normalized `lift_pass_products[0]` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `lift_pass_products[1]` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"san-vito-ski-area-skipass"` | Reviewed source supports the normalized `lift_pass_products[1]` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `longitude` | [OpenStreetMap San Vito di Cadore relation](https://www.openstreetmap.org/relation/47211) | `12.2079` | Reviewed source supports the normalized `longitude` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `name` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"San Vito di Cadore"` | Reviewed source supports the normalized `name` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `price_level` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"medium"` | Reviewed source supports the normalized `price_level` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `region` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"Dolomites"` | Reviewed source supports the normalized `region` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `rentals[0]` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"san-vito-di-cadore:san-vito-ski-area-rental"` | Reviewed source supports the normalized `rentals[0]` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `resort_id` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"san-vito-di-cadore"` | Reviewed source supports the normalized `resort_id` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `season_end_month` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `3` | Reviewed source supports the normalized `season_end_month` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `season_start_month` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `12` | Reviewed source supports the normalized `season_start_month` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `season_windows` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `[]` | Reviewed source supports the normalized `season_windows` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `ski_areas[0]` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"san-vito-di-cadore-ski-area"` | Reviewed source supports the normalized `ski_areas[0]` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `stay_bases[0]` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"san-vito-di-cadore-san-vito-di-cadore"` | Reviewed source supports the normalized `stay_bases[0]` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `summit_elevation_m` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `1584` | Reviewed source supports the normalized `summit_elevation_m` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `terrain_groups` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `[]` | Reviewed source supports the normalized `terrain_groups` value for `san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. | `san-vito-di-cadore` |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `external_validity_summary` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"Also valid in Cortina d'Ampezzo, San Vito di Cadore, and Misurina under the Cortina valley pass; shared ticket validity is pass context, not a ski-connected terrain domain."` | Reviewed source supports the normalized `external_validity_summary` value for `auronzo-di-cadore:auronzo-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `is_default` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `false` | Reviewed source supports the normalized `is_default` value for `auronzo-di-cadore:auronzo-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `lift_pass_product_id` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"auronzo-cortina-valle-skipass"` | Reviewed source supports the normalized `lift_pass_product_id` value for `auronzo-di-cadore:auronzo-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `name` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"Valle Skipass Cortina"` | Reviewed source supports the normalized `name` value for `auronzo-di-cadore:auronzo-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `prices` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `[]` | Reviewed source supports the normalized `prices` value for `auronzo-di-cadore:auronzo-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `terrain_domain_ids` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `[]` | Reviewed source supports the normalized `terrain_domain_ids` value for `auronzo-di-cadore:auronzo-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `valid_ski_area_ids[0]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"auronzo-monte-agudo"` | Reviewed source supports the normalized `valid_ski_area_ids[0]` value for `auronzo-di-cadore:auronzo-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-cortina-valle-skipass` | `validity_scope` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"regional_network"` | Reviewed source supports the normalized `validity_scope` value for `auronzo-di-cadore:auronzo-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `is_default` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `true` | Reviewed source supports the normalized `is_default` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `lift_pass_product_id` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"auronzo-monte-agudo-skipass"` | Reviewed source supports the normalized `lift_pass_product_id` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `name` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"Auronzo di Cadore - Monte Agudo Skipass"` | Reviewed source supports the normalized `name` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].amount` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `49.0` | Reviewed source supports the normalized `prices[0].amount` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].audience` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"adult"` | Reviewed source supports the normalized `prices[0].audience` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].currency` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"EUR"` | Reviewed source supports the normalized `prices[0].currency` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].duration_days` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `1` | Reviewed source supports the normalized `prices[0].duration_days` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].price_kind` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"fixed"` | Reviewed source supports the normalized `prices[0].price_kind` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].season_label` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"main season"` | Reviewed source supports the normalized `prices[0].season_label` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `prices[0].source_url` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/"` | Reviewed source supports the normalized `prices[0].source_url` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `terrain_domain_ids` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `[]` | Reviewed source supports the normalized `terrain_domain_ids` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `valid_ski_area_ids[0]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"auronzo-monte-agudo"` | Reviewed source supports the normalized `valid_ski_area_ids[0]` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:auronzo-di-cadore:auronzo-monte-agudo-skipass` | `validity_scope` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"single_ski_area"` | Reviewed source supports the normalized `validity_scope` value for `auronzo-di-cadore:auronzo-monte-agudo-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `external_validity_summary` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"Also covers San Vito di Cadore, Auronzo di Cadore, and Misurina under the Cortina valley pass; shared ticket validity is not modeled as a terrain domain because these areas are not represented as ski-connected."` | Reviewed source supports the normalized `external_validity_summary` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `is_default` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `true` | Reviewed source supports the normalized `is_default` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `lift_pass_product_id` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"cortina-valle-skipass"` | Reviewed source supports the normalized `lift_pass_product_id` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `name` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"Valle Skipass Cortina"` | Reviewed source supports the normalized `name` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].amount` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `80.0` | Reviewed source supports the normalized `prices[0].amount` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].audience` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"adult"` | Reviewed source supports the normalized `prices[0].audience` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].currency` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"EUR"` | Reviewed source supports the normalized `prices[0].currency` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].duration_days` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `1` | Reviewed source supports the normalized `prices[0].duration_days` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].price_kind` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"fixed"` | Reviewed source supports the normalized `prices[0].price_kind` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].season_label` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"main season"` | Reviewed source supports the normalized `prices[0].season_label` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `prices[0].source_url` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"https://www.skiresort.info/ski-resort/cortina-dampezzo/"` | Reviewed source supports the normalized `prices[0].source_url` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `terrain_domain_ids` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `[]` | Reviewed source supports the normalized `terrain_domain_ids` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `valid_ski_area_ids[0]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"cortina-dampezzo-ski-area"` | Reviewed source supports the normalized `valid_ski_area_ids[0]` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:cortina-dampezzo:cortina-valle-skipass` | `validity_scope` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"regional_network"` | Reviewed source supports the normalized `validity_scope` value for `cortina-dampezzo:cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `external_validity_summary` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"Also valid in Cortina d'Ampezzo, San Vito di Cadore, and Auronzo di Cadore under the Cortina valley pass; shared ticket validity is pass context, not a ski-connected terrain domain."` | Reviewed source supports the normalized `external_validity_summary` value for `misurina:misurina-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `is_default` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `false` | Reviewed source supports the normalized `is_default` value for `misurina:misurina-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `lift_pass_product_id` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"misurina-cortina-valle-skipass"` | Reviewed source supports the normalized `lift_pass_product_id` value for `misurina:misurina-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `name` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"Valle Skipass Cortina"` | Reviewed source supports the normalized `name` value for `misurina:misurina-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `prices` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `[]` | Reviewed source supports the normalized `prices` value for `misurina:misurina-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `terrain_domain_ids` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `[]` | Reviewed source supports the normalized `terrain_domain_ids` value for `misurina:misurina-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `valid_ski_area_ids[0]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"misurina-passo-tre-croci"` | Reviewed source supports the normalized `valid_ski_area_ids[0]` value for `misurina:misurina-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-cortina-valle-skipass` | `validity_scope` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"regional_network"` | Reviewed source supports the normalized `validity_scope` value for `misurina:misurina-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `is_default` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `true` | Reviewed source supports the normalized `is_default` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `lift_pass_product_id` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"misurina-passo-tre-croci-skipass"` | Reviewed source supports the normalized `lift_pass_product_id` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `name` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"Misurina - Passo Tre Croci Skipass"` | Reviewed source supports the normalized `name` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].amount` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `49.0` | Reviewed source supports the normalized `prices[0].amount` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].audience` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"adult"` | Reviewed source supports the normalized `prices[0].audience` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].currency` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"EUR"` | Reviewed source supports the normalized `prices[0].currency` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].duration_days` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `1` | Reviewed source supports the normalized `prices[0].duration_days` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].price_kind` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"fixed"` | Reviewed source supports the normalized `prices[0].price_kind` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].season_label` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"main season"` | Reviewed source supports the normalized `prices[0].season_label` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `prices[0].source_url` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/"` | Reviewed source supports the normalized `prices[0].source_url` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `terrain_domain_ids` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `[]` | Reviewed source supports the normalized `terrain_domain_ids` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `valid_ski_area_ids[0]` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"misurina-passo-tre-croci"` | Reviewed source supports the normalized `valid_ski_area_ids[0]` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:misurina:misurina-passo-tre-croci-skipass` | `validity_scope` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"single_ski_area"` | Reviewed source supports the normalized `validity_scope` value for `misurina:misurina-passo-tre-croci-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `external_validity_summary` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"Also valid in Cortina d'Ampezzo, Auronzo di Cadore, and Misurina under the Cortina valley pass; shared ticket validity is pass context, not a ski-connected terrain domain."` | Reviewed source supports the normalized `external_validity_summary` value for `san-vito-di-cadore:san-vito-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `is_default` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `false` | Reviewed source supports the normalized `is_default` value for `san-vito-di-cadore:san-vito-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `lift_pass_product_id` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"san-vito-cortina-valle-skipass"` | Reviewed source supports the normalized `lift_pass_product_id` value for `san-vito-di-cadore:san-vito-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `name` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"Valle Skipass Cortina"` | Reviewed source supports the normalized `name` value for `san-vito-di-cadore:san-vito-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `prices` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `[]` | Reviewed source supports the normalized `prices` value for `san-vito-di-cadore:san-vito-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `terrain_domain_ids` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `[]` | Reviewed source supports the normalized `terrain_domain_ids` value for `san-vito-di-cadore:san-vito-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `valid_ski_area_ids[0]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"san-vito-di-cadore-ski-area"` | Reviewed source supports the normalized `valid_ski_area_ids[0]` value for `san-vito-di-cadore:san-vito-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-cortina-valle-skipass` | `validity_scope` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"regional_network"` | Reviewed source supports the normalized `validity_scope` value for `san-vito-di-cadore:san-vito-cortina-valle-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `is_default` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `true` | Reviewed source supports the normalized `is_default` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `lift_pass_product_id` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"san-vito-ski-area-skipass"` | Reviewed source supports the normalized `lift_pass_product_id` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `name` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"San Vito Ski Area Skipass"` | Reviewed source supports the normalized `name` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].amount` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `51.0` | Reviewed source supports the normalized `prices[0].amount` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].audience` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"adult"` | Reviewed source supports the normalized `prices[0].audience` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].currency` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"EUR"` | Reviewed source supports the normalized `prices[0].currency` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].duration_days` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `1` | Reviewed source supports the normalized `prices[0].duration_days` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].price_kind` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"fixed"` | Reviewed source supports the normalized `prices[0].price_kind` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].season_label` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"2025/2026 high season"` | Reviewed source supports the normalized `prices[0].season_label` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `prices[0].source_url` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"https://www.skiareasanvito.com/en/rates/"` | Reviewed source supports the normalized `prices[0].source_url` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `terrain_domain_ids` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `[]` | Reviewed source supports the normalized `terrain_domain_ids` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `valid_ski_area_ids[0]` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"san-vito-di-cadore-ski-area"` | Reviewed source supports the normalized `valid_ski_area_ids[0]` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `lift_pass_product:san-vito-di-cadore:san-vito-ski-area-skipass` | `validity_scope` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"single_ski_area"` | Reviewed source supports the normalized `validity_scope` value for `san-vito-di-cadore:san-vito-ski-area-skipass`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `lift_distance` | [Monte Agudo Auronzo Misurina ski area](https://monteagudo.it/en/auronzo-misurina-ski-area/) | `"near"` | Reviewed source supports the normalized `lift_distance` value for `auronzo-di-cadore:monte-agudo-ski-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `name` | [Monte Agudo Auronzo Misurina ski area](https://monteagudo.it/en/auronzo-misurina-ski-area/) | `"Monte Agudo ski rental"` | Reviewed source supports the normalized `name` value for `auronzo-di-cadore:monte-agudo-ski-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `price_max` | [Monte Agudo Auronzo Misurina ski area](https://monteagudo.it/en/auronzo-misurina-ski-area/) | `55.0` | Reviewed source supports the normalized `price_max` value for `auronzo-di-cadore:monte-agudo-ski-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `price_min` | [Monte Agudo Auronzo Misurina ski area](https://monteagudo.it/en/auronzo-misurina-ski-area/) | `35.0` | Reviewed source supports the normalized `price_min` value for `auronzo-di-cadore:monte-agudo-ski-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `price_range` | [Monte Agudo Auronzo Misurina ski area](https://monteagudo.it/en/auronzo-misurina-ski-area/) | `"EUR 35-55"` | Reviewed source supports the normalized `price_range` value for `auronzo-di-cadore:monte-agudo-ski-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:auronzo-di-cadore:monte-agudo-ski-rental` | `quality` | [Monte Agudo Auronzo Misurina ski area](https://monteagudo.it/en/auronzo-misurina-ski-area/) | `"standard"` | Reviewed source supports the normalized `quality` value for `auronzo-di-cadore:monte-agudo-ski-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:misurina:misurina-ski-area-rental` | `lift_distance` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"near"` | Reviewed source supports the normalized `lift_distance` value for `misurina:misurina-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:misurina:misurina-ski-area-rental` | `name` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"Misurina ski-area rental"` | Reviewed source supports the normalized `name` value for `misurina:misurina-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:misurina:misurina-ski-area-rental` | `price_max` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `55.0` | Reviewed source supports the normalized `price_max` value for `misurina:misurina-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:misurina:misurina-ski-area-rental` | `price_min` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `35.0` | Reviewed source supports the normalized `price_min` value for `misurina:misurina-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:misurina:misurina-ski-area-rental` | `price_range` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"EUR 35-55"` | Reviewed source supports the normalized `price_range` value for `misurina:misurina-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:misurina:misurina-ski-area-rental` | `quality` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"standard"` | Reviewed source supports the normalized `quality` value for `misurina:misurina-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `lift_distance` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"near"` | Reviewed source supports the normalized `lift_distance` value for `san-vito-di-cadore:san-vito-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `name` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"San Vito ski-area rental"` | Reviewed source supports the normalized `name` value for `san-vito-di-cadore:san-vito-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `price_max` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `55.0` | Reviewed source supports the normalized `price_max` value for `san-vito-di-cadore:san-vito-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `price_min` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `35.0` | Reviewed source supports the normalized `price_min` value for `san-vito-di-cadore:san-vito-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `price_range` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"EUR 35-55"` | Reviewed source supports the normalized `price_range` value for `san-vito-di-cadore:san-vito-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `rental:san-vito-di-cadore:san-vito-ski-area-rental` | `quality` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"standard"` | Reviewed source supports the normalized `quality` value for `san-vito-di-cadore:san-vito-ski-area-rental`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `base_elevation_m` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `856` | Reviewed source supports the normalized `base_elevation_m` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `latitude` | [OpenStreetMap Auronzo di Cadore relation](https://www.openstreetmap.org/relation/47236) | `46.545` | Reviewed source supports the normalized `latitude` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `longitude` | [OpenStreetMap Auronzo di Cadore relation](https://www.openstreetmap.org/relation/47236) | `12.42` | Reviewed source supports the normalized `longitude` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `name` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `"Auronzo di Cadore - Monte Agudo"` | Reviewed source supports the normalized `name` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `piste_km_by_difficulty.advanced` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `0.7` | Reviewed source supports the normalized `piste_km_by_difficulty.advanced` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `piste_km_by_difficulty.beginner` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `0.2` | Reviewed source supports the normalized `piste_km_by_difficulty.beginner` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `piste_km_by_difficulty.intermediate` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `5.2` | Reviewed source supports the normalized `piste_km_by_difficulty.intermediate` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `season_end_month` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `3` | Reviewed source supports the normalized `season_end_month` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `season_start_month` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `12` | Reviewed source supports the normalized `season_start_month` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `season_windows` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `[]` | Reviewed source supports the normalized `season_windows` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `ski_area_id` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `"auronzo-monte-agudo"` | Reviewed source supports the normalized `ski_area_id` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `summit_elevation_m` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `1585` | Reviewed source supports the normalized `summit_elevation_m` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `total_lift_count` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `3` | Reviewed source supports the normalized `total_lift_count` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:auronzo-monte-agudo` | `total_piste_km` | [Skiresort.info Auronzo di Cadore - Monte Agudo](https://www.skiresort.info/ski-resort/auronzo-di-cadore-monte-agudo/) | `6.1` | Reviewed source supports the normalized `total_piste_km` value for `auronzo-monte-agudo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:cortina-dampezzo-ski-area` | `base_elevation_m` | [Skiresort.info Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `1217` | Reviewed source supports the normalized `base_elevation_m` value for `cortina-dampezzo-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_end_month` | [Skiresort.info Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `5` | Reviewed source supports the normalized `season_end_month` value for `cortina-dampezzo-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_start_month` | [Skiresort.info Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `11` | Reviewed source supports the normalized `season_start_month` value for `cortina-dampezzo-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].end_date` | [Skiresort.info Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `"2027-05-02"` | Reviewed source supports the normalized `season_windows[0].end_date` value for `cortina-dampezzo-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].season_label` | [Skiresort.info Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `"2026/2027"` | Reviewed source supports the normalized `season_windows[0].season_label` value for `cortina-dampezzo-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].start_date` | [Skiresort.info Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `"2026-11-21"` | Reviewed source supports the normalized `season_windows[0].start_date` value for `cortina-dampezzo-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:cortina-dampezzo-ski-area` | `season_windows[0].status` | [Skiresort.info Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `"planned"` | Reviewed source supports the normalized `season_windows[0].status` value for `cortina-dampezzo-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:cortina-dampezzo-ski-area` | `summit_elevation_m` | [Skiresort.info Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `2828` | Reviewed source supports the normalized `summit_elevation_m` value for `cortina-dampezzo-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `base_elevation_m` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `1752` | Reviewed source supports the normalized `base_elevation_m` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `latitude` | [OpenStreetMap Misurina node](https://www.openstreetmap.org/node/1427982374) | `46.5723` | Reviewed source supports the normalized `latitude` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `longitude` | [OpenStreetMap Misurina node](https://www.openstreetmap.org/node/1427982374) | `12.2705` | Reviewed source supports the normalized `longitude` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `name` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `"Misurina - Passo Tre Croci"` | Reviewed source supports the normalized `name` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `piste_km_by_difficulty.advanced` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `0.5` | Reviewed source supports the normalized `piste_km_by_difficulty.advanced` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `piste_km_by_difficulty.beginner` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `0.8` | Reviewed source supports the normalized `piste_km_by_difficulty.beginner` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `piste_km_by_difficulty.intermediate` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `2.9` | Reviewed source supports the normalized `piste_km_by_difficulty.intermediate` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `season_end_month` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `3` | Reviewed source supports the normalized `season_end_month` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `season_start_month` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `12` | Reviewed source supports the normalized `season_start_month` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `season_windows` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `[]` | Reviewed source supports the normalized `season_windows` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `ski_area_id` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `"misurina-passo-tre-croci"` | Reviewed source supports the normalized `ski_area_id` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `summit_elevation_m` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `2114` | Reviewed source supports the normalized `summit_elevation_m` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `total_lift_count` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `2` | Reviewed source supports the normalized `total_lift_count` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:misurina-passo-tre-croci` | `total_piste_km` | [Skiresort.info Misurina - Passo Tre Croci](https://www.skiresort.info/ski-resort/misurina-passo-tre-croci/) | `4.2` | Reviewed source supports the normalized `total_piste_km` value for `misurina-passo-tre-croci`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `base_elevation_m` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `1048` | Reviewed source supports the normalized `base_elevation_m` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `latitude` | [OpenStreetMap San Vito di Cadore relation](https://www.openstreetmap.org/relation/47211) | `46.459` | Reviewed source supports the normalized `latitude` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `longitude` | [OpenStreetMap San Vito di Cadore relation](https://www.openstreetmap.org/relation/47211) | `12.2057` | Reviewed source supports the normalized `longitude` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `name` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `"San Vito di Cadore"` | Reviewed source supports the normalized `name` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `piste_km_by_difficulty.advanced` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `1.0` | Reviewed source supports the normalized `piste_km_by_difficulty.advanced` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `piste_km_by_difficulty.beginner` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `4.0` | Reviewed source supports the normalized `piste_km_by_difficulty.beginner` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `piste_km_by_difficulty.intermediate` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `5.0` | Reviewed source supports the normalized `piste_km_by_difficulty.intermediate` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `season_end_month` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `3` | Reviewed source supports the normalized `season_end_month` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `season_start_month` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `12` | Reviewed source supports the normalized `season_start_month` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `season_windows` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `[]` | Reviewed source supports the normalized `season_windows` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `ski_area_id` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `"san-vito-di-cadore-ski-area"` | Reviewed source supports the normalized `ski_area_id` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `summit_elevation_m` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `1584` | Reviewed source supports the normalized `summit_elevation_m` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `total_lift_count` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `5` | Reviewed source supports the normalized `total_lift_count` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `ski_area:san-vito-di-cadore-ski-area` | `total_piste_km` | [Skiresort.info San Vito di Cadore](https://www.skiresort.info/ski-resort/san-vito-di-cadore/) | `10.0` | Reviewed source supports the normalized `total_piste_km` value for `san-vito-di-cadore-ski-area`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `access_mode` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"ski_bus"` | Reviewed source supports the normalized `access_mode` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `atmosphere_tags[0]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"family"` | Reviewed source supports the normalized `atmosphere_tags[0]` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `atmosphere_tags[1]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"quiet"` | Reviewed source supports the normalized `atmosphere_tags[1]` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `atmosphere_tags[2]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"value"` | Reviewed source supports the normalized `atmosphere_tags[2]` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `base_type` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"town"` | Reviewed source supports the normalized `base_type` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `latitude` | [OpenStreetMap Auronzo di Cadore relation](https://www.openstreetmap.org/relation/47236) | `46.5512` | Reviewed source supports the normalized `latitude` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `lift_distance` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"medium"` | Reviewed source supports the normalized `lift_distance` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `longitude` | [OpenStreetMap Auronzo di Cadore relation](https://www.openstreetmap.org/relation/47236) | `12.443` | Reviewed source supports the normalized `longitude` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `name` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"Auronzo di Cadore"` | Reviewed source supports the normalized `name` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `nearest_lift_distance_m` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `2100` | Reviewed source supports the normalized `nearest_lift_distance_m` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `nearest_lift_name` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"Taiarezze-Malon Chairlift"` | Reviewed source supports the normalized `nearest_lift_name` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `price_max` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `220.0` | Reviewed source supports the normalized `price_max` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `price_min` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `140.0` | Reviewed source supports the normalized `price_min` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `price_range` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"EUR 140-220"` | Reviewed source supports the normalized `price_range` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `quality` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"standard"` | Reviewed source supports the normalized `quality` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `regional_data_ids.osm_relation_id` | [OpenStreetMap Auronzo di Cadore relation](https://www.openstreetmap.org/relation/47236) | `"47236"` | Reviewed source supports the normalized `regional_data_ids.osm_relation_id` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `stay_base_id` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"auronzo-di-cadore-auronzo-di-cadore"` | Reviewed source supports the normalized `stay_base_id` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `supported_skill_levels[0]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"advanced"` | Reviewed source supports the normalized `supported_skill_levels[0]` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `supported_skill_levels[1]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"beginner"` | Reviewed source supports the normalized `supported_skill_levels[1]` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore` | `supported_skill_levels[2]` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"intermediate"` | Reviewed source supports the normalized `supported_skill_levels[2]` value for `auronzo-di-cadore:auronzo-di-cadore-auronzo-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `access_mode` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `access_mode` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `atmosphere_tags` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `atmosphere_tags` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `lift_distance` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `lift_distance` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `name` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `name` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `price_max` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `price_max` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `price_min` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `price_min` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `price_range` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `price_range` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `quality` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `quality` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `regional_data_ids` | [OpenStreetMap Cortina d'Ampezzo relation](https://www.openstreetmap.org/relation/47235) | `null` | Reviewed source supports the normalized `regional_data_ids` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `stay_base_id` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `stay_base_id` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `supported_skill_levels[0]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `supported_skill_levels[0]` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo` | `supported_skill_levels[1]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `null` | Reviewed source supports the normalized `supported_skill_levels[1]` value for `cortina-dampezzo:cortina-dampezzo-cortina-d-ampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `access_mode` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"walk"` | Reviewed source supports the normalized `access_mode` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags[0]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"historic"` | Reviewed source supports the normalized `atmosphere_tags[0]` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags[1]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"premium"` | Reviewed source supports the normalized `atmosphere_tags[1]` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `atmosphere_tags[2]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"scenic"` | Reviewed source supports the normalized `atmosphere_tags[2]` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `base_type` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"town"` | Reviewed source supports the normalized `base_type` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `latitude` | [OpenStreetMap Cortina d'Ampezzo relation](https://www.openstreetmap.org/relation/47235) | `46.5405` | Reviewed source supports the normalized `latitude` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `lift_distance` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"near"` | Reviewed source supports the normalized `lift_distance` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `longitude` | [OpenStreetMap Cortina d'Ampezzo relation](https://www.openstreetmap.org/relation/47235) | `12.1357` | Reviewed source supports the normalized `longitude` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `name` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"Cortina d'Ampezzo"` | Reviewed source supports the normalized `name` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_distance_m` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `472` | Reviewed source supports the normalized `nearest_lift_distance_m` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `nearest_lift_name` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"Funivia Faloria"` | Reviewed source supports the normalized `nearest_lift_name` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `price_max` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `300.0` | Reviewed source supports the normalized `price_max` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `price_min` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `210.0` | Reviewed source supports the normalized `price_min` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `price_range` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"EUR 210-300"` | Reviewed source supports the normalized `price_range` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `quality` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"premium"` | Reviewed source supports the normalized `quality` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `regional_data_ids.osm_relation_id` | [OpenStreetMap Cortina d'Ampezzo relation](https://www.openstreetmap.org/relation/47235) | `"47235"` | Reviewed source supports the normalized `regional_data_ids.osm_relation_id` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `stay_base_id` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"cortina-dampezzo-cortina-dampezzo"` | Reviewed source supports the normalized `stay_base_id` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `supported_skill_levels[0]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"advanced"` | Reviewed source supports the normalized `supported_skill_levels[0]` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:cortina-dampezzo:cortina-dampezzo-cortina-dampezzo` | `supported_skill_levels[1]` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"intermediate"` | Reviewed source supports the normalized `supported_skill_levels[1]` value for `cortina-dampezzo:cortina-dampezzo-cortina-dampezzo`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `access_mode` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"walk"` | Reviewed source supports the normalized `access_mode` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `atmosphere_tags[0]` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"high_altitude"` | Reviewed source supports the normalized `atmosphere_tags[0]` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `atmosphere_tags[1]` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"quiet"` | Reviewed source supports the normalized `atmosphere_tags[1]` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `atmosphere_tags[2]` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"scenic"` | Reviewed source supports the normalized `atmosphere_tags[2]` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `base_type` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"lake_village"` | Reviewed source supports the normalized `base_type` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `latitude` | [OpenStreetMap Misurina node](https://www.openstreetmap.org/node/1427982374) | `46.5785` | Reviewed source supports the normalized `latitude` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `lift_distance` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"near"` | Reviewed source supports the normalized `lift_distance` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `longitude` | [OpenStreetMap Misurina node](https://www.openstreetmap.org/node/1427982374) | `12.252` | Reviewed source supports the normalized `longitude` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `name` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"Misurina"` | Reviewed source supports the normalized `name` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `nearest_lift_distance_m` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `900` | Reviewed source supports the normalized `nearest_lift_distance_m` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `nearest_lift_name` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"Col de Varda Chairlift"` | Reviewed source supports the normalized `nearest_lift_name` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `price_max` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `230.0` | Reviewed source supports the normalized `price_max` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `price_min` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `150.0` | Reviewed source supports the normalized `price_min` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `price_range` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"EUR 150-230"` | Reviewed source supports the normalized `price_range` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `quality` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"standard"` | Reviewed source supports the normalized `quality` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `regional_data_ids.osm_node_id` | [OpenStreetMap Misurina node](https://www.openstreetmap.org/node/1427982374) | `"1427982374"` | Reviewed source supports the normalized `regional_data_ids.osm_node_id` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `stay_base_id` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"misurina-misurina"` | Reviewed source supports the normalized `stay_base_id` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `supported_skill_levels[0]` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"advanced"` | Reviewed source supports the normalized `supported_skill_levels[0]` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `supported_skill_levels[1]` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"beginner"` | Reviewed source supports the normalized `supported_skill_levels[1]` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:misurina:misurina-misurina` | `supported_skill_levels[2]` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"intermediate"` | Reviewed source supports the normalized `supported_skill_levels[2]` value for `misurina:misurina-misurina`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `access_mode` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"ski_bus"` | Reviewed source supports the normalized `access_mode` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `atmosphere_tags[0]` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"family"` | Reviewed source supports the normalized `atmosphere_tags[0]` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `atmosphere_tags[1]` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"quiet"` | Reviewed source supports the normalized `atmosphere_tags[1]` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `atmosphere_tags[2]` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"sunny"` | Reviewed source supports the normalized `atmosphere_tags[2]` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `base_type` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"town"` | Reviewed source supports the normalized `base_type` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `latitude` | [OpenStreetMap San Vito di Cadore relation](https://www.openstreetmap.org/relation/47211) | `46.4764` | Reviewed source supports the normalized `latitude` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `lift_distance` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"near"` | Reviewed source supports the normalized `lift_distance` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `longitude` | [OpenStreetMap San Vito di Cadore relation](https://www.openstreetmap.org/relation/47211) | `12.2079` | Reviewed source supports the normalized `longitude` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `name` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"San Vito di Cadore"` | Reviewed source supports the normalized `name` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `nearest_lift_distance_m` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `800` | Reviewed source supports the normalized `nearest_lift_distance_m` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `nearest_lift_name` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"Tambres Chairlift"` | Reviewed source supports the normalized `nearest_lift_name` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `price_max` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `230.0` | Reviewed source supports the normalized `price_max` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `price_min` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `150.0` | Reviewed source supports the normalized `price_min` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `price_range` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"EUR 150-230"` | Reviewed source supports the normalized `price_range` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `quality` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"standard"` | Reviewed source supports the normalized `quality` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `regional_data_ids.osm_relation_id` | [OpenStreetMap San Vito di Cadore relation](https://www.openstreetmap.org/relation/47211) | `"47211"` | Reviewed source supports the normalized `regional_data_ids.osm_relation_id` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `stay_base_id` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"san-vito-di-cadore-san-vito-di-cadore"` | Reviewed source supports the normalized `stay_base_id` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `supported_skill_levels[0]` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"beginner"` | Reviewed source supports the normalized `supported_skill_levels[0]` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `stay_base:san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore` | `supported_skill_levels[1]` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"intermediate"` | Reviewed source supports the normalized `supported_skill_levels[1]` value for `san-vito-di-cadore:san-vito-di-cadore-san-vito-di-cadore`. | Normalized into the catalog model; estimated commercial buckets remain marked estimated where applicable. |  |
| `destination:cortina-dampezzo` | `name` | [Skipass Cortina winter prices](https://skipasscortina.com/EN/page17-cortina-winter-prices) | `"Valley passes connect Cortina d'Ampezzo, San Vito di Cadore, Auronzo and Misurina over 120 km."` | Official pass source confirms Cortina remains a pass-valid valley destination and that the shared valley scope is broader than the Cortina child ski area. | Boundary evidence records the source statement used for the destination gate, not a literal catalog name replacement. | `cortina-dampezzo` |
| `destination:cortina-dampezzo` | `name` | [Skiresort.info Cortina d'Ampezzo](https://www.skiresort.info/ski-resort/cortina-dampezzo/) | `"Cortina d'Ampezzo ski resort with 2026/27 operating window and local ski-area listing."` | Reviewed ski-area source supports Cortina ski access and local operating metadata. | Boundary evidence records the source statement used for the destination gate, not a literal catalog name replacement. | `cortina-dampezzo` |
| `destination:san-vito-di-cadore` | `name` | [Dolomiti Bellunesi San Vito ski areas](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/san-vito-di-cadore-ski-areas) | `"San Vito Ski Area is part of Area no. 1 and the place is treated as a ski destination."` | Official tourism source supports San Vito as a ski-trip destination with independent stay context. | Boundary evidence records the source statement used for the destination gate, not a literal catalog name replacement. | `san-vito-di-cadore` |
| `destination:san-vito-di-cadore` | `name` | [Ski Area San Vito rates](https://www.skiareasanvito.com/en/rates/) | `"San Vito sells skipasses valid exclusively for its area and also accepts Valle Skipass."` | Official operator source supports local pass identity and independent ski access. | Boundary evidence records the source statement used for the destination gate, not a literal catalog name replacement. | `san-vito-di-cadore` |
| `destination:auronzo-di-cadore` | `name` | [Auronzo official skiing page](https://auronzo.info/en/winter/skiing-in-auronzo-di-cadore/) | `"Auronzo is presented as a town of the Tre Cime with bookable holidays and ski access."` | Official destination source supports independent Auronzo stay context and recommendation value. | Boundary evidence records the source statement used for the destination gate, not a literal catalog name replacement. | `auronzo-di-cadore` |
| `destination:auronzo-di-cadore` | `name` | [Monte Agudo Auronzo Misurina ski area](https://monteagudo.it/en/auronzo-misurina-ski-area/) | `"Monte Agudo in Auronzo has chairlifts, ski slopes, ticketing, ski rental, and operator contact."` | Official operator source supports Auronzo ski access and operations. | Boundary evidence records the source statement used for the destination gate, not a literal catalog name replacement. | `auronzo-di-cadore` |
| `destination:misurina` | `name` | [Auronzo official Misurina page](https://auronzo.info/en/misurina-dolomites/) | `"Misurina has hotels, guesthouses, accommodation and a high-elevation lake setting."` | Official Misurina page supports independent stay context and recommendation value. | Boundary evidence records the source statement used for the destination gate, not a literal catalog name replacement. | `misurina` |
| `destination:misurina` | `name` | [Dolomiti Bellunesi Auronzo-Misurina ski area](https://www.visitdolomitibellunesi.com/en/what-to-do/ski-areas-dolomites/auronzo-misurina-ski-area) | `"Misurina ski area is 25 km from Auronzo and includes Col de Varda and Loita."` | Official tourism source supports independent Misurina ski access distinct from Auronzo. | Boundary evidence records the source statement used for the destination gate, not a literal catalog name replacement. | `misurina` |

## Boundary Decisions

Decision targets: `cortina-dampezzo`, `san-vito-di-cadore`, `auronzo-di-cadore`, `misurina`

| Candidate | Failure Route |
| --- | --- |
| `cortina-dampezzo` | `none` |
| `san-vito-di-cadore` | `none` |
| `auronzo-di-cadore` | `none` |
| `misurina` | `none` |

### Candidate `cortina-dampezzo`

#### Gates

| Gate | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `independent_stay_context` | `pass` | `boundary-cortina-dampezzo-pass` | cortina-dampezzo has source-backed lodging/stay context under its own place identity. |
| `independent_ski_access` | `pass` | `boundary-cortina-dampezzo-ski` | cortina-dampezzo directly accesses a stable local ski area rather than only acting as a neighborhood of another base. |
| `independent_recommendation_value` | `pass` | `boundary-cortina-dampezzo-pass` | cortina-dampezzo can materially change fit through price, atmosphere, access, season/elevation, or weather evidence. |

#### Identity Signals

| Signal | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `official_destination_treatment` | `pass` | `boundary-cortina-dampezzo-pass` | Official source treats the place as a destination or ski-area identity rather than only an internal piste sector. |
| `local_pass` | `pass` | `boundary-cortina-dampezzo-pass` | Local pass evidence is explicit where available; otherwise shared valley pass evidence is kept as context. |

### Candidate `san-vito-di-cadore`

#### Gates

| Gate | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `independent_stay_context` | `pass` | `boundary-san-vito-di-cadore-stay` | san-vito-di-cadore has source-backed lodging/stay context under its own place identity. |
| `independent_ski_access` | `pass` | `boundary-san-vito-di-cadore-pass` | san-vito-di-cadore directly accesses a stable local ski area rather than only acting as a neighborhood of another base. |
| `independent_recommendation_value` | `pass` | `boundary-san-vito-di-cadore-stay` | san-vito-di-cadore can materially change fit through price, atmosphere, access, season/elevation, or weather evidence. |

#### Identity Signals

| Signal | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `official_destination_treatment` | `pass` | `boundary-san-vito-di-cadore-stay` | Official source treats the place as a destination or ski-area identity rather than only an internal piste sector. |
| `local_pass` | `pass` | `boundary-san-vito-di-cadore-pass` | Local pass evidence is explicit where available; otherwise shared valley pass evidence is kept as context. |

### Candidate `auronzo-di-cadore`

#### Gates

| Gate | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `independent_stay_context` | `pass` | `boundary-auronzo-di-cadore-stay` | auronzo-di-cadore has source-backed lodging/stay context under its own place identity. |
| `independent_ski_access` | `pass` | `boundary-auronzo-di-cadore-ski` | auronzo-di-cadore directly accesses a stable local ski area rather than only acting as a neighborhood of another base. |
| `independent_recommendation_value` | `pass` | `boundary-auronzo-di-cadore-stay` | auronzo-di-cadore can materially change fit through price, atmosphere, access, season/elevation, or weather evidence. |

#### Identity Signals

| Signal | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `official_destination_treatment` | `pass` | `boundary-auronzo-di-cadore-stay` | Official source treats the place as a destination or ski-area identity rather than only an internal piste sector. |
| `local_pass` | `unresolved` | `boundary-auronzo-di-cadore-ski` | Local pass evidence is explicit where available; otherwise shared valley pass evidence is kept as context. |

### Candidate `misurina`

#### Gates

| Gate | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `independent_stay_context` | `pass` | `boundary-misurina-stay` | misurina has source-backed lodging/stay context under its own place identity. |
| `independent_ski_access` | `pass` | `boundary-misurina-ski` | misurina directly accesses a stable local ski area rather than only acting as a neighborhood of another base. |
| `independent_recommendation_value` | `pass` | `boundary-misurina-stay` | misurina can materially change fit through price, atmosphere, access, season/elevation, or weather evidence. |

#### Identity Signals

| Signal | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `official_destination_treatment` | `pass` | `boundary-misurina-stay` | Official source treats the place as a destination or ski-area identity rather than only an internal piste sector. |
| `local_pass` | `unresolved` | `boundary-misurina-ski` | Local pass evidence is explicit where available; otherwise shared valley pass evidence is kept as context. |

## Weather Request Geometry

Geometry targets: `cortina-dampezzo-ski-area`

| Ski Area | Before | After | Material Change |
| --- | --- | --- | --- |
| `cortina-dampezzo-ski-area` | `{"base_elevation_m": 1224, "latitude": 46.5405, "longitude": 12.1357, "mid_elevation_m": 2077, "upper_elevation_m": 2759}` | `{"base_elevation_m": 1217, "latitude": 46.5405, "longitude": 12.1357, "mid_elevation_m": 2022, "upper_elevation_m": 2667}` | yes |

## Ranking Impact

Ranking-relevant changes add three new Cadore candidate destinations and refine Cortina pass/season/weather geometry scope. No cross-destination terrain domain was added because the reviewed evidence supports shared pass validity, not ski-connected terrain membership.

## Verification

- `uv run python -m app.data.validate_resort_catalog`
- `BASE_DIR=$(mktemp -d); git show origin/main:app/data/resorts.json > "$BASE_DIR/resorts.json"; git show origin/main:app/data/terrain_domains.json > "$BASE_DIR/terrain_domains.json"; git show origin/main:app/data/resort_trust_manifest.json > "$BASE_DIR/resort_trust_manifest.json"; uv run python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-27-cortina-dampezzo.json --validation-mode reconcile --base-resorts-path "$BASE_DIR/resorts.json" --current-resorts-path app/data/resorts.json --base-terrain-domains-path "$BASE_DIR/terrain_domains.json" --current-terrain-domains-path app/data/terrain_domains.json --base-trust-manifest-path "$BASE_DIR/resort_trust_manifest.json" --current-trust-manifest-path app/data/resort_trust_manifest.json --required-boundary-target cortina-dampezzo --required-boundary-target san-vito-di-cadore --required-boundary-target auronzo-di-cadore --required-boundary-target misurina --required-weather-geometry-target cortina-dampezzo-ski-area --allow-legacy-base-trust-without-terrain-domains`

## Caveats

- San Vito official tourism wording says 20 km, while reviewed ski-area data gives 10 km with a 4/5/1 km difficulty split; the catalog stores the child-scope 10 km value and preserves the conflict in trust notes.
- Auronzo official narrative says nearly 20 km, while the detailed lift/slope table and reviewed ski-area listing support about 6.1 km for Monte Agudo; the catalog stores the child-scope 6.1 km value and preserves the broader wording as a caveat.
- San Vito, Auronzo, and Misurina have no accepted future 2026/27 season-window source yet; typical season months are stored and exact future windows can be added in a later recuration.
- New ski-area weather identities require owner-run archive/climatology backfill after deployment; the retained Cortina weather request geometry change is documented in this report.
