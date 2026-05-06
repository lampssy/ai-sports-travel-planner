import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.ai.llm_client import LLMClient, LLMClientError
from app.data.resort_acquisition.bergfex import (
    extract_bergfex_catalog_candidates,
    filter_bergfex_fallback_candidates,
)
from app.data.resort_acquisition.dem import (
    CoordinatePoint,
    extract_dem_sanity_candidates,
    opentopodata_url,
)
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
    FetchedHtmlDocument,
    FetchedPage,
    fetch_url,
    html_to_text,
    stable_content_hash,
)
from app.data.resort_acquisition.generate_catalog_patch import apply_catalog_patch
from app.data.resort_acquisition.link_classify import (
    MAX_LLM_LINK_CLASSIFICATION_CANDIDATES,
    classify_official_links_with_llm,
)
from app.data.resort_acquisition.llm_budget import (
    LLMRateLimitConfig,
    RateLimitedLLMClient,
)
from app.data.resort_acquisition.llm_extract import extract_official_page_candidates
from app.data.resort_acquisition.models import (
    AcquisitionRunOutput,
    CandidateFact,
    ExtractionMethod,
    FetchLogEntry,
    LiftPassPriceCandidate,
    Proposal,
    ProposalTarget,
    RegionalDataIds,
    ResortSourceConfig,
    SourceReference,
    SourceRegistry,
)
from app.data.resort_acquisition.official_links import (
    OfficialLinkCandidate,
    extract_link_candidates_from_html,
    official_link_candidate_from_url,
    parse_sitemap_urls,
)
from app.data.resort_acquisition.osm import (
    extract_osm_discovery_candidates,
    extract_osm_relation_candidates,
    normalize_osm_relation_id,
    overpass_discovery_query,
    overpass_relation_query,
)
from app.data.resort_acquisition.proposals import (
    build_proposals,
    load_raw_catalog_by_resort,
)
from app.data.resort_acquisition.registry import load_source_registry
from app.data.resort_acquisition.reports import (
    render_evidence_markdown,
    write_run_outputs,
)
from app.data.resort_acquisition.run_catalog_acquisition import (
    _extract_official_page_candidates as runner_extract_official_page_candidates,
)
from app.data.resort_acquisition.run_catalog_acquisition import (
    _fetch_json,
    discover_official_links_for_resort,
)
from app.data.resort_acquisition.run_catalog_acquisition import (
    main as acquisition_main,
)
from app.data.resort_acquisition.source_context import (
    DiscoveredOfficialUrl,
    SourceRunContext,
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


def test_bergfex_source_type_and_extraction_method_are_valid() -> None:
    candidate = CandidateFact(
        resort_id="stubai-glacier",
        field_path="total_piste_km",
        proposed_value=65,
        source=SourceReference(
            source_type="bergfex",
            source_url="https://www.bergfex.com/stubaier-gletscher/",
        ),
        extraction_method="bergfex_public_page",
        fetched_at=datetime.fromisoformat("2026-05-06T10:00:00+00:00"),
        confidence=0.55,
        evidence="Bergfex public page Pistes 65 km",
    )

    assert candidate.source.source_type == "bergfex"
    assert candidate.extraction_method == "bergfex_public_page"


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


def test_build_proposals_does_not_conflict_matching_season_window_dates() -> None:
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
            field_path="season_windows",
            proposed_value={
                "season_label": "2025-2026",
                "start_date": "2025-11-22",
                "end_date": "2026-05-03",
                "status": "planned",
            },
            source=SourceReference(
                source_type="bergfex",
                source_url="https://www.bergfex.com/test-resort/",
            ),
            extraction_method="bergfex_public_page",
            fetched_at=fetched_at,
            confidence=0.55,
        ),
        CandidateFact(
            resort_id="test-resort",
            field_path="season_windows",
            proposed_value={
                "season_label": "Hiver",
                "start_date": "2025-11-22",
                "end_date": "2026-05-03",
                "status": "planned",
            },
            source=source,
            extraction_method="official_page_llm",
            fetched_at=fetched_at,
            confidence=1.0,
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


def test_dem_builds_batched_opentopodata_url() -> None:
    points = [
        CoordinatePoint(target_key="a", latitude=46.1, longitude=11.1),
        CoordinatePoint(target_key="b", latitude=46.2, longitude=11.2),
    ]

    url = opentopodata_url(dataset_stack="eudem25m,mapzen", points=points)

    assert (
        url
        == "https://api.opentopodata.org/v1/eudem25m,mapzen?locations=46.1,11.1%7C46.2,11.2"
    )


def test_extract_dem_candidates_warns_when_point_elevation_far_from_base() -> None:
    resort_payload = {
        "resort_id": "test-resort",
        "ski_areas": [
            {
                "ski_area_id": "test-ski-area",
                "latitude": 46.1,
                "longitude": 11.1,
                "base_elevation_m": 1500,
            }
        ],
    }
    payload = {"results": [{"elevation": 730.4}]}

    candidates = extract_dem_sanity_candidates(
        resort_id="test-resort",
        payload=payload,
        fetched_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        source_url="https://api.opentopodata.org/v1/eudem25m",
        resort_payload=resort_payload,
        dataset_stack="eudem25m",
    )

    assert len(candidates) == 1
    assert candidates[0].target == ProposalTarget(
        entity_type="ski_area", entity_id="test-ski-area"
    )
    assert candidates[0].field_path == "base_elevation_m"
    assert candidates[0].proposed_value == 1500
    assert candidates[0].validation_status == "warning"
    assert candidates[0].extraction_method == "dem"
    assert candidates[0].source.source_type == "dem"
    assert "DEM point elevation 730m" in candidates[0].validation_notes[0]
    assert "OpenTopoData point elevation=730m" in candidates[0].evidence


def _bergfex_document(html: str) -> FetchedHtmlDocument:
    return FetchedHtmlDocument(
        url="https://www.bergfex.com/stubaier-gletscher/",
        final_url="https://www.bergfex.com/stubaier-gletscher/",
        status_code=200,
        fetched_at=datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc),
        raw_html=html,
        visible_text=html_to_text(html),
        content_hash=stable_content_hash(html),
        truncated=False,
    )


def test_extract_bergfex_catalog_candidates_parses_static_fallback_facts() -> None:
    resort_payload = {
        "resort_id": "stubai-glacier",
        "name": "Stubai Glacier",
        "base_elevation_m": 1695,
        "summit_elevation_m": 3210,
        "season_start_month": 10,
        "season_end_month": 5,
        "ski_areas": [
            {
                "ski_area_id": "stubai-glacier-ski-area",
                "name": "Stubai Glacier",
                "base_elevation_m": 1695,
                "summit_elevation_m": 3210,
                "season_start_month": 10,
                "season_end_month": 5,
            }
        ],
    }
    page = _bergfex_document(
        """
        <html><body>
          <h1>Ski resort Stubaier Gletscher / Stubaital</h1>
          <a href="https://apps.apple.com/app/bergfex">App Store</a>
          <a href="https://www.stubaier-gletscher.com/">https://www.stubaier-gletscher.com/</a>
          <div>1.695 - 3.210 m</div>
          <div>
            Current information Today, 15:09 Open lifts 7 / 26
            Snow depth Mountain: 300 cm
          </div>
          <div>Operation: 08:30 - 16:30 Season: 03.10.2025 - 17.05.2026</div>
          <a href="/stubaier-gletscher/pisten/">Pistes 65 km</a>
        </body></html>
        """
    )

    candidates = extract_bergfex_catalog_candidates(
        resort_id="stubai-glacier",
        page=page,
        resort_payload=resort_payload,
    )

    values = {}
    for candidate in candidates:
        key = (
            candidate.target.entity_type,
            candidate.target.entity_id,
            candidate.field_path,
        )
        values[key] = candidate.proposed_value
    assert (
        values[("destination", "stubai-glacier", "ski_area_official_url")]
        == "https://www.stubaier-gletscher.com/"
    )
    assert values[("ski_area", "stubai-glacier-ski-area", "base_elevation_m")] == 1695
    assert values[("destination", "stubai-glacier", "base_elevation_m")] == 1695
    assert values[("ski_area", "stubai-glacier-ski-area", "summit_elevation_m")] == 3210
    assert values[("ski_area", "stubai-glacier-ski-area", "season_start_month")] == 10
    assert values[("ski_area", "stubai-glacier-ski-area", "season_end_month")] == 5
    assert values[("ski_area", "stubai-glacier-ski-area", "season_windows")] == {
        "season_label": "2025-2026",
        "start_date": "2025-10-03",
        "end_date": "2026-05-17",
        "status": "planned",
    }
    assert values[("destination", "stubai-glacier", "season_windows")] == {
        "season_label": "2025-2026",
        "start_date": "2025-10-03",
        "end_date": "2026-05-17",
        "status": "planned",
    }
    assert values[("ski_area", "stubai-glacier-ski-area", "total_piste_km")] == 65
    assert values[("ski_area", "stubai-glacier-ski-area", "total_lift_count")] == 26
    assert all(candidate.source.source_type == "bergfex" for candidate in candidates)
    assert all(
        candidate.extraction_method == "bergfex_public_page" for candidate in candidates
    )


def test_bergfex_parser_ignores_noisy_links_and_open_status() -> None:
    page = _bergfex_document(
        """
        <html><body>
          <a href="https://apps.apple.com/app/bergfex">App Store</a>
          <a href="https://www.skiresort.info/ski-resort/test/">Database profile</a>
          <div>
            Current information Today, 15:09 Open lifts 7 / 26
            Open pistes 34 km
          </div>
        </body></html>
        """
    )

    candidates = extract_bergfex_catalog_candidates(
        resort_id="stubai-glacier",
        page=page,
        resort_payload={"resort_id": "stubai-glacier"},
    )

    field_paths = {candidate.field_path for candidate in candidates}
    assert "ski_area_official_url" not in field_paths
    assert "open_lift_count" not in field_paths
    assert "open_piste_km" not in field_paths


def test_filter_bergfex_suppresses_when_prior_source_agrees() -> None:
    fetched_at = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    bergfex_candidate = CandidateFact(
        resort_id="stubai-glacier",
        field_path="total_piste_km",
        proposed_value=65,
        source=SourceReference(
            source_type="bergfex",
            source_url="https://www.bergfex.com/stubaier-gletscher/",
        ),
        extraction_method="bergfex_public_page",
        fetched_at=fetched_at,
        confidence=0.55,
    )
    prior_candidate = CandidateFact(
        resort_id="stubai-glacier",
        field_path="total_piste_km",
        proposed_value=65,
        source=SourceReference(
            source_type="opendatahub",
            source_url="https://tourism.api.opendatahub.com/v1/SkiArea/SKI123",
        ),
        extraction_method="opendatahub",
        fetched_at=fetched_at,
        confidence=0.95,
    )

    filtered = filter_bergfex_fallback_candidates(
        candidates=[bergfex_candidate],
        prior_candidates=[prior_candidate],
        resort_payload={"resort_id": "stubai-glacier", "total_piste_km": 65},
    )

    assert filtered == []


