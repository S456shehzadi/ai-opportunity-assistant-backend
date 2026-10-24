"""AI Opportunity Extraction & Structured Intelligence Engine package."""

from app.opportunities.extraction.aggregation import OpportunityAggregator
from app.opportunities.extraction.confidence import ConfidenceCalculator
from app.opportunities.extraction.conflicts import ConflictDetector, ConflictRecord
from app.opportunities.extraction.deduplication import OpportunityDeduplicator
from app.opportunities.extraction.engine import (
    OpportunityExtractionEngine,
    OpportunityExtractionModel,
    RuleBasedOpportunityExtractor,
)
from app.opportunities.extraction.evidence import Evidence, EvidenceType, EvidenceValidator
from app.opportunities.extraction.extractors import (
    AcademicRequirementExtractor,
    ApplicationInfoExtractor,
    DeadlineExtractor,
    FundingExtractor,
    LanguageRequirementExtractor,
    SourceTrustAssessor,
)
from app.opportunities.extraction.normalization import (
    DegreeFieldTaxonomy,
    NormalizedOrganization,
    OrganizationNormalizer,
    RequirementNormalizer,
)
from app.opportunities.extraction.schemas import (
    ApplicationMethod,
    DeadlineType,
    ExtractedAcademicRequirement,
    ExtractedDeadline,
    ExtractedField,
    ExtractedLanguageRequirement,
    ExtractedOpportunity,
    FieldStatus,
    FundingPeriod,
    OpportunityCategory,
    SourceTrustType,
    StructuredFundingAmount,
)
from app.opportunities.extraction.validators import ExtractionValidator

__all__ = [
    "AcademicRequirementExtractor",
    "ApplicationInfoExtractor",
    "ApplicationMethod",
    "ConfidenceCalculator",
    "ConflictDetector",
    "ConflictRecord",
    "DeadlineExtractor",
    "DeadlineType",
    "DegreeFieldTaxonomy",
    "Evidence",
    "EvidenceType",
    "EvidenceValidator",
    "ExtractedAcademicRequirement",
    "ExtractedDeadline",
    "ExtractedField",
    "ExtractedLanguageRequirement",
    "ExtractedOpportunity",
    "ExtractionValidator",
    "FieldStatus",
    "FundingExtractor",
    "FundingPeriod",
    "LanguageRequirementExtractor",
    "NormalizedOrganization",
    "OpportunityAggregator",
    "OpportunityCategory",
    "OpportunityDeduplicator",
    "OpportunityExtractionEngine",
    "OpportunityExtractionModel",
    "OrganizationNormalizer",
    "RequirementNormalizer",
    "RuleBasedOpportunityExtractor",
    "SourceTrustAssessor",
    "SourceTrustType",
    "StructuredFundingAmount",
]
