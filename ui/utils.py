"""
Utility functions for the AI Case Conference UI.

This module contains async helpers and API key management.
"""

import asyncio
import os
from typing import TypeVar, Coroutine, Any

import streamlit as st

# Type variable for async return type
T = TypeVar('T')


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine safely in Streamlit context.
    
    Handles the case where an event loop may already be running
    (e.g., future Streamlit async features).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, safe to use asyncio.run
        return asyncio.run(coro)
    
    # Loop already running - use nest_asyncio pattern or create new loop
    import nest_asyncio
    nest_asyncio.apply()
    return loop.run_until_complete(coro)


def get_api_key() -> str | None:
    """
    Get OpenRouter API key from Streamlit secrets (cloud) or environment variable (local).
    
    Priority:
    1. Streamlit secrets (for Streamlit Cloud deployment)
    2. Environment variable (for local development)
    """
    # Try Streamlit secrets first (for Streamlit Cloud)
    try:
        return st.secrets["OPENROUTER_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass
    
    # Fall back to environment variable (for local development)
    return os.getenv("OPENROUTER_API_KEY")