def test_filter_bergfex_fallback_keeps_source_gaps_and_conflicts() -> None:
    fetched_at = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    bergfex_candidate = CandidateFact(
        resort_id="stubai-glacier",
        field_path="total_piste_km",
        proposed_value=65,
        source=SourceReference(
            source_type="bergfex",
            source_url="https://www.bergfex.com/stubaier-gletscher/",
        ),
        extraction_method="bergfex_public_page",
        fetched_at=fetched_at,
        confidence=0.55,
    )
    conflicting_prior_candidates = [
        CandidateFact(
            resort_id="stubai-glacier",
            field_path="total_piste_km",
            proposed_value=value,
            source=SourceReference(
                source_type="opendatahub",
                source_url=f"https://example.com/{value}",
            ),
            extraction_method="opendatahub",
            fetched_at=fetched_at,
            confidence=0.95,
        )
        for value in (64, 66)
    ]

    assert filter_bergfex_fallback_candidates(
        candidates=[bergfex_candidate],
        prior_candidates=[],
        resort_payload={"resort_id": "stubai-glacier", "total_piste_km": 65},
    ) == [bergfex_candidate]
    assert filter_bergfex_fallback_candidates(
        candidates=[bergfex_candidate],
        prior_candidates=conflicting_prior_candidates,
        resort_payload={"resort_id": "stubai-glacier", "total_piste_km": 65},
    ) == [bergfex_candidate]


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
    assert (
        by_url["https://www.example.com/en/skipass-prices"].deterministic_scores[
            "ski_pass"
        ]
        > 0
    )
    assert by_url["https://tickets.example.com/buy"].is_external is True


def test_extract_official_links_avoids_event_and_directions_noise() -> None:
    html = """
    <html>
      <head><title>Stubai Winter</title></head>
      <body>
        <a href="/events/detail/stubaier-musikkarussell-2026-neustift/">
          Top Event Stubaier Musikkarussell 2026 Livemusik
        </a>
        <a href="http://maps.google.com/maps?daddr=Tourismusverband+Stubai">
          Route in Google Maps
        </a>
        <a href="/en/snow-report-open-lifts">Open lifts and slopes</a>
        <a href="/downloads/pistenplan.pdf">Pistenplan</a>
      </body>
    </html>
    """

    links = extract_link_candidates_from_html(
        html=html,
        source_url="https://www.stubai.at/",
        official_seed_url="https://www.stubai.at/",
    )

    by_url = {link.url: link for link in links}
    event = by_url[
        "https://www.stubai.at/events/detail/stubaier-musikkarussell-2026-neustift/"
    ]
    assert event.deterministic_scores["official_status"] == 0
    assert "http://maps.google.com/maps?daddr=Tourismusverband+Stubai" not in by_url
    assert (
        by_url["https://www.stubai.at/en/snow-report-open-lifts"].deterministic_scores[
            "official_status"
        ]
        > 0
    )
    assert (
        by_url["https://www.stubai.at/downloads/pistenplan.pdf"].deterministic_scores[
            "trail_map"
        ]
        > 0
    )


def test_extract_official_links_avoids_summer_opening_as_ski_season() -> None:
    html = """
    <html>
      <head><title>Mairie de Tignes</title></head>
      <body>
        <a href="/agenda/ouverture-des-activites-dete/">
          Ouverture des activités d'été
        </a>
        <a href="/hiver/ouverture-domaine-skiable/">Ouverture hiver ski</a>
      </body>
    </html>
    """

    links = extract_link_candidates_from_html(
        html=html,
        source_url="https://mairie-tignes.fr/",
        official_seed_url="https://mairie-tignes.fr/",
    )

    by_url = {link.url: link for link in links}
    summer_opening = by_url[
        "https://mairie-tignes.fr/agenda/ouverture-des-activites-dete/"
    ]
    assert summer_opening.deterministic_scores["season_dates"] == 0
    assert (
        by_url[
            "https://mairie-tignes.fr/hiver/ouverture-domaine-skiable/"
        ].deterministic_scores["season_dates"]
        > 0
    )

    sitemap_candidate = official_link_candidate_from_url(
        url="https://mairie-tignes.fr/agenda/ouverture-des-activites-dete/",
        source_page_url="https://mairie-tignes.fr/sitemap.xml",
        official_seed_url="https://mairie-tignes.fr/",
        source_page_title="sitemap.xml",
    )

    assert sitemap_candidate is not None
    assert sitemap_candidate.deterministic_scores["season_dates"] == 0


def test_parse_sitemap_urls_keeps_same_host_and_caps_results() -> None:
    xml = (
        "<urlset>"
        + "".join(
            f"<url><loc>https://www.example.com/page-{index}</loc></url>"
            for index in range(45)
        )
        + "</urlset>"
    )

    urls = parse_sitemap_urls(
        xml,
        official_seed_url="https://www.example.com",
        max_urls=40,
    )

    assert len(urls) == 40
    assert urls[0] == "https://www.example.com/page-0"


def test_parse_sitemap_urls_filters_nested_and_external_hosts() -> None:
    xml = """
    <urlset>
      <url><loc>https://www.example.com/same-host</loc></url>
      <url><loc>https://tickets.example.com/direct-subdomain</loc></url>
      <url><loc>https://a.b.example.com/nested-subdomain</loc></url>
      <url><loc>https://external.test/outside</loc></url>
    </urlset>
    """

    urls = parse_sitemap_urls(xml, official_seed_url="https://www.example.com")

    assert urls == [
        "https://www.example.com/same-host",
        "https://tickets.example.com/direct-subdomain",
    ]


def test_extract_official_links_marks_direct_subdomain_external() -> None:
    html = """
    <html>
      <body>
        <a href="https://www.example.com/weather">Weather</a>
        <a href="https://tickets.example.com/buy">Buy tickets</a>
      </body>
    </html>
    """

    links = extract_link_candidates_from_html(
        html=html,
        source_url="https://www.example.com/en",
        official_seed_url="https://www.example.com",
    )

    by_url = {link.url: link for link in links}
    assert by_url["https://tickets.example.com/buy"].is_external is True


def test_extract_official_links_filters_external_noise_without_role_scores() -> None:
    html = """
    <html>
      <body>
        <a href="https://tickets.example.com/buy">Buy tickets</a>
        <a href="https://facebook.com/example">Follow us</a>
        <a href="https://ads.example.net/banner">Partner banner</a>
      </body>
    </html>
    """

    links = extract_link_candidates_from_html(
        html=html,
        source_url="https://www.example.com/en",
        official_seed_url="https://www.example.com",
    )

    by_url = {link.url: link for link in links}
    assert by_url["https://tickets.example.com/buy"].is_external is True
    assert "https://facebook.com/example" not in by_url
    assert "https://ads.example.net/banner" not in by_url


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


