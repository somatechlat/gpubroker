"""
Pytest configuration and fixtures for GPUBROKER E2E tests.

Provides Playwright fixtures for browser automation testing.
"""
import pytest
from playwright.sync_api import sync_playwright


# ============================================
# Playwright Fixtures
# ============================================

@pytest.fixture(scope="session")
def playwright_instance():
    """Create Playwright instance for the session."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance):
    """Launch browser once per session."""
    browser = playwright_instance.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser):
    """Create a new browser context for each test."""
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        locale='es-EC',
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context):
    """Create a new page for each test."""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="function")
def authenticated_page(context):
    """Create a page with admin authentication (if needed)."""
    page = context.new_page()
    # Add authentication logic here if needed
    # For now, just return the page
    yield page
    page.close()


# ============================================
# Test Configuration
# ============================================

@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application."""
    return "http://localhost:28080"


@pytest.fixture(scope="session")
def test_credentials():
    """Test credentials for various services."""
    return {
        'admin': {
            'email': 'admin@gpubroker.io',
            'password': 'admin123',
        },
        'paypal_sandbox': {
            'email': 'sb-zp64z48418674@personal.example.com',
            'password': 'mdEcL1$w',
        },
        'test_customer': {
            'ruc': '1790869571001',
            'email': 'ai@somatech.dev',
            'name': 'INGELSI CIA LTDA',
            'phone': '+5939997202547',
        },
    }


# ============================================
# Pytest Markers
# ============================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "paypal: marks tests that require PayPal sandbox"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests that require authentication"
    )


# ============================================
# Test Hooks
# ============================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Take screenshot on test failure."""
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        # Try to take screenshot on failure
        page = item.funcargs.get('page')
        if page:
            try:
                screenshot_path = f"/tmp/test_failure_{item.name}.png"
                page.screenshot(path=screenshot_path)
                print(f"\n📸 Screenshot saved: {screenshot_path}")
            except Exception as e:
                print(f"\n⚠️ Could not take screenshot: {e}")
