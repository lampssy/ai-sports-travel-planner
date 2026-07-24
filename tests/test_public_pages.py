import re

import pytest
from fastapi.testclient import TestClient

from app.data.catalog_loader import load_catalog
from app.data.catalog_repository import CatalogRepository
from app.data.catalog_sync import sync_catalog_snapshot
from app.data.repositories import (
    RawWeatherHistoryRepository,
    ResortConditionsRepository,
)
from app.domain.catalog import CatalogSnapshot
from app.domain.models import RawWeatherObservation, ResortConditions
from app.domain.planning import PlanningAssessment
from app.main import create_app
from app.public_pages import (
    _current_snow_signal_label,
    render_public_destination_page,
)


@pytest.fixture(autouse=True)
def sync_normalized_catalog(reset_postgres_database: None) -> None:
    sync_catalog_snapshot(load_catalog())


def _seed_tignes_archive_weather() -> None:
    repository = RawWeatherHistoryRepository()
    for observed_on, snowfall_cm, snow_depth_m, max_temp_c, gust_kmh in (
        ("2024-03-05", 9, 1.4, -4, 24),
        ("2025-03-08", 7, 1.2, -2, 28),
    ):
        repository.upsert_observation(
            RawWeatherObservation(
                ski_area_id="tignes-ski-area",
                resort_name="Tignes",
                elevation_band="mid",
                elevation_m=2500,
                observed_on=observed_on,
                observed_at=f"{observed_on}T12:00:00+00:00",
                snowfall_cm=snowfall_cm,
                snow_depth_m=snow_depth_m,
                temperature_2m_max_c=max_temp_c,
                temperature_2m_min_c=max_temp_c - 6,
                wind_speed_10m_max_kmh=gust_kmh - 8,
                wind_gusts_10m_max_kmh=gust_kmh,
                weather_code=3,
                record_type="archive",
                source="open-meteo",
                source_model="best_match",
            )
        )


def _synthetic_multi_area_catalog() -> CatalogSnapshot:
    return CatalogSnapshot.model_validate(
        {
            "schema_version": 2,
            "ski_regions": [
                {
                    "ski_region_id": "sample-valley",
                    "name": "Sample Valley",
                    "grouping_policy": "trip_market",
                }
            ],
            "stay_destinations": [
                {
                    "stay_destination_id": "sample-town",
                    "name": "Sample Town",
                    "country": "Example",
                    "region": "Example Alps",
                    "price_level": "medium",
                    "latitude": 46.0,
                    "longitude": 7.0,
                    "trip_market_region_id": "sample-valley",
                }
            ],
            "stay_bases": [
                {
                    "stay_base_id": "sample-town-center",
                    "stay_destination_id": "sample-town",
                    "name": "Town Center",
                    "price_range": "EUR 100-200",
                    "price_min": 100,
                    "price_max": 200,
                    "quality": "standard",
                }
            ],
            "ski_areas": [
                {
                    "ski_area_id": "sample-east",
                    "name": "East Bowl",
                    "latitude": 46.01,
                    "longitude": 7.01,
                    "base_elevation_m": 1500,
                    "summit_elevation_m": 2500,
                    "season_start_month": 12,
                    "season_end_month": 4,
                    "weather_sampling_status": "active",
                },
                {
                    "ski_area_id": "sample-west",
                    "name": "West Bowl",
                    "latitude": 46.02,
                    "longitude": 7.02,
                    "base_elevation_m": 1600,
                    "summit_elevation_m": 2600,
                    "season_start_month": 12,
                    "season_end_month": 4,
                    "weather_sampling_status": "active",
                },
            ],
            "ski_area_access": [
                {
                    "ski_area_access_id": "sample-town-center--sample-east",
                    "stay_base_id": "sample-town-center",
                    "ski_area_id": "sample-east",
                    "access_mode": "walk",
                    "lift_distance": "near",
                    "is_direct": True,
                    "source_urls": ["https://example.com/sample-east"],
                },
                {
                    "ski_area_access_id": "sample-town-center--sample-west",
                    "stay_base_id": "sample-town-center",
                    "ski_area_id": "sample-west",
                    "access_mode": "ski_bus",
                    "lift_distance": "medium",
                    "is_direct": False,
                    "source_urls": ["https://example.com/sample-west"],
                },
            ],
            "terrain_domains": [],
            "lift_pass_products": [],
            "rental_display_facts": [],
        }
    )


