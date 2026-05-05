# Source Cascade Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend resort catalog acquisition so one artifact-only run gathers Wikidata, OSM, OpenDataHub, DEM, and official-site evidence, then writes one consolidated field-level review packet.

**Architecture:** Keep approved catalog truth git-canonical and keep `proposals.json` per-candidate. Add provider adapters that emit `CandidateFact`s and a run-local source context that lets discovered sources feed later adapters without becoming approved catalog values. Use static HTML/sitemap official-link discovery plus bounded LLM link classification; no browser-rendered crawling.

**Tech Stack:** Python 3.11+, Pydantic v2, `httpx`, standard-library `html.parser`, `xml.etree.ElementTree`, existing Gemini/LLM client abstraction, existing `uv`/pytest/ruff workflow.

---

## File Structure

- Create `app/data/resort_acquisition/source_context.py`: run-local source seeds, discovered URL/ID candidates, and helpers for effective official URLs.
- Create `app/data/resort_acquisition/targeting.py`: shared destination/ski-area targeting and mirror rules now embedded in OpenDataHub extraction.
- Create `app/data/resort_acquisition/wikidata.py`: fetch URL constants and deterministic extraction from `Special:EntityData/{qid}.json`.
- Create `app/data/resort_acquisition/osm.py`: Overpass relation lookup URL/query builder and coordinate extraction.
- Create `app/data/resort_acquisition/dem.py`: OpenTopoData request building, response parsing, and DEM warning candidate generation.
- Create `app/data/resort_acquisition/official_links.py`: static homepage/sitemap fetch parsing, anchor extraction, deterministic role scoring, domain safety checks.
- Create `app/data/resort_acquisition/link_classify.py`: bounded LLM classification and cache for official link candidates.
- Modify `app/data/resort_acquisition/models.py`: add extraction methods/source types, warning status, source-candidate/link models.
- Modify `app/data/resort_acquisition/extractors.py`: move shared targeting code to `targeting.py`, add OpenDataHub contact URL extraction as a discovered official homepage seed.
- Modify `app/data/resort_acquisition/proposals.py`: preserve target-aware comparison and support warning candidates.
- Modify `app/data/resort_acquisition/reports.py`: render grouped field-level evidence while preserving machine-readable proposals.
- Modify `app/data/resort_acquisition/run_catalog_acquisition.py`: orchestrate the source cascade and add skip flags.
- Modify `tests/test_resort_acquisition.py`: add mocked tests for every new adapter and cascade behavior.
- Modify `README.md`, `docs/engineering-notes.md`, and `.github/workflows/catalog-acquisition.yml`: document Sprint 30 acquisition behavior and expose relevant CLI options.

---

### Task 1: Shared Models, Warning Status, and Targeting Helpers

**Files:**
- Modify: `app/data/resort_acquisition/models.py`
- Modify: `app/data/resort_acquisition/proposals.py`
- Modify: `app/data/resort_acquisition/extractors.py`
- Create: `app/data/resort_acquisition/targeting.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing tests for warning proposals and shared mirror targeting**

Add tests near existing proposal-target tests:

```python
def test_build_proposals_marks_warning_candidate() -> None:
    source = SourceReference(source_type="dem", source_url="https://api.opentopodata.org/v1/eudem25m")
    fetched_at = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)
    raw_catalog = {
        "test-resort": {
            "resort_id": "test-resort",
            "ski_areas": [
                {"ski_area_id": "test-ski-area", "base_elevation_m": 1500}
            ],
        }
    }

    proposals = build_proposals(
        raw_catalog,
        [
            CandidateFact(
                resort_id="test-resort",
                target=ProposalTarget(entity_type="ski_area", entity_id="test-ski-area"),
                field_path="base_elevation_m",
                proposed_value=1500,
                source=source,
                extraction_method="dem",
                fetched_at=fetched_at,
                confidence=0.6,
                validation_status="warning",
                validation_notes=[
                    "DEM point elevation 730m is far below catalog base elevation 1500m"
                ],
            )
        ],
    )

    assert proposals[0].status == "warning"
    assert proposals[0].current_value == 1500
    assert proposals[0].validation_notes == [
        "DEM point elevation 730m is far below catalog base elevation 1500m"
    ]


def test_targeting_mirrors_single_ski_area_duplicate_destination_field() -> None:
    resort_payload = {
        "resort_id": "alta-badia",
        "latitude": 46.5536,
        "ski_areas": [{"ski_area_id": "alta-badia-ski-area", "latitude": 46.5536}],
    }

    targets = proposal_targets_for_single_area_source(
        resort_id="alta-badia",
        resort_payload=resort_payload,
        field_path="latitude",
        primary_entity_type="ski_area",
    )

    assert targets == [
        ProposalTarget(entity_type="ski_area", entity_id="alta-badia-ski-area"),
        ProposalTarget(entity_type="destination", entity_id="alta-badia"),
    ]
```

Also import `proposal_targets_for_single_area_source` from the new `targeting.py`.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_build_proposals_marks_warning_candidate tests/test_resort_acquisition.py::test_targeting_mirrors_single_ski_area_duplicate_destination_field -q
```

Expected: failures because `dem`/`warning`/`targeting.py` do not exist yet.

