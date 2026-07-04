from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from app.data.catalog_v2_migration import (
    CatalogV2MigrationReport,
    build_migration_report,
    migrate_catalog_payload,
    migrate_trust_payload,
    reconcile_migration_report,
)


def _add_current_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--catalog-path", type=Path, required=True)
    parser.add_argument("--trust-manifest-path", type=Path, required=True)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate the Snowcast catalog and trust manifest to version 2."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    dry_run = commands.add_parser("dry-run")
    _add_current_paths(dry_run)

    write = commands.add_parser("write")
    _add_current_paths(write)
    write.add_argument("--report-path", type=Path, required=True)

    reconcile = commands.add_parser("reconcile")
    reconcile.add_argument("--base-catalog-path", type=Path, required=True)
    reconcile.add_argument("--current-catalog-path", type=Path, required=True)
    reconcile.add_argument("--base-trust-manifest-path", type=Path, required=True)
    reconcile.add_argument("--current-trust-manifest-path", type=Path, required=True)
    reconcile.add_argument("--report-path", type=Path, required=True)
    return parser.parse_args(argv)


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return dict(payload)


def _serialized(payload: Mapping[str, Any] | CatalogV2MigrationReport) -> str:
    if isinstance(payload, CatalogV2MigrationReport):
        value: Any = payload.model_dump(mode="json")
    else:
        value = payload
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _migrate(
    catalog_path: Path,
    trust_manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], CatalogV2MigrationReport]:
    before_catalog = _read_object(catalog_path)
    before_trust = _read_object(trust_manifest_path)
    after_catalog, audit = migrate_catalog_payload(before_catalog)
    after_trust = migrate_trust_payload(before_trust)
    report = build_migration_report(
        before_catalog=before_catalog,
        after_catalog=after_catalog,
        before_trust=before_trust,
        after_trust=after_trust,
        audit=audit,
    )
    reconcile_migration_report(
        report,
        before_catalog=before_catalog,
        after_catalog=after_catalog,
        before_trust=before_trust,
        after_trust=after_trust,
    )
    return after_catalog, after_trust, report


def _write_replacements(replacements: Mapping[Path, str]) -> None:
    resolved_paths = [path.resolve() for path in replacements]
    if len(set(resolved_paths)) != len(resolved_paths):
        raise ValueError("catalog, trust-manifest, and report paths must be distinct")
    temporary_paths: dict[Path, Path] = {}
    try:
        for path, content in replacements.items():
            temporary = path.with_name(f".{path.name}.catalog-v2.tmp")
            temporary.write_text(content, encoding="utf-8")
            temporary_paths[path] = temporary
        for path, temporary in temporary_paths.items():
            temporary.replace(path)
    finally:
        for temporary in temporary_paths.values():
            temporary.unlink(missing_ok=True)


def _run(args: argparse.Namespace) -> None:
    if args.command in {"dry-run", "write"}:
        catalog, trust, report = _migrate(
            args.catalog_path,
            args.trust_manifest_path,
        )
        if args.command == "dry-run":
            print(_serialized(report), end="")
            return
        _write_replacements(
            {
                args.catalog_path: _serialized(catalog),
                args.trust_manifest_path: _serialized(trust),
                args.report_path: _serialized(report),
            }
        )
        print(f"[catalog-v2-migration-written] report={args.report_path}")
        return

    report = CatalogV2MigrationReport.model_validate(_read_object(args.report_path))
    reconcile_migration_report(
        report,
        before_catalog=_read_object(args.base_catalog_path),
        after_catalog=_read_object(args.current_catalog_path),
        before_trust=_read_object(args.base_trust_manifest_path),
        after_trust=_read_object(args.current_trust_manifest_path),
    )
    print(f"[catalog-v2-migration-reconciled] report={args.report_path}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        _run(args)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        message = " ".join(str(error).splitlines())
        print(f"[catalog-v2-migration-invalid] {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
