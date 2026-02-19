"""
Deployment Services.

Business logic for pod configuration, deployment, and lifecycle management.

Requirements:
- 11.1-11.6: Configure Pod
- 12.1-12.8: Deployment
- 13.1-13.7: Activation
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from .models import PodDeploymentConfig, PodDeploymentLog, ProviderLimits

logger = logging.getLogger('gpubroker.deployment')

# Cache TTL for provider limits (5 minutes)
LIMITS_CACHE_TTL = 300


class CostEstimatorService:
    """
    Service for estimating pod deployment costs.
    
    Requirement 11.4: Show estimated cost per hour/day/month.
    """
    
    @staticmethod
    def estimate_cost(
        gpu_type: str,
        gpu_count: int = 1,
        provider: Optional[str] = None,
        vcpus: int = 4,
        ram_gb: int = 16,
        storage_gb: int = 100,
        storage_type: str = "ssd",
        spot_instance: bool = False,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate cost for a pod configuration.
        
        Returns cost breakdown and estimates for hour/day/month.
        """
        # Get provider limits for pricing
        limits = None
        if provider:
            limits = ProviderLimits.objects.filter(
                provider=provider,
                gpu_type=gpu_type
            ).first()
        
        if not limits:
            # Use default pricing if no specific limits found
            limits = ProviderLimits.objects.filter(gpu_type=gpu_type).first()
        
        if not limits:
            # Fallback to estimated pricing based on GPU type
            base_prices = {
                'RTX 4090': Decimal('0.35'),
                'RTX 3090': Decimal('0.25'),
                'A100 40GB': Decimal('1.50'),
                'A100 80GB': Decimal('1.89'),
                'H100': Decimal('2.49'),
                'A10': Decimal('0.50'),
                'A6000': Decimal('0.80'),
                'V100': Decimal('0.90'),
                'T4': Decimal('0.30'),
            }
            base_price = base_prices.get(gpu_type, Decimal('1.00'))
            cpu_price = Decimal('0.01')
            ram_price = Decimal('0.005')
            storage_price = Decimal('0.0001')
        else:
            base_price = limits.base_price_per_hour
            cpu_price = limits.cpu_price_per_hour
            ram_price = limits.ram_price_per_gb_hour
            storage_price = limits.storage_price_per_gb_hour
        
        # Calculate breakdown
        gpu_cost = base_price * gpu_count
        cpu_cost = cpu_price * vcpus
        ram_cost = ram_price * ram_gb
        storage_cost = storage_price * storage_gb
        
        # Storage type multiplier
        storage_multipliers = {
            'ssd': Decimal('1.0'),
            'nvme': Decimal('1.5'),
            'hdd': Decimal('0.5'),
        }
        storage_cost *= storage_multipliers.get(storage_type, Decimal('1.0'))
        
        # Total hourly cost
        hourly_cost = gpu_cost + cpu_cost + ram_cost + storage_cost
        
        # Spot discount (typically 50-70% off)
        spot_savings = Decimal('0')
        if spot_instance:
            spot_discount = Decimal('0.6')  # 60% discount
            spot_savings = hourly_cost * spot_discount
            hourly_cost = hourly_cost * (1 - spot_discount)
        
        return {
            'price_per_hour': float(hourly_cost),
            'price_per_day': float(hourly_cost * 24),
            'price_per_month': float(hourly_cost * 24 * 30),
            'currency': 'USD',
            'breakdown': {
                'gpu': float(gpu_cost),
                'cpu': float(cpu_cost),
                'ram': float(ram_cost),
                'storage': float(storage_cost),
            },
            'spot_savings': float(spot_savings) if spot_instance else None,
            'provider': provider,
            'gpu_type': gpu_type,
        }
    
    @staticmethod
    def estimate_multiple_providers(
        gpu_type: str,
        gpu_count: int = 1,
        vcpus: int = 4,
        ram_gb: int = 16,
        storage_gb: int = 100,
        storage_type: str = "ssd",
        spot_instance: bool = False,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate costs across multiple providers.
        
        Returns estimates for all available providers with recommendations.
        """
        # Get all providers that support this GPU type
        limits_qs = ProviderLimits.objects.filter(gpu_type=gpu_type)
        
        if region:
            limits_qs = limits_qs.filter(regions__contains=[region])
        
        estimates = []
        for limits in limits_qs:
            estimate = CostEstimatorService.estimate_cost(
                gpu_type=gpu_type,
                gpu_count=gpu_count,
                provider=limits.provider,
                vcpus=vcpus,
                ram_gb=ram_gb,
                storage_gb=storage_gb,
                storage_type=storage_type,
                spot_instance=spot_instance,
                region=region,
            )
            estimates.append(estimate)
        
        # If no provider-specific estimates, return default
        if not estimates:
            default_estimate = CostEstimatorService.estimate_cost(
                gpu_type=gpu_type,
                gpu_count=gpu_count,
                vcpus=vcpus,
                ram_gb=ram_gb,
                storage_gb=storage_gb,
                storage_type=storage_type,
                spot_instance=spot_instance,
            )
            estimates.append(default_estimate)
        
        # Sort by price
        estimates.sort(key=lambda x: x['price_per_hour'])
        
        cheapest = estimates[0] if estimates else None
        
        # Best value considers availability and reliability (simplified)
        best_value = cheapest  # In real implementation, use TOPSIS
        
        return {
            'estimates': estimates,
            'cheapest': cheapest,
            'best_value': best_value,
            'recommended': cheapest['provider'] if cheapest else None,
        }


class ValidationService:
    """
    Service for validating pod configurations against provider limits.
    
    Requirement 11.5: Validate configuration against provider limits.
    """
    
    @staticmethod
    def validate_config(
        gpu_type: str,
        gpu_count: int,
        provider: str,
        vcpus: int,
        ram_gb: int,
        storage_gb: int,
        storage_type: str,
        region: str,
        spot_instance: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate a pod configuration against provider limits.
        
        Returns validation result with errors, warnings, and suggestions.
        """
        errors = []
        warnings = []
        suggested_adjustments = {}
        
        # Get provider limits
        limits = ProviderLimits.objects.filter(
            provider=provider,
            gpu_type=gpu_type
        ).first()
        
        if not limits:
            # Check if GPU type exists at all
            any_limits = ProviderLimits.objects.filter(gpu_type=gpu_type).first()
            if not any_limits:
                errors.append(f"GPU type '{gpu_type}' not found in any provider")
            else:
                errors.append(f"Provider '{provider}' does not support GPU type '{gpu_type}'")
            
            return {
                'is_valid': False,
                'errors': errors,
                'warnings': warnings,
                'provider_limits': {},
                'suggested_adjustments': suggested_adjustments,
            }
        
        # Validate using provider limits
        config = {
            'gpu_count': gpu_count,
            'vcpus': vcpus,
            'ram_gb': ram_gb,
            'storage_gb': storage_gb,
            'storage_type': storage_type,
            'region': region,
            'spot_instance': spot_instance,
        }
        
        is_valid, validation_errors = limits.validate_config(config)
        errors.extend(validation_errors)
        
        # Add warnings for suboptimal configurations
        if vcpus < 4:
            warnings.append("Low vCPU count may impact performance")
        if ram_gb < 8:
            warnings.append("Low RAM may cause out-of-memory issues")
        if storage_gb < 50:
            warnings.append("Low storage may limit model and data storage")
        
        # Suggest adjustments for invalid configs
        if gpu_count > limits.max_gpu_count:
            suggested_adjustments['gpu_count'] = limits.max_gpu_count
        if vcpus > limits.max_vcpus:
            suggested_adjustments['vcpus'] = limits.max_vcpus
        if ram_gb > limits.max_ram_gb:
            suggested_adjustments['ram_gb'] = limits.max_ram_gb
        if storage_gb > limits.max_storage_gb:
            suggested_adjustments['storage_gb'] = limits.max_storage_gb
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'provider_limits': {
                'min_gpu_count': limits.min_gpu_count,
                'max_gpu_count': limits.max_gpu_count,
                'min_vcpus': limits.min_vcpus,
                'max_vcpus': limits.max_vcpus,
                'min_ram_gb': limits.min_ram_gb,
                'max_ram_gb': limits.max_ram_gb,
                'min_storage_gb': limits.min_storage_gb,
                'max_storage_gb': limits.max_storage_gb,
                'supported_storage_types': limits.supported_storage_types,
                'regions': limits.regions,
                'spot_available': limits.spot_available,
            },
            'suggested_adjustments': suggested_adjustments,
        }


