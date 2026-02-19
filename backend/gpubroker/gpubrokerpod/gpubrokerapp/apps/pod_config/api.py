"""
POD Configuration API.

Django Ninja API for GPUBROKER POD configuration CRUD operations.
Supports SANDBOX and LIVE modes with parameter inheritance.

Endpoints:
- POST/GET/PUT/DELETE /api/v2/config/pods
- POST/GET/PUT/DELETE /api/v2/config/pods/{pod_id}/parameters
- POST /api/v2/config/pods/{pod_id}/switch-mode
- GET /api/v2/config/pods/{pod_id}/audit-logs

Requirements: 1.2, 1.3, 1.4, 1.5, 2.1, 2.6
"""

import logging
from datetime import datetime

from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.errors import HttpError

from .models import ParameterAuditLog, PodConfiguration, PodParameter
from .schemas import (
    AuditLogListResponseSchema,
    AuditLogResponseSchema,
    BulkExportResponseSchema,
    BulkImportSchema,
    BulkParameterSchema,
    ModeSwitchResponseSchema,
    ModeSwitchSchema,
    ParameterCreateSchema,
    ParameterListResponseSchema,
    ParameterResponseSchema,
    ParameterUpdateSchema,
    PodConfigCreateSchema,
    PodConfigListResponseSchema,
    PodConfigResponseSchema,
    PodConfigUpdateSchema,
)

logger = logging.getLogger("gpubroker.pod_config.api")

router = Router(tags=["config"])


def get_client_ip(request: HttpRequest) -> str:
    """Extract client IP from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


# =============================================================================
# POD CONFIGURATION CRUD
# =============================================================================


@router.get("/pods", response=PodConfigListResponseSchema)
def list_pods(
    request: HttpRequest,
    mode: str | None = Query(None, description="Filter by mode (sandbox/live)"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """
    List all POD configurations.

    ADMIN ONLY - Returns all PODs with optional filtering.
    """
    queryset = PodConfiguration.objects.all()

    if mode:
        queryset = queryset.filter(mode=mode)
    if status:
        queryset = queryset.filter(status=status)

    total = queryset.count()
    start = (page - 1) * per_page
    end = start + per_page
    items = list(queryset[start:end])

    return PodConfigListResponseSchema(
        total=total, items=[PodConfigResponseSchema.from_orm(pod) for pod in items]
    )


@router.get("/pods/{pod_id}", response=PodConfigResponseSchema)
def get_pod(request: HttpRequest, pod_id: str):
    """
    Get POD configuration by ID.
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)
    return PodConfigResponseSchema.from_orm(pod)


