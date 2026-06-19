from __future__ import annotations

import argparse

from ops.grafana.scripts.alerting_resources import (
    DEFAULT_MANIFEST_PATH,
    client_from_env,
    deploy_from_manifest,
    manifest_path_from_args,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy repo-managed Grafana alerting resources.",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Path to the Grafana alerting manifest.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write alerting resources to Grafana. Omit for dry-run.",
    )
    args = parser.parse_args()

    client = client_from_env() if args.apply else None
    actions = deploy_from_manifest(
        manifest_path=manifest_path_from_args(args),
        client=client,
        apply=args.apply,
    )
    for name, action in actions:
        print(f"{action}: {name}")


if __name__ == "__main__":
    main()
