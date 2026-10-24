"""REST API endpoints for AI Opportunity Extraction & Intelligence Engine."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user_id, get_db, get_optional_db
from app.models.opportunity import Opportunity
from app.opportunities.extraction.deduplication import OpportunityDeduplicator
from app.opportunities.extraction.engine import OpportunityExtractionEngine
from app.opportunities.extraction.schemas import ExtractedOpportunity
from app.schemas.opportunity import OpportunityRead
from app.web.models.document import WebDocument
from app.web.service import WebRetrievalService

router = APIRouter(prefix="/opportunities", tags=["AI Opportunity Extraction"])
web_service = WebRetrievalService()
extraction_engine = OpportunityExtractionEngine()


class OpportunityExtractRequest(BaseModel):
    """Request payload for extracting an opportunity from a URL or pre-retrieved document."""

    url: str | None = Field(
        default=None,
        description="Target web URL to retrieve and extract",
        examples=["https://www.daad.de/en/study-and-research-in-germany/scholarships/"],
    )
    document: WebDocument | None = Field(
        default=None,
        description="Direct WebDocument payload if already retrieved",
    )


class OpportunityBatchExtractRequest(BaseModel):
    """Request payload for multi-page opportunity extraction and consolidation."""

    urls: list[str] = Field(
        default_factory=list,
        description="List of related opportunity URLs (e.g. overview, eligibility, funding)",
    )
    documents: list[WebDocument] = Field(
        default_factory=list,
        description="List of pre-retrieved WebDocument instances to aggregate",
    )


class DeduplicateCheckRequest(BaseModel):
    """Payload to check duplicate status between two programs."""

    title_a: str
    organization_a: str
    url_a: str
    title_b: str
    organization_b: str
    url_b: str


class DeduplicateCheckResponse(BaseModel):
    """Response indicating whether opportunities match."""

    is_duplicate: bool
    canonical_key_a: str
    canonical_key_b: str


@router.post(
    "/extract",
    response_model=ExtractedOpportunity,
    summary="Extract structured opportunity facts from a webpage or WebDocument",
)
async def extract_opportunity(
    payload: OpportunityExtractRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_optional_db),
) -> ExtractedOpportunity:
    """Extracts a fully grounded ExtractedOpportunity record with authentic evidence provenance."""
    doc = payload.document
    if doc is None:
        if not payload.url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'url' or 'document' must be provided.",
            )
        try:
            doc = await web_service.retrieve_and_process(payload.url)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to retrieve webpage: {exc}",
            ) from exc

    return await extraction_engine.extract(doc)


@router.post(
    "/extract-batch",
    response_model=ExtractedOpportunity,
    summary="Consolidate facts across multiple pages of an opportunity",
)
async def extract_batch_opportunity(
    payload: OpportunityBatchExtractRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_optional_db),
) -> ExtractedOpportunity:
    """Combines facts across multiple related pages into a single consolidated record."""
    docs = list(payload.documents)
    for url in payload.urls:
        try:
            doc = await web_service.retrieve_and_process(url)
            docs.append(doc)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to retrieve URL {url}: {exc}",
            ) from exc

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one URL or WebDocument must be provided.",
        )

    return await extraction_engine.extract_batch(docs)


@router.post(
    "/deduplicate",
    response_model=DeduplicateCheckResponse,
    summary="Check if two opportunities represent the same program",
)
async def check_duplicate_opportunities(
    payload: DeduplicateCheckRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> DeduplicateCheckResponse:
    """Checks equality between two opportunities and computes their canonical keys."""
    is_dup = OpportunityDeduplicator.are_duplicates(
        title_a=payload.title_a,
        org_a=payload.organization_a,
        url_a=payload.url_a,
        title_b=payload.title_b,
        org_b=payload.organization_b,
        url_b=payload.url_b,
    )
    key_a = OpportunityDeduplicator.generate_canonical_key(
        title=payload.title_a,
        organization=payload.organization_a,
        category="other",
        official_url=payload.url_a,
    )
    key_b = OpportunityDeduplicator.generate_canonical_key(
        title=payload.title_b,
        organization=payload.organization_b,
        category="other",
        official_url=payload.url_b,
    )
    return DeduplicateCheckResponse(
        is_duplicate=is_dup,
        canonical_key_a=key_a,
        canonical_key_b=key_b,
    )


@router.get(
    "/{opportunity_id}",
    response_model=OpportunityRead,
    summary="Get opportunity details by ID",
)
async def get_opportunity(
    opportunity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OpportunityRead:
    """Retrieves full opportunity details including requirements and official sources."""
    query = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.sources),
            selectinload(Opportunity.requirements),
        )
        .where(Opportunity.id == opportunity_id)
    )
    res = await db.execute(query)
    opp = res.scalar_one_or_none()
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {opportunity_id} not found",
        )
    return OpportunityRead.model_validate(opp)


@router.get(
    "",
    response_model=list[OpportunityRead],
    summary="List opportunities",
)
async def list_opportunities(
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[OpportunityRead]:
    """Lists opportunities with optional category filtering and pagination."""
    query = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.sources),
            selectinload(Opportunity.requirements),
        )
        .order_by(Opportunity.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if category:
        query = query.where(Opportunity.category == category)
    res = await db.execute(query)
    return [OpportunityRead.model_validate(o) for o in res.scalars().all()]
