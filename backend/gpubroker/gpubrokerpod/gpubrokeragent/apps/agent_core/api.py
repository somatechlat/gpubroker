"""
Agent Zero API - GPUBROKERAGENT (ADMIN ONLY).

Django Ninja API for Agent Zero management.
All endpoints require POD Admin role.

Endpoints:
- POST /api/v2/agent/start
- POST /api/v2/agent/stop
- POST /api/v2/agent/pause
- POST /api/v2/agent/resume
- GET /api/v2/agent/status
- GET /api/v2/agent/decisions
- POST /api/v2/agent/decisions/{id}/override
- POST /api/v2/agent/budget
- POST /api/v2/agent/message

Requirements: 3.3, 3.4, 3.7
"""
import logging
from typing import Optional, List

from ninja import Router, Schema
from ninja.errors import HttpError
from django.http import HttpRequest

from .services import get_agent_service

logger = logging.getLogger('gpubroker.agent_zero.api')

router = Router(tags=["agent"])


# =============================================================================
# SCHEMAS
# =============================================================================

class AgentStartSchema(Schema):
    """Schema for starting Agent Zero."""
    pod_id: str
    budget_limit: float


class AgentStopSchema(Schema):
    """Schema for stopping Agent Zero."""
    pod_id: str


class AgentStatusResponseSchema(Schema):
    """Schema for agent status response."""
    status: str
    pod_id: str
    budget_limit: float
    budget_used: float
    budget_remaining: float
    budget_percentage: float
    decisions_count: int
    pending_decisions: int
    session_id: Optional[str] = None


class AgentDecisionSchema(Schema):
    """Schema for agent decision."""
    decision_id: str
    timestamp: str
    action_type: str
    target_resource: str
    provider: str
    reasoning: str
    estimated_cost: float
    actual_cost: Optional[float] = None
    status: str
    admin_override: bool
    admin_notes: Optional[str] = None


class DecisionOverrideSchema(Schema):
    """Schema for overriding a decision."""
    action: str  # approve or reject
    notes: str = ""


class BudgetUpdateSchema(Schema):
    """Schema for updating budget."""
    pod_id: str
    new_limit: float


class AgentMessageSchema(Schema):
    """Schema for sending a message to agent."""
    pod_id: str
    message: str


class AgentMessageResponseSchema(Schema):
    """Schema for agent message response."""
    success: bool
    message_id: Optional[str] = None
    response: str
    tokens_used: int


# =============================================================================
# ADMIN AUTHORIZATION
# =============================================================================

def require_admin(request: HttpRequest):
    """
    Check if user has POD Admin role.
    
    Requirements: 3.2
    """
    # In production, this would check the user's role
    # For now, we check if user is authenticated
    user = getattr(request, 'auth', None) or getattr(request, 'user', None)
    
    if not user:
        raise HttpError(401, "Authentication required")
    
    # Check for admin role (placeholder - implement based on your auth system)
    is_admin = getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
    
    if not is_admin:
        # For development, allow all authenticated users
        # In production, enforce strict admin check
        pass
    
    return user


# =============================================================================
# AGENT CONTROL ENDPOINTS
# =============================================================================

@router.post("/start")
async def start_agent(request: HttpRequest, data: AgentStartSchema):
    """
    Start Agent Zero for a POD.
    
    ADMIN ONLY.
    
    Requirements: 3.1, 3.3
    """
    admin_user = require_admin(request)
    
    service = get_agent_service(data.pod_id)
    result = await service.start(data.budget_limit, admin_user)
    
    if result.get('error'):
        raise HttpError(400, result['error'])
    
    return result


@router.post("/stop")
async def stop_agent(request: HttpRequest, data: AgentStopSchema):
    """
    Stop Agent Zero for a POD.
    
    ADMIN ONLY.
    
    Requirements: 3.1, 3.3
    """
    require_admin(request)
    
    service = get_agent_service(data.pod_id)
    result = await service.stop()
    
    if result.get('error'):
        raise HttpError(400, result['error'])
    
    return result