def test_extract_opendatahub_targets_known_ski_area_terrain() -> None:
    config = ResortSourceConfig(
        regional_data_ids=RegionalDataIds(opendatahub_ski_area_id="SKI123")
    )
    resort_payload = {
        "resort_id": "alta-badia",
        "name": "Alta Badia",
        "ski_areas": [
            {
                "ski_area_id": "alta-badia-ski-area",
                "name": "Alta Badia",
            }
        ],
    }
    payload = {
        "LiftCount": "53",
        "TotalSlopeKm": "130",
        "SlopeKmBlue": "74",
        "SlopeKmRed": "47",
        "SlopeKmBlack": "9",
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

    terrain_targets = {
        candidate.field_path: candidate.target
        for candidate in candidates
        if candidate.field_path
        in {"total_piste_km", "total_lift_count", "piste_km_by_difficulty"}
    }
    assert terrain_targets == {
        "total_piste_km": ProposalTarget(
            entity_type="ski_area", entity_id="alta-badia-ski-area"
        ),
        "total_lift_count": ProposalTarget(
            entity_type="ski_area", entity_id="alta-badia-ski-area"
        ),
        "piste_km_by_difficulty": ProposalTarget(
            entity_type="ski_area", entity_id="alta-badia-ski-area"
        ),
    }


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
                    "P31": [
                        {
                            "rank": "normal",
                            "mainsnak": {
                                "datavalue": {
                                    "value": {
                                        "entity-type": "item",
                                        "numeric-id": 130003,
                                        "id": "Q130003",
                                    },
                                    "type": "wikibase-entityid",
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


def _osm_relation_payload() -> dict[str, object]:
    return {
        "elements": [
            {
                "type": "relation",
                "id": 123456,
                "center": {"lat": 46.551, "lon": 11.755},
                "tags": {"name": "Test Resort"},
            }
        ]
    }


def test_extract_osm_candidates_maps_relation_center_to_coordinates() -> None:
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

    candidates = extract_osm_relation_candidates(
        resort_id="test-resort",
        osm_relation_id="123456",
        payload=_osm_relation_payload(),
        fetched_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        source_url="https://overpass-api.de/api/interpreter",
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
    assert values[("destination", "test-resort", "latitude")] == 46.551
    assert values[("destination", "test-resort", "longitude")] == 11.755
    assert values[("ski_area", "test-ski-area", "latitude")] == 46.551
    assert values[("ski_area", "test-ski-area", "longitude")] == 11.755
    assert all(candidate.extraction_method == "osm" for candidate in candidates)
    assert all(candidate.source.source_type == "osm" for candidate in candidates)
    assert all(
        "OpenStreetMap relation 123456 center" in candidate.evidence
        for candidate in candidates
    )


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


def test_overpass_relation_query_rejects_malformed_relation_id() -> None:
    assert normalize_osm_relation_id("123456") == "123456"
    assert normalize_osm_relation_id("00123456") == "123456"
    assert normalize_osm_relation_id("123);node(1);out;") is None

    with pytest.raises(ValueError, match="positive integer"):
        overpass_relation_query("123);node(1);out;")


@pytest.mark.parametrize("payload", [None, []])
def test_extract_osm_relation_candidates_ignores_malformed_payload(
    payload: object,
) -> None:
    candidates = extract_osm_relation_candidates(
        resort_id="test-resort",
        osm_relation_id="123456",
        payload=payload,  # type: ignore[arg-type]
        fetched_at=datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc),
        source_url="https://overpass-api.de/api/interpreter",
        resort_payload={"resort_id": "test-resort", "ski_areas": []},
    )

    assert candidates == []


def _osm_discovery_payload() -> dict[str, object]:
    return {
        "elements": [
            {
                "type": "relation",
                "id": 777,
                "center": {"lat": 46.501, "lon": 11.001},
                "tags": {
                    "name": "Test Resort",
                    "landuse": "winter_sports",
                    "site": "piste",
                    "website": "https://www.test-resort.example",
                    "website:map": "https://www.test-resort.example/map",
                },
            },
            {
                "type": "way",
                "id": 778,
                "center": {"lat": 46.503, "lon": 11.003},
                "tags": {
                    "name": "Test Resort",
                    "landuse": "winter_sports",
                    "website": "https://www.test-resort.example",
                },
            },
        ]
    }


def test_overpass_discovery_query_uses_bounded_ski_website_search() -> None:
    query = overpass_discovery_query(latitude=46.5, longitude=11.0)

    assert "around:12000,46.5,11.0" in query
    assert '["landuse"="winter_sports"]' in query
    assert '["website"]' in query
    assert '["contact:website"]' in query
    assert '["website:map"]' in query


def test_extract_osm_discovery_candidates_maps_website_map_and_relation_id() -> None:
    candidates = extract_osm_discovery_candidates(
        resort_id="test-resort",
        payload=_osm_discovery_payload(),
        fetched_at=datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc),
        source_url="https://overpass-api.de/api/interpreter?data=query",
        resort_payload={
            "resort_id": "test-resort",
            "name": "Test Resort",
            "latitude": 46.5,
            "longitude": 11.0,
        },
    )

    values = {candidate.field_path: candidate for candidate in candidates}
    assert values["ski_area_official_url"].proposed_value == (
        "https://www.test-resort.example"
    )
    assert values["trail_map_url"].proposed_value == (
        "https://www.test-resort.example/map"
    )
    assert values["regional_data_ids.osm_relation_id"].proposed_value == "777"
    assert all(
        candidate.extraction_method == "osm_discovery" for candidate in candidates
    )
    assert all(candidate.source.source_type == "osm" for candidate in candidates)
    assert values["ski_area_official_url"].confidence >= 0.8
    assert "OpenStreetMap relation/777" in values["ski_area_official_url"].evidence


def test_extract_osm_discovery_candidates_suppresses_nearby_unmatched_objects() -> None:
    candidates = extract_osm_discovery_candidates(
        resort_id="stubai-glacier",
        payload={
            "elements": [
                {
                    "type": "relation",
                    "id": 7768194,
                    "center": {"lat": 47.0685731, "lon": 11.2647437},
                    "tags": {
                        "name": "Stubai",
                        "landuse": "winter_sports",
                        "wikidata": "Q701945",
                        "website": "https://www.stubai.at/",
                    },
                },
                {
                    "type": "way",
                    "id": 539206485,
                    "center": {"lat": 47.132, "lon": 11.318},
                    "tags": {
                        "name": "Schlick 2000",
                        "landuse": "winter_sports",
                        "website": "https://www.stubai.at/skigebiete/schlick2000/skigebiet/",
                    },
                },
                {
                    "type": "relation",
                    "id": 1305661,
                    "center": {"lat": 47.18, "lon": 11.37},
                    "tags": {
                        "name": "Mutterer Alm - Familienrodelbahn",
                        "route": "piste",
                        "piste:type": "sled",
                        "website": "https://www.innsbruck.info/sport/winter/rodeln/rodelbahnen/touren/muttereralm-fuer-familien.html",
                    },
                },
            ],
        },
        fetched_at=datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc),
        source_url="https://overpass-api.de/api/interpreter?data=query",
        resort_payload={
            "resort_id": "stubai-glacier",
            "name": "Stubai Glacier",
            "latitude": 47.1407,
            "longitude": 11.3093,
        },
    )

    values = {
        (candidate.field_path, candidate.proposed_value) for candidate in candidates
    }
    assert ("ski_area_official_url", "https://www.stubai.at/") in values
    assert ("regional_data_ids.osm_relation_id", "7768194") in values
    assert not any(
        value == "https://www.stubai.at/skigebiete/schlick2000/skigebiet/"
        for _, value in values
    )
    assert not any(value == "1305661" for _, value in values)


def test_extract_osm_discovery_candidates_filters_aggregator_domains() -> None:
    candidates = extract_osm_discovery_candidates(
        resort_id="test-resort",
        payload={
            "elements": [
                {
                    "type": "relation",
                    "id": 777,
                    "center": {"lat": 46.501, "lon": 11.001},
                    "tags": {
                        "name": "Test Resort",
                        "landuse": "winter_sports",
                        "website": "https://www.skiresort.de/skigebiet/test-resort/",
                    },
                }
            ]
        },
        fetched_at=datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc),
        source_url="https://overpass-api.de/api/interpreter?data=query",
        resort_payload={
            "resort_id": "test-resort",
            "name": "Test Resort",
            "latitude": 46.5,
            "longitude": 11.0,
        },
    )

    assert candidates == []


def test_extract_osm_discovery_candidates_skips_missing_catalog_coordinates() -> None:
    candidates = extract_osm_discovery_candidates(
        resort_id="test-resort",
        payload=_osm_discovery_payload(),
        fetched_at=datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc),
        source_url="https://overpass-api.de/api/interpreter?data=query",
        resort_payload={"resort_id": "test-resort", "name": "Test Resort"},
    )

    assert candidates == []


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


class RetryThenSuccessLLMClient(LLMClient):
    def __init__(self, *, failures_before_success: int, response: str) -> None:
        self.failures_before_success = failures_before_success
        self.response = response
        self.call_count = 0

    @property
    def model(self) -> str:
        return "retry-model"

    def complete(self, **kwargs) -> str:
        self.call_count += 1
        if self.call_count <= self.failures_before_success:
            raise LLMClientError("temporary network issue", reason="network_error")
        return self.response


class AlwaysFailingLLMClient(LLMClient):
    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        self.call_count = 0

    @property
    def model(self) -> str:
        return "failing-model"

    def complete(self, **kwargs) -> str:
        self.call_count += 1
        raise LLMClientError("simulated LLM failure", reason=self.reason)


class CapturingLLMClient(LLMClient):
    def __init__(self, *, response: str) -> None:
        self.response = response
        self.call_count = 0
        self.last_user_prompt = ""

    @property
    def model(self) -> str:
        return "capturing-model"

    def complete(self, **kwargs) -> str:
        self.call_count += 1
        self.last_user_prompt = kwargs["user_prompt"]
        return self.response


def test_rate_limited_llm_client_enforces_request_budget() -> None:
    client = ConfigurableFakeLLMClient(response="{}")
    limited = RateLimitedLLMClient(
        client,
        LLMRateLimitConfig(request_budget=1),
        logger=logging.getLogger("test"),
    )

    assert limited.complete(system_prompt="", user_prompt="") == "{}"
    with pytest.raises(LLMClientError) as error_info:
        limited.complete(system_prompt="", user_prompt="")

    assert error_info.value.reason == "quota_error"
    assert client.call_count == 1


def test_rate_limited_llm_client_waits_between_provider_calls() -> None:
    current_time = 100.0
    sleeps: list[float] = []

    def clock() -> float:
        return current_time

    def sleeper(delay_seconds: float) -> None:
        nonlocal current_time
        sleeps.append(delay_seconds)
        current_time += delay_seconds

    client = ConfigurableFakeLLMClient(response="{}")
    limited = RateLimitedLLMClient(
        client,
        LLMRateLimitConfig(min_interval_seconds=15.0),
        logger=logging.getLogger("test"),
        clock=clock,
        sleeper=sleeper,
    )

    limited.complete(system_prompt="", user_prompt="")
    limited.complete(system_prompt="", user_prompt="")

    assert sleeps == [15.0]
    assert client.call_count == 2


def test_rate_limited_llm_client_stops_after_provider_quota_error() -> None:
    client = AlwaysFailingLLMClient(reason="quota_error")
    limited = RateLimitedLLMClient(
        client,
        LLMRateLimitConfig(request_budget=10),
        logger=logging.getLogger("test"),
    )

    with pytest.raises(LLMClientError) as first_error:
        limited.complete(system_prompt="", user_prompt="")
    with pytest.raises(LLMClientError) as second_error:
        limited.complete(system_prompt="", user_prompt="")

    assert first_error.value.reason == "quota_error"
    assert second_error.value.reason == "quota_error"
    assert client.call_count == 1


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


def test_extract_official_page_candidates_retries_transient_network_error(
    tmp_path,
) -> None:
    page = _fetched_llm_page()
    client = RetryThenSuccessLLMClient(
        failures_before_success=1,
        response=_llm_response("season_dates_url", "https://example.com/season"),
    )

    candidates, errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert errors == []
    assert len(candidates) == 1
    assert candidates[0].field_path == "season_dates_url"
    assert client.call_count == 2


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


def test_extract_official_page_candidates_salvages_valid_items_from_invalid_price(
    tmp_path,
) -> None:
    page = _fetched_llm_page()
    client = ConfigurableFakeLLMClient(
        response=json.dumps(
            {
                "facts": [
                    {
                        "field_path": "season_dates_url",
                        "value": "https://example.com/season",
                        "evidence": "Season dates page",
                        "confidence": 0.82,
                    }
                ],
                "lift_pass_prices": [
                    {
                        "duration_days": 3,
                        "audience": "adult",
                        "currency": "EUR",
                        "price_kind": "from",
                        "source_url": "https://example.com/prices",
                        "evidence": "Adult 3 days from EUR 220",
                        "confidence": 0.9,
                    },
                    {
                        "duration_days": 6,
                        "audience": "adult",
                        "amount": 390,
                        "currency": "EUR",
                        "price_kind": "fixed",
                        "source_url": "https://example.com/prices",
                        "evidence": "Adult 6 days EUR 390",
                        "confidence": 0.91,
                    },
                ],
            }
        )
    )

    candidates, errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert {candidate.field_path for candidate in candidates} == {
        "season_dates_url",
        "lift_pass_prices",
    }
    price = next(
        candidate
        for candidate in candidates
        if candidate.field_path == "lift_pass_prices"
    )
    assert price.proposed_value["duration_days"] == 6
    assert len(errors) == 1
    assert "invalid LLM extraction output for lift_pass_prices" in errors[0]


def test_extract_official_page_candidates_accepts_season_windows(tmp_path) -> None:
    page = _fetched_llm_page()
    client = ConfigurableFakeLLMClient(
        response=json.dumps(
            {
                "facts": [
                    {
                        "field_path": "season_windows",
                        "value": {
                            "season_label": "2025-2026",
                            "start_date": "2025-10-03",
                            "end_date": "2026-05-17",
                            "status": "planned",
                        },
                        "evidence": "Winter season 03.10.2025 - 17.05.2026",
                        "confidence": 0.92,
                    }
                ],
                "lift_pass_prices": [],
            }
        )
    )

    candidates, errors = extract_official_page_candidates(
        resort_id="stubai-glacier",
        page=page,
        page_role="season_dates",
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert errors == []
    assert candidates[0].field_path == "season_windows"
    assert candidates[0].proposed_value == {
        "season_label": "2025-2026",
        "start_date": "2025-10-03",
        "end_date": "2026-05-17",
        "status": "planned",
    }


def test_extract_official_page_candidates_rejects_child_only_promotional_price(
    tmp_path,
) -> None:
    page = _fetched_llm_page()
    client = ConfigurableFakeLLMClient(
        response=json.dumps(
            {
                "facts": [],
                "lift_pass_prices": [
                    {
                        "duration_days": 1,
                        "audience": "Kinder unter 10 Jahren",
                        "amount": 0,
                        "currency": "EUR",
                        "price_kind": "fixed",
                        "season_label": "Winter",
                        "source_url": "https://example.com/prices",
                        "evidence": (
                            "Kinder unter 10 Jahren erhalten kostenlosen Skipass"
                        ),
                        "confidence": 0.9,
                    }
                ],
            }
        )
    )

    candidates, errors = extract_official_page_candidates(
        resort_id="test-resort",
        page=page,
        page_role="ski_pass",
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert candidates == []
    assert len(errors) == 1
    assert "unsupported LLM lift pass audience" in errors[0]


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


def test_classify_official_links_retries_transient_network_error(tmp_path) -> None:
    links = [
        OfficialLinkCandidate(
            url="https://www.example.com/prices",
            source_page_url="https://www.example.com",
            official_seed_url="https://www.example.com",
            link_text="Prices",
            title=None,
            aria_label=None,
            nearby_text="Ski pass prices",
            source_page_title="Winter",
            is_external=False,
            deterministic_scores={"ski_pass": 0.8},
        )
    ]
    client = RetryThenSuccessLLMClient(
        failures_before_success=1,
        response=json.dumps(
            {
                "roles": {
                    "ski_pass": [
                        {
                            "url": "https://www.example.com/prices",
                            "confidence": 0.9,
                            "reason": "Prices page",
                        }
                    ]
                }
            }
        ),
    )

    classified, errors = classify_official_links_with_llm(
        resort_id="test-resort",
        link_candidates=links,
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert errors == []
    assert classified["ski_pass"][0].url == "https://www.example.com/prices"
    assert client.call_count == 2


def test_classify_official_links_limits_llm_input_to_role_bearing_candidates(
    tmp_path,
) -> None:
    links = [
        OfficialLinkCandidate(
            url=f"https://www.example.com/noise-{index}",
            source_page_url="https://www.example.com",
            official_seed_url="https://www.example.com",
            link_text="About us",
            title=None,
            aria_label=None,
            nearby_text="General page",
            source_page_title="Home",
            is_external=False,
            deterministic_scores={"ski_pass": 0.0},
        )
        for index in range(5)
    ] + [
        OfficialLinkCandidate(
            url=f"https://www.example.com/prices-{index}",
            source_page_url="https://www.example.com",
            official_seed_url="https://www.example.com",
            link_text="Ski pass prices",
            title=None,
            aria_label=None,
            nearby_text="Ski pass prices",
            source_page_title="Winter",
            is_external=False,
            deterministic_scores={"ski_pass": 0.8},
        )
        for index in range(MAX_LLM_LINK_CLASSIFICATION_CANDIDATES + 5)
    ]
    client = CapturingLLMClient(response=json.dumps({"roles": {}}))

    classified, errors = classify_official_links_with_llm(
        resort_id="test-resort",
        link_candidates=links,
        llm_client=client,
        cache_dir=tmp_path,
    )

    assert classified == {}
    assert errors == []
    assert client.call_count == 1
    assert "noise-0" not in client.last_user_prompt
    assert client.last_user_prompt.count("https://www.example.com/prices-") == (
        MAX_LLM_LINK_CLASSIFICATION_CANDIDATES
    )


def test_classify_official_links_rejects_unknown_url(tmp_path) -> None:
    links = [
        OfficialLinkCandidate(
            url="https://www.example.com/prices",
            source_page_url="https://www.example.com",
            official_seed_url="https://www.example.com",
            link_text="Prices",
            title=None,
            aria_label=None,
            nearby_text="Ski pass prices",
            source_page_title="Winter",
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
    assert errors == [
        "LLM link classification returned unknown URL: https://evil.example.com"
    ]


def test_classify_official_links_filters_low_confidence_results(tmp_path) -> None:
    links = [
        OfficialLinkCandidate(
            url="https://www.example.com/events/live-music",
            source_page_url="https://www.example.com",
            official_seed_url="https://www.example.com",
            link_text="Top event live music",
            title=None,
            aria_label=None,
            nearby_text="Top event live music",
            source_page_title="Winter",
            is_external=False,
            deterministic_scores={"official_status": 0.2},
        )
    ]
    client = ConfigurableFakeLLMClient(
        response=json.dumps(
            {
                "roles": {
                    "official_status": [
                        {
                            "url": "https://www.example.com/events/live-music",
                            "confidence": 0.2,
                            "reason": "Low confidence event page",
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
    assert errors == []


def test_classify_official_links_caps_urls_per_role(tmp_path) -> None:
    links = [
        OfficialLinkCandidate(
            url=f"https://www.example.com/prices-{index}",
            source_page_url="https://www.example.com",
            official_seed_url="https://www.example.com",
            link_text=f"Prices {index}",
            title=None,
            aria_label=None,
            nearby_text="Adult tickets",
            source_page_title="Winter",
            is_external=False,
            deterministic_scores={"ski_pass": 0.8},
        )
        for index in range(4)
    ]
    client = ConfigurableFakeLLMClient(
        response=json.dumps(
            {
                "roles": {
                    "ski_pass": [
                        {
                            "url": link.url,
                            "confidence": 0.9,
                            "reason": "Price page link",
                        }
                        for link in links
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
    assert [link.url for link in classified["ski_pass"]] == [
        "https://www.example.com/prices-0",
        "https://www.example.com/prices-1",
        "https://www.example.com/prices-2",
    ]


def test_classify_official_links_uses_cache_for_same_inputs(tmp_path) -> None:
    links = [
        OfficialLinkCandidate(
            url="https://www.example.com/prices",
            source_page_url="https://www.example.com",
            official_seed_url="https://www.example.com",
            link_text="Prices",
            title=None,
            aria_label=None,
            nearby_text="Adult tickets",
            source_page_title="Winter",
            is_external=False,
            deterministic_scores={"ski_pass": 0.8},
        )
    ]
    response = json.dumps(
        {
            "roles": {
                "ski_pass": [
                    {
                        "url": "https://www.example.com/prices",
                        "confidence": 0.88,
                        "reason": "Price page link",
                    }
                ]
            }
        }
    )
    first_client = ConfigurableFakeLLMClient(response=response)
    second_client = ConfigurableFakeLLMClient(response="not-json")

    first_classified, first_errors = classify_official_links_with_llm(
        resort_id="test-resort",
        link_candidates=links,
        llm_client=first_client,
        cache_dir=tmp_path,
    )
    second_classified, second_errors = classify_official_links_with_llm(
        resort_id="test-resort",
        link_candidates=links,
        llm_client=second_client,
        cache_dir=tmp_path,
    )

    assert first_errors == []
    assert second_errors == []
    assert second_classified == first_classified
    assert first_client.call_count == 1
    assert second_client.call_count == 0


def test_classify_official_links_rejects_string_confidence_without_caching(
    tmp_path,
) -> None:
    links = [
        OfficialLinkCandidate(
            url="https://www.example.com/prices",
            source_page_url="https://www.example.com",
            official_seed_url="https://www.example.com",
            link_text="Prices",
            title=None,
            aria_label=None,
            nearby_text="Adult tickets",
            source_page_title="Winter",
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
                            "url": "https://www.example.com/prices",
                            "confidence": "0.93",
                            "reason": "Price page link",
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
    assert len(errors) == 1
    assert errors[0].startswith("invalid LLM link classification output:")
    assert list(tmp_path.glob("*.json")) == []


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
            source=SourceReference(
                source_type="wikidata",
                source_url="https://www.wikidata.org/wiki/Special:EntityData/Q123.json",
            ),
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
            source=SourceReference(
                source_type="osm",
                source_url="https://overpass-api.de/api/interpreter",
            ),
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


def test_render_evidence_sorts_groups_by_severity_before_resort() -> None:
    generated_at = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)
    source = SourceReference(source_type="official", source_url="https://example.com")
    proposals = [
        Proposal(
            resort_id=resort_id,
            field_path="latitude",
            current_value=46.0,
            proposed_value=proposed_value,
            status=status,
            source=source,
            extraction_method="official_page_llm",
            confidence=0.8,
        )
        for resort_id, status, proposed_value in [
            ("resort-same", "same", 46.0),
            ("resort-rejected", "rejected", 46.1),
            ("resort-new", "new", 46.2),
            ("resort-changed", "changed", 46.3),
            ("resort-warning", "warning", 46.4),
            ("resort-conflict", "conflict", 46.5),
        ]
    ]
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=[proposal.resort_id for proposal in proposals],
        proposals=proposals,
        candidates=[],
        fetch_log=[],
    )

    evidence = render_evidence_markdown(output)

    headings = [
        "### `destination:resort-conflict` / `latitude`",
        "### `destination:resort-warning` / `latitude`",
        "### `destination:resort-changed` / `latitude`",
        "### `destination:resort-new` / `latitude`",
        "### `destination:resort-rejected` / `latitude`",
        "### `destination:resort-same` / `latitude`",
    ]
    heading_indexes = [evidence.index(heading) for heading in headings]
    assert heading_indexes == sorted(heading_indexes)


def test_render_evidence_includes_failed_source_health_summary() -> None:
    generated_at = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=["test-resort"],
        proposals=[],
        candidates=[],
        fetch_log=[
            FetchLogEntry(
                resort_id="test-resort\n## fake",
                url="https://example.com/source\n### fake <script>|`",
                fetched_at=generated_at,
                status="failed",
                status_code=503,
                extraction_method="wikidata",
                error="timeout\n## fake <b>|`",
            )
        ],
    )

    evidence = render_evidence_markdown(output)

    assert "## Source Health" in evidence
    assert "Fetch failures: `1`" in evidence
    assert "method=wikidata" in evidence
    assert "status_code=503" in evidence
    assert "\n## fake" not in evidence
    assert "\n### fake" not in evidence
    assert "<script>" not in evidence
    assert "<b>" not in evidence


def test_render_evidence_includes_warning_source_health_summary() -> None:
    generated_at = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=["test-resort"],
        proposals=[],
        candidates=[],
        fetch_log=[
            FetchLogEntry(
                resort_id="test-resort",
                url="https://example.com/prices",
                fetched_at=generated_at,
                status="warning",
                status_code=200,
                extraction_method="official_page_llm",
                error="LLM extraction failed: network_error",
            )
        ],
    )

    evidence = render_evidence_markdown(output)

    assert "Fetch warnings: `1`" in evidence
    assert "method=official_page_llm" in evidence
    assert "LLM extraction failed: network_error" in evidence
    assert "Fetch failures:" not in evidence


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


def test_write_run_outputs_sanitizes_json_values_in_markdown(tmp_path) -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    generated_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    proposal = Proposal(
        resort_id="test-resort",
        field_path="ski_pass_url",
        current_value="old `value` <script>",
        proposed_value="new `value` <b>",
        status="changed",
        source=source,
        extraction_method="official_page_llm",
        confidence=0.8,
    )
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=["test-resort"],
        proposals=[proposal],
        candidates=[],
        fetch_log=[],
    )

    write_run_outputs(tmp_path, output)

    evidence = (tmp_path / "evidence.md").read_text()
    assert "<script>" not in evidence
    assert "<b>" not in evidence
    assert '"old \\`value\\` &lt;script&gt;"' in evidence
    assert '"new \\`value\\` &lt;b&gt;"' in evidence
    assert "Evidence: (none)" in evidence
    assert "Validation notes: (none)" in evidence


def test_write_run_outputs_sanitizes_markdown_code_span_labels(tmp_path) -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    generated_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    proposal = Proposal(
        resort_id="test`resort <script>",
        field_path="ski`pass_url <b>",
        current_value=None,
        proposed_value="https://example.com/prices",
        status="new",
        source=source,
        extraction_method="official_page_llm",
        confidence=0.8,
    )
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=["test`resort <script>"],
        proposals=[proposal],
        candidates=[],
        fetch_log=[],
    )

    write_run_outputs(tmp_path, output)

    evidence = (tmp_path / "evidence.md").read_text()
    assert "## `` test`resort &lt;script&gt; ``" in evidence
    assert (
        "### `` destination:test`resort &lt;script&gt; `` / "
        "`` ski`pass_url &lt;b&gt; ``"
    ) in evidence
    assert "<script>" not in evidence
    assert "<b>" not in evidence


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
    assert "### `destination:test-resort` / `lift_pass_prices`" in evidence
    assert evidence.count("### `destination:test-resort` / `lift_pass_prices`") == 1
    assert evidence.count("- Source:") == 2
    assert "Recommended value: multiple proposals" in evidence


def test_write_run_outputs_recommends_matching_season_window_dates(
    tmp_path,
) -> None:
    generated_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    proposals = [
        Proposal(
            resort_id="test-resort",
            field_path="season_windows",
            current_value=None,
            proposed_value={
                "season_label": "2025-2026",
                "start_date": "2025-11-22",
                "end_date": "2026-05-03",
                "status": "planned",
            },
            status="new",
            source=SourceReference(
                source_type="bergfex",
                source_url="https://www.bergfex.com/test-resort/",
            ),
            extraction_method="bergfex_public_page",
            confidence=0.55,
        ),
        Proposal(
            resort_id="test-resort",
            field_path="season_windows",
            current_value=None,
            proposed_value={
                "season_label": "Hiver",
                "start_date": "2025-11-22",
                "end_date": "2026-05-03",
                "status": "planned",
            },
            status="new",
            source=SourceReference(
                source_type="official",
                source_url="https://www.skipass-tignes.com/",
            ),
            extraction_method="official_page_llm",
            confidence=1.0,
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
    assert "Statuses: new" in evidence
    assert "Recommended value: review required" not in evidence
    assert (
        'Recommended value: {"end_date": "2026-05-03", '
        '"season_label": "Hiver", "start_date": "2025-11-22", '
        '"status": "planned"}'
    ) in evidence


def test_write_run_outputs_keeps_repeatable_conflicts_review_required(
    tmp_path,
) -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    generated_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    proposals = [
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
            status="conflict",
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
                "amount": 410,
                "currency": "EUR",
            },
            status="conflict",
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
    assert "Statuses: conflict" in evidence
    assert "Recommended value: review required" in evidence
    assert "Recommended value: multiple proposals" not in evidence


def test_write_run_outputs_distinguishes_repeated_rental_facts(tmp_path) -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    generated_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    proposals = [
        Proposal(
            resort_id="test-resort",
            field_path="rental_facts",
            current_value=None,
            proposed_value={"name": "Rental A", "price_range": "EUR 30-45"},
            status="new",
            source=source,
            extraction_method="official_page_llm",
            confidence=0.8,
        ),
        Proposal(
            resort_id="test-resort",
            field_path="rental_facts",
            current_value=None,
            proposed_value={"name": "Rental B", "price_range": "EUR 35-50"},
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
    assert "### `destination:test-resort` / `rental_facts`" in evidence
    assert evidence.count("### `destination:test-resort` / `rental_facts`") == 1
    assert evidence.count("- Source:") == 2
    assert "Recommended value: multiple proposals" in evidence


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


def _write_patch_inputs(
    tmp_path,
    *,
    proposals: list[Proposal],
    catalog_payload: list[dict] | None = None,
    registry_payload: dict | None = None,
) -> tuple[Path, Path, Path]:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    output = AcquisitionRunOutput(
        generated_at=datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc),
        selected_resorts=["test-resort"],
        proposals=proposals,
        candidates=[],
        fetch_log=[],
    )
    (artifacts_dir / "proposals.json").write_text(
        json.dumps(output.model_dump(mode="json")),
        encoding="utf-8",
    )
    catalog_path = tmp_path / "resorts.json"
    catalog_path.write_text(
        json.dumps(
            catalog_payload
            if catalog_payload is not None
            else [
                {
                    "resort_id": "test-resort",
                    "name": "Test Resort",
                    "country": "Austria",
                    "region": "Tyrol",
                    "price_level": "medium",
                    "latitude": 47.0,
                    "longitude": 11.0,
                    "base_elevation_m": 1200,
                    "summit_elevation_m": 2800,
                    "season_start_month": 12,
                    "season_end_month": 4,
                    "ski_areas": [
                        {
                            "ski_area_id": "test-resort-ski-area",
                            "name": "Test Resort",
                            "latitude": 47.0,
                            "longitude": 11.0,
                            "base_elevation_m": 1200,
                            "summit_elevation_m": 2800,
                            "season_start_month": 12,
                            "season_end_month": 4,
                        }
                    ],
                    "stay_bases": [
                        {
                            "name": "Village",
                            "price_range": "EUR 150-220",
                            "quality": "standard",
                            "lift_distance": "near",
                            "supported_skill_levels": ["beginner"],
                        }
                    ],
                    "rentals": [],
                }
            ],
        ),
        encoding="utf-8",
    )
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps(
            registry_payload
            if registry_payload is not None
            else {
                "version": 1,
                "resorts": {"test-resort": {"official_urls": {}}},
            }
        ),
        encoding="utf-8",
    )
    return artifacts_dir, catalog_path, registry_path


def test_catalog_patch_applies_safe_new_catalog_and_source_fields(tmp_path) -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    proposals = [
        Proposal(
            resort_id="test-resort",
            target=ProposalTarget(
                entity_type="ski_area", entity_id="test-resort-ski-area"
            ),
            field_path="total_piste_km",
            current_value=None,
            proposed_value=65,
            status="new",
            source=SourceReference(
                source_type="bergfex",
                source_url="https://www.bergfex.com/test-resort/",
            ),
            extraction_method="bergfex_public_page",
            confidence=0.55,
            evidence="Bergfex public page total piste summary",
        ),
        Proposal(
            resort_id="test-resort",
            target=ProposalTarget(
                entity_type="ski_area", entity_id="test-resort-ski-area"
            ),
            field_path="piste_km_by_difficulty",
            current_value=None,
            proposed_value={
                "beginner": 20,
                "intermediate": 35,
                "advanced": 10,
            },
            status="new",
            source=SourceReference(
                source_type="opendatahub",
                source_url="https://tourism.api.opendatahub.com/v1/SkiArea/SKI123",
            ),
            extraction_method="opendatahub",
            confidence=0.95,
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
                "price_kind": "fixed",
                "season_label": "2025-2026",
                "source_url": "https://example.com/prices",
                "evidence": "Adult 6 days EUR 390",
                "confidence": 0.91,
            },
            status="new",
            source=source,
            extraction_method="official_page_llm",
            confidence=0.91,
        ),
        Proposal(
            resort_id="test-resort",
            field_path="ski_pass_url",
            current_value=None,
            proposed_value="https://example.com/prices",
            status="new",
            source=source,
            extraction_method="official_link_discovery",
            confidence=0.8,
        ),
        Proposal(
            resort_id="test-resort",
            field_path="regional_data_ids.osm_relation_id",
            current_value=None,
            proposed_value="123456",
            status="new",
            source=SourceReference(
                source_type="osm",
                source_url="https://overpass-api.de/api/interpreter",
            ),
            extraction_method="osm_discovery",
            confidence=0.85,
        ),
    ]
    artifacts_dir, catalog_path, registry_path = _write_patch_inputs(
        tmp_path,
        proposals=proposals,
    )

    result = apply_catalog_patch(
        artifacts_dir=artifacts_dir,
        catalog_path=catalog_path,
        registry_path=registry_path,
    )

    catalog = json.loads(catalog_path.read_text())
    registry = json.loads(registry_path.read_text())
    ski_area = catalog[0]["ski_areas"][0]
    assert result.applied_count == 5
    assert ski_area["total_piste_km"] == 65
    assert ski_area["piste_km_by_difficulty"] == {
        "beginner": 20,
        "intermediate": 35,
        "advanced": 10,
    }
    assert catalog[0]["lift_pass_prices"] == [
        {
            "duration_days": 6,
            "audience": "adult",
            "amount": 390,
            "currency": "EUR",
            "price_kind": "fixed",
            "season_label": "2025-2026",
            "source_url": "https://example.com/prices",
        }
    ]
    assert registry["resorts"]["test-resort"]["official_urls"]["ski_pass"] == (
        "https://example.com/prices"
    )
    assert (
        registry["resorts"]["test-resort"]["regional_data_ids"]["osm_relation_id"]
        == "123456"
    )
    assert "Applied changes: `5`" in (artifacts_dir / "patch-review.md").read_text()


def test_catalog_patch_deduplicates_season_windows_by_dates_and_status(
    tmp_path,
) -> None:
    proposals = [
        Proposal(
            resort_id="test-resort",
            field_path="season_windows",
            current_value=None,
            proposed_value={
                "season_label": "Hiver",
                "start_date": "2025-11-22",
                "end_date": "2026-05-03",
                "status": "planned",
            },
            status="new",
            source=SourceReference(
                source_type="official",
                source_url="https://www.skipass-tignes.com/",
            ),
            extraction_method="official_page_llm",
            confidence=1.0,
        ),
        Proposal(
            resort_id="test-resort",
            field_path="season_windows",
            current_value=None,
            proposed_value={
                "season_label": "2025-2026",
                "start_date": "2025-11-22",
                "end_date": "2026-05-03",
                "status": "planned",
            },
            status="new",
            source=SourceReference(
                source_type="bergfex",
                source_url="https://www.bergfex.com/test-resort/",
            ),
            extraction_method="bergfex_public_page",
            confidence=0.55,
        ),
    ]
    artifacts_dir, catalog_path, registry_path = _write_patch_inputs(
        tmp_path,
        proposals=proposals,
    )

    result = apply_catalog_patch(
        artifacts_dir=artifacts_dir,
        catalog_path=catalog_path,
        registry_path=registry_path,
    )

    catalog = json.loads(catalog_path.read_text())
    assert result.applied_count == 1
    assert catalog[0]["season_windows"] == [
        {
            "season_label": "Hiver",
            "start_date": "2025-11-22",
            "end_date": "2026-05-03",
            "status": "planned",
        }
    ]


def test_catalog_patch_skips_conflicts_changes_and_destination_terrain(
    tmp_path,
) -> None:
    source = SourceReference(source_type="official", source_url="https://example.com")
    proposals = [
        Proposal(
            resort_id="test-resort",
            field_path="ski_pass_url",
            current_value="https://example.com/old",
            proposed_value="https://example.com/new",
            status="changed",
            source=source,
            extraction_method="official_link_discovery",
            confidence=0.8,
        ),
        Proposal(
            resort_id="test-resort",
            target=ProposalTarget(entity_type="destination", entity_id="test-resort"),
            field_path="total_piste_km",
            current_value=None,
            proposed_value=65,
            status="new",
            source=source,
            extraction_method="official_page_llm",
            confidence=0.8,
        ),
        Proposal(
            resort_id="test-resort",
            target=ProposalTarget(
                entity_type="ski_area", entity_id="test-resort-ski-area"
            ),
            field_path="total_lift_count",
            current_value=None,
            proposed_value=20,
            status="conflict",
            source=source,
            extraction_method="opendatahub",
            confidence=0.95,
        ),
    ]
    artifacts_dir, catalog_path, registry_path = _write_patch_inputs(
        tmp_path,
        proposals=proposals,
        registry_payload={
            "version": 1,
            "resorts": {
                "test-resort": {
                    "official_urls": {
                        "ski_pass": "https://example.com/old",
                    }
                }
            },
        },
    )

    result = apply_catalog_patch(
        artifacts_dir=artifacts_dir,
        catalog_path=catalog_path,
        registry_path=registry_path,
    )

    catalog = json.loads(catalog_path.read_text())
    registry = json.loads(registry_path.read_text())
    assert result.applied_count == 0
    assert "total_piste_km" not in catalog[0]
    assert "total_lift_count" not in catalog[0]["ski_areas"][0]
    assert registry["resorts"]["test-resort"]["official_urls"]["ski_pass"] == (
        "https://example.com/old"
    )
    review = (artifacts_dir / "patch-review.md").read_text()
    assert "changed status is review-only" in review
    assert "terrain facts must target ski_area" in review
    assert "conflict status is review-only" in review


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
            "--skip-wikidata",
            "--skip-osm",
            "--skip-dem",
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
            "--skip-wikidata",
            "--skip-osm",
            "--skip-dem",
        ]
    )

    assert exit_code == 1
    proposals = json.loads((output_dir / "proposals.json").read_text())
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    assert proposals["proposals"]
    assert fetch_log[0]["status"] == "failed"


def test_catalog_acquisition_cli_runs_configured_bergfex_fallback(
    tmp_path,
    monkeypatch,
) -> None:
    registry_path = tmp_path / "sources.json"
    catalog_path = tmp_path / "resorts.json"
    output_dir = tmp_path / "out"
    bergfex_url = "https://www.bergfex.com/stubaier-gletscher/"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "resorts": {
                    "stubai-glacier": {
                        "official_urls": {},
                        "provider_urls": {"bergfex": bergfex_url},
                    }
                },
            }
        )
    )
    catalog_path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "stubai-glacier",
                    "name": "Stubai Glacier",
                    "country": "Austria",
                    "ski_areas": [
                        {
                            "ski_area_id": "stubai-glacier-ski-area",
                            "name": "Stubai Glacier",
                            "base_elevation_m": 1695,
                            "summit_elevation_m": 3210,
                            "season_start_month": 10,
                            "season_end_month": 5,
                        }
                    ],
                }
            ]
        )
    )

    def fake_fetch_html_document(url: str) -> FetchedHtmlDocument:
        assert url == bergfex_url
        return _bergfex_document(
            """
            <html><body>
              <a href="https://www.stubaier-gletscher.com/">https://www.stubaier-gletscher.com/</a>
              <div>1.695 - 3.210 m</div>
              <div>Operation: 08:30 - 16:30 Season: 03.10.2025 - 17.05.2026</div>
              <div>Current information Today, 15:09 Open lifts 7 / 26</div>
              <a href="/stubaier-gletscher/pisten/">Pistes 65 km</a>
            </body></html>
            """
        )

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.fetch_html_document",
        fake_fetch_html_document,
    )

    exit_code = acquisition_main(
        [
            "--resort",
            "stubai-glacier",
            "--registry-path",
            str(registry_path),
            "--catalog-path",
            str(catalog_path),
            "--output-dir",
            str(output_dir),
            "--skip-llm",
            "--skip-opendatahub",
            "--skip-wikidata",
            "--skip-osm",
            "--skip-dem",
            "--skip-official-discovery",
        ]
    )

    assert exit_code == 0
    proposals = json.loads((output_dir / "proposals.json").read_text())
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    field_paths = {proposal["field_path"] for proposal in proposals["proposals"]}
    assert "total_piste_km" in field_paths
    assert "total_lift_count" in field_paths
    assert any(
        entry["extraction_method"] == "bergfex_public_page"
        and entry["status"] == "success"
        for entry in fetch_log
    )


def test_catalog_acquisition_cli_skip_bergfex_disables_configured_fallback(
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
                    "stubai-glacier": {
                        "official_urls": {},
                        "provider_urls": {
                            "bergfex": "https://www.bergfex.com/stubaier-gletscher/"
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
                    "resort_id": "stubai-glacier",
                    "name": "Stubai Glacier",
                    "country": "Austria",
                }
            ]
        )
    )

    def fail_fetch_html_document(url: str) -> FetchedHtmlDocument:
        raise AssertionError(f"Bergfex should be skipped: {url}")

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.fetch_html_document",
        fail_fetch_html_document,
    )

    exit_code = acquisition_main(
        [
            "--resort",
            "stubai-glacier",
            "--registry-path",
            str(registry_path),
            "--catalog-path",
            str(catalog_path),
            "--output-dir",
            str(output_dir),
            "--skip-llm",
            "--skip-opendatahub",
            "--skip-wikidata",
            "--skip-osm",
            "--skip-dem",
            "--skip-official-discovery",
            "--skip-bergfex",
        ]
    )

    assert exit_code == 2
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    assert all(
        entry.get("extraction_method") != "bergfex_public_page" for entry in fetch_log
    )


def test_official_page_llm_extraction_skips_bergfex_provider_url(
    tmp_path,
    monkeypatch,
) -> None:
    def fail_fetch_url(url: str) -> FetchedPage:
        raise AssertionError(f"Bergfex must not be sent to official LLM: {url}")

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.fetch_url",
        fail_fetch_url,
    )

    candidates, fetch_log = runner_extract_official_page_candidates(
        resort_id="stubai-glacier",
        config=ResortSourceConfig(
            provider_urls={"bergfex": "https://www.bergfex.com/stubaier-gletscher/"}
        ),
        max_pages_per_resort=3,
        output_dir=tmp_path,
        llm_client=object(),  # type: ignore[arg-type]
    )

    assert candidates == []
    assert fetch_log == []


def test_official_page_llm_network_exhaustion_logs_warning(
    tmp_path,
    monkeypatch,
) -> None:
    page = _fetched_llm_page()

    def fake_fetch_url(url: str) -> FetchedPage:
        assert url == "https://example.com/prices"
        return page

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.fetch_url",
        fake_fetch_url,
    )
    client = AlwaysFailingLLMClient(reason="network_error")

    candidates, fetch_log = runner_extract_official_page_candidates(
        resort_id="test-resort",
        config=ResortSourceConfig(
            official_urls={"ski_pass": "https://example.com/prices"}
        ),
        max_pages_per_resort=1,
        output_dir=tmp_path,
        llm_client=client,
    )

    assert candidates == []
    assert client.call_count == 3
    assert [entry.status for entry in fetch_log] == ["success", "warning"]
    assert "network_error" in (fetch_log[1].error or "")


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


