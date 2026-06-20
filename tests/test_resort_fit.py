from app.domain.models import PisteKmByDifficulty, SkiArea, StayBase
from app.domain.resort_fit import (
    ranking_cap_for_trust_state,
    skill_fit_factor_for_ski_area,
    stay_base_access_factor,
    terrain_scale_factor_for_ski_area,
    trust_state_for_manifest_status,
)


def _ski_area(
    *,
    total_piste_km: float | None = None,
    beginner: float | None = None,
    intermediate: float | None = None,
    advanced: float | None = None,
    summit_elevation_m: int = 2600,
) -> SkiArea:
    difficulty = None
    if beginner is not None and intermediate is not None and advanced is not None:
        difficulty = PisteKmByDifficulty(
            beginner=beginner,
            intermediate=intermediate,
            advanced=advanced,
        )
    return SkiArea(
        ski_area_id="test-ski-area",
        name="Test Ski Area",
        latitude=45.5,
        longitude=6.7,
        base_elevation_m=1200,
        summit_elevation_m=summit_elevation_m,
        season_start_month=12,
        season_end_month=4,
        total_piste_km=total_piste_km,
        total_lift_count=20,
        piste_km_by_difficulty=difficulty,
    )


def _stay_base(
    *,
    nearest_lift_distance_m: int | None = None,
    access_mode: str = "unknown",
    lift_distance: str = "medium",
) -> StayBase:
    return StayBase(
        stay_base_id="test-village",
        name="Test Village",
        price_range="EUR 150-220",
        price_min=150,
        price_max=220,
        quality="standard",
        lift_distance=lift_distance,
        supported_skill_levels=["beginner", "intermediate"],
        nearest_lift_distance_m=nearest_lift_distance_m,
        access_mode=access_mode,
    )


def test_terrain_scale_uses_source_backed_total_piste_km() -> None:
    assert (
        terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=30)).value == "small"
    )
    assert (
        terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=80)).value
        == "medium"
    )
    assert (
        terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=180)).value
        == "large"
    )
    mega = terrain_scale_factor_for_ski_area(_ski_area(total_piste_km=320))
    assert mega.value == "mega"
    assert mega.trust_state == "source_backed"
    assert mega.lifecycle_state == "active"


def test_terrain_scale_marks_missing_total_piste_km_as_needs_source() -> None:
    factor = terrain_scale_factor_for_ski_area(_ski_area())

    assert factor.value is None
    assert factor.trust_state == "needs_source"
    assert factor.lifecycle_state == "planned"
    assert factor.missing_inputs == ("total_piste_km",)


def test_skill_fit_profile_uses_piste_difficulty_mix() -> None:
    factor = skill_fit_factor_for_ski_area(
        _ski_area(
            total_piste_km=130,
            beginner=50,
            intermediate=55,
            advanced=25,
        )
    )

    assert factor.value == ("beginner", "intermediate")
    assert factor.trust_state == "source_backed"
    assert factor.lifecycle_state == "active"


def test_skill_fit_profile_uses_total_piste_for_intermediate_threshold() -> None:
    factor = skill_fit_factor_for_ski_area(
        _ski_area(
            total_piste_km=80,
            beginner=18,
            intermediate=2,
            advanced=1,
        )
    )

    assert factor.value == ("beginner", "intermediate")


def test_skill_fit_profile_can_mark_advanced_from_large_high_terrain() -> None:
    factor = skill_fit_factor_for_ski_area(
        _ski_area(
            total_piste_km=180,
            beginner=25,
            intermediate=20,
            advanced=5,
            summit_elevation_m=3000,
        )
    )

    assert factor.value == ("beginner", "intermediate", "advanced")


def test_skill_fit_profile_treats_zero_total_piste_as_present_value() -> None:
    factor = skill_fit_factor_for_ski_area(
        _ski_area(
            total_piste_km=0,
            beginner=190,
            intermediate=5,
            advanced=5,
            summit_elevation_m=3000,
        )
    )

    assert factor.value == ("beginner",)


def test_skill_fit_profile_requires_difficulty_mix_for_source_backed_profile() -> None:
    factor = skill_fit_factor_for_ski_area(_ski_area(total_piste_km=90))

    assert factor.value == ("intermediate",)
    assert factor.trust_state == "derived_from_partial_data"
    assert factor.missing_inputs == ("piste_km_by_difficulty",)


def test_stay_base_access_prefers_distance_and_access_mode() -> None:
    walkable = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=450, access_mode="unknown")
    )
    shuttle = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=1200, access_mode="unknown")
    )
    car = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=2200, access_mode="unknown")
    )
    explicit_walk = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=2200, access_mode="walk")
    )
    explicit_bus = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=450, access_mode="ski_bus")
    )
    explicit_car = stay_base_access_factor(
        _stay_base(nearest_lift_distance_m=450, access_mode="car_recommended")
    )

    assert walkable.value == "walkable"
    assert shuttle.value == "shuttle_easy"
    assert car.value == "car_recommended"
    assert explicit_walk.value == "walkable"
    assert explicit_bus.value == "shuttle_easy"
    assert explicit_car.value == "car_recommended"
    assert walkable.trust_state == "source_backed"


def test_stay_base_access_falls_back_to_legacy_bucket_with_partial_trust() -> None:
    factor = stay_base_access_factor(_stay_base(lift_distance="near"))

    assert factor.value == "walkable"
    assert factor.trust_state == "derived_from_partial_data"
    assert factor.missing_inputs == ("nearest_lift_distance_m", "access_mode")


def test_trust_state_and_ranking_caps_map_current_manifest_statuses() -> None:
    assert trust_state_for_manifest_status("verified") == "source_backed"
    assert (
        trust_state_for_manifest_status("verified_with_adjustment") == "source_backed"
    )
    assert trust_state_for_manifest_status("estimated") == "manual_estimate"
    assert trust_state_for_manifest_status("needs_source") == "needs_source"
    assert trust_state_for_manifest_status(None) == "needs_source"

    assert ranking_cap_for_trust_state("source_backed") == 1.0
    assert ranking_cap_for_trust_state("derived_from_partial_data") == 0.7
    assert ranking_cap_for_trust_state("manual_estimate") == 0.25
    assert ranking_cap_for_trust_state("needs_source") == 0.0
