"""
Heuristic Injector - Injects retrieved heuristics into conference prompts.

Presents heuristics as hypotheses that agents must explicitly validate
or reject, preventing blind acceptance.
"""

import logging
from typing import Optional

from src.models.experience import (
    CollisionType,
    HeuristicCollision,
    InjectionContext,
    InjectionResult,
    ReasoningArtifact,
)
from src.learning.library import ExperienceLibrary
from src.learning.classifier import ClassifiedQuery


logger = logging.getLogger(__name__)


class HeuristicInjector:
    """
    Injects retrieved heuristics into agent prompts.
    
    The injection format forces agents to:
    1. Validate qualifying conditions
    2. Check for disqualifying conditions
    3. Consider fragility factors
    4. Explicitly incorporate or reject the heuristic
    """
    
    def __init__(self, library: ExperienceLibrary):
        """
        Initialize the injector.
        
        Args:
            library: Experience Library to retrieve heuristics from
        """
        self.library = library
    
    def get_injection_for_query(self, classified_query: ClassifiedQuery) -> InjectionResult:
        """
        Get heuristics to inject for a classified query.
        
        Args:
            classified_query: The classified query
            
        Returns:
            InjectionResult with heuristics and formatted prompt
        """
        context = InjectionContext(
            query=classified_query.raw_text,
            domain=classified_query.domain,
            patient_factors=classified_query.extracted_entities.get("patient_features", []),
        )
        
        return self.library.get_injection(context)
    
    def build_agent_injection_prompt(
        self,
        injection_result: InjectionResult,
        agent_role: str,
    ) -> str:
        """
        Build the injection prompt for a specific agent.
        
        Args:
            injection_result: Result from library lookup
            agent_role: Role of the agent (advocate, skeptic, etc.)
            
        Returns:
            Formatted injection prompt to prepend to agent instructions
        """
        if injection_result.genesis_mode:
            return self._build_genesis_prompt(injection_result, agent_role)
        
        if injection_result.collision:
            return self._build_collision_prompt(injection_result, agent_role)
        
        if injection_result.heuristics:
            return self._build_single_heuristic_prompt(
                injection_result.heuristics[0], 
                agent_role
            )
        
        return ""  # No injection needed
    
    def _build_genesis_prompt(self, result: InjectionResult, role: str) -> str:
        """Build prompt for genesis mode (no heuristics)."""
        coverage_desc = "low" if result.domain_coverage < 10 else "moderate" if result.domain_coverage < 50 else "good"
        
        role_note = ""
        if role == "advocate":
            role_note = "As the Advocate, you may be establishing the first strong position for this query type."
        elif role == "skeptic":
            role_note = "As the Skeptic, apply rigorous scrutiny since there's no prior institutional knowledge."
        elif role == "empiricist":
            role_note = "As the Empiricist, ground your analysis entirely in current evidence."
        
        return f"""
---
### 🧠 Experience Library Note
**No relevant heuristics found** for this query type.
**Domain coverage:** {result.domain_coverage} heuristics ({coverage_desc})

{role_note}

If this conference reaches high-quality consensus, it may become a founding heuristic 
for this query type. Reason carefully.
---
"""
    
    def _build_single_heuristic_prompt(self, heuristic: ReasoningArtifact, role: str) -> str:
        """Build prompt for a single heuristic injection."""
        h = heuristic
        
        # Format conditions as checkboxes
        qualifying = "\n".join(f"  - [ ] {c}" for c in h.qualifying_conditions) if h.qualifying_conditions else "  - None specified"
        disqualifying = "\n".join(f"  - [ ] {c}" for c in h.disqualifying_conditions) if h.disqualifying_conditions else "  - None specified"
        fragility = "\n".join(f"  - {f}" for f in h.fragility_factors) if h.fragility_factors else "  - None identified"
        
        # Role-specific guidance
        role_guidance = self._get_role_guidance(role)
        
        validation_rate = f"{h.times_accepted}/{h.times_injected}" if h.times_injected > 0 else "Not yet validated"
        
        return f"""
---
### 🧠 Experience Library Retrieval

**⚠️ IMPORTANT:** This is a *hypothesis* from past conferences, NOT a directive.
You MUST validate it against the current case before incorporating.

**Heuristic ID:** `{h.heuristic_id}`
**Confidence:** {h.confidence:.0%} | **Prior validations:** {validation_rate}
**Source:** Conference `{h.source_conference_id}`

**Heuristic:**
> {h.winning_heuristic}

{f'**Counter-argument that was rejected:**' + chr(10) + f'> {h.contra_heuristic}' + chr(10) if h.contra_heuristic else ''}

**Qualifying Conditions (YOU MUST CHECK):**
{qualifying}

**Disqualifying Conditions (CHECK FOR PRESENCE):**
{disqualifying}

**Known Fragility Factors:**
{fragility}

---
{role_guidance}

**MANDATORY:** In your response, you must include a validation section:
```
HEURISTIC VALIDATION [{h.heuristic_id}]:
- Qualifying conditions: [PASS/FAIL for each with reason]
- Disqualifying conditions: [CLEAR/PRESENT for each with reason]
- Relevant fragility factors: [list any that apply]
- Decision: INCORPORATE / REJECT / MODIFY
- Reasoning: [brief explanation]
```
---
"""
    
    def _build_collision_prompt(self, result: InjectionResult, role: str) -> str:
        """Build prompt for colliding heuristics."""
        h1, h2 = result.heuristics[0], result.heuristics[1]
        collision = result.collision
        
        # Format heuristic summaries
        h1_summary = self._format_heuristic_brief(h1)
        h2_summary = self._format_heuristic_brief(h2)
        
        role_guidance = self._get_collision_role_guidance(role)
        
        return f"""
---
### 🧠 Experience Library Retrieval (COLLISION DETECTED)

**⚠️ WARNING:** Two potentially conflicting heuristics were retrieved.
**Collision type:** {collision.collision_type.value}
**Resolution hint:** {collision.resolution_hint}

---

**HEURISTIC A** [`{h1.heuristic_id}`]
{h1_summary}

---

**HEURISTIC B** [`{h2.heuristic_id}`]
{h2_summary}

---
{role_guidance}

**MANDATORY:** You must validate EACH heuristic independently:
```
HEURISTIC A VALIDATION [{h1.heuristic_id}]:
- Qualifying: [PASS/FAIL for each]
- Disqualifying: [CLEAR/PRESENT for each]
- Decision: INCORPORATE / REJECT

HEURISTIC B VALIDATION [{h2.heuristic_id}]:
- Qualifying: [PASS/FAIL for each]
- Disqualifying: [CLEAR/PRESENT for each]
- Decision: INCORPORATE / REJECT

COLLISION RESOLUTION:
[If both pass, explain which applies to this patient and why]
[If conflict unresolvable, flag as "Genuine Clinical Equipoise"]
```
---
"""
    
    def _format_heuristic_brief(self, h: ReasoningArtifact) -> str:
        """Format a brief heuristic summary."""
        qualifying = ", ".join(h.qualifying_conditions[:2]) if h.qualifying_conditions else "None"
        if len(h.qualifying_conditions) > 2:
            qualifying += "..."
        
        disqualifying = ", ".join(h.disqualifying_conditions[:2]) if h.disqualifying_conditions else "None"
        if len(h.disqualifying_conditions) > 2:
            disqualifying += "..."
        
        return f"""**Confidence:** {h.confidence:.0%} | **Validations:** {h.times_accepted}/{h.times_injected}
**Heuristic:** "{h.winning_heuristic}"
**Qualifying:** {qualifying}
**Disqualifying:** {disqualifying}"""
    
    def _get_role_guidance(self, role: str) -> str:
        """Get role-specific guidance for heuristic validation."""
        guidance = {
            "advocate": """**Role Guidance (Advocate):**
If this heuristic validates, incorporate it as supporting evidence for your position.
If it conflicts with your analysis, explain clearly why your approach is superior.""",
            
            "skeptic": """**Role Guidance (Skeptic):**
Critically examine this heuristic. Check if conditions truly apply to THIS patient.
Look for edge cases or factors that might invalidate it.""",
            
            "empiricist": """**Role Guidance (Empiricist):**
Cross-reference this heuristic against current literature. 
Verify the evidence PMIDs are still the most relevant sources.""",
            
            "arbitrator": """**Role Guidance (Arbitrator):**
Consider whether agents properly validated this heuristic.
Note any disagreements about its applicability in your synthesis.""",
        }
        return guidance.get(role, "")
    
    def _get_collision_role_guidance(self, role: str) -> str:
        """Get role-specific guidance for collision resolution."""
        guidance = {
            "advocate": """**Role Guidance (Advocate):**
Evaluate which heuristic better supports optimal patient outcomes.
Argue for the one you believe is most applicable.""",
            
            "skeptic": """**Role Guidance (Skeptic):**
Challenge both heuristics. The collision may indicate neither fully applies.
Look for patient factors that differentiate this case.""",
            
            "empiricist": """**Role Guidance (Empiricist):**
Compare the evidence bases for both heuristics.
Determine if one has stronger or more recent support.""",
            
            "arbitrator": """**Role Guidance (Arbitrator):**
Track how other agents resolve this collision.
Note if genuine equipoise exists.""",
        }
        return guidance.get(role, "")
    
    def record_heuristic_outcome(
        self,
        heuristic_id: str,
        outcome: str,  # "accepted", "rejected", "modified"
    ):
        """
        Record how a heuristic was used in a conference.
        
        Args:
            heuristic_id: ID of the heuristic
            outcome: How it was used
        """
        self.library.record_usage(heuristic_id, outcome)
        logger.info(f"Recorded heuristic {heuristic_id} outcome: {outcome}")