- [ ] **Step 3: Implement model and targeting changes**

In `models.py`:

- extend `ExtractionMethod` with `"wikidata"`, `"osm"`, `"dem"`, `"official_link_discovery"`, and `"official_link_llm"`.
- extend `SourceType` with `"dem"`.
- extend `ProposalStatus` with `"warning"`.
- extend `CandidateFact.validation_status` to `Literal["accepted", "rejected", "warning"]`.

Create `targeting.py` with:

```python
from __future__ import annotations

from typing import Any, Literal

from app.data.resort_acquisition.models import ProposalTarget

PrimaryEntityType = Literal["destination", "ski_area"]


def single_ski_area_payload(resort_payload: dict[str, Any]) -> dict[str, Any] | None:
    ski_areas = resort_payload.get("ski_areas")
    if not isinstance(ski_areas, list) or len(ski_areas) != 1:
        return None
    ski_area = ski_areas[0]
    return ski_area if isinstance(ski_area, dict) else None


def proposal_targets_for_single_area_source(
    *,
    resort_id: str,
    resort_payload: dict[str, Any],
    field_path: str,
    primary_entity_type: PrimaryEntityType,
) -> list[ProposalTarget]:
    targets: list[ProposalTarget] = []
    ski_area = single_ski_area_payload(resort_payload)
    if primary_entity_type == "destination":
        targets.append(ProposalTarget(entity_type="destination", entity_id=resort_id))
        if _can_mirror(resort_payload, ski_area, field_path):
            targets.append(
                ProposalTarget(
                    entity_type="ski_area",
                    entity_id=str(ski_area["ski_area_id"]),
                )
            )
        return targets

    if ski_area is None:
        return []
    targets.append(
        ProposalTarget(entity_type="ski_area", entity_id=str(ski_area["ski_area_id"]))
    )
    if _can_mirror(resort_payload, ski_area, field_path):
        targets.append(ProposalTarget(entity_type="destination", entity_id=resort_id))
    return targets


def _can_mirror(
    resort_payload: dict[str, Any],
    ski_area: dict[str, Any] | None,
    field_path: str,
) -> bool:
    return (
        ski_area is not None
        and isinstance(ski_area.get("ski_area_id"), str)
        and field_path in resort_payload
        and field_path in ski_area
        and resort_payload[field_path] == ski_area[field_path]
    )
```

In `proposals.py`, set proposal `status = "warning"` when `candidate.validation_status == "warning"` before same/changed comparison.

In `extractors.py`, replace local `_single_ski_area_payload` and `_destination_field_is_single_ski_area_duplicate` logic with `proposal_targets_for_single_area_source(primary_entity_type="ski_area")`.

- [ ] **Step 4: Run tests to verify green**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_build_proposals_marks_warning_candidate tests/test_resort_acquisition.py::test_targeting_mirrors_single_ski_area_duplicate_destination_field -q
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/data/resort_acquisition/models.py app/data/resort_acquisition/proposals.py app/data/resort_acquisition/extractors.py app/data/resort_acquisition/targeting.py tests/test_resort_acquisition.py
git commit -m "feat: add source cascade proposal targeting primitives"
```

---

### Task 2: Wikidata Adapter

**Files:**
- Create: `app/data/resort_acquisition/wikidata.py`
- Modify: `app/data/resort_acquisition/models.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing Wikidata extraction tests**

Add tests:

```python
def _wikidata_entity_payload() -> dict[str, object]:
    return {
        "entities": {
            "Q123": {
                "claims": {
                    "P856": [
                        {
                            "rank": "normal",
                            "mainsnak": {
                                "datavalue": {
                                    "value": "https://www.example-resort.com",
                                    "type": "string",
                                }
                            },
                        }
                    ],
                    "P625": [
                        {
                            "rank": "normal",
                            "mainsnak": {
                                "datavalue": {
                                    "value": {
                                        "latitude": 46.55,
                                        "longitude": 11.75,
                                    },
                                    "type": "globecoordinate",
                                }
                            },
                        }
                    ],
                    "P402": [
                        {
                            "rank": "normal",
                            "mainsnak": {
                                "datavalue": {
                                    "value": "123456",
                                    "type": "string",
                                }
                            },
                        }
                    ],
                }
            }
        }
    }


def test_extract_wikidata_candidates_maps_official_url_coordinates_and_osm_id() -> None:
    resort_payload = {
        "resort_id": "test-resort",
        "latitude": 46.0,
        "longitude": 11.0,
        "ski_areas": [
            {
                "ski_area_id": "test-ski-area",
                "latitude": 46.0,
                "longitude": 11.0,
            }
        ],
    }

    candidates = extract_wikidata_candidates(
        resort_id="test-resort",
        wikidata_id="Q123",
        payload=_wikidata_entity_payload(),
        fetched_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        source_url="https://www.wikidata.org/wiki/Special:EntityData/Q123.json",
        resort_payload=resort_payload,
    )

    values = {
        (candidate.target.entity_type, candidate.target.entity_id, candidate.field_path): candidate.proposed_value
        for candidate in candidates
    }
    assert values[("destination", "test-resort", "ski_area_official_url")] == "https://www.example-resort.com"
    assert values[("destination", "test-resort", "regional_data_ids.osm_relation_id")] == "123456"
    assert values[("destination", "test-resort", "latitude")] == 46.55
    assert values[("destination", "test-resort", "longitude")] == 11.75
    assert values[("ski_area", "test-ski-area", "latitude")] == 46.55
    assert values[("ski_area", "test-ski-area", "longitude")] == 11.75
    assert all(candidate.extraction_method == "wikidata" for candidate in candidates)
    assert all(candidate.source.source_type == "wikidata" for candidate in candidates)


def test_extract_wikidata_candidates_ignores_malformed_claims() -> None:
    candidates = extract_wikidata_candidates(
        resort_id="test-resort",
        wikidata_id="Q123",
        payload={"entities": {"Q123": {"claims": {"P625": [{"mainsnak": {}}]}}}},
        fetched_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        source_url="https://www.wikidata.org/wiki/Special:EntityData/Q123.json",
        resort_payload={"resort_id": "test-resort", "ski_areas": []},
    )

    assert candidates == []
```

