"""
Socratic Spiral Topology - First round is questions only.

Based on Socratic dialogue:
- Round 1: Agents only ask questions, surfacing assumptions
- Round 2+: Agents answer the questions and build on each other's insights
- Emphasis on uncovering hidden assumptions before proposing solutions

Best for: Diagnostic dilemmas, complex cases where assumptions need examination
"""

from typing import Callable, Optional

from src.conference.agent import Agent
from src.conference.topologies.base import BaseTopology
from src.models.progress import ProgressStage, ProgressUpdate
from src.models.conference import AgentResponse, ConferenceRound


class SocraticSpiralTopology(BaseTopology):
    """
    Socratic Spiral: First round is questions only, surfacing assumptions.
    
    Round 1: Each agent asks clarifying questions about the case
            - What assumptions are we making?
            - What information is missing?
            - What could we be wrong about?
    
    Round 2: Agents answer the questions raised
    
    Round 3+: Normal deliberation building on the clarified foundation
    """
    
    @property
    def name(self) -> str:
        return "Socratic Spiral"
    
    @property
    def description(self) -> str:
        return "First round is questions only, surfacing assumptions. Best for diagnostic dilemmas."
    
    @property
    def minimum_rounds(self) -> int:
        return 3  # Question round + Answer round + Synthesis
    
    def _get_round_framing(self, round_number: int, agent_role: str) -> str:
        """Get the appropriate framing for each round."""
        if round_number == 1:
            # Question round
            return (
                "SOCRATIC INQUIRY - ROUND 1 (Questions Only)\n\n"
                "In this round, you must ONLY ask questions. Do NOT propose solutions yet.\n\n"
                "Your task is to surface:\n"
                "1. Hidden assumptions in the case presentation\n"
                "2. Critical information that may be missing\n"
                "3. Alternative interpretations we should consider\n"
                "4. Potential cognitive biases at play\n\n"
                "Ask 3-5 probing questions that would help clarify the situation.\n"
                "Format: List your questions clearly, numbered.\n\n"
            )
        elif round_number == 2:
            # Answer round
            return (
                "SOCRATIC INQUIRY - ROUND 2 (Answering Questions)\n\n"
                "Review the questions raised by all panelists in Round 1.\n"
                "For each important question:\n"
                "1. Provide your best answer or analysis\n"
                "2. If the question cannot be answered, explain why and what that implies\n"
                "3. Note any assumptions that were challenged\n\n"
                "Based on this deeper analysis, what is your revised understanding?\n\n"
            )
        else:
            # Synthesis rounds
            return (
                f"SOCRATIC INQUIRY - ROUND {round_number} (Building on Insights)\n\n"
                "Now that we've examined our assumptions and answered key questions, "
                "provide your recommendation while acknowledging:\n"
                "- Which assumptions remain uncertain\n"
                "- What information gaps affect confidence\n"
                "- How cognitive biases might influence this case\n\n"
            )
    
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
        Execute a round with Socratic Spiral format.
        """
        responses = {}
        
        for i, agent in enumerate(self.agents):
            role_display = self._get_role_display(agent.role)
            current_percent = round_base_percent + (i * percent_per_agent)
            
            # Different messaging for question vs answer rounds
            if round_number == 1:
                action = "formulating questions"
            elif round_number == 2:
                action = "analyzing questions"
            else:
                action = "synthesizing insights"
            
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_THINKING,
                f"{role_display} {action}...",
                current_percent,
                agent_id=agent.agent_id,
                role=agent.role,
                round_number=round_number,
            )
            
            framing = self._get_round_framing(round_number, agent.role)
            
            if round_number == 1:
                # Question round: Independent responses
                framed_query = framing + query
                if injection_prompts and agent.agent_id in injection_prompts:
                    framed_query = injection_prompts[agent.agent_id] + "\n\n" + framed_query
                response = await agent.respond_to_query(framed_query)
            else:
                # Answer and synthesis rounds: See previous responses
                previous_round = previous_rounds[-1]
                
                # Compile all previous responses
                other_responses = {}
                for r in previous_rounds:
                    for agent_id, resp in r.agent_responses.items():
                        if agent_id != agent.agent_id:
                            label = f"{self._get_role_display(resp.role)} (Round {r.round_number})"
                            other_responses[label] = resp.content
                
                response = await agent.respond_to_discussion(
                    query=framing + query,
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
            
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_COMPLETE,
                f"{role_display} complete",
                current_percent + percent_per_agent,
                agent_id=agent.agent_id,
                role=agent.role,
                confidence=response.confidence,
                round_number=round_number,
                content=response.content,
            )
        
        return ConferenceRound(
            round_number=round_number,
            agent_responses=responses,
        )

