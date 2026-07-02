import pytest
from fastapi.testclient import TestClient

from app.data.catalog_loader import load_catalog
from app.data.catalog_repository import CatalogRepository
from app.data.catalog_sync import sync_catalog_snapshot
from app.data.repositories import RawWeatherHistoryRepository
from app.domain.models import RawWeatherObservation
from app.main import create_app


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
    assert "Current snow signal" in response.text
    assert "Conditions calendar" in response.text
    assert "Trust and provenance" in response.text
    assert "Source:" in response.text
    assert "View calendar" in response.text
    assert "Mid-mountain snow" in response.text
    assert "mid-mountain typical snow depth" in response.text
    assert "130 cm" in response.text
    assert "Historical data through Mar 2025" in response.text
    assert "archive weather windows" not in response.text
    assert "forecast assisted" not in response.text.lower()
    assert "+00:00" not in response.text
    assert "Le Lac" in response.text
    assert "Tignes ski-area conditions" in response.text


def test_public_destination_page_unknown_destination_returns_404() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ski-destinations/not-a-destination")

    assert response.status_code == 404


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
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ski-destinations/chamonix-mont-blanc")

    assert response.status_code == 200
    assert "Brevent-Flegere ski-area conditions" in response.text
    assert "Grands Montets ski-area conditions" in response.text
    assert "Balme - Le Tour - Vallorcine ski-area conditions" in response.text
    assert "Chamonix-Mont-Blanc combined snow signal" not in response.text


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
