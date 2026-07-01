from __future__ import annotations

import json
import stat
from collections import Counter, defaultdict
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.data.catalog_loader import load_catalog_from_path
from app.data.catalog_migration import (
    CatalogMigration,
    CatalogMigrationBlocked,
    MigrationOverrides,
    build_catalog_migration,
    load_migration_overrides,
    main,
    serialize_catalog,
)
from app.data.loader import load_resorts_from_path, load_terrain_domains_from_path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_RESORTS_PATH = REPO_ROOT / "app/data/resorts.json"
LEGACY_TERRAIN_DOMAINS_PATH = REPO_ROOT / "app/data/terrain_domains.json"
OVERRIDES_PATH = REPO_ROOT / "app/data/catalog_migration_overrides.json"
CATALOG_PATH = REPO_ROOT / "app/data/catalog.json"

EXPECTED_MULTI_AREA_ACCESS = {
    ("chamonix-mont-blanc-chamonix", "brevent-flegere"),
    ("chamonix-mont-blanc-argentiere", "grands-montets"),
    ("chamonix-mont-blanc-argentiere", "balme-le-tour-vallorcine"),
    ("chamonix-mont-blanc-les-houches", "les-houches-saint-gervais"),
    ("zell-am-see-kaprun-kaprun", "maiskogel"),
    ("zell-am-see-kaprun-kaprun", "kitzsteinhorn"),
    ("zell-am-see-kaprun-zell-am-see", "schmittenhoehe"),
}
PROVIDER_ONLY_ACCESS_SOURCES = {
    "les-arcs-arc-1800-village--les-arcs-ski-area": (
        "https://www.bergfex.com/les-arcs-bourg-saint-maurice/"
    ),
    "st-anton-am-arlberg-st-anton-am-arlberg--st-anton-am-arlberg-ski-area": (
        "https://www.bergfex.com/stanton-stchristoph/"
    ),
    "ischgl-ischgl--ischgl-ski-area": (
        "https://www.bergfex.com/silvretta-arena-ischgl-samnaun/"
    ),
    "solden-solden--solden-ski-area": "https://www.bergfex.com/soelden/",
    "kitzbuhel-kitzbuhel--kitzbuhel-ski-area": (
        "https://www.bergfex.com/kitzbuehel-kirchberg/"
    ),
    "saalbach-hinterglemm-saalbach--saalbach-hinterglemm-ski-area": (
        "https://www.bergfex.com/saalbach-hinterglemm-leogang/"
    ),
    "mayrhofen-mayrhofen--mayrhofen-ski-area": ("https://www.bergfex.com/mayrhofen/"),
    "verbier-verbier--verbier-ski-area": "https://www.bergfex.com/verbier/",
    "st-moritz-st-moritz--st-moritz-ski-area": (
        "https://www.bergfex.com/st-moritz-corviglia/"
    ),
    "davos-klosters-davos-platz--davos-klosters-ski-area": (
        "https://www.bergfex.com/skiregionen/davos-klosters-mountains/"
    ),
    "laax-laax--laax-ski-area": "https://www.bergfex.com/laax/",
    "grindelwald-wengen-grindelwald--grindelwald-wengen-ski-area": (
        "https://www.bergfex.com/jungfrau-grindelwald-wengen/"
    ),
}
STUBAI_ACCESS_SOURCES = (
    "https://www.stubai.at/fileadmin/userdaten/tvb-stubai/dokumente/folder/"
    "winter/2025-26/bergbahnenfolder-winter-25-26-EN-komprimiert.pdf",
    "https://www.stubai.at/fileadmin/userdaten/tvb-stubai/dokumente/folder/"
    "winter/2025-26/stubaiMagazin-Wi-25-26-komprimiert.pdf",
)


@pytest.fixture(scope="module")
def migration() -> CatalogMigration:
    legacy_resorts = load_resorts_from_path(LEGACY_RESORTS_PATH)
    legacy_domains = load_terrain_domains_from_path(LEGACY_TERRAIN_DOMAINS_PATH)
    overrides = load_migration_overrides(OVERRIDES_PATH)
    return build_catalog_migration(legacy_resorts, legacy_domains, overrides)


