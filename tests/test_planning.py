from datetime import date

from app.domain.models import SkiArea
from app.domain.planning import derive_planning_assessment


def test_exact_date_planning_uses_season_windows_before_month_fallback() -> None:
    resort = SkiArea(
        ski_area_id="test-glacier",
        name="Test Glacier",
        latitude=46.9,
        longitude=11.0,
        base_elevation_m=1700,
        summit_elevation_m=3200,
        season_start_month=10,
        season_end_month=5,
        season_windows=[
            {
                "season_label": "2025-2026",
                "start_date": "2025-12-01",
                "end_date": "2026-04-15",
                "status": "planned",
            }
        ],
    )

    assessment = derive_planning_assessment(
        resort=resort,
        trip_start_date=date(2025, 11, 20),
        trip_end_date=date(2025, 11, 23),
        snapshots=(),
    )
    month_only = derive_planning_assessment(
        resort=resort,
        travel_month=11,
        snapshots=(),
    )

    assert assessment.conditions.availability_status == "out_of_season"
    assert month_only.conditions.availability_status != "out_of_season"


def test_exact_date_planning_falls_back_to_months_for_unknown_future_season() -> None:
    resort = SkiArea(
        ski_area_id="test-glacier",
        name="Test Glacier",
        latitude=46.9,
        longitude=11.0,
        base_elevation_m=1700,
        summit_elevation_m=3200,
        season_start_month=10,
        season_end_month=5,
        season_windows=[
            {
                "season_label": "2025-2026",
                "start_date": "2025-10-03",
                "end_date": "2026-05-17",
                "status": "planned",
            }
        ],
    )

    assessment = derive_planning_assessment(
        resort=resort,
        trip_start_date=date(2026, 10, 20),
        trip_end_date=date(2026, 10, 23),
        snapshots=(),
    )

    assert assessment.conditions.availability_status != "out_of_season"
