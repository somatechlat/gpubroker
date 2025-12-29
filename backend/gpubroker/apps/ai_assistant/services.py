"""
AI Assistant Services.

Business logic for AI assistant operations.
NO MOCKS. NO FAKE DATA. REAL IMPLEMENTATIONS ONLY.
"""
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import httpx

from .client import SomaAgentClient

logger = logging.getLogger('gpubroker.ai_assistant.services')

# Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "somagent")
SOMA_BASE = os.getenv("SOMA_AGENT_BASE", "")
# Internal Django service URLs (same process, but can be overridden for external services)
PROVIDER_API_URL = os.getenv("PROVIDER_API_URL", "http://localhost:8000/api/v2")
MATH_CORE_URL = os.getenv("MATH_CORE_URL", "http://localhost:8000/api/v2")
MAX_HISTORY_TURNS = int(os.getenv("AI_MAX_HISTORY_TURNS", "10"))


class AIAssistantService:
    """
    AI Assistant service for chat and workload parsing.
    
    Integrates with:
    - SomaAgent for LLM capabilities
    - Provider service for GPU offers
    - Math Core for recommendations
    """
    
    def __init__(self):
        self.llm_provider = LLM_PROVIDER
        self.max_history_turns = MAX_HISTORY_TURNS
    
    async def chat(
        self,
        message: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process chat message through SomaAgent.
        
        Args:
            message: User message
            user_id: Optional user/session identifier
            context: Additional context (filters, workload_profile)
            history: Conversation history
        
        Returns:
            Dict with reply, recommendations, elapsed_ms
        """
        start = time.time()
        context = context or {}
        history = history or []
        
        if not SOMA_BASE:
            raise ValueError("SOMA_AGENT_BASE environment variable not set")
        
        client = SomaAgentClient(base_url=SOMA_BASE)
        recommendations: Optional[List[Dict[str, Any]]] = None
        history_payload: Optional[List[Dict[str, Any]]] = None
        
        try:
            # Trim history to max turns
            trimmed_history = history[-self.max_history_turns:] if history else []
            messages = trimmed_history + [{"role": "user", "content": message}]
            
            # Invoke SomaAgent
            result = await client.invoke(
                messages=messages,
                session_id=user_id,
                tenant=None
            )
            reply = result.get("content") or result.get("reply") or ""
            
            # Fetch session history if user_id provided
            if user_id:
                try:
                    hist = await client.get_session_history(user_id, limit=50)
                    history_payload = hist.get("items") if isinstance(hist, dict) else hist
                except Exception as hist_err:
                    logger.warning(f"Session history fetch failed: {hist_err}")
            
            # Enrich with recommendations
            recommendations = await self._get_recommendations(user_id, context)
            
            elapsed_ms = (time.time() - start) * 1000
            
            return {
                "reply": reply,
                "sources": None,
                "elapsed_ms": elapsed_ms,
                "recommendations": recommendations,
                "session_history": history_payload
            }
        
        except Exception as e:
            logger.error(f"SomaAgent invoke failed: {e}")
            raise
        finally:
            await client.close()
    
    async def _get_recommendations(
        self,
        user_id: Optional[str],
        context: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch recommendations from Math Core."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as http:
                # Get candidate offers from provider service
                filters = context.get("filters", {})
                params = {"per_page": 20, **filters}
                
                prov_resp = await http.get(
                    f"{PROVIDER_API_URL}/providers",
                    params=params
                )
                prov_resp.raise_for_status()
                items = prov_resp.json().get("items", [])
                
                candidate_offers = []
                for it in items[:20]:
                    candidate_offers.append({
                        "price_per_hour": it.get("price_per_hour"),
                        "gpu": it.get("gpu") or it.get("name"),
                        "provider": it.get("provider"),
                        "region": it.get("region"),
                        "availability": it.get("availability"),
                        "compliance_tags": it.get("tags", []),
                        "gpu_memory_gb": it.get("gpu_memory_gb"),
                    })
                
                if not candidate_offers:
                    return None
                
                # Get ensemble recommendations
                payload = {
                    "user_id": user_id,
                    "workload_profile": context.get("workload_profile", {}),
                    "candidate_offers": candidate_offers,
                    "top_k": 5
                }
                
                rec_resp = await http.post(
                    f"{MATH_CORE_URL}/math/ensemble-recommend",
                    json=payload
                )
                rec_resp.raise_for_status()
                rec_data = rec_resp.json()
                
                return rec_data.get("recommendations", [])
        
        except Exception as e:
            logger.warning(f"Recommendation enrichment failed: {e}")
            return None
    
    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get conversation history for a session."""
        if not SOMA_BASE:
            raise ValueError("SOMA_AGENT_BASE environment variable not set")
        
        client = SomaAgentClient(base_url=SOMA_BASE)
        try:
            result = await client.get_session_history(session_id, limit=limit)
            return {
                "items": result.get("items", []) if isinstance(result, dict) else result,
                "session_id": session_id,
                "count": len(result.get("items", [])) if isinstance(result, dict) else len(result)
            }
        finally:
            await client.close()
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available LLM tools."""
        if not SOMA_BASE:
            raise ValueError("SOMA_AGENT_BASE environment variable not set")
        
        client = SomaAgentClient(base_url=SOMA_BASE)
        try:
            return await client.list_tools()
        finally:
            await client.close()
    
    async def health(self) -> Dict[str, Any]:
        """Check AI service health."""
        result = {
            "status": "ok",
            "llm_provider": self.llm_provider,
            "soma_agent_status": None
        }
        
        if SOMA_BASE:
            client = SomaAgentClient(base_url=SOMA_BASE)
            try:
                soma_health = await client.health()
                result["soma_agent_status"] = soma_health.get("status", "unknown")
            except Exception as e:
                logger.warning(f"SomaAgent health check failed: {e}")
                result["soma_agent_status"] = "unavailable"
            finally:
                await client.close()
        else:
            result["soma_agent_status"] = "not_configured"
        
        return result
    
    def parse_workload(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language workload description.
        
        Simple rule-based parsing for common patterns.
        """
        text_lower = text.lower()
        
        # Determine workload type
        if any(kw in text_lower for kw in ["token", "chat", "llm", "inference", "gpt", "llama"]):
            workload_type = "llm_inference"
        elif any(kw in text_lower for kw in ["image", "picture", "stable diffusion", "sdxl", "dall"]):
            workload_type = "image_generation"
        elif any(kw in text_lower for kw in ["train", "fine-tune", "finetune", "training"]):
            workload_type = "training"
        else:
            workload_type = "llm_inference"  # Default
        
        # Extract quantity
        quantity = None
        quantity_match = re.search(r'(\d+)\s*(image|token|request|sample)', text_lower)
        if quantity_match:
            quantity = int(quantity_match.group(1))
        
        # Extract duration
        duration = None
        duration_match = re.search(r'(\d+)\s*(hour|hr|minute|min|day)', text_lower)
        if duration_match:
            duration = f"{duration_match.group(1)} {duration_match.group(2)}"
        
        # Extract region
        region = None
        regions = ["us-east", "us-west", "eu-west", "eu-central", "asia", "ap-"]
        for r in regions:
            if r in text_lower:
                region = r
                break
        
        # Extract quality
        quality = None
        if "high" in text_lower or "quality" in text_lower:
            quality = "high"
        elif "draft" in text_lower or "fast" in text_lower:
            quality = "draft"
        else:
            quality = "standard"
        
        return {
            "workload_type": workload_type,
            "quantity": quantity,
            "duration": duration,
            "region": region,
            "quality": quality
        }


# Global instance
ai_assistant_service = AIAssistantService()


# ============================================
# Workload Templates
# ============================================

WORKLOAD_TEMPLATES = [
    {
        "id": "image_generation",
        "name": "Image Generation",
        "description": "Generate images using Stable Diffusion, SDXL, or similar models",
        "icon": "image",
        "category": "creative",
        "questions": [
            {
                "id": "model",
                "question": "Which image generation model will you use?",
                "field": "model_name",
                "type": "select",
                "options": ["SDXL", "Stable Diffusion 1.5", "Stable Diffusion 2.1", "Midjourney-style", "DALL-E style", "Other"],
                "default": "SDXL",
                "required": True,
                "validation": None
            },
            {
                "id": "quantity",
                "question": "How many images do you need to generate?",
                "field": "quantity",
                "type": "number",
                "options": None,
                "default": 100,
                "required": True,
                "validation": {"min": 1, "max": 100000}
            },
            {
                "id": "resolution",
                "question": "What resolution do you need?",
                "field": "quality",
                "type": "select",
                "options": ["512x512 (draft)", "768x768 (standard)", "1024x1024 (high)", "2048x2048 (ultra)"],
                "default": "1024x1024 (high)",
                "required": True,
                "validation": None
            },
            {
                "id": "duration",
                "question": "How long do you need the GPU for?",
                "field": "duration_hours",
                "type": "range",
                "options": None,
                "default": 1,
                "required": True,
                "validation": {"min": 0.5, "max": 720}
            },
            {
                "id": "region",
                "question": "Preferred region? (optional)",
                "field": "region",
                "type": "select",
                "options": ["Any", "us-east-1", "us-west-2", "eu-west-1", "eu-central-1", "ap-northeast-1"],
                "default": "Any",
                "required": False,
                "validation": None
            }
        ],
        "default_values": {
            "workload_type": "image_generation",
            "batch_size": 1
        },
        "gpu_recommendations": ["RTX 4090", "RTX 3090", "A100", "A10G"]
    },
    {
        "id": "llm_inference",
        "name": "LLM Inference",
        "description": "Run inference on large language models like LLaMA, Mistral, or GPT-style models",
        "icon": "chat",
        "category": "ai",
        "questions": [
            {
                "id": "model_size",
                "question": "What size model will you run?",
                "field": "model_name",
                "type": "select",
                "options": ["7B parameters", "13B parameters", "34B parameters", "70B parameters", "180B+ parameters"],
                "default": "7B parameters",
                "required": True,
                "validation": None
            },
            {
                "id": "tokens",
                "question": "Estimated tokens to process per hour?",
                "field": "quantity",
                "type": "number",
                "options": None,
                "default": 100000,
                "required": True,
                "validation": {"min": 1000, "max": 100000000}
            },
            {
                "id": "context_length",
                "question": "Maximum context length needed?",
                "field": "context_length",
                "type": "select",
                "options": ["2K tokens", "4K tokens", "8K tokens", "16K tokens", "32K tokens", "128K tokens"],
                "default": "4K tokens",
                "required": True,
                "validation": None
            },
            {
                "id": "duration",
                "question": "How long do you need the GPU for?",
                "field": "duration_hours",
                "type": "range",
                "options": None,
                "default": 1,
                "required": True,
                "validation": {"min": 0.5, "max": 720}
            },
            {
                "id": "quantization",
                "question": "Will you use quantization?",
                "field": "quantization",
                "type": "select",
                "options": ["None (FP16)", "INT8", "INT4 (GPTQ/AWQ)", "GGUF Q4"],
                "default": "None (FP16)",
                "required": False,
                "validation": None
            }
        ],
        "default_values": {
            "workload_type": "llm_inference",
            "batch_size": 1
        },
        "gpu_recommendations": ["H100", "A100", "RTX 4090", "L40S"]
    },
    {
        "id": "model_training",
        "name": "Model Training",
        "description": "Train or fine-tune machine learning models",
        "icon": "school",
        "category": "ai",
        "questions": [
            {
                "id": "training_type",
                "question": "What type of training?",
                "field": "training_type",
                "type": "select",
                "options": ["Full fine-tuning", "LoRA/QLoRA", "From scratch", "Transfer learning"],
                "default": "LoRA/QLoRA",
                "required": True,
                "validation": None
            },
            {
                "id": "model_size",
                "question": "Base model size?",
                "field": "model_name",
                "type": "select",
                "options": ["<1B parameters", "1-7B parameters", "7-13B parameters", "13-34B parameters", "34B+ parameters"],
                "default": "7-13B parameters",
                "required": True,
                "validation": None
            },
            {
                "id": "dataset_size",
                "question": "Training dataset size (samples)?",
                "field": "quantity",
                "type": "number",
                "options": None,
                "default": 10000,
                "required": True,
                "validation": {"min": 100, "max": 100000000}
            },
            {
                "id": "epochs",
                "question": "Number of training epochs?",
                "field": "epochs",
                "type": "number",
                "options": None,
                "default": 3,
                "required": True,
                "validation": {"min": 1, "max": 100}
            },
            {
                "id": "duration",
                "question": "Estimated training duration (hours)?",
                "field": "duration_hours",
                "type": "range",
                "options": None,
                "default": 8,
                "required": True,
                "validation": {"min": 1, "max": 720}
            },
            {
                "id": "multi_gpu",
                "question": "Do you need multi-GPU training?",
                "field": "multi_gpu",
                "type": "select",
                "options": ["Single GPU", "2 GPUs", "4 GPUs", "8 GPUs"],
                "default": "Single GPU",
                "required": False,
                "validation": None
            }
        ],
        "default_values": {
            "workload_type": "training",
            "batch_size": 8
        },
        "gpu_recommendations": ["H100", "A100", "RTX 4090", "A6000"]
    },
    {
        "id": "video_processing",
        "name": "Video Processing",
        "description": "Video encoding, transcoding, or AI-based video processing",
        "icon": "videocam",
        "category": "media",
        "questions": [
            {
                "id": "task_type",
                "question": "What video task?",
                "field": "task_type",
                "type": "select",
                "options": ["Transcoding (H.264/H.265)", "AI Upscaling", "AI Frame Interpolation", "Object Detection", "Video Generation"],
                "default": "Transcoding (H.264/H.265)",
                "required": True,
                "validation": None
            },
            {
                "id": "duration_minutes",
                "question": "Total video duration to process (minutes)?",
                "field": "quantity",
                "type": "number",
                "options": None,
                "default": 60,
                "required": True,
                "validation": {"min": 1, "max": 100000}
            },
            {
                "id": "resolution",
                "question": "Target resolution?",
                "field": "quality",
                "type": "select",
                "options": ["720p", "1080p", "1440p", "4K", "8K"],
                "default": "1080p",
                "required": True,
                "validation": None
            },
            {
                "id": "duration",
                "question": "How long do you need the GPU for?",
                "field": "duration_hours",
                "type": "range",
                "options": None,
                "default": 2,
                "required": True,
                "validation": {"min": 0.5, "max": 720}
            }
        ],
        "default_values": {
            "workload_type": "video_processing",
            "batch_size": 1
        },
        "gpu_recommendations": ["RTX 4090", "A100", "L40S", "RTX 3090"]
    },
    {
        "id": "data_processing",
        "name": "Data Processing",
        "description": "GPU-accelerated data processing, ETL, or analytics",
        "icon": "analytics",
        "category": "data",
        "questions": [
            {
                "id": "framework",
                "question": "Which framework will you use?",
                "field": "framework",
                "type": "select",
                "options": ["RAPIDS cuDF", "Dask-CUDA", "PyTorch DataLoader", "TensorFlow Data", "Custom CUDA"],
                "default": "RAPIDS cuDF",
                "required": True,
                "validation": None
            },
            {
                "id": "data_size",
                "question": "Dataset size (GB)?",
                "field": "quantity",
                "type": "number",
                "options": None,
                "default": 100,
                "required": True,
                "validation": {"min": 1, "max": 100000}
            },
            {
                "id": "memory_requirement",
                "question": "Estimated GPU memory needed?",
                "field": "min_vram_gb",
                "type": "select",
                "options": ["8 GB", "16 GB", "24 GB", "48 GB", "80 GB"],
                "default": "24 GB",
                "required": True,
                "validation": None
            },
            {
                "id": "duration",
                "question": "How long do you need the GPU for?",
                "field": "duration_hours",
                "type": "range",
                "options": None,
                "default": 4,
                "required": True,
                "validation": {"min": 0.5, "max": 720}
            }
        ],
        "default_values": {
            "workload_type": "data_processing",
            "batch_size": 1
        },
        "gpu_recommendations": ["A100", "H100", "RTX 4090", "A6000"]
    }
]


class WorkloadTemplateService:
    """
    Service for workload templates and wizard flows.
    
    Provides template definitions and applies user answers
    to generate workload profiles.
    """
    
    def __init__(self):
        self.templates = {t["id"]: t for t in WORKLOAD_TEMPLATES}
    
    def list_templates(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        List all available templates.
        
        Args:
            category: Optional filter by category
        
        Returns:
            Dict with templates list and count
        """
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t["category"] == category]
        
        return {
            "templates": templates,
            "count": len(templates)
        }
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID."""
        return self.templates.get(template_id)
    
    def apply_template(
        self,
        template_id: str,
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply a template with user answers to generate workload profile.
        
        Args:
            template_id: Template to apply
            answers: User answers to template questions
        
        Returns:
            Dict with workload_profile, estimated_requirements, recommended_offers
        """
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Unknown template: {template_id}")
        
        # Start with default values
        workload_profile = dict(template["default_values"])
        
        # Apply answers
        for question in template["questions"]:
            field = question["field"]
            if field in answers:
                value = answers[field]
                # Validate if validation rules exist
                if question.get("validation"):
                    self._validate_answer(value, question["validation"])
                workload_profile[field] = value
            elif question.get("default") is not None:
                workload_profile[field] = question["default"]
        
        # Estimate requirements based on workload profile
        estimated_requirements = self._estimate_requirements(template_id, workload_profile)
        
        return {
            "workload_profile": workload_profile,
            "estimated_requirements": estimated_requirements,
            "recommended_offers": None  # Will be populated by API layer
        }
    
    def _validate_answer(self, value: Any, validation: Dict[str, Any]) -> None:
        """Validate an answer against validation rules."""
        if "min" in validation and value < validation["min"]:
            raise ValueError(f"Value {value} is below minimum {validation['min']}")
        if "max" in validation and value > validation["max"]:
            raise ValueError(f"Value {value} exceeds maximum {validation['max']}")
    
    def _estimate_requirements(
        self,
        template_id: str,
        workload_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimate GPU requirements based on workload profile.
        
        Returns min/recommended VRAM, GPU tiers, and cost estimates.
        """
        workload_type = workload_profile.get("workload_type", template_id)
        
        if workload_type == "image_generation":
            return self._estimate_image_gen(workload_profile)
        elif workload_type == "llm_inference":
            return self._estimate_llm_inference(workload_profile)
        elif workload_type == "training":
            return self._estimate_training(workload_profile)
        elif workload_type == "video_processing":
            return self._estimate_video(workload_profile)
        elif workload_type == "data_processing":
            return self._estimate_data_processing(workload_profile)
        else:
            return self._estimate_generic(workload_profile)
    
    def _estimate_image_gen(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate requirements for image generation."""
        quality = profile.get("quality", "1024x1024 (high)")
        
        # VRAM requirements by resolution
        vram_map = {
            "512x512 (draft)": (6, 8),
            "768x768 (standard)": (8, 12),
            "1024x1024 (high)": (10, 16),
            "2048x2048 (ultra)": (16, 24)
        }
        min_vram, rec_vram = vram_map.get(quality, (10, 16))
        
        # Time per image (seconds)
        time_map = {
            "512x512 (draft)": 2,
            "768x768 (standard)": 4,
            "1024x1024 (high)": 8,
            "2048x2048 (ultra)": 20
        }
        time_per_image = time_map.get(quality, 8)
        
        quantity = profile.get("quantity", 100)
        duration_hours = profile.get("duration_hours", 1)
        
        # Calculate if duration is sufficient
        total_time_needed = (quantity * time_per_image) / 3600  # hours
        
        return {
            "min_vram_gb": min_vram,
            "recommended_vram_gb": rec_vram,
            "recommended_gpu_tiers": ["RTX 4090", "RTX 3090", "A100"],
            "estimated_time_hours": round(total_time_needed, 2),
            "duration_sufficient": duration_hours >= total_time_needed,
            "estimated_cost_range": {
                "low": round(total_time_needed * 0.50, 2),
                "high": round(total_time_needed * 2.00, 2)
            },
            "confidence": 0.85
        }
    
    def _estimate_llm_inference(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate requirements for LLM inference."""
        model_name = profile.get("model_name", "7B parameters")
        quantization = profile.get("quantization", "None (FP16)")
        
        # Base VRAM by model size (FP16)
        vram_base = {
            "7B parameters": 14,
            "13B parameters": 26,
            "34B parameters": 68,
            "70B parameters": 140,
            "180B+ parameters": 360
        }
        base_vram = vram_base.get(model_name, 14)
        
        # Quantization reduction factors
        quant_factor = {
            "None (FP16)": 1.0,
            "INT8": 0.5,
            "INT4 (GPTQ/AWQ)": 0.25,
            "GGUF Q4": 0.25
        }
        factor = quant_factor.get(quantization, 1.0)
        
        min_vram = int(base_vram * factor * 0.8)
        rec_vram = int(base_vram * factor * 1.2)
        
        # Tokens per second estimate
        tps_estimate = {
            "7B parameters": 100,
            "13B parameters": 60,
            "34B parameters": 30,
            "70B parameters": 15,
            "180B+ parameters": 5
        }
        tps = tps_estimate.get(model_name, 50)
        
        quantity = profile.get("quantity", 100000)
        duration_hours = profile.get("duration_hours", 1)
        
        time_needed = quantity / (tps * 3600)
        
        return {
            "min_vram_gb": min_vram,
            "recommended_vram_gb": rec_vram,
            "recommended_gpu_tiers": ["H100", "A100", "RTX 4090"] if base_vram <= 80 else ["H100 SXM", "8xA100"],
            "estimated_tokens_per_second": tps,
            "estimated_time_hours": round(time_needed, 2),
            "duration_sufficient": duration_hours >= time_needed,
            "multi_gpu_required": rec_vram > 80,
            "estimated_cost_range": {
                "low": round(time_needed * 1.00, 2),
                "high": round(time_needed * 5.00, 2)
            },
            "confidence": 0.80
        }
    
    def _estimate_training(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate requirements for model training."""
        model_name = profile.get("model_name", "7-13B parameters")
        training_type = profile.get("training_type", "LoRA/QLoRA")
        
        # Base VRAM by model size for training
        vram_base = {
            "<1B parameters": 8,
            "1-7B parameters": 16,
            "7-13B parameters": 32,
            "13-34B parameters": 48,
            "34B+ parameters": 80
        }
        base_vram = vram_base.get(model_name, 32)
        
        # Training type multiplier
        type_factor = {
            "Full fine-tuning": 3.0,
            "LoRA/QLoRA": 1.0,
            "From scratch": 4.0,
            "Transfer learning": 2.0
        }
        factor = type_factor.get(training_type, 1.5)
        
        min_vram = int(base_vram * factor * 0.8)
        rec_vram = int(base_vram * factor)
        
        return {
            "min_vram_gb": min_vram,
            "recommended_vram_gb": rec_vram,
            "recommended_gpu_tiers": ["H100", "A100", "A6000"] if rec_vram <= 80 else ["8xH100", "8xA100"],
            "multi_gpu_required": rec_vram > 80,
            "estimated_cost_range": {
                "low": round(profile.get("duration_hours", 8) * 2.00, 2),
                "high": round(profile.get("duration_hours", 8) * 8.00, 2)
            },
            "confidence": 0.75
        }
    
    def _estimate_video(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate requirements for video processing."""
        task_type = profile.get("task_type", "Transcoding (H.264/H.265)")
        quality = profile.get("quality", "1080p")
        
        # VRAM by task type
        vram_map = {
            "Transcoding (H.264/H.265)": (4, 8),
            "AI Upscaling": (8, 16),
            "AI Frame Interpolation": (8, 16),
            "Object Detection": (6, 12),
            "Video Generation": (16, 24)
        }
        min_vram, rec_vram = vram_map.get(task_type, (8, 16))
        
        # Adjust for resolution
        res_factor = {"720p": 0.5, "1080p": 1.0, "1440p": 1.5, "4K": 2.0, "8K": 4.0}
        factor = res_factor.get(quality, 1.0)
        
        return {
            "min_vram_gb": int(min_vram * factor),
            "recommended_vram_gb": int(rec_vram * factor),
            "recommended_gpu_tiers": ["RTX 4090", "A100", "L40S"],
            "estimated_cost_range": {
                "low": round(profile.get("duration_hours", 2) * 0.50, 2),
                "high": round(profile.get("duration_hours", 2) * 3.00, 2)
            },
            "confidence": 0.80
        }
    
    def _estimate_data_processing(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate requirements for data processing."""
        min_vram_str = profile.get("min_vram_gb", "24 GB")
        
        # Parse VRAM string
        vram_map = {"8 GB": 8, "16 GB": 16, "24 GB": 24, "48 GB": 48, "80 GB": 80}
        min_vram = vram_map.get(min_vram_str, 24)
        
        return {
            "min_vram_gb": min_vram,
            "recommended_vram_gb": min_vram,
            "recommended_gpu_tiers": ["A100", "H100", "RTX 4090"],
            "estimated_cost_range": {
                "low": round(profile.get("duration_hours", 4) * 1.00, 2),
                "high": round(profile.get("duration_hours", 4) * 4.00, 2)
            },
            "confidence": 0.85
        }
    
    def _estimate_generic(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generic estimation fallback."""
        return {
            "min_vram_gb": 16,
            "recommended_vram_gb": 24,
            "recommended_gpu_tiers": ["RTX 4090", "A100", "RTX 3090"],
            "estimated_cost_range": {
                "low": round(profile.get("duration_hours", 1) * 0.50, 2),
                "high": round(profile.get("duration_hours", 1) * 3.00, 2)
            },
            "confidence": 0.60
        }


# Global template service instance
workload_template_service = WorkloadTemplateService()


# ============================================
# AI Context Awareness Service (Task 15.1)
# Requirements: 25.1, 25.2, 25.3, 25.4
# ============================================

class AIContextAwarenessService:
    """
    Service for AI context awareness features.
    
    Provides:
    - Screen context integration for AI responses
    - Search analysis and insights
    - Context-aware chat with visible offers awareness
    """
    
    def __init__(self):
        self.ai_service = ai_assistant_service
    
    def analyze_search(
        self,
        screen_context: Dict[str, Any],
        user_id: Optional[str] = None,
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze current search context and provide insights.
        
        Args:
            screen_context: Current screen state (filters, visible_offers, etc.)
            user_id: Optional user identifier
            question: Optional specific question about the search
        
        Returns:
            Dict with summary, insights, best_match, suggestions
        
        Requirements: 25.1, 25.2, 25.3
        """
        import time
        start = time.time()
        
        filters = screen_context.get("current_filters", {})
        visible_offers = screen_context.get("visible_offers", [])
        sort_by = screen_context.get("sort_by")
        sort_order = screen_context.get("sort_order", "asc")
        
        insights = []
        suggestions = []
        best_match = None
        
        # Analyze visible offers
        if visible_offers:
            # Calculate statistics
            prices = [o.get("price_per_hour", 0) for o in visible_offers if o.get("price_per_hour")]
            vrams = [o.get("gpu_memory_gb", 0) for o in visible_offers if o.get("gpu_memory_gb")]
            
            if prices:
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)
                
                # Price range insight
                if max_price > min_price * 3:
                    insights.append({
                        "type": "observation",
                        "title": "Wide Price Range",
                        "description": f"Prices vary significantly from ${min_price:.2f} to ${max_price:.2f}/hr. Consider narrowing your search with price filters.",
                        "confidence": 0.9,
                        "related_offers": None
                    })
                
                # Budget-friendly options
                budget_offers = [o for o in visible_offers if o.get("price_per_hour", 999) < avg_price * 0.7]
                if budget_offers:
                    insights.append({
                        "type": "recommendation",
                        "title": "Budget-Friendly Options Available",
                        "description": f"Found {len(budget_offers)} offers below average price. These may offer good value.",
                        "confidence": 0.85,
                        "related_offers": [o.get("id") for o in budget_offers[:3] if o.get("id")]
                    })
            
            if vrams:
                # VRAM distribution insight
                high_vram = [o for o in visible_offers if o.get("gpu_memory_gb", 0) >= 48]
                if high_vram and len(high_vram) < len(visible_offers) * 0.2:
                    insights.append({
                        "type": "tip",
                        "title": "Limited High-VRAM Options",
                        "description": f"Only {len(high_vram)} offers have 48GB+ VRAM. Consider expanding region filters for more options.",
                        "confidence": 0.8,
                        "related_offers": [o.get("id") for o in high_vram if o.get("id")]
                    })
            
            # Availability insight
            available = [o for o in visible_offers if o.get("availability_status") == "available"]
            if len(available) < len(visible_offers) * 0.5:
                insights.append({
                    "type": "warning",
                    "title": "Limited Availability",
                    "description": f"Only {len(available)} of {len(visible_offers)} offers are immediately available. Consider booking soon.",
                    "confidence": 0.95,
                    "related_offers": None
                })
            
            # Find best match based on sort criteria or balanced score
            if visible_offers:
                if sort_by == "price_per_hour" and sort_order == "asc":
                    best_match = min(visible_offers, key=lambda x: x.get("price_per_hour", 999))
                elif sort_by == "gpu_memory_gb" and sort_order == "desc":
                    best_match = max(visible_offers, key=lambda x: x.get("gpu_memory_gb", 0))
                else:
                    # Balanced score: normalize price (lower better) and VRAM (higher better)
                    def score(o):
                        price = o.get("price_per_hour", 999)
                        vram = o.get("gpu_memory_gb", 0)
                        avail = 1 if o.get("availability_status") == "available" else 0.5
                        # Lower price better, higher VRAM better, available better
                        return (vram / max(vrams) if vrams and max(vrams) > 0 else 0) * 0.4 + \
                               (1 - price / max(prices) if prices and max(prices) > 0 else 0) * 0.4 + \
                               avail * 0.2
                    best_match = max(visible_offers, key=score)
        
        # Generate suggestions based on filters
        if not filters:
            suggestions.append("Add filters to narrow down results (e.g., GPU type, region, price range)")
        else:
            if not filters.get("gpu_type"):
                suggestions.append("Specify a GPU type for more targeted results")
            if not filters.get("region"):
                suggestions.append("Add a region filter to find nearby providers with lower latency")
            if filters.get("price_max") and prices and min(prices) > filters.get("price_max", 0) * 0.8:
                suggestions.append("Consider increasing your price limit for more options")
        
        # Generate summary
        if visible_offers:
            gpu_types = list(set(o.get("gpu_type", "Unknown") for o in visible_offers))
            regions = list(set(o.get("region", "Unknown") for o in visible_offers))
            summary = f"Found {len(visible_offers)} GPU offers across {len(gpu_types)} GPU types in {len(regions)} regions. "
            if prices:
                summary += f"Prices range from ${min(prices):.2f} to ${max(prices):.2f}/hr."
        else:
            summary = "No offers match your current filters. Try broadening your search criteria."
            suggestions.append("Remove some filters to see more results")
        
        elapsed_ms = (time.time() - start) * 1000
        
        return {
            "summary": summary,
            "insights": insights,
            "best_match": best_match,
            "suggestions": suggestions,
            "elapsed_ms": elapsed_ms
        }
    
    async def context_aware_chat(
        self,
        message: str,
        user_id: Optional[str] = None,
        screen_context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process chat with screen context awareness.
        
        Enriches the AI context with current screen state for
        more relevant responses.
        
        Args:
            message: User message
            user_id: Optional user identifier
            screen_context: Current screen state
            history: Conversation history
        
        Returns:
            Dict with reply, context_used, referenced_offers, etc.
        
        Requirements: 25.1, 25.2, 25.3, 25.4
        """
        import time
        start = time.time()
        
        context_used = False
        referenced_offers = []
        suggested_filters = None
        
        # Build enriched context from screen state
        enriched_context = {}
        
        if screen_context:
            context_used = True
            filters = screen_context.get("current_filters", {})
            visible_offers = screen_context.get("visible_offers", [])
            selected_offer_id = screen_context.get("selected_offer_id")
            current_page = screen_context.get("current_page")
            
            # Add filters to context
            if filters:
                enriched_context["filters"] = filters
            
            # Summarize visible offers for context
            if visible_offers:
                offer_summary = self._summarize_offers(visible_offers)
                enriched_context["visible_offers_summary"] = offer_summary
                enriched_context["visible_offer_count"] = len(visible_offers)
                
                # If user asks about specific offers, include details
                if any(kw in message.lower() for kw in ["this", "these", "current", "showing", "visible", "displayed"]):
                    enriched_context["visible_offers"] = visible_offers[:10]  # Limit for context size
            
            # Include selected offer details
            if selected_offer_id:
                selected = next((o for o in visible_offers if o.get("id") == selected_offer_id), None)
                if selected:
                    enriched_context["selected_offer"] = selected
                    referenced_offers.append(selected_offer_id)
            
            # Page context
            if current_page:
                enriched_context["current_page"] = current_page
            
            # Detect intent and suggest filter changes
            suggested_filters = self._detect_filter_suggestions(message, filters, visible_offers)
        
        # Call the main chat service with enriched context
        try:
            result = await self.ai_service.chat(
                message=message,
                user_id=user_id,
                context=enriched_context,
                history=history
            )
            reply = result.get("reply", "")
            recommendations = result.get("recommendations")
        except ValueError as e:
            # SomaAgent not configured - provide rule-based response
            reply = self._generate_rule_based_response(message, enriched_context)
            recommendations = None
        
        # Extract referenced offers from response
        if screen_context and screen_context.get("visible_offers"):
            for offer in screen_context["visible_offers"]:
                offer_id = offer.get("id")
                gpu_type = offer.get("gpu_type", "")
                if offer_id and (offer_id in reply or gpu_type.lower() in reply.lower()):
                    if offer_id not in referenced_offers:
                        referenced_offers.append(offer_id)
        
        elapsed_ms = (time.time() - start) * 1000
        
        return {
            "reply": reply,
            "context_used": context_used,
            "referenced_offers": referenced_offers if referenced_offers else None,
            "suggested_filters": suggested_filters,
            "recommendations": recommendations,
            "elapsed_ms": elapsed_ms
        }
    
    def _summarize_offers(self, offers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize visible offers for context."""
        if not offers:
            return {}
        
        prices = [o.get("price_per_hour", 0) for o in offers if o.get("price_per_hour")]
        vrams = [o.get("gpu_memory_gb", 0) for o in offers if o.get("gpu_memory_gb")]
        gpu_types = list(set(o.get("gpu_type", "Unknown") for o in offers))
        regions = list(set(o.get("region", "Unknown") for o in offers))
        providers = list(set(o.get("provider", "Unknown") for o in offers))
        
        return {
            "count": len(offers),
            "price_range": {"min": min(prices), "max": max(prices), "avg": sum(prices)/len(prices)} if prices else None,
            "vram_range": {"min": min(vrams), "max": max(vrams)} if vrams else None,
            "gpu_types": gpu_types[:5],
            "regions": regions[:5],
            "providers": providers[:5],
            "available_count": len([o for o in offers if o.get("availability_status") == "available"])
        }
    
    def _detect_filter_suggestions(
        self,
        message: str,
        current_filters: Dict[str, Any],
        visible_offers: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Detect if user message implies filter changes."""
        message_lower = message.lower()
        suggestions = {}
        
        # GPU type mentions
        gpu_keywords = {
            "a100": "A100",
            "h100": "H100",
            "4090": "RTX 4090",
            "rtx 4090": "RTX 4090",
            "3090": "RTX 3090",
            "rtx 3090": "RTX 3090",
            "v100": "V100",
            "l40": "L40S",
            "a6000": "A6000"
        }
        for kw, gpu_type in gpu_keywords.items():
            if kw in message_lower and current_filters.get("gpu_type") != gpu_type:
                suggestions["gpu_type"] = gpu_type
                break
        
        # Region mentions
        region_keywords = {
            "us-east": "us-east-1",
            "us-west": "us-west-2",
            "europe": "eu-west-1",
            "eu-": "eu-west-1",
            "asia": "ap-northeast-1",
            "ap-": "ap-northeast-1"
        }
        for kw, region in region_keywords.items():
            if kw in message_lower and current_filters.get("region") != region:
                suggestions["region"] = region
                break
        
        # Price mentions
        if "cheap" in message_lower or "budget" in message_lower or "affordable" in message_lower:
            if visible_offers:
                prices = [o.get("price_per_hour", 0) for o in visible_offers if o.get("price_per_hour")]
                if prices:
                    suggestions["price_max"] = round(sum(prices) / len(prices) * 0.7, 2)
        
        if "expensive" in message_lower or "premium" in message_lower or "high-end" in message_lower:
            if visible_offers:
                prices = [o.get("price_per_hour", 0) for o in visible_offers if o.get("price_per_hour")]
                if prices:
                    suggestions["price_min"] = round(sum(prices) / len(prices) * 1.3, 2)
        
        # VRAM mentions
        import re
        vram_match = re.search(r'(\d+)\s*gb', message_lower)
        if vram_match:
            vram_value = int(vram_match.group(1))
            if vram_value in [8, 10, 12, 16, 24, 32, 40, 48, 80]:
                suggestions["gpu_memory_min"] = vram_value
        
        return suggestions if suggestions else None
    
    def _generate_rule_based_response(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate rule-based response when LLM is unavailable."""
        message_lower = message.lower()
        
        # Check for common intents
        if any(kw in message_lower for kw in ["recommend", "suggest", "best", "which"]):
            summary = context.get("visible_offers_summary", {})
            if summary:
                count = summary.get("count", 0)
                price_range = summary.get("price_range", {})
                gpu_types = summary.get("gpu_types", [])
                
                if price_range:
                    return f"Based on your current search showing {count} offers, " \
                           f"prices range from ${price_range.get('min', 0):.2f} to ${price_range.get('max', 0):.2f}/hr. " \
                           f"Available GPU types include: {', '.join(gpu_types[:3])}. " \
                           f"For the best value, look for offers near the average price of ${price_range.get('avg', 0):.2f}/hr."
            return "I can help you find the best GPU for your needs. Please describe your workload or apply some filters to narrow down the options."
        
        if any(kw in message_lower for kw in ["compare", "difference", "vs", "versus"]):
            return "To compare GPUs, select multiple offers from your search results. I can help analyze the differences in price, performance, and availability."
        
        if any(kw in message_lower for kw in ["price", "cost", "expensive", "cheap"]):
            summary = context.get("visible_offers_summary", {})
            price_range = summary.get("price_range", {})
            if price_range:
                return f"Current prices range from ${price_range.get('min', 0):.2f} to ${price_range.get('max', 0):.2f}/hr. " \
                       f"The average is ${price_range.get('avg', 0):.2f}/hr. Use the price filter to narrow down to your budget."
            return "I can help you find GPUs within your budget. What's your target price range per hour?"
        
        if any(kw in message_lower for kw in ["available", "availability", "now", "immediately"]):
            summary = context.get("visible_offers_summary", {})
            available = summary.get("available_count", 0)
            total = summary.get("count", 0)
            if total > 0:
                return f"{available} out of {total} offers are immediately available. Filter by 'Available' status to see only ready-to-use GPUs."
            return "Check the availability status filter to find GPUs that are ready to use immediately."
        
        # Default response
        filters = context.get("filters", {})
        if filters:
            filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items())
            return f"I see you're searching with filters: {filter_desc}. How can I help you refine your search or find the best GPU for your needs?"
        
        return "I'm here to help you find the perfect GPU. Tell me about your workload (e.g., LLM inference, image generation, training) and I'll suggest the best options."


# Global context awareness service instance
ai_context_service = AIContextAwarenessService()