Import `extract_wikidata_candidates`.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_extract_wikidata_candidates_maps_official_url_coordinates_and_osm_id tests/test_resort_acquisition.py::test_extract_wikidata_candidates_ignores_malformed_claims -q
```

Expected: import failure for `app.data.resort_acquisition.wikidata`.

- [ ] **Step 3: Implement `wikidata.py`**

Implement these constants:

- `WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"`
- `WIKIDATA_OFFICIAL_WEBSITE = "P856"`
- `WIKIDATA_COORDINATE_LOCATION = "P625"`
- `WIKIDATA_OSM_RELATION_ID = "P402"`

Implement `wikidata_entity_url(wikidata_id: str) -> str` so it returns `WIKIDATA_ENTITY_URL.format(wikidata_id=wikidata_id)`.

Implement `extract_wikidata_candidates(*, resort_id: str, wikidata_id: str, payload: dict[str, Any], fetched_at: datetime, source_url: str, resort_payload: dict[str, Any]) -> list[CandidateFact]`.

Extraction rules:

- Read `payload["entities"][wikidata_id]["claims"]`.
- Prefer claims whose `rank != "deprecated"`.
- Use the first valid claim per property.
- `P856`: string URL -> destination target `ski_area_official_url`, confidence `0.85`.
- `P402`: string/int relation ID -> destination target `regional_data_ids.osm_relation_id`, confidence `0.85`.
- `P625`: `{latitude, longitude}` -> destination coordinate candidates plus ski-area mirror candidates when `proposal_targets_for_single_area_source` is called with `primary_entity_type="destination"` and returns a ski-area target.
- Evidence strings must name the property, for example `Wikidata P625 coordinate location latitude=46.55, longitude=11.75`.

- [ ] **Step 4: Run tests to verify green**

Run the same two tests. Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add app/data/resort_acquisition/wikidata.py tests/test_resort_acquisition.py
git commit -m "feat: add wikidata resort acquisition adapter"
```

---

### Task 3: OSM Adapter

**Files:**
- Create: `app/data/resort_acquisition/osm.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing OSM extraction tests**

Add:

```python
def test_extract_osm_candidates_maps_relation_center_to_coordinates() -> None:
    payload = {
        "elements": [
            {
                "type": "relation",
                "id": 123456,
                "center": {"lat": 46.551, "lon": 11.751},
                "tags": {"name": "Test Resort"},
            }
        ]
    }
    resort_payload = {
        "resort_id": "test-resort",
        "latitude": 46.0,
        "longitude": 11.0,
        "ski_areas": [
            {"ski_area_id": "test-ski-area", "latitude": 46.0, "longitude": 11.0}
        ],
    }

    candidates = extract_osm_relation_candidates(
        resort_id="test-resort",
        osm_relation_id="123456",
        payload=payload,
        fetched_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        source_url="https://overpass-api.de/api/interpreter",
        resort_payload=resort_payload,
    )

    values = {
        (candidate.target.entity_type, candidate.target.entity_id, candidate.field_path): candidate.proposed_value
        for candidate in candidates
    }
    assert values[("destination", "test-resort", "latitude")] == 46.551
    assert values[("destination", "test-resort", "longitude")] == 11.751
    assert values[("ski_area", "test-ski-area", "latitude")] == 46.551
    assert values[("ski_area", "test-ski-area", "longitude")] == 11.751
    assert all(candidate.extraction_method == "osm" for candidate in candidates)


def test_extract_osm_relation_candidates_ignores_missing_center() -> None:
    candidates = extract_osm_relation_candidates(
        resort_id="test-resort",
        osm_relation_id="123456",
        payload={"elements": [{"type": "relation", "id": 123456}]},
        fetched_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        source_url="https://overpass-api.de/api/interpreter",
        resort_payload={"resort_id": "test-resort", "ski_areas": []},
    )

    assert candidates == []
```

Import `extract_osm_relation_candidates`.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_extract_osm_candidates_maps_relation_center_to_coordinates tests/test_resort_acquisition.py::test_extract_osm_relation_candidates_ignores_missing_center -q
```

Expected: import failure.

- [ ] **Step 3: Implement `osm.py`**

Implement:

```python
OVERPASS_INTERPRETER_URL = "https://overpass-api.de/api/interpreter"

