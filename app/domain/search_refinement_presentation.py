from __future__ import annotations

import hashlib
import json
import re
import tomllib
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import permutations, product
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.domain.search_policy import SearchPolicy, load_search_policy
from app.domain.search_refinement import (
    RefinementCandidateState,
    RefinementOption,
    RefinementProposal,
    RefinementValidationError,
    ValidatedRefinementProposal,
    validate_refinement_proposal,
)
from app.domain.search_v4_models import (
    FactorPreferencePatch,
    SearchIntent,
    SearchObjective,
)

_MAX_INTERACTION_QUESTION_CHARACTERS = 280
_MAX_INTERACTION_REASON_CHARACTERS = 500
_NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
_RegistryQuestionText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=_MAX_INTERACTION_QUESTION_CHARACTERS,
    ),
]
_RegistryDisplayText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=_MAX_INTERACTION_REASON_CHARACTERS,
    ),
]
_RegistryQuestionPhrase = Annotated[
    str,
    StringConstraints(min_length=1, max_length=200),
]
_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")
_QUESTION_START = re.compile(
    r"^(?:What|Which|Would|How|Do|Does|Is|Are)\b",
    flags=re.IGNORECASE,
)
_WORD_TOKEN = re.compile(r"[^\W\d_]+(?:['’‘][^\W\d_]+)?", flags=re.UNICODE)
_ALLOWED_QUESTION_PUNCTUATION = frozenset({"?", "'", "’", "‘", "-"})
_ALLOWED_QUESTION_PHRASE_PUNCTUATION = frozenset({"'", "’", "‘", "-"})
_MULTI_TOPIC_QUESTION_CONNECTORS = (" or ", " versus ", " rather than ")
_ALLOWED_PREFERENCE_QUESTION_SHAPES = (
    "How important is/are <grounded topic> to you/for your trip?",
    "How much should/does <grounded topic> matter/influence your choice?",
    "Would you prefer/like/want <grounded choice>?",
    "Would you rather <grounded choice>?",
    ("Would <grounded topic> matter to you/improve your trip/add value to your trip?"),
    "Does <grounded topic> matter to you/for your trip?",
    "Is/Are <grounded topic> important to you/for your trip?",
    "What kind/type/pace/atmosphere ... would you prefer/like/want?",
    "Which ... would you prefer/choose/rather have?",
    "How easy should <grounded access> be?",
)
_PREFERENCE_QUESTION_PATTERNS = tuple(
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        r"How important (?:is|are) (?P<body>.+) (?:to you|for your trip)\?",
        (
            r"How much (?:should|does) (?P<body>.+) "
            r"(?:matter|influence your choice)\?"
        ),
        r"Would you (?:prefer|like|want) (?P<body>.+)\?",
        r"Would you rather (?P<body>.+)\?",
        (
            r"Would (?P<body>.+) "
            r"(?:matter to you|improve your trip|add value to your trip)\?"
        ),
        r"Does (?P<body>.+) matter (?:to you|for your trip)\?",
        r"(?:Is|Are) (?P<body>.+) important (?:to you|for your trip)\?",
        (
            r"What (?:kind|type|pace|atmosphere)(?: of)? (?P<body>.+) "
            r"would you (?:prefer|like|want)\?"
        ),
        r"Which (?P<body>.+) would you (?:prefer|choose|rather have)\?",
        r"How easy should (?P<body>.+) be\?",
    )
)
_QUESTION_BODY_DISALLOWED_TOKENS = frozenset(
    {
        "add",
        "am",
        "and",
        "are",
        "because",
        "but",
        "can",
        "could",
        "did",
        "do",
        "does",
        "had",
        "has",
        "if",
        "important",
        "importance",
        "improve",
        "influence",
        "is",
        "like",
        "may",
        "matter",
        "matters",
        "might",
        "must",
        "prefer",
        "preference",
        "priority",
        "shall",
        "should",
        "was",
        "were",
        "when",
        "while",
        "will",
        "would",
        "want",
    }
)
_GENERIC_QUESTION_VOCABULARY = frozenset(
    {
        "a",
        "add",
        "an",
        "and",
        "are",
        "as",
        "be",
        "by",
        "could",
        "choice",
        "choose",
        "do",
        "does",
        "easy",
        "easier",
        "ease",
        "even",
        "favour",
        "favor",
        "for",
        "from",
        "have",
        "how",
        "if",
        "important",
        "importance",
        "improve",
        "in",
        "influence",
        "is",
        "it",
        "kind",
        "like",
        "matter",
        "matters",
        "more",
        "of",
        "on",
        "or",
        "prefer",
        "preference",
        "priority",
        "rather",
        "should",
        "suit",
        "than",
        "the",
        "this",
        "to",
        "trip",
        "type",
        "value",
        "versus",
        "what",
        "when",
        "where",
        "which",
        "with",
        "without",
        "would",
        "want",
        "you",
        "your",
        "atmosphere",
    }
)
_SENSITIVE_BRIEF_MARKERS = frozenset(
    {
        "address",
        "bank",
        "card",
        "contact",
        "credential",
        "credentials",
        "email",
        "passport",
        "password",
        "payment",
        "phone",
        "secret",
        "secrets",
        "token",
    }
)
_SENSITIVE_PUBLIC_COPY_TERMS = _SENSITIVE_BRIEF_MARKERS
_EXTERNAL_ACTION_PUBLIC_COPY_MARKERS = frozenset({"external", "offer"})
_NON_TRANSACTION_EXTERNAL_ACTION_VERBS = frozenset(
    {
        "click",
        "follow",
        "provide",
        "send",
        "share",
        "submit",
        "upload",
        "visit",
    }
)
_EXTERNAL_ACTION_CONTEXT_TERMS = frozenset(
    {
        "and",
        "can",
        "could",
        "may",
        "must",
        "never",
        "not",
        "now",
        "please",
        "should",
        "then",
        "to",
        "you",
        "your",
        "would",
    }
)
_UNSUPPORTED_CLAIM_PUBLIC_COPY_TERMS = frozenset(
    {
        "best",
        "cheapest",
        "closest",
        "deepest",
        "fastest",
        "greatest",
        "guarantee",
        "guaranteed",
        "highest",
        "largest",
        "lowest",
        "most",
        "safest",
        "snowiest",
        "worst",
    }
)
_PAYMENT_CREDENTIAL_PUBLIC_COPY_TERMS = frozenset(
    {
        "cvc",
        "cvv",
        "iban",
        "pin",
        "wallet",
    }
)
_PAYMENT_PROVIDER_PUBLIC_COPY_TERMS = frozenset(
    {
        "alipay",
        "cashapp",
        "coinbase",
        "klarna",
        "metamask",
        "paypal",
        "revolut",
        "stripe",
        "venmo",
        "wechatpay",
    }
)
_PAYMENT_PROVIDER_TOKEN_PATTERN = re.compile(
    r"(?:[a-z]+pay|pay[a-z]+)",
    flags=re.IGNORECASE,
)
_SAFE_NON_DIRECTIVE_TRANSACTION_PATTERNS = (
    re.compile(r"\bpass\s+purchase\s+timing\b", flags=re.IGNORECASE),
    re.compile(
        r"\blift[-\s]+pass\s+purchase\s+(?:planning|price\s+comparison)\b",
        flags=re.IGNORECASE,
    ),
)
_TRANSACTION_DIRECTIVE_OR_URGENCY_TERMS = frozenset(
    {
        "complete",
        "confirm",
        "continue",
        "enter",
        "finalise",
        "finalize",
        "finish",
        "immediate",
        "immediately",
        "make",
        "now",
        "place",
        "proceed",
        "start",
        "submit",
        "today",
        "urgent",
        "urgently",
    }
)
_TRANSACTION_ACTION_PATTERN = re.compile(
    r"\b(?:"
    r"reserv(?:e|es|ed|ing|ation|ations)|"
    r"book(?:s|ed|ing|ings)?|"
    r"buy(?:s|ing)?|bought|"
    r"purchas(?:e|es|ed|ing)|"
    r"pay(?:s|ing|ment|ments)?|paid|"
    r"order(?:s|ed|ing)?|"
    r"subscrib(?:e|es|ed|ing)|subscription(?:s)?|"
    r"download(?:s|ed|ing)?|"
    r"install(?:s|ed|ing|ation|ations)?|"
    r"checkout(?:s)?|check[-\s]+out(?:s)?"
    r")\b",
    flags=re.IGNORECASE,
)
_URI_SCHEME_PATTERN = re.compile(
    r"(?<![\w.+-])[a-z][a-z0-9+.-]*:(?=\S)",
    flags=re.IGNORECASE,
)
_WWW_PATTERN = re.compile(r"\bwww\.\S+", flags=re.IGNORECASE)
_BARE_DOMAIN_PATTERN = re.compile(
    r"(?<![@\w-])"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,63}"
    r"(?![\w-])",
    flags=re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_PHONE_OR_PAYMENT_PATTERN = re.compile(r"(?:\d[\s().+-]*){7,}")
