from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from app.data.resort_acquisition.models import (
    CandidateFact,
    OfficialUrlRole,
    ProposalTarget,
    ResortSourceConfig,
    SourceReference,
)

OFFICIAL_ROLE_FIELD_PATHS: dict[OfficialUrlRole, str] = {
    "ski_area": "ski_area_official_url",
    "ski_pass": "ski_pass_url",
    "rental": "rental_url",
    "season_dates": "season_dates_url",
    "trail_map": "trail_map_url",
    "official_status": "official_status_url",
}


def extract_registry_candidates(
    resort_id: str,
    config: ResortSourceConfig,
    fetched_at: datetime,
) -> list[CandidateFact]:
    candidates: list[CandidateFact] = []

    for role, url in config.official_urls.items():
        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                field_path=OFFICIAL_ROLE_FIELD_PATHS[role],
                proposed_value=url,
                source=SourceReference(source_type="official", source_url=url),
                extraction_method="registry",
                fetched_at=fetched_at,
                confidence=1.0,
                evidence=f"Configured official {role} URL in source registry",
            )
        )

    catalog_source = SourceReference(
        source_type="catalog",
        source_name="source registry",
    )
    regional_ids = config.regional_data_ids
    regional_fields = (
        (
            "regional_data_ids.opendatahub_ski_area_id",
            regional_ids.opendatahub_ski_area_id,
        ),
        ("regional_data_ids.osm_relation_id", regional_ids.osm_relation_id),
        ("regional_data_ids.wikidata_id", regional_ids.wikidata_id),
        ("osm_relation_id", regional_ids.osm_relation_id),
        ("wikidata_id", regional_ids.wikidata_id),
    )
    for field_path, value in regional_fields:
        if value is not None:
            candidates.append(
                CandidateFact(
                    resort_id=resort_id,
                    field_path=field_path,
                    proposed_value=value,
                    source=catalog_source,
                    extraction_method="registry",
                    fetched_at=fetched_at,
                    confidence=1.0,
                    evidence=f"Configured {field_path} in source registry",
                )
            )

    return candidates


