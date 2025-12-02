"""
Tests for PerturbationGenerator - creates query-specific fragility perturbations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json

from src.fragility.perturbation_generator import PerturbationGenerator
from src.models.conference import LLMResponse


# ============================================================================
# Initialization Tests
# ============================================================================

class TestPerturbationGeneratorInit:
    """Tests for PerturbationGenerator initialization."""
    
    def test_init_with_default_prompt(self, mock_llm_client):
        """Test initialization loads default prompt template."""
        generator = PerturbationGenerator(mock_llm_client)
        
        assert generator.llm_client == mock_llm_client
        assert generator.prompt_template is not None
        assert len(generator.prompt_template) > 0
    
    def test_init_with_custom_prompt_path(self, mock_llm_client, tmp_path):
        """Test initialization with custom prompt path."""
        custom_prompt = "Generate {num_perturbations} perturbations for {query} with {consensus}"
        prompt_file = tmp_path / "custom_prompt.md"
        prompt_file.write_text(custom_prompt)
        
        generator = PerturbationGenerator(mock_llm_client, prompt_path=prompt_file)
        
        assert generator.prompt_template == custom_prompt
    
    def test_init_with_missing_prompt_uses_default(self, mock_llm_client, tmp_path):
        """Test that missing prompt file falls back to default."""
        missing_path = tmp_path / "nonexistent.md"
        
        generator = PerturbationGenerator(mock_llm_client, prompt_path=missing_path)
        
        # Should have loaded default prompt
        assert "{query}" in generator.prompt_template
        assert "{consensus}" in generator.prompt_template
        assert "{num_perturbations}" in generator.prompt_template


# ============================================================================
# Generation Tests
# ============================================================================

class TestGenerate:
    """Tests for perturbation generation."""
    
    @pytest.mark.asyncio
    async def test_generate_parses_valid_json(self, mock_llm_client, mock_llm_response):
        """Test generation with valid JSON response."""
        json_response = json.dumps({
            "perturbations": [
                "What if the patient has renal impairment?",
                "What if the patient is elderly?",
                "What if the patient has drug allergies?",
            ]
        })
        mock_llm_client.complete = AsyncMock(return_value=mock_llm_response(json_response))
        
        generator = PerturbationGenerator(mock_llm_client)
        result = await generator.generate(
            query="Best treatment for hypertension?",
            consensus="Start with ACE inhibitor.",
            num_perturbations=3,
        )
        
        assert len(result) == 3
        assert "renal impairment" in result[0]
        assert "elderly" in result[1]
        assert "allergies" in result[2]
    
    @pytest.mark.asyncio
    async def test_generate_handles_markdown_wrapped_json(self, mock_llm_client, mock_llm_response):
        """Test parsing JSON wrapped in markdown code blocks."""
        response = """```json
{"perturbations": ["What if patient is pregnant?", "What if patient has liver disease?"]}
```"""
        mock_llm_client.complete = AsyncMock(return_value=mock_llm_response(response))
        
        generator = PerturbationGenerator(mock_llm_client)
        result = await generator.generate(
            query="Treatment for infection?",
            consensus="Use antibiotic X.",
            num_perturbations=2,
        )
        
        assert len(result) == 2
        assert "pregnant" in result[0]
        assert "liver" in result[1]
    
    @pytest.mark.asyncio
    async def test_generate_extracts_from_numbered_list(self, mock_llm_client, mock_llm_response):
        """Test extraction from numbered list when JSON parsing fails."""
        response = """Here are the perturbations:
1. What if the patient has chronic kidney disease?
2. What if the patient is on blood thinners?
3. What if the patient has a history of stroke?"""
        mock_llm_client.complete = AsyncMock(return_value=mock_llm_response(response))
        
        generator = PerturbationGenerator(mock_llm_client)
        result = await generator.generate(
            query="Anticoagulation therapy?",
            consensus="Start warfarin.",
            num_perturbations=3,
        )
        
        assert len(result) == 3
        assert "chronic kidney disease" in result[0]
        assert "blood thinners" in result[1]
        assert "stroke" in result[2]
    
    @pytest.mark.asyncio
    async def test_generate_extracts_from_bullet_list(self, mock_llm_client, mock_llm_response):
        """Test extraction from bullet point list."""
        response = """Perturbations:
