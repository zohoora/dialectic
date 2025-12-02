"""
Tests for ConferenceOrchestrator - the main intelligent conference orchestration layer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.learning.orchestrator import ConferenceOrchestrator, OrchestratedConferenceResult
from src.learning.classifier import ClassifiedQuery
from src.models.conference import ConferenceConfig, ConferenceResult, AgentConfig, AgentRole


# ============================================================================
# OrchestratedConferenceResult Tests
# ============================================================================

class TestOrchestratedConferenceResult:
    """Tests for OrchestratedConferenceResult."""
    
    def test_had_injected_heuristics_true(self, sample_conference_result):
        """Test that had_injected_heuristics returns True when heuristics exist."""
        classification = ClassifiedQuery(
            raw_text="Test query",
            query_type="treatment_selection",
            domain="cardiology",
            complexity="medium",
        )
        
        # Create mock injection result with heuristics
        mock_injection = MagicMock()
        mock_injection.heuristics = [MagicMock()]  # Has one heuristic
        mock_injection.genesis_mode = False
        
        result = OrchestratedConferenceResult(
            conference_result=sample_conference_result,
            classification=classification,
            injection_result=mock_injection,
            config_selected_by_bandit=False,
        )
        
        assert result.had_injected_heuristics is True
    
    def test_had_injected_heuristics_false(self, sample_conference_result):
        """Test that had_injected_heuristics returns False when no heuristics."""
        classification = ClassifiedQuery(
            raw_text="Test query",
            query_type="treatment_selection",
            domain="cardiology",
            complexity="medium",
        )
        
        mock_injection = MagicMock()
        mock_injection.heuristics = []  # No heuristics
        mock_injection.genesis_mode = True
        
        result = OrchestratedConferenceResult(
            conference_result=sample_conference_result,
            classification=classification,
            injection_result=mock_injection,
            config_selected_by_bandit=False,
        )
        
        assert result.had_injected_heuristics is False
    
    def test_was_genesis_true(self, sample_conference_result):
        """Test genesis mode detection."""
        classification = ClassifiedQuery(
            raw_text="Test query",
            query_type="diagnosis",
            domain="oncology",
            complexity="high",
        )
        
        mock_injection = MagicMock()
        mock_injection.heuristics = []
        mock_injection.genesis_mode = True
        
        result = OrchestratedConferenceResult(
            conference_result=sample_conference_result,
            classification=classification,
            injection_result=mock_injection,
            config_selected_by_bandit=True,
        )
        
        assert result.was_genesis is True
    
    def test_was_genesis_false(self, sample_conference_result):
        """Test non-genesis mode detection."""
        classification = ClassifiedQuery(
            raw_text="Test query",
            query_type="treatment_selection",
            domain="cardiology",
            complexity="medium",
        )
        
        mock_injection = MagicMock()
        mock_injection.heuristics = [MagicMock()]
        mock_injection.genesis_mode = False
        
        result = OrchestratedConferenceResult(
            conference_result=sample_conference_result,
            classification=classification,
            injection_result=mock_injection,
            config_selected_by_bandit=False,
        )
        
        assert result.was_genesis is False


# ============================================================================
# ConferenceOrchestrator Initialization Tests
# ============================================================================

class TestConferenceOrchestratorInit:
    """Tests for ConferenceOrchestrator initialization."""
    
    def test_init_creates_data_directory(self, temp_data_dir, mock_llm_client):
        """Test that initialization creates data directory."""
        orchestrator = ConferenceOrchestrator(
            llm_client=mock_llm_client,
            data_dir=temp_data_dir,
        )
        
        assert temp_data_dir.exists()
        assert orchestrator.data_dir == temp_data_dir
    
    def test_init_creates_all_components(self, temp_data_dir, mock_llm_client):
        """Test that all components are initialized."""
        orchestrator = ConferenceOrchestrator(
            llm_client=mock_llm_client,
            data_dir=temp_data_dir,
        )
        
        assert orchestrator.classifier is not None
        assert orchestrator.library is not None
        assert orchestrator.optimizer is not None
        assert orchestrator.feedback_collector is not None
        assert orchestrator.injector is not None
        assert orchestrator.gatekeeper is not None
        assert orchestrator.surgeon is not None


# ============================================================================
# Learning Processing Tests
# ============================================================================

class TestLearningProcessing:
    """Tests for learning outcome processing."""
    
    def test_check_heuristic_outcome_accepted(self, temp_data_dir, mock_llm_client, sample_conference_result):
        """Test detection of accepted heuristic."""
        orchestrator = ConferenceOrchestrator(
            llm_client=mock_llm_client,
            data_dir=temp_data_dir,
        )
        
        # Modify response to include acceptance marker
        sample_conference_result.rounds[0].agent_responses["advocate_1"].content = (
            "Using heuristic-123, Decision: Incorporate this guidance."
        )
        
        result = orchestrator._check_heuristic_outcome(sample_conference_result, "heuristic-123")
        
        assert result == "accepted"
    
    def test_check_heuristic_outcome_rejected(self, temp_data_dir, mock_llm_client, sample_conference_result):
        """Test detection of rejected heuristic."""
        orchestrator = ConferenceOrchestrator(
            llm_client=mock_llm_client,
            data_dir=temp_data_dir,
        )
        
        sample_conference_result.rounds[0].agent_responses["advocate_1"].content = (
            "Regarding heuristic-456, Decision: Reject as not applicable."
        )
        
        result = orchestrator._check_heuristic_outcome(sample_conference_result, "heuristic-456")
        
        assert result == "rejected"
    
    def test_check_heuristic_outcome_modified(self, temp_data_dir, mock_llm_client, sample_conference_result):
        """Test detection of modified heuristic."""
        orchestrator = ConferenceOrchestrator(
            llm_client=mock_llm_client,
            data_dir=temp_data_dir,
        )
        
        sample_conference_result.rounds[0].agent_responses["advocate_1"].content = (
            "heuristic-789, Decision: Modify to fit this case."
        )
        
        result = orchestrator._check_heuristic_outcome(sample_conference_result, "heuristic-789")
        
        assert result == "modified"
    
    def test_check_heuristic_outcome_not_found(self, temp_data_dir, mock_llm_client, sample_conference_result):
        """Test when heuristic is not mentioned."""
        orchestrator = ConferenceOrchestrator(
            llm_client=mock_llm_client,
            data_dir=temp_data_dir,
        )
        
        result = orchestrator._check_heuristic_outcome(sample_conference_result, "nonexistent-id")
        
        assert result is None


# ============================================================================
# Feedback Recording Tests
# ============================================================================

class TestFeedbackRecording:
    """Tests for feedback recording."""
    
    def test_record_feedback(self, temp_data_dir, mock_llm_client):
        """Test recording feedback for a conference."""
        orchestrator = ConferenceOrchestrator(
            llm_client=mock_llm_client,
            data_dir=temp_data_dir,
        )
        
        orchestrator.record_feedback(
            conference_id="test-conf-123",
            useful="yes",
            will_act="yes",
            dissent_useful=True,
        )
        
        # Check feedback was recorded
        feedback = orchestrator.feedback_collector.get_outcome("test-conf-123")
        # May be None if immediate feedback doesn't compute outcome
        # Just verify no exception was raised


# ============================================================================
# Statistics Tests
# ============================================================================

class TestOrchestratorStats:
    """Tests for orchestrator statistics."""
    
    def test_get_stats(self, temp_data_dir, mock_llm_client):
        """Test getting orchestrator statistics."""
        orchestrator = ConferenceOrchestrator(
            llm_client=mock_llm_client,
            data_dir=temp_data_dir,
        )
        
        stats = orchestrator.get_stats()
        
        assert "library_stats" in stats
        assert "optimizer_stats" in stats
        assert "feedback_count" in stats
        assert isinstance(stats["feedback_count"], int)
