"""
Arbitrator engine for conference synthesis.

The Arbitrator reviews all rounds of deliberation and produces
a final synthesis with consensus points and preserved dissent.
"""

import re
from typing import Optional, Protocol

from src.models.conference import (
    AgentRole,
    ArbitratorConfig,
    ConferenceRound,
    ConferenceSynthesis,
    DissentRecord,
    LLMResponse,
)
from src.utils.prompt_loader import (
    build_agent_system_prompt,
    build_arbitrator_prompt,
)


class LLMClientProtocol(Protocol):
    """Protocol for LLM client."""
    
    async def complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        ...


class ArbitratorEngine:
    """
    Synthesizes conference deliberation into final consensus.
    
    The Arbitrator:
    - Reviews all rounds of discussion
    - Identifies consensus points
    - Preserves meaningful dissent
    - Produces actionable recommendations
    """
    
    def __init__(
        self,
        config: ArbitratorConfig,
        llm_client: LLMClientProtocol,
    ):
        """
        Initialize the arbitrator.
        
        Args:
            config: Arbitrator configuration
            llm_client: LLM client for making API calls
        """
        self.config = config
        self.llm_client = llm_client
        self.system_prompt = build_agent_system_prompt("arbitrator")
    
    async def synthesize(
        self,
        query: str,
        rounds: list[ConferenceRound],
    ) -> tuple[ConferenceSynthesis, DissentRecord, LLMResponse]:
        """
        Synthesize all rounds into a final consensus.
        
        Args:
            query: The original clinical question
            rounds: All deliberation rounds
        
        Returns:
            Tuple of (ConferenceSynthesis, DissentRecord, raw LLMResponse)
        """
        # Build the context from all rounds
        all_rounds_dict = []
        for round_result in rounds:
            round_dict = {}
            for agent_id, response in round_result.agent_responses.items():
                role_display = self._get_role_display(response.role)
                round_dict[role_display] = response.content
            all_rounds_dict.append(round_dict)
        
        user_prompt = build_arbitrator_prompt(query, all_rounds_dict)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        llm_response = await self.llm_client.complete(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
        )
        
        # Parse the response into structured output
        synthesis = self._parse_synthesis(llm_response.content)
        dissent = self._parse_dissent(llm_response.content, rounds)
        
        return synthesis, dissent, llm_response
    
    def _parse_synthesis(self, content: str) -> ConferenceSynthesis:
        """
        Parse arbitrator response into ConferenceSynthesis.
        
        Args:
            content: Raw arbitrator response
        
        Returns:
            Structured ConferenceSynthesis
        """
        # Extract synthesis recommendation section
        final_consensus = self._extract_section(
            content,
            ["Synthesis Recommendation", "Final Recommendation", "Recommendation"],
            default=content[:500] if len(content) > 500 else content,
        )
        
        # Extract key points / consensus points
        consensus_section = self._extract_section(
            content,
            ["Consensus Points", "Key Points", "Points of Agreement"],
            default="",
        )
        key_points = self._parse_bullet_points(consensus_section)
        
        # Extract caveats
        caveats_section = self._extract_section(
            content,
            ["Key Caveats", "Caveats", "Limitations"],
            default="",
        )
        caveats = self._parse_bullet_points(caveats_section)
        
        # Extract confidence
        confidence = self._extract_confidence(content)
        
        # Extract evidence summary
        evidence_summary = self._extract_section(
            content,
            ["Evidence Summary", "Supporting Evidence"],
            default="",
        )
        
        return ConferenceSynthesis(
            final_consensus=final_consensus.strip(),
            confidence=confidence,
            key_points=key_points,
            evidence_summary=evidence_summary,
            caveats=caveats,
        )
    
    def _parse_dissent(
        self,
        content: str,
        rounds: list[ConferenceRound],
    ) -> DissentRecord:
        """
        Parse dissent information from arbitrator response.
        
        Args:
            content: Raw arbitrator response
            rounds: Original rounds (for cross-reference)
        
        Returns:
            DissentRecord
        """
        # Check if dissent section exists
        dissent_section = self._extract_section(
            content,
            ["Preserved Dissent", "Dissent", "Disagreement"],
            default="",
        )
        
        if not dissent_section or "none" in dissent_section.lower()[:50]:
            return DissentRecord(preserved=False)
        
        # Try to extract structured dissent
        dissenting_agent = self._extract_field(
            dissent_section,
            ["Dissenting Agent", "Dissenting Role"],
        )
        
        dissent_summary = self._extract_field(
            dissent_section,
            ["Dissent Summary", "Summary"],
        )
        
        dissent_reasoning = self._extract_field(
            dissent_section,
            ["Dissent Reasoning", "Reasoning", "Reason"],
        )
        
        dissent_strength = self._extract_field(
            dissent_section,
            ["Dissent Strength", "Strength"],
        )
        
        # Determine dissenting role
        dissenting_role = self._identify_dissenting_role(dissenting_agent)
        
        return DissentRecord(
            preserved=True,
            dissenting_agent=dissenting_agent or "Unknown",
            dissenting_role=dissenting_role,
            summary=dissent_summary or dissent_section[:200],
            reasoning=dissent_reasoning or "",
            strength=dissent_strength or "Moderate",
        )
    
    def _extract_section(
        self,
        content: str,
        headers: list[str],
        default: str = "",
    ) -> str:
        """
        Extract a section of content by header.
        
        Args:
            content: Full content to search
            headers: Possible section headers to look for
            default: Default value if not found
        
        Returns:
            Section content or default
        """
        for header in headers:
            # Try markdown header formats
            patterns = [
                rf"###\s*{header}\s*\n(.*?)(?=\n###|\n##|\Z)",
                rf"##\s*{header}\s*\n(.*?)(?=\n##|\n#|\Z)",
                rf"\*\*{header}\*\*[:\s]*\n(.*?)(?=\n\*\*|\Z)",
                rf"{header}[:\s]*\n(.*?)(?=\n\n|\Z)",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        
        return default
    
    def _extract_field(self, content: str, field_names: list[str]) -> Optional[str]:
        """Extract a single field value."""
        for field in field_names:
            patterns = [
                rf"\*\*{field}\*\*[:\s]*(.+?)(?:\n|$)",
                rf"{field}[:\s]*(.+?)(?:\n|$)",
                rf"-\s*{field}[:\s]*(.+?)(?:\n|$)",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        
        return None
    
    def _parse_bullet_points(self, content: str) -> list[str]:
        """Parse bullet points from content."""
        if not content:
            return []
        
        points = []
        # Match various bullet formats
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*", "•", "·")):
                point = line.lstrip("-*•· ").strip()
                if point:
                    points.append(point)
            elif re.match(r"^\d+\.", line):
                point = re.sub(r"^\d+\.\s*", "", line).strip()
                if point:
                    points.append(point)
        
        return points
    
    def _extract_confidence(self, content: str) -> float:
        """Extract confidence level from content."""
        content_lower = content.lower()
        
        # Look for explicit confidence
        if "confidence level" in content_lower or "confidence:" in content_lower:
            if "high" in content_lower:
                return 0.85
            elif "medium" in content_lower or "moderate" in content_lower:
                return 0.6
            elif "low" in content_lower:
                return 0.35
        
        return 0.6  # Default to moderate
    
    def _identify_dissenting_role(self, agent_str: Optional[str]) -> Optional[AgentRole]:
        """Identify the role from agent string."""
        if not agent_str:
            return None
        
        agent_lower = agent_str.lower()
        
        role_mapping = {
            "advocate": AgentRole.ADVOCATE,
            "skeptic": AgentRole.SKEPTIC,
            "empiricist": AgentRole.EMPIRICIST,
            "mechanist": AgentRole.MECHANIST,
            "patient": AgentRole.PATIENT_VOICE,
        }
        
        for key, role in role_mapping.items():
            if key in agent_lower:
                return role
        
        return None
    
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

