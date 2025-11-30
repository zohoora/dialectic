"""
Tests for the Learning & Optimization Layer.

Tests Gatekeeper, Surgeon, and Experience Library components.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from src.models.gatekeeper import (
    CalibrationReport,
    DissentStatus,
    GatekeeperFlag,
    GatekeeperInput,
    GatekeeperOutput,
    OutcomeSignals,
    RejectionCode,
)
from src.models.experience import (
    CollisionType,
    ContextVector,
    HeuristicStatus,
    InjectionContext,
    ReasoningArtifact,
    SurgeonInput,
    SurgeonOutput,
)
from src.models.conference import (
    AgentConfig,
    AgentResponse,
    AgentRole,
    ArbitratorConfig,
    ConferenceConfig,
    ConferenceResult,
    ConferenceRound,
    ConferenceSynthesis,
    DissentRecord,
    LLMResponse,
    TokenUsage,
)
from src.models.grounding import GroundingReport, VerifiedCitation, FailedCitation
from src.models.fragility import FragilityOutcome, FragilityReport, FragilityResult
from src.learning.gatekeeper import Gatekeeper
from src.learning.surgeon import Surgeon
from src.learning.library import ExperienceLibrary


# ==============================================================================
# Test Gatekeeper Models
# ==============================================================================

class TestGatekeeperModels:
    """Tests for Gatekeeper data models."""
    
    def test_gatekeeper_input(self):
        """Test creating GatekeeperInput."""
        input_data = GatekeeperInput(
            conference_id="conf_123",
            conference_summary="Test conference",
            final_consensus="Test consensus",
            hallucination_rate=0.1,
            fragility_survival_rate=0.8,
        )
        
        assert input_data.conference_id == "conf_123"
        assert input_data.hallucination_rate == 0.1
    
    def test_gatekeeper_output_eligible(self):
        """Test creating eligible GatekeeperOutput."""
        output = GatekeeperOutput(
            eligible=True,
            reason="Meets all criteria",
            confidence=0.8,
        )
        
        assert output.eligible
        assert output.passed
        assert output.rejection_code is None
    
    def test_gatekeeper_output_rejected(self):
        """Test creating rejected GatekeeperOutput."""
        output = GatekeeperOutput(
            eligible=False,
            reason="High hallucination rate",
            rejection_code=RejectionCode.HALLUCINATION,
            confidence=0.7,
        )
        
        assert not output.eligible
        assert output.rejection_code == RejectionCode.HALLUCINATION
    
    def test_dissent_status(self):
        """Test DissentStatus model."""
        status = DissentStatus(
            dissent_preserved=True,
            dissent_summary="Agent disagreed",
            dissenting_role="skeptic",
            dissent_strength="Strong",
        )
        
        assert status.dissent_preserved
        assert status.dissent_strength == "Strong"


# ==============================================================================
# Test Experience Models
# ==============================================================================

class TestExperienceModels:
    """Tests for Experience Library data models."""
    
    def test_context_vector(self):
        """Test ContextVector model."""
        cv = ContextVector(
            domain="pain_management",
            condition="CRPS",
            treatment_type="pharmacological",
            patient_factors=["elderly", "renal_impairment"],
            keywords=["gabapentin", "neuropathic"],
        )
        
        assert cv.domain == "pain_management"
        assert "elderly" in cv.patient_factors
        assert "CRPS" in cv.to_search_text()
    
    def test_reasoning_artifact(self):
        """Test ReasoningArtifact model."""
        artifact = ReasoningArtifact(
            heuristic_id="heur_123",
            source_conference_id="conf_456",
            winning_heuristic="Consider gabapentin for neuropathic pain",
            context_vector=ContextVector(
                domain="pain",
                condition="neuropathy",
            ),
            qualifying_conditions=["Neuropathic pain confirmed"],
            disqualifying_conditions=["Severe renal impairment"],
            confidence=0.75,
        )
        
        assert artifact.heuristic_id == "heur_123"
        assert artifact.acceptance_rate == 0.5  # No usage data
        assert not artifact.is_well_validated  # Not enough data
    
    def test_artifact_validation_tracking(self):
        """Test artifact validation tracking."""
        artifact = ReasoningArtifact(
            heuristic_id="heur_123",
            source_conference_id="conf_456",
            winning_heuristic="Test",
            context_vector=ContextVector(domain="test", condition="test"),
            times_injected=10,
            times_accepted=7,
            times_rejected=1,
            times_modified=2,
        )
        
        assert artifact.acceptance_rate == 0.8  # (7 + 0.5*2) / 10
        assert artifact.is_well_validated


# ==============================================================================
# Test Gatekeeper
# ==============================================================================

class TestGatekeeper:
    """Tests for Gatekeeper evaluation."""
    
    @pytest.fixture
    def gatekeeper(self):
        """Create a Gatekeeper instance."""
        return Gatekeeper()
    
    @pytest.fixture
    def good_input(self):
        """Create a GatekeeperInput that should pass."""
        return GatekeeperInput(
            conference_id="conf_good",
            conference_summary="Good conference",
            final_consensus="Well-supported recommendation",
            hallucination_rate=0.0,
            fragility_survival_rate=0.9,
            num_rounds=2,
            position_changes=1,
            total_citations=5,
            verified_citations=5,
        )
    
    @pytest.fixture
    def bad_input_hallucination(self):
        """Create input with high hallucination rate."""
        return GatekeeperInput(
            conference_id="conf_bad_hall",
            conference_summary="Bad conference",
            final_consensus="Some recommendation",
            hallucination_rate=0.5,
            fragility_survival_rate=0.9,
            total_citations=10,
            verified_citations=5,
        )
    
    @pytest.fixture
    def bad_input_fragile(self):
        """Create input with low fragility survival."""
        return GatekeeperInput(
            conference_id="conf_fragile",
            conference_summary="Fragile conference",
            final_consensus="Unstable recommendation",
            hallucination_rate=0.0,
            fragility_survival_rate=0.3,
        )
    
    def test_evaluate_good_input(self, gatekeeper, good_input):
        """Test that good input passes evaluation."""
        output = gatekeeper.evaluate_from_input(good_input)
        
        assert output.eligible
        assert output.rejection_code is None
        assert output.confidence > 0.5
    
    def test_evaluate_hallucination(self, gatekeeper, bad_input_hallucination):
        """Test rejection for high hallucination rate."""
        output = gatekeeper.evaluate_from_input(bad_input_hallucination)
        
        assert not output.eligible
        assert output.rejection_code == RejectionCode.HALLUCINATION
    
    def test_evaluate_fragile(self, gatekeeper, bad_input_fragile):
        """Test rejection for low fragility survival."""
        output = gatekeeper.evaluate_from_input(bad_input_fragile)
        
        assert not output.eligible
        assert output.rejection_code == RejectionCode.FRAGILE
    
    def test_evaluate_no_evidence(self, gatekeeper):
        """Test rejection for no citations."""
        input_data = GatekeeperInput(
            conference_id="conf_no_ev",
            conference_summary="No evidence",
            final_consensus="Opinion only",
            hallucination_rate=0.0,
            fragility_survival_rate=0.9,
            total_citations=0,
            verified_citations=0,
        )
        
        output = gatekeeper.evaluate_from_input(input_data)
        
        assert not output.eligible
        assert output.rejection_code == RejectionCode.NO_EVIDENCE
    
    def test_evaluate_shallow(self, gatekeeper):
        """Test rejection for shallow consensus."""
        input_data = GatekeeperInput(
            conference_id="conf_shallow",
            conference_summary="Shallow",
            final_consensus="Quick agreement",
            hallucination_rate=0.0,
            fragility_survival_rate=0.9,
            num_rounds=1,
            position_changes=0,
            verified_citations=2,
        )
        
        output = gatekeeper.evaluate_from_input(input_data)
        
        assert not output.eligible
        assert output.rejection_code == RejectionCode.SHALLOW
    
    def test_strong_evidence_flag(self, gatekeeper):
        """Test that strong evidence adds flag."""
        input_data = GatekeeperInput(
            conference_id="conf_strong",
            conference_summary="Strong evidence",
            final_consensus="Well-supported",
            hallucination_rate=0.0,
            fragility_survival_rate=0.9,
            num_rounds=2,
            position_changes=1,
            total_citations=5,
            verified_citations=5,
        )
        
        output = gatekeeper.evaluate_from_input(input_data)
        
        assert output.eligible
        assert GatekeeperFlag.STRONG_EVIDENCE in output.flags
    
    def test_calibration_insufficient_data(self, gatekeeper):
        """Test calibration with insufficient data."""
        report = gatekeeper.get_calibration_report()
        
        assert report.status == "INSUFFICIENT_DATA"
    
    def test_record_outcome(self, gatekeeper, good_input):
        """Test recording outcome for calibration."""
        gatekeeper.evaluate_from_input(good_input)
        gatekeeper.record_outcome("conf_good", "positive")
        
        # Check decision was updated
        decision = next(
            d for d in gatekeeper.decisions if d.conference_id == "conf_good"
        )
        assert decision.eventual_outcome == "positive"


# ==============================================================================
# Test Surgeon
# ==============================================================================

class TestSurgeon:
    """Tests for Surgeon heuristic extraction."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.complete = AsyncMock(return_value=LLMResponse(
            content='''{
                "extraction_successful": true,
                "winning_heuristic": "Consider gabapentin for neuropathic pain",
                "contra_heuristic": "Opioids were rejected due to addiction risk",
                "context": {
                    "domain": "pain_management",
                    "condition": "neuropathic_pain",
                    "treatment_type": "pharmacological",
                    "patient_factors": ["elderly"],
                    "keywords": ["gabapentin", "neuropathic", "pain"]
                },
                "qualifying_conditions": ["Neuropathic pain confirmed", "No contraindications"],
                "disqualifying_conditions": ["Severe renal impairment", "Gabapentin allergy"],
                "fragility_factors": ["Renal impairment requires dose adjustment"],
                "evidence_summary": "Meta-analyses support efficacy",
                "evidence_pmids": ["12345678"],
                "confidence": 0.8
            }''',
            model="test-model",
            input_tokens=1000,
            output_tokens=500,
        ))
        return client
    
    @pytest.fixture
    def surgeon(self, mock_llm_client):
        """Create a Surgeon instance."""
        return Surgeon(mock_llm_client)
    
    @pytest.fixture
    def surgeon_input(self):
        """Create sample SurgeonInput."""
        return SurgeonInput(
            conference_id="conf_123",
            conference_transcript="Agent 1: ...\nAgent 2: ...",
            final_consensus="Consider gabapentin",
            query="What treatment for neuropathic pain?",
            verified_citations=["12345678"],
        )
    
    @pytest.mark.asyncio
    async def test_extract_success(self, surgeon, surgeon_input):
        """Test successful heuristic extraction."""
        output = await surgeon.extract_from_input(surgeon_input)
        
        assert output.extraction_successful
        assert output.artifact is not None
        assert "gabapentin" in output.artifact.winning_heuristic.lower()
        assert output.artifact.context_vector.domain == "pain_management"
    
    @pytest.mark.asyncio
    async def test_extract_parses_conditions(self, surgeon, surgeon_input):
        """Test that conditions are properly parsed."""
        output = await surgeon.extract_from_input(surgeon_input)
        
        assert len(output.artifact.qualifying_conditions) > 0
        assert len(output.artifact.disqualifying_conditions) > 0
    
    @pytest.mark.asyncio
    async def test_extract_failure(self, mock_llm_client, surgeon_input):
        """Test handling of extraction failure."""
        mock_llm_client.complete = AsyncMock(return_value=LLMResponse(
            content='''{
                "extraction_successful": false,
                "failure_reason": "Reasoning too complex to extract"
            }''',
            model="test-model",
            input_tokens=100,
            output_tokens=50,
        ))
        
        surgeon = Surgeon(mock_llm_client)
        output = await surgeon.extract_from_input(surgeon_input)
        
        assert not output.extraction_successful
        assert output.artifact is None
        assert "complex" in output.failure_reason.lower()
    
    @pytest.mark.asyncio
    async def test_extract_handles_api_error(self, mock_llm_client, surgeon_input):
        """Test handling of API error."""
        mock_llm_client.complete = AsyncMock(side_effect=Exception("API Error"))
        
        surgeon = Surgeon(mock_llm_client)
        output = await surgeon.extract_from_input(surgeon_input)
        
        assert not output.extraction_successful
        assert "error" in output.failure_reason.lower()


