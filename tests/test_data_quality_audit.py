from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.data.audit_data_quality import (
    ArchiveCoverageRow,
    CatalogCompletenessSummary,
    ClimatologyCoverageRow,
    DataQualityAuditResult,
    DataQualityEntityCount,
    DataQualityMetricSnapshot,
    MetricGauge,
    run_data_quality_audit,
    summarize_archive_coverage,
    summarize_catalog_field_groups,
    summarize_climatology_coverage,
    summarize_resort_fit_factors,
    summarize_trust_manifest,
    write_audit_artifacts,
)
from app.data.repositories import RawWeatherHistoryRepository, SnowClimatologyRepository
from app.domain.catalog import CatalogSnapshot
from app.domain.models import (
    RawWeatherObservation,
    SnowClimatologyDaily,
)
from app.observability.jobs import record_data_quality_audit_result
from app.observability.metrics import (
    InMemoryMetricsRecorder,
    reset_metrics_recorder_for_tests,
    set_metrics_recorder_for_tests,
)
from tests.test_catalog_models import example_rental, minimal_catalog_payload

AUDIT_WORKFLOW_PATH = Path(".github/workflows/audit-data-quality.yml")
ALLOWED_AUDIT_METRIC_LABELS = {
    "baseline_period",
    "domain",
    "elevation_band",
    "entity_id",
    "entity_type",
    "factor_id",
    "field_group",
    "ski_area_id",
    "source_model",
    "scope",
    "status",
    "trust_status",
    "trust_state",
}
DISALLOWED_AUDIT_METRIC_LABELS = {
    "api_key",
    "date",
    "issue",
    "raw_status",
    "resort_id",
    "resort_name",
    "source_ref",
    "source_url",
    "token",
    "url",
}


def test_archive_coverage_summary_counts_statuses_and_missing_days() -> None:
    rows = (
        ArchiveCoverageRow(
            ski_area_id="complete-area",
            resort_name="Complete",
            elevation_band="mid",
            expected_days=10,
            covered_days=10,
            first_observed_on="2024-03-01",
            last_observed_on="2024-03-10",
        ),
        ArchiveCoverageRow(
            ski_area_id="partial-area",
            resort_name="Partial",
            elevation_band="mid",
            expected_days=10,
            covered_days=8,
            first_observed_on="2024-03-01",
            last_observed_on="2024-03-08",
        ),
        ArchiveCoverageRow(
            ski_area_id="missing-area",
            resort_name="Missing",
            elevation_band="mid",
            expected_days=10,
            covered_days=0,
            first_observed_on=None,
            last_observed_on=None,
        ),
    )

    summary = summarize_archive_coverage(rows)

    assert summary.ratio == 0.6
    assert summary.status_counts == {"complete": 1, "partial": 1, "missing": 1}
    assert summary.issue_count == 2
    assert summary.missing_days_by_band == {"mid": 12}


def test_climatology_summary_marks_weak_groups_below_thresholds() -> None:
    rows = (
        ClimatologyCoverageRow(
            ski_area_id="complete-area",
            elevation_band="mid",
            baseline_period="normal_30y",
            source_model="snowcast_empirical_v1",
            expected_rows=366,
            actual_rows=366,
            min_evidence_seasons=9,
            latest_archive_year=2025,
        ),
        ClimatologyCoverageRow(
            ski_area_id="short-row-area",
            elevation_band="mid",
            baseline_period="normal_30y",
            source_model="snowcast_empirical_v1",
            expected_rows=366,
            actual_rows=360,
            min_evidence_seasons=10,
            latest_archive_year=2025,
        ),
        ClimatologyCoverageRow(
            ski_area_id="weak-evidence-area",
            elevation_band="upper",
            baseline_period="recent_15y",
            source_model="snowcast_empirical_v1",
            expected_rows=366,
            actual_rows=366,
            min_evidence_seasons=7,
            latest_archive_year=2025,
        ),
        ClimatologyCoverageRow(
            ski_area_id="missing-area",
            elevation_band="base",
            baseline_period="recent_15y",
            source_model="snowcast_empirical_v1",
            expected_rows=366,
            actual_rows=0,
            min_evidence_seasons=None,
            latest_archive_year=None,
        ),
    )

    summary = summarize_climatology_coverage(rows, minimum_evidence_seasons=8)

    assert summary.ratio == 0.7459
    assert summary.status_counts == {"complete": 1, "weak": 2, "missing": 1}
    assert summary.issue_count == 3
    assert {group["ski_area_id"] for group in summary.weak_coverage_groups} == {
        "short-row-area",
        "weak-evidence-area",
    }


