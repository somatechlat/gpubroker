"""
POD Configuration Models.

Models for GPUBROKER POD configuration with CRUD operations.
Supports SANDBOX and LIVE modes with parameter inheritance.

Requirements:
- 1.1: Store all configuration in AWS Parameter Store and Secrets Manager
- 1.2: Provide CRUD API endpoints for all POD parameters
- 1.3: Apply changes without restart (hot reload)
- 1.4: Support parameter inheritance (global → pod-specific)
- 1.5: Audit all parameter changes with timestamp and user
- 1.6: Encrypt all sensitive parameters (API keys, secrets)
"""

import json
import logging
import uuid
from decimal import Decimal
from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

logger = logging.getLogger("gpubroker.pod_config")


class PodConfiguration(models.Model):
    """
    GPUBROKER POD Configuration with CRUD operations.

    All settings are parameters - SANDBOX vs LIVE modes.
    Each POD has its own configuration that can be independently managed.

    Requirements: 1.1, 1.2
    """

    class Mode(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox (Testing)"
        LIVE = "live", "Live (Production)"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"
        DELETED = "deleted", "Deleted"

    # Primary identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pod_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique POD identifier (e.g., gpubroker-prod-001)",
    )
    name = models.CharField(max_length=255, help_text="Human-readable POD name")
    description = models.TextField(blank=True, help_text="POD description")

    # Mode and Status
    mode = models.CharField(
        max_length=10,
        choices=Mode.choices,
        default=Mode.SANDBOX,
        db_index=True,
        help_text="Current operating mode",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )

    # AWS Configuration
    aws_region = models.CharField(max_length=20, default="us-east-1")
    aws_account_id = models.CharField(max_length=20, blank=True)

    # Feature Flags
    agent_zero_enabled = models.BooleanField(
        default=False, help_text="Enable Agent Zero agentic layer (ADMIN ONLY)"
    )
    websocket_enabled = models.BooleanField(
        default=True, help_text="Enable WebSocket real-time updates"
    )
    webhooks_enabled = models.BooleanField(
        default=True, help_text="Enable webhook notifications"
    )

    # Rate Limits (per mode)
    rate_limit_free = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
        help_text="Rate limit for free tier (RPS)",
    )
    rate_limit_pro = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
        help_text="Rate limit for pro tier (RPS)",
    )
    rate_limit_enterprise = models.IntegerField(
        default=1000,
        validators=[MinValueValidator(1), MaxValueValidator(100000)],
        help_text="Rate limit for enterprise tier (RPS)",
    )

    # Billing Configuration
    markup_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        validators=[MinValueValidator(Decimal(0)), MaxValueValidator(Decimal(100))],
        help_text="Markup percentage on provider costs",
    )

    # Owner/Admin
    owner_email = models.EmailField(blank=True, help_text="POD owner email")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_mode_switch = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pod_configurations"
        ordering = ["-created_at"]
        verbose_name = "POD Configuration"
        verbose_name_plural = "POD Configurations"

    def __str__(self):
        return f"{self.name} ({self.pod_id}) - {self.mode}"

    def get_rate_limit(self, plan: str) -> int:
        """Get rate limit for a specific plan."""
        limits = {
            "free": self.rate_limit_free,
            "pro": self.rate_limit_pro,
            "enterprise": self.rate_limit_enterprise,
        }
        return limits.get(plan.lower(), self.rate_limit_free)

    def switch_mode(self, new_mode: str, user=None) -> bool:
        """
        Switch POD mode between SANDBOX and LIVE.

        Requirements: 2.1, 2.6, 2.7
        """
        if new_mode not in [self.Mode.SANDBOX, self.Mode.LIVE]:
            return False

        old_mode = self.mode
        self.mode = new_mode
        self.last_mode_switch = timezone.now()
        self.save(update_fields=["mode", "last_mode_switch", "updated_at"])

        # Log the mode switch
        logger.info(
            f"POD {self.pod_id} mode switched from {old_mode} to {new_mode}",
            extra={
                "pod_id": self.pod_id,
                "old_mode": old_mode,
                "new_mode": new_mode,
                "user": str(user) if user else "system",
            },
        )

        return True


