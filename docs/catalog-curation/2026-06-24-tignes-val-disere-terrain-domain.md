# Tignes-Val d'Isere shared terrain-domain lift count

Applies the catalog conflict rule for official-source disagreement by using the Bergfex Val d'Isere - Tignes skiregion page as fallback corroboration for the shared terrain-domain lift count.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `terrain_domain:tignes-val-disere` | `total_lift_count` | `null` | `72` | `verified_with_adjustment` | no |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `terrain_domain:tignes-val-disere` | `total_lift_count` | [Tignes - Val d'Isere ski area](https://en.tignes.net/skiing/ski-area) | `74` | Official Tignes page describes the linked Tignes-Val d'Isere ski area and publishes 74 ski lifts for that domain. | Official sources conflict, so the Tignes value is retained as conflict evidence rather than used as the canonical terrain-domain lift count. |
| `terrain_domain:tignes-val-disere` | `total_lift_count` | [Tignes - Val d'Isere ski area in Val d'Isere](https://www.valdisere.com/en/val-disere-in-winter/skiing-winter-fun/ski-area-french-alps/) | `71` | Official Val d'Isere page describes the linked Tignes-Val d'Isere ski area and publishes 71 ski lifts for that domain. | Official sources conflict, so the Val d'Isere value is retained as conflict evidence rather than used as the canonical terrain-domain lift count. |
| `terrain_domain:tignes-val-disere` | `total_lift_count` | [Bergfex Val d'Isere - Tignes skiregion](https://www.bergfex.com/skiregionen/valdiseres-tignes/) | `{"lift_category_counts": [15, 38, 6, 3, 2, 1, 7], "sum": 72}` | Bergfex publishes linked skiregion lift category counts for the same 300 km Val d'Isere - Tignes scope. | Summed Bergfex lift categories to total_lift_count=72 as the fallback value after official-source disagreement. |

## Ranking Impact

Not run; current production ranking does not consume terrain_domains yet.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-24-tignes-val-disere-terrain-domain.json --markdown-output docs/catalog-curation/2026-06-24-tignes-val-disere-terrain-domain.md`

## Caveats

- Official linked-domain lift counts remain inconsistent at 74 on Tignes and 71 on Val d'Isere; 72 is a Bergfex fallback value, not an official canonical source value.
