import json
import math
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.ai.llm_client import LLMClient
from app.data.resort_acquisition.discovery import (
    OPENDATAHUB_SKI_AREA_INDEX_URL,
    discover_opendatahub_id_candidates,
    normalize_ski_area_name,
)
from app.data.resort_acquisition.extractors import (
    extract_opendatahub_candidates,
    extract_registry_candidates,
)
from app.data.resort_acquisition.fetching import (
    FetchedPage,
    fetch_url,
    html_to_text,
    stable_content_hash,
)
from app.data.resort_acquisition.llm_extract import extract_official_page_candidates
from app.data.resort_acquisition.models import (
    AcquisitionRunOutput,
    CandidateFact,
    FetchLogEntry,
    LiftPassPriceCandidate,
    Proposal,
    ProposalTarget,
    RegionalDataIds,
    ResortSourceConfig,
    SourceReference,
    SourceRegistry,
)
from app.data.resort_acquisition.proposals import (
    build_proposals,
    load_raw_catalog_by_resort,
)
from app.data.resort_acquisition.registry import load_source_registry
from app.data.resort_acquisition.reports import write_run_outputs
from app.data.resort_acquisition.run_catalog_acquisition import (
    _fetch_json,
)
from app.data.resort_acquisition.run_catalog_acquisition import (
    main as acquisition_main,
)
from app.data.resort_acquisition.targeting import (
    proposal_targets_for_single_area_source,
)
from app.data.resort_acquisition.wikidata import extract_wikidata_candidates

ALTA_BADIA_OPENDATAHUB_ID = "SKI04EBE61F5AA0473F871AF0297887D6C2"


def _source() -> SourceReference:
    return SourceReference(
        source_type="opendatahub",
        source_url="https://tourism.api.opendatahub.com/v1/SkiArea/example",
    )


def test_candidate_fact_requires_non_empty_field_path() -> None:
    source = _source()

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


@pytest.mark.parametrize("field_path", [" ", "stats. .vertical"])
def test_candidate_fact_rejects_whitespace_only_field_path_segments(
    field_path: str,
) -> None:
    source = _source()

    with pytest.raises(ValidationError):
        CandidateFact(
            resort_id="alta-badia",
            field_path=field_path,
            proposed_value=130.0,
            source=source,
            extraction_method="opendatahub",
            fetched_at=datetime.fromisoformat("2026-05-04T10:00:00+00:00"),
            confidence=0.95,
        )


def test_candidate_fact_rejects_non_json_serializable_nested_value() -> None:
    with pytest.raises(ValidationError):
        CandidateFact(
            resort_id="alta-badia",
            field_path="stats.vertical_m",
            proposed_value={"bad": object()},
            source=_source(),
            extraction_method="opendatahub",
            fetched_at=datetime.fromisoformat("2026-05-04T10:00:00+00:00"),
            confidence=0.95,
        )


def test_candidate_fact_rejects_non_finite_nested_float() -> None:
    with pytest.raises(ValidationError):
        CandidateFact(
            resort_id="alta-badia",
            field_path="stats.vertical_m",
            proposed_value={"bad": math.inf},
            source=_source(),
            extraction_method="opendatahub",
            fetched_at=datetime.fromisoformat("2026-05-04T10:00:00+00:00"),
            confidence=0.95,
        )


def test_source_reference_rejects_whitespace_only_url_and_name() -> None:
    with pytest.raises(ValidationError):
        SourceReference(source_type="official", source_url=" ")

    with pytest.raises(ValidationError):
        SourceReference(source_type="official", source_name="\t")


@pytest.mark.parametrize("field_path", [" stats.vertical", "stats.vertical "])
def test_candidate_fact_rejects_field_path_with_outer_whitespace(
    field_path: str,
) -> None:
    with pytest.raises(ValidationError):
        CandidateFact(
            resort_id="alta-badia",
            field_path=field_path,
            proposed_value=130.0,
            source=_source(),
            extraction_method="opendatahub",
            fetched_at=datetime.fromisoformat("2026-05-04T10:00:00+00:00"),
            confidence=0.95,
        )


def test_proposal_rejects_blank_field_path_segments() -> None:
    with pytest.raises(ValidationError):
        Proposal(
            resort_id="alta-badia",
            field_path="stats..vertical",
            current_value=120.0,
            proposed_value=130.0,
            status="changed",
            source=_source(),
            extraction_method="opendatahub",
            confidence=0.95,
        )


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
            field_path="season_dates_url",
            proposed_value="https://example.com/season",
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
    statuses = {
        (proposal.field_path, proposal.proposed_value): proposal.status
        for proposal in proposals
    }

    assert statuses[("total_lift_count", 20)] == "same"
    assert statuses[("ski_pass_url", "https://example.com/other-prices")] == "changed"
    assert statuses[("season_dates_url", "https://example.com/season")] == "new"
    assert statuses[("total_piste_km", 130)] == "conflict"
    assert statuses[("total_piste_km", 125)] == "conflict"


def test_build_proposals_does_not_conflict_repeatable_list_items() -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    raw_catalog = {
        "test-resort": {
            "resort_id": "test-resort",
        }
    }
    candidates = [
        CandidateFact(
            resort_id="test-resort",
            field_path="lift_pass_prices",
            proposed_value={
                "duration_days": 1,
                "audience": "adult",
                "amount": 75,
                "currency": "EUR",
                "price_kind": "fixed",
            },
            source=source,
            extraction_method="official_page_llm",
            fetched_at=fetched_at,
            confidence=0.85,
        ),
        CandidateFact(
            resort_id="test-resort",
            field_path="lift_pass_prices",
            proposed_value={
                "duration_days": 6,
                "audience": "adult",
                "amount": 390,
                "currency": "EUR",
                "price_kind": "fixed",
            },
            source=source,
            extraction_method="official_page_llm",
            fetched_at=fetched_at,
            confidence=0.9,
        ),
    ]

    proposals = build_proposals(raw_catalog, candidates)

    assert [proposal.status for proposal in proposals] == ["new", "new"]


def test_build_proposals_reads_destination_target_current_value() -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    raw_catalog = {
        "test-resort": {
            "resort_id": "test-resort",
            "latitude": 46.5,
            "ski_areas": [
                {
                    "ski_area_id": "test-resort-ski-area",
                    "latitude": 46.7,
                }
            ],
        }
    }

    proposals = build_proposals(
        raw_catalog,
        [
            CandidateFact(
                resort_id="test-resort",
                target=ProposalTarget(
                    entity_type="destination", entity_id="test-resort"
                ),
                field_path="latitude",
                proposed_value=46.6,
                source=source,
                extraction_method="opendatahub",
                fetched_at=fetched_at,
                confidence=0.95,
            )
        ],
    )

    assert len(proposals) == 1
    assert proposals[0].target.entity_type == "destination"
    assert proposals[0].target.entity_id == "test-resort"
    assert proposals[0].current_value == 46.5
    assert proposals[0].status == "changed"


