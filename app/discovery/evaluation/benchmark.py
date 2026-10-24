"""Retrieval benchmark dataset for evaluating semantic, keyword, and hybrid search quality."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkQueryItem:
    """A benchmark query with expected ground-truth relevant and irrelevant opportunity IDs."""

    query: str
    expected_relevant_ids: list[str]
    expected_irrelevant_ids: list[str] = field(default_factory=list)
    language: str = "en"
    category: str = "general"
    hard_constraints: dict[str, Any] = field(default_factory=dict)


def get_default_retrieval_benchmark() -> list[BenchmarkQueryItem]:
    """Returns curated evaluation test collection covering diverse intent scenarios."""
    return [
        BenchmarkQueryItem(
            query="fully funded master's scholarships in computer science",
            expected_relevant_ids=["opp-cs-masters-full-1", "opp-cs-masters-full-2"],
            expected_irrelevant_ids=["opp-undergrad-arts-1", "opp-unfunded-masters-1"],
            category="degree_and_funding",
        ),
        BenchmarkQueryItem(
            query="AI research fellowship in Europe",
            expected_relevant_ids=["opp-ai-fellowship-eu-1"],
            expected_irrelevant_ids=["opp-undergrad-arts-1", "opp-us-internship-1"],
            category="field_and_location",
        ),
        BenchmarkQueryItem(
            query="scholarships with no application fee and no IELTS",
            expected_relevant_ids=["opp-no-fee-no-ielts-1"],
            expected_irrelevant_ids=["opp-high-fee-ielts-req-1"],
            category="requirement_filters",
        ),
        BenchmarkQueryItem(
            query="software engineering internships",
            expected_relevant_ids=["opp-se-internship-1", "opp-tech-internship-2"],
            expected_irrelevant_ids=["opp-cs-masters-full-1"],
            category="opportunity_type",
        ),
        BenchmarkQueryItem(
            query="منح ماجستير ممولة بالكامل للطلاب الدوليين",
            expected_relevant_ids=["opp-cs-masters-full-1", "opp-cs-masters-full-2"],
            expected_irrelevant_ids=["opp-undergrad-arts-1"],
            language="ar",
            category="multilingual_arabic",
        ),
        BenchmarkQueryItem(
            query="ماسٹرز ڈگری کے لیے اسکالرشپ",
            expected_relevant_ids=["opp-cs-masters-full-1"],
            expected_irrelevant_ids=["opp-undergrad-arts-1"],
            language="ur",
            category="multilingual_urdu",
        ),
    ]
