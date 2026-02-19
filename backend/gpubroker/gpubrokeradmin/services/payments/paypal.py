"""
PayPal Payment Service for GPUBROKER Admin

Uses PayPal REST API v2 (Orders) for secure payments.
Uses centralized config for mode switching.

Flow:
    1. Frontend calls create_order() to initiate payment
    2. User is redirected to PayPal to approve payment
    3. PayPal redirects to callback with order ID
    4. capture_order() captures the payment and returns transaction details
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from gpubrokeradmin.apps.subscriptions.models import PaymentTransaction, Payment
from gpubrokeradmin.common.messages import get_message

logger = logging.getLogger('gpubrokeradmin.payments.paypal')


class PayPalService:
    """
    PayPal REST API v2 integration service.
    
    Uses centralized config for credentials and mode.
    """
    
    # PayPal API base URLs
    API_URLS = {
        'sandbox': 'https://api-m.sandbox.paypal.com',
        'live': 'https://api-m.paypal.com',
    }
    
    # Plan descriptions for PayPal order
    PLAN_DESCRIPTIONS = {
        'trial': 'GPUBROKER POD - Trial',
        'basic': 'GPUBROKER POD - Basic Plan',
        'pro': 'GPUBROKER POD - Professional Plan',
        'corp': 'GPUBROKER POD - Corporate Plan',
        'enterprise': 'GPUBROKER POD - Enterprise Plan',
    }
    
    def __init__(self):
        """Initialize PayPal service using centralized config."""
        from gpubrokeradmin.services.config import config
        self._config = config
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        logger.info("PayPal service initialized (using centralized config)")
    
    @property
    def client_id(self) -> str:
        """Get client ID for current mode."""
        return self._config.paypal.client_id
    
    @property
    def client_secret(self) -> str:
        """Get client secret for current mode."""
        return self._config.paypal.client_secret
    
    @property
    def mode(self) -> str:
        """Get current mode."""
        return self._config.mode.current
    
    @property
    def api_base(self) -> str:
        """Get the appropriate PayPal API base URL."""
        return self._config.paypal.api_base
    
    @property
    def is_configured(self) -> bool:
        """Check if PayPal credentials are configured."""
        return self._config.paypal.is_configured
    
    def get_config_status(self) -> dict:
        """Get PayPal configuration status."""
        return {
            'configured': self.is_configured,
            'mode': self.mode,
            'client_id_set': bool(self.client_id),
            'client_secret_set': bool(self.client_secret),
            'api_base': self.api_base,
        }

    def _get_access_token(self) -> Optional[str]:
        """
        Get PayPal OAuth2 access token.
        
        Caches token until expiry.
        
        Returns:
            Access token string or None on failure.
        """
        if not self.is_configured:
            logger.error('PayPal not configured - missing credentials')
            return None
        
        # Check if cached token is still valid
        if self._access_token and self._token_expires:
            if datetime.now(timezone.utc) < self._token_expires:
                return self._access_token
        
        url = f'{self.api_base}/v1/oauth2/token'
        
        try:
            response = requests.post(
                url,
                auth=(self.client_id, self.client_secret),
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data={'grant_type': 'client_credentials'},
                timeout=10,
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get('access_token')
                # Token typically expires in 9 hours, cache for 8
                expires_in = data.get('expires_in', 32400)
                from datetime import timedelta
                self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 3600)
                return self._access_token
            else:
                logger.error(f'PayPal auth error: {response.status_code} - {response.text}')
                return None
        except requests.RequestException as e:
            logger.exception(f'PayPal auth exception: {e}')
            return None

    def _persist_transaction(
        self,
        order_id: str,
        status: str,
        *,
        amount_usd: float = 0.0,
        transaction_id: str = "",
        email: str = "",
        name: str = "",
        plan: str = "",
        mode: str = "",
        metadata: Optional[dict] = None,
        raw_request: Optional[dict] = None,
        raw_response: Optional[dict] = None,
        error_message: str = "",
    ) -> PaymentTransaction:
        """
        Persist a payment transaction event for observability/replay.
        """
        metadata = metadata or {}
        raw_request = raw_request or {}
        raw_response = raw_response or {}
        
        defaults = {
            "status": status,
            "transaction_id": transaction_id,
            "amount_usd": amount_usd,
            "customer_email": email,
            "customer_name": name,
            "plan": plan,
            "mode": mode or self.mode,
            "metadata": metadata,
            "raw_request": raw_request,
            "raw_response": raw_response,
            "error_message": error_message,
            "provider": Payment.Provider.PAYPAL,
        }
        transaction, created = PaymentTransaction.objects.get_or_create(
            order_id=order_id,
            defaults=defaults,
        )
        if not created:
            for field, value in defaults.items():
                if value not in (None, "", {}):
                    setattr(transaction, field, value)
            transaction.save(update_fields=[
                "status",
                "transaction_id",
                "amount_usd",
                "customer_email",
                "customer_name",
                "plan",
                "mode",
                "metadata",
                "raw_request",
                "raw_response",
                "error_message",
                "updated_at",
            ])
        return transaction
    
    def create_order(
        self,
        email: str,
        plan: str,
        amount_usd: float,
        return_url: str,
        cancel_url: str,
        ruc: str = '',
        name: str = '',
    ) -> dict:
        """
        Create a PayPal order for the subscription.
        
        Args:
            email: Customer email
            plan: Subscription plan (trial, basic, pro, corp, enterprise)
            amount_usd: Amount in USD
            return_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
            ruc: Customer RUC (Ecuador tax ID)
            name: Customer name
        
        Returns:
            dict with success, order_id, approval_url or error
        """
        if not self.is_configured:
            return {
                'success': False,
                'error': get_message("paypal.not_configured"),
            }
        
        access_token = self._get_access_token()
        if not access_token:
            return {'success': False, 'error': get_message("paypal.auth_failed")}
        
        # Generate unique reference ID
        reference_id = hashlib.sha256(
            f'{email}:{plan}:{datetime.now(timezone.utc).isoformat()}'.encode()
        ).hexdigest()[:16]
        
        url = f'{self.api_base}/v2/checkout/orders'
        
        order_data = {
            'intent': 'CAPTURE',
            'purchase_units': [
                {
                    'reference_id': reference_id,
                    'description': self.PLAN_DESCRIPTIONS.get(plan, 'GPUBROKER POD Subscription'),
                    'amount': {
                        'currency_code': 'USD',
                        'value': f'{amount_usd:.2f}',
                    },
                }
            ],
            'application_context': {
                'brand_name': 'GPUBROKER',
                'landing_page': 'NO_PREFERENCE',
                'user_action': 'PAY_NOW',
                'shipping_preference': 'NO_SHIPPING',
                'locale': 'es-EC',
                'return_url': return_url,
                'cancel_url': cancel_url,
            },
        }
        
        try:
            response = requests.post(
                url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}',
                },
                json=order_data,
                timeout=15,
            )
            
            if response.status_code in [200, 201]:
                order = response.json()
                order_id = order.get('id')
                
                # Find approval URL
                approval_url = ''
                for link in order.get('links', []):
                    if link.get('rel') == 'approve':
                        approval_url = link.get('href')
                        break
                
                # Store pending transaction
                self._persist_transaction(
                    order_id=order_id,
                    status=Payment.Status.PENDING,
                    amount_usd=amount_usd,
                    email=email,
                    name=name,
                    plan=plan,
                    mode=self.mode,
                    metadata={
                        "ruc": ruc,
                        "reference_id": reference_id,
                    },
                    raw_request=order_data,
                    raw_response=order,
                )
                
                logger.info(f'PayPal order created: {order_id} for {email}')
                return {
                    'success': True,
                    'order_id': order_id,
                    'approval_url': approval_url,
                }
            else:
                error_data = response.json()
                logger.error(f'PayPal order creation failed: {error_data}')
                return {
                    'success': False,
                    'error': error_data.get('message', get_message("paypal.create_failed")),
                    'details': error_data,
                }
        except requests.RequestException as e:
            logger.exception(f'PayPal API error: {e}')
            self._persist_transaction(
                order_id=reference_id,
                status=Payment.Status.FAILED,
                amount_usd=amount_usd,
                email=email,
                name=name,
                plan=plan,
                mode=self.mode,
                metadata={'ruc': ruc},
                raw_request=order_data,
                raw_response={},
                error_message=str(e),
            )
            return {'success': False, 'error': get_message("paypal.api_error", error=str(e))}

    def capture_order(self, order_id: str) -> dict:
        """
        Capture a PayPal order after user approval.
        
        Args:
            order_id: PayPal order ID from the callback
        
        Returns:
            dict with success, transaction_id, email, plan, amount or error
        """
        if not self.is_configured:
            return {'success': False, 'error': get_message("paypal.not_configured")}
        
        access_token = self._get_access_token()
        if not access_token:
            return {'success': False, 'error': get_message("paypal.auth_failed")}
        
        url = f'{self.api_base}/v2/checkout/orders/{order_id}/capture'
        
        try:
            response = requests.post(
                url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}',
                },
                timeout=15,
            )
            
            if response.status_code in [200, 201]:
                capture_data = response.json()
                status = capture_data.get('status')
                
                # Record capture attempt
                self._persist_transaction(
                    order_id=order_id,
                    status=Payment.Status.PROCESSING,
                    raw_response=capture_data,
                )
                
                if status == 'COMPLETED':
                    # Get capture ID from response
                    capture_id = ''
                    payments = capture_data.get('purchase_units', [{}])[0].get('payments', {})
                    captures = payments.get('captures', [])
                    if captures:
                        capture_id = captures[0].get('id', '')
                    
                    pending = PaymentTransaction.objects.filter(order_id=order_id).first()
                    metadata = pending.metadata if pending else {}
                    email = pending.customer_email if pending else ''
                    plan = pending.plan if pending else 'pro'
                    amount = pending.amount_usd if pending else 0
                    ruc = metadata.get('ruc', '')
                    name = pending.customer_name if pending else ''
                    
                    self._persist_transaction(
                        order_id=order_id,
                        status=Payment.Status.COMPLETED,
                        transaction_id=capture_id,
                        amount_usd=float(amount or 0),
                        email=email,
                        name=name,
                        plan=plan,
                        raw_response=capture_data,
                    )
                    
                    logger.info(f'PayPal payment captured: {capture_id} for order {order_id}')
                    return {
                        'success': True,
                        'status': 'COMPLETED',
                        'transaction_id': capture_id,
                        'order_id': order_id,
                        'email': email,
                        'plan': plan,
                        'amount': float(amount or 0),
                        'ruc': ruc,
                        'name': name,
                    }
                else:
                    logger.warning(f'PayPal payment not completed: {status}')
                    self._persist_transaction(
                        order_id=order_id,
                        status=Payment.Status.FAILED,
                        raw_response=capture_data,
                        error_message=get_message("paypal.capture_not_completed", status=status),
                    )
                    return {
                        'success': False,
                        'error': get_message("paypal.capture_not_completed", status=status),
                        'status': status,
                    }
            else:
                error_data = response.json()
                logger.error(f'PayPal capture failed: {error_data}')
                self._persist_transaction(
                    order_id=order_id,
                    status=Payment.Status.FAILED,
                    raw_response=error_data,
                    error_message=error_data.get('message', ''),
                )
                return {
                    'success': False,
                    'error': error_data.get('message', get_message("paypal.capture_failed")),
                    'details': error_data,
                }
        except requests.RequestException as e:
            logger.exception(f'PayPal capture error: {e}')
            self._persist_transaction(
                order_id=order_id,
                status=Payment.Status.FAILED,
                raw_response={},
                error_message=str(e),
            )
            return {'success': False, 'error': get_message("paypal.capture_failed")}
    
    def create_payment_for_subscription(
        self,
        email: str,
        plan: str,
        amount_usd: float,
        ruc: str = '',
        name: str = '',
        base_url: str = '',
    ) -> dict:
        """
        Convenience function to create a PayPal payment for subscription.
        
        This is the main entry point called from the API endpoint.
        
        Args:
            email: Customer email
            plan: Subscription plan
            amount_usd: Amount in USD
            ruc: Customer RUC
            name: Customer name
            base_url: Base URL for callbacks (defaults to GPUBROKER_ADMIN_URL)
        
        Returns:
            dict with success, payment_url (approval_url), order_id or error
        """
        if not base_url:
            base_url = self._config.domain.admin_url
        
        return_url = f'{base_url}/payment/paypal/callback'
        cancel_url = f'{base_url}/checkout?plan={plan}&error=cancelled'
        
        result = self.create_order(email, plan, amount_usd, return_url, cancel_url, ruc, name)
        
        if result['success']:
            return {
                'success': True,
                'payment_url': result['approval_url'],
                'order_id': result['order_id'],
            }
        return result
    
    def handle_payment_callback(self, order_id: str) -> dict:
        """
        Handle PayPal callback after user approves payment.
        
        Args:
            order_id: PayPal order ID from callback URL
        
        Returns:
            dict with success, transaction details or error
        """
        return self.capture_order(order_id)
    
    def get_pending_transaction(self, order_id: str) -> Optional[dict]:
        """
        Get pending transaction data by order ID.
        
        Args:
            order_id: PayPal order ID
        
        Returns:
            Transaction data dict or None
        """
        transaction = PaymentTransaction.objects.filter(order_id=order_id).first()
        if not transaction:
            return None
        return {
            "order_id": transaction.order_id,
            "transaction_id": transaction.transaction_id,
            "status": transaction.status,
            "provider": transaction.provider,
            "email": transaction.customer_email,
            "plan": transaction.plan,
            "amount": float(transaction.amount_usd),
            "metadata": transaction.metadata,
        }


# Singleton instance
paypal_service = PayPalService()
