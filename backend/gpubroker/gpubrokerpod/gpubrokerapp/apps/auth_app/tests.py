"""
Auth App Tests.

Tests for:
- User registration
- User login and JWT token issuance
- Token refresh
- Protected endpoint access
- Password change
"""

import pytest
from gpubrokerpod.gpubrokerapp.apps.auth_app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_refresh_token,
)
from gpubrokerpod.gpubrokerapp.apps.auth_app.services import (
    authenticate_user,
    create_tokens,
    create_user,
    get_password_hash,
    refresh_tokens,
    verify_password,
)

"""
Auth App Tests.

Tests for:
- User registration
- User login and JWT token issuance
- Token refresh
- Protected endpoint access
- Password change
"""
import os

# Test RSA keys for JWT (2048-bit, for testing only)
# Generated fresh using cryptography library
# Can be overridden with environment variables for security
TEST_JWT_PRIVATE_KEY = os.getenv(
    "TEST_JWT_PRIVATE_KEY",
    "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0TrmmA9OY5ZsCjxoJ0YhFC4K7lYnhtw+RvFqqMnYJN+kGqTl\nWzrCwrtPqVE3ep8Mn30rbrA26MX92cyivbWxe7TNzJa63a9Cux88NUseSd01Mm0o\n0s/KbEG/UazyTtMMITukkxX8VFpBIbEhL9JK8kOMcVKg4SjuTGQQY/DMA8FZd6LM\nPj26lsiMsL+Vm9kxRfzEJUc7N5tyHWLADpoUue1yw1lfyo4NTOIqwWQhITlIP+YA\n+ARkyH1EBbNXOB7oRJkKxqDKE2/k+AaPzBjTGh+HH1IGvSeDnpRkwcal7XKFu0l7\nxEwPfRbPQUtFj2bzcGq5LCB/TNqPgX4qSLijSwIDAQABAoIBAARaPf3KeQ5SohYR\nwkuUMTqi5+X5Xi0iBnGiCAlRhEY6w3EtHlBS3UZWcIZ3LWOcTL5B86tZIxXzOHVV\nb8qT2F4DGYeOAyklbN/zpbmowbfg+tWntlexrDuq9SM/08fsAAPuTQgk8ZuCR88+\n82UenMyEDIyMSX3QRNTLUsP2zb0DjlQAlsgT6wx9v249JHt03kIEs27tfTxiEKhU\nab8xFB6WBlQbXaZSabRyCwun79JymWHyIFTExI/qzCBnT6N6LsgZKvQ90k07IkFq\nbMzYON15PooPreMkRMWsh+DTUT/kzVOb/YiaMLJDoAfewxVrVlVqd0r6p85SdHWZ\nt7LUdCECgYEA//mwctrElKGtuFB3hWr2t5qxMn/TvPkCLlKhOT6GNORWfVSOPeyN\nenTc5fdaVlySfgJMEyE31/RYlkDvsq164DKI1NtxhYPuQHQ5H/yXjaE9hEcVuO4k\n6cq9FMlJiwCoYZfmNCBKAEB3q+RnFQ0lGi66piZ0ZHTzcwJPNgD3duMCgYEA0UAP\nHo1nSS6qLeJ9YZKmUNFr2BGvzQJEMfEchUJ3JiAL9Wh3bimZ6w/mUZ1J29iaDZy1\nKsKwQldUnaUSwC8qTf7LaZrr8T2+E9MqiFvEzLo1QXELHdWdmBXxj08kNfzNquIr\nm+cof1DXSkO0sOm0cBYZWHpaVn9ZYdaHNwaBZnkCgYEAjNr6JImLiPpa3MSysGEG\nuEvQXCiI/EDN2W2wuA5WzX4ktby0tRCZXZw2/fiZ5lH0bpCXCiPKVfRoVu4OuHTL\n29kTAIZstnq9vQv3b0mQn+ftMP/ozSWGfHwKhgiphmrrPSDYFTD7Z54R/C2oJ6Zf\nF0RFgy4/+BN+73eC3QW1Jt8CgYBnGBma4u4tZzlfTAScKyWYEeYBWY11AxXYSUPV\nAA82EHnz2hllhEeaQYYnVchK8afM5xV3UN6IgQBmfysC1voP3WYYzMRMYjAhElwV\nPKl0eJW+fVSNyW5QvRb7lXFwy/IErFPyBuyz9X9sznja5PoKc0jfh8C0dx/xjUGn\nQaRFeQKBgEfQtuXDVnc2QJUveYzxk73rdW9XUFxn/DlHVjW9fyClGMkAcWhXChO3\neqjsQF7YcUPk7hE/bH0tMPwZ7qYTgIAK4jIvNK5Q+gbE8qt4ZXPhp7Rt9NIIQwA4\nr4O7ovsL0c4+VTlRVM86n3tHdWQjEuolmUoF8ddUBFCi+/EPANi+\n-----END RSA PRIVATE KEY-----\n",
)

