# Requirements Document

## Introduction

The Provider API Gateway is the central nervous system of GPUBROKER - a high-performance, horizontally scalable gateway that aggregates GPU pricing and availability data from 20+ cloud providers. This system must handle **MILLIONS OF CONCURRENT USERS** while maintaining sub-100ms response times, implementing intelligent caching, circuit breakers, rate limiting, and load balancing across provider adapters.

### Target Scale

| Metric | Target |
|--------|--------|
| Concurrent Users | 10,000,000+ |
| Requests Per Second (Global) | 1,000,000+ RPS |
| Requests Per Second (Per Instance) | 10,000+ RPS |
| Response Time (P50) | < 50ms |
| Response Time (P99) | < 100ms |
| Availability | 99.99% (52 min downtime/year) |
| Data Freshness | < 60 seconds |

### Apache Stack for Scale (NO CELERY, NO ZOOKEEPER)

| Component | Purpose | Why Essential |
|-----------|---------|---------------|
| **Apache Kafka (KRaft Mode)** | Event streaming backbone | Decouples services, handles 1M+ events/sec, **NO ZOOKEEPER** - uses KRaft consensus |
| **Apache Flink** | Real-time stream processing | Sub-second price change detection, anomaly detection |
| **Apache Airflow** | Workflow orchestration | **Replaces Celery**, better visibility, DAG-based scheduling |

> **IMPORTANT**: Kafka runs in KRaft mode (Kafka Raft) - NO ZooKeeper dependency. This simplifies deployment and improves performance.

### Architecture for Millions of Users

```
                                    MILLIONS OF USERS
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │   Global CDN (Edge)   │
                              │   CloudFlare/Fastly   │
                              └───────────┬───────────┘
                                          │
                              ┌───────────▼───────────┐
                              │  Global Load Balancer │
                              │   (AWS ALB / nginx)   │
                              └───────────┬───────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
          ┌─────────▼─────────┐ ┌─────────▼─────────┐ ┌─────────▼─────────┐
          │  Region: US-EAST  │ │  Region: EU-WEST  │ │  Region: AP-SOUTH │
          └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
                    │                     │                     │
          ┌─────────▼─────────────────────▼─────────────────────▼─────────┐
          │                    KUBERNETES CLUSTER                          │
          │  ┌─────────────────────────────────────────────────────────┐  │
          │  │              Django Gateway Pods (Auto-scaling)          │  │
          │  │   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ... ┌─────┐   │  │
          │  │   │ GW1 │ │ GW2 │ │ GW3 │ │ GW4 │ │ GW5 │     │GW-N │   │  │
          │  │   └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘     └──┬──┘   │  │
          │  └──────┼───────┼───────┼───────┼───────┼───────────┼──────┘  │
          │         │       │       │       │       │           │         │
          │  ┌──────▼───────▼───────▼───────▼───────▼───────────▼──────┐  │
          │  │                    Redis Cluster                         │  │
          │  │   ┌─────────┐  ┌─────────┐  ┌─────────┐                 │  │
          │  │   │ Master  │  │ Replica │  │ Replica │  (6+ nodes)     │  │
          │  │   └─────────┘  └─────────┘  └─────────┘                 │  │
          │  └─────────────────────────────────────────────────────────┘  │
          │                                                               │
          │  ┌─────────────────────────────────────────────────────────┐  │
          │  │           Apache Kafka Cluster (KRaft - NO ZOOKEEPER)    │  │
          │  │   ┌────────┐  ┌────────┐  ┌────────┐                    │  │
          │  │   │Broker 1│  │Broker 2│  │Broker 3│  (3+ brokers)      │  │
          │  │   │+Ctrl   │  │+Ctrl   │  │+Ctrl   │  (Combined mode)   │  │
          │  │   └────────┘  └────────┘  └────────┘                    │  │
          │  │   Topics: price-updates, provider-events, webhooks      │  │
          │  └─────────────────────────────────────────────────────────┘  │
          │                                                               │
          │  ┌─────────────────────────────────────────────────────────┐  │
          │  │                    Apache Flink Cluster                  │  │
          │  │   ┌───────────┐  ┌─────────────┐  ┌─────────────┐       │  │
          │  │   │JobManager │  │TaskManager 1│  │TaskManager N│       │  │
          │  │   └───────────┘  └─────────────┘  └─────────────┘       │  │
          │  │   Jobs: PriceChangeDetector, AnomalyDetector            │  │
          │  └─────────────────────────────────────────────────────────┘  │
          │                                                               │
          │  ┌─────────────────────────────────────────────────────────┐  │
          │  │                    Apache Airflow (NO CELERY)            │  │
          │  │   ┌───────────┐  ┌────────┐  ┌────────┐                 │  │
          │  │   │ Scheduler │  │Worker 1│  │Worker N│                 │  │
          │  │   └───────────┘  └────────┘  └────────┘                 │  │
          │  │   DAGs: cache_warming, health_checks, data_sync         │  │
          │  └─────────────────────────────────────────────────────────┘  │
          │                                                               │
          │  ┌─────────────────────────────────────────────────────────┐  │
          │  │                    PostgreSQL Cluster                    │  │
          │  │   ┌────────┐  ┌─────────┐  ┌─────────┐                  │  │
          │  │   │Primary │  │Read Rep │  │Read Rep │  (Patroni HA)    │  │
          │  │   └────────┘  └─────────┘  └─────────┘                  │  │
          │  └─────────────────────────────────────────────────────────┘  │
          │                                                               │
          │  ┌─────────────────────────────────────────────────────────┐  │
          │  │                    HashiCorp Vault                       │  │
          │  │   Secure credential storage for all provider API keys   │  │
          │  └─────────────────────────────────────────────────────────┘  │
          └───────────────────────────────────────────────────────────────┘
```

