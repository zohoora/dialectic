"""
Conference Engine - Main orchestrator for the AI Case Conference system.

This module ties together all conference components:
- Agents with epistemic roles
- Round execution
- Arbitrator synthesis
- Grounding layer (citation verification)
- Fragility testing (stress testing recommendations)
- Token/cost tracking
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Protocol

from src.conference.agent import Agent


# ==============================================================================
# Progress Tracking System
# ==============================================================================

class ProgressStage(str, Enum):
    """Stages of conference execution for progress tracking."""
    INITIALIZING = "initializing"
    ROUND_START = "round_start"
    AGENT_THINKING = "agent_thinking"
    AGENT_COMPLETE = "agent_complete"
    ROUND_COMPLETE = "round_complete"
    GROUNDING = "grounding"
    ARBITRATION = "arbitration"
    FRAGILITY_START = "fragility_start"
    FRAGILITY_TEST = "fragility_test"
    COMPLETE = "complete"


@dataclass
class ProgressUpdate:
    """
    Progress update event for UI callbacks.
    
    Attributes:
        stage: Current stage of execution
        message: Human-readable status message
        percent: Overall progress percentage (0-100)
        detail: Optional extra information (agent role, round number, etc.)
    """
    stage: ProgressStage
    message: str
    percent: int
    detail: dict = field(default_factory=dict)


class ProgressCallback(Protocol):
    """Protocol for progress callback functions."""
    
    def __call__(self, update: ProgressUpdate) -> None:
        """Called with progress updates during conference execution."""
        ...
from src.conference.arbitrator import ArbitratorEngine
from src.conference.round_executor import RoundExecutor
from src.conference.topologies.base import TopologyFactory
from src.fragility.tester import FragilityTester
from src.grounding.engine import GroundingEngine
from src.llm.cost_tracker import CostTracker
from src.models.conference import (
    AgentConfig,
    ConferenceConfig,
    ConferenceResult,
    ConferenceRound,
    ConferenceSynthesis,
    DissentRecord,
    LLMResponse,
    TokenUsage,
)
from src.models.fragility import FragilityReport
from src.models.grounding import GroundingReport


logger = logging.getLogger(__name__)


class LLMClientProtocol(Protocol):
    """Protocol for LLM client."""
    
    async def complete(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        ...
    
    def get_session_usage(self) -> dict:
        ...
    
    def reset_session(self):
        ...


class ConferenceEngine:
    """
    Main orchestrator for running AI case conferences.
    
    Manages the complete conference lifecycle:
    1. Initialize agents from configuration
    2. Execute deliberation rounds
    3. Run grounding layer (citation verification)
    4. Run arbitrator synthesis
    5. Track tokens and costs
    6. Package final results
    """
    
    def __init__(
        self, 
        llm_client: LLMClientProtocol,
        grounding_engine: Optional[GroundingEngine] = None,
    ):
        """
        Initialize the conference engine.
        
        Args:
            llm_client: LLM client for all API calls
            grounding_engine: Optional grounding engine for citation verification
        """
        self.llm_client = llm_client
        self.grounding_engine = grounding_engine
        self.cost_tracker = CostTracker.from_config()
    
    async def run_conference(
        self,
        query: str,
        config: ConferenceConfig,
        conference_id: Optional[str] = None,
        enable_grounding: bool = True,
        enable_fragility: bool = True,
        fragility_tests: int = 3,
        agent_injection_prompts: Optional[dict[str, str]] = None,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
    ) -> ConferenceResult:
        """
        Execute a complete case conference.
        
        Args:
            query: The clinical question to deliberate
            config: Conference configuration (agents, topology, rounds)
            conference_id: Optional ID for this conference (auto-generated if not provided)
            enable_grounding: Whether to run citation verification (default: True)
            enable_fragility: Whether to run fragility testing (default: True)
            fragility_tests: Number of perturbations to test (default: 3)
            agent_injection_prompts: Optional dict of agent_id -> injection prompt to prepend
            progress_callback: Optional callback for live progress updates
        
        Returns:
            ConferenceResult with all rounds, synthesis, and metadata
        """
        # Helper to safely call progress callback
        def report_progress(stage: ProgressStage, message: str, percent: int, **detail):
            if progress_callback:
                progress_callback(ProgressUpdate(
                    stage=stage,
                    message=message,
                    percent=percent,
                    detail=detail,
                ))
        
        # Generate conference ID if not provided
        if conference_id is None:
            conference_id = f"conf_{uuid.uuid4().hex[:12]}"
        
        # Reset tracking for this conference
        self.llm_client.reset_session()
        self.cost_tracker.reset()
        
        # Track timing
        start_time = time.time()
        
        # Report: Initializing
        report_progress(
            ProgressStage.INITIALIZING,
            "Initializing conference...",
            5,
            num_agents=len(config.agents),
            num_rounds=config.num_rounds,
        )
        
        # Initialize agents
        agents = self._create_agents(config)
        
        # Calculate progress allocation:
        # - Rounds: 60% (split among rounds)
        # - Grounding: 10%
        # - Arbitration: 15%
        # - Fragility: 10%
        # - Complete: 5%
        rounds_percent = 60
        grounding_percent = 10 if enable_grounding and self.grounding_engine else 0
        arbitration_percent = 15
        fragility_percent = 10 if enable_fragility else 0
        
        # Create topology-specific executor
        try:
            topology = TopologyFactory.create(config.topology, agents)
            logger.info(f"Using topology: {topology.name}")
            
            # Report topology info
            report_progress(
                ProgressStage.INITIALIZING,
                f"Using {topology.name} topology...",
                7,
                topology=topology.name,
                description=topology.description,
            )
            
            # Execute rounds using topology
            rounds = await topology.execute_all_rounds(
                query=query,
                num_rounds=config.num_rounds,
                agent_injection_prompts=agent_injection_prompts,
                progress_callback=progress_callback,
                base_percent=7,  # Starting after topology init
                percent_allocation=rounds_percent - 2,  # Adjusted for topology init
            )
        except ValueError as e:
            # Fall back to RoundExecutor if topology fails
            logger.warning(f"Topology creation failed: {e}, falling back to free discussion")
            
            # Notify user of fallback
            if progress_callback:
                progress_callback(ProgressUpdate(
                    stage=ProgressStage.INITIALIZING,
                    message=f"Note: {config.topology} topology unavailable, using free discussion",
                    percent=5,
                    detail={"fallback": True, "reason": str(e)},
                ))
            
            round_executor = RoundExecutor(agents)
            rounds = await round_executor.execute_all_rounds(
                query=query,
                num_rounds=config.num_rounds,
                agent_injection_prompts=agent_injection_prompts,
                progress_callback=progress_callback,
                base_percent=5,
                percent_allocation=rounds_percent,
            )
        
        current_percent = 5 + rounds_percent
        
        # Record token usage from rounds
        self._record_round_costs(rounds)
        
        # Run grounding layer if enabled
        grounding_report = None
        if enable_grounding and self.grounding_engine:
            report_progress(
                ProgressStage.GROUNDING,
                "Verifying citations against PubMed...",
                current_percent,
            )
            grounding_report = await self._run_grounding(rounds)
            current_percent += grounding_percent
            logger.info(
                f"Grounding complete: {grounding_report.total_citations} citations, "
                f"{len(grounding_report.citations_failed)} failed"
            )
            report_progress(
                ProgressStage.GROUNDING,
                f"Citation verification complete: {grounding_report.total_citations} citations checked",
                current_percent,
                verified=len(grounding_report.citations_verified),
                failed=len(grounding_report.citations_failed),
            )
        
        # Run arbitrator synthesis
        report_progress(
            ProgressStage.ARBITRATION,
            "Arbitrator synthesizing discussion...",
            current_percent,
            model=config.arbitrator.model.split("/")[-1],
        )
        
        arbitrator = ArbitratorEngine(config.arbitrator, self.llm_client)
        synthesis, dissent, arb_response = await arbitrator.synthesize(
            query=query,
            rounds=rounds,
        )
        current_percent += arbitration_percent
        
        report_progress(
            ProgressStage.ARBITRATION,
            f"Synthesis complete: {synthesis.confidence:.0%} confidence",
            current_percent,
            confidence=synthesis.confidence,
            has_dissent=dissent.preserved,
        )
        
        # Record arbitrator costs
        self.cost_tracker.record_call(
            model=config.arbitrator.model,
            input_tokens=arb_response.input_tokens,
            output_tokens=arb_response.output_tokens,
            context="arbitrator",
        )
        
        # Run fragility testing if enabled
        fragility_report = None
        if enable_fragility:
            report_progress(
                ProgressStage.FRAGILITY_START,
                f"Starting fragility testing ({fragility_tests} perturbations)...",
                current_percent,
                num_tests=fragility_tests,
            )
            
            fragility_report = await self._run_fragility_testing(
                query=query,
                consensus=synthesis.final_consensus,
                model=config.arbitrator.model,
                num_tests=fragility_tests,
                progress_callback=progress_callback,
                base_percent=current_percent,
                percent_allocation=fragility_percent,
            )
            current_percent += fragility_percent
            
            logger.info(
                f"Fragility testing complete: {fragility_report.perturbations_tested} tests, "
                f"survival rate: {fragility_report.survival_rate:.0%}"
            )
        
        # Calculate final timing
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Compile token usage
        token_usage = self._compile_token_usage()
        
        # Report: Complete
        report_progress(
            ProgressStage.COMPLETE,
            "Conference complete!",
            100,
            duration_ms=duration_ms,
            total_tokens=token_usage.total_tokens,
        )
        
        return ConferenceResult(
            conference_id=conference_id,
            query=query,
            config=config,
            rounds=rounds,
            synthesis=synthesis,
            dissent=dissent,
            grounding_report=grounding_report,
            fragility_report=fragility_report,
            token_usage=token_usage,
            duration_ms=duration_ms,
        )
    
    async def _run_fragility_testing(
        self,
        query: str,
        consensus: str,
        model: str,
        num_tests: int = 3,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
        base_percent: int = 0,
        percent_allocation: int = 10,
    ) -> FragilityReport:
        """
        Run fragility testing on the consensus recommendation.
        
        Args:
            query: Original clinical question
            consensus: The consensus recommendation to test
            model: LLM model to use for testing
            num_tests: Number of perturbations to test
            progress_callback: Optional callback for progress updates
            base_percent: Starting percent for progress
            percent_allocation: Percent of total progress to allocate
            
        Returns:
            FragilityReport with test results
        """
        tester = FragilityTester(self.llm_client)
        return await tester.test_consensus(
            query=query,
            consensus=consensus,
            model=model,
            num_tests=num_tests,
            progress_callback=progress_callback,
            base_percent=base_percent,
            percent_allocation=percent_allocation,
        )
    
    async def _run_grounding(self, rounds: list[ConferenceRound]) -> GroundingReport:
        """
        Run grounding layer on all round responses.
        
        Args:
            rounds: List of conference rounds with agent responses
            
        Returns:
            Combined GroundingReport for all rounds
        """
        # Collect all response texts
        all_texts = []
        for round_result in rounds:
            for agent_id, response in round_result.agent_responses.items():
                all_texts.append(response.content)
        
        # Verify citations across all texts
        report = await self.grounding_engine.verify_multiple_texts(all_texts)
        
        # Store individual round reports
        for round_result in rounds:
            round_texts = [
                resp.content for resp in round_result.agent_responses.values()
            ]
            round_report = await self.grounding_engine.verify_multiple_texts(round_texts)
            round_result.grounding_results = round_report
        
        return report
    
    def _create_agents(self, config: ConferenceConfig) -> list[Agent]:
        """Create agent instances from configuration."""
        agents = []
        for agent_config in config.agents:
            agent = Agent(agent_config, self.llm_client)
            agents.append(agent)
        return agents
    
    def _record_round_costs(self, rounds: list[ConferenceRound]):
        """Record costs from all round responses."""
        for round_result in rounds:
            for agent_id, response in round_result.agent_responses.items():
                self.cost_tracker.record_call(
                    model=response.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    context=f"agent_{agent_id}_round_{round_result.round_number}",
                )
    
    def _compile_token_usage(self) -> TokenUsage:
        """Compile final token usage statistics."""
        summary = self.cost_tracker.get_summary()
        
        return TokenUsage(
            total_input_tokens=summary["total_input_tokens"],
            total_output_tokens=summary["total_output_tokens"],
            total_tokens=summary["total_tokens"],
            estimated_cost_usd=summary["total_cost_usd"],
        )
    
    def get_cost_breakdown(self) -> dict:
        """Get detailed cost breakdown by model and role."""
        return self.cost_tracker.get_summary()


def create_default_config(
    advocate_model: str = "anthropic/claude-3.5-sonnet",
    skeptic_model: str = "openai/gpt-4o",
    empiricist_model: str = "openai/gpt-4o-mini",
    arbitrator_model: str = "anthropic/claude-3.5-sonnet",
    num_rounds: int = 2,
    topology: str = "free_discussion",
    mechanist_model: Optional[str] = None,
    patient_voice_model: Optional[str] = None,
    active_agents: Optional[dict[str, str]] = None,
) -> ConferenceConfig:
    """
    Create a default conference configuration.
    
    Args:
        advocate_model: Model for the Advocate agent (ignored if active_agents provided)
        skeptic_model: Model for the Skeptic agent (ignored if active_agents provided)
        empiricist_model: Model for the Empiricist agent (ignored if active_agents provided)
        arbitrator_model: Model for the Arbitrator
        num_rounds: Number of deliberation rounds
        topology: Conference topology (free_discussion, oxford_debate, delphi_method, 
                  socratic_spiral, red_team_blue_team)
        mechanist_model: Model for the Mechanist agent (optional)
        patient_voice_model: Model for the Patient Voice agent (optional)
        active_agents: Dict of role -> model for active agents (overrides individual args)
    
    Returns:
        ConferenceConfig with default settings
    """
    from src.models.conference import AgentRole, ArbitratorConfig, ConferenceTopology
    
    # Map string to enum
    topology_map = {
        "free_discussion": ConferenceTopology.FREE_DISCUSSION,
        "oxford_debate": ConferenceTopology.OXFORD_DEBATE,
        "delphi_method": ConferenceTopology.DELPHI_METHOD,
        "socratic_spiral": ConferenceTopology.SOCRATIC_SPIRAL,
        "red_team_blue_team": ConferenceTopology.RED_TEAM_BLUE_TEAM,
    }
    topology_enum = topology_map.get(topology, ConferenceTopology.FREE_DISCUSSION)
    
    # Role configuration: (role_enum, temperature)
    role_configs = {
        "advocate": (AgentRole.ADVOCATE, 0.7),
        "skeptic": (AgentRole.SKEPTIC, 0.7),
        "empiricist": (AgentRole.EMPIRICIST, 0.5),
        "mechanist": (AgentRole.MECHANIST, 0.5),
        "patient_voice": (AgentRole.PATIENT_VOICE, 0.6),
    }
    
    # Build agents list
    agents = []
    
    if active_agents:
        # Use active_agents dict
        for role, model in active_agents.items():
            if role in role_configs:
                role_enum, temp = role_configs[role]
                agents.append(AgentConfig(
                    agent_id=role,
                    role=role_enum,
                    model=model,
                    temperature=temp,
                ))
    else:
        # Fall back to individual model args
        agents.append(AgentConfig(
            agent_id="advocate",
            role=AgentRole.ADVOCATE,
            model=advocate_model,
            temperature=0.7,
        ))
        agents.append(AgentConfig(
            agent_id="skeptic",
            role=AgentRole.SKEPTIC,
            model=skeptic_model,
            temperature=0.7,
        ))
        agents.append(AgentConfig(
            agent_id="empiricist",
            role=AgentRole.EMPIRICIST,
            model=empiricist_model,
            temperature=0.5,
        ))
        if mechanist_model:
            agents.append(AgentConfig(
                agent_id="mechanist",
                role=AgentRole.MECHANIST,
                model=mechanist_model,
                temperature=0.5,
            ))
        if patient_voice_model:
            agents.append(AgentConfig(
                agent_id="patient_voice",
                role=AgentRole.PATIENT_VOICE,
                model=patient_voice_model,
                temperature=0.6,
            ))
    
    return ConferenceConfig(
        topology=topology_enum,
        num_rounds=num_rounds,
        agents=agents,
        arbitrator=ArbitratorConfig(
            model=arbitrator_model,
            temperature=0.5,
        ),
    )

