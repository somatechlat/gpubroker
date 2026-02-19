# User Journey 1: Landing Page to GPU Deployment

## Overview

This journey covers the complete conversion funnel from landing page visitor to active GPU rental customer.

**Flow:** Landing Page → Plans → Payment → Pod Confirmation → Email Activation → Deployment

**Infrastructure:** AWS-based (ALB, ECS/EKS, RDS, ElastiCache, SES, Stripe/AWS Payment)

---

## Journey Flow Diagram

```mermaid
flowchart TD
    subgraph "LANDING PAGE"
        A[User Visits gpubroker.com] --> B[Landing Page Loads]
        B --> C{User Action}
        C -->|View Plans| D[Plans/Pricing Page]
        C -->|Learn More| E[Features Section]
        C -->|Contact| F[Contact Form]
        E --> D
    end
    
    subgraph "PLANS & PRICING"
        D --> G[Display Plan Options]
        G --> H{Select Plan}
        H -->|Free Trial| I[Free Trial Flow]
        H -->|Pro Plan| J[Pro Plan - $49/mo]
        H -->|Enterprise| K[Enterprise - Custom]
        I --> L[Email Registration]
        J --> M[Payment Page]
        K --> N[Contact Sales]
    end
    
    subgraph "PAYMENT FLOW"
        M --> O[Enter Payment Details]
        O --> P[Stripe Payment Intent]
        P --> Q{Payment Valid?}
        Q -->|No| R[Show Error]
        R --> O
        Q -->|Yes| S[Payment Authorized - NOT Charged Yet]
    end
    
    subgraph "POD CONFIGURATION"
        S --> T[Pod Configuration Page]
        T --> U[Select GPU Type]
        U --> V[Select Region]
        V --> W[Select Duration]
        W --> X[Review Configuration]
        X --> Y[Confirm Pod Setup]
    end
    
    subgraph "EMAIL ACTIVATION"
        Y --> Z[Send Activation Email via AWS SES]
        Z --> AA[User Receives Email]
        AA --> AB[Click Activation Link]
        AB --> AC{Token Valid?}
        AC -->|No| AD[Expired/Invalid Token]
        AC -->|Yes| AE[Account Activated]
    end
    
    subgraph "DEPLOYMENT & PAYMENT"
        AE --> AF[Show Deploy Button]
        AF --> AG[User Clicks Deploy]
        AG --> AH[Capture Payment - CHARGE OCCURS]
        AH --> AI{Payment Captured?}
        AI -->|No| AJ[Payment Failed]
        AI -->|Yes| AK[Provision GPU Pod]
        AK --> AL[Pod Running]
        AL --> AM[Show Connection Details]
    end
    
    style A fill:#e1f5fe
    style D fill:#fff3e0
    style M fill:#fce4ec
    style T fill:#e8f5e9
    style Z fill:#f3e5f5
    style AG fill:#ffebee
    style AL fill:#c8e6c9
```

---

## Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant U as User Browser
    participant CDN as CloudFront CDN
    participant ALB as AWS ALB
    participant GW as Django Gateway
    participant DB as PostgreSQL RDS
    participant Redis as ElastiCache Redis
    participant Stripe as Stripe API
    participant SES as AWS SES
    participant Provider as GPU Provider API
    
    Note over U,Provider: PHASE 1: LANDING PAGE
    U->>CDN: GET gpubroker.com
    CDN->>U: Return cached landing page
    U->>U: View landing page content
    
    Note over U,Provider: PHASE 2: PLANS & PRICING
    U->>ALB: GET /plans
    ALB->>GW: Forward request
    GW->>DB: Get plan details
    DB->>GW: Plan data
    GW->>U: Return plans page
    U->>U: Select Pro Plan ($49/mo)
    
    Note over U,Provider: PHASE 3: REGISTRATION
    U->>ALB: POST /api/v2/auth/register
    ALB->>GW: Forward registration
    GW->>DB: Check email exists
    DB->>GW: Email available
    GW->>DB: Create user (inactive)
    GW->>Redis: Store session
    GW->>U: Return user_id, redirect to payment
    
    Note over U,Provider: PHASE 4: PAYMENT SETUP (NO CHARGE YET)
    U->>ALB: GET /checkout?plan=pro
    ALB->>GW: Forward request
    GW->>Stripe: Create PaymentIntent (setup)
    Stripe->>GW: client_secret
    GW->>U: Return checkout page with Stripe Elements
    U->>Stripe: Enter card details (client-side)
    Stripe->>U: Card validated, PaymentMethod created
    U->>ALB: POST /api/v2/payments/setup
    ALB->>GW: Save PaymentMethod
    GW->>DB: Store payment_method_id
    GW->>U: Payment method saved, redirect to config
    
    Note over U,Provider: PHASE 5: POD CONFIGURATION
    U->>ALB: GET /configure-pod
    ALB->>GW: Forward request
    GW->>Provider: GET available GPUs (cached)
    Provider->>GW: GPU options
    GW->>U: Return configuration page
    U->>U: Select: A100, us-east, 24 hours
    U->>ALB: POST /api/v2/pods/configure
    ALB->>GW: Save configuration
    GW->>DB: Store pod_config (pending)
    GW->>U: Configuration saved
    
    Note over U,Provider: PHASE 6: EMAIL ACTIVATION
    GW->>SES: Send activation email
    SES->>U: Email delivered
    U->>U: Open email, click activation link
    U->>ALB: GET /activate?token=xxx
    ALB->>GW: Validate token
    GW->>Redis: Check token validity
    Redis->>GW: Token valid
    GW->>DB: Activate user account
    GW->>U: Account activated, show deploy button
    
    Note over U,Provider: PHASE 7: DEPLOYMENT (PAYMENT CAPTURED)
    U->>ALB: POST /api/v2/pods/deploy
    ALB->>GW: Deploy request
    GW->>Stripe: Capture PaymentIntent
    Stripe->>GW: Payment captured ($49)
    GW->>DB: Update payment status
    GW->>Provider: POST /provision (A100, us-east)
    Provider->>GW: Pod provisioning...
    Provider->>GW: Pod ready (SSH details)
    GW->>DB: Store pod details
    GW->>Redis: Publish pod_ready event
    GW->>U: Return connection details
    
    Note over U,Provider: PHASE 8: ACTIVE SESSION
    U->>U: Connect to GPU pod via SSH/Jupyter
```

---

## Screen Details

