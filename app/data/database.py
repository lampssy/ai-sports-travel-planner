import os
import sqlite3
from pathlib import Path

from app.config.env import load_dotenv_file
from app.data.loader import DEFAULT_RESORTS_PATH, load_resorts_from_path

DEFAULT_DB_PATH = Path(__file__).with_name("planner.db")
DB_PATH_ENV_VAR = "APP_DB_PATH"


def resolve_db_path() -> Path:
    load_dotenv_file()
    configured = os.getenv(DB_PATH_ENV_VAR)
    if not configured:
        return DEFAULT_DB_PATH
    return Path(configured).expanduser()


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def bootstrap_database(
    db_path: Path | None = None,
    *,
    resorts_path: Path = DEFAULT_RESORTS_PATH,
) -> None:
    db_path = db_path or resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as connection:
        _create_schema(connection)
        _sync_resorts_from_seed(connection, resorts_path)
        _migrate_schema(connection)
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

        CREATE TABLE IF NOT EXISTS ski_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resort_id TEXT NOT NULL REFERENCES resorts(resort_id) ON DELETE CASCADE,
            ski_area_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            base_elevation_m INTEGER NOT NULL,
            summit_elevation_m INTEGER NOT NULL,
            season_start_month INTEGER NOT NULL,
            season_end_month INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stay_bases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resort_id TEXT NOT NULL REFERENCES resorts(resort_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            price_range TEXT NOT NULL,
            price_min REAL NOT NULL,
            price_max REAL NOT NULL,
            quality TEXT NOT NULL,
            lift_distance TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stay_base_skill_levels (
            stay_base_id INTEGER NOT NULL REFERENCES stay_bases(id) ON DELETE CASCADE,
            skill_level TEXT NOT NULL,
            PRIMARY KEY (stay_base_id, skill_level)
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
            resort_id TEXT PRIMARY KEY
                REFERENCES ski_areas(ski_area_id) ON DELETE CASCADE,
            resort_name TEXT NOT NULL UNIQUE,
            snow_confidence_score REAL NOT NULL,
            snow_confidence_label TEXT NOT NULL,
            availability_status TEXT NOT NULL,
            weather_summary TEXT NOT NULL,
            conditions_score REAL NOT NULL,
            updated_at TEXT,
            source TEXT
        );

        CREATE TABLE IF NOT EXISTS resort_condition_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resort_id TEXT NOT NULL REFERENCES ski_areas(ski_area_id) ON DELETE CASCADE,
            resort_name TEXT NOT NULL,
            observed_month INTEGER NOT NULL,
            observed_at TEXT NOT NULL,
            snow_confidence_score REAL NOT NULL,
            snow_confidence_label TEXT NOT NULL,
            availability_status TEXT NOT NULL,
            weather_summary TEXT NOT NULL,
            conditions_score REAL NOT NULL,
            source TEXT,
            UNIQUE(resort_id, observed_at)
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

        CREATE TABLE IF NOT EXISTS outbound_booking_clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            resort_id TEXT NOT NULL REFERENCES resorts(resort_id) ON DELETE CASCADE,
            selected_area_name TEXT NOT NULL,
            selected_ski_area_name TEXT,
            target_url TEXT NOT NULL,
            source_surface TEXT NOT NULL,
            request_id TEXT,
            user_agent TEXT
        );

        CREATE TABLE IF NOT EXISTS current_trip (
            singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
            resort_id TEXT NOT NULL REFERENCES resorts(resort_id) ON DELETE CASCADE,
            resort_name TEXT NOT NULL,
            selected_area_name TEXT NOT NULL,
            selected_ski_area_id TEXT,
            selected_ski_area_name TEXT,
            travel_month INTEGER,
            booking_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_checked_at TEXT
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
    _ensure_column(connection, "current_trip", "last_checked_at", "TEXT")
    _ensure_column(connection, "current_trip", "selected_ski_area_id", "TEXT")
    _ensure_column(connection, "current_trip", "selected_ski_area_name", "TEXT")
    _ensure_column(
        connection, "outbound_booking_clicks", "selected_ski_area_name", "TEXT"
    )
    _rebuild_condition_tables_for_ski_areas(connection)


def _rebuild_condition_tables_for_ski_areas(connection: sqlite3.Connection) -> None:
    foreign_keys = connection.execute(
        "PRAGMA foreign_key_list(resort_conditions)"
    ).fetchall()
    current_target = foreign_keys[0]["table"] if foreign_keys else None
    if current_target == "ski_areas":
        return

    condition_rows = connection.execute("SELECT * FROM resort_conditions").fetchall()
    history_rows = connection.execute(
        "SELECT * FROM resort_condition_history"
    ).fetchall()
    ski_area_rows = connection.execute(
        "SELECT resort_id, ski_area_id, name FROM ski_areas ORDER BY id"
    ).fetchall()

    ski_areas_by_id = {row["ski_area_id"]: row for row in ski_area_rows}
    ski_areas_by_name = {row["name"]: row for row in ski_area_rows}
    ski_areas_by_destination: dict[str, list[sqlite3.Row]] = {}
    for row in ski_area_rows:
        ski_areas_by_destination.setdefault(row["resort_id"], []).append(row)

    def remap_entity_id(entity_id: str, entity_name: str) -> str | None:
        if entity_id in ski_areas_by_id:
            return entity_id
        if entity_name in ski_areas_by_name:
            return ski_areas_by_name[entity_name]["ski_area_id"]
        destination_matches = ski_areas_by_destination.get(entity_id, [])
        if len(destination_matches) == 1:
            return destination_matches[0]["ski_area_id"]
        return None

    remapped_conditions = []
    for row in condition_rows:
        ski_area_id = remap_entity_id(row["resort_id"], row["resort_name"])
        if ski_area_id is None:
            continue
        remapped_conditions.append(
            (
                ski_area_id,
                row["resort_name"],
                row["snow_confidence_score"],
                row["snow_confidence_label"],
                row["availability_status"],
                row["weather_summary"],
                row["conditions_score"],
                row["updated_at"],
                row["source"],
            )
        )

    remapped_history = []
    for row in history_rows:
        ski_area_id = remap_entity_id(row["resort_id"], row["resort_name"])
        if ski_area_id is None:
            continue
        remapped_history.append(
            (
                ski_area_id,
                row["resort_name"],
                row["observed_month"],
                row["observed_at"],
                row["snow_confidence_score"],
                row["snow_confidence_label"],
                row["availability_status"],
                row["weather_summary"],
                row["conditions_score"],
                row["source"],
            )
        )

    connection.execute("DROP TABLE resort_conditions")
    connection.execute("DROP TABLE resort_condition_history")
    connection.executescript(
        """
        CREATE TABLE resort_conditions (
            resort_id TEXT PRIMARY KEY
                REFERENCES ski_areas(ski_area_id) ON DELETE CASCADE,
            resort_name TEXT NOT NULL UNIQUE,
            snow_confidence_score REAL NOT NULL,
            snow_confidence_label TEXT NOT NULL,
            availability_status TEXT NOT NULL,
            weather_summary TEXT NOT NULL,
            conditions_score REAL NOT NULL,
            updated_at TEXT,
            source TEXT
        );

        CREATE TABLE resort_condition_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resort_id TEXT NOT NULL REFERENCES ski_areas(ski_area_id) ON DELETE CASCADE,
            resort_name TEXT NOT NULL,
            observed_month INTEGER NOT NULL,
            observed_at TEXT NOT NULL,
            snow_confidence_score REAL NOT NULL,
            snow_confidence_label TEXT NOT NULL,
            availability_status TEXT NOT NULL,
            weather_summary TEXT NOT NULL,
            conditions_score REAL NOT NULL,
            source TEXT,
            UNIQUE(resort_id, observed_at)
        );
        """
    )
    connection.executemany(
        """
        INSERT INTO resort_conditions (
            resort_id,
            resort_name,
            snow_confidence_score,
            snow_confidence_label,
            availability_status,
            weather_summary,
            conditions_score,
            updated_at,
            source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        remapped_conditions,
    )
    connection.executemany(
        """
        INSERT INTO resort_condition_history (
            resort_id,
            resort_name,
            observed_month,
            observed_at,
            snow_confidence_score,
            snow_confidence_label,
            availability_status,
            weather_summary,
            conditions_score,
            source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        remapped_history,
    )


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
        connection.execute(
            """
            DELETE FROM stay_base_skill_levels
            WHERE stay_base_id IN (
                SELECT id FROM stay_bases WHERE resort_id = ?
            )
            """,
            (resort.resort_id,),
        )
        connection.execute(
            "DELETE FROM stay_bases WHERE resort_id = ?",
            (resort.resort_id,),
        )
        connection.execute(
            "DELETE FROM rentals WHERE resort_id = ?",
            (resort.resort_id,),
        )
        current_ski_area_ids = tuple(
            ski_area.ski_area_id for ski_area in resort.ski_areas
        )
        for ski_area in resort.ski_areas:
            connection.execute(
                """
                INSERT INTO ski_areas (
                    resort_id,
                    ski_area_id,
                    name,
                    latitude,
                    longitude,
                    base_elevation_m,
                    summit_elevation_m,
                    season_start_month,
                    season_end_month
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ski_area_id) DO UPDATE SET
                    resort_id = excluded.resort_id,
                    name = excluded.name,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    base_elevation_m = excluded.base_elevation_m,
                    summit_elevation_m = excluded.summit_elevation_m,
                    season_start_month = excluded.season_start_month,
                    season_end_month = excluded.season_end_month
                """,
                (
                    resort.resort_id,
                    ski_area.ski_area_id,
                    ski_area.name,
                    ski_area.latitude,
                    ski_area.longitude,
                    ski_area.base_elevation_m,
                    ski_area.summit_elevation_m,
                    ski_area.season_start_month,
                    ski_area.season_end_month,
                ),
            )
        if current_ski_area_ids:
            placeholders = ", ".join("?" for _ in current_ski_area_ids)
            connection.execute(
                f"""
                DELETE FROM ski_areas
                WHERE resort_id = ? AND ski_area_id NOT IN ({placeholders})
                """,
                (resort.resort_id, *current_ski_area_ids),
            )
        for stay_base in resort.stay_bases:
            cursor = connection.execute(
                """
                INSERT INTO stay_bases (
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
                    stay_base.name,
                    stay_base.price_range,
                    stay_base.price_min,
                    stay_base.price_max,
                    stay_base.quality,
                    stay_base.lift_distance,
                ),
            )
            stay_base_id = cursor.lastrowid
            for skill_level in stay_base.supported_skill_levels:
                connection.execute(
                    """
                    INSERT INTO stay_base_skill_levels (stay_base_id, skill_level)
                    VALUES (?, ?)
                    """,
                    (stay_base_id, skill_level),
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
