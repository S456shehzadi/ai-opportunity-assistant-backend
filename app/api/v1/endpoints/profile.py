import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user, get_profile_service
from app.models.user import User
from app.schemas.profile import (
    AcademicRecordCreate,
    AcademicRecordRead,
    CertificationCreate,
    CertificationRead,
    FullUserProfileRead,
    LanguageCreate,
    LanguageRead,
    ProjectCreate,
    ProjectRead,
    PublicationCreate,
    PublicationRead,
    ResearchExperienceCreate,
    ResearchExperienceRead,
    SkillCreate,
    SkillRead,
    TestResultCreate,
    TestResultRead,
    UserPreferencesRead,
    UserPreferencesUpdate,
    UserProfileCreate,
    UserProfileRead,
    UserProfileUpdate,
    WorkExperienceCreate,
    WorkExperienceRead,
    WorkExperienceUpdate,
)
from app.services.profile_normalizer import AIProfileContext
from app.services.profile_service import ProfileService

router = APIRouter()


@router.get(
    "",
    response_model=FullUserProfileRead,
    summary="Get Consolidated User Profile",
    description="Returns the current user's profile and all associated sub-records.",
)
async def get_profile(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> FullUserProfileRead:
    full_user = await service.get_full_profile(current_user.id)
    return FullUserProfileRead.model_validate(full_user)


@router.get(
    "/ai-context",
    response_model=AIProfileContext,
    summary="Get AI-Ready Profile Context",
    description="Returns a normalized, structured profile context for AI matching and reasoning.",
)
async def get_ai_profile_context(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> AIProfileContext:
    return await service.get_ai_context(current_user.id)


@router.post(
    "",
    response_model=UserProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Primary User Profile",
)
async def create_profile(
    data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileRead:
    profile = await service.create_profile(current_user.id, data)
    return UserProfileRead.model_validate(profile)


@router.patch(
    "",
    response_model=UserProfileRead,
    summary="Update Primary User Profile",
)
async def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileRead:
    profile = await service.update_profile(current_user.id, data)
    return UserProfileRead.model_validate(profile)


@router.get(
    "/preferences",
    response_model=UserPreferencesRead,
    summary="Get User Preferences",
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserPreferencesRead:
    full_profile = await service.get_full_profile(current_user.id)
    if full_profile.preferences:
        return UserPreferencesRead.model_validate(full_profile.preferences)
    return UserPreferencesRead(
        id=uuid.uuid4(),
        user_id=current_user.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@router.put(
    "/preferences",
    response_model=UserPreferencesRead,
    summary="Update User Preferences",
)
@router.patch(
    "/preferences",
    response_model=UserPreferencesRead,
    summary="Patch User Preferences",
    include_in_schema=False,
)
async def update_preferences(
    data: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserPreferencesRead:
    prefs = await service.update_preferences(current_user.id, data)
    return UserPreferencesRead.model_validate(prefs)


# Sub-resources
@router.post(
    "/academic-records",
    response_model=AcademicRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Academic Record",
)
async def add_academic_record(
    data: AcademicRecordCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> AcademicRecordRead:
    record = await service.add_academic_record(current_user.id, data)
    return AcademicRecordRead.model_validate(record)


@router.delete(
    "/academic-records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Academic Record",
)
async def delete_academic_record(
    record_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> None:
    await service.delete_academic_record(current_user.id, record_id)


@router.post(
    "/test-results",
    response_model=TestResultRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Standardized Test Result",
)
async def add_test_result(
    data: TestResultCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> TestResultRead:
    test = await service.add_test_result(current_user.id, data)
    return TestResultRead.model_validate(test)


@router.post(
    "/skills",
    response_model=SkillRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add User Skill",
)
async def add_skill(
    data: SkillCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> SkillRead:
    skill = await service.add_skill(current_user.id, data)
    return SkillRead.model_validate(skill)


@router.post(
    "/work-experience",
    response_model=WorkExperienceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Work Experience",
)
@router.post(
    "/experience",
    response_model=WorkExperienceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Experience (Alias)",
    include_in_schema=False,
)
async def add_work_experience(
    data: WorkExperienceCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> WorkExperienceRead:
    work = await service.add_work_experience(current_user.id, data)
    return WorkExperienceRead.model_validate(work)


@router.patch(
    "/work-experience/{exp_id}",
    response_model=WorkExperienceRead,
    summary="Update Work Experience",
)
@router.patch(
    "/experience/{exp_id}",
    response_model=WorkExperienceRead,
    summary="Update Experience (Alias)",
    include_in_schema=False,
)
async def update_work_experience(
    exp_id: uuid.UUID,
    data: WorkExperienceUpdate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> WorkExperienceRead:
    work = await service.update_work_experience(current_user.id, exp_id, data)
    return WorkExperienceRead.model_validate(work)


@router.delete(
    "/work-experience/{exp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Work Experience",
)
@router.delete(
    "/experience/{exp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Experience (Alias)",
    include_in_schema=False,
)
async def delete_work_experience(
    exp_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> None:
    await service.delete_work_experience(current_user.id, exp_id)


@router.post(
    "/research-experience",
    response_model=ResearchExperienceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Research Experience",
)
async def add_research_experience(
    data: ResearchExperienceCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ResearchExperienceRead:
    res = await service.add_research_experience(current_user.id, data)
    return ResearchExperienceRead.model_validate(res)


@router.post(
    "/publications",
    response_model=PublicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Publication",
)
async def add_publication(
    data: PublicationCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> PublicationRead:
    pub = await service.add_publication(current_user.id, data)
    return PublicationRead.model_validate(pub)


@router.post(
    "/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Project",
)
async def add_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ProjectRead:
    proj = await service.add_project(current_user.id, data)
    return ProjectRead.model_validate(proj)


@router.post(
    "/languages",
    response_model=LanguageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Language",
)
async def add_language(
    data: LanguageCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> LanguageRead:
    lang = await service.add_language(current_user.id, data)
    return LanguageRead.model_validate(lang)


@router.delete(
    "/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Skill",
)
async def delete_skill(
    skill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> None:
    await service.delete_skill(current_user.id, skill_id)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Project",
)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> None:
    await service.delete_project(current_user.id, project_id)


@router.post(
    "/certifications",
    response_model=CertificationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Certification",
)
async def add_certification(
    data: CertificationCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> CertificationRead:
    cert = await service.add_certification(current_user.id, data)
    return CertificationRead.model_validate(cert)


@router.delete(
    "/certifications/{cert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Certification",
)
async def delete_certification(
    cert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> None:
    await service.delete_certification(current_user.id, cert_id)
