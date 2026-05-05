from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from app.ai.gemini_client import GeminiClient
from app.data.loader import DEFAULT_RESORTS_PATH
from app.data.resort_acquisition.dem import (
    DEFAULT_DEM_DATASET_STACK,
    catalog_ski_area_points,
    extract_dem_sanity_candidates,
    opentopodata_url,
)
from app.data.resort_acquisition.discovery import (
    OPENDATAHUB_DISCOVERY_RESORT_ID,
    OPENDATAHUB_SKI_AREA_INDEX_URL,
    discover_opendatahub_id_candidates,
)
from app.data.resort_acquisition.extractors import (
    OFFICIAL_ROLE_FIELD_PATHS,
    extract_opendatahub_candidates,
    extract_registry_candidates,
)
from app.data.resort_acquisition.fetching import (
    _USER_AGENT,
    FetchedHtmlDocument,
    fetch_html_document,
    fetch_url,
    get_with_transport_retries,
    stable_content_hash,
)
from app.data.resort_acquisition.link_classify import (
    classify_official_links_with_llm,
)
from app.data.resort_acquisition.llm_extract import extract_official_page_candidates
from app.data.resort_acquisition.models import (
    AcquisitionRunOutput,
    CandidateFact,
    ExtractionMethod,
    FetchLogEntry,
    ResortSourceConfig,
    SourceReference,
    SourceRegistry,
)
from app.data.resort_acquisition.official_links import (
    MAX_FIRST_LEVEL_PAGES_PER_RESORT,
    MAX_LINK_CANDIDATES_PER_RESORT,
    OfficialLinkCandidate,
    extract_link_candidates_from_html,
    official_link_candidate_from_url,
    parse_sitemap_urls,
)
from app.data.resort_acquisition.osm import (
    OVERPASS_INTERPRETER_URL,
    extract_osm_relation_candidates,
    normalize_osm_relation_id,
    overpass_relation_query,
)
from app.data.resort_acquisition.proposals import (
    build_proposals,
    load_raw_catalog_by_resort,
)
from app.data.resort_acquisition.registry import (
    DEFAULT_SOURCE_REGISTRY_PATH,
    load_source_registry,
)
from app.data.resort_acquisition.reports import write_run_outputs
from app.data.resort_acquisition.source_context import (
    DiscoveredOfficialUrl,
    SourceRunContext,
)
from app.data.resort_acquisition.wikidata import (
    extract_wikidata_candidates,
    wikidata_entity_url,
)

