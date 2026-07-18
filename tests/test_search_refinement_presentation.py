from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

import app.domain.search_refinement_presentation as presentation_module
from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_policy import load_search_policy
from app.domain.search_refinement import (
    RefinementCandidateState,
    RefinementValidationError,
)
from app.domain.search_refinement_presentation import (
    RefinementPresentationPolicy,
    build_deterministic_refinement_fallback,
    load_refinement_presentation_policy,
    resolve_interaction_copy,
    semantic_refinement_question_id,
    validate_refinement_presentation_policy,
)
from app.domain.search_v4_models import SearchIntent

pytestmark = pytest.mark.db_free

_CONFIGURED_PUBLIC_COPY_FIELDS = (
    ("topics", "fallback_question"),
    ("topics", "fallback_reason"),
    ("answers", "label"),
    ("answers", "description"),
)

_SAFE_NON_DIRECTIVE_TRANSACTION_COPY = (
    "Pass purchase timing",
    "Lift-pass purchase planning",
    "Lift-pass purchase price comparison",
    "How important is pass purchase timing for your trip?",
    "Compare pass purchase timing as part of the ski-day plan.",
)

_ISOLATED_UNSAFE_PUBLIC_COPY = (
    (
        "url",
        "Details at https://example.com",
        "uri",
        "unsafe traveller-facing copy",
    ),
    (
        "external_action",
        "Follow this external offer",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "credential",
        "Password preference",
        "sensitive_request",
        "unsafe traveller-facing copy",
    ),
    (
        "payment",
        "Payment preference",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "contact",
        "Email preference",
        "sensitive_request",
        "unsafe traveller-facing copy",
    ),
    (
        "sensitive",
        "Passport preference",
        "sensitive_request",
        "unsafe traveller-facing copy",
    ),
    ("control", "Calm\0 choice", "control", "unsafe traveller-facing copy"),
    ("bidi", "Calm\u202e choice", "control", "unsafe traveller-facing copy"),
    (
        "unsupported_claim",
        "Best snow option",
        "unsupported_claim",
        "unsafe traveller-facing copy",
    ),
    (
        "machine_id_whole",
        "ischgl-ischgl--ischgl-ski-area--ischgl-vip-skipass",
        "machine_id",
        "unsafe traveller-facing copy",
    ),
    (
        "machine_id_embedded",
        "Prefer alps-region-premium-pass today",
        "machine_id",
        "unsafe traveller-facing copy",
    ),
    ("digit", "Option 2", "numeric_claim", "unsafe traveller-facing copy"),
    (
        "percent",
        "More than half %",
        "numeric_claim",
        "unsafe traveller-facing copy",
    ),
    ("internal", "Ranking preference", "blocked", "blocked traveller-facing copy"),
    (
        "ftp_uri",
        "Would you use ftp://example.com?",
        "uri",
        "unsafe traveller-facing copy",
    ),
    (
        "mailto_uri",
        "Continue at mailto:planning",
        "uri",
        "unsafe traveller-facing copy",
    ),
    (
        "custom_uri",
        "Continue at snowcast:preferences",
        "uri",
        "unsafe traveller-facing copy",
    ),
    (
        "bare_domain",
        "Details at example.com",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "nested_bare_domain",
        "Details at plans.example.co.uk",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "cvv",
        "Enter your CVV to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "cvc",
        "Enter your CVC to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "pin",
        "Enter your PIN to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "iban",
        "Enter your IBAN to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "bank_account",
        "Enter your bank account to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "routing_number",
        "Enter your routing number to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "wallet",
        "Enter your wallet details to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "reserve_action",
        "Reserve this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "book_action",
        "Book this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "buy_action",
        "Buy this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "purchase_action",
        "Purchase this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "pay_action",
        "Pay for this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "subscribe_action",
        "Subscribe for updates",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "download_action",
        "Download this guide",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "install_action",
        "Install this app",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "booking_it_domain",
        "Details at booking.it",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "booking_ski_domain",
        "Details at booking.ski",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "snowcast_ski_domain",
        "Details at snowcast.ski",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "example_xyz_domain",
        "Details at example.xyz",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "paypal_account",
        "Enter your PayPal account to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "googlepay_account",
        "Enter your GooglePay account to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "make_purchase",
        "Make a purchase now",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "complete_booking",
        "Complete this booking now",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "order_pass",
        "Order this lift pass now",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "proceed_checkout",
        "Proceed with checkout now",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "kindly_reserve",
        "Kindly reserve this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "immediately_book",
        "Immediately book this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "confirm_order",
        "Confirm this order today",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "place_order",
        "Place an order today",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "finish_checkout",
        "Finish the checkout today",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "start_subscription",
        "Start a subscription today",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "purchasing_inflection",
        "Purchasing this pass continues externally",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "booked_inflection",
        "Booked this option externally",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "buying_inflection",
        "Buying this option continues externally",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "paid_inflection",
        "Paid for this option externally",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "ordering_inflection",
        "Ordering this option continues externally",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "subscribed_inflection",
        "Subscribed for updates externally",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "downloaded_inflection",
        "Downloaded this guide externally",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "installing_inflection",
        "Installing this app continues externally",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "safe_phrase_with_transaction_trigger",
        "Make pass purchase timing final now",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "safe_phrase_with_urgency",
        "Immediately review lift-pass purchase planning",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "snowcast_unicode_domain",
        "Details at snowcast.рф",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "unicode_domain",
        "Details at пример.рф",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "idna_unicode_domain",
        "Details at bücher.example",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "decomposed_idna_unicode_domain",
        "Details at bu\u0308cher.example",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "idna_ideographic_dot_domain",
        "Details at snowcast。рф",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "idna_fullwidth_dot_domain",
        "Details at snowcast．рф",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "idna_halfwidth_dot_domain",
        "Details at snowcast｡рф",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "idna_mixed_dot_domain",
        "Details at plans。snowcast．рф",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "wise_account",
        "Enter your Wise account to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "skrill_account",
        "Enter your Skrill account to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "account_login",
        "Enter your account login to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "provide_username",
        "Provide your username to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "share_sign_in",
        "Share your sign-in to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "create_account",
        "Create an account to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "send_login",
        "Send your login to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "submit_payment_account",
        "Submit your payment-account to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "continue_with_account",
        "Continue with your account.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "provide_log_in",
        "Provide your log-in to continue.",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "sign_in_account",
        "Sign in to your account",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "log_in_account",
        "Log in to your account",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "connect_account",
        "Connect your account",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "use_account",
        "Use your account",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "bare_username",
        "Username preference",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "bare_login",
        "Login preference",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "bare_sign_in",
        "Sign-in preference",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "bare_log_in",
        "Log in preference",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "preorder",
        "Preorder this lift pass now",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "rebook",
        "Rebook this option now",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "checking_out",
        "Checking out this pass now",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "sign_up",
        "Sign up for updates now",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "register_account",
        "Register this account now",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "preordered_inflection",
        "Preordered this lift pass",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "rebooking_inflection",
        "Rebooking this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "checked_out_inflection",
        "Checked out this pass",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "signing_up_inflection",
        "Signing up for updates",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "prebook_compound",
        "Prebook this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "prebook_exact",
        "Prebook",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "prebooked_compound",
        "Prebooked this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "prebooking_compound",
        "Prebooking this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "repurchase_compound",
        "Repurchase this pass",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "repurchase_exact",
        "Repurchase",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "repurchased_compound",
        "Repurchased this pass",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "repurchasing_compound",
        "Repurchasing this pass",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "reorder_compound",
        "Reorder this lift pass",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "resubscribe_compound",
        "Resubscribe for updates",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "closed_signup",
        "Signup for updates",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "closed_signup_exact",
        "Signup",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "closed_signups",
        "Signups remain open",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "sign_optional_token_up",
        "Sign yourself up",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "signing_optional_token_up",
        "Signing yourself up",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "opt_in",
        "Opt in for updates",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "opt_in_exact",
        "Opt in",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "opt_optional_token_in",
        "Opt yourself in",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "check_optional_token_out",
        "Check yourself out",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "register_outward",
        "Register for updates",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "registers_outward",
        "Registers for updates",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "registered_outward",
        "Registered for updates",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "registering_outward",
        "Registering for updates",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "safe_context_checkout_tail",
        "Lift-pass purchase planning then checking out this pass",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "safe_context_rebook_tail",
        "Pass purchase timing plus rebook this option",
        "external_action",
        "unsafe traveller-facing copy",
    ),
    (
        "safe_context_domain_tail",
        "Pass purchase timing at snowcast.рф",
        "bare_domain",
        "unsafe traveller-facing copy",
    ),
    (
        "safe_context_provider_tail",
        "Lift-pass purchase planning with PayPal",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
    (
        "safe_context_account_tail",
        "Pass purchase timing with your account",
        "payment_credential",
        "unsafe traveller-facing copy",
    ),
)


def _evaluation(factor_id: str, utility: float, *, cap: float = 1) -> FactorEvaluation:
    return FactorEvaluation(
        factor_id=factor_id,
        scope="test",
        entity_ids=("candidate",),
        raw_value=utility,
        raw_utility=utility,
        neutral_utility=0.5,
        effective_evidence_cap=cap,
        evidence_cap_components={"test": cap},
        warnings=(),
        provenance_summary="Test evidence.",
        explanation_inputs={},
    )


def _fallback_candidates() -> tuple[RefinementCandidateState, ...]:
    return tuple(
        RefinementCandidateState(
            candidate_id=candidate_id,
            evaluations=(
                _evaluation("trip_window_snow_fit", 0.7),
                _evaluation("accessible_terrain_scale", terrain),
                _evaluation("stay_base_access", access),
                _evaluation("development_style", development),
            ),
        )
        for candidate_id, terrain, access, development in (
            ("traditional-base", 0.2, 0.3, 1.0),
            ("planned-base", 1.0, 0.9, 0.0),
            ("mixed-base", 0.6, 0.6, 0.5),
        )
    )


def test_default_registry_covers_every_active_clarifiable_factor() -> None:
    search_policy = load_search_policy()
    presentation = load_refinement_presentation_policy()
    expected = {
        factor.factor_id
        for factor in search_policy.factors
        if factor.lifecycle == "active"
        and factor.clarifiable
        and "clarification" in factor.roles
    }
    assert {topic.factor_id for topic in presentation.topics} == expected


def test_default_registry_registers_safe_question_phrases_for_every_topic() -> None:
    presentation = load_refinement_presentation_policy()

    assert len(presentation.topics) == 18
    assert all(topic.question_phrases for topic in presentation.topics)
    assert len(
        {phrase for topic in presentation.topics for phrase in topic.question_phrases}
    ) == sum(len(topic.question_phrases) for topic in presentation.topics)


def test_default_registry_visible_copy_rejects_blocked_audience_terms() -> None:
    presentation = load_refinement_presentation_policy()
    visible_copy = [
        *(topic.fallback_question for topic in presentation.topics),
        *(topic.fallback_reason for topic in presentation.topics),
        *(answer.label for answer in presentation.answers),
        *(answer.description for answer in presentation.answers),
    ]

    for text in visible_copy:
        assert not presentation_module._contains_blocked_token(
            text, presentation.blocked_copy_terms
        ), text


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("topics", "fallback_question"),
        ("topics", "fallback_reason"),
        ("answers", "label"),
        ("answers", "description"),
    ],
)
def test_registry_validation_rejects_blocked_visible_copy(
    section: str,
    field: str,
) -> None:
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    payload[section][0][field] = "Internal optimisation objective"
    configured = RefinementPresentationPolicy.model_validate(payload)

    with pytest.raises(ValueError, match="blocked traveller-facing copy"):
        validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("section", "field", "unsafe_copy"),
    (
        (
            "topics",
            "fallback_question",
            "Would you visit https://example.com/offer?\u202e",
        ),
        (
            "topics",
            "fallback_reason",
            "Send your passport now.\0",
        ),
        (
            "answers",
            "label",
            "Book the guaranteed best option",
        ),
        (
            "answers",
            "description",
            "Share payment details for candidate-a at one hundred percent.",
        ),
    ),
)
def test_registry_validation_rejects_unsafe_public_copy(
    section: str,
    field: str,
    unsafe_copy: str,
) -> None:
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    payload[section][0][field] = unsafe_copy
    configured = RefinementPresentationPolicy.model_validate(payload)

    with pytest.raises(ValueError, match="unsafe traveller-facing copy"):
        validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("section", "field"),
    _CONFIGURED_PUBLIC_COPY_FIELDS,
    ids=("fallback-question", "fallback-reason", "answer-label", "answer-description"),
)
@pytest.mark.parametrize(
    ("category", "unsafe_copy", "expected_violation", "error"),
    _ISOLATED_UNSAFE_PUBLIC_COPY,
    ids=tuple(case[0] for case in _ISOLATED_UNSAFE_PUBLIC_COPY),
)
def test_every_configured_public_copy_field_rejects_each_isolated_unsafe_category(
    section: str,
    field: str,
    category: str,
    unsafe_copy: str,
    expected_violation: str,
    error: str,
) -> None:
    presentation = load_refinement_presentation_policy()
    assert (
        presentation_module._public_copy_safety_violation(
            unsafe_copy,
            blocked_tokens=presentation.blocked_copy_terms,
        )
        == expected_violation
    ), category
    payload = presentation.model_dump(mode="python")
    payload[section][0][field] = unsafe_copy
    configured = RefinementPresentationPolicy.model_validate(payload)

    with pytest.raises(ValueError, match=error):
        validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("section", "field", "safe_copy"),
    (
        (
            "topics",
            "fallback_question",
            "Would a purpose-built ski-day base suit you?",
        ),
        (
            "topics",
            "fallback_reason",
            "A purpose-built ski-day base can shape your trip.",
        ),
        ("answers", "label", "Purpose-built ski-day base"),
        (
            "answers",
            "description",
            "Prefer a purpose-built base for the ski-day routine.",
        ),
    ),
)
def test_configured_public_copy_allows_natural_single_hyphen_words(
    section: str,
    field: str,
    safe_copy: str,
) -> None:
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    payload[section][0][field] = safe_copy
    configured = RefinementPresentationPolicy.model_validate(payload)

    validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("section", "field", "safe_copy"),
    (
        (
            "topics",
            "fallback_question",
            "Would you compare pass choices for this trip?",
        ),
        (
            "topics",
            "fallback_reason",
            "Your route choice can shape the ski-day plan.",
        ),
        ("answers", "label", "Compare travel options"),
        (
            "answers",
            "description",
            "Compare pass purchase timing as part of the ski-day plan.",
        ),
    ),
)
def test_configured_public_copy_allows_ordinary_planning_vocabulary(
    section: str,
    field: str,
    safe_copy: str,
) -> None:
    presentation = load_refinement_presentation_policy()
    assert (
        presentation_module._public_copy_safety_violation(
            safe_copy,
            blocked_tokens=presentation.blocked_copy_terms,
        )
        is None
    )
    payload = presentation.model_dump(mode="python")
    payload[section][0][field] = safe_copy
    configured = RefinementPresentationPolicy.model_validate(payload)

    validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("section", "field"),
    _CONFIGURED_PUBLIC_COPY_FIELDS,
    ids=("fallback-question", "fallback-reason", "answer-label", "answer-description"),
)
@pytest.mark.parametrize("safe_copy", _SAFE_NON_DIRECTIVE_TRANSACTION_COPY)
def test_every_configured_public_copy_field_allows_narrow_purchase_planning_contexts(
    section: str,
    field: str,
    safe_copy: str,
) -> None:
    presentation = load_refinement_presentation_policy()
    assert (
        presentation_module._public_copy_safety_violation(
            safe_copy,
            blocked_tokens=presentation.blocked_copy_terms,
        )
        is None
    )
    payload = presentation.model_dump(mode="python")
    payload[section][0][field] = safe_copy
    configured = RefinementPresentationPolicy.model_validate(payload)

    validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("section", "field", "safe_copy"),
    (
        ("topics", "fallback_question", "Would you compare terrain, e.g. by size?"),
        (
            "topics",
            "fallback_reason",
            "Your answer can compare the piste map and village plan.",
        ),
        ("answers", "label", "Compare pass planning"),
        (
            "answers",
            "description",
            "Review the ski-day plan before choosing a preference.",
        ),
    ),
)
def test_configured_public_copy_allows_safe_non_hostname_planning_copy(
    section: str,
    field: str,
    safe_copy: str,
) -> None:
    presentation = load_refinement_presentation_policy()
    assert (
        presentation_module._public_copy_safety_violation(
            safe_copy,
            blocked_tokens=presentation.blocked_copy_terms,
        )
        is None
    )
    payload = presentation.model_dump(mode="python")
    payload[section][0][field] = safe_copy
    configured = RefinementPresentationPolicy.model_validate(payload)

    validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("section", "field"),
    _CONFIGURED_PUBLIC_COPY_FIELDS,
    ids=("fallback-question", "fallback-reason", "answer-label", "answer-description"),
)
def test_every_configured_public_copy_field_allows_ordinary_dotted_language(
    section: str,
    field: str,
) -> None:
    safe_copy = "Would you compare terrain, e.g. by size?"
    presentation = load_refinement_presentation_policy()
    assert (
        presentation_module._public_copy_safety_violation(
            safe_copy,
            blocked_tokens=presentation.blocked_copy_terms,
        )
        is None
    )
    payload = presentation.model_dump(mode="python")
    payload[section][0][field] = safe_copy
    configured = RefinementPresentationPolicy.model_validate(payload)

    validate_refinement_presentation_policy(configured, load_search_policy())


