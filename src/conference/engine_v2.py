"""
Conference Engine v3 - Adversarial MoE Architecture with Topology Selection.

Integrates all v3 components:
- Intelligent Router with automatic topology selection
- Scout (live literature)
- Lane-based parallel execution
- Cross-examination
- Bifurcated synthesis
- Speculation library integration

v3 additions:
- Topology-aware routing (Oxford Debate, Delphi, Socratic, Red Team)
"""

import logging
import time
import uuid
from typing import Any, Callable, Optional

from src.conference.agent import Agent
from src.conference.arbitrator_v2 import ArbitratorV2
from src.conference.base_engine import BaseConferenceEngine
from src.conference.lanes import LaneExecutor, LaneProgressStage, LaneProgressUpdate
from src.models.conference import (
    AgentConfig,
    ConferenceConfig,
    ConferenceSynthesis,
    DissentRecord,
    TokenUsage,
)
from src.models.progress import ProgressStage, ProgressUpdate
from src.models.v2_schemas import (
    ArbitratorSynthesis,
    ConferenceMode,
    LaneResult,
    PatientContext,
    RoutingDecision,
    ScoutReport,
)
from src.routing.router import route_query
from src.scout.scout import run_scout
from src.utils.protocols import LLMClientProtocol


logger = logging.getLogger(__name__)


# Aliases for backwards compatibility
V2ProgressStage = ProgressStage
V2ProgressUpdate = ProgressUpdate


# =============================================================================
# V2.1 CONFERENCE RESULT
# =============================================================================


class V2ConferenceResult:
    """Complete result from a v2.1 conference."""
    
    def __init__(
        self,
        conference_id: str,
        query: str,
        patient_context: Optional[PatientContext],
        routing_decision: RoutingDecision,
        mode: ConferenceMode,
        scout_report: Optional[ScoutReport],
        lane_a_result: Optional[LaneResult],
        lane_b_result: Optional[LaneResult],
        synthesis: ArbitratorSynthesis,
        legacy_synthesis: Optional[ConferenceSynthesis] = None,
        legacy_dissent: Optional[DissentRecord] = None,
        grounding_report: Optional[Any] = None,
        fragility_report: Optional[Any] = None,
        token_usage: Optional[TokenUsage] = None,
        duration_ms: int = 0,
    ):
        self.conference_id = conference_id
        self.query = query
        self.patient_context = patient_context
        self.routing_decision = routing_decision
        self.mode = mode
        self.scout_report = scout_report
        self.lane_a_result = lane_a_result
        self.lane_b_result = lane_b_result
        self.synthesis = synthesis
        self.legacy_synthesis = legacy_synthesis
        self.legacy_dissent = legacy_dissent
        self.grounding_report = grounding_report
        self.fragility_report = fragility_report
        self.token_usage = token_usage or TokenUsage()
        self.duration_ms = duration_ms


# =============================================================================
# V2.1 CONFERENCE ENGINE
# =============================================================================


