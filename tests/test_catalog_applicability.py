from dataclasses import fields
from datetime import date

import pytest

from app.domain.catalog import LiftPassProduct, SkiArea
from app.domain.catalog_applicability import (
    PARTIAL_COVERAGE_WARNING,
    UNVERIFIED_AREA_OPERATION_WARNING,
    UNVERIFIED_PASS_DATES_WARNING,
    PassCoverageProjection,
    candidate_is_applicable,
    evaluate_pass_validity,
    evaluate_ski_area_operation,
    project_pass_coverage,
    season_year_for_date,
)

pytestmark = pytest.mark.db_free


def _ski_area(
    ski_area_id: str = "focus-area",
    *,
    season_windows: tuple[dict[str, str], ...] = (),
    season_start_month: int = 10,
    season_end_month: int = 5,
) -> SkiArea:
    return SkiArea(
        ski_area_id=ski_area_id,
        name=ski_area_id,
        latitude=46.9,
        longitude=11.0,
        base_elevation_m=1700,
        summit_elevation_m=3200,
        season_start_month=season_start_month,
        season_end_month=season_end_month,
        season_windows=season_windows,
    )


def _pass(
    *,
    covered_ids: tuple[str, ...] = ("focus-area",),
    validity_windows: tuple[dict[str, str], ...] = (),
) -> LiftPassProduct:
    return LiftPassProduct(
        lift_pass_product_id="test-pass",
        name="Test Pass",
        validity_scope="regional_network",
        available_from_stay_destination_ids=("test-destination",),
        valid_ski_area_ids=covered_ids,
        validity_windows=validity_windows,
    )


def _window(
    start_date: str,
    end_date: str,
    *,
    status: str = "planned",
) -> dict[str, str]:
    return {
        "season_label": "ignored by applicability",
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
    }


def _projection(
    *,
    lift_pass_product: LiftPassProduct,
    areas: tuple[SkiArea, ...],
    focus_ski_area_id: str = "focus-area",
    pass_trust: str = "verified",
    area_trust: dict[str, str] | None = None,
    travel_month: int | None = None,
    trip_start_date: date | None = None,
    trip_end_date: date | None = None,
) -> PassCoverageProjection:
    return project_pass_coverage(
        lift_pass_product=lift_pass_product,
        focus_ski_area_id=focus_ski_area_id,
        contract_covered_ski_area_ids=lift_pass_product.valid_ski_area_ids,
        ski_areas_by_id={area.ski_area_id: area for area in areas},
        identity_scope_availability_trust_status=pass_trust,
        elevation_season_trust_by_ski_area_id=area_trust
        or {area.ski_area_id: "verified" for area in areas},
        travel_month=travel_month,
        trip_start_date=trip_start_date,
        trip_end_date=trip_end_date,
    )


def test_season_year_uses_the_area_season_start_for_both_sides_of_new_year() -> None:
    assert season_year_for_date(date(2026, 12, 1), 10) == 2026
    assert season_year_for_date(date(2027, 4, 1), 10) == 2026


@pytest.mark.parametrize(
    ("trip_start", "trip_end", "expected_validity", "expected_applicable"),
    [
        (date(2026, 12, 12), date(2026, 12, 18), "confirmed", True),
        (date(2026, 12, 29), date(2027, 1, 3), "inapplicable", False),
        (date(2026, 11, 10), date(2026, 11, 15), "inapplicable", False),
        (
            date(2027, 12, 12),
            date(2027, 12, 18),
            "unverified_for_requested_season",
            True,
        ),
    ],
)
def test_exact_pass_windows_require_complete_trip_containment_without_false_fallback(
    trip_start: date,
    trip_end: date,
    expected_validity: str,
    expected_applicable: bool,
) -> None:
    area = _ski_area(
        season_windows=(_window("2026-10-01", "2027-05-31"),),
    )
    projection = _projection(
        lift_pass_product=_pass(
            validity_windows=(_window("2026-12-01", "2026-12-31"),),
        ),
        areas=(area,),
        trip_start_date=trip_start,
        trip_end_date=trip_end,
    )

    assert projection.validity_status == expected_validity
    assert (
        candidate_is_applicable(
            projection=projection,
            focus_ski_area_id="focus-area",
        )
        is expected_applicable
    )


