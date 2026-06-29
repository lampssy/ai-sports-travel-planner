# Cervinia Valtournenche Stay-Base Addendum

Added Valtournenche as a second Cervinia stay base within the existing Italian-side Cervinia/Valtournenche ski-area scope. The addendum source-backs the stay-base identity and Salette access geometry with official Cervino pages and OSM objects, while leaving the Cervinia ski-area metrics, lift-pass products, and Matterhorn Ski Paradise terrain-domain links unchanged.

## Changed Fields

| Target | Field | Before | After | Trust | Ranking Relevant |
| --- | --- | --- | --- | --- | --- |
| `destination:cervinia` | `stay_bases` | `["cervinia-breuil-cervinia"]` | `["cervinia-breuil-cervinia", "cervinia-valtournenche"]` | `verified_with_adjustment` | yes |
| `stay_base:cervinia-valtournenche` | `stay_base_id` | `null` | `"cervinia-valtournenche"` | `verified_with_adjustment` | no |
| `stay_base:cervinia-valtournenche` | `name` | `null` | `"Valtournenche"` | `verified` | no |
| `stay_base:cervinia-valtournenche` | `price_range` | `null` | `"EUR 160-240"` | `estimated` | no |
| `stay_base:cervinia-valtournenche` | `quality` | `null` | `"standard"` | `estimated` | no |
| `stay_base:cervinia-valtournenche` | `lift_distance` | `null` | `"medium"` | `verified_with_adjustment` | yes |
| `stay_base:cervinia-valtournenche` | `latitude` | `null` | `45.877` | `verified_with_adjustment` | yes |
| `stay_base:cervinia-valtournenche` | `longitude` | `null` | `7.6228` | `verified_with_adjustment` | yes |
| `stay_base:cervinia-valtournenche` | `nearest_lift_name` | `null` | `"Salette"` | `verified` | yes |
| `stay_base:cervinia-valtournenche` | `nearest_lift_distance_m` | `null` | `1255` | `verified_with_adjustment` | yes |
| `stay_base:cervinia-valtournenche` | `access_mode` | `null` | `"ski_bus"` | `verified_with_adjustment` | yes |
| `stay_base:cervinia-valtournenche` | `base_type` | `null` | `"village"` | `verified` | no |
| `stay_base:cervinia-valtournenche` | `atmosphere_tags` | `null` | `["village", "local_access"]` | `verified_with_adjustment` | no |
| `stay_base:cervinia-valtournenche` | `regional_data_ids` | `null` | `{"nearest_lift_osm_node_id": "342786424", "nearest_lift_osm_way_id": "30833737", "osm_node_id": "5523734363"}` | `verified` | no |
| `stay_base:cervinia-valtournenche` | `supported_skill_levels` | `null` | `["intermediate", "advanced"]` | `estimated` | no |
| `destination:cervinia` | `trust_manifest.source_refs` | `["https://www.cervinia.it/en", "https://www.cervinia.it/en/impianti", "https://drive.google.com/file/d/15SPVS6W4LUnCu5o-ofHpiZgkA6B9Siy1/view?usp=sharing", "https://www.powderhounds.com/Europe/Italy/Cervinia/Ski-Resort.aspx", "https://www.snow-wise.com/our-guide-to/ski-resorts/cervinia/", "https://www.skiresort.info/ski-resort/zermatt-breuil-cervinia-valtournenche-matterhorn/", "https://www.openstreetmap.org/node/253338916", "https://www.openstreetmap.org/node/240324474", "https://whiterent.it/en", "https://whiterent.it/en/ski-rental"]` | `["https://www.cervinia.it/en", "https://www.cervinia.it/en/impianti", "https://drive.google.com/file/d/15SPVS6W4LUnCu5o-ofHpiZgkA6B9Siy1/view?usp=sharing", "https://www.powderhounds.com/Europe/Italy/Cervinia/Ski-Resort.aspx", "https://www.snow-wise.com/our-guide-to/ski-resorts/cervinia/", "https://www.skiresort.info/ski-resort/zermatt-breuil-cervinia-valtournenche-matterhorn/", "https://www.openstreetmap.org/node/253338916", "https://www.openstreetmap.org/node/240324474", "https://www.openstreetmap.org/node/5523734363", "https://www.openstreetmap.org/node/342786424", "https://www.openstreetmap.org/way/30833737", "https://whiterent.it/en", "https://whiterent.it/en/ski-rental"]` | `verified_with_adjustment` | no |
| `destination:cervinia` | `trust_manifest.notes` | `["Official Cervino sources confirm the destination, winter 2026/27 tariff window, lift status/timetable context, and local plus international pass products.", "The catalog keeps ski-area terrain metrics scoped to the Italian-side Cervinia/Valtournenche terrain; Zermatt coverage is represented through the shared Matterhorn Ski Paradise terrain domain on the international pass, not copied into the local ski-area record.", "Stay-base lift access is source-backed with OSM Breuil-Cervinia village and Cretaz lift-station geometry; lodging price, quality, supported-skill, and rental price fields remain product-curated estimates."]` | `["Official Cervino sources confirm the destination, winter 2026/27 tariff window, lift status/timetable context, and local plus international pass products.", "The catalog keeps ski-area terrain metrics scoped to the Italian-side Cervinia/Valtournenche terrain; Zermatt coverage is represented through the shared Matterhorn Ski Paradise terrain domain on the international pass, not copied into the local ski-area record.", "Stay-base lift access is source-backed with OSM Breuil-Cervinia/Cretaz and Valtournenche/Salette geometry; lodging price, quality, supported-skill, and rental price fields remain product-curated estimates."]` | `verified_with_adjustment` | no |