def test_registry_copy_resolves_to_typed_actions() -> None:
    presentation = load_refinement_presentation_policy()
    resolved = presentation.resolve_answer_ids(
        ["development_style.traditional", "local_pace.quiet"]
    )
    assert resolved.label == "Traditional mountain village + Quiet and relaxed"
    assert resolved.description == (
        "Prefer a base with traditional settlement character. "
        "Prefer a calm base rather than a lively one."
    )
    assert [item.factor_id for item in resolved.factor_preferences] == [
        "development_style",
        "local_pace",
    ]


def test_apres_answer_descriptions_name_their_distinct_contexts() -> None:
    presentation = load_refinement_presentation_policy()

    ski_day = presentation.answer_by_id["ski_day_apres.low_key"]
    local = presentation.answer_by_id["local_apres.low_key"]

    assert ski_day.description == "Prefer low-key ski-day après."
    assert local.description == (
        "Prefer a low-key evening near the accommodation base."
    )


def test_safe_dynamic_interaction_copy_survives_unchanged() -> None:
    presentation = load_refinement_presentation_policy()
    question = "What kind of place would you prefer to stay in?"

    assert resolve_interaction_copy(
        question,
        ("development_style",),
        ("candidate-a", "candidate-b"),
        presentation,
    ) == (
        question,
        "Your preferred village or resort style can change which stay base "
        "fits you best.",
    )