def test_catalog_summary_audits_typed_normalized_entities() -> None:
    summary = summarize_catalog_field_groups(_catalog_snapshot(complete=False))

    assert isinstance(summary, CatalogCompletenessSummary)
    assert summary.field_groups["lift_pass_products.prices"].status_counts == {
        "missing": 1
    }
    assert summary.field_groups["ski_areas.terrain_metrics"].status_counts == {
        "missing": 1
    }
    assert any(
        issue["entity_type"] == "stay_bases"
        and issue["entity_id"] == "example-village"
        and issue["field_group"] == "stay_bases.coordinates"
        for issue in summary.issues
    )


def test_resort_fit_factor_summary_flags_core_factor_readiness() -> None:
    complete = summarize_resort_fit_factors(_catalog_snapshot(complete=True))
    thin = summarize_resort_fit_factors(_catalog_snapshot(complete=False))

    assert complete.status_counts["complete"] == 3
    assert thin.issue_count >= 2
    assert any(
        issue["entity_type"] == "ski_areas"
        and issue["entity_id"] == "example-area"
        and issue["factor_id"] == "terrain_scale"
        for issue in thin.issues
    )


def test_resort_fit_factor_metrics_use_bounded_label_sets() -> None:
    summary = summarize_resort_fit_factors(_catalog_snapshot(complete=False))
    gauges_by_name = _gauges_by_name(summary.metric_snapshot())

    status_gauge = gauges_by_name["snowcast_resort_fit_factor_status"][0]
    gap_gauge = gauges_by_name["snowcast_resort_fit_factor_gap_count"][0]

    assert set(status_gauge.labels) == {"domain", "factor_id", "status"}
    assert status_gauge.labels["domain"] == "resort_fit_factors"
    assert set(gap_gauge.labels) == {
        "entity_type",
        "entity_id",
        "factor_id",
        "scope",
        "trust_state",
    }


def test_trust_manifest_summary_maps_existing_manifest_statuses() -> None:
    manifest = {
        "field_groups": ["destination_identity", "season_window"],
        "destinations": {
            "verified-resort": {
                "field_statuses": {
                    "destination_identity": "verified",
                    "season_window": "verified_with_adjustment",
                },
                "source_refs": ["https://example.com/official"],
            },
            "estimated-resort": {
                "field_statuses": {
                    "destination_identity": "estimated",
                    "season_window": "needs_source",
                },
                "source_refs": [],
            },
            "invalid-resort": {
                "field_statuses": {
                    "destination_identity": "verified",
                    "season_window": "made_up_status",
                },
                "source_refs": ["app/data/catalog.json"],
            },
        },
    }

    summary = summarize_trust_manifest(manifest)

    assert summary.ratio == 0.3333
    assert summary.status_counts == {
        "verified": 2,
        "estimated": 1,
        "missing": 1,
        "invalid": 2,
    }
    assert summary.issue_count == 4


def test_trust_manifest_summary_maps_normalized_canonical_manifest() -> None:
    manifest = json.loads(
        Path("app/data/resort_trust_manifest.json").read_text(encoding="utf-8")
    )

    summary = summarize_trust_manifest(manifest)

    expected_rows = sum(
        len(entries) * len(manifest["field_groups"][entity_type])
        for entity_type, entries in manifest["entities"].items()
    )
    assert sum(summary.status_counts.values()) == expected_rows
    assert summary.ratio > 0
    assert summary.status_counts.get("invalid", 0) == 0
    assert "ski_areas.terrain_metrics" in summary.field_group_status_counts