def overpass_relation_query(osm_relation_id: str) -> str:
    return f"[out:json][timeout:25];relation({osm_relation_id});out center tags;"
```

Also implement `extract_osm_relation_candidates(*, resort_id: str, osm_relation_id: str, payload: dict[str, Any], fetched_at: datetime, source_url: str, resort_payload: dict[str, Any]) -> list[CandidateFact]`.

Extraction rules:

- Find the first element with `type == "relation"` and `id == int(osm_relation_id)`.
- Use `element["center"]["lat"]` and `element["center"]["lon"]` if finite and plausible.
- Treat OSM relation coordinates as destination-scoped primary and mirror to a single duplicated ski area using `proposal_targets_for_single_area_source` with `primary_entity_type="destination"`.
- Evidence must include `OpenStreetMap relation <id> center lat=<lat>, lon=<lon>`.

- [ ] **Step 4: Run tests to verify green**

Run the same two tests. Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add app/data/resort_acquisition/osm.py tests/test_resort_acquisition.py
git commit -m "feat: add osm resort acquisition adapter"
```

---

### Task 4: DEM Sanity Adapter

**Files:**
- Create: `app/data/resort_acquisition/dem.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing DEM tests**

Add:

```python
def test_dem_builds_batched_opentopodata_url() -> None:
    url = opentopodata_url(
        dataset_stack="eudem25m,mapzen,srtm90m",
        points=[CoordinatePoint(target_key="a", latitude=46.5, longitude=11.7)],
    )

    assert url.startswith("https://api.opentopodata.org/v1/eudem25m,mapzen,srtm90m?")
    assert "locations=46.5%2C11.7" in url


def test_extract_dem_candidates_warns_when_point_elevation_far_from_base() -> None:
    resort_payload = {
        "resort_id": "test-resort",
        "ski_areas": [
            {
                "ski_area_id": "test-ski-area",
                "latitude": 46.5,
                "longitude": 11.7,
                "base_elevation_m": 1500,
                "summit_elevation_m": 2500,
            }
        ],
    }
    payload = {
        "status": "OK",
        "results": [
            {
                "elevation": 730.0,
                "location": {"lat": 46.5, "lng": 11.7},
                "dataset": "eudem25m",
            }
        ],
    }

    candidates = extract_dem_sanity_candidates(
        resort_id="test-resort",
        resort_payload=resort_payload,
        payload=payload,
        fetched_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        source_url="https://api.opentopodata.org/v1/eudem25m,mapzen,srtm90m",
    )

    assert len(candidates) == 1
    assert candidates[0].target.entity_type == "ski_area"
    assert candidates[0].field_path == "base_elevation_m"
    assert candidates[0].proposed_value == 1500
    assert candidates[0].validation_status == "warning"
    assert "DEM point elevation 730m" in candidates[0].validation_notes[0]
```

Import `CoordinatePoint`, `opentopodata_url`, and `extract_dem_sanity_candidates`.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_dem_builds_batched_opentopodata_url tests/test_resort_acquisition.py::test_extract_dem_candidates_warns_when_point_elevation_far_from_base -q
```

Expected: import failure.

- [ ] **Step 3: Implement `dem.py`**

Implement:

```python
OPENTOPODATA_BASE_URL = "https://api.opentopodata.org/v1"
DEFAULT_DEM_DATASET_STACK = "eudem25m,mapzen,srtm90m"
DEM_BASE_ELEVATION_WARNING_THRESHOLD_M = 500

@dataclass(frozen=True)
class CoordinatePoint:
    target_key: str
    latitude: float
    longitude: float
```

Also implement these functions:

- `catalog_ski_area_points(resort_payload: dict[str, Any]) -> list[CoordinatePoint]`
- `opentopodata_url(*, dataset_stack: str, points: list[CoordinatePoint]) -> str`
- `extract_dem_sanity_candidates(*, resort_id: str, payload: dict[str, Any], fetched_at: datetime, source_url: str, resort_payload: dict[str, Any], dataset_stack: str = DEFAULT_DEM_DATASET_STACK) -> list[CandidateFact]`

Rules:

- Generate one point per catalog `ski_areas[]` entry with valid coordinates.
- URL-encode `locations` as `lat,lon|lat,lon`.
- For each OpenTopoData result, compare rounded DEM elevation to catalog `base_elevation_m`.
- If `abs(dem_elevation - base_elevation_m) > 500`, emit a warning `CandidateFact` targeted at the ski area’s `base_elevation_m`, with `proposed_value` equal to the catalog base value.
- If within threshold, emit no candidate to avoid noise.
- Evidence string: `OpenTopoData point elevation=<elevation>m at <lat>,<lon>; dataset=<dataset>`.

- [ ] **Step 4: Run tests to verify green**

Run the same two tests. Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add app/data/resort_acquisition/dem.py tests/test_resort_acquisition.py
git commit -m "feat: add dem sanity checks for resort acquisition"
```

---

### Task 5: Static Official Link Discovery

**Files:**
- Create: `app/data/resort_acquisition/official_links.py`
- Modify: `app/data/resort_acquisition/fetching.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing official-link tests**

