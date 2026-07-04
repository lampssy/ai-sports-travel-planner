from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.catalog import CatalogSnapshot

pytestmark = pytest.mark.db_free

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "minimal-catalog.json"
REPO_ROOT = Path(__file__).parents[1]


def _run_catalog_cli(catalog_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "app.data.validate_catalog",
            "--catalog-path",
            str(catalog_path),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_load_catalog_from_path_returns_typed_snapshot() -> None:
    from app.data.catalog_loader import load_catalog_from_path

    snapshot = load_catalog_from_path(FIXTURE_PATH)

    assert isinstance(snapshot, CatalogSnapshot)
    assert snapshot.stay_destinations[0].stay_destination_id == "example"


def test_load_catalog_from_path_rejects_unsupported_schema_version(
    tmp_path: Path,
) -> None:
    from app.data.catalog_loader import load_catalog_from_path

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["schema_version"] = 1
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError, match="schema_version"):
        load_catalog_from_path(catalog_path)


def test_load_catalog_from_path_preserves_json_decode_error(tmp_path: Path) -> None:
    from app.data.catalog_loader import load_catalog_from_path

    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text('{"schema_version":', encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_catalog_from_path(catalog_path)


def test_load_catalog_from_path_preserves_missing_file_error(tmp_path: Path) -> None:
    from app.data.catalog_loader import load_catalog_from_path

    with pytest.raises(FileNotFoundError):
        load_catalog_from_path(tmp_path / "missing.json")


def test_load_catalog_caches_immutable_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.data import catalog_loader

    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(catalog_loader, "CATALOG_PATH", catalog_path)
    catalog_loader.load_catalog.cache_clear()

    try:
        first = catalog_loader.load_catalog()
        catalog_path.write_text('{"schema_version": 1}', encoding="utf-8")
        second = catalog_loader.load_catalog()

        assert second is first
        with pytest.raises(ValidationError, match="Instance is frozen"):
            second.schema_version = 1
    finally:
        catalog_loader.load_catalog.cache_clear()


def test_validate_catalog_cli_prints_deterministic_counts() -> None:
    result = _run_catalog_cli(FIXTURE_PATH)

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.strip() == (
        "[catalog-valid] schema_version=2 ski_regions=1 stay_destinations=1 "
        "stay_bases=1 ski_areas=1 access_links=1 terrain_domains=0 "
        "lift_pass_products=1 rental_display_facts=0"
    )


def test_validate_catalog_cli_reports_invalid_json(
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "invalid.json"
    catalog_path.write_text('{"schema_version":', encoding="utf-8")

    result = _run_catalog_cli(catalog_path)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "[catalog-invalid]" in result.stderr
    assert "invalid JSON" in result.stderr
    assert str(catalog_path) in result.stderr


def test_validate_catalog_cli_reports_invalid_utf8(tmp_path: Path) -> None:
    catalog_path = tmp_path / "invalid-utf8.json"
    catalog_path.write_bytes(b"\xff")

    result = _run_catalog_cli(catalog_path)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "[catalog-invalid]" in result.stderr
    assert "invalid UTF-8" in result.stderr
    assert str(catalog_path) in result.stderr
    assert "Traceback" not in result.stderr


def test_catalog_tools_do_not_connect_to_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.data import database

    def reject_database_connection(*args: object, **kwargs: object) -> None:
        raise AssertionError("catalog tools must not connect to the database")

    monkeypatch.setattr(database, "connect", reject_database_connection)
    sys.modules.pop("app.data.validate_catalog", None)
    sys.modules.pop("app.data.catalog_loader", None)

    loader_module = importlib.import_module("app.data.catalog_loader")
    cli_module = importlib.import_module("app.data.validate_catalog")

    assert loader_module.load_catalog_from_path(FIXTURE_PATH).schema_version == 2
    assert cli_module.main(["--catalog-path", str(FIXTURE_PATH)]) == 0
