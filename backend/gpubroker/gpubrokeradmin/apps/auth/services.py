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
import logging
from typing import Optional, Dict, Any
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

from .models import AdminUser, AdminSession, AdminAuditLog

logger = logging.getLogger('gpubroker.auth')

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", settings.SECRET_KEY)
JWT_EXPIRY = int(os.getenv("JWT_EXPIRY", 86400))  # 24 hours


def create_jwt(payload: dict) -> str:
    """
    Create a JWT token.
    
    Args:
        payload: Token payload data
        
    Returns:
        JWT token string
    """
    header = {"alg": "HS256", "typ": "JWT"}
    
    # Add expiry
    payload["exp"] = int(time.time()) + JWT_EXPIRY
    payload["iat"] = int(time.time())
    
    # Encode
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header).encode()
    ).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip("=")
    
    # Sign
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        JWT_SECRET.encode(), 
        message.encode(), 
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload or None if invalid
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, signature_b64 = parts
        
        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            JWT_SECRET.encode(), 
            message.encode(), 
            hashlib.sha256
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
        user_agent: str = ""
    ) -> Dict[str, Any]:
        """
        Authenticate admin user and return JWT token.
        
        Args:
            email: User email
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict with success status, token, and user info
        """
        if not email or not password:
            return {"success": False, "error": "Email y contraseña requeridos"}
        
        email = email.lower().strip()
        
        try:
            user = AdminUser.objects.get(email=email, is_active=True)
        except AdminUser.DoesNotExist:
            return {"success": False, "error": "Usuario no encontrado"}
        
        if not user.check_password(password):
            return {"success": False, "error": "Contraseña incorrecta"}
        
        # Create token
        token = create_jwt({
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
            "name": user.name
        })
        
        # Create session record
        session = AdminSession.objects.create(
            user=user,
            token_hash=hash_token(token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=timezone.now() + timedelta(seconds=JWT_EXPIRY)
        )
        
        # Update last login
        user.last_login_at = timezone.now()
        user.last_login_ip = ip_address
        user.save(update_fields=['last_login_at', 'last_login_ip'])
        
        # Audit log
        AdminAuditLog.objects.create(
            user=user,
            action=AdminAuditLog.ActionType.LOGIN,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"session_id": str(session.id)}
        )
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "name": user.name
            }
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
            user = AdminUser.objects.get(
                id=payload.get("user_id"),
                is_active=True
            )
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
                details={"session_id": str(session.id)}
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