## Field Coverage

| Target | Field | Status | Notes |
| --- | --- | --- | --- |
| `destination:cervinia` | `stay_bases` | `changed` | Added Valtournenche as a second stay-base option under the existing Cervinia destination. |
| `stay_base:cervinia-valtournenche` | `stay_base_id` | `changed` | Added stable stay-base id normalized from the Valtournenche place name. |
| `stay_base:cervinia-valtournenche` | `name` | `changed` | Added source-backed stay-base display name. |
| `stay_base:cervinia-valtournenche` | `price_range` | `changed` | Added conservative estimated lodging range pending a dedicated accommodation sampling policy. |
| `stay_base:cervinia-valtournenche` | `quality` | `changed` | Added standard quality tier as a product-curated estimate. |
| `stay_base:cervinia-valtournenche` | `lift_distance` | `changed` | Added medium bucket from 1255 m OSM Haversine distance to Salette. |
| `stay_base:cervinia-valtournenche` | `latitude` | `changed` | Added rounded OSM settlement coordinate. |
| `stay_base:cervinia-valtournenche` | `longitude` | `changed` | Added rounded OSM settlement coordinate. |
| `stay_base:cervinia-valtournenche` | `nearest_lift_name` | `changed` | Added nearest named lift-station context. |
| `stay_base:cervinia-valtournenche` | `nearest_lift_distance_m` | `changed` | Added computed OSM straight-line access distance. |
| `stay_base:cervinia-valtournenche` | `access_mode` | `changed` | Normalized 1255 m access distance to ski_bus/shuttle-easy rather than walkable. |
| `stay_base:cervinia-valtournenche` | `base_type` | `changed` | Added village base type from OSM settlement classification. |
| `stay_base:cervinia-valtournenche` | `atmosphere_tags` | `changed` | Added conservative source-backed/product-normalized character tags. |
| `stay_base:cervinia-valtournenche` | `regional_data_ids` | `changed` | Added stable OSM object identifiers for the stay base and Salette lift access. |
| `stay_base:cervinia-valtournenche` | `supported_skill_levels` | `changed` | Added intermediate/advanced suitability consistent with the existing Cervinia stay-base scope; remains estimated. |
| `destination:cervinia` | `trust_manifest.source_refs` | `changed` | Added Valtournenche and Salette OSM source references. |
| `destination:cervinia` | `trust_manifest.notes` | `changed` | Updated stay-base access note to cover both Breuil-Cervinia/Cretaz and Valtournenche/Salette. |
| `ski_area:cervinia-ski-area` | `ski_area_id` | `reviewed-no-change` | Valtournenche remains part of the existing Italian-side Cervinia/Valtournenche ski-area scope; no separate ski area added. |
| `ski_area:cervinia-ski-area` | `total_piste_km` | `reviewed-no-change` | Existing 150 km Italian-side Cervinia/Valtournenche metric remains unchanged. |
| `ski_area:cervinia-ski-area` | `total_lift_count` | `reviewed-no-change` | Existing 22-lift Italian-side Cervinia/Valtournenche metric remains unchanged. |
| `lift_pass_product:cervinia-valtournenche-skipass` | `valid_ski_area_ids` | `reviewed-no-change` | Local pass already points at the existing Cervinia ski-area record, which includes Valtournenche. |
| `terrain_domain:matterhorn-ski-paradise` | `ski_area_refs` | `reviewed-no-change` | No terrain-domain change needed because Valtournenche is modeled inside the existing Cervinia ski-area ref. |

