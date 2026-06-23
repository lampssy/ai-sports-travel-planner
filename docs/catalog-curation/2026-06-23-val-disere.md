# Val d'Isere Catalog Curation

Expanded Val d'Isere from a pass/local-piste patch into a full destination field sweep. Added exact official season window, representative stay bases, source-backed rental example, and documented why the 300 km / lift-count linked-domain terrain remains pass scope rather than local ski-area truth.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `ski_area:val-disere-ski-area` | `total_piste_km` | `null` | `150` | `verified` | yes |
| `destination:val-disere` | `season_windows` | `null` | `[{"end_date": "2027-05-02", "season_label": "Winter 2026/27", "start_date": "2026-11-28", "status": "planned"}]` | `verified` | yes |
| `ski_area:val-disere-ski-area` | `season_windows` | `null` | `[{"end_date": "2027-05-02", "season_label": "Winter 2026/27", "start_date": "2026-11-28", "status": "planned"}]` | `verified` | yes |
| `destination:val-disere` | `stay_bases` | `["Val d'Isere"]` | `["val-disere-village", "val-disere-la-daille", "val-disere-le-fornet"]` | `verified_with_adjustment` | yes |
| `rental:ski-hut` | `price_range` | `null` | `"EUR 15-20"` | `verified` | no |
| `lift_pass_product:tignes-val-disere-ski-pass` | `prices` | `null` | `[{"amount": 75, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}, {"amount": 225, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}, {"amount": 450, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 main season; 6 equals 7 days", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}]` | `verified` | no |
| `lift_pass_product:val-disere-day-ticket` | `prices` | `null` | `[{"amount": 68, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}]` | `verified` | no |
| `destination:val-disere` | `trust_manifest.field_statuses.lift_pass_products` | `"needs_source"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:val-disere` | `trust_manifest.field_statuses.stay_base_lift_distance` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:val-disere` | `trust_manifest.field_statuses.rental_examples` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `ski_area:val-disere-ski-area` | `total_piste_km` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Val d'Isere 150km of slopes"` | Official ticket page lists a separate Val d'Isere product with 150 km of slopes. | Stored as local child ski-area piste kilometers, distinct from the 300 km linked Tignes-Val d'Isere domain. |
| `destination:val-disere` | `season_windows` | [Val d'Isere opening date](https://www.valdisere.com/en/val-disere-in-winter/ski-resort-opening-weekend/) | `{"end_date": "2027-05-02", "season_label": "Winter 2026/27", "start_date": "2026-11-28", "status": "planned"}` | Official opening page lists the winter 2026-2027 season from November 28, 2026 to May 2, 2027. | Stored as a planned exact season window while keeping month fallbacks. |
| `ski_area:val-disere-ski-area` | `season_windows` | [Val d'Isere opening date](https://www.valdisere.com/en/val-disere-in-winter/ski-resort-opening-weekend/) | `{"end_date": "2027-05-02", "season_label": "Winter 2026/27", "start_date": "2026-11-28", "status": "planned"}` | The same official window applies to the modeled Val d'Isere ski-area entity. | Stored on the child ski area for season-aware fit checks. |
| `destination:val-disere` | `stay_bases` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `["Val d'Isere village", "La Daille", "Le Fornet lift sectors"]` | Official lift/ticket pages identify the village lift access and named lift sectors such as La Daille and Fornet, while open geodata identifies La Daille and Le Fornet as Val d'Isere places. | Added representative stay bases for access diversity; lodging price and quality remain estimates. |
| `rental:ski-hut` | `price_range` | [Budget Ski Hire, Val d'Isere \| Ski Hut](https://skihut.ski/ski-hut-val-disere/) | `{"advanced_or_snowboard_per_day_eur": 20, "beginner_per_day_eur": 15, "intermediate_per_day_eur": 17}` | Provider page lists daily equipment-rental prices from EUR 15 to EUR 20 for adult ski/snowboard packages. | Normalized provider-specific daily equipment prices to catalog price_range EUR 15-20. |
| `lift_pass_product:tignes-val-disere-ski-pass` | `prices` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `[{"amount": 75, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}, {"amount": 225, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}, {"amount": 450, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 main season; 6 equals 7 days", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}]` | Official ticket page lists adult Tignes-Val d'Isere 1-day, 3-day, and 6=7-day prices for winter 2025/26. | Used representative adult/default prices; broader 300 km linked terrain remains pass-product scope. |
| `lift_pass_product:val-disere-day-ticket` | `prices` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `[{"amount": 68, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}]` | Official ticket page lists a separate local Val d'Isere 1-day adult price. | Stored as a non-default single-ski-area product because it changes both terrain scope and price. |
| `destination:val-disere` | `trust_manifest.field_statuses.lift_pass_products` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Official linked and local ticket products and prices."` | Official ticket evidence supports moving lift_pass_products from needs_source to verified_with_adjustment. | Trust status summarizes scoped pass products and representative adult/default prices. |
| `destination:val-disere` | `trust_manifest.field_statuses.stay_base_lift_distance` | [OpenStreetMap Val-d'Isere relation](https://www.openstreetmap.org/relation/133944) | `"Val d'Isere village, La Daille, and Le Fornet open geodata identity with official lift-sector context."` | Open geodata and official lift-sector evidence support source-backed access classification for representative stay bases. | Exact meter distances remain unresolved; status reflects reviewed access-mode and place identity evidence. |
| `destination:val-disere` | `trust_manifest.field_statuses.rental_examples` | [Ski Hut Val d'Isere](https://www.valdisere.com/en/village-guide/ski-hut-val-disere-en-4044900/) | `"Official tourism listing for Ski Hut rental shop plus provider price page."` | Official tourism listing supports rental identity and provider page supports representative price range. | Rental quality tier remains estimated. |

## Ranking Impact

Required because local piste length, exact season windows, stay-base coverage, and stay-base access inputs changed. Ranking comparison completed with 12 rows written to artifacts/ranking-comparison.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-23-val-disere.json --markdown-output docs/catalog-curation/2026-06-23-val-disere.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`
- `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_validation.py tests/test_loader.py -q`

## Caveats

- The official 300 km / 71 lift / run-count facts describe the linked Tignes-Val d'Isere domain and are not copied onto the local Val d'Isere ski area.
- Local-only Val d'Isere lift count and piste-kilometer difficulty split remain unresolved; reviewed sources publish linked-domain counts or run counts rather than kilometers by difficulty.
- Destination and child ski-area summit elevation remain unchanged pending an owner decision on local-only versus linked-domain weather/elevation semantics.
- Lodging price ranges, stay-base quality tiers, and supported skill levels remain curated estimates pending a dedicated quality and price sampling policy.

## Field Coverage Matrix

### Destination

| Field | Status | Notes |
| --- | --- | --- |
| `resort_id`, `name`, `country`, `region` | reviewed-no-change | Existing identity is consistent with official and open-source records. |
| `price_level` | reviewed-no-change | Existing premium tier remains plausible; detailed lodging price sampling is deferred. |
| `latitude`, `longitude` | reviewed-no-change | Current destination center remains close to the official village/open geodata center. |
| `base_elevation_m` | reviewed-no-change | Existing value remains plausible for the resort base. |
| `summit_elevation_m` | unresolved | Current 3456 m reflects linked high-alpine terrain semantics; local-only versus linked-domain elevation should be decided once for all linked domains. |
| `season_start_month`, `season_end_month` | reviewed-no-change | Month fallbacks still match the official exact winter window. |
| `season_windows` | changed | Added official Winter 2026/27 window. |
| `ski_areas` | changed | Added local 150 km piste total to the modeled Val d'Isere ski area. |
| `terrain_groups` | unresolved | 300 km / lift-count facts describe the linked Tignes-Val d'Isere domain and need cross-destination aggregate modeling. |
| `lift_pass_products` | changed | Added representative linked-domain and local Val d'Isere ticket products/prices. |
| `stay_bases` | changed | Expanded to village, La Daille, and Le Fornet with access metadata and regional IDs. |
| `rentals` | changed | Added Ski Hut as a source-backed budget rental example while retaining Val Ski Shop. |

### Ski Area `val-disere-ski-area`

| Field | Status | Notes |
| --- | --- | --- |
| `ski_area_id`, `name` | reviewed-no-change | Existing local ski-area identity remains appropriate. |
| `latitude`, `longitude` | reviewed-no-change | Existing coordinates remain close enough for resort-fit and weather context. |
| `base_elevation_m` | reviewed-no-change | Existing value remains plausible for Val d'Isere local terrain. |
| `summit_elevation_m` | unresolved | Same linked-domain elevation caveat as the destination. |
| `season_start_month`, `season_end_month` | reviewed-no-change | Month fallbacks match the exact window. |
| `season_windows` | changed | Added official Winter 2026/27 window. |
| `total_piste_km` | changed | Official ticket page supports 150 km for the Val d'Isere local product. |
| `total_lift_count` | unresolved | Reviewed sources publish linked-domain lift totals, not a clean local-only count. |
| `piste_km_by_difficulty.*` | unresolved | Reviewed sources publish run counts or linked-domain facts, not local km by difficulty. |

### Lift-Pass Products

| Product | Status | Notes |
| --- | --- | --- |
| `tignes-val-disere-ski-pass` | changed | Default regional-network product with 1/3/6-day adult price examples and 300 km external validity summary. |
| `val-disere-day-ticket` | changed | Non-default single-ski-area product because it materially changes terrain scope and price. |

### Stay Bases

| Stay Base | Status | Notes |
| --- | --- | --- |
| `val-disere-village` | changed | Added ID, coordinates, nearest lift context, access mode, atmosphere tags, and regional IDs. |
| `val-disere-la-daille` | changed | Added representative lower-valley lift sector with source-backed place ID and access metadata. |
| `val-disere-le-fornet` | changed | Added quieter high-altitude-access hamlet with source-backed place ID and access metadata. |
| `price_range`, `quality`, `supported_skill_levels` | unresolved | Retained curated estimates pending a lodging-quality sampling policy. |
| `nearest_lift_distance_m` | unresolved | Named-lift access is reviewed, but exact meter distances are not source-backed yet. |

### Rentals And Trust

| Field | Status | Notes |
| --- | --- | --- |
| `Val Ski Shop` | reviewed-no-change | Existing premium rental example remains supported by official directory evidence. |
| `Ski Hut` | changed | Added official/provider-supported budget rental example with daily price range. |
| `trust_manifest.field_statuses.lift_pass_products` | changed | Moved to `verified_with_adjustment`. |
| `trust_manifest.field_statuses.stay_base_lift_distance` | changed | Moved to `verified_with_adjustment` for named access and regional identity, with exact distances still unresolved. |
| `trust_manifest.field_statuses.rental_examples` | changed | Moved to `verified_with_adjustment`. |
