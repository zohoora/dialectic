"""
Intelligent Router v3 - Determines conference configuration and topology.

Combines deterministic complexity signals with LLM-based analysis
to route queries to the appropriate conference mode AND deliberation topology.

v3 additions:
- Topology selection based on query patterns
- Oxford Debate for binary comparisons
- Delphi Method for contentious topics
- Red Team for high-stakes decisions
- Socratic Spiral for diagnostic puzzles
"""

import json
import logging
from typing import Optional

from src.models.conference import ConferenceTopology
from src.models.v2_schemas import (
    ConferenceMode,
    PatientContext,
    RoutingDecision,
)
from src.routing.signals import (
    classify_signals,
    detect_complexity_signals,
    detect_topology_signals,
    get_topology_rationale,
)
from src.utils.protocols import LLMClientProtocol


logger = logging.getLogger(__name__)


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
        "default_topology": ConferenceTopology.FREE_DISCUSSION,
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
        "default_topology": ConferenceTopology.FREE_DISCUSSION,
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
        "default_topology": ConferenceTopology.FREE_DISCUSSION,
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
        "default_topology": ConferenceTopology.SOCRATIC_SPIRAL,  # Default for diagnostic
    },
}

# =============================================================================
# TOPOLOGY CONFIGURATIONS (v3)
# =============================================================================

# Map string topology names to enum values
TOPOLOGY_NAME_MAP: dict[str, ConferenceTopology] = {
    "free_discussion": ConferenceTopology.FREE_DISCUSSION,
    "oxford_debate": ConferenceTopology.OXFORD_DEBATE,
    "delphi_method": ConferenceTopology.DELPHI_METHOD,
    "socratic_spiral": ConferenceTopology.SOCRATIC_SPIRAL,
    "red_team_blue_team": ConferenceTopology.RED_TEAM_BLUE_TEAM,
}


# =============================================================================
# ROUTER PROMPT (v3: includes topology selection)
# =============================================================================

ROUTER_SYSTEM_PROMPT = """You are the Conference Router v3. Your job is to analyze a clinical query and determine:
1. The appropriate conference MODE (complexity level)
2. The optimal deliberation TOPOLOGY (discussion structure)

You must output a JSON object with the following fields:
- mode: One of "STANDARD_CARE", "COMPLEX_DILEMMA", "NOVEL_RESEARCH", "DIAGNOSTIC_PUZZLE"
- topology: One of "free_discussion", "oxford_debate", "delphi_method", "socratic_spiral", "red_team_blue_team"
- rationale: Brief explanation of your mode choice (1-2 sentences)
- topology_rationale: Brief explanation of your topology choice (1 sentence)

## Mode Definitions

**STANDARD_CARE**: Straightforward guideline check with clear answers.
Examples: "First-line treatment for hypertension?", "Dosing for amoxicillin in adults"

**COMPLEX_DILEMMA**: Multiple factors complicate the decision.
Examples: Failed multiple treatments, drug interactions, conflicting guidelines

**NOVEL_RESEARCH**: Experimental, off-label, or cutting-edge approaches.
Examples: "Peptide therapy for CRPS", treatment-resistant cases

**DIAGNOSTIC_PUZZLE**: Diagnosis itself is uncertain.
Examples: "What could cause these symptoms?", atypical presentations

## Topology Definitions

**free_discussion**: Open multi-agent deliberation. Best for general exploration.
Use when: Standard cases, no special structure needed.

**oxford_debate**: Two agents argue opposing positions, third judges.
Use when: Binary comparisons ("A vs B"), head-to-head treatment decisions, clear pro/con questions.
Example triggers: "vs", "versus", "which is better", "compare"

**delphi_method**: Anonymous responses to reduce anchoring bias.
Use when: Contentious topics, conflicting guidelines, authority bias concern.
Example triggers: "controversial", "experts disagree", "no consensus"

**socratic_spiral**: First round is questions only, surfacing assumptions.
Use when: Diagnostic puzzles, unclear presentations, need to identify missing information.
Example triggers: "unclear", "what if", "depends on"

**red_team_blue_team**: Adversarial stress-testing of proposals.
Use when: High-stakes decisions, surgical procedures, experimental interventions, irreversible actions.
Example triggers: "surgery", "irreversible", "high-risk", "experimental procedure"

## Output Format

```json
{
    "mode": "COMPLEX_DILEMMA",
    "topology": "oxford_debate",
    "rationale": "Patient comparing two treatment options with different risk profiles.",
    "topology_rationale": "Binary comparison warrants structured debate format."
}
```

## Rules
- Err on the side of COMPLEX_DILEMMA if mode is uncertain.
- Default to "free_discussion" if no clear topology signal.
- High-stakes decisions should almost always use "red_team_blue_team".
- Diagnostic uncertainty should prefer "socratic_spiral".
"""