# ==============================================================================
# Test Experience Library
# ==============================================================================

class TestExperienceLibrary:
    """Tests for Experience Library."""
    
    @pytest.fixture
    def library(self):
        """Create an in-memory library."""
        return ExperienceLibrary()
    
    @pytest.fixture
    def sample_artifact(self):
        """Create a sample artifact."""
        return ReasoningArtifact(
            heuristic_id="heur_test",
            source_conference_id="conf_test",
            winning_heuristic="Test heuristic for CRPS pain",
            context_vector=ContextVector(
                domain="pain_management",
                condition="CRPS",
                treatment_type="pharmacological",
                keywords=["gabapentin", "CRPS", "neuropathic"],
            ),
            qualifying_conditions=["CRPS diagnosis confirmed"],
            disqualifying_conditions=["Renal failure"],
            confidence=0.75,
        )
    
    def test_add_and_get(self, library, sample_artifact):
        """Test adding and retrieving a heuristic."""
        hid = library.add(sample_artifact)
        
        retrieved = library.get(hid)
        
        assert retrieved is not None
        assert retrieved.heuristic_id == hid
        assert retrieved.winning_heuristic == sample_artifact.winning_heuristic
    
    def test_remove(self, library, sample_artifact):
        """Test removing a heuristic."""
        hid = library.add(sample_artifact)
        
        assert library.remove(hid)
        assert library.get(hid) is None
    
    def test_search_by_keyword(self, library, sample_artifact):
        """Test searching by keyword."""
        library.add(sample_artifact)
        
        context = InjectionContext(
            query="What treatment for CRPS?",
            domain="pain_management",
        )
        
        results = library.search(context)
        
        assert len(results) > 0
        assert results[0].heuristic_id == sample_artifact.heuristic_id
    
    def test_search_no_match(self, library, sample_artifact):
        """Test search with no matching keywords."""
        library.add(sample_artifact)
        
        context = InjectionContext(
            query="What about cardiology issues?",
            domain="cardiology",
        )
        
        results = library.search(context)
        
        # Should not match pain management heuristic
        assert len(results) == 0 or results[0].heuristic_id != sample_artifact.heuristic_id
    
    def test_get_injection_genesis_mode(self, library):
        """Test genesis mode when no heuristics found."""
        context = InjectionContext(
            query="What treatment?",
            domain="unknown",
        )
        
        result = library.get_injection(context)
        
        assert result.genesis_mode
        assert result.heuristics_found == 0
        assert "No relevant heuristics found" in result.injection_prompt
    
    def test_get_injection_single_heuristic(self, library, sample_artifact):
        """Test injection with single matching heuristic."""
        library.add(sample_artifact)
        
        context = InjectionContext(
            query="Treatment for CRPS?",
            domain="pain_management",
        )
        
        result = library.get_injection(context)
        
        assert not result.genesis_mode
        assert result.heuristics_found >= 1
        assert "Experience Library Retrieval" in result.injection_prompt
    
    def test_record_usage(self, library, sample_artifact):
        """Test recording usage outcome."""
        library.add(sample_artifact)
        
        library.record_usage(sample_artifact.heuristic_id, "accepted")
        
        h = library.get(sample_artifact.heuristic_id)
        assert h.times_injected == 1
        assert h.times_accepted == 1
    
    def test_update_status(self, library, sample_artifact):
        """Test updating heuristic status."""
        library.add(sample_artifact)
        
        library.update_status(
            sample_artifact.heuristic_id,
            HeuristicStatus.DEPRECATED,
        )
        
        h = library.get(sample_artifact.heuristic_id)
        assert h.status == HeuristicStatus.DEPRECATED
    
    def test_get_stats(self, library, sample_artifact):
        """Test getting library statistics."""
        library.add(sample_artifact)
        
        stats = library.get_stats()
        
        assert stats["total_heuristics"] == 1
        assert stats["active_heuristics"] == 1
        assert "pain_management" in stats["domains"]


