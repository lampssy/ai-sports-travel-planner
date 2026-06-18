from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any, Literal

from app.data.database import resolve_database_url
from app.data.repositories import (
    RawWeatherHistoryRepository,
    ResortRepository,
    SnowClimatologyRepository,
)
from app.domain.models import (
    Destination,
    SnowClimatologyBaselinePeriod,
    WeatherElevationBand,
)
from app.observability.cli import configure_cli_observability
from app.observability.jobs import job_span, record_data_quality_audit_result

DataQualityStatus = Literal[
    "complete", "partial", "missing", "weak", "invalid", "error"
]
TrustCoverageState = Literal["verified", "estimated", "missing", "invalid"]

VALID_DATA_QUALITY_STATUSES: tuple[DataQualityStatus, ...] = (
    "complete",
    "partial",
    "missing",
    "weak",
    "invalid",
    "error",
)
TRUST_COVERAGE_STATES: tuple[TrustCoverageState, ...] = (
    "verified",
    "estimated",
    "missing",
    "invalid",
)
CATALOG_FIELD_GROUPS: tuple[str, ...] = (
    "destination_coordinates",
    "destination_elevation",
    "ski_area_coordinates",
    "ski_area_elevation",
    "season_windows",
    "official_links",
    "regional_ids",
    "stay_bases",
    "rentals",
)
SOURCE_BACKED_TRUST_STATUSES = {"verified", "verified_with_adjustment"}
CATALOG_SELF_REFERENCE = "app/data/resorts.json"
DEFAULT_ARCHIVE_START_DATE = date(1991, 1, 1)
DEFAULT_SOURCE_MODEL = "snowcast_empirical_v1"
DEFAULT_MINIMUM_EVIDENCE_SEASONS = 8
EXPECTED_CLIMATOLOGY_DAILY_ROWS = 366
DEFAULT_OUTPUT_DIR = Path("artifacts/data-quality")
DEFAULT_TRUST_MANIFEST_PATH = Path("app/data/resort_trust_manifest.json")
DEFAULT_ELEVATION_BANDS: tuple[WeatherElevationBand, ...] = ("base", "mid", "upper")
DEFAULT_BASELINE_PERIODS: tuple[SnowClimatologyBaselinePeriod, ...] = (
    "normal_30y",
    "recent_15y",
)


@dataclass(frozen=True)
class MetricGauge:
    name: str
    value: float | int
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DataQualityEntityCount:
    domain: str
    status: str
    count: int

    @property
    def labels(self) -> dict[str, str]:
        return {"domain": self.domain, "status": self.status}


@dataclass(frozen=True)
class DataQualityMetricSnapshot:
    completeness_ratios: dict[str, float] = field(default_factory=dict)
    entity_counts: tuple[DataQualityEntityCount, ...] = ()
    gauges: tuple[MetricGauge, ...] = ()

    @property
    def label_sets(self) -> tuple[dict[str, str], ...]:
        ratio_labels = (
            {"domain": domain} for domain in sorted(self.completeness_ratios)
        )
        entity_labels = (item.labels for item in self.entity_counts)
        gauge_labels = (gauge.labels for gauge in self.gauges)
        return tuple([*ratio_labels, *entity_labels, *gauge_labels])

    @classmethod
    def combine(
        cls,
        *snapshots: DataQualityMetricSnapshot,
    ) -> DataQualityMetricSnapshot:
        completeness_ratios: dict[str, float] = {}
        entity_counts: list[DataQualityEntityCount] = []
        gauges: list[MetricGauge] = []
        for snapshot in snapshots:
            completeness_ratios.update(snapshot.completeness_ratios)
            entity_counts.extend(snapshot.entity_counts)
            gauges.extend(snapshot.gauges)
        return cls(
            completeness_ratios=dict(sorted(completeness_ratios.items())),
            entity_counts=tuple(entity_counts),
            gauges=tuple(gauges),
        )


@dataclass(frozen=True)
class DataQualityAuditResult:
    generated_at: str
    archive_window: dict[str, str | None]
    summary_by_domain: dict[str, dict[str, Any]]
    historical_archive_issues: list[dict[str, Any]]
    snow_climatology_issues: list[dict[str, Any]]
    catalog_field_issues: list[dict[str, Any]]
    source_trust_issues: list[dict[str, Any]]
    warnings: list[str]
    metric_snapshot: DataQualityMetricSnapshot = field(
        default_factory=DataQualityMetricSnapshot
    )

    def as_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class ArchiveCoverageRow:
    ski_area_id: str
    resort_name: str
    elevation_band: WeatherElevationBand | str
    expected_days: int
    covered_days: int
    first_observed_on: str | None
    last_observed_on: str | None

    @property
    def missing_days(self) -> int:
        return max(self.expected_days - self.covered_days, 0)

    @property
    def status(self) -> DataQualityStatus:
        if self.covered_days == self.expected_days:
            return "complete"
        if self.covered_days == 0:
            return "missing"
        return "partial"

    def issue_dict(self) -> dict[str, Any]:
        return {
            "ski_area_id": self.ski_area_id,
            "resort_name": self.resort_name,
            "elevation_band": str(self.elevation_band),
            "expected_days": self.expected_days,
            "covered_days": self.covered_days,
            "missing_days": self.missing_days,
            "first_observed_on": self.first_observed_on,
            "last_observed_on": self.last_observed_on,
            "status": self.status,
        }


