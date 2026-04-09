import sqlite3
from pathlib import Path

from app.data.loader import DEFAULT_RESORTS_PATH, load_resorts_from_path

DEFAULT_DB_PATH = Path(__file__).with_name("planner.db")


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def bootstrap_database(
    db_path: Path = DEFAULT_DB_PATH,
    *,
    resorts_path: Path = DEFAULT_RESORTS_PATH,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as connection:
        _create_schema(connection)
        _migrate_schema(connection)
        _sync_resorts_from_seed(connection, resorts_path)
        _clear_legacy_seeded_conditions(connection)


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS resorts (
            resort_id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            country TEXT NOT NULL,
            region TEXT NOT NULL,
            price_level TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            base_elevation_m INTEGER NOT NULL,
            summit_elevation_m INTEGER NOT NULL,
            season_start_month INTEGER NOT NULL,
            season_end_month INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resort_id TEXT NOT NULL REFERENCES resorts(resort_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            price_range TEXT NOT NULL,
            price_min REAL NOT NULL,
            price_max REAL NOT NULL,
            quality TEXT NOT NULL,
            lift_distance TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS area_skill_levels (
            area_id INTEGER NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
            skill_level TEXT NOT NULL,
            PRIMARY KEY (area_id, skill_level)
        );

        CREATE TABLE IF NOT EXISTS rentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resort_id TEXT NOT NULL REFERENCES resorts(resort_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            price_range TEXT NOT NULL,
            price_min REAL NOT NULL,
            price_max REAL NOT NULL,
            quality TEXT NOT NULL,
            lift_distance TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS resort_conditions (
            resort_id TEXT PRIMARY KEY REFERENCES resorts(resort_id) ON DELETE CASCADE,
            resort_name TEXT NOT NULL UNIQUE,
            snow_confidence_score REAL NOT NULL,
            snow_confidence_label TEXT NOT NULL,
            availability_status TEXT NOT NULL,
            weather_summary TEXT NOT NULL,
            conditions_score REAL NOT NULL,
            updated_at TEXT,
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS llm_parse_cache (
            cache_key TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS llm_narrative_cache (
            cache_key TEXT PRIMARY KEY,
            result_signature TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )


def _migrate_schema(connection: sqlite3.Connection) -> None:
    _ensure_column(connection, "resorts", "latitude", "REAL NOT NULL DEFAULT 0")
    _ensure_column(connection, "resorts", "longitude", "REAL NOT NULL DEFAULT 0")
    _ensure_column(
        connection, "resorts", "base_elevation_m", "INTEGER NOT NULL DEFAULT 0"
    )
    _ensure_column(
        connection, "resorts", "summit_elevation_m", "INTEGER NOT NULL DEFAULT 0"
    )
    _ensure_column(
        connection, "resorts", "season_start_month", "INTEGER NOT NULL DEFAULT 11"
    )
    _ensure_column(
        connection, "resorts", "season_end_month", "INTEGER NOT NULL DEFAULT 4"
    )
    _ensure_column(connection, "resort_conditions", "updated_at", "TEXT")
    _ensure_column(connection, "resort_conditions", "source", "TEXT")


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {
        row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})")
    }
    if column_name in columns:
        return
    connection.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
    )


def _sync_resorts_from_seed(connection: sqlite3.Connection, resorts_path: Path) -> None:
    resorts = load_resorts_from_path(resorts_path)
    seeded_ids = {resort.resort_id for resort in resorts}

    if seeded_ids:
        placeholders = ", ".join("?" for _ in seeded_ids)
        connection.execute(
            f"DELETE FROM resorts WHERE resort_id NOT IN ({placeholders})",
            tuple(seeded_ids),
        )

    for resort in resorts:
        connection.execute(
            """
            INSERT INTO resorts (
                resort_id,
                name,
                country,
                region,
                price_level,
                latitude,
                longitude,
                base_elevation_m,
                summit_elevation_m,
                season_start_month,
                season_end_month
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(resort_id) DO UPDATE SET
                name = excluded.name,
                country = excluded.country,
                region = excluded.region,
                price_level = excluded.price_level,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                base_elevation_m = excluded.base_elevation_m,
                summit_elevation_m = excluded.summit_elevation_m,
                season_start_month = excluded.season_start_month,
                season_end_month = excluded.season_end_month
            """,
            (
                resort.resort_id,
                resort.name,
                resort.country,
                resort.region,
                resort.price_level,
                resort.latitude,
                resort.longitude,
                resort.base_elevation_m,
                resort.summit_elevation_m,
                resort.season_start_month,
                resort.season_end_month,
            ),
        )
        connection.execute("DELETE FROM areas WHERE resort_id = ?", (resort.resort_id,))
        connection.execute(
            "DELETE FROM rentals WHERE resort_id = ?",
            (resort.resort_id,),
        )
        for area in resort.areas:
            cursor = connection.execute(
                """
                INSERT INTO areas (
                    resort_id,
                    name,
                    price_range,
                    price_min,
                    price_max,
                    quality,
                    lift_distance
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resort.resort_id,
                    area.name,
                    area.price_range,
                    area.price_min,
                    area.price_max,
                    area.quality,
                    area.lift_distance,
                ),
            )
            area_id = cursor.lastrowid
            for skill_level in area.supported_skill_levels:
                connection.execute(
                    """
                    INSERT INTO area_skill_levels (area_id, skill_level)
                    VALUES (?, ?)
                    """,
                    (area_id, skill_level),
                )
        for rental in resort.rentals:
            connection.execute(
                """
                INSERT INTO rentals (
                    resort_id,
                    name,
                    price_range,
                    price_min,
                    price_max,
                    quality,
                    lift_distance
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resort.resort_id,
                    rental.name,
                    rental.price_range,
                    rental.price_min,
                    rental.price_max,
                    rental.quality,
                    rental.lift_distance,
                ),
            )


def _clear_legacy_seeded_conditions(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM resort_conditions WHERE source IS NULL")
