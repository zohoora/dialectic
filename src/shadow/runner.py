"""
Shadow Runner - Counterfactual conference evaluation.

Replays past queries with alternative configurations to learn
which settings produce better outcomes without user feedback.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol

from src.models.conference import ConferenceConfig, ConferenceResult
from src.models.shadow import (
    JudgeScores,
    Preference,
    ShadowBatch,
    ShadowInsight,
    ShadowResult,
    ShadowSummary,
)
from src.utils.protocols import LLMClientProtocol


logger = logging.getLogger(__name__)


# Load prompt directly
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def load_shadow_prompt(name: str) -> str:
    """Load a shadow prompt template."""
    prompt_path = PROMPTS_DIR / "shadow" / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Shadow prompt not found: {prompt_path}")
    return prompt_path.read_text()


class ConferenceEngineProtocol(Protocol):
    """Protocol for conference engine."""
    
    async def run_conference(
        self,
        query: str,
        config: ConferenceConfig,
        conference_id: Optional[str] = None,
        enable_grounding: bool = True,
        enable_fragility: bool = True,
        fragility_tests: int = 3,
        agent_injection_prompts: Optional[dict[str, str]] = None,
    ) -> ConferenceResult:
        ...


class ConferenceJudge:
    """
    LLM-based judge for comparing conference outputs.
    
    Uses a strong model to evaluate responses on multiple axes
    without requiring human feedback.
    """
    
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        judge_model: str = "anthropic/claude-3.5-sonnet",
    ):
        """
        Initialize the judge.
        
        Args:
            llm_client: LLM client for judge calls
            judge_model: Model to use for judging
        """
        self.llm_client = llm_client
        self.judge_model = judge_model
        self.prompt_template = load_shadow_prompt("judge")
    
    async def evaluate(
        self,
        query: str,
        response_a: str,
        response_b: str,
    ) -> JudgeScores:
        """
        Compare two responses and return scores.
        
        Args:
            query: Original query
            response_a: First response (original)
            response_b: Second response (alternative)
            
        Returns:
            JudgeScores with evaluation
        """
        # Build prompt
        prompt = self.prompt_template.format(
            query=query,
            response_a=response_a,
            response_b=response_b,
        )
        
        # Call judge model
        response = await self.llm_client.complete(
            model=self.judge_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # Low temp for consistency
            max_tokens=500,
        )
        
        # Parse response
        return self._parse_judge_response(response.content)
    
    def _parse_judge_response(self, content: str) -> JudgeScores:
        """Parse judge response into JudgeScores."""
        try:
            # Extract JSON from response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            data = json.loads(content[json_start:json_end])
            
            # Convert preference
            pref_str = data.get("overall_preference", "TIE").upper()
            if pref_str == "A":
                preference = Preference.ORIGINAL
            elif pref_str == "B":
                preference = Preference.ALTERNATIVE
            else:
                preference = Preference.TIE
            
            # Get scores for response B (alternative)
            scores_b = data.get("scores_b", {})
            
            return JudgeScores(
                accuracy=float(scores_b.get("accuracy", 5)),
                evidence=float(scores_b.get("evidence", 5)),
                calibration=float(scores_b.get("calibration", 5)),
                actionability=float(scores_b.get("actionability", 5)),
                safety=float(scores_b.get("safety", 5)),
                overall_preference=preference,
                reasoning=data.get("reasoning"),
            )
            
        except Exception as e:
            logger.error(f"Failed to parse judge response: {e}")
            # Return neutral scores on error
            return JudgeScores(
                accuracy=5,
                evidence=5,
                calibration=5,
                actionability=5,
                safety=5,
                overall_preference=Preference.TIE,
                reasoning=f"Parse error: {str(e)}",
            )


class ShadowRunner:
    """
    Runs shadow (counterfactual) conferences for optimization.
    
    Use cases:
    - Cold start: Learn from scratch without user feedback
    - Continuous improvement: Test new configs overnight
    - A/B testing: Compare specific configurations
    """
    
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        conference_engine: ConferenceEngineProtocol,
        judge_model: str = "anthropic/claude-3.5-sonnet",
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize the shadow runner.
        
        Args:
            llm_client: LLM client
            conference_engine: Conference engine for running alternatives
            judge_model: Model to use for judging
            storage_path: Path for storing results
        """
        self.llm_client = llm_client
        self.conference_engine = conference_engine
        self.judge = ConferenceJudge(llm_client, judge_model)
        self.storage_path = storage_path
        
        # Storage for past results
        self.results: list[ShadowResult] = []
        
        if storage_path and storage_path.exists():
            self._load_results()
    
    async def run_shadow_evaluation(
        self,
        original_result: ConferenceResult,
        alternative_configs: list[ConferenceConfig],
    ) -> list[ShadowResult]:
        """
        Replay a past conference with alternative configurations.
        
        Args:
            original_result: Original conference result
            alternative_configs: Configurations to test
            
        Returns:
            List of ShadowResult for each config tested
        """
        results = []
        original_synthesis = original_result.synthesis.final_consensus
        
        for alt_config in alternative_configs:
            try:
                start_time = time.time()
                
                # Run conference with alternative config
                alt_result = await self.conference_engine.run_conference(
                    query=original_result.query,
                    config=alt_config,
                    enable_grounding=False,  # Skip for speed
                    enable_fragility=False,
                )
                
                # Judge the results
                scores = await self.judge.evaluate(
                    query=original_result.query,
                    response_a=original_synthesis,
                    response_b=alt_result.synthesis.final_consensus,
                )
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Create result
                shadow_result = ShadowResult(
                    shadow_id=f"shadow_{uuid.uuid4().hex[:12]}",
                    original_conference_id=original_result.conference_id,
                    config_signature=self._config_signature(alt_config),
                    synthesis=alt_result.synthesis.final_consensus,
                    scores=scores,
                    duration_ms=duration_ms,
                    tokens_used=alt_result.token_usage.total_tokens,
                )
                
                results.append(shadow_result)
                self.results.append(shadow_result)
                
                logger.info(
                    f"Shadow run complete: {shadow_result.shadow_id}, "
                    f"preference={scores.overall_preference.value}, "
                    f"score={scores.total_score:.1f}"
                )
                
            except Exception as e:
                logger.error(f"Shadow run failed for config: {e}")
        
        # Save results
        self._save_results()
        
        return results
    
    async def run_batch(
        self,
        batch: ShadowBatch,
        conference_results: dict[str, ConferenceResult],
        configs: dict[str, ConferenceConfig],
    ) -> ShadowBatch:
        """
        Run a batch of shadow evaluations.
        
        Args:
            batch: Batch configuration
            conference_results: Map of conf_id -> ConferenceResult
            configs: Map of config_sig -> ConferenceConfig
            
        Returns:
            Updated batch with results
        """
        batch.status = "running"
        batch.started_at = datetime.now()
        
        for conf_id in batch.conference_ids:
            if conf_id not in conference_results:
                logger.warning(f"Conference {conf_id} not found, skipping")
                continue
            
            original = conference_results[conf_id]
            
            # Get alternative configs
            alt_configs = [
                configs[sig] 
                for sig in batch.alternative_configs 
                if sig in configs
            ]
            
            if not alt_configs:
                continue
            
            # Run evaluations
            results = await self.run_shadow_evaluation(original, alt_configs)
            
            for result in results:
                batch.add_result(result)
        
        batch.status = "completed"
        batch.completed_at = datetime.now()
        batch.total_runs = len(batch.conference_ids) * len(batch.alternative_configs)
        
        return batch
    
    def get_insights(self, min_samples: int = 5) -> list[ShadowInsight]:
        """
        Analyze shadow results and extract insights.
        
        Args:
            min_samples: Minimum samples needed for insight
            
        Returns:
            List of insights
        """
        insights = []
        
        if len(self.results) < min_samples:
            return insights
        
        # Analyze by config signature
        config_stats: dict[str, dict] = {}
        
        for result in self.results:
            sig = result.config_signature
            if sig not in config_stats:
                config_stats[sig] = {
                    "count": 0,
                    "improvements": 0,
                    "total_score": 0,
                }
            
            config_stats[sig]["count"] += 1
            config_stats[sig]["total_score"] += result.scores.total_score
            if result.scores.is_better:
                config_stats[sig]["improvements"] += 1
        
        # Find configs that consistently improve
        for sig, stats in config_stats.items():
            if stats["count"] >= min_samples:
                improvement_rate = stats["improvements"] / stats["count"]
                avg_score = stats["total_score"] / stats["count"]
                
                if improvement_rate > 0.6:
                    confidence = "HIGH" if stats["count"] >= 20 else "MEDIUM" if stats["count"] >= 10 else "LOW"
                    
                    insights.append(ShadowInsight(
                        insight_type="config_better",
                        description=f"Config '{sig[:30]}...' outperforms in {improvement_rate:.0%} of cases (avg score: {avg_score:.1f})",
                        sample_size=stats["count"],
                        confidence=confidence,
                        recommendation=f"Consider using config signature: {sig}",
                    ))
        
        return insights
    
    def get_summary(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> ShadowSummary:
        """
        Get summary of shadow mode findings.
        
        Args:
            start: Start of period (defaults to all time)
            end: End of period (defaults to now)
            
        Returns:
            ShadowSummary
        """
        start = start or datetime.min
        end = end or datetime.now()
        
        # Filter results by period
        period_results = [
            r for r in self.results
            if start <= r.created_at <= end
        ]
        
        if not period_results:
            return ShadowSummary(
                period_start=start,
                period_end=end,
            )
        
        # Calculate stats
        improvements = sum(1 for r in period_results if r.scores.is_better)
        unique_conferences = len(set(r.original_conference_id for r in period_results))
        unique_configs = len(set(r.config_signature for r in period_results))
        
        total_tokens = sum(r.tokens_used for r in period_results)
        
        # Find best config
        config_scores: dict[str, list[float]] = {}
        for r in period_results:
            if r.config_signature not in config_scores:
                config_scores[r.config_signature] = []
            config_scores[r.config_signature].append(r.scores.total_score)
        
        best_config = None
        best_avg = 0
        for sig, scores in config_scores.items():
            avg = sum(scores) / len(scores)
            if avg > best_avg:
                best_avg = avg
                best_config = sig
        
        return ShadowSummary(
            period_start=start,
            period_end=end,
            total_shadow_runs=len(period_results),
            conferences_replayed=unique_conferences,
            configs_tested=unique_configs,
            improvements_found=improvements,
            improvement_rate=improvements / len(period_results) if period_results else 0,
            insights=self.get_insights(),
            best_config_signature=best_config,
            best_config_avg_score=best_avg,
            total_tokens=total_tokens,
        )
    
    def _config_signature(self, config: ConferenceConfig) -> str:
        """Create a hashable signature for a configuration."""
        agent_models = sorted(a.model for a in config.agents)
        return (
            f"{config.num_rounds}:{config.arbitrator.model}:"
            f"{','.join(agent_models)}"
        )
    
    def _save_results(self):
        """Save results to storage."""
        if not self.storage_path:
            return
        
        try:
            data = [r.model_dump(mode="json") for r in self.results[-1000:]]  # Keep last 1000
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save shadow results: {e}")
    
    def _load_results(self):
        """Load results from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return
        
        try:
            data = json.loads(self.storage_path.read_text())
            self.results = [ShadowResult.model_validate(r) for r in data]
            logger.info(f"Loaded {len(self.results)} shadow results")
        except Exception as e:
            logger.error(f"Failed to load shadow results: {e}")