def _weak_wikidata_entity_payload() -> dict[str, object]:
    return {
        "entities": {
            "Q123": {
                "claims": {
                    "P31": [
                        {
                            "rank": "normal",
                            "mainsnak": {
                                "datavalue": {
                                    "value": {
                                        "entity-type": "item",
                                        "numeric-id": 484170,
                                        "id": "Q484170",
                                    },
                                    "type": "wikibase-entityid",
                                }
                            },
                        }
                    ]
                }
            }
        }
    }


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

    def fake_discover_official_links_for_resort(
        **kwargs: object,
    ) -> tuple[list[OfficialLinkCandidate], list[FetchLogEntry]]:
        context = kwargs["context"]
        assert isinstance(context, SourceRunContext)
        assert (
            "https://www.example-resort.com"
            in context.effective_official_urls_by_role()["ski_area"]
        )
        return (
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
        )

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.discover_official_links_for_resort",
        fake_discover_official_links_for_resort,
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


def test_catalog_acquisition_uses_osm_discovery_url_as_same_run_seed(
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
                    "latitude": 46.5,
                    "longitude": 11.0,
                    "ski_areas": [
                        {
                            "ski_area_id": "test-ski-area",
                            "latitude": 46.5,
                            "longitude": 11.0,
                        }
                    ],
                }
            ]
        )
    )

    def fake_fetch_json_value(
        resort_id: str,
        url: str,
        started_at: datetime,
        *,
        extraction_method: ExtractionMethod,
    ) -> tuple[object | None, FetchLogEntry]:
        if extraction_method == "wikidata":
            return _weak_wikidata_entity_payload(), FetchLogEntry(
                resort_id=resort_id,
                url=url,
                fetched_at=started_at,
                status="success",
                extraction_method=extraction_method,
            )
        if extraction_method == "osm_discovery":
            return _osm_discovery_payload(), FetchLogEntry(
                resort_id=resort_id,
                url=url,
                fetched_at=started_at,
                status="success",
                extraction_method=extraction_method,
            )
        if extraction_method == "osm":
            assert "relation%28777%29" in url
            return {
                "elements": [
                    {
                        "type": "relation",
                        "id": 777,
                        "center": {"lat": 46.501, "lon": 11.001},
                        "tags": {"name": "Test Resort"},
                    }
                ]
            }, FetchLogEntry(
                resort_id=resort_id,
                url=url,
                fetched_at=started_at,
                status="success",
                extraction_method=extraction_method,
            )
        raise AssertionError(f"Unexpected fetch: {extraction_method} {url}")

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._extract_opendatahub_discovery",
        lambda *args, **kwargs: ([], None),
    )
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._fetch_json_value",
        fake_fetch_json_value,
    )

    def fake_discover_official_links_for_resort(
        **kwargs: object,
    ) -> tuple[list[OfficialLinkCandidate], list[FetchLogEntry]]:
        context = kwargs["context"]
        assert isinstance(context, SourceRunContext)
        assert (
            "https://www.test-resort.example"
            in context.effective_official_urls_by_role()["ski_area"]
        )
        return [], []

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.discover_official_links_for_resort",
        fake_discover_official_links_for_resort,
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
            "--skip-dem",
            "--skip-llm",
        ]
    )

    assert exit_code == 0
    proposals = json.loads((output_dir / "proposals.json").read_text())
    values = {
        (proposal["extraction_method"], proposal["field_path"]): proposal[
            "proposed_value"
        ]
        for proposal in proposals["proposals"]
    }
    assert (
        values[("osm_discovery", "ski_area_official_url")]
        == "https://www.test-resort.example"
    )
    assert values[("osm_discovery", "regional_data_ids.osm_relation_id")] == "777"
    assert values[("osm", "latitude")] == 46.501


