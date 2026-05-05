# Static Resort Data Acquisition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an artifact-only acquisition pipeline that proposes static and semi-static resort catalog facts with source evidence, without changing approved catalog data automatically.

**Architecture:** Approved truth remains `app/data/resorts.json` and `app/data/resort_trust_manifest.json`. A new `app/data/resort_acquisition/` subsystem loads configured sources, creates deterministic and LLM-backed candidate facts, compares them with the current raw catalog, and writes `proposals.json`, `evidence.md`, `fetch-log.json`, and compact source metadata. The app does not read acquisition outputs.

**Tech Stack:** Python 3.11, Pydantic v2, stdlib `argparse`/`json`/`html.parser`, dev dependency `httpx`, existing `app.ai.llm_client.LLMClient`, existing Gemini client, pytest, ruff, GitHub Actions.

---

## File Structure

- Create `app/data/resort_acquisition/__init__.py`: package marker and short module docstring.
- Create `app/data/resort_acquisition/models.py`: Pydantic models and literal types shared by registry, extractors, proposals, reports, and CLI.
- Create `app/data/resort_acquisition/sources.json`: small checked-in source registry. Start with Alta Badia OpenDataHub ID only, because that ID is already source-backed and avoids questionable official URL guesses.
- Create `app/data/resort_acquisition/registry.py`: load and validate `sources.json`.
- Create `app/data/resort_acquisition/fetching.py`: HTTP fetch wrapper, text extraction, content hashes, compact snapshot metadata.
- Create `app/data/resort_acquisition/extractors.py`: deterministic registry and OpenDataHub extractors.
- Create `app/data/resort_acquisition/llm_extract.py`: official/provider page LLM extraction with schema validation and output-dir file cache.
- Create `app/data/resort_acquisition/proposals.py`: compare candidate facts with raw catalog values and mark proposal status.
- Create `app/data/resort_acquisition/reports.py`: write JSON artifacts and Markdown evidence.
- Create `app/data/resort_acquisition/run_catalog_acquisition.py`: CLI orchestration.
- Create `tests/test_resort_acquisition.py`: unit tests for models, registry, extractors, LLM extraction, proposals, report writing, and CLI smoke output.
- Create `.github/workflows/catalog-acquisition.yml`: manual, read-only artifact workflow.
- Modify `.gitignore`: ignore generated acquisition artifacts.
- Modify `README.md`: add local acquisition command and artifact review notes.
- Modify `docs/engineering-notes.md`: add the durable architecture note for artifact-only catalog acquisition.

---

## Data Contracts

Use these field paths for v1 candidates:

```text
total_piste_km
total_lift_count
piste_km_by_difficulty
ski_area_official_url
ski_pass_url
rental_url
season_dates_url
trail_map_url
official_status_url
regional_data_ids
osm_relation_id
wikidata_id
lift_pass_prices
rental_facts
```

OpenDataHub mapping:

```text
TotalSlopeKm -> total_piste_km
LiftCount -> total_lift_count
SlopeKmBlue -> piste_km_by_difficulty.beginner
SlopeKmRed -> piste_km_by_difficulty.intermediate
SlopeKmBlack -> piste_km_by_difficulty.advanced
SkiAreaMapURL -> trail_map_url
configured regional_data_ids.opendatahub_ski_area_id -> regional_data_ids.opendatahub_ski_area_id
```

Proposal statuses:

```text
new: current catalog has no value at field_path
changed: current catalog value exists and differs
same: current catalog value equals proposed value
rejected: candidate failed validation or came from a closed/unusable source
conflict: multiple accepted candidates for the same field_path disagree
```

---

### Task 1: Acquisition Models

**Files:**
- Create: `app/data/resort_acquisition/__init__.py`
- Create: `app/data/resort_acquisition/models.py`
- Test: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing model tests**

Append these tests to `tests/test_resort_acquisition.py`:

```python
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.data.resort_acquisition.models import (
    CandidateFact,
    LiftPassPriceCandidate,
    SourceReference,
)


def test_candidate_fact_requires_non_empty_field_path() -> None:
    source = SourceReference(
        source_type="opendatahub",
        source_url="https://tourism.api.opendatahub.com/v1/SkiArea/example",
    )

    with pytest.raises(ValidationError):
        CandidateFact(
            resort_id="alta-badia",
            field_path="",
            proposed_value=130.0,
            source=source,
            extraction_method="opendatahub",
            fetched_at=datetime.fromisoformat("2026-05-04T10:00:00+00:00"),
            confidence=0.95,
        )


def test_lift_pass_price_candidate_accepts_six_day_adult_price() -> None:
    price = LiftPassPriceCandidate(
        duration_days=6,
        audience="adult",
        amount=390.0,
        currency="EUR",
        price_kind="fixed",
        season_label="2025/26 winter",
        source_url="https://example.com/prices",
        evidence="6 days adult EUR 390",
        confidence=0.9,
    )

    assert price.duration_days == 6
    assert price.price_kind == "fixed"
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py -q
```

Expected: import failure because `app.data.resort_acquisition.models` does not exist.

- [ ] **Step 3: Add the package marker**

Create `app/data/resort_acquisition/__init__.py`:

```python
"""Artifact-only resort catalog acquisition tools."""
```

- [ ] **Step 4: Add shared Pydantic models**

Create `app/data/resort_acquisition/models.py` with this structure:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

JsonValue = str | int | float | bool | None | dict[str, Any] | list[Any]

PriceKind = Literal["fixed", "from", "range", "unknown"]
ExtractionMethod = Literal["registry", "opendatahub", "official_page_llm"]
SourceType = Literal["catalog", "official", "opendatahub", "osm", "wikidata", "provider"]
ProposalStatus = Literal["new", "changed", "same", "rejected", "conflict"]
FetchStatus = Literal["success", "failed", "skipped"]


class SourceReference(BaseModel):
    source_type: SourceType
    source_url: str | None = None
    source_name: str | None = None
    license: str | None = None

    @model_validator(mode="after")
    def require_url_or_name(self) -> "SourceReference":
        if not self.source_url and not self.source_name:
            raise ValueError("source_url or source_name is required")
        return self


class LiftPassPriceCandidate(BaseModel):
    duration_days: int = Field(ge=1)
    audience: str = Field(min_length=1)
    amount: float | None = Field(default=None, ge=0)
    amount_min: float | None = Field(default=None, ge=0)
    amount_max: float | None = Field(default=None, ge=0)
    currency: str = Field(min_length=3, max_length=3)
    price_kind: PriceKind
    season_label: str | None = None
    source_url: str
    evidence: str | None = None
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def require_amount_shape(self) -> "LiftPassPriceCandidate":
        if self.price_kind == "range":
            if self.amount_min is None or self.amount_max is None:
                raise ValueError("range prices require amount_min and amount_max")
            if self.amount_min > self.amount_max:
                raise ValueError("amount_min cannot exceed amount_max")
            return self
        if self.price_kind in {"fixed", "from"} and self.amount is None:
            raise ValueError("fixed and from prices require amount")
        return self


