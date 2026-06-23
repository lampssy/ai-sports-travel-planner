# Zell am See-Kaprun Catalog Curation

Reviewed Zell am See-Kaprun destination, ski-area, and stay-base fields against official operator/tourism pages plus OSM identity and lift geometry. Added source-backed lift-pass examples, terrain metrics, and stay-base access metadata while leaving unresolved season-window, quality, lodging-price, and weather-coordinate decisions unchanged.

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

## Ranking Impact

Default comparison diagnostics wrote 12 rows to artifacts/ranking-comparison. Zell am See-Kaprun did not enter the generated top-three Austria scenario after this curation, so the artifact has no Zell-specific rank delta; this PR adds factor inputs without changing production ranking behavior.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-23-zell-am-see-kaprun.json --markdown-output docs/catalog-curation/2026-06-23-zell-am-see-kaprun.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`

## Caveats

- Exact future season windows remain unresolved: official pages reviewed on 2026-06-23 expose a 2026-10-10 Kitzsteinhorn start signal but no complete 2026/27 end date for the modeled destination.
- Kitzsteinhorn and Schmittenhoehe ski-area weather coordinates were reviewed but left unchanged because changing weather-critical coordinates would invalidate historical weather semantics and needs an owner checkpoint.
- Kitzsteinhorn and Maiskogel piste difficulty splits remain unresolved because official pages reviewed in this sweep did not publish numeric blue/red/black kilometer splits for those separate modeled entities.
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
| `ski_areas` | changed | Added reviewed terrain/access inputs under modeled ski areas. |
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
| Kitzsteinhorn | `total_lift_count` | unresolved | Official reviewed count is for the broader connected network, not cleanly the separate modeled entity. |
| Kitzsteinhorn | `piste_km_by_difficulty.*` | unresolved | Official reviewed source confirms blue/red/black runs but not numeric split. |
| Maiskogel | `ski_area_id`, `name` | reviewed-no-change | Stable id/display name preserved. |
| Maiskogel | `latitude`, `longitude` | reviewed-no-change | Weather-critical coordinates left unchanged pending owner checkpoint. |
| Maiskogel | `base_elevation_m`, `summit_elevation_m` | reviewed-no-change | Existing elevation range remains aligned to official Maiskogel page. |
| Maiskogel | `season_start_month`, `season_end_month` | reviewed-no-change | December-April fallback retained. |
| Maiskogel | `season_windows` | unresolved | Exact future complete window unavailable. |
| Maiskogel | `total_piste_km`, `total_lift_count` | changed | Added 20 km and 3 lifts from official Maiskogel source. |
| Maiskogel | `piste_km_by_difficulty.*` | unresolved | Official source describes gentle/beginner terrain but not numeric split. |
| Schmittenhoehe | `ski_area_id`, `name` | reviewed-no-change | Stable id/display name preserved. |
| Schmittenhoehe | `latitude`, `longitude` | reviewed-no-change | Weather-critical coordinates left unchanged pending owner checkpoint. |
| Schmittenhoehe | `base_elevation_m`, `summit_elevation_m` | reviewed-no-change | Existing elevation range preserved. |
| Schmittenhoehe | `season_start_month`, `season_end_month` | reviewed-no-change | December-April fallback retained. |
| Schmittenhoehe | `season_windows` | unresolved | Exact future complete window unavailable. |
| Schmittenhoehe | `total_piste_km`, `total_lift_count` | changed | Added 77 km and 27 lifts from official company facts. |
| Schmittenhoehe | `piste_km_by_difficulty.*` | changed | Added 30 km blue, 28 km red, and 19 km black split from official company facts. |

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
- Developer Decision Checkpoint: source-backed curation proceeded without owner prompt for mechanical catalog additions; weather-critical ski-area coordinate changes were intentionally not made and are listed as unresolved.
- ADR: not needed because this PR does not change architecture, persistence, public API contracts, or production ranking policy.
- Advisory review: skipped for this draft PR because the typed curation report plus validation is the review artifact; owner/advisory review can happen on the draft before merge.
