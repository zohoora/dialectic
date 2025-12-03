"""
Free Discussion Topology - All agents see all responses, respond freely.

This is the default and most flexible topology where every agent can see
and respond to every other agent's contributions.

Best for: Exploratory questions, brainstorming, complex multi-factor decisions
"""

from typing import Callable, Optional

from src.conference.agent import Agent
from src.conference.topologies.base import BaseTopology, ProgressStage, ProgressUpdate
from src.models.conference import AgentResponse, ConferenceRound


class FreeDiscussionTopology(BaseTopology):
    """
    Free Discussion: All agents see all responses and respond freely.
    
    Round 1: Each agent responds independently to the query
    Round 2+: Each agent sees all others' responses and can critique/refine
    """
    
    @property
    def name(self) -> str:
        return "Free Discussion"
    
    @property
    def description(self) -> str:
        return "All agents see all responses, respond freely. Best for exploratory questions."
    
    async def execute_round(
        self,
        query: str,
        round_number: int,
        previous_rounds: list[ConferenceRound],
        injection_prompts: Optional[dict[str, str]] = None,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
        round_base_percent: int = 0,
        percent_per_agent: int = 10,
    ) -> ConferenceRound:
        """
        Execute a round with free discussion format.
        
        All agents see all other agents' previous responses.
        """
        responses = {}
        
        for i, agent in enumerate(self.agents):
            role_display = self._get_role_display(agent.role)
            model_short = agent.model.split("/")[-1]
            current_percent = round_base_percent + (i * percent_per_agent)
            
            # Report: Agent thinking
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_THINKING,
                f"{role_display} is deliberating...",
                current_percent,
                agent_id=agent.agent_id,
                role=agent.role,
                model=model_short,
                round_number=round_number,
            )
            
            if round_number == 1:
                # Round 1: Independent response
                injected_query = query
                if injection_prompts and agent.agent_id in injection_prompts:
                    injected_query = injection_prompts[agent.agent_id] + "\n\n" + query
                response = await agent.respond_to_query(injected_query)
            else:
                # Follow-up: See ALL other agents' responses
                previous_round = previous_rounds[-1]
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
            
            # Process librarian queries if available
            response = await self._process_librarian_queries(
                agent_id=agent.agent_id,
                response=response,
                round_number=round_number,
            )
            
            responses[agent.agent_id] = response
            
            # Report: Agent complete (include content for live dialogue)
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_COMPLETE,
                f"{role_display} complete ({response.confidence:.0%} confidence)",
                current_percent + percent_per_agent,
                agent_id=agent.agent_id,
                role=agent.role,
                confidence=response.confidence,
                changed=response.changed_from_previous,
                round_number=round_number,
                content=response.content,
            )
        
        return ConferenceRound(
            round_number=round_number,
            agent_responses=responses,
        )

