"""
GPUBROKER Subscription Models

Subscription and payment management for GPUBROKER POD.
"""
import uuid
import hashlib
from decimal import Decimal
from django.db import models
from django.utils import timezone


class Subscription(models.Model):
    """
    GPUBROKER POD Subscription.
    """
    
    class Status(models.TextChoices):
        PENDING_ACTIVATION = 'pending_activation', 'Pending Activation'
        PROVISIONING = 'provisioning', 'Provisioning'
        RUNNING = 'running', 'Running'
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        FAILED = 'failed', 'Failed'
        DESTROYED = 'destroyed', 'Destroyed'
        EXPIRED = 'expired', 'Expired'
    
    class Plan(models.TextChoices):
        TRIAL = 'trial', 'Trial'
        BASIC = 'basic', 'Basic'
        PRO = 'pro', 'Professional'
        CORP = 'corp', 'Corporate'
        ENTERPRISE = 'enterprise', 'Enterprise'
    
    # Primary identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription_id = models.CharField(max_length=64, unique=True, db_index=True)
    
    # API Key (hashed for security)
    api_key = models.CharField(max_length=64, unique=True, db_index=True)
    api_key_hash = models.CharField(max_length=64, db_index=True)
    
    # Customer info
    email = models.EmailField(db_index=True)
    name = models.CharField(max_length=255, blank=True)
    ruc = models.CharField(max_length=20, blank=True)  # Ecuador tax ID
    
    # Plan and status
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.TRIAL)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_ACTIVATION)
    
    # Token limits
    token_limit = models.IntegerField(default=5000)
    tokens_used = models.IntegerField(default=0)
    
    # Pod info
    pod_id = models.CharField(max_length=64, unique=True, db_index=True)
    pod_url = models.URLField(blank=True)
    task_arn = models.CharField(max_length=255, blank=True)  # ECS task ARN
    
    # Payment info
    payment_provider = models.CharField(max_length=20, blank=True)  # paypal, payphone, stripe
    transaction_id = models.CharField(max_length=100, blank=True, db_index=True)
    order_id = models.CharField(max_length=100, blank=True, db_index=True)
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    card_last4 = models.CharField(max_length=4, blank=True)
    payment_status = models.CharField(max_length=20, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    activated_at = models.DateTimeField(null=True, blank=True)
    destroyed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'gpubroker_subscriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'status']),
            models.Index(fields=['pod_id', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.subscription_id} - {self.email} ({self.plan})"
    
    @classmethod
    def generate_api_key(cls) -> str:
        """Generate a unique API key."""
        unique = uuid.uuid4().hex
        return f"sk_live_{unique}"
    
    @classmethod
    def hash_api_key(cls, api_key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @classmethod
    def generate_subscription_id(cls) -> str:
        """Generate unique subscription ID."""
        return f"sub_{uuid.uuid4().hex[:12]}"
    
    @classmethod
    def generate_pod_id(cls) -> str:
        """Generate unique pod ID."""
        return f"pod-{uuid.uuid4().hex[:8]}"
    
    def get_tokens_remaining(self) -> int:
        """Get remaining tokens."""
        return max(0, self.token_limit - self.tokens_used)
    
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in [self.Status.RUNNING, self.Status.ACTIVE]
    
    def is_expired(self) -> bool:
        """Check if subscription is expired."""
        return self.expires_at < timezone.now()


class Payment(models.Model):
    """
    Payment transaction record.
    """
    
    class Provider(models.TextChoices):
        PAYPAL = 'paypal', 'PayPal'
        PAYPHONE = 'payphone', 'PayPhone'
        STRIPE = 'stripe', 'Stripe'
        MANUAL = 'manual', 'Manual'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription, 
        on_delete=models.CASCADE, 
        related_name='payments'
    )
    
    # Provider info
    provider = models.CharField(max_length=20, choices=Provider.choices)
    transaction_id = models.CharField(max_length=100, db_index=True)
    order_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Amount
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Card info (masked)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'gpubroker_payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider', 'transaction_id']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.provider} - ${self.amount_usd} ({self.status})"


class PodMetrics(models.Model):
    """
    Pod metrics snapshot for monitoring.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription, 
        on_delete=models.CASCADE, 
        related_name='metrics'
    )
    
    # AWS metrics
    cpu_utilization = models.FloatField(default=0.0)
    memory_utilization = models.FloatField(default=0.0)
    network_in_bytes = models.BigIntegerField(default=0)
    network_out_bytes = models.BigIntegerField(default=0)
    
    # Pod info
    public_ip = models.GenericIPAddressField(null=True, blank=True)
    private_ip = models.GenericIPAddressField(null=True, blank=True)
    uptime_seconds = models.IntegerField(default=0)
    
    # Cost
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    
    # Timestamp
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gpubroker_pod_metrics'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['subscription', 'recorded_at']),
        ]
