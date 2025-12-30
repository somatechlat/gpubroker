"""
GPUBROKER API v2 - Django Ninja API.

This module configures the main NinjaAPI instance with:
- OpenAPI documentation at /api/v2/docs
- Consistent error handling
- JWT authentication
- API versioning

Structure:
- /api/v2/ - Root API info
- /api/v2/auth/ - Authentication (GPUBROKERAPP)
- /api/v2/providers/ - Provider marketplace (GPUBROKERAPP)
- /api/v2/kpi/ - KPI calculations (GPUBROKERAPP)
- /api/v2/math/ - Math algorithms (GPUBROKERAPP)
- /api/v2/ai/ - AI assistant (GPUBROKERAPP)
- /api/v2/admin/ - Admin endpoints (GPUBROKERADMIN)
- /api/v2/agent/ - Agent endpoints (GPUBROKERAGENT - ADMIN ONLY)
"""
import uuid
import logging

from ninja import NinjaAPI
from ninja.errors import ValidationError, HttpError
from django.http import JsonResponse

logger = logging.getLogger('gpubroker.api')


def generate_trace_id() -> str:
    """Generate a unique trace ID for error tracking."""
    return str(uuid.uuid4())


# Create the main API instance
api = NinjaAPI(
    title="GPUBROKER API",
    version="2.0.0",
    description="""
    GPU marketplace platform API - Django Ninja v2
    
    Components:
    - GPUBROKERAPP: User-facing SaaS application
    - GPUBROKERADMIN: Control plane for POD management
    - GPUBROKERAGENT: Agentic layer (ADMIN ONLY)
    """,
    urls_namespace="api-v2",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@api.exception_handler(ValidationError)
def validation_error_handler(request, exc: ValidationError):
    """Handle Pydantic/Ninja validation errors."""
    trace_id = generate_trace_id()
    logger.warning(
        f"Validation error: {exc.errors}",
        extra={'trace_id': trace_id, 'path': request.path}
    )
    return JsonResponse({
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors,
            "trace_id": trace_id
        }
    }, status=422)


@api.exception_handler(HttpError)
def http_error_handler(request, exc: HttpError):
    """Handle HTTP errors raised by endpoints."""
    trace_id = generate_trace_id()
    
    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    
    error_code = error_codes.get(exc.status_code, "ERROR")
    
    logger.warning(
        f"HTTP error {exc.status_code}: {exc.message}",
        extra={'trace_id': trace_id, 'path': request.path}
    )
    
    return JsonResponse({
        "error": {
            "code": error_code,
            "message": str(exc.message),
            "details": None,
            "trace_id": trace_id
        }
    }, status=exc.status_code)


@api.exception_handler(Exception)
def generic_error_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    trace_id = generate_trace_id()
    logger.exception(
        f"Unhandled exception: {exc}",
        extra={'trace_id': trace_id, 'path': request.path}
    )
    
    return JsonResponse({
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": None,
            "trace_id": trace_id
        }
    }, status=500)


# =============================================================================
# ROOT ENDPOINT
# =============================================================================

@api.get("/", tags=["info"])
def api_info(request):
    """API information endpoint."""
    from django.conf import settings
    return {
        "name": "GPUBROKER API",
        "version": "2.0.0",
        "mode": settings.GPUBROKER_MODE,
        "status": "operational",
        "docs": "/api/v2/docs",
        "components": {
            "gpubrokerapp": "User-facing SaaS application",
            "gpubrokeradmin": "Control plane for POD management",
            "gpubrokeragent": "Agentic layer (ADMIN ONLY)",
        }
    }


# =============================================================================
# REGISTER ROUTERS
# =============================================================================

# GPUBROKERAPP routers (user-facing)
from gpubrokerpod.gpubrokerapp.apps.auth_app.api import router as auth_router
from gpubrokerpod.gpubrokerapp.apps.providers.api import router as providers_router
from gpubrokerpod.gpubrokerapp.apps.kpi.api import router as kpi_router
from gpubrokerpod.gpubrokerapp.apps.math_core.api import router as math_router
from gpubrokerpod.gpubrokerapp.apps.ai_assistant.api import router as ai_router

api.add_router("/auth/", auth_router, tags=["auth"])
api.add_router("/providers/", providers_router, tags=["providers"])
api.add_router("/kpi/", kpi_router, tags=["kpi"])
api.add_router("/math/", math_router, tags=["math"])
api.add_router("/ai/", ai_router, tags=["ai"])

# GPUBROKERADMIN routers (control plane)
from gpubrokeradmin.api.router import public_router as admin_public_router
from gpubrokeradmin.api.router import admin_router

api.add_router("/admin/public/", admin_public_router, tags=["admin-public"])
api.add_router("/admin/", admin_router, tags=["admin"])

# GPUBROKERAGENT routers (agentic layer - ADMIN ONLY)
# TODO: Add agent routers when apps are implemented
# from gpubrokerpod.gpubrokeragent.apps.agent_core.api import router as agent_router
# api.add_router("/agent/", agent_router, tags=["agent"])
