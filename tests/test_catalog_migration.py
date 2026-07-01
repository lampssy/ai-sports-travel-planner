from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from app.data.catalog_loader import load_catalog_from_path
from app.data.catalog_migration import (
    CatalogMigration,
    build_catalog_migration,
    load_migration_overrides,
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
    assert "cham-sport" in rental_ids
    assert serialize_catalog(migration.snapshot) == serialize_catalog(rerun.snapshot)
    assert migration.report_markdown == rerun.report_markdown


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
    assert "destination.base_elevation_m" in report
    assert "destination.summit_elevation_m" in report
    assert "destination.season_start_month" in report
    assert "destination.season_end_month" in report
    assert "destination.season_windows" in report
    assert "[https://" in report
    assert "asserted.." not in report
    assert "provider-backed/estimated.." not in report
    assert Counter(report.splitlines())["## Generated Access Edges"] == 1


def test_generated_catalog_matches_converter_output_and_validates(
    migration: CatalogMigration,
) -> None:
    expected = serialize_catalog(migration.snapshot)

    assert expected.endswith("\n")
    assert CATALOG_PATH.read_text(encoding="utf-8") == expected
    assert load_catalog_from_path(CATALOG_PATH) == migration.snapshot
    assert "terrain_groups" not in json.loads(expected)
