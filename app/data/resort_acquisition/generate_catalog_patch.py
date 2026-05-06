from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from app.data.loader import DEFAULT_RESORTS_PATH
from app.data.resort_acquisition.models import AcquisitionRunOutput, Proposal
from app.data.resort_acquisition.registry import DEFAULT_SOURCE_REGISTRY_PATH

PatchAction = Literal["applied", "skipped"]

SOURCE_FIELD_TO_ROLE = {
    "ski_area_official_url": "ski_area",
    "ski_pass_url": "ski_pass",
    "rental_url": "rental",
    "season_dates_url": "season_dates",
    "trail_map_url": "trail_map",
    "official_status_url": "official_status",
}
REGIONAL_ID_PREFIX = "regional_data_ids."
SKI_AREA_TERRAIN_FIELDS = {
    "total_piste_km",
    "total_lift_count",
    "piste_km_by_difficulty",
}
AUTO_APPLY_PRICE_DURATIONS = {1, 3, 6}
PRICE_CATALOG_FIELDS = {
    "duration_days",
    "audience",
    "amount",
    "amount_min",
    "amount_max",
    "currency",
    "price_kind",
    "season_label",
    "source_url",
}
SEASON_WINDOW_IDENTITY_FIELDS = ("start_date", "end_date", "status")


@dataclass(frozen=True)
class PatchRecord:
    action: PatchAction
    resort_id: str
    target: str
    field_path: str
    reason: str


@dataclass(frozen=True)
class PatchResult:
    applied_count: int
    skipped_count: int
    changed_files: tuple[str, ...]
    records: tuple[PatchRecord, ...] = field(default_factory=tuple)


def apply_catalog_patch(
    *,
    artifacts_dir: Path,
    catalog_path: Path = DEFAULT_RESORTS_PATH,
    registry_path: Path = DEFAULT_SOURCE_REGISTRY_PATH,
) -> PatchResult:
    output = _load_acquisition_output(artifacts_dir / "proposals.json")
    catalog_payload = _read_json_list(catalog_path, label="catalog")
    registry_payload = _read_json_object(registry_path, label="source registry")

    catalog_changed = False
    registry_changed = False
    records: list[PatchRecord] = []

    for proposal in output.proposals:
        record, changed_file = _apply_proposal(
            proposal=proposal,
            catalog_payload=catalog_payload,
            registry_payload=registry_payload,
        )
        records.append(record)
        if changed_file == "catalog":
            catalog_changed = True
        elif changed_file == "registry":
            registry_changed = True

    if catalog_changed:
        _write_json(catalog_path, catalog_payload)
    if registry_changed:
        _write_json(registry_path, registry_payload)

    changed_files = tuple(
        path
        for path, changed in (
            (str(catalog_path), catalog_changed),
            (str(registry_path), registry_changed),
        )
        if changed
    )
    result = PatchResult(
        applied_count=sum(1 for record in records if record.action == "applied"),
        skipped_count=sum(1 for record in records if record.action == "skipped"),
        changed_files=changed_files,
        records=tuple(records),
    )
    (artifacts_dir / "patch-review.md").write_text(
        render_patch_review(result),
        encoding="utf-8",
    )
    return result


def render_patch_review(result: PatchResult) -> str:
    lines = [
        "# Catalog Acquisition Patch Review",
        "",
        f"Applied changes: `{result.applied_count}`",
        f"Skipped proposals: `{result.skipped_count}`",
        "",
    ]
    if result.changed_files:
        lines.append("Changed files:")
        lines.extend(f"- `{path}`" for path in result.changed_files)
        lines.append("")

    applied = [record for record in result.records if record.action == "applied"]
    skipped = [record for record in result.records if record.action == "skipped"]
    lines.extend(_record_section("Applied", applied))
    lines.extend(_record_section("Skipped", skipped))
    return "\n".join(lines).rstrip() + "\n"


