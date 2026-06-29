from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence, cast

from pydantic import ValidationError

from app.data.catalog_curation import (
    CANONICAL_FIELD_PATHS,
    NESTED_FIELD_PATH_ROOTS,
    CatalogCurationReport,
    CatalogTargetType,
    CatalogValidationError,
    CatalogWeatherRequestGeometry,
    JsonValue,
    catalog_weather_request_geometry,
    json_values_equal,
    rental_reconciliation_target_id,
    validate_catalog_curation_report,
)
from app.data.loader import load_resorts_from_path, load_terrain_domains_from_path
from app.data.validate_resort_catalog import _validate_trust_manifest
from app.domain.models import Destination, SkiArea, TerrainDomain

TargetKey = tuple[CatalogTargetType, str]
DeltaKey = tuple[CatalogTargetType, str, str]

OBJECT_LIST_IDENTITY_FIELDS: dict[str, tuple[str, ...]] = {
    "prices": (
        "duration_days",
        "audience",
        "season_label",
        "currency",
        "price_kind",
    ),
    "ski_area_refs": ("resort_id", "ski_area_id"),
}
CUSTOM_LIST_IDENTITY_FIELDS = frozenset({"season_windows"})
SCALAR_SET_LIST_FIELDS = frozenset(
    {
        "source_refs",
        "source_urls",
        "ski_area_ids",
        "valid_ski_area_ids",
        "terrain_domain_ids",
        "supported_skill_levels",
        "atmosphere_tags",
        "lift_pass_products",
        "ski_areas",
        "terrain_groups",
        "stay_bases",
        "rentals",
    }
)
DESTINATION_ENTITY_COLLECTION_FIELDS = frozenset(
    {"lift_pass_products", "ski_areas", "terrain_groups", "stay_bases", "rentals"}
)


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


def _json_identity_key(value: JsonValue) -> tuple[Any, ...]:
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return ("number", value)
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, dict):
        return (
            "object",
            tuple((key, _json_identity_key(value[key])) for key in sorted(value)),
        )
    if isinstance(value, list):
        return ("array", tuple(_json_identity_key(item) for item in value))
    raise TypeError(f"snapshot value is not JSON-compatible: {type(value).__name__}")


def _stable_list_item_key(
    field_path: str,
    item: JsonValue,
) -> tuple[Any, ...] | None:
    if field_path == "season_windows":
        if not isinstance(item, dict):
            raise TypeError("season_windows entries must be JSON objects")
        season_label = item.get("season_label")
        if isinstance(season_label, str) and season_label.strip():
            return ("object", (("season_label", ("string", season_label.strip())),))
        missing_date_fields = [
            field for field in ("start_date", "end_date") if field not in item
        ]
        if missing_date_fields:
            raise TypeError(
                "season_windows entry is missing fallback identity fields: "
                + ", ".join(missing_date_fields)
            )
        return (
            "object",
            tuple(
                (field, _json_identity_key(cast(JsonValue, item[field])))
                for field in ("start_date", "end_date")
            ),
        )
    identity_fields = OBJECT_LIST_IDENTITY_FIELDS.get(field_path)
    if identity_fields is not None:
        if not isinstance(item, dict):
            raise TypeError(f"{field_path} entries must be JSON objects")
        missing_fields = [field for field in identity_fields if field not in item]
        if missing_fields:
            raise TypeError(
                f"{field_path} entry is missing stable identity fields: "
                + ", ".join(missing_fields)
            )
        return (
            "object",
            tuple(
                (field, _json_identity_key(cast(JsonValue, item[field])))
                for field in identity_fields
            ),
        )
    if field_path in SCALAR_SET_LIST_FIELDS:
        if isinstance(item, (dict, list)):
            raise TypeError(f"{field_path} entries must be JSON scalars")
        return ("scalar", _json_identity_key(item))
    return None