def test_build_proposals_reads_ski_area_target_current_value() -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    raw_catalog = {
        "test-resort": {
            "resort_id": "test-resort",
            "latitude": 46.5,
            "ski_areas": [
                {
                    "ski_area_id": "test-resort-ski-area",
                    "latitude": 46.7,
                }
            ],
        }
    }

    proposals = build_proposals(
        raw_catalog,
        [
            CandidateFact(
                resort_id="test-resort",
                target=ProposalTarget(
                    entity_type="ski_area", entity_id="test-resort-ski-area"
                ),
                field_path="latitude",
                proposed_value=46.8,
                source=source,
                extraction_method="opendatahub",
                fetched_at=fetched_at,
                confidence=0.95,
            )
        ],
    )

    assert len(proposals) == 1
    assert proposals[0].target.entity_type == "ski_area"
    assert proposals[0].target.entity_id == "test-resort-ski-area"
    assert proposals[0].current_value == 46.7
    assert proposals[0].status == "changed"


def test_build_proposals_marks_warning_candidate() -> None:
    source = SourceReference(
        source_type="dem",
        source_url="https://api.opentopodata.org/v1/eudem25m",
    )
    fetched_at = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)
    raw_catalog = {
        "test-resort": {
            "resort_id": "test-resort",
            "ski_areas": [{"ski_area_id": "test-ski-area", "base_elevation_m": 1500}],
        }
    }

    proposals = build_proposals(
        raw_catalog,
        [
            CandidateFact(
                resort_id="test-resort",
                target=ProposalTarget(
                    entity_type="ski_area", entity_id="test-ski-area"
                ),
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


@pytest.mark.parametrize("ski_area_id", [None, "", " ", 123])
def test_targeting_skips_invalid_primary_ski_area_id(ski_area_id: object) -> None:
    resort_payload = {
        "resort_id": "alta-badia",
        "latitude": 46.5536,
        "ski_areas": [{"ski_area_id": ski_area_id, "latitude": 46.5536}],
    }

    targets = proposal_targets_for_single_area_source(
        resort_id="alta-badia",
        resort_payload=resort_payload,
        field_path="latitude",
        primary_entity_type="ski_area",
    )

    assert targets == []


def test_build_proposals_rejects_missing_ski_area_target() -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    raw_catalog = {
        "test-resort": {
            "resort_id": "test-resort",
            "ski_areas": [
                {
                    "ski_area_id": "other-ski-area",
                    "latitude": 46.7,
                }
            ],
        }
    }

    proposals = build_proposals(
        raw_catalog,
        [
            CandidateFact(
                resort_id="test-resort",
                target=ProposalTarget(
                    entity_type="ski_area", entity_id="missing-ski-area"
                ),
                field_path="latitude",
                proposed_value=46.8,
                source=source,
                extraction_method="opendatahub",
                fetched_at=fetched_at,
                confidence=0.95,
            )
        ],
    )

    assert len(proposals) == 1
    assert proposals[0].status == "rejected"
    assert proposals[0].current_value is None
    assert proposals[0].validation_notes == [
        "Target ski_area 'missing-ski-area' not found in resort catalog"
    ]


def test_build_proposals_conflicts_lift_pass_prices_with_same_identity() -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    raw_catalog = {
        "test-resort": {
            "resort_id": "test-resort",
        }
    }
    candidates = [
        CandidateFact(
            resort_id="test-resort",
            field_path="lift_pass_prices",
            proposed_value={
                "duration_days": 6,
                "audience": "adult",
                "amount": 390,
                "currency": "EUR",
                "price_kind": "fixed",
                "season_label": "2025/26 winter",
            },
            source=source,
            extraction_method="official_page_llm",
            fetched_at=fetched_at,
            confidence=0.9,
        ),
        CandidateFact(
            resort_id="test-resort",
            field_path="lift_pass_prices",
            proposed_value={
                "duration_days": 6,
                "audience": "adult",
                "amount": 410,
                "currency": "EUR",
                "price_kind": "fixed",
                "season_label": "2025/26 winter",
            },
            source=source,
            extraction_method="official_page_llm",
            fetched_at=fetched_at,
            confidence=0.85,
        ),
    ]

    proposals = build_proposals(raw_catalog, candidates)

    assert [proposal.status for proposal in proposals] == ["conflict", "conflict"]


def test_load_raw_catalog_by_resort_indexes_valid_catalog(tmp_path) -> None:
    catalog_path = tmp_path / "resorts.json"
    catalog_path.write_text(
        json.dumps(
            [
                {"resort_id": "alpha", "total_lift_count": 10},
                {"resort_id": "bravo", "total_lift_count": 20},
            ]
        )
    )

    catalog = load_raw_catalog_by_resort(catalog_path)

    assert set(catalog) == {"alpha", "bravo"}
    assert catalog["alpha"]["total_lift_count"] == 10


@pytest.mark.parametrize(
    "payload",
    [
        {"resort_id": "alpha"},
        ["not-an-object"],
        [{"resort_id": ""}],
        [{"resort_id": " "}],
    ],
)
def test_load_raw_catalog_by_resort_rejects_invalid_catalog_shape(
    tmp_path,
    payload: object,
) -> None:
    catalog_path = tmp_path / "resorts.json"
    catalog_path.write_text(json.dumps(payload))

    with pytest.raises(ValueError):
        load_raw_catalog_by_resort(catalog_path)


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


def test_lift_pass_price_candidate_rejects_unknown_with_amount() -> None:
    with pytest.raises(ValidationError):
        LiftPassPriceCandidate(
            duration_days=6,
            audience="adult",
            amount=390.0,
            currency="EUR",
            price_kind="unknown",
            source_url="https://example.com/prices",
            confidence=0.9,
        )


def test_lift_pass_price_candidate_rejects_fixed_with_range_fields() -> None:
    with pytest.raises(ValidationError):
        LiftPassPriceCandidate(
            duration_days=6,
            audience="adult",
            amount=390.0,
            amount_min=350.0,
            amount_max=420.0,
            currency="EUR",
            price_kind="fixed",
            source_url="https://example.com/prices",
            confidence=0.9,
        )


def test_html_to_text_removes_script_text_and_collapses_whitespace() -> None:
    html = (
        "<html><head><script>ignore()</script></head>"
        "<body><h1>Prices</h1><p>Adult 6 days EUR 390</p></body></html>"
    )

    text = html_to_text(html)

    assert text == "Prices Adult 6 days EUR 390"
    assert "ignore" not in text


def test_stable_content_hash_is_sha256_hex() -> None:
    digest = stable_content_hash("Adult 6 days EUR 390")

    assert len(digest) == 64
    assert digest == stable_content_hash("Adult 6 days EUR 390")


class _FakeResponse:
    def __init__(
        self,
        *,
        text: str = "<h1>Prices</h1><p>Adult 6 days EUR 390</p>",
        url: str = "https://example.com/prices",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
        error: Exception | None = None,
    ) -> None:
        self.text = text
        self.url = url
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content if content is not None else text.encode("utf-8")
        self._error = error

    def raise_for_status(self) -> None:
        if self._error is not None:
            raise self._error


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response

    def client_class(self):
        response = self.response

        class FakeClient:
            def __init__(self, *, timeout: float, follow_redirects: bool) -> None:
                self.timeout = timeout
                self.follow_redirects = follow_redirects

            def __enter__(self) -> "FakeClient":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def get(self, url: str, *, headers: dict[str, str]) -> _FakeResponse:
                return response

        return FakeClient


def _use_fake_fetch(monkeypatch, response: _FakeResponse) -> None:
    monkeypatch.setattr(
        "app.data.resort_acquisition.fetching.httpx.Client",
        _FakeClient(response).client_class(),
    )


def test_fetch_url_accepts_positional_max_chars(monkeypatch) -> None:
    _use_fake_fetch(monkeypatch, _FakeResponse())

    fetched = fetch_url("https://example.com/prices", 6)

    assert fetched.text == "Prices"
    assert fetched.truncated is True


def test_fetch_url_http_error_returns_status_code_and_error(monkeypatch) -> None:
    response = _FakeResponse(status_code=404)
    response._error = httpx.HTTPStatusError(
        "not found",
        request=httpx.Request("GET", "https://example.com/missing"),
        response=httpx.Response(
            404,
            request=httpx.Request("GET", "https://example.com/missing"),
        ),
    )
    _use_fake_fetch(monkeypatch, response)

    fetched = fetch_url("https://example.com/missing")

    assert fetched.status_code == 404
    assert fetched.text == ""
    assert fetched.content_hash is None
    assert fetched.truncated is False
    assert "not found" in fetched.error


def test_fetch_url_retries_transient_transport_error(monkeypatch) -> None:
    calls: list[str] = []

    class FlakyClient:
        def __init__(self, *, timeout: float, follow_redirects: bool) -> None:
            self.timeout = timeout
            self.follow_redirects = follow_redirects

        def __enter__(self) -> "FlakyClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def get(self, url: str, *, headers: dict[str, str]) -> _FakeResponse:
            calls.append(url)
            if len(calls) == 1:
                raise httpx.ConnectError(
                    "temporary DNS failure",
                    request=httpx.Request("GET", url),
                )
            return _FakeResponse(text="<p>Recovered</p>")

    monkeypatch.setattr(
        "app.data.resort_acquisition.fetching.httpx.Client",
        FlakyClient,
    )

    fetched = fetch_url("https://example.com/prices")

    assert fetched.error is None
    assert fetched.text == "Recovered"
    assert calls == ["https://example.com/prices", "https://example.com/prices"]


def test_fetch_url_preserves_final_url_from_success_response(monkeypatch) -> None:
    _use_fake_fetch(
        monkeypatch,
        _FakeResponse(
            url="https://example.com/final", headers={"content-type": "text/html"}
        ),
    )

    fetched = fetch_url("https://example.com/start")

    assert fetched.url == "https://example.com/start"
    assert fetched.final_url == "https://example.com/final"


def test_fetch_url_hashes_full_extracted_text_before_truncation(monkeypatch) -> None:
    _use_fake_fetch(monkeypatch, _FakeResponse(text="<p>abcdef</p>"))

    fetched = fetch_url("https://example.com/prices", 3)

    assert fetched.text == "abc"
    assert fetched.truncated is True
    assert fetched.content_hash == stable_content_hash("abcdef")


def test_fetch_url_rejects_unsupported_content_type(monkeypatch) -> None:
    _use_fake_fetch(
        monkeypatch,
        _FakeResponse(headers={"content-type": "application/pdf"}),
    )

    fetched = fetch_url("https://example.com/prices.pdf")

    assert fetched.status_code == 200
    assert fetched.text == ""
    assert fetched.content_hash is None
    assert fetched.truncated is False
    assert fetched.error == "Unsupported content type: application/pdf"


def test_fetch_url_rejects_oversized_response_before_parsing(monkeypatch) -> None:
    _use_fake_fetch(
        monkeypatch,
        _FakeResponse(text="<p>abcdef</p>", content=b"abcdef"),
    )

    def fail_if_called(html: str) -> str:
        raise AssertionError("html_to_text should not parse oversized responses")

    monkeypatch.setattr(
        "app.data.resort_acquisition.fetching.html_to_text",
        fail_if_called,
    )

    fetched = fetch_url("https://example.com/prices", max_bytes=3)

    assert fetched.status_code == 200
    assert fetched.text == ""
    assert fetched.content_hash is None
    assert fetched.truncated is False
    assert fetched.error == "Response too large: 6 bytes"


def test_load_source_registry_validates_resort_entries(tmp_path) -> None:
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "resorts": {
                    "alta-badia": {
                        "regional_data_ids": {
                            "opendatahub_ski_area_id": ALTA_BADIA_OPENDATAHUB_ID
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
                        "official_urls": {"blog": "https://example.com/blog"}
                    }
                },
            }
        )
    )

    with pytest.raises(ValueError, match="unsupported official URL role"):
        load_source_registry(registry_path)


def test_load_source_registry_rejects_missing_official_urls(tmp_path) -> None:
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "resorts": {
                    "alta-badia": {
                        "regional_data_ids": {
                            "opendatahub_ski_area_id": ALTA_BADIA_OPENDATAHUB_ID
                        }
                    }
                },
            }
        )
    )

    with pytest.raises(ValueError, match="official_urls"):
        load_source_registry(registry_path)


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