## Evidence

| Target | Field | Source | Source Value | Evidence | Normalization |
| --- | --- | --- | --- | --- | --- |
| `destination:cervinia` | `stay_bases` | [Cervino lifts and slopes](https://www.cervinia.it/en/impianti) | `"Lifts and slopes Cervino Ski Paradise: Breuil-Cervinia, Valtournenche, Chamois, Torgnon and Zermatt."` | Official Cervino lift/slopes page lists Valtournenche within the Cervino Ski Paradise operating context. | Official place names and OSM geometry are normalized into stable Snowcast stay_base_id values. |
| `stay_base:cervinia-valtournenche` | `stay_base_id` | [OpenStreetMap Valtournenche village node](https://www.openstreetmap.org/node/5523734363) | `"Valtournenche"` | OSM provides a named Valtournenche settlement node. | The source place name is normalized to the stable Snowcast id cervinia-valtournenche. |
| `stay_base:cervinia-valtournenche` | `name` | [OpenStreetMap Valtournenche village node](https://www.openstreetmap.org/node/5523734363) | `"Valtournenche"` | OSM names the settlement Valtournenche. |  |
| `stay_base:cervinia-valtournenche` | `lift_distance` | [OpenStreetMap Salette lift station](https://www.openstreetmap.org/node/342786424) | `1255` | Computed Haversine distance from the OSM Valtournenche village node to the OSM Salette lift-station node is 1255 m. | 1255 m is normalized to lift_distance=medium. |
| `stay_base:cervinia-valtournenche` | `latitude` | [OpenStreetMap Valtournenche village node](https://www.openstreetmap.org/node/5523734363) | `45.8769793` | OSM gives the Valtournenche village node latitude as 45.8769793. | Coordinate is rounded to four decimals in the static catalog. |
| `stay_base:cervinia-valtournenche` | `longitude` | [OpenStreetMap Valtournenche village node](https://www.openstreetmap.org/node/5523734363) | `7.622792` | OSM gives the Valtournenche village node longitude as 7.6227920. | Coordinate is rounded to four decimals in the static catalog. |
| `stay_base:cervinia-valtournenche` | `nearest_lift_name` | [OpenStreetMap Salette lift station](https://www.openstreetmap.org/node/342786424) | `"Salette"` | OSM identifies the nearest access station as Salette. |  |
| `stay_base:cervinia-valtournenche` | `nearest_lift_distance_m` | [OpenStreetMap Salette lift station](https://www.openstreetmap.org/node/342786424) | `1255` | Computed Haversine distance from the OSM Valtournenche village node to the OSM Salette lift-station node is 1255 m. |  |
| `stay_base:cervinia-valtournenche` | `access_mode` | [OpenStreetMap Salette lift station](https://www.openstreetmap.org/node/342786424) | `1255` | OSM geometry puts the Valtournenche village coordinate 1255 m from the Salette lift-station node. | Distance is normalized to access_mode=ski_bus, which maps to shuttle-easy stay-base access in Snowcast scoring. |
| `stay_base:cervinia-valtournenche` | `base_type` | [OpenStreetMap Valtournenche village node](https://www.openstreetmap.org/node/5523734363) | `"village"` | OSM classifies Valtournenche as a village place node. |  |
| `stay_base:cervinia-valtournenche` | `atmosphere_tags` | [Cervino lifts and slopes](https://www.cervinia.it/en/impianti) | `"Valtournenche appears as a named Cervino Ski Paradise lift/slopes sector; OSM classifies the settlement as a village."` | Official Cervino and OSM context supports modeling Valtournenche as a village stay base with local Cervinia/Valtournenche access. | Source context is normalized into conservative Snowcast atmosphere tags. |
| `stay_base:cervinia-valtournenche` | `regional_data_ids` | [OpenStreetMap Salette gondola way](https://www.openstreetmap.org/way/30833737) | `{"nearest_lift_osm_node_id": "342786424", "nearest_lift_osm_way_id": "30833737", "osm_node_id": "5523734363"}` | OSM provides stable identifiers for the Valtournenche village node, Salette valley-station node, and Salette gondola way. |  |
| `destination:cervinia` | `trust_manifest.source_refs` | [OpenStreetMap Valtournenche village node](https://www.openstreetmap.org/node/5523734363) | `["https://www.cervinia.it/en", "https://www.cervinia.it/en/impianti", "https://drive.google.com/file/d/15SPVS6W4LUnCu5o-ofHpiZgkA6B9Siy1/view?usp=sharing", "https://www.powderhounds.com/Europe/Italy/Cervinia/Ski-Resort.aspx", "https://www.snow-wise.com/our-guide-to/ski-resorts/cervinia/", "https://www.skiresort.info/ski-resort/zermatt-breuil-cervinia-valtournenche-matterhorn/", "https://www.openstreetmap.org/node/253338916", "https://www.openstreetmap.org/node/240324474", "https://www.openstreetmap.org/node/5523734363", "https://www.openstreetmap.org/node/342786424", "https://www.openstreetmap.org/way/30833737", "https://whiterent.it/en", "https://whiterent.it/en/ski-rental"]` | Valtournenche and Salette OSM references were added to the Cervinia trust manifest source list. |  |
| `destination:cervinia` | `trust_manifest.notes` | [OpenStreetMap Salette lift station](https://www.openstreetmap.org/node/342786424) | `["Official Cervino sources confirm the destination, winter 2026/27 tariff window, lift status/timetable context, and local plus international pass products.", "The catalog keeps ski-area terrain metrics scoped to the Italian-side Cervinia/Valtournenche terrain; Zermatt coverage is represented through the shared Matterhorn Ski Paradise terrain domain on the international pass, not copied into the local ski-area record.", "Stay-base lift access is source-backed with OSM Breuil-Cervinia/Cretaz and Valtournenche/Salette geometry; lodging price, quality, supported-skill, and rental price fields remain product-curated estimates."]` | The manifest note now matches the added Valtournenche/Salette stay-base evidence. |  |

## Ranking Impact

Default comparison diagnostics wrote 12 rows to artifacts/ranking-comparison. Cervinia is not part of the current default comparison scenario set, so no rank movement row was emitted for this addendum; the edited static catalog nevertheless changes ranking-relevant stay-base access fields for future Cervinia-covered scenarios.

## Verification

- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_catalog_curation --report-path docs/catalog-curation/2026-06-29-cervinia-valtournenche-stay-base.json --markdown-output docs/catalog-curation/2026-06-29-cervinia-valtournenche-stay-base.md`
- `UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.compare_ranking --output-dir artifacts/ranking-comparison`
- `UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_catalog_validation.py tests/test_catalog_curation.py -q`
- `git diff --check`

## Caveats

- Valtournenche lodging price range, quality tier, and supported skill levels remain product-curated estimates pending a dedicated accommodation sampling policy.
- The 1255 m lift-access value is a Haversine distance from the OSM Valtournenche village node to the OSM Salette valley-station node, not a walking-route distance.
- No separate Valtournenche ski-area record is created in this addendum because the current catalog models the Italian-side Cervinia/Valtournenche terrain as one ski area.
