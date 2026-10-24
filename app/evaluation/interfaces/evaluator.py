"""Evaluation interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.models.dataset import Dataset, DatasetVersion
from app.evaluation.models.evaluation_run import EvaluationRun
from app.evaluation.schemas.evaluation import (
    DatasetCreate,
    DatasetVersionCreate,
    EvaluationRunCreate,
)


class IEvaluationService(ABC):
    """Abstract interface for managing benchmark datasets and evaluating runs."""

    @abstractmethod
    async def create_dataset(self, db: AsyncSession, payload: DatasetCreate) -> Dataset:
        pass

    @abstractmethod
    async def create_dataset_version(
        self, db: AsyncSession, dataset_id: UUID, payload: DatasetVersionCreate
    ) -> DatasetVersion:
        pass

    @abstractmethod
    async def execute_evaluation_run(
        self, db: AsyncSession, payload: EvaluationRunCreate
    ) -> EvaluationRun:
        pass
