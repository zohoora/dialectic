"""
Tests for the Grounding Engine.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.grounding.engine import GroundingEngine, VerificationResult
from src.grounding.pubmed_client import PubMedClient
from src.grounding.citation_parser import CitationParser
from src.models.grounding import (
    PubMedArticle,
    PubMedSearchResult,
    RawCitation,
    VerifiedCitation,
)


def create_mock_pubmed() -> PubMedClient:
    """Create a mock PubMed client."""
    client = MagicMock(spec=PubMedClient)
    return client


def create_mock_article(
    pmid: str = "12345678",
    title: str = "Test Article",
    authors: list = None,
    year: int = 2024,
) -> PubMedArticle:
    """Create a mock PubMed article."""
    return PubMedArticle(
        pmid=pmid,
        title=title,
        authors=authors or ["Smith J", "Jones M"],
        year=year,
        journal="Test Journal",
        doi="10.1000/test",
    )


class TestGroundingEngineInit:
    """Tests for engine initialization."""
    
    def test_default_init(self):
        """Test default initialization creates clients."""
        engine = GroundingEngine()
        assert engine.pubmed is not None
        assert engine.parser is not None
    
    def test_custom_clients(self):
        """Test initialization with custom clients."""
        mock_pubmed = create_mock_pubmed()
        mock_parser = MagicMock(spec=CitationParser)
        
        engine = GroundingEngine(
            pubmed_client=mock_pubmed,
            citation_parser=mock_parser,
        )
        
        assert engine.pubmed is mock_pubmed
        assert engine.parser is mock_parser


class TestGroundingEngineVerifyPMID:
    """Tests for PMID verification."""
    
    @pytest.mark.asyncio
    async def test_verify_pmid_found(self):
        """Test verifying a citation with PMID."""
        mock_pubmed = create_mock_pubmed()
        mock_pubmed.fetch_by_pmid = AsyncMock(return_value=create_mock_article())
        
        engine = GroundingEngine(pubmed_client=mock_pubmed)
        
        citation = RawCitation(
            original_text="PMID: 12345678",
            citation_type="pmid",
            extracted_pmid="12345678",
        )
        
        report = await engine.verify_citations([citation])
        
        assert len(report.citations_verified) == 1
        assert len(report.citations_failed) == 0
        assert report.citations_verified[0].pmid == "12345678"
        assert report.citations_verified[0].match_type == "pmid_direct"
    
    @pytest.mark.asyncio
    async def test_verify_pmid_not_found(self):
        """Test verifying a PMID that doesn't exist."""
        mock_pubmed = create_mock_pubmed()
        mock_pubmed.fetch_by_pmid = AsyncMock(return_value=None)
        mock_pubmed.search_by_author_year = AsyncMock(
            return_value=PubMedSearchResult(found=False, pmids=[], total_count=0)
        )
        mock_pubmed.fuzzy_search = AsyncMock(
            return_value=PubMedSearchResult(found=False, pmids=[], total_count=0)
        )
        
        engine = GroundingEngine(pubmed_client=mock_pubmed)
        
        citation = RawCitation(
            original_text="PMID: 99999999",
            citation_type="pmid",
            extracted_pmid="99999999",
        )
        
        report = await engine.verify_citations([citation])
        
        assert len(report.citations_verified) == 0
        assert len(report.citations_failed) == 1
        assert report.citations_failed[0].reason == "not_found"


class TestGroundingEngineVerifyAuthorYear:
    """Tests for author-year verification."""
    
    @pytest.mark.asyncio
    async def test_verify_author_year_found(self):
        """Test verifying author-year citation."""
        mock_pubmed = create_mock_pubmed()
        mock_pubmed.search_by_author_year = AsyncMock(
            return_value=PubMedSearchResult(
                found=True,
                pmids=["12345678"],
                total_count=1,
            )
        )
        mock_pubmed.fetch_multiple = AsyncMock(
            return_value=[create_mock_article(authors=["Smith JD"])]
        )
        
        engine = GroundingEngine(pubmed_client=mock_pubmed)
        
        citation = RawCitation(
            original_text="Smith et al. (2024)",
            citation_type="author_year",
            extracted_author="Smith",
            extracted_year=2024,
        )
        
        report = await engine.verify_citations([citation])
        
        assert len(report.citations_verified) == 1
        assert report.citations_verified[0].pmid == "12345678"
    
    @pytest.mark.asyncio
    async def test_verify_author_year_wrong_year(self):
        """Test author-year with year mismatch returns closest match."""
        mock_pubmed = create_mock_pubmed()
        mock_pubmed.search_by_author_year = AsyncMock(
            return_value=PubMedSearchResult(
                found=True,
                pmids=["12345678"],
                total_count=1,
            )
        )
        # Article is from 2023, but citation says 2024
        mock_pubmed.fetch_multiple = AsyncMock(
            return_value=[create_mock_article(year=2023, authors=["Smith JD"])]
        )
        mock_pubmed.fuzzy_search = AsyncMock(
            return_value=PubMedSearchResult(found=False, pmids=[], total_count=0)
        )
        
        engine = GroundingEngine(pubmed_client=mock_pubmed)
        
        citation = RawCitation(
            original_text="Smith et al. (2024)",
            citation_type="author_year",
            extracted_author="Smith",
            extracted_year=2024,
        )
        
        report = await engine.verify_citations([citation])
        
        # Should still verify with year off by 1 (confidence 0.75)
        assert len(report.citations_verified) == 1


