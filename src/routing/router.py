"""
Intelligent Router - Determines conference configuration.

Combines deterministic complexity signals with LLM-based analysis
to route queries to the appropriate conference mode.
"""

import json
import logging
from typing import Optional, Protocol

from src.models.v2_schemas import (
    ConferenceMode,
    PatientContext,
    RoutingDecision,
)
from src.routing.signals import classify_signals, detect_complexity_signals


logger = logging.getLogger(__name__)


# =============================================================================
# LLM CLIENT PROTOCOL
# =============================================================================


class LLMClientProtocol(Protocol):
    """Protocol for LLM client used by router."""

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
# MODE CONFIGURATIONS
# =============================================================================

# Agent configurations by mode
MODE_AGENT_CONFIGS: dict[ConferenceMode, dict] = {
    ConferenceMode.STANDARD_CARE: {
        "agents": ["empiricist", "pragmatist", "arbitrator"],
        "scout": False,
        "risk_profile": 0.2,
        "rounds": 2,
    },
    ConferenceMode.COMPLEX_DILEMMA: {
        "agents": [
            "empiricist",
            "skeptic",
            "mechanist",
            "pragmatist",
            "patient_voice",
            "arbitrator",
        ],
        "scout": True,
        "risk_profile": 0.5,
        "rounds": 3,
    },
    ConferenceMode.NOVEL_RESEARCH: {
        "agents": [
            "empiricist",
            "skeptic",
            "mechanist",
            "speculator",
            "pragmatist",
            "patient_voice",
            "arbitrator",
        ],
        "scout": True,
        "risk_profile": 0.7,
        "rounds": 4,
    },
    ConferenceMode.DIAGNOSTIC_PUZZLE: {
        "agents": [
            "empiricist",
            "skeptic",
            "mechanist",
            "arbitrator",
        ],
        "scout": True,
        "risk_profile": 0.4,
        "rounds": 3,
    },
}


# =============================================================================
# ROUTER PROMPT
# =============================================================================

ROUTER_SYSTEM_PROMPT = """You are the Conference Router. Your job is to analyze a clinical query and determine the appropriate conference configuration.

You must output a JSON object with the following fields:
- mode: One of "STANDARD_CARE", "COMPLEX_DILEMMA", "NOVEL_RESEARCH", "DIAGNOSTIC_PUZZLE"
- rationale: Brief explanation of your choice (1-2 sentences)

## Mode Definitions

**STANDARD_CARE**: Use when the query is a straightforward guideline check with clear answers.
Examples:
- "What is the first-line treatment for hypertension?"
- "Dosing for amoxicillin in adults"
- "Contraindications for metformin"

**COMPLEX_DILEMMA**: Use when multiple factors complicate the decision.
Examples:
- Patient has failed multiple treatments
- Multiple comorbidities affecting drug choice
- Drug interactions to consider
- Conflicting guidelines

**NOVEL_RESEARCH**: Use when the query involves experimental, off-label, or cutting-edge approaches.
Examples:
- "Peptide therapy for CRPS"
- "Any new approaches to treatment-resistant depression?"
- Requests for mechanisms of experimental drugs
- Cases where all standard treatments have failed

**DIAGNOSTIC_PUZZLE**: Use when the diagnosis itself is uncertain.
Examples:
- "What could cause this constellation of symptoms?"
- Atypical presentations
- Rare disease considerations

## Output Format

```json
{
    "mode": "COMPLEX_DILEMMA",
    "rationale": "Patient has failed gabapentin and pregabalin, suggesting need for full conference with multiple perspectives."
}
```

Err on the side of COMPLEX_DILEMMA or NOVEL_RESEARCH if uncertain. It's better to over-analyze than to miss something.
"""


# =============================================================================
# MAIN ROUTING FUNCTION
# =============================================================================


async def route_query(
    query: str,
    patient_context: Optional[PatientContext] = None,
    llm_client: Optional[LLMClientProtocol] = None,
    router_model: str = "openai/gpt-4o",
) -> RoutingDecision:
    """
    Main routing function. Combines deterministic triggers with LLM judgment.
    
    Args:
        query: The clinical question to route
        patient_context: Optional patient information
        llm_client: LLM client for nuanced routing (optional, falls back to rule-based)
        router_model: Model to use for LLM routing
        
    Returns:
        RoutingDecision with mode, agents, and scout activation
    """
    # Step 1: Check deterministic complexity signals
    complexity_signals = detect_complexity_signals(query, patient_context)
    signal_counts = classify_signals(complexity_signals)

    logger.debug(f"Detected {len(complexity_signals)} complexity signals")

    # Step 2: Check for automatic escalation based on signals
    
    # Auto-escalate to NOVEL_RESEARCH if treatment failure signals
    if signal_counts["escalation"] >= 2 or signal_counts["novel"] >= 2:
        mode = ConferenceMode.NOVEL_RESEARCH
        config = MODE_AGENT_CONFIGS[mode]
        
        logger.info(f"Auto-escalating to NOVEL_RESEARCH due to signals: {complexity_signals}")
        
        return RoutingDecision(
            mode=mode,
            active_agents=config["agents"],
            activate_scout=config["scout"],
            risk_profile=config["risk_profile"],
            routing_rationale=f"Auto-escalated due to treatment failure/novel signals: {len(complexity_signals)} triggers detected",
            complexity_signals_detected=complexity_signals,
            estimated_rounds=config["rounds"],
        )

    # Auto-escalate to DIAGNOSTIC_PUZZLE if diagnostic uncertainty signals
    if signal_counts["diagnostic"] >= 2:
        mode = ConferenceMode.DIAGNOSTIC_PUZZLE
        config = MODE_AGENT_CONFIGS[mode]
        
        logger.info(f"Auto-escalating to DIAGNOSTIC_PUZZLE due to signals: {complexity_signals}")
        
        return RoutingDecision(
            mode=mode,
            active_agents=config["agents"],
            activate_scout=config["scout"],
            risk_profile=config["risk_profile"],
            routing_rationale="Auto-escalated due to diagnostic uncertainty signals",
            complexity_signals_detected=complexity_signals,
            estimated_rounds=config["rounds"],
        )

    # Auto-escalate to COMPLEX_DILEMMA if patient complexity
    if signal_counts["patient"] >= 2 or len(complexity_signals) >= 3:
        mode = ConferenceMode.COMPLEX_DILEMMA
        config = MODE_AGENT_CONFIGS[mode]
        
        logger.info(f"Auto-escalating to COMPLEX_DILEMMA due to signals: {complexity_signals}")
        
        return RoutingDecision(
            mode=mode,
            active_agents=config["agents"],
            activate_scout=config["scout"],
            risk_profile=config["risk_profile"],
            routing_rationale=f"Auto-escalated due to patient complexity: {len(complexity_signals)} triggers detected",
            complexity_signals_detected=complexity_signals,
            estimated_rounds=config["rounds"],
        )

    # Step 3: Use LLM for nuanced routing if available
    if llm_client:
        return await _llm_route(
            query=query,
            patient_context=patient_context,
            llm_client=llm_client,
            router_model=router_model,
            complexity_signals=complexity_signals,
        )

    # Step 4: Fall back to simple heuristics
    return _rule_based_route(query, complexity_signals)


