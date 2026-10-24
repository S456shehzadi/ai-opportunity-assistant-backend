"""Learning interfaces module."""

from app.learning.interfaces.model import (
    AIModel,
    ClassificationModel,
    ClassificationResult,
    EmbeddingModel,
    GeneratedTextResponse,
    ModelCapability,
    RerankingModel,
    RerankResult,
    TextGenerationModel,
)
from app.learning.interfaces.provider import (
    IModelProvider,
    ModelProviderType,
)
from app.learning.interfaces.registry import IModelRegistry, IPromptRegistry
from app.learning.interfaces.training import (
    IModelArtifactStore,
    ITrainingBackend,
    TrainingExecutionResult,
)

__all__ = [
    "AIModel",
    "ClassificationModel",
    "ClassificationResult",
    "EmbeddingModel",
    "GeneratedTextResponse",
    "IModelArtifactStore",
    "IModelProvider",
    "IModelRegistry",
    "IPromptRegistry",
    "ITrainingBackend",
    "ModelCapability",
    "ModelProviderType",
    "RerankResult",
    "RerankingModel",
    "TextGenerationModel",
    "TrainingExecutionResult",
]