def _opendatahub_index_record(
    *,
    ski_area_id: str = "SKI123",
    title: str = "Alta Badia ski area",
    closed_data: bool = False,
    license_name: str = "CC0",
) -> dict[str, object]:
    return {
        "Id": ski_area_id,
        "Detail.en.Title": title,
        "Shortname": "DSS3",
        "Latitude": 46.5631,
        "Longitude": 11.8975,
        "TotalSlopeKm": "130",
        "LicenseInfo": {
            "ClosedData": closed_data,
            "License": license_name,
        },
    }


def test_normalize_ski_area_name_strips_ski_area_suffix() -> None:
    assert normalize_ski_area_name("Alta Badia ski area") == "alta badia"
    assert normalize_ski_area_name("Cortina d'Ampezzo") == "cortina d ampezzo"


def test_discover_opendatahub_id_candidates_matches_exact_normalized_name() -> None:
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)

    candidates = discover_opendatahub_id_candidates(
        raw_catalog_by_resort={"alta-badia": {"name": "Alta Badia"}},
        selected_resorts=["alta-badia"],
        registry=SourceRegistry(version=1, resorts={}),
        payload=[_opendatahub_index_record()],
        fetched_at=fetched_at,
        source_url=OPENDATAHUB_SKI_AREA_INDEX_URL,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.resort_id == "alta-badia"
    assert candidate.field_path == "regional_data_ids.opendatahub_ski_area_id"
    assert candidate.proposed_value == "SKI123"
    assert candidate.extraction_method == "opendatahub_discovery"
    assert candidate.source.source_type == "opendatahub"
    assert candidate.source.license == "CC0"
    assert candidate.evidence is not None
    assert "Matched catalog name 'Alta Badia'" in candidate.evidence
    assert "OpenDataHub title 'Alta Badia ski area'" in candidate.evidence
    assert "ClosedData=false" in candidate.evidence


def test_discover_opendatahub_id_candidates_ignores_closed_data_records() -> None:
    candidates = discover_opendatahub_id_candidates(
        raw_catalog_by_resort={"alta-badia": {"name": "Alta Badia"}},
        selected_resorts=["alta-badia"],
        registry=SourceRegistry(version=1, resorts={}),
        payload=[
            _opendatahub_index_record(
                ski_area_id="SKICLOSED",
                closed_data=True,
                license_name="Closed",
            )
        ],
        fetched_at=datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
        source_url=OPENDATAHUB_SKI_AREA_INDEX_URL,
    )

    assert candidates == []


def test_discover_opendatahub_id_candidates_suppresses_configured_same_id() -> None:
    candidates = discover_opendatahub_id_candidates(
        raw_catalog_by_resort={"alta-badia": {"name": "Alta Badia"}},
        selected_resorts=["alta-badia"],
        registry=SourceRegistry(
            version=1,
            resorts={
                "alta-badia": ResortSourceConfig(
                    regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
                )
            },
        ),
        payload=[_opendatahub_index_record()],
        fetched_at=datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
        source_url=OPENDATAHUB_SKI_AREA_INDEX_URL,
    )

    assert candidates == []


def test_discover_opendatahub_id_candidates_conflicts_with_configured_id() -> None:
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    registry = SourceRegistry(
        version=1,
        resorts={
            "alta-badia": ResortSourceConfig(
                regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKIOLD")
            )
        },
    )

    discovery_candidates = discover_opendatahub_id_candidates(
        raw_catalog_by_resort={"alta-badia": {"name": "Alta Badia"}},
        selected_resorts=["alta-badia"],
        registry=registry,
        payload=[_opendatahub_index_record(ski_area_id="SKINEW")],
        fetched_at=fetched_at,
        source_url=OPENDATAHUB_SKI_AREA_INDEX_URL,
    )

    proposals = build_proposals(
        {"alta-badia": {"resort_id": "alta-badia", "name": "Alta Badia"}},
        [
            *extract_registry_candidates(
                "alta-badia",
                registry.resorts["alta-badia"],
                fetched_at,
            ),
            *discovery_candidates,
        ],
    )
    id_proposals = [
        proposal
        for proposal in proposals
        if proposal.field_path == "regional_data_ids.opendatahub_ski_area_id"
    ]

    assert {proposal.proposed_value for proposal in id_proposals} == {
        "SKIOLD",
        "SKINEW",
    }
    assert {proposal.status for proposal in id_proposals} == {"conflict"}


def test_discover_opendatahub_id_candidates_skips_ambiguous_matches() -> None:
    candidates = discover_opendatahub_id_candidates(
        raw_catalog_by_resort={"alta-badia": {"name": "Alta Badia"}},
        selected_resorts=["alta-badia"],
        registry=SourceRegistry(version=1, resorts={}),
        payload=[
            _opendatahub_index_record(ski_area_id="SKI1"),
            _opendatahub_index_record(ski_area_id="SKI2"),
        ],
        fetched_at=datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
        source_url=OPENDATAHUB_SKI_AREA_INDEX_URL,
    )

    assert candidates == []


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

    values = {
        candidate.field_path: candidate.proposed_value for candidate in candidates
    }
    assert values["total_lift_count"] == 53
    assert values["total_piste_km"] == 130.0
    assert values["piste_km_by_difficulty"] == {
        "beginner": 74.0,
        "intermediate": 47.0,
        "advanced": 9.0,
    }
    assert values["trail_map_url"] == "https://example.com/map.pdf"


def test_extract_opendatahub_candidates_targets_existing_ski_area_fields() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    resort_payload = {
        "resort_id": "alta-badia",
        "name": "Alta Badia",
        "latitude": 46.0,
        "longitude": 11.0,
        "base_elevation_m": 1200,
        "summit_elevation_m": 2500,
        "season_start_month": 11,
        "season_end_month": 5,
        "ski_areas": [
            {
                "ski_area_id": "alta-badia-ski-area",
                "name": "Alta Badia",
                "latitude": 46.5536,
                "longitude": 11.8997,
                "base_elevation_m": 1324,
                "summit_elevation_m": 2550,
                "season_start_month": 12,
                "season_end_month": 4,
            }
        ],
    }
    payload = {
        "Latitude": 46.5631,
        "Longitude": 11.8975,
        "AltitudeFrom": 1324,
        "AltitudeTo": 2778,
        "OperationSchedule": [
            {
                "Start": "2025-12-04T00:00:00",
                "Stop": "2026-04-04T00:00:00",
            }
        ],
        "LicenseInfo": {"ClosedData": False, "License": "CC0"},
    }

    candidates = extract_opendatahub_candidates(
        "alta-badia",
        config,
        payload,
        datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
        source_url="https://tourism.api.opendatahub.com/v1/SkiArea/SKI123?language=en",
        resort_payload=resort_payload,
    )

    values = {
        (
            candidate.target.entity_type,
            candidate.target.entity_id,
            candidate.field_path,
        ): candidate.proposed_value
        for candidate in candidates
    }
    ski_area_key_prefix = ("ski_area", "alta-badia-ski-area")
    assert values[(*ski_area_key_prefix, "latitude")] == 46.5631
    assert values[(*ski_area_key_prefix, "longitude")] == 11.8975
    assert values[(*ski_area_key_prefix, "base_elevation_m")] == 1324
    assert values[(*ski_area_key_prefix, "summit_elevation_m")] == 2778
    assert values[(*ski_area_key_prefix, "season_start_month")] == 12
    assert values[(*ski_area_key_prefix, "season_end_month")] == 4
    latitude_candidate = next(
        candidate
        for candidate in candidates
        if candidate.target.entity_type == "ski_area"
        and candidate.field_path == "latitude"
    )
    assert latitude_candidate.evidence is not None
    assert "OpenDataHub Latitude=46.5631" in latitude_candidate.evidence
    assert "ClosedData=false" in latitude_candidate.evidence


def test_extract_opendatahub_candidates_mirrors_duplicated_destination_field() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    resort_payload = {
        "resort_id": "alta-badia",
        "latitude": 46.5536,
        "ski_areas": [
            {
                "ski_area_id": "alta-badia-ski-area",
                "latitude": 46.5536,
            }
        ],
    }
    payload = {
        "Latitude": 46.5631,
        "LicenseInfo": {"ClosedData": False, "License": "CC0"},
    }

    candidates = extract_opendatahub_candidates(
        "alta-badia",
        config,
        payload,
        datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
        source_url="https://tourism.api.opendatahub.com/v1/SkiArea/SKI123?language=en",
        resort_payload=resort_payload,
    )

    targets = {
        (candidate.target.entity_type, candidate.target.entity_id)
        for candidate in candidates
        if candidate.field_path == "latitude"
    }
    assert targets == {
        ("destination", "alta-badia"),
        ("ski_area", "alta-badia-ski-area"),
    }


def test_extract_opendatahub_candidates_skips_diverged_destination_mirror() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    resort_payload = {
        "resort_id": "alta-badia",
        "latitude": 46.0,
        "ski_areas": [
            {
                "ski_area_id": "alta-badia-ski-area",
                "latitude": 46.5536,
            }
        ],
    }
    payload = {
        "Latitude": 46.5631,
        "LicenseInfo": {"ClosedData": False, "License": "CC0"},
    }

    candidates = extract_opendatahub_candidates(
        "alta-badia",
        config,
        payload,
        datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
        source_url="https://tourism.api.opendatahub.com/v1/SkiArea/SKI123?language=en",
        resort_payload=resort_payload,
    )

    targets = {
        (candidate.target.entity_type, candidate.target.entity_id)
        for candidate in candidates
        if candidate.field_path == "latitude"
    }
    assert targets == {("ski_area", "alta-badia-ski-area")}


def test_extract_opendatahub_candidates_does_not_mirror_multiple_ski_areas() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    resort_payload = {
        "resort_id": "linked-resort",
        "latitude": 46.5536,
        "ski_areas": [
            {
                "ski_area_id": "primary-ski-area",
                "latitude": 46.5536,
            },
            {
                "ski_area_id": "secondary-ski-area",
                "latitude": 46.5536,
            },
        ],
    }
    payload = {
        "Latitude": 46.5631,
        "LicenseInfo": {"ClosedData": False, "License": "CC0"},
    }

    candidates = extract_opendatahub_candidates(
        "linked-resort",
        config,
        payload,
        datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
        source_url="https://tourism.api.opendatahub.com/v1/SkiArea/SKI123?language=en",
        resort_payload=resort_payload,
    )

    assert all(
        candidate.target.entity_type != "destination"
        for candidate in candidates
        if candidate.field_path == "latitude"
    )


@pytest.mark.parametrize("lift_count", ["53.9", 53.9])
def test_extract_opendatahub_candidates_skips_fractional_lift_count(
    lift_count: str | float,
) -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    payload = {
        "LiftCount": lift_count,
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

    field_paths = {candidate.field_path for candidate in candidates}
    assert "total_lift_count" not in field_paths


def test_extract_opendatahub_candidates_skips_negative_total_slope_km() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    payload = {
        "TotalSlopeKm": "-130",
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

    field_paths = {candidate.field_path for candidate in candidates}
    assert "total_piste_km" not in field_paths


def test_extract_opendatahub_candidates_skips_non_numeric_lift_count() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    payload = {
        "LiftCount": "not-a-number",
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

    field_paths = {candidate.field_path for candidate in candidates}
    assert "total_lift_count" not in field_paths


def test_extract_opendatahub_candidates_skips_non_numeric_total_slope_km() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    payload = {
        "TotalSlopeKm": "not-a-number",
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

    field_paths = {candidate.field_path for candidate in candidates}
    assert "total_piste_km" not in field_paths


def test_extract_opendatahub_candidates_requires_all_difficulty_components() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    payload = {
        "SlopeKmBlue": "74",
        "SlopeKmRed": "47",
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

    field_paths = {candidate.field_path for candidate in candidates}
    assert "piste_km_by_difficulty" not in field_paths


def test_extract_opendatahub_candidates_skips_non_numeric_difficulty_component() -> (
    None
):
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    payload = {
        "SlopeKmBlue": "74",
        "SlopeKmRed": "not-a-number",
        "SlopeKmBlack": "9",
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

    field_paths = {candidate.field_path for candidate in candidates}
    assert "piste_km_by_difficulty" not in field_paths


def test_extract_opendatahub_candidates_rejects_closed_data_payload() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    payload = {
        "LicenseInfo": {"ClosedData": True, "License": "restricted"},
    }
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)

    candidates = extract_opendatahub_candidates(
        "alta-badia",
        config,
        payload,
        fetched_at,
        source_url="https://tourism.api.opendatahub.com/v1/SkiArea/SKI123?language=en",
    )

    assert len(candidates) == 1
    assert candidates[0].field_path == "regional_data_ids.opendatahub_ski_area_id"
    assert candidates[0].proposed_value == "SKI123"
    assert candidates[0].validation_status == "rejected"
    assert candidates[0].confidence == 0.0
    assert candidates[0].validation_notes == ["OpenDataHub payload is not open data"]


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
        (
            candidate.target.entity_type,
            candidate.target.entity_id,
            candidate.field_path,
        ): candidate.proposed_value
        for candidate in candidates
    }
    assert (
        values[("destination", "test-resort", "ski_area_official_url")]
        == "https://www.example-resort.com"
    )
    assert (
        values[("destination", "test-resort", "regional_data_ids.osm_relation_id")]
        == "123456"
    )
    assert values[("destination", "test-resort", "latitude")] == 46.55
    assert values[("destination", "test-resort", "longitude")] == 11.75
    assert values[("ski_area", "test-ski-area", "latitude")] == 46.55
    assert values[("ski_area", "test-ski-area", "longitude")] == 11.75
    assert all(candidate.extraction_method == "wikidata" for candidate in candidates)
    assert all(candidate.source.source_type == "wikidata" for candidate in candidates)


def test_extract_wikidata_candidates_prefers_preferred_rank_claims() -> None:
    payload = {
        "entities": {
            "Q123": {
                "claims": {
                    "P856": [
                        {
                            "rank": "deprecated",
                            "mainsnak": {
                                "datavalue": {
                                    "value": "https://deprecated.example-resort.com",
                                    "type": "string",
                                }
                            },
                        },
                        {
                            "rank": "normal",
                            "mainsnak": {
                                "datavalue": {
                                    "value": "https://normal.example-resort.com",
                                    "type": "string",
                                }
                            },
                        },
                        {
                            "rank": "preferred",
                            "mainsnak": {
                                "datavalue": {
                                    "value": "https://preferred.example-resort.com",
                                    "type": "string",
                                }
                            },
                        },
                    ]
                }
            }
        }
    }

    candidates = extract_wikidata_candidates(
        resort_id="test-resort",
        wikidata_id="Q123",
        payload=payload,
        fetched_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        source_url="https://www.wikidata.org/wiki/Special:EntityData/Q123.json",
        resort_payload={"resort_id": "test-resort", "ski_areas": []},
    )

    values = {
        candidate.field_path: candidate.proposed_value for candidate in candidates
    }
    assert values["ski_area_official_url"] == "https://preferred.example-resort.com"


def test_extract_wikidata_candidates_falls_back_to_normal_valid_claim() -> None:
    payload = {
        "entities": {
            "Q123": {
                "claims": {
                    "P856": [
                        {
                            "rank": "deprecated",
                            "mainsnak": {
                                "datavalue": {
                                    "value": "https://deprecated.example-resort.com",
                                    "type": "string",
                                }
                            },
                        },
                        {
                            "rank": "preferred",
                            "mainsnak": {},
                        },
                        {
                            "rank": "preferred",
                            "mainsnak": {
                                "datavalue": {
                                    "value": " ",
                                    "type": "string",
                                }
                            },
                        },
                        {
                            "rank": "normal",
                            "mainsnak": {
                                "datavalue": {
                                    "value": "https://normal.example-resort.com",
                                    "type": "string",
                                }
                            },
                        },
                    ]
                }
            }
        }
    }

    candidates = extract_wikidata_candidates(
        resort_id="test-resort",
        wikidata_id="Q123",
        payload=payload,
        fetched_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        source_url="https://www.wikidata.org/wiki/Special:EntityData/Q123.json",
        resort_payload={"resort_id": "test-resort", "ski_areas": []},
    )

    values = {
        candidate.field_path: candidate.proposed_value for candidate in candidates
    }
    assert values["ski_area_official_url"] == "https://normal.example-resort.com"


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


class ConfigurableFakeLLMClient(LLMClient):
    def __init__(self, *, model: str = "fake-model", response: str) -> None:
        self._model = model
        self.response = response
        self.call_count = 0

    @property
    def model(self) -> str:
        return self._model

    def complete(self, **kwargs) -> str:
        self.call_count += 1
        return self.response


def _fetched_llm_page() -> FetchedPage:
    return FetchedPage(
        url="https://example.com/prices",
        final_url="https://example.com/prices",
        status_code=200,
        fetched_at=datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
        text="Adult 6 days EUR 390",
        content_hash="abc123",
        truncated=False,
    )


def _llm_response(field_path: str, value: object) -> str:
    return json.dumps(
        {
            "facts": [
                {
                    "field_path": field_path,
                    "value": value,
                    "evidence": "Official page evidence",
                    "confidence": 0.82,
                }
            ],
            "lift_pass_prices": [],
        }
    )


def test_extract_official_page_candidates_uses_schema_output(tmp_path) -> None:
    page = _fetched_llm_page()

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
    price_candidate = next(
        candidate
        for candidate in candidates
        if candidate.field_path == "lift_pass_prices"
    )
    assert price_candidate.proposed_value["duration_days"] == 6


def test_extract_official_page_candidates_cache_key_includes_role_and_model(
    tmp_path,
) -> None:
    page = _fetched_llm_page()
    ski_pass_client = ConfigurableFakeLLMClient(
        model="fake-model-a",
        response=_llm_response("season_dates_url", "https://example.com/season"),
    )
    rental_client = ConfigurableFakeLLMClient(
        model="fake-model-a",
        response=_llm_response("rental_url", "https://example.com/rental"),
    )
    second_model_client = ConfigurableFakeLLMClient(
        model="fake-model-b",
        response=_llm_response("trail_map_url", "https://example.com/map"),
    )

    ski_pass_candidates, ski_pass_errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=ski_pass_client,
        cache_dir=tmp_path,
    )
    rental_candidates, rental_errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="rental",
        llm_client=rental_client,
        cache_dir=tmp_path,
    )
    second_model_candidates, second_model_errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=second_model_client,
        cache_dir=tmp_path,
    )

    assert ski_pass_errors == []
    assert rental_errors == []
    assert second_model_errors == []
    assert ski_pass_client.call_count == 1
    assert rental_client.call_count == 1
    assert second_model_client.call_count == 1
    assert ski_pass_candidates[0].field_path == "season_dates_url"
    assert rental_candidates[0].field_path == "rental_url"
    assert second_model_candidates[0].field_path == "trail_map_url"
    assert len(list(tmp_path.glob("*.json"))) == 3


def test_extract_official_page_candidates_rejects_corrupted_cache_entry(
    tmp_path,
) -> None:
    page = _fetched_llm_page()
    client = ConfigurableFakeLLMClient(
        response=_llm_response("season_dates_url", "https://example.com/season")
    )

    candidates, errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=client,
        cache_dir=tmp_path,
    )
    assert errors == []
    assert candidates
    cache_file = next(tmp_path.glob("*.json"))
    cache_file.write_text("{not-json", encoding="utf-8")

    cached_candidates, cached_errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert cached_candidates == []
    assert len(cached_errors) == 1
    assert cached_errors[0].startswith(
        "https://example.com/prices: invalid LLM cache entry:"
    )
    assert client.call_count == 1


def test_extract_official_page_candidates_rejects_non_utf8_cache_entry(
    tmp_path,
) -> None:
    page = _fetched_llm_page()
    client = ConfigurableFakeLLMClient(
        response=_llm_response("season_dates_url", "https://example.com/season")
    )

    candidates, errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=client,
        cache_dir=tmp_path,
    )
    assert errors == []
    assert candidates
    cache_file = next(tmp_path.glob("*.json"))
    cache_file.write_bytes(b"\xff\xfe\xfa")

    cached_candidates, cached_errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert cached_candidates == []
    assert len(cached_errors) == 1
    assert cached_errors[0].startswith(
        "https://example.com/prices: invalid LLM cache entry:"
    )
    assert client.call_count == 1


