# Chamonix Mont-Blanc Catalog Curation

Expanded Chamonix from a pass-only patch into a full destination field sweep. Split the previous aggregate ski-area placeholder into modeled local ski areas, added aggregate Chamonix Le Pass terrain, added representative stay bases, kept scoped lift-pass products, and documented unresolved lodging price, rental price, exact per-child difficulty split, and weather-coordinate caveats. A follow-up pass added child-scoped piste/lift totals for Brevent-Flegere, Grands Montets, and Balme from reviewed provider pages while keeping the official Chamonix Le Pass aggregate as aggregate/pass-accessible terrain.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:chamonix-mont-blanc` | `ski_areas` | `["chamonix-mont-blanc-ski-area"]` | `["brevent-flegere", "grands-montets", "balme-le-tour-vallorcine", "les-houches-saint-gervais"]` | `verified_with_adjustment` | yes |
| `terrain_group:chamonix-le-pass-terrain` | `total_piste_km` | `null` | `110` | `verified_with_adjustment` | yes |
| `terrain_group:chamonix-le-pass-terrain` | `total_lift_count` | `null` | `43` | `verified_with_adjustment` | yes |
| `terrain_group:chamonix-le-pass-terrain` | `source_urls` | `null` | `["https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass"]` | `verified_with_adjustment` | no |
| `ski_area:brevent-flegere` | `total_piste_km` | `null` | `56` | `verified_with_adjustment` | yes |
| `ski_area:brevent-flegere` | `total_lift_count` | `null` | `17` | `verified_with_adjustment` | yes |
| `ski_area:grands-montets` | `total_piste_km` | `null` | `29` | `verified_with_adjustment` | yes |
| `ski_area:grands-montets` | `total_lift_count` | `null` | `7` | `verified_with_adjustment` | yes |
| `ski_area:balme-le-tour-vallorcine` | `total_piste_km` | `null` | `29` | `verified_with_adjustment` | yes |
| `ski_area:balme-le-tour-vallorcine` | `total_lift_count` | `null` | `13` | `verified_with_adjustment` | yes |
| `ski_area:les-houches-saint-gervais` | `total_piste_km` | `null` | `31` | `verified` | yes |
| `ski_area:les-houches-saint-gervais` | `total_lift_count` | `null` | `14` | `verified_with_adjustment` | yes |
| `lift_pass_product:chamonix-le-pass` | `validity_scope` | `"single_ski_area"` | `"local_multi_area"` | `verified_with_adjustment` | no |
| `lift_pass_product:chamonix-le-pass` | `valid_ski_area_ids` | `["chamonix-mont-blanc-ski-area"]` | `["brevent-flegere", "grands-montets", "balme-le-tour-vallorcine"]` | `verified_with_adjustment` | no |
| `lift_pass_product:mont-blanc-unlimited` | `valid_ski_area_ids` | `["chamonix-mont-blanc-ski-area"]` | `["brevent-flegere", "grands-montets", "balme-le-tour-vallorcine", "les-houches-saint-gervais"]` | `verified_with_adjustment` | no |
| `lift_pass_product:les-houches-saint-gervais-skipass` | `prices` | `null` | `[{"amount_max": 59.0, "amount_min": 35.3, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "range", "season_label": "Winter 2025/26 Les Houches season range", "source_url": "https://leshouches.montblancnaturalresort.com/en/ticketing/houches-saint-gervais-skipass"}]` | `verified` | no |
| `destination:chamonix-mont-blanc` | `stay_bases` | `["chamonix-mont-blanc-chamonix"]` | `["chamonix-mont-blanc-chamonix", "chamonix-mont-blanc-argentiere", "chamonix-mont-blanc-les-houches"]` | `verified_with_adjustment` | yes |
| `destination:chamonix-mont-blanc` | `trust_manifest.field_statuses.terrain_groups` | `"needs_source"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:chamonix-mont-blanc` | `trust_manifest.field_statuses.stay_base_lift_distance` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:chamonix-mont-blanc` | `trust_manifest.field_statuses.rental_examples` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `destination:chamonix-mont-blanc` | `ski_areas` | [CHAMONIX Le Pass](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `"Brevent-Flegere, Grands Montets, Balme - Le Tour - Vallorcine, plus beginner areas; areas are not linked except Brevent-Flegere."` | Official Chamonix Le Pass page lists the local Chamonix ski areas and states that the areas and sites are not linked except Brevent-Flegere. | Replaced the previous single aggregate ski_area_id with modeled local ski areas so pass and terrain facts are scoped correctly. |
| `terrain_group:chamonix-le-pass-terrain` | `total_piste_km` | [CHAMONIX Le Pass](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `110` | Official Chamonix Le Pass page lists 110 km of slopes for the aggregate local Chamonix pass territory. | Stored as aggregate terrain_group evidence rather than copying the total onto one child ski area. |
| `terrain_group:chamonix-le-pass-terrain` | `total_lift_count` | [CHAMONIX Le Pass](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `{"cable_car": 2, "chairlifts": 14, "gondolas": 6, "skilifts": 21}` | Official Chamonix Le Pass page lists lift inventory for the aggregate local pass territory. | Summed listed lift categories to total_lift_count=43. |
| `terrain_group:chamonix-le-pass-terrain` | `source_urls` | [CHAMONIX Le Pass](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `["https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass"]` | Official Chamonix Le Pass page is the reviewed source for the aggregate/pass-accessible terrain group. |  |
| `ski_area:brevent-flegere` | `total_piste_km` | [Skiresort.info Brevent-Flegere Chamonix](https://www.skiresort.info/ski-resort/brevent-flegere-chamonix/) | `56` | Reviewed provider page publishes child-scoped slope length for Brevent-Flegere. | Kept as child ski-area terrain; it does not replace the official 110 km Chamonix Le Pass aggregate. |
| `ski_area:brevent-flegere` | `total_lift_count` | [Skiresort.info Brevent-Flegere Chamonix](https://www.skiresort.info/ski-resort/brevent-flegere-chamonix/) | `17` | Reviewed provider page publishes child-scoped lift count for Brevent-Flegere. | Kept as child ski-area terrain; official Le Pass lift inventory remains aggregate/pass-accessible terrain. |
| `ski_area:grands-montets` | `total_piste_km` | [Skiresort.info Grands Montets - Argentiere Chamonix](https://www.skiresort.info/ski-resort/grands-montets-argentiere-chamonix/) | `29` | Reviewed provider page publishes child-scoped slope length for Grands Montets. | Kept as child ski-area terrain; it does not replace the official 110 km Chamonix Le Pass aggregate. |
| `ski_area:grands-montets` | `total_lift_count` | [Skiresort.info Grands Montets - Argentiere Chamonix](https://www.skiresort.info/ski-resort/grands-montets-argentiere-chamonix/) | `7` | Reviewed provider page publishes child-scoped lift count for Grands Montets. | Kept as child ski-area terrain; official Le Pass lift inventory remains aggregate/pass-accessible terrain. |
| `ski_area:balme-le-tour-vallorcine` | `total_piste_km` | [Skiresort.info Balme - Les Autannes - Vallorcine/Le Tour](https://www.skiresort.info/ski-resort/balme-les-autannes-vallorcine-le-tour/) | `29` | Reviewed provider page publishes child-scoped slope length for Balme - Le Tour - Vallorcine. | Kept as child ski-area terrain; it does not replace the official 110 km Chamonix Le Pass aggregate. |
| `ski_area:balme-le-tour-vallorcine` | `total_lift_count` | [Skiresort.info Balme - Les Autannes - Vallorcine/Le Tour](https://www.skiresort.info/ski-resort/balme-les-autannes-vallorcine-le-tour/) | `13` | Reviewed provider page publishes child-scoped lift count for Balme - Le Tour - Vallorcine. | Kept as child ski-area terrain; official Le Pass lift inventory remains aggregate/pass-accessible terrain. |
| `ski_area:les-houches-saint-gervais` | `total_piste_km` | [Les Houches - Saint-Gervais ski pass](https://leshouches.montblancnaturalresort.com/en/ticketing/houches-saint-gervais-skipass) | `31` | Official Les Houches - Saint-Gervais pass page lists 31 km of slopes. |  |
| `ski_area:les-houches-saint-gervais` | `total_lift_count` | [Les Houches - Saint-Gervais ski pass](https://leshouches.montblancnaturalresort.com/en/ticketing/houches-saint-gervais-skipass) | `{"cable_car": 1, "chairlifts": 3, "gondolas": 8, "telecabine": 1, "tramway": 1}` | Official Les Houches - Saint-Gervais page lists the lift inventory for that ski area. | Summed listed transport categories to total_lift_count=14. |
| `lift_pass_product:chamonix-le-pass` | `validity_scope` | [CHAMONIX Le Pass](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `"Chamonix ski areas: Brevent-Flegere, Grands Montets, Balme - Le Tour - Vallorcine; areas are not linked except Brevent-Flegere."` | The pass covers multiple modeled local Chamonix ski areas. | Normalized from the earlier single_ski_area placeholder to local_multi_area. |
| `lift_pass_product:chamonix-le-pass` | `valid_ski_area_ids` | [CHAMONIX Le Pass](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `["Brevent-Flegere", "Grands Montets", "Balme - Le Tour - Vallorcine"]` | Official pass page lists the local ski areas covered by Chamonix Le Pass. | Mapped official area names to local Snowcast ski_area_ids. |
| `lift_pass_product:mont-blanc-unlimited` | `valid_ski_area_ids` | [Mont-Blanc Unlimited Ski Pass](https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited) | `"Chamonix ski areas, Les Houches - Saint-Gervais, Evasion Mont Blanc, Italy, Switzerland, and excursion sites."` | Official Mont-Blanc Unlimited page lists local Chamonix ski areas and Les Houches plus broader external access. | Only modeled local ski areas are referenced directly; other external areas stay in external_validity_summary. |
| `lift_pass_product:les-houches-saint-gervais-skipass` | `prices` | [Les Houches - Saint-Gervais ski pass](https://leshouches.montblancnaturalresort.com/en/ticketing/houches-saint-gervais-skipass) | `[{"amount_max": 59.0, "amount_min": 35.3, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "range", "season_label": "Winter 2025/26 Les Houches season range", "source_url": "https://leshouches.montblancnaturalresort.com/en/ticketing/houches-saint-gervais-skipass"}]` | Official Les Houches - Saint-Gervais ticket page lists adult 1-day dynamic price range. | Added as a non-default single-ski-area product because it has materially different terrain and price from Chamonix Le Pass. |
| `destination:chamonix-mont-blanc` | `stay_bases` | [Chamonix-Mont-Blanc Valley village resorts](https://en.chamonix.com/chamonix-mont-blanc-valley/the-village-resorts) | `["Chamonix", "Argentiere", "Les Houches"]` | Official Chamonix valley pages distinguish Chamonix, Argentiere, and Les Houches as meaningful resort villages for ski-trip base selection. | Added representative stay bases while leaving lodging price and quality tiers as estimates. |
| `destination:chamonix-mont-blanc` | `trust_manifest.field_statuses.terrain_groups` | [CHAMONIX Le Pass](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `"Official aggregate terrain metrics for Chamonix Le Pass."` | Official pass territory metrics support moving terrain_groups from needs_source to verified_with_adjustment. | Trust status summarizes aggregate terrain facts separated from child ski-area facts. |
| `destination:chamonix-mont-blanc` | `trust_manifest.field_statuses.stay_base_lift_distance` | [Domaine skiable Brevent-Flegere](https://en.chamonix.com/things-to-see-and-do/sports-and-outdoor/skiing-in-chamonix-mont-blanc-valley/list-of-ski-areas/domaine-skiable-brevent-flegere) | `"Access from the heart of Chamonix for Brevent and from Les Praz for Flegere; bus and train stops listed."` | Official access wording supports source-backed near-access classification for representative Chamonix valley bases. | Detailed meter distances remain unresolved; trust status reflects official access-mode evidence rather than exact geometry. |
| `destination:chamonix-mont-blanc` | `trust_manifest.field_statuses.rental_examples` | [Sport 2000 La Ginabelle Chamonix-Mont-Blanc](https://en.chamonix.com/plan-my-stay/usual-information-services/sports-items/sport-2000-la-ginabelle) | `"CHAMSPORT ski rental shops in central Chamonix with recent equipment for all levels."` | Official Chamonix listing supports the rental provider identity in the catalog. | Rental price range remains estimated because the official listing does not publish a stable ski-package price range. |

## Ranking Impact

Default comparison diagnostics wrote 12 rows to artifacts/ranking-comparison. Review is required because the Chamonix ski-area topology, aggregate terrain, stay-base coverage, and supported-skill inputs changed.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-23-chamonix-mont-blanc.json --markdown-output docs/catalog-curation/2026-06-23-chamonix-mont-blanc.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`
- `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_validation.py tests/test_repository.py tests/test_resort_fit.py -q`

## Caveats

- Chamonix official sources publish Chamonix Le Pass terrain as aggregate metrics; Brevent-Flegere, Grands Montets, and Balme child piste/lift totals now use reviewed child-scoped fallback sources and must not be summed to override the official 110 km / 43 lift pass aggregate.
- Child ski-area difficulty-kilometer splits remain unresolved because reviewed sources do not publish stable blue/red/black kilometer splits for the three Chamonix Le Pass child areas.
- Mont-Blanc Unlimited covers broad external terrain and remains modeled as pass-product scope rather than local terrain truth.
- Sector coordinates are normalized lookup points from open geodata/source context and should not be treated as exact lift-station geometry.
- Lodging price ranges, stay-base quality tiers, supported skill levels, and rental price ranges remain curated estimates pending a dedicated price-sampling policy.
- Exact complete future operating windows remain unresolved across all Chamonix sectors; fallback season months remain in place.

## Field Coverage Matrix

Destination fields:

| Field | Decision | Note |
| --- | --- | --- |
| `resort_id`, `name`, `country`, `region` | reviewed-no-change | Stable Chamonix destination identity is retained; display-name accent/hyphen normalization remains unchanged. |
| `price_level` | reviewed-no-change | `high` remains a product tier; detailed lodging and rental price bands remain estimate-backed. |
| `latitude`, `longitude` | reviewed-no-change | Destination coordinate remains the Chamonix-Mont-Blanc administrative lookup point. |
| `base_elevation_m`, `summit_elevation_m` | unresolved | Current destination summit is compatible with Aiguille du Midi identity, not local piste summit; no change made without an owner decision on weather/elevation semantics. |
| `season_start_month`, `season_end_month` | reviewed-no-change | Broad November-May destination fallback remains compatible with official pass/rate windows. |
| `season_windows` | unresolved | Complete future operating windows vary by sector and were not added as destination truth. |
| `ski_areas` | changed | Replaced one aggregate placeholder with modeled local Chamonix valley ski areas. |
| `terrain_groups` | changed | Added Chamonix Le Pass aggregate/pass-accessible metrics and source URLs so 110 km / 43 lifts are not copied to one child area. |
| `lift_pass_products` | changed | Kept Chamonix Le Pass and Mont-Blanc Unlimited, corrected their scope, and added Les Houches single-area product. |
| `stay_bases` | changed | Added Chamonix, Argentiere, and Les Houches as representative ski-trip bases. |
| `rentals` | reviewed-no-change | Cham'Sport provider identity is source-backed; rental price range remains estimated. |

Ski-area fields:

| Ski Area | Field | Decision | Note |
| --- | --- | --- | --- |
| Brevent-Flegere | `ski_area_id`, `name`, `latitude`, `longitude`, `base_elevation_m`, `summit_elevation_m`, `season_start_month`, `season_end_month` | changed | Added as a local modeled ski area with normalized lookup coordinates and official sector evidence. |
| Brevent-Flegere | `total_piste_km`, `total_lift_count` | changed | Added 56 km and 17 lifts from reviewed child-scoped provider evidence; these child values do not replace the official Chamonix Le Pass aggregate. |
| Brevent-Flegere | `season_windows`, `piste_km_by_difficulty.*` | unresolved | Exact future sector windows and stable difficulty-kilometer splits remain unresolved. |
| Grands Montets | `ski_area_id`, `name`, `latitude`, `longitude`, `base_elevation_m`, `summit_elevation_m`, `season_start_month`, `season_end_month` | changed | Added as a local modeled ski area with official altitude context and normalized lookup coordinates. |
| Grands Montets | `total_piste_km`, `total_lift_count` | changed | Added 29 km and 7 lifts from reviewed child-scoped provider evidence; these child values do not replace the official Chamonix Le Pass aggregate. |
| Grands Montets | `season_windows`, `piste_km_by_difficulty.*` | unresolved | Exact future sector windows, top-access semantics, and stable difficulty-kilometer splits remain unresolved. |
| Balme - Le Tour - Vallorcine | `ski_area_id`, `name`, `latitude`, `longitude`, `base_elevation_m`, `summit_elevation_m`, `season_start_month`, `season_end_month` | changed | Added as a local modeled ski area with normalized lookup coordinates. |
| Balme - Le Tour - Vallorcine | `total_piste_km`, `total_lift_count` | changed | Added 29 km and 13 lifts from reviewed child-scoped provider evidence; these child values do not replace the official Chamonix Le Pass aggregate. |
| Balme - Le Tour - Vallorcine | `season_windows`, `piste_km_by_difficulty.*` | unresolved | Exact future sector windows and stable difficulty-kilometer splits remain unresolved. |
| Les Houches - Saint-Gervais | `ski_area_id`, `name`, `latitude`, `longitude`, `base_elevation_m`, `summit_elevation_m`, `season_start_month`, `season_end_month` | changed | Added because it is a distinct local valley area covered by Mont-Blanc Unlimited and its own pass product. |
| Les Houches - Saint-Gervais | `total_piste_km`, `total_lift_count` | changed | Added 31 km and 14 summed lift/transport installations from the official ticket page. |
| Les Houches - Saint-Gervais | `season_windows`, `piste_km_by_difficulty.*` | unresolved | Official source provides run counts by color, not difficulty kilometers. |

Terrain-group fields:

| Terrain Group | Field | Decision | Note |
| --- | --- | --- | --- |
| Chamonix Le Pass terrain | `terrain_group_id`, `name`, `ski_area_ids`, `metric_scope` | changed | Added aggregate group across Brevent-Flegere, Grands Montets, and Balme. |
| Chamonix Le Pass terrain | `total_piste_km`, `total_lift_count`, `source_urls` | changed | Added 110 km, 43 summed lifts, and source URLs from official pass territory metrics. |
| Chamonix Le Pass terrain | `piste_km_by_difficulty.*` | unresolved | Source gives run counts by color, not kilometers by difficulty. |

Lift-pass product fields:

| Product | Field | Decision | Note |
| --- | --- | --- | --- |
| Chamonix Le Pass | `lift_pass_product_id`, `name`, `is_default`, `prices` | reviewed-no-change | Existing product identity/default and adult 1-day dynamic price range remain valid. |
| Chamonix Le Pass | `validity_scope`, `valid_ski_area_ids` | changed | Scope changed to `local_multi_area` and references the modeled local ski areas it covers. |
| Mont-Blanc Unlimited | `lift_pass_product_id`, `name`, `is_default`, `prices` | reviewed-no-change | Existing regional product identity and representative adult price examples remain valid. |
| Mont-Blanc Unlimited | `valid_ski_area_ids`, `external_validity_summary` | changed | References modeled local ski areas directly and keeps broader France/Italy/Switzerland validity in the summary. |
| Les Houches - Saint-Gervais ski pass | all fields | changed | Added as a non-default `single_ski_area` product because it changes both terrain scope and price. |

Stay-base fields:

| Stay Base | Field | Decision | Note |
| --- | --- | --- | --- |
| Chamonix | `stay_base_id`, `name`, `price_range`, `quality`, `lift_distance` | reviewed-no-change | Stable central base retained; price and quality remain estimated. |
| Chamonix | `supported_skill_levels`, `latitude`, `longitude`, `nearest_lift_name`, `access_mode`, `base_type`, `atmosphere_tags`, `regional_data_ids` | changed | Added official/open-data-backed access and identity metadata, including beginner support from official beginner-area evidence. |
| Argentiere | all fields | changed | Added representative Grands Montets-oriented stay base; price and quality are estimates. |
| Les Houches | all fields | changed | Added representative family/beginner-friendly stay base; price and quality are estimates. |
| All stay bases | `price_min`, `price_max`, exact meter distance | unresolved | Loader can derive price bounds from `price_range`; exact source-backed lodging bands and lift-distance meters need a later sweep. |

Rental fields:

| Rental | Field | Decision | Note |
| --- | --- | --- | --- |
| Cham'Sport | `name`, `quality`, `lift_distance` | reviewed-no-change | Provider identity is supported by the official Chamonix listing. |
| Cham'Sport | `price_range`, `price_min`, `price_max` | unresolved | Official listing does not publish a stable ski-package price range; existing range remains estimated. |

Trust fields:

| Field Group | Decision | Note |
| --- | --- | --- |
| `ski_areas`, `lift_pass_products`, `terrain_groups`, `stay_bases`, `stay_base_lift_distance`, `rental_examples` | changed or reviewed | Source refs now cover topology, pass scope, aggregate terrain, stay-base identity/access, and rental identity. |
| `stay_base_quality_tier`, `supported_skill_levels`, `rental_quality_tier`, `price_ranges` | unresolved/estimated | These remain estimates until a dedicated quality and price sampling policy exists. |
