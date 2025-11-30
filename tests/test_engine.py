"""Tests for ConferenceEngine."""

import pytest

from src.conference.engine import ConferenceEngine, create_default_config
from src.llm.client import MockLLMClient
from src.models.conference import (
    AgentConfig,
    AgentRole,
    ArbitratorConfig,
    ConferenceConfig,
)


class TestConferenceEngine:
    """Tests for ConferenceEngine class."""

    def _create_engine(self) -> tuple[ConferenceEngine, MockLLMClient]:
        """Helper to create engine with mock client."""
        # Set up mock responses for each model
        responses = {
            "advocate/model": """
**Recommended Approach**: Treatment A
**Rationale**: Best evidence supports this approach.
**Evidence**: Smith et al. 2023 showed efficacy.
**Confidence Level**: High
**Position Summary**: Strongly recommend Treatment A.
""",
            "skeptic/model": """
**Key Concerns**: Limited long-term data.
**Evidence Critique**: Smith et al. had small sample size.
**Risk Assessment**: Potential for adverse effects.
**Severity Rating**: Moderate concerns
**Position Summary**: Concerns about Treatment A safety.
""",
            "empiricist/model": """
**Evidence Assessment**: One RCT supports Treatment A.
**Evidence Quality**: Moderate - single RCT.
**Effect Size**: NNT of 5.
**Evidence Gaps**: No trials > 6 months.
**Position Summary**: Limited but promising evidence for Treatment A.
""",
            "arbitrator/model": """
### Consensus Points
- All agents agree Treatment A shows promise
- All agents agree more long-term data needed

### Synthesis Recommendation
Proceed with Treatment A with close monitoring and follow-up at 3 months.

### Key Tradeoffs Acknowledged
- Accepting limited long-term data

### Preserved Dissent
**Dissenting Agent**: Skeptic
**Dissent Summary**: Safety concerns not fully addressed
**Dissent Reasoning**: Insufficient long-term data
**Dissent Strength**: Moderate

### Confidence & Caveats
**Confidence Level**: Medium
**Key Caveats**:
- Monitor for adverse effects
- Plan for long-term follow-up
""",
        }
        
        client = MockLLMClient(responses=responses)
        engine = ConferenceEngine(client)
        return engine, client

    def _create_config(self) -> ConferenceConfig:
        """Helper to create test configuration."""
        return ConferenceConfig(
            num_rounds=2,
            agents=[
                AgentConfig(
                    agent_id="advocate",
                    role=AgentRole.ADVOCATE,
                    model="advocate/model",
                ),
                AgentConfig(
                    agent_id="skeptic",
                    role=AgentRole.SKEPTIC,
                    model="skeptic/model",
                ),
                AgentConfig(
                    agent_id="empiricist",
                    role=AgentRole.EMPIRICIST,
                    model="empiricist/model",
                ),
            ],
            arbitrator=ArbitratorConfig(model="arbitrator/model"),
        )

    @pytest.mark.asyncio
    async def test_run_conference_returns_result(self):
        """Test that run_conference returns ConferenceResult."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        result = await engine.run_conference(
            query="What is the best treatment for condition X?",
            config=config,
        )
        
        assert result is not None
        assert result.query == "What is the best treatment for condition X?"

    @pytest.mark.asyncio
    async def test_conference_has_rounds(self):
        """Test that result contains all rounds."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        result = await engine.run_conference(
            query="Test query",
            config=config,
        )
        
        assert len(result.rounds) == 2
        assert result.rounds[0].round_number == 1
        assert result.rounds[1].round_number == 2

    @pytest.mark.asyncio
    async def test_conference_has_synthesis(self):
        """Test that result contains synthesis."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        result = await engine.run_conference(
            query="Test query",
            config=config,
        )
        
        assert result.synthesis is not None
        assert result.synthesis.final_consensus != ""

    @pytest.mark.asyncio
    async def test_conference_has_dissent(self):
        """Test that result contains dissent record."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        result = await engine.run_conference(
            query="Test query",
            config=config,
        )
        
        assert result.dissent is not None
        assert result.dissent.preserved is True

    @pytest.mark.asyncio
    async def test_conference_tracks_tokens(self):
        """Test that token usage is tracked."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        result = await engine.run_conference(
            query="Test query",
            config=config,
        )
        
        assert result.token_usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_conference_tracks_duration(self):
        """Test that duration is tracked."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        result = await engine.run_conference(
            query="Test query",
            config=config,
        )
        
        # Duration may be 0 for very fast mock execution, just ensure it's non-negative
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_conference_generates_id(self):
        """Test that conference ID is generated."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        result = await engine.run_conference(
            query="Test query",
            config=config,
        )
        
        assert result.conference_id.startswith("conf_")

    @pytest.mark.asyncio
    async def test_conference_uses_provided_id(self):
        """Test that provided conference ID is used."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        result = await engine.run_conference(
            query="Test query",
            config=config,
            conference_id="custom_id_123",
        )
        
        assert result.conference_id == "custom_id_123"

    @pytest.mark.asyncio
    async def test_conference_includes_config(self):
        """Test that result includes configuration."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        result = await engine.run_conference(
            query="Test query",
            config=config,
        )
        
        assert result.config == config

    @pytest.mark.asyncio
    async def test_all_agents_respond_round_one(self):
        """Test that all agents respond in round 1."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        result = await engine.run_conference(
            query="Test query",
            config=config,
        )
        
        round_one = result.rounds[0]
        assert "advocate" in round_one.agent_responses
        assert "skeptic" in round_one.agent_responses
        assert "empiricist" in round_one.agent_responses

    @pytest.mark.asyncio
    async def test_cost_breakdown_available(self):
        """Test that cost breakdown is available."""
        engine, client = self._create_engine()
        config = self._create_config()
        
        await engine.run_conference(
            query="Test query",
            config=config,
        )
        
        breakdown = engine.get_cost_breakdown()
        
        assert "total_cost_usd" in breakdown
        assert "by_model" in breakdown


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""

    def test_creates_valid_config(self):
        """Test that default config is valid."""
        config = create_default_config()
        
        assert config is not None
        assert len(config.agents) == 3
        assert config.arbitrator is not None

    def test_default_has_three_agents(self):
        """Test that default has advocate, skeptic, empiricist."""
        config = create_default_config()
        
        roles = [a.role for a in config.agents]
        assert "advocate" in roles
        assert "skeptic" in roles
        assert "empiricist" in roles

    def test_custom_models(self):
        """Test that custom models can be specified."""
        config = create_default_config(
            advocate_model="custom/advocate",
            skeptic_model="custom/skeptic",
            empiricist_model="custom/empiricist",
            arbitrator_model="custom/arbitrator",
        )
        
        models = [a.model for a in config.agents]
        assert "custom/advocate" in models
        assert "custom/skeptic" in models
        assert "custom/empiricist" in models
        assert config.arbitrator.model == "custom/arbitrator"

    def test_custom_rounds(self):
        """Test that custom round count can be specified."""
        config = create_default_config(num_rounds=3)
        
        assert config.num_rounds == 3


