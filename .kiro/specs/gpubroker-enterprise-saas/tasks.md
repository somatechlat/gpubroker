# Implementation Plan

> **⚠️ SUPERSEDED**: This spec was created for the original microservices architecture. 
> The project has been migrated to Django 5 + Django Ninja. 
> See `.kiro/specs/django-migration/` for the current implementation.

## Phase 1: Math Core Service (GPUMathBroker) - Foundation

> **Status**: ✅ Migrated to `backend/gpubroker/apps/math_core/`

- [-] 1. Create Math Core Service structure
  - [x] 1.1 Create Django app `backend/gpubroker/apps/math_core/`
    - Create main.py, requirements.txt, Dockerfile
    - Set up project structure: core/, algorithms/, models/, tests/
    - _Requirements: 21.1, 21.2, 21.3_
  - [x] 1.2 Implement GPU Benchmarks data model and repository
    - Create gpu_benchmarks table migration
    - Implement GPUBenchmark Pydantic model
    - Create benchmark repository with CRUD operations
    - Seed with verified benchmark data (A100, H100, V100, RTX 4090, etc.)
    - _Requirements: 21.6, 33.4_
  - [x] 1.3 Write property test for GPU benchmark data validity
    - **Property 24: GPU Benchmark Data Validity**
    - **Validates: Requirements 21.6, 33.4**
- [x] 1.4 Implement KPI Calculator module
    - Create `/math/cost-per-token` endpoint
    - Create `/math/cost-per-gflop` endpoint
    - Create `/math/efficiency-score` endpoint
    - Use IEEE 754 double precision, 4 decimal rounding
    - _Requirements: 21.1, 21.2, 5.1, 5.2, 33.3_
  - [x] 1.5 Write property test for cost-per-token calculation
    - **Property 6: Math Core Cost-Per-Token Calculation**
    - **Validates: Requirements 5.1, 21.1, 33.3**

- [ ] 2. Implement TOPSIS Algorithm Engine
  - [x] 2.1 Create TOPSIS engine class with full algorithm
    - Implement vector normalization (L2 norm)
    - Implement weighted normalized matrix calculation
    - Implement ideal/anti-ideal solution determination
    - Implement separation measures (Euclidean distance)
    - Implement relative closeness scoring
    - Create `/math/topsis` endpoint
    - _Requirements: 7.1, 33.1_
  - [x] 2.2 Write property test for TOPSIS determinism
    - **Property 7: TOPSIS Ranking Determinism**
    - **Validates: Requirements 7.1**
  - [x] 2.3 Write property test for TOPSIS ideal solution correctness
    - **Property 8: TOPSIS Ideal Solution Correctness**
    - **Validates: Requirements 7.1**

- [ ] 3. Implement Collaborative Filtering (ALS)
  - [x] 3.1 Create ALS Recommender class
    - Implement matrix factorization with regularization (lambda=0.1)
    - Implement alternating optimization for user/item factors
    - Set latent factors k=50, convergence tolerance 1e-6
    - Create `/math/collaborative-filter` endpoint
    - _Requirements: 7.2, 33.2_
  - [x] 3.2 Write property test for ALS convergence
    - **Property 9: Collaborative Filtering Matrix Factorization Convergence**
    - **Validates: Requirements 7.2, 33.2**

- [ ] 4. Implement Content-Based Similarity
  - [x] 4.1 Create content similarity module
    - Implement cosine similarity calculation
    - Implement feature vector extraction from offers
    - Create `/math/content-similarity` endpoint
    - _Requirements: 7.3_
  - [x]* 4.2 Write property test for cosine similarity bounds
    - **Property 10: Content-Based Similarity Bounds**
    - **Validates: Requirements 7.3**

- [ ] 5. Implement Ensemble Recommender
  - [x] 5.1 Create ensemble recommendation endpoint
    - Combine TOPSIS (0.4) + Collaborative (0.3) + Content-Based (0.3)
    - Create `/math/ensemble-recommend` endpoint
    - Implement cold-start fallback to popularity-based ranking
    - _Requirements: 7.4, 7.5_
  - [x]* 5.2 Write property test for ensemble weight sum
    - **Property 11: Ensemble Recommendation Weight Sum**
    - **Validates: Requirements 7.4**

