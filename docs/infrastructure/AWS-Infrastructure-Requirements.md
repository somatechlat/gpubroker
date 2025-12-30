# GPUBROKER - AWS Infrastructure Requirements

## Document Version: 1.0
## Date: 2024-12-29
## Status: PLANNING MODE - NO CODE

---

## 1. Deployment Modes

### 1.1 Mode Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GPUBROKER DEPLOYMENT MODES                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │         SANDBOX MODE            │  │          LIVE MODE              │  │
│  │    (Development & Testing)      │  │        (Production)             │  │
│  ├─────────────────────────────────┤  ├─────────────────────────────────┤  │
│  │                                 │  │                                 │  │
│  │  ✓ Stripe Test Keys             │  │  ✓ Stripe Live Keys             │  │
│  │  ✓ Provider Sandbox APIs        │  │  ✓ Provider Production APIs     │  │
│  │  ✓ Test Email (no real send)    │  │  ✓ Real Email Delivery          │  │
│  │  ✓ Mock GPU Provisioning        │  │  ✓ Real GPU Provisioning        │  │
│  │  ✓ Test Database                │  │  ✓ Production Database          │  │
│  │  ✓ No Real Charges              │  │  ✓ Real Billing                 │  │
│  │  ✓ Debug Logging                │  │  ✓ Production Logging           │  │
│  │  ✓ Relaxed Rate Limits          │  │  ✓ Strict Rate Limits           │  │
│  │                                 │  │                                 │  │
│  │  ENV: GPUBROKER_MODE=sandbox    │  │  ENV: GPUBROKER_MODE=live       │  │
│  │                                 │  │                                 │  │
│  └─────────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Environment Variables for Mode Switching

| Variable | Sandbox Value | Live Value | Description |
|----------|---------------|------------|-------------|
| `GPUBROKER_MODE` | `sandbox` | `live` | Master mode switch |
| `STRIPE_SECRET_KEY` | `sk_test_xxx` | `sk_live_xxx` | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | `whsec_test_xxx` | `whsec_live_xxx` | Webhook verification |
| `AWS_ACCOUNT_ID` | `sandbox-account` | `prod-account` | AWS account |
| `PROVIDER_API_MODE` | `sandbox` | `production` | Provider API mode |
| `EMAIL_BACKEND` | `console` | `ses` | Email delivery |
| `DATABASE_URL` | `sandbox-db` | `prod-db` | Database connection |


---

## 2. Complete AWS Services Map

