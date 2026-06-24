from app.domain.scoring_scenarios import (
    SCORING_SCENARIOS,
    SCORING_SCENARIOS_BY_ID,
)


def test_scoring_scenarios_cover_initial_golden_set() -> None:
    assert isinstance(SCORING_SCENARIOS, tuple)
    assert [scenario.scenario_id for scenario in SCORING_SCENARIOS] == [
        "snow_sure_late_season_intermediate",
        "beginner_first_trip_low_hassle",
        "family_children_mixed_confidence",
        "advanced_big_terrain",
        "short_break_no_car",
        "value_optimizer",
        "crowd_averse_quiet_slopes",
        "non_skier_partner",
        "luxury_wellness_hotel_trip",
        "late_booking_conditions_chaser",
        "mixed_skill_group",
        "shared_domain_multi_ski_area_grouping",
    ]


def test_scoring_scenarios_include_future_and_missing_factors() -> None:
    beginner = SCORING_SCENARIOS_BY_ID["beginner_first_trip_low_hassle"]
    assert beginner.factor_availability["ski_school_quality"] == "known_missing"
    assert beginner.factor_availability["beginner_package_availability"] == (
        "future_candidate"
    )

    value = SCORING_SCENARIOS_BY_ID["value_optimizer"]
    assert value.factor_availability["lift_pass_price_per_km"] == "near_term"

    crowd = SCORING_SCENARIOS_BY_ID["crowd_averse_quiet_slopes"]
    assert crowd.expected_today_status == "blocked_by_missing_data"
    assert crowd.factor_availability["lift_queue_time"] == "known_missing"


def test_scoring_scenarios_do_not_duplicate_ids() -> None:
    ids = [scenario.scenario_id for scenario in SCORING_SCENARIOS]
    assert len(ids) == len(set(ids))
    assert set(SCORING_SCENARIOS_BY_ID) == set(ids)
