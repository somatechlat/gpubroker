"""
Provider Registry for GPUBROKER.

Manages all provider adapters and enables dynamic registration.
Uses lazy imports to avoid hard failures when an adapter has unmet deps.
"""
from __future__ import annotations

import logging
import importlib
from typing import Dict, List, Type, Optional

from .base import BaseProviderAdapter

logger = logging.getLogger('gpubroker.providers.registry')


# Adapter class paths for lazy loading
# Format: "module_path:ClassName"
_ADAPTER_CLASS_PATHS: Dict[str, str] = {
    "aws_sagemaker": "apps.providers.adapters.aws_sagemaker:AWSSageMakerAdapter",
    "azure_ml": "apps.providers.adapters.azure_ml:AzureMLAdapter",
    "google_vertex_ai": "apps.providers.adapters.google_vertex_ai:GoogleVertexAIAdapter",
    "runpod": "apps.providers.adapters.runpod:RunPodAdapter",
    "lambdalabs": "apps.providers.adapters.lambdalabs:LambdaLabsAdapter",
    "paperspace": "apps.providers.adapters.paperspace:PaperspaceAdapter",
    "groq": "apps.providers.adapters.groq:GroqAdapter",
    "replicate": "apps.providers.adapters.replicate:ReplicateAdapter",
    "deepinfra": "apps.providers.adapters.deepinfra:DeepInfraAdapter",
    "cerebras": "apps.providers.adapters.cerebras:CerebrasAdapter",
    "scaleai": "apps.providers.adapters.scaleai:ScaleaiAdapter",
    "alibaba": "apps.providers.adapters.alibaba:AlibabaAdapter",
    "tencent": "apps.providers.adapters.tencent:TencentAdapter",
    "oracle_oci": "apps.providers.adapters.oracle_oci:OracleOCIAdapter",
    "nvidia_dgx": "apps.providers.adapters.nvidia_dgx:NVIDIADGXAdapter",
    "ibm_watson": "apps.providers.adapters.ibm_watson:IBMWatsonAdapter",
    "spell": "apps.providers.adapters.spell:SpellAdapter",
    "kaggle": "apps.providers.adapters.kaggle:KaggleAdapter",
    "runai": "apps.providers.adapters.runai:RunAIAdapter",
    "vastai": "apps.providers.adapters.vastai:VastAIAdapter",
}


class ProviderRegistry:
    """
    Registry for provider adapters.
    
    Supports:
    - Dynamic registration of adapters
    - Lazy loading of adapter classes
    - Listing available adapters
    """
    
    _adapters: Dict[str, Type[BaseProviderAdapter]] = {}
    _initialized: bool = False
    
    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[BaseProviderAdapter]) -> None:
        """
        Register an adapter class.
        
        Args:
            name: Unique identifier for the adapter
            adapter_class: Adapter class (must inherit BaseProviderAdapter)
        """
        cls._adapters[name] = adapter_class
        logger.debug(f"Registered adapter: {name}")
    
    @classmethod
    def get_adapter(cls, name: str) -> BaseProviderAdapter:
        """
        Get an adapter instance by name.
        
        Args:
            name: Adapter identifier
            
        Returns:
            Adapter instance
            
        Raises:
            ValueError: If adapter not found
        """
        if not cls._initialized:
            cls.initialize_registry()
        
        adapter_class = cls._adapters.get(name)
        if not adapter_class:
            raise ValueError(f"Unknown provider: {name}")
        return adapter_class()
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """
        List all registered adapter names.
        
        Returns:
            List of adapter names
        """
        if not cls._initialized:
            cls.initialize_registry()
        return list(cls._adapters.keys())
    
    @classmethod
    def has_adapter(cls, name: str) -> bool:
        """
        Check if an adapter is registered.
        
        Args:
            name: Adapter identifier
            
        Returns:
            True if adapter exists
        """
        if not cls._initialized:
            cls.initialize_registry()
        return name in cls._adapters
    
    @classmethod
    def get_adapter_class(cls, name: str) -> Optional[Type[BaseProviderAdapter]]:
        """
        Get adapter class without instantiating.
        
        Args:
            name: Adapter identifier
            
        Returns:
            Adapter class or None
        """
        if not cls._initialized:
            cls.initialize_registry()
        return cls._adapters.get(name)
    
    @classmethod
    def initialize_registry(cls) -> None:
        """
        Initialize the registry by loading all adapters.
        
        Uses lazy imports to avoid failures when adapters have unmet dependencies.
        """
        if cls._initialized:
            return
        
        for name, ref in _ADAPTER_CLASS_PATHS.items():
            try:
                module_path, class_name = ref.split(":", 1)
                module = importlib.import_module(module_path)
                adapter_class = getattr(module, class_name)
                if not issubclass(adapter_class, BaseProviderAdapter):
                    raise TypeError(
                        f"Adapter {name} does not inherit BaseProviderAdapter"
                    )
                cls.register_adapter(name, adapter_class)
            except ImportError as e:
                logger.warning(f"Skipping adapter {name}: module not found - {e}")
            except AttributeError as e:
                logger.warning(f"Skipping adapter {name}: class not found - {e}")
            except Exception as e:
                logger.warning(f"Skipping adapter {name} due to error: {e}")
        
        cls._initialized = True
        logger.info(f"Initialized registry with {len(cls._adapters)} adapters")
    
    @classmethod
    def reset(cls) -> None:
        """Reset the registry (useful for testing)."""
        cls._adapters.clear()
        cls._initialized = False
