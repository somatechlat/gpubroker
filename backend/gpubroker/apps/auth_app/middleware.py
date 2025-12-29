"""
Auth Middleware - JWT Authentication Middleware.

This middleware:
1. Extracts JWT from Authorization header
2. Validates the token
3. Attaches user to request.user
4. Logs authentication attempts to AuditLog
"""
import logging
from typing import Optional
from django.http import HttpRequest, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from asgiref.sync import sync_to_async

from .auth import decode_token
from .models import User, AuditLog

logger = logging.getLogger('gpubroker.auth.middleware')


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to attach user from JWT to request.
    
    This middleware runs on every request and:
    - Extracts Bearer token from Authorization header
    - Decodes and validates the JWT
    - Attaches the User instance to request.user
    - Handles token expiry gracefully (returns 401)
    
    Note: This is optional middleware. Endpoints can also use
    JWTAuth() directly for more granular control.
    """
    
    # Paths that don't require authentication
    EXEMPT_PATHS = [
        '/api/v2/',
        '/api/v2/docs',
        '/api/v2/openapi.json',
        '/api/v2/auth/register',
        '/api/v2/auth/login',
        '/api/v2/auth/refresh',
        '/health',
        '/admin/',
        '/static/',
    ]
    
    def process_request(self, request: HttpRequest) -> Optional[JsonResponse]:
        """
        Process incoming request and attach user if JWT is valid.
        
        Returns None to continue processing, or JsonResponse on auth failure.
        """
        # Skip exempt paths
        path = request.path
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return None
        
        # Extract Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            # No auth header - let endpoint decide if auth is required
            request.jwt_user = None
            return None
        
        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            request.jwt_user = None
            return None
        
        token = parts[1]
        
        # Decode and validate token
        payload = decode_token(token)
        
        if not payload:
            # Invalid or expired token
            self._log_auth_failure(request, "invalid_token")
            request.jwt_user = None
            return None
        
        # Get user from database
        user_id = payload.get('sub')
        if not user_id:
            request.jwt_user = None
            return None
        
        try:
            user = User.objects.get(id=user_id, is_active=True)
            request.jwt_user = user
            
            # Log successful authentication (only for non-GET requests to reduce noise)
            if request.method != 'GET':
                self._log_auth_success(request, user)
                
        except User.DoesNotExist:
            self._log_auth_failure(request, "user_not_found", user_id=user_id)
            request.jwt_user = None
        
        return None
    
    def _log_auth_failure(
        self,
        request: HttpRequest,
        reason: str,
        user_id: Optional[str] = None
    ) -> None:
        """Log authentication failure to audit log."""
        try:
            AuditLog.objects.create(
                event_type="auth_failure",
                event_data={
                    "reason": reason,
                    "user_id": user_id,
                    "path": request.path,
                    "method": request.method,
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception as e:
            logger.error(f"Failed to log auth failure: {e}")
    
    def _log_auth_success(self, request: HttpRequest, user: User) -> None:
        """Log successful authentication to audit log."""
        try:
            AuditLog.objects.create(
                user=user,
                event_type="auth_success",
                resource_type="api",
                resource_id=request.path,
                event_data={
                    "method": request.method,
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception as e:
            logger.error(f"Failed to log auth success: {e}")
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class AsyncJWTAuthenticationMiddleware:
    """
    Async version of JWT Authentication Middleware.
    
    Use this for ASGI deployments with async views.
    """
    
    EXEMPT_PATHS = [
        '/api/v2/',
        '/api/v2/docs',
        '/api/v2/openapi.json',
        '/api/v2/auth/register',
        '/api/v2/auth/login',
        '/api/v2/auth/refresh',
        '/health',
        '/admin/',
        '/static/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    async def __call__(self, request: HttpRequest):
        """Process request asynchronously."""
        # Skip exempt paths
        path = request.path
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return await self.get_response(request)
        
        # Extract Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            request.jwt_user = None
            return await self.get_response(request)
        
        # Parse Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            request.jwt_user = None
            return await self.get_response(request)
        
        token = parts[1]
        
        # Decode and validate token
        payload = decode_token(token)
        
        if not payload:
            await self._log_auth_failure_async(request, "invalid_token")
            request.jwt_user = None
            return await self.get_response(request)
        
        # Get user from database
        user_id = payload.get('sub')
        if not user_id:
            request.jwt_user = None
            return await self.get_response(request)
        
        try:
            user = await sync_to_async(User.objects.get)(id=user_id, is_active=True)
            request.jwt_user = user
            
            if request.method != 'GET':
                await self._log_auth_success_async(request, user)
                
        except User.DoesNotExist:
            await self._log_auth_failure_async(request, "user_not_found", user_id=user_id)
            request.jwt_user = None
        
        return await self.get_response(request)
    
    async def _log_auth_failure_async(
        self,
        request: HttpRequest,
        reason: str,
        user_id: Optional[str] = None
    ) -> None:
        """Log authentication failure asynchronously."""
        try:
            await sync_to_async(AuditLog.objects.create)(
                event_type="auth_failure",
                event_data={
                    "reason": reason,
                    "user_id": user_id,
                    "path": request.path,
                    "method": request.method,
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception as e:
            logger.error(f"Failed to log auth failure: {e}")
    
    async def _log_auth_success_async(self, request: HttpRequest, user: User) -> None:
        """Log successful authentication asynchronously."""
        try:
            await sync_to_async(AuditLog.objects.create)(
                user=user,
                event_type="auth_success",
                resource_type="api",
                resource_id=request.path,
                event_data={
                    "method": request.method,
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception as e:
            logger.error(f"Failed to log auth success: {e}")
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
