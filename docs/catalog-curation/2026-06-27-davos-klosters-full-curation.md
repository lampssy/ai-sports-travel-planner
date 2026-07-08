# Davos Klosters full catalog curation - destination and ski-area topology correction

Rebuilds PR #20 on current main and replaces the synthetic Davos Klosters destination and ski area with the source-backed graph. Davos and Klosters are separate stay destinations; five access-owning bases and six distinct ski areas are modeled. Parsenn / Gotschna remains one ski-connected area, the regional pass covers the five Davos Klosters Mountains areas, and private Schatzalp / Strela remains separate. Exact local access claims, current 2026/27 operating windows, representative pass prices, maps, and source-aware feature facts are recorded without copying regional facts onto child areas.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:davos-klosters-regional-pass` | `full` | all canonical fields |
| `lift_pass_product:schatzalp-strela-ski-pass` | `full` | all canonical fields |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `full` | all canonical fields |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `full` | all canonical fields |
| `ski_area:davos-klosters-ski-area` | `full` | all canonical fields |
| `ski_area:jakobshorn` | `full` | all canonical fields |
| `ski_area:madrisa` | `full` | all canonical fields |
| `ski_area:parsenn-gotschna` | `full` | all canonical fields |
| `ski_area:pischa` | `full` | all canonical fields |
| `ski_area:rinerhorn` | `full` | all canonical fields |
| `ski_area:schatzalp-strela` | `full` | all canonical fields |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `full` | all canonical fields |
| `ski_area_access:davos-dorf--pischa` | `full` | all canonical fields |
| `ski_area_access:davos-glaris--rinerhorn` | `full` | all canonical fields |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `full` | all canonical fields |
| `ski_area_access:davos-platz--jakobshorn` | `full` | all canonical fields |
| `ski_area_access:davos-platz--schatzalp-strela` | `full` | all canonical fields |
| `ski_area_access:klosters-dorf--madrisa` | `full` | all canonical fields |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `full` | all canonical fields |
| `ski_region:davos-klosters` | `full` | all canonical fields |
| `stay_base:davos-dorf` | `full` | all canonical fields |
| `stay_base:davos-glaris` | `full` | all canonical fields |
| `stay_base:davos-klosters-davos-platz` | `full` | all canonical fields |
| `stay_base:davos-platz` | `full` | all canonical fields |
| `stay_base:klosters-dorf` | `full` | all canonical fields |
| `stay_base:klosters-platz` | `full` | all canonical fields |
| `stay_destination:davos` | `full` | all canonical fields |
| `stay_destination:davos-klosters` | `full` | all canonical fields |
| `stay_destination:klosters` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:davos-klosters-regional-pass` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:schatzalp-strela-ski-pass` | `full` | all canonical fields |
| `trust_manifest:rental_display_facts:bardill-sport-shop-davos-platz` | `full` | all canonical fields |
| `trust_manifest:rental_display_facts:davos-klosters-bardill-sport-shop-davos` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:davos-dorf--parsenn-gotschna` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:davos-dorf--pischa` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:davos-glaris--rinerhorn` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:davos-platz--jakobshorn` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:davos-platz--schatzalp-strela` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:klosters-dorf--madrisa` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:klosters-platz--parsenn-gotschna` | `full` | all canonical fields |
| `trust_manifest:ski_areas:davos-klosters-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:jakobshorn` | `full` | all canonical fields |
| `trust_manifest:ski_areas:madrisa` | `full` | all canonical fields |
| `trust_manifest:ski_areas:parsenn-gotschna` | `full` | all canonical fields |
| `trust_manifest:ski_areas:pischa` | `full` | all canonical fields |
| `trust_manifest:ski_areas:rinerhorn` | `full` | all canonical fields |
| `trust_manifest:ski_areas:schatzalp-strela` | `full` | all canonical fields |
| `trust_manifest:ski_regions:davos-klosters` | `full` | all canonical fields |
| `trust_manifest:stay_bases:davos-dorf` | `full` | all canonical fields |
| `trust_manifest:stay_bases:davos-glaris` | `full` | all canonical fields |
| `trust_manifest:stay_bases:davos-klosters-davos-platz` | `full` | all canonical fields |
| `trust_manifest:stay_bases:davos-platz` | `full` | all canonical fields |
| `trust_manifest:stay_bases:klosters-dorf` | `full` | all canonical fields |
| `trust_manifest:stay_bases:klosters-platz` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:davos` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:davos-klosters` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:klosters` | `full` | all canonical fields |

## Entity Scope Assessments

