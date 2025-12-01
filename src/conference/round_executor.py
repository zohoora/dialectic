"""
Round executor for conference deliberation.

Handles executing rounds of agent responses, including:
- Round 1: Independent responses to the query
- Round 2+: Responses after seeing other agents' positions
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from src.conference.agent import Agent
from src.models.conference import AgentResponse, ConferenceRound


# Import progress types from engine (avoid circular import by using TYPE_CHECKING)
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


class RoundExecutor:
    """
    Executes rounds of agent deliberation.
    
    Manages parallel execution of agent responses and collects
    results into ConferenceRound objects.
    """
    
    def __init__(self, agents: list[Agent]):
        """
        Initialize the round executor.
        
        Args:
            agents: List of agents participating in the conference
        """
        self.agents = agents
        self._agents_by_id = {a.agent_id: a for a in agents}
    
    async def execute_round_one(
        self, 
        query: str,
        injection_prompts: Optional[dict[str, str]] = None,
    ) -> ConferenceRound:
        """
        Execute Round 1: All agents respond independently to the query.
        
        Agents respond in parallel since they don't see each other's responses.
        
        Args:
            query: The clinical question to analyze
            injection_prompts: Optional dict of agent_id -> injection prompt to prepend
        
        Returns:
            ConferenceRound with all agent responses
        """
        # Build query with injection if provided
        def get_injected_query(agent_id: str) -> str:
            if injection_prompts and agent_id in injection_prompts:
                return injection_prompts[agent_id] + "\n\n" + query
            return query
        
        # Execute all agents in parallel
        tasks = [
            agent.respond_to_query(get_injected_query(agent.agent_id))
            for agent in self.agents
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Build response dictionary
        agent_responses = {
            response.agent_id: response
            for response in responses
        }
        
        return ConferenceRound(
            round_number=1,
            agent_responses=agent_responses,
        )
    
    async def execute_followup_round(
        self,
        query: str,
        previous_round: ConferenceRound,
        round_number: int,
    ) -> ConferenceRound:
        """
        Execute a follow-up round where agents see others' positions.
        
        Each agent sees all other agents' previous responses and can
        critique, refine, or change their position.
        
        Args:
            query: The original clinical question
            previous_round: The previous round's results
            round_number: The current round number (2+)
        
        Returns:
            ConferenceRound with updated agent responses
        """
        tasks = []
        
        for agent in self.agents:
            # Build dict of other agents' responses for this agent to see
            other_responses = {
                self._get_role_display(resp.role): resp.content
                for agent_id, resp in previous_round.agent_responses.items()
                if agent_id != agent.agent_id
            }
            
            task = agent.respond_to_discussion(
                query=query,
                previous_responses=other_responses,
                round_number=round_number,
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        agent_responses = {
            response.agent_id: response
            for response in responses
        }
        
        return ConferenceRound(
            round_number=round_number,
            agent_responses=agent_responses,
        )
    
    async def execute_all_rounds(
        self,
        query: str,
        num_rounds: int,
        agent_injection_prompts: Optional[dict[str, str]] = None,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
        base_percent: int = 0,
        percent_allocation: int = 60,
    ) -> list[ConferenceRound]:
        """
        Execute all deliberation rounds.
        
        Args:
            query: The clinical question
            num_rounds: Total number of rounds to execute
            agent_injection_prompts: Optional dict of agent_id -> injection prompt to prepend
            progress_callback: Optional callback for progress updates
            base_percent: Starting percent for progress tracking
            percent_allocation: Total percent to allocate across all rounds
        
        Returns:
            List of ConferenceRound objects, one per round
        """
        rounds = []
        num_agents = len(self.agents)
        
        # Calculate progress per round and per agent
        percent_per_round = percent_allocation // num_rounds
        percent_per_agent = percent_per_round // num_agents
        
        # Helper to report progress
        def report_progress(stage: ProgressStage, message: str, percent: int, **detail):
            if progress_callback:
                progress_callback(ProgressUpdate(
                    stage=stage,
                    message=message,
                    percent=percent,
                    detail=detail,
                ))
        
        # Round 1: Independent responses (with injection if provided)
        report_progress(
            ProgressStage.ROUND_START,
            f"Starting Round 1 of {num_rounds}...",
            base_percent,
            round_number=1,
            total_rounds=num_rounds,
        )
        
        round_one = await self._execute_round_with_progress(
            query=query,
            round_number=1,
            previous_round=None,
            injection_prompts=agent_injection_prompts,
            progress_callback=progress_callback,
            round_base_percent=base_percent,
            percent_per_agent=percent_per_agent,
        )
        rounds.append(round_one)
        
        report_progress(
            ProgressStage.ROUND_COMPLETE,
            f"Round 1 complete",
            base_percent + percent_per_round,
            round_number=1,
            agent_count=num_agents,
        )
        
        # Subsequent rounds: See others' responses
        previous_round = round_one
        for round_num in range(2, num_rounds + 1):
            round_start_percent = base_percent + (round_num - 1) * percent_per_round
            
            report_progress(
                ProgressStage.ROUND_START,
                f"Starting Round {round_num} of {num_rounds}...",
                round_start_percent,
                round_number=round_num,
                total_rounds=num_rounds,
            )
            
            current_round = await self._execute_round_with_progress(
                query=query,
                round_number=round_num,
                previous_round=previous_round,
                injection_prompts=None,  # Only round 1 gets injection
                progress_callback=progress_callback,
                round_base_percent=round_start_percent,
                percent_per_agent=percent_per_agent,
            )
            rounds.append(current_round)
            
            report_progress(
                ProgressStage.ROUND_COMPLETE,
                f"Round {round_num} complete",
                round_start_percent + percent_per_round,
                round_number=round_num,
                agent_count=num_agents,
            )
            
            previous_round = current_round
        
        return rounds
    
    async def _execute_round_with_progress(
        self,
        query: str,
        round_number: int,
        previous_round: Optional[ConferenceRound],
        injection_prompts: Optional[dict[str, str]],
        progress_callback: Optional[Callable[[ProgressUpdate], None]],
        round_base_percent: int,
        percent_per_agent: int,
    ) -> ConferenceRound:
        """
        Execute a single round with per-agent progress updates.
        
        Unlike parallel execution, this runs agents sequentially to enable
        real-time progress updates. For small numbers of agents, the overhead
        is acceptable.
        """
        # Helper to report progress
        def report_progress(stage: ProgressStage, message: str, percent: int, **detail):
            if progress_callback:
                progress_callback(ProgressUpdate(
                    stage=stage,
                    message=message,
                    percent=percent,
                    detail=detail,
                ))
        
        responses = {}
        
        for i, agent in enumerate(self.agents):
            role_display = self._get_role_display(agent.role)
            model_short = agent.model.split("/")[-1]
            
            # Report: Agent thinking
            current_percent = round_base_percent + (i * percent_per_agent)
            report_progress(
                ProgressStage.AGENT_THINKING,
                f"{role_display} is deliberating...",
                current_percent,
                agent_id=agent.agent_id,
                role=agent.role,
                model=model_short,
                round_number=round_number,
            )
            
            # Execute agent
            if round_number == 1:
                # Round 1: Independent response
                injected_query = query
                if injection_prompts and agent.agent_id in injection_prompts:
                    injected_query = injection_prompts[agent.agent_id] + "\n\n" + query
                response = await agent.respond_to_query(injected_query)
            else:
                # Follow-up round: See others' responses
                other_responses = {
                    self._get_role_display(resp.role): resp.content
                    for agent_id, resp in previous_round.agent_responses.items()
                    if agent_id != agent.agent_id
                }
                response = await agent.respond_to_discussion(
                    query=query,
                    previous_responses=other_responses,
                    round_number=round_number,
                )
            
            responses[agent.agent_id] = response
            
            # Report: Agent complete (include response content for live dialogue)
            report_progress(
                ProgressStage.AGENT_COMPLETE,
                f"{role_display} complete ({response.confidence:.0%} confidence)",
                current_percent + percent_per_agent,
                agent_id=agent.agent_id,
                role=agent.role,
                model=model_short,
                confidence=response.confidence,
                changed=response.changed_from_previous,
                round_number=round_number,
                content=response.content,  # Include for live dialogue view
            )
        
        return ConferenceRound(
            round_number=round_number,
            agent_responses=responses,
        )
    
    def _get_role_display(self, role: str) -> str:
        """Get display name for a role."""
        role_displays = {
            "advocate": "Advocate",
            "skeptic": "Skeptic",
            "empiricist": "Empiricist",
            "mechanist": "Mechanist",
            "patient_voice": "Patient Voice",
        }
        return role_displays.get(role, role.title())
    
    def get_convergence_summary(
        self,
        rounds: list[ConferenceRound],
    ) -> dict:
        """
        Analyze how agents' positions evolved across rounds.
        
        Args:
            rounds: All conference rounds
        
        Returns:
            Dict with convergence analysis
        """
        if len(rounds) < 2:
            return {"converged": True, "changes": []}
        
        changes = []
        for round_result in rounds[1:]:  # Skip round 1
            for agent_id, response in round_result.agent_responses.items():
                if response.changed_from_previous:
                    changes.append({
                        "round": round_result.round_number,
                        "agent": agent_id,
                        "role": response.role,
                    })
        
        # Check final round for remaining disagreement
        final_round = rounds[-1]
        final_positions = [
            r.position_summary
            for r in final_round.agent_responses.values()
        ]
        
        return {
            "converged": len(changes) > 0,  # At least one agent changed
            "changes": changes,
            "num_position_changes": len(changes),
        }

