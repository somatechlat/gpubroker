# Requirements Document: GPUBROKER Agent Zero Integration Layer

## Introduction

This document specifies the requirements for building a **GPUBROKER integration layer** that connects to Agent Zero. Agent Zero is treated as a **BLACK BOX** - we do NOT modify its code. We only build GPUBROKER Django components that communicate WITH Agent Zero via its existing APIs.

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      GPUBROKER POD                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              GPUBROKER Django Layer                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │ Agent       │  │ Budget      │  │ Audit           │  │   │
│  │  │ Proxy API   │  │ Controller  │  │ Logger          │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │   │
│  │         │                │                   │           │   │
│  │         └────────────────┼───────────────────┘           │   │
│  │                          │                               │   │
│  │                    ┌─────▼─────┐                         │   │
│  │                    │  Agent    │                         │   │
│  │                    │  Client   │                         │   │
│  │                    └─────┬─────┘                         │   │
│  └──────────────────────────┼───────────────────────────────┘   │
│                             │                                    │
│                             │ HTTP/WebSocket/MCP/A2A             │
│                             │                                    │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │              AGENT ZERO (BLACK BOX)                       │   │
│  │                                                           │   │
│  │  Runs AS-IS at backend/gpubroker/TMP/agent-zero/         │   │
│  │  - REST API at :port/api/                                │   │
│  │  - WebSocket at :port/ws/                                │   │
│  │  - MCP Server at :port/mcp/                              │   │
│  │  - A2A Protocol at :port/a2a/                            │   │
│  │                                                           │   │
│  │  WE DO NOT TOUCH THIS CODE                               │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Goals

| Goal | Description |
|------|-------------|
| **G1** | Build GPUBROKER Django proxy layer to communicate with Agent Zero |
| **G2** | Expose Agent Zero capabilities via GPUBROKER `/api/v2/` endpoints |
| **G3** | Implement RBAC: Agent Zero accessible ONLY by POD Admin |
| **G4** | Add budget controls and cost tracking on GPUBROKER side |
| **G5** | Add audit logging for all Agent Zero interactions |
| **G6** | Support SANDBOX/LIVE mode switching in GPUBROKER layer |

### What We DO NOT Do

| ❌ DO NOT | Reason |
|-----------|--------|
| Modify Agent Zero code | Black box - runs as-is |
| Migrate Agent Zero to Django | Not our code to change |
| Replace FAISS with Milvus in Agent Zero | Agent Zero uses what it uses |
| Change Agent Zero's internal APIs | We adapt to them |
| Touch `backend/gpubroker/TMP/agent-zero/` | Read-only reference |

---

## Glossary

- **Agent_Zero**: External AI agent framework (BLACK BOX, not modified)
- **Agent_Client**: GPUBROKER Django service that communicates with Agent Zero
- **Agent_Proxy_API**: GPUBROKER Django Ninja endpoints that wrap Agent Zero calls
- **POD_Admin**: Only role allowed to access Agent Zero features
- **Budget_Controller**: GPUBROKER service that tracks/limits Agent Zero costs

---

## Requirements

### Requirement 1: Agent Zero Client Service

**User Story:** As a GPUBROKER system, I want a client service to communicate with Agent Zero, so that I can proxy requests to the agent.

#### Acceptance Criteria

1. THE Agent_Client SHALL connect to Agent Zero's REST API endpoint
2. THE Agent_Client SHALL connect to Agent Zero's WebSocket endpoint for streaming
3. THE Agent_Client SHALL connect to Agent Zero's MCP endpoint for tool integration
4. THE Agent_Client SHALL connect to Agent Zero's A2A endpoint for agent-to-agent communication
5. THE Agent_Client SHALL handle Agent Zero authentication tokens
6. THE Agent_Client SHALL implement retry logic with exponential backoff
7. THE Agent_Client SHALL timeout requests after configurable duration (default: 300s)
8. THE Agent_Client SHALL be implemented as Django service at `gpubrokeragent/services/agent_client.py`
9. THE Agent_Client SHALL NOT modify any Agent Zero code

