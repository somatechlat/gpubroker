"""
Budgets Models - GPUBROKERAGENT (ADMIN ONLY).

Manages agent operation budgets, token limits, and cost tracking.
"""
from django.db import models
from django.conf import settings
import uuid


class AgentBudget(models.Model):
    """
    Budget allocation for agent operations.
    
    Controls how much the agent can spend on:
    - LLM API calls (tokens)
    - Tool executions
    - External API calls
    """
    
    class BudgetType(models.TextChoices):
        TOKENS = 'tokens', 'Token Budget'
        API_CALLS = 'api_calls', 'API Call Budget'
        COST = 'cost', 'Cost Budget (USD)'
    
    class Period(models.TextChoices):
        HOURLY = 'hourly', 'Hourly'
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Scope: global or per-POD
    pod = models.ForeignKey(
        'pod_management.Pod',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='agent_budgets'
    )
    
    budget_type = models.CharField(max_length=20, choices=BudgetType.choices)
    period = models.CharField(max_length=20, choices=Period.choices)
    
    # Limits
    limit_value = models.DecimalField(max_digits=12, decimal_places=4)
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=80.0)
    
    # Current usage
    current_usage = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'agent_budgets'
        verbose_name = 'Agent Budget'
        verbose_name_plural = 'Agent Budgets'
    
    def __str__(self):
        scope = f" ({self.pod.name})" if self.pod else " (Global)"
        return f"{self.budget_type} {self.period}{scope}"
    
    @property
    def usage_percentage(self):
        if self.limit_value == 0:
            return 0
        return float(self.current_usage / self.limit_value * 100)
    
    @property
    def is_exceeded(self):
        return self.current_usage >= self.limit_value
    
    @property
    def is_warning(self):
        return self.usage_percentage >= float(self.warning_threshold)


class AgentUsageLog(models.Model):
    """
    Detailed log of agent resource usage.
    """
    
    class ResourceType(models.TextChoices):
        INPUT_TOKENS = 'input_tokens', 'Input Tokens'
        OUTPUT_TOKENS = 'output_tokens', 'Output Tokens'
        TOOL_CALL = 'tool_call', 'Tool Call'
        EXTERNAL_API = 'external_api', 'External API Call'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session = models.ForeignKey(
        'agent_core.AgentSession',
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    budget = models.ForeignKey(
        AgentBudget,
        on_delete=models.SET_NULL,
        null=True,
        related_name='usage_logs'
    )
    
    resource_type = models.CharField(max_length=50, choices=ResourceType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Context
    model_name = models.CharField(max_length=100, blank=True)
    tool_name = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'agent_usage_logs'
        verbose_name = 'Agent Usage Log'
        verbose_name_plural = 'Agent Usage Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.resource_type}: {self.quantity}"


class AgentCostReport(models.Model):
    """
    Aggregated cost reports for agent operations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    pod = models.ForeignKey(
        'pod_management.Pod',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='agent_cost_reports'
    )
    
    # Time period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Aggregated metrics
    total_sessions = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    total_tool_calls = models.IntegerField(default=0)
    
    # Token usage
    total_input_tokens = models.BigIntegerField(default=0)
    total_output_tokens = models.BigIntegerField(default=0)
    
    # Costs
    llm_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    tool_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'agent_cost_reports'
        verbose_name = 'Agent Cost Report'
        verbose_name_plural = 'Agent Cost Reports'
        ordering = ['-period_end']
    
    def __str__(self):
        scope = f" ({self.pod.name})" if self.pod else " (Global)"
        return f"Cost Report{scope}: {self.period_start} - {self.period_end}"
