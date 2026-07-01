# Campiglio Connected-Domain Migration Reconciliation

- **Madonna di Campiglio:** retained as an independent destination with its existing local weather identity.
- **Pinzolo:** added as an independent destination with a new local weather-owning ski area.
- **Folgarida-Marilleva:** added as an independent destination with a new local weather-owning ski area.
- **Aggregate ownership:** the connected `campiglio-dolomiti-di-brenta` terrain domain owns the reviewed 156 km aggregate; child piste totals remain local.
- **Pass and Pejo semantics:** shared Skiarea products reference the connected domain; Pejo remains disconnected external pass validity, not domain membership.
- **Weather review:** Madonna di Campiglio has `material_change=false`; no `force_refetch` is required for its retained identity.
- **Owner jobs:** Pinzolo and Folgarida-Marilleva require owner-run archive backfill and climatology rebuild after deployment.
- **Main unresolved conflicts:** Campiglio lift count is 61 versus 58 across same-scope official sources; the 156 km domain value also retains the official map's 155 km conflict. Child lift counts and difficulty splits remain unresolved without child-scoped evidence.
- **Pinned data snapshots:** immutable `e8f4e11..e57b5bb`; later commits do not alter the reconciled catalog or trust data.
- Detailed changed-field, coverage, evidence, boundary, and weather tables follow. This artifact is the detailed review record; Task 11 will create a compact PR body that links to it.

## Reviewed Targets

