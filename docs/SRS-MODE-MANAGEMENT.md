# GPUBROKER Mode Management - Software Requirements Specification
## Document: SRS-MODE-001 | Version 1.0 | January 2026

---

## 1. Executive Summary

This document specifies the centralized **Sandbox/Live Mode Management System** for GPUBROKER. The system provides a single toggle switch in the Admin UI that instantly switches ALL project services between testing (Sandbox) and production (Live) modes.

### 1.1 Purpose
Provide developers and operators with a safe way to test all functionality using sandbox/test credentials before switching to live/production mode for real transactions.

### 1.2 Scope
All services across the GPUBROKER platform that have mode-dependent behavior.

---

## 2. Services Inventory

### 2.1 Payment Services

| Service | Sandbox Mode | Live Mode | File Location |
|---------|-------------|-----------|---------------|
| **Stripe** | `sk_test_*`, `pk_test_*` | `sk_live_*`, `pk_live_*` | `gpubrokerpod/apps/billing/stripe_service.py` |
| **PayPal** | `api-m.sandbox.paypal.com` | `api-m.paypal.com` | `gpubrokeradmin/services/payments/paypal.py` |

### 2.2 GPU Provider Services

| Service | Sandbox Mode | Live Mode | File Location |
|---------|-------------|-----------|---------------|
| **RunPod** | Mock data / Test API key | Live API key | `gpubrokerpod/apps/providers/services.py` |
| **Vast.ai** | Mock data / Test API key | Live API key | `gpubrokerpod/apps/providers/vastai.py` |
| **Lambda Labs** | Mock data / Test API key | Live API key | `gpubrokerpod/apps/providers/lambda.py` |

### 2.3 Pod Configuration

| Service | Sandbox Mode | Live Mode | File Location |
|---------|-------------|-----------|---------------|
| **PodConfiguration** | `sandbox_value` field | `live_value` field | `gpubrokerpod/apps/pod_config/models.py` |
| **PodParameter** | Uses `sandbox_value` | Uses `live_value` | `gpubrokerpod/apps/pod_config/models.py` |
| **PodConfigService** | Returns sandbox values | Returns live values | `gpubrokerpod/apps/pod_config/services.py` |

### 2.4 Email Services

| Service | Sandbox Mode | Live Mode | File Location |
|---------|-------------|-----------|---------------|
| **Email Backend** | Console backend (logs) | AWS SES | `gpubrokeradmin/services/email.py` |
| **From Address** | `sandbox-noreply@` | `noreply@` | Settings |

### 2.5 Provisioning Services

| Service | Sandbox Mode | Live Mode | File Location |
|---------|-------------|-----------|---------------|
| **Pod Deployment** | Mock deployment (5s delay) | Real GPU provisioning | `gpubrokeradmin/services/deploy.py` |
| **Auto-Confirm** | Enabled | Disabled | Settings |

### 2.6 Analytics & Webhooks

| Service | Sandbox Mode | Live Mode | File Location |
|---------|-------------|-----------|---------------|
| **Event Tracking** | Disabled | Enabled | `gpubrokeradmin/services/analytics.py` |
| **Webhook Signatures** | Optional verification | Strict verification | Webhook handlers |

---

## 3. Centralized Mode Service

### 3.1 Implementation
```
File: gpubrokeradmin/services/mode.py
Class: ModeService
Instance: mode_service (singleton)
```

### 3.2 Usage Pattern
```python
from gpubrokeradmin.services.mode import mode_service

# Check current mode
if mode_service.is_live:
    # Production behavior
else:
    # Sandbox behavior

# Get mode-aware credentials
stripe_key = mode_service.stripe.secret_key
paypal_config = mode_service.paypal

# Switch mode (admin only)
mode_service.set_mode('live')
```

### 3.3 Configuration Properties

| Property | Returns | Description |
|----------|---------|-------------|
| `mode_service.current_mode` | `'sandbox'` or `'live'` | Current global mode |
| `mode_service.is_sandbox` | `bool` | True if in sandbox mode |
| `mode_service.is_live` | `bool` | True if in live mode |
| `mode_service.stripe` | `StripeConfig` | Stripe configuration |
| `mode_service.paypal` | `PayPalConfig` | PayPal configuration |
| `mode_service.gpu_providers` | `GPUProviderConfig` | GPU provider settings |
| `mode_service.pod_provisioning` | `PodProvisioningConfig` | Pod deployment settings |
| `mode_service.email` | `EmailConfig` | Email backend configuration |
| `mode_service.analytics` | `AnalyticsConfig` | Event tracking settings |
| `mode_service.webhooks` | `WebhookConfig` | Webhook validation settings |

---

## 4. Environment Variables

### 4.1 Global Mode
```
GPUBROKER_MODE=sandbox  # or 'live'
```

