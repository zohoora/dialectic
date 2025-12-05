"""Conference API schemas."""

from typing import Literal, Optional
from pydantic import BaseModel, Field
from enum import Enum


class TopologyType(str, Enum):
    """Available conference topologies."""
    FREE_DISCUSSION = "free_discussion"
    OXFORD_DEBATE = "oxford_debate"
    DELPHI_METHOD = "delphi_method"
    SOCRATIC_SPIRAL = "socratic_spiral"
    RED_TEAM = "red_team"


class ConferenceModeType(str, Enum):
    """v2.1 conference modes (from intelligent routing)."""
    STANDARD_CARE = "STANDARD_CARE"
    COMPLEX_DILEMMA = "COMPLEX_DILEMMA"
    NOVEL_RESEARCH = "NOVEL_RESEARCH"
    DIAGNOSTIC_PUZZLE = "DIAGNOSTIC_PUZZLE"


class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    role: str
    model: str


class LibrarianConfig(BaseModel):
    """Configuration for the librarian agent."""
    model: str = "google/gemini-3-pro-preview"
    max_queries_per_turn: int = 3


class PatientContextRequest(BaseModel):
    """Patient context for v2.1 routing."""
    age: Optional[int] = Field(default=None, ge=0, le=150)
    sex: Optional[Literal["male", "female", "other"]] = None
    comorbidities: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    failed_treatments: list[str] = Field(default_factory=list)
    relevant_history: Optional[str] = None
    constraints: list[str] = Field(default_factory=list, description="e.g., cost sensitive, needle phobia")


class ConferenceRequest(BaseModel):
    """Request to start a new conference."""
    query: str = Field(..., min_length=10, description="Clinical question to deliberate")
    agents: list[AgentConfig] = Field(..., min_length=2, description="Agents to participate")
    arbitrator_model: str = Field(default="anthropic/claude-sonnet-4", description="Model for synthesis")
    num_rounds: int = Field(default=2, ge=1, le=5, description="Number of deliberation rounds")
    topology: TopologyType = Field(default=TopologyType.FREE_DISCUSSION)
    enable_grounding: bool = Field(default=True, description="Verify citations via PubMed")
    enable_fragility: bool = Field(default=False, description="Run fragility testing")
    fragility_tests: int = Field(default=3, ge=1, le=10)
    fragility_model: str = Field(default="anthropic/claude-sonnet-4")
    librarian: Optional[LibrarianConfig] = None
    # v2.1 additions
    patient_context: Optional[PatientContextRequest] = Field(default=None, description="Patient context for routing")
    enable_v2: bool = Field(default=False, description="Use v2.1 lane-based architecture")
    enable_scout: bool = Field(default=True, description="Enable Scout literature search (v2.1)")
    enable_routing: bool = Field(default=True, description="Enable intelligent routing (v2.1)")


class AgentResponse(BaseModel):
    """Single agent response in a round."""
    role: str
    model: str
    content: str
    confidence: float
    changed_from_previous: bool = False


class RoundResult(BaseModel):
    """Result of a single deliberation round."""
    round_number: int
    responses: list[AgentResponse]


class SynthesisResult(BaseModel):
    """Arbitrator synthesis."""
    final_consensus: str
    confidence: float
    model: str


class DissentResult(BaseModel):
    """Preserved dissent."""
    preserved: list[str]
    rationale: str


class ConferenceResponse(BaseModel):
    """Complete conference result."""
    conference_id: str
    query: str
    rounds: list[RoundResult]
    synthesis: SynthesisResult
    dissent: DissentResult
    total_tokens: int
    total_cost: float
    duration_ms: int


class StreamEventType(str, Enum):
    """Types of streaming events."""
    CONFERENCE_START = "conference_start"
    LIBRARIAN_START = "librarian_start"
    LIBRARIAN_COMPLETE = "librarian_complete"
    ROUND_START = "round_start"
    AGENT_THINKING = "agent_thinking"
    AGENT_TOKEN = "agent_token"
    AGENT_COMPLETE = "agent_complete"
    ROUND_COMPLETE = "round_complete"
    GROUNDING_START = "grounding_start"
    GROUNDING_COMPLETE = "grounding_complete"
    ARBITRATION_START = "arbitration_start"
    ARBITRATION_TOKEN = "arbitration_token"
    ARBITRATION_COMPLETE = "arbitration_complete"
    FRAGILITY_START = "fragility_start"
    FRAGILITY_TEST = "fragility_test"
    FRAGILITY_COMPLETE = "fragility_complete"
    CONFERENCE_COMPLETE = "conference_complete"
    ERROR = "error"
    # v2.1 events
    ROUTING_START = "routing_start"
    ROUTING_COMPLETE = "routing_complete"
    SCOUT_START = "scout_start"
    SCOUT_COMPLETE = "scout_complete"
    LANE_A_START = "lane_a_start"
    LANE_A_AGENT = "lane_a_agent"
    LANE_A_COMPLETE = "lane_a_complete"
    LANE_B_START = "lane_b_start"
    LANE_B_AGENT = "lane_b_agent"
    LANE_B_COMPLETE = "lane_b_complete"
    CROSS_EXAM_START = "cross_exam_start"
    CROSS_EXAM_CRITIQUE = "cross_exam_critique"
    CROSS_EXAM_COMPLETE = "cross_exam_complete"
    FEASIBILITY_START = "feasibility_start"
    FEASIBILITY_COMPLETE = "feasibility_complete"


