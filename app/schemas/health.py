from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    database: str = Field(default="configured")
    cache: str = Field(default="configured")
    ai_provider: str = Field(default="configured")
    search_provider: str = Field(default="configured")


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Overall health status")
    environment: str = Field(description="Active environment")
    version: str = Field(description="API version")
    app_name: str = Field(description="Application name")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of the check",
    )
    services: ServiceStatus = Field(default_factory=ServiceStatus)
    metadata: dict[str, Any] = Field(default_factory=dict)
