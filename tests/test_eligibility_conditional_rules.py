"""Unit tests for Boolean AST condition evaluation and Requirement Dependency Graphs."""

from __future__ import annotations

from app.opportunities.eligibility.conditions import (
    AndCondition,
    ConditionEvaluationResult,
    LeafCondition,
    OrCondition,
    UnlessCondition,
)
from app.opportunities.eligibility.rules import RequirementDependencyGraph
from app.opportunities.eligibility.schemas import RequirementEvaluation, RequirementStatus


class TestConditionAST:
    """Tests boolean condition trees maintaining UNKNOWN and CONDITIONAL semantics."""

    def test_leaf_condition(self):
        leaf = LeafCondition(
            field_name="cgpa",
            evaluator_fn=lambda ctx: ConditionEvaluationResult(
                status=RequirementStatus.MATCH
                if ctx.get("cgpa", 0) >= 3.0
                else RequirementStatus.NO_MATCH,
                explanation="CGPA check",
            ),
            description="CGPA >= 3.0",
        )
        assert leaf.evaluate({"cgpa": 3.5}).status == RequirementStatus.MATCH
        assert leaf.evaluate({"cgpa": 2.5}).status == RequirementStatus.NO_MATCH

    def test_and_condition_all_match(self):
        c1 = LeafCondition(
            "a", lambda ctx: ConditionEvaluationResult(RequirementStatus.MATCH, "A matched"), "A"
        )
        c2 = LeafCondition(
            "b", lambda ctx: ConditionEvaluationResult(RequirementStatus.MATCH, "B matched"), "B"
        )
        and_node = AndCondition([c1, c2])

        res = and_node.evaluate({})
        assert res.status == RequirementStatus.MATCH

    def test_and_condition_with_no_match(self):
        c1 = LeafCondition(
            "a", lambda ctx: ConditionEvaluationResult(RequirementStatus.MATCH, "A matched"), "A"
        )
        c2 = LeafCondition(
            "b", lambda ctx: ConditionEvaluationResult(RequirementStatus.NO_MATCH, "B failed"), "B"
        )
        and_node = AndCondition([c1, c2])

        res = and_node.evaluate({})
        assert res.status == RequirementStatus.NO_MATCH
        assert "Failed requirement" in res.explanation

    def test_and_condition_with_unknown_preserves_unknown(self):
        c1 = LeafCondition(
            "a", lambda ctx: ConditionEvaluationResult(RequirementStatus.MATCH, "A matched"), "A"
        )
        c2 = LeafCondition(
            "b", lambda ctx: ConditionEvaluationResult(RequirementStatus.UNKNOWN, "B unknown"), "B"
        )
        and_node = AndCondition([c1, c2])

        res = and_node.evaluate({})
        # Must preserve UNKNOWN instead of collapsing to False
        assert res.status == RequirementStatus.UNKNOWN
        assert "Indeterminate" in res.explanation

    def test_and_condition_with_conflict_preserves_conflict(self):
        c1 = LeafCondition(
            "a", lambda ctx: ConditionEvaluationResult(RequirementStatus.MATCH, "A matched"), "A"
        )
        c2 = LeafCondition(
            "b",
            lambda ctx: ConditionEvaluationResult(RequirementStatus.CONFLICTING, "B conflicting"),
            "B",
        )
        and_node = AndCondition([c1, c2])

        res = and_node.evaluate({})
        assert res.status == RequirementStatus.CONFLICTING

    def test_or_condition_any_match(self):
        c1 = LeafCondition(
            "a", lambda ctx: ConditionEvaluationResult(RequirementStatus.NO_MATCH, "A failed"), "A"
        )
        c2 = LeafCondition(
            "b", lambda ctx: ConditionEvaluationResult(RequirementStatus.MATCH, "B matched"), "B"
        )
        or_node = OrCondition([c1, c2])

        res = or_node.evaluate({})
        assert res.status == RequirementStatus.MATCH
        assert "Satisfied via option" in res.explanation

    def test_or_condition_all_no_match(self):
        c1 = LeafCondition(
            "a", lambda ctx: ConditionEvaluationResult(RequirementStatus.NO_MATCH, "A failed"), "A"
        )
        c2 = LeafCondition(
            "b", lambda ctx: ConditionEvaluationResult(RequirementStatus.NO_MATCH, "B failed"), "B"
        )
        or_node = OrCondition([c1, c2])

        res = or_node.evaluate({})
        assert res.status == RequirementStatus.NO_MATCH

    def test_or_condition_with_unknown_preserves_unknown(self):
        c1 = LeafCondition(
            "a", lambda ctx: ConditionEvaluationResult(RequirementStatus.NO_MATCH, "A failed"), "A"
        )
        c2 = LeafCondition(
            "b", lambda ctx: ConditionEvaluationResult(RequirementStatus.UNKNOWN, "B unknown"), "B"
        )
        or_node = OrCondition([c1, c2])

        res = or_node.evaluate({})
        assert res.status == RequirementStatus.UNKNOWN

    def test_unless_condition_waiver_satisfied(self):
        main = LeafCondition(
            "ielts",
            lambda ctx: ConditionEvaluationResult(RequirementStatus.NO_MATCH, "No IELTS"),
            "IELTS",
        )
        waiver = LeafCondition(
            "emi",
            lambda ctx: ConditionEvaluationResult(RequirementStatus.MATCH, "EMI degree verified"),
            "EMI",
        )
        unless_node = UnlessCondition(main, waiver)

        res = unless_node.evaluate({})
        assert res.status == RequirementStatus.MATCH
        assert res.satisfied_via_waiver is True
        assert "waived" in res.explanation.lower()

    def test_unless_condition_main_satisfied_without_waiver(self):
        main = LeafCondition(
            "ielts",
            lambda ctx: ConditionEvaluationResult(RequirementStatus.MATCH, "IELTS 7.5"),
            "IELTS",
        )
        waiver = LeafCondition(
            "emi",
            lambda ctx: ConditionEvaluationResult(RequirementStatus.NO_MATCH, "No EMI"),
            "EMI",
        )
        unless_node = UnlessCondition(main, waiver)

        res = unless_node.evaluate({})
        assert res.status == RequirementStatus.MATCH
        assert res.satisfied_via_waiver is False

    def test_unless_condition_unknown_waiver_becomes_conditional(self):
        main = LeafCondition(
            "ielts",
            lambda ctx: ConditionEvaluationResult(RequirementStatus.NO_MATCH, "No IELTS"),
            "IELTS",
        )
        waiver = LeafCondition(
            "emi",
            lambda ctx: ConditionEvaluationResult(RequirementStatus.UNKNOWN, "EMI status unknown"),
            "EMI",
        )
        unless_node = UnlessCondition(main, waiver)

        res = unless_node.evaluate({})
        assert res.status == RequirementStatus.CONDITIONAL
        assert "waiver eligibility is unknown" in res.explanation