def test_extract_official_page_candidates_does_not_cache_invalid_llm_output(
    tmp_path,
) -> None:
    page = _fetched_llm_page()
    client = ConfigurableFakeLLMClient(response="not-json")

    candidates, errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert candidates == []
    assert len(errors) == 1
    assert errors[0].startswith(
        "https://example.com/prices: invalid LLM extraction output:"
    )
    assert list(tmp_path.glob("*.json")) == []


def test_extract_official_page_candidates_rejects_lift_count_string_value(
    tmp_path,
) -> None:
    page = _fetched_llm_page()
    client = ConfigurableFakeLLMClient(
        response=_llm_response("total_lift_count", "53 lifts")
    )

    candidates, errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_area",
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert candidates == []
    assert len(errors) == 1
    assert errors[0].startswith(
        "https://example.com/prices: invalid LLM extraction output "
        "for total_lift_count:"
    )
    assert list(tmp_path.glob("*.json")) == []


def test_extract_official_page_candidates_rejects_malformed_difficulty_value(
    tmp_path,
) -> None:
    page = _fetched_llm_page()
    client = ConfigurableFakeLLMClient(
        response=_llm_response(
            "piste_km_by_difficulty",
            {"beginner": 74, "intermediate": 47, "expert": 9},
        )
    )

    candidates, errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_area",
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert candidates == []
    assert len(errors) == 1
    assert errors[0].startswith(
        "https://example.com/prices: invalid LLM extraction output "
        "for piste_km_by_difficulty:"
    )
    assert list(tmp_path.glob("*.json")) == []