def test_metric_snapshot_labels_avoid_private_or_high_cardinality_values() -> None:
    result = DataQualityAuditResult(
        generated_at="2026-06-18T00:00:00+00:00",
        archive_window={"start_date": "2024-03-01", "end_date": "2024-03-10"},
        summary_by_domain={
            "historical_archive": {"ratio": 0.6, "status_counts": {"partial": 1}},
        },
        historical_archive_issues=[
            {
                "ski_area_id": "tignes-ski-area",
                "resort_name": "Tignes",
                "elevation_band": "mid",
                "missing_days": 2,
            }
        ],
        snow_climatology_issues=[],
        catalog_field_issues=[],
        source_trust_issues=[],
        warnings=[],
        metric_snapshot=DataQualityMetricSnapshot(
            completeness_ratios={"historical_archive": 0.6},
            entity_counts=(
                DataQualityEntityCount(
                    domain="historical_archive",
                    status="partial",
                    count=1,
                ),
            ),
            gauges=(
                MetricGauge(
                    name="snowcast_data_missing_days",
                    value=12,
                    labels={
                        "domain": "historical_archive",
                        "elevation_band": "mid",
                    },
                ),
            ),
        ),
    )

    assert result.historical_archive_issues[0]["ski_area_id"] == "tignes-ski-area"
    assert result.as_dict()["historical_archive_issues"][0]["ski_area_id"]

    for labels in result.metric_snapshot.label_sets:
        assert set(labels).issubset(ALLOWED_AUDIT_METRIC_LABELS)
        assert DISALLOWED_AUDIT_METRIC_LABELS.isdisjoint(labels)
        assert all("http" not in str(value).lower() for value in labels.values())


def test_audit_result_preserves_metric_snapshot_positional_slot() -> None:
    snapshot = DataQualityMetricSnapshot(
        completeness_ratios={"historical_archive": 0.6}
    )

    result = DataQualityAuditResult(
        "2026-06-18T00:00:00+00:00",
        {"start_date": "2024-03-01", "end_date": "2024-03-10"},
        {
            "historical_archive": {
                "ratio": 0.6,
                "status_counts": {"partial": 1},
            }
        },
        [],
        [],
        [],
        [],
        [],
        snapshot,
    )

    assert result.metric_snapshot is snapshot
    assert result.resort_fit_factor_issues == []


def test_run_data_quality_audit_exposes_bounded_drilldown_metrics(tmp_path) -> None:
    RawWeatherHistoryRepository().upsert_observations(
        (_raw_weather_observation(observed_on="2024-03-01"),)
    )

    result = run_data_quality_audit(
        archive_start_date=date(2024, 3, 1),
        archive_end_date=date(2024, 3, 2),
        output_dir=tmp_path,
    )
    gauges_by_name = _gauges_by_name(result.metric_snapshot)

    assert "snowcast_archive_coverage_ratio" in gauges_by_name
    assert "snowcast_archive_missing_days_by_ski_area" in gauges_by_name
    assert "snowcast_archive_last_observed_timestamp_seconds" in gauges_by_name
    assert "snowcast_climatology_coverage_ratio" in gauges_by_name
    assert "snowcast_climatology_missing_rows_by_ski_area" in gauges_by_name
    assert "snowcast_climatology_gap_count" in gauges_by_name
    assert "snowcast_catalog_gap_count" in gauges_by_name
    assert "snowcast_trust_gap_count" in gauges_by_name
    assert "snowcast_resort_fit_factor_status" in gauges_by_name
    assert "snowcast_resort_fit_factor_gap_count" in gauges_by_name
    assert "snowcast_data_audit_generated_timestamp_seconds" in gauges_by_name
    assert "snowcast_data_audit_archive_end_timestamp_seconds" in gauges_by_name

    for labels in result.metric_snapshot.label_sets:
        assert set(labels).issubset(ALLOWED_AUDIT_METRIC_LABELS)
        assert DISALLOWED_AUDIT_METRIC_LABELS.isdisjoint(labels)
        assert all("http" not in str(value).lower() for value in labels.values())

    archive_labels = gauges_by_name["snowcast_archive_missing_days_by_ski_area"][
        0
    ].labels
    assert {"ski_area_id", "elevation_band"} <= set(archive_labels)
    catalog_labels = gauges_by_name["snowcast_catalog_gap_count"][0].labels
    assert {"entity_type", "entity_id", "field_group", "status"} <= set(catalog_labels)
    trust_labels = gauges_by_name["snowcast_trust_gap_count"][0].labels
    assert {"entity_type", "entity_id", "field_group", "trust_status"} <= set(
        trust_labels
    )
    factor_status_labels = gauges_by_name["snowcast_resort_fit_factor_status"][0].labels
    assert set(factor_status_labels) == {"domain", "factor_id", "status"}
    factor_gap_labels = gauges_by_name["snowcast_resort_fit_factor_gap_count"][0].labels
    assert set(factor_gap_labels) == {
        "entity_type",
        "entity_id",
        "factor_id",
        "scope",
        "trust_state",
    }


