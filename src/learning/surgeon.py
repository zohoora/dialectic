"""
Surgeon - Extract generalizable heuristics from approved conferences.

The Surgeon performs "lossless compression of logic" - distilling
a conference transcript into a structured, retrievable artifact
for the Experience Library.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Optional, Protocol

from src.models.conference import ConferenceResult, LLMResponse
from src.models.experience import (
    ContextVector,
    ReasoningArtifact,
    SurgeonInput,
    SurgeonOutput,
)
from src.models.fragility import FragilityOutcome


logger = logging.getLogger(__name__)


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


class Surgeon:
    """
    Extracts generalizable heuristics from conference results.
    
    Uses an LLM to analyze the conference transcript and extract
    a structured ReasoningArtifact that can be stored in the
    Experience Library.
    """
    
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        model: str = "anthropic/claude-3.5-sonnet",
        prompt_path: Optional[Path] = None,
    ):
        """
        Initialize the Surgeon.
        
        Args:
            llm_client: LLM client for API calls
            model: Model to use for extraction
            prompt_path: Path to prompt template
        """
        self.llm_client = llm_client
        self.model = model
        
        # Load prompt template
        if prompt_path is None:
            prompt_path = (
                Path(__file__).parent.parent.parent 
                / "prompts" / "learning" / "surgeon.md"
            )
        
        self.prompt_template = self._load_prompt(prompt_path)
    
    def _load_prompt(self, path: Path) -> str:
        """Load prompt template from file."""
        try:
            return path.read_text()
        except FileNotFoundError:
            logger.warning(f"Prompt template not found at {path}, using default")
            return self._default_prompt()
    
    def _default_prompt(self) -> str:
        """Return default prompt if file not found."""
        return """Extract a generalizable heuristic from this conference.

Query: {query}
Consensus: {consensus}
Summary: {transcript}
Evidence: {verified_pmids}
Fragility: {fragility_factors}

Respond with JSON containing: extraction_successful, winning_heuristic, 
context (domain, condition, treatment_type, keywords), qualifying_conditions,
disqualifying_conditions, evidence_summary, confidence."""
    
    async def extract(self, result: ConferenceResult) -> SurgeonOutput:
        """
        Extract a heuristic from a conference result.
        
        Args:
            result: Complete conference result
            
        Returns:
            SurgeonOutput with extracted artifact or failure reason
        """
        # Build input
        surgeon_input = self._build_input(result)
        
        # Run extraction
        return await self.extract_from_input(surgeon_input)
    
    async def extract_from_input(self, surgeon_input: SurgeonInput) -> SurgeonOutput:
        """
        Extract a heuristic from prepared SurgeonInput.
        
        Args:
            surgeon_input: Prepared surgeon input
            
        Returns:
            SurgeonOutput with extracted artifact or failure reason
        """
        # Build prompt
        prompt = self.prompt_template.format(
            query=surgeon_input.query,
            consensus=surgeon_input.final_consensus,
            transcript=surgeon_input.conference_transcript[:3000],  # Limit length
            verified_pmids=", ".join(surgeon_input.verified_citations) or "None",
            fragility_factors=", ".join(surgeon_input.fragility_factors) or "None",
        )
        
        # Call LLM
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await self.llm_client.complete(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for consistent extraction
            )
            
            # Parse response
            return self._parse_response(surgeon_input, response.content)
            
        except Exception as e:
            logger.error(f"Error extracting heuristic: {e}")
            return SurgeonOutput(
                extraction_successful=False,
                failure_reason=f"LLM error: {str(e)[:50]}",
            )
    
    def _build_input(self, result: ConferenceResult) -> SurgeonInput:
        """Build SurgeonInput from ConferenceResult."""
        # Build transcript from rounds
        transcript_parts = []
        for round_result in result.rounds:
            transcript_parts.append(f"--- Round {round_result.round_number} ---")
            for agent_id, response in round_result.agent_responses.items():
                transcript_parts.append(f"[{response.role.upper()}]:")
                transcript_parts.append(response.content[:500])  # Truncate
                transcript_parts.append("")
        
        transcript = "\n".join(transcript_parts)
        
        # Get verified citations
        verified_citations = []
        if result.grounding_report:
            verified_citations = [
                c.pmid for c in result.grounding_report.citations_verified
            ]
        
        # Get failed citations
        failed_citations = []
        if result.grounding_report:
            failed_citations = [
                c.original_text for c in result.grounding_report.citations_failed
            ]
        
        # Get fragility factors
        fragility_factors = []
        if result.fragility_report:
            for r in result.fragility_report.results:
                if r.outcome in (FragilityOutcome.MODIFIES, FragilityOutcome.COLLAPSES):
                    fragility_factors.append(r.perturbation)
        
        return SurgeonInput(
            conference_id=result.conference_id,
            conference_transcript=transcript,
            final_consensus=result.synthesis.final_consensus,
            query=result.query,
            verified_citations=verified_citations,
            failed_citations=failed_citations,
            fragility_factors=fragility_factors,
        )
    
    def _parse_response(
        self,
        surgeon_input: SurgeonInput,
        content: str,
    ) -> SurgeonOutput:
        """
        Parse LLM response into SurgeonOutput.
        
        Args:
            surgeon_input: Original input
            content: Raw LLM response
            
        Returns:
            Parsed SurgeonOutput
        """
        try:
            # Clean up response
            content = content.strip()
            
            # Handle markdown code blocks
            if content.startswith("```"):
                lines = content.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```") and not in_json:
                        in_json = True
                        continue
                    elif line.startswith("```") and in_json:
                        break
                    elif in_json:
                        json_lines.append(line)
                content = "\n".join(json_lines)
            
            # Parse JSON
            data = json.loads(content)
            
            # Check if extraction failed
            if not data.get("extraction_successful", False):
                return SurgeonOutput(
                    extraction_successful=False,
                    failure_reason=data.get("failure_reason", "Extraction failed"),
                )
            
            # Build context vector
            context_data = data.get("context", {})
            context_vector = ContextVector(
                domain=context_data.get("domain", "general"),
                condition=context_data.get("condition", "unspecified"),
                treatment_type=context_data.get("treatment_type"),
                patient_factors=context_data.get("patient_factors", []),
                keywords=context_data.get("keywords", []),
            )
            
            # Generate heuristic ID
            heuristic_id = f"heur_{uuid.uuid4().hex[:12]}"
            
            # Build artifact
            artifact = ReasoningArtifact(
                heuristic_id=heuristic_id,
                source_conference_id=surgeon_input.conference_id,
                winning_heuristic=data.get("winning_heuristic", ""),
                contra_heuristic=data.get("contra_heuristic"),
                context_vector=context_vector,
                qualifying_conditions=data.get("qualifying_conditions", []),
                disqualifying_conditions=data.get("disqualifying_conditions", []),
                fragility_factors=data.get("fragility_factors", []),
                evidence_pmids=data.get("evidence_pmids", []),
                evidence_summary=data.get("evidence_summary"),
                confidence=data.get("confidence", 0.5),
            )
            
            return SurgeonOutput(
                extraction_successful=True,
                artifact=artifact,
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return SurgeonOutput(
                extraction_successful=False,
                failure_reason=f"Failed to parse LLM response: {str(e)[:30]}",
            )
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return SurgeonOutput(
                extraction_successful=False,
                failure_reason=f"Parse error: {str(e)[:50]}",
            )

