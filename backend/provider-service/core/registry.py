"""
Provider Registry for GPUBROKER
Manages all provider adapters and enables dynamic registration.
Uses lazy imports to avoid hard failures when an adapter has unmet deps.
"""

from typing import Dict, List, Type
import logging
import importlib

try:
    from ..adapters.base_adapter import BaseProviderAdapter
except Exception:  # when imported as a top-level module in tests
    from adapters.base_adapter import BaseProviderAdapter  # type: ignore

logger = logging.getLogger(__name__)


_ADAPTER_CLASS_PATHS: Dict[str, str] = {
    # values are relative module path + class name, separated by ':'
    "aws_sagemaker": "..adapters.aws_sagemaker_adapter:AWSSageMakerAdapter",
    "azure_ml": "..adapters.azure_ml_adapter:AzureMLAdapter",
    "google_vertex_ai": "..adapters.google_vertex_ai_adapter:GoogleVertexAIAdapter",
    "runpod": "..adapters.runpod_adapter:RunPodAdapter",
    "lambdalabs": "..adapters.lambdalabs_adapter:LambdaLabsAdapter",
    "paperspace": "..adapters.paperspace_adapter:PaperspaceAdapter",
    "groq": "..adapters.groq_adapter:GroqAdapter",
    "replicate": "..adapters.replicate_adapter:ReplicateAdapter",
    "deepinfra": "..adapters.deepinfra_adapter:DeepInfraAdapter",
    "cerebras": "..adapters.cerebras_adapter:CerebrasAdapter",
    "scaleai": "..adapters.scaleai_adapter:ScaleaiAdapter",
    "alibaba": "..adapters.alibaba_adapter:AlibabaAdapter",
    "tencent": "..adapters.tencent_adapter:TencentAdapter",
    "oracle_oci": "..adapters.oracle_oci_adapter:OracleOCIAdapter",
    "nvidia_dgx": "..adapters.nvidia_dgx_adapter:NVIDIADGXAdapter",
    "ibm_watson": "..adapters.ibm_watson_adapter:IBMWatsonAdapter",
    "spell": "..adapters.spell_adapter:SpellAdapter",
    "kaggle": "..adapters.kaggle_adapter:KaggleAdapter",
    "runai": "..adapters.runai_adapter:RunAIAdapter",
}


class ProviderRegistry:
    _adapters: Dict[str, Type[BaseProviderAdapter]] = {}

    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[BaseProviderAdapter]):
        cls._adapters[name] = adapter_class
        logger.info("Registered adapter: %s", name)

    @classmethod
    def get_adapter(cls, name: str) -> BaseProviderAdapter:
        adapter_class = cls._adapters.get(name)
        if not adapter_class:
            raise ValueError(f"Unknown provider: {name}")
        return adapter_class()

    @classmethod
    def list_adapters(cls) -> List[str]:
        return list(cls._adapters.keys())

    @classmethod
    def initialize_registry(cls):
        for name, ref in _ADAPTER_CLASS_PATHS.items():
            try:
                module_path, class_name = ref.split(":", 1)
                module = importlib.import_module(module_path, package=__package__)
                adapter_class = getattr(module, class_name)
                if not issubclass(adapter_class, BaseProviderAdapter):
                    raise TypeError("Adapter does not inherit BaseProviderAdapter")
                cls.register_adapter(name, adapter_class)
            except Exception as e:
                logger.warning("Skipping adapter %s due to import error: %s", name, e)
        logger.info("Initialized registry with %d adapters", len(cls._adapters))


ProviderRegistry.initialize_registry()
