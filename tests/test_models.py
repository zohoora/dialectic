"""Tests for data models."""

import pytest
from datetime import datetime

from src.models.conference import (
    AgentConfig,
    AgentRole,
    AgentResponse,
    ArbitratorConfig,
    ConferenceConfig,
    ConferenceResult,
    ConferenceRound,
    ConferenceSynthesis,
    ConferenceTopology,
    DissentRecord,
    LLMResponse,
    TokenUsage,
)


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_create_agent_config(self):
        """Test basic agent config creation."""
        config = AgentConfig(
            agent_id="agent_1",
            role=AgentRole.ADVOCATE,
            model="anthropic/claude-3.5-sonnet",
            temperature=0.7,
        )
        assert config.agent_id == "agent_1"
        assert config.role == "advocate"
        assert config.model == "anthropic/claude-3.5-sonnet"
        assert config.temperature == 0.7

    def test_default_temperature(self):
        """Test default temperature value."""
        config = AgentConfig(
            agent_id="agent_1",
            role=AgentRole.SKEPTIC,
            model="openai/gpt-4o",
        )
        assert config.temperature == 0.7

    def test_temperature_validation(self):
        """Test temperature bounds validation."""
        with pytest.raises(ValueError):
            AgentConfig(
                agent_id="agent_1",
                role=AgentRole.ADVOCATE,
                model="test",
                temperature=2.5,  # Above max
            )

    def test_serialization(self):
        """Test model serialization to dict."""
        config = AgentConfig(
            agent_id="agent_1",
            role=AgentRole.EMPIRICIST,
            model="google/gemini-pro-1.5",
        )
        data = config.model_dump()
        assert data["agent_id"] == "agent_1"
        assert data["role"] == "empiricist"


class TestConferenceConfig:
    """Tests for ConferenceConfig model."""

    def test_create_conference_config(self):
        """Test full conference config creation."""
        agents = [
            AgentConfig(
                agent_id="advocate",
                role=AgentRole.ADVOCATE,
                model="anthropic/claude-3.5-sonnet",
            ),
            AgentConfig(
                agent_id="skeptic",
                role=AgentRole.SKEPTIC,
                model="openai/gpt-4o",
            ),
            AgentConfig(
                agent_id="empiricist",
                role=AgentRole.EMPIRICIST,
                model="google/gemini-pro-1.5",
            ),
        ]
        arbitrator = ArbitratorConfig(model="anthropic/claude-3.5-sonnet")
        
        config = ConferenceConfig(
            topology=ConferenceTopology.FREE_DISCUSSION,
            num_rounds=2,
            agents=agents,
            arbitrator=arbitrator,
        )
        
        assert config.topology == "free_discussion"
        assert config.num_rounds == 2
        assert len(config.agents) == 3
        assert config.arbitrator.model == "anthropic/claude-3.5-sonnet"

    def test_default_topology(self):
        """Test default topology is free discussion."""
        config = ConferenceConfig(
            agents=[
                AgentConfig(
                    agent_id="a1",
                    role=AgentRole.ADVOCATE,
                    model="test",
                )
            ],
            arbitrator=ArbitratorConfig(model="test"),
        )
        assert config.topology == "free_discussion"


class TestAgentResponse:
    """Tests for AgentResponse model."""

    def test_create_response(self):
        """Test agent response creation."""
        response = AgentResponse(
            agent_id="advocate",
            role=AgentRole.ADVOCATE,
            model="anthropic/claude-3.5-sonnet",
            content="This is my detailed analysis...",
            position_summary="Recommend treatment A",
            confidence=0.85,
        )
        assert response.agent_id == "advocate"
        assert response.confidence == 0.85
        assert response.changed_from_previous is False

    def test_token_tracking(self):
        """Test token usage fields."""
        response = AgentResponse(
            agent_id="test",
            role=AgentRole.SKEPTIC,
            model="test",
            content="Response",
            input_tokens=100,
            output_tokens=50,
        )
        assert response.input_tokens == 100
        assert response.output_tokens == 50


