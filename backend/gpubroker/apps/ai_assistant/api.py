"""
AI Assistant API - Django Ninja Router.

Endpoints for AI chat, workload parsing, and session management.
NO MOCKS. NO FAKE DATA. REAL IMPLEMENTATIONS ONLY.
"""
import logging

from ninja import Router
from ninja.errors import HttpError

from .schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ParsedWorkload,
    ParseWorkloadRequest,
    SessionHistoryResponse,
    ToolsResponse,
    TemplatesResponse,
    TemplateApplyRequest,
    TemplateApplyResponse,
    WorkloadTemplate,
    # Context Awareness schemas (Task 15.1)
    AnalyzeSearchRequest,
    AnalyzeSearchResponse,
    ContextAwareChatRequest,
    ContextAwareChatResponse,
)
from .services import ai_assistant_service, workload_template_service, ai_context_service

logger = logging.getLogger('gpubroker.ai_assistant.api')

router = Router()


@router.post("/chat", response=ChatResponse)
async def chat(request, payload: ChatRequest):
    """
    Process chat message through AI assistant.
    
    Integrates with SomaAgent LLM and enriches responses
    with GPU recommendations from Math Core.
    """
    try:
        result = await ai_assistant_service.chat(
            message=payload.message,
            user_id=payload.user_id,
            context=payload.context,
            history=payload.history
        )
        return result
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        logger.exception(f"Chat failed: {e}")
        raise HttpError(502, "AI agent call failed")


@router.post("/parse-workload", response=ParsedWorkload)
async def parse_workload(request, payload: ParseWorkloadRequest):
    """
    Parse natural language workload description.
    
    Extracts workload type, quantity, duration, region, and quality
    from free-form text.
    """
    try:
        result = ai_assistant_service.parse_workload(payload.text)
        return result
    except Exception as e:
        logger.exception(f"Workload parsing failed: {e}")
        raise HttpError(500, "Workload parsing failed")


@router.get("/sessions/{session_id}/history", response=SessionHistoryResponse)
async def get_session_history(request, session_id: str, limit: int = 50):
    """
    Get conversation history for a session.
    
    Returns up to `limit` history items for the specified session.
    """
    try:
        result = await ai_assistant_service.get_session_history(
            session_id=session_id,
            limit=limit
        )
        return result
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        logger.exception(f"Session history fetch failed: {e}")
        raise HttpError(502, "Session history fetch failed")


@router.get("/tools", response=ToolsResponse)
async def list_tools(request):
    """
    List available LLM tools.
    
    Returns tools registered with SomaAgent.
    """
    try:
        result = await ai_assistant_service.list_tools()
        return {"tools": result.get("tools", []) if isinstance(result, dict) else result}
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        logger.exception(f"List tools failed: {e}")
        raise HttpError(502, "List tools failed")


@router.get("/health", response=HealthResponse)
async def ai_health(request):
    """
    Check AI assistant service health.
    
    Returns status of LLM provider and SomaAgent connection.
    """
    try:
        result = await ai_assistant_service.health()
        return result
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "llm_provider": "unknown",
            "soma_agent_status": "error"
        }


# ============================================
# Workload Template Endpoints
# ============================================

@router.get("/templates", response=TemplatesResponse)
async def list_templates(request, category: str = None):
    """
    List available workload templates.
    
    Returns templates for common GPU workloads with wizard questions.
    Optionally filter by category: creative, ai, media, data.
    """
    try:
        result = workload_template_service.list_templates(category=category)
        return result
    except Exception as e:
        logger.exception(f"List templates failed: {e}")
        raise HttpError(500, "Failed to list templates")


@router.post("/templates/apply", response=TemplateApplyResponse)
async def apply_template(request, payload: TemplateApplyRequest):
    """
    Apply a workload template with user answers.
    
    Generates a workload profile and estimates GPU requirements.
    Optionally returns recommended GPU offers.
    """
    try:
        result = workload_template_service.apply_template(
            template_id=payload.template_id,
            answers=payload.answers
        )
        
        # Optionally fetch recommended offers
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as http:
                # Get offers matching requirements
                min_vram = result["estimated_requirements"].get("min_vram_gb", 16)
                gpu_tiers = result["estimated_requirements"].get("recommended_gpu_tiers", [])
                
                params = {
                    "gpu_memory_min": min_vram,
                    "per_page": 10,
                    "availability": "available"
                }
                
                from .services import PROVIDER_API_URL
                resp = await http.get(f"{PROVIDER_API_URL}/providers", params=params)
                if resp.status_code == 200:
                    offers = resp.json().get("items", [])
                    # Filter by recommended GPU tiers if possible
                    if gpu_tiers:
                        filtered = [
                            o for o in offers 
                            if any(tier.lower() in (o.get("gpu", "") or o.get("name", "")).lower() 
                                   for tier in gpu_tiers)
                        ]
                        result["recommended_offers"] = filtered[:5] if filtered else offers[:5]
                    else:
                        result["recommended_offers"] = offers[:5]
        except Exception as offer_err:
            logger.warning(f"Failed to fetch recommended offers: {offer_err}")
            # Continue without offers
        
        return result
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        logger.exception(f"Apply template failed: {e}")
        raise HttpError(500, "Failed to apply template")


@router.get("/templates/{template_id}", response=WorkloadTemplate)
async def get_template(request, template_id: str):
    """
    Get a specific workload template by ID.
    
    Returns template definition with wizard questions.
    """
    template = workload_template_service.get_template(template_id)
    if not template:
        raise HttpError(404, f"Template not found: {template_id}")
    return template


# ============================================
# AI Context Awareness Endpoints (Task 15.1)
# Requirements: 25.1, 25.2, 25.3, 25.4
# ============================================

@router.post("/analyze-search", response=AnalyzeSearchResponse)
async def analyze_search(request, payload: AnalyzeSearchRequest):
    """
    Analyze current search context and provide insights.
    
    Takes the current screen state (filters, visible offers) and returns:
    - Summary of search results
    - Insights (recommendations, warnings, tips)
    - Best matching offer
    - Suggestions for filter adjustments
    
    Requirements: 25.1, 25.2, 25.3
    """
    try:
        result = ai_context_service.analyze_search(
            screen_context=payload.screen_context.dict(),
            user_id=payload.user_id,
            question=payload.question
        )
        return result
    except Exception as e:
        logger.exception(f"Analyze search failed: {e}")
        raise HttpError(500, "Failed to analyze search context")


@router.post("/context-chat", response=ContextAwareChatResponse)
async def context_aware_chat(request, payload: ContextAwareChatRequest):
    """
    Process chat message with screen context awareness.
    
    Enriches AI responses with awareness of:
    - Current search filters
    - Visible GPU offers
    - Selected offer details
    - Current page/view
    
    Returns context-aware response with:
    - AI reply
    - Whether context was used
    - Referenced offer IDs
    - Suggested filter changes
    - GPU recommendations
    
    Requirements: 25.1, 25.2, 25.3, 25.4
    """
    try:
        screen_context_dict = payload.screen_context.dict() if payload.screen_context else None
        
        result = await ai_context_service.context_aware_chat(
            message=payload.message,
            user_id=payload.user_id,
            screen_context=screen_context_dict,
            history=payload.history
        )
        return result
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        logger.exception(f"Context-aware chat failed: {e}")
        raise HttpError(502, "AI context chat failed")