class TestGroundingEngineVerifyText:
    """Tests for verifying text with embedded citations."""
    
    @pytest.mark.asyncio
    async def test_verify_text_with_citations(self):
        """Test extracting and verifying citations from text."""
        mock_pubmed = create_mock_pubmed()
        mock_pubmed.fetch_by_pmid = AsyncMock(return_value=create_mock_article())
        
        engine = GroundingEngine(pubmed_client=mock_pubmed)
        
        text = "According to the study (PMID: 12345678), ketamine is effective."
        report = await engine.verify_text(text)
        
        assert len(report.citations_verified) == 1
        assert report.hallucination_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_verify_text_no_citations(self):
        """Test verifying text with no citations."""
        engine = GroundingEngine()
        
        text = "This text has no citations at all."
        report = await engine.verify_text(text)
        
        assert report.total_citations == 0
        assert report.hallucination_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_verify_multiple_texts(self):
        """Test verifying citations across multiple texts."""
        mock_pubmed = create_mock_pubmed()
        mock_pubmed.fetch_by_pmid = AsyncMock(return_value=create_mock_article())
        
        engine = GroundingEngine(pubmed_client=mock_pubmed)
        
        texts = [
            "Study 1 showed (PMID: 12345678)",
            "Study 2 confirmed (PMID: 12345678)",  # Same PMID, should dedupe
        ]
        
        report = await engine.verify_multiple_texts(texts)
        
        # Should only have one citation (deduplicated)
        assert report.total_citations == 1


class TestGroundingEngineMatchConfidence:
    """Tests for match confidence computation."""
    
    def test_exact_match_confidence(self):
        """Test confidence for exact match."""
        engine = GroundingEngine()
        
        citation = RawCitation(
            original_text="Smith (2024)",
            citation_type="author_year",
            extracted_author="Smith",
            extracted_year=2024,
        )
        
        article = create_mock_article(year=2024, authors=["Smith JD"])
        
        confidence = engine._compute_match_confidence(citation, article)
        
        # Both year and author match exactly
        assert confidence == 1.0
    
    def test_partial_match_confidence(self):
        """Test confidence for partial match (year off by 1)."""
        engine = GroundingEngine()
        
        citation = RawCitation(
            original_text="Smith (2024)",
            citation_type="author_year",
            extracted_author="Smith",
            extracted_year=2024,
        )
        
        article = create_mock_article(year=2023, authors=["Smith JD"])
        
        confidence = engine._compute_match_confidence(citation, article)
        
        # Author matches, year off by 1
        assert 0.5 < confidence < 1.0
    
    def test_no_match_confidence(self):
        """Test confidence when nothing matches."""
        engine = GroundingEngine()
        
        citation = RawCitation(
            original_text="Smith (2024)",
            citation_type="author_year",
            extracted_author="Smith",
            extracted_year=2024,
        )
        
        article = create_mock_article(year=2020, authors=["Jones B"])
        
        confidence = engine._compute_match_confidence(citation, article)
        
        # Neither year nor author matches
        assert confidence == 0.0


class TestVerificationResult:
    """Tests for VerificationResult class."""
    
    def test_verified_result(self):
        """Test creating a verified result."""
        citation = VerifiedCitation(
            original_text="Test",
            pmid="12345678",
            title="Test Article",
            year=2024,
            match_type="exact",
        )
        
        result = VerificationResult(verified=True, citation=citation)
        
        assert result.verified is True
        assert result.citation is not None
        assert result.failure is None
    
    def test_failed_result(self):
        """Test creating a failed result."""
        from src.models.grounding import FailedCitation
        
        failure = FailedCitation(
            original_text="Fake (2099)",
            reason="not_found",
        )
        
        result = VerificationResult(verified=False, failure=failure)
        
        assert result.verified is False
        assert result.failure is not None
        assert result.citation is None


class TestGroundingReportProperties:
    """Tests for grounding report computed properties."""
    
    @pytest.mark.asyncio
    async def test_hallucination_rate(self):
        """Test hallucination rate calculation."""
        mock_pubmed = create_mock_pubmed()
        
        # First PMID exists, second doesn't
        async def mock_fetch(pmid):
            if pmid == "11111111":
                return create_mock_article(pmid="11111111")
            return None
        
        mock_pubmed.fetch_by_pmid = mock_fetch
        mock_pubmed.search_by_author_year = AsyncMock(
            return_value=PubMedSearchResult(found=False, pmids=[], total_count=0)
        )
        mock_pubmed.fuzzy_search = AsyncMock(
            return_value=PubMedSearchResult(found=False, pmids=[], total_count=0)
        )
        
        engine = GroundingEngine(pubmed_client=mock_pubmed)
        
        citations = [
            RawCitation(
                original_text="PMID: 11111111",
                citation_type="pmid",
                extracted_pmid="11111111",
            ),
            RawCitation(
                original_text="PMID: 99999999",
                citation_type="pmid",
                extracted_pmid="99999999",
            ),
        ]
        
        report = await engine.verify_citations(citations)
        
        assert report.total_citations == 2
        assert report.hallucination_rate == 0.5  # 1 of 2 failed
        assert report.has_failures is True

