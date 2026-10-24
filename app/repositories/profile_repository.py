import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.profile import (
    AcademicRecord,
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


class ProfileRepository:
    """Async repository for User Profile and related multidimensional sub-records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_user(self, email: str) -> User:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            user = User(email=email, is_active=True)
            self.session.add(user)
            await self.session.flush()
        return user

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_full_user_profile(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.profile),
                selectinload(User.preferences),
                selectinload(User.academic_records),
                selectinload(User.test_results),
                selectinload(User.skills),
                selectinload(User.work_experiences),
                selectinload(User.research_experiences),
                selectinload(User.publications),
                selectinload(User.projects),
                selectinload(User.languages),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_profile(self, user_id: uuid.UUID, profile_data: dict[str, Any]) -> UserProfile:
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await self.session.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile:
            for k, v in profile_data.items():
                if v is not None:
                    setattr(profile, k, v)
        else:
            profile = UserProfile(user_id=user_id, **profile_data)
            self.session.add(profile)

        await self.session.flush()
        return profile

    async def upsert_preferences(
        self, user_id: uuid.UUID, prefs_data: dict[str, Any]
    ) -> UserPreferences:
        stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
        result = await self.session.execute(stmt)
        prefs = result.scalar_one_or_none()

        if prefs:
            for k, v in prefs_data.items():
                if v is not None:
                    setattr(prefs, k, v)
        else:
            prefs = UserPreferences(user_id=user_id, **prefs_data)
            self.session.add(prefs)

        await self.session.flush()
        return prefs

    # Academic Records
    async def add_academic_record(self, user_id: uuid.UUID, data: dict[str, Any]) -> AcademicRecord:
        record = AcademicRecord(user_id=user_id, **data)
        self.session.add(record)
        await self.session.flush()
        return record

    async def delete_academic_record(self, user_id: uuid.UUID, record_id: uuid.UUID) -> bool:
        stmt = select(AcademicRecord).where(
            AcademicRecord.id == record_id, AcademicRecord.user_id == user_id
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            await self.session.delete(record)
            await self.session.flush()
            return True
        return False

    # Test Results
    async def add_test_result(self, user_id: uuid.UUID, data: dict[str, Any]) -> TestResult:
        test = TestResult(user_id=user_id, **data)
        self.session.add(test)
        await self.session.flush()
        return test

    # Skills
    async def add_skill(self, user_id: uuid.UUID, data: dict[str, Any]) -> Skill:
        skill = Skill(user_id=user_id, **data)
        self.session.add(skill)
        await self.session.flush()
        return skill

    # Work Experiences
    async def add_work_experience(self, user_id: uuid.UUID, data: dict[str, Any]) -> WorkExperience:
        work = WorkExperience(user_id=user_id, **data)
        self.session.add(work)
        await self.session.flush()
        return work

    # Research Experiences
    async def add_research_experience(
        self, user_id: uuid.UUID, data: dict[str, Any]
    ) -> ResearchExperience:
        research = ResearchExperience(user_id=user_id, **data)
        self.session.add(research)
        await self.session.flush()
        return research

    # Publications
    async def add_publication(self, user_id: uuid.UUID, data: dict[str, Any]) -> Publication:
        pub = Publication(user_id=user_id, **data)
        self.session.add(pub)
        await self.session.flush()
        return pub

    # Projects
    async def add_project(self, user_id: uuid.UUID, data: dict[str, Any]) -> Project:
        proj = Project(user_id=user_id, **data)
        self.session.add(proj)
        await self.session.flush()
        return proj

    # Languages
    async def add_language(self, user_id: uuid.UUID, data: dict[str, Any]) -> Language:
        lang = Language(user_id=user_id, **data)
        self.session.add(lang)
        await self.session.flush()
        return lang
