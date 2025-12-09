# Design Document: GPUBROKER Enterprise SaaS Platform

## Overview

GPUBROKER is an AI-First enterprise SaaS platform for GPU and cloud inference service discovery, cost optimization, and one-click provisioning. This design document specifies the technical architecture, components, data models, and implementation approach for a system that:

- Aggregates 23+ GPU providers into a unified marketplace
- Provides real-time price feeds via Kafka and WebSocket
- Delivers AI-powered recommendations through proven algorithms (TOPSIS, ALS, Content-Based)
- Processes natural language workload requests ("I need to process 10 AI images for 1 hour")
- Routes ALL mathematical calculations through a centralized Math Core (GPUMathBroker)
- Supports thousands of transactions per minute with sub-200ms latency
- Implements zero-trust security, chaos engineering, and self-healing infrastructure

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              GPUBROKER PLATFORM                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         PRESENTATION LAYER                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │  Next.js    │  │  WebSocket  │  │   Admin     │  │  AI Chat Panel  │  │   │
│  │  │  Frontend   │  │   Client    │  │   Console   │  │  (Always On)    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│                              ┌───────▼───────┐                                   │
│                              │  API Gateway  │ (Kong/Traefik)                    │
│                              │  + WAF + Rate │                                   │
│                              │    Limiter    │                                   │
│                              └───────┬───────┘                                   │
│                                      │                                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         SERVICE MESH (Istio)                              │   │
│  │                              mTLS + Observability                         │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         APPLICATION SERVICES                              │   │
│  │                                                                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │    Auth     │  │  Provider   │  │   Booking   │  │    Billing      │  │   │
│  │  │   Service   │  │   Service   │  │   Service   │  │    Service      │  │   │
│  │  │ (Keycloak)  │  │ (Adapters)  │  │ (Temporal)  │  │  (Kill Bill)    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  │                                                                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │     AI      │  │    Admin    │  │ Compliance  │  │   Notification  │  │   │
│  │  │  Assistant  │  │   Service   │  │   Service   │  │    Service      │  │   │
│  │  │ (LangChain) │  │(React-Admin)│  │   (OPA)     │  │   (Email/WS)    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  │                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    MATH CORE (GPUMathBroker)                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │    KPI      │  │   TOPSIS    │  │     ALS     │  │    Workload     │  │   │
│  │  │ Calculator  │  │   Engine    │  │ Recommender │  │    Mapper       │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │   Price     │  │   Anomaly   │  │  Content    │  │      GPU        │  │   │
│  │  │ Predictor   │  │  Detector   │  │  Similarity │  │   Benchmarks    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA & MESSAGING LAYER                            │   │
│  │                                                                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │ PostgreSQL  │  │ ClickHouse  │  │    Redis    │  │     Kafka       │  │   │
│  │  │   (OLTP)    │  │   (OLAP)    │  │   Cluster   │  │   (Events)      │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  │                                                                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │   Vault     │  │  Temporal   │  │ Meilisearch │  │     MinIO       │  │   │
│  │  │  (Secrets)  │  │ (Workflows) │  │  (Search)   │  │   (Objects)     │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  │                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         OBSERVABILITY LAYER                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │ Prometheus  │  │   Grafana   │  │    Loki     │  │     Tempo       │  │   │
│  │  │  (Metrics)  │  │(Dashboards) │  │   (Logs)    │  │   (Traces)      │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Service Communication Patterns

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMMUNICATION PATTERNS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SYNCHRONOUS (User-Facing, Latency-Critical):                   │
│  ┌──────────┐  REST/gRPC  ┌──────────┐                          │
│  │ Frontend │ ──────────► │ Services │  < 200ms                 │
│  └──────────┘             └──────────┘                          │
│                                                                  │
│  ASYNCHRONOUS (Background, Eventually Consistent):              │
│  ┌──────────┐   Kafka    ┌──────────┐                           │
│  │ Producer │ ─────────► │ Consumer │  price_updates            │
│  └──────────┘            └──────────┘  booking_events           │
│                                        audit_events             │
│                                                                  │
│  REAL-TIME (Live Updates):                                      │
│  ┌──────────┐  WebSocket ┌──────────┐                           │
│  │  Client  │ ◄────────► │ Gateway  │  < 50ms                   │
│  └──────────┘            └──────────┘                           │
│                                                                  │
│  WORKFLOW (Long-Running, Saga):                                 │
│  ┌──────────┐  Temporal  ┌──────────┐                           │
│  │ Booking  │ ─────────► │ Workflow │  with compensation        │
│  └──────────┘            └──────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. API Gateway (Kong/Traefik)

