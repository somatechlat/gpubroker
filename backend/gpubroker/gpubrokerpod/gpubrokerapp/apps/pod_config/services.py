"""
POD Configuration Services.

Business logic for POD configuration management.
Includes AWS Parameter Store and Secrets Manager integration.

Requirements: 1.1, 1.3, 1.6
"""
import logging
from typing import Dict, Any, Optional

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('gpubroker.pod_config.services')

# Cache TTL for parameters (5 minutes)
PARAMETER_CACHE_TTL = 300


class AWSParameterStoreService:
    """
    Service for syncing parameters with AWS Parameter Store and Secrets Manager.
    
    Supports:
    - Syncing sensitive parameters to AWS Secrets Manager
    - Syncing non-sensitive parameters to AWS Parameter Store
    - Hot-reload without restart via cache invalidation
    
    Requirements: 1.1, 1.6
    """
    
    def __init__(self):
        self._ssm_client = None
        self._secrets_client = None
        self._initialized = False
    
    def _get_ssm_client(self):
        """Get or create SSM client."""
        if self._ssm_client is None:
            try:
                import boto3
                self._ssm_client = boto3.client(
                    'ssm',
                    region_name=settings.AWS_REGION
                )
            except Exception as e:
                logger.warning(f"Failed to create SSM client: {e}")
                return None
        return self._ssm_client
    
    def _get_secrets_client(self):
        """Get or create Secrets Manager client."""
        if self._secrets_client is None:
            try:
                import boto3
                self._secrets_client = boto3.client(
                    'secretsmanager',
                    region_name=settings.AWS_REGION
                )
            except Exception as e:
                logger.warning(f"Failed to create Secrets Manager client: {e}")
                return None
        return self._secrets_client
    
    def sync_parameter_to_aws(
        self, 
        pod_id: str, 
        key: str, 
        value: str, 
        mode: str,
        is_sensitive: bool = False
    ) -> Optional[str]:
        """
        Sync a parameter to AWS Parameter Store or Secrets Manager.
        
        Returns the ARN of the created/updated parameter.
        
        Requirements: 1.1, 1.6
        """
        # Build parameter name
        param_name = f"/gpubroker/{pod_id}/{mode}/{key}"
        
        if is_sensitive:
            return self._sync_to_secrets_manager(param_name, value)
        else:
            return self._sync_to_parameter_store(param_name, value)
    
    def _sync_to_parameter_store(self, name: str, value: str) -> Optional[str]:
        """Sync to AWS Systems Manager Parameter Store."""
        client = self._get_ssm_client()
        if client is None:
            logger.warning(f"SSM client not available, skipping sync for {name}")
            return None
        
        try:
            response = client.put_parameter(
                Name=name,
                Value=value,
                Type='String',
                Overwrite=True,
                Tags=[
                    {'Key': 'Application', 'Value': 'GPUBROKER'},
                    {'Key': 'ManagedBy', 'Value': 'pod_config'},
                ]
            )
            
            # Get the ARN
            param_response = client.get_parameter(Name=name)
            arn = param_response['Parameter']['ARN']
            
            logger.info(f"Synced parameter to AWS Parameter Store: {name}")
            return arn
            
        except Exception as e:
            logger.error(f"Failed to sync parameter to AWS: {name} - {e}")
            return None
    
    def _sync_to_secrets_manager(self, name: str, value: str) -> Optional[str]:
        """Sync to AWS Secrets Manager."""
        client = self._get_secrets_client()
        if client is None:
            logger.warning(f"Secrets Manager client not available, skipping sync for {name}")
            return None
        
        try:
            # Try to update existing secret
            try:
                client.put_secret_value(
                    SecretId=name,
                    SecretString=value,
                )
                # Get the ARN from describe
                describe_response = client.describe_secret(SecretId=name)
                arn = describe_response['ARN']
            except client.exceptions.ResourceNotFoundException:
                # Create new secret
                response = client.create_secret(
                    Name=name,
                    SecretString=value,
                    Tags=[
                        {'Key': 'Application', 'Value': 'GPUBROKER'},
                        {'Key': 'ManagedBy', 'Value': 'pod_config'},
                    ]
                )
                arn = response['ARN']
            
            logger.info(f"Synced secret to AWS Secrets Manager: {name}")
            return arn
            
        except Exception as e:
            logger.error(f"Failed to sync secret to AWS: {name} - {e}")
            return None
    
    def get_parameter_from_aws(
        self, 
        pod_id: str, 
        key: str, 
        mode: str,
        is_sensitive: bool = False
    ) -> Optional[str]:
        """
        Get a parameter value from AWS.
        
        Requirements: 1.3 (hot reload support)
        """
        param_name = f"/gpubroker/{pod_id}/{mode}/{key}"
        
        if is_sensitive:
            return self._get_from_secrets_manager(param_name)
        else:
            return self._get_from_parameter_store(param_name)
    
    def _get_from_parameter_store(self, name: str) -> Optional[str]:
        """Get from AWS Systems Manager Parameter Store."""
        client = self._get_ssm_client()
        if client is None:
            return None
        
        try:
            response = client.get_parameter(Name=name, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e:
            logger.warning(f"Failed to get parameter from AWS: {name} - {e}")
            return None
    
    def _get_from_secrets_manager(self, name: str) -> Optional[str]:
        """Get from AWS Secrets Manager."""
        client = self._get_secrets_client()
        if client is None:
            return None
        
        try:
            response = client.get_secret_value(SecretId=name)
            return response['SecretString']
        except Exception as e:
            logger.warning(f"Failed to get secret from AWS: {name} - {e}")
            return None
    
    def delete_parameter_from_aws(
        self, 
        pod_id: str, 
        key: str, 
        mode: str,
        is_sensitive: bool = False
    ) -> bool:
        """Delete a parameter from AWS."""
        param_name = f"/gpubroker/{pod_id}/{mode}/{key}"
        
        if is_sensitive:
            return self._delete_from_secrets_manager(param_name)
        else:
            return self._delete_from_parameter_store(param_name)
    
    def _delete_from_parameter_store(self, name: str) -> bool:
        """Delete from AWS Systems Manager Parameter Store."""
        client = self._get_ssm_client()
        if client is None:
            return False
        
        try:
            client.delete_parameter(Name=name)
            logger.info(f"Deleted parameter from AWS Parameter Store: {name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete parameter from AWS: {name} - {e}")
            return False
    
    def _delete_from_secrets_manager(self, name: str) -> bool:
        """Delete from AWS Secrets Manager."""
        client = self._get_secrets_client()
        if client is None:
            return False
        
        try:
            client.delete_secret(
                SecretId=name,
                ForceDeleteWithoutRecovery=True
            )
            logger.info(f"Deleted secret from AWS Secrets Manager: {name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete secret from AWS: {name} - {e}")
            return False


class ParameterCacheService:
    """
    Service for caching parameters with hot-reload support.
    
    Requirements: 1.3
    """
    
    @staticmethod
    def get_cache_key(pod_id: str, key: str, mode: str) -> str:
        """Generate cache key for a parameter."""
        return f"pod_param:{pod_id}:{mode}:{key}"
    
    @staticmethod
    def get_pod_cache_key(pod_id: str) -> str:
        """Generate cache key for all POD parameters."""
        return f"pod_params:{pod_id}"
    
    @classmethod
    def get_parameter(cls, pod_id: str, key: str, mode: str) -> Optional[str]:
        """
        Get parameter from cache.
        
        Returns None if not cached.
        """
        cache_key = cls.get_cache_key(pod_id, key, mode)
        return cache.get(cache_key)
    
    @classmethod
    def set_parameter(cls, pod_id: str, key: str, mode: str, value: str) -> None:
        """
        Set parameter in cache.
        """
        cache_key = cls.get_cache_key(pod_id, key, mode)
        cache.set(cache_key, value, timeout=PARAMETER_CACHE_TTL)
    
    @classmethod
    def invalidate_parameter(cls, pod_id: str, key: str, mode: str = None) -> None:
        """
        Invalidate parameter cache.
        
        If mode is None, invalidates both sandbox and live.
        """
        if mode:
            cache_key = cls.get_cache_key(pod_id, key, mode)
            cache.delete(cache_key)
        else:
            cache.delete(cls.get_cache_key(pod_id, key, 'sandbox'))
            cache.delete(cls.get_cache_key(pod_id, key, 'live'))
    
    @classmethod
    def invalidate_pod(cls, pod_id: str) -> None:
        """
        Invalidate all cached parameters for a POD.
        
        Used when mode is switched or POD is deleted.
        """
        # Delete the pod-level cache
        cache.delete(cls.get_pod_cache_key(pod_id))
        
        # Note: Individual parameter caches will expire naturally
        # For immediate invalidation, we'd need to track all keys
        logger.info(f"Invalidated cache for POD: {pod_id}")
    
    @classmethod
    def get_all_parameters(cls, pod_id: str, mode: str) -> Optional[Dict[str, str]]:
        """
        Get all parameters for a POD from cache.
        """
        cache_key = f"{cls.get_pod_cache_key(pod_id)}:{mode}"
        return cache.get(cache_key)
    
    @classmethod
    def set_all_parameters(cls, pod_id: str, mode: str, params: Dict[str, str]) -> None:
        """
        Cache all parameters for a POD.
        """
        cache_key = f"{cls.get_pod_cache_key(pod_id)}:{mode}"
        cache.set(cache_key, params, timeout=PARAMETER_CACHE_TTL)


class PodConfigService:
    """
    High-level service for POD configuration management.
    
    Combines database, cache, and AWS operations.
    """
    
    def __init__(self):
        self.aws_service = AWSParameterStoreService()
        self.cache_service = ParameterCacheService
    
    def get_parameter_value(
        self, 
        pod_id: str, 
        key: str, 
        mode: str = None
    ) -> Optional[str]:
        """
        Get parameter value with caching and AWS fallback.
        
        Order: Cache → Database → AWS
        
        Requirements: 1.3
        """
        from .models import PodConfiguration, PodParameter
        
        # Get POD to determine mode if not specified
        if mode is None:
            try:
                pod = PodConfiguration.objects.get(pod_id=pod_id)
                mode = pod.mode
            except PodConfiguration.DoesNotExist:
                return None
        
        # Try cache first
        cached = self.cache_service.get_parameter(pod_id, key, mode)
        if cached is not None:
            return cached
        
        # Try database
        try:
            param = PodParameter.objects.select_related('pod').get(
                pod__pod_id=pod_id,
                key=key
            )
            value = param.get_value(mode)
            
            if value is not None:
                # Cache the value
                self.cache_service.set_parameter(pod_id, key, mode, value)
                return value
        except PodParameter.DoesNotExist:
            pass
        
        # Try AWS as last resort (for sensitive params)
        aws_value = self.aws_service.get_parameter_from_aws(
            pod_id, key, mode, is_sensitive=True
        )
        if aws_value:
            self.cache_service.set_parameter(pod_id, key, mode, aws_value)
            return aws_value
        
        return None
    
    def set_parameter_value(
        self,
        pod_id: str,
        key: str,
        value: str,
        mode: str,
        sync_to_aws: bool = True
    ) -> bool:
        """
        Set parameter value with cache invalidation and AWS sync.
        
        Requirements: 1.1, 1.3, 1.6
        """
        from .models import PodConfiguration, PodParameter
        
        try:
            param = PodParameter.objects.select_related('pod').get(
                pod__pod_id=pod_id,
                key=key
            )
            
            # Update database
            if mode == 'sandbox':
                param.sandbox_value = value
            else:
                param.live_value = value
            param.save()
            
            # Invalidate cache
            self.cache_service.invalidate_parameter(pod_id, key, mode)
            
            # Sync to AWS if sensitive
            if sync_to_aws and param.is_sensitive:
                arn = self.aws_service.sync_parameter_to_aws(
                    pod_id, key, value, mode, is_sensitive=True
                )
                if arn:
                    param.aws_parameter_arn = arn
                    param.save(update_fields=['aws_parameter_arn'])
            
            return True
            
        except PodParameter.DoesNotExist:
            logger.warning(f"Parameter not found: {pod_id}:{key}")
            return False
    
    def get_all_parameters(self, pod_id: str, mode: str = None) -> Dict[str, Any]:
        """
        Get all parameters for a POD as a dictionary.
        
        Requirements: 1.3
        """
        from .models import PodConfiguration, PodParameter
        
        # Get POD to determine mode if not specified
        if mode is None:
            try:
                pod = PodConfiguration.objects.get(pod_id=pod_id)
                mode = pod.mode
            except PodConfiguration.DoesNotExist:
                return {}
        
        # Try cache first
        cached = self.cache_service.get_all_parameters(pod_id, mode)
        if cached is not None:
            return cached
        
        # Load from database
        params = {}
        for param in PodParameter.objects.filter(pod__pod_id=pod_id):
            value = param.get_typed_value(mode)
            if value is not None:
                params[param.key] = value
        
        # Cache the result
        self.cache_service.set_all_parameters(pod_id, mode, params)
        
        return params
    
    def reload_parameters(self, pod_id: str) -> bool:
        """
        Force reload all parameters from database.
        
        Used for hot-reload without restart.
        
        Requirements: 1.3
        """
        # Invalidate all caches for this POD
        self.cache_service.invalidate_pod(pod_id)
        
        # Pre-load parameters into cache
        from .models import PodConfiguration
        try:
            pod = PodConfiguration.objects.get(pod_id=pod_id)
            self.get_all_parameters(pod_id, pod.mode)
            logger.info(f"Reloaded parameters for POD: {pod_id}")
            return True
        except PodConfiguration.DoesNotExist:
            return False


# Singleton instance
pod_config_service = PodConfigService()