### Requirement 1.1: Agent Fleet Manager

**User Story:** As a GPUBROKER system, I want to manage multiple agent instances, so that I can orchestrate specialized agents for different tasks.

#### Acceptance Criteria

1. THE Fleet_Manager SHALL create and manage agent fleets per POD
2. THE Fleet_Manager SHALL spawn an Orchestrator agent (Agent 0) as the primary coordinator
3. THE Fleet_Manager SHALL spawn specialist agents via Agent Zero's `call_subordinate` tool
4. THE Fleet_Manager SHALL track agent hierarchy (parent-child relationships)
5. THE Fleet_Manager SHALL enforce maximum concurrent agents per POD (configurable)
6. THE Fleet_Manager SHALL track agent status (idle, busy, error, terminated)
7. THE Fleet_Manager SHALL load balance tasks across available agents
8. THE Fleet_Manager SHALL be implemented at `gpubrokeragent/services/fleet_manager.py`

### Requirement 1.2: Task Orchestrator

**User Story:** As a GPUBROKER system, I want to queue and route tasks to appropriate agents, so that work is distributed efficiently.

#### Acceptance Criteria

1. THE Task_Orchestrator SHALL maintain priority queues per POD
2. THE Task_Orchestrator SHALL route tasks to agents based on task type and agent role
3. THE Task_Orchestrator SHALL support task priorities: CRITICAL, HIGH, NORMAL, LOW
4. THE Task_Orchestrator SHALL require approval for high-impact tasks (deploy, terminate, scale)
5. THE Task_Orchestrator SHALL track task lifecycle (pending → queued → running → completed/failed)
6. THE Task_Orchestrator SHALL support task rejection with reason
7. THE Task_Orchestrator SHALL be implemented at `gpubrokeragent/services/task_orchestrator.py`

### Requirement 1.3: Agent Profiles

**User Story:** As a GPUBROKER system, I want specialized agent profiles, so that agents are optimized for specific GPU tasks.

#### Acceptance Criteria

1. THE System SHALL provide `gpubroker-orchestrator` profile for main coordination
2. THE System SHALL provide `gpubroker-provisioner` profile for GPU deployment
3. THE System SHALL provide `gpubroker-optimizer` profile for cost optimization
4. THE System SHALL provide `gpubroker-monitor` profile for health monitoring
5. THE System SHALL provide `gpubroker-provider` profile for provider-specific operations
6. THE Agent profiles SHALL be stored in `agents/` directory (Agent Zero configuration)
7. THE Agent profiles SHALL NOT modify Agent Zero code (configuration only)

### Requirement 2: Agent Proxy REST API

**User Story:** As a POD Admin, I want to interact with Agent Zero via GPUBROKER API, so that I have a unified interface.

#### Acceptance Criteria

1. THE System SHALL expose `/api/v2/agent/message` to send messages to Agent Zero
2. THE System SHALL expose `/api/v2/agent/sessions` to list active Agent Zero sessions
3. THE System SHALL expose `/api/v2/agent/sessions/{id}` to get session details
4. THE System SHALL expose `/api/v2/agent/sessions/{id}/terminate` to end sessions
5. THE System SHALL proxy all requests through Agent_Client to Agent Zero
6. THE System SHALL add GPUBROKER authentication before proxying
7. THE System SHALL log all requests to audit log before proxying

### Requirement 2.1: Agent Fleet API

**User Story:** As a POD Admin, I want to manage the agent fleet via API, so that I can control multi-agent operations.

#### Acceptance Criteria

1. THE System SHALL expose `/api/v2/agent/fleet` to get fleet status
2. THE System SHALL expose `/api/v2/agent/fleet/start` to start the agent fleet
3. THE System SHALL expose `/api/v2/agent/fleet/stop` to stop all agents
4. THE System SHALL expose `/api/v2/agent/agents` to list all agents in fleet
5. THE System SHALL expose `/api/v2/agent/agents/{id}` to get agent details
6. THE System SHALL expose `/api/v2/agent/agents/spawn` to spawn specialist agents
7. THE System SHALL expose `/api/v2/agent/agents/{id}/terminate` to terminate specific agent

