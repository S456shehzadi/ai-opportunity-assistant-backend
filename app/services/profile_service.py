import uuid

from app.core.exceptions import EntityNotFoundException
from app.models.profile import (
    AcademicRecord,
    Certification,
    Language,
    Project,
    Publication,
    ResearchExperience,
    Skill,
    TestResult,
    UserPreferences,
    UserProfile,
    WorkExperience,
)
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.schemas.ai_profile import NormalizedAIProfile
from app.schemas.profile import (
    AcademicRecordCreate,
    CertificationCreate,
    LanguageCreate,
    ProjectCreate,
    PublicationCreate,
    ResearchExperienceCreate,
    SkillCreate,
    TestResultCreate,
    UserPreferencesUpdate,
    UserProfileCreate,
    UserProfileUpdate,
    WorkExperienceCreate,
    WorkExperienceUpdate,
)
from app.services.profile_normalizer import AIProfileContext, ProfileNormalizer


class ProfileService:
    """Business service orchestrating user profile management and AI normalization."""

    def __init__(self, repository: ProfileRepository) -> None:
        self.repo = repository

    async def get_or_create_dev_user(self, email: str = "dev.user@example.com") -> User:
        """Helper for development/testing phases until auth is implemented."""
        return await self.repo.get_or_create_user(email)

    async def get_full_profile(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get_full_user_profile(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return user

    async def get_ai_context(self, user_id: uuid.UUID) -> AIProfileContext:
        user = await self.get_full_profile(user_id)
        return ProfileNormalizer.normalize(user)

    async def get_normalized_ai_profile(self, user_id: uuid.UUID) -> NormalizedAIProfile:
        user = await self.get_full_profile(user_id)
        return ProfileNormalizer.normalize_ai_profile(user)

    async def create_profile(self, user_id: uuid.UUID, data: UserProfileCreate) -> UserProfile:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.upsert_profile(user_id, data.model_dump(exclude_unset=True))

    async def update_profile(self, user_id: uuid.UUID, data: UserProfileUpdate) -> UserProfile:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.upsert_profile(user_id, data.model_dump(exclude_unset=True))

    async def update_preferences(
        self, user_id: uuid.UUID, data: UserPreferencesUpdate
    ) -> UserPreferences:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.upsert_preferences(user_id, data.model_dump(exclude_unset=True))

    # Sub-records
    async def add_academic_record(
        self, user_id: uuid.UUID, data: AcademicRecordCreate
    ) -> AcademicRecord:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.add_academic_record(user_id, data.model_dump())

    async def delete_academic_record(self, user_id: uuid.UUID, record_id: uuid.UUID) -> bool:
        deleted = await self.repo.delete_academic_record(user_id, record_id)
        if not deleted:
            raise EntityNotFoundException("AcademicRecord", record_id)
        return True

    async def add_test_result(self, user_id: uuid.UUID, data: TestResultCreate) -> TestResult:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.add_test_result(user_id, data.model_dump())

    async def add_skill(self, user_id: uuid.UUID, data: SkillCreate) -> Skill:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.add_skill(user_id, data.model_dump())

    async def add_work_experience(
        self, user_id: uuid.UUID, data: WorkExperienceCreate
    ) -> WorkExperience:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.add_work_experience(user_id, data.model_dump())

    async def update_work_experience(
        self, user_id: uuid.UUID, exp_id: uuid.UUID, data: WorkExperienceUpdate
    ) -> WorkExperience:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        exp = await self.repo.update_work_experience(user_id, exp_id, data.model_dump(exclude_unset=True))
        if not exp:
            raise EntityNotFoundException("WorkExperience", exp_id)
        return exp

    async def delete_work_experience(self, user_id: uuid.UUID, exp_id: uuid.UUID) -> bool:
        deleted = await self.repo.delete_work_experience(user_id, exp_id)
        if not deleted:
            raise EntityNotFoundException("WorkExperience", exp_id)
        return True

    async def add_research_experience(
        self, user_id: uuid.UUID, data: ResearchExperienceCreate
    ) -> ResearchExperience:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.add_research_experience(user_id, data.model_dump())

    async def add_publication(self, user_id: uuid.UUID, data: PublicationCreate) -> Publication:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.add_publication(user_id, data.model_dump())

    async def add_project(self, user_id: uuid.UUID, data: ProjectCreate) -> Project:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.add_project(user_id, data.model_dump())

    async def delete_project(self, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        deleted = await self.repo.delete_project(user_id, project_id)
        if not deleted:
            raise EntityNotFoundException("Project", project_id)
        return True

    async def delete_skill(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> bool:
        deleted = await self.repo.delete_skill(user_id, skill_id)
        if not deleted:
            raise EntityNotFoundException("Skill", skill_id)
        return True

    async def add_certification(
        self, user_id: uuid.UUID, data: CertificationCreate
    ) -> Certification:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.add_certification(user_id, data.model_dump())

    async def delete_certification(self, user_id: uuid.UUID, cert_id: uuid.UUID) -> bool:
        deleted = await self.repo.delete_certification(user_id, cert_id)
        if not deleted:
            raise EntityNotFoundException("Certification", cert_id)
        return True

    async def add_language(self, user_id: uuid.UUID, data: LanguageCreate) -> Language:
        user = await self.repo.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return await self.repo.add_language(user_id, data.model_dump())