Add:

```python
def test_extract_official_links_from_html_normalizes_and_scores_roles() -> None:
    html = """
    <html>
      <head><title>Winter Resort</title></head>
      <body>
        <a href="/en/skipass-prices" title="Ski pass prices">Tariffe skipass</a>
        <a href="https://tickets.example.com/buy">Buy tickets</a>
        <a href="/summer">Summer</a>
      </body>
    </html>
    """

    links = extract_link_candidates_from_html(
        html=html,
        source_url="https://www.example.com/en",
        official_seed_url="https://www.example.com",
    )

    by_url = {link.url: link for link in links}
    assert "https://www.example.com/en/skipass-prices" in by_url
    assert by_url["https://www.example.com/en/skipass-prices"].deterministic_scores["ski_pass"] > 0
    assert by_url["https://tickets.example.com/buy"].is_external is True


def test_parse_sitemap_urls_keeps_same_host_and_caps_results() -> None:
    xml = "<urlset>" + "".join(
        f"<url><loc>https://www.example.com/page-{index}</loc></url>"
        for index in range(45)
    ) + "</urlset>"

    urls = parse_sitemap_urls(
        xml,
        official_seed_url="https://www.example.com",
        max_urls=40,
    )

    assert len(urls) == 40
    assert urls[0] == "https://www.example.com/page-0"
```

Import `extract_link_candidates_from_html` and `parse_sitemap_urls`.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_extract_official_links_from_html_normalizes_and_scores_roles tests/test_resort_acquisition.py::test_parse_sitemap_urls_keeps_same_host_and_caps_results -q
```

Expected: import failure.

- [ ] **Step 3: Implement static link parsing**

In `fetching.py`, add `FetchedHtmlDocument` and `fetch_html_document()` using the existing `get_with_transport_retries`, `_USER_AGENT`, content-type guard, and byte cap. Return raw HTML plus visible text and content hash.

In `official_links.py`, implement:

```python
OFFICIAL_LINK_ROLES = ("ski_pass", "season_dates", "trail_map", "official_status", "rental")
MAX_LINK_CANDIDATES_PER_RESORT = 100
MAX_SITEMAP_URLS_PER_RESORT = 40
MAX_FIRST_LEVEL_PAGES_PER_RESORT = 20

@dataclass(frozen=True)
class OfficialLinkCandidate:
    url: str
    source_page_url: str
    official_seed_url: str
    link_text: str
    title: str | None
    aria_label: str | None
    nearby_text: str
    source_page_title: str | None
    is_external: bool
    deterministic_scores: dict[str, float]
```

Implement same-host/direct-subdomain safety with `urllib.parse`.

Keyword scoring must include at least:

- `ski_pass`: `skipass`, `ski pass`, `ticket`, `prices`, `tariff`, `tariffe`, `preise`, `forfait`
- `season_dates`: `opening`, `season`, `winter`, `operating`, `öffnungszeiten`, `ouverture`, `apertura`
- `trail_map`: `map`, `piste map`, `skimaps`, `panorama`, `pistenplan`, `plan des pistes`
- `official_status`: `snow report`, `lifts`, `slopes`, `open`, `live`, `impianti`, `remontées`
- `rental`: `rental`, `hire`, `equipment`, `noleggio`, `verleih`, `location ski`

- [ ] **Step 4: Run tests to verify green**

Run the same two tests. Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add app/data/resort_acquisition/fetching.py app/data/resort_acquisition/official_links.py tests/test_resort_acquisition.py
git commit -m "feat: add static official link discovery"
```

---

### Task 6: LLM Link Classification

