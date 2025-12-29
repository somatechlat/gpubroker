"""
AI Assistant Tests.

Tests for:
- Workload parsing
- Workload templates
- Template wizard flows
- Template application
"""
import pytest

from apps.ai_assistant.services import (
    ai_assistant_service,
    workload_template_service,
    WORKLOAD_TEMPLATES,
)


# ============================================
# Workload Parsing Tests
# ============================================

class TestWorkloadParsing:
    """Tests for natural language workload parsing."""
    
    def test_parse_image_generation(self):
        """Test parsing image generation workload."""
        result = ai_assistant_service.parse_workload(
            "I need to generate 500 images using Stable Diffusion"
        )
        
        assert result["workload_type"] == "image_generation"
        assert result["quantity"] == 500
    
    def test_parse_llm_inference(self):
        """Test parsing LLM inference workload."""
        result = ai_assistant_service.parse_workload(
            "I want to run inference on a 7B LLM model for 1000 tokens"
        )
        
        assert result["workload_type"] == "llm_inference"
        assert result["quantity"] == 1000
    
    def test_parse_training(self):
        """Test parsing training workload."""
        result = ai_assistant_service.parse_workload(
            "I need to fine-tune a model with 10000 samples"
        )
        
        assert result["workload_type"] == "training"
        assert result["quantity"] == 10000
    
    def test_parse_duration(self):
        """Test parsing duration from text."""
        result = ai_assistant_service.parse_workload(
            "Generate images for 4 hours"
        )
        
        assert result["duration"] == "4 hour"
    
    def test_parse_region(self):
        """Test parsing region from text."""
        result = ai_assistant_service.parse_workload(
            "I need a GPU in us-east region"
        )
        
        assert result["region"] == "us-east"
    
    def test_parse_quality_high(self):
        """Test parsing high quality setting."""
        result = ai_assistant_service.parse_workload(
            "Generate high quality images"
        )
        
        assert result["quality"] == "high"
    
    def test_parse_quality_draft(self):
        """Test parsing draft quality setting."""
        result = ai_assistant_service.parse_workload(
            "Generate draft images fast"
        )
        
        assert result["quality"] == "draft"
    
    def test_parse_default_workload_type(self):
        """Test default workload type for ambiguous input."""
        result = ai_assistant_service.parse_workload(
            "I need a GPU for my project"
        )
        
        # Default to llm_inference
        assert result["workload_type"] == "llm_inference"


# ============================================
# Workload Template Tests
# ============================================

class TestWorkloadTemplates:
    """Tests for workload template service."""
    
    def test_list_all_templates(self):
        """Test listing all templates."""
        result = workload_template_service.list_templates()
        
        assert "templates" in result
        assert "count" in result
        assert result["count"] == 5
        assert len(result["templates"]) == 5
    
    def test_list_templates_by_category(self):
        """Test filtering templates by category."""
        result = workload_template_service.list_templates(category="ai")
        
        assert result["count"] == 2  # llm_inference and model_training
        for template in result["templates"]:
            assert template["category"] == "ai"
    
    def test_list_templates_creative_category(self):
        """Test filtering templates by creative category."""
        result = workload_template_service.list_templates(category="creative")
        
        assert result["count"] == 1  # image_generation
        assert result["templates"][0]["id"] == "image_generation"
    
    def test_get_template_by_id(self):
        """Test getting a specific template."""
        template = workload_template_service.get_template("image_generation")
        
        assert template is not None
        assert template["id"] == "image_generation"
        assert template["name"] == "Image Generation"
        assert "questions" in template
        assert len(template["questions"]) > 0
    
    def test_get_template_not_found(self):
        """Test getting non-existent template returns None."""
        template = workload_template_service.get_template("nonexistent")
        
        assert template is None
    
    def test_template_has_required_fields(self):
        """Test all templates have required fields."""
        for template in WORKLOAD_TEMPLATES:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "icon" in template
            assert "category" in template
            assert "questions" in template
            assert "default_values" in template
            assert "gpu_recommendations" in template
    
    def test_template_questions_have_required_fields(self):
        """Test all template questions have required fields."""
        for template in WORKLOAD_TEMPLATES:
            for question in template["questions"]:
                assert "id" in question
                assert "question" in question
                assert "field" in question
                assert "type" in question
                assert "required" in question


# ============================================
# Template Application Tests
# ============================================

