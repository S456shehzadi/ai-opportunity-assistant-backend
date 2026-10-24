"""Conditional logic and AST representation for complex opportunity requirements.

Supports multi-clause evaluation (AND, OR, NOT, UNLESS, EXCEPT, IF) preserving
uncertainty (UNKNOWN and CONDITIONAL) without collapsing into binary booleans.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from app.opportunities.eligibility.schemas import RequirementStatus


class LogicalOperator(StrEnum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    UNLESS = "UNLESS"
    EXCEPT = "EXCEPT"
    IF = "IF"
    ONLY_IF = "ONLY_IF"


class ConditionEvaluationResult:
    """Result of evaluating a condition AST node."""

    def __init__(
        self,
        status: RequirementStatus,
        explanation: str,
        satisfied_via_waiver: bool = False,
        details: dict[str, Any] | None = None,
    ):
        self.status = status
        self.explanation = explanation
        self.satisfied_via_waiver = satisfied_via_waiver
        self.details = details or {}


class ConditionNode(ABC):
    """Abstract Base Class for condition AST nodes."""

    @abstractmethod
    def evaluate(self, context: dict[str, Any]) -> ConditionEvaluationResult:
        """Evaluates the condition against the user context dictionary."""
        ...


class LeafCondition(ConditionNode):
    """Atomic evaluation comparing a context key with an expected value or callable."""

    def __init__(
        self,
        field_name: str,
        evaluator_fn: Any,
        description: str,
    ):
        self.field_name = field_name
        self.evaluator_fn = evaluator_fn
        self.description = description

    def evaluate(self, context: dict[str, Any]) -> ConditionEvaluationResult:
        return self.evaluator_fn(context)


class AndCondition(ConditionNode):
    """Logical AND: all sub-conditions must be satisfied."""

    def __init__(self, children: list[ConditionNode]):
        self.children = children

    def evaluate(self, context: dict[str, Any]) -> ConditionEvaluationResult:
        statuses = [child.evaluate(context) for child in self.children]

        # Any definite failure means NO_MATCH
        for res in statuses:
            if res.status == RequirementStatus.NO_MATCH:
                return ConditionEvaluationResult(
                    status=RequirementStatus.NO_MATCH,
                    explanation=f"Failed requirement: {res.explanation}",
                )

        # Any conflicting means CONFLICTING
        for res in statuses:
            if res.status == RequirementStatus.CONFLICTING:
                return ConditionEvaluationResult(
                    status=RequirementStatus.CONFLICTING,
                    explanation=f"Conflicting requirement: {res.explanation}",
                )

        # Any unknown or conditional means the overall condition is unknown/conditional
        for res in statuses:
            if res.status in (RequirementStatus.UNKNOWN, RequirementStatus.CONDITIONAL):
                return ConditionEvaluationResult(
                    status=res.status,
                    explanation=f"Indeterminate prerequisite: {res.explanation}",
                )

        # All MATCH
        return ConditionEvaluationResult(
            status=RequirementStatus.MATCH,
            explanation="All conjunct requirements satisfied.",
        )


class OrCondition(ConditionNode):
    """Logical OR: any sub-condition satisfied yields MATCH."""

    def __init__(self, children: list[ConditionNode]):
        self.children = children

    def evaluate(self, context: dict[str, Any]) -> ConditionEvaluationResult:
        results = [child.evaluate(context) for child in self.children]

        # Any definite match satisfies the OR
        for res in results:
            if res.status == RequirementStatus.MATCH:
                return ConditionEvaluationResult(
                    status=RequirementStatus.MATCH,
                    explanation=f"Satisfied via option: {res.explanation}",
                    satisfied_via_waiver=res.satisfied_via_waiver,
                )

        # If any is unknown or conditional, whole OR is indeterminate
        for res in results:
            if res.status in (RequirementStatus.UNKNOWN, RequirementStatus.CONDITIONAL):
                return ConditionEvaluationResult(
                    status=res.status,
                    explanation=f"Potential alternative: {res.explanation}",
                )

        # If all NO_MATCH
        return ConditionEvaluationResult(
            status=RequirementStatus.NO_MATCH,
            explanation="None of the alternative criteria were satisfied.",
        )


class UnlessCondition(ConditionNode):
    """UNLESS: Main requirement applies UNLESS waiver condition is met.

    e.g. IELTS 6.5 UNLESS previous degree was taught in English.
    """

    def __init__(self, main_condition: ConditionNode, waiver_condition: ConditionNode):
        self.main_condition = main_condition
        self.waiver_condition = waiver_condition

    def evaluate(self, context: dict[str, Any]) -> ConditionEvaluationResult:
        waiver_res = self.waiver_condition.evaluate(context)
        if waiver_res.status == RequirementStatus.MATCH:
            return ConditionEvaluationResult(
                status=RequirementStatus.MATCH,
                explanation=f"Requirement waived: {waiver_res.explanation}",
                satisfied_via_waiver=True,
            )

        main_res = self.main_condition.evaluate(context)
        if main_res.status == RequirementStatus.MATCH:
            return main_res

        # If main condition is UNKNOWN or NO_MATCH, but waiver is UNKNOWN, mark CONDITIONAL
        if waiver_res.status == RequirementStatus.UNKNOWN:
            return ConditionEvaluationResult(
                status=RequirementStatus.CONDITIONAL,
                explanation=(
                    f"{main_res.explanation}; waiver eligibility is unknown: "
                    f"{waiver_res.explanation}"
                ),
            )

        return main_res
