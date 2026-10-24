"""REST API endpoints for web retrieval and webpage content extraction."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, get_optional_db
from app.web.models.document import WebDocument
from app.web.models.errors import (
    ContentTooLargeError,
    InvalidURLError,
    RobotsDisallowedError,
    SSRFBlockedError,
    UnsupportedContentTypeError,
    WebTimeoutError,
)
from app.web.service import WebRetrievalService

router = APIRouter(prefix="/web", tags=["Web Retrieval & Content Extraction"])
web_service = WebRetrievalService()


class RetrieveUrlRequest(BaseModel):
    url: str = Field(
        ...,
        min_length=5,
        max_length=2048,
        description="Target web URL to retrieve and extract (http:// or https://)",
        examples=["https://www.daad.de/en/study-and-research-in-germany/scholarships/"],
    )
    force_refresh: bool = Field(
        default=False,
        description="Whether to bypass cache and force fresh retrieval",
    )


class BatchRetrieveRequest(BaseModel):
    urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of target URLs to retrieve concurrently (up to 10)",
    )
    force_refresh: bool = Field(
        default=False,
        description="Whether to bypass cache and force fresh retrieval",
    )


@router.post(
    "/retrieve",
    response_model=WebDocument,
    summary="Retrieve and extract clean structured document from a webpage",
)
async def retrieve_webpage(
    payload: RetrieveUrlRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_optional_db),
) -> WebDocument:
    """Retrieves target webpage, executes SSRF & robots checks, parses HTML,

    and extracts structured headings, tables, links, metadata, and candidate dates.
    """
    try:
        doc = await web_service.retrieve_document(
            url=payload.url,
            force_refresh=payload.force_refresh,
            db_session=db,
        )
        return doc
    except InvalidURLError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL: {exc.message}",
        ) from exc
    except SSRFBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security violation (SSRF blocked): {exc.message}",
        ) from exc
    except RobotsDisallowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Crawling disallowed by robots.txt: {exc.message}",
        ) from exc
    except ContentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Page exceeds size limit: {exc.message}",
        ) from exc
    except UnsupportedContentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {exc.message}",
        ) from exc
    except WebTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Gateway timeout: {exc.message}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Web retrieval failed: {exc}",
        ) from exc


@router.post(
    "/batch-retrieve",
    response_model=list[dict],
    summary="Batch retrieve multiple webpages concurrently",
)
async def batch_retrieve_webpages(
    payload: BatchRetrieveRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession | None = Depends(get_optional_db),
) -> list[dict]:
    """Retrieves up to 10 URLs concurrently with per-domain polite throttling."""
    results = await web_service.retrieve_batch(
        urls=payload.urls,
        force_refresh=payload.force_refresh,
        db_session=db,
    )
    serialized: list[dict] = []
    for item in results:
        if isinstance(item, WebDocument):
            serialized.append(item.model_dump())
        elif isinstance(item, dict):
            serialized.append(item)
    return serialized
