from __future__ import annotations

import argparse

from ops.grafana.scripts.dashboard_resources import (
    DashboardValidationError,
    load_manifest,
    manifest_path_from_args,
    validate_or_raise,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Grafana dashboards.")
    parser.add_argument(
        "--manifest",
        default="ops/grafana/dashboards.manifest.json",
        help="Path to dashboards manifest.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    for entry in load_manifest(manifest_path_from_args(args)):
        try:
            dashboard = entry.load_dashboard()
            validate_or_raise(dashboard, source=str(entry.dashboard_path))
        except DashboardValidationError as error:
            failures.append(str(error))

    if failures:
        raise SystemExit("\n\n".join(failures))
    print("Grafana dashboard validation passed.")


if __name__ == "__main__":
    main()