@pytest.mark.parametrize(
    "question",
    [
        "How should trip viability influence your ranking?",
        "Should factor development_style have more weight?",
        "Would changing this score reorder candidate-a?",
        "Would 25% more evidence change the result?",
        "Would candidate-b suit you best?",
        "Would option 2 suit you best?",
        "Choose the atmosphere you want?",
        "What kind of place would you prefer to stay in",
        "What " + ("very " * 100) + "long preference matters?",
    ],
)
def test_unsafe_dynamic_question_uses_topic_fallback(question: str) -> None:
    presentation = load_refinement_presentation_policy()

    resolved = resolve_interaction_copy(
        question,
        ("development_style",),
        ("candidate-a", "candidate-b"),
        presentation,
    )

    assert resolved == (
        "What kind of place would you prefer to stay in?",
        "Your preferred village or resort style can change which stay base "
        "fits you best.",
    )


def test_reason_is_always_server_owned_without_discarding_safe_question() -> None:
    presentation = load_refinement_presentation_policy()
    question = "What kind of place would you prefer to stay in?"

    resolved = resolve_interaction_copy(
        question,
        ("development_style",),
        ("candidate-a", "candidate-b"),
        presentation,
    )

    assert resolved == (
        question,
        "Your preferred village or resort style can change which stay base "
        "fits you best.",
    )


