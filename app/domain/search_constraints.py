from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.domain.catalog_applicability import AreaOperationStatus
from app.domain.search_factors.models import FrozenMapping
from app.domain.search_v4_models import FactorRequirement, SearchIntent

TrustStatus = Literal[
    "verified",
    "verified_with_adjustment",
    "estimated",
    "needs_source",
]
Availability = Literal["available", "unavailable", "unknown"]
_NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")
_SOURCE_BACKED = frozenset({"verified", "verified_with_adjustment"})
_TRUST_ORDER = {
    "needs_source": 0,
    "estimated": 1,
    "verified_with_adjustment": 2,
    "verified": 3,
}


class _ConstraintModel(BaseModel):
    model_config = _MODEL_CONFIG


class CandidateLocation(_ConstraintModel):
    country: _NonBlankText
    region: _NonBlankText
    ski_region_ids: tuple[_NonBlankText, ...]
    destination_id: _NonBlankText


class CandidateSeasonEvidence(_ConstraintModel):
    exact_windows: tuple[tuple[date, date], ...] = ()
    recurring_start_month: int | None = Field(default=None, ge=1, le=12)
    recurring_end_month: int | None = Field(default=None, ge=1, le=12)
    trust_status: TrustStatus
    operation_status: AreaOperationStatus | None = None

    @model_validator(mode="after")
    def validate_season(self) -> Self:
        if (self.recurring_start_month is None) != (self.recurring_end_month is None):
            raise ValueError("recurring season months must be provided together")
        if any(end < start for start, end in self.exact_windows):
            raise ValueError("exact season window end must be on or after start")
        return self


class CandidateLodgingEstimate(_ConstraintModel):
    mode: Literal["lodging_nightly", "total_trip"]
    minimum: float = Field(ge=0)
    maximum: float = Field(ge=0)
    currency: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=3, max_length=3),
    ]
    trust_status: TrustStatus
    provenance: _NonBlankText

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.maximum < self.minimum:
            raise ValueError("lodging estimate maximum must be at least minimum")
        return self


class CandidateTravelEvidence(_ConstraintModel):
    mode: Literal["car", "rail", "public_transport", "flight"]
    duration_minutes: int = Field(gt=0)
    provenance: _NonBlankText


class CandidateFeatureFact(_ConstraintModel):
    factor_id: _NonBlankText
    availability: Availability
    trust_status: TrustStatus
    values: tuple[_NonBlankText, ...] = ()


class CandidatePassPrice(_ConstraintModel):
    duration_days: int = Field(gt=0)
    audience: _NonBlankText
    amount_maximum: float = Field(ge=0)
    currency: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=3, max_length=3),
    ]
    season: _NonBlankText
    trust_status: TrustStatus


class ConstraintCandidateFacts(_ConstraintModel):
    candidate_id: _NonBlankText
    location: CandidateLocation
    season: CandidateSeasonEvidence | None = None
    lodging: CandidateLodgingEstimate | None = None
    travel: CandidateTravelEvidence | None = None
    stay_quality_score: float | None = Field(default=None, ge=0, le=10)
    features: tuple[CandidateFeatureFact, ...] = ()
    pass_prices: tuple[CandidatePassPrice, ...] = ()

    @model_validator(mode="after")
    def validate_feature_ids(self) -> Self:
        ids = [feature.factor_id for feature in self.features]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate feature IDs must be unique")
        return self


class ConstraintIssue(_ConstraintModel):
    constraint_id: _NonBlankText
    code: _NonBlankText
    message: _NonBlankText
    details: FrozenMapping = Field(default_factory=dict)


class ConstraintDecision(_ConstraintModel):
    eligible: bool
    failures: tuple[ConstraintIssue, ...]
    warnings: tuple[ConstraintIssue, ...]
    evaluated_constraint_ids: tuple[str, ...]


