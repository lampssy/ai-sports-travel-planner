# Mayrhofen Catalog Curation - scoped Mountopolis owner and regional follow-up

Migrates PR #16 onto the schema-version-2 catalog-curation contract and corrects source ownership. Mayrhofen retains the official 142 km, 61-lift Mountopolis inventory across Ahorn, Penken, Finkenberg, Rastkogel, and Eggalm; Hintertux remains a separate glacier ski-area owner. The wider piste map is removed from Mayrhofen because it includes Hintertux. The Mayrhofen town base keeps its sourced town classification and lively local apres profile using a recurring venue physically located in Mayrhofen. Additional Mayrhofen-Hippach and Tux-Finkenberg stay/access nodes are explicitly deferred as one regional boundary migration.

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
| `ski_area:hintertux-glacier` | `narrow` | `ski_area_id`, `name` |

## Entity Scope Assessments

| Candidate | Kind | Disposition | Signals | Catalog Targets | Evidence | Backlog | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mayrhofen` (Mayrhofen) | `stay_destination` | `represented` | `independent_stay_market`, `direct_access_relationship` | `stay_destination:mayrhofen` | `boundary-mayrhofen` |  | The existing destination remains the reviewed Mayrhofen accommodation and recommendation context. |
| `mayrhofen-mayrhofen` (Mayrhofen town base) | `stay_base` | `represented` | `independent_stay_market`, `direct_access_relationship` | `stay_base:mayrhofen-mayrhofen` | `delta-23` |  | The existing town base owns Mayrhofen-local character, apres, and Penkenbahn access context. |
| `mayrhofen-ski-area` (Mountopolis Mayrhofen terrain owner) | `ski_area` | `represented` | `official_independent_identity` | `ski_area:mayrhofen-ski-area` | `scope-mountopolis-local-owner` |  | The retained ski-area ID owns the operator's jointly published 142 km Mayrhofen inventory, excluding Hintertux Glacier. |
| `mayrhofen-mayrhofen--mayrhofen-ski-area` (Mayrhofen town to Penken access) | `ski_area_access` | `represented` | `direct_access_relationship`, `distinct_access` | `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `delta-17` |  | The existing edge records the representative Mayrhofen town walk to Penkenbahn. |
| `zillertaler-superskipass-mayrhofen` (Zillertaler Superskipass / Skipass Mayrhofen) | `lift_pass_product` | `represented` | `official_product_identity` | `lift_pass_product:zillertaler-superskipass-mayrhofen` | `delta-5` |  | The current pass record keeps its existing local and regional product coverage pending the separate pass-product refinement. |
| `hintertux-glacier` (Hintertux Glacier) | `ski_area` | `represented` | `official_independent_identity`, `separate_operator`, `distinct_elevation_or_season` | `ski_area:hintertux-glacier` | `scope-hintertux-glacier-owner` |  | Hintertux is already modeled as a separate glacier ski-area owner and must not be folded into Mayrhofen's local facts. |
| `mayrhofen-ahorn-sector` (Ahorn sector) | `ski_area` | `not_separate` | `official_map_sector` | `ski_area:mayrhofen-ski-area` | `scope-mountopolis-local-owner` |  | Ahorn is a named sector, but the operator publishes the primary 142 km and 61-lift inventory jointly; a sector label alone does not justify another ski-area owner. |
| `mayrhofen-penken-sector` (Penken sector) | `ski_area` | `not_separate` | `official_map_sector` | `ski_area:mayrhofen-ski-area` | `scope-mountopolis-local-owner` |  | Penken is a named sector, but the operator publishes the primary 142 km and 61-lift inventory jointly; a sector label alone does not justify another ski-area owner. |
| `mayrhofen-finkenberg-sector` (Finkenberg sector) | `ski_area` | `not_separate` | `official_map_sector` | `ski_area:mayrhofen-ski-area` | `scope-mountopolis-local-owner` |  | Finkenberg is a named sector, but the operator publishes the primary 142 km and 61-lift inventory jointly; a sector label alone does not justify another ski-area owner. |
| `mayrhofen-rastkogel-sector` (Rastkogel sector) | `ski_area` | `not_separate` | `official_map_sector` | `ski_area:mayrhofen-ski-area` | `scope-mountopolis-local-owner` |  | Rastkogel is a named sector, but the operator publishes the primary 142 km and 61-lift inventory jointly; a sector label alone does not justify another ski-area owner. |
| `mayrhofen-eggalm-sector` (Eggalm sector) | `ski_area` | `not_separate` | `official_map_sector` | `ski_area:mayrhofen-ski-area` | `scope-mountopolis-local-owner` |  | Eggalm is a named sector, but the operator publishes the primary 142 km and 61-lift inventory jointly; a sector label alone does not justify another ski-area owner. |
| `ski-glacier-world-zillertal-3000` (Ski & Glacier World Zillertal 3000) | `terrain_domain` | `external_pass_context` | `official_product_identity`, `disconnected_terrain` |  | `scope-ski-glacier-world-product-context` |  | The published aggregate spans the separate Hintertux owner and multiple valley access contexts, so this PR keeps it as product context rather than inventing a ski-connected terrain domain. |
| `mayrhofen-hippach` (Mayrhofen-Hippach destination boundary) | `stay_destination` | `deferred` | `independent_stay_market`, `direct_access_relationship` |  | `scope-mayrhofen-hippach-access-bases` | `docs/product-backlog.md#mayrhofen-hippach-and-tux-finkenberg-completion` | The official regional market requires a complete boundary review against the existing Mayrhofen destination. |
| `mayrhofen-schwendau` (Schwendau accommodation base) | `stay_base` | `deferred` | `independent_stay_market`, `direct_access_relationship` |  | `scope-mayrhofen-hippach-access-bases` | `docs/product-backlog.md#mayrhofen-hippach-and-tux-finkenberg-completion` | Schwendau has direct Horbergbahn access, but its owner depends on the Mayrhofen-Hippach destination decision. |
| `mayrhofen-schwendau--mayrhofen-ski-area` (Schwendau to Horbergbahn access) | `ski_area_access` | `deferred` | `direct_access_relationship`, `distinct_access` |  | `scope-mayrhofen-hippach-access-bases` | `docs/product-backlog.md#mayrhofen-hippach-and-tux-finkenberg-completion` | The direct access edge depends on the deferred Schwendau stay base. |
| `mayrhofen-hochschwendberg` (Hochschwendberg accommodation base) | `stay_base` | `deferred` | `independent_stay_market`, `direct_access_relationship` |  | `scope-mayrhofen-hippach-access-bases` | `docs/product-backlog.md#mayrhofen-hippach-and-tux-finkenberg-completion` | Hochschwendberg has direct Möslbahn access, but its owner depends on the regional destination review. |
| `mayrhofen-hochschwendberg--mayrhofen-ski-area` (Hochschwendberg to Möslbahn access) | `ski_area_access` | `deferred` | `direct_access_relationship`, `distinct_access` |  | `scope-mayrhofen-hippach-access-bases` | `docs/product-backlog.md#mayrhofen-hippach-and-tux-finkenberg-completion` | The direct access edge depends on the deferred Hochschwendberg stay base. |
| `tux-finkenberg` (Tux-Finkenberg destination boundary) | `stay_destination` | `deferred` | `independent_stay_market`, `direct_access_relationship` |  | `scope-finkenberg-direct-access` | `docs/product-backlog.md#mayrhofen-hippach-and-tux-finkenberg-completion` | The wider stay market must be reconciled with the existing Hintertux destination before ownership changes. |
| `tux-finkenberg-finkenberg` (Finkenberg accommodation base) | `stay_base` | `deferred` | `independent_stay_market`, `direct_access_relationship` |  | `scope-finkenberg-direct-access` | `docs/product-backlog.md#mayrhofen-hippach-and-tux-finkenberg-completion` | Finkenberg has direct Almbahnen access, but its base owner depends on the deferred Tux-Finkenberg boundary migration. |
| `tux-finkenberg-finkenberg--mayrhofen-ski-area` (Finkenberg to Mayrhofen terrain access) | `ski_area_access` | `deferred` | `direct_access_relationship`, `distinct_access` |  | `scope-finkenberg-direct-access` | `docs/product-backlog.md#mayrhofen-hippach-and-tux-finkenberg-completion` | The direct Finkenberg edge depends on the deferred destination and stay-base identities. |

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
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `field_source_refs` | `{"elevation_season": [], "glacier_terrain": [], "identity_coordinates": [], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": [], "skill_fit": [], "snow_park": [], "snowmaking": [], "terrain_metrics": []}` | `{"elevation_season": ["https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"], "glacier_terrain": [], "identity_coordinates": ["https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"], "marked_freeride_routes": [], "night_skiing": [], "official_documents": [], "ski_day_apres": ["https://www.mayrhofen.at/de/service-providers/kasermandl-penken-1800m-penken"], "skill_fit": ["https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"], "snow_park": ["https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter"], "snowmaking": ["https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter"], "terrain_metrics": ["https://www.skiresort.info/ski-resort/mayrhofen-penken-ahorn-rastkogel-eggalm-mountopolis/", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"]}` | `estimated` | no |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `field_statuses` | `{"elevation_season": "needs_source", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "needs_source", "skill_fit": "estimated", "snow_park": "needs_source", "snowmaking": "needs_source", "terrain_metrics": "needs_source"}` | `{"elevation_season": "verified_with_adjustment", "glacier_terrain": "needs_source", "identity_coordinates": "needs_source", "marked_freeride_routes": "needs_source", "night_skiing": "needs_source", "official_documents": "needs_source", "ski_day_apres": "verified_with_adjustment", "skill_fit": "estimated", "snow_park": "verified", "snowmaking": "verified", "terrain_metrics": "verified_with_adjustment"}` | `estimated` | no |
| `trust_manifest:ski_areas:mayrhofen-ski-area` | `notes` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner."]` | `["Trust-contract first pass; not a full official-source recuration.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands.", "Legacy source-backed status was downgraded to needs_source because no direct external evidence remained for this owner.", "Source-aware v2 enrichment reviewed official Mayrhofner Bergbahnen sources on 2026-07-04.", "Hintertux glacier access was kept separate from the modeled non-glacier Mayrhofen ski area.", "The published 2025/26 piste map includes Hintertux Glacier and is therefore not attached to the narrower 142 km Mayrhofen ski-area owner."]` | `needs_source` | no |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `field_source_refs` | `{"base_character": [], "base_type": [], "coordinates": [], "elevation": [], "identity_ownership": [], "local_apres": [], "lodging_price_quality": []}` | `{"base_character": ["https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal"], "base_type": ["https://www.openstreetmap.org/relation/80064"], "coordinates": ["https://www.openstreetmap.org/relation/80064", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"], "elevation": ["https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal"], "identity_ownership": ["https://www.openstreetmap.org/relation/80064", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"], "local_apres": ["https://www.mayrhofen.at/de/service-providers/brueckenstadl", "https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal"], "lodging_price_quality": ["https://www.openstreetmap.org/relation/80064", "https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html"]}` | `estimated` | no |
| `trust_manifest:stay_bases:mayrhofen-mayrhofen` | `field_statuses` | `{"base_character": "needs_source", "base_type": "needs_source", "coordinates": "needs_source", "elevation": "needs_source", "identity_ownership": "needs_source", "local_apres": "needs_source", "lodging_price_quality": "estimated"}` | `{"base_character": "verified_with_adjustment", "base_type": "verified_with_adjustment", "coordinates": "verified_with_adjustment", "elevation": "verified", "identity_ownership": "needs_source", "local_apres": "verified_with_adjustment", "lodging_price_quality": "estimated"}` | `estimated` | no |
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
| `ski_area:mayrhofen-ski-area` | `official_trail_map.season_label` | `unresolved` | No child-scoped official map was found for the modeled 142 km Mayrhofen ski-area owner, so there is no local map season label to store. |
| `ski_area:mayrhofen-ski-area` | `official_trail_map.url` | `unresolved` | The available official 2025/26 piste map includes Hintertux Glacier and therefore belongs to a wider product/domain context rather than the modeled 142 km Mayrhofen ski-area owner. |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.advanced` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.beginner` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `piste_km_by_difficulty.intermediate` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `season_end_month` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `season_start_month` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `season_windows` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `ski_area_id` | `reviewed-no-change` |  |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.availability` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.intensity` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.season_label` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `snow_park.availability` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `snow_park.park_count` | `changed` |  |
| `ski_area:mayrhofen-ski-area` | `snow_park.season_label` | `unresolved` | Official Mountopolis sources were reviewed, but they did not establish this exact value for the modeled Mayrhofen ski area; it remains unknown rather than being inferred from wider Zillertal or Hintertux products. |
| `ski_area:mayrhofen-ski-area` | `snowmaking.availability` | `changed` |  |
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
| `stay_base:mayrhofen-mayrhofen` | `base_character.development_style` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `base_character.local_pace` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `base_type` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `elevation_m` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `latitude` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.availability` | `changed` |  |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.intensity` | `changed` |  |
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
| `ski_area:hintertux-glacier` | `name` | `reviewed-no-change` |  |
| `ski_area:hintertux-glacier` | `ski_area_id` | `reviewed-no-change` |  |

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
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.availability` | [Kasermandl Penken apres-ski](https://www.mayrhofen.at/de/service-providers/kasermandl-penken-1800m-penken) | `"available"` | The official destination listing documents a dedicated apres venue on Penken. |  |
| `ski_area:mayrhofen-ski-area` | `ski_day_apres_profile.intensity` | [Kasermandl Penken apres-ski](https://www.mayrhofen.at/de/service-providers/kasermandl-penken-1800m-penken) | `"lively"` | The on-mountain venue advertises legendary parties, a dance floor, music, and active celebration. | The explicit party-oriented venue is mapped to lively. |
| `ski_area:mayrhofen-ski-area` | `snow_park.availability` | [Mountopolis winter](https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter) | `"available"` | The official operator presents PenkenPark as the ski area's dedicated snowpark. |  |
| `ski_area:mayrhofen-ski-area` | `snow_park.park_count` | [Mountopolis winter](https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter) | `1` | The scoped operator inventory names one dedicated snowpark, PenkenPark. |  |
| `ski_area:mayrhofen-ski-area` | `snowmaking.availability` | [Mountopolis winter](https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter) | `"available"` | The official operator explicitly credits cutting-edge snowmaking technology for December-to-April conditions. |  |
| `ski_area:mayrhofen-ski-area` | `total_lift_count` | [Mayrhofner Bergbahnen - Mountopolis](https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html) | `61` | Official Zillertal page states 61 modern lifts in the Mountopolis ski area. |  |
| `ski_area:mayrhofen-ski-area` | `total_piste_km` | [Mayrhofner Bergbahnen - Mountopolis](https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html) | `142.0` | Official Zillertal page states 142 kilometres of pistes in the Mountopolis ski area. |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `access_mode` | [OpenStreetMap Penkenbahn station](https://www.openstreetmap.org/node/344469170) | `"walk"` | Penkenbahn is within roughly 500 m of the reviewed Mayrhofen town reference point, supporting walk access. |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `distance_m` | [OpenStreetMap Penkenbahn station](https://www.openstreetmap.org/node/344469170) | `490` | Mayrhofen OSM relation center to Penkenbahn station is about 488 m by haversine distance. | Rounded to the nearest ten metres for catalog stability. |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `lift_distance` | [OpenStreetMap Penkenbahn station](https://www.openstreetmap.org/node/344469170) | `"near"` | OSM Penkenbahn station is approximately 490 m from the Mayrhofen OSM relation center, supporting a near lift-distance bucket. | Distance bucket derived from OSM coordinates and rounded haversine distance. |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `nearest_lift_name` | [OpenStreetMap Penkenbahn station](https://www.openstreetmap.org/node/344469170) | `"Penkenbahn"` | OSM identifies the nearby aerialway station as Penkenbahn. |  |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `regional_data_ids` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `{"nearest_lift_osm_node_id": "344469170", "osm_relation_id": "80064"}` | OSM relation 80064 and Penkenbahn station node 344469170 anchor the stay-base and nearest-lift references. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `ski_area_access:mayrhofen-mayrhofen--mayrhofen-ski-area` | `source_urls` | [OpenStreetMap Penkenbahn station](https://www.openstreetmap.org/node/344469170) | `"walk"` | Penkenbahn is within roughly 500 m of the reviewed Mayrhofen town reference point, supporting walk access. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_base:mayrhofen-mayrhofen` | `base_character.development_style` | [Mayrhofen in Zillertal](https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal) | `"mixed"` | The official profile explicitly says strong traditions and modernity coexist, from farmhouses to luxury hotels. | The explicit traditional-modern blend is mapped to mixed. |
| `stay_base:mayrhofen-mayrhofen` | `base_character.local_pace` | [Mayrhofen in Zillertal](https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal) | `"lively"` | The official profile positions Mayrhofen as an Alpine tourism flagship combining fun, action, hospitality, and a busy town offer. | The broad active resort-town offer is mapped to lively. |
| `stay_base:mayrhofen-mayrhofen` | `base_type` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `"town"` | OSM classifies Mayrhofen as a town-level administrative/place entity. |  |
| `stay_base:mayrhofen-mayrhofen` | `elevation_m` | [Mayrhofen in Zillertal](https://www.mayrhofen.at/de/stories/mayrhofen-im-zillertal) | `630` | The official town profile places Mayrhofen at 630 m. |  |
| `stay_base:mayrhofen-mayrhofen` | `latitude` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `47.1672` | OSM relation 80064 provides Mayrhofen coordinates used for stay-base enrichment. | Rounded OSM latitude 47.1672188 to four decimals. |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.availability` | [Brück'n Stadl in Mayrhofen](https://www.mayrhofen.at/de/service-providers/brueckenstadl) | `"available"` | The official destination listing identifies a recurring winter apres venue at Ahornstraße 850, 6290 Mayrhofen. |  |
| `stay_base:mayrhofen-mayrhofen` | `local_apres_profile.intensity` | [Brück'n Stadl in Mayrhofen](https://www.mayrhofen.at/de/service-providers/brueckenstadl) | `"lively"` | The official listing describes a long-running Mayrhofen venue built around music, dancing, parties, winter DJs, and apres-ski fans. | The recurring party-oriented venue evidence is normalized to Snowcast's lively intensity. |
| `stay_base:mayrhofen-mayrhofen` | `longitude` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `11.8639` | OSM relation 80064 provides Mayrhofen coordinates used for stay-base enrichment. | Rounded OSM longitude 11.8638664 to four decimals. |
| `stay_base:mayrhofen-mayrhofen` | `regional_data_ids` | [OpenStreetMap Mayrhofen relation](https://www.openstreetmap.org/relation/80064) | `{"nearest_lift_osm_node_id": "344469170", "osm_relation_id": "80064"}` | OSM relation 80064 and Penkenbahn station node 344469170 anchor the stay-base and nearest-lift references. | Legacy evidence was translated to the normalized field; the after value preserves the reviewed PR meaning. |
| `stay_destination:mayrhofen` | `name` | [Mayrhofner Bergbahnen - Mountopolis](https://www.zillertal.at/en/winter/holidays/ski-areas/mayrhofner-bergbahnen-mountopolis.html) | `"Mayrhofen"` | The normalized migration retains the already reviewed destination boundary. |  |
| `ski_area:mayrhofen-ski-area` | `name` | [Mountopolis winter terrain](https://www.mayrhofen.at/en/pages/mountopolis-starting-page-winter) | `{"sectors": ["Ahorn", "Penken", "Finkenberg", "Rastkogel", "Eggalm"], "total_lift_count": 61, "total_piste_km": 142}` | The official operator presents Ahorn, Penken, Finkenberg, Rastkogel, and Eggalm together as the 142 km, 61-lift Mountopolis offer. | The named sectors remain inside one modeled ski-area owner because the operator publishes their primary terrain inventory jointly. |
| `ski_area:hintertux-glacier` | `name` | [Hintertux Glacier skiing](https://www.hintertuxergletscher.at/en/skiing/hintertux-glacier/ski-snowboard/) | `"Hintertux Glacier"` | The official glacier operator presents Hintertux as its own glacier ski area while describing wider winter pass coverage separately. |  |
| `ski_area:hintertux-glacier` | `name` | [Ski & Glacier World Zillertal 3000](https://www.hintertuxergletscher.at/en/skiing/hintertux-glacier/ski-snowboard/) | `{"includes": ["Hintertux Glacier", "Eggalm", "Rastkogel", "Finkenberg", "Penken", "Ahorn"], "product_context": "Ski & Glacier World Zillertal 3000"}` | The official page groups the glacier and valley sectors as a wider winter ski product; the published map also spans disconnected access contexts, so the aggregate is not a child map for Mayrhofen. | The wider inventory remains product context rather than a new ski-connected terrain domain in this PR. |
| `stay_destination:mayrhofen` | `name` | [Mayrhofen-Hippach ski-bus and valley access](https://www.mayrhofen.at/en/stories/mayrhofner-bergbahnen-faqs) | `["Mayrhofen", "Hippach", "Schwendau", "Hochschwendberg"]` | The official destination documents a shared Mayrhofen-Hippach bus network serving Penkenbahn, Ahornbahn, Horbergbahn, and Möslbahn, which exposes additional accommodation/access contexts. | The source establishes the regional graph candidates; exact destination and base ownership is deferred for a complete boundary pass. |
| `ski_area:mayrhofen-ski-area` | `name` | [Penken access points](https://www.mayrhofen.at/de/service-providers/mayrhofner-bergbahnen-penkenbahn) | `["Mayrhofen", "Schwendau", "Hochschwendberg", "Finkenberg"]` | The official Penken page identifies direct access from Mayrhofen, Schwendau, Hochschwendberg, and the Finkenberger Almbahn. | The direct-access signal supports a future Finkenberg stay-base edge; it does not split the jointly published Mountopolis terrain owner. |

## Boundary Decisions

- `mayrhofen`: `pass`

## Ranking Impact

Ranking-relevant facts now attach to the normalized ski-area, stay-base, and access-edge owners; Search V3 scoring policy is unchanged.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog --catalog-path app/data/catalog.json --trust-manifest-path app/data/resort_trust_manifest.json`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation typed REPORT.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output REPORT.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation reconcile REPORT.json --base-catalog-path BASE/app/data/catalog.json --current-catalog-path app/data/catalog.json --base-trust-manifest-path BASE/app/data/resort_trust_manifest.json --current-trust-manifest-path app/data/resort_trust_manifest.json --require-report-schema-version 2 --product-backlog-path docs/product-backlog.md --markdown-output REPORT.md`

## Caveats

- MANNI Rental is externally verified, but reviewed sources do not expose a current price table; rental price and quality remain estimated.
- The Zillertaler Superskipass covers a broader Zillertal network; the existing pass relationships are retained pending the separate pass-product refinement.
- The official operator supports snowmaking but does not publish an exact coverage percentage for the modeled owner.
- No child-scoped official piste map was found for the 142 km Mayrhofen owner; the available 2025/26 map also includes the separately modeled Hintertux Glacier.
- Glacier terrain, recurring public night skiing, and marked freeride-route inventory remain unknown for the modeled Mayrhofen owner because the reviewed sources do not establish those exact local facts.
- Mayrhofen-Hippach and Tux-Finkenberg destination boundaries, their additional bases, and direct access edges are deferred together through the catalog-curation backlog.
