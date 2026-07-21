from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from app.domain.catalog import LiftPassProduct, SkiArea
from app.domain.catalog_trust import Status

AreaOperationStatus = Literal["operating", "unavailable", "unverified"]
PassValidityStatus = Literal[
    "not_constrained",
    "confirmed",
    "unverified_for_requested_season",
    "inapplicable",
]
PassCoverageStatus = Literal["full", "partial", "unverified"]

PARTIAL_COVERAGE_WARNING = (
    "Some areas covered by this pass are outside their operating season for "
    "your dates. The published full-network terrain is not date-adjusted."
)
UNVERIFIED_PASS_DATES_WARNING = (
    "Exact pass dates are not yet confirmed for this season."
)
UNVERIFIED_AREA_OPERATION_WARNING = (
    "Operation dates are not confirmed for every area covered by this pass."
)

_SOURCE_BACKED_STATUSES = frozenset({"verified", "verified_with_adjustment"})


@dataclass(frozen=True)
class PassCoverageProjection:
    validity_status: PassValidityStatus
    coverage_status: PassCoverageStatus
    contract_covered_ski_area_ids: tuple[str, ...]
    operating_covered_ski_area_ids: tuple[str, ...]
    unavailable_covered_ski_area_ids: tuple[str, ...]
    unverified_covered_ski_area_ids: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def season_year_for_date(value: date, season_start_month: int) -> int:
    return value.year if value.month >= season_start_month else value.year - 1


