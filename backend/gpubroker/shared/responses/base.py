"""
Standardized API responses for GPUBroker.

Provides consistent response format across all endpoints.
"""

from django.http import JsonResponse
from django.utils import timezone
from typing import Any, Dict, List, Optional, Union


class APIResponse:
    """Standard API response helper."""

    @staticmethod
    def success(
        data: Any = None,
        message: str = None,
        status_code: int = 200,
        metadata: Dict = None,
    ) -> JsonResponse:
        """Return success response."""
        response = {
            "success": True,
            "timestamp": timezone.now().isoformat(),
        }

        if data is not None:
            response["data"] = data

        if message:
            response["message"] = message

        if metadata:
            response["metadata"] = metadata

        return JsonResponse(response, status=status_code)

    @staticmethod
    def error(
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        status_code: int = 400,
        details: Dict = None,
        trace_id: str = None,
    ) -> JsonResponse:
        """Return error response."""
        response = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
            },
            "timestamp": timezone.now().isoformat(),
        }

        if details:
            response["error"]["details"] = details

        if trace_id:
            response["error"]["trace_id"] = trace_id

        return JsonResponse(response, status=status_code)

    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        per_page: int,
        total: int,
        message: str = None,
        metadata: Dict = None,
    ) -> JsonResponse:
        """Return paginated response."""
        total_pages = (total + per_page - 1) // per_page

        response = {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
            "timestamp": timezone.now().isoformat(),
        }

        if message:
            response["message"] = message

        if metadata:
            response["metadata"] = metadata

        return JsonResponse(response)


def paginate_queryset(queryset, page: int = 1, per_page: int = 20):
    """Paginate a queryset and return pagination info."""
    from django.core.paginator import Paginator

    paginator = Paginator(queryset, per_page)

    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)

    return {
        "items": list(page_obj.object_list),
        "page": page_obj.number,
        "per_page": per_page,
        "total": paginator.count,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    }


class ValidationError(Exception):
    """Custom validation error."""

    def __init__(
        self, message: str, field: str = None, error_code: str = "VALIDATION_ERROR"
    ):
        self.message = message
        self.field = field
        self.error_code = error_code
        super().__init__(message)


class APIError(Exception):
    """Custom API error."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "API_ERROR",
        details: Dict = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)