- What if the patient has a pacemaker?
- What if the patient cannot tolerate oral medications?
* What if there are drug interactions?"""
        mock_llm_client.complete = AsyncMock(return_value=mock_llm_response(response))
        
        generator = PerturbationGenerator(mock_llm_client)
        result = await generator.generate(
            query="MRI recommendation?",
            consensus="Recommend MRI scan.",
            num_perturbations=3,
        )
        
        assert len(result) == 3
        assert "pacemaker" in result[0]
        assert "oral medications" in result[1]
        assert "drug interactions" in result[2]
    
    @pytest.mark.asyncio
    async def test_generate_uses_fallback_on_error(self, mock_llm_client):
        """Test that fallback perturbations are used when LLM call fails."""
        mock_llm_client.complete = AsyncMock(side_effect=Exception("API Error"))
        
        generator = PerturbationGenerator(mock_llm_client)
        result = await generator.generate(
            query="Treatment question?",
            consensus="Some recommendation.",
            num_perturbations=3,
        )
        
        # Should return fallback generic perturbations
        assert len(result) == 3
        assert all(isinstance(p, str) for p in result)
        assert all(len(p) > 10 for p in result)
    
    @pytest.mark.asyncio
    async def test_generate_uses_fallback_on_invalid_json(self, mock_llm_client, mock_llm_response):
        """Test fallback when JSON is completely invalid and no list items found."""
        response = "Sorry, I cannot generate perturbations."
        mock_llm_client.complete = AsyncMock(return_value=mock_llm_response(response))
        
        generator = PerturbationGenerator(mock_llm_client)
        result = await generator.generate(
            query="Test?",
            consensus="Test.",
            num_perturbations=2,
        )
        
        # Should return fallback perturbations
        assert len(result) == 2
        assert all(isinstance(p, str) for p in result)
    
    @pytest.mark.asyncio
    async def test_generate_passes_correct_model(self, mock_llm_client, mock_llm_response):
        """Test that the specified model is used."""
        mock_llm_client.complete = AsyncMock(return_value=mock_llm_response('{"perturbations": ["test"]}'))
        
        generator = PerturbationGenerator(mock_llm_client)
        await generator.generate(
            query="Test?",
            consensus="Test.",
            num_perturbations=1,
            model="anthropic/claude-3-opus",
        )
        
        mock_llm_client.complete.assert_called_once()
        call_kwargs = mock_llm_client.complete.call_args[1]
        assert call_kwargs["model"] == "anthropic/claude-3-opus"


# ============================================================================
# Parse Response Tests
# ============================================================================

class TestParseResponse:
    """Tests for response parsing."""
    
    def test_parse_valid_json(self, mock_llm_client):
        """Test parsing valid JSON response."""
        generator = PerturbationGenerator(mock_llm_client)
        content = '{"perturbations": ["A", "B", "C"]}'
        
        result = generator._parse_response(content, 3)
        
        assert result == ["A", "B", "C"]
    
    def test_parse_json_with_whitespace(self, mock_llm_client):
        """Test parsing JSON with surrounding whitespace."""
        generator = PerturbationGenerator(mock_llm_client)
        content = '   \n{"perturbations": ["A", "B"]}\n   '
        
        result = generator._parse_response(content, 2)
        
        assert result == ["A", "B"]
    
    def test_parse_filters_empty_perturbations(self, mock_llm_client):
        """Test that empty perturbations are filtered out."""
        generator = PerturbationGenerator(mock_llm_client)
        content = '{"perturbations": ["A", "", "B", "C"]}'
        
        result = generator._parse_response(content, 3)
        
        assert result == ["A", "B", "C"]


# ============================================================================
# Extract from Text Tests
# ============================================================================

class TestExtractFromText:
    """Tests for extracting perturbations from unstructured text."""
    
    def test_extract_numbered_items(self, mock_llm_client):
        """Test extraction of numbered list items."""
        generator = PerturbationGenerator(mock_llm_client)
        content = "1. First perturbation here\n2. Second perturbation here"
        
        result = generator._extract_from_text(content, 2)
        
        assert len(result) == 2
        assert "First perturbation" in result[0]
        assert "Second perturbation" in result[1]
    
    def test_extract_dash_bullets(self, mock_llm_client):
        """Test extraction of dash bullet points."""
        generator = PerturbationGenerator(mock_llm_client)
        content = "- First bullet point\n- Second bullet point"
        
        result = generator._extract_from_text(content, 2)
        
        assert len(result) == 2
    
    def test_extract_filters_short_items(self, mock_llm_client):
        """Test that very short items are filtered out."""
        generator = PerturbationGenerator(mock_llm_client)
        content = "1. OK\n2. This is a longer perturbation that should be kept"
        
        result = generator._extract_from_text(content, 2)
        
        # "OK" is too short (< 10 chars), should be filtered
        assert len(result) == 1
        assert "longer perturbation" in result[0]
    
    def test_extract_returns_fallback_when_no_items(self, mock_llm_client):
        """Test fallback when no valid items found."""
        generator = PerturbationGenerator(mock_llm_client)
        content = "This text has no list items."
        
        result = generator._extract_from_text(content, 3)
        
        # Should return fallback perturbations
        assert len(result) == 3


# ============================================================================
# Fallback Perturbations Tests
# ============================================================================

class TestFallbackPerturbations:
    """Tests for fallback perturbation generation."""
    
    def test_fallback_returns_requested_count(self, mock_llm_client):
        """Test that fallback returns requested number of perturbations."""
        generator = PerturbationGenerator(mock_llm_client)
        
        result = generator._fallback_perturbations(3)
        
        assert len(result) == 3
    
    def test_fallback_returns_medical_perturbations(self, mock_llm_client):
        """Test that fallback perturbations are medically relevant."""
        generator = PerturbationGenerator(mock_llm_client)
        
        result = generator._fallback_perturbations(5)
        
        # Check for common medical conditions
        all_text = " ".join(result).lower()
        assert any(term in all_text for term in ["renal", "elderly", "pregnant", "hepatic", "allergies"])
    
    def test_fallback_respects_max_count(self, mock_llm_client):
        """Test that fallback doesn't return more than available."""
        generator = PerturbationGenerator(mock_llm_client)
        
        result = generator._fallback_perturbations(100)
        
        # Should return at most the number of generic perturbations available (8)
        assert len(result) <= 8
        assert len(result) > 0
