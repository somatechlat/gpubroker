"""
Billing Schemas - Pydantic models for API request/response.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

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
    features: Dict[str, Any]
    description: str
    is_popular: bool = False
    annual_savings: float = 0.0


class PlansListResponse(Schema):
    """Response for plans listing endpoint."""
    plans: List[PlanItem]
    default_plan: str = "free"


class SubscriptionStatus(Schema):
    """Current subscription status."""
    id: str
    plan_id: str
    plan_name: str
    plan_tier: str
    status: str
    billing_interval: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    tokens_used: int = 0
    tokens_remaining: int = 0
    cancel_at_period_end: bool = False


class SetupIntentRequest(Schema):
    """Request to create a Stripe SetupIntent."""
    return_url: Optional[str] = None


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
    payment_method_id: Optional[str] = None
    promo_code: Optional[str] = None


class SubscribeResponse(Schema):
    """Response after creating subscription."""
    subscription_id: str
    status: str
    client_secret: Optional[str] = None  # For 3D Secure
    requires_action: bool = False


class CancelSubscriptionRequest(Schema):
    """Request to cancel subscription."""
    cancel_immediately: bool = False
    reason: Optional[str] = None


class PaymentMethodItem(Schema):
    """Payment method details."""
    id: str
    type: str
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None
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
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    pdf_url: Optional[str] = None


class InvoiceListResponse(Schema):
    """Response for invoice listing."""
    invoices: List[InvoiceItem]
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
    subscription: Optional[SubscriptionStatus] = None
    usage: Optional[UsageSummary] = None
    payment_methods: List[PaymentMethodItem] = []
    upcoming_invoice: Optional[InvoiceItem] = None
    recent_invoices: List[InvoiceItem] = []
