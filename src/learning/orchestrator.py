"""
Conference Orchestrator - Ties together classification, library, bandit, and injection.

This is the main entry point for running an "intelligent" conference that:
1. Classifies the query
2. Retrieves relevant heuristics
3. Selects optimal configuration via bandit
4. Injects heuristics into agent prompts
5. Runs the conference
6. Records feedback for learning
"""

import logging
from pathlib import Path
from typing import Optional

from src.models.conference import ConferenceConfig, ConferenceResult
from src.models.experience import InjectionResult
from src.conference.engine import ConferenceEngine
from src.grounding.engine import GroundingEngine
from src.fragility.tester import FragilityTester
from src.learning.classifier import ClassifiedQuery, QueryClassifier
from src.learning.gatekeeper import Gatekeeper
from src.learning.library import ExperienceLibrary
from src.learning.injector import HeuristicInjector
from src.learning.optimizer import ConfigurationOptimizer, FeedbackCollector
from src.learning.surgeon import Surgeon
from src.llm.client import LLMClient


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


class ConferenceOrchestrator:
    """
    Main orchestrator for intelligent conference execution.
    
    Integrates:
    - Query classification
    - Experience Library retrieval
    - Configuration optimization (bandit)
    - Heuristic injection
    - Conference execution
    - Learning feedback loop
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
        self.llm_client = llm_client or LLMClient()
        self.data_dir = data_dir or Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.classifier = QueryClassifier(llm_client=self.llm_client)
        self.library = ExperienceLibrary(
            storage_path=self.data_dir / "experience_library.json"
        )
        self.optimizer = ConfigurationOptimizer(
            storage_path=self.data_dir / "optimizer_state.json"
        )
        self.feedback_collector = FeedbackCollector(
            storage_path=self.data_dir / "feedback.json"
        )
        self.injector = HeuristicInjector(self.library)
        self.gatekeeper = Gatekeeper()
        self.surgeon = Surgeon(self.llm_client)
        
        logger.info("ConferenceOrchestrator initialized with all components")
    
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
        Run a fully orchestrated conference.
        
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
        classification = self.classifier.classify(query)
        logger.info(
            f"Query classified: type={classification.query_type}, "
            f"domain={classification.domain}, complexity={classification.complexity}"
        )
        
        # Step 2: Get relevant heuristics
        injection_result = self.injector.get_injection_for_query(classification)
        logger.info(
            f"Injection result: {len(injection_result.heuristics)} heuristics, "
            f"genesis={injection_result.genesis_mode}"
        )
        
        # Step 3: Select or validate configuration
        config_selected_by_bandit = False
        if config is None:
            # Use default config for now - bandit selection needs available configs
            config = ConferenceEngine.create_default_config()
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
        fragility_tester = FragilityTester(self.llm_client) if enable_fragility else None
        
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
    ):
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
            # Check if heuristic was validated in responses
            # This is a simplified check - could be more sophisticated
            outcome = self._check_heuristic_outcome(result, h.heuristic_id)
            if outcome:
                self.injector.record_heuristic_outcome(h.heuristic_id, outcome)
    
    def _check_heuristic_outcome(
        self,
        result: ConferenceResult,
        heuristic_id: str,
    ) -> Optional[str]:
        """
        Check how a heuristic was used in the conference.
        
        Returns "accepted", "rejected", "modified", or None if not found.
        """
        # Look through all responses for validation markers
        for round_result in result.rounds:
            for response in round_result.agent_responses.values():
                content = response.content.lower()
                
                if heuristic_id.lower() in content:
                    if "decision: incorporate" in content:
                        return "accepted"
                    elif "decision: reject" in content:
                        return "rejected"
                    elif "decision: modify" in content:
                        return "modified"
        
        return None
    
    def record_feedback(
        self,
        conference_id: str,
        useful: Optional[str] = None,
        will_act: Optional[str] = None,
        dissent_useful: Optional[bool] = None,
    ):
        """
        Record immediate feedback for a conference.
        
        Args:
            conference_id: ID of the conference
            useful: "yes", "partially", "no"
            will_act: "yes", "modified", "no"
            dissent_useful: Whether dissent was useful
        """
        self.feedback_collector.record_immediate(
            conference_id,
            useful=useful,
            will_act=will_act,
            dissent_useful=dissent_useful,
        )
        
        # Update bandit if we have outcome
        outcome = self.feedback_collector.get_outcome(conference_id)
        if outcome is not None:
            # Would need to store classification with conference for proper update
            logger.info(f"Feedback recorded for {conference_id}: outcome={outcome:.2f}")
    
    def get_stats(self) -> dict:
        """Get orchestrator statistics."""
        return {
            "library_stats": self.library.get_stats(),
            "optimizer_stats": self.optimizer.get_stats(),
            "feedback_count": len(self.feedback_collector.feedback),
        }

