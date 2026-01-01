"""
Stripe Integration Service - Real Stripe API integration.

Handles:
- Customer management
- SetupIntent for secure card storage
- Subscription lifecycle
- Webhook processing
- Invoice management

SANDBOX MODE: Uses Stripe test keys (sk_test_*, pk_test_*)
LIVE MODE: Uses Stripe live keys (sk_live_*, pk_live_*)
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple

import stripe
from django.conf import settings
from django.core.cache import cache
from asgiref.sync import sync_to_async

from .models import Plan, Subscription, PaymentMethod, Invoice

logger = logging.getLogger('gpubroker.billing.stripe')


class StripeService:
    """
    Stripe integration service.
    
    Automatically uses test or live keys based on GPUBROKER_MODE setting.
    """
    
    def __init__(self):
        """Initialize Stripe with appropriate keys."""
        self.mode = getattr(settings, 'GPUBROKER_MODE', 'sandbox')
        
        # Get Stripe keys from settings
        if self.mode == 'live':
            self.secret_key = getattr(settings, 'STRIPE_SECRET_KEY_LIVE', '')
            self.publishable_key = getattr(settings, 'STRIPE_PUBLISHABLE_KEY_LIVE', '')
        else:
            # Sandbox mode - use test keys
            self.secret_key = getattr(settings, 'STRIPE_SECRET_KEY_TEST', '')
            self.publishable_key = getattr(settings, 'STRIPE_PUBLISHABLE_KEY_TEST', '')
        
        # Configure Stripe
        stripe.api_key = self.secret_key
        stripe.api_version = '2023-10-16'
        
        self.webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        
        logger.info(f"Stripe initialized in {self.mode} mode")
    
    @property
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return bool(self.secret_key and self.publishable_key)
    
    # ==========================================
    # Customer Management
    # ==========================================
    
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        Create a Stripe customer.
        
        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata
            
        Returns:
            Stripe customer ID or None
        """
        if not self.is_configured:
            logger.warning("Stripe not configured, skipping customer creation")
            return None
        
        try:
            customer = await sync_to_async(stripe.Customer.create)(
                email=email,
                name=name,
                metadata=metadata or {},
            )
            logger.info(f"Created Stripe customer: {customer.id}")
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            return None
    
    async def get_customer(self, customer_id: str) -> Optional[Dict]:
        """Get Stripe customer by ID."""
        if not self.is_configured:
            return None
        
        try:
            customer = await sync_to_async(stripe.Customer.retrieve)(customer_id)
            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "default_payment_method": customer.invoice_settings.default_payment_method,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get Stripe customer: {e}")
            return None
    
    async def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        default_payment_method: Optional[str] = None,
    ) -> bool:
        """Update Stripe customer."""
        if not self.is_configured:
            return False
        
        try:
            update_data = {}
            if email:
                update_data['email'] = email
            if name:
                update_data['name'] = name
            if default_payment_method:
                update_data['invoice_settings'] = {
                    'default_payment_method': default_payment_method
                }
            
            await sync_to_async(stripe.Customer.modify)(customer_id, **update_data)
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe customer: {e}")
            return False
    
    # ==========================================
    # SetupIntent (Card Storage)
    # ==========================================
    
    async def create_setup_intent(
        self,
        customer_id: str,
        payment_method_types: List[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Create a SetupIntent for secure card storage.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_types: Allowed payment methods
            metadata: Additional metadata
            
        Returns:
            Dict with client_secret and setup_intent_id
        """
        if not self.is_configured:
            logger.warning("Stripe not configured, returning mock SetupIntent")
            return {
                "client_secret": "seti_mock_client_secret",
                "setup_intent_id": "seti_mock_id",
                "publishable_key": self.publishable_key or "pk_test_mock",
            }
        
        try:
            setup_intent = await sync_to_async(stripe.SetupIntent.create)(
                customer=customer_id,
                payment_method_types=payment_method_types or ['card'],
                metadata=metadata or {},
            )
            
            return {
                "client_secret": setup_intent.client_secret,
                "setup_intent_id": setup_intent.id,
                "publishable_key": self.publishable_key,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create SetupIntent: {e}")
            return None
    
    async def confirm_setup_intent(self, setup_intent_id: str) -> Optional[Dict]:
        """Get SetupIntent status after confirmation."""
        if not self.is_configured:
            return None
        
        try:
            setup_intent = await sync_to_async(stripe.SetupIntent.retrieve)(setup_intent_id)
            return {
                "id": setup_intent.id,
                "status": setup_intent.status,
                "payment_method": setup_intent.payment_method,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve SetupIntent: {e}")
            return None

    
    # ==========================================
    # Payment Methods
    # ==========================================
    
    async def get_payment_method(self, payment_method_id: str) -> Optional[Dict]:
        """Get payment method details."""
        if not self.is_configured:
            return None
        
        try:
            pm = await sync_to_async(stripe.PaymentMethod.retrieve)(payment_method_id)
            return {
                "id": pm.id,
                "type": pm.type,
                "card_brand": pm.card.brand if pm.card else None,
                "card_last4": pm.card.last4 if pm.card else None,
                "card_exp_month": pm.card.exp_month if pm.card else None,
                "card_exp_year": pm.card.exp_year if pm.card else None,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get payment method: {e}")
            return None
    
    async def attach_payment_method(
        self,
        payment_method_id: str,
        customer_id: str,
    ) -> bool:
        """Attach a payment method to a customer."""
        if not self.is_configured:
            return True  # Mock success in sandbox
        
        try:
            await sync_to_async(stripe.PaymentMethod.attach)(
                payment_method_id,
                customer=customer_id,
            )
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to attach payment method: {e}")
            return False
    
    async def detach_payment_method(self, payment_method_id: str) -> bool:
        """Detach a payment method from customer."""
        if not self.is_configured:
            return True
        
        try:
            await sync_to_async(stripe.PaymentMethod.detach)(payment_method_id)
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to detach payment method: {e}")
            return False
    
    async def list_payment_methods(
        self,
        customer_id: str,
        type: str = 'card',
    ) -> List[Dict]:
        """List customer's payment methods."""
        if not self.is_configured:
            return []
        
        try:
            methods = await sync_to_async(stripe.PaymentMethod.list)(
                customer=customer_id,
                type=type,
            )
            return [
                {
                    "id": pm.id,
                    "type": pm.type,
                    "card_brand": pm.card.brand if pm.card else None,
                    "card_last4": pm.card.last4 if pm.card else None,
                    "card_exp_month": pm.card.exp_month if pm.card else None,
                    "card_exp_year": pm.card.exp_year if pm.card else None,
                }
                for pm in methods.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list payment methods: {e}")
            return []
    
    # ==========================================
    # Subscriptions
    # ==========================================
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        payment_method_id: Optional[str] = None,
        trial_days: int = 0,
        metadata: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Create a Stripe subscription.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            payment_method_id: Payment method to use
            trial_days: Trial period in days
            metadata: Additional metadata
            
        Returns:
            Subscription details or None
        """
        if not self.is_configured:
            logger.warning("Stripe not configured, returning mock subscription")
            return {
                "id": "sub_mock_id",
                "status": "active",
                "current_period_start": datetime.now(timezone.utc),
                "current_period_end": datetime.now(timezone.utc),
                "client_secret": None,
                "requires_action": False,
            }
        
        try:
            sub_data = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata or {},
                "payment_behavior": "default_incomplete",
                "payment_settings": {
                    "save_default_payment_method": "on_subscription",
                },
                "expand": ["latest_invoice.payment_intent"],
            }
            
            if payment_method_id:
                sub_data["default_payment_method"] = payment_method_id
            
            if trial_days > 0:
                sub_data["trial_period_days"] = trial_days
            
            subscription = await sync_to_async(stripe.Subscription.create)(**sub_data)
            
            # Check if payment requires action (3D Secure)
            requires_action = False
            client_secret = None
            
            if subscription.latest_invoice and subscription.latest_invoice.payment_intent:
                pi = subscription.latest_invoice.payment_intent
                if pi.status == 'requires_action':
                    requires_action = True
                    client_secret = pi.client_secret
            
            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(
                    subscription.current_period_start, tz=timezone.utc
                ),
                "current_period_end": datetime.fromtimestamp(
                    subscription.current_period_end, tz=timezone.utc
                ),
                "client_secret": client_secret,
                "requires_action": requires_action,
            }
        except stripe.error.CardError as e:
            logger.error(f"Card error creating subscription: {e}")
            return {"error": str(e.user_message), "code": e.code}
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            return None
    
    async def get_subscription(self, subscription_id: str) -> Optional[Dict]:
        """Get subscription details."""
        if not self.is_configured:
            return None
        
        try:
            sub = await sync_to_async(stripe.Subscription.retrieve)(subscription_id)
            return {
                "id": sub.id,
                "status": sub.status,
                "current_period_start": datetime.fromtimestamp(
                    sub.current_period_start, tz=timezone.utc
                ),
                "current_period_end": datetime.fromtimestamp(
                    sub.current_period_end, tz=timezone.utc
                ),
                "cancel_at_period_end": sub.cancel_at_period_end,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get subscription: {e}")
            return None
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_immediately: bool = False,
    ) -> bool:
        """Cancel a subscription."""
        if not self.is_configured:
            return True
        
        try:
            if cancel_immediately:
                await sync_to_async(stripe.Subscription.delete)(subscription_id)
            else:
                await sync_to_async(stripe.Subscription.modify)(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return False
    
    async def update_subscription(
        self,
        subscription_id: str,
        price_id: Optional[str] = None,
        payment_method_id: Optional[str] = None,
    ) -> bool:
        """Update subscription (change plan or payment method)."""
        if not self.is_configured:
            return True
        
        try:
            update_data = {}
            
            if price_id:
                # Get current subscription to find item ID
                sub = await sync_to_async(stripe.Subscription.retrieve)(subscription_id)
                if sub.items.data:
                    update_data['items'] = [{
                        'id': sub.items.data[0].id,
                        'price': price_id,
                    }]
            
            if payment_method_id:
                update_data['default_payment_method'] = payment_method_id
            
            if update_data:
                await sync_to_async(stripe.Subscription.modify)(
                    subscription_id,
                    **update_data,
                )
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription: {e}")
            return False

    
    # ==========================================
    # Invoices
    # ==========================================
    
    async def get_upcoming_invoice(self, customer_id: str) -> Optional[Dict]:
        """Get upcoming invoice for customer."""
        if not self.is_configured:
            return None
        
        try:
            invoice = await sync_to_async(stripe.Invoice.upcoming)(customer=customer_id)
            return {
                "amount_due": invoice.amount_due / 100,  # Convert from cents
                "currency": invoice.currency,
                "period_start": datetime.fromtimestamp(
                    invoice.period_start, tz=timezone.utc
                ) if invoice.period_start else None,
                "period_end": datetime.fromtimestamp(
                    invoice.period_end, tz=timezone.utc
                ) if invoice.period_end else None,
                "lines": [
                    {
                        "description": line.description,
                        "amount": line.amount / 100,
                    }
                    for line in invoice.lines.data
                ],
            }
        except stripe.error.InvalidRequestError:
            # No upcoming invoice
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get upcoming invoice: {e}")
            return None
    
    async def list_invoices(
        self,
        customer_id: str,
        limit: int = 10,
    ) -> List[Dict]:
        """List customer's invoices."""
        if not self.is_configured:
            return []
        
        try:
            invoices = await sync_to_async(stripe.Invoice.list)(
                customer=customer_id,
                limit=limit,
            )
            return [
                {
                    "id": inv.id,
                    "number": inv.number,
                    "status": inv.status,
                    "amount_due": inv.amount_due / 100,
                    "amount_paid": inv.amount_paid / 100,
                    "currency": inv.currency,
                    "created": datetime.fromtimestamp(inv.created, tz=timezone.utc),
                    "due_date": datetime.fromtimestamp(inv.due_date, tz=timezone.utc) if inv.due_date else None,
                    "paid_at": datetime.fromtimestamp(inv.status_transitions.paid_at, tz=timezone.utc) if inv.status_transitions.paid_at else None,
                    "pdf_url": inv.invoice_pdf,
                    "hosted_invoice_url": inv.hosted_invoice_url,
                }
                for inv in invoices.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list invoices: {e}")
            return []
    
    # ==========================================
    # Webhook Processing
    # ==========================================
    
    def verify_webhook(self, payload: bytes, signature: str) -> Optional[Dict]:
        """
        Verify and parse Stripe webhook.
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header
            
        Returns:
            Parsed event or None if invalid
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured")
            return None
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret,
            )
            return {
                "id": event.id,
                "type": event.type,
                "data": event.data.object,
            }
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse webhook: {e}")
            return None
    
    async def handle_webhook_event(self, event: Dict) -> bool:
        """
        Handle a verified webhook event.
        
        Args:
            event: Parsed webhook event
            
        Returns:
            True if handled successfully
        """
        event_type = event.get('type')
        data = event.get('data', {})
        
        handlers = {
            'customer.subscription.created': self._handle_subscription_created,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_deleted,
            'invoice.paid': self._handle_invoice_paid,
            'invoice.payment_failed': self._handle_invoice_payment_failed,
            'payment_method.attached': self._handle_payment_method_attached,
            'payment_method.detached': self._handle_payment_method_detached,
        }
        
        handler = handlers.get(event_type)
        if handler:
            return await handler(data)
        
        logger.debug(f"Unhandled webhook event type: {event_type}")
        return True
    
    async def _handle_subscription_created(self, data: Dict) -> bool:
        """Handle subscription.created webhook."""
        logger.info(f"Subscription created: {data.get('id')}")
        # Update local subscription record
        return True
    
    async def _handle_subscription_updated(self, data: Dict) -> bool:
        """Handle subscription.updated webhook."""
        stripe_sub_id = data.get('id')
        status = data.get('status')
        
        try:
            subscription = await sync_to_async(
                Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).first
            )()
            
            if subscription:
                subscription.status = status
                subscription.current_period_start = datetime.fromtimestamp(
                    data.get('current_period_start'), tz=timezone.utc
                )
                subscription.current_period_end = datetime.fromtimestamp(
                    data.get('current_period_end'), tz=timezone.utc
                )
                subscription.cancel_at_period_end = data.get('cancel_at_period_end', False)
                await sync_to_async(subscription.save)()
                logger.info(f"Updated subscription {stripe_sub_id} to status {status}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to handle subscription update: {e}")
            return False
    
    async def _handle_subscription_deleted(self, data: Dict) -> bool:
        """Handle subscription.deleted webhook."""
        stripe_sub_id = data.get('id')
        
        try:
            subscription = await sync_to_async(
                Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).first
            )()
            
            if subscription:
                subscription.status = Subscription.Status.CANCELED
                subscription.canceled_at = datetime.now(timezone.utc)
                await sync_to_async(subscription.save)()
                logger.info(f"Canceled subscription {stripe_sub_id}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to handle subscription deletion: {e}")
            return False
    
    async def _handle_invoice_paid(self, data: Dict) -> bool:
        """Handle invoice.paid webhook."""
        logger.info(f"Invoice paid: {data.get('id')}")
        # Could trigger email notification here
        return True
    
    async def _handle_invoice_payment_failed(self, data: Dict) -> bool:
        """Handle invoice.payment_failed webhook."""
        logger.warning(f"Invoice payment failed: {data.get('id')}")
        # Could trigger notification to user
        return True
    
    async def _handle_payment_method_attached(self, data: Dict) -> bool:
        """Handle payment_method.attached webhook."""
        logger.info(f"Payment method attached: {data.get('id')}")
        return True
    
    async def _handle_payment_method_detached(self, data: Dict) -> bool:
        """Handle payment_method.detached webhook."""
        pm_id = data.get('id')
        
        try:
            await sync_to_async(
                PaymentMethod.objects.filter(stripe_payment_method_id=pm_id).update
            )(is_active=False)
            logger.info(f"Deactivated payment method {pm_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to handle payment method detachment: {e}")
            return False
    
    # ==========================================
    # Products and Prices (Plan Sync)
    # ==========================================
    
    async def sync_plans_from_stripe(self) -> int:
        """
        Sync plans from Stripe products/prices.
        
        Returns:
            Number of plans synced
        """
        if not self.is_configured:
            return 0
        
        try:
            # Get all active products
            products = await sync_to_async(stripe.Product.list)(active=True)
            
            synced = 0
            for product in products.data:
                # Get prices for this product
                prices = await sync_to_async(stripe.Price.list)(
                    product=product.id,
                    active=True,
                )
                
                for price in prices.data:
                    # Map to local plan
                    tier = product.metadata.get('tier', 'basic')
                    
                    plan, created = await sync_to_async(Plan.objects.update_or_create)(
                        stripe_product_id=product.id,
                        defaults={
                            'name': product.name,
                            'tier': tier,
                            'stripe_price_id': price.id,
                            'price_monthly': Decimal(price.unit_amount / 100) if price.recurring.interval == 'month' else Decimal('0'),
                            'price_annual': Decimal(price.unit_amount / 100) if price.recurring.interval == 'year' else Decimal('0'),
                            'currency': price.currency.upper(),
                            'description': product.description or '',
                            'features': product.metadata,
                        }
                    )
                    synced += 1
                    logger.info(f"Synced plan: {product.name}")
            
            return synced
        except stripe.error.StripeError as e:
            logger.error(f"Failed to sync plans from Stripe: {e}")
            return 0


# Singleton instance
_stripe_service: Optional[StripeService] = None


def get_stripe_service() -> StripeService:
    """Get Stripe service singleton."""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service
