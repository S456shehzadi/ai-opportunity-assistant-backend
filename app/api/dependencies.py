import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.jwt import decode_token
from app.core.auth.token_blacklist import get_token_blacklist_service
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.models.user import User, UserRole
from app.repositories.profile_repository import ProfileRepository
from app.services.profile_service import ProfileService


def get_current_settings(
    settings: Settings = Depends(get_settings),
) -> Settings:
    """Dependency injection for application settings."""
    return settings


async def get_db(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for async database session."""
    yield session


async def get_optional_db(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[AsyncSession | None, None]:
    """Dependency injection for optional async database session."""
    yield session


def get_profile_repository(
    session: AsyncSession = Depends(get_db),
) -> ProfileRepository:
    """Dependency providing ProfileRepository bound to request session."""
    return ProfileRepository(session)


def get_profile_service(
    repo: ProfileRepository = Depends(get_profile_repository),
) -> ProfileService:
    """Dependency providing ProfileService."""
    return ProfileService(repo)


async def get_current_dev_user(
    service: ProfileService = Depends(get_profile_service),
    session: AsyncSession = Depends(get_db),
) -> User:
    """DEVELOPMENT ONLY: Returns a persistent development user for testing endpoints

    before full authentication is implemented. Falls back gracefully when database is offline.
    """
    try:
        return await service.get_or_create_dev_user("developer@example.com")
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass
        return User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="developer@example.com",
            is_active=True,
        )


async def get_current_user(
    authorization: str | None = Header(default=None),
    dev_user: User = Depends(get_current_dev_user),
    service: ProfileService = Depends(get_profile_service),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Authenticates user via Bearer JWT token or falls back to development user."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ")[1]
        try:
            claims = decode_token(token)
            jti = claims.get("jti")
            blacklist = get_token_blacklist_service()
            if jti and await blacklist.is_revoked(jti, db=session):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication token has been revoked",
                )

            user_id = uuid.UUID(claims.get("sub", ""))
            query = select(User).where(User.id == user_id)
            res = await session.execute(query)
            user = res.scalar_one_or_none()
            if user and user.is_active:
                return user
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or not found",
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(exc)}",
            ) from exc

    # In development/testing environments, provide development user
    if not settings.is_production:
        return dev_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


async def get_current_user_id(
    user: User = Depends(get_current_user),
) -> uuid.UUID:
    """Returns current user's UUID."""
    return user.id


async def get_current_reviewer_user(
    user: User = Depends(get_current_user),
) -> User:
    """Verifies user has at least REVIEWER or ADMIN role."""
    if user.role not in (UserRole.REVIEWER, UserRole.ADMIN, UserRole.DATA_REVIEWER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer authorization required",
        )
    return user


async def get_current_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """Verifies user has ADMIN role."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin authorization required",
        )
    return user
