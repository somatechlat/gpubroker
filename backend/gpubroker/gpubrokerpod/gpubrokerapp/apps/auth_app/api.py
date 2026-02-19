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

from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from .auth import JWTAuth
from .models import User
from .schemas import (
    EmailVerificationRequest,
    ForgotPasswordRequest,
    PasswordChange,
    RefreshTokenRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserLogin,
    UserProfileUpdate,
    UserResponse,
)
from .services import (
    authenticate_user,
    change_password,
    create_password_reset_token,
    create_tokens,
    create_user,
    create_verification_token,
    get_user_by_email,
    log_audit_event,
    refresh_tokens,
    reset_password_with_token,
    send_password_reset_email,
    send_verification_email,
    update_user_profile,
    verify_email_token,
)

logger = logging.getLogger("gpubroker.auth")

router = Router(tags=["auth"])


def get_client_ip(request: HttpRequest) -> str:
    """Extract client IP from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


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
            user_agent=request.META.get("HTTP_USER_AGENT"),
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
            user_agent=request.META.get("HTTP_USER_AGENT"),
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
        user_agent=request.META.get("HTTP_USER_AGENT"),
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


@router.post("/verify-email", auth=None)
async def verify_email(request: HttpRequest, data: EmailVerificationRequest):
    """
    Verify user email with token.

    Token is sent via email after registration.
    """
    user = await verify_email_token(data.token)

    if not user:
        raise HttpError(400, "Invalid or expired verification token")

    # Log audit event
    await log_audit_event(
        event_type="email_verified",
        user=user,
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
    )

    return {"message": "Email verified successfully"}


@router.post("/resend-verification", auth=None)
async def resend_verification(request: HttpRequest, data: ResendVerificationRequest):
    """
    Resend verification email.

    Rate limited to prevent abuse.
    """
    user = await get_user_by_email(data.email)

    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a verification link has been sent"}

    if user.is_verified:
        return {"message": "Email is already verified"}

    # Create and send verification token
    token = await create_verification_token(user)
    await send_verification_email(user, token)

    return {"message": "If the email exists, a verification link has been sent"}


@router.post("/forgot-password", auth=None)
async def forgot_password(request: HttpRequest, data: ForgotPasswordRequest):
    """
    Request password reset email.

    Sends reset link if email exists.
    """
    token = await create_password_reset_token(data.email)

    if token:
        await send_password_reset_email(data.email, token)

    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password", auth=None)
async def reset_password(request: HttpRequest, data: ResetPasswordRequest):
    """
    Reset password with token.

    Token is sent via email from forgot-password endpoint.
    """
    success = await reset_password_with_token(data.token, data.new_password)

    if not success:
        raise HttpError(400, "Invalid or expired reset token")

    return {"message": "Password reset successfully"}
