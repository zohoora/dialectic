"""
Playwright configuration for Streamlit UI testing.

This configuration sets up Playwright to work with Streamlit's
server-side rendering and WebSocket connections.
"""

# Playwright pytest plugin configuration
# These are picked up automatically by pytest-playwright

# Default browser to use
BROWSER = "chromium"

# Headless mode (set to False for debugging)
HEADLESS = True

# Slow down actions for debugging (milliseconds)
SLOW_MO = 0

# Default timeout for actions (milliseconds)
DEFAULT_TIMEOUT = 30000

# Viewport size
VIEWPORT = {"width": 1280, "height": 720}

# Base URL for Streamlit app (default local)
BASE_URL = "http://localhost:8501"

# Screenshot on failure
SCREENSHOT_ON_FAILURE = True

# Video recording (off by default for speed)
VIDEO = "off"  # Can be "on", "off", "retain-on-failure"

# Trace recording (off by default)
TRACING = "off"  # Can be "on", "off", "retain-on-failure"


def get_browser_context_args():
    """Get arguments for creating browser contexts."""
    return {
        "viewport": VIEWPORT,
        "ignore_https_errors": True,
        "java_script_enabled": True,
    }


def get_launch_args():
    """Get arguments for launching the browser."""
    return {
        "headless": HEADLESS,
        "slow_mo": SLOW_MO,
    }