def test_multiple_topics_use_generic_copy_only_for_unsafe_fields() -> None:
    presentation = load_refinement_presentation_policy()

    assert resolve_interaction_copy(
        "How should ranking weight affect candidate-a?",
        ("accessible_terrain_scale", "stay_base_access"),
        ("candidate-a",),
        presentation,
    ) == (
        "Which of these trip preferences matters most to you?",
        "Your answer can distinguish otherwise similar trip options.",
    )


def test_blocked_terms_and_candidate_ids_match_whole_tokens_only() -> None:
    presentation = load_refinement_presentation_policy()
    question = "Which traditional mountain village or resort would you prefer?"

    assert resolve_interaction_copy(
        question,
        ("development_style",),
        ("large",),
        presentation,
    ) == (
        question,
        "Your preferred village or resort style can change which stay base "
        "fits you best.",
    )


def test_factual_selected_topic_question_uses_registered_fallback() -> None:
    presentation = load_refinement_presentation_policy()

    assert resolve_interaction_copy(
        "Is snowmaking backup dependable?",
        ("snowmaking_availability", "trip_window_snow_fit"),
        (),
        presentation,
    ) == (
        "Which of these trip preferences matters most to you?",
        "Your answer can distinguish otherwise similar trip options.",
    )
    assert (
        resolve_interaction_copy(
            "Is snowmaking backup important?",
            ("snowmaking_availability",),
            (),
            presentation,
        )[0]
        == "Would snowmaking backup matter if natural snow looks weak?"
    )


