"""
Fragility Tester for stress-testing consensus recommendations.

Tests recommendations against various perturbations (e.g., renal impairment,
pregnancy, elderly patients) to identify conditions where recommendations
may need modification or don't apply.

Supports both:
- Static perturbations: A fixed list of perturbations
- Dynamic perturbations: LLM-generated query-specific perturbations
"""

import json
import logging
import random
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING

from src.models.fragility import (
    DEFAULT_MEDICAL_PERTURBATIONS,
    FragilityOutcome,
    FragilityReport,
    FragilityResult,
)
from src.models.progress import ProgressStage, ProgressUpdate
from src.utils.protocols import LLMClientProtocol

if TYPE_CHECKING:
    from src.fragility.perturbation_generator import PerturbationGenerator


logger = logging.getLogger(__name__)


class FragilityTester:
    """
    Tests consensus recommendations against perturbations.
    
    Identifies conditions under which a recommendation:
    - SURVIVES: Still holds as stated
    - MODIFIES: Needs adjustment but core approach valid
    - COLLAPSES: No longer valid or safe
    
    Supports both static (fixed list) and dynamic (LLM-generated) perturbations.
    When a PerturbationGenerator is provided, it will generate query-specific
    perturbations tailored to the clinical question and consensus.
    """
    
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        perturbations: Optional[list[str]] = None,
        prompt_path: Optional[Path] = None,
        perturbation_generator: Optional["PerturbationGenerator"] = None,
    ):
        """
        Initialize the fragility tester.
        
        Args:
            llm_client: LLM client for API calls
            perturbations: Custom perturbations (uses defaults if not provided)
            prompt_path: Path to prompt template (uses default if not provided)
            perturbation_generator: Optional generator for dynamic perturbations
        """
        self.llm_client = llm_client
        self.perturbations = perturbations or DEFAULT_MEDICAL_PERTURBATIONS
        self.perturbation_generator = perturbation_generator
        
        # Load prompt template
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent.parent / "prompts" / "fragility" / "fragility_test.md"
        
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
        return """You are testing if a medical recommendation survives a perturbation.

Original Question: {query}
Consensus: {consensus}
Perturbation: {perturbation}

Respond with JSON only:
{{{{"outcome": "SURVIVES" | "MODIFIES" | "COLLAPSES", "explanation": "...", "modified_recommendation": null or "..."}}}}"""
    
    async def test_consensus(
        self,
        query: str,
        consensus: str,
        model: str,
        num_tests: int = 3,
        specific_perturbations: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
        base_percent: int = 0,
        percent_allocation: int = 10,
        fragility_model: Optional[str] = None,
    ) -> FragilityReport:
        """
        Test a consensus recommendation against perturbations.
        
        Args:
            query: Original clinical question
            consensus: The consensus recommendation to test
            model: LLM model to use for testing the consensus
            num_tests: Number of perturbations to test (default: 3)
            specific_perturbations: Specific perturbations to test (random if not provided)
            progress_callback: Optional callback for progress updates
            base_percent: Starting percent for progress tracking
            percent_allocation: Total percent to allocate across tests
            fragility_model: Model to use for generating perturbations (if dynamic)
            
        Returns:
            FragilityReport with test results
        """
        # Helper to report progress
        def report_progress(message: str, percent: int, **detail):
            if progress_callback:
                progress_callback(ProgressUpdate(
                    stage=ProgressStage.FRAGILITY_TEST,
                    message=message,
                    percent=percent,
                    detail=detail,
                ))
        
        # Select perturbations
        if specific_perturbations:
            selected = specific_perturbations[:num_tests]
        elif self.perturbation_generator is not None:
            # Use dynamic perturbation generation
            report_progress(
                "Generating query-specific perturbations...",
                base_percent,
                phase="generating",
            )
            generator_model = fragility_model or model
            selected = await self.perturbation_generator.generate(
                query=query,
                consensus=consensus,
                num_perturbations=num_tests,
                model=generator_model,
            )
            logger.info(f"Generated {len(selected)} perturbations for fragility testing")
        else:
            # Use static perturbations
            selected = random.sample(
                self.perturbations,
                min(num_tests, len(self.perturbations))
            )
        
        results = []
        percent_per_test = percent_allocation // max(len(selected), 1)
        
        for i, perturbation in enumerate(selected):
            current_percent = base_percent + (i * percent_per_test)
            
            # Report: Testing perturbation
            report_progress(
                f"Testing: {perturbation[:50]}...",
                current_percent,
                test_number=i + 1,
                total_tests=len(selected),
                perturbation=perturbation,
            )
            
            result = await self._test_single_perturbation(
                query=query,
                consensus=consensus,
                perturbation=perturbation,
                model=model,
            )
            results.append(result)
            
            # Report: Test complete
            report_progress(
                f"Test {i + 1}/{len(selected)}: {result.outcome.value}",
                current_percent + percent_per_test,
                test_number=i + 1,
                total_tests=len(selected),
                perturbation=perturbation,
                outcome=result.outcome.value,
            )
        
        return FragilityReport(
            perturbations_tested=len(results),
            results=results,
        )
    
    async def _test_single_perturbation(
        self,
        query: str,
        consensus: str,
        perturbation: str,
        model: str,
    ) -> FragilityResult:
        """
        Test a single perturbation against the consensus.
        
        Args:
            query: Original clinical question
            consensus: The consensus to test
            perturbation: The perturbation to apply
            model: LLM model to use
            
        Returns:
            FragilityResult with the outcome
        """
        # Build prompt
        prompt = self.prompt_template.format(
            query=query,
            consensus=consensus,
            perturbation=perturbation,
        )
        
        # Call LLM
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await self.llm_client.complete(
                model=model,
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent results
            )
            
            # Parse response
            return self._parse_response(perturbation, response.content)
            
        except Exception as e:
            logger.error(f"Error testing perturbation '{perturbation}': {e}")
            return FragilityResult(
                perturbation=perturbation,
                outcome=FragilityOutcome.SURVIVES,  # Default to survives on error
                explanation=f"Error during testing: {str(e)}",
            )
    
    def _parse_response(self, perturbation: str, content: str) -> FragilityResult:
        """
        Parse LLM response into FragilityResult.
        
        Args:
            perturbation: The perturbation tested
            content: Raw LLM response content
            
        Returns:
            Parsed FragilityResult
        """
        try:
            # Try to extract JSON from response
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
            
            # Extract outcome
            outcome_str = data.get("outcome", "SURVIVES").upper()
            try:
                outcome = FragilityOutcome(outcome_str)
            except ValueError:
                outcome = FragilityOutcome.SURVIVES
            
            return FragilityResult(
                perturbation=perturbation,
                outcome=outcome,
                explanation=data.get("explanation", "No explanation provided"),
                modified_recommendation=data.get("modified_recommendation"),
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            
            # Try to extract outcome from text
            content_upper = content.upper()
            if "COLLAPSES" in content_upper:
                outcome = FragilityOutcome.COLLAPSES
            elif "MODIFIES" in content_upper:
                outcome = FragilityOutcome.MODIFIES
            else:
                outcome = FragilityOutcome.SURVIVES
            
            return FragilityResult(
                perturbation=perturbation,
                outcome=outcome,
                explanation=content[:200],  # Use first 200 chars as explanation
            )
    
    def get_available_perturbations(self) -> list[str]:
        """Return list of available perturbations."""
        return self.perturbations.copy()
    
    def add_perturbation(self, perturbation: str):
        """Add a custom perturbation."""
        if perturbation not in self.perturbations:
            self.perturbations.append(perturbation)

