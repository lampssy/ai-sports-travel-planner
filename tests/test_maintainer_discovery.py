from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from ops.maintainer.discovery import (
    DISCOVERY_SUBREGIONS,
    CoverageCandidate,
    CoverageRegistry,
    DiscoveryCandidate,
    ProposalRecord,
    catalog_entity_keys,
    discovery_subregion,
    parse_catalog_backlog,
    proposal_record_from_comment,
    require_publication_ready,
    select_discovery_candidate,
    verify_origin_cleanup,
    with_official_urls,
)
from ops.maintainer.models import MachineState, MaintainerState
from ops.maintainer.publication import MaintainerSummary, render_summary

pytestmark = pytest.mark.db_free

CATALOG_PATH = Path("app/data/catalog.json")
REGISTRY_PATH = Path("docs/catalog-discovery/alpine-coverage-registry.json")
TRUST_PATH = Path("app/data/resort_trust_manifest.json")
BACKLOG_REF = "docs/product-backlog.md#regional-extension"


def _coverage_payload(
    key: str = "ski_area:horn",
    *,
    kind: str = "ski_area",
    urls: list[str] | None = None,
) -> dict[str, object]:
    return {
        "candidate_key": key,
        "display_name": "Horn",
        "country": "Austria",
        "alpine_subregion": "Austrian Alps",
        "regional_graph_key": "regional-extension",
        "candidate_kind": kind,
        "official_urls": urls or ["https://operator.example.org/horn"],
    }


def _registry(*entries: dict[str, object]) -> CoverageRegistry:
    return CoverageRegistry.model_validate(
        {"schema_version": 1, "entries": list(entries)}, strict=True
    )


def _backlog(markers: tuple[str, ...] = ("stay_destination:leogang",)) -> str:
    rendered = "\n".join(f"- `{marker}` — candidate" for marker in markers)
    return f"""# Backlog

## Catalog Curation Refinements

The examples `ski_area:example-only` and `stay_destination:also-example`
document the marker syntax and are not active candidates.

### Regional Extension

Candidate inventory:

{rendered}

Why deferred: graph migration.

## Current Backlog

### Unrelated

- `ski_area:not-in-curation-section`
"""


def _backlog_candidate(key: str = "stay_destination:leogang") -> DiscoveryCandidate:
    return next(
        item for item in parse_catalog_backlog(_backlog((key,))) if item.key == key
    )


def _proposal(
    *,
    candidate_key: str = "ski_area:open-area",
    graph: str = "open-region",
    lifecycle_state: str = "OPEN",
    is_proposal: bool = True,
) -> ProposalRecord:
    return ProposalRecord(
        lifecycle_state=lifecycle_state,
        is_proposal=is_proposal,
        candidate_key=candidate_key,
        origin_fingerprint="a" * 64,
        fingerprint="b" * 64,
        regional_graph_key=graph,
    )


def _render_candidate_summary(
    *, state: MaintainerState = MaintainerState.PROPOSAL
) -> str:
    machine_state = MachineState(
        head_sha="a" * 40,
        lineage_id="discovery-horn",
        candidate_key="ski_area:horn",
        candidate_origin_fingerprint="b" * 64,
        candidate_fingerprint="c" * 64,
        regional_graph_key="regional-extension",
        last_publication="complete",
    )
    return render_summary(
        MaintainerSummary(
            state=state,
            head_sha=machine_state.head_sha,
            result="Proposal published.",
            ci_status="Not started.",
            owner_action="Review proposal.",
            machine_state=machine_state,
        )
    )


def test_registry_rejects_duplicate_candidate_keys() -> None:
    payload = _coverage_payload()
    with pytest.raises(ValidationError, match="candidate keys must be unique"):
        _registry(payload, payload)


