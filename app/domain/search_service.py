from urllib.parse import urlencode

from app.data.repositories import (
    get_condition_history_repository,
    get_resort_repository,
    is_condition_fresh,
)
from app.domain.models import (
    Area,
    ConfidenceContributor,
    ExplanationItem,
    ProvenanceInfo,
    Rental,
    Resort,
    ResortConditions,
    SearchExplanation,
    SearchFilters,
    SearchResult,
)
from app.domain.planning import derive_planning_assessment
from app.domain.ranking import (
    availability_penalty,
    budget_penalty,
    lift_distance_matches,
    lift_distance_score,
    package_price,
    quality_score,
    skill_fit_score,
    skill_level_matches,
)
from app.integrations.conditions import get_conditions_provider


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


def _build_planning_provenance(
    *,
    evidence_count: int,
    latest_snapshot_at: str | None,
) -> ProvenanceInfo:
    if evidence_count > 0:
        return ProvenanceInfo(
            source_name="snapshot_history+seasonality",
            source_type="estimated",
            updated_at=latest_snapshot_at,
            freshness_status="historical",
            basis_summary=(
                "Estimated from stored monthly snapshots combined with resort "
                "seasonality."
            ),
        )

    return ProvenanceInfo(
        source_name="snapshot_history+seasonality",
        source_type="estimated",
        updated_at=None,
        freshness_status="unknown",
        basis_summary=(
            "Estimated from resort seasonality and elevation because stored "
            "snapshot history is still sparse."
        ),
    )


def _build_explanation(
    *,
    area: Area,
    filters: SearchFilters,
    penalty: float,
    conditions: ResortConditions,
) -> SearchExplanation:
    highlights = [
        ExplanationItem(label=f"{area.name} supports {filters.skill_level} skiers."),
        ExplanationItem(
            label=f"Area quality clears the requested {filters.stars}-star threshold."
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
            ExplanationItem(label="Snow confidence is good for this trip window.")
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Snow outlook is strong for the selected trip window.",
                direction="positive",
            )
        )
    elif conditions.snow_confidence_label == "fair":
        highlights.append(
            ExplanationItem(label="Snow confidence is fair for this trip window.")
        )
    else:
        risks.append(
            ExplanationItem(label="Snow outlook is poor for this trip window.")
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
                label="Package price is slightly outside the requested budget."
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
            ExplanationItem(label="Resort operations are limited at the moment.")
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Operational limits reduce recommendation certainty.",
                direction="negative",
            )
        )
    elif conditions.availability_status == "temporarily_closed":
        risks.append(
            ExplanationItem(
                label=(
                    "Resort is temporarily closed due to current operating conditions."
                )
            )
        )
        confidence_contributors.append(
            ConfidenceContributor(
                label="Temporary closure materially lowers recommendation certainty.",
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

    if area.lift_distance == "near":
        highlights.append(
            ExplanationItem(label="Selected area keeps you close to the lift.")
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


def _build_result(
    resort_id: str,
    resort_name: str,
    country: str,
    region: str,
    area: Area,
    rental: Rental,
    filters: SearchFilters,
    conditions: ResortConditions | None,
    conditions_provenance: ProvenanceInfo,
    planning_summary: str | None = None,
    planning_provenance: ProvenanceInfo | None = None,
    planning_evidence_count: int | None = None,
    best_travel_months: tuple[int, ...] = (),
) -> SearchResult | None:
    active_conditions = conditions or _fallback_conditions(resort_name)
    price = package_price(area, rental)
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

    quality = quality_score(area.quality)
    skill_bonus = skill_fit_score(area, filters.skill_level)
    lift_bonus = lift_distance_score(area.lift_distance) / 10
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
        area=area,
        filters=filters,
        penalty=penalty,
        conditions=active_conditions,
    )

    return SearchResult(
        resort_id=resort_id,
        resort_name=resort_name,
        region=region,
        selected_area_name=area.name,
        selected_area_lift_distance=area.lift_distance,
        area_price_range=area.price_range,
        rental_name=rental.name,
        rental_price_range=rental.price_range,
        rating_estimate=quality,
        link=build_accommodation_link(resort_name=resort_name, country=country),
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
        best_travel_months=list(best_travel_months),
    )


def search_resorts(
    filters: SearchFilters,
    *,
    resorts: tuple[Resort, ...] | None = None,
    conditions_provider=None,
    condition_history_repository=None,
) -> list[SearchResult]:
    normalized_location = filters.location.strip().lower()
    results: list[SearchResult] = []
    active_resorts = resorts or get_resort_repository().list_resorts()
    active_conditions_provider = conditions_provider or get_conditions_provider()
    history_repository = (
        condition_history_repository or get_condition_history_repository()
    )

    for resort in active_resorts:
        if resort.country.lower() != normalized_location:
            continue

        current_conditions = active_conditions_provider.get_conditions_for_resort(
            resort.name
        )
        conditions_provenance = _build_conditions_provenance(current_conditions)
        planning_summary: str | None = None
        planning_provenance: ProvenanceInfo | None = None
        planning_evidence_count: int | None = None
        best_travel_months: tuple[int, ...] = ()

        if filters.travel_month is not None:
            planning = derive_planning_assessment(
                resort=resort,
                travel_month=filters.travel_month,
                snapshots=history_repository.list_snapshots_for_resort(
                    resort.resort_id
                ),
            )
            resort_conditions = planning.conditions
            planning_summary = planning.planning_summary
            planning_evidence_count = planning.evidence_count
            best_travel_months = planning.best_travel_months
            planning_provenance = _build_planning_provenance(
                evidence_count=planning.evidence_count,
                latest_snapshot_at=planning.latest_snapshot_at,
            )
        else:
            resort_conditions = current_conditions

        matching_pairs: list[SearchResult] = []
        for area in resort.areas:
            if quality_score(area.quality) < filters.stars:
                continue
            if not skill_level_matches(area, filters.skill_level):
                continue
            if not lift_distance_matches(area.lift_distance, filters.lift_distance):
                continue

            for rental in resort.rentals:
                if filters.lift_distance and not lift_distance_matches(
                    rental.lift_distance, filters.lift_distance
                ):
                    continue

                result = _build_result(
                    resort_id=resort.resort_id,
                    resort_name=resort.name,
                    country=resort.country,
                    region=resort.region,
                    area=area,
                    rental=rental,
                    filters=filters,
                    conditions=resort_conditions,
                    conditions_provenance=conditions_provenance,
                    planning_summary=planning_summary,
                    planning_provenance=planning_provenance,
                    planning_evidence_count=planning_evidence_count,
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
                        result.selected_area_name,
                    ),
                )[0]
            )

    return sorted(
        results,
        key=lambda result: (
            -result.score,
            -result.snow_confidence_score,
            result.resort_name,
            result.selected_area_name,
        ),
    )[:3]
