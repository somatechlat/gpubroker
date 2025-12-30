"""
GPUBROKER Admin E2E Tests with Playwright

Tests the admin pages are accessible and rendering correctly.
Uses headless Chromium for fast iteration.
"""
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:28080"


class TestAdminLogin:
    """Test admin login page."""
    
    def test_login_page_loads(self, page: Page):
        """Verify login page loads and displays correctly."""
        page.goto(f"{BASE_URL}/admin/login/")
        
        # Check page title
        expect(page).to_have_title("Admin Login - GPUBROKER")
        
        # Check logo text is present (use first match)
        expect(page.get_by_text("GPUBROKER", exact=True).first).to_be_visible()
        
        # Check form elements exist
        expect(page.locator("#email")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
        expect(page.locator("#loginBtn")).to_be_visible()
        
        print("✅ Login page loads correctly")
    
    def test_login_form_validation(self, page: Page):
        """Test login form has proper validation."""
        page.goto(f"{BASE_URL}/admin/login/")
        
        # Email field should be required
        email_input = page.locator("#email")
        expect(email_input).to_have_attribute("required", "")
        expect(email_input).to_have_attribute("type", "email")
        
        # Password field should be required
        password_input = page.locator("#password")
        expect(password_input).to_have_attribute("required", "")
        expect(password_input).to_have_attribute("type", "password")
        
        print("✅ Login form validation works")


class TestCheckoutPage:
    """Test checkout page."""
    
    def test_checkout_page_loads(self, page: Page):
        """Verify checkout page loads with plan parameter."""
        page.goto(f"{BASE_URL}/checkout/?plan=pro")
        
        # Check page title
        expect(page).to_have_title("Checkout - GPUBROKER")
        
        # Check RUC validation section
        expect(page.locator("text=Verifica tu Identidad")).to_be_visible()
        expect(page.locator("#identifier")).to_be_visible()
        expect(page.locator("#validateBtn")).to_be_visible()
        
        print("✅ Checkout page loads correctly")
    
    def test_checkout_plan_display(self, page: Page):
        """Test that plan info is displayed correctly."""
        page.goto(f"{BASE_URL}/checkout/?plan=pro")
        
        # Wait for JavaScript to update plan info
        page.wait_for_timeout(500)
        
        # Plan name should be visible after validation
        # (Plan section is hidden until RUC is validated)
        expect(page.locator("#planSection")).to_be_hidden()
        
        print("✅ Checkout plan display works")


class TestActivatePage:
    """Test activation page."""
    
    def test_activate_page_loads(self, page: Page):
        """Verify activate page loads."""
        page.goto(f"{BASE_URL}/activate/")
        
        # Check page title (actual title from template)
        expect(page).to_have_title("Activar GPUBROKER POD")
        
        print("✅ Activate page loads correctly")


class TestProvisioningPage:
    """Test provisioning page."""
    
    def test_provisioning_page_loads(self, page: Page):
        """Verify provisioning page loads."""
        page.goto(f"{BASE_URL}/provisioning/")
        
        # Check page title (actual title from template)
        expect(page).to_have_title("Desplegando GPUBROKER POD")
        
        print("✅ Provisioning page loads correctly")


class TestReadyPage:
    """Test ready page."""
    
    def test_ready_page_loads(self, page: Page):
        """Verify ready page loads."""
        page.goto(f"{BASE_URL}/ready/")
        
        # Check page title (actual title from template)
        expect(page).to_have_title("¡GPUBROKER POD Listo!")
        
        print("✅ Ready page loads correctly")


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_endpoint(self, page: Page):
        """Verify health endpoint returns healthy status."""
        response = page.goto(f"{BASE_URL}/health")
        
        assert response.status == 200
        
        # Get JSON response
        content = page.content()
        assert '"status": "healthy"' in content or '"status":"healthy"' in content
        
        print("✅ Health endpoint returns healthy")


class TestSomatechBranding:
    """Test SOMATECH branding is present across all pages."""
    
    def test_login_page_somatech_footer(self, page: Page):
        """Verify login page has SOMATECH footer."""
        page.goto(f"{BASE_URL}/admin/login/")
        
        # Check SOMATECH link is present
        somatech_link = page.locator("a[href='https://www.somatech.dev']")
        expect(somatech_link).to_be_visible()
        
        # Check footer text
        expect(page.get_by_text("Desarrollado por")).to_be_visible()
        
        print("✅ Login page has SOMATECH branding")
    
    def test_checkout_page_somatech_footer(self, page: Page):
        """Verify checkout page has SOMATECH footer."""
        page.goto(f"{BASE_URL}/checkout/?plan=pro")
        
        # Check SOMATECH link is present
        somatech_link = page.locator("a[href='https://www.somatech.dev']")
        expect(somatech_link).to_be_visible()
        
        print("✅ Checkout page has SOMATECH branding")
    
    def test_activate_page_somatech_footer(self, page: Page):
        """Verify activate page has SOMATECH footer."""
        page.goto(f"{BASE_URL}/activate/")
        
        # Check SOMATECH link is present
        somatech_link = page.locator("a[href='https://www.somatech.dev']")
        expect(somatech_link).to_be_visible()
        
        print("✅ Activate page has SOMATECH branding")
    
    def test_provisioning_page_somatech_footer(self, page: Page):
        """Verify provisioning page has SOMATECH footer."""
        page.goto(f"{BASE_URL}/provisioning/")
        
        # Check SOMATECH link is present
        somatech_link = page.locator("a[href='https://www.somatech.dev']")
        expect(somatech_link).to_be_visible()
        
        print("✅ Provisioning page has SOMATECH branding")
    
    def test_ready_page_somatech_footer(self, page: Page):
        """Verify ready page has SOMATECH footer."""
        page.goto(f"{BASE_URL}/ready/")
        
        # Check SOMATECH link is present
        somatech_link = page.locator("a[href='https://www.somatech.dev']")
        expect(somatech_link).to_be_visible()
        
        print("✅ Ready page has SOMATECH branding")


# Pytest configuration
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
