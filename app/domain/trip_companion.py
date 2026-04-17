from __future__ import annotations

from datetime import UTC, datetime

from app.data.repositories import (
    CurrentTripRepository,
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    is_condition_fresh,
)
from app.domain.models import (
    CurrentTrip,
    CurrentTripComparisonBasis,
    CurrentTripDelta,
    CurrentTripSummary,
    ProvenanceInfo,
    ResortConditions,
    ResortConditionSnapshot,
)


def _fallback_conditions(resort_name: str) -> ResortConditions:
    return ResortConditions(
        resort_name=resort_name,
        snow_confidence_score=0.4,
        availability_status="limited",
        weather_summary="No live conditions signal available for this resort.",
        conditions_score=0.4,
    )


def _build_conditions_provenance(
    conditions: ResortConditions | None,
) -> ProvenanceInfo:
    if conditions is None or (
        conditions.updated_at is None and conditions.source is None
    ):
        return ProvenanceInfo(
            source_name=None,
            source_type="estimated",
            updated_at=None,
            freshness_status="unknown",
            basis_summary=(
                "Using an estimated fallback because no live forecast signal is "
                "available for this resort."
            ),
        )

    freshness_status = "unknown"
    if conditions.updated_at is not None:
        freshness_status = "fresh" if is_condition_fresh(conditions) else "stale"

    return ProvenanceInfo(
        source_name=conditions.source or "open-meteo",
        source_type="forecast",
        updated_at=conditions.updated_at,
        freshness_status=freshness_status,
        basis_summary=(
            "Using a current forecast-based conditions signal from the latest "
            "weather refresh."
        ),
    )


def _comparison_basis(trip: CurrentTrip) -> tuple[datetime, CurrentTripComparisonBasis]:
    if trip.last_checked_at is not None:
        baseline_at = datetime.fromisoformat(trip.last_checked_at)
        return baseline_at, CurrentTripComparisonBasis(
            kind="since_last_check",
            baseline_at=trip.last_checked_at,
            label="Since last check",
        )

    baseline_at = datetime.fromisoformat(trip.created_at)
    return baseline_at, CurrentTripComparisonBasis(
        kind="since_trip_saved",
        baseline_at=trip.created_at,
        label="Since trip was saved",
    )


def _latest_snapshot_before(
    snapshots: tuple[ResortConditionSnapshot, ...],
    *,
    baseline_at: datetime,
) -> ResortConditionSnapshot | None:
    for snapshot in reversed(snapshots):
        observed_at = datetime.fromisoformat(snapshot.observed_at)
        if observed_at <= baseline_at:
            return snapshot
    return None


def _delta_from_conditions(
    *,
    current_conditions: ResortConditions,
    provenance: ProvenanceInfo,
    prior_snapshot: ResortConditionSnapshot,
) -> CurrentTripDelta:
    changes: list[str] = []

    snow_delta = (
        current_conditions.snow_confidence_score - prior_snapshot.snow_confidence_score
    )
    if current_conditions.snow_confidence_label != prior_snapshot.snow_confidence_label:
        direction = "improved" if snow_delta >= 0 else "weakened"
        changes.append(
            "Snow confidence "
            f"{direction} from {prior_snapshot.snow_confidence_label} "
            f"to {current_conditions.snow_confidence_label}."
        )
    elif abs(snow_delta) >= 0.08:
        direction = "up" if snow_delta > 0 else "down"
        changes.append(
            f"Snow confidence moved {direction} by "
            f"{abs(round(snow_delta * 100))} points."
        )

    if current_conditions.availability_status != prior_snapshot.availability_status:
        previous_status = prior_snapshot.availability_status.replace("_", " ")
        current_status = current_conditions.availability_status.replace("_", " ")
        changes.append(
            f"Availability changed from {previous_status} to {current_status}."
        )

    if current_conditions.weather_summary != prior_snapshot.weather_summary:
        changes.append("Weather summary shifted since the previous recorded snapshot.")

    if provenance.freshness_status == "stale":
        changes.append("The latest forecast refresh is now stale.")

    if not changes:
        return CurrentTripDelta(
            status="unchanged",
            summary="No material conditions changes since the comparison baseline.",
            changes=[],
        )

    return CurrentTripDelta(
        status="changed",
        summary="Conditions changed since the comparison baseline.",
        changes=changes,
    )


def build_current_trip_summary(
    *,
    trip_repository: CurrentTripRepository | None = None,
    conditions_repository: ResortConditionsRepository | None = None,
    history_repository: ResortConditionHistoryRepository | None = None,
) -> CurrentTripSummary | None:
    trip_repo = trip_repository or CurrentTripRepository()
    conditions_repo = conditions_repository or ResortConditionsRepository()
    history_repo = history_repository or ResortConditionHistoryRepository()

    trip = trip_repo.get_current_trip()
    if trip is None:
        return None

    stored_conditions = conditions_repo.get_conditions_for_ski_area(
        trip.selected_ski_area_name
    )
    current_conditions = stored_conditions or _fallback_conditions(
        trip.selected_ski_area_name
    )
    provenance = _build_conditions_provenance(stored_conditions)
    baseline_at, basis = _comparison_basis(trip)

    current_updated_at = (
        datetime.fromisoformat(current_conditions.updated_at)
        if current_conditions.updated_at is not None
        else None
    )
    snapshots = history_repo.list_snapshots_for_resort(trip.selected_ski_area_id)

    if current_updated_at is None:
        delta = CurrentTripDelta(
            status="insufficient_history",
            summary=(
                "Current conditions have not been refreshed yet, so there is not "
                "enough history to compare."
            ),
            changes=[],
        )
    elif current_updated_at <= baseline_at:
        delta = CurrentTripDelta(
            status="unchanged",
            summary=(
                "No newer conditions refresh has landed since the comparison baseline."
            ),
            changes=[],
        )
    else:
        prior_snapshot = _latest_snapshot_before(snapshots, baseline_at=baseline_at)
        if prior_snapshot is None:
            delta = CurrentTripDelta(
                status="insufficient_history",
                summary=(
                    "Conditions were refreshed after the comparison baseline, "
                    "but there is not enough earlier history to compare yet."
                ),
                changes=[],
            )
        else:
            delta = _delta_from_conditions(
                current_conditions=current_conditions,
                provenance=provenance,
                prior_snapshot=prior_snapshot,
            )

    return CurrentTripSummary(
        trip=trip,
        current_conditions=current_conditions,
        current_conditions_provenance=provenance,
        comparison_basis=basis,
        delta=delta,
    )


def mark_current_trip_checked(
    *,
    trip_repository: CurrentTripRepository | None = None,
    checked_at: str | None = None,
) -> CurrentTrip | None:
    trip_repo = trip_repository or CurrentTripRepository()
    timestamp = checked_at or datetime.now(UTC).isoformat()
    return trip_repo.mark_checked(checked_at=timestamp)
