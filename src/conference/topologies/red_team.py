"""
Red Team / Blue Team Topology - One builds proposal, other attacks it.

Based on adversarial review:
- Blue Team (Advocate): Builds and defends a proposal
- Red Team (Skeptic): Systematically attacks the proposal
- Other agents can provide evidence or perspective

Best for: Risk assessment, safety evaluation, stress-testing proposals
"""

from typing import Callable, Optional

from src.conference.agent import Agent
from src.conference.topologies.base import BaseTopology, ProgressStage, ProgressUpdate
from src.models.conference import AgentResponse, ConferenceRound


class RedTeamBlueTeamTopology(BaseTopology):
    """
    Red Team / Blue Team: One builds proposal, other attacks it.
    
    Required roles: advocate (Blue Team), skeptic (Red Team)
    
    Round 1: 
      - Blue Team (Advocate) presents complete proposal
      - Red Team (Skeptic) prepares attack strategy
    
    Round 2:
      - Red Team attacks with specific vulnerabilities
      - Blue Team must defend or acknowledge weaknesses
    
    Round 3+:
      - Continued attack/defense
      - Other agents provide supporting analysis
    
    Final output identifies:
      - Vulnerabilities that were successfully defended
      - Vulnerabilities that remain concerning
      - Conditions under which the proposal fails
    """
    
    @property
    def name(self) -> str:
        return "Red Team / Blue Team"
    
    @property
    def description(self) -> str:
        return "Adversarial review: one team builds, other attacks. Best for risk assessment."
    
    @property
    def minimum_rounds(self) -> int:
        return 2  # Proposal + Attack
    
    @property
    def required_roles(self) -> list[str]:
        return ["advocate", "skeptic"]
    
    def _get_team_framing(
        self, 
        agent_role: str, 
        round_number: int,
        is_proposer: bool,
    ) -> str:
        """Get team-specific framing for each round."""
        
        if is_proposer:  # Blue Team (Advocate)
            if round_number == 1:
                return (
                    "🔵 BLUE TEAM BRIEF\n\n"
                    "You are the PROPOSAL TEAM. Your mission:\n"
                    "1. Present the most defensible recommendation\n"
                    "2. Anticipate attacks and build in safeguards\n"
                    "3. Acknowledge limitations preemptively\n\n"
                    "Your proposal will be systematically attacked. Build it strong.\n\n"
                )
            else:
                return (
                    "🔵 BLUE TEAM DEFENSE\n\n"
                    "The Red Team has attacked your proposal. You must:\n"
                    "1. Defend against valid attacks with evidence\n"
                    "2. Acknowledge vulnerabilities you cannot defend\n"
                    "3. Propose mitigations for real weaknesses\n\n"
                    "An honest defense is stronger than an overconfident one.\n\n"
                )
        else:  # Red Team (Skeptic)
            if round_number == 1:
                return (
                    "🔴 RED TEAM BRIEF\n\n"
                    "You are the ATTACK TEAM. Your mission:\n"
                    "1. Identify every possible failure mode\n"
                    "2. Challenge every assumption\n"
                    "3. Find edge cases and contraindications\n\n"
                    "Prepare your attack strategy. List vulnerabilities to probe.\n\n"
                )
            else:
                return (
                    "🔴 RED TEAM ATTACK\n\n"
                    "Execute your attack on the Blue Team's proposal:\n"
                    "1. Present specific vulnerabilities with evidence\n"
                    "2. Challenge the weakest points in their defense\n"
                    "3. Identify real-world scenarios where this fails\n\n"
                    "Be rigorous but fair. The goal is to strengthen, not destroy.\n\n"
                )
    
    def _get_support_framing(self, agent_role: str, round_number: int) -> str:
        """Get framing for supporting agents (not advocate/skeptic)."""
        role_focus = {
            "empiricist": "evidence quality and relevance",
            "mechanist": "biological plausibility of claims",
            "patient_voice": "practical acceptability and adherence",
        }
        focus = role_focus.get(agent_role, "your area of expertise")
        
        return (
            f"📊 TECHNICAL ANALYST ({self._get_role_display(agent_role).upper()})\n\n"
            f"Provide expert analysis focused on {focus}.\n"
            "Evaluate both the Blue Team's proposal and Red Team's attacks.\n"
            "Which side has stronger support for their position?\n\n"
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
        Execute a round with Red Team / Blue Team format.
        """
        responses = {}
        agent_idx = 0
        
        # Get team members
        blue_team = self._agents_by_role.get("advocate")
        red_team = self._agents_by_role.get("skeptic")
        support_agents = [a for a in self.agents if a.role not in ["advocate", "skeptic"]]
        
        # Round structure: Blue first, then Red, then support
        agents_order = []
        if round_number == 1:
            # Round 1: Blue proposes, Red prepares
            if blue_team:
                agents_order.append((blue_team, True))  # Blue first
            if red_team:
                agents_order.append((red_team, False))  # Red prepares
        else:
            # Round 2+: Red attacks, Blue defends
            if red_team:
                agents_order.append((red_team, False))  # Red attacks
            if blue_team:
                agents_order.append((blue_team, True))  # Blue defends
        
        # Add support agents last
        for agent in support_agents:
            agents_order.append((agent, None))  # None = support role
        
        for agent, is_blue_team in agents_order:
            role_display = self._get_role_display(agent.role)
            current_percent = round_base_percent + (agent_idx * percent_per_agent)
            
            # Team-specific display
            if is_blue_team is True:
                team_label = "🔵 Blue Team"
            elif is_blue_team is False:
                team_label = "🔴 Red Team"
            else:
                team_label = "📊 Analyst"
            
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_THINKING,
                f"{team_label} ({role_display}) working...",
                current_percent,
                agent_id=agent.agent_id,
                role=agent.role,
                team="blue" if is_blue_team else ("red" if is_blue_team is False else "support"),
                round_number=round_number,
            )
            
            # Get appropriate framing
            if is_blue_team is not None:
                framing = self._get_team_framing(agent.role, round_number, is_blue_team)
            else:
                framing = self._get_support_framing(agent.role, round_number)
            
            if round_number == 1 and agent_idx == 0:
                # First agent in round 1: Independent response
                framed_query = framing + query
                if injection_prompts and agent.agent_id in injection_prompts:
                    framed_query = injection_prompts[agent.agent_id] + "\n\n" + framed_query
                response = await agent.respond_to_query(framed_query)
            else:
                # See relevant previous responses
                other_responses = {}
                
                # Include responses from current round so far
                for aid, resp in responses.items():
                    other_responses[self._get_role_display(resp.role)] = resp.content
                
                # Include relevant responses from previous rounds
                if previous_rounds:
                    for prev_round in previous_rounds:
                        for aid, resp in prev_round.agent_responses.items():
                            label = f"{self._get_role_display(resp.role)} (R{prev_round.round_number})"
                            other_responses[label] = resp.content
                
                response = await agent.respond_to_discussion(
                    query=framing + query,
                    previous_responses=other_responses,
                    round_number=round_number,
                )
            
            responses[agent.agent_id] = response
            agent_idx += 1
            
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_COMPLETE,
                f"{team_label} ({role_display}) complete",
                current_percent + percent_per_agent,
                agent_id=agent.agent_id,
                role=agent.role,
                confidence=response.confidence,
                round_number=round_number,
            )
        
        return ConferenceRound(
            round_number=round_number,
            agent_responses=responses,
        )

