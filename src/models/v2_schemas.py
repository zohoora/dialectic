"""
AI Case Conference System v2.1 - Data Schemas

These Pydantic models support the "Adversarial MoE" architecture with:
- Intelligent routing
- Lane-based parallel execution
- Scout (live literature)
- Speculation library
- Bifurcated output (Clinical + Exploratory)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# ENUMERATIONS
# =============================================================================


class ConferenceMode(str, Enum):
    """The routing mode determined by the Intelligent Router."""

    STANDARD_CARE = "STANDARD_CARE"  # Simple guideline check
    COMPLEX_DILEMMA = "COMPLEX_DILEMMA"  # Multi-factor decision
    NOVEL_RESEARCH = "NOVEL_RESEARCH"  # Experimental territory
    DIAGNOSTIC_PUZZLE = "DIAGNOSTIC_PUZZLE"  # Unclear diagnosis


class Lane(str, Enum):
    """The two reasoning lanes in v2.1 architecture."""

    CLINICAL = "A"  # Lane A: Safety, guidelines, evidence
    EXPLORATORY = "B"  # Lane B: Mechanism, novelty, theory


class EvidenceGrade(str, Enum):
    """Evidence quality grading for Scout findings."""

    META_ANALYSIS = "meta_analysis"  # Systematic review / Cochrane
    RCT_LARGE = "rct_large"  # RCT n > 100
    RCT_SMALL = "rct_small"  # RCT n < 100
    OBSERVATIONAL = "observational"  # Cohort, case-control
    PREPRINT = "preprint"  # Not peer-reviewed
    CASE_REPORT = "case_report"  # Single case
    CONFLICTING = "conflicting"  # Contradicts consensus
    EXPERT_OPINION = "expert_opinion"  # No primary data


class SpeculationStatus(str, Enum):
    """Lifecycle status of a speculation in the library."""

    UNVERIFIED = "UNVERIFIED"  # Initial state
    WATCHING = "WATCHING"  # On watch list
    EVIDENCE_FOUND = "EVIDENCE_FOUND"  # New evidence detected
    PARTIALLY_VALIDATED = "PARTIALLY_VALIDATED"  # Some support
    VALIDATED = "VALIDATED"  # Ready for Experience Library
    CONTRADICTED = "CONTRADICTED"  # Evidence against
    DEPRECATED = "DEPRECATED"  # Removed


class CitationStatus(str, Enum):
    """Status of a citation after grounding."""

    VERIFIED = "VERIFIED"
    NOT_FOUND = "NOT_FOUND"
    YEAR_MISMATCH = "YEAR_MISMATCH"
    AUTHOR_MISMATCH = "AUTHOR_MISMATCH"
    CONTENT_UNVERIFIED = "CONTENT_UNVERIFIED"  # Exists but claim not checked


# =============================================================================
# PATIENT CONTEXT
# =============================================================================


class PatientContext(BaseModel):
    """Patient information provided with the query."""

    model_config = ConfigDict(use_enum_values=True)

    age: Optional[int] = Field(default=None, ge=0, le=150)
    sex: Optional[Literal["male", "female", "other"]] = None
    comorbidities: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    failed_treatments: list[str] = Field(default_factory=list)
    relevant_history: Optional[str] = None
    constraints: list[str] = Field(
        default_factory=list,
        description="e.g., needle phobia, cost sensitive, rural location",
    )


# =============================================================================
# ROUTING SCHEMAS
# =============================================================================


class RoutingDecision(BaseModel):
    """Output of the Intelligent Router."""

    model_config = ConfigDict(use_enum_values=True)

    mode: ConferenceMode
    active_agents: list[str] = Field(
        description="List of agent roles to activate (e.g., 'empiricist', 'speculator')"
    )
    activate_scout: bool = Field(default=False)
    risk_profile: float = Field(ge=0.0, le=1.0, default=0.5)
    routing_rationale: str = Field(default="")
    complexity_signals_detected: list[str] = Field(default_factory=list)
    estimated_rounds: int = Field(default=4)

    @property
    def lane_a_agents(self) -> list[str]:
        """Agents assigned to Lane A (Clinical)."""
        clinical_agents = {"empiricist", "skeptic", "pragmatist", "patient_voice"}
        return [a for a in self.active_agents if a in clinical_agents]

    @property
    def lane_b_agents(self) -> list[str]:
        """Agents assigned to Lane B (Exploratory)."""
        exploratory_agents = {"mechanist", "speculator"}
        return [a for a in self.active_agents if a in exploratory_agents]


# =============================================================================
# SCOUT SCHEMAS
# =============================================================================


class ScoutCitation(BaseModel):
    """A single citation found by the Scout."""

    title: str
    authors: list[str] = Field(default_factory=list)
    journal: Optional[str] = None
    year: int
    pmid: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    evidence_grade: EvidenceGrade
    sample_size: Optional[int] = None
    is_preprint: bool = False
    source_url: Optional[str] = None

    # Scout's assessment
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.5)
    key_finding: str = Field(default="")  # One-sentence summary
    conflicts_with_consensus: bool = False


class ScoutReport(BaseModel):
    """Complete output from the Scout."""

    scout_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_keywords: list[str] = Field(default_factory=list)
    search_date: datetime = Field(default_factory=datetime.utcnow)
    date_range_months: int = 12

    # Categorized findings
    meta_analyses: list[ScoutCitation] = Field(default_factory=list)
    high_quality_rcts: list[ScoutCitation] = Field(default_factory=list)
    preliminary_evidence: list[ScoutCitation] = Field(default_factory=list)
    conflicting_evidence: list[ScoutCitation] = Field(default_factory=list)

    # Metadata
    total_results_found: int = 0
    results_after_filtering: int = 0
    is_empty: bool = False
    search_queries_used: list[str] = Field(default_factory=list)

    def to_context_block(self) -> str:
        """Format the Scout report for injection into agent context."""
        if self.is_empty:
            return """
