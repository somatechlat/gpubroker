"""
Providers App Models - GPU provider marketplace.

Maps to existing PostgreSQL tables:
- providers
- gpu_offers
- price_history
- kpi_calculations
- provider_health_checks

Uses managed=False to prevent Django from altering existing schema.
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class Provider(models.Model):
    """
    GPU cloud provider information.
    
    Maps to existing 'providers' table.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('maintenance', 'Maintenance'),
        ('deprecated', 'Deprecated'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    website_url = models.URLField(max_length=500, blank=True, null=True)
    api_base_url = models.URLField(max_length=500)
    documentation_url = models.URLField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    supported_regions = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    compliance_tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    reliability_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'providers'
        managed = False
        verbose_name = 'Provider'
        verbose_name_plural = 'Providers'
        ordering = ['display_name']
    
    def __str__(self):
        return self.display_name


class GPUOffer(models.Model):
    """
    GPU instance offer from a provider.
    
    Maps to existing 'gpu_offers' table.
    """
    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('limited', 'Limited'),
        ('unavailable', 'Unavailable'),
    ]
    
    STORAGE_TYPE_CHOICES = [
        ('SSD', 'SSD'),
        ('NVMe', 'NVMe'),
        ('HDD', 'HDD'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='offers')
    external_id = models.CharField(max_length=255)  # Provider's internal ID
    name = models.CharField(max_length=255, blank=True, null=True)  # Display name
    gpu_type = models.CharField(max_length=100)
    gpu_memory_gb = models.IntegerField()
    cpu_cores = models.IntegerField()
    ram_gb = models.IntegerField()
    storage_gb = models.IntegerField()
    storage_type = models.CharField(max_length=20, choices=STORAGE_TYPE_CHOICES, default='SSD')
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=4)
    currency = models.CharField(max_length=3, default='USD')
    region = models.CharField(max_length=50)
    availability_zone = models.CharField(max_length=100, blank=True, null=True)
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    min_rental_time = models.IntegerField(default=1)  # minutes
    max_rental_time = models.IntegerField(blank=True, null=True)  # minutes, null = unlimited
    spot_pricing = models.BooleanField(default=False)
    preemptible = models.BooleanField(default=False)
    sla_uptime = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # percentage
    network_speed_gbps = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    compliance_tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'gpu_offers'
        managed = False
        unique_together = [['provider', 'external_id']]
        verbose_name = 'GPU Offer'
        verbose_name_plural = 'GPU Offers'
        ordering = ['price_per_hour']
        indexes = [
            models.Index(fields=['gpu_type']),
            models.Index(fields=['region']),
            models.Index(fields=['price_per_hour']),
            models.Index(fields=['availability_status']),
        ]
    
    @property
    def last_updated(self):
        """Alias for last_seen_at for API compatibility."""
        return self.last_seen_at or self.updated_at
    
    def __str__(self):
        return f"{self.gpu_type} @ {self.provider.display_name} - ${self.price_per_hour}/hr"


class PriceHistory(models.Model):
    """
    Historical price tracking for GPU offers.
    
    Maps to existing 'price_history' table.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer = models.ForeignKey(GPUOffer, on_delete=models.CASCADE, related_name='price_history')
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=4)
    availability_status = models.CharField(max_length=20)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_history'
        managed = False
        verbose_name = 'Price History'
        verbose_name_plural = 'Price History'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['offer', 'recorded_at']),
        ]
    
    def __str__(self):
        return f"{self.offer.gpu_type} - ${self.price_per_hour} @ {self.recorded_at}"


class KPICalculation(models.Model):
    """
    Calculated KPI metrics for GPU offers.
    
    Maps to existing 'kpi_calculations' table.
    """
    CALCULATION_TYPES = [
        ('cost_per_token', 'Cost per Token'),
        ('cost_per_gflop', 'Cost per GFLOP'),
        ('efficiency_score', 'Efficiency Score'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer = models.ForeignKey(GPUOffer, on_delete=models.CASCADE, related_name='kpi_calculations')
    calculation_type = models.CharField(max_length=50, choices=CALCULATION_TYPES)
    value = models.DecimalField(max_digits=12, decimal_places=6)
    metadata = models.JSONField(default=dict)
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kpi_calculations'
        managed = False
        unique_together = [['offer', 'calculation_type']]  # Simplified from date-based
        verbose_name = 'KPI Calculation'
        verbose_name_plural = 'KPI Calculations'
        ordering = ['-calculated_at']
    
    def __str__(self):
        return f"{self.calculation_type}: {self.value} for {self.offer.gpu_type}"


class ProviderHealthCheck(models.Model):
    """
    Provider API health monitoring.
    
    Maps to existing 'provider_health_checks' table.
    """
    STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('degraded', 'Degraded'),
        ('down', 'Down'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='health_checks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    response_time_ms = models.IntegerField()
    error_message = models.TextField(blank=True, null=True)
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'provider_health_checks'
        managed = False
        verbose_name = 'Provider Health Check'
        verbose_name_plural = 'Provider Health Checks'
        ordering = ['-checked_at']
    
    def __str__(self):
        return f"{self.provider.display_name}: {self.status} @ {self.checked_at}"
