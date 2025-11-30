"""
Tests for PubMed client.

Uses mocked HTTP responses to test client logic without making real API calls.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.grounding.pubmed_client import PubMedClient


# Sample XML responses for mocking
SEARCH_RESPONSE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<eSearchResult>
    <Count>2</Count>
    <RetMax>2</RetMax>
    <IdList>
        <Id>12345678</Id>
        <Id>87654321</Id>
    </IdList>
</eSearchResult>
"""

SEARCH_EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<eSearchResult>
    <Count>0</Count>
    <RetMax>0</RetMax>
    <IdList/>
</eSearchResult>
"""

FETCH_RESPONSE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
    <PubmedArticle>
        <MedlineCitation>
            <PMID>12345678</PMID>
            <Article>
                <Journal>
                    <Title>Nature Medicine</Title>
                    <JournalIssue>
                        <PubDate>
                            <Year>2024</Year>
                        </PubDate>
                    </JournalIssue>
                </Journal>
                <ArticleTitle>Ketamine for Treatment-Resistant Depression: A Systematic Review</ArticleTitle>
                <AuthorList>
                    <Author>
                        <LastName>Smith</LastName>
                        <Initials>JD</Initials>
                    </Author>
                    <Author>
                        <LastName>Jones</LastName>
                        <Initials>AB</Initials>
                    </Author>
                </AuthorList>
                <Abstract>
                    <AbstractText>This is a test abstract about ketamine.</AbstractText>
                </Abstract>
            </Article>
        </MedlineCitation>
        <PubmedData>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345678</ArticleId>
                <ArticleId IdType="doi">10.1038/nm.1234</ArticleId>
            </ArticleIdList>
        </PubmedData>
    </PubmedArticle>
</PubmedArticleSet>
"""

FETCH_MULTIPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
    <PubmedArticle>
        <MedlineCitation>
            <PMID>11111111</PMID>
            <Article>
                <Journal><Title>Journal A</Title>
                    <JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue>
                </Journal>
                <ArticleTitle>Article One</ArticleTitle>
                <AuthorList>
                    <Author><LastName>First</LastName><Initials>A</Initials></Author>
                </AuthorList>
            </Article>
        </MedlineCitation>
    </PubmedArticle>
    <PubmedArticle>
        <MedlineCitation>
            <PMID>22222222</PMID>
            <Article>
                <Journal><Title>Journal B</Title>
                    <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
                </Journal>
                <ArticleTitle>Article Two</ArticleTitle>
                <AuthorList>
                    <Author><LastName>Second</LastName><Initials>B</Initials></Author>
                </AuthorList>
            </Article>
        </MedlineCitation>
    </PubmedArticle>
</PubmedArticleSet>
"""


class TestPubMedClientInit:
    """Tests for PubMed client initialization."""
    
    def test_default_init(self):
        """Test default initialization."""
        client = PubMedClient()
        assert client.api_key is None
        assert client.timeout == 30.0
        assert client._request_delay == 0.35  # Without API key
    
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = PubMedClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client._request_delay == 0.1  # With API key
    
    def test_init_with_timeout(self):
        """Test initialization with custom timeout."""
        client = PubMedClient(timeout=60.0)
        assert client.timeout == 60.0


class TestPubMedClientSearch:
    """Tests for PubMed search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_found(self):
        """Test search with results found."""
        client = PubMedClient()
        
        mock_response = MagicMock()
        mock_response.text = SEARCH_RESPONSE_XML
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_instance
            
            result = await client.search("ketamine depression")
        
        assert result.found is True
        assert len(result.pmids) == 2
        assert "12345678" in result.pmids
        assert result.total_count == 2
        assert result.query_used == "ketamine depression"
    
    @pytest.mark.asyncio
    async def test_search_not_found(self):
        """Test search with no results."""
        client = PubMedClient()
        
        mock_response = MagicMock()
        mock_response.text = SEARCH_EMPTY_XML
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_instance
            
            result = await client.search("nonexistent term xyz123")
        
        assert result.found is False
        assert result.pmids == []
        assert result.total_count == 0
    
    @pytest.mark.asyncio
    async def test_search_http_error(self):
        """Test search handles HTTP errors gracefully."""
        client = PubMedClient()
        
        # Create an async context manager that raises on get()
        async def raise_on_get(*args, **kwargs):
            raise httpx.HTTPError("Connection failed")
        
        mock_client_instance = MagicMock()
        mock_client_instance.get = raise_on_get
        
        async def mock_aenter(self):
            return mock_client_instance
        
        async def mock_aexit(self, *args):
            pass
        
        with patch.object(httpx.AsyncClient, "__aenter__", mock_aenter):
            with patch.object(httpx.AsyncClient, "__aexit__", mock_aexit):
                result = await client.search("test query")
        
        assert result.found is False
        assert result.pmids == []