def test_extract_official_page_candidates_normalizes_valid_lift_count(
    tmp_path,
) -> None:
    page = _fetched_llm_page()
    client = ConfigurableFakeLLMClient(response=_llm_response("total_lift_count", 53.0))

    candidates, errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_area",
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert errors == []
    assert len(candidates) == 1
    assert candidates[0].proposed_value == 53
    assert isinstance(candidates[0].proposed_value, int)
    assert len(list(tmp_path.glob("*.json"))) == 1


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
    assert "Target: `destination:test-resort`" in evidence
    assert "total_piste_km" in evidence
    assert "130 km of pistes" in evidence


def test_write_run_outputs_sanitizes_markdown_free_text(tmp_path) -> None:
    source = SourceReference(
        source_type="official",
        source_url="https://example.com/prices\n### fake source <b>|`",
    )
    generated_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    proposal = Proposal(
        resort_id="test-resort\n## fake resort",
        field_path="total_piste_km",
        current_value=None,
        proposed_value=130.0,
        status="new",
        source=source,
        extraction_method="official_page_llm",
        confidence=0.8,
        evidence="130 km of pistes\n### fake evidence <script>|`",
        validation_notes=["review\n## fake note <em>|`"],
    )
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=["test-resort\n## fake selected"],
        proposals=[proposal],
        candidates=[],
        fetch_log=[],
    )

    write_run_outputs(tmp_path, output)

    evidence = (tmp_path / "evidence.md").read_text()
    assert "\n## fake" not in evidence
    assert "\n### fake" not in evidence
    assert "<script>" not in evidence
    assert "<b>" not in evidence
    assert "<em>" not in evidence
    assert "130 km of pistes ### fake evidence &lt;script&gt;\\|\\`" in evidence


