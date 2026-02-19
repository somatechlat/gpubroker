"""
Billing Services - Business logic for billing operations.

Handles:
- Plan management
- Stripe integration
- Subscription lifecycle
- Usage tracking
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any

from django.core.cache import cache
from asgiref.sync import sync_to_async

from .models import Plan, Subscription, UsageRecord

logger = logging.getLogger('gpubroker.billing.services')

# Cache TTL for plans (5 minutes)
PLANS_CACHE_TTL = 300


async def get_all_plans(include_inactive: bool = False) -> List[Dict[str, Any]]:
    """
    Get all subscription plans.
    
    Args:
        include_inactive: Include inactive plans
        
    Returns:
        List of plan dicts
    """
    # Check cache first
    cache_key = f"billing:plans:{include_inactive}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Query database
    queryset = Plan.objects.all()
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    
    plans = []
    async for plan in queryset.order_by('display_order'):
        plans.append({
            "id": str(plan.id),
            "name": plan.name,
            "tier": plan.tier,
            "price_monthly": float(plan.price_monthly),
            "price_annual": float(plan.price_annual),
            "currency": plan.currency,
            "tokens_monthly": plan.tokens_monthly,
            "max_agents": plan.max_agents,
            "max_pods": plan.max_pods,
            "api_rate_limit": plan.api_rate_limit,
            "features": plan.features,
            "description": plan.description,
            "is_popular": plan.is_popular,
            "annual_savings": float(plan.annual_savings),
        })
    
    # Cache the result
    cache.set(cache_key, plans, PLANS_CACHE_TTL)
    
    return plans


async def get_plan_by_id(plan_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific plan by ID.
    
    Args:
        plan_id: Plan UUID
        
    Returns:
        Plan dict or None
    """
    try:
        plan = await sync_to_async(Plan.objects.get)(id=plan_id)
        return {
            "id": str(plan.id),
            "name": plan.name,
            "tier": plan.tier,
            "price_monthly": float(plan.price_monthly),
            "price_annual": float(plan.price_annual),
            "currency": plan.currency,
            "tokens_monthly": plan.tokens_monthly,
            "max_agents": plan.max_agents,
            "max_pods": plan.max_pods,
            "api_rate_limit": plan.api_rate_limit,
            "features": plan.features,
            "description": plan.description,
            "is_popular": plan.is_popular,
            "stripe_price_id": plan.stripe_price_id,
        }
    except Plan.DoesNotExist:
        return None


async def get_plan_by_tier(tier: str) -> Optional[Dict[str, Any]]:
    """
    Get a plan by tier name.
    
    Args:
        tier: Plan tier (free, basic, pro, corp, enterprise)
        
    Returns:
        Plan dict or None
    """
    try:
        plan = await sync_to_async(Plan.objects.filter(tier=tier, is_active=True).first)()
        if not plan:
            return None
        return {
            "id": str(plan.id),
            "name": plan.name,
            "tier": plan.tier,
            "price_monthly": float(plan.price_monthly),
            "price_annual": float(plan.price_annual),
            "currency": plan.currency,
            "tokens_monthly": plan.tokens_monthly,
            "max_agents": plan.max_agents,
            "max_pods": plan.max_pods,
            "api_rate_limit": plan.api_rate_limit,
            "features": plan.features,
            "stripe_price_id": plan.stripe_price_id,
        }
    except Exception as e:
        logger.error(f"Failed to get plan by tier: {e}")
        return None


