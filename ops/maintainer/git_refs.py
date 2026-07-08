from __future__ import annotations

import re

_SAFE_BRANCH_CHARACTERS = re.compile(r"^[A-Za-z0-9._/-]+$")


def is_safe_codex_branch(branch: object) -> bool:
    """Return whether a branch passes the repo's static codex/* ref policy."""

    if (
        not isinstance(branch, str)
        or not branch.startswith("codex/")
        or len(branch) == len("codex/")
        or _SAFE_BRANCH_CHARACTERS.fullmatch(branch) is None
        or branch.endswith(("/", "."))
        or "//" in branch
        or ".." in branch
        or "@{" in branch
    ):
        return False
    return not any(
        segment in {"", ".", ".."}
        or segment.startswith(("-", "."))
        or segment.endswith(".lock")
        for segment in branch.split("/")
    )