| Target | Scope | Required Fields |
| --- | --- | --- |
| `destination:madonna-di-campiglio` | `full` | all canonical fields |
| `destination:pinzolo` | `full` | all canonical fields |
| `destination:folgarida-marilleva` | `full` | all canonical fields |
| `ski_area:madonna-di-campiglio-ski-area` | `full` | all canonical fields |
| `ski_area:pinzolo-ski-area` | `full` | all canonical fields |
| `ski_area:folgarida-marilleva-ski-area` | `full` | all canonical fields |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `full` | all canonical fields |
| `stay_base:pinzolo:pinzolo-pinzolo` | `full` | all canonical fields |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `full` | all canonical fields |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `full` | all canonical fields |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `full` | all canonical fields |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `full` | all canonical fields |
| `rental:folgarida-marilleva:ski-point` | `full` | all canonical fields |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `full` | all canonical fields |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `full` | all canonical fields |
| `rental:pinzolo:il-comodo-sci` | `full` | all canonical fields |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `full` | all canonical fields |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `full` | all canonical fields |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `full` | all canonical fields |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `full` | all canonical fields |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `full` | all canonical fields |
| `terrain_domain:matterhorn-ski-paradise` | `full` | all canonical fields |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `full` | all canonical fields |
| `trust_manifest:destination:madonna-di-campiglio` | `full` | all canonical fields |
| `trust_manifest:destination:pinzolo` | `full` | all canonical fields |
| `trust_manifest:destination:folgarida-marilleva` | `full` | all canonical fields |
| `trust_manifest:terrain_domain:tignes-val-disere` | `full` | all canonical fields |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `full` | all canonical fields |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `full` | all canonical fields |

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:folgarida-marilleva` | `base_elevation_m` | `null` | `1300` | `verified` | yes |
| `destination:folgarida-marilleva` | `country` | `null` | `"Italy"` | `estimated` | no |
| `destination:folgarida-marilleva` | `latitude` | `null` | `46.3030712` | `verified` | yes |
| `destination:folgarida-marilleva` | `lift_pass_products[0]` | `null` | `"folgarida-marilleva-campiglio-skiarea-pass"` | `verified_with_adjustment` | no |
| `destination:folgarida-marilleva` | `lift_pass_products[1]` | `null` | `"folgarida-marilleva-local-pass"` | `verified_with_adjustment` | no |
| `destination:folgarida-marilleva` | `longitude` | `null` | `10.8656079` | `verified` | yes |
| `destination:folgarida-marilleva` | `name` | `null` | `"Folgarida-Marilleva"` | `verified` | no |
| `destination:folgarida-marilleva` | `price_level` | `null` | `"medium"` | `estimated` | no |
| `destination:folgarida-marilleva` | `region` | `null` | `"Trentino"` | `estimated` | no |
| `destination:folgarida-marilleva` | `rentals[0]` | `null` | `"folgarida-marilleva:ski-point"` | `verified_with_adjustment` | no |
| `destination:folgarida-marilleva` | `resort_id` | `null` | `"folgarida-marilleva"` | `verified` | no |
| `destination:folgarida-marilleva` | `season_end_month` | `null` | `4` | `estimated` | no |
| `destination:folgarida-marilleva` | `season_start_month` | `null` | `12` | `estimated` | no |
| `destination:folgarida-marilleva` | `season_windows` | `null` | `[]` | `needs_source` | no |
| `destination:folgarida-marilleva` | `ski_areas[0]` | `null` | `"folgarida-marilleva-ski-area"` | `verified_with_adjustment` | no |
| `destination:folgarida-marilleva` | `stay_bases[0]` | `null` | `"folgarida-marilleva-daolasa"` | `verified_with_adjustment` | no |
| `destination:folgarida-marilleva` | `stay_bases[1]` | `null` | `"folgarida-marilleva-folgarida"` | `verified_with_adjustment` | no |
| `destination:folgarida-marilleva` | `stay_bases[2]` | `null` | `"folgarida-marilleva-marilleva-1400"` | `verified_with_adjustment` | no |
| `destination:folgarida-marilleva` | `stay_bases[3]` | `null` | `"folgarida-marilleva-marilleva-900"` | `verified_with_adjustment` | no |
| `destination:folgarida-marilleva` | `summit_elevation_m` | `null` | `2180` | `verified` | yes |
| `destination:folgarida-marilleva` | `terrain_groups` | `null` | `[]` | `needs_source` | no |
| `destination:madonna-di-campiglio` | `lift_pass_products[0]` | `null` | `"madonna-di-campiglio-campiglio-skiarea-pass"` | `verified_with_adjustment` | no |
| `destination:madonna-di-campiglio` | `rentals[0]` | `null` | `"madonna-di-campiglio:campiglio-ski-rent-lorenzetti"` | `verified_with_adjustment` | no |
| `destination:madonna-di-campiglio` | `rentals[1]` | `"madonna-di-campiglio:ski-rent-campiglio"` | `null` | `verified_with_adjustment` | no |
| `destination:madonna-di-campiglio` | `season_start_month` | `12` | `11` | `verified` | yes |
| `destination:pinzolo` | `base_elevation_m` | `null` | `800` | `estimated` | yes |
| `destination:pinzolo` | `country` | `null` | `"Italy"` | `estimated` | no |
| `destination:pinzolo` | `latitude` | `null` | `46.1617322` | `verified` | yes |
| `destination:pinzolo` | `lift_pass_products[0]` | `null` | `"pinzolo-campiglio-skiarea-pass"` | `verified_with_adjustment` | no |
| `destination:pinzolo` | `lift_pass_products[1]` | `null` | `"pinzolo-local-pass"` | `verified_with_adjustment` | no |
| `destination:pinzolo` | `longitude` | `null` | `10.7650043` | `verified` | yes |
| `destination:pinzolo` | `name` | `null` | `"Pinzolo"` | `verified` | no |
| `destination:pinzolo` | `price_level` | `null` | `"medium"` | `estimated` | no |
| `destination:pinzolo` | `region` | `null` | `"Trentino"` | `estimated` | no |
| `destination:pinzolo` | `rentals[0]` | `null` | `"pinzolo:il-comodo-sci"` | `verified_with_adjustment` | no |
| `destination:pinzolo` | `resort_id` | `null` | `"pinzolo"` | `verified` | no |
| `destination:pinzolo` | `season_end_month` | `null` | `4` | `estimated` | no |
| `destination:pinzolo` | `season_start_month` | `null` | `12` | `estimated` | no |
| `destination:pinzolo` | `season_windows` | `null` | `[]` | `needs_source` | no |
| `destination:pinzolo` | `ski_areas[0]` | `null` | `"pinzolo-ski-area"` | `verified_with_adjustment` | no |
| `destination:pinzolo` | `stay_bases[0]` | `null` | `"pinzolo-pinzolo"` | `verified_with_adjustment` | no |
| `destination:pinzolo` | `summit_elevation_m` | `null` | `2100` | `estimated` | yes |
| `destination:pinzolo` | `terrain_groups` | `null` | `[]` | `needs_source` | no |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `external_validity_summary` | `null` | `"Includes Pejo as disconnected external pass coverage; Pejo is not part of the ski-connected Campiglio terrain domain."` | `verified_with_adjustment` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `is_default` | `null` | `true` | `verified_with_adjustment` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `lift_pass_product_id` | `null` | `"folgarida-marilleva-campiglio-skiarea-pass"` | `verified` | no |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `name` | `null` | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | `verified` | no |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].amount` | `null` | `85.0` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].duration_days` | `null` | `1` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].source_url` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].amount` | `null` | `237.0` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].duration_days` | `null` | `3` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].source_url` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].amount` | `null` | `424.0` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].duration_days` | `null` | `6` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].source_url` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `terrain_domain_ids[0]` | `null` | `"campiglio-dolomiti-di-brenta"` | `verified_with_adjustment` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `valid_ski_area_ids[0]` | `null` | `"folgarida-marilleva-ski-area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `is_default` | `null` | `false` | `verified_with_adjustment` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `lift_pass_product_id` | `null` | `"folgarida-marilleva-local-pass"` | `verified` | no |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `name` | `null` | `"Folgarida Marilleva Skipass"` | `verified` | no |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].amount` | `null` | `67.0` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].duration_days` | `null` | `1` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].source_url` | `null` | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].amount` | `null` | `189.0` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].duration_days` | `null` | `3` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].source_url` | `null` | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].amount` | `null` | `339.0` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].duration_days` | `null` | `6` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].source_url` | `null` | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf"` | `verified` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `valid_ski_area_ids[0]` | `null` | `"folgarida-marilleva-ski-area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `external_validity_summary` | `null` | `"Includes Pejo as disconnected external pass coverage; Pejo is not part of the ski-connected Campiglio terrain domain."` | `verified_with_adjustment` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `is_default` | `null` | `true` | `verified_with_adjustment` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `lift_pass_product_id` | `null` | `"madonna-di-campiglio-campiglio-skiarea-pass"` | `verified` | no |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `name` | `null` | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | `verified` | no |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].amount` | `null` | `85.0` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].duration_days` | `null` | `1` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].source_url` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].amount` | `null` | `237.0` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].duration_days` | `null` | `3` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].source_url` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].amount` | `null` | `424.0` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].duration_days` | `null` | `6` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].source_url` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `terrain_domain_ids[0]` | `null` | `"campiglio-dolomiti-di-brenta"` | `verified_with_adjustment` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `valid_ski_area_ids[0]` | `null` | `"madonna-di-campiglio-ski-area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `external_validity_summary` | `null` | `"Includes Pejo as disconnected external pass coverage; Pejo is not part of the ski-connected Campiglio terrain domain."` | `verified_with_adjustment` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `is_default` | `null` | `true` | `verified_with_adjustment` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `lift_pass_product_id` | `null` | `"pinzolo-campiglio-skiarea-pass"` | `verified` | no |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `name` | `null` | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | `verified` | no |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].amount` | `null` | `85.0` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].duration_days` | `null` | `1` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].source_url` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].amount` | `null` | `237.0` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].duration_days` | `null` | `3` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].source_url` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].amount` | `null` | `424.0` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].duration_days` | `null` | `6` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].source_url` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `terrain_domain_ids[0]` | `null` | `"campiglio-dolomiti-di-brenta"` | `verified_with_adjustment` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `valid_ski_area_ids[0]` | `null` | `"pinzolo-ski-area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `is_default` | `null` | `false` | `verified_with_adjustment` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `lift_pass_product_id` | `null` | `"pinzolo-local-pass"` | `verified` | no |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `name` | `null` | `"Pinzolo Skipass"` | `verified` | no |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].amount` | `null` | `65.0` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].duration_days` | `null` | `1` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].source_url` | `null` | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].amount` | `null` | `180.0` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].duration_days` | `null` | `3` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].source_url` | `null` | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].amount` | `null` | `315.0` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].audience` | `null` | `"adult"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].currency` | `null` | `"EUR"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].duration_days` | `null` | `6` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].price_kind` | `null` | `"fixed"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].season_label` | `null` | `"high season 2025/26"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].source_url` | `null` | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf"` | `verified` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `terrain_domain_ids` | `null` | `[]` | `verified_with_adjustment` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `valid_ski_area_ids[0]` | `null` | `"pinzolo-ski-area"` | `verified_with_adjustment` | yes |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `validity_scope` | `null` | `"single_ski_area"` | `verified_with_adjustment` | yes |
| `rental:folgarida-marilleva:ski-point` | `lift_distance` | `null` | `"near"` | `estimated` | no |
| `rental:folgarida-marilleva:ski-point` | `name` | `null` | `"Ski Point"` | `verified` | no |
| `rental:folgarida-marilleva:ski-point` | `price_max` | `null` | `45.0` | `estimated` | no |
| `rental:folgarida-marilleva:ski-point` | `price_min` | `null` | `30.0` | `estimated` | no |
| `rental:folgarida-marilleva:ski-point` | `price_range` | `null` | `"EUR 30-45"` | `estimated` | no |
| `rental:folgarida-marilleva:ski-point` | `quality` | `null` | `"standard"` | `estimated` | no |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `lift_distance` | `null` | `"near"` | `estimated` | no |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `name` | `null` | `"Campiglio Ski Rent - Lorenzetti"` | `verified` | no |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `price_max` | `null` | `50.0` | `estimated` | no |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `price_min` | `null` | `35.0` | `estimated` | no |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `price_range` | `null` | `"EUR 35-50"` | `estimated` | no |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `quality` | `null` | `"standard"` | `estimated` | no |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `lift_distance` | `"near"` | `null` | `verified_with_adjustment` | no |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `name` | `"Ski Rent Campiglio"` | `null` | `verified_with_adjustment` | no |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `price_max` | `50.0` | `null` | `verified_with_adjustment` | no |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `price_min` | `35.0` | `null` | `verified_with_adjustment` | no |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `price_range` | `"EUR 35-50"` | `null` | `verified_with_adjustment` | no |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `quality` | `"standard"` | `null` | `verified_with_adjustment` | no |
| `rental:pinzolo:il-comodo-sci` | `lift_distance` | `null` | `"near"` | `estimated` | no |
| `rental:pinzolo:il-comodo-sci` | `name` | `null` | `"Il Comodo Sci"` | `verified` | no |
| `rental:pinzolo:il-comodo-sci` | `price_max` | `null` | `45.0` | `estimated` | no |
| `rental:pinzolo:il-comodo-sci` | `price_min` | `null` | `30.0` | `estimated` | no |
| `rental:pinzolo:il-comodo-sci` | `price_range` | `null` | `"EUR 30-45"` | `estimated` | no |
| `rental:pinzolo:il-comodo-sci` | `quality` | `null` | `"standard"` | `estimated` | no |
| `ski_area:folgarida-marilleva-ski-area` | `base_elevation_m` | `null` | `1300` | `verified` | yes |
| `ski_area:folgarida-marilleva-ski-area` | `latitude` | `null` | `46.3030712` | `verified` | yes |
| `ski_area:folgarida-marilleva-ski-area` | `longitude` | `null` | `10.8656079` | `verified` | yes |
| `ski_area:folgarida-marilleva-ski-area` | `name` | `null` | `"Folgarida-Marilleva"` | `verified` | no |
| `ski_area:folgarida-marilleva-ski-area` | `season_end_month` | `null` | `4` | `estimated` | no |
| `ski_area:folgarida-marilleva-ski-area` | `season_start_month` | `null` | `12` | `estimated` | no |
| `ski_area:folgarida-marilleva-ski-area` | `season_windows` | `null` | `[]` | `needs_source` | no |
| `ski_area:folgarida-marilleva-ski-area` | `ski_area_id` | `null` | `"folgarida-marilleva-ski-area"` | `verified` | no |
| `ski_area:folgarida-marilleva-ski-area` | `summit_elevation_m` | `null` | `2180` | `verified` | yes |
| `ski_area:folgarida-marilleva-ski-area` | `total_piste_km` | `null` | `62.0` | `verified` | yes |
| `ski_area:madonna-di-campiglio-ski-area` | `season_start_month` | `12` | `11` | `verified` | yes |
| `ski_area:madonna-di-campiglio-ski-area` | `total_piste_km` | `null` | `62.0` | `verified` | yes |
| `ski_area:pinzolo-ski-area` | `base_elevation_m` | `null` | `800` | `estimated` | yes |
| `ski_area:pinzolo-ski-area` | `latitude` | `null` | `46.1617322` | `verified` | yes |
| `ski_area:pinzolo-ski-area` | `longitude` | `null` | `10.7650043` | `verified` | yes |
| `ski_area:pinzolo-ski-area` | `name` | `null` | `"Pinzolo"` | `verified` | no |
| `ski_area:pinzolo-ski-area` | `season_end_month` | `null` | `4` | `estimated` | no |
| `ski_area:pinzolo-ski-area` | `season_start_month` | `null` | `12` | `estimated` | no |
| `ski_area:pinzolo-ski-area` | `season_windows` | `null` | `[]` | `needs_source` | no |
| `ski_area:pinzolo-ski-area` | `ski_area_id` | `null` | `"pinzolo-ski-area"` | `verified` | no |
| `ski_area:pinzolo-ski-area` | `summit_elevation_m` | `null` | `2100` | `estimated` | yes |
| `ski_area:pinzolo-ski-area` | `total_piste_km` | `null` | `31.0` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `atmosphere_tags[0]` | `null` | `"practical"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `atmosphere_tags[1]` | `null` | `"rail-access"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `base_type` | `null` | `"resort_station"` | `verified_with_adjustment` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `latitude` | `null` | `46.3195236` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `longitude` | `null` | `10.8398851` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `name` | `null` | `"Daolasa"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `nearest_lift_distance_m` | `null` | `285` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `nearest_lift_name` | `null` | `"Daolasa"` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `price_max` | `null` | `180.0` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `price_min` | `null` | `110.0` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `price_range` | `null` | `"EUR 110-180"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `regional_data_ids.nearest_lift_osm_node_id` | `null` | `"1096349433"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `regional_data_ids.osm_node_id` | `null` | `"6043719130"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `stay_base_id` | `null` | `"folgarida-marilleva-daolasa"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `supported_skill_levels[0]` | `null` | `"advanced"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `supported_skill_levels[1]` | `null` | `"beginner"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `supported_skill_levels[2]` | `null` | `"intermediate"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `atmosphere_tags[0]` | `null` | `"family-friendly"` | `verified_with_adjustment` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `atmosphere_tags[1]` | `null` | `"scenic"` | `verified_with_adjustment` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `base_type` | `null` | `"resort_station"` | `verified_with_adjustment` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `latitude` | `null` | `46.3030712` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `longitude` | `null` | `10.8656079` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `name` | `null` | `"Folgarida"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `nearest_lift_distance_m` | `null` | `516` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `nearest_lift_name` | `null` | `"Folgarida"` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `price_max` | `null` | `210.0` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `price_min` | `null` | `130.0` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `price_range` | `null` | `"EUR 130-210"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `regional_data_ids.nearest_lift_osm_node_id` | `null` | `"648469713"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `regional_data_ids.osm_node_id` | `null` | `"327580361"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `stay_base_id` | `null` | `"folgarida-marilleva-folgarida"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `supported_skill_levels[0]` | `null` | `"advanced"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `supported_skill_levels[1]` | `null` | `"beginner"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `supported_skill_levels[2]` | `null` | `"intermediate"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `atmosphere_tags[0]` | `null` | `"family-friendly"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `atmosphere_tags[1]` | `null` | `"ski-in-ski-out"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `base_type` | `null` | `"resort_station"` | `verified_with_adjustment` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `latitude` | `null` | `46.3024327` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `longitude` | `null` | `10.8101466` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `name` | `null` | `"Marilleva 1400"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `nearest_lift_distance_m` | `null` | `172` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `nearest_lift_name` | `null` | `"Marilleva"` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `price_max` | `null` | `190.0` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `price_min` | `null` | `120.0` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `price_range` | `null` | `"EUR 120-190"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `regional_data_ids.nearest_lift_osm_node_id` | `null` | `"1096349822"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `regional_data_ids.osm_node_id` | `null` | `"331259364"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `stay_base_id` | `null` | `"folgarida-marilleva-marilleva-1400"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `supported_skill_levels[0]` | `null` | `"advanced"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `supported_skill_levels[1]` | `null` | `"beginner"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `supported_skill_levels[2]` | `null` | `"intermediate"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `atmosphere_tags[0]` | `null` | `"family-friendly"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `atmosphere_tags[1]` | `null` | `"practical"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `base_type` | `null` | `"resort_station"` | `verified_with_adjustment` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `latitude` | `null` | `46.3144534` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `longitude` | `null` | `10.8127255` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `name` | `null` | `"Marilleva 900"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `nearest_lift_distance_m` | `null` | `47` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `nearest_lift_name` | `null` | `"Contrè"` | `verified` | yes |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `price_max` | `null` | `170.0` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `price_min` | `null` | `100.0` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `price_range` | `null` | `"EUR 100-170"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `regional_data_ids.nearest_lift_osm_node_id` | `null` | `"8662539441"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `regional_data_ids.osm_node_id` | `null` | `"331259493"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `stay_base_id` | `null` | `"folgarida-marilleva-marilleva-900"` | `verified` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `supported_skill_levels[0]` | `null` | `"advanced"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `supported_skill_levels[1]` | `null` | `"beginner"` | `estimated` | no |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `supported_skill_levels[2]` | `null` | `"intermediate"` | `estimated` | no |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `access_mode` | `"unknown"` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags[0]` | `null` | `"family-friendly"` | `verified_with_adjustment` | no |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags[1]` | `null` | `"premium"` | `verified_with_adjustment` | no |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags[2]` | `null` | `"scenic"` | `verified_with_adjustment` | no |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `base_type` | `null` | `"town"` | `verified_with_adjustment` | no |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `latitude` | `null` | `46.2269942` | `verified` | yes |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `longitude` | `null` | `10.8270157` | `verified` | yes |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_distance_m` | `null` | `243` | `verified` | yes |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_name` | `null` | `"Spinale Express"` | `verified` | yes |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `regional_data_ids.nearest_lift_osm_node_id` | `null` | `"1023438277"` | `verified` | no |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `regional_data_ids.osm_node_id` | `null` | `"1796357582"` | `verified` | no |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `supported_skill_levels[0]` | `null` | `"advanced"` | `estimated` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `access_mode` | `null` | `"walk"` | `verified_with_adjustment` | yes |
| `stay_base:pinzolo:pinzolo-pinzolo` | `atmosphere_tags[0]` | `null` | `"family-friendly"` | `verified_with_adjustment` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `atmosphere_tags[1]` | `null` | `"quiet"` | `verified_with_adjustment` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `atmosphere_tags[2]` | `null` | `"scenic"` | `verified_with_adjustment` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `base_type` | `null` | `"town"` | `verified_with_adjustment` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `latitude` | `null` | `46.1617322` | `verified` | yes |
| `stay_base:pinzolo:pinzolo-pinzolo` | `lift_distance` | `null` | `"near"` | `verified_with_adjustment` | yes |
| `stay_base:pinzolo:pinzolo-pinzolo` | `longitude` | `null` | `10.7650043` | `verified` | yes |
| `stay_base:pinzolo:pinzolo-pinzolo` | `name` | `null` | `"Pinzolo"` | `verified` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `nearest_lift_distance_m` | `null` | `206` | `verified` | yes |
| `stay_base:pinzolo:pinzolo-pinzolo` | `nearest_lift_name` | `null` | `"Funivia Pinzolo - Pra Rodont"` | `verified` | yes |
| `stay_base:pinzolo:pinzolo-pinzolo` | `price_max` | `null` | `180.0` | `estimated` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `price_min` | `null` | `110.0` | `estimated` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `price_range` | `null` | `"EUR 110-180"` | `estimated` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `regional_data_ids.nearest_lift_osm_node_id` | `null` | `"298987790"` | `verified` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `regional_data_ids.osm_node_id` | `null` | `"4311362989"` | `verified` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `stay_base_id` | `null` | `"pinzolo-pinzolo"` | `verified` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `supported_skill_levels[0]` | `null` | `"advanced"` | `estimated` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `supported_skill_levels[1]` | `null` | `"beginner"` | `estimated` | no |
| `stay_base:pinzolo:pinzolo-pinzolo` | `supported_skill_levels[2]` | `null` | `"intermediate"` | `estimated` | no |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `metric_scope` | `null` | `"aggregate"` | `verified_with_adjustment` | no |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `name` | `null` | `"Campiglio Dolomiti di Brenta"` | `verified` | no |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `season_windows` | `null` | `[]` | `needs_source` | no |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[0].resort_id` | `null` | `"folgarida-marilleva"` | `verified_with_adjustment` | yes |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[0].ski_area_id` | `null` | `"folgarida-marilleva-ski-area"` | `verified_with_adjustment` | yes |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[1].resort_id` | `null` | `"madonna-di-campiglio"` | `verified_with_adjustment` | yes |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[1].ski_area_id` | `null` | `"madonna-di-campiglio-ski-area"` | `verified_with_adjustment` | yes |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[2].resort_id` | `null` | `"pinzolo"` | `verified_with_adjustment` | yes |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[2].ski_area_id` | `null` | `"pinzolo-ski-area"` | `verified_with_adjustment` | yes |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `source_urls[0]` | `null` | `"https://www.campigliodolomiti.it/en/ski-area"` | `verified` | no |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `source_urls[1]` | `null` | `"https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf"` | `verified` | no |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `terrain_domain_id` | `null` | `"campiglio-dolomiti-di-brenta"` | `verified` | no |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `total_piste_km` | `null` | `156.0` | `verified_with_adjustment` | yes |
| `terrain_domain:matterhorn-ski-paradise` | `source_urls[2]` | `null` | `"https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn"` | `verified_with_adjustment` | no |
| `terrain_domain:matterhorn-ski-paradise` | `total_lift_count` | `54` | `52` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `display_name` | `null` | `"Folgarida-Marilleva"` | `verified` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.country_region` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.destination_coordinates` | `null` | `"verified"` | `verified` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.destination_elevation` | `null` | `"verified"` | `verified` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.destination_identity` | `null` | `"verified"` | `verified` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.lift_pass_products` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.price_ranges` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.rental_examples` | `null` | `"verified"` | `verified` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.rental_quality_tier` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.season_window` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.ski_areas` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.stay_base_lift_distance` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.stay_base_quality_tier` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.stay_bases` | `null` | `"verified"` | `verified` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.supported_skill_levels` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.terrain_groups` | `null` | `"needs_source"` | `needs_source` | no |
| `trust_manifest:destination:folgarida-marilleva` | `notes[0]` | `null` | `"The resulting model represents Folgarida-Marilleva as an independent destination with one local weather-owning ski area and four reviewed stay bases."` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `notes[1]` | `null` | `"The local 62 km and 1300-2180 m facts remain child-scoped; the shared 156 km aggregate belongs only to campiglio-dolomiti-di-brenta."` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `notes[2]` | `null` | `"Country/region normalization, price level, season-month defaults, lodging and rental prices and quality, supported skills, rental lift-distance, and unsourced atmosphere tags are estimates."` | `estimated` | no |
| `trust_manifest:destination:folgarida-marilleva` | `notes[3]` | `null` | `"folgarida-marilleva-ski-area is a new weather identity that requires owner-run history backfill and climatology after deployment."` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[0]` | `null` | `"https://www.campigliodolomiti.it/en/ski-area"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[1]` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[2]` | `null` | `"https://www.openstreetmap.org/node/1096349433"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[3]` | `null` | `"https://www.openstreetmap.org/node/1096349822"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[4]` | `null` | `"https://www.openstreetmap.org/node/327580361"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[5]` | `null` | `"https://www.openstreetmap.org/node/331259364"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[6]` | `null` | `"https://www.openstreetmap.org/node/331259493"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[7]` | `null` | `"https://www.openstreetmap.org/node/6043719130"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[8]` | `null` | `"https://www.openstreetmap.org/node/648469713"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[9]` | `null` | `"https://www.openstreetmap.org/node/8662539441"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[10]` | `null` | `"https://www.ski.it/en/skiarea/folgarida-marilleva"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[11]` | `null` | `"https://www.ski.it/it/noleggi/folgarida/ski-point"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[12]` | `null` | `"https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[13]` | `null` | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.destination_elevation` | `"verified"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.lift_pass_products` | `"needs_source"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.rental_examples` | `"estimated"` | `"verified"` | `verified` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.season_window` | `"verified"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.ski_areas` | `"verified"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.stay_base_lift_distance` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[0]` | `"Trust-contract first pass; not a full official-source recuration."` | `"Full destination sweep uses official local, connected-domain, pass, rental, ski-map, and OSM evidence."` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[1]` | `"Price, quality, lift-distance, skill, and rental fields are product-curated estimates until source-backed enrichment lands."` | `"Madonna di Campiglio remains an independent destination and retains madonna-di-campiglio-ski-area as its weather identity."` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[2]` | `null` | `"The local 62 km fact stays on Madonna's child ski area; the shared 156 km aggregate belongs only to campiglio-dolomiti-di-brenta."` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[3]` | `null` | `"The shared pass references the connected terrain domain while Pejo remains disconnected external pass validity."` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[4]` | `null` | `"Price ranges, quality tiers, supported skill levels, rental lift-distance, and other rows marked estimated remain estimates."` | `estimated` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[0]` | `"docs/sprint-17-resort-audit-results.md"` | `null` | `needs_source` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[1]` | `null` | `"https://www.campigliodolomiti.it/en/ski-area"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[2]` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[3]` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[4]` | `null` | `"https://www.openstreetmap.org/node/1023438277"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[5]` | `null` | `"https://www.openstreetmap.org/node/1796357582"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[6]` | `null` | `"https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[7]` | `null` | `"https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `display_name` | `null` | `"Pinzolo"` | `verified` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.country_region` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.destination_coordinates` | `null` | `"verified"` | `verified` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.destination_elevation` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.destination_identity` | `null` | `"verified"` | `verified` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.lift_pass_products` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.price_ranges` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.rental_examples` | `null` | `"verified"` | `verified` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.rental_quality_tier` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.season_window` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.ski_areas` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.stay_base_lift_distance` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.stay_base_quality_tier` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.stay_bases` | `null` | `"verified"` | `verified` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.supported_skill_levels` | `null` | `"estimated"` | `estimated` | no |
| `trust_manifest:destination:pinzolo` | `field_statuses.terrain_groups` | `null` | `"needs_source"` | `needs_source` | no |
| `trust_manifest:destination:pinzolo` | `notes[0]` | `null` | `"The resulting model represents Pinzolo as an independent destination with one local weather-owning ski area and source-backed identity and coordinates."` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `notes[1]` | `null` | `"Pinzolo's local 31 km fact remains child-scoped; the 156 km aggregate belongs only to campiglio-dolomiti-di-brenta."` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `notes[2]` | `null` | `"The 800-2100 m geometry, country/region normalization, price level, season-month defaults, lodging and rental prices and quality, supported skills, and rental lift-distance are estimates."` | `estimated` | no |
| `trust_manifest:destination:pinzolo` | `notes[3]` | `null` | `"pinzolo-ski-area is a new weather identity that requires owner-run history backfill and climatology after deployment."` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `source_refs[0]` | `null` | `"https://www.bergfex.it/pinzolo/"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `source_refs[1]` | `null` | `"https://www.campigliodolomiti.it/en/services/il-comodo-sci"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `source_refs[2]` | `null` | `"https://www.campigliodolomiti.it/en/ski-area"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `source_refs[3]` | `null` | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `source_refs[4]` | `null` | `"https://www.openstreetmap.org/node/298987790"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `source_refs[5]` | `null` | `"https://www.openstreetmap.org/node/4311362989"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `source_refs[6]` | `null` | `"https://www.ski.it/en/skiarea/pinzolo"` | `verified_with_adjustment` | no |
| `trust_manifest:destination:pinzolo` | `source_refs[7]` | `null` | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `display_name` | `null` | `"Campiglio Dolomiti di Brenta"` | `verified` | no |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `field_statuses.membership` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `field_statuses.season_window` | `null` | `"needs_source"` | `needs_source` | no |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `field_statuses.terrain_metrics` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[0]` | `null` | `"Official sources identify Madonna di Campiglio, Pinzolo, and Folgarida-Marilleva as the ski-connected domain members; Pejo is excluded and remains external pass validity."` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[1]` | `null` | `"The 156 km aggregate uses the official tourism-domain value while preserving the official map's conflicting 155 km value."` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[2]` | `null` | `"Lift count, domain elevations, difficulty split, and shared season window remain omitted until same-scope sources are accepted."` | `needs_source` | no |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[3]` | `null` | `"The terrain domain owns no weather history; weather remains on the three local ski-area identities."` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `source_refs[0]` | `null` | `"https://www.campigliodolomiti.it/en/ski-area"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `source_refs[1]` | `null` | `"https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `display_name` | `null` | `"Matterhorn Ski Paradise"` | `verified` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `field_statuses.membership` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `field_statuses.season_window` | `null` | `"needs_source"` | `needs_source` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `field_statuses.terrain_metrics` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `notes[0]` | `null` | `"Official Matterhorn Paradise sources support ski-connected Zermatt and Cervinia membership; Snowcast normalizes those places to their modeled destination and ski-area ids."` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `notes[1]` | `null` | `"The current official region page supports the 360 km and 52-lift cross-border aggregate; terrain_metrics remains verified_with_adjustment because the 1620 m lower bound is normalized from the official Zermatt resort-side elevation. The 3883 m summit is separately source-backed, and the domain does not own weather evidence."` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `notes[2]` | `null` | `"No shared-domain season window is stored; Zermatt and Cervinia season evidence remains scoped to their local ski areas and pass products."` | `needs_source` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[0]` | `null` | `"https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[1]` | `null` | `"https://www.matterhornparadise.ch/en/experience/peaks/matterhorn-glacier-paradise"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[2]` | `null` | `"https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[3]` | `null` | `"https://www.matterhornparadise.ch/en/experience/skiing"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:tignes-val-disere` | `display_name` | `null` | `"Tignes - Val d'Isere"` | `verified` | no |
| `trust_manifest:terrain_domain:tignes-val-disere` | `field_statuses.membership` | `null` | `"verified"` | `verified` | no |
| `trust_manifest:terrain_domain:tignes-val-disere` | `field_statuses.season_window` | `null` | `"needs_source"` | `needs_source` | no |
| `trust_manifest:terrain_domain:tignes-val-disere` | `field_statuses.terrain_metrics` | `null` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:tignes-val-disere` | `notes[0]` | `null` | `"Official Tignes and Val d'Isere pages identify one ski-connected 300 km domain spanning both modeled destinations."` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:tignes-val-disere` | `notes[1]` | `null` | `"The aggregate lift count is verified_with_adjustment: official pages conflict at 74 and 71 lifts, so the reviewed Bergfex category sum supplies the normalized value of 72; aggregate elevations remain scoped to the domain."` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:tignes-val-disere` | `notes[2]` | `null` | `"No shared-domain season window is stored; season dates remain owned by the local ski-area records."` | `needs_source` | no |
| `trust_manifest:terrain_domain:tignes-val-disere` | `source_refs[0]` | `null` | `"https://en.tignes.net/skiing/ski-area"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:tignes-val-disere` | `source_refs[1]` | `null` | `"https://www.bergfex.com/skiregionen/valdiseres-tignes/"` | `verified_with_adjustment` | no |
| `trust_manifest:terrain_domain:tignes-val-disere` | `source_refs[2]` | `null` | `"https://www.valdisere.com/en/val-disere-in-winter/skiing-winter-fun/ski-area-french-alps/"` | `verified_with_adjustment` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `destination:madonna-di-campiglio` | `base_elevation_m` | `reviewed-no-change` | Destination base elevation 1550 m retained. |
| `destination:madonna-di-campiglio` | `country` | `reviewed-no-change` | Italy identity value retained. |
| `destination:madonna-di-campiglio` | `latitude` | `reviewed-no-change` | Destination latitude 46.2267 retained. |
| `destination:madonna-di-campiglio` | `lift_pass_products` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `destination:madonna-di-campiglio` | `longitude` | `reviewed-no-change` | Destination longitude 10.8268 retained. |
| `destination:madonna-di-campiglio` | `name` | `reviewed-no-change` | Madonna di Campiglio name retained. |
| `destination:madonna-di-campiglio` | `price_level` | `reviewed-no-change` | Existing medium price-level estimate retained; this is an estimate, not a sourced market-price fact. |
| `destination:madonna-di-campiglio` | `region` | `reviewed-no-change` | Trentino regional identity retained. |
| `destination:madonna-di-campiglio` | `rentals` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `destination:madonna-di-campiglio` | `resort_id` | `reviewed-no-change` | Stable destination ID retained. |
| `destination:madonna-di-campiglio` | `season_end_month` | `reviewed-no-change` | Existing April season-end estimate retained; no exact future season window is claimed. |
| `destination:madonna-di-campiglio` | `season_start_month` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:madonna-di-campiglio` | `season_windows` | `unresolved` | No accepted source provides an exact future destination season window. The final catalog omits this field; it remains unresolved until sourced. |
| `destination:madonna-di-campiglio` | `ski_areas` | `unresolved` | The final catalog contains the destination's ski-area records from the reviewed leaf targets in this plan; Exact leaf deltas are reported separately from this container row. |
| `destination:madonna-di-campiglio` | `stay_bases` | `unresolved` | The final catalog contains the destination's stay-base records from the reviewed leaf targets in this plan; Exact leaf deltas are reported separately from this container row. |
| `destination:madonna-di-campiglio` | `summit_elevation_m` | `reviewed-no-change` | Destination summit elevation 2504 m retained. |
| `destination:madonna-di-campiglio` | `terrain_groups` | `not-applicable` | No destination-local aggregate terrain group is reviewed; the connected 156 km aggregate belongs to the Campiglio terrain domain. |
| `destination:madonna-di-campiglio` | `lift_pass_products[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:madonna-di-campiglio` | `rentals[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:madonna-di-campiglio` | `rentals[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:pinzolo` | `base_elevation_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `country` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `latitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `lift_pass_products` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `destination:pinzolo` | `longitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `price_level` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `region` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `rentals` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `destination:pinzolo` | `resort_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `season_end_month` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `season_start_month` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `season_windows` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `ski_areas` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `destination:pinzolo` | `stay_bases` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `destination:pinzolo` | `summit_elevation_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `terrain_groups` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:pinzolo` | `lift_pass_products[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:pinzolo` | `lift_pass_products[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:pinzolo` | `rentals[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:pinzolo` | `ski_areas[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:pinzolo` | `stay_bases[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:folgarida-marilleva` | `base_elevation_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `country` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `latitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `lift_pass_products` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `destination:folgarida-marilleva` | `longitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `price_level` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `region` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `rentals` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `destination:folgarida-marilleva` | `resort_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `season_end_month` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `season_start_month` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `season_windows` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `ski_areas` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `destination:folgarida-marilleva` | `stay_bases` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `destination:folgarida-marilleva` | `summit_elevation_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `terrain_groups` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `destination:folgarida-marilleva` | `lift_pass_products[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:folgarida-marilleva` | `lift_pass_products[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:folgarida-marilleva` | `rentals[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:folgarida-marilleva` | `ski_areas[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:folgarida-marilleva` | `stay_bases[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:folgarida-marilleva` | `stay_bases[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:folgarida-marilleva` | `stay_bases[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `destination:folgarida-marilleva` | `stay_bases[3]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `ski_area:madonna-di-campiglio-ski-area` | `base_elevation_m` | `reviewed-no-change` | Ski-area base elevation 1550 m retained. |
| `ski_area:madonna-di-campiglio-ski-area` | `latitude` | `reviewed-no-change` | Ski-area latitude 46.2267 retained. |
| `ski_area:madonna-di-campiglio-ski-area` | `longitude` | `reviewed-no-change` | Ski-area longitude 10.8268 retained. |
| `ski_area:madonna-di-campiglio-ski-area` | `name` | `reviewed-no-change` | Existing Madonna di Campiglio ski-area name retained. |
| `ski_area:madonna-di-campiglio-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | No accepted child-scoped source supports the ski area's advanced piste kilometers. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:madonna-di-campiglio-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | No accepted child-scoped source supports the ski area's beginner piste kilometers. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:madonna-di-campiglio-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | No accepted child-scoped source supports the ski area's intermediate piste kilometers. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:madonna-di-campiglio-ski-area` | `season_end_month` | `reviewed-no-change` | Existing April ski-area season-end estimate retained; no exact future season window is claimed. |
| `ski_area:madonna-di-campiglio-ski-area` | `season_start_month` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:madonna-di-campiglio-ski-area` | `season_windows` | `unresolved` | No accepted child-scoped source provides an exact future operating window. The final catalog omits this field; it remains unresolved until sourced. |
| `ski_area:madonna-di-campiglio-ski-area` | `ski_area_id` | `reviewed-no-change` | Existing Madonna di Campiglio ski-area ski_area_id retained. |
| `ski_area:madonna-di-campiglio-ski-area` | `summit_elevation_m` | `reviewed-no-change` | Ski-area summit elevation 2504 m retained. |
| `ski_area:madonna-di-campiglio-ski-area` | `total_lift_count` | `unresolved` | No accepted child-scoped source supports the ski area's lift count. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:madonna-di-campiglio-ski-area` | `total_piste_km` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:pinzolo-ski-area` | `base_elevation_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:pinzolo-ski-area` | `latitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:pinzolo-ski-area` | `longitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:pinzolo-ski-area` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:pinzolo-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | No accepted child-scoped source supports the ski area's advanced piste kilometers. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:pinzolo-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | No accepted child-scoped source supports the ski area's beginner piste kilometers. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:pinzolo-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | No accepted child-scoped source supports the ski area's intermediate piste kilometers. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:pinzolo-ski-area` | `season_end_month` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:pinzolo-ski-area` | `season_start_month` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:pinzolo-ski-area` | `season_windows` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:pinzolo-ski-area` | `ski_area_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:pinzolo-ski-area` | `summit_elevation_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:pinzolo-ski-area` | `total_lift_count` | `unresolved` | No accepted child-scoped source supports the ski area's lift count. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:pinzolo-ski-area` | `total_piste_km` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:folgarida-marilleva-ski-area` | `base_elevation_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:folgarida-marilleva-ski-area` | `latitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:folgarida-marilleva-ski-area` | `longitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:folgarida-marilleva-ski-area` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:folgarida-marilleva-ski-area` | `piste_km_by_difficulty.advanced` | `unresolved` | No accepted child-scoped source supports the ski area's advanced piste kilometers. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:folgarida-marilleva-ski-area` | `piste_km_by_difficulty.beginner` | `unresolved` | No accepted child-scoped source supports the ski area's beginner piste kilometers. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:folgarida-marilleva-ski-area` | `piste_km_by_difficulty.intermediate` | `unresolved` | No accepted child-scoped source supports the ski area's intermediate piste kilometers. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:folgarida-marilleva-ski-area` | `season_end_month` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:folgarida-marilleva-ski-area` | `season_start_month` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:folgarida-marilleva-ski-area` | `season_windows` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:folgarida-marilleva-ski-area` | `ski_area_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:folgarida-marilleva-ski-area` | `summit_elevation_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `ski_area:folgarida-marilleva-ski-area` | `total_lift_count` | `unresolved` | No accepted child-scoped source supports the ski area's lift count. The final catalog omits the value; it remains unresolved until child-scoped evidence is available. |
| `ski_area:folgarida-marilleva-ski-area` | `total_piste_km` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `access_mode` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `base_type` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `latitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `lift_distance` | `reviewed-no-change` | The approved plan proposed a value for this field, but the parsed e8f4e11-to-e57b5bb snapshots contain no delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `longitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `name` | `reviewed-no-change` | The approved plan proposed a value for this field, but the parsed e8f4e11-to-e57b5bb snapshots contain no delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_distance_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `price_max` | `reviewed-no-change` | The approved plan proposed a value for this field, but the parsed e8f4e11-to-e57b5bb snapshots contain no delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `price_min` | `reviewed-no-change` | The approved plan proposed a value for this field, but the parsed e8f4e11-to-e57b5bb snapshots contain no delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `price_range` | `reviewed-no-change` | The approved plan proposed a value for this field, but the parsed e8f4e11-to-e57b5bb snapshots contain no delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `quality` | `reviewed-no-change` | The approved plan proposed a value for this field, but the parsed e8f4e11-to-e57b5bb snapshots contain no delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `regional_data_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `stay_base_id` | `reviewed-no-change` | The approved plan proposed a value for this field, but the parsed e8f4e11-to-e57b5bb snapshots contain no delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `supported_skill_levels` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `regional_data_ids.nearest_lift_osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `regional_data_ids.osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `supported_skill_levels[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `access_mode` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `atmosphere_tags` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `base_type` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `latitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `longitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `nearest_lift_distance_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `nearest_lift_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `price_max` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `price_min` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `price_range` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `quality` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `regional_data_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `stay_base_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `supported_skill_levels` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `atmosphere_tags[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `atmosphere_tags[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `atmosphere_tags[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `regional_data_ids.nearest_lift_osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `regional_data_ids.osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `supported_skill_levels[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `supported_skill_levels[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:pinzolo:pinzolo-pinzolo` | `supported_skill_levels[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `access_mode` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `atmosphere_tags` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `base_type` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `latitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `longitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `nearest_lift_distance_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `nearest_lift_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `price_max` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `price_min` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `price_range` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `quality` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `regional_data_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `stay_base_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `supported_skill_levels` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `atmosphere_tags[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `atmosphere_tags[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `regional_data_ids.nearest_lift_osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `regional_data_ids.osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `supported_skill_levels[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `supported_skill_levels[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `supported_skill_levels[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `access_mode` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `atmosphere_tags` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `base_type` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `latitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `longitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `nearest_lift_distance_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `nearest_lift_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `price_max` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `price_min` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `price_range` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `quality` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `regional_data_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `stay_base_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `supported_skill_levels` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `atmosphere_tags[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `atmosphere_tags[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `regional_data_ids.nearest_lift_osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `regional_data_ids.osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `supported_skill_levels[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `supported_skill_levels[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `supported_skill_levels[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `access_mode` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `atmosphere_tags` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `base_type` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `latitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `longitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `nearest_lift_distance_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `nearest_lift_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `price_max` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `price_min` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `price_range` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `quality` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `regional_data_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `stay_base_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `supported_skill_levels` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `atmosphere_tags[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `atmosphere_tags[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `regional_data_ids.nearest_lift_osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `regional_data_ids.osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `supported_skill_levels[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `supported_skill_levels[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `supported_skill_levels[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `access_mode` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `atmosphere_tags` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `base_type` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `latitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `longitude` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `nearest_lift_distance_m` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `nearest_lift_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `price_max` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `price_min` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `price_range` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `quality` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `regional_data_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `stay_base_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `supported_skill_levels` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `atmosphere_tags[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `atmosphere_tags[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `regional_data_ids.nearest_lift_osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `regional_data_ids.osm_node_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `supported_skill_levels[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `supported_skill_levels[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `supported_skill_levels[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `rental:folgarida-marilleva:ski-point` | `lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:folgarida-marilleva:ski-point` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:folgarida-marilleva:ski-point` | `price_max` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:folgarida-marilleva:ski-point` | `price_min` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:folgarida-marilleva:ski-point` | `price_range` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:folgarida-marilleva:ski-point` | `quality` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `price_max` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `price_min` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `price_range` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `quality` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `price_max` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `price_min` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `price_range` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `quality` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:pinzolo:il-comodo-sci` | `lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:pinzolo:il-comodo-sci` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:pinzolo:il-comodo-sci` | `price_max` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:pinzolo:il-comodo-sci` | `price_min` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:pinzolo:il-comodo-sci` | `price_range` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `rental:pinzolo:il-comodo-sci` | `quality` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `external_validity_summary` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `is_default` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `lift_pass_product_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `terrain_domain_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `valid_ski_area_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `validity_scope` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `terrain_domain_ids[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `valid_ski_area_ids[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `external_validity_summary` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `is_default` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `lift_pass_product_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `terrain_domain_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `valid_ski_area_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `validity_scope` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `terrain_domain_ids[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `valid_ski_area_ids[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `external_validity_summary` | `reviewed-no-change` | The approved plan proposed a value for this field, but the parsed e8f4e11-to-e57b5bb snapshots contain no delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `is_default` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `lift_pass_product_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `terrain_domain_ids` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `valid_ski_area_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `validity_scope` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `valid_ski_area_ids[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `external_validity_summary` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `is_default` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `lift_pass_product_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `terrain_domain_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `valid_ski_area_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `validity_scope` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `terrain_domain_ids[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `valid_ski_area_ids[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `external_validity_summary` | `reviewed-no-change` | The approved plan proposed a value for this field, but the parsed e8f4e11-to-e57b5bb snapshots contain no delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `is_default` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `lift_pass_product_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `terrain_domain_ids` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `valid_ski_area_ids` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `validity_scope` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].amount` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].audience` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].currency` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].duration_days` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].price_kind` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].season_label` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].source_url` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `valid_ski_area_ids[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `terrain_domain:matterhorn-ski-paradise` | `base_elevation_m` | `reviewed-no-change` | Existing Matterhorn Ski Paradise base_elevation_m value retained; The final snapshot does not modify this domain. |
| `terrain_domain:matterhorn-ski-paradise` | `metric_scope` | `reviewed-no-change` | Existing Matterhorn Ski Paradise metric_scope value retained; The final snapshot does not modify this domain. |
| `terrain_domain:matterhorn-ski-paradise` | `name` | `reviewed-no-change` | Existing Matterhorn Ski Paradise name value retained; The final snapshot does not modify this domain. |
| `terrain_domain:matterhorn-ski-paradise` | `piste_km_by_difficulty.advanced` | `unresolved` | The existing Matterhorn domain has no piste_km_by_difficulty.advanced value and this Campiglio task reviewed no same-scope source; The final catalog leaves it unset. |
| `terrain_domain:matterhorn-ski-paradise` | `piste_km_by_difficulty.beginner` | `unresolved` | The existing Matterhorn domain has no piste_km_by_difficulty.beginner value and this Campiglio task reviewed no same-scope source; The final catalog leaves it unset. |
| `terrain_domain:matterhorn-ski-paradise` | `piste_km_by_difficulty.intermediate` | `unresolved` | The existing Matterhorn domain has no piste_km_by_difficulty.intermediate value and this Campiglio task reviewed no same-scope source; The final catalog leaves it unset. |
| `terrain_domain:matterhorn-ski-paradise` | `season_windows` | `unresolved` | The existing Matterhorn domain has no shared season window and this Campiglio task reviewed no source for one; The final catalog leaves it unset. |
| `terrain_domain:matterhorn-ski-paradise` | `ski_area_refs` | `reviewed-no-change` | Existing Matterhorn Ski Paradise ski_area_refs value retained; The final snapshot does not modify this domain. |
| `terrain_domain:matterhorn-ski-paradise` | `source_urls` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `terrain_domain:matterhorn-ski-paradise` | `summit_elevation_m` | `reviewed-no-change` | Existing Matterhorn Ski Paradise summit_elevation_m value retained; The final snapshot does not modify this domain. |
| `terrain_domain:matterhorn-ski-paradise` | `terrain_domain_id` | `reviewed-no-change` | Existing Matterhorn Ski Paradise terrain_domain_id value retained; The final snapshot does not modify this domain. |
| `terrain_domain:matterhorn-ski-paradise` | `total_lift_count` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `terrain_domain:matterhorn-ski-paradise` | `total_piste_km` | `reviewed-no-change` | Existing Matterhorn Ski Paradise total_piste_km value retained; The final snapshot does not modify this domain. |
| `terrain_domain:matterhorn-ski-paradise` | `source_urls[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `base_elevation_m` | `unresolved` | No accepted source supports the Campiglio domain's domain-wide base elevation. The final catalog omits the field; it remains unresolved until same-scope evidence is available. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `metric_scope` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `piste_km_by_difficulty.advanced` | `unresolved` | No accepted source supports the Campiglio domain's advanced piste kilometers. The final catalog omits the field; it remains unresolved until same-scope evidence is available. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `piste_km_by_difficulty.beginner` | `unresolved` | No accepted source supports the Campiglio domain's beginner piste kilometers. The final catalog omits the field; it remains unresolved until same-scope evidence is available. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `piste_km_by_difficulty.intermediate` | `unresolved` | No accepted source supports the Campiglio domain's intermediate piste kilometers. The final catalog omits the field; it remains unresolved until same-scope evidence is available. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `season_windows` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `source_urls` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `summit_elevation_m` | `unresolved` | No accepted source supports the Campiglio domain's domain-wide summit elevation. The final catalog omits the field; it remains unresolved until same-scope evidence is available. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `terrain_domain_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `total_lift_count` | `unresolved` | Official same-scope sources conflict: the official tourism page reports 61 lifts and the official ski map reports 58. Both are official, but neither is established as authoritative or current enough to select; no accepted same-scope Bergfex fallback was used. The final catalog therefore omits total_lift_count and the field remains unresolved. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `total_piste_km` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[0].resort_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[0].ski_area_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[1].resort_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[1].ski_area_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[2].resort_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[2].ski_area_id` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `source_urls[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `source_urls[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `display_name` | `reviewed-no-change` | Existing trust display name Madonna di Campiglio retained. |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:destination:madonna-di-campiglio` | `notes` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.destination_elevation` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.lift_pass_products` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.rental_examples` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.season_window` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.ski_areas` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.stay_base_lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[3]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[4]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[3]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[4]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[5]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[6]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[7]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `display_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:destination:pinzolo` | `notes` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:destination:pinzolo` | `source_refs` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:destination:pinzolo` | `field_statuses.country_region` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.destination_coordinates` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.destination_elevation` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.destination_identity` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.lift_pass_products` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.price_ranges` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.rental_examples` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.rental_quality_tier` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.season_window` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.ski_areas` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.stay_base_lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.stay_base_quality_tier` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.stay_bases` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.supported_skill_levels` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `field_statuses.terrain_groups` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `notes[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `notes[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `notes[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `notes[3]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `source_refs[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `source_refs[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `source_refs[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `source_refs[3]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `source_refs[4]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `source_refs[5]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `source_refs[6]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:pinzolo` | `source_refs[7]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `display_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:destination:folgarida-marilleva` | `notes` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.country_region` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.destination_coordinates` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.destination_elevation` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.destination_identity` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.lift_pass_products` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.price_ranges` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.rental_examples` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.rental_quality_tier` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.season_window` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.ski_areas` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.stay_base_lift_distance` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.stay_base_quality_tier` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.stay_bases` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.supported_skill_levels` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.terrain_groups` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `notes[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `notes[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `notes[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `notes[3]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[10]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[11]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[12]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[13]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[3]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[4]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[5]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[6]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[7]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[8]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[9]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `display_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `field_statuses` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `notes` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `source_refs` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `field_statuses.membership` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `field_statuses.season_window` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `field_statuses.terrain_metrics` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `notes[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `notes[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `notes[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `source_refs[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `source_refs[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:tignes-val-disere` | `source_refs[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `display_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `field_statuses` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `notes` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `field_statuses.membership` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `field_statuses.season_window` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `field_statuses.terrain_metrics` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `notes[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `notes[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `notes[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[3]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `display_name` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot delta. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `field_statuses` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `source_refs` | `reviewed-no-change` | Container reviewed in full; exact changed leaves are reported as separate changed coverage rows. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `field_statuses.membership` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `field_statuses.season_window` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `field_statuses.terrain_metrics` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[2]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[3]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `source_refs[0]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `source_refs[1]` | `changed` | Exact parsed e8f4e11-to-e57b5bb snapshot leaf delta. |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization | Boundary Targets |
| --- | --- | --- | --- | --- | --- | --- |
| `destination:folgarida-marilleva` | `name` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"Folgarida-Marilleva"` | The candidate-specific official Folgarida-Marilleva page presents booking and accommodation, local ski access, and distinct destination positioning. |  | `folgarida-marilleva` |
| `destination:madonna-di-campiglio` | `name` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `"Madonna di Campiglio"` | The candidate-specific official Madonna di Campiglio page presents booking and accommodation, local ski access, and distinct destination positioning. |  | `madonna-di-campiglio` |
| `destination:pinzolo` | `name` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"Pinzolo"` | The candidate-specific official Pinzolo page presents booking and accommodation, local ski access, and distinct destination positioning. |  | `pinzolo` |
| `destination:folgarida-marilleva` | `base_elevation_m` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `1300` | The linked Campiglio Dolomiti di Brenta Official Ski Map supports the reviewed base_elevation_m leaf. |  |  |
| `destination:folgarida-marilleva` | `latitude` | [OpenStreetMap node 327580361 - Folgarida place node](https://www.openstreetmap.org/node/327580361) | `46.3030712` | The exact OSM object supplies the reviewed latitude leaf. |  |  |
| `destination:folgarida-marilleva` | `lift_pass_products[0]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"folgarida-marilleva-campiglio-skiarea-pass"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed lift_pass_products[0] leaf. |  |  |
| `destination:folgarida-marilleva` | `lift_pass_products[1]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"folgarida-marilleva-local-pass"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed lift_pass_products[1] leaf. |  |  |
| `destination:folgarida-marilleva` | `longitude` | [OpenStreetMap node 327580361 - Folgarida place node](https://www.openstreetmap.org/node/327580361) | `10.8656079` | The exact OSM object supplies the reviewed longitude leaf. |  |  |
| `destination:folgarida-marilleva` | `rentals[0]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"folgarida-marilleva:ski-point"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed rentals[0] leaf. |  |  |
| `destination:folgarida-marilleva` | `resort_id` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"Folgarida-Marilleva"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed resort_id leaf. | The official name is normalized to stable catalog ID folgarida-marilleva. |  |
| `destination:folgarida-marilleva` | `ski_areas[0]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"folgarida-marilleva-ski-area"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed ski_areas[0] leaf. |  |  |
| `destination:folgarida-marilleva` | `stay_bases[0]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"folgarida-marilleva-daolasa"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed stay_bases[0] leaf. |  |  |
| `destination:folgarida-marilleva` | `stay_bases[1]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"folgarida-marilleva-folgarida"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed stay_bases[1] leaf. |  |  |
| `destination:folgarida-marilleva` | `stay_bases[2]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"folgarida-marilleva-marilleva-1400"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed stay_bases[2] leaf. |  |  |
| `destination:folgarida-marilleva` | `stay_bases[3]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"folgarida-marilleva-marilleva-900"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed stay_bases[3] leaf. |  |  |
| `destination:folgarida-marilleva` | `summit_elevation_m` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `2180` | The linked Campiglio Dolomiti di Brenta Official Ski Map supports the reviewed summit_elevation_m leaf. |  |  |
| `destination:madonna-di-campiglio` | `lift_pass_products[0]` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `"madonna-di-campiglio-campiglio-skiarea-pass"` | The linked Madonna di Campiglio - Official Ski Area supports the reviewed lift_pass_products[0] leaf. |  |  |
| `destination:madonna-di-campiglio` | `rentals[0]` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `"madonna-di-campiglio:campiglio-ski-rent-lorenzetti"` | The linked Madonna di Campiglio - Official Ski Area supports the reviewed rentals[0] leaf. |  |  |
| `destination:madonna-di-campiglio` | `rentals[1]` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `null` | The linked Madonna di Campiglio - Official Ski Area supports the reviewed rentals[1] leaf. |  |  |
| `destination:madonna-di-campiglio` | `season_start_month` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `11` | The linked Madonna di Campiglio - Official Ski Area supports the reviewed season_start_month leaf. |  |  |
| `destination:pinzolo` | `base_elevation_m` | [Bergfex - Pinzolo](https://www.bergfex.it/pinzolo/) | `800` | The linked Bergfex - Pinzolo supports the reviewed base_elevation_m leaf. |  |  |
| `destination:pinzolo` | `latitude` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `46.1617322` | The exact OSM object supplies the reviewed latitude leaf. |  |  |
| `destination:pinzolo` | `lift_pass_products[0]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"pinzolo-campiglio-skiarea-pass"` | The linked Pinzolo - Official Ski Area supports the reviewed lift_pass_products[0] leaf. |  |  |
| `destination:pinzolo` | `lift_pass_products[1]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"pinzolo-local-pass"` | The linked Pinzolo - Official Ski Area supports the reviewed lift_pass_products[1] leaf. |  |  |
| `destination:pinzolo` | `longitude` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `10.7650043` | The exact OSM object supplies the reviewed longitude leaf. |  |  |
| `destination:pinzolo` | `rentals[0]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"pinzolo:il-comodo-sci"` | The linked Pinzolo - Official Ski Area supports the reviewed rentals[0] leaf. |  |  |
| `destination:pinzolo` | `resort_id` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"Pinzolo"` | The linked Pinzolo - Official Ski Area supports the reviewed resort_id leaf. | The official name is normalized to stable catalog ID pinzolo. |  |
| `destination:pinzolo` | `ski_areas[0]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"pinzolo-ski-area"` | The linked Pinzolo - Official Ski Area supports the reviewed ski_areas[0] leaf. |  |  |
| `destination:pinzolo` | `stay_bases[0]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"pinzolo-pinzolo"` | The linked Pinzolo - Official Ski Area supports the reviewed stay_bases[0] leaf. |  |  |
| `destination:pinzolo` | `summit_elevation_m` | [Bergfex - Pinzolo](https://www.bergfex.it/pinzolo/) | `2100` | The linked Bergfex - Pinzolo supports the reviewed summit_elevation_m leaf. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `external_validity_summary` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Pejo"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed external_validity_summary leaf. | Disconnected Pejo coverage is retained as external pass context, not terrain-domain membership. |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `is_default` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed is_default leaf. | Product selection policy normalized to is_default=True. |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `lift_pass_product_id` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed lift_pass_product_id leaf. | The official product name is normalized to stable ID folgarida-marilleva-campiglio-skiarea-pass. |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `name` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed name leaf. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].amount` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `85` | The official tariff supports prices[0].amount, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].audience` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"adult"` | The official tariff supports prices[0].audience, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].currency` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"EUR"` | The official tariff supports prices[0].currency, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].duration_days` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `1` | The official tariff supports prices[0].duration_days, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].price_kind` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"fixed"` | The official tariff supports prices[0].price_kind, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].season_label` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"high season 2025/26"` | The official tariff supports prices[0].season_label, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[0].source_url` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | The official tariff supports prices[0].source_url, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].amount` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `237` | The official tariff supports prices[1].amount, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].audience` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"adult"` | The official tariff supports prices[1].audience, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].currency` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"EUR"` | The official tariff supports prices[1].currency, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].duration_days` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `3` | The official tariff supports prices[1].duration_days, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].price_kind` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"fixed"` | The official tariff supports prices[1].price_kind, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].season_label` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"high season 2025/26"` | The official tariff supports prices[1].season_label, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[1].source_url` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | The official tariff supports prices[1].source_url, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].amount` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `424` | The official tariff supports prices[2].amount, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].audience` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"adult"` | The official tariff supports prices[2].audience, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].currency` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"EUR"` | The official tariff supports prices[2].currency, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].duration_days` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `6` | The official tariff supports prices[2].duration_days, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].price_kind` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"fixed"` | The official tariff supports prices[2].price_kind, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].season_label` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"high season 2025/26"` | The official tariff supports prices[2].season_label, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `prices[2].source_url` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | The official tariff supports prices[2].source_url, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `terrain_domain_ids[0]` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"campiglio-dolomiti-di-brenta"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed terrain_domain_ids[0] leaf. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `valid_ski_area_ids[0]` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"folgarida-marilleva-ski-area"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed valid_ski_area_ids[0] leaf. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass` | `validity_scope` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed validity_scope leaf. | Official product scope normalized to regional_network. |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `is_default` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"Folgarida Marilleva Skipass"` | The linked 2025/26 Folgarida Marilleva Tariff PDF supports the reviewed is_default leaf. | Product selection policy normalized to is_default=False. |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `lift_pass_product_id` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"Folgarida Marilleva Skipass"` | The linked 2025/26 Folgarida Marilleva Tariff PDF supports the reviewed lift_pass_product_id leaf. | The official product name is normalized to stable ID folgarida-marilleva-local-pass. |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `name` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"Folgarida Marilleva Skipass"` | The linked 2025/26 Folgarida Marilleva Tariff PDF supports the reviewed name leaf. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].amount` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `67` | The official tariff supports prices[0].amount, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].audience` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"adult"` | The official tariff supports prices[0].audience, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].currency` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"EUR"` | The official tariff supports prices[0].currency, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].duration_days` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `1` | The official tariff supports prices[0].duration_days, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].price_kind` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"fixed"` | The official tariff supports prices[0].price_kind, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].season_label` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"high season 2025/26"` | The official tariff supports prices[0].season_label, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[0].source_url` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf"` | The official tariff supports prices[0].source_url, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].amount` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `189` | The official tariff supports prices[1].amount, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].audience` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"adult"` | The official tariff supports prices[1].audience, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].currency` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"EUR"` | The official tariff supports prices[1].currency, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].duration_days` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `3` | The official tariff supports prices[1].duration_days, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].price_kind` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"fixed"` | The official tariff supports prices[1].price_kind, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].season_label` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"high season 2025/26"` | The official tariff supports prices[1].season_label, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[1].source_url` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf"` | The official tariff supports prices[1].source_url, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].amount` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `339` | The official tariff supports prices[2].amount, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].audience` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"adult"` | The official tariff supports prices[2].audience, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].currency` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"EUR"` | The official tariff supports prices[2].currency, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].duration_days` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `6` | The official tariff supports prices[2].duration_days, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].price_kind` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"fixed"` | The official tariff supports prices[2].price_kind, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].season_label` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"high season 2025/26"` | The official tariff supports prices[2].season_label, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `prices[2].source_url` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf"` | The official tariff supports prices[2].source_url, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `terrain_domain_ids` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"Folgarida Marilleva Skipass"` | The linked 2025/26 Folgarida Marilleva Tariff PDF supports the reviewed terrain_domain_ids leaf. | Local-only coverage normalized to no terrain-domain references. |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `valid_ski_area_ids[0]` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"folgarida-marilleva-ski-area"` | The linked 2025/26 Folgarida Marilleva Tariff PDF supports the reviewed valid_ski_area_ids[0] leaf. |  |  |
| `lift_pass_product:folgarida-marilleva:folgarida-marilleva-local-pass` | `validity_scope` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"Folgarida Marilleva Skipass"` | The linked 2025/26 Folgarida Marilleva Tariff PDF supports the reviewed validity_scope leaf. | Official product scope normalized to single_ski_area. |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `external_validity_summary` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Pejo"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed external_validity_summary leaf. | Disconnected Pejo coverage is retained as external pass context, not terrain-domain membership. |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `is_default` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed is_default leaf. | Product selection policy normalized to is_default=True. |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `lift_pass_product_id` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed lift_pass_product_id leaf. | The official product name is normalized to stable ID madonna-di-campiglio-campiglio-skiarea-pass. |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `name` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed name leaf. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].amount` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `85` | The official tariff supports prices[0].amount, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].audience` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"adult"` | The official tariff supports prices[0].audience, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].currency` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"EUR"` | The official tariff supports prices[0].currency, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].duration_days` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `1` | The official tariff supports prices[0].duration_days, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].price_kind` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"fixed"` | The official tariff supports prices[0].price_kind, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].season_label` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"high season 2025/26"` | The official tariff supports prices[0].season_label, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[0].source_url` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | The official tariff supports prices[0].source_url, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].amount` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `237` | The official tariff supports prices[1].amount, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].audience` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"adult"` | The official tariff supports prices[1].audience, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].currency` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"EUR"` | The official tariff supports prices[1].currency, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].duration_days` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `3` | The official tariff supports prices[1].duration_days, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].price_kind` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"fixed"` | The official tariff supports prices[1].price_kind, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].season_label` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"high season 2025/26"` | The official tariff supports prices[1].season_label, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[1].source_url` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | The official tariff supports prices[1].source_url, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].amount` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `424` | The official tariff supports prices[2].amount, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].audience` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"adult"` | The official tariff supports prices[2].audience, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].currency` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"EUR"` | The official tariff supports prices[2].currency, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].duration_days` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `6` | The official tariff supports prices[2].duration_days, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].price_kind` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"fixed"` | The official tariff supports prices[2].price_kind, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].season_label` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"high season 2025/26"` | The official tariff supports prices[2].season_label, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `prices[2].source_url` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | The official tariff supports prices[2].source_url, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `terrain_domain_ids[0]` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"campiglio-dolomiti-di-brenta"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed terrain_domain_ids[0] leaf. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `valid_ski_area_ids[0]` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"madonna-di-campiglio-ski-area"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed valid_ski_area_ids[0] leaf. |  |  |
| `lift_pass_product:madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass` | `validity_scope` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed validity_scope leaf. | Official product scope normalized to regional_network. |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `external_validity_summary` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Pejo"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed external_validity_summary leaf. | Disconnected Pejo coverage is retained as external pass context, not terrain-domain membership. |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `is_default` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed is_default leaf. | Product selection policy normalized to is_default=True. |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `lift_pass_product_id` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed lift_pass_product_id leaf. | The official product name is normalized to stable ID pinzolo-campiglio-skiarea-pass. |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `name` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed name leaf. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].amount` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `85` | The official tariff supports prices[0].amount, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].audience` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"adult"` | The official tariff supports prices[0].audience, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].currency` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"EUR"` | The official tariff supports prices[0].currency, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].duration_days` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `1` | The official tariff supports prices[0].duration_days, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].price_kind` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"fixed"` | The official tariff supports prices[0].price_kind, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].season_label` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"high season 2025/26"` | The official tariff supports prices[0].season_label, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[0].source_url` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | The official tariff supports prices[0].source_url, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].amount` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `237` | The official tariff supports prices[1].amount, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].audience` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"adult"` | The official tariff supports prices[1].audience, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].currency` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"EUR"` | The official tariff supports prices[1].currency, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].duration_days` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `3` | The official tariff supports prices[1].duration_days, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].price_kind` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"fixed"` | The official tariff supports prices[1].price_kind, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].season_label` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"high season 2025/26"` | The official tariff supports prices[1].season_label, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[1].source_url` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | The official tariff supports prices[1].source_url, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].amount` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `424` | The official tariff supports prices[2].amount, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].audience` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"adult"` | The official tariff supports prices[2].audience, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].currency` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"EUR"` | The official tariff supports prices[2].currency, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].duration_days` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `6` | The official tariff supports prices[2].duration_days, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].price_kind` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"fixed"` | The official tariff supports prices[2].price_kind, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].season_label` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"high season 2025/26"` | The official tariff supports prices[2].season_label, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `prices[2].source_url` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | The official tariff supports prices[2].source_url, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `terrain_domain_ids[0]` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"campiglio-dolomiti-di-brenta"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed terrain_domain_ids[0] leaf. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `valid_ski_area_ids[0]` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"pinzolo-ski-area"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed valid_ski_area_ids[0] leaf. |  |  |
| `lift_pass_product:pinzolo:pinzolo-campiglio-skiarea-pass` | `validity_scope` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"Campiglio Dolomiti di Brenta Skiarea Skipass"` | The linked Campiglio Dolomiti di Brenta Skiarea Skipass supports the reviewed validity_scope leaf. | Official product scope normalized to regional_network. |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `is_default` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"Pinzolo Skipass"` | The linked 2025/26 Pinzolo Tariff PDF supports the reviewed is_default leaf. | Product selection policy normalized to is_default=False. |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `lift_pass_product_id` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"Pinzolo Skipass"` | The linked 2025/26 Pinzolo Tariff PDF supports the reviewed lift_pass_product_id leaf. | The official product name is normalized to stable ID pinzolo-local-pass. |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `name` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"Pinzolo Skipass"` | The linked 2025/26 Pinzolo Tariff PDF supports the reviewed name leaf. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].amount` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `65` | The official tariff supports prices[0].amount, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].audience` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"adult"` | The official tariff supports prices[0].audience, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].currency` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"EUR"` | The official tariff supports prices[0].currency, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].duration_days` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `1` | The official tariff supports prices[0].duration_days, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].price_kind` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"fixed"` | The official tariff supports prices[0].price_kind, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].season_label` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"high season 2025/26"` | The official tariff supports prices[0].season_label, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[0].source_url` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf"` | The official tariff supports prices[0].source_url, the exact leaf for representative price example 1. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].amount` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `180` | The official tariff supports prices[1].amount, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].audience` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"adult"` | The official tariff supports prices[1].audience, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].currency` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"EUR"` | The official tariff supports prices[1].currency, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].duration_days` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `3` | The official tariff supports prices[1].duration_days, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].price_kind` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"fixed"` | The official tariff supports prices[1].price_kind, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].season_label` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"high season 2025/26"` | The official tariff supports prices[1].season_label, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[1].source_url` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf"` | The official tariff supports prices[1].source_url, the exact leaf for representative price example 2. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].amount` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `315` | The official tariff supports prices[2].amount, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].audience` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"adult"` | The official tariff supports prices[2].audience, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].currency` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"EUR"` | The official tariff supports prices[2].currency, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].duration_days` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `6` | The official tariff supports prices[2].duration_days, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].price_kind` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"fixed"` | The official tariff supports prices[2].price_kind, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].season_label` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"high season 2025/26"` | The official tariff supports prices[2].season_label, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `prices[2].source_url` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf"` | The official tariff supports prices[2].source_url, the exact leaf for representative price example 3. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `terrain_domain_ids` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"Pinzolo Skipass"` | The linked 2025/26 Pinzolo Tariff PDF supports the reviewed terrain_domain_ids leaf. | Local-only coverage normalized to no terrain-domain references. |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `valid_ski_area_ids[0]` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"pinzolo-ski-area"` | The linked 2025/26 Pinzolo Tariff PDF supports the reviewed valid_ski_area_ids[0] leaf. |  |  |
| `lift_pass_product:pinzolo:pinzolo-local-pass` | `validity_scope` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"Pinzolo Skipass"` | The linked 2025/26 Pinzolo Tariff PDF supports the reviewed validity_scope leaf. | Official product scope normalized to single_ski_area. |  |
| `rental:folgarida-marilleva:ski-point` | `name` | [Folgarida Marilleva - Ski Point](https://www.ski.it/it/noleggi/folgarida/ski-point) | `"Ski Point"` | The linked Folgarida Marilleva - Ski Point supports the reviewed name leaf. |  |  |
| `rental:madonna-di-campiglio:campiglio-ski-rent-lorenzetti` | `name` | [Campiglio Dolomiti - Ski Rentals](https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals) | `"Campiglio Ski Rent - Lorenzetti"` | The linked Campiglio Dolomiti - Ski Rentals supports the reviewed name leaf. |  |  |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `lift_distance` | [Campiglio Dolomiti - Ski Rentals](https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals) | `"Campiglio Ski Rent - Lorenzetti"` | The linked Campiglio Dolomiti - Ski Rentals supports the reviewed lift_distance leaf. | The official provider identity replaces the superseded Ski Rent Campiglio seed record; reconciliation represents the rename as removal and addition targets. |  |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `name` | [Campiglio Dolomiti - Ski Rentals](https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals) | `"Campiglio Ski Rent - Lorenzetti"` | The linked Campiglio Dolomiti - Ski Rentals supports the reviewed name leaf. | The official provider identity replaces the superseded Ski Rent Campiglio seed record; reconciliation represents the rename as removal and addition targets. |  |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `price_max` | [Campiglio Dolomiti - Ski Rentals](https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals) | `"Campiglio Ski Rent - Lorenzetti"` | The linked Campiglio Dolomiti - Ski Rentals supports the reviewed price_max leaf. | The official provider identity replaces the superseded Ski Rent Campiglio seed record; reconciliation represents the rename as removal and addition targets. |  |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `price_min` | [Campiglio Dolomiti - Ski Rentals](https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals) | `"Campiglio Ski Rent - Lorenzetti"` | The linked Campiglio Dolomiti - Ski Rentals supports the reviewed price_min leaf. | The official provider identity replaces the superseded Ski Rent Campiglio seed record; reconciliation represents the rename as removal and addition targets. |  |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `price_range` | [Campiglio Dolomiti - Ski Rentals](https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals) | `"Campiglio Ski Rent - Lorenzetti"` | The linked Campiglio Dolomiti - Ski Rentals supports the reviewed price_range leaf. | The official provider identity replaces the superseded Ski Rent Campiglio seed record; reconciliation represents the rename as removal and addition targets. |  |
| `rental:madonna-di-campiglio:ski-rent-campiglio` | `quality` | [Campiglio Dolomiti - Ski Rentals](https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals) | `"Campiglio Ski Rent - Lorenzetti"` | The linked Campiglio Dolomiti - Ski Rentals supports the reviewed quality leaf. | The official provider identity replaces the superseded Ski Rent Campiglio seed record; reconciliation represents the rename as removal and addition targets. |  |
| `rental:pinzolo:il-comodo-sci` | `name` | [Campiglio Dolomiti - Il Comodo Sci](https://www.campigliodolomiti.it/en/services/il-comodo-sci) | `"Il Comodo Sci"` | The linked Campiglio Dolomiti - Il Comodo Sci supports the reviewed name leaf. |  |  |
| `ski_area:folgarida-marilleva-ski-area` | `base_elevation_m` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `1300` | The linked Campiglio Dolomiti di Brenta Official Ski Map supports the reviewed base_elevation_m leaf. |  |  |
| `ski_area:folgarida-marilleva-ski-area` | `latitude` | [OpenStreetMap node 327580361 - Folgarida place node](https://www.openstreetmap.org/node/327580361) | `46.3030712` | The exact OSM object supplies the reviewed latitude leaf. |  |  |
| `ski_area:folgarida-marilleva-ski-area` | `longitude` | [OpenStreetMap node 327580361 - Folgarida place node](https://www.openstreetmap.org/node/327580361) | `10.8656079` | The exact OSM object supplies the reviewed longitude leaf. |  |  |
| `ski_area:folgarida-marilleva-ski-area` | `name` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"Folgarida-Marilleva"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed name leaf. |  |  |
| `ski_area:folgarida-marilleva-ski-area` | `ski_area_id` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"Folgarida-Marilleva"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed ski_area_id leaf. | The official name is normalized to stable catalog ID folgarida-marilleva-ski-area. |  |
| `ski_area:folgarida-marilleva-ski-area` | `summit_elevation_m` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `2180` | The linked Campiglio Dolomiti di Brenta Official Ski Map supports the reviewed summit_elevation_m leaf. |  |  |
| `ski_area:folgarida-marilleva-ski-area` | `total_piste_km` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `62` | The linked Campiglio Dolomiti di Brenta Official Ski Map supports the reviewed total_piste_km leaf. |  |  |
| `ski_area:madonna-di-campiglio-ski-area` | `season_start_month` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `11` | The linked Madonna di Campiglio - Official Ski Area supports the reviewed season_start_month leaf. |  |  |
| `ski_area:madonna-di-campiglio-ski-area` | `total_piste_km` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `62` | The linked Campiglio Dolomiti di Brenta Official Ski Map supports the reviewed total_piste_km leaf. |  |  |
| `ski_area:pinzolo-ski-area` | `base_elevation_m` | [Bergfex - Pinzolo](https://www.bergfex.it/pinzolo/) | `800` | The linked Bergfex - Pinzolo supports the reviewed base_elevation_m leaf. |  |  |
| `ski_area:pinzolo-ski-area` | `latitude` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `46.1617322` | The exact OSM object supplies the reviewed latitude leaf. |  |  |
| `ski_area:pinzolo-ski-area` | `longitude` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `10.7650043` | The exact OSM object supplies the reviewed longitude leaf. |  |  |
| `ski_area:pinzolo-ski-area` | `name` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"Pinzolo"` | The linked Pinzolo - Official Ski Area supports the reviewed name leaf. |  |  |
| `ski_area:pinzolo-ski-area` | `ski_area_id` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"Pinzolo"` | The linked Pinzolo - Official Ski Area supports the reviewed ski_area_id leaf. | The official name is normalized to stable catalog ID pinzolo-ski-area. |  |
| `ski_area:pinzolo-ski-area` | `summit_elevation_m` | [Bergfex - Pinzolo](https://www.bergfex.it/pinzolo/) | `2100` | The linked Bergfex - Pinzolo supports the reviewed summit_elevation_m leaf. |  |  |
| `ski_area:pinzolo-ski-area` | `total_piste_km` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `31` | The linked Pinzolo - Official Ski Area supports the reviewed total_piste_km leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `access_mode` | [OpenStreetMap node 1096349433 - Daolasa](https://www.openstreetmap.org/node/1096349433) | `"walk"` | The linked OpenStreetMap node 1096349433 - Daolasa supports the reviewed access_mode leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `base_type` | [OpenStreetMap node 6043719130 - Daolasa](https://www.openstreetmap.org/node/6043719130) | `"Daolasa"` | The linked OpenStreetMap node 6043719130 - Daolasa supports the reviewed base_type leaf. | OSM place context normalized to stay-base type resort_station. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `latitude` | [OpenStreetMap node 6043719130 - Daolasa](https://www.openstreetmap.org/node/6043719130) | `46.3195236` | The exact OSM object supplies the reviewed latitude leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `lift_distance` | [OpenStreetMap node 1096349433 - Daolasa](https://www.openstreetmap.org/node/1096349433) | `"near"` | The linked OpenStreetMap node 1096349433 - Daolasa supports the reviewed lift_distance leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `longitude` | [OpenStreetMap node 6043719130 - Daolasa](https://www.openstreetmap.org/node/6043719130) | `10.8398851` | The exact OSM object supplies the reviewed longitude leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `name` | [OpenStreetMap node 6043719130 - Daolasa](https://www.openstreetmap.org/node/6043719130) | `"Daolasa"` | The linked OpenStreetMap node 6043719130 - Daolasa supports the reviewed name leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `nearest_lift_distance_m` | [OpenStreetMap node 1096349433 - Daolasa](https://www.openstreetmap.org/node/1096349433) | `285` | This exact distance leaf is derived from the reviewed stay-base and lift OSM point pair; the linked lift object is the most directly relevant source. | Integer metres are calculated with Haversine distance from the reviewed stay-base point to the reviewed lift point; both OSM objects are retained in the manifest source set. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `nearest_lift_name` | [OpenStreetMap node 1096349433 - Daolasa](https://www.openstreetmap.org/node/1096349433) | `"Daolasa"` | The linked OpenStreetMap node 1096349433 - Daolasa supports the reviewed nearest_lift_name leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `regional_data_ids.nearest_lift_osm_node_id` | [OpenStreetMap node 6043719130 - Daolasa](https://www.openstreetmap.org/node/6043719130) | `"1096349433"` | The linked OSM object matches the exact ID stored in regional_data_ids.nearest_lift_osm_node_id. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `regional_data_ids.osm_node_id` | [OpenStreetMap node 6043719130 - Daolasa](https://www.openstreetmap.org/node/6043719130) | `"6043719130"` | The linked OSM object matches the exact ID stored in regional_data_ids.osm_node_id. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-daolasa` | `stay_base_id` | [OpenStreetMap node 6043719130 - Daolasa](https://www.openstreetmap.org/node/6043719130) | `"Daolasa"` | The linked OpenStreetMap node 6043719130 - Daolasa supports the reviewed stay_base_id leaf. | The OSM place name is normalized to stay-base ID folgarida-marilleva-daolasa. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `access_mode` | [OpenStreetMap node 648469713 - Folgarida](https://www.openstreetmap.org/node/648469713) | `"walk"` | The linked OpenStreetMap node 648469713 - Folgarida supports the reviewed access_mode leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `atmosphere_tags[0]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"family-friendly"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed atmosphere_tags[0] leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `atmosphere_tags[1]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"scenic"` | The linked Folgarida-Marilleva - Official Ski Area supports the reviewed atmosphere_tags[1] leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `base_type` | [OpenStreetMap node 327580361 - Folgarida](https://www.openstreetmap.org/node/327580361) | `"Folgarida"` | The linked OpenStreetMap node 327580361 - Folgarida supports the reviewed base_type leaf. | OSM place context normalized to stay-base type resort_station. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `latitude` | [OpenStreetMap node 327580361 - Folgarida](https://www.openstreetmap.org/node/327580361) | `46.3030712` | The exact OSM object supplies the reviewed latitude leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `lift_distance` | [OpenStreetMap node 648469713 - Folgarida](https://www.openstreetmap.org/node/648469713) | `"near"` | The linked OpenStreetMap node 648469713 - Folgarida supports the reviewed lift_distance leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `longitude` | [OpenStreetMap node 327580361 - Folgarida](https://www.openstreetmap.org/node/327580361) | `10.8656079` | The exact OSM object supplies the reviewed longitude leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `name` | [OpenStreetMap node 327580361 - Folgarida](https://www.openstreetmap.org/node/327580361) | `"Folgarida"` | The linked OpenStreetMap node 327580361 - Folgarida supports the reviewed name leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `nearest_lift_distance_m` | [OpenStreetMap node 648469713 - Folgarida](https://www.openstreetmap.org/node/648469713) | `516` | This exact distance leaf is derived from the reviewed stay-base and lift OSM point pair; the linked lift object is the most directly relevant source. | Integer metres are calculated with Haversine distance from the reviewed stay-base point to the reviewed lift point; both OSM objects are retained in the manifest source set. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `nearest_lift_name` | [OpenStreetMap node 648469713 - Folgarida](https://www.openstreetmap.org/node/648469713) | `"Folgarida"` | The linked OpenStreetMap node 648469713 - Folgarida supports the reviewed nearest_lift_name leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `regional_data_ids.nearest_lift_osm_node_id` | [OpenStreetMap node 327580361 - Folgarida](https://www.openstreetmap.org/node/327580361) | `"648469713"` | The linked OSM object matches the exact ID stored in regional_data_ids.nearest_lift_osm_node_id. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `regional_data_ids.osm_node_id` | [OpenStreetMap node 327580361 - Folgarida](https://www.openstreetmap.org/node/327580361) | `"327580361"` | The linked OSM object matches the exact ID stored in regional_data_ids.osm_node_id. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-folgarida` | `stay_base_id` | [OpenStreetMap node 327580361 - Folgarida](https://www.openstreetmap.org/node/327580361) | `"Folgarida"` | The linked OpenStreetMap node 327580361 - Folgarida supports the reviewed stay_base_id leaf. | The OSM place name is normalized to stay-base ID folgarida-marilleva-folgarida. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `access_mode` | [OpenStreetMap node 1096349822 - Marilleva](https://www.openstreetmap.org/node/1096349822) | `"walk"` | The linked OpenStreetMap node 1096349822 - Marilleva supports the reviewed access_mode leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `base_type` | [OpenStreetMap node 331259364 - Marilleva 1400](https://www.openstreetmap.org/node/331259364) | `"Marilleva 1400"` | The linked OpenStreetMap node 331259364 - Marilleva 1400 supports the reviewed base_type leaf. | OSM place context normalized to stay-base type resort_station. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `latitude` | [OpenStreetMap node 331259364 - Marilleva 1400](https://www.openstreetmap.org/node/331259364) | `46.3024327` | The exact OSM object supplies the reviewed latitude leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `lift_distance` | [OpenStreetMap node 1096349822 - Marilleva](https://www.openstreetmap.org/node/1096349822) | `"near"` | The linked OpenStreetMap node 1096349822 - Marilleva supports the reviewed lift_distance leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `longitude` | [OpenStreetMap node 331259364 - Marilleva 1400](https://www.openstreetmap.org/node/331259364) | `10.8101466` | The exact OSM object supplies the reviewed longitude leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `name` | [OpenStreetMap node 331259364 - Marilleva 1400](https://www.openstreetmap.org/node/331259364) | `"Marilleva 1400"` | The linked OpenStreetMap node 331259364 - Marilleva 1400 supports the reviewed name leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `nearest_lift_distance_m` | [OpenStreetMap node 1096349822 - Marilleva](https://www.openstreetmap.org/node/1096349822) | `172` | This exact distance leaf is derived from the reviewed stay-base and lift OSM point pair; the linked lift object is the most directly relevant source. | Integer metres are calculated with Haversine distance from the reviewed stay-base point to the reviewed lift point; both OSM objects are retained in the manifest source set. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `nearest_lift_name` | [OpenStreetMap node 1096349822 - Marilleva](https://www.openstreetmap.org/node/1096349822) | `"Marilleva"` | The linked OpenStreetMap node 1096349822 - Marilleva supports the reviewed nearest_lift_name leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `regional_data_ids.nearest_lift_osm_node_id` | [OpenStreetMap node 331259364 - Marilleva 1400](https://www.openstreetmap.org/node/331259364) | `"1096349822"` | The linked OSM object matches the exact ID stored in regional_data_ids.nearest_lift_osm_node_id. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `regional_data_ids.osm_node_id` | [OpenStreetMap node 331259364 - Marilleva 1400](https://www.openstreetmap.org/node/331259364) | `"331259364"` | The linked OSM object matches the exact ID stored in regional_data_ids.osm_node_id. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-1400` | `stay_base_id` | [OpenStreetMap node 331259364 - Marilleva 1400](https://www.openstreetmap.org/node/331259364) | `"Marilleva 1400"` | The linked OpenStreetMap node 331259364 - Marilleva 1400 supports the reviewed stay_base_id leaf. | The OSM place name is normalized to stay-base ID folgarida-marilleva-marilleva-1400. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `access_mode` | [OpenStreetMap node 8662539441 - Contrè](https://www.openstreetmap.org/node/8662539441) | `"walk"` | The linked OpenStreetMap node 8662539441 - Contrè supports the reviewed access_mode leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `base_type` | [OpenStreetMap node 331259493 - Marilleva 900](https://www.openstreetmap.org/node/331259493) | `"Marilleva 900"` | The linked OpenStreetMap node 331259493 - Marilleva 900 supports the reviewed base_type leaf. | OSM place context normalized to stay-base type resort_station. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `latitude` | [OpenStreetMap node 331259493 - Marilleva 900](https://www.openstreetmap.org/node/331259493) | `46.3144534` | The exact OSM object supplies the reviewed latitude leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `lift_distance` | [OpenStreetMap node 8662539441 - Contrè](https://www.openstreetmap.org/node/8662539441) | `"near"` | The linked OpenStreetMap node 8662539441 - Contrè supports the reviewed lift_distance leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `longitude` | [OpenStreetMap node 331259493 - Marilleva 900](https://www.openstreetmap.org/node/331259493) | `10.8127255` | The exact OSM object supplies the reviewed longitude leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `name` | [OpenStreetMap node 331259493 - Marilleva 900](https://www.openstreetmap.org/node/331259493) | `"Marilleva 900"` | The linked OpenStreetMap node 331259493 - Marilleva 900 supports the reviewed name leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `nearest_lift_distance_m` | [OpenStreetMap node 8662539441 - Contrè](https://www.openstreetmap.org/node/8662539441) | `47` | This exact distance leaf is derived from the reviewed stay-base and lift OSM point pair; the linked lift object is the most directly relevant source. | Integer metres are calculated with Haversine distance from the reviewed stay-base point to the reviewed lift point; both OSM objects are retained in the manifest source set. |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `nearest_lift_name` | [OpenStreetMap node 8662539441 - Contrè](https://www.openstreetmap.org/node/8662539441) | `"Contrè"` | The linked OpenStreetMap node 8662539441 - Contrè supports the reviewed nearest_lift_name leaf. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `regional_data_ids.nearest_lift_osm_node_id` | [OpenStreetMap node 331259493 - Marilleva 900](https://www.openstreetmap.org/node/331259493) | `"8662539441"` | The linked OSM object matches the exact ID stored in regional_data_ids.nearest_lift_osm_node_id. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `regional_data_ids.osm_node_id` | [OpenStreetMap node 331259493 - Marilleva 900](https://www.openstreetmap.org/node/331259493) | `"331259493"` | The linked OSM object matches the exact ID stored in regional_data_ids.osm_node_id. |  |  |
| `stay_base:folgarida-marilleva:folgarida-marilleva-marilleva-900` | `stay_base_id` | [OpenStreetMap node 331259493 - Marilleva 900](https://www.openstreetmap.org/node/331259493) | `"Marilleva 900"` | The linked OpenStreetMap node 331259493 - Marilleva 900 supports the reviewed stay_base_id leaf. | The OSM place name is normalized to stay-base ID folgarida-marilleva-marilleva-900. |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `access_mode` | [OpenStreetMap node 1023438277 - Spinale Express](https://www.openstreetmap.org/node/1023438277) | `"walk"` | The linked OpenStreetMap node 1023438277 - Spinale Express supports the reviewed access_mode leaf. |  |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags[0]` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `"family-friendly"` | The linked Madonna di Campiglio - Official Ski Area supports the reviewed atmosphere_tags[0] leaf. |  |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags[1]` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `"premium"` | The linked Madonna di Campiglio - Official Ski Area supports the reviewed atmosphere_tags[1] leaf. |  |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `atmosphere_tags[2]` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `"scenic"` | The linked Madonna di Campiglio - Official Ski Area supports the reviewed atmosphere_tags[2] leaf. |  |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `base_type` | [OpenStreetMap node 1796357582 - Madonna di Campiglio](https://www.openstreetmap.org/node/1796357582) | `"Madonna di Campiglio"` | The linked OpenStreetMap node 1796357582 - Madonna di Campiglio supports the reviewed base_type leaf. | OSM place context normalized to stay-base type town. |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `latitude` | [OpenStreetMap node 1796357582 - Madonna di Campiglio](https://www.openstreetmap.org/node/1796357582) | `46.2269942` | The exact OSM object supplies the reviewed latitude leaf. |  |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `longitude` | [OpenStreetMap node 1796357582 - Madonna di Campiglio](https://www.openstreetmap.org/node/1796357582) | `10.8270157` | The exact OSM object supplies the reviewed longitude leaf. |  |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_distance_m` | [OpenStreetMap node 1023438277 - Spinale Express](https://www.openstreetmap.org/node/1023438277) | `243` | This exact distance leaf is derived from the reviewed stay-base and lift OSM point pair; the linked lift object is the most directly relevant source. | Integer metres are calculated with Haversine distance from the reviewed stay-base point to the reviewed lift point; both OSM objects are retained in the manifest source set. |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `nearest_lift_name` | [OpenStreetMap node 1023438277 - Spinale Express](https://www.openstreetmap.org/node/1023438277) | `"Spinale express"` | The linked OpenStreetMap node 1023438277 - Spinale Express supports the reviewed nearest_lift_name leaf. | OSM capitalization normalized to Spinale Express. |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `regional_data_ids.nearest_lift_osm_node_id` | [OpenStreetMap node 1796357582 - Madonna di Campiglio](https://www.openstreetmap.org/node/1796357582) | `"1023438277"` | The linked OSM object matches the exact ID stored in regional_data_ids.nearest_lift_osm_node_id. |  |  |
| `stay_base:madonna-di-campiglio:madonna-di-campiglio-madonna-di-campiglio` | `regional_data_ids.osm_node_id` | [OpenStreetMap node 1796357582 - Madonna di Campiglio](https://www.openstreetmap.org/node/1796357582) | `"1796357582"` | The linked OSM object matches the exact ID stored in regional_data_ids.osm_node_id. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `access_mode` | [OpenStreetMap node 298987790 - Funivia Pinzolo - Pra Rodont](https://www.openstreetmap.org/node/298987790) | `"walk"` | The linked OpenStreetMap node 298987790 - Funivia Pinzolo - Pra Rodont supports the reviewed access_mode leaf. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `atmosphere_tags[0]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"family-friendly"` | The linked Pinzolo - Official Ski Area supports the reviewed atmosphere_tags[0] leaf. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `atmosphere_tags[1]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"quiet"` | The linked Pinzolo - Official Ski Area supports the reviewed atmosphere_tags[1] leaf. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `atmosphere_tags[2]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"scenic"` | The linked Pinzolo - Official Ski Area supports the reviewed atmosphere_tags[2] leaf. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `base_type` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `"Pinzolo"` | The linked OpenStreetMap node 4311362989 - Pinzolo supports the reviewed base_type leaf. | OSM place context normalized to stay-base type town. |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `latitude` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `46.1617322` | The exact OSM object supplies the reviewed latitude leaf. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `lift_distance` | [OpenStreetMap node 298987790 - Funivia Pinzolo - Pra Rodont](https://www.openstreetmap.org/node/298987790) | `"near"` | The linked OpenStreetMap node 298987790 - Funivia Pinzolo - Pra Rodont supports the reviewed lift_distance leaf. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `longitude` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `10.7650043` | The exact OSM object supplies the reviewed longitude leaf. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `name` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `"Pinzolo"` | The linked OpenStreetMap node 4311362989 - Pinzolo supports the reviewed name leaf. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `nearest_lift_distance_m` | [OpenStreetMap node 298987790 - Funivia Pinzolo - Pra Rodont](https://www.openstreetmap.org/node/298987790) | `206` | This exact distance leaf is derived from the reviewed stay-base and lift OSM point pair; the linked lift object is the most directly relevant source. | Integer metres are calculated with Haversine distance from the reviewed stay-base point to the reviewed lift point; both OSM objects are retained in the manifest source set. |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `nearest_lift_name` | [OpenStreetMap node 298987790 - Funivia Pinzolo - Pra Rodont](https://www.openstreetmap.org/node/298987790) | `"Funivia Pinzolo - Pra Rodont"` | The linked OpenStreetMap node 298987790 - Funivia Pinzolo - Pra Rodont supports the reviewed nearest_lift_name leaf. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `regional_data_ids.nearest_lift_osm_node_id` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `"298987790"` | The linked OSM object matches the exact ID stored in regional_data_ids.nearest_lift_osm_node_id. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `regional_data_ids.osm_node_id` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `"4311362989"` | The linked OSM object matches the exact ID stored in regional_data_ids.osm_node_id. |  |  |
| `stay_base:pinzolo:pinzolo-pinzolo` | `stay_base_id` | [OpenStreetMap node 4311362989 - Pinzolo](https://www.openstreetmap.org/node/4311362989) | `"Pinzolo"` | The linked OpenStreetMap node 4311362989 - Pinzolo supports the reviewed stay_base_id leaf. | The OSM place name is normalized to stay-base ID pinzolo-pinzolo. |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `metric_scope` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"domain-wide ski area"` | The linked Campiglio Dolomiti - Ski Area supports the reviewed metric_scope leaf. | The domain-wide source scope is normalized to metric_scope=aggregate. |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `name` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"Campiglio Dolomiti di Brenta"` | The linked Campiglio Dolomiti - Ski Area supports the reviewed name leaf. |  |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[0].resort_id` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"Madonna di Campiglio"` | The linked Campiglio Dolomiti - Ski Area supports the reviewed ski_area_refs[0].resort_id leaf. | Official place labels are normalized to exact catalog resort and ski-area references; Pejo is intentionally excluded. |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[0].ski_area_id` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"Madonna di Campiglio"` | The linked Campiglio Dolomiti - Ski Area supports the reviewed ski_area_refs[0].ski_area_id leaf. | Official place labels are normalized to exact catalog resort and ski-area references; Pejo is intentionally excluded. |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[1].resort_id` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"Pinzolo"` | The linked Campiglio Dolomiti - Ski Area supports the reviewed ski_area_refs[1].resort_id leaf. | Official place labels are normalized to exact catalog resort and ski-area references; Pejo is intentionally excluded. |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[1].ski_area_id` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"Pinzolo"` | The linked Campiglio Dolomiti - Ski Area supports the reviewed ski_area_refs[1].ski_area_id leaf. | Official place labels are normalized to exact catalog resort and ski-area references; Pejo is intentionally excluded. |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[2].resort_id` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"Folgarida-Marilleva"` | The linked Campiglio Dolomiti - Ski Area supports the reviewed ski_area_refs[2].resort_id leaf. | Official place labels are normalized to exact catalog resort and ski-area references; Pejo is intentionally excluded. |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `ski_area_refs[2].ski_area_id` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"Folgarida-Marilleva"` | The linked Campiglio Dolomiti - Ski Area supports the reviewed ski_area_refs[2].ski_area_id leaf. | Official place labels are normalized to exact catalog resort and ski-area references; Pejo is intentionally excluded. |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `source_urls[0]` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"https://www.campigliodolomiti.it/en/ski-area"` | The linked URL is the exact reviewed source_urls[0] leaf. |  |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `source_urls[1]` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `"https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf"` | The linked URL is the exact reviewed source_urls[1] leaf. |  |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `terrain_domain_id` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"Campiglio Dolomiti di Brenta"` | The linked Campiglio Dolomiti - Ski Area supports the reviewed terrain_domain_id leaf. | The official domain name is normalized to catalog ID campiglio-dolomiti-di-brenta. |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `total_piste_km` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `156` | The tourism source says 156 km while the official map says 155 km; 156 km is accepted as the canonical tourism-domain value and is not sum-derived. |  |  |
| `terrain_domain:matterhorn-ski-paradise` | `source_urls[2]` | [Matterhorn Paradise - Zermatt Matterhorn Region](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `"https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn"` | The linked URL is the exact reviewed source_urls[2] leaf. |  |  |
| `terrain_domain:matterhorn-ski-paradise` | `total_lift_count` | [Matterhorn Paradise - Zermatt Matterhorn Region](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `52` | The linked Matterhorn Paradise - Zermatt Matterhorn Region supports the reviewed total_lift_count leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `display_name` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"Folgarida-Marilleva"` | The linked official source directly supports manifest leaf display_name. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.destination_coordinates` | [OpenStreetMap node 327580361](https://www.openstreetmap.org/node/327580361) | `"verified"` | Manifest source-set summary for field_statuses.destination_coordinates: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.destination_elevation` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `"verified"` | Manifest source-set summary for field_statuses.destination_elevation: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.destination_identity` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"verified"` | Manifest source-set summary for field_statuses.destination_identity: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.lift_pass_products` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.lift_pass_products: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.rental_examples` | [Folgarida Marilleva - Ski Point](https://www.ski.it/it/noleggi/folgarida/ski-point) | `"verified"` | Manifest source-set summary for field_statuses.rental_examples: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.ski_areas` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.ski_areas: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.stay_base_lift_distance` | [OpenStreetMap node 648469713](https://www.openstreetmap.org/node/648469713) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.stay_base_lift_distance: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `field_statuses.stay_bases` | [OpenStreetMap node 327580361](https://www.openstreetmap.org/node/327580361) | `"verified"` | Manifest source-set summary for field_statuses.stay_bases: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `notes[0]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"The resulting model represents Folgarida-Marilleva as an independent destination with one local weather-owning ski area and four reviewed stay bases."` | Manifest source-set summary for notes[0]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `notes[1]` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `"The local 62 km and 1300-2180 m facts remain child-scoped; the shared 156 km aggregate belongs only to campiglio-dolomiti-di-brenta."` | Manifest source-set summary for notes[1]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `notes[3]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"folgarida-marilleva-ski-area is a new weather identity that requires owner-run history backfill and climatology after deployment."` | Manifest source-set summary for notes[3]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[0]` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"https://www.campigliodolomiti.it/en/ski-area"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[1]` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[2]` | [OpenStreetMap node 1096349433](https://www.openstreetmap.org/node/1096349433) | `"https://www.openstreetmap.org/node/1096349433"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[3]` | [OpenStreetMap node 1096349822](https://www.openstreetmap.org/node/1096349822) | `"https://www.openstreetmap.org/node/1096349822"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[4]` | [OpenStreetMap node 327580361](https://www.openstreetmap.org/node/327580361) | `"https://www.openstreetmap.org/node/327580361"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[5]` | [OpenStreetMap node 331259364](https://www.openstreetmap.org/node/331259364) | `"https://www.openstreetmap.org/node/331259364"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[6]` | [OpenStreetMap node 331259493](https://www.openstreetmap.org/node/331259493) | `"https://www.openstreetmap.org/node/331259493"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[7]` | [OpenStreetMap node 6043719130](https://www.openstreetmap.org/node/6043719130) | `"https://www.openstreetmap.org/node/6043719130"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[8]` | [OpenStreetMap node 648469713](https://www.openstreetmap.org/node/648469713) | `"https://www.openstreetmap.org/node/648469713"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[9]` | [OpenStreetMap node 8662539441](https://www.openstreetmap.org/node/8662539441) | `"https://www.openstreetmap.org/node/8662539441"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[10]` | [Folgarida-Marilleva - Official Ski Area](https://www.ski.it/en/skiarea/folgarida-marilleva) | `"https://www.ski.it/en/skiarea/folgarida-marilleva"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[11]` | [Folgarida Marilleva - Ski Point](https://www.ski.it/it/noleggi/folgarida/ski-point) | `"https://www.ski.it/it/noleggi/folgarida/ski-point"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[12]` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `"https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:folgarida-marilleva` | `source_refs[13]` | [2025/26 Folgarida Marilleva Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf) | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFFMit.pdf"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.destination_elevation` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.destination_elevation: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.lift_pass_products` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.lift_pass_products: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.rental_examples` | [Campiglio Dolomiti - Ski Rentals](https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals) | `"verified"` | Manifest source-set summary for field_statuses.rental_examples: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.season_window` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.season_window: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.ski_areas` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.ski_areas: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `field_statuses.stay_base_lift_distance` | [OpenStreetMap node 1023438277](https://www.openstreetmap.org/node/1023438277) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.stay_base_lift_distance: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[0]` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `"Full destination sweep uses official local, connected-domain, pass, rental, ski-map, and OSM evidence."` | Manifest source-set summary for notes[0]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[1]` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `"Madonna di Campiglio remains an independent destination and retains madonna-di-campiglio-ski-area as its weather identity."` | Manifest source-set summary for notes[1]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[2]` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `"The local 62 km fact stays on Madonna's child ski area; the shared 156 km aggregate belongs only to campiglio-dolomiti-di-brenta."` | Manifest source-set summary for notes[2]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `notes[3]` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"The shared pass references the connected terrain domain while Pejo remains disconnected external pass validity."` | Manifest source-set summary for notes[3]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[1]` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"https://www.campigliodolomiti.it/en/ski-area"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[2]` | [Campiglio Dolomiti - Ski Rentals](https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/ski-rentals"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[3]` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[4]` | [OpenStreetMap node 1023438277](https://www.openstreetmap.org/node/1023438277) | `"https://www.openstreetmap.org/node/1023438277"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[5]` | [OpenStreetMap node 1796357582](https://www.openstreetmap.org/node/1796357582) | `"https://www.openstreetmap.org/node/1796357582"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[6]` | [Madonna di Campiglio - Official Ski Area](https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino) | `"https://www.ski.it/en/skiarea/madonna-di-campiglio-trentino"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:madonna-di-campiglio` | `source_refs[7]` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `"https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:pinzolo` | `display_name` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"Pinzolo"` | The linked official source directly supports manifest leaf display_name. |  |  |
| `trust_manifest:destination:pinzolo` | `field_statuses.destination_coordinates` | [OpenStreetMap node 4311362989](https://www.openstreetmap.org/node/4311362989) | `"verified"` | Manifest source-set summary for field_statuses.destination_coordinates: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:pinzolo` | `field_statuses.destination_identity` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"verified"` | Manifest source-set summary for field_statuses.destination_identity: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:pinzolo` | `field_statuses.lift_pass_products` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.lift_pass_products: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:pinzolo` | `field_statuses.rental_examples` | [Campiglio Dolomiti - Il Comodo Sci](https://www.campigliodolomiti.it/en/services/il-comodo-sci) | `"verified"` | Manifest source-set summary for field_statuses.rental_examples: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:pinzolo` | `field_statuses.stay_base_lift_distance` | [OpenStreetMap node 298987790](https://www.openstreetmap.org/node/298987790) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.stay_base_lift_distance: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:pinzolo` | `field_statuses.stay_bases` | [OpenStreetMap node 4311362989](https://www.openstreetmap.org/node/4311362989) | `"verified"` | Manifest source-set summary for field_statuses.stay_bases: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:pinzolo` | `notes[0]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"The resulting model represents Pinzolo as an independent destination with one local weather-owning ski area and source-backed identity and coordinates."` | Manifest source-set summary for notes[0]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:pinzolo` | `notes[1]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"Pinzolo's local 31 km fact remains child-scoped; the 156 km aggregate belongs only to campiglio-dolomiti-di-brenta."` | Manifest source-set summary for notes[1]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:pinzolo` | `notes[3]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"pinzolo-ski-area is a new weather identity that requires owner-run history backfill and climatology after deployment."` | Manifest source-set summary for notes[3]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:destination:pinzolo` | `source_refs[0]` | [bergfex.it - Pinzolo](https://www.bergfex.it/pinzolo/) | `"https://www.bergfex.it/pinzolo/"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:pinzolo` | `source_refs[1]` | [Campiglio Dolomiti - Il Comodo Sci](https://www.campigliodolomiti.it/en/services/il-comodo-sci) | `"https://www.campigliodolomiti.it/en/services/il-comodo-sci"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:pinzolo` | `source_refs[2]` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"https://www.campigliodolomiti.it/en/ski-area"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:pinzolo` | `source_refs[3]` | [Campiglio Dolomiti di Brenta Skiarea Skipass](https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea) | `"https://www.campigliodolomiti.it/en/skiarea/inverno/skipass/skipass-skiarea"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:pinzolo` | `source_refs[4]` | [OpenStreetMap node 298987790](https://www.openstreetmap.org/node/298987790) | `"https://www.openstreetmap.org/node/298987790"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:pinzolo` | `source_refs[5]` | [OpenStreetMap node 4311362989](https://www.openstreetmap.org/node/4311362989) | `"https://www.openstreetmap.org/node/4311362989"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:pinzolo` | `source_refs[6]` | [Pinzolo - Official Ski Area](https://www.ski.it/en/skiarea/pinzolo) | `"https://www.ski.it/en/skiarea/pinzolo"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:destination:pinzolo` | `source_refs[7]` | [2025/26 Pinzolo Tariff PDF](https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf) | `"https://www.ski.it/ski/documenti-file/skipass/listini/2025-2026listinoFPIit.pdf"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `display_name` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"Campiglio Dolomiti di Brenta"` | The linked official source directly supports manifest leaf display_name. |  |  |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `field_statuses.membership` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.membership: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `field_statuses.terrain_metrics` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.terrain_metrics: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[0]` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"Official sources identify Madonna di Campiglio, Pinzolo, and Folgarida-Marilleva as the ski-connected domain members; Pejo is excluded and remains external pass validity."` | Manifest source-set summary for notes[0]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[1]` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"The 156 km aggregate uses the official tourism-domain value while preserving the official map's conflicting 155 km value."` | Manifest source-set summary for notes[1]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `notes[3]` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"The terrain domain owns no weather history; weather remains on the three local ski-area identities."` | Manifest source-set summary for notes[3]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `source_refs[0]` | [Campiglio Dolomiti - Ski Area](https://www.campigliodolomiti.it/en/ski-area) | `"https://www.campigliodolomiti.it/en/ski-area"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:terrain_domain:campiglio-dolomiti-di-brenta` | `source_refs[1]` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `"https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `display_name` | [Matterhorn Paradise - Zermatt Matterhorn Region](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `"Matterhorn Ski Paradise"` | The linked official source directly supports manifest leaf display_name. |  |  |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `field_statuses.membership` | [Matterhorn Paradise - Zermatt Matterhorn Region](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.membership: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `field_statuses.terrain_metrics` | [Matterhorn Paradise - Zermatt Matterhorn Region](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.terrain_metrics: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `notes[0]` | [Matterhorn Paradise - Zermatt Matterhorn Region](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `"Official Matterhorn Paradise sources support ski-connected Zermatt and Cervinia membership; Snowcast normalizes those places to their modeled destination and ski-area ids."` | Manifest source-set summary for notes[0]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `notes[1]` | [Matterhorn Paradise - Zermatt Matterhorn Region](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `"The current official region page supports the 360 km and 52-lift cross-border aggregate; terrain_metrics remains verified_with_adjustment because the 1620 m lower bound is normalized from the official Zermatt resort-side elevation. The 3883 m summit is separately source-backed, and the domain does not own weather evidence."` | Manifest source-set summary for notes[1]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[0]` | [Matterhorn Paradise - Winter Ski Pass](https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter) | `"https://www.matterhornparadise.ch/en/book/tickets/ski-pass-winter"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[1]` | [Matterhorn Glacier Paradise](https://www.matterhornparadise.ch/en/experience/peaks/matterhorn-glacier-paradise) | `"https://www.matterhornparadise.ch/en/experience/peaks/matterhorn-glacier-paradise"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[2]` | [Matterhorn Paradise - Zermatt Matterhorn Region](https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn) | `"https://www.matterhornparadise.ch/en/experience/region-zermatt-matterhorn"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:terrain_domain:matterhorn-ski-paradise` | `source_refs[3]` | [Matterhorn Paradise - Skiing](https://www.matterhornparadise.ch/en/experience/skiing) | `"https://www.matterhornparadise.ch/en/experience/skiing"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:terrain_domain:tignes-val-disere` | `display_name` | [Tignes Official Ski Area](https://en.tignes.net/skiing/ski-area) | `"Tignes - Val d'Isere"` | The linked official source directly supports manifest leaf display_name. |  |  |
| `trust_manifest:terrain_domain:tignes-val-disere` | `field_statuses.membership` | [Tignes Official Ski Area](https://en.tignes.net/skiing/ski-area) | `"verified"` | Manifest source-set summary for field_statuses.membership: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:tignes-val-disere` | `field_statuses.terrain_metrics` | [Bergfex - Tignes / Val d'Isere](https://www.bergfex.com/skiregionen/valdiseres-tignes/) | `"verified_with_adjustment"` | Manifest source-set summary for field_statuses.terrain_metrics: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:tignes-val-disere` | `notes[0]` | [Tignes Official Ski Area](https://en.tignes.net/skiing/ski-area) | `"Official Tignes and Val d'Isere pages identify one ski-connected 300 km domain spanning both modeled destinations."` | Manifest source-set summary for notes[0]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:tignes-val-disere` | `notes[1]` | [Bergfex - Tignes / Val d'Isere](https://www.bergfex.com/skiregionen/valdiseres-tignes/) | `"The aggregate lift count is verified_with_adjustment: official pages conflict at 74 and 71 lifts, so the reviewed Bergfex category sum supplies the normalized value of 72; aggregate elevations remain scoped to the domain."` | Manifest source-set summary for notes[1]: the value reflects the complete reviewed source set and curation policy. The linked URL is the most directly relevant source; it does not alone prove this leaf. |  |  |
| `trust_manifest:terrain_domain:tignes-val-disere` | `source_refs[0]` | [Tignes Official Ski Area](https://en.tignes.net/skiing/ski-area) | `"https://en.tignes.net/skiing/ski-area"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:terrain_domain:tignes-val-disere` | `source_refs[1]` | [Bergfex - Tignes / Val d'Isere](https://www.bergfex.com/skiregionen/valdiseres-tignes/) | `"https://www.bergfex.com/skiregionen/valdiseres-tignes/"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `trust_manifest:terrain_domain:tignes-val-disere` | `source_refs[2]` | [Val d'Isere Official Ski Area](https://www.valdisere.com/en/val-disere-in-winter/skiing-winter-fun/ski-area-french-alps/) | `"https://www.valdisere.com/en/val-disere-in-winter/skiing-winter-fun/ski-area-french-alps/"` | This source_refs leaf adds the exact external URL linked here. |  |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `total_lift_count` | [Ski area Madonna di Campiglio - Official Tourism Page](https://www.campigliodolomiti.it/en/ski-area) | `61` | The two official sources cover the same Campiglio terrain-domain lift-count scope but conflict at 61 and 58. Neither value is selected, so this evidence supports the unresolved coverage row only. | Recorded as one side of an unresolved same-scope official conflict; no catalog value is selected. |  |
| `terrain_domain:campiglio-dolomiti-di-brenta` | `total_lift_count` | [Campiglio Dolomiti di Brenta Official Ski Map](https://www.ski.it/ski/documenti-file/live/Ski_Map_Skiarea.pdf) | `58` | The two official sources cover the same Campiglio terrain-domain lift-count scope but conflict at 61 and 58. Neither value is selected, so this evidence supports the unresolved coverage row only. | Recorded as one side of an unresolved same-scope official conflict; no catalog value is selected. |  |

## Boundary Decisions

Decision targets: `madonna-di-campiglio`, `pinzolo`, `folgarida-marilleva`

| Candidate | Failure Route |
| --- | --- |
| `madonna-di-campiglio` | `none` |
| `pinzolo` | `none` |
| `folgarida-marilleva` | `none` |

### Candidate `madonna-di-campiglio`

#### Gates

| Gate | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `independent_stay_context` | `pass` | `boundary-madonna-di-campiglio` | The candidate-specific official page presents booking and accommodation. |
| `independent_ski_access` | `pass` | `boundary-madonna-di-campiglio` | The candidate-specific official page presents local ski access. |
| `independent_recommendation_value` | `pass` | `boundary-madonna-di-campiglio` | The candidate-specific official page presents distinct positioning. |

#### Identity Signals

| Signal | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `official_destination_treatment` | `pass` | `boundary-madonna-di-campiglio` | The official ski-area source presents the candidate by name. |

### Candidate `pinzolo`

#### Gates

| Gate | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `independent_stay_context` | `pass` | `boundary-pinzolo` | The candidate-specific official page presents booking and accommodation. |
| `independent_ski_access` | `pass` | `boundary-pinzolo` | The candidate-specific official page presents local ski access. |
| `independent_recommendation_value` | `pass` | `boundary-pinzolo` | The candidate-specific official page presents distinct positioning. |

#### Identity Signals

| Signal | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `official_destination_treatment` | `pass` | `boundary-pinzolo` | The official ski-area source presents the candidate by name. |

### Candidate `folgarida-marilleva`

#### Gates

| Gate | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `independent_stay_context` | `pass` | `boundary-folgarida-marilleva` | The candidate-specific official page presents booking and accommodation. |
| `independent_ski_access` | `pass` | `boundary-folgarida-marilleva` | The candidate-specific official page presents local ski access. |
| `independent_recommendation_value` | `pass` | `boundary-folgarida-marilleva` | The candidate-specific official page presents distinct positioning. |

#### Identity Signals

| Signal | Status | Evidence Refs | Notes |
| --- | --- | --- | --- |
| `official_destination_treatment` | `pass` | `boundary-folgarida-marilleva` | The official ski-area source presents the candidate by name. |

## Weather Request Geometry

Geometry targets: `madonna-di-campiglio-ski-area`

| Ski Area | Before | After | Material Change |
| --- | --- | --- | --- |
| `madonna-di-campiglio-ski-area` | `{"base_elevation_m": 1550, "latitude": 46.2267, "longitude": 10.8268, "mid_elevation_m": 2027, "upper_elevation_m": 2409}` | `{"base_elevation_m": 1550, "latitude": 46.2267, "longitude": 10.8268, "mid_elevation_m": 2027, "upper_elevation_m": 2409}` | no |

## Ranking Impact

The default ranking diagnostic produced 12 rows / 11 groups and emitted none of the three Campiglio destinations (Madonna di Campiglio, Pinzolo, or Folgarida-Marilleva), so this run establishes no comparative ranking outcome for them.

## Verification

- `REPO_DOC=docs BASE=$(mktemp -d) CURRENT=$(mktemp -d); git show e8f4e11:app/data/resorts.json > "$BASE/resorts.json"; git show e8f4e11:app/data/terrain_domains.json > "$BASE/terrain_domains.json"; git show e8f4e11:app/data/resort_trust_manifest.json > "$BASE/resort_trust_manifest.json"; git show e57b5bb:app/data/resorts.json > "$CURRENT/resorts.json"; git show e57b5bb:app/data/terrain_domains.json > "$CURRENT/terrain_domains.json"; git show e57b5bb:app/data/resort_trust_manifest.json > "$CURRENT/resort_trust_manifest.json"; UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --validation-mode reconcile --report-path "$REPO_DOC/catalog-curation/2026-06-27-madonna-di-campiglio.json" --base-resorts-path "$BASE/resorts.json" --current-resorts-path "$CURRENT/resorts.json" --base-terrain-domains-path "$BASE/terrain_domains.json" --current-terrain-domains-path "$CURRENT/terrain_domains.json" --base-trust-manifest-path "$BASE/resort_trust_manifest.json" --current-trust-manifest-path "$CURRENT/resort_trust_manifest.json" --required-boundary-target madonna-di-campiglio --required-boundary-target pinzolo --required-boundary-target folgarida-marilleva --required-weather-geometry-target madonna-di-campiglio-ski-area --allow-legacy-base-trust-without-terrain-domains --markdown-output "$REPO_DOC/catalog-curation/2026-06-27-madonna-di-campiglio.md"`

## Caveats

- The Campiglio terrain-domain aggregate remains 156 km from the official tourism source, with the conflicting 155 km official-map value kept visible in evidence.
- Campiglio terrain-domain total_lift_count remains unset: the official tourism page reports 61 lifts and the official ski map reports 58 for the same scope; both sources are official, neither is established as authoritative or current enough to select, and no accepted same-scope Bergfex fallback was used.
- Child total_piste_km values remain scoped to their local ski areas. Child lift counts and difficulty splits remain unresolved where no child-scoped source was accepted; domain elevations, difficulty splits, and shared season timing remain unresolved where no same-scope source was accepted.
- Pejo remains disconnected external pass validity and is not a Campiglio terrain-domain member. Shared Skiarea products reference the domain; destination-local products remain local.
- Estimated fields remain estimates, including Pinzolo ski-area elevations and the corresponding estimated trust group, lodging and rental quality or price bands, broad skill support, and unsourced atmosphere tags. Stored price_min and price_max values are model derivations of the reviewed price_range strings, not independent market observations.
- The durable trust notes preserve source conflicts, child/domain scope, estimates, external validity, and weather ownership exactly as stored in the pinned e57b5bb manifest.
- The new Pinzolo and Folgarida-Marilleva weather identities still require owner-run archive backfill and climatology rebuild after deployment; this report runs neither workflow.
- Madonna di Campiglio retains identical before/after weather-request geometry, so validator-computed material_change is false and no conditional force_refetch is required for that retained identity.
- Production search may display multiple Campiglio domain members until separate deduplication work lands.
