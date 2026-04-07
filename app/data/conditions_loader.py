import json
from pathlib import Path

from pydantic import ValidationError

from app.domain.models import ResortConditions

DEFAULT_CONDITIONS_PATH = (
    Path(__file__).parent.parent / "integrations" / "conditions.json"
)


def load_conditions_from_path(path: Path) -> dict[str, ResortConditions]:
    try:
        payload = json.loads(path.read_text())
    except OSError as error:
        raise ValueError(f"Unable to read conditions data from {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}") from error

    try:
        return {
            item["resort_name"]: ResortConditions.model_validate(item)
            for item in payload
        }
    except KeyError as error:
        raise ValueError(f"Missing required field: {error.args[0]}") from error
    except ValidationError as error:
        raise ValueError("Invalid conditions data") from error
