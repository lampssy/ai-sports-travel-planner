from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from app.data.resort_acquisition.fetching import FetchedHtmlDocument
from app.data.resort_acquisition.models import (
    CandidateFact,
    JsonValue,
    ProposalTarget,
    SourceReference,
)
from app.data.resort_acquisition.targeting import (
    proposal_targets_for_single_area_source,
)

BERGFEX_PROVIDER_KEY = "bergfex"
BERGFEX_CONFIDENCE = 0.55
BERGFEX_SOURCE_NAME = "Bergfex public resort page"

_ELEVATION_RANGE_RE = re.compile(
    r"\b(?P<base>\d{1,4}(?:[.,]\d{3})?)\s*[-–]\s*"
    r"(?P<summit>\d{1,4}(?:[.,]\d{3})?)\s*m\b"
)
_SEASON_RANGE_RE = re.compile(
    r"\bSeason:\s*"
    r"(?P<start_day>\d{1,2})\.(?P<start_month>\d{1,2})\."
    r"(?P<start_year>\d{4})\s*[-–]\s*"
    r"(?P<end_day>\d{1,2})\.(?P<end_month>\d{1,2})\."
    r"(?P<end_year>\d{4})\b",
    re.IGNORECASE,
)
_TOTAL_PISTE_KM_RE = re.compile(
    r"(?<!Open )\bPistes?\s+(?P<km>\d+(?:[.,]\d+)?)\s*km\b",
    re.IGNORECASE,
)
_OPEN_LIFTS_TOTAL_RE = re.compile(
    r"\bOpen lifts?\s+(?P<open>\d+)\s*/\s*(?P<total>\d+)\b",
    re.IGNORECASE,
)

_DENIED_EXTERNAL_DOMAIN_PARTS = (
    "bergfex.",
    "apple.com",
    "google.",
    "facebook.",
    "instagram.",
    "youtube.",
    "skiresort.",
    "outdooractive.",
    "schweizmobil.ch",
)


@dataclass(frozen=True)
class _Anchor:
    href: str
    text: str


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_href: str | None = None
        self._current_parts: list[str] = []
        self.anchors: list[_Anchor] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_by_name = {name.lower(): value for name, value in attrs}
        href = attrs_by_name.get("href")
        if href:
            self._current_href = href
            self._current_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current_href is None:
            return
        text = " ".join(part.strip() for part in self._current_parts if part.strip())
        self.anchors.append(_Anchor(href=self._current_href, text=text))
        self._current_href = None
        self._current_parts = []


def extract_bergfex_catalog_candidates(
    *,
    resort_id: str,
    page: FetchedHtmlDocument,
    resort_payload: dict[str, Any],
) -> list[CandidateFact]:
    source = SourceReference(
        source_type="bergfex",
        source_url=page.final_url,
        source_name=BERGFEX_SOURCE_NAME,
    )
    candidates: list[CandidateFact] = []

    official_url = _best_external_official_url(
        html=page.raw_html,
        base_url=page.final_url,
        resort_payload=resort_payload,
    )
    if official_url is not None:
        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                field_path="ski_area_official_url",
                proposed_value=official_url,
                source=source,
                extraction_method="bergfex_public_page",
                fetched_at=page.fetched_at,
                confidence=BERGFEX_CONFIDENCE,
                evidence=f"Bergfex public page external official link={official_url}",
            )
        )

    elevation_range = _extract_elevation_range(page.visible_text)
    if elevation_range is not None:
        base_elevation, summit_elevation, evidence = elevation_range
        _extend_targeted_candidates(
            candidates=candidates,
            resort_id=resort_id,
            resort_payload=resort_payload,
            source=source,
            fetched_at=page.fetched_at,
            field_path="base_elevation_m",
            proposed_value=base_elevation,
            evidence=evidence,
        )
        _extend_targeted_candidates(
            candidates=candidates,
            resort_id=resort_id,
            resort_payload=resort_payload,
            source=source,
            fetched_at=page.fetched_at,
            field_path="summit_elevation_m",
            proposed_value=summit_elevation,
            evidence=evidence,
        )

    season_range = _extract_season_months(page.visible_text)
    if season_range is not None:
        start_month, end_month, season_window, evidence = season_range
        _extend_targeted_candidates(
            candidates=candidates,
            resort_id=resort_id,
            resort_payload=resort_payload,
            source=source,
            fetched_at=page.fetched_at,
            field_path="season_start_month",
            proposed_value=start_month,
            evidence=evidence,
        )
        _extend_targeted_candidates(
            candidates=candidates,
            resort_id=resort_id,
            resort_payload=resort_payload,
            source=source,
            fetched_at=page.fetched_at,
            field_path="season_end_month",
            proposed_value=end_month,
            evidence=evidence,
        )
        _extend_targeted_candidates(
            candidates=candidates,
            resort_id=resort_id,
            resort_payload=resort_payload,
            source=source,
            fetched_at=page.fetched_at,
            field_path="season_windows",
            proposed_value=season_window,
            evidence=evidence,
        )

    total_piste_km = _extract_total_piste_km(page.visible_text)
    if total_piste_km is not None:
        value, evidence = total_piste_km
        _extend_targeted_candidates(
            candidates=candidates,
            resort_id=resort_id,
            resort_payload=resort_payload,
            source=source,
            fetched_at=page.fetched_at,
            field_path="total_piste_km",
            proposed_value=value,
            evidence=evidence,
        )

    total_lift_count = _extract_total_lift_count(page.visible_text)
    if total_lift_count is not None:
        value, evidence = total_lift_count
        _extend_targeted_candidates(
            candidates=candidates,
            resort_id=resort_id,
            resort_payload=resort_payload,
            source=source,
            fetched_at=page.fetched_at,
            field_path="total_lift_count",
            proposed_value=value,
            evidence=evidence,
        )

    return candidates


