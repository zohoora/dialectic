"""
AI Case Conference System v3 - Data Schemas

Re-exports from submodules for backward compatibility.
Import directly from submodules for cleaner code:
- src.models.enums
- src.models.patient
- src.models.routing
- src.models.scout
- src.models.critique
- src.models.synthesis
- src.models.speculation
- src.models.state
"""

# Re-export all models for backward compatibility
from src.models.critique import Critique, FeasibilityAssessment
from src.models.enums import (
    CitationStatus,
    ConferenceMode,
    EvidenceGrade,
    Lane,
    SpeculationStatus,
)
from src.models.patient import PatientContext
from src.models.routing import RoutingDecision
from src.models.scout import ScoutCitation, ScoutReport
from src.models.speculation import Speculation, ValidationResult, WatchListTrigger
from src.models.state import ClassifiedQuery, LaneResult, V2ConferenceState
from src.models.synthesis import (
    ArbitratorSynthesis,
    ClinicalConsensus,
    ExploratoryConsideration,
    Tension,
)

__all__ = [
    # Enums
    "ConferenceMode",
    "Lane",
    "EvidenceGrade",
    "SpeculationStatus",
    "CitationStatus",
    # Patient
    "PatientContext",
    # Routing
    "RoutingDecision",
    # Scout
    "ScoutCitation",
    "ScoutReport",
    # Critique
    "Critique",
    "FeasibilityAssessment",
    # Synthesis
    "ClinicalConsensus",
    "ExploratoryConsideration",
    "Tension",
    "ArbitratorSynthesis",
    # Speculation
    "Speculation",
    "WatchListTrigger",
    "ValidationResult",
    # State
    "LaneResult",
    "V2ConferenceState",
    "ClassifiedQuery",
]
