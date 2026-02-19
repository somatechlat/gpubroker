# Software Requirements Specification (SRS)
**Project**: GPUBroker  
**Version**: 1.0.0  
**Date**: 2026-01-05  
**Standard**: ISO/IEC 29148:2018  
**Authors**: SOMA Engineering Team

---

## 1. Introduction

### 1.1 Purpose
This SRS specifies the complete software requirements for **GPUBroker**, an industrial-scale decentralized marketplace for high-performance AI compute resources (H100, A100, MI300X GPUs). This document provides an exhaustive description of all backend modules, streaming pipelines, frontend components, API contracts, and operational

 requirements.

### 1.2 Scope
GPUBroker is a **"No Brain Inside"** streaming broker that facilitates the trading of compute resources between providers (data centers, enterprises with idle GPUs) and consumers (AI startups, researchers).

**Backend Stack**:
- Django 5 + Django Ninja REST API
- Python 3.11 microservices
- Apache Kafka for event streaming
- Apache Flink for real-time aggregation
- Apache Airflow for batch orchestration
- PostgreSQL for transactional data
- ClickHouse for analytics
- Redis for caching and rate limiting

**Frontend Stack**:
- Lit 3 Web Components
- Bun 1.3.5 runtime
- Vite for development
- Universal "Clean Light Theme"

**Architecture Principle**: **"Isolated Local Ingress"** - Local Minikube/Tilt ingress is exposed on port 10355 and Kubernetes resources are isolated in the `gpubrokernamespace` namespace.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| Node | Physical server(s) with GPU hardware |
| Order | Bid or ask for compute time |
| Spot Market | Real-time auction for idle capacity |
| Reserved Instance | Pre-paid commitment for guaranteed capacity |
| Cluster | Group of nodes under single provider |
| POD | Provider Operations Dashboard |
| DAG | Directed Acyclic Graph (Airflow workflow) |
| Flink Job | Real-time stream processing application |

### 1.4 References
- ISO/IEC 29148:2018 - Requirements Engineering
- Apache Kafka Documentation
- Apache Flink Documentation
- Apache Airflow Documentation
- Django Ninja API Documentation

---

## 2. Overall Description

### 2.1 Product Perspective
GPUBroker is the **Compute Marketplace pillar** of the SOMA ecosystem, providing the hardware layer for:
- **AgentVoiceBox**: Voice model training and inference
- **Voyant**: Large-scale data processing
- **External customers**: AI labs, universities, enterprises

**System Integration**:
- **Keycloak**: OAuth2 identity provider
- **SpiceDB**: ReBAC authorization
- **PostgreSQL**: Transactional state
- **ClickHouse**: Time-series analytics (pricing, utilization)
- **Redis**: Session management and caching
- **Kafka**: Event backbone (orders, telemetry, billing)
- **Flink**: Real-time price aggregation and matching
- **Airflow**: Batch billing and reporting jobs
- **Prometheus/Grafana**: Observability stack
- **Lago**: Usage-based billing

### 2.2 Product Functions

#### Core Marketplace
1. **Order Matching**: Automated bid/ask matching engine
2. **Spot Market**: Dynamic pricing for immediate capacity
3. **Reserved Instances**: Long-term commitments with discounts
4. **Cluster Management**: Provider node orchestration
5. **Billing & Metering**: Per-second GPU billing

#### Provider Operations
1. **Node Registration**: Onboard GPU hardware to platform
2. **Health Monitoring**: Real-time node telemetry
3. **Revenue Analytics**: Provider earnings dashboards
4. **Deployment Automation**: Container orchestration on nodes

#### Consumer Operations
1. **Instance Launching**: Deploy workloads to rented GPUs
2. **SSH Access**: Secure remote login to instances
3. **Cost Tracking**: Real-time usage visibility
4. **Job Scheduling**: Queue management for compute tasks

### 2.3 User Classes

| User Class | Description | Technical Proficiency |
|------------|-------------|----------------------|
| **Platform Admin** | Manages infrastructure, monitors health, handles disputes | High |
| **Compute Provider** | Lists GPU hardware, sets pricing, monitors utilization | Medium-High |
| **Compute Consumer** | Rents GPUs, deploys workloads, tracks costs | Medium |
| **Developer** | Integrates GPUBroker APIs into ML pipelines | High |

