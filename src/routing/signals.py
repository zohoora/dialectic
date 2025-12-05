"""
Complexity Signal Detection - Deterministic triggers for routing decisions.

v3: Extended with topology detection for automatic deliberation structure selection.

These signals override LLM judgment when certain patterns are detected,
ensuring complex cases are never under-analyzed and optimal topologies are selected.
"""

import re
from typing import Optional, Tuple

from src.models.v2_schemas import PatientContext


# =============================================================================
# COMPLEXITY KEYWORDS
# =============================================================================

COMPLEXITY_KEYWORDS = [
    "failed",
    "resistant",
    "refractory",
    "experimental",
    "off-label",
    "novel",
    "unconventional",
    "complex",
    "multiple",
    "conflicting",
    "contraindicated",
    "allergy",
    "interaction",
    "intolerant",
    "non-responder",
    "treatment-resistant",
    "rare",
    "orphan",
    "paradoxical",
]

# =============================================================================
# ESCALATION PATTERNS (Regex)
# =============================================================================

ESCALATION_PATTERNS = [
    r"fail(ed|ure|ing)",
    r"resist(ant|ance)",
    r"refractor(y|iness)",
    r"not\s+respond(ing|ed)?",
    r"tried\s+everything",
    r"nothing\s+work(s|ed|ing)",
    r"what\s+else",
    r"alternative",
    r"last\s+resort",
    r"desperate",
    r"out\s+of\s+options",
    r"no\s+improvement",
    r"worsening",
    r"despite\s+treatment",
    r"contraindicated",
    r"can'?t\s+(take|tolerate|use)",
]

# =============================================================================
# NOVEL/RESEARCH PATTERNS
# =============================================================================

NOVEL_PATTERNS = [
    r"new\s+(treatment|therapy|approach)",
    r"latest\s+(research|evidence)",
    r"emerging",
    r"experimental",
    r"clinical\s+trial",
    r"off.?label",
    r"peptide",
    r"biologic",
    r"novel\s+mechanism",
    r"cutting.?edge",
]

# =============================================================================
# DIAGNOSTIC PUZZLE PATTERNS
# =============================================================================

DIAGNOSTIC_PATTERNS = [
    r"what\s+(could|might)\s+(cause|explain)",
    r"differential\s+diagnosis",
    r"unknown\s+etiology",
    r"atypical\s+presentation",
    r"unclear\s+diagnosis",
    r"rule\s+out",
    r"work.?up",
    r"constellation\s+of\s+symptoms",
    r"negative\s+(for|ANA|RF|anti-CCP)",
]


# =============================================================================
# TOPOLOGY SELECTION PATTERNS (v3)
# =============================================================================

# Binary comparison patterns → Oxford Debate
COMPARISON_PATTERNS = [
    r"\bvs\.?\b",                        # "A vs B"
    r"\bversus\b",                       # "A versus B"  
    r"\bor\b.{1,30}\?",                  # "X or Y?" (limited distance)
    r"which\s+(is|would\s+be)\s+better",
    r"compare",
    r"comparison",
    r"between\s+.{1,50}\s+and\s+",       # "between X and Y"
    r"prefer\s+.{1,30}\s+over",
    r"choose\s+.{1,30}\s+or",
    r"head.?to.?head",
    r"superiority",
    r"non.?inferior",
    r"(drug|treatment|therapy)\s+a\s+(vs?\.?|or)\s+(drug|treatment|therapy)\s+b",
]

# Authority-sensitive / contentious patterns → Delphi Method
CONTENTIOUS_PATTERNS = [
    r"controversial",
    r"conflicting\s+(guidelines|evidence|recommendations|opinions)",
    r"experts?\s+disagree",
    r"no\s+consensus",
    r"depends\s+on\s+who\s+you\s+ask",
    r"hotly\s+debated",
    r"divided\s+opinion",
    r"school\s+of\s+thought",
    r"some\s+say.{1,50}others\s+say",
    r"guideline\s+discordance",
    r"(european|american|british)\s+guidelines?\s+differ",
]

# High-stakes / safety-critical patterns → Red Team
HIGH_STAKES_PATTERNS = [
    r"\b(surgery|surgical|operation|operative)\b",
    r"irreversible",
    r"life.?threatening",
    r"high.?risk",
    r"experimental\s+(procedure|surgery|intervention)",
    r"chemo(therapy)?",
    r"\bradiation\b",
    r"transplant",
    r"off.?label\s+use",
    r"compassionate\s+use",
    r"last.?ditch",
    r"palliative.{1,30}(aggressive|experimental)",
    r"major\s+(surgery|procedure|intervention)",
    r"(could|might|may)\s+be\s+fatal",
    r"risk\s+of\s+death",
    r"permanent\s+(damage|disability|loss)",
]

# Assumption-heavy / needs-clarification patterns → Socratic Spiral
# (These overlap with DIAGNOSTIC_PATTERNS but focus on surfacing assumptions)
SOCRATIC_PATTERNS = [
    r"assuming",
    r"if\s+.{1,50}\s+then",
    r"depends\s+on",
    r"what\s+if",
    r"unclear\s+whether",
    r"need\s+to\s+know",
    r"more\s+information",
    r"missing\s+(data|information|context)",
    r"key\s+question",
    r"fundamental\s+question",
    r"underlying\s+cause",
    r"root\s+cause",
]


