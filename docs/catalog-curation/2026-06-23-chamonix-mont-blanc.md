# Chamonix Mont-Blanc Catalog Curation

Reviewed Chamonix Mont-Blanc lift-pass product scope against official Mont-Blanc Natural Resort ticket pages. Added CHAMONIX Le Pass as the default local modeled product and Mont-Blanc Unlimited as a broader regional-network product while leaving terrain, stay-base, rental, lodging-price, and exact season-window enrichment unresolved for later curation.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:chamonix-le-pass` | `name` | `null` | `"CHAMONIX Le Pass"` | `verified` | no |
| `lift_pass_product:chamonix-le-pass` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | no |
| `lift_pass_product:chamonix-le-pass` | `is_default` | `null` | `true` | `verified_with_adjustment` | no |
| `lift_pass_product:chamonix-le-pass` | `valid_ski_area_ids` | `null` | `["chamonix-mont-blanc-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:chamonix-le-pass` | `prices` | `null` | `[{"amount_max": 59.2, "amount_min": 47.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "range", "season_label": "Winter 2025/26 Chamonix Le Pass season range", "source_url": "https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass"}]` | `verified_with_adjustment` | no |
| `lift_pass_product:mont-blanc-unlimited` | `name` | `null` | `"Mont-Blanc Unlimited"` | `verified` | no |
| `lift_pass_product:mont-blanc-unlimited` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `lift_pass_product:mont-blanc-unlimited` | `valid_ski_area_ids` | `null` | `["chamonix-mont-blanc-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:mont-blanc-unlimited` | `external_validity_summary` | `null` | `"Also covers broader Mont-Blanc Natural Resort ski and visit access beyond the modeled Chamonix ski-area entity, including cross-border ski areas marketed across France, Italy, and Switzerland."` | `verified_with_adjustment` | no |
| `lift_pass_product:mont-blanc-unlimited` | `prices` | `null` | `[{"amount_max": 100.0, "amount_min": 70.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "range", "season_label": "Winter 2025/26 Mont-Blanc Unlimited season range", "source_url": "https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited"}, {"amount_max": 152.0, "amount_min": 106.4, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "range", "season_label": "Winter 2025/26 Mont-Blanc Unlimited season range", "source_url": "https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited"}, {"amount_max": 284.0, "amount_min": 240.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "range", "season_label": "Winter 2025/26 Mont-Blanc Unlimited season range", "source_url": "https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited"}]` | `verified_with_adjustment` | no |
| `destination:chamonix-mont-blanc` | `trust_manifest.field_statuses.lift_pass_products` | `"needs_source"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `lift_pass_product:chamonix-le-pass` | `name` | [CHAMONIX Le Pass - ski pass - Mont-Blanc](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `"Pass CHAMONIX Le Pass"` | Official ticketing page names the local Chamonix product as CHAMONIX Le Pass. | Normalized official product heading capitalization into Snowcast display name. |
| `lift_pass_product:chamonix-le-pass` | `validity_scope` | [CHAMONIX Le Pass - ski pass - Mont-Blanc](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `"Access to Chamonix ski areas: Brevent-Flegere, Grands Montets top closed, Balme-Le Tour-Vallorcine, and beginner areas."` | Official ticketing page scopes CHAMONIX Le Pass to Chamonix ski areas rather than the broader cross-border Mont-Blanc Unlimited network. | The current catalog has one modeled Chamonix ski-area entity, so the local Chamonix-area pass is represented as single_ski_area against that aggregate modeled entity. |
| `lift_pass_product:chamonix-le-pass` | `is_default` | [CHAMONIX Le Pass - ski pass - Mont-Blanc](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `"Adult: 1 day Ski in Chamonix"` | The official page positions CHAMONIX Le Pass as the Chamonix skiing product, making it the default local planning product over the broader Mont-Blanc Unlimited add-on product. | Default means representative local adult/default product for Snowcast display, not a claim that every Chamonix visitor should buy this pass. |
| `lift_pass_product:chamonix-le-pass` | `valid_ski_area_ids` | [CHAMONIX Le Pass - ski pass - Mont-Blanc](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `"Chamonix ski areas"` | Official Chamonix-area product maps to the existing Chamonix Mont-Blanc ski-area entity in the catalog. | The modeled ski-area id is a Snowcast stable identifier, not source wording. |
| `lift_pass_product:chamonix-le-pass` | `prices` | [CHAMONIX Le Pass - ski pass - Mont-Blanc](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `[{"amount_max": 59.2, "amount_min": 47.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "range", "season_label": "Winter 2025/26 Chamonix Le Pass season range", "source_url": "https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass"}]` | Official ticketing page lists adult 1-day CHAMONIX Le Pass pricing as a seasonal range from EUR 47.00 to EUR 59.20. | Stored as a range because the page presents different seasonal prices on one product page. |
| `lift_pass_product:mont-blanc-unlimited` | `name` | [Mont-Blanc Unlimited Ski Pass - Across 3 countries](https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited) | `"Pass MONT BLANC Unlimited"` | Official ticketing page names the broader product as Mont-Blanc Unlimited. | Normalized official product heading capitalization into Snowcast display name. |
| `lift_pass_product:mont-blanc-unlimited` | `validity_scope` | [Mont-Blanc Unlimited Ski Pass - Across 3 countries](https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited) | `"All resorts Adult Ski & Visits; Across 3 countries"` | Official ticketing page presents Mont-Blanc Unlimited as a broader all-resorts ski-and-visit product across three countries. | Normalized broad official validity wording to regional_network because it extends beyond the modeled Chamonix ski-area entity. |
| `lift_pass_product:mont-blanc-unlimited` | `valid_ski_area_ids` | [Mont-Blanc Unlimited Ski Pass - Across 3 countries](https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited) | `"All resorts Adult Ski & Visits"` | Mont-Blanc Unlimited includes the modeled Chamonix ski-area entity and additional external access. | External covered regions are summarized instead of adding non-modeled ski areas to valid_ski_area_ids. |
| `lift_pass_product:mont-blanc-unlimited` | `external_validity_summary` | [Mont-Blanc Unlimited Ski Pass - Across 3 countries](https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited) | `"Across 3 countries"` | Official product title and page positioning support an external validity summary beyond the Chamonix local product. | Snowcast summarizes the external network instead of modeling every external partner area in the Chamonix destination. |
| `lift_pass_product:mont-blanc-unlimited` | `prices` | [Mont-Blanc Unlimited Ski Pass - Across 3 countries](https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited) | `[{"amount_max": 100.0, "amount_min": 70.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "range", "season_label": "Winter 2025/26 Mont-Blanc Unlimited season range", "source_url": "https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited"}, {"amount_max": 152.0, "amount_min": 106.4, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "range", "season_label": "Winter 2025/26 Mont-Blanc Unlimited season range", "source_url": "https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited"}, {"amount_max": 284.0, "amount_min": 240.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "range", "season_label": "Winter 2025/26 Mont-Blanc Unlimited season range", "source_url": "https://www.montblancnaturalresort.com/en/ticketing/montblanc-unlimited"}]` | Official ticketing page lists adult Mont-Blanc Unlimited 1-day, 3-day, and 6-day prices as seasonal ranges. | Stored representative 1/3/6-day adult/default ranges rather than the full tariff table. |
| `destination:chamonix-mont-blanc` | `trust_manifest.field_statuses.lift_pass_products` | [CHAMONIX Le Pass - ski pass - Mont-Blanc](https://domaineschamonix.montblancnaturalresort.com/en/ticketing/chamonix-lepass) | `"Official CHAMONIX Le Pass and Mont-Blanc Unlimited ticketing evidence."` | Official product scope and pricing evidence supports moving lift_pass_products from needs_source to verified_with_adjustment. | Trust status summarizes multiple scoped pass-product facts and representative price ranges. |

## Ranking Impact

Not run for this pass-product-only curation. Current production ranking does not consume lift_pass_products directly.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-23-chamonix-mont-blanc.json --markdown-output docs/catalog-curation/2026-06-23-chamonix-mont-blanc.md`

## Caveats

- Chamonix terrain remains modeled as one aggregate ski-area entity; this PR does not split Brevent-Flegere, Grands Montets, Balme, Les Houches, or beginner sectors.
- Official Chamonix Le Pass page reviewed in this pass exposed a 1-day adult range but not a clean 3-day or 6-day local-product tariff table suitable for static catalog examples.
- Stay-base coordinates, nearest-lift distance, lodging price, rental price, quality tier, and supported skill levels remain estimate-backed pending a later stay-base/rental curation sweep.
- Exact season windows remain unchanged; the official ticket pages expose tariff periods, but this PR does not convert them into destination operating windows.

## Field Sweep

Destination fields:

| Field | Decision | Note |
| --- | --- | --- |
| `resort_id`, `name`, `country`, `region` | reviewed-no-change | Existing identity fields were not changed in this pass-product-focused sweep. |
| `price_level` | reviewed-no-change | Lodging price tier remains product-curated and estimate-backed. |
| `latitude`, `longitude` | reviewed-no-change | Destination coordinates remain unchanged pending a geospatial curation sweep. |
| `base_elevation_m`, `summit_elevation_m` | reviewed-no-change | Elevation model unchanged; this PR does not reinterpret Chamonix valley versus lift-access summit semantics. |
| `season_start_month`, `season_end_month`, `season_windows` | unresolved | Ticket tariff periods were reviewed but not promoted to destination operating windows. |
| `lift_pass_products` | changed | Added CHAMONIX Le Pass and Mont-Blanc Unlimited as scoped pass products with representative adult/default prices. |
| `ski_areas`, `terrain_groups` | unresolved | Chamonix sector/terrain modeling needs a separate curation decision before adding aggregate piste/lift metrics. |
| `stay_bases`, `rentals` | reviewed-no-change | Stay-base and rental examples remain estimate-backed until a dedicated access/rental sweep. |

Lift-pass product fields:

| Product | Field | Decision | Note |
| --- | --- | --- | --- |
| CHAMONIX Le Pass | `lift_pass_product_id`, `name` | changed | Added stable product id and official product name. |
| CHAMONIX Le Pass | `validity_scope`, `is_default`, `valid_ski_area_ids` | changed | Modeled as the default local Chamonix product against the existing aggregate ski-area entity. |
| CHAMONIX Le Pass | `prices` | changed | Added adult 1-day seasonal range from the official product page. |
| Mont-Blanc Unlimited | `lift_pass_product_id`, `name` | changed | Added broader official product separately from the local Chamonix pass. |
| Mont-Blanc Unlimited | `validity_scope`, `valid_ski_area_ids`, `external_validity_summary` | changed | Modeled as a regional-network product because official wording extends beyond the Chamonix modeled ski-area entity. |
| Mont-Blanc Unlimited | `prices` | changed | Added representative adult 1/3/6-day seasonal ranges from the official product page. |
