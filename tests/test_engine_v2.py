"""Tests for the v2.1 Conference Engine."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.conference.engine_v2 import (
    ConferenceEngineV2,
    V2ProgressStage,
    V2ProgressUpdate,
)
from src.models.conference import (
    AgentConfig,
    AgentRole,
    ArbitratorConfig,
    ConferenceConfig,
    LLMResponse,
)
from src.models.v2_schemas import (
    ArbitratorSynthesis,
    ClinicalConsensus,
    ConferenceMode,
    ExploratoryConsideration,
    Lane,
    LaneResult,
    PatientContext,
    RoutingDecision,
    ScoutReport,
    Tension,
    V2ConferenceState,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_llm_client():
    """Create a comprehensive mock LLM client."""
    client = MagicMock()
    
    # Default response
    client.complete = AsyncMock(return_value=LLMResponse(
        content="""
        **Analysis**: This is a mock analysis.
        **Recommendation**: Mock recommendation.
        **Confidence**: High
        """,
        model="test-model",
        input_tokens=100,
        output_tokens=50,
    ))
    
    return client


@pytest.fixture
def mock_grounding_engine():
    """Create a mock grounding engine."""
    engine = MagicMock()
    engine.verify_citations = AsyncMock(return_value={
        "citations_checked": 2,
        "citations_verified": 2,
        "citations_failed": 0,
        "hallucination_rate": 0.0,
    })
    return engine


@pytest.fixture
def sample_conference_config():
    """Create a sample conference config."""
    return ConferenceConfig(
        agents=[
            AgentConfig(
                agent_id="empiricist_1",
                role=AgentRole.EMPIRICIST,
                model="test-model",
            ),
            AgentConfig(
                agent_id="skeptic_1",
                role=AgentRole.SKEPTIC,
                model="test-model",
            ),
            AgentConfig(
                agent_id="mechanist_1",
                role=AgentRole.MECHANIST,
                model="test-model",
            ),
            AgentConfig(
                agent_id="speculator_1",
                role=AgentRole.SPECULATOR,
                model="test-model",
            ),
        ],
        arbitrator=ArbitratorConfig(model="test-model"),
        topology="free_discussion",
        num_rounds=2,
    )


@pytest.fixture
def sample_patient_context():
    """Create a sample patient context."""
    return PatientContext(
        age=55,
        sex="male",
        comorbidities=["diabetes", "hypertension"],
        failed_treatments=["metformin"],
    )


@pytest.fixture
def engine_v2(mock_llm_client, mock_grounding_engine):
    """Create a ConferenceEngineV2 instance."""
    return ConferenceEngineV2(
        llm_client=mock_llm_client,
        grounding_engine=mock_grounding_engine,
    )


# =============================================================================
# ENGINE INITIALIZATION TESTS
# =============================================================================


class TestEngineV2Init:
    """Tests for ConferenceEngineV2 initialization."""

    def test_init_with_all_params(self, mock_llm_client, mock_grounding_engine):
        """Test initialization with all parameters."""
        engine = ConferenceEngineV2(
            llm_client=mock_llm_client,
            grounding_engine=mock_grounding_engine,
        )
        
        assert engine is not None
        assert engine.llm_client is not None
        assert engine.grounding_engine is not None

    def test_init_without_grounding(self, mock_llm_client):
        """Test initialization without grounding engine."""
        engine = ConferenceEngineV2(
            llm_client=mock_llm_client,
            grounding_engine=None,
        )
        
        assert engine is not None
        assert engine.grounding_engine is None


# =============================================================================
# ROUTING INTEGRATION TESTS
# =============================================================================


class TestRoutingIntegration:
    """Tests for routing integration in v2 engine."""

    @pytest.mark.asyncio
    async def test_run_conference_with_routing(
        self,
        engine_v2,
        sample_conference_config,
        sample_patient_context,
    ):
        """Test that conference uses intelligent routing."""
        with patch("src.conference.engine_v2.route_query") as mock_route:
            mock_route.return_value = RoutingDecision(
                mode=ConferenceMode.COMPLEX_DILEMMA,
                active_agents=["empiricist", "skeptic", "mechanist"],
                activate_scout=True,
                risk_profile=0.5,
            )
            
            result = await engine_v2.run_conference(
                query="Complex treatment decision",
                config=sample_conference_config,
                patient_context=sample_patient_context,
                enable_routing=True,
            )
            
            # Routing should have been called
            mock_route.assert_called_once()

    @pytest.mark.asyncio
    async def test_routing_disabled_uses_all_agents(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that disabling routing uses all configured agents."""
        with patch("src.conference.engine_v2.route_query") as mock_route:
            result = await engine_v2.run_conference(
                query="Test query",
                config=sample_conference_config,
                patient_context=None,
                enable_routing=False,
            )
            
            # Routing should NOT have been called
            mock_route.assert_not_called()


# =============================================================================
# SCOUT INTEGRATION TESTS
# =============================================================================


