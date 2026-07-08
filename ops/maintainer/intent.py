from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from app.data.catalog_curation import (
    CatalogCurationReport,
    CatalogValidationError,
    validate_catalog_curation_report,
)

CATALOG_PATH = "app/data/catalog.json"
TRUST_MANIFEST_PATH = "app/data/resort_trust_manifest.json"
BACKLOG_PATH = "docs/product-backlog.md"
CURATION_REPORT_PREFIX = "docs/catalog-curation/"

CATALOG_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("ski_regions", "ski_region_id", "ski_region"),
    ("stay_destinations", "stay_destination_id", "stay_destination"),
    ("stay_bases", "stay_base_id", "stay_base"),
    ("ski_areas", "ski_area_id", "ski_area"),
    ("ski_area_access", "ski_area_access_id", "ski_area_access"),
    ("terrain_domains", "terrain_domain_id", "terrain_domain"),
    ("lift_pass_products", "lift_pass_product_id", "lift_pass_product"),
    ("rental_display_facts", "rental_display_fact_id", "rental_display_fact"),
)
_ENTITY_ID = re.compile(r"^[a-z0-9]+(?:-+[a-z0-9]+)*$")
_GIT_OID = re.compile(r"^[0-9a-f]{40}$")
_BACKLOG_MARKER = re.compile(
    r"(?<!`)`(stay_destination|stay_base|ski_area|ski_area_access|"
    r"terrain_domain|lift_pass_product):([a-z0-9]+(?:-+[a-z0-9]+)*)`(?!`)"
)
_CURATION_ARTIFACT = re.compile(
    r"^docs/catalog-curation/[A-Za-z0-9][A-Za-z0-9._-]*\.(?:json|md)$"
)
_DISCOVERY_ARTIFACT = re.compile(
    r"^docs/catalog-discovery/[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
)


class IntentValidationError(ValueError):
    """The selected revisions cannot produce a safe semantic snapshot."""


class IntentDriftError(RuntimeError):
    """A rebase changed the selected branch's semantic intent."""


class IntentSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    changed_paths: frozenset[str]
    catalog_targets: frozenset[str]
    report_targets: frozenset[str]
    removed_backlog_markers: frozenset[str]


class IntentDiffEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str
    old_mode: str
    new_mode: str
    old_oid: str
    new_oid: str
    status: str


class IntentRepository(Protocol):
    def diff_entries(self, base: str, head: str) -> tuple[IntentDiffEntry, ...]: ...

    def show_text(self, revision: str, path: str) -> str: ...


def build_intent_snapshot(
    repository: IntentRepository,
    base: str,
    head: str,
) -> IntentSnapshot:
    """Build intent only from immutable Git objects, never checkout contents."""
    try:
        entries = repository.diff_entries(base, head)
    except Exception as error:
        raise IntentValidationError(
            f"cannot list changed paths for {base}..{head}: {error}"
        ) from error

    _validate_diff_entries(entries)
    changed_paths = frozenset(entry.path for entry in entries)

    _validate_changed_paths(changed_paths)

    catalog_targets: frozenset[str] = frozenset()
    if CATALOG_PATH in changed_paths:
        before = _load_json_object(repository, base, CATALOG_PATH, "base catalog")
        after = _load_json_object(repository, head, CATALOG_PATH, "head catalog")
        catalog_targets = _compare_catalog(before, after)

    report_targets: set[str] = set()
    for path in sorted(changed_paths):
        if path.startswith(CURATION_REPORT_PREFIX) and path.endswith(".json"):
            report_targets.update(_report_targets(repository, head, path))

    removed_backlog_markers: frozenset[str] = frozenset()
    if BACKLOG_PATH in changed_paths:
        before = _show_required(repository, base, BACKLOG_PATH, "base backlog")
        after = _show_required(repository, head, BACKLOG_PATH, "head backlog")
        removed_backlog_markers = frozenset(
            _backlog_markers(before, "base backlog")
            - _backlog_markers(after, "head backlog")
        )

    return IntentSnapshot(
        changed_paths=changed_paths,
        catalog_targets=catalog_targets,
        report_targets=frozenset(report_targets),
        removed_backlog_markers=removed_backlog_markers,
    )


def compare_intent(before: IntentSnapshot, after: IntentSnapshot) -> None:
    """Fail without mutation when a rebase expands paths or changes semantics."""
    issues: list[str] = []
    added_paths = after.changed_paths - before.changed_paths
    if added_paths:
        issues.append(_difference_message("changed_paths", "added", added_paths))

    for field_name in (
        "catalog_targets",
        "report_targets",
        "removed_backlog_markers",
    ):
        before_items = getattr(before, field_name)
        after_items = getattr(after, field_name)
        added = after_items - before_items
        removed = before_items - after_items
        if added:
            issues.append(_difference_message(field_name, "added", added))
        if removed:
            issues.append(_difference_message(field_name, "removed", removed))

    if issues:
        raise IntentDriftError("intent drift detected: " + "; ".join(issues))


def _difference_message(field_name: str, change: str, items: set[str]) -> str:
    rendered = (
        (repr(item) for item in sorted(items))
        if field_name == "changed_paths"
        else iter(sorted(items))
    )
    return f"{field_name} {change}: {', '.join(rendered)}"


def _validate_changed_paths(paths: frozenset[str]) -> None:
    unexpected = sorted(path for path in paths if not is_allowed_curation_path(path))
    if unexpected:
        raise IntentValidationError(
            "unexpected changed paths: " + ", ".join(repr(path) for path in unexpected)
        )


