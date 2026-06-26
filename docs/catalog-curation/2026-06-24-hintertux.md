# Hintertux Catalog Curation

Reviewed Hintertux destination, Hintertux Glacier ski-area terrain, winter season window, default regional-network pass product, and stay-base access fields against official Hintertux/Tux-Finkenberg pages, OSM geometry, Wikidata identity, and reviewed editorial piste/lift breakdowns. Added local terrain metrics only to the modeled Hintertux Glacier ski area and kept the broader Ski & Glacier World Zillertal 3000 / Zillertaler Superskipass terrain scope in the pass-product external summary rather than creating a partial shared terrain domain.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:hintertux` | `season_windows` | `null` | `[{"end_date": "2027-05-07", "season_label": "Winter 2026/27", "start_date": "2026-10-03", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:hintertux-glacier` | `season_windows` | `null` | `[{"end_date": "2027-05-07", "season_label": "Winter 2026/27", "start_date": "2026-10-03", "status": "planned"}]` | `verified_with_adjustment` | yes |
| `ski_area:hintertux-glacier` | `total_piste_km` | `null` | `64.0` | `verified` | yes |
| `ski_area:hintertux-glacier` | `total_lift_count` | `null` | `20` | `verified_with_adjustment` | yes |
| `ski_area:hintertux-glacier` | `piste_km_by_difficulty` | `null` | `{"advanced": 11.7, "beginner": 17.2, "intermediate": 35.1}` | `verified_with_adjustment` | yes |
| `stay_base:hintertux-hintertux` | `lift_distance` | `"near"` | `"medium"` | `verified_with_adjustment` | yes |
| `stay_base:hintertux-hintertux` | `latitude` | `null` | `47.115` | `verified_with_adjustment` | no |
| `stay_base:hintertux-hintertux` | `longitude` | `null` | `11.6825` | `verified_with_adjustment` | no |
| `stay_base:hintertux-hintertux` | `nearest_lift_name` | `null` | `"Gletscherbus 1 Talstation"` | `verified` | no |
| `stay_base:hintertux-hintertux` | `nearest_lift_distance_m` | `null` | `1074` | `verified_with_adjustment` | yes |
| `stay_base:hintertux-hintertux` | `access_mode` | `"unknown"` | `"ski_bus"` | `verified_with_adjustment` | yes |
| `stay_base:hintertux-hintertux` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:hintertux-hintertux` | `atmosphere_tags` | `[]` | `["glacier_access", "snow_sure", "pure_skiing"]` | `verified_with_adjustment` | no |
| `stay_base:hintertux-hintertux` | `regional_data_ids` | `{}` | `{"nearest_lift_osm_node_id": "27337851", "nearest_lift_osm_way_id": "4388462", "osm_node_id": "321007835", "wikidata_id": "Q688964"}` | `verified` | no |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `is_default` | `null` | `true` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `validity_scope` | `null` | `"regional_network"` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `valid_ski_area_ids` | `null` | `["hintertux-glacier"]` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `external_validity_summary` | `null` | `"Winter 2026/27 pass covers Hintertux Glacier locally; during the main winter network window it also covers Eggalm, Rastkogel, Finkenberg, Penken/Mayrhofen, Ahorn, and broader Zillertal Superskipass terrain depending on duration and date."` | `verified_with_adjustment` | no |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `prices` | `null` | `[{"amount": 82.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27", "source_url": "https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 main Zillertaler Superskipass window", "source_url": "https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/"}, {"amount": 399.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 main Zillertaler Superskipass window", "source_url": "https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/"}]` | `verified` | no |
| `destination:hintertux` | `trust_manifest.field_statuses.stay_base_lift_distance` | `"estimated"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |
| `destination:hintertux` | `trust_manifest.field_statuses.lift_pass_products` | `"needs_source"` | `"verified_with_adjustment"` | `verified_with_adjustment` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `destination:hintertux` | `season_windows` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `ski_area:hintertux-glacier` | `season_windows` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `ski_area:hintertux-glacier` | `total_piste_km` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `ski_area:hintertux-glacier` | `total_lift_count` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `ski_area:hintertux-glacier` | `piste_km_by_difficulty` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `stay_base:hintertux-hintertux` | `lift_distance` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `stay_base:hintertux-hintertux` | `latitude` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `stay_base:hintertux-hintertux` | `longitude` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `stay_base:hintertux-hintertux` | `nearest_lift_name` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `stay_base:hintertux-hintertux` | `nearest_lift_distance_m` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `stay_base:hintertux-hintertux` | `access_mode` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `stay_base:hintertux-hintertux` | `base_type` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `stay_base:hintertux-hintertux` | `atmosphere_tags` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `stay_base:hintertux-hintertux` | `regional_data_ids` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `is_default` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `validity_scope` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `valid_ski_area_ids` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `external_validity_summary` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `prices` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `destination:hintertux` | `trust_manifest.field_statuses.stay_base_lift_distance` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |
| `destination:hintertux` | `trust_manifest.field_statuses.lift_pass_products` | `changed` | Typed coverage backfilled from the historical changed-field entry; see the Markdown report for the full field coverage matrix. |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `destination:hintertux` | `season_windows` | [Tickets and rates Hintertux Glacier](https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/) | `[{"end_date": "2027-05-07", "season_label": "Winter 2026/27", "start_date": "2026-10-03", "status": "planned"}]` | Official Hintertux ticket page publishes the winter 2026/27 ski-pass validity window from October 3, 2026 through May 7, 2027. |  |
| `ski_area:hintertux-glacier` | `season_windows` | [Tickets and rates Hintertux Glacier](https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/) | `[{"end_date": "2027-05-07", "season_label": "Winter 2026/27", "start_date": "2026-10-03", "status": "planned"}]` | Official Hintertux ticket page publishes the winter 2026/27 ski-pass validity window used for the single modeled ski area. |  |
| `ski_area:hintertux-glacier` | `total_piste_km` | [Glacier ski area Hintertux Glacier](https://www.hintertuxergletscher.at/en/skiing/hintertux-glacier/glacier-ski-area/) | `64.0` | Official Hintertux Glacier page states the local glacier ski area offers up to 64 kilometers of slopes from 1,500 m to 3,250 m. |  |
| `ski_area:hintertux-glacier` | `total_lift_count` | [Ski lifts Hintertux Glacier](https://www.skiresort.info/ski-resort/hintertux-glacier-hintertuxer-gletscher/ski-lifts/) | `20` | Reviewed editorial ski-lift page lists 20 ski lifts for the scoped Hintertux Glacier ski resort. |  |
| `ski_area:hintertux-glacier` | `piste_km_by_difficulty` | [Slopes Hintertux Glacier](https://www.skiresort.info/ski-resort/hintertux-glacier-hintertuxer-gletscher/slope-offering/) | `{"advanced": 11.7, "beginner": 17.2, "intermediate": 35.1}` | Reviewed editorial slope page splits the 64 km local Hintertux Glacier terrain into 17.2 km easy, 35.1 km intermediate, and 11.7 km difficult slopes. |  |
| `stay_base:hintertux-hintertux` | `lift_distance` | [OpenStreetMap Gletscherbus 1 Talstation](https://www.openstreetmap.org/node/27337851) | `1074` | Computed Haversine distance from the OSM Hintertux village node to the OSM Gletscherbus 1 bottom-station node is 1,074 m. | Distance is normalized from the previous legacy near bucket to lift_distance=medium because it is above the walkable <=500 m factor threshold and within the <=1500 m shuttle-easy range. |
| `stay_base:hintertux-hintertux` | `latitude` | [OpenStreetMap Hintertux village node](https://www.openstreetmap.org/node/321007835) | `47.1150202` | OSM place node for Hintertux provides the stay-base village coordinate. | Rounded to 4 decimal places for catalog consistency. |
| `stay_base:hintertux-hintertux` | `longitude` | [OpenStreetMap Hintertux village node](https://www.openstreetmap.org/node/321007835) | `11.6824994` | OSM place node for Hintertux provides the stay-base village coordinate. | Rounded to 4 decimal places for catalog consistency. |
| `stay_base:hintertux-hintertux` | `nearest_lift_name` | [OpenStreetMap Gletscherbus 1 Talstation](https://www.openstreetmap.org/node/27337851) | `"Gletscherbus 1 Talstation"` | OSM station node identifies Gletscherbus 1 Talstation as the bottom station for the nearest glacier-access lift. |  |
| `stay_base:hintertux-hintertux` | `nearest_lift_distance_m` | [OpenStreetMap Gletscherbus 1 Talstation](https://www.openstreetmap.org/node/27337851) | `1074` | Computed Haversine distance from the OSM Hintertux village node to the OSM Gletscherbus 1 bottom-station node. |  |
| `stay_base:hintertux-hintertux` | `access_mode` | [Arrival and parking at Hintertux Glacier](https://www.hintertuxergletscher.at/en/information/plan-your-visit/getting-there-parking/) | `{"nearest_lift_distance_m": 1074, "official_access_context": "Official page describes bus access to Hintertux and parking directly at the valley station."}` | Official access page describes reaching Hintertux by bus from Mayrhofen and valley-station parking, while OSM geometry puts the village about 1.1 km from Gletscherbus 1 Talstation. | Combined official bus/valley-station access context with OSM distance to normalize access_mode to ski_bus rather than walk. |
| `stay_base:hintertux-hintertux` | `base_type` | [OpenStreetMap Hintertux village node](https://www.openstreetmap.org/node/321007835) | `"village"` | OSM classifies Hintertux as a village place node. |  |
| `stay_base:hintertux-hintertux` | `atmosphere_tags` | [Glacier ski area Hintertux Glacier](https://www.hintertuxergletscher.at/en/skiing/hintertux-glacier/glacier-ski-area/) | `"Austria's snow-sure glacier ski area with year-round glacier skiing and high-altitude slopes."` | Official glacier page supports glacier-access, snow-sure, and skiing-first character for the Hintertux stay base. | Official descriptive claims are normalized into Snowcast atmosphere tags. |
| `stay_base:hintertux-hintertux` | `regional_data_ids` | [Wikidata Hintertux Glacier](https://www.wikidata.org/wiki/Q688964) | `{"nearest_lift_osm_node_id": "27337851", "nearest_lift_osm_way_id": "4388462", "osm_node_id": "321007835", "wikidata_id": "Q688964"}` | OSM provides stable village and lift-station object IDs; Wikidata provides the Hintertux Glacier entity id. |  |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `is_default` | [Tickets and rates Hintertux Glacier](https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/) | `"Winter 2026/27 adult ski-pass rates for Hintertux Glacier and the main Zillertal network window."` | Official Hintertux ticket page presents the representative winter adult/default ski-pass pricing for this destination. | Normalized official ticket-page positioning to is_default=true for the only curated Hintertux pass product. |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `validity_scope` | [Ski & Glacier World Zillertal 3000](https://www.hintertuxergletscher.at/en/skiing/ski-glacier-world-zillertal-3000/) | `"Hintertux Glacier, Eggalm, Rastkogel, Finkenberg, Penken/Mayrhofen and Ahorn merge to form Ski & Glacier World Zillertal 3000."` | Official network page describes pass-relevant terrain beyond the single modeled Hintertux Glacier ski area. | Broader official network scope is normalized to validity_scope=regional_network without creating a partial shared terrain domain. |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `valid_ski_area_ids` | [Tickets and rates Hintertux Glacier](https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/) | `"Hintertux Glacier local validity plus broader main-season network validity."` | Official ticket page identifies Hintertux Glacier as the local modeled ski area covered by the curated pass product. | Mapped official Hintertux Glacier wording to local ski_area_id hintertux-glacier; external areas remain in external_validity_summary. |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `external_validity_summary` | [Ski & Glacier World Zillertal 3000](https://www.hintertuxergletscher.at/en/skiing/ski-glacier-world-zillertal-3000/) | `"Hintertux Glacier, Eggalm, Rastkogel, Finkenberg, Penken/Mayrhofen and Ahorn; up to 206 km of pistes from 630 m to 3,250 m."` | Official network page describes the wider linked terrain scope covered during the main winter network window. | External scope is summarized on the pass product because several areas are not modeled as local Hintertux ski areas. |
| `lift_pass_product:ski-glacier-world-zillertal-3000` | `prices` | [Tickets and rates Hintertux Glacier](https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/) | `[{"amount": 82.0, "audience": "adult", "currency": "EUR", "duration_days": 1, "price_kind": "fixed", "season_label": "Winter 2026/27", "source_url": "https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/"}, {"amount": 241.0, "audience": "adult", "currency": "EUR", "duration_days": 3, "price_kind": "fixed", "season_label": "Winter 2026/27 main Zillertaler Superskipass window", "source_url": "https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/"}, {"amount": 399.0, "audience": "adult", "currency": "EUR", "duration_days": 6, "price_kind": "fixed", "season_label": "Winter 2026/27 main Zillertaler Superskipass window", "source_url": "https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/"}]` | Official tariff page lists adult 1-day, 3-day, and 6-day winter 2026/27 prices used as representative default pass examples. |  |
| `destination:hintertux` | `trust_manifest.field_statuses.stay_base_lift_distance` | [OpenStreetMap Gletscherbus 1 Talstation](https://www.openstreetmap.org/node/27337851) | `"OSM village/lift geometry plus official access context."` | Stay-base access now has reviewed OSM distance and official access context, so the manifest field group moves from estimated to verified_with_adjustment. | Trust status summarizes multiple reviewed source-backed access facts rather than one raw source value. |
| `destination:hintertux` | `trust_manifest.field_statuses.lift_pass_products` | [Tickets and rates Hintertux Glacier](https://www.hintertuxergletscher.at/en/tickets-rates/tickets-rates/rates-hintertux-glacier/) | `"Official Hintertux Glacier and Zillertal ski-pass validity and price evidence."` | Official pass scope and price evidence supports moving lift_pass_products from needs_source to verified_with_adjustment. | Trust status summarizes scoped pass-product facts rather than one raw source value. |

## Ranking Impact

Default comparison diagnostics wrote 12 DB-backed rows to artifacts/ranking-comparison. Hintertux appears in the austria_advanced_access scenario and moves from current rank 2 to candidate rank 1. A read-only static-catalog factor check confirms the edited JSON now derives terrain_scale=medium, skill_fit=('intermediate'), and stay_base_access=shuttle_easy for Hintertux; the DB-backed artifact may require a local seed sync before its component breakdown fully reflects this branch's checked-in catalog.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-24-hintertux.json --markdown-output docs/catalog-curation/2026-06-24-hintertux.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`

## Caveats

- The broader Ski & Glacier World Zillertal 3000 / Zillertaler Superskipass terrain scope is intentionally not modeled as a shared terrain domain in this PR because it includes unmodeled areas beyond Hintertux and Mayrhofen.
- Official pages reviewed in this sweep did not publish a local Hintertux Glacier blue/red/black numeric split or static total lift count; those fields use reviewed editorial evidence and remain verified_with_adjustment rather than fully official verified.
- Lodging price range, stay-base quality, supported skill levels, rental price range, and rental quality remain product-curated estimates.
## Field Coverage Matrix

Destination fields:

| Field | Decision | Note |
| --- | --- | --- |
| `resort_id` | reviewed-no-change | Stable id remains `hintertux`. |
| `name` | reviewed-no-change | Official operator/tourism sources use Hintertux and Hintertux Glacier for this destination scope. |
| `country` | reviewed-no-change | Austria remains source-consistent. |
| `region` | reviewed-no-change | Tyrol remains source-consistent. |
| `price_level` | reviewed-no-change | Legacy product tier remains `high`; detailed lodging/rental price trust stays estimated. |
| `latitude` | reviewed-no-change | Destination coordinate remains product-normalized to the Hintertux/Glacier destination identity. |
| `longitude` | reviewed-no-change | Destination coordinate remains product-normalized to the Hintertux/Glacier destination identity. |
| `base_elevation_m` | reviewed-no-change | 1,500 m remains aligned to official valley-station/base elevation. |
| `summit_elevation_m` | reviewed-no-change | 3,250 m remains aligned to official high-point/glacier elevation. |
| `season_start_month` | reviewed-no-change | October remains aligned to the reviewed winter 2026/27 product window. |
| `season_end_month` | reviewed-no-change | May remains aligned to the reviewed winter 2026/27 product window. |
| `season_windows` | changed | Added the reviewed winter 2026/27 exact product window. |
| `lift_pass_products` | changed | Added one default regional-network pass product with external Zillertal validity summary and reviewed adult price examples. |
| `ski_areas` | changed | Added reviewed local Hintertux Glacier terrain metrics and exact season window. |
| `terrain_groups` | not-applicable | Single modeled local ski area; no local aggregate terrain group created. |
| `stay_bases` | changed | Added reviewed Hintertux village access metadata and corrected legacy lift-distance bucket. |
| `rentals` | reviewed-no-change | Existing INTERSPORT Hintertux example remains in place; rental pricing/quality trust remains estimated. |

Ski-area fields:

| Ski Area | Field | Decision | Note |
| --- | --- | --- | --- |
| Hintertux Glacier | `ski_area_id`, `name` | reviewed-no-change | Stable id/display name preserved. |
| Hintertux Glacier | `latitude`, `longitude` | reviewed-no-change | Weather-critical coordinates left unchanged as product-normalized glacier lookup coordinates. |
| Hintertux Glacier | `base_elevation_m`, `summit_elevation_m` | reviewed-no-change | Existing 1,500-3,250 m range matches official elevation wording. |
| Hintertux Glacier | `season_start_month`, `season_end_month` | reviewed-no-change | Month fallback remains October-May. |
| Hintertux Glacier | `season_windows` | changed | Added the reviewed winter 2026/27 exact product window. |
| Hintertux Glacier | `total_piste_km` | changed | Added 64 km from the official local glacier ski-area page. |
| Hintertux Glacier | `total_lift_count` | changed | Added 20 lifts from reviewed editorial static lift inventory. |
| Hintertux Glacier | `piste_km_by_difficulty.beginner` | changed | Added 17.2 km easy slopes from reviewed editorial slope breakdown. |
| Hintertux Glacier | `piste_km_by_difficulty.intermediate` | changed | Added 35.1 km intermediate slopes from reviewed editorial slope breakdown. |
| Hintertux Glacier | `piste_km_by_difficulty.advanced` | changed | Added 11.7 km difficult slopes from reviewed editorial slope breakdown. |

Terrain-group fields:

| Terrain Group | Field | Decision | Note |
| --- | --- | --- | --- |
| None | `terrain_group_id`, `name`, `ski_area_ids`, `metric_scope` | not-applicable | No local aggregate terrain group applies to the single modeled Hintertux ski area. |
| None | `total_piste_km`, `total_lift_count`, `piste_km_by_difficulty.*` | not-applicable | Broader Zillertal 3000 aggregate terrain is intentionally not copied into a Hintertux terrain group. |

Terrain-domain fields:

| Terrain Domain | Field | Decision | Note |
| --- | --- | --- | --- |
| Ski & Glacier World Zillertal 3000 | `terrain_domain_id`, `name`, `ski_area_refs.*`, `metric_scope` | not-applicable | Owner decision chose not to create a partial shared terrain domain for this PR because the official network scope includes unmodeled areas. |
| Ski & Glacier World Zillertal 3000 | `total_piste_km`, `total_lift_count`, `base_elevation_m`, `summit_elevation_m`, `piste_km_by_difficulty.*`, `season_windows`, `source_urls` | not-applicable | Network facts are summarized on the pass product only; terrain-domain modeling is a follow-up for a broader Zillertal/Mayrhofen curation pass. |

Lift-pass product fields:

| Product | Field | Decision | Note |
| --- | --- | --- | --- |
| Ski & Glacier World Zillertal 3000 / Zillertaler Superskipass | `lift_pass_product_id`, `name` | changed | Added stable product id `ski-glacier-world-zillertal-3000` and official display-oriented name. |
| Ski & Glacier World Zillertal 3000 / Zillertaler Superskipass | `validity_scope` | changed | Modeled as `regional_network` because official validity extends beyond the single local ski area. |
| Ski & Glacier World Zillertal 3000 / Zillertaler Superskipass | `is_default` | changed | Marked as the representative default adult/default product for Hintertux planning. |
| Ski & Glacier World Zillertal 3000 / Zillertaler Superskipass | `valid_ski_area_ids` | changed | Local modeled coverage is limited to `hintertux-glacier`. |
| Ski & Glacier World Zillertal 3000 / Zillertaler Superskipass | `terrain_domain_ids` | not-applicable | No shared terrain domain was created in this PR. |
| Ski & Glacier World Zillertal 3000 / Zillertaler Superskipass | `external_validity_summary` | changed | Captures Eggalm, Rastkogel, Finkenberg, Penken/Mayrhofen, Ahorn, and broader Zillertal validity without copying terrain metrics. |
| Ski & Glacier World Zillertal 3000 / Zillertaler Superskipass | `prices` | changed | Added 1-day, 3-day, and 6-day adult fixed-price examples from official winter 2026/27 tariff data. |

Stay-base fields:

| Stay Base | Field | Decision | Note |
| --- | --- | --- | --- |
| Hintertux | `stay_base_id`, `name` | reviewed-no-change | Stable id/display name preserved. |
| Hintertux | `price_range` | reviewed-no-change | Existing lodging estimate retained; trust remains estimated. |
| Hintertux | `price_min`, `price_max` | not-applicable | Raw catalog omits these by convention; loader derives them from `price_range`. |
| Hintertux | `quality` | reviewed-no-change | Existing premium tier retained; trust remains estimated. |
| Hintertux | `lift_distance` | changed | Updated from `near` to `medium` after OSM distance review. |
| Hintertux | `supported_skill_levels` | reviewed-no-change | Existing compatibility list retained; trust remains estimated. |
| Hintertux | `latitude`, `longitude` | changed | Added OSM village coordinates rounded for catalog consistency. |
| Hintertux | `nearest_lift_name`, `nearest_lift_distance_m` | changed | Added Gletscherbus 1 Talstation and computed 1,074 m distance. |
| Hintertux | `access_mode` | changed | Added `ski_bus` from official bus/valley-station access context plus OSM distance. |
| Hintertux | `base_type` | changed | Added OSM village classification. |
| Hintertux | `atmosphere_tags` | changed | Added official-source-backed glacier/snow-sure/pure-skiing tags. |
| Hintertux | `regional_data_ids` | changed | Added OSM village, OSM lift-station/lift-way, and Wikidata ids. |

Rental fields:

| Rental | Field | Decision | Note |
| --- | --- | --- | --- |
| INTERSPORT Hintertux | `name` | reviewed-no-change | Existing provider example remains source-backed by the current manifest source refs. |
| INTERSPORT Hintertux | `price_range` | unresolved | Existing rental price estimate was not promoted because no reviewed current tariff was added in this sweep. |
| INTERSPORT Hintertux | `price_min`, `price_max` | not-applicable | Raw catalog omits these by convention; loader derives them from `price_range`. |
| INTERSPORT Hintertux | `quality` | unresolved | Existing rental quality tier remains a product estimate. |
| INTERSPORT Hintertux | `lift_distance` | unresolved | Existing rental lift-distance tier remains a product estimate pending rental-specific geometry review. |

## Process Gate

- Classification: `review-gated`.
- Developer Decision Checkpoint: resolved by owner choice to model only a Hintertux pass product with `validity_scope=regional_network` and `external_validity_summary`, without adding a partial shared terrain domain.
- ADR: not needed for this PR because it applies the existing scoped catalog model and ADR rather than introducing a new durable modeling pattern.
- Advisory review: skipped for this draft PR because the change is a source-backed catalog curation with a typed report, owner-resolved scope choice, and draft PR review before merge; run `feature-review` before merge if reviewer sign-off is desired.
