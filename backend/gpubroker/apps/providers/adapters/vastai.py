"""
VastAI Provider Adapter

Production-ready adapter for Vast.ai cloud GPU services.
Implements BaseProviderAdapter interface.
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from .base_adapter import (
    BaseProviderAdapter,
    GPUInstance,
    ProviderError,
    AuthenticationError,
    RateLimitError,
    NetworkError,
)


class Adapter(BaseProviderAdapter):
    """VastAI provider adapter."""

    @property
    def provider_id(self) -> str:
        return "vastai"

    @property
    def provider_name(self) -> str:
        return "Vast.ai"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://console.vast.ai/api/v0"
        self.api_key = config.get("api_key", "")
        self.timeout = config.get("timeout", 30)

        # Provider-specific performance data (overrides base defaults)
        self.performance_data = {
            "H100": 12000.0,
            "A100": 8000.0,
            "A100-80GB": 8000.0,
            "A100-40GB": 7200.0,
            "A6000": 2200.0,
            "RTX 4090": 4500.0,
            "RTX 3090": 3500.0,
            "RTX 3080": 2800.0,
            "RTX A5000": 1800.0,
            "RTX A4000": 1200.0,
            "V100": 3000.0,
            "V100-32GB": 3000.0,
            "P100": 1500.0,
            "T4": 800.0,
        }

    async def test_connection(self) -> bool:
        """Test connection to Vast.ai API."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/bundles/"
                headers = self._get_headers()

                async with session.get(
                    url, headers=headers, timeout=self.timeout
                ) as response:
                    return response.status == 200

        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    async def get_instances(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[GPUInstance]:
        """
        Get available GPU instances from Vast.ai.

        Args:
            filters: Optional filters including gpu_type, region, max_price, etc.

        Returns:
            List of GPU instances

        Raises:
            ProviderError: If unable to fetch instances
        """
        try:
            # Build request parameters
            params = {}
            if filters:
                if "gpu_type" in filters:
                    params["gpu_name"] = filters["gpu_type"]
                if "region" in filters:
                    params["cloud_type"] = filters["region"]
                if "min_rental_time" in filters:
                    params["min_bid"] = filters["min_rental_time"]
                if "max_price" in filters:
                    params["max_price"] = filters["max_price"]
                if "sort_by" in filters:
                    params["sort"] = filters["sort_by"]
                else:
                    params["sort"] = "score-"

            # Fetch instances with retry logic
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/bundles/"
                headers = self._get_headers()

                response_data = await self._retry_with_backoff(
                    lambda: self._fetch_instances_page(session, url, headers, params)
                )

                instances = []
                for item in response_data.get("offers", []):
                    try:
                        instance = self._parse_instance(item)
                        if self.validate_instance(instance):
                            instances.append(instance)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse instance {item.get('id', 'unknown')}: {e}"
                        )

                # Apply additional filtering
                if filters:
                    instances = self._apply_filters(instances, filters)

                self.logger.info(f"Retrieved {len(instances)} instances from Vast.ai")
                return instances

        except aiohttp.ClientError as e:
            raise NetworkError(
                f"Network error fetching instances: {e}", self.provider_id
            )
        except Exception as e:
            raise ProviderError(f"Failed to fetch instances: {e}", self.provider_id)

    async def get_instance_by_id(self, instance_id: str) -> Optional[GPUInstance]:
        """Get specific instance by ID."""
        try:
            filters = {"instance_id": instance_id}
            instances = await self.get_instances(filters)
            return instances[0] if instances else None
        except Exception as e:
            self.logger.error(f"Failed to get instance {instance_id}: {e}")
            return None

    async def get_performance_estimate(self, gpu_type: str) -> float:
        """Get performance estimate for GPU type."""
        # Use provider-specific data first
        if gpu_type.upper() in self.performance_data:
            return self.performance_data[gpu_type.upper()]

        # Try to match partial names
        for key, value in self.performance_data.items():
            if key.lower() in gpu_type.lower() or gpu_type.lower() in key.lower():
                return value

        # Fall back to base implementation
        return await super().get_performance_estimate(gpu_type)

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {"Accept": "application/json", "User-Agent": "GPUBroker/2.0"}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    async def _fetch_instances_page(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: Dict[str, str],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fetch a single page of instances."""
        async with session.get(
            url, headers=headers, params=params, timeout=self.timeout
        ) as response:
            # Handle rate limiting
            if response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    f"Rate limited, retry after {retry_after}s",
                    retry_after=retry_after,
                    provider=self.provider_id,
                )

            # Handle authentication errors
            if response.status == 401:
                raise AuthenticationError("Invalid API credentials", self.provider_id)

            # Handle other HTTP errors
            if response.status >= 400:
                error_text = await response.text()
                raise ProviderError(
                    f"API request failed: {response.status} - {error_text}",
                    self.provider_id,
                )

            return await response.json()

    def _parse_instance(self, item: Dict[str, Any]) -> GPUInstance:
        """Parse Vast.ai API response into GPUInstance."""
        # Extract basic info
        instance_id = str(item.get("id", ""))
        gpu_name = item.get("gpu_name", "")
        num_gpus = item.get("num_gpus", 1)

        # Handle multiple GPUs
        display_name = f"{num_gpus}x {gpu_name}" if num_gpus > 1 else gpu_name

        # Extract and convert specifications
        gpu_memory_gb = self._safe_int_conversion(item.get("gpu_ram", 0))
        cpu_cores = self._safe_int_conversion(item.get("cpu_cores", 0))
        ram_gb = self._safe_int_conversion(item.get("cpu_ram", 0))
        storage_gb = self._safe_int_conversion(item.get("disk_space", 0))

        # Pricing
        price_per_hour = self._safe_float_conversion(item.get("dph_total", 0))

        # Location
        region = self._clean_string(item.get("geolocation", "Unknown"))
        cloud_type = item.get("hosting_type", 0)  # 0=p2p, 1=datacenter
        availability_zone = "P2P" if cloud_type == 0 else "Datacenter"

        # Availability
        is_rentable = item.get("rentable", False)
        reliability = self._safe_float_conversion(item.get("reliability2", 0))
        availability_status = "available" if is_rentable else "unavailable"

        # Rental terms
        min_rental_time = self._safe_int_conversion(item.get("min_bid", 1))
        max_rental_time = None

        # Instance characteristics
        spot_pricing = True  # Vast.ai is primarily spot pricing
        preemptible = spot_pricing

        # Network
        inet_up = self._safe_float_conversion(item.get("inet_up", 0))
        network_speed_gbps = inet_up / 1000 if inet_up > 0 else None

        # Performance estimate
        base_tps = self.performance_data.get(gpu_name.upper(), 0.0)
        performance_tps = base_tps * num_gpus

        # Additional metadata
        metadata = {
            "vastai_score": item.get("score", 0),
            "vastai_reliability": reliability,
            "vastai_hosting_type": cloud_type,
            "vastai_direct_port": item.get("direct_port", False),
            "vastai_inet_up": inet_up,
            "vastai_inet_down": self._safe_float_conversion(item.get("inet_down", 0)),
            "vastai_disk_bw": self._safe_float_conversion(item.get("disk_bw", 0)),
            "vastai_dlperf": self._safe_float_conversion(item.get("dlperf", 0)),
            "vastai_driver_version": self._clean_string(item.get("cuda_max_good", "")),
            "vastai_storage_type": self._clean_string(item.get("disk_type", "")),
            "num_gpus": num_gpus,
        }

        return GPUInstance(
            provider_id=self.provider_id,
            instance_id=instance_id,
            name=display_name,
            gpu_type=gpu_name,
            gpu_memory_gb=gpu_memory_gb,
            cpu_cores=cpu_cores,
            ram_gb=ram_gb,
            storage_gb=storage_gb,
            storage_type=self._get_storage_type(item.get("disk_type", "")),
            price_per_hour=price_per_hour,
            currency="USD",
            region=region,
            availability_zone=availability_zone,
            availability_status=availability_status,
            min_rental_time=min_rental_time,
            max_rental_time=max_rental_time,
            spot_pricing=spot_pricing,
            preemptible=preemptible,
            network_speed_gbps=network_speed_gbps,
            performance_tps=performance_tps,
            metadata=metadata,
        )

    def _get_storage_type(self, disk_type: str) -> str:
        """Map Vast.ai disk types to standard storage types."""
        disk_type = disk_type.lower()
        if "nvme" in disk_type:
            return "NVMe"
        elif "ssd" in disk_type:
            return "SSD"
        elif "hdd" in disk_type:
            return "HDD"
        else:
            return "SSD"  # Default assumption

    def _apply_filters(
        self, instances: List[GPUInstance], filters: Dict[str, Any]
    ) -> List[GPUInstance]:
        """Apply additional filters to instances."""
        filtered_instances = instances

        # Filter by instance_id if specified
        if "instance_id" in filters:
            instance_id = filters["instance_id"]
            filtered_instances = [
                instance
                for instance in filtered_instances
                if instance.instance_id == instance_id
            ]

        # Filter by GPU type if specified (more flexible matching)
        if "gpu_type" in filters:
            gpu_type = filters["gpu_type"].lower()
            filtered_instances = [
                instance
                for instance in filtered_instances
                if gpu_type in instance.gpu_type.lower()
            ]

        # Filter by minimum GPU memory
        if "min_memory" in filters:
            min_memory = filters["min_memory"]
            filtered_instances = [
                instance
                for instance in filtered_instances
                if instance.gpu_memory_gb >= min_memory
            ]

        # Filter by maximum price
        if "max_price" in filters:
            max_price = filters["max_price"]
            filtered_instances = [
                instance
                for instance in filtered_instances
                if instance.price_per_hour <= max_price
            ]

        # Filter by region
        if "regions" in filters:
            regions = [r.lower() for r in filters["regions"]]
            filtered_instances = [
                instance
                for instance in filtered_instances
                if instance.region.lower() in regions
            ]

        # Filter by availability
        if filters.get("available_only", True):
            filtered_instances = [
                instance
                for instance in filtered_instances
                if instance.availability_status == "available"
            ]

        # Sort results
        if "sort_by" in filters:
            sort_by = filters["sort_by"]
            reverse = sort_by.startswith("-")
            field = sort_by.lstrip("-")

            if hasattr(GPUInstance, field):
                filtered_instances.sort(
                    key=lambda x: getattr(x, field), reverse=reverse
                )

        return filtered_instances


# Provider metadata for registry
provider_info = {
    "name": "Vast.ai",
    "description": "Cloud GPU marketplace with competitive spot pricing",
    "website": "https://vast.ai/",
    "documentation": "https://console.vast.ai/api/",
    "supported_regions": ["US", "EU", "Asia", "Canada", "Australia"],
    "supported_gpus": [
        "H100",
        "A100",
        "A6000",
        "RTX 4090",
        "RTX 3090",
        "RTX 3080",
        "RTX A5000",
        "RTX A4000",
        "V100",
        "P100",
        "T4",
    ],
    "pricing_model": ["spot", "on-demand"],
    "features": [
        "spot_instances",
        "direct_ssh_access",
        "gpu_passthrough",
        "multiple_regions",
        "p2p_hosting",
        "datacenter_hosting",
    ],
}

# Update adapter class with provider info
Adapter.provider_info = provider_info
