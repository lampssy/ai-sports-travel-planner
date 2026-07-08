from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Set
from datetime import date
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.data.catalog_curation_backlog import markdown_heading_anchor
from app.domain.catalog import CatalogSnapshot
from app.domain.source_urls import validate_direct_external_http_url
from ops.maintainer.models import MaintainerState
from ops.maintainer.publication import parse_machine_state

CandidateKind = Literal[
    "stay_destination",
    "stay_base",
    "ski_area",
    "ski_area_access",
    "terrain_domain",
    "lift_pass_product",
]
AlpineSubregion = Literal[
    "French Alps",
    "Swiss Alps",
    "Austrian Alps",
    "Italian Alps",
    "German Alps",
    "Slovenian Alps",
]
CandidateOrigin = Literal["backlog", "registry"]
ProposalLifecycle = Literal["OPEN", "CLOSED", "MERGED"]

DISCOVERY_SUBREGIONS: tuple[AlpineSubregion, ...] = (
    "French Alps",
    "Swiss Alps",
    "Austrian Alps",
    "Italian Alps",
    "German Alps",
    "Slovenian Alps",
)

_CANDIDATE_KINDS: tuple[str, ...] = (
    "stay_destination",
    "stay_base",
    "ski_area",
    "ski_area_access",
    "terrain_domain",
    "lift_pass_product",
)
_KIND_PATTERN = "(?:" + "|".join(_CANDIDATE_KINDS) + ")"
_ENTITY_ID_PATTERN = r"[a-z0-9]+(?:-+[a-z0-9]+)*"
_ENTITY_ID = re.compile(rf"^{_ENTITY_ID_PATTERN}$")
_CANDIDATE_KEY = re.compile(rf"^(?P<kind>{_KIND_PATTERN}):{_ENTITY_ID_PATTERN}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_SINGLE_BACKTICK_CODE = re.compile(r"(?<!`)`([^`\r\n]+)`(?!`)")
_TYPED_MARKER_SIGNAL = re.compile(rf"{_KIND_PATTERN}:[^\s`]*")
_SECTION_HEADING = "## Catalog Curation Refinements"
_MACHINE_MARKER_SIGNAL = "snowcast-maintainer-state:"

_CATALOG_KEY_FIELDS: tuple[tuple[str, str, CandidateKind], ...] = (
    ("stay_destinations", "stay_destination_id", "stay_destination"),
    ("stay_bases", "stay_base_id", "stay_base"),
    ("ski_areas", "ski_area_id", "ski_area"),
    ("ski_area_access", "ski_area_access_id", "ski_area_access"),
    ("terrain_domains", "terrain_domain_id", "terrain_domain"),
    ("lift_pass_products", "lift_pass_product_id", "lift_pass_product"),
)
assert tuple(kind for _, _, kind in _CATALOG_KEY_FIELDS) == _CANDIDATE_KINDS


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_urls(urls: Iterable[str], *, require_nonempty: bool) -> tuple[str, ...]:
    normalized = tuple(sorted(validate_direct_external_http_url(url) for url in urls))
    if require_nonempty and not normalized:
        raise ValueError("proposal candidate requires an official identity URL")
    if len(normalized) != len(set(normalized)):
        raise ValueError("official URLs must be unique")
    return normalized


def _proposal_fingerprint(
    *,
    key: str,
    regional_graph_key: str,
    origin_fingerprint: str,
    official_urls: tuple[str, ...],
) -> str:
    if not official_urls:
        return origin_fingerprint
    return _fingerprint(
        {
            "key": key,
            "official_urls": official_urls,
            "origin_fingerprint": origin_fingerprint,
            "regional_graph_key": regional_graph_key,
        }
    )


class CoverageCandidate(_StrictFrozenModel):
    candidate_key: str = Field(
        pattern=rf"^{_KIND_PATTERN}:{_ENTITY_ID_PATTERN}$",
    )
    display_name: str = Field(min_length=1)
    country: str = Field(min_length=1)
    alpine_subregion: AlpineSubregion
    regional_graph_key: str = Field(pattern=rf"^{_ENTITY_ID_PATTERN}$")
    candidate_kind: CandidateKind
    official_urls: tuple[str, ...] = Field(min_length=1)

    @field_validator("official_urls", mode="before")
    @classmethod
    def accept_json_url_array(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("display_name", "country")
    @classmethod
    def reject_blank_or_padded_text(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("text must be non-blank and unpadded")
        return value

    @model_validator(mode="after")
    def validate_key_kind_and_urls(self) -> Self:
        prefix, _ = self.candidate_key.split(":", 1)
        if prefix != self.candidate_kind:
            raise ValueError("candidate key prefix must match candidate kind")
        normalized = _validate_urls(self.official_urls, require_nonempty=True)
        object.__setattr__(self, "official_urls", normalized)
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class CoverageRegistry(_StrictFrozenModel):
    schema_version: Literal[1]
    entries: tuple[CoverageCandidate, ...]

    @field_validator("entries", mode="before")
    @classmethod
    def accept_json_entry_array(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def validate_unique_candidates(self) -> Self:
        keys = [entry.candidate_key for entry in self.entries]
        if len(keys) != len(set(keys)):
            raise ValueError("candidate keys must be unique")
        return self


class DiscoveryCandidate(_StrictFrozenModel):
    key: str = Field(pattern=rf"^{_KIND_PATTERN}:{_ENTITY_ID_PATTERN}$")
    display_name: str = Field(min_length=1)
    candidate_kind: CandidateKind
    country: str | None = Field(default=None, min_length=1)
    alpine_subregion: AlpineSubregion | None = None
    regional_graph_key: str = Field(pattern=rf"^{_ENTITY_ID_PATTERN}$")
    official_urls: tuple[str, ...]
    origin: CandidateOrigin
    backlog_ref: str | None
    backlog_marker: str | None
    origin_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("official_urls", mode="before")
    @classmethod
    def accept_json_url_array(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("display_name", "country")
    @classmethod
    def reject_blank_or_padded_text(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError("text must be non-blank and unpadded")
        return value

    @model_validator(mode="after")
    def validate_candidate_contract(self) -> Self:
        prefix, _ = self.key.split(":", 1)
        if prefix != self.candidate_kind:
            raise ValueError("candidate key prefix must match candidate kind")
        normalized_urls = _validate_urls(self.official_urls, require_nonempty=False)
        object.__setattr__(self, "official_urls", normalized_urls)

        if self.origin == "backlog":
            expected_ref = f"docs/product-backlog.md#{self.regional_graph_key}"
            if (
                self.backlog_ref != expected_ref
                or self.backlog_marker != f"`{self.key}`"
            ):
                raise ValueError("backlog candidate requires its exact origin metadata")
        elif self.backlog_ref is not None or self.backlog_marker is not None:
            raise ValueError("registry candidate must not carry backlog metadata")

        if self.origin == "registry" and (
            self.country is None or self.alpine_subregion is None or not normalized_urls
        ):
            raise ValueError("registry candidate requires geography and official URLs")

        expected_fingerprint = (
            self.origin_fingerprint
            if self.origin == "registry"
            else _proposal_fingerprint(
                key=self.key,
                regional_graph_key=self.regional_graph_key,
                origin_fingerprint=self.origin_fingerprint,
                official_urls=normalized_urls,
            )
        )
        if self.fingerprint != expected_fingerprint:
            raise ValueError("candidate fingerprint does not match canonical content")
        return self


class ProposalRecord(_StrictFrozenModel):
    lifecycle_state: ProposalLifecycle
    is_proposal: bool
    candidate_key: str | None = Field(
        default=None,
        pattern=rf"^{_KIND_PATTERN}:{_ENTITY_ID_PATTERN}$",
    )
    origin_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    regional_graph_key: str | None = Field(
        default=None,
        pattern=rf"^{_ENTITY_ID_PATTERN}$",
    )

    @model_validator(mode="after")
    def validate_candidate_metadata(self) -> Self:
        metadata = (
            self.candidate_key,
            self.origin_fingerprint,
            self.fingerprint,
            self.regional_graph_key,
        )
        if any(value is not None for value in metadata) and not all(
            value is not None for value in metadata
        ):
            raise ValueError("candidate metadata must be complete")
        if self.is_proposal and self.candidate_key is None:
            raise ValueError("proposal candidate metadata must be complete")
        return self


def with_official_urls(
    candidate: DiscoveryCandidate,
    official_urls: tuple[str, ...],
) -> DiscoveryCandidate:
    candidate = DiscoveryCandidate.model_validate(candidate, strict=True)
    validated = _validate_urls(official_urls, require_nonempty=True)
    if candidate.origin == "registry":
        if validated != candidate.official_urls:
            raise ValueError("registry official URLs are immutable")
        return candidate
    payload = candidate.model_dump(mode="python")
    payload.update(
        {
            "official_urls": validated,
            "fingerprint": _proposal_fingerprint(
                key=candidate.key,
                regional_graph_key=candidate.regional_graph_key,
                origin_fingerprint=candidate.origin_fingerprint,
                official_urls=validated,
            ),
        }
    )
    return DiscoveryCandidate.model_validate(payload, strict=True)


def require_publication_ready(candidate: DiscoveryCandidate) -> DiscoveryCandidate:
    candidate = DiscoveryCandidate.model_validate(candidate, strict=True)
    if not candidate.official_urls:
        raise ValueError("proposal candidate requires an official identity URL")
    return candidate


def discovery_subregion(scan_date: date) -> str:
    if type(scan_date) is not date:
        raise TypeError("scan_date must be a date")
    iso = scan_date.isocalendar()
    return DISCOVERY_SUBREGIONS[(iso.week + iso.weekday) % len(DISCOVERY_SUBREGIONS)]


def parse_catalog_backlog(markdown: str) -> list[DiscoveryCandidate]:
    if not isinstance(markdown, str):
        raise TypeError("backlog markdown must be text")
    lines = markdown.splitlines()
    section_indexes = [
        index for index, line in enumerate(lines) if line == _SECTION_HEADING
    ]
    if len(section_indexes) != 1:
        raise ValueError(
            "backlog must contain exactly one Catalog Curation Refinements section"
        )

    section_start = section_indexes[0] + 1
    section_end = next(
        (
            index
            for index in range(section_start, len(lines))
            if lines[index].startswith("## ") and not lines[index].startswith("### ")
        ),
        len(lines),
    )
    items: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_body: list[str] = []
    anchors: set[str] = set()
    for line in lines[section_start:section_end]:
        if line.startswith("### "):
            if current_title is not None:
                items.append((current_title, current_body))
            current_title = line.removeprefix("### ").strip()
            if not current_title:
                raise ValueError("backlog item heading must not be blank")
            anchor = markdown_heading_anchor(current_title)
            if not anchor or _ENTITY_ID.fullmatch(anchor) is None:
                raise ValueError("backlog item heading has an invalid canonical anchor")
            if anchor in anchors:
                raise ValueError("backlog item anchors must be unique")
            anchors.add(anchor)
            current_body = []
            continue
        if current_title is not None:
            current_body.append(line)
    if current_title is not None:
        items.append((current_title, current_body))

    candidates: list[DiscoveryCandidate] = []
    seen_keys: set[str] = set()
    for title, body_lines in items:
        graph_key = markdown_heading_anchor(title)
        body = "\n".join(body_lines).strip()
        code_spans = list(_SINGLE_BACKTICK_CODE.finditer(body))
        body_without_code = _SINGLE_BACKTICK_CODE.sub("", body)
        if _TYPED_MARKER_SIGNAL.search(body_without_code):
            raise ValueError(
                "catalog candidate markers must be enclosed in single backticks"
            )

        for span in code_spans:
            marker = span.group(1)
            if not re.match(rf"^{_KIND_PATTERN}:", marker):
                continue
            match = _CANDIDATE_KEY.fullmatch(marker)
            if match is None:
                raise ValueError("malformed catalog candidate marker")
            if marker in seen_keys:
                raise ValueError("backlog candidate markers must be unique")
            seen_keys.add(marker)
            kind = match.group("kind")
            identifier = marker.split(":", 1)[1]
            backlog_ref = f"docs/product-backlog.md#{graph_key}"
            origin_fingerprint = _fingerprint(
                {
                    "backlog_ref": backlog_ref,
                    "body": body,
                    "key": marker,
                }
            )
            candidates.append(
                DiscoveryCandidate(
                    key=marker,
                    display_name=identifier.replace("-", " ").title(),
                    candidate_kind=kind,
                    country=None,
                    alpine_subregion=None,
                    regional_graph_key=graph_key,
                    official_urls=(),
                    origin="backlog",
                    backlog_ref=backlog_ref,
                    backlog_marker=f"`{marker}`",
                    origin_fingerprint=origin_fingerprint,
                    fingerprint=origin_fingerprint,
                )
            )
    return candidates


def catalog_entity_keys(catalog_path: Path) -> set[str]:
    try:
        raw_catalog = catalog_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"cannot read catalog: {error}") from error
    try:
        payload = json.loads(
            raw_catalog,
            object_pairs_hook=_strict_json_object,
            parse_constant=_reject_json_constant,
        )
        _validate_raw_catalog_identity(payload)
        snapshot = CatalogSnapshot.model_validate(payload)
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        raise ValueError(f"catalog is invalid: {error}") from error

    keys: set[str] = set()
    for section, id_field, kind in _CATALOG_KEY_FIELDS:
        for entity in getattr(snapshot, section):
            entity_id = getattr(entity, id_field)
            key = f"{kind}:{entity_id}"
            if _CANDIDATE_KEY.fullmatch(key) is None:
                raise ValueError(
                    f"catalog contains malformed catalog entity key: {key}"
                )
            keys.add(key)
    return keys


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON constant: {value}")


def _validate_raw_catalog_identity(payload: object) -> None:
    if not isinstance(payload, dict):
        raise ValueError("catalog root must be a JSON object")
    expected_sections = set(CatalogSnapshot.model_fields)
    actual_sections = set(payload)
    if actual_sections != expected_sections:
        missing = sorted(expected_sections - actual_sections)
        unknown = sorted(actual_sections - expected_sections)
        raise ValueError(
            f"catalog sections must match schema (missing={missing}, unknown={unknown})"
        )
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 2:
        raise ValueError("catalog schema_version must be integer 2")

    id_fields = {
        "ski_regions": "ski_region_id",
        **{section: id_field for section, id_field, _ in _CATALOG_KEY_FIELDS},
        "rental_display_facts": "rental_display_fact_id",
    }
    for section, id_field in id_fields.items():
        rows = payload[section]
        if not isinstance(rows, list):
            raise ValueError(f"catalog section {section} must be a JSON array")
        seen: set[str] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"{section}[{index}] must be a JSON object")
            entity_id = row.get(id_field)
            if (
                not isinstance(entity_id, str)
                or _ENTITY_ID.fullmatch(entity_id) is None
            ):
                raise ValueError(
                    f"{section}[{index}].{id_field} must be a canonical entity ID"
                )
            if entity_id in seen:
                raise ValueError(f"duplicate {id_field}: {entity_id}")
            seen.add(entity_id)


def _registry_candidates(registry: CoverageRegistry) -> list[DiscoveryCandidate]:
    candidates: list[DiscoveryCandidate] = []
    for entry in registry.entries:
        origin_fingerprint = entry.fingerprint
        candidates.append(
            DiscoveryCandidate(
                key=entry.candidate_key,
                display_name=entry.display_name,
                candidate_kind=entry.candidate_kind,
                country=entry.country,
                alpine_subregion=entry.alpine_subregion,
                regional_graph_key=entry.regional_graph_key,
                official_urls=entry.official_urls,
                origin="registry",
                backlog_ref=None,
                backlog_marker=None,
                origin_fingerprint=origin_fingerprint,
                fingerprint=origin_fingerprint,
            )
        )
    return candidates


def select_discovery_candidate(
    backlog: list[DiscoveryCandidate],
    registry: CoverageRegistry,
    catalog_keys: set[str],
    open_proposals: list[ProposalRecord],
    declined_fingerprints: set[tuple[str, str]],
) -> DiscoveryCandidate | None:
    validated_backlog = [
        DiscoveryCandidate.model_validate(candidate, strict=True)
        for candidate in backlog
    ]
    registry = CoverageRegistry.model_validate(registry, strict=True)
    validated_catalog_keys = _validated_catalog_key_set(catalog_keys, "catalog")
    records = [
        ProposalRecord.model_validate(record, strict=True) for record in open_proposals
    ]
    declined = _validated_declined_fingerprints(declined_fingerprints)

    active_records = [record for record in records if record.lifecycle_state == "OPEN"]
    if sum(record.is_proposal for record in active_records) >= 3:
        return None

    open_keys = {
        record.candidate_key
        for record in active_records
        if record.candidate_key is not None
    }
    open_graphs = {
        record.regional_graph_key
        for record in active_records
        if record.regional_graph_key is not None
    }
    considered_keys: set[str] = set()
    for candidate in [*validated_backlog, *_registry_candidates(registry)]:
        if candidate.key in considered_keys:
            continue
        considered_keys.add(candidate.key)
        if candidate.key in validated_catalog_keys or candidate.key in open_keys:
            continue
        if candidate.regional_graph_key in open_graphs:
            continue
        if (candidate.key, candidate.origin_fingerprint) in declined:
            continue
        return candidate
    return None


def _validated_declined_fingerprints(
    values: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    if not isinstance(values, (set, frozenset)):
        raise TypeError("declined fingerprints must be a set")
    validated: set[tuple[str, str]] = set()
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValueError(
                "declined fingerprint entries must be key/fingerprint pairs"
            )
        key, fingerprint = item
        if (
            not isinstance(key, str)
            or _CANDIDATE_KEY.fullmatch(key) is None
            or not isinstance(fingerprint, str)
            or _HASH.fullmatch(fingerprint) is None
        ):
            raise ValueError("declined fingerprint entry is malformed")
        validated.add((key, fingerprint))
    return validated


def _validated_catalog_key_set(values: Set[str], description: str) -> set[str]:
    if not isinstance(values, (set, frozenset)):
        raise TypeError(f"{description} keys must be a set")
    validated: set[str] = set()
    for key in values:
        if not isinstance(key, str) or _CANDIDATE_KEY.fullmatch(key) is None:
            raise ValueError(f"malformed catalog entity key in {description}: {key!r}")
        validated.add(key)
    return validated


def verify_origin_cleanup(
    candidate: DiscoveryCandidate,
    base_catalog_keys: set[str],
    proposed_catalog_keys: set[str],
    proposed_backlog: str,
) -> None:
    candidate = DiscoveryCandidate.model_validate(candidate, strict=True)
    base_keys = _validated_catalog_key_set(base_catalog_keys, "base catalog")
    proposed_keys = _validated_catalog_key_set(
        proposed_catalog_keys, "proposed catalog"
    )

    if candidate.key in base_keys:
        raise ValueError("proposal candidate already exists in base catalog")
    if not base_keys.issubset(proposed_keys):
        raise ValueError("proposal must not remove existing catalog keys")
    if candidate.key not in proposed_keys:
        raise ValueError("proposal does not add its candidate key")

    proposed_candidates = parse_catalog_backlog(proposed_backlog)
    if candidate.origin == "backlog" and any(
        remaining.key == candidate.key for remaining in proposed_candidates
    ):
        raise ValueError("proposal leaves its resolved backlog marker behind")


def proposal_record_from_comment(
    body: str,
    *,
    lifecycle_state: ProposalLifecycle,
    maintainer_state: MaintainerState | None,
) -> ProposalRecord:
    machine = parse_machine_state(body)
    if machine is None:
        if (
            maintainer_state is MaintainerState.PROPOSAL
            or _MACHINE_MARKER_SIGNAL in body
        ):
            raise ValueError("proposal record requires a valid machine state")
        return ProposalRecord(lifecycle_state=lifecycle_state, is_proposal=False)

    if machine.candidate_key is None:
        if maintainer_state is MaintainerState.PROPOSAL:
            raise ValueError("proposal record requires candidate machine state")
        return ProposalRecord(lifecycle_state=lifecycle_state, is_proposal=False)

    return ProposalRecord(
        lifecycle_state=lifecycle_state,
        is_proposal=maintainer_state is MaintainerState.PROPOSAL,
        candidate_key=machine.candidate_key,
        origin_fingerprint=machine.candidate_origin_fingerprint,
        fingerprint=machine.candidate_fingerprint,
        regional_graph_key=machine.regional_graph_key,
    )