class PodParameter(models.Model):
    """
    Individual parameter for a POD with mode-specific values.

    Supports hot-reload without restart and AWS Parameter Store sync.

    Requirements: 1.3, 1.4, 1.6
    """

    class ParameterType(models.TextChoices):
        STRING = "string", "String"
        INTEGER = "integer", "Integer"
        FLOAT = "float", "Float"
        BOOLEAN = "boolean", "Boolean"
        JSON = "json", "JSON"
        SECRET = "secret", "Secret (Encrypted)"

    # Primary identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationship to POD
    pod = models.ForeignKey(
        PodConfiguration, on_delete=models.CASCADE, related_name="parameters"
    )

    # Parameter key (unique per POD)
    key = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Parameter key (e.g., STRIPE_API_KEY, MAX_CONCURRENT_JOBS)",
    )

    # Mode-specific values
    sandbox_value = models.TextField(
        blank=True, null=True, help_text="Value used in SANDBOX mode"
    )
    live_value = models.TextField(
        blank=True, null=True, help_text="Value used in LIVE mode"
    )

    # Parameter metadata
    parameter_type = models.CharField(
        max_length=10, choices=ParameterType.choices, default=ParameterType.STRING
    )
    description = models.TextField(blank=True, help_text="Parameter description")
    is_sensitive = models.BooleanField(
        default=False,
        help_text="If true, value is encrypted and stored in Secrets Manager",
    )
    is_required = models.BooleanField(
        default=False, help_text="If true, parameter must have a value"
    )

    # Default value (used if mode-specific value is not set)
    default_value = models.TextField(
        blank=True,
        null=True,
        help_text="Default value if mode-specific value is not set",
    )

    # AWS Parameter Store ARN (for secrets)
    aws_parameter_arn = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="AWS Parameter Store/Secrets Manager ARN",
    )

    # Validation
    validation_regex = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Regex pattern for value validation",
    )
    min_value = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Minimum value (for numeric types)",
    )
    max_value = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Maximum value (for numeric types)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pod_parameters"
        unique_together = ["pod", "key"]
        ordering = ["key"]
        verbose_name = "POD Parameter"
        verbose_name_plural = "POD Parameters"

    def __str__(self):
        return f"{self.pod.pod_id}:{self.key}"

    def get_value(self, mode: str = None) -> str | None:
        """
        Get parameter value for the specified mode.

        Falls back to: mode_value → default_value → None
        """
        if mode is None:
            mode = self.pod.mode

        if mode == PodConfiguration.Mode.SANDBOX:
            value = self.sandbox_value
        else:
            value = self.live_value

        if value is None or value == "":
            value = self.default_value

        return value

    def get_typed_value(self, mode: str = None) -> Any:
        """
        Get parameter value converted to its declared type.
        """
        value = self.get_value(mode)

        if value is None:
            return None

        try:
            if self.parameter_type == self.ParameterType.INTEGER:
                return int(value)
            if self.parameter_type == self.ParameterType.FLOAT:
                return float(value)
            if self.parameter_type == self.ParameterType.BOOLEAN:
                return value.lower() in ("true", "1", "yes", "on")
            if self.parameter_type == self.ParameterType.JSON:
                return json.loads(value)
            return value
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to convert parameter {self.key}: {e}")
            return value

    def set_value(self, value: Any, mode: str, user=None, reason: str = "") -> bool:
        """
        Set parameter value for the specified mode with audit logging.

        Requirements: 1.5
        """
        # Convert value to string for storage
        if isinstance(value, bool):
            str_value = "true" if value else "false"
        elif isinstance(value, (dict, list)):
            str_value = json.dumps(value)
        else:
            str_value = str(value)

        # Get old value for audit
        old_value = self.get_value(mode)

        # Update the appropriate field
        if mode == PodConfiguration.Mode.SANDBOX:
            self.sandbox_value = str_value
        else:
            self.live_value = str_value

        self.save(
            update_fields=[
                (
                    "sandbox_value"
                    if mode == PodConfiguration.Mode.SANDBOX
                    else "live_value"
                ),
                "updated_at",
            ]
        )

        # Create audit log
        ParameterAuditLog.objects.create(
            parameter=self,
            changed_by_id=user.id if user and hasattr(user, "id") else None,
            old_value=old_value,
            new_value=str_value,
            mode_affected=mode,
            change_reason=reason,
        )

        logger.info(
            f"Parameter {self.key} updated for POD {self.pod.pod_id}",
            extra={
                "pod_id": self.pod.pod_id,
                "key": self.key,
                "mode": mode,
                "user": str(user) if user else "system",
            },
        )

        return True


class ParameterAuditLog(models.Model):
    """
    Audit log for all parameter changes.

    Tracks who changed what, when, and why.

    Requirements: 1.5
    """

    # Primary identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationship to parameter (nullable for mode switches)
    parameter = models.ForeignKey(
        PodParameter,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )

    # For mode switches without specific parameter
    pod = models.ForeignKey(
        PodConfiguration,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )

    # Who made the change
    changed_by_id = models.UUIDField(null=True, blank=True)
    changed_by_email = models.EmailField(blank=True)

    # What changed
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    mode_affected = models.CharField(max_length=10, help_text="sandbox, live, or both")

    # Why it changed
    change_reason = models.TextField(blank=True)
    change_type = models.CharField(
        max_length=20, default="update", help_text="create, update, delete, mode_switch"
    )

    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "parameter_audit_logs"
        ordering = ["-created_at"]
        verbose_name = "Parameter Audit Log"
        verbose_name_plural = "Parameter Audit Logs"
        indexes = [
            models.Index(fields=["parameter", "-created_at"]),
            models.Index(fields=["pod", "-created_at"]),
            models.Index(fields=["changed_by_id", "-created_at"]),
        ]

    def __str__(self):
        if self.parameter:
            return f"{self.parameter.key} changed at {self.created_at}"
        if self.pod:
            return f"POD {self.pod.pod_id} {self.change_type} at {self.created_at}"
        return f"Audit log {self.id}"