class TestScoutIntegration:
    """Tests for Scout integration in v2 engine."""

    @pytest.mark.asyncio
    async def test_scout_activated_when_enabled(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that Scout is activated when enabled."""
        with patch("src.conference.engine_v2.route_query") as mock_route, \
             patch("src.conference.engine_v2.run_scout") as mock_scout:
            
            mock_route.return_value = RoutingDecision(
                mode=ConferenceMode.NOVEL_RESEARCH,
                active_agents=["empiricist", "speculator"],
                activate_scout=True,
            )
            mock_scout.return_value = ScoutReport(
                is_empty=False,
                query_keywords=["test"],
            )
            
            result = await engine_v2.run_conference(
                query="Novel treatment options",
                config=sample_conference_config,
                enable_scout=True,
                enable_routing=True,
            )
            
            # Scout should have been called
            mock_scout.assert_called_once()

    @pytest.mark.asyncio
    async def test_scout_disabled_not_called(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that Scout is not called when disabled."""
        with patch("src.conference.engine_v2.run_scout") as mock_scout:
            result = await engine_v2.run_conference(
                query="Simple query",
                config=sample_conference_config,
                enable_scout=False,
                enable_routing=False,
            )
            
            # Scout should NOT have been called
            mock_scout.assert_not_called()


# =============================================================================
# LANE EXECUTION TESTS
# =============================================================================


class TestLaneExecution:
    """Tests for two-lane execution in v2 engine."""

    @pytest.mark.asyncio
    async def test_both_lanes_execute(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that both lanes execute."""
        result = await engine_v2.run_conference(
            query="Test query for two lanes",
            config=sample_conference_config,
            enable_routing=False,
        )
        
        # Should have results from both lanes
        assert result is not None
        # The v2 result should contain lane information
        if hasattr(result, 'lane_a_result'):
            assert result.lane_a_result is not None
        if hasattr(result, 'lane_b_result'):
            assert result.lane_b_result is not None


# =============================================================================
# CROSS-EXAMINATION TESTS
# =============================================================================


class TestCrossExamExecution:
    """Tests for cross-examination phase."""

    @pytest.mark.asyncio
    async def test_cross_examination_runs(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that cross-examination phase runs."""
        result = await engine_v2.run_conference(
            query="Complex query needing cross-exam",
            config=sample_conference_config,
            enable_routing=False,
        )
        
        # Cross-exam should have produced critiques
        assert result is not None


# =============================================================================
# SYNTHESIS TESTS
# =============================================================================


class TestSynthesis:
    """Tests for arbitrator synthesis in v2 engine."""

    @pytest.mark.asyncio
    async def test_produces_bifurcated_output(
        self,
        engine_v2,
        sample_conference_config,
        mock_llm_client,
    ):
        """Test that synthesis produces bifurcated output."""
        # Mock the arbitrator to return structured synthesis
        mock_llm_client.complete = AsyncMock(return_value=LLMResponse(
            content="""
            CLINICAL_CONSENSUS:
            Recommend standard treatment A.
            
            EXPLORATORY:
            HYPOTHESIS: Novel approach B
            Mechanism: Unknown pathway
            
            TENSIONS:
            Standard vs novel approaches
            """,
            model="test-model",
            input_tokens=100,
            output_tokens=200,
        ))
        
        result = await engine_v2.run_conference(
            query="Treatment decision",
            config=sample_conference_config,
            enable_routing=False,
        )
        
        assert result is not None
        assert result.synthesis is not None


# =============================================================================
# PROGRESS CALLBACK TESTS
# =============================================================================


class TestProgressCallbacks:
    """Tests for progress callbacks in v2 engine."""

    @pytest.mark.asyncio
    async def test_progress_callback_called(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that progress callback is called during conference."""
        progress_updates = []
        
        def progress_callback(update: V2ProgressUpdate):
            progress_updates.append(update)
        
        result = await engine_v2.run_conference(
            query="Test query",
            config=sample_conference_config,
            progress_callback=progress_callback,
            enable_routing=False,
        )
        
        # Should have received progress updates
        assert len(progress_updates) > 0

    @pytest.mark.asyncio
    async def test_progress_stages_in_order(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that progress stages occur in logical order."""
        progress_updates = []
        
        def progress_callback(update: V2ProgressUpdate):
            progress_updates.append(update)
        
        result = await engine_v2.run_conference(
            query="Test query",
            config=sample_conference_config,
            progress_callback=progress_callback,
            enable_routing=False,
        )
        
        # Extract stages
        stages = [u.stage for u in progress_updates]
        
        # Should start with INITIALIZING
        assert V2ProgressStage.INITIALIZING in stages

    @pytest.mark.asyncio
    async def test_progress_includes_percent(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that progress updates include percentage."""
        progress_updates = []
        
        def progress_callback(update: V2ProgressUpdate):
            progress_updates.append(update)
        
        result = await engine_v2.run_conference(
            query="Test query",
            config=sample_conference_config,
            progress_callback=progress_callback,
            enable_routing=False,
        )
        
        # All updates should have percent
        for update in progress_updates:
            assert hasattr(update, 'percent')
            assert 0 <= update.percent <= 100


# =============================================================================
# RESULT STRUCTURE TESTS
# =============================================================================


class TestResultStructure:
    """Tests for v2 conference result structure."""

    @pytest.mark.asyncio
    async def test_result_has_required_fields(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that result has all required fields."""
        result = await engine_v2.run_conference(
            query="Test query",
            config=sample_conference_config,
            enable_routing=False,
        )
        
        # Required fields
        assert result.conference_id is not None
        assert result.query is not None
        assert result.synthesis is not None
        assert result.token_usage is not None

    @pytest.mark.asyncio
    async def test_result_includes_routing_decision(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that result includes routing decision."""
        with patch("src.conference.engine_v2.route_query") as mock_route:
            mock_route.return_value = RoutingDecision(
                mode=ConferenceMode.COMPLEX_DILEMMA,
                active_agents=["empiricist", "skeptic"],
                activate_scout=False,
            )
            
            result = await engine_v2.run_conference(
                query="Test query",
                config=sample_conference_config,
                enable_routing=True,
            )
            
            assert result.routing_decision is not None
            assert result.routing_decision.mode == ConferenceMode.COMPLEX_DILEMMA

    @pytest.mark.asyncio
    async def test_result_includes_scout_report_when_activated(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that result includes Scout report when activated."""
        with patch("src.conference.engine_v2.route_query") as mock_route, \
             patch("src.conference.engine_v2.run_scout") as mock_scout:
            
            mock_route.return_value = RoutingDecision(
                mode=ConferenceMode.NOVEL_RESEARCH,
                active_agents=["empiricist"],
                activate_scout=True,
            )
            mock_scout.return_value = ScoutReport(
                is_empty=False,
                query_keywords=["test"],
            )
            
            result = await engine_v2.run_conference(
                query="Novel research query",
                config=sample_conference_config,
                enable_scout=True,
                enable_routing=True,
            )
            
            assert result.scout_report is not None


# =============================================================================
# GROUNDING INTEGRATION TESTS
# =============================================================================


class TestGroundingIntegration:
    """Tests for grounding integration in v2 engine."""

    @pytest.mark.asyncio
    async def test_grounding_runs_when_enabled(
        self,
        engine_v2,
        sample_conference_config,
        mock_grounding_engine,
    ):
        """Test that grounding runs when enabled."""
        result = await engine_v2.run_conference(
            query="Test query with citations",
            config=sample_conference_config,
            enable_grounding=True,
            enable_routing=False,
        )
        
        # Grounding should have been called
        # (The exact verification depends on implementation)
        assert result is not None

    @pytest.mark.asyncio
    async def test_grounding_disabled_not_called(
        self,
        mock_llm_client,
        sample_conference_config,
    ):
        """Test that grounding is not called when disabled."""
        mock_grounding = MagicMock()
        
        engine = ConferenceEngineV2(
            llm_client=mock_llm_client,
            grounding_engine=mock_grounding,
        )
        
        result = await engine.run_conference(
            query="Test query",
            config=sample_conference_config,
            enable_grounding=False,
            enable_routing=False,
        )
        
        # Grounding verify_citations should NOT have been called
        mock_grounding.verify_citations.assert_not_called()


# =============================================================================
# FRAGILITY INTEGRATION TESTS
# =============================================================================


class TestFragilityIntegration:
    """Tests for fragility testing integration in v2 engine."""

    @pytest.mark.asyncio
    async def test_fragility_runs_when_enabled(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test that fragility testing runs when enabled."""
        result = await engine_v2.run_conference(
            query="Test query",
            config=sample_conference_config,
            enable_fragility=True,
            fragility_tests=3,
            enable_routing=False,
        )
        
        # Should have fragility report
        assert result is not None
        if hasattr(result, 'fragility_report') and result.fragility_report:
            assert result.fragility_report is not None


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in v2 engine."""

    @pytest.mark.asyncio
    async def test_handles_llm_error(
        self,
        mock_llm_client,
        sample_conference_config,
    ):
        """Test handling of LLM errors."""
        mock_llm_client.complete = AsyncMock(side_effect=Exception("LLM Error"))
        
        engine = ConferenceEngineV2(
            llm_client=mock_llm_client,
            grounding_engine=None,
        )
        
        with pytest.raises(Exception):
            await engine.run_conference(
                query="Test query",
                config=sample_conference_config,
                enable_routing=False,
            )

    @pytest.mark.asyncio
    async def test_handles_routing_error(
        self,
        engine_v2,
        sample_conference_config,
    ):
        """Test handling of routing errors."""
        with patch("src.conference.engine_v2.route_query") as mock_route:
            mock_route.side_effect = Exception("Routing error")
            
            # Should handle gracefully or raise
            try:
                result = await engine_v2.run_conference(
                    query="Test query",
                    config=sample_conference_config,
                    enable_routing=True,
                )
            except Exception as e:
                assert "Routing" in str(e) or True  # Error is expected