async def get_user_subscription(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user's active subscription.
    
    Args:
        user_id: User UUID
        
    Returns:
        Subscription dict or None
    """
    try:
        subscription = await sync_to_async(
            Subscription.objects.select_related('plan').filter(
                user_id=user_id,
                status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
            ).first
        )()
        
        if not subscription:
            return None
        
        return {
            "id": str(subscription.id),
            "plan_id": str(subscription.plan.id),
            "plan_name": subscription.plan.name,
            "plan_tier": subscription.plan.tier,
            "status": subscription.status,
            "billing_interval": subscription.billing_interval,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "tokens_used": subscription.tokens_used,
            "tokens_remaining": subscription.tokens_remaining,
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }
    except Exception as e:
        logger.error(f"Failed to get user subscription: {e}")
        return None


async def create_subscription(
    user_id: str,
    plan_id: str,
    billing_interval: str = "monthly",
    stripe_subscription_id: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Create a new subscription for a user.
    
    Args:
        user_id: User UUID
        plan_id: Plan UUID
        billing_interval: monthly or annual
        stripe_subscription_id: Stripe subscription ID
        stripe_customer_id: Stripe customer ID
        
    Returns:
        Created subscription dict or None
    """
    try:
        plan = await sync_to_async(Plan.objects.get)(id=plan_id)
        
        # Cancel any existing active subscriptions
        await sync_to_async(
            Subscription.objects.filter(
                user_id=user_id,
                status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
            ).update
        )(status=Subscription.Status.CANCELED, canceled_at=datetime.now(timezone.utc))
        
        # Create new subscription
        now = datetime.now(timezone.utc)
        subscription = await sync_to_async(Subscription.objects.create)(
            user_id=user_id,
            plan=plan,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            status=Subscription.Status.ACTIVE,
            billing_interval=billing_interval,
            current_period_start=now,
            current_period_end=now,  # Will be updated by Stripe webhook
            tokens_reset_at=now,
        )
        
        return {
            "id": str(subscription.id),
            "plan_id": str(plan.id),
            "plan_name": plan.name,
            "status": subscription.status,
        }
    except Plan.DoesNotExist:
        logger.error(f"Plan not found: {plan_id}")
        return None
    except Exception as e:
        logger.error(f"Failed to create subscription: {e}")
        return None


async def cancel_subscription(
    user_id: str,
    cancel_immediately: bool = False,
    reason: Optional[str] = None,
) -> bool:
    """
    Cancel user's subscription.
    
    Args:
        user_id: User UUID
        cancel_immediately: Cancel now vs at period end
        reason: Cancellation reason
        
    Returns:
        True if successful
    """
    try:
        subscription = await sync_to_async(
            Subscription.objects.filter(
                user_id=user_id,
                status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
            ).first
        )()
        
        if not subscription:
            return False
        
        if cancel_immediately:
            subscription.status = Subscription.Status.CANCELED
            subscription.canceled_at = datetime.now(timezone.utc)
        else:
            subscription.cancel_at_period_end = True
        
        await sync_to_async(subscription.save)()
        
        # Cancel in Stripe if subscription exists
        if subscription.stripe_subscription_id:
            try:
                from .stripe_service import StripeService
                stripe_service = StripeService()
                await stripe_service.cancel_subscription(subscription.stripe_subscription_id)
                logger.info(f"Canceled Stripe subscription: {subscription.stripe_subscription_id}")
            except Exception as stripe_error:
                logger.error(f"Failed to cancel Stripe subscription {subscription.stripe_subscription_id}: {stripe_error}")
                # Continue anyway - local cancellation succeeded
        
        return True
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        return False


async def record_usage(
    user_id: str,
    usage_type: str,
    quantity: Decimal,
    metadata: Optional[Dict] = None,
) -> bool:
    """
    Record usage for billing.
    
    Args:
        user_id: User UUID
        usage_type: Type of usage (api_call, token, gpu_hour, storage)
        quantity: Amount used
        metadata: Additional metadata
        
    Returns:
        True if successful
    """
    try:
        subscription = await sync_to_async(
            Subscription.objects.filter(
                user_id=user_id,
                status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
            ).first
        )()
        
        if not subscription:
            logger.warning(f"No active subscription for user {user_id}")
            return False
        
        now = datetime.now(timezone.utc)
        
        # Create usage record
        await sync_to_async(UsageRecord.objects.create)(
            user_id=user_id,
            subscription=subscription,
            usage_type=usage_type,
            quantity=quantity,
            metadata=metadata or {},
            period_start=subscription.current_period_start or now,
            period_end=subscription.current_period_end or now,
            recorded_at=now,
        )
        
        # Update subscription token count if applicable
        if usage_type == UsageRecord.UsageType.TOKEN:
            subscription.tokens_used += int(quantity)
            await sync_to_async(subscription.save)(update_fields=['tokens_used', 'updated_at'])
        
        return True
    except Exception as e:
        logger.error(f"Failed to record usage: {e}")
        return False


async def get_usage_summary(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get usage summary for current billing period.
    
    Args:
        user_id: User UUID
        
    Returns:
        Usage summary dict or None
    """
    try:
        subscription = await sync_to_async(
            Subscription.objects.select_related('plan').filter(
                user_id=user_id,
                status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
            ).first
        )()
        
        if not subscription:
            return None
        
        # Get usage records for current period
        period_start = subscription.current_period_start or subscription.created_at
        period_end = subscription.current_period_end or datetime.now(timezone.utc)
        
        # Aggregate usage by type
        api_calls = 0
        gpu_hours = Decimal('0')
        
        async for record in UsageRecord.objects.filter(
            subscription=subscription,
            recorded_at__gte=period_start,
            recorded_at__lte=period_end,
        ):
            if record.usage_type == UsageRecord.UsageType.API_CALL:
                api_calls += int(record.quantity)
            elif record.usage_type == UsageRecord.UsageType.GPU_HOUR:
                gpu_hours += record.quantity
        
        return {
            "tokens_used": subscription.tokens_used,
            "tokens_limit": subscription.plan.tokens_monthly,
            "tokens_remaining": subscription.tokens_remaining,
            "api_calls": api_calls,
            "gpu_hours": float(gpu_hours),
            "period_start": period_start,
            "period_end": period_end,
        }
    except Exception as e:
        logger.error(f"Failed to get usage summary: {e}")
        return None


async def seed_default_plans() -> int:
    """
    Seed default subscription plans.
    
    Returns:
        Number of plans created
    """
    default_plans = [
        {
            "name": "Free Trial",
            "tier": Plan.Tier.FREE,
            "price_monthly": Decimal('0.00'),
            "price_annual": Decimal('0.00'),
            "tokens_monthly": 1000,
            "max_agents": 1,
            "max_pods": 1,
            "api_rate_limit": 10,
            "features": {
                "api_access": True,
                "websocket_access": False,
                "priority_support": False,
            },
            "description": "Perfect for trying out GPUBROKER",
            "display_order": 0,
        },
        {
            "name": "Basic",
            "tier": Plan.Tier.BASIC,
            "price_monthly": Decimal('20.00'),
            "price_annual": Decimal('200.00'),
            "tokens_monthly": 5000,
            "max_agents": 2,
            "max_pods": 2,
            "api_rate_limit": 30,
            "features": {
                "api_access": True,
                "websocket_access": True,
                "priority_support": False,
            },
            "description": "For individual developers and small projects",
            "display_order": 1,
        },
        {
            "name": "Pro",
            "tier": Plan.Tier.PRO,
            "price_monthly": Decimal('40.00'),
            "price_annual": Decimal('400.00'),
            "tokens_monthly": 10000,
            "max_agents": 5,
            "max_pods": 5,
            "api_rate_limit": 100,
            "features": {
                "api_access": True,
                "websocket_access": True,
                "priority_support": True,
            },
            "description": "For growing teams and production workloads",
            "is_popular": True,
            "display_order": 2,
        },
        {
            "name": "Corporate",
            "tier": Plan.Tier.CORP,
            "price_monthly": Decimal('99.00'),
            "price_annual": Decimal('990.00'),
            "tokens_monthly": 50000,
            "max_agents": 10,
            "max_pods": 10,
            "api_rate_limit": 500,
            "features": {
                "api_access": True,
                "websocket_access": True,
                "priority_support": True,
                "sla_guarantee": True,
            },
            "description": "For organizations with demanding workloads",
            "display_order": 3,
        },
        {
            "name": "Enterprise",
            "tier": Plan.Tier.ENTERPRISE,
            "price_monthly": Decimal('299.00'),
            "price_annual": Decimal('2990.00'),
            "tokens_monthly": 200000,
            "max_agents": -1,  # Unlimited
            "max_pods": -1,  # Unlimited
            "api_rate_limit": 1000,
            "features": {
                "api_access": True,
                "websocket_access": True,
                "priority_support": True,
                "dedicated_resources": True,
                "custom_integrations": True,
                "sla_guarantee": True,
                "account_manager": True,
            },
            "description": "Custom solutions for large enterprises",
            "display_order": 4,
        },
    ]
    
    created = 0
    for plan_data in default_plans:
        plan, was_created = await sync_to_async(Plan.objects.get_or_create)(
            tier=plan_data["tier"],
            defaults=plan_data,
        )
        if was_created:
            created += 1
            logger.info(f"Created plan: {plan.name}")
    
    return created