TEST_JWT_PUBLIC_KEY = os.getenv(
    "TEST_JWT_PUBLIC_KEY",
    "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0TrmmA9OY5ZsCjxoJ0Yh\nFC4K7lYnhtw+RvFqqMnYJN+kGqTlWzrCwrtPqVE3ep8Mn30rbrA26MX92cyivbWx\ne7TNzJa63a9Cux88NUseSd01Mm0o0s/KbEG/UazyTtMMITukkxX8VFpBIbEhL9JK\n8kOMcVKg4SjuTGQQY/DMA8FZd6LMPj26lsiMsL+Vm9kxRfzEJUc7N5tyHWLADpoU\nue1yw1lfyo4NTOIqwWQhITlIP+YA+ARkyH1EBbNXOB7oRJkKxqDKE2/k+AaPzBjT\nGh+HH1IGvSeDnpRkwcal7XKFu0l7xEwPfRbPQUtFj2bzcGq5LCB/TNqPgX4qSLij\nSwIDAQAB\n-----END PUBLIC KEY-----\n",
)

# Settings override for JWT tests
JWT_TEST_SETTINGS = {
    "JWT_PRIVATE_KEY": TEST_JWT_PRIVATE_KEY,
    "JWT_PUBLIC_KEY": TEST_JWT_PUBLIC_KEY,
    "JWT_ALGORITHM": "RS256",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": 15,
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS": 7,
}


# ============================================
# Password Hashing Tests
# ============================================


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_hash_password(self):
        """Test password hashing produces valid hash."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$argon2")

    def test_verify_correct_password(self):
        """Test verifying correct password returns True."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Test verifying wrong password returns False."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password("WrongPassword", hashed) is False


# ============================================
# JWT Token Tests
# ============================================


class TestJWTTokens:
    """Tests for JWT token creation and validation."""

    @pytest.fixture(autouse=True)
    def setup_jwt_settings(self, settings):
        """Configure JWT settings for tests."""
        # Strip any leading/trailing whitespace from keys
        settings.JWT_PRIVATE_KEY = TEST_JWT_PRIVATE_KEY.strip()
        settings.JWT_PUBLIC_KEY = TEST_JWT_PUBLIC_KEY.strip()
        settings.JWT_ALGORITHM = "RS256"
        settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
        settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

    def test_create_access_token(self):
        """Test access token creation."""
        token_data = {"sub": "test@example.com", "roles": ["user"]}
        token = create_access_token(token_data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        token_data = {"sub": "test@example.com", "roles": ["user"]}
        token = create_refresh_token(token_data)

        assert token is not None
        assert isinstance(token, str)

    def test_decode_access_token(self):
        """Test decoding access token."""
        email = "test@example.com"
        token_data = {"sub": email, "roles": ["user"]}
        token = create_access_token(token_data)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == email
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_refresh_token(self):
        """Test decoding refresh token."""
        email = "test@example.com"
        token_data = {"sub": email, "roles": ["user"]}
        token = create_refresh_token(token_data)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == email
        assert payload["type"] == "refresh"

    def test_verify_refresh_token(self):
        """Test refresh token verification."""
        email = "test@example.com"
        token_data = {"sub": email, "roles": ["user"]}
        token = create_refresh_token(token_data)

        result = verify_refresh_token(token)

        assert result == email

    def test_verify_access_token_as_refresh_fails(self):
        """Test that access token cannot be used as refresh token."""
        token_data = {"sub": "test@example.com", "roles": ["user"]}
        access_token = create_access_token(token_data)

        result = verify_refresh_token(access_token)

        assert result is None

    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None."""
        result = decode_token("invalid.token.here")
        assert result is None


# ============================================
# User Service Tests
# ============================================


@pytest.mark.django_db
class TestUserServices:
    """Tests for user service functions."""

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Test successful user creation."""
        user = await create_user(
            email="newuser@example.com",
            password="SecurePassword123!",
            full_name="New User",
            organization="Test Org",
        )

        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.organization == "Test Org"
        assert user.is_active is True
        assert user.password_hash != "SecurePassword123!"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self):
        """Test creating user with duplicate email raises error."""
        await create_user(
            email="duplicate@example.com",
            password="Password123!",
            full_name="First User",
        )

        with pytest.raises(ValueError, match="Email already registered"):
            await create_user(
                email="duplicate@example.com",
                password="Password456!",
                full_name="Second User",
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, test_user):
        """Test successful user authentication."""
        # Create user with known password
        password = "TestPassword123!"
        user = await create_user(
            email="auth_test@example.com",
            password=password,
            full_name="Auth Test User",
        )

        authenticated = await authenticate_user("auth_test@example.com", password)

        assert authenticated is not None
        assert authenticated.email == "auth_test@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password fails."""
        await create_user(
            email="wrongpass@example.com",
            password="CorrectPassword123!",
            full_name="Test User",
        )

        authenticated = await authenticate_user(
            "wrongpass@example.com", "WrongPassword!"
        )

        assert authenticated is None

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self):
        """Test authentication for non-existent user fails."""
        authenticated = await authenticate_user(
            "nonexistent@example.com", "Password123!"
        )
        assert authenticated is None

    def test_create_tokens(self, test_user):
        """Test token creation for user."""
        access_token, refresh_token, expires_in = create_tokens(test_user)

        assert access_token is not None
        assert refresh_token is not None
        assert expires_in > 0

        # Verify tokens are valid
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        assert access_payload["sub"] == test_user.email
        assert refresh_payload["sub"] == test_user.email

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self):
        """Test token refresh with valid refresh token."""
        # Create user and tokens
        user = await create_user(
            email="refresh_test@example.com",
            password="Password123!",
            full_name="Refresh Test",
        )
        _, refresh_token, _ = create_tokens(user)

        result = await refresh_tokens(refresh_token)

        assert result is not None
        new_access, new_refresh, expires_in = result
        assert new_access is not None
        assert new_refresh is not None
        assert expires_in > 0

    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_token(self):
        """Test token refresh with invalid token fails."""
        result = await refresh_tokens("invalid.refresh.token")
        assert result is None


