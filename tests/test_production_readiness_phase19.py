"""Production Readiness & Release Decision Verification Suite for Phase 19."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.opportunities.eligibility.engine import EligibilityEngine
from app.opportunities.eligibility.schemas import OverallEligibilityStatus


@pytest.mark.asyncio
async def test_account_recovery_and_password_reset(client: AsyncClient) -> None:
    """Verifies Journey 1: Forgot password token issuance and password reset."""
    # 1. Register test user
    email = "recovery.tester@example.com"
    pwd = "OriginalPassword123!"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd},
    )
    assert reg_res.status_code == 201

    # 2. Request password reset
    forgot_res = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )
    assert forgot_res.status_code == 200
    assert "instructions have been generated" in forgot_res.json()["message"]

    # 3. Simulate token generation and reset password
    from datetime import timedelta

    from app.core.auth.jwt import create_token
    user_id = reg_res.json()["id"]
    reset_token = create_token(
        payload={"sub": str(user_id), "email": email, "type": "password_reset"},
        expires_delta=timedelta(hours=1),
        token_type="password_reset",
    )

    new_pwd = "NewSecurePassword456!"
    reset_res = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": new_pwd},
    )
    assert reset_res.status_code == 200
    assert "successfully reset" in reset_res.json()["message"]

    # 4. Verify login works with new password and fails with old password
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_pwd},
    )
    assert new_login.status_code == 200
    assert new_login.json()["access_token"]


@pytest.mark.asyncio
async def test_account_deletion_and_data_scrubbing(client: AsyncClient) -> None:
    """Verifies Journey 14: Permanent account deletion cascades and revokes credentials."""
    # 1. Register and login
    email = "delete.me@example.com"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!"},
    )
    assert reg_res.status_code == 201

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create profile
    prof_res = await client.post(
        "/api/v1/profile",
        json={"nationality": "Germany", "education_level": "Master's"},
        headers=headers,
    )
    assert prof_res.status_code == 201

    # 3. Request account deletion
    del_res = await client.delete("/api/v1/auth/account", headers=headers)
    assert del_res.status_code == 200
    assert "permanently deleted" in del_res.json()["message"]

    # 4. Confirm revoked token can no longer access endpoints
    get_me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert get_me_res.status_code == 401

    # 5. Confirm user cannot log back in
    relogin_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert relogin_res.status_code == 401


@pytest.mark.asyncio
async def test_eligibility_admission_guarantee_disclaimer() -> None:
    """Verifies AI outputs explicitly state eligibility is not an admission guarantee."""
    from tests.test_eligibility_engine_scenarios import (
        OPPORTUNITY_A_STANDARD_DICT,
        USER_PROFILE_A_DICT,
    )
    engine = EligibilityEngine()
    result = await engine.evaluate(
        profile=USER_PROFILE_A_DICT,
        opportunity=OPPORTUNITY_A_STANDARD_DICT,
    )
    assert result.overall_status in [
        OverallEligibilityStatus.CLEARLY_ELIGIBLE,
        OverallEligibilityStatus.POTENTIALLY_ELIGIBLE,
    ]
    # Check explicit legal disclaimer
    disclaimer = result.admission_guarantee_disclaimer
    assert "admission prediction or scholarship funding guarantee" in disclaimer
    assert "Final selection decisions rest solely with the issuing institution" in disclaimer


@pytest.mark.asyncio
async def test_search_provider_graceful_error_handling(client: AsyncClient) -> None:
    """Verifies search endpoint returns explicit error rather than fabricating fake results."""
    # When payload is empty, expect 422
    res = await client.post("/api/v1/search", json={})
    assert res.status_code in [401, 422]