### 2.4 Operating Environment

**Backend**:
- **OS**: Linux (Ubuntu 22.04 LTS)
- **Runtime**: Python 3.11
- **Database**: PostgreSQL 15, ClickHouse 24
- **Streaming**: Kafka 3.5, Flink 1.18
- **Orchestration**: Airflow 2.8, Tilt, Kubernetes
- **Local Ingress Port**: 10355 (Tilt/Minikube)

**Frontend**:
- **Browser**: Chrome/Firefox/Safari (latest 2 versions)
- **Runtime**: Bun 1.3.5
- **Dev Server**: Vite 5

### 2.5 Constraints

1. **Memory Limit**: 10GB total cluster memory allocation (production infrastructure constraint)
2. **Local Ingress**: Ingress MUST use port 10355 and resources MUST be isolated in `gpubrokernamespace`
3. **Log Rotation**: Aggressive log rotation to prevent disk exhaustion
4. **No Brain Inside**: Zero ML/AI processing in broker - pure marketplace logic
5. **Eventual Consistency**: Pricing and availability updates are eventually consistent

---

## 3. Backend System Architecture

### 3.1 Django Applications

#### 3.1.1 **apps/core**
**Purpose**: Shared foundation layer for all backend services.

**Modules** (3 files):
- `models.py`: BaseModel, TenantModel
- `utils.py`: Common utilities
- `exceptions.py`: Custom exceptions

**Key Responsibilities**:
- Base model classes with tenant isolation
- Shared utility functions
- Exception handling framework

---

#### 3.1.2 **apps/auth_app**
**Purpose**: Authentication and authorization.

**Modules** (13 files):
- `models.py`: User, Role, Permission
- `api.py`: Auth endpoints
- `keycloak_integration.py`: SSO integration
- `spicedb_integration.py`: ReBAC permissions
- `middleware.py`: Auth middleware
- `permissions.py`: Permission decorators

**Key Responsibilities**:
- User authentication via Keycloak
- Role-based access control
- API key management
- Session management

**API Endpoints**:
- `POST /api/v2/auth/login` - Login via OAuth
- `POST /api/v2/auth/logout` - Revoke session
- `GET /api/v2/auth/me` - Get current user
- `POST /api/v2/auth/api-keys` - Generate API key

**Database Tables**:
- `auth_user`
- `auth_role`
- `auth_permission`
- `auth_apikey`

---

#### 3.1.3 **apps/providers**
**Purpose**: GPU provider (data center) management.

**Modules** (16 files):
- `models.py`: Provider, Cluster, Node, GPU
- `api.py`: Provider management endpoints
- `telemetry.py`: Node health monitoring
- `pricing.py`: Dynamic pricing logic
- `availability.py`: Capacity tracking
- `billing.py`: Provider revenue calculation

**Key Responsibilities**:
- Provider onboarding and verification
- GPU node registration
- Real-time telemetry ingestion
- Pricing strategy configuration
- Revenue analytics

**API Endpoints**:
- `POST /api/v2/providers` - Register provider
- `GET /api/v2/providers/{id}` - Get provider details
- `POST /api/v2/providers/{id}/clusters` - Create cluster
- `POST /api/v2/clusters/{id}/nodes` - Register node
- `GET /api/v2/nodes/{id}/telemetry` - Get node health
- `PUT /api/v2/nodes/{id}/pricing` - Update node pricing

**Database Tables**:
- `providers_provider`
- `providers_cluster`
- `providers_node`
- `providers_gpu` (GPU specs: model, VRAM, CUDA version)
- `providers_telemetry` (time-series data)

**Telemetry Schema**:
```python
{
  "node_id": UUID,
  "timestamp": datetime,
  "gpu_utilization": float,  # 0.0-1.0
  "memory_utilization": float,
  "temperature": int,  # Celsius
  "power_draw": int,  # Watts
  "status": str  # "healthy" | "degraded" | "offline"
}
```

---