# =============================================================================
# MAIN ROUTING FUNCTION (v3: with topology)
# =============================================================================


async def route_query(
    query: str,
    patient_context: Optional[PatientContext] = None,
    llm_client: Optional[LLMClientProtocol] = None,
    router_model: str = "openai/gpt-4o",
    mode_override: Optional[str] = None,
    topology_override: Optional[str] = None,
) -> RoutingDecision:
    """
    Main routing function. Combines deterministic triggers with LLM judgment.
    Includes automatic topology selection.
    
    Args:
        query: The clinical question to route
        patient_context: Optional patient information
        llm_client: LLM client for nuanced routing (optional, falls back to rule-based)
        router_model: Model to use for LLM routing
        mode_override: Optional manual mode override (bypasses routing for mode)
        topology_override: Optional manual topology override (bypasses routing for topology)
        
    Returns:
        RoutingDecision with mode, topology, agents, and scout activation
    """
    # Handle topology override
    if topology_override:
        override_topology = TOPOLOGY_NAME_MAP.get(topology_override, ConferenceTopology.FREE_DISCUSSION)
        logger.info(f"Using topology override: {topology_override}")
    else:
        override_topology = None
    
    # Handle mode override
    if mode_override:
        try:
            override_mode = ConferenceMode(mode_override)
            config = MODE_AGENT_CONFIGS[override_mode]
            effective_topology = override_topology or config["default_topology"]
            
            logger.info(f"Using mode override: {mode_override}, topology: {effective_topology.value}")
            
            return RoutingDecision(
                mode=override_mode,
                active_agents=config["agents"],
                activate_scout=config["scout"],
                risk_profile=config["risk_profile"],
                routing_rationale=f"Manual mode override: {mode_override}",
                complexity_signals_detected=[],
                estimated_rounds=config["rounds"],
                topology=effective_topology,
                topology_rationale=f"Manual topology: {effective_topology.value}" if override_topology else "Default for mode",
                topology_signals_detected=[],
            )
        except ValueError:
            logger.warning(f"Invalid mode override: {mode_override}, falling back to routing")
    
    # Step 1: Check deterministic complexity signals
    complexity_signals = detect_complexity_signals(query, patient_context)
    signal_counts = classify_signals(complexity_signals)

    logger.debug(f"Detected {len(complexity_signals)} complexity signals")
    
    # Step 1b: Detect topology signals
    topology_signals, recommended_topology_name = detect_topology_signals(query)
    recommended_topology = TOPOLOGY_NAME_MAP.get(
        recommended_topology_name, 
        ConferenceTopology.FREE_DISCUSSION
    )
    topology_rationale = get_topology_rationale(recommended_topology_name, topology_signals)
    
    # Use override topology if provided, otherwise use detected
    effective_topology = override_topology or recommended_topology
    if override_topology:
        topology_rationale = f"Manual override: {override_topology}"
    
    logger.debug(f"Detected topology signals: {topology_signals}, effective topology: {effective_topology.value}")

    # Step 2: Check for automatic escalation based on signals
    
    # Auto-escalate to NOVEL_RESEARCH if treatment failure signals
    if signal_counts["escalation"] >= 2 or signal_counts["novel"] >= 2:
        mode = ConferenceMode.NOVEL_RESEARCH
        config = MODE_AGENT_CONFIGS[mode]
        
        # Use override if provided, else use detected, else red_team for high-stakes
        if not override_topology:
            if signal_counts.get("high_stakes", 0) >= 1:
                effective_topology = ConferenceTopology.RED_TEAM_BLUE_TEAM
                topology_rationale = "High-stakes novel research requires adversarial review"
        
        logger.info(f"Auto-escalating to NOVEL_RESEARCH due to signals: {complexity_signals}")
        
        return RoutingDecision(
            mode=mode,
            active_agents=config["agents"],
            activate_scout=config["scout"],
            risk_profile=config["risk_profile"],
            routing_rationale=f"Auto-escalated due to treatment failure/novel signals: {len(complexity_signals)} triggers detected",
            complexity_signals_detected=complexity_signals,
            estimated_rounds=config["rounds"],
            topology=effective_topology,
            topology_signals_detected=topology_signals,
            topology_rationale=topology_rationale,
        )

    # Auto-escalate to DIAGNOSTIC_PUZZLE if diagnostic uncertainty signals
    if signal_counts["diagnostic"] >= 2:
        mode = ConferenceMode.DIAGNOSTIC_PUZZLE
        config = MODE_AGENT_CONFIGS[mode]
        
        # Diagnostic puzzles default to socratic spiral (unless overridden)
        if not override_topology:
            effective_topology = ConferenceTopology.SOCRATIC_SPIRAL
            topology_rationale = "Diagnostic uncertainty - question-first approach surfaces hidden assumptions"
        
        logger.info(f"Auto-escalating to DIAGNOSTIC_PUZZLE due to signals: {complexity_signals}")
        
        return RoutingDecision(
            mode=mode,
            active_agents=config["agents"],
            activate_scout=config["scout"],
            risk_profile=config["risk_profile"],
            routing_rationale="Auto-escalated due to diagnostic uncertainty signals",
            complexity_signals_detected=complexity_signals,
            estimated_rounds=config["rounds"],
            topology=effective_topology,
            topology_signals_detected=topology_signals,
            topology_rationale=topology_rationale,
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
            topology=effective_topology,
            topology_signals_detected=topology_signals,
            topology_rationale=topology_rationale,
        )

    # Step 3: Use LLM for nuanced routing if available
    if llm_client:
        return await _llm_route(
            query=query,
            patient_context=patient_context,
            llm_client=llm_client,
            router_model=router_model,
            complexity_signals=complexity_signals,
            topology_signals=topology_signals,
            effective_topology=effective_topology,
            topology_rationale=topology_rationale,
        )

    # Step 4: Fall back to simple heuristics
    return _rule_based_route(query, complexity_signals, topology_signals, effective_topology, topology_rationale)


