from functools import lru_cache
from pathlib import Path

from app.data.database import DEFAULT_DB_PATH, bootstrap_database, connect
from app.domain.models import Area, Rental, Resort, ResortConditions


class ResortRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        bootstrap_database(self._db_path)

    def list_resorts(self) -> tuple[Resort, ...]:
        with connect(self._db_path) as connection:
            resort_rows = connection.execute(
                """
                SELECT resort_id, name, country, region, price_level
                FROM resorts
                ORDER BY name
                """
            ).fetchall()
            area_rows = connection.execute(
                """
                SELECT id, resort_id, name, price_range, price_min, price_max,
                       quality, lift_distance
                FROM areas
                ORDER BY resort_id, id
                """
            ).fetchall()
            skill_rows = connection.execute(
                """
                SELECT area_id, skill_level
                FROM area_skill_levels
                ORDER BY area_id, skill_level
                """
            ).fetchall()
            rental_rows = connection.execute(
                """
                SELECT resort_id, name, price_range, price_min, price_max,
                       quality, lift_distance
                FROM rentals
                ORDER BY resort_id, id
                """
            ).fetchall()

        skills_by_area: dict[int, list[str]] = {}
        for row in skill_rows:
            skills_by_area.setdefault(row["area_id"], []).append(row["skill_level"])

        areas_by_resort: dict[str, list[Area]] = {}
        for row in area_rows:
            areas_by_resort.setdefault(row["resort_id"], []).append(
                Area.model_validate(
                    {
                        "name": row["name"],
                        "price_range": row["price_range"],
                        "price_min": row["price_min"],
                        "price_max": row["price_max"],
                        "quality": row["quality"],
                        "lift_distance": row["lift_distance"],
                        "supported_skill_levels": skills_by_area.get(row["id"], []),
                    }
                )
            )

        rentals_by_resort: dict[str, list[Rental]] = {}
        for row in rental_rows:
            rentals_by_resort.setdefault(row["resort_id"], []).append(
                Rental.model_validate(
                    {
                        "name": row["name"],
                        "price_range": row["price_range"],
                        "price_min": row["price_min"],
                        "price_max": row["price_max"],
                        "quality": row["quality"],
                        "lift_distance": row["lift_distance"],
                    }
                )
            )

        return tuple(
            Resort.model_validate(
                {
                    "resort_id": row["resort_id"],
                    "name": row["name"],
                    "country": row["country"],
                    "region": row["region"],
                    "price_level": row["price_level"],
                    "areas": areas_by_resort.get(row["resort_id"], []),
                    "rentals": rentals_by_resort.get(row["resort_id"], []),
                }
            )
            for row in resort_rows
        )


class ResortConditionsRepository:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        bootstrap_database(self._db_path)

    def list_conditions(self) -> dict[str, ResortConditions]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT resort_name, snow_confidence_score, snow_confidence_label,
                       availability_status, weather_summary, conditions_score
                FROM resort_conditions
                ORDER BY resort_name
                """
            ).fetchall()

        return {
            row["resort_name"]: ResortConditions.model_validate(dict(row))
            for row in rows
        }

    def get_conditions_for_resort(self, resort_name: str) -> ResortConditions | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                """
                SELECT resort_name, snow_confidence_score, snow_confidence_label,
                       availability_status, weather_summary, conditions_score
                FROM resort_conditions
                WHERE resort_name = ?
                """,
                (resort_name,),
            ).fetchone()

        if row is None:
            return None
        return ResortConditions.model_validate(dict(row))


@lru_cache
def get_resort_repository(db_path: Path = DEFAULT_DB_PATH) -> ResortRepository:
    return ResortRepository(db_path)


@lru_cache
def get_conditions_repository(
    db_path: Path = DEFAULT_DB_PATH,
) -> ResortConditionsRepository:
    return ResortConditionsRepository(db_path)


def clear_repository_caches() -> None:
    get_resort_repository.cache_clear()
    get_conditions_repository.cache_clear()
