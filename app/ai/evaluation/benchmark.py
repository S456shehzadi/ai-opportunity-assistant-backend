from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class EvaluationMetric(BaseModel):
    name: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkDataset(BaseModel):
    name: str
    sample_count: int
    version: str


class ModelEvaluator(ABC):
    """Abstract interface for offline and online model quality benchmarks."""

    @abstractmethod
    async def evaluate_extraction(self, dataset: BenchmarkDataset) -> list[EvaluationMetric]:
        pass

    @abstractmethod
    async def evaluate_grounding(self, dataset: BenchmarkDataset) -> list[EvaluationMetric]:
        """Verify hallucination rates and claim-evidence alignment."""
        pass
