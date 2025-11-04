"""
Provider Registry for GPUBROKER
Manages all provider adapters and enables dynamic registration
"""

from typing import Dict, List, Type
import logging

# Import all adapters
from ..adapters.base_adapter import BaseProviderAdapter
from ..adapters.vast_ai_adapter import VastAiAdapter
from ..adapters.core_weave_adapter import CoreWeaveAdapter
from ..adapters.hugging_face_adapter import HuggingFaceAdapter
from ..adapters.aws_sagemaker_adapter import AWSSageMakerAdapter
from ..adapters.azure_ml_adapter import AzureMLAdapter
from ..adapters.google_vertex_ai_adapter import GoogleVertexAIAdapter
from ..adapters.runpod_adapter import RunPodAdapter
from ..adapters.lambdalabs_adapter import LambdaLabsAdapter
from ..adapters.paperspace_adapter import PaperspaceAdapter
from ..adapters.groq_adapter import GroqAdapter
from ..adapters.replicate_adapter import ReplicateAdapter
from ..adapters.deepinfra_adapter import DeepInfraAdapter
from ..adapters.cerebras_adapter import CerebrasAdapter
from ..adapters.scaleai_adapter import ScaleaiAdapter
from ..adapters.alibaba_adapter import AlibabaAdapter
from ..adapters.tencent_adapter import TencentAdapter
from ..adapters.oracle_oci_adapter import OracleOCIAdapter
from ..adapters.nvidia_dgx_adapter import NVIDIADGXAdapter
from ..adapters.ibm_watson_adapter import IBMWatsonAdapter
from ..adapters.spell_adapter import SpellAdapter
from ..adapters.kaggle_adapter import KaggleAdapter
from ..adapters.runai_adapter import RunAIAdapter

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for all provider adapters"""

    _adapters: Dict[str, Type[BaseProviderAdapter]] = {}

    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[BaseProviderAdapter]):
        """Register a new adapter"""
        cls._adapters[name] = adapter_class
        logger.info(f"Registered adapter: {name}")

    @classmethod
    def get_adapter(cls, name: str) -> BaseProviderAdapter:
        """Get adapter instance by name"""
        adapter_class = cls._adapters.get(name)
        if not adapter_class:
            raise ValueError(f"Unknown provider: {name}")
        return adapter_class()

    @classmethod
    def list_adapters(cls) -> List[str]:
        """List all registered adapter names"""
        return list(cls._adapters.keys())

    @classmethod
    def initialize_registry(cls):
        """Initialize with all available adapters"""
        adapters = [
            ("vast_ai", VastAiAdapter),
            ("core_weave", CoreWeaveAdapter),
            ("huggingface", HuggingFaceAdapter),
            ("aws_sagemaker", AWSSageMakerAdapter),
            ("azure_ml", AzureMLAdapter),
            ("google_vertex_ai", GoogleVertexAIAdapter),
            ("runpod", RunPodAdapter),
            ("lambdalabs", LambdaLabsAdapter),
            ("paperspace", PaperspaceAdapter),
            ("groq", GroqAdapter),
            ("replicate", ReplicateAdapter),
            ("deepinfra", DeepInfraAdapter),
            ("cerebras", CerebrasAdapter),
            ("scaleai", ScaleaiAdapter),
            ("alibaba", AlibabaAdapter),
            ("tencent", TencentAdapter),
            ("oracle_oci", OracleOCIAdapter),
            ("nvidia_dgx", NVIDIADGXAdapter),
            ("ibm_watson", IBMWatsonAdapter),
            ("spell", SpellAdapter),
            ("kaggle", KaggleAdapter),
            ("runai", RunAIAdapter),
        ]

        for name, adapter_class in adapters:
            cls.register_adapter(name, adapter_class)

        logger.info(f"Initialized registry with {len(adapters)} adapters")


# Initialize registry on import
ProviderRegistry.initialize_registry()