### 4.2 Stripe Configuration
```
# Sandbox Keys
STRIPE_SECRET_KEY_TEST=sk_test_...
STRIPE_PUBLISHABLE_KEY_TEST=pk_test_...

# Live Keys
STRIPE_SECRET_KEY_LIVE=sk_live_...
STRIPE_PUBLISHABLE_KEY_LIVE=pk_live_...

# Shared
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 4.3 PayPal Configuration
```
# Sandbox Credentials
PAYPAL_CLIENT_ID_SANDBOX=...
PAYPAL_CLIENT_SECRET_SANDBOX=...

# Live Credentials
PAYPAL_CLIENT_ID_LIVE=...
PAYPAL_CLIENT_SECRET_LIVE=...
```

### 4.4 GPU Provider Configuration
```
# Live Keys
RUNPOD_API_KEY=...
VASTAI_API_KEY=...
LAMBDA_API_KEY=...

# Test Keys (optional)
RUNPOD_API_KEY_TEST=...
VASTAI_API_KEY_TEST=...
LAMBDA_API_KEY_TEST=...

# Sandbox Behavior
MOCK_GPU_PROVISIONING=true  # Use mock data in sandbox
```

---

## 5. Admin UI Requirements

### 5.1 Mode Toggle Switch
- Location: Admin dashboard header (persistent across all pages)
- Design: Toggle switch matching PayPal style (Sandbox | Live)
- Visual Indicator: Clear badge showing current mode on all pages

### 5.2 Confirmation Dialog
When switching to Live mode:
```
⚠️ Switch to Live Mode?

You are about to switch to LIVE mode. This will:
• Process REAL payments
• Send REAL emails to customers
• Provision REAL GPU resources
• Use production API credentials

Are you sure you want to continue?

[Cancel] [Switch to Live]
```

### 5.3 Mode Indicator Colors
- **Sandbox**: Blue badge with "SANDBOX" text
- **Live**: Red badge with "LIVE" text

---

## 6. API Endpoints

### 6.1 Mode Management API
```
GET  /api/v2/admin/mode         # Get current mode status
POST /api/v2/admin/mode         # Switch mode (requires admin)
GET  /api/v2/admin/mode/config  # Get all mode-aware configurations
```

### 6.2 Response Schema
```json
{
  "mode": "sandbox",
  "is_live": false,
  "is_sandbox": true,
  "stripe_configured": true,
  "paypal_configured": true,
  "mock_gpu": true,
  "mock_pods": true,
  "email_backend": "django.core.mail.backends.console.EmailBackend"
}
```

---

## 7. Database Schema

### 7.1 PodConfiguration Model
```python
class PodConfiguration(models.Model):
    class Mode(models.TextChoices):
        SANDBOX = 'sandbox', 'Sandbox (Testing)'
        LIVE = 'live', 'Live (Production)'
    
    mode = models.CharField(
        max_length=10,
        choices=Mode.choices,
        default=Mode.SANDBOX
    )
```

### 7.2 PodParameter Model
```python
class PodParameter(models.Model):
    sandbox_value = models.TextField(blank=True)  # Value for SANDBOX mode
    live_value = models.TextField(blank=True)     # Value for LIVE mode
    default_value = models.TextField(blank=True)  # Fallback value
```

---

## 8. Security Considerations

### 8.1 Mode Switch Authorization
- Only users with `is_superuser=True` can switch modes
- Mode switch logged with timestamp and user ID
- Rate limit: Max 5 mode switches per hour

### 8.2 Credential Isolation
- Live credentials never logged
- Sandbox credentials can be logged for debugging
- Webhook payloads logged only in sandbox mode

### 8.3 Accidental Live Mode Protection
- Confirmation dialog required for sandbox → live switch
- 5-second countdown before live mode activation
- Quick "Revert to Sandbox" button always visible in Live mode

---

## 9. Testing Requirements

### 9.1 Sandbox Mode Tests
- [ ] All Stripe test transactions work
- [ ] All PayPal sandbox transactions work
- [ ] Mock GPU data returned correctly
- [ ] Pod provisioning uses mock deployment
- [ ] Emails logged to console (not sent)
- [ ] Webhooks accept unsigned payloads

### 9.2 Live Mode Tests
- [ ] Real Stripe transactions (use test card in live mode)
- [ ] Real PayPal transactions (use test account)
- [ ] Real GPU provider API calls
- [ ] Real pod provisioning
- [ ] Real SES email sending
- [ ] Webhook signature validation enforced

---

## 10. Migration Path

### 10.1 Existing Code Updates Required
All files with hardcoded mode logic should be updated to use `mode_service`:

1. `gpubrokerpod/apps/billing/stripe_service.py` - Use `mode_service.stripe`
2. `gpubrokeradmin/services/payments/paypal.py` - Use `mode_service.paypal`
3. `gpubrokerpod/apps/pod_config/services.py` - Use `mode_service.current_mode`
4. `gpubrokeradmin/services/email.py` - Use `mode_service.email`
5. `gpubrokeradmin/services/deploy.py` - Use `mode_service.pod_provisioning`

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-01 | GPUBROKER Team | Initial specification |
