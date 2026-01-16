"""
Authentication API endpoints using Django Ninja.

Provides secure login, logout, token refresh, and user management.
"""

from ninja import Router, Schema
from ninja.security import HttpBearer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import Optional

from apps.auth_app.services.jwt_service import (
    jwt_service,
    JWTError,
    TokenExpiredError,
    InvalidTokenError,
)
from apps.auth_app.models import User, UserSession
from shared.responses.base import APIResponse

router = Router(tags=["Authentication"])


# Schema definitions
class LoginRequest(Schema):
    email: str
    password: str
    remember_me: Optional[bool] = False


class RegisterRequest(Schema):
    email: str
    password: str
    full_name: str
    organization: Optional[str] = None


class TokenResponse(Schema):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


class RefreshRequest(Schema):
    refresh_token: str


class UserResponse(Schema):
    id: str
    email: str
    full_name: str
    organization: Optional[str]
    is_verified: bool
    is_staff: bool
    created_at: str


class JWTAuth(HttpBearer):
    """JWT authentication for Django Ninja."""

    def authenticate(self, request, token):
        try:
            # Validate token
            payload = jwt_service.validate_token(token, "access")

            # Check if token is blacklisted
            if jwt_service.is_token_blacklisted(payload.get("jti")):
                return None

            # Get user
            User = get_user_model()
            try:
                user = User.objects.get(id=payload["sub"], is_active=True)
                request.user = user
                return user
            except User.DoesNotExist:
                return None

        except (JWTError, TokenExpiredError, InvalidTokenError):
            return None


# Authentication endpoints
@router.post("/login", response={200: TokenResponse, 401: dict})
def login(request, data: LoginRequest):
    """Authenticate user and return JWT tokens."""
    try:
        # Authenticate user
        user = authenticate(request, username=data.email, password=data.password)

        if not user:
            return 401, {
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                }
            }

        if not user.is_active:
            return 401, {
                "error": {"code": "ACCOUNT_DISABLED", "message": "Account is disabled"}
            }

        # Generate JWT tokens
        tokens = jwt_service.generate_tokens(user)

        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        # Return response
        return 200, {
            **tokens,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "organization": user.organization,
                "is_verified": user.is_verified,
                "is_staff": user.is_staff,
                "created_at": user.created_at.isoformat(),
            },
        }

    except Exception as e:
        return 401, {
            "error": {
                "code": "LOGIN_FAILED",
                "message": "Login failed. Please try again.",
            }
        }


@router.post("/register", response={201: TokenResponse, 400: dict})
def register(request, data: RegisterRequest):
    """Register new user account."""
    try:
        User = get_user_model()

        # Check if user already exists
        if User.objects.filter(email=data.email.lower()).exists():
            return 400, {
                "error": {
                    "code": "USER_EXISTS",
                    "message": "User with this email already exists",
                }
            }

        # Validate password
        try:
            validate_password(data.password)
        except ValidationError as e:
            return 400, {
                "error": {"code": "INVALID_PASSWORD", "message": " ".join(e.messages)}
            }

        # Create user
        user = User.objects.create_user(
            email=data.email.lower(),
            password=data.password,
            full_name=data.full_name,
            organization=data.organization,
        )

        # Generate JWT tokens
        tokens = jwt_service.generate_tokens(user)

        # Return response
        return 201, {
            **tokens,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "organization": user.organization,
                "is_verified": user.is_verified,
                "is_staff": user.is_staff,
                "created_at": user.created_at.isoformat(),
            },
        }

    except Exception as e:
        return 400, {
            "error": {
                "code": "REGISTRATION_FAILED",
                "message": "Registration failed. Please try again.",
            }
        }


@router.post("/refresh", response={200: dict, 401: dict})
def refresh_token(request, data: RefreshRequest):
    """Refresh access token using refresh token."""
    try:
        tokens = jwt_service.refresh_access_token(data.refresh_token)
        return 200, tokens

    except TokenExpiredError:
        return 401, {
            "error": {
                "code": "REFRESH_TOKEN_EXPIRED",
                "message": "Refresh token has expired. Please login again.",
            }
        }
    except InvalidTokenError:
        return 401, {
            "error": {
                "code": "INVALID_REFRESH_TOKEN",
                "message": "Invalid refresh token. Please login again.",
            }
        }
    except Exception as e:
        return 401, {
            "error": {
                "code": "TOKEN_REFRESH_FAILED",
                "message": "Failed to refresh token. Please try again.",
            }
        }


