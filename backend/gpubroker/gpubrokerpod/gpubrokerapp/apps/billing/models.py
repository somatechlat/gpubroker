"""
Billing Models - Subscription plans, payments, and invoices.

Models:
- Plan: Subscription plan definitions (FREE, PRO, ENTERPRISE)
- Subscription: User subscriptions
- PaymentMethod: Stored payment methods
- Invoice: Generated invoices
- UsageRecord: Usage tracking for billing
"""

import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone


class Plan(models.Model):
    """
    Subscription plan definition.

    Plans are synced from Stripe but stored locally for fast access.
    """

    class Tier(models.TextChoices):
        FREE = "free", "Free"
        BASIC = "basic", "Basic"
        PRO = "pro", "Pro"
        CORP = "corp", "Corporate"
        ENTERPRISE = "enterprise", "Enterprise"

    class BillingInterval(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Plan identification
    name = models.CharField(max_length=100)
    tier = models.CharField(max_length=20, choices=Tier.choices)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True)

    # Pricing
    price_monthly = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    price_annual = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    currency = models.CharField(max_length=3, default="USD")

    # Features and limits
    tokens_monthly = models.IntegerField(default=1000)
    max_agents = models.IntegerField(default=1)
    max_pods = models.IntegerField(default=1)
    api_rate_limit = models.IntegerField(default=10, help_text="Requests per minute")

    # Feature flags
    features = models.JSONField(default=dict, help_text="Feature flags for this plan")

    # Display
    description = models.TextField(blank=True)
    is_popular = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_plans"
        ordering = ["display_order", "price_monthly"]
        indexes = [
            models.Index(fields=["tier"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.tier})"

    @property
    def annual_savings(self) -> Decimal:
        """Calculate annual savings vs monthly billing."""
        monthly_total = self.price_monthly * 12
        return monthly_total - self.price_annual


class Subscription(models.Model):
    """
    User subscription to a plan.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELED = "canceled", "Canceled"
        TRIALING = "trialing", "Trialing"
        PAUSED = "paused", "Paused"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User reference (string to avoid circular import)
    user_id = models.UUIDField(db_index=True)

    # Plan reference
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="subscriptions"
    )

    # Stripe references
    stripe_subscription_id = models.CharField(
        max_length=100, blank=True, null=True, unique=True
    )
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)

    # Status
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TRIALING
    )

    # Billing period
    billing_interval = models.CharField(
        max_length=20,
        choices=Plan.BillingInterval.choices,
        default=Plan.BillingInterval.MONTHLY,
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    # Trial
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)

    # Cancellation
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)

    # Usage tracking
    tokens_used = models.IntegerField(default=0)
    tokens_reset_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_subscriptions"
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["stripe_subscription_id"]),
        ]

    def __str__(self):
        return f"Subscription {self.id} - {self.plan.name}"

    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in [self.Status.ACTIVE, self.Status.TRIALING]

    @property
    def tokens_remaining(self) -> int:
        """Calculate remaining tokens for current period."""
        return max(0, self.plan.tokens_monthly - self.tokens_used)


class PaymentMethod(models.Model):
    """
    Stored payment method for a user.
    """

    class Type(models.TextChoices):
        CARD = "card", "Credit/Debit Card"
        BANK = "bank", "Bank Account"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User reference
    user_id = models.UUIDField(db_index=True)

    # Stripe reference
    stripe_payment_method_id = models.CharField(max_length=100, unique=True)

    # Type and details
    type = models.CharField(max_length=20, choices=Type.choices)

    # Card details (masked)
    card_brand = models.CharField(max_length=20, blank=True, null=True)
    card_last4 = models.CharField(max_length=4, blank=True, null=True)
    card_exp_month = models.IntegerField(null=True, blank=True)
    card_exp_year = models.IntegerField(null=True, blank=True)

    # Status
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_payment_methods"
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["is_default"]),
        ]

    def __str__(self):
        if self.type == self.Type.CARD:
            return f"{self.card_brand} ****{self.card_last4}"
        return f"{self.type}"


class Invoice(models.Model):
    """
    Invoice record for billing.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        PAID = "paid", "Paid"
        VOID = "void", "Void"
        UNCOLLECTIBLE = "uncollectible", "Uncollectible"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User and subscription
    user_id = models.UUIDField(db_index=True)
    subscription = models.ForeignKey(
        Subscription, on_delete=models.SET_NULL, null=True, related_name="invoices"
    )

    # Stripe reference
    stripe_invoice_id = models.CharField(
        max_length=100, blank=True, null=True, unique=True
    )

    # Invoice details
    invoice_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")

    # Dates
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # PDF
    pdf_url = models.URLField(blank=True, null=True)

    # Line items stored as JSON
    line_items = models.JSONField(default=list)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_invoices"
        ordering = ["-invoice_date"]
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["invoice_date"]),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number}"


class UsageRecord(models.Model):
    """
    Usage tracking for metered billing.
    """

    class UsageType(models.TextChoices):
        API_CALL = "api_call", "API Call"
        TOKEN = "token", "Token Usage"
        GPU_HOUR = "gpu_hour", "GPU Hour"
        STORAGE = "storage", "Storage (GB)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User and subscription
    user_id = models.UUIDField(db_index=True)
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="usage_records"
    )

    # Usage details
    usage_type = models.CharField(max_length=20, choices=UsageType.choices)
    quantity = models.DecimalField(max_digits=15, decimal_places=4)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal("0.00")
    )

    # Metadata
    metadata = models.JSONField(default=dict)

    # Billing period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()

    # Stripe reference
    stripe_usage_record_id = models.CharField(max_length=100, blank=True, null=True)

    # Timestamps
    recorded_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_usage_records"
        indexes = [
            models.Index(fields=["user_id", "usage_type"]),
            models.Index(fields=["subscription", "period_start"]),
            models.Index(fields=["recorded_at"]),
        ]

    def __str__(self):
        return f"{self.usage_type}: {self.quantity}"
