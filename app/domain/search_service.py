from urllib.parse import urlencode

from app.data.repositories import (
    get_condition_history_repository,
    get_raw_weather_history_repository,
    get_resort_repository,
    is_condition_fresh,
)
from app.domain.models import (
    ConfidenceContributor,
    Destination,
    ExplanationItem,
    ProvenanceInfo,
    Rental,
    ResortConditions,
    SearchExplanation,
    SearchFilters,
    SearchResult,
    SkiArea,
    StayBase,
    WeatherEvidenceMetrics,
)
from app.domain.planning import (
    derive_planning_assessment,
    derive_weather_evidence_metrics,
)
from app.domain.planning_policy import DEFAULT_PLANNING_HEURISTIC_POLICY
from app.domain.ranking import (
    availability_penalty,
    budget_penalty,
    lift_distance_matches,
    lift_distance_score,
    quality_score,
    skill_fit_score,
    skill_level_matches,
    stay_base_budget_price,
)
from app.integrations.conditions import get_conditions_provider

POLICY = DEFAULT_PLANNING_HEURISTIC_POLICY


def build_accommodation_link(*, resort_name: str, country: str) -> str:
    query = urlencode(
        {
            "ss": f"{resort_name}, {country}",
            "group_adults": 2,
            "no_rooms": 1,
            "group_children": 0,
        }
    )
    return f"https://www.booking.com/searchresults.html?{query}"


def _fallback_conditions(resort_name: str) -> ResortConditions:
    return ResortConditions(
        resort_name=resort_name,
        snow_confidence_score=0.4,
        availability_status="limited",
        weather_summary="No live conditions signal available for this ski area.",
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


def _build_planning_provenance(
    *,
    evidence_count: int,
    latest_snapshot_at: str | None,
    evidence_source: str,
    evidence_profile: str,
) -> ProvenanceInfo:
    text_policy = POLICY.text
    if evidence_profile == "forecast_assisted":
        profile_text = text_policy.forecast_assisted
        source_name = profile_text.source_name
        basis_summary = profile_text.provenance_summary
    elif evidence_profile == "archive_backed":
        profile_text = text_policy.archive_backed
        source_name = profile_text.source_name
        basis_summary = profile_text.provenance_summary
    elif evidence_source == "snapshot_history":
        source_name = text_policy.snapshot_fallback_source_name
        basis_summary = text_policy.snapshot_fallback_provenance_summary
    else:
        profile_text = text_policy.fallback_heavy
        source_name = profile_text.source_name
        basis_summary = profile_text.provenance_summary
    if evidence_count > 0:
        return ProvenanceInfo(
            source_name=source_name,
            source_type="estimated",
            updated_at=latest_snapshot_at,
            freshness_status="historical",
            basis_summary=basis_summary,
            evidence_profile=evidence_profile,
        )

    return ProvenanceInfo(
        source_name=source_name,
        source_type="estimated",
        updated_at=None,
        freshness_status="unknown",
        basis_summary=basis_summary,
        evidence_profile=evidence_profile,
    )


def _build_explanation(
    *,
    stay_base: StayBase,
    ski_area: SkiArea,
    filters: SearchFilters,
    penalty: float,
    conditions: ResortConditions,
) -> SearchExplanation:
    quality_label = {
        1: "budget",
        2: "standard",
        3: "premium",
    }[filters.stars]
    highlights = [
        ExplanationItem(
            label=f"{stay_base.name} supports {filters.skill_level} skiers."
        ),
        ExplanationItem(
            label=(f"Stay-base quality clears the requested {quality_label} tier.")
        ),
    ]
    risks: list[ExplanationItem] = []
    confidence_contributors = [
        ConfidenceContributor(
            label=(
                f"Skill match is strong for the requested {filters.skill_level} level."
            ),
            direction="positive",
        ),
    ]

    if conditions.snow_confidence_label == "good":
        highlights.append(
            ExplanationItem(
                label=f"{ski_area.name} has good snow confidence for this trip window."
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Snow outlook is strong for the selected ski area.",
                direction="positive",
            )
        )
    elif conditions.snow_confidence_label == "fair":
        highlights.append(
            ExplanationItem(
                label=f"{ski_area.name} has fair snow confidence for this trip window."
            )
        )
    else:
        risks.append(
            ExplanationItem(
                label=f"{ski_area.name} has poor snow confidence for this trip window."
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Weak snow outlook reduces recommendation certainty.",
                direction="negative",
            )
        )

    if penalty > 0:
        risks.append(
            ExplanationItem(
                label=(
                    "Stay-base nightly estimate is slightly outside the requested "
                    "budget."
                )
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label=(
                    "Budget stretch lowers certainty that this is the best-fit option."
                ),
                direction="negative",
            )
        )

    if conditions.availability_status == "limited":
        risks.append(
            ExplanationItem(
                label="Weather signal suggests some disruption risk right now."
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Weather disruption risk reduces recommendation certainty.",
                direction="negative",
            )
        )
    elif conditions.availability_status == "temporarily_closed":
        risks.append(
            ExplanationItem(
                label=("Weather signal suggests high disruption risk right now.")
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label=(
                    "High disruption risk materially lowers recommendation certainty."
                ),
                direction="negative",
            )
        )
    elif conditions.availability_status == "out_of_season":
        risks.append(
            ExplanationItem(label="Resort is outside its typical ski season window.")
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label=(
                    "Out-of-season timing materially lowers recommendation certainty."
                ),
                direction="negative",
            )
        )

    if stay_base.lift_distance == "near":
        highlights.append(
            ExplanationItem(label="Selected stay base keeps you close to the lift.")
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Near-lift access improves practical fit for the trip.",
                direction="positive",
            )
        )

    return SearchExplanation(
        highlights=highlights,
        risks=risks,
        confidence_contributors=confidence_contributors,
    )


