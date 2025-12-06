"""
Conference Orchestrator v3 - Learning-enabled v3 conference execution.

Extends the v3 conference engine with:
1. Query classification
2. Experience Library retrieval (lane-aware)
3. Heuristic injection (clinical vs exploratory)
4. Learning feedback loop (Gatekeeper + Surgeon)
5. Speculation Library integration

This orchestrator wraps ConferenceEngineV2 (which handles v2.1 and v3)
and adds the learning layer that was missing from the direct engine usage.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from src.conference.engine_v2 import ConferenceEngineV2, V2ConferenceResult
from src.grounding.engine import GroundingEngine
from src.learning.classifier import ClassifiedQuery
from src.learning.gatekeeper import GatekeeperV3
from src.learning.injector import LaneAwareInjector
from src.learning.surgeon import SurgeonV3
from src.llm.client import LLMClient
from src.models.conference import ConferenceConfig
from src.models.enums import Lane
from src.models.experience import InjectionResult
from src.models.progress import ProgressStage, ProgressUpdate
from src.models.patient import PatientContext
from src.speculation.library import SpeculationLibrary


logger = logging.getLogger(__name__)


# Aliases for backwards compatibility
V2ProgressStage = ProgressStage
V2ProgressUpdate = ProgressUpdate


# =============================================================================
# MODEL CONFIGURATION
# =============================================================================


@dataclass
class V3ModelConfig:
    """
    Configuration for which LLM models to use for each v3 component.
    
    This allows fine-grained control over model selection:
    - Use fast/cheap models for classification
    - Use powerful models for synthesis and extraction
    - Use specialized models for specific tasks
    """
    
    # Routing model - determines conference mode and topology
    router_model: str = "openai/gpt-4o"
    
    # Classifier model - categorizes queries for learning (fast, cheap)
    classifier_model: str = "anthropic/claude-3-haiku"
    
    # Surgeon model - extracts heuristics from conferences
    surgeon_model: str = "anthropic/claude-sonnet-4"
    
    # Scout model - analyzes literature search results
    scout_model: str = "openai/gpt-4o"
    
    # Validator model - validates speculations against evidence
    validator_model: str = "openai/gpt-4o"
    
    @classmethod
    def from_dict(cls, data: dict) -> "V3ModelConfig":
        """Create config from dict (e.g., from API request)."""
        return cls(
            router_model=data.get("router_model", cls.router_model),
            classifier_model=data.get("classifier_model", cls.classifier_model),
            surgeon_model=data.get("surgeon_model", cls.surgeon_model),
            scout_model=data.get("scout_model", cls.scout_model),
            validator_model=data.get("validator_model", cls.validator_model),
        )


# =============================================================================
# RESULT TYPES
# =============================================================================


@dataclass
class OrchestratedV3Result:
    """Result from an orchestrated v3 conference with all metadata."""
    
    conference_result: V2ConferenceResult
    classification: ClassifiedQuery
    injection_result: InjectionResult
    learning_outcome: dict = field(default_factory=dict)
    
    @property
    def had_injected_heuristics(self) -> bool:
        """Whether heuristics were injected."""
        return len(self.injection_result.heuristics) > 0
    
    @property
    def was_genesis(self) -> bool:
        """Whether this was a genesis (first of its kind) conference."""
        return self.injection_result.genesis_mode
    
    @property
    def heuristic_extracted(self) -> bool:
        """Whether a new heuristic was extracted."""
        return self.learning_outcome.get("extracted", False)
    
    @property
    def speculation_stored(self) -> bool:
        """Whether speculations were stored."""
        return self.learning_outcome.get("speculations_stored", 0) > 0


# =============================================================================
# ORCHESTRATOR V3
# =============================================================================


class ConferenceOrchestratorV3:
    """
    Learning-enabled orchestrator for v3 conferences.
    
    Wraps ConferenceEngineV2 with:
    - Query classification
    - Experience Library retrieval and injection
    - Lane-aware heuristic injection
    - Gatekeeper evaluation
    - Surgeon extraction (from both lanes)
    - Speculation Library integration
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        data_dir: Optional[Path] = None,
        model_config: Optional[V3ModelConfig] = None,
    ):
        """
        Initialize the v3 orchestrator.
        
        Args:
            llm_client: LLM client (created if not provided)
            data_dir: Directory for persistent storage
            model_config: Model configuration for v3 components
        """
        self.llm_client = llm_client or LLMClient()
        self.data_dir = data_dir or Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Store model config (with defaults if not provided)
        self.model_config = model_config or V3ModelConfig()
        
        # Initialize learning components with configured models
        self._init_components()
        
        logger.info("ConferenceOrchestratorV3 initialized with learning components")
    
    def _init_components(self) -> None:
        """Initialize all components."""
        from src.learning.classifier import QueryClassifier
        from src.learning.library import ExperienceLibrary
        from src.learning.optimizer import ConfigurationOptimizer, FeedbackCollector
        
        self.classifier = QueryClassifier(
            llm_client=self.llm_client,
            model=self.model_config.classifier_model,
        )
        self.library = ExperienceLibrary(
            storage_path=self.data_dir / "experience_library_v3.json"
        )
        self.optimizer = ConfigurationOptimizer(
            storage_path=self.data_dir / "optimizer_state_v3.json"
        )
        self.feedback_collector = FeedbackCollector(
            storage_path=self.data_dir / "feedback_v3.json"
        )
        
        # Lane-aware injector
        self.injector = LaneAwareInjector(self.library)
        
        # V3-aware gatekeeper and surgeon with configured models
        self.gatekeeper = GatekeeperV3()
        self.surgeon = SurgeonV3(
            self.llm_client,
            model=self.model_config.surgeon_model,
        )
        
        # Speculation Library
        self.speculation_library = SpeculationLibrary(
            storage_path=self.data_dir / "speculation_library.json"
        )
        
        # Grounding engine
        self.grounding_engine = GroundingEngine()
    
    async def run(
        self,
        query: str,
        config: ConferenceConfig,
        patient_context: Optional[PatientContext] = None,
        enable_routing: bool = True,
        enable_scout: bool = True,
        enable_grounding: bool = True,
        enable_fragility: bool = True,
        fragility_tests: int = 3,
        enable_learning: bool = True,
        enable_injection: bool = True,
        mode_override: Optional[str] = None,
        topology_override: Optional[str] = None,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
    ) -> OrchestratedV3Result:
        """
        Run a fully orchestrated v3 conference.
        
        Args:
            query: The clinical question
            config: Conference configuration
            patient_context: Optional patient information
            enable_routing: Enable intelligent routing
            enable_scout: Enable Scout literature search
            enable_grounding: Enable citation verification
            enable_fragility: Enable fragility testing
            fragility_tests: Number of fragility tests
            enable_learning: Enable learning (Gatekeeper/Surgeon)
            enable_injection: Enable heuristic injection
            mode_override: Optional manual mode override
            topology_override: Optional manual topology override
            progress_callback: Progress callback function
            
        Returns:
            OrchestratedV3Result with conference result and metadata
        """
        # Helper to report learning progress
        def report_learning(stage: str, message: str):
            if progress_callback:
                progress_callback(ProgressUpdate(
                    stage=ProgressStage.INITIALIZING,
                    message=f"[Learning] {message}",
                    percent=0,
                    detail={"learning_stage": stage},
                ))
        
        report_learning("classify", "Classifying query...")
        
        # Step 1: Classify the query
        classification = self.classifier.classify(query)
        logger.info(
            f"Query classified: type={classification.query_type}, "
            f"domain={classification.domain}, complexity={classification.complexity}"
        )
        
        # Step 2: Get relevant heuristics
        report_learning("retrieve", "Retrieving relevant heuristics...")
        injection_result = self.injector.get_injection_for_query(classification)
        logger.info(
            f"Injection result: {len(injection_result.heuristics)} heuristics, "
            f"genesis={injection_result.genesis_mode}"
        )
        
        # Step 3: Build lane-aware injection prompts
        agent_injection_prompts = {}
        if enable_injection and injection_result.heuristics:
            report_learning("inject", "Building lane-aware injection prompts...")
            agent_injection_prompts = self._build_lane_aware_prompts(
                config, injection_result
            )
            logger.info(f"Built injection prompts for {len(agent_injection_prompts)} agents")
        
        # Step 4: Create and run v3 engine
        engine = ConferenceEngineV2(
            llm_client=self.llm_client,
            grounding_engine=self.grounding_engine if enable_grounding else None,
            speculation_library=self.speculation_library,
        )
        
        result = await engine.run_conference(
            query=query,
            config=config,
            patient_context=patient_context,
            enable_routing=enable_routing,
            enable_scout=enable_scout,
            enable_grounding=enable_grounding,
            enable_fragility=enable_fragility,
            fragility_tests=fragility_tests,
            router_model=self.model_config.router_model,
            scout_model=self.model_config.scout_model,
            mode_override=mode_override,
            topology_override=topology_override,
            agent_injection_prompts=agent_injection_prompts,
            progress_callback=progress_callback,
        )
        
        # Step 5: Process learning outcomes
        learning_outcome = {}
        if enable_learning:
            report_learning("evaluate", "Evaluating for learning eligibility...")
            learning_outcome = await self._process_learning(
                result, classification, injection_result
            )
        
        return OrchestratedV3Result(
            conference_result=result,
            classification=classification,
            injection_result=injection_result,
            learning_outcome=learning_outcome,
        )
    
    def _build_lane_aware_prompts(
        self,
        config: ConferenceConfig,
        injection_result: InjectionResult,
    ) -> dict[str, str]:
        """Build lane-aware injection prompts for all agents."""
        prompts = {}
        
        for agent in config.agents:
            role = agent.role.value if hasattr(agent.role, 'value') else str(agent.role)
            role_lower = role.lower()
            
            # Determine lane
            if role_lower in self.injector.LANE_A_ROLES:
                lane = Lane.CLINICAL
            elif role_lower in self.injector.LANE_B_ROLES:
                lane = Lane.EXPLORATORY
            else:
                lane = Lane.CLINICAL  # Default to clinical for unknown roles
            
            prompts[agent.agent_id] = self.injector.build_lane_aware_injection_prompt(
                injection_result, role_lower, lane.value
            )
        
        return prompts
    
    async def _process_learning(
        self,
        result: V2ConferenceResult,
        classification: ClassifiedQuery,
        injection_result: InjectionResult,
    ) -> dict:
        """
        Process learning outcomes from conference.
        
        Returns dict with learning metadata.
        """
        outcome = {
            "evaluated": True,
            "eligible": False,
            "extracted": False,
            "speculations_stored": 0,
            "heuristics_extracted": [],
        }
        
        # Evaluate with gatekeeper
        gk_output = self.gatekeeper.evaluate_v3(result)
        logger.info(f"GatekeeperV3: eligible={gk_output.eligible}, reason={gk_output.reason}")
        
        outcome["eligible"] = gk_output.eligible
        outcome["gatekeeper_reason"] = gk_output.reason
        
        # Extract heuristics if eligible
        if gk_output.eligible:
            try:
                artifacts = await self.surgeon.extract_from_v3(result)
                for artifact in artifacts:
                    self.library.add(artifact)
                    outcome["heuristics_extracted"].append(artifact.heuristic_id)
                    logger.info(f"New heuristic extracted: {artifact.heuristic_id}")
                
                outcome["extracted"] = len(artifacts) > 0
                
            except Exception as e:
                logger.error(f"Heuristic extraction failed: {e}")
                outcome["extraction_error"] = str(e)
        
        # Record heuristic usage outcomes
        for h in injection_result.heuristics:
            usage_outcome = self._check_heuristic_outcome(result, h.heuristic_id)
            if usage_outcome:
                self.injector.record_heuristic_outcome(h.heuristic_id, usage_outcome)
        
        # Count speculations stored
        if self.speculation_library and result.lane_b_result:
            outcome["speculations_stored"] = len(
                [r for r in result.lane_b_result.agent_responses.values()]
            )
        
        return outcome
    
    def _check_heuristic_outcome(
        self,
        result: V2ConferenceResult,
        heuristic_id: str,
    ) -> Optional[str]:
        """
        Check how a heuristic was used in the v3 conference.
        
        Returns "accepted", "rejected", "modified", or None.
        """
        # Check Lane A responses
        if result.lane_a_result:
            for response in result.lane_a_result.agent_responses.values():
                content = response.content.lower()
                
                if heuristic_id.lower() in content or "heuristic" in content:
                    if "incorporate" in content or "accept" in content:
                        return "accepted"
                    elif "reject" in content:
                        return "rejected"
                    elif "modify" in content:
                        return "modified"
        
        # Check synthesis
        if result.synthesis:
            synthesis_text = (
                result.synthesis.clinical_consensus.recommendation.lower()
                if result.synthesis.clinical_consensus
                else ""
            )
            
            if heuristic_id.lower() in synthesis_text:
                return "accepted"  # If in final synthesis, it was incorporated
        
        return None
    
    def get_stats(self) -> dict:
        """Get orchestrator statistics."""
        speculation_stats = (
            self.speculation_library.get_stats() 
            if self.speculation_library 
            else {"total_speculations": 0}
        )
        return {
            "library_stats": self.library.get_stats(),
            "optimizer_stats": self.optimizer.get_stats(),
            "feedback_count": len(self.feedback_collector.feedback),
            "speculation_stats": speculation_stats,
        }
