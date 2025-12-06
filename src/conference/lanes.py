"""
Lane Executor v3 - Parallel Lane A/B execution with topology awareness.

Manages the adversarial mixture-of-experts pattern:
- Lane A (Clinical): Empiricist, Skeptic, Pragmatist, Patient Voice
- Lane B (Exploratory): Mechanist, Speculator
- Cross-examination between lanes
- Feasibility assessment of both lanes

v3 additions:
- Topology-aware execution (stores selected topology for future use)
"""

import asyncio
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from src.conference.agent import Agent
from src.models.v2_schemas import (
    Critique,
    FeasibilityAssessment,
    Lane,
    LaneResult,
    PatientContext,
    RoutingDecision,
    ScoutReport,
)
from src.models.progress import ProgressStage, ProgressUpdate
from src.utils.parsing import format_patient_context, get_role_display, parse_bullet_points


logger = logging.getLogger(__name__)


# =============================================================================
# PROGRESS TYPES
# =============================================================================


class LaneProgressStage(str, Enum):
    """Progress stages for lane-based execution."""
    
    ROUTING_COMPLETE = "routing_complete"
    SCOUT_SEARCHING = "scout_searching"
    SCOUT_COMPLETE = "scout_complete"
    LANE_A_START = "lane_a_start"
    LANE_A_AGENT = "lane_a_agent"
    LANE_A_COMPLETE = "lane_a_complete"
    LANE_B_START = "lane_b_start"
    LANE_B_AGENT = "lane_b_agent"
    LANE_B_COMPLETE = "lane_b_complete"
    CROSS_EXAM_START = "cross_exam_start"
    CROSS_EXAM_CRITIQUE = "cross_exam_critique"
    CROSS_EXAM_COMPLETE = "cross_exam_complete"
    FEASIBILITY_START = "feasibility_start"
    FEASIBILITY_ASSESSMENT = "feasibility_assessment"
    FEASIBILITY_COMPLETE = "feasibility_complete"


# Map lane-specific stages to unified stages
LANE_TO_UNIFIED_STAGE = {
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
    LaneProgressStage.SCOUT_SEARCHING: ProgressStage.SCOUT_SEARCHING,
    LaneProgressStage.SCOUT_COMPLETE: ProgressStage.SCOUT_COMPLETE,
    LaneProgressStage.ROUTING_COMPLETE: ProgressStage.ROUTING,
}


# Alias for backward compatibility
LaneProgressUpdate = ProgressUpdate


def make_lane_progress(
    stage: LaneProgressStage,
    message: str,
    percent: int,
    **detail,
) -> ProgressUpdate:
    """Create a unified ProgressUpdate from a lane-specific stage."""
    unified_stage = LANE_TO_UNIFIED_STAGE.get(stage, ProgressStage.INITIALIZING)
    return ProgressUpdate(
        stage=unified_stage,
        message=message,
        percent=percent,
        detail={"lane_stage": stage.value, **detail},
    )


# =============================================================================
# CROSS-EXAMINATION PROMPTS
# =============================================================================


def load_cross_exam_prompt(filename: str) -> str:
    """Load a cross-examination prompt template."""
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "cross_exam" / filename
    if prompt_path.exists():
        return prompt_path.read_text()
    else:
        logger.warning(f"Cross-exam prompt not found: {prompt_path}")
        return ""


# =============================================================================
# LANE EXECUTOR
# =============================================================================


