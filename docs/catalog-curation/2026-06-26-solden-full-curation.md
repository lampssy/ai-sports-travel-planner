# Sölden Catalog Curation - normalized model migration

Migrates PR #13 onto the normalized Snowcast catalog. Facts are assigned to explicit regions, stay destinations, stay bases, ski areas, access edges, terrain domains, pass products, and rental facts. Source-aware v2 enrichment follow-up: Reviewed Sölden's new ski-area and stay-base facts against official Bergbahnen Sölden and destination sources. Added snowmaking, two glacier ski areas, AREA 47 Snowpark, scheduled night skiing, marked ski-route availability, the official map, ski-day apres, village elevation, lively pace, and local apres while leaving unsupported snowmaking coverage and a route count unresolved.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `lift_pass_product:otztal-super-skipass` | `full` | all canonical fields |
| `lift_pass_product:solden-skipass` | `full` | all canonical fields |
| `rental_display_fact:solden-grizzly-sports` | `full` | all canonical fields |
| `ski_area:solden-ski-area` | `full` | all canonical fields |
| `ski_area_access:solden-solden--solden-ski-area` | `full` | all canonical fields |
| `ski_region:solden` | `full` | all canonical fields |
| `stay_base:solden-solden` | `full` | all canonical fields |
| `stay_destination:solden` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `full` | all canonical fields |
| `trust_manifest:lift_pass_products:solden-skipass` | `full` | all canonical fields |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_areas:solden-ski-area` | `full` | all canonical fields |
| `trust_manifest:ski_regions:solden` | `full` | all canonical fields |
| `trust_manifest:stay_bases:solden-solden` | `full` | all canonical fields |
| `trust_manifest:stay_destinations:solden` | `full` | all canonical fields |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:otztal-super-skipass` | `available_from_stay_destination_ids` | `null` | `["solden"]` | `estimated` | no |
| `lift_pass_product:otztal-super-skipass` | `default_for_stay_destination_ids` | `null` | `[]` | `estimated` | no |
| `lift_pass_product:otztal-super-skipass` | `external_validity_summary` | `null` | `"From 3 days, Sölden ski passes automatically cover all six Ötztal ski areas; Snowcast currently models only Sölden locally."` | `estimated` | no |
| `lift_pass_product:otztal-super-skipass` | `lift_pass_product_id` | `null` | `"otztal-super-skipass"` | `estimated` | no |
| `lift_pass_product:otztal-super-skipass` | `name` | `null` | `"Ötztal Super Ski Pass"` | `estimated` | no |
| `lift_pass_product:otztal-super-skipass` | `prices` | `null` | `[{"amount": 251.5, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 peak season cash desk", "source_url": "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"}, {"amount": 478.5, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 peak season cash desk", "source_url": "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"}]` | `estimated` | no |
| `lift_pass_product:otztal-super-skipass` | `terrain_domain_ids` | `null` | `[]` | `estimated` | no |
| `lift_pass_product:otztal-super-skipass` | `valid_ski_area_ids` | `null` | `["solden-ski-area"]` | `estimated` | no |
| `lift_pass_product:otztal-super-skipass` | `validity_scope` | `null` | `"regional_network"` | `estimated` | no |
| `lift_pass_product:solden-skipass` | `available_from_stay_destination_ids` | `null` | `["solden"]` | `estimated` | no |
| `lift_pass_product:solden-skipass` | `default_for_stay_destination_ids` | `null` | `["solden"]` | `estimated` | no |
| `lift_pass_product:solden-skipass` | `lift_pass_product_id` | `null` | `"solden-skipass"` | `estimated` | no |
| `lift_pass_product:solden-skipass` | `name` | `null` | `"Sölden Skipass"` | `estimated` | no |
| `lift_pass_product:solden-skipass` | `prices` | `null` | `[{"amount": 171.5, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 2, "price_kind": "fixed", "season_label": "Winter 2026/27 peak season cash desk", "source_url": "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"}, {"amount": 86.5, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 peak season cash desk", "source_url": "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"}]` | `estimated` | no |
| `lift_pass_product:solden-skipass` | `terrain_domain_ids` | `null` | `[]` | `estimated` | no |
| `lift_pass_product:solden-skipass` | `valid_ski_area_ids` | `null` | `["solden-ski-area"]` | `estimated` | no |
| `lift_pass_product:solden-skipass` | `validity_scope` | `null` | `"single_ski_area"` | `estimated` | no |
| `ski_area:solden-ski-area` | `glacier_terrain.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:solden-ski-area` | `marked_freeride_routes.availability` | `"unknown"` | `"available"` | `verified_with_adjustment` | no |
| `ski_area:solden-ski-area` | `name` | `"Solden"` | `"Sölden"` | `verified_with_adjustment` | no |
| `ski_area:solden-ski-area` | `night_skiing.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:solden-ski-area` | `night_skiing.season_label` | `null` | `"2025/26"` | `verified_with_adjustment` | no |
| `ski_area:solden-ski-area` | `official_trail_map.url` | `null` | `"https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes"` | `verified` | no |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.advanced` | `null` | `31.4` | `verified_with_adjustment` | yes |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.beginner` | `null` | `76.4` | `verified_with_adjustment` | yes |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.intermediate` | `null` | `37.8` | `verified_with_adjustment` | yes |
| `ski_area:solden-ski-area` | `season_start_month` | `11` | `9` | `verified_with_adjustment` | yes |
| `ski_area:solden-ski-area` | `season_windows` | `[]` | `[{"end_date": "2026-11-11", "season_label": "Fall 2026 glacier skiing", "start_date": "2026-09-25", "status": "planned"}, {"end_date": "2027-04-18", "season_label": "Winter 2026/27", "start_date": "2026-11-12", "status": "planned"}, {"end_date": "2027-05-02", "season_label": "Spring 2027 glacier skiing", "start_date": "2027-04-19", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `ski_area:solden-ski-area` | `snow_park.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:solden-ski-area` | `snow_park.park_count` | `null` | `1` | `verified` | no |
| `ski_area:solden-ski-area` | `snowmaking.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:solden-ski-area` | `supported_skill_levels` | `["intermediate", "advanced"]` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:solden-ski-area` | `total_lift_count` | `null` | `31` | `verified` | yes |
| `ski_area:solden-ski-area` | `total_piste_km` | `null` | `146.0` | `verified` | yes |
| `ski_area_access:solden-solden--solden-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:solden-solden--solden-ski-area` | `nearest_lift_name` | `null` | `"Giggijochbahn / Gaislachkoglbahn I"` | `verified_with_adjustment` | no |
| `ski_area_access:solden-solden--solden-ski-area` | `source_urls` | `["https://www.bergfex.com/soelden/"]` | `["https://www.bergfex.com/soelden/", "https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423"]` | `verified_with_adjustment` | no |
| `ski_region:solden` | `name` | `"Solden"` | `"Sölden"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `base_character.local_pace` | `"unknown"` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `base_type` | `null` | `"village"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `elevation_m` | `null` | `1377` | `verified` | no |
| `stay_base:solden-solden` | `latitude` | `null` | `46.9666` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `local_apres_profile.availability` | `"unknown"` | `"available"` | `verified` | no |
| `stay_base:solden-solden` | `local_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `longitude` | `null` | `11.0073` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `name` | `"Solden"` | `"Sölden"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `regional_data_ids` | `{}` | `{"osm_relation_id": "77772"}` | `verified_with_adjustment` | no |
| `stay_destination:solden` | `name` | `"Solden"` | `"Sölden"` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `display_name` | `null` | `"Ötztal Super Ski Pass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `field_source_refs` | `null` | `{"coverage": ["https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/29330800", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423", "https://www.soelden.com/en/region-villages/soelden-a-z/grizzley-sports.i-5dfbcae7-c289-4786-a410-8910af0c2403", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/3-days-otztal.lt-209052", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/6-days-otztal.lt-209064"], "identity_scope_availability": ["https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/29330800", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423", "https://www.soelden.com/en/region-villages/soelden-a-z/grizzley-sports.i-5dfbcae7-c289-4786-a410-8910af0c2403", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/3-days-otztal.lt-209052", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/6-days-otztal.lt-209064"], "pass_accessible_terrain": ["https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/29330800", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423", "https://www.soelden.com/en/region-villages/soelden-a-z/grizzley-sports.i-5dfbcae7-c289-4786-a410-8910af0c2403", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/3-days-otztal.lt-209052", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/6-days-otztal.lt-209064"], "prices": ["https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/29330800", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423", "https://www.soelden.com/en/region-villages/soelden-a-z/grizzley-sports.i-5dfbcae7-c289-4786-a410-8910af0c2403", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/3-days-otztal.lt-209052", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/6-days-otztal.lt-209064"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `field_statuses` | `null` | `{"coverage": "estimated", "identity_scope_availability": "estimated", "pass_accessible_terrain": "needs_source", "prices": "estimated"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `notes` | `null` | `["PR #13 legacy curation was translated onto normalized catalog ownership and relationships."]` | `estimated` | no |
| `trust_manifest:lift_pass_products:solden-skipass` | `display_name` | `null` | `"Sölden Skipass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:solden-skipass` | `field_source_refs` | `null` | `{"coverage": ["https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/29330800", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423", "https://www.soelden.com/en/region-villages/soelden-a-z/grizzley-sports.i-5dfbcae7-c289-4786-a410-8910af0c2403", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/3-days-otztal.lt-209052", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/6-days-otztal.lt-209064"], "identity_scope_availability": ["https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/29330800", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423", "https://www.soelden.com/en/region-villages/soelden-a-z/grizzley-sports.i-5dfbcae7-c289-4786-a410-8910af0c2403", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/3-days-otztal.lt-209052", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/6-days-otztal.lt-209064"], "pass_accessible_terrain": ["https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/29330800", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423", "https://www.soelden.com/en/region-villages/soelden-a-z/grizzley-sports.i-5dfbcae7-c289-4786-a410-8910af0c2403", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/3-days-otztal.lt-209052", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/6-days-otztal.lt-209064"], "prices": ["https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/29330800", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423", "https://www.soelden.com/en/region-villages/soelden-a-z/grizzley-sports.i-5dfbcae7-c289-4786-a410-8910af0c2403", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/3-days-otztal.lt-209052", "https://www.soelden.com/en/search-book/ski-mountain-lift-tickets/ticket-overview/6-days-otztal.lt-209064"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:solden-skipass` | `field_statuses` | `null` | `{"coverage": "estimated", "identity_scope_availability": "estimated", "pass_accessible_terrain": "needs_source", "prices": "estimated"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:solden-skipass` | `notes` | `null` | `["PR #13 legacy curation was translated onto normalized catalog ownership and relationships."]` | `estimated` | no |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `display_name` | `"Solden -> Solden"` | `"Sölden -> Sölden"` | `estimated` | no |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/soelden/"], "relationship": ["https://www.bergfex.com/soelden/"]}` | `{"access_mode_distance": ["https://www.bergfex.com/soelden/", "https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423"], "relationship": ["https://www.bergfex.com/soelden/", "https://www.openstreetmap.org/relation/77772", "https://www.openstreetmap.org/way/92100602", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "estimated"}` | `estimated` | no |
| `trust_manifest:ski_areas:solden-ski-area` | `display_name` | `"Solden"` | `"Sölden"` | `estimated` | no |
| `trust_manifest:ski_areas:solden-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund"], "glacier_terrain": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information"], "identity_coordinates": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund"], "marked_freeride_routes": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes"], "night_skiing": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/further-tickets"], "official_documents": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes"], "ski_day_apres": ["https://www.soelden.com/en/region-villages/soelden-a-z/bergzauber.i-38deba50-4e3e-4977-8f71-bd6c705a0bfd"], "skill_fit": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund"], "snow_park": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/highlights-in-the-ski-area/snowpark-funslopes-funcross"], "snowmaking": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information"], "terrain_metrics": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund"]}` | `estimated` | no |
| `trust_manifest:ski_areas:solden-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "verified", "identity_coordinates": "verified_with_adjustment", "marked_freeride_routes": "verified_with_adjustment", "night_skiing": "verified", "official_documents": "verified", "ski_day_apres": "verified_with_adjustment", "skill_fit": "estimated", "snow_park": "verified", "snowmaking": "verified", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:solden-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner.", "Source-aware v2 enrichment reviewed official Sölden ski-area sources on 2026-07-04.", "The official 100% snow-guarantee claim was not reused as snowmaking coverage."]` | `needs_source` | no |
| `trust_manifest:ski_regions:solden` | `display_name` | `"Solden"` | `"Sölden"` | `estimated` | no |
| `trust_manifest:ski_regions:solden` | `field_source_refs` | `{"identity": [], "membership_context": []}` | `{"identity": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding"], "membership_context": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding"]}` | `estimated` | no |
| `trust_manifest:ski_regions:solden` | `field_statuses` | `{"identity": "needs_source", "membership_context": "estimated"}` | `{"identity": "verified_with_adjustment", "membership_context": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:solden-solden` | `display_name` | `"Solden"` | `"Sölden"` | `estimated` | no |
| `trust_manifest:stay_bases:solden-solden` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `{"base_character": ["https://www.soelden.com/en/region-villages"], "base_type": [], "coordinates": ["https://www.openstreetmap.org/relation/77772", "https://www.soelden.com/en/activities/winter/skiing-snowboarding"], "elevation": ["https://ext.soelden.com/prospekte/pdf/en_huettenwandern.pdf"], "identity_ownership": ["https://www.openstreetmap.org/relation/77772", "https://www.soelden.com/en/activities/winter/skiing-snowboarding"], "local_apres": ["https://www.soelden.com/en/region-villages", "https://www.soelden.com/en/region-villages/soelden-a-z/fire-ice.i-8823bf5b-30d6-4c56-b5c4-3e4d5bf6a5bd"], "lodging_price_quality": ["https://www.openstreetmap.org/relation/77772", "https://www.soelden.com/en/activities/winter/skiing-snowboarding"]}` | `estimated` | no |
| `trust_manifest:stay_bases:solden-solden` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `{"base_character": "verified_with_adjustment", "base_type": "needs_source", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified_with_adjustment", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:solden-solden` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner.", "Source-aware v2 enrichment reviewed official Sölden elevation, village identity, and nightlife sources on 2026-07-04."]` | `needs_source` | no |
| `trust_manifest:stay_destinations:solden` | `display_name` | `"Solden"` | `"Sölden"` | `estimated` | no |
| `trust_manifest:stay_destinations:solden` | `field_source_refs` | `{"coordinates": [], "identity_location": [], "price_level": []}` | `{"coordinates": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding"], "identity_location": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding"], "price_level": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding"]}` | `estimated` | no |
| `trust_manifest:stay_destinations:solden` | `field_statuses` | `{"coordinates": "needs_source", "identity_location": "needs_source", "price_level": "estimated"}` | `{"coordinates": "needs_source", "identity_location": "verified_with_adjustment", "price_level": "estimated"}` | `estimated` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `lift_pass_product:otztal-super-skipass` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:otztal-super-skipass` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:otztal-super-skipass` | `external_validity_summary` | `changed` |  |
| `lift_pass_product:otztal-super-skipass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:otztal-super-skipass` | `name` | `changed` |  |
| `lift_pass_product:otztal-super-skipass` | `pass_accessible_terrain` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `lift_pass_product:otztal-super-skipass` | `prices` | `changed` |  |
| `lift_pass_product:otztal-super-skipass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:otztal-super-skipass` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:otztal-super-skipass` | `validity_scope` | `changed` |  |
| `lift_pass_product:solden-skipass` | `available_from_stay_destination_ids` | `changed` |  |
| `lift_pass_product:solden-skipass` | `default_for_stay_destination_ids` | `changed` |  |
| `lift_pass_product:solden-skipass` | `external_validity_summary` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `lift_pass_product:solden-skipass` | `lift_pass_product_id` | `changed` |  |
| `lift_pass_product:solden-skipass` | `name` | `changed` |  |
| `lift_pass_product:solden-skipass` | `pass_accessible_terrain` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `lift_pass_product:solden-skipass` | `prices` | `changed` |  |
| `lift_pass_product:solden-skipass` | `terrain_domain_ids` | `changed` |  |
| `lift_pass_product:solden-skipass` | `valid_ski_area_ids` | `changed` |  |
| `lift_pass_product:solden-skipass` | `validity_scope` | `changed` |  |
| `rental_display_fact:solden-grizzly-sports` | `lift_distance` | `reviewed-no-change` |  |
| `rental_display_fact:solden-grizzly-sports` | `name` | `reviewed-no-change` |  |
| `rental_display_fact:solden-grizzly-sports` | `price_max` | `reviewed-no-change` |  |
| `rental_display_fact:solden-grizzly-sports` | `price_min` | `reviewed-no-change` |  |
| `rental_display_fact:solden-grizzly-sports` | `price_range` | `reviewed-no-change` |  |
| `rental_display_fact:solden-grizzly-sports` | `quality` | `reviewed-no-change` |  |
| `rental_display_fact:solden-grizzly-sports` | `rental_display_fact_id` | `reviewed-no-change` |  |
| `rental_display_fact:solden-grizzly-sports` | `stay_base_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `rental_display_fact:solden-grizzly-sports` | `stay_destination_id` | `reviewed-no-change` |  |
| `ski_area:solden-ski-area` | `base_elevation_m` | `reviewed-no-change` |  |
| `ski_area:solden-ski-area` | `glacier_terrain.availability` | `changed` | The operator explicitly identifies two connected glacier ski areas, Rettenbachferner and Tiefenbachferner. |
| `ski_area:solden-ski-area` | `latitude` | `reviewed-no-change` |  |
| `ski_area:solden-ski-area` | `longitude` | `reviewed-no-change` |  |
| `ski_area:solden-ski-area` | `marked_freeride_routes.availability` | `changed` | The official interactive map explicitly includes marked, avalanche-protected, ungroomed ski routes. |
| `ski_area:solden-ski-area` | `marked_freeride_routes.route_count` | `unresolved` | Official Sölden ski-area sources were reviewed, but they did not establish this exact value; it remains unknown rather than being inferred from marketing language or adjacent Ötztal areas. |
| `ski_area:solden-ski-area` | `marked_freeride_routes.season_label` | `unresolved` | Official Sölden ski-area sources were reviewed, but they did not establish this exact value; it remains unknown rather than being inferred from marketing language or adjacent Ötztal areas. |
| `ski_area:solden-ski-area` | `name` | `changed` |  |
| `ski_area:solden-ski-area` | `night_skiing.availability` | `changed` | The official ticket page advertises Wednesday night skiing on a floodlit piste at Gaislachkogl. |
| `ski_area:solden-ski-area` | `night_skiing.season_label` | `changed` | The published schedule runs from late December to late March within winter 2025/26. |
| `ski_area:solden-ski-area` | `official_trail_map.season_label` | `unresolved` | Official Sölden ski-area sources were reviewed, but they did not establish this exact value; it remains unknown rather than being inferred from marketing language or adjacent Ötztal areas. |
| `ski_area:solden-ski-area` | `official_trail_map.url` | `changed` | Official interactive Sölden ski-area map and download page. |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:solden-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:solden-ski-area` | `season_start_month` | `changed` |  |
| `ski_area:solden-ski-area` | `season_windows` | `changed` |  |
| `ski_area:solden-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.availability` | `changed` | The official directory identifies slope-side apres venues including Bergzauber. |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.intensity` | `changed` | Multiple slope-side venues and lively post-ski use support a lively classification. |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.season_label` | `unresolved` | Official Sölden ski-area sources were reviewed, but they did not establish this exact value; it remains unknown rather than being inferred from marketing language or adjacent Ötztal areas. |
| `ski_area:solden-ski-area` | `snow_park.availability` | `changed` | The official page documents AREA 47 Snow Park Sölden. |
| `ski_area:solden-ski-area` | `snow_park.park_count` | `changed` | The scoped official inventory names one dedicated snowpark. |
| `ski_area:solden-ski-area` | `snow_park.season_label` | `unresolved` | Official Sölden ski-area sources were reviewed, but they did not establish this exact value; it remains unknown rather than being inferred from marketing language or adjacent Ötztal areas. |
| `ski_area:solden-ski-area` | `snowmaking.availability` | `changed` | The official ski-area page explicitly cites modern snowmaking systems. |
| `ski_area:solden-ski-area` | `snowmaking.coverage_basis` | `unresolved` | Official Sölden ski-area sources were reviewed, but they did not establish this exact value; it remains unknown rather than being inferred from marketing language or adjacent Ötztal areas. |
| `ski_area:solden-ski-area` | `snowmaking.coverage_pct` | `unresolved` | Official Sölden ski-area sources were reviewed, but they did not establish this exact value; it remains unknown rather than being inferred from marketing language or adjacent Ötztal areas. |
| `ski_area:solden-ski-area` | `snowmaking.season_label` | `unresolved` | Official Sölden ski-area sources were reviewed, but they did not establish this exact value; it remains unknown rather than being inferred from marketing language or adjacent Ötztal areas. |
| `ski_area:solden-ski-area` | `summit_elevation_m` | `reviewed-no-change` |  |
| `ski_area:solden-ski-area` | `supported_skill_levels` | `changed` |  |
| `ski_area:solden-ski-area` | `total_lift_count` | `changed` |  |
| `ski_area:solden-ski-area` | `total_piste_km` | `changed` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `distance_m` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area_access:solden-solden--solden-ski-area` | `duration_minutes` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area_access:solden-solden--solden-ski-area` | `is_direct` | `reviewed-no-change` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `lift_distance` | `reviewed-no-change` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `regional_data_ids` | `reviewed-no-change` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `ski_area_access_id` | `reviewed-no-change` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `stay_base_id` | `reviewed-no-change` |  |
| `ski_region:solden` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:solden` | `name` | `changed` |  |
| `ski_region:solden` | `parent_ski_region_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `ski_region:solden` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:solden` | `source_urls` | `reviewed-no-change` |  |
| `stay_base:solden-solden` | `base_character.development_style` | `unresolved` | Official Sölden destination sources were reviewed, but they did not establish this exact stay-base value; it remains unknown rather than being inferred. |
| `stay_base:solden-solden` | `base_character.local_pace` | `changed` | The official destination calls Sölden an urban-lifestyle homebase active by day and night. |
| `stay_base:solden-solden` | `base_type` | `changed` |  |
| `stay_base:solden-solden` | `elevation_m` | `changed` | Official destination material places Sölden at 1,377 m. |
| `stay_base:solden-solden` | `latitude` | `changed` |  |
| `stay_base:solden-solden` | `local_apres_profile.availability` | `changed` | The official directory inventories large apres and nightlife venues in central Sölden. |
| `stay_base:solden-solden` | `local_apres_profile.intensity` | `changed` | Official destination material foregrounds nightlife, bars, and an active day-and-night identity. |
| `stay_base:solden-solden` | `local_apres_profile.season_label` | `unresolved` | Official Sölden destination sources were reviewed, but they did not establish this exact stay-base value; it remains unknown rather than being inferred. |
| `stay_base:solden-solden` | `longitude` | `changed` |  |
| `stay_base:solden-solden` | `name` | `changed` |  |
| `stay_base:solden-solden` | `price_max` | `reviewed-no-change` |  |
| `stay_base:solden-solden` | `price_min` | `reviewed-no-change` |  |
| `stay_base:solden-solden` | `price_range` | `reviewed-no-change` |  |
| `stay_base:solden-solden` | `quality` | `reviewed-no-change` |  |
| `stay_base:solden-solden` | `regional_data_ids` | `changed` |  |
| `stay_base:solden-solden` | `stay_base_id` | `reviewed-no-change` |  |
| `stay_base:solden-solden` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:solden` | `country` | `reviewed-no-change` |  |
| `stay_destination:solden` | `latitude` | `reviewed-no-change` |  |
| `stay_destination:solden` | `longitude` | `reviewed-no-change` |  |
| `stay_destination:solden` | `name` | `changed` |  |
| `stay_destination:solden` | `price_level` | `reviewed-no-change` |  |
| `stay_destination:solden` | `region` | `reviewed-no-change` |  |
| `stay_destination:solden` | `regional_data_ids` | `reviewed-no-change` |  |
| `stay_destination:solden` | `stay_destination_id` | `reviewed-no-change` |  |
| `stay_destination:solden` | `trip_market_region_id` | `reviewed-no-change` |  |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `field_source_refs` | `changed` |  |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `notes` | `changed` |  |
| `trust_manifest:lift_pass_products:solden-skipass` | `display_name` | `changed` |  |
| `trust_manifest:lift_pass_products:solden-skipass` | `field_source_refs` | `changed` |  |
| `trust_manifest:lift_pass_products:solden-skipass` | `field_statuses` | `changed` |  |
| `trust_manifest:lift_pass_products:solden-skipass` | `notes` | `changed` |  |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:ski_areas:solden-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:solden-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:solden-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:solden-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_regions:solden` | `display_name` | `changed` |  |
| `trust_manifest:ski_regions:solden` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_regions:solden` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_regions:solden` | `notes` | `reviewed-no-change` |  |
| `trust_manifest:stay_bases:solden-solden` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:solden-solden` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:solden-solden` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:solden-solden` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:solden` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:solden` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:solden` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:solden` | `notes` | `reviewed-no-change` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `ski_area:solden-ski-area` | `name` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | Official ski-area page uses the Sölden spelling. |  |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.advanced` | [FAQ & Refund](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund) | `{"black": 23.0, "blue": 76.4, "fun_park": 1.7, "red": 37.8, "ski_routes": 6.7}` | Official FAQ gives blue, red, black, ski-route, and fun-park kilometres for Sölden. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.beginner` | [FAQ & Refund](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund) | `{"black": 23.0, "blue": 76.4, "fun_park": 1.7, "red": 37.8, "ski_routes": 6.7}` | Official FAQ gives blue, red, black, ski-route, and fun-park kilometres for Sölden. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.intermediate` | [FAQ & Refund](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund) | `{"black": 23.0, "blue": 76.4, "fun_park": 1.7, "red": 37.8, "ski_routes": 6.7}` | Official FAQ gives blue, red, black, ski-route, and fun-park kilometres for Sölden. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:solden-ski-area` | `season_start_month` | [Ski passes & prices](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices) | `9` | Official 2026/27 season table starts glacier skiing on 25 September 2026. |  |
| `ski_area:solden-ski-area` | `season_windows` | [Ski passes & prices](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices) | `[{"end_date": "2026-11-11", "season_label": "Fall 2026 glacier skiing", "start_date": "2026-09-25", "status": "planned"}, {"end_date": "2027-04-18", "season_label": "Winter 2026/27", "start_date": "2026-11-12", "status": "planned"}, {"end_date": "2027-05-02", "season_label": "Spring 2027 glacier skiing", "start_date": "2027-04-19", "status": "planned"}]` | Official 2026/27 table lists the Sölden glacier/winter operating windows used for the ski-area weather entity. |  |
| `ski_area:solden-ski-area` | `supported_skill_levels` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | Official ski-area page uses the Sölden spelling. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area:solden-ski-area` | `total_lift_count` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `31` | Official ski-area page lists 31 mountain lifts. |  |
| `ski_area:solden-ski-area` | `total_piste_km` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `146.0` | Official ski-area page lists 146 slope kilometers. |  |
| `ski_area_access:solden-solden--solden-ski-area` | `access_mode` | [Giggijochbahn](https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423) | `"Bus stop: Sölden Giggijochbahn (2 minutes on foot)"` | Official Giggijochbahn page places the access point directly in Sölden with a two-minute walk from the named bus stop. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:solden-solden--solden-ski-area` | `nearest_lift_name` | [Giggijochbahn](https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423) | `"Giggijochbahn"` | Official Sölden A-Z page identifies Giggijochbahn and its valley station address in Sölden. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:solden-solden--solden-ski-area` | `source_urls` | [Giggijochbahn](https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423) | `"Bus stop: Sölden Giggijochbahn (2 minutes on foot)"` | Official Giggijochbahn page places the access point directly in Sölden with a two-minute walk from the named bus stop. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_region:solden` | `name` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | Official resort page uses the Sölden spelling. |  |
| `stay_base:solden-solden` | `base_type` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden resort village"` | Official ski-area page presents Sölden as the valley base for the ski area. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:solden-solden` | `latitude` | [OpenStreetMap relation 77772](https://www.openstreetmap.org/relation/77772) | `46.9666319` | OpenStreetMap administrative relation provides the Sölden centroid latitude. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:solden-solden` | `longitude` | [OpenStreetMap relation 77772](https://www.openstreetmap.org/relation/77772) | `11.0072845` | OpenStreetMap administrative relation provides the Sölden centroid longitude. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:solden-solden` | `name` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | Official resort page uses the Sölden spelling for the stay base. |  |
| `stay_base:solden-solden` | `regional_data_ids` | [OpenStreetMap relation 77772](https://www.openstreetmap.org/relation/77772) | `{"osm_relation_id": "77772"}` | OpenStreetMap relation id is stored for future regional-data joins. |  |
| `stay_destination:solden` | `name` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | Official resort page uses the Sölden spelling. |  |
| `stay_destination:solden` | `name` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | The normalized migration retains the already reviewed destination boundary. |  |
| `ski_area:solden-ski-area` | `glacier_terrain.availability` | [Sölden ski-area information](https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information) | `"available"` | The operator explicitly identifies two connected glacier ski areas, Rettenbachferner and Tiefenbachferner. |  |
| `ski_area:solden-ski-area` | `marked_freeride_routes.availability` | [Sölden ski-area map, lifts and slopes](https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes) | `"available"` | The official interactive map explicitly includes marked, avalanche-protected, ungroomed ski routes. | The operator's ski-route definition is mapped to marked freeride-route availability. |
| `ski_area:solden-ski-area` | `night_skiing.availability` | [Sölden night skiing tickets](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/further-tickets) | `"available"` | The official ticket page advertises Wednesday night skiing on a floodlit piste at Gaislachkogl. |  |
| `ski_area:solden-ski-area` | `night_skiing.season_label` | [Sölden night skiing tickets](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/further-tickets) | `"2025/26"` | The published schedule runs from late December to late March within winter 2025/26. | The dated operating window is normalized to 2025/26. |
| `ski_area:solden-ski-area` | `official_trail_map.url` | [Sölden ski-area map, lifts and slopes](https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes) | `"https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes"` | Official interactive Sölden ski-area map and download page. |  |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.availability` | [Bergzauber slope-side apres](https://www.soelden.com/en/region-villages/soelden-a-z/bergzauber.i-38deba50-4e3e-4977-8f71-bd6c705a0bfd) | `"available"` | The official directory identifies slope-side apres venues including Bergzauber. |  |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.intensity` | [Bergzauber slope-side apres](https://www.soelden.com/en/region-villages/soelden-a-z/bergzauber.i-38deba50-4e3e-4977-8f71-bd6c705a0bfd) | `"lively"` | Multiple slope-side venues and lively post-ski use support a lively classification. | The official venue offer is mapped to lively. |
| `ski_area:solden-ski-area` | `snow_park.availability` | [Sölden snowpark and fun slopes](https://www.soelden.com/en/activities/winter/skiing-snowboarding/highlights-in-the-ski-area/snowpark-funslopes-funcross) | `"available"` | The official page documents AREA 47 Snow Park Sölden. |  |
| `ski_area:solden-ski-area` | `snow_park.park_count` | [Sölden snowpark and fun slopes](https://www.soelden.com/en/activities/winter/skiing-snowboarding/highlights-in-the-ski-area/snowpark-funslopes-funcross) | `1` | The scoped official inventory names one dedicated snowpark. |  |
| `ski_area:solden-ski-area` | `snowmaking.availability` | [Sölden ski-area information](https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information) | `"available"` | The official ski-area page explicitly cites modern snowmaking systems. |  |
| `stay_base:solden-solden` | `base_character.local_pace` | [Sölden region and villages](https://www.soelden.com/en/region-villages) | `"lively"` | The official destination calls Sölden an urban-lifestyle homebase active by day and night. | The explicit urban and nightlife positioning is mapped to lively. |
| `stay_base:solden-solden` | `elevation_m` | [Official Sölden hiking brochure](https://ext.soelden.com/prospekte/pdf/en_huettenwandern.pdf) | `1377` | Official destination material places Sölden at 1,377 m. |  |
| `stay_base:solden-solden` | `local_apres_profile.availability` | [Fire and Ice Sölden](https://www.soelden.com/en/region-villages/soelden-a-z/fire-ice.i-8823bf5b-30d6-4c56-b5c4-3e4d5bf6a5bd) | `"available"` | The official directory inventories large apres and nightlife venues in central Sölden. |  |
| `stay_base:solden-solden` | `local_apres_profile.intensity` | [Sölden region and villages](https://www.soelden.com/en/region-villages) | `"lively"` | Official destination material foregrounds nightlife, bars, and an active day-and-night identity. | The broad nightlife offer is mapped to lively. |

## Boundary Decisions

- `solden`: `pass`

## Ranking Impact

Ranking-relevant facts now attach to the normalized ski-area, stay-base, and access-edge owners; Search V3 scoring policy is unchanged.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation typed REPORT.json --markdown-output REPORT.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation reconcile REPORT.json --base-catalog-path BASE/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json`

## Caveats

- Peak-season cash-desk prices are used as representative reviewed examples because Sölden uses dynamic online pricing and lower online rates vary by booking date.
- Piste difficulty buckets include official ski-route and fun-park kilometres in advanced because the current schema has no separate ski-route or fun-park bucket.
- Accommodation/rental price ranges and quality tiers remain product-curated estimates pending a reviewed provider sampling policy.
- Source-aware v2 enrichment follow-up: The official 100% figure is a snow-guarantee claim, not a snowmaking-coverage percentage, so coverage remains null.
- Source-aware v2 enrichment follow-up: The official map confirms marked ski routes but does not expose a complete stable route count in the reviewed page text.
- Source-aware v2 enrichment follow-up: Official destination material supports an urban, lively pace but does not cleanly classify the village's development style, which remains unknown.
