from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

OFFICIAL_LINK_ROLES = (
    "ski_pass",
    "season_dates",
    "trail_map",
    "official_status",
    "rental",
)
MAX_LINK_CANDIDATES_PER_RESORT = 100
MAX_SITEMAP_URLS_PER_RESORT = 40
MAX_FIRST_LEVEL_PAGES_PER_RESORT = 20

_IGNORED_HREF_SCHEMES = ("mailto:", "tel:", "javascript:")
_WHITESPACE_RE = re.compile(r"\s+")
_ROLE_KEYWORDS = {
    "ski_pass": (
        "skipass",
        "ski pass",
        "ticket",
        "prices",
        "tariff",
        "tariffe",
        "preise",
        "forfait",
    ),
    "season_dates": (
        "opening",
        "season",
        "winter",
        "operating",
        "öffnungszeiten",
        "ouverture",
        "apertura",
    ),
    "trail_map": (
        "map",
        "piste map",
        "skimaps",
        "panorama",
        "pistenplan",
        "plan des pistes",
    ),
    "official_status": (
        "snow report",
        "lifts",
        "slopes",
        "open",
        "live",
        "impianti",
        "remontées",
    ),
    "rental": (
        "rental",
        "hire",
        "equipment",
        "noleggio",
        "verleih",
        "location ski",
    ),
}


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


@dataclass(frozen=True)
class _ParsedAnchor:
    href: str
    link_text: str
    title: str | None
    aria_label: str | None


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[_ParsedAnchor] = []
        self.page_title: str | None = None
        self._title_parts: list[str] = []
        self._in_title = False
        self._active_anchor: dict[str, str | None] | None = None
        self._active_anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value for name, value in attrs}
        if tag.lower() == "title":
            self._in_title = True
            return
        if tag.lower() != "a" or self._active_anchor is not None:
            return
        href = attr_map.get("href")
        if href is None:
            return
        self._active_anchor = {
            "href": href,
            "title": attr_map.get("title"),
            "aria_label": attr_map.get("aria-label"),
        }
        self._active_anchor_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
            title = _normalize_text(" ".join(self._title_parts))
            self.page_title = title or None
            return
        if tag.lower() != "a" or self._active_anchor is None:
            return
        self.anchors.append(
            _ParsedAnchor(
                href=self._active_anchor["href"] or "",
                link_text=_normalize_text(" ".join(self._active_anchor_text)),
                title=_normalize_optional_text(self._active_anchor["title"]),
                aria_label=_normalize_optional_text(self._active_anchor["aria_label"]),
            )
        )
        self._active_anchor = None
        self._active_anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if self._active_anchor is not None:
            self._active_anchor_text.append(data)


def extract_link_candidates_from_html(
    *,
    html: str,
    source_url: str,
    official_seed_url: str,
    max_links: int = MAX_LINK_CANDIDATES_PER_RESORT,
) -> list[OfficialLinkCandidate]:
    if max_links <= 0:
        return []

    parser = _AnchorParser()
    parser.feed(html)
    parser.close()

    source_is_official = _is_allowed_official_url(source_url, official_seed_url)
    seen_urls: set[str] = set()
    candidates: list[OfficialLinkCandidate] = []
    for anchor in parser.anchors:
        normalized_url = _normalize_link_url(anchor.href, source_url)
        if normalized_url is None or normalized_url in seen_urls:
            continue
        is_external = _comparison_host(normalized_url) != _comparison_seed_host(
            official_seed_url
        )
        nearby_text = _nearby_text(
            anchor.link_text,
            anchor.title,
            anchor.aria_label,
            parser.page_title,
        )
        deterministic_scores = _score_roles(
            normalized_url,
            anchor.link_text,
            anchor.title,
            anchor.aria_label,
            nearby_text,
        )
        is_official_safe = _is_allowed_official_url(normalized_url, official_seed_url)
        if not is_official_safe:
            if not source_is_official:
                continue
            if not _has_positive_role_score(deterministic_scores):
                continue
            is_external = True

        seen_urls.add(normalized_url)
        candidates.append(
            OfficialLinkCandidate(
                url=normalized_url,
                source_page_url=source_url,
                official_seed_url=official_seed_url,
                link_text=anchor.link_text,
                title=anchor.title,
                aria_label=anchor.aria_label,
                nearby_text=nearby_text,
                source_page_title=parser.page_title,
                is_external=is_external,
                deterministic_scores=deterministic_scores,
            )
        )
        if len(candidates) >= max_links:
            break

    return candidates


def parse_sitemap_urls(
    xml: str,
    *,
    official_seed_url: str,
    max_urls: int = MAX_SITEMAP_URLS_PER_RESORT,
) -> list[str]:
    if max_urls <= 0:
        return []

    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    urls: list[str] = []
    seen_urls: set[str] = set()
    for element in root.iter():
        if _local_name(element.tag) != "loc" or element.text is None:
            continue
        normalized_url = _normalize_absolute_url(element.text)
        if (
            normalized_url is None
            or normalized_url in seen_urls
            or not _is_allowed_official_url(normalized_url, official_seed_url)
        ):
            continue
        seen_urls.add(normalized_url)
        urls.append(normalized_url)
        if len(urls) >= max_urls:
            break

    return urls


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _normalize_optional_text(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = _normalize_text(text)
    return normalized or None


def _normalize_link_url(href: str, source_url: str) -> str | None:
    href = href.strip()
    if not href or href.startswith("#"):
        return None
    if href.lower().startswith(_IGNORED_HREF_SCHEMES):
        return None
    return _normalize_absolute_url(urljoin(source_url, href))


def _normalize_absolute_url(url: str) -> str | None:
    url = url.strip()
    if not url:
        return None
    parsed = urlparse(urldefrag(url).url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed.geturl()


def _host(url: str) -> str | None:
    hostname = urlparse(url).hostname
    return hostname.lower() if hostname else None


def _comparison_seed_host(official_seed_url: str) -> str | None:
    return _comparison_host(official_seed_url)


def _comparison_host(url: str) -> str | None:
    host = _host(url)
    if host is None:
        return None
    return host.removeprefix("www.")


def _is_allowed_official_url(url: str, official_seed_url: str) -> bool:
    candidate_host = _host(url)
    seed_host = _comparison_seed_host(official_seed_url)
    if candidate_host is None or seed_host is None:
        return False
    candidate_host = candidate_host.removeprefix("www.")
    if candidate_host == seed_host:
        return True
    candidate_labels = candidate_host.split(".")
    seed_labels = seed_host.split(".")
    return (
        len(candidate_labels) == len(seed_labels) + 1
        and candidate_labels[1:] == seed_labels
    )


def _nearby_text(*parts: str | None) -> str:
    return _normalize_text(" ".join(part for part in parts if part))[:240]


def _score_roles(*parts: str | None) -> dict[str, float]:
    combined_text = " ".join(part for part in parts if part).lower()
    scores: dict[str, float] = {}
    for role in OFFICIAL_LINK_ROLES:
        hits = sum(1 for keyword in _ROLE_KEYWORDS[role] if keyword in combined_text)
        scores[role] = min(1.0, hits * 0.2)
    return scores


def _has_positive_role_score(scores: dict[str, float]) -> bool:
    return any(score > 0 for score in scores.values())


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]
