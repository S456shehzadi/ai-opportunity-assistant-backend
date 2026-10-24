from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def create_engine_and_session() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    settings = get_settings()

    engine_kwargs: dict[str, Any] = {
        "echo": settings.LOG_LEVEL.upper() == "DEBUG",
        "future": True,
        "pool_pre_ping": True,
    }

    # Apply production connection pooling parameters for PostgreSQL
    if "postgresql" in settings.DATABASE_URL:
        engine_kwargs.update(
            {
                "pool_size": settings.DATABASE_POOL_SIZE,
                "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
                "pool_recycle": settings.DATABASE_POOL_RECYCLE,
                "connect_args": {
                    "command_timeout": settings.DATABASE_STATEMENT_TIMEOUT_MS / 1000.0,
                },
            }
        )
    elif "sqlite" in settings.DATABASE_URL:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if "///" in settings.DATABASE_URL:
            from pathlib import Path

            db_part = settings.DATABASE_URL.split("///", 1)[1]
            if db_part and db_part != ":memory:":
                Path(db_part).parent.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return engine, session_factory


engine, async_session_factory = create_engine_and_session()


async def init_db() -> None:
    """Initializes tables for development/testing if they don't already exist."""
    from app.models.base import Base
    import app.models  # noqa: F401
    try:
        import app.analytics.models  # noqa: F401
        import app.evaluation.models  # noqa: F401
        import app.feedback.models  # noqa: F401
        import app.learning.models  # noqa: F401
        import app.review.models.correction  # noqa: F401
        import app.review.models.review_item  # noqa: F401
    except Exception:
        pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async SQLAlchemy session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        finally:
            await session.close()
