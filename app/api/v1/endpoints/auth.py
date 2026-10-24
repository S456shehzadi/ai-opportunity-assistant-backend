"""REST API endpoints for user authentication, token rotation, and sessions."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserAuthResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])
auth_service = AuthService()


@router.post(
    "/register",
    response_model=UserAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
)
async def register(
    payload: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserAuthResponse:
    """Creates a new user record with secure PBKDF2 password hashing."""
    client_ip = request.client.host if request.client else None
    user = await auth_service.register_user(db=db, payload=payload, ip_address=client_ip)
    return UserAuthResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT token pair",
)
async def login(
    payload: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Verifies credentials and issues short-lived access and long-lived refresh tokens."""
    client_ip = request.client.host if request.client else None
    return await auth_service.authenticate_user(db=db, payload=payload, ip_address=client_ip)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and retrieve new access token",
)
async def refresh_token(
    payload: TokenRefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Performs token rotation: revokes prior refresh token and issues a new pair."""
    client_ip = request.client.host if request.client else None
    return await auth_service.refresh_tokens(
        db=db,
        refresh_token=payload.refresh_token,
        ip_address=client_ip,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out and revoke current access token",
)
async def logout(
    current_user: User = Depends(get_current_user),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Blacklists the active access token and clears session state."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ")[1]
        await auth_service.logout_user(db=db, token=token, user_id=current_user.id)


@router.get(
    "/me",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserAuthResponse:
    """Returns profile and permission role of active authenticated user."""
    return UserAuthResponse.model_validate(current_user)


@router.delete(
    "/account",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Permanently delete user account and all personal profile data",
)
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Permanently deletes account, cascades data scrubbing, and revokes active token."""
    client_ip = request.client.host if request.client else None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ")[1]
        await auth_service.logout_user(db=db, token=token, user_id=current_user.id)

    await auth_service.delete_user_account(db=db, user_id=current_user.id, ip_address=client_ip)
    return MessageResponse(
        message="Your account and all associated profile data have been permanently deleted."
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset token",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Issues password reset verification instructions."""
    client_ip = request.client.host if request.client else None
    await auth_service.request_password_reset(db=db, email=payload.email, ip_address=client_ip)
    return MessageResponse(
        message=(
            "If an account matches that email address, password "
            "reset instructions have been generated."
        )
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using verification token",
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Resets user password with valid reset token."""
    client_ip = request.client.host if request.client else None
    await auth_service.reset_password(
        db=db,
        token=payload.token,
        new_password=payload.new_password,
        ip_address=client_ip,
    )
    return MessageResponse(message="Your password has been successfully reset. You may now log in.")
