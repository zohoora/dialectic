"""
Citation parser for extracting references from text.

Handles various citation formats commonly used by LLMs.
"""

import re
from typing import Optional

from src.models.grounding import RawCitation


class CitationParser:
    """
    Parses and extracts citations from text.
    
    Handles multiple citation formats:
    - PMID: 12345678
    - DOI: 10.xxxx/...
    - Author et al. (YEAR)
    - Author YEAR
    - Various journal reference formats
    """
    
    # Regex patterns for different citation formats
    PATTERNS = {
        # PMID patterns
        "pmid": [
            r"PMID[:\s]*(\d{7,8})",
            r"PubMed[:\s]*(\d{7,8})",
            r"(?:pmid|pubmed)\s*[:#]?\s*(\d{7,8})",
        ],
        # DOI patterns
        "doi": [
            r"(?:doi[:\s]*)?10\.\d{4,9}/[^\s\)\],\"']+",
            r"https?://doi\.org/(10\.\d{4,9}/[^\s\)\],\"']+)",
        ],
        # Author-year patterns (ordered from most specific to least specific)
        "author_year": [
            # Smith et al. (2024) or Smith et al., 2024
            r"([A-Z][a-z]{2,})\s+et\s+al\.?\s*[\(,]\s*((?:19|20)\d{2})\s*\)?",
            # Smith & Jones (2024) - must come before single author pattern
            r"([A-Z][a-z]{2,})\s*(?:&|and)\s*[A-Z][a-z]+\s*\(\s*((?:19|20)\d{2})\s*\)",
            # Smith (2024) - only proper names (3+ chars to avoid "In", "At", etc.)
            r"([A-Z][a-z]{2,})\s*\(\s*((?:19|20)\d{2})\s*\)",
        ],
    }
    
    # Common words that should NOT be treated as author names
    NON_AUTHOR_WORDS = {
        "in", "at", "on", "by", "to", "for", "the", "and", "but", "with",
        "from", "about", "after", "before", "during", "since", "until",
    }
    
    def extract_citations(self, text: str) -> list[RawCitation]:
        """
        Extract all citations from a block of text.
        
        Args:
            text: Text containing potential citations
            
        Returns:
            List of RawCitation objects
        """
        citations = []
        seen = set()  # Track seen citations to avoid duplicates
        
        # Extract PMIDs
        for pattern in self.PATTERNS["pmid"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                pmid = match.group(1)
                key = f"pmid:{pmid}"
                if key not in seen:
                    seen.add(key)
                    citations.append(RawCitation(
                        original_text=match.group(0).strip(),
                        citation_type="pmid",
                        extracted_pmid=pmid,
                    ))
        
        # Extract DOIs
        for pattern in self.PATTERNS["doi"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                doi = match.group(0)
                # Clean up the DOI
                doi = re.sub(r"^doi[:\s]*", "", doi, flags=re.IGNORECASE)
                doi = re.sub(r"^https?://doi\.org/", "", doi)
                key = f"doi:{doi}"
                if key not in seen:
                    seen.add(key)
                    citations.append(RawCitation(
                        original_text=match.group(0).strip(),
                        citation_type="doi",
                        extracted_doi=doi,
                    ))
        
        # Extract author-year citations
        # Track positions that have been matched to avoid overlapping matches
        matched_positions = set()
        
        for pattern in self.PATTERNS["author_year"]:
            for match in re.finditer(pattern, text):
                author = match.group(1)
                year = int(match.group(2))
                
                # Skip if this looks like a common word, not a name
                if author.lower() in self.NON_AUTHOR_WORDS:
                    continue
                
                # Skip if this position was already matched by a more specific pattern
                pos = (match.start(), match.end())
                overlaps = any(
                    (s <= match.start() < e) or (s < match.end() <= e)
                    for s, e in matched_positions
                )
                if overlaps:
                    continue
                
                key = f"author_year:{author.lower()}:{year}"
                if key not in seen:
                    seen.add(key)
                    matched_positions.add(pos)
                    citations.append(RawCitation(
                        original_text=match.group(0).strip(),
                        citation_type="author_year",
                        extracted_author=author,
                        extracted_year=year,
                    ))
        
        return citations
    
    def extract_citations_from_multiple(
        self, 
        texts: list[str]
    ) -> list[RawCitation]:
        """
        Extract citations from multiple text blocks.
        
        Deduplicates across all texts.
        
        Args:
            texts: List of text blocks to search
            
        Returns:
            Deduplicated list of RawCitation objects
        """
        all_citations = []
        seen = set()
        
        for text in texts:
            citations = self.extract_citations(text)
            for citation in citations:
                key = self._citation_key(citation)
                if key not in seen:
                    seen.add(key)
                    all_citations.append(citation)
        
        return all_citations
    
    def _citation_key(self, citation: RawCitation) -> str:
        """Generate a unique key for a citation."""
        if citation.extracted_pmid:
            return f"pmid:{citation.extracted_pmid}"
        elif citation.extracted_doi:
            return f"doi:{citation.extracted_doi}"
        elif citation.extracted_author and citation.extracted_year:
            return f"author_year:{citation.extracted_author.lower()}:{citation.extracted_year}"
        return f"unknown:{citation.original_text}"
    
    def normalize_for_search(self, citation: RawCitation) -> str:
        """
        Convert a citation to a PubMed search query.
        
        Args:
            citation: The raw citation to normalize
            
        Returns:
            Search query string for PubMed
        """
        if citation.extracted_pmid:
            return citation.extracted_pmid
        
        if citation.extracted_doi:
            # DOI search in PubMed
            return f"{citation.extracted_doi}[doi]"
        
        if citation.extracted_author and citation.extracted_year:
            # Author + year search
            return f"{citation.extracted_author}[Author] AND {citation.extracted_year}[pdat]"
        
        # Fallback: clean up the original text for search
        cleaned = re.sub(r"[^\w\s]", " ", citation.original_text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
    
    def parse_inline_citation(self, text: str) -> Optional[RawCitation]:
        """
        Try to parse a single inline citation.
        
        Useful for parsing citations that agents claim in a specific format.
        
        Args:
            text: Single citation text
            
        Returns:
            RawCitation if parseable, None otherwise
        """
        citations = self.extract_citations(text)
        return citations[0] if citations else None


def extract_citations(text: str) -> list[RawCitation]:
    """
    Convenience function to extract citations from text.
    
    Args:
        text: Text containing potential citations
        
    Returns:
        List of RawCitation objects
    """
    parser = CitationParser()
    return parser.extract_citations(text)


def normalize_citation(citation: RawCitation) -> str:
    """
    Convenience function to normalize a citation for search.
    
    Args:
        citation: Raw citation to normalize
        
    Returns:
        Search query string
    """
    parser = CitationParser()
    return parser.normalize_for_search(citation)

