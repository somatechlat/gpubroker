"""
Provider Registry System

Manages registration and instantiation of provider adapters.
Provides auto-discovery and lazy loading functionality.
"""

import importlib
import logging
from typing import Dict, Type, List, Optional
from ..adapters.base_adapter import BaseProviderAdapter, AdapterNotFoundError

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for managing provider adapters."""

    _adapters: Dict[str, Type[BaseProviderAdapter]] = {}
    _instances: Dict[str, BaseProviderAdapter] = {}
    _providers_config: Dict[str, Dict] = {}

    @classmethod
    def register(cls, name: str, adapter_class: Type[BaseProviderAdapter]) -> None:
        """
        Register a provider adapter class.

        Args:
            name: Provider name (unique identifier)
            adapter_class: Adapter class that inherits from BaseProviderAdapter

        Raises:
            ValueError: If adapter class is invalid
        """
        # Validate adapter implementation
        if not BaseProviderAdapter.validate_adapter_implementation(adapter_class):
            raise ValueError(
                f"Adapter class {adapter_class} does not implement required methods"
            )

        cls._adapters[name] = adapter_class
        logger.info(f"Registered provider adapter: {name} -> {adapter_class.__name__}")

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Unregister a provider adapter.

        Args:
            name: Provider name to unregister

        Returns:
            True if unregistered successfully, False if not found
        """
        if name in cls._adapters:
            del cls._adapters[name]

            # Clean up any existing instance
            if name in cls._instances:
                del cls._instances[name]

            logger.info(f"Unregistered provider adapter: {name}")
            return True

        return False

    @classmethod
    def get_adapter_class(cls, name: str) -> Type[BaseProviderAdapter]:
        """
        Get adapter class by name.

        Args:
            name: Provider name

        Returns:
            Adapter class

        Raises:
            AdapterNotFoundError: If adapter not found
        """
        if name not in cls._adapters:
            raise AdapterNotFoundError(f"Provider adapter '{name}' not found")

        return cls._adapters[name]

    @classmethod
    def get_adapter(cls, name: str, config: Dict = None) -> BaseProviderAdapter:
        """
        Get or create adapter instance.

        Args:
            name: Provider name
            config: Provider configuration (optional, uses stored config if not provided)

        Returns:
            Adapter instance

        Raises:
            AdapterNotFoundError: If adapter not found
        """
        # Use stored config if not provided
        if config is None:
            config = cls._providers_config.get(name, {})

        # Create instance if not cached
        if name not in cls._instances:
            adapter_class = cls.get_adapter_class(name)
            cls._instances[name] = adapter_class(config)
            logger.info(f"Created adapter instance for: {name}")

        return cls._instances[name]

    @classmethod
    def list_available(cls) -> List[str]:
        """
        List all registered adapter names.

        Returns:
            List of provider names
        """
        return list(cls._adapters.keys())

    @classmethod
    def list_instances(cls) -> Dict[str, str]:
        """
        List active adapter instances.

        Returns:
            Dictionary mapping provider names to adapter class names
        """
        return {
            name: adapter.__class__.__name__ for name, adapter in cls._instances.items()
        }

    @classmethod
    def configure_provider(cls, name: str, config: Dict) -> None:
        """
        Store configuration for a provider.

        Args:
            name: Provider name
            config: Configuration dictionary
        """
        cls._providers_config[name] = config
        logger.debug(f"Stored configuration for provider: {name}")

    @classmethod
    def get_provider_config(cls, name: str) -> Dict:
        """
        Get configuration for a provider.

        Args:
            name: Provider name

        Returns:
            Configuration dictionary
        """
        return cls._providers_config.get(name, {})

    @classmethod
    def auto_register(cls) -> None:
        """
        Auto-register all available adapter modules.

        Discovers adapter modules in the adapters package and registers them.
        """
        adapter_modules = [
            "vastai",
            "aws",
            "gcp",
            "azure",
            "runpod",
            "lambda",
            "tenstorrent",
            "coreweave",
            "fluidstack",
            "vultr",
            "digitalocean",
            "linode",
            "hetzner",
            "scaleway",
            "ovh",
            "ibm",
            "oracle",
            "paperspace",
        ]

        registered_count = 0

        for module_name in adapter_modules:
            try:
                module = importlib.import_module(
                    f".adapters.{module_name}", package=__package__
                )

                # Look for an Adapter class in the module
                adapter_class = getattr(module, "Adapter", None)
                if adapter_class and issubclass(adapter_class, BaseProviderAdapter):
                    cls.register(module_name, adapter_class)
                    registered_count += 1
                else:
                    logger.warning(
                        f"Module {module_name} does not have a valid Adapter class"
                    )

            except ImportError as e:
                logger.debug(f"Could not import adapter {module_name}: {e}")
            except Exception as e:
                logger.error(f"Error registering adapter {module_name}: {e}")

        logger.info(f"Auto-registered {registered_count} provider adapters")

    @classmethod
    def validate_all_adapters(cls) -> Dict[str, bool]:
        """
        Validate all registered adapters.

        Returns:
            Dictionary mapping adapter names to validation results
        """
        results = {}

        for name, adapter_class in cls._adapters.items():
            try:
                is_valid = BaseProviderAdapter.validate_adapter_implementation(
                    adapter_class
                )
                results[name] = is_valid

                if not is_valid:
                    logger.error(f"Adapter {name} failed validation")

            except Exception as e:
                logger.error(f"Error validating adapter {name}: {e}")
                results[name] = False

        return results

    @classmethod
    def get_adapter_info(cls) -> Dict[str, Dict]:
        """
        Get information about all registered adapters.

        Returns:
            Dictionary with adapter metadata
        """
        info = {}

        for name, adapter_class in cls._adapters.items():
            adapter_info = {
                "class_name": adapter_class.__name__,
                "module": adapter_class.__module__,
                "has_instance": name in cls._instances,
                "has_config": name in cls._providers_config,
            }

            # Try to get provider info from class (if available)
            if hasattr(adapter_class, "provider_info"):
                adapter_info.update(adapter_class.provider_info)

            info[name] = adapter_info

        return info

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached instances."""
        cls._instances.clear()
        logger.info("Cleared adapter instance cache")

    @classmethod
    def health_check_all(cls) -> Dict[str, Dict]:
        """
        Perform health check on all instantiated adapters.

        Returns:
            Dictionary mapping provider names to health check results
        """
        results = {}

        for name, adapter in cls._instances.items():
            try:
                # Use asyncio to run async health check
                import asyncio

                if hasattr(adapter, "health_check"):
                    health_result = asyncio.run(adapter.health_check())
                    results[name] = health_result
                else:
                    results[name] = {
                        "provider_id": name,
                        "healthy": False,
                        "error": "Health check method not implemented",
                    }

            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = {"provider_id": name, "healthy": False, "error": str(e)}

        return results


# Global registry instance
registry = ProviderRegistry()

# Auto-register adapters on import
try:
    registry.auto_register()
except Exception as e:
    logger.error(f"Failed to auto-register adapters: {e}")


# Convenience functions
def get_provider(name: str, config: Dict = None) -> BaseProviderAdapter:
    """Convenience function to get a provider adapter."""
    return registry.get_adapter(name, config)


def list_providers() -> List[str]:
    """Convenience function to list available providers."""
    return registry.list_available()


def register_provider(name: str, adapter_class: Type[BaseProviderAdapter]) -> None:
    """Convenience function to register a provider."""
    registry.register(name, adapter_class)


def configure_provider(name: str, config: Dict) -> None:
    """Convenience function to configure a provider."""
    registry.configure_provider(name, config)
