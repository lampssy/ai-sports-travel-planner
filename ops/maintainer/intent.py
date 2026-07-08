from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Protocol

from pydantic import BaseModel, ConfigDict

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
CATALOG_KINDS = frozenset(kind for _, _, kind in CATALOG_SECTIONS)
SCOPE_KINDS = frozenset(
    {
        "stay_destination",
        "stay_base",
        "ski_area",
        "ski_area_access",
        "terrain_domain",
        "lift_pass_product",
    }
)
REPORT_KINDS = CATALOG_KINDS | {"trust_manifest"}
TRUST_MANIFEST_NAMESPACES = frozenset(section for section, _, _ in CATALOG_SECTIONS)

_ENTITY_ID = re.compile(r"^[a-z0-9]+(?:-+[a-z0-9]+)*$")
_BACKLOG_MARKER = re.compile(
    r"(?<!`)`(stay_destination|stay_base|ski_area|ski_area_access|"
    r"terrain_domain|lift_pass_product):([a-z0-9]+(?:-+[a-z0-9]+)*)`(?!`)"
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


class IntentRepository(Protocol):
    def diff_names(self, base: str, head: str) -> tuple[str, ...]: ...

    def show_text(self, revision: str, path: str) -> str: ...


def build_intent_snapshot(
    repository: IntentRepository,
    base: str,
    head: str,
) -> IntentSnapshot:
    """Build intent only from immutable Git objects, never checkout contents."""
    try:
        changed_paths = frozenset(repository.diff_names(base, head))
    except Exception as error:
        raise IntentValidationError(
            f"cannot list changed paths for {base}..{head}: {error}"
        ) from error

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
    return f"{field_name} {change}: {', '.join(sorted(items))}"


def _validate_changed_paths(paths: frozenset[str]) -> None:
    unexpected = sorted(path for path in paths if not _is_allowed_path(path))
    if unexpected:
        raise IntentValidationError(
            "unexpected changed paths: " + ", ".join(unexpected)
        )


def _is_allowed_path(path: str) -> bool:
    if not isinstance(path, str) or not path:
        return False
    pure = PurePosixPath(path)
    segments = path.split("/")
    if (
        pure.is_absolute()
        or any(part in {"", ".", ".."} for part in segments)
        or "\\" in path
        or any(character.isspace() and character != " " for character in path)
    ):
        return False
    if path in {CATALOG_PATH, TRUST_MANIFEST_PATH, BACKLOG_PATH}:
        return True
    return path.startswith(
        (CURATION_REPORT_PREFIX, "tests/test_catalog_", "docs/catalog-discovery/")
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

    reviewed_targets = report.get("reviewed_targets")
    assessments = report.get("entity_scope_assessments")
    if not isinstance(reviewed_targets, list):
        raise IntentValidationError(f"{path}: reviewed_targets must be a list")
    if not isinstance(assessments, list):
        raise IntentValidationError(f"{path}: entity_scope_assessments must be a list")

    targets: set[str] = set()
    for index, target in enumerate(reviewed_targets):
        _add_target(
            targets,
            target,
            allowed_kinds=REPORT_KINDS,
            location=f"{path}:reviewed_targets[{index}]",
        )
    for assessment_index, assessment in enumerate(assessments):
        if not isinstance(assessment, dict):
            raise IntentValidationError(
                f"{path}:entity_scope_assessments[{assessment_index}] must be an object"
            )
        target_refs = assessment.get("target_refs")
        if not isinstance(target_refs, list):
            raise IntentValidationError(
                f"{path}:entity_scope_assessments[{assessment_index}].target_refs "
                "must be a list"
            )
        for target_index, target in enumerate(target_refs):
            _add_target(
                targets,
                target,
                allowed_kinds=SCOPE_KINDS,
                location=(
                    f"{path}:entity_scope_assessments[{assessment_index}]"
                    f".target_refs[{target_index}]"
                ),
            )
    return frozenset(targets)


def _add_target(
    targets: set[str],
    value: object,
    *,
    allowed_kinds: frozenset[str] | set[str],
    location: str,
) -> None:
    if not isinstance(value, dict):
        raise IntentValidationError(f"{location} must be an object")
    kind = value.get("target_type")
    entity_id = value.get("target_id")
    if not isinstance(kind, str) or kind not in allowed_kinds:
        raise IntentValidationError(f"{location}.target_type is unsupported")
    if not isinstance(entity_id, str):
        raise IntentValidationError(f"{location}.target_id must be a string")
    if kind == "trust_manifest":
        namespace, separator, nested_id = entity_id.partition(":")
        valid_id = (
            bool(separator)
            and namespace in TRUST_MANIFEST_NAMESPACES
            and _ENTITY_ID.fullmatch(nested_id) is not None
        )
    else:
        valid_id = _ENTITY_ID.fullmatch(entity_id) is not None
    if not valid_id:
        raise IntentValidationError(f"{location}.target_id is malformed")
    targets.add(f"{kind}:{entity_id}")


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
