# Val d'Isere Catalog Curation

Reviewed Val d'Isere ticket products and local piste length against official Val d'Isere pages. Added the linked Tignes - Val d'Isere pass as the default regional-network product, added a secondary Val d'Isere-only day ticket, and filled local Val d'Isere piste kilometers without copying the 300 km linked-domain terrain into local ski-area facts.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `ski_area:val-disere-ski-area` | `total_piste_km` | `null` | `150` | `verified` | yes |
| `lift_pass_product:tignes-val-disere-ski-pass` | `name` | `null` | `"Tignes - Val d'Isere ski pass"` | `verified` | no |
| `lift_pass_product:tignes-val-disere-ski-pass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `lift_pass_product:tignes-val-disere-ski-pass` | `is_default` | `null` | `true` | `verified_with_adjustment` | no |
| `lift_pass_product:tignes-val-disere-ski-pass` | `valid_ski_area_ids` | `null` | `["val-disere-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:tignes-val-disere-ski-pass` | `external_validity_summary` | `null` | `"Also valid across the linked Tignes - Val d'Isere ski area beyond the modeled Val d'Isere ski-area entity."` | `verified_with_adjustment` | no |
| `lift_pass_product:tignes-val-disere-ski-pass` | `prices` | `null` | `[{"amount": 75, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}, {"amount": 225, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}, {"amount": 450, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 main season; 6 equals 7 days", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}]` | `verified_with_adjustment` | no |
| `lift_pass_product:val-disere-day-ticket` | `name` | `null` | `"Val d'Isere day ticket"` | `verified` | no |
| `lift_pass_product:val-disere-day-ticket` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | no |
| `lift_pass_product:val-disere-day-ticket` | `is_default` | `null` | `false` | `verified_with_adjustment` | no |
| `lift_pass_product:val-disere-day-ticket` | `valid_ski_area_ids` | `null` | `["val-disere-ski-area"]` | `verified_with_adjustment` | no |
| `lift_pass_product:val-disere-day-ticket` | `prices` | `null` | `[{"amount": 68, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}]` | `verified_with_adjustment` | no |
| `destination:val-disere` | `trust_manifest.field_statuses.lift_pass_products` | `"needs_source"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `ski_area:val-disere-ski-area` | `total_piste_km` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Val d'Isere 150km of slopes"` | Official Val d'Isere ticket page separates the local Val d'Isere product and labels it as 150 km of slopes. | Stored the local Val d'Isere figure on the modeled Val d'Isere ski-area entity; the 300 km linked domain remains pass-product scope, not local terrain truth. |
| `lift_pass_product:tignes-val-disere-ski-pass` | `name` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Tignes - Val d'Isere 300km of slopes"` | Official ticket page names the linked-domain product as Tignes - Val d'Isere. | Normalized source heading into a stable Snowcast product display name. |
| `lift_pass_product:tignes-val-disere-ski-pass` | `validity_scope` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Tignes - Val d'Isere 300km of slopes"` | Official page presents the default pass as the linked Tignes - Val d'Isere domain rather than only local Val d'Isere terrain. | Normalized linked-domain validity to regional_network because Tignes is outside this destination's modeled local ski-area ids. |
| `lift_pass_product:tignes-val-disere-ski-pass` | `is_default` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Tignes - Val d'Isere is listed first with 1/3/6-day tariffs; Val d'Isere-only has a one-day local tariff."` | Official ticket page positions the linked-domain pass as the primary multi-day ski pass product. | Default means representative adult/default product for planning display, not mandatory purchase guidance. |
| `lift_pass_product:tignes-val-disere-ski-pass` | `valid_ski_area_ids` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Tignes - Val d'Isere includes Val d'Isere and Tignes terrain."` | The product covers the modeled Val d'Isere ski-area entity and external Tignes terrain. | Only local modeled ski_area_ids are stored; Tignes is summarized as external validity. |
| `lift_pass_product:tignes-val-disere-ski-pass` | `external_validity_summary` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Tignes - Val d'Isere 300km of slopes"` | Official page supports an external validity summary covering the linked Tignes terrain. | External linked terrain is summarized rather than copied into Val d'Isere local ski-area facts. |
| `lift_pass_product:tignes-val-disere-ski-pass` | `prices` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `[{"amount": 75, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}, {"amount": 225, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}, {"amount": 450, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2025/26 main season; 6 equals 7 days", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}]` | Official ticket page lists adult Tignes - Val d'Isere 1-day, 3-day, and 6=7-day prices for winter 2025/26. | Stored representative adult/default 1/3/6-day prices rather than the full tariff table. |
| `lift_pass_product:val-disere-day-ticket` | `name` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Val d'Isere 150km of slopes; 1 day 68 EUR"` | Official ticket page exposes a Val d'Isere-only one-day product separate from the linked-domain pass. | Normalized source product section into a stable Snowcast product name. |
| `lift_pass_product:val-disere-day-ticket` | `validity_scope` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Val d'Isere 150km of slopes"` | Official ticket page separates the Val d'Isere product from the Tignes - Val d'Isere linked-domain product. | Normalized Val d'Isere-only scope to single_ski_area for the modeled local ski-area entity. |
| `lift_pass_product:val-disere-day-ticket` | `is_default` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Val d'Isere product has a one-day local tariff; linked-domain product has the main multi-day tariffs."` | The Val d'Isere-only one-day ticket is modeled as a secondary product because the linked-domain product carries the primary multi-day tariff table. | Default marker remains false for the local day product. |
| `lift_pass_product:val-disere-day-ticket` | `valid_ski_area_ids` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Val d'Isere 150km of slopes"` | Official Val d'Isere-only product maps to the modeled Val d'Isere ski-area entity. | The ski_area_id is Snowcast stable catalog identity, not source wording. |
| `lift_pass_product:val-disere-day-ticket` | `prices` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `[{"amount": 68, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2025/26 main season", "source_url": "https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/"}]` | Official ticket page lists the adult Val d'Isere-only one-day price as EUR 68 for winter 2025/26. |  |
| `destination:val-disere` | `trust_manifest.field_statuses.lift_pass_products` | [Ski passes Tignes - Val d'Isere and Val d'Isere prices](https://www.valdisere.com/en/prepare-for-your-stay/buy-my-skipass/) | `"Official linked-domain and Val d'Isere-only pass-product evidence."` | Official product scope and price evidence supports moving lift_pass_products from needs_source to verified_with_adjustment. | Trust status summarizes multiple scoped pass products and representative adult/default prices. |

## Ranking Impact

Ranking comparison required because total_piste_km is a current fit input. Results should be reviewed in artifacts/ranking-comparison for any score/rank movement after this curation.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-23-val-disere.json --markdown-output docs/catalog-curation/2026-06-23-val-disere.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`

## Caveats

- The 300 km linked Tignes - Val d'Isere terrain is modeled only as pass-product scope; this PR does not add it to local Val d'Isere piste facts.
- Official page reviewed here supports local Val d'Isere piste kilometers but not local blue/red/black kilometer splits or a clean local lift-count fact.
- Stay-base coordinates, nearest-lift distance, lodging price, rental price, quality tier, and supported skill levels remain estimate-backed pending a dedicated stay-base/rental sweep.
- Exact season windows remain unchanged; ticket validity and published key dates need a separate season-window curation decision.

## Field Sweep

Destination fields:

| Field | Decision | Note |
| --- | --- | --- |
| `resort_id`, `name`, `country`, `region` | reviewed-no-change | Existing identity fields were not changed in this pass-product and piste-km sweep. |
| `price_level` | reviewed-no-change | Lodging price tier remains product-curated and estimate-backed. |
| `latitude`, `longitude` | reviewed-no-change | Destination coordinates remain unchanged pending a geospatial curation sweep. |
| `base_elevation_m`, `summit_elevation_m` | reviewed-no-change | Elevation model remains unchanged. |
| `season_start_month`, `season_end_month`, `season_windows` | unresolved | Ticket validity dates and key dates were not converted into operating windows in this PR. |
| `lift_pass_products` | changed | Added linked-domain and local-day pass products with reviewed adult/default prices. |
| `ski_areas` | changed | Added local Val d'Isere total piste kilometers. |
| `terrain_groups` | unresolved | The 300 km Tignes - Val d'Isere linked terrain is kept as pass-product scope until cross-destination terrain modeling is designed. |
| `stay_bases`, `rentals` | reviewed-no-change | Stay-base and rental examples remain estimate-backed until a dedicated access/rental sweep. |

Ski-area fields:

| Ski Area | Field | Decision | Note |
| --- | --- | --- | --- |
| Val d'Isere | `total_piste_km` | changed | Added 150 km from the official Val d'Isere ticket page's local product section. |
| Val d'Isere | `total_lift_count` | unresolved | Reviewed sources did not provide a clean local-only lift count distinct from the linked-domain count. |
| Val d'Isere | `piste_km_by_difficulty.*` | unresolved | Reviewed sources did not provide local-only blue/red/black kilometer splits. |

Lift-pass product fields:

| Product | Field | Decision | Note |
| --- | --- | --- | --- |
| Tignes - Val d'Isere ski pass | `lift_pass_product_id`, `name` | changed | Added stable product id and normalized official linked-domain product name. |
| Tignes - Val d'Isere ski pass | `validity_scope`, `is_default`, `valid_ski_area_ids`, `external_validity_summary` | changed | Modeled as the default regional-network product because it extends beyond the local Val d'Isere ski-area entity. |
| Tignes - Val d'Isere ski pass | `prices` | changed | Added representative adult 1/3/6-day main-season prices from the official ticket page. |
| Val d'Isere day ticket | `lift_pass_product_id`, `name` | changed | Added separate local product for the cheaper one-day Val d'Isere-only ticket. |
| Val d'Isere day ticket | `validity_scope`, `is_default`, `valid_ski_area_ids` | changed | Modeled as a secondary single-ski-area product. |
| Val d'Isere day ticket | `prices` | changed | Added adult 1-day local price from the official ticket page. |