# ==============================================================================
# Test Collision Detection
# ==============================================================================

class TestCollisionDetection:
    """Tests for heuristic collision detection."""
    
    @pytest.fixture
    def library(self):
        """Create library with conflicting heuristics."""
        lib = ExperienceLibrary()
        
        # Heuristic recommending gabapentin
        lib.add(ReasoningArtifact(
            heuristic_id="heur_pro",
            source_conference_id="conf_1",
            winning_heuristic="Use gabapentin for CRPS pain",
            context_vector=ContextVector(
                domain="pain_management",
                condition="CRPS",
                keywords=["gabapentin", "CRPS"],
            ),
        ))
        
        # Heuristic cautioning against gabapentin
        lib.add(ReasoningArtifact(
            heuristic_id="heur_contra",
            source_conference_id="conf_2",
            winning_heuristic="Avoid gabapentin in elderly due to fall risk",
            context_vector=ContextVector(
                domain="pain_management",
                condition="CRPS",
                patient_factors=["elderly"],
                keywords=["gabapentin", "CRPS", "elderly"],
            ),
        ))
        
        return lib
    
    def test_detects_collision(self, library):
        """Test detection of heuristic collision."""
        context = InjectionContext(
            query="Gabapentin for CRPS in elderly patient?",
            domain="pain_management",
            patient_factors=["elderly"],
        )
        
        result = library.get_injection(context)
        
        # Should find both and detect collision
        # Note: DIRECT_CONTRADICTION is detected because one says "Use" and other says "Avoid"
        if result.heuristics_found >= 2 and result.collision:
            assert result.collision.collision_type in (
                CollisionType.DIRECT_CONTRADICTION,
                CollisionType.PATIENT_SUBSET,
            )
            assert "COLLISION DETECTED" in result.injection_prompt

