"""
POD Configuration API Schemas.

Pydantic/Ninja schemas for request/response validation.
"""
from typing import Optional, List, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ninja import Schema


# =============================================================================
# POD CONFIGURATION SCHEMAS
# =============================================================================

class PodConfigCreateSchema(Schema):
    """Schema for creating a new POD configuration."""
    pod_id: str
    name: str
    description: str = ""
    mode: str = "sandbox"
    aws_region: str = "us-east-1"
    aws_account_id: str = ""
    agent_zero_enabled: bool = False
    websocket_enabled: bool = True
    webhooks_enabled: bool = True
    rate_limit_free: int = 10
    rate_limit_pro: int = 100
    rate_limit_enterprise: int = 1000
    markup_percentage: float = 10.0
    owner_email: str = ""


class PodConfigUpdateSchema(Schema):
    """Schema for updating a POD configuration."""
    name: Optional[str] = None
    description: Optional[str] = None
    aws_region: Optional[str] = None
    aws_account_id: Optional[str] = None
    agent_zero_enabled: Optional[bool] = None
    websocket_enabled: Optional[bool] = None
    webhooks_enabled: Optional[bool] = None
    rate_limit_free: Optional[int] = None
    rate_limit_pro: Optional[int] = None
    rate_limit_enterprise: Optional[int] = None
    markup_percentage: Optional[float] = None
    owner_email: Optional[str] = None


class PodConfigResponseSchema(Schema):
    """Schema for POD configuration response."""
    id: UUID
    pod_id: str
    name: str
    description: str
    mode: str
    status: str
    aws_region: str
    aws_account_id: str
    agent_zero_enabled: bool
    websocket_enabled: bool
    webhooks_enabled: bool
    rate_limit_free: int
    rate_limit_pro: int
    rate_limit_enterprise: int
    markup_percentage: float
    owner_email: str
    created_at: datetime
    updated_at: datetime
    last_mode_switch: Optional[datetime] = None


class PodConfigListResponseSchema(Schema):
    """Schema for listing POD configurations."""
    total: int
    items: List[PodConfigResponseSchema]


# =============================================================================
# POD PARAMETER SCHEMAS
# =============================================================================

class ParameterCreateSchema(Schema):
    """Schema for creating a new parameter."""
    key: str
    sandbox_value: Optional[str] = None
    live_value: Optional[str] = None
    default_value: Optional[str] = None
    parameter_type: str = "string"
    description: str = ""
    is_sensitive: bool = False
    is_required: bool = False
    validation_regex: Optional[str] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None


class ParameterUpdateSchema(Schema):
    """Schema for updating a parameter."""
    sandbox_value: Optional[str] = None
    live_value: Optional[str] = None
    default_value: Optional[str] = None
    description: Optional[str] = None
    is_sensitive: Optional[bool] = None
    is_required: Optional[bool] = None
    validation_regex: Optional[str] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    change_reason: str = ""


class ParameterResponseSchema(Schema):
    """Schema for parameter response."""
    id: UUID
    key: str
    sandbox_value: Optional[str] = None
    live_value: Optional[str] = None
    default_value: Optional[str] = None
    parameter_type: str
    description: str
    is_sensitive: bool
    is_required: bool
    validation_regex: Optional[str] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    aws_parameter_arn: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    @staticmethod
    def resolve_sandbox_value(obj):
        """Mask sensitive values."""
        if obj.is_sensitive and obj.sandbox_value:
            return "********"
        return obj.sandbox_value
    
    @staticmethod
    def resolve_live_value(obj):
        """Mask sensitive values."""
        if obj.is_sensitive and obj.live_value:
            return "********"
        return obj.live_value


class ParameterListResponseSchema(Schema):
    """Schema for listing parameters."""
    total: int
    items: List[ParameterResponseSchema]


# =============================================================================
# MODE SWITCHING SCHEMAS
# =============================================================================

class ModeSwitchSchema(Schema):
    """Schema for mode switching request."""
    mode: str
    confirmation: str
    reason: str = ""


class ModeSwitchResponseSchema(Schema):
    """Schema for mode switching response."""
    success: bool
    pod_id: str
    old_mode: str
    new_mode: str
    message: str


# =============================================================================
# AUDIT LOG SCHEMAS
# =============================================================================

class AuditLogResponseSchema(Schema):
    """Schema for audit log response."""
    id: UUID
    parameter_key: Optional[str] = None
    pod_id: Optional[str] = None
    changed_by_email: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    mode_affected: str
    change_reason: str
    change_type: str
    ip_address: Optional[str] = None
    created_at: datetime
    
    @staticmethod
    def resolve_parameter_key(obj):
        """Get parameter key if available."""
        return obj.parameter.key if obj.parameter else None
    
    @staticmethod
    def resolve_pod_id(obj):
        """Get pod_id from parameter or direct reference."""
        if obj.parameter:
            return obj.parameter.pod.pod_id
        elif obj.pod:
            return obj.pod.pod_id
        return None


class AuditLogListResponseSchema(Schema):
    """Schema for listing audit logs."""
    total: int
    items: List[AuditLogResponseSchema]


# =============================================================================
# BULK OPERATIONS SCHEMAS
# =============================================================================

class BulkParameterSchema(Schema):
    """Schema for bulk parameter import/export."""
    key: str
    sandbox_value: Optional[str] = None
    live_value: Optional[str] = None
    default_value: Optional[str] = None
    parameter_type: str = "string"
    description: str = ""
    is_sensitive: bool = False
    is_required: bool = False


class BulkImportSchema(Schema):
    """Schema for bulk parameter import."""
    parameters: List[BulkParameterSchema]
    overwrite_existing: bool = False


class BulkExportResponseSchema(Schema):
    """Schema for bulk parameter export."""
    pod_id: str
    mode: str
    exported_at: datetime
    parameters: List[BulkParameterSchema]
