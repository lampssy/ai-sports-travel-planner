from __future__ import annotations

import argparse

from ops.grafana.scripts.alerting_resources import (
    DEFAULT_MANIFEST_PATH,
    manifest_path_from_args,
    validate_or_raise,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate repo-managed Grafana alerting resources.",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Path to the Grafana alerting manifest.",
    )
    args = parser.parse_args()

    manifest_path = manifest_path_from_args(args)
    validate_or_raise(manifest_path)
    print(f"Validated Grafana alerting resources: {manifest_path}")


if __name__ == "__main__":
    main()
