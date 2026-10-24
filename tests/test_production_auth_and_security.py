import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.core.auth.passwords import hash_password, verify_password
from app.core.auth.token_blacklist import is_token_revoked, revoke_token
from app.core.config import Settings
from app.main import create_application


def test_password_hashing_and_verification() -> None:
    raw_password = "SuperSecretPassword123!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("pbkdf2:sha256:")

    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False


def test_jwt_token_lifecycle(test_settings: Settings) -> None:
    token = create_access_token(user_id="user_123", email="test@example.com", role="USER")
    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user_123"
    assert payload["role"] == "USER"
    assert payload["type"] == "access"

    refresh_token = create_refresh_token(user_id="user_123", email="test@example.com", role="USER")
    refresh_payload = decode_token(refresh_token)
    assert refresh_payload is not None
    assert refresh_payload["type"] == "refresh"


@pytest.mark.asyncio
async def test_token_blacklist() -> None:
    token = "sample_revoked_token_xyz"
    assert await is_token_revoked(token) is False

    await revoke_token(token)
    assert await is_token_revoked(token) is True


@pytest.mark.asyncio
async def test_auth_registration_and_login_flow(client: AsyncClient) -> None:
    # 1. Register new user
    reg_payload = {
        "email": "prod_user@example.com",
        "password": "SecurePassword123!",
        "role": "USER",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["email"] == "prod_user@example.com"
    assert "hashed_password" not in user_data

    # 2. Duplicate registration should fail
    dup_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_resp.status_code == 409

    # 3. Login with invalid password
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "prod_user@example.com", "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401

    # 4. Login with valid password
    good_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "prod_user@example.com", "password": "SecurePassword123!"},
    )
    assert good_login.status_code == 200
    token_data = good_login.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    assert access_token
    assert refresh_token

    # 5. Access /me with bearer token
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "prod_user@example.com"

    # 6. Refresh tokens
    ref_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_resp.status_code == 200
    new_tokens = ref_resp.json()
    new_access = new_tokens["access_token"]
    assert new_access != access_token

    # 7. Old refresh token should now be blacklisted
    stale_ref = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert stale_ref.status_code == 401

    # 8. Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert logout_resp.status_code == 204

    # 9. Access with logged-out token should be rejected
    rejected_me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert rejected_me.status_code == 401


@pytest.mark.asyncio
async def test_correlation_id_middleware(client: AsyncClient) -> None:
    resp = await client.get("/live")
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
    custom_id = "test-custom-trace-uuid"
    resp_custom = await client.get("/live", headers={"X-Request-ID": custom_id})
    assert resp_custom.headers.get("x-request-id") == custom_id


@pytest.mark.asyncio
async def test_payload_size_limit_middleware(client: AsyncClient) -> None:
    # Small payload succeeds
    resp_ok = await client.get("/live")
    assert resp_ok.status_code == 200

    # Oversized payload rejected
    large_headers = {"Content-Length": str(15 * 1024 * 1024)}  # 15MB
    resp_large = await client.post("/api/v1/auth/login", content=b"a", headers=large_headers)
    assert resp_large.status_code == 413


@pytest.mark.asyncio
async def test_maintenance_mode_middleware() -> None:
    app = create_application()
    app.state.maintenance_mode = True

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Health probes remain open
        live_resp = await ac.get("/live")
        assert live_resp.status_code == 200

        ready_resp = await ac.get("/ready")
        assert ready_resp.status_code == 200

        # Application endpoint returns 503 with Retry-After
        api_resp = await ac.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "pass"},
        )
        assert api_resp.status_code == 503
        assert "Retry-After" in api_resp.headers
