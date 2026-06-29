# Zermatt Full Static Catalog Curation - 2026-06-27

Full source-backed static catalog curation for Zermatt. Adds the 2026/27 winter season window, local Zermatt terrain scope, local and International pass products, a cross-border Matterhorn Ski Paradise terrain domain, and OSM-backed stay-base access evidence.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:zermatt` | `season_windows` | `null` | `[{"end_date": "2027-05-03", "season_label": "Winter 2026/27", "start_date": "2026-11-01", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:zermatt-ski-area` | `season_windows` | `null` | `[{"end_date": "2027-05-03", "season_label": "Winter 2026/27", "start_date": "2026-11-01", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:zermatt-ski-area` | `total_piste_km` | `null` | `200.0` | `verified_with_adjustment` | yes |
| `stay_base:zermatt-zermatt` | `latitude` | `null` | `46.0212` | `verified_with_adjustment` | no |
| `stay_base:zermatt-zermatt` | `longitude` | `null` | `7.7493` | `verified_with_adjustment` | no |
| `stay_base:zermatt-zermatt` | `nearest_lift_name` | `null` | `"Zermatt-Sunnegga funicular"` | `verified_with_adjustment` | no |
| `stay_base:zermatt-zermatt` | `nearest_lift_distance_m` | `null` | `320` | `verified_with_adjustment` | yes |
| `stay_base:zermatt-zermatt` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:zermatt-zermatt` | `base_type` | `null` | `"town"` | `verified_with_adjustment` | no |
| `stay_base:zermatt-zermatt` | `atmosphere_tags` | `[]` | `["premium", "car_free", "scenic", "walkable_lifts", "glacier_access"]` | `verified_with_adjustment` | no |
| `stay_base:zermatt-zermatt` | `regional_data_ids` | `{}` | `{"nearest_lift_osm_way_id": "22330086", "osm_relation_id": "1685406"}` | `verified_with_adjustment` | no |
| `stay_base:zermatt-zermatt` | `supported_skill_levels` | `["intermediate", "advanced"]` | `["beginner", "intermediate", "advanced"]` | `verified_with_adjustment` | yes |
| `lift_pass_product:zermatt-ski-pass` | `name` | `null` | `"Zermatt ski pass"` | `verified_with_adjustment` | no |
| `lift_pass_product:zermatt-ski-pass` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:zermatt-ski-pass` | `is_default` | `null` | `true` | `verified_with_adjustment` | yes |
| `lift_pass_product:zermatt-ski-pass` | `valid_ski_area_ids` | `null` | `["zermatt-ski-area"]` | `verified_with_adjustment` | yes |
| `lift_pass_product:zermatt-ski-pass` | `prices` | `null` | `[{"amount": 89.0, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "from", "season_label": "Winter 2026/27 Zermatt low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}, {"amount": 209.0, "audience": "adult", "currency": "CHF", "duration_days": 3, "price_kind": "from", "season_label": "Winter 2026/27 Zermatt low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}, {"amount": 384.0, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "from", "season_label": "Winter 2026/27 Zermatt low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}]` | `verified_with_adjustment` | yes |
| `lift_pass_product:zermatt-international-ski-pass` | `name` | `null` | `"International ski pass Zermatt-Cervinia"` | `verified_with_adjustment` | no |
| `lift_pass_product:zermatt-international-ski-pass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | yes |
| `lift_pass_product:zermatt-international-ski-pass` | `is_default` | `null` | `false` | `verified_with_adjustment` | no |
| `lift_pass_product:zermatt-international-ski-pass` | `valid_ski_area_ids` | `null` | `["zermatt-ski-area"]` | `verified_with_adjustment` | yes |
| `lift_pass_product:zermatt-international-ski-pass` | `terrain_domain_ids` | `null` | `["matterhorn-ski-paradise"]` | `verified_with_adjustment` | yes |
| `lift_pass_product:zermatt-international-ski-pass` | `external_validity_summary` | `null` | `"Covers the local Zermatt ski area and optional access to the Italian Breuil-Cervinia/Valtournenche terrain, subject to timetable, weather, and pass conditions."` | `verified_with_adjustment` | yes |
| `lift_pass_product:zermatt-international-ski-pass` | `prices` | `null` | `[{"amount": 104.0, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "from", "season_label": "Winter 2026/27 International low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}, {"amount": 232.0, "audience": "adult", "currency": "CHF", "duration_days": 3, "price_kind": "from", "season_label": "Winter 2026/27 International low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}, {"amount": 432.0, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "from", "season_label": "Winter 2026/27 International low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}]` | `verified_with_adjustment` | yes |
| `terrain_domain:matterhorn-ski-paradise` | `name` | `null` | `"Matterhorn Ski Paradise"` | `verified_with_adjustment` | no |
| `terrain_domain:matterhorn-ski-paradise` | `ski_area_refs` | `null` | `[{"resort_id": "zermatt", "ski_area_id": "zermatt-ski-area"}, {"resort_id": "cervinia", "ski_area_id": "cervinia-ski-area"}]` | `verified_with_adjustment` | yes |
| `terrain_domain:matterhorn-ski-paradise` | `metric_scope` | `null` | `"aggregate"` | `verified_with_adjustment` | no |
| `terrain_domain:matterhorn-ski-paradise` | `total_piste_km` | `null` | `360.0` | `verified_with_adjustment` | yes |
| `terrain_domain:matterhorn-ski-paradise` | `total_lift_count` | `null` | `54` | `verified_with_adjustment` | yes |
| `terrain_domain:matterhorn-ski-paradise` | `base_elevation_m` | `null` | `1620` | `verified_with_adjustment` | yes |
| `terrain_domain:matterhorn-ski-paradise` | `summit_elevation_m` | `null` | `3883` | `verified_with_adjustment` | no |
| `terrain_domain:matterhorn-ski-paradise` | `source_urls` | `null` | `["https://www.matterhornparadise.ch/en/experience/skiing", "https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter", "https://www.matterhornparadise.ch/en/experience/peaks/matterhorn-glacier-paradise"]` | `verified_with_adjustment` | no |
| `destination:zermatt` | `trust_manifest.field_statuses.terrain_groups` | `"needs_source"` | `"verified_with_adjustment"` | `verified_with_adjustment` | yes |
| `destination:zermatt` | `trust_manifest.field_statuses.stay_base_lift_distance` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | yes |
| `destination:zermatt` | `trust_manifest.field_statuses.supported_skill_levels` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | yes |
| `destination:zermatt` | `trust_manifest.field_statuses.lift_pass_products` | `"needs_source"` | `"verified_with_adjustment"` | `verified_with_adjustment` | yes |
| `destination:zermatt` | `trust_manifest.field_statuses.rental_examples` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:zermatt` | `trust_manifest.source_refs` | `["docs/sprint-17-resort-audit-results.md", "https://www.matterhornparadise.ch/en/experience/skiing", "https://www.matterhornparadise.ch/en/experience/peaks/matterhorn-glacier-paradise", "https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn"]` | `["https://www.matterhornparadise.ch/en/experience/skiing", "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes", "https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter", "https://www.matterhornparadise.ch/en/experience/peaks/matterhorn-glacier-paradise", "https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn", "https://www.openstreetmap.org/relation/1685406", "https://www.openstreetmap.org/way/22330086", "https://www.openstreetmap.org/node/5475862597", "https://www.zermattglaciersport.ch/en/rental/"]` | `verified_with_adjustment` | no |
| `destination:zermatt` | `trust_manifest.notes` | `["Sample rechecked against official Matterhorn Paradise sources during the source-backed trust pass.", "Matterhorn Ski Paradise is marketed as year-round skiing; the current season window remains a winter-main-season product adjustment.", "Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands."]` | `["Full static curation pass completed with official Matterhorn Paradise/Zermatt Bergbahnen sources, OSM access references, and Glacier Sport rental evidence.", "Local Zermatt ski-area terrain is stored as the Zermatt-only 200 km pass scope; the 360 km cross-border Matterhorn Ski Paradise claim is modeled as a shared terrain domain for optional International pass access.", "Piste difficulty split, local lift count, lodging/rental price ranges, and normalized quality tiers remain unresolved or estimated where reviewed official sources did not publish enough scoped evidence."]` | `verified_with_adjustment` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `destination:zermatt` | `season_windows` | `changed` | Reviewed in this full Zermatt curation pass. |
| `ski_area:zermatt-ski-area` | `season_windows` | `changed` | Reviewed in this full Zermatt curation pass. |
| `ski_area:zermatt-ski-area` | `total_piste_km` | `changed` | Reviewed in this full Zermatt curation pass. |
| `stay_base:zermatt-zermatt` | `latitude` | `changed` | Reviewed in this full Zermatt curation pass. |
| `stay_base:zermatt-zermatt` | `longitude` | `changed` | Reviewed in this full Zermatt curation pass. |
| `stay_base:zermatt-zermatt` | `nearest_lift_name` | `changed` | Reviewed in this full Zermatt curation pass. |
| `stay_base:zermatt-zermatt` | `nearest_lift_distance_m` | `changed` | Reviewed in this full Zermatt curation pass. |
| `stay_base:zermatt-zermatt` | `access_mode` | `changed` | Reviewed in this full Zermatt curation pass. |
| `stay_base:zermatt-zermatt` | `base_type` | `changed` | Reviewed in this full Zermatt curation pass. |
| `stay_base:zermatt-zermatt` | `atmosphere_tags` | `changed` | Reviewed in this full Zermatt curation pass. |
| `stay_base:zermatt-zermatt` | `regional_data_ids` | `changed` | Reviewed in this full Zermatt curation pass. |
| `stay_base:zermatt-zermatt` | `supported_skill_levels` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-ski-pass` | `name` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-ski-pass` | `validity_scope` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-ski-pass` | `is_default` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-ski-pass` | `valid_ski_area_ids` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-ski-pass` | `prices` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-international-ski-pass` | `name` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-international-ski-pass` | `validity_scope` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-international-ski-pass` | `is_default` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-international-ski-pass` | `valid_ski_area_ids` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-international-ski-pass` | `terrain_domain_ids` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-international-ski-pass` | `external_validity_summary` | `changed` | Reviewed in this full Zermatt curation pass. |
| `lift_pass_product:zermatt-international-ski-pass` | `prices` | `changed` | Reviewed in this full Zermatt curation pass. |
| `terrain_domain:matterhorn-ski-paradise` | `name` | `changed` | Reviewed in this full Zermatt curation pass. |
| `terrain_domain:matterhorn-ski-paradise` | `ski_area_refs` | `changed` | Reviewed in this full Zermatt curation pass. |
| `terrain_domain:matterhorn-ski-paradise` | `metric_scope` | `changed` | Reviewed in this full Zermatt curation pass. |
| `terrain_domain:matterhorn-ski-paradise` | `total_piste_km` | `changed` | Reviewed in this full Zermatt curation pass. |
| `terrain_domain:matterhorn-ski-paradise` | `total_lift_count` | `changed` | Reviewed in this full Zermatt curation pass. |
| `terrain_domain:matterhorn-ski-paradise` | `base_elevation_m` | `changed` | Reviewed in this full Zermatt curation pass. |
| `terrain_domain:matterhorn-ski-paradise` | `summit_elevation_m` | `changed` | Reviewed in this full Zermatt curation pass. |
| `terrain_domain:matterhorn-ski-paradise` | `source_urls` | `changed` | Reviewed in this full Zermatt curation pass. |
| `destination:zermatt` | `trust_manifest.field_statuses.terrain_groups` | `changed` | Reviewed in this full Zermatt curation pass. |
| `destination:zermatt` | `trust_manifest.field_statuses.stay_base_lift_distance` | `changed` | Reviewed in this full Zermatt curation pass. |
| `destination:zermatt` | `trust_manifest.field_statuses.supported_skill_levels` | `changed` | Reviewed in this full Zermatt curation pass. |
| `destination:zermatt` | `trust_manifest.field_statuses.lift_pass_products` | `changed` | Reviewed in this full Zermatt curation pass. |
| `destination:zermatt` | `trust_manifest.field_statuses.rental_examples` | `changed` | Reviewed in this full Zermatt curation pass. |
| `destination:zermatt` | `trust_manifest.source_refs` | `changed` | Reviewed in this full Zermatt curation pass. |
| `destination:zermatt` | `trust_manifest.notes` | `changed` | Reviewed in this full Zermatt curation pass. |
| `destination:zermatt` | `resort_id` | `reviewed-no-change` | Stable destination id retained. |
| `destination:zermatt` | `name` | `reviewed-no-change` | Official sources confirm Zermatt naming. |
| `destination:zermatt` | `country` | `reviewed-no-change` | Switzerland retained. |
| `destination:zermatt` | `region` | `reviewed-no-change` | Valais retained. |
| `destination:zermatt` | `price_level` | `reviewed-no-change` | High price level retained; lodging and rental price ranges remain estimated. |
| `destination:zermatt` | `latitude` | `reviewed-no-change` | Existing destination latitude retained; OSM town relation reviewed. |
| `destination:zermatt` | `longitude` | `reviewed-no-change` | Existing destination longitude retained; OSM town relation reviewed. |
| `destination:zermatt` | `base_elevation_m` | `reviewed-no-change` | Existing 1620 m base aligns with official resort-region page. |
| `destination:zermatt` | `summit_elevation_m` | `reviewed-no-change` | Existing 3883 m summit aligns with Matterhorn Glacier Paradise official page. |
| `destination:zermatt` | `season_start_month` | `reviewed-no-change` | Month fallback retained; exact 2026/27 window added. |
| `destination:zermatt` | `season_end_month` | `reviewed-no-change` | Month fallback retained; exact 2026/27 window added. |
| `destination:zermatt` | `ski_areas` | `reviewed-no-change` | Single Zermatt ski area retained. |
| `destination:zermatt` | `terrain_groups` | `reviewed-no-change` | No destination-local terrain group added; cross-border aggregate is modeled as a terrain domain. |
| `destination:zermatt` | `stay_bases` | `reviewed-no-change` | Single Zermatt stay base retained and enriched. |
| `destination:zermatt` | `rentals` | `reviewed-no-change` | Glacier Sport rental example retained and externally reviewed. |
| `ski_area:zermatt-ski-area` | `ski_area_id` | `reviewed-no-change` | Stable ski-area id retained. |
| `ski_area:zermatt-ski-area` | `name` | `reviewed-no-change` | Existing Zermatt ski-area name retained. |
| `ski_area:zermatt-ski-area` | `latitude` | `reviewed-no-change` | Existing ski-area coordinate retained for weather lookup. |
| `ski_area:zermatt-ski-area` | `longitude` | `reviewed-no-change` | Existing ski-area coordinate retained for weather lookup. |
| `ski_area:zermatt-ski-area` | `base_elevation_m` | `reviewed-no-change` | Existing base elevation retained. |
| `ski_area:zermatt-ski-area` | `summit_elevation_m` | `reviewed-no-change` | Existing summit elevation retained. |
| `ski_area:zermatt-ski-area` | `season_start_month` | `reviewed-no-change` | Month fallback retained. |
| `ski_area:zermatt-ski-area` | `season_end_month` | `reviewed-no-change` | Month fallback retained. |
| `ski_area:zermatt-ski-area` | `total_lift_count` | `unresolved` | Unresolved for local Zermatt-only scope; official 54-lift fact is cross-border Matterhorn Ski Paradise aggregate. |
| `ski_area:zermatt-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | Unresolved; reviewed official sources did not publish a local scoped difficulty split. |
| `ski_area:zermatt-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | Unresolved; reviewed official sources did not publish a local scoped difficulty split. |
| `ski_area:zermatt-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | Unresolved; reviewed official sources did not publish a local scoped difficulty split. |
| `stay_base:zermatt-zermatt` | `stay_base_id` | `reviewed-no-change` | Existing stable stay-base id retained. |
| `stay_base:zermatt-zermatt` | `name` | `reviewed-no-change` | Existing stay-base name retained. |
| `stay_base:zermatt-zermatt` | `price_range` | `unresolved` | Accommodation price range remains estimated. |
| `stay_base:zermatt-zermatt` | `quality` | `unresolved` | Normalized stay-base quality remains estimated premium. |
| `stay_base:zermatt-zermatt` | `lift_distance` | `reviewed-no-change` | Legacy near bucket retained; precise nearest_lift_distance_m now carries source-backed access detail. |
| `rental:zermatt:glacier-sport-zermatt` | `name` | `reviewed-no-change` | Glacier Sport rental name externally verified. |
| `rental:zermatt:glacier-sport-zermatt` | `price_range` | `unresolved` | Reviewed rental source publishes CHF ski-only rates, but catalog rental price_range remains EUR-normalized legacy estimate until currency handling is widened. |
| `rental:zermatt:glacier-sport-zermatt` | `quality` | `unresolved` | Rental quality remains estimated premium. |
| `rental:zermatt:glacier-sport-zermatt` | `lift_distance` | `unresolved` | Rental lift distance remains estimated near. |
| `lift_pass_product:zermatt-ski-pass` | `terrain_domain_ids` | `not-applicable` | Local Zermatt pass does not include cross-border terrain-domain access. |
| `terrain_domain:matterhorn-ski-paradise` | `piste_km_by_difficulty.beginner` | `unresolved` | No official aggregate difficulty split stored for the terrain domain. |
| `terrain_domain:matterhorn-ski-paradise` | `piste_km_by_difficulty.intermediate` | `unresolved` | No official aggregate difficulty split stored for the terrain domain. |
| `terrain_domain:matterhorn-ski-paradise` | `piste_km_by_difficulty.advanced` | `unresolved` | No official aggregate difficulty split stored for the terrain domain. |
| `terrain_domain:matterhorn-ski-paradise` | `season_windows` | `not-applicable` | Season windows are tracked on Zermatt ski-area/pass scope rather than the shared terrain domain. |
| `destination:zermatt` | `trust_manifest.field_statuses.destination_identity` | `reviewed-no-change` | Retained verified-with-adjustment identity status. |
| `destination:zermatt` | `trust_manifest.field_statuses.country_region` | `reviewed-no-change` | Retained verified-with-adjustment country/region status. |
| `destination:zermatt` | `trust_manifest.field_statuses.destination_coordinates` | `reviewed-no-change` | Retained verified-with-adjustment coordinate status. |
| `destination:zermatt` | `trust_manifest.field_statuses.destination_elevation` | `reviewed-no-change` | Retained verified-with-adjustment elevation status. |
| `destination:zermatt` | `trust_manifest.field_statuses.season_window` | `reviewed-no-change` | Retained verified-with-adjustment season status with exact 2026/27 window now in catalog. |
| `destination:zermatt` | `trust_manifest.field_statuses.ski_areas` | `reviewed-no-change` | Retained verified-with-adjustment ski-area status. |
| `destination:zermatt` | `trust_manifest.field_statuses.stay_bases` | `reviewed-no-change` | Retained verified-with-adjustment stay-base status. |
| `destination:zermatt` | `trust_manifest.field_statuses.stay_base_quality_tier` | `reviewed-no-change` | Still estimated. |
| `destination:zermatt` | `trust_manifest.field_statuses.rental_quality_tier` | `reviewed-no-change` | Still estimated. |
| `destination:zermatt` | `trust_manifest.field_statuses.price_ranges` | `reviewed-no-change` | Still estimated for lodging/rental display ranges. |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `destination:zermatt` | `season_windows` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `[{"end_date": "2027-05-03", "season_label": "Winter 2026/27", "start_date": "2026-11-01", "status": "planned"}]` | Official winter ski-pass page publishes the 2026/27 winter season from 2026-11-01 to 2027-05-03. |  |
| `ski_area:zermatt-ski-area` | `season_windows` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `[{"end_date": "2027-05-03", "season_label": "Winter 2026/27", "start_date": "2026-11-01", "status": "planned"}]` | The Zermatt winter pass season window supports the ski-area season window. |  |
| `ski_area:zermatt-ski-area` | `total_piste_km` | [Ski passes winter online booking](https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter) | `200.0` | Official Zermatt winter pass page states the Zermatt pass gives access to up to 200 km on the Swiss-side sectors. |  |
| `stay_base:zermatt-zermatt` | `latitude` | [OpenStreetMap Zermatt relation](https://www.openstreetmap.org/relation/1685406) | `46.0212` | OSM relation 1685406 provides Zermatt town coordinates. | Rounded OSM latitude 46.0212076 to four decimals. |
| `stay_base:zermatt-zermatt` | `longitude` | [OpenStreetMap Zermatt relation](https://www.openstreetmap.org/relation/1685406) | `7.7493` | OSM relation 1685406 provides Zermatt town coordinates. | Rounded OSM longitude 7.7492540 to four decimals. |
| `stay_base:zermatt-zermatt` | `nearest_lift_name` | [OpenStreetMap Zermatt-Sunnegga funicular](https://www.openstreetmap.org/way/22330086) | `"Zermatt-Sunnegga funicular"` | OSM identifies the Zermatt-Sunnegga funicular as a nearby lift-access route. |  |
| `stay_base:zermatt-zermatt` | `nearest_lift_distance_m` | [OpenStreetMap Zermatt-Sunnegga funicular](https://www.openstreetmap.org/way/22330086) | `320` | The valley-side end of the Sunnegga funicular way is roughly 320 m from the Zermatt town relation reference point. | Rounded approximate way-endpoint distance to the nearest ten metres. |
| `stay_base:zermatt-zermatt` | `access_mode` | [Ski passes winter online booking](https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter) | `"walk"` | The official winter pass includes local bus access, and OSM places the Sunnegga funicular within walking distance of central Zermatt. | Normalized to walk for the central Zermatt stay base. |
| `stay_base:zermatt-zermatt` | `base_type` | [Zermatt region and Matterhorn](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `"town"` | Official region page describes Zermatt as a village/resort at the foot of the Matterhorn; catalog normalizes this stay base as town. |  |
| `stay_base:zermatt-zermatt` | `atmosphere_tags` | [Zermatt region and Matterhorn](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `["premium", "car_free", "scenic", "walkable_lifts", "glacier_access"]` | Official sources support premium, scenic, car-free, glacier-access, and walkable-lift character for Zermatt. | Tags are normalized Snowcast editorial labels from official/open evidence. |
| `stay_base:zermatt-zermatt` | `regional_data_ids` | [OpenStreetMap Zermatt relation](https://www.openstreetmap.org/relation/1685406) | `{"nearest_lift_osm_way_id": "22330086", "osm_relation_id": "1685406"}` | OSM relation 1685406 and Sunnegga funicular way 22330086 anchor the stay-base access references. |  |
| `stay_base:zermatt-zermatt` | `supported_skill_levels` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `["beginner", "intermediate", "advanced"]` | Official beginner ski-pass and Wolli Beginners Park references support beginner access in addition to intermediate/advanced terrain. |  |
| `lift_pass_product:zermatt-ski-pass` | `name` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `"Zermatt ski pass"` | Official Zermatt tariff page supports the local Zermatt ski-pass product, scope, and representative adult from-prices. |  |
| `lift_pass_product:zermatt-ski-pass` | `validity_scope` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `"single_ski_area"` | Official Zermatt tariff page supports the local Zermatt ski-pass product, scope, and representative adult from-prices. |  |
| `lift_pass_product:zermatt-ski-pass` | `is_default` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `true` | Official Zermatt tariff page supports the local Zermatt ski-pass product, scope, and representative adult from-prices. |  |
| `lift_pass_product:zermatt-ski-pass` | `valid_ski_area_ids` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `["zermatt-ski-area"]` | Official Zermatt tariff page supports the local Zermatt ski-pass product, scope, and representative adult from-prices. |  |
| `lift_pass_product:zermatt-ski-pass` | `prices` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `[{"amount": 89.0, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "from", "season_label": "Winter 2026/27 Zermatt low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}, {"amount": 209.0, "audience": "adult", "currency": "CHF", "duration_days": 3, "price_kind": "from", "season_label": "Winter 2026/27 Zermatt low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}, {"amount": 384.0, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "from", "season_label": "Winter 2026/27 Zermatt low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}]` | Official Zermatt tariff page supports the local Zermatt ski-pass product, scope, and representative adult from-prices. |  |
| `lift_pass_product:zermatt-international-ski-pass` | `name` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `"International ski pass Zermatt-Cervinia"` | Official Zermatt tariff and booking pages support the International pass covering local Zermatt plus Cervinia/Valtournenche access. |  |
| `lift_pass_product:zermatt-international-ski-pass` | `validity_scope` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `"regional_network"` | Official Zermatt tariff and booking pages support the International pass covering local Zermatt plus Cervinia/Valtournenche access. | Modeled as regional_network because the pass extends beyond the local Zermatt ski area. |
| `lift_pass_product:zermatt-international-ski-pass` | `is_default` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `false` | Official Zermatt tariff and booking pages support the International pass covering local Zermatt plus Cervinia/Valtournenche access. |  |
| `lift_pass_product:zermatt-international-ski-pass` | `valid_ski_area_ids` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `["zermatt-ski-area"]` | Official Zermatt tariff and booking pages support the International pass covering local Zermatt plus Cervinia/Valtournenche access. |  |
| `lift_pass_product:zermatt-international-ski-pass` | `terrain_domain_ids` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `["matterhorn-ski-paradise"]` | Official Zermatt tariff and booking pages support the International pass covering local Zermatt plus Cervinia/Valtournenche access. |  |
| `lift_pass_product:zermatt-international-ski-pass` | `external_validity_summary` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `"Covers the local Zermatt ski area and optional access to the Italian Breuil-Cervinia/Valtournenche terrain, subject to timetable, weather, and pass conditions."` | Official Zermatt tariff and booking pages support the International pass covering local Zermatt plus Cervinia/Valtournenche access. |  |
| `lift_pass_product:zermatt-international-ski-pass` | `prices` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `[{"amount": 104.0, "audience": "adult", "currency": "CHF", "duration_days": 1, "price_kind": "from", "season_label": "Winter 2026/27 International low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}, {"amount": 232.0, "audience": "adult", "currency": "CHF", "duration_days": 3, "price_kind": "from", "season_label": "Winter 2026/27 International low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}, {"amount": 432.0, "audience": "adult", "currency": "CHF", "duration_days": 6, "price_kind": "from", "season_label": "Winter 2026/27 International low-price windows", "source_url": "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes"}]` | Official Zermatt tariff and booking pages support the International pass covering local Zermatt plus Cervinia/Valtournenche access. |  |
| `terrain_domain:matterhorn-ski-paradise` | `name` | [Matterhorn Ski Paradise skiing](https://www.matterhornparadise.ch/en/experience/skiing) | `"Matterhorn Ski Paradise"` | Official Matterhorn Paradise sources support the cross-border ski-domain aggregate and Zermatt/Cervinia access scope. |  |
| `terrain_domain:matterhorn-ski-paradise` | `ski_area_refs` | [Ski passes winter online booking](https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter) | `[{"resort_id": "zermatt", "ski_area_id": "zermatt-ski-area"}, {"resort_id": "cervinia", "ski_area_id": "cervinia-ski-area"}]` | Official Matterhorn Paradise sources support the cross-border ski-domain aggregate and Zermatt/Cervinia access scope. | Terrain domain is an aggregate access domain and does not own weather evidence. |
| `terrain_domain:matterhorn-ski-paradise` | `metric_scope` | [Matterhorn Glacier Paradise](https://www.matterhornparadise.ch/en/experience/peaks/matterhorn-glacier-paradise) | `"aggregate"` | Official Matterhorn Paradise sources support the cross-border ski-domain aggregate and Zermatt/Cervinia access scope. | Terrain domain is an aggregate access domain and does not own weather evidence. |
| `terrain_domain:matterhorn-ski-paradise` | `total_piste_km` | [Matterhorn Ski Paradise skiing](https://www.matterhornparadise.ch/en/experience/skiing) | `360.0` | Official Matterhorn Paradise sources support the cross-border ski-domain aggregate and Zermatt/Cervinia access scope. |  |
| `terrain_domain:matterhorn-ski-paradise` | `total_lift_count` | [Matterhorn Ski Paradise skiing](https://www.matterhornparadise.ch/en/experience/skiing) | `54` | Official Matterhorn Paradise sources support the cross-border ski-domain aggregate and Zermatt/Cervinia access scope. |  |
| `terrain_domain:matterhorn-ski-paradise` | `base_elevation_m` | [Zermatt region and Matterhorn](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `1620` | Official region page states Zermatt-Matterhorn resort lies at 1620 metres above sea level. | Used as the lower resort-side elevation for the aggregate Matterhorn Ski Paradise terrain-domain elevation range. |
| `terrain_domain:matterhorn-ski-paradise` | `summit_elevation_m` | [Matterhorn Glacier Paradise](https://www.matterhornparadise.ch/en/experience/peaks/matterhorn-glacier-paradise) | `3883` | Official Matterhorn Paradise sources support the cross-border ski-domain aggregate and Zermatt/Cervinia access scope. |  |
| `terrain_domain:matterhorn-ski-paradise` | `source_urls` | [Matterhorn Ski Paradise skiing](https://www.matterhornparadise.ch/en/experience/skiing) | `["https://www.matterhornparadise.ch/en/experience/skiing", "https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter", "https://www.matterhornparadise.ch/en/experience/peaks/matterhorn-glacier-paradise"]` | Official Matterhorn Paradise sources support the cross-border ski-domain aggregate and Zermatt/Cervinia access scope. |  |
| `destination:zermatt` | `trust_manifest.field_statuses.terrain_groups` | [Matterhorn Ski Paradise skiing](https://www.matterhornparadise.ch/en/experience/skiing) | `"verified_with_adjustment"` | Official cross-border terrain aggregate now supports the terrain-domain/aggregate terrain trust group. |  |
| `destination:zermatt` | `trust_manifest.field_statuses.stay_base_lift_distance` | [OpenStreetMap Zermatt-Sunnegga funicular](https://www.openstreetmap.org/way/22330086) | `"verified_with_adjustment"` | OSM access reference now supports the stay-base lift-distance group. |  |
| `destination:zermatt` | `trust_manifest.field_statuses.supported_skill_levels` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `"verified_with_adjustment"` | Official beginner pass and park references now support beginner/intermediate/advanced suitability. |  |
| `destination:zermatt` | `trust_manifest.field_statuses.lift_pass_products` | [Zermatt ski pass prices](https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes) | `"verified_with_adjustment"` | Official tariff page now supports local and International pass products. |  |
| `destination:zermatt` | `trust_manifest.field_statuses.rental_examples` | [Glacier Sport rental](https://www.zermattglaciersport.ch/en/rental/) | `"verified_with_adjustment"` | Official Glacier Sport rental page verifies the rental example and published rental rates. |  |
| `destination:zermatt` | `trust_manifest.source_refs` | [Matterhorn Ski Paradise skiing](https://www.matterhornparadise.ch/en/experience/skiing) | `["https://www.matterhornparadise.ch/en/experience/skiing", "https://www.matterhornparadise.ch/en/information/tickets-prices/ski-passes", "https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter", "https://www.matterhornparadise.ch/en/experience/peaks/matterhorn-glacier-paradise", "https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn", "https://www.openstreetmap.org/relation/1685406", "https://www.openstreetmap.org/way/22330086", "https://www.openstreetmap.org/node/5475862597", "https://www.zermattglaciersport.ch/en/rental/"]` | Manifest source refs now use reviewed external official/open/provider URLs instead of internal sprint notes. |  |
| `destination:zermatt` | `trust_manifest.notes` | [Matterhorn Ski Paradise skiing](https://www.matterhornparadise.ch/en/experience/skiing) | `["Full static curation pass completed with official Matterhorn Paradise/Zermatt Bergbahnen sources, OSM access references, and Glacier Sport rental evidence.", "Local Zermatt ski-area terrain is stored as the Zermatt-only 200 km pass scope; the 360 km cross-border Matterhorn Ski Paradise claim is modeled as a shared terrain domain for optional International pass access.", "Piste difficulty split, local lift count, lodging/rental price ranges, and normalized quality tiers remain unresolved or estimated where reviewed official sources did not publish enough scoped evidence."]` | Manifest notes document local versus cross-border terrain scope and unresolved fields. |  |

## Ranking Impact

Default comparison diagnostics wrote 12 DB-backed rows across 11 groups to artifacts/ranking-comparison. Zermatt appears in scenario switzerland_intermediate: current rank 2, candidate rank 3, rank_delta=1, with terrain_source_scope=ski_area and terrain_source_id=zermatt-ski-area. The artifact remains diagnostic-only and does not change production ordering.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-27-zermatt-full-curation.json --markdown-output docs/catalog-curation/2026-06-27-zermatt-full-curation.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`
- `git diff --check`

## Caveats

- Local Zermatt lift count remains unresolved because reviewed official sources expose 54 lifts for the cross-border Matterhorn Ski Paradise aggregate, not a clearly scoped Zermatt-only lift count.
- Piste difficulty split remains unresolved because reviewed official sources did not publish a local or aggregate beginner/intermediate/advanced kilometer split.
- Rental/stay price ranges and normalized quality tiers remain estimated; Glacier Sport publishes CHF rental rates but the current static rental price_range parser is EUR-normalized.
