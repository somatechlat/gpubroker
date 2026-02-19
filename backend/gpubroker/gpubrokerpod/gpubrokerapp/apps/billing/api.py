"""
Billing API Endpoints - Django Ninja Router.

Endpoints:
- GET /plans - List subscription plans
- GET /subscription - Get current subscription
- POST /subscribe - Create subscription
- POST /cancel - Cancel subscription
- GET /usage - Get usage summary
- GET /invoices - List invoices
- POST /setup-intent - Create Stripe SetupIntent
- POST /webhook - Stripe webhook handler
"""
import logging
from typing import List

from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest

from .schemas import (
    PlansListResponse,
    PlanItem,
    SubscriptionStatus,
    SubscribeRequest,
    SubscribeResponse,
    CancelSubscriptionRequest,
    SetupIntentRequest,
    SetupIntentResponse,
    UsageSummary,
    InvoiceListResponse,
    InvoiceItem,
    BillingOverview,
    PaymentMethodItem,
    AddPaymentMethodRequest,
    StripeConfigResponse,
)
from .services import (
    get_all_plans,
    get_plan_by_id,
    get_user_subscription,
    create_subscription,
    cancel_subscription,
    get_usage_summary,
)
from .stripe_service import get_stripe_service
from gpubrokerpod.gpubrokerapp.apps.auth_app.auth import JWTAuth

logger = logging.getLogger('gpubroker.billing.api')

router = Router(tags=["billing"])


@router.get("/plans", response=PlansListResponse, auth=None)
async def list_plans(request: HttpRequest):
    """
    List all available subscription plans.
    
    This endpoint is public (no auth required) for pricing page display.
    Plans are cached for 5 minutes.
    """
    plans = await get_all_plans()
    
    plan_items = [
        PlanItem(
            id=p["id"],
            name=p["name"],
            tier=p["tier"],
            price_monthly=p["price_monthly"],
            price_annual=p["price_annual"],
            currency=p["currency"],
            tokens_monthly=p["tokens_monthly"],
            max_agents=p["max_agents"],
            max_pods=p["max_pods"],
            api_rate_limit=p["api_rate_limit"],
            features=p["features"],
            description=p["description"],
            is_popular=p["is_popular"],
            annual_savings=p["annual_savings"],
        )
        for p in plans
    ]
    
    return PlansListResponse(
        plans=plan_items,
        default_plan="free",
    )


@router.get("/subscription", response=SubscriptionStatus, auth=JWTAuth())
async def get_subscription(request: HttpRequest):
    """
    Get current user's subscription status.
    """
    user = request.auth
    
    subscription = await get_user_subscription(str(user.id))
    
    if not subscription:
        raise HttpError(404, "No active subscription found")
    
    return SubscriptionStatus(**subscription)


@router.post("/subscribe", response=SubscribeResponse, auth=JWTAuth())
async def subscribe(request: HttpRequest, data: SubscribeRequest):
    """
    Create a new subscription.
    
    For paid plans, requires a valid payment method.
    Free plans can be subscribed without payment.
    """
    user = request.auth
    stripe_service = get_stripe_service()
    
    # Get the plan
    plan = await get_plan_by_id(data.plan_id)
    if not plan:
        raise HttpError(404, "Plan not found")
    
    # Check if payment is required
    if plan["price_monthly"] > 0 and not data.payment_method_id:
        raise HttpError(400, "Payment method required for paid plans")
    
    # Get or create Stripe customer
    existing_sub = await get_user_subscription(str(user.id))
    customer_id = existing_sub.get('stripe_customer_id') if existing_sub else None
    
    if not customer_id and stripe_service.is_configured:
        customer_id = await stripe_service.create_customer(
            email=user.email,
            name=getattr(user, 'full_name', None),
            metadata={"user_id": str(user.id)},
        )
    
    # Create Stripe subscription for paid plans
    stripe_sub_id = None
    client_secret = None
    requires_action = False
    
    if plan["price_monthly"] > 0 and plan.get("stripe_price_id") and stripe_service.is_configured:
        stripe_result = await stripe_service.create_subscription(
            customer_id=customer_id,
            price_id=plan["stripe_price_id"],
            payment_method_id=data.payment_method_id,
            metadata={"user_id": str(user.id), "plan_id": data.plan_id},
        )
        
        if stripe_result and "error" in stripe_result:
            raise HttpError(400, stripe_result["error"])
        
        if stripe_result:
            stripe_sub_id = stripe_result["id"]
            client_secret = stripe_result.get("client_secret")
            requires_action = stripe_result.get("requires_action", False)
    
    # Create local subscription record
    subscription = await create_subscription(
        user_id=str(user.id),
        plan_id=data.plan_id,
        billing_interval=data.billing_interval,
        stripe_subscription_id=stripe_sub_id,
        stripe_customer_id=customer_id,
    )
    
    if not subscription:
        raise HttpError(500, "Failed to create subscription")
    
    return SubscribeResponse(
        subscription_id=subscription["id"],
        status=subscription["status"],
        client_secret=client_secret,
        requires_action=requires_action,
    )


