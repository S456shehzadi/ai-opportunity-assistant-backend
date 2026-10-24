"""Grounded AI Opportunity Assistant and Conversational Intelligence package."""

from app.ai.conversation.assistant import OpportunityAssistant
from app.ai.conversation.citations import CitationService
from app.ai.conversation.context import ConversationContext, ProfileContextBuilder
from app.ai.conversation.evidence_selector import EvidenceSelector
from app.ai.conversation.intent import ConversationalIntentClassifier
from app.ai.conversation.memory import ConversationMemory
from app.ai.conversation.orchestrator import ConversationalOrchestrator
from app.ai.conversation.planner import AssistantPlanner, ExecutionPlan, PlanStep
from app.ai.conversation.prompts import PROMPT_VERSION
from app.ai.conversation.response_generator import GroundedResponseGenerator
from app.ai.conversation.safety import PromptInjectionDefense, ToolPermissionGuardrails
from app.ai.conversation.schemas import (
    AssistantIntent,
    AssistantIntentType,
    AssistantResponse,
    AssistantResponseType,
    ChatRequestPayload,
    CitationItem,
    ClaimType,
    ComparisonResult,
    OpportunitySearchPage,
    OpportunitySummary,
    ResponseClaim,
    ToolPermission,
)
from app.ai.conversation.tools import AssistantTools
from app.ai.conversation.validators import ResponseGroundingValidator

__all__ = [
    "PROMPT_VERSION",
    "AssistantIntent",
    "AssistantIntentType",
    "AssistantPlanner",
    "AssistantResponse",
    "AssistantResponseType",
    "AssistantTools",
    "ChatRequestPayload",
    "CitationItem",
    "CitationService",
    "ClaimType",
    "ComparisonResult",
    "ConversationContext",
    "ConversationMemory",
    "ConversationalIntentClassifier",
    "ConversationalOrchestrator",
    "EvidenceSelector",
    "ExecutionPlan",
    "GroundedResponseGenerator",
    "OpportunityAssistant",
    "OpportunitySearchPage",
    "OpportunitySummary",
    "PlanStep",
    "ProfileContextBuilder",
    "PromptInjectionDefense",
    "ResponseClaim",
    "ResponseGroundingValidator",
    "ToolPermission",
    "ToolPermissionGuardrails",
]
