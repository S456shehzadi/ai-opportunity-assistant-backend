from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    assistant,
    auth,
    beta,
    discovery,
    eligibility,
    evaluation,
    feedback,
    health,
    model_registry,
    monitoring,
    notifications,
    opportunities,
    profile,
    query,
    ranking,
    review,
    search,
    training,
    web,
)

api_v1_router = APIRouter()

# Core system endpoints
api_v1_router.include_router(health.router, tags=["System"])

# Authentication & Access Control endpoints
api_v1_router.include_router(auth.router)

# User Profile endpoints
api_v1_router.include_router(profile.router, prefix="/profile", tags=["Profile"])

# Query Understanding & Context endpoints
api_v1_router.include_router(query.router)

# Live Web Search endpoints
api_v1_router.include_router(search.router)

# Advanced Semantic Opportunity Discovery & Retrieval endpoints
api_v1_router.include_router(discovery.router)

# Web Retrieval & Content Extraction endpoints
api_v1_router.include_router(web.router)

# AI Opportunity Extraction & Intelligence Engine endpoints
api_v1_router.include_router(opportunities.router)

# AI Eligibility Matching & Personalized Intelligence endpoints
api_v1_router.include_router(eligibility.router)

# Personalized Opportunity Discovery & Ranking endpoints
api_v1_router.include_router(ranking.router)

# Grounded AI Opportunity Assistant endpoints
api_v1_router.include_router(assistant.router)

# Opportunity Monitoring & Sweeps endpoints
api_v1_router.include_router(monitoring.router)

# User Notifications & Preferences endpoints
api_v1_router.include_router(notifications.router)

# User Feedback & Error Reporting endpoints
api_v1_router.include_router(feedback.router)

# Privacy-Preserving Analytics endpoints
api_v1_router.include_router(analytics.router)

# Human-in-the-Loop Review Queue endpoints
api_v1_router.include_router(review.router)

# Benchmark Evaluation & Datasets endpoints
api_v1_router.include_router(evaluation.router)

# Model Training & Fine-Tuning endpoints
api_v1_router.include_router(training.router)

# Specialized Model Registry & Governance endpoints
api_v1_router.include_router(model_registry.router)

# Beta Launch, Feature Flags, Triage & Observability endpoints
api_v1_router.include_router(beta.router)