#### 3.1.4 **apps/math_core**
**Purpose**: Mathematical models for order matching and pricing.

**Modules** (13 files):
- `matching_engine.py`: Order book and matching algorithm
- `pricing_model.py`: Dynamic pricing calculations
- `auction.py`: Spot market auction logic
- `optimizer.py`: Resource allocation optimizer
- `validator.py`: Order validation rules

**Key Algorithms**:

**1. Order Matching** (Pro-Rata with Price-Time Priority):
```python
def match_orders(bids: List[Order], asks: List[Order]) -> List[Trade]:
    """
    Match bids and asks using pro-rata allocation.
    
    Algorithm:
    1. Sort bids descending by price, then by timestamp
    2. Sort asks ascending by price, then by timestamp
    3. For each bid-ask pair where bid_price >= ask_price:
       - Allocate GPUs proportionally to order size
       - Execute trades at midpoint price
    """
    trades = []
    bid_idx, ask_idx = 0, 0
    
    while bid_idx < len(bids) and ask_idx < len(asks):
        bid, ask = bids[bid_idx], asks[ask_idx]
        
        if bid.price >= ask.price:
            quantity = min(bid.remaining, ask.remaining)
            trade_price = (bid.price + ask.price) / 2
            
            trades.append(Trade(
                buyer=bid.user_id,
                seller=ask.user_id,
                quantity=quantity,
                price=trade_price,
                timestamp=now()
            ))
            
            bid.remaining -= quantity
            ask.remaining -= quantity
            
            if bid.remaining == 0:
                bid_idx += 1
            if ask.remaining == 0:
                ask_idx += 1
        else:
            break
    
    return trades
```

**2. Dynamic Pricing Model**:
```python
def calculate_spot_price(utilization: float, base_price: float) -> float:
    """
    Surge pricing based on cluster utilization.
    
    Formula: price = base_price * (1 + k * utilization^2)
    Where k = 2.0 (surge multiplier)
    """
    surge_multiplier = 2.0
    return base_price * (1 + surge_multiplier * (utilization ** 2))
```

**API Endpoints**:
- `POST /api/v2/orders/match` - Trigger manual match (admin only)
- `GET /api/v2/pricing/spot` - Get current spot prices
- `POST /api/v2/pricing/calculate` - Calculate estimated price

---

#### 3.1.5 **apps/kpi**
**Purpose**: Key Performance Indicators and analytics.

**Modules** (8 files):
- `models.py`: KPI, Metric, Dashboard
- `api.py`: Analytics endpoints
- `aggregator.py`: Metric aggregation logic
- `clickhouse_queries.py`: ClickHouse query templates

**Tracked KPIs**:
1. **Total Trading Volume** (USD/hour)
2. **GPU Utilization** (%)
3. **Average Spot Price** (USD/GPU-hour)
4. **Active Providers** (count)
5. **Active Consumers** (count)
6. **Order Fill Rate** (%)
7. **Platform Revenue** (USD)

**API Endpoints**:
- `GET /api/v2/kpi/dashboard` - Get summary KPIs
- `GET /api/v2/kpi/utilization` - Historical utilization
- `GET /api/v2/kpi/revenue` - Revenue breakdown

**ClickHouse Queries**:
```sql
-- Hourly trading volume
SELECT
    toStartOfHour(timestamp) as hour,
    sum(quantity * price) as volume_usd
FROM trades
WHERE timestamp >= now() - INTERVAL 24 HOUR
GROUP BY hour
ORDER BY hour;
```

---

#### 3.1.6 **apps/websocket_gateway**
**Purpose**: Real-time WebSocket communication.

**Modules** (8 files):
- `consumers.py`: WebSocket consumer classes
- `routing.py`: WebSocket URL routing
- `protocol.py`: Message formats
- `handlers/`: Event handlers

**Channels**:
1. `/ws/orders/{user_id}` - Order updates
2. `/ws/telemetry/{cluster_id}` - Live node metrics
3. `/ws/pricing` - Real-time price feed
4. `/ws/admin/control` - Admin control panel