@pytest.mark.parametrize(
    "question",
    [
        "Would you prefer only options?",
        "Does dependable snow from glacier terrain matter for your trip?",
        "Is dependable snow from glacier terrain important for your trip?",
        "Are dependable snow conditions from glacier terrain important for your trip?",
        "How important is dependable snow from glacier terrain for your trip?",
        (
            "How important are dependable snow conditions from glacier terrain for "
            "your trip?"
        ),
        "Would dependable snow conditions from glacier terrain improve your trip?",
        "Would glacier terrain for dependable snow conditions matter to you?",
        "Would glacier terrain improve dependable snow conditions for your trip?",
    ],
)
def test_dynamic_question_rejects_unregistered_semantic_compositions(
    question: str,
) -> None:
    presentation = load_refinement_presentation_policy()

    assert (
        resolve_interaction_copy(
            question,
            ("night_skiing", "glacier_terrain")
            if question == "Would you prefer only options?"
            else ("trip_window_snow_fit", "glacier_terrain"),
            (),
            presentation,
        )[0]
        == "Which of these trip preferences matters most to you?"
    )


def test_dynamic_question_accepts_registered_two_topic_comparison() -> None:
    presentation = load_refinement_presentation_policy()
    question = (
        "Would you rather have more terrain on your selected pass or easier access "
        "from where you stay?"
    )

    assert (
        resolve_interaction_copy(
            question,
            ("accessible_terrain_scale", "stay_base_access"),
            (),
            presentation,
        )[0]
        == question
    )


@pytest.mark.parametrize("connector", ["or", "versus", "rather than"])
def test_dynamic_question_accepts_only_controlled_comparison_connectors(
    connector: str,
) -> None:
    presentation = load_refinement_presentation_policy()
    question = (
        f"Would you prefer selected pass terrain {connector} "
        "access from your accommodation base?"
    )

    assert (
        resolve_interaction_copy(
            question,
            ("accessible_terrain_scale", "stay_base_access"),
            (),
            presentation,
        )[0]
        == question
    )

    assert (
        resolve_interaction_copy(
            "Would you prefer selected pass terrain and access from your "
            "accommodation base?",
            ("accessible_terrain_scale", "stay_base_access"),
            (),
            presentation,
        )[0]
        == "Which of these trip preferences matters most to you?"
    )


@pytest.mark.parametrize(
    ("topic_ids", "question"),
    [
        (
            ("trip_window_snow_fit",),
            "How important are dependable snow conditions for your trip?",
        ),
        (
            ("pass_price_per_day",),
            "How much should lift-pass price influence your choice?",
        ),
        (
            ("accessible_terrain_scale",),
            "Would you prefer more terrain covered by the selected pass?",
        ),
        (
            ("pass_terrain_value",),
            "Would you rather maximise terrain covered for the pass price?",
        ),
        (
            ("night_skiing",),
            "Would recurring night skiing add value to your trip?",
        ),
        (
            ("glacier_terrain",),
            "Does glacier terrain matter to you?",
        ),
        (
            ("trip_window_snow_fit",),
            "Are dependable snow conditions important to you?",
        ),
        (
            ("development_style",),
            "What kind of village or resort development style would you prefer?",
        ),
        (
            ("development_style",),
            "Which traditional mountain village would you choose?",
        ),
        (
            ("stay_base_access",),
            "How easy should access from your accommodation base be?",
        ),
    ],
)
def test_registered_preference_question_forms_accept_safe_paraphrases(
    topic_ids: tuple[str, ...],
    question: str,
) -> None:
    presentation = load_refinement_presentation_policy()

    assert (
        resolve_interaction_copy(
            question,
            topic_ids,
            (),
            presentation,
        )[0]
        == question
    )


@pytest.mark.parametrize(
    ("topic_ids", "question", "fallback_question"),
    [
        (
            ("stay_base_access",),
            "Would your accommodation base have easy access to the slopes?",
            "How easy should it be to reach the slopes from where you stay?",
        ),
        (
            ("glacier_terrain", "trip_window_snow_fit"),
            (
                "Does glacier terrain have dependable snow conditions for your "
                "trip, and does this matter?"
            ),
            "Which of these trip preferences matters most to you?",
        ),
        (
            ("glacier_terrain", "trip_window_snow_fit"),
            (
                "Does glacier terrain have dependable snow conditions for your trip "
                "and is this important?"
            ),
            "Which of these trip preferences matters most to you?",
        ),
        (
            ("glacier_terrain", "trip_window_snow_fit"),
            (
                "Does glacier terrain have dependable snow conditions for your trip "
                "and is this a priority?"
            ),
            "Which of these trip preferences matters most to you?",
        ),
        (
            ("glacier_terrain", "trip_window_snow_fit"),
            (
                "Does glacier terrain have dependable snow conditions for your trip "
                "and does this matter?"
            ),
            "Which of these trip preferences matters most to you?",
        ),
        (
            ("glacier_terrain",),
            "Would glacier terrain matter to you improve your trip?",
            "Does glacier terrain matter for this trip?",
        ),
    ],
)
def test_dynamic_question_rejects_factual_or_appended_preference_clauses(
    topic_ids: tuple[str, ...],
    question: str,
    fallback_question: str,
) -> None:
    presentation = load_refinement_presentation_policy()

    assert (
        resolve_interaction_copy(
            question,
            topic_ids,
            (),
            presentation,
        )[0]
        == fallback_question
    )


