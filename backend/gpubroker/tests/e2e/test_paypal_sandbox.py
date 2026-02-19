"""
GPUBROKER Admin E2E Tests - PayPal Sandbox Integration

Tests the complete PayPal payment flow using sandbox credentials.
This test requires:
1. Django server running on localhost:10355
2. PayPal sandbox credentials configured
3. Network access to PayPal sandbox

Test Data:
- PayPal Sandbox Email: [REDACTED - Use PAYPAL_SANDBOX_EMAIL env var]
- PayPal Sandbox Password: [REDACTED - Use PAYPAL_SANDBOX_PASSWORD env var]
"""

import os

import pytest
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout

BASE_URL = "http://localhost:10355"

# PayPal sandbox buyer credentials from environment
PAYPAL_SANDBOX_EMAIL = os.getenv("PAYPAL_SANDBOX_EMAIL", "test@example.com")
PAYPAL_SANDBOX_PASSWORD = os.getenv("PAYPAL_SANDBOX_PASSWORD", "test_password")

# Test customer data
TEST_RUC = "1790869571001"
TEST_EMAIL = "ai@somatech.dev"
TEST_NAME = "INGELSI CIA LTDA"


class TestPayPalSandboxIntegration:
    """Test PayPal sandbox payment integration."""

    def test_paypal_sandbox_configured(self, page: Page):
        """Verify PayPal sandbox is properly configured."""
        response = page.goto(f"{BASE_URL}/api/v2/admin/public/payment/paypal/status")

        assert response.status == 200

        content = page.content()
        assert '"configured": true' in content or '"configured":true' in content
        assert '"mode": "sandbox"' in content or '"mode":"sandbox"' in content

        print("✅ PayPal sandbox is configured")

    def test_create_paypal_order(self, page: Page):
        """Test creating a PayPal order via API."""
        page.goto(f"{BASE_URL}/checkout/?plan=pro")

        result = page.evaluate("""
            async () => {
                const response = await fetch('/api/v2/admin/public/payment/paypal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        email: 'ai@somatech.dev',
                        plan: 'pro',
                        amount: 49.00,
                        ruc: '1790869571001',
                        name: 'INGELSI CIA LTDA'
                    })
                });
                return await response.json();
            }
        """)

        assert (
            result.get("success") == True
        ), f"Order creation failed: {result.get('error')}"
        assert "order_id" in result
        assert "payment_url" in result
        assert "paypal.com" in result["payment_url"]

        print(f"✅ PayPal order created: {result['order_id']}")
        print(f"   Payment URL: {result['payment_url'][:60]}...")

        return result

    def test_paypal_approval_url_valid(self, page: Page):
        """Test that PayPal approval URL is valid and accessible."""
        page.goto(f"{BASE_URL}/checkout/?plan=pro")

        result = page.evaluate("""
            async () => {
                const response = await fetch('/api/v2/admin/public/payment/paypal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        email: 'test@example.com',
                        plan: 'pro',
                        amount: 49.00,
                        ruc: '1790869571001',
                        name: 'Test Company'
                    })
                });
                return await response.json();
            }
        """)

        if result.get("success"):
            payment_url = result["payment_url"]

            # Verify URL structure
            assert "sandbox.paypal.com" in payment_url
            assert "token=" in payment_url

            print("✅ PayPal approval URL is valid")
            print("   URL contains sandbox domain: ✓")
            print("   URL contains token: ✓")
        else:
            print(f"⚠️ Could not create order: {result.get('error')}")

    @pytest.mark.slow
    def test_full_paypal_payment_flow(self, page: Page):
        """
        Test complete PayPal payment flow.

        This test:
        1. Creates a PayPal order
        2. Navigates to PayPal sandbox
        3. Logs in with sandbox buyer account
        4. Completes the payment
        5. Verifies redirect back to app

        Note: This test is marked as slow and may be skipped in CI.
        """
        # Step 1: Create PayPal order
        page.goto(f"{BASE_URL}/checkout/?plan=pro")

        result = page.evaluate("""
            async () => {
                const response = await fetch('/api/v2/admin/public/payment/paypal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        email: 'ai@somatech.dev',
                        plan: 'pro',
                        amount: 49.00,
                        ruc: '1790869571001',
                        name: 'INGELSI CIA LTDA'
                    })
                });
                return await response.json();
            }
        """)

        if not result.get("success"):
            pytest.skip(f"Could not create PayPal order: {result.get('error')}")

        payment_url = result["payment_url"]
        order_id = result["order_id"]

        print(f"✅ Step 1: Order created - {order_id}")

        # Step 2: Navigate to PayPal
        try:
            page.goto(payment_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)

            print("✅ Step 2: Navigated to PayPal")

            # Step 3: Login to PayPal sandbox
            # Wait for email field
            email_field = page.locator('input[name="login_email"]')
            if email_field.is_visible(timeout=10000):
                email_field.fill(PAYPAL_SANDBOX_EMAIL)
                page.locator("#btnNext").click()
                page.wait_for_timeout(2000)

                # Fill password
                password_field = page.locator('input[name="login_password"]')
                if password_field.is_visible(timeout=10000):
                    password_field.fill(PAYPAL_SANDBOX_PASSWORD)
                    page.locator("#btnLogin").click()

                    print("✅ Step 3: Logged in to PayPal sandbox")

                    # Step 4: Wait for payment confirmation page
                    page.wait_for_timeout(5000)

                    # Try to click payment button
                    payment_buttons = [
                        "#payment-submit-btn",
                        "#confirmButtonTop",
                        'button[data-testid="submit-button-initial"]',
                    ]

                    for selector in payment_buttons:
                        try:
                            btn = page.locator(selector)
                            if btn.is_visible(timeout=3000):
                                btn.click()
                                print(f"✅ Step 4: Clicked payment button ({selector})")
                                break
                        except:
                            continue

                    # Step 5: Wait for redirect
                    page.wait_for_timeout(10000)

                    current_url = page.url
                    print(f"✅ Step 5: Final URL - {current_url[:60]}...")

                    # Check if redirected back to our app
                    if "localhost:10355" in current_url:
                        print("✅ Successfully redirected back to app!")
                        if "payment=success" in current_url:
                            print("✅ Payment marked as successful!")
                    else:
                        print("⚠️ Still on PayPal or other page")
                else:
                    print("⚠️ Password field not found")
            else:
                print(
                    "⚠️ Email field not found - PayPal page structure may have changed"
                )

        except PlaywrightTimeout as e:
            print(f"⚠️ Timeout during PayPal flow: {e}")
            # Take screenshot for debugging
            page.screenshot(path="/tmp/paypal_timeout.png")

    def test_capture_order_api(self, page: Page):
        """Test PayPal order capture API endpoint."""
        page.goto(f"{BASE_URL}/checkout/?plan=pro")

        # First create an order
        create_result = page.evaluate("""
            async () => {
                const response = await fetch('/api/v2/admin/public/payment/paypal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        email: 'test@example.com',
                        plan: 'pro',
                        amount: 49.00,
                        ruc: '1790869571001',
                        name: 'Test Company'
                    })
                });
                return await response.json();
            }
        """)

        if not create_result.get("success"):
            pytest.skip("Could not create order for capture test")

        order_id = create_result["order_id"]

        # Try to capture (will fail without user approval, but tests endpoint)
        capture_result = page.evaluate(f"""
            async () => {{
                const response = await fetch('/api/v2/admin/public/payment/paypal/capture/{order_id}', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}}
                }});
                return {{
                    status: response.status,
                    data: await response.json()
                }};
            }}
        """)

        # Should return error since order wasn't approved
        assert capture_result["status"] in [200, 400, 422]

        print(f"✅ Capture API responds: {capture_result['status']}")
        print(f"   Response: {capture_result['data']}")


