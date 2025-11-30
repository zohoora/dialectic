"""
Data models for the Gatekeeper system.

The Gatekeeper determines whether a conference result contains
generalizable wisdom worthy of extraction to the Experience Library.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RejectionCode(str, Enum):
    """Codes for why a conference was rejected by the Gatekeeper."""
    
    HALLUCINATION = "HALLUCINATION"  # Contains unverified citations
    FRAGILE = "FRAGILE"  # Recommendation breaks under perturbation
    IDIOSYNCRATIC = "IDIOSYNCRATIC"  # Relies on patient-specific constraints
    NO_EVIDENCE = "NO_EVIDENCE"  # Consensus with no cited evidence
    SHALLOW = "SHALLOW"  # Immediate agreement without debate
    CIRCULAR = "CIRCULAR"  # Circular reasoning detected


class GatekeeperFlag(str, Enum):
    """Flags that modify the Gatekeeper's assessment."""
    
    HALLUCINATION_SELF_CORRECTED = "HALLUCINATION_SELF_CORRECTED"
    NARROW_SUBSET = "NARROW_SUBSET"  # Applies to specific patient subset
    STRONG_EVIDENCE = "STRONG_EVIDENCE"  # Well-supported by citations
    CONTESTED_BUT_RESOLVED = "CONTESTED_BUT_RESOLVED"  # Had dissent but reached consensus


class DissentStatus(BaseModel):
    """Status of dissent in the conference."""
    
    dissent_preserved: bool = Field(
        default=False,
        description="Whether any agent preserved dissent"
    )
    dissent_summary: Optional[str] = Field(
        default=None,
        description="Summary of the dissenting position"
    )
    dissenting_role: Optional[str] = Field(
        default=None,
        description="Role of the dissenting agent"
    )
    dissent_strength: str = Field(
        default="None",
        description="Strength of dissent: Strong, Moderate, Weak, None"
    )


class OutcomeSignals(BaseModel):
    """Outcome signals from user feedback (if available)."""
    
    user_rating: Optional[str] = Field(
        default=None,
        description="User rating: positive, neutral, negative"
    )
    user_acted_on: Optional[bool] = Field(
        default=None,
        description="Whether user acted on the recommendation"
    )
    user_modified: Optional[bool] = Field(
        default=None,
        description="Whether user modified the recommendation before acting"
    )


class GatekeeperInput(BaseModel):
    """Input to the Gatekeeper evaluation."""
    
    conference_id: str = Field(..., description="ID of the conference")
    conference_summary: str = Field(..., description="Summary of the conference")
    final_consensus: str = Field(..., description="The final consensus recommendation")
    
    # Quality indicators
    hallucination_rate: float = Field(
        default=0.0,
        description="Rate of failed citations (0-1)"
    )
    fragility_survival_rate: float = Field(
        default=1.0,
        description="Fragility survival rate (0-1)"
    )
    
    # Dissent info
    dissent_status: DissentStatus = Field(
        default_factory=DissentStatus,
        description="Status of any preserved dissent"
    )
    
    # Conference dynamics
    num_rounds: int = Field(default=1, description="Number of deliberation rounds")
    position_changes: int = Field(
        default=0,
        description="Number of position changes during deliberation"
    )
    total_citations: int = Field(
        default=0,
        description="Total citations claimed by agents"
    )
    verified_citations: int = Field(
        default=0,
        description="Number of verified citations"
    )
    
    # Optional outcome signals
    outcome_signals: Optional[OutcomeSignals] = Field(
        default=None,
        description="User feedback if available"
    )


class GatekeeperOutput(BaseModel):
    """Output from the Gatekeeper evaluation."""
    
    eligible: bool = Field(
        ...,
        description="Whether conference is eligible for extraction"
    )
    reason: str = Field(
        ...,
        description="Brief explanation (max 50 words)"
    )
    rejection_code: Optional[RejectionCode] = Field(
        default=None,
        description="Primary rejection reason if not eligible"
    )
    secondary_code: Optional[RejectionCode] = Field(
        default=None,
        description="Secondary rejection reason if applicable"
    )
    flags: list[GatekeeperFlag] = Field(
        default_factory=list,
        description="Flags that modify the assessment"
    )
    confidence: float = Field(
        default=0.5,
        description="Confidence in the eligibility decision (0-1)"
    )
    
    @property
    def passed(self) -> bool:
        """Alias for eligible."""
        return self.eligible


class GatekeeperDecision(BaseModel):
    """Record of a Gatekeeper decision for calibration."""
    
    conference_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    passed: bool
    rejection_code: Optional[RejectionCode] = None
    confidence: float
    eventual_outcome: Optional[str] = None  # Filled later with feedback


class CalibrationReport(BaseModel):
    """Report on Gatekeeper calibration."""
    
    status: str = Field(
        ...,
        description="INSUFFICIENT_DATA, TOO_LOOSE, POSSIBLY_TOO_STRICT, WELL_CALIBRATED"
    )
    false_positive_rate: Optional[float] = Field(
        default=None,
        description="Rate of bad outcomes among passed conferences"
    )
    rejection_rate: Optional[float] = Field(
        default=None,
        description="Rate of conferences rejected"
    )
    recommendation: str = Field(
        ...,
        description="Recommendation for adjustment"
    )
    decisions_analyzed: int = Field(
        default=0,
        description="Number of decisions with outcomes analyzed"
    )