class CandidateFact(BaseModel):
    resort_id: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    proposed_value: JsonValue
    source: SourceReference
    extraction_method: ExtractionMethod
    fetched_at: datetime
    confidence: float = Field(ge=0, le=1)
    evidence: str | None = None
    validation_status: Literal["accepted", "rejected"] = "accepted"
    validation_notes: list[str] = Field(default_factory=list)

    @field_validator("field_path")
    @classmethod
    def reject_blank_segments(cls, value: str) -> str:
        if any(not segment for segment in value.split(".")):
            raise ValueError("field_path cannot contain blank segments")
        return value


class FetchLogEntry(BaseModel):
    resort_id: str
    url: str
    fetched_at: datetime
    status: FetchStatus
    status_code: int | None = None
    content_hash: str | None = None
    extraction_method: ExtractionMethod | None = None
    truncated: bool = False
    error: str | None = None


class Proposal(BaseModel):
    resort_id: str
    field_path: str
    current_value: JsonValue
    proposed_value: JsonValue
    status: ProposalStatus
    source: SourceReference
    extraction_method: ExtractionMethod
    confidence: float = Field(ge=0, le=1)
    evidence: str | None = None
    validation_notes: list[str] = Field(default_factory=list)


class AcquisitionRunOutput(BaseModel):
    generated_at: datetime
    selected_resorts: list[str]
    proposals: list[Proposal]
    candidates: list[CandidateFact]
    fetch_log: list[FetchLogEntry]
```

- [ ] **Step 5: Run model tests**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py -q
```

Expected: the two model tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add app/data/resort_acquisition/__init__.py app/data/resort_acquisition/models.py tests/test_resort_acquisition.py
git commit -m "feat: add resort acquisition data models"
```

---

### Task 2: Source Registry Loader

**Files:**
- Create: `app/data/resort_acquisition/sources.json`
- Create: `app/data/resort_acquisition/registry.py`
- Modify: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing registry tests**

Append:

```python
import json

from app.data.resort_acquisition.registry import load_source_registry


def test_load_source_registry_validates_resort_entries(tmp_path) -> None:
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "resorts": {
                    "alta-badia": {
                        "regional_data_ids": {
                            "opendatahub_ski_area_id": "SKI04EBE61F5AA0473F871AF0297887D6C2"
                        },
                        "official_urls": {
                            "ski_pass": "https://www.altabadia.org/en/ski-holidays/ski-pass.html"
                        },
                    }
                },
            }
        )
    )

    registry = load_source_registry(registry_path)

    assert registry.version == 1
    assert registry.resorts["alta-badia"].regional_data_ids.opendatahub_ski_area_id


def test_load_source_registry_rejects_unknown_url_role(tmp_path) -> None:
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "resorts": {
                    "alta-badia": {
                        "official_urls": {
                            "blog": "https://example.com/blog"
                        }
                    }
                },
            }
        )
    )

    with pytest.raises(ValueError, match="unsupported official URL role"):
        load_source_registry(registry_path)
```

- [ ] **Step 2: Run registry tests and confirm failure**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_load_source_registry_validates_resort_entries tests/test_resort_acquisition.py::test_load_source_registry_rejects_unknown_url_role -q
```

Expected: import failure because `registry.py` does not exist.

- [ ] **Step 3: Extend models with registry models**

Append to `app/data/resort_acquisition/models.py`:

```python
OfficialUrlRole = Literal[
    "ski_area",
    "ski_pass",
    "rental",
    "season_dates",
    "trail_map",
    "official_status",
]


class RegionalDataIds(BaseModel):
    opendatahub_ski_area_id: str | None = None
    osm_relation_id: str | None = None
    wikidata_id: str | None = None


class ResortSourceConfig(BaseModel):
    official_urls: dict[OfficialUrlRole, str] = Field(default_factory=dict)
    provider_urls: dict[str, str] = Field(default_factory=dict)
    regional_data_ids: RegionalDataIds = Field(default_factory=RegionalDataIds)


class SourceRegistry(BaseModel):
    version: int
    resorts: dict[str, ResortSourceConfig] = Field(default_factory=dict)
```

- [ ] **Step 4: Add checked-in registry seed**

Create `app/data/resort_acquisition/sources.json`:

```json
{
  "version": 1,
  "resorts": {
    "alta-badia": {
      "regional_data_ids": {
        "opendatahub_ski_area_id": "SKI04EBE61F5AA0473F871AF0297887D6C2"
      },
      "official_urls": {}
    }
  }
}
```

- [ ] **Step 5: Add loader**

Create `app/data/resort_acquisition/registry.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.data.resort_acquisition.models import OfficialUrlRole, SourceRegistry

DEFAULT_SOURCE_REGISTRY_PATH = Path(__file__).with_name("sources.json")
SUPPORTED_OFFICIAL_URL_ROLES = set(OfficialUrlRole.__args__)


def load_source_registry(path: Path = DEFAULT_SOURCE_REGISTRY_PATH) -> SourceRegistry:
    try:
        payload = json.loads(path.read_text())
    except OSError as error:
        raise ValueError(f"Unable to read source registry at {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in source registry at {path}") from error

    _validate_raw_registry(payload)
    try:
        return SourceRegistry.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"Invalid source registry at {path}: {error}") from error


def _validate_raw_registry(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("source registry must be an object")
    if not isinstance(payload.get("resorts"), dict):
        raise ValueError("source registry must contain resorts object")

    for resort_id, resort_payload in payload["resorts"].items():
        if not isinstance(resort_id, str) or not resort_id:
            raise ValueError("source registry resort ids must be non-empty strings")
        if not isinstance(resort_payload, dict):
            raise ValueError(f"{resort_id}: source registry entry must be an object")
        official_urls = resort_payload.get("official_urls", {})
        if not isinstance(official_urls, dict):
            raise ValueError(f"{resort_id}: official_urls must be an object")
        for role in official_urls:
            if role not in SUPPORTED_OFFICIAL_URL_ROLES:
                raise ValueError(f"{resort_id}: unsupported official URL role {role!r}")
```

- [ ] **Step 6: Run registry tests**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_load_source_registry_validates_resort_entries tests/test_resort_acquisition.py::test_load_source_registry_rejects_unknown_url_role -q
```

Expected: both tests pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add app/data/resort_acquisition/models.py app/data/resort_acquisition/registry.py app/data/resort_acquisition/sources.json tests/test_resort_acquisition.py
git commit -m "feat: add resort acquisition source registry"
```

---

### Task 3: Deterministic Extractors

**Files:**
- Create: `app/data/resort_acquisition/extractors.py`
- Modify: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing extractor tests**

Append:

```python
from datetime import timezone

from app.data.resort_acquisition.extractors import (
    extract_opendatahub_candidates,
    extract_registry_candidates,
)
from app.data.resort_acquisition.models import RegionalDataIds, ResortSourceConfig


def test_extract_registry_candidates_emits_url_and_id_facts() -> None:
    config = ResortSourceConfig(
        official_urls={"ski_pass": "https://example.com/prices"},
        regional_data_ids=RegionalDataIds(osm_relation_id="12345"),
    )
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)

    candidates = extract_registry_candidates("test-resort", config, fetched_at)

    field_paths = {candidate.field_path for candidate in candidates}
    assert "ski_pass_url" in field_paths
    assert "regional_data_ids.osm_relation_id" in field_paths


def test_extract_opendatahub_candidates_maps_ski_area_fields() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    payload = {
        "LiftCount": "53",
        "TotalSlopeKm": "130",
        "SlopeKmBlue": "74",
        "SlopeKmRed": "47",
        "SlopeKmBlack": "9",
        "SkiAreaMapURL": "https://example.com/map.pdf",
        "LicenseInfo": {"ClosedData": False, "License": "CC0"},
    }
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)

    candidates = extract_opendatahub_candidates(
        "alta-badia",
        config,
        payload,
        fetched_at,
        source_url="https://tourism.api.opendatahub.com/v1/SkiArea/SKI123?language=en",
    )

    values = {candidate.field_path: candidate.proposed_value for candidate in candidates}
    assert values["total_lift_count"] == 53
    assert values["total_piste_km"] == 130.0
    assert values["piste_km_by_difficulty"] == {
        "beginner": 74.0,
        "intermediate": 47.0,
        "advanced": 9.0,
    }
    assert values["trail_map_url"] == "https://example.com/map.pdf"
```

- [ ] **Step 2: Run extractor tests and confirm failure**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_extract_registry_candidates_emits_url_and_id_facts tests/test_resort_acquisition.py::test_extract_opendatahub_candidates_maps_ski_area_fields -q
```

Expected: import failure because `extractors.py` does not exist.

- [ ] **Step 3: Add deterministic extractors**

Create `app/data/resort_acquisition/extractors.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.data.resort_acquisition.models import (
    CandidateFact,
    ResortSourceConfig,
    SourceReference,
)

OFFICIAL_ROLE_FIELD_PATHS = {
    "ski_area": "ski_area_official_url",
    "ski_pass": "ski_pass_url",
    "rental": "rental_url",
    "season_dates": "season_dates_url",
    "trail_map": "trail_map_url",
    "official_status": "official_status_url",
}


def extract_registry_candidates(
    resort_id: str,
    config: ResortSourceConfig,
    fetched_at: datetime,
) -> list[CandidateFact]:
    candidates: list[CandidateFact] = []
    for role, url in sorted(config.official_urls.items()):
        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                field_path=OFFICIAL_ROLE_FIELD_PATHS[role],
                proposed_value=url,
                source=SourceReference(source_type="official", source_url=url),
                extraction_method="registry",
                fetched_at=fetched_at,
                confidence=1.0,
                evidence=f"Configured official {role} URL",
            )
        )

    regional = config.regional_data_ids
    regional_values = {
        "regional_data_ids.opendatahub_ski_area_id": regional.opendatahub_ski_area_id,
        "regional_data_ids.osm_relation_id": regional.osm_relation_id,
        "regional_data_ids.wikidata_id": regional.wikidata_id,
        "osm_relation_id": regional.osm_relation_id,
        "wikidata_id": regional.wikidata_id,
    }
    for field_path, value in regional_values.items():
        if value:
            candidates.append(
                CandidateFact(
                    resort_id=resort_id,
                    field_path=field_path,
                    proposed_value=value,
                    source=SourceReference(source_type="catalog", source_name="source registry"),
                    extraction_method="registry",
                    fetched_at=fetched_at,
                    confidence=1.0,
                    evidence=f"Configured {field_path}",
                )
            )
    return candidates


def extract_opendatahub_candidates(
    resort_id: str,
    config: ResortSourceConfig,
    payload: dict[str, Any],
    fetched_at: datetime,
    *,
    source_url: str,
) -> list[CandidateFact]:
    license_info = payload.get("LicenseInfo") if isinstance(payload, dict) else None
    if not isinstance(license_info, dict) or license_info.get("ClosedData") is not False:
        return [
            CandidateFact(
                resort_id=resort_id,
                field_path="regional_data_ids.opendatahub_ski_area_id",
                proposed_value=config.regional_data_ids.opendatahub_ski_area_id,
                source=SourceReference(source_type="opendatahub", source_url=source_url),
                extraction_method="opendatahub",
                fetched_at=fetched_at,
                confidence=0.0,
                evidence="OpenDataHub payload is closed or missing license metadata",
                validation_status="rejected",
                validation_notes=["OpenDataHub payload is not open data"],
            )
        ]

    source = SourceReference(
        source_type="opendatahub",
        source_url=source_url,
        license=str(license_info.get("License", "")) or None,
    )
    candidates: list[CandidateFact] = []

    total_piste_km = _parse_float(payload.get("TotalSlopeKm"))
    if total_piste_km is not None:
        candidates.append(_candidate(resort_id, "total_piste_km", total_piste_km, source, fetched_at))

    total_lift_count = _parse_int(payload.get("LiftCount"))
    if total_lift_count is not None:
        candidates.append(_candidate(resort_id, "total_lift_count", total_lift_count, source, fetched_at))

    difficulty = {
        "beginner": _parse_float(payload.get("SlopeKmBlue")),
        "intermediate": _parse_float(payload.get("SlopeKmRed")),
        "advanced": _parse_float(payload.get("SlopeKmBlack")),
    }
    if all(value is not None for value in difficulty.values()):
        candidates.append(_candidate(resort_id, "piste_km_by_difficulty", difficulty, source, fetched_at))

    trail_map_url = payload.get("SkiAreaMapURL")
    if isinstance(trail_map_url, str) and trail_map_url.strip():
        candidates.append(_candidate(resort_id, "trail_map_url", trail_map_url.strip(), source, fetched_at))

    opendatahub_id = config.regional_data_ids.opendatahub_ski_area_id
    if opendatahub_id:
        candidates.append(
            _candidate(
                resort_id,
                "regional_data_ids.opendatahub_ski_area_id",
                opendatahub_id,
                source,
                fetched_at,
            )
        )
    return candidates


def _candidate(
    resort_id: str,
    field_path: str,
    value: Any,
    source: SourceReference,
    fetched_at: datetime,
) -> CandidateFact:
    return CandidateFact(
        resort_id=resort_id,
        field_path=field_path,
        proposed_value=value,
        source=source,
        extraction_method="opendatahub",
        fetched_at=fetched_at,
        confidence=0.95,
        evidence=f"OpenDataHub field mapped to {field_path}",
    )


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value: Any) -> int | None:
    parsed = _parse_float(value)
    if parsed is None:
        return None
    return int(parsed)
```

- [ ] **Step 4: Run extractor tests**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_extract_registry_candidates_emits_url_and_id_facts tests/test_resort_acquisition.py::test_extract_opendatahub_candidates_maps_ski_area_fields -q
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/data/resort_acquisition/extractors.py tests/test_resort_acquisition.py
git commit -m "feat: add deterministic resort source extractors"
```