## Glossary

- **Gateway**: The central API aggregation layer that routes requests to provider adapters
- **Provider_Adapter**: A normalized interface to a specific GPU cloud provider (RunPod, Vast.ai, AWS, etc.)
- **Circuit_Breaker**: A fault-tolerance pattern that prevents cascading failures when providers are unavailable
- **Rate_Limiter**: A component that enforces request quotas per user/plan tier
- **Cache_Layer**: Multi-tier caching (Redis L1, in-memory L2) for provider responses
- **Load_Balancer**: Distributes requests across adapter instances and manages provider health
- **Offer**: A normalized GPU rental offer with price, specs, and availability
- **Health_Check**: Periodic probe to verify provider API availability
- **WebSocket_Gateway**: Django Channels-based real-time communication layer (always available)
- **Kafka_Producer**: Component that publishes events to Apache Kafka topics
- **Kafka_Consumer**: Component that consumes events from Apache Kafka topics
- **Flink_Job**: Apache Flink streaming job for real-time data processing
- **Airflow_Scheduler**: Apache Airflow component that schedules DAG execution
- **Airflow_Worker**: Apache Airflow component that executes tasks
- **DAG**: Directed Acyclic Graph - Airflow workflow definition
- **SSE**: Server-Sent Events - one-way streaming from server to client

## Requirements

### Requirement 1: High-Performance Request Handling

**User Story:** As a GPUBROKER user, I want the API to respond within 100ms even under heavy load, so that I can make real-time GPU rental decisions.

#### Acceptance Criteria

1. THE Gateway SHALL handle at least 10,000 concurrent requests per second per instance
2. WHEN a cached response exists, THE Gateway SHALL return it within 10ms
3. WHEN fetching from providers, THE Gateway SHALL parallelize requests to all adapters
4. THE Gateway SHALL use async/await patterns throughout for non-blocking I/O
5. WHEN response time exceeds 5 seconds, THE Gateway SHALL timeout and return cached data or error

### Requirement 2: Multi-Tier Caching Strategy

**User Story:** As a system architect, I want intelligent caching to reduce provider API calls and improve response times, so that the system remains performant and cost-effective.

#### Acceptance Criteria

1. THE Cache_Layer SHALL implement L1 (Redis) and L2 (in-memory) caching
2. WHEN a request arrives, THE Gateway SHALL check L2 cache first, then L1, then fetch from providers
3. THE Cache_Layer SHALL store provider responses with configurable TTL (default: 60 seconds for pricing, 300 seconds for static data)
4. WHEN cache is invalidated, THE Gateway SHALL refresh data asynchronously without blocking requests
5. THE Cache_Layer SHALL implement cache stampede prevention using probabilistic early expiration
6. WHEN Redis is unavailable, THE Gateway SHALL fall back to L2 in-memory cache gracefully

### Requirement 3: Circuit Breaker Pattern

**User Story:** As a system operator, I want the gateway to gracefully handle provider failures, so that one failing provider doesn't bring down the entire system.

#### Acceptance Criteria

