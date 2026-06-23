# Zell am See-Kaprun Catalog Curation

Reviewed Zell am See-Kaprun destination, ski-area, stay-base, pass-product, and aggregate terrain fields against official operator/tourism pages, OSM identity and lift geometry, and reviewed editorial aggregate terrain evidence. Added source-backed lift-pass examples, explicit Ski ALPIN CARD validity scope, terrain metrics, an aggregate Kitzsteinhorn/Maiskogel terrain group, and stay-base access metadata while leaving unresolved season-window, quality, lodging-price, and child-area difficulty-split decisions unchanged.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:zell-am-see-kaprun` | `lift_pass_prices` | `[]` | `[{"amount": 82, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 440, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 74, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 396, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}]` | `verified` | no |
| `ski_area:kitzsteinhorn` | `total_piste_km` | `null` | `41` | `verified` | yes |
| `ski_area:maiskogel` | `total_piste_km` | `null` | `20` | `verified` | yes |
| `ski_area:maiskogel` | `total_lift_count` | `null` | `3` | `verified` | yes |
| `ski_area:schmittenhoehe` | `total_piste_km` | `null` | `77` | `verified` | yes |
| `ski_area:schmittenhoehe` | `total_lift_count` | `null` | `27` | `verified` | yes |
| `ski_area:schmittenhoehe` | `piste_km_by_difficulty` | `null` | `{"advanced": 19, "beginner": 30, "intermediate": 28}` | `verified` | yes |
| `stay_base:zell-am-see-kaprun-kaprun` | `latitude` | `null` | `47.2714` | `verified_with_adjustment` | no |
| `stay_base:zell-am-see-kaprun-kaprun` | `longitude` | `null` | `12.7574` | `verified_with_adjustment` | no |
| `stay_base:zell-am-see-kaprun-kaprun` | `nearest_lift_name` | `null` | `"MK Maiskogelbahn"` | `verified` | no |
| `stay_base:zell-am-see-kaprun-kaprun` | `nearest_lift_distance_m` | `null` | `266` | `verified_with_adjustment` | yes |
| `stay_base:zell-am-see-kaprun-kaprun` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:zell-am-see-kaprun-kaprun` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:zell-am-see-kaprun-kaprun` | `atmosphere_tags` | `[]` | `["family_friendly", "glacier_access", "ski_in_ski_out"]` | `verified_with_adjustment` | no |
| `stay_base:zell-am-see-kaprun-kaprun` | `regional_data_ids` | `{}` | `{"nearest_lift_osm_way_id": "158348741", "osm_relation_id": "945977"}` | `verified` | no |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `lift_distance` | `"medium"` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `latitude` | `null` | `47.324` | `verified_with_adjustment` | no |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `longitude` | `null` | `12.7963` | `verified_with_adjustment` | no |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `nearest_lift_name` | `null` | `"cityXpress"` | `verified` | no |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `nearest_lift_distance_m` | `null` | `186` | `verified_with_adjustment` | yes |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `base_type` | `null` | `"town"` | `verified` | no |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `atmosphere_tags` | `[]` | `["lake_town", "panoramic", "family_friendly", "apres_ski"]` | `verified_with_adjustment` | no |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `regional_data_ids` | `{}` | `{"nearest_lift_osm_way_id": "197183389", "osm_relation_id": "945962"}` | `verified` | no |
| `destination:zell-am-see-kaprun` | `trust_manifest.field_statuses.stay_base_lift_distance` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-alpin-card` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-alpin-card` | `valid_ski_area_ids` | `null` | `["kitzsteinhorn", "maiskogel", "schmittenhoehe"]` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-alpin-card` | `prices` | `null` | `[{"amount": 82, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 440, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 74, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 396, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}]` | `verified` | no |
| `terrain_group:kitzsteinhorn-maiskogel` | `total_piste_km` | `null` | `62.5` | `verified_with_adjustment` | yes |
| `terrain_group:kitzsteinhorn-maiskogel` | `total_lift_count` | `null` | `24` | `verified_with_adjustment` | yes |
| `terrain_group:kitzsteinhorn-maiskogel` | `piste_km_by_difficulty` | `null` | `{"advanced": 9, "beginner": 30.5, "intermediate": 23}` | `verified_with_adjustment` | yes |
| `destination:zell-am-see-kaprun` | `trust_manifest.field_statuses.lift_pass_products` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:zell-am-see-kaprun` | `trust_manifest.field_statuses.terrain_groups` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `destination:zell-am-see-kaprun` | `lift_pass_prices` | [Ski pass prices Zell am See-Kaprun winter 2026/27](https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes) | `[{"amount": 82, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 440, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 74, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 396, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}]` | Official tariff page lists adult 1-day and 6-day Ski ALPIN CARD prices for main season and winter-start/bonus season. |  |
| `ski_area:kitzsteinhorn` | `total_piste_km` | [Winter 2025/26 Kitzsteinhorn press information](https://www.kitzsteinhorn.at/en/service/backstage/press/winter-2025-26-pr15634) | `41` | Official operator press page states that Kitzsteinhorn has 41 km of slopes across blue, red, and black runs. |  |
| `ski_area:maiskogel` | `total_piste_km` | [Maiskogel family ski resort](https://www.kitzsteinhorn.at/en/winter/maiskogel-ski-board) | `20` | Official Maiskogel page lists 20 kilometres of pistes. |  |
| `ski_area:maiskogel` | `total_lift_count` | [Maiskogel family ski resort](https://www.kitzsteinhorn.at/en/winter/maiskogel-ski-board) | `3` | Official Maiskogel page lists 3 cable cars and lifts. |  |
| `ski_area:schmittenhoehe` | `total_piste_km` | [The Company Schmittenhoehebahn AG](https://www.schmitten.at/en/Company) | `77` | Official company facts page lists 77 km of slopes for Schmittenhoehe. |  |
| `ski_area:schmittenhoehe` | `total_lift_count` | [The Company Schmittenhoehebahn AG](https://www.schmitten.at/en/Company) | `27` | Official company facts page lists 27 cable cars and lifts. |  |
| `ski_area:schmittenhoehe` | `piste_km_by_difficulty` | [The Company Schmittenhoehebahn AG](https://www.schmitten.at/en/Company) | `{"advanced": 19, "beginner": 30, "intermediate": 28}` | Official company facts page splits Schmittenhoehe slopes into 30 km blue, 28 km red, and 19 km black runs. |  |
| `stay_base:zell-am-see-kaprun-kaprun` | `latitude` | [OpenStreetMap relation 945977 Kaprun](https://www.openstreetmap.org/relation/945977) | `47.2713898` | OSM administrative relation for Kaprun provides the town coordinate used for stay-base identity. | Rounded to 4 decimal places for catalog consistency. |
| `stay_base:zell-am-see-kaprun-kaprun` | `longitude` | [OpenStreetMap relation 945977 Kaprun](https://www.openstreetmap.org/relation/945977) | `12.7573679` | OSM administrative relation for Kaprun provides the town coordinate used for stay-base identity. | Rounded to 4 decimal places for catalog consistency. |
| `stay_base:zell-am-see-kaprun-kaprun` | `nearest_lift_name` | [OpenStreetMap way 158348741 MK Maiskogelbahn](https://www.openstreetmap.org/way/158348741) | `"MK Maiskogelbahn"` | OSM station way identifies MK Maiskogelbahn as the nearest lift station used for Kaprun access. |  |
| `stay_base:zell-am-see-kaprun-kaprun` | `nearest_lift_distance_m` | [OpenStreetMap way 158348741 MK Maiskogelbahn](https://www.openstreetmap.org/way/158348741) | `266` | Computed Haversine distance from OSM Kaprun relation coordinate to the OSM MK Maiskogelbahn station coordinate. |  |
| `stay_base:zell-am-see-kaprun-kaprun` | `access_mode` | [Kaprun-Kitzsteinhorn connected press information](https://www.kitzsteinhorn.at/en/service/backstage/press/kaprun-kitzsteinhorn-connected-as-of-30-nov.--pr5487) | `"within easy walking distance; no car required"` | Official K-ONNECTION press page describes Kaprun Center as within easy walking distance for locals and guests in town and says no car is required. | Official walk-access wording is normalized to access_mode=walk. |
| `stay_base:zell-am-see-kaprun-kaprun` | `base_type` | [OpenStreetMap relation 945977 Kaprun](https://www.openstreetmap.org/relation/945977) | `"village"` | OSM classifies Kaprun as a village administrative place. |  |
| `stay_base:zell-am-see-kaprun-kaprun` | `atmosphere_tags` | [Maiskogel family ski resort](https://www.kitzsteinhorn.at/en/winter/maiskogel-ski-board) | `"family mountain close to town with Kitzsteinhorn glacier access and ski-in/ski-out connection"` | Official pages describe Maiskogel as family-oriented and close to town, while the K-ONNECTION source supports ski-in/ski-out glacier access from Kaprun. | Official descriptive phrases are normalized into Snowcast atmosphere tags. |
| `stay_base:zell-am-see-kaprun-kaprun` | `regional_data_ids` | [OpenStreetMap relation 945977 Kaprun](https://www.openstreetmap.org/relation/945977) | `{"nearest_lift_osm_way_id": "158348741", "osm_relation_id": "945977"}` | OSM relation and station way provide stable identifiers for Kaprun and MK Maiskogelbahn. |  |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `lift_distance` | [OpenStreetMap way 197183389 cityXpress](https://www.openstreetmap.org/way/197183389) | `186` | Computed OSM distance from Zell am See town relation coordinate to the cityXpress station is inside the near-access bucket. | Meter distance is normalized to Snowcast lift_distance=near. |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `latitude` | [OpenStreetMap relation 945962 Zell am See](https://www.openstreetmap.org/relation/945962) | `47.3239636` | OSM administrative relation for Zell am See provides the town coordinate used for stay-base identity. | Rounded to 4 decimal places for catalog consistency. |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `longitude` | [OpenStreetMap relation 945962 Zell am See](https://www.openstreetmap.org/relation/945962) | `12.7963165` | OSM administrative relation for Zell am See provides the town coordinate used for stay-base identity. | Rounded to 4 decimal places for catalog consistency. |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `nearest_lift_name` | [OpenStreetMap way 197183389 cityXpress](https://www.openstreetmap.org/way/197183389) | `"cityXpress"` | OSM station way identifies cityXpress as the nearest lift station used for Zell am See access. |  |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `nearest_lift_distance_m` | [OpenStreetMap way 197183389 cityXpress](https://www.openstreetmap.org/way/197183389) | `186` | Computed Haversine distance from OSM Zell am See relation coordinate to the OSM cityXpress station coordinate. |  |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `access_mode` | [Ski resorts Zell am See-Kaprun](https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-resorts) | `"three access points in Zell am See"` | Official regional page describes Schmittenhoehe access points in Zell am See, with cityXpress confirmed by OSM as near the town center coordinate. | Official access-point wording plus OSM distance is normalized to access_mode=walk. |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `base_type` | [OpenStreetMap relation 945962 Zell am See](https://www.openstreetmap.org/relation/945962) | `"town"` | OSM classifies Zell am See as a town administrative place. |  |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `atmosphere_tags` | [Panorama mountain Schmittenhoehe](https://www.zellamsee-kaprun.com/en/experience/attractions/schmittenhoehe) | `"local mountain with Lake Zell panorama, family highlights, sunny terraces, and ski huts"` | Official Schmittenhoehe attraction page supports lake/panorama, family-friendly, and hut/apres-style character for the Zell am See stay base. | Official descriptive phrases are normalized into Snowcast atmosphere tags. |
| `stay_base:zell-am-see-kaprun-zell-am-see` | `regional_data_ids` | [OpenStreetMap relation 945962 Zell am See](https://www.openstreetmap.org/relation/945962) | `{"nearest_lift_osm_way_id": "197183389", "osm_relation_id": "945962"}` | OSM relation and station way provide stable identifiers for Zell am See and cityXpress. |  |
| `destination:zell-am-see-kaprun` | `trust_manifest.field_statuses.stay_base_lift_distance` | [Kaprun-Kitzsteinhorn connected press information](https://www.kitzsteinhorn.at/en/service/backstage/press/kaprun-kitzsteinhorn-connected-as-of-30-nov.--pr5487) | `"OSM lift distances plus official walk-access descriptions"` | Kaprun and Zell am See stay-base access now have OSM distance measurements and official access evidence, allowing the manifest group to move from estimated to verified_with_adjustment. | Multiple source-backed access facts are summarized as the trust-manifest status verified_with_adjustment. |
| `lift_pass_product:ski-alpin-card` | `validity_scope` | [Kitzsteinhorn ALPIN CARD](https://www.kitzsteinhorn.at/en/tickets-prices/alpin-card) | `"Ski ALPIN CARD spans Kitzsteinhorn, Maiskogel, Schmittenhoehe, and Skicircus validity."` | Official ALPIN CARD page describes the pass as a regional network product spanning the modeled local ski areas plus external Skicircus terrain. | Normalized official pass-network wording to validity_scope=regional_network. |
| `lift_pass_product:ski-alpin-card` | `valid_ski_area_ids` | [Ski pass prices Zell am See-Kaprun winter 2026/27](https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes) | `"Ski passes valid for Schmittenhoehe, Kitzsteinhorn Kaprun, and Skicircus."` | Official tariff page ties Ski ALPIN CARD validity to the local modeled ski areas and broader network. | Mapped official named areas to local ski_area_ids kitzsteinhorn, maiskogel, and schmittenhoehe. |
| `lift_pass_product:ski-alpin-card` | `prices` | [Ski pass prices Zell am See-Kaprun winter 2026/27](https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes) | `[{"amount": 82, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 440, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 main season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 74, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}, {"amount": 396, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 winter start and bonus season", "source_url": "https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes"}]` | Official tariff page lists adult 1-day and 6-day Ski ALPIN CARD prices for main season and winter-start/bonus season. |  |
| `terrain_group:kitzsteinhorn-maiskogel` | `total_piste_km` | [Skiresort.info ALPIN CARD terrain overview](https://www.skiresort.info/ski-resorts/alpin-card/sorted/day-ticket-price/) | `62.5` | Reviewed editorial ALPIN CARD overview lists 62.5 km of slopes for the aggregate Kitzsteinhorn/Maiskogel - Kaprun terrain entity. |  |
| `terrain_group:kitzsteinhorn-maiskogel` | `total_lift_count` | [Skiresort.info ALPIN CARD terrain overview](https://www.skiresort.info/ski-resorts/alpin-card/sorted/day-ticket-price/) | `24` | Reviewed editorial ALPIN CARD overview lists 24 lifts for the aggregate Kitzsteinhorn/Maiskogel - Kaprun terrain entity. |  |
| `terrain_group:kitzsteinhorn-maiskogel` | `piste_km_by_difficulty` | [Skiresort.info ALPIN CARD terrain overview](https://www.skiresort.info/ski-resorts/alpin-card/sorted/day-ticket-price/) | `{"advanced": 9, "beginner": 30.5, "intermediate": 23}` | Reviewed editorial ALPIN CARD overview publishes the aggregate 30.5 km beginner, 23 km intermediate, and 9 km advanced split. |  |
| `destination:zell-am-see-kaprun` | `trust_manifest.field_statuses.lift_pass_products` | [Ski pass prices Zell am See-Kaprun winter 2026/27](https://www.zellamsee-kaprun.com/en/sport/winter/skiing/ski-passes) | `"Official Ski ALPIN CARD tariff and validity evidence."` | Official pass and price evidence supports moving lift_pass_products to verified_with_adjustment. | Trust status summarizes multiple scoped pass-product facts rather than one raw source value. |
| `destination:zell-am-see-kaprun` | `trust_manifest.field_statuses.terrain_groups` | [Skiresort.info ALPIN CARD terrain overview](https://www.skiresort.info/ski-resorts/alpin-card/sorted/day-ticket-price/) | `"Reviewed editorial aggregate terrain metrics for Kitzsteinhorn/Maiskogel."` | Reviewed editorial aggregate terrain evidence supports moving terrain_groups to verified_with_adjustment while child ski-area splits remain unresolved. | Trust status summarizes aggregate terrain facts separated from child ski-area facts. |

## Ranking Impact

Default comparison diagnostics wrote 12 rows to artifacts/ranking-comparison. The new Ski ALPIN CARD product is display/trust metadata, and the new Kitzsteinhorn/Maiskogel terrain group is aggregate evidence that current production ranking does not consume directly; child ski-area facts remain unchanged except for the already curated values.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-23-zell-am-see-kaprun.json --markdown-output docs/catalog-curation/2026-06-23-zell-am-see-kaprun.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`

## Caveats

- Exact future season windows remain unresolved: official pages reviewed on 2026-06-23 expose a 2026-10-10 Kitzsteinhorn start signal but no complete 2026/27 end date for the modeled destination.
- Kitzsteinhorn and Schmittenhoehe ski-area weather coordinates were reviewed but left unchanged because changing weather-critical coordinates would invalidate historical weather semantics and needs an owner checkpoint.
- Separate Kitzsteinhorn and Maiskogel child-area piste difficulty splits remain unresolved because official pages reviewed in this sweep did not publish numeric blue/red/black kilometer splits for those separate modeled entities; the reviewed Kitzsteinhorn/Maiskogel aggregate split is captured only under terrain_groups.
- Lodging price ranges, quality tiers, supported skill levels, and rental price ranges remain curated estimates; this sweep did not add source-backed accommodation or rental pricing evidence.
## Field Coverage Matrix

Destination fields:

| Field | Decision | Note |
| --- | --- | --- |
| `resort_id` | reviewed-no-change | Stable id remains `zell-am-see-kaprun`. |
| `name` | reviewed-no-change | Official tourism/operator sources use Zell am See-Kaprun. |
| `country` | reviewed-no-change | Austria remains source-consistent. |
| `region` | reviewed-no-change | Salzburg remains source-consistent. |
| `price_level` | reviewed-no-change | Legacy product tier remains `medium`; detailed lodging/rental price trust stays estimated. |
| `latitude` | reviewed-no-change | Destination coordinate remains product-normalized to Zell am See-Kaprun area identity. |
| `longitude` | reviewed-no-change | Destination coordinate remains product-normalized to Zell am See-Kaprun area identity. |
| `base_elevation_m` | reviewed-no-change | 757 m remains plausible for the valley/base-level destination model. |
| `summit_elevation_m` | reviewed-no-change | 3029 m remains aligned to Top of Salzburg/Kitzsteinhorn visitor summit. |
| `season_start_month` | reviewed-no-change | October remains supported by Kitzsteinhorn early-season operation. |
| `season_end_month` | reviewed-no-change | May remains supported by Kitzsteinhorn late-spring operation. |
| `season_windows` | unresolved | Future 2026/27 complete end date was not published in reviewed official sources. |
| `lift_pass_prices` | changed | Added adult 1-day and 6-day Ski ALPIN CARD examples for winter 2026/27. |
| `lift_pass_products` | changed | Added Ski ALPIN CARD as a scoped regional-network pass product covering the modeled local ski areas and external Skicircus validity. |
| `ski_areas` | changed | Added reviewed terrain/access inputs under modeled ski areas. |
| `terrain_groups` | changed | Added an aggregate Kitzsteinhorn/Maiskogel terrain group so reviewed aggregate terrain metrics are not copied onto child ski areas. |
| `stay_bases` | changed | Added reviewed access metadata for Kaprun and Zell am See. |
| `rentals` | reviewed-no-change | Rental scope was not requested; existing example remains in place. |

Ski-area fields:

| Ski Area | Field | Decision | Note |
| --- | --- | --- | --- |
| Kitzsteinhorn | `ski_area_id`, `name` | reviewed-no-change | Stable id/display name preserved. |
| Kitzsteinhorn | `latitude`, `longitude` | reviewed-no-change | Weather-critical coordinates left unchanged pending owner checkpoint. |
| Kitzsteinhorn | `base_elevation_m`, `summit_elevation_m` | reviewed-no-change | Existing product-normalized elevation range preserved. |
| Kitzsteinhorn | `season_start_month`, `season_end_month` | reviewed-no-change | October-May model remains supported. |
| Kitzsteinhorn | `season_windows` | unresolved | Exact future complete window unavailable. |
| Kitzsteinhorn | `total_piste_km` | changed | Added 41 km official Kitzsteinhorn slope value. |
| Kitzsteinhorn | `total_lift_count` | unresolved | Separate child-area lift count remains unresolved; aggregate Kitzsteinhorn/Maiskogel count is modeled under `terrain_groups`. |
| Kitzsteinhorn | `piste_km_by_difficulty.*` | unresolved | Separate child-area split remains unresolved; aggregate Kitzsteinhorn/Maiskogel split is modeled under `terrain_groups`. |
| Maiskogel | `ski_area_id`, `name` | reviewed-no-change | Stable id/display name preserved. |
| Maiskogel | `latitude`, `longitude` | reviewed-no-change | Weather-critical coordinates left unchanged pending owner checkpoint. |
| Maiskogel | `base_elevation_m`, `summit_elevation_m` | reviewed-no-change | Existing elevation range remains aligned to official Maiskogel page. |
| Maiskogel | `season_start_month`, `season_end_month` | reviewed-no-change | December-April fallback retained. |
| Maiskogel | `season_windows` | unresolved | Exact future complete window unavailable. |
| Maiskogel | `total_piste_km`, `total_lift_count` | changed | Added 20 km and 3 lifts from official Maiskogel source. |
| Maiskogel | `piste_km_by_difficulty.*` | unresolved | Separate child-area split remains unresolved; official source describes gentle/beginner terrain but not numeric split. |
| Schmittenhoehe | `ski_area_id`, `name` | reviewed-no-change | Stable id/display name preserved. |
| Schmittenhoehe | `latitude`, `longitude` | reviewed-no-change | Weather-critical coordinates left unchanged pending owner checkpoint. |
| Schmittenhoehe | `base_elevation_m`, `summit_elevation_m` | reviewed-no-change | Existing elevation range preserved. |
| Schmittenhoehe | `season_start_month`, `season_end_month` | reviewed-no-change | December-April fallback retained. |
| Schmittenhoehe | `season_windows` | unresolved | Exact future complete window unavailable. |
| Schmittenhoehe | `total_piste_km`, `total_lift_count` | changed | Added 77 km and 27 lifts from official company facts. |
| Schmittenhoehe | `piste_km_by_difficulty.*` | changed | Added 30 km blue, 28 km red, and 19 km black split from official company facts. |

Lift-pass product fields:

| Product | Field | Decision | Note |
| --- | --- | --- | --- |
| Ski ALPIN CARD | `lift_pass_product_id`, `name` | changed | Added stable product id `ski-alpin-card` and official display name. |
| Ski ALPIN CARD | `validity_scope`, `valid_ski_area_ids` | changed | Modeled as `regional_network`, locally covering Kitzsteinhorn, Maiskogel, and Schmittenhoehe. |
| Ski ALPIN CARD | `external_validity_summary` | changed | Added external Skicircus validity summary rather than modeling every external resort as a Zell ski area. |
| Ski ALPIN CARD | `prices` | changed | Reuses the reviewed adult/default Ski ALPIN CARD price examples already present in destination-level compatibility prices. |

Terrain-group fields:

| Terrain Group | Field | Decision | Note |
| --- | --- | --- | --- |
| Kitzsteinhorn/Maiskogel | `terrain_group_id`, `name`, `ski_area_ids`, `metric_scope` | changed | Added an aggregate group linked to Kitzsteinhorn and Maiskogel with `metric_scope=aggregate`. |
| Kitzsteinhorn/Maiskogel | `total_piste_km`, `total_lift_count` | changed | Added 62.5 km and 24 lifts from reviewed editorial aggregate terrain evidence. |
| Kitzsteinhorn/Maiskogel | `piste_km_by_difficulty.*` | changed | Added 30.5 km beginner, 23 km intermediate, and 9 km advanced as aggregate metrics only. |

Stay-base fields:

| Stay Base | Field | Decision | Note |
| --- | --- | --- | --- |
| Kaprun | `stay_base_id`, `name` | reviewed-no-change | Stable id/display name preserved. |
| Kaprun | `price_range` | reviewed-no-change | Existing lodging estimate retained; trust remains estimated. |
| Kaprun | `price_min`, `price_max` | not-applicable | Raw catalog omits these by convention; loader derives them from `price_range`. |
| Kaprun | `quality` | reviewed-no-change | Existing tier retained; trust remains estimated. |
| Kaprun | `lift_distance` | reviewed-no-change | Existing `near` bucket matches OSM distance/access review. |
| Kaprun | `supported_skill_levels` | reviewed-no-change | Existing compatibility list retained; trust remains estimated. |
| Kaprun | `latitude`, `longitude` | changed | Added OSM town coordinates rounded for catalog consistency. |
| Kaprun | `nearest_lift_name`, `nearest_lift_distance_m` | changed | Added MK Maiskogelbahn and computed 266 m distance. |
| Kaprun | `access_mode` | changed | Added `walk` from official no-car/walking access evidence. |
| Kaprun | `base_type`, `atmosphere_tags`, `regional_data_ids` | changed | Added OSM identity and official character tags. |
| Zell am See | `stay_base_id`, `name` | reviewed-no-change | Stable id/display name preserved. |
| Zell am See | `price_range` | reviewed-no-change | Existing lodging estimate retained; trust remains estimated. |
| Zell am See | `price_min`, `price_max` | not-applicable | Raw catalog omits these by convention; loader derives them from `price_range`. |
| Zell am See | `quality` | reviewed-no-change | Existing tier retained; trust remains estimated. |
| Zell am See | `lift_distance` | changed | Updated from `medium` to `near` after 186 m OSM distance review. |
| Zell am See | `supported_skill_levels` | reviewed-no-change | Existing compatibility list retained; trust remains estimated. |
| Zell am See | `latitude`, `longitude` | changed | Added OSM town coordinates rounded for catalog consistency. |
| Zell am See | `nearest_lift_name`, `nearest_lift_distance_m` | changed | Added cityXpress and computed 186 m distance. |
| Zell am See | `access_mode` | changed | Added `walk` from official access-point evidence plus OSM distance. |
| Zell am See | `base_type`, `atmosphere_tags`, `regional_data_ids` | changed | Added OSM identity and official character tags. |

## Process Gate

- Classification: `review-gated`.
- Developer Decision Checkpoint: resolved by owner agreement to add scoped pass products and aggregate terrain groups rather than duplicating network/aggregate facts onto child ski areas.
- ADR: added for the catalog scope model because this is a durable source-trust and data-model decision.
- Advisory review: skipped for this draft PR because the typed curation report plus validation is the review artifact; owner/advisory review can happen on the draft before merge.
