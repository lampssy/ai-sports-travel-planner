from __future__ import annotations

import json
from collections.abc import Iterable

import pytest

from ops.maintainer.intent import (
    IntentDriftError,
    IntentSnapshot,
    IntentValidationError,
    build_intent_snapshot,
    compare_intent,
)

pytestmark = pytest.mark.db_free


CATALOG_SECTIONS = {
    "ski_regions": "ski_region_id",
    "stay_destinations": "stay_destination_id",
    "stay_bases": "stay_base_id",
    "ski_areas": "ski_area_id",
    "ski_area_access": "ski_area_access_id",
    "terrain_domains": "terrain_domain_id",
    "lift_pass_products": "lift_pass_product_id",
    "rental_display_facts": "rental_display_fact_id",
}


class FakeIntentRepository:
    def __init__(
        self,
        changed_paths: Iterable[str],
        revisions: dict[tuple[str, str], str],
    ) -> None:
        self._changed_paths = tuple(changed_paths)
        self._revisions = revisions
        self.show_calls: list[tuple[str, str]] = []

    def diff_names(self, base: str, head: str) -> tuple[str, ...]:
        assert (base, head) == ("base", "head")
        return self._changed_paths

    def show_text(self, revision: str, path: str) -> str:
        self.show_calls.append((revision, path))
        try:
            return self._revisions[(revision, path)]
        except KeyError as error:
            raise RuntimeError(f"missing {revision}:{path}") from error


def _catalog(**rows: list[dict[str, object]]) -> str:
    payload: dict[str, object] = {"schema_version": 2}
    payload.update({section: rows.get(section, []) for section in CATALOG_SECTIONS})
    return json.dumps(payload)


def _snapshot(
    *,
    changed_paths: frozenset[str] = frozenset({"app/data/catalog.json"}),
    catalog_targets: frozenset[str] = frozenset({"ski_area:alpha"}),
    report_targets: frozenset[str] = frozenset({"ski_area:alpha"}),
    removed_backlog_markers: frozenset[str] = frozenset({"ski_area:alpha"}),
) -> IntentSnapshot:
    return IntentSnapshot(
        changed_paths=changed_paths,
        catalog_targets=catalog_targets,
        report_targets=report_targets,
        removed_backlog_markers=removed_backlog_markers,
    )


def test_compare_intent_accepts_equal_semantic_intent_and_removed_paths() -> None:
    before = _snapshot(
        changed_paths=frozenset(
            {"app/data/catalog.json", "tests/test_catalog_alpha.py"}
        )
    )
    after = _snapshot()

    compare_intent(before, after)


@pytest.mark.parametrize(
    ("field", "value", "diagnostic"),
    [
        (
            "changed_paths",
            frozenset({"app/data/catalog.json", "docs/product-backlog.md"}),
            "changed_paths added: docs/product-backlog.md",
        ),
        (
            "catalog_targets",
            frozenset({"ski_area:alpha", "ski_area:beta"}),
            "catalog_targets added: ski_area:beta",
        ),
        (
            "report_targets",
            frozenset({"ski_area:alpha", "trust_manifest:ski_areas:alpha"}),
            "report_targets added: trust_manifest:ski_areas:alpha",
        ),
        (
            "removed_backlog_markers",
            frozenset({"ski_area:alpha", "ski_area:beta"}),
            "removed_backlog_markers added: ski_area:beta",
        ),
    ],
)
def test_compare_intent_rejects_added_items_with_diagnostic(
    field: str,
    value: frozenset[str],
    diagnostic: str,
) -> None:
    before = _snapshot()
    values = before.model_dump()
    values[field] = value
    after = IntentSnapshot.model_validate(values)

    with pytest.raises(IntentDriftError, match=diagnostic):
        compare_intent(before, after)


def test_compare_intent_reports_removed_semantic_targets() -> None:
    before = _snapshot(catalog_targets=frozenset({"ski_area:alpha", "ski_area:beta"}))

    with pytest.raises(
        IntentDriftError,
        match="catalog_targets removed: ski_area:beta",
    ):
        compare_intent(before, _snapshot())


def test_catalog_changes_map_all_supported_sections_to_typed_targets() -> None:
    base = _catalog()
    changed_rows = {
        section: [{id_field: f"{section.replace('_', '-')}-id", "name": "changed"}]
        for section, id_field in CATALOG_SECTIONS.items()
    }
    head = _catalog(**changed_rows)
    repository = FakeIntentRepository(
        ["app/data/catalog.json"],
        {
            ("base", "app/data/catalog.json"): base,
            ("head", "app/data/catalog.json"): head,
        },
    )

    snapshot = build_intent_snapshot(repository, "base", "head")

    assert snapshot.catalog_targets == frozenset(
        {
            "ski_region:ski-regions-id",
            "stay_destination:stay-destinations-id",
            "stay_base:stay-bases-id",
            "ski_area:ski-areas-id",
            "ski_area_access:ski-area-access-id",
            "terrain_domain:terrain-domains-id",
            "lift_pass_product:lift-pass-products-id",
            "rental_display_fact:rental-display-facts-id",
        }
    )