**Message Protocol** (JSON-RPC 2.0):
```json
{
  "jsonrpc": "2.0",
  "method": "order.update",
  "params": {
    "order_id": "uuid",
    "status": "filled",
    "filled_quantity": 8,
    "avg_price": 2.45
  },
  "id": 123
}
```

---

#### 3.1.7 **apps/ai_assistant**
**Purpose**: MCP (Model Context Protocol) server for AI assistant integration.

**Modules** (9 files):
- `mcp_server.py`: MCP server implementation
- `tools.py`: Tool definitions for AI
- `context.py`: Context management
- `api.py`: Assistant endpoints

**MCP Tools Exposed**:
1. `list_clusters` - Get available GPU clusters
2. `get_spot_price` - Query current pricing
3. `create_order` - Place buy/sell order
4. `get_node_health` - Check node status
5. `calculate_costs` - Estimate job cost

**Purpose**: Enable AI agents (Agent Zero, etc.) to interact with marketplace programmatically.

---

### 3.2 Apache Kafka Topics

**Event Streaming Architecture**:

| Topic | Partitions | Retention | Purpose |
|-------|-----------|-----------|---------|
| `orders.created` | 10 | 7 days | New order submissions |
| `orders.matched` | 10 | 7 days | Matched trades |
| `orders.cancelled` | 10 | 7 days | Order cancellations |
| `telemetry.gpu` | 32 | 24 hours | GPU health metrics |
| `telemetry.node` | 32 | 24 hours | Node system metrics |
| `billing.usage` | 10 | 90 days | Compute usage events |
| `pricing.updates` | 1 | 1 hour | Price changes |
| `audit.log` | 5 | 365 days | Security audit trail |

**Event Schema Example** (`orders.created`):
```json
{
  "event_id": "uuid",
  "timestamp": "2026-01-05T09:30:00Z",
  "order": {
    "id": "uuid",
    "user_id": "uuid",
    "type": "bid",
    "gpu_type": "H100",
    "quantity": 8,
    "price": 2.50,
    "duration_hours": 24
  }
}
```

---

### 3.3 Apache Flink Jobs

#### 3.3.1 **flink_jobs/price_aggregator.py**
**Purpose**: Real-time price aggregation and index calculation.

**Input Stream**: `telemetry.gpu` + `orders.matched`  
**Output Stream**: `pricing.updates`  
**Window**: 5-minute tumbling window

**Processing Logic**:
```python
class PriceAggregator:
    def process_window(self, trades: List[Trade]) -> PriceUpdate:
        """
        Aggregate trades to calculate:
        - Weighted average price (by volume)
        - Min/max prices
        - Trading volume
        - Price volatility (std deviation)
        """
        total_volume = sum(t.quantity * t.price for t in trades)
        total_quantity = sum(t.quantity for t in trades)
        
        return PriceUpdate(
            gpu_type=trades[0].gpu_type,
            avg_price=total_volume / total_quantity,
            min_price=min(t.price for t in trades),
            max_price=max(t.price for t in trades),
            volume=total_volume,
            timestamp=now()
        )
```

**Deployment**: Flink Job Manager on port 28081

---

### 3.4 Apache Airflow DAGs

#### 3.4.1 **dags/billing_dag.py**
**Purpose**: Daily billing aggregation and invoice generation.

**Schedule**: `@daily` (runs at 00:00 UTC)

**Tasks**:
1. `extract_usage_events` - Query Kafka for billing events
2. `aggregate_by_tenant` - Sum usage per tenant
3. `calculate_charges` - Apply pricing tiers
4. `generate_invoices` - Create Lago invoices
5. `send_notifications` - Email invoices to tenants

**Dependencies**:
```
extract_usage_events >> aggregate_by_tenant >> calculate_charges >> generate_invoices >> send_notifications
```

**SLA**: Must complete within 2 hours

---

## 4. Frontend System Architecture

### 4.1 Directory Structure

```
frontend/src/
├── components/          # 4 Lit components
│   ├── saas-layout.ts
│   ├── saas-glass-modal.ts
│   ├── saas-status-dot.ts
│   └── saas-infra-card.ts
├── views/               # 2 page views
│   ├── view-login.ts
│   └── view-broker-setup.ts
├── lib/                 # 3 utility modules
│   ├── api-client.ts
│   ├── formatters.ts
│   └── validators.ts
└── styles/              # 1 global CSS
    └── globals.css
```