def _json_key(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, (list, tuple)):
        value = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in value
        ]
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _legacy_ski_areas() -> dict[str, object]:
    legacy = load_resorts_from_path(LEGACY_RESORTS_PATH)
    return {
        area.ski_area_id: area
        for destination in legacy
        for area in destination.ski_areas
    }


def _migration_cli_args(
    *,
    output_path: Path,
    report_path: Path,
    resorts_path: Path = LEGACY_RESORTS_PATH,
    terrain_domains_path: Path = LEGACY_TERRAIN_DOMAINS_PATH,
    overrides_path: Path = OVERRIDES_PATH,
) -> list[str]:
    return [
        "--resorts-path",
        str(resorts_path),
        "--terrain-domains-path",
        str(terrain_domains_path),
        "--overrides-path",
        str(overrides_path),
        "--output-path",
        str(output_path),
        "--report-path",
        str(report_path),
    ]


def test_conversion_preserves_exact_entity_counts_and_ski_area_ids(
    migration: CatalogMigration,
) -> None:
    snapshot = migration.snapshot
    legacy_area_ids = set(_legacy_ski_areas())

    assert len(snapshot.stay_destinations) == 31
    assert len(snapshot.stay_bases) == 45
    assert len(snapshot.ski_areas) == 36
    assert len(snapshot.rental_display_facts) == 32
    assert len(snapshot.ski_regions) == 28
    assert len(snapshot.ski_area_access) == 47
    assert len(snapshot.terrain_domains) == 4
    assert len(snapshot.lift_pass_products) == 24
    assert {area.ski_area_id for area in snapshot.ski_areas} == legacy_area_ids
    assert migration.audit.ski_area_id_changes == ()


def test_conversion_preserves_every_ski_area_fact(
    migration: CatalogMigration,
) -> None:
    expected_by_id = _legacy_ski_areas()
    shared_fields = (
        "name",
        "latitude",
        "longitude",
        "base_elevation_m",
        "summit_elevation_m",
        "season_start_month",
        "season_end_month",
        "season_windows",
        "total_piste_km",
        "total_lift_count",
        "piste_km_by_difficulty",
    )

    for converted in migration.snapshot.ski_areas:
        legacy = expected_by_id[converted.ski_area_id]
        assert {
            field: _json_key(getattr(converted, field)) for field in shared_fields
        } == {field: _json_key(getattr(legacy, field)) for field in shared_fields}


def test_conversion_preserves_all_pass_prices_with_only_reviewed_shared_dedup(
    migration: CatalogMigration,
) -> None:
    legacy = load_resorts_from_path(LEGACY_RESORTS_PATH)
    overrides = load_migration_overrides(OVERRIDES_PATH)
    canonical_by_source_id = {
        source_id: canonical_id
        for canonical_id, source_ids in overrides.shared_pass_ids.items()
        for source_id in source_ids
    }
    expected_prices: dict[str, set[str]] = defaultdict(set)

    for destination in legacy:
        for product in destination.lift_pass_products:
            source_id = f"{destination.resort_id}:{product.lift_pass_product_id}"
            canonical_id = canonical_by_source_id.get(
                source_id, product.lift_pass_product_id
            )
            expected_prices[canonical_id].update(
                _json_key(price) for price in product.prices
            )

    actual_prices = {
        product.lift_pass_product_id: [_json_key(price) for price in product.prices]
        for product in migration.snapshot.lift_pass_products
    }
    assert set(actual_prices) == set(expected_prices)
    for product_id, prices in actual_prices.items():
        assert len(prices) == len(set(prices))
        assert set(prices) == expected_prices[product_id]


def test_pass_price_source_urls_are_normalized_before_shared_dedup() -> None:
    legacy = load_resorts_from_path(LEGACY_RESORTS_PATH)
    domains = load_terrain_domains_from_path(LEGACY_TERRAIN_DOMAINS_PATH)
    overrides = load_migration_overrides(OVERRIDES_PATH)
    tignes = next(item for item in legacy if item.resort_id == "tignes")
    shared_pass = next(
        product
        for product in tignes.lift_pass_products
        if product.lift_pass_product_id == "tignes-val-disere-ski-pass"
    )
    source_url = shared_pass.prices[0].source_url
    assert source_url is not None
    shared_pass.prices[0].source_url = f"  {source_url}  "

    converted = build_catalog_migration(legacy, domains, overrides).snapshot
    converted_pass = next(
        product
        for product in converted.lift_pass_products
        if product.lift_pass_product_id == "tignes-val-disere-ski-pass"
    )

    assert len(converted_pass.prices) == 3
    assert all(
        price.source_url is None or price.source_url == price.source_url.strip()
        for price in converted_pass.prices
    )