def filter_bergfex_fallback_candidates(
    *,
    candidates: list[CandidateFact],
    prior_candidates: list[CandidateFact],
    resort_payload: dict[str, Any],
) -> list[CandidateFact]:
    filtered: list[CandidateFact] = []
    prior_values_by_key: dict[tuple[str, str, str, str], set[str]] = {}

    for candidate in prior_candidates:
        if (
            candidate.validation_status != "accepted"
            or candidate.extraction_method == "bergfex_public_page"
        ):
            continue
        key = _fallback_key(candidate)
        prior_values_by_key.setdefault(key, set()).add(
            json.dumps(candidate.proposed_value, sort_keys=True, allow_nan=False)
        )

    for candidate in candidates:
        key = _fallback_key(candidate)
        prior_values = prior_values_by_key.get(key, set())
        current_value = _current_value(
            resort_payload=resort_payload,
            target=candidate.target,
            field_path=candidate.field_path,
        )
        current_value_key = (
            json.dumps(current_value, sort_keys=True, allow_nan=False)
            if current_value is not None
            else None
        )

        if current_value is None or not prior_values or len(prior_values) > 1:
            filtered.append(candidate)
            continue
        if current_value_key not in prior_values:
            filtered.append(candidate)

    return filtered


def _extend_targeted_candidates(
    *,
    candidates: list[CandidateFact],
    resort_id: str,
    resort_payload: dict[str, Any],
    source: SourceReference,
    fetched_at: datetime,
    field_path: str,
    proposed_value: JsonValue,
    evidence: str,
) -> None:
    targets = proposal_targets_for_single_area_source(
        resort_id=resort_id,
        resort_payload=resort_payload,
        field_path=field_path,
        primary_entity_type="ski_area",
    )
    for target in targets:
        candidates.append(
            _candidate(
                resort_id=resort_id,
                target=target,
                field_path=field_path,
                proposed_value=proposed_value,
                source=source,
                fetched_at=fetched_at,
                evidence=evidence,
            )
        )


def _candidate(
    *,
    resort_id: str,
    target: ProposalTarget,
    field_path: str,
    proposed_value: JsonValue,
    source: SourceReference,
    fetched_at: datetime,
    evidence: str,
) -> CandidateFact:
    return CandidateFact(
        resort_id=resort_id,
        target=target,
        field_path=field_path,
        proposed_value=proposed_value,
        source=source,
        extraction_method="bergfex_public_page",
        fetched_at=fetched_at,
        confidence=BERGFEX_CONFIDENCE,
        evidence=evidence,
    )


def _fallback_key(candidate: CandidateFact) -> tuple[str, str, str, str]:
    return (
        candidate.resort_id,
        candidate.target.entity_type,
        candidate.target.entity_id,
        candidate.field_path,
    )


def _current_value(
    *,
    resort_payload: dict[str, Any],
    target: ProposalTarget,
    field_path: str,
) -> JsonValue:
    if target.entity_type == "destination":
        return _field_path_value(resort_payload, field_path)

    ski_area = _ski_area_payload(resort_payload, target.entity_id)
    if ski_area is None:
        return None
    return _field_path_value(ski_area, field_path)


def _field_path_value(payload: dict[str, Any], field_path: str) -> JsonValue:
    current: Any = payload
    for segment in field_path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _ski_area_payload(
    resort_payload: dict[str, Any],
    ski_area_id: str,
) -> dict[str, Any] | None:
    ski_areas = resort_payload.get("ski_areas")
    if not isinstance(ski_areas, list):
        return None
    for ski_area in ski_areas:
        if isinstance(ski_area, dict) and ski_area.get("ski_area_id") == ski_area_id:
            return ski_area
    return None