class ConferenceEngineV2(BaseConferenceEngine):
    """
    v2.1 Conference Engine with Adversarial MoE architecture.
    
    Features:
    - Intelligent routing to determine conference mode
    - Scout for live literature search
    - Parallel Lane A/B execution
    - Cross-examination between lanes
    - Bifurcated synthesis
    - Optional fallback to v1.0 behavior for STANDARD_CARE mode
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        grounding_engine: Optional[Any] = None,
        speculation_library: Optional[Any] = None,
    ):
        """
        Initialize the v2.1 conference engine.
        
        Args:
            llm_client: LLM client for all API calls
            grounding_engine: Optional grounding engine for citation verification
            speculation_library: Optional speculation library for hypothesis tracking
        """
        super().__init__(llm_client, grounding_engine)
        self.speculation_library = speculation_library

    async def run_conference(
        self,
        query: str,
        config: ConferenceConfig,
        patient_context: Optional[PatientContext] = None,
        conference_id: Optional[str] = None,
        enable_routing: bool = True,
        enable_scout: bool = True,
        enable_grounding: bool = True,
        enable_fragility: bool = True,
        fragility_tests: int = 3,
        fragility_model: Optional[str] = None,
        router_model: Optional[str] = None,
        scout_model: Optional[str] = None,
        mode_override: Optional[str] = None,
        topology_override: Optional[str] = None,
        agent_injection_prompts: Optional[dict[str, str]] = None,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
    ) -> V2ConferenceResult:
        """
        Execute a conference.
        
        Args:
            query: The clinical question to deliberate
            config: Conference configuration
            patient_context: Optional patient information
            conference_id: Optional ID (auto-generated if not provided)
            enable_routing: Whether to use intelligent routing
            enable_scout: Whether to run Scout literature search
            enable_grounding: Whether to verify citations
            enable_fragility: Whether to run fragility testing
            fragility_tests: Number of perturbation tests
            fragility_model: Model for fragility testing
            router_model: Model for intelligent routing
            scout_model: Model for Scout analysis
            mode_override: Optional manual mode override
            topology_override: Optional manual topology override
            agent_injection_prompts: Per-agent injection prompts
            progress_callback: Progress callback function
            
        Returns:
            V2ConferenceResult with all outputs
        """
        # Create progress reporter helper
        report = self.create_progress_reporter(progress_callback)

        # Generate conference ID
        if conference_id is None:
            conference_id = f"v2_conf_{uuid.uuid4().hex[:12]}"

        # Reset tracking
        self._reset_tracking()

        start_time = time.time()

        report(ProgressStage.INITIALIZING, "Initializing v2.1 conference...", 2)

        # Step 1: Intelligent Routing
        if enable_routing:
            report(ProgressStage.ROUTING, "Analyzing query complexity...", 5)
            
            routing_decision = await route_query(
                query=query,
                patient_context=patient_context,
                llm_client=self.llm_client,
                router_model=router_model or "openai/gpt-4o",
                mode_override=mode_override,
                topology_override=topology_override,
            )
            
            mode_str = routing_decision.mode if isinstance(routing_decision.mode, str) else routing_decision.mode.value
            topology_str = routing_decision.topology if isinstance(routing_decision.topology, str) else routing_decision.topology.value
            logger.info(f"Routed to mode: {mode_str}, topology: {topology_str}")
            report(
                ProgressStage.ROUTING,
                f"Mode: {mode_str} | Topology: {topology_str}",
                10,
                mode=mode_str,
                topology=topology_str,
                topology_rationale=routing_decision.topology_rationale,
                agents=routing_decision.active_agents,
                rationale=routing_decision.routing_rationale,
            )
        else:
            # Default routing for all agents
            from src.models.conference import ConferenceTopology
            routing_decision = RoutingDecision(
                mode=ConferenceMode.COMPLEX_DILEMMA,
                active_agents=[a.role if isinstance(a.role, str) else a.role.value for a in config.agents],
                activate_scout=True,
                topology=ConferenceTopology.FREE_DISCUSSION,
                topology_rationale="Default: no routing - using free discussion",
            )

        # Step 2: Scout (if activated)
        scout_report = None
        if enable_scout and routing_decision.activate_scout:
            report(ProgressStage.SCOUT_SEARCHING, "Searching recent literature...", 12)
            
            try:
                scout_report = await run_scout(
                    query=query,
                    patient_context=patient_context,
                    date_range_months=12,
                )
                
                report(
                    ProgressStage.SCOUT_COMPLETE,
                    f"Found {scout_report.results_after_filtering} relevant papers",
                    18,
                    total_found=scout_report.total_results_found,
                    filtered=scout_report.results_after_filtering,
                    meta_analyses=len(scout_report.meta_analyses),
                    rcts=len(scout_report.high_quality_rcts),
                )
            except Exception as e:
                logger.error(f"Scout failed: {e}")
                scout_report = ScoutReport(is_empty=True, query_keywords=[])
                report(ProgressStage.SCOUT_COMPLETE, "Scout search failed", 18)

        # Step 3: Create agents based on routing
        agents = self._create_agents_v2(config, routing_decision)
        
        logger.info(f"Created {len(agents)} agents: {[a.role for a in agents]}")

        # Step 4: Execute lanes
        lane_executor = LaneExecutor(
            agents=agents,
            routing_decision=routing_decision,
            scout_report=scout_report,
            patient_context=patient_context,
        )

        # Create a lane progress adapter
        def lane_progress_adapter(update: LaneProgressUpdate):
            # Map lane progress to v2 progress
            stage_map = {
                LaneProgressStage.LANE_A_START: ProgressStage.LANE_A_START,
                LaneProgressStage.LANE_A_AGENT: ProgressStage.LANE_A_AGENT,
                LaneProgressStage.LANE_A_COMPLETE: ProgressStage.LANE_A_COMPLETE,
                LaneProgressStage.LANE_B_START: ProgressStage.LANE_B_START,
                LaneProgressStage.LANE_B_AGENT: ProgressStage.LANE_B_AGENT,
                LaneProgressStage.LANE_B_COMPLETE: ProgressStage.LANE_B_COMPLETE,
                LaneProgressStage.CROSS_EXAM_START: ProgressStage.CROSS_EXAMINATION,
                LaneProgressStage.CROSS_EXAM_CRITIQUE: ProgressStage.CROSS_EXAMINATION,
                LaneProgressStage.CROSS_EXAM_COMPLETE: ProgressStage.CROSS_EXAMINATION,
                LaneProgressStage.FEASIBILITY_START: ProgressStage.FEASIBILITY,
                LaneProgressStage.FEASIBILITY_ASSESSMENT: ProgressStage.FEASIBILITY,
                LaneProgressStage.FEASIBILITY_COMPLETE: ProgressStage.FEASIBILITY,
            }
            v2_stage = stage_map.get(update.stage, ProgressStage.INITIALIZING)
            # Scale percent from lane range to overall range
            scaled_percent = 20 + int(update.percent * 0.5)  # Map to 20-70%
            report(v2_stage, update.message, scaled_percent, **update.detail)

        report(ProgressStage.LANE_A_START, "Starting parallel lane execution...", 20)

        # Execute parallel lanes
        lane_a_result, lane_b_result = await lane_executor.execute_parallel_lanes(
            query=query,
            injection_prompts=agent_injection_prompts,
            progress_callback=lane_progress_adapter if progress_callback else None,
            base_percent=0,
            percent_allocation=50,
        )

        # Execute cross-examination
        report(ProgressStage.CROSS_EXAMINATION, "Starting cross-examination...", 50)
        
        cross_exam_critiques = await lane_executor.execute_cross_examination(
            query=query,
            lane_a_result=lane_a_result,
            lane_b_result=lane_b_result,
            progress_callback=lane_progress_adapter if progress_callback else None,
            base_percent=50,
            percent_allocation=15,
        )

        # Execute feasibility assessment
        report(ProgressStage.FEASIBILITY, "Assessing feasibility...", 65)
        
        feasibility_assessments = await lane_executor.execute_feasibility_round(
            query=query,
            lane_a_result=lane_a_result,
            lane_b_result=lane_b_result,
            progress_callback=lane_progress_adapter if progress_callback else None,
            base_percent=65,
            percent_allocation=10,
        )

        # Step 5: Grounding (if enabled)
        grounding_report = None
        if enable_grounding and self.grounding_engine:
            report(ProgressStage.GROUNDING, "Verifying citations...", 75)
            
            # Collect all response texts
            all_texts = []
            for response in lane_a_result.agent_responses.values():
                all_texts.append(response.content)
            for response in lane_b_result.agent_responses.values():
                all_texts.append(response.content)
            
            try:
                grounding_report = await self.grounding_engine.verify_multiple_texts(all_texts)
                report(
                    ProgressStage.GROUNDING,
                    f"Verified {grounding_report.total_citations} citations",
                    80,
                )
            except Exception as e:
                logger.error(f"Grounding failed: {e}")

        # Step 6: Arbitrator synthesis
        report(ProgressStage.ARBITRATION, "Synthesizing results...", 82)
        
        patient_context_str = self._format_patient_context(patient_context)
        
        arbitrator = ArbitratorV2(config.arbitrator, self.llm_client)
        synthesis, arb_response = await arbitrator.synthesize_lanes(
            query=query,
            lane_a_result=lane_a_result,
            lane_b_result=lane_b_result,
            cross_exam_critiques=cross_exam_critiques,
            feasibility_assessments=feasibility_assessments,
            patient_context_str=patient_context_str,
            scout_report=scout_report,
        )

        report(
            ProgressStage.ARBITRATION,
            f"Synthesis complete ({synthesis.overall_confidence:.0%} confidence)",
            90,
            confidence=synthesis.overall_confidence,
        )

        # Step 7: Fragility testing (if enabled)
        fragility_report = None
        if enable_fragility:
            report(ProgressStage.FRAGILITY_START, "Testing recommendation fragility...", 92)
            
            try:
                from src.fragility.tester import FragilityTester
                
                tester = FragilityTester(self.llm_client)
                fragility_report = await tester.test_consensus(
                    query=query,
                    consensus=synthesis.clinical_consensus.recommendation,
                    model=fragility_model or config.arbitrator.model,
                    num_tests=fragility_tests,
                )
                
                report(
                    ProgressStage.FRAGILITY_TEST,
                    f"Fragility: {fragility_report.survival_rate:.0%} survival rate",
                    98,
                    survival_rate=fragility_report.survival_rate,
                )
            except Exception as e:
                logger.error(f"Fragility testing failed: {e}")

        # Step 8: Store speculations (if library available)
        if self.speculation_library and lane_b_result:
            self._store_speculations(
                conference_id=conference_id,
                query=query,
                lane_b_result=lane_b_result,
            )

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Compile token usage
        token_usage = self._compile_token_usage()

        # Create legacy-compatible outputs
        legacy_synthesis = ConferenceSynthesis(
            final_consensus=synthesis.clinical_consensus.recommendation,
            confidence=synthesis.overall_confidence,
            key_points=[
                *synthesis.clinical_consensus.evidence_basis[:3],
                *[h.hypothesis for h in synthesis.exploratory_considerations[:2]],
            ],
            evidence_summary="\n".join(synthesis.clinical_consensus.evidence_basis),
            caveats=[t.description for t in synthesis.tensions],
        )

        legacy_dissent = DissentRecord(
            preserved=bool(synthesis.preserved_dissent),
            summary=synthesis.preserved_dissent[0] if synthesis.preserved_dissent else "",
        )

        report(ProgressStage.COMPLETE, "Conference complete!", 100)

        return V2ConferenceResult(
            conference_id=conference_id,
            query=query,
            patient_context=patient_context,
            routing_decision=routing_decision,
            mode=routing_decision.mode,
            scout_report=scout_report,
            lane_a_result=lane_a_result,
            lane_b_result=lane_b_result,
            synthesis=synthesis,
            legacy_synthesis=legacy_synthesis,
            legacy_dissent=legacy_dissent,
            grounding_report=grounding_report,
            fragility_report=fragility_report,
            token_usage=token_usage,
            duration_ms=duration_ms,
        )

    def _create_agents_v2(
        self,
        config: ConferenceConfig,
        routing_decision: RoutingDecision,
    ) -> list[Agent]:
        """Create agents based on routing decision."""
        agents = []
        
        # Get active agents from routing
        active_roles = set(routing_decision.active_agents)
        
        # Create agents for each active role
        for agent_config in config.agents:
            role_str = agent_config.role if isinstance(agent_config.role, str) else agent_config.role.value
            if role_str in active_roles or role_str == "arbitrator":
                agent = Agent(agent_config, self.llm_client)
                agents.append(agent)
        
        # Add missing agents with default configuration
        existing_roles = {a.role for a in agents}
        for role in active_roles:
            if role not in existing_roles and role != "arbitrator":
                # Create with default model
                default_config = AgentConfig(
                    agent_id=role,
                    role=role,
                    model="anthropic/claude-sonnet-4",
                    temperature=0.6,
                )
                agent = Agent(default_config, self.llm_client)
                agents.append(agent)
        
        return agents

    def _format_patient_context(self, context: Optional[PatientContext]) -> str:
        """Format patient context for prompts."""
        if not context:
            return "No patient context provided."
        
        parts = []
        if context.age:
            parts.append(f"Age: {context.age}")
        if context.sex:
            parts.append(f"Sex: {context.sex}")
        if context.comorbidities:
            parts.append(f"Comorbidities: {', '.join(context.comorbidities)}")
        if context.current_medications:
            parts.append(f"Current medications: {', '.join(context.current_medications)}")
        if context.failed_treatments:
            parts.append(f"Failed treatments: {', '.join(context.failed_treatments)}")
        if context.allergies:
            parts.append(f"Allergies: {', '.join(context.allergies)}")
        if context.constraints:
            parts.append(f"Constraints: {', '.join(context.constraints)}")
        if context.relevant_history:
            parts.append(f"Relevant history: {context.relevant_history}")
        
        return "\n".join(parts) if parts else "No patient context provided."

    def _store_speculations(
        self,
        conference_id: str,
        query: str,
        lane_b_result: LaneResult,
    ):
        """Extract and store speculations from Lane B."""
        if not self.speculation_library:
            return
        
        # Look for Speculator's response
        for agent_id, response in lane_b_result.agent_responses.items():
            if response.role == "speculator":
                # Extract speculation
                speculation = self.speculation_library.extract_speculation_from_response(
                    response_content=response.content,
                    conference_id=conference_id,
                    query=query,
                )
                
                if speculation:
                    self.speculation_library.store(speculation)
                    logger.info(f"Stored speculation: {speculation.hypothesis[:50]}...")