def test_write_audit_artifacts_creates_json_and_markdown(tmp_path) -> None:
    result = DataQualityAuditResult(
        generated_at="2026-06-18T00:00:00+00:00",
        archive_window={"start_date": "1991-01-01", "end_date": "2026-03-01"},
        summary_by_domain={
            "historical_archive": {
                "ratio": 0.98,
                "issue_count": 1,
                "status_counts": {"partial": 1},
            },
        },
        historical_archive_issues=[
            {
                "ski_area_id": "tignes-ski-area",
                "elevation_band": "mid",
                "missing_days": 3,
                "status": "partial",
            },
        ],
        snow_climatology_issues=[],
        catalog_field_issues=[],
        source_trust_issues=[],
        warnings=[],
    )

    write_audit_artifacts(result, output_dir=tmp_path)

    summary = (tmp_path / "data-quality-summary.json").read_text(encoding="utf-8")
    report = (tmp_path / "data-quality-report.md").read_text(encoding="utf-8")
    assert '"historical_archive"' in summary
    assert "Historical Archive Issues" in report
    assert "tignes-ski-area" in report
    assert "Resort Fit Factor Issues" in report


def test_record_data_quality_audit_result_emits_bounded_metrics() -> None:
    recorder = InMemoryMetricsRecorder()
    set_metrics_recorder_for_tests(recorder)
    snapshot = DataQualityMetricSnapshot(
        completeness_ratios={"historical_archive": 0.98},
        entity_counts=(
            DataQualityEntityCount(
                domain="historical_archive",
                status="partial",
                count=2,
            ),
        ),
        gauges=(
            MetricGauge(
                name="snowcast_data_missing_days",
                value=3,
                labels={"domain": "historical_archive", "elevation_band": "mid"},
            ),
        ),
    )

    try:
        record_data_quality_audit_result(snapshot)
    finally:
        reset_metrics_recorder_for_tests()

    assert recorder.gauges == [
        (
            "snowcast_data_completeness_ratio",
            {"domain": "historical_archive"},
            0.98,
        ),
        (
            "snowcast_data_completeness_entities",
            {"domain": "historical_archive", "status": "partial"},
            2,
        ),
        (
            "snowcast_data_missing_days",
            {"domain": "historical_archive", "elevation_band": "mid"},
            3,
        ),
    ]


def test_catalog_gap_metrics_identify_normalized_entity_owner() -> None:
    summary = summarize_catalog_field_groups(_catalog_snapshot(complete=False))
    gap_gauges = [
        gauge
        for gauge in summary.metric_snapshot().gauges
        if gauge.name == "snowcast_catalog_gap_count"
    ]

    assert gap_gauges
    assert all("entity_type" in gauge.labels for gauge in gap_gauges)
    assert all("entity_id" in gauge.labels for gauge in gap_gauges)
    assert {gauge.labels["entity_type"] for gauge in gap_gauges} >= {
        "ski_areas",
        "stay_bases",
    }


