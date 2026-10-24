from app.ai.query.query_understanding_service import QueryUnderstandingService
from app.models.profile import EducationLevel, UserProfile
from app.models.user import User
from app.search.planner.search_planner import SearchPlanner
from app.services.context.context_service import OpportunitySearchContextService
from app.services.profile_normalizer import ProfileNormalizer


def test_search_planner_bounds_queries() -> None:
    planner = SearchPlanner()
    intent, queries = planner.plan_from_query(
        "Find fully funded master's scholarships in Europe for computer science without IELTS.",
        max_queries=2,
    )

    # Must be bounded by max_queries
    assert len(queries) == 2
    assert queries[0].priority <= queries[1].priority


def test_search_planner_plans_from_context() -> None:
    import uuid

    query_service = QueryUnderstandingService()
    intent = query_service.understand_query("Find master's scholarships in Germany")

    user = User(id=uuid.uuid4(), email="applicant@test.com", is_active=True)
    user.profile = UserProfile(
        nationality="Pakistan",
        education_level=EducationLevel.UNDERGRADUATE,
    )
    profile = ProfileNormalizer.normalize_ai_profile(user)

    ctx_service = OpportunitySearchContextService(query_service=query_service)
    context = ctx_service.build_context(intent, profile)

    planner = SearchPlanner()
    queries = planner.plan_from_context(context, max_queries=3)

    assert len(queries) <= 3
    # Check that planned queries address Germany and scholarships
    query_texts = [q.query.lower() for q in queries]
    assert any("germany" in q for q in query_texts)
