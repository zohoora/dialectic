"""
AI Case Conference System - Enumerations

Centralized enum definitions for the v3 architecture.
"""

from enum import Enum


class ConferenceMode(str, Enum):
    """The routing mode determined by the Intelligent Router."""

    STANDARD_CARE = "STANDARD_CARE"  # Simple guideline check
    COMPLEX_DILEMMA = "COMPLEX_DILEMMA"  # Multi-factor decision
    NOVEL_RESEARCH = "NOVEL_RESEARCH"  # Experimental territory
    DIAGNOSTIC_PUZZLE = "DIAGNOSTIC_PUZZLE"  # Unclear diagnosis


class Lane(str, Enum):
    """The two reasoning lanes in v3 architecture."""

    CLINICAL = "A"  # Lane A: Safety, guidelines, evidence
    EXPLORATORY = "B"  # Lane B: Mechanism, novelty, theory


class EvidenceGrade(str, Enum):
    """Evidence quality grading for Scout findings."""

    META_ANALYSIS = "meta_analysis"  # Systematic review / Cochrane
    RCT_LARGE = "rct_large"  # RCT n > 100
    RCT_SMALL = "rct_small"  # RCT n < 100
    OBSERVATIONAL = "observational"  # Cohort, case-control
    PREPRINT = "preprint"  # Not peer-reviewed
    CASE_REPORT = "case_report"  # Single case
    CONFLICTING = "conflicting"  # Contradicts consensus
    EXPERT_OPINION = "expert_opinion"  # No primary data


class SpeculationStatus(str, Enum):
    """Lifecycle status of a speculation in the library."""

    UNVERIFIED = "UNVERIFIED"  # Initial state
    WATCHING = "WATCHING"  # On watch list
    EVIDENCE_FOUND = "EVIDENCE_FOUND"  # New evidence detected
    PARTIALLY_VALIDATED = "PARTIALLY_VALIDATED"  # Some support
    VALIDATED = "VALIDATED"  # Ready for Experience Library
    CONTRADICTED = "CONTRADICTED"  # Evidence against
    DEPRECATED = "DEPRECATED"  # Removed


class CitationStatus(str, Enum):
    """Status of a citation after grounding."""

    VERIFIED = "VERIFIED"
    NOT_FOUND = "NOT_FOUND"
    YEAR_MISMATCH = "YEAR_MISMATCH"
    AUTHOR_MISMATCH = "AUTHOR_MISMATCH"
    CONTENT_UNVERIFIED = "CONTENT_UNVERIFIED"  # Exists but claim not checked