1. THE Circuit_Breaker SHALL track failure rates per provider adapter
2. WHEN failure rate exceeds 50% over 10 requests, THE Circuit_Breaker SHALL open the circuit
3. WHILE circuit is open, THE Gateway SHALL return cached data or skip the provider
4. WHEN circuit is open for 30 seconds, THE Circuit_Breaker SHALL enter half-open state
5. WHEN a request succeeds in half-open state, THE Circuit_Breaker SHALL close the circuit
6. THE Circuit_Breaker SHALL emit metrics for monitoring (open/closed/half-open counts)

### Requirement 4: Rate Limiting by Plan Tier

**User Story:** As a product manager, I want to enforce different rate limits based on subscription tier, so that we can monetize API access fairly.

#### Acceptance Criteria

1. THE Rate_Limiter SHALL enforce requests per second limits: Free=10, Pro=100, Enterprise=1000
2. WHEN rate limit is exceeded, THE Gateway SHALL return HTTP 429 with Retry-After header
3. THE Rate_Limiter SHALL use sliding window algorithm for smooth rate limiting
4. THE Rate_Limiter SHALL identify users by JWT claims or API key
5. WHEN user is anonymous, THE Rate_Limiter SHALL apply Free tier limits by IP address
6. THE Rate_Limiter SHALL store counters in Redis for distributed rate limiting

### Requirement 5: Provider Adapter Load Balancing

**User Story:** As a system architect, I want to distribute load across provider adapters intelligently, so that no single adapter becomes a bottleneck.

#### Acceptance Criteria

1. THE Load_Balancer SHALL distribute requests using weighted round-robin based on provider health
2. WHEN a provider is slow (>2s response), THE Load_Balancer SHALL reduce its weight
3. THE Load_Balancer SHALL support provider-specific concurrency limits
4. WHEN all providers are unhealthy, THE Gateway SHALL return cached data with warning
5. THE Load_Balancer SHALL implement request queuing with backpressure for burst handling

### Requirement 6: Health Monitoring and Metrics

**User Story:** As a DevOps engineer, I want comprehensive health monitoring, so that I can proactively identify and resolve issues.

#### Acceptance Criteria

1. THE Gateway SHALL expose Prometheus metrics for request latency, throughput, and error rates
2. THE Gateway SHALL perform periodic health checks on all provider adapters (every 30 seconds)
3. WHEN a provider health check fails, THE Gateway SHALL mark it as unhealthy
4. THE Gateway SHALL expose a /health endpoint with detailed provider status
5. THE Gateway SHALL log all requests with trace IDs for distributed tracing (OpenTelemetry)

### Requirement 7: Request Aggregation and Normalization

**User Story:** As a developer, I want a unified API that aggregates data from all providers, so that I don't need to integrate with each provider separately.

#### Acceptance Criteria

1. THE Gateway SHALL normalize all provider responses into a standard Offer schema
2. WHEN fetching offers, THE Gateway SHALL query all healthy providers in parallel
3. THE Gateway SHALL merge and deduplicate offers from multiple providers
4. THE Gateway SHALL support filtering by GPU type, price range, region, and availability
5. THE Gateway SHALL support sorting by price, performance, or custom scoring (TOPSIS)
6. THE Gateway SHALL paginate results with cursor-based pagination for large datasets

### Requirement 8: Horizontal Scalability

**User Story:** As a system architect, I want the gateway to scale horizontally, so that we can handle traffic growth by adding more instances.

#### Acceptance Criteria

1. THE Gateway SHALL be stateless, storing all state in Redis/PostgreSQL
2. THE Gateway SHALL support running multiple instances behind a load balancer
3. WHEN a new instance starts, THE Gateway SHALL warm its cache from Redis
4. THE Gateway SHALL use connection pooling for database and Redis connections
5. THE Gateway SHALL support graceful shutdown with request draining

### Requirement 9: Provider Credential Management

**User Story:** As a security engineer, I want provider API keys stored securely in Vault, so that credentials are never exposed in code or logs.

#### Acceptance Criteria

1. THE Gateway SHALL fetch provider API keys from HashiCorp Vault
2. THE Gateway SHALL cache Vault tokens with automatic renewal
3. WHEN Vault is unavailable, THE Gateway SHALL use cached credentials for up to 1 hour
4. THE Gateway SHALL never log API keys or sensitive credentials
5. THE Gateway SHALL support per-user provider credentials for enterprise customers

### Requirement 10: Apache Airflow Workflow Orchestration (NO CELERY)

