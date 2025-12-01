"""
Data models for Fragility Testing.

Fragility testing stress-tests consensus recommendations by applying
perturbations (e.g., "What if patient has renal impairment?") to see
if the recommendation still holds.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FragilityOutcome(str, Enum):
    """Possible outcomes when testing a recommendation against a perturbation."""
    
    SURVIVES = "SURVIVES"  # Recommendation still holds
    MODIFIES = "MODIFIES"  # Recommendation needs adjustment
    COLLAPSES = "COLLAPSES"  # Recommendation no longer valid


class FragilityResult(BaseModel):
    """Result of testing a single perturbation."""
    
    perturbation: str = Field(..., description="The perturbation that was tested")
    outcome: FragilityOutcome = Field(..., description="Whether recommendation survived")
    explanation: str = Field(..., description="Brief explanation of the outcome")
    modified_recommendation: Optional[str] = Field(
        default=None,
        description="If MODIFIES, what the adjusted recommendation would be"
    )


class FragilityReport(BaseModel):
    """Complete fragility report for a consensus recommendation."""
    
    perturbations_tested: int = Field(
        default=0,
        description="Number of perturbations tested"
    )
    
    results: list[FragilityResult] = Field(
        default_factory=list,
        description="Individual test results"
    )
    
    @property
    def survived(self) -> list[FragilityResult]:
        """Perturbations that the recommendation survived."""
        return [r for r in self.results if r.outcome == FragilityOutcome.SURVIVES]
    
    @property
    def modified(self) -> list[FragilityResult]:
        """Perturbations that require recommendation modification."""
        return [r for r in self.results if r.outcome == FragilityOutcome.MODIFIES]
    
    @property
    def collapsed(self) -> list[FragilityResult]:
        """Perturbations that invalidate the recommendation."""
        return [r for r in self.results if r.outcome == FragilityOutcome.COLLAPSES]
    
    @property
    def survival_rate(self) -> float:
        """Fraction of perturbations the recommendation survived."""
        if self.perturbations_tested == 0:
            return 1.0
        return len(self.survived) / self.perturbations_tested
    
    @property
    def is_fragile(self) -> bool:
        """Whether the recommendation is considered fragile (survival < 30%)."""
        return self.survival_rate < 0.3
    
    @property
    def fragility_level(self) -> str:
        """Human-readable fragility level."""
        rate = self.survival_rate
        if rate >= 0.7:
            return "LOW"
        elif rate >= 0.3:
            return "MODERATE"
        else:
            return "HIGH"


# Default medical perturbations for clinical recommendations
DEFAULT_MEDICAL_PERTURBATIONS = [
    "What if the patient has renal impairment (GFR < 30)?",
    "What if the patient is on anticoagulation therapy?",
    "What if the patient is pregnant or planning pregnancy?",
    "What if the patient is elderly (age > 75)?",
    "What if cost is the primary constraint for this patient?",
    "What if the patient has a history of substance use disorder?",
    "What if the patient has liver disease (Child-Pugh B or C)?",
    "What if the patient is immunocompromised?",
    "What if the patient has cardiac disease (CHF, arrhythmia)?",
    "What if the patient has a history of falls?",
    "What if the patient has cognitive impairment or dementia?",
    "What if the patient has limited access to follow-up care?",
    "What if the patient has multiple drug allergies?",
    "What if the patient is on multiple other medications (polypharmacy)?",
    "What if the patient has a bleeding disorder?",
]

