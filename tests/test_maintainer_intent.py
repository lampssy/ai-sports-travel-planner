from __future__ import annotations

import json
from collections.abc import Iterable

import pytest

from app.domain.catalog import CatalogSnapshot
from ops.maintainer.intent import (
    CATALOG_SECTIONS as INTENT_CATALOG_SECTIONS,
)
from ops.maintainer.intent import (
    IntentDiffEntry,
    IntentDriftError,
    IntentSnapshot,
    IntentValidationError,
    build_intent_snapshot,
    compare_intent,
    is_allowed_curation_path,
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
        *,
        entries: Iterable[IntentDiffEntry] | None = None,
    ) -> None:
        self._changed_paths = tuple(changed_paths)
        self._entries = (
            tuple(entries)
            if entries is not None
            else tuple(
                IntentDiffEntry(
                    path=path,
                    old_mode="100644",
                    new_mode="100644",
                    old_oid="a" * 40,
                    new_oid="b" * 40,
                    status="M",
                )
                for path in self._changed_paths
            )
        )
        self._revisions = revisions
        self.show_calls: list[tuple[str, str]] = []

    def diff_names(self, base: str, head: str) -> tuple[str, ...]:
        assert (base, head) == ("base", "head")
        return self._changed_paths

    def diff_entries(self, base: str, head: str) -> tuple[IntentDiffEntry, ...]:
        assert (base, head) == ("base", "head")
        return self._entries

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


def _valid_full_report() -> dict[str, object]:
    return {
        "report_schema_version": 2,
        "title": "Alpha full curation",
        "summary": "Reviews Alpha against its official source.",
        "reviewed_targets": [
            {
                "target_type": "ski_area",
                "target_id": "alpha",
                "scope": "narrow",
                "required_field_paths": ["name"],
            },
            {
                "target_type": "trust_manifest",
                "target_id": "ski_areas:alpha",
                "scope": "narrow",
                "required_field_paths": ["display_name"],
            },
        ],
        "entity_scope_assessments": [
            {
                "candidate_id": "alpha",
                "candidate_name": "Alpha",
                "candidate_kind": "ski_area",
                "disposition": "represented",
                "signals": ["official_independent_identity"],
                "evidence_refs": ["alpha-scope"],
                "target_refs": [
                    {"target_type": "ski_area", "target_id": "alpha"},
                ],
                "rationale": "The official source confirms the represented entity.",
            }
        ],
        "evidence": [
            {
                "evidence_id": "alpha-scope",
                "target_type": "ski_area",
                "target_id": "alpha",
                "field_path": "name",
                "source_type": "official",
                "source_url": "https://example.com/alpha",
                "source_title": "Official Alpha",
                "source_value": "Alpha",
                "evidence_summary": "Confirms Alpha's independent identity.",
            }
        ],
        "field_coverage": [
            {
                "target_type": "ski_area",
                "target_id": "alpha",
                "field_path": "name",
                "status": "reviewed-no-change",
            },
            {
                "target_type": "trust_manifest",
                "target_id": "ski_areas:alpha",
                "field_path": "display_name",
                "status": "reviewed-no-change",
            },
        ],
    }


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
    ("path", "allowed"),
    [
        ("app/data/catalog.json", True),
        ("docs/catalog-curation/report.json", True),
        ("tests/test_catalog_alpha.py", False),
        ("README.md", False),
        ("../app/data/catalog.json", False),
    ],
)
def test_public_owned_path_predicate_matches_task4_contract(
    path: str,
    allowed: bool,
) -> None:
    assert is_allowed_curation_path(path) is allowed