def test_write_run_outputs_distinguishes_repeated_field_proposals(tmp_path) -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    generated_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    proposals = [
        Proposal(
            resort_id="test-resort",
            field_path="lift_pass_prices",
            current_value=None,
            proposed_value={
                "duration_days": 1,
                "audience": "adult",
                "amount": 75,
                "currency": "EUR",
            },
            status="new",
            source=source,
            extraction_method="official_page_llm",
            confidence=0.8,
        ),
        Proposal(
            resort_id="test-resort",
            field_path="lift_pass_prices",
            current_value=None,
            proposed_value={
                "duration_days": 6,
                "audience": "adult",
                "amount": 390,
                "currency": "EUR",
            },
            status="new",
            source=source,
            extraction_method="official_page_llm",
            confidence=0.9,
        ),
    ]
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=["test-resort"],
        proposals=proposals,
        candidates=[],
        fetch_log=[],
    )

    write_run_outputs(tmp_path, output)

    evidence = (tmp_path / "evidence.md").read_text()
    assert "### `lift_pass_prices` proposal 1" in evidence
    assert "### `lift_pass_prices` proposal 2" in evidence
    assert evidence.count("### `lift_pass_prices` proposal ") == 2


def test_write_run_outputs_removes_stale_source_snapshots(tmp_path) -> None:
    snapshots_dir = tmp_path / "source-snapshots"
    snapshots_dir.mkdir()
    stale_file = snapshots_dir / "stale.txt"
    stale_file.write_text("old snapshot")
    output = AcquisitionRunOutput(
        generated_at=datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc),
        selected_resorts=[],
        proposals=[],
        candidates=[],
        fetch_log=[],
    )

    write_run_outputs(tmp_path, output)

    assert snapshots_dir.is_dir()
    assert not stale_file.exists()
    assert list(snapshots_dir.iterdir()) == []


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


