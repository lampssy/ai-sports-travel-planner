from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from app.domain.search_factors import build_factor_registry
from app.domain.search_policy import (
    DEFAULT_SEARCH_POLICY_PATH,
    load_search_policy,
    render_policy_inventory,
    replace_policy_inventory,
)

DEFAULT_MODEL_DOCUMENT_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "search-ranking-model.md"
)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render Search V4 policy and keep the canonical model inventory in sync."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of updating when the canonical inventory is stale.",
    )
    parser.add_argument(
        "--policy-path",
        type=Path,
        default=DEFAULT_SEARCH_POLICY_PATH,
        help="Explicit Search V4 TOML policy path.",
    )
    parser.add_argument(
        "--document-path",
        type=Path,
        default=DEFAULT_MODEL_DOCUMENT_PATH,
        help="Canonical Markdown document containing the generated marker block.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        policy = load_search_policy(args.policy_path)
        evaluator_statuses = build_factor_registry().evaluator_statuses()
        inventory = render_policy_inventory(
            policy, evaluator_statuses=evaluator_statuses
        )
        current = args.document_path.read_text(encoding="utf-8")
        expected = replace_policy_inventory(current, inventory)
    except (OSError, ValueError) as error:
        print(f"search policy inventory failed: {error}", file=sys.stderr)
        return 2

    if args.check:
        if current != expected:
            print(
                "search policy inventory is stale; run "
                "python -m app.data.explain_search_policy",
                file=sys.stderr,
            )
            return 1
        print(
            "search policy inventory is current: "
            f"model={policy.search_model_version} "
            f"policy={policy.ranking_policy_version}"
        )
        return 0

    args.document_path.write_text(expected, encoding="utf-8")
    print(inventory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
