"""
Base topology class and factory for conference topologies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, TYPE_CHECKING

from src.conference.agent import Agent
from src.models.conference import AgentResponse, ConferenceRound, ConferenceTopology

if TYPE_CHECKING:
    from src.conference.round_executor import ProgressUpdate


class ProgressStage(str, Enum):
    """Stages of conference execution for progress tracking."""
    INITIALIZING = "initializing"
    ROUND_START = "round_start"
    AGENT_THINKING = "agent_thinking"
    AGENT_COMPLETE = "agent_complete"
    ROUND_COMPLETE = "round_complete"
    GROUNDING = "grounding"
    ARBITRATION = "arbitration"
    FRAGILITY_START = "fragility_start"
    FRAGILITY_TEST = "fragility_test"
    COMPLETE = "complete"


@dataclass
class ProgressUpdate:
    """Progress update event for UI callbacks."""
    stage: ProgressStage
    message: str
    percent: int
    detail: dict = field(default_factory=dict)


class BaseTopology(ABC):
    """
    Abstract base class for conference topologies.
    
    Each topology defines how agents interact during deliberation rounds.
    """
    
    def __init__(self, agents: list[Agent], librarian_service=None):
        """
        Initialize the topology.
        
        Args:
            agents: List of agents participating in the conference
            librarian_service: Optional librarian service for document queries
        """
        self.agents = agents
        self._agents_by_id = {a.agent_id: a for a in agents}
        self._agents_by_role = {a.role: a for a in agents}
        self.librarian_service = librarian_service
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the topology name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a brief description of this topology."""
        pass
    
    @property
    def minimum_rounds(self) -> int:
        """Minimum rounds required for this topology."""
        return 1  # Default allows single round
    
    @property
    def required_roles(self) -> list[str]:
        """Roles required for this topology (empty = any roles work)."""
        return []
    
    def validate_agents(self) -> tuple[bool, str]:
        """
        Validate that the agents meet this topology's requirements.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.required_roles:
            agent_roles = {a.role for a in self.agents}
            missing = set(self.required_roles) - agent_roles
            if missing:
                return False, f"Missing required roles: {missing}"
        return True, ""
    
    @abstractmethod
    async def execute_round(
        self,
        query: str,
        round_number: int,
        previous_rounds: list[ConferenceRound],
        injection_prompts: Optional[dict[str, str]] = None,
        progress_callback: Optional[Callable[["ProgressUpdate"], None]] = None,
        round_base_percent: int = 0,
        percent_per_agent: int = 10,
    ) -> ConferenceRound:
        """
        Execute a single round according to this topology's rules.
        
        Args:
            query: The clinical question
            round_number: Current round number (1-indexed)
            previous_rounds: All previous rounds
            injection_prompts: Optional heuristic injection prompts
            progress_callback: Progress callback function
            round_base_percent: Base progress percent for this round
            percent_per_agent: Progress percent to allocate per agent
            
        Returns:
            ConferenceRound with agent responses
        """
        pass
    
    async def execute_all_rounds(
        self,
        query: str,
        num_rounds: int,
        agent_injection_prompts: Optional[dict[str, str]] = None,
        progress_callback: Optional[Callable[["ProgressUpdate"], None]] = None,
        base_percent: int = 0,
        percent_allocation: int = 60,
    ) -> list[ConferenceRound]:
        """
        Execute all deliberation rounds.
        
        Args:
            query: The clinical question
            num_rounds: Total number of rounds
            agent_injection_prompts: Optional injection prompts
            progress_callback: Progress callback
            base_percent: Starting percent
            percent_allocation: Total percent allocation
            
        Returns:
            List of ConferenceRound objects
        """
        # Enforce minimum rounds
        num_rounds = max(num_rounds, self.minimum_rounds)
        
        rounds = []
        percent_per_round = percent_allocation // num_rounds
        percent_per_agent = percent_per_round // max(1, len(self.agents))
        
        for round_num in range(1, num_rounds + 1):
            round_base = base_percent + (round_num - 1) * percent_per_round
            
            # Report round start
            if progress_callback:
                progress_callback(ProgressUpdate(
                    stage=ProgressStage.ROUND_START,
                    message=f"Starting Round {round_num} of {num_rounds}...",
                    percent=round_base,
                    detail={"round_number": round_num, "total_rounds": num_rounds},
                ))
            
            # Execute round
            round_result = await self.execute_round(
                query=query,
                round_number=round_num,
                previous_rounds=rounds,
                injection_prompts=agent_injection_prompts if round_num == 1 else None,
                progress_callback=progress_callback,
                round_base_percent=round_base,
                percent_per_agent=percent_per_agent,
            )
            rounds.append(round_result)
            
            # Report round complete
            if progress_callback:
                progress_callback(ProgressUpdate(
                    stage=ProgressStage.ROUND_COMPLETE,
                    message=f"Round {round_num} complete",
                    percent=round_base + percent_per_round,
                    detail={"round_number": round_num, "agent_count": len(self.agents)},
                ))
        
        return rounds
    
    def _get_role_display(self, role: str) -> str:
        """Get display name for a role."""
        role_displays = {
            "advocate": "Advocate",
            "skeptic": "Skeptic",
            "empiricist": "Empiricist",
            "mechanist": "Mechanist",
            "patient_voice": "Patient Voice",
            "arbitrator": "Arbitrator",
        }
        return role_displays.get(role, role.title())
    
    def _report_progress(
        self,
        callback: Optional[Callable[["ProgressUpdate"], None]],
        stage: ProgressStage,
        message: str,
        percent: int,
        **detail,
    ):
        """Helper to report progress."""
        if callback:
            callback(ProgressUpdate(
                stage=stage,
                message=message,
                percent=percent,
                detail=detail,
            ))
    
    async def _process_librarian_queries(
        self,
        agent_id: str,
        response: AgentResponse,
        round_number: int,
    ) -> AgentResponse:
        """
        Process librarian queries in an agent's response.
        
        Args:
            agent_id: The agent's ID
            response: The agent's response
            round_number: Current round number
            
        Returns:
            Updated AgentResponse with librarian answers appended (if any)
        """
        if self.librarian_service is None:
            return response
        
        queries = await self.librarian_service.process_agent_queries(
            agent_id=agent_id,
            response_text=response.content,
            round_number=round_number,
        )
        
        if not queries:
            return response
        
        # Format answers and append to response
        librarian_answers = self.librarian_service.format_query_answers(queries)
        
        return AgentResponse(
            agent_id=response.agent_id,
            role=response.role,
            model=response.model,
            content=response.content + librarian_answers,
            position_summary=response.position_summary,
            confidence=response.confidence,
            changed_from_previous=response.changed_from_previous,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )


class TopologyFactory:
    """Factory for creating topology instances."""
    
    @staticmethod
    def create(
        topology_type: ConferenceTopology,
        agents: list[Agent],
        librarian_service=None,
    ) -> BaseTopology:
        """
        Create a topology instance.
        
        Args:
            topology_type: The topology type enum
            agents: List of agents
            librarian_service: Optional librarian service for document queries
            
        Returns:
            Topology instance
            
        Raises:
            ValueError: If topology type is not supported
        """
        from src.conference.topologies.free_discussion import FreeDiscussionTopology
        from src.conference.topologies.oxford_debate import OxfordDebateTopology
        from src.conference.topologies.delphi_method import DelphiMethodTopology
        from src.conference.topologies.socratic_spiral import SocraticSpiralTopology
        from src.conference.topologies.red_team import RedTeamBlueTeamTopology
        
        topology_map = {
            ConferenceTopology.FREE_DISCUSSION: FreeDiscussionTopology,
            ConferenceTopology.OXFORD_DEBATE: OxfordDebateTopology,
            ConferenceTopology.DELPHI_METHOD: DelphiMethodTopology,
            ConferenceTopology.SOCRATIC_SPIRAL: SocraticSpiralTopology,
            ConferenceTopology.RED_TEAM_BLUE_TEAM: RedTeamBlueTeamTopology,
        }
        
        topology_class = topology_map.get(topology_type)
        if not topology_class:
            raise ValueError(f"Unknown topology: {topology_type}")
        
        topology = topology_class(agents, librarian_service=librarian_service)
        
        # Validate agents for this topology
        is_valid, error = topology.validate_agents()
        if not is_valid:
            raise ValueError(f"Invalid agents for {topology.name}: {error}")
        
        return topology