OPENDATAHUB_SKI_AREA_URL = (
    "https://tourism.api.opendatahub.com/v1/SkiArea/{ski_area_id}?language=en"
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    registry = load_source_registry(args.registry_path)
    raw_catalog = load_raw_catalog_by_resort(args.catalog_path)
    selected_resorts = _select_resorts(
        raw_catalog,
        resort_ids=args.resort,
        country=args.country,
    )

    generated_at = datetime.now(timezone.utc)
    candidates: list[CandidateFact] = []
    fetch_log: list[FetchLogEntry] = []
    llm_client = GeminiClient() if not args.skip_llm else None
    discovered_opendatahub_ids: dict[str, str] = {}

    if not args.skip_opendatahub:
        discovery_candidates, discovery_log = _extract_opendatahub_discovery(
            selected_resorts,
            raw_catalog,
            registry,
            generated_at,
        )
        candidates.extend(discovery_candidates)
        if discovery_log is not None:
            fetch_log.append(discovery_log)
        discovered_opendatahub_ids = _discovered_opendatahub_ids(discovery_candidates)

    for resort_id in selected_resorts:
        config = registry.resorts.get(resort_id)
        if config is not None:
            candidates.extend(
                extract_registry_candidates(resort_id, config, generated_at)
            )
        elif args.skip_opendatahub:
            fetch_log.append(
                FetchLogEntry(
                    resort_id=resort_id,
                    url="source registry",
                    fetched_at=generated_at,
                    status="skipped",
                    error="No source registry entry for selected resort",
                )
            )

        config = config or ResortSourceConfig()
        source_context = SourceRunContext.from_config(config)
        configured_opendatahub_id = config.regional_data_ids.opendatahub_ski_area_id
        discovered_opendatahub_id = discovered_opendatahub_ids.get(resort_id)
        effective_config = _config_with_opendatahub_id(
            config,
            discovered_opendatahub_id,
        )

        if not args.skip_opendatahub:
            opendatahub_candidates, opendatahub_log = _extract_opendatahub(
                resort_id,
                effective_config,
                generated_at,
                raw_catalog.get(resort_id),
            )
            if (
                configured_opendatahub_id is None
                and discovered_opendatahub_id is not None
            ):
                opendatahub_candidates = [
                    candidate
                    for candidate in opendatahub_candidates
                    if candidate.field_path
                    != "regional_data_ids.opendatahub_ski_area_id"
                ]
            candidates.extend(opendatahub_candidates)
            if opendatahub_log is not None:
                fetch_log.append(opendatahub_log)

        if not args.skip_wikidata:
            wikidata_candidates, wikidata_log = _extract_wikidata(
                resort_id=resort_id,
                context=source_context,
                started_at=generated_at,
                resort_payload=raw_catalog.get(resort_id, {}),
            )
            candidates.extend(wikidata_candidates)
            if wikidata_log is not None:
                fetch_log.append(wikidata_log)
            _add_wikidata_discoveries_to_context(source_context, wikidata_candidates)

        if not args.skip_osm:
            osm_candidates, osm_log = _extract_osm(
                resort_id=resort_id,
                context=source_context,
                started_at=generated_at,
                resort_payload=raw_catalog.get(resort_id, {}),
            )
            candidates.extend(osm_candidates)
            if osm_log is not None:
                fetch_log.append(osm_log)

        if not args.skip_dem:
            dem_candidates, dem_log = _extract_dem(
                resort_id=resort_id,
                started_at=generated_at,
                resort_payload=raw_catalog.get(resort_id, {}),
            )
            candidates.extend(dem_candidates)
            if dem_log is not None:
                fetch_log.append(dem_log)

        link_candidates: list[OfficialLinkCandidate] = []
        if not args.skip_official_discovery:
            link_candidates, link_fetch_log = discover_official_links_for_resort(
                resort_id=resort_id,
                context=source_context,
            )
            fetch_log.extend(link_fetch_log)
            deterministic_link_candidates = _official_link_candidates(
                resort_id=resort_id,
                link_candidates=link_candidates,
                fetched_at=generated_at,
                extraction_method="official_link_discovery",
            )
            candidates.extend(deterministic_link_candidates)
            _add_official_link_discoveries_to_context(
                source_context,
                deterministic_link_candidates,
                source="official_link_discovery",
            )

        if (
            link_candidates
            and llm_client is not None
            and not args.skip_llm_link_classification
        ):
            llm_link_candidates, llm_link_fetch_log = _classify_official_links(
                resort_id=resort_id,
                link_candidates=link_candidates,
                output_dir=args.output_dir,
                llm_client=llm_client,
                fetched_at=generated_at,
            )
            candidates.extend(llm_link_candidates)
            fetch_log.extend(llm_link_fetch_log)
            _add_official_link_discoveries_to_context(
                source_context,
                llm_link_candidates,
                source="official_link_llm",
            )

        if llm_client is not None:
            page_candidates, page_fetch_log = _extract_official_page_candidates(
                resort_id=resort_id,
                config=source_context.effective_official_extraction_config(),
                max_pages_per_resort=args.max_pages_per_resort,
                output_dir=args.output_dir,
                llm_client=llm_client,
            )
            candidates.extend(page_candidates)
            fetch_log.extend(page_fetch_log)

    proposals = build_proposals(raw_catalog, candidates)
    output = AcquisitionRunOutput(
        generated_at=generated_at,
        selected_resorts=selected_resorts,
        proposals=proposals,
        candidates=candidates,
        fetch_log=fetch_log,
    )
    write_run_outputs(args.output_dir, output)

    print(
        f"Wrote {len(proposals)} proposals for "
        f"{len(selected_resorts)} resorts to {args.output_dir}"
    )
    if any(entry.status == "failed" for entry in fetch_log):
        return 1
    return (
        0
        if any(candidate.validation_status == "accepted" for candidate in candidates)
        else 2
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run resort catalog acquisition for selected resorts."
    )
    parser.add_argument("--resort", action="append", default=[])
    parser.add_argument("--country")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-pages-per-resort", type=int, default=3)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--skip-opendatahub", action="store_true")
    parser.add_argument("--skip-wikidata", action="store_true")
    parser.add_argument("--skip-osm", action="store_true")
    parser.add_argument("--skip-dem", action="store_true")
    parser.add_argument("--skip-official-discovery", action="store_true")
    parser.add_argument("--skip-llm-link-classification", action="store_true")
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=DEFAULT_SOURCE_REGISTRY_PATH,
    )
    parser.add_argument("--catalog-path", type=Path, default=DEFAULT_RESORTS_PATH)
    args = parser.parse_args(argv)
    if args.max_pages_per_resort < 0:
        raise ValueError("max-pages-per-resort must be non-negative")
    return args