---

### Task 4: Fetching And Compact Snapshots

**Files:**
- Create: `app/data/resort_acquisition/fetching.py`
- Modify: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing fetching tests**

Append:

```python
from app.data.resort_acquisition.fetching import html_to_text, stable_content_hash


def test_html_to_text_removes_script_text_and_collapses_whitespace() -> None:
    html = "<html><head><script>ignore()</script></head><body><h1>Prices</h1><p>Adult 6 days EUR 390</p></body></html>"

    text = html_to_text(html)

    assert text == "Prices Adult 6 days EUR 390"
    assert "ignore" not in text


def test_stable_content_hash_is_sha256_hex() -> None:
    digest = stable_content_hash("Adult 6 days EUR 390")

    assert len(digest) == 64
    assert digest == stable_content_hash("Adult 6 days EUR 390")
```

- [ ] **Step 2: Run fetching tests and confirm failure**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_html_to_text_removes_script_text_and_collapses_whitespace tests/test_resort_acquisition.py::test_stable_content_hash_is_sha256_hex -q
```

Expected: import failure because `fetching.py` does not exist.

- [ ] **Step 3: Add fetching utilities**

Create `app/data/resort_acquisition/fetching.py`:

```python
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser

import httpx


@dataclass(frozen=True)
class FetchedPage:
    url: str
    final_url: str
    status_code: int | None
    fetched_at: datetime
    text: str
    content_hash: str | None
    truncated: bool
    error: str | None = None


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._blocked_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._blocked_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._blocked_depth:
            self._blocked_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._blocked_depth == 0 and data.strip():
            self.parts.append(data.strip())


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def stable_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_url(url: str, *, max_chars: int = 30_000, timeout_seconds: float = 15.0) -> FetchedPage:
    fetched_at = datetime.now(timezone.utc)
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "SnowcastCatalogAcquisition/1.0"})
            response.raise_for_status()
    except httpx.HTTPError as error:
        status_code = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
        return FetchedPage(
            url=url,
            final_url=url,
            status_code=status_code,
            fetched_at=fetched_at,
            text="",
            content_hash=None,
            truncated=False,
            error=str(error),
        )

    text = html_to_text(response.text)
    truncated = len(text) > max_chars
    clipped_text = text[:max_chars] if truncated else text
    return FetchedPage(
        url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        fetched_at=fetched_at,
        text=clipped_text,
        content_hash=stable_content_hash(text),
        truncated=truncated,
    )
```

- [ ] **Step 4: Run fetching tests**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_html_to_text_removes_script_text_and_collapses_whitespace tests/test_resort_acquisition.py::test_stable_content_hash_is_sha256_hex -q
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/data/resort_acquisition/fetching.py tests/test_resort_acquisition.py
git commit -m "feat: add resort source fetching helpers"
```

---

### Task 5: LLM Official Page Extraction

**Files:**
- Create: `app/data/resort_acquisition/llm_extract.py`
- Modify: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing fake-LLM tests**

Append:

```python
from app.ai.llm_client import LLMClient
from app.data.resort_acquisition.fetching import FetchedPage
from app.data.resort_acquisition.llm_extract import extract_official_page_candidates


class FakeLLMClient(LLMClient):
    @property
    def model(self) -> str:
        return "fake-model"

    def complete(self, **kwargs) -> str:
        return json.dumps(
            {
                "facts": [
                    {
                        "field_path": "season_dates_url",
                        "value": "https://example.com/season",
                        "evidence": "Winter season page",
                        "confidence": 0.82,
                    }
                ],
                "lift_pass_prices": [
                    {
                        "duration_days": 6,
                        "audience": "adult",
                        "amount": 390,
                        "currency": "EUR",
                        "price_kind": "fixed",
                        "season_label": "2025/26 winter",
                        "source_url": "https://example.com/prices",
                        "evidence": "Adult 6 days EUR 390",
                        "confidence": 0.91,
                    }
                ],
            }
        )


def test_extract_official_page_candidates_uses_schema_output(tmp_path) -> None:
    page = FetchedPage(
        url="https://example.com/prices",
        final_url="https://example.com/prices",
        status_code=200,
        fetched_at=datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
        text="Adult 6 days EUR 390",
        content_hash="abc123",
        truncated=False,
    )

    candidates, errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=FakeLLMClient(),
        cache_dir=tmp_path,
    )

    assert errors == []
    assert {candidate.field_path for candidate in candidates} == {
        "season_dates_url",
        "lift_pass_prices",
    }
    price_candidate = next(candidate for candidate in candidates if candidate.field_path == "lift_pass_prices")
    assert price_candidate.proposed_value["duration_days"] == 6
```

- [ ] **Step 2: Run LLM extraction test and confirm failure**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_extract_official_page_candidates_uses_schema_output -q
```

Expected: import failure because `llm_extract.py` does not exist.

- [ ] **Step 3: Add LLM extraction module**

Create `app/data/resort_acquisition/llm_extract.py`:

```python
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.ai.llm_client import LLMClient, LLMClientError
from app.data.resort_acquisition.fetching import FetchedPage
from app.data.resort_acquisition.models import (
    CandidateFact,
    LiftPassPriceCandidate,
    SourceReference,
)

PROMPT_VERSION = "official-page-v1"
SCHEMA_VERSION = "official-page-schema-v1"
ALLOWED_LLM_FACT_FIELDS = {
    "total_piste_km",
    "total_lift_count",
    "piste_km_by_difficulty",
    "ski_area_official_url",
    "ski_pass_url",
    "rental_url",
    "season_dates_url",
    "trail_map_url",
    "official_status_url",
    "rental_facts",
}


class ExtractedFact(BaseModel):
    field_path: str
    value: Any = None
    evidence: str | None = None
    confidence: float = Field(ge=0, le=1)


class ExtractedOfficialPage(BaseModel):
    facts: list[ExtractedFact] = Field(default_factory=list)
    lift_pass_prices: list[LiftPassPriceCandidate] = Field(default_factory=list)


