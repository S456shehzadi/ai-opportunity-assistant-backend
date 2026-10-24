from abc import ABC, abstractmethod
from typing import Any


class TrainingPipeline(ABC):
    """Abstract lifecycle pipeline for model fine-tuning and evaluation."""

    @abstractmethod
    async def clean_data(self, raw_data_path: str) -> str:
        pass

    @abstractmethod
    async def run_training(self, dataset_path: str, model_config: dict[str, Any]) -> str:
        pass

    @abstractmethod
    async def evaluate_model(
        self, checkpoint_path: str, eval_dataset_path: str
    ) -> dict[str, float]:
        pass