def test_catalog_acquisition_does_not_run_osm_discovery_for_strong_wikidata(
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
                    "latitude": 46.5,
                    "longitude": 11.0,
                }
            ]
        )
    )

    def fake_fetch_json_value(
        resort_id: str,
        url: str,
        started_at: datetime,
        *,
        extraction_method: ExtractionMethod,
    ) -> tuple[object | None, FetchLogEntry]:
        if extraction_method == "wikidata":
            return _wikidata_entity_payload(), FetchLogEntry(
                resort_id=resort_id,
                url=url,
                fetched_at=started_at,
                status="success",
                extraction_method=extraction_method,
            )
        if extraction_method == "osm":
            return _osm_relation_payload(), FetchLogEntry(
                resort_id=resort_id,
                url=url,
                fetched_at=started_at,
                status="success",
                extraction_method=extraction_method,
            )
        raise AssertionError(f"Unexpected fetch: {extraction_method} {url}")

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._extract_opendatahub_discovery",
        lambda *args, **kwargs: ([], None),
    )
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._fetch_json_value",
        fake_fetch_json_value,
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
            "--skip-dem",
            "--skip-official-discovery",
            "--skip-llm",
        ]
    )

    assert exit_code == 0
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    assert not any(
        entry.get("extraction_method") == "osm_discovery" for entry in fetch_log
    )


