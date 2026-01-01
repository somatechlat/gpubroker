"""
GPUBROKER Admin API Router

Django Ninja API for GPUBROKER POD administration.
"""
from ninja import Router, Schema
from ninja.security import HttpBearer
from typing import List, Optional, Dict, Any
from datetime import datetime
from django.http import HttpRequest

from ..apps.auth.services import AdminAuthService
from ..apps.auth.models import AdminUser
from ..apps.subscriptions.services import SubscriptionService
from ..apps.subscriptions.models import Subscription
from ..services.deploy import DeployService
from ..services.geo import geo_service


# ============================================
# AUTHENTICATION
# ============================================

class AdminAuth(HttpBearer):
    """JWT Bearer authentication for admin API."""
    
    def authenticate(self, request: HttpRequest, token: str) -> Optional[AdminUser]:
        user = AdminAuthService.verify_token(token)
        if user:
            request.admin_user = user
            return user
        return None


# ============================================
# SCHEMAS
# ============================================

class LoginSchema(Schema):
    email: str
    password: str


class LoginResponseSchema(Schema):
    success: bool
    token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SubscriptionCreateSchema(Schema):
    email: str
    plan: str = "pro"
    ruc: str = ""  # Optional - only required for Ecuador
    card_last4: str = "****"
    transaction_id: str = ""
    order_id: str = ""
    amount: float = 0.0
    payment_provider: str = "unknown"
    name: str = ""
    country_code: str = ""  # ISO country code from geo-detection


class SubscriptionActivateSchema(Schema):
    api_key: str


class PodActionSchema(Schema):
    pod_id: str


class DashboardResponseSchema(Schema):
    pods: Dict[str, Any]
    revenue: Dict[str, Any]
    plans: Dict[str, int]
    customers: Dict[str, Any]
    alerts: Dict[str, Any]
    activity: List[Dict[str, Any]]


# ============================================
# ROUTERS
# ============================================

# Public router (no auth required)
public_router = Router(tags=["Public"])

# Admin router (auth required)
admin_router = Router(tags=["Admin"], auth=AdminAuth())


# ============================================
# PUBLIC ENDPOINTS
# ============================================

@public_router.get("/health")
def health_check(request):
    """Health check endpoint for ALB."""
    return {"status": "healthy", "service": "GPUBROKER Admin"}


@public_router.get("/geo/detect")
def detect_geo(request):
    """
    Detect user's country from IP for country-specific validation.
    
    Returns checkout configuration including:
    - geo: detected location info
    - show_tax_id: whether to show RUC/Cedula field
    - tax_id_label: label for the tax ID field
    - language: preferred language code
    """
    # Get client IP (handle proxies)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0].strip()
    else:
        ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    # Check for forced country setting (for testing or single-country deployments)
    from django.conf import settings
    force_country = getattr(settings, 'GPUBROKER_FORCE_COUNTRY', '')
    
    if force_country:
        # Use forced country instead of geo-detection
        requirements = geo_service.get_validation_requirements(force_country)
        return {
            'geo': {
                'country_code': force_country,
                'country_name': force_country,
                'detected': False,
                'source': 'forced',
                'is_private': False,
            },
            'validation': requirements,
            'show_tax_id': requirements['requires_tax_id'],
            'tax_id_label': requirements.get('tax_id_name', ''),
            'language': requirements.get('language', 'en'),
        }
    
    # Normal geo-detection
    config = geo_service.get_checkout_config(ip_address)
    return config


