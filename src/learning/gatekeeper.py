"""
Gatekeeper - Quality control for Experience Library extraction.

Determines whether a conference result contains generalizable wisdom
worthy of extraction. Prevents the library from being polluted with
idiosyncratic or poorly-supported heuristics.
"""

import logging
from datetime import datetime
from typing import Optional

from src.models.conference import ConferenceResult, DissentRecord
from src.models.gatekeeper import (
    CalibrationReport,
    DissentStatus,
    GatekeeperDecision,
    GatekeeperFlag,
    GatekeeperInput,
    GatekeeperOutput,
    OutcomeSignals,
    RejectionCode,
)


logger = logging.getLogger(__name__)


class Gatekeeper:
    """
    Evaluates conference results for eligibility to enter Experience Library.
    
    Applies strict criteria:
    1. Hallucination check - no unverified citations
    2. Fragility check - recommendation survives perturbations
    3. Generalizability check - not overly patient-specific
    4. Evidence check - has cited evidence
    5. Consensus depth check - substantive debate occurred
    """
    
    # Configurable thresholds
    MAX_HALLUCINATION_RATE = 0.1  # Allow up to 10% failed citations
    MIN_FRAGILITY_SURVIVAL = 0.3  # At least 30% survival rate
    MIN_CITATIONS = 1  # At least 1 citation required
    MIN_ROUNDS_FOR_DEPTH = 2  # Need at least 2 rounds for depth
    
    def __init__(
        self,
        hallucination_threshold: float = MAX_HALLUCINATION_RATE,
        fragility_threshold: float = MIN_FRAGILITY_SURVIVAL,
        min_citations: int = MIN_CITATIONS,
        strict_mode: bool = False,
    ):
        """
        Initialize the Gatekeeper.
        
        Args:
            hallucination_threshold: Max allowed hallucination rate
            fragility_threshold: Min required fragility survival rate
            min_citations: Min required verified citations
            strict_mode: If True, apply stricter criteria
        """
        self.hallucination_threshold = hallucination_threshold
        self.fragility_threshold = fragility_threshold
        self.min_citations = min_citations
        self.strict_mode = strict_mode
        
        # Track decisions for calibration
        self.decisions: list[GatekeeperDecision] = []
    
    def evaluate(self, result: ConferenceResult) -> GatekeeperOutput:
        """
        Evaluate a conference result for Experience Library eligibility.
        
        Args:
            result: Complete conference result
            
        Returns:
            GatekeeperOutput with eligibility decision
        """
        # Build input from conference result
        gk_input = self._build_input(result)
        
        # Run evaluation
        output = self._run_evaluation(gk_input)
        
        # Record decision for calibration
        self._record_decision(result.conference_id, output)
        
        return output
    
    def evaluate_from_input(self, gk_input: GatekeeperInput) -> GatekeeperOutput:
        """
        Evaluate from a pre-built GatekeeperInput.
        
        Args:
            gk_input: Prepared gatekeeper input
            
        Returns:
            GatekeeperOutput with eligibility decision
        """
        output = self._run_evaluation(gk_input)
        self._record_decision(gk_input.conference_id, output)
        return output
    
    def _build_input(self, result: ConferenceResult) -> GatekeeperInput:
        """Build GatekeeperInput from ConferenceResult."""
        # Calculate hallucination rate
        hallucination_rate = 0.0
        total_citations = 0
        verified_citations = 0
        
        if result.grounding_report:
            total_citations = result.grounding_report.total_citations
            verified_citations = len(result.grounding_report.citations_verified)
            hallucination_rate = result.grounding_report.hallucination_rate
        
        # Get fragility survival rate
        fragility_survival = 1.0
        if result.fragility_report:
            fragility_survival = result.fragility_report.survival_rate
        
        # Build dissent status
        dissent_status = self._build_dissent_status(result.dissent)
        
        # Count position changes across rounds
        position_changes = 0
        for round_result in result.rounds:
            for agent_id, response in round_result.agent_responses.items():
                if response.changed_from_previous:
                    position_changes += 1
        
        return GatekeeperInput(
            conference_id=result.conference_id,
            conference_summary=self._summarize_conference(result),
            final_consensus=result.synthesis.final_consensus,
            hallucination_rate=hallucination_rate,
            fragility_survival_rate=fragility_survival,
            dissent_status=dissent_status,
            num_rounds=len(result.rounds),
            position_changes=position_changes,
            total_citations=total_citations,
            verified_citations=verified_citations,
        )
    
    def _build_dissent_status(self, dissent: DissentRecord) -> DissentStatus:
        """Build DissentStatus from DissentRecord."""
        if not dissent.preserved:
            return DissentStatus(dissent_preserved=False)
        
        return DissentStatus(
            dissent_preserved=True,
            dissent_summary=dissent.summary,
            dissenting_role=dissent.dissenting_role,
            dissent_strength=dissent.strength or "Moderate",
        )
    
    def _summarize_conference(self, result: ConferenceResult) -> str:
        """Generate brief summary of conference."""
        parts = [
            f"Query: {result.query[:100]}...",
            f"Rounds: {len(result.rounds)}",
            f"Consensus confidence: {result.synthesis.confidence:.0%}",
        ]
        if result.dissent.preserved:
            parts.append(f"Dissent from: {result.dissent.dissenting_role}")
        return " | ".join(parts)
    
    def _run_evaluation(self, gk_input: GatekeeperInput) -> GatekeeperOutput:
        """
        Run the actual evaluation logic.
        
        Returns GatekeeperOutput with decision.
        """
        flags: list[GatekeeperFlag] = []
        rejection_code: Optional[RejectionCode] = None
        secondary_code: Optional[RejectionCode] = None
        reasons: list[str] = []
        confidence = 0.7  # Start with moderate confidence
        
        # 1. HALLUCINATION CHECK
        if gk_input.hallucination_rate > self.hallucination_threshold:
            rejection_code = RejectionCode.HALLUCINATION
            reasons.append(
                f"Hallucination rate {gk_input.hallucination_rate:.0%} exceeds "
                f"threshold {self.hallucination_threshold:.0%}"
            )
        elif gk_input.hallucination_rate > 0:
            # Some failed but below threshold - flag it
            flags.append(GatekeeperFlag.HALLUCINATION_SELF_CORRECTED)
            confidence -= 0.1
        
        # 2. FRAGILITY CHECK
        if gk_input.fragility_survival_rate < self.fragility_threshold:
            if rejection_code is None:
                rejection_code = RejectionCode.FRAGILE
            else:
                secondary_code = RejectionCode.FRAGILE
            reasons.append(
                f"Fragility survival {gk_input.fragility_survival_rate:.0%} below "
                f"threshold {self.fragility_threshold:.0%}"
            )
        elif gk_input.fragility_survival_rate >= 0.8:
            # High survival rate increases confidence
            confidence += 0.1
        
        # 3. EVIDENCE CHECK
        if gk_input.verified_citations < self.min_citations:
            if rejection_code is None:
                rejection_code = RejectionCode.NO_EVIDENCE
            else:
                secondary_code = secondary_code or RejectionCode.NO_EVIDENCE
            reasons.append(
                f"Only {gk_input.verified_citations} verified citations "
                f"(minimum: {self.min_citations})"
            )
        elif gk_input.verified_citations >= 3:
            flags.append(GatekeeperFlag.STRONG_EVIDENCE)
            confidence += 0.1
        
        # 4. CONSENSUS DEPTH CHECK
        if gk_input.num_rounds < self.MIN_ROUNDS_FOR_DEPTH and gk_input.position_changes == 0:
            if rejection_code is None:
                rejection_code = RejectionCode.SHALLOW
            else:
                secondary_code = secondary_code or RejectionCode.SHALLOW
            reasons.append("No substantive debate occurred")
        elif gk_input.position_changes > 0:
            # Position changes indicate real deliberation
            flags.append(GatekeeperFlag.CONTESTED_BUT_RESOLVED)
            confidence += 0.05
        
        # 5. DISSENT CONSIDERATION
        if gk_input.dissent_status.dissent_preserved:
            if gk_input.dissent_status.dissent_strength == "Strong":
                # Strong dissent reduces confidence
                confidence -= 0.15
                flags.append(GatekeeperFlag.NARROW_SUBSET)
            elif gk_input.dissent_status.dissent_strength == "Moderate":
                confidence -= 0.05
        
        # Strict mode applies additional checks
        if self.strict_mode:
            if gk_input.hallucination_rate > 0:
                if rejection_code is None:
                    rejection_code = RejectionCode.HALLUCINATION
                    reasons.append("Strict mode: any failed citations disqualify")
        
        # Build output
        eligible = rejection_code is None
        
        if eligible:
            reason = "Conference meets all quality criteria for extraction"
            if flags:
                reason += f" (flags: {', '.join(f.value for f in flags)})"
        else:
            reason = "; ".join(reasons[:2])  # Limit to first 2 reasons
        
        # Clamp confidence
        confidence = max(0.1, min(0.95, confidence))
        
        return GatekeeperOutput(
            eligible=eligible,
            reason=reason,
            rejection_code=rejection_code,
            secondary_code=secondary_code,
            flags=flags,
            confidence=confidence,
        )
    
    def _record_decision(self, conference_id: str, output: GatekeeperOutput):
        """Record decision for calibration tracking."""
        decision = GatekeeperDecision(
            conference_id=conference_id,
            passed=output.eligible,
            rejection_code=output.rejection_code,
            confidence=output.confidence,
        )
        self.decisions.append(decision)
        
        logger.info(
            f"Gatekeeper decision for {conference_id}: "
            f"{'PASS' if output.eligible else 'REJECT'} "
            f"(confidence: {output.confidence:.0%})"
        )
    
    def record_outcome(self, conference_id: str, outcome: str):
        """
        Record eventual outcome for a conference (for calibration).
        
        Args:
            conference_id: ID of the conference
            outcome: "positive", "neutral", or "negative"
        """
        for decision in self.decisions:
            if decision.conference_id == conference_id:
                decision.eventual_outcome = outcome
                logger.info(f"Recorded outcome '{outcome}' for {conference_id}")
                return
        
        logger.warning(f"No decision found for conference {conference_id}")
    
    def get_calibration_report(self) -> CalibrationReport:
        """
        Analyze Gatekeeper calibration based on recorded outcomes.
        
        Returns:
            CalibrationReport with analysis and recommendations
        """
        # Filter to decisions with outcomes
        decisions_with_outcomes = [
            d for d in self.decisions if d.eventual_outcome is not None
        ]
        
        if len(decisions_with_outcomes) < 10:
            return CalibrationReport(
                status="INSUFFICIENT_DATA",
                recommendation="Continue collecting outcomes (need at least 10)",
                decisions_analyzed=len(decisions_with_outcomes),
            )
        
        # Calculate false positive rate
        passed_decisions = [d for d in decisions_with_outcomes if d.passed]
        passed_bad = sum(
            1 for d in passed_decisions if d.eventual_outcome == "negative"
        )
        
        if len(passed_decisions) == 0:
            fpr = 0.0
        else:
            fpr = passed_bad / len(passed_decisions)
        
        # Calculate rejection rate
        rejection_rate = sum(
            1 for d in decisions_with_outcomes if not d.passed
        ) / len(decisions_with_outcomes)
        
        # Determine status
        if fpr > 0.3:
            status = "TOO_LOOSE"
            recommendation = "Tighten Gatekeeper criteria (FPR too high)"
        elif fpr < 0.1 and rejection_rate > 0.8:
            status = "POSSIBLY_TOO_STRICT"
            recommendation = "Consider loosening criteria if library growth is slow"
        else:
            status = "WELL_CALIBRATED"
            recommendation = "Maintain current thresholds"
        
        return CalibrationReport(
            status=status,
            false_positive_rate=fpr,
            rejection_rate=rejection_rate,
            recommendation=recommendation,
            decisions_analyzed=len(decisions_with_outcomes),
        )
    
    def reset_calibration(self):
        """Reset calibration tracking."""
        self.decisions = []


# =============================================================================
# GATEKEEPER V3 (V2ConferenceResult aware)
# =============================================================================


class GatekeeperV3(Gatekeeper):
    """
    Extended gatekeeper for v3 conferences.
    
    Evaluates V2ConferenceResult format with lane-based outputs.
    """
    
    def evaluate_v3(self, result: "V2ConferenceResult") -> GatekeeperOutput:
        """
        Evaluate a v3 conference result for learning eligibility.
        
        Args:
            result: V2ConferenceResult from conference
            
        Returns:
            GatekeeperOutput with eligibility decision
        """
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


# Type hints for V3 result - imported at runtime to avoid circular imports
if False:  # TYPE_CHECKING equivalent without import
    from src.conference.engine_v2 import V2ConferenceResult

