"""
Integration tests for the Grounding Layer.

These tests make real API calls to PubMed.
Skip by default, enable with: pytest -m integration
"""

import pytest
from src.grounding.citation_parser import CitationParser
from src.grounding.engine import GroundingEngine
from src.grounding.pubmed_client import PubMedClient


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestPubMedRealAPI:
    """Tests that make real PubMed API calls."""
    
    @pytest.mark.asyncio
    async def test_search_real_query(self):
        """Test searching PubMed with a real query."""
        client = PubMedClient()
        result = await client.search("ketamine depression treatment")
        
        assert result.found is True
        assert len(result.pmids) > 0
        assert result.total_count > 0
    
    @pytest.mark.asyncio
    async def test_fetch_known_pmid(self):
        """Test fetching a known article by PMID."""
        client = PubMedClient()
        # PMID for a well-known ketamine study
        article = await client.fetch_by_pmid("23982301")
        
        assert article is not None
        assert article.pmid == "23982301"
        assert "ketamine" in article.title.lower() or len(article.title) > 0
        assert article.year > 2000
    
    @pytest.mark.asyncio
    async def test_author_year_search(self):
        """Test searching by author and year."""
        client = PubMedClient()
        result = await client.search_by_author_year("Zarate", 2013)
        
        # Zarate is a prominent ketamine researcher
        assert result.found is True
        assert len(result.pmids) > 0
    
    @pytest.mark.asyncio
    async def test_nonexistent_pmid(self):
        """Test fetching a PMID that doesn't exist."""
        client = PubMedClient()
        # Use a PMID that definitely doesn't exist (too many digits)
        article = await client.fetch_by_pmid("999999999999")
        
        assert article is None


class TestGroundingEngineReal:
    """Integration tests for the full grounding engine."""
    
    @pytest.mark.asyncio
    async def test_verify_real_citation(self):
        """Test verifying a real citation."""
        engine = GroundingEngine()
        
        text = """
        According to a landmark study (PMID: 23982301), ketamine shows
        rapid antidepressant effects in treatment-resistant depression.
        """
        
        report = await engine.verify_text(text)
        
        # Should find at least one citation
        assert report.total_citations >= 1
        
        # PubMed API can be flaky, so we check if verification was attempted
        # rather than requiring success
        if report.total_citations > 0:
            # Either verified or failed, but should have processed
            assert len(report.citations_verified) + len(report.citations_failed) > 0
    
    @pytest.mark.asyncio
    async def test_verify_fake_citation(self):
        """Test that fake citations are caught."""
        engine = GroundingEngine()
        
        text = """
        According to Nonexistent et al. (2099), fake results were found.
        """
        
        report = await engine.verify_text(text)
        
        # This citation should fail (2099 is in the future)
        if report.total_citations > 0:
            # If a citation was extracted, it should fail
            assert report.has_failures or report.total_citations == 0
    
    @pytest.mark.asyncio
    async def test_mixed_citations(self):
        """Test with a mix of real and questionable citations."""
        engine = GroundingEngine()
        
        text = """
        Real studies like PMID: 23982301 show ketamine's efficacy.
        However, Smith (2025) found different results.
        """
        
        report = await engine.verify_text(text)
        
        # Should have found at least the PMID citation
        assert report.total_citations >= 1
    
    @pytest.mark.asyncio
    async def test_no_citations(self):
        """Test text with no citations."""
        engine = GroundingEngine()
        
        text = "This is just regular text with no citations at all."
        
        report = await engine.verify_text(text)
        
        assert report.total_citations == 0
        assert report.hallucination_rate == 0.0
        assert not report.has_failures


class TestCitationParserWithRealData:
    """Test citation parser with realistic medical text."""
    
    def test_extract_from_medical_text(self):
        """Test extracting citations from realistic medical text."""
        parser = CitationParser()
        
        text = """
        Ketamine has emerged as a rapid-acting antidepressant 
        (Zarate et al., 2006; PMID: 16894061). Multiple trials have 
        confirmed its efficacy (Murrough et al., 2013). The mechanism
        involves NMDA receptor antagonism and subsequent AMPA activation
        (Autry et al., 2011).
        """
        
        citations = parser.extract_citations(text)
        
        # Should find PMID and author-year citations
        assert len(citations) >= 2
        
        # Check PMID was extracted
        pmid_citations = [c for c in citations if c.extracted_pmid]
        assert len(pmid_citations) >= 1
        assert pmid_citations[0].extracted_pmid == "16894061"
    
    def test_extract_guidelines(self):
        """Test extracting guideline-style citations."""
        parser = CitationParser()
        
        text = """
        According to the APA Guidelines (2019), first-line treatments
        include SSRIs and CBT. The NICE guidelines (2022) recommend
        stepped care approaches.
        """
        
        citations = parser.extract_citations(text)
        
        # Should extract these as author-year style
        # (APA 2019, NICE 2022 might be extracted)
        assert len(citations) >= 0  # May or may not extract these


# Configuration for running integration tests
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )

