import json
import re
import subprocess
import sys
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any, get_args
from urllib.parse import urlsplit

import pytest
from pydantic import ValidationError

from app.domain import catalog_trust as catalog_trust_module
from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_trust import (
    FIELD_GROUPS,
    CatalogEntityType,
    CatalogTrustManifest,
    EntityTrustEntry,
    Status,
)
from tests.test_catalog_models import (
    add_terrain_domain,
    example_rental,
    minimal_catalog_payload,
)

EXPECTED_FIELD_GROUPS = {
    "ski_regions": ("identity", "membership_context"),
    "stay_destinations": (
        "identity_location",
        "coordinates",
        "price_level",
    ),
    "stay_bases": (
        "identity_ownership",
        "coordinates",
        "elevation",
        "lodging_price_quality",
        "base_type",
        "base_character",
        "local_apres",
    ),
    "ski_areas": (
        "identity_coordinates",
        "elevation_season",
        "terrain_metrics",
        "skill_fit",
        "snowmaking",
        "glacier_terrain",
        "snow_park",
        "night_skiing",
        "marked_freeride_routes",
        "ski_day_apres",
        "official_documents",
    ),
    "ski_area_access": ("relationship", "access_mode_distance"),
    "terrain_domains": (
        "membership_connectivity",
        "aggregate_terrain",
        "season",
        "official_documents",
    ),
    "lift_pass_products": (
        "identity_scope_availability",
        "coverage",
        "prices",
        "pass_accessible_terrain",
    ),
    "rental_display_facts": (
        "identity_ownership",
        "price_quality_access",
    ),
}
EXPECTED_ENTITY_TYPES = tuple(EXPECTED_FIELD_GROUPS)
EXPECTED_STATUSES = (
    "verified",
    "verified_with_adjustment",
    "estimated",
    "needs_source",
)
REPO_ROOT = Path(__file__).parents[1]
CATALOG_PATH = REPO_ROOT / "app" / "data" / "catalog.json"
TRUST_MANIFEST_PATH = REPO_ROOT / "app" / "data" / "resort_trust_manifest.json"
CATALOG_COLLECTION_BY_ENTITY_TYPE = {
    "ski_regions": "ski_regions",
    "stay_destinations": "stay_destinations",
    "stay_bases": "stay_bases",
    "ski_areas": "ski_areas",
    "ski_area_access": "ski_area_access",
    "terrain_domains": "terrain_domains",
    "lift_pass_products": "lift_pass_products",
    "rental_display_facts": "rental_display_facts",
}