def test_configured_fallback_questions_bypass_generated_copy_grammar() -> None:
    presentation = load_refinement_presentation_policy()

    validate_refinement_presentation_policy(presentation, load_search_policy())
    for topic in presentation.topics:
        assert (
            resolve_interaction_copy(
                "This is not a generated preference question.",
                (topic.topic_id,),
                (),
                presentation,
            )[0]
            == topic.fallback_question
        )


@pytest.mark.parametrize(
    "symbol",
    ["💳", "€", "$", "=", "→", "/"],
)
def test_dynamic_question_rejects_symbols_outside_the_character_policy(
    symbol: str,
) -> None:
    presentation = load_refinement_presentation_policy()

    assert (
        resolve_interaction_copy(
            f"Would you prefer traditional mountain village {symbol} or resort?",
            ("development_style",),
            (),
            presentation,
        )[0]
        == "What kind of place would you prefer to stay in?"
    )


@pytest.mark.parametrize("apostrophe", ["'", "’", "‘"])
def test_dynamic_question_allows_registered_minimal_punctuation(
    apostrophe: str,
) -> None:
    presentation = load_refinement_presentation_policy()
    question = "Would you prefer a traditional mountain village?"

    assert presentation_module._has_only_allowed_question_characters(
        f"traveller{apostrophe}s preference?"
    )
    assert (
        resolve_interaction_copy(
            question,
            ("development_style",),
            (),
            presentation,
        )[0]
        == question
    )


@pytest.mark.parametrize("separator", [",", ";", ":"])
def test_dynamic_question_rejects_clause_separators(separator: str) -> None:
    presentation = load_refinement_presentation_policy()

    assert (
        resolve_interaction_copy(
            (
                "Would you prefer a traditional mountain village"
                f"{separator} or a purpose-built ski resort?"
            ),
            ("development_style",),
            (),
            presentation,
        )[0]
        == "What kind of place would you prefer to stay in?"
    )


def test_sensitive_marker_anywhere_in_brief_forces_registered_fallback() -> None:
    presentation = load_refinement_presentation_policy()

    assert (
        resolve_interaction_copy(
            "What traditional mountain village would you prefer?",
            ("development_style",),
            (),
            presentation,
            untrusted_brief="password is blue traditional mountain village",
        )[0]
        == "What kind of place would you prefer to stay in?"
    )


def test_registry_fallback_uses_first_material_topic_and_authoritative_copy() -> None:
    presentation = load_refinement_presentation_policy()
    fallback = build_deterministic_refinement_fallback(
        intent=SearchIntent(),
        candidates=_fallback_candidates(),
        policy=load_search_policy(),
        presentation=presentation,
    )

    assert fallback is not None
    development_topic = presentation.topic_by_id["development_style"]
    assert fallback.proposal.question_id == semantic_refinement_question_id(
        topic_ids=(development_topic.topic_id,),
        answer_id_sets=tuple(
            (answer_id,) for answer_id in development_topic.fallback_answer_ids
        ),
        presentation=presentation,
    )
    assert (
        fallback.proposal.question == "What kind of place would you prefer to stay in?"
    )
    assert fallback.proposal.reason == (
        "Your preferred village or resort style can change which stay base "
        "fits you best."
    )
    assert [option.label for option in fallback.proposal.options] == [
        "Traditional mountain village",
        "A mix of old and new",
        "Purpose-built ski resort",
        "It doesn't matter",
    ]
    assert fallback.impact.material is True


def test_registry_fallback_returns_none_without_actionable_trusted_variation() -> None:
    candidates = tuple(
        RefinementCandidateState(
            candidate_id=f"unknown-{index}",
            evaluations=(
                _evaluation("trip_window_snow_fit", 0.5, cap=0),
                _evaluation("accessible_terrain_scale", utility, cap=0),
                _evaluation("stay_base_access", 1 - utility, cap=0),
                _evaluation("development_style", utility, cap=0),
            ),
        )
        for index, utility in enumerate((0.2, 0.6, 1.0))
    )

    assert (
        build_deterministic_refinement_fallback(
            intent=SearchIntent(),
            candidates=candidates,
            policy=load_search_policy(),
            presentation=load_refinement_presentation_policy(),
        )
        is None
    )


def test_registry_fallback_suppresses_answered_semantic_id() -> None:
    presentation = load_refinement_presentation_policy()
    first = build_deterministic_refinement_fallback(
        intent=SearchIntent(),
        candidates=_fallback_candidates(),
        policy=load_search_policy(),
        presentation=presentation,
    )
    assert first is not None

    next_fallback = build_deterministic_refinement_fallback(
        intent=SearchIntent(),
        candidates=_fallback_candidates(),
        policy=load_search_policy(),
        presentation=presentation,
        already_answered_question_ids=frozenset({first.proposal.question_id}),
    )

    assert next_fallback is None or next_fallback.proposal.question_id != (
        first.proposal.question_id
    )