def test_catalog_comparison_rejects_duplicate_typed_ids() -> None:
    duplicate = _catalog(
        ski_areas=[
            {"ski_area_id": "alpha", "name": "one"},
            {"ski_area_id": "alpha", "name": "two"},
        ]
    )
    repository = FakeIntentRepository(
        ["app/data/catalog.json"],
        {
            ("base", "app/data/catalog.json"): _catalog(),
            ("head", "app/data/catalog.json"): duplicate,
        },
    )

    with pytest.raises(IntentValidationError, match="duplicate ski_area_id alpha"):
        build_intent_snapshot(repository, "base", "head")


def test_catalog_comparison_requires_schema_version_two() -> None:
    repository = FakeIntentRepository(
        ["app/data/catalog.json"],
        {
            ("base", "app/data/catalog.json"): _catalog(),
            (
                "head",
                "app/data/catalog.json",
            ): _catalog().replace('"schema_version": 2', '"schema_version": 1'),
        },
    )

    with pytest.raises(IntentValidationError, match="catalog schema_version must be 2"):
        build_intent_snapshot(repository, "base", "head")


def test_schema_v2_report_collects_reviewed_scope_and_trust_targets() -> None:
    path = "docs/catalog-curation/alpha.json"
    report = {
        "report_schema_version": 2,
        "reviewed_targets": [
            {"target_type": "ski_area", "target_id": "alpha"},
            {
                "target_type": "trust_manifest",
                "target_id": "ski_areas:alpha",
            },
        ],
        "entity_scope_assessments": [
            {
                "target_refs": [
                    {"target_type": "stay_base", "target_id": "alpha-village"}
                ]
            }
        ],
    }
    repository = FakeIntentRepository(
        [path],
        {("head", path): json.dumps(report)},
    )

    snapshot = build_intent_snapshot(repository, "base", "head")

    assert snapshot.report_targets == frozenset(
        {
            "ski_area:alpha",
            "stay_base:alpha-village",
            "trust_manifest:ski_areas:alpha",
        }
    )
    assert repository.show_calls == [("head", path)]


def test_report_target_can_be_declared_by_review_and_scope_without_drift() -> None:
    path = "docs/catalog-curation/alpha.json"
    report = {
        "report_schema_version": 2,
        "reviewed_targets": [
            {"target_type": "ski_area", "target_id": "alpha"},
        ],
        "entity_scope_assessments": [
            {
                "target_refs": [
                    {"target_type": "ski_area", "target_id": "alpha"},
                ]
            }
        ],
    }
    repository = FakeIntentRepository(
        [path],
        {("head", path): json.dumps(report)},
    )

    snapshot = build_intent_snapshot(repository, "base", "head")

    assert snapshot.report_targets == frozenset({"ski_area:alpha"})


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not-json", "invalid JSON"),
        ('{"report_schema_version": NaN}', "invalid JSON"),
        (json.dumps([{"report_schema_version": 2}]), "must be a JSON object"),
        (
            json.dumps(
                {
                    "report_schema_version": 1,
                    "reviewed_targets": [],
                    "entity_scope_assessments": [],
                }
            ),
            "report_schema_version must be 2",
        ),
    ],
)
def test_changed_report_rejects_malformed_or_v1_content(
    content: str,
    message: str,
) -> None:
    path = "docs/catalog-curation/alpha.json"
    repository = FakeIntentRepository([path], {("head", path): content})

    with pytest.raises(IntentValidationError, match=message):
        build_intent_snapshot(repository, "base", "head")


def test_changed_report_rejects_deletion_instead_of_ignoring_it() -> None:
    path = "docs/catalog-curation/alpha.json"
    repository = FakeIntentRepository([path], {})

    with pytest.raises(IntentValidationError, match="cannot read changed report"):
        build_intent_snapshot(repository, "base", "head")


def test_backlog_parser_only_tracks_exact_markers_in_exact_section() -> None:
    path = "docs/product-backlog.md"
    base = """# Backlog

## Catalog Curation Réfinements

- `ski_area:unicode-heading`

## Catalog Curation Refinements

- `ski_area:removed`
- ski_area:not-backticked
- ``ski_area:double-backticks``
- `ski_region:unsupported-kind`

## Another Section

- `ski_area:outside`
"""
    head = base.replace("- `ski_area:removed`\n", "")
    repository = FakeIntentRepository(
        [path],
        {("base", path): base, ("head", path): head},
    )

    snapshot = build_intent_snapshot(repository, "base", "head")

    assert snapshot.removed_backlog_markers == frozenset({"ski_area:removed"})


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "docs/catalog-curation-evil/report.json",
        "tests/test_catalogue.py",
        "docs/catalog-curation/../secrets.json",
        "docs/catalog-curation/./report.json",
        "docs/catalog-curation//report.json",
        "docs/catalog-curation/",
        "/docs/catalog-curation/report.json",
    ],
)
def test_unexpected_or_traversal_path_is_rejected_exactly(path: str) -> None:
    repository = FakeIntentRepository([path], {})

    with pytest.raises(IntentValidationError, match="unexpected changed paths") as exc:
        build_intent_snapshot(repository, "base", "head")

    assert path in str(exc.value)
