"""
AI Case Conference System - Speculation Library Schemas

Models for hypothesis tracking and validation.
"""

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.models.enums import EvidenceGrade, SpeculationStatus
from src.models.scout import ScoutCitation


class Speculation(BaseModel):
    """A hypothesis stored in the Speculation Library."""

    speculation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Origin
    origin_conference_id: str = ""
    origin_query: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # The hypothesis
    hypothesis: str
    mechanism: str = ""
    source_agent: str = "speculator"

    # Confidence and validation
    initial_confidence: Literal["low", "medium", "high"] = "low"
    validation_criteria: str = ""  # What would prove this
    evidence_needed: str = ""  # Specific study type needed

    # Watch list
    watch_keywords: list[str] = Field(default_factory=list)

    # Lifecycle
    status: SpeculationStatus = SpeculationStatus.UNVERIFIED
    last_checked: Optional[datetime] = None
    evidence_found: list[ScoutCitation] = Field(default_factory=list)

    # If validated
    promoted_to_experience_library: bool = False
    experience_library_id: Optional[str] = None


class WatchListTrigger(BaseModel):
    """Event when Scout finds evidence matching a speculation."""

    trigger_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    speculation_id: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    matching_citations: list[ScoutCitation] = Field(default_factory=list)
    match_quality: Literal["exact", "partial", "weak"] = "partial"
    requires_human_review: bool = True
    auto_action_taken: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validating a speculation against new evidence."""

    speculation_id: str
    validation_date: datetime = Field(default_factory=datetime.utcnow)

    new_evidence: list[ScoutCitation] = Field(default_factory=list)
    support_level: Literal[
        "confirms", "partially_supports", "inconclusive", "contradicts"
    ] = "inconclusive"
    evidence_quality: EvidenceGrade = EvidenceGrade.OBSERVATIONAL

    action: Literal[
        "promote_to_experience_library", "upgrade_status", "keep_watching", "deprecate"
    ] = "keep_watching"
    new_status: SpeculationStatus = SpeculationStatus.WATCHING
    requires_human_review: bool = True
    validation_notes: str = ""

