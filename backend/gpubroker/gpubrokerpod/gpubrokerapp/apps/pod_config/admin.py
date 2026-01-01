"""
POD Configuration Admin.

Django admin interface for managing POD configurations.
"""
from django.contrib import admin
from .models import PodConfiguration, PodParameter, ParameterAuditLog


class PodParameterInline(admin.TabularInline):
    """Inline admin for POD parameters."""
    model = PodParameter
    extra = 0
    fields = ['key', 'parameter_type', 'sandbox_value', 'live_value', 'is_sensitive', 'is_required']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PodConfiguration)
class PodConfigurationAdmin(admin.ModelAdmin):
    """Admin for POD Configuration."""
    
    list_display = [
        'pod_id', 'name', 'mode', 'status', 'aws_region', 
        'agent_zero_enabled', 'created_at'
    ]
    list_filter = ['mode', 'status', 'aws_region', 'agent_zero_enabled']
    search_fields = ['pod_id', 'name', 'owner_email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_mode_switch']
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'pod_id', 'name', 'description', 'owner_email']
        }),
        ('Mode & Status', {
            'fields': ['mode', 'status', 'last_mode_switch']
        }),
        ('AWS Configuration', {
            'fields': ['aws_region', 'aws_account_id']
        }),
        ('Feature Flags', {
            'fields': ['agent_zero_enabled', 'websocket_enabled', 'webhooks_enabled']
        }),
        ('Rate Limits', {
            'fields': ['rate_limit_free', 'rate_limit_pro', 'rate_limit_enterprise']
        }),
        ('Billing', {
            'fields': ['markup_percentage']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [PodParameterInline]


@admin.register(PodParameter)
class PodParameterAdmin(admin.ModelAdmin):
    """Admin for POD Parameters."""
    
    list_display = [
        'key', 'pod', 'parameter_type', 'is_sensitive', 'is_required', 'updated_at'
    ]
    list_filter = ['parameter_type', 'is_sensitive', 'is_required', 'pod']
    search_fields = ['key', 'description', 'pod__pod_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Identification', {
            'fields': ['id', 'pod', 'key', 'description']
        }),
        ('Values', {
            'fields': ['sandbox_value', 'live_value', 'default_value']
        }),
        ('Type & Validation', {
            'fields': ['parameter_type', 'is_sensitive', 'is_required', 'validation_regex', 'min_value', 'max_value']
        }),
        ('AWS Integration', {
            'fields': ['aws_parameter_arn'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(ParameterAuditLog)
class ParameterAuditLogAdmin(admin.ModelAdmin):
    """Admin for Parameter Audit Logs."""
    
    list_display = [
        'created_at', 'parameter', 'pod', 'change_type', 
        'mode_affected', 'changed_by_email'
    ]
    list_filter = ['change_type', 'mode_affected', 'created_at']
    search_fields = ['parameter__key', 'pod__pod_id', 'changed_by_email', 'change_reason']
    readonly_fields = [
        'id', 'parameter', 'pod', 'changed_by_id', 'changed_by_email',
        'old_value', 'new_value', 'mode_affected', 'change_reason',
        'change_type', 'ip_address', 'user_agent', 'created_at'
    ]
    
    def has_add_permission(self, request):
        """Audit logs should not be manually created."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Audit logs should not be modified."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Audit logs should not be deleted."""
        return False