@router.post("/cancel", auth=JWTAuth())
async def cancel(request: HttpRequest, data: CancelSubscriptionRequest):
    """
    Cancel current subscription.
    
    By default, cancels at end of billing period.
    Set cancel_immediately=true to cancel now.
    """
    user = request.auth
    
    success = await cancel_subscription(
        user_id=str(user.id),
        cancel_immediately=data.cancel_immediately,
        reason=data.reason,
    )
    
    if not success:
        raise HttpError(400, "Failed to cancel subscription")
    
    return {"status": "canceled", "immediate": data.cancel_immediately}


@router.get("/usage", response=UsageSummary, auth=JWTAuth())
async def get_usage(request: HttpRequest):
    """
    Get usage summary for current billing period.
    """
    user = request.auth
    
    usage = await get_usage_summary(str(user.id))
    
    if not usage:
        raise HttpError(404, "No active subscription found")
    
    return UsageSummary(**usage)


@router.post("/setup-intent", response=SetupIntentResponse, auth=JWTAuth())
async def create_setup_intent(request: HttpRequest, data: SetupIntentRequest):
    """
    Create a Stripe SetupIntent for adding a payment method.
    
    Returns client_secret for Stripe Elements.
    """
    user = request.auth
    stripe_service = get_stripe_service()
    
    if not stripe_service.is_configured:
        # Return mock data for sandbox mode without Stripe keys
        return SetupIntentResponse(
            client_secret="seti_mock_client_secret_for_sandbox",
            setup_intent_id="seti_mock_sandbox",
            publishable_key="pk_test_mock_sandbox",
        )
    
    # Get or create Stripe customer
    subscription = await get_user_subscription(str(user.id))
    customer_id = subscription.get('stripe_customer_id') if subscription else None
    
    if not customer_id:
        # Create new Stripe customer
        customer_id = await stripe_service.create_customer(
            email=user.email,
            name=getattr(user, 'full_name', None),
            metadata={"user_id": str(user.id)},
        )
        if not customer_id:
            raise HttpError(500, "Failed to create payment customer")
    
    # Create SetupIntent
    result = await stripe_service.create_setup_intent(
        customer_id=customer_id,
        metadata={"user_id": str(user.id)},
    )
    
    if not result:
        raise HttpError(500, "Failed to create setup intent")
    
    return SetupIntentResponse(
        client_secret=result["client_secret"],
        setup_intent_id=result["setup_intent_id"],
        publishable_key=result.get("publishable_key", ""),
    )


@router.get("/config", response=StripeConfigResponse, auth=None)
async def get_stripe_config(request: HttpRequest):
    """
    Get Stripe publishable key for frontend.
    
    This endpoint is public (no auth required).
    """
    stripe_service = get_stripe_service()
    
    return StripeConfigResponse(
        publishable_key=stripe_service.publishable_key or "pk_test_mock_sandbox",
        mode=stripe_service.mode,
    )