@dataclass(frozen=True)
class ArchiveCoverageSummary:
    ratio: float
    status_counts: dict[str, int]
    issue_count: int
    missing_days_by_band: dict[str, int]
    issues: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))

    def metric_snapshot(
        self, *, domain: str = "historical_archive"
    ) -> DataQualityMetricSnapshot:
        gauges = tuple(
            MetricGauge(
                name="snowcast_data_missing_days",
                value=missing_days,
                labels={"domain": domain, "elevation_band": band},
            )
            for band, missing_days in sorted(self.missing_days_by_band.items())
        )
        return _summary_metric_snapshot(
            domain=domain,
            ratio=self.ratio,
            status_counts=self.status_counts,
            gauges=gauges,
        )


@dataclass(frozen=True)
class ClimatologyCoverageRow:
    ski_area_id: str
    elevation_band: WeatherElevationBand | str
    baseline_period: SnowClimatologyBaselinePeriod | str
    source_model: str
    expected_rows: int
    actual_rows: int
    min_evidence_seasons: int | None
    latest_archive_year: int | None

    @property
    def missing_rows(self) -> int:
        return max(self.expected_rows - self.actual_rows, 0)

    def status(self, *, minimum_evidence_seasons: int) -> DataQualityStatus:
        if self.expected_rows <= 0 or self.actual_rows < 0:
            return "invalid"
        if self.actual_rows > self.expected_rows:
            return "invalid"
        if self.actual_rows == 0:
            return "missing"
        if self.actual_rows < self.expected_rows:
            return "weak"
        if self.min_evidence_seasons is None:
            return "weak"
        if self.min_evidence_seasons < minimum_evidence_seasons:
            return "weak"
        return "complete"

    def issue_dict(self, *, minimum_evidence_seasons: int) -> dict[str, Any]:
        return {
            "ski_area_id": self.ski_area_id,
            "elevation_band": str(self.elevation_band),
            "baseline_period": str(self.baseline_period),
            "source_model": self.source_model,
            "expected_rows": self.expected_rows,
            "actual_rows": self.actual_rows,
            "missing_rows": self.missing_rows,
            "min_evidence_seasons": self.min_evidence_seasons,
            "latest_archive_year": self.latest_archive_year,
            "minimum_evidence_seasons": minimum_evidence_seasons,
            "status": self.status(minimum_evidence_seasons=minimum_evidence_seasons),
        }


@dataclass(frozen=True)
class ClimatologyCoverageSummary:
    ratio: float
    status_counts: dict[str, int]
    issue_count: int
    weak_coverage_groups: list[dict[str, Any]]
    issues: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))

    def metric_snapshot(
        self,
        *,
        domain: str = "snow_climatology",
    ) -> DataQualityMetricSnapshot:
        weak_counts: dict[tuple[str, str], int] = defaultdict(int)
        for group in self.weak_coverage_groups:
            source_model = str(group["source_model"])
            baseline_period = str(group["baseline_period"])
            weak_counts[(source_model, baseline_period)] += 1

        gauges = tuple(
            MetricGauge(
                name="snowcast_climatology_weak_coverage_groups",
                value=count,
                labels={
                    "source_model": source_model,
                    "baseline_period": baseline_period,
                },
            )
            for (source_model, baseline_period), count in sorted(weak_counts.items())
        )
        return _summary_metric_snapshot(
            domain=domain,
            ratio=self.ratio,
            status_counts=self.status_counts,
            gauges=gauges,
        )


@dataclass(frozen=True)
class CatalogFieldGroupSummary:
    field_group: str
    ratio: float
    total_count: int
    status_counts: dict[str, int]

    @property
    def complete_count(self) -> int:
        return self.status_counts.get("complete", 0)


