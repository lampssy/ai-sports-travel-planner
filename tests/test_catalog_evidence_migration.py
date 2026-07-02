from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.data.bootstrap_database as bootstrap_cli
import app.data.verify_catalog_evidence as evidence
from app.data.catalog_loader import load_catalog
from app.data.catalog_repository import CatalogRepository
from app.data.catalog_sync import sync_catalog_snapshot
from app.data.database import bootstrap_database, connect
from app.domain.catalog import CatalogSnapshot
from tests.test_catalog_models import minimal_catalog_payload

EVIDENCE_TABLES = (
    "raw_weather_history",
    "ski_area_snow_climatology_daily",
    "resort_conditions",
    "resort_condition_history",
)


def _seed_evidence_rows(ski_area_id: str) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO raw_weather_history (
                ski_area_id, resort_name, elevation_band, elevation_m,
                observed_on, observed_at, snowfall_cm, snow_depth_m,
                temperature_2m_max_c, temperature_2m_min_c,
                wind_speed_10m_max_kmh, wind_gusts_10m_max_kmh,
                weather_code, record_type, source, source_model
            ) VALUES (
                %s, 'Tignes', 'mid', 2500, '2024-03-05',
                '2024-03-05T12:00:00+00:00', 8, 1.3, -3, -9, 18, 24,
                3, 'archive', 'open-meteo', 'best_match'
            )
            """,
            (ski_area_id,),
        )
        connection.execute(
            """
            INSERT INTO ski_area_snow_climatology_daily (
                ski_area_id, resort_name, elevation_band, elevation_m,
                month, day, baseline_period, baseline_start_year,
                baseline_end_year, evidence_seasons, latest_archive_year,
                snow_depth_cm_p25, snow_depth_cm_p50, snow_depth_cm_p75,
                prob_snow_depth_ge_30cm, prob_snow_depth_ge_50cm,
                avg_daily_snowfall_cm, prob_rain_risk, prob_freeze_thaw,
                avg_max_temperature_c, avg_wind_gust_kmh,
                avg_snow_confidence_score, avg_conditions_score,
                source_model, computed_at
            ) VALUES (
                %s, 'Tignes', 'mid', 2500, 3, 10, 'normal_30y',
                1996, 2025, 30, 2025, 80, 120, 160, 0.93, 0.87,
                6.5, 0.07, 0.12, -2.4, 28, 0.82, 0.78,
                'snowcast_empirical_v1', '2026-06-15T00:00:00+00:00'
            )
            """,
            (ski_area_id,),
        )
        connection.execute(
            """
            INSERT INTO resort_conditions (
                ski_area_id, resort_name, snow_confidence_score,
                snow_confidence_label, availability_status, weather_summary,
                conditions_score, updated_at, source
            ) VALUES (
                %s, 'Tignes', 0.82, 'good', 'open', 'Fresh snow.', 0.76,
                '2026-01-15T00:00:00+00:00', 'open-meteo'
            )
            """,
            (ski_area_id,),
        )
        connection.execute(
            """
            INSERT INTO resort_condition_history (
                ski_area_id, resort_name, observed_month, observed_at,
                snow_confidence_score, snow_confidence_label,
                availability_status, weather_summary, conditions_score, source
            ) VALUES (
                %s, 'Tignes', 3, '2024-03-05T12:00:00+00:00', 0.82,
                'good', 'open', 'Fresh snow.', 0.76, 'open-meteo'
            )
            """,
            (ski_area_id,),
        )


def _evidence_counts(ski_area_id: str) -> dict[str, int]:
    with connect() as connection:
        return {
            table_name: connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name} WHERE ski_area_id = %s",
                (ski_area_id,),
            ).fetchone()["count"]
            for table_name in EVIDENCE_TABLES
        }


def _database_fingerprint() -> dict[str, object]:
    with connect() as connection:
        return {
            "ski_areas": connection.execute(
                """
                SELECT ski_area_id, is_active
                FROM ski_areas
                ORDER BY ski_area_id
                """
            ).fetchall(),
            "evidence_counts": {
                table_name: connection.execute(
                    f"SELECT COUNT(*) AS count FROM {table_name}"
                ).fetchone()["count"]
                for table_name in EVIDENCE_TABLES
            },
        }


def test_normalized_sync_preserves_weather_evidence_by_ski_area_id() -> None:
    bootstrap_database()
    _seed_evidence_rows("tignes-ski-area")
    before = _evidence_counts("tignes-ski-area")

    sync_catalog_snapshot(load_catalog())

    assert _evidence_counts("tignes-ski-area") == before
    assert CatalogRepository().get_ski_area("tignes-ski-area") is not None


def test_retiring_ski_area_preserves_all_evidence_and_hides_active_read() -> None:
    bootstrap_database()
    _seed_evidence_rows("tignes-ski-area")
    before = _evidence_counts("tignes-ski-area")
    sync_catalog_snapshot(load_catalog())

    sync_catalog_snapshot(CatalogSnapshot.model_validate(minimal_catalog_payload()))

    assert _evidence_counts("tignes-ski-area") == before
    assert CatalogRepository().get_ski_area("tignes-ski-area") is None
    with connect() as connection:
        area = connection.execute(
            "SELECT is_active FROM ski_areas WHERE ski_area_id = %s",
            ("tignes-ski-area",),
        ).fetchone()
    assert area == {"is_active": False}


def test_collect_evidence_counts_groups_all_four_tables_by_ski_area_id() -> None:
    bootstrap_database()
    _seed_evidence_rows("tignes-ski-area")

    counts = evidence.collect_evidence_counts()

    assert counts["tignes-ski-area"] == evidence.SkiAreaEvidenceCounts(
        raw_weather_history=1,
        climatology_daily=1,
        current_conditions=1,
        condition_history=1,
    )


def test_collect_evidence_counts_accepts_pre_cutover_evidence_key_names() -> None:
    bootstrap_database()
    _seed_evidence_rows("tignes-ski-area")
    with connect() as connection:
        connection.execute(
            "ALTER TABLE raw_weather_history RENAME COLUMN ski_area_id TO resort_id"
        )
        connection.execute(
            "ALTER TABLE resort_condition_history "
            "RENAME COLUMN ski_area_id TO resort_id"
        )

    counts = evidence.collect_evidence_counts()

    assert counts["tignes-ski-area"] == evidence.SkiAreaEvidenceCounts(
        raw_weather_history=1,
        climatology_daily=1,
        current_conditions=1,
        condition_history=1,
    )


def test_write_snapshot_is_deterministic_typed_and_read_only(tmp_path: Path) -> None:
    bootstrap_database()
    _seed_evidence_rows("tignes-ski-area")
    snapshot_path = tmp_path / "evidence.json"
    database_before = _database_fingerprint()

    assert evidence.main(["--write-snapshot", str(snapshot_path)]) == 0
    first_write = snapshot_path.read_text(encoding="utf-8")
    assert evidence.main(["--write-snapshot", str(snapshot_path)]) == 0

    parsed = evidence.CatalogEvidenceSnapshot.model_validate_json(first_write)
    payload = json.loads(first_write)
    assert snapshot_path.read_text(encoding="utf-8") == first_write
    assert first_write.endswith("\n")
    assert payload["schema_version"] == 1
    assert list(payload["ski_areas"]) == sorted(payload["ski_areas"])
    assert parsed.ski_areas["tignes-ski-area"].raw_weather_history == 1
    assert _database_fingerprint() == database_before


def test_compare_snapshot_fails_if_retained_area_loses_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bootstrap_database()
    _seed_evidence_rows("tignes-ski-area")
    snapshot_path = tmp_path / "evidence.json"
    assert evidence.main(["--write-snapshot", str(snapshot_path)]) == 0
    capsys.readouterr()
    with connect() as connection:
        connection.execute(
            "DELETE FROM raw_weather_history WHERE ski_area_id = %s",
            ("tignes-ski-area",),
        )

    exit_code = evidence.main(["--compare-snapshot", str(snapshot_path)])

    assert exit_code == 1
    assert (
        "tignes-ski-area raw_weather_history: expected at least 1, found 0"
        in capsys.readouterr().err
    )


def test_compare_snapshot_allows_evidence_count_increases(tmp_path: Path) -> None:
    bootstrap_database()
    _seed_evidence_rows("tignes-ski-area")
    snapshot_path = tmp_path / "evidence.json"
    assert evidence.main(["--write-snapshot", str(snapshot_path)]) == 0
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO raw_weather_history (
                ski_area_id, resort_name, elevation_band, elevation_m,
                observed_on, observed_at, snowfall_cm, snow_depth_m,
                temperature_2m_max_c, temperature_2m_min_c,
                wind_speed_10m_max_kmh, wind_gusts_10m_max_kmh,
                weather_code, record_type, source, source_model
            ) VALUES (
                %s, 'Tignes', 'mid', 2500, '2024-03-06',
                '2024-03-06T12:00:00+00:00', 4, 1.4, -2, -8, 16, 22,
                2, 'archive', 'open-meteo', 'best_match'
            )
            """,
            ("tignes-ski-area",),
        )

    database_before = _database_fingerprint()
    assert evidence.main(["--compare-snapshot", str(snapshot_path)]) == 0
    assert _database_fingerprint() == database_before


