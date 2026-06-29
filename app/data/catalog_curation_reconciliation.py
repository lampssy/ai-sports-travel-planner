from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence, cast

from app.data.catalog_curation import (
    CANONICAL_FIELD_PATHS,
    NESTED_FIELD_PATH_ROOTS,
    CatalogCurationReport,
    CatalogTargetType,
    CatalogValidationError,
    JsonValue,
    catalog_weather_request_geometry,
    rental_reconciliation_target_id,
    validate_catalog_curation_report,
)
from app.data.loader import load_resorts_from_path, load_terrain_domains_from_path
from app.data.validate_resort_catalog import _validate_trust_manifest
from app.domain.models import Destination, SkiArea, TerrainDomain

TargetKey = tuple[CatalogTargetType, str]
DeltaKey = tuple[CatalogTargetType, str, str]


@dataclass(frozen=True)
class CatalogSnapshotDelta:
    target_type: CatalogTargetType
    target_id: str
    field_path: str
    before: JsonValue
    after: JsonValue

    @property
    def key(self) -> DeltaKey:
        return (self.target_type, self.target_id, self.field_path)


@dataclass(frozen=True)
class CatalogCurationReconciliationResult:
    deltas: tuple[CatalogSnapshotDelta, ...]
    required_boundary_targets: tuple[str, ...]
    required_weather_geometry_targets: tuple[str, ...]

    @property
    def delta_count(self) -> int:
        return len(self.deltas)

    @property
    def required_boundary_target_count(self) -> int:
        return len(self.required_boundary_targets)

    @property
    def required_weather_geometry_target_count(self) -> int:
        return len(self.required_weather_geometry_targets)


@dataclass(frozen=True)
class _CatalogSnapshot:
    targets: dict[TargetKey, dict[str, JsonValue]]
    destinations: dict[str, Destination]
    ski_areas: dict[str, SkiArea]