@dataclass(frozen=True)
class CatalogCompletenessSummary:
    ratio: float
    status_counts: dict[str, int]
    field_groups: dict[str, CatalogFieldGroupSummary]
    issue_count: int
    issues: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))

    def metric_snapshot(
        self,
        *,
        domain: str = "catalog_required_fields",
    ) -> DataQualityMetricSnapshot:
        gauges = []
        for field_group, group_summary in sorted(self.field_groups.items()):
            for status, count in group_summary.status_counts.items():
                gauges.append(
                    MetricGauge(
                        name="snowcast_catalog_field_groups",
                        value=count,
                        labels={"field_group": field_group, "status": status},
                    )
                )
        gap_counts: Counter[tuple[str, str, str]] = Counter()
        for issue in self.issues:
            resort_id = issue.get("resort_id")
            field_group = issue.get("field_group")
            status = issue.get("status")
            if not resort_id or not field_group or not status:
                continue
            gap_counts[(str(resort_id), str(field_group), str(status))] += 1
        for (resort_id, field_group, status), count in sorted(gap_counts.items()):
            gauges.append(
                MetricGauge(
                    name="snowcast_catalog_gap_count",
                    value=count,
                    labels={
                        "resort_id": resort_id,
                        "field_group": field_group,
                        "status": status,
                    },
                )
            )
        return _summary_metric_snapshot(
            domain=domain,
            ratio=self.ratio,
            status_counts=self.status_counts,
            gauges=tuple(gauges),
        )


@dataclass(frozen=True)
class TrustCoverageRow:
    resort_id: str
    field_group: str
    trust_status: TrustCoverageState
    raw_status: str | None
    source_ref_count: int

    def issue_dict(self) -> dict[str, Any]:
        return {
            "resort_id": self.resort_id,
            "field_group": self.field_group,
            "trust_status": self.trust_status,
            "raw_status": self.raw_status,
            "source_ref_count": self.source_ref_count,
        }


@dataclass(frozen=True)
class TrustCoverageSummary:
    ratio: float
    status_counts: dict[str, int]
    field_group_status_counts: dict[str, dict[str, int]]
    issue_count: int
    issues: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))

    def metric_snapshot(
        self,
        *,
        domain: str = "catalog_source_trust",
    ) -> DataQualityMetricSnapshot:
        gauges = []
        for field_group, status_counts in sorted(
            self.field_group_status_counts.items()
        ):
            for trust_status, count in status_counts.items():
                gauges.append(
                    MetricGauge(
                        name="snowcast_catalog_trust_status",
                        value=count,
                        labels={
                            "field_group": field_group,
                            "trust_status": trust_status,
                        },
                    )
                )
        gap_counts: Counter[tuple[str, str, str]] = Counter()
        for issue in self.issues:
            resort_id = issue.get("resort_id")
            field_group = issue.get("field_group")
            trust_status = issue.get("trust_status")
            if not resort_id or not field_group or not trust_status:
                continue
            gap_counts[(str(resort_id), str(field_group), str(trust_status))] += 1
        for (resort_id, field_group, trust_status), count in sorted(gap_counts.items()):
            gauges.append(
                MetricGauge(
                    name="snowcast_trust_gap_count",
                    value=count,
                    labels={
                        "resort_id": resort_id,
                        "field_group": field_group,
                        "trust_status": trust_status,
                    },
                )
            )
        return DataQualityMetricSnapshot(
            completeness_ratios={domain: self.ratio},
            gauges=tuple(gauges),
        )


def summarize_archive_coverage(
    rows: tuple[ArchiveCoverageRow, ...],
) -> ArchiveCoverageSummary:
    status_counts = Counter(row.status for row in rows)
    missing_days_by_band: dict[str, int] = defaultdict(int)
    issues: list[dict[str, Any]] = []
    for row in rows:
        if row.missing_days:
            missing_days_by_band[str(row.elevation_band)] += row.missing_days
        if row.status != "complete":
            issues.append(row.issue_dict())

    covered_days = sum(min(max(row.covered_days, 0), row.expected_days) for row in rows)
    expected_days = sum(max(row.expected_days, 0) for row in rows)
    return ArchiveCoverageSummary(
        ratio=_ratio(covered_days, expected_days),
        status_counts=_ordered_counts(
            status_counts, ("complete", "partial", "missing", "invalid", "error")
        ),
        issue_count=len(issues),
        missing_days_by_band=dict(sorted(missing_days_by_band.items())),
        issues=issues,
    )


