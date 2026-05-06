from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.data.loader import DEFAULT_RESORTS_PATH
from app.data.resort_acquisition.models import (
    CandidateFact,
    JsonValue,
    Proposal,
    ProposalTarget,
)

REPEATABLE_FIELD_PATHS = {"rental_facts"}
LIFT_PASS_PRICE_IDENTITY_FIELDS = (
    "duration_days",
    "audience",
    "currency",
    "season_label",
    "price_kind",
)
SEASON_WINDOW_IDENTITY_FIELDS = ("start_date", "end_date", "status")


def load_raw_catalog_by_resort(
    path: Path = DEFAULT_RESORTS_PATH,
) -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text())
    except OSError as error:
        raise ValueError(f"Unable to read resort data from {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}") from error

    if not isinstance(payload, list):
        raise ValueError("Resort catalog must be a top-level list")

    raw_catalog_by_resort: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise ValueError(f"Resort catalog entry {index} must be an object")
        resort_id = entry.get("resort_id")
        if not isinstance(resort_id, str) or not resort_id.strip():
            raise ValueError(f"Resort catalog entry {index} must include resort_id")
        raw_catalog_by_resort[resort_id] = entry

    return raw_catalog_by_resort


def build_proposals(
    raw_catalog_by_resort: dict[str, dict[str, Any]],
    candidates: list[CandidateFact],
) -> list[Proposal]:
    conflict_keys = _conflict_keys(candidates)
    proposals: list[Proposal] = []

    for candidate in candidates:
        resort_payload = raw_catalog_by_resort.get(candidate.resort_id, {})
        current_value, target_validation_notes = _get_target_field_path(
            resort_payload,
            candidate.target,
            candidate.field_path,
        )
        conflict_key = _candidate_conflict_key(candidate)
        validation_notes = [
            *candidate.validation_notes,
            *target_validation_notes,
        ]

        if candidate.validation_status == "rejected" or target_validation_notes:
            status = "rejected"
        elif candidate.validation_status == "warning":
            status = "warning"
        elif conflict_key is not None and conflict_key in conflict_keys:
            status = "conflict"
        elif _candidate_matches_current(current_value, candidate):
            status = "same"
        elif _candidate_is_new(current_value, candidate):
            status = "new"
        else:
            status = "changed"

        proposals.append(
            Proposal(
                resort_id=candidate.resort_id,
                target=candidate.target,
                field_path=candidate.field_path,
                current_value=current_value,
                proposed_value=candidate.proposed_value,
                status=status,
                source=candidate.source,
                extraction_method=candidate.extraction_method,
                confidence=candidate.confidence,
                evidence=candidate.evidence,
                validation_notes=validation_notes,
            )
        )

    return proposals


def _conflict_keys(candidates: list[CandidateFact]) -> set[tuple[Any, ...]]:
    values_by_key: dict[tuple[Any, ...], set[str]] = {}
    for candidate in candidates:
        if candidate.validation_status != "accepted":
            continue
        key = _candidate_conflict_key(candidate)
        if key is None:
            continue
        values_by_key.setdefault(key, set()).add(
            _candidate_value_compare_key(candidate)
        )

    return {key for key, values in values_by_key.items() if len(values) > 1}


def _candidate_conflict_key(candidate: CandidateFact) -> tuple[Any, ...] | None:
    if candidate.field_path in REPEATABLE_FIELD_PATHS:
        return None
    if candidate.field_path == "lift_pass_prices":
        if not isinstance(candidate.proposed_value, dict):
            return None
        identity = tuple(
            candidate.proposed_value.get(field)
            for field in LIFT_PASS_PRICE_IDENTITY_FIELDS
        )
        return (
            candidate.resort_id,
            candidate.target.entity_type,
            candidate.target.entity_id,
            candidate.field_path,
            *identity,
        )
    return (
        candidate.resort_id,
        candidate.target.entity_type,
        candidate.target.entity_id,
        candidate.field_path,
    )


def _get_target_field_path(
    resort_payload: dict[str, Any],
    target: ProposalTarget,
    field_path: str,
) -> tuple[JsonValue, list[str]]:
    if target.entity_type == "destination":
        return _get_field_path(resort_payload, field_path), []

    ski_area = _find_ski_area_payload(resort_payload, target.entity_id)
    if ski_area is None:
        return None, [
            f"Target ski_area '{target.entity_id}' not found in resort catalog"
        ]
    return _get_field_path(ski_area, field_path), []


def _get_field_path(payload: dict[str, Any], field_path: str) -> JsonValue:
    current: Any = payload
    for segment in field_path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _candidate_matches_current(
    current_value: JsonValue,
    candidate: CandidateFact,
) -> bool:
    if candidate.field_path == "season_windows" and isinstance(current_value, list):
        return any(
            _field_values_match(
                candidate.field_path,
                item,
                candidate.proposed_value,
            )
            for item in current_value
        )
    return current_value == candidate.proposed_value


def _candidate_is_new(current_value: JsonValue, candidate: CandidateFact) -> bool:
    if current_value is None:
        return True
    return candidate.field_path == "season_windows" and current_value == []


def _find_ski_area_payload(
    resort_payload: dict[str, Any],
    ski_area_id: str,
) -> dict[str, Any] | None:
    ski_areas = resort_payload.get("ski_areas")
    if not isinstance(ski_areas, list):
        return None
    for ski_area in ski_areas:
        if not isinstance(ski_area, dict):
            continue
        if ski_area.get("ski_area_id") == ski_area_id:
            return ski_area
    return None


def _json_compare_key(value: JsonValue) -> str:
    return json.dumps(value, sort_keys=True, allow_nan=False)


def _candidate_value_compare_key(candidate: CandidateFact) -> str:
    return _field_value_compare_key(candidate.field_path, candidate.proposed_value)


def _field_values_match(field_path: str, left: JsonValue, right: JsonValue) -> bool:
    if field_path == "season_windows":
        left_key = _season_window_identity_key(left)
        right_key = _season_window_identity_key(right)
        if left_key is not None and right_key is not None:
            return left_key == right_key
    return left == right


def _field_value_compare_key(field_path: str, value: JsonValue) -> str:
    if field_path == "season_windows":
        identity_key = _season_window_identity_key(value)
        if identity_key is not None:
            return identity_key
    return _json_compare_key(value)


def _season_window_identity_key(value: JsonValue) -> str | None:
    if not isinstance(value, dict):
        return None
    identity = {
        field: value.get(field)
        for field in SEASON_WINDOW_IDENTITY_FIELDS
        if value.get(field) is not None
    }
    if set(identity) != set(SEASON_WINDOW_IDENTITY_FIELDS):
        return None
    return _json_compare_key(identity)
