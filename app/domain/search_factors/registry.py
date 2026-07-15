from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_policy import SearchPolicy


class FactorEvaluator(Protocol):
    factor_id: str

    def evaluate(self, context: object, candidate: object) -> FactorEvaluation: ...


class FactorRegistryError(ValueError):
    pass


class FactorRegistry:
    """Immutable lookup from stable factor ID to one typed evaluator."""

    def __init__(self, evaluators: Iterable[FactorEvaluator]) -> None:
        by_factor_id: dict[str, FactorEvaluator] = {}
        for evaluator in evaluators:
            factor_id = evaluator.factor_id.strip()
            if not factor_id:
                raise FactorRegistryError("evaluator factor_id must not be blank")
            if factor_id in by_factor_id:
                raise FactorRegistryError(f"duplicate evaluator: {factor_id}")
            by_factor_id[factor_id] = evaluator
        self._by_factor_id = by_factor_id

    @property
    def factor_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_factor_id))

    def get(self, factor_id: str) -> FactorEvaluator:
        try:
            return self._by_factor_id[factor_id]
        except KeyError as error:
            raise FactorRegistryError(
                f"unknown factor evaluator: {factor_id}"
            ) from error

    def evaluator_statuses(self) -> dict[str, str]:
        return {factor_id: "registered" for factor_id in self.factor_ids}

    def validate_policy(self, policy: SearchPolicy) -> None:
        expected = {factor.factor_id for factor in policy.factors_requiring_evaluators}
        actual = set(self._by_factor_id)
        missing = sorted(expected - actual)
        unconfigured = sorted(actual - expected)
        if not missing and not unconfigured:
            return

        problems: list[str] = []
        if missing:
            problems.append(f"missing evaluators: {', '.join(missing)}")
        if unconfigured:
            problems.append(f"unconfigured evaluators: {', '.join(unconfigured)}")
        raise FactorRegistryError("; ".join(problems))
