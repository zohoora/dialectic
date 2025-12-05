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
from typing import Any, Callable, Optional

from src.conference.engine_v2 import (
    ConferenceEngineV2,
    V2ConferenceResult,
    V2ProgressStage,
    V2ProgressUpdate,
)
from src.grounding.engine import GroundingEngine
from src.learning.classifier import ClassifiedQuery, QueryClassifier
from src.learning.gatekeeper import Gatekeeper
from src.learning.injector import HeuristicInjector
from src.learning.library import ExperienceLibrary
from src.learning.optimizer import ConfigurationOptimizer, FeedbackCollector
from src.learning.surgeon import Surgeon
from src.llm.client import LLMClient
from src.models.conference import ConferenceConfig
from src.models.experience import InjectionResult, ReasoningArtifact
from src.models.v2_schemas import (
    ArbitratorSynthesis,
    Lane,
    PatientContext,
    RoutingDecision,
)
from src.speculation.library import SpeculationLibrary


logger = logging.getLogger(__name__)


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
# LANE-AWARE INJECTOR
# =============================================================================


class LaneAwareInjector(HeuristicInjector):
    """
    Extended injector that builds lane-specific injection prompts.
    
    Lane A (Clinical) agents get evidence-focused guidance.
    Lane B (Exploratory) agents get hypothesis-focused guidance.
    """
    
    # Lane A roles (clinical/evidence-based)
    LANE_A_ROLES = {"empiricist", "skeptic", "pragmatist", "patient_voice"}
    
    # Lane B roles (exploratory/mechanistic)
    LANE_B_ROLES = {"mechanist", "speculator"}
    
    def build_lane_aware_injection_prompt(
        self,
        injection_result: InjectionResult,
        agent_role: str,
        lane: Lane,
    ) -> str:
        """
        Build injection prompt with lane-specific guidance.
        
        Args:
            injection_result: Result from library lookup
            agent_role: Role of the agent
            lane: Which lane this agent is in
            
        Returns:
            Formatted injection prompt
        """
        base_prompt = self.build_agent_injection_prompt(injection_result, agent_role)
        
        if not base_prompt:
            return ""
        
        # Add lane-specific guidance
        lane_guidance = self._get_lane_guidance(lane, agent_role)
        
        return base_prompt + lane_guidance
    
    def _get_lane_guidance(self, lane: Lane, role: str) -> str:
        """Get lane-specific guidance to append to injection."""
        if lane == Lane.CLINICAL:
            return """

---
### Lane A Context (Clinical)
Your focus is on **safe, evidence-based, guideline-adherent** recommendations.
When validating heuristics:
- Prioritize heuristics with strong RCT or meta-analysis support
- Be cautious with heuristics that lack recent evidence
- Consider feasibility in standard clinical practice
---
"""
        else:  # Lane B - Exploratory
            return """

---
### Lane B Context (Exploratory)
Your focus is on **mechanism, innovation, and theoretical possibilities**.
When validating heuristics:
- Consider whether the mechanism applies to this patient's phenotype
- Look for heuristics that might inform novel approaches
- It's OK to explore heuristics speculatively - clearly label speculation
---
"""


# =============================================================================
# V3 SURGEON (Lane-aware extraction)
# =============================================================================