def extract_opendatahub_candidates(
    resort_id: str,
    config: ResortSourceConfig,
    payload: dict[str, Any],
    fetched_at: datetime,
    *,
    source_url: str,
    resort_payload: dict[str, Any] | None = None,
) -> list[CandidateFact]:
    license_info = payload.get("LicenseInfo")
    opendatahub_id = config.regional_data_ids.opendatahub_ski_area_id
    if (
        not isinstance(license_info, dict)
        or license_info.get("ClosedData") is not False
    ):
        return [
            CandidateFact(
                resort_id=resort_id,
                field_path="regional_data_ids.opendatahub_ski_area_id",
                proposed_value=opendatahub_id,
                source=SourceReference(
                    source_type="opendatahub", source_url=source_url
                ),
                extraction_method="opendatahub",
                fetched_at=fetched_at,
                confidence=0.0,
                validation_status="rejected",
                validation_notes=["OpenDataHub payload is not open data"],
                evidence="OpenDataHub payload is closed or missing license metadata",
            )
        ]

    source = SourceReference(
        source_type="opendatahub",
        source_url=source_url,
        license=license_info.get("License"),
    )
    candidates: list[CandidateFact] = []

    def add_candidate(
        field_path: str,
        proposed_value: Any,
        evidence: str,
        *,
        target: ProposalTarget | None = None,
    ) -> None:
        candidate_kwargs: dict[str, Any] = {}
        if target is not None:
            candidate_kwargs["target"] = target
        candidates.append(
            CandidateFact(
                resort_id=resort_id,
                field_path=field_path,
                proposed_value=proposed_value,
                source=source,
                extraction_method="opendatahub",
                fetched_at=fetched_at,
                confidence=0.95,
                evidence=(
                    f"{evidence}; License={license_info.get('License')}; "
                    "ClosedData=false"
                ),
                **candidate_kwargs,
            )
        )

    if opendatahub_id is not None:
        add_candidate(
            "regional_data_ids.opendatahub_ski_area_id",
            opendatahub_id,
            f"OpenDataHub Id={opendatahub_id}",
        )

    total_slope_km = _parse_float(payload.get("TotalSlopeKm"))
    if total_slope_km is not None:
        add_candidate(
            "total_piste_km",
            total_slope_km,
            f"OpenDataHub TotalSlopeKm={payload.get('TotalSlopeKm')}",
        )

    lift_count = _parse_int(payload.get("LiftCount"))
    if lift_count is not None:
        add_candidate(
            "total_lift_count",
            lift_count,
            f"OpenDataHub LiftCount={payload.get('LiftCount')}",
        )

    slope_km_blue = _parse_float(payload.get("SlopeKmBlue"))
    slope_km_red = _parse_float(payload.get("SlopeKmRed"))
    slope_km_black = _parse_float(payload.get("SlopeKmBlack"))
    if (
        slope_km_blue is not None
        and slope_km_red is not None
        and slope_km_black is not None
    ):
        add_candidate(
            "piste_km_by_difficulty",
            {
                "beginner": slope_km_blue,
                "intermediate": slope_km_red,
                "advanced": slope_km_black,
            },
            "OpenDataHub "
            f"SlopeKmBlue={payload.get('SlopeKmBlue')}, "
            f"SlopeKmRed={payload.get('SlopeKmRed')}, "
            f"SlopeKmBlack={payload.get('SlopeKmBlack')}",
        )

    ski_area_map_url = payload.get("SkiAreaMapURL")
    if isinstance(ski_area_map_url, str) and ski_area_map_url.strip():
        add_candidate(
            "trail_map_url",
            ski_area_map_url,
            f"OpenDataHub SkiAreaMapURL={ski_area_map_url}",
        )

    if resort_payload is not None:
        candidates.extend(
            _extract_existing_field_candidates(
                resort_id=resort_id,
                resort_payload=resort_payload,
                payload=payload,
                source=source,
                fetched_at=fetched_at,
                license_name=license_info.get("License"),
            )
        )

    return candidates


def _extract_existing_field_candidates(
    *,
    resort_id: str,
    resort_payload: dict[str, Any],
    payload: dict[str, Any],
    source: SourceReference,
    fetched_at: datetime,
    license_name: Any,
) -> list[CandidateFact]:
    ski_area_payload = _single_ski_area_payload(resort_payload)
    if ski_area_payload is None:
        return []

    ski_area_id = ski_area_payload.get("ski_area_id")
    if not isinstance(ski_area_id, str) or not ski_area_id.strip():
        return []

    field_values: list[tuple[str, JsonCandidateValue, str]] = []
    latitude = _parse_latitude(payload.get("Latitude"))
    if latitude is not None:
        field_values.append(
            ("latitude", latitude, f"OpenDataHub Latitude={payload.get('Latitude')}")
        )
    longitude = _parse_longitude(payload.get("Longitude"))
    if longitude is not None:
        field_values.append(
            (
                "longitude",
                longitude,
                f"OpenDataHub Longitude={payload.get('Longitude')}",
            )
        )
    altitude_from = _parse_int(payload.get("AltitudeFrom"))
    if altitude_from is not None:
        field_values.append(
            (
                "base_elevation_m",
                altitude_from,
                f"OpenDataHub AltitudeFrom={payload.get('AltitudeFrom')}",
            )
        )
    altitude_to = _parse_int(payload.get("AltitudeTo"))
    if altitude_to is not None:
        field_values.append(
            (
                "summit_elevation_m",
                altitude_to,
                f"OpenDataHub AltitudeTo={payload.get('AltitudeTo')}",
            )
        )

    season_months = _operation_schedule_months(payload.get("OperationSchedule"))
    if season_months is not None:
        start_month, end_month, evidence = season_months
        if start_month is not None:
            field_values.append(("season_start_month", start_month, evidence))
        if end_month is not None:
            field_values.append(("season_end_month", end_month, evidence))

    candidates: list[CandidateFact] = []
    ski_area_target = ProposalTarget(entity_type="ski_area", entity_id=ski_area_id)
    destination_target = ProposalTarget(
        entity_type="destination",
        entity_id=resort_id,
    )
    for field_path, proposed_value, evidence in field_values:
        candidates.append(
            _existing_field_candidate(
                resort_id=resort_id,
                target=ski_area_target,
                field_path=field_path,
                proposed_value=proposed_value,
                source=source,
                fetched_at=fetched_at,
                license_name=license_name,
                evidence=evidence,
            )
        )
        if _destination_field_is_single_ski_area_duplicate(
            resort_payload,
            ski_area_payload,
            field_path,
        ):
            candidates.append(
                _existing_field_candidate(
                    resort_id=resort_id,
                    target=destination_target,
                    field_path=field_path,
                    proposed_value=proposed_value,
                    source=source,
                    fetched_at=fetched_at,
                    license_name=license_name,
                    evidence=evidence,
                )
            )

    return candidates


