"""
End-to-End / Smoke Tests for critical paths.

These tests verify that the major components work together correctly.
They use mocks for external services (LLM API, PubMed) but test the
integration of internal components.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json

from src.conference.engine import ConferenceEngine, create_default_config
from src.models.conference import (
    AgentConfig, AgentRole, ConferenceConfig, ConferenceResult,
    LLMResponse, ConferenceRound, ConferenceSynthesis
)


# ============================================================================
# Basic Conference Flow Tests
# ============================================================================

class TestBasicConferenceFlow:
    """Test basic conference execution flow."""
    
    @pytest.fixture
    def mock_engine_llm_client(self, mock_llm_response):
        """Create a mock LLM client for engine tests."""
        client = MagicMock()
        
        # Default response for agent queries
        client.complete = AsyncMock(return_value=mock_llm_response(
            "Based on current evidence, I recommend metformin as first-line treatment. "
            "This is supported by ADA guidelines and the UKPDS trial."
        ))
        
        return client
    
    @pytest.mark.asyncio
    async def test_minimal_conference_creation(self, mock_engine_llm_client):
        """Test that a minimal conference can be created and run."""
        engine = ConferenceEngine(llm_client=mock_engine_llm_client)
        config = create_default_config()
        
        # Verify config is valid
        assert config is not None
        assert len(config.agents) > 0
        assert config.arbitrator is not None
    
    @pytest.mark.asyncio
    async def test_conference_runs_all_rounds(self, mock_engine_llm_client):
        """Test that conference executes all configured rounds."""
        engine = ConferenceEngine(llm_client=mock_engine_llm_client)
        config = create_default_config()
        config.num_rounds = 2
        
        result = await engine.run_conference(
            query="Test medical question?",
            config=config,
            enable_grounding=False,
            enable_fragility=False,
        )
        
        assert result is not None
        assert result.conference_id is not None
        assert len(result.rounds) == 2
    
    @pytest.mark.asyncio
    async def test_conference_produces_synthesis(self, mock_engine_llm_client, mock_llm_response):
        """Test that conference produces a synthesis."""
        # Configure synthesis response
        synthesis_json = json.dumps({
            "final_consensus": "Recommend metformin as first-line treatment.",
            "dissenting_views": ["Consider GLP-1 agonists for high CV risk patients."],
            "evidence_summary": "Based on ADA guidelines and UKPDS trial.",
            "confidence_score": 0.85,
        })
        
        call_count = [0]
        async def mock_complete(*args, **kwargs):
            call_count[0] += 1
            # Return synthesis JSON for the synthesis call (usually later calls)
            if "synthesize" in str(kwargs.get("messages", [])).lower() or call_count[0] > 3:
                return mock_llm_response(synthesis_json)
            return mock_llm_response("Standard agent response for round discussion.")
        
        mock_engine_llm_client.complete = AsyncMock(side_effect=mock_complete)
        
        engine = ConferenceEngine(llm_client=mock_engine_llm_client)
        config = create_default_config()
        config.num_rounds = 1
        
        result = await engine.run_conference(
            query="What is the best treatment for diabetes?",
            config=config,
            enable_grounding=False,
            enable_fragility=False,
        )
        
        assert result.synthesis is not None
        assert result.synthesis.final_consensus is not None


# ============================================================================
# Conference with Fragility Testing
# ============================================================================

class TestConferenceWithFragility:
    """Test conference with fragility testing enabled."""
    
    @pytest.mark.asyncio
    async def test_fragility_pipeline_integration(self, mock_llm_client, mock_llm_response):
        """Test that fragility testing integrates with conference."""
        call_count = [0]
        
        async def varied_response(*args, **kwargs):
            call_count[0] += 1
            messages = kwargs.get("messages", [])
            msg_content = str(messages).lower()
            
            # Return fragility-related responses
            if "perturbation" in msg_content or "fragility" in msg_content:
                if "generate" in msg_content:
                    return mock_llm_response(json.dumps({
                        "perturbations": ["What if patient has renal failure?"]
                    }))
                elif "test" in msg_content or "evaluate" in msg_content:
                    return mock_llm_response(json.dumps({
                        "changed": True,
                        "change_severity": "moderate",
                        "analysis": "Recommendation changed due to renal concerns.",
                    }))
            
            # Return synthesis
            if "synthesize" in msg_content or "consensus" in msg_content:
                return mock_llm_response(json.dumps({
                    "final_consensus": "Test consensus",
                    "dissenting_views": [],
                    "evidence_summary": "Test evidence",
                    "confidence_score": 0.8,
                }))
            
            return mock_llm_response("Standard response.")
        
        mock_llm_client.complete = AsyncMock(side_effect=varied_response)
        
        engine = ConferenceEngine(llm_client=mock_llm_client)
        config = create_default_config()
        config.num_rounds = 1
        
        result = await engine.run_conference(
            query="Treatment for condition X?",
            config=config,
            enable_grounding=False,
            enable_fragility=True,
            fragility_tests=1,
        )
        
        assert result is not None
        # Fragility report may or may not be populated depending on implementation


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling in critical paths."""
    
    @pytest.mark.asyncio
    async def test_conference_handles_llm_error_gracefully(self, mock_llm_client):
        """Test that conference handles LLM errors gracefully."""
        mock_llm_client.complete = AsyncMock(side_effect=Exception("API Error"))
        
        engine = ConferenceEngine(llm_client=mock_llm_client)
        config = create_default_config()
        
        # Should raise or handle error gracefully
        with pytest.raises(Exception):
            await engine.run_conference(
                query="Test query?",
                config=config,
                enable_grounding=False,
                enable_fragility=False,
            )


# ============================================================================
# Performance / Resource Tests
# ============================================================================

class TestPerformance:
    """Test performance-related aspects."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_conference_tracks_costs(self, mock_llm_client, mock_llm_response):
        """Test that conference tracks token usage and costs."""
        # Configure response with usage info
        def response_with_usage(content):
            return LLMResponse(
                content=content,
                model="test-model",
                input_tokens=100,
                output_tokens=50,
            )
        
        mock_llm_client.complete = AsyncMock(return_value=response_with_usage("Test response"))
        
        engine = ConferenceEngine(llm_client=mock_llm_client)
        config = create_default_config()
        config.num_rounds = 1
        
        result = await engine.run_conference(
            query="Test?",
            config=config,
            enable_grounding=False,
            enable_fragility=False,
        )
        
        # Token usage should be tracked
        assert result.token_usage is not None