def test_conversion_builds_exact_trip_market_memberships(
    migration: CatalogMigration,
) -> None:
    snapshot = migration.snapshot
    memberships = {
        destination.stay_destination_id: destination.trip_market_region_id
        for destination in snapshot.stay_destinations
    }

    assert memberships["tignes"] == "tignes-val-disere"
    assert memberships["val-disere"] == "tignes-val-disere"
    assert memberships["madonna-di-campiglio"] == ("campiglio-dolomiti-di-brenta")
    assert memberships["pinzolo"] == "campiglio-dolomiti-di-brenta"
    assert memberships["folgarida-marilleva"] == "campiglio-dolomiti-di-brenta"
    assert memberships["chamonix-mont-blanc"] == "chamonix-valley"

    shared_destination_ids = {
        "tignes",
        "val-disere",
        "madonna-di-campiglio",
        "pinzolo",
        "folgarida-marilleva",
        "chamonix-mont-blanc",
    }
    assert all(
        destination_id == region_id
        for destination_id, region_id in memberships.items()
        if destination_id not in shared_destination_ids
    )
    assert all(
        region.grouping_policy == "trip_market" for region in snapshot.ski_regions
    )


def test_conversion_uses_only_explicit_non_cartesian_access(
    migration: CatalogMigration,
) -> None:
    legacy = load_resorts_from_path(LEGACY_RESORTS_PATH)
    expected_single_area_access = {
        (base.stay_base_id, destination.ski_areas[0].ski_area_id)
        for destination in legacy
        if len(destination.ski_areas) == 1
        for base in destination.stay_bases
    }
    actual_access = {
        (access.stay_base_id, access.ski_area_id)
        for access in migration.snapshot.ski_area_access
    }

    assert actual_access == expected_single_area_access | EXPECTED_MULTI_AREA_ACCESS


def test_conversion_moves_matching_access_facts_and_keeps_balme_unestimated(
    migration: CatalogMigration,
) -> None:
    access_by_pair = {
        (access.stay_base_id, access.ski_area_id): access
        for access in migration.snapshot.ski_area_access
    }
    balme = access_by_pair[
        ("chamonix-mont-blanc-argentiere", "balme-le-tour-vallorcine")
    ]
    kaprun_maiskogel = access_by_pair[("zell-am-see-kaprun-kaprun", "maiskogel")]
    kaprun_kitzsteinhorn = access_by_pair[
        ("zell-am-see-kaprun-kaprun", "kitzsteinhorn")
    ]

    assert balme.access_mode == "ski_bus"
    assert balme.is_direct is False
    assert balme.distance_m is None
    assert balme.duration_minutes is None
    assert balme.source_urls == (
        "https://en.chamonix.com/things-to-see-and-do/sports-and-outdoor/"
        "skiing-in-chamonix-mont-blanc-valley/list-of-ski-areas/"
        "ski-area-balme-vallorcine?espace_congres=124173",
    )
    assert kaprun_maiskogel.nearest_lift_name == "MK Maiskogelbahn"
    assert kaprun_maiskogel.distance_m == 266
    assert kaprun_maiskogel.regional_data_ids["nearest_lift_osm_way_id"] == (
        "158348741"
    )
    assert kaprun_kitzsteinhorn.distance_m is None
    assert kaprun_kitzsteinhorn.duration_minutes is None


def test_every_access_edge_has_direct_external_sources(
    migration: CatalogMigration,
) -> None:
    for access in migration.snapshot.ski_area_access:
        assert access.source_urls
        assert all(
            url.startswith(("http://", "https://")) for url in access.source_urls
        )
        assert all("docs/" not in url for url in access.source_urls)
    assert migration.audit.blocked_relationships == ()


