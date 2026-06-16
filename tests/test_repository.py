import json
from datetime import UTC, date, datetime, timedelta

import pytest

from app.data.database import _create_schema, bootstrap_database, connect
from app.data.repositories import (
    RawWeatherHistoryRepository,
    ResortConditionsRepository,
    ResortRepository,
    SnowClimatologyRepository,
    TravelCacheRepository,
)
from app.domain.models import (
    RawWeatherObservation,
    ResortConditions,
    SearchFilters,
    SnowClimatologyDaily,
)
from app.domain.search_service import search_resorts
from app.domain.travel import TravelOrigin


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
        travel_tables = {
            row["table_name"]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                    'travel_geocode_cache',
                    'travel_route_cache'
                  )
                """
            ).fetchall()
        }
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
    assert travel_tables == {"travel_geocode_cache", "travel_route_cache"}
    assert {
        "elevation_band",
        "elevation_m",
        "precipitation_sum_mm",
        "rain_sum_mm",
        "precipitation_hours",
        "snowfall_water_equivalent_sum_mm",
        "apparent_temperature_2m_max_c",
        "apparent_temperature_2m_min_c",
        "cloud_cover_mean_pct",
        "sunshine_duration_seconds",
        "visibility_min_m",
    } <= raw_columns


def test_bootstrap_database_creates_snow_climatology_table() -> None:
    bootstrap_database()

    with connect() as connection:
        columns = {
            row["column_name"]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'ski_area_snow_climatology_daily'
                """
            ).fetchall()
        }
        index_row = connection.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'ski_area_snow_climatology_daily'
              AND indexname = 'ski_area_snow_climatology_lookup_idx'
            """
        ).fetchone()

    assert {
        "ski_area_id",
        "elevation_band",
        "baseline_period",
        "baseline_start_year",
        "baseline_end_year",
        "evidence_seasons",
        "month",
        "day",
        "snow_depth_cm_p50",
        "prob_snow_depth_ge_30cm",
        "avg_snow_confidence_score",
        "avg_conditions_score",
    } <= columns
    assert index_row is not None


def test_travel_cache_repository_recreates_missing_cache_tables() -> None:
    bootstrap_database()
    with connect() as connection:
        connection.execute("DROP TABLE travel_route_cache")
        connection.execute("DROP TABLE travel_geocode_cache")

    repository = TravelCacheRepository()
    assert repository.get_geocode("berlin") is None

    repository.set_geocode("berlin", TravelOrigin("Berlin", 52.52, 13.405))

    assert repository.get_geocode("berlin") == TravelOrigin(
        "Berlin",
        52.52,
        13.405,
    )


def _raw_weather_observation(
    *,
    resort_id: str = "tignes-ski-area",
    resort_name: str = "Tignes",
    elevation_band: str,
    elevation_m: int,
    observed_on: str = "2024-03-05",
    snow_depth_m: float,
) -> RawWeatherObservation:
    return RawWeatherObservation(
        resort_id=resort_id,
        resort_name=resort_name,
        elevation_band=elevation_band,
        elevation_m=elevation_m,
        observed_on=observed_on,
        observed_at=f"{observed_on}T12:00:00+00:00",
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
        precipitation_sum_mm=3.4,
        rain_sum_mm=0.8,
        precipitation_hours=4.0,
        snowfall_water_equivalent_sum_mm=2.6,
        apparent_temperature_2m_max_c=-8.0,
        apparent_temperature_2m_min_c=-15.0,
        cloud_cover_mean_pct=72.0,
        sunshine_duration_seconds=12600.0,
        visibility_min_m=8800.0,
    )


def _snow_climatology_row(
    *,
    ski_area_id: str = "tignes-ski-area",
    resort_name: str = "Tignes",
    elevation_band: str = "mid",
    elevation_m: int = 2500,
    month: int = 3,
    day: int = 10,
    baseline_period: str = "normal_30y",
    evidence_seasons: int = 30,
) -> SnowClimatologyDaily:
    return SnowClimatologyDaily(
        ski_area_id=ski_area_id,
        resort_name=resort_name,
        elevation_band=elevation_band,
        elevation_m=elevation_m,
        month=month,
        day=day,
        baseline_period=baseline_period,
        baseline_start_year=1996,
        baseline_end_year=2025,
        evidence_seasons=evidence_seasons,
        latest_archive_year=2025,
        snow_depth_cm_p25=80.0,
        snow_depth_cm_p50=120.0,
        snow_depth_cm_p75=160.0,
        prob_snow_depth_ge_30cm=0.93,
        prob_snow_depth_ge_50cm=0.87,
        avg_daily_snowfall_cm=6.5,
        prob_rain_risk=0.07,
        prob_freeze_thaw=0.12,
        avg_max_temperature_c=-2.4,
        avg_wind_gust_kmh=28.0,
        avg_snow_confidence_score=0.82,
        avg_conditions_score=0.78,
        source_model="snowcast_empirical_v1",
        computed_at="2026-06-15T00:00:00+00:00",
    )


def _resort_conditions(
    resort_name: str,
    *,
    snow_confidence_score: float = 0.82,
    conditions_score: float = 0.76,
) -> ResortConditions:
    return ResortConditions(
        resort_name=resort_name,
        snow_confidence_score=snow_confidence_score,
        snow_confidence_label="good",
        availability_status="open",
        weather_summary=f"Fresh conditions for {resort_name}.",
        conditions_score=conditions_score,
        updated_at="2026-01-15T00:00:00+00:00",
        source="open-meteo",
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
    assert mid_rows[0].precipitation_sum_mm == 3.4
    assert mid_rows[0].rain_sum_mm == 0.8
    assert mid_rows[0].precipitation_hours == 4.0
    assert mid_rows[0].snowfall_water_equivalent_sum_mm == 2.6
    assert mid_rows[0].apparent_temperature_2m_max_c == -8.0
    assert mid_rows[0].apparent_temperature_2m_min_c == -15.0
    assert mid_rows[0].cloud_cover_mean_pct == 72.0
    assert mid_rows[0].sunshine_duration_seconds == 12600.0
    assert mid_rows[0].visibility_min_m == 8800.0


def test_raw_weather_history_lists_multiple_resorts_by_band() -> None:
    repository = RawWeatherHistoryRepository()
    repository.upsert_observation(
        _raw_weather_observation(
            resort_id="tignes-ski-area",
            resort_name="Tignes",
            elevation_band="mid",
            elevation_m=2500,
            observed_on="2024-03-05",
            snow_depth_m=1.3,
        )
    )
    repository.upsert_observation(
        _raw_weather_observation(
            resort_id="cervinia-ski-area",
            resort_name="Cervinia",
            elevation_band="upper",
            elevation_m=3300,
            observed_on="2024-03-05",
            snow_depth_m=2.2,
        )
    )

    grouped = repository.list_observations_for_resorts(
        ("tignes-ski-area", "cervinia-ski-area"),
        elevation_bands=("mid", "upper", "base"),
    )

    assert grouped[("tignes-ski-area", "mid")][0].snow_depth_m == 1.3
    assert grouped[("cervinia-ski-area", "upper")][0].snow_depth_m == 2.2
    assert grouped[("tignes-ski-area", "upper")] == ()
    assert grouped[("cervinia-ski-area", "base")] == ()


def test_raw_weather_history_batch_upsert_writes_multiple_rows_idempotently() -> None:
    repository = RawWeatherHistoryRepository()
    rows = (
        _raw_weather_observation(
            elevation_band="mid",
            elevation_m=2500,
            observed_on="2024-03-05",
            snow_depth_m=1.3,
        ),
        _raw_weather_observation(
            elevation_band="mid",
            elevation_m=2500,
            observed_on="2024-03-06",
            snow_depth_m=1.4,
        ),
    )

    assert repository.upsert_observations(rows) == 2
    assert repository.upsert_observations(rows) == 2

    stored = repository.list_observations_for_resort(
        "tignes-ski-area",
        elevation_band="mid",
    )
    assert [row.observed_on for row in stored] == ["2024-03-05", "2024-03-06"]
    assert [row.snow_depth_m for row in stored] == [1.3, 1.4]


def test_snow_climatology_repository_upserts_and_lists_window_rows() -> None:
    repository = SnowClimatologyRepository()
    repository.upsert_daily_rows(
        (
            _snow_climatology_row(month=3, day=10),
            _snow_climatology_row(month=3, day=11),
            _snow_climatology_row(month=3, day=12, baseline_period="recent_15y"),
            _snow_climatology_row(month=4, day=10),
        )
    )

    grouped = repository.list_daily_rows_for_resorts_window(
        ("tignes-ski-area",),
        elevation_bands=("mid",),
        baseline_periods=("normal_30y", "recent_15y"),
        trip_start_date=date(2027, 3, 10),
        trip_end_date=date(2027, 3, 11),
    )

    normal_rows = grouped[("tignes-ski-area", "mid", "normal_30y")]
    recent_rows = grouped[("tignes-ski-area", "mid", "recent_15y")]
    assert [row.day for row in normal_rows] == [10, 11]
    assert recent_rows == ()


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


def test_repository_preserves_stable_stay_base_ids_and_optional_facts(tmp_path) -> None:
    resorts_path = tmp_path / "resorts.json"
    resorts_path.write_text(
        json.dumps(
            [
                {
                    "resort_id": "round-trip-resort",
                    "name": "Round Trip Resort",
                    "country": "France",
                    "region": "Northern Alps",
                    "price_level": "medium",
                    "latitude": 45.9,
                    "longitude": 6.8,
                    "base_elevation_m": 1200,
                    "summit_elevation_m": 2800,
                    "season_start_month": 12,
                    "season_end_month": 4,
                    "ski_areas": [
                        {
                            "ski_area_id": "round-trip-resort-ski-area",
                            "name": "Round Trip Ski Area",
                            "latitude": 45.9,
                            "longitude": 6.8,
                            "base_elevation_m": 1200,
                            "summit_elevation_m": 2800,
                            "season_start_month": 12,
                            "season_end_month": 4,
                        }
                    ],
                    "stay_bases": [
                        {
                            "stay_base_id": "round-trip-village",
                            "name": "Round Trip Village",
                            "price_range": "EUR 150-220",
                            "quality": "standard",
                            "lift_distance": "near",
                            "supported_skill_levels": ["beginner", "intermediate"],
                            "latitude": 45.91,
                            "longitude": 6.81,
                            "nearest_lift_name": "Village Gondola",
                            "nearest_lift_distance_m": 350,
                            "access_mode": "walk",
                            "base_type": "village",
                            "atmosphere_tags": ["quiet", "family"],
                            "regional_data_ids": {"osm": "node/123"},
                        }
                    ],
                    "rentals": [
                        {
                            "name": "Rental Shop",
                            "price_range": "EUR 40-60",
                            "quality": "standard",
                            "lift_distance": "near",
                        }
                    ],
                }
            ]
        )
    )
    bootstrap_database(resorts_path=resorts_path)

    resort = ResortRepository().get_resort_by_id("round-trip-resort")

    assert resort is not None
    stay_base = resort.stay_bases[0]
    assert stay_base.stay_base_id == "round-trip-village"
    assert stay_base.latitude == 45.91
    assert stay_base.longitude == 6.81
    assert stay_base.nearest_lift_name == "Village Gondola"
    assert stay_base.nearest_lift_distance_m == 350
    assert stay_base.access_mode == "walk"
    assert stay_base.base_type == "village"
    assert stay_base.atmosphere_tags == ["quiet", "family"]
    assert stay_base.regional_data_ids == {"osm": "node/123"}
    assert stay_base.supported_skill_levels == ["beginner", "intermediate"]


def _create_legacy_stay_base_schema_with_row() -> None:
    with connect() as connection:
        connection.execute("DROP TABLE stay_base_skill_levels")
        connection.execute("DROP TABLE stay_bases")
        connection.execute(
            """
            CREATE TABLE stay_bases (
                id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                resort_id TEXT NOT NULL REFERENCES resorts(resort_id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                price_range TEXT NOT NULL,
                price_min DOUBLE PRECISION NOT NULL,
                price_max DOUBLE PRECISION NOT NULL,
                quality TEXT NOT NULL,
                lift_distance TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO stay_bases (
                resort_id,
                name,
                price_range,
                price_min,
                price_max,
                quality,
                lift_distance
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "chamonix-mont-blanc",
                "Argentière Centre",
                "EUR 180-260",
                180,
                260,
                "standard",
                "near",
            ),
        )


def test_schema_migration_backfills_legacy_stay_base_ids() -> None:
    _create_legacy_stay_base_schema_with_row()
    with connect() as connection:
        _create_schema(connection)

        row = connection.execute(
            """
            SELECT stay_base_id
            FROM stay_bases
            WHERE resort_id = %s AND name = %s
            """,
            ("chamonix-mont-blanc", "Argentière Centre"),
        ).fetchone()

    assert row is not None
    assert row["stay_base_id"] == "chamonix-mont-blanc-argentiere-centre"

    resort = ResortRepository().get_resort_by_id("chamonix-mont-blanc")

    assert resort is not None
    assert resort.stay_bases[0].stay_base_id == (
        "chamonix-mont-blanc-argentiere-centre"
    )


def test_repository_auto_migrates_legacy_stay_base_schema_before_read() -> None:
    _create_legacy_stay_base_schema_with_row()

    resort = ResortRepository().get_resort_by_id("chamonix-mont-blanc")

    assert resort is not None
    assert resort.stay_bases[0].stay_base_id == (
        "chamonix-mont-blanc-argentiere-centre"
    )


def test_schema_migration_rejects_future_blank_stay_base_ids() -> None:
    with connect() as connection:
        _create_schema(connection)

        with pytest.raises(Exception):
            connection.execute(
                """
                UPDATE stay_bases
                SET stay_base_id = ''
                WHERE resort_id = %s
                """,
                ("chamonix-mont-blanc",),
            )


def test_schema_migration_rejects_future_null_stay_base_ids() -> None:
    with connect() as connection:
        _create_schema(connection)

        with pytest.raises(Exception):
            connection.execute(
                """
                UPDATE stay_bases
                SET stay_base_id = NULL
                WHERE resort_id = %s
                """,
                ("chamonix-mont-blanc",),
            )


def test_repository_defaults_malformed_stay_base_json_facts() -> None:
    with connect() as connection:
        connection.execute(
            """
            UPDATE stay_bases
            SET atmosphere_tags_json = %s,
                regional_data_ids_json = %s
            WHERE resort_id = %s
            """,
            ("not-json", "[1, 2, 3]", "chamonix-mont-blanc"),
        )

    resort = ResortRepository().get_resort_by_id("chamonix-mont-blanc")

    assert resort is not None
    assert resort.stay_bases[0].atmosphere_tags == []
    assert resort.stay_bases[0].regional_data_ids == {}


def test_repository_defaults_wrong_shaped_stay_base_json_facts() -> None:
    with connect() as connection:
        connection.execute(
            """
            UPDATE stay_bases
            SET atmosphere_tags_json = %s,
                regional_data_ids_json = %s
            WHERE resort_id = %s
            """,
            ('{"not": "a-list"}', '["not", "a-dict"]', "chamonix-mont-blanc"),
        )

    resort = ResortRepository().get_resort_by_id("chamonix-mont-blanc")

    assert resort is not None
    assert resort.stay_bases[0].atmosphere_tags == []
    assert resort.stay_bases[0].regional_data_ids == {}


def test_conditions_repository_returns_none_before_refresh() -> None:
    repository = ResortConditionsRepository()

    conditions = repository.get_conditions_for_resort("Chamonix Mont-Blanc")

    assert conditions is None


def test_conditions_repository_cache_expires_across_repository_instances() -> None:
    now = datetime(2026, 1, 15, tzinfo=UTC)
    reader = ResortConditionsRepository(
        conditions_cache_ttl=timedelta(minutes=5),
        clock=lambda: now,
    )
    writer = ResortConditionsRepository()

    assert reader.list_conditions() == {}

    writer.upsert_conditions(
        entity_id="tignes-ski-area",
        entity_name="Tignes",
        conditions=_resort_conditions("Tignes", conditions_score=0.91),
    )

    assert reader.list_conditions() == {}

    now += timedelta(minutes=6)

    refreshed_conditions = reader.list_conditions()

    assert refreshed_conditions["Tignes"].conditions_score == 0.91


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
