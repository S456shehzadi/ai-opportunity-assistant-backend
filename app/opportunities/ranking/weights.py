"""Configurable weights and normalization for ranking factors."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, Field

from app.opportunities.ranking.schemas import RankingFactorType


class RankingWeightsConfig(BaseModel):
    """Configurable weights controlling the importance of each ranking dimension."""

    academic_fit: float = Field(default=0.16, ge=0.0)
    field_fit: float = Field(default=0.12, ge=0.0)
    funding_fit: float = Field(default=0.14, ge=0.0)
    location_fit: float = Field(default=0.10, ge=0.0)
    degree_level_fit: float = Field(default=0.10, ge=0.0)
    deadline_relevance: float = Field(default=0.08, ge=0.0)
    freshness: float = Field(default=0.06, ge=0.0)
    source_quality: float = Field(default=0.06, ge=0.0)
    query_relevance: float = Field(default=0.10, ge=0.0)
    eligibility_completeness: float = Field(default=0.04, ge=0.0)

    # Optional factor extensions
    profile_fit: float = Field(default=0.0, ge=0.0)
    language_fit: float = Field(default=0.0, ge=0.0)
    test_requirement_fit: float = Field(default=0.0, ge=0.0)
    experience_fit: float = Field(default=0.08, ge=0.0)
    user_preference_fit: float = Field(default=0.0, ge=0.0)
    opportunity_category_fit: float = Field(default=0.0, ge=0.0)

    def get_factor_weight(self, factor_type: RankingFactorType) -> float:
        """Returns the raw configured weight for a factor type."""
        mapping = {
            RankingFactorType.ACADEMIC_FIT: self.academic_fit,
            RankingFactorType.FIELD_FIT: self.field_fit,
            RankingFactorType.FUNDING_FIT: self.funding_fit,
            RankingFactorType.LOCATION_FIT: self.location_fit,
            RankingFactorType.DEGREE_LEVEL_FIT: self.degree_level_fit,
            RankingFactorType.DEADLINE_RELEVANCE: self.deadline_relevance,
            RankingFactorType.FRESHNESS: self.freshness,
            RankingFactorType.SOURCE_QUALITY: self.source_quality,
            RankingFactorType.QUERY_RELEVANCE: self.query_relevance,
            RankingFactorType.ELIGIBILITY_COMPLETENESS: self.eligibility_completeness,
            RankingFactorType.PROFILE_FIT: self.profile_fit,
            RankingFactorType.LANGUAGE_FIT: self.language_fit,
            RankingFactorType.TEST_REQUIREMENT_FIT: self.test_requirement_fit,
            RankingFactorType.EXPERIENCE_FIT: self.experience_fit,
            RankingFactorType.USER_PREFERENCE_FIT: self.user_preference_fit,
            RankingFactorType.OPPORTUNITY_CATEGORY_FIT: self.opportunity_category_fit,
        }
        return mapping.get(factor_type, 0.0)

    def get_normalized_weights(self) -> dict[RankingFactorType, float]:
        """Calculates normalized weights where sum equals 1.0."""
        active = {
            factor: self.get_factor_weight(factor)
            for factor in RankingFactorType
            if self.get_factor_weight(factor) > 0.0
        }
        total = sum(active.values())
        if total <= 0:
            count = len(active) or 1
            return dict.fromkeys(active, 1.0 / count)
        return {f: w / total for f, w in active.items()}

    def version_hash(self) -> str:
        """Returns a deterministic SHA-256 fingerprint for configuration caching."""
        dumped = json.dumps(self.model_dump(), sort_keys=True)
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:12]
