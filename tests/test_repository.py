from datetime import UTC, date, datetime, timedelta

from app.data.catalog_loader import load_catalog
from app.data.catalog_sync import sync_catalog_snapshot
from app.data.database import bootstrap_database, connect
from app.data.repositories import (
    AppUserRepository,
    CurrentTripRepository,
    RawWeatherHistoryRepository,
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    SnowClimatologyRepository,
    TravelCacheRepository,
)
from app.domain.models import (
    CurrentTrip,
    RawWeatherObservation,
    ResortConditions,
    ResortConditionSnapshot,
    SnowClimatologyDaily,
)
from app.domain.travel import TravelOrigin


def test_bootstrap_database_creates_schema_and_seeds_data() -> None:
    bootstrap_database()

    with connect() as connection:
        destination_count = connection.execute(
            "SELECT COUNT(*) AS count FROM stay_destinations WHERE is_active"
        ).fetchone()["count"]
        ski_area_count = connection.execute(
            "SELECT COUNT(*) AS count FROM ski_areas"
        ).fetchone()["count"]
        stay_base_count = connection.execute(
            "SELECT COUNT(*) AS count FROM stay_bases"
        ).fetchone()["count"]
        rental_count = connection.execute(
            "SELECT COUNT(*) AS count FROM rental_display_facts WHERE is_active"
        ).fetchone()["count"]
        terrain_domain_count = connection.execute(
            "SELECT COUNT(*) AS count FROM terrain_domains"
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
        legacy_resorts = connection.execute(
            "SELECT to_regclass('public.resorts') AS table_name"
        ).fetchone()["table_name"]

    assert 20 <= destination_count <= 40
    assert ski_area_count > 0
    assert stay_base_count > 0
    assert rental_count > 0
    assert terrain_domain_count >= 1
    assert conditions_count == 0
    assert travel_tables == {"travel_geocode_cache", "travel_route_cache"}
    assert legacy_resorts is None
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


def test_ski_area_evidence_foreign_keys_do_not_cascade_delete() -> None:
    bootstrap_database()

    with connect() as connection:
        constraints = {
            row["table_name"]: row["confdeltype"]
            for row in connection.execute(
                """
                SELECT source.relname AS table_name, constraint_row.confdeltype
                FROM pg_constraint constraint_row
                JOIN pg_class source ON source.oid = constraint_row.conrelid
                WHERE constraint_row.contype = 'f'
                  AND source.relname IN (
                    'raw_weather_history',
                    'ski_area_snow_climatology_daily',
                    'resort_conditions',
                    'resort_condition_history'
                  )
                """
            ).fetchall()
        }

    assert constraints == {
        "raw_weather_history": "r",
        "ski_area_snow_climatology_daily": "r",
        "resort_conditions": "r",
        "resort_condition_history": "r",
    }


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
    ski_area_id: str = "tignes-ski-area",
    resort_name: str = "Tignes",
    elevation_band: str,
    elevation_m: int,
    observed_on: str = "2024-03-05",
    snow_depth_m: float,
) -> RawWeatherObservation:
    return RawWeatherObservation(
        ski_area_id=ski_area_id,
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

    all_rows = repository.list_observations_for_ski_area("tignes-ski-area")
    mid_rows = repository.list_observations_for_ski_area(
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


def test_raw_weather_history_lists_multiple_ski_areas_by_band() -> None:
    repository = RawWeatherHistoryRepository()
    repository.upsert_observation(
        _raw_weather_observation(
            ski_area_id="tignes-ski-area",
            resort_name="Tignes",
            elevation_band="mid",
            elevation_m=2500,
            observed_on="2024-03-05",
            snow_depth_m=1.3,
        )
    )
    repository.upsert_observation(
        _raw_weather_observation(
            ski_area_id="cervinia-ski-area",
            resort_name="Cervinia",
            elevation_band="upper",
            elevation_m=3300,
            observed_on="2024-03-05",
            snow_depth_m=2.2,
        )
    )

    grouped = repository.list_observations_for_ski_areas(
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

    stored = repository.list_observations_for_ski_area(
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

    grouped = repository.list_daily_rows_for_ski_areas_window(
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

    deleted = repository.delete_observations_for_ski_area(
        ski_area_id="tignes-ski-area",
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 31),
        record_type="archive",
    )

    assert deleted == 1
    assert repository.list_observations_for_ski_area("tignes-ski-area") == ()


def test_weather_models_and_repositories_use_ski_area_id() -> None:
    raw_repository = RawWeatherHistoryRepository()
    history_repository = ResortConditionHistoryRepository()
    observation = _raw_weather_observation(
        elevation_band="mid",
        elevation_m=2500,
        snow_depth_m=1.3,
    )
    snapshot = ResortConditionSnapshot(
        ski_area_id="tignes-ski-area",
        resort_name="Tignes",
        observed_month=3,
        observed_at="2024-03-05T12:00:00+00:00",
        snow_confidence_score=0.82,
        snow_confidence_label="good",
        availability_status="open",
        weather_summary="Fresh snow.",
        conditions_score=0.76,
        source="open-meteo",
    )

    assert "resort_id" not in RawWeatherObservation.model_fields
    assert "resort_id" not in ResortConditionSnapshot.model_fields
    raw_repository.upsert_observation(observation)
    history_repository.append_snapshot(snapshot=snapshot)

    stored_observations = raw_repository.list_observations_for_ski_area(
        "tignes-ski-area"
    )
    stored_snapshots = history_repository.list_snapshots_for_ski_area("tignes-ski-area")

    assert stored_observations[0].ski_area_id == "tignes-ski-area"
    assert stored_snapshots[0].ski_area_id == "tignes-ski-area"


def test_conditions_repository_returns_none_before_refresh() -> None:
    repository = ResortConditionsRepository()

    conditions = repository.get_conditions_for_ski_area("brevent-flegere")

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

    assert refreshed_conditions["tignes-ski-area"].conditions_score == 0.91


def test_bootstrap_keeps_conditions_table_empty_in_fresh_database() -> None:
    bootstrap_database()
    bootstrap_database()

    with connect() as connection:
        conditions_count = connection.execute(
            "SELECT COUNT(*) AS count FROM resort_conditions"
        ).fetchone()["count"]

    assert conditions_count == 0


def test_current_trip_repository_round_trips_normalized_configuration() -> None:
    sync_catalog_snapshot(load_catalog())
    user = AppUserRepository().upsert_google_user(
        provider_subject="normalized-trip-user",
        email="normalized-trip@example.com",
        display_name="Normalized Trip User",
    )
    created_at = "2026-07-02T08:00:00+00:00"
    trip = CurrentTrip(
        ski_region_id="tignes-val-disere",
        ski_region_name="Tignes - Val d'Isere",
        stay_destination_id="tignes",
        stay_destination_name="Tignes",
        stay_base_id="tignes-val-claret",
        stay_base_name="Val Claret",
        focus_ski_area_id="tignes-ski-area",
        focus_ski_area_name="Tignes",
        lift_pass_product_id="tignes-val-disere-ski-pass",
        lift_pass_product_name="Tignes - Val d'Isere ski pass",
        travel_month=3,
        trip_start_date=None,
        trip_end_date=None,
        booking_status="not_booked_yet",
        created_at=created_at,
        updated_at=created_at,
        last_checked_at=None,
    )

    saved = CurrentTripRepository().upsert_current_trip(
        user_id=user.user_id,
        trip=trip,
    )

    assert saved == trip
    assert CurrentTripRepository().get_current_trip(user_id=user.user_id) == trip