def _select_resorts(
    raw_catalog: dict[str, dict[str, Any]],
    *,
    resort_ids: list[str],
    country: str | None,
) -> list[str]:
    if resort_ids:
        selected = sorted(dict.fromkeys(resort_ids))
        unknown_ids = [
            resort_id for resort_id in selected if resort_id not in raw_catalog
        ]
        if unknown_ids:
            raise ValueError(f"Unknown resort ID: {', '.join(unknown_ids)}")
    elif country is not None:
        selected = sorted(
            resort_id
            for resort_id, resort in raw_catalog.items()
            if resort.get("country") == country
        )
    else:
        selected = sorted(raw_catalog)

    if not selected:
        raise ValueError("No resorts selected")
    return selected


def _extract_opendatahub_discovery(
    selected_resorts: list[str],
    raw_catalog: dict[str, dict[str, Any]],
    registry: SourceRegistry,
    started_at: datetime,
) -> tuple[list[CandidateFact], FetchLogEntry | None]:
    payload, fetch_log = _fetch_json_value(
        OPENDATAHUB_DISCOVERY_RESORT_ID,
        OPENDATAHUB_SKI_AREA_INDEX_URL,
        started_at,
        extraction_method="opendatahub_discovery",
    )
    if payload is None:
        return [], fetch_log
    return (
        discover_opendatahub_id_candidates(
            raw_catalog_by_resort=raw_catalog,
            selected_resorts=selected_resorts,
            registry=registry,
            payload=payload,
            fetched_at=fetch_log.fetched_at,
            source_url=OPENDATAHUB_SKI_AREA_INDEX_URL,
        ),
        fetch_log,
    )


def _discovered_opendatahub_ids(candidates: list[CandidateFact]) -> dict[str, str]:
    discovered: dict[str, str] = {}
    for candidate in candidates:
        if (
            candidate.validation_status == "accepted"
            and candidate.field_path == "regional_data_ids.opendatahub_ski_area_id"
            and isinstance(candidate.proposed_value, str)
        ):
            discovered[candidate.resort_id] = candidate.proposed_value
    return discovered


def _config_with_opendatahub_id(
    config: ResortSourceConfig,
    opendatahub_id: str | None,
) -> ResortSourceConfig:
    if config.regional_data_ids.opendatahub_ski_area_id is not None:
        return config
    if opendatahub_id is None:
        return config
    return config.model_copy(
        update={
            "regional_data_ids": config.regional_data_ids.model_copy(
                update={"opendatahub_ski_area_id": opendatahub_id}
            )
        }
    )


def _extract_opendatahub(
    resort_id: str,
    config: ResortSourceConfig,
    started_at: datetime,
    resort_payload: dict[str, Any] | None = None,
) -> tuple[list[CandidateFact], FetchLogEntry | None]:
    ski_area_id = config.regional_data_ids.opendatahub_ski_area_id
    if ski_area_id is None:
        return [], None

    source_url = OPENDATAHUB_SKI_AREA_URL.format(ski_area_id=ski_area_id)
    payload, fetch_log = _fetch_json(resort_id, source_url, started_at)
    if payload is None:
        return [], fetch_log
    return (
        extract_opendatahub_candidates(
            resort_id,
            config,
            payload,
            fetch_log.fetched_at,
            source_url=source_url,
            resort_payload=resort_payload,
        ),
        fetch_log,
    )


