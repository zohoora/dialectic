"""
Data models for the Experience Library.

The Experience Library stores generalizable heuristics extracted
from high-quality conference results via the Surgeon.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HeuristicStatus(str, Enum):
    """Status of a heuristic in the library."""
    
    ACTIVE = "ACTIVE"  # Available for injection
    DEPRECATED = "DEPRECATED"  # No longer recommended
    SUPERSEDED = "SUPERSEDED"  # Replaced by newer heuristic
    UNDER_REVIEW = "UNDER_REVIEW"  # Being evaluated


class ContextVector(BaseModel):
    """
    Embedding-friendly context for similarity matching.
    Used to retrieve relevant heuristics for new queries.
    """
    
    domain: str = Field(..., description="Medical domain (e.g., pain, cardiology)")
    condition: str = Field(..., description="Primary condition being addressed")
    treatment_type: Optional[str] = Field(
        default=None,
        description="Type of treatment (pharmacological, procedural, etc.)"
    )
    patient_factors: list[str] = Field(
        default_factory=list,
        description="Key patient factors (elderly, renal impairment, etc.)"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Searchable keywords"
    )
    
    def to_search_text(self) -> str:
        """Convert to searchable text for retrieval."""
        parts = [
            f"Domain: {self.domain}",
            f"Condition: {self.condition}",
        ]
        if self.treatment_type:
            parts.append(f"Treatment: {self.treatment_type}")
        if self.patient_factors:
            parts.append(f"Patient factors: {', '.join(self.patient_factors)}")
        if self.keywords:
            parts.append(f"Keywords: {', '.join(self.keywords)}")
        return " | ".join(parts)


class ReasoningArtifact(BaseModel):
    """
    A generalizable heuristic extracted from a conference.
    This is the core data structure stored in the Experience Library.
    """
    
    # Identification
    heuristic_id: str = Field(..., description="Unique identifier for this heuristic")
    source_conference_id: str = Field(..., description="Conference this was extracted from")
    created_at: datetime = Field(default_factory=datetime.now)
    
    # The heuristic itself
    winning_heuristic: str = Field(
        ...,
        description="The main recommendation/insight (max 100 words)"
    )
    contra_heuristic: Optional[str] = Field(
        default=None,
        description="What was considered but rejected, and why"
    )
    
    # Context for retrieval
    context_vector: ContextVector = Field(
        ...,
        description="Context for similarity matching"
    )
    
    # Applicability boundaries
    qualifying_conditions: list[str] = Field(
        default_factory=list,
        description="Conditions that must be true for this heuristic to apply"
    )
    disqualifying_conditions: list[str] = Field(
        default_factory=list,
        description="Conditions that would invalidate this heuristic"
    )
    fragility_factors: list[str] = Field(
        default_factory=list,
        description="Known scenarios where this may need modification"
    )
    
    # Evidence basis
    evidence_pmids: list[str] = Field(
        default_factory=list,
        description="PubMed IDs of supporting evidence"
    )
    evidence_summary: Optional[str] = Field(
        default=None,
        description="Brief summary of evidence basis"
    )
    
    # Quality metrics
    confidence: float = Field(
        default=0.5,
        description="Initial confidence (0-1)"
    )
    times_injected: int = Field(default=0, description="Times presented to conferences")
    times_accepted: int = Field(default=0, description="Times incorporated by agents")
    times_rejected: int = Field(default=0, description="Times explicitly rejected")
    times_modified: int = Field(default=0, description="Times modified before use")
    
    # Status
    status: HeuristicStatus = Field(
        default=HeuristicStatus.ACTIVE,
        description="Current status of this heuristic"
    )
    superseded_by: Optional[str] = Field(
        default=None,
        description="ID of heuristic that supersedes this one"
    )
    
    @property
    def acceptance_rate(self) -> float:
        """Rate at which this heuristic is accepted when injected."""
        total = self.times_injected
        if total == 0:
            return 0.5  # No data
        return (self.times_accepted + 0.5 * self.times_modified) / total
    
    @property
    def is_well_validated(self) -> bool:
        """Whether this heuristic has been sufficiently validated."""
        return self.times_injected >= 5 and self.acceptance_rate >= 0.6


class SurgeonInput(BaseModel):
    """Input to the Surgeon for heuristic extraction."""
    
    conference_id: str
    conference_transcript: str = Field(
        ...,
        description="Full transcript of the conference deliberation"
    )
    final_consensus: str = Field(..., description="The final consensus recommendation")
    query: str = Field(..., description="Original query that started the conference")
    
    # Quality reports
    verified_citations: list[str] = Field(
        default_factory=list,
        description="PMIDs of verified citations"
    )
    failed_citations: list[str] = Field(
        default_factory=list,
        description="Citations that failed verification"
    )
    fragility_factors: list[str] = Field(
        default_factory=list,
        description="Perturbations that modified the recommendation"
    )
    
    # Gatekeeper info
    gatekeeper_flags: list[str] = Field(
        default_factory=list,
        description="Flags from Gatekeeper evaluation"
    )


class SurgeonOutput(BaseModel):
    """Output from the Surgeon."""
    
    extraction_successful: bool = Field(
        ...,
        description="Whether extraction succeeded"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="If failed, why"
    )
    artifact: Optional[ReasoningArtifact] = Field(
        default=None,
        description="The extracted heuristic if successful"
    )


class CollisionType(str, Enum):
    """Types of collisions between heuristics."""
    
    DIRECT_CONTRADICTION = "DIRECT_CONTRADICTION"  # A says X, B says not X
    SCOPE_OVERLAP = "SCOPE_OVERLAP"  # Same domain, different recommendations
    TEMPORAL = "TEMPORAL"  # Old vs new guidance
    PATIENT_SUBSET = "PATIENT_SUBSET"  # Different patient populations


class HeuristicCollision(BaseModel):
    """Detected collision between two heuristics."""
    
    heuristic_a_id: str
    heuristic_b_id: str
    collision_type: CollisionType
    resolution_hint: str = Field(
        ...,
        description="Guidance for resolving the collision"
    )


class InjectionContext(BaseModel):
    """Context for injecting heuristics into a conference."""
    
    query: str = Field(..., description="The current query")
    domain: Optional[str] = Field(default=None, description="Detected domain")
    patient_factors: list[str] = Field(
        default_factory=list,
        description="Detected patient factors"
    )


class InjectionResult(BaseModel):
    """Result of heuristic retrieval for injection."""
    
    heuristics_found: int = Field(
        default=0,
        description="Number of relevant heuristics found"
    )
    heuristics: list[ReasoningArtifact] = Field(
        default_factory=list,
        description="Retrieved heuristics"
    )
    collision: Optional[HeuristicCollision] = Field(
        default=None,
        description="Collision if multiple heuristics conflict"
    )
    injection_prompt: str = Field(
        default="",
        description="Formatted prompt to inject into conference"
    )
    genesis_mode: bool = Field(
        default=False,
        description="True if no relevant heuristics were found"
    )
    domain_coverage: int = Field(
        default=0,
        description="Total heuristics in this domain"
    )

