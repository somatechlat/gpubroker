"""
Deployment API.

Django Ninja API for pod configuration, deployment, and lifecycle management.

Endpoints:
- POST/GET/PUT/DELETE /api/v2/deployment/configs - Pod configuration CRUD
- POST /api/v2/deployment/estimate - Cost estimation
- POST /api/v2/deployment/validate - Configuration validation
- POST /api/v2/deployment/deploy - Deploy a configuration
- GET /api/v2/deployment/status/{id} - Deployment status
- POST /api/v2/deployment/activate - Activate a pod
- POST /api/v2/deployment/pods/{id}/action - Pod lifecycle actions
- GET /api/v2/deployment/pods/{id}/logs - Deployment logs
- GET /api/v2/deployment/limits - Provider limits

Requirements:
- 11.1-11.6: Configure Pod
- 12.1-12.8: Deployment
- 13.1-13.7: Activation
"""

import logging
from uuid import UUID

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
from ninja import Query, Router
from ninja.errors import HttpError

from .models import PodDeploymentConfig, PodDeploymentLog, ProviderLimits
from .schemas import (
    # Activation schemas
    ActivationRequestSchema,
    ActivationResponseSchema,
    ConnectionDetailsSchema,
    # Cost estimation schemas
    CostEstimateRequestSchema,
    CostEstimateResponseSchema,
    CostEstimateSchema,
    # Log schemas
    DeploymentLogSchema,
    DeploymentLogsResponseSchema,
    DeploymentReviewSchema,
    DeploymentStatusSchema,
    # Deployment schemas
    DeployRequestSchema,
    DeployResponseSchema,
    # Lifecycle schemas
    PodActionRequestSchema,
    PodActionResponseSchema,
    # Configuration schemas
    PodConfigCreateSchema,
    PodConfigListResponseSchema,
    PodConfigResponseSchema,
    PodConfigUpdateSchema,
    PodStatusSchema,
    ProviderLimitsListResponseSchema,
    # Provider limits schemas
    ProviderLimitsSchema,
    # Validation schemas
    ValidateConfigRequestSchema,
    ValidateConfigResponseSchema,
)
from .services import (
    activation_service,
    cost_estimator_service,
    deployment_service,
    pod_configuration_service,
    validation_service,
)

logger = logging.getLogger("gpubroker.deployment.api")

router = Router(tags=["deployment"])


def get_user_id(request: HttpRequest) -> UUID:
    """
    Extract user ID from JWT token in request.

    Args:
        request: HTTP request with Authorization header

    Returns:
        User UUID from JWT token

    Raises:
        ValueError: If no valid authentication found
    """
    # Check for user_id set by auth middleware
    user_id = getattr(request, "user_id", None)
    if user_id:
        return UUID(str(user_id))

    # Extract from JWT token in Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            from gpubrokerpod.gpubrokerapp.apps.auth_app.services import (
                verify_jwt_token,
            )

            payload = verify_jwt_token(token)
            return UUID(payload["user_id"])
        except Exception as e:
            logger.error(f"JWT verification failed: {e}")
            raise ValueError("Invalid authentication token")

    # Check for API key authentication
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        try:
            from gpubrokerpod.gpubrokerapp.apps.auth_app.models import User

            user = User.objects.get(api_key=api_key)
            return user.id
        except User.DoesNotExist:
            raise ValueError("Invalid API key")

    raise ValueError("No authentication provided")


def get_user_email(request: HttpRequest) -> str:
    """Extract user email from request."""
    return getattr(request, "user_email", "user@example.com")


def is_sandbox_mode() -> bool:
    """Check if running in sandbox mode."""
    return getattr(settings, "GPUBROKER_MODE", "sandbox") == "sandbox"


# =============================================================================
# POD CONFIGURATION CRUD (Task 15)
# =============================================================================


@router.post("/configs", response=PodConfigResponseSchema)
def create_config(request: HttpRequest, data: PodConfigCreateSchema):
    """
    Create a new pod configuration (draft).

    Requirement 11.6: Save configuration as draft before deployment.
    """
    user_id = get_user_id(request)
    user_email = get_user_email(request)

    try:
        config = pod_configuration_service.create_config(
            user_id=user_id,
            user_email=user_email,
            name=data.name,
            description=data.description,
            gpu_type=data.gpu.gpu_type,
            gpu_count=data.gpu.gpu_count,
            gpu_model=data.gpu.gpu_model or "",
            gpu_memory_gb=data.gpu.gpu_memory_gb or 0,
            provider_selection_mode=data.provider.mode,
            provider=data.provider.provider or "",
            provider_offer_id=data.provider.provider_offer_id or "",
            vcpus=data.resources.vcpus,
            ram_gb=data.resources.ram_gb,
            storage_gb=data.resources.storage_gb,
            storage_type=data.resources.storage_type,
            network_speed_gbps=data.resources.network_speed_gbps,
            public_ip=data.resources.public_ip,
            region=data.region.region,
            availability_zone=data.region.availability_zone or "",
            spot_instance=data.pricing.spot_instance if data.pricing else False,
            max_spot_price=data.pricing.max_spot_price if data.pricing else None,
            tags=data.tags,
            metadata=data.metadata,
        )

        return _config_to_response(config)

    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        raise HttpError(400, str(e))


