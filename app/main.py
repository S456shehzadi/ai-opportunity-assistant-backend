from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import health
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    CorrelationIdMiddleware,
    MaintenanceModeMiddleware,
    PayloadSizeLimitMiddleware,
    RateLimitMiddleware,
)
from app.core.redis import get_redis_service
from app.core.security import SecurityHeadersMiddleware

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager for startup and shutdown routines."""
    setup_logging()
    settings = get_settings()
    logger.info(
        "Starting %s v%s [Environment: %s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_ENV,
    )
    logger.info(
        "Configured AI Provider: %s (Model: %s)",
        settings.AI_MODEL_PROVIDER,
        settings.AI_MODEL_NAME,
    )
    logger.info("Configured Search Provider: %s", settings.SEARCH_PROVIDER)
    
    # Initialize database tables and seed verified opportunities
    try:
        from app.core.database import async_session_factory, init_db
        await init_db()
        logger.info("Database initialized successfully.")

        from app.data.seed_data import seed_database_if_empty
        await seed_database_if_empty()

        from app.discovery import get_discovery_indexer
        async with async_session_factory() as session:
            indexer = get_discovery_indexer()
            stats = await indexer.reindex_all(session)
            logger.info("Discovery Engine indexed opportunities: %s", stats)
    except Exception as exc:
        logger.warning("Database / discovery initialization check: %s", exc)

    # Initialize connection pools
    redis_service = get_redis_service()
    await redis_service.get_client()

    yield

    logger.info("Shutting down %s", settings.APP_NAME)
    await redis_service.close()


def create_application() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Global AI-Powered Opportunity Discovery and Reasoning Platform API",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Middlewares (outermost executed first)
    app.add_middleware(MaintenanceModeMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(PayloadSizeLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Standardized Exception Handling
    register_exception_handlers(app)

    # Root Health, Liveness, Readiness, and Metrics probes
    app.include_router(health.router, tags=["System Probes"])

    # API Version 1 Routing
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()