**User Story:** As a system architect, I want Apache Airflow for workflow orchestration, so that background tasks have visibility, retries, and scheduling.

#### Acceptance Criteria

1. THE Gateway SHALL use Apache Airflow for all scheduled background tasks
2. THE Airflow_Scheduler SHALL run cache warming DAGs every 5 minutes
3. THE Airflow_Scheduler SHALL run health check DAGs every 30 seconds (via sensor)
4. THE Airflow_Scheduler SHALL run data sync DAGs hourly
5. WHEN a task fails, THE Airflow_Worker SHALL retry with exponential backoff
6. THE Gateway SHALL NOT use Celery for any background task execution

### Requirement 11: WebSocket Real-Time Updates (ALWAYS AVAILABLE)

**User Story:** As a GPUBROKER user, I want real-time updates via WebSocket, so that I can see price changes and availability instantly without polling.

#### Acceptance Criteria

1. THE Gateway SHALL provide WebSocket endpoints via Django Channels
2. THE WebSocket_Gateway SHALL be always available as primary real-time channel
3. WHEN a price changes, THE Gateway SHALL push update to all subscribed WebSocket clients
4. THE WebSocket_Gateway SHALL support subscription channels: price_updates, health_status, availability, provider:{name}, gpu:{type}, region:{name}
5. WHEN a client connects, THE WebSocket_Gateway SHALL send connection confirmation with available subscriptions
6. THE WebSocket_Gateway SHALL support ping/pong for connection health
7. WHEN a client disconnects, THE Gateway SHALL clean up subscriptions gracefully

### Requirement 12: Apache Kafka Event Streaming

**User Story:** As a system architect, I want Apache Kafka as the event backbone, so that all components can communicate asynchronously with guaranteed delivery.

#### Acceptance Criteria

1. THE Gateway SHALL publish price update events to Kafka topic gpubroker.price-updates
2. THE Gateway SHALL publish provider events to Kafka topic gpubroker.provider-events
3. THE Gateway SHALL publish webhook requests to Kafka topic gpubroker.webhooks
4. WHEN publishing to Kafka, THE Gateway SHALL use snappy compression and batching
5. THE Kafka_Consumer SHALL process events with at-least-once delivery guarantee
6. THE Gateway SHALL support Kafka unavailability with local queue fallback

### Requirement 13: Apache Flink Real-Time Stream Processing

**User Story:** As a data engineer, I want Apache Flink for real-time stream processing, so that we can detect price changes and anomalies in real-time.

#### Acceptance Criteria

1. THE Flink_Job SHALL consume from gpubroker.price-updates topic
2. THE Flink_Job SHALL detect significant price changes (>5% threshold)
3. THE Flink_Job SHALL detect pricing anomalies using statistical analysis (z-score > 3)
4. THE Flink_Job SHALL compute real-time aggregations (avg price per GPU type, 1-minute windows)
5. THE Flink_Job SHALL publish alerts to gpubroker.price-alerts topic
6. WHEN Flink detects a significant change, THE Gateway SHALL notify WebSocket subscribers

### Requirement 14: Multiple Connection Methods

**User Story:** As a developer, I want multiple ways to connect to the Gateway, so that I can choose the best method for my use case.

#### Acceptance Criteria

1. THE Gateway SHALL support REST API via Django Ninja (primary)
2. THE Gateway SHALL support WebSocket via Django Channels (real-time)
3. THE Gateway SHALL support Server-Sent Events (SSE) for one-way streaming
4. THE Gateway SHALL expose metrics via Prometheus endpoint (/metrics)
5. THE Gateway SHALL expose health via dedicated endpoint (/health)
6. ALL connection methods SHALL share the same authentication (JWT)


---

## User Journey Stories