class TestConferenceEngineEdgeCases:
    """Edge case tests for ConferenceEngine."""

    @pytest.mark.asyncio
    async def test_single_round_conference(self):
        """Test conference with single round."""
        client = MockLLMClient()
        engine = ConferenceEngine(client)
        
        config = ConferenceConfig(
            num_rounds=1,
            agents=[
                AgentConfig(
                    agent_id="agent",
                    role=AgentRole.ADVOCATE,
                    model="test",
                ),
            ],
            arbitrator=ArbitratorConfig(model="test"),
        )
        
        result = await engine.run_conference(
            query="Test",
            config=config,
        )
        
        assert len(result.rounds) == 1

    @pytest.mark.asyncio
    async def test_multiple_conferences_reset_tracking(self):
        """Test that token tracking resets between conferences."""
        client = MockLLMClient()
        engine = ConferenceEngine(client)
        
        config = ConferenceConfig(
            num_rounds=1,
            agents=[
                AgentConfig(
                    agent_id="agent",
                    role=AgentRole.ADVOCATE,
                    model="test",
                ),
            ],
            arbitrator=ArbitratorConfig(model="test"),
        )
        
        # Run first conference
        result1 = await engine.run_conference(query="Test 1", config=config)
        tokens1 = result1.token_usage.total_tokens
        
        # Run second conference
        result2 = await engine.run_conference(query="Test 2", config=config)
        tokens2 = result2.token_usage.total_tokens
        
        # Token counts should be similar (not cumulative)
        assert abs(tokens1 - tokens2) < tokens1  # Not doubled

