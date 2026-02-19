"""
Auth App Pydantic Schemas for Django Ninja.

Request/Response schemas for authentication endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: str = Field(..., min_length=1, max_length=255)
    organization: str | None = Field(None, max_length=255)


class UserLogin(BaseModel):
    """Schema for user login request."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900, description="Access token expiry in seconds")


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class UserResponse(BaseModel):
    """Schema for user profile response."""

    id: str
    email: str
    full_name: str
    organization: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""

    full_name: str | None = Field(None, min_length=1, max_length=255)
    organization: str | None = Field(None, max_length=255)


class PasswordChange(BaseModel):
    """Schema for password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    detail: str
    code: str | None = None


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request."""

    token: str


class ResendVerificationRequest(BaseModel):
    """Schema for resending verification email."""

    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema for password reset request."""

    token: str
    new_password: str = Field(..., min_length=8)


class OAuthCallbackRequest(BaseModel):
    """Schema for OAuth callback."""

    provider: str  # google, github
    code: str
    state: str | None = None


class OAuthTokenResponse(BaseModel):
    """Schema for OAuth token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_user: bool = False
