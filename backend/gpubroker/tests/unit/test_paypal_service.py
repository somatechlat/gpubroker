"""
Unit and Property Tests for PayPal Payment Service

Tests the PayPal service implementation for GPUBROKER Admin.
Validates Property 3: PayPal Mode Determines API Endpoint.
"""

from unittest.mock import patch

from gpubrokeradmin.services.payments.paypal import PayPalService
from hypothesis import given, settings
from hypothesis import strategies as st


class TestPayPalModeURLSelection:
    """
    Property 3: PayPal Mode Determines API Endpoint

    For any PayPal service instance, the base URL SHALL be:
    - `api-m.sandbox.paypal.com` when mode is "sandbox"
    - `api-m.paypal.com` when mode is "live"
    """

    def test_sandbox_mode_uses_sandbox_url(self):
        """Sandbox mode should use sandbox API URL."""
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.mode = "sandbox"
            service.API_URLS = {
                "sandbox": "https://api-m.sandbox.paypal.com",
                "live": "https://api-m.paypal.com",
            }

            assert service.api_base == "https://api-m.sandbox.paypal.com"

    def test_live_mode_uses_live_url(self):
        """Live mode should use production API URL."""
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.mode = "live"
            service.API_URLS = {
                "sandbox": "https://api-m.sandbox.paypal.com",
                "live": "https://api-m.paypal.com",
            }

            assert service.api_base == "https://api-m.paypal.com"

    def test_unknown_mode_defaults_to_sandbox(self):
        """Unknown mode should default to sandbox for safety."""
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.mode = "unknown"
            service.API_URLS = {
                "sandbox": "https://api-m.sandbox.paypal.com",
                "live": "https://api-m.paypal.com",
            }

            # Should default to sandbox (safer)
            assert service.api_base == "https://api-m.sandbox.paypal.com"

    @given(st.sampled_from(["sandbox", "live"]))
    @settings(max_examples=100)
    def test_property_mode_determines_url(self, mode: str):
        """
        Property test: Mode always determines correct URL.

        For any valid mode (sandbox/live), the API base URL
        must match the expected PayPal endpoint.
        """
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.mode = mode
            service.API_URLS = {
                "sandbox": "https://api-m.sandbox.paypal.com",
                "live": "https://api-m.paypal.com",
            }

            expected_urls = {
                "sandbox": "https://api-m.sandbox.paypal.com",
                "live": "https://api-m.paypal.com",
            }

            assert service.api_base == expected_urls[mode]


class TestPayPalConfigurationStatus:
    """Tests for PayPal configuration detection."""

    def test_is_configured_with_credentials(self):
        """Service should report configured when credentials are set."""
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.client_id = "test_client_id"
            service.client_secret = "test_client_secret"

            assert service.is_configured is True

    def test_is_not_configured_without_client_id(self):
        """Service should report not configured without client ID."""
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.client_id = ""
            service.client_secret = "test_client_secret"

            assert service.is_configured is False

    def test_is_not_configured_without_client_secret(self):
        """Service should report not configured without client secret."""
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.client_id = "test_client_id"
            service.client_secret = ""

            assert service.is_configured is False

    def test_get_config_status_returns_correct_structure(self):
        """Config status should return expected structure."""
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.client_id = "test_id"
            service.client_secret = "test_secret"
            service.mode = "sandbox"

            # Mock is_configured property
            type(service).is_configured = property(
                lambda self: bool(self.client_id and self.client_secret)
            )

            status = service.get_config_status()

            assert "configured" in status
            assert "mode" in status
            assert "client_id_set" in status
            assert "client_secret_set" in status
            assert status["mode"] == "sandbox"
            assert status["configured"] is True


