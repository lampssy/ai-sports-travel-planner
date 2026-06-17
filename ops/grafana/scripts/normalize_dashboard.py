from __future__ import annotations

import argparse
from pathlib import Path

from ops.grafana.scripts.dashboard_resources import (
    load_json,
    normalize_dashboard_resource,
    validate_or_raise,
    write_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize an exported Grafana dashboard resource."
    )
    parser.add_argument("input", help="Path to exported dashboard JSON.")
    parser.add_argument("output", help="Path to write normalized dashboard JSON.")
    parser.add_argument("--name", required=True, help="Stable dashboard resource name.")
    parser.add_argument(
        "--folder-uid",
        default=None,
        help="Optional Grafana folder UID. Use an empty string for General.",
    )
    args = parser.parse_args()

    normalized = normalize_dashboard_resource(
        load_json(Path(args.input)),
        name=args.name,
        folder_uid=args.folder_uid,
    )
    validate_or_raise(normalized, source=args.output)
    write_json(Path(args.output), normalized)
    print(f"Wrote normalized dashboard: {args.output}")


if __name__ == "__main__":
    main()
