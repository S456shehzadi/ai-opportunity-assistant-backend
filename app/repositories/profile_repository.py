import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
                selectinload(User.certifications),
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
        # Prevent duplicate records on repeated requests
        deg = data.get("degree")
        inst = data.get("institution")
        field = data.get("field_of_study")
        if deg and inst:
            stmt = select(AcademicRecord).where(
                AcademicRecord.user_id == user_id,
                AcademicRecord.degree == deg,
                AcademicRecord.institution == inst,
            )
            res = await self.session.execute(stmt)
            existing = res.scalars().first()
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k) and v is not None:
                        setattr(existing, k, v)
                await self.session.flush()
                return existing

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
        name = data.get("name")
        if name:
            stmt = select(Skill).where(
                Skill.user_id == user_id,
                Skill.name.ilike(name.strip())
            )
            res = await self.session.execute(stmt)
            existing = res.scalars().first()
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k) and v is not None:
                        setattr(existing, k, v)
                await self.session.flush()
                return existing

        skill = Skill(user_id=user_id, **data)
        self.session.add(skill)
        await self.session.flush()
        return skill

    async def delete_skill(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> bool:
        stmt = select(Skill).where(
            Skill.id == skill_id, Skill.user_id == user_id
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            await self.session.delete(record)
            await self.session.flush()
            return True
        return False

    # Work Experiences
    async def add_work_experience(self, user_id: uuid.UUID, data: dict[str, Any]) -> WorkExperience:
        title = data.get("job_title")
        org = data.get("organization")
        cat = data.get("category", "Employment")
        if title and org:
            stmt = select(WorkExperience).where(
                WorkExperience.user_id == user_id,
                WorkExperience.job_title.ilike(title.strip()),
                WorkExperience.organization.ilike(org.strip()),
                WorkExperience.category == cat,
            )
            res = await self.session.execute(stmt)
            existing = res.scalars().first()
            if existing:
                for k, v in data.items():
                    if hasattr(existing, k) and v is not None:
                        setattr(existing, k, v)
                await self.session.flush()
                return existing

        work = WorkExperience(user_id=user_id, **data)
        self.session.add(work)
        await self.session.flush()
        return work

    async def update_work_experience(
        self, user_id: uuid.UUID, exp_id: uuid.UUID, data: dict[str, Any]
    ) -> WorkExperience | None:
        stmt = select(WorkExperience).where(
            WorkExperience.id == exp_id, WorkExperience.user_id == user_id
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            return None
        for k, v in data.items():
            if hasattr(record, k) and v is not None:
                setattr(record, k, v)
        await self.session.flush()
        return record

    async def delete_work_experience(self, user_id: uuid.UUID, exp_id: uuid.UUID) -> bool:
        stmt = select(WorkExperience).where(
            WorkExperience.id == exp_id, WorkExperience.user_id == user_id
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            await self.session.delete(record)
            await self.session.flush()
            return True
        return False

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

    async def delete_project(self, user_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        stmt = select(Project).where(Project.id == project_id, Project.user_id == user_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            await self.session.delete(record)
            await self.session.flush()
            return True
        return False

    # Certifications
    async def add_certification(self, user_id: uuid.UUID, data: dict[str, Any]) -> Certification:
        cert = Certification(user_id=user_id, **data)
        self.session.add(cert)
        await self.session.flush()
        return cert

    async def delete_certification(self, user_id: uuid.UUID, cert_id: uuid.UUID) -> bool:
        stmt = select(Certification).where(
            Certification.id == cert_id, Certification.user_id == user_id
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            await self.session.delete(record)
            await self.session.flush()
            return True
        return False

    # Languages
    async def add_language(self, user_id: uuid.UUID, data: dict[str, Any]) -> Language:
        lang = Language(user_id=user_id, **data)
        self.session.add(lang)
        await self.session.flush()
        return lang