def test_registry_fallback_tries_every_topic_before_returning_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted_ids: list[str] = []

    def reject(*, proposal: object, **_kwargs: object) -> None:
        attempted_ids.append(getattr(proposal, "question_id"))
        raise RefinementValidationError("not material")

    monkeypatch.setattr(presentation_module, "validate_refinement_proposal", reject)
    presentation = load_refinement_presentation_policy()

    assert (
        build_deterministic_refinement_fallback(
            intent=SearchIntent(),
            candidates=_fallback_candidates(),
            policy=load_search_policy(),
            presentation=presentation,
        )
        is None
    )
    assert len(attempted_ids) == len(presentation.topics)


def test_registry_fallback_does_not_swallow_configuration_errors() -> None:
    presentation = load_refinement_presentation_policy()
    development_topic = next(
        topic for topic in presentation.topics if topic.topic_id == "development_style"
    ).model_copy(update={"fallback_answer_ids": ("missing.answer", "also.missing")})
    broken = presentation.model_copy(
        update={
            "topics": tuple(
                development_topic if topic.topic_id == "development_style" else topic
                for topic in presentation.topics
            )
        }
    )

    with pytest.raises(KeyError, match="unknown refinement answer ID"):
        build_deterministic_refinement_fallback(
            intent=SearchIntent(),
            candidates=_fallback_candidates(),
            policy=load_search_policy(),
            presentation=broken,
        )


def test_registry_fallback_does_not_swallow_pydantic_construction_errors() -> None:
    presentation = load_refinement_presentation_policy()
    broken = presentation.model_copy(
        update={
            "topics": tuple(
                topic.model_copy(update={"fallback_question": "x" * 501})
                for topic in presentation.topics
            )
        }
    )

    with pytest.raises(ValidationError, match="question"):
        build_deterministic_refinement_fallback(
            intent=SearchIntent(),
            candidates=_fallback_candidates(),
            policy=load_search_policy(),
            presentation=broken,
        )


@pytest.mark.parametrize(
    ("field", "maximum"),
    [
        ("label", 80),
        ("description", 240),
    ],
)
def test_registry_rejects_fallback_option_copy_exceeding_search_policy_bounds(
    field: str,
    maximum: int,
) -> None:
    presentation = load_refinement_presentation_policy()
    payload = presentation.model_dump(mode="python")
    payload["answers"][0][field] = "x" * (maximum + 1)
    configured = RefinementPresentationPolicy.model_validate(payload)

    with pytest.raises(ValueError, match=f"max_option_{field}_characters"):
        validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("field", "maximum"),
    [
        ("label", 80),
        ("description", 240),
    ],
)
def test_registry_accepts_fallback_option_copy_at_search_policy_bounds(
    field: str,
    maximum: int,
) -> None:
    presentation = load_refinement_presentation_policy()
    payload = presentation.model_dump(mode="python")
    payload["answers"][0][field] = "x" * maximum
    configured = RefinementPresentationPolicy.model_validate(payload)

    validate_refinement_presentation_policy(configured, load_search_policy())


@pytest.mark.parametrize(
    ("section", "field", "maximum"),
    [
        ("topics", "fallback_question", 280),
        ("topics", "fallback_reason", 500),
        ("answers", "label", 500),
        ("answers", "description", 500),
    ],
)
def test_registry_rejects_copy_exceeding_public_bounds(
    section: str,
    field: str,
    maximum: int,
) -> None:
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    payload[section][0][field] = "x" * (maximum + 1)

    with pytest.raises(ValidationError, match=field):
        RefinementPresentationPolicy.model_validate(payload)


def test_registry_resolves_task_2_provider_answer_ids() -> None:
    presentation = load_refinement_presentation_policy()

    resolved = presentation.resolve_answer_ids(
        [
            "accessible_terrain_scale.as_much_as_possible",
            "stay_base_access.as_easy_as_possible",
        ]
    )

    assert resolved.answer_ids == (
        "accessible_terrain_scale.as_much_as_possible",
        "stay_base_access.as_easy_as_possible",
    )
    assert [item.factor_id for item in resolved.factor_preferences] == [
        "accessible_terrain_scale",
        "stay_base_access",
    ]


def test_provider_topics_expose_only_approved_copy_for_allowed_factors() -> None:
    presentation = load_refinement_presentation_policy()

    topics = presentation.provider_topics(frozenset({"development_style"}))

    assert len(topics) == 1
    topic = topics[0]
    assert topic["topic_id"] == "development_style"
    assert topic["question_phrases"] == (
        "village or resort development style",
        "traditional mountain village",
        "a traditional mountain village",
        "traditional mountain village or resort",
    )
    assert topic["answers"] == (
        {
            "answer_id": "development_style.traditional",
            "label": "Traditional mountain village",
            "description": ("Prefer a base with traditional settlement character."),
        },
        {
            "answer_id": "development_style.mixed",
            "label": "A mix of old and new",
            "description": (
                "Prefer a base with a mix of old and new settlement character."
            ),
        },
        {
            "answer_id": "development_style.planned_resort",
            "label": "Purpose-built ski resort",
            "description": "Prefer a purpose-built ski resort base.",
        },
        {
            "answer_id": "development_style.ignore",
            "label": "It doesn't matter",
            "description": (
                "Do not use the village or resort development style as an "
                "extra preference."
            ),
        },
    )


