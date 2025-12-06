"""
Unified progress tracking models for conference execution.

Consolidates progress stages and updates from all engine versions
into a single, extensible system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class ProgressStage(str, Enum):
    """
    Unified progress stages for conference execution.
    
    Covers all stages from v1 and v2/v3 conference flows.
    """
    
    # Initialization
    INITIALIZING = "initializing"
    
    # Routing (v2/v3)
    ROUTING = "routing"
    
    # Scout / Literature Search (v2/v3)
    SCOUT_SEARCHING = "scout_searching"
    SCOUT_COMPLETE = "scout_complete"
    
    # Librarian Analysis (v1)
    LIBRARIAN_ANALYSIS = "librarian_analysis"
    
    # Round-based execution (v1)
    ROUND_START = "round_start"
    AGENT_THINKING = "agent_thinking"
    AGENT_COMPLETE = "agent_complete"
    ROUND_COMPLETE = "round_complete"
    
    # Lane-based execution (v2/v3)
    LANE_A_START = "lane_a_start"
    LANE_A_AGENT = "lane_a_agent"
    LANE_A_COMPLETE = "lane_a_complete"
    LANE_B_START = "lane_b_start"
    LANE_B_AGENT = "lane_b_agent"
    LANE_B_COMPLETE = "lane_b_complete"
    
    # Cross-examination (v2/v3)
    CROSS_EXAMINATION = "cross_examination"
    
    # Feasibility assessment (v2/v3)
    FEASIBILITY = "feasibility"
    
    # Grounding / Citation verification
    GROUNDING = "grounding"
    
    # Arbitration / Synthesis
    ARBITRATION = "arbitration"
    
    # Fragility testing
    FRAGILITY_START = "fragility_start"
    FRAGILITY_TEST = "fragility_test"
    
    # Completion
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ProgressUpdate:
    """
    Progress update event for UI callbacks.
    
    Attributes:
        stage: Current stage of execution
        message: Human-readable status message
        percent: Overall progress percentage (0-100)
        detail: Optional extra information (agent role, round number, etc.)
    """
    stage: ProgressStage
    message: str
    percent: int
    detail: dict = field(default_factory=dict)


class ProgressCallback(Protocol):
    """Protocol for progress callback functions."""
    
    def __call__(self, update: ProgressUpdate) -> None:
        """Called with progress updates during conference execution."""
        ...


# Aliases for backwards compatibility
V2ProgressStage = ProgressStage
V2ProgressUpdate = ProgressUpdate

