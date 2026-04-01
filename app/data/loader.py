import json
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from app.domain.models import Area, Rental, Resort


DEFAULT_RESORTS_PATH = Path(__file__).with_name("resorts.json")


def _parse_price_range(price_range: str) -> tuple[float, float]:
    normalized = price_range.replace("EUR", "").replace("€", "").strip()
    parts = normalized.split("-", maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Invalid price range: {price_range}")
    try:
        minimum = float(parts[0].strip())
        maximum = float(parts[1].strip())
    except ValueError as error:
        raise ValueError(f"Invalid price range: {price_range}") from error
    if minimum > maximum:
        raise ValueError(f"Invalid price range: {price_range}")
    return minimum, maximum


def _build_area(payload: dict) -> Area:
    minimum, maximum = _parse_price_range(payload["price_range"])
    return Area.model_validate(
        {
            **payload,
            "price_min": minimum,
            "price_max": maximum,
        }
    )


def _build_rental(payload: dict) -> Rental:
    minimum, maximum = _parse_price_range(payload["price_range"])
    return Rental.model_validate(
        {
            **payload,
            "price_min": minimum,
            "price_max": maximum,
        }
    )


def load_resorts_from_path(path: Path) -> list[Resort]:
    try:
        payload = json.loads(path.read_text())
    except OSError as error:
        raise ValueError(f"Unable to read resort data from {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}") from error

    resorts: list[Resort] = []
    try:
        for resort_payload in payload:
            areas = [_build_area(area) for area in resort_payload["areas"]]
            rentals = [_build_rental(rental) for rental in resort_payload["rentals"]]
            resorts.append(
                Resort.model_validate(
                    {
                        **resort_payload,
                        "areas": areas,
                        "rentals": rentals,
                    }
                )
            )
    except KeyError as error:
        raise ValueError(f"Missing required field: {error.args[0]}") from error
    except ValidationError as error:
        raise ValueError("Invalid resort data") from error

    return resorts


@lru_cache
def load_resorts() -> tuple[Resort, ...]:
    return tuple(load_resorts_from_path(DEFAULT_RESORTS_PATH))
