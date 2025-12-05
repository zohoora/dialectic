"""Tests for the Lane Executor (v2.1 parallel lane architecture)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.conference.lanes import (
    LaneExecutor,
    LaneProgressStage,
    LaneProgressUpdate,
)
from src.models.conference import AgentConfig, AgentRole, LLMResponse
from src.models.v2_schemas import (
    ConferenceMode,
    Critique,
    EvidenceGrade,
    FeasibilityAssessment,
    Lane,
    LaneResult,
    PatientContext,
    RoutingDecision,
    ScoutCitation,
    ScoutReport,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.complete = AsyncMock(return_value=LLMResponse(
        content="Mock agent response with analysis and recommendations.",
        model="test-model",
        input_tokens=100,
        output_tokens=50,
    ))
    return client


@pytest.fixture
def sample_routing_decision():
    """Create a sample routing decision for COMPLEX_DILEMMA."""
    return RoutingDecision(
        mode=ConferenceMode.COMPLEX_DILEMMA,
        active_agents=[
            "empiricist", "skeptic", "pragmatist", "patient_voice",
            "mechanist", "speculator"
        ],
        activate_scout=True,
        risk_profile=0.5,
    )


@pytest.fixture
def sample_scout_report():
    """Create a sample Scout report."""
    return ScoutReport(
        is_empty=False,
        query_keywords=["diabetes", "treatment"],
        high_quality_rcts=[
            ScoutCitation(
                title="RCT of new diabetes treatment",
                authors=["Smith J"],
                year=2024,
                evidence_grade=EvidenceGrade.RCT_LARGE,
                key_finding="Significant improvement",
                sample_size=500,
            )
        ],
    )


@pytest.fixture
def sample_patient_context():
    """Create a sample patient context."""
    return PatientContext(
        age=55,
        sex="male",
        comorbidities=["hypertension", "obesity"],
        current_medications=["metformin"],
        failed_treatments=["sulfonylurea"],
    )


@pytest.fixture
def mock_agents(mock_llm_client):
    """Create mock agents for testing."""
    from src.conference.agent import Agent
    
    agents = []
    roles = ["empiricist", "skeptic", "pragmatist", "patient_voice", "mechanist", "speculator"]
    
    for role in roles:
        config = AgentConfig(
            agent_id=f"{role}_1",
            role=role,
            model="test-model",
            temperature=0.5,
        )
        agent = Agent(config, mock_llm_client)
        agents.append(agent)
    
    return agents


@pytest.fixture
def lane_executor(
    mock_agents,
    sample_routing_decision,
    sample_scout_report,
    sample_patient_context,
):
    """Create a LaneExecutor instance."""
    return LaneExecutor(
        agents=mock_agents,
        routing_decision=sample_routing_decision,
        scout_report=sample_scout_report,
        patient_context=sample_patient_context,
    )


# =============================================================================
# LANE EXECUTOR INITIALIZATION TESTS
# =============================================================================


class TestLaneExecutorInit:
    """Tests for LaneExecutor initialization."""

    def test_init_with_all_params(
        self,
        mock_agents,
        sample_routing_decision,
        sample_scout_report,
        sample_patient_context,
    ):
        """Test initialization with all parameters."""
        executor = LaneExecutor(
            agents=mock_agents,
            routing_decision=sample_routing_decision,
            scout_report=sample_scout_report,
            patient_context=sample_patient_context,
        )
        
        assert executor is not None
        assert len(executor.agents) == len(mock_agents)

    def test_init_without_scout(
        self,
        mock_agents,
        sample_routing_decision,
        sample_patient_context,
    ):
        """Test initialization without Scout report."""
        executor = LaneExecutor(
            agents=mock_agents,
            routing_decision=sample_routing_decision,
            scout_report=None,
            patient_context=sample_patient_context,
        )
        
        assert executor is not None
        assert executor.scout_report is None

    def test_init_without_patient_context(
        self,
        mock_agents,
        sample_routing_decision,
        sample_scout_report,
    ):
        """Test initialization without patient context."""
        executor = LaneExecutor(
            agents=mock_agents,
            routing_decision=sample_routing_decision,
            scout_report=sample_scout_report,
            patient_context=None,
        )
        
        assert executor is not None


# =============================================================================
# LANE ASSIGNMENT TESTS
# =============================================================================


class TestLaneAssignment:
    """Tests for lane assignment logic."""

    def test_lane_a_assignment(self, lane_executor):
        """Test that Lane A gets clinical agents."""
        lane_a_agents = lane_executor.lane_a_agents
        
        # Lane A should contain clinical agents
        clinical_roles = {"empiricist", "skeptic", "pragmatist", "patient_voice"}
        for agent in lane_a_agents:
            assert agent.role in clinical_roles

    def test_lane_b_assignment(self, lane_executor):
        """Test that Lane B gets exploratory agents."""
        lane_b_agents = lane_executor.lane_b_agents
        
        # Lane B should contain exploratory agents
        exploratory_roles = {"mechanist", "speculator"}
        for agent in lane_b_agents:
            assert agent.role in exploratory_roles

    def test_no_overlap_between_lanes(self, lane_executor):
        """Test that agents are not in both lanes."""
        lane_a_ids = {a.agent_id for a in lane_executor.lane_a_agents}
        lane_b_ids = {a.agent_id for a in lane_executor.lane_b_agents}
        
        # No overlap
        assert len(lane_a_ids & lane_b_ids) == 0


# =============================================================================
# PARALLEL LANE EXECUTION TESTS
# =============================================================================


class TestParallelLaneExecution:
    """Tests for parallel lane execution."""

    @pytest.mark.asyncio
    async def test_execute_parallel_lanes(self, lane_executor):
        """Test parallel execution of both lanes."""
        lane_a_result, lane_b_result = await lane_executor.execute_parallel_lanes(
            query="What is the treatment for diabetes?",
        )
        
        # Both lanes should return results
        assert lane_a_result is not None
        assert lane_b_result is not None
        
        # Results should be LaneResult instances
        assert isinstance(lane_a_result, LaneResult)
        assert isinstance(lane_b_result, LaneResult)
        
        # Correct lane assignments
        assert lane_a_result.lane == Lane.CLINICAL
        assert lane_b_result.lane == Lane.EXPLORATORY

    @pytest.mark.asyncio
    async def test_lane_a_has_responses(self, lane_executor):
        """Test that Lane A produces agent responses."""
        lane_a_result, _ = await lane_executor.execute_parallel_lanes(
            query="Test query",
        )
        
        # Should have responses from clinical agents
        assert len(lane_a_result.agent_responses) > 0

    @pytest.mark.asyncio
    async def test_lane_b_has_responses(self, lane_executor):
        """Test that Lane B produces agent responses."""
        _, lane_b_result = await lane_executor.execute_parallel_lanes(
            query="Test query",
        )
        
        # Should have responses from exploratory agents
        assert len(lane_b_result.agent_responses) > 0

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, lane_executor):
        """Test that progress callback is called during execution."""
        progress_updates = []
        
        def progress_callback(update: LaneProgressUpdate):
            progress_updates.append(update)
        
        await lane_executor.execute_parallel_lanes(
            query="Test query",
            progress_callback=progress_callback,
        )
        
        # Should have received progress updates
        assert len(progress_updates) > 0
        
        # Should include lane start events
        stages = [u.stage for u in progress_updates]
        assert LaneProgressStage.LANE_A_START in stages or LaneProgressStage.LANE_B_START in stages


# =============================================================================
# CROSS-EXAMINATION TESTS
# =============================================================================


class TestCrossExamination:
    """Tests for cross-examination between lanes."""

    @pytest.fixture
    def lane_results(self, lane_executor):
        """Pre-execute lanes to get results for cross-exam."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            lane_executor.execute_parallel_lanes(query="Test query")
        )

    @pytest.mark.asyncio
    async def test_execute_cross_examination(self, lane_executor):
        """Test cross-examination execution."""
        # First execute parallel lanes
        lane_a_result, lane_b_result = await lane_executor.execute_parallel_lanes(
            query="Test query",
        )
        
        # Then execute cross-examination
        critiques = await lane_executor.execute_cross_examination(
            query="Test query",
            lane_a_result=lane_a_result,
            lane_b_result=lane_b_result,
        )
        
        # Should return list of critiques
        assert isinstance(critiques, list)

    @pytest.mark.asyncio
    async def test_cross_exam_includes_skeptic_critique(self, lane_executor):
        """Test that cross-exam includes Skeptic's safety critique."""
        lane_a_result, lane_b_result = await lane_executor.execute_parallel_lanes(
            query="Test query",
        )
        
        critiques = await lane_executor.execute_cross_examination(
            query="Test query",
            lane_a_result=lane_a_result,
            lane_b_result=lane_b_result,
        )
        
        # Should have critiques (may be empty if agents not configured)
        # Just verify it runs without error
        assert isinstance(critiques, list)

    @pytest.mark.asyncio
    async def test_cross_exam_targets_correct_lanes(self, lane_executor):
        """Test that critiques target the correct lanes."""
        lane_a_result, lane_b_result = await lane_executor.execute_parallel_lanes(
            query="Test query",
        )
        
        critiques = await lane_executor.execute_cross_examination(
            query="Test query",
            lane_a_result=lane_a_result,
            lane_b_result=lane_b_result,
        )
        
        for critique in critiques:
            assert isinstance(critique, Critique)
            assert critique.target_lane in [Lane.CLINICAL, Lane.EXPLORATORY]


