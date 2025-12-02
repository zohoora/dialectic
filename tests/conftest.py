"""
Pytest configuration and shared fixtures for the test suite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from src.models.conference import (
    AgentConfig, AgentRole, ConferenceConfig, ConferenceResult,
    LLMResponse, ConferenceRound, ConferenceSynthesis, AgentResponse,
    ArbitratorConfig, TokenUsage, DissentRecord
)
from src.models.fragility import FragilityReport, FragilityResult, FragilityOutcome


# ============================================================================
# Mock LLM Client
# ============================================================================

@pytest.fixture
def mock_llm_response():
    """Factory for creating mock LLM responses."""
    def _create(content: str, model: str = "test-model", input_tokens: int = 100, output_tokens: int = 50):
        return LLMResponse(
            content=content,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    return _create


@pytest.fixture
def mock_llm_client(mock_llm_response):
    """Create a mock LLM client that returns configurable responses."""
    client = MagicMock()
    client.complete = AsyncMock(return_value=mock_llm_response("Default mock response"))
    return client


# ============================================================================
# Conference Fixtures
# ============================================================================

@pytest.fixture
def sample_agent_configs():
    """Create sample agent configurations."""
    return [
        AgentConfig(
            agent_id="advocate_1",
            role=AgentRole.ADVOCATE,
            model="test-model",
        ),
        AgentConfig(
            agent_id="skeptic_1",
            role=AgentRole.SKEPTIC,
            model="test-model",
        ),
        AgentConfig(
            agent_id="empiricist_1",
            role=AgentRole.EMPIRICIST,
            model="test-model",
        ),
    ]


@pytest.fixture
def sample_conference_config(sample_agent_configs):
    """Create a sample conference configuration."""
    return ConferenceConfig(
        agents=sample_agent_configs,
        arbitrator=ArbitratorConfig(
            model="test-model",
        ),
        topology="free_discussion",
        num_rounds=2,
    )


@pytest.fixture
def sample_round_result():
    """Create a sample round result."""
    return ConferenceRound(
        round_number=1,
        agent_responses={
            "advocate_1": AgentResponse(
                agent_id="advocate_1",
                role=AgentRole.ADVOCATE,
                model="test-model",
                content="Consider metformin as first-line treatment.",
                confidence=0.8,
            ),
            "skeptic_1": AgentResponse(
                agent_id="skeptic_1",
                role=AgentRole.SKEPTIC,
                model="test-model",
                content="Agree with metformin. Monitor cardiac function.",
                confidence=0.75,
            ),
        }
    )


@pytest.fixture
def sample_synthesis_result():
    """Create a sample synthesis result."""
    return ConferenceSynthesis(
        final_consensus="Recommend metformin as first-line treatment with cardiac monitoring.",
        confidence=0.85,
        key_points=["Strong evidence base", "Well-tolerated"],
        evidence_summary="Strong evidence from UKPDS and ADA guidelines.",
        caveats=["Consider GLP-1 agonists for patients with high cardiovascular risk."],
    )


@pytest.fixture
def sample_conference_result(sample_round_result, sample_synthesis_result, sample_conference_config):
    """Create a sample conference result."""
    return ConferenceResult(
        conference_id="test-conference-123",
        query="What is the best first-line treatment for type 2 diabetes in a patient with cardiovascular disease?",
        config=sample_conference_config,
        rounds=[sample_round_result],
        synthesis=sample_synthesis_result,
        token_usage=TokenUsage(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_tokens=1500,
            estimated_cost_usd=0.05,
        ),
        dissent=DissentRecord(preserved=False),
    )


# ============================================================================
# Fragility Fixtures
# ============================================================================

@pytest.fixture
def sample_fragility_result():
    """Create a sample fragility test result."""
    return FragilityResult(
        perturbation="What if the patient has renal impairment?",
        explanation="The recommendation changed to account for renal dosing.",
        outcome=FragilityOutcome.MODIFIES,
        modified_recommendation="Recommend metformin with dose adjustment; avoid if GFR < 30.",
    )


@pytest.fixture
def sample_fragility_report(sample_fragility_result):
    """Create a sample fragility report.
    
    Note: survival_rate and fragility_level are computed properties,
    not constructor parameters.
    """
    return FragilityReport(
        results=[sample_fragility_result],
        perturbations_tested=1,
    )


# ============================================================================
# Experience/Heuristic Fixtures
# ============================================================================

# Note: InjectionResult is complex and varies by test - create inline in tests that need it


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def prompts_dir():
    """Return the path to the prompts directory."""
    return Path(__file__).parent.parent / "prompts"


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def mock_pubmed_response():
    """Create a mock PubMed search response."""
    return {
        "esearchresult": {
            "count": "10",
            "idlist": ["12345678", "23456789", "34567890"],
        }
    }


@pytest.fixture
def mock_pubmed_summary():
    """Create a mock PubMed summary response."""
    return {
        "result": {
            "12345678": {
                "uid": "12345678",
                "title": "Metformin in Type 2 Diabetes",
                "authors": [{"name": "Smith J"}, {"name": "Jones A"}],
                "source": "Diabetes Care",
                "pubdate": "2023",
            }
        }
    }
