"""Tests for the Intelligent Router (v2.1)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.routing.signals import (
    COMPLEXITY_KEYWORDS,
    ESCALATION_PATTERNS,
    detect_complexity_signals,
)
from src.routing.router import (
    route_query,
    MODE_AGENT_CONFIGS,
    ROUTER_SYSTEM_PROMPT,
)
from src.models.v2_schemas import (
    ConferenceMode,
    PatientContext,
)


# =============================================================================
# COMPLEXITY SIGNAL DETECTION TESTS
# =============================================================================


class TestComplexitySignalDetection:
    """Tests for detect_complexity_signals function."""

    def test_detects_keyword_failed(self):
        """Test detection of 'failed' keyword."""
        signals = detect_complexity_signals(
            "Patient has failed gabapentin for CRPS",
            None,
        )
        assert any("failed" in s for s in signals)

    def test_detects_keyword_resistant(self):
        """Test detection of 'resistant' keyword."""
        signals = detect_complexity_signals(
            "Treatment-resistant depression",
            None,
        )
        assert any("resistant" in s for s in signals)

    def test_detects_keyword_refractory(self):
        """Test detection of 'refractory' keyword."""
        signals = detect_complexity_signals(
            "Refractory epilepsy management",
            None,
        )
        assert any("refractor" in s for s in signals)

    def test_detects_escalation_pattern_failed(self):
        """Test detection of failure patterns."""
        signals = detect_complexity_signals(
            "The patient has not responded to standard treatments",
            None,
        )
        assert len(signals) > 0

    def test_detects_escalation_pattern_tried_everything(self):
        """Test detection of 'tried everything' pattern."""
        signals = detect_complexity_signals(
            "We've tried everything for this patient's pain",
            None,
        )
        assert any("tried" in s.lower() for s in signals)

    def test_detects_multiple_comorbidities(self):
        """Test detection of multiple comorbidities from patient context."""
        context = PatientContext(
            comorbidities=["diabetes", "hypertension", "CKD"],
        )
        signals = detect_complexity_signals(
            "What is the best treatment?",
            context,
        )
        assert any("comorbidities" in s for s in signals)

    def test_detects_failed_treatments(self):
        """Test detection of failed treatments from patient context."""
        context = PatientContext(
            failed_treatments=["metformin", "sulfonylurea"],
        )
        signals = detect_complexity_signals(
            "What is the next option?",
            context,
        )
        assert any("failed_treatments" in s for s in signals)

    def test_detects_polypharmacy(self):
        """Test detection of polypharmacy."""
        context = PatientContext(
            current_medications=[
                "med1", "med2", "med3", "med4", "med5", "med6"
            ],
        )
        signals = detect_complexity_signals(
            "Adding a new medication",
            context,
        )
        assert any("polypharmacy" in s for s in signals)

    def test_detects_allergies(self):
        """Test detection of allergies."""
        context = PatientContext(
            allergies=["penicillin", "sulfa"],
        )
        signals = detect_complexity_signals(
            "What antibiotic to use?",
            context,
        )
        assert any("allergies" in s for s in signals)

    def test_simple_query_no_signals(self):
        """Test that simple queries have no complexity signals."""
        signals = detect_complexity_signals(
            "What is the first-line treatment for hypertension?",
            None,
        )
        # Simple queries should have few or no signals
        assert len(signals) < 2

    def test_multiple_signals_detected(self):
        """Test detection of multiple complexity signals."""
        context = PatientContext(
            failed_treatments=["gabapentin", "pregabalin"],
            comorbidities=["diabetes", "hypertension", "CKD"],
        )
        signals = detect_complexity_signals(
            "Patient has failed multiple treatments for refractory pain",
            context,
        )
        # Should detect keyword + patient context signals
        assert len(signals) >= 3


# =============================================================================
# ROUTING DECISION TESTS
# =============================================================================


class TestRouteQuery:
    """Tests for route_query function."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.complete = AsyncMock(return_value=MagicMock(
            content='{"mode": "COMPLEX_DILEMMA", "rationale": "Multiple factors involved"}'
        ))
        return client

    @pytest.mark.asyncio
    async def test_auto_escalates_with_multiple_signals(self, mock_llm_client):
        """Test automatic escalation with multiple complexity signals."""
        context = PatientContext(
            failed_treatments=["gabapentin", "pregabalin"],
        )
        
        result = await route_query(
            query="Patient has failed gabapentin and pregabalin for CRPS",
            patient_context=context,
            llm_client=mock_llm_client,
        )
        
        # Should auto-escalate without calling LLM
        assert result.mode in [ConferenceMode.COMPLEX_DILEMMA, ConferenceMode.NOVEL_RESEARCH]
        assert "auto-escalate" in result.routing_rationale.lower() or len(result.complexity_signals) >= 2

    @pytest.mark.asyncio
    async def test_activates_scout_for_novel_research(self, mock_llm_client):
        """Test Scout activation for NOVEL_RESEARCH mode."""
        # Configure mock to return NOVEL_RESEARCH
        mock_llm_client.complete = AsyncMock(return_value=MagicMock(
            content='{"mode": "NOVEL_RESEARCH", "rationale": "Experimental treatment requested"}'
        ))
        
        result = await route_query(
            query="Are there any experimental treatments for CRPS?",
            patient_context=None,
            llm_client=mock_llm_client,
        )
        
        # NOVEL_RESEARCH should activate Scout
        if result.mode == ConferenceMode.NOVEL_RESEARCH:
            assert result.activate_scout is True

    @pytest.mark.asyncio
    async def test_standard_care_minimal_agents(self, mock_llm_client):
        """Test STANDARD_CARE uses minimal agents."""
        # Configure mock to return STANDARD_CARE
        mock_llm_client.complete = AsyncMock(return_value=MagicMock(
            content='{"mode": "STANDARD_CARE", "rationale": "Simple guideline check"}'
        ))
        
        result = await route_query(
            query="What is the dosage of amoxicillin for adults?",
            patient_context=None,
            llm_client=mock_llm_client,
        )
        
        if result.mode == ConferenceMode.STANDARD_CARE:
            # STANDARD_CARE should have fewer agents
            assert len(result.active_agents) <= 4
            assert result.activate_scout is False

    @pytest.mark.asyncio
    async def test_routing_returns_valid_decision(self, mock_llm_client):
        """Test that routing returns a valid RoutingDecision."""
        result = await route_query(
            query="Complex case with multiple factors",
            patient_context=None,
            llm_client=mock_llm_client,
        )
        
        # Verify structure
        assert result.mode in ConferenceMode.__members__.values()
        assert isinstance(result.active_agents, list)
        assert isinstance(result.activate_scout, bool)
        assert 0.0 <= result.risk_profile <= 1.0

    @pytest.mark.asyncio
    async def test_lane_properties(self, mock_llm_client):
        """Test lane_a_agents and lane_b_agents properties."""
        result = await route_query(
            query="Complex treatment decision",
            patient_context=None,
            llm_client=mock_llm_client,
        )
        
        # Lane A should contain clinical agents
        clinical_agents = {"empiricist", "skeptic", "pragmatist", "patient_voice"}
        for agent in result.lane_a_agents:
            assert agent in clinical_agents
        
        # Lane B should contain exploratory agents
        exploratory_agents = {"mechanist", "speculator"}
        for agent in result.lane_b_agents:
            assert agent in exploratory_agents


