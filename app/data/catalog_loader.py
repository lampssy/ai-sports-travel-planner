import json
from functools import lru_cache
from pathlib import Path

from app.domain.catalog import CatalogSnapshot

CATALOG_PATH = Path(__file__).with_name("catalog.json")


def load_catalog_from_path(path: Path) -> CatalogSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CatalogSnapshot.model_validate(payload)


@lru_cache(maxsize=1)
def load_catalog() -> CatalogSnapshot:
    return load_catalog_from_path(CATALOG_PATH)
