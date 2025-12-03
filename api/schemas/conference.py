"""Conference API schemas."""

from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class TopologyType(str, Enum):
    """Available conference topologies."""
    FREE_DISCUSSION = "free_discussion"
    OXFORD_DEBATE = "oxford_debate"
    DELPHI_METHOD = "delphi_method"
    SOCRATIC_SPIRAL = "socratic_spiral"
    RED_TEAM = "red_team"


class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    role: str
    model: str


class LibrarianConfig(BaseModel):
    """Configuration for the librarian agent."""
    model: str = "google/gemini-3-pro-preview"
    max_queries_per_turn: int = 3


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


class StreamEvent(BaseModel):
    """Event sent via SSE during conference."""
    event: StreamEventType
    data: dict = Field(default_factory=dict)

