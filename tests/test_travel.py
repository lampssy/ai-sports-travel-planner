import pytest

from app.domain.catalog import StayDestination
from app.domain.travel import (
    InMemoryTravelCache,
    assess_deterministic_travel_effort,
    assess_travel_effort,
    normalize_origin_text,
)


@pytest.fixture
def sample_destination() -> StayDestination:
    return StayDestination(
        stay_destination_id="alta-badia",
        name="Alta Badia",
        country="Italy",
        region="Dolomites",
        price_level="medium",
        latitude=46.5547,
        longitude=11.8735,
        trip_market_region_id="alta-badia",
    )


def test_normalize_origin_text_is_stable() -> None:
    assert normalize_origin_text("  München, Germany ") == "munchen germany"


def test_assess_travel_effort_returns_approximate_car_estimate_for_known_origin(
    sample_destination: StayDestination,
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
    sample_destination: StayDestination,
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
    cervinia = StayDestination(
        stay_destination_id="cervinia",
        name="Cervinia",
        country="Italy",
        region="Aosta Valley",
        price_level="high",
        latitude=45.9367,
        longitude=7.6297,
        trip_market_region_id="cervinia",
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
    sample_destination: StayDestination,
) -> None:
    assessment = assess_travel_effort(
        origin_text="München, Germany",
        destination=sample_destination,
        cache=InMemoryTravelCache(),
    )

    assert assessment is not None
    assert assessment.origin_label == "Munich"


def test_assess_travel_effort_uses_route_cache_on_second_call(
    sample_destination: StayDestination,
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
    sample_destination: StayDestination,
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
    sample_destination: StayDestination,
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
    sample_destination: StayDestination,
) -> None:
    assessment = assess_travel_effort(
        origin_text="Munich",
        destination=sample_destination,
        cache=InMemoryTravelCache(),
        max_drive_minutes=1,
    )

    assert assessment is not None
    assert assessment.exceeds_max_drive is True


def test_travel_effort_accepts_normalized_stay_destination() -> None:
    destination = StayDestination(
        stay_destination_id="example",
        name="Example",
        country="Austria",
        region="Tyrol",
        price_level="medium",
        latitude=47.0,
        longitude=11.0,
        trip_market_region_id="example",
    )

    result = assess_deterministic_travel_effort("Munich", destination)

    assert result is not None
    assert result.destination_label == "Example"
