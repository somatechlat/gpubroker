# Implementation Plan: Provider API Gateway

## Overview

This implementation plan transforms the Provider API Gateway design into actionable coding tasks. The gateway is the CORE of GPUBROKER, designed to handle millions of concurrent users with Apache Kafka (KRaft), Flink, and Airflow.

**Stack:**
- Django 5 + Django Ninja (REST API)
- Django Channels (WebSocket)
- Apache Kafka KRaft (NO ZooKeeper)
- Apache Flink (Stream Processing)
- Apache Airflow (NO Celery)
- Redis Cluster (Caching, Rate Limiting)
- PostgreSQL (Persistence)
- HashiCorp Vault (Credentials)

## Tasks

- [ ] 1. Core Infrastructure Setup
  - [ ] 1.1 Create multi-tier cache module with L2 in-memory and L1 Redis
    - Implement L2InMemoryCache with probabilistic early expiration (XFetch)
    - Implement MultiTierCache with L2→L1→fetch lookup order
    - Add Redis fallback when unavailable
    - _Requirements: 2.1, 2.2, 2.5, 2.6_

  - [ ] 1.2 Create Redis-backed sliding window rate limiter
    - Implement SlidingWindowRateLimiter using Redis sorted sets
    - Support plan tiers: Free=10, Pro=100, Enterprise=1000 RPS
    - Return HTTP 429 with Retry-After header
    - Identify users by JWT, API key, or IP address
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ] 1.3 Enhance circuit breaker with Prometheus metrics
    - Add failure rate threshold (50% over 10 requests)
    - Implement half-open state with 3 trial calls
    - Add Prometheus metrics: state, failures, successes, rejections
    - Add latency histogram per provider
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 1.4 Create weighted load balancer with health tracking
    - Implement weighted round-robin based on provider health
    - Reduce weight by 50% for slow providers (>2s)
    - Support provider-specific concurrency limits
    - Implement request queuing with backpressure
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 1.5 Write property tests for cache, rate limiter, circuit breaker
    - **Property 1: Cache lookup order (L2→L1→fetch)**
    - **Property 2: Cache TTL expiration**
    - **Property 3: Rate limit enforcement by plan**
    - **Property 4: Circuit breaker state machine**
    - **Validates: Requirements 2.2, 2.3, 4.1, 3.2**

- [ ] 2. Checkpoint - Core Infrastructure
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Vault Integration for Credentials
  - [ ] 3.1 Create Vault credential manager
    - Implement VaultCredentialManager with hvac client
    - Cache credentials with automatic renewal
    - Fallback to cached credentials when Vault unavailable (up to 1 hour)
    - Support per-user enterprise credentials
    - Never log API keys or sensitive data
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 3.2 Write property tests for Vault integration
    - **Property 18: Vault credential retrieval with fallback**
    - **Property 19: Credential security (no logging)**
    - **Validates: Requirements 9.1, 9.3, 9.4**

- [ ] 4. Apache Kafka Integration (KRaft Mode)
  - [ ] 4.1 Create Kafka producer client
    - Configure for KRaft mode (NO ZooKeeper)
    - Implement publish_price_update, publish_provider_event, publish_webhook_request
    - Use snappy compression and batching
    - Add delivery callbacks for confirmation
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ] 4.2 Create Kafka consumer client
    - Implement consume_loop with at-least-once delivery
    - Handle price changes, provider events, webhooks
    - Support local queue fallback when Kafka unavailable
    - _Requirements: 12.6_

  - [ ] 4.3 Create Kafka topic configuration
    - Define topics: price-updates, provider-events, webhooks, price-alerts
    - Configure partitions (12) and replication (3)
    - Add dead letter queue topics
    - _Requirements: 12.2, 12.3, 12.4_

  - [ ]* 4.4 Write property tests for Kafka integration
    - **Property 14: Kafka event delivery**
    - **Validates: Requirements 12.2, 12.5**