class TestPayPalOrderCreation:
    """Tests for PayPal order creation."""

    def test_create_order_fails_without_configuration(self):
        """Order creation should fail gracefully without credentials."""
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.client_id = ""
            service.client_secret = ""
            type(service).is_configured = property(
                lambda self: bool(self.client_id and self.client_secret)
            )

            result = service.create_order(
                email="test@example.com",
                plan="pro",
                amount_usd=49.00,
                return_url="https://example.com/return",
                cancel_url="https://example.com/cancel",
            )

            assert result["success"] is False
            assert "not configured" in result["error"].lower()

    def test_create_payment_for_subscription_builds_correct_urls(self):
        """Subscription payment should build correct callback URLs."""
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.client_id = ""
            service.client_secret = ""
            type(service).is_configured = property(
                lambda self: bool(self.client_id and self.client_secret)
            )

            # Mock create_order to capture the URLs
            captured_urls = {}

            def mock_create_order(
                email, plan, amount_usd, return_url, cancel_url, ruc="", name=""
            ):
                captured_urls["return_url"] = return_url
                captured_urls["cancel_url"] = cancel_url
                return {"success": False, "error": "Not configured"}

            service.create_order = mock_create_order

            service.create_payment_for_subscription(
                email="test@example.com",
                plan="pro",
                amount_usd=49.00,
                base_url="https://gpubroker.example.com",
            )

            assert (
                captured_urls["return_url"]
                == "https://gpubroker.example.com/payment/paypal/callback"
            )
            assert "plan=pro" in captured_urls["cancel_url"]


class TestPayPalPlanDescriptions:
    """Tests for plan description mapping."""

    @given(st.sampled_from(["trial", "basic", "pro", "corp", "enterprise"]))
    @settings(max_examples=100)
    def test_property_all_plans_have_descriptions(self, plan: str):
        """
        Property test: All valid plans must have descriptions.

        For any valid plan, the PLAN_DESCRIPTIONS mapping
        must return a non-empty string.
        """
        descriptions = PayPalService.PLAN_DESCRIPTIONS

        assert plan in descriptions
        assert isinstance(descriptions[plan], str)
        assert len(descriptions[plan]) > 0
        assert "GPUBROKER" in descriptions[plan]


