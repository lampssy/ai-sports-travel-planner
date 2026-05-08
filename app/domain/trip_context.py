from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.domain.models import (
    BudgetMode,
    SearchFilterPatch,
    TripClarification,
    TripClarificationOption,
    TripContext,
    TripContextPatch,
)

BUDGET_AMOUNT_PATTERN = re.compile(
    r"(?:\bEUR\s*|€\s*)(?P<prefix_amount>\d+(?:[,.]\d{3})*(?:\.\d+)?)\b"
    r"|(?P<suffix_amount>\d+(?:[,.]\d{3})*(?:\.\d+)?)\s*\bEUR\b",
    re.IGNORECASE,
)
TOTAL_BUDGET_TERMS = (
    "total budget",
    "overall budget",
    "all-in",
    "all-in budget",
    "all in",
    "all in budget",
    "whole-trip",
    "whole-trip budget",
    "whole trip",
    "whole trip budget",
)
NIGHTLY_BUDGET_TERMS = (
    "per night",
    "per-night",
    "nightly",
    "a night",
    "each night",
)
TRAVEL_EFFORT_TERMS = (
    "not too far away",
    "nearby",
    "close by",
    "easy to get to",
    "short travel",
    "short trip",
    "driving distance",
    "by car",
)
ORIGIN_PATTERN = re.compile(
    r"\bfrom\s+(?P<origin>[a-z][a-z\s.-]{1,40}?)(?:[,;]|\s+to\b|\s+for\b|\s+with\b|$)",
    re.IGNORECASE,
)
GROUP_SIZE_PATTERN = re.compile(
    r"\b(?:for\s+)?(?:a\s+)?(?:group|party|family)\s+of\s+(?P<size>\d+)\b",
    re.IGNORECASE,
)
NUMERIC_PARTY_PATTERN = re.compile(
    r"\b(?:for\s+)?(?P<size>\d+)\s+(?:people|persons|travelers|travellers|adults)\b",
    re.IGNORECASE,
)
WORD_PARTY_PATTERN = re.compile(
    r"\b(?:for\s+)?(?P<size>one|two|three|four|five|six|seven|eight|nine|ten)\s+"
    r"(?:people|persons|travelers|travellers|adults)\b",
    re.IGNORECASE,
)
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def build_trip_context_payload(
    *,
    query: str,
    filters: dict[str, Any],
    trip_context: TripContext | None = None,
) -> dict[str, Any]:
    heuristic_context = TripContext(
        budget_mode=_detect_budget_mode(query),
        budget_min=_extract_budget_amount(query),
        budget_max=_extract_budget_amount(query),
        party_size=_detect_party_size(query),
        trip_duration_nights=_derive_trip_duration_nights(filters),
        origin_text=_detect_origin_text(query),
    )
    context = _merge_context(
        heuristic_context=heuristic_context,
        provided_context=trip_context,
    )
    clarifications = _build_clarifications(query=query, context=context)
    assumptions = _build_assumptions(context)
    return {
        "trip_context": context,
        "clarifications": clarifications,
        "assumptions": assumptions,
    }


def _merge_context(
    *,
    heuristic_context: TripContext,
    provided_context: TripContext | None,
) -> TripContext:
    if provided_context is None:
        return heuristic_context

    merged = heuristic_context.model_dump()
    for key, value in provided_context.model_dump().items():
        if value is not None:
            merged[key] = value
    return TripContext.model_validate(merged)


def _extract_budget_amount(query: str) -> float | None:
    match = BUDGET_AMOUNT_PATTERN.search(query)
    if match is None:
        return None

    amount_text = (
        match.group("prefix_amount") or match.group("suffix_amount") or ""
    ).replace(",", "")
    return float(amount_text)


def _detect_budget_mode(query: str) -> BudgetMode | None:
    normalized = query.lower()
    if any(term in normalized for term in TOTAL_BUDGET_TERMS):
        return "total_trip"
    if any(term in normalized for term in NIGHTLY_BUDGET_TERMS):
        return "lodging_nightly"
    return None


def _detect_party_size(query: str) -> int | None:
    group_match = GROUP_SIZE_PATTERN.search(query)
    if group_match is not None:
        return int(group_match.group("size"))

    numeric_match = NUMERIC_PARTY_PATTERN.search(query)
    if numeric_match is not None:
        return int(numeric_match.group("size"))

    word_match = WORD_PARTY_PATTERN.search(query)
    if word_match is not None:
        return NUMBER_WORDS[word_match.group("size").lower()]

    normalized = query.lower()
    if re.search(r"\b(?:solo|alone)\b", normalized):
        return 1
    if re.search(r"\b(?:couple|pair)\b", normalized):
        return 2
    if re.search(r"\bfamily\b", normalized):
        return 4
    if re.search(r"\bgroup\b", normalized):
        return 4
    return None