_PAYMENT_CREDENTIAL_PATTERN = re.compile(
    r"\b(?:"
    r"bank[\s-]+account|"
    r"account[\s-]+(?:details|number)|"
    r"routing[\s-]+(?:details|number)|"
    r"sort[\s-]+code|"
    r"swift[\s-]+code"
    r")\b",
    flags=re.IGNORECASE,
)
_MACHINE_SLUG_ID_PATTERN = re.compile(
    r"(?<![\w-])[a-z0-9]+(?:-[a-z0-9]+){2,}(?![\w-])",
    flags=re.IGNORECASE,
)
_MACHINE_KEY_ID_PATTERN = re.compile(
    r"(?<!\w)[a-z0-9]+(?:[_:][a-z0-9]+)+(?!\w)",
    flags=re.IGNORECASE,
)
_MULTI_TOPIC_FALLBACK = (
    "Which of these trip preferences matters most to you?",
    "Your answer can distinguish otherwise similar trip options.",
)
DEFAULT_REFINEMENT_PRESENTATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "search-refinement"
    / "presentation-v1.toml"
)


class _PresentationModel(BaseModel):
    model_config = _MODEL_CONFIG


class RefinementAnswerPolicy(_PresentationModel):
    answer_id: _NonBlankText
    factor_id: _NonBlankText
    label: _RegistryDisplayText
    description: _RegistryDisplayText
    factor_preference_patch: FactorPreferencePatch | None = None
    objective_patch: SearchObjective | None = None

    @model_validator(mode="after")
    def require_one_matching_action(self) -> Self:
        if (self.factor_preference_patch is None) == (self.objective_patch is None):
            raise ValueError("answer requires exactly one typed action")
        target = (
            self.factor_preference_patch.factor_id
            if self.factor_preference_patch is not None
            else self.objective_patch.factor_id
        )
        if target != self.factor_id:
            raise ValueError("answer action must target factor_id")
        return self