def test_trust_gap_metrics_identify_normalized_entity_owner() -> None:
    summary = summarize_trust_manifest(
        {
            "field_groups": ["destination_identity"],
            "destinations": {
                "thin": {
                    "field_statuses": {"destination_identity": "estimated"},
                    "source_refs": [],
                }
            },
        }
    )
    gap_gauges = [
        gauge
        for gauge in summary.metric_snapshot().gauges
        if gauge.name == "snowcast_trust_gap_count"
    ]

    assert gap_gauges == [
        MetricGauge(
            name="snowcast_trust_gap_count",
            value=1,
            labels={
                "entity_type": "stay_destinations",
                "entity_id": "thin",
                "field_group": "destination_identity",
                "trust_status": "estimated",
            },
        )
    ]


def test_run_data_quality_audit_writes_artifacts_from_seeded_database(tmp_path) -> None:
    result = run_data_quality_audit(
        archive_start_date=date(2024, 3, 1),
        archive_end_date=date(2024, 3, 2),
        output_dir=tmp_path,
    )

    assert result.archive_window == {
        "start_date": "2024-03-01",
        "end_date": "2024-03-02",
    }
    assert set(result.summary_by_domain) == {
        "historical_archive",
        "snow_climatology",
        "catalog_required_fields",
        "catalog_source_trust",
        "resort_fit_factors",
    }
    assert result.metric_snapshot.completeness_ratios.keys() == set(
        result.summary_by_domain
    )
    assert (tmp_path / "data-quality-summary.json").exists()
    assert (tmp_path / "data-quality-report.md").exists()


def test_audit_data_quality_workflow_exports_artifacts_and_otel_env() -> None:
    workflow = AUDIT_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python -m app.data.audit_data_quality" in workflow
    assert "actions/upload-artifact" in workflow
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in workflow
    assert "OTEL_EXPORTER_OTLP_HEADERS" in workflow
    assert "DATABASE_URL" in workflow
    assert "artifacts/data-quality" in workflow


def test_raw_weather_archive_coverage_helper_is_bounded_and_distinct() -> None:
    repository = RawWeatherHistoryRepository()
    repository.upsert_observations(
        (
            _raw_weather_observation(observed_on="2024-03-05"),
            _raw_weather_observation(observed_on="2024-03-05", source="fallback"),
            _raw_weather_observation(observed_on="2024-03-06"),
            _raw_weather_observation(
                observed_on="2024-03-07",
                elevation_band="upper",
                elevation_m=3200,
            ),
        )
    )

    coverage = repository.list_archive_coverage(
        ski_area_ids=("tignes-ski-area", "cervinia-ski-area"),
        elevation_bands=("mid", "upper"),
        start_date=date(2024, 3, 5),
        end_date=date(2024, 3, 6),
    )

    assert coverage[("tignes-ski-area", "mid")].covered_days == 2
    assert coverage[("tignes-ski-area", "mid")].first_observed_on == "2024-03-05"
    assert coverage[("tignes-ski-area", "mid")].last_observed_on == "2024-03-06"
    assert coverage[("tignes-ski-area", "upper")].covered_days == 0
    assert coverage[("cervinia-ski-area", "mid")].covered_days == 0


def test_raw_weather_latest_archive_observed_on_returns_max_archive_date() -> None:
    repository = RawWeatherHistoryRepository()
    repository.upsert_observations(
        (
            _raw_weather_observation(observed_on="2024-03-05"),
            _raw_weather_observation(observed_on="2024-03-06"),
        )
    )

    assert repository.latest_archive_observed_on() == date(2024, 3, 6)


def test_snow_climatology_coverage_helper_filters_by_source_model() -> None:
    repository = SnowClimatologyRepository()
    repository.upsert_daily_rows(
        (
            _snow_climatology_row(day=10, evidence_seasons=12),
            _snow_climatology_row(day=11, evidence_seasons=8),
            _snow_climatology_row(
                day=12,
                evidence_seasons=5,
                source_model="other_model",
            ),
        )
    )

    coverage = repository.list_climatology_coverage(
        ski_area_ids=("tignes-ski-area",),
        elevation_bands=("mid",),
        baseline_periods=("normal_30y", "recent_15y"),
        source_model="snowcast_empirical_v1",
    )

    normal = coverage[("tignes-ski-area", "mid", "normal_30y")]
    recent = coverage[("tignes-ski-area", "mid", "recent_15y")]
    assert normal.row_count == 2
    assert normal.min_evidence_seasons == 8
    assert normal.latest_archive_year == 2025
    assert recent.row_count == 0
    assert recent.min_evidence_seasons is None


