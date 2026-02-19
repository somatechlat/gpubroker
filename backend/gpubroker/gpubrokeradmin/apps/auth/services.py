"""
GPUBROKER Admin Authentication Services

JWT-based authentication service for GPUBROKER POD Admin.
"""

import os
import hashlib
import hmac
import json
import time
import base64
import binascii
import logging
import secrets
from typing import Optional, Dict, Any
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

from .models import AdminUser, AdminSession, AdminAuditLog

logger = logging.getLogger("gpubroker.auth")

# Security Configuration
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET or JWT_SECRET in ["change-me", "insecure", ""]:
    raise ValueError("JWT_SECRET environment variable must be set to a secure value")

JWT_EXPIRY = int(os.getenv("JWT_EXPIRY", 900))  # 15 minutes (reduced from 24 hours)
REFRESH_TOKEN_EXPIRY = int(os.getenv("REFRESH_TOKEN_EXPIRY", 86400))  # 24 hours
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))
ACCOUNT_LOCKOUT_TIME = int(os.getenv("ACCOUNT_LOCKOUT_TIME", 900))  # 15 minutes


def create_jwt(payload: dict, expiry: Optional[int] = None) -> str:
    """
    Create a JWT token with security enhancements.

    Args:
        payload: Token payload data
        expiry: Custom expiry time (optional)

    Returns:
        JWT token string
    """
    if not JWT_SECRET:
        raise ValueError("JWT secret is not configured")

    # Security: Add unique identifier and timestamp
    header = {"alg": "HS256", "typ": "JWT", "jti": secrets.token_urlsafe(16)}

    # Add security claims
    token_expiry = expiry or JWT_EXPIRY
    payload.update(
        {
            "exp": int(time.time()) + token_expiry,
            "iat": int(time.time()),
            "nbf": int(time.time()),  # Not before
            "iss": "gpubroker-admin",  # Issuer
            "aud": "gpubroker-admin",  # Audience
        }
    )

    # Encode components
    header_b64 = (
        base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )

    # Create signature
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        JWT_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token with comprehensive security checks.

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid
    """
    if not JWT_SECRET:
        logger.error("JWT secret is not configured")
        return None

    try:
        # Check token format
        if not token or not isinstance(token, str):
            return None

        parts = token.split(".")
        if len(parts) != 3:
            logger.warning("Invalid JWT format")
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Check token length (prevent very long tokens)
        if len(token) > 2048:
            logger.warning("JWT token too long")
            return None

        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            JWT_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            logger.warning("JWT signature verification failed")
            return None

        # Decode payload safely
        payload_b64_padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64_padded)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Verify security claims
        now = int(time.time())

        # Check expiration
        exp = payload.get("exp")
        if not exp or exp < now:
            logger.warning("JWT token expired")
            return None

        # Check not before
        nbf = payload.get("nbf")
        if nbf and nbf > now:
            logger.warning("JWT token not yet valid")
            return None

        # Check issued at
        iat = payload.get("iat")
        if not iat or iat > now + 60:  # Allow 60 seconds clock skew
            logger.warning("JWT issued in the future")
            return None

        # Verify issuer and audience
        if payload.get("iss") != "gpubroker-admin":
            logger.warning("Invalid JWT issuer")
            return None

        if payload.get("aud") != "gpubroker-admin":
            logger.warning("Invalid JWT audience")
            return None

        return payload

    except (
        ValueError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        binascii.Error,
    ) as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.warning(f"JWT verification error: {e}")
        return None

    try:
        # Check token format
        if not token or not isinstance(token, str):
            return None

        parts = token.split(".")
        if len(parts) != 3:
            logger.warning("Invalid JWT format")
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Check token length (prevent very long tokens)
        if len(token) > 2048:
            logger.warning("JWT token too long")
            return None

        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            JWT_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            logger.warning("JWT signature verification failed")
            return None

        # Decode payload safely
        try:
            payload_b64_padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64_padded)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"JWT payload decode error: {e}")
            return None

        # Verify security claims
        now = int(time.time())

        # Check expiration
        exp = payload.get("exp")
        if not exp or exp < now:
            logger.warning("JWT token expired")
            return None

        # Check not before
        nbf = payload.get("nbf")
        if nbf and nbf > now:
            logger.warning("JWT token not yet valid")
            return None

        # Check issued at
        iat = payload.get("iat")
        if not iat or iat > now + 60:  # Allow 60 seconds clock skew
            logger.warning("JWT issued in the future")
            return None

        # Verify issuer and audience
        if payload.get("iss") != "gpubroker-admin":
            logger.warning("Invalid JWT issuer")
            return None

        if payload.get("aud") != "gpubroker-admin":
            logger.warning("Invalid JWT audience")
            return None

        return payload

    except Exception as e:
        logger.warning(f"JWT verification error: {e}")
        return None

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            JWT_SECRET.encode(), message.encode(), hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            return None

        # Decode payload
        payload_b64_padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64_padded))

        # Check expiry
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception as e:
        logger.warning(f"JWT verification error: {e}")
        return None


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class AdminAuthService:
    """
    Admin authentication service.
    """

    @staticmethod
    def login(
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> Dict[str, Any]:
        """
        Authenticate admin user with enhanced security checks.

        Args:
            email: User email
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Dict with success status, token, and user info
        """
        # Input validation
        if not email or not password:
            return {"success": False, "error": "Email y contraseña requeridos"}

        # Email format validation
        email = email.lower().strip()
        if len(email) > 254 or "@" not in email:
            return {"success": False, "error": "Formato de email inválido"}

        # Password length check
        if len(password) > 128:
            return {"success": False, "error": "Contraseña demasiado larga"}

        # IP-based rate limiting check
        if ip_address:
            login_attempts_key = f"login_attempts:{ip_address}"
            attempts = cache.get(login_attempts_key, 0)
            if attempts >= MAX_LOGIN_ATTEMPTS:
                logger.warning(
                    f"IP {ip_address} blocked due to too many login attempts"
                )
                return {
                    "success": False,
                    "error": "Demasiados intentos. Intente más tarde.",
                }

        try:
            user = AdminUser.objects.get(email=email, is_active=True)
        except AdminUser.DoesNotExist:
            # Record failed attempt for IP
            if ip_address:
                login_attempts_key = f"login_attempts:{ip_address}"
                attempts = cache.incr(login_attempts_key)
                if attempts == 1:
                    cache.set(
                        login_attempts_key, attempts, timeout=ACCOUNT_LOCKOUT_TIME
                    )
            return {"success": False, "error": "Credenciales inválidas"}

        # Check account lockout
        if user.is_locked:
            if user.lockout_until and user.lockout_until > timezone.now():
                return {"success": False, "error": "Cuenta bloqueada temporalmente"}
            else:
                # Lockout expired, reset
                user.is_locked = False
                user.lockout_until = None
                user.failed_login_attempts = 0
                user.save(
                    update_fields=[
                        "is_locked",
                        "lockout_until",
                        "failed_login_attempts",
                    ]
                )

        # Password verification with timing attack protection
        if not user.check_password(password):
            # Increment failed attempts
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

            # Lock account if too many attempts
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.is_locked = True
                user.lockout_until = timezone.now() + timedelta(
                    seconds=ACCOUNT_LOCKOUT_TIME
                )
                logger.warning(f"User {email} locked due to failed login attempts")

            user.save(
                update_fields=["failed_login_attempts", "is_locked", "lockout_until"]
            )

            # Record failed attempt for IP
            if ip_address:
                login_attempts_key = f"login_attempts:{ip_address}"
                attempts = cache.incr(login_attempts_key)
                if attempts == 1:
                    cache.set(
                        login_attempts_key, attempts, timeout=ACCOUNT_LOCKOUT_TIME
                    )

            # Log failed attempt
            AdminAuditLog.objects.create(
                user=user,
                action=AdminAuditLog.ActionType.LOGIN_FAILED,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"failed_attempts": user.failed_login_attempts},
            )

            return {"success": False, "error": "Credenciales inválidas"}

        # Successful authentication - reset counters
        user.failed_login_attempts = 0
        user.is_locked = False
        user.lockout_until = None
        user.last_login_at = timezone.now()
        user.last_login_ip = ip_address
        user.save(
            update_fields=[
                "failed_login_attempts",
                "is_locked",
                "lockout_until",
                "last_login_at",
                "last_login_ip",
            ]
        )

        # Create access token (short-lived)
        access_token = create_jwt(
            {
                "user_id": str(user.id),
                "email": user.email,
                "role": user.role,
                "name": user.name,
                "token_type": "access",
            },
            expiry=JWT_EXPIRY,
        )

        # Create refresh token (longer-lived)
        refresh_token = create_jwt(
            {"user_id": str(user.id), "email": user.email, "token_type": "refresh"},
            expiry=REFRESH_TOKEN_EXPIRY,
        )

        # Create session record
        session = AdminSession.objects.create(
            user=user,
            token_hash=hash_token(access_token),
            refresh_token_hash=hash_token(refresh_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=timezone.now() + timedelta(seconds=REFRESH_TOKEN_EXPIRY),
        )

        # Clear IP-based rate limiting on successful login
        if ip_address:
            cache.delete(f"login_attempts:{ip_address}")

        # Audit log successful login
        AdminAuditLog.objects.create(
            user=user,
            action=AdminAuditLog.ActionType.LOGIN,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "session_id": str(session.id),
                "ip_address": ip_address,
                "user_agent": user_agent[:200],  # Truncate for security
            },
        )

        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": JWT_EXPIRY,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "name": user.name,
            },
        }

    @staticmethod
    def verify_token(token: str) -> Optional[AdminUser]:
        """
        Verify token and return user.

        Args:
            token: JWT token

        Returns:
            AdminUser or None
        """
        payload = verify_jwt(token)
        if not payload:
            return None

        try:
            user = AdminUser.objects.get(id=payload.get("user_id"), is_active=True)
            return user
        except AdminUser.DoesNotExist:
            return None

    @staticmethod
    def logout(token: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Logout user by revoking session.

        Args:
            token: JWT token
            ip_address: Client IP

        Returns:
            Dict with success status
        """
        token_hash = hash_token(token)

        try:
            session = AdminSession.objects.get(token_hash=token_hash)
            session.revoke()

            # Audit log
            AdminAuditLog.objects.create(
                user=session.user,
                action=AdminAuditLog.ActionType.LOGOUT,
                ip_address=ip_address,
                details={"session_id": str(session.id)},
            )

            return {"success": True}
        except AdminSession.DoesNotExist:
            return {"success": False, "error": "Session not found"}

    @staticmethod
    def get_current_user(token: str) -> Optional[Dict[str, Any]]:
        """
        Get current user from token.

        Args:
            token: JWT token

        Returns:
            User dict or None
        """
        payload = verify_jwt(token)
        if not payload:
            return None
        return payload
