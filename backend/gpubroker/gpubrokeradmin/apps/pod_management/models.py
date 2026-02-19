"""
Pod Management Models - GPUBROKERADMIN Control Plane.

Manages POD deployments, configurations, and lifecycle.
"""
from django.db import models
from django.conf import settings
import uuid


class Pod(models.Model):
    """
    Represents a deployed GPUBROKERPOD instance.
    
    Each POD is an isolated tenant environment with its own:
    - Configuration parameters
    - User base
    - Provider connections
    - Billing settings
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Deployment'
        DEPLOYING = 'deploying', 'Deploying'
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        TERMINATING = 'terminating', 'Terminating'
        TERMINATED = 'terminated', 'Terminated'
        ERROR = 'error', 'Error'
    
    class Mode(models.TextChoices):
        SANDBOX = 'sandbox', 'Sandbox (Testing)'
        LIVE = 'live', 'Live (Production)'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Deployment configuration
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.SANDBOX)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # AWS deployment info
    aws_region = models.CharField(max_length=50, default='us-east-1')
    aws_stack_id = models.CharField(max_length=255, blank=True, null=True)
    api_gateway_url = models.URLField(blank=True, null=True)
    
    # Owner and billing
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_pods'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deployed_at = models.DateTimeField(blank=True, null=True)
    terminated_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'admin_pods'
        verbose_name = 'POD'
        verbose_name_plural = 'PODs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.mode})"


class PodConfiguration(models.Model):
    """
    Configuration parameters for a POD.
    
    All settings are stored as key-value pairs with CRUD operations.
    Supports SANDBOX vs LIVE mode-specific configurations.
    """
    
    class Category(models.TextChoices):
        GENERAL = 'general', 'General Settings'
        PROVIDERS = 'providers', 'Provider Settings'
        BILLING = 'billing', 'Billing Settings'
        SECURITY = 'security', 'Security Settings'
        LIMITS = 'limits', 'Rate Limits & Quotas'
        FEATURES = 'features', 'Feature Flags'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pod = models.ForeignKey(Pod, on_delete=models.CASCADE, related_name='configurations')
    
    category = models.CharField(max_length=50, choices=Category.choices)
    key = models.CharField(max_length=100)
    value = models.JSONField()
    
    # Mode-specific: null means applies to both modes
    mode = models.CharField(max_length=20, choices=Pod.Mode.choices, blank=True, null=True)
    
    # Metadata
    description = models.TextField(blank=True)
    is_secret = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admin_pod_configurations'
        unique_together = [['pod', 'key', 'mode']]
        verbose_name = 'POD Configuration'
        verbose_name_plural = 'POD Configurations'
    
    def __str__(self):
        mode_str = f" ({self.mode})" if self.mode else ""
        return f"{self.pod.name}: {self.key}{mode_str}"


class PodDeploymentLog(models.Model):
    """
    Deployment history and logs for PODs.
    """
    
    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DEPLOY = 'deploy', 'Deploy'
        SUSPEND = 'suspend', 'Suspend'
        RESUME = 'resume', 'Resume'
        TERMINATE = 'terminate', 'Terminate'
        SCALE = 'scale', 'Scale'
        CONFIG_CHANGE = 'config_change', 'Configuration Change'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pod = models.ForeignKey(Pod, on_delete=models.CASCADE, related_name='deployment_logs')
    
    action = models.CharField(max_length=50, choices=Action.choices)
    status = models.CharField(max_length=50)
    message = models.TextField(blank=True)
    details = models.JSONField(default=dict)
    
    # Who performed the action
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pod_actions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_pod_deployment_logs'
        verbose_name = 'POD Deployment Log'
        verbose_name_plural = 'POD Deployment Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.pod.name}: {self.action} at {self.created_at}"
