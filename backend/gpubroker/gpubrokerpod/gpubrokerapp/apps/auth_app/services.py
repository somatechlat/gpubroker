"""
Auth App Business Logic Services.

Handles user creation, authentication, and token management.
"""
import logging
from typing import Optional, Tuple
from django.conf import settings
from passlib.context import CryptContext

from .models import User, AuditLog
from .auth import create_access_token, create_refresh_token, verify_refresh_token

logger = logging.getLogger('gpubroker.auth')

# Password hashing context - Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)


async def create_user(
    email: str,
    password: str,
    full_name: str,
    organization: Optional[str] = None
) -> User:
    """
    Create a new user.
    
    Args:
        email: User email (unique)
        password: Plain text password (will be hashed)
        full_name: User's full name
        organization: Optional organization name
        
    Returns:
        Created User instance
        
    Raises:
        ValueError: If email already exists
    """
    # Check if user already exists
    existing = await User.objects.filter(email=email).aexists()
    if existing:
        raise ValueError("Email already registered")
    
    # Create user with hashed password
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name,
        organization=organization,
        is_active=True,
        is_verified=False,
    )
    await user.asave()
    
    logger.info(f"Created new user: {email}")
    return user


async def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.
    
    Args:
        email: User email
        password: Plain text password
        
    Returns:
        User instance if credentials valid, None otherwise
    """
    user = await User.objects.filter(email=email).afirst()
    
    if not user:
        logger.warning(f"Login attempt for non-existent user: {email}")
        return None
    
    if not verify_password(password, user.password_hash):
        logger.warning(f"Invalid password for user: {email}")
        return None
    
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {email}")
        return None
    
    logger.info(f"User authenticated: {email}")
    return user


def create_tokens(user: User) -> Tuple[str, str, int]:
    """
    Create access and refresh tokens for a user.
    
    Args:
        user: Authenticated User instance
        
    Returns:
        Tuple of (access_token, refresh_token, expires_in_seconds)
    """
    # Token claims
    token_data = {
        "sub": user.email,
        "roles": [user.role] if hasattr(user, 'role') and user.role else ["user"],
    }
    
    # Add tenant_id if user has a tenant
    if hasattr(user, 'tenant_id') and user.tenant_id:
        token_data["tenant_id"] = str(user.tenant_id)
    
    # Create tokens
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    return access_token, refresh_token, expires_in


async def refresh_tokens(refresh_token: str) -> Optional[Tuple[str, str, int]]:
    """
    Refresh access and refresh tokens.
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        Tuple of (new_access_token, new_refresh_token, expires_in) or None if invalid
    """
    # Verify refresh token
    email = verify_refresh_token(refresh_token)
    if not email:
        logger.warning("Invalid refresh token")
        return None
    
    # Get user
    user = await User.objects.filter(email=email, is_active=True).afirst()
    if not user:
        logger.warning(f"Refresh token for non-existent/inactive user: {email}")
        return None
    
    # Create new tokens
    return create_tokens(user)


async def get_user_by_email(email: str) -> Optional[User]:
    """Get a user by email."""
    return await User.objects.filter(email=email).afirst()


async def get_user_by_id(user_id: str) -> Optional[User]:
    """Get a user by ID."""
    return await User.objects.filter(id=user_id).afirst()


async def update_user_profile(
    user: User,
    full_name: Optional[str] = None,
    organization: Optional[str] = None
) -> User:
    """
    Update user profile.
    
    Args:
        user: User instance to update
        full_name: New full name (optional)
        organization: New organization (optional)
        
    Returns:
        Updated User instance
    """
    if full_name is not None:
        user.full_name = full_name
    if organization is not None:
        user.organization = organization
    
    await user.asave()
    logger.info(f"Updated profile for user: {user.email}")
    return user


async def change_password(
    user: User,
    current_password: str,
    new_password: str
) -> bool:
    """
    Change user password.
    
    Args:
        user: User instance
        current_password: Current password for verification
        new_password: New password to set
        
    Returns:
        True if password changed, False if current password invalid
    """
    if not verify_password(current_password, user.password_hash):
        logger.warning(f"Password change failed - invalid current password: {user.email}")
        return False
    
    user.password_hash = get_password_hash(new_password)
    await user.asave()
    
    logger.info(f"Password changed for user: {user.email}")
    return True


async def log_audit_event(
    event_type: str,
    user: Optional[User] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    event_data: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """
    Log an audit event.
    
    Args:
        event_type: Type of event (e.g., 'login', 'logout', 'password_change')
        user: User who performed the action
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        event_data: Additional event data
        ip_address: Client IP address
        user_agent: Client user agent
    """
    try:
        audit = AuditLog(
            event_type=event_type,
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            event_data=event_data or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await audit.asave()
    except Exception as e:
        # Don't fail the main operation if audit logging fails
        logger.error(f"Failed to log audit event: {e}")


# =============================================================================
# EMAIL VERIFICATION
# =============================================================================

import secrets
import hashlib


def generate_verification_token() -> str:
    """Generate a secure verification token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


