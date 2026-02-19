"""
Decisions Models - GPUBROKERAGENT (ADMIN ONLY).

Tracks agent decision-making for GPU recommendations and optimizations.
"""

import uuid

from django.conf import settings
from django.db import models


class AgentDecision(models.Model):
    """
    Records agent decisions for GPU recommendations.

    Provides audit trail and explainability for agent actions.
    """

    class DecisionType(models.TextChoices):
        GPU_RECOMMENDATION = "gpu_recommendation", "GPU Recommendation"
        PROVIDER_SELECTION = "provider_selection", "Provider Selection"
        COST_OPTIMIZATION = "cost_optimization", "Cost Optimization"
        SCALING_SUGGESTION = "scaling_suggestion", "Scaling Suggestion"
        ALERT_RESPONSE = "alert_response", "Alert Response"

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXECUTED = "executed", "Executed"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    session = models.ForeignKey(
        "agent_core.AgentSession",
        on_delete=models.SET_NULL,
        null=True,
        related_name="decisions",
    )

    decision_type = models.CharField(max_length=50, choices=DecisionType.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PROPOSED
    )

    # Decision details
    title = models.CharField(max_length=255)
    description = models.TextField()
    reasoning = models.TextField()

    # Input data used for decision
    input_data = models.JSONField(default=dict)

    # Recommended action
    recommended_action = models.JSONField(default=dict)

    # Confidence and metrics
    confidence_score = models.FloatField(default=0.0)
    estimated_impact = models.JSONField(default=dict)

    # Approval workflow
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_decisions",
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True)

    # Execution tracking
    executed_at = models.DateTimeField(blank=True, null=True)
    execution_result = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "agent_decisions"
        verbose_name = "Agent Decision"
        verbose_name_plural = "Agent Decisions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.decision_type}: {self.title}"


class DecisionFeedback(models.Model):
    """
    Feedback on agent decisions for learning and improvement.
    """

    class Rating(models.IntegerChoices):
        VERY_POOR = 1, "Very Poor"
        POOR = 2, "Poor"
        NEUTRAL = 3, "Neutral"
        GOOD = 4, "Good"
        EXCELLENT = 5, "Excellent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    decision = models.ForeignKey(
        AgentDecision, on_delete=models.CASCADE, related_name="feedback"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="decision_feedback",
    )

    rating = models.IntegerField(choices=Rating.choices)
    comment = models.TextField(blank=True)

    # Specific feedback categories
    accuracy_rating = models.IntegerField(choices=Rating.choices, blank=True, null=True)
    usefulness_rating = models.IntegerField(
        choices=Rating.choices, blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_decision_feedback"
        verbose_name = "Decision Feedback"
        verbose_name_plural = "Decision Feedback"

    def __str__(self):
        return f"Feedback on {self.decision.title}: {self.rating}"