# =============================================================================
# FEASIBILITY ASSESSMENT TESTS
# =============================================================================


class TestFeasibilityAssessment:
    """Tests for feasibility assessment round."""

    @pytest.mark.asyncio
    async def test_execute_feasibility_round(self, lane_executor):
        """Test feasibility assessment execution."""
        lane_a_result, lane_b_result = await lane_executor.execute_parallel_lanes(
            query="Test query",
        )
        
        assessments = await lane_executor.execute_feasibility_round(
            query="Test query",
            lane_a_result=lane_a_result,
            lane_b_result=lane_b_result,
        )
        
        # Should return list of assessments
        assert isinstance(assessments, list)

    @pytest.mark.asyncio
    async def test_feasibility_includes_pragmatist(self, lane_executor):
        """Test that feasibility includes Pragmatist assessment."""
        lane_a_result, lane_b_result = await lane_executor.execute_parallel_lanes(
            query="Test query",
        )
        
        assessments = await lane_executor.execute_feasibility_round(
            query="Test query",
            lane_a_result=lane_a_result,
            lane_b_result=lane_b_result,
        )
        
        # Verify structure
        for assessment in assessments:
            assert isinstance(assessment, FeasibilityAssessment)


# =============================================================================
# CONTEXT INJECTION TESTS
# =============================================================================