def evaluate_search_constraints(
    *,
    candidate: ConstraintCandidateFacts,
    intent: SearchIntent,
) -> ConstraintDecision:
    failures: list[ConstraintIssue] = []
    warnings: list[ConstraintIssue] = []
    evaluated: list[str] = []
    constraints = intent.constraints

    if constraints.location is not None:
        evaluated.append("location_scope")
        if not _location_matches(candidate.location, constraints.location):
            failures.append(
                _issue(
                    "location_scope",
                    "location_mismatch",
                    "Candidate is outside the requested location scope.",
                )
            )

    if constraints.travel_window is not None:
        evaluated.append("season_viability")
        _evaluate_season(
            candidate=candidate,
            intent=intent,
            failures=failures,
            warnings=warnings,
        )

    if constraints.lodging_budget is not None:
        evaluated.append("lodging_budget")
        _evaluate_lodging(
            candidate=candidate,
            intent=intent,
            failures=failures,
            warnings=warnings,
        )

    if constraints.travel_limit is not None:
        evaluated.append("travel_limit")
        _evaluate_travel(
            candidate=candidate,
            intent=intent,
            failures=failures,
            warnings=warnings,
        )

    if constraints.minimum_stay_quality is not None:
        evaluated.append("minimum_stay_quality")
        threshold = constraints.minimum_stay_quality.minimum_score
        if candidate.stay_quality_score is None:
            warnings.append(
                _issue(
                    "minimum_stay_quality",
                    "stay_quality_estimate_missing",
                    "No comparable stay-quality estimate is available.",
                )
            )
        elif candidate.stay_quality_score < threshold:
            failures.append(
                _issue(
                    "minimum_stay_quality",
                    "stay_quality_below_minimum",
                    "Candidate is below the requested minimum stay quality.",
                    score=candidate.stay_quality_score,
                    minimum=threshold,
                )
            )

    existing_requirement_ids = {
        requirement.factor_id for requirement in constraints.factor_requirements
    }
    synthesized_requirements = tuple(
        FactorRequirement(
            factor_id=preference.factor_id,
            values=preference.values,
            minimum_trust="verified_with_adjustment",
        )
        for preference in intent.factor_preferences
        if preference.mode == "require"
        and preference.factor_id not in existing_requirement_ids
    )
    factor_requirements = (
        *constraints.factor_requirements,
        *synthesized_requirements,
    )
    if factor_requirements:
        evaluated.append("factor_requirement")
        _evaluate_feature_requirements(
            candidate=candidate,
            requirements=factor_requirements,
            failures=failures,
        )

    if constraints.pass_price_ceiling is not None:
        evaluated.append("pass_price_ceiling")
        _evaluate_pass_price(candidate=candidate, intent=intent, failures=failures)

    return ConstraintDecision(
        eligible=not failures,
        failures=tuple(failures),
        warnings=tuple(warnings),
        evaluated_constraint_ids=tuple(evaluated),
    )


def _location_matches(candidate: CandidateLocation, requested: object) -> bool:
    country = getattr(requested, "country")
    region = getattr(requested, "region")
    ski_region_ids = getattr(requested, "ski_region_ids")
    destination_ids = getattr(requested, "destination_ids")
    return (
        (country is None or _same_text(candidate.country, country))
        and (region is None or _same_text(candidate.region, region))
        and (
            not ski_region_ids
            or bool(set(candidate.ski_region_ids) & set(ski_region_ids))
        )
        and (not destination_ids or candidate.destination_id in destination_ids)
    )