### Journey 1: Anonymous User Browsing GPU Offers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  JOURNEY 1: Anonymous User Browsing GPU Offers                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. User visits GPUBROKER website                                          │
│     └─► Frontend loads, connects to WebSocket                              │
│                                                                             │
│  2. User views GPU offers list                                             │
│     └─► GET /api/v2/providers?page=1&per_page=20                          │
│     └─► Rate limited at Free tier (10 RPS by IP)                          │
│     └─► Response from L2 cache (if hit) or L1 Redis or live fetch         │
│                                                                             │
│  3. User applies filters (GPU type, price, region)                         │
│     └─► GET /api/v2/providers?gpu=A100&max_price=2.0&region=us-east       │
│     └─► Filters applied server-side, cached response                       │
│                                                                             │
│  4. User receives real-time price update via WebSocket                     │
│     └─► WebSocket message: {type: "price_update", provider: "vastai", ...} │
│     └─► Frontend updates UI without refresh                                │
│                                                                             │
│  5. User clicks on offer to see details                                    │
│     └─► GET /api/v2/providers/{offer_id}                                  │
│     └─► Detailed offer with specs, availability, compliance tags           │
│                                                                             │
│  6. User wants to rent → prompted to register/login                        │
│     └─► Redirect to /auth/login or /auth/register                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Journey 2: Registered User with Pro Plan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  JOURNEY 2: Registered User with Pro Plan                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. User logs in                                                           │
│     └─► POST /api/v2/auth/login {email, password}                         │
│     └─► Returns JWT access_token + refresh_token                          │
│                                                                             │
│  2. User connects to WebSocket with JWT                                    │
│     └─► ws://host/ws/providers/?token={jwt}                               │
│     └─► Authenticated connection, Pro tier rate limits                     │
│                                                                             │
│  3. User subscribes to specific channels                                   │
│     └─► WebSocket: {type: "subscribe", channel: "gpu:A100"}               │
│     └─► WebSocket: {type: "subscribe", channel: "provider:vastai"}        │
│                                                                             │
│  4. User browses offers with higher rate limit (100 RPS)                   │
│     └─► GET /api/v2/providers with X-Plan: pro header                     │
│     └─► Access to advanced filters and sorting                             │
│                                                                             │
│  5. User uses TOPSIS ranking for best value                                │
│     └─► GET /api/v2/providers/ranking?method=topsis&weights=price:0.5,...  │
│     └─► Returns offers ranked by multi-criteria decision analysis          │
│                                                                             │
│  6. User saves favorite offers                                             │
│     └─► POST /api/v2/users/favorites {offer_id}                           │
│     └─► Stored in PostgreSQL, synced across devices                        │
│                                                                             │
│  7. User sets price alert                                                  │
│     └─► POST /api/v2/alerts {gpu_type: "A100", max_price: 1.5}            │
│     └─► Alert stored, Flink job monitors for condition                     │
│     └─► When triggered: WebSocket notification + email                     │
│                                                                             │
│  8. User initiates GPU rental                                              │
│     └─► POST /api/v2/rentals {offer_id, duration_hours}                   │
│     └─► Gateway calls provider API with user's credentials                 │
│     └─► Returns rental confirmation with connection details                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Journey 3: Enterprise User with Custom Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  JOURNEY 3: Enterprise User with Custom Integration                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Enterprise admin configures provider credentials                        │
│     └─► POST /api/v2/providers/config/integrations                        │
│         {provider: "vastai", api_key: "xxx"}                               │
│     └─► Credentials stored in Vault under enterprise namespace             │
│                                                                             │
│  2. Enterprise sets up webhook for price changes                           │
│     └─► POST /api/v2/webhooks                                             │
│         {url: "https://enterprise.com/webhook", events: ["price_change"]}  │
│     └─► Webhook registered, Kafka consumer will deliver events             │
│                                                                             │
│  3. Enterprise uses API with high rate limit (1000 RPS)                    │
│     └─► All requests with X-Plan: enterprise header                       │
│     └─► Dedicated rate limit bucket per API key                            │
│                                                                             │
│  4. Enterprise integrates with their ML pipeline                           │
│     └─► GET /api/v2/providers/stream (SSE)                                │
│     └─► Continuous stream of price updates for ML training                 │
│                                                                             │
│  5. Enterprise uses bulk operations                                        │
│     └─► POST /api/v2/providers/bulk/query                                 │
│         {queries: [{gpu: "A100", region: "us-east"}, ...]}                 │
│     └─► Batch query for multiple GPU types/regions                         │
│                                                                             │
│  6. Enterprise accesses analytics API                                      │
│     └─► GET /api/v2/analytics/price-history?gpu=A100&days=30              │
│     └─► Historical price data for analysis                                 │
│                                                                             │
│  7. Enterprise receives webhook notification                               │
│     └─► Kafka → Airflow webhook_delivery DAG → Enterprise endpoint        │
│     └─► Retry with exponential backoff on failure                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Journey 4: AI Agent Autonomous GPU Procurement

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  JOURNEY 4: AI Agent Autonomous GPU Procurement                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. AI Agent authenticates via service account                             │
│     └─► POST /api/v2/auth/service-token                                   │
│         {service_id: "ml-pipeline-agent", secret: "xxx"}                   │
│     └─► Returns long-lived service JWT                                     │
│                                                                             │
│  2. AI Agent queries available GPUs matching requirements                  │
│     └─► POST /api/v2/providers/query                                      │
│         {                                                                   │
│           gpu_type: "A100",                                                │
│           min_memory_gb: 80,                                               │
│           max_price: 2.0,                                                  │
│           min_availability: "available",                                   │
│           regions: ["us-east", "us-west"],                                 │
│           compliance_tags: ["soc2", "hipaa"]                               │
│         }                                                                   │
│                                                                             │
│  3. AI Agent uses decision API for optimal selection                       │
│     └─► POST /api/v2/providers/decide                                     │
│         {                                                                   │
│           candidates: [offer_ids],                                         │
│           criteria: {                                                       │
│             price: {weight: 0.4, direction: "minimize"},                   │
│             performance: {weight: 0.3, direction: "maximize"},             │
│             availability: {weight: 0.2, direction: "maximize"},            │
│             latency: {weight: 0.1, direction: "minimize"}                  │
│           },                                                                │
│           method: "topsis"                                                 │
│         }                                                                   │
│     └─► Returns ranked offers with scores                                  │
│                                                                             │
│  4. AI Agent provisions GPU automatically                                  │
│     └─► POST /api/v2/rentals/provision                                    │
│         {offer_id: "xxx", duration_hours: 24, auto_renew: true}           │
│     └─► Gateway provisions via provider API                                │
│     └─► Returns connection details (SSH, Jupyter, etc.)                    │
│                                                                             │
│  5. AI Agent monitors rental health                                        │
│     └─► WebSocket subscription to rental:{rental_id}                      │
│     └─► Receives health updates, utilization metrics                       │
│                                                                             │
│  6. AI Agent scales based on workload                                      │
│     └─► POST /api/v2/rentals/{rental_id}/scale                            │
│         {action: "add", count: 2}                                          │
│     └─► Provisions additional GPUs from same/similar offers                │
│                                                                             │
│  7. AI Agent terminates when done                                          │
│     └─► DELETE /api/v2/rentals/{rental_id}                                │
│     └─► Gateway terminates via provider API                                │
│     └─► Final cost calculated and logged                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Inter-Module Communication API