def _stable_list_entries(
    field_path: str,
    values: list[JsonValue],
) -> list[tuple[tuple[Any, ...], JsonValue]] | None:
    if (
        field_path not in OBJECT_LIST_IDENTITY_FIELDS
        and field_path not in CUSTOM_LIST_IDENTITY_FIELDS
        and field_path not in SCALAR_SET_LIST_FIELDS
    ):
        return None
    entries: list[tuple[tuple[Any, ...], JsonValue]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in values:
        key = _stable_list_item_key(field_path, item)
        if key is None:
            raise TypeError(f"{field_path} has no stable list identity policy")
        if key in seen:
            raise ValueError(f"{field_path} contains a duplicate stable identity")
        seen.add(key)
        entries.append((key, item))
    return sorted(entries, key=lambda entry: entry[0])


def _canonicalize_json(
    value: Any,
    *,
    list_field_path: str | None = None,
) -> JsonValue:
    if isinstance(value, dict):
        return {
            str(key): _canonicalize_json(nested_value)
            for key, nested_value in sorted(
                value.items(), key=lambda item: str(item[0])
            )
        }
    if isinstance(value, list):
        normalized = [_canonicalize_json(item) for item in value]
        if list_field_path is None:
            return normalized
        stable_entries = _stable_list_entries(list_field_path, normalized)
        if stable_entries is None:
            return normalized
        return [item for _, item in stable_entries]
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
    return _canonicalize_json(value, list_field_path=field_path)


def _entity_fields(model: Any, target_type: CatalogTargetType) -> dict[str, JsonValue]:
    payload = model.model_dump(mode="json")
    return {
        field_path: (
            []
            if target_type == "destination"
            and field_path in DESTINATION_ENTITY_COLLECTION_FIELDS
            else _nested_value(payload, field_path)
        )
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
    except (TypeError, ValidationError, ValueError) as error:
        issues.append(f"Invalid trust manifest at {path}: {error}")
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
                field_path: _canonicalize_json(
                    raw_entry.get(field_path),
                    list_field_path=field_path,
                )
                for field_path in sorted(CANONICAL_FIELD_PATHS["trust_manifest"])
            }
            _add_target(
                targets,
                target_type="trust_manifest",
                target_id=f"{namespace}:{record_id}",
                fields=fields,
                issues=issues,
            )


def _validate_snapshot_list_shape(
    path: Path,
    label: str,
    issues: list[str],
) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        issues.append(f"Unable to read {label} at {path}: {error}")
        return False
    except json.JSONDecodeError as error:
        issues.append(f"Invalid JSON in {label} at {path}: {error}")
        return False
    if not isinstance(payload, list):
        issues.append(f"{label} at {path} must be a JSON list")
        return False
    return True


def _load_snapshot(
    *,
    resorts_path: Path,
    terrain_domains_path: Path,
    trust_manifest_path: Path,
    label: str,
) -> _CatalogSnapshot:
    issues: list[str] = []
    destinations = []
    if _validate_snapshot_list_shape(resorts_path, f"{label} resort snapshot", issues):
        try:
            destinations = load_resorts_from_path(resorts_path)
        except (OSError, TypeError, ValidationError, ValueError) as error:
            issues.append(f"{label} resort snapshot: {error}")
    terrain_domains = []
    if _validate_snapshot_list_shape(
        terrain_domains_path,
        f"{label} terrain-domain snapshot",
        issues,
    ):
        try:
            terrain_domains = load_terrain_domains_from_path(terrain_domains_path)
        except (OSError, TypeError, ValidationError, ValueError) as error:
            issues.append(f"{label} terrain-domain snapshot: {error}")
    manifest = _load_trust_manifest(trust_manifest_path, issues)
    try:
        _validate_trust_manifest(
            manifest,
            {destination.resort_id for destination in destinations},
            {
                terrain_domain.terrain_domain_id: terrain_domain.name
                for terrain_domain in terrain_domains
            },
            issues,
        )
    except (OSError, TypeError, ValidationError, ValueError) as error:
        issues.append(f"{label} trust manifest validation: {error}")

    targets: dict[TargetKey, dict[str, JsonValue]] = {}
    destination_by_id: dict[str, Destination] = {}
    ski_area_by_id: dict[str, SkiArea] = {}
    try:
        destination_by_id, ski_area_by_id = _index_destinations(
            destinations,
            targets,
            issues,
        )
        _index_terrain_domains(terrain_domains, targets, issues)
    except (OSError, TypeError, ValidationError, ValueError) as error:
        issues.append(f"{label} snapshot normalization: {error}")
    try:
        _index_trust_manifest(manifest, targets, issues)
    except (OSError, TypeError, ValidationError, ValueError) as error:
        issues.append(f"{label} trust manifest indexing: {error}")
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
            before = base_fields.get(field_path, _MISSING)
            after = current_fields.get(field_path, _MISSING)
            if field_path in NESTED_FIELD_PATH_ROOTS[target_type]:
                field_deltas = _nested_field_deltas(field_path, before, after)
            else:
                reported_before = _reported_snapshot_value(before)
                reported_after = _reported_snapshot_value(after)
                field_deltas = (
                    ((field_path, reported_before, reported_after),)
                    if not json_values_equal(reported_before, reported_after)
                    else ()
                )
            for delta_field_path, delta_before, delta_after in field_deltas:
                if json_values_equal(delta_before, delta_after):
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
    if (
        before is not _MISSING
        and after is not _MISSING
        and json_values_equal(cast(JsonValue, before), cast(JsonValue, after))
    ):
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
        if not before_list and not after_list:
            return (
                (
                    field_path,
                    _reported_snapshot_value(before),
                    _reported_snapshot_value(after),
                ),
            )
        before_entries = _stable_list_entries(field_path, before_list)
        after_entries = _stable_list_entries(field_path, after_list)
        if before_entries is not None and after_entries is not None:
            before_by_key = dict(before_entries)
            after_by_key = dict(after_entries)
            return tuple(
                delta
                for index, key in enumerate(
                    sorted(set(before_by_key) | set(after_by_key))
                )
                for delta in _nested_field_deltas(
                    f"{field_path}[{index}]",
                    before_by_key.get(key, _MISSING),
                    after_by_key.get(key, _MISSING),
                )
            )
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
        if not json_values_equal(change.before, delta.before) or not json_values_equal(
            change.after, delta.after
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


def _validate_required_boundary_targets(
    report: CatalogCurationReport,
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


def _derived_retained_weather_geometry(
    base: _CatalogSnapshot,
    current: _CatalogSnapshot,
) -> dict[
    str,
    tuple[CatalogWeatherRequestGeometry, CatalogWeatherRequestGeometry],
]:
    derived: dict[
        str,
        tuple[CatalogWeatherRequestGeometry, CatalogWeatherRequestGeometry],
    ] = {}
    for ski_area_id in sorted(set(base.ski_areas) & set(current.ski_areas)):
        before = catalog_weather_request_geometry(base.ski_areas[ski_area_id])
        after = catalog_weather_request_geometry(current.ski_areas[ski_area_id])
        if before != after:
            derived[ski_area_id] = (before, after)
    return derived


def _validate_weather_geometry(
    report: CatalogCurationReport,
    base: _CatalogSnapshot,
    current: _CatalogSnapshot,
    required_targets: tuple[str, ...],
    issues: list[str],
) -> None:
    declared_targets = set(report.weather_request_geometry_targets)
    external_targets = set(required_targets)
    derived_geometry = _derived_retained_weather_geometry(base, current)
    derived_targets = set(derived_geometry)
    assessments = {
        assessment.ski_area_id: assessment
        for assessment in report.weather_request_geometry_assessments
    }
    if not derived_targets.issubset(declared_targets) or not derived_targets.issubset(
        external_targets
    ):
        issues.append(
            "derived retained weather geometry targets must be included in report "
            "and required targets: "
            f"derived={_format_target_set(derived_targets)} "
            f"report={_format_target_set(declared_targets)} "
            f"external={_format_target_set(external_targets)}"
        )
    for ski_area_id in sorted(declared_targets):
        base_ski_area = base.ski_areas.get(ski_area_id)
        current_ski_area = current.ski_areas.get(ski_area_id)
        if base_ski_area is None or current_ski_area is None:
            issues.append(
                f"{ski_area_id}: explicit weather geometry target must be retained "
                "in both snapshots"
            )
            continue
        expected_before = catalog_weather_request_geometry(base_ski_area)
        expected_after = catalog_weather_request_geometry(current_ski_area)
        assessment = assessments.get(ski_area_id)
        if assessment is None:
            issues.append(
                f"{ski_area_id}: explicit weather geometry target requires an "
                "assessment"
            )
            continue
        if assessment.before != expected_before or assessment.after != expected_after:
            issues.append(
                f"{ski_area_id}: weather geometry assessment does not match snapshots"
            )
        elif ski_area_id in derived_geometry and not assessment.material_change:
            issues.append(
                f"{ski_area_id}: derived weather geometry assessment must be material"
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