### 4.2 Core Components

#### 4.2.1 **view-broker-setup.ts**
**Purpose**: "Cluster Control Tower" - the Mother Screen for GPU providers.

**Layout**:
- **Top Panel**: Marketplace KPIs (volume, utilization, spot price)
- **Left Panel**: Provider's clusters and nodes
- **Right Panel**: Active orders and trades
- **Modals**: Node configuration, pricing strategy

**Features**:
1. Real-time cluster health visualization
2. GPU utilization charts
3. Revenue analytics
4. Order management
5. Pricing configuration

**API Calls**:
- `GET /api/v2/providers/me/clusters` - List my clusters
- `GET /api/v2/nodes?cluster_id={id}` - Get cluster nodes
- `GET /api/v2/kpi/dashboard` - Marketplace KPIs
- `WS /ws/telemetry/{cluster_id}` - Live metrics stream

**WebSocket Integration**:
```typescript
const ws = new WebSocket(`ws://localhost:28050/ws/telemetry/${clusterId}`);
ws.onmessage = (event) => {
  const telemetry = JSON.parse(event.data);
  updateNodeStatus(telemetry.node_id, telemetry);
};
```

---

## 5. API Specification

### 5.1 Order Management Endpoints

| Method | Endpoint | Description | Request Body |Response |
|--------|----------|-------------|--------------|---------|
| POST | `/api/v2/orders` | Create order (bid/ask) | `{type, gpu_type, quantity, price, duration_hours}` | `{order_id, status, created_at}` |
| GET | `/api/v2/orders` | List user's orders | Query: `?status=active&limit=50` | `{items[], total}` |
| GET | `/api/v2/orders/{id}` | Get order details | - | `{id, status, filled_quantity, ...}` |
| DELETE | `/api/v2/orders/{id}` | Cancel order | - | `{success: true}` |
| GET | `/api/v2/orders/{id}/trades` | Get order's trades | - | `{trades[]}` |

### 5.2 Provider Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/api/v2/providers` | Register as provider | `{name, company, kyc_data}` | `{provider_id}` |
| POST | `/api/v2/providers/{id}/clusters` | Create cluster | `{name, region, specs}` | `{cluster_id}` |
| POST | `/api/v2/clusters/{id}/nodes` | Register node | `{hostname, gpu_specs[]}` | `{node_id, onboarding_token}` |
| PUT | `/api/v2/nodes/{id}/pricing` | Set node pricing | `{base_price, surge_enabled}` | `{success: true}` |
| GET | `/api/v2/providers/me/revenue` | Get revenue analytics | Query: `?from=2026-01-01&to=2026-01-31` | `{total_revenue, breakdown[]}` |

### 5.3 Telemetry Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/api/v2/telemetry/batch` | Submit node metrics (batch) | `{node_id, metrics[]}` | `{accepted: 1200}` |
| GET | `/api/v2/telemetry/{node_id}` | Get node metrics | Query: `?from=timestamp&to=timestamp` | `{metrics[]}` |
| WebSocket | `/ws/telemetry/{cluster_id}` | Real-time metrics stream | - | JSON stream |

**Telemetry Submission Rate**: Max 1 event per node per 5 seconds

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Metric | Requirement | Notes |
|--------|-------------|-------|
| Order Matching Latency | < 50ms (p95) | From order submission to trade execution |
| API Response Time | < 100ms (p95) | All REST endpoints |
| WebSocket Latency | < 50ms | Message round-trip |
| Flink Processing Delay | < 10s | From Kafka event to aggregated result |
| Kafka Throughput | 100,000 msgs/sec | Cluster-wide |

### 6.2 Scalability

| Dimension | Target | Implementation |
|-----------|--------|----------------|
| Concurrent Orders | 1,000,000+ | Partitioned order book |
| Active Nodes | 100,000+ | Horizontal scaling |
| Trades per Second | 10,000+ | Kafka as event log |
| Telemetry Events/sec | 1,000,000+ | ClickHouse for time-series |

