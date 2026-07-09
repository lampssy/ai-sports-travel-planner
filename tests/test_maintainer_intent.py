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
    compare_review_scope,
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
    diff_entries: tuple[IntentDiffEntry, ...] | None = None,
    catalog_targets: frozenset[str] = frozenset({"ski_area:alpha"}),
    report_targets: frozenset[str] = frozenset({"ski_area:alpha"}),
) -> IntentSnapshot:
    return IntentSnapshot(
        changed_paths=changed_paths,
        diff_entries=diff_entries
        if diff_entries is not None
        else (
            IntentDiffEntry(
                path="app/data/catalog.json",
                old_mode="100644",
                new_mode="100644",
                old_oid="a" * 40,
                new_oid="b" * 40,
                status="M",
            ),
        ),
        catalog_targets=catalog_targets,
        report_targets=report_targets,
    )


def test_intent_allows_arbitrary_backlog_prose_without_reading_it() -> None:
    path = "docs/product-backlog.md"
    repository = FakeIntentRepository(
        [path],
        {
            ("base", path): "## repeated\n## repeated\n`not:parsed`\n",
            ("head", path): "free-form prose without required sections\n",
        },
    )

    snapshot = build_intent_snapshot(repository, "base", "head")

    assert snapshot.changed_paths == frozenset({path})
    assert snapshot.diff_entries == repository.diff_entries("base", "head")
    assert snapshot.catalog_targets == frozenset()
    assert snapshot.report_targets == frozenset()
    assert repository.show_calls == []


@pytest.mark.parametrize(
    ("path", "old_mode", "new_mode", "status", "message"),
    [
        ("tests/test_catalog_alpha.py", "100644", "100644", "M", "unexpected"),
        ("app/data/catalog.json", "120000", "120000", "M", "unsafe diff"),
        ("app/data/catalog.json", "160000", "160000", "M", "unsafe diff"),
        ("app/data/catalog.json", "100644", "100755", "M", "unsafe diff"),
    ],
)
def test_intent_rejects_executable_paths_or_unsafe_modes(
    path: str,
    old_mode: str,
    new_mode: str,
    status: str,
    message: str,
) -> None:
    entry = IntentDiffEntry(
        path=path,
        old_mode=old_mode,
        new_mode=new_mode,
        old_oid="a" * 40,
        new_oid="b" * 40,
        status=status,
    )
    repository = FakeIntentRepository([path], {}, entries=[entry])

    with pytest.raises(IntentValidationError, match=message):
        build_intent_snapshot(repository, "base", "head")


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        (
            "changed_paths",
            frozenset({"docs/product-backlog.md"}),
            "changed path scope",
        ),
        (
            "diff_entries",
            (
                IntentDiffEntry(
                    path="app/data/catalog.json",
                    old_mode="100644",
                    new_mode="100644",
                    old_oid="c" * 40,
                    new_oid="d" * 40,
                    status="M",
                ),
            ),
            "file mode or change kind",
        ),
        (
            "catalog_targets",
            frozenset({"ski_area:beta"}),
            "catalog target scope",
        ),
        (
            "report_targets",
            frozenset({"ski_area:beta"}),
            "curation report target scope",
        ),
    ],
)
def test_compare_intent_rejects_each_drift_dimension(
    field: str,
    replacement: object,
    message: str,
) -> None:
    before = _snapshot()
    after = before.model_copy(update={field: replacement})

    with pytest.raises(IntentDriftError, match=message):
        compare_intent(before, after)


def test_compare_intent_accepts_exact_equality() -> None:
    snapshot = _snapshot()

    compare_intent(snapshot, snapshot)


def test_compare_review_scope_accepts_content_changes() -> None:
    before = _snapshot()
    changed_entries = tuple(
        entry.model_copy(update={"new_oid": "c" * 40}) for entry in before.diff_entries
    )
    after = before.model_copy(update={"diff_entries": changed_entries})

    compare_review_scope(before, after)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        (
            "changed_paths",
            frozenset({"docs/product-backlog.md"}),
            "changed path scope",
        ),
        (
            "diff_entries",
            (
                IntentDiffEntry(
                    path="app/data/catalog.json",
                    old_mode="100644",
                    new_mode="100755",
                    old_oid="a" * 40,
                    new_oid="b" * 40,
                    status="M",
                ),
            ),
            "file mode or change kind",
        ),
        (
            "catalog_targets",
            frozenset({"ski_area:beta"}),
            "catalog target scope",
        ),
    ],
)
def test_compare_review_scope_rejects_scope_drift(
    field: str,
    replacement: object,
    message: str,
) -> None:
    before = _snapshot()
    after = before.model_copy(update={field: replacement})

    with pytest.raises(IntentDriftError, match=message):
        compare_review_scope(before, after)


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