**Files:**
- Create: `app/data/resort_acquisition/link_classify.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing LLM link-classification tests**

Add:

```python
def test_classify_official_links_with_llm_validates_urls_and_roles(tmp_path) -> None:
    links = [
        OfficialLinkCandidate(
            url="https://www.example.com/it/tariffe-skipass",
            source_page_url="https://www.example.com",
            official_seed_url="https://www.example.com",
            link_text="Tariffe skipass",
            title=None,
            aria_label=None,
            nearby_text="Prezzi per adulti",
            source_page_title="Inverno",
            is_external=False,
            deterministic_scores={"ski_pass": 0.8},
        )
    ]
    client = ConfigurableFakeLLMClient(
        response=json.dumps(
            {
                "roles": {
                    "ski_pass": [
                        {
                            "url": "https://www.example.com/it/tariffe-skipass",
                            "confidence": 0.93,
                            "reason": "Italian label means ski pass tariffs",
                            "language_hint": "it",
                        }
                    ]
                }
            }
        )
    )

    classified, errors = classify_official_links_with_llm(
        resort_id="test-resort",
        link_candidates=links,
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert errors == []
    assert classified["ski_pass"][0].url == "https://www.example.com/it/tariffe-skipass"
    assert classified["ski_pass"][0].confidence == 0.93
    assert client.call_count == 1


def test_classify_official_links_rejects_unknown_url(tmp_path) -> None:
    links = []
    client = ConfigurableFakeLLMClient(
        response=json.dumps(
            {
                "roles": {
                    "ski_pass": [
                        {
                            "url": "https://evil.example.com",
                            "confidence": 0.9,
                            "reason": "bad",
                        }
                    ]
                }
            }
        )
    )

    classified, errors = classify_official_links_with_llm(
        resort_id="test-resort",
        link_candidates=links,
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert classified == {}
    assert errors == ["LLM link classification returned unknown URL: https://evil.example.com"]
```

Import `classify_official_links_with_llm` and `OfficialLinkCandidate`.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_classify_official_links_with_llm_validates_urls_and_roles tests/test_resort_acquisition.py::test_classify_official_links_rejects_unknown_url -q
```

Expected: import failure.

- [ ] **Step 3: Implement `link_classify.py`**

Implement:

- `PROMPT_VERSION = "official-link-classifier-v1"`
- `SCHEMA_VERSION = "official-link-classifier-schema-v1"`
- `ClassifiedOfficialLink` Pydantic model with `url`, `confidence`, `reason`, `language_hint`.
- `classify_official_links_with_llm(*, resort_id: str, link_candidates: list[OfficialLinkCandidate], llm_client: Any, cache_dir: Path, model: str | None = None) -> tuple[dict[str, list[ClassifiedOfficialLink]], list[str]]`.
- Strict role set from `OFFICIAL_LINK_ROLES`.
- Cache key built from resort ID, sorted link candidate JSON, prompt version, schema version, and model.
- JSON schema that requires `roles` object and per-link `url`, `confidence`, and `reason`.
- Reject any URL that was not present in input candidates.
- Return cached classification without incrementing the fake client call count on a second invocation.

- [ ] **Step 4: Run tests to verify green**

Run the same two tests. Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add app/data/resort_acquisition/link_classify.py tests/test_resort_acquisition.py
git commit -m "feat: add llm official link classification"
```

---

### Task 7: Runner Source Cascade and Skip Flags

**Files:**
- Create: `app/data/resort_acquisition/source_context.py`
- Modify: `app/data/resort_acquisition/run_catalog_acquisition.py`
- Modify: `app/data/resort_acquisition/extractors.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing runner tests for same-run cascade**

Add:

```python
def test_catalog_acquisition_uses_wikidata_official_url_as_same_run_discovery_seed(
    tmp_path,
    monkeypatch,
) -> None:
    registry_path = tmp_path / "sources.json"
    catalog_path = tmp_path / "resorts.json"
    output_dir = tmp_path / "out"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "resorts": {
                    "test-resort": {
                        "regional_data_ids": {"wikidata_id": "Q123"},
                        "official_urls": {},
                    }
                },
            }
        )
    )
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "test-resort",
                    "name": "Test Resort",
                    "country": "Italy",
                    "latitude": 46.0,
                    "longitude": 11.0,
                    "ski_areas": [
                        {
                            "ski_area_id": "test-ski-area",
                            "latitude": 46.0,
                            "longitude": 11.0,
                            "base_elevation_m": 1500,
                            "summit_elevation_m": 2500,
                        }
                    ],
                }
            ]
        )
    )

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._extract_opendatahub_discovery",
        lambda *args, **kwargs: ([], None),
    )
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._fetch_json_value",
        fake_fetch_json_value_for_wikidata_q123,
    )
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.discover_official_links_for_resort",
        lambda **kwargs: (
            [
                OfficialLinkCandidate(
                    url="https://www.example-resort.com/prices",
                    source_page_url="https://www.example-resort.com",
                    official_seed_url="https://www.example-resort.com",
                    link_text="Ski pass prices",
                    title=None,
                    aria_label=None,
                    nearby_text="Adult prices",
                    source_page_title="Home",
                    is_external=False,
                    deterministic_scores={"ski_pass": 0.9},
                )
            ],
            [],
        ),
    )

    exit_code = acquisition_main(
        [
            "--resort",
            "test-resort",
            "--registry-path",
            str(registry_path),
            "--catalog-path",
            str(catalog_path),
            "--output-dir",
            str(output_dir),
            "--skip-opendatahub",
            "--skip-osm",
            "--skip-dem",
            "--skip-llm",
        ]
    )

    assert exit_code == 0
    proposals = json.loads((output_dir / "proposals.json").read_text())
    field_paths = {proposal["field_path"] for proposal in proposals["proposals"]}
    assert "ski_area_official_url" in field_paths
    assert "ski_pass_url" in field_paths
```

Add this helper beside the runner tests:

```python
def fake_fetch_json_value_for_wikidata_q123(
    resort_id: str,
    url: str,
    started_at: datetime,
    *,
    extraction_method: ExtractionMethod,
) -> tuple[object | None, FetchLogEntry]:
    assert resort_id == "test-resort"
    assert url == "https://www.wikidata.org/wiki/Special:EntityData/Q123.json"
    assert extraction_method == "wikidata"
    return _wikidata_entity_payload(), FetchLogEntry(
        resort_id=resort_id,
        url=url,
        fetched_at=started_at,
        status="success",
        status_code=200,
        extraction_method=extraction_method,
        content_hash="wikidata-q123",
    )
```

Add skip-flag tests:

```python
def test_catalog_acquisition_skip_wikidata_disables_wikidata_fetch(tmp_path, monkeypatch) -> None:
    registry_path = tmp_path / "sources.json"
    catalog_path = tmp_path / "resorts.json"
    output_dir = tmp_path / "out"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "resorts": {
                    "test-resort": {
                        "regional_data_ids": {"wikidata_id": "Q123"},
                        "official_urls": {},
                    }
                },
            }
        )
    )
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "test-resort",
                    "name": "Test Resort",
                    "country": "Italy",
                    "region": "Test",
                    "latitude": 46.0,
                    "longitude": 11.0,
                    "ski_areas": [],
                }
            ]
        )
    )

    def fail_if_called(
        resort_id: str,
        url: str,
        started_at: datetime,
        *,
        extraction_method: ExtractionMethod,
    ) -> tuple[object | None, FetchLogEntry]:
        raise AssertionError(f"unexpected fetch for {extraction_method}: {url}")

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._fetch_json_value",
        fail_if_called,
    )

    exit_code = acquisition_main(
        [
            "--resort",
            "test-resort",
            "--registry-path",
            str(registry_path),
            "--catalog-path",
            str(catalog_path),
            "--output-dir",
            str(output_dir),
            "--skip-wikidata",
            "--skip-opendatahub",
            "--skip-osm",
            "--skip-dem",
            "--skip-llm",
        ]
    )

    assert exit_code == 0
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    assert all(entry.get("extraction_method") != "wikidata" for entry in fetch_log["fetch_log"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_catalog_acquisition_uses_wikidata_official_url_as_same_run_discovery_seed tests/test_resort_acquisition.py::test_catalog_acquisition_skip_wikidata_disables_wikidata_fetch -q
```

Expected: parser rejects new flags and runner lacks cascade functions.

- [ ] **Step 3: Implement `source_context.py`**

Implement:

```python
@dataclass
class SourceRunContext:
    resort_id: str
    configured_official_urls: dict[OfficialUrlRole, str]
    discovered_official_urls: dict[OfficialUrlRole, list[DiscoveredOfficialUrl]]
    configured_regional_ids: RegionalDataIds
    discovered_regional_ids: RegionalDataIds

@dataclass(frozen=True)
class DiscoveredOfficialUrl:
    role: OfficialUrlRole
    url: str
    source: SourceReference
    confidence: float
    evidence: str
```

Implement `SourceRunContext.official_urls_for_role(self, role: OfficialUrlRole) -> list[str]`.

Implement `SourceRunContext.effective_config_for_official_extraction(self) -> ResortSourceConfig`.

Rules:

- Configured official URLs are first.
- Discovered URLs are appended in confidence order.
- Limit effective official extraction to 3 URLs per role.
- Regional IDs discovered from Wikidata fill only missing configured IDs for same-run fetches.

- [ ] **Step 4: Implement runner flags and orchestration**

Add parser flags:

- `--skip-wikidata`
- `--skip-osm`
- `--skip-dem`
- `--skip-official-discovery`
- `--skip-llm-link-classification`

In `main()` per resort:

1. Build `SourceRunContext`.
2. Add registry candidates.
3. Run OpenDataHub discovery/detail unless skipped.
4. Run Wikidata if configured QID exists and not skipped. Add candidates. Add P856 as discovered homepage seed. Add P402 as same-run OSM ID if no configured OSM ID.
5. Run OSM if relation ID exists and not skipped.
6. Run DEM after coordinate candidates/current catalog points unless skipped.
7. Run official link discovery unless skipped, using configured URLs plus discovered homepage seeds.
8. Run LLM link classification unless `--skip-llm` or `--skip-llm-link-classification`.
9. Convert deterministic/LLM classified role URLs into URL `CandidateFact`s with `extraction_method` `"official_link_discovery"` or `"official_link_llm"`.
10. Build effective official URL config and run existing official-page extraction unless `--skip-llm`.

Preserve failure behavior:

- Any fetch failure still writes artifacts and returns `1`.
- No accepted candidates returns `2`.
- Skip flags do not create failed fetch-log entries.

- [ ] **Step 5: Run tests to verify green**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_catalog_acquisition_uses_wikidata_official_url_as_same_run_discovery_seed tests/test_resort_acquisition.py::test_catalog_acquisition_skip_wikidata_disables_wikidata_fetch -q
```

Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add app/data/resort_acquisition/source_context.py app/data/resort_acquisition/run_catalog_acquisition.py app/data/resort_acquisition/extractors.py tests/test_resort_acquisition.py
git commit -m "feat: orchestrate source cascade acquisition"
```

---

### Task 8: Consolidated Field-Level Evidence Report

**Files:**
- Modify: `app/data/resort_acquisition/reports.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing grouped evidence tests**

Add:

```python
def test_render_evidence_groups_multiple_sources_for_same_target_field() -> None:
    generated_at = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)
    target = ProposalTarget(entity_type="ski_area", entity_id="test-ski-area")
    proposals = [
        Proposal(
            resort_id="test-resort",
            target=target,
            field_path="latitude",
            current_value=46.0,
            proposed_value=46.55,
            status="changed",
            source=SourceReference(source_type="wikidata", source_url="https://www.wikidata.org/wiki/Special:EntityData/Q123.json"),
            extraction_method="wikidata",
            confidence=0.85,
            evidence="Wikidata P625 coordinate location latitude=46.55",
        ),
        Proposal(
            resort_id="test-resort",
            target=target,
            field_path="latitude",
            current_value=46.0,
            proposed_value=46.551,
            status="changed",
            source=SourceReference(source_type="osm", source_url="https://overpass-api.de/api/interpreter"),
            extraction_method="osm",
            confidence=0.8,
            evidence="OpenStreetMap relation 123 center lat=46.551",
        ),
    ]
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=["test-resort"],
        proposals=proposals,
        candidates=[],
        fetch_log=[],
    )

    evidence = render_evidence_markdown(output)

    assert "## `test-resort`" in evidence
    assert "### `ski_area:test-ski-area` / `latitude`" in evidence
    assert evidence.count("- Source:") == 2
    assert "Recommended value: review required" in evidence
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_render_evidence_groups_multiple_sources_for_same_target_field -q
```

Expected: current report renders one section per proposal.

- [ ] **Step 3: Implement grouped evidence rendering**

In `reports.py`:

- Keep `proposals.json` unchanged.
- Group proposals by `(resort_id, target.entity_type, target.entity_id, field_path)`.
- Sort groups by severity: conflict, warning, changed, new, rejected, same.
- For each group render:
  - current value
  - recommended value if all non-rejected proposals agree on one proposed value; otherwise `review required`
  - statuses present
  - one evidence bullet per proposal with source, method, confidence, proposed value, evidence, and validation notes.
- Add source-health summary from `fetch_log` failures at the top.
- Keep markdown sanitization for all free text.

- [ ] **Step 4: Run grouped evidence tests and existing report tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py::test_render_evidence_groups_multiple_sources_for_same_target_field tests/test_resort_acquisition.py::test_write_run_outputs_creates_json_and_markdown_artifacts tests/test_resort_acquisition.py::test_write_run_outputs_sanitizes_markdown_free_text -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/data/resort_acquisition/reports.py tests/test_resort_acquisition.py
git commit -m "feat: group resort acquisition evidence by field"
```

