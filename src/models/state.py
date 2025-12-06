"""
AI Case Conference System - Conference State Schemas

Models for orchestration state and classified queries.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.models.critique import Critique, FeasibilityAssessment
from src.models.enums import Lane
from src.models.patient import PatientContext
from src.models.routing import RoutingDecision
from src.models.scout import ScoutReport
from src.models.speculation import Speculation
from src.models.synthesis import ArbitratorSynthesis


class LaneResult(BaseModel):
    """Results from one lane's execution."""

    model_config = ConfigDict(use_enum_values=True)

    lane: Lane
    agent_responses: dict[str, Any] = Field(
        default_factory=dict
    )  # agent_id -> AgentResponse
    critiques_received: list[Critique] = Field(default_factory=list)
    feasibility_assessments: list[FeasibilityAssessment] = Field(default_factory=list)


class V2ConferenceState(BaseModel):
    """Extended state for v3 conference orchestration."""

    model_config = ConfigDict(use_enum_values=True)

    # Input
    query: str
    patient_context: Optional[PatientContext] = None

    # Routing
    routing_decision: Optional[RoutingDecision] = None

    # Scout
    scout_report: Optional[ScoutReport] = None

    # Library lookups
    retrieved_heuristics: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_speculations: list[Speculation] = Field(default_factory=list)

    # Lane results
    lane_a_result: Optional[LaneResult] = None
    lane_b_result: Optional[LaneResult] = None

    # Cross-examination
    cross_exam_critiques: list[Critique] = Field(default_factory=list)

    # Feasibility round
    feasibility_assessments: list[FeasibilityAssessment] = Field(default_factory=list)

    # Synthesis
    synthesis: Optional[ArbitratorSynthesis] = None

    # Control flow
    current_phase: str = "init"
    errors: list[str] = Field(default_factory=list)


class ClassifiedQuery(BaseModel):
    """Query after classification (extended for v3)."""

    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_text: str
    embedding: Optional[list[float]] = None
    query_type: str = ""  # DIAGNOSTIC_DILEMMA, THERAPEUTIC_SELECTION, etc.
    subtags: list[str] = Field(default_factory=list)
    uncertainty_domain: str = ""  # mechanism_known_outcomes_uncertain, etc.
    classification_confidence: float = 0.0
    extracted_entities: dict[str, Any] = Field(default_factory=dict)
    patient_context: Optional[PatientContext] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