@router.post("/pods", response=PodConfigResponseSchema)
def create_pod(request: HttpRequest, data: PodConfigCreateSchema):
    """
    Create new POD configuration.

    ADMIN ONLY - Creates a new POD with default parameters.
    """
    # Check if pod_id already exists
    if PodConfiguration.objects.filter(pod_id=data.pod_id).exists():
        raise HttpError(409, f"POD with ID '{data.pod_id}' already exists")

    with transaction.atomic():
        pod = PodConfiguration.objects.create(
            pod_id=data.pod_id,
            name=data.name,
            description=data.description,
            mode=data.mode,
            aws_region=data.aws_region,
            aws_account_id=data.aws_account_id,
            agent_zero_enabled=data.agent_zero_enabled,
            websocket_enabled=data.websocket_enabled,
            webhooks_enabled=data.webhooks_enabled,
            rate_limit_free=data.rate_limit_free,
            rate_limit_pro=data.rate_limit_pro,
            rate_limit_enterprise=data.rate_limit_enterprise,
            markup_percentage=data.markup_percentage,
            owner_email=data.owner_email,
        )

        # Create audit log
        ParameterAuditLog.objects.create(
            pod=pod,
            changed_by_email=getattr(request, "user_email", ""),
            old_value=None,
            new_value=f"POD created: {pod.pod_id}",
            mode_affected="both",
            change_reason="POD creation",
            change_type="create",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    logger.info(f"POD created: {pod.pod_id}")
    return PodConfigResponseSchema.from_orm(pod)


@router.put("/pods/{pod_id}", response=PodConfigResponseSchema)
def update_pod(request: HttpRequest, pod_id: str, data: PodConfigUpdateSchema):
    """
    Update POD configuration.

    ADMIN ONLY - Updates POD settings (not mode).
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)

    with transaction.atomic():
        # Track changes for audit
        changes = []

        for field, value in data.dict(exclude_unset=True).items():
            if value is not None:
                old_value = getattr(pod, field)
                if old_value != value:
                    changes.append(f"{field}: {old_value} → {value}")
                    setattr(pod, field, value)

        if changes:
            pod.save()

            # Create audit log
            ParameterAuditLog.objects.create(
                pod=pod,
                changed_by_email=getattr(request, "user_email", ""),
                old_value=None,
                new_value="; ".join(changes),
                mode_affected="both",
                change_reason="POD configuration update",
                change_type="update",
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

    logger.info(f"POD updated: {pod.pod_id}")
    return PodConfigResponseSchema.from_orm(pod)


@router.delete("/pods/{pod_id}")
def delete_pod(request: HttpRequest, pod_id: str):
    """
    Delete POD configuration.

    ADMIN ONLY - Soft deletes the POD (sets status to deleted).
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)

    with transaction.atomic():
        # Soft delete
        pod.status = PodConfiguration.Status.DELETED
        pod.save(update_fields=["status", "updated_at"])

        # Create audit log
        ParameterAuditLog.objects.create(
            pod=pod,
            changed_by_email=getattr(request, "user_email", ""),
            old_value=None,
            new_value=f"POD deleted: {pod.pod_id}",
            mode_affected="both",
            change_reason="POD deletion",
            change_type="delete",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    logger.info(f"POD deleted: {pod.pod_id}")
    return {"success": True, "message": f"POD {pod_id} deleted"}


# =============================================================================
# POD PARAMETER CRUD
# =============================================================================


@router.get("/pods/{pod_id}/parameters", response=ParameterListResponseSchema)
def list_parameters(
    request: HttpRequest,
    pod_id: str,
    parameter_type: str | None = Query(None, description="Filter by type"),
    is_sensitive: bool | None = Query(None, description="Filter by sensitivity"),
    search: str | None = Query(None, description="Search by key"),
):
    """
    List all parameters for a POD.
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)
    queryset = pod.parameters.all()

    if parameter_type:
        queryset = queryset.filter(parameter_type=parameter_type)
    if is_sensitive is not None:
        queryset = queryset.filter(is_sensitive=is_sensitive)
    if search:
        queryset = queryset.filter(key__icontains=search)

    items = list(queryset)

    return ParameterListResponseSchema(
        total=len(items),
        items=[ParameterResponseSchema.from_orm(param) for param in items],
    )


@router.get("/pods/{pod_id}/parameters/{key}", response=ParameterResponseSchema)
def get_parameter(request: HttpRequest, pod_id: str, key: str):
    """
    Get specific parameter by key.
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)
    param = get_object_or_404(PodParameter, pod=pod, key=key)
    return ParameterResponseSchema.from_orm(param)