---

### Task 9: Documentation, Workflow Flags, and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/engineering-notes.md`
- Modify: `.github/workflows/catalog-acquisition.yml`
- Modify: `PROJECT.md` only if implementation changes the Sprint 30 boundaries
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Update docs**

Document:

- Sprint 30 provider cascade.
- `--skip-wikidata`, `--skip-osm`, `--skip-dem`, `--skip-official-discovery`, and `--skip-llm-link-classification`.
- `--skip-llm` disables both link classification and official-page fact extraction.
- Static official-link discovery uses no browser runtime.
- DEM warnings are sanity checks, not replacement elevation facts.

- [ ] **Step 2: Update GitHub Actions workflow inputs**

In `.github/workflows/catalog-acquisition.yml`, add manual inputs for the new skip flags and pass them through to the CLI only when selected. Keep workflow artifact-only: no commit, push, or PR creation.

- [ ] **Step 3: Run focused verification**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_resort_acquisition.py -q
```

Expected: all resort acquisition tests pass.

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app/data/resort_acquisition tests/test_resort_acquisition.py tests/conftest.py
```

Expected: `All checks passed!`

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.validate_resort_catalog
```

Expected: catalog valid output.

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 4: Run artifact-only smoke checks**

OpenDataHub-backed smoke:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition --resort alta-badia --skip-llm --output-dir artifacts/catalog-acquisition
```

