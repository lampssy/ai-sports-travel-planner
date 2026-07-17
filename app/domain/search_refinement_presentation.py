from __future__ import annotations

import tomllib
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.search_policy import SearchPolicy, load_search_policy
from app.domain.search_v4_models import FactorPreferencePatch, SearchObjective

_NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")
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
    label: _NonBlankText
    description: _NonBlankText
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
    fallback_question: _NonBlankText
    fallback_reason: _NonBlankText
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
                "traveller_topic": topic.traveller_topic,
                "fallback_question": topic.fallback_question,
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
    _require_unique_ids("topic", [topic.topic_id for topic in presentation.topics])
    _require_unique_ids(
        "topic factor", [topic.factor_id for topic in presentation.topics]
    )
    _require_unique_ids("answer", [answer.answer_id for answer in presentation.answers])
    _require_unique_ids(
        "fallback priority",
        [str(topic.fallback_priority) for topic in presentation.topics],
    )

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


def _require_unique_ids(kind: str, values: Sequence[str]) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        raise ValueError(f"{kind} IDs must be unique: {', '.join(duplicates)}")
