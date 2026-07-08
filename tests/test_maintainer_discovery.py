from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.catalog import CatalogSnapshot
from app.domain.catalog_trust import CatalogTrustManifest
from ops.maintainer import SUMMARY_MARKER
from ops.maintainer.discovery import (
    DISCOVERY_SUBREGIONS,
    CoverageCandidate,
    CoverageRegistry,
    DiscoveryCandidate,
    DiscoveryOrigin,
    ProposalRecord,
    catalog_entity_keys,
    discovery_subregion,
    parse_catalog_backlog,
    parse_discovery_origin,
    proposal_record_from_pull_request,
    render_candidate_discovery_origin,
    render_discovery_origin,
    require_publication_ready,
    select_discovery_candidate,
    verify_origin_cleanup,
    with_official_urls,
)
from ops.maintainer.github import TRUSTED_MAINTAINER_LOGIN, GitHubComment
from ops.maintainer.models import (
    MachineState,
    MaintainerLane,
    MaintainerState,
    PullRequest,
)
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
    pr_number: int = 101,
    candidate_key: str = "ski_area:open-area",
    graph: str = "open-region",
    lifecycle_state: str = "OPEN",
    is_proposal: bool = True,
    lane: MaintainerLane = MaintainerLane.CATALOG_DISCOVERY,
) -> ProposalRecord:
    return ProposalRecord(
        pr_number=pr_number,
        lifecycle_state=lifecycle_state,
        lane=lane,
        is_discovery_lineage=True,
        is_proposal=is_proposal,
        candidate_key=candidate_key,
        origin_fingerprint="a" * 64,
        fingerprint="b" * 64,
        regional_graph_key=graph,
    )


def _origin_marker(
    *,
    candidate_key: str = "ski_area:horn",
    origin_fingerprint: str = "b" * 64,
    fingerprint: str = "c" * 64,
    regional_graph_key: str = "regional-extension",
) -> str:
    return render_discovery_origin(
        DiscoveryOrigin(
            candidate_key=candidate_key,
            origin_fingerprint=origin_fingerprint,
            fingerprint=fingerprint,
            regional_graph_key=regional_graph_key,
        )
    )


def _pull_request(
    *,
    number: int = 101,
    lifecycle_state: str = "OPEN",
    labels: frozenset[str] = frozenset(
        {MaintainerLane.CATALOG_DISCOVERY, MaintainerState.PROPOSAL}
    ),
    changed_paths: frozenset[str] = frozenset({"app/data/catalog.json"}),
    body: str | None = None,
    head_sha: str = "a" * 40,
) -> PullRequest:
    return PullRequest(
        number=number,
        title="Discover Horn",
        url=f"https://github.com/lampssy/ai-sports-travel-planner/pull/{number}",
        base_ref_name="main",
        head_ref_name=f"codex/catalog-curation-{number}",
        head_repository_owner="lampssy",
        is_cross_repository=False,
        lifecycle_state=lifecycle_state,
        created_at=datetime(2026, 7, 8, tzinfo=UTC),
        labels=labels,
        head_sha=head_sha,
        mergeable="MERGEABLE",
        check_state="success",
        changed_paths=changed_paths,
        body=body if body is not None else _origin_marker(),
    )


def _comment(
    body: str | None = None,
    *,
    comment_id: int = 501,
    author_login: str = TRUSTED_MAINTAINER_LOGIN,
) -> GitHubComment:
    return GitHubComment(
        comment_id=comment_id,
        body=body if body is not None else _render_candidate_summary(),
        author_login=author_login,
    )