def test_provider_only_edges_remain_estimated_without_access_precision(
    migration: CatalogMigration,
) -> None:
    access_by_id = {
        access.ski_area_access_id: access
        for access in migration.snapshot.ski_area_access
    }

    assert set(PROVIDER_ONLY_ACCESS_SOURCES) < set(access_by_id)
    for access_id, source_url in PROVIDER_ONLY_ACCESS_SOURCES.items():
        access = access_by_id[access_id]
        assert access.source_urls == (source_url,)
        assert access.access_mode == "unknown"
        assert access.is_direct is False
        assert access.distance_m is None
        assert access.duration_minutes is None
    assert migration.report_markdown.count("provider-backed/estimated") == 12


def test_stubai_edges_use_official_valley_ski_bus_without_precision(
    migration: CatalogMigration,
) -> None:
    access_by_id = {
        access.ski_area_access_id: access
        for access in migration.snapshot.ski_area_access
    }
    stubai_edge_ids = (
        "stubai-glacier-fulpmes--stubai-glacier-ski-area",
        "stubai-glacier-neustift-im-stubaital--stubai-glacier-ski-area",
    )

    for access_id in stubai_edge_ids:
        access = access_by_id[access_id]
        assert access.source_urls == STUBAI_ACCESS_SOURCES
        assert access.access_mode == "ski_bus"
        assert access.is_direct is False
        assert access.distance_m is None
        assert access.duration_minutes is None


def test_every_access_edge_has_reviewed_explicit_directness(
    migration: CatalogMigration,
) -> None:
    overrides = load_migration_overrides(OVERRIDES_PATH)
    access_by_id = {
        access.ski_area_access_id: access
        for access in migration.snapshot.ski_area_access
    }

    assert set(overrides.access_edge_overrides) == set(access_by_id)
    assert (
        access_by_id["la-plagne-plagne-centre--la-plagne-ski-area"].is_direct is False
    )
    assert all(
        not access.is_direct
        for access in access_by_id.values()
        if access.access_mode in {"unknown", "ski_bus"}
    )


def test_identity_only_osm_evidence_blocks_access_conversion() -> None:
    legacy = load_resorts_from_path(LEGACY_RESORTS_PATH)
    domains = load_terrain_domains_from_path(LEGACY_TERRAIN_DOMAINS_PATH)
    overrides = load_migration_overrides(OVERRIDES_PATH)
    sources = dict(overrides.destination_access_source_urls)
    sources.pop("val-disere")
    overrides = overrides.model_copy(
        update={"destination_access_source_urls": sources}, deep=True
    )

    with pytest.raises(CatalogMigrationBlocked) as error:
        build_catalog_migration(legacy, domains, overrides)

    assert error.value.relationship_ids == (
        "val-disere-la-daille--val-disere-ski-area",
        "val-disere-le-fornet--val-disere-ski-area",
        "val-disere-village--val-disere-ski-area",
    )


def test_missing_access_override_rejects_unreviewed_directness() -> None:
    legacy = load_resorts_from_path(LEGACY_RESORTS_PATH)
    domains = load_terrain_domains_from_path(LEGACY_TERRAIN_DOMAINS_PATH)
    overrides = load_migration_overrides(OVERRIDES_PATH)
    access_edges = dict(overrides.access_edge_overrides)
    missing_id = "la-plagne-plagne-centre--la-plagne-ski-area"
    access_edges.pop(missing_id, None)
    overrides = overrides.model_copy(
        update={"access_edge_overrides": access_edges}, deep=True
    )

    with pytest.raises(
        ValueError, match=f"missing explicit access override: {missing_id}"
    ):
        build_catalog_migration(legacy, domains, overrides)


