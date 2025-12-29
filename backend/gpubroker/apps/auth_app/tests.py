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
from django.test import override_settings

from apps.auth_app.models import User
from apps.auth_app.services import (
    create_user,
    authenticate_user,
    create_tokens,
    refresh_tokens,
    verify_password,
    get_password_hash,
)
from apps.auth_app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_refresh_token,
)


# ============================================
# Password Hashing Tests
# ============================================

class TestPasswordHashing:
    """Tests for password hashing utilities."""
    
    def test_hash_password(self):
        """Test password hashing produces valid hash."""
        password = 'SecurePassword123!'
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith('$argon2')
    
    def test_verify_correct_password(self):
        """Test verifying correct password returns True."""
        password = 'SecurePassword123!'
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_wrong_password(self):
        """Test verifying wrong password returns False."""
        password = 'SecurePassword123!'
        hashed = get_password_hash(password)
        
        assert verify_password('WrongPassword', hashed) is False


# ============================================
# JWT Token Tests
# ============================================

class TestJWTTokens:
    """Tests for JWT token creation and validation."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        token_data = {'sub': 'test@example.com', 'roles': ['user']}
        token = create_access_token(token_data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        token_data = {'sub': 'test@example.com', 'roles': ['user']}
        token = create_refresh_token(token_data)
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_decode_access_token(self):
        """Test decoding access token."""
        email = 'test@example.com'
        token_data = {'sub': email, 'roles': ['user']}
        token = create_access_token(token_data)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload['sub'] == email
        assert payload['type'] == 'access'
        assert 'exp' in payload
        assert 'iat' in payload
    
    def test_decode_refresh_token(self):
        """Test decoding refresh token."""
        email = 'test@example.com'
        token_data = {'sub': email, 'roles': ['user']}
        token = create_refresh_token(token_data)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload['sub'] == email
        assert payload['type'] == 'refresh'
    
    def test_verify_refresh_token(self):
        """Test refresh token verification."""
        email = 'test@example.com'
        token_data = {'sub': email, 'roles': ['user']}
        token = create_refresh_token(token_data)
        
        result = verify_refresh_token(token)
        
        assert result == email
    
    def test_verify_access_token_as_refresh_fails(self):
        """Test that access token cannot be used as refresh token."""
        token_data = {'sub': 'test@example.com', 'roles': ['user']}
        access_token = create_access_token(token_data)
        
        result = verify_refresh_token(access_token)
        
        assert result is None
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None."""
        result = decode_token('invalid.token.here')
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
            email='newuser@example.com',
            password='SecurePassword123!',
            full_name='New User',
            organization='Test Org',
        )
        
        assert user is not None
        assert user.email == 'newuser@example.com'
        assert user.full_name == 'New User'
        assert user.organization == 'Test Org'
        assert user.is_active is True
        assert user.password_hash != 'SecurePassword123!'
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self):
        """Test creating user with duplicate email raises error."""
        await create_user(
            email='duplicate@example.com',
            password='Password123!',
            full_name='First User',
        )
        
        with pytest.raises(ValueError, match='Email already registered'):
            await create_user(
                email='duplicate@example.com',
                password='Password456!',
                full_name='Second User',
            )
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, test_user):
        """Test successful user authentication."""
        # Create user with known password
        password = 'TestPassword123!'
        user = await create_user(
            email='auth_test@example.com',
            password=password,
            full_name='Auth Test User',
        )
        
        authenticated = await authenticate_user('auth_test@example.com', password)
        
        assert authenticated is not None
        assert authenticated.email == 'auth_test@example.com'
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password fails."""
        await create_user(
            email='wrongpass@example.com',
            password='CorrectPassword123!',
            full_name='Test User',
        )
        
        authenticated = await authenticate_user('wrongpass@example.com', 'WrongPassword!')
        
        assert authenticated is None
    
    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self):
        """Test authentication for non-existent user fails."""
        authenticated = await authenticate_user('nonexistent@example.com', 'Password123!')
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
        
        assert access_payload['sub'] == test_user.email
        assert refresh_payload['sub'] == test_user.email
    
    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self):
        """Test token refresh with valid refresh token."""
        # Create user and tokens
        user = await create_user(
            email='refresh_test@example.com',
            password='Password123!',
            full_name='Refresh Test',
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
        result = await refresh_tokens('invalid.refresh.token')
        assert result is None


# ============================================
# API Endpoint Tests
# ============================================

@pytest.mark.django_db
class TestAuthAPI:
    """Tests for auth API endpoints."""
    
    @pytest.mark.asyncio
    async def test_register_endpoint(self, api_client):
        """Test user registration endpoint."""
        response = await api_client.post('/auth/register', json={
            'email': 'api_register@example.com',
            'password': 'SecurePassword123!',
            'full_name': 'API Register User',
            'organization': 'Test Org',
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == 'api_register@example.com'
        assert data['full_name'] == 'API Register User'
        assert 'id' in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, api_client):
        """Test registration with duplicate email fails."""
        # First registration
        await api_client.post('/auth/register', json={
            'email': 'duplicate_api@example.com',
            'password': 'Password123!',
            'full_name': 'First User',
        })
        
        # Second registration with same email
        response = await api_client.post('/auth/register', json={
            'email': 'duplicate_api@example.com',
            'password': 'Password456!',
            'full_name': 'Second User',
        })
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_login_endpoint(self, api_client):
        """Test login endpoint."""
        # Register user first
        password = 'LoginPassword123!'
        await api_client.post('/auth/register', json={
            'email': 'login_test@example.com',
            'password': password,
            'full_name': 'Login Test User',
        })
        
        # Login
        response = await api_client.post('/auth/login', json={
            'email': 'login_test@example.com',
            'password': password,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['token_type'] == 'bearer'
        assert data['expires_in'] > 0
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials fails."""
        response = await api_client.post('/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'WrongPassword!',
        })
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint(self, api_client):
        """Test token refresh endpoint."""
        # Register and login
        password = 'RefreshPassword123!'
        await api_client.post('/auth/register', json={
            'email': 'refresh_api@example.com',
            'password': password,
            'full_name': 'Refresh API User',
        })
        
        login_response = await api_client.post('/auth/login', json={
            'email': 'refresh_api@example.com',
            'password': password,
        })
        refresh_token = login_response.json()['refresh_token']
        
        # Refresh
        response = await api_client.post('/auth/refresh', json={
            'refresh_token': refresh_token,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert 'refresh_token' in data
    
    @pytest.mark.asyncio
    async def test_me_endpoint_authenticated(self, api_client, test_user, auth_headers):
        """Test /me endpoint with valid authentication."""
        response = await api_client.get('/auth/me', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == test_user.email
        assert data['full_name'] == test_user.full_name
    
    @pytest.mark.asyncio
    async def test_me_endpoint_unauthenticated(self, api_client):
        """Test /me endpoint without authentication fails."""
        response = await api_client.get('/auth/me')
        
        assert response.status_code == 401