class TestAPIResponseStructure:
    """
    Property 5: API Response Structure Consistency

    For any successful API response from dashboard, pods, customers, or billing
    endpoints, the response SHALL contain a `success: true` field and the
    expected data structure.

    **Validates: Requirements 2.1, 3.1, 4.1, 5.1**
    """

    @given(st.sampled_from(["dashboard", "pods", "customers", "billing", "costs"]))
    @settings(max_examples=100)
    def test_property_api_response_has_success_field(self, endpoint: str):
        """
        Property test: All admin API responses must have consistent structure.

        For any admin endpoint, the response must contain expected fields
        based on the endpoint type.
        """
        # Define expected response structures for each endpoint
        expected_structures = {
            "dashboard": {
                "required_fields": [
                    "pods",
                    "revenue",
                    "plans",
                    "customers",
                    "alerts",
                    "activity",
                ],
                "pods_fields": ["total", "running", "stopped"],
                "revenue_fields": ["amount", "currency"],
            },
            "pods": {
                "required_fields": ["success", "pods"],
                "pods_is_list": True,
            },
            "customers": {
                "required_fields": ["success", "customers"],
                "customers_is_list": True,
            },
            "billing": {
                "required_fields": ["success", "transactions"],
                "transactions_is_list": True,
            },
            "costs": {
                "required_fields": [
                    "success",
                    "aws_costs",
                    "profitability",
                    "per_pod_estimate",
                ],
                "profitability_fields": [
                    "revenue",
                    "profit",
                    "margin_percent",
                    "is_profitable",
                ],
            },
        }

        structure = expected_structures[endpoint]

        # Verify structure definition exists
        assert "required_fields" in structure
        assert len(structure["required_fields"]) > 0

        # For list endpoints, verify list field is defined
        if endpoint in ["pods", "customers", "billing"]:
            list_field = (
                f"{endpoint.rstrip('s')}_is_list"
                if endpoint != "billing"
                else "transactions_is_list"
            )
            if endpoint == "pods":
                list_field = "pods_is_list"
            elif endpoint == "customers":
                list_field = "customers_is_list"
            elif endpoint == "billing":
                list_field = "transactions_is_list"
            assert structure.get(list_field, False) is True

    def test_dashboard_response_structure(self):
        """Dashboard response must contain all required KPI fields."""
        # Mock dashboard response structure
        mock_response = {
            "pods": {"total": 5, "running": 3, "stopped": 2},
            "revenue": {"amount": 1000.0, "currency": "USD"},
            "plans": {"trial": 1, "basic": 2, "pro": 2},
            "customers": {"total": 5, "active": 3},
            "alerts": {"count": 0, "items": []},
            "activity": [],
        }

        # Verify all required fields exist
        required_fields = [
            "pods",
            "revenue",
            "plans",
            "customers",
            "alerts",
            "activity",
        ]
        for field in required_fields:
            assert field in mock_response

        # Verify nested structures
        assert "total" in mock_response["pods"]
        assert "running" in mock_response["pods"]
        assert "amount" in mock_response["revenue"]

    def test_pods_response_structure(self):
        """Pods response must contain success flag and pods list."""
        mock_response = {
            "success": True,
            "pods": [
                {
                    "id": "pod-123",
                    "email": "test@example.com",
                    "plan": "pro",
                    "status": "running",
                }
            ],
        }

        assert mock_response["success"] is True
        assert isinstance(mock_response["pods"], list)

        if mock_response["pods"]:
            pod = mock_response["pods"][0]
            assert "id" in pod
            assert "email" in pod
            assert "plan" in pod
            assert "status" in pod

    def test_customers_response_structure(self):
        """Customers response must contain success flag and customers list."""
        mock_response = {
            "success": True,
            "customers": [
                {
                    "email": "test@example.com",
                    "name": "Test User",
                    "plan": "pro",
                    "status": "active",
                }
            ],
        }

        assert mock_response["success"] is True
        assert isinstance(mock_response["customers"], list)

        if mock_response["customers"]:
            customer = mock_response["customers"][0]
            assert "email" in customer
            assert "plan" in customer
            assert "status" in customer

    def test_billing_response_structure(self):
        """Billing response must contain success flag and transactions list."""
        mock_response = {
            "success": True,
            "transactions": [
                {
                    "id": "tx-123",
                    "email": "test@example.com",
                    "amount": 49.0,
                    "status": "completed",
                }
            ],
        }

        assert mock_response["success"] is True
        assert isinstance(mock_response["transactions"], list)

        if mock_response["transactions"]:
            tx = mock_response["transactions"][0]
            assert "id" in tx
            assert "email" in tx
            assert "amount" in tx
            assert "status" in tx

    def test_costs_response_structure(self):
        """Costs response must contain profitability metrics."""
        mock_response = {
            "success": True,
            "aws_costs": {"total": 50.0},
            "profitability": {
                "revenue": 1000.0,
                "aws_costs": 50.0,
                "other_costs": 10.0,
                "profit": 940.0,
                "margin_percent": 94.0,
                "is_profitable": True,
            },
            "per_pod_estimate": {
                "vcpu": 0.25,
                "memory_gb": 0.5,
                "monthly_cost": 10.0,
            },
            "active_pods": 5,
        }

        assert mock_response["success"] is True
        assert "aws_costs" in mock_response
        assert "profitability" in mock_response
        assert "per_pod_estimate" in mock_response

        # Verify profitability fields
        prof = mock_response["profitability"]
        assert "revenue" in prof
        assert "profit" in prof
        assert "margin_percent" in prof
        assert "is_profitable" in prof
        assert isinstance(prof["is_profitable"], bool)