### 6.3 Reliability

**Uptime SLA**: 99.95% for trading engine  
**Data Durability**: 99.999999999% (Kafka replication factor 3)  
**Disaster Recovery**: RPO 5min, RTO 30min  

**Fault Tolerance**:
- Kafka: 3 replicas per partition
- PostgreSQL: Streaming replication (primary + 2 replicas)
- Flink: Checkpoints every 60 seconds
- Airflow: Retry failed tasks 3 times

### 6.4 Memory Constraints

**CRITICAL CONSTRAINT**: Total cluster memory allocation = 10GB

**Service Memory Allocation**:
| Service | Max Memory | Enforcement |
|---------|-----------|-------------|
| PostgreSQL | 2GB | `shared_buffers=512MB, max_connections=50` |
| Redis | 512MB | `maxmemory 512mb, maxmemory-policy allkeys-lru` |
| Kafka | 2GB | JVM heap size limited |
| Flink Job Manager | 1GB | `jobmanager.memory.process.size: 1GB` |
| Django API | 1.5GB | `gunicorn --workers 2 --max-requests 1000` |
| Airflow Scheduler | 512MB | `--concurrency 2` |

**Log Rotation** (to prevent disk exhaustion):
```bash
# All services rotate logs at 50MB, keep 2 files
/etc/logrotate.d/gpubroker:
  size 50M
  rotate 2
  compress
  delaycompress
```

### 6.5 Local Ingress & Namespace Isolation

Local Minikube/Tilt deployments expose ingress on port 10355 through Nginx.
All Kubernetes resources are scoped to the `gpubrokernamespace` namespace.

| Service | Port | Protocol |
|---------|------|----------|
| Nginx Ingress | 10355 | HTTP |

---

## 7. Data Models

### 7.1 Core Entities

#### Provider
```python
class Provider:
    id: UUID
    name: str
    company: str
    status: str  # "pending_kyc" | "verified" | "suspended"
    created_at: datetime
    total_revenue: Decimal
```

#### Cluster
```python
class Cluster:
    id: UUID
    provider_id: UUID
    name: str
    region: str  # "us-west-2", "eu-central-1"
    total_gpus: int
    available_gpus: int
    created_at: datetime
```

#### Node
```python
class Node:
    id: UUID
    cluster_id: UUID
    hostname: str
    ip_address: str
    gpus: List[GPU]
    status: str  # "healthy" | "degraded" | "offline"
    base_price: Decimal  # USD per GPU-hour
    surge_enabled: bool
    created_at: datetime
```

#### GPU
```python
class GPU:
    id: UUID
    node_id: UUID
    model: str  # "H100", "A100-80GB", "MI300X"
    vram_gb: int
    cuda_version: str
    pcie_slot: str
    status: str  # "available" | "allocated" | "maintenance"
```

#### Order
```python
class Order:
    id: UUID
    user_id: UUID
    type: str  # "bid" | "ask"
    gpu_type: str
    quantity: int
    price: Decimal
    duration_hours: int
    status: str  # "pending" | "partial" | "filled" | "cancelled"
    filled_quantity: int
    created_at: datetime
    expires_at: datetime
```

#### Trade
```python
class Trade:
    id: UUID
    order_id: UUID
    buyer_id: UUID
    seller_id: UUID
    gpu_type: str
    quantity: int
    price: Decimal
    executed_at: datetime
    instance_ids: List[UUID]  # Created compute instances
```

---

## 8. Deployment Architecture

### 8.1 Kubernetes Services

**Local + Production Stack** (Kubernetes services):

1. `postgres` - PostgreSQL 15
2. `redis` - Redis 7
3. `kafka-1`, `kafka-2`, `kafka-3` - Kafka cluster
4. `zookeeper` - Kafka coordination
5. `clickhouse` - Analytics database
6. `api` - Django REST API
7. `websocket` - WebSocket gateway
8. `flink-jobmanager` - Flink orchestrator
9. `flink-taskmanager` - Flink worker
10. `airflow-webserver` - Airflow UI
11. `airflow-scheduler` - DAG scheduler
12. `airflow-worker` - Task executor
13. `keycloak` - Identity provider
14. `prometheus` - Metrics collection
15. `grafana` - Visualization
16. `frontend` - Lit dev server (dev only)
17. `nginx` - Reverse proxy

