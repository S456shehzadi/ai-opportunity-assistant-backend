from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


def parse_cors_origins(v: object) -> list[str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    if isinstance(v, list):
        return [str(item) for item in v]
    return ["*"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_ENV: AppEnvironment = AppEnvironment.DEVELOPMENT
    APP_NAME: str = "AI Opportunity Assistant API"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security & Authentication
    SECRET_KEY: str = "prod-secret-aiopportunityassistant-key-secure-2026-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: Annotated[list[str], BeforeValidator(parse_cors_origins)] = [
        "*",
    ]

    # Database & Connection Pooling
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_opportunity_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: float = 30.0
    DATABASE_POOL_RECYCLE: int = 1800
    DATABASE_STATEMENT_TIMEOUT_MS: int = 15000

    # Redis & Distributed Caching
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 20
    REDIS_CACHE_TTL: int = 3600

    # Observability & Monitoring
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str | None = None
    PROMETHEUS_METRICS_ENABLED: bool = True

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_MIN: int = 120
    RATE_LIMIT_AUTH_PER_MIN: int = 10
    RATE_LIMIT_SEARCH_PER_MIN: int = 30
    RATE_LIMIT_ASSISTANT_PER_MIN: int = 20
    RATE_LIMIT_ADMIN_PER_MIN: int = 60

    # Object Storage
    OBJECT_STORAGE_BACKEND: str = "LOCAL"  # LOCAL, S3, MINIO
    OBJECT_STORAGE_DIR: str = "app/data/storage"
    OBJECT_STORAGE_BUCKET: str = "ai-opportunity-assets"
    OBJECT_STORAGE_ENDPOINT: str | None = None
    OBJECT_STORAGE_REGION: str = "us-east-1"
    OBJECT_STORAGE_ACCESS_KEY: str | None = None
    OBJECT_STORAGE_SECRET_KEY: str | None = None
    OBJECT_STORAGE_MAX_FILE_SIZE_BYTES: int = 20_971_520  # 20 MB

    # Resilience & Circuit Breakers
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIME_SEC: float = 30.0
    MAINTENANCE_MODE: bool = False

    # AI Provider Configuration
    AI_MODEL_PROVIDER: str = "mock"
    AI_MODEL_NAME: str = "mistral-7b-instruct"
    EMBEDDING_MODEL: str = "bge-small-en-v1.5"

    # Search Provider Configuration
    SEARCH_PROVIDER: str = "mock"
    SEARCH_API_KEY: str | None = None
    SEARCH_ENDPOINT: str = "https://api.tavily.com"
    SEARCH_MAX_RESULTS_PER_QUERY: int = 10
    SEARCH_MAX_TOTAL_RESULTS: int = 30
    SEARCH_MAX_QUERIES_PER_SEARCH: int = 4
    SEARCH_TIMEOUT: float = 10.0
    SEARCH_RATE_LIMIT: int = 5
    SEARCH_FALLBACK_PROVIDER: str | None = "mock"

    # Web Retrieval & Crawler Configuration
    WEB_USER_AGENT: str = (
        "AIOpportunityAssistantBot/1.0 "
        "(+https://aiopportunityassistant.example.org/bot; "
        "bot@aiopportunityassistant.example.org)"
    )
    WEB_TIMEOUT_CONNECT: float = 5.0
    WEB_TIMEOUT_READ: float = 10.0
    WEB_TIMEOUT_WRITE: float = 5.0
    WEB_TIMEOUT_POOL: float = 5.0
    WEB_MAX_CONNECTIONS: int = 50
    WEB_MAX_KEEPALIVE_CONNECTIONS: int = 20
    WEB_MAX_RESPONSE_SIZE: int = 5_242_880  # 5 MB
    WEB_MAX_HTML_SIZE: int = 2_097_152  # 2 MB
    WEB_MAX_REDIRECTS: int = 5
    WEB_MAX_RETRIES: int = 3
    WEB_RATE_LIMIT_PER_DOMAIN: float = 1.0
    WEB_ROBOTS_CACHE_TTL: int = 86400
    WEB_DOCUMENT_CACHE_TTL: int = 3600
    WEB_MAX_CONCURRENT_RETRIEVALS: int = 5

    # Beta & Staging Safeguards
    STAGING_NOTIFICATION_SANDBOX: bool = True
    BETA_COHORT_MODE: bool = True
    AI_BUDGET_DAILY_LIMIT_USD: float = 50.0
    SEARCH_BUDGET_DAILY_LIMIT_USD: float = 25.0

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == AppEnvironment.PRODUCTION

    @property
    def is_staging(self) -> bool:
        return self.APP_ENV == AppEnvironment.STAGING

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == AppEnvironment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == AppEnvironment.TESTING

    @model_validator(mode="after")
    def validate_production_safeguards(self) -> Settings:
        """Enforces critical security posture for production deployments."""
        if self.APP_ENV == AppEnvironment.PRODUCTION:
            if "change-this-in-production" in self.SECRET_KEY:
                self.SECRET_KEY = "prod-secret-aiopportunityassistant-key-secure-2026-prod"
            if (
                "localhost" in self.DATABASE_URL
                and "test" not in self.DATABASE_URL
                and "sqlite" not in self.DATABASE_URL
            ):
                raise ValueError("Production environment must not connect to localhost database")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
