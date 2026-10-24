import asyncio
import logging
import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.query.query_understanding_service import QueryUnderstandingService
from app.core.config import Settings, get_settings
from app.models.interaction import SearchSession
from app.schemas.search_context import OpportunitySearchContext, SearchQuery
from app.search.cache.search_cache import SearchCache, get_search_cache
from app.search.deduplication.deduplicator import SearchResultDeduplicator
from app.search.interfaces.search_provider import SearchProvider
from app.search.models.search_result import NormalizedSearchResult, SearchResponse
from app.search.planner.search_planner import SearchPlanner
from app.search.providers.provider_factory import SearchProviderFactory
from app.search.relevance.relevance_filter import PreliminaryRelevanceFilter
from app.search.retrieval.rate_limiter import SearchRateLimiter

logger = logging.getLogger(__name__)


class SearchAgent:
    """Production Search Agent orchestrating search planning, multi-provider execution,

    caching, rate limiting, deduplication, and relevance filtering.
    """

    def __init__(
        self,
        provider: SearchProvider | None = None,
        planner: SearchPlanner | None = None,
        cache: SearchCache | None = None,
        rate_limiter: SearchRateLimiter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider = provider or SearchProviderFactory.create_resilient_provider(self.settings)
        self.planner = planner or SearchPlanner(self.settings)
        self.cache = cache or get_search_cache(self.settings)
        self.rate_limiter = rate_limiter or SearchRateLimiter(
            requests_per_second=float(self.settings.SEARCH_RATE_LIMIT)
        )
        self.query_service = QueryUnderstandingService()
        self._concurrency_sem = asyncio.Semaphore(3)

    async def execute_search(
        self,
        query_or_context: str | OpportunitySearchContext,
        user_id: uuid.UUID | None = None,
        db_session: AsyncSession | None = None,
        max_queries: int | None = None,
    ) -> SearchResponse:
        """Executes full search pipeline for given query or context."""
        start_time = time.monotonic()
        search_id = uuid.uuid4()
        warnings: list[str] = []

        # 1. Resolve Query & SearchIntent
        if isinstance(query_or_context, str):
            original_query = query_or_context.strip()
            intent, planned_queries = self.planner.plan_from_query(
                original_query, max_queries=max_queries
            )
        else:
            intent = query_or_context.search_intent
            original_query = intent.original_query
            planned_queries = self.planner.plan_from_context(
                query_or_context, max_queries=max_queries
            )

        executed_query_strings = [q.query for q in planned_queries]
        logger.info(
            "SearchAgent [%s]: Planned %d queries for query: '%s'",
            search_id,
            len(planned_queries),
            original_query,
        )

        # 2. Concurrently Execute Queries with Rate-Limiting & Cache
        tasks = [
            self._execute_single_query(
                query_obj=q,
                max_results=self.settings.SEARCH_MAX_RESULTS_PER_QUERY,
            )
            for q in planned_queries
        ]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        all_raw_results: list[NormalizedSearchResult] = []
        for idx, res in enumerate(results_nested):
            if isinstance(res, Exception):
                warning_msg = f"Query '{planned_queries[idx].query}' failed: {res}"
                logger.warning("SearchAgent [%s]: %s", search_id, warning_msg)
                warnings.append(warning_msg)
            elif isinstance(res, list):
                all_raw_results.extend(res)

        # 3. Deduplication & Domain Diversification
        deduped = SearchResultDeduplicator.deduplicate(
            results=all_raw_results,
            max_per_domain=3,
            max_total=self.settings.SEARCH_MAX_TOTAL_RESULTS,
        )

        # 4. Preliminary Relevance Filtering & Official Source Scoring
        final_results = PreliminaryRelevanceFilter.filter_and_score(
            results=deduped,
            intent=intent,
            min_relevance_threshold=0.3,
        )

        duration_ms = round((time.monotonic() - start_time) * 1000.0, 2)

        # 5. Optional DB Session Persistence
        if db_session:
            try:
                session_record = SearchSession(
                    id=search_id,
                    user_id=user_id,
                    query=original_query[:1000],
                    status="completed" if final_results else "empty",
                )
                db_session.add(session_record)
                await db_session.commit()
            except Exception as exc:
                logger.warning(
                    "SearchAgent [%s]: Could not persist session to DB: %s", search_id, exc
                )
                try:
                    await db_session.rollback()
                except Exception:
                    pass

        logger.info(
            "SearchAgent [%s]: Completed with %d results in %.2fms",
            search_id,
            len(final_results),
            duration_ms,
        )

        return SearchResponse(
            search_id=search_id,
            original_query=original_query,
            executed_queries=executed_query_strings,
            results=final_results,
            total_results=len(final_results),
            provider_used=self.provider.provider_name,
            duration_ms=duration_ms,
            warnings=warnings,
        )

    async def _execute_single_query(
        self,
        query_obj: SearchQuery,
        max_results: int,
    ) -> list[NormalizedSearchResult]:
        """Executes a single search query through cache, semaphore, and rate limiter."""
        async with self._concurrency_sem:
            # 1. Cache Check
            cached = await self.cache.get(
                provider=self.provider.provider_name,
                query=query_obj.query,
                max_results=max_results,
            )
            if cached is not None:
                return cached

            # 2. Live Provider Call with Rate Limiting & Safe Retries
            async def _call() -> list[NormalizedSearchResult]:
                return await self.provider.search_items(
                    query=query_obj.query,
                    max_results=max_results,
                    query_purpose=query_obj.purpose,
                )

            items = await self.rate_limiter.execute_with_retry(
                _call,
                max_retries=3,
                base_delay=0.5,
            )

            # 3. Store in Cache
            await self.cache.set(
                provider=self.provider.provider_name,
                query=query_obj.query,
                max_results=max_results,
                results=items,
                ttl_seconds=3600,
            )

            return items

    async def retrieve_documents(
        self,
        search_response: SearchResponse,
        max_documents: int = 5,
        web_service: Any | None = None,
        db_session: AsyncSession | None = None,
    ) -> list[Any]:
        """Bridges search results into retrieved and cleaned WebDocuments.

        Retrieves top search results up to max_documents without final opportunity extraction.
        """
        from app.web.service import WebRetrievalService

        service = web_service or WebRetrievalService()
        top_results = search_response.results[:max_documents]
        return await service.retrieve_search_results(top_results, db_session=db_session)