class TestRequirementDependencyGraph:
    """Tests requirement prerequisites and dependency evaluation."""

    def test_graph_all_prerequisites_met(self):
        graph = RequirementDependencyGraph()
        graph.add_node("req1", "degree_level", "Bachelor's Degree")
        graph.add_node("req2", "cgpa", "Minimum CGPA 3.0")
        graph.add_prerequisite("req2", "req1")

        evaluations = {
            "req1": RequirementEvaluation(
                requirement_id="req1",
                requirement_type="degree_level",
                requirement_description="Bachelor's Degree",
                status=RequirementStatus.MATCH,
                explanation="Degree matched",
            ),
            "req2": RequirementEvaluation(
                requirement_id="req2",
                requirement_type="cgpa",
                requirement_description="Minimum CGPA 3.0",
                status=RequirementStatus.MATCH,
                explanation="CGPA matched",
            ),
        }
        notes = graph.evaluate_dependencies(evaluations)
        assert len(notes) == 0

    def test_graph_prerequisite_unmet_generates_warning(self):
        graph = RequirementDependencyGraph()
        graph.add_node("req1", "degree_level", "Bachelor's Degree")
        graph.add_node("req2", "cgpa", "Minimum CGPA 3.0")
        graph.add_prerequisite("req2", "req1")

        evaluations = {
            "req1": RequirementEvaluation(
                requirement_id="req1",
                requirement_type="degree_level",
                requirement_description="Bachelor's Degree",
                status=RequirementStatus.UNKNOWN,
                explanation="Degree not declared",
            ),
            "req2": RequirementEvaluation(
                requirement_id="req2",
                requirement_type="cgpa",
                requirement_description="Minimum CGPA 3.0",
                status=RequirementStatus.MATCH,
                explanation="CGPA matched",
            ),
        }
        notes = graph.evaluate_dependencies(evaluations)
        assert len(notes) == 1
        assert "prerequisite 'Bachelor's Degree' has status UNKNOWN" in notes[0]