class RefinementTopicPolicy(_PresentationModel):
    topic_id: _NonBlankText
    factor_id: _NonBlankText
    traveller_topic: _NonBlankText
    question_phrases: tuple[_RegistryQuestionPhrase, ...] = Field(
        min_length=1, max_length=8
    )
    fallback_question: _RegistryQuestionText
    fallback_reason: _RegistryDisplayText
    fallback_answer_ids: tuple[_NonBlankText, ...] = Field(min_length=2, max_length=5)
    answer_ids: tuple[_NonBlankText, ...] = Field(min_length=2, max_length=8)
    fallback_priority: int = Field(ge=1, le=100)


class ResolvedRefinementAnswer(_PresentationModel):
    answer_ids: tuple[_NonBlankText, ...]
    label: _NonBlankText
    description: _NonBlankText
    factor_preferences: tuple[FactorPreferencePatch, ...] = ()
    objectives: tuple[SearchObjective, ...] = ()


class RefinementPresentationPolicy(_PresentationModel):
    presentation_policy_version: _NonBlankText
    blocked_copy_terms: tuple[_NonBlankText, ...]
    topics: tuple[RefinementTopicPolicy, ...]
    answers: tuple[RefinementAnswerPolicy, ...]

    @property
    def topic_by_id(self) -> Mapping[str, RefinementTopicPolicy]:
        return MappingProxyType({topic.topic_id: topic for topic in self.topics})

    @property
    def answer_by_id(self) -> Mapping[str, RefinementAnswerPolicy]:
        return MappingProxyType({answer.answer_id: answer for answer in self.answers})

    def provider_topics(
        self, allowed_factor_ids: frozenset[str]
    ) -> tuple[dict[str, object], ...]:
        answers_by_id = self.answer_by_id
        return tuple(
            {
                "topic_id": topic.topic_id,
                "question_phrases": topic.question_phrases,
                "allowed_preference_question_shapes": (
                    _ALLOWED_PREFERENCE_QUESTION_SHAPES
                ),
                "answers": tuple(
                    {
                        "answer_id": answer_id,
                        "label": answers_by_id[answer_id].label,
                        "description": answers_by_id[answer_id].description,
                    }
                    for answer_id in topic.answer_ids
                ),
            }
            for topic in self.topics
            if topic.factor_id in allowed_factor_ids
        )

    def approved_question_vocabulary(self, topic_ids: Sequence[str]) -> frozenset[str]:
        return _GENERIC_QUESTION_VOCABULARY | frozenset(
            token
            for topic_id in topic_ids
            for token in self._topic_question_tokens(topic_id)
        )

    def _topic_question_tokens(self, topic_id: str) -> frozenset[str]:
        try:
            topic = self.topic_by_id[topic_id]
        except KeyError as error:
            raise KeyError(f"unknown refinement topic ID: {topic_id}") from error
        return frozenset(
            token for phrase in topic.question_phrases for token in _tokens(phrase)
        )

    def resolve_answer_ids(self, answer_ids: Sequence[str]) -> ResolvedRefinementAnswer:
        if not answer_ids:
            raise ValueError("refinement answer IDs must not be empty")
        if len(answer_ids) > 3:
            raise ValueError("a refinement option may contain at most 3 answer IDs")
        if len(answer_ids) != len(set(answer_ids)):
            raise ValueError("refinement answer IDs must be unique")
        answers: list[RefinementAnswerPolicy] = []
        for answer_id in answer_ids:
            try:
                answers.append(self.answer_by_id[answer_id])
            except KeyError as error:
                raise KeyError(f"unknown refinement answer ID: {answer_id}") from error
        factor_ids = [answer.factor_id for answer in answers]
        if len(factor_ids) != len(set(factor_ids)):
            raise ValueError("multiple answers target factor")
        return ResolvedRefinementAnswer(
            answer_ids=tuple(answer_ids),
            label=" + ".join(answer.label for answer in answers),
            description=" ".join(answer.description for answer in answers),
            factor_preferences=tuple(
                answer.factor_preference_patch
                for answer in answers
                if answer.factor_preference_patch is not None
            ),
            objectives=tuple(
                answer.objective_patch
                for answer in answers
                if answer.objective_patch is not None
            ),
        )