def _render_candidate_summary(
    *,
    state: MaintainerState = MaintainerState.PROPOSAL,
    candidate_key: str = "ski_area:horn",
    origin_fingerprint: str = "b" * 64,
    fingerprint: str = "c" * 64,
    regional_graph_key: str = "regional-extension",
    head_sha: str = "a" * 40,
) -> str:
    machine_state = MachineState(
        head_sha=head_sha,
        lineage_id="discovery-horn",
        candidate_key=candidate_key,
        candidate_origin_fingerprint=origin_fingerprint,
        candidate_fingerprint=fingerprint,
        regional_graph_key=regional_graph_key,
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


def test_equivalent_url_spellings_canonicalize_before_fingerprinting() -> None:
    decorated = CoverageCandidate.model_validate(
        _coverage_payload(urls=["HTTPS://BÜCHER.EXAMPLE.ORG:443#publisher-navigation"]),
        strict=True,
    )
    canonical = CoverageCandidate.model_validate(
        _coverage_payload(urls=["https://xn--bcher-kva.example.org/"]),
        strict=True,
    )

    assert decorated.official_urls == ("https://xn--bcher-kva.example.org/",)
    assert decorated.fingerprint == canonical.fingerprint


def test_equivalent_urls_are_duplicates_after_canonicalization() -> None:
    with pytest.raises(ValidationError, match="official URLs must be unique"):
        CoverageCandidate.model_validate(
            _coverage_payload(
                urls=[
                    "https://operator.example.org:443/path?q=1#first",
                    "HTTPS://OPERATOR.EXAMPLE.ORG/path?q=1#second",
                ]
            ),
            strict=True,
        )


def test_url_canonicalization_preserves_meaningful_path_and_query() -> None:
    candidate = CoverageCandidate.model_validate(
        _coverage_payload(
            urls=["HTTP://OPERATOR.EXAMPLE.ORG:80/path/?season=winter#map"]
        ),
        strict=True,
    )

    assert candidate.official_urls == (
        "http://operator.example.org/path/?season=winter",
    )


def test_discovery_origin_marker_roundtrips_and_is_candidate_stable() -> None:
    candidate = with_official_urls(
        _backlog_candidate(),
        ("https://operator.example.org/leogang",),
    )
    origin = DiscoveryOrigin(
        candidate_key=candidate.key,
        origin_fingerprint=candidate.origin_fingerprint,
        fingerprint=candidate.fingerprint,
        regional_graph_key=candidate.regional_graph_key,
    )

    marker = render_discovery_origin(origin)

    assert marker.startswith("<!-- snowcast-discovery-origin:{")
    assert marker.endswith("} -->")
    assert "\n" not in marker
    assert parse_discovery_origin(f"Managed context\n{marker}\nMore context") == origin
    assert render_candidate_discovery_origin(candidate) == marker
    assert "head_sha" not in marker
    assert "lane:" not in marker

    invalid_origin = origin.model_copy(update={"candidate_key": "INVALID"})
    with pytest.raises(ValidationError):
        render_discovery_origin(invalid_origin)

    with pytest.raises(ValueError, match="official identity URL"):
        render_candidate_discovery_origin(_backlog_candidate())


def test_discovery_origin_parser_rejects_duplicate_and_noncanonical_markers() -> None:
    candidate = with_official_urls(
        _backlog_candidate(),
        ("https://operator.example.org/leogang",),
    )
    marker = render_candidate_discovery_origin(candidate)

    with pytest.raises(ValueError, match="exactly one canonical"):
        parse_discovery_origin(f"{marker}\n{marker}")

    noncanonical = marker.replace(':"', ': "', 1)
    with pytest.raises(ValueError, match="canonical"):
        parse_discovery_origin(noncanonical)


@pytest.mark.parametrize(
    "body",
    [
        "snowcast-discovery-origin: dangling signal",
        '<!-- snowcast-discovery-origin:{"candidate_key":"ski_area:horn"}',
        (
            '<!-- snowcast-discovery-origin:{"candidate_key":'
            '"ski_area:horn\\u0000","fingerprint":"'
            + "a" * 64
            + '","origin_fingerprint":"'
            + "b" * 64
            + '","regional_graph_key":"regional-extension"} -->'
        ),
    ],
)
def test_discovery_origin_parser_rejects_malformed_or_unsafe_signal(
    body: str,
) -> None:
    with pytest.raises(ValueError, match="discovery origin marker"):
        parse_discovery_origin(body)


def test_discovery_origin_parser_returns_none_without_marker_signal() -> None:
    assert parse_discovery_origin("Ordinary managed PR body.") is None


def test_checked_in_registry_is_bounded_to_catalog_and_exact_backlog_markers() -> None:
    registry = CoverageRegistry.model_validate_json(
        REGISTRY_PATH.read_text(encoding="utf-8")
    )
    snapshot = CatalogSnapshot.model_validate_json(
        CATALOG_PATH.read_text(encoding="utf-8")
    )
    trust = CatalogTrustManifest.model_validate_json(
        TRUST_PATH.read_text(encoding="utf-8")
    )
    trust.validate_against_catalog(snapshot)
    catalog_keys = catalog_entity_keys(CATALOG_PATH)
    backlog_keys = {
        candidate.key
        for candidate in parse_catalog_backlog(
            Path("docs/product-backlog.md").read_text(encoding="utf-8")
        )
    }
    registry_keys = {entry.candidate_key for entry in registry.entries}
    sourceable_backlog_keys = registry_keys & backlog_keys
    expected_represented = {
        f"stay_destination:{destination.stay_destination_id}"
        for destination in snapshot.stay_destinations
        if trust.entities["stay_destinations"][
            destination.stay_destination_id
        ].field_source_refs["identity_location"]
    } | {
        f"ski_area:{area.ski_area_id}"
        for area in snapshot.ski_areas
        if trust.entities["ski_areas"][area.ski_area_id].field_source_refs[
            "identity_coordinates"
        ]
    }

    assert len(expected_represented) == 52
    assert registry_keys & catalog_keys == expected_represented
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
    assert require_publication_ready(updated) == updated


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


def test_public_boundaries_revalidate_invalid_model_copies() -> None:
    candidate = _backlog_candidate()
    invalid_candidate = candidate.model_copy(update={"key": "INVALID"})
    registry_entry = CoverageCandidate.model_validate(_coverage_payload(), strict=True)
    invalid_entry = registry_entry.model_copy(update={"candidate_key": "INVALID"})
    invalid_registry = CoverageRegistry(
        schema_version=1,
        entries=(registry_entry,),
    ).model_copy(update={"entries": (invalid_entry,)})
    invalid_record = _proposal().model_copy(update={"pr_number": 0})

    with pytest.raises(ValidationError):
        require_publication_ready(invalid_candidate)
    with pytest.raises(ValidationError):
        select_discovery_candidate(
            backlog=[invalid_candidate],
            registry=_registry(),
            catalog_keys=set(),
            open_proposals=[],
            declined_fingerprints=set(),
        )
    with pytest.raises(ValidationError):
        select_discovery_candidate(
            backlog=[],
            registry=invalid_registry,
            catalog_keys=set(),
            open_proposals=[],
            declined_fingerprints=set(),
        )
    with pytest.raises(ValidationError):
        select_discovery_candidate(
            backlog=[],
            registry=_registry(),
            catalog_keys=set(),
            open_proposals=[invalid_record],
            declined_fingerprints=set(),
        )
    with pytest.raises(ValidationError):
        verify_origin_cleanup(
            candidate=invalid_candidate,
            base_catalog_keys=set(),
            proposed_catalog_keys={"stay_destination:leogang"},
            proposed_backlog=_backlog(()),
        )


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
        _proposal(pr_number=100 + index, candidate_key=f"ski_area:area-{index}")
        for index in range(3)
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

    candidates[2] = ProposalRecord(
        pr_number=999,
        lifecycle_state="OPEN",
        lane=MaintainerLane.CATALOG_CURATION,
        is_discovery_lineage=False,
        is_proposal=False,
    )
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
        _proposal(pr_number=100 + index, candidate_key=f"ski_area:area-{index}")
        for index in range(2)
    ] + [_proposal(pr_number=102, lifecycle_state="CLOSED")]

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


