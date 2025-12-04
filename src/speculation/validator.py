"""
Speculation Validator - Validates speculations against new evidence.

Triggered when Scout finds evidence matching a speculation's watch keywords.
Determines whether to promote, upgrade, or deprecate speculations.
"""

import logging
from typing import Optional, Protocol

from src.models.v2_schemas import (
    EvidenceGrade,
    ScoutCitation,
    Speculation,
    SpeculationStatus,
    ValidationResult,
)


logger = logging.getLogger(__name__)


# =============================================================================
# LLM CLIENT PROTOCOL
# =============================================================================


class LLMClientProtocol(Protocol):
    """Protocol for LLM client used by validator."""

    async def complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> "LLMResponse":
        ...


class LLMResponse(Protocol):
    content: str


# =============================================================================
# VALIDATION PROMPT
# =============================================================================

VALIDATION_PROMPT = """You are evaluating whether new evidence supports or contradicts a hypothesis.

## The Hypothesis
{hypothesis}

## The Mechanism
{mechanism}

## Validation Criteria (What would prove this)
{validation_criteria}

## New Evidence Found
{evidence}

## Your Task

Analyze whether this evidence:
1. **CONFIRMS** the hypothesis (strong support)
2. **PARTIALLY_SUPPORTS** the hypothesis (related but not conclusive)
3. **INCONCLUSIVE** (doesn't really address the hypothesis)
4. **CONTRADICTS** the hypothesis (evidence against)

## Output Format

Provide your analysis in the following format:

SUPPORT_LEVEL: [confirms/partially_supports/inconclusive/contradicts]

KEY_FINDINGS:
- [Relevant finding 1]
- [Relevant finding 2]

REASONING:
[Your detailed analysis of how the evidence relates to the hypothesis]

REMAINING_GAPS:
- [What still needs to be proven]

Be rigorous. A preprint with n=12 does not "confirm" a hypothesis.
Only "confirms" if there is high-quality evidence directly supporting the claim.
"""


# =============================================================================
# VALIDATOR CLASS
# =============================================================================


