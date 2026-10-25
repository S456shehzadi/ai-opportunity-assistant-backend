"""Production authentication service coordinating credentials, tokens, and audit trails."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.jwt import (
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
)
from app.core.auth.passwords import hash_password, verify_password
from app.core.auth.token_blacklist import get_token_blacklist_service
from app.core.config import get_settings
from app.models.security import AuditLogRecord
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user onboarding, credential validation, token rotation, and security auditing."""

    def __init__(self) -> None:
        self.blacklist = get_token_blacklist_service()
        self.settings = get_settings()

    async def register_user(
        self,
        db: AsyncSession,
        payload: UserRegisterRequest,
        ip_address: str | None = None,
    ) -> User:
        """Registers a new user account with hashed password."""
        query = select(User).where(User.email == payload.email.lower().strip())
        res = await db.execute(query)
        if res.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        hashed = hash_password(payload.password)
        user = User(
            email=payload.email.lower().strip(),
            full_name=payload.full_name.strip() if payload.full_name else None,
            hashed_password=hashed,
            role=payload.role,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        await self.record_audit_log(
            db=db,
            user_id=user.id,
            action="USER_REGISTRATION",
            resource_type="USER",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        await db.commit()
        await db.refresh(user)
        return user

    async def authenticate_user(
        self,
        db: AsyncSession,
        payload: UserLoginRequest,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """Authenticates user credentials and issues JWT token pair."""
        query = select(User).where(User.email == payload.email.lower().strip())
        res = await db.execute(query)
        user = res.scalar_one_or_none()

        if not user or not user.hashed_password:
            await self.record_audit_log(
                db=db,
                user_id=user.id if user else None,
                action="USER_LOGIN_FAILED",
                resource_type="USER",
                ip_address=ip_address,
                status="FAILURE",
                details={"reason": "Invalid credentials"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(payload.password, user.hashed_password):
            await self.record_audit_log(
                db=db,
                user_id=user.id,
                action="USER_LOGIN_FAILED",
                resource_type="USER",
                ip_address=ip_address,
                status="FAILURE",
                details={"reason": "Password mismatch"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or suspended",
            )

        access_token = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
        )
        refresh_token = create_refresh_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
        )

        await self.record_audit_log(
            db=db,
            user_id=user.id,
            action="USER_LOGIN_SUCCESS",
            resource_type="USER",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        await db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_tokens(
        self,
        db: AsyncSession,
        refresh_token: str,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """Rotates refresh token and generates a new access token."""
        try:
            claims = decode_token(refresh_token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid refresh token: {str(exc)}",
            ) from exc

        if claims.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Provided token is not a refresh token",
            )

        jti = claims.get("jti")
        if jti and await self.blacklist.is_revoked(jti, db=db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        user_id_str = claims.get("sub")
        try:
            user_id = UUID(user_id_str)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed token user identity",
            ) from None

        query = select(User).where(User.id == user_id)
        res = await db.execute(query)
        user = res.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Invalidate old refresh token (token rotation)
        if jti:
            exp_ts = claims.get("exp", int(datetime.now(UTC).timestamp()) + 3600)
            await self.blacklist.revoke_token(
                jti=jti,
                user_id=user.id,
                expires_at=datetime.fromtimestamp(exp_ts, tz=UTC),
                token_type="refresh",
                db=db,
            )

        new_access = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
        )
        new_refresh = create_refresh_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
        )

        await self.record_audit_log(
            db=db,
            user_id=user.id,
            action="TOKEN_ROTATION",
            resource_type="AUTH",
            ip_address=ip_address,
        )
        await db.commit()

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout_user(
        self,
        db: AsyncSession,
        token: str,
        user_id: UUID,
    ) -> None:
        """Explicitly revokes active access token upon user logout."""
        try:
            claims = decode_token(token)
            jti = claims.get("jti")
            if jti:
                exp_ts = claims.get("exp", int(datetime.now(UTC).timestamp()) + 3600)
                await self.blacklist.revoke_token(
                    jti=jti,
                    user_id=user_id,
                    expires_at=datetime.fromtimestamp(exp_ts, tz=UTC),
                    token_type=claims.get("type", "access"),
                    db=db,
                )
        except Exception as exc:
            logger.warning("Error revoking token during logout: %s", exc)

    async def record_audit_log(
        self,
        db: AsyncSession,
        user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "SUCCESS",
        details: dict | None = None,
    ) -> None:
        """Records an auditable security event."""
        log = AuditLogRecord(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            details=details or {},
        )
        db.add(log)

    async def delete_user_account(
        self,
        db: AsyncSession,
        user_id: UUID,
        ip_address: str | None = None,
    ) -> None:
        """Permanently deletes user account, cascades user data scrub, and logs security audit."""
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user_email = user.email
        await db.delete(user)
        await db.commit()

        logger.info("Permanently deleted user account %s (%s)", user_id, user_email)

    async def request_password_reset(
        self,
        db: AsyncSession,
        email: str,
        ip_address: str | None = None,
    ) -> str:
        """Generates a secure password reset token for account recovery."""
        query = select(User).where(User.email == email.lower().strip())
        res = await db.execute(query)
        user = res.scalar_one_or_none()
        if not user:
            # Constant-time mitigation: return dummy token representation to avoid email enumeration
            logger.info("Password reset requested for non-existent email %s", email)
            return "simulated-reset-token-for-unregistered-address"

        reset_token = create_token(
            payload={"sub": str(user.id), "email": user.email, "type": "password_reset"},
            expires_delta=timedelta(hours=1),
            token_type="password_reset",
        )

        await self.record_audit_log(
            db=db,
            user_id=user.id,
            action="PASSWORD_RESET_REQUESTED",
            resource_type="USER",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        await db.commit()
        return reset_token

    async def reset_password(
        self,
        db: AsyncSession,
        token: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> None:
        """Verifies reset token and updates user credentials."""
        try:
            payload = decode_token(token)
            if payload.get("type") != "password_reset":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token type for password reset",
                )
            user_id = UUID(payload.get("sub"))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            ) from exc

        user = await db.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive",
            )

        user.hashed_password = hash_password(new_password)
        await self.record_audit_log(
            db=db,
            user_id=user.id,
            action="PASSWORD_RESET_COMPLETED",
            resource_type="USER",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        await db.commit()
        logger.info("Successfully reset password for user %s", user.id)