### Requirement 2.2: Task Management API

**User Story:** As a POD Admin, I want to manage agent tasks via API, so that I can control what agents do.

#### Acceptance Criteria

1. THE System SHALL expose `/api/v2/agent/tasks` to list all tasks
2. THE System SHALL expose `/api/v2/agent/tasks` (POST) to submit new tasks
3. THE System SHALL expose `/api/v2/agent/tasks/{id}` to get task details
4. THE System SHALL expose `/api/v2/agent/tasks/{id}/approve` to approve pending tasks
5. THE System SHALL expose `/api/v2/agent/tasks/{id}/reject` to reject pending tasks
6. THE System SHALL support task types: FIND_GPU, DEPLOY_GPU, TERMINATE_GPU, SCALE_GPU, OPTIMIZE_COST, HEALTH_CHECK

### Requirement 2.3: Decision Management API

**User Story:** As a POD Admin, I want to review and override agent decisions, so that I maintain control over autonomous actions.

#### Acceptance Criteria

1. THE System SHALL expose `/api/v2/agent/decisions` to list all decisions
2. THE System SHALL expose `/api/v2/agent/decisions/{id}` to get decision details
3. THE System SHALL expose `/api/v2/agent/decisions/{id}/override` to approve/reject decisions
4. THE System SHALL require admin notes when overriding decisions
5. THE System SHALL log all overrides to audit trail

### Requirement 3: Agent Proxy WebSocket

**User Story:** As a POD Admin, I want real-time streaming from Agent Zero, so that I can see responses as they generate.

#### Acceptance Criteria

1. THE System SHALL expose `/ws/agent/{session_id}/` via Django Channels
2. THE WebSocket SHALL proxy messages to/from Agent Zero's WebSocket
3. THE WebSocket SHALL stream Agent Zero responses token-by-token to client
4. THE WebSocket SHALL authenticate connections via JWT
5. THE WebSocket SHALL enforce POD Admin role check
6. THE WebSocket SHALL handle reconnection gracefully
7. THE System SHALL log WebSocket events to audit log

### Requirement 4: RBAC - POD Admin Only Access

**User Story:** As a security engineer, I want Agent Zero accessible only by POD Admin, so that autonomous operations are controlled.

#### Acceptance Criteria

1. THE System SHALL restrict all `/api/v2/agent/*` endpoints to POD Admin role
2. THE System SHALL restrict all `/ws/agent/*` WebSocket connections to POD Admin role
3. WHEN non-admin user accesses agent endpoints, THE System SHALL return 403 Forbidden
4. THE System SHALL validate POD Admin role via Django permissions
5. THE System SHALL log all access attempts (successful and denied)
6. THE System SHALL enforce MFA for agent access in LIVE mode

### Requirement 5: Budget Controller

**User Story:** As a POD Admin, I want budget limits on Agent Zero usage, so that I can control costs.

#### Acceptance Criteria

1. THE Budget_Controller SHALL track estimated costs per Agent Zero session
2. THE Budget_Controller SHALL enforce budget limits per POD
3. WHEN budget threshold reached (50%, 75%, 90%), THE System SHALL send notification
4. WHEN budget exceeded, THE System SHALL block new Agent Zero requests
5. THE Budget_Controller SHALL store budget data in Django ORM
6. THE System SHALL expose `/api/v2/agent/budget` to view budget status
7. THE Budget_Controller SHALL reset budgets on configurable schedule

### Requirement 6: Audit Logging

**User Story:** As a security auditor, I want comprehensive logs of Agent Zero interactions, so that I can review autonomous decisions.

#### Acceptance Criteria

