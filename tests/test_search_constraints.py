from __future__ import annotations

from datetime import date

import pytest

from app.domain.search_constraints import (
    CandidateFeatureFact,
    CandidateLocation,
    CandidateLodgingEstimate,
    CandidatePassPrice,
    CandidateSeasonEvidence,
    CandidateTravelEvidence,
    ConstraintCandidateFacts,
    evaluate_search_constraints,
)
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    FactorRequirement,
    LocationScope,
    LodgingBudgetConstraint,
    PassPriceCeilingConstraint,
    SearchConstraints,
    SearchIntent,
    TravelLimitConstraint,
    TravelWindow,
)

pytestmark = pytest.mark.db_free


def _candidate(**updates: object) -> ConstraintCandidateFacts:
    values: dict[str, object] = {
        "candidate_id": "candidate",
        "location": CandidateLocation(
            country="France",
            region="Savoie",
            ski_region_ids=("region",),
            destination_id="destination",
        ),
    }
    values.update(updates)
    return ConstraintCandidateFacts.model_validate(values)


def test_location_and_source_backed_exact_season_are_hard_constraints() -> None:
    candidate = _candidate(
        season=CandidateSeasonEvidence(
            exact_windows=((date(2026, 12, 5), date(2027, 4, 18)),),
            recurring_start_month=12,
            recurring_end_month=4,
            trust_status="verified",
        )
    )

    accepted = evaluate_search_constraints(
        candidate=candidate,
        intent=SearchIntent(
            constraints=SearchConstraints(
                location=LocationScope(country="France"),
                travel_window=TravelWindow(
                    start_date=date(2027, 2, 10),
                    end_date=date(2027, 2, 15),
                ),
            )
        ),
    )
    rejected = evaluate_search_constraints(
        candidate=candidate,
        intent=SearchIntent(
            constraints=SearchConstraints(
                location=LocationScope(country="Austria"),
                travel_window=TravelWindow(
                    start_date=date(2027, 5, 10),
                    end_date=date(2027, 5, 15),
                ),
            )
        ),
    )

    assert accepted.eligible is True
    assert rejected.eligible is False
    assert {issue.code for issue in rejected.failures} == {
        "location_mismatch",
        "outside_season_window",
    }


def test_missing_or_untrusted_season_evidence_warns_without_false_exclusion() -> None:
    decision = evaluate_search_constraints(
        candidate=_candidate(
            season=CandidateSeasonEvidence(
                recurring_start_month=12,
                recurring_end_month=4,
                trust_status="needs_source",
            )
        ),
        intent=SearchIntent(
            constraints=SearchConstraints(travel_window=TravelWindow(month=2))
        ),
    )

    assert decision.eligible is True
    assert [warning.code for warning in decision.warnings] == [
        "season_evidence_uncertain"
    ]


@pytest.mark.parametrize(
    ("operation_status", "eligible", "failure_codes", "warning_codes"),
    (
        ("operating", True, set(), []),
        ("unavailable", False, {"outside_season_window"}, []),
        ("unverified", True, set(), ["season_evidence_uncertain"]),
    ),
)
def test_central_operation_status_overrides_raw_window_fallback(
    operation_status: str,
    eligible: bool,
    failure_codes: set[str],
    warning_codes: list[str],
) -> None:
    candidate = _candidate(
        season=CandidateSeasonEvidence(
            exact_windows=((date(2026, 12, 1), date(2026, 12, 31)),),
            recurring_start_month=12,
            recurring_end_month=4,
            trust_status="verified",
            operation_status=operation_status,
        )
    )

    decision = evaluate_search_constraints(
        candidate=candidate,
        intent=SearchIntent(
            constraints=SearchConstraints(
                travel_window=TravelWindow(
                    start_date=date(2027, 1, 10),
                    end_date=date(2027, 1, 12),
                )
            )
        ),
    )

    assert decision.eligible is eligible
    assert {issue.code for issue in decision.failures} == failure_codes
    assert [issue.code for issue in decision.warnings] == warning_codes