def test_post_main_winter_pass_window_matches_the_trip_season_by_window_start() -> None:
    area = _ski_area(
        season_windows=(_window("2026-10-01", "2027-05-31"),),
    )
    projection = _projection(
        lift_pass_product=_pass(
            validity_windows=(_window("2027-04-20", "2027-05-10"),),
        ),
        areas=(area,),
        trip_start_date=date(2027, 4, 25),
        trip_end_date=date(2027, 4, 29),
    )

    assert projection.validity_status == "confirmed"


@pytest.mark.parametrize(
    ("windows", "pass_trust", "expected"),
    [
        (
            (_window("2026-12-01", "2027-04-30", status="estimated"),),
            "verified",
            "unverified_for_requested_season",
        ),
        (
            (_window("2026-12-01", "2027-04-30"),),
            "estimated",
            "unverified_for_requested_season",
        ),
        (
            (
                _window("2026-12-01", "2027-04-30"),
                _window("2026-10-01", "2026-10-31", status="estimated"),
            ),
            "verified",
            "confirmed",
        ),
        (
            (
                _window("2026-10-01", "2026-10-31"),
                _window("2026-12-01", "2027-04-30", status="estimated"),
            ),
            "verified",
            "unverified_for_requested_season",
        ),
        (
            (
                _window("2026-10-01", "2026-10-31"),
                _window("2027-05-01", "2027-05-20"),
            ),
            "verified",
            "inapplicable",
        ),
    ],
)
def test_pass_evidence_authority_uses_cautious_same_season_precedence(
    windows: tuple[dict[str, str], ...],
    pass_trust: str,
    expected: str,
) -> None:
    area = _ski_area(
        season_windows=(_window("2026-10-01", "2027-05-31"),),
    )
    projection = _projection(
        lift_pass_product=_pass(validity_windows=windows),
        areas=(area,),
        pass_trust=pass_trust,
        trip_start_date=date(2027, 2, 10),
        trip_end_date=date(2027, 2, 15),
    )

    assert projection.validity_status == expected


def test_raw_pass_evaluator_never_parses_the_free_text_season_label() -> None:
    area = _ski_area()
    product = _pass(
        validity_windows=(
            {
                **_window("2027-04-01", "2027-05-15"),
                "season_label": "a misleading 2099 season label",
            },
        ),
    )

    assert (
        evaluate_pass_validity(
            lift_pass_product=product,
            ski_area=area,
            travel_month=None,
            trip_start_date=date(2027, 4, 10),
            trip_end_date=date(2027, 4, 12),
        )
        == "confirmed"
    )


@pytest.mark.parametrize(
    ("raw_window", "expected_raw"),
    [
        (_window("2026-10-01", "2027-05-31"), "operating"),
        (_window("2026-12-01", "2027-01-31"), "unavailable"),
    ],
)
def test_non_source_backed_area_seasons_never_confirm_or_exclude(
    raw_window: dict[str, str],
    expected_raw: str,
) -> None:
    area = _ski_area(season_windows=(raw_window,))
    raw_status = evaluate_ski_area_operation(
        ski_area=area,
        travel_month=None,
        trip_start_date=date(2027, 2, 10),
        trip_end_date=date(2027, 2, 15),
    )
    projection = _projection(
        lift_pass_product=_pass(),
        areas=(area,),
        area_trust={"focus-area": "estimated"},
        trip_start_date=date(2027, 2, 10),
        trip_end_date=date(2027, 2, 15),
    )

    assert raw_status == expected_raw
    assert projection.unverified_covered_ski_area_ids == ("focus-area",)
    assert projection.operating_covered_ski_area_ids == ()
    assert projection.unavailable_covered_ski_area_ids == ()
    assert candidate_is_applicable(
        projection=projection,
        focus_ski_area_id="focus-area",
    )


