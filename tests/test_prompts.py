"""Tests for prompt loading utilities."""

import pytest
from pathlib import Path

from src.utils.prompt_loader import (
    load_prompt,
    format_prompt,
    build_agent_system_prompt,
    build_round_one_user_prompt,
    build_followup_round_prompt,
    build_arbitrator_prompt,
    get_available_roles,
    PROMPTS_DIR,
)


class TestLoadPrompt:
    """Tests for load_prompt function."""

    def test_load_advocate_prompt(self):
        """Test loading advocate prompt."""
        prompt = load_prompt("advocate", "agents")
        
        assert "The Advocate" in prompt
        assert "Recommended Approach" in prompt
        assert "Confidence Level" in prompt

    def test_load_skeptic_prompt(self):
        """Test loading skeptic prompt."""
        prompt = load_prompt("skeptic", "agents")
        
        assert "The Skeptic" in prompt
        assert "Key Concerns" in prompt
        assert "Risk Assessment" in prompt

    def test_load_empiricist_prompt(self):
        """Test loading empiricist prompt."""
        prompt = load_prompt("empiricist", "agents")
        
        assert "The Empiricist" in prompt
        assert "Evidence Assessment" in prompt
        assert "Evidence Quality" in prompt

    def test_load_arbitrator_prompt(self):
        """Test loading arbitrator prompt."""
        prompt = load_prompt("arbitrator", "agents")
        
        assert "The Arbitrator" in prompt
        assert "Synthesis Recommendation" in prompt
        assert "Preserved Dissent" in prompt

    def test_load_nonexistent_prompt_raises(self):
        """Test that loading nonexistent prompt raises error."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_prompt("nonexistent_role", "agents")
        
        assert "Prompt file not found" in str(exc_info.value)


class TestFormatPrompt:
    """Tests for format_prompt function."""

    def test_simple_substitution(self):
        """Test simple variable substitution."""
        template = "Hello {name}, welcome to {place}."
        result = format_prompt(template, name="Alice", place="the conference")
        
        assert result == "Hello Alice, welcome to the conference."

    def test_no_substitution_needed(self):
        """Test template with no variables."""
        template = "This is a static template."
        result = format_prompt(template)
        
        assert result == template

    def test_missing_variable_stays(self):
        """Test that missing variables are left as-is."""
        template = "Hello {name}, your role is {role}."
        result = format_prompt(template, name="Bob")
        
        assert result == "Hello Bob, your role is {role}."

    def test_numeric_substitution(self):
        """Test substitution with numeric values."""
        template = "Round {round} of {total}."
        result = format_prompt(template, round=1, total=3)
        
        assert result == "Round 1 of 3."


class TestBuildAgentSystemPrompt:
    """Tests for build_agent_system_prompt function."""

    def test_build_advocate_system_prompt(self):
        """Test building advocate system prompt."""
        prompt = build_agent_system_prompt("advocate")
        
        assert "The Advocate" in prompt
        assert "medical case conference" in prompt

    def test_build_skeptic_system_prompt(self):
        """Test building skeptic system prompt."""
        prompt = build_agent_system_prompt("skeptic")
        
        assert "The Skeptic" in prompt


class TestBuildRoundOneUserPrompt:
    """Tests for build_round_one_user_prompt function."""

    def test_includes_query(self):
        """Test that prompt includes the query."""
        query = "What is the best treatment for chronic pain?"
        prompt = build_round_one_user_prompt(query)
        
        assert query in prompt
        assert "Clinical Question" in prompt

    def test_includes_instructions(self):
        """Test that prompt includes instructions."""
        prompt = build_round_one_user_prompt("Test query")
        
        assert "analysis" in prompt.lower()
        assert "output format" in prompt.lower()


class TestBuildFollowupRoundPrompt:
    """Tests for build_followup_round_prompt function."""

    def test_includes_previous_responses(self):
        """Test that prompt includes previous responses."""
        query = "Test query"
        previous = {
            "advocate": "I recommend treatment A.",
            "skeptic": "I have concerns about treatment A.",
        }
        
        prompt = build_followup_round_prompt(query, previous, round_number=2)
        
        assert "treatment A" in prompt
        assert "Advocate" in prompt
        assert "Skeptic" in prompt

    def test_indicates_round_number(self):
        """Test that prompt indicates round number."""
        prompt = build_followup_round_prompt(
            "Query",
            {"agent": "Response"},
            round_number=3,
        )
        
        assert "Round 3" in prompt
        assert "Round 2" in prompt  # References previous round

    def test_includes_position_change_instruction(self):
        """Test that prompt mentions position changes."""
        prompt = build_followup_round_prompt(
            "Query",
            {"agent": "Response"},
            round_number=2,
        )
        
        assert "Position Changed" in prompt


class TestBuildArbitratorPrompt:
    """Tests for build_arbitrator_prompt function."""

    def test_includes_all_rounds(self):
        """Test that prompt includes all rounds."""
        query = "Test query"
        rounds = [
            {
                "advocate": "Round 1 advocate response",
                "skeptic": "Round 1 skeptic response",
            },
            {
                "advocate": "Round 2 advocate response",
                "skeptic": "Round 2 skeptic response",
            },
        ]
        
        prompt = build_arbitrator_prompt(query, rounds)
        
        assert "Round 1" in prompt
        assert "Round 2" in prompt
        assert "Round 1 advocate" in prompt
        assert "Round 2 skeptic" in prompt

    def test_includes_synthesis_instructions(self):
        """Test that prompt includes synthesis instructions."""
        prompt = build_arbitrator_prompt("Query", [{"agent": "Response"}])
        
        assert "synthesize" in prompt.lower()
        assert "dissent" in prompt.lower()


class TestGetAvailableRoles:
    """Tests for get_available_roles function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        roles = get_available_roles()
        
        assert isinstance(roles, list)

    def test_includes_expected_roles(self):
        """Test that list includes expected roles."""
        roles = get_available_roles()
        
        assert "advocate" in roles
        assert "skeptic" in roles
        assert "empiricist" in roles

    def test_excludes_arbitrator(self):
        """Test that arbitrator is excluded from agent roles."""
        roles = get_available_roles()
        
        # Arbitrator is handled separately
        assert "arbitrator" not in roles

