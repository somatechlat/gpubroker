"""
Agent Zero Service - GPUBROKERAGENT (ADMIN ONLY).

Service for managing Agent Zero integration.
Provides start, stop, pause, resume operations.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from django.utils import timezone as django_timezone

from ..decisions.models import AgentDecision
from .models import AgentMessage, AgentSession

logger = logging.getLogger("gpubroker.agent_zero")


class AgentStatus(Enum):
    """Agent Zero operational status."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class AgentDecisionRecord:
    """Record of an autonomous decision made by Agent Zero."""

    decision_id: str
    timestamp: datetime
    action_type: str  # provision, scale, terminate, optimize
    target_resource: str
    provider: str
    reasoning: str
    estimated_cost: float
    actual_cost: float | None = None
    status: str = "pending"  # pending, approved, executed, rejected, failed
    admin_override: bool = False
    admin_notes: str | None = None


class AgentZeroService:
    """
    Service for managing Agent Zero integration.

    ADMIN ONLY ACCESS - Controls autonomous GPU procurement.

    Requirements: 3.1, 3.2
    """

    def __init__(self, pod_id: str):
        self.pod_id = pod_id
        self.status = AgentStatus.STOPPED
        self.budget_limit: Decimal = Decimal("0.0")
        self.budget_used: Decimal = Decimal("0.0")
        self._agent_instance = None
        self._current_session: AgentSession | None = None
        self._decisions: list[AgentDecisionRecord] = []

    async def start(self, budget_limit: float, admin_user=None) -> dict[str, Any]:
        """
        Start Agent Zero with budget limit.

        ADMIN ONLY.

        Requirements: 3.1, 3.5
        """
        if self.status == AgentStatus.RUNNING:
            return {"error": "Agent already running", "status": self.status.value}

        self.budget_limit = Decimal(str(budget_limit))
        self.status = AgentStatus.STARTING

        try:
            # Create a new session
            self._current_session = await self._create_session(admin_user)

            # Initialize Agent Zero from TMP/agent-zero
            self._agent_instance = await self._initialize_agent()

            self.status = AgentStatus.RUNNING

            logger.info(
                f"Agent Zero started for POD {self.pod_id} with budget ${budget_limit}",
                extra={
                    "pod_id": self.pod_id,
                    "budget_limit": budget_limit,
                    "session_id": (
                        str(self._current_session.id) if self._current_session else None
                    ),
                },
            )

            return {
                "success": True,
                "status": self.status.value,
                "budget_limit": float(self.budget_limit),
                "pod_id": self.pod_id,
                "session_id": (
                    str(self._current_session.id) if self._current_session else None
                ),
            }

        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Failed to start Agent Zero: {e}")
            return {"error": str(e), "status": self.status.value}

    async def stop(self) -> dict[str, Any]:
        """
        Stop Agent Zero.

        ADMIN ONLY.

        Requirements: 3.1
        """
        if self.status not in [AgentStatus.RUNNING, AgentStatus.PAUSED]:
            return {"error": "Agent not running", "status": self.status.value}

        # End current session
        if self._current_session:
            self._current_session.status = AgentSession.Status.COMPLETED
            self._current_session.ended_at = django_timezone.now()
            await self._save_session(self._current_session)

        self.status = AgentStatus.STOPPED
        self._agent_instance = None

        logger.info(f"Agent Zero stopped for POD {self.pod_id}")

        return {
            "success": True,
            "status": self.status.value,
            "message": "Agent stopped successfully",
        }

    async def pause(self) -> dict[str, Any]:
        """
        Pause Agent Zero (no new decisions).

        ADMIN ONLY.

        Requirements: 3.1
        """
        if self.status != AgentStatus.RUNNING:
            return {"error": "Agent not running", "status": self.status.value}

        self.status = AgentStatus.PAUSED

        if self._current_session:
            self._current_session.status = AgentSession.Status.PAUSED
            await self._save_session(self._current_session)

        logger.info(f"Agent Zero paused for POD {self.pod_id}")

        return {
            "success": True,
            "status": self.status.value,
            "message": "Agent paused successfully",
        }

    async def resume(self) -> dict[str, Any]:
        """
        Resume Agent Zero.

        ADMIN ONLY.

        Requirements: 3.1
        """
        if self.status != AgentStatus.PAUSED:
            return {"error": "Agent not paused", "status": self.status.value}

        self.status = AgentStatus.RUNNING

        if self._current_session:
            self._current_session.status = AgentSession.Status.ACTIVE
            await self._save_session(self._current_session)

        logger.info(f"Agent Zero resumed for POD {self.pod_id}")

        return {
            "success": True,
            "status": self.status.value,
            "message": "Agent resumed successfully",
        }

    async def get_status(self) -> dict[str, Any]:
        """
        Get Agent Zero status.

        ADMIN ONLY.

        Requirements: 3.3
        """
        budget_used = await self._calculate_budget_used()
        pending_count = len([d for d in self._decisions if d.status == "pending"])

        return {
            "status": self.status.value,
            "pod_id": self.pod_id,
            "budget_limit": float(self.budget_limit),
            "budget_used": float(budget_used),
            "budget_remaining": float(self.budget_limit - budget_used),
            "budget_percentage": (
                float(budget_used / self.budget_limit * 100)
                if self.budget_limit > 0
                else 0
            ),
            "decisions_count": len(self._decisions),
            "pending_decisions": pending_count,
            "session_id": (
                str(self._current_session.id) if self._current_session else None
            ),
        }

    async def get_decisions(
        self, limit: int = 100, status_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get recent decisions.

        ADMIN ONLY.

        Requirements: 3.6
        """
        decisions = self._decisions

        if status_filter:
            decisions = [d for d in decisions if d.status == status_filter]

        return [
            {
                "decision_id": d.decision_id,
                "timestamp": d.timestamp.isoformat(),
                "action_type": d.action_type,
                "target_resource": d.target_resource,
                "provider": d.provider,
                "reasoning": d.reasoning,
                "estimated_cost": d.estimated_cost,
                "actual_cost": d.actual_cost,
                "status": d.status,
                "admin_override": d.admin_override,
                "admin_notes": d.admin_notes,
            }
            for d in decisions[-limit:]
        ]

    async def override_decision(
        self,
        decision_id: str,
        action: str,  # approve, reject
        notes: str,
        admin_user=None,
    ) -> dict[str, Any]:
        """
        Override an agent decision.

        ADMIN ONLY.

        Requirements: 3.7
        """
        decision = next(
            (d for d in self._decisions if d.decision_id == decision_id), None
        )

        if not decision:
            return {"error": "Decision not found"}

        if decision.status not in ["pending", "proposed"]:
            return {"error": f"Cannot override decision with status: {decision.status}"}

        decision.admin_override = True
        decision.admin_notes = notes

        if action == "approve":
            decision.status = "approved"
            # Execute the decision
            result = await self._execute_decision(decision)
            if result.get("success"):
                decision.status = "executed"
                decision.actual_cost = result.get(
                    "actual_cost", decision.estimated_cost
                )
        elif action == "reject":
            decision.status = "rejected"
        else:
            return {"error": f"Invalid action: {action}. Must be 'approve' or 'reject'"}

        # Persist to database
        await self._persist_decision(decision, admin_user)

        logger.info(
            f"Decision {decision_id} {action}ed by admin",
            extra={
                "decision_id": decision_id,
                "action": action,
                "notes": notes,
                "admin": str(admin_user) if admin_user else "unknown",
            },
        )

        return {
            "success": True,
            "decision_id": decision_id,
            "status": decision.status,
            "message": f"Decision {action}ed successfully",
        }

    async def set_budget_limit(self, new_limit: float) -> dict[str, Any]:
        """
        Update budget limit.

        ADMIN ONLY.

        Requirements: 3.5
        """
        old_limit = self.budget_limit
        self.budget_limit = Decimal(str(new_limit))

        logger.info(
            f"Budget limit changed from ${old_limit} to ${new_limit}",
            extra={
                "pod_id": self.pod_id,
                "old_limit": float(old_limit),
                "new_limit": new_limit,
            },
        )

        return {
            "success": True,
            "old_limit": float(old_limit),
            "new_limit": new_limit,
            "budget_used": float(self.budget_used),
        }

    async def send_message(self, message: str, admin_user=None) -> dict[str, Any]:
        """
        Send a message to Agent Zero.

        ADMIN ONLY.
        """
        if self.status != AgentStatus.RUNNING:
            return {"error": "Agent not running", "status": self.status.value}

        if not self._current_session:
            return {"error": "No active session"}

        # Record user message
        user_message = await self._create_message(
            session=self._current_session,
            role=AgentMessage.Role.USER,
            content=message,
        )

        # Process with Agent Zero (placeholder)
        response = await self._process_message(message)

        # Record assistant response
        assistant_message = await self._create_message(
            session=self._current_session,
            role=AgentMessage.Role.ASSISTANT,
            content=response.get("content", ""),
            tokens_used=response.get("tokens_used", 0),
        )

        return {
            "success": True,
            "message_id": str(assistant_message.id),
            "response": response.get("content", ""),
            "tokens_used": response.get("tokens_used", 0),
        }

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _initialize_agent(self):
        """
        Initialize Agent Zero instance.

        This is a placeholder - actual implementation depends on Agent Zero API.
        Agent Zero source is in TMP/agent-zero (gitignored).
        """
        # In production, this would initialize the actual Agent Zero instance
        # For now, we return a placeholder
        logger.info(f"Initializing Agent Zero for POD {self.pod_id}")
        return {"initialized": True, "pod_id": self.pod_id}

    async def _calculate_budget_used(self) -> Decimal:
        """Calculate total budget used by executed decisions."""
        total = Decimal("0.0")
        for d in self._decisions:
            if d.status == "executed":
                cost = d.actual_cost or d.estimated_cost
                total += Decimal(str(cost))
        self.budget_used = total
        return total

    async def _execute_decision(self, decision: AgentDecisionRecord) -> dict[str, Any]:
        """
        Execute an approved decision.

        This would call the appropriate provider API.
        """
        logger.info(
            f"Executing decision {decision.decision_id}: {decision.action_type}",
            extra={
                "decision_id": decision.decision_id,
                "action_type": decision.action_type,
                "target": decision.target_resource,
                "provider": decision.provider,
            },
        )

        # Placeholder for actual execution
        # In production, this would call provider APIs
        return {
            "success": True,
            "actual_cost": decision.estimated_cost,
        }

    async def _create_session(self, admin_user) -> AgentSession:
        """Create a new agent session."""
        from django.db import sync_to_async

        @sync_to_async
        def create():
            return AgentSession.objects.create(
                admin_user=admin_user,
                status=AgentSession.Status.ACTIVE,
                context={
                    "pod_id": self.pod_id,
                    "budget_limit": float(self.budget_limit),
                },
            )

        return await create()

    async def _save_session(self, session: AgentSession):
        """Save session to database."""
        from django.db import sync_to_async

        @sync_to_async
        def save():
            session.save()

        await save()

    async def _create_message(
        self,
        session: AgentSession,
        role: str,
        content: str,
        tokens_used: int = 0,
    ) -> AgentMessage:
        """Create a new message in the session."""
        from django.db import sync_to_async

        @sync_to_async
        def create():
            return AgentMessage.objects.create(
                session=session,
                role=role,
                content=content,
                tokens_used=tokens_used,
            )

        return await create()

    async def _process_message(self, message: str) -> dict[str, Any]:
        """
        Process a message with Agent Zero.

        Placeholder - actual implementation depends on Agent Zero API.
        """
        # In production, this would call Agent Zero
        return {
            "content": f"Agent Zero received: {message}",
            "tokens_used": len(message.split()) * 2,  # Rough estimate
        }

    async def _persist_decision(self, decision: AgentDecisionRecord, admin_user=None):
        """Persist decision to database."""
        from django.db import sync_to_async

        @sync_to_async
        def save():
            AgentDecision.objects.update_or_create(
                id=decision.decision_id,
                defaults={
                    "session": self._current_session,
                    "decision_type": decision.action_type,
                    "status": decision.status,
                    "title": f"{decision.action_type}: {decision.target_resource}",
                    "description": decision.reasoning,
                    "reasoning": decision.reasoning,
                    "input_data": {
                        "target_resource": decision.target_resource,
                        "provider": decision.provider,
                    },
                    "recommended_action": {
                        "action_type": decision.action_type,
                        "estimated_cost": decision.estimated_cost,
                    },
                    "estimated_impact": {
                        "cost": decision.estimated_cost,
                    },
                    "approved_by": admin_user if decision.admin_override else None,
                    "approved_at": (
                        django_timezone.now() if decision.status == "approved" else None
                    ),
                    "rejection_reason": (
                        decision.admin_notes if decision.status == "rejected" else ""
                    ),
                    "executed_at": (
                        django_timezone.now() if decision.status == "executed" else None
                    ),
                    "execution_result": (
                        {
                            "actual_cost": decision.actual_cost,
                        }
                        if decision.actual_cost
                        else {}
                    ),
                },
            )

        await save()


# =========================================================================
# Service Registry
# =========================================================================

_agent_services: dict[str, AgentZeroService] = {}


def get_agent_service(pod_id: str) -> AgentZeroService:
    """
    Get Agent Zero service for a POD.

    Creates a new service if one doesn't exist.
    """
    if pod_id not in _agent_services:
        _agent_services[pod_id] = AgentZeroService(pod_id)
    return _agent_services[pod_id]


def remove_agent_service(pod_id: str) -> bool:
    """Remove Agent Zero service for a POD."""
    if pod_id in _agent_services:
        del _agent_services[pod_id]
        return True
    return False
