"""
Agent class for conference participants.

Each agent represents an AI with an assigned epistemic role (Advocate, Skeptic, etc.)
that participates in the conference deliberation.
"""

import re
from typing import Optional, Protocol

from src.models.conference import AgentConfig, AgentResponse, AgentRole, LLMResponse
from src.utils.prompt_loader import (
    build_agent_system_prompt,
    build_round_one_user_prompt,
    build_followup_round_prompt,
)


class LLMClientProtocol(Protocol):
    """Protocol for LLM client to allow dependency injection."""
    
    async def complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        ...


class Agent:
    """
    A conference participant with an assigned role.
    
    Agents use their role-specific prompts to respond to queries
    and critique other agents' positions.
    """
    
    def __init__(self, config: AgentConfig, llm_client: LLMClientProtocol):
        """
        Initialize an agent.
        
        Args:
            config: Agent configuration (role, model, temperature)
            llm_client: LLM client for making API calls
        """
        self.config = config
        self.llm_client = llm_client
        self.system_prompt = build_agent_system_prompt(config.role)
    
    @property
    def agent_id(self) -> str:
        return self.config.agent_id
    
    @property
    def role(self) -> AgentRole:
        return AgentRole(self.config.role)
    
    @property
    def model(self) -> str:
        return self.config.model
    
    async def respond_to_query(self, query: str) -> AgentResponse:
        """
        Generate an initial response to a clinical query (Round 1).
        
        Args:
            query: The clinical question to analyze
        
        Returns:
            AgentResponse with the agent's analysis
        """
        user_prompt = build_round_one_user_prompt(query)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        llm_response = await self.llm_client.complete(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
        )
        
        return self._parse_response(llm_response, changed=False)
    
    async def respond_to_discussion(
        self,
        query: str,
        previous_responses: dict[str, str],
        round_number: int,
    ) -> AgentResponse:
        """
        Generate a response after seeing other agents' positions (Round 2+).
        
        Args:
            query: The original clinical question
            previous_responses: Dict mapping role names to their previous responses
            round_number: The current round number
        
        Returns:
            AgentResponse with the agent's updated analysis
        """
        user_prompt = build_followup_round_prompt(
            query=query,
            previous_responses=previous_responses,
            round_number=round_number,
        )
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        llm_response = await self.llm_client.complete(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
        )
        
        # Check if position changed
        changed = self._detect_position_change(llm_response.content)
        
        return self._parse_response(llm_response, changed=changed)
    
    def _parse_response(self, llm_response: LLMResponse, changed: bool) -> AgentResponse:
        """
        Parse an LLM response into an AgentResponse.
        
        Args:
            llm_response: Raw response from the LLM
            changed: Whether the agent changed their position
        
        Returns:
            Structured AgentResponse
        """
        content = llm_response.content
        
        # Extract position summary if present
        position_summary = self._extract_position_summary(content)
        
        # Extract confidence if present
        confidence = self._extract_confidence(content)
        
        return AgentResponse(
            agent_id=self.config.agent_id,
            role=self.role,
            model=self.config.model,
            content=content,
            position_summary=position_summary,
            confidence=confidence,
            changed_from_previous=changed,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
        )
    
    def _extract_position_summary(self, content: str) -> str:
        """
        Extract the position summary from response content.
        
        Looks for a line starting with "Position Summary:" or similar.
        """
        # Try to find explicit position summary
        patterns = [
            r"\*\*Position Summary\*\*:\s*(.+?)(?:\n|$)",
            r"Position Summary:\s*(.+?)(?:\n|$)",
            r"\*\*Summary\*\*:\s*(.+?)(?:\n|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: use first sentence of content
        first_line = content.split("\n")[0]
        if len(first_line) > 200:
            return first_line[:200] + "..."
        return first_line
    
    def _extract_confidence(self, content: str) -> float:
        """
        Extract confidence level from response content.
        
        Maps High/Medium/Low to numeric values.
        """
        content_lower = content.lower()
        
        # Look for explicit confidence statements
        if "confidence level" in content_lower or "confidence:" in content_lower:
            if "high" in content_lower:
                return 0.85
            elif "medium" in content_lower or "moderate" in content_lower:
                return 0.6
            elif "low" in content_lower:
                return 0.35
        
        # Default to moderate confidence
        return 0.5
    
    def _detect_position_change(self, content: str) -> bool:
        """
        Detect if the agent indicates they changed their position.
        """
        indicators = [
            "position changed",
            "i have changed",
            "i've changed",
            "i now agree",
            "i've reconsidered",
            "i have reconsidered",
            "upon reflection",
            "having considered",
            "i concede",
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in indicators)