### Requirement 15: Internal Service Communication

**User Story:** As a system architect, I want well-defined APIs for inter-module communication, so that services can communicate reliably and be developed independently.

#### Acceptance Criteria

1. THE Gateway SHALL expose internal APIs for other GPUBROKER modules
2. THE Gateway SHALL authenticate internal requests via service tokens
3. THE Gateway SHALL support both sync (REST) and async (Kafka) communication
4. THE Gateway SHALL implement circuit breakers for internal service calls
5. THE Gateway SHALL log all inter-service communication with correlation IDs

### Internal API Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INTERNAL API ENDPOINTS (for other GPUBROKER modules)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  KPI Module Integration:                                                    │
│  ├─► GET  /internal/v1/providers/stats                                     │
│  │       Returns: provider count, offer count, avg prices                  │
│  ├─► GET  /internal/v1/providers/health-summary                            │
│  │       Returns: health status of all providers                           │
│  └─► POST /internal/v1/providers/metrics                                   │
│          Accepts: custom metrics from KPI module                           │
│                                                                             │
│  AI Assistant Integration:                                                  │
│  ├─► POST /internal/v1/providers/recommend                                 │
│  │       Accepts: user requirements, budget, preferences                   │
│  │       Returns: AI-ranked recommendations                                │
│  ├─► POST /internal/v1/providers/explain                                   │
│  │       Accepts: offer_id                                                 │
│  │       Returns: natural language explanation of offer                    │
│  └─► POST /internal/v1/providers/compare                                   │
│          Accepts: [offer_ids]                                              │
│          Returns: detailed comparison matrix                               │
│                                                                             │
│  Billing Module Integration:                                                │
│  ├─► GET  /internal/v1/providers/pricing/{offer_id}                        │
│  │       Returns: current pricing, historical avg                          │
│  ├─► POST /internal/v1/rentals/cost-estimate                               │
│  │       Accepts: offer_id, duration, options                              │
│  │       Returns: estimated cost breakdown                                 │
│  └─► POST /internal/v1/rentals/finalize                                    │
│          Accepts: rental_id, final_duration                                │
│          Returns: final cost, invoice data                                 │
│                                                                             │
│  Auth Module Integration:                                                   │
│  ├─► POST /internal/v1/auth/validate-token                                 │
│  │       Accepts: JWT token                                                │
│  │       Returns: user_id, plan, permissions                               │
│  └─► GET  /internal/v1/auth/service-permissions/{service_id}               │
│          Returns: allowed endpoints, rate limits                           │
│                                                                             │
│  Notification Module Integration:                                           │
│  ├─► POST /internal/v1/notifications/price-alert                           │
│  │       Accepts: user_id, alert_config, triggered_offer                   │
│  │       Triggers: email, push, in-app notification                        │
│  └─► POST /internal/v1/notifications/rental-status                         │
│          Accepts: user_id, rental_id, status_change                        │
│          Triggers: appropriate notifications                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Requirement 16: Inter-Agent Communication Protocol

