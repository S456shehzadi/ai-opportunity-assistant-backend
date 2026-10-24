import logging
import re
import sys
from typing import Any

from app.core.config import get_settings

SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "secret_key",
    "api_key",
    "authorization",
    "bearer",
}

SENSITIVE_PATTERN = re.compile(
    r"(password|token|secret|key|authorization|bearer)\s*[:=]\s*['\"]?([^'\"\s,]+)['\"]?",
    re.IGNORECASE,
)


class RedactingFormatter(logging.Formatter):
    """Custom log formatter that scrubs sensitive keys/values from log outputs."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return SENSITIVE_PATTERN.sub(r"\1=***", original)


def setup_logging() -> None:
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = RedactingFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Sanitize dictionary data before logging or serialization."""
    sanitized: dict[str, Any] = {}
    for k, v in payload.items():
        if any(secret in k.lower() for secret in SENSITIVE_KEYS):
            sanitized[k] = "***REDACTED***"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_payload(v)
        else:
            sanitized[k] = v
    return sanitized
