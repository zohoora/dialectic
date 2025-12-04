"""
Data models for the AI Case Conference system.

These Pydantic models define the core data structures used throughout
the conference system, from configuration to results.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from src.models.fragility import FragilityReport
    from src.models.grounding import GroundingReport


class AgentRole(str, Enum):
    """Epistemic roles that agents can assume in a conference."""
    
    ADVOCATE = "advocate"
    SKEPTIC = "skeptic"
    EMPIRICIST = "empiricist"
    MECHANIST = "mechanist"
    PATIENT_VOICE = "patient_voice"
    ARBITRATOR = "arbitrator"
    # v2.1 additions
    SPECULATOR = "speculator"
    PRAGMATIST = "pragmatist"


class ConferenceTopology(str, Enum):
    """Types of conference discussion structures."""
    
    FREE_DISCUSSION = "free_discussion"
    OXFORD_DEBATE = "oxford_debate"
    DELPHI_METHOD = "delphi_method"
    SOCRATIC_SPIRAL = "socratic_spiral"
    RED_TEAM_BLUE_TEAM = "red_team_blue_team"


class AgentConfig(BaseModel):
    """Configuration for a single agent in the conference."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    agent_id: str = Field(..., description="Unique identifier for this agent")
    role: AgentRole = Field(..., description="Epistemic role assigned to this agent")
    model: str = Field(..., description="LLM model identifier (e.g., 'anthropic/claude-3.5-sonnet')")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")


class ArbitratorConfig(BaseModel):
    """Configuration for the arbitrator agent."""
    
    model: str = Field(..., description="LLM model identifier for arbitrator")
    temperature: float = Field(default=0.5, ge=0.0, le=2.0)


class ConferenceConfig(BaseModel):
    """Complete configuration for a conference."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    topology: ConferenceTopology = Field(
        default=ConferenceTopology.FREE_DISCUSSION,
        description="Structure of agent interaction"
    )
    num_rounds: int = Field(default=2, ge=1, le=10, description="Number of deliberation rounds")
    agents: list[AgentConfig] = Field(..., description="List of participating agents")
    arbitrator: ArbitratorConfig = Field(..., description="Arbitrator configuration")


class AgentResponse(BaseModel):
    """Response from a single agent in a conference round."""
    
    agent_id: str = Field(..., description="ID of the responding agent")
    role: AgentRole = Field(..., description="Role of the agent")
    model: str = Field(..., description="Model used for this response")
    content: str = Field(..., description="Full response content")
    position_summary: str = Field(
        default="",
        description="One-line summary of agent's position"
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in their position (0-1)"
    )
    changed_from_previous: bool = Field(
        default=False,
        description="Whether agent changed position from previous round"
    )
    
    # Token usage tracking
    input_tokens: int = Field(default=0, description="Input tokens consumed")
    output_tokens: int = Field(default=0, description="Output tokens generated")
    
    model_config = ConfigDict(use_enum_values=True)


class ConferenceRound(BaseModel):
    """Results from a single round of conference deliberation."""
    
    round_number: int = Field(..., ge=1, description="Round number (1-indexed)")
    agent_responses: dict[str, AgentResponse] = Field(
        default_factory=dict,
        description="Responses keyed by agent_id"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this round was executed"
    )
    # Grounding results for this round (optional, added in Phase 2)
    grounding_results: Optional["GroundingReport"] = Field(
        default=None,
        description="Citation verification results for this round"
    )


class ConferenceSynthesis(BaseModel):
    """Final synthesized output from the arbitrator."""
    
    final_consensus: str = Field(..., description="The synthesized recommendation")
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Overall confidence level"
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Key points of agreement"
    )
    evidence_summary: str = Field(
        default="",
        description="Summary of supporting evidence"
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Important caveats or limitations"
    )


class DissentRecord(BaseModel):
    """Record of any preserved dissent from the conference."""
    
    preserved: bool = Field(
        default=False,
        description="Whether dissent was preserved"
    )
    dissenting_agent: Optional[str] = Field(
        default=None,
        description="Agent ID of the dissenter"
    )
    dissenting_role: Optional[AgentRole] = Field(
        default=None,
        description="Role of the dissenting agent"
    )
    summary: str = Field(
        default="",
        description="Summary of the dissenting position"
    )
    reasoning: str = Field(
        default="",
        description="Reasoning behind the dissent"
    )
    strength: str = Field(
        default="",
        description="Strength of dissent: 'Strong', 'Moderate', 'Weak'"
    )
    
    model_config = ConfigDict(use_enum_values=True)


class TokenUsage(BaseModel):
    """Token usage statistics for a conference."""
    
    total_input_tokens: int = Field(default=0)
    total_output_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    estimated_cost_usd: float = Field(default=0.0)


class ConferenceResult(BaseModel):
    """Complete result from a conference execution."""
    
    conference_id: str = Field(..., description="Unique ID for this conference")
    query: str = Field(..., description="Original query text")
    
    config: ConferenceConfig = Field(..., description="Configuration used")
    rounds: list[ConferenceRound] = Field(
        default_factory=list,
        description="All deliberation rounds"
    )
    synthesis: ConferenceSynthesis = Field(..., description="Final synthesis")
    dissent: DissentRecord = Field(
        default_factory=DissentRecord,
        description="Any preserved dissent"
    )
    
    # Grounding report (added in Phase 2)
    grounding_report: Optional["GroundingReport"] = Field(
        default=None,
        description="Combined citation verification results"
    )
    
    # Fragility report (added in Phase 3)
    fragility_report: Optional["FragilityReport"] = Field(
        default=None,
        description="Stress test results for the recommendation"
    )
    
    token_usage: TokenUsage = Field(
        default_factory=TokenUsage,
        description="Token usage statistics"
    )
    duration_ms: int = Field(default=0, description="Total duration in milliseconds")
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the conference was run"
    )
    
    model_config = ConfigDict(use_enum_values=True)


class LLMResponse(BaseModel):
    """Response from an LLM API call."""
    
    content: str = Field(..., description="Response content")
    model: str = Field(..., description="Model that generated the response")
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    finish_reason: str = Field(default="stop")


# Import and resolve forward references for grounding and fragility models
# This must be done after all classes are defined
def _resolve_forward_refs():
    """Resolve forward references for Pydantic models."""
    from src.models.fragility import FragilityReport
    from src.models.grounding import GroundingReport
    ConferenceRound.model_rebuild()
    ConferenceResult.model_rebuild()


_resolve_forward_refs()
