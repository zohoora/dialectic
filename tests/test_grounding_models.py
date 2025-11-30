"""
Tests for grounding data models.
"""

import pytest
from src.models.grounding import (
    PubMedArticle,
    RawCitation,
    VerifiedCitation,
    FailedCitation,
    GroundingReport,
    PubMedSearchResult,
)


class TestPubMedArticle:
    """Tests for PubMedArticle model."""
    
    def test_create_article(self):
        """Test creating a PubMed article."""
        article = PubMedArticle(
            pmid="12345678",
            title="Test Article Title",
            authors=["Smith J", "Jones M"],
            year=2024,
            journal="Test Journal",
            doi="10.1000/test",
        )
        assert article.pmid == "12345678"
        assert article.title == "Test Article Title"
        assert len(article.authors) == 2
        assert article.year == 2024
        assert article.doi == "10.1000/test"
    
    def test_article_minimal(self):
        """Test article with minimal required fields."""
        article = PubMedArticle(
            pmid="99999999",
            title="Minimal Article",
            year=2020,
        )
        assert article.pmid == "99999999"
        assert article.authors == []
        assert article.journal == ""
        assert article.doi is None


class TestRawCitation:
    """Tests for RawCitation model."""
    
    def test_raw_citation_pmid(self):
        """Test citation with PMID."""
        citation = RawCitation(
            original_text="PMID: 12345678",
            citation_type="pmid",
            extracted_pmid="12345678",
        )
        assert citation.citation_type == "pmid"
        assert citation.extracted_pmid == "12345678"
    
    def test_raw_citation_author_year(self):
        """Test citation with author and year."""
        citation = RawCitation(
            original_text="Smith et al. 2024",
            citation_type="author_year",
            extracted_author="Smith",
            extracted_year=2024,
        )
        assert citation.citation_type == "author_year"
        assert citation.extracted_author == "Smith"
        assert citation.extracted_year == 2024


class TestVerifiedCitation:
    """Tests for VerifiedCitation model."""
    
    def test_verified_citation(self):
        """Test creating a verified citation."""
        citation = VerifiedCitation(
            original_text="Smith 2024",
            pmid="12345678",
            title="The Smith Study",
            authors=["Smith J", "Doe J"],
            year=2024,
            journal="Nature Medicine",
            match_type="exact",
            match_confidence=1.0,
        )
        assert citation.original_text == "Smith 2024"
        assert citation.pmid == "12345678"
        assert citation.match_type == "exact"
        assert citation.match_confidence == 1.0
    
    def test_fuzzy_match(self):
        """Test a fuzzy matched citation."""
        citation = VerifiedCitation(
            original_text="Smyth 2024",  # Typo in original
            pmid="12345678",
            title="The Smith Study",
            year=2024,
            match_type="fuzzy",
            match_confidence=0.85,
        )
        assert citation.match_type == "fuzzy"
        assert citation.match_confidence == 0.85


class TestFailedCitation:
    """Tests for FailedCitation model."""
    
    def test_not_found(self):
        """Test citation not found in PubMed."""
        citation = FailedCitation(
            original_text="Nonexistent et al. 2099",
            reason="not_found",
            search_query="Nonexistent 2099",
        )
        assert citation.reason == "not_found"
        assert citation.closest_match is None
    
    def test_with_closest_match(self):
        """Test failed citation with a close match suggested."""
        closest = VerifiedCitation(
            original_text="Smith 2023",
            pmid="11111111",
            title="Similar Study",
            year=2023,
            match_type="fuzzy",
            match_confidence=0.6,
        )
        citation = FailedCitation(
            original_text="Smith 2024",
            reason="year_mismatch",
            search_query="Smith 2024",
            closest_match=closest,
        )
        assert citation.reason == "year_mismatch"
        assert citation.closest_match is not None
        assert citation.closest_match.year == 2023


class TestGroundingReport:
    """Tests for GroundingReport model."""
    
    def test_empty_report(self):
        """Test empty grounding report."""
        report = GroundingReport()
        assert report.total_citations == 0
        assert report.hallucination_rate == 0.0
        assert report.has_failures is False
    
    def test_all_verified(self):
        """Test report with all citations verified."""
        report = GroundingReport(
            citations_verified=[
                VerifiedCitation(
                    original_text="Study 1",
                    pmid="11111111",
                    title="First Study",
                    year=2024,
                ),
                VerifiedCitation(
                    original_text="Study 2",
                    pmid="22222222",
                    title="Second Study",
                    year=2023,
                ),
            ]
        )
        assert report.total_citations == 2
        assert report.hallucination_rate == 0.0
        assert report.has_failures is False
    
    def test_some_failed(self):
        """Test report with mixed results."""
        report = GroundingReport(
            citations_verified=[
                VerifiedCitation(
                    original_text="Real Study",
                    pmid="11111111",
                    title="Real Study Title",
                    year=2024,
                ),
            ],
            citations_failed=[
                FailedCitation(
                    original_text="Fake Study",
                    reason="not_found",
                ),
            ],
        )
        assert report.total_citations == 2
        assert report.hallucination_rate == 0.5
        assert report.has_failures is True
    
    def test_merge_reports(self):
        """Test merging two reports."""
        report1 = GroundingReport(
            citations_verified=[
                VerifiedCitation(
                    original_text="Study A",
                    pmid="11111111",
                    title="A",
                    year=2024,
                ),
            ],
        )
        report2 = GroundingReport(
            citations_verified=[
                VerifiedCitation(
                    original_text="Study B",
                    pmid="22222222",
                    title="B",
                    year=2023,
                ),
            ],
            citations_failed=[
                FailedCitation(
                    original_text="Study C",
                    reason="not_found",
                ),
            ],
        )
        merged = report1.merge(report2)
        assert merged.total_citations == 3
        assert len(merged.citations_verified) == 2
        assert len(merged.citations_failed) == 1


class TestPubMedSearchResult:
    """Tests for PubMedSearchResult model."""
    
    def test_found_result(self):
        """Test search with results."""
        result = PubMedSearchResult(
            found=True,
            pmids=["12345678", "87654321"],
            total_count=2,
            query_used="ketamine pain",
        )
        assert result.found is True
        assert len(result.pmids) == 2
    
    def test_no_results(self):
        """Test search with no results."""
        result = PubMedSearchResult(
            found=False,
            pmids=[],
            total_count=0,
            query_used="nonexistent term xyz123",
        )
        assert result.found is False
        assert result.pmids == []