class SurgeonV3(Surgeon):
    """
    Extended surgeon for v3 conferences.
    
    Can extract heuristics from:
    - Clinical consensus (Lane A)
    - Exploratory considerations (Lane B)
    - Cross-examination insights
    """
    
    async def extract_from_v3(
        self,
        result: V2ConferenceResult,
    ) -> list[ReasoningArtifact]:
        """
        Extract heuristics from a v3 conference result.
        
        May extract multiple artifacts:
        - One from clinical consensus
        - One or more from exploratory considerations
        
        Args:
            result: V2ConferenceResult from conference
            
        Returns:
            List of extracted artifacts (may be empty)
        """
        artifacts = []
        
        # Extract from clinical consensus
        if result.synthesis and result.synthesis.clinical_consensus:
            clinical_artifact = await self._extract_clinical_heuristic(result)
            if clinical_artifact:
                artifacts.append(clinical_artifact)
        
        # Extract from exploratory considerations (with hypothesis tag)
        if result.synthesis and result.synthesis.exploratory_considerations:
            for consideration in result.synthesis.exploratory_considerations:
                # Only extract high-evidence exploratory considerations
                if consideration.evidence_level in ["early_clinical", "off_label"]:
                    exploratory_artifact = await self._extract_exploratory_heuristic(
                        result, consideration
                    )
                    if exploratory_artifact:
                        artifacts.append(exploratory_artifact)
        
        return artifacts
    
    async def _extract_clinical_heuristic(
        self,
        result: V2ConferenceResult,
    ) -> Optional[ReasoningArtifact]:
        """Extract heuristic from clinical consensus (Lane A)."""
        consensus = result.synthesis.clinical_consensus
        
        # Build a v1-style input for the base surgeon
        from src.models.experience import SurgeonInput, ContextVector
        
        # Build transcript from Lane A responses
        transcript_parts = []
        if result.lane_a_result:
            for agent_id, response in result.lane_a_result.agent_responses.items():
                transcript_parts.append(f"[{response.role}]: {response.content[:500]}")
        
        surgeon_input = SurgeonInput(
            conference_id=result.conference_id,
            query=result.query,
            final_consensus=consensus.recommendation,
            conference_transcript="\n\n".join(transcript_parts),
            verified_citations=consensus.evidence_basis,
            fragility_factors=result.fragility_results.instability_zones if result.fragility_results else [],
        )
        
        output = await self.extract_from_input(surgeon_input)
        
        if output.extraction_successful and output.artifact:
            # Tag as clinical heuristic
            output.artifact.context_vector.keywords.append("lane_a")
            output.artifact.context_vector.keywords.append("clinical")
            return output.artifact
        
        return None
    
    async def _extract_exploratory_heuristic(
        self,
        result: V2ConferenceResult,
        consideration: Any,
    ) -> Optional[ReasoningArtifact]:
        """Extract heuristic from exploratory consideration (Lane B)."""
        from src.models.experience import ContextVector
        import uuid
        
        # Build artifact directly for exploratory hypothesis
        artifact = ReasoningArtifact(
            heuristic_id=f"hyp_{uuid.uuid4().hex[:8]}",
            source_conference_id=result.conference_id,
            winning_heuristic=f"HYPOTHESIS: {consideration.hypothesis}",
            contra_heuristic="",  # Exploratory doesn't have contra
            context_vector=ContextVector(
                domain=self._infer_domain(result.query),
                condition="",
                treatment_type="exploratory",
                keywords=["lane_b", "exploratory", "hypothesis"],
            ),
            qualifying_conditions=[f"Mechanism: {consideration.mechanism}"] if consideration.mechanism else [],
            disqualifying_conditions=consideration.risks,
            fragility_factors=[consideration.what_would_validate] if consideration.what_would_validate else [],
            confidence=0.3,  # Low confidence for exploratory
            evidence_summary=f"Evidence level: {consideration.evidence_level}",
        )
        
        return artifact
    
    def _infer_domain(self, query: str) -> str:
        """Simple domain inference from query."""
        query_lower = query.lower()
        domains = {
            "pain": "pain_management",
            "diabetes": "endocrinology",
            "hypertension": "cardiology",
            "cancer": "oncology",
            "infection": "infectious_disease",
            "depression": "psychiatry",
            "anxiety": "psychiatry",
        }
        for keyword, domain in domains.items():
            if keyword in query_lower:
                return domain
        return "general"


# =============================================================================
# GATEKEEPER V3 (V2ConferenceResult aware)
# =============================================================================