1. THE System SHALL log all messages sent to Agent Zero
2. THE System SHALL log all responses received from Agent Zero
3. THE System SHALL log session start/end events
4. THE System SHALL log budget threshold events
5. THE Audit_Log SHALL include: timestamp, user_id, pod_id, action, request, response
6. THE Audit_Log SHALL be stored in Django ORM model
7. THE System SHALL expose `/api/v2/agent/audit` to query audit logs (POD Admin only)

### Requirement 7: SANDBOX/LIVE Mode Support

**User Story:** As a POD Admin, I want SANDBOX mode to test Agent Zero integration, so that testing doesn't affect production.

#### Acceptance Criteria

1. THE System SHALL check POD's SANDBOX/LIVE mode before proxying to Agent Zero
2. WHEN in SANDBOX mode, THE System SHALL connect to Agent Zero with test configuration
3. WHEN in SANDBOX mode, THE System SHALL use mock budget tracking (no real limits)
4. WHEN in LIVE mode, THE System SHALL enforce real budget limits
5. THE System SHALL include mode indicator in all API responses
6. THE System SHALL log mode in all audit entries

### Requirement 8: Agent Zero Health Check

**User Story:** As a POD Admin, I want to know if Agent Zero is available, so that I can troubleshoot issues.

#### Acceptance Criteria

1. THE System SHALL expose `/api/v2/agent/health` endpoint
2. THE Health_Check SHALL ping Agent Zero's health endpoint
3. THE Health_Check SHALL return Agent Zero's status (up/down)
4. THE Health_Check SHALL return Agent Zero's version if available
5. THE Health_Check SHALL cache results for 30 seconds
6. THE System SHALL include Agent Zero health in POD status dashboard

### Requirement 9: Session Management

**User Story:** As a POD Admin, I want to manage Agent Zero sessions, so that I can control resource usage.

#### Acceptance Criteria

1. THE System SHALL track active Agent Zero sessions in Django ORM
2. THE System SHALL enforce maximum concurrent sessions per POD (configurable)
3. THE System SHALL auto-terminate idle sessions after timeout (configurable)
4. THE System SHALL allow manual session termination via API
5. THE System SHALL clean up session data on termination
6. THE System SHALL expose session list in admin dashboard

### Requirement 10: Configuration Management

**User Story:** As a POD Admin, I want to configure Agent Zero integration settings, so that I can customize behavior.

#### Acceptance Criteria

1. THE System SHALL store Agent Zero connection settings in AWS Parameter Store
2. THE System SHALL support configurable: endpoint URL, timeout, max sessions, budget limits
3. THE System SHALL hot-reload configuration changes without restart
4. THE System SHALL validate configuration before applying
5. THE System SHALL expose `/api/v2/agent/config` for viewing settings (POD Admin only)
6. THE System SHALL audit all configuration changes

---

## Data Models (GPUBROKER Django ORM)

### AgentSession Model

```python
# gpubrokeragent/apps/sessions/models.py
class AgentSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active'
        IDLE = 'idle'
        TERMINATED = 'terminated'
        ERROR = 'error'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    pod = models.ForeignKey('pods.Pod', on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    agent_zero_session_id = models.CharField(max_length=255)  # ID from Agent Zero
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    mode = models.CharField(max_length=10)  # SANDBOX or LIVE
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    terminated_at = models.DateTimeField(null=True)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    message_count = models.IntegerField(default=0)
```

### AgentAuditLog Model