def _evaluate_season(
    *,
    candidate: ConstraintCandidateFacts,
    intent: SearchIntent,
    failures: list[ConstraintIssue],
    warnings: list[ConstraintIssue],
) -> None:
    window = intent.constraints.travel_window
    assert window is not None
    evidence = candidate.season
    if evidence is not None and evidence.operation_status is not None:
        if evidence.operation_status == "unavailable":
            failures.append(
                _issue(
                    "season_viability",
                    "outside_season_window",
                    "Requested travel window is outside the source-backed ski season.",
                )
            )
        elif evidence.operation_status == "unverified":
            warnings.append(
                _issue(
                    "season_viability",
                    "season_evidence_uncertain",
                    "Season evidence is missing or not source-backed; "
                    "candidate remains eligible.",
                )
            )
        return
    if evidence is None or evidence.trust_status not in _SOURCE_BACKED:
        warnings.append(
            _issue(
                "season_viability",
                "season_evidence_uncertain",
                "Season evidence is missing or not source-backed; "
                "candidate remains eligible.",
            )
        )
        return
    matches = False
    if window.start_date is not None and window.end_date is not None:
        if evidence.exact_windows:
            matches = any(
                start <= window.start_date and window.end_date <= end
                for start, end in evidence.exact_windows
            )
        else:
            matches = _date_range_matches_recurring_months(
                window.start_date,
                window.end_date,
                evidence.recurring_start_month,
                evidence.recurring_end_month,
            )
    elif window.month is not None:
        matches = _month_is_in_recurring_window(
            window.month,
            evidence.recurring_start_month,
            evidence.recurring_end_month,
        ) or any(
            _exact_window_contains_month(start, end, window.month)
            for start, end in evidence.exact_windows
        )
    if not matches:
        failures.append(
            _issue(
                "season_viability",
                "outside_season_window",
                "Requested travel window is outside the source-backed ski season.",
            )
        )


def _evaluate_lodging(
    *,
    candidate: ConstraintCandidateFacts,
    intent: SearchIntent,
    failures: list[ConstraintIssue],
    warnings: list[ConstraintIssue],
) -> None:
    requested = intent.constraints.lodging_budget
    assert requested is not None
    estimate = candidate.lodging
    if estimate is None:
        warnings.append(
            _issue(
                "lodging_budget",
                "lodging_estimate_missing",
                "No lodging estimate is available; candidate remains eligible.",
            )
        )
        return
    if estimate.mode != requested.mode or not _same_text(
        estimate.currency, requested.currency
    ):
        warnings.append(
            _issue(
                "lodging_budget",
                "lodging_estimate_not_comparable",
                "Lodging estimate is not comparable to the requested budget.",
            )
        )
        return
    if estimate.minimum > requested.effective_maximum:
        failures.append(
            _issue(
                "lodging_budget",
                "lodging_budget_clear_non_overlap",
                "Estimated lodging range is clearly above the flexible budget ceiling.",
                estimate_minimum=estimate.minimum,
                estimate_maximum=estimate.maximum,
                requested_maximum=requested.maximum,
                effective_flex=requested.effective_flex,
                effective_maximum=requested.effective_maximum,
                provenance=estimate.provenance,
            )
        )


def _evaluate_travel(
    *,
    candidate: ConstraintCandidateFacts,
    intent: SearchIntent,
    failures: list[ConstraintIssue],
    warnings: list[ConstraintIssue],
) -> None:
    requested = intent.constraints.travel_limit
    assert requested is not None
    evidence = candidate.travel
    if evidence is None or evidence.mode != requested.mode:
        warnings.append(
            _issue(
                "travel_limit",
                "travel_evidence_missing",
                "No comparable route evidence is available; "
                "candidate remains eligible.",
            )
        )
        return
    maximum_minutes = requested.maximum_duration_hours * 60
    if evidence.duration_minutes > maximum_minutes:
        failures.append(
            _issue(
                "travel_limit",
                "travel_limit_exceeded",
                "Candidate exceeds the requested maximum travel duration.",
                duration_minutes=evidence.duration_minutes,
                maximum_duration_minutes=maximum_minutes,
                provenance=evidence.provenance,
            )
        )