def _canonicalize_json(value: Any) -> JsonValue:
    if isinstance(value, dict):
        return {
            str(key): _canonicalize_json(nested_value)
            for key, nested_value in sorted(
                value.items(), key=lambda item: str(item[0])
            )
        }
    if isinstance(value, list):
        normalized = [_canonicalize_json(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"snapshot value is not JSON-compatible: {type(value).__name__}")


def _nested_value(payload: dict[str, Any], field_path: str) -> JsonValue:
    value: Any = payload
    for segment in field_path.split("."):
        if value is None:
            return None
        if not isinstance(value, dict):
            raise TypeError(f"cannot resolve {field_path!r} through non-object value")
        value = value.get(segment)
    return _canonicalize_json(value)


def _entity_fields(model: Any, target_type: CatalogTargetType) -> dict[str, JsonValue]:
    payload = model.model_dump(mode="json")
    return {
        field_path: _nested_value(payload, field_path)
        for field_path in sorted(CANONICAL_FIELD_PATHS[target_type])
    }


def _add_target(
    targets: dict[TargetKey, dict[str, JsonValue]],
    *,
    target_type: CatalogTargetType,
    target_id: str,
    fields: dict[str, JsonValue],
    issues: list[str],
) -> None:
    key = (target_type, target_id)
    if key in targets:
        issues.append(f"{target_type}:{target_id}: duplicate snapshot target identity")
        return
    targets[key] = fields


def _index_destinations(
    destinations: list[Destination],
    targets: dict[TargetKey, dict[str, JsonValue]],
    issues: list[str],
) -> tuple[dict[str, Destination], dict[str, SkiArea]]:
    destination_by_id: dict[str, Destination] = {}
    ski_area_by_id: dict[str, SkiArea] = {}
    for destination in destinations:
        if destination.resort_id in destination_by_id:
            issues.append(
                f"destination:{destination.resort_id}: duplicate snapshot target "
                "identity"
            )
            continue
        destination_by_id[destination.resort_id] = destination

        rental_ids: list[str] = []
        rental_names_by_id: dict[str, str] = {}
        for rental in destination.rentals:
            rental_id = rental_reconciliation_target_id(
                destination.resort_id,
                rental.name,
            )
            if rental_id in rental_names_by_id:
                issues.append(
                    f"destination:{destination.resort_id}: rental reconciliation "
                    f"identity collision for {rental_names_by_id[rental_id]!r} and "
                    f"{rental.name!r} at {rental_id}"
                )
                continue
            rental_names_by_id[rental_id] = rental.name
            rental_ids.append(rental_id)
            _add_target(
                targets,
                target_type="rental",
                target_id=rental_id,
                fields=_entity_fields(rental, "rental"),
                issues=issues,
            )

        destination_fields = _entity_fields(destination, "destination")
        destination_fields.update(
            {
                "lift_pass_products": sorted(
                    product.lift_pass_product_id
                    for product in destination.lift_pass_products
                ),
                "ski_areas": sorted(
                    ski_area.ski_area_id for ski_area in destination.ski_areas
                ),
                "terrain_groups": sorted(
                    terrain_group.terrain_group_id
                    for terrain_group in destination.terrain_groups
                ),
                "stay_bases": sorted(
                    stay_base.stay_base_id for stay_base in destination.stay_bases
                ),
                "rentals": sorted(rental_ids),
            }
        )
        _add_target(
            targets,
            target_type="destination",
            target_id=destination.resort_id,
            fields=destination_fields,
            issues=issues,
        )

        for ski_area in destination.ski_areas:
            if ski_area.ski_area_id in ski_area_by_id:
                issues.append(
                    f"ski_area:{ski_area.ski_area_id}: duplicate snapshot target "
                    "identity"
                )
            else:
                ski_area_by_id[ski_area.ski_area_id] = ski_area
            _add_target(
                targets,
                target_type="ski_area",
                target_id=ski_area.ski_area_id,
                fields=_entity_fields(ski_area, "ski_area"),
                issues=issues,
            )
        for stay_base in destination.stay_bases:
            _add_target(
                targets,
                target_type="stay_base",
                target_id=stay_base.stay_base_id,
                fields=_entity_fields(stay_base, "stay_base"),
                issues=issues,
            )
        for terrain_group in destination.terrain_groups:
            _add_target(
                targets,
                target_type="terrain_group",
                target_id=terrain_group.terrain_group_id,
                fields=_entity_fields(terrain_group, "terrain_group"),
                issues=issues,
            )
        for product in destination.lift_pass_products:
            _add_target(
                targets,
                target_type="lift_pass_product",
                target_id=product.lift_pass_product_id,
                fields=_entity_fields(product, "lift_pass_product"),
                issues=issues,
            )
    return destination_by_id, ski_area_by_id


def _index_terrain_domains(
    terrain_domains: list[TerrainDomain],
    targets: dict[TargetKey, dict[str, JsonValue]],
    issues: list[str],
) -> None:
    for terrain_domain in terrain_domains:
        _add_target(
            targets,
            target_type="terrain_domain",
            target_id=terrain_domain.terrain_domain_id,
            fields=_entity_fields(terrain_domain, "terrain_domain"),
            issues=issues,
        )


def _load_trust_manifest(path: Path, issues: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        issues.append(f"Unable to read trust manifest at {path}: {error}")
        return {}
    except json.JSONDecodeError as error:
        issues.append(f"Invalid JSON in trust manifest at {path}: {error}")
        return {}
    if not isinstance(payload, dict):
        issues.append(f"trust manifest at {path} must be a JSON object")
        return {}
    return payload


def _index_trust_manifest(
    manifest: dict[str, Any],
    targets: dict[TargetKey, dict[str, JsonValue]],
    issues: list[str],
) -> None:
    for namespace, manifest_key in (
        ("destination", "destinations"),
        ("terrain_domain", "terrain_domains"),
    ):
        entries = manifest.get(manifest_key)
        if not isinstance(entries, dict):
            continue
        for record_id, raw_entry in entries.items():
            if not isinstance(record_id, str) or not isinstance(raw_entry, dict):
                continue
            fields = {
                field_path: _canonicalize_json(raw_entry.get(field_path))
                for field_path in sorted(CANONICAL_FIELD_PATHS["trust_manifest"])
            }
            _add_target(
                targets,
                target_type="trust_manifest",
                target_id=f"{namespace}:{record_id}",
                fields=fields,
                issues=issues,
            )


def _load_snapshot(
    *,
    resorts_path: Path,
    terrain_domains_path: Path,
    trust_manifest_path: Path,
    label: str,
) -> _CatalogSnapshot:
    issues: list[str] = []
    try:
        destinations = load_resorts_from_path(resorts_path)
    except ValueError as error:
        issues.append(f"{label} resort snapshot: {error}")
        destinations = []
    try:
        terrain_domains = load_terrain_domains_from_path(terrain_domains_path)
    except ValueError as error:
        issues.append(f"{label} terrain-domain snapshot: {error}")
        terrain_domains = []
    manifest = _load_trust_manifest(trust_manifest_path, issues)
    _validate_trust_manifest(
        manifest,
        {destination.resort_id for destination in destinations},
        {
            terrain_domain.terrain_domain_id: terrain_domain.name
            for terrain_domain in terrain_domains
        },
        issues,
    )

    targets: dict[TargetKey, dict[str, JsonValue]] = {}
    destination_by_id, ski_area_by_id = _index_destinations(
        destinations,
        targets,
        issues,
    )
    _index_terrain_domains(terrain_domains, targets, issues)
    _index_trust_manifest(manifest, targets, issues)
    if issues:
        raise CatalogValidationError(sorted(set(issues)))
    return _CatalogSnapshot(
        targets=targets,
        destinations=destination_by_id,
        ski_areas=ski_area_by_id,
    )


def _derive_deltas(
    base: _CatalogSnapshot,
    current: _CatalogSnapshot,
) -> tuple[CatalogSnapshotDelta, ...]:
    deltas: list[CatalogSnapshotDelta] = []
    for target_key in sorted(set(base.targets) | set(current.targets)):
        target_type, target_id = target_key
        base_fields = base.targets.get(target_key, {})
        current_fields = current.targets.get(target_key, {})
        for field_path in sorted(CANONICAL_FIELD_PATHS[target_type]):
            before = base_fields.get(field_path)
            after = current_fields.get(field_path)
            if field_path in NESTED_FIELD_PATH_ROOTS[target_type]:
                field_deltas = _nested_field_deltas(field_path, before, after)
            elif before != after:
                field_deltas = ((field_path, before, after),)
            else:
                field_deltas = ()
            for delta_field_path, delta_before, delta_after in field_deltas:
                if delta_before == delta_after:
                    continue
                deltas.append(
                    CatalogSnapshotDelta(
                        target_type=target_type,
                        target_id=target_id,
                        field_path=delta_field_path,
                        before=delta_before,
                        after=delta_after,
                    )
                )
    return tuple(deltas)


_MISSING = object()


def _reported_snapshot_value(value: JsonValue | object) -> JsonValue:
    return None if value is _MISSING else cast(JsonValue, value)


def _nested_field_deltas(
    field_path: str,
    before: JsonValue | object,
    after: JsonValue | object,
) -> tuple[tuple[str, JsonValue, JsonValue], ...]:
    if before is not _MISSING and after is not _MISSING and before == after:
        return ()
    if (
        (before is _MISSING or isinstance(before, dict))
        and (after is _MISSING or isinstance(after, dict))
        and (isinstance(before, dict) or isinstance(after, dict))
    ):
        before_dict = before if isinstance(before, dict) else {}
        after_dict = after if isinstance(after, dict) else {}
        keys = sorted(set(before_dict) | set(after_dict))
        if not keys:
            return (
                (
                    field_path,
                    _reported_snapshot_value(before),
                    _reported_snapshot_value(after),
                ),
            )
        return tuple(
            delta
            for key in keys
            for delta in _nested_field_deltas(
                f"{field_path}.{key}",
                before_dict.get(key, _MISSING),
                after_dict.get(key, _MISSING),
            )
        )
    if (
        (before is _MISSING or isinstance(before, list))
        and (after is _MISSING or isinstance(after, list))
        and (isinstance(before, list) or isinstance(after, list))
    ):
        before_list = before if isinstance(before, list) else []
        after_list = after if isinstance(after, list) else []
        length = max(len(before_list), len(after_list))
        if length == 0:
            return (
                (
                    field_path,
                    _reported_snapshot_value(before),
                    _reported_snapshot_value(after),
                ),
            )
        return tuple(
            delta
            for index in range(length)
            for delta in _nested_field_deltas(
                f"{field_path}[{index}]",
                before_list[index] if index < len(before_list) else _MISSING,
                after_list[index] if index < len(after_list) else _MISSING,
            )
        )
    return (
        (
            field_path,
            _reported_snapshot_value(before),
            _reported_snapshot_value(after),
        ),
    )


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
        if change.before != delta.before or change.after != delta.after:
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


def _validate_required_boundary_targets(
    report: CatalogCurationReport,
    base: _CatalogSnapshot,
    current: _CatalogSnapshot,
    required_targets: tuple[str, ...],
    issues: list[str],
) -> None:
    assessments = {
        assessment.candidate_id: assessment
        for assessment in report.destination_boundary_assessments
    }
    declared_targets = set(report.boundary_decision_targets)
    for destination_id, assessment in assessments.items():
        if not assessment.is_passing:
            issues.append(
                f"{destination_id}: reconcile mode requires a complete passing "
                "assessment"
            )
    for destination_id in required_targets:
        if (
            destination_id not in base.destinations
            or destination_id not in current.destinations
        ):
            issues.append(
                f"{destination_id}: required boundary target must be retained in "
                "both snapshots"
            )
        if destination_id not in declared_targets:
            issues.append(
                f"{destination_id}: required boundary target is missing from report"
            )
            continue
        assessment = assessments.get(destination_id)
        if assessment is None or not assessment.is_passing:
            issues.append(
                f"{destination_id}: required boundary target needs a complete "
                "passing assessment"
            )


def _validate_weather_geometry(
    report: CatalogCurationReport,
    base: _CatalogSnapshot,
    current: _CatalogSnapshot,
    required_targets: tuple[str, ...],
    issues: list[str],
) -> None:
    declared_targets = set(report.weather_request_geometry_targets)
    assessments = {
        assessment.ski_area_id: assessment
        for assessment in report.weather_request_geometry_assessments
    }
    for ski_area_id in required_targets:
        if ski_area_id not in declared_targets:
            issues.append(
                f"{ski_area_id}: required weather geometry target is missing "
                "from report"
            )
    for ski_area_id in sorted(declared_targets | set(required_targets)):
        base_ski_area = base.ski_areas.get(ski_area_id)
        current_ski_area = current.ski_areas.get(ski_area_id)
        if base_ski_area is None or current_ski_area is None:
            issues.append(
                f"{ski_area_id}: weather geometry target must be retained in "
                "both snapshots"
            )
            continue
        assessment = assessments.get(ski_area_id)
        if assessment is None:
            continue
        expected_before = catalog_weather_request_geometry(base_ski_area)
        expected_after = catalog_weather_request_geometry(current_ski_area)
        if assessment.before != expected_before or assessment.after != expected_after:
            issues.append(
                f"{ski_area_id}: weather geometry assessment does not match snapshots"
            )


def _unique_required_targets(
    values: Sequence[str],
    *,
    label: str,
    issues: list[str],
) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values)
    if any(not value for value in normalized):
        issues.append(f"{label} cannot contain blank values")
    if len(set(normalized)) != len(normalized):
        issues.append(f"{label} must be unique")
    return normalized


def _format_target_set(values: set[str]) -> str:
    return "[" + ", ".join(sorted(values)) + "]"


def _validate_required_target_declarations(
    report: CatalogCurationReport,
    required_boundary_targets: tuple[str, ...],
    required_weather_geometry_targets: tuple[str, ...],
    issues: list[str],
) -> None:
    external_boundary_targets = set(required_boundary_targets)
    report_boundary_targets = set(report.boundary_decision_targets)
    if not external_boundary_targets:
        issues.append(
            "reconcile validation requires at least one required_boundary_target"
        )
    if external_boundary_targets != report_boundary_targets:
        issues.append(
            "required_boundary_targets must exactly match "
            "report.boundary_decision_targets: "
            f"external={_format_target_set(external_boundary_targets)} "
            f"report={_format_target_set(report_boundary_targets)}"
        )

    external_geometry_targets = set(required_weather_geometry_targets)
    report_geometry_targets = set(report.weather_request_geometry_targets)
    if external_geometry_targets != report_geometry_targets:
        issues.append(
            "required_weather_geometry_targets must exactly match "
            "report.weather_request_geometry_targets: "
            f"external={_format_target_set(external_geometry_targets)} "
            f"report={_format_target_set(report_geometry_targets)}"
        )


def reconcile_catalog_curation_report(
    report: CatalogCurationReport,
    *,
    base_resorts_path: Path,
    current_resorts_path: Path,
    base_terrain_domains_path: Path,
    current_terrain_domains_path: Path,
    base_trust_manifest_path: Path,
    current_trust_manifest_path: Path,
    required_boundary_targets: Sequence[str] = (),
    required_weather_geometry_targets: Sequence[str] = (),
) -> CatalogCurationReconciliationResult:
    validate_catalog_curation_report(report)
    issues: list[str] = []
    normalized_boundary_targets = _unique_required_targets(
        required_boundary_targets,
        label="required_boundary_targets",
        issues=issues,
    )
    normalized_geometry_targets = _unique_required_targets(
        required_weather_geometry_targets,
        label="required_weather_geometry_targets",
        issues=issues,
    )
    _validate_required_target_declarations(
        report,
        normalized_boundary_targets,
        normalized_geometry_targets,
        issues,
    )
    if issues:
        raise CatalogValidationError(sorted(set(issues)))

    base = _load_snapshot(
        resorts_path=base_resorts_path,
        terrain_domains_path=base_terrain_domains_path,
        trust_manifest_path=base_trust_manifest_path,
        label="base",
    )
    current = _load_snapshot(
        resorts_path=current_resorts_path,
        terrain_domains_path=current_terrain_domains_path,
        trust_manifest_path=current_trust_manifest_path,
        label="current",
    )
    deltas = _derive_deltas(base, current)
    _validate_delta_parity(report, deltas, issues)
    _validate_required_boundary_targets(
        report,
        base,
        current,
        normalized_boundary_targets,
        issues,
    )
    _validate_weather_geometry(
        report,
        base,
        current,
        normalized_geometry_targets,
        issues,
    )
    if issues:
        raise CatalogValidationError(sorted(set(issues)))
    return CatalogCurationReconciliationResult(
        deltas=deltas,
        required_boundary_targets=normalized_boundary_targets,
        required_weather_geometry_targets=normalized_geometry_targets,
    )
