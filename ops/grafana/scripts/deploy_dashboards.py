from __future__ import annotations

import argparse

from ops.grafana.scripts.dashboard_resources import (
    client_from_env,
    deploy_from_manifest,
    manifest_path_from_args,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Grafana dashboards.")
    parser.add_argument(
        "--manifest",
        default="ops/grafana/dashboards.manifest.json",
        help="Path to dashboards manifest.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to Grafana. Omit for dry-run validation.",
    )
    args = parser.parse_args()

    client = client_from_env() if args.apply else None
    actions = deploy_from_manifest(
        manifest_path=manifest_path_from_args(args),
        client=client,
        apply=args.apply,
    )
    for name, action in actions:
        print(f"{name}: {action}")


if __name__ == "__main__":
    main()
