from dataclasses import dataclass, field
from typing import Any

from app.ai.query.intent_schemas import SearchIntent, UserIntentType
from app.ai.query.query_understanding_service import QueryUnderstandingService


@dataclass
class QueryBenchmarkSample:
    query: str
    expected_intent: UserIntentType
    expected_is_search: bool = True
    expected_categories: list[str] = field(default_factory=list)
    expected_countries: list[str] = field(default_factory=list)
    expected_regions: list[str] = field(default_factory=list)
    expected_degrees: list[str] = field(default_factory=list)
    expected_fields: list[str] = field(default_factory=list)
    expected_has_no_test_constraint: str | None = None  # e.g. "IELTS"
    expected_is_fully_funded: bool = False
    expected_has_temporal_constraint: bool = False


@dataclass
class EvaluationReport:
    total_samples: int
    intent_accuracy: float
    category_accuracy: float
    constraint_extraction_rate: float
    passed_samples: int
    details: list[dict[str, Any]] = field(default_factory=list)


REFERENCE_BENCHMARK_SAMPLES: list[QueryBenchmarkSample] = [
    QueryBenchmarkSample(
        query="Find fully funded master's scholarships in Europe for computer science.",
        expected_intent=UserIntentType.FIND_SCHOLARSHIPS,
        expected_is_search=True,
        expected_categories=["Scholarship"],
        expected_regions=["Europe"],
        expected_degrees=["Master's"],
        expected_fields=["Computer Science"],
        expected_is_fully_funded=True,
    ),
    QueryBenchmarkSample(
        query="Which scholarships can I apply for without IELTS?",
        expected_intent=UserIntentType.FIND_SCHOLARSHIPS,
        expected_is_search=True,
        expected_categories=["Scholarship"],
        expected_has_no_test_constraint="IELTS",
    ),
    QueryBenchmarkSample(
        query="Find AI internships in Germany for international students.",
        expected_intent=UserIntentType.FIND_INTERNSHIPS,
        expected_is_search=True,
        expected_categories=["Internship"],
        expected_countries=["Germany"],
        expected_fields=["Artificial Intelligence"],
    ),
    QueryBenchmarkSample(
        query="Show me research fellowships related to machine learning.",
        expected_intent=UserIntentType.FIND_RESEARCH_OPPORTUNITIES,
        expected_is_search=True,
        expected_categories=["Fellowship"],
        expected_fields=["Machine Learning"],
    ),
    QueryBenchmarkSample(
        query="Find startup funding opportunities available to women founders.",
        expected_intent=UserIntentType.FIND_FUNDING,
        expected_is_search=True,
        expected_categories=["Startup Funding"],
    ),
    QueryBenchmarkSample(
        query="Which opportunities can I apply for this month?",
        expected_intent=UserIntentType.DISCOVER_OPPORTUNITIES,
        expected_is_search=True,
        expected_has_temporal_constraint=True,
    ),
    QueryBenchmarkSample(
        query="What does Erasmus Mundus mean?",
        expected_intent=UserIntentType.EXPLAIN_OPPORTUNITY,
        expected_is_search=False,
    ),
]


class QueryUnderstandingEvaluator:
    """Evaluates query understanding accuracy against curated benchmark test sets."""

    def __init__(self, service: QueryUnderstandingService | None = None) -> None:
        self.service = service or QueryUnderstandingService()

    def evaluate(self, samples: list[QueryBenchmarkSample] | None = None) -> EvaluationReport:
        dataset = samples or REFERENCE_BENCHMARK_SAMPLES
        total = len(dataset)
        correct_intents = 0
        correct_categories = 0
        correct_constraints = 0
        fully_passed = 0
        details: list[dict[str, Any]] = []

        for sample in dataset:
            actual: SearchIntent = self.service.understand_query(sample.query)

            intent_match = actual.intent_type == sample.expected_intent
            is_search_match = actual.is_search_intent == sample.expected_is_search
            if intent_match and is_search_match:
                correct_intents += 1

            cat_match = True
            for exp_cat in sample.expected_categories:
                if exp_cat not in actual.opportunity_categories:
                    cat_match = False
                    break
            if cat_match:
                correct_categories += 1

            constraints_ok = True
            # Country / Region check
            for exp_c in sample.expected_countries:
                if exp_c not in actual.countries:
                    constraints_ok = False
            for exp_r in sample.expected_regions:
                if exp_r not in actual.regions:
                    constraints_ok = False
            # Degree check
            for exp_deg in sample.expected_degrees:
                if exp_deg not in actual.degree_levels:
                    constraints_ok = False
            # Field check
            for exp_f in sample.expected_fields:
                if exp_f not in actual.fields:
                    constraints_ok = False
            # Funding check
            if sample.expected_is_fully_funded:
                if not any(fc.is_fully_funded for fc in actual.funding_constraints):
                    constraints_ok = False
            # Test constraint check
            if sample.expected_has_no_test_constraint:
                if not any(
                    tc.test_name == sample.expected_has_no_test_constraint
                    for tc in actual.language_test_constraints
                ):
                    constraints_ok = False
            # Temporal check
            if sample.expected_has_temporal_constraint:
                if not actual.deadline_constraints:
                    constraints_ok = False

            if constraints_ok:
                correct_constraints += 1

            sample_passed = intent_match and is_search_match and cat_match and constraints_ok
            if sample_passed:
                fully_passed += 1

            details.append(
                {
                    "query": sample.query,
                    "expected_intent": sample.expected_intent.value,
                    "actual_intent": actual.intent_type.value,
                    "intent_match": intent_match,
                    "categories_match": cat_match,
                    "constraints_match": constraints_ok,
                    "passed": sample_passed,
                }
            )

        return EvaluationReport(
            total_samples=total,
            intent_accuracy=round(correct_intents / total, 3) if total else 0.0,
            category_accuracy=round(correct_categories / total, 3) if total else 0.0,
            constraint_extraction_rate=round(correct_constraints / total, 3) if total else 0.0,
            passed_samples=fully_passed,
            details=details,
        )
