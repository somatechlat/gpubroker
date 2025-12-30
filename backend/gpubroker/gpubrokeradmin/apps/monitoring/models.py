"""
Monitoring Models - GPUBROKERADMIN Control Plane.

Monitors provider health, POD metrics, and system status.
"""
from django.db import models
import uuid


class ProviderHealthCheck(models.Model):
    """
    Health check results for GPU providers across all PODs.
    """
    
    class Status(models.TextChoices):
        HEALTHY = 'healthy', 'Healthy'
        DEGRADED = 'degraded', 'Degraded'
        UNHEALTHY = 'unhealthy', 'Unhealthy'
        UNKNOWN = 'unknown', 'Unknown'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    provider_name = models.CharField(max_length=100)
    endpoint = models.URLField()
    
    status = models.CharField(max_length=20, choices=Status.choices)
    response_time_ms = models.IntegerField(blank=True, null=True)
    error_message = models.TextField(blank=True)
    
    # Metrics
    success_rate_1h = models.FloatField(default=100.0)
    avg_response_time_1h = models.FloatField(default=0.0)
    
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_provider_health_checks'
        verbose_name = 'Provider Health Check'
        verbose_name_plural = 'Provider Health Checks'
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['provider_name', '-checked_at']),
        ]
    
    def __str__(self):
        return f"{self.provider_name}: {self.status} at {self.checked_at}"


class PodMetrics(models.Model):
    """
    Aggregated metrics for POD instances.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    pod = models.ForeignKey(
        'pod_management.Pod',
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    
    # Request metrics
    requests_total = models.BigIntegerField(default=0)
    requests_success = models.BigIntegerField(default=0)
    requests_failed = models.BigIntegerField(default=0)
    
    # User metrics
    active_users = models.IntegerField(default=0)
    total_users = models.IntegerField(default=0)
    
    # Provider metrics
    provider_calls = models.BigIntegerField(default=0)
    provider_errors = models.BigIntegerField(default=0)
    
    # Performance
    avg_response_time_ms = models.FloatField(default=0.0)
    p95_response_time_ms = models.FloatField(default=0.0)
    p99_response_time_ms = models.FloatField(default=0.0)
    
    # Cost metrics
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Time window
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_pod_metrics'
        verbose_name = 'POD Metrics'
        verbose_name_plural = 'POD Metrics'
        ordering = ['-period_end']
        indexes = [
            models.Index(fields=['pod', '-period_end']),
        ]
    
    def __str__(self):
        return f"{self.pod.name} metrics: {self.period_start} - {self.period_end}"


class SystemStatus(models.Model):
    """
    Overall system status and health.
    """
    
    class Component(models.TextChoices):
        API_GATEWAY = 'api_gateway', 'API Gateway'
        DATABASE = 'database', 'Database'
        CACHE = 'cache', 'Cache (Redis)'
        QUEUE = 'queue', 'Message Queue (Kafka)'
        PROVIDERS = 'providers', 'GPU Providers'
        AUTH = 'auth', 'Authentication'
    
    class Status(models.TextChoices):
        OPERATIONAL = 'operational', 'Operational'
        DEGRADED = 'degraded', 'Degraded Performance'
        PARTIAL_OUTAGE = 'partial_outage', 'Partial Outage'
        MAJOR_OUTAGE = 'major_outage', 'Major Outage'
        MAINTENANCE = 'maintenance', 'Under Maintenance'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    component = models.CharField(max_length=50, choices=Component.choices)
    status = models.CharField(max_length=50, choices=Status.choices)
    message = models.TextField(blank=True)
    
    # Metrics
    uptime_percentage = models.FloatField(default=100.0)
    last_incident_at = models.DateTimeField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admin_system_status'
        verbose_name = 'System Status'
        verbose_name_plural = 'System Statuses'
    
    def __str__(self):
        return f"{self.component}: {self.status}"
