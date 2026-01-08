"""
GPUBROKER Subscription Services

Business logic for subscription management.
"""
import logging
from typing import Dict, Any, Optional
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from .models import Subscription, Payment, PodMetrics, PaymentTransaction
from gpubrokeradmin.common.messages import get_message

logger = logging.getLogger('gpubroker.subscriptions')


# Plan configuration
PLAN_CONFIG = {
    'trial': {'name': 'Prueba Gratuita', 'price': Decimal('0.00'), 'tokens': 1000},
    'basic': {'name': 'Básico', 'price': Decimal('20.00'), 'tokens': 5000},
    'pro': {'name': 'Profesional', 'price': Decimal('40.00'), 'tokens': 10000},
    'corp': {'name': 'Corporativo', 'price': Decimal('99.00'), 'tokens': 50000},
    'enterprise': {'name': 'Enterprise', 'price': Decimal('299.00'), 'tokens': 200000},
}


class SubscriptionService:
    """
    Service for managing subscriptions.
    """
    
    @staticmethod
    @transaction.atomic
    def create_subscription(
        email: str,
        plan: str,
        ruc: str = "",
        card_last4: str = "****",
        transaction_id: str = "",
        order_id: str = "",
        amount: float = 0.0,
        payment_provider: str = "unknown",
        name: str = "",
        country_code: str = "",
    ) -> Dict[str, Any]:
        """
        Create a new subscription after payment.
        
        Args:
            email: Customer email
            plan: Subscription plan
            ruc: Ecuador tax ID (only required for EC)
            card_last4: Last 4 digits of card
            transaction_id: Payment transaction ID
            order_id: Payment order ID
            amount: Payment amount in USD
            payment_provider: Payment provider name
            name: Customer name
            country_code: ISO country code from geo-detection
            
        Returns:
            Dict with subscription details
        """
        try:
            # Generate identifiers
            subscription_id = Subscription.generate_subscription_id()
            api_key = Subscription.generate_api_key()
            pod_id = Subscription.generate_pod_id()
            
            # Get plan config
            plan_config = PLAN_CONFIG.get(plan, PLAN_CONFIG['pro'])
            
            # Create subscription
            subscription = Subscription.objects.create(
                subscription_id=subscription_id,
                api_key=api_key,
                api_key_hash=Subscription.hash_api_key(api_key),
                email=email,
                name=name,
                ruc=ruc,
                plan=plan,
                status=Subscription.Status.PENDING_ACTIVATION,
                token_limit=plan_config['tokens'],
                tokens_used=0,
                pod_id=pod_id,
                pod_url=f"https://{pod_id}.gpubroker.site",
                payment_provider=payment_provider,
                transaction_id=transaction_id,
                order_id=order_id,
                amount_usd=Decimal(str(amount)),
                card_last4=card_last4,
                payment_status='completed' if amount > 0 else 'pending',
                payment_date=timezone.now() if amount > 0 else None,
                expires_at=timezone.now() + timedelta(days=30),
            )
            
            # Link any pending payment transaction record
            if order_id or transaction_id:
                try:
                    PaymentTransaction.objects.filter(
                        order_id=order_id
                    ).update(
                        subscription=subscription,
                        status=Payment.Status.COMPLETED if amount > 0 else Payment.Status.PENDING,
                    )
                except Exception as link_error:
                    logger.warning(f"[Subscription] Unable to link payment transaction: {link_error}")
            
            # Create payment record if amount > 0
            if amount > 0:
                Payment.objects.create(
                    subscription=subscription,
                    provider=payment_provider,
                    transaction_id=transaction_id,
                    order_id=order_id,
                    amount_usd=Decimal(str(amount)),
                    status=Payment.Status.COMPLETED,
                    card_last4=card_last4,
                    completed_at=timezone.now(),
                )
            
            logger.info(f"[Subscription] Created: {subscription_id} for {email}")
            
            return {
                "success": True,
                "subscription_id": subscription_id,
                "api_key": api_key,
                "pod_id": pod_id,
                "pod_url": f"https://{pod_id}.gpubroker.site",
                "status": "pending_activation",
                "message": get_message("subscription.created_pending"),
            }
            
        except Exception as e:
            logger.error(f"[Subscription] Error creating: {e}")
            return {
                "success": False,
                "error": get_message("subscription.create_error", error=str(e)),
            }
    
    @staticmethod
    def validate_api_key(api_key: str) -> Dict[str, Any]:
        """
        Validate an API key and return subscription details.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Dict with validation result
        """
        try:
            subscription = Subscription.objects.get(api_key=api_key)
            return {
                "valid": True,
                "subscription": subscription,
            }
        except Subscription.DoesNotExist:
            return {
                "valid": False,
                "error": get_message("subscription.api_key_invalid"),
            }
    
    @staticmethod
    @transaction.atomic
    def activate_subscription(api_key: str) -> Dict[str, Any]:
        """
        Activate subscription and trigger pod deployment.
        
        Args:
            api_key: Subscription API key
            
        Returns:
            Dict with activation result
        """
        validation = SubscriptionService.validate_api_key(api_key)
        
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}
        
        subscription = validation["subscription"]
        
        if subscription.status not in [
            Subscription.Status.PENDING_ACTIVATION, 
            Subscription.Status.FAILED
        ]:
            return {"success": False, "error": get_message("subscription.already_active")}
        
        # Update status to provisioning
        subscription.status = Subscription.Status.PROVISIONING
        subscription.activated_at = timezone.now()
        subscription.save(update_fields=['status', 'activated_at', 'updated_at'])
        
        # Trigger deployment (async in production)
        from ..services.deploy import DeployService
        deploy_result = DeployService.deploy_pod(
            pod_id=subscription.pod_id,
            email=subscription.email,
            plan=subscription.plan,
            api_key=api_key,
        )
        
        if deploy_result.get("success"):
            subscription.task_arn = deploy_result.get("task_arn", "")
            subscription.save(update_fields=['task_arn', 'updated_at'])
        
        return {
            "success": True,
            "pod_id": subscription.pod_id,
            "pod_url": subscription.pod_url,
            "status": "provisioning",
            "message": get_message("subscription.provisioning"),
        }
    
    @staticmethod
    def get_subscription_status(api_key: str) -> Dict[str, Any]:
        """
        Get current status of subscription and pod.
        
        Args:
            api_key: Subscription API key
            
        Returns:
            Dict with status details
        """
        validation = SubscriptionService.validate_api_key(api_key)
        
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}
        
        subscription = validation["subscription"]
        
        # Check pod status if provisioning
        if subscription.status == Subscription.Status.PROVISIONING:
            from ..services.deploy import DeployService
            pod_status = DeployService.get_pod_status(subscription.pod_id)
            
            if pod_status.get("status") == "running":
                subscription.status = Subscription.Status.RUNNING
                subscription.save(update_fields=['status', 'updated_at'])
        
        progress_map = {
            Subscription.Status.PENDING_ACTIVATION: 0,
            Subscription.Status.PROVISIONING: 50,
            Subscription.Status.RUNNING: 100,
            Subscription.Status.ACTIVE: 100,
            Subscription.Status.FAILED: 0,
        }
        
        return {
            "success": True,
            "status": subscription.status,
            "progress": progress_map.get(subscription.status, 0),
            "pod_id": subscription.pod_id,
            "pod_url": subscription.pod_url,
            "tokens_remaining": subscription.get_tokens_remaining(),
            "expires_at": subscription.expires_at.isoformat(),
        }
    
    @staticmethod
    def get_dashboard_data() -> Dict[str, Any]:
        """
        Get dashboard data for admin panel.
        
        Returns:
            Dict with dashboard metrics
        """
        from django.db.models import Sum, Count, Q
        from datetime import datetime
        
        subscriptions = Subscription.objects.all()
        
        # Calculate stats
        running_pods = subscriptions.filter(
            status__in=[Subscription.Status.RUNNING, Subscription.Status.ACTIVE]
        ).count()
        
        total_revenue = subscriptions.aggregate(
            total=Sum('amount_usd')
        )['total'] or Decimal('0.00')
        
        total_customers = subscriptions.values('email').distinct().count()
        
        # Recent subscriptions
        recent = subscriptions.order_by('-created_at')[:5]
        
        pods_list = [
            {
                "id": s.pod_id,
                "email": s.email,
                "plan": s.plan,
                "status": s.status,
            }
            for s in recent
        ]
        
        customers_list = [
            {
                "name": s.name or "N/A",
                "email": s.email,
                "plan": s.plan,
                "date": s.created_at.strftime("%Y-%m-%d"),
            }
            for s in recent
        ]
        
        # Plan distribution
        plan_counts = {
            "trial": subscriptions.filter(plan='trial').count(),
            "pro": subscriptions.filter(plan='pro').count(),
            "corp": subscriptions.filter(plan='corp').count(),
        }
        
        # Monthly revenue
        monthly_totals = [0] * 12
        for s in subscriptions:
            if s.created_at and s.amount_usd > 0:
                month = s.created_at.month - 1
                if 0 <= month < 12:
                    monthly_totals[month] += float(s.amount_usd)
        
        # Activity feed
        activity = []
        for s in recent[:5]:
            if s.status == Subscription.Status.RUNNING:
                activity.append({
                    "id": str(s.id),
                    "type": "pod_started",
                    "icon": "check_circle",
                    "title": f"Pod {s.pod_id} activo",
                    "description": f"Pod para {s.email} iniciado",
                    "time": s.created_at.strftime("%Y-%m-%d"),
                    "details": {
                        "pod_id": s.pod_id,
                        "email": s.email,
                        "plan": s.plan,
                    },
                })
            elif s.amount_usd > 0:
                activity.append({
                    "id": str(s.id),
                    "type": "payment",
                    "icon": "payments",
                    "title": f"Pago ${s.amount_usd} USD",
                    "description": f"Pago recibido de {s.email}",
                    "time": (s.payment_date or s.created_at).strftime("%Y-%m-%d"),
                    "details": {
                        "transaction_id": s.transaction_id,
                        "amount": str(s.amount_usd),
                        "email": s.email,
                    },
                })
            else:
                activity.append({
                    "id": str(s.id),
                    "type": "registration",
                    "icon": "person_add",
                    "title": f"Nuevo registro: {s.email}",
                    "description": f"Plan {s.plan.upper()}",
                    "time": s.created_at.strftime("%Y-%m-%d"),
                    "details": {
                        "email": s.email,
                        "plan": s.plan,
                        "ruc": s.ruc,
                    },
                })
        
        today = timezone.now().strftime("%Y-%m-%d")
        week_ago = (timezone.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        return {
            "pods": {
                "active": running_pods,
                "total": subscriptions.count(),
                "provisioning": subscriptions.filter(
                    status=Subscription.Status.PROVISIONING
                ).count(),
                "change": f"+{subscriptions.filter(created_at__date=today).count()}",
                "list": pods_list,
            },
            "revenue": {
                "amount": float(total_revenue),
                "monthly": monthly_totals,
                "change": "+23%",
                "transactions": subscriptions.filter(amount_usd__gt=0).count(),
                "average": round(
                    float(total_revenue) / max(subscriptions.filter(amount_usd__gt=0).count(), 1),
                    2
                ),
                "growth": "+23%",
            },
            "plans": plan_counts,
            "customers": {
                "total": total_customers,
                "active": subscriptions.filter(
                    status__in=[
                        Subscription.Status.RUNNING,
                        Subscription.Status.ACTIVE,
                        Subscription.Status.PROVISIONING
                    ]
                ).count(),
                "change": f"+{subscriptions.filter(created_at__date__gte=week_ago).count()}",
                "recent": customers_list,
            },
            "alerts": {
                "count": subscriptions.filter(status=Subscription.Status.FAILED).count(),
                "items": [
                    {
                        "icon": "warning",
                        "title": f"Pod {s.pod_id} error",
                        "severity": "error",
                    }
                    for s in subscriptions.filter(status=Subscription.Status.FAILED)[:5]
                ],
            },
            "activity": activity,
        }
