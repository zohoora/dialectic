"""
UI components for the AI Case Conference application.

This module contains reusable Streamlit rendering components.
"""

from ui.components.sidebar import render_sidebar
from ui.components.results import (
    render_agent_response,
    render_round,
    render_synthesis,
    render_dissent,
    render_grounding,
    render_fragility,
    render_metrics,
)
from ui.components.feedback import (
    render_gatekeeper,
    render_extraction_result,
    render_feedback_form,
)
from ui.components.learning import (
    render_library_stats,
    render_optimizer_insights,
    render_classification,
    render_injection_info,
    render_shadow_summary,
)

__all__ = [
    # Sidebar
    "render_sidebar",
    # Results
    "render_agent_response",
    "render_round",
    "render_synthesis",
    "render_dissent",
    "render_grounding",
    "render_fragility",
    "render_metrics",
    # Feedback
    "render_gatekeeper",
    "render_extraction_result",
    "render_feedback_form",
    # Learning
    "render_library_stats",
    "render_optimizer_insights",
    "render_classification",
    "render_injection_info",
    "render_shadow_summary",
]

