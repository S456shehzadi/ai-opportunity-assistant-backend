import uuid

from app.models.profile import EducationLevel, UserPreferences, UserProfile
from app.models.user import User
from app.schemas.search_context import ClarificationImportance, ConflictResolutionType
from app.services.context.context_service import OpportunitySearchContextService
from app.services.profile_normalizer import ProfileNormalizer


def test_conflict_detection_query_overrides_profile_preferences() -> None:
    user_id = uuid.uuid4()
    user = User(id=user_id, email="scholar@test.com", is_active=True)
    user.profile = UserProfile(
        user_id=user_id,
        nationality="Pakistan",
        education_level=EducationLevel.MASTERS,
    )
    user.preferences = UserPreferences(
        user_id=user_id,
        preferred_countries=["Germany"],  # Profile prefers Germany
        preferred_opportunity_categories=["Scholarship"],
    )

    profile = ProfileNormalizer.normalize_ai_profile(user)
    context_service = OpportunitySearchContextService()

    # User asks for Japan explicitly
    ctx = context_service.build_context(
        query="Find opportunities in Japan",
        profile=profile,
    )

    # Must detect conflict: Query (Japan) vs Profile (Germany)
    assert len(ctx.conflicts) >= 1
    conflict = next(c for c in ctx.conflicts if c.field == "country")
    assert "Japan" in conflict.query_value
    assert "Germany" in conflict.profile_value
    assert conflict.resolution == ConflictResolutionType.QUERY_OVERRIDE

    # Japan should be in explicit constraints
    assert "Japan" in ctx.explicit_constraints["countries"]


def test_ambiguity_detection_for_vague_query() -> None:
    user_id = uuid.uuid4()
    user = User(id=user_id, email="newbie@test.com", is_active=True)
    # Minimal profile without degree level or preferences
    profile = ProfileNormalizer.normalize_ai_profile(user)

    context_service = OpportunitySearchContextService()
    ctx = context_service.build_context(
        query="Find scholarships for me",
        profile=profile,
    )

    # Must detect ambiguity
    fields_needing_clarification = [c.field for c in ctx.clarification_requirements]
    assert "degree_level" in fields_needing_clarification
    assert "target_location" in fields_needing_clarification

    # Verify importance
    degree_clarification = next(
        c for c in ctx.clarification_requirements if c.field == "degree_level"
    )
    assert degree_clarification.importance == ClarificationImportance.CRITICAL


def test_strict_separation_of_explicit_and_profile_constraints() -> None:
    user_id = uuid.uuid4()
    user = User(id=user_id, email="applicant@test.com", is_active=True)
    user.profile = UserProfile(
        user_id=user_id,
        nationality="Pakistan",
        country_of_residence="Pakistan",
        education_level=EducationLevel.UNDERGRADUATE,
    )
    profile = ProfileNormalizer.normalize_ai_profile(user)

    context_service = OpportunitySearchContextService()
    ctx = context_service.build_context(
        query="Find scholarships in Italy",
        profile=profile,
    )

    # Italy is EXPLICIT
    assert "Italy" in ctx.explicit_constraints["countries"]

    # Pakistan is PROFILE context, NEVER EXPLICIT
    assert "Pakistan" not in ctx.explicit_constraints.get("countries", [])
    assert ctx.profile_constraints["nationality"] == "Pakistan"
