"""
Oxford Debate Topology - Two agents argue opposing positions, third judges.

Structured like a formal debate:
- Round 1: Advocate presents case, Skeptic presents counter-case
- Round 2+: Each responds to the other's arguments
- Judge (Empiricist by default) evaluates the arguments

Best for: Binary decisions, contested topics, when clear pros/cons are needed
"""

from typing import Callable, Optional

from src.conference.agent import Agent
from src.conference.topologies.base import BaseTopology, ProgressStage, ProgressUpdate
from src.models.conference import AgentResponse, ConferenceRound


class OxfordDebateTopology(BaseTopology):
    """
    Oxford Debate: Two agents argue opposing positions, third judges.
    
    Required roles: advocate, skeptic (+ one judge: empiricist, mechanist, or patient_voice)
    
    Round 1: 
      - Advocate presents the case FOR the most promising approach
      - Skeptic presents the case AGAINST or for an alternative
      - Judge observes (optional: asks clarifying questions)
    
    Round 2+:
      - Advocate responds to Skeptic's points
      - Skeptic responds to Advocate's points  
      - Judge evaluates strength of arguments
    
    Final round:
      - Judge provides evaluation of which side argued more effectively
    """
    
    @property
    def name(self) -> str:
        return "Oxford Debate"
    
    @property
    def description(self) -> str:
        return "Two agents argue opposing positions, third judges. Best for binary decisions."
    
    @property
    def minimum_rounds(self) -> int:
        return 2  # At least opening + rebuttal
    
    @property
    def required_roles(self) -> list[str]:
        return ["advocate", "skeptic"]
    
    def _get_debaters(self) -> tuple[Agent, Agent]:
        """Get the two debating agents."""
        advocate = self._agents_by_role.get("advocate")
        skeptic = self._agents_by_role.get("skeptic")
        return advocate, skeptic
    
    def _get_judge(self) -> Optional[Agent]:
        """Get the judge agent (prefers empiricist, then others)."""
        for role in ["empiricist", "mechanist", "patient_voice"]:
            if role in self._agents_by_role:
                return self._agents_by_role[role]
        # Return any agent that's not advocate or skeptic
        for agent in self.agents:
            if agent.role not in ["advocate", "skeptic"]:
                return agent
        return None
    
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
        Execute a round in Oxford Debate format.
        """
        advocate, skeptic = self._get_debaters()
        judge = self._get_judge()
        
        responses = {}
        agent_idx = 0
        
        # Debate-specific framing for each agent
        def get_debate_framing(agent: Agent, is_round_one: bool) -> str:
            if agent.role == "advocate":
                if is_round_one:
                    return (
                        "You are the ADVOCATE in an Oxford-style debate. "
                        "Present the strongest possible case for the most promising approach. "
                        "Your goal is to convince the judge that your recommendation is correct.\n\n"
                    )
                else:
                    return (
                        "REBUTTAL ROUND: The Skeptic has challenged your position. "
                        "Address their concerns directly and reinforce your case.\n\n"
                    )
            elif agent.role == "skeptic":
                if is_round_one:
                    return (
                        "You are the SKEPTIC in an Oxford-style debate. "
                        "Present the strongest case AGAINST the obvious approach or FOR an alternative. "
                        "Challenge assumptions and highlight risks.\n\n"
                    )
                else:
                    return (
                        "REBUTTAL ROUND: The Advocate has presented their case. "
                        "Attack their weakest points and strengthen your alternative.\n\n"
                    )
            else:  # Judge
                if is_round_one:
                    return (
                        "You are the JUDGE in this Oxford-style debate. "
                        "Observe the arguments from both sides. You may ask clarifying questions.\n\n"
                    )
                else:
                    return (
                        "EVALUATION ROUND: Review the arguments from both debaters. "
                        "Assess the strength of evidence and reasoning on each side. "
                        "Which side argues more effectively and why?\n\n"
                    )
        
        # Execute debaters first (in order: Advocate, then Skeptic)
        for agent in [advocate, skeptic]:
            if not agent:
                continue
                
            role_display = self._get_role_display(agent.role)
            current_percent = round_base_percent + (agent_idx * percent_per_agent)
            
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_THINKING,
                f"{role_display} preparing argument...",
                current_percent,
                agent_id=agent.agent_id,
                role=agent.role,
                round_number=round_number,
            )
            
            framing = get_debate_framing(agent, round_number == 1)
            
            if round_number == 1:
                injected_query = framing + query
                if injection_prompts and agent.agent_id in injection_prompts:
                    injected_query = injection_prompts[agent.agent_id] + "\n\n" + injected_query
                response = await agent.respond_to_query(injected_query)
            else:
                # In debate, each debater only sees opponent's response
                previous_round = previous_rounds[-1]
                opponent_role = "skeptic" if agent.role == "advocate" else "advocate"
                opponent_agent = self._agents_by_role.get(opponent_role)
                
                other_responses = {}
                if opponent_agent and opponent_agent.agent_id in previous_round.agent_responses:
                    opponent_resp = previous_round.agent_responses[opponent_agent.agent_id]
                    other_responses[self._get_role_display(opponent_role)] = opponent_resp.content
                
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
            agent_idx += 1
            
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_COMPLETE,
                f"{role_display} argument complete",
                current_percent + percent_per_agent,
                agent_id=agent.agent_id,
                role=agent.role,
                confidence=response.confidence,
                round_number=round_number,
                content=response.content,
            )
        
        # Then execute judge (sees both debaters)
        if judge:
            role_display = self._get_role_display(judge.role) + " (Judge)"
            current_percent = round_base_percent + (agent_idx * percent_per_agent)
            
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_THINKING,
                f"{role_display} evaluating debate...",
                current_percent,
                agent_id=judge.agent_id,
                role=judge.role,
                round_number=round_number,
            )
            
            framing = get_debate_framing(judge, round_number == 1)
            
            if round_number == 1:
                # First round: judge sees both opening statements
                all_responses = {
                    self._get_role_display(r.role): r.content
                    for r in responses.values()
                }
                response = await judge.respond_to_discussion(
                    query=framing + query,
                    previous_responses=all_responses,
                    round_number=round_number,
                )
            else:
                # Later rounds: judge sees all arguments
                previous_round = previous_rounds[-1]
                all_responses = {
                    self._get_role_display(resp.role): resp.content
                    for agent_id, resp in previous_round.agent_responses.items()
                }
                # Add current round responses
                all_responses.update({
                    self._get_role_display(r.role): r.content
                    for r in responses.values()
                })
                
                response = await judge.respond_to_discussion(
                    query=framing + query,
                    previous_responses=all_responses,
                    round_number=round_number,
                )
            
            # Process librarian queries if available
            response = await self._process_librarian_queries(
                agent_id=judge.agent_id,
                response=response,
                round_number=round_number,
            )
            
            responses[judge.agent_id] = response
            
            self._report_progress(
                progress_callback,
                ProgressStage.AGENT_COMPLETE,
                f"{role_display} evaluation complete",
                current_percent + percent_per_agent,
                agent_id=judge.agent_id,
                role=judge.role,
                confidence=response.confidence,
                round_number=round_number,
                content=response.content,
            )
        
        return ConferenceRound(
            round_number=round_number,
            agent_responses=responses,
        )

