# Implementation Plan: GPUBROKER POD Admin Migration

## Overview

This plan completes the migration of SercopPODAdmin (Flask) to Django 5 + Django Ninja. Tasks focus on copying and adapting the reference implementation to the existing Django architecture.

## Tasks

- [x] 1. Copy and adapt PayPal payment service
  - [x] 1.1 Create PayPal service at `gpubrokeradmin/services/payments/paypal.py`
    - Copy logic from `TMP/SercopPODAdminREFERECENE/api/payment_paypal.py`
    - Adapt to Django patterns (settings, logging)
    - Support sandbox/live modes via `PAYPAL_MODE` env var
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_
  - [x] 1.2 Write property test for PayPal mode URL selection
    - **Property 3: PayPal Mode Determines API Endpoint**
    - **Validates: Requirements 1.5**

- [x] 2. Copy and adapt admin dashboard template
  - [x] 2.1 Update `gpubrokeradmin/templates/admin/index.html`
    - Copy full HTML from `TMP/SercopPODAdminREFERECENE/admin/index.html`
    - Adapt URLs to Django patterns (`/admin/`, `/admin/login/`)
    - Add Django template tags (`{% load static %}`)
    - Include KPI cards, charts, activity feed, modals
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 3. Copy and adapt admin CSS
  - [x] 3.1 Update `gpubrokeradmin/static/gpubrokeradmin/css/admin.css`
    - Copy full CSS from `TMP/SercopPODAdminREFERECENE/admin/css/admin.css`
    - Include glassmorphism, master-detail, full-screen modals
    - _Requirements: 2.1, 3.1, 4.1, 5.1_

- [x] 4. Copy and adapt admin JavaScript
  - [x] 4.1 Update `gpubrokeradmin/static/gpubrokeradmin/js/admin.js`
    - Copy full JS from `TMP/SercopPODAdminREFERECENE/admin/js/admin.js`
    - Adapt API endpoints to `/api/v2/admin/`
    - Adapt URLs to Django patterns
    - Include charts, modals, pod lifecycle actions
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 5. Checkpoint - Verify dashboard renders
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create billing template
  - [x] 6.1 Create `gpubrokeradmin/templates/admin/billing.html`
    - Adapt billing modal from reference to full page
    - Include master-detail layout for transactions
    - Include transaction details panel
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 7. Create customers template
  - [x] 7.1 Create `gpubrokeradmin/templates/admin/customers.html`
    - Adapt customers modal from reference to full page
    - Include master-detail layout for customers
    - Include customer details panel with pod and payment info
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 8. Create costs template
  - [x] 8.1 Create `gpubrokeradmin/templates/admin/costs.html`
    - Create costs page with AWS costs breakdown
    - Include profitability metrics
    - Include per-pod cost estimates
    - Include profit margin gauge
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 9. Add API endpoints for admin dashboard
  - [x] 9.1 Add dashboard endpoint to `gpubrokeradmin/api/router.py`
    - `GET /api/v2/admin/dashboard` - KPIs, activity, charts data
    - Adapt from `TMP/SercopPODAdminREFERECENE/app.py` `/api/admin/dashboard`
    - _Requirements: 2.1_
  - [x] 9.2 Add pods endpoints
    - `GET /api/v2/admin/pods` - List all pods
    - `POST /api/v2/admin/pod/start` - Start pod
    - `POST /api/v2/admin/pod/stop` - Stop pod
    - `POST /api/v2/admin/pod/destroy` - Destroy pod
    - `GET /api/v2/admin/pod/{id}/metrics` - Pod metrics
    - _Requirements: 2.1_
  - [x] 9.3 Add customers endpoints
    - `GET /api/v2/admin/customers` - List customers
    - `GET /api/v2/admin/customer/{email}` - Customer details
    - _Requirements: 4.1, 4.2_
  - [x] 9.4 Add billing endpoints
    - `GET /api/v2/admin/billing` - List transactions
    - `GET /api/v2/admin/transaction/{id}` - Transaction details
    - `POST /api/v2/admin/resend-receipt` - Resend receipt
    - _Requirements: 3.1, 3.2, 3.4_
  - [x] 9.5 Add costs endpoint
    - `GET /api/v2/admin/costs` - AWS costs and profitability
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 9.6 Write property test for API response structure
    - **Property 5: API Response Structure Consistency**
    - **Validates: Requirements 2.1, 3.1, 4.1, 5.1**

- [x] 10. Add PayPal payment endpoints
  - [x] 10.1 Add PayPal endpoints to API router
    - `POST /api/v2/payment/paypal` - Create order
    - `POST /api/v2/payment/paypal/capture/{order_id}` - Capture order
    - `GET /api/v2/payment/paypal/status` - Config status
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_
  - [x] 10.2 Write property test for PayPal order creation
    - **Property 1: PayPal Order Creation Returns Valid Approval URL**
    - **Validates: Requirements 1.1, 1.2**

- [x] 11. Checkpoint - Verify API endpoints work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Update Django configuration
  - [x] 12.1 Verify INSTALLED_APPS includes admin apps
    - `gpubrokeradmin.apps.auth`
    - `gpubrokeradmin.apps.subscriptions`
    - _Requirements: 6.1, 6.2_
  - [x] 12.2 Verify URL configuration
    - gpubrokeradmin URLs in `config/urls.py`
    - API routers in `config/api/__init__.py`
    - _Requirements: 6.3, 6.4_
  - [x] 12.3 Verify template and static configuration
    - Template directories in TEMPLATES setting
    - Static directories in STATICFILES_DIRS
    - _Requirements: 6.5, 6.6_

- [x] 13. Final checkpoint - Full integration test
  - Ensure all tests pass, ask the user if questions arise.
  - Test dashboard loads with real data
  - Test pod lifecycle actions
  - Test payment flow (sandbox)

## Notes

- All tasks including property-based tests are required
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Reference code is at `TMP/SercopPODAdminREFERECENE/` - copy and adapt, don't rewrite