def _evaluate_feature_requirements(
    *,
    candidate: ConstraintCandidateFacts,
    requirements: tuple[FactorRequirement, ...],
    failures: list[ConstraintIssue],
) -> None:
    facts = {fact.factor_id: fact for fact in candidate.features}
    for requirement in requirements:
        fact = facts.get(requirement.factor_id)
        if fact is None or fact.availability == "unknown":
            failures.append(
                _issue(
                    "factor_requirement",
                    "required_feature_unknown",
                    f"Required feature {requirement.factor_id} is not verified.",
                    factor_id=requirement.factor_id,
                )
            )
            continue
        if fact.availability == "unavailable":
            failures.append(
                _issue(
                    "factor_requirement",
                    "required_feature_unavailable",
                    f"Required feature {requirement.factor_id} is unavailable.",
                    factor_id=requirement.factor_id,
                )
            )
            continue
        if _TRUST_ORDER[fact.trust_status] < _TRUST_ORDER[requirement.minimum_trust]:
            failures.append(
                _issue(
                    "factor_requirement",
                    "feature_trust_below_requirement",
                    f"Required feature {requirement.factor_id} has insufficient trust.",
                    factor_id=requirement.factor_id,
                    trust_status=fact.trust_status,
                    minimum_trust=requirement.minimum_trust,
                )
            )
            continue
        if requirement.values and not set(requirement.values).intersection(fact.values):
            failures.append(
                _issue(
                    "factor_requirement",
                    "required_feature_value_mismatch",
                    f"Required feature {requirement.factor_id} does not match "
                    "requested values.",
                    factor_id=requirement.factor_id,
                    requested_values=requirement.values,
                    actual_values=fact.values,
                )
            )


def _evaluate_pass_price(
    *,
    candidate: ConstraintCandidateFacts,
    intent: SearchIntent,
    failures: list[ConstraintIssue],
) -> None:
    requested = intent.constraints.pass_price_ceiling
    assert requested is not None
    matching = [
        price
        for price in candidate.pass_prices
        if price.duration_days == requested.duration_days
        and _same_text(price.audience, requested.audience)
        and _same_text(price.currency, requested.currency)
        and _same_text(price.season, requested.season)
        and price.trust_status in _SOURCE_BACKED
    ]
    if not matching:
        failures.append(
            _issue(
                "pass_price_ceiling",
                "comparable_pass_price_missing",
                "No source-backed price matches the requested pass slice.",
            )
        )
        return
    lowest_maximum = min(price.amount_maximum for price in matching)
    if lowest_maximum > requested.maximum:
        failures.append(
            _issue(
                "pass_price_ceiling",
                "pass_price_ceiling_exceeded",
                "All comparable pass products exceed the requested price ceiling.",
                lowest_comparable_maximum=lowest_maximum,
                requested_maximum=requested.maximum,
            )
        )


def _issue(
    constraint_id: str,
    code: str,
    message: str,
    **details: object,
) -> ConstraintIssue:
    return ConstraintIssue(
        constraint_id=constraint_id,
        code=code,
        message=message,
        details=details,
    )


def _same_text(left: str, right: str) -> bool:
    return left.strip().casefold() == right.strip().casefold()


def _month_is_in_recurring_window(
    month: int,
    start_month: int | None,
    end_month: int | None,
) -> bool:
    if start_month is None or end_month is None:
        return False
    if start_month <= end_month:
        return start_month <= month <= end_month
    return month >= start_month or month <= end_month


def _date_range_matches_recurring_months(
    start: date,
    end: date,
    start_month: int | None,
    end_month: int | None,
) -> bool:
    current = start
    while current <= end:
        if not _month_is_in_recurring_window(current.month, start_month, end_month):
            return False
        current += timedelta(days=1)
    return True


def _exact_window_contains_month(start: date, end: date, month: int) -> bool:
    current = date(start.year, start.month, 1)
    end_month = date(end.year, end.month, 1)
    while current <= end_month:
        if current.month == month:
            return True
        current = (
            date(current.year + 1, 1, 1)
            if current.month == 12
            else date(current.year, current.month + 1, 1)
        )
    return False
