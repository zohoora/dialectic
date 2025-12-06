"""
Learning & Optimization Layer.

Contains components for:
- Gatekeeper: Quality control for experience extraction
- Surgeon: Heuristic extraction from conferences
- Experience Library: Storage and retrieval of heuristics
- Orchestrators: Learning-enabled conference execution
"""

from src.learning.base_library import BaseLibrary, keyword_match_score
from src.learning.base_orchestrator import BaseOrchestrator
from src.learning.orchestrator import ConferenceOrchestrator, OrchestratedConferenceResult
from src.learning.orchestrator_v3 import (
    ConferenceOrchestratorV3,
    OrchestratedV3Result,
    V3ModelConfig,
)

__all__ = [
    "BaseLibrary",
    "keyword_match_score",
    "BaseOrchestrator",
    "ConferenceOrchestrator",
    "OrchestratedConferenceResult",
    "ConferenceOrchestratorV3",
    "OrchestratedV3Result",
    "V3ModelConfig",
]