### 8.2 Tilt Orchestration

**Tiltfile** manages:
- Kubernetes resources via `infrastructure/k8s/local-prod.yaml`
- Namespace/configmap/secret generation via `scripts/tilt/render-k8s-config.sh`
- Image builds via `minikube image build` for backend/frontend
- Automatic rebuild on dependency changes

**Services Health Checks**:
```yaml
# Each service must implement /health endpoint
# Example response:
{
  "status": "healthy",
  "timestamp": "2026-01-05T09:30:00Z",
  "uptime_seconds": 3600,
  "version": "1.0.0",
  "dependencies": {
    "postgres": "connected",
    "redis": "connected",
    "kafka": "connected"
  }
}
```

---

## 9. Testing Requirements

### 9.1 Backend Tests

**Unit Tests** (pytest):
- 80%+ coverage
- All matching engine algorithms
- Pricing model calculations
- Data validation logic

**Integration Tests**:
- API endpoint contracts
- Kafka producer/consumer flows
- PostgreSQL transactions
- ClickHouse queries

**Stream Processing Tests** (Flink):
- Window aggregation correctness
- Late event handling
- Exactly-once semantics

### 9.2 E2E Tests (Playwright)

**Critical User Flows**:
1. Provider registers cluster → Add nodes → Set pricing
2. Consumer places bid → Order matched → Trade executed
3. Admin views marketplace KPIs → Exports reports

**Performance Tests**:
- Order submission throughput (target: 1000 orders/sec)
- WebSocket concurrent connections (target: 10,000)

---

## 10. Verification & Validation

### 10.1 Acceptance Criteria

**Order Matching**:
- ✅ Orders match within 50ms of submission
- ✅ Matching follows pro-rata rules correctly
- ✅ No double-allocation of GPUs

**Billing Accuracy**:
- ✅ Usage tracked with per-second granularity
- ✅ Pricing calculations match specifications
- ✅ Invoices generated daily without failures

**Scalability**:
- ✅ System handles 1M orders/day without degradation
- ✅ Memory usage stays under 10GB cluster-wide
- ✅ Ingress uses port 10355 and resources are isolated in `gpubrokernamespace`

### 10.2 Manual Verification

1. Run `tilt up` in `gpubroker/`
2. Verify all services healthy at `http://localhost:28090` (Airflow UI)
3. Navigate to `http://localhost:28100` (Frontend)
4. Complete provider registration flow
5. Submit test order via API
6. Verify Kafka events in topic `orders.created`
7. Verify Flink job aggregates prices
8. Verify ClickHouse stores telemetry

---

## 11. Operational Requirements

### 11.1 Monitoring

**Prometheus Metrics**:
- `gpubroker_orders_total{type="bid|ask"}` - Counter
- `gpubroker_trades_executed_total` - Counter
- `gpubroker_gpu_utilization{cluster_id}` - Gauge
- `gpubroker_api_latency_seconds` - Histogram
- `gpubroker_kafka_lag{topic,partition}` - Gauge

**Grafana Dashboards**:
1. **Marketplace Overview** - Trading volume, spot prices, utilization
2. **Provider Dashboard** - Revenue, node health, availability
3. **System Health** - Service uptime, memory usage, API latency
4. **Kafka Monitoring** - Throughput, lag, consumer metrics

### 11.2 Alerting

**Critical Alerts** (PagerDuty):
- API error rate > 1%
- Kafka consumer lag > 10,000 messages
- PostgreSQL replica lag > 30s
- Cluster memory usage > 9GB
- Any service down > 2 minutes

### 11.3 Backup & Recovery

**PostgreSQL**:
- Continuous WAL archiving to S3
- Daily full backups
- Point-in-time recovery supported

**Kafka**:
- Replication factor 3
- Topic backups via Mirror Maker

**ClickHouse**:
- Daily snapshots to S3
- 90-day retention

---

**END OF GPUBROKER SRS v1.0.0**
