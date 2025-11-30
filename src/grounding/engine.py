"""
Grounding Engine for citation verification.

Orchestrates the verification of citations using PubMed and other sources.
"""

import logging
from typing import Optional

from src.grounding.citation_parser import CitationParser
from src.grounding.pubmed_client import PubMedClient
from src.models.grounding import (
    FailedCitation,
    GroundingReport,
    RawCitation,
    VerifiedCitation,
)


logger = logging.getLogger(__name__)


class GroundingEngine:
    """
    Orchestrates citation verification across multiple sources.
    
    Currently supports:
    - PubMed (primary source for biomedical literature)
    
    Future sources could include:
    - Clinical guidelines databases
    - Drug databases (DrugBank, RxNorm)
    """
    
    def __init__(
        self, 
        pubmed_client: Optional[PubMedClient] = None,
        citation_parser: Optional[CitationParser] = None,
    ):
        """
        Initialize the grounding engine.
        
        Args:
            pubmed_client: PubMed client instance (creates default if not provided)
            citation_parser: Citation parser instance (creates default if not provided)
        """
        self.pubmed = pubmed_client or PubMedClient()
        self.parser = citation_parser or CitationParser()
    
    async def verify_text(self, text: str) -> GroundingReport:
        """
        Extract and verify all citations from a text.
        
        Args:
            text: Text containing potential citations
            
        Returns:
            GroundingReport with verification results
        """
        citations = self.parser.extract_citations(text)
        return await self.verify_citations(citations)
    
    async def verify_multiple_texts(self, texts: list[str]) -> GroundingReport:
        """
        Extract and verify citations from multiple texts.
        
        Deduplicates citations across texts.
        
        Args:
            texts: List of texts to check
            
        Returns:
            Combined GroundingReport
        """
        citations = self.parser.extract_citations_from_multiple(texts)
        return await self.verify_citations(citations)
    
    async def verify_citations(
        self, 
        citations: list[RawCitation]
    ) -> GroundingReport:
        """
        Verify a list of raw citations.
        
        Args:
            citations: List of RawCitation objects to verify
            
        Returns:
            GroundingReport with verification results
        """
        verified = []
        failed = []
        
        for citation in citations:
            result = await self._verify_single_citation(citation)
            if result.verified:
                verified.append(result.citation)
            else:
                failed.append(result.failure)
        
        return GroundingReport(
            citations_verified=verified,
            citations_failed=failed,
        )
    
    async def _verify_single_citation(
        self, 
        citation: RawCitation
    ) -> "VerificationResult":
        """
        Attempt to verify a single citation.
        
        Tries exact match first, then fuzzy search.
        
        Args:
            citation: Raw citation to verify
            
        Returns:
            VerificationResult with success or failure details
        """
        logger.debug(f"Verifying citation: {citation.original_text}")
        
        # Try PMID direct lookup if available
        if citation.extracted_pmid:
            result = await self._verify_by_pmid(citation)
            if result.verified:
                return result
        
        # Try author-year search
        if citation.extracted_author and citation.extracted_year:
            result = await self._verify_by_author_year(citation)
            if result.verified:
                return result
        
        # Try fuzzy search as fallback
        result = await self._verify_by_fuzzy_search(citation)
        if result.verified:
            return result
        
        # Verification failed
        logger.warning(f"Citation not verified: {citation.original_text}")
        return VerificationResult(
            verified=False,
            failure=FailedCitation(
                original_text=citation.original_text,
                reason="not_found",
                search_query=self.parser.normalize_for_search(citation),
                closest_match=result.closest_match,
            ),
        )
    
    async def _verify_by_pmid(
        self, 
        citation: RawCitation
    ) -> "VerificationResult":
        """Verify citation by direct PMID lookup."""
        article = await self.pubmed.fetch_by_pmid(citation.extracted_pmid)
        
        if article:
            return VerificationResult(
                verified=True,
                citation=VerifiedCitation(
                    original_text=citation.original_text,
                    pmid=article.pmid,
                    title=article.title,
                    authors=article.authors,
                    year=article.year,
                    journal=article.journal,
                    doi=article.doi,
                    match_type="pmid_direct",
                    match_confidence=1.0,
                ),
            )
        
        return VerificationResult(verified=False)
    
    async def _verify_by_author_year(
        self, 
        citation: RawCitation
    ) -> "VerificationResult":
        """Verify citation by author and year search."""
        search_result = await self.pubmed.search_by_author_year(
            author=citation.extracted_author,
            year=citation.extracted_year,
        )
        
        if not search_result.found:
            return VerificationResult(verified=False)
        
        # Fetch the top result
        articles = await self.pubmed.fetch_multiple(search_result.pmids[:3])
        
        if not articles:
            return VerificationResult(verified=False)
        
        # Find best match
        best_match = self._find_best_match(citation, articles)
        
        if best_match and best_match[1] >= 0.7:  # Confidence threshold
            article, confidence = best_match
            return VerificationResult(
                verified=True,
                citation=VerifiedCitation(
                    original_text=citation.original_text,
                    pmid=article.pmid,
                    title=article.title,
                    authors=article.authors,
                    year=article.year,
                    journal=article.journal,
                    doi=article.doi,
                    match_type="exact" if confidence >= 0.9 else "fuzzy",
                    match_confidence=confidence,
                ),
            )
        
        # Return closest match even if below threshold
        if best_match:
            article, confidence = best_match
            return VerificationResult(
                verified=False,
                closest_match=VerifiedCitation(
                    original_text=citation.original_text,
                    pmid=article.pmid,
                    title=article.title,
                    authors=article.authors,
                    year=article.year,
                    journal=article.journal,
                    doi=article.doi,
                    match_type="fuzzy",
                    match_confidence=confidence,
                ),
            )
        
        return VerificationResult(verified=False)
    
    async def _verify_by_fuzzy_search(
        self, 
        citation: RawCitation
    ) -> "VerificationResult":
        """Verify citation using fuzzy search."""
        search_result = await self.pubmed.fuzzy_search(citation.original_text)
        
        if not search_result.found:
            return VerificationResult(verified=False)
        
        # Fetch top results
        articles = await self.pubmed.fetch_multiple(search_result.pmids[:5])
        
        if not articles:
            return VerificationResult(verified=False)
        
        # Find best match
        best_match = self._find_best_match(citation, articles)
        
        if best_match and best_match[1] >= 0.6:  # Lower threshold for fuzzy
            article, confidence = best_match
            return VerificationResult(
                verified=True,
                citation=VerifiedCitation(
                    original_text=citation.original_text,
                    pmid=article.pmid,
                    title=article.title,
                    authors=article.authors,
                    year=article.year,
                    journal=article.journal,
                    doi=article.doi,
                    match_type="fuzzy",
                    match_confidence=confidence,
                ),
            )
        
        # Return closest match
        if best_match:
            article, confidence = best_match
            return VerificationResult(
                verified=False,
                closest_match=VerifiedCitation(
                    original_text=citation.original_text,
                    pmid=article.pmid,
                    title=article.title,
                    authors=article.authors,
                    year=article.year,
                    journal=article.journal,
                    doi=article.doi,
                    match_type="fuzzy",
                    match_confidence=confidence,
                ),
            )
        
        return VerificationResult(verified=False)
    
    def _find_best_match(
        self, 
        citation: RawCitation, 
        articles: list
    ) -> Optional[tuple]:
        """
        Find the best matching article for a citation.
        
        Args:
            citation: The citation to match
            articles: List of PubMedArticle candidates
            
        Returns:
            Tuple of (article, confidence) or None
        """
        if not articles:
            return None
        
        best_article = None
        best_confidence = 0.0
        
        for article in articles:
            confidence = self._compute_match_confidence(citation, article)
            if confidence > best_confidence:
                best_confidence = confidence
                best_article = article
        
        return (best_article, best_confidence) if best_article else None
    
    def _compute_match_confidence(
        self, 
        citation: RawCitation, 
        article
    ) -> float:
        """
        Compute confidence score for a citation-article match.
        
        Args:
            citation: The citation
            article: PubMedArticle to compare
            
        Returns:
            Confidence score 0.0 to 1.0
        """
        score = 0.0
        factors = 0
        
        # Year match (exact = 1.0, off by 1 = 0.5)
        if citation.extracted_year:
            factors += 1
            year_diff = abs(citation.extracted_year - article.year)
            if year_diff == 0:
                score += 1.0
            elif year_diff == 1:
                score += 0.5
        
        # Author match
        if citation.extracted_author and article.authors:
            factors += 1
            author_lower = citation.extracted_author.lower()
            # Check if author name appears in any of the article's authors
            for article_author in article.authors:
                if author_lower in article_author.lower():
                    score += 1.0
                    break
        
        # PMID match (exact)
        if citation.extracted_pmid:
            factors += 1
            if citation.extracted_pmid == article.pmid:
                score += 1.0
        
        # DOI match (exact)
        if citation.extracted_doi and article.doi:
            factors += 1
            if citation.extracted_doi.lower() == article.doi.lower():
                score += 1.0
        
        # If no specific factors matched, give a base score
        if factors == 0:
            return 0.3
        
        return score / factors


class VerificationResult:
    """Result of attempting to verify a single citation."""
    
    def __init__(
        self,
        verified: bool,
        citation: Optional[VerifiedCitation] = None,
        failure: Optional[FailedCitation] = None,
        closest_match: Optional[VerifiedCitation] = None,
    ):
        self.verified = verified
        self.citation = citation
        self.failure = failure
        self.closest_match = closest_match