def _list_planning_snapshots(
    *,
    history_repository,
    destination: Destination,
    ski_area: SkiArea,
) -> tuple:
    snapshots = history_repository.list_snapshots_for_resort(ski_area.ski_area_id)
    if snapshots or ski_area.ski_area_id == destination.resort_id:
        return snapshots
    return history_repository.list_snapshots_for_resort(destination.resort_id)


def _list_raw_weather_observations(
    *,
    raw_history_repository,
    destination: Destination,
    ski_area: SkiArea,
) -> tuple:
    observations = raw_history_repository.list_observations_for_resort(
        ski_area.ski_area_id,
        elevation_band="mid",
    )
    if observations or ski_area.ski_area_id == destination.resort_id:
        return observations
    return raw_history_repository.list_observations_for_resort(
        destination.resort_id,
        elevation_band="mid",
    )


def _build_result(
    destination: Destination,
    ski_area: SkiArea,
    stay_base: StayBase,
    rental: Rental,
    filters: SearchFilters,
    conditions: ResortConditions | None,
    conditions_provenance: ProvenanceInfo,
    planning_summary: str | None = None,
    planning_provenance: ProvenanceInfo | None = None,
    planning_evidence_count: int | None = None,
    planning_weather_metrics: WeatherEvidenceMetrics | None = None,
    best_travel_months: tuple[int, ...] = (),
) -> SearchResult | None:
    active_conditions = conditions or _fallback_conditions(ski_area.name)
    price = stay_base_budget_price(stay_base)
    penalty = budget_penalty(
        price=price,
        min_price=filters.min_price,
        max_price=filters.max_price,
        budget_flex=filters.budget_flex,
    )
    if penalty is None:
        return None

    availability_score_penalty = availability_penalty(
        active_conditions.availability_status
    )
    if availability_score_penalty is None:
        return None

    quality = quality_score(stay_base.quality)
    skill_bonus = skill_fit_score(stay_base, filters.skill_level)
    lift_bonus = lift_distance_score(stay_base.lift_distance) / 10
    price_component = (1 / price) * 0.3
    conditions_score = active_conditions.conditions_score
    snow_confidence_score = active_conditions.snow_confidence_score
    score = (
        quality * 0.55
        + price_component
        + skill_bonus
        + lift_bonus
        + conditions_score * 0.35
        - penalty
        - availability_score_penalty
    )
    explanation = _build_explanation(
        stay_base=stay_base,
        ski_area=ski_area,
        filters=filters,
        penalty=penalty,
        conditions=active_conditions,
    )

    return SearchResult(
        resort_id=destination.resort_id,
        resort_name=destination.name,
        region=destination.region,
        selected_ski_area_id=ski_area.ski_area_id,
        selected_ski_area_name=ski_area.name,
        selected_stay_base_name=stay_base.name,
        selected_stay_base_lift_distance=stay_base.lift_distance,
        stay_base_price_range=stay_base.price_range,
        selected_area_name=stay_base.name,
        selected_area_lift_distance=stay_base.lift_distance,
        area_price_range=stay_base.price_range,
        rental_name=rental.name,
        rental_price_range=rental.price_range,
        rating_estimate=quality,
        link=build_accommodation_link(
            resort_name=destination.name,
            country=destination.country,
        ),
        score=score,
        budget_penalty=penalty,
        conditions_summary=active_conditions.weather_summary,
        snow_confidence_score=snow_confidence_score,
        snow_confidence_label=active_conditions.snow_confidence_label,
        availability_status=active_conditions.availability_status,
        conditions_score=conditions_score,
        conditions_provenance=conditions_provenance,
        explanation=explanation,
        recommendation_confidence=min(
            (quality / 3) * 0.45
            + snow_confidence_score * 0.35
            + (1 - availability_score_penalty) * 0.2,
            1.0,
        ),
        planning_summary=planning_summary,
        planning_provenance=planning_provenance,
        planning_evidence_count=planning_evidence_count,
        planning_weather_metrics=planning_weather_metrics,
        best_travel_months=list(best_travel_months),
    )