**Purpose:** Single entry point for all external traffic with security, rate limiting, and routing.

**Interfaces:**
- `POST /auth/*` → Auth Service
- `GET/POST /providers/*` → Provider Service
- `POST /ai/*` → AI Assistant Service
- `GET/POST /math/*` → Math Core Service
- `GET/POST /bookings/*` → Booking Service
- `GET/POST /admin/*` → Admin Service

**Configuration:**
```yaml
rate_limiting:
  default: 100 req/s per user
  burst: 150 req/s
  by_plan:
    free: 10 req/s
    pro: 100 req/s
    enterprise: 1000 req/s

security:
  waf: enabled
  cors: configured per origin
  jwt_validation: required
  request_signing: optional (enterprise)
```

### 2. Auth Service (Keycloak + Custom)

**Purpose:** Authentication, authorization, MFA, and session management.

**Interfaces:**
```
POST /auth/login          → { access_token, refresh_token, expires_in }
POST /auth/register       → { user_id, verification_required }
POST /auth/refresh        → { access_token, refresh_token }
POST /auth/logout         → { success }
POST /auth/mfa/enroll     → { secret, qr_code_url }
POST /auth/mfa/verify     → { success }
GET  /auth/me             → { user_id, email, roles, tenant_id }
```

**Security Features:**
- JWT with RS256 signing (asymmetric)
- Token binding to client fingerprint
- Refresh token rotation
- Session revocation on suspicious activity

### 3. Provider Service

**Purpose:** Aggregate, normalize, and serve GPU offerings from all providers.

**Interfaces:**
```
GET  /providers                    → { total, items[], warnings[] }
GET  /providers/{id}               → ProviderOffer
GET  /providers/export             → CSV/JSON file
POST /providers/search             → { total, items[] } (advanced search)
GET  /providers/health             → { provider_statuses[] }
POST /config/integrations          → { status, provider }
GET  /config/integrations          → IntegrationStatus[]
```

**Adapter Pattern:**
```python
class BaseProviderAdapter(ABC):
    PROVIDER_NAME: str
    BASE_URL: str
    
    @abstractmethod
    async def get_offers(self, auth_token: str) -> List[ProviderOffer]
    
    @abstractmethod
    async def validate_credentials(self, credentials: Dict) -> bool
    
    @abstractmethod
    async def book_instance(self, offer_id: str, duration: int) -> BookingResult
```

### 4. Math Core Service (GPUMathBroker)

**Purpose:** Centralized mathematical calculations, algorithms, and GPU benchmarks.

**Interfaces:**
```
# KPI Calculations
POST /math/cost-per-token         → { cost_per_token, confidence }
POST /math/cost-per-gflop         → { cost_per_gflop, confidence }
POST /math/efficiency-score       → { score, breakdown }

# Recommendation Algorithms
POST /math/topsis                  → { rankings[], scores[], ideal, anti_ideal }
POST /math/collaborative-filter   → { recommendations[], similarity_scores[] }
POST /math/content-similarity     → { matches[], cosine_scores[] }
POST /math/ensemble-recommend     → { final_rankings[], algorithm_weights }

# Workload Mapping
POST /math/estimate-workload      → { gpu_requirements, estimated_cost, duration }
POST /math/map-workload-to-gpu    → { recommended_gpus[], confidence }

# Price Analysis
POST /math/predict-price          → { predicted_price, confidence_interval }
POST /math/detect-anomaly         → { is_anomaly, z_score, details }

# Benchmarks
GET  /math/benchmarks/{gpu_type}  → GPUBenchmark
PUT  /math/benchmarks/{gpu_type}  → { updated } (admin only)
```