def _extract_wikidata(
    *,
    resort_id: str,
    context: SourceRunContext,
    started_at: datetime,
    resort_payload: dict[str, Any],
) -> tuple[list[CandidateFact], FetchLogEntry | None]:
    wikidata_id = context.effective_regional_ids().wikidata_id
    if wikidata_id is None:
        return [], None

    source_url = wikidata_entity_url(wikidata_id)
    payload, fetch_log = _fetch_json_value(
        resort_id,
        source_url,
        started_at,
        extraction_method="wikidata",
    )
    if not isinstance(payload, dict):
        return [], fetch_log

    return (
        extract_wikidata_candidates(
            resort_id=resort_id,
            wikidata_id=wikidata_id,
            payload=payload,
            fetched_at=fetch_log.fetched_at,
            source_url=source_url,
            resort_payload=resort_payload,
        ),
        fetch_log,
    )


def _add_wikidata_discoveries_to_context(
    context: SourceRunContext,
    candidates: list[CandidateFact],
) -> None:
    for candidate in candidates:
        if candidate.validation_status != "accepted":
            continue
        if candidate.field_path == "ski_area_official_url" and isinstance(
            candidate.proposed_value, str
        ):
            context.add_discovered_official_url(
                DiscoveredOfficialUrl(
                    role="ski_area",
                    url=candidate.proposed_value,
                    confidence=candidate.confidence,
                    source="wikidata",
                )
            )
        if candidate.field_path == "regional_data_ids.osm_relation_id" and isinstance(
            candidate.proposed_value, str
        ):
            context.add_discovered_regional_id(
                "osm_relation_id",
                candidate.proposed_value,
            )


def _extract_osm(
    *,
    resort_id: str,
    context: SourceRunContext,
    started_at: datetime,
    resort_payload: dict[str, Any],
) -> tuple[list[CandidateFact], FetchLogEntry | None]:
    osm_relation_id = context.effective_regional_ids().osm_relation_id
    if osm_relation_id is None:
        return [], None
    normalized_osm_relation_id = normalize_osm_relation_id(osm_relation_id)
    if normalized_osm_relation_id is None:
        return [], FetchLogEntry(
            resort_id=resort_id,
            url="osm relation",
            fetched_at=started_at,
            status="skipped",
            extraction_method="osm",
            error=f"Invalid OSM relation ID: {osm_relation_id!r}",
        )

    query = overpass_relation_query(normalized_osm_relation_id)
    source_url = f"{OVERPASS_INTERPRETER_URL}?data={quote(query, safe='')}"
    payload, fetch_log = _fetch_json_value(
        resort_id,
        source_url,
        started_at,
        extraction_method="osm",
    )
    if not isinstance(payload, dict):
        return [], fetch_log

    return (
        extract_osm_relation_candidates(
            resort_id=resort_id,
            osm_relation_id=normalized_osm_relation_id,
            payload=payload,
            fetched_at=fetch_log.fetched_at,
            source_url=source_url,
            resort_payload=resort_payload,
        ),
        fetch_log,
    )


def _extract_dem(
    *,
    resort_id: str,
    started_at: datetime,
    resort_payload: dict[str, Any],
) -> tuple[list[CandidateFact], FetchLogEntry | None]:
    points = catalog_ski_area_points(resort_payload)
    if not points:
        return [], None

    source_url = opentopodata_url(
        dataset_stack=DEFAULT_DEM_DATASET_STACK,
        points=points,
    )
    payload, fetch_log = _fetch_json_value(
        resort_id,
        source_url,
        started_at,
        extraction_method="dem",
    )
    if not isinstance(payload, dict):
        return [], fetch_log

    return (
        extract_dem_sanity_candidates(
            resort_id=resort_id,
            payload=payload,
            fetched_at=fetch_log.fetched_at,
            source_url=source_url,
            resort_payload=resort_payload,
        ),
        fetch_log,
    )


