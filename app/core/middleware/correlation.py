"""Correlation and request tracing middleware."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Generates or propagates unique correlation identifiers across requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())

        request.state.request_id = req_id
        request.state.trace_id = trace_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = req_id
        response.headers["X-Trace-ID"] = trace_id
        return response
