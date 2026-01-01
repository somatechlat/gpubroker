"""
Billing Admin Configuration.
"""
from django.contrib import admin
from .models import Plan, Subscription, PaymentMethod, Invoice, UsageRecord


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Admin for subscription plans."""
    
    list_display = ['name', 'tier', 'price_monthly', 'price_annual', 'tokens_monthly', 'is_active', 'is_popular']
    list_filter = ['tier', 'is_active', 'is_popular']
    search_fields = ['name', 'description']
    ordering = ['display_order']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'tier', 'description')
        }),
        ('Pricing', {
            'fields': ('price_monthly', 'price_annual', 'currency')
        }),
        ('Limits', {
            'fields': ('tokens_monthly', 'max_agents', 'max_pods', 'api_rate_limit')
        }),
        ('Features', {
            'fields': ('features',)
        }),
        ('Display', {
            'fields': ('is_popular', 'display_order', 'is_active')
        }),
        ('Stripe', {
            'fields': ('stripe_price_id', 'stripe_product_id'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin for subscriptions."""
    
    list_display = ['id', 'user_id', 'plan', 'status', 'billing_interval', 'current_period_end']
    list_filter = ['status', 'billing_interval', 'plan']
    search_fields = ['user_id', 'stripe_subscription_id']
    raw_id_fields = ['plan']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin for payment methods."""
    
    list_display = ['id', 'user_id', 'type', 'card_brand', 'card_last4', 'is_default']
    list_filter = ['type', 'is_default', 'is_active']
    search_fields = ['user_id', 'stripe_payment_method_id']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin for invoices."""
    
    list_display = ['invoice_number', 'user_id', 'status', 'total', 'invoice_date', 'paid_at']
    list_filter = ['status', 'invoice_date']
    search_fields = ['invoice_number', 'user_id', 'stripe_invoice_id']
    date_hierarchy = 'invoice_date'


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    """Admin for usage records."""
    
    list_display = ['id', 'user_id', 'usage_type', 'quantity', 'recorded_at']
    list_filter = ['usage_type', 'recorded_at']
    search_fields = ['user_id']
    date_hierarchy = 'recorded_at'
