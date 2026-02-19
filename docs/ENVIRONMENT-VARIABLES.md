# GPUBROKER Environment Variables Reference
## Complete Configuration for Sandbox and Live Deployments

---

## 1. Global Mode Configuration

```bash
# =============================================================================
# GLOBAL MODE (sandbox or live)
# =============================================================================
GPUBROKER_MODE=sandbox    # Options: sandbox, live

# Domain Configuration
GPUBROKER_DOMAIN=gpubroker.site
GPUBROKER_BASE_URL=https://gpubroker.site
GPUBROKER_ADMIN_URL=https://admin.gpubroker.site
GPUBROKER_API_URL=https://api.gpubroker.site
```

---

## 2. Payment Configuration

### 2.1 Stripe
```bash
# =============================================================================
# STRIPE CONFIGURATION
# =============================================================================

# Sandbox Keys (sk_test_*, pk_test_*)
STRIPE_SECRET_KEY_TEST=sk_test_...
STRIPE_PUBLISHABLE_KEY_TEST=pk_test_...

# Live Keys (sk_live_*, pk_live_*)
STRIPE_SECRET_KEY_LIVE=sk_live_...
STRIPE_PUBLISHABLE_KEY_LIVE=pk_live_...

# Webhook Secret (shared or mode-specific)
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_WEBHOOK_SECRET_TEST=whsec_test_...
STRIPE_WEBHOOK_SECRET_LIVE=whsec_live_...
```

### 2.2 PayPal
```bash
# =============================================================================
# PAYPAL CONFIGURATION
# =============================================================================

# Sandbox Credentials (from developer.paypal.com)
PAYPAL_CLIENT_ID_SANDBOX=AY...sandbox
PAYPAL_CLIENT_SECRET_SANDBOX=EP...sandbox

# Live Credentials (from paypal.com/business)
PAYPAL_CLIENT_ID_LIVE=AY...live
PAYPAL_CLIENT_SECRET_LIVE=EP...live
```

---

## 3. GPU Provider Configuration

```bash
# =============================================================================
# GPU PROVIDERS
# =============================================================================

# RunPod
RUNPOD_API_KEY=...                    # Live API key
RUNPOD_API_KEY_TEST=...               # Test/sandbox API key (optional)

# Vast.ai
VASTAI_API_KEY=...                    # Live API key
VASTAI_API_KEY_TEST=...               # Test API key (optional)

# Lambda Labs
LAMBDA_API_KEY=...                    # Live API key
LAMBDA_API_KEY_TEST=...               # Test API key (optional)

# Sandbox Behavior
MOCK_GPU_PROVISIONING=true            # Use mock data in sandbox mode
```

---

## 4. AWS Configuration

```bash
# =============================================================================
# AWS CONFIGURATION
# =============================================================================

# Core AWS
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=302776397208
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# ECS/Fargate (Pod Deployment)
ECS_CLUSTER_NAME=gpubroker-pods
ECS_TASK_DEFINITION=gpubroker-pod
ECS_SUBNETS=subnet-xxx,subnet-yyy
ECS_SECURITY_GROUPS=sg-xxx

# S3 (Static assets, backups)
S3_BUCKET_STATIC=gpubroker-site-landing
S3_BUCKET_BACKUPS=gpubroker-backups

# SES (Email)
SES_FROM_EMAIL=noreply@gpubroker.site
SES_REGION=us-east-1

# CloudFront
CLOUDFRONT_DISTRIBUTION_ID=E3295G0PO2RW7M
```

---

## 5. Database Configuration

```bash
# =============================================================================
# DATABASE
# =============================================================================

# PostgreSQL (same for both modes, different data)
DATABASE_URL=postgresql://gpubroker:password@postgres:5432/gpubroker
POSTGRES_USER=gpubroker
POSTGRES_PASSWORD=gpubroker_secure_password
POSTGRES_DB=gpubroker

# Redis (caching, mode state persistence)
REDIS_URL=redis://redis:6379/0

# ClickHouse (analytics)
CLICKHOUSE_URL=http://clickhouse:8123
CLICKHOUSE_DATABASE=gpubroker
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=...
```

---

## 6. Security & Authentication

```bash
# =============================================================================
# SECURITY
# =============================================================================

# Django
SECRET_KEY=your-super-secret-key-change-in-production
DEBUG=false                           # Always false in Live mode

# JWT Keys
JWT_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----...
JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----...
JWT_ALGORITHM=RS256

# CORS
CORS_ALLOWED_ORIGINS=https://gpubroker.site,https://admin.gpubroker.site
ALLOWED_HOSTS=gpubroker.site,admin.gpubroker.site,localhost
```

---

## 7. Regional Configuration

```bash
# =============================================================================
# REGIONAL SETTINGS
# =============================================================================

# Geo-detection
GPUBROKER_DEFAULT_REGION=US
GPUBROKER_DEPLOYMENT_REGION=GLOBAL    # Options: GLOBAL, LATAM, EC, US, EU

# Force specific country (for testing)
GPUBROKER_FORCE_COUNTRY=             # Empty for auto-detect, or 'EC', 'US', etc.
```

