"""Pydantic schemas for authentication and authorization."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    """Payload for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.USER


class UserLoginRequest(BaseModel):
    """Payload for user authentication."""

    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Token response payload containing bearer access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefreshRequest(BaseModel):
    """Payload to refresh an expired access token."""

    refresh_token: str


class UserAuthResponse(BaseModel):
    """User profile data returned upon successful authentication."""

    id: UUID
    email: str
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ForgotPasswordRequest(BaseModel):
    """Payload to request password reset token."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload to reset password using verification token."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    """Generic status/message response payload."""

    message: str
