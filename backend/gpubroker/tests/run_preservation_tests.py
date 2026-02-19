#!/usr/bin/env python
"""
Standalone test runner for preservation property tests.

This script runs the preservation tests WITHOUT Django setup to avoid
conflicts with the OLD architecture in Django settings.

These tests verify POD SaaS structure and code patterns exist and are
accessible, confirming baseline behavior to preserve.
"""

import sys
from pathlib import Path

# Add POD SaaS to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
POD_SAAS_PATH = PROJECT_ROOT / "backend" / "gpubroker" / "gpubrokerpod"
sys.path.insert(0, str(POD_SAAS_PATH))

# Test counters
tests_passed = 0
tests_failed = 0
failures = []


def test_result(test_name, passed, error_msg=None):
    """Record test result."""
    global tests_passed, tests_failed, failures
    if passed:
        tests_passed += 1
        print(f"✓ {test_name}")
    else:
        tests_failed += 1
        failures.append((test_name, error_msg))
        print(f"✗ {test_name}")
        if error_msg:
            print(f"  Error: {error_msg}")


def run_tests():
    """Run all preservation tests."""
    print("=" * 70)
    print("PRESERVATION PROPERTY TESTS - POD SaaS Structure Verification")
    print("=" * 70)
    print()

    # ========================================================================
    # PROPERTY 2.1: Authentication Preservation Tests
    # ========================================================================
    print("Testing Authentication Preservation...")

    # Test 2.1.1: User model structure
    try:
        user_model_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "auth_app"
            / "models.py"
        )
        assert (
            user_model_path.exists()
        ), f"User model file should exist at {user_model_path}"

        model_content = user_model_path.read_text()
        assert "class User(" in model_content, "User model class should be defined"

        expected_fields = [
            "email",
            "password_hash",
            "full_name",
            "organization",
            "is_active",
            "is_verified",
        ]
        for field in expected_fields:
            assert field in model_content, f"User model should have '{field}' field"

        assert (
            "def set_password(" in model_content
        ), "User model should have set_password method"
        assert (
            "def check_password(" in model_content
        ), "User model should have check_password method"

        test_result("2.1.1 User model structure preserved", True)
    except AssertionError as e:
        test_result("2.1.1 User model structure preserved", False, str(e))

    # Test 2.1.2: Password hashing behavior
    try:
        user_model_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "auth_app"
            / "models.py"
        )
        model_content = user_model_path.read_text()

        assert (
            "passlib" in model_content or "argon2" in model_content
        ), "User model should use passlib or argon2"
        test_result("2.1.2 Password hashing behavior preserved", True)
    except AssertionError as e:
        test_result("2.1.2 Password hashing behavior preserved", False, str(e))

    print()

    # ========================================================================
    # PROPERTY 2.2: Provider Data Preservation Tests
    # ========================================================================
    print("Testing Provider Data Preservation...")

    # Test 2.2.1: Provider model structure
    try:
        provider_model_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "providers"
            / "models.py"
        )
        assert provider_model_path.exists(), "Provider model file should exist"

        model_content = provider_model_path.read_text()
        assert (
            "class Provider(" in model_content
        ), "Provider model class should be defined"

        expected_fields = [
            "name",
            "display_name",
            "api_base_url",
            "status",
            "reliability_score",
        ]
        for field in expected_fields:
            assert field in model_content, f"Provider model should have '{field}' field"

        test_result("2.2.1 Provider model structure preserved", True)
    except AssertionError as e:
        test_result("2.2.1 Provider model structure preserved", False, str(e))

    # Test 2.2.2: GPU offer model structure
    try:
        provider_model_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "providers"
            / "models.py"
        )
        model_content = provider_model_path.read_text()

        assert (
            "class GPUOffer(" in model_content
        ), "GPUOffer model class should be defined"

        expected_fields = [
            "gpu_type",
            "gpu_memory_gb",
            "cpu_cores",
            "ram_gb",
            "price_per_hour",
            "region",
        ]
        for field in expected_fields:
            assert field in model_content, f"GPUOffer model should have '{field}' field"

        test_result("2.2.2 GPU offer model structure preserved", True)
    except AssertionError as e:
        test_result("2.2.2 GPU offer model structure preserved", False, str(e))

    print()

    # ========================================================================
    # PROPERTY 2.3: Billing Preservation Tests
    # ========================================================================
    print("Testing Billing Preservation...")

    # Test 2.3.1: Billing models structure
    try:
        billing_model_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "billing"
            / "models.py"
        )
        assert billing_model_path.exists(), "Billing model file should exist"

        model_content = billing_model_path.read_text()
        assert (
            "class Subscription(" in model_content
        ), "Subscription model should be defined"
        assert (
            "class PaymentMethod(" in model_content or "class Payment(" in model_content
        ), "Payment/PaymentMethod model should be defined"
        assert "class Invoice(" in model_content, "Invoice model should be defined"

        test_result("2.3.1 Billing models structure preserved", True)
    except AssertionError as e:
        test_result("2.3.1 Billing models structure preserved", False, str(e))

    # Test 2.3.2: Billing services structure
    try:
        stripe_service_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "billing"
            / "stripe_service.py"
        )
        email_service_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "billing"
            / "email_service.py"
        )

        assert stripe_service_path.exists(), "Stripe service file should exist"
        assert email_service_path.exists(), "Email service file should exist"

        stripe_content = stripe_service_path.read_text()
        assert (
            "def create_customer(" in stripe_content
        ), "stripe_service should have create_customer function"

        test_result("2.3.2 Billing services structure preserved", True)
    except AssertionError as e:
        test_result("2.3.2 Billing services structure preserved", False, str(e))

    print()

    # ========================================================================
    # PROPERTY 2.4: Deployment Preservation Tests
    # ========================================================================
    print("Testing Deployment Preservation...")

    # Test 2.4.1: Deployment models structure
    try:
        deployment_model_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "deployment"
            / "models.py"
        )
        assert deployment_model_path.exists(), "Deployment model file should exist"

        model_content = deployment_model_path.read_text()
        assert (
            "class PodDeploymentConfig(" in model_content
            or "class Deployment(" in model_content
        ), "Deployment/PodDeploymentConfig model should be defined"

        expected_fields = ["user_id", "status", "gpu_type"]
        for field in expected_fields:
            assert (
                field in model_content
            ), f"Deployment model should have '{field}' field"

        test_result("2.4.1 Deployment models structure preserved", True)
    except AssertionError as e:
        test_result("2.4.1 Deployment models structure preserved", False, str(e))

    # Test 2.4.2: Deployment services structure
    try:
        deployment_services_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "deployment"
            / "services.py"
        )
        assert (
            deployment_services_path.exists()
        ), "Deployment services file should exist"

        services_content = deployment_services_path.read_text()
        # Check for any deployment-related functions
        assert (
            "def " in services_content
        ), "deployment services should have functions defined"

        test_result("2.4.2 Deployment services structure preserved", True)
    except AssertionError as e:
        test_result("2.4.2 Deployment services structure preserved", False, str(e))

    # Test 2.4.3: Pod config models structure
    try:
        pod_config_model_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "pod_config"
            / "models.py"
        )
        assert pod_config_model_path.exists(), "PodConfig model file should exist"

        model_content = pod_config_model_path.read_text()
        # Check for any model class definition
        assert (
            "class " in model_content and "models.Model" in model_content
        ), "Pod config should have model classes defined"

        test_result("2.4.3 Pod config models structure preserved", True)
    except AssertionError as e:
        test_result("2.4.3 Pod config models structure preserved", False, str(e))

    print()

    # ========================================================================
    # PROPERTY 2.5: Dashboard Preservation Tests
    # ========================================================================
    print("Testing Dashboard Preservation...")

    # Test 2.5.1: Dashboard services structure
    try:
        dashboard_services_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "dashboard"
            / "services.py"
        )
        assert dashboard_services_path.exists(), "Dashboard services file should exist"

        services_content = dashboard_services_path.read_text()
        assert (
            "def get_" in services_content
        ), "dashboard services should have getter functions"

        test_result("2.5.1 Dashboard services structure preserved", True)
    except AssertionError as e:
        test_result("2.5.1 Dashboard services structure preserved", False, str(e))

    # Test 2.5.2: Dashboard schemas structure
    try:
        dashboard_schemas_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "dashboard"
            / "schemas.py"
        )
        assert dashboard_schemas_path.exists(), "Dashboard schemas file should exist"

        test_result("2.5.2 Dashboard schemas structure preserved", True)
    except AssertionError as e:
        test_result("2.5.2 Dashboard schemas structure preserved", False, str(e))

    print()

    # ========================================================================
    # PROPERTY 2.6: Websocket Gateway Preservation Tests
    # ========================================================================
    print("Testing Websocket Gateway Preservation...")

    # Test 2.6.1: Websocket routing structure
    try:
        websocket_routing_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "websocket_gateway"
            / "routing.py"
        )
        assert websocket_routing_path.exists(), "Websocket routing file should exist"

        routing_content = websocket_routing_path.read_text()
        assert (
            "websocket_urlpatterns" in routing_content
        ), "websocket_gateway routing should have websocket_urlpatterns"

        test_result("2.6.1 Websocket routing structure preserved", True)
    except AssertionError as e:
        test_result("2.6.1 Websocket routing structure preserved", False, str(e))

    # Test 2.6.2: Websocket consumers structure
    try:
        websocket_consumers_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "websocket_gateway"
            / "consumers.py"
        )
        assert (
            websocket_consumers_path.exists()
        ), "Websocket consumers file should exist"

        consumers_content = websocket_consumers_path.read_text()
        assert (
            "Consumer" in consumers_content
        ), "websocket_gateway consumers should have Consumer classes"
        assert (
            "def connect(" in consumers_content
        ), "Consumer should have connect method"
        assert (
            "def disconnect(" in consumers_content
        ), "Consumer should have disconnect method"

        test_result("2.6.2 Websocket consumers structure preserved", True)
    except AssertionError as e:
        test_result("2.6.2 Websocket consumers structure preserved", False, str(e))

    print()

    # ========================================================================
    # PROPERTY 2.7: API Endpoint Preservation Tests
    # ========================================================================
    print("Testing API Endpoint Preservation...")

    # Test 2.7.1: Provider API structure
    try:
        provider_api_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "providers"
            / "api.py"
        )
        assert provider_api_path.exists(), "Provider API file should exist"

        api_content = provider_api_path.read_text()
        assert "router" in api_content, "provider API should have router"

        test_result("2.7.1 Provider API structure preserved", True)
    except AssertionError as e:
        test_result("2.7.1 Provider API structure preserved", False, str(e))

    # Test 2.7.2: Billing API structure
    try:
        billing_api_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "billing"
            / "api.py"
        )
        assert billing_api_path.exists(), "Billing API file should exist"

        api_content = billing_api_path.read_text()
        assert "router" in api_content, "billing API should have router"

        test_result("2.7.2 Billing API structure preserved", True)
    except AssertionError as e:
        test_result("2.7.2 Billing API structure preserved", False, str(e))

    # Test 2.7.3: Deployment API structure
    try:
        deployment_api_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "deployment"
            / "api.py"
        )
        assert deployment_api_path.exists(), "Deployment API file should exist"

        api_content = deployment_api_path.read_text()
        assert "router" in api_content, "deployment API should have router"

        test_result("2.7.3 Deployment API structure preserved", True)
    except AssertionError as e:
        test_result("2.7.3 Deployment API structure preserved", False, str(e))

    # Test 2.7.4: Dashboard API structure
    try:
        dashboard_api_path = (
            PROJECT_ROOT
            / "backend"
            / "gpubroker"
            / "gpubrokerpod"
            / "gpubrokerapp"
            / "apps"
            / "dashboard"
            / "api.py"
        )
        assert dashboard_api_path.exists(), "Dashboard API file should exist"

        api_content = dashboard_api_path.read_text()
        assert "router" in api_content, "dashboard API should have router"

        test_result("2.7.4 Dashboard API structure preserved", True)
    except AssertionError as e:
        test_result("2.7.4 Dashboard API structure preserved", False, str(e))

    print()

    # ========================================================================
    # PROPERTY 2.8: Overall System Integrity Tests
    # ========================================================================
    print("Testing Overall System Integrity...")

    # Test 2.8.1: POD SaaS directory structure
    try:
        pod_saas_base = PROJECT_ROOT / "backend" / "gpubroker" / "gpubrokerpod"
        assert pod_saas_base.exists(), "POD SaaS base directory should exist"

        gpubrokerapp = pod_saas_base / "gpubrokerapp"
        assert gpubrokerapp.exists(), "POD SaaS gpubrokerapp directory should exist"

        apps_dir = gpubrokerapp / "apps"
        assert apps_dir.exists(), "POD SaaS apps directory should exist"

        expected_apps = [
            "auth_app",
            "providers",
            "billing",
            "deployment",
            "dashboard",
            "websocket_gateway",
            "pod_config",
        ]

        for app_name in expected_apps:
            app_path = apps_dir / app_name
            assert app_path.exists(), f"POD SaaS app directory should exist: {app_path}"

        test_result("2.8.1 POD SaaS directory structure intact", True)
    except AssertionError as e:
        test_result("2.8.1 POD SaaS directory structure intact", False, str(e))

    # Test 2.8.2: All POD SaaS apps importable
    try:
        pod_saas_apps = [
            "gpubrokerapp.apps.auth_app",
            "gpubrokerapp.apps.providers",
            "gpubrokerapp.apps.billing",
            "gpubrokerapp.apps.deployment",
            "gpubrokerapp.apps.dashboard",
            "gpubrokerapp.apps.websocket_gateway",
            "gpubrokerapp.apps.pod_config",
        ]

        for app_module in pod_saas_apps:
            try:
                __import__(app_module)
            except ImportError as e:
                raise AssertionError(
                    f"Failed to import POD SaaS app '{app_module}': {e}"
                )

        test_result("2.8.2 All POD SaaS apps importable", True)
    except AssertionError as e:
        test_result("2.8.2 All POD SaaS apps importable", False, str(e))

    print()

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print(f"Total Tests:  {tests_passed + tests_failed}")
    print()

    if tests_failed > 0:
        print("FAILED TESTS:")
        for test_name, error_msg in failures:
            print(f"  - {test_name}")
            if error_msg:
                print(f"    {error_msg}")
        print()
        return 1
    print("✅ ALL PRESERVATION TESTS PASSED!")
    print()
    print("POD SaaS structure is intact and accessible.")
    print("Baseline behavior confirmed - ready for architecture cleanup.")
    return 0


if __name__ == "__main__":
    sys.exit(run_tests())