def test_catalog_acquisition_skip_osm_disables_discovery_and_relation_fetch(
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
                    "latitude": 46.5,
                    "longitude": 11.0,
                }
            ]
        )
    )

    def fake_fetch_json_value(
        resort_id: str,
        url: str,
        started_at: datetime,
        *,
        extraction_method: ExtractionMethod,
    ) -> tuple[object | None, FetchLogEntry]:
        if extraction_method == "wikidata":
            return _weak_wikidata_entity_payload(), FetchLogEntry(
                resort_id=resort_id,
                url=url,
                fetched_at=started_at,
                status="success",
                extraction_method=extraction_method,
            )
        raise AssertionError(f"OSM should be skipped: {extraction_method} {url}")

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._extract_opendatahub_discovery",
        lambda *args, **kwargs: ([], None),
    )
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._fetch_json_value",
        fake_fetch_json_value,
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
            "--skip-official-discovery",
            "--skip-llm",
        ]
    )

    assert exit_code == 0
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    assert not any(
        entry.get("extraction_method") in {"osm_discovery", "osm"}
        for entry in fetch_log
    )


def test_catalog_acquisition_osm_discovery_failure_returns_failure_code(
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
                    "latitude": 46.5,
                    "longitude": 11.0,
                }
            ]
        )
    )

    def fake_fetch_json_value(
        resort_id: str,
        url: str,
        started_at: datetime,
        *,
        extraction_method: ExtractionMethod,
    ) -> tuple[object | None, FetchLogEntry]:
        if extraction_method == "wikidata":
            return _weak_wikidata_entity_payload(), FetchLogEntry(
                resort_id=resort_id,
                url=url,
                fetched_at=started_at,
                status="success",
                extraction_method=extraction_method,
            )
        if extraction_method == "osm_discovery":
            return None, FetchLogEntry(
                resort_id=resort_id,
                url=url,
                fetched_at=started_at,
                status="failed",
                extraction_method=extraction_method,
                error="simulated overpass failure",
            )
        raise AssertionError(f"Unexpected fetch: {extraction_method} {url}")

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._extract_opendatahub_discovery",
        lambda *args, **kwargs: ([], None),
    )
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._fetch_json_value",
        fake_fetch_json_value,
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
            "--skip-dem",
            "--skip-official-discovery",
            "--skip-llm",
        ]
    )

    assert exit_code == 1
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    assert any(
        entry.get("extraction_method") == "osm_discovery"
        and entry["status"] == "failed"
        and "simulated overpass failure" in entry["error"]
        for entry in fetch_log
    )