def _load_canonical_pair() -> tuple[CatalogSnapshot, CatalogTrustManifest]:
    catalog = CatalogSnapshot.model_validate_json(
        CATALOG_PATH.read_text(encoding="utf-8")
    )
    manifest = CatalogTrustManifest.model_validate_json(
        TRUST_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    return catalog, manifest


def _run_catalog_cli(
    catalog_path: Path,
    trust_manifest_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "app.data.validate_catalog",
        "--catalog-path",
        str(catalog_path),
    ]
    if trust_manifest_path is not None:
        command.extend(["--trust-manifest-path", str(trust_manifest_path)])
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _minimal_snapshot(*, with_rental: bool = False) -> CatalogSnapshot:
    payload = minimal_catalog_payload()
    if with_rental:
        payload["rental_display_facts"].append(example_rental())
    return CatalogSnapshot.model_validate(payload)


def _complete_snapshot() -> CatalogSnapshot:
    payload = minimal_catalog_payload()
    add_terrain_domain(payload)
    payload["rental_display_facts"].append(example_rental())
    return CatalogSnapshot.model_validate(payload)


def _entry_payload(display_name: str, groups: tuple[str, ...]) -> dict[str, Any]:
    return {
        "display_name": display_name,
        "field_statuses": {group: "estimated" for group in groups},
        "field_source_refs": {group: [] for group in groups},
        "notes": [],
    }


def _manifest_payload(
    *,
    with_rental: bool = False,
    with_terrain_domain: bool = False,
) -> dict[str, Any]:
    entities: dict[str, dict[str, dict[str, Any]]] = {
        entity_type: {} for entity_type in EXPECTED_ENTITY_TYPES
    }
    names = {
        "ski_regions": ("example", "Example Valley"),
        "stay_destinations": ("example", "Example"),
        "stay_bases": ("example-village", "Example Village"),
        "ski_areas": ("example-area", "Example Area"),
        "ski_area_access": (
            "example-village--example-area",
            "Example Village -> Example Area",
        ),
        "lift_pass_products": ("example-local-pass", "Example Local Pass"),
    }
    if with_terrain_domain:
        names.update(
            {
                "ski_areas": ("other-area", "Other Area"),
                "ski_area_access": (
                    "example-village--other-area",
                    "Example Village -> Other Area",
                ),
                "terrain_domains": ("example-domain", "Example Domain"),
            }
        )
    for entity_type, (entity_id, display_name) in names.items():
        entities[entity_type][entity_id] = _entry_payload(
            display_name, EXPECTED_FIELD_GROUPS[entity_type]
        )
    if with_terrain_domain:
        entities["ski_areas"]["example-area"] = _entry_payload(
            "Example Area", EXPECTED_FIELD_GROUPS["ski_areas"]
        )
        entities["ski_area_access"]["example-village--example-area"] = _entry_payload(
            "Example Village -> Example Area",
            EXPECTED_FIELD_GROUPS["ski_area_access"],
        )
    if with_rental:
        entities["rental_display_facts"]["example-rental"] = _entry_payload(
            "Example Rental", EXPECTED_FIELD_GROUPS["rental_display_facts"]
        )
    for access_entry in entities["ski_area_access"].values():
        access_entry["field_source_refs"]["relationship"] = [
            "https://www.openstreetmap.org/way/1"
        ]

    return {
        "version": "2",
        "catalog_schema_version": 2,
        "status_values": list(EXPECTED_STATUSES),
        "field_groups": {
            entity_type: list(groups)
            for entity_type, groups in EXPECTED_FIELD_GROUPS.items()
        },
        "entities": entities,
    }


def _validated_manifest(*, with_rental: bool = False) -> CatalogTrustManifest:
    return CatalogTrustManifest.model_validate(
        _manifest_payload(with_rental=with_rental)
    )


def test_contract_declares_exact_entity_types_statuses_and_field_groups() -> None:
    assert get_args(CatalogEntityType) == EXPECTED_ENTITY_TYPES
    assert get_args(Status) == EXPECTED_STATUSES
    assert dict(FIELD_GROUPS) == EXPECTED_FIELD_GROUPS

    with pytest.raises(TypeError):
        FIELD_GROUPS["ski_regions"] = ("other",)  # type: ignore[index]


def test_entity_descriptors_exactly_cover_catalog_namespaces() -> None:
    descriptor_types = tuple(
        descriptor.entity_type
        for descriptor in catalog_trust_module._ENTITY_DESCRIPTORS
    )

    assert descriptor_types == EXPECTED_ENTITY_TYPES


@pytest.mark.parametrize("field_name", ["field_groups", "entities"])
@pytest.mark.parametrize("change", ["missing", "unknown"])
def test_manifest_requires_exact_namespaces(field_name: str, change: str) -> None:
    payload = _manifest_payload()
    if change == "missing":
        del payload[field_name]["rental_display_facts"]
    else:
        payload[field_name]["unknown_entities"] = {}

    with pytest.raises(
        ValidationError,
        match=rf"{field_name}.*exactly all catalog entity namespaces.*{change}",
    ):
        CatalogTrustManifest.model_validate(payload)


@pytest.mark.parametrize("field_name", ["field_groups", "entities"])
def test_manifest_rejects_non_string_namespace_keys_deterministically(
    field_name: str,
) -> None:
    payload = _manifest_payload()
    payload[field_name][1] = {}

    with pytest.raises(ValidationError) as error:
        CatalogTrustManifest.model_validate(payload)

    assert error.value.errors()[0]["loc"] == (field_name,)
    assert f"{field_name} namespace keys must be strings; got: int" in str(error.value)


def test_valid_minimal_manifest_matches_catalog_snapshot() -> None:
    snapshot = _minimal_snapshot()
    manifest = _validated_manifest()

    manifest.validate_against_catalog(snapshot)

    assert manifest.version == "2"
    assert manifest.catalog_schema_version == snapshot.schema_version
    assert manifest.entities["terrain_domains"] == {}
    assert manifest.entities["rental_display_facts"] == {}


def test_complete_manifest_matches_catalog_with_all_entity_types() -> None:
    snapshot = _complete_snapshot()
    manifest = CatalogTrustManifest.model_validate(
        _manifest_payload(with_rental=True, with_terrain_domain=True)
    )

    manifest.validate_against_catalog(snapshot)

    assert snapshot.terrain_domains
    assert all(manifest.entities[entity_type] for entity_type in EXPECTED_ENTITY_TYPES)


def test_access_sources_may_be_partitioned_across_trust_groups() -> None:
    snapshot = _minimal_snapshot()
    access = snapshot.ski_area_access[0]
    relationship_url = access.source_urls[0]
    mode_url = "https://www.openstreetmap.org/node/2"
    snapshot = snapshot.model_copy(
        update={
            "ski_area_access": (
                access.model_copy(update={"source_urls": (relationship_url, mode_url)}),
            )
        }
    )
    payload = _manifest_payload()
    entry = payload["entities"]["ski_area_access"][access.ski_area_access_id]
    entry["field_source_refs"]["relationship"] = [relationship_url]
    entry["field_source_refs"]["access_mode_distance"] = [mode_url]

    CatalogTrustManifest.model_validate(payload).validate_against_catalog(snapshot)


def test_access_source_may_be_shared_by_multiple_trust_groups() -> None:
    snapshot = _minimal_snapshot()
    access = snapshot.ski_area_access[0]
    payload = _manifest_payload()
    entry = payload["entities"]["ski_area_access"][access.ski_area_access_id]
    entry["field_source_refs"]["access_mode_distance"] = list(access.source_urls)

    CatalogTrustManifest.model_validate(payload).validate_against_catalog(snapshot)


def test_access_source_rollup_rejects_catalog_url_without_group_owner() -> None:
    snapshot = _minimal_snapshot()
    access = snapshot.ski_area_access[0]
    payload = _manifest_payload()
    payload["entities"]["ski_area_access"][access.ski_area_access_id][
        "field_source_refs"
    ]["relationship"] = []

    with pytest.raises(
        ValueError,
        match="catalog sources without field-group ownership",
    ):
        CatalogTrustManifest.model_validate(payload).validate_against_catalog(snapshot)


def test_access_source_rollup_rejects_group_url_missing_from_catalog() -> None:
    snapshot = _minimal_snapshot()
    access = snapshot.ski_area_access[0]
    payload = _manifest_payload()
    payload["entities"]["ski_area_access"][access.ski_area_access_id][
        "field_source_refs"
    ]["access_mode_distance"] = ["https://www.openstreetmap.org/node/2"]

    with pytest.raises(
        ValueError,
        match="field-group sources absent from catalog source_urls",
    ):
        CatalogTrustManifest.model_validate(payload).validate_against_catalog(snapshot)


@pytest.mark.parametrize(
    ("change", "entity_id", "message"),
    [
        ("missing", "example-area", "missing trust entry"),
        ("unknown", "unknown-area", "unknown trust entry"),
    ],
)
def test_catalog_validation_rejects_missing_or_unknown_entity(
    change: str, entity_id: str, message: str
) -> None:
    payload = _manifest_payload()
    if change == "missing":
        del payload["entities"]["ski_areas"][entity_id]
    else:
        payload["entities"]["ski_areas"][entity_id] = _entry_payload(
            "Unknown Area", EXPECTED_FIELD_GROUPS["ski_areas"]
        )

    manifest = CatalogTrustManifest.model_validate(payload)

    with pytest.raises(
        ValueError,
        match=rf"ski_areas/{re.escape(entity_id)}.*{message}",
    ):
        manifest.validate_against_catalog(_minimal_snapshot())


@pytest.mark.parametrize(
    ("change", "error_label"),
    [("missing", "missing"), ("extra", "unknown")],
)
def test_catalog_validation_rejects_missing_or_extra_entry_group(
    change: str,
    error_label: str,
) -> None:
    payload = _manifest_payload()
    statuses = payload["entities"]["ski_areas"]["example-area"]["field_statuses"]
    if change == "missing":
        group = "skill_fit"
        del statuses[group]
    else:
        group = "snow_quality"
        statuses[group] = "estimated"

    with pytest.raises(
        ValidationError,
        match=rf"ski_areas field_statuses.*{error_label}: {group}",
    ):
        CatalogTrustManifest.model_validate(payload)


@pytest.mark.parametrize(
    ("change", "error_label"),
    [("missing", "missing"), ("extra", "unknown")],
)
def test_manifest_rejects_missing_or_extra_field_source_group(
    change: str,
    error_label: str,
) -> None:
    payload = _manifest_payload()
    source_refs = payload["entities"]["ski_areas"]["example-area"]["field_source_refs"]
    if change == "missing":
        group = "skill_fit"
        del source_refs[group]
    else:
        group = "snow_quality"
        source_refs[group] = []

    with pytest.raises(
        ValidationError,
        match=rf"ski_areas field_source_refs.*{error_label}: {group}",
    ):
        CatalogTrustManifest.model_validate(payload)


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_manifest_rejects_field_groups_that_differ_from_contract(change: str) -> None:
    payload = _manifest_payload()
    groups = payload["field_groups"]["ski_areas"]
    if change == "missing":
        groups.remove("skill_fit")
    else:
        groups.append("snow_quality")

    with pytest.raises(
        ValidationError,
        match=r"field_groups.*ski_areas.*must equal FIELD_GROUPS",
    ):
        CatalogTrustManifest.model_validate(payload)


@pytest.mark.parametrize(
    "status_values",
    [
        [*EXPECTED_STATUSES, "verified"],
        list(EXPECTED_STATUSES[:-1]),
        [*EXPECTED_STATUSES[:-1], "invalid"],
    ],
    ids=["duplicate", "missing", "invalid"],
)
def test_manifest_rejects_invalid_or_duplicate_status_values(
    status_values: list[str],
) -> None:
    payload = _manifest_payload()
    payload["status_values"] = status_values

    with pytest.raises(ValidationError, match="status_values"):
        CatalogTrustManifest.model_validate(payload)


@pytest.mark.parametrize("status", ["verified", "verified_with_adjustment"])
def test_catalog_validation_requires_source_for_verified_group(status: str) -> None:
    payload = _manifest_payload()
    entry = payload["entities"]["ski_areas"]["example-area"]
    entry["field_statuses"]["terrain_metrics"] = status
    entry["field_source_refs"]["identity_coordinates"] = [
        "https://www.example.com/identity"
    ]
    manifest = CatalogTrustManifest.model_validate(payload)

    with pytest.raises(
        ValueError,
        match=(
            r"ski_areas/example-area/terrain_metrics.*"
            r"requires at least one source ref"
        ),
    ):
        manifest.validate_against_catalog(_minimal_snapshot())


@pytest.mark.parametrize(
    "source_ref",
    [
        "app/data/catalog.json",
        "https://localhost/catalog",
        "https://www.google.com/search?q=example+area",
        "https://www.google.co.uk/search?q=example+area",
        "https://www.ecosia.org/search?q=example+area",
        "https://www.startpage.com/sp/search?query=example+area",
        "https://www.qwant.com/?q=example+area",
        "https://lite.duckduckgo.com/lite/?q=example+area",
        "https://html.duckduckgo.com/html/?q=example+area",
        "https://www.bing.com/images/search?q=example+area",
        "https://www.bing.com/videos/search?q=example+area",
        "https://search.brave.com/images?q=example+area",
        "https://search.yahoo.com/search/images?p=example+area",
        "https://search.brave.com/news?q=example+area",
        "https://www.ecosia.org/videos?q=example+area",
        "https://www.baidu.com/search/index?word=example+area",
        "https://yandex.com/search/?text=example+area",
        "https://yandex.com/images/search?text=example+area",
        "https://www.ecosia.org/images?q=example+area",
        "not a URL",
    ],
    ids=[
        "internal-path",
        "localhost",
        "google-search",
        "google-country-search",
        "ecosia-search",
        "startpage-search",
        "qwant-search",
        "duckduckgo-lite",
        "duckduckgo-html",
        "bing-images",
        "bing-videos",
        "brave-images",
        "yahoo-images",
        "brave-news",
        "ecosia-videos",
        "baidu-images",
        "yandex-search",
        "yandex-images",
        "ecosia-images",
        "invalid-url",
    ],
)
def test_manifest_rejects_non_direct_source_refs(source_ref: str) -> None:
    payload = _manifest_payload()
    payload["entities"]["ski_areas"]["example-area"]["field_source_refs"][
        "terrain_metrics"
    ] = [source_ref]

    with pytest.raises(ValidationError) as error:
        CatalogTrustManifest.model_validate(payload)

    assert error.value.errors()[0]["loc"] == (
        "entities",
        "ski_areas",
        "example-area",
        "field_source_refs",
    )
    assert "direct external HTTP(S) URL" in str(error.value)


@pytest.mark.parametrize(
    "invalid_source_ref",
    [
        "https://localhost/catalog",
        "https://lite.duckduckgo.com/lite/?q=example+area",
    ],
    ids=["invalid-direct-url", "search-result-url"],
)
def test_source_ref_errors_include_original_input_index(
    invalid_source_ref: str,
) -> None:
    payload = _manifest_payload()
    payload["entities"]["ski_areas"]["example-area"]["field_source_refs"][
        "terrain_metrics"
    ] = ["https://www.example.com/valid", invalid_source_ref]

    with pytest.raises(
        ValidationError,
        match=r"field_source_refs\.terrain_metrics\[1\]",
    ):
        CatalogTrustManifest.model_validate(payload)


@pytest.mark.parametrize(
    "source_ref",
    [
        "https://www.google.co.uk/maps/place/Example",
        "https://www.ecosia.org/about",
        "https://duckduckgo.com/about",
        "https://www.bing.com/maps",
        "https://search.brave.com/help",
        "https://yandex.com/maps",
        "https://www.example.com/search?q=example+area",
    ],
    ids=[
        "google-direct-page",
        "ecosia-direct-page",
        "duckduckgo-direct-page",
        "bing-direct-page",
        "brave-direct-page",
        "yandex-direct-page",
        "unrelated-search-path",
    ],
)
def test_manifest_accepts_ordinary_direct_pages(source_ref: str) -> None:
    entry = EntityTrustEntry.model_validate(
        {
            "display_name": "Example Area",
            "field_statuses": {"terrain_metrics": "verified"},
            "field_source_refs": {"terrain_metrics": [source_ref]},
        }
    )

    assert entry.field_source_refs["terrain_metrics"] == (source_ref,)


def test_entry_normalizes_display_name_and_direct_source_refs() -> None:
    entry = EntityTrustEntry.model_validate(
        {
            "display_name": "  Example Area  ",
            "field_statuses": {"terrain_metrics": "verified"},
            "field_source_refs": {
                "terrain_metrics": ["  https://www.example.com/area  "]
            },
            "notes": ["Reviewed"],
        }
    )

    assert entry.display_name == "Example Area"
    assert entry.field_source_refs["terrain_metrics"] == (
        "https://www.example.com/area",
    )
    assert entry.notes == ("Reviewed",)


@pytest.mark.parametrize(
    ("entity_type", "entity_id", "display_name"),
    [
        ("ski_regions", "example", "Wrong Valley"),
        ("stay_destinations", "example", "Wrong Destination"),
        ("stay_bases", "example-village", "Wrong Village"),
        ("ski_areas", "example-area", "Wrong Area"),
        (
            "ski_area_access",
            "example-village--example-area",
            "Example Area -> Example Village",
        ),
        ("terrain_domains", "example-domain", "Wrong Domain"),
        ("lift_pass_products", "example-local-pass", "Wrong Pass"),
        ("rental_display_facts", "example-rental", "Example Village Rental"),
    ],
)
def test_catalog_validation_rejects_display_name_mismatch(
    entity_type: str, entity_id: str, display_name: str
) -> None:
    payload = _manifest_payload(with_rental=True, with_terrain_domain=True)
    payload["entities"][entity_type][entity_id]["display_name"] = display_name
    manifest = CatalogTrustManifest.model_validate(payload)

    with pytest.raises(
        ValueError,
        match=rf"{entity_type}/{re.escape(entity_id)}.*display_name.*does not match",
    ):
        manifest.validate_against_catalog(_complete_snapshot())


@pytest.mark.parametrize("target", ["entry", "manifest"])
def test_models_reject_unknown_fields(target: str) -> None:
    payload = _manifest_payload()
    if target == "entry":
        payload["entities"]["ski_areas"]["example-area"]["confidence"] = 1
    else:
        payload["generated_at"] = "2026-07-01"

    with pytest.raises(ValidationError, match="extra_forbidden"):
        CatalogTrustManifest.model_validate(payload)


def test_models_copy_inputs_and_expose_immutable_mappings_and_tuples() -> None:
    payload = _manifest_payload()
    manifest = CatalogTrustManifest.model_validate(payload)
    entry = manifest.entities["ski_areas"]["example-area"]

    payload["field_groups"]["ski_areas"].append("mutated")
    payload["entities"]["ski_areas"]["example-area"]["field_statuses"]["mutated"] = (
        "estimated"
    )
    payload["entities"]["ski_areas"]["example-area"]["field_source_refs"][
        "terrain_metrics"
    ].append("https://www.example.com/mutated")
    payload["entities"]["ski_areas"]["example-area"]["notes"].append("mutated")
    payload["entities"]["ski_areas"]["other-area"] = deepcopy(
        payload["entities"]["ski_areas"]["example-area"]
    )

    assert manifest.field_groups["ski_areas"] == EXPECTED_FIELD_GROUPS["ski_areas"]
    assert "mutated" not in entry.field_statuses
    assert entry.field_source_refs["terrain_metrics"] == ()
    assert entry.notes == ()
    assert "other-area" not in manifest.entities["ski_areas"]
    assert isinstance(entry.field_source_refs, Mapping)
    assert isinstance(entry.field_source_refs["terrain_metrics"], tuple)
    assert isinstance(entry.notes, tuple)

    with pytest.raises(TypeError):
        manifest.entities["ski_areas"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        manifest.entities["ski_areas"]["other-area"] = entry  # type: ignore[index]
    with pytest.raises(TypeError):
        entry.field_statuses["terrain_metrics"] = "verified"  # type: ignore[index]
    with pytest.raises(TypeError):
        entry.field_source_refs["terrain_metrics"] = ()  # type: ignore[index]


def test_deepcopy_and_deep_model_copy_preserve_safe_immutable_models() -> None:
    manifest = _validated_manifest()

    for copied in (manifest.model_copy(deep=True), deepcopy(manifest)):
        assert copied == manifest
        assert copied is not manifest
        assert copied.entities is not manifest.entities
        with pytest.raises(TypeError):
            copied.entities["ski_areas"]["other-area"] = copied.entities["ski_areas"][
                "example-area"
            ]  # type: ignore[index]


def test_model_copy_update_revalidates_frozen_models() -> None:
    manifest = _validated_manifest()
    entry = manifest.entities["ski_areas"]["example-area"]

    with pytest.raises(ValidationError, match="display_name"):
        entry.model_copy(update={"display_name": " "})
    with pytest.raises(ValidationError, match="entities"):
        manifest.model_copy(update={"entities": {}})


@pytest.mark.parametrize(
    ("entity_type", "entity_id"),
    [
        ("stay_destinations", "example"),
        ("stay_bases", "example-village"),
        ("rental_display_facts", "example-rental"),
    ],
)
def test_shared_field_groups_follow_their_namespace_order(
    entity_type: str,
    entity_id: str,
) -> None:
    payload = _manifest_payload(with_rental=True)
    entry_payload = payload["entities"][entity_type][entity_id]
    entry_payload["field_statuses"] = dict(
        reversed(list(entry_payload["field_statuses"].items()))
    )
    entry_payload["field_source_refs"] = dict(
        reversed(list(entry_payload["field_source_refs"].items()))
    )

    manifest = CatalogTrustManifest.model_validate(payload)
    entry = manifest.entities[entity_type][entity_id]
    dumped = json.loads(manifest.model_dump_json())

    assert tuple(entry.field_statuses) == EXPECTED_FIELD_GROUPS[entity_type]
    assert tuple(entry.field_source_refs) == EXPECTED_FIELD_GROUPS[entity_type]
    assert (
        tuple(dumped["entities"][entity_type][entity_id]["field_statuses"])
        == EXPECTED_FIELD_GROUPS[entity_type]
    )
    assert (
        tuple(dumped["entities"][entity_type][entity_id]["field_source_refs"])
        == EXPECTED_FIELD_GROUPS[entity_type]
    )


def test_semantically_equivalent_manifests_have_canonical_models_and_json() -> None:
    canonical_payload = _manifest_payload()
    area_entries = canonical_payload["entities"]["ski_areas"]
    area_entries["z-area"] = _entry_payload(
        "Z Area", EXPECTED_FIELD_GROUPS["ski_areas"]
    )
    area_entries["a-area"] = _entry_payload(
        "A Area", EXPECTED_FIELD_GROUPS["ski_areas"]
    )
    canonical_refs = [
        "https://www.example.com/a",
        "https://www.example.com/z",
    ]
    area_entries["example-area"]["field_source_refs"]["terrain_metrics"] = (
        canonical_refs
    )

    permuted_payload = deepcopy(canonical_payload)
    permuted_payload["status_values"] = list(reversed(EXPECTED_STATUSES))
    permuted_payload["field_groups"] = dict(
        reversed(list(permuted_payload["field_groups"].items()))
    )
    permuted_payload["entities"] = dict(
        reversed(list(permuted_payload["entities"].items()))
    )
    for entries in permuted_payload["entities"].values():
        for entry in entries.values():
            entry["field_statuses"] = dict(
                reversed(list(entry["field_statuses"].items()))
            )
            entry["field_source_refs"] = dict(
                reversed(list(entry["field_source_refs"].items()))
            )
        reversed_entries = dict(reversed(list(entries.items())))
        entries.clear()
        entries.update(reversed_entries)
    permuted_payload["entities"]["ski_areas"]["example-area"]["field_source_refs"][
        "terrain_metrics"
    ] = [
        "https://www.example.com/z",
        "  https://www.example.com/a  ",
        "https://www.example.com/z",
    ]

    canonical = CatalogTrustManifest.model_validate(canonical_payload)
    permuted = CatalogTrustManifest.model_validate(permuted_payload)

    assert canonical == permuted
    assert canonical.model_dump_json() == permuted.model_dump_json()
    assert canonical.status_values == EXPECTED_STATUSES
    assert tuple(canonical.field_groups) == EXPECTED_ENTITY_TYPES
    assert tuple(canonical.entities) == EXPECTED_ENTITY_TYPES
    assert tuple(canonical.entities["ski_areas"]) == (
        "a-area",
        "example-area",
        "z-area",
    )
    assert (
        tuple(canonical.entities["ski_areas"]["example-area"].field_statuses)
        == EXPECTED_FIELD_GROUPS["ski_areas"]
    )
    assert canonical.entities["ski_areas"]["example-area"].field_source_refs[
        "terrain_metrics"
    ] == tuple(canonical_refs)


def test_manifest_json_round_trip_uses_objects_and_arrays() -> None:
    payload = _manifest_payload()
    payload["entities"]["ski_areas"]["example-area"]["field_source_refs"][
        "terrain_metrics"
    ] = ["https://www.example.com/area"]
    payload["entities"]["ski_areas"]["example-area"]["notes"] = ["Reviewed"]
    manifest = CatalogTrustManifest.model_validate(payload)

    dumped = json.loads(manifest.model_dump_json())

    assert isinstance(dumped["field_groups"], dict)
    assert isinstance(dumped["field_groups"]["ski_areas"], list)
    assert isinstance(dumped["entities"], dict)
    assert isinstance(dumped["entities"]["ski_areas"], dict)
    assert isinstance(
        dumped["entities"]["ski_areas"]["example-area"]["field_source_refs"],
        dict,
    )
    assert isinstance(
        dumped["entities"]["ski_areas"]["example-area"]["field_source_refs"][
            "terrain_metrics"
        ],
        list,
    )
    assert isinstance(dumped["entities"]["ski_areas"]["example-area"]["notes"], list)

    round_tripped = CatalogTrustManifest.model_validate_json(manifest.model_dump_json())
    round_tripped.validate_against_catalog(_minimal_snapshot())
    assert round_tripped == manifest


def test_canonical_manifest_exactly_matches_catalog_graph() -> None:
    raw_manifest = json.loads(TRUST_MANIFEST_PATH.read_text(encoding="utf-8"))
    catalog, manifest = _load_canonical_pair()

    manifest.validate_against_catalog(catalog)

    assert tuple(raw_manifest) == (
        "version",
        "catalog_schema_version",
        "status_values",
        "field_groups",
        "entities",
    )
    assert manifest.catalog_schema_version == 2
    assert tuple(manifest.entities) == EXPECTED_ENTITY_TYPES
    assert {
        entity_type: len(manifest.entities[entity_type])
        for entity_type in EXPECTED_ENTITY_TYPES
    } == {
        entity_type: len(
            getattr(catalog, CATALOG_COLLECTION_BY_ENTITY_TYPE[entity_type])
        )
        for entity_type in EXPECTED_ENTITY_TYPES
    }
    for entity_type, entries in manifest.entities.items():
        for entry in entries.values():
            assert tuple(entry.field_statuses) == EXPECTED_FIELD_GROUPS[entity_type]
            assert tuple(entry.field_source_refs) == EXPECTED_FIELD_GROUPS[entity_type]


def test_canonical_manifest_has_only_direct_external_source_refs() -> None:
    _, manifest = _load_canonical_pair()

    for entity_type, entries in manifest.entities.items():
        for entity_id, entry in entries.items():
            for group, source_refs in entry.field_source_refs.items():
                for source_ref in source_refs:
                    parsed = urlsplit(source_ref)
                    assert parsed.scheme in {"http", "https"}, (
                        f"{entity_type}/{entity_id}/{group}: internal source ref "
                        f"{source_ref!r}"
                    )
                    assert not catalog_trust_module._is_web_search_result_url(
                        source_ref
                    ), (
                        f"{entity_type}/{entity_id}/{group}: search-result source "
                        f"ref {source_ref!r}"
                    )


def test_canonical_manifest_routes_special_terrain_trust_to_new_owners() -> None:
    _, manifest = _load_canonical_pair()

    chamonix_pass = manifest.entities["lift_pass_products"]["chamonix-le-pass"]
    kitzsteinhorn_domain = manifest.entities["terrain_domains"][
        "kitzsteinhorn-maiskogel"
    ]

    assert (
        chamonix_pass.field_statuses["pass_accessible_terrain"]
        == "verified_with_adjustment"
    )
    assert kitzsteinhorn_domain.field_statuses == {
        "membership_connectivity": "verified_with_adjustment",
        "aggregate_terrain": "verified_with_adjustment",
        "season": "needs_source",
        "official_documents": "needs_source",
    }


def test_canonical_manifest_keeps_access_sources_on_access_owner() -> None:
    catalog, manifest = _load_canonical_pair()
    access_entries = manifest.entities["ski_area_access"]

    for access in catalog.ski_area_access:
        entry = access_entries[access.ski_area_access_id]
        assert all(
            source_refs
            for group, source_refs in entry.field_source_refs.items()
            if entry.field_statuses[group] in {"verified", "verified_with_adjustment"}
        )
        grouped_sources = {
            source
            for source_refs in entry.field_source_refs.values()
            for source in source_refs
        }
        assert grouped_sources == set(access.source_urls)


def test_canonical_manifest_uses_domain_owned_sources() -> None:
    catalog, manifest = _load_canonical_pair()

    for domain in catalog.terrain_domains:
        entry = manifest.entities["terrain_domains"][domain.terrain_domain_id]
        for group in ("membership_connectivity", "aggregate_terrain", "season"):
            assert entry.field_source_refs[group] == tuple(sorted(domain.source_urls))
        expected_document_sources = (
            ()
            if domain.official_trail_map is None
            else (str(domain.official_trail_map.url),)
        )
        assert (
            entry.field_source_refs["official_documents"] == expected_document_sources
        )


def test_validate_catalog_cli_validates_canonical_catalog_and_manifest() -> None:
    catalog, manifest = _load_canonical_pair()
    result = _run_catalog_cli(CATALOG_PATH, TRUST_MANIFEST_PATH)

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.strip() == (
        f"[catalog-valid] schema_version={catalog.schema_version} "
        f"ski_regions={len(catalog.ski_regions)} "
        f"stay_destinations={len(catalog.stay_destinations)} "
        f"stay_bases={len(catalog.stay_bases)} "
        f"ski_areas={len(catalog.ski_areas)} "
        f"access_links={len(catalog.ski_area_access)} "
        f"terrain_domains={len(catalog.terrain_domains)} "
        f"lift_pass_products={len(catalog.lift_pass_products)} "
        f"rental_display_facts={len(catalog.rental_display_facts)} "
        f"trust_manifest_version={manifest.version} "
        f"trust_entries={sum(len(entries) for entries in manifest.entities.values())}"
    )


@pytest.mark.parametrize(
    ("contents", "expected_error"),
    [
        (b"\xff", "invalid UTF-8"),
        (b'{"version":', "invalid JSON"),
        (b"{}", "trust manifest validation failed"),
    ],
    ids=["utf8", "json", "pydantic"],
)
def test_validate_catalog_cli_rejects_invalid_trust_manifest(
    tmp_path: Path,
    contents: bytes,
    expected_error: str,
) -> None:
    manifest_path = tmp_path / "trust.json"
    manifest_path.write_bytes(contents)

    result = _run_catalog_cli(CATALOG_PATH, manifest_path)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "[catalog-invalid]" in result.stderr
    assert expected_error in result.stderr
    assert str(manifest_path) in result.stderr
    assert "Traceback" not in result.stderr


def test_validate_catalog_cli_rejects_manifest_graph_mismatch(
    tmp_path: Path,
) -> None:
    payload = json.loads(TRUST_MANIFEST_PATH.read_text(encoding="utf-8"))
    del payload["entities"]["ski_areas"]["alta-badia-ski-area"]
    manifest_path = tmp_path / "trust.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    result = _run_catalog_cli(CATALOG_PATH, manifest_path)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "[catalog-invalid]" in result.stderr
    assert "trust manifest graph validation failed" in result.stderr
    assert "ski_areas/alta-badia-ski-area: missing trust entry" in result.stderr
    assert "Traceback" not in result.stderr