```python
# gpubrokeragent/apps/audit/models.py
class AgentAuditLog(models.Model):
    class ActionType(models.TextChoices):
        MESSAGE_SENT = 'message_sent'
        RESPONSE_RECEIVED = 'response_received'
        SESSION_STARTED = 'session_started'
        SESSION_TERMINATED = 'session_terminated'
        BUDGET_WARNING = 'budget_warning'
        BUDGET_EXCEEDED = 'budget_exceeded'
        ACCESS_DENIED = 'access_denied'
        CONFIG_CHANGED = 'config_changed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    pod = models.ForeignKey('pods.Pod', on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    session = models.ForeignKey(AgentSession, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=30, choices=ActionType.choices)
    mode = models.CharField(max_length=10)  # SANDBOX or LIVE
    request_data = models.JSONField(null=True)
    response_data = models.JSONField(null=True)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### AgentBudget Model

```python
# gpubrokeragent/apps/budgets/models.py
class AgentBudget(models.Model):
    class ResetPeriod(models.TextChoices):
        DAILY = 'daily'
        WEEKLY = 'weekly'
        MONTHLY = 'monthly'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    pod = models.OneToOneField('pods.Pod', on_delete=models.CASCADE)
    limit_usd = models.DecimalField(max_digits=10, decimal_places=2)
    used_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reset_period = models.CharField(max_length=10, choices=ResetPeriod.choices, default=ResetPeriod.MONTHLY)
    last_reset_at = models.DateTimeField(auto_now_add=True)
    alert_threshold_50_sent = models.BooleanField(default=False)
    alert_threshold_75_sent = models.BooleanField(default=False)
    alert_threshold_90_sent = models.BooleanField(default=False)
```

---

## API Endpoints Summary

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/v2/agent/health` | GET | Check Agent Zero availability | POD Admin |
| `/api/v2/agent/message` | POST | Send message to Agent Zero | POD Admin |
| `/api/v2/agent/sessions` | GET | List active sessions | POD Admin |
| `/api/v2/agent/sessions/{id}` | GET | Get session details | POD Admin |
| `/api/v2/agent/sessions/{id}/terminate` | POST | Terminate session | POD Admin |
| `/api/v2/agent/budget` | GET | Get budget status | POD Admin |
| `/api/v2/agent/budget` | PATCH | Update budget limits | POD Admin |
| `/api/v2/agent/audit` | GET | Query audit logs | POD Admin |
| `/api/v2/agent/config` | GET | Get configuration | POD Admin |
| `/ws/agent/{session_id}/` | WebSocket | Real-time streaming | POD Admin |

---

## Integration Points

### Agent Zero Connection

```python
# gpubrokeragent/services/agent_client.py
class AgentZeroClient:
    """
    Client to communicate with Agent Zero BLACK BOX.
    We do NOT modify Agent Zero - we only call its APIs.
    """
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url  # e.g., "http://localhost:50001"
        self.token = token
    
    async def send_message(self, message: str, session_id: str = None) -> dict:
        """Send message to Agent Zero REST API"""
        # Calls Agent Zero's /api/message endpoint
        pass
    
    async def connect_websocket(self, session_id: str) -> WebSocket:
        """Connect to Agent Zero WebSocket for streaming"""
        # Connects to Agent Zero's /ws/ endpoint
        pass
    
    async def health_check(self) -> dict:
        """Check Agent Zero health"""
        # Calls Agent Zero's health endpoint
        pass
    
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate Agent Zero session"""
        # Calls Agent Zero's session termination endpoint
        pass
```

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| Unauthorized access | POD Admin role required for all endpoints |
| Cost overrun | Budget limits enforced in GPUBROKER layer |
| Audit trail | All interactions logged before proxying |
| Token exposure | Agent Zero tokens stored in AWS Secrets Manager |
| Mode confusion | Clear SANDBOX/LIVE indicators in all responses |

---

## Performance Requirements

| Metric | Target | Notes |
|--------|--------|-------|
| Proxy latency overhead | ≤50ms | GPUBROKER layer adds minimal latency |
| WebSocket relay latency | ≤20ms | Near real-time streaming |
| Health check response | ≤1s | Cached for 30s |
| Audit log write | Async | Non-blocking |
| Max concurrent sessions | 10/POD | Configurable |

---

## References

| Document | Location | Description |
|----------|----------|-------------|
| Agent Zero (BLACK BOX) | `backend/gpubroker/TMP/agent-zero/` | Reference only - DO NOT MODIFY |
| GPUBROKER POD SaaS Spec | `.kiro/specs/gpubroker-pod-saas/` | Parent platform spec |
| GPUBROKER SRS | `docs/SRS.md` | Main platform SRS |