async def _llm_route(
    query: str,
    patient_context: Optional[PatientContext],
    llm_client: LLMClientProtocol,
    router_model: str,
    complexity_signals: list[str],
    topology_signals: list[str],
    effective_topology: ConferenceTopology,
    topology_rationale: str,
) -> RoutingDecision:
    """Use LLM for nuanced routing decision (includes topology)."""
    
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
Note: Topology has already been determined as {effective_topology.value}.

Query: {query}

{patient_info}

Detected Complexity Signals: {complexity_signals or 'None'}
Detected Topology Signals: {topology_signals or 'None'}

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
            max_tokens=300,
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
            topology=effective_topology,
            topology_signals_detected=topology_signals,
            topology_rationale=topology_rationale,
        )

    except Exception as e:
        logger.warning(f"LLM routing failed: {e}, falling back to rule-based")
        return _rule_based_route(query, complexity_signals, topology_signals, effective_topology, topology_rationale)


def _rule_based_route(
    query: str, 
    complexity_signals: list[str],
    topology_signals: list[str],
    effective_topology: ConferenceTopology,
    topology_rationale: str,
) -> RoutingDecision:
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
            topology=effective_topology,
            topology_signals_detected=topology_signals,
            topology_rationale=topology_rationale,
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
            topology=effective_topology,
            topology_signals_detected=topology_signals,
            topology_rationale=topology_rationale,
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
        topology=effective_topology,
        topology_signals_detected=topology_signals,
        topology_rationale=topology_rationale,
    )

