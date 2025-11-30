"""
Cost tracking utilities for LLM usage.

Provides cost calculation based on model pricing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import yaml


@dataclass
class ModelCost:
    """Cost structure for a model."""
    
    model_id: str
    display_name: str
    cost_input_per_1k: float  # Cost per 1K input tokens
    cost_output_per_1k: float  # Cost per 1K output tokens


@dataclass
class APICallRecord:
    """Record of a single API call."""
    
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    context: str = ""  # e.g., "agent_advocate", "arbitrator"


@dataclass
class CostTracker:
    """
    Tracks costs across LLM API calls.
    
    Loads model pricing from config and calculates costs.
    """
    
    model_costs: dict[str, ModelCost] = field(default_factory=dict)
    call_records: list[APICallRecord] = field(default_factory=list)
    
    @classmethod
    def from_config(cls, config_path: str = "config/models.yaml") -> "CostTracker":
        """Load cost tracker from config file."""
        tracker = cls()
        
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            for model_key, model_data in config.get("models", {}).items():
                tracker.model_costs[model_data["id"]] = ModelCost(
                    model_id=model_data["id"],
                    display_name=model_data.get("display_name", model_key),
                    cost_input_per_1k=model_data.get("cost_input", 0.0),
                    cost_output_per_1k=model_data.get("cost_output", 0.0),
                )
        except FileNotFoundError:
            # Use defaults if config not found
            pass
        
        return tracker
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for a single API call.
        
        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        
        Returns:
            Estimated cost in USD
        """
        if model in self.model_costs:
            costs = self.model_costs[model]
            input_cost = (input_tokens / 1000) * costs.cost_input_per_1k
            output_cost = (output_tokens / 1000) * costs.cost_output_per_1k
            return input_cost + output_cost
        
        # Default pricing if model not in config
        # Use conservative estimates
        default_input_per_1k = 0.005
        default_output_per_1k = 0.015
        input_cost = (input_tokens / 1000) * default_input_per_1k
        output_cost = (output_tokens / 1000) * default_output_per_1k
        return input_cost + output_cost
    
    def record_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        context: str = "",
    ) -> APICallRecord:
        """
        Record an API call and calculate its cost.
        
        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            context: Optional context (e.g., agent role)
        
        Returns:
            The created APICallRecord
        """
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        
        record = APICallRecord(
            timestamp=datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            context=context,
        )
        
        self.call_records.append(record)
        return record
    
    def get_total_cost(self) -> float:
        """Get total cost across all recorded calls."""
        return sum(r.cost_usd for r in self.call_records)
    
    def get_total_tokens(self) -> tuple[int, int]:
        """Get total input and output tokens."""
        input_total = sum(r.input_tokens for r in self.call_records)
        output_total = sum(r.output_tokens for r in self.call_records)
        return input_total, output_total
    
    def get_summary(self) -> dict:
        """
        Get a summary of usage and costs.
        
        Returns:
            Dict with total tokens, cost, and breakdown by model
        """
        input_total, output_total = self.get_total_tokens()
        
        by_model: dict[str, dict] = {}
        for record in self.call_records:
            if record.model not in by_model:
                by_model[record.model] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
            by_model[record.model]["calls"] += 1
            by_model[record.model]["input_tokens"] += record.input_tokens
            by_model[record.model]["output_tokens"] += record.output_tokens
            by_model[record.model]["cost_usd"] += record.cost_usd
        
        return {
            "total_input_tokens": input_total,
            "total_output_tokens": output_total,
            "total_tokens": input_total + output_total,
            "total_cost_usd": self.get_total_cost(),
            "num_calls": len(self.call_records),
            "by_model": by_model,
        }
    
    def reset(self):
        """Clear all recorded calls."""
        self.call_records = []

