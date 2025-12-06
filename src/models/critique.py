"""
AI Case Conference System - Cross-Examination Schemas

Models for inter-lane critique and feasibility assessment.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import Lane


class Critique(BaseModel):
    """A critique from cross-examination between lanes."""

    critic_role: str
    target_role: str
    target_lane: Lane
    critique_type: Literal["safety", "feasibility", "stagnation", "mechanism"]
    content: str
    severity: Literal["minor", "moderate", "major", "critical"]
    specific_concerns: list[str] = Field(default_factory=list)


class FeasibilityAssessment(BaseModel):
    """Assessment from Pragmatist or Patient Voice."""

    model_config = ConfigDict(use_enum_values=True)

    assessor_role: str
    target_lane: Lane

    # Pragmatist fields
    can_be_done: Optional[bool] = None
    system_barriers: list[str] = Field(default_factory=list)
    cost_concerns: list[str] = Field(default_factory=list)
    access_issues: list[str] = Field(default_factory=list)

    # Patient Voice fields
    patient_burden: Optional[Literal["low", "moderate", "high", "very_high"]] = None
    adherence_likelihood: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    qol_impact: Optional[str] = None
    patient_concerns: list[str] = Field(default_factory=list)

    overall_feasibility: Literal[
        "recommended", "possible", "difficult", "not_recommended"
    ] = "possible"
    summary: str = ""

