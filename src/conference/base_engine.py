"""
Base Conference Engine - Shared functionality for all engine implementations.

This module provides the common infrastructure used by both v1 (ConferenceEngine)
and v2/v3 (ConferenceEngineV2) implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from src.conference.agent import Agent
from src.llm.cost_tracker import CostTracker
from src.models.conference import (
    AgentConfig,
    ConferenceConfig,
    ConferenceRound,
    TokenUsage,
)
from src.models.progress import ProgressCallback, ProgressStage, ProgressUpdate
from src.utils.protocols import LLMClientProtocol


logger = logging.getLogger(__name__)


class BaseConferenceEngine(ABC):
    """
    Abstract base class for conference engines.
    
    Provides shared functionality:
    - LLM client management
    - Cost tracking
    - Agent creation
    - Token usage compilation
    - Progress reporting helpers
    """
    
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        grounding_engine: Optional[Any] = None,
    ):
        """
        Initialize the base engine.
        
        Args:
            llm_client: LLM client for all API calls
            grounding_engine: Optional grounding engine for citation verification
        """
        self.llm_client = llm_client
        self.grounding_engine = grounding_engine
        self.cost_tracker = CostTracker.from_config()
    
    def _create_agents(
        self,
        config: ConferenceConfig,
        include_librarian: bool = False,
        routing_decision: Optional[Any] = None,
    ) -> list[Agent]:
        """
        Create agent instances from configuration.
        
        Args:
            config: Conference configuration with agent configs
            include_librarian: Whether to include librarian query instructions
            routing_decision: Optional routing decision to filter agents
            
        Returns:
            List of Agent instances
        """
        agents = []
        
        # Get active roles if routing decision provided
        active_roles = None
        if routing_decision and hasattr(routing_decision, 'active_agents'):
            active_roles = set(routing_decision.active_agents)
        
        for agent_config in config.agents:
            # Get role string for comparison
            role_str = (
                agent_config.role 
                if isinstance(agent_config.role, str) 
                else agent_config.role.value
            )
            
            # Filter by routing decision if applicable
            if active_roles is not None:
                if role_str not in active_roles and role_str != "arbitrator":
                    continue
            
            agent = Agent(
                agent_config,
                self.llm_client,
                include_librarian=include_librarian,
            )
            agents.append(agent)
        
        return agents
    
    def _record_round_costs(self, rounds: list[ConferenceRound]) -> None:
        """
        Record costs from all round responses.
        
        Args:
            rounds: List of conference rounds with agent responses
        """
        for round_result in rounds:
            for agent_id, response in round_result.agent_responses.items():
                self.cost_tracker.record_call(
                    model=response.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    context=f"agent_{agent_id}_round_{round_result.round_number}",
                )
    
    def _compile_token_usage(self) -> TokenUsage:
        """
        Compile final token usage statistics.
        
        Returns:
            TokenUsage with total counts and estimated cost
        """
        summary = self.cost_tracker.get_summary()
        
        return TokenUsage(
            total_input_tokens=summary.get("total_input_tokens", 0),
            total_output_tokens=summary.get("total_output_tokens", 0),
            total_tokens=summary.get("total_tokens", 0),
            estimated_cost_usd=summary.get("total_cost_usd", 0.0),
        )
    
    def _reset_tracking(self) -> None:
        """Reset session and cost tracking for a new conference."""
        self.llm_client.reset_session()
        self.cost_tracker.reset()
    
    def get_cost_breakdown(self) -> dict:
        """
        Get detailed cost breakdown by model and role.
        
        Returns:
            Dict with cost breakdown
        """
        return self.cost_tracker.get_summary()
    
    @staticmethod
    def create_progress_reporter(
        callback: Optional[Callable[[ProgressUpdate], None]],
    ) -> Callable:
        """
        Create a progress reporting helper function.
        
        Args:
            callback: Optional progress callback
            
        Returns:
            Function that safely reports progress
        """
        def report(
            stage: ProgressStage,
            message: str,
            percent: int,
            **detail: Any,
        ) -> None:
            if callback:
                callback(ProgressUpdate(
                    stage=stage,
                    message=message,
                    percent=percent,
                    detail=detail,
                ))
        
        return report