def _record_section(title: str, records: list[PatchRecord]) -> list[str]:
    lines = [f"## {title}", ""]
    if not records:
        return [*lines, "(none)", ""]
    for record in records:
        lines.append(
            "- "
            f"resort=`{record.resort_id}`; "
            f"target=`{record.target}`; "
            f"field=`{record.field_path}`; "
            f"reason={record.reason}"
        )
    lines.append("")
    return lines


def _apply_proposal(
    *,
    proposal: Proposal,
    catalog_payload: list[Any],
    registry_payload: dict[str, Any],
) -> tuple[PatchRecord, str | None]:
    target_label = f"{proposal.target.entity_type}:{proposal.target.entity_id}"
    if proposal.status != "new":
        return (
            _skipped(
                proposal,
                reason=f"{proposal.status} status is review-only",
            ),
            None,
        )

    if proposal.field_path in SOURCE_FIELD_TO_ROLE:
        changed = _apply_source_url(registry_payload, proposal)
        return (
            _applied_or_skipped(
                proposal,
                changed=changed,
                applied_reason="filled missing source registry official URL",
                skipped_reason="source registry official URL already set",
            ),
            "registry" if changed else None,
        )

    if proposal.field_path.startswith(REGIONAL_ID_PREFIX):
        changed = _apply_regional_id(registry_payload, proposal)
        return (
            _applied_or_skipped(
                proposal,
                changed=changed,
                applied_reason="filled missing source registry regional ID",
                skipped_reason="source registry regional ID already set",
            ),
            "registry" if changed else None,
        )

    if proposal.field_path in SKI_AREA_TERRAIN_FIELDS:
        changed, reason = _apply_ski_area_field(catalog_payload, proposal)
        return (
            _applied_or_skipped(
                proposal,
                changed=changed,
                applied_reason="filled missing ski-area terrain field",
                skipped_reason=reason,
            ),
            "catalog" if changed else None,
        )

    if proposal.field_path == "season_windows":
        changed, reason = _append_season_window(catalog_payload, proposal)
        return (
            _applied_or_skipped(
                proposal,
                changed=changed,
                applied_reason="appended missing season window",
                skipped_reason=reason,
            ),
            "catalog" if changed else None,
        )

    if proposal.field_path == "lift_pass_prices":
        changed, reason = _append_lift_pass_price(catalog_payload, proposal)
        return (
            _applied_or_skipped(
                proposal,
                changed=changed,
                applied_reason="appended reviewed lift-pass price",
                skipped_reason=reason,
            ),
            "catalog" if changed else None,
        )

    return (
        PatchRecord(
            action="skipped",
            resort_id=proposal.resort_id,
            target=target_label,
            field_path=proposal.field_path,
            reason="unsupported field path",
        ),
        None,
    )


def _apply_source_url(
    registry_payload: dict[str, Any],
    proposal: Proposal,
) -> bool:
    if not isinstance(proposal.proposed_value, str) or not proposal.proposed_value:
        return False
    role = SOURCE_FIELD_TO_ROLE[proposal.field_path]
    config = _registry_resort_config(registry_payload, proposal.resort_id)
    official_urls = config.setdefault("official_urls", {})
    if not isinstance(official_urls, dict) or official_urls.get(role):
        return False
    official_urls[role] = proposal.proposed_value
    return True


def _apply_regional_id(
    registry_payload: dict[str, Any],
    proposal: Proposal,
) -> bool:
    if not isinstance(proposal.proposed_value, str) or not proposal.proposed_value:
        return False
    field_name = proposal.field_path.removeprefix(REGIONAL_ID_PREFIX)
    config = _registry_resort_config(registry_payload, proposal.resort_id)
    regional_ids = config.setdefault("regional_data_ids", {})
    if not isinstance(regional_ids, dict) or regional_ids.get(field_name):
        return False
    regional_ids[field_name] = proposal.proposed_value
    return True


