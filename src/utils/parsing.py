"""
Shared text parsing utilities for LLM response extraction.

These utilities are used across arbitrator implementations to parse
structured content from LLM responses.
"""

import re
from typing import Optional


def extract_section(
    content: str,
    headers: list[str],
    default: str = "",
) -> str:
    """
    Extract a section of content by header.
    
    Searches for markdown headers (##, ###) or bold text (**Header**) 
    and extracts the content until the next section.
    
    Args:
        content: Full content to search
        headers: Possible section headers to look for (in priority order)
        default: Default value if not found
    
    Returns:
        Section content or default
    """
    for header in headers:
        # Escape special regex characters in header
        escaped_header = re.escape(header)
        
        patterns = [
            # ### Header format (common in markdown)
            rf"###\s*{escaped_header}[^\n]*\n(.*?)(?=\n###|\n##|\n---|\Z)",
            # ## Header format
            rf"##\s*{escaped_header}[^\n]*\n(.*?)(?=\n##|\n#|\n---|\Z)",
            # **Header** bold format
            rf"\*\*{escaped_header}\*\*[:\s]*\n?(.*?)(?=\n\*\*|\n---|\Z)",
            # Plain Header: format (with colon)
            rf"{escaped_header}[:\s]*\n(.*?)(?=\n\n|\Z)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    return default


def extract_field(
    content: str,
    field_names: list[str],
) -> Optional[str]:
    """
    Extract a single field value from content.
    
    Looks for patterns like:
    - **Field**: Value
    - Field: Value
    - - Field: Value
    
    Args:
        content: Content to search
        field_names: Possible field names to look for (in priority order)
    
    Returns:
        Field value or None if not found
    """
    for field in field_names:
        # Escape special regex characters
        escaped_field = re.escape(field)
        
        patterns = [
            # **Field**: Value (multiline)
            rf"\*\*{escaped_field}\*\*[:\s]*(.+?)(?:\n\n|\n\*\*|\Z)",
            # Field: Value (multiline)
            rf"{escaped_field}[:\s]*(.+?)(?:\n\n|\n\*\*|\Z)",
            # - Field: Value (single line, list item)
            rf"-\s*{escaped_field}[:\s]*(.+?)(?:\n|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
    
    return None


def parse_bullet_points(content: str) -> list[str]:
    """
    Parse bullet points from content.
    
    Recognizes various bullet formats:
    - Dash lists (- item)
    - Asterisk lists (* item)
    - Dot lists (• item, · item)
    - Numbered lists (1. item)
    
    Args:
        content: Content containing bullet points
    
    Returns:
        List of bullet point strings
    """
    if not content:
        return []
    
    points = []
    
    for line in content.split("\n"):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Match various bullet formats
        if line.startswith(("-", "*", "•", "·")):
            point = line.lstrip("-*•· ").strip()
            if point:
                points.append(point)
        elif re.match(r"^\d+\.", line):
            # Numbered list
            point = re.sub(r"^\d+\.\s*", "", line).strip()
            if point:
                points.append(point)
    
    return points


def extract_confidence(content: str) -> float:
    """
    Extract confidence level from content.
    
    Looks for explicit confidence markers and keywords.
    
    Args:
        content: Content to search
    
    Returns:
        Confidence float between 0 and 1 (default: 0.6)
    """
    content_lower = content.lower()
    
    # Look for explicit percentage
    percentage_match = re.search(r"confidence[:\s]*(\d+)%", content_lower)
    if percentage_match:
        return min(int(percentage_match.group(1)) / 100, 1.0)
    
    # Look for explicit confidence level section
    confidence_section = extract_section(
        content,
        ["Overall Confidence", "OVERALL CONFIDENCE", "Confidence Level"],
    )
    
    if confidence_section:
        return _parse_confidence_level(confidence_section)
    
    # Fall back to keyword search
    if "confidence level" in content_lower or "confidence:" in content_lower:
        return _parse_confidence_level(content_lower)
    
    return 0.6  # Default to moderate


def _parse_confidence_level(text: str) -> float:
    """
    Parse confidence level from text keywords.
    
    Args:
        text: Text containing confidence keywords
    
    Returns:
        Confidence float
    """
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


def get_role_display(role: str) -> str:
    """
    Get human-readable display name for an agent role.
    
    Args:
        role: Role identifier (e.g., "patient_voice")
    
    Returns:
        Display name (e.g., "Patient Voice")
    """
    displays = {
        "advocate": "Advocate",
        "skeptic": "Skeptic",
        "empiricist": "Empiricist",
        "mechanist": "Mechanist",
        "patient_voice": "Patient Voice",
        "pragmatist": "Pragmatist",
        "speculator": "Speculator",
        "arbitrator": "Arbitrator",
    }
    return displays.get(role, role.replace("_", " ").title())


def format_patient_context(patient_context) -> str:
    """
    Format patient context object into a readable string.
    
    Works with PatientContext objects or any object with similar attributes.
    
    Args:
        patient_context: Object with patient attributes (age, sex, etc.)
    
    Returns:
        Formatted string describing patient context
    """
    if not patient_context:
        return "No patient context provided."
    
    parts = []
    
    # Try to access common attributes
    pc = patient_context
    
    if hasattr(pc, "age") and pc.age:
        parts.append(f"Age: {pc.age}")
    if hasattr(pc, "sex") and pc.sex:
        parts.append(f"Sex: {pc.sex}")
    if hasattr(pc, "comorbidities") and pc.comorbidities:
        parts.append(f"Comorbidities: {', '.join(pc.comorbidities)}")
    if hasattr(pc, "failed_treatments") and pc.failed_treatments:
        parts.append(f"Failed treatments: {', '.join(pc.failed_treatments)}")
    if hasattr(pc, "current_medications") and pc.current_medications:
        parts.append(f"Current medications: {', '.join(pc.current_medications)}")
    if hasattr(pc, "allergies") and pc.allergies:
        parts.append(f"Allergies: {', '.join(pc.allergies)}")
    if hasattr(pc, "constraints") and pc.constraints:
        parts.append(f"Constraints: {', '.join(pc.constraints)}")
    if hasattr(pc, "relevant_history") and pc.relevant_history:
        parts.append(f"Relevant history: {pc.relevant_history}")
    
    return "\n".join(parts) if parts else "No patient context provided."