**Algorithm Specifications:**

```python
# TOPSIS Implementation
class TOPSISEngine:
    def calculate(self, decision_matrix: np.ndarray, weights: List[float], 
                  criteria_types: List[str]) -> TOPSISResult:
        """
        1. Normalize matrix using vector normalization: r_ij = x_ij / sqrt(sum(x_ij^2))
        2. Apply weights: v_ij = w_j * r_ij
        3. Determine ideal (A+) and anti-ideal (A-) solutions
        4. Calculate separation: S+ = sqrt(sum((v_ij - v_j+)^2))
        5. Calculate relative closeness: C_i = S_i- / (S_i+ + S_i-)
        6. Rank by C_i descending
        """
        pass

# ALS Collaborative Filtering
class ALSRecommender:
    def __init__(self, factors: int = 50, regularization: float = 0.1, 
                 iterations: int = 15):
        self.factors = factors
        self.regularization = regularization
        self.iterations = iterations
    
    def fit(self, user_item_matrix: sparse.csr_matrix) -> None:
        """Alternating Least Squares with implicit feedback"""
        pass
    
    def recommend(self, user_id: str, n: int = 5) -> List[Recommendation]:
        pass
```

### 5. AI Assistant Service

**Purpose:** Natural language interface for workload requests and recommendations.

**Interfaces:**
```
POST /ai/chat                     → { response, recommendations[], context_id }
POST /ai/parse-workload           → { workload_type, parameters, confidence }
POST /ai/recommend                → { recommendations[], explanation }
GET  /ai/templates                → WorkloadTemplate[]
POST /ai/feedback                 → { recorded }
GET  /ai/context/{session_id}     → ConversationContext
```

**LangChain Pipeline:**
```python
class GPUBrokerAIAssistant:
    def __init__(self):
        self.llm = Ollama(model="mistral:7b")
        self.memory = ConversationBufferWindowMemory(k=10)
        self.tools = [
            MathCoreTool(),
            ProviderSearchTool(),
            RecommendationTool(),
            BookingTool()
        ]
        self.agent = create_react_agent(self.llm, self.tools)
    
    async def process_message(self, message: str, context: Dict) -> AIResponse:
        # 1. Parse intent
        # 2. Extract workload parameters
        # 3. Call Math Core for calculations
        # 4. Get recommendations
        # 5. Format conversational response
        pass
```

### 6. Booking Service (Temporal Workflows)

**Purpose:** Manage GPU instance reservations with saga pattern for reliability.

**Interfaces:**
```
POST /bookings                    → { booking_id, status }
GET  /bookings/{id}               → Booking
PUT  /bookings/{id}/cancel        → { status }
GET  /bookings/user/{user_id}     → Booking[]
POST /bookings/{id}/extend        → { new_end_time, additional_cost }
```

**Temporal Workflow:**
```python
@workflow.defn
class BookingWorkflow:
    @workflow.run
    async def run(self, booking_request: BookingRequest) -> BookingResult:
        # 1. Validate offer availability
        # 2. Reserve with provider (with compensation)
        # 3. Create billing record
        # 4. Send confirmation notification
        # 5. Schedule usage tracking
        pass
    
    @workflow.signal
    async def cancel(self):
        # Trigger compensation activities
        pass
```

### 7. WebSocket Gateway

**Purpose:** Real-time price updates and notifications to connected clients.