def _apply_ski_area_field(
    catalog_payload: list[Any],
    proposal: Proposal,
) -> tuple[bool, str]:
    if proposal.target.entity_type != "ski_area":
        return False, "terrain facts must target ski_area"
    ski_area = _find_ski_area(
        catalog_payload,
        proposal.resort_id,
        proposal.target.entity_id,
    )
    if ski_area is None:
        return False, "target ski_area not found"
    if ski_area.get(proposal.field_path) is not None:
        return False, "ski-area field already set"
    ski_area[proposal.field_path] = proposal.proposed_value
    return True, ""


def _append_season_window(
    catalog_payload: list[Any],
    proposal: Proposal,
) -> tuple[bool, str]:
    if not isinstance(proposal.proposed_value, dict):
        return False, "season window proposal is not an object"
    target_payload = _find_target_payload(catalog_payload, proposal)
    if target_payload is None:
        return False, "target entity not found"
    windows = target_payload.setdefault("season_windows", [])
    if not isinstance(windows, list):
        return False, "season_windows is not a list"
    if any(_same_season_window(window, proposal.proposed_value) for window in windows):
        return False, "season window already present"
    windows.append(proposal.proposed_value)
    return True, ""


def _append_lift_pass_price(
    catalog_payload: list[Any],
    proposal: Proposal,
) -> tuple[bool, str]:
    if proposal.target.entity_type != "destination":
        return False, "lift-pass prices must target destination"
    if proposal.extraction_method != "official_page_llm":
        return False, "lift-pass prices must come from official-page LLM extraction"
    if proposal.source.source_type != "official":
        return False, "lift-pass prices must come from official sources"
    if not isinstance(proposal.proposed_value, dict):
        return False, "lift-pass price proposal is not an object"
    if not _supported_price_duration(proposal.proposed_value):
        return False, "lift-pass price duration is not auto-applied"

    price = {
        key: value
        for key, value in proposal.proposed_value.items()
        if key in PRICE_CATALOG_FIELDS and value is not None
    }
    try:
        _validate_price_shape(price)
    except ValueError as error:
        return False, str(error)

    resort = _find_resort(catalog_payload, proposal.resort_id)
    if resort is None:
        return False, "target destination not found"
    prices = resort.setdefault("lift_pass_prices", [])
    if not isinstance(prices, list):
        return False, "lift_pass_prices is not a list"
    if any(_price_identity(existing) == _price_identity(price) for existing in prices):
        return False, "lift-pass price already present"
    prices.append(price)
    return True, ""


def _supported_price_duration(value: dict[str, Any]) -> bool:
    duration_days = value.get("duration_days")
    return (
        isinstance(duration_days, int) and duration_days in AUTO_APPLY_PRICE_DURATIONS
    )


def _validate_price_shape(price: dict[str, Any]) -> None:
    required = {"duration_days", "audience", "currency", "price_kind"}
    missing = sorted(required - set(price))
    if missing:
        raise ValueError(f"lift-pass price missing fields: {', '.join(missing)}")
    price_kind = price["price_kind"]
    if price_kind == "range":
        if "amount" in price:
            raise ValueError("range prices cannot include amount")
        if "amount_min" not in price or "amount_max" not in price:
            raise ValueError("range prices require amount_min and amount_max")
        return
    if price_kind in {"fixed", "from"}:
        if "amount" not in price:
            raise ValueError("fixed and from prices require amount")
        if "amount_min" in price or "amount_max" in price:
            raise ValueError("fixed and from prices cannot include range amounts")
        return
    if price_kind == "unknown":
        if {"amount", "amount_min", "amount_max"} & set(price):
            raise ValueError("unknown prices cannot include amount values")
        return
    raise ValueError(f"unsupported price_kind: {price_kind}")


def _price_identity(price: Any) -> tuple[Any, ...] | None:
    if not isinstance(price, dict):
        return None
    return (
        price.get("duration_days"),
        str(price.get("audience", "")).lower(),
        price.get("currency"),
        price.get("season_label"),
        price.get("price_kind"),
    )