def evaluate_ski_area_operation(
    *,
    ski_area: SkiArea,
    travel_month: int | None,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> AreaOperationStatus:
    if trip_start_date is not None and trip_end_date is not None:
        requested_season_year = season_year_for_date(
            trip_start_date,
            ski_area.season_start_month,
        )
        matching_windows = tuple(
            window
            for window in ski_area.season_windows
            if season_year_for_date(
                window.start_date,
                ski_area.season_start_month,
            )
            == requested_season_year
        )
        if any(
            window.status == "planned"
            and window.start_date <= trip_start_date
            and trip_end_date <= window.end_date
            for window in matching_windows
        ):
            return "operating"
        if any(window.status != "planned" for window in matching_windows):
            return "unverified"
        if matching_windows:
            return "unavailable"
        if _all_trip_dates_are_in_recurring_season(
            trip_start_date=trip_start_date,
            trip_end_date=trip_end_date,
            season_start_month=ski_area.season_start_month,
            season_end_month=ski_area.season_end_month,
        ):
            return "unverified"
        return "unavailable"

    if travel_month is None:
        return "unverified"
    if _is_month_in_season(
        travel_month,
        ski_area.season_start_month,
        ski_area.season_end_month,
    ):
        return "unverified"
    return "unavailable"


def evaluate_pass_validity(
    *,
    lift_pass_product: LiftPassProduct,
    ski_area: SkiArea,
    travel_month: int | None,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> PassValidityStatus:
    if not lift_pass_product.validity_windows:
        return "not_constrained"
    if trip_start_date is None or trip_end_date is None:
        return "unverified_for_requested_season"

    requested_season_year = season_year_for_date(
        trip_start_date,
        ski_area.season_start_month,
    )
    matching_windows = tuple(
        window
        for window in lift_pass_product.validity_windows
        if season_year_for_date(
            window.start_date,
            ski_area.season_start_month,
        )
        == requested_season_year
    )
    if any(
        window.status == "planned"
        and window.start_date <= trip_start_date
        and trip_end_date <= window.end_date
        for window in matching_windows
    ):
        return "confirmed"
    if any(window.status != "planned" for window in matching_windows):
        return "unverified_for_requested_season"
    if matching_windows:
        return "inapplicable"
    return "unverified_for_requested_season"


def project_pass_coverage(
    *,
    lift_pass_product: LiftPassProduct,
    focus_ski_area_id: str,
    contract_covered_ski_area_ids: tuple[str, ...],
    ski_areas_by_id: Mapping[str, SkiArea],
    identity_scope_availability_trust_status: Status,
    elevation_season_trust_by_ski_area_id: Mapping[str, Status],
    travel_month: int | None,
    trip_start_date: date | None,
    trip_end_date: date | None,
) -> PassCoverageProjection:
    focus_ski_area = ski_areas_by_id[focus_ski_area_id]
    validity_status = evaluate_pass_validity(
        lift_pass_product=lift_pass_product,
        ski_area=focus_ski_area,
        travel_month=travel_month,
        trip_start_date=trip_start_date,
        trip_end_date=trip_end_date,
    )
    if (
        lift_pass_product.validity_windows
        and identity_scope_availability_trust_status not in _SOURCE_BACKED_STATUSES
    ):
        validity_status = "unverified_for_requested_season"

    operating_ids: list[str] = []
    unavailable_ids: list[str] = []
    unverified_ids: list[str] = []
    for ski_area_id in contract_covered_ski_area_ids:
        operation_status = evaluate_ski_area_operation(
            ski_area=ski_areas_by_id[ski_area_id],
            travel_month=travel_month,
            trip_start_date=trip_start_date,
            trip_end_date=trip_end_date,
        )
        if (
            elevation_season_trust_by_ski_area_id[ski_area_id]
            not in _SOURCE_BACKED_STATUSES
        ):
            operation_status = "unverified"

        if operation_status == "operating":
            operating_ids.append(ski_area_id)
        elif operation_status == "unavailable":
            unavailable_ids.append(ski_area_id)
        else:
            unverified_ids.append(ski_area_id)

    coverage_status = _coverage_status(
        operating_ids=operating_ids,
        unavailable_ids=unavailable_ids,
        unverified_ids=unverified_ids,
    )
    warnings = _coverage_warnings(
        validity_status=validity_status,
        operating_ids=operating_ids,
        unavailable_ids=unavailable_ids,
        unverified_ids=unverified_ids,
        has_travel_window=(
            travel_month is not None
            or (trip_start_date is not None and trip_end_date is not None)
        ),
    )
    return PassCoverageProjection(
        validity_status=validity_status,
        coverage_status=coverage_status,
        contract_covered_ski_area_ids=contract_covered_ski_area_ids,
        operating_covered_ski_area_ids=tuple(operating_ids),
        unavailable_covered_ski_area_ids=tuple(unavailable_ids),
        unverified_covered_ski_area_ids=tuple(unverified_ids),
        warnings=warnings,
    )


def candidate_is_applicable(
    *,
    projection: PassCoverageProjection,
    focus_ski_area_id: str,
) -> bool:
    return (
        projection.validity_status != "inapplicable"
        and focus_ski_area_id not in projection.unavailable_covered_ski_area_ids
    )


def _all_trip_dates_are_in_recurring_season(
    *,
    trip_start_date: date,
    trip_end_date: date,
    season_start_month: int,
    season_end_month: int,
) -> bool:
    current_date = trip_start_date
    while current_date <= trip_end_date:
        if not _is_month_in_season(
            current_date.month,
            season_start_month,
            season_end_month,
        ):
            return False
        current_date += timedelta(days=1)
    return True


def _is_month_in_season(month: int, start_month: int, end_month: int) -> bool:
    if start_month <= end_month:
        return start_month <= month <= end_month
    return month >= start_month or month <= end_month


def _coverage_status(
    *,
    operating_ids: list[str],
    unavailable_ids: list[str],
    unverified_ids: list[str],
) -> PassCoverageStatus:
    if unverified_ids:
        return "unverified"
    if unavailable_ids:
        return "partial"
    if operating_ids:
        return "full"
    return "unverified"


def _coverage_warnings(
    *,
    validity_status: PassValidityStatus,
    operating_ids: list[str],
    unavailable_ids: list[str],
    unverified_ids: list[str],
    has_travel_window: bool,
) -> tuple[str, ...]:
    if not has_travel_window:
        return ()

    include_partial_warning = bool(operating_ids and unavailable_ids)
    include_pass_warning = validity_status == "unverified_for_requested_season"
    include_area_warning = bool(unverified_ids)
    return tuple(
        warning
        for warning, include in (
            (PARTIAL_COVERAGE_WARNING, include_partial_warning),
            (UNVERIFIED_PASS_DATES_WARNING, include_pass_warning),
            (UNVERIFIED_AREA_OPERATION_WARNING, include_area_warning),
        )
        if include
    )
