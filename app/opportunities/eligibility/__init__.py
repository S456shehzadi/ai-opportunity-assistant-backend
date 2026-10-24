"""AI Eligibility Matching & Personalized Opportunity Intelligence."""

from app.opportunities.eligibility.engine import EligibilityEngine, RuleBasedEligibilityModel
from app.opportunities.eligibility.schemas import (
    EligibilityConfidence,
    EligibilityResult,
    OverallEligibilityStatus,
    PersonalizedIntelligenceSummary,
    RequirementEvaluation,
    RequirementPriority,
    RequirementStatus,
)

__all__ = [
    "EligibilityConfidence",
    "EligibilityEngine",
    "EligibilityResult",
    "OverallEligibilityStatus",
    "PersonalizedIntelligenceSummary",
    "RequirementEvaluation",
    "RequirementPriority",
    "RequirementStatus",
    "RuleBasedEligibilityModel",
]