def summarize_climatology_coverage(
    rows: tuple[ClimatologyCoverageRow, ...],
    *,
    minimum_evidence_seasons: int = 8,
) -> ClimatologyCoverageSummary:
    status_counts: Counter[str] = Counter()
    weak_coverage_groups: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    actual_rows = 0
    expected_rows = 0

    for row in rows:
        status = row.status(minimum_evidence_seasons=minimum_evidence_seasons)
        status_counts[status] += 1
        expected_rows += max(row.expected_rows, 0)
        actual_rows += min(max(row.actual_rows, 0), max(row.expected_rows, 0))
        if status == "weak":
            weak_coverage_groups.append(
                row.issue_dict(minimum_evidence_seasons=minimum_evidence_seasons)
            )
        if status != "complete":
            issues.append(
                row.issue_dict(minimum_evidence_seasons=minimum_evidence_seasons)
            )

    return ClimatologyCoverageSummary(
        ratio=_ratio(actual_rows, expected_rows),
        status_counts=_ordered_counts(
            status_counts, ("complete", "weak", "missing", "invalid", "error")
        ),
        issue_count=len(issues),
        weak_coverage_groups=weak_coverage_groups,
        issues=issues,
    )


def summarize_catalog_field_groups(
    resorts: tuple[Destination, ...],
) -> CatalogCompletenessSummary:
    rows: list[dict[str, Any]] = []
    for resort in resorts:
        _add_catalog_row(
            rows,
            resort_id=resort.resort_id,
            entity_type="destination",
            entity_id=resort.resort_id,
            field_group="destination_coordinates",
            status=_coordinate_status(resort.latitude, resort.longitude),
        )
        _add_catalog_row(
            rows,
            resort_id=resort.resort_id,
            entity_type="destination",
            entity_id=resort.resort_id,
            field_group="destination_elevation",
            status=_elevation_status(
                resort.base_elevation_m, resort.summit_elevation_m
            ),
        )
        _add_catalog_row(
            rows,
            resort_id=resort.resort_id,
            entity_type="destination",
            entity_id=resort.resort_id,
            field_group="season_windows",
            status="complete"
            if resort.season_windows
            or any(ski_area.season_windows for ski_area in resort.ski_areas)
            else "missing",
            issue="missing_exact_season_windows",
        )
        _add_catalog_row(
            rows,
            resort_id=resort.resort_id,
            entity_type="destination",
            entity_id=resort.resort_id,
            field_group="official_links",
            status="complete"
            if any(price.source_url for price in resort.lift_pass_prices)
            else "missing",
            issue="missing_source_url",
        )
        _add_catalog_row(
            rows,
            resort_id=resort.resort_id,
            entity_type="destination",
            entity_id=resort.resort_id,
            field_group="stay_bases",
            status="complete" if resort.stay_bases else "missing",
            issue="missing_stay_bases",
        )
        _add_catalog_row(
            rows,
            resort_id=resort.resort_id,
            entity_type="destination",
            entity_id=resort.resort_id,
            field_group="rentals",
            status="complete" if resort.rentals else "missing",
            issue="missing_rentals",
        )

        if resort.ski_areas:
            for ski_area in resort.ski_areas:
                _add_catalog_row(
                    rows,
                    resort_id=resort.resort_id,
                    entity_type="ski_area",
                    entity_id=ski_area.ski_area_id,
                    field_group="ski_area_coordinates",
                    status=_coordinate_status(ski_area.latitude, ski_area.longitude),
                )
                _add_catalog_row(
                    rows,
                    resort_id=resort.resort_id,
                    entity_type="ski_area",
                    entity_id=ski_area.ski_area_id,
                    field_group="ski_area_elevation",
                    status=_elevation_status(
                        ski_area.base_elevation_m, ski_area.summit_elevation_m
                    ),
                )
        else:
            _add_catalog_row(
                rows,
                resort_id=resort.resort_id,
                entity_type="destination",
                entity_id=resort.resort_id,
                field_group="ski_area_coordinates",
                status="missing",
                issue="missing_ski_areas",
            )
            _add_catalog_row(
                rows,
                resort_id=resort.resort_id,
                entity_type="destination",
                entity_id=resort.resort_id,
                field_group="ski_area_elevation",
                status="missing",
                issue="missing_ski_areas",
            )

        if resort.stay_bases:
            for stay_base in resort.stay_bases:
                _add_catalog_row(
                    rows,
                    resort_id=resort.resort_id,
                    entity_type="stay_base",
                    entity_id=stay_base.stay_base_id,
                    field_group="regional_ids",
                    status="complete" if stay_base.regional_data_ids else "missing",
                    issue="missing_regional_ids",
                )
        else:
            _add_catalog_row(
                rows,
                resort_id=resort.resort_id,
                entity_type="destination",
                entity_id=resort.resort_id,
                field_group="regional_ids",
                status="missing",
                issue="missing_stay_bases",
            )

    field_groups: dict[str, CatalogFieldGroupSummary] = {}
    overall_counts: Counter[str] = Counter()
    complete_rows = 0
    issues: list[dict[str, Any]] = []
    for field_group in CATALOG_FIELD_GROUPS:
        group_rows = [row for row in rows if row["field_group"] == field_group]
        group_counts = Counter(str(row["status"]) for row in group_rows)
        field_groups[field_group] = CatalogFieldGroupSummary(
            field_group=field_group,
            ratio=_ratio(group_counts.get("complete", 0), len(group_rows)),
            total_count=len(group_rows),
            status_counts=_ordered_counts(
                group_counts, ("complete", "missing", "invalid", "error")
            ),
        )
        overall_counts.update(group_counts)
        complete_rows += group_counts.get("complete", 0)
        issues.extend(row for row in group_rows if row["status"] != "complete")

    return CatalogCompletenessSummary(
        ratio=_ratio(complete_rows, len(rows)),
        status_counts=_ordered_counts(
            overall_counts, ("complete", "missing", "invalid", "error")
        ),
        field_groups=field_groups,
        issue_count=len(issues),
        issues=issues,
    )


