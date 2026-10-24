from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import AppEnvironment, Settings, get_settings
from app.core.database import get_db_session
from app.main import create_application
from app.models.base import Base


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        APP_ENV=AppEnvironment.TESTING,
        APP_NAME="AI Opportunity Assistant API [Test]",
        APP_VERSION="0.1.0",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        AI_MODEL_PROVIDER="mock",
        SEARCH_PROVIDER="mock",
    )


@pytest.fixture
async def test_db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(
    test_settings: Settings, test_db_session: AsyncSession
) -> AsyncIterator[AsyncClient]:
    app = create_application()
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