class TestTemplateApplication:
    """Tests for applying templates with answers."""
    
    def test_apply_image_generation_template(self):
        """Test applying image generation template."""
        result = workload_template_service.apply_template(
            template_id="image_generation",
            answers={
                "model_name": "SDXL",
                "quantity": 100,
                "quality": "1024x1024 (high)",
                "duration_hours": 2,
                "region": "us-east-1"
            }
        )
        
        assert "workload_profile" in result
        assert "estimated_requirements" in result
        
        profile = result["workload_profile"]
        assert profile["workload_type"] == "image_generation"
        assert profile["quantity"] == 100
        assert profile["quality"] == "1024x1024 (high)"
        
        requirements = result["estimated_requirements"]
        assert "min_vram_gb" in requirements
        assert "recommended_vram_gb" in requirements
        assert "recommended_gpu_tiers" in requirements
        assert requirements["min_vram_gb"] >= 8
    
    def test_apply_llm_inference_template(self):
        """Test applying LLM inference template."""
        result = workload_template_service.apply_template(
            template_id="llm_inference",
            answers={
                "model_name": "7B parameters",
                "quantity": 100000,
                "context_length": "4K tokens",
                "duration_hours": 1,
                "quantization": "None (FP16)"
            }
        )
        
        profile = result["workload_profile"]
        assert profile["workload_type"] == "llm_inference"
        
        requirements = result["estimated_requirements"]
        assert requirements["min_vram_gb"] >= 10
        assert "estimated_tokens_per_second" in requirements
    
    def test_apply_training_template(self):
        """Test applying training template."""
        result = workload_template_service.apply_template(
            template_id="model_training",
            answers={
                "training_type": "LoRA/QLoRA",
                "model_name": "7-13B parameters",
                "quantity": 10000,
                "epochs": 3,
                "duration_hours": 8
            }
        )
        
        profile = result["workload_profile"]
        assert profile["workload_type"] == "training"
        
        requirements = result["estimated_requirements"]
        assert requirements["min_vram_gb"] >= 20
    
    def test_apply_template_with_defaults(self):
        """Test applying template uses defaults for missing answers."""
        result = workload_template_service.apply_template(
            template_id="image_generation",
            answers={}  # No answers, use all defaults
        )
        
        profile = result["workload_profile"]
        assert profile["workload_type"] == "image_generation"
        assert profile["quantity"] == 100  # Default
        assert profile["model_name"] == "SDXL"  # Default
    
    def test_apply_template_unknown_id(self):
        """Test applying unknown template raises error."""
        with pytest.raises(ValueError, match="Unknown template"):
            workload_template_service.apply_template(
                template_id="nonexistent",
                answers={}
            )
    
    def test_apply_template_validation_min(self):
        """Test template validation rejects values below minimum."""
        with pytest.raises(ValueError, match="below minimum"):
            workload_template_service.apply_template(
                template_id="image_generation",
                answers={"quantity": 0}  # Min is 1
            )
    
    def test_apply_template_validation_max(self):
        """Test template validation rejects values above maximum."""
        with pytest.raises(ValueError, match="exceeds maximum"):
            workload_template_service.apply_template(
                template_id="image_generation",
                answers={"quantity": 1000000}  # Max is 100000
            )


# ============================================
# Requirement Estimation Tests
# ============================================

