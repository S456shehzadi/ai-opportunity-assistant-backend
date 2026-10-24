import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.query.intent_schemas import SearchIntent
from app.ai.query.query_understanding_service import QueryUnderstandingService
from app.api.dependencies import get_current_user_id, get_profile_service
from app.schemas.search_context import OpportunitySearchContext, SearchQuery
from app.services.context.context_service import OpportunitySearchContextService
from app.services.profile_service import ProfileService
from app.services.query_optimizer import QueryOptimizer

router = APIRouter(prefix="/query", tags=["Query Understanding"])

query_service = QueryUnderstandingService()
context_service = OpportunitySearchContextService(query_service=query_service)


class QueryRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, max_length=1000, description="Natural language user question"
    )
    as_of_date: date | None = Field(
        default=None, description="Optional override date for temporal parsing"
    )


class QueryOptimizeRequest(BaseModel):
    query: str | None = Field(default=None, description="Raw query string")
    intent: SearchIntent | None = Field(default=None, description="Pre-computed SearchIntent")


@router.post(
    "/understand",
    response_model=SearchIntent,
    summary="Understand natural language query intent and extract constraints",
)
async def understand_query(payload: QueryRequest) -> SearchIntent:
    """Parses natural-language user query into structured search intent without external AI APIs."""
    return query_service.understand_query(payload.query, as_of_date=payload.as_of_date)


@router.post(
    "/context",
    response_model=OpportunitySearchContext,
    summary="Construct unified search context fusing user profile and query intent",
)
async def build_search_context(
    payload: QueryRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    profile_service: ProfileService = Depends(get_profile_service),
) -> OpportunitySearchContext:
    """Fuses current user's normalized profile with the query intent,

    executing conflict and ambiguity detection.
    """
    try:
        normalized_profile = await profile_service.get_normalized_ai_profile(user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User profile could not be loaded: {exc}",
        ) from exc

    intent = query_service.understand_query(payload.query, as_of_date=payload.as_of_date)
    return context_service.build_context(intent, normalized_profile)


@router.post(
    "/optimize",
    response_model=list[SearchQuery],
    summary="Generate optimized web search queries from natural language or intent",
)
async def optimize_query(payload: QueryOptimizeRequest) -> list[SearchQuery]:
    """Generates multiple targeted search queries tailored for search engine retrieval."""
    if payload.intent:
        intent = payload.intent
    elif payload.query:
        intent = query_service.understand_query(payload.query)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'query' or 'intent' must be provided",
        )

    return QueryOptimizer.optimize_queries(intent)