class StreamEvent(BaseModel):
    """Event sent via SSE during conference."""
    event: StreamEventType
    data: dict = Field(default_factory=dict)


# =============================================================================
# v2.1 RESPONSE SCHEMAS
# =============================================================================


class ScoutCitationResponse(BaseModel):
    """Scout citation in response."""
    title: str
    authors: list[str] = Field(default_factory=list)
    journal: Optional[str] = None
    year: int
    pmid: Optional[str] = None
    evidence_grade: str  # meta_analysis, rct_large, etc.
    key_finding: str = ""


class ScoutReportResponse(BaseModel):
    """Scout report in response."""
    is_empty: bool = False
    query_keywords: list[str] = Field(default_factory=list)
    meta_analyses: list[ScoutCitationResponse] = Field(default_factory=list)
    high_quality_rcts: list[ScoutCitationResponse] = Field(default_factory=list)
    preliminary_evidence: list[ScoutCitationResponse] = Field(default_factory=list)
    conflicting_evidence: list[ScoutCitationResponse] = Field(default_factory=list)
    total_found: int = 0


class TopologyType(str, Enum):
    """v3: Selected deliberation topology."""
    FREE_DISCUSSION = "free_discussion"
    OXFORD_DEBATE = "oxford_debate"
    DELPHI_METHOD = "delphi_method"
    SOCRATIC_SPIRAL = "socratic_spiral"
    RED_TEAM_BLUE_TEAM = "red_team_blue_team"


class RoutingResponse(BaseModel):
    """Routing decision in response (v3: includes topology)."""
    mode: ConferenceModeType
    active_agents: list[str]
    activate_scout: bool
    rationale: str = ""
    complexity_signals: list[str] = Field(default_factory=list)
    # v3: topology fields
    topology: TopologyType = TopologyType.FREE_DISCUSSION
    topology_rationale: str = ""
    topology_signals: list[str] = Field(default_factory=list)


class ClinicalConsensusResponse(BaseModel):
    """Clinical consensus (Lane A output)."""
    recommendation: str
    evidence_basis: list[str] = Field(default_factory=list)
    confidence: float
    safety_profile: str = ""
    contraindications: list[str] = Field(default_factory=list)


class ExploratoryConsiderationResponse(BaseModel):
    """Exploratory consideration (Lane B output)."""
    hypothesis: str
    mechanism: str = ""
    evidence_level: str = "theoretical"
    potential_benefit: str = ""
    risks: list[str] = Field(default_factory=list)
    what_would_validate: str = ""


class TensionResponse(BaseModel):
    """Tension between lanes."""
    description: str
    lane_a_position: str = ""
    lane_b_position: str = ""
    resolution: str = "unresolved"


class V2SynthesisResponse(BaseModel):
    """v2.1 bifurcated synthesis response."""
    clinical_consensus: ClinicalConsensusResponse
    exploratory_considerations: list[ExploratoryConsiderationResponse] = Field(default_factory=list)
    tensions: list[TensionResponse] = Field(default_factory=list)
    safety_concerns: list[str] = Field(default_factory=list)
    stagnation_concerns: list[str] = Field(default_factory=list)
    what_would_change: str = ""
    preserved_dissent: list[str] = Field(default_factory=list)
    overall_confidence: float


class LaneResultResponse(BaseModel):
    """Result from one lane."""
    lane: str  # "A" or "B"
    responses: list[AgentResponse] = Field(default_factory=list)


class V2ConferenceResponse(BaseModel):
    """v2.1 conference result."""
    conference_id: str
    query: str
    mode: ConferenceModeType
    routing: RoutingResponse
    scout_report: Optional[ScoutReportResponse] = None
    lane_a: Optional[LaneResultResponse] = None
    lane_b: Optional[LaneResultResponse] = None
    synthesis: V2SynthesisResponse
    # Legacy compatibility
    legacy_synthesis: Optional[SynthesisResult] = None
    legacy_dissent: Optional[DissentResult] = None
    # Metadata
    total_tokens: int = 0
    total_cost: float = 0.0
    duration_ms: int = 0