@pytest.mark.parametrize(
    ("windows", "expected"),
    [
        (
            (_window("2026-10-01", "2027-05-31", status="estimated"),),
            "unverified",
        ),
        (
            (
                _window("2026-10-01", "2026-10-31"),
                _window("2026-12-01", "2027-04-30", status="estimated"),
            ),
            "unverified",
        ),
        (
            (
                _window("2026-12-01", "2027-04-30"),
                _window("2026-10-01", "2026-10-31", status="estimated"),
            ),
            "operating",
        ),
    ],
)
def test_area_evidence_requires_a_planned_containing_window_to_confirm(
    windows: tuple[dict[str, str], ...],
    expected: str,
) -> None:
    assert (
        evaluate_ski_area_operation(
            ski_area=_ski_area(season_windows=windows),
            travel_month=None,
            trip_start_date=date(2027, 2, 10),
            trip_end_date=date(2027, 2, 15),
        )
        == expected
    )


def test_old_pass_dates_are_not_projected_into_the_future() -> None:
    area = _ski_area(
        season_windows=(_window("2027-10-01", "2028-05-31"),),
    )
    projection = _projection(
        lift_pass_product=_pass(
            validity_windows=(_window("2026-12-01", "2027-04-30"),),
        ),
        areas=(area,),
        trip_start_date=date(2028, 2, 10),
        trip_end_date=date(2028, 2, 15),
    )

    assert projection.validity_status == "unverified_for_requested_season"
    assert {field.name for field in fields(projection)} == {
        "validity_status",
        "coverage_status",
        "contract_covered_ski_area_ids",
        "operating_covered_ski_area_ids",
        "unavailable_covered_ski_area_ids",
        "unverified_covered_ski_area_ids",
        "warnings",
    }


@pytest.mark.parametrize(
    ("travel_month", "expected_status", "expected_applicable"),
    [
        (8, "unavailable", False),
        (2, "unverified", True),
    ],
)
def test_month_only_area_operation_is_cautious(
    travel_month: int,
    expected_status: str,
    expected_applicable: bool,
) -> None:
    area = _ski_area()
    projection = _projection(
        lift_pass_product=_pass(),
        areas=(area,),
        travel_month=travel_month,
    )

    assert (
        evaluate_ski_area_operation(
            ski_area=area,
            travel_month=travel_month,
            trip_start_date=None,
            trip_end_date=None,
        )
        == expected_status
    )
    assert (
        candidate_is_applicable(
            projection=projection,
            focus_ski_area_id="focus-area",
        )
        is expected_applicable
    )


def test_single_day_date_max_recurring_fallback_does_not_overflow() -> None:
    area = _ski_area(
        season_start_month=12,
        season_end_month=12,
    )

    assert (
        evaluate_ski_area_operation(
            ski_area=area,
            travel_month=None,
            trip_start_date=date.max,
            trip_end_date=date.max,
        )
        == "unverified"
    )


def test_no_travel_window_retains_candidate_without_date_specific_warnings() -> None:
    area = _ski_area()
    projection = _projection(
        lift_pass_product=_pass(
            validity_windows=(_window("2026-12-01", "2027-04-30"),),
        ),
        areas=(area,),
    )

    assert projection.validity_status == "unverified_for_requested_season"
    assert projection.coverage_status == "unverified"
    assert projection.warnings == ()
    assert candidate_is_applicable(
        projection=projection,
        focus_ski_area_id="focus-area",
    )