def test_proposal_record_uses_exactly_one_trusted_canonical_summary() -> None:
    forged = _comment(comment_id=1, author_login="attacker")
    record = proposal_record_from_pull_request(
        _pull_request(),
        [forged, _comment(comment_id=2)],
    )

    assert record.pr_number == 101
    assert record.lane is MaintainerLane.CATALOG_DISCOVERY
    assert record.is_discovery_lineage is True
    assert record.candidate_key == "ski_area:horn"
    assert record.regional_graph_key == "regional-extension"
    assert record.is_proposal is True


@pytest.mark.parametrize(
    "comments",
    [
        [],
        [_comment(author_login="attacker")],
    ],
)
def test_open_discovery_lineage_rejects_deleted_or_untrusted_summary(
    comments: list[GitHubComment],
) -> None:
    with pytest.raises(ValueError, match="exactly one trusted canonical summary"):
        proposal_record_from_pull_request(_pull_request(), comments)


@pytest.mark.parametrize(
    "labels",
    [
        frozenset({MaintainerLane.CATALOG_DISCOVERY}),
        frozenset({MaintainerLane.CATALOG_CURATION, MaintainerState.PROPOSAL}),
    ],
)
def test_discovery_lane_or_proposal_state_requires_body_origin_marker(
    labels: frozenset[str],
) -> None:
    with pytest.raises(ValueError, match="discovery origin marker"):
        proposal_record_from_pull_request(
            _pull_request(labels=labels, body=""),
            [_comment()],
        )