**User Story:** As an AI/ML engineer, I want a standardized protocol for AI agents to communicate with the Gateway, so that autonomous systems can procure and manage GPU resources.

#### Acceptance Criteria

1. THE Gateway SHALL support Agent-to-Agent (A2A) communication protocol
2. THE Gateway SHALL authenticate agents via service tokens with scoped permissions
3. THE Gateway SHALL support agent capability discovery
4. THE Gateway SHALL implement agent request queuing with priority
5. THE Gateway SHALL log all agent actions for audit and debugging

### Agent Communication Protocol

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENT-TO-AGENT (A2A) COMMUNICATION PROTOCOL                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Agent Registration:                                                        │
│  POST /api/v2/agents/register                                              │
│  {                                                                          │
│    "agent_id": "ml-training-agent-001",                                    │
│    "agent_type": "autonomous",                                             │
│    "capabilities": ["query", "provision", "scale", "terminate"],           │
│    "owner_id": "enterprise-123",                                           │
│    "callback_url": "https://agent.enterprise.com/callback",                │
│    "max_budget_per_hour": 100.0,                                           │
│    "allowed_providers": ["vastai", "runpod", "lambdalabs"]                 │
│  }                                                                          │
│  Returns: {agent_token, permissions, rate_limits}                          │
│                                                                             │
│  Agent Capability Discovery:                                                │
│  GET /api/v2/agents/capabilities                                           │
│  Returns:                                                                   │
│  {                                                                          │
│    "gateway_version": "2.0.0",                                             │
│    "supported_actions": [                                                   │
│      {"action": "query", "endpoint": "/providers/query", "method": "POST"},│
│      {"action": "decide", "endpoint": "/providers/decide", "method": "POST"},
│      {"action": "provision", "endpoint": "/rentals/provision", "method": "POST"},
│      {"action": "scale", "endpoint": "/rentals/{id}/scale", "method": "POST"},
│      {"action": "terminate", "endpoint": "/rentals/{id}", "method": "DELETE"}
│    ],                                                                       │
│    "supported_criteria": ["price", "performance", "availability", "latency"],
│    "supported_methods": ["topsis", "weighted_sum", "pareto"]               │
│  }                                                                          │
│                                                                             │
│  Agent Action Request:                                                      │
│  POST /api/v2/agents/actions                                               │
│  {                                                                          │
│    "action": "provision",                                                  │
│    "priority": "high",                                                     │
│    "idempotency_key": "uuid-xxx",                                          │
│    "params": {                                                              │
│      "offer_id": "xxx",                                                    │
│      "duration_hours": 24                                                  │
│    },                                                                       │
│    "constraints": {                                                         │
│      "max_cost": 50.0,                                                     │
│      "timeout_seconds": 300                                                │
│    }                                                                        │
│  }                                                                          │
│  Returns: {action_id, status, result_or_error}                             │
│                                                                             │
│  Agent Action Status:                                                       │
│  GET /api/v2/agents/actions/{action_id}                                    │
│  Returns: {status, progress, result, logs}                                 │
│                                                                             │
│  Agent WebSocket Channel:                                                   │
│  ws://host/ws/agents/{agent_id}/                                           │
│  Bidirectional communication for:                                          │
│  - Real-time action updates                                                │
│  - Price alerts                                                            │
│  - Rental health monitoring                                                │
│  - System notifications                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Kafka Topics for Inter-Service Communication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  KAFKA TOPICS (KRaft Mode - NO ZOOKEEPER)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Public Topics (consumed by multiple services):                             │
│  ├─► gpubroker.price-updates                                               │
│  │   Schema: {provider, offer_id, old_price, new_price, timestamp}         │
│  │   Consumers: Flink, Notification Service, Analytics                     │
│  │                                                                          │
│  ├─► gpubroker.provider-events                                             │
│  │   Schema: {provider, event_type, data, timestamp}                       │
│  │   Consumers: Health Monitor, Dashboard, Alerting                        │
│  │                                                                          │
│  └─► gpubroker.rental-events                                               │
│      Schema: {rental_id, user_id, event_type, data, timestamp}             │
│      Consumers: Billing, Notification, Analytics                           │
│                                                                             │
│  Internal Topics (service-to-service):                                      │
│  ├─► gpubroker.internal.kpi-requests                                       │
│  │   Schema: {request_id, metric_type, params, callback_topic}             │
│  │                                                                          │
│  ├─► gpubroker.internal.ai-recommendations                                 │
│  │   Schema: {request_id, user_id, requirements, recommendations}          │
│  │                                                                          │
│  └─► gpubroker.internal.billing-events                                     │
│      Schema: {event_type, rental_id, amount, currency, timestamp}          │
│                                                                             │
│  Agent Topics:                                                              │
│  ├─► gpubroker.agents.actions                                              │
│  │   Schema: {agent_id, action_id, action_type, params, status}            │
│  │                                                                          │
│  └─► gpubroker.agents.notifications                                        │
│      Schema: {agent_id, notification_type, data, timestamp}                │
│                                                                             │
│  Dead Letter Topics:                                                        │
│  ├─► gpubroker.dlq.webhooks                                                │
│  ├─► gpubroker.dlq.notifications                                           │
│  └─► gpubroker.dlq.agent-actions                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete API Endpoint Summary