- [ ] 5. Checkpoint - Kafka Integration
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. WebSocket Gateway (Django Channels)
  - [ ] 6.1 Create WebSocket consumer for real-time updates
    - Implement ProviderGatewayConsumer with subscription channels
    - Support channels: price_updates, health_status, provider:{name}, gpu:{type}
    - Handle subscribe/unsubscribe messages
    - Implement ping/pong for connection health
    - _Requirements: 11.1, 11.2, 11.4, 11.5, 11.6, 11.7_

  - [ ] 6.2 Create WebSocket event handlers
    - Implement price_update, health_update, availability_update handlers
    - Broadcast to subscribed clients via channel layer
    - _Requirements: 11.3_

  - [ ] 6.3 Configure Django Channels routing
    - Add WebSocket URL patterns
    - Configure Redis channel layer
    - _Requirements: 11.1_

  - [ ]* 6.4 Write property tests for WebSocket
    - **Property 16: WebSocket real-time updates**
    - **Validates: Requirements 11.3**

- [ ] 7. Apache Flink Integration
  - [ ] 7.1 Create Flink SQL jobs for price change detection
    - Implement PriceChangeDetector (>5% threshold)
    - Implement AnomalyDetector (z-score > 3)
    - Implement RealTimeAggregator (1-minute tumbling windows)
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ] 7.2 Create Flink result consumer
    - Consume from gpubroker.price-changes topic
    - Push updates to WebSocket subscribers
    - _Requirements: 13.5, 13.6_

  - [ ]* 7.3 Write property tests for Flink integration
    - **Property 15: Flink price change detection**
    - **Validates: Requirements 13.2**

- [ ] 8. Checkpoint - Real-Time Pipeline
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Apache Airflow DAGs (NO CELERY)
  - [ ] 9.1 Create cache warming DAG
    - Schedule every 5 minutes
    - Warm cache for all providers in parallel
    - Store results in Redis
    - _Requirements: 10.1, 10.2_

  - [ ] 9.2 Create health check DAG
    - Schedule every minute
    - Check all provider health endpoints
    - Update load balancer health status
    - _Requirements: 10.3_

  - [ ] 9.3 Create data sync DAG
    - Schedule hourly
    - Sync provider offers to PostgreSQL
    - _Requirements: 10.4_

  - [ ] 9.4 Create webhook delivery DAG
    - Triggered by Kafka events
    - Retry with exponential backoff
    - Dead letter queue for failures
    - _Requirements: 10.5_

  - [ ]* 9.5 Write property tests for Airflow DAGs
    - **Property 17: Airflow DAG execution**
    - **Validates: Requirements 10.2**

- [ ] 10. Checkpoint - Background Tasks
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Enhanced Provider API Endpoints
  - [ ] 11.1 Update list_providers endpoint with new components
    - Integrate multi-tier cache
    - Integrate sliding window rate limiter
    - Integrate circuit breaker
    - Integrate load balancer
    - Add parallel provider fetching
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.1, 7.2_

  - [ ] 11.2 Create advanced query endpoint
    - POST /api/v2/providers/query with criteria
    - Support complex filters and constraints
    - _Requirements: 7.4_

  - [ ] 11.3 Create TOPSIS decision endpoint
    - POST /api/v2/providers/decide
    - Support multiple decision methods
    - _Requirements: 7.5_

  - [ ] 11.4 Create SSE streaming endpoint
    - GET /api/v2/providers/stream
    - Continuous price updates
    - _Requirements: 14.3_

  - [ ] 11.5 Create bulk query endpoint
    - POST /api/v2/providers/bulk/query
    - Batch queries for enterprise
    - _Requirements: 7.6_

  - [ ]* 11.6 Write property tests for API endpoints
    - **Property 11: Parallel provider fetching**
    - **Property 12: Response normalization**
    - **Property 13: Filter correctness**
    - **Validates: Requirements 1.3, 7.1, 7.4**

- [ ] 12. Checkpoint - API Endpoints
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Internal Service APIs
  - [ ] 13.1 Create KPI module integration endpoints
    - GET /internal/v1/providers/stats
    - GET /internal/v1/providers/health-summary
    - _Requirements: 15.1_

  - [ ] 13.2 Create AI Assistant integration endpoints
    - POST /internal/v1/providers/recommend
    - POST /internal/v1/providers/compare
    - _Requirements: 15.1_

  - [ ] 13.3 Create Billing module integration endpoints
    - GET /internal/v1/providers/pricing/{id}
    - POST /internal/v1/rentals/cost-estimate
    - _Requirements: 15.1_

  - [ ] 13.4 Create service token authentication
    - Validate service tokens
    - Scope permissions per service
    - _Requirements: 15.2_

  - [ ]* 13.5 Write integration tests for internal APIs
    - Test service-to-service authentication
    - Test circuit breakers for internal calls
    - _Requirements: 15.4_

