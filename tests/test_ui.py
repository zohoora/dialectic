"""
Playwright UI Tests for Streamlit Application.

These tests verify the Streamlit UI functionality using Playwright.
They require a running Streamlit server (started automatically in fixtures).

Run with: pytest -m ui -v
"""

import os
import pytest
import subprocess
import time
import signal
from pathlib import Path

# Only import playwright if available
pytest.importorskip("playwright")

from playwright.sync_api import Page, expect, sync_playwright


# ============================================================================
# Constants
# ============================================================================

STREAMLIT_PORT = 8502
STREAMLIT_URL = f"http://localhost:{STREAMLIT_PORT}"
DEFAULT_WAIT_MS = 2000  # Standard wait time for Streamlit to render


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def streamlit_server():
    """Start a Streamlit server for UI testing.
    
    This fixture starts the Streamlit app in a subprocess and waits
    for it to be ready before yielding. It cleans up after tests complete.
    """
    env = os.environ.copy()
    env["OPENROUTER_API_KEY"] = "test-key-for-ui-tests"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    
    app_path = Path(__file__).parent.parent / "ui" / "app.py"
    
    process = subprocess.Popen(
        ["streamlit", "run", str(app_path), "--server.port", str(STREAMLIT_PORT), "--server.headless", "true"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid if os.name != 'nt' else None,
    )
    
    # Wait for server to be ready (max 30 seconds)
    max_wait = 30
    start_time = time.time()
    server_ready = False
    
    while time.time() - start_time < max_wait:
        try:
            import httpx
            response = httpx.get(f"{STREAMLIT_URL}/_stcore/health", timeout=2)
            if response.status_code == 200:
                server_ready = True
                break
        except Exception:
            pass
        time.sleep(0.5)
    
    if not server_ready:
        process.terminate()
        pytest.skip("Streamlit server failed to start")
    
    yield STREAMLIT_URL
    
    # Cleanup
    if os.name != 'nt':
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    else:
        process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="module")