def test_discovery_lineage_rejects_malformed_trusted_summary() -> None:
    malformed = _render_candidate_summary().replace('"schema_version":1', '"extra":1')
    with pytest.raises(ValueError, match="valid candidate machine state"):
        proposal_record_from_pull_request(_pull_request(), [_comment(malformed)])

    duplicate_marker = f"{_render_candidate_summary()}\n{SUMMARY_MARKER}"
    with pytest.raises(ValueError, match="canonical maintainer summary"):
        proposal_record_from_pull_request(_pull_request(), [_comment(duplicate_marker)])


def test_discovery_lineage_rejects_incomplete_candidate_machine_metadata() -> None:
    machine_state = MachineState(
        head_sha="a" * 40,
        lineage_id="incomplete-candidate",
        candidate_key="ski_area:horn",
        last_publication="complete",
    )
    body = render_summary(
        MaintainerSummary(
            state=MaintainerState.PROPOSAL,
            head_sha=machine_state.head_sha,
            result="Proposal published.",
            ci_status="Not started.",
            owner_action="Review proposal.",
            machine_state=machine_state,
        )
    )

    with pytest.raises(ValidationError, match="candidate metadata must be complete"):
        proposal_record_from_pull_request(_pull_request(), [_comment(body)])


def test_proposal_boundary_revalidates_pr_and_comment_identity() -> None:
    invalid_pr = _pull_request().model_copy(update={"number": 0})
    with pytest.raises(ValidationError):
        proposal_record_from_pull_request(invalid_pr, [_comment()])

    invalid_comment = GitHubComment(
        comment_id=0,
        body=f"{SUMMARY_MARKER} secret-do-not-echo",
        author_login=TRUSTED_MAINTAINER_LOGIN,
    )
    with pytest.raises(ValueError) as error:
        proposal_record_from_pull_request(_pull_request(), [invalid_comment])
    assert "secret-do-not-echo" not in str(error.value)


def test_discovery_lineage_rejects_duplicate_trusted_summaries() -> None:
    with pytest.raises(ValueError, match="exactly one trusted canonical summary"):
        proposal_record_from_pull_request(
            _pull_request(),
            [_comment(comment_id=1), _comment(comment_id=2)],
        )


def test_approved_discovery_and_routed_curation_remain_discovery_lineage() -> None:
    approved = proposal_record_from_pull_request(
        _pull_request(labels=frozenset({MaintainerLane.CATALOG_DISCOVERY})),
        [_comment()],
    )
    routed = proposal_record_from_pull_request(
        _pull_request(
            labels=frozenset(
                {MaintainerLane.CATALOG_CURATION, MaintainerState.WORKING}
            ),
            changed_paths=frozenset({"app/data/catalog.json"}),
        ),
        [_comment()],
    )

    assert approved.is_discovery_lineage and not approved.is_proposal
    assert routed.is_discovery_lineage and not routed.is_proposal
    assert routed.lane is MaintainerLane.CATALOG_CURATION
    for record in (approved, routed):
        assert (
            select_discovery_candidate(
                backlog=[_backlog_candidate("ski_area:horn")],
                registry=_registry(),
                catalog_keys=set(),
                open_proposals=[record],
                declined_fingerprints=set(),
            )
            is None
        )


def test_unrelated_curation_record_does_not_require_summary() -> None:
    record = proposal_record_from_pull_request(
        _pull_request(
            labels=frozenset({MaintainerLane.CATALOG_CURATION}),
            changed_paths=frozenset({"app/data/catalog.json"}),
            body="",
        ),
        [],
    )

    assert record.is_discovery_lineage is False
    assert record.candidate_key is None


def test_curation_candidate_summary_without_origin_is_inconsistent() -> None:
    with pytest.raises(ValueError, match="candidate metadata.*origin marker"):
        proposal_record_from_pull_request(
            _pull_request(
                labels=frozenset({MaintainerLane.CATALOG_CURATION}),
                body="",
            ),
            [_comment()],
        )


