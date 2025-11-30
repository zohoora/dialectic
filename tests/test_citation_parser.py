"""
Tests for citation parser.
"""

import pytest
from src.grounding.citation_parser import (
    CitationParser,
    extract_citations,
    normalize_citation,
)
from src.models.grounding import RawCitation


class TestCitationParserPMID:
    """Tests for PMID extraction."""
    
    def test_pmid_with_colon(self):
        """Test PMID: format."""
        parser = CitationParser()
        text = "This is supported by PMID: 12345678"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].citation_type == "pmid"
        assert citations[0].extracted_pmid == "12345678"
    
    def test_pmid_lowercase(self):
        """Test lowercase pmid."""
        parser = CitationParser()
        text = "See pmid 87654321 for details"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].extracted_pmid == "87654321"
    
    def test_pubmed_format(self):
        """Test PubMed: format."""
        parser = CitationParser()
        text = "Reference: PubMed: 11111111"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].extracted_pmid == "11111111"
    
    def test_multiple_pmids(self):
        """Test extracting multiple PMIDs."""
        parser = CitationParser()
        text = "See PMID: 11111111 and PMID: 22222222"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 2
        pmids = {c.extracted_pmid for c in citations}
        assert pmids == {"11111111", "22222222"}


class TestCitationParserDOI:
    """Tests for DOI extraction."""
    
    def test_doi_with_prefix(self):
        """Test DOI: prefix format."""
        parser = CitationParser()
        text = "DOI: 10.1038/nature12373"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].citation_type == "doi"
        assert "10.1038/nature12373" in citations[0].extracted_doi
    
    def test_doi_url(self):
        """Test DOI as URL."""
        parser = CitationParser()
        text = "Available at https://doi.org/10.1001/jama.2024.1234"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].citation_type == "doi"
    
    def test_doi_bare(self):
        """Test bare DOI without prefix."""
        parser = CitationParser()
        text = "Reference 10.1016/j.pain.2024.01.001"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert "10.1016" in citations[0].extracted_doi


class TestCitationParserAuthorYear:
    """Tests for author-year citation extraction."""
    
    def test_et_al_parentheses(self):
        """Test 'Author et al. (YEAR)' format."""
        parser = CitationParser()
        text = "According to Smith et al. (2024)"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].citation_type == "author_year"
        assert citations[0].extracted_author == "Smith"
        assert citations[0].extracted_year == 2024
    
    def test_et_al_comma(self):
        """Test 'Author et al., YEAR' format."""
        parser = CitationParser()
        text = "As shown by Jones et al., 2023"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].extracted_author == "Jones"
        assert citations[0].extracted_year == 2023
    
    def test_single_author_parentheses(self):
        """Test 'Author (YEAR)' format."""
        parser = CitationParser()
        text = "Wilson (2022) demonstrated"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].extracted_author == "Wilson"
        assert citations[0].extracted_year == 2022
    
    def test_author_and_author(self):
        """Test 'Author & Author (YEAR)' format."""
        parser = CitationParser()
        text = "Brown & Davis (2021)"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].extracted_author == "Brown"
        assert citations[0].extracted_year == 2021
    
    def test_author_space_year(self):
        """Test 'Author YEAR' format - intentionally not supported.
        
        The 'Author YEAR' format (without parentheses) is too ambiguous
        and prone to false positives, so it's not extracted.
        """
        parser = CitationParser()
        text = "Referenced by Miller 2020"
        citations = parser.extract_citations(text)
        
        # This format is intentionally not supported due to false positives
        assert len(citations) == 0
    
    def test_multiple_author_year(self):
        """Test extracting multiple author-year citations."""
        parser = CitationParser()
        text = "Both Smith (2024) and Jones et al. (2023) agree."
        citations = parser.extract_citations(text)
        
        assert len(citations) == 2


class TestCitationParserMixed:
    """Tests for mixed citation extraction."""
    
    def test_mixed_citations(self):
        """Test extracting different citation types from same text."""
        parser = CitationParser()
        text = """
        The study by Smith et al. (2024) found significant results.
        See also PMID: 12345678 for additional data.
        Full text available at doi: 10.1000/test.
        """
        citations = parser.extract_citations(text)
        
        assert len(citations) == 3
        types = {c.citation_type for c in citations}
        assert types == {"author_year", "pmid", "doi"}
    
    def test_deduplication(self):
        """Test that duplicate citations are not extracted twice."""
        parser = CitationParser()
        text = "PMID: 12345678 and also PMID: 12345678"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
    
    def test_dedup_across_texts(self):
        """Test deduplication across multiple texts."""
        parser = CitationParser()
        texts = [
            "Smith et al. (2024) found",
            "As Smith et al. (2024) showed",
        ]
        citations = parser.extract_citations_from_multiple(texts)
        
        assert len(citations) == 1


class TestCitationParserNormalization:
    """Tests for citation normalization to search queries."""
    
    def test_normalize_pmid(self):
        """Test PMID normalization."""
        parser = CitationParser()
        citation = RawCitation(
            original_text="PMID: 12345678",
            citation_type="pmid",
            extracted_pmid="12345678",
        )
        query = parser.normalize_for_search(citation)
        assert query == "12345678"
    
    def test_normalize_doi(self):
        """Test DOI normalization."""
        parser = CitationParser()
        citation = RawCitation(
            original_text="doi: 10.1000/test",
            citation_type="doi",
            extracted_doi="10.1000/test",
        )
        query = parser.normalize_for_search(citation)
        assert "10.1000/test[doi]" in query
    
    def test_normalize_author_year(self):
        """Test author-year normalization."""
        parser = CitationParser()
        citation = RawCitation(
            original_text="Smith et al. (2024)",
            citation_type="author_year",
            extracted_author="Smith",
            extracted_year=2024,
        )
        query = parser.normalize_for_search(citation)
        assert "Smith[Author]" in query
        assert "2024[pdat]" in query


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_extract_citations_function(self):
        """Test the extract_citations convenience function."""
        text = "See Smith (2024)"
        citations = extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].extracted_author == "Smith"
    
    def test_normalize_citation_function(self):
        """Test the normalize_citation convenience function."""
        citation = RawCitation(
            original_text="PMID: 12345678",
            citation_type="pmid",
            extracted_pmid="12345678",
        )
        query = normalize_citation(citation)
        assert query == "12345678"


class TestCitationParserEdgeCases:
    """Tests for edge cases."""
    
    def test_no_citations(self):
        """Test text with no citations."""
        parser = CitationParser()
        text = "This text has no citations."
        citations = parser.extract_citations(text)
        
        assert len(citations) == 0
    
    def test_year_without_author(self):
        """Test that standalone years are not extracted."""
        parser = CitationParser()
        text = "In 2024, many things happened."
        citations = parser.extract_citations(text)
        
        # Should not extract just a year
        assert len(citations) == 0
    
    def test_old_year(self):
        """Test citations from older years."""
        parser = CitationParser()
        text = "Classic study by Johnson (1998)"
        citations = parser.extract_citations(text)
        
        assert len(citations) == 1
        assert citations[0].extracted_year == 1998
    
    def test_parse_inline_citation(self):
        """Test parsing a single inline citation."""
        parser = CitationParser()
        result = parser.parse_inline_citation("Smith (2024)")
        
        assert result is not None
        assert result.extracted_author == "Smith"
    
    def test_parse_inline_no_match(self):
        """Test parsing text that isn't a citation."""
        parser = CitationParser()
        result = parser.parse_inline_citation("just some text")
        
        assert result is None