def extract_official_page_candidates(
    *,
    resort_id: str,
    page: FetchedPage,
    page_role: str,
    llm_client: LLMClient,
    cache_dir: Path,
) -> tuple[list[CandidateFact], list[str]]:
    if not page.text.strip() or page.content_hash is None:
        return [], [f"{page.url}: no fetched text available for LLM extraction"]

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = _cache_key(page.final_url, page.content_hash)
    cache_path = cache_dir / f"{cache_key}.json"
    errors: list[str] = []

    if cache_path.exists():
        raw_response = cache_path.read_text()
    else:
        try:
            raw_response = llm_client.complete(
                system_prompt=_system_prompt(),
                user_prompt=_user_prompt(page_role=page_role, url=page.final_url, text=page.text),
                temperature=0.0,
                response_mime_type="application/json",
                response_json_schema=_response_json_schema(),
            )
        except LLMClientError as error:
            return [], [f"{page.url}: LLM extraction failed: {error.reason}"]
        cache_path.write_text(raw_response)

    try:
        payload = json.loads(raw_response)
        extracted = ExtractedOfficialPage.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as error:
        return [], [f"{page.url}: invalid LLM extraction output: {error}"]

    source = SourceReference(source_type="official", source_url=page.final_url)
    candidates: list[CandidateFact] = []
    for fact in extracted.facts:
        if fact.value is None:
            continue
        if fact.field_path not in ALLOWED_LLM_FACT_FIELDS:
            errors.append(f"{page.url}: unsupported LLM field_path {fact.field_path}")
            continue
        if not fact.evidence:
            errors.append(f"{page.url}: missing evidence for {fact.field_path}")
            continue
        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                field_path=fact.field_path,
                proposed_value=fact.value,
                source=source,
                extraction_method="official_page_llm",
                fetched_at=page.fetched_at,
                confidence=fact.confidence,
                evidence=fact.evidence,
            )
        )

    for price in extracted.lift_pass_prices:
        if not price.evidence:
            errors.append(f"{page.url}: missing evidence for lift_pass_prices")
            continue
        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                field_path="lift_pass_prices",
                proposed_value=price.model_dump(mode="json"),
                source=source,
                extraction_method="official_page_llm",
                fetched_at=page.fetched_at,
                confidence=price.confidence,
                evidence=price.evidence,
            )
        )
    return candidates, errors


def _cache_key(url: str, content_hash: str) -> str:
    raw = "|".join([url, content_hash, SCHEMA_VERSION, PROMPT_VERSION])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _system_prompt() -> str:
    return (
        "Extract only explicit ski resort catalog facts from the provided official or provider page. "
        "Return JSON matching the schema. Use null for missing values. Do not infer values from unrelated text."
    )


def _user_prompt(*, page_role: str, url: str, text: str) -> str:
    return (
        f"Page role: {page_role}\n"
        f"URL: {url}\n"
        "Allowed fact fields: total_piste_km, total_lift_count, piste_km_by_difficulty, "
        "ski_area_official_url, ski_pass_url, rental_url, season_dates_url, trail_map_url, "
        "official_status_url, rental_facts.\n"
        "For lift pass prices, extract adult 1-day, 3-day, and 6-day prices only when explicitly present.\n\n"
        f"Page text:\n{text}"
    )


def _response_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "facts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field_path": {"type": "string"},
                        "value": {},
                        "evidence": {"type": ["string", "null"]},
                        "confidence": {"type": "number"},
                    },
                    "required": ["field_path", "value", "confidence"],
                },
            },
            "lift_pass_prices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "duration_days": {"type": "integer"},
                        "audience": {"type": "string"},
                        "amount": {"type": ["number", "null"]},
                        "amount_min": {"type": ["number", "null"]},
                        "amount_max": {"type": ["number", "null"]},
                        "currency": {"type": "string"},
                        "price_kind": {"type": "string", "enum": ["fixed", "from", "range", "unknown"]},
                        "season_label": {"type": ["string", "null"]},
                        "source_url": {"type": "string"},
                        "evidence": {"type": ["string", "null"]},
                        "confidence": {"type": "number"},
                    },
                    "required": ["duration_days", "audience", "currency", "price_kind", "source_url", "confidence"],
                },
            },
        },
        "required": ["facts", "lift_pass_prices"],
    }
```

- [ ] **Step 4: Run LLM extraction test**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_extract_official_page_candidates_uses_schema_output -q
```

Expected: test passes.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/data/resort_acquisition/llm_extract.py tests/test_resort_acquisition.py
git commit -m "feat: add official page llm extraction"
```

---

### Task 6: Proposal Comparison

**Files:**
- Create: `app/data/resort_acquisition/proposals.py`
- Modify: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing proposal tests**

Append:

```python
from app.data.resort_acquisition.proposals import build_proposals


def test_build_proposals_marks_new_changed_same_and_conflict() -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    raw_catalog = {
        "test-resort": {
            "resort_id": "test-resort",
            "total_lift_count": 20,
            "ski_pass_url": "https://example.com/prices",
        }
    }
    candidates = [
        CandidateFact(
            resort_id="test-resort",
            field_path="total_lift_count",
            proposed_value=20,
            source=source,
            extraction_method="registry",
            fetched_at=fetched_at,
            confidence=1.0,
        ),
        CandidateFact(
            resort_id="test-resort",
            field_path="total_piste_km",
            proposed_value=130,
            source=source,
            extraction_method="opendatahub",
            fetched_at=fetched_at,
            confidence=0.95,
        ),
        CandidateFact(
            resort_id="test-resort",
            field_path="ski_pass_url",
            proposed_value="https://example.com/other-prices",
            source=source,
            extraction_method="registry",
            fetched_at=fetched_at,
            confidence=1.0,
        ),
        CandidateFact(
            resort_id="test-resort",
            field_path="total_piste_km",
            proposed_value=125,
            source=source,
            extraction_method="official_page_llm",
            fetched_at=fetched_at,
            confidence=0.7,
        ),
    ]

    proposals = build_proposals(raw_catalog, candidates)
    statuses = {(proposal.field_path, proposal.proposed_value): proposal.status for proposal in proposals}

    assert statuses[("total_lift_count", 20)] == "same"
    assert statuses[("ski_pass_url", "https://example.com/other-prices")] == "changed"
    assert statuses[("total_piste_km", 130)] == "conflict"
    assert statuses[("total_piste_km", 125)] == "conflict"
```

- [ ] **Step 2: Run proposal test and confirm failure**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_build_proposals_marks_new_changed_same_and_conflict -q
```

Expected: import failure because `proposals.py` does not exist.

- [ ] **Step 3: Add proposal comparison**

Create `app/data/resort_acquisition/proposals.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.data.loader import DEFAULT_RESORTS_PATH
from app.data.resort_acquisition.models import CandidateFact, JsonValue, Proposal


def load_raw_catalog_by_resort(path: Path = DEFAULT_RESORTS_PATH) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        raise ValueError("resort catalog must be a JSON list")
    result: dict[str, dict[str, Any]] = {}
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("resort catalog entries must be objects")
        resort_id = item.get("resort_id")
        if not isinstance(resort_id, str) or not resort_id:
            raise ValueError("resort catalog entries require resort_id")
        result[resort_id] = item
    return result


def build_proposals(
    raw_catalog_by_resort: dict[str, dict[str, Any]],
    candidates: list[CandidateFact],
) -> list[Proposal]:
    conflict_keys = _conflict_keys(candidates)
    proposals: list[Proposal] = []
    for candidate in candidates:
        current_value = _get_field_path(
            raw_catalog_by_resort.get(candidate.resort_id, {}),
            candidate.field_path,
        )
        if candidate.validation_status == "rejected":
            status = "rejected"
        elif (candidate.resort_id, candidate.field_path) in conflict_keys:
            status = "conflict"
        elif current_value == candidate.proposed_value:
            status = "same"
        elif current_value is None:
            status = "new"
        else:
            status = "changed"
        proposals.append(
            Proposal(
                resort_id=candidate.resort_id,
                field_path=candidate.field_path,
                current_value=current_value,
                proposed_value=candidate.proposed_value,
                status=status,
                source=candidate.source,
                extraction_method=candidate.extraction_method,
                confidence=candidate.confidence,
                evidence=candidate.evidence,
                validation_notes=candidate.validation_notes,
            )
        )
    return proposals


def _conflict_keys(candidates: list[CandidateFact]) -> set[tuple[str, str]]:
    grouped: dict[tuple[str, str], set[str]] = {}
    for candidate in candidates:
        if candidate.validation_status == "rejected":
            continue
        key = (candidate.resort_id, candidate.field_path)
        grouped.setdefault(key, set()).add(json.dumps(candidate.proposed_value, sort_keys=True))
    return {key for key, values in grouped.items() if len(values) > 1}


def _get_field_path(payload: dict[str, Any], field_path: str) -> JsonValue:
    current: Any = payload
    for segment in field_path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current
```

