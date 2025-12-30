"""
Auth App API Endpoints - Django Ninja Router.

Endpoints:
- POST /register - User registration
- POST /login - User login (returns JWT tokens)
- POST /refresh - Refresh access token
- GET /me - Get current user profile
- PATCH /me - Update current user profile
- POST /change-password - Change password
"""
import logging
from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest

from .schemas import (
    UserCreate,
    UserLogin,
    Token,
    RefreshTokenRequest,
    UserResponse,
    UserProfileUpdate,
    PasswordChange,
)
from .services import (
    create_user,
    authenticate_user,
    create_tokens,
    refresh_tokens,
    update_user_profile,
    change_password,
    log_audit_event,
)
from .auth import JWTAuth
from .models import User

logger = logging.getLogger('gpubroker.auth')

router = Router(tags=["auth"])


def get_client_ip(request: HttpRequest) -> str:
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@router.post("/register", response=UserResponse, auth=None)
async def register(request: HttpRequest, data: UserCreate):
    """
    Register a new user.
    
    Returns the created user profile (without password).
    """
    try:
        user = await create_user(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            organization=data.organization,
        )
        
        # Log audit event
        await log_audit_event(
            event_type="user_registered",
            user=user,
            resource_type="user",
            resource_id=str(user.id),
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            organization=user.organization,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
        )
        
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HttpError(500, "Registration failed")


@router.post("/login", response=Token, auth=None)
async def login(request: HttpRequest, data: UserLogin):
    """
    Authenticate user and return JWT tokens.
    
    Returns access_token (15 min) and refresh_token (7 days).
    """
    user = await authenticate_user(data.email, data.password)
    
    if not user:
        # Log failed attempt
        await log_audit_event(
            event_type="login_failed",
            event_data={"email": data.email},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
        )
        raise HttpError(401, "Invalid credentials")
    
    access_token, refresh_token, expires_in = create_tokens(user)
    
    # Log successful login
    await log_audit_event(
        event_type="login_success",
        user=user,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT'),
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post("/refresh", response=Token, auth=None)
async def refresh(request: HttpRequest, data: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    
    Returns new access_token and refresh_token.
    """
    result = await refresh_tokens(data.refresh_token)
    
    if not result:
        raise HttpError(401, "Invalid or expired refresh token")
    
    access_token, refresh_token, expires_in = result
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.get("/me", response=UserResponse, auth=JWTAuth())
async def get_current_user(request: HttpRequest):
    """
    Get current authenticated user profile.
    
    Requires valid JWT access token.
    """
    user: User = request.auth
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        organization=user.organization,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.patch("/me", response=UserResponse, auth=JWTAuth())
async def update_current_user(request: HttpRequest, data: UserProfileUpdate):
    """
    Update current user profile.
    
    Only full_name and organization can be updated.
    """
    user: User = request.auth
    
    updated_user = await update_user_profile(
        user=user,
        full_name=data.full_name,
        organization=data.organization,
    )
    
    # Log audit event
    await log_audit_event(
        event_type="profile_updated",
        user=user,
        resource_type="user",
        resource_id=str(user.id),
        event_data={"updated_fields": data.model_dump(exclude_none=True)},
        ip_address=get_client_ip(request),
    )
    
    return UserResponse(
        id=str(updated_user.id),
        email=updated_user.email,
        full_name=updated_user.full_name,
        organization=updated_user.organization,
        is_active=updated_user.is_active,
        is_verified=updated_user.is_verified,
        created_at=updated_user.created_at,
    )


@router.post("/change-password", auth=JWTAuth())
async def change_user_password(request: HttpRequest, data: PasswordChange):
    """
    Change current user's password.
    
    Requires current password for verification.
    """
    user: User = request.auth
    
    success = await change_password(
        user=user,
        current_password=data.current_password,
        new_password=data.new_password,
    )
    
    if not success:
        raise HttpError(400, "Invalid current password")
    
    # Log audit event
    await log_audit_event(
        event_type="password_changed",
        user=user,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
    )
    
    return {"message": "Password changed successfully"}
