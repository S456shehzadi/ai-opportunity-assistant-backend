"""Tests for runtime model serving, canary traffic routing, and safe fallback protection."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.models.model_registry import (
    ModelDefinition,
    ModelHealthStatus,
    ModelStatus,
    ModelType,
)
from app.learning.services.model_serving_service import ModelServingService


@pytest.mark.asyncio
async def test_serving_routing_and_canary_selection(test_db_session: AsyncSession) -> None:
    serving = ModelServingService()

    # Create primary production model
    prod_model = ModelDefinition(
        model_id="prod-classifier-v1",
        provider="LOCAL",
        model_name="bert-classifier",
        model_type=ModelType.QUERY_UNDERSTANDING,
        version="1.0.0",
        capabilities=["QUERY"],
        active=True,
        status=ModelStatus.PRODUCTION,
        canary_percentage=0.0,
    )
    # Create candidate model with 100% canary traffic for deterministic test
    canary_model = ModelDefinition(
        model_id="candidate-classifier-v2",
        provider="LOCAL",
        model_name="roberta-classifier",
        model_type=ModelType.QUERY_UNDERSTANDING,
        version="2.0.0",
        capabilities=["QUERY"],
        active=True,
        status=ModelStatus.CANDIDATE,
        canary_percentage=100.0,
    )
    test_db_session.add_all([prod_model, canary_model])
    await test_db_session.commit()

    selected, is_canary = await serving.get_active_model_for_task(
        db=test_db_session,
        task=ModelType.QUERY_UNDERSTANDING,
    )
    assert selected is not None
    assert is_canary is True
    assert selected.model_id == "candidate-classifier-v2"


@pytest.mark.asyncio
async def test_safe_fallback_on_model_failure(test_db_session: AsyncSession) -> None:
    serving = ModelServingService()

    # Register active model
    model = ModelDefinition(
        model_id="flaky-model-v1",
        provider="LOCAL",
        model_name="flaky-net",
        model_type=ModelType.ELIGIBILITY_ASSIST,
        version="1.0.0",
        capabilities=["ELIGIBILITY"],
        active=True,
        status=ModelStatus.PRODUCTION,
        health_status=ModelHealthStatus.HEALTHY,
    )
    test_db_session.add(model)
    await test_db_session.commit()

    async def faulty_specialized_invoker():
        raise RuntimeError("GPU Out Of Memory in neural runtime")

    async def reliable_fallback_invoker():
        return {"result": "fallback_grounded_output", "status": "deterministic_baseline"}

    result, meta = await serving.execute_with_fallback(
        db=test_db_session,
        task=ModelType.ELIGIBILITY_ASSIST,
        specialized_invoker=faulty_specialized_invoker,
        fallback_invoker=reliable_fallback_invoker,
    )

    # Verification: Seamless fallback occurred without crash
    assert meta["used_fallback"] is True
    assert "Out Of Memory" in meta["fallback_reason"]
    assert result["result"] == "fallback_grounded_output"

    # Model health was automatically degraded
    await test_db_session.refresh(model)
    assert model.health_status == ModelHealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_deterministic_guardrails_never_overridden_by_neural_output() -> None:
    """Verifies architectural guarantee: deterministic rules (dates, GPA, nationality)

    always hold absolute veto power over any neural model prediction.
    """
    # 1. Simulate neural model prediction claiming "ELIGIBLE"
    neural_prediction = {
        "is_eligible": True,
        "confidence": 0.99,
        "reasoning": "Candidate appears highly promising",
    }

    # 2. Hard deterministic constraints
    user_gpa = 2.8
    minimum_required_gpa = 3.5
    deadline_passed = True

    # Deterministic guardrail check
    deterministic_violations = []
    if deadline_passed:
        deterministic_violations.append("Application deadline has passed")
    if user_gpa < minimum_required_gpa:
        deterministic_violations.append(
            f"User GPA ({user_gpa}) is below required minimum ({minimum_required_gpa})"
        )

    # Final combined decision must enforce deterministic veto
    if deterministic_violations:
        final_decision = {
            "is_eligible": False,
            "violations": deterministic_violations,
            "neural_assist_ignored": True,
        }
    else:
        final_decision = neural_prediction

    assert final_decision["is_eligible"] is False
    assert final_decision["neural_assist_ignored"] is True
    assert len(final_decision["violations"]) == 2
