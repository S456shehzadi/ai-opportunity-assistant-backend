import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, get_db
from app.schemas.search_context import OpportunitySearchContext
from app.search.agent.search_agent import SearchAgent
from app.search.models.search_result import SearchResponse

router = APIRouter(prefix="/search", tags=["Live Web Search"])
search_agent = SearchAgent()


class SearchApiRequest(BaseModel):
    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
        description="Natural language opportunity search question",
    )
    context: OpportunitySearchContext | None = Field(
        default=None,
        description="Structured OpportunitySearchContext from query understanding",
    )
    max_queries: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="Optional limit on planned search queries",
    )
    as_of_date: date | None = Field(
        default=None,
        description="Optional reference date for relative temporal parsing",
    )


@router.post(
    "",
    response_model=SearchResponse,
    summary="Execute planned live web search for opportunities",
)
async def execute_search(
    payload: SearchApiRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Executes planned web search using structured search context or natural language query.

    Orchestrates query planning, multi-provider execution, caching, deduplication,
    and preliminary relevance filtering. Never exposes provider credentials.
    """
    target = payload.context or payload.query
    if not target:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Either 'query' or 'context' must be provided.",
        )

    try:
        response = await search_agent.execute_search(
            query_or_context=target,
            user_id=user_id,
            db_session=db,
            max_queries=payload.max_queries,
        )
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search execution failed: {exc}",
        ) from exc