async def create_verification_token(user: User) -> str:
    """
    Create an email verification token for a user.
    
    Args:
        user: User to create token for
        
    Returns:
        Plain text token (to be sent via email)
    """
    from django.core.cache import cache
    
    token = generate_verification_token()
    token_hash = hash_token(token)
    
    # Store token hash in cache with 24h expiry
    cache_key = f"email_verification:{token_hash}"
    cache.set(cache_key, str(user.id), timeout=86400)  # 24 hours
    
    logger.info(f"Created verification token for user: {user.email}")
    return token


async def verify_email_token(token: str) -> Optional[User]:
    """
    Verify an email verification token.
    
    Args:
        token: Plain text token from email link
        
    Returns:
        User if token valid, None otherwise
    """
    from django.core.cache import cache
    
    token_hash = hash_token(token)
    cache_key = f"email_verification:{token_hash}"
    
    user_id = cache.get(cache_key)
    if not user_id:
        logger.warning("Invalid or expired verification token")
        return None
    
    # Get user and mark as verified
    user = await User.objects.filter(id=user_id).afirst()
    if not user:
        logger.warning(f"User not found for verification token: {user_id}")
        return None
    
    user.is_verified = True
    await user.asave()
    
    # Delete the token
    cache.delete(cache_key)
    
    logger.info(f"Email verified for user: {user.email}")
    return user


async def create_password_reset_token(email: str) -> Optional[str]:
    """
    Create a password reset token.
    
    Args:
        email: User email
        
    Returns:
        Plain text token or None if user not found
    """
    from django.core.cache import cache
    
    user = await User.objects.filter(email=email, is_active=True).afirst()
    if not user:
        logger.warning(f"Password reset requested for non-existent user: {email}")
        return None
    
    token = generate_verification_token()
    token_hash = hash_token(token)
    
    # Store token hash in cache with 1h expiry
    cache_key = f"password_reset:{token_hash}"
    cache.set(cache_key, str(user.id), timeout=3600)  # 1 hour
    
    logger.info(f"Created password reset token for user: {email}")
    return token


async def reset_password_with_token(token: str, new_password: str) -> bool:
    """
    Reset password using a reset token.
    
    Args:
        token: Plain text token from email link
        new_password: New password to set
        
    Returns:
        True if successful, False otherwise
    """
    from django.core.cache import cache
    
    token_hash = hash_token(token)
    cache_key = f"password_reset:{token_hash}"
    
    user_id = cache.get(cache_key)
    if not user_id:
        logger.warning("Invalid or expired password reset token")
        return False
    
    user = await User.objects.filter(id=user_id).afirst()
    if not user:
        logger.warning(f"User not found for password reset: {user_id}")
        return False
    
    user.password_hash = get_password_hash(new_password)
    await user.asave()
    
    # Delete the token
    cache.delete(cache_key)
    
    logger.info(f"Password reset for user: {user.email}")
    return True


async def send_verification_email(user: User, token: str) -> bool:
    """
    Send verification email to user.
    
    Args:
        user: User to send email to
        token: Verification token
        
    Returns:
        True if sent successfully
    """
    # TODO: Implement AWS SES email sending
    # For now, log the token (SANDBOX mode behavior)
    from django.conf import settings
    
    mode = getattr(settings, 'GPUBROKER_MODE', 'sandbox')
    
    if mode == 'sandbox':
        # In sandbox mode, auto-verify
        logger.info(f"[SANDBOX] Verification token for {user.email}: {token}")
        user.is_verified = True
        await user.asave()
        return True
    
    # In live mode, send actual email via SES
    # TODO: Implement SES integration
    logger.info(f"Would send verification email to {user.email}")
    return True


async def send_password_reset_email(email: str, token: str) -> bool:
    """
    Send password reset email.
    
    Args:
        email: User email
        token: Reset token
        
    Returns:
        True if sent successfully
    """
    from django.conf import settings
    
    mode = getattr(settings, 'GPUBROKER_MODE', 'sandbox')
    
    if mode == 'sandbox':
        logger.info(f"[SANDBOX] Password reset token for {email}: {token}")
        return True
    
    # TODO: Implement SES integration
    logger.info(f"Would send password reset email to {email}")
    return True
