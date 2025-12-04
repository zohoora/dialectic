"""
Intelligent Router - MoE-style agent selection for v2.1.

Determines conference mode and which agents to activate based on
complexity signals and LLM analysis.
"""

from src.routing.router import route_query
from src.routing.signals import detect_complexity_signals

__all__ = ["route_query", "detect_complexity_signals"]