def test_stay_base_identity_osm_ids_do_not_become_access_sources(
    migration: CatalogMigration,
) -> None:
    bases = {base.stay_base_id: base for base in migration.snapshot.stay_bases}
    accesses = {
        access.ski_area_access_id: access
        for access in migration.snapshot.ski_area_access
    }
    alta_badia_base = bases["alta-badia-corvara"]
    alta_badia_access = accesses["alta-badia-corvara--alta-badia-ski-area"]

    assert alta_badia_base.regional_data_ids["osm_relation_id"] == "47252"
    assert "https://www.openstreetmap.org/relation/47252" not in (
        alta_badia_access.source_urls
    )
    assert "https://www.openstreetmap.org/node/224065479" in (
        alta_badia_access.source_urls
    )

    for access in accesses.values():
        base = bases[access.stay_base_id]
        access_osm_ids = {
            value
            for key, value in access.regional_data_ids.items()
            if key.startswith("nearest_lift_osm_")
        }
        for key, value in base.regional_data_ids.items():
            if key.startswith("osm_") and value not in access_osm_ids:
                osm_kind = key.removeprefix("osm_").removesuffix("_id")
                assert f"https://www.openstreetmap.org/{osm_kind}/{value}" not in (
                    access.source_urls
                )


def test_osm_relation_alias_is_canonicalized(migration: CatalogMigration) -> None:
    livigno = next(
        base
        for base in migration.snapshot.stay_bases
        if base.stay_base_id == "livigno-livigno"
    )

    assert livigno.regional_data_ids["osm_relation_id"] == "47273"
    assert "osm_relation" not in livigno.regional_data_ids


@pytest.mark.parametrize("invalid_osm_id", ["0", "-1", "not-a-number"])
def test_malformed_typed_osm_ids_are_rejected(invalid_osm_id: str) -> None:
    legacy = load_resorts_from_path(LEGACY_RESORTS_PATH)
    domains = load_terrain_domains_from_path(LEGACY_TERRAIN_DOMAINS_PATH)
    overrides = load_migration_overrides(OVERRIDES_PATH)
    destination = legacy[0]
    destination.stay_bases[0].regional_data_ids["osm_relation_id"] = invalid_osm_id

    with pytest.raises(ValueError, match="osm_relation_id must be a positive integer"):
        build_catalog_migration(legacy, domains, overrides)


def test_access_override_requires_explicit_directness() -> None:
    payload = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    edge = next(iter(payload["access_edge_overrides"].values()))
    edge.pop("is_direct")

    with pytest.raises(ValidationError, match="is_direct"):
        MigrationOverrides.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "stale_value", "message"),
    [
        (
            "destination_access_source_urls",
            ("https://example.org/access",),
            "destination access source override references unknown destination",
        ),
        (
            "shared_pass_external_validity_summaries",
            "stale summary",
            "shared pass summary override references unknown pass",
        ),
        (
            "trip_market_names",
            "Stale market",
            "trip market name override references unknown shared market",
        ),
    ],
)
def test_stale_override_namespaces_are_rejected(
    field_name: str, stale_value: object, message: str
) -> None:
    legacy = load_resorts_from_path(LEGACY_RESORTS_PATH)
    domains = load_terrain_domains_from_path(LEGACY_TERRAIN_DOMAINS_PATH)
    overrides = load_migration_overrides(OVERRIDES_PATH)
    values = dict(getattr(overrides, field_name))
    values["stale-id"] = stale_value
    overrides = overrides.model_copy(update={field_name: values}, deep=True)

    with pytest.raises(ValueError, match=message):
        build_catalog_migration(legacy, domains, overrides)


def test_cli_rejects_output_report_alias_before_writing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    shared_path = tmp_path / "shared.json"

    result = main(_migration_cli_args(output_path=shared_path, report_path=shared_path))

    assert result == 1
    assert not shared_path.exists()
    assert "aliased paths: output_path and report_path" in capsys.readouterr().err


