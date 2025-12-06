"""
Conference Orchestrator (v1) - Learning-enabled v1 conference execution.

This module provides backwards-compatible orchestration for v1 conferences.
For new implementations, use ConferenceOrchestratorV3 from orchestrator_v3.py.
"""

import logging
from pathlib import Path
from typing import Optional

from src.conference.engine import ConferenceEngine
from src.grounding.engine import GroundingEngine
from src.learning.base_orchestrator import BaseOrchestrator
from src.llm.client import LLMClient
from src.models.conference import ConferenceConfig, ConferenceResult
from src.models.experience import InjectionResult
from src.learning.classifier import ClassifiedQuery


logger = logging.getLogger(__name__)


class OrchestratedConferenceResult:
    """Result from an orchestrated conference with all metadata."""
    
    def __init__(
        self,
        conference_result: ConferenceResult,
        classification: ClassifiedQuery,
        injection_result: InjectionResult,
        config_selected_by_bandit: bool,
    ):
        self.conference_result = conference_result
        self.classification = classification
        self.injection_result = injection_result
        self.config_selected_by_bandit = config_selected_by_bandit
    
    @property
    def had_injected_heuristics(self) -> bool:
        return len(self.injection_result.heuristics) > 0
    
    @property
    def was_genesis(self) -> bool:
        return self.injection_result.genesis_mode


class ConferenceOrchestrator(BaseOrchestrator):
    """
    Main orchestrator for intelligent v1 conference execution.
    
    Integrates:
    - Query classification
    - Experience Library retrieval
    - Configuration optimization (bandit)
    - Heuristic injection
    - Conference execution
    - Learning feedback loop
    
    Note: This is the v1 orchestrator. For v3 features (lanes, scout, etc.),
    use ConferenceOrchestratorV3.
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        data_dir: Optional[Path] = None,
    ):
        """
        Initialize the orchestrator with all components.
        
        Args:
            llm_client: LLM client (created if not provided)
            data_dir: Directory for persistent storage
        """
        super().__init__(llm_client, data_dir, data_suffix="")
        logger.info("ConferenceOrchestrator (v1) initialized with all components")
    
    async def run(
        self,
        query: str,
        config: Optional[ConferenceConfig] = None,
        enable_grounding: bool = True,
        enable_fragility: bool = True,
        enable_learning: bool = True,
        enable_injection: bool = True,
        fragility_tests: int = 3,
    ) -> OrchestratedConferenceResult:
        """
        Run a fully orchestrated v1 conference.
        
        Args:
            query: The clinical question
            config: Conference config (selected by bandit if not provided)
            enable_grounding: Enable citation verification
            enable_fragility: Enable fragility testing
            enable_learning: Enable gatekeeper/surgeon
            enable_injection: Enable heuristic injection
            fragility_tests: Number of fragility tests
            
        Returns:
            OrchestratedConferenceResult with all metadata
        """
        # Step 1: Classify the query
        classification = self._classify_query(query)
        
        # Step 2: Get relevant heuristics
        injection_result = self._get_heuristics(classification)
        
        # Step 3: Select or validate configuration
        config_selected_by_bandit = False
        if config is None:
            from src.conference.engine import create_default_config
            config = create_default_config()
            config_selected_by_bandit = True
            logger.info("Using default config (bandit selection pending available configs)")
        
        # Step 4: Build injection prompts for agents
        agent_injection_prompts = {}
        if enable_injection and injection_result.heuristics:
            for agent in config.agents:
                role = agent.role.value if hasattr(agent.role, 'value') else str(agent.role)
                agent_injection_prompts[agent.agent_id] = self.injector.build_agent_injection_prompt(
                    injection_result, role
                )
            logger.info(f"Built injection prompts for {len(agent_injection_prompts)} agents")
        
        # Step 5: Create and run conference engine
        grounding_engine = GroundingEngine() if enable_grounding else None
        
        engine = ConferenceEngine(
            llm_client=self.llm_client,
            grounding_engine=grounding_engine,
        )
        
        # Run the conference
        result = await engine.run_conference(
            query=query,
            config=config,
            enable_grounding=enable_grounding,
            enable_fragility=enable_fragility,
            fragility_tests=fragility_tests,
            agent_injection_prompts=agent_injection_prompts,
        )
        
        # Step 6: Process learning outcomes
        if enable_learning:
            await self._process_learning(result, classification, injection_result)
        
        return OrchestratedConferenceResult(
            conference_result=result,
            classification=classification,
            injection_result=injection_result,
            config_selected_by_bandit=config_selected_by_bandit,
        )
    
    async def _process_learning(
        self,
        result: ConferenceResult,
        classification: ClassifiedQuery,
        injection_result: InjectionResult,
    ) -> None:
        """Process learning outcomes from conference."""
        
        # Evaluate with gatekeeper
        gk_output = self.gatekeeper.evaluate(result)
        logger.info(f"Gatekeeper: eligible={gk_output.eligible}, reason={gk_output.reason}")
        
        # Extract heuristic if eligible
        if gk_output.eligible:
            try:
                extraction = await self.surgeon.extract(result)
                if extraction.extraction_successful and extraction.artifact:
                    self.library.add(extraction.artifact)
                    logger.info(f"New heuristic extracted: {extraction.artifact.heuristic_id}")
            except Exception as e:
                logger.error(f"Heuristic extraction failed: {e}")
        
        # Record heuristic usage outcomes
        for h in injection_result.heuristics:
            outcome = self._check_heuristic_outcome(result, h.heuristic_id)
            if outcome:
                self.injector.record_heuristic_outcome(h.heuristic_id, outcome)
    
    def _check_heuristic_outcome(
        self,
        result: ConferenceResult,
        heuristic_id: str,
    ) -> Optional[str]:
        """
        Check how a heuristic was used in the v1 conference.
        
        Returns "accepted", "rejected", "modified", or None if not found.
        """
        for round_result in result.rounds:
            for response in round_result.agent_responses.values():
                outcome = self._check_heuristic_outcome_in_content(
                    response.content, heuristic_id
                )
                if outcome:
                    return outcome
        return None