def test_public_destination_page_returns_server_rendered_html() -> None:
    _seed_tignes_archive_weather()
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ski-destinations/tignes")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Tignes ski destination guide | Snowcast</title>" in response.text
    assert (
        '<link rel="canonical" href="http://testserver/ski-destinations/tignes"'
        in response.text
    )
    assert '<meta property="og:title"' in response.text
    assert '<meta name="twitter:description"' in response.text
    assert "--ember: #b83d1d" in response.text
    assert "--ember-on-dark: #ff8fb1" in response.text
    assert ".hero-main .eyebrow { color: var(--ember-on-dark); }" in response.text
    assert "Latest available snow signal" in response.text
    assert "Snow fit" not in response.text
    assert "Not enough evidence" in response.text
    assert "Conditions calendar" in response.text
    assert "How we use source data" in response.text
    assert "Source:" in response.text
    assert "View calendar" in response.text
    assert "Mid-mountain snow" in response.text
    assert "mid-mountain typical snow depth" in response.text
    assert "130 cm" in response.text
    assert "Historical data through Mar 2025" in response.text
    assert "archive weather windows" not in response.text
    assert "forecast and historical weather information" in response.text
    assert "current forecasts and historical weather records" not in response.text
    assert "reviewed destination and access details" in response.text
    assert "historical weather records" in response.text
    assert "Data status:" in response.text
    assert "evidence stay attached" not in response.text
    assert "curated destination" not in response.text
    assert "archive weather" not in response.text
    assert "Freshness:" not in response.text
    assert "forecast assisted" not in response.text.lower()
    assert "+00:00" not in response.text
    assert "Le Lac" in response.text
    assert "Places to stay" in response.text
    assert "Stay areas Snowcast can consider" in response.text
    assert "Ski region" in response.text
    assert "Tignes ski-area conditions" in response.text
    lower_response = response.text.lower()
    assert "quality tier" not in lower_response
    assert "stay base" not in lower_response
    assert "recommended places to stay" not in lower_response
    assert "trip market" not in lower_response
    assert "trust and provenance" not in lower_response
    assert "weather score" not in lower_response


def test_public_calendar_keeps_poor_measured_snow_honest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_tignes_archive_weather()
    monkeypatch.setattr(
        "app.public_pages.derive_planning_assessment",
        lambda **_kwargs: PlanningAssessment(
            conditions=ResortConditions(
                resort_name="Tignes",
                snow_confidence_score=0.2,
                snow_confidence_label="poor",
                availability_status="limited",
                weather_summary="Historically weak snow signal.",
                conditions_score=0.2,
            ),
            planning_summary="Historically weak snow signal.",
            evidence_count=2,
            best_travel_months=(),
            latest_snapshot_at="2025-03-08T12:00:00+00:00",
            evidence_source="raw_history",
            evidence_profile="archive_backed",
        ),
    )
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ski-destinations/tignes")

    assert response.status_code == 200
    march_match = re.search(
        r'<article class="month[^>]*>.*?<h3>March</h3>.*?</article>',
        response.text,
        flags=re.DOTALL,
    )
    assert march_match is not None
    march = march_match.group(0)
    assert "Historical snow conditions look poor" in march
    assert "Historically weak snow signal with mid-mountain typical snow depth" in march
    assert "Not enough evidence" not in march


def test_public_destination_fallback_uses_evidence_limitation_not_a_fit_state() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ski-destinations/tignes")

    assert response.status_code == 200
    assert "Latest available snow signal" in response.text
    assert "Not enough evidence" in response.text
    assert "Some concerns" not in response.text


def test_public_calendar_fallback_months_use_seasonal_estimates() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ski-destinations/tignes")

    assert response.status_code == 200
    month_cards = re.findall(
        r'<article class="month[^>]*>.*?</article>',
        response.text,
        flags=re.DOTALL,
    )
    assert month_cards
    for card in month_cards:
        assert "Seasonal estimate" in card
        assert "Not enough historical snow-depth evidence" in card
        assert "Historical snow conditions" not in card
        assert "Historically strong snow signal" not in card
        assert "Historically mixed snow signal" not in card
        assert "Historically weak snow signal" not in card
    assert "Highest seasonal estimates:" in response.text
    assert "Historically strongest months:" not in response.text