def test_catalog_acquisition_skip_wikidata_disables_wikidata_fetch(
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
                }
            ]
        )
    )

    def fail_fetch_json_value(
        resort_id: str,
        url: str,
        started_at: datetime,
        *,
        extraction_method: ExtractionMethod,
    ) -> tuple[object | None, FetchLogEntry]:
        raise AssertionError("Wikidata should not be fetched")

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._fetch_json_value",
        fail_fetch_json_value,
    )
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._extract_opendatahub_discovery",
        lambda *args, **kwargs: ([], None),
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
    assert not any(entry.get("extraction_method") == "wikidata" for entry in fetch_log)


def test_catalog_acquisition_skips_invalid_osm_relation_id_before_fetch(
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
                        "official_urls": {},
                        "regional_data_ids": {
                            "osm_relation_id": "123);node(1);out;",
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
                    "country": "Italy",
                }
            ]
        )
    )

    def fail_fetch_json_value(
        resort_id: str,
        url: str,
        started_at: datetime,
        *,
        extraction_method: ExtractionMethod,
    ) -> tuple[object | None, FetchLogEntry]:
        raise AssertionError(f"OSM should not fetch invalid relation ID: {url}")

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition._fetch_json_value",
        fail_fetch_json_value,
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
            "--skip-wikidata",
            "--skip-dem",
            "--skip-official-discovery",
            "--skip-llm",
        ]
    )

    assert exit_code == 0
    fetch_log = json.loads((output_dir / "fetch-log.json").read_text())
    assert any(
        entry["extraction_method"] == "osm"
        and entry["status"] == "skipped"
        and "Invalid OSM relation ID" in entry["error"]
        for entry in fetch_log
    )


def test_discover_official_links_caps_candidates_globally_across_seeds(
    monkeypatch,
) -> None:
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    context = SourceRunContext.from_config(
        ResortSourceConfig(
            official_urls={"ski_area": "https://seed-one.example"},
        )
    )
    context.add_discovered_official_url(
        DiscoveredOfficialUrl(
            role="ski_area",
            url="https://seed-two.example",
            confidence=0.8,
            source="test",
        )
    )

    class FakeHtmlDocument:
        def __init__(self, url: str) -> None:
            self.url = url
            self.final_url = url
            self.status_code = 200
            self.fetched_at = fetched_at
            self.raw_html = "<html></html>"
            self.content_hash = f"hash:{url}"
            self.truncated = False

    def fake_fetch_html_document(url: str) -> FakeHtmlDocument:
        return FakeHtmlDocument(url)

    def fake_extract_link_candidates_from_html(
        *,
        html: str,
        source_url: str,
        official_seed_url: str,
        max_links: int,
        allow_external_links: bool = True,
    ) -> list[OfficialLinkCandidate]:
        urls = (
            [
                "https://seed-one.example/candidate-0",
                "https://seed-one.example/candidate-1",
            ]
            if official_seed_url == "https://seed-one.example"
            else [
                "https://seed-one.example/candidate-0",
                "https://seed-two.example/candidate-unique",
            ]
        )
        return [
            OfficialLinkCandidate(
                url=url,
                source_page_url=source_url,
                official_seed_url=official_seed_url,
                link_text=f"Candidate {index}",
                title=None,
                aria_label=None,
                nearby_text="Ski pass prices",
                source_page_title=None,
                is_external=False,
                deterministic_scores={"ski_pass": 0.8},
            )
            for index, url in enumerate(urls[:max_links])
        ]

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.fetch_html_document",
        fake_fetch_html_document,
    )
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.extract_link_candidates_from_html",
        fake_extract_link_candidates_from_html,
    )

    candidates, fetch_log = discover_official_links_for_resort(
        resort_id="test-resort",
        context=context,
        max_links_per_resort=3,
    )

    assert len(candidates) == 3
    assert [candidate.url for candidate in candidates] == [
        "https://seed-one.example/candidate-0",
        "https://seed-one.example/candidate-1",
        "https://seed-two.example/candidate-unique",
    ]
    fetched_urls = [entry.url for entry in fetch_log]
    assert "https://seed-one.example" in fetched_urls
    assert "https://seed-two.example" in fetched_urls


