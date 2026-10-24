"""Payload size restriction middleware protecting against oversized requests."""

from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

MAX_PAYLOAD_BYTES = 10_485_760  # 10 MB


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects incoming HTTP requests that exceed permitted payload thresholds."""

    def __init__(self, app: object, max_bytes: int = MAX_PAYLOAD_BYTES) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Payload Too Large",
                            "message": (
                                "Request body exceeds maximum allowed size of "
                                f"{self.max_bytes} bytes."
                            ),
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)