# ============================================
# API Endpoint Tests
# ============================================


@pytest.mark.django_db(transaction=True)
class TestAuthAPI:
    """Tests for auth API endpoints."""

    @pytest.mark.asyncio
    async def test_register_endpoint(self, api_client):
        """Test user registration endpoint."""
        response = await api_client.post(
            "/auth/register",
            json={
                "email": "api_register@example.com",
                "password": "SecurePassword123!",
                "full_name": "API Register User",
                "organization": "Test Org",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "api_register@example.com"
        assert data["full_name"] == "API Register User"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, api_client):
        """Test registration with duplicate email fails."""
        # First registration
        await api_client.post(
            "/auth/register",
            json={
                "email": "duplicate_api@example.com",
                "password": "Password123!",
                "full_name": "First User",
            },
        )

        # Second registration with same email
        response = await api_client.post(
            "/auth/register",
            json={
                "email": "duplicate_api@example.com",
                "password": "Password456!",
                "full_name": "Second User",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_endpoint(self, api_client):
        """Test login endpoint."""
        # Register user first
        password = "LoginPassword123!"
        await api_client.post(
            "/auth/register",
            json={
                "email": "login_test@example.com",
                "password": password,
                "full_name": "Login Test User",
            },
        )

        # Login
        response = await api_client.post(
            "/auth/login",
            json={
                "email": "login_test@example.com",
                "password": password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials fails."""
        response = await api_client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword!",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_endpoint(self, api_client):
        """Test token refresh endpoint."""
        # Register and login
        password = "RefreshPassword123!"
        await api_client.post(
            "/auth/register",
            json={
                "email": "refresh_api@example.com",
                "password": password,
                "full_name": "Refresh API User",
            },
        )

        login_response = await api_client.post(
            "/auth/login",
            json={
                "email": "refresh_api@example.com",
                "password": password,
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = await api_client.post(
            "/auth/refresh",
            json={
                "refresh_token": refresh_token,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_me_endpoint_authenticated(self, api_client, test_user, auth_headers):
        """Test /me endpoint with valid authentication."""
        response = await api_client.get("/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name

    @pytest.mark.asyncio
    async def test_me_endpoint_unauthenticated(self, api_client):
        """Test /me endpoint without authentication fails."""
        response = await api_client.get("/auth/me")

        assert response.status_code == 401
