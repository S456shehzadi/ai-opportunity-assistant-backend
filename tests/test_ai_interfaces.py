import pytest
from pydantic import BaseModel

from app.ai.interfaces.grounding import (
    ConfidenceLevel,
    GroundedClaim,
    GroundedResponse,
    SourceEvidence,
)
from app.ai.interfaces.specialized import SearchIntent
from app.ai.orchestrator.orchestrator import OpportunityAIOrchestrator
from app.ai.providers.factory import ProviderType, get_ai_provider


class DummyStructuredModel(BaseModel):
    title: str = "Test"
    score: float = 0.95


@pytest.mark.asyncio
async def test_mock_ai_provider_generation() -> None:
    provider = get_ai_provider(ProviderType.MOCK)
    model = provider.get_model("test-model")

    text = await model.generate("Explain scholarships")
    assert "Mock response" in text

    embeddings = await model.embed(["Scholarships in Europe"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 384


@pytest.mark.asyncio
async def test_ai_orchestrator_skeleton() -> None:
    orchestrator = OpportunityAIOrchestrator()
    intent = await orchestrator.understand_query("Find full scholarships for Pakistan students")
    assert isinstance(intent, SearchIntent)
    assert intent.raw_query == "Find full scholarships for Pakistan students"

    response = await orchestrator.generate_response(
        user_query="test",
        ranked_opportunities=[],
        eligibility_evaluations=[],
    )
    assert isinstance(response, GroundedResponse)


def test_grounding_claim_structure() -> None:
    evidence = SourceEvidence(
        source_url="https://daad.de/scholarships",
        source_domain="daad.de",
        exact_text_snippet="Deadline is October 31, 2026.",
        is_official_source=True,
    )
    claim = GroundedClaim(
        claim_text="The deadline for DAAD scholarship is October 31, 2026.",
        property_name="deadline",
        evidence=[evidence],
        confidence=ConfidenceLevel.HIGH,
    )
    assert claim.confidence == ConfidenceLevel.HIGH
    assert len(claim.evidence) == 1
    assert claim.evidence[0].is_official_source is True