def _best_external_official_url(
    *,
    html: str,
    base_url: str,
    resort_payload: dict[str, Any],
) -> str | None:
    parser = _AnchorParser()
    parser.feed(html)
    parser.close()

    scored_urls: list[tuple[float, str]] = []
    resort_tokens = _resort_tokens(resort_payload)
    for anchor in parser.anchors:
        url = _normalized_http_url(anchor.href, base_url)
        if url is None:
            continue
        host = urlsplit(url).netloc.lower()
        if _is_denied_external_host(host):
            continue

        score = _external_url_score(url, anchor.text, resort_tokens)
        if score >= 0.4:
            scored_urls.append((-score, url))

    if not scored_urls:
        return None
    return sorted(scored_urls)[0][1]


def _normalized_http_url(href: str, base_url: str) -> str | None:
    absolute_url = urljoin(base_url, href.strip())
    parsed = urlsplit(absolute_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, "")
    )


def _is_denied_external_host(host: str) -> bool:
    host = host.removeprefix("www.")
    return any(part in host for part in _DENIED_EXTERNAL_DOMAIN_PARTS)


def _external_url_score(url: str, text: str, resort_tokens: set[str]) -> float:
    parsed = urlsplit(url)
    host_tokens = _tokens(parsed.netloc)
    text_lower = text.lower()
    score = 0.0
    if "www." in text_lower or text_lower.startswith(("http://", "https://")):
        score += 0.4
    if any(word in text_lower for word in ("official", "website", "homepage")):
        score += 0.3
    if resort_tokens and host_tokens.intersection(resort_tokens):
        score += 0.3
    return score


def _resort_tokens(resort_payload: dict[str, Any]) -> set[str]:
    raw_names: list[str] = []
    name = resort_payload.get("name")
    if isinstance(name, str):
        raw_names.append(name)
    ski_areas = resort_payload.get("ski_areas")
    if isinstance(ski_areas, list):
        for ski_area in ski_areas:
            if isinstance(ski_area, dict) and isinstance(ski_area.get("name"), str):
                raw_names.append(ski_area["name"])
    tokens: set[str] = set()
    for raw_name in raw_names:
        tokens.update(_tokens(raw_name))
    return tokens


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.split(r"[^a-z0-9]+", value.lower()) if len(token) >= 4
    }


def _extract_elevation_range(text: str) -> tuple[int, int, str] | None:
    for match in _ELEVATION_RANGE_RE.finditer(text):
        base = _parse_elevation_int(match.group("base"))
        summit = _parse_elevation_int(match.group("summit"))
        if base is None or summit is None:
            continue
        if 300 <= base < summit <= 5000:
            return (
                base,
                summit,
                f"Bergfex public page elevation range '{match.group(0)}'",
            )
    return None


def _extract_season_months(text: str) -> tuple[int, int, dict[str, str], str] | None:
    match = _SEASON_RANGE_RE.search(text)
    if match is None:
        return None
    try:
        start_date = date(
            int(match.group("start_year")),
            int(match.group("start_month")),
            int(match.group("start_day")),
        )
        end_date = date(
            int(match.group("end_year")),
            int(match.group("end_month")),
            int(match.group("end_day")),
        )
    except ValueError:
        return None
    if end_date < start_date:
        return None
    season_label = (
        str(start_date.year)
        if start_date.year == end_date.year
        else f"{start_date.year}-{end_date.year}"
    )
    season_window = {
        "season_label": season_label,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "status": "planned",
    }
    return (
        start_date.month,
        end_date.month,
        season_window,
        f"Bergfex public page season range '{match.group(0)}'",
    )


def _extract_total_piste_km(text: str) -> tuple[int | float, str] | None:
    match = _TOTAL_PISTE_KM_RE.search(text)
    if match is None:
        return None
    value = _parse_positive_float(match.group("km"))
    if value is None:
        return None
    normalized_value: int | float = int(value) if value.is_integer() else value
    return (
        normalized_value,
        f"Bergfex public page total piste summary '{match.group(0)}'",
    )


def _extract_total_lift_count(text: str) -> tuple[int, str] | None:
    match = _OPEN_LIFTS_TOTAL_RE.search(text)
    if match is None:
        return None
    total = int(match.group("total"))
    return (
        total,
        "Bergfex public page open-lifts summary "
        f"'{match.group(0)}'; extracting total_lift_count only",
    )


def _parse_elevation_int(value: str) -> int | None:
    normalized = value.replace(".", "").replace(",", "")
    try:
        parsed = int(normalized)
    except ValueError:
        return None
    return parsed


def _parse_positive_float(value: str) -> float | None:
    try:
        parsed = float(value.replace(",", "."))
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed
