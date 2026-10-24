import uuid

from app.ai.query.query_understanding_service import QueryUnderstandingService
from app.models.profile import EducationLevel, UserProfile
from app.models.user import User
from app.services.profile_normalizer import ProfileNormalizer
from app.services.query_optimizer import QueryOptimizer


def test_query_optimizer_generates_multiple_targeted_queries() -> None:
    service = QueryUnderstandingService()
    intent = service.understand_query(
        "Find fully funded master's scholarships in Europe for computer science without IELTS."
    )

    queries = QueryOptimizer.optimize_queries(intent)

    # Must generate multiple queries (Priority 1 direct, Priority 2 no-IELTS, Priority 2 portal)
    assert len(queries) >= 3

    # Primary query
    p1 = next(q for q in queries if q.priority == 1)
    assert "fully funded" in p1.query.lower()
    assert "computer science" in p1.query.lower()
    assert "scholarship" in p1.query.lower()

    # IELTS-specific query
    ielts_query = next(q for q in queries if "no_ielts" in q.purpose)
    assert "ielts" in ielts_query.query.lower()

    # Official portal query (Europe -> Erasmus Mundus)
    portal_query = next(q for q in queries if q.source_type == "official_portal")
    assert "erasmus mundus" in portal_query.query.lower()

    # Excluded terms
    assert "undergraduate" in p1.excluded_terms or "bachelor" in p1.excluded_terms


def test_query_optimizer_profile_enrichment() -> None:
    service = QueryUnderstandingService()
    intent = service.understand_query("Find master's scholarships in Germany")

    user_id = uuid.uuid4()
    user = User(id=user_id, email="student@test.com", is_active=True)
    user.profile = UserProfile(
        user_id=user_id,
        nationality="Pakistan",
        education_level=EducationLevel.UNDERGRADUATE,
    )
    profile = ProfileNormalizer.normalize_ai_profile(user)

    queries = QueryOptimizer.optimize_queries(intent, profile=profile)

    # Must include nationality-eligible search query
    nat_query = next(q for q in queries if q.purpose == "nationality_eligible_search")
    assert "Pakistan" in nat_query.query