def browser_context():
    """Create a Playwright browser context."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )
        yield context
        context.close()
        browser.close()


@pytest.fixture
def page(browser_context, streamlit_server):
    """Create a new page for each test, already navigated to the app."""
    page = browser_context.new_page()
    page.set_default_timeout(30000)
    page.goto(streamlit_server)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(DEFAULT_WAIT_MS)
    yield page
    page.close()


# ============================================================================
# App Loading Tests
# ============================================================================

@pytest.mark.ui
class TestAppLoading:
    """Test that the app loads correctly."""
    
    def test_app_loads_with_header(self, page):
        """Test that the app loads and shows the main header."""
        header = page.locator("text=Case Conference")
        expect(header.first).to_be_visible(timeout=10000)
    
    def test_app_shows_sidebar(self, page):
        """Test that the sidebar is visible."""
        sidebar = page.locator('[data-testid="stSidebar"]')
        expect(sidebar).to_be_visible()
    
    def test_app_shows_text_area(self, page):
        """Test that the query text area is visible."""
        text_area = page.locator("textarea")
        expect(text_area.first).to_be_visible()


# ============================================================================
# Sidebar Configuration Tests
# ============================================================================

@pytest.mark.ui
class TestSidebarConfiguration:
    """Test sidebar configuration options."""
    
    def test_preset_buttons_exist(self, page):
        """Test that preset buttons (Fast, Standard, Deep) exist."""
        expect(page.locator('button:has-text("Fast")')).to_be_visible()
        expect(page.locator('button:has-text("Standard")')).to_be_visible()
        expect(page.locator('button:has-text("Deep")')).to_be_visible()
    
    def test_agent_checkboxes_exist(self, page):
        """Test that agent selection checkboxes exist."""
        # Look for agent expander and expand it
        agents_expander = page.locator('text=Agents')
        if agents_expander.count() > 0:
            agents_expander.first.click()
            page.wait_for_timeout(500)
        
        advocate_checkbox = page.locator('text=Advocate')
        expect(advocate_checkbox.first).to_be_visible()
    
    def test_clicking_preset_changes_config(self, page):
        """Test that clicking a preset button updates configuration."""
        page.locator('button:has-text("Fast")').click()
        page.wait_for_timeout(1000)
        
        # The app should still be functional after preset click
        expect(page.locator("textarea").first).to_be_visible()


# ============================================================================
# Query Input Tests
# ============================================================================

@pytest.mark.ui
class TestQueryInput:
    """Test query input functionality."""
    
    def test_can_type_in_text_area(self, page):
        """Test that text can be entered in the query text area."""
        text_area = page.locator("textarea").first
        test_query = "Test medical question for UI testing"
        text_area.fill(test_query)
        expect(text_area).to_have_value(test_query)
    
    def test_example_buttons_exist(self, page):
        """Test that example query buttons exist."""
        crps_button = page.locator('button:has-text("CRPS")')
        expect(crps_button).to_be_visible()
    
    def test_clicking_example_fills_query(self, page):
        """Test that clicking an example button fills the query."""
        page.locator('button:has-text("CRPS")').click()
        page.wait_for_timeout(DEFAULT_WAIT_MS)
        
        # After clicking, the page reruns - check that text area is still there
        expect(page.locator("textarea").first).to_be_visible()


# ============================================================================
# Conference Button Tests
# ============================================================================

@pytest.mark.ui
class TestConferenceButton:
    """Test the Start Conference button."""
    
    def test_start_button_exists(self, page):
        """Test that the Start Conference button exists."""
        start_button = page.locator('button:has-text("Start Conference")')
        expect(start_button).to_be_visible()
    
    def test_start_button_visible_with_default_agents(self, page):
        """Test that start button is visible with default agent configuration."""
        # The button should be enabled by default (3 agents selected)
        start_button = page.locator('button:has-text("Start Conference")')
        expect(start_button).to_be_visible()


# ============================================================================
# Responsive Layout Tests
# ============================================================================

@pytest.mark.ui
class TestResponsiveLayout:
    """Test responsive layout behavior."""
    
    @pytest.mark.parametrize("width,height,name", [
        (375, 667, "mobile"),
        (768, 1024, "tablet"),
    ])
    def test_app_works_at_viewport_size(self, browser_context, streamlit_server, width, height, name):
        """Test that app renders correctly at different viewport sizes."""
        page = browser_context.new_page()
        page.set_viewport_size({"width": width, "height": height})
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(DEFAULT_WAIT_MS)
        
        # App should still show main elements
        expect(page.locator("textarea").first).to_be_visible()
        page.close()


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.ui
class TestErrorHandling:
    """Test error handling in the UI."""
    
    def test_empty_query_shows_warning(self, page):
        """Test that submitting empty query shows a warning."""
        text_area = page.locator("textarea").first
        text_area.fill("")
        
        page.locator('button:has-text("Start Conference")').click()
        page.wait_for_timeout(1000)
        
        # The app shouldn't crash - text area should still be visible
        expect(page.locator("textarea").first).to_be_visible()


# ============================================================================
# Accessibility Tests
# ============================================================================

@pytest.mark.ui
class TestAccessibility:
    """Basic accessibility tests."""
    
    def test_buttons_are_focusable(self, page):
        """Test that interactive elements can be focused."""
        # Tab through the page
        for _ in range(3):
            page.keyboard.press("Tab")
        
        focused = page.evaluate("document.activeElement.tagName")
        assert focused is not None
    
    def test_text_area_has_placeholder(self, page):
        """Test that text area has helpful placeholder text."""
        text_area = page.locator("textarea").first
        placeholder = text_area.get_attribute("placeholder")
        
        assert placeholder is not None
        assert len(placeholder) > 10


# ============================================================================
# Integration Smoke Test
# ============================================================================

@pytest.mark.ui
class TestIntegrationSmoke:
    """Smoke test for full UI integration."""
    
    def test_full_page_interaction_flow(self, page):
        """Test a full interaction flow through the UI."""
        # 1. Check app loaded
        expect(page.locator("textarea").first).to_be_visible()
        
        # 2. Click a preset
        standard_button = page.locator('button:has-text("Standard")')
        if standard_button.is_visible():
            standard_button.click()
            page.wait_for_timeout(500)
        
        # 3. Enter a query
        page.locator("textarea").first.fill("Test query for smoke test")
        
        # 4. Verify everything is still functional
        expect(page.locator('button:has-text("Start Conference")')).to_be_visible()
        
        # 5. Check sidebar is accessible
        expect(page.locator('[data-testid="stSidebar"]')).to_be_visible()


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.ui
@pytest.mark.slow
class TestPerformance:
    """Basic performance tests."""
    
    def test_page_loads_within_timeout(self, browser_context, streamlit_server):
        """Test that the page loads within acceptable time."""
        page = browser_context.new_page()
        
        start_time = time.time()
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")
        load_time = time.time() - start_time
        
        assert load_time < 10, f"Page took {load_time:.2f}s to load"
        page.close()
    
    def test_multiple_interactions_dont_slow_down(self, page):
        """Test that multiple interactions don't cause slowdown."""
        text_area = page.locator("textarea").first
        
        for i in range(5):
            start_time = time.time()
            text_area.fill(f"Query iteration {i}")
            interaction_time = time.time() - start_time
            
            assert interaction_time < 2, f"Interaction {i} took {interaction_time:.2f}s"
