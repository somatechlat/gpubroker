"""
Deployment API Schemas.

Pydantic/Ninja schemas for pod configuration and deployment.

Requirements:
- 11.1-11.6: Configure Pod
- 12.1-12.8: Deployment
- 13.1-13.7: Activation
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from ninja import Schema


# =============================================================================
# POD CONFIGURATION SCHEMAS (Task 15)
# =============================================================================

class GPUSelectionSchema(Schema):
    """Schema for GPU selection (Requirement 11.1)."""
    gpu_type: str
    gpu_model: Optional[str] = None
    gpu_count: int = 1
    gpu_memory_gb: Optional[int] = None


class ProviderSelectionSchema(Schema):
    """Schema for provider selection (Requirement 11.2)."""
    mode: str = "manual"  # manual, auto_cheapest, auto_best_value, auto_fastest
    provider: Optional[str] = None
    provider_offer_id: Optional[str] = None


class ResourceConfigSchema(Schema):
    """Schema for resource configuration (Requirement 11.3)."""
    vcpus: int = 4
    ram_gb: int = 16
    storage_gb: int = 100
    storage_type: str = "ssd"
    network_speed_gbps: float = 1.0
    public_ip: bool = True


class RegionConfigSchema(Schema):
    """Schema for region configuration."""
    region: str = "us-east-1"
    availability_zone: Optional[str] = None


class PricingOptionsSchema(Schema):
    """Schema for pricing options."""
    spot_instance: bool = False
    max_spot_price: Optional[float] = None


class PodConfigCreateSchema(Schema):
    """Schema for creating a new pod configuration."""
    name: str
    description: str = ""
    gpu: GPUSelectionSchema
    provider: ProviderSelectionSchema
    resources: ResourceConfigSchema
    region: RegionConfigSchema
    pricing: Optional[PricingOptionsSchema] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class PodConfigUpdateSchema(Schema):
    """Schema for updating a pod configuration."""
    name: Optional[str] = None
    description: Optional[str] = None
    gpu: Optional[GPUSelectionSchema] = None
    provider: Optional[ProviderSelectionSchema] = None
    resources: Optional[ResourceConfigSchema] = None
    region: Optional[RegionConfigSchema] = None
    pricing: Optional[PricingOptionsSchema] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CostEstimateSchema(Schema):
    """Schema for cost estimates (Requirement 11.4)."""
    price_per_hour: float
    price_per_day: float
    price_per_month: float
    currency: str = "USD"
    breakdown: Dict[str, float] = {}  # {gpu: X, cpu: Y, ram: Z, storage: W}
    spot_savings: Optional[float] = None


class ValidationResultSchema(Schema):
    """Schema for validation results (Requirement 11.5)."""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    provider_limits: Dict[str, Any] = {}


class PodConfigResponseSchema(Schema):
    """Schema for pod configuration response."""
    id: UUID
    name: str
    description: str
    status: str
    
    # GPU
    gpu_type: str
    gpu_model: str
    gpu_count: int
    gpu_memory_gb: int
    
    # Provider
    provider_selection_mode: str
    provider: str
    provider_offer_id: str
    
    # Resources
    vcpus: int
    ram_gb: int
    storage_gb: int
    storage_type: str
    network_speed_gbps: float
    public_ip: bool
    
    # Region
    region: str
    availability_zone: str
    
    # Pricing
    spot_instance: bool
    max_spot_price: Optional[float] = None
    
    # Cost Estimates
    estimated_price_per_hour: float
    estimated_price_per_day: float
    estimated_price_per_month: float
    currency: str
    
    # Validation
    is_valid: bool
    validation_errors: List[str] = []
    
    # Metadata
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime


class PodConfigListResponseSchema(Schema):
    """Schema for listing pod configurations."""
    total: int
    items: List[PodConfigResponseSchema]


class PodConfigSummarySchema(Schema):
    """Schema for pod configuration summary (for lists)."""
    id: UUID
    name: str
    status: str
    gpu_type: str
    gpu_count: int
    provider: str
    region: str
    estimated_price_per_hour: float
    is_valid: bool
    created_at: datetime


# =============================================================================
# COST ESTIMATOR SCHEMAS (Task 15.3)
# =============================================================================

class CostEstimateRequestSchema(Schema):
    """Request schema for cost estimation."""
    gpu_type: str
    gpu_count: int = 1
    provider: Optional[str] = None
    vcpus: int = 4
    ram_gb: int = 16
    storage_gb: int = 100
    storage_type: str = "ssd"
    spot_instance: bool = False
    region: Optional[str] = None


class CostEstimateResponseSchema(Schema):
    """Response schema for cost estimation."""
    estimates: List[CostEstimateSchema]  # Multiple providers if auto-select
    cheapest: Optional[CostEstimateSchema] = None
    best_value: Optional[CostEstimateSchema] = None
    recommended: Optional[str] = None  # Provider name


# =============================================================================
# VALIDATION SCHEMAS (Task 15.4)
# =============================================================================

class ValidateConfigRequestSchema(Schema):
    """Request schema for configuration validation."""
    gpu_type: str
    gpu_count: int = 1
    provider: str
    vcpus: int = 4
    ram_gb: int = 16
    storage_gb: int = 100
    storage_type: str = "ssd"
    region: str = "us-east-1"
    spot_instance: bool = False


class ValidateConfigResponseSchema(Schema):
    """Response schema for configuration validation."""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    provider_limits: Dict[str, Any] = {}
    suggested_adjustments: Dict[str, Any] = {}


# =============================================================================
# DEPLOYMENT SCHEMAS (Task 16)
# =============================================================================

class DeployRequestSchema(Schema):
    """Request schema for deployment."""
    config_id: UUID
    confirm: bool = False  # Must be True to deploy


class DeployResponseSchema(Schema):
    """Response schema for deployment."""
    success: bool
    deployment_id: str
    status: str
    message: str
    estimated_time_minutes: int = 5


class DeploymentStatusSchema(Schema):
    """Schema for deployment status."""
    id: UUID
    name: str
    status: str
    progress_percent: int = 0
    current_step: str = ""
    steps_completed: List[str] = []
    steps_remaining: List[str] = []
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None


class DeploymentReviewSchema(Schema):
    """Schema for deployment review page (Requirement 12.1, 12.2)."""
    config: PodConfigResponseSchema
    cost_estimate: CostEstimateSchema
    validation: ValidationResultSchema
    terms_accepted: bool = False
    can_deploy: bool = False


# =============================================================================
# ACTIVATION SCHEMAS (Task 17)
# =============================================================================

class ActivationRequestSchema(Schema):
    """Request schema for pod activation."""
    token: str


class ActivationResponseSchema(Schema):
    """Response schema for pod activation."""
    success: bool
    status: str
    message: str
    connection_details: Optional[Dict[str, Any]] = None


class ConnectionDetailsSchema(Schema):
    """Schema for connection details (Requirement 13.5)."""
    ssh_host: Optional[str] = None
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_key_url: Optional[str] = None
    jupyter_url: Optional[str] = None
    jupyter_token: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    web_terminal_url: Optional[str] = None
    additional: Dict[str, Any] = {}


# =============================================================================
# POD LIFECYCLE SCHEMAS
# =============================================================================

class PodActionRequestSchema(Schema):
    """Request schema for pod actions (start, stop, pause, resume, terminate)."""
    action: str  # start, stop, pause, resume, terminate
    force: bool = False


class PodActionResponseSchema(Schema):
    """Response schema for pod actions."""
    success: bool
    action: str
    old_status: str
    new_status: str
    message: str


class PodStatusSchema(Schema):
    """Schema for pod status."""
    id: UUID
    name: str
    status: str
    gpu_type: str
    provider: str
    region: str
    started_at: Optional[datetime] = None
    runtime_hours: float = 0
    current_cost: float = 0
    connection_details: Optional[ConnectionDetailsSchema] = None


# =============================================================================
# DEPLOYMENT LOG SCHEMAS
# =============================================================================

class DeploymentLogSchema(Schema):
    """Schema for deployment log entry."""
    id: UUID
    event_type: str
    message: str
    details: Dict[str, Any] = {}
    old_status: str
    new_status: str
    created_at: datetime


class DeploymentLogsResponseSchema(Schema):
    """Response schema for deployment logs."""
    deployment_id: UUID
    logs: List[DeploymentLogSchema]
    total: int


# =============================================================================
# PROVIDER LIMITS SCHEMAS
# =============================================================================

class ProviderLimitsSchema(Schema):
    """Schema for provider limits."""
    provider: str
    gpu_type: str
    min_gpu_count: int
    max_gpu_count: int
    min_vcpus: int
    max_vcpus: int
    vcpu_increments: int
    min_ram_gb: int
    max_ram_gb: int
    ram_increments_gb: int
    min_storage_gb: int
    max_storage_gb: int
    storage_increments_gb: int
    supported_storage_types: List[str]
    regions: List[str]
    spot_available: bool
    base_price_per_hour: float


class ProviderLimitsListResponseSchema(Schema):
    """Response schema for listing provider limits."""
    items: List[ProviderLimitsSchema]
    total: int
