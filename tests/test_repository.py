from datetime import date

from app.data.database import bootstrap_database, connect
from app.data.repositories import (
    RawWeatherHistoryRepository,
    ResortConditionsRepository,
    ResortRepository,
)
from app.domain.models import RawWeatherObservation, SearchFilters
from app.domain.search_service import search_resorts


def test_bootstrap_database_creates_schema_and_seeds_data() -> None:
    bootstrap_database()

    with connect() as connection:
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
        raw_columns = {
            row["column_name"]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'raw_weather_history'
                """
            ).fetchall()
        }

    assert 20 <= resort_count <= 30
    assert ski_area_count > 0
    assert stay_base_count > 0
    assert rental_count > 0
    assert conditions_count == 0
    assert {"elevation_band", "elevation_m"} <= raw_columns


def _raw_weather_observation(
    *,
    elevation_band: str,
    elevation_m: int,
    snow_depth_m: float,
) -> RawWeatherObservation:
    return RawWeatherObservation(
        resort_id="tignes-ski-area",
        resort_name="Tignes",
        elevation_band=elevation_band,
        elevation_m=elevation_m,
        observed_on="2024-03-05",
        observed_at="2024-03-05T12:00:00+00:00",
        snowfall_cm=8,
        snow_depth_m=snow_depth_m,
        temperature_2m_max_c=-3,
        temperature_2m_min_c=-9,
        wind_speed_10m_max_kmh=18,
        wind_gusts_10m_max_kmh=24,
        weather_code=3,
        record_type="archive",
        source="open-meteo",
        source_model="best_match",
    )


def test_raw_weather_history_upsert_is_elevation_band_aware() -> None:
    repository = RawWeatherHistoryRepository()

    repository.upsert_observation(
        _raw_weather_observation(
            elevation_band="mid",
            elevation_m=2500,
            snow_depth_m=1.3,
        )
    )
    repository.upsert_observation(
        _raw_weather_observation(
            elevation_band="upper",
            elevation_m=3200,
            snow_depth_m=3.2,
        )
    )

    all_rows = repository.list_observations_for_resort("tignes-ski-area")
    mid_rows = repository.list_observations_for_resort(
        "tignes-ski-area",
        elevation_band="mid",
    )

    assert len(all_rows) == 2
    assert {row.elevation_band for row in all_rows} == {"mid", "upper"}
    assert len(mid_rows) == 1
    assert mid_rows[0].snow_depth_m == 1.3


def test_raw_weather_history_delete_path_can_target_archive_rows() -> None:
    repository = RawWeatherHistoryRepository()
    repository.upsert_observation(
        _raw_weather_observation(
            elevation_band="mid",
            elevation_m=2500,
            snow_depth_m=1.3,
        )
    )

    deleted = repository.delete_observations_for_resort(
        resort_id="tignes-ski-area",
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 31),
        record_type="archive",
    )

    assert deleted == 1
    assert repository.list_observations_for_resort("tignes-ski-area") == ()


def test_resort_repository_returns_nested_models() -> None:
    repository = ResortRepository()

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


def test_conditions_repository_returns_none_before_refresh() -> None:
    repository = ResortConditionsRepository()

    conditions = repository.get_conditions_for_resort("Chamonix Mont-Blanc")

    assert conditions is None


def test_bootstrap_keeps_conditions_table_empty_in_fresh_database() -> None:
    bootstrap_database()
    bootstrap_database()

    with connect() as connection:
        conditions_count = connection.execute(
            "SELECT COUNT(*) AS count FROM resort_conditions"
        ).fetchone()["count"]

    assert conditions_count == 0


def test_search_resorts_works_with_postgres_backed_repositories() -> None:
    resorts = ResortRepository()
    conditions = ResortConditionsRepository()

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