- [ ] 14. Agent-to-Agent (A2A) Protocol
  - [ ] 14.1 Create agent registration endpoint
    - POST /api/v2/agents/register
    - Store agent capabilities and budget limits
    - _Requirements: 16.1, 16.2_

  - [ ] 14.2 Create agent capability discovery endpoint
    - GET /api/v2/agents/capabilities
    - Return supported actions and criteria
    - _Requirements: 16.3_

  - [ ] 14.3 Create agent action endpoints
    - POST /api/v2/agents/actions
    - GET /api/v2/agents/actions/{id}
    - Implement action queuing with priority
    - _Requirements: 16.4_

  - [ ] 14.4 Create agent WebSocket channel
    - ws://host/ws/agents/{agent_id}/
    - Bidirectional communication
    - _Requirements: 16.5_

  - [ ]* 14.5 Write integration tests for A2A protocol
    - Test agent registration and authentication
    - Test action execution and status tracking
    - _Requirements: 16.1, 16.4_

- [ ] 15. Checkpoint - Inter-Service Communication
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Rental Management APIs
  - [ ] 16.1 Create rental provision endpoint
    - POST /api/v2/rentals/provision
    - Call provider API with user credentials
    - Return connection details
    - _Requirements: Journey 2.8, Journey 4.4_

  - [ ] 16.2 Create rental status endpoint
    - GET /api/v2/rentals/{id}
    - Return rental health and utilization
    - _Requirements: Journey 4.5_

  - [ ] 16.3 Create rental scale endpoint
    - POST /api/v2/rentals/{id}/scale
    - Add/remove GPUs from rental
    - _Requirements: Journey 4.6_

  - [ ] 16.4 Create rental termination endpoint
    - DELETE /api/v2/rentals/{id}
    - Calculate final cost
    - _Requirements: Journey 4.7_

  - [ ]* 16.5 Write integration tests for rental APIs
    - Test full rental lifecycle
    - _Requirements: Journey 4_

- [ ] 17. Alert and Webhook APIs
  - [ ] 17.1 Create price alert endpoints
    - POST /api/v2/alerts
    - GET /api/v2/alerts
    - DELETE /api/v2/alerts/{id}
    - _Requirements: Journey 2.7_

  - [ ] 17.2 Create webhook registration endpoints
    - POST /api/v2/webhooks
    - GET /api/v2/webhooks
    - DELETE /api/v2/webhooks/{id}
    - _Requirements: Journey 3.2_

  - [ ]* 17.3 Write integration tests for alerts and webhooks
    - Test alert triggering via Flink
    - Test webhook delivery via Airflow
    - _Requirements: Journey 2.7, Journey 3.7_

- [ ] 18. Checkpoint - Full Feature Set
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 19. Health and Metrics Endpoints
  - [ ] 19.1 Create comprehensive health endpoint
    - GET /health with detailed provider status
    - Include Kafka, Flink, Airflow health
    - _Requirements: 6.4_

  - [ ] 19.2 Create Prometheus metrics endpoint
    - GET /metrics
    - Expose all gateway metrics
    - _Requirements: 6.1_

  - [ ] 19.3 Add OpenTelemetry tracing
    - Add trace IDs to all requests
    - Configure OTLP exporter
    - _Requirements: 6.5_

- [ ] 20. Docker Compose Configuration
  - [ ] 20.1 Create docker-compose.yml for development
    - Kafka KRaft (NO ZooKeeper)
    - Flink JobManager + TaskManager
    - Airflow Scheduler + Workers
    - Redis Cluster
    - PostgreSQL
    - Vault
    - _Requirements: All infrastructure_

  - [ ] 20.2 Create Kubernetes manifests for production
    - HPA for gateway pods (10-1000 replicas)
    - StatefulSets for Kafka, Redis, PostgreSQL
    - _Requirements: 8.1, 8.2_

- [ ] 21. Final Checkpoint - Complete System
  - Ensure all tests pass
  - Run full integration test suite on real infrastructure
  - Verify all user journeys work end-to-end
  - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional property-based tests
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- All testing on REAL infrastructure (no mocks except unit tests)
- NO CELERY - use Apache Airflow for all background tasks
- NO ZOOKEEPER - use Kafka KRaft mode
