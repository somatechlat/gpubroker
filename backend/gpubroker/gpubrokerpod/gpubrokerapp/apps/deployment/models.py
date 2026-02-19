"""
Deployment Models.

Models for GPU pod configuration, deployment, and lifecycle management.

Requirements:
- 11.1: Allow selection of GPU type
- 11.2: Allow selection of provider (or auto-select best)
- 11.3: Allow configuration of vCPUs, RAM, storage
- 11.4: Show estimated cost per hour/day/month
- 11.5: Validate configuration against provider limits
- 11.6: Save configuration as draft before deployment
- 12.1-12.8: Deployment flow
- 13.1-13.7: Activation flow
"""

import logging
import secrets
import uuid
from decimal import Decimal
from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

logger = logging.getLogger("gpubroker.deployment")


class PodDeploymentConfig(models.Model):
    """
    GPU Pod deployment configuration.

    Stores user's pod configuration before and after deployment.
    Supports draft saving (Requirement 11.6).
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft (Not Deployed)"
        PENDING = "pending", "Pending Deployment"
        PROVISIONING = "provisioning", "Provisioning"
        READY = "ready", "Ready (Awaiting Activation)"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        STOPPING = "stopping", "Stopping"
        STOPPED = "stopped", "Stopped"
        TERMINATING = "terminating", "Terminating"
        TERMINATED = "terminated", "Terminated"
        FAILED = "failed", "Failed"
        ERROR = "error", "Error"

    class ProviderSelectionMode(models.TextChoices):
        MANUAL = "manual", "Manual Selection"
        AUTO_CHEAPEST = "auto_cheapest", "Auto - Cheapest"
        AUTO_BEST_VALUE = "auto_best_value", "Auto - Best Value (TOPSIS)"
        AUTO_FASTEST = "auto_fastest", "Auto - Fastest Available"

    # Primary identifier
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User reference (UUID from auth system)
    user_id = models.UUIDField(db_index=True, help_text="User who created this config")
    user_email = models.EmailField(blank=True, help_text="User email for notifications")

    # Pod identification
    name = models.CharField(max_length=100, help_text="User-defined pod name")
    description = models.TextField(blank=True, help_text="Pod description")

    # Status
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )

    # GPU Selection (Requirement 11.1)
    gpu_type = models.CharField(
        max_length=100, help_text="GPU type (e.g., RTX 4090, A100 80GB, H100)"
    )
    gpu_model = models.CharField(
        max_length=100, blank=True, help_text="Specific GPU model"
    )
    gpu_count = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        help_text="Number of GPUs",
    )
    gpu_memory_gb = models.PositiveIntegerField(default=0, help_text="GPU memory in GB")

    # Provider Selection (Requirement 11.2)
    provider_selection_mode = models.CharField(
        max_length=20,
        choices=ProviderSelectionMode.choices,
        default=ProviderSelectionMode.MANUAL,
    )
    provider = models.CharField(
        max_length=50, blank=True, help_text="Selected provider (if manual)"
    )
    provider_offer_id = models.CharField(
        max_length=255, blank=True, help_text="Provider's offer ID"
    )

    # Resource Configuration (Requirement 11.3)
    vcpus = models.PositiveIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(256)],
        help_text="Number of vCPUs",
    )
    ram_gb = models.PositiveIntegerField(
        default=16,
        validators=[MinValueValidator(1), MaxValueValidator(2048)],
        help_text="RAM in GB",
    )
    storage_gb = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(10), MaxValueValidator(10000)],
        help_text="Storage in GB",
    )
    storage_type = models.CharField(
        max_length=20,
        default="ssd",
        choices=[
            ("ssd", "SSD"),
            ("nvme", "NVMe SSD"),
            ("hdd", "HDD"),
        ],
    )

    # Network Configuration
    network_speed_gbps = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.0"),
        help_text="Network speed in Gbps",
    )
    public_ip = models.BooleanField(default=True, help_text="Assign public IP")

    # Region Configuration
    region = models.CharField(
        max_length=50, default="us-east-1", help_text="Deployment region"
    )
    availability_zone = models.CharField(
        max_length=50, blank=True, help_text="Specific availability zone"
    )

    # Pricing Options
    spot_instance = models.BooleanField(
        default=False, help_text="Use spot/preemptible instance"
    )
    max_spot_price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Maximum spot price per hour",
    )

    # Cost Estimates (Requirement 11.4)
    estimated_price_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal(0),
        help_text="Estimated cost per hour",
    )
    estimated_price_per_day = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal(0),
        help_text="Estimated cost per day",
    )
    estimated_price_per_month = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal(0),
        help_text="Estimated cost per month (30 days)",
    )
    currency = models.CharField(max_length=3, default="USD")

    # Provider Limits (Requirement 11.5)
    provider_limits = models.JSONField(
        default=dict, blank=True, help_text="Provider-specific limits for validation"
    )
    validation_errors = models.JSONField(
        default=list, blank=True, help_text="Validation errors if any"
    )
    is_valid = models.BooleanField(
        default=False, help_text="Configuration passes validation"
    )

    # Deployment Details
    deployment_id = models.CharField(
        max_length=255, blank=True, help_text="Provider's deployment/instance ID"
    )
    deployment_started_at = models.DateTimeField(null=True, blank=True)
    deployment_completed_at = models.DateTimeField(null=True, blank=True)

    # Activation (Requirement 13)
    activation_token = models.CharField(
        max_length=64, blank=True, help_text="Secure token for activation"
    )
    activation_token_expires_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    # Connection Details (Requirement 13.5)
    connection_details = models.JSONField(
        default=dict, blank=True, help_text="SSH, Jupyter, etc. connection info"
    )

    # Runtime Info
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    total_runtime_hours = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal(0)
    )
    total_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal(0)
    )

    # Metadata
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pod_deployment_configs"
        ordering = ["-created_at"]
        verbose_name = "Pod Deployment Config"
        verbose_name_plural = "Pod Deployment Configs"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["provider", "status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.gpu_type}) - {self.status}"

    def save(self, *args, **kwargs):
        """Override save to calculate cost estimates."""
        self._calculate_cost_estimates()
        super().save(*args, **kwargs)

    def _calculate_cost_estimates(self):
        """Calculate cost estimates based on hourly rate."""
        if self.estimated_price_per_hour > 0:
            self.estimated_price_per_day = self.estimated_price_per_hour * 24
            self.estimated_price_per_month = self.estimated_price_per_hour * 24 * 30

    def generate_activation_token(self) -> str:
        """Generate a secure activation token."""
        self.activation_token = secrets.token_urlsafe(48)
        self.activation_token_expires_at = timezone.now() + timezone.timedelta(hours=24)
        self.save(update_fields=["activation_token", "activation_token_expires_at"])
        return self.activation_token

    def verify_activation_token(self, token: str) -> bool:
        """Verify the activation token."""
        if not self.activation_token or not self.activation_token_expires_at:
            return False
        if self.activation_token != token:
            return False
        if timezone.now() > self.activation_token_expires_at:
            return False
        return True

    def can_deploy(self) -> bool:
        """Check if configuration can be deployed."""
        return self.status == self.Status.DRAFT and self.is_valid

    def can_activate(self) -> bool:
        """Check if pod can be activated."""
        return self.status == self.Status.READY

    def can_stop(self) -> bool:
        """Check if pod can be stopped."""
        return self.status in [self.Status.RUNNING, self.Status.PAUSED]

    def can_terminate(self) -> bool:
        """Check if pod can be terminated."""
        return self.status not in [
            self.Status.TERMINATED,
            self.Status.TERMINATING,
            self.Status.DRAFT,
        ]


class PodDeploymentLog(models.Model):
    """
    Log of deployment events and status changes.
    """

    class EventType(models.TextChoices):
        CREATED = "created", "Configuration Created"
        UPDATED = "updated", "Configuration Updated"
        VALIDATED = "validated", "Configuration Validated"
        VALIDATION_FAILED = "validation_failed", "Validation Failed"
        DEPLOYMENT_STARTED = "deployment_started", "Deployment Started"
        PROVISIONING = "provisioning", "Provisioning"
        PROVISIONING_PROGRESS = "provisioning_progress", "Provisioning Progress"
        PROVISIONING_COMPLETE = "provisioning_complete", "Provisioning Complete"
        PROVISIONING_FAILED = "provisioning_failed", "Provisioning Failed"
        ACTIVATION_EMAIL_SENT = "activation_email_sent", "Activation Email Sent"
        ACTIVATED = "activated", "Pod Activated"
        STARTED = "started", "Pod Started"
        PAUSED = "paused", "Pod Paused"
        RESUMED = "resumed", "Pod Resumed"
        STOPPED = "stopped", "Pod Stopped"
        TERMINATED = "terminated", "Pod Terminated"
        ERROR = "error", "Error"
        COST_UPDATE = "cost_update", "Cost Updated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    deployment = models.ForeignKey(
        PodDeploymentConfig, on_delete=models.CASCADE, related_name="logs"
    )

    event_type = models.CharField(max_length=30, choices=EventType.choices)

    message = models.TextField(help_text="Human-readable event message")

    details = models.JSONField(
        default=dict, blank=True, help_text="Additional event details"
    )

    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "pod_deployment_logs"
        ordering = ["-created_at"]
        verbose_name = "Pod Deployment Log"
        verbose_name_plural = "Pod Deployment Logs"

    def __str__(self):
        return f"{self.deployment.name}: {self.event_type} at {self.created_at}"


class ProviderLimits(models.Model):
    """
    Provider-specific resource limits for validation.

    Requirement 11.5: Validate configuration against provider limits.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    provider = models.CharField(max_length=50, db_index=True)
    gpu_type = models.CharField(max_length=100, db_index=True)

    # GPU limits
    min_gpu_count = models.PositiveIntegerField(default=1)
    max_gpu_count = models.PositiveIntegerField(default=8)

    # CPU limits
    min_vcpus = models.PositiveIntegerField(default=1)
    max_vcpus = models.PositiveIntegerField(default=256)
    vcpu_increments = models.PositiveIntegerField(default=1)

    # RAM limits
    min_ram_gb = models.PositiveIntegerField(default=1)
    max_ram_gb = models.PositiveIntegerField(default=2048)
    ram_increments_gb = models.PositiveIntegerField(default=1)

    # Storage limits
    min_storage_gb = models.PositiveIntegerField(default=10)
    max_storage_gb = models.PositiveIntegerField(default=10000)
    storage_increments_gb = models.PositiveIntegerField(default=10)
    supported_storage_types = models.JSONField(
        default=list, help_text="List of supported storage types"
    )

    # Rental limits
    min_rental_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("1.0")
    )
    max_rental_hours = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Pricing
    base_price_per_hour = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal(0)
    )
    cpu_price_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal(0),
        help_text="Additional cost per vCPU per hour",
    )
    ram_price_per_gb_hour = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal(0),
        help_text="Additional cost per GB RAM per hour",
    )
    storage_price_per_gb_hour = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=Decimal(0),
        help_text="Additional cost per GB storage per hour",
    )

    # Availability
    regions = models.JSONField(default=list, help_text="Available regions for this GPU")
    spot_available = models.BooleanField(default=False)

    # Metadata
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "provider_limits"
        unique_together = ["provider", "gpu_type"]
        verbose_name = "Provider Limits"
        verbose_name_plural = "Provider Limits"

    def __str__(self):
        return f"{self.provider}: {self.gpu_type}"

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, list]:
        """
        Validate a configuration against these limits.

        Returns (is_valid, list_of_errors).
        """
        errors = []

        # Validate GPU count
        gpu_count = config.get("gpu_count", 1)
        if gpu_count < self.min_gpu_count:
            errors.append(f"GPU count must be at least {self.min_gpu_count}")
        if gpu_count > self.max_gpu_count:
            errors.append(f"GPU count cannot exceed {self.max_gpu_count}")

        # Validate vCPUs
        vcpus = config.get("vcpus", 4)
        if vcpus < self.min_vcpus:
            errors.append(f"vCPUs must be at least {self.min_vcpus}")
        if vcpus > self.max_vcpus:
            errors.append(f"vCPUs cannot exceed {self.max_vcpus}")
        if self.vcpu_increments > 1 and vcpus % self.vcpu_increments != 0:
            errors.append(f"vCPUs must be in increments of {self.vcpu_increments}")

        # Validate RAM
        ram_gb = config.get("ram_gb", 16)
        if ram_gb < self.min_ram_gb:
            errors.append(f"RAM must be at least {self.min_ram_gb} GB")
        if ram_gb > self.max_ram_gb:
            errors.append(f"RAM cannot exceed {self.max_ram_gb} GB")
        if self.ram_increments_gb > 1 and ram_gb % self.ram_increments_gb != 0:
            errors.append(f"RAM must be in increments of {self.ram_increments_gb} GB")

        # Validate storage
        storage_gb = config.get("storage_gb", 100)
        if storage_gb < self.min_storage_gb:
            errors.append(f"Storage must be at least {self.min_storage_gb} GB")
        if storage_gb > self.max_storage_gb:
            errors.append(f"Storage cannot exceed {self.max_storage_gb} GB")

        # Validate storage type
        storage_type = config.get("storage_type", "ssd")
        if (
            self.supported_storage_types
            and storage_type not in self.supported_storage_types
        ):
            errors.append(
                f"Storage type '{storage_type}' not supported. Available: {self.supported_storage_types}"
            )

        # Validate region
        region = config.get("region", "")
        if self.regions and region and region not in self.regions:
            errors.append(f"Region '{region}' not available. Available: {self.regions}")

        # Validate spot pricing
        if config.get("spot_instance") and not self.spot_available:
            errors.append("Spot instances not available for this GPU type")

        return len(errors) == 0, errors

    def calculate_price(self, config: dict[str, Any]) -> Decimal:
        """
        Calculate estimated price per hour for a configuration.
        """
        gpu_count = config.get("gpu_count", 1)
        vcpus = config.get("vcpus", 4)
        ram_gb = config.get("ram_gb", 16)
        storage_gb = config.get("storage_gb", 100)

        price = self.base_price_per_hour * gpu_count
        price += self.cpu_price_per_hour * vcpus
        price += self.ram_price_per_gb_hour * ram_gb
        price += self.storage_price_per_gb_hour * storage_gb

        return price
