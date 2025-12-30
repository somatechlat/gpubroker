"""
Notifications Models - GPUBROKERADMIN Control Plane.

Manages email notifications, alerts, and communication.
"""
from django.db import models
from django.conf import settings
import uuid


class NotificationTemplate(models.Model):
    """
    Email and notification templates.
    """
    
    class TemplateType(models.TextChoices):
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        PUSH = 'push', 'Push Notification'
        WEBHOOK = 'webhook', 'Webhook'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    template_type = models.CharField(max_length=20, choices=TemplateType.choices)
    
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    html_body = models.TextField(blank=True)
    
    # Template variables documentation
    variables = models.JSONField(default=list)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admin_notification_templates'
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"


class NotificationLog(models.Model):
    """
    Log of sent notifications.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        FAILED = 'failed', 'Failed'
        BOUNCED = 'bounced', 'Bounced'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='logs'
    )
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notification_logs'
    )
    recipient_email = models.EmailField()
    
    pod = models.ForeignKey(
        'pod_management.Pod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_logs'
    )
    
    subject = models.CharField(max_length=255)
    body = models.TextField()
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)
    
    sent_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_notification_logs'
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"To {self.recipient_email}: {self.subject[:50]}"


class AlertRule(models.Model):
    """
    Alert rules for monitoring and notifications.
    """
    
    class Severity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'
        CRITICAL = 'critical', 'Critical'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Scope: null = global, otherwise specific POD
    pod = models.ForeignKey(
        'pod_management.Pod',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='alert_rules'
    )
    
    # Rule configuration
    metric = models.CharField(max_length=100)
    condition = models.CharField(max_length=50)
    threshold = models.FloatField()
    severity = models.CharField(max_length=20, choices=Severity.choices)
    
    # Notification settings
    notification_template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='alert_rules'
    )
    notify_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='alert_subscriptions',
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    cooldown_minutes = models.IntegerField(default=15)
    last_triggered_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admin_alert_rules'
        verbose_name = 'Alert Rule'
        verbose_name_plural = 'Alert Rules'
    
    def __str__(self):
        return f"{self.name} ({self.severity})"
