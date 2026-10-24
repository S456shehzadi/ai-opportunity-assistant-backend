"""Model catalog management, lifecycle promotion gates, rollback, and model cards."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.learning.models.model_card import ModelCardRecord
from app.learning.models.model_registry import (
    ModelDefinition,
    ModelStatus,
    ModelType,
)
from app.learning.schemas.learning import ModelDefinitionCreate
from app.learning.schemas.training import (
    ModelCardCreate,
    ModelPromotionRequest,
    ModelRollbackRequest,
)

logger = logging.getLogger(__name__)

ALLOWED_TRANSITIONS = {
    ModelStatus.DEVELOPMENT: {ModelStatus.EVALUATION, ModelStatus.ARCHIVED},
    ModelStatus.EVALUATION: {ModelStatus.CANDIDATE, ModelStatus.DEVELOPMENT, ModelStatus.ARCHIVED},
    ModelStatus.CANDIDATE: {ModelStatus.STAGING, ModelStatus.EVALUATION, ModelStatus.ARCHIVED},
    ModelStatus.STAGING: {ModelStatus.PRODUCTION, ModelStatus.CANDIDATE, ModelStatus.ARCHIVED},
    ModelStatus.PRODUCTION: {ModelStatus.STAGING, ModelStatus.ARCHIVED, ModelStatus.RETIRED},
    ModelStatus.ARCHIVED: {ModelStatus.DEVELOPMENT, ModelStatus.RETIRED},
    ModelStatus.RETIRED: set(),
}


class ModelRegistryService:
    """Oversees model registration, governance audits, lifecycle gates, and instant rollback."""

    async def register_model(
        self,
        db: AsyncSession,
        payload: ModelDefinitionCreate,
        model_card_payload: ModelCardCreate | None = None,
    ) -> ModelDefinition:
        """Registers a new model definition with optional model card governance."""
        model = ModelDefinition(
            model_id=payload.model_id,
            provider=payload.provider,
            model_name=payload.model_name,
            model_type=payload.model_type,
            version=payload.version,
            capabilities=payload.capabilities,
            active=payload.active,
            configuration_reference=payload.configuration_reference,
            status=ModelStatus.DEVELOPMENT,
        )
        db.add(model)
        await db.flush()

        if model_card_payload:
            card = ModelCardRecord(
                model_definition_id=model.id,
                purpose=model_card_payload.purpose,
                task=model_card_payload.task,
                intended_use=model_card_payload.intended_use,
                non_intended_use=model_card_payload.non_intended_use,
                limitations=model_card_payload.limitations,
                evaluation_metrics=model_card_payload.evaluation_metrics,
                training_data_provenance=model_card_payload.training_data_provenance,
                license=model_card_payload.license,
                ethical_considerations=model_card_payload.ethical_considerations,
            )
            db.add(card)

        await db.commit()
        return await self.get_model(db, model.model_id) or model

    async def get_model(self, db: AsyncSession, model_id: str) -> ModelDefinition | None:
        """Retrieves model definition with attached model card."""
        query = (
            select(ModelDefinition)
            .where(ModelDefinition.model_id == model_id)
            .options(selectinload(ModelDefinition.model_card))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_models(
        self,
        db: AsyncSession,
        task: ModelType | None = None,
        status: ModelStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ModelDefinition]:
        """Lists models with optional task and lifecycle status filtering."""
        query = select(ModelDefinition).options(selectinload(ModelDefinition.model_card))
        if task:
            query = query.where(ModelDefinition.model_type == task)
        if status:
            query = query.where(ModelDefinition.status == status)
        query = query.order_by(ModelDefinition.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def promote_model(
        self,
        db: AsyncSession,
        model_id: str,
        request: ModelPromotionRequest,
    ) -> ModelDefinition:
        """Validates gates and transitions model to the next lifecycle stage."""
        model = await self.get_model(db, model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        current_status = model.status
        target_status = request.target_status

        # Validate transition permission
        allowed = ALLOWED_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise ValueError(
                f"Invalid lifecycle transition from {current_status} to {target_status}"
            )

        # Gate verification: minimum metric thresholds for promotion beyond evaluation
        if target_status in (ModelStatus.CANDIDATE, ModelStatus.STAGING, ModelStatus.PRODUCTION):
            if request.min_metric_threshold and model.model_card:
                recorded_metrics = model.model_card.evaluation_metrics
                for metric_key, min_val in request.min_metric_threshold.items():
                    actual_val = recorded_metrics.get(metric_key, 0.0)
                    if actual_val < min_val:
                        raise ValueError(
                            f"Model failed promotion gate for {metric_key}: "
                            f"{actual_val} < required {min_val}"
                        )

        # Production promotion logic: preserve rollback link and demote current active model
        if target_status == ModelStatus.PRODUCTION:
            prod_query = select(ModelDefinition).where(
                ModelDefinition.model_type == model.model_type,
                ModelDefinition.status == ModelStatus.PRODUCTION,
                ModelDefinition.model_id != model_id,
            )
            prod_result = await db.execute(prod_query)
            current_prods = prod_result.scalars().all()
            for prev_prod in current_prods:
                model.rollback_model_id = prev_prod.model_id
                prev_prod.status = ModelStatus.STAGING

        model.status = target_status
        await db.commit()
        return await self.get_model(db, model_id) or model

    async def rollback_model(
        self,
        db: AsyncSession,
        model_id: str,
        request: ModelRollbackRequest,
    ) -> ModelDefinition:
        """Performs atomic rollback to previous stable production version."""
        current_model = await self.get_model(db, model_id)
        if not current_model:
            raise ValueError(f"Model {model_id} not found")

        target_model_id = request.target_model_id or current_model.rollback_model_id
        if not target_model_id:
            raise ValueError("No valid rollback target available for this model")

        target_model = await self.get_model(db, target_model_id)
        if not target_model:
            raise ValueError(f"Rollback target model {target_model_id} not found")

        # Demote current model and restore target model
        current_model.status = ModelStatus.ARCHIVED
        target_model.status = ModelStatus.PRODUCTION
        target_model.rollback_model_id = None

        await db.commit()
        return await self.get_model(db, target_model_id) or target_model

    async def update_canary(
        self,
        db: AsyncSession,
        model_id: str,
        canary_percentage: float,
    ) -> ModelDefinition:
        """Sets traffic split percentage for candidate canary evaluation."""
        model = await self.get_model(db, model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        model.canary_percentage = max(0.0, min(100.0, canary_percentage))
        await db.commit()
        return model

    async def upsert_model_card(
        self,
        db: AsyncSession,
        model_id: str,
        payload: ModelCardCreate,
    ) -> ModelCardRecord:
        """Creates or updates auditable model card."""
        model = await self.get_model(db, model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        card_query = select(ModelCardRecord).where(ModelCardRecord.model_definition_id == model.id)
        card_res = await db.execute(card_query)
        card = card_res.scalar_one_or_none()

        if card:
            card.purpose = payload.purpose
            card.task = payload.task
            card.intended_use = payload.intended_use
            card.non_intended_use = payload.non_intended_use
            card.limitations = payload.limitations
            card.evaluation_metrics = payload.evaluation_metrics
            card.training_data_provenance = payload.training_data_provenance
            card.license = payload.license
            card.ethical_considerations = payload.ethical_considerations
        else:
            card = ModelCardRecord(
                model_definition_id=model.id,
                purpose=payload.purpose,
                task=payload.task,
                intended_use=payload.intended_use,
                non_intended_use=payload.non_intended_use,
                limitations=payload.limitations,
                evaluation_metrics=payload.evaluation_metrics,
                training_data_provenance=payload.training_data_provenance,
                license=payload.license,
                ethical_considerations=payload.ethical_considerations,
            )
            db.add(card)

        await db.commit()
        await db.refresh(card)
        return card
