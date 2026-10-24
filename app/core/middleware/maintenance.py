"""Maintenance mode interceptor middleware."""

from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

EXEMPT_PATHS = {"/health", "/live", "/ready", "/metrics", "/api/v1/health"}


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """Returns 503 maintenance status while maintaining infrastructure health probes."""

    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        is_maintenance = (
            getattr(request.app.state, "maintenance_mode", False) or self.settings.MAINTENANCE_MODE
        )
        if is_maintenance and request.url.path not in EXEMPT_PATHS:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "maintenance",
                    "message": (
                        "We'll be back soon. The platform is undergoing scheduled maintenance."
                    ),
                },
                headers={"Retry-After": "300"},
            )

        return await call_next(request)
