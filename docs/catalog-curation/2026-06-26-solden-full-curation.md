# Sölden Catalog Curation - normalized model migration

Expanded Sölden from its legacy placeholder into a full source-aware catalog curation. The review-fix pass corrects Top Season pass labels, keeps the conflicting 146/147 km official terrain totals explicit, leaves the incompatible difficulty split unresolved, aligns base-type trust, classifies the village's documented inherited and resort-era development as mixed, removes the stale night-ski season label, strengthens ski-day apres evidence, and normalizes one Giggijochbahn access endpoint with OSM geometry.

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
| `lift_pass_product:otztal-super-skipass` | `available_from_stay_destination_ids` | `null` | `["solden"]` | `verified_with_adjustment` | no |
| `lift_pass_product:otztal-super-skipass` | `default_for_stay_destination_ids` | `null` | `[]` | `estimated` | no |
| `lift_pass_product:otztal-super-skipass` | `external_validity_summary` | `null` | `"From 3 days, Sölden ski passes automatically cover all six Ötztal ski areas; Snowcast currently models only Sölden locally."` | `verified_with_adjustment` | no |
| `lift_pass_product:otztal-super-skipass` | `lift_pass_product_id` | `null` | `"otztal-super-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:otztal-super-skipass` | `name` | `null` | `"Ötztal Super Ski Pass"` | `verified_with_adjustment` | no |
| `lift_pass_product:otztal-super-skipass` | `prices` | `null` | `[{"amount": 251.5, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 top season cash desk", "source_url": "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"}, {"amount": 478.5, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 top season cash desk", "source_url": "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"}]` | `verified` | no |
| `lift_pass_product:otztal-super-skipass` | `terrain_domain_ids` | `null` | `[]` | `estimated` | no |
| `lift_pass_product:otztal-super-skipass` | `valid_ski_area_ids` | `null` | `["solden-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:otztal-super-skipass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `lift_pass_product:solden-skipass` | `available_from_stay_destination_ids` | `null` | `["solden"]` | `verified_with_adjustment` | no |
| `lift_pass_product:solden-skipass` | `default_for_stay_destination_ids` | `null` | `["solden"]` | `estimated` | no |
| `lift_pass_product:solden-skipass` | `lift_pass_product_id` | `null` | `"solden-skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:solden-skipass` | `name` | `null` | `"Sölden Skipass"` | `verified_with_adjustment` | no |
| `lift_pass_product:solden-skipass` | `prices` | `null` | `[{"amount": 86.5, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 top season cash desk", "source_url": "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"}, {"amount": 171.5, "amount_max": null, "amount_min": null, "audience": "adult", "currency": "EUR", "duration_days": 2, "price_kind": "fixed", "season_label": "Winter 2026/27 top season cash desk", "source_url": "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"}]` | `verified` | no |
| `lift_pass_product:solden-skipass` | `terrain_domain_ids` | `null` | `[]` | `estimated` | no |
| `lift_pass_product:solden-skipass` | `valid_ski_area_ids` | `null` | `["solden-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:solden-skipass` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | no |
| `ski_area:solden-ski-area` | `glacier_terrain.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:solden-ski-area` | `marked_freeride_routes.availability` | `"unknown"` | `"available"` | `verified_with_adjustment` | no |
| `ski_area:solden-ski-area` | `name` | `"Solden"` | `"Sölden"` | `verified_with_adjustment` | no |
| `ski_area:solden-ski-area` | `night_skiing.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:solden-ski-area` | `official_trail_map.url` | `null` | `"https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes"` | `verified` | no |
| `ski_area:solden-ski-area` | `season_start_month` | `11` | `9` | `verified_with_adjustment` | yes |
| `ski_area:solden-ski-area` | `season_windows` | `[]` | `[{"end_date": "2026-11-11", "season_label": "Fall 2026 glacier skiing", "start_date": "2026-09-25", "status": "planned"}, {"end_date": "2027-04-18", "season_label": "Winter 2026/27", "start_date": "2026-11-12", "status": "planned"}, {"end_date": "2027-05-02", "season_label": "Spring 2027 glacier skiing", "start_date": "2027-04-19", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `ski_area:solden-ski-area` | `snow_park.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:solden-ski-area` | `snow_park.park_count` | `null` | `1` | `verified` | no |
| `ski_area:solden-ski-area` | `snowmaking.availability` | `"unknown"` | `"available"` | `verified` | no |
| `ski_area:solden-ski-area` | `supported_skill_levels` | `["intermediate", "advanced"]` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `ski_area:solden-ski-area` | `total_lift_count` | `null` | `31` | `verified` | yes |
| `ski_area:solden-ski-area` | `total_piste_km` | `null` | `146.0` | `verified_with_adjustment` | yes |
| `ski_area_access:solden-solden--solden-ski-area` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `ski_area_access:solden-solden--solden-ski-area` | `distance_m` | `null` | `661` | `verified_with_adjustment` | yes |
| `ski_area_access:solden-solden--solden-ski-area` | `nearest_lift_name` | `null` | `"Giggijochbahn"` | `verified_with_adjustment` | no |
| `ski_area_access:solden-solden--solden-ski-area` | `regional_data_ids` | `{}` | `{"osm_node_id": "322677891", "osm_way_id": "29330800"}` | `verified_with_adjustment` | no |
| `ski_area_access:solden-solden--solden-ski-area` | `source_urls` | `["https://www.bergfex.com/soelden/"]` | `["https://www.openstreetmap.org/node/322677891", "https://www.openstreetmap.org/way/29330800", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423"]` | `verified_with_adjustment` | no |
| `ski_region:solden` | `name` | `"Solden"` | `"Sölden"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `base_character.development_style` | `"unknown"` | `"mixed"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `base_character.local_pace` | `"unknown"` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `base_type` | `null` | `"village"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `elevation_m` | `null` | `1377` | `verified` | no |
| `stay_base:solden-solden` | `latitude` | `null` | `46.9666` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `local_apres_profile.availability` | `"unknown"` | `"available"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `local_apres_profile.intensity` | `null` | `"lively"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `longitude` | `null` | `11.0073` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `name` | `"Solden"` | `"Sölden"` | `verified_with_adjustment` | no |
| `stay_base:solden-solden` | `regional_data_ids` | `{}` | `{"osm_relation_id": "77772"}` | `verified_with_adjustment` | no |
| `stay_destination:solden` | `name` | `"Solden"` | `"Sölden"` | `verified_with_adjustment` | no |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `display_name` | `null` | `"Ötztal Super Ski Pass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `field_source_refs` | `null` | `{"coverage": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"], "identity_scope_availability": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"], "pass_accessible_terrain": [], "prices": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "verified"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:otztal-super-skipass` | `notes` | `null` | `["Official 2026/27 tariff material establishes that passes from 3 days cover all six Ötztal ski areas; Snowcast currently links only the modeled Sölden ski area and keeps the remaining coverage in external_validity_summary.", "Representative 3-day and 6-day adult cash-desk prices use the official Top Season band (19 December 2026 to 6 January 2027 and 30 January to 26 February 2027)."]` | `estimated` | no |
| `trust_manifest:lift_pass_products:solden-skipass` | `display_name` | `null` | `"Sölden Skipass"` | `estimated` | no |
| `trust_manifest:lift_pass_products:solden-skipass` | `field_source_refs` | `null` | `{"coverage": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"], "identity_scope_availability": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"], "pass_accessible_terrain": [], "prices": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter"]}` | `estimated` | no |
| `trust_manifest:lift_pass_products:solden-skipass` | `field_statuses` | `null` | `{"coverage": "verified_with_adjustment", "identity_scope_availability": "verified_with_adjustment", "pass_accessible_terrain": "needs_source", "prices": "verified"}` | `estimated` | no |
| `trust_manifest:lift_pass_products:solden-skipass` | `notes` | `null` | `["Official 2026/27 tariff material establishes that passes up to 2 days are valid only in the Sölden ski area.", "Representative 1-day and 2-day adult cash-desk prices use the official Top Season band (19 December 2026 to 6 January 2027 and 30 January to 26 February 2027)."]` | `estimated` | no |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `display_name` | `"Solden -> Solden"` | `"Sölden -> Sölden"` | `estimated` | no |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `field_source_refs` | `{"access_mode_distance": ["https://www.bergfex.com/soelden/"], "relationship": ["https://www.bergfex.com/soelden/"]}` | `{"access_mode_distance": ["https://www.openstreetmap.org/node/322677891", "https://www.openstreetmap.org/way/29330800", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423"], "relationship": ["https://www.openstreetmap.org/node/322677891", "https://www.openstreetmap.org/way/29330800", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423"]}` | `estimated` | no |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `field_statuses` | `{"access_mode_distance": "estimated", "relationship": "estimated"}` | `{"access_mode_distance": "verified_with_adjustment", "relationship": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Provider-backed relationship remains estimated; no exact distance or duration is asserted."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Giggijochbahn is the nearest reviewed feeder lift to the representative Sölden stay-base coordinate.", "The 661 m distance is a reviewed Haversine calculation from OSM relation 77772's representative coordinate to OSM valley-station node 322677891; it is not a routed walking distance.", "Official lift placement and OSM geometry are normalized to walk access; no walking duration is asserted."]` | `estimated` | no |
| `trust_manifest:ski_areas:solden-ski-area` | `display_name` | `"Solden"` | `"Sölden"` | `estimated` | no |
| `trust_manifest:ski_areas:solden-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices"], "glacier_terrain": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information"], "identity_coordinates": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding"], "marked_freeride_routes": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes"], "night_skiing": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/further-tickets"], "official_documents": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes"], "ski_day_apres": ["https://www.soelden.com/en/region-villages/nightlife-apre-ski", "https://www.soelden.com/en/region-villages/soelden-a-z/bergzauber.i-38deba50-4e3e-4977-8f71-bd6c705a0bfd", "https://www.soelden.com/en/region-villages/soelden-a-z/marco-s.i-55bc8680-ee96-433c-a4c5-5b79916b9a18"], "skill_fit": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund"], "snow_park": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding/highlights-in-the-ski-area/snowpark-funslopes-funcross"], "snowmaking": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding"], "terrain_metrics": ["https://www.soelden.com/en/activities/winter/skiing-snowboarding", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes", "https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund"]}` | `estimated` | no |
| `trust_manifest:ski_areas:solden-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "verified", "identity_coordinates": "estimated", "marked_freeride_routes": "verified_with_adjustment", "night_skiing": "verified", "official_documents": "verified", "ski_day_apres": "verified_with_adjustment", "skill_fit": "verified_with_adjustment", "snow_park": "verified", "snowmaking": "verified", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:solden-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Official Sölden ski-area sources were rechecked on 2026-07-06; the existing ski-area coordinates remain an estimated weather lookup point rather than a newly verified geometry fact.", "The detailed official FAQ and ski-map inventory publish 146 km while broad official marketing pages publish 147 km; Snowcast retains 146 km with verified-with-adjustment trust because the detailed same-scope inventory is more specific.", "The official blue, red, and black pistes total 137.2 km while the 146 km headline also includes 6.7 km of ski routes and 1.7 km of fun-park terrain; piste_km_by_difficulty remains null because the current schema cannot preserve those separate categories without misclassifying them as advanced pistes.", "Official all-skill-level wording is normalized to beginner, intermediate, and advanced support.", "The current recurring night-skiing page is seasonless, so availability is verified while season_label remains null.", "Multiple official ski-area and valley-run apres venues plus the official broad apres inventory support the lively ski-day normalization."]` | `estimated` | no |
| `trust_manifest:ski_regions:solden` | `display_name` | `"Solden"` | `"Sölden"` | `estimated` | no |
| `trust_manifest:ski_regions:solden` | `field_source_refs` | `{"identity": [], "membership_context": []}` | `{"identity": ["https://www.soelden.com/en/region-villages"], "membership_context": ["https://www.soelden.com/en/region-villages"]}` | `estimated` | no |
| `trust_manifest:ski_regions:solden` | `field_statuses` | `{"identity": "needs_source", "membership_context": "estimated"}` | `{"identity": "verified_with_adjustment", "membership_context": "estimated"}` | `estimated` | no |
| `trust_manifest:ski_regions:solden` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Trip-market membership is retained as reviewed migration context and remains estimated.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Trip-market membership is retained as reviewed migration context and remains estimated.", "Official destination material establishes the Sölden region identity; the normalized trip-market membership remains product-curated."]` | `estimated` | no |
| `trust_manifest:stay_bases:solden-solden` | `display_name` | `"Solden"` | `"Sölden"` | `estimated` | no |
| `trust_manifest:stay_bases:solden-solden` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `{"base_character": ["https://bergbahnen.soelden.com/en/about-us/company-history", "https://www.soelden.com/en/region-villages", "https://www.soelden.gv.at/"], "base_type": ["https://www.soelden.com/en/region-villages/villages/soelden"], "coordinates": ["https://www.openstreetmap.org/relation/77772"], "elevation": ["https://www.soelden.com/en/region-villages/villages/soelden"], "identity_ownership": ["https://www.openstreetmap.org/relation/77772", "https://www.soelden.com/en/region-villages/villages/soelden"], "local_apres": ["https://www.soelden.com/en/region-villages", "https://www.soelden.com/en/region-villages/nightlife-apre-ski", "https://www.soelden.com/en/region-villages/soelden-a-z/fire-ice.i-8823bf5b-30d6-4c56-b5c4-3e4d5bf6a5bd"], "lodging_price_quality": []}` | `estimated` | no |
| `trust_manifest:stay_bases:solden-solden` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "verified_with_adjustment", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_bases:solden-solden` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Official Sölden village material establishes the structural village type and 1,377 m base elevation; OSM relation 77772 provides the representative settlement geometry.", "Official municipal history describes Sölden's evolution from a mountain-farming settlement into an international tourism destination, while the lift-company history documents substantial resort-era development from 1948 onward; this combination is normalized to mixed development style.", "Official destination and nightlife material is normalized to a lively local pace and lively local apres profile."]` | `estimated` | no |
| `trust_manifest:stay_destinations:solden` | `display_name` | `"Solden"` | `"Sölden"` | `estimated` | no |
| `trust_manifest:stay_destinations:solden` | `field_source_refs` | `{"coordinates": [], "identity_location": [], "price_level": []}` | `{"coordinates": [], "identity_location": ["https://www.soelden.com/en/region-villages/villages/soelden"], "price_level": []}` | `estimated` | no |
| `trust_manifest:stay_destinations:solden` | `field_statuses` | `{"coordinates": "needs_source", "identity_location": "needs_source", "price_level": "estimated"}` | `{"coordinates": "needs_source", "identity_location": "verified_with_adjustment", "price_level": "estimated"}` | `estimated` | no |
| `trust_manifest:stay_destinations:solden` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Official destination material establishes Sölden as the bookable village context; destination coordinates and price level retain their previous trust states."]` | `estimated` | no |

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
| `ski_area:solden-ski-area` | `night_skiing.season_label` | `unresolved` | The current recurring night-skiing page publishes no season-specific label. |
| `ski_area:solden-ski-area` | `official_trail_map.season_label` | `unresolved` | Official Sölden ski-area sources were reviewed, but they did not establish this exact value; it remains unknown rather than being inferred from marketing language or adjacent Ötztal areas. |
| `ski_area:solden-ski-area` | `official_trail_map.url` | `changed` | Official interactive Sölden ski-area map and download page. |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | Official blue/red/black pistes total 137.2 km, while the 146 km headline also includes 6.7 km of ski routes and 1.7 km of fun-park terrain. The current schema cannot preserve the separate categories without misclassifying them as advanced. |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | Official blue/red/black pistes total 137.2 km, while the 146 km headline also includes 6.7 km of ski routes and 1.7 km of fun-park terrain. The current schema cannot preserve the separate categories without misclassifying them as advanced. |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | Official blue/red/black pistes total 137.2 km, while the 146 km headline also includes 6.7 km of ski routes and 1.7 km of fun-park terrain. The current schema cannot preserve the separate categories without misclassifying them as advanced. |
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
| `ski_area:solden-ski-area` | `total_piste_km` | `changed` | Retains the detailed official FAQ and ski-map value of 146 km; broad official marketing pages currently publish 147 km and are preserved as a conflict. |
| `ski_area_access:solden-solden--solden-ski-area` | `access_mode` | `changed` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `distance_m` | `changed` | Reviewed 661 m Haversine distance from the Sölden stay-base coordinate to OSM Giggijochbahn valley-station node 322677891. |
| `ski_area_access:solden-solden--solden-ski-area` | `duration_minutes` | `unresolved` | Reviewed sources did not resolve this exact value. |
| `ski_area_access:solden-solden--solden-ski-area` | `is_direct` | `reviewed-no-change` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `lift_distance` | `reviewed-no-change` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `nearest_lift_name` | `changed` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `regional_data_ids` | `changed` | Stores matching Giggijochbahn OSM valley-station node and lift way provenance. |
| `ski_area_access:solden-solden--solden-ski-area` | `ski_area_access_id` | `reviewed-no-change` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `source_urls` | `changed` |  |
| `ski_area_access:solden-solden--solden-ski-area` | `stay_base_id` | `reviewed-no-change` |  |
| `ski_region:solden` | `grouping_policy` | `reviewed-no-change` |  |
| `ski_region:solden` | `name` | `changed` |  |
| `ski_region:solden` | `parent_ski_region_id` | `not-applicable` | Optional field is not applicable to this reviewed entity. |
| `ski_region:solden` | `ski_region_id` | `reviewed-no-change` |  |
| `ski_region:solden` | `source_urls` | `reviewed-no-change` |  |
| `stay_base:solden-solden` | `base_character.development_style` | `changed` | Official municipal and lift-company histories establish both the pre-ski settlement and substantial resort-era development. |
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
| `trust_manifest:ski_area_access:solden-solden--solden-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_areas:solden-ski-area` | `display_name` | `changed` |  |
| `trust_manifest:ski_areas:solden-ski-area` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_areas:solden-ski-area` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_areas:solden-ski-area` | `notes` | `changed` |  |
| `trust_manifest:ski_regions:solden` | `display_name` | `changed` |  |
| `trust_manifest:ski_regions:solden` | `field_source_refs` | `changed` |  |
| `trust_manifest:ski_regions:solden` | `field_statuses` | `changed` |  |
| `trust_manifest:ski_regions:solden` | `notes` | `changed` |  |
| `trust_manifest:stay_bases:solden-solden` | `display_name` | `changed` |  |
| `trust_manifest:stay_bases:solden-solden` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_bases:solden-solden` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_bases:solden-solden` | `notes` | `changed` |  |
| `trust_manifest:stay_destinations:solden` | `display_name` | `changed` |  |
| `trust_manifest:stay_destinations:solden` | `field_source_refs` | `changed` |  |
| `trust_manifest:stay_destinations:solden` | `field_statuses` | `changed` |  |
| `trust_manifest:stay_destinations:solden` | `notes` | `changed` |  |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:otztal-super-skipass` | `available_from_stay_destination_ids` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `["solden"]` | The Sölden operator publishes the regional product as the automatic product from three days. |  |
| `lift_pass_product:otztal-super-skipass` | `external_validity_summary` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `"From 3 days, Sölden ski passes automatically cover all six Ötztal ski areas; Snowcast currently models only Sölden locally."` | The official tariff lists Sölden, Obergurgl-Hochgurgl, Hochötz-Kühtai, Vent, Niederthai and Gries for passes from three days. | The six-area official coverage is summarized while only the modeled Sölden ski area is stored as a local catalog relationship. |
| `lift_pass_product:otztal-super-skipass` | `lift_pass_product_id` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `"Ötztal Super Skipass"` | The official tariff names the regional product used from three days. | The official product name is normalized to the stable catalog ID otztal-super-skipass. |
| `lift_pass_product:otztal-super-skipass` | `name` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `"Ötztal Super Ski Pass"` | The official tariff identifies the Ötztal regional ski-pass product. |  |
| `lift_pass_product:otztal-super-skipass` | `prices` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `{"band": "Top Season", "cash_desk_adult_prices": [{"adult_eur": 251.5, "duration_days": 3}, {"adult_eur": 478.5, "duration_days": 6}], "dates": ["2026-12-19/2027-01-06", "2027-01-30/2027-02-26"]}` | The official tariff supplies exact adult cash-desk prices for the selected representative durations and Top Season date bands. | The official tariff rows are normalized into Snowcast price objects with adult audience, EUR currency, fixed cash-desk price kind, exact duration, and Top Season label. |
| `lift_pass_product:otztal-super-skipass` | `valid_ski_area_ids` | [Sölden FAQ and lift-ticket validity](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund) | `["solden-ski-area"]` | The official validity statement includes the modeled Sölden ski area; additional Ötztal areas are not yet modeled locally. | Only modeled coverage is stored in valid_ski_area_ids; unmodeled regional coverage remains in external_validity_summary. |
| `lift_pass_product:otztal-super-skipass` | `validity_scope` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `"from 3 days: all Ötztal ski areas"` | The official tariff defines the product boundary by duration. | The official multi-area validity is normalized to regional_network. |
| `lift_pass_product:solden-skipass` | `available_from_stay_destination_ids` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `["solden"]` | The Sölden operator publishes and sells this product for the Sölden stay market. |  |
| `lift_pass_product:solden-skipass` | `lift_pass_product_id` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `"Sölden Skipass"` | The official tariff names the Sölden-only short-duration product. | The official product name is normalized to the stable catalog ID solden-skipass. |
| `lift_pass_product:solden-skipass` | `name` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `"Sölden Skipass"` | The official tariff identifies the Sölden ski-pass product. |  |
| `lift_pass_product:solden-skipass` | `prices` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `{"band": "Top Season", "cash_desk_adult_prices": [{"adult_eur": 86.5, "duration_days": 1}, {"adult_eur": 171.5, "duration_days": 2}], "dates": ["2026-12-19/2027-01-06", "2027-01-30/2027-02-26"]}` | The official tariff supplies exact adult cash-desk prices for the selected representative durations and Top Season date bands. | The official tariff rows are normalized into Snowcast price objects with adult audience, EUR currency, fixed cash-desk price kind, exact duration, and Top Season label. |
| `lift_pass_product:solden-skipass` | `valid_ski_area_ids` | [Sölden FAQ and lift-ticket validity](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund) | `["solden-ski-area"]` | The official validity statement restricts short-duration passes to the modeled Sölden ski area. |  |
| `lift_pass_product:solden-skipass` | `validity_scope` | [Sölden winter 2026/27 tariff](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/winter) | `"up to 2 days: Sölden only"` | The official tariff defines the product boundary by duration. | The official duration-based product is normalized to single_ski_area. |
| `ski_area:solden-ski-area` | `glacier_terrain.availability` | [Sölden ski-area information](https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information) | `"available"` | The operator explicitly identifies two connected glacier ski areas, Rettenbachferner and Tiefenbachferner. |  |
| `ski_area:solden-ski-area` | `marked_freeride_routes.availability` | [Sölden ski-area map, lifts and slopes](https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes) | `"available"` | The official interactive map explicitly includes marked, avalanche-protected, ungroomed ski routes. | The operator's ski-route definition is mapped to marked freeride-route availability. |
| `ski_area:solden-ski-area` | `name` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | Official ski-area page uses the Sölden spelling. |  |
| `ski_area:solden-ski-area` | `night_skiing.availability` | [Sölden night skiing tickets](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/further-tickets) | `"available"` | The official ticket page advertises Wednesday night skiing on a floodlit piste at Gaislachkogl. |  |
| `ski_area:solden-ski-area` | `night_skiing.season_label` | [Sölden night skiing tickets](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/further-tickets) | `null` | The current recurring page gives a late-December through late-March schedule without naming a season. | Availability is retained, but season_label remains null rather than carrying forward 2025/26. |
| `ski_area:solden-ski-area` | `official_trail_map.url` | [Sölden ski-area map, lifts and slopes](https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes) | `"https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information/ski-area-map-lifts-slopes"` | Official interactive Sölden ski-area map and download page. |  |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.advanced` | [Sölden FAQ and terrain breakdown](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund) | `{"black": 23.0, "blue": 76.4, "fun_park": 1.7, "red": 37.8, "ski_routes": 6.7}` | The official detailed inventory publishes blue, red and black pistes separately from ski routes and fun-park terrain. | The normalized difficulty split remains unresolved because its three buckets cannot represent the separately published route and fun-park categories while satisfying the current total-consistency contract. |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.beginner` | [Sölden FAQ and terrain breakdown](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund) | `{"black": 23.0, "blue": 76.4, "fun_park": 1.7, "red": 37.8, "ski_routes": 6.7}` | The official detailed inventory publishes blue, red and black pistes separately from ski routes and fun-park terrain. | The normalized difficulty split remains unresolved because its three buckets cannot represent the separately published route and fun-park categories while satisfying the current total-consistency contract. |
| `ski_area:solden-ski-area` | `piste_km_by_difficulty.intermediate` | [Sölden FAQ and terrain breakdown](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund) | `{"black": 23.0, "blue": 76.4, "fun_park": 1.7, "red": 37.8, "ski_routes": 6.7}` | The official detailed inventory publishes blue, red and black pistes separately from ski routes and fun-park terrain. | The normalized difficulty split remains unresolved because its three buckets cannot represent the separately published route and fun-park categories while satisfying the current total-consistency contract. |
| `ski_area:solden-ski-area` | `season_start_month` | [Ski passes & prices](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices) | `9` | Official 2026/27 season table starts glacier skiing on 25 September 2026. |  |
| `ski_area:solden-ski-area` | `season_windows` | [Ski passes & prices](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices) | `[{"end_date": "2026-11-11", "season_label": "Fall 2026 glacier skiing", "start_date": "2026-09-25", "status": "planned"}, {"end_date": "2027-04-18", "season_label": "Winter 2026/27", "start_date": "2026-11-12", "status": "planned"}, {"end_date": "2027-05-02", "season_label": "Spring 2027 glacier skiing", "start_date": "2027-04-19", "status": "planned"}]` | Official 2026/27 table lists the Sölden glacier/winter operating windows used for the ski-area weather entity. |  |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.availability` | [Bergzauber](https://www.soelden.com/en/region-villages/soelden-a-z/bergzauber.i-38deba50-4e3e-4977-8f71-bd6c705a0bfd) | `"slope-side apres venue on the Gaislachkogl valley run"` | The official directory confirms a ski-day apres venue directly on a Sölden valley run. | The exact official venue listing is normalized to ski-day apres availability. |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.intensity` | [Sölden nightlife and apres-ski](https://www.soelden.com/en/region-villages/nightlife-apre-ski) | `"lively nightlife with many party locations and apres-ski venues"` | The official destination presents a broad, lively apres scene with many locations. | The broad official scene description is combined with multiple exact ski-area and valley-run venue listings and normalized to lively. |
| `ski_area:solden-ski-area` | `ski_day_apres_profile.intensity` | [Marco's](https://www.soelden.com/en/region-villages/soelden-a-z/marco-s.i-55bc8680-ee96-433c-a4c5-5b79916b9a18) | `"large apres venue reached directly from the Giggijoch run with live music"` | The official listing corroborates active post-ski use, capacity and recurring entertainment at another ski-run venue. | Used as corroboration for the area-wide lively classification, not as a sole-source intensity claim. |
| `ski_area:solden-ski-area` | `snow_park.availability` | [Sölden snowpark and fun slopes](https://www.soelden.com/en/activities/winter/skiing-snowboarding/highlights-in-the-ski-area/snowpark-funslopes-funcross) | `"available"` | The official page documents AREA 47 Snow Park Sölden. |  |
| `ski_area:solden-ski-area` | `snow_park.park_count` | [Sölden snowpark and fun slopes](https://www.soelden.com/en/activities/winter/skiing-snowboarding/highlights-in-the-ski-area/snowpark-funslopes-funcross) | `1` | The scoped official inventory names one dedicated snowpark. |  |
| `ski_area:solden-ski-area` | `snowmaking.availability` | [Sölden ski-area information](https://www.soelden.com/en/activities/winter/skiing-snowboarding/ski-area-information) | `"available"` | The official ski-area page explicitly cites modern snowmaking systems. |  |
| `ski_area:solden-ski-area` | `supported_skill_levels` | [Sölden FAQ and terrain breakdown](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund) | `"terrain for all skill levels, from beginner slopes to demanding descents"` | The official FAQ explicitly describes beginner through demanding terrain. | Official wording is normalized to Snowcast's beginner, intermediate and advanced vocabulary. |
| `ski_area:solden-ski-area` | `total_lift_count` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `31` | Official ski-area page lists 31 mountain lifts. |  |
| `ski_area:solden-ski-area` | `total_piste_km` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `147.0` | The current broad official ski-area marketing page publishes 147 km for the same ski-area scope. | This same-scope official conflict is preserved; the detailed FAQ and ski-map inventory take precedence for the stored 146 km value. |
| `ski_area:solden-ski-area` | `total_piste_km` | [Sölden FAQ and terrain breakdown](https://www.soelden.com/en/activities/winter/skiing-snowboarding/skipasses-prices/faq-refund) | `146.0` | The detailed official FAQ publishes a 146 km total and itemizes its piste, route and fun-park components. | The detailed same-scope inventory is retained over the conflicting broad marketing headline. |
| `ski_area_access:solden-solden--solden-ski-area` | `access_mode` | [Giggijochbahn](https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423) | `"Giggijochbahn valley station in Sölden"` | The official lift listing establishes the named feeder lift in Sölden. | Official placement and the reviewed 661 m OSM geometry are normalized to walk access. |
| `ski_area_access:solden-solden--solden-ski-area` | `distance_m` | [OpenStreetMap node 322677891](https://www.openstreetmap.org/node/322677891) | `{"haversine_distance_m": 661, "stay_base_coordinate": [46.9666319, 11.0072845], "valley_station_coordinate": [46.9725038, 11.0086824]}` | The actual Giggijochbahn valley-station node is 661 m from the representative Sölden stay-base coordinate by Haversine calculation. | This is a straight-line reviewed approximation, not a routed walking distance. |
| `ski_area_access:solden-solden--solden-ski-area` | `nearest_lift_name` | [OpenStreetMap way 29330800](https://www.openstreetmap.org/way/29330800) | `"Giggijochbahn"` | The named OSM aerialway and its valley station match the official Giggijochbahn listing. |  |
| `ski_area_access:solden-solden--solden-ski-area` | `regional_data_ids` | [OpenStreetMap Giggijochbahn valley station](https://www.openstreetmap.org/node/322677891) | `{"osm_node_id": "322677891", "osm_way_id": "29330800"}` | The access edge stores the exact valley-station node and named aerialway used for its geometry. |  |
| `ski_area_access:solden-solden--solden-ski-area` | `source_urls` | [Giggijochbahn](https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423) | `["https://www.openstreetmap.org/node/322677891", "https://www.openstreetmap.org/way/29330800", "https://www.soelden.com/en/region-villages/soelden-a-z/giggijochbahn.i-93ccf5ab-f1a1-43bb-a48b-fe0198cf5423"]` | The access sources now refer consistently to the selected Giggijochbahn endpoint. |  |
| `ski_region:solden` | `name` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | Official resort page uses the Sölden spelling. |  |
| `stay_base:solden-solden` | `base_character.development_style` | [Municipality of Sölden](https://www.soelden.gv.at/) | `"Sölden developed from a mountain-farming settlement into an international tourism destination over the last 90 years."` | The official municipality establishes an inherited settlement predating modern ski tourism and its later tourism-led transformation. | The combination of an established settlement and substantial tourism-era development is normalized to mixed rather than traditional or planned_resort. |
| `stay_base:solden-solden` | `base_character.development_style` | [Bergbahnen Sölden company history](https://bergbahnen.soelden.com/en/about-us/company-history) | `"Tourism infrastructure expanded from the first Hochsölden chairlift in 1948 into a leading Alpine destination."` | The official lift-company history documents substantial post-war resort-era development layered onto the established settlement. | The source corroborates the resort-era half of the mixed development-style classification. |
| `stay_base:solden-solden` | `base_character.local_pace` | [Sölden region and villages](https://www.soelden.com/en/region-villages) | `"lively"` | The official destination calls Sölden an urban-lifestyle homebase active by day and night. | The explicit urban and nightlife positioning is mapped to lively. |
| `stay_base:solden-solden` | `base_type` | [Official Sölden village description](https://www.soelden.com/en/region-villages/villages/soelden) | `"village"` | The official destination page explicitly describes Sölden's village area. | The structural settlement description is normalized to the controlled village base type. |
| `stay_base:solden-solden` | `elevation_m` | [Official Sölden village description](https://www.soelden.com/en/region-villages/villages/soelden) | `1377` | The official destination page states that the Sölden village area begins at 1,377 m. |  |
| `stay_base:solden-solden` | `latitude` | [OpenStreetMap relation 77772](https://www.openstreetmap.org/relation/77772) | `46.9666319` | OpenStreetMap administrative relation provides the Sölden centroid latitude. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:solden-solden` | `local_apres_profile.availability` | [Fire and Ice Sölden](https://www.soelden.com/en/region-villages/soelden-a-z/fire-ice.i-8823bf5b-30d6-4c56-b5c4-3e4d5bf6a5bd) | `"available"` | The official directory inventories large apres and nightlife venues in central Sölden. |  |
| `stay_base:solden-solden` | `local_apres_profile.intensity` | [Sölden region and villages](https://www.soelden.com/en/region-villages) | `"lively"` | Official destination material foregrounds nightlife, bars, and an active day-and-night identity. | The broad nightlife offer is mapped to lively. |
| `stay_base:solden-solden` | `longitude` | [OpenStreetMap relation 77772](https://www.openstreetmap.org/relation/77772) | `11.0072845` | OpenStreetMap administrative relation provides the Sölden centroid longitude. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:solden-solden` | `name` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | Official resort page uses the Sölden spelling for the stay base. |  |
| `stay_base:solden-solden` | `regional_data_ids` | [OpenStreetMap relation 77772](https://www.openstreetmap.org/relation/77772) | `{"osm_relation_id": "77772"}` | OpenStreetMap relation id is stored for future regional-data joins. |  |
| `stay_destination:solden` | `name` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | The normalized migration retains the already reviewed destination boundary. |  |
| `stay_destination:solden` | `name` | [Sölden ski area](https://www.soelden.com/en/activities/winter/skiing-snowboarding) | `"Sölden"` | Official resort page uses the Sölden spelling. |  |

## Boundary Decisions

- `solden`: `pass`

## Ranking Impact

Ranking-relevant season, terrain-total, skill-support, and reviewed access-distance facts attach to the normalized ski-area and access-edge owners; the incompatible difficulty split remains missing rather than being misclassified.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation typed REPORT.json --markdown-output REPORT.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation reconcile REPORT.json --base-catalog-path BASE/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json`

## Caveats

- The detailed official FAQ and ski-map inventory publish 146 km while broad official marketing pages publish 147 km for the same Sölden ski-area scope; Snowcast retains 146 km with documented detailed-source precedence.
- The official blue/red/black pistes total 137.2 km while the 146 km headline also includes 6.7 km of ski routes and 1.7 km of fun-park terrain; piste_km_by_difficulty remains null because the current schema cannot represent those categories separately.
- Top Season cash-desk prices are representative reviewed examples because Sölden uses dynamic online pricing and lower online rates vary by booking date.
- The current recurring night-skiing page does not publish a season label, so night_skiing.season_label remains null.
- The 661 m Giggijochbahn access distance is a Haversine approximation from representative OSM points, not a routed walking distance; duration remains null.
- Accommodation and rental price ranges and quality tiers remain product-curated estimates pending a reviewed provider sampling policy.
- The official 100% figure is a snow-guarantee claim, not a snowmaking-coverage percentage, so coverage remains null.
- The official map confirms marked ski routes but does not expose a complete stable route count in the reviewed page text.
