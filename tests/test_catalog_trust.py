import json
import re
from copy import deepcopy
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_trust import (
    FIELD_GROUPS,
    CatalogEntityType,
    CatalogTrustManifest,
    EntityTrustEntry,
    Status,
)
from tests.test_catalog_models import example_rental, minimal_catalog_payload

EXPECTED_FIELD_GROUPS = {
    "ski_regions": ("identity", "membership_context"),
    "stay_destinations": (
        "identity_location",
        "coordinates",
        "price_level_atmosphere",
    ),
    "stay_bases": (
        "identity_ownership",
        "coordinates",
        "lodging_price_quality",
        "atmosphere",
    ),
    "ski_areas": (
        "identity_coordinates",
        "elevation_season",
        "terrain_metrics",
        "skill_fit",
    ),
    "ski_area_access": ("relationship", "access_mode_distance"),
    "terrain_domains": (
        "membership_connectivity",
        "aggregate_terrain",
        "season",
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


def _minimal_snapshot(*, with_rental: bool = False) -> CatalogSnapshot:
    payload = minimal_catalog_payload()
    if with_rental:
        payload["rental_display_facts"].append(example_rental())
    return CatalogSnapshot.model_validate(payload)


def _entry_payload(display_name: str, groups: tuple[str, ...]) -> dict[str, Any]:
    return {
        "display_name": display_name,
        "field_statuses": {group: "estimated" for group in groups},
        "source_refs": [],
        "notes": [],
    }


def _manifest_payload(*, with_rental: bool = False) -> dict[str, Any]:
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
    for entity_type, (entity_id, display_name) in names.items():
        entities[entity_type][entity_id] = _entry_payload(
            display_name, EXPECTED_FIELD_GROUPS[entity_type]
        )
    if with_rental:
        entities["rental_display_facts"]["example-rental"] = _entry_payload(
            "Example Rental", EXPECTED_FIELD_GROUPS["rental_display_facts"]
        )

    return {
        "version": "1",
        "catalog_schema_version": 1,
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


def test_valid_minimal_manifest_matches_catalog_snapshot() -> None:
    snapshot = _minimal_snapshot()
    manifest = _validated_manifest()

    manifest.validate_against_catalog(snapshot)

    assert manifest.version == "1"
    assert manifest.catalog_schema_version == snapshot.schema_version
    assert manifest.entities["terrain_domains"] == {}
    assert manifest.entities["rental_display_facts"] == {}


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
    ("change", "group", "message"),
    [
        ("missing", "skill_fit", "missing field status"),
        ("extra", "snow_quality", "unknown field status"),
    ],
)
def test_catalog_validation_rejects_missing_or_extra_entry_group(
    change: str, group: str, message: str
) -> None:
    payload = _manifest_payload()
    statuses = payload["entities"]["ski_areas"]["example-area"]["field_statuses"]
    if change == "missing":
        del statuses[group]
    else:
        statuses[group] = "estimated"

    manifest = CatalogTrustManifest.model_validate(payload)

    with pytest.raises(
        ValueError,
        match=rf"ski_areas/example-area/{group}.*{message}",
    ):
        manifest.validate_against_catalog(_minimal_snapshot())


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
    payload["entities"]["ski_areas"]["example-area"]["field_statuses"][
        "terrain_metrics"
    ] = status
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
        "not a URL",
    ],
    ids=["internal-path", "localhost", "search-results", "invalid-url"],
)
def test_manifest_rejects_non_direct_source_refs(source_ref: str) -> None:
    payload = _manifest_payload()
    payload["entities"]["ski_areas"]["example-area"]["source_refs"] = [source_ref]

    with pytest.raises(ValidationError) as error:
        CatalogTrustManifest.model_validate(payload)

    assert error.value.errors()[0]["loc"] == (
        "entities",
        "ski_areas",
        "example-area",
        "source_refs",
    )
    assert "direct external HTTP(S) URL" in str(error.value)


def test_entry_normalizes_display_name_and_direct_source_refs() -> None:
    entry = EntityTrustEntry.model_validate(
        {
            "display_name": "  Example Area  ",
            "field_statuses": {"terrain_metrics": "verified"},
            "source_refs": ["  https://www.example.com/area  "],
            "notes": ["Reviewed"],
        }
    )

    assert entry.display_name == "Example Area"
    assert entry.source_refs == ("https://www.example.com/area",)
    assert entry.notes == ("Reviewed",)


@pytest.mark.parametrize(
    ("entity_type", "entity_id", "display_name"),
    [
        ("ski_areas", "example-area", "Wrong Area"),
        (
            "ski_area_access",
            "example-village--example-area",
            "Example Area -> Example Village",
        ),
        ("rental_display_facts", "example-rental", "Example Village Rental"),
    ],
)
def test_catalog_validation_rejects_display_name_mismatch(
    entity_type: str, entity_id: str, display_name: str
) -> None:
    with_rental = entity_type == "rental_display_facts"
    payload = _manifest_payload(with_rental=with_rental)
    payload["entities"][entity_type][entity_id]["display_name"] = display_name
    manifest = CatalogTrustManifest.model_validate(payload)

    with pytest.raises(
        ValueError,
        match=rf"{entity_type}/{re.escape(entity_id)}.*display_name.*does not match",
    ):
        manifest.validate_against_catalog(_minimal_snapshot(with_rental=with_rental))


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
    payload["entities"]["ski_areas"]["example-area"]["source_refs"].append(
        "https://www.example.com/mutated"
    )
    payload["entities"]["ski_areas"]["example-area"]["notes"].append("mutated")
    payload["entities"]["ski_areas"]["other-area"] = deepcopy(
        payload["entities"]["ski_areas"]["example-area"]
    )

    assert manifest.field_groups["ski_areas"] == EXPECTED_FIELD_GROUPS["ski_areas"]
    assert "mutated" not in entry.field_statuses
    assert entry.source_refs == ()
    assert entry.notes == ()
    assert "other-area" not in manifest.entities["ski_areas"]
    assert isinstance(entry.source_refs, tuple)
    assert isinstance(entry.notes, tuple)

    with pytest.raises(TypeError):
        manifest.entities["ski_areas"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        manifest.entities["ski_areas"]["other-area"] = entry  # type: ignore[index]
    with pytest.raises(TypeError):
        entry.field_statuses["terrain_metrics"] = "verified"  # type: ignore[index]


def test_manifest_json_round_trip_uses_objects_and_arrays() -> None:
    payload = _manifest_payload()
    payload["entities"]["ski_areas"]["example-area"]["source_refs"] = [
        "https://www.example.com/area"
    ]
    payload["entities"]["ski_areas"]["example-area"]["notes"] = ["Reviewed"]
    manifest = CatalogTrustManifest.model_validate(payload)

    dumped = json.loads(manifest.model_dump_json())

    assert isinstance(dumped["field_groups"], dict)
    assert isinstance(dumped["field_groups"]["ski_areas"], list)
    assert isinstance(dumped["entities"], dict)
    assert isinstance(dumped["entities"]["ski_areas"], dict)
    assert isinstance(
        dumped["entities"]["ski_areas"]["example-area"]["source_refs"], list
    )
    assert isinstance(dumped["entities"]["ski_areas"]["example-area"]["notes"], list)

    round_tripped = CatalogTrustManifest.model_validate_json(manifest.model_dump_json())
    round_tripped.validate_against_catalog(_minimal_snapshot())
    assert round_tripped == manifest