- [x] 6. Implement Workload-to-GPU Mapping Engine
  - [x] 6.1 Create workload mapping module
    - Implement image generation workload mapping (VRAM, time estimates)
    - Implement LLM inference workload mapping (context length, TPS)
    - Implement training workload mapping (dataset size, epochs)
    - Create `/math/estimate-workload` endpoint
    - Create `/math/map-workload-to-gpu` endpoint
    - _Requirements: 22.2, 22.3, 22.4, 27.1, 27.2, 27.3_
  - [x]* 6.3 Write property test for workload mapping completeness
    - **Property 13: Workload-to-GPU Mapping Completeness**
    - **Validates: Requirements 22.2, 22.3, 22.4, 27.1, 27.2, 27.3**

- [ ] 7. Checkpoint - Ensure all Math Core tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 2: Enhanced Provider Service

- [ ] 8. Refactor Provider Service to use Math Core
  - [x] 8.1 Add Math Core client to Provider Service
    - Create MathCoreClient class with circuit breaker
    - Replace inline KPI calculations with Math Core calls
    - Add fallback to cached KPIs on Math Core failure
    - _Requirements: 21.1, 35.5_
  - [x] 8.2 Implement provider offer normalization validation
    - Add Pydantic validation for all required fields
    - Add data type validation and coercion
    - _Requirements: 2.2, 2.5_
  - [x]* 8.3 Write property test for offer normalization
    - **Property 2: Provider Offer Normalization Consistency**
    - **Validates: Requirements 2.2, 2.5**

- [x] 9. Implement Real-Time Price Feed with Kafka
  - [x] 9.1 Add Kafka producer to ingestion pipeline
    - Publish price changes to `price_updates` topic
    - Include offer_id, old_price, new_price, timestamp
    - _Requirements: 3.1_
  - [x] 9.2 Create WebSocket Gateway service
    - Migrated to `backend/gpubroker/apps/websocket_gateway/` with Django Channels
    - Subscribe to Redis Pub/Sub for price updates
    - Implement client connection management
    - Implement heartbeat pings every 30 seconds
    - _Requirements: 3.2, 3.3, 3.4_
  - [x]* 9.3 Write property test for WebSocket delivery latency
    - **Property 21: WebSocket Message Delivery Latency**
    - **Validates: Requirements 3.3, 32.5**

- [ ] 10. Enhance Filtering and Search
  - [x] 10.1 Add advanced filter support
    - Implement all filter types: gpu_type, gpu_memory_gb, price range, region, availability, compliance_tags, provider_name
    - Add full-text search with Meilisearch integration
    - _Requirements: 4.1, 4.2_
  - [x]* 10.2 Write property test for filter correctness
    - **Property 4: Filter Query Correctness**
    - **Validates: Requirements 4.1, 4.2**
  - [x]* 10.3 Write property test for pagination consistency
    - **Property 5: Pagination Consistency**
    - **Validates: Requirements 4.6**

- [ ] 11. Checkpoint - Ensure Provider Service tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 3: AI Assistant Service

- [ ] 12. Create AI Assistant Service
  - [x] 12.1 Migrated to `backend/gpubroker/apps/ai_assistant/`
    - Django Ninja API endpoints
    - Set up LangChain with Ollama/Mistral-7B
    - Create conversation memory management
    - _Requirements: 8.3_
  - [x] 12.2 Implement natural language workload parser
    - Create intent extraction pipeline
    - Extract: workload_type, quantity, duration, quality, region
    - Create `/ai/parse-workload` endpoint
    - _Requirements: 22.1_
  - [x]* 12.3 Write property test for workload extraction
    - **Property 12: Natural Language Workload Extraction**
    - **Validates: Requirements 22.1**