**Protocol:**
```
Client → Server:
  { type: "subscribe", channels: ["price_updates", "user_notifications"] }
  { type: "unsubscribe", channels: ["price_updates"] }
  { type: "ping" }

Server → Client:
  { type: "price_update", data: { offer_id, old_price, new_price, timestamp } }
  { type: "notification", data: { type, message, action_url } }
  { type: "pong" }
```

## Data Models

### Core Entities

```sql
-- Users and Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    tenant_id UUID REFERENCES tenants(id),
    role VARCHAR(50) DEFAULT 'user',
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Multi-tenancy
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    api_calls_limit INTEGER DEFAULT 100,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Providers
CREATE TABLE providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    api_base_url VARCHAR(500) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    reliability_score DECIMAL(3,2) DEFAULT 0.5,
    last_sync_at TIMESTAMPTZ,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- GPU Offers (Normalized)
CREATE TABLE gpu_offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES providers(id),
    external_id VARCHAR(255) NOT NULL,
    gpu_type VARCHAR(100) NOT NULL,
    gpu_memory_gb INTEGER NOT NULL,
    cpu_cores INTEGER,
    ram_gb INTEGER,
    storage_gb INTEGER,
    price_per_hour DECIMAL(10,4) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    region VARCHAR(50) NOT NULL,
    availability_status VARCHAR(20) DEFAULT 'available',
    compliance_tags TEXT[] DEFAULT '{}',
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider_id, external_id)
);

-- GPU Benchmarks (Math Core Reference Data)
CREATE TABLE gpu_benchmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gpu_model VARCHAR(100) UNIQUE NOT NULL,
    tflops_fp32 DECIMAL(10,2),
    tflops_fp16 DECIMAL(10,2),
    tflops_int8 DECIMAL(10,2),
    memory_bandwidth_gbps DECIMAL(10,2),
    vram_gb INTEGER,
    tokens_per_second_7b INTEGER,
    tokens_per_second_13b INTEGER,
    tokens_per_second_70b INTEGER,
    image_gen_per_minute INTEGER,
    source VARCHAR(255),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Price History (Time-Series in ClickHouse)
CREATE TABLE price_history (
    offer_id UUID,
    price_per_hour DECIMAL(10,4),
    availability_status VARCHAR(20),
    recorded_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (offer_id, recorded_at);

-- Bookings
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    offer_id UUID REFERENCES gpu_offers(id),
    provider_booking_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    total_cost DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Conversation History
CREATE TABLE ai_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(255) NOT NULL,
    messages JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Recommendation Feedback (for ML training)
CREATE TABLE recommendation_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    recommendation_id VARCHAR(255),
    offer_id UUID REFERENCES gpu_offers(id),
    was_booked BOOLEAN,
    explicit_feedback VARCHAR(20), -- 'positive', 'negative', null
    position_in_list INTEGER,
    algorithm_used VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log (Immutable with Hash Chain)
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    previous_hash VARCHAR(64),
    current_hash VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Kafka Topics

```
price_updates:
  key: provider_id
  value: { offer_id, old_price, new_price, timestamp }
  partitions: 12
  retention: 7 days

booking_events:
  key: booking_id
  value: { event_type, booking_id, user_id, details, timestamp }
  partitions: 6
  retention: 30 days

audit_events:
  key: tenant_id
  value: { action, user_id, resource, details, timestamp }
  partitions: 6
  retention: 365 days

ai_interactions:
  key: user_id
  value: { session_id, message, response, recommendations, timestamp }
  partitions: 6
  retention: 90 days
```

### Redis Cache Structure

```
# Provider offers cache (TTL: 60s)
providers:list:{hash(filters)} → JSON { total, items[] }

# Individual offer cache (TTL: 300s)
offer:{offer_id} → JSON ProviderOffer

# User session (TTL: 15min)
session:{user_id} → JSON { token, roles, tenant_id }