- [ ] **Step 4: Run proposal test**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_build_proposals_marks_new_changed_same_and_conflict -q
```

Expected: test passes.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/data/resort_acquisition/proposals.py tests/test_resort_acquisition.py
git commit -m "feat: compare resort acquisition candidates"
```

---

### Task 7: Artifact Report Writer

**Files:**
- Create: `app/data/resort_acquisition/reports.py`
- Modify: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing report tests**

Append:

```python
from app.data.resort_acquisition.models import AcquisitionRunOutput, FetchLogEntry, Proposal
from app.data.resort_acquisition.reports import write_run_outputs


def test_write_run_outputs_creates_json_and_markdown_artifacts(tmp_path) -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    generated_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    proposal = Proposal(
        resort_id="test-resort",
        field_path="total_piste_km",
        current_value=None,
        proposed_value=130.0,
        status="new",
        source=source,
        extraction_method="official_page_llm",
        confidence=0.8,
        evidence="130 km of pistes",
    )
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=["test-resort"],
        proposals=[proposal],
        candidates=[],
        fetch_log=[
            FetchLogEntry(
                resort_id="test-resort",
                url="https://example.com",
                fetched_at=generated_at,
                status="success",
                status_code=200,
                content_hash="abc123",
                extraction_method="official_page_llm",
            )
        ],
    )

    write_run_outputs(tmp_path, output)

    proposals = json.loads((tmp_path / "proposals.json").read_text())
    fetch_log = json.loads((tmp_path / "fetch-log.json").read_text())
    evidence = (tmp_path / "evidence.md").read_text()
    assert proposals["selected_resorts"] == ["test-resort"]
    assert fetch_log[0]["status"] == "success"
    assert "total_piste_km" in evidence
    assert "130 km of pistes" in evidence
```

- [ ] **Step 2: Run report test and confirm failure**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_write_run_outputs_creates_json_and_markdown_artifacts -q
```

Expected: import failure because `reports.py` does not exist.

- [ ] **Step 3: Add report writer**

Create `app/data/resort_acquisition/reports.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from app.data.resort_acquisition.models import AcquisitionRunOutput, Proposal


def write_run_outputs(output_dir: Path, output: AcquisitionRunOutput) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "source-snapshots").mkdir(exist_ok=True)
    (output_dir / "proposals.json").write_text(
        json.dumps(output.model_dump(mode="json"), indent=2, sort_keys=True)
    )
    (output_dir / "fetch-log.json").write_text(
        json.dumps(
            [entry.model_dump(mode="json") for entry in output.fetch_log],
            indent=2,
            sort_keys=True,
        )
    )
    (output_dir / "evidence.md").write_text(render_evidence_markdown(output))


def render_evidence_markdown(output: AcquisitionRunOutput) -> str:
    lines = [
        "# Resort Catalog Acquisition Evidence",
        "",
        f"Generated at: `{output.generated_at.isoformat()}`",
        "",
        f"Selected resorts: {', '.join(output.selected_resorts) if output.selected_resorts else '(none)'}",
        "",
    ]
    proposals_by_resort: dict[str, list[Proposal]] = {}
    for proposal in output.proposals:
        proposals_by_resort.setdefault(proposal.resort_id, []).append(proposal)

    for resort_id in sorted(proposals_by_resort):
        lines.extend([f"## {resort_id}", ""])
        for proposal in sorted(proposals_by_resort[resort_id], key=lambda item: item.field_path):
            lines.extend(
                [
                    f"### `{proposal.field_path}`",
                    "",
                    f"- Status: `{proposal.status}`",
                    f"- Current value: `{_json_inline(proposal.current_value)}`",
                    f"- Proposed value: `{_json_inline(proposal.proposed_value)}`",
                    f"- Source: `{proposal.source.source_url or proposal.source.source_name}`",
                    f"- Method: `{proposal.extraction_method}`",
                    f"- Confidence: `{proposal.confidence}`",
                ]
            )
            if proposal.evidence:
                lines.append(f"- Evidence: {proposal.evidence}")
            if proposal.validation_notes:
                lines.append(f"- Validation notes: {'; '.join(proposal.validation_notes)}")
            lines.append("")

    if not output.proposals:
        lines.extend(["No proposals generated.", ""])
    return "\n".join(lines)


def _json_inline(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)
```

- [ ] **Step 4: Run report test**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_write_run_outputs_creates_json_and_markdown_artifacts -q
```

Expected: test passes.

- [ ] **Step 5: Commit**

Run:

```bash
git add app/data/resort_acquisition/reports.py tests/test_resort_acquisition.py
git commit -m "feat: write resort acquisition artifacts"
```

---

### Task 8: CLI Orchestration

**Files:**
- Create: `app/data/resort_acquisition/run_catalog_acquisition.py`
- Modify: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing CLI smoke test**

Append:

```python
from app.data.resort_acquisition.run_catalog_acquisition import main as acquisition_main


def test_catalog_acquisition_cli_writes_outputs_for_registry_only_run(tmp_path) -> None:
    registry_path = tmp_path / "sources.json"
    catalog_path = tmp_path / "resorts.json"
    output_dir = tmp_path / "out"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "resorts": {
                    "test-resort": {
                        "official_urls": {"ski_pass": "https://example.com/prices"},
                        "regional_data_ids": {"osm_relation_id": "12345"},
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
                    "country": "France",
                }
            ]
        )
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
            "--skip-llm",
            "--skip-opendatahub",
        ]
    )

    assert exit_code == 0
    proposals = json.loads((output_dir / "proposals.json").read_text())
    field_paths = {proposal["field_path"] for proposal in proposals["proposals"]}
    assert "ski_pass_url" in field_paths
    assert "regional_data_ids.osm_relation_id" in field_paths
```

