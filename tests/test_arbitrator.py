"""Tests for ArbitratorEngine."""

import pytest

from src.conference.arbitrator import ArbitratorEngine
from src.llm.client import MockLLMClient
from src.models.conference import (
    AgentResponse,
    AgentRole,
    ArbitratorConfig,
    ConferenceRound,
)


class TestArbitratorEngine:
    """Tests for ArbitratorEngine class."""

    def _create_arbitrator(self, response: str = None) -> tuple[ArbitratorEngine, MockLLMClient]:
        """Helper to create arbitrator with mock client."""
        default_response = """
### Consensus Points
- All agents agree that evidence is limited
- All agents agree that patient safety is paramount

### Synthesis Recommendation
Based on the deliberation, I recommend a cautious approach with Treatment A, 
starting at a low dose with close monitoring.

### Key Tradeoffs Acknowledged
- Accepting limited long-term data in favor of addressing immediate symptoms

### Preserved Dissent
**Dissenting Agent**: Skeptic
**Dissent Summary**: Concerns about long-term safety remain unaddressed
**Dissent Reasoning**: No trials beyond 6 months exist
**Dissent Strength**: Moderate

### Confidence & Caveats
**Confidence Level**: Medium
**Key Caveats**:
- Limited long-term data
- Patient should be monitored closely
**Would Reconsider If**: New safety data emerges
"""
        
        client = MockLLMClient(responses={
            "arbitrator/model": response or default_response,
        })
        
        config = ArbitratorConfig(
            model="arbitrator/model",
            temperature=0.5,
        )
        
        arbitrator = ArbitratorEngine(config, client)
        return arbitrator, client

    def _create_rounds(self) -> list[ConferenceRound]:
        """Helper to create test rounds."""
        round_1 = ConferenceRound(
            round_number=1,
            agent_responses={
                "advocate": AgentResponse(
                    agent_id="advocate",
                    role=AgentRole.ADVOCATE,
                    model="test",
                    content="I recommend Treatment A.",
                ),
                "skeptic": AgentResponse(
                    agent_id="skeptic",
                    role=AgentRole.SKEPTIC,
                    model="test",
                    content="I have concerns about Treatment A.",
                ),
            },
        )
        
        round_2 = ConferenceRound(
            round_number=2,
            agent_responses={
                "advocate": AgentResponse(
                    agent_id="advocate",
                    role=AgentRole.ADVOCATE,
                    model="test",
                    content="I acknowledge the concerns but still recommend A.",
                ),
                "skeptic": AgentResponse(
                    agent_id="skeptic",
                    role=AgentRole.SKEPTIC,
                    model="test",
                    content="My concerns remain.",
                ),
            },
        )
        
        return [round_1, round_2]

    @pytest.mark.asyncio
    async def test_synthesize_returns_tuple(self):
        """Test that synthesize returns correct tuple."""
        arbitrator, client = self._create_arbitrator()
        rounds = self._create_rounds()
        
        synthesis, dissent, raw = await arbitrator.synthesize(
            query="Test query",
            rounds=rounds,
        )
        
        assert synthesis is not None
        assert dissent is not None
        assert raw is not None

    @pytest.mark.asyncio
    async def test_synthesis_has_consensus(self):
        """Test that synthesis contains final consensus."""
        arbitrator, client = self._create_arbitrator()
        rounds = self._create_rounds()
        
        synthesis, _, _ = await arbitrator.synthesize(
            query="Test query",
            rounds=rounds,
        )
        
        assert synthesis.final_consensus != ""
        assert "Treatment A" in synthesis.final_consensus

    @pytest.mark.asyncio
    async def test_synthesis_has_key_points(self):
        """Test that synthesis contains key points."""
        arbitrator, client = self._create_arbitrator()
        rounds = self._create_rounds()
        
        synthesis, _, _ = await arbitrator.synthesize(
            query="Test query",
            rounds=rounds,
        )
        
        assert len(synthesis.key_points) > 0

    @pytest.mark.asyncio
    async def test_synthesis_has_confidence(self):
        """Test that synthesis has confidence level."""
        arbitrator, client = self._create_arbitrator()
        rounds = self._create_rounds()
        
        synthesis, _, _ = await arbitrator.synthesize(
            query="Test query",
            rounds=rounds,
        )
        
        assert 0 <= synthesis.confidence <= 1

    @pytest.mark.asyncio
    async def test_dissent_preserved(self):
        """Test that dissent is preserved when present."""
        arbitrator, client = self._create_arbitrator()
        rounds = self._create_rounds()
        
        _, dissent, _ = await arbitrator.synthesize(
            query="Test query",
            rounds=rounds,
        )
        
        assert dissent.preserved is True
        assert "Skeptic" in dissent.dissenting_agent

    @pytest.mark.asyncio
    async def test_dissent_has_summary(self):
        """Test that dissent has summary."""
        arbitrator, client = self._create_arbitrator()
        rounds = self._create_rounds()
        
        _, dissent, _ = await arbitrator.synthesize(
            query="Test query",
            rounds=rounds,
        )
        
        assert dissent.summary != ""

    @pytest.mark.asyncio
    async def test_no_dissent_when_none_present(self):
        """Test handling when no dissent in response."""
        response = """
### Consensus Points
- All agents agree

### Synthesis Recommendation
Everyone agrees on Treatment A.

### Preserved Dissent
None - all agents reached consensus.

### Confidence & Caveats
**Confidence Level**: High
"""
        arbitrator, client = self._create_arbitrator(response)
        rounds = self._create_rounds()
        
        _, dissent, _ = await arbitrator.synthesize(
            query="Test query",
            rounds=rounds,
        )
        
        assert dissent.preserved is False

    @pytest.mark.asyncio
    async def test_uses_correct_model(self):
        """Test that arbitrator uses configured model."""
        arbitrator, client = self._create_arbitrator()
        rounds = self._create_rounds()
        
        await arbitrator.synthesize(query="Test", rounds=rounds)
        
        assert len(client.calls) == 1
        assert client.calls[0]["model"] == "arbitrator/model"

    @pytest.mark.asyncio
    async def test_uses_correct_temperature(self):
        """Test that arbitrator uses configured temperature."""
        arbitrator, client = self._create_arbitrator()
        rounds = self._create_rounds()
        
        await arbitrator.synthesize(query="Test", rounds=rounds)
        
        assert client.calls[0]["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_includes_all_rounds_in_prompt(self):
        """Test that all rounds are included in the prompt."""
        arbitrator, client = self._create_arbitrator()
        rounds = self._create_rounds()
        
        await arbitrator.synthesize(query="Test", rounds=rounds)
        
        user_message = client.calls[0]["messages"][1]["content"]
        assert "Round 1" in user_message
        assert "Round 2" in user_message

    @pytest.mark.asyncio
    async def test_extracts_caveats(self):
        """Test that caveats are extracted."""
        arbitrator, client = self._create_arbitrator()
        rounds = self._create_rounds()
        
        synthesis, _, _ = await arbitrator.synthesize(
            query="Test",
            rounds=rounds,
        )
        
        assert len(synthesis.caveats) > 0


class TestArbitratorConfidenceParsing:
    """Tests for confidence level parsing."""

    @pytest.mark.asyncio
    async def test_high_confidence(self):
        """Test parsing high confidence."""
        response = """
### Synthesis Recommendation
Strong recommendation.

### Confidence & Caveats
**Confidence Level**: High - strong consensus.
"""
        client = MockLLMClient(responses={"model": response})
        arbitrator = ArbitratorEngine(
            ArbitratorConfig(model="model"),
            client,
        )
        
        synthesis, _, _ = await arbitrator.synthesize("Test", [])
        
        assert synthesis.confidence == 0.85

    @pytest.mark.asyncio
    async def test_low_confidence(self):
        """Test parsing low confidence."""
        response = """
### Synthesis Recommendation
Tentative recommendation.

### Confidence & Caveats
**Confidence Level**: Low - limited evidence.
"""
        client = MockLLMClient(responses={"model": response})
        arbitrator = ArbitratorEngine(
            ArbitratorConfig(model="model"),
            client,
        )
        
        synthesis, _, _ = await arbitrator.synthesize("Test", [])
        
        assert synthesis.confidence == 0.35

    @pytest.mark.asyncio
    async def test_default_confidence(self):
        """Test default confidence when not specified."""
        response = """
### Synthesis Recommendation
Some recommendation without confidence stated.
"""
        client = MockLLMClient(responses={"model": response})
        arbitrator = ArbitratorEngine(
            ArbitratorConfig(model="model"),
            client,
        )
        
        synthesis, _, _ = await arbitrator.synthesize("Test", [])
        
        assert synthesis.confidence == 0.6  # Default to moderate

