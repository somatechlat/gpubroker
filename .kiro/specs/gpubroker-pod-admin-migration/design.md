# Design Document: GPUBROKER POD Admin Migration

## Overview

This design document specifies the completion of the GPUBROKER POD Admin migration from SercopPODAdmin (Flask) to Django 5 + Django Ninja. The migration adapts the reference implementation at `TMP/SercopPODAdminREFERECENE/` to the existing Django architecture.

## Architecture

The GPUBROKER Admin follows a layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Django Templates (HTML)                   │
│  index.html │ billing.html │ customers.html │ costs.html    │
├─────────────────────────────────────────────────────────────┤
│                    Static Assets (CSS/JS)                    │
│  admin.css │ admin.js                                        │
├─────────────────────────────────────────────────────────────┤
│                    Django Ninja API (/api/v2/)               │
│  dashboard │ pods │ customers │ billing │ costs │ payments  │
├─────────────────────────────────────────────────────────────┤
│                    Django Services                           │
│  PayPal │ Deploy │ Email │ Observability                    │
├─────────────────────────────────────────────────────────────┤
│                    Django ORM Models                         │
│  Subscription │ AdminUser │ Pod │ Transaction               │
├─────────────────────────────────────────────────────────────┤
│                    AWS Infrastructure                        │
│  DynamoDB │ ECS Fargate │ CloudWatch │ SES │ S3             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. PayPal Payment Service

**Location:** `gpubrokeradmin/services/payments/paypal.py`

**Interface:**
```python
class PayPalService:
    def __init__(self, mode: str = "sandbox"):
        """Initialize PayPal service with mode (sandbox/live)."""
        
    def create_order(self, amount: float, email: str, plan: str, 
                     ruc: str = "", name: str = "") -> dict:
        """Create PayPal order and return approval URL."""
        
    def capture_order(self, order_id: str) -> dict:
        """Capture approved PayPal order and return transaction details."""
        
    def is_configured(self) -> bool:
        """Check if PayPal credentials are configured."""
        
    def get_config_status(self) -> dict:
        """Return configuration status for diagnostics."""
```

**Dependencies:**
- `PAYPAL_CLIENT_ID` environment variable
- `PAYPAL_CLIENT_SECRET` environment variable
- `PAYPAL_MODE` environment variable (sandbox/live)

### 2. Admin Dashboard API

**Location:** `gpubrokeradmin/api/router.py`

**Endpoints:**
```
GET  /api/v2/admin/dashboard     - Dashboard KPIs and activity
GET  /api/v2/admin/pods          - List all pods
POST /api/v2/admin/pod/start     - Start a pod
POST /api/v2/admin/pod/stop      - Stop a pod
POST /api/v2/admin/pod/destroy   - Destroy a pod
GET  /api/v2/admin/pod/{id}/metrics - Pod AWS metrics
GET  /api/v2/admin/customers     - List all customers
GET  /api/v2/admin/customer/{email} - Customer details
GET  /api/v2/admin/billing       - List transactions
GET  /api/v2/admin/transaction/{id} - Transaction details
GET  /api/v2/admin/costs         - AWS costs and profitability
POST /api/v2/admin/resend-receipt - Resend receipt email
```

### 3. Admin Templates

**Location:** `gpubrokeradmin/templates/admin/`

**Files:**
- `index.html` - Dashboard with KPI cards, charts, activity feed
- `billing.html` - Transactions list with master-detail layout
- `customers.html` - Customers list with master-detail layout
- `costs.html` - AWS costs and profitability metrics

**Design System:**
- Geist font family (sans + mono)
- Material Symbols Rounded icons
- Glassmorphism cards with backdrop blur
- Green accent color (#22C55E)
- Full-screen modals with master-detail layout

### 4. Static Assets

**Location:** `gpubrokeradmin/static/gpubrokeradmin/`

**Files:**
- `css/admin.css` - Complete design system from reference
- `js/admin.js` - Dashboard logic, charts, modals, API calls

## Data Models

### Subscription (Existing)
```python
class Subscription(models.Model):
    api_key = models.CharField(primary_key=True)
    email = models.EmailField()
    name = models.CharField(max_length=255)
    plan = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    pod_id = models.CharField(max_length=100)
    pod_url = models.URLField()
    ruc = models.CharField(max_length=13, blank=True)
    amount_usd = models.DecimalField()
    transaction_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
```

### PayPal Transaction (In-Memory)
```python
# Stored in memory for callback matching
pending_transactions = {
    "order_id": {
        "email": str,
        "plan": str,
        "amount": float,
        "ruc": str,
        "name": str,
        "created_at": datetime
    }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: PayPal Order Creation Returns Valid Approval URL

*For any* valid payment request with amount > 0 and valid email, the PayPal service SHALL return a response containing an approval URL that starts with the PayPal domain.

**Validates: Requirements 1.1, 1.2**

### Property 2: PayPal Capture Returns Transaction Details

*For any* valid order ID that has been approved, the PayPal capture SHALL return a response containing transaction_id, amount, and email fields.

**Validates: Requirements 1.3, 1.4**

### Property 3: PayPal Mode Determines API Endpoint

*For any* PayPal service instance, the base URL SHALL be `api-m.sandbox.paypal.com` when mode is "sandbox" and `api-m.paypal.com` when mode is "live".

**Validates: Requirements 1.5**

### Property 4: Dashboard Authentication Redirect

*For any* request to the dashboard without a valid JWT token, the page SHALL redirect to the login page before rendering content.

**Validates: Requirements 2.6**

### Property 5: API Response Structure Consistency

*For any* successful API response from dashboard, pods, customers, or billing endpoints, the response SHALL contain a `success: true` field and the expected data structure.

**Validates: Requirements 2.1, 3.1, 4.1, 5.1**

## Error Handling

### PayPal Errors
- Missing credentials: Return `{"success": false, "error": "PayPal not configured"}`
- API errors: Return `{"success": false, "error": "<PayPal error message>"}`
- Network errors: Return `{"success": false, "error": "Connection failed"}`

### API Errors
- Unauthorized: Return 401 with `{"error": "Unauthorized"}`
- Not found: Return 404 with `{"error": "Resource not found"}`
- Server error: Return 500 with `{"error": "<error message>"}`

### Template Errors
- Missing token: Redirect to `/admin/login/`
- API failure: Display error state in UI with retry option

## Testing Strategy

### Unit Tests
- PayPal service configuration detection
- PayPal order creation with mocked API
- PayPal capture with mocked API
- API endpoint authentication
- API response structure validation

### Property-Based Tests
- PayPal URL generation for various modes
- API response structure consistency
- Authentication redirect behavior

### Integration Tests
- Full payment flow (sandbox mode)
- Dashboard data loading
- Pod lifecycle operations

**Testing Framework:** pytest with hypothesis for property-based testing

**Minimum Iterations:** 100 per property test