def test_cli_rejects_hard_linked_input_output_alias(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    resorts_path = tmp_path / "resorts.json"
    resorts_content = LEGACY_RESORTS_PATH.read_text(encoding="utf-8")
    resorts_path.write_text(resorts_content, encoding="utf-8")
    output_path = tmp_path / "catalog.json"
    output_path.hardlink_to(resorts_path)
    report_path = tmp_path / "report.md"

    result = main(
        _migration_cli_args(
            resorts_path=resorts_path,
            output_path=output_path,
            report_path=report_path,
        )
    )

    assert result == 1
    assert resorts_path.read_text(encoding="utf-8") == resorts_content
    assert "aliased paths: resorts_path and output_path" in capsys.readouterr().err


def test_report_publish_failure_leaves_catalog_unchanged_and_cleans_temps(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output_path = tmp_path / "catalog.json"
    output_path.write_text("old-catalog\n", encoding="utf-8")
    report_path = tmp_path / "report-target"
    report_path.mkdir()

    result = main(_migration_cli_args(output_path=output_path, report_path=report_path))

    assert result == 1
    assert output_path.read_text(encoding="utf-8") == "old-catalog\n"
    assert not list(tmp_path.glob(".*.tmp"))
    assert "[catalog-migration-write-failed]" in capsys.readouterr().err


def test_report_staging_failure_leaves_catalog_unchanged_and_cleans_temps(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output_path = tmp_path / "catalog.json"
    output_path.write_text("old-catalog\n", encoding="utf-8")
    invalid_parent = tmp_path / "not-a-directory"
    invalid_parent.write_text("file\n", encoding="utf-8")
    report_path = invalid_parent / "report.md"

    result = main(_migration_cli_args(output_path=output_path, report_path=report_path))

    assert result == 1
    assert output_path.read_text(encoding="utf-8") == "old-catalog\n"
    assert not list(tmp_path.glob(".*.tmp"))
    assert "[catalog-migration-write-failed]" in capsys.readouterr().err


def test_output_staging_failure_does_not_publish_staged_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    invalid_parent = tmp_path / "not-a-directory"
    invalid_parent.write_text("file\n", encoding="utf-8")
    output_path = invalid_parent / "catalog.json"
    report_path = tmp_path / "report.md"
    report_path.write_text("old-report\n", encoding="utf-8")

    result = main(_migration_cli_args(output_path=output_path, report_path=report_path))

    assert result == 1
    assert report_path.read_text(encoding="utf-8") == "old-report\n"
    assert not list(tmp_path.glob(".*.tmp"))
    assert "[catalog-migration-write-failed]" in capsys.readouterr().err


def test_successful_publication_preserves_or_sets_readable_file_modes(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "catalog.json"
    output_path.write_text("old-catalog\n", encoding="utf-8")
    output_path.chmod(0o640)
    report_path = tmp_path / "report.md"

    result = main(_migration_cli_args(output_path=output_path, report_path=report_path))

    assert result == 0
    assert stat.S_IMODE(output_path.stat().st_mode) == 0o640
    assert stat.S_IMODE(report_path.stat().st_mode) == 0o644


def test_conversion_preserves_domains_and_routes_both_terrain_groups(
    migration: CatalogMigration,
) -> None:
    legacy_domains = load_terrain_domains_from_path(LEGACY_TERRAIN_DOMAINS_PATH)
    domains_by_id = {
        domain.terrain_domain_id: domain
        for domain in migration.snapshot.terrain_domains
    }

    assert set(domains_by_id) == {
        "tignes-val-disere",
        "matterhorn-ski-paradise",
        "campiglio-dolomiti-di-brenta",
        "kitzsteinhorn-maiskogel",
    }
    for legacy in legacy_domains:
        converted = domains_by_id[legacy.terrain_domain_id]
        assert converted.ski_area_ids == tuple(
            ref.ski_area_id for ref in legacy.ski_area_refs
        )
        assert converted.source_urls == tuple(legacy.source_urls)
        for field in (
            "name",
            "metric_scope",
            "total_piste_km",
            "total_lift_count",
            "base_elevation_m",
            "summit_elevation_m",
            "piste_km_by_difficulty",
            "season_windows",
        ):
            assert _json_key(getattr(converted, field)) == _json_key(
                getattr(legacy, field)
            )

    kitz = domains_by_id["kitzsteinhorn-maiskogel"]
    assert kitz.ski_area_ids == ("kitzsteinhorn", "maiskogel")
    assert kitz.total_piste_km == 62.5
    assert kitz.total_lift_count == 24
    assert kitz.piste_km_by_difficulty is not None
    assert kitz.piste_km_by_difficulty.model_dump() == {
        "beginner": 30.5,
        "intermediate": 23.0,
        "advanced": 9.0,
    }
    assert kitz.source_urls == (
        "https://www.kitzsteinhorn.at/en/service/backstage/press/"
        "winter-2025-26-pr15634",
        "https://www.skiresort.info/ski-resort/"
        "kitzsteinhorn-maiskogel-kaprun/slope-offering/",
    )
    assert migration.audit.terrain_group_routes == (
        ("chamonix-le-pass-terrain", "pass:chamonix-le-pass"),
        ("kitzsteinhorn-maiskogel", "terrain_domain"),
    )


def test_chamonix_aggregate_becomes_pass_accessible_terrain(
    migration: CatalogMigration,
) -> None:
    passes = {
        product.lift_pass_product_id: product
        for product in migration.snapshot.lift_pass_products
    }
    aggregate = passes["chamonix-le-pass"].pass_accessible_terrain

    assert aggregate is not None
    assert aggregate.metric_scope == "pass_accessible"
    assert aggregate.total_piste_km == 110
    assert aggregate.total_lift_count == 43
    assert aggregate.source_urls == (
        "https://domaineschamonix.montblancnaturalresort.com/en/ticketing/"
        "chamonix-lepass",
    )


def test_shared_passes_merge_availability_defaults_coverage_and_prices(
    migration: CatalogMigration,
) -> None:
    passes = {
        product.lift_pass_product_id: product
        for product in migration.snapshot.lift_pass_products
    }
    tignes = passes["tignes-val-disere-ski-pass"]
    campiglio = passes["campiglio-skiarea-pass"]

    assert tignes.available_from_stay_destination_ids == ("tignes", "val-disere")
    assert tignes.default_for_stay_destination_ids == ("tignes", "val-disere")
    assert tignes.valid_ski_area_ids == (
        "tignes-ski-area",
        "val-disere-ski-area",
    )
    assert tignes.terrain_domain_ids == ("tignes-val-disere",)
    assert len(tignes.prices) == 3

    assert campiglio.available_from_stay_destination_ids == (
        "folgarida-marilleva",
        "madonna-di-campiglio",
        "pinzolo",
    )
    assert campiglio.default_for_stay_destination_ids == (
        "folgarida-marilleva",
        "madonna-di-campiglio",
        "pinzolo",
    )
    assert campiglio.valid_ski_area_ids == (
        "folgarida-marilleva-ski-area",
        "madonna-di-campiglio-ski-area",
        "pinzolo-ski-area",
    )
    assert campiglio.terrain_domain_ids == ("campiglio-dolomiti-di-brenta",)
    assert len(campiglio.prices) == 3
    assert migration.audit.merged_pass_source_ids == {
        "campiglio-skiarea-pass": (
            "folgarida-marilleva:folgarida-marilleva-campiglio-skiarea-pass",
            "madonna-di-campiglio:madonna-di-campiglio-campiglio-skiarea-pass",
            "pinzolo:pinzolo-campiglio-skiarea-pass",
        ),
        "tignes-val-disere-ski-pass": (
            "tignes:tignes-val-disere-ski-pass",
            "val-disere:tignes-val-disere-ski-pass",
        ),
    }


def test_rental_ids_are_slugged_unique_and_deterministic(
    migration: CatalogMigration,
) -> None:
    rental_ids = [
        rental.rental_display_fact_id
        for rental in migration.snapshot.rental_display_facts
    ]
    rerun = build_catalog_migration(
        load_resorts_from_path(LEGACY_RESORTS_PATH),
        load_terrain_domains_from_path(LEGACY_TERRAIN_DOMAINS_PATH),
        load_migration_overrides(OVERRIDES_PATH),
    )

    assert len(rental_ids) == len(set(rental_ids)) == 32
    assert "chamonix-mont-blanc-cham-sport" in rental_ids
    assert all(
        rental.rental_display_fact_id.startswith(f"{rental.stay_destination_id}-")
        for rental in migration.snapshot.rental_display_facts
    )
    assert serialize_catalog(migration.snapshot) == serialize_catalog(rerun.snapshot)
    assert migration.report_markdown == rerun.report_markdown


def test_rental_ids_are_stable_under_reordering_and_cross_destination_growth(
    migration: CatalogMigration,
) -> None:
    domains = load_terrain_domains_from_path(LEGACY_TERRAIN_DOMAINS_PATH)
    overrides = load_migration_overrides(OVERRIDES_PATH)
    reordered = load_resorts_from_path(LEGACY_RESORTS_PATH)
    for destination in reordered:
        destination.rentals.reverse()
    reordered.reverse()
    reordered_migration = build_catalog_migration(reordered, domains, overrides)

    grown = load_resorts_from_path(LEGACY_RESORTS_PATH)
    chamonix_rental = grown[0].rentals[0]
    tignes = next(item for item in grown if item.resort_id == "tignes")
    tignes.rentals.append(chamonix_rental.model_copy(deep=True))
    grown_migration = build_catalog_migration(grown, domains, overrides)

    original_ids = {
        (rental.stay_destination_id, rental.name): rental.rental_display_fact_id
        for rental in migration.snapshot.rental_display_facts
    }
    reordered_ids = {
        (rental.stay_destination_id, rental.name): rental.rental_display_fact_id
        for rental in reordered_migration.snapshot.rental_display_facts
    }
    grown_ids = {
        (rental.stay_destination_id, rental.name): rental.rental_display_fact_id
        for rental in grown_migration.snapshot.rental_display_facts
    }

    assert reordered_ids == original_ids
    assert all(grown_ids[key] == rental_id for key, rental_id in original_ids.items())
    assert grown_ids[("tignes", "Cham'Sport")] == "tignes-cham-sport"


def test_same_destination_normalized_rental_name_collision_is_rejected() -> None:
    legacy = load_resorts_from_path(LEGACY_RESORTS_PATH)
    domains = load_terrain_domains_from_path(LEGACY_TERRAIN_DOMAINS_PATH)
    overrides = load_migration_overrides(OVERRIDES_PATH)
    chamonix = next(item for item in legacy if item.resort_id == "chamonix-mont-blanc")
    chamonix.rentals.append(
        chamonix.rentals[0].model_copy(update={"name": "Cham Sport"}, deep=True)
    )

    with pytest.raises(
        ValueError,
        match="rental display ID collision for chamonix-mont-blanc-cham-sport",
    ):
        build_catalog_migration(legacy, domains, overrides)


def test_report_contains_required_review_sections_and_zero_blockers(
    migration: CatalogMigration,
) -> None:
    report = migration.report_markdown
    required_sections = (
        "## Before/After Entity Counts",
        "## Stable ID Changes",
        "## Trip-Market Memberships",
        "## Generated Access Edges",
        "## Merged Passes",
        "## Terrain Group Routing",
        "## Rental ID Mapping",
        "## Blocked/Unsourced Relationships",
        "## Dropped Fields",
        "## Estimated/Derived Decisions",
    )

    assert all(section in report for section in required_sections)
    assert "Blocked relationships: **0**" in report
    assert "Stay-destination ID changes: **0**" in report
    assert "Stay-base ID changes: **0**" in report
    assert "Ski-area ID changes: **0**" in report
    assert "Existing terrain-domain ID changes: **0**" in report
    assert "Lift-pass ID merges: **2**" in report
    assert (
        f"All {migration.audit.after_counts['stay_destinations']} stay-destination IDs"
    ) in report
    assert f"All {migration.audit.after_counts['stay_bases']} loaded stay-base IDs" in (
        report
    )
    assert (
        f"All {migration.audit.after_counts['ski_areas']} weather-owning ski-area IDs"
        in report
    )
    assert (
        f"{migration.audit.after_counts['rental_display_facts']} deterministic IDs"
        in report
    )
    assert "destination.base_elevation_m" in report
    assert "destination.summit_elevation_m" in report
    assert "destination.season_start_month" in report
    assert "destination.season_end_month" in report
    assert "destination.season_windows" in report
    assert "[https://" in report
    assert "asserted.." not in report
    assert "provider-backed/estimated.." not in report
    assert Counter(report.splitlines())["## Generated Access Edges"] == 1
    assert (
        "| `chamonix-mont-blanc` | `Cham'Sport` | `chamonix-mont-blanc-cham-sport` |"
    ) in report
    assert len(migration.audit.rental_id_mappings) == 32


def test_generated_catalog_matches_converter_output_and_validates(
    migration: CatalogMigration,
) -> None:
    expected = serialize_catalog(migration.snapshot)

    assert expected.endswith("\n")
    assert CATALOG_PATH.read_text(encoding="utf-8") == expected
    assert load_catalog_from_path(CATALOG_PATH) == migration.snapshot
    assert "terrain_groups" not in json.loads(expected)
