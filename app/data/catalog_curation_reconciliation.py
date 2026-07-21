from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.data.catalog_curation import (
    CANONICAL_FIELD_PATHS,
    CatalogCurationReport,
    CatalogTargetType,
    CatalogValidationError,
    CatalogWeatherRequestGeometry,
    JsonValue,
    catalog_weather_request_geometry,
    json_values_equal,
    validate_catalog_curation_report,
)
from app.data.catalog_loader import load_catalog_from_path
from app.domain.catalog import CatalogSnapshot, SkiArea, SkiAreaAccess
from app.domain.catalog_trust import CatalogTrustManifest

TargetKey = tuple[CatalogTargetType, str]
DeltaKey = tuple[CatalogTargetType, str, str]
_MISSING = object()


@dataclass(frozen=True)
class CatalogSnapshotDelta:
    target_type: CatalogTargetType
    target_id: str
    field_path: str
    before: JsonValue
    after: JsonValue

    @property
    def key(self) -> DeltaKey:
        return self.target_type, self.target_id, self.field_path


@dataclass(frozen=True)
class CatalogCurationReconciliationResult:
    deltas: tuple[CatalogSnapshotDelta, ...]

    @property
    def delta_count(self) -> int:
        return len(self.deltas)


@dataclass(frozen=True)
class _CatalogSnapshot:
    catalog: CatalogSnapshot
    trust_manifest: CatalogTrustManifest
    targets: dict[TargetKey, dict[str, JsonValue]]
    ski_areas: dict[str, SkiArea]
    access_by_id: dict[str, SkiAreaAccess]


@dataclass(frozen=True)
class _EntityDescriptor:
    target_type: CatalogTargetType
    collection_name: str
    id_field: str


ENTITY_DESCRIPTORS = (
    _EntityDescriptor("ski_region", "ski_regions", "ski_region_id"),
    _EntityDescriptor(
        "stay_destination",
        "stay_destinations",
        "stay_destination_id",
    ),
    _EntityDescriptor("stay_base", "stay_bases", "stay_base_id"),
    _EntityDescriptor("ski_area", "ski_areas", "ski_area_id"),
    _EntityDescriptor(
        "ski_area_access",
        "ski_area_access",
        "ski_area_access_id",
    ),
    _EntityDescriptor("terrain_domain", "terrain_domains", "terrain_domain_id"),
    _EntityDescriptor(
        "lift_pass_product",
        "lift_pass_products",
        "lift_pass_product_id",
    ),
    _EntityDescriptor(
        "rental_display_fact",
        "rental_display_facts",
        "rental_display_fact_id",
    ),
)


def _nested_value(payload: dict[str, Any], field_path: str) -> JsonValue:
    value: Any = payload
    for segment in field_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(segment)
    return _canonicalize_json(value)


def _canonicalize_json(value: Any) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _canonicalize_json(item) for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize_json(item) for item in value]
    raise TypeError(f"snapshot value is not JSON-compatible: {type(value).__name__}")


def _entity_fields(model: Any, target_type: CatalogTargetType) -> dict[str, JsonValue]:
    payload = model.model_dump(mode="json")
    return {
        field_path: _nested_value(payload, field_path)
        for field_path in sorted(CANONICAL_FIELD_PATHS[target_type])
    }


def _load_trust_manifest(path: Path) -> CatalogTrustManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CatalogTrustManifest.model_validate(payload)


def _load_snapshot(
    *,
    catalog_path: Path,
    trust_manifest_path: Path,
    label: str,
) -> _CatalogSnapshot:
    issues: list[str] = []
    try:
        catalog = load_catalog_from_path(catalog_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
        raise CatalogValidationError([f"{label} catalog: {error}"]) from error
    try:
        trust = _load_trust_manifest(trust_manifest_path)
        trust.validate_against_catalog(catalog)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValidationError,
        ValueError,
    ) as error:
        raise CatalogValidationError([f"{label} trust manifest: {error}"]) from error

    targets: dict[TargetKey, dict[str, JsonValue]] = {}
    for descriptor in ENTITY_DESCRIPTORS:
        for entity in getattr(catalog, descriptor.collection_name):
            entity_id = getattr(entity, descriptor.id_field)
            key = (descriptor.target_type, entity_id)
            if key in targets:
                issues.append(
                    f"{descriptor.target_type}:{entity_id}: duplicate target identity"
                )
                continue
            targets[key] = _entity_fields(entity, descriptor.target_type)
    for entity_type, entries in trust.entities.items():
        for entity_id, entry in entries.items():
            target_id = f"{entity_type}:{entity_id}"
            targets[("trust_manifest", target_id)] = _entity_fields(
                entry,
                "trust_manifest",
            )
    if issues:
        raise CatalogValidationError(sorted(set(issues)))
    return _CatalogSnapshot(
        catalog=catalog,
        trust_manifest=trust,
        targets=targets,
        ski_areas={area.ski_area_id: area for area in catalog.ski_areas},
        access_by_id={
            access.ski_area_access_id: access for access in catalog.ski_area_access
        },
    )


