"""Shared contracts for the local Snowcast maintainer."""

REPOSITORY = "lampssy/ai-sports-travel-planner"
REPOSITORY_SSH_URL = "git@github.com-lampss:lampssy/ai-sports-travel-planner.git"
DEFAULT_BASE_BRANCH = "main"

SUMMARY_MARKER = "<!-- snowcast-maintainer-summary -->"
BODY_START = "<!-- snowcast-maintainer-body:start -->"
BODY_END = "<!-- snowcast-maintainer-body:end -->"

LABEL_DEFINITIONS = {
    "lane:catalog-discovery": (
        "Catalog discovery proposal workflow",
        "5319E7",
    ),
    "lane:catalog-curation": (
        "Catalog curation readiness workflow",
        "1D76DB",
    ),
    "maintainer:proposal": (
        "Waiting for owner onboarding decision",
        "D4C5F9",
    ),
    "maintainer:working": (
        "Automated review or remediation in progress",
        "FBCA04",
    ),
    "maintainer:waiting-ci": (
        "Automated work complete; required checks pending",
        "BFDADC",
    ),
    "maintainer:ready": (
        "Reviewed head is green and ready for owner merge",
        "0E8A16",
    ),
    "maintainer:owner-decision": (
        "Blocked on a product or domain decision",
        "D93F0B",
    ),
    "maintainer:manual-check": (
        "Requires focused manual investigation",
        "E99695",
    ),
    "maintainer:blocked": (
        "Automation cannot make safe progress",
        "B60205",
    ),
}