class TestRequirementEstimation:
    """Tests for GPU requirement estimation."""
    
    def test_image_gen_vram_by_resolution(self):
        """Test VRAM estimation varies by resolution."""
        result_draft = workload_template_service.apply_template(
            "image_generation",
            {"quality": "512x512 (draft)"}
        )
        result_ultra = workload_template_service.apply_template(
            "image_generation",
            {"quality": "2048x2048 (ultra)"}
        )
        
        # Ultra should require more VRAM
        assert (result_ultra["estimated_requirements"]["min_vram_gb"] > 
                result_draft["estimated_requirements"]["min_vram_gb"])
    
    def test_llm_vram_by_model_size(self):
        """Test VRAM estimation varies by model size."""
        result_7b = workload_template_service.apply_template(
            "llm_inference",
            {"model_name": "7B parameters"}
        )
        result_70b = workload_template_service.apply_template(
            "llm_inference",
            {"model_name": "70B parameters"}
        )
        
        # 70B should require more VRAM
        assert (result_70b["estimated_requirements"]["min_vram_gb"] > 
                result_7b["estimated_requirements"]["min_vram_gb"])
    
    def test_llm_vram_with_quantization(self):
        """Test quantization reduces VRAM requirements."""
        result_fp16 = workload_template_service.apply_template(
            "llm_inference",
            {"model_name": "7B parameters", "quantization": "None (FP16)"}
        )
        result_int4 = workload_template_service.apply_template(
            "llm_inference",
            {"model_name": "7B parameters", "quantization": "INT4 (GPTQ/AWQ)"}
        )
        
        # INT4 should require less VRAM
        assert (result_int4["estimated_requirements"]["min_vram_gb"] < 
                result_fp16["estimated_requirements"]["min_vram_gb"])
    
    def test_training_vram_by_type(self):
        """Test training VRAM varies by training type."""
        result_lora = workload_template_service.apply_template(
            "model_training",
            {"training_type": "LoRA/QLoRA", "model_name": "7-13B parameters"}
        )
        result_full = workload_template_service.apply_template(
            "model_training",
            {"training_type": "Full fine-tuning", "model_name": "7-13B parameters"}
        )
        
        # Full fine-tuning should require more VRAM
        assert (result_full["estimated_requirements"]["min_vram_gb"] > 
                result_lora["estimated_requirements"]["min_vram_gb"])
    
    def test_duration_sufficient_flag(self):
        """Test duration_sufficient flag is calculated correctly."""
        # Short duration for many images
        result_short = workload_template_service.apply_template(
            "image_generation",
            {"quantity": 10000, "duration_hours": 0.5, "quality": "1024x1024 (high)"}
        )
        
        # Long duration for few images
        result_long = workload_template_service.apply_template(
            "image_generation",
            {"quantity": 10, "duration_hours": 10, "quality": "1024x1024 (high)"}
        )
        
        assert result_short["estimated_requirements"]["duration_sufficient"] is False
        assert result_long["estimated_requirements"]["duration_sufficient"] is True
    
    def test_cost_range_estimation(self):
        """Test cost range is estimated."""
        result = workload_template_service.apply_template(
            "image_generation",
            {"quantity": 100, "duration_hours": 2}
        )
        
        cost_range = result["estimated_requirements"]["estimated_cost_range"]
        assert "low" in cost_range
        assert "high" in cost_range
        assert cost_range["low"] < cost_range["high"]
        assert cost_range["low"] > 0
    
    def test_confidence_score(self):
        """Test confidence score is included."""
        result = workload_template_service.apply_template(
            "image_generation",
            {"quantity": 100}
        )
        
        assert "confidence" in result["estimated_requirements"]
        assert 0 <= result["estimated_requirements"]["confidence"] <= 1


# ============================================
# API Endpoint Tests
# ============================================

@pytest.mark.django_db
class TestAIAssistantAPI:
    """Tests for AI assistant API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_templates_endpoint(self, api_client):
        """Test GET /ai/templates endpoint."""
        response = await api_client.get('/ai/templates')
        
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "count" in data
        assert data["count"] == 5
    
    @pytest.mark.asyncio
    async def test_list_templates_with_category(self, api_client):
        """Test GET /ai/templates with category filter."""
        response = await api_client.get('/ai/templates?category=ai')
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
    
    @pytest.mark.asyncio
    async def test_get_template_endpoint(self, api_client):
        """Test GET /ai/templates/{template_id} endpoint."""
        response = await api_client.get('/ai/templates/image_generation')
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "image_generation"
        assert "questions" in data
    
    @pytest.mark.asyncio
    async def test_get_template_not_found(self, api_client):
        """Test GET /ai/templates/{template_id} for unknown template."""
        response = await api_client.get('/ai/templates/nonexistent')
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_apply_template_endpoint(self, api_client):
        """Test POST /ai/templates/apply endpoint."""
        response = await api_client.post('/ai/templates/apply', json={
            "template_id": "image_generation",
            "answers": {
                "quantity": 100,
                "quality": "1024x1024 (high)",
                "duration_hours": 2
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "workload_profile" in data
        assert "estimated_requirements" in data
        assert data["workload_profile"]["workload_type"] == "image_generation"
    
    @pytest.mark.asyncio
    async def test_apply_template_invalid_template(self, api_client):
        """Test POST /ai/templates/apply with invalid template."""
        response = await api_client.post('/ai/templates/apply', json={
            "template_id": "nonexistent",
            "answers": {}
        })
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_parse_workload_endpoint(self, api_client):
        """Test POST /ai/parse-workload endpoint."""
        response = await api_client.post('/ai/parse-workload', json={
            "text": "I need to generate 500 images using Stable Diffusion"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["workload_type"] == "image_generation"
        assert data["quantity"] == 500
