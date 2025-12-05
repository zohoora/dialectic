"""
Tests for v3 Conference Orchestrator with learning integration.

Tests the OrchestratorV3 components:
- LaneAwareInjector
- GatekeeperV3
- SurgeonV3
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.learning.orchestrator_v3 import (
    ConferenceOrchestratorV3,
    GatekeeperV3,
    LaneAwareInjector,
    OrchestratedV3Result,
    SurgeonV3,
)
from src.models.v2_schemas import (
    ArbitratorSynthesis,
    ClinicalConsensus,
    ExploratoryConsideration,
    Lane,
    LaneResult,
    RoutingDecision,
    Tension,
)
from src.models.experience import InjectionResult, ReasoningArtifact
from src.learning.library import ExperienceLibrary


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_library():
    """Create a mock experience library."""
    library = MagicMock(spec=ExperienceLibrary)
    library.get_stats.return_value = {"total_heuristics": 5}
    return library


@pytest.fixture
def lane_aware_injector(mock_library):
    """Create a LaneAwareInjector with mock library."""
    return LaneAwareInjector(mock_library)


@pytest.fixture
def mock_v2_result():
    """Create a mock V2ConferenceResult for testing."""
    result = MagicMock()
    result.conference_id = "test_conf_123"
    result.query = "What is the best treatment for diabetes?"
    
    # Mock synthesis
    result.synthesis = ArbitratorSynthesis(
        clinical_consensus=ClinicalConsensus(
            recommendation="Start metformin as first-line therapy",
            evidence_basis=["PMID:12345", "PMID:67890"],
            confidence=0.85,
            safety_profile="Generally well tolerated",
        ),
        exploratory_considerations=[
            ExploratoryConsideration(
                hypothesis="GLP-1 agonists may provide additional cardiovascular benefit",
                mechanism="GLP-1 receptor activation in cardiac tissue",
                evidence_level="early_clinical",
                potential_benefit="Weight loss + CV protection",
            ),
        ],
        tensions=[
            Tension(
                description="Cost vs efficacy debate",
                resolution="defer_to_clinical",
            ),
        ],
        overall_confidence=0.75,
        preserved_dissent=["Skeptic notes limited long-term data"],
    )
    
    # Mock lane results
    result.lane_a_result = LaneResult(
        lane=Lane.CLINICAL,
        agent_responses={
            "empiricist": MagicMock(role="empiricist", content="Evidence supports metformin..."),
            "skeptic": MagicMock(role="skeptic", content="I have some concerns about..."),
        },
    )
    
    result.lane_b_result = LaneResult(
        lane=Lane.EXPLORATORY,
        agent_responses={
            "mechanist": MagicMock(role="mechanist", content="The mechanism suggests..."),
        },
    )
    
    result.fragility_results = None
    
    return result


# =============================================================================
# LANE-AWARE INJECTOR TESTS
# =============================================================================


class TestLaneAwareInjector:
    """Tests for lane-aware heuristic injection."""
    
    def test_lane_a_roles_defined(self, lane_aware_injector):
        """Lane A roles should be defined."""
        assert "empiricist" in lane_aware_injector.LANE_A_ROLES
        assert "skeptic" in lane_aware_injector.LANE_A_ROLES
        assert "pragmatist" in lane_aware_injector.LANE_A_ROLES
        assert "patient_voice" in lane_aware_injector.LANE_A_ROLES
    
    def test_lane_b_roles_defined(self, lane_aware_injector):
        """Lane B roles should be defined."""
        assert "mechanist" in lane_aware_injector.LANE_B_ROLES
        assert "speculator" in lane_aware_injector.LANE_B_ROLES
    
    def test_no_overlap_between_lanes(self, lane_aware_injector):
        """Lane A and Lane B should not share roles."""
        overlap = lane_aware_injector.LANE_A_ROLES & lane_aware_injector.LANE_B_ROLES
        assert len(overlap) == 0
    
    def test_lane_a_guidance_contains_clinical_focus(self, lane_aware_injector):
        """Lane A guidance should mention clinical/evidence focus."""
        guidance = lane_aware_injector._get_lane_guidance(Lane.CLINICAL, "empiricist")
        assert "clinical" in guidance.lower() or "evidence" in guidance.lower()
    
    def test_lane_b_guidance_contains_exploratory_focus(self, lane_aware_injector):
        """Lane B guidance should mention exploratory/mechanism focus."""
        guidance = lane_aware_injector._get_lane_guidance(Lane.EXPLORATORY, "mechanist")
        assert "exploratory" in guidance.lower() or "mechanism" in guidance.lower()


# =============================================================================
# GATEKEEPER V3 TESTS
# =============================================================================


class TestGatekeeperV3:
    """Tests for v3 gatekeeper evaluation."""
    
    def test_eligible_result(self, mock_v2_result):
        """High-quality result should be eligible."""
        gk = GatekeeperV3()
        output = gk.evaluate_v3(mock_v2_result)
        
        assert output.eligible is True
        assert "quality" in output.reason.lower()
    
    def test_rejects_low_confidence(self, mock_v2_result):
        """Low confidence should not be eligible."""
        gk = GatekeeperV3()
        mock_v2_result.synthesis.overall_confidence = 0.3
        
        output = gk.evaluate_v3(mock_v2_result)
        
        assert output.eligible is False
        assert "confidence" in output.reason.lower()
    
    def test_rejects_low_clinical_confidence(self, mock_v2_result):
        """Low clinical consensus confidence should not be eligible."""
        gk = GatekeeperV3()
        mock_v2_result.synthesis.clinical_consensus.confidence = 0.4
        
        output = gk.evaluate_v3(mock_v2_result)
        
        assert output.eligible is False
        assert "clinical" in output.reason.lower()
    
    def test_rejects_no_synthesis(self, mock_v2_result):
        """Missing synthesis should not be eligible."""
        gk = GatekeeperV3()
        mock_v2_result.synthesis = None
        
        output = gk.evaluate_v3(mock_v2_result)
        
        assert output.eligible is False
        assert "synthesis" in output.reason.lower()
    
    def test_rejects_no_evidence(self, mock_v2_result):
        """Missing evidence basis should not be eligible."""
        gk = GatekeeperV3()
        mock_v2_result.synthesis.clinical_consensus.evidence_basis = []
        
        output = gk.evaluate_v3(mock_v2_result)
        
        assert output.eligible is False
        assert "evidence" in output.reason.lower()
    
    def test_rejects_too_many_unresolved_tensions(self, mock_v2_result):
        """Too many unresolved tensions should not be eligible."""
        gk = GatekeeperV3()
        mock_v2_result.synthesis.tensions = [
            Tension(description="Tension 1", resolution="unresolved"),
            Tension(description="Tension 2", resolution="unresolved"),
        ]
        
        output = gk.evaluate_v3(mock_v2_result)
        
        assert output.eligible is False
        assert "tension" in output.reason.lower()


# =============================================================================
# ORCHESTRATED RESULT TESTS
# =============================================================================


class TestOrchestratedV3Result:
    """Tests for OrchestratedV3Result dataclass."""
    
    def test_had_injected_heuristics_true(self, mock_v2_result):
        """Should return True when heuristics were injected."""
        injection_result = MagicMock(spec=InjectionResult)
        injection_result.heuristics = [MagicMock()]
        injection_result.genesis_mode = False
        
        result = OrchestratedV3Result(
            conference_result=mock_v2_result,
            classification=MagicMock(),
            injection_result=injection_result,
        )
        
        assert result.had_injected_heuristics is True
    
    def test_had_injected_heuristics_false(self, mock_v2_result):
        """Should return False when no heuristics were injected."""
        injection_result = MagicMock(spec=InjectionResult)
        injection_result.heuristics = []
        injection_result.genesis_mode = True
        
        result = OrchestratedV3Result(
            conference_result=mock_v2_result,
            classification=MagicMock(),
            injection_result=injection_result,
        )
        
        assert result.had_injected_heuristics is False
    
    def test_was_genesis(self, mock_v2_result):
        """Should return genesis mode status."""
        injection_result = MagicMock(spec=InjectionResult)
        injection_result.heuristics = []
        injection_result.genesis_mode = True
        
        result = OrchestratedV3Result(
            conference_result=mock_v2_result,
            classification=MagicMock(),
            injection_result=injection_result,
        )
        
        assert result.was_genesis is True
    
    def test_heuristic_extracted(self, mock_v2_result):
        """Should return extraction status from learning outcome."""
        injection_result = MagicMock(spec=InjectionResult)
        injection_result.heuristics = []
        injection_result.genesis_mode = False
        
        result = OrchestratedV3Result(
            conference_result=mock_v2_result,
            classification=MagicMock(),
            injection_result=injection_result,
            learning_outcome={"extracted": True},
        )
        
        assert result.heuristic_extracted is True


# =============================================================================
# INTEGRATION TESTS (would need mocked LLM)
# =============================================================================


class TestOrchestratorV3Integration:
    """Integration tests for the full orchestrator (require mocking)."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initializes(self, tmp_path):
        """Orchestrator should initialize without errors."""
        with patch('src.learning.orchestrator_v3.LLMClient'):
            orchestrator = ConferenceOrchestratorV3(
                data_dir=tmp_path,
            )
            
            assert orchestrator.library is not None
            assert orchestrator.injector is not None
            assert orchestrator.gatekeeper is not None
            assert orchestrator.surgeon is not None
    
    def test_get_stats(self, tmp_path):
        """get_stats should return structured data."""
        with patch('src.learning.orchestrator_v3.LLMClient'):
            orchestrator = ConferenceOrchestratorV3(
                data_dir=tmp_path,
            )
            
            stats = orchestrator.get_stats()
            
            assert "library_stats" in stats
            assert "optimizer_stats" in stats
            assert "feedback_count" in stats
            assert "speculation_stats" in stats

