"""
AI Case Conference System - Scout Schemas

Models for live literature search and evidence grading.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.models.enums import EvidenceGrade


class ScoutCitation(BaseModel):
    """A single citation found by the Scout."""

    title: str
    authors: list[str] = Field(default_factory=list)
    journal: Optional[str] = None
    year: int
    pmid: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    evidence_grade: EvidenceGrade
    sample_size: Optional[int] = None
    is_preprint: bool = False
    source_url: Optional[str] = None

    # Scout's assessment
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.5)
    key_finding: str = Field(default="")  # One-sentence summary
    conflicts_with_consensus: bool = False


class ScoutReport(BaseModel):
    """Complete output from the Scout."""

    scout_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_keywords: list[str] = Field(default_factory=list)
    search_date: datetime = Field(default_factory=datetime.utcnow)
    date_range_months: int = 12

    # Categorized findings
    meta_analyses: list[ScoutCitation] = Field(default_factory=list)
    high_quality_rcts: list[ScoutCitation] = Field(default_factory=list)
    preliminary_evidence: list[ScoutCitation] = Field(default_factory=list)
    conflicting_evidence: list[ScoutCitation] = Field(default_factory=list)

    # Metadata
    total_results_found: int = 0
    results_after_filtering: int = 0
    is_empty: bool = False
    search_queries_used: list[str] = Field(default_factory=list)

    def to_context_block(self) -> str:
        """Format the Scout report for injection into agent context."""
        if self.is_empty:
            return """
# SCOUT REPORT: NO RECENT EVIDENCE FOUND

No publications matching the query were found in the last 12 months.
Recommendations will be based on established evidence only.
"""

        lines = ["# SCOUT REPORT: EMERGING EVIDENCE (Last 12 Months)\n"]

        if self.meta_analyses:
            lines.append("## Meta-Analyses / Systematic Reviews (HIGHEST WEIGHT)")
            lines.append(
                "These synthesize multiple studies. May significantly update priors.\n"
            )
            for c in self.meta_analyses:
                lines.append(f"* **{c.title}** ({c.year})")
                lines.append(f"  - Finding: {c.key_finding}")
                if c.pmid:
                    lines.append(f"  - PMID: {c.pmid}")
                lines.append("")

        if self.high_quality_rcts:
            lines.append("## Peer-Reviewed RCTs (HIGH WEIGHT)")
            lines.append("Can update priors if methodology is sound.\n")
            for c in self.high_quality_rcts:
                n_str = f" (n={c.sample_size})" if c.sample_size else ""
                lines.append(f"* **{c.title}**{n_str} ({c.year})")
                lines.append(f"  - Finding: {c.key_finding}")
                if c.pmid:
                    lines.append(f"  - PMID: {c.pmid}")
                lines.append("")

        if self.preliminary_evidence:
            lines.append("## Preliminary Evidence (SIGNALS ONLY)")
            lines.append("Treat as signals. Do NOT present as established fact.\n")
            for c in self.preliminary_evidence:
                preprint_flag = " [PREPRINT]" if c.is_preprint else ""
                lines.append(f"* **{c.title}**{preprint_flag} ({c.year})")
                lines.append(f"  - Finding: {c.key_finding}")
                lines.append("")

        if self.conflicting_evidence:
            lines.append("## Conflicting / Contested Evidence")
            lines.append(
                "Acknowledge the conflict. Do NOT auto-resolve in favor of recency.\n"
            )
            for c in self.conflicting_evidence:
                lines.append(f"* **{c.title}** ({c.year})")
                lines.append(f"  - Finding: {c.key_finding}")
                lines.append(f"  - **Conflict:** This contradicts established consensus.")
                lines.append("")

        lines.append("---")
        lines.append("**Instructions for agents:** Weight evidence according to grade.")
        lines.append("Recency does NOT equal reliability. A 2025 preprint with n=12")
        lines.append("should NOT override 20 years of replicated RCTs.")

        return "\n".join(lines)

