"""Tests for cost tracking utilities."""

import pytest
from datetime import datetime

from src.llm.cost_tracker import CostTracker, ModelCost, APICallRecord


class TestModelCost:
    """Tests for ModelCost dataclass."""

    def test_create_model_cost(self):
        """Test creating a model cost entry."""
        cost = ModelCost(
            model_id="anthropic/claude-3.5-sonnet",
            display_name="Claude 3.5 Sonnet",
            cost_input_per_1k=0.003,
            cost_output_per_1k=0.015,
        )
        
        assert cost.model_id == "anthropic/claude-3.5-sonnet"
        assert cost.cost_input_per_1k == 0.003
        assert cost.cost_output_per_1k == 0.015


class TestCostTracker:
    """Tests for CostTracker."""

    def test_calculate_cost_with_known_model(self):
        """Test cost calculation for a model in the tracker."""
        tracker = CostTracker()
        tracker.model_costs["test/model"] = ModelCost(
            model_id="test/model",
            display_name="Test Model",
            cost_input_per_1k=0.01,  # $0.01 per 1K input tokens
            cost_output_per_1k=0.02,  # $0.02 per 1K output tokens
        )
        
        cost = tracker.calculate_cost(
            model="test/model",
            input_tokens=1000,
            output_tokens=500,
        )
        
        # 1000 input * $0.01/1K + 500 output * $0.02/1K = $0.01 + $0.01 = $0.02
        assert cost == pytest.approx(0.02)

    def test_calculate_cost_with_unknown_model(self):
        """Test cost calculation falls back to defaults for unknown model."""
        tracker = CostTracker()
        
        cost = tracker.calculate_cost(
            model="unknown/model",
            input_tokens=1000,
            output_tokens=1000,
        )
        
        # Should use default pricing
        assert cost > 0

    def test_record_call(self):
        """Test recording an API call."""
        tracker = CostTracker()
        
        record = tracker.record_call(
            model="test/model",
            input_tokens=100,
            output_tokens=50,
            context="agent_advocate",
        )
        
        assert isinstance(record, APICallRecord)
        assert record.model == "test/model"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.context == "agent_advocate"
        assert record.cost_usd > 0
        assert isinstance(record.timestamp, datetime)

    def test_get_total_cost(self):
        """Test getting total cost across calls."""
        tracker = CostTracker()
        
        tracker.record_call("model-a", 100, 50)
        tracker.record_call("model-a", 100, 50)
        tracker.record_call("model-b", 200, 100)
        
        total = tracker.get_total_cost()
        
        assert total > 0
        # Should be sum of all individual costs
        individual_sum = sum(r.cost_usd for r in tracker.call_records)
        assert total == pytest.approx(individual_sum)

    def test_get_total_tokens(self):
        """Test getting total token counts."""
        tracker = CostTracker()
        
        tracker.record_call("model", 100, 50)
        tracker.record_call("model", 200, 100)
        tracker.record_call("model", 300, 150)
        
        input_total, output_total = tracker.get_total_tokens()
        
        assert input_total == 600
        assert output_total == 300

    def test_get_summary(self):
        """Test getting usage summary."""
        tracker = CostTracker()
        
        tracker.record_call("model-a", 100, 50)
        tracker.record_call("model-a", 100, 50)
        tracker.record_call("model-b", 200, 100)
        
        summary = tracker.get_summary()
        
        assert summary["total_input_tokens"] == 400
        assert summary["total_output_tokens"] == 200
        assert summary["total_tokens"] == 600
        assert summary["num_calls"] == 3
        assert "model-a" in summary["by_model"]
        assert "model-b" in summary["by_model"]
        assert summary["by_model"]["model-a"]["calls"] == 2
        assert summary["by_model"]["model-b"]["calls"] == 1

    def test_reset(self):
        """Test resetting the tracker."""
        tracker = CostTracker()
        
        tracker.record_call("model", 100, 50)
        tracker.record_call("model", 100, 50)
        
        assert len(tracker.call_records) == 2
        
        tracker.reset()
        
        assert len(tracker.call_records) == 0
        assert tracker.get_total_cost() == 0

    def test_from_config(self):
        """Test loading tracker from config file."""
        # This will load from actual config file
        tracker = CostTracker.from_config("config/models.yaml")
        
        # Should have loaded models from config
        assert len(tracker.model_costs) > 0
        
        # Check a known model is loaded (updated to current models)
        assert "anthropic/claude-opus-4.5" in tracker.model_costs

    def test_from_config_missing_file(self):
        """Test loading tracker with missing config file."""
        tracker = CostTracker.from_config("nonexistent.yaml")
        
        # Should return empty tracker, not raise
        assert len(tracker.model_costs) == 0