def search_resorts(
    filters: SearchFilters,
    *,
    resorts: tuple[Destination, ...] | None = None,
    conditions_provider=None,
    condition_history_repository=None,
    raw_weather_history_repository=None,
) -> list[SearchResult]:
    normalized_location = filters.location.strip().lower()
    results: list[SearchResult] = []
    active_resorts = resorts or get_resort_repository().list_resorts()
    active_conditions_provider = conditions_provider or get_conditions_provider()
    history_repository = (
        condition_history_repository or get_condition_history_repository()
    )
    active_raw_history_repository = (
        raw_weather_history_repository or get_raw_weather_history_repository()
    )

    for resort in active_resorts:
        if resort.country.lower() != normalized_location:
            continue

        matching_pairs: list[SearchResult] = []
        for stay_base in resort.stay_bases:
            if quality_score(stay_base.quality) < filters.stars:
                continue
            if not skill_level_matches(stay_base, filters.skill_level):
                continue
            if not lift_distance_matches(
                stay_base.lift_distance, filters.lift_distance
            ):
                continue

            for ski_area in resort.ski_areas:
                current_conditions = (
                    active_conditions_provider.get_conditions_for_resort(ski_area.name)
                )
                conditions_provenance = _build_conditions_provenance(current_conditions)
                planning_summary: str | None = None
                planning_provenance: ProvenanceInfo | None = None
                planning_evidence_count: int | None = None
                planning_weather_metrics: WeatherEvidenceMetrics | None = None
                best_travel_months: tuple[int, ...] = ()

                if filters.travel_month is not None or (
                    filters.trip_start_date is not None
                    and filters.trip_end_date is not None
                ):
                    raw_weather_observations = _list_raw_weather_observations(
                        raw_history_repository=active_raw_history_repository,
                        destination=resort,
                        ski_area=ski_area,
                    )
                    planning = derive_planning_assessment(
                        resort=ski_area,
                        travel_month=filters.travel_month,
                        snapshots=_list_planning_snapshots(
                            history_repository=history_repository,
                            destination=resort,
                            ski_area=ski_area,
                        ),
                        raw_weather_observations=raw_weather_observations,
                        current_conditions=current_conditions,
                        trip_start_date=filters.trip_start_date,
                        trip_end_date=filters.trip_end_date,
                    )
                    ski_area_conditions = planning.conditions
                    planning_summary = planning.planning_summary
                    planning_evidence_count = planning.evidence_count
                    best_travel_months = planning.best_travel_months
                    planning_provenance = _build_planning_provenance(
                        evidence_count=planning.evidence_count,
                        latest_snapshot_at=planning.latest_snapshot_at,
                        evidence_source=planning.evidence_source,
                        evidence_profile=planning.evidence_profile,
                    )
                    planning_weather_metrics = derive_weather_evidence_metrics(
                        raw_weather_observations=raw_weather_observations,
                        travel_month=filters.travel_month,
                        trip_start_date=filters.trip_start_date,
                        trip_end_date=filters.trip_end_date,
                    )
                else:
                    ski_area_conditions = current_conditions

                for rental in resort.rentals:
                    if filters.lift_distance and not lift_distance_matches(
                        rental.lift_distance, filters.lift_distance
                    ):
                        continue

                    result = _build_result(
                        destination=resort,
                        ski_area=ski_area,
                        stay_base=stay_base,
                        rental=rental,
                        filters=filters,
                        conditions=ski_area_conditions,
                        conditions_provenance=conditions_provenance,
                        planning_summary=planning_summary,
                        planning_provenance=planning_provenance,
                        planning_evidence_count=planning_evidence_count,
                        planning_weather_metrics=planning_weather_metrics,
                        best_travel_months=best_travel_months,
                    )
                    if result is not None:
                        matching_pairs.append(result)

        if matching_pairs:
            results.append(
                sorted(
                    matching_pairs,
                    key=lambda result: (
                        -result.score,
                        -result.snow_confidence_score,
                        result.resort_name,
                        result.selected_stay_base_name,
                        result.selected_ski_area_name,
                    ),
                )[0]
            )

    return sorted(
        results,
        key=lambda result: (
            -result.score,
            -result.snow_confidence_score,
            result.resort_name,
            result.selected_stay_base_name,
            result.selected_ski_area_name,
        ),
    )[:3]
