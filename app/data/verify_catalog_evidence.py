from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import psycopg
from psycopg import sql
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.data.database import connect


class SkiAreaEvidenceCounts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_weather_history: int = Field(ge=0, strict=True)
    climatology_daily: int = Field(ge=0, strict=True)
    current_conditions: int = Field(ge=0, strict=True)
    condition_history: int = Field(ge=0, strict=True)


class CatalogEvidenceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    ski_areas: dict[str, SkiAreaEvidenceCounts]

    @field_validator("ski_areas")
    @classmethod
    def validate_ski_area_ids(
        cls,
        ski_areas: dict[str, SkiAreaEvidenceCounts],
    ) -> dict[str, SkiAreaEvidenceCounts]:
        invalid_ids = [
            ski_area_id for ski_area_id in ski_areas if not ski_area_id.strip()
        ]
        if invalid_ids:
            raise ValueError("ski area evidence IDs must not be blank")
        return ski_areas


class EvidenceComparisonError(RuntimeError):
    """Raised when current evidence violates a saved preservation snapshot."""


EVIDENCE_TABLES = {
    "raw_weather_history": "raw_weather_history",
    "climatology_daily": "ski_area_snow_climatology_daily",
    "current_conditions": "resort_conditions",
    "condition_history": "resort_condition_history",
}


def collect_evidence_counts(
    database_url: str | None = None,
) -> dict[str, SkiAreaEvidenceCounts]:
    with connect(database_url) as connection:
        connection.read_only = True
        area_rows = connection.execute(
            "SELECT ski_area_id FROM ski_areas ORDER BY ski_area_id"
        ).fetchall()
        counts = {
            row["ski_area_id"]: {field_name: 0 for field_name in EVIDENCE_TABLES}
            for row in area_rows
        }
        for field_name, table_name in EVIDENCE_TABLES.items():
            key_column = _resolve_evidence_key_column(connection, table_name)
            rows = connection.execute(
                sql.SQL(
                    "SELECT {} AS ski_area_id, COUNT(*) AS count "
                    "FROM {} GROUP BY {} ORDER BY {}"
                ).format(
                    sql.Identifier(key_column),
                    sql.Identifier(table_name),
                    sql.Identifier(key_column),
                    sql.Identifier(key_column),
                )
            ).fetchall()
            for row in rows:
                counts.setdefault(
                    row["ski_area_id"],
                    {name: 0 for name in EVIDENCE_TABLES},
                )[field_name] = row["count"]

    return {
        ski_area_id: SkiAreaEvidenceCounts.model_validate(values)
        for ski_area_id, values in sorted(counts.items())
    }


def _resolve_evidence_key_column(
    connection: psycopg.Connection[Any],
    table_name: str,
) -> str:
    rows = connection.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
          AND column_name IN ('ski_area_id', 'resort_id')
        """,
        (table_name,),
    ).fetchall()
    columns = {row["column_name"] for row in rows}
    if "ski_area_id" in columns:
        return "ski_area_id"
    if "resort_id" in columns:
        return "resort_id"
    raise RuntimeError(f"{table_name} has no ski-area evidence key column")


def build_evidence_snapshot(
    database_url: str | None = None,
) -> CatalogEvidenceSnapshot:
    return CatalogEvidenceSnapshot(ski_areas=collect_evidence_counts(database_url))


def write_evidence_snapshot(
    path: Path,
    database_url: str | None = None,
) -> CatalogEvidenceSnapshot:
    snapshot = build_evidence_snapshot(database_url)
    serialized = json.dumps(
        snapshot.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )
    path.write_text(f"{serialized}\n", encoding="utf-8")
    return snapshot


def load_evidence_snapshot(path: Path) -> CatalogEvidenceSnapshot:
    return CatalogEvidenceSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def compare_evidence_snapshot(
    snapshot: CatalogEvidenceSnapshot,
    *,
    database_url: str | None = None,
    allow_new_area_ids: set[str] | frozenset[str] = frozenset(),
) -> None:
    current = collect_evidence_counts(database_url)
    expected_ids = set(snapshot.ski_areas)
    current_ids = set(current)
    failures: list[str] = []

    for ski_area_id in sorted(expected_ids - current_ids):
        failures.append(f"snapshot ski area {ski_area_id} is missing from database")

    for ski_area_id in sorted(expected_ids & current_ids):
        expected_counts = snapshot.ski_areas[ski_area_id]
        current_counts = current[ski_area_id]
        for field_name, expected_count in expected_counts.model_dump().items():
            current_count = getattr(current_counts, field_name)
            if current_count < expected_count:
                failures.append(
                    f"{ski_area_id} {field_name}: expected at least "
                    f"{expected_count}, found {current_count}"
                )

    for ski_area_id in sorted(current_ids - expected_ids):
        if ski_area_id not in allow_new_area_ids:
            failures.append(f"unexpected new ski area {ski_area_id}")
            continue
        if any(current[ski_area_id].model_dump().values()):
            failures.append(f"allowed new ski area {ski_area_id} has evidence rows")

    if failures:
        raise EvidenceComparisonError("\n".join(failures))


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory ski-area evidence without modifying the database."
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--write-snapshot",
        type=Path,
        metavar="PATH",
        help="Write current evidence counts to PATH.",
    )
    modes.add_argument(
        "--compare-snapshot",
        type=Path,
        metavar="PATH",
        help="Compare current evidence counts with PATH.",
    )
    parser.add_argument(
        "--allow-new-area",
        action="append",
        default=[],
        metavar="ID",
        help="Allow a new ski-area ID only when it has zero evidence rows.",
    )
    parser.add_argument(
        "--database-url",
        help="Explicit Postgres database URL. Defaults to DATABASE_URL.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.write_snapshot is not None:
        try:
            snapshot = write_evidence_snapshot(
                args.write_snapshot,
                database_url=args.database_url,
            )
        except OSError as error:
            print(f"unable to write evidence snapshot: {error}", file=sys.stderr)
            return 2
        print(
            "evidence snapshot written: "
            f"path={args.write_snapshot} ski_areas={len(snapshot.ski_areas)}"
        )
        return 0

    try:
        snapshot = load_evidence_snapshot(args.compare_snapshot)
    except (OSError, UnicodeError, ValidationError) as error:
        print(f"invalid evidence snapshot: {error}", file=sys.stderr)
        return 2
    try:
        compare_evidence_snapshot(
            snapshot,
            database_url=args.database_url,
            allow_new_area_ids=frozenset(args.allow_new_area),
        )
    except EvidenceComparisonError as error:
        print(f"evidence comparison failed:\n{error}", file=sys.stderr)
        return 1

    current_ids = set(collect_evidence_counts(args.database_url))
    retained_count = len(current_ids & set(snapshot.ski_areas))
    new_count = len(current_ids - set(snapshot.ski_areas))
    print(
        "evidence comparison passed: "
        f"retained_ski_areas={retained_count} new_ski_areas={new_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
