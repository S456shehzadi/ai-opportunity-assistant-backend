from app.ai.query.intent_schemas import SearchIntent
from app.ai.query.query_understanding_service import QueryUnderstandingService
from app.core.config import Settings, get_settings
from app.schemas.search_context import OpportunitySearchContext, SearchQuery
from app.services.query_optimizer import QueryOptimizer


class SearchPlanner:
    """Plans and bounds targeted search queries from OpportunitySearchContext."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.max_queries = self.settings.SEARCH_MAX_QUERIES_PER_SEARCH
        self.max_results_per_query = self.settings.SEARCH_MAX_RESULTS_PER_QUERY
        self.query_service = QueryUnderstandingService()

    def plan_from_context(
        self,
        context: OpportunitySearchContext,
        max_queries: int | None = None,
    ) -> list[SearchQuery]:
        """Generates a small, targeted, bounded list of search queries from context."""
        limit = max_queries or self.max_queries
        candidate_queries = context.potential_search_queries

        if not candidate_queries:
            # Fallback to generating queries via optimizer
            candidate_queries = QueryOptimizer.optimize_queries(
                context.search_intent, context.candidate_profile
            )

        # Sort by priority (1 is highest priority)
        sorted_queries = sorted(candidate_queries, key=lambda q: q.priority)

        # Truncate to maximum configured queries
        return sorted_queries[:limit]

    def plan_from_query(
        self,
        raw_query: str,
        max_queries: int | None = None,
    ) -> tuple[SearchIntent, list[SearchQuery]]:
        """Convenience method for generating queries from raw user query."""
        limit = max_queries or self.max_queries
        intent = self.query_service.understand_query(raw_query)
        queries = QueryOptimizer.optimize_queries(intent)
        sorted_queries = sorted(queries, key=lambda q: q.priority)
        return intent, sorted_queries[:limit]