@router.get("/configs", response=PodConfigListResponseSchema)
def list_configs(
    request: HttpRequest,
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """
    List pod configurations for the current user.
    """
    user_id = get_user_id(request)

    items, total = pod_configuration_service.list_configs(
        user_id=user_id,
        status=status,
        page=page,
        per_page=per_page,
    )

    return PodConfigListResponseSchema(
        total=total, items=[_config_to_response(c) for c in items]
    )


@router.get("/configs/{config_id}", response=PodConfigResponseSchema)
def get_config(request: HttpRequest, config_id: UUID):
    """
    Get a pod configuration by ID.
    """
    user_id = get_user_id(request)

    try:
        config = pod_configuration_service.get_config(config_id, user_id)
        return _config_to_response(config)
    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Configuration not found")


@router.put("/configs/{config_id}", response=PodConfigResponseSchema)
def update_config(request: HttpRequest, config_id: UUID, data: PodConfigUpdateSchema):
    """
    Update a pod configuration.

    Only allowed for DRAFT status.
    """
    user_id = get_user_id(request)

    try:
        updates = {}

        if data.name is not None:
            updates["name"] = data.name
        if data.description is not None:
            updates["description"] = data.description
        if data.gpu is not None:
            updates["gpu_type"] = data.gpu.gpu_type
            updates["gpu_count"] = data.gpu.gpu_count
            if data.gpu.gpu_model:
                updates["gpu_model"] = data.gpu.gpu_model
            if data.gpu.gpu_memory_gb:
                updates["gpu_memory_gb"] = data.gpu.gpu_memory_gb
        if data.provider is not None:
            updates["provider_selection_mode"] = data.provider.mode
            if data.provider.provider:
                updates["provider"] = data.provider.provider
            if data.provider.provider_offer_id:
                updates["provider_offer_id"] = data.provider.provider_offer_id
        if data.resources is not None:
            updates["vcpus"] = data.resources.vcpus
            updates["ram_gb"] = data.resources.ram_gb
            updates["storage_gb"] = data.resources.storage_gb
            updates["storage_type"] = data.resources.storage_type
            updates["network_speed_gbps"] = data.resources.network_speed_gbps
            updates["public_ip"] = data.resources.public_ip
        if data.region is not None:
            updates["region"] = data.region.region
            if data.region.availability_zone:
                updates["availability_zone"] = data.region.availability_zone
        if data.pricing is not None:
            updates["spot_instance"] = data.pricing.spot_instance
            updates["max_spot_price"] = data.pricing.max_spot_price
        if data.tags is not None:
            updates["tags"] = data.tags
        if data.metadata is not None:
            updates["metadata"] = data.metadata

        config = pod_configuration_service.update_config(config_id, user_id, **updates)
        return _config_to_response(config)

    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Configuration not found")
    except ValueError as e:
        raise HttpError(400, str(e))


@router.delete("/configs/{config_id}")
def delete_config(request: HttpRequest, config_id: UUID):
    """
    Delete a pod configuration.

    Only allowed for DRAFT status.
    """
    user_id = get_user_id(request)

    try:
        pod_configuration_service.delete_config(config_id, user_id)
        return {"success": True, "message": "Configuration deleted"}
    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Configuration not found")
    except ValueError as e:
        raise HttpError(400, str(e))


# =============================================================================
# COST ESTIMATION (Task 15.3)
# =============================================================================


@router.post("/estimate", response=CostEstimateResponseSchema)
def estimate_cost(request: HttpRequest, data: CostEstimateRequestSchema):
    """
    Estimate cost for a pod configuration.

    Requirement 11.4: Show estimated cost per hour/day/month.
    """
    if data.provider:
        # Single provider estimate
        estimate = cost_estimator_service.estimate_cost(
            gpu_type=data.gpu_type,
            gpu_count=data.gpu_count,
            provider=data.provider,
            vcpus=data.vcpus,
            ram_gb=data.ram_gb,
            storage_gb=data.storage_gb,
            storage_type=data.storage_type,
            spot_instance=data.spot_instance,
            region=data.region,
        )

        return CostEstimateResponseSchema(
            estimates=[CostEstimateSchema(**estimate)],
            cheapest=CostEstimateSchema(**estimate),
            best_value=CostEstimateSchema(**estimate),
            recommended=data.provider,
        )
    # Multi-provider estimate
    result = cost_estimator_service.estimate_multiple_providers(
        gpu_type=data.gpu_type,
        gpu_count=data.gpu_count,
        vcpus=data.vcpus,
        ram_gb=data.ram_gb,
        storage_gb=data.storage_gb,
        storage_type=data.storage_type,
        spot_instance=data.spot_instance,
        region=data.region,
    )

    return CostEstimateResponseSchema(
        estimates=[CostEstimateSchema(**e) for e in result["estimates"]],
        cheapest=(
            CostEstimateSchema(**result["cheapest"]) if result["cheapest"] else None
        ),
        best_value=(
            CostEstimateSchema(**result["best_value"]) if result["best_value"] else None
        ),
        recommended=result["recommended"],
    )


# =============================================================================
# VALIDATION (Task 15.4)
# =============================================================================


@router.post("/validate", response=ValidateConfigResponseSchema)
def validate_config(request: HttpRequest, data: ValidateConfigRequestSchema):
    """
    Validate a pod configuration against provider limits.

    Requirement 11.5: Validate configuration against provider limits.
    """
    result = validation_service.validate_config(
        gpu_type=data.gpu_type,
        gpu_count=data.gpu_count,
        provider=data.provider,
        vcpus=data.vcpus,
        ram_gb=data.ram_gb,
        storage_gb=data.storage_gb,
        storage_type=data.storage_type,
        region=data.region,
        spot_instance=data.spot_instance,
    )

    return ValidateConfigResponseSchema(**result)


# =============================================================================
# DEPLOYMENT (Task 16)
# =============================================================================


@router.get("/configs/{config_id}/review", response=DeploymentReviewSchema)
def get_deployment_review(request: HttpRequest, config_id: UUID):
    """
    Get deployment review page data.

    Requirements 12.1, 12.2: Show configuration summary and final cost.
    """
    user_id = get_user_id(request)

    try:
        config = pod_configuration_service.get_config(config_id, user_id)

        # Get cost estimate
        cost_estimate = cost_estimator_service.estimate_cost(
            gpu_type=config.gpu_type,
            gpu_count=config.gpu_count,
            provider=config.provider,
            vcpus=config.vcpus,
            ram_gb=config.ram_gb,
            storage_gb=config.storage_gb,
            storage_type=config.storage_type,
            spot_instance=config.spot_instance,
            region=config.region,
        )

        # Get validation
        validation = validation_service.validate_config(
            gpu_type=config.gpu_type,
            gpu_count=config.gpu_count,
            provider=config.provider,
            vcpus=config.vcpus,
            ram_gb=config.ram_gb,
            storage_gb=config.storage_gb,
            storage_type=config.storage_type,
            region=config.region,
            spot_instance=config.spot_instance,
        )

        return DeploymentReviewSchema(
            config=_config_to_response(config),
            cost_estimate=CostEstimateSchema(**cost_estimate),
            validation=ValidateConfigResponseSchema(**validation),
            terms_accepted=False,
            can_deploy=config.can_deploy(),
        )

    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Configuration not found")


@router.post("/deploy", response=DeployResponseSchema)
def deploy(request: HttpRequest, data: DeployRequestSchema):
    """
    Deploy a pod configuration.

    Requirements 12.3-12.8: Deployment flow.
    """
    user_id = get_user_id(request)

    if not data.confirm:
        raise HttpError(400, "Must confirm deployment by setting confirm=true")

    try:
        result = deployment_service.deploy(
            config_id=data.config_id,
            user_id=user_id,
            sandbox_mode=is_sandbox_mode(),
        )

        return DeployResponseSchema(**result)

    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Configuration not found")
    except ValueError as e:
        raise HttpError(400, str(e))


@router.get("/status/{config_id}", response=DeploymentStatusSchema)
def get_deployment_status(request: HttpRequest, config_id: UUID):
    """
    Get deployment status.
    """
    user_id = get_user_id(request)

    try:
        result = deployment_service.get_status(config_id, user_id)
        return DeploymentStatusSchema(**result)
    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Configuration not found")


# =============================================================================
# ACTIVATION (Task 17)
# =============================================================================


@router.post("/activate/{config_id}", response=ActivationResponseSchema)
def activate_pod(request: HttpRequest, config_id: UUID, data: ActivationRequestSchema):
    """
    Activate a pod.

    Requirements 13.1-13.7: Activation flow.
    """
    try:
        result = activation_service.activate(
            config_id=config_id,
            token=data.token,
            sandbox_mode=is_sandbox_mode(),
        )

        return ActivationResponseSchema(**result)

    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Pod not found")
    except ValueError as e:
        raise HttpError(400, str(e))


@router.get("/pods/{config_id}/connection", response=ConnectionDetailsSchema)
def get_connection_details(request: HttpRequest, config_id: UUID):
    """
    Get connection details for a running pod.

    Requirement 13.5: Return connection details.
    """
    user_id = get_user_id(request)

    try:
        details = activation_service.get_connection_details(config_id, user_id)
        return ConnectionDetailsSchema(**details)
    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Pod not found")
    except ValueError as e:
        raise HttpError(400, str(e))


# =============================================================================
# POD LIFECYCLE
# =============================================================================


@router.post("/pods/{config_id}/action", response=PodActionResponseSchema)
def pod_action(request: HttpRequest, config_id: UUID, data: PodActionRequestSchema):
    """
    Perform a lifecycle action on a pod (start, stop, pause, resume, terminate).
    """
    user_id = get_user_id(request)

    try:
        config = PodDeploymentConfig.objects.get(id=config_id, user_id=user_id)
        old_status = config.status

        action_map = {
            "start": (
                PodDeploymentConfig.Status.RUNNING,
                PodDeploymentLog.EventType.STARTED,
            ),
            "stop": (
                PodDeploymentConfig.Status.STOPPED,
                PodDeploymentLog.EventType.STOPPED,
            ),
            "pause": (
                PodDeploymentConfig.Status.PAUSED,
                PodDeploymentLog.EventType.PAUSED,
            ),
            "resume": (
                PodDeploymentConfig.Status.RUNNING,
                PodDeploymentLog.EventType.RESUMED,
            ),
            "terminate": (
                PodDeploymentConfig.Status.TERMINATED,
                PodDeploymentLog.EventType.TERMINATED,
            ),
        }

        if data.action not in action_map:
            raise HttpError(400, f"Invalid action: {data.action}")

        new_status, event_type = action_map[data.action]

        # Validate action is allowed
        if data.action == "terminate" and not config.can_terminate():
            raise HttpError(400, "Cannot terminate pod in current state")
        if data.action == "stop" and not config.can_stop():
            raise HttpError(400, "Cannot stop pod in current state")

        # Update status
        config.status = new_status
        if data.action == "stop":
            config.stopped_at = timezone.now()
        elif data.action == "start":
            config.started_at = timezone.now()
        config.save()

        # Create log
        PodDeploymentLog.objects.create(
            deployment=config,
            event_type=event_type,
            message=f"Pod {data.action}",
            old_status=old_status,
            new_status=new_status,
        )

        return PodActionResponseSchema(
            success=True,
            action=data.action,
            old_status=old_status,
            new_status=new_status,
            message=f"Pod {data.action} successful",
        )

    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Pod not found")


@router.get("/pods/{config_id}/status", response=PodStatusSchema)
def get_pod_status(request: HttpRequest, config_id: UUID):
    """
    Get current pod status.
    """
    user_id = get_user_id(request)

    try:
        config = PodDeploymentConfig.objects.get(id=config_id, user_id=user_id)

        # Calculate runtime
        runtime_hours = 0
        if config.started_at:
            from django.utils import timezone

            end_time = config.stopped_at or timezone.now()
            runtime_hours = (end_time - config.started_at).total_seconds() / 3600

        return PodStatusSchema(
            id=config.id,
            name=config.name,
            status=config.status,
            gpu_type=config.gpu_type,
            provider=config.provider,
            region=config.region,
            started_at=config.started_at,
            runtime_hours=runtime_hours,
            current_cost=float(config.estimated_price_per_hour) * runtime_hours,
            connection_details=(
                ConnectionDetailsSchema(**config.connection_details)
                if config.connection_details
                else None
            ),
        )

    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Pod not found")


# =============================================================================
# DEPLOYMENT LOGS
# =============================================================================


@router.get("/pods/{config_id}/logs", response=DeploymentLogsResponseSchema)
def get_deployment_logs(request: HttpRequest, config_id: UUID):
    """
    Get deployment logs for a pod.
    """
    user_id = get_user_id(request)

    try:
        config = PodDeploymentConfig.objects.get(id=config_id, user_id=user_id)
        logs = PodDeploymentLog.objects.filter(deployment=config).order_by(
            "-created_at"
        )[:100]

        return DeploymentLogsResponseSchema(
            deployment_id=config.id,
            logs=[
                DeploymentLogSchema(
                    id=log.id,
                    event_type=log.event_type,
                    message=log.message,
                    details=log.details,
                    old_status=log.old_status,
                    new_status=log.new_status,
                    created_at=log.created_at,
                )
                for log in logs
            ],
            total=logs.count(),
        )

    except PodDeploymentConfig.DoesNotExist:
        raise HttpError(404, "Pod not found")


# =============================================================================
# PROVIDER LIMITS
# =============================================================================


@router.get("/limits", response=ProviderLimitsListResponseSchema)
def list_provider_limits(
    request: HttpRequest,
    provider: str | None = Query(None, description="Filter by provider"),
    gpu_type: str | None = Query(None, description="Filter by GPU type"),
):
    """
    List provider limits for validation.
    """
    queryset = ProviderLimits.objects.all()

    if provider:
        queryset = queryset.filter(provider=provider)
    if gpu_type:
        queryset = queryset.filter(gpu_type__icontains=gpu_type)

    items = list(queryset)

    return ProviderLimitsListResponseSchema(
        items=[
            ProviderLimitsSchema(
                provider=limit.provider,
                gpu_type=limit.gpu_type,
                min_gpu_count=limit.min_gpu_count,
                max_gpu_count=limit.max_gpu_count,
                min_vcpus=limit.min_vcpus,
                max_vcpus=limit.max_vcpus,
                vcpu_increments=limit.vcpu_increments,
                min_ram_gb=limit.min_ram_gb,
                max_ram_gb=limit.max_ram_gb,
                ram_increments_gb=limit.ram_increments_gb,
                min_storage_gb=limit.min_storage_gb,
                max_storage_gb=limit.max_storage_gb,
                storage_increments_gb=limit.storage_increments_gb,
                supported_storage_types=limit.supported_storage_types,
                regions=limit.regions,
                spot_available=limit.spot_available,
                base_price_per_hour=float(limit.base_price_per_hour),
            )
            for limit in items
        ],
        total=len(items),
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _config_to_response(config: PodDeploymentConfig) -> PodConfigResponseSchema:
    """Convert a PodDeploymentConfig to response schema."""
    return PodConfigResponseSchema(
        id=config.id,
        name=config.name,
        description=config.description,
        status=config.status,
        gpu_type=config.gpu_type,
        gpu_model=config.gpu_model,
        gpu_count=config.gpu_count,
        gpu_memory_gb=config.gpu_memory_gb,
        provider_selection_mode=config.provider_selection_mode,
        provider=config.provider,
        provider_offer_id=config.provider_offer_id,
        vcpus=config.vcpus,
        ram_gb=config.ram_gb,
        storage_gb=config.storage_gb,
        storage_type=config.storage_type,
        network_speed_gbps=float(config.network_speed_gbps),
        public_ip=config.public_ip,
        region=config.region,
        availability_zone=config.availability_zone,
        spot_instance=config.spot_instance,
        max_spot_price=float(config.max_spot_price) if config.max_spot_price else None,
        estimated_price_per_hour=float(config.estimated_price_per_hour),
        estimated_price_per_day=float(config.estimated_price_per_day),
        estimated_price_per_month=float(config.estimated_price_per_month),
        currency=config.currency,
        is_valid=config.is_valid,
        validation_errors=config.validation_errors,
        tags=config.tags,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


# Import timezone at module level


# Import timezone at module level
