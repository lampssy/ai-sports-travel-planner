from __future__ import annotations

from typing import Any, Literal

from app.data.resort_acquisition.models import ProposalTarget

PrimaryEntityType = Literal["destination", "ski_area"]


def single_ski_area_payload(resort_payload: dict[str, Any]) -> dict[str, Any] | None:
    ski_areas = resort_payload.get("ski_areas")
    if not isinstance(ski_areas, list) or len(ski_areas) != 1:
        return None
    ski_area = ski_areas[0]
    return ski_area if isinstance(ski_area, dict) else None


def proposal_targets_for_single_area_source(
    *,
    resort_id: str,
    resort_payload: dict[str, Any],
    field_path: str,
    primary_entity_type: PrimaryEntityType,
) -> list[ProposalTarget]:
    targets: list[ProposalTarget] = []
    ski_area = single_ski_area_payload(resort_payload)
    ski_area_id = _ski_area_id(ski_area)
    if primary_entity_type == "destination":
        targets.append(ProposalTarget(entity_type="destination", entity_id=resort_id))
        if ski_area_id is not None and _can_mirror(
            resort_payload, ski_area, field_path
        ):
            targets.append(
                ProposalTarget(
                    entity_type="ski_area",
                    entity_id=ski_area_id,
                )
            )
        return targets

    if ski_area_id is None:
        return []
    targets.append(ProposalTarget(entity_type="ski_area", entity_id=ski_area_id))
    if _can_mirror(resort_payload, ski_area, field_path):
        targets.append(ProposalTarget(entity_type="destination", entity_id=resort_id))
    return targets


def _can_mirror(
    resort_payload: dict[str, Any],
    ski_area: dict[str, Any] | None,
    field_path: str,
) -> bool:
    return (
        ski_area is not None
        and _ski_area_id(ski_area) is not None
        and field_path in resort_payload
        and field_path in ski_area
        and resort_payload[field_path] == ski_area[field_path]
    )


def _ski_area_id(ski_area: dict[str, Any] | None) -> str | None:
    if ski_area is None:
        return None
    ski_area_id = ski_area.get("ski_area_id")
    if not isinstance(ski_area_id, str) or not ski_area_id.strip():
        return None
    return ski_area_id
