import pytest

from app.domain.models import Destination, Rental, SkiArea, StayBase
from app.domain.travel import (
    InMemoryTravelCache,
    assess_deterministic_travel_effort,
    assess_travel_effort,
    normalize_origin_text,
)


@pytest.fixture
def sample_destination() -> Destination:
    ski_area = SkiArea(
        ski_area_id="alta-badia",
        name="Alta Badia",
        latitude=46.5547,
        longitude=11.8735,
        base_elevation_m=1324,
        summit_elevation_m=2778,
        season_start_month=12,
        season_end_month=4,
    )
    return Destination(
        resort_id="alta-badia",
        name="Alta Badia",
        country="Italy",
        region="Dolomites",
        price_level="medium",
        latitude=ski_area.latitude,
        longitude=ski_area.longitude,
        base_elevation_m=ski_area.base_elevation_m,
        summit_elevation_m=ski_area.summit_elevation_m,
        season_start_month=ski_area.season_start_month,
        season_end_month=ski_area.season_end_month,
        stay_bases=[
            StayBase(
                stay_base_id="alta-badia-corvara",
                name="Corvara",
                price_range="EUR 180-260",
                price_min=180,
                price_max=260,
                quality="standard",
                lift_distance="near",
                supported_skill_levels=["intermediate", "advanced"],
            )
        ],
        ski_areas=[ski_area],
        rentals=[
            Rental(
                name="Alta Badia Rental",
                price_range="EUR 35-55",
                price_min=35,
                price_max=55,
                quality="standard",
                lift_distance="near",
            )
        ],
    )


def test_normalize_origin_text_is_stable() -> None:
    assert normalize_origin_text("  München, Germany ") == "munchen germany"


def test_assess_travel_effort_returns_approximate_car_estimate_for_known_origin(
    sample_destination: Destination,
) -> None:
    cache = InMemoryTravelCache()
    assessment = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=cache,
    )

    assert assessment is not None
    assert assessment.origin_label == "Munich"
    assert assessment.destination_label == "Alta Badia"
    assert assessment.mode == "car"
    assert assessment.distance_km > 0
    assert assessment.duration_minutes > 0
    assert assessment.effort_label in {"easy", "moderate", "long", "very_long"}
    assert 0 <= assessment.score <= 1
    assert assessment.summary.startswith("Approx. ")
    assert assessment.provenance == "estimated_fallback"
    assert assessment.provider == "approximate_haversine_v2"
    assert assessment.caveat == (
        "Approximate car estimate based on straight-line distance, a road "
        "multiplier, and calibrated long-distance drive speed."
    )


def test_assess_deterministic_travel_effort_does_not_require_cache(
    sample_destination: Destination,
) -> None:
    assessment = assess_deterministic_travel_effort(
        origin_text="Warsaw",
        destination=sample_destination,
        tolerance="medium",
    )

    assert assessment is not None
    assert assessment.origin_label == "Warsaw"
    assert assessment.destination_label == "Alta Badia"
    assert assessment.provider == "approximate_haversine_v2"
    assert assessment.provenance == "estimated_fallback"
    assert assessment.cache_hit is False


def test_assess_travel_effort_calibrates_long_distance_drive_time() -> None:
    cervinia = Destination(
        resort_id="cervinia",
        name="Cervinia",
        country="Italy",
        region="Aosta Valley",
        price_level="high",
        latitude=45.9367,
        longitude=7.6297,
        base_elevation_m=2050,
        summit_elevation_m=3480,
        season_start_month=11,
        season_end_month=5,
        stay_bases=[],
        ski_areas=[],
        rentals=[],
    )

    assessment = assess_travel_effort(
        origin_text="Warsaw",
        destination=cervinia,
        cache=InMemoryTravelCache(),
    )

    assert assessment is not None
    assert assessment.distance_km == pytest.approx(1616, abs=30)
    assert 16 * 60 <= assessment.duration_minutes <= 19 * 60
    assert "17h" in assessment.summary or "18h" in assessment.summary


def test_assess_travel_effort_handles_munich_country_origin_variant(
    sample_destination: Destination,
) -> None:
    assessment = assess_travel_effort(
        origin_text="München, Germany",
        destination=sample_destination,
        cache=InMemoryTravelCache(),
    )

    assert assessment is not None
    assert assessment.origin_label == "Munich"


def test_assess_travel_effort_uses_route_cache_on_second_call(
    sample_destination: Destination,
) -> None:
    cache = InMemoryTravelCache()
    first = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=cache,
    )
    second = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=cache,
    )

    assert first is not None
    assert second is not None
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.duration_minutes == first.duration_minutes


def test_assess_travel_effort_route_cache_survives_destination_name_changes(
    sample_destination: Destination,
) -> None:
    cache = InMemoryTravelCache()
    first = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=cache,
    )
    renamed_destination = sample_destination.model_copy(
        update={"name": "Alta Badia Dolomites"}
    )
    second = assess_travel_effort(
        origin_text="Munich",
        destination=renamed_destination,
        cache=cache,
    )

    assert first is not None
    assert second is not None
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.duration_minutes == first.duration_minutes


def test_assess_travel_effort_route_cache_misses_when_coordinates_change(
    sample_destination: Destination,
) -> None:
    cache = InMemoryTravelCache()
    first = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=cache,
    )
    moved_destination = sample_destination.model_copy(
        update={"latitude": sample_destination.latitude + 0.1}
    )
    second = assess_travel_effort(
        origin_text="Munich",
        destination=moved_destination,
        cache=cache,
    )

    assert first is not None
    assert second is not None
    assert first.cache_hit is False
    assert second.cache_hit is False
    assert second.duration_minutes != first.duration_minutes


def test_assess_travel_effort_respects_max_drive_threshold(
    sample_destination: Destination,
) -> None:
    assessment = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=InMemoryTravelCache(),
        max_drive_minutes=1,
    )

    assert assessment is not None
    assert assessment.exceeds_max_drive is True
