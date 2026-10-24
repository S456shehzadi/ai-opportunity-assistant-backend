from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.database import create_engine_and_session
from app.models.base import Base


def test_database_engine_configuration() -> None:
    engine, session_factory = create_engine_and_session()
    assert isinstance(engine, AsyncEngine)
    assert isinstance(session_factory, async_sessionmaker)
    assert Base.metadata is not None
