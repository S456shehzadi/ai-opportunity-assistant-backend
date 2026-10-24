"""JWT encoding, decoding, and signature verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import timedelta
from typing import Any

from app.core.config import get_settings


def _b64encode(data: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(data: str) -> bytes:
    """Base64url decode with padding added."""
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(
    payload: dict[str, Any],
    expires_delta: timedelta,
    token_type: str = "access",
) -> str:
    """Encodes and signs a JWT token with HS256."""
    settings = get_settings()
    now = int(time.time())
    exp = now + int(expires_delta.total_seconds())

    claims = {
        **payload,
        "iat": now,
        "exp": exp,
        "jti": str(uuid.uuid4()),
        "type": token_type,
    }

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=signing_input,
        digestmod=hashlib.sha256,
    ).digest()
    sig_b64 = _b64encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Creates a short-lived access token."""
    settings = get_settings()
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_token(
        payload={"sub": user_id, "email": email, "role": role},
        expires_delta=delta,
        token_type="access",
    )


def create_refresh_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Creates a long-lived refresh token."""
    settings = get_settings()
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_token(
        payload={"sub": user_id, "email": email, "role": role},
        expires_delta=delta,
        token_type="refresh",
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decodes and validates token signature and expiration."""
    settings = get_settings()
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode()

    expected_sig = hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=signing_input,
        digestmod=hashlib.sha256,
    ).digest()

    try:
        actual_sig = _b64decode(sig_b64)
    except Exception as exc:
        raise ValueError("Malformed token signature") from exc

    if not hmac.compare_digest(actual_sig, expected_sig):
        raise ValueError("Invalid token signature")

    try:
        payload_bytes = _b64decode(payload_b64)
        claims = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Malformed token payload") from exc

    now = int(time.time())
    if claims.get("exp", 0) < now:
        raise ValueError("Token has expired")

    return claims
