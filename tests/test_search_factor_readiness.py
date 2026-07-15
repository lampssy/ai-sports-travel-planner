from __future__ import annotations

from pathlib import Path

import pytest

from app.data.audit_search_factor_readiness import build_readiness_report
from app.data.catalog_loader import load_catalog
from app.domain.catalog_trust import CatalogTrustManifest
from app.domain.search_factors.static import build_static_factor_registry
from app.domain.search_policy import load_search_policy

pytestmark = pytest.mark.db_free


def _manifest() -> CatalogTrustManifest:
    return CatalogTrustManifest.model_validate_json(
        Path("app/data/resort_trust_manifest.json").read_text(encoding="utf-8")
    )


def test_readiness_audit_covers_the_complete_policy_inventory() -> None:
    policy = load_search_policy()
    report = build_readiness_report(
        snapshot=load_catalog(),
        manifest=_manifest(),
        policy=policy,
        registry=build_static_factor_registry(),
        pass_duration_days=6,
        pass_audience="adult",
        pass_season_label=None,
    )

    assert {row.factor_id for row in report.factors} == {
        factor.factor_id for factor in policy.factors
    }
    by_factor = {row.factor_id: row for row in report.factors}
    assert by_factor["accessible_terrain_scale"].population_count > 0
    assert 0 <= by_factor["accessible_terrain_scale"].resolved_coverage <= 1
    assert by_factor["snow_park"].verified_positive_count > 0
    assert by_factor["local_pace"].distinct_trusted_utilities >= 2
    assert by_factor["trip_window_snow_fit"].evaluator_status == "not_registered"
    assert by_factor["expected_open_piste_ratio"].evaluator_status == "not_required"


def test_readiness_audit_reports_comparable_pass_slice() -> None:
    report = build_readiness_report(
        snapshot=load_catalog(),
        manifest=_manifest(),
        policy=load_search_policy(),
        registry=build_static_factor_registry(),
        pass_duration_days=6,
        pass_audience="adult",
        pass_season_label=None,
    )
    by_factor = {row.factor_id: row for row in report.factors}

    assert by_factor["pass_price_per_day"].comparable_slice_count > 0
    assert (
        by_factor["pass_terrain_value"].comparable_slice_count
        <= by_factor["pass_price_per_day"].comparable_slice_count
    )