Expected:

- exit `0`
- `artifacts/catalog-acquisition/fetch-log.json` includes successful OpenDataHub discovery/detail entries
- `artifacts/catalog-acquisition/proposals.json` includes targeted OpenDataHub candidates

Static discovery smoke without LLM:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition --resort alta-badia --skip-llm --skip-opendatahub --skip-wikidata --skip-osm --skip-dem --output-dir artifacts/catalog-acquisition-static-links
```

Expected:

- exit `0` if configured official URL seeds are present for the resort, otherwise exit `2`
- artifacts are still written
- no LLM cache directory is required

- [ ] **Step 5: Commit**

```bash
git add README.md docs/engineering-notes.md .github/workflows/catalog-acquisition.yml PROJECT.md tests/test_resort_acquisition.py
git commit -m "docs: document source cascade acquisition workflow"
```

---

## Final Acceptance Checklist

- [ ] `proposals.json` remains machine-readable per candidate and includes `target`.
- [ ] `evidence.md` groups by resort, target, and field.
- [ ] Same-run discovered Wikidata official URLs can feed link discovery without becoming approved catalog data.
- [ ] Same-run discovered Wikidata OSM relation IDs can feed OSM extraction without becoming approved catalog data.
- [ ] DEM emits warnings only; it does not replace base/summit values.
- [ ] Static official-link discovery does not require browser dependencies.
- [ ] LLM link classification validates roles and URLs against collected candidates.
- [ ] `--skip-llm` disables both link classification and official-page fact extraction.
- [ ] No adapter performs broad name search, search-engine discovery, or auto-writes catalog files.
- [ ] All focused tests, lint, catalog validation, diff check, and smoke checks complete.