def test_catalog_acquisition_cli_rejects_negative_max_pages(tmp_path) -> None:
    registry_path = tmp_path / "sources.json"
    catalog_path = tmp_path / "resorts.json"
    output_dir = tmp_path / "out"
    registry_path.write_text(json.dumps({"version": 1, "resorts": {}}))
    catalog_path.write_text(json.dumps([]))

    with pytest.raises(ValueError, match="max-pages-per-resort must be non-negative"):
        acquisition_main(
            [
                "--registry-path",
                str(registry_path),
                "--catalog-path",
                str(catalog_path),
                "--output-dir",
                str(output_dir),
                "--max-pages-per-resort",
                "-1",
                "--skip-llm",
                "--skip-opendatahub",
            ]
        )


def test_catalog_acquisition_cli_returns_fetch_failure_code_after_writing_artifacts(
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
                        "official_urls": {"ski_pass": "https://example.com/prices"},
                        "regional_data_ids": {
                            "opendatahub_ski_area_id": "SKI123",
                            "osm_relation_id": "12345",
                        },
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

    def fail_fetch_json(
        resort_id: str,
        url: str,
        started_at: datetime,
    ) -> tuple[None, FetchLogEntry]:
        return None, FetchLogEntry(
            resort_id=resort_id,
            url=url,
            fetched_at=started_at,
            status="failed",
            extraction_method="opendatahub",
            error="simulated fetch failure",
        )

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._fetch_json",
        fail_fetch_json,
    )
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._extract_opendatahub_discovery",
        lambda *args: ([], None),
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
        ]
    )

    assert exit_code == 1
    proposals = json.loads((output_dir / "proposals.json").read_text())
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    assert proposals["proposals"]
    assert fetch_log[0]["status"] == "failed"


class _JsonResponse:
    def __init__(self, payload: object, *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


def _use_routing_json_fetch(
    monkeypatch,
    responses_by_url: dict[str, object],
) -> None:
    class RoutingClient:
        def __init__(self, *, timeout: float, follow_redirects: bool) -> None:
            self.timeout = timeout
            self.follow_redirects = follow_redirects

        def __enter__(self) -> "RoutingClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def get(self, url: str, *, headers: dict[str, str]) -> _JsonResponse:
            if url not in responses_by_url:
                raise AssertionError(f"Unexpected URL: {url}")
            return _JsonResponse(responses_by_url[url])

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.httpx.Client",
        RoutingClient,
    )