### 2.1 AWS Services by Layer

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS SERVICES - FULL MAP                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: EDGE & GLOBAL                                              │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ Route 53      │ │ CloudFront    │ │ AWS Shield    │              │   │
│  │  │ • DNS         │ │ • CDN         │ │ • DDoS        │              │   │
│  │  │ • Health      │ │ • Edge Cache  │ │ • Advanced    │              │   │
│  │  │ • Failover    │ │ • SSL/TLS     │ │ • WAF Rules   │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  │  ┌───────────────┐ ┌───────────────┐                                │   │
│  │  │ AWS WAF       │ │ Global        │                                │   │
│  │  │ • Rules       │ │ Accelerator   │                                │   │
│  │  │ • Rate Limit  │ │ • Anycast     │                                │   │
│  │  │ • Geo Block   │ │ • TCP/UDP     │                                │   │
│  │  └───────────────┘ └───────────────┘                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: API & AUTHENTICATION                                       │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ API Gateway   │ │ Cognito       │ │ App Mesh      │              │   │
│  │  │ • REST API    │ │ • User Pools  │ │ • Service     │              │   │
│  │  │ • WebSocket   │ │ • Identity    │ │   Mesh        │              │   │
│  │  │ • HTTP API    │ │ • OAuth/OIDC  │ │ • mTLS        │              │   │
│  │  │ • Throttling  │ │ • MFA         │ │ • Observ.     │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: COMPUTE (AUTO-SCALING)                                     │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ Lambda        │ │ ECS Fargate   │ │ App Runner    │              │   │
│  │  │ • Functions   │ │ • Django      │ │ • Simple      │              │   │
│  │  │ • 0-1000 conc │ │ • Channels    │ │   Deploy      │              │   │
│  │  │ • Event-driven│ │ • Auto-scale  │ │ • Auto-scale  │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  │  ┌───────────────┐ ┌───────────────┐                                │   │
│  │  │ EKS           │ │ EC2 Auto      │                                │   │
│  │  │ • Kubernetes  │ │ Scaling       │                                │   │
│  │  │ • Pods        │ │ • Spot        │                                │   │
│  │  │ • HPA/VPA     │ │ • Reserved    │                                │   │
│  │  └───────────────┘ └───────────────┘                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 4: DATA & CACHING                                             │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ RDS Aurora    │ │ ElastiCache   │ │ DynamoDB      │              │   │
│  │  │ • PostgreSQL  │ │ • Redis       │ │ • Sessions    │              │   │
│  │  │ • Serverless  │ │ • Cluster     │ │ • Rate Limits │              │   │
│  │  │ • Multi-AZ    │ │ • Replication │ │ • Global      │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  │  ┌───────────────┐ ┌───────────────┐                                │   │
│  │  │ S3            │ │ DocumentDB    │                                │   │
│  │  │ • Static      │ │ • MongoDB     │                                │   │
│  │  │ • Backups     │ │ • Compatible  │                                │   │
│  │  │ • Logs        │ │ • Flexible    │                                │   │
│  │  └───────────────┘ └───────────────┘                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```


```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS SERVICES - FULL MAP (Continued)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 5: EVENT STREAMING & MESSAGING                                │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ MSK (Kafka)   │ │ Kinesis       │ │ EventBridge   │              │   │
│  │  │ • KRaft Mode  │ │ • Data Stream │ │ • Event Bus   │              │   │
│  │  │ • Topics      │ │ • Firehose    │ │ • Rules       │              │   │
│  │  │ • Partitions  │ │ • Analytics   │ │ • Scheduler   │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ SQS           │ │ SNS           │ │ MQ            │              │   │
│  │  │ • Standard    │ │ • Topics      │ │ • RabbitMQ    │              │   │
│  │  │ • FIFO        │ │ • Push        │ │ • ActiveMQ    │              │   │
│  │  │ • DLQ         │ │ • Fan-out     │ │ • MQTT        │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 6: WORKFLOW & ORCHESTRATION                                   │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ Step          │ │ MWAA          │ │ Batch         │              │   │
│  │  │ Functions     │ │ (Airflow)     │ │ • Jobs        │              │   │
│  │  │ • State       │ │ • DAGs        │ │ • Compute     │              │   │
│  │  │   Machine     │ │ • Scheduling  │ │ • Spot        │              │   │
│  │  │ • Workflows   │ │ • Workers     │ │ • Queues      │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 7: SECURITY & SECRETS                                         │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ Secrets       │ │ KMS           │ │ IAM           │              │   │
│  │  │ Manager       │ │ • CMK         │ │ • Roles       │              │   │
│  │  │ • Rotation    │ │ • Encrypt     │ │ • Policies    │              │   │
│  │  │ • Versioning  │ │ • Sign        │ │ • Federation  │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ Certificate   │ │ Security Hub  │ │ GuardDuty     │              │   │
│  │  │ Manager       │ │ • Compliance  │ │ • Threat      │              │   │
│  │  │ • SSL/TLS     │ │ • Findings    │ │   Detection   │              │   │
│  │  │ • Auto-renew  │ │ • Standards   │ │ • ML-based    │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 8: PAYMENTS & NOTIFICATIONS                                   │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ Stripe        │ │ SES           │ │ Pinpoint      │              │   │
│  │  │ (External)    │ │ • Email       │ │ • Push        │              │   │
│  │  │ • Payments    │ │ • Templates   │ │ • SMS         │              │   │
│  │  │ • Subscript.  │ │ • Tracking    │ │ • Campaigns   │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 9: OBSERVABILITY & MONITORING                                 │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ CloudWatch    │ │ X-Ray         │ │ Managed       │              │   │
│  │  │ • Metrics     │ │ • Tracing     │ │ Grafana       │              │   │
│  │  │ • Logs        │ │ • Service Map │ │ • Dashboards  │              │   │
│  │  │ • Alarms      │ │ • Insights    │ │ • Alerts      │              │   │
│  │  │ • Dashboards  │ │ • Sampling    │ │ • Prometheus  │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  │  ┌───────────────┐ ┌───────────────┐                                │   │
│  │  │ Managed       │ │ OpenSearch    │                                │   │
│  │  │ Prometheus    │ │ • Logs        │                                │   │
│  │  │ • Metrics     │ │ • Search      │                                │   │
│  │  │ • PromQL      │ │ • Analytics   │                                │   │
│  │  └───────────────┘ └───────────────┘                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 10: AI/ML & AGENTIC                                           │   │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐              │   │
│  │  │ Bedrock       │ │ SageMaker     │ │ Comprehend    │              │   │
│  │  │ • Foundation  │ │ • Training    │ │ • NLP         │              │   │
│  │  │   Models      │ │ • Inference   │ │ • Sentiment   │              │   │
│  │  │ • Agents      │ │ • Endpoints   │ │ • Entities    │              │   │
│  │  └───────────────┘ └───────────────┘ └───────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```


---

## 3. Auto-Scaling Policies

### 3.1 Compute Auto-Scaling

| Service | Metric | Scale Out | Scale In | Min | Max |
|---------|--------|-----------|----------|-----|-----|
| ECS Fargate | CPU > 70% | +2 tasks | -1 task | 2 | 100 |
| ECS Fargate | Memory > 80% | +2 tasks | -1 task | 2 | 100 |
| ECS Fargate | Request Count > 1000/min | +5 tasks | -2 tasks | 2 | 100 |
| Lambda | Concurrent > 100 | Auto | Auto | 0 | 1000 |
| Aurora | Connections > 80% | +1 ACU | -1 ACU | 2 | 64 |
| ElastiCache | Memory > 75% | Add node | Remove node | 2 | 10 |

### 3.2 Load Balancer Configuration

```yaml
# Application Load Balancer Settings
ALB:
  Type: application
  Scheme: internet-facing
  
  Listeners:
    - Port: 443
      Protocol: HTTPS
      Certificate: ACM
      DefaultAction: forward-to-target-group
    
    - Port: 80
      Protocol: HTTP
      DefaultAction: redirect-to-https
  
  TargetGroups:
    - Name: django-api
      Protocol: HTTP
      Port: 8000
      HealthCheck:
        Path: /health
        Interval: 30
        Timeout: 5
        HealthyThreshold: 2
        UnhealthyThreshold: 3
    
    - Name: websocket
      Protocol: HTTP
      Port: 8001
      HealthCheck:
        Path: /ws/health
        Interval: 30
      Stickiness:
        Enabled: true
        Duration: 86400  # 24 hours for WebSocket
  
  AutoScaling:
    MinCapacity: 2
    MaxCapacity: 100
    TargetTrackingPolicies:
      - MetricType: ALBRequestCountPerTarget
        TargetValue: 1000
      - MetricType: CPUUtilization
        TargetValue: 70
