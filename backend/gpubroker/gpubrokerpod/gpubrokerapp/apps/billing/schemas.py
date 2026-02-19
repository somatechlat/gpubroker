"""
Billing Schemas - Pydantic models for API request/response.
"""

from datetime import datetime
from typing import Any

from ninja import Schema


class PlanFeatures(Schema):
    """Features included in a plan."""

    api_access: bool = True
    websocket_access: bool = False
    priority_support: bool = False
    dedicated_resources: bool = False
    custom_integrations: bool = False
    sla_guarantee: bool = False
    account_manager: bool = False


class PlanItem(Schema):
    """Single plan in list response."""

    id: str
    name: str
    tier: str
    price_monthly: float
    price_annual: float
    currency: str = "USD"
    tokens_monthly: int
    max_agents: int
    max_pods: int
    api_rate_limit: int
    features: dict[str, Any]
    description: str
    is_popular: bool = False
    annual_savings: float = 0.0


class PlansListResponse(Schema):
    """Response for plans listing endpoint."""

    plans: list[PlanItem]
    default_plan: str = "free"


class SubscriptionStatus(Schema):
    """Current subscription status."""

    id: str
    plan_id: str
    plan_name: str
    plan_tier: str
    status: str
    billing_interval: str
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    tokens_used: int = 0
    tokens_remaining: int = 0
    cancel_at_period_end: bool = False


class SetupIntentRequest(Schema):
    """Request to create a Stripe SetupIntent."""

    return_url: str | None = None


class SetupIntentResponse(Schema):
    """Response with SetupIntent client secret."""

    client_secret: str
    setup_intent_id: str
    publishable_key: str = ""


class StripeConfigResponse(Schema):
    """Stripe configuration for frontend."""

    publishable_key: str
    mode: str = "sandbox"


class AddPaymentMethodRequest(Schema):
    """Request to add a payment method after SetupIntent confirmation."""

    setup_intent_id: str


class SubscribeRequest(Schema):
    """Request to create a subscription."""

    plan_id: str
    billing_interval: str = "monthly"  # monthly or annual
    payment_method_id: str | None = None
    promo_code: str | None = None


class SubscribeResponse(Schema):
    """Response after creating subscription."""

    subscription_id: str
    status: str
    client_secret: str | None = None  # For 3D Secure
    requires_action: bool = False


class CancelSubscriptionRequest(Schema):
    """Request to cancel subscription."""

    cancel_immediately: bool = False
    reason: str | None = None


class PaymentMethodItem(Schema):
    """Payment method details."""

    id: str
    type: str
    card_brand: str | None = None
    card_last4: str | None = None
    card_exp_month: int | None = None
    card_exp_year: int | None = None
    is_default: bool = False


class InvoiceItem(Schema):
    """Invoice summary."""

    id: str
    invoice_number: str
    status: str
    subtotal: float
    tax: float
    total: float
    currency: str
    invoice_date: datetime
    due_date: datetime | None = None
    paid_at: datetime | None = None
    pdf_url: str | None = None


class InvoiceListResponse(Schema):
    """Response for invoice listing."""

    invoices: list[InvoiceItem]
    total: int


class UsageSummary(Schema):
    """Usage summary for current period."""

    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    api_calls: int
    gpu_hours: float
    period_start: datetime
    period_end: datetime


class BillingOverview(Schema):
    """Complete billing overview."""

    subscription: SubscriptionStatus | None = None
    usage: UsageSummary | None = None
    payment_methods: list[PaymentMethodItem] = []
    upcoming_invoice: InvoiceItem | None = None
    recent_invoices: list[InvoiceItem] = []
