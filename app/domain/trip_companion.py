from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from app.data.repositories import (
    CompanionEventRepository,
    CurrentTripRepository,
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    is_condition_fresh,
)
from app.domain.models import (
    CompanionStatus,
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


def _trip_window_status(
    trip: CurrentTrip,
    *,
    current_date: datetime | None = None,
) -> CompanionStatus:
    if trip.trip_start_date is None or trip.trip_end_date is None:
        return CompanionStatus(
            trip_window_status="unscheduled",
            trip_window_label="Trip dates not set",
            notification_eligible=False,
            eligibility_reason="Exact trip dates are not available.",
            actionable_change_available=False,
        )

    today = (current_date or datetime.now(UTC)).date()
    if today < trip.trip_start_date:
        status = "upcoming"
        label = "Trip upcoming"
        eligible = True
        reason = "Trip dates are in the future."
    elif today > trip.trip_end_date:
        status = "past"
        label = "Trip finished"
        eligible = False
        reason = "Trip dates have ended."
    else:
        status = "active"
        label = "Trip active"
        eligible = True
        reason = "Trip dates include today."

    return CompanionStatus(
        trip_window_status=status,
        trip_window_label=label,
        notification_eligible=eligible,
        eligibility_reason=reason,
        actionable_change_available=False,
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
    comparison_basis: CurrentTripComparisonBasis,
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
            summary=(
                "Conditions have not changed "
                f"{_comparison_basis_copy(comparison_basis)}."
            ),
            changes=[],
        )

    return CurrentTripDelta(
        status="changed",
        summary=f"Conditions have changed {_comparison_basis_copy(comparison_basis)}.",
        changes=changes,
    )


def _comparison_basis_copy(comparison_basis: CurrentTripComparisonBasis) -> str:
    if comparison_basis.kind == "since_trip_saved":
        return "since you saved this trip"
    return "since your last check"


def _event_signature(
    *,
    trip: CurrentTrip,
    current_conditions: ResortConditions,
    basis: CurrentTripComparisonBasis,
    delta: CurrentTripDelta,
    companion_status: CompanionStatus,
) -> str:
    return hashlib.sha256(
        "|".join(
            [
                trip.ski_region_id,
                trip.stay_destination_id,
                trip.stay_base_id,
                trip.focus_ski_area_id,
                trip.lift_pass_product_id,
                basis.baseline_at,
                current_conditions.updated_at or "none",
                delta.status,
                delta.summary,
                ",".join(delta.changes),
                companion_status.trip_window_status,
                str(companion_status.notification_eligible),
            ]
        ).encode("utf-8")
    ).hexdigest()


def maybe_record_companion_event(
    *,
    user_id: str,
    summary: CurrentTripSummary,
    event_repository: CompanionEventRepository | None = None,
) -> None:
    if summary.delta.status != "changed":
        return
    if not summary.companion_status.notification_eligible:
        return

    repo = event_repository or CompanionEventRepository()
    repo.record_event(
        user_id=user_id,
        ski_region_id=summary.trip.ski_region_id,
        stay_destination_id=summary.trip.stay_destination_id,
        stay_base_id=summary.trip.stay_base_id,
        focus_ski_area_id=summary.trip.focus_ski_area_id,
        lift_pass_product_id=summary.trip.lift_pass_product_id,
        event_type="conditions_change",
        event_signature=_event_signature(
            trip=summary.trip,
            current_conditions=summary.current_conditions,
            basis=summary.comparison_basis,
            delta=summary.delta,
            companion_status=summary.companion_status,
        ),
        actionable=True,
        summary=summary.delta.summary,
        changes=summary.delta.changes,
        trip_window_status=summary.companion_status.trip_window_status,
        conditions_updated_at=summary.current_conditions.updated_at,
    )


def build_current_trip_summary(
    *,
    user_id: str,
    trip_repository: CurrentTripRepository | None = None,
    conditions_repository: ResortConditionsRepository | None = None,
    history_repository: ResortConditionHistoryRepository | None = None,
    now: datetime | None = None,
) -> CurrentTripSummary | None:
    trip_repo = trip_repository or CurrentTripRepository()
    conditions_repo = conditions_repository or ResortConditionsRepository()
    history_repo = history_repository or ResortConditionHistoryRepository()

    trip = trip_repo.get_current_trip(user_id=user_id)
    if trip is None:
        return None

    stored_conditions = conditions_repo.get_conditions_for_ski_area(
        trip.focus_ski_area_id
    )
    current_conditions = stored_conditions or _fallback_conditions(
        trip.focus_ski_area_name
    )
    provenance = _build_conditions_provenance(stored_conditions)
    baseline_at, basis = _comparison_basis(trip)
    companion_status = _trip_window_status(trip, current_date=now)

    current_updated_at = (
        datetime.fromisoformat(current_conditions.updated_at)
        if current_conditions.updated_at is not None
        else None
    )
    snapshots = history_repo.list_snapshots_for_ski_area(trip.focus_ski_area_id)

    if current_updated_at is None:
        delta = CurrentTripDelta(
            status="insufficient_history",
            summary=(
                "Current conditions are not available yet, so there is not enough "
                "history to compare."
            ),
            changes=[],
        )
    elif current_updated_at <= baseline_at:
        delta = CurrentTripDelta(
            status="unchanged",
            summary=f"Conditions have not changed {_comparison_basis_copy(basis)}.",
            changes=[],
        )
    else:
        prior_snapshot = _latest_snapshot_before(snapshots, baseline_at=baseline_at)
        if prior_snapshot is None:
            delta = CurrentTripDelta(
                status="insufficient_history",
                summary=(
                    f"Conditions are newer {_comparison_basis_copy(basis)}, but "
                    "there is not enough earlier history to compare."
                ),
                changes=[],
            )
        else:
            delta = _delta_from_conditions(
                current_conditions=current_conditions,
                provenance=provenance,
                prior_snapshot=prior_snapshot,
                comparison_basis=basis,
            )

    companion_status = companion_status.model_copy(
        update={
            "actionable_change_available": (
                companion_status.notification_eligible and delta.status == "changed"
            )
        }
    )

    return CurrentTripSummary(
        trip=trip,
        current_conditions=current_conditions,
        current_conditions_provenance=provenance,
        comparison_basis=basis,
        delta=delta,
        companion_status=companion_status,
    )


def mark_current_trip_checked(
    *,
    user_id: str,
    trip_repository: CurrentTripRepository | None = None,
    checked_at: str | None = None,
) -> CurrentTrip | None:
    trip_repo = trip_repository or CurrentTripRepository()
    timestamp = checked_at or datetime.now(UTC).isoformat()
    return trip_repo.mark_checked(user_id=user_id, checked_at=timestamp)