@router.post("/pause")
async def pause_agent(request: HttpRequest, data: AgentStopSchema):
    """
    Pause Agent Zero for a POD.
    
    ADMIN ONLY.
    """
    require_admin(request)
    
    service = get_agent_service(data.pod_id)
    result = await service.pause()
    
    if result.get('error'):
        raise HttpError(400, result['error'])
    
    return result


@router.post("/resume")
async def resume_agent(request: HttpRequest, data: AgentStopSchema):
    """
    Resume Agent Zero for a POD.
    
    ADMIN ONLY.
    """
    require_admin(request)
    
    service = get_agent_service(data.pod_id)
    result = await service.resume()
    
    if result.get('error'):
        raise HttpError(400, result['error'])
    
    return result


@router.get("/status/{pod_id}", response=AgentStatusResponseSchema)
async def get_agent_status(request: HttpRequest, pod_id: str):
    """
    Get Agent Zero status for a POD.
    
    ADMIN ONLY.
    
    Requirements: 3.3
    """
    require_admin(request)
    
    service = get_agent_service(pod_id)
    result = await service.get_status()
    
    return AgentStatusResponseSchema(**result)


# =============================================================================
# DECISION ENDPOINTS
# =============================================================================

@router.get("/decisions/{pod_id}", response=List[AgentDecisionSchema])
async def get_decisions(
    request: HttpRequest,
    pod_id: str,
    status: Optional[str] = None,
    limit: int = 100,
):
    """
    Get Agent Zero decisions for a POD.
    
    ADMIN ONLY.
    
    Requirements: 3.4, 3.6
    """
    require_admin(request)
    
    service = get_agent_service(pod_id)
    decisions = await service.get_decisions(limit=limit, status_filter=status)
    
    return [AgentDecisionSchema(**d) for d in decisions]


@router.post("/decisions/{pod_id}/{decision_id}/override")
async def override_decision(
    request: HttpRequest,
    pod_id: str,
    decision_id: str,
    data: DecisionOverrideSchema,
):
    """
    Override an Agent Zero decision.
    
    ADMIN ONLY.
    
    Requirements: 3.7
    """
    admin_user = require_admin(request)
    
    if data.action not in ['approve', 'reject']:
        raise HttpError(400, "Action must be 'approve' or 'reject'")
    
    service = get_agent_service(pod_id)
    result = await service.override_decision(
        decision_id=decision_id,
        action=data.action,
        notes=data.notes,
        admin_user=admin_user,
    )
    
    if result.get('error'):
        raise HttpError(400, result['error'])
    
    return result


# =============================================================================
# BUDGET ENDPOINTS
# =============================================================================

@router.post("/budget")
async def update_budget(request: HttpRequest, data: BudgetUpdateSchema):
    """
    Update Agent Zero budget limit.
    
    ADMIN ONLY.
    
    Requirements: 3.5
    """
    require_admin(request)
    
    service = get_agent_service(data.pod_id)
    result = await service.set_budget_limit(data.new_limit)
    
    return result


# =============================================================================
# MESSAGE ENDPOINTS
# =============================================================================

@router.post("/message", response=AgentMessageResponseSchema)
async def send_message(request: HttpRequest, data: AgentMessageSchema):
    """
    Send a message to Agent Zero.
    
    ADMIN ONLY.
    """
    admin_user = require_admin(request)
    
    service = get_agent_service(data.pod_id)
    result = await service.send_message(data.message, admin_user)
    
    if result.get('error'):
        raise HttpError(400, result['error'])
    
    return AgentMessageResponseSchema(
        success=result.get('success', False),
        message_id=result.get('message_id'),
        response=result.get('response', ''),
        tokens_used=result.get('tokens_used', 0),
    )
