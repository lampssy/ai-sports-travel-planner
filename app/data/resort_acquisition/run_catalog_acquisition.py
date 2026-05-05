from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.ai.gemini_client import GeminiClient
from app.data.loader import DEFAULT_RESORTS_PATH
from app.data.resort_acquisition.discovery import (
    OPENDATAHUB_DISCOVERY_RESORT_ID,
    OPENDATAHUB_SKI_AREA_INDEX_URL,
    discover_opendatahub_id_candidates,
)
from app.data.resort_acquisition.extractors import (
    extract_opendatahub_candidates,
    extract_registry_candidates,
)
from app.data.resort_acquisition.fetching import (
    _USER_AGENT,
    fetch_url,
    get_with_transport_retries,
    stable_content_hash,
)
from app.data.resort_acquisition.llm_extract import extract_official_page_candidates
from app.data.resort_acquisition.models import (
    AcquisitionRunOutput,
    CandidateFact,
    ExtractionMethod,
    FetchLogEntry,
    ResortSourceConfig,
    SourceRegistry,
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

        if llm_client is not None:
            page_candidates, page_fetch_log = _extract_official_page_candidates(
                resort_id=resort_id,
                config=config,
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
