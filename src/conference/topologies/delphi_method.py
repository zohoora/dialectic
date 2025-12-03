"""
Delphi Method Topology - Anonymous rounds to reduce anchoring bias.

Based on the classical Delphi technique:
- Agents don't know who said what (responses are anonymized)
- This reduces anchoring bias and authority effects
- Each round, agents see a summary of positions without attribution

Best for: Reducing anchoring bias, getting unbiased expert opinions
"""

import random
from typing import Callable, Optional

from src.conference.agent import Agent
from src.conference.topologies.base import BaseTopology, ProgressStage, ProgressUpdate
from src.models.conference import AgentResponse, ConferenceRound


class DelphiMethodTopology(BaseTopology):
    """
    Delphi Method: Anonymous rounds to reduce anchoring bias.
    
    Key features:
    - Responses are presented anonymously (no role labels)
    - Order of responses is randomized
    - Agents cannot anchor on authority
    
    Round 1: Each agent responds independently (baseline)
    Round 2+: Each agent sees anonymized responses from previous round
    """
    
    @property
    def name(self) -> str:
        return "Delphi Method"
    
    @property
    def description(self) -> str:
        return "Anonymous rounds reduce anchoring bias. Agents don't know who said what."
    
    @property
    def minimum_rounds(self) -> int:
        return 2
    
    def _anonymize_responses(self, responses: dict[str, AgentResponse]) -> dict[str, str]:
        """
        Anonymize responses by removing role information.
        
        Returns responses with anonymous labels like "Panelist A", "Panelist B"
        """
        # Shuffle to prevent order-based identification
        response_list = list(responses.values())
        random.shuffle(response_list)
        
        labels = ["A", "B", "C", "D", "E", "F", "G", "H"]
        anonymized = {}
        
        for i, resp in enumerate(response_list):
            label = f"Panelist {labels[i] if i < len(labels) else i + 1}"
            # Strip any obvious role references from content
            content = resp.content
            # Remove explicit role mentions (basic cleanup)
            for role in ["Advocate", "Skeptic", "Empiricist", "Mechanist", "Patient Voice"]:
                content = content.replace(f"As the {role}", "As a panelist")
                content = content.replace(f"as the {role}", "as a panelist")
            anonymized[label] = content
        
        return anonymized
    
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
        Execute a round with Delphi Method (anonymous responses).
        """
        responses = {}
        
        # Delphi-specific framing
        delphi_framing = (
            "DELPHI METHOD: This is an anonymous consultation. "
            "You will see other panelists' views without knowing their roles or identities. "
            "Focus on the substance of arguments, not who made them. "
            "You may revise your position based on the collective wisdom.\n\n"
        )
        
        for i, agent in enumerate(self.agents):
            role_display = self._get_role_display(agent.role)
            current_percent = round_base_percent + (i * percent_per_agent)
            
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_THINKING,
                f"Panelist {i + 1} (anonymous) deliberating...",
                current_percent,
                agent_id=agent.agent_id,
                role="anonymous",  # Don't reveal role in progress
                round_number=round_number,
            )
            
            if round_number == 1:
                # First round: Independent response
                framed_query = delphi_framing + query
                if injection_prompts and agent.agent_id in injection_prompts:
                    framed_query = injection_prompts[agent.agent_id] + "\n\n" + framed_query
                response = await agent.respond_to_query(framed_query)
            else:
                # Later rounds: See ANONYMIZED previous responses
                previous_round = previous_rounds[-1]
                anonymized = self._anonymize_responses(previous_round.agent_responses)
                
                response = await agent.respond_to_discussion(
                    query=delphi_framing + query,
                    previous_responses=anonymized,
                    round_number=round_number,
                )
            
            # Process librarian queries if available
            response = await self._process_librarian_queries(
                agent_id=agent.agent_id,
                response=response,
                round_number=round_number,
            )
            
            responses[agent.agent_id] = response
            
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_COMPLETE,
                f"Panelist {i + 1} complete",
                current_percent + percent_per_agent,
                agent_id=agent.agent_id,
                role="anonymous",
                confidence=response.confidence,
                round_number=round_number,
                content=response.content,
            )
        
        return ConferenceRound(
            round_number=round_number,
            agent_responses=responses,
        )