JsonCandidateValue = str | int | float | bool | None | dict[str, Any] | list[Any]


def _existing_field_candidate(
    *,
    resort_id: str,
    target: ProposalTarget,
    field_path: str,
    proposed_value: JsonCandidateValue,
    source: SourceReference,
    fetched_at: datetime,
    license_name: Any,
    evidence: str,
) -> CandidateFact:
    return CandidateFact(
        resort_id=resort_id,
        target=target,
        field_path=field_path,
        proposed_value=proposed_value,
        source=source,
        extraction_method="opendatahub",
        fetched_at=fetched_at,
        confidence=0.95,
        evidence=f"{evidence}; License={license_name}; ClosedData=false",
    )


def _single_ski_area_payload(resort_payload: dict[str, Any]) -> dict[str, Any] | None:
    ski_areas = resort_payload.get("ski_areas")
    if not isinstance(ski_areas, list) or len(ski_areas) != 1:
        return None
    ski_area = ski_areas[0]
    return ski_area if isinstance(ski_area, dict) else None


def _destination_field_is_single_ski_area_duplicate(
    resort_payload: dict[str, Any],
    ski_area_payload: dict[str, Any],
    field_path: str,
) -> bool:
    return (
        field_path in resort_payload
        and field_path in ski_area_payload
        and resort_payload[field_path] == ski_area_payload[field_path]
    )


def _parse_latitude(value: Any) -> float | None:
    parsed = _parse_finite_float(value)
    if parsed is None or parsed < -90 or parsed > 90:
        return None
    return parsed


def _parse_longitude(value: Any) -> float | None:
    parsed = _parse_finite_float(value)
    if parsed is None or parsed < -180 or parsed > 180:
        return None
    return parsed


def _parse_finite_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _operation_schedule_months(
    value: Any,
) -> tuple[int | None, int | None, str] | None:
    if not isinstance(value, list):
        return None
    for schedule in value:
        if not isinstance(schedule, dict):
            continue
        start_value = schedule.get("Start")
        stop_value = schedule.get("Stop")
        start_month = _parse_iso_month(start_value)
        stop_month = _parse_iso_month(stop_value)
        if start_month is None and stop_month is None:
            continue
        return (
            start_month,
            stop_month,
            f"OpenDataHub OperationSchedule Start={start_value}, Stop={stop_value}",
        )
    return None


def _parse_iso_month(value: Any) -> int | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).month
    except ValueError:
        return None


def _parse_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < 0:
        return None
    return parsed


def _parse_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed_float = float(value)
    except (TypeError, ValueError):
        return None
    if (
        not math.isfinite(parsed_float)
        or parsed_float < 0
        or not parsed_float.is_integer()
    ):
        return None
    return int(parsed_float)
