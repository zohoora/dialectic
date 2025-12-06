"""
Perturbation Generator for creating query-specific fragility tests.

Uses an LLM to generate perturbations tailored to the specific clinical
question and recommendation, rather than using a fixed list.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from src.utils.protocols import LLMClientProtocol


logger = logging.getLogger(__name__)


class PerturbationGenerator:
    """
    Generates query-specific perturbations using an LLM.
    
    Instead of using a fixed list of medical perturbations, this generator
    analyzes the specific clinical question and consensus to create
    perturbations that are most relevant to the case at hand.
    """
    
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_path: Optional[Path] = None,
    ):
        """
        Initialize the perturbation generator.
        
        Args:
            llm_client: LLM client for API calls
            prompt_path: Path to prompt template (uses default if not provided)
        """
        self.llm_client = llm_client
        
        # Load prompt template
        if prompt_path is None:
            prompt_path = (
                Path(__file__).parent.parent.parent
                / "prompts"
                / "fragility"
                / "generate_perturbations.md"
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
        return """Generate {num_perturbations} clinical perturbations for testing this recommendation.

Question: {query}
Consensus: {consensus}

Respond with JSON only:
{{"perturbations": ["perturbation 1", "perturbation 2", ...]}}"""
    
    async def generate(
        self,
        query: str,
        consensus: str,
        num_perturbations: int = 5,
        model: str = "anthropic/claude-3.5-sonnet",
    ) -> list[str]:
        """
        Generate perturbations tailored to the specific query and consensus.
        
        Args:
            query: Original clinical question
            consensus: The consensus recommendation to test
            num_perturbations: Number of perturbations to generate
            model: LLM model to use for generation
            
        Returns:
            List of generated perturbation strings
        """
        # Build prompt
        prompt = self.prompt_template.format(
            query=query,
            consensus=consensus,
            num_perturbations=num_perturbations,
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await self.llm_client.complete(
                model=model,
                messages=messages,
                temperature=0.7,  # Higher temperature for creative perturbations
            )
            
            return self._parse_response(response.content, num_perturbations)
            
        except Exception as e:
            logger.error(f"Error generating perturbations: {e}")
            # Return fallback generic perturbations
            return self._fallback_perturbations(num_perturbations)
    
    def _parse_response(self, content: str, num_perturbations: int) -> list[str]:
        """
        Parse LLM response into list of perturbations.
        
        Args:
            content: Raw LLM response content
            num_perturbations: Expected number of perturbations
            
        Returns:
            List of perturbation strings
        """
        try:
            # Strip and clean content
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
            perturbations = data.get("perturbations", [])
            
            # Validate we got a list of strings
            if isinstance(perturbations, list):
                return [str(p) for p in perturbations if p]
            
            logger.warning("Perturbations field was not a list")
            return self._fallback_perturbations(num_perturbations)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            
            # Try to extract perturbations from text
            return self._extract_from_text(content, num_perturbations)
    
    def _extract_from_text(self, content: str, num_perturbations: int) -> list[str]:
        """
        Extract perturbations from unstructured text.
        
        Args:
            content: Raw text content
            num_perturbations: Maximum number to extract
            
        Returns:
            List of extracted perturbations
        """
        perturbations = []
        
        # Look for numbered items or bullet points
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            # Match numbered items: "1. What if...", "1) What if..."
            if line and (line[0].isdigit() or line.startswith(("-", "*", "•"))):
                # Clean up the line
                clean = line.lstrip("0123456789.-*•) ").strip()
                if clean and len(clean) > 10:  # Minimum length check
                    perturbations.append(clean)
        
        if perturbations:
            return perturbations[:num_perturbations]
        
        return self._fallback_perturbations(num_perturbations)
    
    def _fallback_perturbations(self, num_perturbations: int) -> list[str]:
        """
        Return generic fallback perturbations.
        
        Args:
            num_perturbations: Number to return
            
        Returns:
            List of generic perturbations
        """
        generic = [
            "What if the patient has renal impairment (eGFR < 30)?",
            "What if the patient is elderly (> 80 years)?",
            "What if the patient is pregnant or breastfeeding?",
            "What if the patient has hepatic dysfunction?",
            "What if the patient has multiple drug allergies?",
            "What if the patient has cardiovascular disease?",
            "What if the patient has limited healthcare access?",
            "What if the patient previously failed first-line treatment?",
        ]
        return generic[:num_perturbations]