@pytest.mark.parametrize(
    ("label", "source_available", "freshness_status", "expected"),
    [
        ("good", True, "fresh", "Current snow conditions look good"),
        ("fair", True, "fresh", "Current snow conditions are mixed"),
        ("poor", True, "fresh", "Current snow conditions look poor"),
        (
            "good",
            True,
            "stale",
            "Latest available snow conditions look good (out of date)",
        ),
        ("fair", False, "unknown", "Not enough evidence"),
    ],
)
def test_current_snow_signal_labels_reflect_source_availability(
    label: str,
    source_available: bool,
    freshness_status: str,
    expected: str,
) -> None:
    assert (
        _current_snow_signal_label(
            label,
            source_available=source_available,
            freshness_status=freshness_status,
        )
        == expected
    )


def test_public_destination_page_does_not_call_stale_forecast_current() -> None:
    ResortConditionsRepository().upsert_conditions(
        entity_id="tignes-ski-area",
        entity_name="Tignes",
        conditions=ResortConditions(
            resort_name="Tignes",
            snow_confidence_score=0.8,
            snow_confidence_label="good",
            availability_status="open",
            weather_summary="The latest available forecast shows settled weather.",
            conditions_score=0.8,
            updated_at="2020-01-01T00:00:00+00:00",
            source="open-meteo",
        ),
    )
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ski-destinations/tignes")

    area_match = re.search(
        r'<section id="ski-area-tignes-ski-area".*?</section>',
        response.text,
        flags=re.DOTALL,
    )
    assert area_match is not None
    area_section = area_match.group(0)
    assert "Latest available snow signal" in area_section
    assert "Latest available snow conditions look good (out of date)" in area_section
    assert "This forecast is out of date." in area_section
    assert "Data status:</strong> out of date" in area_section
    assert "Current snow" not in area_section
    assert "current forecast" not in area_section.lower()


def test_public_destination_page_unknown_destination_returns_404() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ski-destinations/not-a-destination")

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "<title>Destination not found | Snowcast</title>" in response.text
    assert "<main" in response.text
    assert "<h1>We could not find this ski destination</h1>" in response.text
    assert "Return to search" in response.text
    assert 'href="/"' in response.text
    assert "Unknown stay_destination_id" not in response.text


def test_sitemap_lists_every_public_destination_page() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in (
        response.text
    )
    for destination in CatalogRepository().get_snapshot().stay_destinations:
        assert (
            f"http://testserver/ski-destinations/{destination.stay_destination_id}"
        ) in response.text


def test_multi_area_destination_keeps_weather_sections_area_specific() -> None:
    html = render_public_destination_page(
        stay_destination_id="sample-town",
        base_url="http://testserver",
        catalog_snapshot=_synthetic_multi_area_catalog(),
    )

    assert html.count('class="card area-section"') == 2
    assert 'id="ski-area-sample-east"' in html
    assert 'id="ski-area-sample-west"' in html
    assert "East Bowl ski-area conditions" in html
    assert "West Bowl ski-area conditions" in html
    assert "Sample Town combined snow signal" not in html


def test_robots_txt_allows_indexing_and_points_to_sitemap() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/robots.txt")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "User-agent: *" in response.text
    assert "Allow: /" in response.text
    assert "Sitemap: http://testserver/sitemap.xml" in response.text


def test_public_routes_do_not_replace_search_context_spa_routes(tmp_path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>frontend</html>", encoding="utf-8")

    app = create_app(frontend_dist_dir=dist_dir)

    with TestClient(app) as client:
        public_response = client.get("/ski-destinations/tignes")
        app_detail_response = client.get("/recommendations/tignes-val-disere")
        current_trip_response = client.get("/current-trip")

    assert public_response.status_code == 200
    assert "Tignes ski destination guide" in public_response.text
    assert app_detail_response.status_code == 200
    assert "frontend" in app_detail_response.text
    assert current_trip_response.status_code == 200
    assert "frontend" in current_trip_response.text