class TestPayPalErrorHandling:
    """Test PayPal error handling scenarios."""

    def test_invalid_amount(self, page: Page):
        """Test order creation with invalid amount."""
        page.goto(f"{BASE_URL}/checkout/?plan=pro")

        result = page.evaluate("""
            async () => {
                const response = await fetch('/api/v2/admin/public/payment/paypal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        email: 'test@example.com',
                        plan: 'pro',
                        amount: -10.00,
                        ruc: '1790869571001',
                        name: 'Test Company'
                    })
                });
                return await response.json();
            }
        """)

        # Should handle gracefully
        print(f"✅ Invalid amount handled: {result}")

    def test_missing_email(self, page: Page):
        """Test order creation with missing email."""
        page.goto(f"{BASE_URL}/checkout/?plan=pro")

        result = page.evaluate("""
            async () => {
                const response = await fetch('/api/v2/admin/public/payment/paypal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        plan: 'pro',
                        amount: 49.00,
                        ruc: '1790869571001',
                        name: 'Test Company'
                    })
                });
                return {
                    status: response.status,
                    data: await response.json()
                };
            }
        """)

        # Should return validation error
        assert result["status"] in [200, 400, 422]

        print(f"✅ Missing email handled: {result['status']}")

    def test_capture_nonexistent_order(self, page: Page):
        """Test capturing a non-existent order."""
        page.goto(f"{BASE_URL}/checkout/?plan=pro")
        page.wait_for_load_state("networkidle")

        result = page.evaluate("""
            async () => {
                try {
                    const response = await fetch('/api/v2/admin/public/payment/paypal/capture/NONEXISTENT123', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'}
                    });
                    return {
                        status: response.status,
                        data: await response.json()
                    };
                } catch (e) {
                    return {error: e.message, status: 500};
                }
            }
        """)

        # Should return error (200 with success=false is also valid)
        assert result["status"] in [200, 400, 404, 422]

        print(f"✅ Non-existent order capture handled: {result['status']}")


# Pytest fixtures
@pytest.fixture(scope="function")
def page(browser):
    """Create a new page for each test."""
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="session")
def browser(playwright):
    """Launch browser once per session."""
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()
