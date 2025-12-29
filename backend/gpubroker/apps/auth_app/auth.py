"""
JWT Authentication for Django Ninja.

Implements RS256 JWT authentication.
Uses python-jose for JWT encoding/decoding.
"""
import logging
from typing import Optional, Any
from datetime import datetime, timedelta, timezone

from django.conf import settings
from ninja.security import HttpBearer
from jose import jwt, JWTError

logger = logging.getLogger('gpubroker.auth')


class JWTAuth(HttpBearer):
    """
    JWT Bearer token authentication for Django Ninja.
    
    Validates RS256 signed JWT tokens and returns the authenticated user.
    """
    
    async def authenticate(self, request, token: str) -> Optional[Any]:
        """
        Authenticate a request using JWT Bearer token.
        
        Args:
            request: Django request object
            token: JWT token from Authorization header
            
        Returns:
            User instance if valid, None otherwise
        """
        try:
            # Decode and verify JWT
            payload = jwt.decode(
                token,
                settings.JWT_PUBLIC_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Extract email from 'sub' claim
            email: str = payload.get("sub")
            if not email:
                logger.warning("JWT missing 'sub' claim")
                return None
            
            # Check token expiry (jose handles this, but double-check)
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                logger.warning(f"JWT expired for user: {email}")
                return None
            
            # Check token type (reject refresh tokens)
            token_type = payload.get("type")
            if token_type == "refresh":
                logger.warning(f"Refresh token used for authentication: {email}")
                return None
            
            # Async ORM lookup
            from apps.auth_app.models import User
            user = await User.objects.filter(email=email, is_active=True).afirst()
            
            if not user:
                logger.warning(f"User not found or inactive: {email}")
                return None
            
            # Attach token payload to request for later use
            request.jwt_payload = payload
            
            logger.debug(f"Authenticated user: {email}")
            return user
            
        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None


class OptionalJWTAuth(HttpBearer):
    """
    Optional JWT authentication - doesn't fail if no token provided.
    
    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    
    async def authenticate(self, request, token: str) -> Optional[Any]:
        """Authenticate if token provided, return None otherwise."""
        if not token:
            return None
        
        # Delegate to main JWTAuth
        auth = JWTAuth()
        return await auth.authenticate(request, token)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Claims to include in token (must include 'sub' for email)
        expires_delta: Token expiry time (default: 15 minutes)
        
    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_PRIVATE_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Claims to include in token (must include 'sub' for email)
        expires_delta: Token expiry time (default: 7 days)
        
    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_PRIVATE_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decode a JWT token without authentication context.
    
    Args:
        token: JWT token string
        
    Returns:
        Token payload dict or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_refresh_token(token: str) -> Optional[str]:
    """
    Verify a refresh token and return the email.
    
    Args:
        token: JWT refresh token
        
    Returns:
        Email from token if valid refresh token, None otherwise
    """
    payload = decode_token(token)
    if not payload:
        return None
    
    # Must be a refresh token
    if payload.get("type") != "refresh":
        return None
    
    # Check expiry
    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
        return None
    
    return payload.get("sub")
