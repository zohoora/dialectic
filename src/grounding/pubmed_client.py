"""
PubMed client for citation verification.

Uses NCBI E-utilities API to search and fetch article details.
API documentation: https://www.ncbi.nlm.nih.gov/books/NBK25500/
"""

import asyncio
import os
import re
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import quote

import httpx

from src.models.grounding import PubMedArticle, PubMedSearchResult


class PubMedClient:
    """
    Client for interacting with PubMed via NCBI E-utilities.
    
    Rate limits:
    - Without API key: 3 requests/second
    - With API key: 10 requests/second
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        """
        Initialize the PubMed client.
        
        Args:
            api_key: NCBI API key for higher rate limits (optional)
            timeout: HTTP request timeout in seconds
        """
        self.api_key = api_key or os.getenv("NCBI_API_KEY")
        self.timeout = timeout
        self._request_delay = 0.1 if self.api_key else 0.35  # Respect rate limits
        self._last_request_time = 0.0
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self._request_delay:
            await asyncio.sleep(self._request_delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()
    
    def _build_params(self, **kwargs) -> dict:
        """Build request parameters with API key if available."""
        params = {"retmode": "xml", "db": "pubmed"}
        params.update(kwargs)
        if self.api_key:
            params["api_key"] = self.api_key
        return params
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10
    ) -> PubMedSearchResult:
        """
        Search PubMed for articles matching a query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            PubMedSearchResult with matching PMIDs
        """
        await self._rate_limit()
        
        params = self._build_params(
            term=query,
            retmax=max_results,
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/esearch.fcgi",
                    params=params,
                )
                response.raise_for_status()
                
                # Parse XML response
                root = ET.fromstring(response.text)
                
                # Get count
                count_elem = root.find(".//Count")
                total_count = int(count_elem.text) if count_elem is not None else 0
                
                # Get PMIDs
                pmids = []
                for id_elem in root.findall(".//Id"):
                    if id_elem.text:
                        pmids.append(id_elem.text)
                
                return PubMedSearchResult(
                    found=len(pmids) > 0,
                    pmids=pmids,
                    total_count=total_count,
                    query_used=query,
                )
                
        except httpx.HTTPError as e:
            # Return empty result on HTTP error
            return PubMedSearchResult(
                found=False,
                pmids=[],
                total_count=0,
                query_used=query,
            )
        except ET.ParseError:
            return PubMedSearchResult(
                found=False,
                pmids=[],
                total_count=0,
                query_used=query,
            )
    
    async def fetch_by_pmid(self, pmid: str) -> Optional[PubMedArticle]:
        """
        Fetch article details by PMID.
        
        Args:
            pmid: PubMed ID to fetch
            
        Returns:
            PubMedArticle if found, None otherwise
        """
        await self._rate_limit()
        
        params = self._build_params(id=pmid)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/efetch.fcgi",
                    params=params,
                )
                response.raise_for_status()
                
                return self._parse_article_xml(response.text, pmid)
                
        except (httpx.HTTPError, ET.ParseError):
            return None
    
    async def fetch_multiple(self, pmids: list[str]) -> list[PubMedArticle]:
        """
        Fetch multiple articles by PMID.
        
        Args:
            pmids: List of PubMed IDs to fetch
            
        Returns:
            List of PubMedArticle objects
        """
        if not pmids:
            return []
        
        await self._rate_limit()
        
        params = self._build_params(id=",".join(pmids))
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/efetch.fcgi",
                    params=params,
                )
                response.raise_for_status()
                
                return self._parse_multiple_articles_xml(response.text)
                
        except (httpx.HTTPError, ET.ParseError):
            return []
    
    def _parse_article_xml(self, xml_text: str, pmid: str) -> Optional[PubMedArticle]:
        """Parse a single article from XML response."""
        try:
            root = ET.fromstring(xml_text)
            article_elem = root.find(".//PubmedArticle")
            
            if article_elem is None:
                return None
            
            return self._extract_article(article_elem, pmid)
            
        except ET.ParseError:
            return None
    
    def _parse_multiple_articles_xml(self, xml_text: str) -> list[PubMedArticle]:
        """Parse multiple articles from XML response."""
        articles = []
        try:
            root = ET.fromstring(xml_text)
            
            for article_elem in root.findall(".//PubmedArticle"):
                # Get PMID from within the article
                pmid_elem = article_elem.find(".//PMID")
                if pmid_elem is not None and pmid_elem.text:
                    article = self._extract_article(article_elem, pmid_elem.text)
                    if article:
                        articles.append(article)
            
            return articles
            
        except ET.ParseError:
            return []
    
    def _extract_article(self, article_elem: ET.Element, pmid: str) -> Optional[PubMedArticle]:
        """Extract article data from an XML element."""
        try:
            # Get title
            title_elem = article_elem.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None and title_elem.text else "Unknown Title"
            
            # Get authors
            authors = []
            for author_elem in article_elem.findall(".//Author"):
                last_name = author_elem.find("LastName")
                initials = author_elem.find("Initials")
                if last_name is not None and last_name.text:
                    author_str = last_name.text
                    if initials is not None and initials.text:
                        author_str += f" {initials.text}"
                    authors.append(author_str)
            
            # Get year
            year = 0
            pub_date = article_elem.find(".//PubDate")
            if pub_date is not None:
                year_elem = pub_date.find("Year")
                if year_elem is not None and year_elem.text:
                    try:
                        year = int(year_elem.text)
                    except ValueError:
                        pass
                # Try MedlineDate if Year not found
                if year == 0:
                    medline_date = pub_date.find("MedlineDate")
                    if medline_date is not None and medline_date.text:
                        # Extract year from MedlineDate (e.g., "2024 Jan-Feb")
                        match = re.search(r"(\d{4})", medline_date.text)
                        if match:
                            year = int(match.group(1))
            
            # Get journal
            journal_elem = article_elem.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None and journal_elem.text else ""
            
            # Get DOI
            doi = None
            for article_id in article_elem.findall(".//ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = article_id.text
                    break
            
            # Get abstract
            abstract_elem = article_elem.find(".//Abstract/AbstractText")
            abstract = abstract_elem.text if abstract_elem is not None and abstract_elem.text else ""
            
            return PubMedArticle(
                pmid=pmid,
                title=title,
                authors=authors,
                year=year,
                journal=journal,
                doi=doi,
                abstract=abstract,
            )
            
        except Exception:
            return None
    
    async def search_by_author_year(
        self, 
        author: str, 
        year: int,
        keywords: list[str] = None,
    ) -> PubMedSearchResult:
        """
        Search for articles by author and year.
        
        Args:
            author: Author last name
            year: Publication year
            keywords: Optional additional keywords
            
        Returns:
            PubMedSearchResult with matching PMIDs
        """
        # Build search query
        query_parts = [f"{author}[Author]", f"{year}[pdat]"]
        if keywords:
            for kw in keywords:
                query_parts.append(f"{kw}")
        
        query = " AND ".join(query_parts)
        return await self.search(query)
    
    async def fuzzy_search(
        self, 
        citation_text: str,
        max_results: int = 5,
    ) -> PubMedSearchResult:
        """
        Perform a fuzzy search based on citation text.
        
        Attempts to find articles even with imprecise citation format.
        
        Args:
            citation_text: Raw citation text to search for
            max_results: Maximum results to return
            
        Returns:
            PubMedSearchResult with best matches
        """
        # Clean up the citation text
        cleaned = re.sub(r"[^\w\s]", " ", citation_text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        
        # Try to extract year
        year_match = re.search(r"\b(19|20)\d{2}\b", citation_text)
        year = year_match.group(0) if year_match else None
        
        # Build a loose query
        query = cleaned
        if year:
            query = f"{cleaned} AND {year}[pdat]"
        
        return await self.search(query, max_results=max_results)