def summarize_trust_manifest(manifest: Mapping[str, Any]) -> TrustCoverageSummary:
    field_groups = _manifest_field_groups(manifest)
    destinations = manifest.get("destinations")
    if not isinstance(destinations, Mapping):
        return TrustCoverageSummary(
            ratio=0.0,
            status_counts={"invalid": 1},
            field_group_status_counts={},
            issue_count=1,
            issues=[
                {
                    "resort_id": None,
                    "field_group": None,
                    "trust_status": "invalid",
                    "raw_status": None,
                    "source_ref_count": 0,
                    "issue": "missing_destinations_object",
                }
            ],
        )

    rows: list[TrustCoverageRow] = []
    for resort_id, entry in sorted(destinations.items()):
        if not isinstance(entry, Mapping):
            for field_group in field_groups:
                rows.append(
                    TrustCoverageRow(
                        resort_id=str(resort_id),
                        field_group=field_group,
                        trust_status="invalid",
                        raw_status=None,
                        source_ref_count=0,
                    )
                )
            continue

        raw_field_statuses = entry.get("field_statuses")
        field_statuses = (
            raw_field_statuses if isinstance(raw_field_statuses, Mapping) else {}
        )
        source_refs = _source_refs(entry.get("source_refs"))
        has_external_source = bool(set(source_refs) - {CATALOG_SELF_REFERENCE})
        for field_group in field_groups:
            raw_status = field_statuses.get(field_group)
            rows.append(
                TrustCoverageRow(
                    resort_id=str(resort_id),
                    field_group=field_group,
                    trust_status=_trust_coverage_state(
                        raw_status=raw_status,
                        has_external_source=has_external_source,
                    ),
                    raw_status=str(raw_status) if raw_status is not None else None,
                    source_ref_count=len(source_refs),
                )
            )

    status_counts = Counter(row.trust_status for row in rows)
    field_group_status_counts: dict[str, dict[str, int]] = {}
    for field_group in field_groups:
        group_counts = Counter(
            row.trust_status for row in rows if row.field_group == field_group
        )
        field_group_status_counts[field_group] = _ordered_counts(
            group_counts, TRUST_COVERAGE_STATES
        )
    issues = [row.issue_dict() for row in rows if row.trust_status != "verified"]
    return TrustCoverageSummary(
        ratio=_ratio(status_counts.get("verified", 0), len(rows)),
        status_counts=_ordered_counts(status_counts, TRUST_COVERAGE_STATES),
        field_group_status_counts=field_group_status_counts,
        issue_count=len(issues),
        issues=issues,
    )