def discover_official_links_for_resort(
    *,
    resort_id: str,
    context: SourceRunContext,
    max_links_per_resort: int = MAX_LINK_CANDIDATES_PER_RESORT,
) -> tuple[list[OfficialLinkCandidate], list[FetchLogEntry]]:
    if max_links_per_resort <= 0:
        return [], []

    candidates: list[OfficialLinkCandidate] = []
    fetch_log: list[FetchLogEntry] = []
    seen_candidate_urls: set[str] = set()
    fetched_page_urls: set[str] = set()
    first_level_pages_remaining = MAX_FIRST_LEVEL_PAGES_PER_RESORT

    for seed_url in context.effective_official_urls_by_role().get("ski_area", []):
        page, page_log = _fetch_official_discovery_page(
            resort_id=resort_id,
            url=seed_url,
            required=True,
        )
        fetch_log.append(page_log)
        fetched_page_urls.add(seed_url)
        if page is None:
            continue

        first_level_candidates = extract_link_candidates_from_html(
            html=page.raw_html,
            source_url=page.final_url,
            official_seed_url=seed_url,
            max_links=max_links_per_resort,
        )
        _extend_official_link_candidates(
            candidates=candidates,
            seen_candidate_urls=seen_candidate_urls,
            link_candidates=first_level_candidates,
            max_links_per_resort=max_links_per_resort,
        )

        sitemap_url = _sitemap_url_for_seed(seed_url)
        if sitemap_url is not None:
            sitemap_page, sitemap_log = _fetch_official_discovery_page(
                resort_id=resort_id,
                url=sitemap_url,
                required=False,
            )
            fetch_log.append(sitemap_log)
            fetched_page_urls.add(sitemap_url)
            if sitemap_page is not None:
                sitemap_candidates = [
                    candidate
                    for url in parse_sitemap_urls(
                        sitemap_page.raw_html,
                        official_seed_url=seed_url,
                    )
                    if (
                        candidate := official_link_candidate_from_url(
                            url=url,
                            source_page_url=sitemap_page.final_url,
                            official_seed_url=seed_url,
                            source_page_title="sitemap.xml",
                        )
                    )
                    is not None
                ]
                first_level_candidates.extend(sitemap_candidates)
                _extend_official_link_candidates(
                    candidates=candidates,
                    seen_candidate_urls=seen_candidate_urls,
                    link_candidates=sitemap_candidates,
                    max_links_per_resort=max_links_per_resort,
                )

        for first_level_url in _selected_first_level_page_urls(
            first_level_candidates,
            fetched_page_urls=fetched_page_urls,
            max_pages=first_level_pages_remaining,
        ):
            if first_level_pages_remaining <= 0:
                break
            first_level_page, first_level_log = _fetch_official_discovery_page(
                resort_id=resort_id,
                url=first_level_url,
                required=False,
            )
            fetch_log.append(first_level_log)
            fetched_page_urls.add(first_level_url)
            first_level_pages_remaining -= 1
            if first_level_page is None:
                continue
            first_level_page_candidates = extract_link_candidates_from_html(
                html=first_level_page.raw_html,
                source_url=first_level_page.final_url,
                official_seed_url=seed_url,
                max_links=max_links_per_resort,
                allow_external_links=False,
            )
            _extend_official_link_candidates(
                candidates=candidates,
                seen_candidate_urls=seen_candidate_urls,
                link_candidates=first_level_page_candidates,
                max_links_per_resort=max_links_per_resort,
            )

    return candidates, fetch_log


def _fetch_official_discovery_page(
    *,
    resort_id: str,
    url: str,
    required: bool,
) -> tuple[FetchedHtmlDocument | None, FetchLogEntry]:
    try:
        page = fetch_html_document(url)
    except (httpx.HTTPError, ValueError) as error:
        response = error.response if isinstance(error, httpx.HTTPStatusError) else None
        return None, FetchLogEntry(
            resort_id=resort_id,
            url=url,
            fetched_at=datetime.now(timezone.utc),
            status="failed" if required else "skipped",
            status_code=response.status_code if response is not None else None,
            extraction_method="official_link_discovery",
            error=str(error),
        )

    return page, FetchLogEntry(
        resort_id=resort_id,
        url=url,
        fetched_at=page.fetched_at,
        status="success",
        status_code=page.status_code,
        content_hash=page.content_hash,
        extraction_method="official_link_discovery",
        truncated=page.truncated,
    )