# AI conversation context (TTL: 1h)
ai:context:{session_id} → JSON { messages[], filters, recommendations[] }

# Presets cache (TTL: 1h)
presets:{preset_name} → JSON { offers[], generated_at }

# Rate limiting (sliding window)
ratelimit:{user_id}:{window} → count
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Authentication Token Validity
*For any* valid user credentials, when login is performed, the returned JWT SHALL decode successfully with the correct user_id, roles, and non-expired timestamp.
**Validates: Requirements 1.1, 1.3**

### Property 2: Provider Offer Normalization Consistency
*For any* raw provider API response, when normalized through an adapter, the resulting ProviderOffer SHALL contain all required fields (provider, region, instance_type, price_per_hour, availability) with valid data types.
**Validates: Requirements 2.2, 2.5**

### Property 3: Price History Append-Only Integrity
*For any* price update event, when recorded to price_history, the record SHALL be immutable and the offer_id SHALL reference a valid gpu_offers entry.
**Validates: Requirements 2.3, 3.1**

### Property 4: Filter Query Correctness
*For any* filter combination (gpu_type, region, max_price), the returned offers SHALL all satisfy every specified filter criterion.
**Validates: Requirements 4.1, 4.2**

### Property 5: Pagination Consistency
*For any* paginated query with page P and per_page N, the union of all pages SHALL equal the total result set with no duplicates and no missing items.
**Validates: Requirements 4.6**

### Property 6: Math Core Cost-Per-Token Calculation
*For any* GPU type with known benchmark data, the cost_per_token calculation SHALL equal: price_per_hour / (tokens_per_second * 3600) with IEEE 754 double precision.
**Validates: Requirements 5.1, 21.1, 33.3**

### Property 7: TOPSIS Ranking Determinism
*For any* decision matrix and weight vector, repeated TOPSIS calculations SHALL produce identical rankings (deterministic output).
**Validates: Requirements 7.1, 33.1**

### Property 8: TOPSIS Ideal Solution Correctness
*For any* TOPSIS calculation, the ideal solution SHALL contain the maximum value for benefit criteria and minimum value for cost criteria from the normalized weighted matrix.
**Validates: Requirements 7.1**

### Property 9: Collaborative Filtering Matrix Factorization Convergence
*For any* user-item matrix, ALS training SHALL reduce reconstruction error monotonically until convergence tolerance (1e-6) is reached.
**Validates: Requirements 7.2, 33.2**

### Property 10: Content-Based Similarity Bounds
*For any* two feature vectors, cosine similarity SHALL be in range [-1, 1] and identical vectors SHALL produce similarity = 1.0.
**Validates: Requirements 7.3**

### Property 11: Ensemble Recommendation Weight Sum
*For any* ensemble recommendation, the algorithm weights SHALL sum to 1.0 (TOPSIS 0.4 + Collaborative 0.3 + Content-Based 0.3 = 1.0).
**Validates: Requirements 7.4**

### Property 12: Natural Language Workload Extraction
*For any* workload request containing quantity and duration, the AI parser SHALL extract numeric values for quantity and duration_hours with >90% accuracy on test set.
**Validates: Requirements 22.1**

### Property 13: Workload-to-GPU Mapping Completeness
*For any* supported workload type (image_generation, llm_inference, training), the mapping engine SHALL return at least one recommended GPU tier.
**Validates: Requirements 22.2, 22.3, 22.4, 27.1, 27.2, 27.3**

### Property 14: AI Response Time Bound
*For any* AI chat request, the end-to-end response time SHALL be ≤2000ms for 95th percentile of requests.
**Validates: Requirements 8.1, 32.1**

### Property 15: Circuit Breaker State Transitions
*For any* circuit breaker, state transitions SHALL follow: CLOSED → OPEN (after threshold failures) → HALF_OPEN (after timeout) → CLOSED (after success) or OPEN (after failure).
**Validates: Requirements 35.1**

