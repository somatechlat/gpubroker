# GPUBROKER Agentic OS Platform - Architecture Report

## Executive Summary

This document outlines the comprehensive architecture for integrating Agent Zero as an **Agentic OS Platform** within GPUBROKER. Agent Zero is treated as a **BLACK BOX** - we do NOT modify its code. Instead, we build a sophisticated GPUBROKER Django orchestration layer that communicates with Agent Zero's APIs to enable multi-agent spawning, coordination, and autonomous GPU/service procurement.

---

## Agent Zero Capabilities Analysis (BLACK BOX)

### Core Multi-Agent Architecture

Based on reverse engineering Agent Zero's codebase (READ-ONLY), here's what it provides:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AGENT ZERO INTERNAL ARCHITECTURE                      │
│                              (BLACK BOX - DO NOT TOUCH)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         AGENT HIERARCHY                              │    │
│  │                                                                      │    │
│  │    ┌─────────┐                                                       │    │
│  │    │ Agent 0 │ ◄── Superior (User/Admin)                            │    │
│  │    │ (A0)    │                                                       │    │
│  │    └────┬────┘                                                       │    │
│  │         │ call_subordinate(profile="developer", message="...")       │    │
│  │         ▼                                                            │    │
│  │    ┌─────────┐                                                       │    │
│  │    │ Agent 1 │ ◄── Subordinate (Developer Profile)                  │    │
│  │    │ (A1)    │                                                       │    │
│  │    └────┬────┘                                                       │    │
│  │         │ call_subordinate(profile="researcher", message="...")      │    │
│  │         ▼                                                            │    │
│  │    ┌─────────┐                                                       │    │
│  │    │ Agent 2 │ ◄── Sub-subordinate (Researcher Profile)             │    │
│  │    │ (A2)    │                                                       │    │
│  │    └─────────┘                                                       │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      AVAILABLE AGENT PROFILES                        │    │
│  │                                                                      │    │
│  │  • default    - General purpose agent                               │    │
│  │  • developer  - Code-focused agent                                  │    │
│  │  • researcher - Research and analysis agent                         │    │
│  │  • hacker     - Security/penetration testing agent                  │    │
│  │  • agent0     - Base configuration                                  │    │
│  │  • _example   - Template for custom profiles                        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         BUILT-IN TOOLS                               │    │
│  │                                                                      │    │
│  │  • call_subordinate  - Spawn/delegate to sub-agents                 │    │
│  │  • code_execution    - Execute Python/Node.js/Shell                 │    │
│  │  • memory_tool       - Save/load/delete memories                    │    │
│  │  • response_tool     - Output final response                        │    │
│  │  • behavior_adjust   - Modify agent behavior dynamically            │    │
│  │  • browser           - Web browsing capabilities                    │    │
│  │  • search_engine     - SearXNG integration                          │    │
│  │  • document_query    - RAG knowledge base queries                   │    │
│  │  • scheduler         - Task scheduling                              │    │
│  │  • a2a_chat          - Agent-to-Agent communication                 │    │
│  │  • notify_user       - Send notifications                           │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         API ENDPOINTS                                │    │
│  │                                                                      │    │
│  │  REST API:                                                          │    │
│  │  • POST /message         - Send message to agent                    │    │
│  │  • POST /message_async   - Async message (non-blocking)             │    │
│  │  • GET  /health          - Health check                             │    │
│  │  • POST /chat_create     - Create new chat context                  │    │
│  │  • POST /chat_reset      - Reset chat context                       │    │
│  │  • POST /chat_load       - Load existing chat                       │    │
│  │  • GET  /poll            - Poll for updates                         │    │
│  │  • POST /pause           - Pause agent execution                    │    │
│  │  • POST /nudge           - Resume agent execution                   │    │
│  │  • GET  /history_get     - Get conversation history                 │    │
│  │  • GET  /ctx_window_get  - Get context window info                  │    │
│  │                                                                      │    │
│  │  MCP Server: /mcp/*      - Model Context Protocol                   │    │
│  │  A2A Server: /a2a/*      - Agent-to-Agent Protocol                  │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Agent Zero Features We Leverage

| Feature | Description | How We Use It |
|---------|-------------|---------------|
| **Multi-Agent Spawning** | `call_subordinate` tool creates child agents | Orchestrate specialized agents for GPU tasks |
| **Agent Profiles** | Pre-configured agent personalities | Create GPU-specific profiles (provisioner, optimizer, monitor) |
| **Memory System** | Persistent memory across sessions | Store GPU pricing, provider preferences, past decisions |
| **MCP Protocol** | Model Context Protocol server | Integrate with external tools and services |
| **A2A Protocol** | Agent-to-Agent communication | Enable agent collaboration |
| **Code Execution** | Run Python/Shell in Docker | Execute provider API calls, infrastructure scripts |
| **Knowledge Base** | RAG-augmented queries | Store GPU documentation, provider specs |
| **Scheduler** | Task scheduling | Schedule price checks, auto-scaling decisions |

---

## GPUBROKER Agentic OS Platform Architecture


### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           GPUBROKER AGENTIC OS PLATFORM                                  │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                        GPUBROKER DJANGO ORCHESTRATION LAYER                        │  │
│  │                                                                                    │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │  │
│  │  │  Agent Fleet    │  │  Task           │  │  Decision       │  │  Budget      │  │  │
│  │  │  Manager        │  │  Orchestrator   │  │  Tracker        │  │  Controller  │  │  │
│  │  │                 │  │                 │  │                 │  │              │  │  │
│  │  │ • Spawn agents  │  │ • Queue tasks   │  │ • Log decisions │  │ • Track cost │  │  │
│  │  │ • Track status  │  │ • Route to      │  │ • Audit trail   │  │ • Enforce    │  │  │
│  │  │ • Load balance  │  │   agents        │  │ • Approval flow │  │   limits     │  │  │
│  │  │ • Health check  │  │ • Priority      │  │ • Rollback      │  │ • Alerts     │  │  │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘  │  │
│  │           │                    │                    │                   │          │  │
│  │           └────────────────────┼────────────────────┼───────────────────┘          │  │
│  │                                │                    │                              │  │
│  │                         ┌──────▼──────────────────────────┐                        │  │
│  │                         │      AGENT ZERO CLIENT          │                        │  │
│  │                         │                                 │                        │  │
│  │                         │  • HTTP Client (REST API)       │                        │  │
│  │                         │  • WebSocket Client (Streaming) │                        │  │
│  │                         │  • MCP Client (Tools)           │                        │  │
│  │                         │  • A2A Client (Agent Comms)     │                        │  │
│  │                         └──────────────┬──────────────────┘                        │  │
│  │                                        │                                           │  │
│  └────────────────────────────────────────┼───────────────────────────────────────────┘  │
│                                           │                                              │
│                                           │ HTTP/WebSocket/MCP/A2A                       │
│                                           │                                              │
│  ┌────────────────────────────────────────▼───────────────────────────────────────────┐  │
│  │                         AGENT ZERO RUNTIME (BLACK BOX)                              │  │
│  │                                                                                     │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                        MULTI-AGENT HIERARCHY                                 │   │  │
│  │  │                                                                              │   │  │
│  │  │   ┌──────────────────────────────────────────────────────────────────────┐  │   │  │
│  │  │   │                    AGENT 0 (ORCHESTRATOR)                             │  │   │  │
│  │  │   │                    Profile: gpubroker-orchestrator                    │  │   │  │
│  │  │   │                                                                       │  │   │  │
│  │  │   │  Responsibilities:                                                    │  │   │  │
│  │  │   │  • Receive tasks from GPUBROKER                                       │  │   │  │
│  │  │   │  • Analyze requirements                                               │  │   │  │
│  │  │   │  • Spawn specialized sub-agents                                       │  │   │  │
│  │  │   │  • Coordinate multi-agent workflows                                   │  │   │  │
│  │  │   │  • Report results back to GPUBROKER                                   │  │   │  │
│  │  │   └───────────────────────────┬───────────────────────────────────────────┘  │   │  │
│  │  │                               │                                              │   │  │
│  │  │         ┌─────────────────────┼─────────────────────┐                        │   │  │
│  │  │         │                     │                     │                        │   │  │
│  │  │         ▼                     ▼                     ▼                        │   │  │
│  │  │   ┌───────────┐         ┌───────────┐         ┌───────────┐                  │   │  │
│  │  │   │  AGENT 1  │         │  AGENT 2  │         │  AGENT 3  │                  │   │  │
│  │  │   │ Provisioner│        │ Optimizer │         │  Monitor  │                  │   │  │
│  │  │   │           │         │           │         │           │                  │   │  │
│  │  │   │ • Find GPU│         │ • Compare │         │ • Watch   │                  │   │  │
│  │  │   │ • Deploy  │         │   prices  │         │   health  │                  │   │  │
│  │  │   │ • Config  │         │ • Optimize│         │ • Alert   │                  │   │  │
│  │  │   │           │         │   costs   │         │ • Scale   │                  │   │  │
│  │  │   └─────┬─────┘         └─────┬─────┘         └─────┬─────┘                  │   │  │
│  │  │         │                     │                     │                        │   │  │
│  │  │         ▼                     ▼                     ▼                        │   │  │
│  │  │   ┌───────────┐         ┌───────────┐         ┌───────────┐                  │   │  │
│  │  │   │  AGENT 4  │         │  AGENT 5  │         │  AGENT 6  │                  │   │  │
│  │  │   │ Provider  │         │ Researcher│         │ Scheduler │                  │   │  │
│  │  │   │ Specialist│         │           │         │           │                  │   │  │
│  │  │   │           │         │ • Market  │         │ • Cron    │                  │   │  │
│  │  │   │ • RunPod  │         │   analysis│         │   tasks   │                  │   │  │
│  │  │   │ • Lambda  │         │ • Trends  │         │ • Auto    │                  │   │  │
│  │  │   │ • Vast.ai │         │ • Reports │         │   scale   │                  │   │  │
│  │  │   └───────────┘         └───────────┘         └───────────┘                  │   │  │
│  │  │                                                                              │   │  │
│  │  └──────────────────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                                     │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                           SHARED RESOURCES                                   │   │  │
│  │  │                                                                              │   │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │   │  │
│  │  │  │   Memory    │  │  Knowledge  │  │ Instruments │  │    MCP Tools        │ │   │  │
│  │  │  │   System    │  │    Base     │  │             │  │                     │ │   │  │
│  │  │  │             │  │             │  │ • GPU APIs  │  │ • Provider APIs     │ │   │  │
│  │  │  │ • Pricing   │  │ • GPU Docs  │  │ • Deploy    │  │ • Billing APIs      │ │   │  │
│  │  │  │   history   │  │ • Provider  │  │   scripts   │  │ • Monitoring APIs   │ │   │  │
│  │  │  │ • Decisions │  │   specs     │  │ • Health    │  │ • Notification APIs │ │   │  │
│  │  │  │ • Prefs     │  │ • Best      │  │   checks    │  │                     │ │   │  │
│  │  │  │             │  │   practices │  │             │  │                     │ │   │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │   │  │
│  │  │                                                                              │   │  │
│  │  └──────────────────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Agent Fleet Manager

The Agent Fleet Manager is responsible for managing multiple Agent Zero instances and their spawned sub-agents.

```python
# gpubrokeragent/services/fleet_manager.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime
import uuid

class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"      # Main coordinator (Agent 0)
    PROVISIONER = "provisioner"        # GPU deployment specialist
    OPTIMIZER = "optimizer"            # Cost optimization specialist
    MONITOR = "monitor"                # Health monitoring specialist
    RESEARCHER = "researcher"          # Market research specialist
    SCHEDULER = "scheduler"            # Task scheduling specialist
    PROVIDER_SPECIALIST = "provider"   # Provider-specific specialist

@dataclass
class AgentInstance:
    """Represents a single agent instance in the fleet."""
    id: str
    context_id: str                    # Agent Zero context ID
    role: AgentRole
    profile: str                       # Agent Zero profile name
    parent_id: Optional[str] = None    # Parent agent ID (for hierarchy)
    children_ids: List[str] = field(default_factory=list)
    status: str = "idle"               # idle, busy, error, terminated
    current_task: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    estimated_cost: float = 0.0

@dataclass
class AgentFleet:
    """Manages a fleet of agents for a POD."""
    pod_id: str
    orchestrator: Optional[AgentInstance] = None
    agents: Dict[str, AgentInstance] = field(default_factory=dict)
    max_agents: int = 10
    total_cost: float = 0.0

class AgentFleetManager:
    """
    Manages multiple Agent Zero instances for GPUBROKER.
    
    This is the GPUBROKER layer - we communicate WITH Agent Zero,
    we do NOT modify Agent Zero code.
    """
    
    def __init__(self, agent_client: "AgentZeroClient"):
        self.client = agent_client
        self.fleets: Dict[str, AgentFleet] = {}
    
    async def create_fleet(self, pod_id: str, budget_limit: float) -> AgentFleet:
        """Create a new agent fleet for a POD."""
        fleet = AgentFleet(pod_id=pod_id)
        
        # Create orchestrator agent (Agent 0)
        orchestrator = await self._spawn_agent(
            fleet=fleet,
            role=AgentRole.ORCHESTRATOR,
            profile="gpubroker-orchestrator"
        )
        fleet.orchestrator = orchestrator
        fleet.agents[orchestrator.id] = orchestrator
        
        self.fleets[pod_id] = fleet
        return fleet
    
    async def spawn_specialist(
        self, 
        pod_id: str, 
        role: AgentRole,
        parent_id: Optional[str] = None,
        task_context: Optional[str] = None
    ) -> AgentInstance:
        """
        Spawn a specialist agent via Agent Zero's call_subordinate.
        
        This sends a message to Agent Zero asking it to spawn a sub-agent.
        We track the spawned agent in our fleet manager.
        """
        fleet = self.fleets.get(pod_id)
        if not fleet:
            raise ValueError(f"Fleet not found for POD {pod_id}")
        
        if len(fleet.agents) >= fleet.max_agents:
            raise ValueError(f"Max agents ({fleet.max_agents}) reached for POD {pod_id}")
        
        # Map role to Agent Zero profile
        profile_map = {
            AgentRole.PROVISIONER: "gpubroker-provisioner",
            AgentRole.OPTIMIZER: "gpubroker-optimizer",
            AgentRole.MONITOR: "gpubroker-monitor",
            AgentRole.RESEARCHER: "researcher",
            AgentRole.SCHEDULER: "gpubroker-scheduler",
            AgentRole.PROVIDER_SPECIALIST: "gpubroker-provider",
        }
        
        profile = profile_map.get(role, "default")
        
        # Send message to orchestrator to spawn sub-agent
        parent = fleet.agents.get(parent_id) if parent_id else fleet.orchestrator
        if not parent:
            parent = fleet.orchestrator
        
        # This calls Agent Zero's API to spawn a subordinate
        spawn_message = f"""
        Spawn a new subordinate agent with the following configuration:
        - Profile: {profile}
        - Role: {role.value}
        - Task Context: {task_context or 'General assistance'}
        
        Use the call_subordinate tool with reset="true" to create a new agent.
        """
        
        response = await self.client.send_message(
            message=spawn_message,
            context_id=parent.context_id
        )
        
        # Track the new agent in our fleet
        agent = AgentInstance(
            id=str(uuid.uuid4()),
            context_id=response.get("context", parent.context_id),
            role=role,
            profile=profile,
            parent_id=parent.id
        )
        
        fleet.agents[agent.id] = agent
        parent.children_ids.append(agent.id)
        
        return agent
    
    async def delegate_task(
        self,
        pod_id: str,
        task: str,
        target_role: Optional[AgentRole] = None,
        agent_id: Optional[str] = None
    ) -> dict:
        """
        Delegate a task to an agent in the fleet.
        
        If no specific agent is specified, the orchestrator will
        decide which agent (or new sub-agent) should handle it.
        """
        fleet = self.fleets.get(pod_id)
        if not fleet:
            raise ValueError(f"Fleet not found for POD {pod_id}")
        
        # Find target agent
        if agent_id:
            agent = fleet.agents.get(agent_id)
        elif target_role:
            # Find agent with matching role
            agent = next(
                (a for a in fleet.agents.values() if a.role == target_role and a.status == "idle"),
                None
            )
            if not agent:
                # Spawn new specialist
                agent = await self.spawn_specialist(pod_id, target_role, task_context=task)
        else:
            # Default to orchestrator
            agent = fleet.orchestrator
        
        if not agent:
            raise ValueError("No suitable agent found")
        
        # Update agent status
        agent.status = "busy"
        agent.current_task = task
        agent.last_activity = datetime.utcnow()
        
        # Send task to Agent Zero
        response = await self.client.send_message(
            message=task,
            context_id=agent.context_id
        )
        
        # Update agent status
        agent.status = "idle"
        agent.current_task = None
        agent.message_count += 1
        
        return {
            "agent_id": agent.id,
            "role": agent.role.value,
            "response": response
        }
    
    async def get_fleet_status(self, pod_id: str) -> dict:
        """Get status of all agents in a fleet."""
        fleet = self.fleets.get(pod_id)
        if not fleet:
            return {"error": "Fleet not found"}
        
        return {
            "pod_id": pod_id,
            "total_agents": len(fleet.agents),
            "max_agents": fleet.max_agents,
            "total_cost": fleet.total_cost,
            "agents": [
                {
                    "id": a.id,
                    "role": a.role.value,
                    "status": a.status,
                    "current_task": a.current_task,
                    "message_count": a.message_count,
                    "children_count": len(a.children_ids)
                }
                for a in fleet.agents.values()
            ]
        }
```



### 2. Task Orchestrator

The Task Orchestrator manages the queue of tasks and routes them to appropriate agents.

```python
# gpubrokeragent/services/task_orchestrator.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Awaitable
from enum import Enum
from datetime import datetime
import uuid
import asyncio
from collections import deque

class TaskPriority(Enum):
    CRITICAL = 1    # Immediate execution (e.g., emergency scale-down)
    HIGH = 2        # High priority (e.g., user-initiated deployment)
    NORMAL = 3      # Normal priority (e.g., scheduled optimization)
    LOW = 4         # Low priority (e.g., background research)

class TaskType(Enum):
    # GPU Provisioning
    FIND_GPU = "find_gpu"
    DEPLOY_GPU = "deploy_gpu"
    TERMINATE_GPU = "terminate_gpu"
    SCALE_GPU = "scale_gpu"
    
    # Optimization
    OPTIMIZE_COST = "optimize_cost"
    COMPARE_PROVIDERS = "compare_providers"
    ANALYZE_USAGE = "analyze_usage"
    
    # Monitoring
    HEALTH_CHECK = "health_check"
    ALERT_RESPONSE = "alert_response"
    
    # Research
    MARKET_RESEARCH = "market_research"
    PRICE_ANALYSIS = "price_analysis"
    
    # Scheduling
    SCHEDULED_TASK = "scheduled_task"
    AUTO_SCALE = "auto_scale"

@dataclass
class AgentTask:
    """Represents a task to be executed by an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: TaskType = TaskType.FIND_GPU
    priority: TaskPriority = TaskPriority.NORMAL
    pod_id: str = ""
    user_id: str = ""
    
    # Task details
    description: str = ""
    parameters: Dict = field(default_factory=dict)
    
    # Execution state
    status: str = "pending"  # pending, queued, running, completed, failed
    assigned_agent_id: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Cost tracking
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    
    # Approval (for high-impact tasks)
    requires_approval: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

class TaskOrchestrator:
    """
    Orchestrates task execution across the agent fleet.
    
    Routes tasks to appropriate agents based on type, priority,
    and agent availability.
    """
    
    def __init__(self, fleet_manager: "AgentFleetManager"):
        self.fleet_manager = fleet_manager
        self.task_queues: Dict[str, deque] = {}  # pod_id -> queue
        self.active_tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: Dict[str, List[AgentTask]] = {}
        self._running = False
    
    # Task type to agent role mapping
    TASK_ROLE_MAP = {
        TaskType.FIND_GPU: AgentRole.PROVISIONER,
        TaskType.DEPLOY_GPU: AgentRole.PROVISIONER,
        TaskType.TERMINATE_GPU: AgentRole.PROVISIONER,
        TaskType.SCALE_GPU: AgentRole.PROVISIONER,
        TaskType.OPTIMIZE_COST: AgentRole.OPTIMIZER,
        TaskType.COMPARE_PROVIDERS: AgentRole.OPTIMIZER,
        TaskType.ANALYZE_USAGE: AgentRole.OPTIMIZER,
        TaskType.HEALTH_CHECK: AgentRole.MONITOR,
        TaskType.ALERT_RESPONSE: AgentRole.MONITOR,
        TaskType.MARKET_RESEARCH: AgentRole.RESEARCHER,
        TaskType.PRICE_ANALYSIS: AgentRole.RESEARCHER,
        TaskType.SCHEDULED_TASK: AgentRole.SCHEDULER,
        TaskType.AUTO_SCALE: AgentRole.SCHEDULER,
    }
    
    # Tasks that require admin approval before execution
    APPROVAL_REQUIRED_TASKS = {
        TaskType.DEPLOY_GPU,
        TaskType.TERMINATE_GPU,
        TaskType.SCALE_GPU,
        TaskType.AUTO_SCALE,
    }
    
    async def submit_task(self, task: AgentTask) -> str:
        """Submit a task for execution."""
        # Check if approval is required
        if task.type in self.APPROVAL_REQUIRED_TASKS:
            task.requires_approval = True
            task.status = "pending_approval"
        else:
            task.status = "queued"
        
        # Add to queue
        if task.pod_id not in self.task_queues:
            self.task_queues[task.pod_id] = deque()
        
        # Insert based on priority
        queue = self.task_queues[task.pod_id]
        inserted = False
        for i, existing in enumerate(queue):
            if task.priority.value < existing.priority.value:
                queue.insert(i, task)
                inserted = True
                break
        if not inserted:
            queue.append(task)
        
        return task.id
    
    async def approve_task(self, task_id: str, approver_id: str) -> bool:
        """Approve a task that requires approval."""
        for queue in self.task_queues.values():
            for task in queue:
                if task.id == task_id:
                    task.approved_by = approver_id
                    task.approved_at = datetime.utcnow()
                    task.status = "queued"
                    return True
        return False
    
    async def reject_task(self, task_id: str, reason: str) -> bool:
        """Reject a task that requires approval."""
        for pod_id, queue in self.task_queues.items():
            for task in list(queue):
                if task.id == task_id:
                    task.status = "rejected"
                    task.error = reason
                    queue.remove(task)
                    if pod_id not in self.completed_tasks:
                        self.completed_tasks[pod_id] = []
                    self.completed_tasks[pod_id].append(task)
                    return True
        return False
    
    async def process_queue(self, pod_id: str):
        """Process tasks in the queue for a POD."""
        if pod_id not in self.task_queues:
            return
        
        queue = self.task_queues[pod_id]
        
        while queue:
            task = queue[0]
            
            # Skip tasks pending approval
            if task.status == "pending_approval":
                queue.rotate(-1)  # Move to end
                continue
            
            # Get appropriate agent role
            target_role = self.TASK_ROLE_MAP.get(task.type, AgentRole.ORCHESTRATOR)
            
            try:
                # Execute task
                task.status = "running"
                task.started_at = datetime.utcnow()
                self.active_tasks[task.id] = task
                
                # Build task message for agent
                task_message = self._build_task_message(task)
                
                # Delegate to fleet
                result = await self.fleet_manager.delegate_task(
                    pod_id=pod_id,
                    task=task_message,
                    target_role=target_role
                )
                
                task.result = result
                task.status = "completed"
                task.assigned_agent_id = result.get("agent_id")
                
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
            
            finally:
                task.completed_at = datetime.utcnow()
                queue.popleft()
                del self.active_tasks[task.id]
                
                if pod_id not in self.completed_tasks:
                    self.completed_tasks[pod_id] = []
                self.completed_tasks[pod_id].append(task)
    
    def _build_task_message(self, task: AgentTask) -> str:
        """Build a message for the agent based on task type."""
        messages = {
            TaskType.FIND_GPU: f"""
                Find the best GPU option for the following requirements:
                {task.parameters}
                
                Consider: price, availability, performance, and provider reliability.
                Use the TOPSIS ranking method to compare options.
                Return the top 3 recommendations with reasoning.
            """,
            TaskType.DEPLOY_GPU: f"""
                Deploy a GPU instance with the following configuration:
                {task.parameters}
                
                Steps:
                1. Verify the configuration is valid
                2. Check budget availability
                3. Call the provider API to provision
                4. Wait for instance to be ready
                5. Return connection details
            """,
            TaskType.OPTIMIZE_COST: f"""
                Analyze current GPU usage and find cost optimization opportunities:
                {task.parameters}
                
                Consider:
                - Underutilized instances
                - Cheaper alternatives
                - Spot/preemptible options
                - Reserved instance opportunities
            """,
            TaskType.HEALTH_CHECK: f"""
                Perform health check on GPU instances:
                {task.parameters}
                
                Check:
                - Instance status
                - GPU utilization
                - Memory usage
                - Network connectivity
                - Provider API status
            """,
        }
        
        return messages.get(task.type, f"Execute task: {task.description}\nParameters: {task.parameters}")
```



### 3. Agent Zero Client (Communication Layer)

The Agent Zero Client handles all communication with the Agent Zero BLACK BOX.

```python
# gpubrokeragent/services/agent_client.py

import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger('gpubroker.agent_client')

@dataclass
class AgentZeroConfig:
    """Configuration for Agent Zero connection."""
    base_url: str = "http://localhost:50001"
    api_key: str = ""
    timeout: int = 300  # 5 minutes default
    max_retries: int = 3
    retry_delay: float = 1.0
    websocket_url: Optional[str] = None
    
    def __post_init__(self):
        if not self.websocket_url:
            self.websocket_url = self.base_url.replace("http", "ws")

class AgentZeroClient:
    """
    Client to communicate with Agent Zero BLACK BOX.
    
    We do NOT modify Agent Zero - we only call its APIs.
    This client handles:
    - REST API calls (message, health, chat management)
    - WebSocket streaming (real-time responses)
    - MCP protocol (tool integration)
    - A2A protocol (agent-to-agent communication)
    """
    
    def __init__(self, config: AgentZeroConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws_connections: Dict[str, aiohttp.ClientWebSocketResponse] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            headers = {}
            if self.config.api_key:
                headers["X-API-KEY"] = self.config.api_key
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
        return self._session
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        session = await self._get_session()
        url = f"{self.config.base_url}/{endpoint}"
        
        try:
            async with session.request(method, url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    raise PermissionError("Invalid API key")
                elif response.status == 429:
                    # Rate limited - retry with backoff
                    if retry_count < self.config.max_retries:
                        await asyncio.sleep(self.config.retry_delay * (2 ** retry_count))
                        return await self._request(method, endpoint, data, retry_count + 1)
                    raise Exception("Rate limit exceeded")
                else:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
        
        except aiohttp.ClientError as e:
            if retry_count < self.config.max_retries:
                await asyncio.sleep(self.config.retry_delay * (2 ** retry_count))
                return await self._request(method, endpoint, data, retry_count + 1)
            raise
    
    # ==================== REST API Methods ====================
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Agent Zero health status."""
        return await self._request("GET", "health")
    
    async def send_message(
        self, 
        message: str, 
        context_id: Optional[str] = None,
        attachments: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Send a message to Agent Zero.
        
        This is the primary way to interact with agents.
        Agent Zero will process the message and may spawn sub-agents.
        """
        data = {
            "text": message,
            "context": context_id or "",
        }
        if attachments:
            data["attachments"] = attachments
        
        return await self._request("POST", "message", data)
    
    async def send_message_async(
        self, 
        message: str, 
        context_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message asynchronously (non-blocking)."""
        data = {
            "text": message,
            "context": context_id or "",
        }
        return await self._request("POST", "message_async", data)
    
    async def create_chat(
        self, 
        current_context: Optional[str] = None,
        new_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new chat context."""
        data = {}
        if current_context:
            data["current_context"] = current_context
        if new_context:
            data["new_context"] = new_context
        return await self._request("POST", "chat_create", data)
    
    async def reset_chat(self, context_id: str) -> Dict[str, Any]:
        """Reset a chat context."""
        return await self._request("POST", "chat_reset", {"context": context_id})
    
    async def load_chat(self, context_id: str) -> Dict[str, Any]:
        """Load an existing chat context."""
        return await self._request("POST", "chat_load", {"context": context_id})
    
    async def get_history(self, context_id: str) -> Dict[str, Any]:
        """Get conversation history for a context."""
        return await self._request("GET", f"history_get?context={context_id}")
    
    async def pause_agent(self, context_id: str) -> Dict[str, Any]:
        """Pause agent execution."""
        return await self._request("POST", "pause", {"context": context_id})
    
    async def nudge_agent(self, context_id: str) -> Dict[str, Any]:
        """Resume/nudge agent execution."""
        return await self._request("POST", "nudge", {"context": context_id})
    
    async def poll_updates(self, context_id: str, log_version: int = 0) -> Dict[str, Any]:
        """Poll for updates from agent."""
        return await self._request("GET", f"poll?context={context_id}&log_from={log_version}")
    
    async def get_context_window(self, context_id: str) -> Dict[str, Any]:
        """Get context window information."""
        return await self._request("GET", f"ctx_window_get?context={context_id}")
    
    # ==================== WebSocket Streaming ====================
    
    async def connect_websocket(
        self, 
        context_id: str,
        on_message: Callable[[str], Awaitable[None]],
        on_error: Optional[Callable[[Exception], Awaitable[None]]] = None
    ):
        """
        Connect to Agent Zero WebSocket for streaming responses.
        
        This allows real-time streaming of agent responses token-by-token.
        """
        session = await self._get_session()
        ws_url = f"{self.config.websocket_url}/ws/{context_id}"
        
        try:
            async with session.ws_connect(ws_url) as ws:
                self._ws_connections[context_id] = ws
                
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await on_message(msg.data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        if on_error:
                            await on_error(Exception(f"WebSocket error: {ws.exception()}"))
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        break
        
        except Exception as e:
            if on_error:
                await on_error(e)
            raise
        
        finally:
            self._ws_connections.pop(context_id, None)
    
    async def send_websocket_message(self, context_id: str, message: str):
        """Send message via WebSocket."""
        ws = self._ws_connections.get(context_id)
        if ws:
            await ws.send_str(json.dumps({"text": message}))
    
    async def close_websocket(self, context_id: str):
        """Close WebSocket connection."""
        ws = self._ws_connections.pop(context_id, None)
        if ws:
            await ws.close()
    
    # ==================== MCP Protocol ====================
    
    async def mcp_list_tools(self) -> Dict[str, Any]:
        """List available MCP tools."""
        return await self._request("GET", "mcp_servers_status")
    
    async def mcp_call_tool(
        self, 
        server_name: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an MCP tool."""
        # MCP calls go through the agent message system
        message = f"""
        Use the MCP tool:
        Server: {server_name}
        Tool: {tool_name}
        Arguments: {json.dumps(arguments)}
        """
        return await self.send_message(message)
    
    # ==================== Cleanup ====================
    
    async def close(self):
        """Close all connections."""
        # Close WebSocket connections
        for context_id in list(self._ws_connections.keys()):
            await self.close_websocket(context_id)
        
        # Close HTTP session
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
```



---

## Multi-Agent Workflow Examples

### Workflow 1: Autonomous GPU Procurement

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS GPU PROCUREMENT WORKFLOW                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Request: "Find me the cheapest A100 GPU for ML training"              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 1: GPUBROKER receives request                                   │    │
│  │                                                                      │    │
│  │  TaskOrchestrator.submit_task(                                       │    │
│  │      type=TaskType.FIND_GPU,                                         │    │
│  │      parameters={"gpu_type": "A100", "optimize": "cost"}             │    │
│  │  )                                                                   │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 2: Task routed to Orchestrator Agent (A0)                       │    │
│  │                                                                      │    │
│  │  AgentZeroClient.send_message(                                       │    │
│  │      message="Find cheapest A100 GPU...",                            │    │
│  │      context_id=orchestrator.context_id                              │    │
│  │  )                                                                   │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 3: Orchestrator spawns specialist agents                        │    │
│  │                                                                      │    │
│  │  Agent 0 (Orchestrator) thinks:                                      │    │
│  │  "I need to query multiple providers. Let me spawn specialists."     │    │
│  │                                                                      │    │
│  │  Uses call_subordinate tool:                                         │    │
│  │  {                                                                   │    │
│  │      "tool_name": "call_subordinate",                                │    │
│  │      "tool_args": {                                                  │    │
│  │          "profile": "gpubroker-provider",                            │    │
│  │          "message": "Query RunPod for A100 availability and pricing",│    │
│  │          "reset": "true"                                             │    │
│  │      }                                                               │    │
│  │  }                                                                   │    │
│  │                                                                      │    │
│  │  Spawns 3 provider specialists in parallel:                          │    │
│  │  • Agent 1: RunPod specialist                                        │    │
│  │  • Agent 2: Lambda Labs specialist                                   │    │
│  │  • Agent 3: Vast.ai specialist                                       │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│         ┌───────────────────────┼───────────────────────┐                    │
│         │                       │                       │                    │
│         ▼                       ▼                       ▼                    │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐            │
│  │   Agent 1   │         │   Agent 2   │         │   Agent 3   │            │
│  │   RunPod    │         │ Lambda Labs │         │   Vast.ai   │            │
│  │             │         │             │         │             │            │
│  │ Executes:   │         │ Executes:   │         │ Executes:   │            │
│  │ code_exec   │         │ code_exec   │         │ code_exec   │            │
│  │ tool to     │         │ tool to     │         │ tool to     │            │
│  │ call API    │         │ call API    │         │ call API    │            │
│  │             │         │             │         │             │            │
│  │ Returns:    │         │ Returns:    │         │ Returns:    │            │
│  │ $2.50/hr    │         │ $2.79/hr    │         │ $1.89/hr    │            │
│  │ 5 available │         │ 3 available │         │ 8 available │            │
│  └──────┬──────┘         └──────┬──────┘         └──────┬──────┘            │
│         │                       │                       │                    │
│         └───────────────────────┼───────────────────────┘                    │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 4: Orchestrator aggregates and ranks results                    │    │
│  │                                                                      │    │
│  │  Agent 0 receives results from all subordinates                      │    │
│  │                                                                      │    │
│  │  Spawns Optimizer agent:                                             │    │
│  │  {                                                                   │    │
│  │      "tool_name": "call_subordinate",                                │    │
│  │      "tool_args": {                                                  │    │
│  │          "profile": "gpubroker-optimizer",                           │    │
│  │          "message": "Rank these options using TOPSIS: [results]",    │    │
│  │          "reset": "true"                                             │    │
│  │      }                                                               │    │
│  │  }                                                                   │    │
│  │                                                                      │    │
│  │  Optimizer returns ranked list:                                      │    │
│  │  1. Vast.ai - $1.89/hr (Best value)                                  │    │
│  │  2. RunPod - $2.50/hr (Good reliability)                             │    │
│  │  3. Lambda Labs - $2.79/hr (Premium support)                         │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 5: Result returned to GPUBROKER                                 │    │
│  │                                                                      │    │
│  │  GPUBROKER receives structured response:                             │    │
│  │  {                                                                   │    │
│  │      "recommendations": [                                            │    │
│  │          {                                                           │    │
│  │              "provider": "vast.ai",                                  │    │
│  │              "gpu": "A100",                                          │    │
│  │              "price_per_hour": 1.89,                                 │    │
│  │              "availability": 8,                                      │    │
│  │              "topsis_score": 0.92                                    │    │
│  │          },                                                          │    │
│  │          ...                                                         │    │
│  │      ],                                                              │    │
│  │      "agents_used": 5,                                               │    │
│  │      "execution_time": "12.3s"                                       │    │
│  │  }                                                                   │    │
│  │                                                                      │    │
│  │  DecisionTracker logs the decision for audit                         │    │
│  │  BudgetController tracks estimated cost                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Workflow 2: Autonomous Cost Optimization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS COST OPTIMIZATION WORKFLOW                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Trigger: Scheduled task (daily at 2 AM) or budget threshold alert          │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 1: Scheduler triggers optimization task                         │    │
│  │                                                                      │    │
│  │  TaskOrchestrator.submit_task(                                       │    │
│  │      type=TaskType.OPTIMIZE_COST,                                    │    │
│  │      priority=TaskPriority.NORMAL,                                   │    │
│  │      parameters={"scope": "all_active_instances"}                    │    │
│  │  )                                                                   │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 2: Orchestrator analyzes current state                          │    │
│  │                                                                      │    │
│  │  Agent 0 spawns Monitor agent to gather metrics:                     │    │
│  │  • Current GPU utilization                                           │    │
│  │  • Memory usage patterns                                             │    │
│  │  • Cost per instance                                                 │    │
│  │  • Uptime statistics                                                 │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 3: Optimizer agent identifies opportunities                     │    │
│  │                                                                      │    │
│  │  Findings:                                                           │    │
│  │  • Instance A: 15% utilization → Recommend downgrade                 │    │
│  │  • Instance B: Running 24/7 → Recommend spot instance                │    │
│  │  • Instance C: Peak hours only → Recommend auto-scaling              │    │
│  │                                                                      │    │
│  │  Potential savings: $450/month                                       │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 4: Generate optimization proposals                              │    │
│  │                                                                      │    │
│  │  Proposals require POD Admin approval:                               │    │
│  │                                                                      │    │
│  │  Proposal 1: Downgrade Instance A                                    │    │
│  │  - Current: A100 80GB @ $2.50/hr                                     │    │
│  │  - Proposed: A100 40GB @ $1.50/hr                                    │    │
│  │  - Savings: $720/month                                               │    │
│  │  - Risk: Low (utilization supports downgrade)                        │    │
│  │                                                                      │    │
│  │  Proposal 2: Switch Instance B to Spot                               │    │
│  │  - Current: On-demand @ $2.50/hr                                     │    │
│  │  - Proposed: Spot @ $0.75/hr                                         │    │
│  │  - Savings: $1,260/month                                             │    │
│  │  - Risk: Medium (may be interrupted)                                 │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 5: Await admin approval                                         │    │
│  │                                                                      │    │
│  │  GPUBROKER sends notification to POD Admin                           │    │
│  │  Admin reviews proposals in dashboard                                │    │
│  │  Admin approves Proposal 1, rejects Proposal 2                       │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ STEP 6: Execute approved optimizations                               │    │
│  │                                                                      │    │
│  │  Provisioner agent executes:                                         │    │
│  │  1. Create new A100 40GB instance                                    │    │
│  │  2. Migrate workload                                                 │    │
│  │  3. Verify functionality                                             │    │
│  │  4. Terminate old instance                                           │    │
│  │                                                                      │    │
│  │  All actions logged to audit trail                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Custom Agent Profiles for GPUBROKER

We will create custom Agent Zero profiles (stored in `agents/` directory) that are specialized for GPU operations. These profiles are loaded by Agent Zero - we don't modify Agent Zero code, we just provide configuration.

### Profile: gpubroker-orchestrator

```yaml
# agents/gpubroker-orchestrator/config.yaml
name: "GPUBROKER Orchestrator"
description: "Main coordinator for GPU procurement and management tasks"
system_prompt_additions:
  - "You are the GPUBROKER Orchestrator Agent."
  - "Your role is to coordinate GPU procurement, optimization, and monitoring tasks."
  - "You have access to specialized subordinate agents for specific tasks."
  - "Always consider cost, availability, and reliability when making decisions."
  - "Log all decisions for audit purposes."
  - "Respect budget limits set by the POD Admin."

tools_enabled:
  - call_subordinate
  - memory_tool
  - response_tool
  - scheduler
  - notify_user

subordinate_profiles:
  - gpubroker-provisioner
  - gpubroker-optimizer
  - gpubroker-monitor
  - gpubroker-provider
```

### Profile: gpubroker-provisioner

```yaml
# agents/gpubroker-provisioner/config.yaml
name: "GPUBROKER Provisioner"
description: "Specialist for GPU deployment and configuration"
system_prompt_additions:
  - "You are a GPU Provisioning Specialist."
  - "Your role is to deploy, configure, and terminate GPU instances."
  - "You have access to all GPU provider APIs via code execution."
  - "Always verify configurations before deployment."
  - "Report deployment status and connection details."

tools_enabled:
  - code_execution_tool
  - memory_tool
  - response_tool

instruments:
  - deploy_gpu
  - terminate_gpu
  - configure_gpu
  - get_connection_details
```

### Profile: gpubroker-optimizer

```yaml
# agents/gpubroker-optimizer/config.yaml
name: "GPUBROKER Optimizer"
description: "Specialist for cost optimization and resource efficiency"
system_prompt_additions:
  - "You are a Cost Optimization Specialist."
  - "Your role is to analyze GPU usage and find cost savings."
  - "Use TOPSIS ranking for comparing options."
  - "Consider spot instances, reserved capacity, and right-sizing."
  - "Generate actionable recommendations with risk assessments."

tools_enabled:
  - code_execution_tool
  - memory_tool
  - response_tool
  - search_engine

knowledge_base:
  - gpu_pricing_history
  - provider_comparison
  - optimization_strategies
```



---

## Django Models for Agentic OS Platform

```python
# gpubrokeragent/apps/agent_core/models.py

import uuid
from django.db import models
from django.contrib.auth import get_user_model

class AgentFleet(models.Model):
    """
    Represents a fleet of agents for a POD.
    Each POD has one fleet that manages multiple agents.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    pod = models.OneToOneField('pods.Pod', on_delete=models.CASCADE, related_name='agent_fleet')
    
    # Fleet configuration
    max_agents = models.IntegerField(default=10)
    budget_limit_usd = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    budget_used_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Status
    is_active = models.BooleanField(default=False)
    orchestrator_context_id = models.CharField(max_length=64, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'agent_fleets'


class AgentInstance(models.Model):
    """
    Represents a single agent instance in the fleet.
    Tracks agent state, role, and hierarchy.
    """
    class Role(models.TextChoices):
        ORCHESTRATOR = 'orchestrator', 'Orchestrator'
        PROVISIONER = 'provisioner', 'Provisioner'
        OPTIMIZER = 'optimizer', 'Optimizer'
        MONITOR = 'monitor', 'Monitor'
        RESEARCHER = 'researcher', 'Researcher'
        SCHEDULER = 'scheduler', 'Scheduler'
        PROVIDER = 'provider', 'Provider Specialist'
    
    class Status(models.TextChoices):
        IDLE = 'idle', 'Idle'
        BUSY = 'busy', 'Busy'
        ERROR = 'error', 'Error'
        TERMINATED = 'terminated', 'Terminated'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    fleet = models.ForeignKey(AgentFleet, on_delete=models.CASCADE, related_name='agents')
    
    # Agent Zero context
    context_id = models.CharField(max_length=64)
    profile = models.CharField(max_length=64)
    
    # Role and hierarchy
    role = models.CharField(max_length=20, choices=Role.choices)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IDLE)
    current_task_id = models.UUIDField(null=True, blank=True)
    
    # Metrics
    message_count = models.IntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    terminated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'agent_instances'


class AgentTask(models.Model):
    """
    Represents a task to be executed by an agent.
    Tracks task lifecycle from submission to completion.
    """
    class TaskType(models.TextChoices):
        FIND_GPU = 'find_gpu', 'Find GPU'
        DEPLOY_GPU = 'deploy_gpu', 'Deploy GPU'
        TERMINATE_GPU = 'terminate_gpu', 'Terminate GPU'
        SCALE_GPU = 'scale_gpu', 'Scale GPU'
        OPTIMIZE_COST = 'optimize_cost', 'Optimize Cost'
        COMPARE_PROVIDERS = 'compare_providers', 'Compare Providers'
        ANALYZE_USAGE = 'analyze_usage', 'Analyze Usage'
        HEALTH_CHECK = 'health_check', 'Health Check'
        ALERT_RESPONSE = 'alert_response', 'Alert Response'
        MARKET_RESEARCH = 'market_research', 'Market Research'
        PRICE_ANALYSIS = 'price_analysis', 'Price Analysis'
        SCHEDULED_TASK = 'scheduled_task', 'Scheduled Task'
        AUTO_SCALE = 'auto_scale', 'Auto Scale'
    
    class Priority(models.TextChoices):
        CRITICAL = 'critical', 'Critical'
        HIGH = 'high', 'High'
        NORMAL = 'normal', 'Normal'
        LOW = 'low', 'Low'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REJECTED = 'rejected', 'Rejected'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    fleet = models.ForeignKey(AgentFleet, on_delete=models.CASCADE, related_name='tasks')
    
    # Task details
    task_type = models.CharField(max_length=30, choices=TaskType.choices)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    description = models.TextField()
    parameters = models.JSONField(default=dict)
    
    # Execution
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    assigned_agent = models.ForeignKey(AgentInstance, on_delete=models.SET_NULL, null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    
    # Approval
    requires_approval = models.BooleanField(default=False)
    approved_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_tasks')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Cost tracking
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    actual_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Requester
    requested_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, related_name='requested_tasks')
    
    class Meta:
        db_table = 'agent_tasks'
        ordering = ['-created_at']


class AgentDecision(models.Model):
    """
    Records autonomous decisions made by agents.
    Provides audit trail for all agent actions.
    """
    class ActionType(models.TextChoices):
        PROVISION = 'provision', 'Provision Resource'
        TERMINATE = 'terminate', 'Terminate Resource'
        SCALE = 'scale', 'Scale Resource'
        OPTIMIZE = 'optimize', 'Optimize Configuration'
        ALERT = 'alert', 'Send Alert'
        RECOMMEND = 'recommend', 'Make Recommendation'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        EXECUTED = 'executed', 'Executed'
        REJECTED = 'rejected', 'Rejected'
        FAILED = 'failed', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    fleet = models.ForeignKey(AgentFleet, on_delete=models.CASCADE, related_name='decisions')
    task = models.ForeignKey(AgentTask, on_delete=models.SET_NULL, null=True, blank=True, related_name='decisions')
    agent = models.ForeignKey(AgentInstance, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Decision details
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    target_resource = models.CharField(max_length=255)
    provider = models.CharField(max_length=64, blank=True)
    reasoning = models.TextField()
    
    # Cost
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    actual_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    # Status and approval
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    admin_override = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    overridden_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'agent_decisions'
        ordering = ['-created_at']


class AgentMessage(models.Model):
    """
    Logs all messages sent to/from agents.
    Provides complete audit trail of agent communications.
    """
    class Direction(models.TextChoices):
        INBOUND = 'inbound', 'To Agent'
        OUTBOUND = 'outbound', 'From Agent'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    agent = models.ForeignKey(AgentInstance, on_delete=models.CASCADE, related_name='messages')
    task = models.ForeignKey(AgentTask, on_delete=models.SET_NULL, null=True, blank=True)
    
    direction = models.CharField(max_length=10, choices=Direction.choices)
    content = models.TextField()
    
    # Token tracking for cost estimation
    token_count = models.IntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'agent_messages'
        ordering = ['-created_at']
```

---

## API Endpoints for Agentic OS Platform

```python
# gpubrokeragent/api/fleet.py

from ninja import Router, Schema
from typing import List, Optional
from uuid import UUID
from datetime import datetime

router = Router(tags=["Agent Fleet"])

# ==================== Schemas ====================

class FleetStatusSchema(Schema):
    id: UUID
    pod_id: str
    is_active: bool
    max_agents: int
    current_agents: int
    budget_limit_usd: float
    budget_used_usd: float
    orchestrator_status: Optional[str]

class AgentSchema(Schema):
    id: UUID
    context_id: str
    role: str
    profile: str
    status: str
    parent_id: Optional[UUID]
    children_count: int
    message_count: int
    estimated_cost_usd: float
    last_activity_at: datetime

class TaskSchema(Schema):
    id: UUID
    task_type: str
    priority: str
    status: str
    description: str
    assigned_agent_id: Optional[UUID]
    requires_approval: bool
    estimated_cost_usd: float
    created_at: datetime

class TaskCreateSchema(Schema):
    task_type: str
    priority: str = "normal"
    description: str
    parameters: dict = {}

class DecisionSchema(Schema):
    id: UUID
    action_type: str
    target_resource: str
    provider: str
    reasoning: str
    status: str
    estimated_cost_usd: float
    admin_override: bool
    created_at: datetime

# ==================== Fleet Management ====================

@router.get("/fleet", response=FleetStatusSchema)
async def get_fleet_status(request):
    """Get current fleet status for the POD."""
    # Implementation
    pass

@router.post("/fleet/start")
async def start_fleet(request, budget_limit: float = 1000.0):
    """Start the agent fleet for the POD."""
    # Implementation
    pass

@router.post("/fleet/stop")
async def stop_fleet(request):
    """Stop the agent fleet and terminate all agents."""
    # Implementation
    pass

# ==================== Agent Management ====================

@router.get("/agents", response=List[AgentSchema])
async def list_agents(request):
    """List all agents in the fleet."""
    # Implementation
    pass

@router.get("/agents/{agent_id}", response=AgentSchema)
async def get_agent(request, agent_id: UUID):
    """Get details of a specific agent."""
    # Implementation
    pass

@router.post("/agents/spawn")
async def spawn_agent(request, role: str, task_context: Optional[str] = None):
    """Spawn a new specialist agent."""
    # Implementation
    pass

@router.post("/agents/{agent_id}/terminate")
async def terminate_agent(request, agent_id: UUID):
    """Terminate a specific agent."""
    # Implementation
    pass

# ==================== Task Management ====================

@router.get("/tasks", response=List[TaskSchema])
async def list_tasks(request, status: Optional[str] = None):
    """List all tasks."""
    # Implementation
    pass

@router.post("/tasks", response=TaskSchema)
async def create_task(request, data: TaskCreateSchema):
    """Submit a new task for execution."""
    # Implementation
    pass

@router.get("/tasks/{task_id}", response=TaskSchema)
async def get_task(request, task_id: UUID):
    """Get details of a specific task."""
    # Implementation
    pass

@router.post("/tasks/{task_id}/approve")
async def approve_task(request, task_id: UUID):
    """Approve a task that requires approval."""
    # Implementation
    pass

@router.post("/tasks/{task_id}/reject")
async def reject_task(request, task_id: UUID, reason: str):
    """Reject a task that requires approval."""
    # Implementation
    pass

# ==================== Decision Management ====================

@router.get("/decisions", response=List[DecisionSchema])
async def list_decisions(request, status: Optional[str] = None):
    """List all agent decisions."""
    # Implementation
    pass

@router.get("/decisions/{decision_id}", response=DecisionSchema)
async def get_decision(request, decision_id: UUID):
    """Get details of a specific decision."""
    # Implementation
    pass

@router.post("/decisions/{decision_id}/override")
async def override_decision(request, decision_id: UUID, action: str, notes: str):
    """Override an agent decision (approve/reject)."""
    # Implementation
    pass

# ==================== Direct Agent Communication ====================

@router.post("/message")
async def send_message(request, message: str, agent_id: Optional[UUID] = None):
    """Send a message directly to an agent."""
    # Implementation
    pass

@router.get("/message/stream/{context_id}")
async def stream_messages(request, context_id: str):
    """Stream messages from an agent via WebSocket."""
    # Implementation - returns WebSocket upgrade
    pass
```

---

## Summary: Agentic OS Platform Architecture

### Key Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| **Agent Fleet Manager** | Manage multiple agent instances, spawn specialists | `gpubrokeragent/services/fleet_manager.py` |
| **Task Orchestrator** | Queue and route tasks to appropriate agents | `gpubrokeragent/services/task_orchestrator.py` |
| **Agent Zero Client** | HTTP/WS/MCP communication with Agent Zero | `gpubrokeragent/services/agent_client.py` |
| **Decision Tracker** | Log and audit all agent decisions | `gpubrokeragent/services/decision_tracker.py` |
| **Budget Controller** | Track costs and enforce limits | `gpubrokeragent/services/budget_controller.py` |

### Agent Hierarchy

```
POD Admin (Human)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    GPUBROKER LAYER                           │
│  (Fleet Manager, Task Orchestrator, Budget Controller)       │
└─────────────────────────────────────────────────────────────┘
    │
    ▼ HTTP/WebSocket/MCP
┌─────────────────────────────────────────────────────────────┐
│                 AGENT ZERO (BLACK BOX)                       │
│                                                              │
│  Agent 0 (Orchestrator)                                      │
│      ├── Agent 1 (Provisioner)                               │
│      │       └── Agent 4 (Provider Specialist)               │
│      ├── Agent 2 (Optimizer)                                 │
│      │       └── Agent 5 (Researcher)                        │
│      └── Agent 3 (Monitor)                                   │
│              └── Agent 6 (Scheduler)                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Integration Principles

1. **BLACK BOX**: Agent Zero runs AS-IS - we do NOT modify its code
2. **Proxy Layer**: All communication goes through GPUBROKER Django layer
3. **RBAC**: Only POD Admin can access agent features
4. **Audit Trail**: Every message and decision is logged
5. **Budget Control**: Costs tracked and limits enforced in GPUBROKER layer
6. **Multi-Agent**: Leverage Agent Zero's `call_subordinate` for specialist agents
7. **Custom Profiles**: Create GPUBROKER-specific agent profiles (configuration only)

### Next Steps

1. ✅ Architecture Report (this document)
2. ⏳ Update requirements.md with multi-agent requirements
3. ⏳ Create design.md with detailed component specifications
4. ⏳ Create tasks.md with implementation plan
5. ⏳ Implement Agent Zero Client
6. ⏳ Implement Fleet Manager
7. ⏳ Implement Task Orchestrator
8. ⏳ Create custom agent profiles
9. ⏳ Implement API endpoints
10. ⏳ Integration testing

---

*Document Version: 1.0*
*Created: December 29, 2025*
*Author: GPUBROKER Architecture Team*