def _sitemap_url_for_seed(seed_url: str) -> str | None:
    parsed = urlsplit(seed_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, "/sitemap.xml", "", ""))


def _extend_official_link_candidates(
    *,
    candidates: list[OfficialLinkCandidate],
    seen_candidate_urls: set[str],
    link_candidates: list[OfficialLinkCandidate],
    max_links_per_resort: int,
) -> None:
    for candidate in link_candidates:
        if len(candidates) >= max_links_per_resort:
            break
        if candidate.url in seen_candidate_urls:
            continue
        seen_candidate_urls.add(candidate.url)
        candidates.append(candidate)


def _selected_first_level_page_urls(
    link_candidates: list[OfficialLinkCandidate],
    *,
    fetched_page_urls: set[str],
    max_pages: int,
) -> list[str]:
    selected_urls: list[str] = []
    seen_urls: set[str] = set()
    for candidate in sorted(link_candidates, key=_official_link_candidate_sort_key):
        if len(selected_urls) >= max_pages:
            break
        if (
            candidate.is_external
            or candidate.url in fetched_page_urls
            or candidate.url in seen_urls
            or max(candidate.deterministic_scores.values(), default=0.0) <= 0
        ):
            continue
        seen_urls.add(candidate.url)
        selected_urls.append(candidate.url)
    return selected_urls


def _official_link_candidate_sort_key(
    candidate: OfficialLinkCandidate,
) -> tuple[float, float, int, str]:
    role_scores = tuple(candidate.deterministic_scores.values())
    return (
        -max(role_scores, default=0.0),
        -sum(role_scores),
        len(candidate.url),
        candidate.url,
    )


def _official_link_candidates(
    *,
    resort_id: str,
    link_candidates: list[OfficialLinkCandidate],
    fetched_at: datetime,
    extraction_method: ExtractionMethod,
) -> list[CandidateFact]:
    candidates: list[CandidateFact] = []
    for link_candidate in link_candidates:
        for role, score in link_candidate.deterministic_scores.items():
            field_path = OFFICIAL_ROLE_FIELD_PATHS.get(role)  # type: ignore[arg-type]
            if field_path is None or score <= 0:
                continue
            candidates.append(
                CandidateFact(
                    resort_id=resort_id,
                    field_path=field_path,
                    proposed_value=link_candidate.url,
                    source=SourceReference(
                        source_type="official",
                        source_url=link_candidate.source_page_url,
                    ),
                    extraction_method=extraction_method,
                    fetched_at=fetched_at,
                    confidence=min(0.9, score),
                    evidence=(
                        f"link_text={link_candidate.link_text!r}; "
                        f"source_page_url={link_candidate.source_page_url}; "
                        f"deterministic_score={score}"
                    ),
                )
            )
    return candidates


def _classify_official_links(
    *,
    resort_id: str,
    link_candidates: list[OfficialLinkCandidate],
    output_dir: Path,
    llm_client: GeminiClient,
    fetched_at: datetime,
) -> tuple[list[CandidateFact], list[FetchLogEntry]]:
    try:
        classified_links, errors = classify_official_links_with_llm(
            resort_id=resort_id,
            link_candidates=link_candidates,
            llm_client=llm_client,
            cache_dir=output_dir / "link-classifier-cache",
        )
    except Exception as error:  # pragma: no cover - defensive around cache I/O.
        classified_links = {}
        errors = [f"LLM link classification failed: {error}"]

    candidates: list[CandidateFact] = []
    for role, links in classified_links.items():
        field_path = OFFICIAL_ROLE_FIELD_PATHS.get(role)  # type: ignore[arg-type]
        if field_path is None:
            continue
        for link in links:
            candidates.append(
                CandidateFact(
                    resort_id=resort_id,
                    field_path=field_path,
                    proposed_value=link.url,
                    source=SourceReference(source_type="official", source_url=link.url),
                    extraction_method="official_link_llm",
                    fetched_at=fetched_at,
                    confidence=link.confidence,
                    evidence=link.reason,
                )
            )

    fetch_log = [
        FetchLogEntry(
            resort_id=resort_id,
            url="official link classifier",
            fetched_at=fetched_at,
            status="failed",
            extraction_method="official_link_llm",
            error=error,
        )
        for error in errors
    ]
    return candidates, fetch_log