### Property 16: Graceful Degradation Fallback
*For any* AI service failure, the platform SHALL return rule-based recommendations within 500ms without error to the user.
**Validates: Requirements 35.3**

### Property 17: Audit Log Hash Chain Integrity
*For any* audit log entry, current_hash SHALL equal SHA256(previous_hash + entry_data), forming an unbroken chain.
**Validates: Requirements 16.4, 31.6**

### Property 18: Rate Limiting Enforcement
*For any* user exceeding rate limit, subsequent requests within the window SHALL receive HTTP 429 with valid Retry-After header.
**Validates: Requirements 19.6, 31.2**

### Property 19: JWT Token Expiry Enforcement
*For any* expired JWT token, authentication SHALL fail with HTTP 401 regardless of signature validity.
**Validates: Requirements 1.3, 1.5**

### Property 20: Booking Idempotency
*For any* booking request with the same idempotency key, repeated submissions SHALL return the same booking_id without creating duplicates.
**Validates: Requirements 12.2**

### Property 21: WebSocket Message Delivery Latency
*For any* price update event, WebSocket broadcast to connected clients SHALL complete within 500ms of Kafka message receipt.
**Validates: Requirements 3.3, 32.5**

### Property 22: Cache Consistency on Update
*For any* offer price update, the cached entry SHALL be invalidated or updated within 1 second of database write.
**Validates: Requirements 32.1, 18.4**

### Property 23: Preset Recommendation Freshness
*For any* displayed preset, the generated_at timestamp SHALL be within 1 hour of current time under normal operation.
**Validates: Requirements 10.3, 28.1**

### Property 24: GPU Benchmark Data Validity
*For any* GPU model in benchmarks table, tflops_fp32 SHALL be > 0 and tokens_per_second_7b SHALL be > 0 for inference-capable GPUs.
**Validates: Requirements 21.6, 33.4**

### Property 25: Disaster Recovery RPO Compliance
*For any* point-in-time recovery request, data loss SHALL be ≤5 minutes from the failure timestamp.
**Validates: Requirements 37.1**

## Error Handling

### Error Response Format
All services SHALL return errors in consistent JSON format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error message",
    "details": { "field": "gpu_type", "reason": "required" },
    "trace_id": "abc123-def456"
  }
}
```

### Error Categories and HTTP Status Codes
| Category | Code | HTTP Status | Retry |
|----------|------|-------------|-------|
| VALIDATION_ERROR | 1xxx | 400 | No |
| AUTHENTICATION_ERROR | 2xxx | 401 | No |
| AUTHORIZATION_ERROR | 3xxx | 403 | No |
| NOT_FOUND | 4xxx | 404 | No |
| RATE_LIMITED | 5xxx | 429 | Yes (with backoff) |
| PROVIDER_ERROR | 6xxx | 502 | Yes |
| SERVICE_UNAVAILABLE | 7xxx | 503 | Yes |
| INTERNAL_ERROR | 9xxx | 500 | Yes |

### Circuit Breaker Configuration
```yaml
circuit_breaker:
  failure_threshold: 5
  failure_window_seconds: 30
  recovery_timeout_seconds: 60
  half_open_max_requests: 3
  
  per_service:
    provider_adapters:
      failure_threshold: 3
      recovery_timeout_seconds: 120
    math_core:
      failure_threshold: 10
      recovery_timeout_seconds: 30
    ai_assistant:
      failure_threshold: 5
      recovery_timeout_seconds: 60
