"""
AI Assistant Pydantic Schemas.

Request/Response models for AI assistant endpoints.
NO MOCKS. NO FAKE DATA. REAL SCHEMAS ONLY.
"""
from typing import Any, Dict, List, Optional

from ninja import Schema
from pydantic import Field


class ChatRequest(Schema):
    """Request for AI chat endpoint."""
    user_id: Optional[str] = None
    message: str = Field(..., min_length=1, description="User message")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Conversation history [{role, content}]"
    )


class ChatResponse(Schema):
    """Response from AI chat endpoint."""
    reply: str
    sources: Optional[List[str]] = None
    elapsed_ms: float
    recommendations: Optional[List[Dict[str, Any]]] = None
    session_history: Optional[List[Dict[str, Any]]] = None


class ParseWorkloadRequest(Schema):
    """Request for workload parsing."""
    text: str = Field(..., min_length=1, description="Natural language workload description")


class ParsedWorkload(Schema):
    """Parsed workload from natural language."""
    workload_type: str
    quantity: Optional[int] = None
    duration: Optional[str] = None
    region: Optional[str] = None
    quality: Optional[str] = None


class SessionHistoryResponse(Schema):
    """Response for session history."""
    items: List[Dict[str, Any]]
    session_id: str
    count: int


class ToolsResponse(Schema):
    """Response for available tools."""
    tools: List[Dict[str, Any]]


class HealthResponse(Schema):
    """Response for AI service health."""
    status: str
    llm_provider: str
    soma_agent_status: Optional[str] = None


# ============================================
# Workload Template Schemas
# ============================================

class TemplateQuestion(Schema):
    """A question in a template wizard flow."""
    id: str = Field(..., description="Unique question identifier")
    question: str = Field(..., description="Question text to display")
    field: str = Field(..., description="Field name this question populates")
    type: str = Field(..., description="Input type: text, number, select, range")
    options: Optional[List[str]] = Field(None, description="Options for select type")
    default: Optional[Any] = Field(None, description="Default value")
    required: bool = Field(default=True, description="Whether answer is required")
    validation: Optional[Dict[str, Any]] = Field(None, description="Validation rules")


class WorkloadTemplate(Schema):
    """A workload template with wizard questions."""
    id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Template description")
    icon: str = Field(..., description="Icon identifier for UI")
    category: str = Field(..., description="Template category")
    questions: List[TemplateQuestion] = Field(..., description="Wizard questions")
    default_values: Dict[str, Any] = Field(default_factory=dict, description="Default workload values")
    gpu_recommendations: List[str] = Field(default_factory=list, description="Recommended GPU types")


class TemplatesResponse(Schema):
    """Response for templates list."""
    templates: List[WorkloadTemplate]
    count: int


class TemplateApplyRequest(Schema):
    """Request to apply a template with answers."""
    template_id: str = Field(..., description="Template to apply")
    answers: Dict[str, Any] = Field(..., description="Answers to template questions")


class TemplateApplyResponse(Schema):
    """Response from applying a template."""
    workload_profile: Dict[str, Any] = Field(..., description="Generated workload profile")
    estimated_requirements: Dict[str, Any] = Field(..., description="Estimated GPU requirements")
    recommended_offers: Optional[List[Dict[str, Any]]] = Field(None, description="Recommended GPU offers")