def _add_official_link_discoveries_to_context(
    context: SourceRunContext,
    candidates: list[CandidateFact],
    *,
    source: str,
) -> None:
    field_roles = {
        field_path: role for role, field_path in OFFICIAL_ROLE_FIELD_PATHS.items()
    }
    for candidate in candidates:
        if candidate.validation_status != "accepted":
            continue
        role = field_roles.get(candidate.field_path)
        if role is None or not isinstance(candidate.proposed_value, str):
            continue
        context.add_discovered_official_url(
            DiscoveredOfficialUrl(
                role=role,
                url=candidate.proposed_value,
                confidence=candidate.confidence,
                source=source,
            )
        )


def _extract_official_page_candidates(
    *,
    resort_id: str,
    config: ResortSourceConfig,
    max_pages_per_resort: int,
    output_dir: Path,
    llm_client: GeminiClient,
) -> tuple[list[CandidateFact], list[FetchLogEntry]]:
    candidates: list[CandidateFact] = []
    fetch_log: list[FetchLogEntry] = []
    page_urls = list(config.official_urls.items()) + [
        (f"provider:{name}", url) for name, url in config.provider_urls.items()
    ]

    for page_role, url in page_urls[:max_pages_per_resort]:
        page = fetch_url(url)
        fetch_log.append(
            FetchLogEntry(
                resort_id=resort_id,
                url=page.url,
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

        page_candidates, extraction_errors = extract_official_page_candidates(
            resort_id=resort_id,
            page=page,
            page_role=page_role,
            llm_client=llm_client,
            cache_dir=output_dir / "llm-cache",
        )
        candidates.extend(page_candidates)
        for error in extraction_errors:
            fetch_log.append(
                FetchLogEntry(
                    resort_id=resort_id,
                    url=page.final_url,
                    fetched_at=page.fetched_at,
                    status="failed",
                    status_code=page.status_code,
                    content_hash=page.content_hash,
                    extraction_method="official_page_llm",
                    truncated=page.truncated,
                    error=error,
                )
            )

    return candidates, fetch_log


def _fetch_json(
    resort_id: str,
    url: str,
    started_at: datetime,
) -> tuple[dict[str, Any] | None, FetchLogEntry]:
    payload, fetch_log = _fetch_json_value(
        resort_id,
        url,
        started_at,
        extraction_method="opendatahub",
    )
    if payload is None:
        return None, fetch_log
    if not isinstance(payload, dict):
        return None, fetch_log.model_copy(
            update={
                "status": "failed",
                "content_hash": None,
                "error": "JSON payload is not an object",
            }
        )
    return payload, fetch_log


def _fetch_json_value(
    resort_id: str,
    url: str,
    started_at: datetime,
    *,
    extraction_method: ExtractionMethod,
) -> tuple[Any | None, FetchLogEntry]:
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = get_with_transport_retries(
                client,
                url,
                headers={"User-Agent": _USER_AGENT},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as error:
        response = error.response if isinstance(error, httpx.HTTPStatusError) else None
        return None, FetchLogEntry(
            resort_id=resort_id,
            url=url,
            fetched_at=started_at,
            status="failed",
            status_code=response.status_code if response is not None else None,
            extraction_method=extraction_method,
            error=str(error),
        )

    return payload, FetchLogEntry(
        resort_id=resort_id,
        url=url,
        fetched_at=started_at,
        status="success",
        status_code=response.status_code,
        content_hash=stable_content_hash(json.dumps(payload, sort_keys=True)),
        extraction_method=extraction_method,
    )


if __name__ == "__main__":
    raise SystemExit(main())
