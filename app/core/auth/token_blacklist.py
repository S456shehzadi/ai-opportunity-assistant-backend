"""Token revocation and blacklist verification."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import RevokedTokenRecord

logger = logging.getLogger(__name__)


class TokenBlacklistService:
    """Manages token revocation state with memory cache and database persistence."""

    def __init__(self) -> None:
        self._memory_blacklist: set[str] = set()

    async def is_revoked(self, jti: str, db: AsyncSession | None = None) -> bool:
        """Determines if the token identifier has been revoked."""
        if jti in self._memory_blacklist:
            return True

        if db is not None:
            query = select(RevokedTokenRecord).where(RevokedTokenRecord.jti == jti)
            res = await db.execute(query)
            if res.scalar_one_or_none() is not None:
                self._memory_blacklist.add(jti)
                return True

        return False

    async def revoke_token(
        self,
        jti: str,
        user_id: UUID,
        expires_at: datetime,
        token_type: str = "access",
        db: AsyncSession | None = None,
    ) -> None:
        """Revokes token and persists revocation record."""
        self._memory_blacklist.add(jti)
        if db is not None:
            record = RevokedTokenRecord(
                jti=jti,
                token_type=token_type,
                user_id=user_id,
                expires_at=expires_at,
            )
            db.add(record)
            await db.commit()
            logger.info("Token %s for user %s revoked at %s", jti, user_id, datetime.now(UTC))


_token_blacklist_service: TokenBlacklistService | None = None


def get_token_blacklist_service() -> TokenBlacklistService:
    global _token_blacklist_service
    if _token_blacklist_service is None:
        _token_blacklist_service = TokenBlacklistService()
    return _token_blacklist_service


async def is_token_revoked(jti: str, db: AsyncSession | None = None) -> bool:
    """Convenience helper to check token revocation."""
    return await get_token_blacklist_service().is_revoked(jti, db=db)


async def revoke_token(
    jti: str,
    user_id: UUID | None = None,
    expires_at: datetime | None = None,
    token_type: str = "access",
    db: AsyncSession | None = None,
) -> None:
    """Convenience helper to revoke a token."""
    import uuid

    uid = user_id or uuid.uuid4()
    exp = expires_at or datetime.now(UTC)
    await get_token_blacklist_service().revoke_token(
        jti=jti,
        user_id=uid,
        expires_at=exp,
        token_type=token_type,
        db=db,
    )
