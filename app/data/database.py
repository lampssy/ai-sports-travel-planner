import sqlite3
from pathlib import Path

from app.data.conditions_loader import (
    DEFAULT_CONDITIONS_PATH,
    load_conditions_from_path,
)
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
    conditions_path: Path = DEFAULT_CONDITIONS_PATH,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as connection:
        _create_schema(connection)
        _seed_resorts_if_empty(connection, resorts_path)
        _seed_conditions_if_empty(connection, conditions_path)


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS resorts (
            resort_id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            country TEXT NOT NULL,
            region TEXT NOT NULL,
            price_level TEXT NOT NULL
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
            conditions_score REAL NOT NULL
        );
        """
    )


def _seed_resorts_if_empty(connection: sqlite3.Connection, resorts_path: Path) -> None:
    resort_count = connection.execute("SELECT COUNT(*) FROM resorts").fetchone()[0]
    if resort_count:
        return

    resorts = load_resorts_from_path(resorts_path)
    for resort in resorts:
        connection.execute(
            """
            INSERT INTO resorts (resort_id, name, country, region, price_level)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                resort.resort_id,
                resort.name,
                resort.country,
                resort.region,
                resort.price_level,
            ),
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


def _seed_conditions_if_empty(
    connection: sqlite3.Connection,
    conditions_path: Path,
) -> None:
    conditions_count = connection.execute(
        "SELECT COUNT(*) FROM resort_conditions"
    ).fetchone()[0]
    if conditions_count:
        return

    resorts_by_name = {
        row["name"]: row["resort_id"]
        for row in connection.execute("SELECT resort_id, name FROM resorts")
    }
    conditions = load_conditions_from_path(conditions_path)
    for resort_name, condition in conditions.items():
        connection.execute(
            """
            INSERT INTO resort_conditions (
                resort_id,
                resort_name,
                snow_confidence_score,
                snow_confidence_label,
                availability_status,
                weather_summary,
                conditions_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resorts_by_name[resort_name],
                resort_name,
                condition.snow_confidence_score,
                condition.snow_confidence_label,
                condition.availability_status,
                condition.weather_summary,
                condition.conditions_score,
            ),
        )