def detect_complexity_signals(
    query: str,
    patient_context: Optional[PatientContext] = None,
) -> list[str]:
    """
    Detect hard-coded complexity signals that influence routing.
    
    Returns list of detected signals. Used by the Router to determine
    if automatic escalation is warranted.
    
    Args:
        query: The raw query text
        patient_context: Optional patient information
        
    Returns:
        List of detected signal strings (e.g., "keyword:failed", "pattern:refractory")
    """
    signals = []
    query_lower = query.lower()

    # Keyword detection
    for keyword in COMPLEXITY_KEYWORDS:
        if keyword in query_lower:
            signals.append(f"keyword:{keyword}")

    # Pattern detection - escalation
    for pattern in ESCALATION_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            signals.append(f"escalation:{pattern}")

    # Pattern detection - novel/research
    for pattern in NOVEL_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            signals.append(f"novel:{pattern}")

    # Pattern detection - diagnostic puzzle
    for pattern in DIAGNOSTIC_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            signals.append(f"diagnostic:{pattern}")

    # Patient context signals
    if patient_context:
        if len(patient_context.comorbidities) > 2:
            signals.append(f"comorbidities:{len(patient_context.comorbidities)}")

        if len(patient_context.failed_treatments) > 0:
            signals.append(
                f"failed_treatments:{len(patient_context.failed_treatments)}"
            )

        if len(patient_context.current_medications) > 5:
            signals.append(
                f"polypharmacy:{len(patient_context.current_medications)}"
            )

        if patient_context.allergies:
            signals.append(f"allergies:{len(patient_context.allergies)}")

        if patient_context.constraints:
            signals.append(f"constraints:{len(patient_context.constraints)}")

    return signals


def classify_signals(signals: list[str]) -> dict[str, int]:
    """
    Classify signals by type and count them.
    
    Args:
        signals: List of signal strings
        
    Returns:
        Dict with counts per signal type
    """
    counts = {
        "escalation": 0,
        "novel": 0,
        "diagnostic": 0,
        "keyword": 0,
        "patient": 0,
        # v3: topology signals
        "comparison": 0,
        "contentious": 0,
        "high_stakes": 0,
        "socratic": 0,
    }

    for signal in signals:
        if signal.startswith("escalation:"):
            counts["escalation"] += 1
        elif signal.startswith("novel:"):
            counts["novel"] += 1
        elif signal.startswith("diagnostic:"):
            counts["diagnostic"] += 1
        elif signal.startswith("keyword:"):
            counts["keyword"] += 1
        elif signal.startswith("comparison:"):
            counts["comparison"] += 1
        elif signal.startswith("contentious:"):
            counts["contentious"] += 1
        elif signal.startswith("high_stakes:"):
            counts["high_stakes"] += 1
        elif signal.startswith("socratic:"):
            counts["socratic"] += 1
        else:
            counts["patient"] += 1

    return counts


# =============================================================================
# TOPOLOGY DETECTION (v3)
# =============================================================================


def detect_topology_signals(query: str) -> Tuple[list[str], str]:
    """
    Detect signals that suggest a specific deliberation topology.
    
    Returns:
        Tuple of (list of detected signals, recommended topology name)
        
    Topology recommendations:
        - "oxford_debate": Binary comparisons, A vs B
        - "delphi_method": Contentious topics, reduce anchoring bias
        - "red_team_blue_team": High-stakes, safety-critical decisions
        - "socratic_spiral": Diagnostic puzzles, assumption surfacing
        - "free_discussion": Default for general exploration
    """
    query_lower = query.lower()
    signals = []
    
    # Check comparison patterns → Oxford Debate
    for pattern in COMPARISON_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            signals.append(f"comparison:{pattern}")
    
    # Check contentious patterns → Delphi Method
    for pattern in CONTENTIOUS_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            signals.append(f"contentious:{pattern}")
    
    # Check high-stakes patterns → Red Team
    for pattern in HIGH_STAKES_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            signals.append(f"high_stakes:{pattern}")
    
    # Check socratic patterns → Socratic Spiral
    for pattern in SOCRATIC_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            signals.append(f"socratic:{pattern}")
    
    # Determine recommended topology based on signal counts
    comparison_count = len([s for s in signals if s.startswith("comparison:")])
    contentious_count = len([s for s in signals if s.startswith("contentious:")])
    high_stakes_count = len([s for s in signals if s.startswith("high_stakes:")])
    socratic_count = len([s for s in signals if s.startswith("socratic:")])
    
    # Priority order: High stakes > Comparison > Contentious > Socratic > Free
    # (Safety-critical trumps all)
    if high_stakes_count >= 2:
        return signals, "red_team_blue_team"
    
    if comparison_count >= 1:
        return signals, "oxford_debate"
    
    if contentious_count >= 1:
        return signals, "delphi_method"
    
    if socratic_count >= 2:
        return signals, "socratic_spiral"
    
    return signals, "free_discussion"


def get_topology_rationale(topology: str, signals: list[str]) -> str:
    """Generate a human-readable rationale for topology selection."""
    
    rationales = {
        "oxford_debate": "Binary comparison detected - structured debate will clarify trade-offs",
        "delphi_method": "Contentious topic detected - anonymous deliberation reduces anchoring bias",
        "red_team_blue_team": "High-stakes decision detected - adversarial review ensures safety",
        "socratic_spiral": "Unclear assumptions detected - question-first approach surfaces hidden factors",
        "free_discussion": "General deliberation - open discussion format",
    }
    
    base = rationales.get(topology, "Default topology selected")
    
    if signals:
        trigger_types = set(s.split(":")[0] for s in signals[:3])
        return f"{base} (triggers: {', '.join(trigger_types)})"
    
    return base

