"""Tests for model catalog, promotion quality gates, atomic rollback, and canary traffic."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_dev_user
from app.learning.models.model_registry import (
    ModelStatus,
    ModelType,
)
from app.learning.schemas.learning import ModelDefinitionCreate
from app.learning.schemas.training import (
    ModelCardCreate,
    ModelPromotionRequest,
    ModelRollbackRequest,
)
from app.learning.services.model_registry_service import ModelRegistryService
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_model_registry_lifecycle_and_promotion_gates(
    test_db_session: AsyncSession,
) -> None:
    service = ModelRegistryService()

    # 1. Register candidate model with card
    model_payload = ModelDefinitionCreate(
        model_id="specialized-extractor-v1",
        provider="LOCAL",
        model_name="extractor-bert",
        model_type=ModelType.OPPORTUNITY_EXTRACTION,
        version="1.0.0",
        capabilities=["EXTRACTION"],
    )
    card_payload = ModelCardCreate(
        purpose="Extract opportunity fields accurately",
        task="OPPORTUNITY_EXTRACTION",
        intended_use="Structured field extraction from academic web pages",
        limitations=["May struggle with non-English pages"],
        evaluation_metrics={"accuracy": 0.92, "f1": 0.89},
        license="MIT",
    )

    model = await service.register_model(
        db=test_db_session,
        payload=model_payload,
        model_card_payload=card_payload,
    )
    assert model.status == ModelStatus.DEVELOPMENT
    assert model.model_card is not None
    assert model.model_card.evaluation_metrics["accuracy"] == 0.92

    # 2. Promote to EVALUATION
    model = await service.promote_model(
        db=test_db_session,
        model_id="specialized-extractor-v1",
        request=ModelPromotionRequest(target_status=ModelStatus.EVALUATION),
    )
    assert model.status == ModelStatus.EVALUATION

    # 3. Promote to CANDIDATE with gate threshold that fails
    with pytest.raises(ValueError, match="failed promotion gate for accuracy"):
        await service.promote_model(
            db=test_db_session,
            model_id="specialized-extractor-v1",
            request=ModelPromotionRequest(
                target_status=ModelStatus.CANDIDATE,
                min_metric_threshold={"accuracy": 0.95},  # actual is 0.92 -> fails
            ),
        )

    # 4. Promote to CANDIDATE with passing threshold
    model = await service.promote_model(
        db=test_db_session,
        model_id="specialized-extractor-v1",
        request=ModelPromotionRequest(
            target_status=ModelStatus.CANDIDATE,
            min_metric_threshold={"accuracy": 0.90},
        ),
    )
    assert model.status == ModelStatus.CANDIDATE

    # 5. Promote to STAGING
    model = await service.promote_model(
        db=test_db_session,
        model_id="specialized-extractor-v1",
        request=ModelPromotionRequest(target_status=ModelStatus.STAGING),
    )
    assert model.status == ModelStatus.STAGING

    # 6. Promote to PRODUCTION
    model = await service.promote_model(
        db=test_db_session,
        model_id="specialized-extractor-v1",
        request=ModelPromotionRequest(target_status=ModelStatus.PRODUCTION),
    )
    assert model.status == ModelStatus.PRODUCTION


@pytest.mark.asyncio
async def test_atomic_model_rollback(test_db_session: AsyncSession) -> None:
    service = ModelRegistryService()

    # Step 1: Create Model V1 and set to PRODUCTION
    v1 = await service.register_model(
        db=test_db_session,
        payload=ModelDefinitionCreate(
            model_id="ranker-v1",
            provider="LOCAL",
            model_name="ranker-bert",
            model_type=ModelType.RERANKING,
        ),
    )
    v1.status = ModelStatus.PRODUCTION
    await test_db_session.commit()

    # Step 2: Create Model V2, promote through STAGING to PRODUCTION
    v2 = await service.register_model(
        db=test_db_session,
        payload=ModelDefinitionCreate(
            model_id="ranker-v2",
            provider="LOCAL",
            model_name="ranker-roberta",
            model_type=ModelType.RERANKING,
        ),
    )
    v2.status = ModelStatus.STAGING
    await test_db_session.commit()

    promoted_v2 = await service.promote_model(
        db=test_db_session,
        model_id="ranker-v2",
        request=ModelPromotionRequest(target_status=ModelStatus.PRODUCTION),
    )
    assert promoted_v2.status == ModelStatus.PRODUCTION
    assert promoted_v2.rollback_model_id == "ranker-v1"

    # Verify previous v1 was demoted to STAGING
    prev_v1 = await service.get_model(test_db_session, "ranker-v1")
    assert prev_v1 is not None
    assert prev_v1.status == ModelStatus.STAGING

    # Step 3: Trigger atomic rollback of V2
    restored = await service.rollback_model(
        db=test_db_session,
        model_id="ranker-v2",
        request=ModelRollbackRequest(reason="Regression in precision detected"),
    )
    assert restored.model_id == "ranker-v1"
    assert restored.status == ModelStatus.PRODUCTION

    demoted_v2 = await service.get_model(test_db_session, "ranker-v2")
    assert demoted_v2 is not None
    assert demoted_v2.status == ModelStatus.ARCHIVED


@pytest.mark.asyncio
async def test_model_registry_api_endpoints(
    client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    admin_user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000088"),
        email="admin_registry@example.com",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db_session.add(admin_user)
    await test_db_session.commit()

    if hasattr(client, "_transport") and hasattr(client._transport, "app"):
        client._transport.app.dependency_overrides[get_current_dev_user] = lambda: admin_user

    # 1. Register model
    reg_payload = {
        "model_id": "api-query-v1",
        "provider": "LOCAL",
        "model_name": "query-model",
        "model_type": "QUERY_UNDERSTANDING",
        "version": "1.0.0",
        "capabilities": ["QUERY"],
        "active": True,
        "configuration_reference": {},
    }
    res = await client.post("/api/v1/models", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["model_id"] == "api-query-v1"
    assert data["status"] == "DEVELOPMENT"

    # 2. Update canary percentage
    canary_res = await client.post(
        "/api/v1/models/api-query-v1/canary",
        json={"canary_percentage": 25.0},
    )
    assert canary_res.status_code == 200
    assert canary_res.json()["canary_percentage"] == 25.0

    # 3. Check health probe
    health_res = await client.get("/api/v1/models/api-query-v1/health")
    assert health_res.status_code == 200
    assert health_res.json()["is_healthy"] is True
    assert health_res.json()["health_status"] == "HEALTHY"

    # 4. Upsert model card
    card_payload = {
        "purpose": "Accurate query parsing",
        "task": "QUERY_UNDERSTANDING",
        "intended_use": "Search query structuring",
        "non_intended_use": "Free text generation",
        "limitations": ["Short queries only"],
        "evaluation_metrics": {"accuracy": 0.95},
        "training_data_provenance": {"dataset": "curated_v1"},
        "license": "Apache-2.0",
        "ethical_considerations": "Safe",
    }
    card_res = await client.put(
        "/api/v1/models/api-query-v1/card",
        json=card_payload,
    )
    assert card_res.status_code == 200
    assert card_res.json()["license"] == "Apache-2.0"