async def _llm_route(
    query: str,
    patient_context: Optional[PatientContext],
    llm_client: LLMClientProtocol,
    router_model: str,
    complexity_signals: list[str],
) -> RoutingDecision:
    """Use LLM for nuanced routing decision."""
    
    # Build prompt
    patient_info = ""
    if patient_context:
        patient_info = f"""
Patient Context:
- Age: {patient_context.age or 'Unknown'}
- Sex: {patient_context.sex or 'Unknown'}
- Comorbidities: {', '.join(patient_context.comorbidities) or 'None listed'}
- Current Medications: {', '.join(patient_context.current_medications) or 'None listed'}
- Failed Treatments: {', '.join(patient_context.failed_treatments) or 'None listed'}
- Allergies: {', '.join(patient_context.allergies) or 'None listed'}
- Constraints: {', '.join(patient_context.constraints) or 'None listed'}
"""

    user_prompt = f"""Analyze this clinical query and determine the appropriate conference mode.

Query: {query}

{patient_info}

Detected Complexity Signals: {complexity_signals or 'None'}

Respond with a JSON object containing "mode" and "rationale".
"""

    try:
        response = await llm_client.complete(
            model=router_model,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=200,
        )

        # Parse response
        content = response.content.strip()
        
        # Try to extract JSON from the response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        mode = ConferenceMode(result["mode"])
        config = MODE_AGENT_CONFIGS[mode]

        return RoutingDecision(
            mode=mode,
            active_agents=config["agents"],
            activate_scout=config["scout"],
            risk_profile=config["risk_profile"],
            routing_rationale=result.get("rationale", ""),
            complexity_signals_detected=complexity_signals,
            estimated_rounds=config["rounds"],
        )

    except Exception as e:
        logger.warning(f"LLM routing failed: {e}, falling back to rule-based")
        return _rule_based_route(query, complexity_signals)


def _rule_based_route(query: str, complexity_signals: list[str]) -> RoutingDecision:
    """Simple rule-based fallback routing."""
    
    query_lower = query.lower()

    # Check for diagnostic keywords
    diagnostic_keywords = ["diagnosis", "what is", "what could", "differential", "workup"]
    if any(kw in query_lower for kw in diagnostic_keywords):
        mode = ConferenceMode.DIAGNOSTIC_PUZZLE
        config = MODE_AGENT_CONFIGS[mode]
        return RoutingDecision(
            mode=mode,
            active_agents=config["agents"],
            activate_scout=config["scout"],
            risk_profile=config["risk_profile"],
            routing_rationale="Query appears to be diagnostic in nature",
            complexity_signals_detected=complexity_signals,
            estimated_rounds=config["rounds"],
        )

    # Check for simple guideline queries
    simple_keywords = ["first-line", "dosing", "dose", "contraindications", "side effects"]
    if any(kw in query_lower for kw in simple_keywords) and not complexity_signals:
        mode = ConferenceMode.STANDARD_CARE
        config = MODE_AGENT_CONFIGS[mode]
        return RoutingDecision(
            mode=mode,
            active_agents=config["agents"],
            activate_scout=config["scout"],
            risk_profile=config["risk_profile"],
            routing_rationale="Simple guideline query with no complexity signals",
            complexity_signals_detected=complexity_signals,
            estimated_rounds=config["rounds"],
        )

    # Default to COMPLEX_DILEMMA for safety
    mode = ConferenceMode.COMPLEX_DILEMMA
    config = MODE_AGENT_CONFIGS[mode]
    return RoutingDecision(
        mode=mode,
        active_agents=config["agents"],
        activate_scout=config["scout"],
        risk_profile=config["risk_profile"],
        routing_rationale="Defaulting to full conference for thorough analysis",
        complexity_signals_detected=complexity_signals,
        estimated_rounds=config["rounds"],
    )