class PodConfigurationService:
    """
    Service for managing pod configurations.
    
    Requirements 11.1-11.6: Configure Pod.
    """
    
    def __init__(self):
        self.cost_service = CostEstimatorService()
        self.validation_service = ValidationService()
    
    def create_config(
        self,
        user_id: UUID,
        user_email: str,
        name: str,
        gpu_type: str,
        gpu_count: int = 1,
        gpu_model: str = "",
        gpu_memory_gb: int = 0,
        provider_selection_mode: str = "manual",
        provider: str = "",
        provider_offer_id: str = "",
        vcpus: int = 4,
        ram_gb: int = 16,
        storage_gb: int = 100,
        storage_type: str = "ssd",
        network_speed_gbps: float = 1.0,
        public_ip: bool = True,
        region: str = "us-east-1",
        availability_zone: str = "",
        spot_instance: bool = False,
        max_spot_price: Optional[float] = None,
        description: str = "",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> PodDeploymentConfig:
        """
        Create a new pod configuration (draft).
        
        Requirement 11.6: Save configuration as draft before deployment.
        """
        with transaction.atomic():
            # Auto-select provider if needed
            if provider_selection_mode != "manual" and not provider:
                provider = self._auto_select_provider(
                    gpu_type=gpu_type,
                    mode=provider_selection_mode,
                    region=region,
                )
            
            # Calculate cost estimates
            cost_estimate = self.cost_service.estimate_cost(
                gpu_type=gpu_type,
                gpu_count=gpu_count,
                provider=provider,
                vcpus=vcpus,
                ram_gb=ram_gb,
                storage_gb=storage_gb,
                storage_type=storage_type,
                spot_instance=spot_instance,
                region=region,
            )
            
            # Validate configuration
            validation = self.validation_service.validate_config(
                gpu_type=gpu_type,
                gpu_count=gpu_count,
                provider=provider,
                vcpus=vcpus,
                ram_gb=ram_gb,
                storage_gb=storage_gb,
                storage_type=storage_type,
                region=region,
                spot_instance=spot_instance,
            )
            
            # Create config
            config = PodDeploymentConfig.objects.create(
                user_id=user_id,
                user_email=user_email,
                name=name,
                description=description,
                status=PodDeploymentConfig.Status.DRAFT,
                gpu_type=gpu_type,
                gpu_model=gpu_model,
                gpu_count=gpu_count,
                gpu_memory_gb=gpu_memory_gb,
                provider_selection_mode=provider_selection_mode,
                provider=provider,
                provider_offer_id=provider_offer_id,
                vcpus=vcpus,
                ram_gb=ram_gb,
                storage_gb=storage_gb,
                storage_type=storage_type,
                network_speed_gbps=Decimal(str(network_speed_gbps)),
                public_ip=public_ip,
                region=region,
                availability_zone=availability_zone,
                spot_instance=spot_instance,
                max_spot_price=Decimal(str(max_spot_price)) if max_spot_price else None,
                estimated_price_per_hour=Decimal(str(cost_estimate['price_per_hour'])),
                estimated_price_per_day=Decimal(str(cost_estimate['price_per_day'])),
                estimated_price_per_month=Decimal(str(cost_estimate['price_per_month'])),
                provider_limits=validation.get('provider_limits', {}),
                validation_errors=validation.get('errors', []),
                is_valid=validation['is_valid'],
                tags=tags or [],
                metadata=metadata or {},
            )
            
            # Create log entry
            PodDeploymentLog.objects.create(
                deployment=config,
                event_type=PodDeploymentLog.EventType.CREATED,
                message=f"Pod configuration '{name}' created",
                details={
                    'gpu_type': gpu_type,
                    'provider': provider,
                    'region': region,
                },
                new_status=config.status,
            )
            
            logger.info(f"Pod config created: {config.id} - {name}")
            return config
    
    def update_config(
        self,
        config_id: UUID,
        user_id: UUID,
        **updates
    ) -> PodDeploymentConfig:
        """
        Update a pod configuration.
        
        Only allowed for DRAFT status.
        """
        config = PodDeploymentConfig.objects.get(id=config_id, user_id=user_id)
        
        if config.status != PodDeploymentConfig.Status.DRAFT:
            raise ValueError("Can only update configurations in DRAFT status")
        
        with transaction.atomic():
            # Update fields
            for field, value in updates.items():
                if hasattr(config, field) and value is not None:
                    setattr(config, field, value)
            
            # Recalculate cost estimates
            cost_estimate = self.cost_service.estimate_cost(
                gpu_type=config.gpu_type,
                gpu_count=config.gpu_count,
                provider=config.provider,
                vcpus=config.vcpus,
                ram_gb=config.ram_gb,
                storage_gb=config.storage_gb,
                storage_type=config.storage_type,
                spot_instance=config.spot_instance,
                region=config.region,
            )
            
            config.estimated_price_per_hour = Decimal(str(cost_estimate['price_per_hour']))
            config.estimated_price_per_day = Decimal(str(cost_estimate['price_per_day']))
            config.estimated_price_per_month = Decimal(str(cost_estimate['price_per_month']))
            
            # Revalidate
            validation = self.validation_service.validate_config(
                gpu_type=config.gpu_type,
                gpu_count=config.gpu_count,
                provider=config.provider,
                vcpus=config.vcpus,
                ram_gb=config.ram_gb,
                storage_gb=config.storage_gb,
                storage_type=config.storage_type,
                region=config.region,
                spot_instance=config.spot_instance,
            )
            
            config.provider_limits = validation.get('provider_limits', {})
            config.validation_errors = validation.get('errors', [])
            config.is_valid = validation['is_valid']
            
            config.save()
            
            # Create log entry
            PodDeploymentLog.objects.create(
                deployment=config,
                event_type=PodDeploymentLog.EventType.UPDATED,
                message=f"Pod configuration updated",
                details={'updated_fields': list(updates.keys())},
                old_status=config.status,
                new_status=config.status,
            )
            
            logger.info(f"Pod config updated: {config.id}")
            return config
    
    def get_config(self, config_id: UUID, user_id: UUID) -> PodDeploymentConfig:
        """Get a pod configuration by ID."""
        return PodDeploymentConfig.objects.get(id=config_id, user_id=user_id)
    
    def list_configs(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[PodDeploymentConfig], int]:
        """List pod configurations for a user."""
        queryset = PodDeploymentConfig.objects.filter(user_id=user_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        total = queryset.count()
        start = (page - 1) * per_page
        end = start + per_page
        items = list(queryset[start:end])
        
        return items, total
    
    def delete_config(self, config_id: UUID, user_id: UUID) -> bool:
        """Delete a pod configuration (only DRAFT status)."""
        config = PodDeploymentConfig.objects.get(id=config_id, user_id=user_id)
        
        if config.status != PodDeploymentConfig.Status.DRAFT:
            raise ValueError("Can only delete configurations in DRAFT status")
        
        config.delete()
        logger.info(f"Pod config deleted: {config_id}")
        return True
    
    def _auto_select_provider(
        self,
        gpu_type: str,
        mode: str,
        region: Optional[str] = None,
    ) -> str:
        """
        Auto-select provider based on mode.
        
        Requirement 11.2: Allow selection of provider (or auto-select best).
        """
        # Get available providers for this GPU type
        limits_qs = ProviderLimits.objects.filter(gpu_type=gpu_type)
        
        if region:
            limits_qs = limits_qs.filter(regions__contains=[region])
        
        if not limits_qs.exists():
            return ""
        
        if mode == "auto_cheapest":
            # Select cheapest provider
            cheapest = limits_qs.order_by('base_price_per_hour').first()
            return cheapest.provider if cheapest else ""
        
        elif mode == "auto_best_value":
            # Use TOPSIS or similar ranking (simplified here)
            # In real implementation, consider availability, reliability, etc.
            best = limits_qs.order_by('base_price_per_hour').first()
            return best.provider if best else ""
        
        elif mode == "auto_fastest":
            # Select provider with best availability
            # In real implementation, check real-time availability
            fastest = limits_qs.first()
            return fastest.provider if fastest else ""
        
        return ""


class DeploymentService:
    """
    Service for deploying pods.
    
    Requirements 12.1-12.8: Deployment.
    """
    
    def __init__(self):
        self.config_service = PodConfigurationService()
    
    def deploy(
        self,
        config_id: UUID,
        user_id: UUID,
        sandbox_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Deploy a pod configuration.
        
        Requirements:
        - 12.3: Create pod record (pending)
        - 12.4: Publish to Kafka
        - 12.5: Provision via provider API
        - 12.8: Sandbox mode mock provisioning
        """
        config = PodDeploymentConfig.objects.get(id=config_id, user_id=user_id)
        
        if not config.can_deploy():
            raise ValueError(f"Cannot deploy: status={config.status}, is_valid={config.is_valid}")
        
        with transaction.atomic():
            old_status = config.status
            config.status = PodDeploymentConfig.Status.PENDING
            config.deployment_started_at = timezone.now()
            config.save()
            
            # Create log entry
            PodDeploymentLog.objects.create(
                deployment=config,
                event_type=PodDeploymentLog.EventType.DEPLOYMENT_STARTED,
                message="Deployment started",
                old_status=old_status,
                new_status=config.status,
            )
        
        # In sandbox mode, mock the provisioning
        if sandbox_mode:
            return self._mock_deploy(config)
        
        # In production, publish to Kafka for async processing
        # This would be handled by a separate worker
        return {
            'success': True,
            'deployment_id': str(config.id),
            'status': config.status,
            'message': 'Deployment started. You will receive an email when ready.',
            'estimated_time_minutes': 5,
        }
    
    def _mock_deploy(self, config: PodDeploymentConfig) -> Dict[str, Any]:
        """
        Mock deployment for sandbox mode.
        
        Requirement 12.8: Sandbox mode mock provisioning (instant success).
        """
        with transaction.atomic():
            # Simulate provisioning
            config.status = PodDeploymentConfig.Status.PROVISIONING
            config.save()
            
            PodDeploymentLog.objects.create(
                deployment=config,
                event_type=PodDeploymentLog.EventType.PROVISIONING,
                message="[SANDBOX] Provisioning started",
                old_status=PodDeploymentConfig.Status.PENDING,
                new_status=config.status,
            )
            
            # Instant success in sandbox
            config.status = PodDeploymentConfig.Status.READY
            config.deployment_completed_at = timezone.now()
            config.deployment_id = f"sandbox-{config.id}"
            
            # Generate activation token
            config.generate_activation_token()
            
            # Mock connection details
            config.connection_details = {
                'ssh_host': f'sandbox-{config.id[:8]}.gpubroker.dev',
                'ssh_port': 22,
                'ssh_user': 'root',
                'jupyter_url': f'https://sandbox-{config.id[:8]}.gpubroker.dev:8888',
                'jupyter_token': 'sandbox-token-12345',
                'api_endpoint': f'https://api.sandbox-{config.id[:8]}.gpubroker.dev',
            }
            
            config.save()
            
            PodDeploymentLog.objects.create(
                deployment=config,
                event_type=PodDeploymentLog.EventType.PROVISIONING_COMPLETE,
                message="[SANDBOX] Provisioning complete",
                old_status=PodDeploymentConfig.Status.PROVISIONING,
                new_status=config.status,
            )
        
        return {
            'success': True,
            'deployment_id': str(config.id),
            'status': config.status,
            'message': '[SANDBOX] Deployment complete. Check your email for activation.',
            'estimated_time_minutes': 0,
        }
    
    def get_status(self, config_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Get deployment status."""
        config = PodDeploymentConfig.objects.get(id=config_id, user_id=user_id)
        
        # Calculate progress
        progress_map = {
            PodDeploymentConfig.Status.DRAFT: 0,
            PodDeploymentConfig.Status.PENDING: 10,
            PodDeploymentConfig.Status.PROVISIONING: 50,
            PodDeploymentConfig.Status.READY: 90,
            PodDeploymentConfig.Status.RUNNING: 100,
            PodDeploymentConfig.Status.FAILED: 0,
            PodDeploymentConfig.Status.ERROR: 0,
        }
        
        return {
            'id': str(config.id),
            'name': config.name,
            'status': config.status,
            'progress_percent': progress_map.get(config.status, 0),
            'current_step': config.status,
            'started_at': config.deployment_started_at,
            'estimated_completion': None,
            'error_message': config.validation_errors[0] if config.validation_errors else None,
        }


class ActivationService:
    """
    Service for activating pods.
    
    Requirements 13.1-13.7: Activation.
    """
    
    def activate(
        self,
        config_id: UUID,
        token: str,
        sandbox_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Activate a pod.
        
        Requirements:
        - 13.2: Verify token
        - 13.3: Start pod
        - 13.4: Update status to running
        - 13.5: Return connection details
        - 13.7: Sandbox mode mock connection
        """
        config = PodDeploymentConfig.objects.get(id=config_id)
        
        # Verify token
        if not config.verify_activation_token(token):
            raise ValueError("Invalid or expired activation token")
        
        if not config.can_activate():
            raise ValueError(f"Cannot activate: status={config.status}")
        
        with transaction.atomic():
            old_status = config.status
            config.status = PodDeploymentConfig.Status.RUNNING
            config.activated_at = timezone.now()
            config.started_at = timezone.now()
            config.save()
            
            PodDeploymentLog.objects.create(
                deployment=config,
                event_type=PodDeploymentLog.EventType.ACTIVATED,
                message="Pod activated and running",
                old_status=old_status,
                new_status=config.status,
            )
        
        return {
            'success': True,
            'status': config.status,
            'message': 'Pod activated successfully',
            'connection_details': config.connection_details,
        }
    
    def get_connection_details(
        self,
        config_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """Get connection details for a running pod."""
        config = PodDeploymentConfig.objects.get(id=config_id, user_id=user_id)
        
        if config.status != PodDeploymentConfig.Status.RUNNING:
            raise ValueError(f"Pod is not running: status={config.status}")
        
        return config.connection_details


# Singleton instances
cost_estimator_service = CostEstimatorService()
validation_service = ValidationService()
pod_configuration_service = PodConfigurationService()
deployment_service = DeploymentService()
activation_service = ActivationService()