class GatekeeperV3(Gatekeeper):
    """
    Extended gatekeeper for v3 conferences.
    
    Evaluates V2ConferenceResult format with lane-based outputs.
    """
    
    def evaluate_v3(self, result: V2ConferenceResult) -> Any:
        """
        Evaluate a v3 conference result for learning eligibility.
        
        Args:
            result: V2ConferenceResult from conference
            
        Returns:
            GatekeeperOutput with eligibility decision
        """
        from src.models.gatekeeper import GatekeeperOutput
        
        # Check for basic requirements
        if not result.synthesis:
            return GatekeeperOutput(
                eligible=False,
                reason="No synthesis produced",
            )
        
        synthesis = result.synthesis
        
        # Check confidence threshold
        if synthesis.overall_confidence < 0.5:
            return GatekeeperOutput(
                eligible=False,
                reason=f"Confidence too low: {synthesis.overall_confidence:.0%}",
            )
        
        # Check for clinical consensus
        if not synthesis.clinical_consensus:
            return GatekeeperOutput(
                eligible=False,
                reason="No clinical consensus reached",
            )
        
        # Check clinical consensus confidence
        if synthesis.clinical_consensus.confidence < 0.6:
            return GatekeeperOutput(
                eligible=False,
                reason=f"Clinical confidence too low: {synthesis.clinical_consensus.confidence:.0%}",
            )
        
        # Check for unresolved critical tensions
        critical_tensions = [
            t for t in synthesis.tensions 
            if t.resolution == "unresolved"
        ]
        if len(critical_tensions) >= 2:
            return GatekeeperOutput(
                eligible=False,
                reason=f"Too many unresolved tensions: {len(critical_tensions)}",
            )
        
        # Check for evidence basis
        if not synthesis.clinical_consensus.evidence_basis:
            return GatekeeperOutput(
                eligible=False,
                reason="No evidence basis provided",
            )
        
        # Passed all checks
        return GatekeeperOutput(
            eligible=True,
            reason="Conference meets quality thresholds",
            quality_signals={
                "confidence": synthesis.overall_confidence,
                "clinical_confidence": synthesis.clinical_consensus.confidence,
                "evidence_count": len(synthesis.clinical_consensus.evidence_basis),
                "exploratory_count": len(synthesis.exploratory_considerations),
                "tensions_resolved": len(synthesis.tensions) - len(critical_tensions),
            },
        )


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
    ):
        """
        Initialize the v3 orchestrator.
        
        Args:
            llm_client: LLM client (created if not provided)
            data_dir: Directory for persistent storage
        """
        self.llm_client = llm_client or LLMClient()
        self.data_dir = data_dir or Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize learning components
        self.classifier = QueryClassifier(llm_client=self.llm_client)
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
        
        # V3-aware gatekeeper and surgeon
        self.gatekeeper = GatekeeperV3()
        self.surgeon = SurgeonV3(self.llm_client)
        
        # Speculation Library
        self.speculation_library = SpeculationLibrary(
            storage_path=self.data_dir / "speculation_library.json"
        )
        
        # Grounding engine
        self.grounding_engine = GroundingEngine()
        
        logger.info("ConferenceOrchestratorV3 initialized with learning components")
    
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
        progress_callback: Optional[Callable[[V2ProgressUpdate], None]] = None,
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
            progress_callback: Progress callback function
            
        Returns:
            OrchestratedV3Result with conference result and metadata
        """
        # Helper to report learning progress
        def report_learning(stage: str, message: str):
            if progress_callback:
                progress_callback(V2ProgressUpdate(
                    stage=V2ProgressStage.INITIALIZING,
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
                injection_result, role_lower, lane
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
            usage_outcome = self._check_heuristic_outcome_v3(result, h.heuristic_id)
            if usage_outcome:
                self.injector.record_heuristic_outcome(h.heuristic_id, usage_outcome)
        
        # Count speculations stored
        if self.speculation_library and result.lane_b_result:
            outcome["speculations_stored"] = len(
                [r for r in result.lane_b_result.agent_responses.values()]
            )
        
        return outcome
    
    def _check_heuristic_outcome_v3(
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
        logger.info(f"Feedback recorded for {conference_id}")
    
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