def test_origin_marker_on_unlabeled_open_pr_creates_discovery_lineage() -> None:
    record = proposal_record_from_pull_request(
        _pull_request(labels=frozenset()),
        [_comment()],
    )

    assert record.is_discovery_lineage is True
    assert record.lane is None
    assert record.candidate_key == "ski_area:horn"


def test_origin_marker_requires_trusted_summary_after_curation_routing() -> None:
    with pytest.raises(ValueError, match="exactly one trusted canonical summary"):
        proposal_record_from_pull_request(
            _pull_request(labels=frozenset({MaintainerLane.CATALOG_CURATION})),
            [_comment(author_login="attacker")],
        )


def test_discovery_origin_must_match_summary_candidate_metadata() -> None:
    conflicting_origin = _origin_marker(fingerprint="d" * 64)

    with pytest.raises(ValueError, match="does not match discovery origin"):
        proposal_record_from_pull_request(
            _pull_request(body=conflicting_origin),
            [_comment()],
        )


def test_discovery_summary_head_must_match_current_pr_head() -> None:
    with pytest.raises(ValueError, match="does not match pull request head"):
        proposal_record_from_pull_request(
            _pull_request(head_sha="d" * 40),
            [_comment()],
        )


def test_closed_origin_lineage_does_not_block_new_selection() -> None:
    closed = proposal_record_from_pull_request(
        _pull_request(
            lifecycle_state="CLOSED",
            labels=frozenset({MaintainerLane.CATALOG_CURATION}),
        ),
        [_comment()],
    )

    assert closed.is_discovery_lineage is True
    assert (
        select_discovery_candidate(
            backlog=[_backlog_candidate("ski_area:horn")],
            registry=_registry(),
            catalog_keys=set(),
            open_proposals=[closed],
            declined_fingerprints=set(),
        )
        is not None
    )


def test_proposal_record_model_rejects_partial_metadata() -> None:
    with pytest.raises(ValidationError, match="candidate metadata must be complete"):
        ProposalRecord(
            pr_number=101,
            lifecycle_state="OPEN",
            lane=MaintainerLane.CATALOG_DISCOVERY,
            is_discovery_lineage=True,
            is_proposal=True,
            candidate_key="ski_area:horn",
        )


def test_selection_deduplicates_identical_pr_records_and_rejects_conflicts() -> None:
    record = _proposal(pr_number=123)
    assert (
        select_discovery_candidate(
            backlog=[_backlog_candidate()],
            registry=_registry(),
            catalog_keys=set(),
            open_proposals=[record, record, record],
            declined_fingerprints=set(),
        )
        is not None
    )

    conflicting = record.model_copy(update={"candidate_key": "ski_area:other"})
    with pytest.raises(ValueError, match="conflicting proposal records for PR 123"):
        select_discovery_candidate(
            backlog=[_backlog_candidate()],
            registry=_registry(),
            catalog_keys=set(),
            open_proposals=[record, conflicting],
            declined_fingerprints=set(),
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


@pytest.mark.parametrize("location", ["preamble", "outside-section"])
def test_origin_cleanup_rejects_marker_moved_outside_active_h3(
    location: str,
) -> None:
    candidate = _backlog_candidate()
    proposed_backlog = _backlog(())
    if location == "preamble":
        proposed_backlog = proposed_backlog.replace(
            "`ski_area:example-only`",
            candidate.backlog_marker,
        )
    else:
        proposed_backlog += f"\nMoved marker: {candidate.backlog_marker}\n"

    with pytest.raises(ValueError, match="leaves its resolved backlog marker"):
        verify_origin_cleanup(
            candidate=candidate,
            base_catalog_keys={"ski_area:existing"},
            proposed_catalog_keys={"ski_area:existing", candidate.key},
            proposed_backlog=proposed_backlog,
        )


def test_origin_cleanup_rejects_marker_for_any_new_coherent_graph_key() -> None:
    candidate = _backlog_candidate()
    proposed_backlog = _backlog(()) + "\nDeferred elsewhere: `ski_area:other`\n"

    with pytest.raises(ValueError, match="new catalog key marker remains"):
        verify_origin_cleanup(
            candidate=candidate,
            base_catalog_keys={"ski_area:existing"},
            proposed_catalog_keys={
                "ski_area:existing",
                candidate.key,
                "ski_area:other",
            },
            proposed_backlog=proposed_backlog,
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