---

## 8. Feature Flags

```bash
# =============================================================================
# FEATURE FLAGS (SANDBOX vs LIVE behavior)
# =============================================================================

# Auto-confirm emails in sandbox (skip email verification)
AUTO_CONFIRM_EMAIL=true               # true in sandbox, false in live

# Mock external services
MOCK_GPU_PROVISIONING=true           # true in sandbox
MOCK_PAYMENT_PROCESSING=false        # Use real Stripe/PayPal test modes

# Logging
LOG_WEBHOOK_PAYLOADS=true            # true in sandbox for debugging
LOG_LEVEL=DEBUG                      # DEBUG in sandbox, INFO in live
```

---

## 9. Sample .env Files

### 9.1 Local Development (.env.local)
```bash
# Local Development Environment
GPUBROKER_MODE=sandbox
GPUBROKER_DOMAIN=localhost
DEBUG=true

# Database (Local)
DATABASE_URL=postgresql://gpubroker:gpubroker_dev_password@localhost:28001/gpubroker
REDIS_URL=redis://localhost:28004/0

# Stripe Test Keys
STRIPE_SECRET_KEY_TEST=sk_test_xxx
STRIPE_PUBLISHABLE_KEY_TEST=pk_test_xxx

# PayPal Sandbox
PAYPAL_CLIENT_ID_SANDBOX=AY-sandbox
PAYPAL_CLIENT_SECRET_SANDBOX=EP-sandbox

# Mock everything
MOCK_GPU_PROVISIONING=true
AUTO_CONFIRM_EMAIL=true
```

### 9.2 Staging (.env.staging)
```bash
# Staging Environment (Real AWS, Test Payment Keys)
GPUBROKER_MODE=sandbox
GPUBROKER_DOMAIN=staging.gpubroker.site
DEBUG=false

# Database (RDS)
DATABASE_URL=postgresql://gpubroker:xxx@staging-db.xxx.us-east-1.rds.amazonaws.com:5432/gpubroker
REDIS_URL=redis://staging-redis.xxx.cache.amazonaws.com:6379/0

# Stripe Test Keys (Real Test Mode)
STRIPE_SECRET_KEY_TEST=sk_test_real
STRIPE_PUBLISHABLE_KEY_TEST=pk_test_real

# PayPal Sandbox
PAYPAL_CLIENT_ID_SANDBOX=AY-sandbox-real
PAYPAL_CLIENT_SECRET_SANDBOX=EP-sandbox-real

# Real AWS but Mock GPU
MOCK_GPU_PROVISIONING=true
AUTO_CONFIRM_EMAIL=false
```

### 9.3 Production (.env.production)
```bash
# Production Environment
GPUBROKER_MODE=live
GPUBROKER_DOMAIN=gpubroker.site
DEBUG=false

# Database (RDS)
DATABASE_URL=postgresql://gpubroker:xxx@prod-db.xxx.us-east-1.rds.amazonaws.com:5432/gpubroker
REDIS_URL=redis://prod-redis.xxx.cache.amazonaws.com:6379/0

# Stripe LIVE Keys
STRIPE_SECRET_KEY_LIVE=sk_live_real
STRIPE_PUBLISHABLE_KEY_LIVE=pk_live_real

# PayPal LIVE
PAYPAL_CLIENT_ID_LIVE=AY-live
PAYPAL_CLIENT_SECRET_LIVE=EP-live

# Everything Real
MOCK_GPU_PROVISIONING=false
AUTO_CONFIRM_EMAIL=false
LOG_WEBHOOK_PAYLOADS=false
```

---

## 10. Kubernetes Local Overrides

Local development uses Minikube + Tilt. Override settings via the generated
`gpubroker-django-config` ConfigMap and `gpubroker-secrets` Secret produced
by `scripts/tilt/render-k8s-config.sh`.

## 11. AWS Parameter Store / Secrets Manager

For production, store sensitive values in AWS Parameter Store:

```bash
# Store secrets
aws ssm put-parameter --name "/gpubroker/prod/STRIPE_SECRET_KEY_LIVE" --value "sk_live_xxx" --type SecureString
aws ssm put-parameter --name "/gpubroker/prod/PAYPAL_CLIENT_SECRET_LIVE" --value "xxx" --type SecureString
aws ssm put-parameter --name "/gpubroker/prod/DATABASE_URL" --value "postgresql://..." --type SecureString

# Retrieve at runtime (in ECS task definition)
"secrets": [
  {"name": "STRIPE_SECRET_KEY_LIVE", "valueFrom": "/gpubroker/prod/STRIPE_SECRET_KEY_LIVE"},
  {"name": "PAYPAL_CLIENT_SECRET_LIVE", "valueFrom": "/gpubroker/prod/PAYPAL_CLIENT_SECRET_LIVE"}
]
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-01 | GPUBROKER Team | Initial release |