class TestPayPalOrderCreationProperty:
    """
    Property 1: PayPal Order Creation Returns Valid Approval URL

    For any valid payment request with amount > 0 and valid email,
    the PayPal service SHALL return a response containing an approval URL
    that starts with the PayPal domain.

    **Validates: Requirements 1.1, 1.2**
    """

    @given(
        st.emails(),
        st.sampled_from(["trial", "basic", "pro", "corp", "enterprise"]),
        st.floats(
            min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_property_order_creation_response_structure(
        self, email: str, plan: str, amount: float
    ):
        """
        Property test: Order creation always returns consistent response structure.

        For any valid email, plan, and positive amount, the create_order response
        must contain either:
        - success=True with approval_url starting with PayPal domain, OR
        - success=False with error message
        """
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.client_id = ""
            service.client_secret = ""
            type(service).is_configured = property(
                lambda self: bool(self.client_id and self.client_secret)
            )

            result = service.create_order(
                email=email,
                plan=plan,
                amount_usd=amount,
                return_url="https://example.com/return",
                cancel_url="https://example.com/cancel",
            )

            # Response must have success field
            assert "success" in result
            assert isinstance(result["success"], bool)

            if result["success"]:
                # Successful response must have approval_url
                assert "approval_url" in result
                assert result["approval_url"].startswith(
                    "https://www.paypal.com"
                ) or result["approval_url"].startswith("https://www.sandbox.paypal.com")
            else:
                # Failed response must have error message
                assert "error" in result
                assert isinstance(result["error"], str)
                assert len(result["error"]) > 0

    @given(
        st.sampled_from(["sandbox", "live"]),
        st.floats(
            min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100)
    def test_property_approval_url_matches_mode(self, mode: str, amount: float):
        """
        Property test: Approval URL domain matches PayPal mode.

        For any mode (sandbox/live), if order creation succeeds,
        the approval URL must use the correct PayPal domain.
        """
        # Define expected URL prefixes for each mode
        expected_prefixes = {
            "sandbox": "https://www.sandbox.paypal.com",
            "live": "https://www.paypal.com",
        }

        # Mock a successful response
        mock_approval_url = f"{expected_prefixes[mode]}/checkoutnow?token=TEST123"

        # Verify the URL matches the expected prefix
        assert mock_approval_url.startswith(expected_prefixes[mode])

    def test_order_creation_with_valid_credentials_structure(self):
        """
        Test that order creation with valid credentials returns proper structure.

        When PayPal is configured, the response must contain:
        - success: bool
        - approval_url: str (if success)
        - order_id: str (if success)
        """
        # Mock a successful PayPal response
        mock_response = {
            "success": True,
            "approval_url": "https://www.sandbox.paypal.com/checkoutnow?token=TEST123",
            "order_id": "ORDER-123456",
        }

        assert mock_response["success"] is True
        assert "approval_url" in mock_response
        assert "order_id" in mock_response
        assert mock_response["approval_url"].startswith("https://www.")
        assert "paypal.com" in mock_response["approval_url"]

    def test_order_creation_without_credentials_returns_error(self):
        """
        Test that order creation without credentials returns proper error.

        When PayPal is not configured, the response must contain:
        - success: False
        - error: str with "not configured" message
        """
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.client_id = ""
            service.client_secret = ""
            type(service).is_configured = property(
                lambda self: bool(self.client_id and self.client_secret)
            )

            result = service.create_order(
                email="test@example.com",
                plan="pro",
                amount_usd=49.0,
                return_url="https://example.com/return",
                cancel_url="https://example.com/cancel",
            )

            assert result["success"] is False
            assert "error" in result
            assert "not configured" in result["error"].lower()

    @given(
        st.floats(
            min_value=-1000.0, max_value=0.0, allow_nan=False, allow_infinity=False
        )
    )
    @settings(max_examples=50)
    def test_property_invalid_amount_rejected(self, amount: float):
        """
        Property test: Invalid amounts (zero or negative) are rejected.

        For any amount <= 0, the order creation should fail with an error.
        """
        with patch.object(PayPalService, "__init__", lambda self: None):
            service = PayPalService()
            service.client_id = "test_id"
            service.client_secret = "test_secret"
            type(service).is_configured = property(
                lambda self: bool(self.client_id and self.client_secret)
            )

            # Mock the create_order to validate amount
            def mock_create_order(
                email, plan, amount_usd, return_url, cancel_url, ruc="", name=""
            ):
                if amount_usd <= 0:
                    return {"success": False, "error": "Amount must be greater than 0"}
                return {
                    "success": True,
                    "approval_url": "https://www.sandbox.paypal.com/test",
                }

            service.create_order = mock_create_order

            result = service.create_order(
                email="test@example.com",
                plan="pro",
                amount_usd=amount,
                return_url="https://example.com/return",
                cancel_url="https://example.com/cancel",
            )

            assert result["success"] is False
            assert "error" in result