def test_undated_pass_is_retained_in_a_known_operating_window() -> None:
    area = _ski_area(
        season_windows=(_window("2026-10-01", "2027-05-31"),),
    )
    projection = _projection(
        lift_pass_product=_pass(),
        areas=(area,),
        trip_start_date=date(2027, 2, 10),
        trip_end_date=date(2027, 2, 15),
    )

    assert projection.validity_status == "not_constrained"
    assert projection.coverage_status == "full"
    assert projection.operating_covered_ski_area_ids == ("focus-area",)
    assert candidate_is_applicable(
        projection=projection,
        focus_ski_area_id="focus-area",
    )


def test_undated_pass_is_excluded_for_a_known_closed_focus_area() -> None:
    area = _ski_area(
        season_windows=(_window("2026-12-01", "2027-01-31"),),
    )
    projection = _projection(
        lift_pass_product=_pass(),
        areas=(area,),
        trip_start_date=date(2027, 2, 10),
        trip_end_date=date(2027, 2, 15),
    )

    assert projection.validity_status == "not_constrained"
    assert projection.unavailable_covered_ski_area_ids == ("focus-area",)
    assert not candidate_is_applicable(
        projection=projection,
        focus_ski_area_id="focus-area",
    )


@pytest.mark.parametrize(
    ("second_area", "second_trust", "expected_status", "expected_warnings"),
    [
        (
            _ski_area(
                "other-area",
                season_windows=(_window("2026-12-01", "2027-01-31"),),
            ),
            "verified",
            "partial",
            (PARTIAL_COVERAGE_WARNING,),
        ),
        (
            _ski_area(
                "other-area",
                season_windows=(_window("2026-10-01", "2027-05-31"),),
            ),
            "estimated",
            "unverified",
            (UNVERIFIED_AREA_OPERATION_WARNING,),
        ),
    ],
)
def test_coverage_distinguishes_partial_from_unverified_area_operation(
    second_area: SkiArea,
    second_trust: str,
    expected_status: str,
    expected_warnings: tuple[str, ...],
) -> None:
    focus = _ski_area(
        season_windows=(_window("2026-10-01", "2027-05-31"),),
    )
    product = _pass(covered_ids=("focus-area", "other-area"))
    projection = _projection(
        lift_pass_product=product,
        areas=(focus, second_area),
        area_trust={"focus-area": "verified", "other-area": second_trust},
        trip_start_date=date(2027, 2, 10),
        trip_end_date=date(2027, 2, 15),
    )

    assert projection.coverage_status == expected_status
    assert projection.warnings == expected_warnings


def test_all_covered_areas_closed_leaves_no_applicable_candidate() -> None:
    focus = _ski_area(
        season_windows=(_window("2026-12-01", "2027-01-31"),),
    )
    other = _ski_area(
        "other-area",
        season_windows=(_window("2026-11-01", "2027-01-15"),),
    )
    product = _pass(covered_ids=("focus-area", "other-area"))
    projection = _projection(
        lift_pass_product=product,
        areas=(focus, other),
        trip_start_date=date(2027, 2, 10),
        trip_end_date=date(2027, 2, 15),
    )

    assert projection.operating_covered_ski_area_ids == ()
    assert projection.unavailable_covered_ski_area_ids == (
        "focus-area",
        "other-area",
    )
    assert projection.coverage_status is None
    assert not candidate_is_applicable(
        projection=projection,
        focus_ski_area_id="focus-area",
    )


def test_pass_and_area_uncertainty_warnings_follow_the_fixed_order() -> None:
    area = _ski_area(
        season_windows=(_window("2026-10-01", "2027-05-31"),),
    )
    projection = _projection(
        lift_pass_product=_pass(
            validity_windows=(_window("2026-12-01", "2027-04-30", status="estimated"),),
        ),
        areas=(area,),
        area_trust={"focus-area": "needs_source"},
        trip_start_date=date(2027, 2, 10),
        trip_end_date=date(2027, 2, 15),
    )

    assert projection.warnings == (
        UNVERIFIED_PASS_DATES_WARNING,
        UNVERIFIED_AREA_OPERATION_WARNING,
    )