| Candidate | Kind | Disposition | Signals | Catalog Targets | Evidence | Backlog | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `davos` (Davos) | `stay_destination` | `add_entity` | `independent_stay_market`, `distinct_access` | `stay_destination:davos` | `change-342` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `klosters` (Klosters) | `stay_destination` | `add_entity` | `independent_stay_market`, `distinct_access` | `stay_destination:klosters` | `change-360` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `davos-dorf` (Davos Dorf) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:davos-dorf` | `change-259` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `davos-glaris` (Davos Glaris) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:davos-glaris` | `change-274` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `davos-platz` (Davos Platz) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:davos-platz` | `change-301` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `klosters-dorf` (Klosters Dorf) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:klosters-dorf` | `change-317` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `klosters-platz` (Klosters Platz) | `stay_base` | `add_entity` | `distinct_access` | `stay_base:klosters-platz` | `change-333` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `jakobshorn` (Jakobshorn) | `ski_area` | `add_entity` | `official_independent_identity`, `independent_status_or_schedule` | `ski_area:jakobshorn` | `change-065` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `madrisa` (Madrisa) | `ski_area` | `add_entity` | `official_independent_identity`, `independent_status_or_schedule` | `ski_area:madrisa` | `change-088` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `parsenn-gotschna` (Parsenn / Gotschna) | `ski_area` | `add_entity` | `official_independent_identity`, `independent_status_or_schedule` | `ski_area:parsenn-gotschna` | `change-107` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `pischa` (Pischa) | `ski_area` | `add_entity` | `official_independent_identity`, `independent_status_or_schedule` | `ski_area:pischa` | `change-127` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `rinerhorn` (Rinerhorn) | `ski_area` | `add_entity` | `official_independent_identity`, `independent_status_or_schedule` | `ski_area:rinerhorn` | `change-147` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `schatzalp-strela` (Schatzalp / Strela) | `ski_area` | `add_entity` | `official_independent_identity`, `independent_status_or_schedule` | `ski_area:schatzalp-strela` | `change-167` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `davos-dorf--parsenn-gotschna` (Davos Dorf  > Parsenn Gotschna) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:davos-dorf--parsenn-gotschna` | `change-179` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `davos-dorf--pischa` (Davos Dorf  > Pischa) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:davos-dorf--pischa` | `change-188` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `davos-glaris--rinerhorn` (Davos Glaris  > Rinerhorn) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:davos-glaris--rinerhorn` | `change-197` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `davos-platz--jakobshorn` (Davos Platz  > Jakobshorn) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:davos-platz--jakobshorn` | `change-214` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `davos-platz--schatzalp-strela` (Davos Platz  > Schatzalp Strela) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:davos-platz--schatzalp-strela` | `change-223` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `klosters-dorf--madrisa` (Klosters Dorf  > Madrisa) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:klosters-dorf--madrisa` | `change-232` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `klosters-platz--parsenn-gotschna` (Klosters Platz  > Parsenn Gotschna) | `ski_area_access` | `add_entity` | `direct_access_relationship` | `ski_area_access:klosters-platz--parsenn-gotschna` | `change-241` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `davos-klosters-regional-pass` (Davos Klosters regional ski pass) | `lift_pass_product` | `add_entity` | `official_product_identity` | `lift_pass_product:davos-klosters-regional-pass` | `change-004` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `schatzalp-strela-ski-pass` (Schatzalp / Strela ski pass) | `lift_pass_product` | `add_entity` | `official_product_identity` | `lift_pass_product:schatzalp-strela-ski-pass` | `change-014` |  | The candidate owns a distinct catalog identity, access relationship, terrain owner, or official ticket product supported by the cited source. |
| `davos-klosters` (Legacy davos-klosters) | `stay_destination` | `not_separate` | `independent_stay_market` | `stay_destination:davos-klosters` | `scope-retired-01` |  | The legacy synthetic target does not represent an independent current owner and is retired in favor of the source-backed graph. |
| `davos-klosters-davos-platz` (Legacy davos-klosters-davos-platz) | `stay_base` | `not_separate` | `distinct_access` | `stay_base:davos-klosters-davos-platz` | `scope-retired-02` |  | The legacy synthetic target does not represent an independent current owner and is retired in favor of the source-backed graph. |
| `davos-klosters-ski-area` (Legacy davos-klosters-ski-area) | `ski_area` | `not_separate` | `disconnected_terrain`, `official_independent_identity` | `ski_area:davos-klosters-ski-area` | `scope-retired-03` |  | The legacy synthetic target does not represent an independent current owner and is retired in favor of the source-backed graph. |
| `davos-klosters-davos-platz--davos-klosters-ski-area` (Legacy davos-klosters-davos-platz--davos-klosters-ski-area) | `ski_area_access` | `not_separate` | `direct_access_relationship` | `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `scope-retired-04` |  | The legacy synthetic target does not represent an independent current owner and is retired in favor of the source-backed graph. |
| `davos-klosters-connected-terrain-domain` (Davos Klosters regional pass terrain) | `terrain_domain` | `external_pass_context` | `disconnected_terrain`, `official_product_identity` |  | `change-009` |  | The regional pass spans disconnected mountains; shared validity remains pass context and must not create a connected terrain domain. |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:davos-klosters-regional-pass` | `available_from_stay_destination_ids` | `null` | `["davos", "klosters"]` | `verified` | no |
| `lift_pass_product:davos-klosters-regional-pass` | `default_for_stay_destination_ids` | `null` | `["davos", "klosters"]` | `verified` | no |
| `lift_pass_product:davos-klosters-regional-pass` | `external_validity_summary` | `null` | `"Regional ticket covers the five Davos Klosters Mountains ski areas modeled here. The separately operated Schatzalp / Strela ski area is excluded."` | `verified` | no |
| `lift_pass_product:davos-klosters-regional-pass` | `lift_pass_product_id` | `null` | `"davos-klosters-regional-pass"` | `verified` | no |
| `lift_pass_product:davos-klosters-regional-pass` | `name` | `null` | `"Davos Klosters regional ski pass"` | `verified` | no |
| `lift_pass_product:davos-klosters-regional-pass` | `pass_accessible_terrain` | `null` | `{"metric_scope": "pass_accessible", "piste_km_by_difficulty": null, "source_urls": ["https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures"], "total_lift_count": 44, "total_piste_km": 253.0}` | `verified` | no |
| `lift_pass_product:davos-klosters-regional-pass` | `prices` | `null` | `[{"amount": 94.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 regional pass", "source_url": "https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets"}, {"amount": 230.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 regional pass", "source_url": "https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets"}, {"amount": 390.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 regional pass", "source_url": "https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets"}]` | `verified` | no |
| `lift_pass_product:davos-klosters-regional-pass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | no |
| `lift_pass_product:davos-klosters-regional-pass` | `valid_ski_area_ids` | `null` | `["jakobshorn", "madrisa", "parsenn-gotschna", "pischa", "rinerhorn"]` | `verified_with_adjustment` | no |
| `lift_pass_product:davos-klosters-regional-pass` | `validity_scope` | `null` | `"regional_network"` | `verified` | no |
| `lift_pass_product:schatzalp-strela-ski-pass` | `available_from_stay_destination_ids` | `null` | `["davos"]` | `verified_with_adjustment` | no |
| `lift_pass_product:schatzalp-strela-ski-pass` | `default_for_stay_destination_ids` | `null` | `[]` | `verified_with_adjustment` | no |
| `lift_pass_product:schatzalp-strela-ski-pass` | `external_validity_summary` | `null` | `"Separate private ski-area ticket; Davos Klosters Mountains regional passes are not valid at Schatzalp / Strela."` | `verified_with_adjustment` | no |
| `lift_pass_product:schatzalp-strela-ski-pass` | `lift_pass_product_id` | `null` | `"schatzalp-strela-ski-pass"` | `verified_with_adjustment` | no |
| `lift_pass_product:schatzalp-strela-ski-pass` | `name` | `null` | `"Schatzalp / Strela ski pass"` | `verified_with_adjustment` | no |
| `lift_pass_product:schatzalp-strela-ski-pass` | `prices` | `null` | `[]` | `needs_source` | no |
| `lift_pass_product:schatzalp-strela-ski-pass` | `terrain_domain_ids` | `null` | `[]` | `verified` | no |
| `lift_pass_product:schatzalp-strela-ski-pass` | `valid_ski_area_ids` | `null` | `["schatzalp-strela"]` | `verified` | no |
| `lift_pass_product:schatzalp-strela-ski-pass` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | no |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `lift_distance` | `null` | `"near"` | `estimated` | no |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `name` | `null` | `"Bardill Sport Shop Davos"` | `verified_with_adjustment` | no |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `price_max` | `null` | `60.0` | `estimated` | no |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `price_min` | `null` | `40.0` | `estimated` | no |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `price_range` | `null` | `"EUR 40-60"` | `estimated` | no |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `quality` | `null` | `"standard"` | `estimated` | no |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `rental_display_fact_id` | `null` | `"bardill-sport-shop-davos-platz"` | `verified_with_adjustment` | no |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `stay_base_id` | `null` | `"davos-platz"` | `verified_with_adjustment` | no |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `stay_destination_id` | `null` | `"davos"` | `verified_with_adjustment` | no |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `lift_distance` | `"near"` | `null` | `needs_source` | no |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `name` | `"Bardill Sport Shop Davos"` | `null` | `needs_source` | no |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `price_max` | `60.0` | `null` | `needs_source` | no |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `price_min` | `40.0` | `null` | `needs_source` | no |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `price_range` | `"EUR 40-60"` | `null` | `needs_source` | no |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `quality` | `"standard"` | `null` | `needs_source` | no |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `rental_display_fact_id` | `"davos-klosters-bardill-sport-shop-davos"` | `null` | `needs_source` | no |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `stay_destination_id` | `"davos-klosters"` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `base_elevation_m` | `1560` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `glacier_terrain.availability` | `"unknown"` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `latitude` | `46.8027` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `longitude` | `9.836` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `marked_freeride_routes.availability` | `"unknown"` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `name` | `"Davos Klosters"` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `night_skiing.availability` | `"unknown"` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `season_end_month` | `4` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `season_start_month` | `12` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `season_windows` | `[]` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `ski_area_id` | `"davos-klosters-ski-area"` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `ski_day_apres_profile.availability` | `"unknown"` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `snow_park.availability` | `"unknown"` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `snowmaking.availability` | `"unknown"` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `snowmaking.coverage_basis` | `"unknown"` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `summit_elevation_m` | `2844` | `null` | `needs_source` | no |
| `ski_area:davos-klosters-ski-area` | `supported_skill_levels` | `["intermediate", "advanced"]` | `null` | `needs_source` | no |
| `ski_area:jakobshorn` | `base_elevation_m` | `null` | `1560` | `verified` | yes |
| `ski_area:jakobshorn` | `glacier_terrain.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:jakobshorn` | `latitude` | `null` | `46.772399` | `verified_with_adjustment` | no |
| `ski_area:jakobshorn` | `longitude` | `null` | `9.8493406` | `verified_with_adjustment` | no |
| `ski_area:jakobshorn` | `marked_freeride_routes.availability` | `null` | `"available"` | `verified_with_adjustment` | yes |
| `ski_area:jakobshorn` | `marked_freeride_routes.route_count` | `null` | `2` | `verified_with_adjustment` | yes |
| `ski_area:jakobshorn` | `name` | `null` | `"Jakobshorn"` | `verified_with_adjustment` | no |
| `ski_area:jakobshorn` | `night_skiing.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:jakobshorn` | `season_end_month` | `null` | `4` | `verified` | yes |
| `ski_area:jakobshorn` | `season_start_month` | `null` | `11` | `verified` | yes |
| `ski_area:jakobshorn` | `season_windows` | `null` | `[{"end_date": "2026-11-29", "season_label": "Winter 2026/27 pre-opening", "start_date": "2026-11-27", "status": "planned"}, {"end_date": "2027-04-11", "season_label": "Winter 2026/27 main season", "start_date": "2026-12-04", "status": "planned"}]` | `verified` | yes |
| `ski_area:jakobshorn` | `ski_area_id` | `null` | `"jakobshorn"` | `verified_with_adjustment` | no |
| `ski_area:jakobshorn` | `ski_day_apres_profile.availability` | `null` | `"available"` | `verified` | yes |
| `ski_area:jakobshorn` | `ski_day_apres_profile.intensity` | `null` | `"lively"` | `verified` | yes |
| `ski_area:jakobshorn` | `snow_park.availability` | `null` | `"available"` | `verified` | yes |
| `ski_area:jakobshorn` | `snow_park.park_count` | `null` | `1` | `verified` | yes |
| `ski_area:jakobshorn` | `snowmaking.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:jakobshorn` | `snowmaking.coverage_basis` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:jakobshorn` | `summit_elevation_m` | `null` | `2600` | `verified` | yes |
| `ski_area:jakobshorn` | `supported_skill_levels` | `null` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:jakobshorn` | `total_lift_count` | `null` | `12` | `verified_with_adjustment` | yes |
| `ski_area:jakobshorn` | `total_piste_km` | `null` | `55.0` | `verified_with_adjustment` | yes |
| `ski_area:madrisa` | `base_elevation_m` | `null` | `1887` | `verified` | yes |
| `ski_area:madrisa` | `glacier_terrain.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:madrisa` | `latitude` | `null` | `46.9097225` | `verified_with_adjustment` | no |
| `ski_area:madrisa` | `longitude` | `null` | `9.8774507` | `verified_with_adjustment` | no |
| `ski_area:madrisa` | `marked_freeride_routes.availability` | `null` | `"available"` | `verified_with_adjustment` | yes |
| `ski_area:madrisa` | `marked_freeride_routes.route_count` | `null` | `1` | `verified_with_adjustment` | yes |
| `ski_area:madrisa` | `name` | `null` | `"Madrisa"` | `verified_with_adjustment` | no |
| `ski_area:madrisa` | `night_skiing.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:madrisa` | `official_trail_map.url` | `null` | `"https://www.davosklostersmountains.ch/archiv/dkm/dokumente/karten/Pistenplan-Madrisa.pdf"` | `verified` | no |
| `ski_area:madrisa` | `season_end_month` | `null` | `3` | `verified` | yes |
| `ski_area:madrisa` | `season_start_month` | `null` | `12` | `verified` | yes |
| `ski_area:madrisa` | `season_windows` | `null` | `[{"end_date": "2027-03-29", "season_label": "Winter 2026/27", "start_date": "2026-12-18", "status": "planned"}]` | `verified` | yes |
| `ski_area:madrisa` | `ski_area_id` | `null` | `"madrisa"` | `verified_with_adjustment` | no |
| `ski_area:madrisa` | `ski_day_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:madrisa` | `snow_park.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:madrisa` | `snowmaking.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:madrisa` | `snowmaking.coverage_basis` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:madrisa` | `summit_elevation_m` | `null` | `2611` | `verified` | yes |
| `ski_area:madrisa` | `supported_skill_levels` | `null` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:madrisa` | `total_piste_km` | `null` | `31.0` | `verified_with_adjustment` | yes |
| `ski_area:parsenn-gotschna` | `base_elevation_m` | `null` | `1560` | `verified_with_adjustment` | yes |
| `ski_area:parsenn-gotschna` | `glacier_terrain.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:parsenn-gotschna` | `latitude` | `null` | `46.842102` | `verified_with_adjustment` | no |
| `ski_area:parsenn-gotschna` | `longitude` | `null` | `9.8353422` | `verified_with_adjustment` | no |
| `ski_area:parsenn-gotschna` | `marked_freeride_routes.availability` | `null` | `"available"` | `verified_with_adjustment` | yes |
| `ski_area:parsenn-gotschna` | `marked_freeride_routes.route_count` | `null` | `5` | `verified_with_adjustment` | yes |
| `ski_area:parsenn-gotschna` | `name` | `null` | `"Parsenn / Gotschna"` | `verified_with_adjustment` | no |
| `ski_area:parsenn-gotschna` | `night_skiing.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:parsenn-gotschna` | `season_end_month` | `null` | `4` | `verified_with_adjustment` | yes |
| `ski_area:parsenn-gotschna` | `season_start_month` | `null` | `11` | `verified_with_adjustment` | yes |
| `ski_area:parsenn-gotschna` | `season_windows` | `null` | `[{"end_date": "2026-11-15", "season_label": "Winter 2026/27 pre-opening", "start_date": "2026-11-13", "status": "planned"}, {"end_date": "2027-04-04", "season_label": "Winter 2026/27 main season", "start_date": "2026-11-20", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:parsenn-gotschna` | `ski_area_id` | `null` | `"parsenn-gotschna"` | `verified_with_adjustment` | no |
| `ski_area:parsenn-gotschna` | `ski_day_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:parsenn-gotschna` | `snow_park.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:parsenn-gotschna` | `snowmaking.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:parsenn-gotschna` | `snowmaking.coverage_basis` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:parsenn-gotschna` | `summit_elevation_m` | `null` | `2844` | `verified_with_adjustment` | yes |
| `ski_area:parsenn-gotschna` | `supported_skill_levels` | `null` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:parsenn-gotschna` | `total_lift_count` | `null` | `18` | `verified_with_adjustment` | yes |
| `ski_area:parsenn-gotschna` | `total_piste_km` | `null` | `97.0` | `verified_with_adjustment` | yes |
| `ski_area:pischa` | `base_elevation_m` | `null` | `1799` | `verified` | yes |
| `ski_area:pischa` | `glacier_terrain.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:pischa` | `latitude` | `null` | `46.805988` | `verified_with_adjustment` | no |
| `ski_area:pischa` | `longitude` | `null` | `9.9084508` | `verified_with_adjustment` | no |
| `ski_area:pischa` | `marked_freeride_routes.availability` | `null` | `"available"` | `verified` | yes |
| `ski_area:pischa` | `marked_freeride_routes.route_count` | `null` | `1` | `verified` | yes |
| `ski_area:pischa` | `name` | `null` | `"Pischa"` | `verified_with_adjustment` | no |
| `ski_area:pischa` | `night_skiing.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:pischa` | `season_end_month` | `null` | `3` | `verified` | yes |
| `ski_area:pischa` | `season_start_month` | `null` | `12` | `verified` | yes |
| `ski_area:pischa` | `season_windows` | `null` | `[{"end_date": "2027-01-17", "season_label": "Winter 2026/27 before WEF closure", "start_date": "2026-12-26", "status": "planned"}, {"end_date": "2027-03-29", "season_label": "Winter 2026/27 after WEF closure", "start_date": "2027-01-23", "status": "planned"}]` | `verified` | yes |
| `ski_area:pischa` | `ski_area_id` | `null` | `"pischa"` | `verified_with_adjustment` | no |
| `ski_area:pischa` | `ski_day_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:pischa` | `snow_park.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:pischa` | `snowmaking.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:pischa` | `snowmaking.coverage_basis` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:pischa` | `summit_elevation_m` | `null` | `2481` | `verified` | yes |
| `ski_area:pischa` | `supported_skill_levels` | `null` | `["advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:pischa` | `total_lift_count` | `null` | `1` | `verified` | yes |
| `ski_area:pischa` | `total_piste_km` | `null` | `0.0` | `verified` | yes |
| `ski_area:rinerhorn` | `base_elevation_m` | `null` | `1457` | `verified_with_adjustment` | yes |
| `ski_area:rinerhorn` | `glacier_terrain.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:rinerhorn` | `latitude` | `null` | `46.741226` | `verified_with_adjustment` | no |
| `ski_area:rinerhorn` | `longitude` | `null` | `9.7980089` | `verified_with_adjustment` | no |
| `ski_area:rinerhorn` | `marked_freeride_routes.availability` | `null` | `"available"` | `verified_with_adjustment` | yes |
| `ski_area:rinerhorn` | `marked_freeride_routes.route_count` | `null` | `3` | `verified_with_adjustment` | yes |
| `ski_area:rinerhorn` | `name` | `null` | `"Rinerhorn"` | `verified_with_adjustment` | no |
| `ski_area:rinerhorn` | `night_skiing.availability` | `null` | `"available"` | `verified` | yes |
| `ski_area:rinerhorn` | `night_skiing.season_label` | `null` | `"Winter 2026/27"` | `verified` | no |
| `ski_area:rinerhorn` | `season_end_month` | `null` | `3` | `verified_with_adjustment` | yes |
| `ski_area:rinerhorn` | `season_start_month` | `null` | `12` | `verified_with_adjustment` | yes |
| `ski_area:rinerhorn` | `season_windows` | `null` | `[{"end_date": "2027-01-17", "season_label": "Winter 2026/27 before WEF closure", "start_date": "2026-12-18", "status": "planned"}, {"end_date": "2027-03-29", "season_label": "Winter 2026/27 after WEF closure", "start_date": "2027-01-23", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:rinerhorn` | `ski_area_id` | `null` | `"rinerhorn"` | `verified_with_adjustment` | no |
| `ski_area:rinerhorn` | `ski_day_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:rinerhorn` | `snow_park.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:rinerhorn` | `snowmaking.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:rinerhorn` | `snowmaking.coverage_basis` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:rinerhorn` | `summit_elevation_m` | `null` | `2490` | `verified_with_adjustment` | yes |
| `ski_area:rinerhorn` | `supported_skill_levels` | `null` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:rinerhorn` | `total_lift_count` | `null` | `5` | `verified_with_adjustment` | yes |
| `ski_area:rinerhorn` | `total_piste_km` | `null` | `39.0` | `verified_with_adjustment` | yes |
| `ski_area:schatzalp-strela` | `base_elevation_m` | `null` | `1557` | `verified_with_adjustment` | yes |
| `ski_area:schatzalp-strela` | `glacier_terrain.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:schatzalp-strela` | `latitude` | `null` | `46.8013896` | `verified_with_adjustment` | no |
| `ski_area:schatzalp-strela` | `longitude` | `null` | `9.8149673` | `verified_with_adjustment` | no |
| `ski_area:schatzalp-strela` | `marked_freeride_routes.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:schatzalp-strela` | `name` | `null` | `"Schatzalp / Strela"` | `verified_with_adjustment` | no |
| `ski_area:schatzalp-strela` | `night_skiing.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:schatzalp-strela` | `official_trail_map.url` | `null` | `"https://resources.davos.ch/fileadmin/user_upload/dokumente/broschueren_karten/Winterkarte-Schatzalp.pdf"` | `verified` | no |
| `ski_area:schatzalp-strela` | `season_end_month` | `null` | `3` | `verified_with_adjustment` | yes |
| `ski_area:schatzalp-strela` | `season_start_month` | `null` | `12` | `verified_with_adjustment` | yes |
| `ski_area:schatzalp-strela` | `season_windows` | `null` | `[]` | `verified_with_adjustment` | yes |
| `ski_area:schatzalp-strela` | `ski_area_id` | `null` | `"schatzalp-strela"` | `verified_with_adjustment` | no |
| `ski_area:schatzalp-strela` | `ski_day_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:schatzalp-strela` | `snow_park.availability` | `null` | `"unknown"` | `needs_source` | no |
| `ski_area:schatzalp-strela` | `snowmaking.availability` | `null` | `"unavailable"` | `verified` | yes |
| `ski_area:schatzalp-strela` | `snowmaking.coverage_basis` | `null` | `"unknown"` | `verified` | no |
| `ski_area:schatzalp-strela` | `summit_elevation_m` | `null` | `2350` | `verified_with_adjustment` | yes |
| `ski_area:schatzalp-strela` | `supported_skill_levels` | `null` | `["beginner", "intermediate"]` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `nearest_lift_name` | `null` | `"Parsenn funicular"` | `verified_with_adjustment` | no |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `regional_data_ids` | `null` | `{}` | `verified_with_adjustment` | no |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `ski_area_access_id` | `null` | `"davos-dorf--parsenn-gotschna"` | `verified` | no |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `ski_area_id` | `null` | `"parsenn-gotschna"` | `verified` | no |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `source_urls` | `null` | `["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn"]` | `verified` | no |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `stay_base_id` | `null` | `"davos-dorf"` | `verified` | no |
| `ski_area_access:davos-dorf--pischa` | `access_mode` | `null` | `"ski_bus"` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-dorf--pischa` | `is_direct` | `null` | `false` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-dorf--pischa` | `lift_distance` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-dorf--pischa` | `nearest_lift_name` | `null` | `"Pischa cable car"` | `verified_with_adjustment` | no |
| `ski_area_access:davos-dorf--pischa` | `regional_data_ids` | `null` | `{}` | `verified_with_adjustment` | no |
| `ski_area_access:davos-dorf--pischa` | `ski_area_access_id` | `null` | `"davos-dorf--pischa"` | `verified` | no |
| `ski_area_access:davos-dorf--pischa` | `ski_area_id` | `null` | `"pischa"` | `verified` | no |
| `ski_area_access:davos-dorf--pischa` | `source_urls` | `null` | `["https://www.davosklostersmountains.ch/en/mountains/mountains/pischa"]` | `verified` | no |
| `ski_area_access:davos-dorf--pischa` | `stay_base_id` | `null` | `"davos-dorf"` | `verified` | no |
| `ski_area_access:davos-glaris--rinerhorn` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-glaris--rinerhorn` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-glaris--rinerhorn` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-glaris--rinerhorn` | `nearest_lift_name` | `null` | `"Rinerhorn gondola"` | `verified_with_adjustment` | no |
| `ski_area_access:davos-glaris--rinerhorn` | `regional_data_ids` | `null` | `{}` | `verified_with_adjustment` | no |
| `ski_area_access:davos-glaris--rinerhorn` | `ski_area_access_id` | `null` | `"davos-glaris--rinerhorn"` | `verified` | no |
| `ski_area_access:davos-glaris--rinerhorn` | `ski_area_id` | `null` | `"rinerhorn"` | `verified` | no |
| `ski_area_access:davos-glaris--rinerhorn` | `source_urls` | `null` | `["https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn"]` | `verified` | no |
| `ski_area_access:davos-glaris--rinerhorn` | `stay_base_id` | `null` | `"davos-glaris"` | `verified` | no |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `access_mode` | `"unknown"` | `null` | `needs_source` | no |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `is_direct` | `false` | `null` | `needs_source` | no |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `lift_distance` | `"near"` | `null` | `needs_source` | no |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `regional_data_ids` | `{}` | `null` | `needs_source` | no |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `ski_area_access_id` | `"davos-klosters-davos-platz--davos-klosters-ski-area"` | `null` | `needs_source` | no |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `ski_area_id` | `"davos-klosters-ski-area"` | `null` | `needs_source` | no |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `source_urls` | `["https://www.bergfex.com/skiregionen/davos-klosters-mountains/"]` | `null` | `needs_source` | no |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `stay_base_id` | `"davos-klosters-davos-platz"` | `null` | `needs_source` | no |
| `ski_area_access:davos-platz--jakobshorn` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-platz--jakobshorn` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-platz--jakobshorn` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-platz--jakobshorn` | `nearest_lift_name` | `null` | `"Jakobshorn cable car"` | `verified_with_adjustment` | no |
| `ski_area_access:davos-platz--jakobshorn` | `regional_data_ids` | `null` | `{}` | `verified_with_adjustment` | no |
| `ski_area_access:davos-platz--jakobshorn` | `ski_area_access_id` | `null` | `"davos-platz--jakobshorn"` | `verified` | no |
| `ski_area_access:davos-platz--jakobshorn` | `ski_area_id` | `null` | `"jakobshorn"` | `verified` | no |
| `ski_area_access:davos-platz--jakobshorn` | `source_urls` | `null` | `["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn"]` | `verified` | no |
| `ski_area_access:davos-platz--jakobshorn` | `stay_base_id` | `null` | `"davos-platz"` | `verified` | no |
| `ski_area_access:davos-platz--schatzalp-strela` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-platz--schatzalp-strela` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-platz--schatzalp-strela` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:davos-platz--schatzalp-strela` | `nearest_lift_name` | `null` | `"Schatzalp funicular"` | `verified_with_adjustment` | no |
| `ski_area_access:davos-platz--schatzalp-strela` | `regional_data_ids` | `null` | `{}` | `verified_with_adjustment` | no |
| `ski_area_access:davos-platz--schatzalp-strela` | `ski_area_access_id` | `null` | `"davos-platz--schatzalp-strela"` | `verified` | no |
| `ski_area_access:davos-platz--schatzalp-strela` | `ski_area_id` | `null` | `"schatzalp-strela"` | `verified` | no |
| `ski_area_access:davos-platz--schatzalp-strela` | `source_urls` | `null` | `["https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela"]` | `verified` | no |
| `ski_area_access:davos-platz--schatzalp-strela` | `stay_base_id` | `null` | `"davos-platz"` | `verified` | no |
| `ski_area_access:klosters-dorf--madrisa` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:klosters-dorf--madrisa` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:klosters-dorf--madrisa` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:klosters-dorf--madrisa` | `nearest_lift_name` | `null` | `"Madrisa gondola"` | `verified_with_adjustment` | no |
| `ski_area_access:klosters-dorf--madrisa` | `regional_data_ids` | `null` | `{}` | `verified_with_adjustment` | no |
| `ski_area_access:klosters-dorf--madrisa` | `ski_area_access_id` | `null` | `"klosters-dorf--madrisa"` | `verified` | no |
| `ski_area_access:klosters-dorf--madrisa` | `ski_area_id` | `null` | `"madrisa"` | `verified` | no |
| `ski_area_access:klosters-dorf--madrisa` | `source_urls` | `null` | `["https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa"]` | `verified` | no |
| `ski_area_access:klosters-dorf--madrisa` | `stay_base_id` | `null` | `"klosters-dorf"` | `verified` | no |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `is_direct` | `null` | `true` | `verified_with_adjustment` | yes |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `nearest_lift_name` | `null` | `"Gotschna cable car"` | `verified_with_adjustment` | no |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `regional_data_ids` | `null` | `{}` | `verified_with_adjustment` | no |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `ski_area_access_id` | `null` | `"klosters-platz--parsenn-gotschna"` | `verified` | no |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `ski_area_id` | `null` | `"parsenn-gotschna"` | `verified` | no |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `source_urls` | `null` | `["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn"]` | `verified` | no |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `stay_base_id` | `null` | `"klosters-platz"` | `verified` | no |
| `ski_region:davos-klosters` | `source_urls` | `[]` | `["https://www.davos.ch/en/activities/snowsports/ski-snowboard"]` | `verified` | no |
| `stay_base:davos-dorf` | `base_character.development_style` | `null` | `"mixed"` | `estimated` | no |
| `stay_base:davos-dorf` | `base_character.local_pace` | `null` | `"balanced"` | `estimated` | no |
| `stay_base:davos-dorf` | `base_type` | `null` | `"neighbourhood"` | `verified_with_adjustment` | yes |
| `stay_base:davos-dorf` | `elevation_m` | `null` | `1560` | `verified_with_adjustment` | yes |
| `stay_base:davos-dorf` | `latitude` | `null` | `46.8065596` | `verified` | no |
| `stay_base:davos-dorf` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:davos-dorf` | `longitude` | `null` | `9.8381801` | `verified` | no |
| `stay_base:davos-dorf` | `name` | `null` | `"Davos Dorf"` | `verified` | no |
| `stay_base:davos-dorf` | `price_max` | `null` | `260.0` | `estimated` | no |
| `stay_base:davos-dorf` | `price_min` | `null` | `190.0` | `estimated` | no |
| `stay_base:davos-dorf` | `price_range` | `null` | `"EUR 190-260"` | `estimated` | no |
| `stay_base:davos-dorf` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:davos-dorf` | `regional_data_ids` | `null` | `{"osm_node_id": "26032383"}` | `verified` | no |
| `stay_base:davos-dorf` | `stay_base_id` | `null` | `"davos-dorf"` | `verified` | no |
| `stay_base:davos-dorf` | `stay_destination_id` | `null` | `"davos"` | `verified` | no |
| `stay_base:davos-glaris` | `base_character.development_style` | `null` | `"traditional"` | `verified_with_adjustment` | yes |
| `stay_base:davos-glaris` | `base_character.local_pace` | `null` | `"quiet"` | `verified_with_adjustment` | yes |
| `stay_base:davos-glaris` | `base_type` | `null` | `"hamlet"` | `verified` | yes |
| `stay_base:davos-glaris` | `elevation_m` | `null` | `1457` | `verified` | yes |
| `stay_base:davos-glaris` | `latitude` | `null` | `46.7417217` | `verified` | no |
| `stay_base:davos-glaris` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:davos-glaris` | `longitude` | `null` | `9.7775036` | `verified` | no |
| `stay_base:davos-glaris` | `name` | `null` | `"Davos Glaris"` | `verified` | no |
| `stay_base:davos-glaris` | `price_max` | `null` | `220.0` | `estimated` | no |
| `stay_base:davos-glaris` | `price_min` | `null` | `150.0` | `estimated` | no |
| `stay_base:davos-glaris` | `price_range` | `null` | `"EUR 150-220"` | `estimated` | no |
| `stay_base:davos-glaris` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:davos-glaris` | `regional_data_ids` | `null` | `{"osm_node_id": "12853320191"}` | `verified` | no |
| `stay_base:davos-glaris` | `stay_base_id` | `null` | `"davos-glaris"` | `verified` | no |
| `stay_base:davos-glaris` | `stay_destination_id` | `null` | `"davos"` | `verified` | no |
| `stay_base:davos-klosters-davos-platz` | `base_character.development_style` | `"unknown"` | `null` | `needs_source` | no |
| `stay_base:davos-klosters-davos-platz` | `base_character.local_pace` | `"unknown"` | `null` | `needs_source` | no |
| `stay_base:davos-klosters-davos-platz` | `local_apres_profile.availability` | `"unknown"` | `null` | `needs_source` | no |
| `stay_base:davos-klosters-davos-platz` | `name` | `"Davos Platz"` | `null` | `needs_source` | no |
| `stay_base:davos-klosters-davos-platz` | `price_max` | `260.0` | `null` | `needs_source` | no |
| `stay_base:davos-klosters-davos-platz` | `price_min` | `190.0` | `null` | `needs_source` | no |
| `stay_base:davos-klosters-davos-platz` | `price_range` | `"EUR 190-260"` | `null` | `needs_source` | no |
| `stay_base:davos-klosters-davos-platz` | `quality` | `"standard"` | `null` | `needs_source` | no |
| `stay_base:davos-klosters-davos-platz` | `regional_data_ids` | `{}` | `null` | `needs_source` | no |
| `stay_base:davos-klosters-davos-platz` | `stay_base_id` | `"davos-klosters-davos-platz"` | `null` | `needs_source` | no |
| `stay_base:davos-klosters-davos-platz` | `stay_destination_id` | `"davos-klosters"` | `null` | `needs_source` | no |
| `stay_base:davos-platz` | `base_character.development_style` | `null` | `"mixed"` | `verified_with_adjustment` | yes |
| `stay_base:davos-platz` | `base_character.local_pace` | `null` | `"lively"` | `verified_with_adjustment` | yes |
| `stay_base:davos-platz` | `base_type` | `null` | `"neighbourhood"` | `verified_with_adjustment` | yes |
| `stay_base:davos-platz` | `elevation_m` | `null` | `1560` | `verified_with_adjustment` | yes |
| `stay_base:davos-platz` | `latitude` | `null` | `46.7933845` | `verified` | no |
| `stay_base:davos-platz` | `local_apres_profile.availability` | `null` | `"available"` | `verified_with_adjustment` | yes |
| `stay_base:davos-platz` | `local_apres_profile.intensity` | `null` | `"destination_defining"` | `verified_with_adjustment` | yes |
| `stay_base:davos-platz` | `longitude` | `null` | `9.8206999` | `verified` | no |
| `stay_base:davos-platz` | `name` | `null` | `"Davos Platz"` | `verified` | no |
| `stay_base:davos-platz` | `price_max` | `null` | `260.0` | `estimated` | no |
| `stay_base:davos-platz` | `price_min` | `null` | `190.0` | `estimated` | no |
| `stay_base:davos-platz` | `price_range` | `null` | `"EUR 190-260"` | `estimated` | no |
| `stay_base:davos-platz` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:davos-platz` | `regional_data_ids` | `null` | `{"osm_node_id": "240072917"}` | `verified` | no |
| `stay_base:davos-platz` | `stay_base_id` | `null` | `"davos-platz"` | `verified` | no |
| `stay_base:davos-platz` | `stay_destination_id` | `null` | `"davos"` | `verified` | no |
| `stay_base:klosters-dorf` | `base_character.development_style` | `null` | `"traditional"` | `verified_with_adjustment` | yes |
| `stay_base:klosters-dorf` | `base_character.local_pace` | `null` | `"quiet"` | `verified_with_adjustment` | yes |
| `stay_base:klosters-dorf` | `base_type` | `null` | `"neighbourhood"` | `verified_with_adjustment` | yes |
| `stay_base:klosters-dorf` | `elevation_m` | `null` | `1124` | `verified` | yes |
| `stay_base:klosters-dorf` | `latitude` | `null` | `46.8835913` | `verified` | no |
| `stay_base:klosters-dorf` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:klosters-dorf` | `longitude` | `null` | `9.87523` | `verified` | no |
| `stay_base:klosters-dorf` | `name` | `null` | `"Klosters Dorf"` | `verified` | no |
| `stay_base:klosters-dorf` | `price_max` | `null` | `240.0` | `estimated` | no |
| `stay_base:klosters-dorf` | `price_min` | `null` | `170.0` | `estimated` | no |
| `stay_base:klosters-dorf` | `price_range` | `null` | `"EUR 170-240"` | `estimated` | no |
| `stay_base:klosters-dorf` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:klosters-dorf` | `regional_data_ids` | `null` | `{"osm_node_id": "5370737666"}` | `verified` | no |
| `stay_base:klosters-dorf` | `stay_base_id` | `null` | `"klosters-dorf"` | `verified` | no |
| `stay_base:klosters-dorf` | `stay_destination_id` | `null` | `"klosters"` | `verified` | no |
| `stay_base:klosters-platz` | `base_character.development_style` | `null` | `"traditional"` | `verified_with_adjustment` | yes |
| `stay_base:klosters-platz` | `base_character.local_pace` | `null` | `"quiet"` | `verified_with_adjustment` | yes |
| `stay_base:klosters-platz` | `base_type` | `null` | `"neighbourhood"` | `verified_with_adjustment` | yes |
| `stay_base:klosters-platz` | `elevation_m` | `null` | `1191` | `verified` | yes |
| `stay_base:klosters-platz` | `latitude` | `null` | `46.8682882` | `verified` | no |
| `stay_base:klosters-platz` | `local_apres_profile.availability` | `null` | `"unknown"` | `needs_source` | no |
| `stay_base:klosters-platz` | `longitude` | `null` | `9.8821599` | `verified` | no |
| `stay_base:klosters-platz` | `name` | `null` | `"Klosters Platz"` | `verified` | no |
| `stay_base:klosters-platz` | `price_max` | `null` | `270.0` | `estimated` | no |
| `stay_base:klosters-platz` | `price_min` | `null` | `190.0` | `estimated` | no |
| `stay_base:klosters-platz` | `price_range` | `null` | `"EUR 190-270"` | `estimated` | no |
| `stay_base:klosters-platz` | `quality` | `null` | `"premium"` | `estimated` | no |
| `stay_base:klosters-platz` | `regional_data_ids` | `null` | `{"osm_node_id": "240119460"}` | `verified` | no |
| `stay_base:klosters-platz` | `stay_base_id` | `null` | `"klosters-platz"` | `verified` | no |
| `stay_base:klosters-platz` | `stay_destination_id` | `null` | `"klosters"` | `verified` | no |
| `stay_destination:davos` | `country` | `null` | `"Switzerland"` | `verified` | no |
| `stay_destination:davos` | `latitude` | `null` | `46.8027` | `verified_with_adjustment` | no |
| `stay_destination:davos` | `longitude` | `null` | `9.836` | `verified_with_adjustment` | no |
| `stay_destination:davos` | `name` | `null` | `"Davos"` | `verified` | no |
| `stay_destination:davos` | `price_level` | `null` | `"medium"` | `estimated` | no |
| `stay_destination:davos` | `region` | `null` | `"Graubunden"` | `verified` | no |
| `stay_destination:davos` | `regional_data_ids` | `null` | `{}` | `verified_with_adjustment` | no |
| `stay_destination:davos` | `stay_destination_id` | `null` | `"davos"` | `verified` | no |
| `stay_destination:davos` | `trip_market_region_id` | `null` | `"davos-klosters"` | `verified` | no |
| `stay_destination:davos-klosters` | `country` | `"Switzerland"` | `null` | `needs_source` | no |
| `stay_destination:davos-klosters` | `latitude` | `46.8027` | `null` | `needs_source` | no |
| `stay_destination:davos-klosters` | `longitude` | `9.836` | `null` | `needs_source` | no |
| `stay_destination:davos-klosters` | `name` | `"Davos Klosters"` | `null` | `needs_source` | no |
| `stay_destination:davos-klosters` | `price_level` | `"medium"` | `null` | `needs_source` | no |
| `stay_destination:davos-klosters` | `region` | `"Graubunden"` | `null` | `needs_source` | no |
| `stay_destination:davos-klosters` | `regional_data_ids` | `{}` | `null` | `needs_source` | no |
| `stay_destination:davos-klosters` | `stay_destination_id` | `"davos-klosters"` | `null` | `needs_source` | no |
| `stay_destination:davos-klosters` | `trip_market_region_id` | `"davos-klosters"` | `null` | `needs_source` | no |
| `stay_destination:klosters` | `country` | `null` | `"Switzerland"` | `verified` | no |
| `stay_destination:klosters` | `latitude` | `null` | `46.8682882` | `verified` | no |
| `stay_destination:klosters` | `longitude` | `null` | `9.8821599` | `verified` | no |
| `stay_destination:klosters` | `name` | `null` | `"Klosters"` | `verified` | no |
| `stay_destination:klosters` | `price_level` | `null` | `"high"` | `estimated` | no |
| `stay_destination:klosters` | `region` | `null` | `"Graubunden"` | `verified` | no |
| `stay_destination:klosters` | `regional_data_ids` | `null` | `{"osm_node_id": "240119460"}` | `verified` | no |
| `stay_destination:klosters` | `stay_destination_id` | `null` | `"klosters"` | `verified` | no |
| `stay_destination:klosters` | `trip_market_region_id` | `null` | `"davos-klosters"` | `verified` | no |
| `trust_manifest:lift_pass_products:davos-klosters-regional-pass` | `display_name` | `null` | `"Davos Klosters regional ski pass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:davos-klosters-regional-pass` | `field_source_refs` | `null` | `{"coverage": ["https://www.davosklostersmountains.ch/archiv/dkm/dokumente/b2b/winter/grp-info_Winter_en.pdf", "https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets"], "identity_scope_availability": ["https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets"], "pass_accessible_terrain": ["https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures"], "prices": ["https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:davos-klosters-regional-pass` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified", "pass_accessible_terrain": "verified", "prices": "verified"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:davos-klosters-regional-pass` | `notes` | `null` | `["The regional product links exactly the five modeled Davos Klosters Mountains areas and excludes the private Schatzalp / Strela area.", "The representative 1-, 3-, and 6-day adult prices are the published Winter 2026/27 fixed regional rates.", "The 253 km and 44-lift metrics remain pass-accessible aggregate facts and are not copied onto any child ski area."]` | `estimated` | no |
| `trust_manifest:lift_pass_products:schatzalp-strela-ski-pass` | `display_name` | `null` | `"Schatzalp / Strela ski pass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:schatzalp-strela-ski-pass` | `field_source_refs` | `null` | `{"coverage": ["https://resources.davos.ch/fileadmin/user_upload/dokumente/broschueren_karten/Winterkarte-Schatzalp.pdf"], "identity_scope_availability": ["https://www.schatzalp.ch/en/agb", "https://www.schatzalp.ch/en/funicular"], "pass_accessible_terrain": [], "prices": []}` | `estimated` | no |
| `trust_manifest:lift_pass_products:schatzalp-strela-ski-pass` | `field_statuses` | `null` | `{"coverage": "verified", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "needs_source"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:schatzalp-strela-ski-pass` | `notes` | `null` | `["Official operator terms establish a separate ticket product for the Schatzalp funicular and ski-area facilities.", "The official winter map states that Davos Klosters Mountains passes are not valid in the private Schatzalp / Strela area.", "No current representative ski-pass price or exact pass terrain aggregate was accepted."]` | `estimated` | no |
| `trust_manifest:rental_display_facts:bardill-sport-shop-davos-platz` | `display_name` | `null` | `"Bardill Sport Shop Davos"` | `estimated` | no |
| `trust_manifest:rental_display_facts:bardill-sport-shop-davos-platz` | `field_source_refs` | `null` | `{"identity_ownership": ["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn"], "price_quality_access": []}` | `estimated` | no |
| `trust_manifest:rental_display_facts:bardill-sport-shop-davos-platz` | `field_statuses` | `null` | `{"identity_ownership": "verified_with_adjustment", "price_quality_access": "estimated"}` | `estimated` | no |
| `trust_manifest:rental_display_facts:bardill-sport-shop-davos-platz` | `notes` | `null` | `["The official Jakobshorn page confirms equipment rental at sports shops by the valley station; the existing Bardill display fact is retargeted to Davos Platz.", "Price, quality, and lift-distance remain product-curated estimates."]` | `estimated` | no |
| `trust_manifest:rental_display_facts:davos-klosters-bardill-sport-shop-davos` | `display_name` | `"Bardill Sport Shop Davos"` | `null` | `needs_source` | no |
| `trust_manifest:rental_display_facts:davos-klosters-bardill-sport-shop-davos` | `field_source_refs` | `{"identity_ownership": [], "price_quality_access": []}` | `null` | `needs_source` | no |
| `trust_manifest:rental_display_facts:davos-klosters-bardill-sport-shop-davos` | `field_statuses` | `{"identity_ownership": "estimated", "price_quality_access": "estimated"}` | `null` | `needs_source` | no |
| `trust_manifest:rental_display_facts:davos-klosters-bardill-sport-shop-davos` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands."]` | `null` | `needs_source` | no |
| `trust_manifest:ski_area_access:davos-dorf--parsenn-gotschna` | `display_name` | `null` | `"Davos Dorf -> Parsenn / Gotschna"` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-dorf--parsenn-gotschna` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn"], "relationship": ["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-dorf--parsenn-gotschna` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-dorf--parsenn-gotschna` | `notes` | `null` | `["The official area page identifies the Parsenn funicular as the Davos feeder.", "Near walk access is asserted without an unsupported exact distance or duration."]` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-dorf--pischa` | `display_name` | `null` | `"Davos Dorf -> Pischa"` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-dorf--pischa` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.davosklostersmountains.ch/en/mountains/mountains/pischa"], "relationship": ["https://www.davosklostersmountains.ch/en/mountains/mountains/pischa"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-dorf--pischa` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-dorf--pischa` | `notes` | `null` | `["The official area page directs guests to the Pischabus stop near the Parsenn valley station in Davos Dorf.", "No unsupported exact bus duration or distance is stored."]` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-glaris--rinerhorn` | `display_name` | `null` | `"Davos Glaris -> Rinerhorn"` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-glaris--rinerhorn` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn"], "relationship": ["https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-glaris--rinerhorn` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-glaris--rinerhorn` | `notes` | `null` | `["The official Rinerhorn page locates the valley station in Davos Glaris.", "Near walk access is asserted without an unsupported exact distance or duration."]` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `display_name` | `"Davos Platz -> Davos Klosters"` | `null` | `needs_source` | no |
| `trust_manifest:ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/skiregionen/davos-klosters-mountains/"], "relationship": ["https://www.bergfex.com/skiregionen/davos-klosters-mountains/"]}` | `null` | `needs_source` | no |
| `trust_manifest:ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `null` | `needs_source` | no |
| `trust_manifest:ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Provider-backed relationship remains estimated; no exact distance or duration is asserted."]` | `null` | `needs_source` | no |
| `trust_manifest:ski_area_access:davos-platz--jakobshorn` | `display_name` | `null` | `"Davos Platz -> Jakobshorn"` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-platz--jakobshorn` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn"], "relationship": ["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-platz--jakobshorn` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-platz--jakobshorn` | `notes` | `null` | `["The official Jakobshorn page places the valley access and Bolgen area in central Davos Platz.", "Near walk access replaces the unsupported 560 m claim; no exact distance or duration is stored."]` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-platz--schatzalp-strela` | `display_name` | `null` | `"Davos Platz -> Schatzalp / Strela"` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-platz--schatzalp-strela` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela"], "relationship": ["https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-platz--schatzalp-strela` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:davos-platz--schatzalp-strela` | `notes` | `null` | `["Official tourism places the Schatzalp funicular four minutes from the center of Davos Platz.", "The source supports near walk access but not a precise metric distance."]` | `estimated` | no |
| `trust_manifest:ski_area_access:klosters-dorf--madrisa` | `display_name` | `null` | `"Klosters Dorf -> Madrisa"` | `estimated` | no |
| `trust_manifest:ski_area_access:klosters-dorf--madrisa` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa"], "relationship": ["https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:klosters-dorf--madrisa` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:klosters-dorf--madrisa` | `notes` | `null` | `["The official Madrisa page gives the operator address in Klosters Dorf and identifies the Madrisa gondola as the feeder.", "Near walk access is asserted without an unsupported exact distance or duration."]` | `estimated` | no |
| `trust_manifest:ski_area_access:klosters-platz--parsenn-gotschna` | `display_name` | `null` | `"Klosters Platz -> Parsenn / Gotschna"` | `estimated` | no |
| `trust_manifest:ski_area_access:klosters-platz--parsenn-gotschna` | `field_source_refs` | `null` | `{"access_mode_distance": ["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn"], "relationship": ["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:klosters-platz--parsenn-gotschna` | `field_statuses` | `null` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified"}` | `estimated` | no |
| `trust_manifest:ski_area_access:klosters-platz--parsenn-gotschna` | `notes` | `null` | `["The official area page identifies the Gotschna cable car as the Klosters feeder to the connected Parsenn / Gotschna area.", "Near walk access is asserted without an unsupported exact distance or duration."]` | `estimated` | no |
| `trust_manifest:ski_areas:davos-klosters-ski-area` | `display_name` | `"Davos Klosters"` | `null` | `needs_source` | no |
| `trust_manifest:ski_areas:davos-klosters-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `null` | `needs_source` | no |
| `trust_manifest:ski_areas:davos-klosters-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `null` | `needs_source` | no |
| `trust_manifest:ski_areas:davos-klosters-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `null` | `needs_source` | no |
| `trust_manifest:ski_areas:jakobshorn` | `display_name` | `null` | `"Jakobshorn"` | `estimated` | no |
| `trust_manifest:ski_areas:jakobshorn` | `field_source_refs` | `null` | `{"elevation_season": ["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn", "https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes"], "glacier_terrain": [], "identity_coordinates": ["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn", "https://www.openstreetmap.org/node/2896258648"], "marked_freeride_routes": ["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn", "https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures"], "night_skiing": [], "official_documents": [], "ski_day_apres": ["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn"], "skill_fit": ["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn"], "snow_park": ["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn"], "snowmaking": [], "terrain_metrics": ["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn"]}` | `estimated` | no |
| `trust_manifest:ski_areas:jakobshorn` | `field_statuses` | `null` | `{"elevation_season": "verified", "glacier_terrain": "needs_source", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "verified_with_adjustment", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "verified", "skill_fit": "verified_with_adjustment", "snow_park": "verified", "snowmaking": "needs_source", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:jakobshorn` | `notes` | `null` | `["Jakobshorn is an independently presented mountain with its own metrics and operating schedule.", "The representative weather coordinate uses the mapped summit; the base elevation is normalized from the Davos valley context.", "The official 55 km total conflicts with the separate difficulty-and-route inventory, so no difficulty split is stored."]` | `estimated` | no |
| `trust_manifest:ski_areas:madrisa` | `display_name` | `null` | `"Madrisa"` | `estimated` | no |
| `trust_manifest:ski_areas:madrisa` | `field_source_refs` | `null` | `{"elevation_season": ["https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa", "https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes"], "glacier_terrain": [], "identity_coordinates": ["https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa", "https://www.openstreetmap.org/way/601298991"], "marked_freeride_routes": ["https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures"], "night_skiing": [], "official_documents": ["https://www.davosklostersmountains.ch/archiv/dkm/dokumente/karten/Pistenplan-Madrisa.pdf"], "ski_day_apres": [], "skill_fit": ["https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa"], "snow_park": [], "snowmaking": [], "terrain_metrics": ["https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa", "https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures"]}` | `estimated` | no |
| `trust_manifest:ski_areas:madrisa` | `field_statuses` | `null` | `{"elevation_season": "verified", "glacier_terrain": "needs_source", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "verified_with_adjustment", "night_skiing": "needs_source", "official_documents": "verified", "ski_day_apres": "needs_source", "skill_fit": "verified_with_adjustment", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:madrisa` | `notes` | `null` | `["Madrisa is an independently presented mountain with its own metrics, map and operating schedule.", "The official page enumerates lift types differently from the live facility counter, so total_lift_count remains unresolved.", "The official 31 km total conflicts with the separate difficulty-and-route inventory, so no difficulty split is stored."]` | `estimated` | no |
| `trust_manifest:ski_areas:parsenn-gotschna` | `display_name` | `null` | `"Parsenn / Gotschna"` | `estimated` | no |
| `trust_manifest:ski_areas:parsenn-gotschna` | `field_source_refs` | `null` | `{"elevation_season": ["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn", "https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes"], "glacier_terrain": [], "identity_coordinates": ["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn", "https://www.openstreetmap.org/way/601299396"], "marked_freeride_routes": ["https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures"], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": ["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn"], "snow_park": [], "snowmaking": [], "terrain_metrics": ["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn"]}` | `estimated` | no |
| `trust_manifest:ski_areas:parsenn-gotschna` | `field_statuses` | `null` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "needs_source", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "verified_with_adjustment", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "verified_with_adjustment", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:parsenn-gotschna` | `notes` | `null` | `["Parsenn and Gotschna are one ski-connected operating area reached from Davos and Klosters, not separate ski areas.", "The 2026/27 window starts with the first published Davos-side opening; the Klosters-side Gotschna opening is later.", "The official 97 km total conflicts with the separate difficulty-and-route inventory, so no difficulty split is stored."]` | `estimated` | no |
| `trust_manifest:ski_areas:pischa` | `display_name` | `null` | `"Pischa"` | `estimated` | no |
| `trust_manifest:ski_areas:pischa` | `field_source_refs` | `null` | `{"elevation_season": ["https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes", "https://www.davosklostersmountains.ch/en/mountains/winter/winter-activities/snowshoe-hiking"], "glacier_terrain": [], "identity_coordinates": ["https://www.davosklostersmountains.ch/en/mountains/mountains/pischa", "https://www.openstreetmap.org/way/601299503"], "marked_freeride_routes": ["https://www.davosklostersmountains.ch/en/mountains/mountains/pischa", "https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures"], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": ["https://www.davosklostersmountains.ch/en/mountains/mountains/pischa"], "snow_park": [], "snowmaking": [], "terrain_metrics": ["https://www.davosklostersmountains.ch/en/mountains/mountains/pischa", "https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures"]}` | `estimated` | no |
| `trust_manifest:ski_areas:pischa` | `field_statuses` | `null` | `{"elevation_season": "verified", "glacier_terrain": "needs_source", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "verified", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "verified_with_adjustment", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "verified"}` | `estimated` | no |
| `trust_manifest:ski_areas:pischa` | `notes` | `null` | `["Pischa is an independently presented freeride mountain with no groomed pistes and one lift.", "The published WEF closure is represented by two season windows instead of overstating continuous operation."]` | `estimated` | no |
| `trust_manifest:ski_areas:rinerhorn` | `display_name` | `null` | `"Rinerhorn"` | `estimated` | no |
| `trust_manifest:ski_areas:rinerhorn` | `field_source_refs` | `null` | `{"elevation_season": ["https://www.davos.ch/entdecken/ausfluege-in-und-um-davos-klosters/umgebung-seitentaeler", "https://www.davosklostersmountains.ch/archiv/dkm/dokumente/karten/Pistenplan-DKM.pdf", "https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn", "https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes"], "glacier_terrain": [], "identity_coordinates": ["https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn", "https://www.openstreetmap.org/way/601300983"], "marked_freeride_routes": ["https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures"], "night_skiing": ["https://www.davosklostersmountains.ch/en/mountains/gastro-events/events/Rinerhorn-night-skiing-and-sledding_e_1275719", "https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn"], "official_documents": [], "ski_day_apres": [], "skill_fit": ["https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn"], "snow_park": [], "snowmaking": [], "terrain_metrics": ["https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn"]}` | `estimated` | no |
| `trust_manifest:ski_areas:rinerhorn` | `field_statuses` | `null` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "needs_source", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "verified_with_adjustment", "night_skiing": "verified", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "verified_with_adjustment", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:rinerhorn` | `notes` | `null` | `["Rinerhorn is an independently presented mountain with its own local metrics and operating schedule.", "The recurring official night-skiing offer supports availability; no one-off event inference is used.", "The official 39 km total conflicts with the separate difficulty-and-route inventory, so no difficulty split is stored."]` | `estimated` | no |
| `trust_manifest:ski_areas:schatzalp-strela` | `display_name` | `null` | `"Schatzalp / Strela"` | `estimated` | no |
| `trust_manifest:ski_areas:schatzalp-strela` | `field_source_refs` | `null` | `{"elevation_season": ["https://resources.davos.ch/fileadmin/user_upload/dokumente/broschueren_karten/Winterkarte-Schatzalp.pdf", "https://www.schatzalp.ch/en/funicular"], "glacier_terrain": [], "identity_coordinates": ["https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela", "https://www.openstreetmap.org/node/2894011356"], "marked_freeride_routes": [], "night_skiing": [], "official_documents": ["https://resources.davos.ch/fileadmin/user_upload/dokumente/broschueren_karten/Winterkarte-Schatzalp.pdf"], "ski_day_apres": [], "skill_fit": ["https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela"], "snow_park": [], "snowmaking": ["https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela"], "terrain_metrics": []}` | `estimated` | no |
| `trust_manifest:ski_areas:schatzalp-strela` | `field_statuses` | `null` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "needs_source", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "verified", "ski_day_apres": "needs_source", "skill_fit": "verified_with_adjustment", "snow_park": "needs_source", "snowmaking": "verified", "terrain_metrics": "needs_source"}` | `estimated` | no |
| `trust_manifest:ski_areas:schatzalp-strela` | `notes` | `null` | `["Schatzalp / Strela is a separate private ski area and is not part of the Davos Klosters Mountains regional pass.", "The official page establishes natural-snow operation without artificial snowmaking.", "The funicular window does not prove the exact ski-area season, so season_windows and local terrain totals remain unresolved."]` | `estimated` | no |
| `trust_manifest:ski_regions:davos-klosters` | `field_source_refs` | `{"identity": [], "membership_context": []}` | `{"identity": ["https://www.davos.ch/en/activities/snowsports/ski-snowboard"], "membership_context": ["https://www.davos.ch/en/activities/snowsports/ski-snowboard"]}` | `estimated` | no |
| `trust_manifest:ski_regions:davos-klosters` | `field_statuses` | `{"identity": "needs_source", "membership_context": "estimated"}` | `{"identity": "verified", "membership_context": "verified"}` | `estimated` | no |
| `trust_manifest:ski_regions:davos-klosters` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Trip-market membership is retained as reviewed migration context and remains estimated.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Official tourism presents Davos and Klosters together as one trip market with six distinct ski areas.", "The trip-market region groups planning context only; it does not imply ski-connected terrain."]` | `estimated` | no |
| `trust_manifest:stay_bases:davos-dorf` | `display_name` | `null` | `"Davos Dorf"` | `estimated` | no |
| `trust_manifest:stay_bases:davos-dorf` | `field_source_refs` | `null` | `{"base_character": [], "base_type": ["https://www.openstreetmap.org/node/26032383"], "coordinates": ["https://www.openstreetmap.org/node/26032383"], "elevation": ["https://www.davos.ch/en/information/portrait-image/davos"], "identity_ownership": ["https://www.davos.ch/en/information/portrait-image/davos", "https://www.openstreetmap.org/node/26032383"], "local_apres": [], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:davos-dorf` | `field_statuses` | `null` | `{"base_character": "estimated", "base_type": "verified_with_adjustment", "coordinates": "verified", "elevation": "verified_with_adjustment", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:davos-dorf` | `notes` | `null` | `["OpenStreetMap identifies Davos Dorf as a suburb; Snowcast normalizes that settlement role to neighbourhood.", "The official Davos elevation is used as the local base elevation because the source does not publish a separate Dorf figure.", "Lodging and character values remain product-curated estimates; no exact local après source was accepted."]` | `estimated` | no |
| `trust_manifest:stay_bases:davos-glaris` | `display_name` | `null` | `"Davos Glaris"` | `estimated` | no |
| `trust_manifest:stay_bases:davos-glaris` | `field_source_refs` | `null` | `{"base_character": ["https://www.davos.ch/entdecken/ausfluege-in-und-um-davos-klosters/umgebung-seitentaeler"], "base_type": ["https://www.openstreetmap.org/node/12853320191"], "coordinates": ["https://www.openstreetmap.org/node/12853320191"], "elevation": ["https://www.davos.ch/entdecken/ausfluege-in-und-um-davos-klosters/umgebung-seitentaeler"], "identity_ownership": ["https://www.davos.ch/en/information/portrait-image/davos", "https://www.openstreetmap.org/node/12853320191"], "local_apres": [], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:davos-glaris` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified", "coordinates": "verified", "elevation": "verified", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:davos-glaris` | `notes` | `null` | `["Davos Glaris is retained as a distinct hamlet because it owns the direct Rinerhorn feeder relationship.", "Official tourism gives Glaris as 1457 m and describes it as a typical Walser settlement; Snowcast normalizes that to traditional and quiet with an explicit adjustment.", "Lodging values remain product-curated estimates; no exact local après source was accepted."]` | `estimated` | no |
| `trust_manifest:stay_bases:davos-klosters-davos-platz` | `display_name` | `"Davos Platz"` | `null` | `needs_source` | no |
| `trust_manifest:stay_bases:davos-klosters-davos-platz` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `null` | `needs_source` | no |
| `trust_manifest:stay_bases:davos-klosters-davos-platz` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `null` | `needs_source` | no |
| `trust_manifest:stay_bases:davos-klosters-davos-platz` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `null` | `needs_source` | no |
| `trust_manifest:stay_bases:davos-platz` | `display_name` | `null` | `"Davos Platz"` | `estimated` | no |
| `trust_manifest:stay_bases:davos-platz` | `field_source_refs` | `null` | `{"base_character": ["https://www.davos.ch/en/information/portrait-image/davos"], "base_type": ["https://www.openstreetmap.org/node/240072917"], "coordinates": ["https://www.openstreetmap.org/node/240072917"], "elevation": ["https://www.davos.ch/en/information/portrait-image/davos"], "identity_ownership": ["https://www.davos.ch/en/information/portrait-image/davos", "https://www.openstreetmap.org/node/240072917"], "local_apres": ["https://www.davos.ch/en/information/portrait-image/davos"], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:davos-platz` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified", "elevation": "verified_with_adjustment", "identity_ownership": "verified", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:davos-platz` | `notes` | `null` | `["OpenStreetMap identifies Davos Platz as a suburb; Snowcast normalizes that settlement role to neighbourhood.", "The official Davos portrait supports a mixed urban-alpine, lively destination profile; it is applied to central Davos Platz with an explicit adjustment.", "Lodging values remain product-curated estimates."]` | `estimated` | no |
| `trust_manifest:stay_bases:klosters-dorf` | `display_name` | `null` | `"Klosters Dorf"` | `estimated` | no |
| `trust_manifest:stay_bases:klosters-dorf` | `field_source_refs` | `null` | `{"base_character": ["https://www.davos.ch/en/information/portrait-image/klosters"], "base_type": ["https://www.davos.ch/en/information/portrait-image/klosters", "https://www.openstreetmap.org/node/5370737666"], "coordinates": ["https://www.openstreetmap.org/node/5370737666"], "elevation": ["https://www.openstreetmap.org/node/5370737666"], "identity_ownership": ["https://www.davos.ch/en/information/portrait-image/klosters", "https://www.openstreetmap.org/node/5370737666"], "local_apres": [], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:klosters-dorf` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified", "elevation": "verified", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:klosters-dorf` | `notes` | `null` | `["Klosters Dorf is modeled as a neighbourhood within the Klosters stay destination because it owns the Madrisa feeder relationship.", "Traditional and quiet character values normalize the official description of Klosters as an original chalet village with discreet luxury.", "The destination portrait does not establish a local après offer, so the local profile remains unknown; lodging values remain product-curated estimates."]` | `estimated` | no |
| `trust_manifest:stay_bases:klosters-platz` | `display_name` | `null` | `"Klosters Platz"` | `estimated` | no |
| `trust_manifest:stay_bases:klosters-platz` | `field_source_refs` | `null` | `{"base_character": ["https://www.davos.ch/en/information/portrait-image/klosters"], "base_type": ["https://www.openstreetmap.org/node/240119460"], "coordinates": ["https://www.openstreetmap.org/node/240119460"], "elevation": ["https://www.openstreetmap.org/node/240119460"], "identity_ownership": ["https://www.davos.ch/en/information/portrait-image/klosters", "https://www.openstreetmap.org/node/240119460"], "local_apres": [], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:klosters-platz` | `field_statuses` | `null` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified", "elevation": "verified", "identity_ownership": "verified", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:klosters-platz` | `notes` | `null` | `["OpenStreetMap identifies Klosters Platz as a suburb; Snowcast normalizes that settlement role to neighbourhood.", "Traditional and quiet character values normalize the official description of Klosters as an original chalet village with discreet luxury.", "The destination portrait does not establish a local après offer, so the local profile remains unknown; lodging values remain product-curated estimates."]` | `estimated` | no |
| `trust_manifest:stay_destinations:davos` | `display_name` | `null` | `"Davos"` | `estimated` | no |
| `trust_manifest:stay_destinations:davos` | `field_source_refs` | `null` | `{"coordinates": ["https://www.davos.ch/en/information/portrait-image/davos", "https://www.openstreetmap.org/node/240072917"], "identity_location": ["https://www.davos.ch/en/information/portrait-image/davos"], "price_level": []}` | `estimated` | no |
| `trust_manifest:stay_destinations:davos` | `field_statuses` | `null` | `{"coordinates": "verified_with_adjustment", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:davos` | `notes` | `null` | `["Official tourism treats Davos as an independent stay market within the joint Davos Klosters trip market.", "The destination coordinate is a representative Davos center; individual stay bases own their local coordinates.", "Price level remains a product-curated estimate."]` | `estimated` | no |
| `trust_manifest:stay_destinations:davos-klosters` | `display_name` | `"Davos Klosters"` | `null` | `needs_source` | no |
| `trust_manifest:stay_destinations:davos-klosters` | `field_source_refs` | `{"coordinates": [], "identity_location": [], "price_level": []}` | `null` | `needs_source` | no |
| `trust_manifest:stay_destinations:davos-klosters` | `field_statuses` | `{"coordinates": "needs_source", "identity_location": "needs_source", "price_level": "estimated"}` | `null` | `needs_source` | no |
| `trust_manifest:stay_destinations:davos-klosters` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `null` | `needs_source` | no |
| `trust_manifest:stay_destinations:klosters` | `display_name` | `null` | `"Klosters"` | `estimated` | no |
| `trust_manifest:stay_destinations:klosters` | `field_source_refs` | `null` | `{"coordinates": ["https://www.openstreetmap.org/node/240119460"], "identity_location": ["https://www.davos.ch/en/information/portrait-image/klosters"], "price_level": []}` | `estimated` | no |
| `trust_manifest:stay_destinations:klosters` | `field_statuses` | `null` | `{"coordinates": "verified", "identity_location": "verified", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:klosters` | `notes` | `null` | `["Official tourism treats Klosters as an independent stay market within the joint Davos Klosters trip market.", "The representative destination coordinate uses Klosters Platz; local stay bases retain their own anchors.", "Price level remains a product-curated estimate."]` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:davos-klosters-regional-pass` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:davos-klosters-regional-pass` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:davos-klosters-regional-pass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:davos-klosters-regional-pass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:davos-klosters-regional-pass` | `name` | `changed` |  |
| `lift_pass_product:davos-klosters-regional-pass` | `pass_accessible_terrain` | `changed` |  |
| `lift_pass_product:davos-klosters-regional-pass` | `prices` | `changed` |  |
| `lift_pass_product:davos-klosters-regional-pass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:davos-klosters-regional-pass` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:davos-klosters-regional-pass` | `validity_scope` | `changed` |  |
| `lift_pass_product:schatzalp-strela-ski-pass` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:schatzalp-strela-ski-pass` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:schatzalp-strela-ski-pass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:schatzalp-strela-ski-pass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:schatzalp-strela-ski-pass` | `name` | `changed` |  |
| `lift_pass_product:schatzalp-strela-ski-pass` | `pass_accessible_terrain` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `lift_pass_product:schatzalp-strela-ski-pass` | `prices` | `changed` |  |
| `lift_pass_product:schatzalp-strela-ski-pass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:schatzalp-strela-ski-pass` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:schatzalp-strela-ski-pass` | `validity_scope` | `changed` |  |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `lift_distance` | `changed` |  |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `name` | `changed` |  |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `price_max` | `changed` |  |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `price_min` | `changed` |  |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `price_range` | `changed` |  |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `quality` | `changed` |  |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `rental_display_fact_id` | `changed` |  |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `stay_base_id` | `changed` |  |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `stay_destination_id` | `changed` |  |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `lift_distance` | `changed` |  |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `name` | `changed` |  |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `price_max` | `changed` |  |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `price_min` | `changed` |  |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `price_range` | `changed` |  |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `quality` | `changed` |  |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `rental_display_fact_id` | `changed` |  |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `stay_base_id` | `not-applicable` | Legacy target retired by this curation. |
| `rental_display_fact:davos-klosters-bardill-sport-shop-davos` | `stay_destination_id` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `base_elevation_m` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `glacier_terrain.availability` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `latitude` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `longitude` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `marked_freeride_routes.availability` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `marked_freeride_routes.route_count` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `marked_freeride_routes.season_label` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `name` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `night_skiing.availability` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `night_skiing.season_label` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `official_trail_map.season_label` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `official_trail_map.url` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `piste_km_by_difficulty.advanced` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `piste_km_by_difficulty.beginner` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `piste_km_by_difficulty.intermediate` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `season_end_month` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `season_windows` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `ski_day_apres_profile.intensity` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `ski_day_apres_profile.season_label` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `snow_park.availability` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `snow_park.park_count` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `snow_park.season_label` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `snowmaking.availability` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `snowmaking.coverage_basis` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `snowmaking.coverage_pct` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `snowmaking.season_label` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `summit_elevation_m` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:davos-klosters-ski-area` | `total_lift_count` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:davos-klosters-ski-area` | `total_piste_km` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area:jakobshorn` | `base_elevation_m` | `changed` |  |
| `ski_area:jakobshorn` | `glacier_terrain.availability` | `changed` |  |
| `ski_area:jakobshorn` | `latitude` | `changed` |  |
| `ski_area:jakobshorn` | `longitude` | `changed` |  |
| `ski_area:jakobshorn` | `marked_freeride_routes.availability` | `changed` |  |
| `ski_area:jakobshorn` | `marked_freeride_routes.route_count` | `changed` |  |
| `ski_area:jakobshorn` | `marked_freeride_routes.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `name` | `changed` |  |
| `ski_area:jakobshorn` | `night_skiing.availability` | `changed` |  |
| `ski_area:jakobshorn` | `night_skiing.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `official_trail_map.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `official_trail_map.url` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `piste_km_by_difficulty.advanced` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `piste_km_by_difficulty.beginner` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `piste_km_by_difficulty.intermediate` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `season_end_month` | `changed` |  |
| `ski_area:jakobshorn` | `season_start_month` | `changed` |  |
| `ski_area:jakobshorn` | `season_windows` | `changed` |  |
| `ski_area:jakobshorn` | `ski_area_id` | `changed` |  |
| `ski_area:jakobshorn` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:jakobshorn` | `ski_day_apres_profile.intensity` | `changed` |  |
| `ski_area:jakobshorn` | `ski_day_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `snow_park.availability` | `changed` |  |
| `ski_area:jakobshorn` | `snow_park.park_count` | `changed` |  |
| `ski_area:jakobshorn` | `snow_park.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `snowmaking.availability` | `changed` |  |
| `ski_area:jakobshorn` | `snowmaking.coverage_basis` | `changed` |  |
| `ski_area:jakobshorn` | `snowmaking.coverage_pct` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `snowmaking.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:jakobshorn` | `summit_elevation_m` | `changed` |  |
| `ski_area:jakobshorn` | `supported_skill_levels` | `changed` |  |
| `ski_area:jakobshorn` | `total_lift_count` | `changed` |  |
| `ski_area:jakobshorn` | `total_piste_km` | `changed` |  |
| `ski_area:madrisa` | `base_elevation_m` | `changed` |  |
| `ski_area:madrisa` | `glacier_terrain.availability` | `changed` |  |
| `ski_area:madrisa` | `latitude` | `changed` |  |
| `ski_area:madrisa` | `longitude` | `changed` |  |
| `ski_area:madrisa` | `marked_freeride_routes.availability` | `changed` |  |
| `ski_area:madrisa` | `marked_freeride_routes.route_count` | `changed` |  |
| `ski_area:madrisa` | `marked_freeride_routes.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `name` | `changed` |  |
| `ski_area:madrisa` | `night_skiing.availability` | `changed` |  |
| `ski_area:madrisa` | `night_skiing.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `official_trail_map.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `official_trail_map.url` | `changed` |  |
| `ski_area:madrisa` | `piste_km_by_difficulty.advanced` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `piste_km_by_difficulty.beginner` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `piste_km_by_difficulty.intermediate` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `season_end_month` | `changed` |  |
| `ski_area:madrisa` | `season_start_month` | `changed` |  |
| `ski_area:madrisa` | `season_windows` | `changed` |  |
| `ski_area:madrisa` | `ski_area_id` | `changed` |  |
| `ski_area:madrisa` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:madrisa` | `ski_day_apres_profile.intensity` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `ski_day_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `snow_park.availability` | `changed` |  |
| `ski_area:madrisa` | `snow_park.park_count` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `snow_park.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `snowmaking.availability` | `changed` |  |
| `ski_area:madrisa` | `snowmaking.coverage_basis` | `changed` |  |
| `ski_area:madrisa` | `snowmaking.coverage_pct` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `snowmaking.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `summit_elevation_m` | `changed` |  |
| `ski_area:madrisa` | `supported_skill_levels` | `changed` |  |
| `ski_area:madrisa` | `total_lift_count` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:madrisa` | `total_piste_km` | `changed` |  |
| `ski_area:parsenn-gotschna` | `base_elevation_m` | `changed` |  |
| `ski_area:parsenn-gotschna` | `glacier_terrain.availability` | `changed` |  |
| `ski_area:parsenn-gotschna` | `latitude` | `changed` |  |
| `ski_area:parsenn-gotschna` | `longitude` | `changed` |  |
| `ski_area:parsenn-gotschna` | `marked_freeride_routes.availability` | `changed` |  |
| `ski_area:parsenn-gotschna` | `marked_freeride_routes.route_count` | `changed` |  |
| `ski_area:parsenn-gotschna` | `marked_freeride_routes.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `name` | `changed` |  |
| `ski_area:parsenn-gotschna` | `night_skiing.availability` | `changed` |  |
| `ski_area:parsenn-gotschna` | `night_skiing.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `official_trail_map.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `official_trail_map.url` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `piste_km_by_difficulty.advanced` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `piste_km_by_difficulty.beginner` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `piste_km_by_difficulty.intermediate` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `season_end_month` | `changed` |  |
| `ski_area:parsenn-gotschna` | `season_start_month` | `changed` |  |
| `ski_area:parsenn-gotschna` | `season_windows` | `changed` |  |
| `ski_area:parsenn-gotschna` | `ski_area_id` | `changed` |  |
| `ski_area:parsenn-gotschna` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:parsenn-gotschna` | `ski_day_apres_profile.intensity` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `ski_day_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `snow_park.availability` | `changed` |  |
| `ski_area:parsenn-gotschna` | `snow_park.park_count` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `snow_park.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `snowmaking.availability` | `changed` |  |
| `ski_area:parsenn-gotschna` | `snowmaking.coverage_basis` | `changed` |  |
| `ski_area:parsenn-gotschna` | `snowmaking.coverage_pct` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `snowmaking.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:parsenn-gotschna` | `summit_elevation_m` | `changed` |  |
| `ski_area:parsenn-gotschna` | `supported_skill_levels` | `changed` |  |
| `ski_area:parsenn-gotschna` | `total_lift_count` | `changed` |  |
| `ski_area:parsenn-gotschna` | `total_piste_km` | `changed` |  |
| `ski_area:pischa` | `base_elevation_m` | `changed` |  |
| `ski_area:pischa` | `glacier_terrain.availability` | `changed` |  |
| `ski_area:pischa` | `latitude` | `changed` |  |
| `ski_area:pischa` | `longitude` | `changed` |  |
| `ski_area:pischa` | `marked_freeride_routes.availability` | `changed` |  |
| `ski_area:pischa` | `marked_freeride_routes.route_count` | `changed` |  |
| `ski_area:pischa` | `marked_freeride_routes.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `name` | `changed` |  |
| `ski_area:pischa` | `night_skiing.availability` | `changed` |  |
| `ski_area:pischa` | `night_skiing.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `official_trail_map.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `official_trail_map.url` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `piste_km_by_difficulty.advanced` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `piste_km_by_difficulty.beginner` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `piste_km_by_difficulty.intermediate` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `season_end_month` | `changed` |  |
| `ski_area:pischa` | `season_start_month` | `changed` |  |
| `ski_area:pischa` | `season_windows` | `changed` |  |
| `ski_area:pischa` | `ski_area_id` | `changed` |  |
| `ski_area:pischa` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:pischa` | `ski_day_apres_profile.intensity` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `ski_day_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `snow_park.availability` | `changed` |  |
| `ski_area:pischa` | `snow_park.park_count` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `snow_park.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `snowmaking.availability` | `changed` |  |
| `ski_area:pischa` | `snowmaking.coverage_basis` | `changed` |  |
| `ski_area:pischa` | `snowmaking.coverage_pct` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `snowmaking.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:pischa` | `summit_elevation_m` | `changed` |  |
| `ski_area:pischa` | `supported_skill_levels` | `changed` |  |
| `ski_area:pischa` | `total_lift_count` | `changed` |  |
| `ski_area:pischa` | `total_piste_km` | `changed` |  |
| `ski_area:rinerhorn` | `base_elevation_m` | `changed` |  |
| `ski_area:rinerhorn` | `glacier_terrain.availability` | `changed` |  |
| `ski_area:rinerhorn` | `latitude` | `changed` |  |
| `ski_area:rinerhorn` | `longitude` | `changed` |  |
| `ski_area:rinerhorn` | `marked_freeride_routes.availability` | `changed` |  |
| `ski_area:rinerhorn` | `marked_freeride_routes.route_count` | `changed` |  |
| `ski_area:rinerhorn` | `marked_freeride_routes.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `name` | `changed` |  |
| `ski_area:rinerhorn` | `night_skiing.availability` | `changed` |  |
| `ski_area:rinerhorn` | `night_skiing.season_label` | `changed` |  |
| `ski_area:rinerhorn` | `official_trail_map.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `official_trail_map.url` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `piste_km_by_difficulty.advanced` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `piste_km_by_difficulty.beginner` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `piste_km_by_difficulty.intermediate` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `season_end_month` | `changed` |  |
| `ski_area:rinerhorn` | `season_start_month` | `changed` |  |
| `ski_area:rinerhorn` | `season_windows` | `changed` |  |
| `ski_area:rinerhorn` | `ski_area_id` | `changed` |  |
| `ski_area:rinerhorn` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:rinerhorn` | `ski_day_apres_profile.intensity` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `ski_day_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `snow_park.availability` | `changed` |  |
| `ski_area:rinerhorn` | `snow_park.park_count` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `snow_park.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `snowmaking.availability` | `changed` |  |
| `ski_area:rinerhorn` | `snowmaking.coverage_basis` | `changed` |  |
| `ski_area:rinerhorn` | `snowmaking.coverage_pct` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `snowmaking.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:rinerhorn` | `summit_elevation_m` | `changed` |  |
| `ski_area:rinerhorn` | `supported_skill_levels` | `changed` |  |
| `ski_area:rinerhorn` | `total_lift_count` | `changed` |  |
| `ski_area:rinerhorn` | `total_piste_km` | `changed` |  |
| `ski_area:schatzalp-strela` | `base_elevation_m` | `changed` |  |
| `ski_area:schatzalp-strela` | `glacier_terrain.availability` | `changed` |  |
| `ski_area:schatzalp-strela` | `latitude` | `changed` |  |
| `ski_area:schatzalp-strela` | `longitude` | `changed` |  |
| `ski_area:schatzalp-strela` | `marked_freeride_routes.availability` | `changed` |  |
| `ski_area:schatzalp-strela` | `marked_freeride_routes.route_count` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `marked_freeride_routes.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `name` | `changed` |  |
| `ski_area:schatzalp-strela` | `night_skiing.availability` | `changed` |  |
| `ski_area:schatzalp-strela` | `night_skiing.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `official_trail_map.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `official_trail_map.url` | `changed` |  |
| `ski_area:schatzalp-strela` | `piste_km_by_difficulty.advanced` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `piste_km_by_difficulty.beginner` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `piste_km_by_difficulty.intermediate` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `season_end_month` | `changed` |  |
| `ski_area:schatzalp-strela` | `season_start_month` | `changed` |  |
| `ski_area:schatzalp-strela` | `season_windows` | `changed` |  |
| `ski_area:schatzalp-strela` | `ski_area_id` | `changed` |  |
| `ski_area:schatzalp-strela` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:schatzalp-strela` | `ski_day_apres_profile.intensity` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `ski_day_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `snow_park.availability` | `changed` |  |
| `ski_area:schatzalp-strela` | `snow_park.park_count` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `snow_park.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `snowmaking.availability` | `changed` |  |
| `ski_area:schatzalp-strela` | `snowmaking.coverage_basis` | `changed` |  |
| `ski_area:schatzalp-strela` | `snowmaking.coverage_pct` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `snowmaking.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `summit_elevation_m` | `changed` |  |
| `ski_area:schatzalp-strela` | `supported_skill_levels` | `changed` |  |
| `ski_area:schatzalp-strela` | `total_lift_count` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area:schatzalp-strela` | `total_piste_km` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `access_mode` | `changed` |  |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `distance_m` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `duration_minutes` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `is_direct` | `changed` |  |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `lift_distance` | `changed` |  |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `regional_data_ids` | `changed` |  |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `ski_area_id` | `changed` |  |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `source_urls` | `changed` |  |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `stay_base_id` | `changed` |  |
| `ski_area_access:davos-dorf--pischa` | `access_mode` | `changed` |  |
| `ski_area_access:davos-dorf--pischa` | `distance_m` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-dorf--pischa` | `duration_minutes` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-dorf--pischa` | `is_direct` | `changed` |  |
| `ski_area_access:davos-dorf--pischa` | `lift_distance` | `changed` |  |
| `ski_area_access:davos-dorf--pischa` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:davos-dorf--pischa` | `regional_data_ids` | `changed` |  |
| `ski_area_access:davos-dorf--pischa` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:davos-dorf--pischa` | `ski_area_id` | `changed` |  |
| `ski_area_access:davos-dorf--pischa` | `source_urls` | `changed` |  |
| `ski_area_access:davos-dorf--pischa` | `stay_base_id` | `changed` |  |
| `ski_area_access:davos-glaris--rinerhorn` | `access_mode` | `changed` |  |
| `ski_area_access:davos-glaris--rinerhorn` | `distance_m` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-glaris--rinerhorn` | `duration_minutes` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-glaris--rinerhorn` | `is_direct` | `changed` |  |
| `ski_area_access:davos-glaris--rinerhorn` | `lift_distance` | `changed` |  |
| `ski_area_access:davos-glaris--rinerhorn` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:davos-glaris--rinerhorn` | `regional_data_ids` | `changed` |  |
| `ski_area_access:davos-glaris--rinerhorn` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:davos-glaris--rinerhorn` | `ski_area_id` | `changed` |  |
| `ski_area_access:davos-glaris--rinerhorn` | `source_urls` | `changed` |  |
| `ski_area_access:davos-glaris--rinerhorn` | `stay_base_id` | `changed` |  |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `distance_m` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `duration_minutes` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `is_direct` | `changed` |  |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `lift_distance` | `changed` |  |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `nearest_lift_name` | `not-applicable` | Legacy target retired by this curation. |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `regional_data_ids` | `changed` |  |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `ski_area_id` | `changed` |  |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `stay_base_id` | `changed` |  |
| `ski_area_access:davos-platz--jakobshorn` | `access_mode` | `changed` |  |
| `ski_area_access:davos-platz--jakobshorn` | `distance_m` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-platz--jakobshorn` | `duration_minutes` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-platz--jakobshorn` | `is_direct` | `changed` |  |
| `ski_area_access:davos-platz--jakobshorn` | `lift_distance` | `changed` |  |
| `ski_area_access:davos-platz--jakobshorn` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:davos-platz--jakobshorn` | `regional_data_ids` | `changed` |  |
| `ski_area_access:davos-platz--jakobshorn` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:davos-platz--jakobshorn` | `ski_area_id` | `changed` |  |
| `ski_area_access:davos-platz--jakobshorn` | `source_urls` | `changed` |  |
| `ski_area_access:davos-platz--jakobshorn` | `stay_base_id` | `changed` |  |
| `ski_area_access:davos-platz--schatzalp-strela` | `access_mode` | `changed` |  |
| `ski_area_access:davos-platz--schatzalp-strela` | `distance_m` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-platz--schatzalp-strela` | `duration_minutes` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:davos-platz--schatzalp-strela` | `is_direct` | `changed` |  |
| `ski_area_access:davos-platz--schatzalp-strela` | `lift_distance` | `changed` |  |
| `ski_area_access:davos-platz--schatzalp-strela` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:davos-platz--schatzalp-strela` | `regional_data_ids` | `changed` |  |
| `ski_area_access:davos-platz--schatzalp-strela` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:davos-platz--schatzalp-strela` | `ski_area_id` | `changed` |  |
| `ski_area_access:davos-platz--schatzalp-strela` | `source_urls` | `changed` |  |
| `ski_area_access:davos-platz--schatzalp-strela` | `stay_base_id` | `changed` |  |
| `ski_area_access:klosters-dorf--madrisa` | `access_mode` | `changed` |  |
| `ski_area_access:klosters-dorf--madrisa` | `distance_m` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:klosters-dorf--madrisa` | `duration_minutes` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:klosters-dorf--madrisa` | `is_direct` | `changed` |  |
| `ski_area_access:klosters-dorf--madrisa` | `lift_distance` | `changed` |  |
| `ski_area_access:klosters-dorf--madrisa` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:klosters-dorf--madrisa` | `regional_data_ids` | `changed` |  |
| `ski_area_access:klosters-dorf--madrisa` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:klosters-dorf--madrisa` | `ski_area_id` | `changed` |  |
| `ski_area_access:klosters-dorf--madrisa` | `source_urls` | `changed` |  |
| `ski_area_access:klosters-dorf--madrisa` | `stay_base_id` | `changed` |  |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `access_mode` | `changed` |  |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `distance_m` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `duration_minutes` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `is_direct` | `changed` |  |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `lift_distance` | `changed` |  |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `regional_data_ids` | `changed` |  |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `ski_area_access_id` | `changed` |  |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `ski_area_id` | `changed` |  |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `source_urls` | `changed` |  |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `stay_base_id` | `changed` |  |
| `ski_region:davos-klosters` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:davos-klosters` | `name` | `reviewed-no-change` |  |
| `ski_region:davos-klosters` | `parent_ski_region_id` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `ski_region:davos-klosters` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:davos-klosters` | `source_urls` | `changed` |  |
| `stay_base:davos-dorf` | `base_character.development_style` | `changed` |  |
| `stay_base:davos-dorf` | `base_character.local_pace` | `changed` |  |
| `stay_base:davos-dorf` | `base_type` | `changed` |  |
| `stay_base:davos-dorf` | `elevation_m` | `changed` |  |
| `stay_base:davos-dorf` | `latitude` | `changed` |  |
| `stay_base:davos-dorf` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:davos-dorf` | `local_apres_profile.intensity` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `stay_base:davos-dorf` | `local_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `stay_base:davos-dorf` | `longitude` | `changed` |  |
| `stay_base:davos-dorf` | `name` | `changed` |  |
| `stay_base:davos-dorf` | `price_max` | `changed` |  |
| `stay_base:davos-dorf` | `price_min` | `changed` |  |
| `stay_base:davos-dorf` | `price_range` | `changed` |  |
| `stay_base:davos-dorf` | `quality` | `changed` |  |
| `stay_base:davos-dorf` | `regional_data_ids` | `changed` |  |
| `stay_base:davos-dorf` | `stay_base_id` | `changed` |  |
| `stay_base:davos-dorf` | `stay_destination_id` | `changed` |  |
| `stay_base:davos-glaris` | `base_character.development_style` | `changed` |  |
| `stay_base:davos-glaris` | `base_character.local_pace` | `changed` |  |
| `stay_base:davos-glaris` | `base_type` | `changed` |  |
| `stay_base:davos-glaris` | `elevation_m` | `changed` |  |
| `stay_base:davos-glaris` | `latitude` | `changed` |  |
| `stay_base:davos-glaris` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:davos-glaris` | `local_apres_profile.intensity` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `stay_base:davos-glaris` | `local_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `stay_base:davos-glaris` | `longitude` | `changed` |  |
| `stay_base:davos-glaris` | `name` | `changed` |  |
| `stay_base:davos-glaris` | `price_max` | `changed` |  |
| `stay_base:davos-glaris` | `price_min` | `changed` |  |
| `stay_base:davos-glaris` | `price_range` | `changed` |  |
| `stay_base:davos-glaris` | `quality` | `changed` |  |
| `stay_base:davos-glaris` | `regional_data_ids` | `changed` |  |
| `stay_base:davos-glaris` | `stay_base_id` | `changed` |  |
| `stay_base:davos-glaris` | `stay_destination_id` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `base_character.development_style` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `base_character.local_pace` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `base_type` | `not-applicable` | Legacy target retired by this curation. |
| `stay_base:davos-klosters-davos-platz` | `elevation_m` | `not-applicable` | Legacy target retired by this curation. |
| `stay_base:davos-klosters-davos-platz` | `latitude` | `not-applicable` | Legacy target retired by this curation. |
| `stay_base:davos-klosters-davos-platz` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `local_apres_profile.intensity` | `not-applicable` | Legacy target retired by this curation. |
| `stay_base:davos-klosters-davos-platz` | `local_apres_profile.season_label` | `not-applicable` | Legacy target retired by this curation. |
| `stay_base:davos-klosters-davos-platz` | `longitude` | `not-applicable` | Legacy target retired by this curation. |
| `stay_base:davos-klosters-davos-platz` | `name` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `price_max` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `price_min` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `price_range` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `quality` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `regional_data_ids` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `stay_base_id` | `changed` |  |
| `stay_base:davos-klosters-davos-platz` | `stay_destination_id` | `changed` |  |
| `stay_base:davos-platz` | `base_character.development_style` | `changed` |  |
| `stay_base:davos-platz` | `base_character.local_pace` | `changed` |  |
| `stay_base:davos-platz` | `base_type` | `changed` |  |
| `stay_base:davos-platz` | `elevation_m` | `changed` |  |
| `stay_base:davos-platz` | `latitude` | `changed` |  |
| `stay_base:davos-platz` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:davos-platz` | `local_apres_profile.intensity` | `changed` |  |
| `stay_base:davos-platz` | `local_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `stay_base:davos-platz` | `longitude` | `changed` |  |
| `stay_base:davos-platz` | `name` | `changed` |  |
| `stay_base:davos-platz` | `price_max` | `changed` |  |
| `stay_base:davos-platz` | `price_min` | `changed` |  |
| `stay_base:davos-platz` | `price_range` | `changed` |  |
| `stay_base:davos-platz` | `quality` | `changed` |  |
| `stay_base:davos-platz` | `regional_data_ids` | `changed` |  |
| `stay_base:davos-platz` | `stay_base_id` | `changed` |  |
| `stay_base:davos-platz` | `stay_destination_id` | `changed` |  |
| `stay_base:klosters-dorf` | `base_character.development_style` | `changed` |  |
| `stay_base:klosters-dorf` | `base_character.local_pace` | `changed` |  |
| `stay_base:klosters-dorf` | `base_type` | `changed` |  |
| `stay_base:klosters-dorf` | `elevation_m` | `changed` |  |
| `stay_base:klosters-dorf` | `latitude` | `changed` |  |
| `stay_base:klosters-dorf` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:klosters-dorf` | `local_apres_profile.intensity` | `unresolved` | No accepted owner-scoped source establishes a local après intensity. |
| `stay_base:klosters-dorf` | `local_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `stay_base:klosters-dorf` | `longitude` | `changed` |  |
| `stay_base:klosters-dorf` | `name` | `changed` |  |
| `stay_base:klosters-dorf` | `price_max` | `changed` |  |
| `stay_base:klosters-dorf` | `price_min` | `changed` |  |
| `stay_base:klosters-dorf` | `price_range` | `changed` |  |
| `stay_base:klosters-dorf` | `quality` | `changed` |  |
| `stay_base:klosters-dorf` | `regional_data_ids` | `changed` |  |
| `stay_base:klosters-dorf` | `stay_base_id` | `changed` |  |
| `stay_base:klosters-dorf` | `stay_destination_id` | `changed` |  |
| `stay_base:klosters-platz` | `base_character.development_style` | `changed` |  |
| `stay_base:klosters-platz` | `base_character.local_pace` | `changed` |  |
| `stay_base:klosters-platz` | `base_type` | `changed` |  |
| `stay_base:klosters-platz` | `elevation_m` | `changed` |  |
| `stay_base:klosters-platz` | `latitude` | `changed` |  |
| `stay_base:klosters-platz` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:klosters-platz` | `local_apres_profile.intensity` | `unresolved` | No accepted owner-scoped source establishes a local après intensity. |
| `stay_base:klosters-platz` | `local_apres_profile.season_label` | `unresolved` | No accepted owner-scoped source establishes a more specific current value. |
| `stay_base:klosters-platz` | `longitude` | `changed` |  |
| `stay_base:klosters-platz` | `name` | `changed` |  |
| `stay_base:klosters-platz` | `price_max` | `changed` |  |
| `stay_base:klosters-platz` | `price_min` | `changed` |  |
| `stay_base:klosters-platz` | `price_range` | `changed` |  |
| `stay_base:klosters-platz` | `quality` | `changed` |  |
| `stay_base:klosters-platz` | `regional_data_ids` | `changed` |  |
| `stay_base:klosters-platz` | `stay_base_id` | `changed` |  |
| `stay_base:klosters-platz` | `stay_destination_id` | `changed` |  |
| `stay_destination:davos` | `country` | `changed` |  |
| `stay_destination:davos` | `latitude` | `changed` |  |
| `stay_destination:davos` | `longitude` | `changed` |  |
| `stay_destination:davos` | `name` | `changed` |  |
| `stay_destination:davos` | `price_level` | `changed` |  |
| `stay_destination:davos` | `region` | `changed` |  |
| `stay_destination:davos` | `regional_data_ids` | `changed` |  |
| `stay_destination:davos` | `stay_destination_id` | `changed` |  |
| `stay_destination:davos` | `trip_market_region_id` | `changed` |  |
| `stay_destination:davos-klosters` | `country` | `changed` |  |
| `stay_destination:davos-klosters` | `latitude` | `changed` |  |
| `stay_destination:davos-klosters` | `longitude` | `changed` |  |
| `stay_destination:davos-klosters` | `name` | `changed` |  |
| `stay_destination:davos-klosters` | `price_level` | `changed` |  |
| `stay_destination:davos-klosters` | `region` | `changed` |  |
| `stay_destination:davos-klosters` | `regional_data_ids` | `changed` |  |
| `stay_destination:davos-klosters` | `stay_destination_id` | `changed` |  |
| `stay_destination:davos-klosters` | `trip_market_region_id` | `changed` |  |
| `stay_destination:klosters` | `country` | `changed` |  |
| `stay_destination:klosters` | `latitude` | `changed` |  |
| `stay_destination:klosters` | `longitude` | `changed` |  |
| `stay_destination:klosters` | `name` | `changed` |  |
| `stay_destination:klosters` | `price_level` | `changed` |  |
| `stay_destination:klosters` | `region` | `changed` |  |
| `stay_destination:klosters` | `regional_data_ids` | `changed` |  |
| `stay_destination:klosters` | `stay_destination_id` | `changed` |  |
| `stay_destination:klosters` | `trip_market_region_id` | `changed` |  |
| `trust_manifest:lift_pass_products:davos-klosters-regional-pass` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:davos-klosters-regional-pass` | `field_source_refs` | `changed` |  |
| `trust_manifest:lift_pass_products:davos-klosters-regional-pass` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:davos-klosters-regional-pass` | `notes` | `changed` |  |
| `trust_manifest:lift_pass_products:schatzalp-strela-ski-pass` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:schatzalp-strela-ski-pass` | `field_source_refs` | `changed` |  |
| `trust_manifest:lift_pass_products:schatzalp-strela-ski-pass` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:schatzalp-strela-ski-pass` | `notes` | `changed` |  |
| `trust_manifest:rental_display_facts:bardill-sport-shop-davos-platz` | `display_name` | `changed` |  |
| `trust_manifest:rental_display_facts:bardill-sport-shop-davos-platz` | `field_source_refs` | `changed` |  |
| `trust_manifest:rental_display_facts:bardill-sport-shop-davos-platz` | `field_statuses` | `changed` |  |
| `trust_manifest:rental_display_facts:bardill-sport-shop-davos-platz` | `notes` | `changed` |  |
| `trust_manifest:rental_display_facts:davos-klosters-bardill-sport-shop-davos` | `display_name` | `changed` |  |
| `trust_manifest:rental_display_facts:davos-klosters-bardill-sport-shop-davos` | `field_source_refs` | `changed` |  |
| `trust_manifest:rental_display_facts:davos-klosters-bardill-sport-shop-davos` | `field_statuses` | `changed` |  |
| `trust_manifest:rental_display_facts:davos-klosters-bardill-sport-shop-davos` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:davos-dorf--parsenn-gotschna` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:davos-dorf--parsenn-gotschna` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:davos-dorf--parsenn-gotschna` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:davos-dorf--parsenn-gotschna` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:davos-dorf--pischa` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:davos-dorf--pischa` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:davos-dorf--pischa` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:davos-dorf--pischa` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:davos-glaris--rinerhorn` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:davos-glaris--rinerhorn` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:davos-glaris--rinerhorn` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:davos-glaris--rinerhorn` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:davos-platz--jakobshorn` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:davos-platz--jakobshorn` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:davos-platz--jakobshorn` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:davos-platz--jakobshorn` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:davos-platz--schatzalp-strela` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:davos-platz--schatzalp-strela` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:davos-platz--schatzalp-strela` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:davos-platz--schatzalp-strela` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:klosters-dorf--madrisa` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:klosters-dorf--madrisa` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:klosters-dorf--madrisa` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:klosters-dorf--madrisa` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:klosters-platz--parsenn-gotschna` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:klosters-platz--parsenn-gotschna` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:klosters-platz--parsenn-gotschna` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:klosters-platz--parsenn-gotschna` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:davos-klosters-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:davos-klosters-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:davos-klosters-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:davos-klosters-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:jakobshorn` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:jakobshorn` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:jakobshorn` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:jakobshorn` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:madrisa` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:madrisa` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:madrisa` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:madrisa` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:parsenn-gotschna` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:parsenn-gotschna` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:parsenn-gotschna` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:parsenn-gotschna` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:pischa` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:pischa` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:pischa` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:pischa` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:rinerhorn` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:rinerhorn` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:rinerhorn` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:rinerhorn` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:schatzalp-strela` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:schatzalp-strela` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:schatzalp-strela` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:schatzalp-strela` | `notes` | `changed` |  |
| `trust_manifest:ski_regions:davos-klosters` | `display_name` | `reviewed-no-change` |  |
| `trust_manifest:ski_regions:davos-klosters` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_regions:davos-klosters` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_regions:davos-klosters` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:davos-dorf` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:davos-dorf` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:davos-dorf` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:davos-dorf` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:davos-glaris` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:davos-glaris` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:davos-glaris` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:davos-glaris` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:davos-klosters-davos-platz` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:davos-klosters-davos-platz` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:davos-klosters-davos-platz` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:davos-klosters-davos-platz` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:davos-platz` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:davos-platz` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:davos-platz` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:davos-platz` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:klosters-dorf` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:klosters-dorf` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:klosters-dorf` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:klosters-dorf` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:klosters-platz` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:klosters-platz` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:klosters-platz` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:klosters-platz` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:davos` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:davos` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:davos` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:davos` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:davos-klosters` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:davos-klosters` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:davos-klosters` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:davos-klosters` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:klosters` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:klosters` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:klosters` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:klosters` | `notes` | `changed` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:davos-klosters-regional-pass` | `available_from_stay_destination_ids` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets) | `["davos", "klosters"]` | The accepted source supports the normalized available_from_stay_destination_ids value for davos-klosters-regional-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:davos-klosters-regional-pass` | `default_for_stay_destination_ids` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets) | `["davos", "klosters"]` | The accepted source supports the normalized default_for_stay_destination_ids value for davos-klosters-regional-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:davos-klosters-regional-pass` | `external_validity_summary` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets) | `"Regional ticket covers the five Davos Klosters Mountains ski areas modeled here. The separately operated Schatzalp / Strela ski area is excluded."` | The accepted source supports the normalized external_validity_summary value for davos-klosters-regional-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:davos-klosters-regional-pass` | `lift_pass_product_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets) | `"davos-klosters-regional-pass"` | The accepted source supports the normalized lift_pass_product_id value for davos-klosters-regional-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:davos-klosters-regional-pass` | `name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets) | `"Davos Klosters regional ski pass"` | The accepted source supports the normalized name value for davos-klosters-regional-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:davos-klosters-regional-pass` | `pass_accessible_terrain` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures) | `{"metric_scope": "pass_accessible", "piste_km_by_difficulty": null, "source_urls": ["https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures"], "total_lift_count": 44, "total_piste_km": 253.0}` | The accepted source supports the normalized pass_accessible_terrain value for davos-klosters-regional-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:davos-klosters-regional-pass` | `prices` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets) | `[{"amount": 94.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 regional pass", "source_url": "https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets"}, {"amount": 230.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 regional pass", "source_url": "https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets"}, {"amount": 390.0, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 regional pass", "source_url": "https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets"}]` | The accepted source supports the normalized prices value for davos-klosters-regional-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:davos-klosters-regional-pass` | `terrain_domain_ids` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/archiv/dkm/dokumente/b2b/winter/grp-info_Winter_en.pdf) | `[]` | The accepted source supports the normalized terrain_domain_ids value for davos-klosters-regional-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:davos-klosters-regional-pass` | `valid_ski_area_ids` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/archiv/dkm/dokumente/b2b/winter/grp-info_Winter_en.pdf) | `["jakobshorn", "madrisa", "parsenn-gotschna", "pischa", "rinerhorn"]` | The accepted source supports the normalized valid_ski_area_ids value for davos-klosters-regional-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:davos-klosters-regional-pass` | `validity_scope` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/rates-tickets/ski-regional-tickets) | `"regional_network"` | The accepted source supports the normalized validity_scope value for davos-klosters-regional-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:schatzalp-strela-ski-pass` | `available_from_stay_destination_ids` | [schatzalp.ch source](https://www.schatzalp.ch/en/agb) | `["davos"]` | The accepted source supports the normalized available_from_stay_destination_ids value for schatzalp-strela-ski-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:schatzalp-strela-ski-pass` | `default_for_stay_destination_ids` | [schatzalp.ch source](https://www.schatzalp.ch/en/agb) | `[]` | The accepted source supports the normalized default_for_stay_destination_ids value for schatzalp-strela-ski-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:schatzalp-strela-ski-pass` | `external_validity_summary` | [schatzalp.ch source](https://www.schatzalp.ch/en/agb) | `"Separate private ski-area ticket; Davos Klosters Mountains regional passes are not valid at Schatzalp / Strela."` | The accepted source supports the normalized external_validity_summary value for schatzalp-strela-ski-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:schatzalp-strela-ski-pass` | `lift_pass_product_id` | [schatzalp.ch source](https://www.schatzalp.ch/en/agb) | `"schatzalp-strela-ski-pass"` | The accepted source supports the normalized lift_pass_product_id value for schatzalp-strela-ski-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:schatzalp-strela-ski-pass` | `name` | [schatzalp.ch source](https://www.schatzalp.ch/en/agb) | `"Schatzalp / Strela ski pass"` | The accepted source supports the normalized name value for schatzalp-strela-ski-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:schatzalp-strela-ski-pass` | `terrain_domain_ids` | [resources.davos.ch source](https://resources.davos.ch/fileadmin/user_upload/dokumente/broschueren_karten/Winterkarte-Schatzalp.pdf) | `[]` | The accepted source supports the normalized terrain_domain_ids value for schatzalp-strela-ski-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:schatzalp-strela-ski-pass` | `valid_ski_area_ids` | [resources.davos.ch source](https://resources.davos.ch/fileadmin/user_upload/dokumente/broschueren_karten/Winterkarte-Schatzalp.pdf) | `["schatzalp-strela"]` | The accepted source supports the normalized valid_ski_area_ids value for schatzalp-strela-ski-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `lift_pass_product:schatzalp-strela-ski-pass` | `validity_scope` | [schatzalp.ch source](https://www.schatzalp.ch/en/agb) | `"single_ski_area"` | The accepted source supports the normalized validity_scope value for schatzalp-strela-ski-pass. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"Bardill Sport Shop Davos"` | The accepted source supports the normalized name value for bardill-sport-shop-davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `rental_display_fact_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"bardill-sport-shop-davos-platz"` | The accepted source supports the normalized rental_display_fact_id value for bardill-sport-shop-davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `stay_base_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"davos-platz"` | The accepted source supports the normalized stay_base_id value for bardill-sport-shop-davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `rental_display_fact:bardill-sport-shop-davos-platz` | `stay_destination_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"davos"` | The accepted source supports the normalized stay_destination_id value for bardill-sport-shop-davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `base_elevation_m` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `1560` | The accepted source supports the normalized base_elevation_m value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/2896258648) | `46.772399` | The accepted source supports the normalized latitude value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/2896258648) | `9.8493406` | The accepted source supports the normalized longitude value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `marked_freeride_routes.availability` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"available"` | The accepted source supports the normalized marked_freeride_routes.availability value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `marked_freeride_routes.route_count` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `2` | The accepted source supports the normalized marked_freeride_routes.route_count value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"Jakobshorn"` | The accepted source supports the normalized name value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `season_end_month` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `4` | The accepted source supports the normalized season_end_month value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `season_start_month` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `11` | The accepted source supports the normalized season_start_month value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `season_windows` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `[{"end_date": "2026-11-29", "season_label": "Winter 2026/27 pre-opening", "start_date": "2026-11-27", "status": "planned"}, {"end_date": "2027-04-11", "season_label": "Winter 2026/27 main season", "start_date": "2026-12-04", "status": "planned"}]` | The accepted source supports the normalized season_windows value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"jakobshorn"` | The accepted source supports the normalized ski_area_id value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `ski_day_apres_profile.availability` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"available"` | The accepted source supports the normalized ski_day_apres_profile.availability value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `ski_day_apres_profile.intensity` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"lively"` | The accepted source supports the normalized ski_day_apres_profile.intensity value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `snow_park.availability` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"available"` | The accepted source supports the normalized snow_park.availability value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `snow_park.park_count` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `1` | The accepted source supports the normalized snow_park.park_count value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `summit_elevation_m` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `2600` | The accepted source supports the normalized summit_elevation_m value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `supported_skill_levels` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `["beginner", "intermediate", "advanced"]` | The accepted source supports the normalized supported_skill_levels value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `total_lift_count` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `12` | The accepted source supports the normalized total_lift_count value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:jakobshorn` | `total_piste_km` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `55.0` | The accepted source supports the normalized total_piste_km value for jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `base_elevation_m` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `1887` | The accepted source supports the normalized base_elevation_m value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/way/601298991) | `46.9097225` | The accepted source supports the normalized latitude value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/way/601298991) | `9.8774507` | The accepted source supports the normalized longitude value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `marked_freeride_routes.availability` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures) | `"available"` | The accepted source supports the normalized marked_freeride_routes.availability value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `marked_freeride_routes.route_count` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures) | `1` | The accepted source supports the normalized marked_freeride_routes.route_count value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `"Madrisa"` | The accepted source supports the normalized name value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `official_trail_map.url` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/archiv/dkm/dokumente/karten/Pistenplan-Madrisa.pdf) | `"https://www.davosklostersmountains.ch/archiv/dkm/dokumente/karten/Pistenplan-Madrisa.pdf"` | The accepted source supports the normalized official_trail_map.url value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `season_end_month` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `3` | The accepted source supports the normalized season_end_month value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `season_start_month` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `12` | The accepted source supports the normalized season_start_month value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `season_windows` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `[{"end_date": "2027-03-29", "season_label": "Winter 2026/27", "start_date": "2026-12-18", "status": "planned"}]` | The accepted source supports the normalized season_windows value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `"madrisa"` | The accepted source supports the normalized ski_area_id value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `summit_elevation_m` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `2611` | The accepted source supports the normalized summit_elevation_m value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `supported_skill_levels` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `["beginner", "intermediate", "advanced"]` | The accepted source supports the normalized supported_skill_levels value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:madrisa` | `total_piste_km` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `31.0` | The accepted source supports the normalized total_piste_km value for madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `base_elevation_m` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `1560` | The accepted source supports the normalized base_elevation_m value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/way/601299396) | `46.842102` | The accepted source supports the normalized latitude value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/way/601299396) | `9.8353422` | The accepted source supports the normalized longitude value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `marked_freeride_routes.availability` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures) | `"available"` | The accepted source supports the normalized marked_freeride_routes.availability value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `marked_freeride_routes.route_count` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures) | `5` | The accepted source supports the normalized marked_freeride_routes.route_count value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"Parsenn / Gotschna"` | The accepted source supports the normalized name value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `season_end_month` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `4` | The accepted source supports the normalized season_end_month value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `season_start_month` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `11` | The accepted source supports the normalized season_start_month value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `season_windows` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `[{"end_date": "2026-11-15", "season_label": "Winter 2026/27 pre-opening", "start_date": "2026-11-13", "status": "planned"}, {"end_date": "2027-04-04", "season_label": "Winter 2026/27 main season", "start_date": "2026-11-20", "status": "planned"}]` | The accepted source supports the normalized season_windows value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"parsenn-gotschna"` | The accepted source supports the normalized ski_area_id value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `summit_elevation_m` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `2844` | The accepted source supports the normalized summit_elevation_m value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `supported_skill_levels` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `["beginner", "intermediate", "advanced"]` | The accepted source supports the normalized supported_skill_levels value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `total_lift_count` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `18` | The accepted source supports the normalized total_lift_count value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:parsenn-gotschna` | `total_piste_km` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `97.0` | The accepted source supports the normalized total_piste_km value for parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `base_elevation_m` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/winter-activities/snowshoe-hiking) | `1799` | The accepted source supports the normalized base_elevation_m value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/way/601299503) | `46.805988` | The accepted source supports the normalized latitude value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/way/601299503) | `9.9084508` | The accepted source supports the normalized longitude value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `marked_freeride_routes.availability` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `"available"` | The accepted source supports the normalized marked_freeride_routes.availability value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `marked_freeride_routes.route_count` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `1` | The accepted source supports the normalized marked_freeride_routes.route_count value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `"Pischa"` | The accepted source supports the normalized name value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `season_end_month` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `3` | The accepted source supports the normalized season_end_month value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `season_start_month` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `12` | The accepted source supports the normalized season_start_month value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `season_windows` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `[{"end_date": "2027-01-17", "season_label": "Winter 2026/27 before WEF closure", "start_date": "2026-12-26", "status": "planned"}, {"end_date": "2027-03-29", "season_label": "Winter 2026/27 after WEF closure", "start_date": "2027-01-23", "status": "planned"}]` | The accepted source supports the normalized season_windows value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `"pischa"` | The accepted source supports the normalized ski_area_id value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `summit_elevation_m` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/winter-activities/snowshoe-hiking) | `2481` | The accepted source supports the normalized summit_elevation_m value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `supported_skill_levels` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `["advanced"]` | The accepted source supports the normalized supported_skill_levels value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `total_lift_count` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `1` | The accepted source supports the normalized total_lift_count value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:pischa` | `total_piste_km` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `0.0` | The accepted source supports the normalized total_piste_km value for pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `base_elevation_m` | [davos.ch source](https://www.davos.ch/entdecken/ausfluege-in-und-um-davos-klosters/umgebung-seitentaeler) | `1457` | The accepted source supports the normalized base_elevation_m value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/way/601300983) | `46.741226` | The accepted source supports the normalized latitude value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/way/601300983) | `9.7980089` | The accepted source supports the normalized longitude value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `marked_freeride_routes.availability` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures) | `"available"` | The accepted source supports the normalized marked_freeride_routes.availability value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `marked_freeride_routes.route_count` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/recent-news/company/facts-and-figures) | `3` | The accepted source supports the normalized marked_freeride_routes.route_count value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `"Rinerhorn"` | The accepted source supports the normalized name value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `night_skiing.availability` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/gastro-events/events/Rinerhorn-night-skiing-and-sledding_e_1275719) | `"available"` | The accepted source supports the normalized night_skiing.availability value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `season_end_month` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `3` | The accepted source supports the normalized season_end_month value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `season_start_month` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `12` | The accepted source supports the normalized season_start_month value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `season_windows` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/winter/live-info/current-operating-infos?active=operationTimes) | `[{"end_date": "2027-01-17", "season_label": "Winter 2026/27 before WEF closure", "start_date": "2026-12-18", "status": "planned"}, {"end_date": "2027-03-29", "season_label": "Winter 2026/27 after WEF closure", "start_date": "2027-01-23", "status": "planned"}]` | The accepted source supports the normalized season_windows value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `"rinerhorn"` | The accepted source supports the normalized ski_area_id value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `summit_elevation_m` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/archiv/dkm/dokumente/karten/Pistenplan-DKM.pdf) | `2490` | The accepted source supports the normalized summit_elevation_m value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `supported_skill_levels` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `["beginner", "intermediate", "advanced"]` | The accepted source supports the normalized supported_skill_levels value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `total_lift_count` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `5` | The accepted source supports the normalized total_lift_count value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:rinerhorn` | `total_piste_km` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `39.0` | The accepted source supports the normalized total_piste_km value for rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `base_elevation_m` | [schatzalp.ch source](https://www.schatzalp.ch/en/funicular) | `1557` | The accepted source supports the normalized base_elevation_m value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/2894011356) | `46.8013896` | The accepted source supports the normalized latitude value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/2894011356) | `9.8149673` | The accepted source supports the normalized longitude value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `name` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `"Schatzalp / Strela"` | The accepted source supports the normalized name value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `official_trail_map.url` | [resources.davos.ch source](https://resources.davos.ch/fileadmin/user_upload/dokumente/broschueren_karten/Winterkarte-Schatzalp.pdf) | `"https://resources.davos.ch/fileadmin/user_upload/dokumente/broschueren_karten/Winterkarte-Schatzalp.pdf"` | The accepted source supports the normalized official_trail_map.url value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `season_end_month` | [schatzalp.ch source](https://www.schatzalp.ch/en/funicular) | `3` | The accepted source supports the normalized season_end_month value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `season_start_month` | [schatzalp.ch source](https://www.schatzalp.ch/en/funicular) | `12` | The accepted source supports the normalized season_start_month value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `season_windows` | [schatzalp.ch source](https://www.schatzalp.ch/en/funicular) | `[]` | The accepted source supports the normalized season_windows value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `ski_area_id` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `"schatzalp-strela"` | The accepted source supports the normalized ski_area_id value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `snowmaking.availability` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `"unavailable"` | The accepted source supports the normalized snowmaking.availability value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `snowmaking.coverage_basis` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `"unknown"` | The accepted source supports the normalized snowmaking.coverage_basis value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `summit_elevation_m` | [schatzalp.ch source](https://www.schatzalp.ch/en/funicular) | `2350` | The accepted source supports the normalized summit_elevation_m value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area:schatzalp-strela` | `supported_skill_levels` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `["beginner", "intermediate"]` | The accepted source supports the normalized supported_skill_levels value for schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `access_mode` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"walk"` | The accepted source supports the normalized access_mode value for davos-dorf--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `is_direct` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `true` | The accepted source supports the normalized is_direct value for davos-dorf--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `lift_distance` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"near"` | The accepted source supports the normalized lift_distance value for davos-dorf--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `nearest_lift_name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"Parsenn funicular"` | The accepted source supports the normalized nearest_lift_name value for davos-dorf--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `regional_data_ids` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `{}` | The accepted source supports the normalized regional_data_ids value for davos-dorf--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `ski_area_access_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"davos-dorf--parsenn-gotschna"` | The accepted source supports the normalized ski_area_access_id value for davos-dorf--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"parsenn-gotschna"` | The accepted source supports the normalized ski_area_id value for davos-dorf--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `source_urls` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn"]` | The accepted source supports the normalized source_urls value for davos-dorf--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--parsenn-gotschna` | `stay_base_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"davos-dorf"` | The accepted source supports the normalized stay_base_id value for davos-dorf--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--pischa` | `access_mode` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `"ski_bus"` | The accepted source supports the normalized access_mode value for davos-dorf--pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--pischa` | `is_direct` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `false` | The accepted source supports the normalized is_direct value for davos-dorf--pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--pischa` | `lift_distance` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `"medium"` | The accepted source supports the normalized lift_distance value for davos-dorf--pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--pischa` | `nearest_lift_name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `"Pischa cable car"` | The accepted source supports the normalized nearest_lift_name value for davos-dorf--pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--pischa` | `regional_data_ids` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `{}` | The accepted source supports the normalized regional_data_ids value for davos-dorf--pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--pischa` | `ski_area_access_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `"davos-dorf--pischa"` | The accepted source supports the normalized ski_area_access_id value for davos-dorf--pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--pischa` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `"pischa"` | The accepted source supports the normalized ski_area_id value for davos-dorf--pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--pischa` | `source_urls` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `["https://www.davosklostersmountains.ch/en/mountains/mountains/pischa"]` | The accepted source supports the normalized source_urls value for davos-dorf--pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-dorf--pischa` | `stay_base_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/pischa) | `"davos-dorf"` | The accepted source supports the normalized stay_base_id value for davos-dorf--pischa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-glaris--rinerhorn` | `access_mode` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `"walk"` | The accepted source supports the normalized access_mode value for davos-glaris--rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-glaris--rinerhorn` | `is_direct` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `true` | The accepted source supports the normalized is_direct value for davos-glaris--rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-glaris--rinerhorn` | `lift_distance` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `"near"` | The accepted source supports the normalized lift_distance value for davos-glaris--rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-glaris--rinerhorn` | `nearest_lift_name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `"Rinerhorn gondola"` | The accepted source supports the normalized nearest_lift_name value for davos-glaris--rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-glaris--rinerhorn` | `regional_data_ids` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `{}` | The accepted source supports the normalized regional_data_ids value for davos-glaris--rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-glaris--rinerhorn` | `ski_area_access_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `"davos-glaris--rinerhorn"` | The accepted source supports the normalized ski_area_access_id value for davos-glaris--rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-glaris--rinerhorn` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `"rinerhorn"` | The accepted source supports the normalized ski_area_id value for davos-glaris--rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-glaris--rinerhorn` | `source_urls` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `["https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn"]` | The accepted source supports the normalized source_urls value for davos-glaris--rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-glaris--rinerhorn` | `stay_base_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/rinerhorn) | `"davos-glaris"` | The accepted source supports the normalized stay_base_id value for davos-glaris--rinerhorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--jakobshorn` | `access_mode` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"walk"` | The accepted source supports the normalized access_mode value for davos-platz--jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--jakobshorn` | `is_direct` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `true` | The accepted source supports the normalized is_direct value for davos-platz--jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--jakobshorn` | `lift_distance` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"near"` | The accepted source supports the normalized lift_distance value for davos-platz--jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--jakobshorn` | `nearest_lift_name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"Jakobshorn cable car"` | The accepted source supports the normalized nearest_lift_name value for davos-platz--jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--jakobshorn` | `regional_data_ids` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `{}` | The accepted source supports the normalized regional_data_ids value for davos-platz--jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--jakobshorn` | `ski_area_access_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"davos-platz--jakobshorn"` | The accepted source supports the normalized ski_area_access_id value for davos-platz--jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--jakobshorn` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"jakobshorn"` | The accepted source supports the normalized ski_area_id value for davos-platz--jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--jakobshorn` | `source_urls` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `["https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn"]` | The accepted source supports the normalized source_urls value for davos-platz--jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--jakobshorn` | `stay_base_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/jakobshorn) | `"davos-platz"` | The accepted source supports the normalized stay_base_id value for davos-platz--jakobshorn. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--schatzalp-strela` | `access_mode` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `"walk"` | The accepted source supports the normalized access_mode value for davos-platz--schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--schatzalp-strela` | `is_direct` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `true` | The accepted source supports the normalized is_direct value for davos-platz--schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--schatzalp-strela` | `lift_distance` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `"near"` | The accepted source supports the normalized lift_distance value for davos-platz--schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--schatzalp-strela` | `nearest_lift_name` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `"Schatzalp funicular"` | The accepted source supports the normalized nearest_lift_name value for davos-platz--schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--schatzalp-strela` | `regional_data_ids` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `{}` | The accepted source supports the normalized regional_data_ids value for davos-platz--schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--schatzalp-strela` | `ski_area_access_id` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `"davos-platz--schatzalp-strela"` | The accepted source supports the normalized ski_area_access_id value for davos-platz--schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--schatzalp-strela` | `ski_area_id` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `"schatzalp-strela"` | The accepted source supports the normalized ski_area_id value for davos-platz--schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--schatzalp-strela` | `source_urls` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `["https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela"]` | The accepted source supports the normalized source_urls value for davos-platz--schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:davos-platz--schatzalp-strela` | `stay_base_id` | [davos.ch source](https://www.davos.ch/en/discover/mountains-in-davos-klosters/schatzalp-strela) | `"davos-platz"` | The accepted source supports the normalized stay_base_id value for davos-platz--schatzalp-strela. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-dorf--madrisa` | `access_mode` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `"walk"` | The accepted source supports the normalized access_mode value for klosters-dorf--madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-dorf--madrisa` | `is_direct` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `true` | The accepted source supports the normalized is_direct value for klosters-dorf--madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-dorf--madrisa` | `lift_distance` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `"near"` | The accepted source supports the normalized lift_distance value for klosters-dorf--madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-dorf--madrisa` | `nearest_lift_name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `"Madrisa gondola"` | The accepted source supports the normalized nearest_lift_name value for klosters-dorf--madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-dorf--madrisa` | `regional_data_ids` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `{}` | The accepted source supports the normalized regional_data_ids value for klosters-dorf--madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-dorf--madrisa` | `ski_area_access_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `"klosters-dorf--madrisa"` | The accepted source supports the normalized ski_area_access_id value for klosters-dorf--madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-dorf--madrisa` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `"madrisa"` | The accepted source supports the normalized ski_area_id value for klosters-dorf--madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-dorf--madrisa` | `source_urls` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `["https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa"]` | The accepted source supports the normalized source_urls value for klosters-dorf--madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-dorf--madrisa` | `stay_base_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/madrisa) | `"klosters-dorf"` | The accepted source supports the normalized stay_base_id value for klosters-dorf--madrisa. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `access_mode` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"walk"` | The accepted source supports the normalized access_mode value for klosters-platz--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `is_direct` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `true` | The accepted source supports the normalized is_direct value for klosters-platz--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `lift_distance` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"near"` | The accepted source supports the normalized lift_distance value for klosters-platz--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `nearest_lift_name` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"Gotschna cable car"` | The accepted source supports the normalized nearest_lift_name value for klosters-platz--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `regional_data_ids` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `{}` | The accepted source supports the normalized regional_data_ids value for klosters-platz--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `ski_area_access_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"klosters-platz--parsenn-gotschna"` | The accepted source supports the normalized ski_area_access_id value for klosters-platz--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `ski_area_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"parsenn-gotschna"` | The accepted source supports the normalized ski_area_id value for klosters-platz--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `source_urls` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `["https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn"]` | The accepted source supports the normalized source_urls value for klosters-platz--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_area_access:klosters-platz--parsenn-gotschna` | `stay_base_id` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/mountains/parsenn) | `"klosters-platz"` | The accepted source supports the normalized stay_base_id value for klosters-platz--parsenn-gotschna. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `ski_region:davos-klosters` | `source_urls` | [davos.ch source](https://www.davos.ch/en/activities/snowsports/ski-snowboard) | `["https://www.davos.ch/en/activities/snowsports/ski-snowboard"]` | The accepted source supports the normalized source_urls value for davos-klosters. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-dorf` | `base_type` | [openstreetmap.org source](https://www.openstreetmap.org/node/26032383) | `"neighbourhood"` | The accepted source supports the normalized base_type value for davos-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-dorf` | `elevation_m` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `1560` | The accepted source supports the normalized elevation_m value for davos-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-dorf` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/26032383) | `46.8065596` | The accepted source supports the normalized latitude value for davos-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-dorf` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/26032383) | `9.8381801` | The accepted source supports the normalized longitude value for davos-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-dorf` | `name` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"Davos Dorf"` | The accepted source supports the normalized name value for davos-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-dorf` | `regional_data_ids` | [openstreetmap.org source](https://www.openstreetmap.org/node/26032383) | `{"osm_node_id": "26032383"}` | The accepted source supports the normalized regional_data_ids value for davos-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-dorf` | `stay_base_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"davos-dorf"` | The accepted source supports the normalized stay_base_id value for davos-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-dorf` | `stay_destination_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"davos"` | The accepted source supports the normalized stay_destination_id value for davos-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-glaris` | `base_type` | [openstreetmap.org source](https://www.openstreetmap.org/node/12853320191) | `"hamlet"` | The accepted source supports the normalized base_type value for davos-glaris. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-glaris` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/12853320191) | `46.7417217` | The accepted source supports the normalized latitude value for davos-glaris. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-glaris` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/12853320191) | `9.7775036` | The accepted source supports the normalized longitude value for davos-glaris. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-glaris` | `name` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"Davos Glaris"` | The accepted source supports the normalized name value for davos-glaris. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-glaris` | `regional_data_ids` | [openstreetmap.org source](https://www.openstreetmap.org/node/12853320191) | `{"osm_node_id": "12853320191"}` | The accepted source supports the normalized regional_data_ids value for davos-glaris. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-glaris` | `stay_base_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"davos-glaris"` | The accepted source supports the normalized stay_base_id value for davos-glaris. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-glaris` | `stay_destination_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"davos"` | The accepted source supports the normalized stay_destination_id value for davos-glaris. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `base_character.development_style` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"mixed"` | The accepted source supports the normalized base_character.development_style value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `base_character.local_pace` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"lively"` | The accepted source supports the normalized base_character.local_pace value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `base_type` | [openstreetmap.org source](https://www.openstreetmap.org/node/240072917) | `"neighbourhood"` | The accepted source supports the normalized base_type value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `elevation_m` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `1560` | The accepted source supports the normalized elevation_m value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/240072917) | `46.7933845` | The accepted source supports the normalized latitude value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `local_apres_profile.availability` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"available"` | The accepted source supports the normalized local_apres_profile.availability value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `local_apres_profile.intensity` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"destination_defining"` | The accepted source supports the normalized local_apres_profile.intensity value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/240072917) | `9.8206999` | The accepted source supports the normalized longitude value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `name` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"Davos Platz"` | The accepted source supports the normalized name value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `regional_data_ids` | [openstreetmap.org source](https://www.openstreetmap.org/node/240072917) | `{"osm_node_id": "240072917"}` | The accepted source supports the normalized regional_data_ids value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `stay_base_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"davos-platz"` | The accepted source supports the normalized stay_base_id value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:davos-platz` | `stay_destination_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"davos"` | The accepted source supports the normalized stay_destination_id value for davos-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-dorf` | `base_character.development_style` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"traditional"` | The accepted source supports the normalized base_character.development_style value for klosters-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-dorf` | `base_character.local_pace` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"quiet"` | The accepted source supports the normalized base_character.local_pace value for klosters-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-dorf` | `base_type` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"neighbourhood"` | The accepted source supports the normalized base_type value for klosters-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-dorf` | `elevation_m` | [openstreetmap.org source](https://www.openstreetmap.org/node/5370737666) | `1124` | The accepted source supports the normalized elevation_m value for klosters-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-dorf` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/5370737666) | `46.8835913` | The accepted source supports the normalized latitude value for klosters-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-dorf` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/5370737666) | `9.87523` | The accepted source supports the normalized longitude value for klosters-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-dorf` | `name` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"Klosters Dorf"` | The accepted source supports the normalized name value for klosters-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-dorf` | `regional_data_ids` | [openstreetmap.org source](https://www.openstreetmap.org/node/5370737666) | `{"osm_node_id": "5370737666"}` | The accepted source supports the normalized regional_data_ids value for klosters-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-dorf` | `stay_base_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"klosters-dorf"` | The accepted source supports the normalized stay_base_id value for klosters-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-dorf` | `stay_destination_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"klosters"` | The accepted source supports the normalized stay_destination_id value for klosters-dorf. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-platz` | `base_character.development_style` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"traditional"` | The accepted source supports the normalized base_character.development_style value for klosters-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-platz` | `base_character.local_pace` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"quiet"` | The accepted source supports the normalized base_character.local_pace value for klosters-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-platz` | `base_type` | [openstreetmap.org source](https://www.openstreetmap.org/node/240119460) | `"neighbourhood"` | The accepted source supports the normalized base_type value for klosters-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-platz` | `elevation_m` | [openstreetmap.org source](https://www.openstreetmap.org/node/240119460) | `1191` | The accepted source supports the normalized elevation_m value for klosters-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-platz` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/240119460) | `46.8682882` | The accepted source supports the normalized latitude value for klosters-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-platz` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/240119460) | `9.8821599` | The accepted source supports the normalized longitude value for klosters-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-platz` | `name` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"Klosters Platz"` | The accepted source supports the normalized name value for klosters-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-platz` | `regional_data_ids` | [openstreetmap.org source](https://www.openstreetmap.org/node/240119460) | `{"osm_node_id": "240119460"}` | The accepted source supports the normalized regional_data_ids value for klosters-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-platz` | `stay_base_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"klosters-platz"` | The accepted source supports the normalized stay_base_id value for klosters-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_base:klosters-platz` | `stay_destination_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"klosters"` | The accepted source supports the normalized stay_destination_id value for klosters-platz. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:davos` | `country` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"Switzerland"` | The accepted source supports the normalized country value for davos. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:davos` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/240072917) | `46.8027` | The accepted source supports the normalized latitude value for davos. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:davos` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/240072917) | `9.836` | The accepted source supports the normalized longitude value for davos. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:davos` | `name` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"Davos"` | The accepted source supports the normalized name value for davos. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:davos` | `region` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"Graubunden"` | The accepted source supports the normalized region value for davos. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:davos` | `regional_data_ids` | [openstreetmap.org source](https://www.openstreetmap.org/node/240072917) | `{}` | The accepted source supports the normalized regional_data_ids value for davos. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:davos` | `stay_destination_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"davos"` | Official tourism establishes Davos as an independent stay and access context. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:davos` | `trip_market_region_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `"davos-klosters"` | The accepted source supports the normalized trip_market_region_id value for davos. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:klosters` | `country` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"Switzerland"` | The accepted source supports the normalized country value for klosters. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:klosters` | `latitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/240119460) | `46.8682882` | The accepted source supports the normalized latitude value for klosters. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:klosters` | `longitude` | [openstreetmap.org source](https://www.openstreetmap.org/node/240119460) | `9.8821599` | The accepted source supports the normalized longitude value for klosters. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:klosters` | `name` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"Klosters"` | The accepted source supports the normalized name value for klosters. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:klosters` | `region` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"Graubunden"` | The accepted source supports the normalized region value for klosters. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:klosters` | `regional_data_ids` | [openstreetmap.org source](https://www.openstreetmap.org/node/240119460) | `{"osm_node_id": "240119460"}` | The accepted source supports the normalized regional_data_ids value for klosters. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:klosters` | `stay_destination_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"klosters"` | Official tourism establishes Klosters as an independent stay and access context. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:klosters` | `trip_market_region_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/klosters) | `"davos-klosters"` | The accepted source supports the normalized trip_market_region_id value for klosters. | The catalog value is normalized to Snowcast ownership, identifiers, enums, and units; it is not a verbatim transcription. |
| `stay_destination:davos-klosters` | `stay_destination_id` | [davos.ch source](https://www.davos.ch/en/information/portrait-image/davos) | `null` | Official tourism treats Davos and Klosters as distinct stay markets. | The source establishes the replacement topology; the after value is null because the legacy synthetic entity is retired. |
| `stay_base:davos-klosters-davos-platz` | `stay_base_id` | [openstreetmap.org source](https://www.openstreetmap.org/node/240072917) | `null` | The legacy destination-qualified base is replaced by the canonical Davos Platz base. | The source establishes the replacement topology; the after value is null because the legacy synthetic entity is retired. |
| `ski_area:davos-klosters-ski-area` | `ski_area_id` | [davos.ch source](https://www.davos.ch/en/activities/snowsports/ski-snowboard) | `null` | Official tourism presents six distinct ski areas rather than one connected aggregate area. | The source establishes the replacement topology; the after value is null because the legacy synthetic entity is retired. |
| `ski_area_access:davos-klosters-davos-platz--davos-klosters-ski-area` | `ski_area_access_id` | [davos.ch source](https://www.davos.ch/en/activities/snowsports/ski-snowboard) | `null` | The synthetic aggregate access edge is replaced by exact base-to-area relationships. | The source establishes the replacement topology; the after value is null because the legacy synthetic entity is retired. |
| `stay_base:davos-glaris` | `elevation_m` | [davos.ch source](https://www.davos.ch/entdecken/ausfluege-in-und-um-davos-klosters/umgebung-seitentaeler) | `1457` | Official tourism gives the exact Glaris elevation and describes its traditional Walser settlement character. | The local pace is a cautious Snowcast normalization of the official settlement description; elevation is transcribed in metres. |
| `stay_base:davos-glaris` | `base_character.development_style` | [davos.ch source](https://www.davos.ch/entdecken/ausfluege-in-und-um-davos-klosters/umgebung-seitentaeler) | `"traditional"` | Official tourism gives the exact Glaris elevation and describes its traditional Walser settlement character. | The local pace is a cautious Snowcast normalization of the official settlement description; elevation is transcribed in metres. |
| `stay_base:davos-glaris` | `base_character.local_pace` | [davos.ch source](https://www.davos.ch/entdecken/ausfluege-in-und-um-davos-klosters/umgebung-seitentaeler) | `"quiet"` | Official tourism gives the exact Glaris elevation and describes its traditional Walser settlement character. | The local pace is a cautious Snowcast normalization of the official settlement description; elevation is transcribed in metres. |
| `ski_area:rinerhorn` | `night_skiing.season_label` | [davosklostersmountains.ch source](https://www.davosklostersmountains.ch/en/mountains/gastro-events/events/Rinerhorn-night-skiing-and-sledding_e_1275719) | `"Winter 2026/27"` | The official recurring Rinerhorn night-skiing schedule publishes dates for Winter 2026/27. | The dated recurring schedule is normalized to the Winter 2026/27 season label; it is not a one-off event inference. |

## Boundary Decisions

- `davos`: `pass`
- `klosters`: `pass`

## Ranking Impact

The corrected graph lets search and planning compare the actual Davos and Klosters stay contexts, exact feeder relationships, child-area terrain and season facts, and the proper regional-versus-private pass coverage. Product-curated lodging estimates remain explicitly estimated.

## Verification

- `UV_PROJECT_ENVIRONMENT=/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv uv run --no-config --no-sync python -m app.data.validate_catalog_curation typed docs/catalog-curation/2026-06-27-davos-klosters-full-curation.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output docs/catalog-curation/2026-06-27-davos-klosters-full-curation.md`
- `UV_PROJECT_ENVIRONMENT=/Users/awownysz/repos/personal_projects/ai-sports-travel-planner/.venv uv run --no-config --no-sync python -m app.data.validate_catalog_curation reconcile docs/catalog-curation/2026-06-27-davos-klosters-full-curation.json --base-catalog-path /tmp/pr20-main-catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path /tmp/pr20-main-trust.json --current-trust-manifest-path app/data/resort_trust_manifest.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output docs/catalog-curation/2026-06-27-davos-klosters-full-curation.md`

## Caveats

- Difficulty kilometre splits remain unresolved where current official child totals conflict with the separate difficulty-and-marked-route inventory; marked routes are not folded into groomed-piste difficulty buckets.
- Madrisa total lift count remains unresolved because official presentations enumerate facilities differently.
- Schatzalp / Strela exact ski-area season window, terrain totals and current representative ski-pass prices remain unresolved; the funicular schedule is not treated as an exact ski-area schedule.
- The retired aggregate ski-area ID had no rows in the reviewed local weather, condition, climatology, trip or companion tables. New child IDs require normal future weather backfill; no historical evidence migration is performed.