- [ ] 13. Implement AI Chat Endpoint
  - [x] 13.1 Create chat endpoint with context management
    - Create `/ai/chat` endpoint
    - Implement conversation history (10 turns)
    - Integrate with Math Core for calculations
    - Integrate with Recommendation Engine
    - _Requirements: 8.1, 8.2, 8.4, 8.5, 8.6_
  - [x]* 13.2 Write property test for AI response time
    - **Property 14: AI Response Time Bound**
    - **Validates: Requirements 8.1, 32.1**

- [ ] 14. Implement Workload Templates
  - [x] 14.1 Create template system
    - Define templates: Image Generation, LLM Inference, Model Training, Video Processing, Data Processing
    - Create mini-wizard question flows per template
    - Create `/ai/templates` endpoint
    - _Requirements: 23.1, 23.2, 23.3, 23.4, 23.5_

- [ ] 15. Implement AI Context Awareness
  - [x] 15.1 Add screen context integration
    - Pass current filters to AI context
    - Pass visible offers to AI context
    - Implement "analyze my current search" capability
    - _Requirements: 25.1, 25.2, 25.3, 25.4_

- [ ] 16. Checkpoint - Ensure AI Assistant tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 4: Frontend AI-First Experience

- [ ] 17. Implement Persistent AI Button
  - [ ] 17.1 Create floating AI assistant button component
    - Position fixed bottom-right on all pages
    - Implement chat panel overlay (non-blocking)
    - Add unread message indicator
    - Mobile responsive (FAB → full-screen)
    - _Requirements: 9.1, 9.2, 9.3, 9.5, 9.6_

- [ ] 18. Implement AI Chat Panel
  - [ ] 18.1 Create ChatPanel component
    - Message list with user/assistant styling
    - Input field with send button
    - Loading states and error handling
    - Quick-action template buttons
    - _Requirements: 8.1, 23.1_
  - [ ] 18.2 Implement AI recommendation cards
    - Create AIRecommendationCard component
    - Show rank, provider logo, GPU, cost, score, explanation
    - Add "Book Now" button with pre-filled form
    - _Requirements: 24.1, 24.2, 24.3, 24.4_

- [ ] 19. Implement Preset Recommendations
  - [ ] 19.1 Create preset cards on dashboard
    - Display: Best Value, Highest Performance, Most Reliable, Budget Friendly, Enterprise Grade
    - Show top offer summary, savings %, confidence score
    - Add personalized "For You" preset
    - _Requirements: 10.1, 10.2, 10.4, 10.5_

- [ ] 20. Implement Real-Time Price Updates
  - [x] 20.1 Add WebSocket client to frontend
    - Connect to WebSocket Gateway
    - Handle price update messages
    - Animate price changes (3 second highlight)
    - Implement reconnection with exponential backoff
    - _Requirements: 3.5, 3.6_

- [ ] 21. Enhance Dashboard Metrics
  - [ ] 21.1 Implement KPI Overview with Math Core data
    - Display: active providers, available GPUs, avg price, savings potential
    - Add price distribution histogram
    - Add provider market share pie chart
    - Add 7-day price trend line chart
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 22. Checkpoint - Ensure Frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 5: Security & Resilience

- [ ] 23. Implement Circuit Breakers
  - [ ] 23.1 Add circuit breaker to all service clients
    - Configure: 5 failures in 30s → open, 60s recovery, 3 half-open requests
    - Implement per-service configuration
    - _Requirements: 35.1_
  - [ ]* 23.2 Write property test for circuit breaker state transitions
    - **Property 15: Circuit Breaker State Transitions**
    - **Validates: Requirements 35.1**

- [ ] 24. Implement Graceful Degradation
  - [ ] 24.1 Add fallback handlers for all services
    - AI fallback to rule-based recommendations
    - Math Core fallback to cached KPIs
    - Provider fallback to cached offers with "stale" flag
    - _Requirements: 35.2, 35.3, 35.4, 35.5_
  - [ ]* 24.2 Write property test for graceful degradation
    - **Property 16: Graceful Degradation Fallback**
    - **Validates: Requirements 35.3**