@public_router.post("/admin/login", response=LoginResponseSchema)
def admin_login(request, data: LoginSchema):
    """Admin login endpoint."""
    ip_address = request.META.get("REMOTE_ADDR")
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    
    result = AdminAuthService.login(
        email=data.email,
        password=data.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return result


@public_router.post("/subscription/create")
def create_subscription(request, data: SubscriptionCreateSchema):
    """Create subscription after payment.
    
    RUC/Cedula is only required for Ecuador (EC) registrations.
    For other countries, the ruc field can be empty.
    """
    # Determine country from request or provided country_code
    country_code = data.country_code
    if not country_code:
        # Fallback to geo-detection from IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        geo = geo_service.get_country_from_ip(ip_address)
        country_code = geo.get('country_code', 'US')
    
    # Check if RUC is required for this country
    requirements = geo_service.get_validation_requirements(country_code)
    
    if requirements['requires_tax_id'] and not data.ruc:
        return {
            "success": False,
            "error": f"{requirements['tax_id_name']} es requerido para registros desde {country_code}",
        }
    
    result = SubscriptionService.create_subscription(
        email=data.email,
        plan=data.plan,
        ruc=data.ruc,
        card_last4=data.card_last4,
        transaction_id=data.transaction_id,
        order_id=data.order_id,
        amount=data.amount,
        payment_provider=data.payment_provider,
        name=data.name,
        country_code=country_code,
    )
    return result


@public_router.post("/subscription/activate")
def activate_subscription(request, data: SubscriptionActivateSchema):
    """Activate subscription and deploy pod."""
    result = SubscriptionService.activate_subscription(data.api_key)
    return result


@public_router.get("/pod/status")
def get_pod_status(request, key: str):
    """Get pod deployment status."""
    result = SubscriptionService.get_subscription_status(key)
    return result


@public_router.post("/validate/ruc")
def validate_ruc(request, data: Dict[str, str]):
    """Validate RUC (Ecuador tax ID)."""
    ruc = data.get("ruc", "")
    
    # Basic RUC validation (13 digits)
    if not ruc or len(ruc) != 13 or not ruc.isdigit():
        return {"valid": False, "message": "RUC debe tener 13 dígitos"}
    
    # Check province code (first 2 digits)
    province = int(ruc[:2])
    if province < 1 or province > 24:
        return {"valid": False, "message": "Código de provincia inválido"}
    
    return {"valid": True, "message": "RUC válido", "type": "ruc"}


@public_router.post("/validate/cedula")
def validate_cedula(request, data: Dict[str, str]):
    """Validate Ecuadorian Cedula."""
    cedula = data.get("cedula", "")
    
    if not cedula or len(cedula) != 10 or not cedula.isdigit():
        return {"valid": False, "message": "Cédula debe tener 10 dígitos"}
    
    # Checksum validation
    province = int(cedula[:2])
    if province < 1 or province > 24:
        return {"valid": False, "message": "Código de provincia inválido"}
    
    # Luhn-like algorithm for Ecuador cedula
    coefficients = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for i, coef in enumerate(coefficients):
        val = int(cedula[i]) * coef
        if val > 9:
            val -= 9
        total += val
    
    check_digit = (10 - (total % 10)) % 10
    if check_digit != int(cedula[9]):
        return {"valid": False, "message": "Dígito verificador inválido"}
    
    return {"valid": True, "message": "Cédula válida", "type": "cedula"}


@public_router.post("/validate/identity")
def validate_identity(request, data: Dict[str, str]):
    """Validate either RUC or Cedula based on length."""
    identifier = data.get("identifier", "").strip()
    
    if len(identifier) == 13:
        result = validate_ruc(request, {"ruc": identifier})
        result["type"] = "ruc"
        return result
    elif len(identifier) == 10:
        result = validate_cedula(request, {"cedula": identifier})
        result["type"] = "cedula"
        return result
    else:
        return {
            "valid": False,
            "message": "Ingrese RUC (13 dígitos) o Cédula (10 dígitos)",
        }


# ============================================
# ADMIN ENDPOINTS (Auth Required)
# ============================================

@admin_router.get("/dashboard")
def get_dashboard(request):
    """Get dashboard data for admin panel."""
    return SubscriptionService.get_dashboard_data()


@admin_router.get("/pods")
def list_pods(request):
    """Get all pods for admin."""
    subscriptions = Subscription.objects.all().order_by('-created_at')
    
    pods = [
        {
            "id": s.pod_id,
            "subscription_id": s.subscription_id,
            "email": s.email,
            "name": s.name,
            "plan": s.plan,
            "status": s.status,
            "pod_url": s.pod_url,
            "created_at": s.created_at.isoformat(),
            "tokens_used": s.tokens_used,
            "token_limit": s.token_limit,
        }
        for s in subscriptions
    ]
    
    return {"success": True, "pods": pods}


@admin_router.post("/pod/destroy")
def destroy_pod(request, data: PodActionSchema):
    """Destroy/stop a pod."""
    from django.utils import timezone
    
    try:
        subscription = Subscription.objects.get(pod_id=data.pod_id)
        
        # Stop ECS task
        DeployService.stop_pod(data.pod_id)
        
        # Update status
        subscription.status = Subscription.Status.DESTROYED
        subscription.destroyed_at = timezone.now()
        subscription.save(update_fields=['status', 'destroyed_at', 'updated_at'])
        
        return {
            "success": True,
            "message": f"Pod {data.pod_id} destruido",
            "status": "destroyed",
        }
    except Subscription.DoesNotExist:
        return {"success": False, "error": "Pod not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@admin_router.post("/pod/start")
def start_pod(request, data: PodActionSchema):
    """Start/restart a pod."""
    try:
        subscription = Subscription.objects.get(pod_id=data.pod_id)
        
        # Deploy to ECS
        result = DeployService.deploy_pod(
            pod_id=data.pod_id,
            email=subscription.email,
            plan=subscription.plan,
            api_key=subscription.api_key,
        )
        
        if result.get("success"):
            subscription.status = Subscription.Status.PROVISIONING
            subscription.task_arn = result.get("task_arn", "")
            subscription.save(update_fields=['status', 'task_arn', 'updated_at'])
            
            return {
                "success": True,
                "message": f"Pod {data.pod_id} iniciando",
                "status": "provisioning",
                "task_arn": result.get("task_arn"),
            }
        else:
            return {"success": False, "error": result.get("error", "Deployment failed")}
            
    except Subscription.DoesNotExist:
        return {"success": False, "error": "Pod not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@admin_router.get("/pod/{pod_id}/metrics")
def get_pod_metrics(request, pod_id: str):
    """Get real AWS metrics for a pod."""
    result = DeployService.get_pod_metrics(pod_id)
    return result


@admin_router.get("/costs")
def get_costs(request):
    """Get comprehensive AWS costs and profitability metrics."""
    from decimal import Decimal
    
    # Fargate pricing (us-east-1)
    FARGATE_VCPU_HOUR = Decimal('0.04048')
    FARGATE_GB_HOUR = Decimal('0.004445')
    POD_VCPU = Decimal('0.25')
    POD_MEMORY_GB = Decimal('0.5')
    
    subscriptions = Subscription.objects.all()
    
    # Calculate revenue
    total_revenue = sum(
        float(s.amount_usd) for s in subscriptions
    )
    
    active_pods = subscriptions.filter(
        status__in=[
            Subscription.Status.RUNNING,
            Subscription.Status.ACTIVE,
            Subscription.Status.PROVISIONING
        ]
    ).count()
    
    # Estimate AWS costs (simplified)
    hours = 720  # Monthly hours
    pod_cost = float(
        (hours * POD_VCPU * FARGATE_VCPU_HOUR) +
        (hours * POD_MEMORY_GB * FARGATE_GB_HOUR)
    )
    
    aws_costs = active_pods * pod_cost
    other_costs = 10  # Fixed costs
    total_costs = aws_costs + other_costs
    profit = total_revenue - total_costs
    margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        "success": True,
        "aws_costs": {
            "total": round(aws_costs, 2),
            "total_hours": active_pods * hours,
            "pod_count": active_pods,
        },
        "profitability": {
            "revenue": round(total_revenue, 2),
            "aws_costs": round(aws_costs, 2),
            "other_costs": round(other_costs, 2),
            "total_costs": round(total_costs, 2),
            "profit": round(profit, 2),
            "margin_percent": round(margin, 1),
            "is_profitable": profit > 0,
        },
        "per_pod_estimate": {
            "vcpu": float(POD_VCPU),
            "memory_gb": float(POD_MEMORY_GB),
            "monthly_cost": round(pod_cost, 2),
        },
        "active_pods": active_pods,
        "total_revenue": round(total_revenue, 2),
        "last_updated": datetime.now().isoformat(),
    }


@admin_router.get("/customer/{email}")
def get_customer(request, email: str):
    """Get customer details by email."""
    subscriptions = Subscription.objects.filter(email=email).order_by('-created_at')
    
    if not subscriptions.exists():
        return {"error": "Customer not found"}, 404
    
    customer = subscriptions.first()
    total_paid = sum(float(s.amount_usd) for s in subscriptions)
    
    payments = [
        {
            "amount": float(s.amount_usd),
            "date": s.created_at.strftime("%Y-%m-%d"),
            "method": s.payment_provider or "PayPal",
            "description": f"Plan {s.plan.upper()}",
        }
        for s in subscriptions
        if s.amount_usd > 0
    ]
    
    return {
        "email": customer.email,
        "name": customer.name or "Cliente",
        "plan": customer.plan,
        "status": customer.status,
        "pod_id": customer.pod_id,
        "pod_status": customer.status,
        "ruc": customer.ruc,
        "created_at": customer.created_at.isoformat(),
        "total_paid": total_paid,
        "payments": payments,
    }


@admin_router.get("/transaction/{tx_id}")
def get_transaction(request, tx_id: str):
    """Get transaction details by transaction ID."""
    try:
        subscription = Subscription.objects.get(transaction_id=tx_id)
        
        return {
            "transaction_id": subscription.transaction_id,
            "amount": float(subscription.amount_usd),
            "email": subscription.email,
            "name": subscription.name,
            "plan": subscription.plan,
            "pod_id": subscription.pod_id,
            "status": "completed",
            "method": subscription.payment_provider or "PayPal",
            "created_at": subscription.created_at.isoformat(),
            "date": subscription.payment_date.strftime("%Y-%m-%d") if subscription.payment_date else "",
        }
    except Subscription.DoesNotExist:
        return {"error": "Transaction not found"}, 404


@admin_router.post("/resend-receipt")
def resend_receipt(request, data: Dict[str, Any]):
    """Resend receipt email to customer."""
    from ..services.email import EmailService
    
    email = data.get("email")
    
    if not email:
        return {"error": "Email required"}, 400
    
    # Find subscription
    try:
        subscription = Subscription.objects.filter(email=email).order_by('-created_at').first()
        if subscription:
            EmailService.send_payment_receipt(
                to_email=email,
                api_key=subscription.api_key,
                plan=subscription.plan,
                pod_id=subscription.pod_id,
                pod_url=subscription.pod_url,
                transaction_id=subscription.transaction_id,
                order_id=subscription.order_id,
                amount=float(subscription.amount_usd),
                payment_provider=subscription.payment_provider,
                name=subscription.name,
                ruc=subscription.ruc,
            )
            return {"success": True, "message": f"Receipt sent to {email}"}
    except Exception:
        pass
    
    return {"success": True, "message": f"Receipt logged for {email}"}


@admin_router.get("/customers")
def list_customers(request):
    """Get all customers for admin."""
    subscriptions = Subscription.objects.all().order_by('-created_at')
    
    # Group by email to get unique customers
    customers_dict = {}
    for s in subscriptions:
        if s.email not in customers_dict:
            customers_dict[s.email] = {
                "email": s.email,
                "name": s.name or s.email.split('@')[0],
                "plan": s.plan,
                "status": s.status,
                "pod_id": s.pod_id,
                "ruc": s.ruc,
                "created_at": s.created_at.isoformat(),
                "total_paid": float(s.amount_usd),
            }
        else:
            customers_dict[s.email]["total_paid"] += float(s.amount_usd)
    
    customers = list(customers_dict.values())
    
    return {"success": True, "customers": customers}


@admin_router.get("/billing")
def list_transactions(request):
    """Get all transactions for admin."""
    subscriptions = Subscription.objects.filter(
        amount_usd__gt=0
    ).order_by('-created_at')
    
    transactions = [
        {
            "id": s.transaction_id or f"TXN-{s.subscription_id[:8]}",
            "email": s.email,
            "name": s.name or s.email.split('@')[0],
            "plan": s.plan,
            "amount": float(s.amount_usd),
            "method": s.payment_provider or "PayPal",
            "status": "completed",
            "pod_id": s.pod_id,
            "order_id": s.order_id,
            "created_at": s.created_at.isoformat(),
            "date": s.payment_date.strftime("%Y-%m-%d") if s.payment_date else s.created_at.strftime("%Y-%m-%d"),
        }
        for s in subscriptions
    ]
    
    return {"success": True, "transactions": transactions}


# ============================================
# PAYPAL PAYMENT ENDPOINTS
# ============================================

class PayPalOrderSchema(Schema):
    email: str
    plan: str
    amount: float
    ruc: str = ""
    name: str = ""


class PayPalCaptureSchema(Schema):
    order_id: str


@public_router.post("/payment/paypal")
def create_paypal_order(request, data: PayPalOrderSchema):
    """Create PayPal order for subscription payment."""
    from ..services.payments.paypal import paypal_service
    
    result = paypal_service.create_payment_for_subscription(
        email=data.email,
        plan=data.plan,
        amount_usd=data.amount,
        ruc=data.ruc,
        name=data.name,
    )
    return result


@public_router.post("/payment/paypal/capture/{order_id}")
def capture_paypal_order(request, order_id: str):
    """Capture approved PayPal order."""
    from ..services.payments.paypal import paypal_service
    
    result = paypal_service.capture_order(order_id)
    return result


@public_router.get("/payment/paypal/status")
def get_paypal_status(request):
    """Get PayPal configuration status."""
    from ..services.payments.paypal import paypal_service
    
    return paypal_service.get_config_status()


# ============================================
# MODE MANAGEMENT ENDPOINTS
# ============================================

class ModeSwitchSchema(Schema):
    mode: str  # 'sandbox' or 'live'
    confirm: bool = False  # Must be True to switch to live


@public_router.get("/mode")
def get_current_mode(request):
    """Get current global mode status (public for UI display)."""
    from ..services.mode import mode_service
    
    return mode_service.get_status()


@public_router.get("/mode/config")
def get_mode_config(request):
    """Get all mode-aware configurations (for debugging/admin)."""
    from ..services.mode import mode_service
    
    return mode_service.get_all_configs()


@admin_router.get("/mode")
def admin_get_mode(request):
    """Get current mode status (authenticated)."""
    from ..services.mode import mode_service
    
    status = mode_service.get_status()
    status['can_switch'] = True  # Admin can always switch
    return status


@admin_router.post("/mode")
def admin_switch_mode(request, data: ModeSwitchSchema):
    """
    Switch global mode between sandbox and live.
    
    Requires admin authentication.
    When switching to 'live', confirm=True is required.
    """
    from ..services.mode import mode_service
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Validate mode
    if data.mode not in ('sandbox', 'live'):
        return {
            "success": False,
            "error": f"Invalid mode: {data.mode}. Must be 'sandbox' or 'live'"
        }
    
    # Require confirmation for switching to live
    if data.mode == 'live' and not data.confirm:
        return {
            "success": False,
            "error": "Switching to LIVE mode requires confirm=true",
            "warning": "Live mode will process REAL payments and provision REAL resources!",
            "current_mode": mode_service.current_mode,
        }
    
    # Get admin user for logging
    admin_email = getattr(request, 'admin_user', {})
    if hasattr(admin_email, 'email'):
        admin_email = admin_email.email
    else:
        admin_email = 'unknown'
    
    old_mode = mode_service.current_mode
    
    # Switch mode
    try:
        mode_service.set_mode(data.mode)
        
        logger.warning(
            f"Mode switched by admin: {old_mode} -> {data.mode}",
            extra={
                'admin': admin_email,
                'old_mode': old_mode,
                'new_mode': data.mode,
            }
        )
        
        return {
            "success": True,
            "message": f"Mode switched from {old_mode} to {data.mode}",
            "old_mode": old_mode,
            "new_mode": data.mode,
            "admin": admin_email,
            "status": mode_service.get_status(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "current_mode": mode_service.current_mode,
        }