```

### 3.3 Database Auto-Scaling (Aurora Serverless v2)

```yaml
Aurora:
  Engine: aurora-postgresql
  EngineVersion: "15.4"
  ServerlessV2ScalingConfiguration:
    MinCapacity: 2    # 2 ACUs minimum
    MaxCapacity: 64   # 64 ACUs maximum
  
  # Auto-scaling triggers
  ScalingPolicies:
    - Metric: CPUUtilization
      Target: 70%
    - Metric: DatabaseConnections
      Target: 80%
    - Metric: FreeableMemory
      Target: 20%  # Scale up when < 20% free
  
  # Multi-AZ for high availability
  MultiAZ: true
  
  # Read replicas for read scaling
  ReadReplicas:
    Count: 2
    AutoScaling: true
```

---

## 4. Cost Optimization

### 4.1 Sandbox vs Live Cost Structure

| Component | Sandbox (Dev) | Live (Production) |
|-----------|---------------|-------------------|
| ECS Fargate | 2 tasks (0.25 vCPU) | 10-100 tasks (1 vCPU) |
| Aurora | 2 ACU | 8-64 ACU |
| ElastiCache | cache.t3.micro | cache.r6g.large cluster |
| MSK (Kafka) | kafka.t3.small (1 broker) | kafka.m5.large (3 brokers) |
| Lambda | 128 MB | 512-1024 MB |
| API Gateway | Standard | Standard + Caching |

### 4.2 Estimated Monthly Costs

| Environment | Estimated Cost | Notes |
|-------------|----------------|-------|
| Sandbox | $200-500/month | Minimal resources |
| Live (Low) | $2,000-5,000/month | 10K users |
| Live (Medium) | $10,000-25,000/month | 100K users |
| Live (High) | $50,000-100,000/month | 1M+ users |

---

## 5. High Availability & Disaster Recovery

### 5.1 Multi-AZ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MULTI-AZ DEPLOYMENT                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Region: us-east-1                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  ┌─────────────────────┐        ┌─────────────────────┐             │   │
│  │  │   AZ: us-east-1a    │        │   AZ: us-east-1b    │             │   │
│  │  │                     │        │                     │             │   │
│  │  │  ┌───────────────┐  │        │  ┌───────────────┐  │             │   │
│  │  │  │ ECS Tasks     │  │        │  │ ECS Tasks     │  │             │   │
│  │  │  │ (Django)      │  │        │  │ (Django)      │  │             │   │
│  │  │  └───────────────┘  │        │  └───────────────┘  │             │   │
│  │  │                     │        │                     │             │   │
│  │  │  ┌───────────────┐  │        │  ┌───────────────┐  │             │   │
│  │  │  │ Aurora        │  │◄──────►│  │ Aurora        │  │             │   │
│  │  │  │ Primary       │  │ Sync   │  │ Replica       │  │             │   │
│  │  │  └───────────────┘  │        │  └───────────────┘  │             │   │
│  │  │                     │        │                     │             │   │
│  │  │  ┌───────────────┐  │        │  ┌───────────────┐  │             │   │
│  │  │  │ ElastiCache   │  │◄──────►│  │ ElastiCache   │  │             │   │
│  │  │  │ Primary       │  │ Repl   │  │ Replica       │  │             │   │
│  │  │  └───────────────┘  │        │  └───────────────┘  │             │   │
│  │  │                     │        │                     │             │   │
│  │  │  ┌───────────────┐  │        │  ┌───────────────┐  │             │   │
│  │  │  │ MSK Broker 1  │  │        │  │ MSK Broker 2  │  │             │   │
│  │  │  └───────────────┘  │        │  └───────────────┘  │             │   │
│  │  │                     │        │                     │             │   │
│  │  └─────────────────────┘        └─────────────────────┘             │   │
│  │                                                                      │   │
│  │                         ┌─────────────────────┐                      │   │
│  │                         │   AZ: us-east-1c    │                      │   │
│  │                         │                     │                      │   │
│  │                         │  ┌───────────────┐  │                      │   │
│  │                         │  │ ECS Tasks     │  │                      │   │
│  │                         │  │ (Django)      │  │                      │   │
│  │                         │  └───────────────┘  │                      │   │
│  │                         │                     │                      │   │
│  │                         │  ┌───────────────┐  │                      │   │
│  │                         │  │ Aurora        │  │                      │   │
│  │                         │  │ Replica       │  │                      │   │
│  │                         │  └───────────────┘  │                      │   │
│  │                         │                     │                      │   │
│  │                         │  ┌───────────────┐  │                      │   │
│  │                         │  │ MSK Broker 3  │  │                      │   │
│  │                         │  └───────────────┘  │                      │   │
│  │                         │                     │                      │   │
│  │                         └─────────────────────┘                      │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Disaster Recovery (DR) Strategy

| Component | RPO | RTO | DR Strategy |
|-----------|-----|-----|-------------|
| Aurora | 1 second | 1 minute | Multi-AZ + Global Database |
| ElastiCache | 0 | 1 minute | Multi-AZ Replication |
| S3 | 0 | 0 | Cross-Region Replication |
| MSK | 0 | 5 minutes | Multi-AZ + MirrorMaker |
| Secrets | 0 | 0 | Multi-Region |