- [ ] 25. Implement Audit Log with Hash Chain
  - [ ] 25.1 Create audit logging service
    - Implement hash chain: current_hash = SHA256(previous_hash + entry_data)
    - Create audit_log table with immutable design
    - Add audit middleware to all services
    - _Requirements: 16.4_
  - [ ]* 25.2 Write property test for hash chain integrity
    - **Property 17: Audit Log Hash Chain Integrity**
    - **Validates: Requirements 16.4, 31.6**

- [ ] 26. Implement Rate Limiting
  - [ ] 26.1 Add rate limiting to API Gateway
    - Implement sliding window algorithm
    - Configure per-plan limits (free: 10/s, pro: 100/s, enterprise: 1000/s)
    - Return HTTP 429 with Retry-After header
    - _Requirements: 19.6, 31.2_
  - [ ]* 26.2 Write property test for rate limiting
    - **Property 18: Rate Limiting Enforcement**
    - **Validates: Requirements 19.6, 31.2**

- [ ] 27. Checkpoint - Ensure Security tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 6: Auth Service Enhancement

- [ ] 28. Enhance JWT Authentication
  - [ ] 28.1 Implement RS256 JWT signing
    - Generate RSA key pair for signing
    - Implement token binding to client fingerprint
    - Add 15-minute access token, 7-day refresh token
    - _Requirements: 1.1, 30.2_
  - [ ]* 28.2 Write property test for token validity
    - **Property 1: Authentication Token Validity**
    - **Validates: Requirements 1.1, 1.3**
  - [ ]* 28.3 Write property test for token expiry enforcement
    - **Property 19: JWT Token Expiry Enforcement**
    - **Validates: Requirements 1.3, 1.5**

- [ ] 29. Implement MFA Support
  - [ ] 29.1 Add TOTP MFA enrollment and verification
    - Create `/auth/mfa/enroll` endpoint
    - Create `/auth/mfa/verify` endpoint
    - Integrate with login flow
    - _Requirements: 1.2_

- [ ] 30. Checkpoint - Ensure Auth tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 7: Booking & Billing

- [ ] 31. Implement Booking Service with Temporal
  - [ ] 31.1 Create booking workflow
    - Create `backend/booking-service/` with Temporal integration
    - Implement BookingWorkflow with saga pattern
    - Add compensation activities for rollback
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  - [ ]* 31.2 Write property test for booking idempotency
    - **Property 20: Booking Idempotency**
    - **Validates: Requirements 12.2**

- [ ] 32. Implement Billing Integration
  - [ ] 32.1 Create billing service scaffold
    - Integrate with Kill Bill or Stripe
    - Implement subscription plans (free, pro, enterprise)
    - Implement usage metering
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

- [ ] 33. Checkpoint - Ensure Booking/Billing tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Phase 8: Observability & Infrastructure

- [ ] 34. Implement Observability Stack
  - [ ] 34.1 Add Prometheus metrics to all services
    - Expose /metrics endpoint
    - Add request_count, latency, error_count metrics
    - _Requirements: 17.1, 17.2_
  - [ ] 34.2 Create Grafana dashboards
    - Service health dashboard
    - KPI trends dashboard
    - Billing & usage dashboard
    - _Requirements: 17.5_
  - [ ] 34.3 Add structured logging with correlation IDs
    - JSON format with trace_id propagation
    - OpenTelemetry integration
    - _Requirements: 17.3, 17.4_

- [ ] 35. Implement Chaos Engineering Setup
  - [ ] 35.1 Add Chaos Mesh configuration
    - Pod termination experiments
    - Network latency injection
    - CPU/memory stress tests
    - _Requirements: 36.1, 36.2_

- [ ] 36. Implement CI/CD Pipeline
  - [ ] 36.1 Enhance GitHub Actions workflow
    - Add lint, type-check, unit tests, integration tests
    - Add security scans (Trivy, Bandit)
    - Add Docker build and push
    - _Requirements: 20.1, 20.2_
  - [ ] 36.2 Add Helm charts and ArgoCD configuration
    - Create Helm chart for each service
    - Configure ArgoCD for GitOps deployment
    - _Requirements: 20.3, 20.4_

- [ ] 37. Final Checkpoint - Full test suite
  - Ensure all tests pass, ask the user if questions arise.
