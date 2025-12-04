"""
Complexity Signal Detection - Deterministic triggers for routing decisions.

These signals override LLM judgment when certain patterns are detected,
ensuring complex cases are never under-analyzed.
"""

import re
from typing import Optional

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
        else:
            counts["patient"] += 1

    return counts

