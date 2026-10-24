"""Cryptographic password hashing and verification using standard PBKDF2-HMAC-SHA256."""

from __future__ import annotations

import hashlib
import hmac
import os


def hash_password(plain_password: str, iterations: int = 100_000) -> str:
    """Hashes a plain password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=plain_password.encode("utf-8"),
        salt=salt,
        iterations=iterations,
    )
    return f"pbkdf2:sha256:{iterations}${salt.hex()}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored PBKDF2 hash using constant-time comparison."""
    if not hashed_password or not hashed_password.startswith("pbkdf2:sha256:"):
        return False

    try:
        header, salt_hex, expected_key_hex = hashed_password.split("$")
        iterations = int(header.split(":")[2])
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(expected_key_hex)

        actual_key = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=plain_password.encode("utf-8"),
            salt=salt,
            iterations=iterations,
        )
        return hmac.compare_digest(actual_key, expected_key)
    except Exception:
        return False
