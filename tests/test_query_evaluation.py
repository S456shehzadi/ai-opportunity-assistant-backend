from app.ai.evaluation.query_benchmark import (
    REFERENCE_BENCHMARK_SAMPLES,
    QueryUnderstandingEvaluator,
)


def test_query_understanding_evaluator_benchmark() -> None:
    evaluator = QueryUnderstandingEvaluator()
    report = evaluator.evaluate(REFERENCE_BENCHMARK_SAMPLES)

    assert report.total_samples == len(REFERENCE_BENCHMARK_SAMPLES)
    assert report.intent_accuracy >= 0.85
    assert report.category_accuracy >= 0.85
    assert report.constraint_extraction_rate >= 0.85
    assert report.passed_samples >= 5