# SCOUT REPORT: NO RECENT EVIDENCE FOUND

No publications matching the query were found in the last 12 months.
Recommendations will be based on established evidence only.
"""

        lines = ["# SCOUT REPORT: EMERGING EVIDENCE (Last 12 Months)\n"]

        if self.meta_analyses:
            lines.append("## Meta-Analyses / Systematic Reviews (HIGHEST WEIGHT)")
            lines.append(
                "These synthesize multiple studies. May significantly update priors.\n"
            )
            for c in self.meta_analyses:
                lines.append(f"* **{c.title}** ({c.year})")
                lines.append(f"  - Finding: {c.key_finding}")
                if c.pmid:
                    lines.append(f"  - PMID: {c.pmid}")
                lines.append("")

        if self.high_quality_rcts:
            lines.append("## Peer-Reviewed RCTs (HIGH WEIGHT)")
            lines.append("Can update priors if methodology is sound.\n")
            for c in self.high_quality_rcts:
                n_str = f" (n={c.sample_size})" if c.sample_size else ""
                lines.append(f"* **{c.title}**{n_str} ({c.year})")
                lines.append(f"  - Finding: {c.key_finding}")
                if c.pmid:
                    lines.append(f"  - PMID: {c.pmid}")
                lines.append("")

        if self.preliminary_evidence:
            lines.append("## Preliminary Evidence (SIGNALS ONLY)")
            lines.append("Treat as signals. Do NOT present as established fact.\n")
            for c in self.preliminary_evidence:
                preprint_flag = " [PREPRINT]" if c.is_preprint else ""
                lines.append(f"* **{c.title}**{preprint_flag} ({c.year})")
                lines.append(f"  - Finding: {c.key_finding}")
                lines.append("")

        if self.conflicting_evidence:
            lines.append("## Conflicting / Contested Evidence")
            lines.append(
                "Acknowledge the conflict. Do NOT auto-resolve in favor of recency.\n"
            )
            for c in self.conflicting_evidence:
                lines.append(f"* **{c.title}** ({c.year})")
                lines.append(f"  - Finding: {c.key_finding}")
                lines.append(f"  - **Conflict:** This contradicts established consensus.")
                lines.append("")

        lines.append("---")
        lines.append("**Instructions for agents:** Weight evidence according to grade.")
        lines.append("Recency does NOT equal reliability. A 2025 preprint with n=12")
        lines.append("should NOT override 20 years of replicated RCTs.")

        return "\n".join(lines)


# =============================================================================
# CROSS-EXAMINATION SCHEMAS
# =============================================================================


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


# =============================================================================
# ARBITRATOR SYNTHESIS SCHEMAS (BIFURCATED OUTPUT)
# =============================================================================


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
    """Complete synthesis from the Arbitrator (v2.1 bifurcated format)."""

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


# =============================================================================
# SPECULATION LIBRARY SCHEMAS
# =============================================================================


class Speculation(BaseModel):
    """A hypothesis stored in the Speculation Library."""

    speculation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Origin
    origin_conference_id: str = ""
    origin_query: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # The hypothesis
    hypothesis: str
    mechanism: str = ""
    source_agent: str = "speculator"

    # Confidence and validation
    initial_confidence: Literal["low", "medium", "high"] = "low"
    validation_criteria: str = ""  # What would prove this
    evidence_needed: str = ""  # Specific study type needed

    # Watch list
    watch_keywords: list[str] = Field(default_factory=list)

    # Lifecycle
    status: SpeculationStatus = SpeculationStatus.UNVERIFIED
    last_checked: Optional[datetime] = None
    evidence_found: list[ScoutCitation] = Field(default_factory=list)

    # If validated
    promoted_to_experience_library: bool = False
    experience_library_id: Optional[str] = None


class WatchListTrigger(BaseModel):
    """Event when Scout finds evidence matching a speculation."""

    trigger_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    speculation_id: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    matching_citations: list[ScoutCitation] = Field(default_factory=list)
    match_quality: Literal["exact", "partial", "weak"] = "partial"
    requires_human_review: bool = True
    auto_action_taken: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validating a speculation against new evidence."""

    speculation_id: str
    validation_date: datetime = Field(default_factory=datetime.utcnow)

    new_evidence: list[ScoutCitation] = Field(default_factory=list)
    support_level: Literal[
        "confirms", "partially_supports", "inconclusive", "contradicts"
    ] = "inconclusive"
    evidence_quality: EvidenceGrade = EvidenceGrade.OBSERVATIONAL

    action: Literal[
        "promote_to_experience_library", "upgrade_status", "keep_watching", "deprecate"
    ] = "keep_watching"
    new_status: SpeculationStatus = SpeculationStatus.WATCHING
    requires_human_review: bool = True
    validation_notes: str = ""


# =============================================================================
# CONFERENCE STATE (for orchestration)
# =============================================================================


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
    """Extended state for v2.1 conference orchestration."""

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


# =============================================================================
# CLASSIFIED QUERY (Extended from v1.0)
# =============================================================================


class ClassifiedQuery(BaseModel):
    """Query after classification (extended for v2.1)."""

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

