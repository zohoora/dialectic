"""
Data models for the Grounding Layer.

These models handle citation verification and tracking of hallucinated
vs verified references in agent responses.
"""

from typing import Optional

from pydantic import BaseModel, Field


class PubMedArticle(BaseModel):
    """Article details from PubMed."""
    
    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Article title")
    authors: list[str] = Field(default_factory=list, description="List of authors")
    year: int = Field(..., description="Publication year")
    journal: str = Field(default="", description="Journal name")
    doi: Optional[str] = Field(default=None, description="DOI if available")
    abstract: str = Field(default="", description="Article abstract")


class RawCitation(BaseModel):
    """A raw citation extracted from text before verification."""
    
    original_text: str = Field(..., description="Original citation text as found")
    citation_type: str = Field(
        default="unknown",
        description="Type: 'pmid', 'doi', 'author_year', 'unknown'"
    )
    extracted_pmid: Optional[str] = Field(default=None, description="PMID if directly mentioned")
    extracted_doi: Optional[str] = Field(default=None, description="DOI if directly mentioned")
    extracted_author: Optional[str] = Field(default=None, description="First author if parsed")
    extracted_year: Optional[int] = Field(default=None, description="Year if parsed")


class VerifiedCitation(BaseModel):
    """A citation that was verified to exist in PubMed."""
    
    original_text: str = Field(..., description="Original citation text from agent")
    pmid: str = Field(..., description="Verified PubMed ID")
    title: str = Field(..., description="Article title")
    authors: list[str] = Field(default_factory=list, description="Author list")
    year: int = Field(..., description="Publication year")
    journal: str = Field(default="", description="Journal name")
    doi: Optional[str] = Field(default=None, description="DOI if available")
    match_type: str = Field(
        default="exact",
        description="How it matched: 'exact', 'fuzzy', 'pmid_direct'"
    )
    match_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence of the match"
    )


class FailedCitation(BaseModel):
    """A citation that could not be verified."""
    
    original_text: str = Field(..., description="Original citation text")
    reason: str = Field(
        ...,
        description="Why verification failed: 'not_found', 'year_mismatch', 'author_mismatch'"
    )
    search_query: str = Field(default="", description="Query used for search")
    closest_match: Optional[VerifiedCitation] = Field(
        default=None,
        description="Closest matching article if found"
    )
    was_self_corrected: bool = Field(
        default=False,
        description="Whether conference caught this before output"
    )


class GroundingReport(BaseModel):
    """Complete grounding report for a conference or round."""
    
    citations_verified: list[VerifiedCitation] = Field(
        default_factory=list,
        description="Successfully verified citations"
    )
    citations_failed: list[FailedCitation] = Field(
        default_factory=list,
        description="Citations that failed verification"
    )
    
    @property
    def total_citations(self) -> int:
        """Total number of citations checked."""
        return len(self.citations_verified) + len(self.citations_failed)
    
    @property
    def hallucination_rate(self) -> float:
        """Fraction of citations that failed verification."""
        if self.total_citations == 0:
            return 0.0
        return len(self.citations_failed) / self.total_citations
    
    @property
    def has_failures(self) -> bool:
        """Whether any citations failed verification."""
        return len(self.citations_failed) > 0
    
    self_corrected: bool = Field(
        default=False,
        description="Whether conference caught and corrected hallucinations"
    )
    
    def merge(self, other: "GroundingReport") -> "GroundingReport":
        """Merge another grounding report into this one."""
        return GroundingReport(
            citations_verified=self.citations_verified + other.citations_verified,
            citations_failed=self.citations_failed + other.citations_failed,
            self_corrected=self.self_corrected or other.self_corrected,
        )


class PubMedSearchResult(BaseModel):
    """Result from a PubMed search query."""
    
    found: bool = Field(..., description="Whether any results were found")
    pmids: list[str] = Field(default_factory=list, description="List of matching PMIDs")
    total_count: int = Field(default=0, description="Total results in PubMed")
    query_used: str = Field(default="", description="The search query used")