@router.get("/invoices", response=InvoiceListResponse, auth=JWTAuth())
async def list_invoices(
    request: HttpRequest,
    page: int = 1,
    per_page: int = 10,
):
    """
    List user's invoices.
    """
    user = request.auth
    stripe_service = get_stripe_service()
    
    # Get user's Stripe customer ID
    subscription = await get_user_subscription(str(user.id))
    customer_id = subscription.get('stripe_customer_id') if subscription else None
    
    if not customer_id or not stripe_service.is_configured:
        return InvoiceListResponse(invoices=[], total=0)
    
    # Fetch invoices from Stripe
    invoices = await stripe_service.list_invoices(customer_id, limit=per_page)
    
    invoice_items = [
        InvoiceItem(
            id=inv["id"],
            invoice_number=inv["number"] or inv["id"],
            status=inv["status"],
            subtotal=inv["amount_due"],
            tax=0.0,
            total=inv["amount_paid"],
            currency=inv["currency"].upper(),
            invoice_date=inv["created"],
            due_date=inv.get("due_date"),
            paid_at=inv.get("paid_at"),
            pdf_url=inv.get("pdf_url"),
        )
        for inv in invoices
    ]
    
    return InvoiceListResponse(
        invoices=invoice_items,
        total=len(invoice_items),
    )


@router.get("/payment-methods", response=List[PaymentMethodItem], auth=JWTAuth())
async def list_payment_methods(request: HttpRequest):
    """
    List user's saved payment methods.
    """
    user = request.auth
    stripe_service = get_stripe_service()
    
    # Get user's Stripe customer ID
    subscription = await get_user_subscription(str(user.id))
    customer_id = subscription.get('stripe_customer_id') if subscription else None
    
    if not customer_id or not stripe_service.is_configured:
        return []
    
    methods = await stripe_service.list_payment_methods(customer_id)
    
    return [
        PaymentMethodItem(
            id=pm["id"],
            type=pm["type"],
            card_brand=pm.get("card_brand"),
            card_last4=pm.get("card_last4"),
            card_exp_month=pm.get("card_exp_month"),
            card_exp_year=pm.get("card_exp_year"),
            is_default=False,  # Would need to check customer's default
        )
        for pm in methods
    ]


@router.post("/payment-methods/{payment_method_id}/default", auth=JWTAuth())
async def set_default_payment_method(request: HttpRequest, payment_method_id: str):
    """
    Set a payment method as default.
    """
    user = request.auth
    stripe_service = get_stripe_service()
    
    subscription = await get_user_subscription(str(user.id))
    customer_id = subscription.get('stripe_customer_id') if subscription else None
    
    if not customer_id:
        raise HttpError(400, "No payment customer found")
    
    success = await stripe_service.update_customer(
        customer_id,
        default_payment_method=payment_method_id,
    )
    
    if not success:
        raise HttpError(500, "Failed to update default payment method")
    
    return {"status": "success", "default_payment_method": payment_method_id}


@router.delete("/payment-methods/{payment_method_id}", auth=JWTAuth())
async def delete_payment_method(request: HttpRequest, payment_method_id: str):
    """
    Remove a saved payment method.
    """
    user = request.auth
    stripe_service = get_stripe_service()
    
    success = await stripe_service.detach_payment_method(payment_method_id)
    
    if not success:
        raise HttpError(500, "Failed to remove payment method")
    
    return {"status": "deleted", "payment_method_id": payment_method_id}


@router.post("/webhook", auth=None)
async def stripe_webhook(request: HttpRequest):
    """
    Handle Stripe webhook events.
    
    This endpoint is called by Stripe to notify us of events.
    """
    stripe_service = get_stripe_service()
    
    # Get raw body and signature
    payload = request.body
    signature = request.headers.get('Stripe-Signature', '')
    
    # Verify webhook
    event = stripe_service.verify_webhook(payload, signature)
    
    if not event:
        raise HttpError(400, "Invalid webhook signature")
    
    # Handle the event
    success = await stripe_service.handle_webhook_event(event)
    
    if not success:
        logger.error(f"Failed to handle webhook event: {event.get('type')}")
    
    return {"received": True}


@router.get("/overview", response=BillingOverview, auth=JWTAuth())
async def get_overview(request: HttpRequest):
    """
    Get complete billing overview.
    
    Includes subscription, usage, payment methods, and recent invoices.
    """
    user = request.auth
    
    subscription = await get_user_subscription(str(user.id))
    usage = await get_usage_summary(str(user.id)) if subscription else None
    
    return BillingOverview(
        subscription=SubscriptionStatus(**subscription) if subscription else None,
        usage=UsageSummary(**usage) if usage else None,
        payment_methods=[],
        upcoming_invoice=None,
        recent_invoices=[],
    )
