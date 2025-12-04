"""
Arbitrator v2.1 - Bifurcated synthesis for lane-based architecture.

Produces separate Clinical Consensus (Lane A) and Exploratory Considerations (Lane B),
along with tensions between lanes and preserved dissent.
"""

import re
from typing import Optional, Protocol

from src.models.conference import (
    ArbitratorConfig,
    ConferenceRound,
    LLMResponse,
)
from src.models.v2_schemas import (
    ArbitratorSynthesis,
    ClinicalConsensus,
    Critique,
    ExploratoryConsideration,
    FeasibilityAssessment,
    Lane,
    LaneResult,
    ScoutReport,
    Tension,
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


# =============================================================================
# V2.1 ARBITRATOR PROMPT
# =============================================================================

ARBITRATOR_V2_SYSTEM_PROMPT = """You are the Arbitrator in a multi-agent clinical case conference. Your role is to synthesize the outputs from two parallel reasoning lanes and produce a bifurcated recommendation.

## Your Task

You have access to:
1. **Lane A (Clinical)** - Empiricist, Skeptic, Pragmatist, Patient Voice
   - Focus: Evidence-based, safe, implementable recommendations
   
2. **Lane B (Exploratory)** - Mechanist, Speculator
   - Focus: Mechanism-based insights, innovative approaches, hypotheses

3. **Cross-Examination** - Each lane has critiqued the other
   - Safety critiques from Skeptic about Lane B
   - Stagnation critiques from Speculator about Lane A

4. **Feasibility Assessments** - Pragmatist and Patient Voice on both lanes

## Output Format

You MUST produce output in the following format:

### CLINICAL CONSENSUS (Lane A)

**Primary Recommendation**:
[The actionable, evidence-based recommendation for this patient]

**Evidence Basis**:
- [Citation/Evidence 1]
- [Citation/Evidence 2]

**Confidence**: [High/Medium/Low]

**Safety Considerations**:
[Key safety points, contraindications, monitoring needed]

**Implementation Notes**:
[Practical considerations for implementation]

---

### EXPLORATORY CONSIDERATIONS (Lane B)

**HYPOTHESIS 1: [Title]**
- Mechanism: [Proposed mechanism]
- Evidence needed: [What would validate this]
- Risk/Reward: [Assessment]

**HYPOTHESIS 2: [Title]** (if applicable)
- Mechanism: [Proposed mechanism]
- Evidence needed: [What would validate this]
- Risk/Reward: [Assessment]

---

### TENSIONS & CONFLICTS

**Tension 1**: [Description]
- Lane A says: [Position]
- Lane B says: [Position]
- Resolution: [How to think about this - defer to clinical/exploration/unresolved]

---

### WHAT WOULD CHANGE THIS RECOMMENDATION

[Specific conditions under which the clinical recommendation would change]

---

### PRESERVED DISSENT

[Any strong disagreements that should not be hidden from the user]

---

### OVERALL CONFIDENCE

**Level**: [High/Medium/Low]

**Uncertainty Map**:
- Agreed: [Topics where all agents converged]
- Contested: [Topics with active disagreement]
- Unknown: [Topics where we lack sufficient data]

## Critical Rules

1. Do NOT pick a winner between Lane A and Lane B - they serve different purposes
2. Do NOT hide safety concerns raised by Skeptic
3. Do NOT dismiss speculative ideas - present them as what they are (hypotheses)
4. If grounding failed for a citation, note it explicitly
5. If Scout found relevant evidence, incorporate it appropriately
"""


ARBITRATOR_V2_USER_PROMPT = """## Clinical Query

{query}

## Patient Context

{patient_context}

## Scout Report (Recent Evidence)

{scout_report}

## Lane A: Clinical Consensus Track

{lane_a_output}

## Lane B: Exploratory Track

{lane_b_output}

## Cross-Examination Critiques

{cross_exam}

## Feasibility Assessments

{feasibility}

---

Now synthesize these inputs into a bifurcated recommendation following the output format specified in your instructions.
"""


# =============================================================================
# ARBITRATOR V2 CLASS
# =============================================================================


class ArbitratorV2:
    """
    v2.1 Arbitrator for lane-based conference synthesis.
    
    Produces bifurcated output:
    - Clinical Consensus (from Lane A)
    - Exploratory Considerations (from Lane B)
    - Tensions between lanes
    - Preserved dissent
    """

    def __init__(
        self,
        config: ArbitratorConfig,
        llm_client: LLMClientProtocol,
    ):
        """
        Initialize the v2.1 arbitrator.
        
        Args:
            config: Arbitrator configuration
            llm_client: LLM client for API calls
        """
        self.config = config
        self.llm_client = llm_client

    async def synthesize_lanes(
        self,
        query: str,
        lane_a_result: LaneResult,
        lane_b_result: LaneResult,
        cross_exam_critiques: list[Critique],
        feasibility_assessments: list[FeasibilityAssessment],
        patient_context_str: str = "",
        scout_report: Optional[ScoutReport] = None,
    ) -> tuple[ArbitratorSynthesis, LLMResponse]:
        """
        Synthesize lane results into bifurcated output.
        
        Args:
            query: Original clinical question
            lane_a_result: Results from Lane A (Clinical)
            lane_b_result: Results from Lane B (Exploratory)
            cross_exam_critiques: Cross-examination critiques
            feasibility_assessments: Feasibility assessments
            patient_context_str: Formatted patient context
            scout_report: Optional Scout findings
            
        Returns:
            Tuple of (ArbitratorSynthesis, raw LLMResponse)
        """
        # Format inputs
        lane_a_output = self._format_lane_output(lane_a_result, "Clinical")
        lane_b_output = self._format_lane_output(lane_b_result, "Exploratory")
        cross_exam_str = self._format_critiques(cross_exam_critiques)
        feasibility_str = self._format_feasibility(feasibility_assessments)
        scout_str = scout_report.to_context_block() if scout_report else "No recent evidence found."

        # Build prompt
        user_prompt = ARBITRATOR_V2_USER_PROMPT.format(
            query=query,
            patient_context=patient_context_str or "Not provided",
            scout_report=scout_str,
            lane_a_output=lane_a_output,
            lane_b_output=lane_b_output,
            cross_exam=cross_exam_str,
            feasibility=feasibility_str,
        )

        messages = [
            {"role": "system", "content": ARBITRATOR_V2_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # Call LLM
        llm_response = await self.llm_client.complete(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=2500,
        )

        # Parse response
        synthesis = self._parse_synthesis(llm_response.content, cross_exam_critiques)

        return synthesis, llm_response

    def _format_lane_output(self, lane_result: LaneResult, lane_name: str) -> str:
        """Format lane output for the prompt."""
        if not lane_result.agent_responses:
            return f"No {lane_name} responses available."

        lines = []
        for agent_id, response in lane_result.agent_responses.items():
            role_display = self._role_display(response.role)
            lines.append(f"### {role_display}")
            lines.append(f"**Confidence**: {response.confidence:.0%}")
            lines.append("")
            lines.append(response.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _format_critiques(self, critiques: list[Critique]) -> str:
        """Format cross-examination critiques for the prompt."""
        if not critiques:
            return "No cross-examination performed."

        lines = []
        for critique in critiques:
            lines.append(f"### {self._role_display(critique.critic_role)} critiques Lane {critique.target_lane.value}")
            lines.append(f"**Type**: {critique.critique_type}")
            lines.append(f"**Severity**: {critique.severity}")
            lines.append("")
            lines.append(critique.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _format_feasibility(self, assessments: list[FeasibilityAssessment]) -> str:
        """Format feasibility assessments for the prompt."""
        if not assessments:
            return "No feasibility assessment performed."

        lines = []
        for assessment in assessments:
            lines.append(f"### {self._role_display(assessment.assessor_role)} on Lane {assessment.target_lane.value}")
            lines.append(f"**Overall Feasibility**: {assessment.overall_feasibility}")
            lines.append("")
            lines.append(assessment.summary)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _parse_synthesis(
        self,
        content: str,
        critiques: list[Critique],
    ) -> ArbitratorSynthesis:
        """Parse LLM response into ArbitratorSynthesis."""
        
        # Parse clinical consensus
        clinical_consensus = self._parse_clinical_consensus(content)
        
        # Parse exploratory considerations
        exploratory = self._parse_exploratory(content)
        
        # Parse tensions
        tensions = self._parse_tensions(content)
        
        # Extract safety concerns from critiques
        safety_concerns = [
            c.content[:200] for c in critiques
            if c.critique_type == "safety"
        ]
        
        # Extract stagnation concerns
        stagnation_concerns = [
            c.content[:200] for c in critiques
            if c.critique_type == "stagnation"
        ]
        
        # Parse what would change
        what_would_change = self._extract_section(
            content,
            ["What Would Change", "What Would Change This Recommendation"],
        )
        
        # Parse preserved dissent
        dissent_section = self._extract_section(
            content,
            ["Preserved Dissent", "Dissent"],
        )
        preserved_dissent = self._parse_bullet_points(dissent_section) if dissent_section else []
        
        # Parse overall confidence
        confidence = self._extract_confidence(content)
        
        # Parse uncertainty map
        uncertainty_map = self._parse_uncertainty_map(content)

        return ArbitratorSynthesis(
            clinical_consensus=clinical_consensus,
            exploratory_considerations=exploratory,
            tensions=tensions,
            safety_concerns_raised=safety_concerns,
            stagnation_concerns_raised=stagnation_concerns,
            what_would_change_mind=what_would_change,
            preserved_dissent=preserved_dissent,
            overall_confidence=confidence,
            uncertainty_map=uncertainty_map,
        )

    def _parse_clinical_consensus(self, content: str) -> ClinicalConsensus:
        """Parse clinical consensus section."""
        # Find the clinical consensus section
        clinical_section = self._extract_section(
            content,
            ["Clinical Consensus", "CLINICAL CONSENSUS"],
        )

        if not clinical_section:
            clinical_section = content[:1000]  # Fallback

        # Extract recommendation
        recommendation = self._extract_field(
            clinical_section,
            ["Primary Recommendation", "Recommendation"],
        ) or clinical_section[:500]

        # Extract evidence basis
        evidence_section = self._extract_field(
            clinical_section,
            ["Evidence Basis", "Evidence"],
        )
        evidence_basis = self._parse_bullet_points(evidence_section) if evidence_section else []

        # Extract confidence
        confidence_str = self._extract_field(
            clinical_section,
            ["Confidence"],
        )
        confidence = self._parse_confidence_level(confidence_str)

        # Extract safety
        safety = self._extract_field(
            clinical_section,
            ["Safety Considerations", "Safety"],
        ) or ""

        # Extract implementation
        implementation = self._extract_field(
            clinical_section,
            ["Implementation Notes", "Implementation"],
        )
        
        # Parse contraindications if present
        contraindications = []
        if "contraindication" in clinical_section.lower():
            contra_match = re.search(
                r"contraindication[s]?[:\s]+(.+?)(?:\n\n|\Z)",
                clinical_section,
                re.IGNORECASE | re.DOTALL,
            )
            if contra_match:
                contraindications = self._parse_bullet_points(contra_match.group(1))

        return ClinicalConsensus(
            recommendation=recommendation.strip(),
            evidence_basis=evidence_basis,
            confidence=confidence,
            safety_profile=safety,
            contraindications=contraindications,
            monitoring_required=[],  # Could be parsed if present
        )

    def _parse_exploratory(self, content: str) -> list[ExploratoryConsideration]:
        """Parse exploratory considerations section."""
        exploratory_section = self._extract_section(
            content,
            ["Exploratory Considerations", "EXPLORATORY CONSIDERATIONS", "Lane B"],
        )

        if not exploratory_section:
            return []

        considerations = []

        # Find HYPOTHESIS sections
        hypothesis_pattern = r"\*\*HYPOTHESIS\s*\d*[:\s]*([^*]+)\*\*(.*?)(?=\*\*HYPOTHESIS|\Z)"
        matches = re.findall(hypothesis_pattern, exploratory_section, re.DOTALL | re.IGNORECASE)

        for title, body in matches:
            # Extract mechanism
            mechanism = self._extract_field(body, ["Mechanism"]) or ""

            # Extract evidence needed
            evidence_needed = self._extract_field(
                body,
                ["Evidence needed", "Evidence that would validate"],
            ) or ""

            # Extract risk/reward
            risk_reward = self._extract_field(body, ["Risk/Reward", "Risk"]) or ""

            # Parse risks from risk/reward
            risks = []
            if "risk" in risk_reward.lower():
                risk_parts = risk_reward.split("/")
                if len(risk_parts) > 1:
                    risks = [risk_parts[1].strip()]

            considerations.append(ExploratoryConsideration(
                hypothesis=title.strip(),
                mechanism=mechanism,
                evidence_level="theoretical",
                potential_benefit=risk_reward.split("/")[0].strip() if "/" in risk_reward else "",
                risks=risks,
                what_would_validate=evidence_needed,
                is_hypothesis=True,
            ))

        return considerations

    def _parse_tensions(self, content: str) -> list[Tension]:
        """Parse tensions section."""
        tensions_section = self._extract_section(
            content,
            ["Tensions", "TENSIONS", "Tensions & Conflicts", "TENSIONS & CONFLICTS"],
        )

        if not tensions_section:
            return []

        tensions = []

        # Find tension entries
        tension_pattern = r"\*\*Tension\s*\d*\*\*[:\s]*([^\n]+)(.*?)(?=\*\*Tension|\Z)"
        matches = re.findall(tension_pattern, tensions_section, re.DOTALL | re.IGNORECASE)

        for description, body in matches:
            lane_a_pos = self._extract_field(body, ["Lane A says", "Lane A"]) or ""
            lane_b_pos = self._extract_field(body, ["Lane B says", "Lane B"]) or ""
            resolution_text = self._extract_field(body, ["Resolution"]) or ""

            # Determine resolution type
            resolution = "unresolved"
            if "defer to clinical" in resolution_text.lower():
                resolution = "defer_to_clinical"
            elif "defer to exploration" in resolution_text.lower():
                resolution = "defer_to_exploration"
            elif "context" in resolution_text.lower():
                resolution = "context_dependent"

            tensions.append(Tension(
                description=description.strip(),
                lane_a_position=lane_a_pos,
                lane_b_position=lane_b_pos,
                resolution=resolution,
                resolution_rationale=resolution_text,
            ))

        return tensions

    def _parse_uncertainty_map(self, content: str) -> dict[str, str]:
        """Parse uncertainty map section."""
        uncertainty_section = self._extract_section(
            content,
            ["Uncertainty Map", "UNCERTAINTY MAP"],
        )

        if not uncertainty_section:
            return {}

        uncertainty_map = {}

        # Extract agreed topics
        agreed = self._extract_field(uncertainty_section, ["Agreed"])
        if agreed:
            for topic in agreed.split(","):
                topic = topic.strip()
                if topic:
                    uncertainty_map[topic] = "agreed"

        # Extract contested topics
        contested = self._extract_field(uncertainty_section, ["Contested"])
        if contested:
            for topic in contested.split(","):
                topic = topic.strip()
                if topic:
                    uncertainty_map[topic] = "contested"

        # Extract unknown topics
        unknown = self._extract_field(uncertainty_section, ["Unknown"])
        if unknown:
            for topic in unknown.split(","):
                topic = topic.strip()
                if topic:
                    uncertainty_map[topic] = "unknown"

        return uncertainty_map

    def _extract_section(self, content: str, headers: list[str]) -> str:
        """Extract a section by header."""
        for header in headers:
            patterns = [
                rf"###\s*{header}[^\n]*\n(.*?)(?=\n###|\n---|\Z)",
                rf"##\s*{header}[^\n]*\n(.*?)(?=\n##|\n---|\Z)",
                rf"\*\*{header}\*\*[:\s]*\n?(.*?)(?=\n\*\*|\n---|\Z)",
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return ""

    def _extract_field(self, content: str, field_names: list[str]) -> Optional[str]:
        """Extract a single field value."""
        for field in field_names:
            patterns = [
                rf"\*\*{field}\*\*[:\s]*(.+?)(?:\n\n|\n\*\*|\Z)",
                rf"{field}[:\s]*(.+?)(?:\n\n|\n\*\*|\Z)",
                rf"-\s*{field}[:\s]*(.+?)(?:\n|$)",
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    return match.group(1).strip()

        return None

    def _parse_bullet_points(self, content: str) -> list[str]:
        """Parse bullet points from content."""
        if not content:
            return []

        points = []
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
        """Extract overall confidence level."""
        confidence_section = self._extract_section(
            content,
            ["Overall Confidence", "OVERALL CONFIDENCE"],
        )

        if confidence_section:
            return self._parse_confidence_level(confidence_section)

        # Fallback to searching content
        content_lower = content.lower()
        if "high" in content_lower and "confidence" in content_lower:
            return 0.85
        elif "low" in content_lower and "confidence" in content_lower:
            return 0.35

        return 0.6

    def _parse_confidence_level(self, text: Optional[str]) -> float:
        """Parse confidence level from text."""
        if not text:
            return 0.6

        text_lower = text.lower()
        if "high" in text_lower:
            return 0.85
        elif "low" in text_lower:
            return 0.35
        elif "medium" in text_lower or "moderate" in text_lower:
            return 0.6

        return 0.6

    def _role_display(self, role: str) -> str:
        """Get display name for a role."""
        displays = {
            "empiricist": "Empiricist",
            "skeptic": "Skeptic",
            "pragmatist": "Pragmatist",
            "patient_voice": "Patient Voice",
            "mechanist": "Mechanist",
            "speculator": "Speculator",
            "advocate": "Advocate",
        }
        return displays.get(role, role.title())

