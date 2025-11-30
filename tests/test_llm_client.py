"""Tests for LLM client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm.client import LLMClient, MockLLMClient
from src.models.conference import LLMResponse


class TestMockLLMClient:
    """Tests for MockLLMClient."""

    @pytest.mark.asyncio
    async def test_mock_client_returns_response(self):
        """Test that mock client returns a valid response."""
        client = MockLLMClient()
        
        response = await client.complete(
            model="test/model",
            messages=[{"role": "user", "content": "Hello"}],
        )
        
        assert isinstance(response, LLMResponse)
        assert response.model == "test/model"
        assert "Mock response" in response.content

    @pytest.mark.asyncio
    async def test_mock_client_custom_responses(self):
        """Test that mock client uses custom responses."""
        client = MockLLMClient(responses={
            "anthropic/claude-3.5-sonnet": "Custom Claude response",
            "openai/gpt-4o": "Custom GPT response",
        })
        
        claude_response = await client.complete(
            model="anthropic/claude-3.5-sonnet",
            messages=[{"role": "user", "content": "Test"}],
        )
        
        gpt_response = await client.complete(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": "Test"}],
        )
        
        assert claude_response.content == "Custom Claude response"
        assert gpt_response.content == "Custom GPT response"

    @pytest.mark.asyncio
    async def test_mock_client_records_calls(self):
        """Test that mock client records all calls."""
        client = MockLLMClient()
        
        await client.complete(
            model="model-a",
            messages=[{"role": "user", "content": "First"}],
            temperature=0.5,
        )
        await client.complete(
            model="model-b",
            messages=[{"role": "user", "content": "Second"}],
            temperature=0.8,
        )
        
        assert len(client.calls) == 2
        assert client.calls[0]["model"] == "model-a"
        assert client.calls[0]["temperature"] == 0.5
        assert client.calls[1]["model"] == "model-b"

    @pytest.mark.asyncio
    async def test_mock_client_tracks_tokens(self):
        """Test that mock client simulates token tracking."""
        client = MockLLMClient()
        
        response = await client.complete(
            model="test",
            messages=[{"role": "user", "content": "Hello world this is a test"}],
        )
        
        # Mock estimates tokens as len/4
        assert response.input_tokens > 0
        assert response.output_tokens > 0

    @pytest.mark.asyncio
    async def test_mock_client_session_usage(self):
        """Test session usage tracking."""
        client = MockLLMClient()
        
        await client.complete(
            model="model-a",
            messages=[{"role": "user", "content": "Test"}],
        )
        await client.complete(
            model="model-a",
            messages=[{"role": "user", "content": "Test"}],
        )
        await client.complete(
            model="model-b",
            messages=[{"role": "user", "content": "Test"}],
        )
        
        usage = client.get_session_usage()
        
        assert "model-a" in usage
        assert "model-b" in usage
        assert usage["model-a"]["calls"] == 2
        assert usage["model-b"]["calls"] == 1

    @pytest.mark.asyncio
    async def test_mock_client_reset(self):
        """Test session reset."""
        client = MockLLMClient()
        
        await client.complete(
            model="test",
            messages=[{"role": "user", "content": "Test"}],
        )
        
        assert len(client.calls) == 1
        
        client.reset_session()
        
        assert len(client.calls) == 0
        assert len(client._session_costs) == 0


class TestLLMClient:
    """Tests for LLMClient."""

    def test_client_requires_api_key(self):
        """Test that client raises error without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                LLMClient()
            
            assert "API key required" in str(exc_info.value)

    def test_client_accepts_api_key_param(self):
        """Test that client accepts API key as parameter."""
        client = LLMClient(api_key="test-key")
        assert client.api_key == "test-key"

    def test_client_reads_env_api_key(self):
        """Test that client reads API key from environment."""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "env-key"}):
            client = LLMClient()
            assert client.api_key == "env-key"

    def test_client_sets_openrouter_base_url(self):
        """Test that client uses OpenRouter base URL."""
        client = LLMClient(api_key="test-key")
        assert client.client.base_url.host == "openrouter.ai"

    def test_client_session_tracking_starts_empty(self):
        """Test that session tracking starts empty."""
        client = LLMClient(api_key="test-key")
        usage = client.get_session_usage()
        assert usage == {}

    def test_client_reset_session(self):
        """Test session reset."""
        client = LLMClient(api_key="test-key")
        client._session_costs = [{"model": "test", "input_tokens": 100, "output_tokens": 50}]
        
        client.reset_session()
        
        assert client._session_costs == []

