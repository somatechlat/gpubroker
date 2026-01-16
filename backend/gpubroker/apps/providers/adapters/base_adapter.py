"""
Base Provider Adapter Interface

Defines the contract that all provider adapters must implement.
Provides common functionality and error handling.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import time


@dataclass
class GPUInstance:
    """GPU instance data structure."""

    provider_id: str
    instance_id: str
    name: Optional[str] = None
    gpu_type: str = ""
    gpu_memory_gb: int = 0
    cpu_cores: int = 0
    ram_gb: int = 0
    storage_gb: int = 0
    storage_type: str = "SSD"
    price_per_hour: float = 0.0
    currency: str = "USD"
    region: str = ""
    availability_zone: Optional[str] = None
    availability_status: str = "available"
    min_rental_time: int = 1
    max_rental_time: Optional[int] = None
    spot_pricing: bool = False
    preemptible: bool = False
    network_speed_gbps: Optional[float] = None
    performance_tps: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class ProviderError(Exception):
    """Base exception for provider errors."""

    def __init__(self, message: str, provider: str = None, error_code: str = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        super().__init__(message)


class AuthenticationError(ProviderError):
    """Authentication failure."""

    pass


class RateLimitError(ProviderError):
    """Rate limiting error."""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class NetworkError(ProviderError):
    """Network connectivity error."""

    pass


class AdapterNotFoundError(ProviderError):
    """Adapter not found error."""

    pass


class BaseProviderAdapter(ABC):
    """Abstract base class for all provider adapters."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validated = False
        self._last_health_check = None
        self._healthy = None

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Return unique provider identifier."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return human-readable provider name."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test connection to provider API.

        Returns:
            True if connection is successful, False otherwise.
        """
        pass

    async def validate_credentials(self) -> bool:
        """
        Validate API credentials.

        Returns:
            True if credentials are valid, False otherwise.
        """
        try:
            result = await self.test_connection()
            self._validated = result
            return result
        except Exception as e:
            self.logger.error(f"Credentials validation failed: {e}")
            return False

    @abstractmethod
    async def get_instances(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[GPUInstance]:
        """
        Get available GPU instances from provider.

        Args:
            filters: Optional filters to apply (gpu_type, region, max_price, etc.)

        Returns:
            List of GPU instances

        Raises:
            ProviderError: If unable to fetch instances
        """
        pass

    async def get_instance_by_id(self, instance_id: str) -> Optional[GPUInstance]:
        """
        Get specific instance by ID.

        Args:
            instance_id: Provider's instance ID

        Returns:
            GPU instance if found, None otherwise
        """
        try:
            instances = await self.get_instances()
            for instance in instances:
                if instance.instance_id == instance_id:
                    return instance
            return None
        except Exception as e:
            self.logger.error(f"Failed to get instance {instance_id}: {e}")
            return None

    async def get_performance_estimate(self, gpu_type: str) -> float:
        """
        Get performance estimate for GPU type.

        Args:
            gpu_type: GPU type (e.g., 'A100', 'V100')

        Returns:
            Performance estimate in tokens per second
        """
        # Default performance mapping - can be overridden by specific adapters
        performance_map = {
            "A100": 1550.0,
            "A100-80GB": 1550.0,
            "A100-40GB": 1400.0,
            "V100": 840.0,
            "V100-32GB": 840.0,
            "V100-16GB": 750.0,
            "RTX 4090": 1310.0,
            "RTX 3090": 980.0,
            "RTX A6000": 1000.0,
            "RTX A5000": 720.0,
            "RTX A4000": 480.0,
            "T4": 340.0,
            "P100": 420.0,
            "K80": 180.0,
        }

        # Try exact match first
        if gpu_type in performance_map:
            return performance_map[gpu_type]

        # Try partial match
        for key, value in performance_map.items():
            if gpu_type.startswith(key) or key.startswith(gpu_type):
                return value

        # Default estimate
        self.logger.warning(f"Unknown GPU type: {gpu_type}, using default performance")
        return 100.0

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on provider.

        Returns:
            Health check results
        """
        start_time = time.time()

        try:
            # Test basic connectivity
            is_healthy = await self.test_connection()

            # Test instance fetching (with limit)
            instances = []
            if is_healthy:
                try:
                    instances = await self.get_instances(limit=5)
                except Exception as e:
                    self.logger.warning(
                        f"Instance fetch failed during health check: {e}"
                    )
                    is_healthy = False

            response_time = (time.time() - start_time) * 1000

            result = {
                "provider_id": self.provider_id,
                "provider_name": self.provider_name,
                "healthy": is_healthy,
                "response_time_ms": round(response_time, 2),
                "instance_count": len(instances),
                "timestamp": datetime.utcnow().isoformat(),
                "error": None,
            }

            self._last_health_check = result
            self._healthy = is_healthy

            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            result = {
                "provider_id": self.provider_id,
                "provider_name": self.provider_name,
                "healthy": False,
                "response_time_ms": round(response_time, 2),
                "instance_count": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

            self._last_health_check = result
            self._healthy = False

            return result

    def get_last_health_check(self) -> Optional[Dict[str, Any]]:
        """Get last health check result."""
        return self._last_health_check

    def is_healthy(self) -> Optional[bool]:
        """Get current health status."""
        return self._healthy

    def _safe_int_conversion(self, value: Any, default: int = 0) -> int:
        """Safely convert value to int."""
        try:
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                # Handle memory units (MB, GB, TB)
                value_lower = value.lower()
                if "tb" in value_lower:
                    return int(float(value.replace("tb", "").strip()) * 1024 * 1024)
                elif "gb" in value_lower:
                    return int(float(value.replace("gb", "").strip()) * 1024)
                elif "mb" in value_lower:
                    return int(float(value.replace("mb", "").strip()))
                else:
                    return int(float(value))
            return default
        except (ValueError, TypeError):
            return default

    def _safe_float_conversion(self, value: Any, default: float = 0.0) -> float:
        """Safely convert value to float."""
        try:
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Clean up currency symbols and other characters
                clean_value = value.replace("$", "").replace(",", "").strip()
                return float(clean_value)
            return default
        except (ValueError, TypeError):
            return default

    def _clean_string(self, value: Any, default: str = "") -> str:
        """Clean and return string value."""
        if value is None:
            return default
        if isinstance(value, str):
            return value.strip()
        return str(value) if value else default

    async def _retry_with_backoff(
        self,
        func,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        """
        Retry function with exponential backoff.

        Args:
            func: Async function to retry
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
        """
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries:
                    raise

                delay = min(base_delay * (2**attempt), max_delay)
                self.logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)

    def validate_instance(self, instance: GPUInstance) -> bool:
        """
        Validate instance data.

        Args:
            instance: GPU instance to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["provider_id", "instance_id", "gpu_type"]

        for field in required_fields:
            if not getattr(instance, field):
                self.logger.warning(f"Instance missing required field: {field}")
                return False

        if instance.price_per_hour < 0:
            self.logger.warning(f"Invalid price for instance {instance.instance_id}")
            return False

        if instance.gpu_memory_gb < 0:
            self.logger.warning(
                f"Invalid GPU memory for instance {instance.instance_id}"
            )
            return False

        return True

    @classmethod
    def validate_adapter_implementation(cls, adapter_class) -> bool:
        """
        Validate that adapter class implements all required methods.

        Args:
            adapter_class: Adapter class to validate

        Returns:
            True if valid, False otherwise
        """
        required_methods = [
            "provider_id",
            "provider_name",
            "test_connection",
            "get_instances",
        ]

        for method in required_methods:
            if not hasattr(adapter_class, method):
                logging.error(f"Adapter missing required method: {method}")
                return False

        return True