@router.post("/logout", response={200: dict, 401: dict})
def logout(request):
    """Logout user and revoke tokens."""
    try:
        # Get token from Authorization header
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return 401, {
                "error": {"code": "NO_TOKEN", "message": "No access token provided"}
            }

        token = auth_header[7:]  # Remove 'Bearer ' prefix

        # Revoke token
        jwt_service.revoke_token(token)

        return 200, {"message": "Successfully logged out"}

    except Exception as e:
        return 401, {
            "error": {
                "code": "LOGOUT_FAILED",
                "message": "Logout failed. Please try again.",
            }
        }


@router.get("/me", response={200: UserResponse, 401: dict}, auth=JWTAuth())
def get_current_user(request):
    """Get current authenticated user information."""
    return 200, {
        "id": str(request.user.id),
        "email": request.user.email,
        "full_name": request.user.full_name,
        "organization": request.user.organization,
        "is_verified": request.user.is_verified,
        "is_staff": request.user.is_staff,
        "created_at": request.user.created_at.isoformat(),
    }


@router.post(
    "/change-password", response={200: dict, 400: dict, 401: dict}, auth=JWTAuth()
)
def change_password(request, data: dict):
    """Change user password."""
    try:
        current_password = data.get("current_password")
        new_password = data.get("new_password")

        if not current_password or not new_password:
            return 400, {
                "error": {
                    "code": "MISSING_FIELDS",
                    "message": "Current password and new password are required",
                }
            }

        # Verify current password
        if not request.user.check_password(current_password):
            return 400, {
                "error": {
                    "code": "INVALID_CURRENT_PASSWORD",
                    "message": "Current password is incorrect",
                }
            }

        # Validate new password
        try:
            validate_password(new_password, user=request.user)
        except ValidationError as e:
            return 400, {
                "error": {"code": "INVALID_PASSWORD", "message": " ".join(e.messages)}
            }

        # Update password
        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])

        # Revoke all existing tokens for security
        UserSession.objects.filter(user=request.user, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )

        return 200, {"message": "Password changed successfully. Please login again."}

    except Exception as e:
        return 400, {
            "error": {
                "code": "PASSWORD_CHANGE_FAILED",
                "message": "Failed to change password. Please try again.",
            }
        }


@router.get("/sessions", response={200: list, 401: dict}, auth=JWTAuth())
def get_active_sessions(request):
    """Get list of active user sessions."""
    try:
        sessions = UserSession.objects.filter(
            user=request.user, revoked_at__isnull=True, expires_at__gt=timezone.now()
        ).order_by("-created_at")

        session_data = []
        for session in sessions:
            session_data.append(
                {
                    "id": str(session.jti),
                    "created_at": session.created_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "ip_address": session.ip_address,
                    "user_agent": session.user_agent,
                    "is_current": session.jti
                    == getattr(request, "_current_session_jti", None),
                }
            )

        return 200, session_data

    except Exception as e:
        return 401, {
            "error": {
                "code": "SESSIONS_FETCH_FAILED",
                "message": "Failed to fetch sessions.",
            }
        }


@router.delete(
    "/sessions/{session_id}", response={200: dict, 404: dict, 401: dict}, auth=JWTAuth()
)
def revoke_session(request, session_id: str):
    """Revoke a specific user session."""
    try:
        session = UserSession.objects.filter(
            user=request.user, jti=session_id, revoked_at__isnull=True
        ).first()

        if not session:
            return 404, {
                "error": {"code": "SESSION_NOT_FOUND", "message": "Session not found"}
            }

        # Revoke session
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])

        return 200, {"message": "Session revoked successfully"}

    except Exception as e:
        return 401, {
            "error": {
                "code": "SESSION_REVOKE_FAILED",
                "message": "Failed to revoke session.",
            }
        }