def _reported_value(value: JsonValue | object) -> JsonValue:
    return None if value is _MISSING else value  # type: ignore[return-value]


def _derive_deltas(
    base: _CatalogSnapshot,
    current: _CatalogSnapshot,
) -> tuple[CatalogSnapshotDelta, ...]:
    deltas: list[CatalogSnapshotDelta] = []
    for target_type, target_id in sorted(set(base.targets) | set(current.targets)):
        before_fields = base.targets.get((target_type, target_id), {})
        after_fields = current.targets.get((target_type, target_id), {})
        for field_path in sorted(CANONICAL_FIELD_PATHS[target_type]):
            before = _reported_value(before_fields.get(field_path, _MISSING))
            after = _reported_value(after_fields.get(field_path, _MISSING))
            if json_values_equal(before, after):
                continue
            deltas.append(
                CatalogSnapshotDelta(
                    target_type=target_type,
                    target_id=target_id,
                    field_path=field_path,
                    before=before,
                    after=after,
                )
            )
    return tuple(deltas)


def _validate_delta_parity(
    report: CatalogCurationReport,
    deltas: tuple[CatalogSnapshotDelta, ...],
    issues: list[str],
) -> None:
    deltas_by_key = {delta.key: delta for delta in deltas}
    changes_by_key = {change.target_key: change for change in report.changes}
    for key, delta in deltas_by_key.items():
        change = changes_by_key.get(key)
        target_type, target_id, field_path = key
        if change is None:
            issues.append(
                f"{target_type}:{target_id} {field_path}: missing report change "
                "for snapshot delta"
            )
            continue
        if not json_values_equal(change.before, delta.before) or not json_values_equal(
            change.after,
            delta.after,
        ):
            issues.append(
                f"{target_type}:{target_id} {field_path}: report before/after "
                "does not match snapshot delta"
            )
    for key in sorted(set(changes_by_key) - set(deltas_by_key)):
        target_type, target_id, field_path = key
        issues.append(
            f"{target_type}:{target_id} {field_path}: report change has no "
            "snapshot delta"
        )


def _validate_access_link_endpoints(
    report: CatalogCurationReport,
    deltas: tuple[CatalogSnapshotDelta, ...],
    base: _CatalogSnapshot,
    current: _CatalogSnapshot,
    issues: list[str],
) -> None:
    changed_access_ids = {
        delta.target_id for delta in deltas if delta.target_type == "ski_area_access"
    }
    reviewed = {target.target_key for target in report.reviewed_targets}
    for access_id in sorted(changed_access_ids):
        endpoints: set[tuple[str, str]] = set()
        for access in (
            base.access_by_id.get(access_id),
            current.access_by_id.get(access_id),
        ):
            if access is None:
                continue
            endpoints.add(("stay_base", access.stay_base_id))
            endpoints.add(("ski_area", access.ski_area_id))
        for target_type, target_id in sorted(endpoints - reviewed):
            issues.append(
                f"ski_area_access:{access_id}: missing reviewed endpoint "
                f"{target_type}:{target_id}"
            )


def _validate_full_access_mode_resolution(
    report: CatalogCurationReport,
    current: _CatalogSnapshot,
    issues: list[str],
) -> None:
    coverage_by_key = {
        coverage.target_key: coverage for coverage in report.field_coverage
    }
    for reviewed in report.reviewed_targets:
        if reviewed.target_type != "ski_area_access" or reviewed.scope != "full":
            continue
        access = current.access_by_id.get(reviewed.target_id)
        if access is None or access.access_mode != "unknown":
            continue
        coverage = coverage_by_key.get(
            ("ski_area_access", reviewed.target_id, "access_mode")
        )
        if coverage is None or coverage.status != "unresolved":
            issues.append(
                f"ski_area_access:{reviewed.target_id} "
                "access_mode=unknown must be unresolved in a full review"
            )


