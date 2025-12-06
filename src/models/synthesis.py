"""
AI Case Conference System - Arbitrator Synthesis Schemas

Models for bifurcated output (Clinical + Exploratory).
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ClinicalConsensus(BaseModel):
    """The actionable clinical recommendation (Lane A output)."""

    recommendation: str
    evidence_basis: list[str] = Field(default_factory=list)  # Key citations
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    safety_profile: str = ""
    contraindications: list[str] = Field(default_factory=list)
    monitoring_required: list[str] = Field(default_factory=list)


class ExploratoryConsideration(BaseModel):
    """A theoretical approach worth considering (Lane B output)."""

    hypothesis: str
    mechanism: str = ""
    evidence_level: Literal[
        "theoretical", "preclinical", "early_clinical", "off_label"
    ] = "theoretical"
    potential_benefit: str = ""
    risks: list[str] = Field(default_factory=list)
    what_would_validate: str = ""  # What evidence would confirm this
    is_hypothesis: bool = True  # For UI labeling


class Tension(BaseModel):
    """An unresolved conflict between lanes."""

    description: str
    lane_a_position: str = ""
    lane_b_position: str = ""
    resolution: Literal[
        "defer_to_clinical", "defer_to_exploration", "unresolved", "context_dependent"
    ] = "unresolved"
    resolution_rationale: str = ""


class ArbitratorSynthesis(BaseModel):
    """Complete synthesis from the Arbitrator (v3 bifurcated format)."""

    synthesis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Main outputs
    clinical_consensus: ClinicalConsensus
    exploratory_considerations: list[ExploratoryConsideration] = Field(
        default_factory=list
    )

    # Tensions and conflicts
    tensions: list[Tension] = Field(default_factory=list)

    # Cross-examination summary
    safety_concerns_raised: list[str] = Field(default_factory=list)
    stagnation_concerns_raised: list[str] = Field(default_factory=list)

    # What would change the recommendation
    what_would_change_mind: str = ""

    # Dissent preservation (from v1.0)
    preserved_dissent: list[str] = Field(default_factory=list)

    # Overall assessment
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    uncertainty_map: dict[str, str] = Field(
        default_factory=dict
    )  # topic -> "agreed" | "contested" | "unknown"

