import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.data.loader import DEFAULT_RESORTS_PATH, load_resorts_from_path

DEFAULT_TRUST_MANIFEST_PATH = Path(__file__).with_name("resort_trust_manifest.json")

TrustStatus = Literal[
    "verified", "verified_with_adjustment", "estimated", "needs_source"
]

TRUST_STATUSES: set[str] = {
    "verified",
    "verified_with_adjustment",
    "estimated",
    "needs_source",
}

SOURCE_BACKED_TRUST_STATUSES: set[str] = {"verified", "verified_with_adjustment"}
CATALOG_SELF_REFERENCE = "app/data/resorts.json"

REQUIRED_TRUST_FIELD_GROUPS: tuple[str, ...] = (
    "destination_identity",
    "country_region",
    "destination_coordinates",
    "destination_elevation",
    "season_window",
    "ski_areas",
    "stay_bases",
    "stay_base_quality_tier",
    "stay_base_lift_distance",
    "supported_skill_levels",
    "rental_examples",
    "rental_quality_tier",
    "price_ranges",
)


@dataclass(frozen=True)
class CatalogValidationReport:
    destination_count: int
    ski_area_count: int
    stay_base_count: int
    rental_count: int


class CatalogValidationError(ValueError):
    def __init__(self, issues: list[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("\n".join(issues))


def validate_catalog(
    *,
    resorts_path: Path = DEFAULT_RESORTS_PATH,
    trust_manifest_path: Path = DEFAULT_TRUST_MANIFEST_PATH,
) -> CatalogValidationReport:
    issues: list[str] = []

    raw_resorts = _read_json_list(resorts_path, issues, label="resort catalog")
    raw_manifest = _read_json_object(
        trust_manifest_path,
        issues,
        label="trust manifest",
    )
    if issues:
        raise CatalogValidationError(issues)

    assert raw_resorts is not None
    assert raw_manifest is not None

    _validate_raw_catalog(raw_resorts, issues)

    try:
        resorts = load_resorts_from_path(resorts_path)
    except ValueError as error:
        issues.append(str(error))
        resorts = []

    _validate_loaded_catalog(resorts, issues)
    _validate_trust_manifest(
        raw_manifest, {resort.resort_id for resort in resorts}, issues
    )

    if issues:
        raise CatalogValidationError(sorted(set(issues)))

    return CatalogValidationReport(
        destination_count=len(resorts),
        ski_area_count=sum(len(resort.ski_areas) for resort in resorts),
        stay_base_count=sum(len(resort.stay_bases) for resort in resorts),
        rental_count=sum(len(resort.rentals) for resort in resorts),
    )


def _read_json_list(path: Path, issues: list[str], *, label: str) -> list[Any] | None:
    payload = _read_json(path, issues, label=label)
    if payload is None:
        return None
    if not isinstance(payload, list):
        issues.append(f"{label} must be a JSON list")
        return None
    return payload


def _read_json_object(
    path: Path, issues: list[str], *, label: str
) -> dict[str, Any] | None:
    payload = _read_json(path, issues, label=label)
    if payload is None:
        return None
    if not isinstance(payload, dict):
        issues.append(f"{label} must be a JSON object")
        return None
    return payload


def _read_json(path: Path, issues: list[str], *, label: str) -> Any | None:
    try:
        return json.loads(path.read_text())
    except OSError as error:
        issues.append(f"Unable to read {label} at {path}: {error}")
    except json.JSONDecodeError as error:
        issues.append(f"Invalid JSON in {label} at {path}: {error}")
    return None


def _validate_raw_catalog(raw_resorts: list[Any], issues: list[str]) -> None:
    for index, raw in enumerate(raw_resorts):
        if not isinstance(raw, dict):
            issues.append(f"resort entry {index} must be an object")
            continue
        resort_id = str(raw.get("resort_id", f"<missing:{index}>"))
        if "areas" in raw:
            issues.append(f"{resort_id}: legacy 'areas' key is not allowed")
        if not raw.get("ski_areas"):
            issues.append(f"{resort_id}: explicit ski_areas are required")
        if not raw.get("stay_bases"):
            issues.append(f"{resort_id}: explicit stay_bases are required")


def _validate_loaded_catalog(resorts: list[Any], issues: list[str]) -> None:
    resort_ids: set[str] = set()
    ski_area_ids: set[str] = set()
    for resort in resorts:
        if resort.resort_id in resort_ids:
            issues.append(f"{resort.resort_id}: duplicate destination id")
        resort_ids.add(resort.resort_id)

        _validate_coordinates(
            resort.resort_id,
            latitude=resort.latitude,
            longitude=resort.longitude,
            issues=issues,
        )
        _validate_elevation(
            resort.resort_id,
            base=resort.base_elevation_m,
            summit=resort.summit_elevation_m,
            issues=issues,
        )

        for ski_area in resort.ski_areas:
            if ski_area.ski_area_id in ski_area_ids:
                issues.append(f"{ski_area.ski_area_id}: duplicate ski-area id")
            ski_area_ids.add(ski_area.ski_area_id)
            _validate_coordinates(
                ski_area.ski_area_id,
                latitude=ski_area.latitude,
                longitude=ski_area.longitude,
                issues=issues,
            )
            _validate_elevation(
                ski_area.ski_area_id,
                base=ski_area.base_elevation_m,
                summit=ski_area.summit_elevation_m,
                issues=issues,
            )


def _validate_coordinates(
    label: str,
    *,
    latitude: float,
    longitude: float,
    issues: list[str],
) -> None:
    if not (35 <= latitude <= 55 and -10 <= longitude <= 30):
        issues.append(f"{label}: coordinates are outside the current Europe/Alps range")


def _validate_elevation(
    label: str,
    *,
    base: int,
    summit: int,
    issues: list[str],
) -> None:
    if base <= 0 or summit <= 0:
        issues.append(f"{label}: elevations must be positive")
    if summit <= base:
        issues.append(f"{label}: summit elevation must be above base elevation")
    if summit > 5000:
        issues.append(f"{label}: summit elevation is implausible for current catalog")


def _validate_trust_manifest(
    manifest: dict[str, Any],
    resort_ids: set[str],
    issues: list[str],
) -> None:
    manifest_destinations = manifest.get("destinations")
    if not isinstance(manifest_destinations, dict):
        issues.append("trust manifest must contain destinations object")
        return

    manifest_ids = set(manifest_destinations)
    for missing in sorted(resort_ids - manifest_ids):
        issues.append(f"{missing}: missing trust manifest entry")
    for extra in sorted(manifest_ids - resort_ids):
        issues.append(f"{extra}: trust manifest entry has no catalog destination")

    manifest_groups = manifest.get("field_groups")
    if tuple(manifest_groups or ()) != REQUIRED_TRUST_FIELD_GROUPS:
        issues.append("trust manifest field_groups do not match required contract")

    for resort_id, entry in manifest_destinations.items():
        if not isinstance(entry, dict):
            issues.append(f"{resort_id}: trust manifest entry must be an object")
            continue
        field_statuses = entry.get("field_statuses")
        if not isinstance(field_statuses, dict):
            issues.append(f"{resort_id}: field_statuses must be an object")
            continue
        source_refs = _validate_source_refs(resort_id, entry.get("source_refs"), issues)
        has_source_backed_status = False
        for group in REQUIRED_TRUST_FIELD_GROUPS:
            status = field_statuses.get(group)
            if status not in TRUST_STATUSES:
                issues.append(
                    f"{resort_id}: {group} has invalid trust status {status!r}"
                )
                continue
            if status in SOURCE_BACKED_TRUST_STATUSES:
                has_source_backed_status = True
        if has_source_backed_status and not (source_refs - {CATALOG_SELF_REFERENCE}):
            issues.append(
                f"{resort_id}: verified trust statuses require source_refs beyond "
                f"{CATALOG_SELF_REFERENCE}"
            )


def _validate_source_refs(
    resort_id: str,
    raw_source_refs: Any,
    issues: list[str],
) -> set[str]:
    if raw_source_refs is None:
        return set()
    if not isinstance(raw_source_refs, list):
        issues.append(f"{resort_id}: source_refs must be a list when provided")
        return set()

    source_refs: set[str] = set()
    for index, source_ref in enumerate(raw_source_refs):
        if not isinstance(source_ref, str) or not source_ref.strip():
            issues.append(
                f"{resort_id}: source_refs[{index}] must be a non-empty string"
            )
            continue
        source_refs.add(source_ref)
    return source_refs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Snowcast resort catalog and trust manifest."
    )
    parser.add_argument("--resorts-path", type=Path, default=DEFAULT_RESORTS_PATH)
    parser.add_argument(
        "--trust-manifest-path",
        type=Path,
        default=DEFAULT_TRUST_MANIFEST_PATH,
    )
    args = parser.parse_args()

    try:
        report = validate_catalog(
            resorts_path=args.resorts_path,
            trust_manifest_path=args.trust_manifest_path,
        )
    except CatalogValidationError as error:
        for issue in error.issues:
            print(f"[catalog-invalid] {issue}")
        return 1

    print(
        "[catalog-valid] "
        f"destinations={report.destination_count} "
        f"ski_areas={report.ski_area_count} "
        f"stay_bases={report.stay_base_count} "
        f"rentals={report.rental_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