def test_candidate_rejects_duplicate_official_urls() -> None:
    with pytest.raises(ValidationError, match="official URLs must be unique"):
        CoverageCandidate.model_validate(
            _coverage_payload(
                urls=[
                    "https://operator.example.org/horn",
                    "https://operator.example.org/horn",
                ]
            ),
            strict=True,
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (_coverage_payload(kind="stay_destination"), "prefix must match"),
        (
            _coverage_payload(urls=["http://127.0.0.1/horn"]),
            "direct external HTTP",
        ),
        (
            {**_coverage_payload(), "alpine_subregion": "Rockies"},
            "Input should be",
        ),
        ({**_coverage_payload(), "mutable_status": "proposed"}, "Extra inputs"),
    ],
)
def test_registry_candidate_fails_closed(
    payload: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        CoverageCandidate.model_validate(payload, strict=True)


def test_candidate_fingerprint_canonicalizes_url_order() -> None:
    left = CoverageCandidate.model_validate(
        _coverage_payload(
            urls=["https://operator.example.org/z", "https://operator.example.org/a"]
        ),
        strict=True,
    )
    right = CoverageCandidate.model_validate(
        _coverage_payload(
            urls=["https://operator.example.org/a", "https://operator.example.org/z"]
        ),
        strict=True,
    )

    assert left.official_urls == (
        "https://operator.example.org/a",
        "https://operator.example.org/z",
    )
    assert left.fingerprint == right.fingerprint


def test_checked_in_registry_is_bounded_to_catalog_and_exact_backlog_markers() -> None:
    registry = CoverageRegistry.model_validate_json(
        REGISTRY_PATH.read_text(encoding="utf-8")
    )
    catalog_keys = catalog_entity_keys(CATALOG_PATH)
    backlog_keys = {
        candidate.key
        for candidate in parse_catalog_backlog(
            Path("docs/product-backlog.md").read_text(encoding="utf-8")
        )
    }
    registry_keys = {entry.candidate_key for entry in registry.entries}
    sourceable_backlog_keys = registry_keys & backlog_keys

    assert len(registry_keys & catalog_keys) == 52
    assert sourceable_backlog_keys == {
        "ski_area:kitzbuheler-horn",
        "stay_destination:mittersill",
        "stay_destination:hollersbach",
        "stay_base:mittersill-pass-thurn",
        "stay_base:hollersbach-hollersbach",
        "stay_destination:reith-bei-kitzbuhel",
        "stay_destination:aurach-bei-kitzbuhel",
        "stay_base:kirchberg-aschau",
        "stay_destination:leogang",
        "stay_base:leogang-leogang",
        "ski_area:leogang-ski-area",
        "ski_area_access:leogang-leogang--leogang-ski-area",
        "stay_destination:fieberbrunn",
        "stay_base:fieberbrunn-fieberbrunn",
        "ski_area:fieberbrunn-ski-area",
        "ski_area_access:fieberbrunn-fieberbrunn--fieberbrunn-ski-area",
        "terrain_domain:skicircus-saalbach-hinterglemm-leogang-fieberbrunn",
    }
    assert registry_keys <= catalog_keys | backlog_keys
    assert "ski_area:example-only" not in registry_keys
    assert "stay_destination:also-example" not in registry_keys


def test_represented_registry_urls_come_from_identity_trust_groups() -> None:
    registry = CoverageRegistry.model_validate_json(
        REGISTRY_PATH.read_text(encoding="utf-8")
    )
    trust = json.loads(TRUST_PATH.read_text(encoding="utf-8"))
    namespaces = {
        "stay_destination": ("stay_destinations", "identity_location"),
        "ski_area": ("ski_areas", "identity_coordinates"),
    }
    catalog_keys = catalog_entity_keys(CATALOG_PATH)

    for entry in registry.entries:
        if entry.candidate_key not in catalog_keys:
            continue
        namespace, group = namespaces[entry.candidate_kind]
        entity_id = entry.candidate_key.split(":", 1)[1]
        trusted_urls = set(
            trust["entities"][namespace][entity_id]["field_source_refs"][group]
        )
        assert set(entry.official_urls) <= trusted_urls


def test_backlog_parser_preserves_item_and_marker_order_and_ignores_preamble() -> None:
    markdown = _backlog(("stay_destination:leogang", "ski_area:leogang-ski-area"))
    markdown = markdown.replace(
        "## Current Backlog",
        "### Second Region\n\n"
        "- `stay_base:fieberbrunn-fieberbrunn`\n\n"
        "## Current Backlog",
    )

    candidates = parse_catalog_backlog(markdown)

    assert [item.key for item in candidates] == [
        "stay_destination:leogang",
        "ski_area:leogang-ski-area",
        "stay_base:fieberbrunn-fieberbrunn",
    ]
    assert all("example" not in item.key for item in candidates)
    assert candidates[0].backlog_ref == BACKLOG_REF
    assert candidates[0].official_urls == ()
    assert candidates[0].fingerprint == candidates[0].origin_fingerprint


@pytest.mark.parametrize(
    ("markdown", "message"),
    [
        ("# Backlog\n", "exactly one Catalog Curation Refinements"),
        (
            _backlog()
            + "\n## Catalog Curation Refinements\n\n### Other\n- `ski_area:other`\n",
            "exactly one Catalog Curation Refinements",
        ),
        (
            _backlog() + "\n" + _backlog().split("## Current Backlog", 1)[0],
            "exactly one Catalog Curation Refinements",
        ),
        (
            _backlog(("ski_area:duplicate", "ski_area:duplicate")),
            "backlog candidate markers must be unique",
        ),
        (
            _backlog().replace(
                "`stay_destination:leogang`", "`stay_destination:Leogang`"
            ),
            "malformed catalog candidate marker",
        ),
        (
            _backlog().replace(
                "`stay_destination:leogang`", "stay_destination:leogang"
            ),
            "must be enclosed in single backticks",
        ),
        (
            _backlog().replace(
                "## Current Backlog",
                "### Regional--Extension\n\n- `ski_area:other`\n\n## Current Backlog",
            ),
            "backlog item anchors must be unique",
        ),
    ],
)
def test_backlog_parser_rejects_ambiguous_or_malformed_input(
    markdown: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        parse_catalog_backlog(markdown)


def test_catalog_entity_keys_uses_normalized_schema_mapping() -> None:
    keys = catalog_entity_keys(CATALOG_PATH)

    assert "stay_destination:kitzbuhel" in keys
    assert "ski_area:kitzbuhel-ski-area" in keys
    assert any(key.startswith("ski_area_access:") for key in keys)
    assert not any(key.startswith("ski_area_acces:") for key in keys)


def test_catalog_entity_keys_rejects_invalid_schema_and_duplicates(
    tmp_path: Path,
) -> None:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    payload["ski_areas"].append(payload["ski_areas"][0])
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate ski_area_id"):
        catalog_entity_keys(path)


def test_with_official_urls_validates_sorts_and_preserves_origin() -> None:
    candidate = _backlog_candidate()
    updated = with_official_urls(
        candidate,
        (
            "https://operator.example.org/z",
            "https://operator.example.org/a",
        ),
    )

    assert updated.official_urls == (
        "https://operator.example.org/a",
        "https://operator.example.org/z",
    )
    assert updated.origin_fingerprint == candidate.origin_fingerprint
    assert updated.fingerprint != candidate.fingerprint
    assert require_publication_ready(updated) is updated


def test_registry_candidate_uses_entry_fingerprint_without_double_hashing() -> None:
    entry = CoverageCandidate.model_validate(_coverage_payload(), strict=True)
    selected = select_discovery_candidate(
        backlog=[],
        registry=CoverageRegistry(schema_version=1, entries=(entry,)),
        catalog_keys=set(),
        open_proposals=[],
        declined_fingerprints=set(),
    )

    assert selected is not None
    assert selected.origin == "registry"
    assert selected.origin_fingerprint == entry.fingerprint
    assert selected.fingerprint == entry.fingerprint


def test_registry_candidate_url_enrichment_cannot_change_entry_fingerprint() -> None:
    entry = CoverageCandidate.model_validate(_coverage_payload(), strict=True)
    candidate = select_discovery_candidate(
        backlog=[],
        registry=CoverageRegistry(schema_version=1, entries=(entry,)),
        catalog_keys=set(),
        open_proposals=[],
        declined_fingerprints=set(),
    )
    assert candidate is not None

    preserved = with_official_urls(candidate, candidate.official_urls)
    assert preserved.origin_fingerprint == entry.fingerprint
    assert preserved.fingerprint == entry.fingerprint
    with pytest.raises(ValueError, match="registry official URLs are immutable"):
        with_official_urls(candidate, ("https://operator.example.org/changed",))


@pytest.mark.parametrize(
    "urls",
    [
        (),
        ("https://operator.example.org/horn", "https://operator.example.org/horn"),
        ("http://10.0.0.1/horn",),
    ],
)
def test_with_official_urls_rejects_unpublishable_values(urls: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        with_official_urls(_backlog_candidate(), urls)


def test_backlog_candidate_is_selected_before_registry_candidate() -> None:
    selected = select_discovery_candidate(
        backlog=[_backlog_candidate()],
        registry=_registry(_coverage_payload()),
        catalog_keys=set(),
        open_proposals=[],
        declined_fingerprints=set(),
    )

    assert selected is not None
    assert selected.origin == "backlog"


def test_three_open_proposals_stop_discovery_but_unrelated_records_do_not() -> None:
    candidates = [
        _proposal(candidate_key=f"ski_area:area-{index}") for index in range(3)
    ]
    assert (
        select_discovery_candidate(
            backlog=[_backlog_candidate()],
            registry=_registry(),
            catalog_keys=set(),
            open_proposals=candidates,
            declined_fingerprints=set(),
        )
        is None
    )

    candidates[2] = ProposalRecord(lifecycle_state="OPEN", is_proposal=False)
    assert (
        select_discovery_candidate(
            backlog=[_backlog_candidate()],
            registry=_registry(),
            catalog_keys=set(),
            open_proposals=candidates,
            declined_fingerprints=set(),
        )
        is not None
    )


def test_closed_proposal_does_not_consume_open_cap() -> None:
    records = [
        _proposal(candidate_key=f"ski_area:area-{index}") for index in range(2)
    ] + [_proposal(lifecycle_state="CLOSED")]

    assert (
        select_discovery_candidate(
            backlog=[_backlog_candidate()],
            registry=_registry(),
            catalog_keys=set(),
            open_proposals=records,
            declined_fingerprints=set(),
        )
        is not None
    )


def test_selection_skips_catalog_open_key_and_graph_overlap() -> None:
    backlog = parse_catalog_backlog(
        _backlog(("stay_destination:first", "stay_destination:second"))
        .replace("### Regional Extension", "### First Graph")
        .replace(
            "## Current Backlog",
            "### Second Graph\n\n- `ski_area:third`\n\n## Current Backlog",
        )
    )
    selected = select_discovery_candidate(
        backlog=backlog,
        registry=_registry(),
        catalog_keys={"stay_destination:first"},
        open_proposals=[
            _proposal(candidate_key="stay_destination:second", graph="first-graph")
        ],
        declined_fingerprints=set(),
    )

    assert selected is not None
    assert selected.key == "ski_area:third"


def test_open_nonproposal_candidate_still_blocks_regional_overlap() -> None:
    candidate = _backlog_candidate()
    record = _proposal(
        candidate_key="stay_destination:accepted-candidate",
        graph=candidate.regional_graph_key,
        is_proposal=False,
    )

    assert (
        select_discovery_candidate(
            backlog=[candidate],
            registry=_registry(),
            catalog_keys=set(),
            open_proposals=[record],
            declined_fingerprints=set(),
        )
        is None
    )


def test_closed_declined_fingerprint_is_not_recreated() -> None:
    candidate = _backlog_candidate()
    assert (
        select_discovery_candidate(
            backlog=[candidate],
            registry=_registry(),
            catalog_keys=set(),
            open_proposals=[],
            declined_fingerprints={(candidate.key, candidate.origin_fingerprint)},
        )
        is None
    )


def test_registry_copy_does_not_bypass_declined_backlog_origin() -> None:
    candidate = _backlog_candidate()
    registry_copy = _coverage_payload(
        key=candidate.key,
        kind=candidate.candidate_kind,
    )
    assert (
        select_discovery_candidate(
            backlog=[candidate],
            registry=_registry(registry_copy),
            catalog_keys=set(),
            open_proposals=[],
            declined_fingerprints={(candidate.key, candidate.origin_fingerprint)},
        )
        is None
    )


def test_url_less_backlog_candidate_requires_research_before_publication() -> None:
    candidate = _backlog_candidate()
    selected = select_discovery_candidate(
        backlog=[candidate],
        registry=_registry(),
        catalog_keys=set(),
        open_proposals=[],
        declined_fingerprints=set(),
    )

    assert selected == candidate
    with pytest.raises(ValueError, match="official identity URL"):
        require_publication_ready(selected)


def test_proposal_record_parses_only_trusted_machine_state() -> None:
    record = proposal_record_from_comment(
        _render_candidate_summary(),
        lifecycle_state="OPEN",
        maintainer_state=MaintainerState.PROPOSAL,
    )

    assert record.candidate_key == "ski_area:horn"
    assert record.regional_graph_key == "regional-extension"
    assert record.is_proposal is True


def test_proposal_record_fails_closed_for_malformed_proposal_marker() -> None:
    malformed = _render_candidate_summary().replace('"schema_version":1', '"extra":1')
    with pytest.raises(ValueError, match="valid machine state"):
        proposal_record_from_comment(
            malformed,
            lifecycle_state="OPEN",
            maintainer_state=MaintainerState.PROPOSAL,
        )


def test_unrelated_record_does_not_require_candidate_machine_state() -> None:
    record = proposal_record_from_comment(
        "No maintainer marker.",
        lifecycle_state="OPEN",
        maintainer_state=None,
    )

    assert record.is_proposal is False
    assert record.candidate_key is None


def test_proposal_record_model_rejects_partial_metadata() -> None:
    with pytest.raises(ValidationError, match="candidate metadata must be complete"):
        ProposalRecord(
            lifecycle_state="OPEN",
            is_proposal=True,
            candidate_key="ski_area:horn",
        )


def test_origin_cleanup_requires_new_catalog_key_and_exact_marker_removal() -> None:
    candidate = _backlog_candidate()
    proposed_backlog = _backlog(())

    verify_origin_cleanup(
        candidate=candidate,
        base_catalog_keys={"ski_area:existing"},
        proposed_catalog_keys={"ski_area:existing", candidate.key},
        proposed_backlog=proposed_backlog,
    )

    with pytest.raises(ValueError, match="leaves its resolved backlog marker"):
        verify_origin_cleanup(
            candidate=candidate,
            base_catalog_keys={"ski_area:existing"},
            proposed_catalog_keys={"ski_area:existing", candidate.key},
            proposed_backlog=_backlog(),
        )


@pytest.mark.parametrize(
    ("base", "proposed", "message"),
    [
        (
            {"stay_destination:leogang"},
            {"stay_destination:leogang"},
            "already exists in base catalog",
        ),
        ({"ski_area:existing"}, {"ski_area:existing"}, "does not add"),
        (
            {"ski_area:existing"},
            {"stay_destination:leogang"},
            "must not remove existing catalog keys",
        ),
        (
            {"ski_area:Bad"},
            {"ski_area:Bad", "stay_destination:leogang"},
            "malformed catalog entity key",
        ),
    ],
)
def test_origin_cleanup_rejects_malformed_catalog_sets(
    base: set[str], proposed: set[str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        verify_origin_cleanup(
            candidate=_backlog_candidate(),
            base_catalog_keys=base,
            proposed_catalog_keys=proposed,
            proposed_backlog=_backlog(()),
        )


def test_discovery_subregion_rotates_deterministically_across_all_six_regions() -> None:
    mondays = [date.fromisocalendar(2026, week, 1) for week in range(1, 7)]

    assert {discovery_subregion(day) for day in mondays} == set(DISCOVERY_SUBREGIONS)
    assert discovery_subregion(date(2026, 7, 8)) == discovery_subregion(
        date.fromisoformat("2026-07-08")
    )