class LaneExecutor:
    """
    Executes the v2.1 lane-based conference architecture.
    
    Manages parallel execution of Lane A (Clinical) and Lane B (Exploratory),
    followed by cross-examination and feasibility assessment.
    """

    # Lane assignments
    LANE_A_ROLES = {"empiricist", "skeptic", "pragmatist", "patient_voice"}
    LANE_B_ROLES = {"mechanist", "speculator"}
    
    # Cross-examination assignments
    CROSS_EXAM_CONFIG = [
        # (critic_role, target_lane, critique_type, prompt_file)
        ("skeptic", Lane.EXPLORATORY, "safety", "skeptic_reviews_lane_b.md"),
        ("speculator", Lane.CLINICAL, "stagnation", "speculator_reviews_lane_a.md"),
        ("mechanist", Lane.CLINICAL, "mechanism", "mechanist_reviews_lane_a.md"),
        ("pragmatist", Lane.EXPLORATORY, "feasibility", "pragmatist_reviews_lane_b.md"),
    ]

    def __init__(
        self,
        agents: list[Agent],
        routing_decision: RoutingDecision,
        scout_report: Optional[ScoutReport] = None,
        patient_context: Optional[PatientContext] = None,
        librarian_service: Optional[Any] = None,
    ):
        """
        Initialize the lane executor.
        
        Args:
            agents: All agents for this conference
            routing_decision: Router's decision about mode and agents
            scout_report: Optional Scout findings to inject
            patient_context: Optional patient information
            librarian_service: Optional librarian for document queries
        """
        self.agents = agents
        self.routing_decision = routing_decision
        self.scout_report = scout_report
        self.patient_context = patient_context
        self.librarian_service = librarian_service
        
        # v3: Store topology for potential topology-specific execution
        self.topology = routing_decision.topology
        self.lane_a_topology = routing_decision.effective_lane_a_topology
        self.lane_b_topology = routing_decision.effective_lane_b_topology
        
        # Index agents by role
        self._agents_by_role = {a.role: a for a in agents}
        
        # Split agents into lanes
        self.lane_a_agents = [
            a for a in agents if a.role in self.LANE_A_ROLES
        ]
        self.lane_b_agents = [
            a for a in agents if a.role in self.LANE_B_ROLES
        ]
        
        # Get topology string for logging
        topology_str = self.topology if isinstance(self.topology, str) else self.topology.value
        
        logger.info(
            f"Lane Executor initialized: "
            f"Lane A={[a.role for a in self.lane_a_agents]}, "
            f"Lane B={[a.role for a in self.lane_b_agents]}, "
            f"Topology={topology_str}"
        )

    async def execute_lane(
        self,
        lane: Lane,
        query: str,
        injection_prompts: Optional[dict[str, str]] = None,
        progress_callback: Optional[Callable[[LaneProgressUpdate], None]] = None,
        base_percent: int = 0,
        percent_allocation: int = 20,
    ) -> LaneResult:
        """
        Execute all agents in a single lane.
        
        Args:
            lane: Which lane to execute (CLINICAL or EXPLORATORY)
            query: The clinical question
            injection_prompts: Optional per-agent injection prompts
            progress_callback: Optional progress callback
            base_percent: Starting progress percentage
            percent_allocation: Percentage points allocated to this lane
            
        Returns:
            LaneResult with all agent responses
        """
        agents = self.lane_a_agents if lane == Lane.CLINICAL else self.lane_b_agents
        
        if not agents:
            return LaneResult(lane=lane)
        
        # Build context to inject (Scout report, etc.)
        base_context = self._build_lane_context(lane)
        
        responses = {}
        percent_per_agent = percent_allocation // len(agents) if agents else 0
        
        for i, agent in enumerate(agents):
            current_percent = base_percent + (i * percent_per_agent)
            
            # Report progress
            if progress_callback:
                lane_str = lane if isinstance(lane, str) else lane.value
                stage = LaneProgressStage.LANE_A_AGENT if lane_str == "CLINICAL" else LaneProgressStage.LANE_B_AGENT
                progress_callback(LaneProgressUpdate(
                    stage=stage,
                    message=f"{self._role_display(agent.role)} analyzing...",
                    percent=current_percent,
                    detail={
                        "agent": agent.role,
                        "lane": lane_str,
                    },
                ))
            
            # Build full query with injections
            full_query = self._build_agent_query(
                agent=agent,
                query=query,
                base_context=base_context,
                injection_prompts=injection_prompts,
            )
            
            # Execute agent
            response = await agent.respond_to_query(full_query)
            responses[agent.agent_id] = response
            
            # Report completion
            if progress_callback:
                stage = LaneProgressStage.LANE_A_AGENT if lane_str == "CLINICAL" else LaneProgressStage.LANE_B_AGENT
                progress_callback(LaneProgressUpdate(
                    stage=stage,
                    message=f"{self._role_display(agent.role)} complete ({response.confidence:.0%})",
                    percent=current_percent + percent_per_agent,
                    detail={
                        "agent": agent.role,
                        "lane": lane_str,
                        "confidence": response.confidence,
                        "content": response.content,
                    },
                ))
        
        return LaneResult(
            lane=lane,
            agent_responses=responses,
        )

    async def execute_parallel_lanes(
        self,
        query: str,
        injection_prompts: Optional[dict[str, str]] = None,
        progress_callback: Optional[Callable[[LaneProgressUpdate], None]] = None,
        base_percent: int = 0,
        percent_allocation: int = 40,
    ) -> tuple[LaneResult, LaneResult]:
        """
        Execute both lanes in parallel.
        
        Args:
            query: The clinical question
            injection_prompts: Optional per-agent injection prompts
            progress_callback: Optional progress callback
            base_percent: Starting progress percentage
            percent_allocation: Percentage points for both lanes
            
        Returns:
            Tuple of (Lane A result, Lane B result)
        """
        half_allocation = percent_allocation // 2
        
        # Report lane starts
        if progress_callback:
            progress_callback(LaneProgressUpdate(
                stage=LaneProgressStage.LANE_A_START,
                message="Starting Lane A (Clinical)...",
                percent=base_percent,
                detail={"agents": [a.role for a in self.lane_a_agents]},
            ))
            progress_callback(LaneProgressUpdate(
                stage=LaneProgressStage.LANE_B_START,
                message="Starting Lane B (Exploratory)...",
                percent=base_percent,
                detail={"agents": [a.role for a in self.lane_b_agents]},
            ))
        
        # Execute both lanes in parallel
        lane_a_task = self.execute_lane(
            lane=Lane.CLINICAL,
            query=query,
            injection_prompts=injection_prompts,
            progress_callback=progress_callback,
            base_percent=base_percent,
            percent_allocation=half_allocation,
        )
        
        lane_b_task = self.execute_lane(
            lane=Lane.EXPLORATORY,
            query=query,
            injection_prompts=injection_prompts,
            progress_callback=progress_callback,
            base_percent=base_percent + half_allocation,
            percent_allocation=half_allocation,
        )
        
        lane_a_result, lane_b_result = await asyncio.gather(lane_a_task, lane_b_task)
        
        # Report completion
        if progress_callback:
            progress_callback(LaneProgressUpdate(
                stage=LaneProgressStage.LANE_A_COMPLETE,
                message="Lane A complete",
                percent=base_percent + half_allocation,
                detail={"num_responses": len(lane_a_result.agent_responses)},
            ))
            progress_callback(LaneProgressUpdate(
                stage=LaneProgressStage.LANE_B_COMPLETE,
                message="Lane B complete",
                percent=base_percent + percent_allocation,
                detail={"num_responses": len(lane_b_result.agent_responses)},
            ))
        
        return lane_a_result, lane_b_result

    async def execute_cross_examination(
        self,
        query: str,
        lane_a_result: LaneResult,
        lane_b_result: LaneResult,
        progress_callback: Optional[Callable[[LaneProgressUpdate], None]] = None,
        base_percent: int = 0,
        percent_allocation: int = 20,
    ) -> list[Critique]:
        """
        Execute cross-examination between lanes.
        
        Each lane's agents critique the other lane's output.
        
        Args:
            query: Original clinical question
            lane_a_result: Results from Lane A
            lane_b_result: Results from Lane B
            progress_callback: Optional progress callback
            base_percent: Starting progress percentage
            percent_allocation: Percentage points for cross-exam
            
        Returns:
            List of Critique objects
        """
        if progress_callback:
            progress_callback(LaneProgressUpdate(
                stage=LaneProgressStage.CROSS_EXAM_START,
                message="Starting cross-examination...",
                percent=base_percent,
                detail={},
            ))
        
        # Format lane outputs for critique
        lane_a_output = self._format_lane_output(lane_a_result)
        lane_b_output = self._format_lane_output(lane_b_result)
        patient_context_str = self._format_patient_context_str()
        
        critiques = []
        
        # Filter to available critics
        available_critics = [
            config for config in self.CROSS_EXAM_CONFIG
            if config[0] in self._agents_by_role
        ]
        
        if not available_critics:
            logger.warning("No critics available for cross-examination")
            return []
        
        percent_per_critique = percent_allocation // len(available_critics)
        
        for i, (critic_role, target_lane, critique_type, prompt_file) in enumerate(available_critics):
            current_percent = base_percent + (i * percent_per_critique)
            
            critic = self._agents_by_role.get(critic_role)
            if not critic:
                continue
            
            # Load and format the cross-exam prompt
            prompt_template = load_cross_exam_prompt(prompt_file)
            if not prompt_template:
                # Fallback to basic critique prompt
                prompt_template = self._get_fallback_cross_exam_prompt(critique_type)
            
            # Format the prompt
            if target_lane == Lane.EXPLORATORY:
                formatted_prompt = prompt_template.format(
                    lane_b_output=lane_b_output,
                    patient_context=patient_context_str,
                )
            else:
                formatted_prompt = prompt_template.format(
                    lane_a_output=lane_a_output,
                    patient_context=patient_context_str,
                )
            
            # Report progress
            target_lane_str = target_lane if isinstance(target_lane, str) else target_lane.value
            if progress_callback:
                progress_callback(LaneProgressUpdate(
                    stage=LaneProgressStage.CROSS_EXAM_CRITIQUE,
                    message=f"{self._role_display(critic_role)} critiquing Lane {target_lane_str}...",
                    percent=current_percent,
                    detail={
                        "critic": critic_role,
                        "target_lane": target_lane_str,
                        "critique_type": critique_type,
                    },
                ))
            
            # Execute critique
            response = await critic.respond_to_query(
                f"## Cross-Examination Task\n\n{formatted_prompt}\n\n## Original Query\n{query}"
            )
            
            # Parse into Critique object
            critique = Critique(
                critic_role=critic_role,
                target_role="lane_" + target_lane_str.lower(),
                target_lane=target_lane,
                critique_type=critique_type,
                content=response.content,
                severity=self._extract_severity(response.content),
                specific_concerns=self._extract_concerns(response.content),
            )
            critiques.append(critique)
        
        if progress_callback:
            progress_callback(LaneProgressUpdate(
                stage=LaneProgressStage.CROSS_EXAM_COMPLETE,
                message="Cross-examination complete",
                percent=base_percent + percent_allocation,
                detail={"num_critiques": len(critiques)},
            ))
        
        return critiques

    async def execute_feasibility_round(
        self,
        query: str,
        lane_a_result: LaneResult,
        lane_b_result: LaneResult,
        progress_callback: Optional[Callable[[LaneProgressUpdate], None]] = None,
        base_percent: int = 0,
        percent_allocation: int = 10,
    ) -> list[FeasibilityAssessment]:
        """
        Execute feasibility assessment of both lanes.
        
        Pragmatist and Patient Voice assess practical implementability.
        
        Args:
            query: Original clinical question
            lane_a_result: Results from Lane A
            lane_b_result: Results from Lane B
            progress_callback: Optional progress callback
            base_percent: Starting progress percentage
            percent_allocation: Percentage points for feasibility
            
        Returns:
            List of FeasibilityAssessment objects
        """
        if progress_callback:
            progress_callback(LaneProgressUpdate(
                stage=LaneProgressStage.FEASIBILITY_START,
                message="Starting feasibility assessment...",
                percent=base_percent,
                detail={},
            ))
        
        # Format both lane outputs
        lane_a_output = self._format_lane_output(lane_a_result)
        lane_b_output = self._format_lane_output(lane_b_result)
        
        assessors = ["pragmatist", "patient_voice"]
        available_assessors = [r for r in assessors if r in self._agents_by_role]
        
        if not available_assessors:
            return []
        
        assessments = []
        percent_per_assessor = percent_allocation // len(available_assessors)
        
        for i, role in enumerate(available_assessors):
            agent = self._agents_by_role.get(role)
            if not agent:
                continue
            
            current_percent = base_percent + (i * percent_per_assessor)
            
            # Build feasibility prompt
            feasibility_prompt = f"""## Feasibility Assessment Task

You have seen the outputs from both lanes of the conference:

### Lane A (Clinical Consensus)
{lane_a_output}

### Lane B (Exploratory Considerations)
{lane_b_output}

### Your Task
Assess the practical feasibility of implementing recommendations from BOTH lanes.
Consider: access, cost, coverage, monitoring burden, patient acceptance.

For EACH lane, provide:
1. Can this be implemented?
2. What are the barriers?
3. What modifications would improve feasibility?

### Original Query
{query}
"""
            
            if progress_callback:
                progress_callback(LaneProgressUpdate(
                    stage=LaneProgressStage.FEASIBILITY_ASSESSMENT,
                    message=f"{self._role_display(role)} assessing feasibility...",
                    percent=current_percent,
                    detail={"assessor": role},
                ))
            
            response = await agent.respond_to_query(feasibility_prompt)
            
            # Create assessment for each lane
            for lane in [Lane.CLINICAL, Lane.EXPLORATORY]:
                assessment = FeasibilityAssessment(
                    assessor_role=role,
                    target_lane=lane,
                    summary=response.content,
                    overall_feasibility="possible",  # Could be parsed from response
                )
                assessments.append(assessment)
        
        if progress_callback:
            progress_callback(LaneProgressUpdate(
                stage=LaneProgressStage.FEASIBILITY_COMPLETE,
                message="Feasibility assessment complete",
                percent=base_percent + percent_allocation,
                detail={"num_assessments": len(assessments)},
            ))
        
        return assessments

    def _build_lane_context(self, lane: Lane) -> str:
        """Build context string to inject for a lane."""
        parts = []
        
        # Add Scout report if available
        if self.scout_report and not self.scout_report.is_empty:
            parts.append(self.scout_report.to_context_block())
        
        # Add lane-specific instructions
        if lane == Lane.CLINICAL:
            parts.append("""
## Your Lane: CLINICAL (Lane A)

Your focus is on **safe, evidence-based, implementable** recommendations.
- Ground claims in published evidence
- Prioritize safety and feasibility
- Consider the patient's real-world constraints
""")
        else:
            parts.append("""
## Your Lane: EXPLORATORY (Lane B)

Your focus is on **mechanism, innovation, and theoretical possibilities**.
- Propose hypotheses based on biology
- Consider off-label and experimental approaches
- Clearly label speculation as such
""")
        
        return "\n\n".join(parts)

    def _build_agent_query(
        self,
        agent: Agent,
        query: str,
        base_context: str,
        injection_prompts: Optional[dict[str, str]],
    ) -> str:
        """Build the full query for an agent including all context."""
        parts = [base_context]
        
        # Add per-agent injection if provided
        if injection_prompts and agent.agent_id in injection_prompts:
            parts.append(injection_prompts[agent.agent_id])
        
        # Add the actual query
        parts.append(f"## Clinical Question\n\n{query}")
        
        return "\n\n".join(parts)

    def _format_lane_output(self, lane_result: LaneResult) -> str:
        """Format lane output for cross-examination."""
        lines = []
        for agent_id, response in lane_result.agent_responses.items():
            lines.append(f"### {self._role_display(response.role)}")
            lines.append(response.content)
            lines.append("")
        return "\n".join(lines)

    def _format_patient_context_str(self) -> str:
        """Format patient context for prompts."""
        return format_patient_context(self.patient_context)

    def _role_display(self, role: str) -> str:
        """Get display name for a role."""
        return get_role_display(role)

    def _extract_severity(self, content: str) -> str:
        """Extract severity level from critique content."""
        content_lower = content.lower()
        if "critical" in content_lower or "unacceptable" in content_lower:
            return "critical"
        elif "major" in content_lower or "serious" in content_lower:
            return "major"
        elif "moderate" in content_lower:
            return "moderate"
        return "minor"

    def _extract_concerns(self, content: str) -> list[str]:
        """Extract specific concerns from critique content."""
        concerns = parse_bullet_points(content)
        # Filter to meaningful concerns and limit
        return [c[:200] for c in concerns if len(c) > 10][:5]

    def _get_fallback_cross_exam_prompt(self, critique_type: str) -> str:
        """Get fallback cross-exam prompt if template not found."""
        prompts = {
            "safety": """Review the following output and identify safety concerns:

{lane_b_output}

Patient Context:
{patient_context}

Focus on: drug interactions, contraindications, monitoring requirements, adverse effects.""",
            "stagnation": """Review the following output and identify where it may be too conservative:

{lane_a_output}

Patient Context:
{patient_context}

Focus on: missed opportunities, paradigm blindness, therapeutic inertia.""",
            "mechanism": """Review the following output for mechanism understanding:

{lane_a_output}

Patient Context:
{patient_context}

Focus on: mechanism gaps, phenotype mismatches, target selection issues.""",
            "feasibility": """Review the following output for practical feasibility:

{lane_b_output}

Patient Context:
{patient_context}

Focus on: access barriers, cost issues, monitoring burden, implementation challenges.""",
        }
        return prompts.get(critique_type, prompts["safety"])

