"""
Agent Core Models - GPUBROKERAGENT (ADMIN ONLY).

Django wrapper for Agent Zero integration.
Provides ORM models for agent sessions, conversations, and tool executions.

NOTE: This is a Django layer ON TOP of Agent Zero.
We do NOT modify Agent Zero code - it's reference only.
"""

import uuid

from django.conf import settings
from django.db import models


class AgentSession(models.Model):
    """
    Agent Zero session tracking.

    Each session represents an interaction context with the agent.
    ADMIN ONLY access.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Admin user who initiated the session
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_sessions",
    )

    # POD context (if scoped to a specific POD)
    pod = models.ForeignKey(
        "pod_management.Pod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_sessions",
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )

    # Agent Zero internal session ID
    agent_zero_session_id = models.CharField(max_length=255, blank=True, null=True)

    # Session metadata
    context = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "agent_sessions"
        verbose_name = "Agent Session"
        verbose_name_plural = "Agent Sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session {self.id} by {self.admin_user.email}"


class AgentMessage(models.Model):
    """
    Messages in an agent conversation.
    """

    class Role(models.TextChoices):
        USER = "user", "User (Admin)"
        ASSISTANT = "assistant", "Assistant (Agent)"
        SYSTEM = "system", "System"
        TOOL = "tool", "Tool Result"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        AgentSession, on_delete=models.CASCADE, related_name="messages"
    )

    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()

    # Tool call information (if role is TOOL)
    tool_name = models.CharField(max_length=100, blank=True, null=True)
    tool_input = models.JSONField(default=dict, blank=True)
    tool_output = models.JSONField(default=dict, blank=True)

    # Metadata
    tokens_used = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_messages"
        verbose_name = "Agent Message"
        verbose_name_plural = "Agent Messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class AgentToolExecution(models.Model):
    """
    Log of tool executions by the agent.

    Tracks all tools invoked by Agent Zero for audit and debugging.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        TIMEOUT = "timeout", "Timeout"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        AgentSession, on_delete=models.CASCADE, related_name="tool_executions"
    )
    message = models.ForeignKey(
        AgentMessage,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tool_executions",
    )

    tool_name = models.CharField(max_length=100)
    tool_input = models.JSONField(default=dict)
    tool_output = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)

    # Performance metrics
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    duration_ms = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_tool_executions"
        verbose_name = "Agent Tool Execution"
        verbose_name_plural = "Agent Tool Executions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tool_name}: {self.status}"
