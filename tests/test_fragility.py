"""
Tests for the Fragility Testing module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models.fragility import (
    DEFAULT_MEDICAL_PERTURBATIONS,
    FragilityOutcome,
    FragilityReport,
    FragilityResult,
)
from src.models.conference import LLMResponse
from src.fragility.tester import FragilityTester


# ==============================================================================
# Test FragilityResult Model
# ==============================================================================

class TestFragilityResult:
    """Tests for FragilityResult model."""
    
    def test_create_survives_result(self):
        """Test creating a SURVIVES result."""
        result = FragilityResult(
            perturbation="What if patient has renal impairment?",
            outcome=FragilityOutcome.SURVIVES,
            explanation="The recommendation still applies with dose adjustment.",
        )
        
        assert result.perturbation == "What if patient has renal impairment?"
        assert result.outcome == FragilityOutcome.SURVIVES
        assert result.modified_recommendation is None
    
    def test_create_modifies_result(self):
        """Test creating a MODIFIES result."""
        result = FragilityResult(
            perturbation="What if patient is on anticoagulation?",
            outcome=FragilityOutcome.MODIFIES,
            explanation="Need to adjust for bleeding risk.",
            modified_recommendation="Consider withholding anticoagulation 5 days before procedure.",
        )
        
        assert result.outcome == FragilityOutcome.MODIFIES
        assert result.modified_recommendation is not None
    
    def test_create_collapses_result(self):
        """Test creating a COLLAPSES result."""
        result = FragilityResult(
            perturbation="What if patient is pregnant?",
            outcome=FragilityOutcome.COLLAPSES,
            explanation="Drug is contraindicated in pregnancy.",
        )
        
        assert result.outcome == FragilityOutcome.COLLAPSES


# ==============================================================================
# Test FragilityReport Model
# ==============================================================================

class TestFragilityReport:
    """Tests for FragilityReport model."""
    
    def test_empty_report(self):
        """Test empty report defaults."""
        report = FragilityReport()
        
        assert report.perturbations_tested == 0
        assert report.results == []
        assert report.survival_rate == 1.0
        assert report.fragility_level == "LOW"
    
    def test_all_survive(self):
        """Test report where all tests survive."""
        results = [
            FragilityResult(
                perturbation="Test 1",
                outcome=FragilityOutcome.SURVIVES,
                explanation="OK",
            ),
            FragilityResult(
                perturbation="Test 2",
                outcome=FragilityOutcome.SURVIVES,
                explanation="OK",
            ),
        ]
        
        report = FragilityReport(
            perturbations_tested=2,
            results=results,
        )
        
        assert len(report.survived) == 2
        assert len(report.modified) == 0
        assert len(report.collapsed) == 0
        assert report.survival_rate == 1.0
        assert report.fragility_level == "LOW"
        assert not report.is_fragile
    
    def test_mixed_results(self):
        """Test report with mixed outcomes."""
        results = [
            FragilityResult(
                perturbation="Test 1",
                outcome=FragilityOutcome.SURVIVES,
                explanation="OK",
            ),
            FragilityResult(
                perturbation="Test 2",
                outcome=FragilityOutcome.MODIFIES,
                explanation="Needs adjustment",
            ),
            FragilityResult(
                perturbation="Test 3",
                outcome=FragilityOutcome.COLLAPSES,
                explanation="Not valid",
            ),
        ]
        
        report = FragilityReport(
            perturbations_tested=3,
            results=results,
        )
        
        assert len(report.survived) == 1
        assert len(report.modified) == 1
        assert len(report.collapsed) == 1
        assert report.survival_rate == pytest.approx(1/3)
        assert report.fragility_level == "HIGH"
        assert report.is_fragile
    
    def test_moderate_fragility(self):
        """Test moderate fragility level."""
        results = [
            FragilityResult(perturbation="Test 1", outcome=FragilityOutcome.SURVIVES, explanation="OK"),
            FragilityResult(perturbation="Test 2", outcome=FragilityOutcome.SURVIVES, explanation="OK"),
            FragilityResult(perturbation="Test 3", outcome=FragilityOutcome.MODIFIES, explanation="Modified"),
            FragilityResult(perturbation="Test 4", outcome=FragilityOutcome.COLLAPSES, explanation="Failed"),
        ]
        
        report = FragilityReport(perturbations_tested=4, results=results)
        
        assert report.survival_rate == 0.5
        assert report.fragility_level == "MODERATE"


# ==============================================================================
# Test Default Perturbations
# ==============================================================================

class TestDefaultPerturbations:
    """Tests for default medical perturbations."""
    
    def test_default_perturbations_exist(self):
        """Test that default perturbations are defined."""
        assert len(DEFAULT_MEDICAL_PERTURBATIONS) > 0
    
    def test_perturbations_are_questions(self):
        """Test that perturbations are phrased as questions."""
        for perturbation in DEFAULT_MEDICAL_PERTURBATIONS:
            assert "?" in perturbation or "if" in perturbation.lower()
    
    def test_key_scenarios_covered(self):
        """Test that key clinical scenarios are covered."""
        combined = " ".join(DEFAULT_MEDICAL_PERTURBATIONS).lower()
        
        # Key scenarios that should be covered
        assert "renal" in combined
        assert "anticoagulation" in combined or "bleeding" in combined
        assert "pregnant" in combined
        assert "elderly" in combined or "75" in combined
        assert "cost" in combined


# ==============================================================================
# Test FragilityTester
# ==============================================================================

class TestFragilityTester:
    """Tests for FragilityTester class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.complete = AsyncMock(return_value=LLMResponse(
            content='{"outcome": "SURVIVES", "explanation": "The recommendation holds.", "modified_recommendation": null}',
            model="test-model",
            input_tokens=100,
            output_tokens=50,
        ))
        return client
    
    @pytest.fixture
    def tester(self, mock_llm_client):
        """Create a FragilityTester with mock client."""
        return FragilityTester(mock_llm_client)
    
    def test_init_default_perturbations(self, mock_llm_client):
        """Test initialization with default perturbations."""
        tester = FragilityTester(mock_llm_client)
        assert tester.perturbations == DEFAULT_MEDICAL_PERTURBATIONS
    
    def test_init_custom_perturbations(self, mock_llm_client):
        """Test initialization with custom perturbations."""
        custom = ["Custom test 1?", "Custom test 2?"]
        tester = FragilityTester(mock_llm_client, perturbations=custom)
        assert tester.perturbations == custom
    
    @pytest.mark.asyncio
    async def test_test_consensus_basic(self, tester, mock_llm_client):
        """Test basic consensus testing."""
        report = await tester.test_consensus(
            query="What treatment for CRPS?",
            consensus="Recommend gabapentin 300mg TID.",
            model="test-model",
            num_tests=2,
        )
        
        assert report.perturbations_tested == 2
        assert len(report.results) == 2
        assert mock_llm_client.complete.call_count == 2
    
    @pytest.mark.asyncio
    async def test_test_consensus_specific_perturbations(self, tester, mock_llm_client):
        """Test with specific perturbations."""
        specific = ["Test A?", "Test B?", "Test C?"]
        report = await tester.test_consensus(
            query="Query",
            consensus="Consensus",
            model="test-model",
            num_tests=3,
            specific_perturbations=specific,
        )
        
        assert report.perturbations_tested == 3
        # Verify the specific perturbations were used
        perturbations_used = [r.perturbation for r in report.results]
        assert set(perturbations_used) == set(specific)
    
    @pytest.mark.asyncio
    async def test_parse_json_response(self, mock_llm_client):
        """Test parsing valid JSON response."""
        mock_llm_client.complete = AsyncMock(return_value=LLMResponse(
            content='{"outcome": "MODIFIES", "explanation": "Needs dose adjustment.", "modified_recommendation": "Use lower dose."}',
            model="test-model",
            input_tokens=100,
            output_tokens=50,
        ))
        
        tester = FragilityTester(mock_llm_client)
        report = await tester.test_consensus(
            query="Query",
            consensus="Consensus",
            model="test-model",
            num_tests=1,
            specific_perturbations=["Test?"],
        )
        
        assert report.results[0].outcome == FragilityOutcome.MODIFIES
        assert "dose adjustment" in report.results[0].explanation
        assert report.results[0].modified_recommendation == "Use lower dose."
    
    @pytest.mark.asyncio
    async def test_parse_markdown_json_response(self, mock_llm_client):
        """Test parsing JSON wrapped in markdown code block."""
        mock_llm_client.complete = AsyncMock(return_value=LLMResponse(
            content='```json\n{"outcome": "COLLAPSES", "explanation": "Not safe.", "modified_recommendation": null}\n```',
            model="test-model",
            input_tokens=100,
            output_tokens=50,
        ))
        
        tester = FragilityTester(mock_llm_client)
        report = await tester.test_consensus(
            query="Query",
            consensus="Consensus",
            model="test-model",
            num_tests=1,
            specific_perturbations=["Test?"],
        )
        
        assert report.results[0].outcome == FragilityOutcome.COLLAPSES
    
    @pytest.mark.asyncio
    async def test_parse_invalid_json_fallback(self, mock_llm_client):
        """Test fallback parsing when JSON is invalid."""
        mock_llm_client.complete = AsyncMock(return_value=LLMResponse(
            content='The recommendation MODIFIES because of safety concerns.',
            model="test-model",
            input_tokens=100,
            output_tokens=50,
        ))
        
        tester = FragilityTester(mock_llm_client)
        report = await tester.test_consensus(
            query="Query",
            consensus="Consensus",
            model="test-model",
            num_tests=1,
            specific_perturbations=["Test?"],
        )
        
        # Should fallback to extracting outcome from text
        assert report.results[0].outcome == FragilityOutcome.MODIFIES
    
    @pytest.mark.asyncio
    async def test_handles_api_error(self, mock_llm_client):
        """Test handling of API errors."""
        mock_llm_client.complete = AsyncMock(side_effect=Exception("API Error"))
        
        tester = FragilityTester(mock_llm_client)
        report = await tester.test_consensus(
            query="Query",
            consensus="Consensus",
            model="test-model",
            num_tests=1,
            specific_perturbations=["Test?"],
        )
        
        # Should default to SURVIVES on error
        assert report.results[0].outcome == FragilityOutcome.SURVIVES
        assert "Error" in report.results[0].explanation
    
    def test_get_available_perturbations(self, tester):
        """Test getting available perturbations."""
        perturbations = tester.get_available_perturbations()
        assert perturbations == DEFAULT_MEDICAL_PERTURBATIONS
        # Verify it's a copy, not the original
        perturbations.append("New test")
        assert "New test" not in tester.perturbations
    
    def test_add_perturbation(self, tester):
        """Test adding a custom perturbation."""
        original_count = len(tester.perturbations)
        tester.add_perturbation("What if the patient has severe anxiety?")
        
        assert len(tester.perturbations) == original_count + 1
        assert "anxiety" in tester.perturbations[-1]
    
    def test_add_duplicate_perturbation(self, tester):
        """Test that duplicate perturbations are not added."""
        original_count = len(tester.perturbations)
        existing = tester.perturbations[0]
        tester.add_perturbation(existing)
        
        assert len(tester.perturbations) == original_count