# =============================================================================
# MODE CONFIGURATION TESTS
# =============================================================================


class TestModeConfigurations:
    """Tests for mode agent configurations."""

    def test_all_modes_have_configs(self):
        """Test that all conference modes have configurations."""
        for mode in ConferenceMode:
            assert mode in MODE_AGENT_CONFIGS

    def test_standard_care_config(self):
        """Test STANDARD_CARE configuration."""
        config = MODE_AGENT_CONFIGS[ConferenceMode.STANDARD_CARE]
        assert config["scout"] is False
        assert config["risk_profile"] < 0.5

    def test_novel_research_config(self):
        """Test NOVEL_RESEARCH configuration."""
        config = MODE_AGENT_CONFIGS[ConferenceMode.NOVEL_RESEARCH]
        assert config["scout"] is True
        assert config["risk_profile"] > 0.5
        # Should include speculator
        assert any("speculator" in str(a).lower() for a in config["agents"])

    def test_router_prompt_exists(self):
        """Test that router system prompt is defined."""
        assert ROUTER_SYSTEM_PROMPT is not None
        assert len(ROUTER_SYSTEM_PROMPT) > 100
        assert "STANDARD_CARE" in ROUTER_SYSTEM_PROMPT
        assert "COMPLEX_DILEMMA" in ROUTER_SYSTEM_PROMPT