def run_data_quality_audit(
    *,
    database_url: str | None = None,
    archive_start_date: date = DEFAULT_ARCHIVE_START_DATE,
    archive_end_date: date | None = None,
    source_model: str = DEFAULT_SOURCE_MODEL,
    minimum_evidence_seasons: int = DEFAULT_MINIMUM_EVIDENCE_SEASONS,
    output_dir: Path | None = None,
    trust_manifest_path: Path = DEFAULT_TRUST_MANIFEST_PATH,
) -> DataQualityAuditResult:
    effective_database_url = database_url or resolve_database_url()
    resort_repository = ResortRepository(effective_database_url)
    raw_repository = RawWeatherHistoryRepository(effective_database_url)
    climatology_repository = SnowClimatologyRepository(effective_database_url)
    resorts = resort_repository.list_resorts()
    ski_area_names = {
        ski_area.ski_area_id: ski_area.name
        for resort in resorts
        for ski_area in resort.ski_areas
    }
    ski_area_ids = tuple(sorted(ski_area_names))
    warnings: list[str] = []

    effective_archive_end_date = archive_end_date
    if effective_archive_end_date is None:
        effective_archive_end_date = raw_repository.latest_archive_observed_on()
        if effective_archive_end_date is None:
            effective_archive_end_date = archive_start_date
            warnings.append(
                "No archive rows found; archive end date fell back to start date."
            )
        else:
            warnings.append(
                "Archive end date inferred from latest raw_weather_history archive row."
            )
    if effective_archive_end_date < archive_start_date:
        raise ValueError("archive_end_date cannot be earlier than archive_start_date")

    expected_days = (effective_archive_end_date - archive_start_date).days + 1
    archive_stats = raw_repository.list_archive_coverage(
        resort_ids=ski_area_ids,
        elevation_bands=DEFAULT_ELEVATION_BANDS,
        start_date=archive_start_date,
        end_date=effective_archive_end_date,
    )
    archive_rows = tuple(
        ArchiveCoverageRow(
            ski_area_id=ski_area_id,
            resort_name=ski_area_names.get(ski_area_id, ski_area_id),
            elevation_band=elevation_band,
            expected_days=expected_days,
            covered_days=stats.covered_days,
            first_observed_on=stats.first_observed_on,
            last_observed_on=stats.last_observed_on,
        )
        for (ski_area_id, elevation_band), stats in sorted(archive_stats.items())
    )

    climatology_stats = climatology_repository.list_climatology_coverage(
        ski_area_ids=ski_area_ids,
        elevation_bands=DEFAULT_ELEVATION_BANDS,
        baseline_periods=DEFAULT_BASELINE_PERIODS,
        source_model=source_model,
    )
    climatology_rows = tuple(
        ClimatologyCoverageRow(
            ski_area_id=ski_area_id,
            elevation_band=elevation_band,
            baseline_period=baseline_period,
            source_model=source_model,
            expected_rows=EXPECTED_CLIMATOLOGY_DAILY_ROWS,
            actual_rows=stats.row_count,
            min_evidence_seasons=stats.min_evidence_seasons,
            latest_archive_year=stats.latest_archive_year,
        )
        for (ski_area_id, elevation_band, baseline_period), stats in sorted(
            climatology_stats.items()
        )
    )

    archive_summary = summarize_archive_coverage(archive_rows)
    climatology_summary = summarize_climatology_coverage(
        climatology_rows,
        minimum_evidence_seasons=minimum_evidence_seasons,
    )
    catalog_summary = summarize_catalog_field_groups(resorts)
    trust_summary = summarize_trust_manifest(_load_trust_manifest(trust_manifest_path))
    generated_at = datetime.now(UTC)
    metric_snapshot = DataQualityMetricSnapshot.combine(
        archive_summary.metric_snapshot(),
        _archive_detail_metric_snapshot(archive_rows),
        climatology_summary.metric_snapshot(),
        _climatology_detail_metric_snapshot(
            climatology_rows,
            minimum_evidence_seasons=minimum_evidence_seasons,
        ),
        catalog_summary.metric_snapshot(),
        trust_summary.metric_snapshot(),
        DataQualityMetricSnapshot(
            gauges=(
                MetricGauge(
                    name="snowcast_data_audit_generated_timestamp_seconds",
                    value=generated_at.timestamp(),
                ),
                MetricGauge(
                    name="snowcast_data_audit_archive_end_timestamp_seconds",
                    value=_date_timestamp_seconds(effective_archive_end_date),
                    labels={"domain": "historical_archive"},
                ),
            )
        ),
    )
    result = DataQualityAuditResult(
        generated_at=generated_at.isoformat(),
        archive_window={
            "start_date": archive_start_date.isoformat(),
            "end_date": effective_archive_end_date.isoformat(),
        },
        summary_by_domain={
            "historical_archive": archive_summary.as_dict(),
            "snow_climatology": climatology_summary.as_dict(),
            "catalog_required_fields": catalog_summary.as_dict(),
            "catalog_source_trust": trust_summary.as_dict(),
        },
        historical_archive_issues=archive_summary.issues,
        snow_climatology_issues=climatology_summary.issues,
        catalog_field_issues=catalog_summary.issues,
        source_trust_issues=trust_summary.issues,
        warnings=warnings,
        metric_snapshot=metric_snapshot,
    )
    if output_dir is not None:
        write_audit_artifacts(result, output_dir=output_dir)
    return result


def write_audit_artifacts(
    result: DataQualityAuditResult,
    *,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data-quality-summary.json").write_text(
        json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "data-quality-report.md").write_text(
        render_markdown_report(result),
        encoding="utf-8",
    )


