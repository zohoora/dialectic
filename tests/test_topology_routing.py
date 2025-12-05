"""
Tests for v3 topology routing.

Tests the automatic topology selection based on query patterns.
"""

import pytest
from src.routing.signals import (
    detect_topology_signals,
    get_topology_rationale,
    COMPARISON_PATTERNS,
    CONTENTIOUS_PATTERNS,
    HIGH_STAKES_PATTERNS,
    SOCRATIC_PATTERNS,
)


class TestTopologySignalPatterns:
    """Test that topology signal patterns are correctly defined."""
    
    def test_comparison_patterns_exist(self):
        """Test that comparison patterns list is populated."""
        assert len(COMPARISON_PATTERNS) > 0
        assert r"\bvs\.?\b" in COMPARISON_PATTERNS
    
    def test_contentious_patterns_exist(self):
        """Test that contentious patterns list is populated."""
        assert len(CONTENTIOUS_PATTERNS) > 0
        assert r"controversial" in CONTENTIOUS_PATTERNS
    
    def test_high_stakes_patterns_exist(self):
        """Test that high stakes patterns list is populated."""
        assert len(HIGH_STAKES_PATTERNS) > 0
        assert r"irreversible" in HIGH_STAKES_PATTERNS
    
    def test_socratic_patterns_exist(self):
        """Test that socratic patterns list is populated."""
        assert len(SOCRATIC_PATTERNS) > 0
        assert r"assuming" in SOCRATIC_PATTERNS


class TestTopologyDetection:
    """Test topology detection from query patterns."""
    
    def test_comparison_detects_oxford_debate(self):
        """Binary comparisons should recommend Oxford Debate."""
        signals, topology = detect_topology_signals(
            "Should I use metformin vs ozempic for this patient?"
        )
        assert topology == "oxford_debate"
        assert any("comparison:" in s for s in signals)
    
    def test_versus_detects_oxford_debate(self):
        """Explicit 'versus' should recommend Oxford Debate."""
        signals, topology = detect_topology_signals(
            "Adalimumab versus infliximab for Crohn's disease?"
        )
        assert topology == "oxford_debate"
    
    def test_which_is_better_detects_oxford_debate(self):
        """'Which is better' should recommend Oxford Debate."""
        signals, topology = detect_topology_signals(
            "Which is better for rheumatoid arthritis: MTX or biologics?"
        )
        assert topology == "oxford_debate"
    
    def test_controversial_detects_delphi(self):
        """Controversial topics should recommend Delphi Method."""
        signals, topology = detect_topology_signals(
            "This is a controversial topic with conflicting guidelines"
        )
        assert topology == "delphi_method"
        assert any("contentious:" in s for s in signals)
    
    def test_experts_disagree_detects_delphi(self):
        """Expert disagreement should recommend Delphi Method."""
        signals, topology = detect_topology_signals(
            "Experts disagree on the optimal approach here"
        )
        assert topology == "delphi_method"
    
    def test_surgery_detects_red_team(self):
        """Surgical procedures should recommend Red Team (with enough signals)."""
        signals, topology = detect_topology_signals(
            "Considering major surgery with irreversible consequences"
        )
        assert topology == "red_team_blue_team"
        assert any("high_stakes:" in s for s in signals)
    
    def test_experimental_procedure_detects_red_team(self):
        """Experimental procedures should recommend Red Team."""
        signals, topology = detect_topology_signals(
            "This experimental procedure is high-risk and could be fatal"
        )
        assert topology == "red_team_blue_team"
    
    def test_diagnostic_detects_socratic(self):
        """Diagnostic uncertainty should recommend Socratic Spiral."""
        signals, topology = detect_topology_signals(
            "Assuming this is autoimmune, what if it's something else? Depends on test results."
        )
        assert topology == "socratic_spiral"
        assert any("socratic:" in s for s in signals)
    
    def test_simple_query_defaults_to_free_discussion(self):
        """Simple queries without signals should default to free discussion."""
        signals, topology = detect_topology_signals(
            "What is the standard treatment for uncomplicated UTI?"
        )
        assert topology == "free_discussion"
        # Should have few or no signals
        assert len(signals) < 2
    
    def test_high_stakes_trumps_comparison(self):
        """High-stakes should take priority over comparison signals."""
        signals, topology = detect_topology_signals(
            "Surgery A vs Surgery B: which is less likely to be fatal and irreversible?"
        )
        # High stakes (2+ signals) should win
        assert topology == "red_team_blue_team"


class TestTopologyRationale:
    """Test topology rationale generation."""
    
    def test_oxford_debate_rationale(self):
        """Oxford debate should have appropriate rationale."""
        rationale = get_topology_rationale("oxford_debate", ["comparison:vs"])
        assert "comparison" in rationale.lower() or "debate" in rationale.lower()
    
    def test_delphi_rationale(self):
        """Delphi should have appropriate rationale."""
        rationale = get_topology_rationale("delphi_method", ["contentious:controversial"])
        assert "contentious" in rationale.lower() or "bias" in rationale.lower()
    
    def test_red_team_rationale(self):
        """Red team should have appropriate rationale."""
        rationale = get_topology_rationale("red_team_blue_team", ["high_stakes:surgery"])
        assert "high-stakes" in rationale.lower() or "safety" in rationale.lower()
    
    def test_socratic_rationale(self):
        """Socratic should have appropriate rationale."""
        rationale = get_topology_rationale("socratic_spiral", ["socratic:assuming"])
        assert "assumption" in rationale.lower() or "question" in rationale.lower()
    
    def test_free_discussion_rationale(self):
        """Free discussion should have appropriate rationale."""
        rationale = get_topology_rationale("free_discussion", [])
        assert "general" in rationale.lower() or "default" in rationale.lower()


class TestEdgeCases:
    """Test edge cases for topology detection."""
    
    def test_empty_query(self):
        """Empty query should default to free discussion."""
        signals, topology = detect_topology_signals("")
        assert topology == "free_discussion"
        assert len(signals) == 0
    
    def test_mixed_signals_priority(self):
        """When multiple signal types present, priority should be followed."""
        # Query with both comparison and high-stakes (2 high-stakes: surgical + high-risk)
        signals, topology = detect_topology_signals(
            "Drug A vs Drug B for this surgical patient who is high-risk"
        )
        # 2+ high-stakes signals should trigger red team (safety trumps comparison)
        assert topology == "red_team_blue_team"
        
        # But with only 1 high-stakes signal, comparison should win
        signals2, topology2 = detect_topology_signals(
            "Drug A vs Drug B for this surgical patient"
        )
        # Only 1 high-stakes signal (surgical), comparison should win
        assert topology2 == "oxford_debate"
    
    def test_case_insensitivity(self):
        """Pattern matching should be case insensitive."""
        signals1, topology1 = detect_topology_signals("METFORMIN VS OZEMPIC")
        signals2, topology2 = detect_topology_signals("metformin vs ozempic")
        assert topology1 == topology2 == "oxford_debate"
    
    def test_signals_returned_correctly(self):
        """Detected signals should be returned in the list."""
        signals, topology = detect_topology_signals("Treatment A versus Treatment B")
        assert len(signals) > 0
        # All signals should have format "type:pattern"
        for signal in signals:
            assert ":" in signal

