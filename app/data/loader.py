import json
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from app.domain.models import Destination, Rental, SkiArea, StayBase

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


def _build_stay_base(payload: dict) -> StayBase:
    minimum, maximum = _parse_price_range(payload["price_range"])
    return StayBase.model_validate(
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


def _build_ski_area_from_payload(payload: dict) -> SkiArea:
    return SkiArea.model_validate(payload)


def _default_ski_area_from_destination(payload: dict) -> SkiArea:
    return SkiArea.model_validate(
        {
            "ski_area_id": f"{payload['resort_id']}-ski-area",
            "name": payload["name"],
            "latitude": payload["latitude"],
            "longitude": payload["longitude"],
            "base_elevation_m": payload["base_elevation_m"],
            "summit_elevation_m": payload["summit_elevation_m"],
            "season_start_month": payload["season_start_month"],
            "season_end_month": payload["season_end_month"],
        }
    )


def load_resorts_from_path(path: Path) -> list[Destination]:
    try:
        payload = json.loads(path.read_text())
    except OSError as error:
        raise ValueError(f"Unable to read resort data from {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}") from error

    resorts: list[Destination] = []
    try:
        for resort_payload in payload:
            stay_base_payloads = resort_payload.get("stay_bases") or resort_payload.get(
                "areas", []
            )
            stay_bases = [
                _build_stay_base(stay_base) for stay_base in stay_base_payloads
            ]
            ski_area_payloads = resort_payload.get("ski_areas")
            ski_areas = (
                [
                    _build_ski_area_from_payload(ski_area)
                    for ski_area in ski_area_payloads
                ]
                if ski_area_payloads
                else [_default_ski_area_from_destination(resort_payload)]
            )
            rentals = [_build_rental(rental) for rental in resort_payload["rentals"]]
            resorts.append(
                Destination.model_validate(
                    {
                        **resort_payload,
                        "stay_bases": stay_bases,
                        "ski_areas": ski_areas,
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
def load_resorts() -> tuple[Destination, ...]:
    return tuple(load_resorts_from_path(DEFAULT_RESORTS_PATH))