```

### Fallback Strategies
| Service | Fallback |
|---------|----------|
| Provider Adapter | Return cached offers with "stale" flag |
| Math Core | Use pre-computed KPIs from cache |
| AI Assistant | Rule-based recommendations |
| Price Feed | Display last known prices with timestamp |
| Booking | Queue request for retry, notify user |

## Testing Strategy

### Dual Testing Approach

**Unit Tests (pytest, jest):**
- Test individual functions and methods
- Mock external dependencies
- Coverage target: ≥80%
- Run on every commit

**Property-Based Tests (Hypothesis, fast-check):**
- Verify universal properties across random inputs
- Minimum 100 iterations per property
- Tag format: `**Feature: gpubroker-enterprise-saas, Property {N}: {description}**`

### Test Categories

1. **Math Core Algorithm Tests**
   - TOPSIS with known decision matrices
   - ALS convergence verification
   - Cosine similarity edge cases
   - Numerical precision validation

2. **API Contract Tests**
   - OpenAPI schema validation
   - Request/response format verification
   - Error response consistency

3. **Integration Tests**
   - Provider adapter with sandbox APIs
   - End-to-end booking flow
   - AI chat with mock LLM

4. **Performance Tests (k6)**
   - Load test: 10,000 concurrent users
   - Latency targets: p95 < 200ms
   - Throughput: 5,000 req/s sustained

5. **Chaos Tests (Chaos Mesh)**
   - Pod termination recovery
   - Network partition handling
   - Database failover

6. **Security Tests**
   - OWASP ZAP scans
   - JWT manipulation attempts
   - SQL injection fuzzing
   - Rate limit bypass attempts

### Property-Based Test Examples

```python
# Property 6: Cost-per-token calculation
@given(
    price=st.floats(min_value=0.01, max_value=100.0),
    tps=st.integers(min_value=100, max_value=10000)
)
def test_cost_per_token_calculation(price, tps):
    """
    **Feature: gpubroker-enterprise-saas, Property 6: Math Core Cost-Per-Token Calculation**
    """
    result = math_core.calculate_cost_per_token(price, tps)
    expected = price / (tps * 3600)
    assert abs(result - expected) < 1e-10  # IEEE 754 precision

# Property 7: TOPSIS determinism
@given(
    matrix=st.lists(st.lists(st.floats(min_value=0.1, max_value=100), min_size=3, max_size=3), min_size=5, max_size=20),
    weights=st.lists(st.floats(min_value=0.1, max_value=1.0), min_size=3, max_size=3)
)
def test_topsis_determinism(matrix, weights):
    """
    **Feature: gpubroker-enterprise-saas, Property 7: TOPSIS Ranking Determinism**
    """
    result1 = topsis_engine.calculate(matrix, weights)
    result2 = topsis_engine.calculate(matrix, weights)
    assert result1.rankings == result2.rankings

# Property 10: Cosine similarity bounds
@given(
    vec1=st.lists(st.floats(min_value=-100, max_value=100), min_size=5, max_size=5),
    vec2=st.lists(st.floats(min_value=-100, max_value=100), min_size=5, max_size=5)
)
def test_cosine_similarity_bounds(vec1, vec2):
    """
    **Feature: gpubroker-enterprise-saas, Property 10: Content-Based Similarity Bounds**
    """
    similarity = math_core.cosine_similarity(vec1, vec2)
    assert -1.0 <= similarity <= 1.0
    
    # Identical vectors should have similarity 1.0
    self_similarity = math_core.cosine_similarity(vec1, vec1)
    assert abs(self_similarity - 1.0) < 1e-10
```

### CI/CD Test Pipeline

```yaml
stages:
  - lint:
      - ruff check (Python)
      - eslint (TypeScript)
      - prettier check
  
  - unit_tests:
      - pytest --cov=80%
      - jest --coverage
  
  - property_tests:
      - pytest -m property --hypothesis-profile=ci
  
  - integration_tests:
      - pytest -m integration
      - playwright e2e
  
  - security_scans:
      - trivy image scan
      - bandit (Python SAST)
      - npm audit
      - OWASP ZAP (on staging)
  
  - performance_tests:
      - k6 run load_test.js (nightly)
  
  - chaos_tests:
      - chaos-mesh experiments (weekly)
```
