# Requirements Document

## Introduction

This document specifies the REMAINING requirements for completing the GPUBROKER POD Admin migration from SercopPODAdmin (Flask) to Django 5 + Django Ninja. Most core functionality is already implemented - this focuses on what's MISSING.

## Already Implemented (DO NOT RE-IMPLEMENT)

The following are ALREADY DONE in Django:
- ✅ Admin authentication (`gpubrokeradmin/apps/auth/`) - JWT, sessions, audit logs
- ✅ Subscription management (`gpubrokeradmin/apps/subscriptions/`) - Django ORM
- ✅ Pod deployment service (`gpubrokeradmin/services/deploy.py`) - AWS ECS Fargate
- ✅ Email service (`gpubrokeradmin/services/email.py`) - AWS SES
- ✅ API router (`gpubrokeradmin/api/router.py`) - Django Ninja
- ✅ RUC/Cedula validation (in API router)
- ✅ Basic templates (login, checkout, activate, provisioning, ready)

## Glossary

- **GPUBROKER_Admin**: The Django admin application for managing GPU broker subscriptions and pods
- **Pod**: A deployed ECS Fargate container running GPUBROKER for a customer
- **PayPal_Service**: PayPal REST API v2 integration for payments
- **Admin_Dashboard**: Web interface for administrators

## Requirements

### Requirement 1: PayPal Payment Service

**User Story:** As a customer, I want to pay with PayPal, so that I can purchase a subscription.

#### Acceptance Criteria

1. WHEN a payment is initiated, THE PayPal_Service SHALL create an order via PayPal REST API v2
2. THE PayPal_Service SHALL return an approval URL for customer redirect
3. WHEN customer approves payment, THE PayPal_Service SHALL capture the order
4. IF payment capture succeeds, THEN THE PayPal_Service SHALL return transaction ID and details
5. THE PayPal_Service SHALL support both sandbox and live modes via PAYPAL_MODE environment variable
6. IF PayPal credentials are not configured, THEN THE PayPal_Service SHALL return configuration error
7. THE PayPal_Service SHALL store pending transactions in memory for callback matching

### Requirement 2: Admin Dashboard Template

**User Story:** As an administrator, I want a dashboard interface, so that I can monitor business metrics.

#### Acceptance Criteria

1. THE Dashboard_Template SHALL display KPI cards (pods, revenue, customers, alerts)
2. THE Dashboard_Template SHALL display revenue chart (monthly)
3. THE Dashboard_Template SHALL display plan distribution chart
4. THE Dashboard_Template SHALL display activity feed with recent events
5. THE Dashboard_Template SHALL include modals for pods, revenue, customers, alerts details
6. THE Dashboard_Template SHALL redirect to login if JWT token is missing
7. THE Dashboard_Template SHALL support sandbox/live environment toggle

### Requirement 3: Admin Billing Template

**User Story:** As an administrator, I want to view billing information, so that I can track transactions.

#### Acceptance Criteria

1. THE Billing_Template SHALL display all transactions list
2. THE Billing_Template SHALL display transaction details when selected
3. THE Billing_Template SHALL show customer, pod, and payment information
4. THE Billing_Template SHALL support resending receipt emails
5. THE Billing_Template SHALL link to customer and pod detail views

### Requirement 4: Admin Customers Template

**User Story:** As an administrator, I want to view customer information, so that I can manage accounts.

#### Acceptance Criteria

1. THE Customers_Template SHALL display all customers list
2. THE Customers_Template SHALL display customer details when selected
3. THE Customers_Template SHALL show subscription, pod, and payment history
4. THE Customers_Template SHALL link to pod and billing views

### Requirement 5: Admin Costs Template

**User Story:** As an administrator, I want to view costs and profitability, so that I can monitor business health.

#### Acceptance Criteria

1. THE Costs_Template SHALL display AWS costs breakdown
2. THE Costs_Template SHALL display profitability metrics (revenue, costs, profit, margin)
3. THE Costs_Template SHALL display per-pod cost estimates
4. THE Costs_Template SHALL display profit margin gauge
5. THE Costs_Template SHALL auto-refresh every 60 seconds

### Requirement 6: Django Integration

**User Story:** As a developer, I want the admin app fully integrated with Django, so that it works correctly.

#### Acceptance Criteria

1. THE gpubrokeradmin.apps.auth app SHALL be registered in INSTALLED_APPS
2. THE gpubrokeradmin.apps.subscriptions app SHALL be registered in INSTALLED_APPS
3. THE gpubrokeradmin URLs SHALL be included in config/urls.py
4. THE gpubrokeradmin API routers SHALL be registered in config/api/__init__.py
5. THE TEMPLATES setting SHALL include gpubrokeradmin template directories
6. THE STATICFILES_DIRS SHALL include gpubrokeradmin static directories

### Requirement 7: Cleanup

**User Story:** As a developer, I want the TMP folder removed, so that the codebase is clean.

#### Acceptance Criteria

1. WHEN migration is complete, THE TMP/SercopPODAdminREFERECENE folder SHALL be deleted
2. THE TMP/agent-zero folder SHALL remain (reference for Agent Zero integration)