def render_markdown_report(result: DataQualityAuditResult) -> str:
    lines = [
        "# Snowcast Data Quality Audit",
        "",
        f"Generated: `{result.generated_at}`",
        "",
        "## Summary",
        "",
        "| Domain | Completeness | Issues | Status counts |",
        "| --- | ---: | ---: | --- |",
    ]
    for domain, summary in result.summary_by_domain.items():
        ratio = float(summary.get("ratio", 0.0))
        issue_count = int(summary.get("issue_count", 0))
        status_counts = summary.get("status_counts", {})
        lines.append(
            f"| `{domain}` | {ratio:.1%} | {issue_count} | "
            f"`{json.dumps(status_counts, sort_keys=True)}` |"
        )

    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result.warnings)

    _append_issue_section(
        lines,
        "Historical Archive Issues",
        result.historical_archive_issues,
        ("ski_area_id", "elevation_band", "status", "missing_days"),
    )
    _append_issue_section(
        lines,
        "Snow Climatology Issues",
        result.snow_climatology_issues,
        (
            "ski_area_id",
            "elevation_band",
            "baseline_period",
            "status",
            "actual_rows",
            "min_evidence_seasons",
        ),
    )
    _append_issue_section(
        lines,
        "Catalog Field Issues",
        result.catalog_field_issues,
        ("entity_type", "entity_id", "field_group", "status", "issue"),
    )
    _append_issue_section(
        lines,
        "Source Trust Issues",
        result.source_trust_issues,
        ("resort_id", "field_group", "trust_status", "raw_status"),
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit Snowcast data quality and export summary telemetry."
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Postgres connection string. Defaults to DATABASE_URL/local settings.",
    )
    parser.add_argument(
        "--archive-start-date",
        type=_parse_date,
        default=DEFAULT_ARCHIVE_START_DATE,
        help="First archive date expected in raw_weather_history.",
    )
    parser.add_argument(
        "--archive-end-date",
        type=_parse_optional_date,
        default=None,
        help="Latest archive date expected. Omit to infer from DB.",
    )
    parser.add_argument(
        "--source-model",
        default=DEFAULT_SOURCE_MODEL,
        help="Derived climatology source-model/version label.",
    )
    parser.add_argument(
        "--minimum-evidence-seasons",
        type=int,
        default=DEFAULT_MINIMUM_EVIDENCE_SEASONS,
        help="Minimum evidence seasons before climatology coverage is strong.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for JSON and Markdown audit artifacts.",
    )
    args = parser.parse_args()

    with configure_cli_observability(job_name="audit_data_quality"):
        with job_span("audit_data_quality"):
            result = run_data_quality_audit(
                database_url=args.database_url,
                archive_start_date=args.archive_start_date,
                archive_end_date=args.archive_end_date,
                source_model=args.source_model,
                minimum_evidence_seasons=args.minimum_evidence_seasons,
                output_dir=args.output_dir,
            )
            record_data_quality_audit_result(result.metric_snapshot)
    print(
        "Data quality audit:",
        f"archive={result.summary_by_domain['historical_archive']['ratio']:.1%}",
        f"climatology={result.summary_by_domain['snow_climatology']['ratio']:.1%}",
        f"catalog={result.summary_by_domain['catalog_required_fields']['ratio']:.1%}",
        f"trust={result.summary_by_domain['catalog_source_trust']['ratio']:.1%}",
    )


def is_valid_data_quality_status(value: str) -> bool:
    return value in VALID_DATA_QUALITY_STATUSES


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_optional_date(value: str) -> date | None:
    if not value:
        return None
    return _parse_date(value)