@pytest.mark.parametrize(
    ("field", "value", "diagnostic"),
    [
        (
            "changed_paths",
            frozenset({"app/data/catalog.json", "docs/product-backlog.md"}),
            "changed_paths added: 'docs/product-backlog.md'",
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


def test_catalog_intent_descriptors_cover_catalog_snapshot_entity_sections() -> None:
    snapshot_sections = set(CatalogSnapshot.model_fields) - {"schema_version"}

    assert {section for section, _, _ in INTENT_CATALOG_SECTIONS} == snapshot_sections


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


def test_full_schema_v2_report_collects_reviewed_scope_and_trust_targets() -> None:
    path = "docs/catalog-curation/alpha.json"
    report = _valid_full_report()
    repository = FakeIntentRepository(
        [path],
        {("head", path): json.dumps(report)},
    )

    snapshot = build_intent_snapshot(repository, "base", "head")

    assert snapshot.report_targets == frozenset(
        {
            "ski_area:alpha",
            "trust_manifest:ski_areas:alpha",
        }
    )
    assert repository.show_calls == [("head", path)]


def test_report_target_can_be_declared_by_review_and_scope_without_drift() -> None:
    path = "docs/catalog-curation/alpha.json"
    report = _valid_full_report()
    repository = FakeIntentRepository(
        [path],
        {("head", path): json.dumps(report)},
    )

    snapshot = build_intent_snapshot(repository, "base", "head")

    assert snapshot.report_targets == frozenset(
        {"ski_area:alpha", "trust_manifest:ski_areas:alpha"}
    )


def test_incomplete_schema_v2_report_is_rejected_with_path_context() -> None:
    path = "docs/catalog-curation/incomplete.json"
    report = {
        "report_schema_version": 2,
        "reviewed_targets": [],
        "entity_scope_assessments": [],
    }
    repository = FakeIntentRepository(
        [path],
        {("head", path): json.dumps(report)},
    )

    with pytest.raises(IntentValidationError, match=path) as exc:
        build_intent_snapshot(repository, "base", "head")

    assert "title" in str(exc.value)
    assert "summary" in str(exc.value)


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


@pytest.mark.parametrize(
    ("old_mode", "new_mode", "old_oid", "new_oid", "status"),
    [
        ("120000", "120000", "a" * 40, "b" * 40, "M"),
        ("160000", "160000", "a" * 40, "b" * 40, "M"),
        ("100644", "100755", "a" * 40, "a" * 40, "M"),
        ("100644", "120000", "a" * 40, "b" * 40, "T"),
        ("100644", "100644", "not-an-oid", "b" * 40, "M"),
    ],
)
def test_intent_rejects_symlink_submodule_type_and_mode_tricks(
    old_mode: str,
    new_mode: str,
    old_oid: str,
    new_oid: str,
    status: str,
) -> None:
    path = "tests/test_catalog_alpha.py"
    entry = IntentDiffEntry(
        path=path,
        old_mode=old_mode,
        new_mode=new_mode,
        old_oid=old_oid,
        new_oid=new_oid,
        status=status,
    )
    repository = FakeIntentRepository([path], {}, entries=[entry])

    with pytest.raises(IntentValidationError, match="unsafe diff metadata"):
        build_intent_snapshot(repository, "base", "head")


@pytest.mark.parametrize(
    "path",
    [
        "docs/catalog-curation/nested/report.json",
        "docs/catalog-curation/report.txt",
        "tests/test_catalog_alpha.py/extra",
        "tests/test_catalog_alpha.txt",
        "docs/catalog-discovery/nested/report.json",
        "docs/catalog-discovery/report.md",
        "tests/test_catalog_bad\x7f.py",
    ],
)
def test_intent_rejects_allowed_prefix_shape_bypasses(path: str) -> None:
    repository = FakeIntentRepository([path], {})

    with pytest.raises(IntentValidationError, match="unexpected changed paths"):
        build_intent_snapshot(repository, "base", "head")


def test_intent_rejects_executable_catalog_test_changes() -> None:
    path = "tests/test_catalog_alpha.py"
    repository = FakeIntentRepository([path], {})

    with pytest.raises(IntentValidationError, match="unexpected changed paths"):
        build_intent_snapshot(repository, "base", "head")


@pytest.mark.parametrize(
    "path",
    [
        "docs/catalog-curation/report.json",
        "docs/catalog-curation/report.md",
        "docs/catalog-discovery/report.json",
    ],
)
def test_intent_accepts_only_expected_top_level_artifact_shapes(path: str) -> None:
    revisions: dict[tuple[str, str], str] = {}
    if path.endswith(".json") and path.startswith("docs/catalog-curation/"):
        revisions[("head", path)] = json.dumps(_valid_full_report())
    repository = FakeIntentRepository([path], revisions)

    snapshot = build_intent_snapshot(repository, "base", "head")

    assert snapshot.changed_paths == frozenset({path})


def test_unexpected_path_diagnostic_escapes_control_characters() -> None:
    path = "tests/test_catalog_bad\ninjected.py"
    repository = FakeIntentRepository([path], {})

    with pytest.raises(IntentValidationError) as exc:
        build_intent_snapshot(repository, "base", "head")

    assert repr(path) in str(exc.value)
    assert "\n" not in str(exc.value)


def test_unsafe_metadata_diagnostic_escapes_control_characters() -> None:
    path = "tests/test_catalog_bad\x1binjected.py"
    entry = IntentDiffEntry(
        path=path,
        old_mode="120000",
        new_mode="120000",
        old_oid="a" * 40,
        new_oid="b" * 40,
        status="M",
    )
    repository = FakeIntentRepository([path], {}, entries=[entry])

    with pytest.raises(IntentValidationError) as exc:
        build_intent_snapshot(repository, "base", "head")

    assert repr(path) in str(exc.value)
    assert "\x1b" not in str(exc.value)


def test_changed_path_drift_diagnostic_escapes_control_characters() -> None:
    unsafe_path = "tests/test_catalog_bad\ninjected.py"
    after = _snapshot(changed_paths=frozenset({"app/data/catalog.json", unsafe_path}))

    with pytest.raises(IntentDriftError) as exc:
        compare_intent(_snapshot(), after)

    assert repr(unsafe_path) in str(exc.value)
    assert "\n" not in str(exc.value)