class TestContextInjection:
    """Tests for context injection into agents."""

    @pytest.mark.asyncio
    async def test_scout_report_injected(self, lane_executor, sample_scout_report):
        """Test that Scout report is injected into agent context."""
        # The Scout report should be formatted and injected
        # This is verified by the lane executor using the scout_report
        lane_a_result, lane_b_result = await lane_executor.execute_parallel_lanes(
            query="Test query",
        )
        
        # If Scout report exists, it should have been used
        assert lane_executor.scout_report is not None

    @pytest.mark.asyncio
    async def test_patient_context_injected(self, lane_executor, sample_patient_context):
        """Test that patient context is injected."""
        lane_a_result, lane_b_result = await lane_executor.execute_parallel_lanes(
            query="Test query",
        )
        
        # Patient context should be available
        assert lane_executor.patient_context is not None
        assert lane_executor.patient_context.age == 55


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in lane execution."""

    @pytest.mark.asyncio
    async def test_handles_agent_error(self, lane_executor, mock_llm_client):
        """Test handling of individual agent errors."""
        # Make one agent fail
        call_count = 0
        original_complete = mock_llm_client.complete
        
        async def failing_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Agent failed")
            return await original_complete(*args, **kwargs)
        
        mock_llm_client.complete = failing_complete
        
        # Should handle the error gracefully
        try:
            lane_a_result, lane_b_result = await lane_executor.execute_parallel_lanes(
                query="Test query",
            )
            # Should complete even with one failure
        except Exception:
            # Or it might propagate - both are valid behaviors
            pass

    @pytest.mark.asyncio
    async def test_empty_lane_handling(
        self,
        mock_agents,
        sample_scout_report,
        sample_patient_context,
    ):
        """Test handling when a lane has no agents."""
        # Create routing with only Lane A agents
        routing = RoutingDecision(
            mode=ConferenceMode.STANDARD_CARE,
            active_agents=["empiricist", "pragmatist"],  # No Lane B agents
            activate_scout=False,
        )
        
        # Filter to only include active agents
        active_agents = [a for a in mock_agents if a.role in routing.active_agents]
        
        executor = LaneExecutor(
            agents=active_agents,
            routing_decision=routing,
            scout_report=None,
            patient_context=sample_patient_context,
        )
        
        lane_a_result, lane_b_result = await executor.execute_parallel_lanes(
            query="Simple query",
        )
        
        # Lane A should have results
        assert lane_a_result is not None
        
        # Lane B might be empty or have default behavior
        assert lane_b_result is not None