def _catalog_snapshot(*, complete: bool) -> CatalogSnapshot:
    payload = minimal_catalog_payload()
    if complete:
        payload["ski_regions"][0]["source_urls"] = [
            "https://example.com/example-valley"
        ]
        payload["stay_destinations"][0]["regional_data_ids"] = {"wikidata_id": "Q1"}
        payload["stay_bases"][0].update(
            {
                "latitude": 45.0,
                "longitude": 6.0,
                "regional_data_ids": {"osm_node_id": "1"},
            }
        )
        payload["ski_areas"][0].update(
            {
                "season_windows": [
                    {
                        "season_label": "2026-2027",
                        "start_date": "2026-12-01",
                        "end_date": "2027-04-15",
                        "status": "planned",
                    }
                ],
                "total_piste_km": 130,
                "total_lift_count": 24,
                "piste_km_by_difficulty": {
                    "beginner": 50,
                    "intermediate": 55,
                    "advanced": 25,
                },
            }
        )
        payload["lift_pass_products"][0]["prices"] = [
            {
                "duration_days": 1,
                "audience": "adult",
                "amount": 65,
                "currency": "EUR",
                "price_kind": "fixed",
                "season_label": "2026-2027",
                "source_url": "https://example.com/lift-passes",
            }
        ]
        payload["rental_display_facts"] = [example_rental()]
    return CatalogSnapshot.model_validate(payload)


def _gauges_by_name(
    snapshot: DataQualityMetricSnapshot,
) -> dict[str, list[MetricGauge]]:
    gauges: dict[str, list[MetricGauge]] = {}
    for gauge in snapshot.gauges:
        gauges.setdefault(gauge.name, []).append(gauge)
    return gauges


def _raw_weather_observation(
    *,
    observed_on: str,
    elevation_band: str = "mid",
    elevation_m: int = 2500,
    source: str = "open-meteo",
) -> RawWeatherObservation:
    return RawWeatherObservation(
        ski_area_id="tignes-ski-area",
        resort_name="Tignes",
        elevation_band=elevation_band,
        elevation_m=elevation_m,
        observed_on=observed_on,
        observed_at=f"{observed_on}T12:00:00+00:00",
        snowfall_cm=8,
        snow_depth_m=1.3,
        temperature_2m_max_c=-3,
        temperature_2m_min_c=-9,
        wind_speed_10m_max_kmh=18,
        wind_gusts_10m_max_kmh=24,
        weather_code=3,
        record_type="archive",
        source=source,
        source_model="best_match",
    )


def _snow_climatology_row(
    *,
    day: int,
    evidence_seasons: int,
    source_model: str = "snowcast_empirical_v1",
) -> SnowClimatologyDaily:
    return SnowClimatologyDaily(
        ski_area_id="tignes-ski-area",
        resort_name="Tignes",
        elevation_band="mid",
        elevation_m=2500,
        month=3,
        day=day,
        baseline_period="normal_30y",
        baseline_start_year=1996,
        baseline_end_year=2025,
        evidence_seasons=evidence_seasons,
        latest_archive_year=2025,
        snow_depth_cm_p25=80.0,
        snow_depth_cm_p50=120.0,
        snow_depth_cm_p75=160.0,
        prob_snow_depth_ge_30cm=0.93,
        prob_snow_depth_ge_50cm=0.87,
        avg_daily_snowfall_cm=6.5,
        prob_rain_risk=0.07,
        prob_freeze_thaw=0.12,
        avg_max_temperature_c=-2.4,
        avg_wind_gust_kmh=28.0,
        avg_snow_confidence_score=0.82,
        avg_conditions_score=0.78,
        source_model=source_model,
        computed_at="2026-06-15T00:00:00+00:00",
    )