def test_discover_official_links_treats_discovered_seed_fetch_failure_as_skipped(
    monkeypatch,
) -> None:
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    context = SourceRunContext.from_config(
        ResortSourceConfig(
            official_urls={"ski_area": "https://configured.example"},
        )
    )
    context.add_discovered_official_url(
        DiscoveredOfficialUrl(
            role="ski_area",
            url="https://discovered.example/stale",
            confidence=0.9,
            source="osm_discovery",
        )
    )

    class FakeHtmlDocument:
        def __init__(self, url: str) -> None:
            self.url = url
            self.final_url = url
            self.status_code = 200
            self.fetched_at = fetched_at
            self.raw_html = "<html></html>"
            self.content_hash = f"hash:{url}"
            self.truncated = False

    def fake_fetch_html_document(url: str) -> FakeHtmlDocument:
        if url == "https://discovered.example/stale":
            request = httpx.Request("GET", url)
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("not found", request=request, response=response)
        return FakeHtmlDocument(url)

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.fetch_html_document",
        fake_fetch_html_document,
    )

    _, fetch_log = discover_official_links_for_resort(
        resort_id="test-resort",
        context=context,
        max_links_per_resort=5,
    )

    stale_log = next(
        entry for entry in fetch_log if entry.url == "https://discovered.example/stale"
    )
    assert stale_log.status == "skipped"
    assert stale_log.status_code == 404


def test_discover_official_links_fetches_sitemap_and_first_level_pages(
    monkeypatch,
) -> None:
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    context = SourceRunContext.from_config(
        ResortSourceConfig(
            official_urls={"ski_area": "https://www.example.com"},
        )
    )

    class FakeHtmlDocument:
        def __init__(self, url: str, raw_html: str) -> None:
            self.url = url
            self.final_url = url
            self.status_code = 200
            self.fetched_at = fetched_at
            self.raw_html = raw_html
            self.content_hash = f"hash:{url}"
            self.truncated = False

    documents = {
        "https://www.example.com": """
            <html><head><title>Winter</title></head><body>
              <a href="/skipass-prices">Ski pass prices</a>
            </body></html>
        """,
        "https://www.example.com/sitemap.xml": """
            <urlset>
              <url><loc>https://www.example.com/rentals</loc></url>
            </urlset>
        """,
        "https://www.example.com/skipass-prices": """
            <html><body>
              <a href="/trail-map">Piste map</a>
              <a href="https://external-ticket.test/buy">Buy tickets</a>
              <a href="https://tickets.example.com/buy">Buy tickets</a>
            </body></html>
        """,
        "https://www.example.com/rentals": """
            <html><body><a href="/noleggio">Noleggio sci</a></body></html>
        """,
    }

    def fake_fetch_html_document(url: str) -> FakeHtmlDocument:
        return FakeHtmlDocument(url, documents[url])

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.fetch_html_document",
        fake_fetch_html_document,
    )

    candidates, fetch_log = discover_official_links_for_resort(
        resort_id="test-resort",
        context=context,
        max_links_per_resort=10,
    )

    candidate_urls = {candidate.url for candidate in candidates}
    assert "https://www.example.com/skipass-prices" in candidate_urls
    assert "https://www.example.com/rentals" in candidate_urls
    assert "https://www.example.com/trail-map" in candidate_urls
    assert "https://www.example.com/noleggio" in candidate_urls
    assert "https://external-ticket.test/buy" not in candidate_urls
    assert "https://tickets.example.com/buy" not in candidate_urls
    assert [entry.url for entry in fetch_log] == [
        "https://www.example.com",
        "https://www.example.com/sitemap.xml",
        "https://www.example.com/skipass-prices",
        "https://www.example.com/rentals",
    ]


def test_discover_official_links_limits_first_level_fetches_per_resort(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.MAX_FIRST_LEVEL_PAGES_PER_RESORT",
        1,
    )
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    context = SourceRunContext.from_config(
        ResortSourceConfig(
            official_urls={"ski_area": "https://seed-one.example"},
        )
    )
    context.add_discovered_official_url(
        DiscoveredOfficialUrl(
            role="ski_area",
            url="https://seed-two.example",
            confidence=0.8,
            source="test",
        )
    )

    class FakeHtmlDocument:
        def __init__(self, url: str, raw_html: str) -> None:
            self.url = url
            self.final_url = url
            self.status_code = 200
            self.fetched_at = fetched_at
            self.raw_html = raw_html
            self.content_hash = f"hash:{url}"
            self.truncated = False

    documents = {
        "https://seed-one.example": (
            '<html><a href="/one-prices">Ski pass prices</a></html>'
        ),
        "https://seed-one.example/sitemap.xml": "<urlset></urlset>",
        "https://seed-one.example/one-prices": "<html></html>",
        "https://seed-two.example": (
            '<html><a href="/two-prices">Ski pass prices</a></html>'
        ),
        "https://seed-two.example/sitemap.xml": "<urlset></urlset>",
        "https://seed-two.example/two-prices": "<html></html>",
    }

    def fake_fetch_html_document(url: str) -> FakeHtmlDocument:
        return FakeHtmlDocument(url, documents[url])

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.fetch_html_document",
        fake_fetch_html_document,
    )

    _, fetch_log = discover_official_links_for_resort(
        resort_id="test-resort",
        context=context,
        max_links_per_resort=10,
    )

    fetched_urls = [entry.url for entry in fetch_log]
    assert "https://seed-one.example/one-prices" in fetched_urls
    assert "https://seed-two.example/two-prices" not in fetched_urls
    assert "https://seed-two.example" in fetched_urls
    assert "https://seed-two.example/sitemap.xml" in fetched_urls


def test_discover_official_links_fetches_cascade_when_candidate_cap_full(
    monkeypatch,
) -> None:
    fetched_at = datetime(2026, 5, 4, 10, 0, tzinfo=timezone.utc)
    context = SourceRunContext.from_config(
        ResortSourceConfig(
            official_urls={"ski_area": "https://www.example.com"},
        )
    )

    class FakeHtmlDocument:
        def __init__(self, url: str, raw_html: str) -> None:
            self.url = url
            self.final_url = url
            self.status_code = 200
            self.fetched_at = fetched_at
            self.raw_html = raw_html
            self.content_hash = f"hash:{url}"
            self.truncated = False

    documents = {
        "https://www.example.com": (
            '<html><a href="/skipass-prices">Ski pass prices</a></html>'
        ),
        "https://www.example.com/sitemap.xml": """
            <urlset>
              <url><loc>https://www.example.com/rentals</loc></url>
            </urlset>
        """,
        "https://www.example.com/skipass-prices": "<html></html>",
        "https://www.example.com/rentals": "<html></html>",
    }

    def fake_fetch_html_document(url: str) -> FakeHtmlDocument:
        return FakeHtmlDocument(url, documents[url])

    monkeypatch.setattr(
        "app.data.resort_acquisition.run_catalog_acquisition.fetch_html_document",
        fake_fetch_html_document,
    )

    candidates, fetch_log = discover_official_links_for_resort(
        resort_id="test-resort",
        context=context,
        max_links_per_resort=1,
    )

    assert [candidate.url for candidate in candidates] == [
        "https://www.example.com/skipass-prices"
    ]
    assert [entry.url for entry in fetch_log] == [
        "https://www.example.com",
        "https://www.example.com/sitemap.xml",
        "https://www.example.com/skipass-prices",
        "https://www.example.com/rentals",
    ]


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


def test_catalog_acquisition_workflow_can_create_draft_pr_only_when_requested() -> None:
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
        inputs = triggers["workflow_dispatch"]["inputs"]
        assert inputs["create_pr"]["default"] is False

        permissions = parsed_workflow["permissions"]
        assert permissions["contents"] == "write"
        assert permissions["pull-requests"] == "write"

        steps = parsed_workflow["jobs"]["catalog-acquisition"]["steps"]
        assert any("upload-artifact" in step.get("uses", "") for step in steps)
        assert any(
            step.get("name") == "Apply conservative catalog patch"
            and "generate_catalog_patch" in step["run"]
            and "inputs.create_pr" in step.get("if", "")
            for step in steps
        )
        assert any(
            step.get("name") == "Validate patched catalog"
            and "validate_resort_catalog" in step["run"]
            and "inputs.create_pr" in step.get("if", "")
            for step in steps
        )
        assert any(
            step.get("name") == "Run focused patch tests"
            and "pytest tests/test_loader.py tests/test_resort_acquisition.py -q"
            in step["run"]
            and "inputs.create_pr" in step.get("if", "")
            for step in steps
        )
        assert any(
            step.get("name") == "Create draft catalog patch PR"
            and "gh pr create" in step["run"]
            and "--draft" in step["run"]
            and "inputs.create_pr" in step.get("if", "")
            for step in steps
        )

        build_args_step = next(
            step for step in steps if step["name"] == "Build acquisition arguments"
        )
        assert "${{ inputs." not in build_args_step["run"]
        assert build_args_step["env"] == {
            "INPUT_RESORTS": "${{ inputs.resorts }}",
            "INPUT_COUNTRY": "${{ inputs.country }}",
            "INPUT_SKIP_LLM": "${{ inputs.skip_llm }}",
            "INPUT_SKIP_WIKIDATA": "${{ inputs.skip_wikidata }}",
            "INPUT_SKIP_OSM": "${{ inputs.skip_osm }}",
            "INPUT_SKIP_DEM": "${{ inputs.skip_dem }}",
            "INPUT_SKIP_OFFICIAL_DISCOVERY": ("${{ inputs.skip_official_discovery }}"),
            "INPUT_SKIP_LLM_LINK_CLASSIFICATION": (
                "${{ inputs.skip_llm_link_classification }}"
            ),
            "INPUT_SKIP_BERGFEX": "${{ inputs.skip_bergfex }}",
            "INPUT_MAX_PAGES_PER_RESORT": "${{ inputs.max_pages_per_resort }}",
        }
        for flag in [
            "--skip-wikidata",
            "--skip-osm",
            "--skip-dem",
            "--skip-official-discovery",
            "--skip-llm-link-classification",
            "--skip-bergfex",
        ]:
            assert flag in build_args_step["run"]
    else:
        assert "workflow_dispatch:" in workflow
        assert "create_pr:" in workflow
        assert "default: false" in workflow
        assert "contents: write" in workflow
        assert "pull-requests: write" in workflow
        assert "upload-artifact" in workflow
        assert "generate_catalog_patch" in workflow
        assert "gh pr create" in workflow
        assert "--draft" in workflow