def _load_trust_manifest(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_issue_section(
    lines: list[str],
    title: str,
    issues: list[dict[str, Any]],
    columns: tuple[str, ...],
) -> None:
    lines.extend(["", f"## {title}", ""])
    if not issues:
        lines.append("No issues found.")
        return
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for issue in issues[:100]:
        lines.append(
            "| "
            + " | ".join(_markdown_cell(issue.get(column)) for column in columns)
            + " |"
        )
    if len(issues) > 100:
        lines.append("")
        lines.append(f"Showing first 100 of {len(issues)} issues.")


def _markdown_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")


def _summary_metric_snapshot(
    *,
    domain: str,
    ratio: float,
    status_counts: Mapping[str, int],
    gauges: tuple[MetricGauge, ...] = (),
) -> DataQualityMetricSnapshot:
    return DataQualityMetricSnapshot(
        completeness_ratios={domain: ratio},
        entity_counts=tuple(
            DataQualityEntityCount(domain=domain, status=status, count=count)
            for status, count in status_counts.items()
        ),
        gauges=gauges,
    )


def _add_catalog_row(
    rows: list[dict[str, Any]],
    *,
    resort_id: str,
    entity_type: str,
    entity_id: str,
    field_group: str,
    status: DataQualityStatus,
    issue: str = "",
) -> None:
    rows.append(
        {
            "resort_id": resort_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "field_group": field_group,
            "status": status,
            "issue": "" if status == "complete" else issue or status,
        }
    )


def _coordinate_status(
    latitude: float | None, longitude: float | None
) -> DataQualityStatus:
    if latitude is None or longitude is None:
        return "missing"
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return "invalid"
    return "complete"


def _elevation_status(
    base_elevation_m: int | None, summit_elevation_m: int | None
) -> DataQualityStatus:
    if base_elevation_m is None or summit_elevation_m is None:
        return "missing"
    if base_elevation_m <= 0 or summit_elevation_m <= base_elevation_m:
        return "invalid"
    return "complete"


def _manifest_field_groups(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    raw_field_groups = manifest.get("field_groups")
    if isinstance(raw_field_groups, list):
        field_groups = tuple(
            field_group
            for field_group in raw_field_groups
            if isinstance(field_group, str)
        )
        if field_groups:
            return field_groups

    destinations = manifest.get("destinations")
    if not isinstance(destinations, Mapping):
        return ()

    groups: set[str] = set()
    for entry in destinations.values():
        if not isinstance(entry, Mapping):
            continue
        field_statuses = entry.get("field_statuses")
        if isinstance(field_statuses, Mapping):
            groups.update(str(group) for group in field_statuses)
    return tuple(sorted(groups))


def _source_refs(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )


def _trust_coverage_state(
    *,
    raw_status: Any,
    has_external_source: bool,
) -> TrustCoverageState:
    if raw_status in SOURCE_BACKED_TRUST_STATUSES:
        return "verified" if has_external_source else "invalid"
    if raw_status == "estimated":
        return "estimated"
    if raw_status in {None, "needs_source"}:
        return "missing"
    return "invalid"


def _ordered_counts(
    counter: Mapping[str, int],
    ordered_keys: tuple[str, ...],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key in ordered_keys:
        count = counter.get(key, 0)
        if count:
            counts[key] = count
    for key in sorted(counter):
        if key not in counts and counter[key]:
            counts[key] = counter[key]
    return counts


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _archive_detail_metric_snapshot(
    rows: tuple[ArchiveCoverageRow, ...],
) -> DataQualityMetricSnapshot:
    gauges: list[MetricGauge] = []
    for row in rows:
        labels = {
            "ski_area_id": row.ski_area_id,
            "elevation_band": str(row.elevation_band),
        }
        gauges.append(
            MetricGauge(
                name="snowcast_archive_coverage_ratio",
                value=_ratio(row.covered_days, row.expected_days),
                labels=labels,
            )
        )
        gauges.append(
            MetricGauge(
                name="snowcast_archive_missing_days_by_ski_area",
                value=row.missing_days,
                labels=labels,
            )
        )
        if row.last_observed_on:
            gauges.append(
                MetricGauge(
                    name="snowcast_archive_last_observed_timestamp_seconds",
                    value=_date_string_timestamp_seconds(row.last_observed_on),
                    labels=labels,
                )
            )
    return DataQualityMetricSnapshot(gauges=tuple(gauges))


def _climatology_detail_metric_snapshot(
    rows: tuple[ClimatologyCoverageRow, ...],
    *,
    minimum_evidence_seasons: int,
) -> DataQualityMetricSnapshot:
    gauges: list[MetricGauge] = []
    for row in rows:
        labels = {
            "ski_area_id": row.ski_area_id,
            "elevation_band": str(row.elevation_band),
            "baseline_period": str(row.baseline_period),
            "source_model": row.source_model,
        }
        gauges.append(
            MetricGauge(
                name="snowcast_climatology_coverage_ratio",
                value=_ratio(row.actual_rows, row.expected_rows),
                labels=labels,
            )
        )
        gauges.append(
            MetricGauge(
                name="snowcast_climatology_missing_rows_by_ski_area",
                value=row.missing_rows,
                labels=labels,
            )
        )
        status = row.status(minimum_evidence_seasons=minimum_evidence_seasons)
        if status != "complete":
            gauges.append(
                MetricGauge(
                    name="snowcast_climatology_gap_count",
                    value=1,
                    labels={**labels, "status": status},
                )
            )
    return DataQualityMetricSnapshot(gauges=tuple(gauges))


def _date_string_timestamp_seconds(value: str) -> float:
    return _date_timestamp_seconds(date.fromisoformat(value))


def _date_timestamp_seconds(value: date) -> float:
    return datetime.combine(value, time.min, tzinfo=UTC).timestamp()


def _json_safe(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    return value


if __name__ == "__main__":
    main()