def resolve_interaction_copy(
    question: str,
    topic_ids: Sequence[str],
    candidate_ids: Sequence[str],
    presentation: RefinementPresentationPolicy,
    *,
    untrusted_brief: str | None = None,
) -> tuple[str, str]:
    """Keep only selected-topic-grounded question copy; reason is server-owned."""

    fallback_question, fallback_reason = _fallback_copy(topic_ids, presentation)
    blocked_tokens = (*presentation.blocked_copy_terms, *candidate_ids)
    resolved_question = (
        question
        if _safe_question(
            question,
            blocked_tokens,
            topic_ids=topic_ids,
            presentation=presentation,
            untrusted_brief=untrusted_brief,
        )
        else fallback_question
    )
    return resolved_question, fallback_reason


def semantic_refinement_question_id(
    *,
    topic_ids: Sequence[str],
    answer_id_sets: Sequence[Sequence[str]],
    presentation: RefinementPresentationPolicy,
) -> str:
    semantic_payload = {
        "presentation_policy_version": presentation.presentation_policy_version,
        "topic_ids": sorted(topic_ids),
        "answer_id_sets": sorted(sorted(answer_ids) for answer_ids in answer_id_sets),
    }
    semantic_digest = hashlib.sha256(
        json.dumps(
            semantic_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"refinement-{semantic_digest}"


def build_deterministic_refinement_fallback(
    *,
    intent: SearchIntent,
    candidates: Sequence[RefinementCandidateState],
    policy: SearchPolicy,
    presentation: RefinementPresentationPolicy,
    already_answered_question_ids: frozenset[str] = frozenset(),
) -> ValidatedRefinementProposal | None:
    """Return the first material registry-backed fallback question."""

    for topic in sorted(presentation.topics, key=lambda item: item.fallback_priority):
        try:
            options = tuple(
                _fallback_option(answer_id, presentation)
                for answer_id in topic.fallback_answer_ids
            )
            proposal = RefinementProposal(
                question_id=semantic_refinement_question_id(
                    topic_ids=(topic.topic_id,),
                    answer_id_sets=tuple(
                        (answer_id,) for answer_id in topic.fallback_answer_ids
                    ),
                    presentation=presentation,
                ),
                question=topic.fallback_question,
                reason=topic.fallback_reason,
                options=options,
            )
            return validate_refinement_proposal(
                proposal=proposal,
                intent=intent,
                candidates=candidates,
                policy=policy,
                already_answered_question_ids=already_answered_question_ids,
            )
        except RefinementValidationError:
            continue
    return None


def _fallback_option(
    answer_id: str,
    presentation: RefinementPresentationPolicy,
) -> RefinementOption:
    resolved = presentation.resolve_answer_ids((answer_id,))
    return RefinementOption(
        label=resolved.label,
        description=resolved.description,
        group_priority_patches=(),
        factor_preference_patches=resolved.factor_preferences,
        objective_patches=resolved.objectives,
    )


def _fallback_copy(
    topic_ids: Sequence[str],
    presentation: RefinementPresentationPolicy,
) -> tuple[str, str]:
    if not topic_ids:
        raise ValueError("refinement interaction copy requires at least one topic")
    if len(topic_ids) > 1:
        return _MULTI_TOPIC_FALLBACK
    try:
        topic = presentation.topic_by_id[topic_ids[0]]
    except KeyError as error:
        raise KeyError(f"unknown refinement topic ID: {topic_ids[0]}") from error
    return topic.fallback_question, topic.fallback_reason


def _safe_question(
    question: str,
    blocked_tokens: Sequence[str],
    *,
    topic_ids: Sequence[str],
    presentation: RefinementPresentationPolicy,
    untrusted_brief: str | None,
) -> bool:
    question_tokens = frozenset(_tokens(question))
    approved_vocabulary = presentation.approved_question_vocabulary(topic_ids)
    semantic_body = _preference_question_body(question)
    return (
        len(question) <= _MAX_INTERACTION_QUESTION_CHARACTERS
        and question.endswith("?")
        and _QUESTION_START.match(question) is not None
        and question_tokens <= approved_vocabulary
        and semantic_body is not None
        and _matches_registered_question_phrases(
            semantic_body,
            topic_ids,
            presentation,
        )
        and _has_only_allowed_question_characters(question)
        and _public_copy_safety_violation(
            question,
            blocked_tokens=blocked_tokens,
        )
        is None
        and not _brief_requires_registered_fallback(untrusted_brief)
    )


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(
        match.group(0).casefold().replace("’", "'").replace("‘", "'")
        for match in _WORD_TOKEN.finditer(text)
    )


def _contains_sensitive_pattern(text: str) -> bool:
    return any(
        pattern.search(text) is not None
        for pattern in (
            _URI_SCHEME_PATTERN,
            _WWW_PATTERN,
            _BARE_DOMAIN_PATTERN,
            _EMAIL_PATTERN,
            _PHONE_OR_PAYMENT_PATTERN,
        )
    )


def _contains_control_character(text: str) -> bool:
    return any(unicodedata.category(character).startswith("C") for character in text)


def _has_only_allowed_question_characters(question: str) -> bool:
    return all(
        unicodedata.category(character)[0] in {"L", "M"}
        or character.isspace()
        or character in _ALLOWED_QUESTION_PUNCTUATION
        for character in question
    )


def _has_only_allowed_question_phrase_characters(phrase: str) -> bool:
    return all(
        unicodedata.category(character)[0] in {"L", "M"}
        or character == " "
        or character in _ALLOWED_QUESTION_PHRASE_PUNCTUATION
        for character in phrase
    )


def _preference_question_body(question: str) -> str | None:
    if any(separator in question for separator in (",", ";", ":")):
        return None
    for pattern in _PREFERENCE_QUESTION_PATTERNS:
        match = pattern.fullmatch(question)
        if match is None:
            continue
        body_tokens = frozenset(_tokens(match.group("body")))
        if body_tokens and not body_tokens & _QUESTION_BODY_DISALLOWED_TOKENS:
            return match.group("body")
        return None
    return None


def _matches_registered_question_phrases(
    semantic_body: str,
    topic_ids: Sequence[str],
    presentation: RefinementPresentationPolicy,
) -> bool:
    normalized_body = _normalize_question_phrase(semantic_body)
    if len(topic_ids) == 1:
        topic = presentation.topic_by_id[topic_ids[0]]
        return normalized_body in topic.question_phrases

    topics = tuple(presentation.topic_by_id[topic_id] for topic_id in topic_ids)
    for ordered_topics in permutations(topics):
        for phrases in product(*(topic.question_phrases for topic in ordered_topics)):
            for connectors in product(
                _MULTI_TOPIC_QUESTION_CONNECTORS,
                repeat=len(phrases) - 1,
            ):
                composition = phrases[0] + "".join(
                    connector + phrase
                    for connector, phrase in zip(connectors, phrases[1:], strict=True)
                )
                if normalized_body == composition:
                    return True
    return False


def _normalize_question_phrase(text: str) -> str:
    return unicodedata.normalize("NFC", " ".join(text.split())).casefold()


def _brief_requires_registered_fallback(brief: str | None) -> bool:
    if not brief:
        return False
    return bool(
        frozenset(_tokens(brief)) & _SENSITIVE_BRIEF_MARKERS
        or _contains_sensitive_pattern(brief)
    )


def _contains_digit_or_percent(text: str) -> bool:
    return "%" in text or any(character.isdigit() for character in text)


def _contains_blocked_token(text: str, tokens: Sequence[str]) -> bool:
    return any(
        re.search(
            rf"(?<!\w){re.escape(token)}(?!\w)",
            text,
            flags=re.IGNORECASE,
        )
        is not None
        for token in tokens
        if token
    )


def _public_copy_safety_violation(
    text: str,
    *,
    blocked_tokens: Sequence[str] = (),
) -> str | None:
    """Return the first deterministic safety category for public copy."""

    if _contains_control_character(text):
        return "control"
    if _URI_SCHEME_PATTERN.search(text) is not None:
        return "uri"
    if (
        _WWW_PATTERN.search(text) is not None
        or _BARE_DOMAIN_PATTERN.search(text) is not None
    ):
        return "bare_domain"
    if _contains_sensitive_pattern(text):
        return "sensitive_pattern"
    if _contains_digit_or_percent(text):
        return "numeric_claim"
    if _contains_machine_id_shape(text):
        return "machine_id"
    tokens = _tokens(text)
    token_set = frozenset(tokens)
    if (
        token_set
        & (_PAYMENT_CREDENTIAL_PUBLIC_COPY_TERMS | _PAYMENT_PROVIDER_PUBLIC_COPY_TERMS)
        or any(_PAYMENT_PROVIDER_TOKEN_PATTERN.fullmatch(token) for token in tokens)
        or _PAYMENT_CREDENTIAL_PATTERN.search(text) is not None
    ):
        return "payment_credential"
    if token_set & _SENSITIVE_PUBLIC_COPY_TERMS:
        return "sensitive_request"
    if _contains_external_action(text, tokens):
        return "external_action"
    if _contains_unsupported_claim(tokens):
        return "unsupported_claim"
    if _contains_blocked_token(text, blocked_tokens):
        return "blocked"
    return None


def _contains_machine_id_shape(text: str) -> bool:
    return (
        "--" in text
        or _MACHINE_SLUG_ID_PATTERN.search(text) is not None
        or _MACHINE_KEY_ID_PATTERN.search(text) is not None
    )


def _contains_external_action(text: str, tokens: Sequence[str]) -> bool:
    if frozenset(tokens) & _EXTERNAL_ACTION_PUBLIC_COPY_MARKERS:
        return True
    has_transaction_shape = _TRANSACTION_ACTION_PATTERN.search(text) is not None
    transaction_copy = text
    for safe_pattern in _SAFE_NON_DIRECTIVE_TRANSACTION_PATTERNS:
        transaction_copy = safe_pattern.sub(" ", transaction_copy)
    if _TRANSACTION_ACTION_PATTERN.search(transaction_copy) is not None:
        return True
    if has_transaction_shape and (
        frozenset(tokens) & _TRANSACTION_DIRECTIVE_OR_URGENCY_TERMS
    ):
        return True
    return any(
        token in _NON_TRANSACTION_EXTERNAL_ACTION_VERBS
        and (index == 0 or tokens[index - 1] in _EXTERNAL_ACTION_CONTEXT_TERMS)
        for index, token in enumerate(tokens)
    )


def _contains_unsupported_claim(tokens: Sequence[str]) -> bool:
    for index, token in enumerate(tokens):
        if token not in _UNSUPPORTED_CLAIM_PUBLIC_COPY_TERMS:
            continue
        if (
            token == "best"
            and index >= 2
            and (tokens[index - 2], tokens[index - 1])
            in {
                ("fit", "you"),
                ("fits", "you"),
                ("suit", "you"),
                ("suits", "you"),
            }
        ):
            continue
        if (
            token == "most"
            and index >= 1
            and tokens[index - 1] == "matters"
            and tuple(tokens[index + 1 : index + 3]) == ("to", "you")
        ):
            continue
        return True
    return False


def load_refinement_presentation_policy(
    path: Path = DEFAULT_REFINEMENT_PRESENTATION_PATH,
) -> RefinementPresentationPolicy:
    with path.open("rb") as policy_file:
        presentation = RefinementPresentationPolicy.model_validate(
            tomllib.load(policy_file)
        )
    validate_refinement_presentation_policy(presentation, load_search_policy())
    return presentation


def validate_refinement_presentation_policy(
    presentation: RefinementPresentationPolicy,
    search_policy: SearchPolicy,
) -> None:
    _validate_visible_copy(presentation)
    _require_unique_ids("topic", [topic.topic_id for topic in presentation.topics])
    _require_unique_ids(
        "topic factor", [topic.factor_id for topic in presentation.topics]
    )
    _require_unique_ids("answer", [answer.answer_id for answer in presentation.answers])
    _require_unique_ids(
        "fallback priority",
        [str(topic.fallback_priority) for topic in presentation.topics],
    )
    _validate_registered_question_phrases(presentation)

    active_clarifiable = {
        factor.factor_id
        for factor in search_policy.factors
        if factor.lifecycle == "active"
        and factor.clarifiable
        and "clarification" in factor.roles
    }
    topic_factor_ids = {topic.factor_id for topic in presentation.topics}
    if topic_factor_ids != active_clarifiable:
        missing = sorted(active_clarifiable - topic_factor_ids)
        unexpected = sorted(topic_factor_ids - active_clarifiable)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        raise ValueError(
            "topics must cover active clarifiable factors exactly; "
            + "; ".join(details)
        )

    factor_by_id = {factor.factor_id: factor for factor in search_policy.factors}
    answers_by_id = presentation.answer_by_id
    answer_ids_by_factor: dict[str, set[str]] = {}
    for answer in presentation.answers:
        if answer.factor_id not in topic_factor_ids:
            raise ValueError(
                f"answer {answer.answer_id} belongs to factor without a topic: "
                f"{answer.factor_id}"
            )
        factor = factor_by_id.get(answer.factor_id)
        if factor is None:
            raise ValueError(
                f"answer {answer.answer_id} targets unknown factor {answer.factor_id}"
            )
        if answer.factor_preference_patch is not None:
            patch = answer.factor_preference_patch
            if patch.mode not in factor.allowed_modes:
                raise ValueError(
                    f"factor {factor.factor_id} does not allow mode {patch.mode}"
                )
            unsupported_values = set(patch.values) - set(factor.allowed_values)
            if unsupported_values:
                raise ValueError(
                    f"factor {factor.factor_id} does not allow values: "
                    f"{', '.join(sorted(unsupported_values))}"
                )
        else:
            if factor.activation != "objective_selected":
                raise ValueError(
                    f"objective answer {answer.answer_id} requires "
                    "objective_selected factor"
                )
        answer_ids_by_factor.setdefault(answer.factor_id, set()).add(answer.answer_id)

    for topic in presentation.topics:
        _validate_fallback_copy_bounds(topic, search_policy)
        for answer_id in topic.answer_ids:
            answer = answers_by_id.get(answer_id)
            if answer is None:
                raise ValueError(
                    f"topic {topic.topic_id} references unknown answer {answer_id}"
                )
            if answer.factor_id != topic.factor_id:
                raise ValueError(
                    f"answer {answer_id} belongs to factor {answer.factor_id}, "
                    f"not topic {topic.topic_id}"
                )
        if len(topic.answer_ids) != len(set(topic.answer_ids)):
            raise ValueError(f"topic {topic.topic_id} answer IDs must be unique")
        if len(topic.fallback_answer_ids) != len(set(topic.fallback_answer_ids)):
            raise ValueError(
                f"topic {topic.topic_id} fallback answer IDs must be unique"
            )
        for answer_id in topic.fallback_answer_ids:
            if answer_id not in topic.answer_ids:
                raise ValueError(
                    f"fallback answer {answer_id} is not an answer for topic "
                    f"{topic.topic_id}"
                )
        listed_answers = set(topic.answer_ids)
        owned_answers = answer_ids_by_factor.get(topic.factor_id, set())
        if listed_answers != owned_answers:
            raise ValueError(
                f"topic {topic.topic_id} must list every answer for factor "
                f"{topic.factor_id}"
            )

        for answer_id in topic.fallback_answer_ids:
            _validate_fallback_option_bounds(
                presentation.resolve_answer_ids((answer_id,)),
                topic.topic_id,
                answer_id,
                search_policy,
            )


def _validate_visible_copy(presentation: RefinementPresentationPolicy) -> None:
    visible_copy = (
        *(
            (f"topic {topic.topic_id} fallback question", topic.fallback_question)
            for topic in presentation.topics
        ),
        *(
            (f"topic {topic.topic_id} fallback reason", topic.fallback_reason)
            for topic in presentation.topics
        ),
        *(
            (f"answer {answer.answer_id} label", answer.label)
            for answer in presentation.answers
        ),
        *(
            (f"answer {answer.answer_id} description", answer.description)
            for answer in presentation.answers
        ),
    )
    for field, text in visible_copy:
        violation = _public_copy_safety_violation(
            text,
            blocked_tokens=presentation.blocked_copy_terms,
        )
        if violation == "blocked":
            raise ValueError(f"{field} contains blocked traveller-facing copy")
        if violation is not None:
            raise ValueError(f"{field} contains unsafe traveller-facing copy")


def _validate_registered_question_phrases(
    presentation: RefinementPresentationPolicy,
) -> None:
    phrase_owners: dict[str, str] = {}
    for topic in presentation.topics:
        for phrase in topic.question_phrases:
            if phrase != _normalize_question_phrase(phrase):
                raise ValueError(
                    f"topic {topic.topic_id} question phrase must be normalized"
                )
            violation = _public_copy_safety_violation(
                phrase,
                blocked_tokens=presentation.blocked_copy_terms,
            )
            if violation == "control":
                raise ValueError(
                    f"topic {topic.topic_id} question phrase contains control content"
                )
            if not _has_only_allowed_question_phrase_characters(phrase):
                raise ValueError(
                    f"topic {topic.topic_id} question phrase contains unsupported "
                    "characters"
                )
            if violation not in {None, "blocked"}:
                raise ValueError(
                    f"topic {topic.topic_id} question phrase contains unsafe content"
                )
            if violation == "blocked":
                raise ValueError(
                    f"topic {topic.topic_id} question phrase contains blocked content"
                )
            previous_owner = phrase_owners.setdefault(phrase, topic.topic_id)
            if previous_owner != topic.topic_id:
                raise ValueError(
                    "question phrases must be unique across topics: "
                    f"{phrase!r} belongs to {previous_owner} and {topic.topic_id}"
                )
        if len(topic.question_phrases) != len(set(topic.question_phrases)):
            raise ValueError(f"topic {topic.topic_id} question phrases must be unique")


def _validate_fallback_copy_bounds(
    topic: RefinementTopicPolicy,
    search_policy: SearchPolicy,
) -> None:
    maximum = search_policy.refinement.max_question_characters
    if len(topic.fallback_question) > maximum:
        raise ValueError(
            f"topic {topic.topic_id} fallback question exceeds search policy "
            f"max_question_characters ({maximum})"
        )


def _validate_fallback_option_bounds(
    option: ResolvedRefinementAnswer,
    topic_id: str,
    answer_id: str,
    search_policy: SearchPolicy,
) -> None:
    limits = search_policy.refinement
    if len(option.label) > limits.max_option_label_characters:
        raise ValueError(
            f"topic {topic_id} fallback answer {answer_id} label exceeds search "
            "policy max_option_label_characters "
            f"({limits.max_option_label_characters})"
        )
    if len(option.description) > limits.max_option_description_characters:
        raise ValueError(
            f"topic {topic_id} fallback answer {answer_id} description exceeds "
            "search policy max_option_description_characters "
            f"({limits.max_option_description_characters})"
        )


def _require_unique_ids(kind: str, values: Sequence[str]) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        raise ValueError(f"{kind} IDs must be unique: {', '.join(duplicates)}")