class TestPubMedClientFetch:
    """Tests for PubMed fetch functionality."""
    
    @pytest.mark.asyncio
    async def test_fetch_by_pmid(self):
        """Test fetching article by PMID."""
        client = PubMedClient()
        
        mock_response = MagicMock()
        mock_response.text = FETCH_RESPONSE_XML
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_instance
            
            article = await client.fetch_by_pmid("12345678")
        
        assert article is not None
        assert article.pmid == "12345678"
        assert "Ketamine" in article.title
        assert article.year == 2024
        assert len(article.authors) == 2
        assert "Smith JD" in article.authors
        assert article.journal == "Nature Medicine"
        assert article.doi == "10.1038/nm.1234"
    
    @pytest.mark.asyncio
    async def test_fetch_multiple(self):
        """Test fetching multiple articles."""
        client = PubMedClient()
        
        mock_response = MagicMock()
        mock_response.text = FETCH_MULTIPLE_XML
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_instance
            
            articles = await client.fetch_multiple(["11111111", "22222222"])
        
        assert len(articles) == 2
        assert articles[0].pmid == "11111111"
        assert articles[0].title == "Article One"
        assert articles[1].pmid == "22222222"
        assert articles[1].year == 2024
    
    @pytest.mark.asyncio
    async def test_fetch_not_found(self):
        """Test fetching non-existent PMID."""
        client = PubMedClient()
        
        mock_response = MagicMock()
        mock_response.text = '<?xml version="1.0"?><PubmedArticleSet/>'
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_instance
            
            article = await client.fetch_by_pmid("00000000")
        
        assert article is None


class TestPubMedClientSearchMethods:
    """Tests for specialized search methods."""
    
    @pytest.mark.asyncio
    async def test_search_by_author_year(self):
        """Test author/year search builds correct query."""
        client = PubMedClient()
        
        mock_response = MagicMock()
        mock_response.text = SEARCH_RESPONSE_XML
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_instance
            
            result = await client.search_by_author_year("Smith", 2024)
        
        # Verify the query was constructed correctly
        assert result.found is True
        call_args = mock_instance.get.call_args
        params = call_args.kwargs.get("params", {})
        assert "Smith[Author]" in params.get("term", "")
        assert "2024[pdat]" in params.get("term", "")
    
    @pytest.mark.asyncio
    async def test_fuzzy_search(self):
        """Test fuzzy search extracts year and cleans text."""
        client = PubMedClient()
        
        mock_response = MagicMock()
        mock_response.text = SEARCH_RESPONSE_XML
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_instance
            
            result = await client.fuzzy_search("Smith et al. (2024) - ketamine study")
        
        assert result.found is True
        # Verify year was extracted
        call_args = mock_instance.get.call_args
        params = call_args.kwargs.get("params", {})
        assert "2024[pdat]" in params.get("term", "")


class TestPubMedClientRateLimiting:
    """Tests for rate limiting behavior."""
    
    def test_rate_limit_delay_without_key(self):
        """Test rate limit delay is set correctly without API key."""
        client = PubMedClient()
        assert client._request_delay == 0.35
    
    def test_rate_limit_delay_with_key(self):
        """Test rate limit delay is lower with API key."""
        client = PubMedClient(api_key="test_key")
        assert client._request_delay == 0.1