def _validate_diff_entries(entries: tuple[IntentDiffEntry, ...]) -> None:
    paths = [entry.path for entry in entries]
    if len(paths) != len(set(paths)):
        raise IntentValidationError("diff contains duplicate changed paths")
    zero_oid = "0" * 40
    for entry in entries:
        valid_oids = (
            _GIT_OID.fullmatch(entry.old_oid) is not None
            and _GIT_OID.fullmatch(entry.new_oid) is not None
        )
        if entry.status == "A":
            safe = (
                valid_oids
                and entry.old_mode == "000000"
                and entry.new_mode == "100644"
                and entry.old_oid == zero_oid
                and entry.new_oid != zero_oid
            )
        elif entry.status == "D":
            safe = (
                valid_oids
                and entry.old_mode == "100644"
                and entry.new_mode == "000000"
                and entry.old_oid != zero_oid
                and entry.new_oid == zero_oid
            )
        elif entry.status == "M":
            safe = (
                valid_oids
                and entry.old_mode == "100644"
                and entry.new_mode == "100644"
                and entry.old_oid != entry.new_oid
                and entry.old_oid != zero_oid
                and entry.new_oid != zero_oid
            )
        else:
            safe = False
        if not safe:
            raise IntentValidationError(
                f"unsafe diff metadata for changed path {entry.path!r}"
            )


def is_allowed_curation_path(path: str) -> bool:
    """Return whether Task 4 owns this exact repository-relative path."""
    if not isinstance(path, str) or not path:
        return False
    pure = PurePosixPath(path)
    segments = path.split("/")
    if (
        pure.is_absolute()
        or any(part in {"", ".", ".."} for part in segments)
        or "\\" in path
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
    ):
        return False
    if path in {CATALOG_PATH, TRUST_MANIFEST_PATH, BACKLOG_PATH}:
        return True
    return any(
        pattern.fullmatch(path) is not None
        for pattern in (_CURATION_ARTIFACT, _DISCOVERY_ARTIFACT)
    )


def _load_json_object(
    repository: IntentRepository,
    revision: str,
    path: str,
    description: str,
) -> dict[str, object]:
    content = _show_required(repository, revision, path, description)
    try:
        value = json.loads(content, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError) as error:
        raise IntentValidationError(
            f"{description} contains invalid JSON: {error}"
        ) from error
    if not isinstance(value, dict):
        raise IntentValidationError(f"{description} must be a JSON object")
    return value


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON constant {value}")


def _show_required(
    repository: IntentRepository,
    revision: str,
    path: str,
    description: str,
) -> str:
    try:
        return repository.show_text(revision, path)
    except Exception as error:
        raise IntentValidationError(
            f"cannot read {description} {revision}:{path}: {error}"
        ) from error


def _compare_catalog(
    before: dict[str, object],
    after: dict[str, object],
) -> frozenset[str]:
    if before.get("schema_version") != 2 or after.get("schema_version") != 2:
        raise IntentValidationError("catalog schema_version must be 2")
    changed: set[str] = set()
    for section, id_field, kind in CATALOG_SECTIONS:
        before_rows = _catalog_rows(before, section, id_field)
        after_rows = _catalog_rows(after, section, id_field)
        for entity_id in before_rows.keys() | after_rows.keys():
            if before_rows.get(entity_id) != after_rows.get(entity_id):
                changed.add(f"{kind}:{entity_id}")
    return frozenset(changed)


def _catalog_rows(
    catalog: dict[str, object],
    section: str,
    id_field: str,
) -> dict[str, dict[str, object]]:
    value = catalog.get(section)
    if not isinstance(value, list):
        raise IntentValidationError(f"catalog section {section} must be a list")
    rows: dict[str, dict[str, object]] = {}
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            raise IntentValidationError(f"{section}[{index}] must be a JSON object")
        entity_id = row.get(id_field)
        if not isinstance(entity_id, str) or _ENTITY_ID.fullmatch(entity_id) is None:
            raise IntentValidationError(
                f"{section}[{index}].{id_field} must be a canonical entity ID"
            )
        if entity_id in rows:
            raise IntentValidationError(f"duplicate {id_field} {entity_id}")
        rows[entity_id] = row
    return rows


def _report_targets(
    repository: IntentRepository,
    revision: str,
    path: str,
) -> frozenset[str]:
    try:
        report = _load_json_object(repository, revision, path, f"changed report {path}")
    except IntentValidationError as error:
        if "cannot read" in str(error):
            raise IntentValidationError(
                f"cannot read changed report {path}: {error}"
            ) from error
        raise
    if report.get("report_schema_version") != 2:
        raise IntentValidationError(f"{path}: report_schema_version must be 2")
    try:
        typed_report = CatalogCurationReport.model_validate(report)
        validate_catalog_curation_report(typed_report)
    except (ValidationError, CatalogValidationError) as error:
        raise IntentValidationError(
            f"{path}: invalid CatalogCurationReport: {error}"
        ) from error

    targets = {
        f"{target.target_type}:{target.target_id}"
        for target in typed_report.reviewed_targets
    }
    targets.update(
        f"{target.target_type}:{target.target_id}"
        for assessment in typed_report.entity_scope_assessments
        for target in assessment.target_refs
    )
    return frozenset(targets)


def _backlog_markers(markdown: str, description: str) -> frozenset[str]:
    section_lines: list[str] = []
    in_section = False
    section_count = 0
    for line in markdown.splitlines():
        if line == "## Catalog Curation Refinements":
            section_count += 1
            in_section = True
            continue
        if line.startswith("## ") and not line.startswith("### "):
            in_section = False
            continue
        if in_section:
            section_lines.append(line)
    if section_count != 1:
        raise IntentValidationError(
            f"{description} must contain exactly one "
            "## Catalog Curation Refinements section"
        )
    return frozenset(
        f"{match.group(1)}:{match.group(2)}"
        for line in section_lines
        for match in _BACKLOG_MARKER.finditer(line)
    )