def _derived_weather_geometry(
    base: _CatalogSnapshot,
    current: _CatalogSnapshot,
) -> dict[str, tuple[CatalogWeatherRequestGeometry, CatalogWeatherRequestGeometry]]:
    derived = {}
    for ski_area_id in sorted(set(base.ski_areas) & set(current.ski_areas)):
        before = catalog_weather_request_geometry(base.ski_areas[ski_area_id])
        after = catalog_weather_request_geometry(current.ski_areas[ski_area_id])
        if before != after:
            derived[ski_area_id] = before, after
    return derived


def _validate_weather_geometry(
    report: CatalogCurationReport,
    base: _CatalogSnapshot,
    current: _CatalogSnapshot,
    issues: list[str],
) -> None:
    derived = _derived_weather_geometry(base, current)
    declared = set(report.weather_request_geometry_targets)
    if set(derived) != declared:
        issues.append(
            "weather_request_geometry_targets must exactly match retained ski-area "
            f"geometry changes: derived={sorted(derived)} report={sorted(declared)}"
        )
    assessments = {
        assessment.ski_area_id: assessment
        for assessment in report.weather_request_geometry_assessments
    }
    for ski_area_id, (before, after) in derived.items():
        assessment = assessments.get(ski_area_id)
        if assessment is None:
            continue
        if assessment.before != before or assessment.after != after:
            issues.append(
                f"{ski_area_id}: weather geometry assessment does not match snapshots"
            )


def _validate_pass_validity_window_trust(
    report: CatalogCurationReport,
    current: _CatalogSnapshot,
    issues: list[str],
) -> None:
    evidence_urls_by_pass: dict[str, set[str]] = {}
    for evidence in report.evidence:
        if (
            evidence.target_type == "lift_pass_product"
            and evidence.field_path == "validity_windows"
            and evidence.source_type == "official"
        ):
            evidence_urls_by_pass.setdefault(evidence.target_id, set()).add(
                evidence.source_url
            )

    for change in report.changes:
        if (
            change.target_type != "lift_pass_product"
            or change.field_path != "validity_windows"
            or change.after is None
        ):
            continue
        trust = current.trust_manifest.entities["lift_pass_products"][change.target_id]
        owning_status = trust.field_statuses["identity_scope_availability"]
        if owning_status != change.trust_status:
            issues.append(
                f"lift_pass_product:{change.target_id} validity_windows "
                f"trust_status={change.trust_status} does not match "
                "identity_scope_availability "
                f"status={owning_status}"
            )
        if not isinstance(change.after, list) or not change.after:
            continue
        missing_source_urls = sorted(
            evidence_urls_by_pass.get(change.target_id, set())
            - set(trust.field_source_refs["identity_scope_availability"])
        )
        if missing_source_urls:
            issues.append(
                f"lift_pass_product:{change.target_id} "
                "identity_scope_availability source refs omit validity evidence: "
                + ", ".join(missing_source_urls)
            )


def reconcile_catalog_curation_report(
    report: CatalogCurationReport,
    *,
    base_catalog_path: Path,
    current_catalog_path: Path,
    base_trust_manifest_path: Path,
    current_trust_manifest_path: Path,
) -> CatalogCurationReconciliationResult:
    validate_catalog_curation_report(report)
    base = _load_snapshot(
        catalog_path=base_catalog_path,
        trust_manifest_path=base_trust_manifest_path,
        label="base",
    )
    current = _load_snapshot(
        catalog_path=current_catalog_path,
        trust_manifest_path=current_trust_manifest_path,
        label="current",
    )
    deltas = _derive_deltas(base, current)
    issues: list[str] = []
    _validate_delta_parity(report, deltas, issues)
    _validate_access_link_endpoints(report, deltas, base, current, issues)
    _validate_full_access_mode_resolution(report, current, issues)
    _validate_weather_geometry(report, base, current, issues)
    _validate_pass_validity_window_trust(report, current, issues)
    if issues:
        raise CatalogValidationError(sorted(set(issues)))
    return CatalogCurationReconciliationResult(deltas=deltas)