def _registry_resort_config(
    registry_payload: dict[str, Any],
    resort_id: str,
) -> dict[str, Any]:
    resorts = registry_payload.setdefault("resorts", {})
    if not isinstance(resorts, dict):
        raise ValueError("source registry resorts must be an object")
    config = resorts.setdefault(resort_id, {})
    if not isinstance(config, dict):
        raise ValueError(f"source registry resort entry must be an object: {resort_id}")
    config.setdefault("official_urls", {})
    return config


def _find_target_payload(
    catalog_payload: list[Any],
    proposal: Proposal,
) -> dict[str, Any] | None:
    if proposal.target.entity_type == "destination":
        return _find_resort(catalog_payload, proposal.resort_id)
    return _find_ski_area(
        catalog_payload,
        proposal.resort_id,
        proposal.target.entity_id,
    )


def _find_resort(catalog_payload: list[Any], resort_id: str) -> dict[str, Any] | None:
    for resort in catalog_payload:
        if isinstance(resort, dict) and resort.get("resort_id") == resort_id:
            return resort
    return None


def _find_ski_area(
    catalog_payload: list[Any],
    resort_id: str,
    ski_area_id: str,
) -> dict[str, Any] | None:
    resort = _find_resort(catalog_payload, resort_id)
    if resort is None:
        return None
    ski_areas = resort.get("ski_areas")
    if not isinstance(ski_areas, list):
        return None
    for ski_area in ski_areas:
        if isinstance(ski_area, dict) and ski_area.get("ski_area_id") == ski_area_id:
            return ski_area
    return None


def _applied_or_skipped(
    proposal: Proposal,
    *,
    changed: bool,
    applied_reason: str,
    skipped_reason: str,
) -> PatchRecord:
    if changed:
        return PatchRecord(
            action="applied",
            resort_id=proposal.resort_id,
            target=f"{proposal.target.entity_type}:{proposal.target.entity_id}",
            field_path=proposal.field_path,
            reason=applied_reason,
        )
    return _skipped(proposal, reason=skipped_reason)


def _skipped(proposal: Proposal, *, reason: str) -> PatchRecord:
    return PatchRecord(
        action="skipped",
        resort_id=proposal.resort_id,
        target=f"{proposal.target.entity_type}:{proposal.target.entity_id}",
        field_path=proposal.field_path,
        reason=reason,
    )


def _load_acquisition_output(path: Path) -> AcquisitionRunOutput:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return AcquisitionRunOutput.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ValueError(f"could not read acquisition proposals: {path}") from error


def _read_json_list(path: Path, *, label: str) -> list[Any]:
    payload = _read_json(path, label=label)
    if not isinstance(payload, list):
        raise ValueError(f"{label} must be a JSON list")
    return payload


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    payload = _read_json(path, label=label)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _read_json(path: Path, *, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read {label}: {path}") from error


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _same_season_window(left: Any, right: Any) -> bool:
    left_key = _season_window_identity_key(left)
    right_key = _season_window_identity_key(right)
    if left_key is not None and right_key is not None:
        return left_key == right_key
    return left == right


def _season_window_identity_key(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    identity = {
        field: value.get(field)
        for field in SEASON_WINDOW_IDENTITY_FIELDS
        if value.get(field) is not None
    }
    if set(identity) != set(SEASON_WINDOW_IDENTITY_FIELDS):
        return None
    return json.dumps(identity, sort_keys=True, allow_nan=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Apply conservative catalog acquisition proposals to local JSON files."
        )
    )
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument("--catalog-path", type=Path, default=DEFAULT_RESORTS_PATH)
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=DEFAULT_SOURCE_REGISTRY_PATH,
    )
    args = parser.parse_args(argv)

    result = apply_catalog_patch(
        artifacts_dir=args.artifacts_dir,
        catalog_path=args.catalog_path,
        registry_path=args.registry_path,
    )
    print(
        f"Applied {result.applied_count} catalog acquisition proposals; "
        f"skipped {result.skipped_count}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