- [ ] **Step 2: Run CLI test and confirm failure**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_catalog_acquisition_cli_writes_outputs_for_registry_only_run -q
```

Expected: import failure because `run_catalog_acquisition.py` does not exist.

- [ ] **Step 3: Add CLI orchestration**

Create `app/data/resort_acquisition/run_catalog_acquisition.py`:

```python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.ai.gemini_client import GeminiClient
from app.data.loader import DEFAULT_RESORTS_PATH
from app.data.resort_acquisition.extractors import (
    extract_opendatahub_candidates,
    extract_registry_candidates,
)
from app.data.resort_acquisition.fetching import fetch_url, stable_content_hash
from app.data.resort_acquisition.llm_extract import extract_official_page_candidates
from app.data.resort_acquisition.models import AcquisitionRunOutput, CandidateFact, FetchLogEntry
from app.data.resort_acquisition.proposals import build_proposals, load_raw_catalog_by_resort
from app.data.resort_acquisition.registry import DEFAULT_SOURCE_REGISTRY_PATH, load_source_registry
from app.data.resort_acquisition.reports import write_run_outputs

OPENDATAHUB_SKI_AREA_URL = "https://tourism.api.opendatahub.com/v1/SkiArea/{ski_area_id}?language=en"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate resort catalog acquisition proposals.")
    parser.add_argument("--resort", action="append", default=[], help="Resort id to process. Can be repeated.")
    parser.add_argument("--country", help="Country filter from the current catalog.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-pages-per-resort", type=int, default=3)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--skip-opendatahub", action="store_true")
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_SOURCE_REGISTRY_PATH)
    parser.add_argument("--catalog-path", type=Path, default=DEFAULT_RESORTS_PATH)
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    generated_at = datetime.now(timezone.utc)
    registry = load_source_registry(args.registry_path)
    raw_catalog = load_raw_catalog_by_resort(args.catalog_path)
    selected_resorts = _select_resorts(raw_catalog, args.resort, args.country)
    if not selected_resorts:
        raise ValueError("No resorts selected")

    candidates: list[CandidateFact] = []
    fetch_log: list[FetchLogEntry] = []
    llm_client = None if args.skip_llm else GeminiClient()
    llm_cache_dir = output_dir / "llm-cache"

    for resort_id in selected_resorts:
        config = registry.resorts.get(resort_id)
        if config is None:
            fetch_log.append(
                FetchLogEntry(
                    resort_id=resort_id,
                    url="source registry",
                    fetched_at=generated_at,
                    status="skipped",
                    error="No source registry entry for selected resort",
                )
            )
            continue

        candidates.extend(extract_registry_candidates(resort_id, config, generated_at))

        if not args.skip_opendatahub and config.regional_data_ids.opendatahub_ski_area_id:
            source_url = OPENDATAHUB_SKI_AREA_URL.format(
                ski_area_id=config.regional_data_ids.opendatahub_ski_area_id
            )
            payload, log_entry = _fetch_json(resort_id, source_url, generated_at)
            fetch_log.append(log_entry)
            if payload is not None:
                candidates.extend(
                    extract_opendatahub_candidates(
                        resort_id,
                        config,
                        payload,
                        log_entry.fetched_at,
                        source_url=source_url,
                    )
                )

        if llm_client is not None:
            configured_pages = list(config.official_urls.items())
            configured_pages.extend(
                (f"provider:{name}", url)
                for name, url in sorted(config.provider_urls.items())
            )
            for page_role, url in configured_pages[: args.max_pages_per_resort]:
                page = fetch_url(url)
                fetch_log.append(
                    FetchLogEntry(
                        resort_id=resort_id,
                        url=url,
                        fetched_at=page.fetched_at,
                        status="failed" if page.error else "success",
                        status_code=page.status_code,
                        content_hash=page.content_hash,
                        extraction_method="official_page_llm",
                        truncated=page.truncated,
                        error=page.error,
                    )
                )
                if page.error:
                    continue
                extracted, errors = extract_official_page_candidates(
                    resort_id=resort_id,
                    page=page,
                    page_role=page_role,
                    llm_client=llm_client,
                    cache_dir=llm_cache_dir,
                )
                candidates.extend(extracted)
                for error in errors:
                    fetch_log.append(
                        FetchLogEntry(
                            resort_id=resort_id,
                            url=url,
                            fetched_at=page.fetched_at,
                            status="failed",
                            extraction_method="official_page_llm",
                            error=error,
                        )
                    )

    proposals = build_proposals(raw_catalog, candidates)
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=selected_resorts,
        proposals=proposals,
        candidates=candidates,
        fetch_log=fetch_log,
    )
    write_run_outputs(output_dir, output)
    print(
        f"Wrote {len(proposals)} proposals for {len(selected_resorts)} resorts to {output_dir}"
    )
    has_accepted_candidate = any(
        candidate.validation_status == "accepted" for candidate in candidates
    )
    return 0 if has_accepted_candidate else 2


def _select_resorts(
    raw_catalog: dict[str, dict[str, Any]],
    resort_ids: list[str],
    country: str | None,
) -> list[str]:
    if resort_ids:
        missing = sorted(set(resort_ids) - set(raw_catalog))
        if missing:
            raise ValueError(f"Unknown resort ids: {', '.join(missing)}")
        return sorted(dict.fromkeys(resort_ids))
    if country:
        return sorted(
            resort_id
            for resort_id, payload in raw_catalog.items()
            if payload.get("country") == country
        )
    return sorted(raw_catalog)


def _fetch_json(
    resort_id: str,
    url: str,
    started_at: datetime,
) -> tuple[dict[str, Any] | None, FetchLogEntry]:
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "SnowcastCatalogAcquisition/1.0"})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as error:
        return None, FetchLogEntry(
            resort_id=resort_id,
            url=url,
            fetched_at=started_at,
            status="failed",
            extraction_method="opendatahub",
            error=str(error),
        )
    content_hash = stable_content_hash(json.dumps(payload, sort_keys=True))
    return payload, FetchLogEntry(
        resort_id=resort_id,
        url=url,
        fetched_at=started_at,
        status="success",
        status_code=response.status_code,
        content_hash=content_hash,
        extraction_method="opendatahub",
    )


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI test**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_catalog_acquisition_cli_writes_outputs_for_registry_only_run -q
```

Expected: test passes.

- [ ] **Step 5: Run deterministic local smoke**

Run:

```bash
uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition --resort alta-badia --skip-llm --output-dir /tmp/catalog-acquisition-smoke
```

Expected output includes:

```text
Wrote
proposals for 1 resorts to /tmp/catalog-acquisition-smoke
```

Then inspect:

```bash
ls /tmp/catalog-acquisition-smoke
```

Expected files:

```text
evidence.md
fetch-log.json
proposals.json
source-snapshots
```

- [ ] **Step 6: Commit**

Run:

```bash
git add app/data/resort_acquisition/run_catalog_acquisition.py tests/test_resort_acquisition.py
git commit -m "feat: add resort acquisition cli"
```

---

### Task 9: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/catalog-acquisition.yml`
- Modify: `tests/test_resort_acquisition.py`

- [ ] **Step 1: Write failing workflow shape test**

Append:

```python
def test_catalog_acquisition_workflow_is_manual_read_only_and_artifact_only() -> None:
    workflow = Path(".github/workflows/catalog-acquisition.yml").read_text()

    assert "workflow_dispatch:" in workflow
    assert "contents: read" in workflow
    assert "upload-artifact" in workflow
    assert "git push" not in workflow
    assert "create-pull-request" not in workflow
    assert "pull-request" not in workflow
```

- [ ] **Step 2: Run workflow test and confirm failure**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_catalog_acquisition_workflow_is_manual_read_only_and_artifact_only -q
```

Expected: file-not-found failure because the workflow does not exist.

- [ ] **Step 3: Add manual artifact workflow**

Create `.github/workflows/catalog-acquisition.yml`:

```yaml
name: Catalog Acquisition

on:
  workflow_dispatch:
    inputs:
      resorts:
        description: "Comma-separated resort ids. Leave empty to use country or all resorts."
        required: false
        type: string
      country:
        description: "Optional exact country filter from app/data/resorts.json."
        required: false
        type: string
      skip_llm:
        description: "Skip LLM extraction and run deterministic sources only."
        required: true
        default: true
        type: boolean
      max_pages_per_resort:
        description: "Maximum official/provider pages to fetch per resort when LLM extraction is enabled."
        required: true
        default: "3"
        type: string

permissions:
  contents: read

jobs:
  catalog-acquisition:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Install dependencies
        run: uv sync --dev --no-config

      - name: Validate checked-in catalog
        run: uv run --no-config python -m app.data.validate_resort_catalog

      - name: Build acquisition arguments
        id: args
        shell: bash
        run: |
          set -euo pipefail
          args=()
          if [ -n "${{ inputs.resorts }}" ]; then
            IFS=',' read -ra resorts <<< "${{ inputs.resorts }}"
            for resort in "${resorts[@]}"; do
              trimmed="$(echo "$resort" | xargs)"
              if [ -n "$trimmed" ]; then
                args+=(--resort "$trimmed")
              fi
            done
          fi
          if [ -n "${{ inputs.country }}" ]; then
            args+=(--country "${{ inputs.country }}")
          fi
          if [ "${{ inputs.skip_llm }}" = "true" ]; then
            args+=(--skip-llm)
          fi
          args+=(--max-pages-per-resort "${{ inputs.max_pages_per_resort }}")
          printf 'args<<EOF\n' >> "$GITHUB_OUTPUT"
          printf '%q ' "${args[@]}" >> "$GITHUB_OUTPUT"
          printf '\nEOF\n' >> "$GITHUB_OUTPUT"

      - name: Run catalog acquisition
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: >
          uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition
          ${{ steps.args.outputs.args }}
          --output-dir artifacts/catalog-acquisition

      - name: Upload acquisition artifacts
        uses: actions/upload-artifact@v4
        with:
          name: catalog-acquisition
          path: artifacts/catalog-acquisition
          if-no-files-found: error
```

- [ ] **Step 4: Run workflow test**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py::test_catalog_acquisition_workflow_is_manual_read_only_and_artifact_only -q
```

Expected: test passes.

- [ ] **Step 5: Commit**

Run:

```bash
git add .github/workflows/catalog-acquisition.yml tests/test_resort_acquisition.py
git commit -m "ci: add manual catalog acquisition workflow"
```

---

### Task 10: Documentation And Artifact Hygiene

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/engineering-notes.md`

- [ ] **Step 1: Add artifact ignore rule**

Add this line to `.gitignore`:

```gitignore
artifacts/
```

- [ ] **Step 2: Add README usage section**

In `README.md`, after the catalog validator command, add:

````markdown
To generate source-backed catalog proposals without changing checked-in catalog data:

```bash
uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition --resort alta-badia --skip-llm --output-dir artifacts/catalog-acquisition
```

The acquisition command writes review artifacts only:
- `proposals.json` for normalized candidate facts and current-value comparisons
- `evidence.md` for human review by resort and field
- `fetch-log.json` for source status, timestamps, hashes, and extraction errors

Accepted values must still be applied through a reviewed change to `app/data/resorts.json` and `app/data/resort_trust_manifest.json`, followed by:

```bash
uv run --no-config python -m app.data.validate_resort_catalog
```
````

- [ ] **Step 3: Add engineering note**

Append this section to `docs/engineering-notes.md`:

```markdown
## Resort Catalog Acquisition

Approved resort catalog values remain git-canonical in `app/data/resorts.json` and `app/data/resort_trust_manifest.json`. The acquisition pipeline is intentionally artifact-only: it fetches configured official/open sources, extracts candidate facts, compares them with current catalog values, and writes evidence for human review.

The application must not read acquisition artifacts. Accepted facts are promoted through normal catalog edits and the catalog validator. This keeps the product surface stable while allowing source-backed data collection, repeated refresh runs, and a future migration toward richer acquisition storage if volume requires it.
```

- [ ] **Step 4: Run docs-free focused tests**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py -q
```

Expected: all resort acquisition tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add .gitignore README.md docs/engineering-notes.md
git commit -m "docs: document resort catalog acquisition artifacts"
```

---

### Task 11: Final Verification

**Files:**
- All files from previous tasks

- [ ] **Step 1: Run catalog validator**

Run:

```bash
uv run --no-config python -m app.data.validate_resort_catalog
```

Expected output:

```text
Catalog validation passed:
```

- [ ] **Step 2: Run deterministic acquisition smoke**

Run:

```bash
uv run --no-config python -m app.data.resort_acquisition.run_catalog_acquisition --resort alta-badia --skip-llm --output-dir /tmp/catalog-acquisition-smoke
```

Expected: command exits `0`, and `/tmp/catalog-acquisition-smoke/evidence.md` includes Alta Badia proposals for OpenDataHub-backed fields when the OpenDataHub API is reachable. If the API fetch fails, `fetch-log.json` records the failure and registry candidates are still written.

- [ ] **Step 3: Run focused tests**

Run:

```bash
uv run --no-config pytest tests/test_resort_acquisition.py tests/test_catalog_validation.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Run lint**

Run:

```bash
uv run --no-config ruff check app tests
```

Expected: no ruff violations.

- [ ] **Step 5: Run full test suite**

Run:

```bash
uv run --no-config pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Review generated artifacts**

Run:

```bash
sed -n '1,200p' /tmp/catalog-acquisition-smoke/evidence.md
sed -n '1,120p' /tmp/catalog-acquisition-smoke/fetch-log.json
```

Confirm:

- `evidence.md` is grouped by resort and field.
- Every proposal includes status, current value, proposed value, source, method, confidence, and evidence when available.
- `fetch-log.json` includes status, timestamp, URL, method, and error text for failures.
- No command modified `app/data/resorts.json` or `app/data/resort_trust_manifest.json`.

- [ ] **Step 7: Final commit if verification required file edits**

Run only if verification led to edits:

```bash
git add app/data/resort_acquisition tests/test_resort_acquisition.py .github/workflows/catalog-acquisition.yml .gitignore README.md docs/engineering-notes.md
git commit -m "fix: stabilize resort acquisition verification"
```