def test_catalog_acquisition_cli_discovers_opendatahub_id_without_registry_entry(
    tmp_path,
    monkeypatch,
) -> None:
    registry_path = tmp_path / "sources.json"
    catalog_path = tmp_path / "resorts.json"
    output_dir = tmp_path / "out"
    registry_path.write_text(json.dumps({"version": 1, "resorts": {}}))
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "alta-badia",
                    "name": "Alta Badia",
                    "country": "Italy",
                }
            ]
        )
    )
    detail_url = "https://tourism.api.opendatahub.com/v1/SkiArea/SKI123?language=en"
    _use_routing_json_fetch(
        monkeypatch,
        {
            OPENDATAHUB_SKI_AREA_INDEX_URL: [_opendatahub_index_record()],
            detail_url: {
                "Id": "SKI123",
                "TotalSlopeKm": "130",
                "LiftCount": "53",
                "LicenseInfo": {"ClosedData": False, "License": "CC0"},
            },
        },
    )

    exit_code = acquisition_main(
        [
            "--resort",
            "alta-badia",
            "--registry-path",
            str(registry_path),
            "--catalog-path",
            str(catalog_path),
            "--output-dir",
            str(output_dir),
            "--skip-llm",
        ]
    )

    assert exit_code == 0
    proposals = json.loads((output_dir / "proposals.json").read_text())
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    discovery_proposals = [
        proposal
        for proposal in proposals["proposals"]
        if proposal["extraction_method"] == "opendatahub_discovery"
    ]
    assert discovery_proposals
    assert discovery_proposals[0]["field_path"] == (
        "regional_data_ids.opendatahub_ski_area_id"
    )
    assert discovery_proposals[0]["evidence"]
    assert {proposal["field_path"] for proposal in proposals["proposals"]} >= {
        "regional_data_ids.opendatahub_ski_area_id",
        "total_piste_km",
    }
    assert any(
        entry["resort_id"] == "opendatahub-discovery" and entry["status"] == "success"
        for entry in fetch_log
    )


def test_catalog_acquisition_cli_skip_opendatahub_disables_discovery(
    tmp_path,
    monkeypatch,
) -> None:
    registry_path = tmp_path / "sources.json"
    catalog_path = tmp_path / "resorts.json"
    output_dir = tmp_path / "out"
    registry_path.write_text(json.dumps({"version": 1, "resorts": {}}))
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "alta-badia",
                    "name": "Alta Badia",
                    "country": "Italy",
                }
            ]
        )
    )

    class FailingClient:
        def __init__(self, *, timeout: float, follow_redirects: bool) -> None:
            self.timeout = timeout
            self.follow_redirects = follow_redirects

        def __enter__(self) -> "FailingClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def get(self, url: str, *, headers: dict[str, str]) -> _JsonResponse:
            raise AssertionError("OpenDataHub should not be fetched")

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.httpx.Client",
        FailingClient,
    )

    exit_code = acquisition_main(
        [
            "--resort",
            "alta-badia",
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

    assert exit_code == 2
    proposals = json.loads((output_dir / "proposals.json").read_text())
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    assert proposals["proposals"] == []
    assert not any(entry["resort_id"] == "opendatahub-discovery" for entry in fetch_log)


def test_catalog_acquisition_cli_records_discovery_fetch_failure(
    tmp_path,
    monkeypatch,
) -> None:
    registry_path = tmp_path / "sources.json"
    catalog_path = tmp_path / "resorts.json"
    output_dir = tmp_path / "out"
    registry_path.write_text(json.dumps({"version": 1, "resorts": {}}))
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "alta-badia",
                    "name": "Alta Badia",
                    "country": "Italy",
                }
            ]
        )
    )

    class FailingClient:
        def __init__(self, *, timeout: float, follow_redirects: bool) -> None:
            self.timeout = timeout
            self.follow_redirects = follow_redirects

        def __enter__(self) -> "FailingClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def get(self, url: str, *, headers: dict[str, str]) -> _JsonResponse:
            raise httpx.ConnectError(
                "temporary DNS failure",
                request=httpx.Request("GET", url),
            )

    monkeypatch.setattr(
        "app.data.resort_acquisition.fetching._TRANSPORT_RETRY_DELAYS_SECONDS",
        (),
    )
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.httpx.Client",
        FailingClient,
    )

    exit_code = acquisition_main(
        [
            "--resort",
            "alta-badia",
            "--registry-path",
            str(registry_path),
            "--catalog-path",
            str(catalog_path),
            "--output-dir",
            str(output_dir),
            "--skip-llm",
        ]
    )

    assert exit_code == 1
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    assert fetch_log[0]["resort_id"] == "opendatahub-discovery"
    assert fetch_log[0]["status"] == "failed"
    assert "temporary DNS failure" in fetch_log[0]["error"]


def test_fetch_json_retries_transient_transport_error(monkeypatch) -> None:
    calls: list[str] = []

    class JsonResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"Id": "SKI123"}

    class FlakyClient:
        def __init__(self, *, timeout: float, follow_redirects: bool) -> None:
            self.timeout = timeout
            self.follow_redirects = follow_redirects

        def __enter__(self) -> "FlakyClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def get(self, url: str, *, headers: dict[str, str]) -> JsonResponse:
            calls.append(url)
            if len(calls) == 1:
                raise httpx.ConnectError(
                    "temporary DNS failure",
                    request=httpx.Request("GET", url),
                )
            return JsonResponse()

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.httpx.Client",
        FlakyClient,
    )

    payload, fetch_log = _fetch_json(
        "alta-badia",
        "https://example.com/opendatahub",
        datetime.fromisoformat("2026-05-04T10:00:00+00:00"),
    )

    assert payload == {"Id": "SKI123"}
    assert fetch_log.status == "success"
    assert calls == [
        "https://example.com/opendatahub",
        "https://example.com/opendatahub",
    ]


def test_catalog_acquisition_workflow_is_manual_read_only_and_artifact_only() -> None:
    workflow = Path(".github/workflows/catalog-acquisition.yml").read_text()

    try:
        import yaml
    except ImportError:
        parsed_workflow = None
    else:
        parsed_workflow = yaml.safe_load(workflow)
        if isinstance(parsed_workflow, dict) and True in parsed_workflow:
            parsed_workflow["on"] = parsed_workflow[True]

    if parsed_workflow is not None:
        triggers = parsed_workflow["on"]
        assert "workflow_dispatch" in triggers

        permissions = parsed_workflow["permissions"]
        assert permissions["contents"] == "read"
        assert "write" not in permissions.values()

        steps = parsed_workflow["jobs"]["catalog-acquisition"]["steps"]
        assert any("upload-artifact" in step.get("uses", "") for step in steps)

        build_args_step = next(
            step for step in steps if step["name"] == "Build acquisition arguments"
        )
        assert "${{ inputs." not in build_args_step["run"]
        assert build_args_step["env"] == {
            "INPUT_RESORTS": "${{ inputs.resorts }}",
            "INPUT_COUNTRY": "${{ inputs.country }}",
            "INPUT_SKIP_LLM": "${{ inputs.skip_llm }}",
            "INPUT_MAX_PAGES_PER_RESORT": "${{ inputs.max_pages_per_resort }}",
        }
    else:
        assert "workflow_dispatch:" in workflow
        assert "contents: read" in workflow
        assert "upload-artifact" in workflow

    dangerous_patterns = [
        "git push",
        "gh pr create",
        "gh repo",
        "create-pull-request",
        "pull-request",
        "contents: write",
    ]
    for pattern in dangerous_patterns:
        assert pattern not in workflow