def test_compare_snapshot_requires_allowance_for_new_zero_evidence_area(
    tmp_path: Path,
) -> None:
    bootstrap_database()
    snapshot_path = tmp_path / "evidence.json"
    assert evidence.main(["--write-snapshot", str(snapshot_path)]) == 0
    sync_catalog_snapshot(CatalogSnapshot.model_validate(minimal_catalog_payload()))

    assert evidence.main(["--compare-snapshot", str(snapshot_path)]) == 1
    assert (
        evidence.main(
            [
                "--compare-snapshot",
                str(snapshot_path),
                "--allow-new-area",
                "example-area",
            ]
        )
        == 0
    )


def test_compare_snapshot_rejects_evidence_for_allowed_new_area(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bootstrap_database()
    snapshot_path = tmp_path / "evidence.json"
    assert evidence.main(["--write-snapshot", str(snapshot_path)]) == 0
    sync_catalog_snapshot(CatalogSnapshot.model_validate(minimal_catalog_payload()))
    _seed_evidence_rows("example-area")
    capsys.readouterr()

    exit_code = evidence.main(
        [
            "--compare-snapshot",
            str(snapshot_path),
            "--allow-new-area",
            "example-area",
        ]
    )

    assert exit_code == 1
    assert (
        "allowed new ski area example-area has evidence rows" in capsys.readouterr().err
    )


def test_compare_snapshot_rejects_invalid_typed_snapshot(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bootstrap_database()
    snapshot_path = tmp_path / "invalid-evidence.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "ski_areas": {
                    "tignes-ski-area": {
                        "raw_weather_history": "1",
                        "climatology_daily": 0,
                        "current_conditions": 0,
                        "condition_history": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = evidence.main(["--compare-snapshot", str(snapshot_path)])

    assert exit_code == 2
    assert "invalid evidence snapshot" in capsys.readouterr().err


def test_compare_snapshot_rejects_non_utf8_snapshot(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    snapshot_path = tmp_path / "invalid-encoding.json"
    snapshot_path.write_bytes(b"\xff\xfe")

    exit_code = evidence.main(["--compare-snapshot", str(snapshot_path)])

    assert exit_code == 2
    assert "invalid evidence snapshot" in capsys.readouterr().err


def test_bootstrap_cli_validates_catalog_before_database_access(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    catalog_path = tmp_path / "invalid-catalog.json"
    catalog_path.write_text('{"schema_version": 1}', encoding="utf-8")

    exit_code = bootstrap_cli.main(
        [
            "--catalog-path",
            str(catalog_path),
            "--database-url",
            "postgresql://planner:planner@127.0.0.1:1/unreachable",
        ]
    )

    assert exit_code == 2
    assert "catalog validation failed" in capsys.readouterr().err


def test_bootstrap_cli_upgrades_legacy_owner_shape_and_preserves_evidence(
    tmp_path: Path,
) -> None:
    bootstrap_database()
    _seed_evidence_rows("tignes-ski-area")
    before = evidence.build_evidence_snapshot()
    with connect() as connection:
        connection.execute(
            "ALTER TABLE ski_areas "
            "ADD COLUMN resort_id TEXT NOT NULL DEFAULT 'legacy-resort'"
        )
        connection.execute(
            "ALTER TABLE stay_bases "
            "ADD COLUMN resort_id TEXT NOT NULL DEFAULT 'legacy-resort'"
        )
        connection.execute(
            "ALTER TABLE raw_weather_history RENAME COLUMN ski_area_id TO resort_id"
        )
        connection.execute(
            "ALTER TABLE resort_condition_history "
            "RENAME COLUMN ski_area_id TO resort_id"
        )

    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(minimal_catalog_payload()),
        encoding="utf-8",
    )

    assert bootstrap_cli.main(["--catalog-path", str(catalog_path)]) == 0
    evidence.compare_evidence_snapshot(before, allow_new_area_ids={"example-area"})

    with connect() as connection:
        columns = {
            table_name: {
                row["column_name"]
                for row in connection.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema() AND table_name = %s
                    """,
                    (table_name,),
                ).fetchall()
            }
            for table_name in (
                "ski_areas",
                "stay_bases",
                "raw_weather_history",
                "resort_condition_history",
            )
        }

    assert "resort_id" not in columns["ski_areas"]
    assert "resort_id" not in columns["stay_bases"]
    assert "resort_id" not in columns["raw_weather_history"]
    assert "resort_id" not in columns["resort_condition_history"]


def test_bootstrap_cli_syncs_catalog_and_prints_bounded_counts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(minimal_catalog_payload()),
        encoding="utf-8",
    )

    exit_code = bootstrap_cli.main(["--catalog-path", str(catalog_path)])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == (
        "catalog sync complete: ski_regions=1 stay_destinations=1 "
        "stay_bases=1 ski_areas=1 ski_area_access=1 terrain_domains=0 "
        "lift_pass_products=1 rental_display_facts=0 relationships=2"
    )