@router.post("/pods/{pod_id}/parameters", response=ParameterResponseSchema)
def create_parameter(request: HttpRequest, pod_id: str, data: ParameterCreateSchema):
    """
    Create new parameter for POD.
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)

    # Check if key already exists
    if PodParameter.objects.filter(pod=pod, key=data.key).exists():
        raise HttpError(409, f"Parameter '{data.key}' already exists for this POD")

    with transaction.atomic():
        param = PodParameter.objects.create(
            pod=pod,
            key=data.key,
            sandbox_value=data.sandbox_value,
            live_value=data.live_value,
            default_value=data.default_value,
            parameter_type=data.parameter_type,
            description=data.description,
            is_sensitive=data.is_sensitive,
            is_required=data.is_required,
            validation_regex=data.validation_regex,
            min_value=data.min_value,
            max_value=data.max_value,
        )

        # Create audit log
        ParameterAuditLog.objects.create(
            parameter=param,
            changed_by_email=getattr(request, "user_email", ""),
            old_value=None,
            new_value=f"sandbox={data.sandbox_value}, live={data.live_value}",
            mode_affected="both",
            change_reason="Parameter creation",
            change_type="create",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    logger.info(f"Parameter created: {pod.pod_id}:{data.key}")
    return ParameterResponseSchema.from_orm(param)


@router.put("/pods/{pod_id}/parameters/{key}", response=ParameterResponseSchema)
def update_parameter(
    request: HttpRequest, pod_id: str, key: str, data: ParameterUpdateSchema
):
    """
    Update parameter with audit logging.

    Requirements: 1.5
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)
    param = get_object_or_404(PodParameter, pod=pod, key=key)

    with transaction.atomic():
        # Track old values
        old_sandbox = param.sandbox_value
        old_live = param.live_value

        # Determine which mode was affected
        mode_affected = "both"
        if data.sandbox_value is not None and data.live_value is None:
            mode_affected = "sandbox"
        elif data.live_value is not None and data.sandbox_value is None:
            mode_affected = "live"

        # Update fields
        for field, value in data.dict(exclude_unset=True).items():
            if field != "change_reason" and value is not None:
                setattr(param, field, value)

        param.save()

        # Create audit log
        ParameterAuditLog.objects.create(
            parameter=param,
            changed_by_email=getattr(request, "user_email", ""),
            old_value=f"sandbox={old_sandbox}, live={old_live}",
            new_value=f"sandbox={param.sandbox_value}, live={param.live_value}",
            mode_affected=mode_affected,
            change_reason=data.change_reason or "Parameter update",
            change_type="update",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    logger.info(f"Parameter updated: {pod.pod_id}:{key}")
    return ParameterResponseSchema.from_orm(param)


@router.delete("/pods/{pod_id}/parameters/{key}")
def delete_parameter(request: HttpRequest, pod_id: str, key: str):
    """
    Delete parameter.
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)
    param = get_object_or_404(PodParameter, pod=pod, key=key)

    with transaction.atomic():
        # Create audit log before deletion
        ParameterAuditLog.objects.create(
            pod=pod,  # Use pod reference since parameter will be deleted
            changed_by_email=getattr(request, "user_email", ""),
            old_value=f"key={key}, sandbox={param.sandbox_value}, live={param.live_value}",
            new_value=None,
            mode_affected="both",
            change_reason="Parameter deletion",
            change_type="delete",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        param.delete()

    logger.info(f"Parameter deleted: {pod.pod_id}:{key}")
    return {"success": True, "message": f"Parameter {key} deleted"}


# =============================================================================
# MODE SWITCHING
# =============================================================================


@router.post("/pods/{pod_id}/switch-mode", response=ModeSwitchResponseSchema)
def switch_mode(request: HttpRequest, pod_id: str, data: ModeSwitchSchema):
    """
    Switch POD between SANDBOX and LIVE modes.

    Requires confirmation string for LIVE mode.

    Requirements: 2.1, 2.6
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)

    # Validate mode
    if data.mode not in [PodConfiguration.Mode.SANDBOX, PodConfiguration.Mode.LIVE]:
        raise HttpError(400, f"Invalid mode: {data.mode}. Must be 'sandbox' or 'live'")

    # Check if already in target mode
    if pod.mode == data.mode:
        return ModeSwitchResponseSchema(
            success=True,
            pod_id=pod_id,
            old_mode=pod.mode,
            new_mode=data.mode,
            message=f"POD is already in {data.mode} mode",
        )

    # Require confirmation for LIVE mode
    expected_confirmation = f"SWITCH-{pod_id}-TO-LIVE"
    if data.mode == PodConfiguration.Mode.LIVE:
        if data.confirmation != expected_confirmation:
            raise HttpError(
                400,
                f"Invalid confirmation for LIVE mode switch. "
                f"Expected: '{expected_confirmation}'",
            )

    old_mode = pod.mode

    with transaction.atomic():
        # Switch mode
        pod.switch_mode(data.mode)

        # Create audit log
        ParameterAuditLog.objects.create(
            pod=pod,
            changed_by_email=getattr(request, "user_email", ""),
            old_value=old_mode,
            new_value=data.mode,
            mode_affected="both",
            change_reason=data.reason or f"Mode switch from {old_mode} to {data.mode}",
            change_type="mode_switch",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    logger.info(f"POD mode switched: {pod_id} from {old_mode} to {data.mode}")

    return ModeSwitchResponseSchema(
        success=True,
        pod_id=pod_id,
        old_mode=old_mode,
        new_mode=data.mode,
        message=f"Successfully switched from {old_mode} to {data.mode}",
    )


# =============================================================================
# AUDIT LOGS
# =============================================================================


@router.get("/pods/{pod_id}/audit-logs", response=AuditLogListResponseSchema)
def list_audit_logs(
    request: HttpRequest,
    pod_id: str,
    change_type: str | None = Query(None, description="Filter by change type"),
    mode_affected: str | None = Query(None, description="Filter by mode affected"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """
    List audit logs for a POD.

    Requirements: 1.5
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)

    # Get logs from both parameter and pod references
    from django.db.models import Q

    queryset = ParameterAuditLog.objects.filter(
        Q(parameter__pod=pod) | Q(pod=pod)
    ).order_by("-created_at")

    if change_type:
        queryset = queryset.filter(change_type=change_type)
    if mode_affected:
        queryset = queryset.filter(mode_affected=mode_affected)

    total = queryset.count()
    start = (page - 1) * per_page
    end = start + per_page
    items = list(queryset[start:end])

    return AuditLogListResponseSchema(
        total=total, items=[AuditLogResponseSchema.from_orm(log) for log in items]
    )


# =============================================================================
# BULK OPERATIONS
# =============================================================================


@router.post("/pods/{pod_id}/parameters/bulk-import")
def bulk_import_parameters(request: HttpRequest, pod_id: str, data: BulkImportSchema):
    """
    Bulk import parameters for a POD.

    Requirements: 15.4
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)

    created = 0
    updated = 0
    skipped = 0

    with transaction.atomic():
        for param_data in data.parameters:
            existing = PodParameter.objects.filter(pod=pod, key=param_data.key).first()

            if existing:
                if data.overwrite_existing:
                    # Update existing
                    existing.sandbox_value = param_data.sandbox_value
                    existing.live_value = param_data.live_value
                    existing.default_value = param_data.default_value
                    existing.parameter_type = param_data.parameter_type
                    existing.description = param_data.description
                    existing.is_sensitive = param_data.is_sensitive
                    existing.is_required = param_data.is_required
                    existing.save()
                    updated += 1
                else:
                    skipped += 1
            else:
                # Create new
                PodParameter.objects.create(
                    pod=pod,
                    key=param_data.key,
                    sandbox_value=param_data.sandbox_value,
                    live_value=param_data.live_value,
                    default_value=param_data.default_value,
                    parameter_type=param_data.parameter_type,
                    description=param_data.description,
                    is_sensitive=param_data.is_sensitive,
                    is_required=param_data.is_required,
                )
                created += 1

        # Create audit log
        ParameterAuditLog.objects.create(
            pod=pod,
            changed_by_email=getattr(request, "user_email", ""),
            old_value=None,
            new_value=f"Bulk import: {created} created, {updated} updated, {skipped} skipped",
            mode_affected="both",
            change_reason="Bulk parameter import",
            change_type="create",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    logger.info(
        f"Bulk import for {pod_id}: {created} created, {updated} updated, {skipped} skipped"
    )

    return {
        "success": True,
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }


@router.get("/pods/{pod_id}/parameters/bulk-export", response=BulkExportResponseSchema)
def bulk_export_parameters(request: HttpRequest, pod_id: str):
    """
    Bulk export parameters for a POD.

    Requirements: 15.4
    """
    pod = get_object_or_404(PodConfiguration, pod_id=pod_id)

    parameters = [
        BulkParameterSchema(
            key=param.key,
            sandbox_value=param.sandbox_value if not param.is_sensitive else None,
            live_value=param.live_value if not param.is_sensitive else None,
            default_value=param.default_value,
            parameter_type=param.parameter_type,
            description=param.description,
            is_sensitive=param.is_sensitive,
            is_required=param.is_required,
        )
        for param in pod.parameters.all()
    ]

    return BulkExportResponseSchema(
        pod_id=pod_id,
        mode=pod.mode,
        exported_at=datetime.now(),
        parameters=parameters,
    )