### Public API (External)

| Method | Endpoint | Auth | Rate Limit | Description |
|--------|----------|------|------------|-------------|
| GET | /api/v2/providers | Optional | By plan | List GPU offers with filters |
| GET | /api/v2/providers/{id} | Optional | By plan | Get offer details |
| POST | /api/v2/providers/query | Required | By plan | Advanced query with criteria |
| POST | /api/v2/providers/decide | Required | By plan | TOPSIS/multi-criteria decision |
| GET | /api/v2/providers/ranking | Required | By plan | Get ranked offers |
| GET | /api/v2/providers/stream | Required | By plan | SSE price stream |
| GET | /api/v2/providers/health | None | None | Provider health status |
| POST | /api/v2/providers/config/integrations | Required | By plan | Save provider credentials |
| GET | /api/v2/providers/config/integrations | Required | By plan | List integrations |
| POST | /api/v2/rentals/provision | Required | By plan | Provision GPU rental |
| GET | /api/v2/rentals/{id} | Required | By plan | Get rental status |
| POST | /api/v2/rentals/{id}/scale | Required | By plan | Scale rental |
| DELETE | /api/v2/rentals/{id} | Required | By plan | Terminate rental |
| POST | /api/v2/alerts | Required | By plan | Create price alert |
| GET | /api/v2/alerts | Required | By plan | List alerts |
| POST | /api/v2/webhooks | Required | Enterprise | Register webhook |
| GET | /api/v2/analytics/price-history | Required | By plan | Historical prices |

### WebSocket Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| ws://host/ws/providers/ | Optional | Real-time price updates |
| ws://host/ws/providers/{provider}/ | Optional | Provider-specific updates |
| ws://host/ws/rentals/{rental_id}/ | Required | Rental status updates |
| ws://host/ws/agents/{agent_id}/ | Required | Agent communication |

### Internal API (Service-to-Service)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /internal/v1/providers/stats | Service | Provider statistics |
| GET | /internal/v1/providers/health-summary | Service | Health summary |
| POST | /internal/v1/providers/recommend | Service | AI recommendations |
| POST | /internal/v1/providers/compare | Service | Offer comparison |
| GET | /internal/v1/providers/pricing/{id} | Service | Current pricing |
| POST | /internal/v1/rentals/cost-estimate | Service | Cost estimation |
| POST | /internal/v1/auth/validate-token | Service | Token validation |
| POST | /internal/v1/notifications/price-alert | Service | Trigger notification |

### Agent API

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /api/v2/agents/register | Service | Register agent |
| GET | /api/v2/agents/capabilities | Agent | Discover capabilities |
| POST | /api/v2/agents/actions | Agent | Execute action |
| GET | /api/v2/agents/actions/{id} | Agent | Action status |
