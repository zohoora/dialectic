"""
AI Case Conference System - Routing Schemas

Models for intelligent query routing and topology selection.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.models.conference import ConferenceTopology
from src.models.enums import ConferenceMode


class RoutingDecision(BaseModel):
    """Output of the Intelligent Router (v3: with topology selection)."""

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
    
    # v3: Topology selection
    topology: ConferenceTopology = Field(
        default=ConferenceTopology.FREE_DISCUSSION,
        description="Selected deliberation topology based on query analysis"
    )
    topology_signals_detected: list[str] = Field(
        default_factory=list,
        description="Signals that influenced topology selection"
    )
    topology_rationale: str = Field(
        default="",
        description="Explanation for topology selection"
    )
    
    # v3: Lane-specific topologies (optional, for advanced scenarios)
    lane_a_topology: Optional[ConferenceTopology] = Field(
        default=None,
        description="Override topology for Lane A (Clinical). If None, uses main topology."
    )
    lane_b_topology: Optional[ConferenceTopology] = Field(
        default=None,
        description="Override topology for Lane B (Exploratory). If None, uses main topology."
    )

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
    
    @property
    def effective_lane_a_topology(self) -> ConferenceTopology:
        """Get the effective topology for Lane A."""
        return self.lane_a_topology or self.topology
    
    @property
    def effective_lane_b_topology(self) -> ConferenceTopology:
        """Get the effective topology for Lane B."""
        return self.lane_b_topology or self.topology