def test_lodging_budget_excludes_only_clear_non_overlap_and_never_missing_data() -> (
    None
):
    intent = SearchIntent(
        constraints=SearchConstraints(
            lodging_budget=LodgingBudgetConstraint(
                mode="lodging_nightly",
                maximum=200,
                currency="EUR",
            )
        )
    )
    inside = evaluate_search_constraints(
        candidate=_candidate(
            lodging=CandidateLodgingEstimate(
                mode="lodging_nightly",
                minimum=190,
                maximum=240,
                currency="EUR",
                trust_status="estimated",
                provenance="Catalog stay-base estimate.",
            )
        ),
        intent=intent,
    )
    outside = evaluate_search_constraints(
        candidate=_candidate(
            lodging=CandidateLodgingEstimate(
                mode="lodging_nightly",
                minimum=225,
                maximum=260,
                currency="EUR",
                trust_status="estimated",
                provenance="Catalog stay-base estimate.",
            )
        ),
        intent=intent,
    )
    missing = evaluate_search_constraints(candidate=_candidate(), intent=intent)

    assert inside.eligible is True
    assert outside.eligible is False
    assert outside.failures[0].code == "lodging_budget_clear_non_overlap"
    assert missing.eligible is True
    assert missing.warnings[0].code == "lodging_estimate_missing"


def test_travel_limit_requires_comparable_route_but_keeps_missing_route_visible() -> (
    None
):
    intent = SearchIntent(
        constraints=SearchConstraints(
            travel_limit=TravelLimitConstraint(
                maximum_duration_hours=15,
                mode="car",
            )
        )
    )
    too_far = evaluate_search_constraints(
        candidate=_candidate(
            travel=CandidateTravelEvidence(
                mode="car",
                duration_minutes=901,
                provenance="Routing provider.",
            )
        ),
        intent=intent,
    )
    missing = evaluate_search_constraints(candidate=_candidate(), intent=intent)

    assert too_far.eligible is False
    assert too_far.failures[0].code == "travel_limit_exceeded"
    assert missing.eligible is True
    assert missing.warnings[0].code == "travel_evidence_missing"


def test_verified_feature_requirement_rejects_unknown_or_weak_evidence() -> None:
    intent = SearchIntent(
        constraints=SearchConstraints(
            factor_requirements=(
                FactorRequirement(
                    factor_id="night_skiing",
                    minimum_trust="verified_with_adjustment",
                ),
            )
        )
    )
    verified = evaluate_search_constraints(
        candidate=_candidate(
            features=(
                CandidateFeatureFact(
                    factor_id="night_skiing",
                    availability="available",
                    trust_status="verified",
                ),
            )
        ),
        intent=intent,
    )
    weak = evaluate_search_constraints(
        candidate=_candidate(
            features=(
                CandidateFeatureFact(
                    factor_id="night_skiing",
                    availability="available",
                    trust_status="estimated",
                ),
            )
        ),
        intent=intent,
    )
    unknown = evaluate_search_constraints(candidate=_candidate(), intent=intent)

    assert verified.eligible is True
    assert weak.eligible is False
    assert weak.failures[0].code == "feature_trust_below_requirement"
    assert unknown.eligible is False
    assert unknown.failures[0].code == "required_feature_unknown"


def test_require_preference_becomes_a_verified_feature_constraint() -> None:
    intent = SearchIntent(
        factor_preferences=(
            FactorPreferencePatch(
                factor_id="snow_park",
                mode="require",
            ),
        )
    )

    decision = evaluate_search_constraints(candidate=_candidate(), intent=intent)

    assert decision.eligible is False
    assert decision.failures[0].code == "required_feature_unknown"


def test_pass_price_ceiling_uses_only_exact_comparable_slice() -> None:
    intent = SearchIntent(
        constraints=SearchConstraints(
            pass_price_ceiling=PassPriceCeilingConstraint(
                maximum=350,
                currency="EUR",
                duration_days=6,
                audience="adult",
                season="2026-2027",
            )
        )
    )
    decision = evaluate_search_constraints(
        candidate=_candidate(
            pass_prices=(
                CandidatePassPrice(
                    duration_days=6,
                    audience="adult",
                    amount_maximum=360,
                    currency="EUR",
                    season="2025-2026",
                    trust_status="verified",
                ),
                CandidatePassPrice(
                    duration_days=6,
                    audience="adult",
                    amount_maximum=340,
                    currency="EUR",
                    season="2026-2027",
                    trust_status="verified",
                ),
            )
        ),
        intent=intent,
    )

    assert decision.eligible is True
    assert not decision.failures

    missing = evaluate_search_constraints(candidate=_candidate(), intent=intent)
    assert missing.eligible is False
    assert missing.failures[0].code == "comparable_pass_price_missing"