class SpeculationValidator:
    """
    Validates speculations against new evidence.
    
    Triggered when Scout finds evidence matching a speculation.
    Uses LLM to analyze evidence quality and determine action.
    """

    def __init__(self, llm_client: LLMClientProtocol):
        """
        Initialize the validator.
        
        Args:
            llm_client: LLM client for analysis
        """
        self.llm_client = llm_client

    async def validate(
        self,
        speculation: Speculation,
        new_evidence: list[ScoutCitation],
        validation_model: str = "openai/gpt-4o",
    ) -> ValidationResult:
        """
        Validate a speculation against new evidence.
        
        Args:
            speculation: The speculation to validate
            new_evidence: New citations found by Scout
            validation_model: LLM model to use for analysis
            
        Returns:
            ValidationResult with assessment and recommended action
        """
        if not new_evidence:
            return ValidationResult(
                speculation_id=speculation.speculation_id,
                new_evidence=[],
                support_level="inconclusive",
                evidence_quality=EvidenceGrade.EXPERT_OPINION,
                action="keep_watching",
                new_status=SpeculationStatus.WATCHING,
                requires_human_review=False,
                validation_notes="No evidence to evaluate",
            )

        # Format evidence for prompt
        evidence_text = self._format_evidence(new_evidence)

        # Build validation prompt
        prompt = VALIDATION_PROMPT.format(
            hypothesis=speculation.hypothesis,
            mechanism=speculation.mechanism or "Not specified",
            validation_criteria=speculation.validation_criteria or "Not specified",
            evidence=evidence_text,
        )

        # Get LLM analysis
        try:
            response = await self.llm_client.complete(
                model=validation_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
            )

            # Parse response
            support_level = self._extract_support_level(response.content)
            reasoning = self._extract_reasoning(response.content)

        except Exception as e:
            logger.error(f"Validation LLM call failed: {e}")
            support_level = "inconclusive"
            reasoning = f"Validation failed: {e}"

        # Get best evidence grade
        best_grade = self._get_best_evidence_grade(new_evidence)

        # Determine action based on support + evidence quality
        action, new_status, requires_review = self._determine_action(
            support_level, best_grade
        )

        return ValidationResult(
            speculation_id=speculation.speculation_id,
            new_evidence=new_evidence,
            support_level=support_level,
            evidence_quality=best_grade,
            action=action,
            new_status=new_status,
            requires_human_review=requires_review,
            validation_notes=reasoning,
        )

    def _format_evidence(self, citations: list[ScoutCitation]) -> str:
        """Format citations for the validation prompt."""
        lines = []

        grade_icons = {
            EvidenceGrade.META_ANALYSIS: "🟣 META-ANALYSIS",
            EvidenceGrade.RCT_LARGE: "🟢 RCT (Large)",
            EvidenceGrade.RCT_SMALL: "🟢 RCT (Small)",
            EvidenceGrade.OBSERVATIONAL: "🟡 Observational",
            EvidenceGrade.PREPRINT: "🟡 Preprint",
            EvidenceGrade.CASE_REPORT: "🟡 Case Report",
            EvidenceGrade.CONFLICTING: "🔴 Conflicting",
            EvidenceGrade.EXPERT_OPINION: "⚪ Expert Opinion",
        }

        for c in citations:
            grade_str = grade_icons.get(c.evidence_grade, "⚪ Unknown")
            lines.append(f"### {grade_str}")
            lines.append(f"**{c.title}** ({c.year})")
            if c.sample_size:
                lines.append(f"Sample size: n={c.sample_size}")
            lines.append(f"Finding: {c.key_finding}")
            if c.pmid:
                lines.append(f"PMID: {c.pmid}")
            lines.append("")

        return "\n".join(lines)

    def _extract_support_level(self, response: str) -> str:
        """Extract support level from LLM response."""
        response_lower = response.lower()

        # Look for explicit SUPPORT_LEVEL line
        if "support_level:" in response_lower:
            for line in response.split("\n"):
                if "support_level:" in line.lower():
                    value = line.split(":", 1)[1].strip().lower()
                    if value in ["confirms", "partially_supports", "inconclusive", "contradicts"]:
                        return value

        # Fallback to keyword detection
        if "confirms" in response_lower and "not confirm" not in response_lower:
            return "confirms"
        elif "contradicts" in response_lower or "contradicted" in response_lower:
            return "contradicts"
        elif "partial" in response_lower or "some support" in response_lower:
            return "partially_supports"

        return "inconclusive"

    def _extract_reasoning(self, response: str) -> str:
        """Extract reasoning section from LLM response."""
        # Look for REASONING: section
        if "REASONING:" in response:
            parts = response.split("REASONING:")
            if len(parts) > 1:
                reasoning = parts[1].split("REMAINING_GAPS:")[0].strip()
                return reasoning[:500]  # Truncate to reasonable length

        # Fallback: take middle portion of response
        lines = response.split("\n")
        # Skip first few lines (likely headers) and last few (likely gaps)
        middle = lines[3:-3] if len(lines) > 6 else lines
        return "\n".join(middle)[:500]

    def _get_best_evidence_grade(self, citations: list[ScoutCitation]) -> EvidenceGrade:
        """Get the highest quality evidence grade from citations."""
        grade_order = [
            EvidenceGrade.META_ANALYSIS,
            EvidenceGrade.RCT_LARGE,
            EvidenceGrade.RCT_SMALL,
            EvidenceGrade.OBSERVATIONAL,
            EvidenceGrade.CASE_REPORT,
            EvidenceGrade.PREPRINT,
            EvidenceGrade.EXPERT_OPINION,
        ]

        for grade in grade_order:
            if any(c.evidence_grade == grade for c in citations):
                return grade

        return EvidenceGrade.EXPERT_OPINION

    def _determine_action(
        self,
        support_level: str,
        evidence_grade: EvidenceGrade,
    ) -> tuple[str, SpeculationStatus, bool]:
        """
        Determine action based on support level and evidence quality.
        
        Returns:
            Tuple of (action, new_status, requires_human_review)
        """
        high_quality = evidence_grade in [
            EvidenceGrade.META_ANALYSIS,
            EvidenceGrade.RCT_LARGE,
        ]

        if support_level == "confirms":
            if high_quality:
                # Strong evidence confirms - promote to Experience Library
                return (
                    "promote_to_experience_library",
                    SpeculationStatus.VALIDATED,
                    True,  # Human review required for promotion
                )
            else:
                # Weaker evidence confirms - upgrade but don't promote yet
                return (
                    "upgrade_status",
                    SpeculationStatus.PARTIALLY_VALIDATED,
                    True,
                )

        elif support_level == "partially_supports":
            return (
                "upgrade_status",
                SpeculationStatus.PARTIALLY_VALIDATED,
                False,  # Can auto-upgrade, no human needed
            )

        elif support_level == "contradicts":
            if high_quality:
                # Strong evidence contradicts - deprecate
                return (
                    "deprecate",
                    SpeculationStatus.CONTRADICTED,
                    True,  # Human should verify before deprecating
                )
            else:
                # Weak contradiction - keep watching
                return (
                    "keep_watching",
                    SpeculationStatus.WATCHING,
                    True,  # Flag for review
                )

        else:  # inconclusive
            return (
                "keep_watching",
                SpeculationStatus.WATCHING,
                False,
            )


async def run_validation_scan(
    speculation_library: "SpeculationLibrary",
    scout_report: "ScoutReport",
    validator: SpeculationValidator,
) -> list[ValidationResult]:
    """
    Scan Scout report for matches against watched speculations.
    
    Args:
        speculation_library: The speculation library to scan
        scout_report: Recent Scout findings
        validator: Validator instance
        
    Returns:
        List of validation results for matched speculations
    """
    if scout_report.is_empty:
        return []

    # Get all watch keywords
    watch_entries = speculation_library.get_all_watch_keywords()

    if not watch_entries:
        return []

    # Collect all citations
    all_citations = (
        scout_report.meta_analyses
        + scout_report.high_quality_rcts
        + scout_report.preliminary_evidence
        + scout_report.conflicting_evidence
    )

    results = []

    for entry in watch_entries:
        # Check if any citation matches any keyword
        matching_citations = []

        for citation in all_citations:
            citation_text = f"{citation.title} {citation.key_finding}".lower()

            for keyword in entry["keywords"]:
                if keyword.lower() in citation_text:
                    matching_citations.append(citation)
                    break

        if matching_citations:
            # Get the full speculation
            speculation = speculation_library.get(entry["speculation_id"])

            if speculation:
                # Run validation
                result = await validator.validate(speculation, matching_citations)
                results.append(result)

                # Record the match
                speculation_library.record_evidence_match(
                    speculation_id=speculation.speculation_id,
                    citations=matching_citations,
                    match_quality="partial",
                )

                logger.info(
                    f"Validated speculation {speculation.speculation_id}: "
                    f"{result.support_level}"
                )

    return results