class TestConferenceRound:
    """Tests for ConferenceRound model."""

    def test_create_round(self):
        """Test round creation with responses."""
        responses = {
            "advocate": AgentResponse(
                agent_id="advocate",
                role=AgentRole.ADVOCATE,
                model="test",
                content="Advocate response",
            ),
            "skeptic": AgentResponse(
                agent_id="skeptic",
                role=AgentRole.SKEPTIC,
                model="test",
                content="Skeptic response",
            ),
        }
        
        round_result = ConferenceRound(
            round_number=1,
            agent_responses=responses,
        )
        
        assert round_result.round_number == 1
        assert len(round_result.agent_responses) == 2
        assert "advocate" in round_result.agent_responses

    def test_timestamp_auto_set(self):
        """Test timestamp is automatically set."""
        round_result = ConferenceRound(round_number=1)
        assert round_result.timestamp is not None
        assert isinstance(round_result.timestamp, datetime)


class TestConferenceSynthesis:
    """Tests for ConferenceSynthesis model."""

    def test_create_synthesis(self):
        """Test synthesis creation."""
        synthesis = ConferenceSynthesis(
            final_consensus="Based on the discussion, treatment A is recommended.",
            confidence=0.78,
            key_points=[
                "Strong evidence for efficacy",
                "Acceptable safety profile",
            ],
            evidence_summary="Three RCTs support this approach.",
            caveats=["Limited data in elderly patients"],
        )
        
        assert synthesis.confidence == 0.78
        assert len(synthesis.key_points) == 2
        assert len(synthesis.caveats) == 1


class TestDissentRecord:
    """Tests for DissentRecord model."""

    def test_no_dissent(self):
        """Test default no-dissent record."""
        dissent = DissentRecord()
        assert dissent.preserved is False
        assert dissent.dissenting_agent is None

    def test_with_dissent(self):
        """Test dissent record with preserved dissent."""
        dissent = DissentRecord(
            preserved=True,
            dissenting_agent="skeptic",
            dissenting_role=AgentRole.SKEPTIC,
            summary="Insufficient evidence for long-term safety",
            reasoning="No trials beyond 6 months duration",
            strength="Moderate",
        )
        
        assert dissent.preserved is True
        assert dissent.dissenting_agent == "skeptic"
        assert dissent.strength == "Moderate"


class TestConferenceResult:
    """Tests for ConferenceResult model."""

    def test_create_full_result(self):
        """Test complete conference result creation."""
        config = ConferenceConfig(
            agents=[
                AgentConfig(
                    agent_id="a1",
                    role=AgentRole.ADVOCATE,
                    model="test",
                )
            ],
            arbitrator=ArbitratorConfig(model="test"),
        )
        
        synthesis = ConferenceSynthesis(
            final_consensus="Recommendation here",
            confidence=0.8,
        )
        
        result = ConferenceResult(
            conference_id="conf_123",
            query="What is the best treatment for condition X?",
            config=config,
            synthesis=synthesis,
            duration_ms=45000,
        )
        
        assert result.conference_id == "conf_123"
        assert result.duration_ms == 45000
        assert result.token_usage.total_tokens == 0  # Default

    def test_token_usage_tracking(self):
        """Test token usage in result."""
        usage = TokenUsage(
            total_input_tokens=5000,
            total_output_tokens=2000,
            total_tokens=7000,
            estimated_cost_usd=0.15,
        )
        
        assert usage.total_tokens == 7000
        assert usage.estimated_cost_usd == 0.15


class TestLLMResponse:
    """Tests for LLMResponse model."""

    def test_create_llm_response(self):
        """Test LLM response creation."""
        response = LLMResponse(
            content="This is the model output.",
            model="anthropic/claude-3.5-sonnet",
            input_tokens=150,
            output_tokens=75,
            finish_reason="stop",
        )
        
        assert response.content == "This is the model output."
        assert response.input_tokens == 150
        assert response.finish_reason == "stop"

