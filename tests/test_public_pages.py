from fastapi.testclient import TestClient

from app.data.repositories import RawWeatherHistoryRepository, ResortRepository
from app.domain.models import RawWeatherObservation
from app.main import create_app


def _seed_tignes_archive_weather() -> None:
    resort = ResortRepository().get_resort_by_id("tignes")
    assert resort is not None
    ski_area = resort.ski_areas[0]
    repository = RawWeatherHistoryRepository()
    for observed_on, snowfall_cm, snow_depth_m, max_temp_c, gust_kmh in (
        ("2024-03-05", 9, 1.4, -4, 24),
        ("2025-03-08", 7, 1.2, -2, 28),
    ):
        repository.upsert_observation(
            RawWeatherObservation(
                resort_id=ski_area.ski_area_id,
                resort_name=ski_area.name,
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


def test_public_resort_page_returns_server_rendered_html() -> None:
    _seed_tignes_archive_weather()
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ski-resorts/tignes")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Tignes ski resort guide | Snowcast</title>" in response.text
    assert (
        '<link rel="canonical" href="http://testserver/ski-resorts/tignes"'
        in response.text
    )
    assert '<meta property="og:title"' in response.text
    assert '<meta name="twitter:description"' in response.text
    assert "Current snow signal" in response.text
    assert "Conditions calendar" in response.text
    assert "Trust and provenance" in response.text
    assert "Source:" in response.text
    assert "View calendar" in response.text
    assert "Typical snow depth" in response.text
    assert "130 cm" in response.text
    assert "Historical data through Mar 2025" in response.text
    assert "archive weather windows" not in response.text
    assert "forecast assisted" not in response.text.lower()
    assert "+00:00" not in response.text
    assert "Le Lac" in response.text


def test_public_resort_page_unknown_resort_returns_404() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/ski-resorts/not-a-resort")

    assert response.status_code == 404


def test_sitemap_lists_every_public_resort_page() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in (
        response.text
    )
    for resort in ResortRepository().list_resorts():
        assert f"http://testserver/ski-resorts/{resort.resort_id}" in response.text


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
        public_response = client.get("/ski-resorts/tignes")
        app_detail_response = client.get("/resorts/tignes")
        current_trip_response = client.get("/current-trip")

    assert public_response.status_code == 200
    assert "Tignes ski resort guide" in public_response.text
    assert app_detail_response.status_code == 200
    assert "frontend" in app_detail_response.text
    assert current_trip_response.status_code == 200
    assert "frontend" in current_trip_response.text
