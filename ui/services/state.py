"""
Cached state management for the AI Case Conference UI.

This module provides cached resource getters using Streamlit's caching mechanisms
to share expensive resources (libraries, optimizers) across reruns.
"""

import logging
from pathlib import Path
from typing import Optional

import streamlit as st

from src.learning.library import ExperienceLibrary
from src.learning.optimizer import ConfigurationOptimizer, FeedbackCollector
from src.shadow.runner import ShadowRunner


@st.cache_resource
def get_experience_library() -> Optional[ExperienceLibrary]:
    """Get the shared Experience Library instance.
    
    Returns None if initialization fails (e.g., file I/O error).
    """
    try:
        storage_path = Path(__file__).parent.parent.parent / "data" / "experience_library.json"
        # Ensure data directory exists
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        return ExperienceLibrary(storage_path=storage_path)
    except Exception as e:
        logging.warning(f"Failed to initialize ExperienceLibrary: {e}")
        return None


@st.cache_resource
def get_optimizer() -> Optional[ConfigurationOptimizer]:
    """Get the shared Configuration Optimizer instance.
    
    Returns None if initialization fails (e.g., file I/O error).
    """
    try:
        storage_path = Path(__file__).parent.parent.parent / "data" / "optimizer_state.json"
        # Ensure data directory exists
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        return ConfigurationOptimizer(storage_path=storage_path)
    except Exception as e:
        logging.warning(f"Failed to initialize ConfigurationOptimizer: {e}")
        return None


@st.cache_resource
def get_feedback_collector() -> Optional[FeedbackCollector]:
    """Get the shared Feedback Collector instance.
    
    Returns None if initialization fails (e.g., file I/O error).
    """
    try:
        storage_path = Path(__file__).parent.parent.parent / "data" / "feedback.json"
        # Ensure data directory exists
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        return FeedbackCollector(storage_path=storage_path)
    except Exception as e:
        logging.warning(f"Failed to initialize FeedbackCollector: {e}")
        return None


@st.cache_resource
def get_shadow_runner(_api_key: str) -> Optional[ShadowRunner]:
    """Get the shared Shadow Runner instance.
    
    Note: _api_key prefix tells Streamlit not to hash this parameter.
    Returns None if the client fails to initialize (e.g., invalid API key).
    """
    try:
        from src.llm.client import LLMClient
        from src.conference.engine import ConferenceEngine
        storage_path = Path(__file__).parent.parent.parent / "data" / "shadow_results.json"
        client = LLMClient(api_key=_api_key)
        engine = ConferenceEngine(client)
        return ShadowRunner(client, engine, storage_path=storage_path)
    except Exception as e:
        # Log the error but don't crash - shadow mode is optional
        logging.warning(f"Failed to initialize ShadowRunner: {e}")
        return None