def test_registry_rejects_duplicate_topic_and_answer_ids() -> None:
    search_policy = load_search_policy()
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    duplicate_topic = deepcopy(payload)
    duplicate_topic["topics"] = (
        *duplicate_topic["topics"],
        duplicate_topic["topics"][0],
    )
    with pytest.raises(ValueError, match="topic IDs must be unique"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(duplicate_topic), search_policy
        )

    duplicate_answer = deepcopy(payload)
    duplicate_answer["answers"] = (
        *duplicate_answer["answers"],
        duplicate_answer["answers"][0],
    )
    with pytest.raises(ValueError, match="answer IDs must be unique"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(duplicate_answer), search_policy
        )


@pytest.mark.parametrize(
    ("phrase", "error"),
    [
        ("", "at least 1 character"),
        (" Not normalized", "normalized"),
        ("safe  phrase", "normalized"),
        ("ranking preference", "blocked"),
        ("share your password", "unsafe"),
        ("terrain ‮ access", "control"),
        ("terrain / access", "characters"),
        ("terrain ☃ access", "characters"),
    ],
)
def test_registry_rejects_invalid_registered_question_phrases(
    phrase: str,
    error: str,
) -> None:
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    payload["topics"][0]["question_phrases"] = (phrase,)

    if not phrase:
        with pytest.raises(ValidationError, match=error):
            RefinementPresentationPolicy.model_validate(payload)
        return

    configured = RefinementPresentationPolicy.model_validate(payload)
    with pytest.raises(ValueError, match=error):
        validate_refinement_presentation_policy(configured, load_search_policy())


def test_registry_bounds_registered_question_phrases() -> None:
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    payload["topics"][0]["question_phrases"] = ("x" * 201,)

    with pytest.raises(ValidationError, match="at most 200 characters"):
        RefinementPresentationPolicy.model_validate(payload)


def test_registry_rejects_question_phrase_collisions_between_topics() -> None:
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    payload["topics"][1]["question_phrases"] = payload["topics"][0]["question_phrases"]
    configured = RefinementPresentationPolicy.model_validate(payload)

    with pytest.raises(ValueError, match="question phrases must be unique"):
        validate_refinement_presentation_policy(configured, load_search_policy())


def test_registry_rejects_unknown_or_repeated_answers() -> None:
    presentation = load_refinement_presentation_policy()
    with pytest.raises(KeyError, match="unknown refinement answer ID"):
        presentation.resolve_answer_ids(["unknown.answer"])
    with pytest.raises(ValueError, match="must be unique"):
        presentation.resolve_answer_ids(
            ["development_style.traditional", "development_style.traditional"]
        )


def test_registry_rejects_more_than_three_distinct_answer_ids() -> None:
    presentation = load_refinement_presentation_policy()

    with pytest.raises(ValueError, match="at most 3 answer IDs"):
        presentation.resolve_answer_ids(
            [
                "trip_window_snow_fit.high",
                "accessible_terrain_scale.as_much_as_possible",
                "terrain_potential_scale.high",
                "lift_network_scale.high",
            ]
        )


def test_registry_rejects_illegal_actions_and_objective_targets() -> None:
    search_policy = load_search_policy()
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    illegal_mode = deepcopy(payload)
    illegal_mode["answers"][0]["factor_preference_patch"]["mode"] = "require"
    with pytest.raises(ValueError, match="does not allow mode"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(illegal_mode), search_policy
        )

    illegal_value = deepcopy(payload)
    categorical = next(
        answer
        for answer in illegal_value["answers"]
        if answer["answer_id"] == "local_pace.quiet"
    )
    categorical["factor_preference_patch"]["values"] = ("unknown",)
    with pytest.raises(ValueError, match="does not allow values"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(illegal_value), search_policy
        )

    objective = deepcopy(payload)
    objective["answers"][0].pop("factor_preference_patch")
    objective["answers"][0]["objective_patch"] = {
        "factor_id": "trip_window_snow_fit",
        "importance": "high",
    }
    with pytest.raises(ValueError, match="objective_selected"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(objective), search_policy
        )


def test_registry_rejects_invalid_topic_ownership_and_fallback_shape() -> None:
    search_policy = load_search_policy()
    payload = load_refinement_presentation_policy().model_dump(mode="python")
    foreign_answer = deepcopy(payload)
    foreign_answer["topics"][0]["answer_ids"] = (
        foreign_answer["topics"][0]["answer_ids"][0],
        "local_pace.quiet",
    )
    with pytest.raises(ValueError, match="belongs to factor"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(foreign_answer), search_policy
        )

    presentation = load_refinement_presentation_policy()
    with pytest.raises(ValueError, match="multiple answers target factor"):
        presentation.resolve_answer_ids(
            ["trip_window_snow_fit.high", "trip_window_snow_fit.normal"]
        )

    too_many_fallbacks = deepcopy(payload)
    topic = too_many_fallbacks["topics"][0]
    topic["fallback_answer_ids"] = topic["fallback_answer_ids"] * 2
    with pytest.raises(ValidationError, match="at most 5 items"):
        RefinementPresentationPolicy.model_validate(too_many_fallbacks)

    foreign_fallback = deepcopy(payload)
    foreign_fallback["topics"][0]["fallback_answer_ids"] = (
        foreign_fallback["topics"][0]["fallback_answer_ids"][0],
        "local_pace.quiet",
    )
    with pytest.raises(ValueError, match="fallback answer"):
        validate_refinement_presentation_policy(
            RefinementPresentationPolicy.model_validate(foreign_fallback), search_policy
        )
