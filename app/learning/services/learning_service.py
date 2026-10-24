"""Learning service managing model registry, prompts, and experimentation safety."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.learning.interfaces.registry import IModelRegistry, IPromptRegistry
from app.learning.models.experiment import (
    Experiment,
    ExperimentStatus,
    ExperimentVariant,
)
from app.learning.models.model_registry import ModelDefinition
from app.learning.models.prompt_version import PromptVersionRecord
from app.learning.schemas.learning import (
    ExperimentCreate,
    ModelDefinitionCreate,
    PromptVersionCreate,
)

logger = logging.getLogger(__name__)


class LearningService(IModelRegistry, IPromptRegistry):
    """Provides provider-independent model registration, prompt versioning, and safe experiments."""

    # 1. Model Registry
    async def register_model(
        self,
        db: AsyncSession,
        payload: ModelDefinitionCreate,
    ) -> ModelDefinition:
        """Registers a model definition into the catalog."""
        model = ModelDefinition(
            model_id=payload.model_id,
            provider=payload.provider,
            model_name=payload.model_name,
            model_type=payload.model_type,
            version=payload.version,
            capabilities=payload.capabilities,
            active=payload.active,
            configuration_reference=payload.configuration_reference,
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)
        return model

    async def get_active_model(
        self,
        db: AsyncSession,
        model_id: str,
    ) -> ModelDefinition | None:
        """Retrieves an active model definition by ID."""
        query = select(ModelDefinition).where(
            ModelDefinition.model_id == model_id,
            ModelDefinition.active.is_(True),
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    # 2. Prompt Registry
    async def register_prompt_version(
        self,
        db: AsyncSession,
        payload: PromptVersionCreate,
    ) -> PromptVersionRecord:
        """Registers an explicit prompt template version."""
        record = PromptVersionRecord(
            prompt_name=payload.prompt_name,
            prompt_version=payload.prompt_version,
            task=payload.task,
            template=payload.template,
            active=payload.active,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def get_prompt_version(
        self,
        db: AsyncSession,
        prompt_name: str,
        version: str,
    ) -> PromptVersionRecord | None:
        """Finds a prompt template by name and version."""
        query = select(PromptVersionRecord).where(
            PromptVersionRecord.prompt_name == prompt_name,
            PromptVersionRecord.prompt_version == version,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    # 3. Experimentation with Safety Guardrails
    async def create_experiment(
        self,
        db: AsyncSession,
        payload: ExperimentCreate,
    ) -> Experiment:
        """Creates an A/B experiment with strict safety checks forbidding eligibility tampering."""
        # Safety gate: strictly never allow experiments to manipulate eligibility determinations
        if "ELIGIBILITY" in payload.target_metric.upper() or "ELIGIBILITY" in payload.name.upper():
            raise ValueError("Experimentation on user eligibility is forbidden by safety policy.")

        experiment = Experiment(
            name=payload.name,
            description=payload.description,
            hypothesis=payload.hypothesis,
            status=ExperimentStatus.DRAFT,
            target_metric=payload.target_metric,
        )
        db.add(experiment)
        await db.flush()

        for v in payload.variants:
            variant = ExperimentVariant(
                experiment_id=experiment.id,
                variant_key=v.variant_key,
                traffic_percentage=v.traffic_percentage,
                configuration=v.configuration,
            )
            db.add(variant)

        await db.commit()
        await db.refresh(experiment)
        return experiment
