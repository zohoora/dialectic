"""
Integration tests for the AI Case Conference system.

These tests make real API calls and are skipped by default.
Run with: pytest tests/test_integration.py -v --run-integration
"""

import os
import pytest

from src.conference.engine import ConferenceEngine, create_default_config
from src.llm.client import LLMClient
from src.models.conference import ConferenceConfig, AgentConfig, AgentRole, ArbitratorConfig


# Skip integration tests unless explicitly requested
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests skipped. Set RUN_INTEGRATION_TESTS=1 to run."
)


@pytest.fixture
def llm_client():
    """Create a real LLM client."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")
    return LLMClient(api_key=api_key)


@pytest.fixture
def simple_config():
    """Create a minimal configuration for testing."""
    return ConferenceConfig(
        num_rounds=1,
        agents=[
            AgentConfig(
                agent_id="advocate",
                role=AgentRole.ADVOCATE,
                model="openai/gpt-4o-mini",  # Cheaper model for testing
                temperature=0.7,
            ),
            AgentConfig(
                agent_id="skeptic",
                role=AgentRole.SKEPTIC,
                model="openai/gpt-4o-mini",
                temperature=0.7,
            ),
        ],
        arbitrator=ArbitratorConfig(
            model="openai/gpt-4o-mini",
            temperature=0.5,
        ),
    )


class TestRealAPIIntegration:
    """Integration tests with real API calls."""

    @pytest.mark.asyncio
    async def test_simple_conference(self, llm_client, simple_config):
        """Test running a simple conference with real API."""
        engine = ConferenceEngine(llm_client)
        
        result = await engine.run_conference(
            query="Should a patient with mild hypertension (BP 145/92) start medication?",
            config=simple_config,
        )
        
        # Basic assertions
        assert result is not None
        assert result.conference_id is not None
        assert len(result.rounds) == 1
        
        # Synthesis should have content
        assert result.synthesis.final_consensus
        assert len(result.synthesis.final_consensus) > 50
        
        # Token usage should be recorded
        assert result.token_usage.total_tokens > 0
        
        print(f"\n=== Conference Result ===")
        print(f"ID: {result.conference_id}")
        print(f"Duration: {result.duration_ms}ms")
        print(f"Tokens: {result.token_usage.total_tokens}")
        print(f"Cost: ${result.token_usage.estimated_cost_usd:.4f}")
        print(f"\nSynthesis:\n{result.synthesis.final_consensus}")

    @pytest.mark.asyncio
    async def test_two_round_conference(self, llm_client):
        """Test a two-round conference."""
        config = ConferenceConfig(
            num_rounds=2,
            agents=[
                AgentConfig(
                    agent_id="advocate",
                    role=AgentRole.ADVOCATE,
                    model="openai/gpt-4o-mini",
                ),
                AgentConfig(
                    agent_id="skeptic",
                    role=AgentRole.SKEPTIC,
                    model="openai/gpt-4o-mini",
                ),
            ],
            arbitrator=ArbitratorConfig(model="openai/gpt-4o-mini"),
        )
        
        engine = ConferenceEngine(llm_client)
        
        result = await engine.run_conference(
            query="Is it safe to combine acetaminophen and ibuprofen for pain management?",
            config=config,
        )
        
        assert len(result.rounds) == 2
        assert result.synthesis.final_consensus
        
        print(f"\n=== Two-Round Conference ===")
        print(f"Round 1 responses: {len(result.rounds[0].agent_responses)}")
        print(f"Round 2 responses: {len(result.rounds[1].agent_responses)}")
        print(f"\nSynthesis:\n{result.synthesis.final_consensus}")

    @pytest.mark.asyncio
    async def test_different_models(self, llm_client):
        """Test using different models for different agents."""
        config = ConferenceConfig(
            num_rounds=1,
            agents=[
                AgentConfig(
                    agent_id="advocate",
                    role=AgentRole.ADVOCATE,
                    model="openai/gpt-4o-mini",
                ),
                AgentConfig(
                    agent_id="skeptic",
                    role=AgentRole.SKEPTIC,
                    model="openai/gpt-4o-mini",
                ),
                AgentConfig(
                    agent_id="empiricist",
                    role=AgentRole.EMPIRICIST,
                    model="openai/gpt-4o-mini",
                ),
            ],
            arbitrator=ArbitratorConfig(model="openai/gpt-4o-mini"),
        )
        
        engine = ConferenceEngine(llm_client)
        
        result = await engine.run_conference(
            query="What is the first-line treatment for type 2 diabetes in a patient with mild kidney disease?",
            config=config,
        )
        
        # All three agents should have responded
        assert len(result.rounds[0].agent_responses) == 3
        assert "advocate" in result.rounds[0].agent_responses
        assert "skeptic" in result.rounds[0].agent_responses
        assert "empiricist" in result.rounds[0].agent_responses


class TestLLMClientReal:
    """Test the LLM client with real API calls."""

    @pytest.mark.asyncio
    async def test_single_completion(self, llm_client):
        """Test a single API completion."""
        response = await llm_client.complete(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'Hello, World!' and nothing else."}
            ],
            temperature=0.0,
        )
        
        assert response is not None
        assert "Hello" in response.content
        assert response.input_tokens > 0
        assert response.output_tokens > 0

    @pytest.mark.asyncio
    async def test_session_tracking(self, llm_client):
        """Test session usage tracking."""
        llm_client.reset_session()
        
        await llm_client.complete(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hello"}],
        )
        
        await llm_client.complete(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "Say goodbye"}],
        )
        
        usage = llm_client.get_session_usage()
        
        assert "openai/gpt-4o-mini" in usage
        assert usage["openai/gpt-4o-mini"]["calls"] == 2


def pytest_configure(config):
    """Add custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_addoption(parser):
    """Add command line option for integration tests."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires API key)",
    )


def pytest_collection_modifyitems(config, items):
    """Handle the --run-integration flag."""
    if config.getoption("--run-integration"):
        os.environ["RUN_INTEGRATION_TESTS"] = "1"

