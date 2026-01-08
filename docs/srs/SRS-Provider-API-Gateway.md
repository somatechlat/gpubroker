# Software Requirements Specification (SRS)
# GPUBROKER Provider API Gateway

**Document Version:** 1.0  
**Date:** 2024-12-29  
**Status:** Draft  
**Classification:** Internal  

---

## Document Control

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2024-12-29 | GPUBROKER Team | Initial SRS for Provider API Gateway |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Features and Requirements](#3-system-features-and-requirements)
4. [External Interface Requirements](#4-external-interface-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [System Architecture](#6-system-architecture)
7. [Data Requirements](#7-data-requirements)
8. [Security Requirements](#8-security-requirements)
9. [Appendices](#9-appendices)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) document describes the functional and non-functional requirements for the GPUBROKER Provider API Gateway system. This document is intended for:

- Software architects and developers
- Quality assurance engineers
- DevOps and infrastructure engineers
- Project managers and stakeholders

### 1.2 Scope

The Provider API Gateway is the core component of GPUBROKER that:

- Aggregates GPU pricing and availability data from 20+ cloud providers
- Handles millions of concurrent users with sub-100ms response times
- Provides real-time updates via WebSocket and Server-Sent Events
- Implements intelligent caching, circuit breakers, and rate limiting
- Uses Apache Kafka (KRaft), Flink, and Airflow for event processing

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| API | Application Programming Interface |
| CDN | Content Delivery Network |
| DAG | Directed Acyclic Graph (Airflow workflow) |
| GPU | Graphics Processing Unit |
| JWT | JSON Web Token |
| KRaft | Kafka Raft consensus protocol (replaces ZooKeeper) |
| L1 Cache | Level 1 cache (Redis distributed cache) |
| L2 Cache | Level 2 cache (in-memory per-instance cache) |
| PEE | Probabilistic Early Expiration (cache stampede prevention) |
| RPS | Requests Per Second |
| SLA | Service Level Agreement |
| SSE | Server-Sent Events |
| TTL | Time To Live |
| WebSocket | Full-duplex communication protocol |

### 1.4 References

| Document | Version | Description |
|----------|---------|-------------|
| Django 5 Documentation | 5.0 | Web framework documentation |
| Django Ninja Documentation | 1.0 | API framework documentation |
| Apache Kafka Documentation | 3.6 | Event streaming platform |
| Apache Flink Documentation | 1.18 | Stream processing framework |
| Apache Airflow Documentation | 2.8 | Workflow orchestration |
| HashiCorp Vault Documentation | 1.15 | Secrets management |

### 1.5 Overview

This document follows ISO/IEC/IEEE 29148:2018 structure for software requirements specifications.

---

## 2. Overall Description

### 2.1 Product Perspective

The Provider API Gateway is a subsystem of GPUBROKER that serves as the central nervous system for GPU pricing aggregation. It interfaces with:

- **External GPU Providers**: RunPod, Vast.ai, AWS, Azure, GCP, Lambda Labs, etc.
- **Frontend Applications**: Web dashboard, mobile apps, CLI tools
- **Internal Services**: KPI analytics, AI assistant, billing system
- **Infrastructure**: Kubernetes, Redis, PostgreSQL, Kafka, Flink, Airflow

### 2.2 Product Functions

| Function | Description |
|----------|-------------|
| F1: Provider Aggregation | Fetch and normalize GPU offers from 20+ providers |
| F2: Real-Time Updates | Push price changes via WebSocket/SSE |
| F3: Intelligent Caching | Multi-tier caching with stampede prevention |
| F4: Rate Limiting | Plan-based rate limiting (Free/Pro/Enterprise) |
| F5: Circuit Breaking | Fault tolerance for provider failures |
| F6: Load Balancing | Weighted distribution across providers |
| F7: Event Streaming | Kafka-based async communication |
| F8: Stream Processing | Flink-based real-time analytics |
| F9: Workflow Orchestration | Airflow-based background tasks |
| F10: Credential Management | Vault-based secure API key storage |

### 2.3 User Classes and Characteristics

| User Class | Description | Technical Level |
|------------|-------------|-----------------|
| Free Users | Anonymous or registered users with basic access | Low |
| Pro Users | Paid subscribers with higher rate limits | Medium |
| Enterprise Users | Business customers with custom integrations | High |
| API Developers | Third-party developers using GPUBROKER API | High |
| System Administrators | DevOps managing the infrastructure | Expert |

### 2.4 Operating Environment

| Component | Specification |
|-----------|---------------|
| Runtime | Python 3.11+, Django 5.0+ |
| Container | containerd, Kubernetes |
| Database | PostgreSQL 15+ (Patroni HA) |
| Cache | Redis 7+ (Cluster mode) |
| Message Queue | Apache Kafka 3.6+ (KRaft mode, NO ZooKeeper) |
| Stream Processing | Apache Flink 1.18+ |
| Workflow | Apache Airflow 2.8+ |
| Secrets | HashiCorp Vault 1.15+ |

### 2.5 Design and Implementation Constraints

| Constraint | Description |
|------------|-------------|
| C1 | Django 5 + Django Ninja ONLY (no FastAPI) |
| C2 | Django ORM ONLY (no SQLAlchemy) |
| C3 | Apache Airflow ONLY (NO Celery) |
| C4 | Apache Kafka KRaft mode (NO ZooKeeper) |
| C5 | All credentials in HashiCorp Vault |
| C6 | Stateless gateway instances |
| C7 | Real infrastructure testing (no mocks in integration tests) |

### 2.6 Assumptions and Dependencies

| ID | Assumption/Dependency |
|----|----------------------|
| A1 | Provider APIs remain stable and available |
| A2 | Kubernetes cluster has auto-scaling enabled |
| A3 | Redis cluster has sufficient memory for caching |
| A4 | Kafka cluster has sufficient throughput for events |
| A5 | Network latency to providers is < 500ms |


---

## 3. System Features and Requirements

### 3.1 High-Performance Request Handling

**Priority:** Critical  
**Risk:** High  

#### 3.1.1 Description

The gateway must handle millions of concurrent users with sub-100ms response times.

#### 3.1.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | THE Gateway SHALL handle at least 10,000 concurrent requests per second per instance | Critical |
| FR-1.2 | WHEN a cached response exists, THE Gateway SHALL return it within 10ms | Critical |
| FR-1.3 | WHEN fetching from providers, THE Gateway SHALL parallelize requests to all adapters | High |
| FR-1.4 | THE Gateway SHALL use async/await patterns throughout for non-blocking I/O | High |
| FR-1.5 | WHEN response time exceeds 5 seconds, THE Gateway SHALL timeout and return cached data or error | High |

### 3.2 Multi-Tier Caching Strategy

**Priority:** Critical  
**Risk:** Medium  

#### 3.2.1 Description

Intelligent caching reduces provider API calls and improves response times.

#### 3.2.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | THE Cache_Layer SHALL implement L1 (Redis) and L2 (in-memory) caching | Critical |
| FR-2.2 | WHEN a request arrives, THE Gateway SHALL check L2 cache first, then L1, then fetch from providers | Critical |
| FR-2.3 | THE Cache_Layer SHALL store provider responses with configurable TTL (default: 60s pricing, 300s static) | High |
| FR-2.4 | WHEN cache is invalidated, THE Gateway SHALL refresh data asynchronously without blocking requests | High |
| FR-2.5 | THE Cache_Layer SHALL implement cache stampede prevention using probabilistic early expiration | High |
| FR-2.6 | WHEN Redis is unavailable, THE Gateway SHALL fall back to L2 in-memory cache gracefully | Critical |

### 3.3 Circuit Breaker Pattern

**Priority:** High  
**Risk:** Medium  

#### 3.3.1 Description

Graceful handling of provider failures prevents cascading failures.

#### 3.3.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | THE Circuit_Breaker SHALL track failure rates per provider adapter | High |
| FR-3.2 | WHEN failure rate exceeds 50% over 10 requests, THE Circuit_Breaker SHALL open the circuit | High |
| FR-3.3 | WHILE circuit is open, THE Gateway SHALL return cached data or skip the provider | High |
| FR-3.4 | WHEN circuit is open for 30 seconds, THE Circuit_Breaker SHALL enter half-open state | Medium |
| FR-3.5 | WHEN a request succeeds in half-open state, THE Circuit_Breaker SHALL close the circuit | Medium |
| FR-3.6 | THE Circuit_Breaker SHALL emit Prometheus metrics for monitoring | Medium |

### 3.4 Rate Limiting by Plan Tier

**Priority:** High  
**Risk:** Low  

#### 3.4.1 Description

Different rate limits based on subscription tier enable fair monetization.

#### 3.4.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | THE Rate_Limiter SHALL enforce requests per second limits: Free=10, Pro=100, Enterprise=1000 | High |
| FR-4.2 | WHEN rate limit is exceeded, THE Gateway SHALL return HTTP 429 with Retry-After header | High |
| FR-4.3 | THE Rate_Limiter SHALL use sliding window algorithm for smooth rate limiting | High |
| FR-4.4 | THE Rate_Limiter SHALL identify users by JWT claims or API key | High |
| FR-4.5 | WHEN user is anonymous, THE Rate_Limiter SHALL apply Free tier limits by IP address | Medium |
| FR-4.6 | THE Rate_Limiter SHALL store counters in Redis for distributed rate limiting | High |

### 3.5 Provider Adapter Load Balancing

**Priority:** High  
**Risk:** Medium  

#### 3.5.1 Description

Intelligent load distribution prevents adapter bottlenecks.

#### 3.5.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | THE Load_Balancer SHALL distribute requests using weighted round-robin based on provider health | High |
| FR-5.2 | WHEN a provider is slow (>2s response), THE Load_Balancer SHALL reduce its weight by 50% | Medium |
| FR-5.3 | THE Load_Balancer SHALL support provider-specific concurrency limits | Medium |
| FR-5.4 | WHEN all providers are unhealthy, THE Gateway SHALL return cached data with warning | High |
| FR-5.5 | THE Load_Balancer SHALL implement request queuing with backpressure for burst handling | Medium |

### 3.6 Health Monitoring and Metrics

**Priority:** High  
**Risk:** Low  

#### 3.6.1 Description

Comprehensive health monitoring enables proactive issue resolution.

#### 3.6.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | THE Gateway SHALL expose Prometheus metrics for request latency, throughput, and error rates | High |
| FR-6.2 | THE Gateway SHALL perform periodic health checks on all provider adapters (every 30 seconds) | High |
| FR-6.3 | WHEN a provider health check fails, THE Gateway SHALL mark it as unhealthy | High |
| FR-6.4 | THE Gateway SHALL expose a /health endpoint with detailed provider status | High |
| FR-6.5 | THE Gateway SHALL log all requests with trace IDs for distributed tracing (OpenTelemetry) | Medium |

### 3.7 Request Aggregation and Normalization

**Priority:** Critical  
**Risk:** Medium  

#### 3.7.1 Description

Unified API aggregates data from all providers with standard schema.

#### 3.7.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-7.1 | THE Gateway SHALL normalize all provider responses into a standard Offer schema | Critical |
| FR-7.2 | WHEN fetching offers, THE Gateway SHALL query all healthy providers in parallel | High |
| FR-7.3 | THE Gateway SHALL merge and deduplicate offers from multiple providers | High |
| FR-7.4 | THE Gateway SHALL support filtering by GPU type, price range, region, and availability | High |
| FR-7.5 | THE Gateway SHALL support sorting by price, performance, or custom scoring (TOPSIS) | Medium |
| FR-7.6 | THE Gateway SHALL paginate results with cursor-based pagination for large datasets | Medium |

### 3.8 Horizontal Scalability

**Priority:** Critical  
**Risk:** Medium  

#### 3.8.1 Description

Gateway scales horizontally to handle traffic growth.

#### 3.8.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-8.1 | THE Gateway SHALL be stateless, storing all state in Redis/PostgreSQL | Critical |
| FR-8.2 | THE Gateway SHALL support running multiple instances behind a load balancer | Critical |
| FR-8.3 | WHEN a new instance starts, THE Gateway SHALL warm its cache from Redis | High |
| FR-8.4 | THE Gateway SHALL use connection pooling for database and Redis connections | High |
| FR-8.5 | THE Gateway SHALL support graceful shutdown with request draining | Medium |

### 3.9 Provider Credential Management

**Priority:** Critical  
**Risk:** High  

#### 3.9.1 Description

Secure credential storage in HashiCorp Vault.

#### 3.9.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-9.1 | THE Gateway SHALL fetch provider API keys from HashiCorp Vault | Critical |
| FR-9.2 | THE Gateway SHALL cache Vault tokens with automatic renewal | High |
| FR-9.3 | WHEN Vault is unavailable, THE Gateway SHALL use cached credentials for up to 1 hour | High |
| FR-9.4 | THE Gateway SHALL never log API keys or sensitive credentials | Critical |
| FR-9.5 | THE Gateway SHALL support per-user provider credentials for enterprise customers | Medium |

### 3.10 Apache Airflow Workflow Orchestration

**Priority:** High  
**Risk:** Medium  

#### 3.10.1 Description

Apache Airflow replaces Celery for all background task orchestration.

#### 3.10.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-10.1 | THE Gateway SHALL use Apache Airflow for all scheduled background tasks | High |
| FR-10.2 | THE Airflow_Scheduler SHALL run cache warming DAGs every 5 minutes | High |
| FR-10.3 | THE Airflow_Scheduler SHALL run health check DAGs every minute | High |
| FR-10.4 | THE Airflow_Scheduler SHALL run data sync DAGs hourly | Medium |
| FR-10.5 | WHEN a task fails, THE Airflow_Worker SHALL retry with exponential backoff | High |
| FR-10.6 | THE Gateway SHALL NOT use Celery for any background task execution | Critical |

### 3.11 WebSocket Real-Time Updates

**Priority:** High  
**Risk:** Medium  

#### 3.11.1 Description

Real-time updates via WebSocket (always available).

#### 3.11.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-11.1 | THE Gateway SHALL provide WebSocket endpoints via Django Channels | High |
| FR-11.2 | THE WebSocket_Gateway SHALL be always available as primary real-time channel | High |
| FR-11.3 | WHEN a price changes, THE Gateway SHALL push update to all subscribed WebSocket clients | High |
| FR-11.4 | THE WebSocket_Gateway SHALL support subscription channels: price_updates, health_status, availability, provider:{name}, gpu:{type}, region:{name} | High |
| FR-11.5 | WHEN a client connects, THE WebSocket_Gateway SHALL send connection confirmation | Medium |
| FR-11.6 | THE WebSocket_Gateway SHALL support ping/pong for connection health | Medium |

### 3.12 Apache Kafka Event Streaming (KRaft Mode)

**Priority:** High  
**Risk:** Medium  

#### 3.12.1 Description

Apache Kafka (KRaft mode, NO ZooKeeper) as event backbone.

#### 3.12.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-12.1 | THE Gateway SHALL use Apache Kafka in KRaft mode (NO ZooKeeper) | Critical |
| FR-12.2 | THE Gateway SHALL publish price update events to Kafka topic gpubroker.price-updates | High |
| FR-12.3 | THE Gateway SHALL publish provider events to Kafka topic gpubroker.provider-events | High |
| FR-12.4 | THE Gateway SHALL publish webhook requests to Kafka topic gpubroker.webhooks | Medium |
| FR-12.5 | WHEN publishing to Kafka, THE Gateway SHALL use snappy compression and batching | Medium |
| FR-12.6 | THE Kafka_Consumer SHALL process events with at-least-once delivery guarantee | High |

### 3.13 Apache Flink Real-Time Stream Processing

**Priority:** Medium  
**Risk:** Medium  

#### 3.13.1 Description

Apache Flink for real-time stream processing and analytics.

#### 3.13.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-13.1 | THE Flink_Job SHALL consume from gpubroker.price-updates topic | High |
| FR-13.2 | THE Flink_Job SHALL detect significant price changes (>5% threshold) | High |
| FR-13.3 | THE Flink_Job SHALL detect pricing anomalies using statistical analysis (z-score > 3) | Medium |
| FR-13.4 | THE Flink_Job SHALL compute real-time aggregations (avg price per GPU type, 1-minute windows) | Medium |
| FR-13.5 | THE Flink_Job SHALL publish alerts to gpubroker.price-alerts topic | Medium |
| FR-13.6 | WHEN Flink detects a significant change, THE Gateway SHALL notify WebSocket subscribers | High |


---

## 4. External Interface Requirements

### 4.1 User Interfaces

| Interface | Description |
|-----------|-------------|
| REST API | Django Ninja-based JSON API at /api/v2/providers |
| WebSocket | Django Channels at ws://host/ws/providers/ |
| SSE | Server-Sent Events at /api/v2/providers/stream |
| Metrics | Prometheus metrics at /metrics |
| Health | Health check at /health |

### 4.2 Hardware Interfaces

Not applicable - cloud-native deployment.

### 4.3 Software Interfaces

| System | Interface | Protocol |
|--------|-----------|----------|
| PostgreSQL | Django ORM | TCP/5432 |
| Redis | django-redis | TCP/6379 |
| Kafka | confluent-kafka | TCP/9092 |
| Flink | REST API | HTTP/8081 |
| Airflow | REST API | HTTP/8080 |
| Vault | hvac client | HTTP/8200 |
| Prometheus | /metrics endpoint | HTTP |
| OpenTelemetry | OTLP exporter | gRPC/4317 |

### 4.4 Communication Interfaces

| Protocol | Port | Description |
|----------|------|-------------|
| HTTP/HTTPS | 80/443 | REST API, SSE |
| WebSocket | 80/443 | Real-time updates |
| gRPC | 4317 | OpenTelemetry traces |
| TCP | 9092 | Kafka brokers |
| TCP | 5432 | PostgreSQL |
| TCP | 6379 | Redis |

---

## 5. Non-Functional Requirements

### 5.1 Performance Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-P1 | Response time (P50) | < 50ms |
| NFR-P2 | Response time (P99) | < 100ms |
| NFR-P3 | Throughput per instance | 10,000+ RPS |
| NFR-P4 | Global throughput | 1,000,000+ RPS |
| NFR-P5 | Concurrent connections | 10,000,000+ |
| NFR-P6 | Cache hit ratio | > 95% |
| NFR-P7 | WebSocket message latency | < 100ms |
| NFR-P8 | Kafka event processing latency | < 1s |

### 5.2 Safety Requirements

| ID | Requirement |
|----|-------------|
| NFR-S1 | System SHALL NOT expose sensitive credentials in logs or responses |
| NFR-S2 | System SHALL gracefully degrade when dependencies fail |
| NFR-S3 | System SHALL NOT lose data during failures (at-least-once delivery) |

### 5.3 Security Requirements

| ID | Requirement |
|----|-------------|
| NFR-SEC1 | All API endpoints SHALL require JWT authentication (except /health, /metrics) |
| NFR-SEC2 | All credentials SHALL be stored in HashiCorp Vault |
| NFR-SEC3 | All external communication SHALL use TLS 1.3 |
| NFR-SEC4 | Rate limiting SHALL prevent DDoS attacks |
| NFR-SEC5 | Input validation SHALL prevent injection attacks |
| NFR-SEC6 | CORS SHALL be configured to allow only trusted origins |

### 5.4 Software Quality Attributes

| Attribute | Requirement |
|-----------|-------------|
| Availability | 99.99% uptime (52 min downtime/year) |
| Reliability | MTBF > 720 hours |
| Maintainability | Modular architecture, comprehensive logging |
| Portability | Container-based, cloud-agnostic |
| Scalability | Horizontal scaling via Kubernetes HPA |
| Testability | 80%+ code coverage, property-based tests |

### 5.5 Business Rules

| ID | Rule |
|----|------|
| BR-1 | Free tier users limited to 10 RPS |
| BR-2 | Pro tier users limited to 100 RPS |
| BR-3 | Enterprise tier users limited to 1000 RPS |
| BR-4 | Cache TTL for pricing data: 60 seconds |
| BR-5 | Cache TTL for static data: 300 seconds |
| BR-6 | Circuit breaker opens at 50% failure rate |
| BR-7 | Circuit breaker reset timeout: 30 seconds |

---

## 6. System Architecture

### 6.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GPUBROKER PROVIDER API GATEWAY                       │
│                    Architecture for Millions of Concurrent Users             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        EDGE LAYER                                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ CloudFlare  │  │   Fastly    │  │  AWS Shield │  (CDN + DDoS)    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────▼───────────────────────────────────┐   │
│  │                     LOAD BALANCER LAYER                              │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  AWS ALB / nginx / HAProxy (Global + Regional)              │    │   │
│  │  │  - SSL termination                                          │    │   │
│  │  │  - Health checks                                            │    │   │
│  │  │  - Sticky sessions (WebSocket)                              │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────▼───────────────────────────────────┐   │
│  │                     APPLICATION LAYER (Kubernetes)                   │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  Django Gateway Pods (HPA: 10-1000 replicas)                 │   │   │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ... ┌────────┐  │   │   │
│  │  │  │  GW-1  │ │  GW-2  │ │  GW-3  │ │  GW-4  │     │  GW-N  │  │   │   │
│  │  │  │        │ │        │ │        │ │        │     │        │  │   │   │
│  │  │  │ Django │ │ Django │ │ Django │ │ Django │     │ Django │  │   │   │
│  │  │  │ Ninja  │ │ Ninja  │ │ Ninja  │ │ Ninja  │     │ Ninja  │  │   │   │
│  │  │  │Channels│ │Channels│ │Channels│ │Channels│     │Channels│  │   │   │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘     └────────┘  │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  L2 In-Memory Cache (per pod, 10K entries, PEE algorithm)    │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────▼───────────────────────────────────┐   │
│  │                     DATA LAYER                                       │   │
│  │                                                                      │   │
│  │  ┌────────────────────────┐  ┌────────────────────────┐             │   │
│  │  │  Redis Cluster (L1)    │  │  PostgreSQL (Patroni)  │             │   │
│  │  │  ┌──────┐ ┌──────┐     │  │  ┌────────┐ ┌────────┐ │             │   │
│  │  │  │Master│ │Master│     │  │  │Primary │ │Replica │ │             │   │
│  │  │  └──────┘ └──────┘     │  │  └────────┘ └────────┘ │             │   │
│  │  │  ┌──────┐ ┌──────┐     │  │  ┌────────┐ ┌────────┐ │             │   │
│  │  │  │Replica│ │Replica│   │  │  │Replica │ │Replica │ │             │   │
│  │  │  └──────┘ └──────┘     │  │  └────────┘ └────────┘ │             │   │
│  │  │  - Rate limit counters │  │  - GPU offers          │             │   │
│  │  │  - Session data        │  │  - Provider configs    │             │   │
│  │  │  - Cache data          │  │  - User preferences    │             │   │
│  │  │  - Pub/Sub channels    │  │  - Audit logs          │             │   │
│  │  └────────────────────────┘  └────────────────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────▼───────────────────────────────────┐   │
│  │                     EVENT STREAMING LAYER (Apache Stack)             │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  Apache Kafka Cluster (KRaft Mode - NO ZOOKEEPER)              │ │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │ │   │
│  │  │  │ Broker 1 │ │ Broker 2 │ │ Broker 3 │  (Combined mode)       │ │   │
│  │  │  │ +Ctrl    │ │ +Ctrl    │ │ +Ctrl    │                        │ │   │
│  │  │  └──────────┘ └──────────┘ └──────────┘                        │ │   │
│  │  │  Topics:                                                        │ │   │
│  │  │  - gpubroker.price-updates (partitions: 12, replication: 3)    │ │   │
│  │  │  - gpubroker.provider-events (partitions: 6, replication: 3)   │ │   │
│  │  │  - gpubroker.webhooks (partitions: 6, replication: 3)          │ │   │
│  │  │  - gpubroker.price-alerts (partitions: 6, replication: 3)      │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                    │                                 │   │
│  │  ┌────────────────────────────────▼───────────────────────────────┐ │   │
│  │  │  Apache Flink Cluster                                          │ │   │
│  │  │  ┌───────────┐  ┌─────────────┐  ┌─────────────┐               │ │   │
│  │  │  │JobManager │  │TaskManager 1│  │TaskManager N│               │ │   │
│  │  │  └───────────┘  └─────────────┘  └─────────────┘               │ │   │
│  │  │  Jobs:                                                          │ │   │
│  │  │  - PriceChangeDetector (detects >5% changes)                   │ │   │
│  │  │  - AnomalyDetector (z-score > 3)                               │ │   │
│  │  │  - RealTimeAggregator (1-min tumbling windows)                 │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  Apache Airflow (NO CELERY)                                    │ │   │
│  │  │  ┌───────────┐  ┌────────┐  ┌────────┐  ┌────────┐            │ │   │
│  │  │  │ Scheduler │  │Worker 1│  │Worker 2│  │Worker N│            │ │   │
│  │  │  └───────────┘  └────────┘  └────────┘  └────────┘            │ │   │
│  │  │  DAGs:                                                          │ │   │
│  │  │  - cache_warming (every 5 min)                                 │ │   │
│  │  │  - health_checks (every 1 min)                                 │ │   │
│  │  │  - data_sync (hourly)                                          │ │   │
│  │  │  - webhook_delivery (triggered)                                │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────▼───────────────────────────────────┐   │
│  │                     SECURITY LAYER                                   │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  HashiCorp Vault                                               │ │   │
│  │  │  - Provider API keys (RunPod, Vast.ai, AWS, etc.)             │ │   │
│  │  │  - Database credentials                                        │ │   │
│  │  │  - JWT signing keys                                            │ │   │
│  │  │  - Per-user enterprise credentials                             │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────▼───────────────────────────────────┐   │
│  │                     OBSERVABILITY LAYER                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │  Prometheus  │  │   Grafana    │  │    Loki      │               │   │
│  │  │  (metrics)   │  │ (dashboards) │  │   (logs)     │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  │  ┌──────────────┐  ┌──────────────┐                                 │   │
│  │  │    Tempo     │  │ OpenTelemetry│                                 │   │
│  │  │  (traces)    │  │  Collector   │                                 │   │
│  │  └──────────────┘  └──────────────┘                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Django Gateway Instance                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │   Django Ninja  │  │ Django Channels │  │   Prometheus    │         │
│  │   REST API      │  │   WebSocket     │  │   Metrics       │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│  ┌────────▼────────────────────▼────────────────────▼────────┐         │
│  │                    Request Handler                         │         │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │         │
│  │  │ Rate Limiter │  │   JWT Auth   │  │  Middleware  │     │         │
│  │  │ (Redis)      │  │  (Vault)     │  │  (Logging)   │     │         │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │         │
│  └────────────────────────────┬──────────────────────────────┘         │
│                               │                                         │
│  ┌────────────────────────────▼──────────────────────────────┐         │
│  │                    Business Logic                          │         │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │         │
│  │  │ Multi-Tier   │  │   Circuit    │  │    Load      │     │         │
│  │  │   Cache      │  │   Breaker    │  │  Balancer    │     │         │
│  │  │ (L2→L1)      │  │  (per prov)  │  │ (weighted)   │     │         │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │         │
│  └────────────────────────────┬──────────────────────────────┘         │
│                               │                                         │
│  ┌────────────────────────────▼──────────────────────────────┐         │
│  │                    Provider Adapters                       │         │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │         │
│  │  │ RunPod │ │Vast.ai │ │  AWS   │ │ Azure  │ │  GCP   │   │         │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │         │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │         │
│  │  │Lambda  │ │Paper-  │ │  Groq  │ │Replicate│ │Deep-  │   │         │
│  │  │Labs    │ │space   │ │        │ │        │ │Infra  │   │         │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │         │
│  └────────────────────────────┬──────────────────────────────┘         │
│                               │                                         │
│  ┌────────────────────────────▼──────────────────────────────┐         │
│  │                    Event Publishing                        │         │
│  │  ┌──────────────────────────────────────────────────────┐ │         │
│  │  │  Kafka Producer (price-updates, provider-events)     │ │         │
│  │  └──────────────────────────────────────────────────────┘ │         │
│  └───────────────────────────────────────────────────────────┘         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```


---

## 7. Data Requirements

### 7.1 Data Models

#### 7.1.1 GPU Offer Schema

```json
{
  "id": "string (UUID)",
  "provider": "string (provider name)",
  "name": "string (offer name)",
  "gpu_type": "string (e.g., RTX 4090, A100)",
  "gpu_count": "integer",
  "gpu_memory_gb": "integer",
  "vcpus": "integer",
  "ram_gb": "integer",
  "storage_gb": "integer",
  "price_per_hour": "decimal",
  "spot_price": "decimal (nullable)",
  "currency": "string (default: USD)",
  "availability_status": "enum (available, limited, unavailable)",
  "region": "string",
  "compliance_tags": "array of strings",
  "last_updated": "datetime"
}
```

#### 7.1.2 Provider Schema

```json
{
  "id": "string (UUID)",
  "name": "string (unique)",
  "display_name": "string",
  "api_base_url": "string (URL)",
  "is_active": "boolean",
  "health_status": "enum (healthy, degraded, unhealthy)",
  "last_health_check": "datetime",
  "rate_limit_per_minute": "integer"
}
```

### 7.2 Data Flow

```
Provider APIs → Adapters → Normalization → Cache → Response
                    ↓
              Kafka Topics → Flink Processing → Alerts
                    ↓
              PostgreSQL (persistence)
```

### 7.3 Data Retention

| Data Type | Retention Period |
|-----------|------------------|
| GPU Offers | 30 days |
| Health Checks | 7 days |
| Audit Logs | 90 days |
| Kafka Events | 7 days |
| Cache Data | TTL-based (60-300s) |

---

## 8. Security Requirements

### 8.1 Authentication

| Method | Use Case |
|--------|----------|
| JWT (RS256) | API authentication |
| API Key | Machine-to-machine |
| WebSocket Token | Real-time connections |

### 8.2 Authorization

| Role | Permissions |
|------|-------------|
| Anonymous | Read public offers (rate limited) |
| Free User | Read offers, basic filters |
| Pro User | Full API access, higher limits |
| Enterprise | Custom integrations, webhooks |
| Admin | Full system access |

### 8.3 Data Protection

| Requirement | Implementation |
|-------------|----------------|
| Encryption at rest | PostgreSQL TDE, Redis encryption |
| Encryption in transit | TLS 1.3 everywhere |
| Secrets management | HashiCorp Vault |
| PII handling | No PII stored in logs |

---

## 9. Appendices

### 9.1 Kafka KRaft Configuration

```properties
# server.properties for KRaft mode (NO ZOOKEEPER)
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@kafka1:9093,2@kafka2:9093,3@kafka3:9093
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
inter.broker.listener.name=PLAINTEXT
controller.listener.names=CONTROLLER
log.dirs=/var/kafka-logs
num.partitions=12
default.replication.factor=3
min.insync.replicas=2
```

### 9.2 Minikube + Tilt (Development)

Local development is standardized on Minikube (vfkit) with Tilt orchestration.
See `docs/infrastructure/deployment-setup.md` for the workflow and required
environment variables.

### 9.3 Traceability Matrix

| Requirement | Design Component | Test Case |
|-------------|------------------|-----------|
| FR-1.1 | Gateway async handlers | TC-PERF-001 |
| FR-2.1 | MultiTierCache class | TC-CACHE-001 |
| FR-3.1 | AsyncCircuitBreaker | TC-CB-001 |
| FR-4.1 | SlidingWindowRateLimiter | TC-RL-001 |
| FR-5.1 | WeightedLoadBalancer | TC-LB-001 |
| FR-10.1 | Airflow DAGs | TC-AF-001 |
| FR-11.1 | ProviderGatewayConsumer | TC-WS-001 |
| FR-12.1 | KafkaProducerClient | TC-KF-001 |
| FR-13.1 | Flink SQL jobs | TC-FL-001 |

---

## Document Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Author | | | |
| Technical Lead | | | |
| Architect | | | |
| QA Lead | | | |
| Product Owner | | | |

---

*End of Document*


---

## Addendum A: User Journey Stories

### A.1 Journey 1: Anonymous User Browsing GPU Offers

| Step | Action | API Call | Response |
|------|--------|----------|----------|
| 1 | Visit website | WebSocket connect | Connection established |
| 2 | View offers | GET /api/v2/providers | Paginated offer list |
| 3 | Apply filters | GET /api/v2/providers?gpu=A100 | Filtered results |
| 4 | Receive update | WebSocket message | Price update notification |
| 5 | View details | GET /api/v2/providers/{id} | Offer details |
| 6 | Want to rent | Redirect | Login/register prompt |

### A.2 Journey 2: Registered User with Pro Plan

| Step | Action | API Call | Response |
|------|--------|----------|----------|
| 1 | Login | POST /api/v2/auth/login | JWT tokens |
| 2 | Connect WebSocket | ws://host/ws/providers/?token=jwt | Authenticated connection |
| 3 | Subscribe | WebSocket: {type: subscribe} | Subscription confirmed |
| 4 | Browse offers | GET /api/v2/providers | Higher rate limit |
| 5 | TOPSIS ranking | GET /api/v2/providers/ranking | Ranked offers |
| 6 | Save favorite | POST /api/v2/users/favorites | Saved |
| 7 | Set alert | POST /api/v2/alerts | Alert created |
| 8 | Rent GPU | POST /api/v2/rentals/provision | Rental confirmation |

### A.3 Journey 3: Enterprise User with Custom Integration

| Step | Action | API Call | Response |
|------|--------|----------|----------|
| 1 | Configure credentials | POST /api/v2/providers/config/integrations | Stored in Vault |
| 2 | Setup webhook | POST /api/v2/webhooks | Webhook registered |
| 3 | High-rate API access | GET /api/v2/providers | 1000 RPS limit |
| 4 | ML pipeline stream | GET /api/v2/providers/stream | SSE stream |
| 5 | Bulk query | POST /api/v2/providers/bulk/query | Batch results |
| 6 | Analytics | GET /api/v2/analytics/price-history | Historical data |
| 7 | Receive webhook | Kafka → Airflow → Enterprise | Event delivered |

### A.4 Journey 4: AI Agent Autonomous GPU Procurement

| Step | Action | API Call | Response |
|------|--------|----------|----------|
| 1 | Authenticate | POST /api/v2/auth/service-token | Service JWT |
| 2 | Query GPUs | POST /api/v2/providers/query | Matching offers |
| 3 | Decision API | POST /api/v2/providers/decide | Ranked selection |
| 4 | Provision | POST /api/v2/rentals/provision | Connection details |
| 5 | Monitor | WebSocket subscription | Health updates |
| 6 | Scale | POST /api/v2/rentals/{id}/scale | Additional GPUs |
| 7 | Terminate | DELETE /api/v2/rentals/{id} | Final cost |

---

## Addendum B: Inter-Module Communication

### B.1 Internal API Endpoints

| Module | Endpoint | Method | Description |
|--------|----------|--------|-------------|
| KPI | /internal/v1/providers/stats | GET | Provider statistics |
| KPI | /internal/v1/providers/health-summary | GET | Health summary |
| AI | /internal/v1/providers/recommend | POST | AI recommendations |
| AI | /internal/v1/providers/explain | POST | Offer explanation |
| AI | /internal/v1/providers/compare | POST | Comparison matrix |
| Billing | /internal/v1/providers/pricing/{id} | GET | Current pricing |
| Billing | /internal/v1/rentals/cost-estimate | POST | Cost estimation |
| Billing | /internal/v1/rentals/finalize | POST | Final cost |
| Auth | /internal/v1/auth/validate-token | POST | Token validation |
| Notify | /internal/v1/notifications/price-alert | POST | Trigger alert |

### B.2 Kafka Topics

| Topic | Schema | Consumers |
|-------|--------|-----------|
| gpubroker.price-updates | {provider, offer_id, old_price, new_price} | Flink, Notifications |
| gpubroker.provider-events | {provider, event_type, data} | Health Monitor |
| gpubroker.rental-events | {rental_id, user_id, event_type} | Billing, Analytics |
| gpubroker.agents.actions | {agent_id, action_id, action_type} | Agent Processor |
| gpubroker.dlq.* | Dead letter queues | Error handling |

### B.3 Agent Communication Protocol

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v2/agents/register | POST | Register agent |
| /api/v2/agents/capabilities | GET | Discover capabilities |
| /api/v2/agents/actions | POST | Execute action |
| /api/v2/agents/actions/{id} | GET | Action status |
| ws://host/ws/agents/{id}/ | WebSocket | Real-time communication |

---

*End of Addendum*
