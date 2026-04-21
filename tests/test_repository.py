from datetime import date

from app.data.correct_raw_weather_record_types import correct_raw_weather_record_types
from app.data.database import bootstrap_database, connect
from app.data.repositories import ResortConditionsRepository, ResortRepository
from app.domain.models import SearchFilters
from app.domain.search_service import search_resorts


def test_bootstrap_database_creates_schema_and_seeds_data(tmp_path) -> None:
    db_path = tmp_path / "planner.db"

    bootstrap_database(db_path)

    with connect(db_path) as connection:
        resort_count = connection.execute(
            "SELECT COUNT(*) AS count FROM resorts"
        ).fetchone()["count"]
        ski_area_count = connection.execute(
            "SELECT COUNT(*) AS count FROM ski_areas"
        ).fetchone()["count"]
        stay_base_count = connection.execute(
            "SELECT COUNT(*) AS count FROM stay_bases"
        ).fetchone()["count"]
        rental_count = connection.execute(
            "SELECT COUNT(*) AS count FROM rentals"
        ).fetchone()["count"]
        conditions_count = connection.execute(
            "SELECT COUNT(*) AS count FROM resort_conditions"
        ).fetchone()["count"]

    assert 20 <= resort_count <= 30
    assert ski_area_count > 0
    assert stay_base_count > 0
    assert rental_count > 0
    assert conditions_count == 0


def test_resort_repository_returns_nested_models(tmp_path) -> None:
    repository = ResortRepository(tmp_path / "planner.db")

    resorts = repository.list_resorts()
    chamonix = next(
        resort for resort in resorts if resort.name == "Chamonix Mont-Blanc"
    )

    assert chamonix.resort_id == "chamonix-mont-blanc"
    assert chamonix.region == "Haute-Savoie"
    assert chamonix.latitude > 0
    assert chamonix.summit_elevation_m > chamonix.base_elevation_m
    assert chamonix.stay_bases
    assert chamonix.ski_areas
    assert chamonix.rentals
    assert chamonix.stay_bases[0].supported_skill_levels


def test_conditions_repository_returns_none_before_refresh(tmp_path) -> None:
    repository = ResortConditionsRepository(tmp_path / "planner.db")

    conditions = repository.get_conditions_for_resort("Chamonix Mont-Blanc")

    assert conditions is None


def test_bootstrap_keeps_conditions_table_empty_in_fresh_database(tmp_path) -> None:
    db_path = tmp_path / "planner.db"
    bootstrap_database(db_path)
    bootstrap_database(db_path)

    with connect(db_path) as connection:
        conditions_count = connection.execute(
            "SELECT COUNT(*) AS count FROM resort_conditions"
        ).fetchone()["count"]

    assert conditions_count == 0


def test_search_resorts_works_with_sqlite_backed_repositories(tmp_path) -> None:
    db_path = tmp_path / "planner.db"
    resorts = ResortRepository(db_path)
    conditions = ResortConditionsRepository(db_path)

    results = search_resorts(
        SearchFilters(
            location="France",
            min_price=150,
            max_price=320,
            stars=1,
            skill_level="intermediate",
        ),
        resorts=resorts.list_resorts(),
        conditions_provider=conditions,
    )

    assert results
    assert (
        results[0].conditions_summary
        == "No live conditions signal available for this ski area."
    )


def test_correct_raw_weather_record_types_marks_rows_around_cutoff(tmp_path) -> None:
    db_path = tmp_path / "planner.db"
    bootstrap_database(db_path)

    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO raw_weather_history (
                resort_id,
                resort_name,
                observed_on,
                observed_at,
                snowfall_cm,
                snow_depth_m,
                temperature_2m_max_c,
                temperature_2m_min_c,
                wind_speed_10m_max_kmh,
                wind_gusts_10m_max_kmh,
                weather_code,
                record_type,
                source,
                source_model
            ) VALUES
                (
                    'tignes-ski-area',
                    'Tignes',
                    '2026-04-01',
                    '2026-04-01T12:00:00+00:00',
                    5,
                    1.0,
                    -2,
                    -8,
                    15,
                    25,
                    3,
                    'forecast',
                    'open-meteo',
                    'best_match'
                ),
                (
                    'tignes-ski-area',
                    'Tignes',
                    '2026-04-02',
                    '2026-04-02T12:00:00+00:00',
                    4,
                    0.9,
                    -1,
                    -7,
                    12,
                    20,
                    3,
                    'archive',
                    'open-meteo',
                    'best_match'
                )
            """
        )

    result = correct_raw_weather_record_types(
        database_url=db_path,
        forecast_after=date(2026, 4, 1),
    )

    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT observed_on::text AS observed_on, record_type
            FROM raw_weather_history
            WHERE resort_id = 'tignes-ski-area'
            ORDER BY observed_on
            """
        ).fetchall()

    assert result.archive_rows == 1
    assert result.forecast_rows == 1
    assert rows == [
        {"observed_on": "2026-04-01", "record_type": "archive"},
        {"observed_on": "2026-04-02", "record_type": "forecast"},
    ]