def _derive_trip_duration_nights(filters: dict[str, Any]) -> int | None:
    start_date = _parse_date(filters.get("trip_start_date"))
    end_date = _parse_date(filters.get("trip_end_date"))
    if start_date is None or end_date is None:
        return None

    nights = (end_date - start_date).days
    if nights < 1:
        return None
    return nights


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _detect_origin_text(query: str) -> str | None:
    match = ORIGIN_PATTERN.search(query)
    if match is None:
        return None
    return " ".join(match.group("origin").split()).strip().title() or None


def _build_clarifications(
    *,
    query: str,
    context: TripContext,
) -> list[TripClarification]:
    clarifications: list[TripClarification] = []

    if context.budget_min is not None and context.budget_mode is None:
        clarifications.append(_budget_mode_clarification(context.budget_min))

    has_exact_timing = context.trip_duration_nights is not None
    if context.budget_mode == "total_trip" and not has_exact_timing:
        clarifications.append(_trip_duration_clarification())

    if context.budget_mode == "total_trip" and context.party_size is None:
        clarifications.append(_party_size_clarification())

    if _mentions_travel_effort(query) and context.origin_text is None:
        clarifications.append(_travel_origin_clarification())

    return sorted(clarifications, key=lambda item: item.priority, reverse=True)[:3]


def _budget_mode_clarification(amount: float) -> TripClarification:
    return TripClarification(
        id="budget-mode",
        question="Is this budget for nightly lodging or the whole trip?",
        reason="Budget amount was detected without clear budget mode.",
        priority=100,
        options=[
            TripClarificationOption(
                id="lodging-nightly",
                label="Nightly lodging",
                description="Use the amount as the stay-base nightly budget.",
                context_patch=TripContextPatch(budget_mode="lodging_nightly"),
                filter_patch=SearchFilterPatch(
                    min_price=amount,
                    max_price=amount,
                ),
            ),
            TripClarificationOption(
                id="total-trip",
                label="Total trip",
                description="Use the amount as the whole-trip budget.",
                context_patch=TripContextPatch(budget_mode="total_trip"),
            ),
        ],
    )


def _trip_duration_clarification() -> TripClarification:
    return TripClarification(
        id="trip-duration",
        question="How many nights should the total budget cover?",
        reason="Total trip budget needs a trip length before nightly planning.",
        priority=90,
        options=[
            TripClarificationOption(
                id="short-stay",
                label="3 nights",
                description="Plan the total budget around a short ski break.",
                context_patch=TripContextPatch(trip_duration_nights=3),
            ),
            TripClarificationOption(
                id="week-stay",
                label="7 nights",
                description="Plan the total budget around a week-long trip.",
                context_patch=TripContextPatch(trip_duration_nights=7),
            ),
        ],
    )


def _party_size_clarification() -> TripClarification:
    return TripClarification(
        id="party-size",
        question="How many people is the total budget for?",
        reason="Total trip budget needs party size before per-person planning.",
        priority=80,
        options=[
            TripClarificationOption(
                id="solo",
                label="1 person",
                description="Plan the budget for one traveler.",
                context_patch=TripContextPatch(party_size=1),
            ),
            TripClarificationOption(
                id="couple",
                label="2 people",
                description="Plan the budget for two travelers.",
                context_patch=TripContextPatch(party_size=2),
            ),
            TripClarificationOption(
                id="family",
                label="4 people",
                description="Plan the budget for a family or small group.",
                context_patch=TripContextPatch(party_size=4),
            ),
        ],
    )


def _travel_origin_clarification() -> TripClarification:
    return TripClarification(
        id="travel-origin",
        question="Where will you travel from?",
        reason="Travel effort was mentioned without a starting point.",
        priority=70,
        options=[
            TripClarificationOption(
                id="add-origin",
                label="Add origin",
                description=(
                    "Capture a starting point for future travel-effort planning."
                ),
            ),
        ],
    )


def _mentions_travel_effort(query: str) -> bool:
    normalized = query.lower()
    return any(term in normalized for term in TRAVEL_EFFORT_TERMS)


def _build_assumptions(context: TripContext) -> list[str]:
    if context.budget_mode != "total_trip":
        return []
    return [
        "Travel cost is not included in total-trip budget planning until travel "
        "effort is implemented."
    ]
